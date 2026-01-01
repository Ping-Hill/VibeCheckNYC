#!/usr/bin/env python3
"""
Rebuild VibeCheck database from source JSON
============================================
Cleanly rebuilds the database from vibecheck_results.json
"""

import json
import sqlite3
from pathlib import Path

# ==============================================================================
# CONFIG
# ==============================================================================

INPUT_DIR = Path("./vibecheck_full_output")
RESULTS_FILE = INPUT_DIR / "vibecheck_results.json"
DB_PATH = INPUT_DIR / "vibecheck.db"
BACKUP_DB_PATH = INPUT_DIR / "vibecheck_backup_before_rebuild.db"

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("\n" + "=" * 60)
    print("🔧 REBUILDING VIBECHECK DATABASE FROM SOURCE JSON")
    print("=" * 60)

    # Check if results file exists
    if not RESULTS_FILE.exists():
        print(f"\n❌ Results file not found: {RESULTS_FILE}")
        return

    # Backup existing database
    if DB_PATH.exists():
        print(f"\n💾 Backing up existing database to {BACKUP_DB_PATH}...")
        import shutil
        shutil.copy2(DB_PATH, BACKUP_DB_PATH)
        print("✅ Backup complete")

        # Delete old database
        print(f"\n🗑️  Deleting corrupted database...")
        DB_PATH.unlink()

    # Load JSON data
    print(f"\n📂 Reading data from {RESULTS_FILE}...")
    with open(RESULTS_FILE) as f:
        data = json.load(f)
    print(f"✅ Loaded {len(data)} restaurants")

    # Initialize database
    print(f"\n📊 Creating new database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables
    print("   Creating tables...")

    # Main restaurants table
    cursor.execute("""
        CREATE TABLE restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            place_id TEXT UNIQUE NOT NULL,
            data_id TEXT,
            address TEXT,
            rating REAL,
            reviews_count INTEGER,
            neighborhood TEXT,
            price_level INTEGER
        )
    """)

    # Reviews table
    cursor.execute("""
        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER,
            review_text TEXT,
            likes INTEGER DEFAULT 0,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
    """)

    # Vibe photos table
    cursor.execute("""
        CREATE TABLE vibe_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER,
            photo_url TEXT,
            local_filename TEXT,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
    """)

    # Vibe analysis table
    cursor.execute("""
        CREATE TABLE vibe_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER,
            vibe_name TEXT,
            mention_count INTEGER,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        )
    """)

    print("✅ Tables created")

    # Load data
    print(f"\n🔄 Loading data into database...")
    restaurants_loaded = 0
    reviews_loaded = 0
    photos_loaded = 0
    vibes_loaded = 0
    skipped_duplicates = 0

    # Track seen place_ids to avoid duplicates
    seen_place_ids = set()

    for i, restaurant in enumerate(data):
        if (i + 1) % 100 == 0:
            print(f"   Processed {i + 1}/{len(data)} restaurants...")

        info = restaurant.get("info", {})
        place_id = info.get("place_id")

        # Skip if we've already seen this place_id
        if place_id in seen_place_ids:
            skipped_duplicates += 1
            continue

        seen_place_ids.add(place_id)

        # Insert restaurant
        cursor.execute("""
            INSERT INTO restaurants
            (name, place_id, data_id, address, rating, reviews_count, neighborhood, price_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            info.get("name"),
            place_id,
            info.get("data_id"),
            info.get("address"),
            info.get("rating"),
            info.get("reviews_count"),
            info.get("neighborhood"),
            info.get("price_level")
        ))

        restaurant_id = cursor.lastrowid
        restaurants_loaded += 1

        # Insert reviews (ONLY for this restaurant)
        for review in restaurant.get("reviews", []):
            cursor.execute("""
                INSERT INTO reviews (restaurant_id, review_text, likes)
                VALUES (?, ?, ?)
            """, (
                restaurant_id,
                review.get("text", ""),
                review.get("likes", 0)
            ))
            reviews_loaded += 1

        # Insert vibe photos - use ALL downloaded files, not just vibe_photos URLs
        photo_urls = restaurant.get("vibe_photos", [])
        downloaded_files = restaurant.get("downloaded_files", [])

        # Insert all downloaded files (AI-classified and ordered)
        for j, local_file in enumerate(downloaded_files):
            url = photo_urls[j] if j < len(photo_urls) else None
            cursor.execute("""
                INSERT INTO vibe_photos (restaurant_id, photo_url, local_filename)
                VALUES (?, ?, ?)
            """, (restaurant_id, url, local_file))
            photos_loaded += 1

        # Insert vibe analysis
        vibe_data = restaurant.get("vibe_analysis", {})
        top_vibes = vibe_data.get("top_vibes", [])

        for vibe_name, count in top_vibes:
            cursor.execute("""
                INSERT INTO vibe_analysis (restaurant_id, vibe_name, mention_count)
                VALUES (?, ?, ?)
            """, (restaurant_id, vibe_name, count))
            vibes_loaded += 1

    conn.commit()
    conn.close()

    print(f"\n✅ Database rebuild complete!")
    print(f"\n📊 STATISTICS:")
    print(f"   🍽️  Restaurants loaded: {restaurants_loaded}")
    print(f"   ⚠️  Skipped duplicates: {skipped_duplicates}")
    print(f"   📝 Reviews loaded: {reviews_loaded}")
    print(f"   📷 Photos loaded: {photos_loaded}")
    print(f"   💫 Vibes loaded: {vibes_loaded}")

    # Verify the fix
    print(f"\n🔍 Verifying fix...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check Stick To My Pot
    cursor.execute("""
        SELECT r.name, rev.review_text
        FROM restaurants r
        JOIN reviews rev ON r.id = rev.restaurant_id
        WHERE r.name = 'Stick To My Pot'
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row:
        print(f"\n   'Stick To My Pot' first review:")
        print(f"   {row[1][:100]}...")

    # Check for duplicate reviews
    cursor.execute("""
        SELECT COUNT(DISTINCT review_text) as unique_reviews,
               COUNT(*) as total_reviews
        FROM reviews
    """)
    unique, total = cursor.fetchone()
    print(f"\n   Total reviews: {total}")
    print(f"   Unique reviews: {unique}")
    print(f"   Duplicates: {total - unique}")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ DATABASE REBUILD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
