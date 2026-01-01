"""
Classify restaurant photos as interior/exterior vs food using AI vision model.
Then reorder photos so interior/exterior photos show first.
DOES NOT TOUCH ROUTING - only reorders photos within each restaurant.
"""
import sqlite3
import json
from pathlib import Path
from transformers import pipeline
from PIL import Image

# Paths
DB_PATH = Path(__file__).parent.parent / "vibecheck_full_output" / "vibecheck.db"
IMAGE_DIR = Path(__file__).parent.parent / "vibecheck_full_output" / "images_compressed"
CHECKPOINT_FILE = Path(__file__).parent.parent / "vibecheck_full_output" / "classify_checkpoint.json"

# Load CLIP vision model for zero-shot image classification
print("Loading vision model...")
classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")

def classify_photo(image_path):
    """
    Classify a photo as 'interior' (building/space), 'food', or 'people'.
    Returns: 'interior', 'food', or 'people'
    """
    try:
        image = Image.open(image_path)

        # First check: Is this a people photo?
        people_labels = ["people portrait selfie group photo", "restaurant interior exterior building food"]
        people_results = classifier(image, candidate_labels=people_labels)

        if people_results[0]['label'].startswith('people') and people_results[0]['score'] > 0.65:
            return 'people'

        # Second check: Interior/exterior vs food
        labels = ["restaurant interior or exterior building atmosphere", "food dish plate meal"]
        results = classifier(image, candidate_labels=labels)

        top_label = results[0]['label']

        # Map to simple category
        if "interior" in top_label or "exterior" in top_label or "atmosphere" in top_label:
            return 'interior'
        else:
            return 'food'
    except Exception as e:
        print(f"  Error classifying {image_path.name}: {e}")
        return 'unknown'

def load_checkpoint():
    """Load processed restaurant IDs from checkpoint."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            return set(json.load(f).get('processed', []))
    return set()

def save_checkpoint(processed_ids):
    """Save processed restaurant IDs to checkpoint."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({'processed': list(processed_ids)}, f)

def reorder_photos():
    """
    Classify all photos and reorder them so interior/exterior photos come first.
    DOES NOT CHANGE restaurant_id - only reorders photos within each restaurant.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Load checkpoint
    processed_ids = load_checkpoint()
    print(f"Loaded checkpoint: {len(processed_ids)} restaurants already processed")

    # Get all restaurants that have photos
    cursor.execute("SELECT DISTINCT restaurant_id FROM vibe_photos ORDER BY restaurant_id")
    restaurant_ids = [row[0] for row in cursor.fetchall()]

    # Filter out already processed
    restaurant_ids = [rid for rid in restaurant_ids if rid not in processed_ids]

    print(f"\nProcessing {len(restaurant_ids)} restaurants...")
    print(f"Total to process including already done: {len(restaurant_ids) + len(processed_ids)}")

    for i, restaurant_id in enumerate(restaurant_ids, 1):
        print(f"\n[{i}/{len(restaurant_ids)}] Restaurant ID: {restaurant_id}")

        # Get ALL photos for this restaurant (both vibe and ChIJ)
        cursor.execute("""
            SELECT id, local_filename, photo_url, restaurant_id
            FROM vibe_photos
            WHERE restaurant_id = ?
            ORDER BY id
        """, (restaurant_id,))

        photos = cursor.fetchall()
        if not photos:
            continue

        # Classify each photo
        classified_photos = []
        for photo_id, filename, photo_url, resto_id in photos:
            if not filename:
                print(f"  Warning: Photo ID {photo_id} has no filename, skipping")
                continue

            image_path = IMAGE_DIR / filename

            if image_path.exists():
                category = classify_photo(image_path)
                classified_photos.append({
                    'id': photo_id,
                    'filename': filename,
                    'photo_url': photo_url,
                    'restaurant_id': resto_id,  # PRESERVE restaurant_id
                    'category': category
                })
                print(f"  {filename}: {category}")
            else:
                print(f"  Warning: {filename} not found in images_compressed, skipping")
                # Keep it but mark as unknown
                classified_photos.append({
                    'id': photo_id,
                    'filename': filename,
                    'photo_url': photo_url,
                    'restaurant_id': resto_id,
                    'category': 'unknown'
                })

        # Reorder: interior/exterior first, then food, then people, then unknown
        interior_photos = [p for p in classified_photos if p['category'] == 'interior']
        food_photos = [p for p in classified_photos if p['category'] == 'food']
        people_photos = [p for p in classified_photos if p['category'] == 'people']
        unknown_photos = [p for p in classified_photos if p['category'] == 'unknown']

        reordered = interior_photos + food_photos + people_photos + unknown_photos

        print(f"  Reordered: {len(interior_photos)} interior, {len(food_photos)} food, {len(people_photos)} people, {len(unknown_photos)} unknown")

        # Update database by renaming files to match new order
        for new_order, photo in enumerate(reordered, 1):
            old_filename = photo['filename']

            # Determine new filename based on type
            if old_filename.startswith('ChIJ'):
                # ChIJ photos: ChIJxxxxxx_1.jpg -> ChIJxxxxxx_<new_order>.jpg
                # Keep everything before the last underscore
                base_name = old_filename.rsplit('_', 1)[0]  # Everything before last _
                ext = old_filename.rsplit('.', 1)[-1]
                new_filename = f"{base_name}_{new_order}.{ext}"
            elif '_vibe_' in old_filename:
                # Vibe photos: Restaurant_vibe_1.jpg -> Restaurant_vibe_<new_order>.jpg
                base_name = old_filename.rsplit('_vibe_', 1)[0]
                ext = old_filename.rsplit('.', 1)[-1]
                new_filename = f"{base_name}_vibe_{new_order}.{ext}"
            else:
                # Unknown format, skip
                continue

            if new_filename != old_filename:
                print(f"    Renaming: {old_filename} -> {new_filename}")

                # Update database (PRESERVE restaurant_id)
                cursor.execute("""
                    UPDATE vibe_photos
                    SET local_filename = ?
                    WHERE id = ?
                """, (new_filename, photo['id']))

                # Rename physical file
                old_path = IMAGE_DIR / old_filename
                new_path = IMAGE_DIR / new_filename
                if old_path.exists():
                    old_path.rename(new_path)

        # Mark as processed and save checkpoint
        processed_ids.add(restaurant_id)
        save_checkpoint(processed_ids)

        # Commit after each restaurant
        conn.commit()

    conn.close()
    print("\n✅ Photo classification and reordering complete!")
    print(f"Total restaurants processed: {len(processed_ids)}")

if __name__ == "__main__":
    reorder_photos()
