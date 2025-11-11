#!/usr/bin/env python3
"""sales_over_time.py

Read the daily_revenue JSON and write its contents to MongoDB collection
`sales_over_time`. Replaces previous documents on each run. Uses the DB
name embedded in the MONGO_URI (or MONGO_DB env override).

Usage:
  python sales_over_time.py [path/to/daily_revenue.json]

"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Dict

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file won't be loaded.")
    load_dotenv = None


def read_json(path: Path) -> List[Dict]:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def write_to_mongo(records: List[Dict]):
    try:
        from pymongo import MongoClient
    except Exception:
        raise RuntimeError('pymongo is required; install it in the environment')

    # Load environment variables from .env file
    if load_dotenv:
        # Look for .env file in parent directory (server/)
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"[ENV] Loaded environment variables from: {env_path}")
        else:
            print("⚠️  No .env file found in server directory")

    mongo_uri = os.environ.get('MONGO_URI') or os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017'

    client = MongoClient(mongo_uri)
    try:
        # prefer DB from URI unless env override provided
        db_override = os.environ.get('MONGO_DB') or os.environ.get('MONGO_DB_NAME')
        default_db = None
        try:
            default_db = client.get_default_database()
        except Exception:
            default_db = None

        if default_db is not None and not db_override:
            db_name = default_db.name
        else:
            db_name = db_override or (default_db.name if default_db is not None else 'swas')

        print(f'Writing {len(records)} records to {db_name}.sales_over_time')
        db = client[db_name]
        coll = db['sales_over_time']

        coll.delete_many({})
        inserted = 0
        if records:
            res = coll.insert_many(records)
            inserted = len(res.inserted_ids) if res and hasattr(res, 'inserted_ids') else len(records)

        print(f'Inserted {inserted} documents into {db_name}.sales_over_time')
    finally:
        client.close()


def main():
    import sys

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('output/daily_revenue.json')
    if not path.exists():
        print('Input file not found:', path)
        raise SystemExit(2)

    data = read_json(path)
    write_to_mongo(data)


if __name__ == '__main__':
    main()
