#!/usr/bin/env python3
"""
Add latitude and longitude columns to restaurants table and populate from raw_data
"""

import sqlite3
import json

DB_PATH = "vibecheck_full_output/vibecheck.db"

def add_columns():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Add latitude and longitude columns if they don't exist
    try:
        cursor.execute("ALTER TABLE restaurants ADD COLUMN latitude REAL")
        print("✅ Added latitude column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️  latitude column already exists")
        else:
            raise

    try:
        cursor.execute("ALTER TABLE restaurants ADD COLUMN longitude REAL")
        print("✅ Added longitude column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️  longitude column already exists")
        else:
            raise

    conn.commit()

    # Populate latitude and longitude from all_restaurants.json
    print(f"\nLoading restaurant data...")

    with open("vibecheck_full_output/all_restaurants.json", 'r') as f:
        all_restaurants = json.load(f)

    # Create a dict mapping place_id to coordinates
    coords_by_place_id = {}
    for rest in all_restaurants:
        place_id = rest.get('place_id')
        lat = rest.get('latitude')
        lon = rest.get('longitude')
        if place_id and lat is not None and lon is not None:
            coords_by_place_id[place_id] = (lat, lon)

    print(f"Found coordinates for {len(coords_by_place_id)} restaurants")

    # Update database
    cursor.execute("SELECT id, place_id FROM restaurants")
    restaurants = cursor.fetchall()

    print(f"Updating {len(restaurants)} restaurants in database...")

    updated = 0
    for rest_id, place_id in restaurants:
        if place_id in coords_by_place_id:
            lat, lon = coords_by_place_id[place_id]
            cursor.execute(
                "UPDATE restaurants SET latitude = ?, longitude = ? WHERE id = ?",
                (lat, lon, rest_id)
            )
            updated += 1

    conn.commit()
    print(f"✅ Updated {updated} restaurants with coordinates")

    # Show stats
    cursor.execute("SELECT COUNT(*) FROM restaurants WHERE latitude IS NOT NULL")
    with_coords = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM restaurants")
    total = cursor.fetchone()[0]

    print(f"\n📊 Stats:")
    print(f"   Total restaurants: {total}")
    print(f"   With coordinates: {with_coords}")
    print(f"   Missing coordinates: {total - with_coords}")

    conn.close()

if __name__ == "__main__":
    add_columns()
