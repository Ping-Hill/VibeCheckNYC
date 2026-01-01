"""
Reroute ALL vibe photos to their correct restaurants based on filenames.
NO DELETIONS - only fixing restaurant_id assignments.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "vibecheck_full_output" / "vibecheck.db"

def normalize_name(name):
    """Normalize a name for comparison (remove special chars, spaces, etc)."""
    normalized = name.upper()
    normalized = normalized.replace("'", "").replace("&", "").replace(",", "")
    normalized = normalized.replace("-", "").replace(".", "").replace("|", "")
    normalized = normalized.replace("  ", " ").replace(" ", "_")
    normalized = normalized.strip("_")
    return normalized

def extract_restaurant_name_from_filename(filename):
    """Extract restaurant name from photo filename (everything before _vibe_)."""
    if '_vibe_' not in filename:
        return None
    name_part = filename.split('_vibe_')[0]
    return name_part.upper()

def find_best_matching_restaurant(photo_name, restaurants):
    """Find the best matching restaurant for a photo filename."""
    if not photo_name:
        return None, None, 0

    best_match = None
    best_score = 0

    for resto_id, resto_name in restaurants:
        normalized_resto = normalize_name(resto_name)

        # Exact match
        if normalized_resto == photo_name:
            return resto_id, resto_name, 100

        # Check if photo name is contained in restaurant name
        if photo_name in normalized_resto:
            score = (len(photo_name) / len(normalized_resto)) * 90
            if score > best_score:
                best_score = score
                best_match = (resto_id, resto_name)

        # Check if restaurant name is contained in photo name
        elif normalized_resto in photo_name:
            score = (len(normalized_resto) / len(photo_name)) * 85
            if score > best_score:
                best_score = score
                best_match = (resto_id, resto_name)

    if best_match and best_score > 70:
        return best_match[0], best_match[1], best_score

    return None, None, 0

def reroute_photos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("REROUTING ALL VIBE PHOTOS TO CORRECT RESTAURANTS")
    print("=" * 80)

    # Get all restaurants
    cursor.execute("SELECT id, name FROM restaurants ORDER BY id")
    restaurants = cursor.fetchall()
    print(f"\nLoaded {len(restaurants)} restaurants")

    # Get all vibe photos
    cursor.execute("""
        SELECT id, local_filename, restaurant_id
        FROM vibe_photos
        WHERE local_filename LIKE '%_vibe_%'
    """)
    vibe_photos = cursor.fetchall()
    print(f"Found {len(vibe_photos)} vibe photos to process")

    # Track statistics
    stats = {
        'correct': 0,
        'rerouted': 0,
        'no_match': 0,
        'low_confidence': 0
    }

    reroutes = []
    no_match_photos = []

    for photo_id, filename, current_resto_id in vibe_photos:
        # Extract restaurant name from filename
        photo_resto_name = extract_restaurant_name_from_filename(filename)

        if not photo_resto_name:
            stats['no_match'] += 1
            no_match_photos.append(filename)
            continue

        # Find the correct restaurant
        correct_id, correct_name, confidence = find_best_matching_restaurant(
            photo_resto_name, restaurants
        )

        if not correct_id:
            stats['no_match'] += 1
            no_match_photos.append(filename)
            continue

        if confidence < 80:
            stats['low_confidence'] += 1

        # Check if it's already assigned correctly
        if correct_id == current_resto_id:
            stats['correct'] += 1
        else:
            stats['rerouted'] += 1
            reroutes.append({
                'photo_id': photo_id,
                'filename': filename,
                'old_id': current_resto_id,
                'new_id': correct_id,
                'new_name': correct_name,
                'confidence': confidence
            })

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Already correct: {stats['correct']}")
    print(f"Need rerouting: {stats['rerouted']}")
    print(f"No match found: {stats['no_match']}")
    print(f"Low confidence: {stats['low_confidence']}")

    # Show sample of reroutes
    print("\nSample reroutes (first 20):")
    for reroute in reroutes[:20]:
        # Get old restaurant name
        cursor.execute("SELECT name FROM restaurants WHERE id = ?", (reroute['old_id'],))
        old_name_result = cursor.fetchone()
        old_name = old_name_result[0] if old_name_result else "Unknown"
        print(f"  {reroute['filename']}")
        print(f"    FROM: {old_name} (ID {reroute['old_id']})")
        print(f"    TO:   {reroute['new_name']} (ID {reroute['new_id']}) [{reroute['confidence']:.1f}%]")

    if len(reroutes) > 20:
        print(f"  ... and {len(reroutes) - 20} more reroutes")

    # Apply reroutes
    print("\n" + "=" * 80)
    print("APPLYING REROUTES (NO DELETIONS)")
    print("=" * 80)

    for i, reroute in enumerate(reroutes, 1):
        cursor.execute("""
            UPDATE vibe_photos
            SET restaurant_id = ?
            WHERE id = ?
        """, (reroute['new_id'], reroute['photo_id']))

        if i % 100 == 0:
            print(f"  Rerouted {i}/{len(reroutes)} photos...")

    conn.commit()
    print(f"✓ Rerouted {len(reroutes)} photos")

    # Final statistics
    cursor.execute("SELECT COUNT(*) FROM vibe_photos")
    final_count = cursor.fetchone()[0]

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Total photos (NO DELETIONS): {final_count}")
    print(f"Photos rerouted: {len(reroutes)}")
    print(f"Photos that couldn't be matched: {len(no_match_photos)}")

    conn.close()

    return stats, reroutes

if __name__ == "__main__":
    stats, reroutes = reroute_photos()
