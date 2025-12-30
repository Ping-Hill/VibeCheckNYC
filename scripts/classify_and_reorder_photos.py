"""
Classify restaurant photos as interior/exterior vs food using AI vision model.
Then reorder photos in database so interior/exterior photos show first.
"""
import os
import sqlite3
from pathlib import Path
from transformers import pipeline
from PIL import Image

# Paths
DB_PATH = Path(__file__).parent.parent / "vibecheck_full_output" / "vibecheck.db"
IMAGE_DIR = Path(__file__).parent.parent / "vibecheck_full_output" / "images"

# Load CLIP vision model for zero-shot image classification
print("Loading vision model...")
classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")

def classify_photo(image_path):
    """
    Classify a photo as 'interior' (building/space), 'food', or 'people' (reject).
    Returns: 'interior', 'food', or 'people'
    """
    try:
        image = Image.open(image_path)

        # First check: Is this a people photo?
        people_labels = ["people portrait selfie group photo", "restaurant interior exterior building food"]
        people_results = classifier(image, candidate_labels=people_labels)

        if people_results[0]['label'].startswith('people') and people_results[0]['score'] > 0.65:
            print(f"  {image_path.name}: PEOPLE PHOTO - SKIP ({people_results[0]['score']:.2f})")
            return 'people'

        # Second check: Interior/exterior vs food
        labels = ["restaurant interior or exterior building", "food dish plate meal"]
        results = classifier(image, candidate_labels=labels)

        top_label = results[0]['label']
        score = results[0]['score']

        print(f"  {image_path.name}: {top_label} ({score:.2f})")

        # Map to simple category
        if "interior" in top_label or "exterior" in top_label:
            return 'interior'
        else:
            return 'food'
    except Exception as e:
        print(f"  Error classifying {image_path.name}: {e}")
        return 'unknown'

def reorder_photos(test_mode=True, test_limit=10):
    """
    Classify all vibe photos and reorder them so interior/exterior photos come first.

    Args:
        test_mode: If True, only process test_limit restaurants
        test_limit: Number of restaurants to process in test mode
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all restaurants
    cursor.execute("SELECT DISTINCT restaurant_id FROM vibe_photos WHERE local_filename LIKE '%_vibe_%'")
    restaurant_ids = [row[0] for row in cursor.fetchall()]

    if test_mode:
        restaurant_ids = restaurant_ids[:test_limit]
        print(f"\n🧪 TEST MODE: Processing {len(restaurant_ids)} restaurants...")
    else:
        print(f"\nProcessing {len(restaurant_ids)} restaurants...")

    for i, restaurant_id in enumerate(restaurant_ids, 1):
        print(f"\n[{i}/{len(restaurant_ids)}] Restaurant ID: {restaurant_id}")

        # Get all vibe photos for this restaurant
        cursor.execute("""
            SELECT id, local_filename, photo_url
            FROM vibe_photos
            WHERE restaurant_id = ? AND local_filename LIKE '%_vibe_%'
            ORDER BY id
        """, (restaurant_id,))

        photos = cursor.fetchall()
        if not photos:
            continue

        # Classify each photo
        classified_photos = []
        for photo_id, filename, photo_url in photos:
            image_path = IMAGE_DIR / filename

            if image_path.exists():
                category = classify_photo(image_path)
                classified_photos.append({
                    'id': photo_id,
                    'filename': filename,
                    'photo_url': photo_url,
                    'category': category
                })
            else:
                print(f"  Warning: {filename} not found, skipping")

        # Reorder: interior/exterior first, then food, skip people photos
        interior_photos = [p for p in classified_photos if p['category'] == 'interior']
        food_photos = [p for p in classified_photos if p['category'] == 'food']
        people_photos = [p for p in classified_photos if p['category'] == 'people']
        unknown_photos = [p for p in classified_photos if p['category'] == 'unknown']

        # Delete people photos from database
        for photo in people_photos:
            print(f"    Deleting people photo: {photo['filename']}")
            cursor.execute("DELETE FROM vibe_photos WHERE id = ?", (photo['id'],))

        reordered = interior_photos + food_photos + unknown_photos

        print(f"  Reordered: {len(interior_photos)} interior, {len(food_photos)} food, {len(people_photos)} people (deleted), {len(unknown_photos)} unknown")

        # Update database with new order by renaming files
        # We'll update the filenames to include a sort prefix
        for new_order, photo in enumerate(reordered, 1):
            # Extract base name without _vibe_X.jpg
            base_name = photo['filename'].rsplit('_vibe_', 1)[0]
            ext = photo['filename'].rsplit('.', 1)[-1]

            # Create new filename with correct order
            new_filename = f"{base_name}_vibe_{new_order}.{ext}"

            if new_filename != photo['filename']:
                print(f"    Renaming: {photo['filename']} -> {new_filename}")

                # Update database
                cursor.execute("""
                    UPDATE vibe_photos
                    SET local_filename = ?
                    WHERE id = ?
                """, (new_filename, photo['id']))

                # Rename physical file
                old_path = IMAGE_DIR / photo['filename']
                new_path = IMAGE_DIR / new_filename
                if old_path.exists():
                    old_path.rename(new_path)

    conn.commit()
    conn.close()
    print("\n✅ Photo reordering complete!")

if __name__ == "__main__":
    reorder_photos()
