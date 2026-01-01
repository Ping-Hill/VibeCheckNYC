"""
Sync database filenames to match the actual files in images_corect_order.
This updates the database to match the AI-classified and reordered files.
NO DELETIONS - only updates filenames in database.
"""
import sqlite3
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "vibecheck_full_output" / "vibecheck.db"
IMAGE_DIR = Path(__file__).parent.parent / "vibecheck_full_output" / "images_corect_order"

def normalize_name(name):
    """Normalize restaurant name to match filename pattern."""
    normalized = name.upper()
    normalized = normalized.replace("'", "").replace("&", "").replace(",", "")
    normalized = normalized.replace("-", "").replace(".", "").replace("|", "")
    normalized = normalized.replace("  ", " ").replace(" ", "_")
    normalized = normalized.strip("_")
    return normalized

def extract_place_id_from_filename(filename):
    """Extract Google Place ID from ChIJ filename."""
    if not filename.startswith('ChIJ'):
        return None
    # Keep everything before the last underscore
    return filename.rsplit('_', 1)[0]

def sync_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("SYNCING DATABASE TO MATCH FILES")
    print("=" * 80)

    # Get all restaurants
    cursor.execute("SELECT id, name, place_id FROM restaurants ORDER BY id")
    restaurants = cursor.fetchall()
    print(f"\nLoaded {len(restaurants)} restaurants")

    # Build lookup maps
    name_to_resto = {}  # normalized_name -> (id, name, place_id)
    place_id_to_resto = {}  # place_id -> (id, name, place_id)

    for resto_id, name, place_id in restaurants:
        normalized = normalize_name(name)
        name_to_resto[normalized] = (resto_id, name, place_id)
        place_id_to_resto[place_id] = (resto_id, name, place_id)

    # Get all files in the directory
    all_files = list(IMAGE_DIR.glob("*.jpg"))
    print(f"Found {len(all_files)} files in images_corect_order")

    # Group files by restaurant
    files_by_restaurant = defaultdict(list)

    for file_path in all_files:
        filename = file_path.name

        # Match to restaurant
        if filename.startswith('ChIJ'):
            # ChIJ photo - match by Place ID
            place_id = extract_place_id_from_filename(filename)
            if place_id in place_id_to_resto:
                resto_id, resto_name, _ = place_id_to_resto[place_id]
                files_by_restaurant[resto_id].append(filename)
        elif '_vibe_' in filename:
            # Vibe photo - match by restaurant name
            resto_part = filename.split('_vibe_')[0].upper()
            # Find best match
            best_match = None
            best_score = 0
            for norm_name, (rid, rname, rpid) in name_to_resto.items():
                if resto_part == norm_name:
                    best_match = (rid, rname)
                    break
                elif resto_part in norm_name or norm_name in resto_part:
                    score = min(len(resto_part), len(norm_name)) / max(len(resto_part), len(norm_name))
                    if score > best_score and score > 0.7:
                        best_score = score
                        best_match = (rid, rname)

            if best_match:
                files_by_restaurant[best_match[0]].append(filename)

    print(f"\nMatched files to {len(files_by_restaurant)} restaurants")

    # Now update database
    updates = []
    current_photos_map = {}  # (restaurant_id, order) -> photo_id

    # Get current database state
    cursor.execute("SELECT id, restaurant_id, local_filename FROM vibe_photos ORDER BY id")
    for photo_id, resto_id, filename in cursor.fetchall():
        if (resto_id, filename) not in current_photos_map:
            current_photos_map[(resto_id, filename)] = photo_id

    # For each restaurant, map new files
    total_updated = 0
    total_skipped = 0

    for resto_id in sorted(files_by_restaurant.keys()):
        files = sorted(files_by_restaurant[resto_id])

        # Get current photos for this restaurant from database
        cursor.execute("""
            SELECT id, local_filename
            FROM vibe_photos
            WHERE restaurant_id = ?
            ORDER BY id
        """, (resto_id,))

        current_photos = cursor.fetchall()

        if len(files) != len(current_photos):
            print(f"  Warning: Restaurant {resto_id} has {len(current_photos)} in DB but {len(files)} files")

        # Map files to photo IDs
        for i, (photo_id, old_filename) in enumerate(current_photos):
            if i < len(files):
                new_filename = files[i]
                if old_filename != new_filename:
                    updates.append((new_filename, photo_id))
                    total_updated += 1
            else:
                total_skipped += 1

    print(f"\n" + "=" * 80)
    print("APPLYING UPDATES")
    print("=" * 80)
    print(f"Total filename updates: {total_updated}")
    print(f"Photos skipped: {total_skipped}")

    # Apply updates
    for i, (new_filename, photo_id) in enumerate(updates, 1):
        cursor.execute("""
            UPDATE vibe_photos
            SET local_filename = ?
            WHERE id = ?
        """, (new_filename, photo_id))

        if i % 1000 == 0:
            print(f"  Updated {i}/{total_updated}...")

    conn.commit()
    conn.close()

    print(f"\n✅ Database sync complete!")
    print(f"Updated {total_updated} filenames")

if __name__ == "__main__":
    sync_database()
