#!/usr/bin/env python3
"""
replace_db_data.py

Replace MongoDB collections with generated test data.
This script will:
1. Connect to MongoDB
2. Drop existing collections
3. Insert new test data from JSON files

Usage:
  python replace_db_data.py --db-uri "mongodb://localhost:27017/your_db_name"
  
Or with default local MongoDB:
  python replace_db_data.py

Requires:
  pip install pymongo
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file won't be loaded.")
    load_dotenv = None


def convert_iso_strings_to_dates(obj: Any) -> Any:
    """
    Recursively convert ISO datetime strings to Python datetime objects.
    Handles nested dictionaries, lists, and direct values.
    
    Args:
        obj: The object to process (dict, list, or primitive value)
    
    Returns:
        The processed object with ISO strings converted to datetime objects
    """
    # ISO 8601 datetime pattern with timezone: YYYY-MM-DDTHH:MM:SS.sss+00:00
    iso_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$')
    
    if isinstance(obj, dict):
        # Process dictionary recursively
        return {key: convert_iso_strings_to_dates(value) for key, value in obj.items()}
    
    elif isinstance(obj, list):
        # Process list recursively
        return [convert_iso_strings_to_dates(item) for item in obj]
    
    elif isinstance(obj, str):
        # Check if string matches ISO datetime pattern
        if iso_pattern.match(obj):
            try:
                # Convert ISO string to datetime object
                # Remove the +00:00 timezone suffix and parse
                iso_str = obj[:-6]  # Remove +00:00
                dt = datetime.strptime(iso_str, '%Y-%m-%dT%H:%M:%S.%f')
                return dt
            except ValueError:
                # If parsing fails, return original string
                return obj
        else:
            return obj
    
    else:
        # Return primitive values unchanged
        return obj


class DatabaseReplacer:
    def __init__(self, db_uri: str = "mongodb://localhost:27017/swas_db", data_dir: str = "./output"):
        """
        Initialize the database replacer
        
        Args:
            db_uri: MongoDB connection URI
            data_dir: Directory containing the JSON files
        """
        self.db_uri = db_uri
        self.data_dir = data_dir
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        
        # Collection mapping: file_name -> collection_name
        self.collection_mapping = {
            "customers.json": "customers",
            "line_items.json": "line_items", 
            "payments.json": "payments",
            "promos.json": "promos",
            "transactions.json": "transactions",
            "unavailability.json": "unavailability",
            "appointments.json": "appointments"
        }
    
    def connect(self) -> bool:
        """Connect to MongoDB"""
        try:
            print("🔌 Connecting to MongoDB...")
            self.client = MongoClient(self.db_uri)
            
            # Extract database name from URI or use default
            if "/" in self.db_uri and self.db_uri.split("/")[-1]:
                db_name = self.db_uri.split("/")[-1]
                # Remove query parameters if present
                if "?" in db_name:
                    db_name = db_name.split("?")[0]
            else:
                db_name = "swas_db"  # default database name
            
            self.db = self.client[db_name]
            
            # Test connection
            self.client.admin.command('ping')
            print(f"✅ Successfully connected to database: {db_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            print("🔌 Disconnected from MongoDB")
    
    def load_json_file(self, file_path: str) -> Optional[List[Dict]]:
        """Load data from JSON file"""
        try:
            if not os.path.exists(file_path):
                print(f"⚠️  File not found: {file_path}")
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not isinstance(data, list):
                print(f"⚠️  Expected list in {file_path}, got {type(data)}")
                return None
                
            print(f"📂 Loaded {len(data)} records from {file_path}")
            return data
            
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
            return None
    
    def drop_collection(self, collection_name: str) -> bool:
        """Drop a collection if it exists"""
        try:
            if collection_name in self.db.list_collection_names():
                self.db[collection_name].drop()
                print(f"🗑️  Dropped existing collection: {collection_name}")
            else:
                print(f"ℹ️  Collection {collection_name} does not exist, skipping drop")
            return True
            
        except Exception as e:
            print(f"❌ Error dropping collection {collection_name}: {e}")
            return False
    
    def insert_data(self, collection_name: str, data: List[Dict]) -> bool:
        """Insert data into a collection, converting ISO datetime strings to Date objects"""
        try:
            if not data:
                print(f"⚠️  No data to insert into {collection_name}")
                return True
            
            # Convert ISO datetime strings to Python datetime objects
            print(f"🔄 Converting ISO datetime strings to Date objects...")
            converted_data = convert_iso_strings_to_dates(data)
            
            collection: Collection = self.db[collection_name]
            result = collection.insert_many(converted_data)
            
            print(f"✅ Inserted {len(result.inserted_ids)} documents into {collection_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error inserting data into {collection_name}: {e}")
            return False
    
    def replace_collection(self, file_name: str, collection_name: str) -> bool:
        """Replace a collection with data from JSON file"""
        print(f"\n🔄 Processing {file_name} -> {collection_name}")
        
        # Load data from file
        file_path = os.path.join(self.data_dir, file_name)
        data = self.load_json_file(file_path)
        
        if data is None:
            return False
        
        # Drop existing collection
        if not self.drop_collection(collection_name):
            return False
        
        # Insert new data
        return self.insert_data(collection_name, data)
    
    def replace_all_collections(self) -> bool:
        """Replace all collections with test data"""
        print("🚀 Starting database replacement process...")
        print("=" * 50)
        
        success_count = 0
        total_count = len(self.collection_mapping)
        
        for file_name, collection_name in self.collection_mapping.items():
            if self.replace_collection(file_name, collection_name):
                success_count += 1
            else:
                print(f"⚠️  Failed to replace {collection_name}")
        
        print("\n" + "=" * 50)
        print(f"📊 Summary: {success_count}/{total_count} collections replaced successfully")
        
        if success_count == total_count:
            print("🎉 Database replacement completed successfully!")
            return True
        else:
            print("⚠️  Some collections failed to replace")
            return False
    
    def verify_data(self) -> bool:
        """Verify the replaced data by counting documents in each collection"""
        print("\n🔍 Verifying replaced data...")
        print("-" * 30)
        
        all_good = True
        
        for file_name, collection_name in self.collection_mapping.items():
            try:
                # Count documents in collection
                doc_count = self.db[collection_name].count_documents({})
                
                # Load original file to compare count
                file_path = os.path.join(self.data_dir, file_name)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        original_data = json.load(f)
                    original_count = len(original_data) if isinstance(original_data, list) else 0
                    
                    if doc_count == original_count:
                        print(f"✅ {collection_name}: {doc_count} documents")
                    else:
                        print(f"⚠️  {collection_name}: {doc_count} documents (expected {original_count})")
                        all_good = False
                else:
                    print(f"✅ {collection_name}: {doc_count} documents (file not found for verification)")
                    
            except Exception as e:
                print(f"❌ Error verifying {collection_name}: {e}")
                all_good = False
        
        print("-" * 30)
        if all_good:
            print("✅ All collections verified successfully!")
        else:
            print("⚠️  Some verification issues found")
            
        return all_good


def parse_args():
    # Load environment variables from .env file
    if load_dotenv:
        # Look for .env file in parent directory (server/)
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"📁 Loaded environment variables from: {env_path}")
        else:
            print("⚠️  No .env file found in server directory")
    
    # Use environment variable if available, otherwise default
    default_uri = os.environ.get('MONGO_URI') or os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/swas_db'
    
    parser = argparse.ArgumentParser(description='Replace MongoDB collections with test data')
    parser.add_argument(
        '--db-uri', 
        type=str, 
        default=default_uri,
        help='MongoDB connection URI (loaded from MONGO_URI environment variable or defaults to localhost)'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='./output',
        help='Directory containing JSON files (default: ./output)'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify existing data, don\'t replace'
    )
    parser.add_argument(
        '--skip-verification',
        action='store_true',
        help='Skip verification after replacement'
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("🔧 MongoDB Database Replacer")
    print("=" * 50)
    print("Database URI: [Loaded from environment]")
    print(f"Data Directory: {args.data_dir}")
    print("=" * 50)
    
    # Initialize replacer
    replacer = DatabaseReplacer(
        db_uri=args.db_uri,
        data_dir=args.data_dir
    )
    
    # Connect to database
    if not replacer.connect():
        return 1
    
    try:
        if args.verify_only:
            # Only verify existing data
            replacer.verify_data()
        else:
            # Replace collections
            success = replacer.replace_all_collections()
            
            # Verify if requested
            if not args.skip_verification and success:
                replacer.verify_data()
            
            if not success:
                return 1
                
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        return 1
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
        
    finally:
        replacer.disconnect()
    
    print("\n✨ Operation completed!")
    return 0


if __name__ == "__main__":
    exit(main())