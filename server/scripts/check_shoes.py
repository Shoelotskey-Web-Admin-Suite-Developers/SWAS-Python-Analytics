#!/usr/bin/env python3
import pymongo
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')

# Connect to MongoDB
client = pymongo.MongoClient(os.getenv('MONGODB_URI'))
db = client['swas_database']

# Get sample line items to check shoe models
items = list(db.line_items.find({}, {'shoes': 1, 'line_item_id': 1}).limit(10))

print('Sample shoe models in database:')
for item in items:
    print(f"- {item['line_item_id']}: {item['shoes']}")

# Close connection
client.close()