#!/usr/bin/env python3
"""
clean_transaction_revenue.py

Produce a cleaned CSV with columns: date_time,transaction_id,revenue,branch_id
from MongoDB collections. Only completed transactions (date_out not null)
are included. Revenue is the sum of payments for the transaction.

Usage:
  python clean_transaction_revenue.py --db-uri "mongodb://localhost:27017/swas_db" --out cleaned_transactions_revenue.csv
  
Or with default local MongoDB:
  python clean_transaction_revenue.py --out cleaned_transactions_revenue.csv

Requires:
  pip install pymongo
"""
from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    from pymongo import MongoClient
except ImportError:
    raise RuntimeError('pymongo is required; install it with: pip install pymongo')

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file won't be loaded.")
    load_dotenv = None


def connect_to_db(db_uri: str):
    """Connect to MongoDB and return database instance"""
    try:
        client = MongoClient(db_uri)
        
        # Extract database name from URI or use default
        db_name = "swas_db"  # default database name
        if "/" in db_uri and db_uri.split("/")[-1]:
            # Extract database name, handle query parameters
            db_part = db_uri.split("/")[-1]
            if "?" in db_part:
                db_name = db_part.split("?")[0]
            else:
                db_name = db_part
        
        db = client[db_name]
        
        # Test connection
        client.admin.command('ping')
        print(f"[SUCCESS] Successfully connected to database: {db_name}")
        return db, client
        
    except Exception as e:
        print(f"[ERROR] Failed to connect to MongoDB: {e}")
        raise


def read_transactions_from_db(db) -> List[Dict[str, Any]]:
    """Read transactions from MongoDB"""
    collection = db['transactions']
    transactions = list(collection.find({}))
    
    # Convert ObjectId to string and handle date fields
    for tx in transactions:
        if '_id' in tx:
            tx['_id'] = str(tx['_id'])
        # Convert datetime objects to ISO strings for consistency
        if 'date_in' in tx and tx['date_in']:
            tx['date_in'] = tx['date_in'].isoformat() if hasattr(tx['date_in'], 'isoformat') else tx['date_in']
        if 'date_out' in tx and tx['date_out']:
            tx['date_out'] = tx['date_out'].isoformat() if hasattr(tx['date_out'], 'isoformat') else tx['date_out']
    
    print(f"[DATA] Retrieved {len(transactions)} transactions from database")
    return transactions


def read_payments_from_db(db) -> List[Dict[str, Any]]:
    """Read payments from MongoDB"""
    collection = db['payments']
    payments = list(collection.find({}))
    
    # Convert ObjectId to string and handle date fields
    for payment in payments:
        if '_id' in payment:
            payment['_id'] = str(payment['_id'])
        # Convert datetime objects to ISO strings for consistency
        if 'payment_date' in payment and payment['payment_date']:
            payment['payment_date'] = payment['payment_date'].isoformat() if hasattr(payment['payment_date'], 'isoformat') else payment['payment_date']
    
    print(f"[DATA] Retrieved {len(payments)} payments from database")
    return payments


def parse_date(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    try:
        # try ISO formats
        return datetime.fromisoformat(v)
    except Exception:
        # try some common formats
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(v, fmt)
            except Exception:
                continue
    return None


def parse_args():
    # Load environment variables from .env file
    if load_dotenv:
        # Look for .env file in parent directory (server/)
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"[ENV] Loaded environment variables from: {env_path}")
        else:
            print("[WARN] No .env file found in server directory")
    
    # Use environment variable if available, otherwise default
    default_uri = os.environ.get('MONGO_URI') or os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/swas_db'
    
    # Don't show the actual URI in help for security
    help_text = 'MongoDB connection URI (loaded from MONGO_URI environment variable or defaults to localhost)'
    
    p = argparse.ArgumentParser()
    p.add_argument('--db-uri', default=default_uri, help=help_text)
    p.add_argument('--out', default='output/cleaned_transactions_revenue.csv')
    return p.parse_args()


def to_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def main():
    args = parse_args()

    # Connect to MongoDB (don't display full URI for security)
    print("[DB] Connecting to MongoDB...")
    db, client = connect_to_db(args.db_uri)
    
    try:
        # Read data from MongoDB collections
        tx_rows = read_transactions_from_db(db)
        pay_rows = read_payments_from_db(db)

        # Sum payments by transaction_id
        payments_by_tx = defaultdict(float)
        for p in pay_rows:
            txid = p.get('transaction_id') or p.get('transactionId')
            if not txid:
                continue
            amt = to_float(p.get('payment_amount') or p.get('amount') or p.get('payment') or 0)
            payments_by_tx[str(txid)] += amt

        out_path = args.out
        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)

        with open(out_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['date_time', 'transaction_id', 'revenue', 'branch_id'])

            completed_count = 0
            for r in tx_rows:
                date_out_raw = r.get('date_out')
                date_out_dt = parse_date(date_out_raw) if date_out_raw not in (None, '', 'null') else None
                if date_out_dt is None:
                    continue

                txid = r.get('transaction_id') or r.get('transactionId')
                branch = r.get('branch_id') or r.get('branchId') or r.get('branch')
                revenue = round(payments_by_tx.get(str(txid), 0.0), 2)

                # Use ISO 8601 datetime string for date_time
                date_time_str = date_out_dt.isoformat()
                writer.writerow([date_time_str, str(txid), f"{revenue:.2f}", branch])
                completed_count += 1

            print(f'[SUCCESS] Processed {completed_count} completed transactions')
            print(f'[OUTPUT] Wrote cleaned CSV to {out_path}')
        
    finally:
        # Close database connection
        if client:
            client.close()
            print("[DB] Disconnected from MongoDB")


if __name__ == '__main__':
    main()
