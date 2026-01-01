"""
Remove duplicate photo entries from vibe_photos table.
Keep only the first instance of each unique (restaurant_id, local_filename) combination.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "vibecheck_full_output" / "vibecheck.db"

def remove_duplicates():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("REMOVING DUPLICATE PHOTO ENTRIES")
    print("=" * 80)

    # Find duplicates
    cursor.execute("""
        SELECT restaurant_id, local_filename, COUNT(*) as count
        FROM vibe_photos
        GROUP BY restaurant_id, local_filename
        HAVING count > 1
        ORDER BY count DESC
    """)

    duplicates = cursor.fetchall()
    print(f"\nFound {len(duplicates)} unique photo entries with duplicates")

    total_to_delete = sum(count - 1 for _, _, count in duplicates)
    print(f"Total duplicate entries to delete: {total_to_delete}")

    # Show sample
    print("\nSample duplicates:")
    for resto_id, filename, count in duplicates[:10]:
        cursor.execute("SELECT name FROM restaurants WHERE id = ?", (resto_id,))
        resto_name = cursor.fetchone()[0]
        print(f"  {resto_name}: {filename} ({count} copies)")

    deleted_count = 0

    for resto_id, filename, count in duplicates:
        # Get all IDs for this duplicate
        cursor.execute("""
            SELECT id FROM vibe_photos
            WHERE restaurant_id = ? AND local_filename = ?
            ORDER BY id
        """, (resto_id, filename))

        ids = [row[0] for row in cursor.fetchall()]

        # Keep the first one, delete the rest
        ids_to_delete = ids[1:]

        for photo_id in ids_to_delete:
            cursor.execute("DELETE FROM vibe_photos WHERE id = ?", (photo_id,))
            deleted_count += 1

        if deleted_count % 100 == 0:
            print(f"  Deleted {deleted_count}/{total_to_delete} duplicates...")

    conn.commit()

    print(f"\n✓ Deleted {deleted_count} duplicate photo entries")

    # Final count
    cursor.execute("SELECT COUNT(*) FROM vibe_photos")
    final_count = cursor.fetchone()[0]
    print(f"Total photos remaining: {final_count}")

    # Verify no duplicates remain
    cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT restaurant_id, local_filename, COUNT(*) as count
            FROM vibe_photos
            GROUP BY restaurant_id, local_filename
            HAVING count > 1
        )
    """)
    remaining_dups = cursor.fetchone()[0]
    print(f"Remaining duplicates: {remaining_dups}")

    conn.close()

if __name__ == "__main__":
    remove_duplicates()
