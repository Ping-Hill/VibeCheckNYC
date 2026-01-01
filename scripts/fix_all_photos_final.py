"""
Final photo fix script:
1. Reroute ChIJ photos to correct restaurants (match ChIJ ID in filename to restaurant place_id)
2. Remove duplicate database entries (keep only 1 entry per unique restaurant_id + filename)
3. Triple-check everything before applying

NO FILES WILL BE DELETED - only database entries fixed
"""
import sqlite3
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "vibecheck_full_output" / "vibecheck.db"

def extract_place_id_from_filename(filename):
    """Extract Google Place ID from ChIJ filename."""
    if not filename.startswith('ChIJ'):
        return None
    # ChIJq4U9crpZwokRQ1CSpBwEgSw_1.jpg -> ChIJq4U9crpZwokRQ1CSpBwEgSw
    parts = filename.split('_')
    if len(parts) >= 2:
        return parts[0]  # Everything before the first underscore
    return None

def fix_all_photos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("PHOTO FIX - FINAL VERSION")
    print("=" * 80)

    # Step 1: Build a map of place_id -> restaurant_id
    cursor.execute("SELECT id, place_id, name FROM restaurants")
    restaurants = cursor.fetchall()

    place_id_to_resto = {}
    for resto_id, place_id, name in restaurants:
        place_id_to_resto[place_id] = (resto_id, name)

    print(f"\nLoaded {len(restaurants)} restaurants")

    # Step 2: Get all photos
    cursor.execute("SELECT id, local_filename, restaurant_id FROM vibe_photos ORDER BY id")
    all_photos = cursor.fetchall()
    print(f"Found {len(all_photos)} total photo entries in database")

    # Step 3: Analyze what needs to be fixed
    chi_reroutes = []  # ChIJ photos that need rerouting
    duplicates_to_remove = []  # Duplicate entries to remove

    # Track unique photos per restaurant
    seen_photos = defaultdict(set)  # {restaurant_id: {filename1, filename2, ...}}
    photo_entries = defaultdict(list)  # {(restaurant_id, filename): [id1, id2, ...]}

    for photo_id, filename, restaurant_id in all_photos:
        key = (restaurant_id, filename)
        photo_entries[key].append(photo_id)

    print(f"\nAnalyzing photos...")

    # Find ChIJ photos that need rerouting
    chi_count = 0
    chi_correct = 0
    chi_need_reroute = 0

    for photo_id, filename, current_resto_id in all_photos:
        if filename and filename.startswith('ChIJ'):
            chi_count += 1
            place_id = extract_place_id_from_filename(filename)

            if place_id and place_id in place_id_to_resto:
                correct_resto_id, correct_name = place_id_to_resto[place_id]

                if correct_resto_id != current_resto_id:
                    chi_need_reroute += 1
                    chi_reroutes.append({
                        'photo_id': photo_id,
                        'filename': filename,
                        'old_resto_id': current_resto_id,
                        'new_resto_id': correct_resto_id,
                        'new_resto_name': correct_name
                    })
                else:
                    chi_correct += 1

    print(f"\nChIJ Photos Analysis:")
    print(f"  Total ChIJ photos: {chi_count}")
    print(f"  Already correctly assigned: {chi_correct}")
    print(f"  Need rerouting: {chi_need_reroute}")

    # Find duplicates
    duplicate_count = 0
    for (resto_id, filename), photo_ids in photo_entries.items():
        if len(photo_ids) > 1:
            # Keep the first one, mark rest for deletion
            duplicate_count += len(photo_ids) - 1
            for photo_id in photo_ids[1:]:
                duplicates_to_remove.append({
                    'photo_id': photo_id,
                    'filename': filename,
                    'resto_id': resto_id
                })

    print(f"\nDuplicate Database Entries:")
    print(f"  Total duplicate entries to remove: {len(duplicates_to_remove)}")

    # Show samples
    print(f"\nSample ChIJ reroutes (first 10):")
    for reroute in chi_reroutes[:10]:
        cursor.execute("SELECT name FROM restaurants WHERE id = ?", (reroute['old_resto_id'],))
        old_name_result = cursor.fetchone()
        old_name = old_name_result[0] if old_name_result else "Unknown"
        print(f"  {reroute['filename']}")
        print(f"    FROM: {old_name} (ID {reroute['old_resto_id']})")
        print(f"    TO:   {reroute['new_resto_name']} (ID {reroute['new_resto_id']})")

    print(f"\nSample duplicates to remove (first 10):")
    for dup in duplicates_to_remove[:10]:
        cursor.execute("SELECT name FROM restaurants WHERE id = ?", (dup['resto_id'],))
        resto_name = cursor.fetchone()[0]
        print(f"  {resto_name}: {dup['filename']} (photo_id: {dup['photo_id']})")

    # Triple check: Calculate final expected counts
    print("\n" + "=" * 80)
    print("TRIPLE CHECK - EXPECTED RESULTS")
    print("=" * 80)

    current_total = len(all_photos)
    expected_after_dedup = current_total - len(duplicates_to_remove)

    print(f"Current total photo entries: {current_total}")
    print(f"Will remove duplicates: {len(duplicates_to_remove)}")
    print(f"Will reroute ChIJ photos: {len(chi_reroutes)}")
    print(f"Expected final photo entries: {expected_after_dedup}")

    # Count unique photos per restaurant after dedup
    unique_photos_per_resto = defaultdict(int)
    for (resto_id, filename), photo_ids in photo_entries.items():
        unique_photos_per_resto[resto_id] += 1  # Count each unique photo once

    # Adjust for reroutes
    for reroute in chi_reroutes:
        old_id = reroute['old_resto_id']
        new_id = reroute['new_resto_id']
        filename = reroute['filename']

        # Only adjust if it's not a duplicate (i.e., only 1 entry exists)
        key = (old_id, filename)
        if len(photo_entries[key]) == 1:
            unique_photos_per_resto[old_id] -= 1
            unique_photos_per_resto[new_id] += 1

    # Show distribution
    photo_count_distribution = defaultdict(int)
    for resto_id, count in unique_photos_per_resto.items():
        photo_count_distribution[count] += 1

    print(f"\nExpected photo distribution after fix:")
    for count in sorted(photo_count_distribution.keys(), reverse=True):
        num_restos = photo_count_distribution[count]
        print(f"  {count} photos: {num_restos} restaurants")

    print("\n" + "=" * 80)
    print("APPLYING FIXES")
    print("=" * 80)

    # Apply ChIJ reroutes
    print(f"\n1. Rerouting {len(chi_reroutes)} ChIJ photos...")
    for i, reroute in enumerate(chi_reroutes, 1):
        cursor.execute("""
            UPDATE vibe_photos
            SET restaurant_id = ?
            WHERE id = ?
        """, (reroute['new_resto_id'], reroute['photo_id']))

        if i % 100 == 0:
            print(f"   Rerouted {i}/{len(chi_reroutes)}...")

    print(f"✓ Rerouted {len(chi_reroutes)} ChIJ photos")

    # Remove duplicates
    print(f"\n2. Removing {len(duplicates_to_remove)} duplicate database entries...")
    for i, dup in enumerate(duplicates_to_remove, 1):
        cursor.execute("DELETE FROM vibe_photos WHERE id = ?", (dup['photo_id'],))

        if i % 100 == 0:
            print(f"   Removed {i}/{len(duplicates_to_remove)}...")

    print(f"✓ Removed {len(duplicates_to_remove)} duplicate entries")

    conn.commit()

    # Final verification
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    cursor.execute("SELECT COUNT(*) FROM vibe_photos")
    final_count = cursor.fetchone()[0]
    print(f"Final photo entries: {final_count}")
    print(f"Expected: {expected_after_dedup}")
    print(f"Match: {'✓ YES' if final_count == expected_after_dedup else '✗ NO - SOMETHING WRONG'}")

    # Check for remaining duplicates
    cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT restaurant_id, local_filename, COUNT(*) as cnt
            FROM vibe_photos
            GROUP BY restaurant_id, local_filename
            HAVING cnt > 1
        )
    """)
    remaining_dups = cursor.fetchone()[0]
    print(f"Remaining duplicates: {remaining_dups}")

    # Show sample restaurants
    print("\nSample restaurant photo counts:")
    cursor.execute("""
        SELECT r.name, COUNT(vp.id) as photo_count
        FROM restaurants r
        LEFT JOIN vibe_photos vp ON r.id = vp.restaurant_id
        WHERE r.id IN (1, 3, 5, 47, 614, 618)
        GROUP BY r.id
        ORDER BY r.id
    """)
    for name, count in cursor.fetchall():
        print(f"  {name}: {count} photos")

    conn.close()

    print("\n" + "=" * 80)
    print("✓ COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    fix_all_photos()
