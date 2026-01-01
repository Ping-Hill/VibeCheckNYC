"""
Fix photo assignments by matching photo filenames to correct restaurant names.
This will:
1. Find the correct restaurant for each photo based on its filename
2. Update the restaurant_id to point to the correct restaurant
3. Delete ChIJ duplicate photos
"""
import sqlite3
from pathlib import Path
import re

DB_PATH = Path(__file__).parent.parent / "vibecheck_full_output" / "vibecheck.db"

def normalize_name(name):
    """Normalize a name for comparison (remove special chars, spaces, etc)."""
    normalized = name.upper()
    normalized = normalized.replace("'", "").replace("&", "").replace(",", "")
    normalized = normalized.replace("-", "").replace(".", "").replace("|", "")
    normalized = normalized.replace("  ", " ").replace(" ", "_")
    # Remove trailing underscores
    normalized = normalized.strip("_")
    return normalized

def extract_restaurant_name_from_filename(filename):
    """Extract restaurant name from photo filename (everything before _vibe_)."""
    if '_vibe_' not in filename:
        return None

    # Get the part before _vibe_
    name_part = filename.split('_vibe_')[0]
    return name_part.upper()

def find_best_matching_restaurant(photo_name, restaurants):
    """
    Find the best matching restaurant for a photo filename.
    Returns (restaurant_id, restaurant_name, confidence_score).
    """
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

    if best_match and best_score > 70:  # Only return if confidence is high
        return best_match[0], best_match[1], best_score

    return None, None, 0

def fix_photo_assignments():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("FIXING PHOTO ASSIGNMENTS")
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
        'fixed': 0,
        'no_match': 0,
        'low_confidence': 0
    }

    fixes = []
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
            print(f"  Low confidence match ({confidence:.1f}%): {filename} -> {correct_name}")

        # Check if it's already assigned correctly
        if correct_id == current_resto_id:
            stats['correct'] += 1
        else:
            stats['fixed'] += 1
            fixes.append({
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
    print(f"Need fixing: {stats['fixed']}")
    print(f"No match found: {stats['no_match']}")
    print(f"Low confidence: {stats['low_confidence']}")

    if no_match_photos:
        print(f"\nSample photos with no match:")
        for photo in no_match_photos[:10]:
            print(f"  - {photo}")

    # Ask for confirmation
    print("\n" + "=" * 80)
    print(f"Ready to fix {stats['fixed']} photo assignments")
    print("=" * 80)

    # Show sample of fixes
    print("\nSample fixes (first 20):")
    for fix in fixes[:20]:
        # Get old restaurant name
        cursor.execute("SELECT name FROM restaurants WHERE id = ?", (fix['old_id'],))
        old_name = cursor.fetchone()[0]
        print(f"  {fix['filename']}")
        print(f"    FROM: {old_name} (ID {fix['old_id']})")
        print(f"    TO:   {fix['new_name']} (ID {fix['new_id']}) [{fix['confidence']:.1f}% confidence]")

    if len(fixes) > 20:
        print(f"  ... and {len(fixes) - 20} more fixes")

    # Apply fixes
    print("\n" + "=" * 80)
    print("APPLYING FIXES")
    print("=" * 80)

    for i, fix in enumerate(fixes, 1):
        cursor.execute("""
            UPDATE vibe_photos
            SET restaurant_id = ?
            WHERE id = ?
        """, (fix['new_id'], fix['photo_id']))

        if i % 100 == 0:
            print(f"  Fixed {i}/{len(fixes)} photos...")

    conn.commit()
    print(f"✓ Fixed {len(fixes)} photo assignments")

    # Now delete ChIJ duplicates
    print("\n" + "=" * 80)
    print("DELETING ChIJ DUPLICATE PHOTOS")
    print("=" * 80)

    cursor.execute("SELECT COUNT(*) FROM vibe_photos WHERE local_filename LIKE 'ChIJ%'")
    chi_count = cursor.fetchone()[0]
    print(f"Found {chi_count} ChIJ duplicate photos to delete")

    cursor.execute("DELETE FROM vibe_photos WHERE local_filename LIKE 'ChIJ%'")
    conn.commit()
    print(f"✓ Deleted {chi_count} ChIJ duplicate photos")

    # Final statistics
    cursor.execute("SELECT COUNT(*) FROM vibe_photos")
    final_count = cursor.fetchone()[0]

    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Total photos remaining: {final_count}")
    print(f"Photos reassigned: {len(fixes)}")
    print(f"ChIJ duplicates deleted: {chi_count}")

    # Verify: check how many restaurants still have wrong photos
    cursor.execute("""
        SELECT r.id, r.name, vp.local_filename
        FROM restaurants r
        JOIN vibe_photos vp ON r.id = vp.restaurant_id
        WHERE vp.local_filename LIKE '%_vibe_%'
    """)

    all_assignments = cursor.fetchall()
    wrong_assignments = 0

    for resto_id, resto_name, filename in all_assignments:
        photo_name = extract_restaurant_name_from_filename(filename)
        if photo_name:
            normalized_resto = normalize_name(resto_name)
            if photo_name not in normalized_resto and normalized_resto not in photo_name:
                wrong_assignments += 1

    print(f"Remaining mismatches: {wrong_assignments}")

    conn.close()

    return stats, fixes

if __name__ == "__main__":
    stats, fixes = fix_photo_assignments()
