#!/usr/bin/env python3
"""
Fix photo filenames in database to match actual downloaded files
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path("./vibecheck_full_output/vibecheck.db")
JSON_PATH = Path("./vibecheck_full_output/vibecheck_results.json")

print("Loading JSON data...")
data = json.load(open(JSON_PATH))

# Build place_id to downloaded_files mapping
place_id_to_files = {}
for restaurant in data:
    place_id = restaurant.get("info", {}).get("place_id")
    downloaded_files = restaurant.get("downloaded_files", [])
    if place_id and downloaded_files:
        place_id_to_files[place_id] = downloaded_files

print(f"Found {len(place_id_to_files)} restaurants with downloaded files")

# Connect to database
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all restaurants
cursor.execute("SELECT id, place_id FROM restaurants")
restaurants = cursor.fetchall()

updated_count = 0
for restaurant in restaurants:
    rest_id = restaurant['id']
    place_id = restaurant['place_id']

    if place_id not in place_id_to_files:
        continue

    downloaded_files = place_id_to_files[place_id]

    # Delete existing photos for this restaurant
    cursor.execute("DELETE FROM vibe_photos WHERE restaurant_id = ?", (rest_id,))

    # Insert correct filenames
    for filename in downloaded_files:
        cursor.execute("""
            INSERT INTO vibe_photos (restaurant_id, photo_url, local_filename)
            VALUES (?, NULL, ?)
        """, (rest_id, filename))

    updated_count += 1
    if updated_count % 100 == 0:
        print(f"Updated {updated_count} restaurants...")

conn.commit()
conn.close()

print(f"\n✅ Updated {updated_count} restaurants with correct photo filenames")
