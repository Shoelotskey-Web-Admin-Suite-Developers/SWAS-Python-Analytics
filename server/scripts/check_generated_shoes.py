#!/usr/bin/env python3
import json

# Load the generated line_items.json file
with open('./output/line_items.json', 'r') as f:
    data = json.load(f)

print('Sample shoe models from generated data:')
for i, item in enumerate(data[:10]):
    print(f"- {item['shoes']}")