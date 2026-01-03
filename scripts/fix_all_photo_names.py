#!/usr/bin/env python3
"""
Fix ALL photo filenames in database to match the human-readable files in S3
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path("./vibecheck_full_output/vibecheck.db")
IMAGES_DIR = Path("./vibecheck_full_output/images_compressed")

# Get all actual image files
print("Scanning image files...")
all_image_files = list(IMAGES_DIR.glob("*.jpg"))
print(f"Found {len(all_image_files)} image files")

# Build restaurant name -> files mapping
restaurant_files = {}
for img_path in all_image_files:
    filename = img_path.name
    # Extract restaurant name from filename (everything before _vibe_)
    if "_vibe_" in filename:
        rest_name = filename.split("_vibe_")[0].replace("_", " ")
        if rest_name not in restaurant_files:
            restaurant_files[rest_name] = []
        restaurant_files[rest_name].append(filename)

print(f"Found {len(restaurant_files)} unique restaurant names in files")

# Sort files for each restaurant
for rest_name in restaurant_files:
    restaurant_files[rest_name].sort()

# Connect to database
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all restaurants
cursor.execute("SELECT id, name, place_id FROM restaurants")
restaurants = cursor.fetchall()

updated_count = 0
matched_count = 0
no_match_count = 0

for restaurant in restaurants:
    rest_id = restaurant['id']
    rest_name = restaurant['name']

    # Try exact match first
    normalized_name = rest_name.replace(" ", "_").replace("'", "").replace("-", "_").replace(".", "").replace("&", "").replace("(", "").replace(")", "").replace("/", "_").replace(",", "")

    # Look for matching files
    matching_files = None

    # Try different variations
    for key in restaurant_files.keys():
        if normalized_name.lower() == key.lower() or \
           normalized_name.lower().replace("__", "_") == key.lower() or \
           key.lower() in normalized_name.lower() or \
           normalized_name.lower() in key.lower():
            matching_files = restaurant_files[key]
            matched_count += 1
            break

    if not matching_files:
        no_match_count += 1
        continue

    # Delete existing photos
    cursor.execute("DELETE FROM vibe_photos WHERE restaurant_id = ?", (rest_id,))

    # Insert correct filenames
    for filename in matching_files:
        cursor.execute("""
            INSERT INTO vibe_photos (restaurant_id, photo_url, local_filename)
            VALUES (?, NULL, ?)
        """, (rest_id, filename))

    updated_count += 1
    if updated_count % 100 == 0:
        print(f"Updated {updated_count} restaurants...")

conn.commit()
conn.close()

print(f"\n✅ DONE!")
print(f"   Updated: {updated_count} restaurants")
print(f"   Matched: {matched_count} restaurants")
print(f"   No match: {no_match_count} restaurants")
