"""
Analyze the vibe_photos table to find restaurants with cross-contaminated photos.
This script identifies:
1. ChIJ duplicate photos
2. Restaurants with photos from OTHER restaurants assigned to them
"""
import sqlite3
from pathlib import Path
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "vibecheck_full_output" / "vibecheck.db"

def normalize_restaurant_name(name):
    """Normalize restaurant name to match filename pattern."""
    # Remove common punctuation and convert to format used in filenames
    normalized = name.replace("'", "").replace("&", "").replace(",", "")
    normalized = normalized.replace(" ", "_")
    return normalized.upper()

def analyze_contamination():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all restaurants
    cursor.execute("SELECT id, name FROM restaurants ORDER BY id")
    restaurants = cursor.fetchall()

    print(f"Analyzing {len(restaurants)} restaurants...\n")

    contaminated_restaurants = []
    chi_duplicate_count = 0
    total_wrong_photos = 0

    for restaurant_id, restaurant_name in restaurants:
        # Get all photos for this restaurant
        cursor.execute("""
            SELECT local_filename
            FROM vibe_photos
            WHERE restaurant_id = ?
        """, (restaurant_id,))

        photos = [row[0] for row in cursor.fetchall() if row[0]]

        if not photos:
            continue

        # Categorize photos
        chi_photos = [p for p in photos if p and p.startswith('ChIJ')]
        vibe_photos = [p for p in photos if p and '_vibe_' in p]

        # Check for wrong restaurant photos
        normalized_name = normalize_restaurant_name(restaurant_name)

        wrong_photos = []
        correct_photos = []

        for photo in vibe_photos:
            # Extract restaurant name from filename (everything before _vibe_)
            if '_vibe_' in photo:
                photo_restaurant = photo.split('_vibe_')[0].upper()

                # Check if this photo belongs to this restaurant
                if photo_restaurant != normalized_name:
                    wrong_photos.append(photo)
                else:
                    correct_photos.append(photo)

        # Track ChIJ duplicates
        chi_duplicate_count += len(chi_photos)

        # If restaurant has wrong photos, record it
        if wrong_photos:
            total_wrong_photos += len(wrong_photos)
            contaminated_restaurants.append({
                'id': restaurant_id,
                'name': restaurant_name,
                'total_photos': len(photos),
                'correct_photos': len(correct_photos),
                'wrong_photos': len(wrong_photos),
                'chi_duplicates': len(chi_photos),
                'wrong_photo_list': wrong_photos,
                'correct_photo_list': correct_photos
            })

    conn.close()

    # Print summary
    print("=" * 80)
    print("PHOTO CONTAMINATION ANALYSIS REPORT")
    print("=" * 80)
    print(f"\nTotal ChIJ duplicate photos: {chi_duplicate_count:,}")
    print(f"Total restaurants with cross-contamination: {len(contaminated_restaurants)}")
    print(f"Total wrong photos assigned: {total_wrong_photos}")

    # Print detailed contamination report
    if contaminated_restaurants:
        print("\n" + "=" * 80)
        print("RESTAURANTS WITH CROSS-CONTAMINATED PHOTOS")
        print("=" * 80)

        # Sort by number of wrong photos (descending)
        contaminated_restaurants.sort(key=lambda x: x['wrong_photos'], reverse=True)

        for i, resto in enumerate(contaminated_restaurants[:50], 1):  # Show top 50
            print(f"\n{i}. {resto['name']} (ID: {resto['id']})")
            print(f"   Total photos: {resto['total_photos']}")
            print(f"   ✓ Correct photos: {resto['correct_photos']}")
            print(f"   ✗ Wrong photos: {resto['wrong_photos']}")
            print(f"   � ChIJ duplicates: {resto['chi_duplicates']}")

            if resto['wrong_photos'] <= 10:  # Show filenames if not too many
                print(f"   Wrong photos from other restaurants:")
                for photo in resto['wrong_photo_list']:
                    other_resto_name = photo.split('_vibe_')[0].replace('_', ' ')
                    print(f"      - {photo} (from: {other_resto_name})")

        if len(contaminated_restaurants) > 50:
            print(f"\n... and {len(contaminated_restaurants) - 50} more restaurants with contamination")

    # Print statistics
    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)
    wrong_photo_counts = defaultdict(int)
    for resto in contaminated_restaurants:
        wrong_photo_counts[resto['wrong_photos']] += 1

    print("\nDistribution of wrong photos per restaurant:")
    for count in sorted(wrong_photo_counts.keys()):
        num_restaurants = wrong_photo_counts[count]
        print(f"  {count} wrong photos: {num_restaurants} restaurants")

    print("\n" + "=" * 80)

    return contaminated_restaurants, chi_duplicate_count

if __name__ == "__main__":
    contaminated, chi_count = analyze_contamination()

    # Save detailed report to file
    report_path = Path(__file__).parent.parent / "vibecheck_full_output" / "contamination_report.txt"
    with open(report_path, 'w') as f:
        f.write("DETAILED PHOTO CONTAMINATION REPORT\n")
        f.write("=" * 80 + "\n\n")

        for resto in contaminated:
            f.write(f"Restaurant: {resto['name']} (ID: {resto['id']})\n")
            f.write(f"Total photos: {resto['total_photos']}\n")
            f.write(f"Correct photos: {resto['correct_photos']}\n")
            f.write(f"Wrong photos: {resto['wrong_photos']}\n")
            f.write(f"ChIJ duplicates: {resto['chi_duplicates']}\n")
            f.write(f"\nCorrect photos:\n")
            for photo in resto['correct_photo_list']:
                f.write(f"  ✓ {photo}\n")
            f.write(f"\nWrong photos (from other restaurants):\n")
            for photo in resto['wrong_photo_list']:
                f.write(f"  ✗ {photo}\n")
            f.write("\n" + "-" * 80 + "\n\n")

    print(f"\nDetailed report saved to: {report_path}")
