#!/usr/bin/env python3
"""
Restore full 15 reviews per restaurant from backup database
===========================================================
Uses the Dec 22 backup which has correct 15 reviews per restaurant,
but copies them correctly matched to place_ids to avoid the duplication bug.
"""

import sqlite3
from pathlib import Path

# ==============================================================================
# CONFIG
# ==============================================================================

OUTPUT_DIR = Path("./vibecheck_full_output")
CURRENT_DB = OUTPUT_DIR / "vibecheck.db"
BACKUP_DB = OUTPUT_DIR / "backups/vibecheck_backup_20251222_234838.db"
BACKUP_CURRENT = OUTPUT_DIR / "vibecheck_backup_before_review_restore.db"

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("\n" + "=" * 60)
    print("📝 RESTORING FULL REVIEWS FROM BACKUP")
    print("=" * 60)

    if not BACKUP_DB.exists():
        print(f"\n❌ Backup database not found: {BACKUP_DB}")
        return

    # Backup current database
    print(f"\n💾 Backing up current database...")
    import shutil
    shutil.copy2(CURRENT_DB, BACKUP_CURRENT)
    print("✅ Backup complete")

    # Connect to both databases
    current_conn = sqlite3.connect(CURRENT_DB)
    current_conn.row_factory = sqlite3.Row
    current_cursor = current_conn.cursor()

    backup_conn = sqlite3.connect(BACKUP_DB)
    backup_conn.row_factory = sqlite3.Row
    backup_cursor = backup_conn.cursor()

    # Clear existing reviews in current database
    print(f"\n🗑️  Clearing existing reviews...")
    current_cursor.execute("DELETE FROM reviews")
    current_conn.commit()

    # Get place_id to restaurant_id mapping from CURRENT database
    print(f"\n📊 Building place_id mappings...")
    current_cursor.execute("SELECT id, place_id FROM restaurants")
    place_id_to_current_id = {row['place_id']: row['id'] for row in current_cursor.fetchall()}
    print(f"   Found {len(place_id_to_current_id)} restaurants in current DB")

    # Get place_id mapping from BACKUP database
    backup_cursor.execute("SELECT id, place_id FROM restaurants")
    place_id_to_backup_id = {row['place_id']: row['id'] for row in backup_cursor.fetchall()}
    print(f"   Found {len(place_id_to_backup_id)} restaurants in backup DB")

    # Copy reviews using place_id matching
    print(f"\n🔄 Copying reviews from backup...")
    reviews_copied = 0
    restaurants_with_reviews = 0
    skipped_restaurants = 0

    for place_id, current_rest_id in place_id_to_current_id.items():
        backup_rest_id = place_id_to_backup_id.get(place_id)

        if not backup_rest_id:
            skipped_restaurants += 1
            continue

        # Get reviews from backup for this restaurant
        backup_cursor.execute("""
            SELECT review_text, likes
            FROM reviews
            WHERE restaurant_id = ?
        """, (backup_rest_id,))

        reviews = backup_cursor.fetchall()

        if reviews:
            restaurants_with_reviews += 1
            for review in reviews:
                current_cursor.execute("""
                    INSERT INTO reviews (restaurant_id, review_text, likes)
                    VALUES (?, ?, ?)
                """, (current_rest_id, review['review_text'], review['likes']))
                reviews_copied += 1

        if restaurants_with_reviews % 100 == 0:
            print(f"   Processed {restaurants_with_reviews} restaurants...")

    current_conn.commit()

    print(f"\n✅ Review restoration complete!")
    print(f"\n📊 STATISTICS:")
    print(f"   🍽️  Restaurants with reviews: {restaurants_with_reviews}")
    print(f"   ⚠️  Skipped (not in backup): {skipped_restaurants}")
    print(f"   📝 Total reviews copied: {reviews_copied}")

    # Verify
    print(f"\n🔍 Verifying restoration...")
    current_cursor.execute("""
        SELECT name, COUNT(r.id) as review_count
        FROM restaurants rest
        JOIN reviews r ON rest.id = r.restaurant_id
        GROUP BY rest.id
        ORDER BY review_count DESC
        LIMIT 5
    """)

    print("\n   Top restaurants by review count:")
    for row in current_cursor.fetchall():
        print(f"   {row['name']}: {row['review_count']} reviews")

    current_conn.close()
    backup_conn.close()

    print("\n" + "=" * 60)
    print("✅ REVIEW RESTORATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
