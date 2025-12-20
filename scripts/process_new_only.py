#!/usr/bin/env python3
"""
Process ONLY the 708 NEW restaurants with SerpAPI
Does NOT touch the old 2,972 restaurants
"""

import json
import os
import time
import requests
from pathlib import Path
from serpapi import GoogleSearch

# ==============================================================================
# CONFIG
# ==============================================================================

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

OUTPUT_DIR = Path("./vibecheck_full_output")
IMAGE_DIR = OUTPUT_DIR / "images"
NEW_RESTAURANTS_FILE = OUTPUT_DIR / "new_restaurants_only.json"
CHECKPOINT_FILE = OUTPUT_DIR / "checkpoint.json"
RESULTS_FILE = OUTPUT_DIR / "vibecheck_results.json"

MIN_REVIEWS_NEEDED = 5
MIN_IMAGES_NEEDED = 5

# ==============================================================================
# SERPAPI FUNCTIONS
# ==============================================================================

def get_vibe_photos_and_reviews(place_id: str, name: str) -> dict:
    """Use SerpAPI to fetch vibe photos and reviews."""
    params = {
        "engine": "google_maps_reviews",
        "place_id": place_id,
        "api_key": SERPAPI_API_KEY,
        "hl": "en"
    }

    try:
        search = GoogleSearch(params)
        result = search.get_dict()

        reviews = result.get("reviews", [])

        photo_urls = []
        review_data = []

        for review in reviews[:MIN_REVIEWS_NEEDED]:
            text = review.get("snippet", "")
            if text:
                review_data.append({
                    "text": text,
                    "rating": review.get("rating", 0),
                    "date": review.get("date", ""),
                })

            images = review.get("images", [])
            for img in images:
                if isinstance(img, dict):
                    url = img.get("thumbnail")
                elif isinstance(img, str):
                    url = img
                else:
                    continue

                if url and url not in photo_urls:
                    photo_urls.append(url)
                    if len(photo_urls) >= MIN_IMAGES_NEEDED:
                        break

            if len(photo_urls) >= MIN_IMAGES_NEEDED:
                break

        return {
            "reviews": review_data,
            "photo_urls": photo_urls
        }

    except Exception as e:
        print(f"      ⚠️  SerpAPI error for {name}: {e}")
        return {"reviews": [], "photo_urls": []}

def download_image(url: str, filename: str) -> bool:
    """Download image from URL to file."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            filepath = IMAGE_DIR / filename
            with open(filepath, "wb") as f:
                f.write(response.content)
            return True
    except Exception:
        pass
    return False

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("\n" + "=" * 60)
    print("📸 PROCESS NEW RESTAURANTS ONLY")
    print("=" * 60)
    print("This will ONLY process the 708 NEW restaurants")
    print("Will NOT touch the old 2,972 restaurants")

    if not SERPAPI_API_KEY:
        print("\n❌ SERPAPI_API_KEY not set!")
        return

    # Load the 708 new restaurants
    if not NEW_RESTAURANTS_FILE.exists():
        print(f"\n❌ {NEW_RESTAURANTS_FILE} not found!")
        return

    with open(NEW_RESTAURANTS_FILE) as f:
        new_restaurants = json.load(f)

    print(f"\n✅ Loaded {len(new_restaurants)} NEW restaurants")

    # Load checkpoint
    processed = set()
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            checkpoint = json.load(f)
            processed = set(checkpoint.get("processed", []))
        print(f"✅ Loaded checkpoint: {len(processed)} already processed")

    # Load existing results
    results = []
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            results = json.load(f)
        print(f"✅ Loaded existing results: {len(results)} restaurants")

    # Filter: only process NEW restaurants that haven't been processed yet
    new_place_ids = set(r["place_id"] for r in new_restaurants)
    to_process = [r for r in new_restaurants if r["place_id"] not in processed]

    print(f"\n🎯 Will process: {len(to_process)} NEW restaurants")
    print(f"   Already done: {len(new_place_ids & processed)} NEW")
    print(f"   Total NEW: {len(new_restaurants)}")

    # Process
    for idx, restaurant in enumerate(to_process, 1):
        place_id = restaurant.get("place_id", "")
        name = restaurant.get("name", "Unknown")

        if not place_id:
            continue

        print(f"\n[{idx}/{len(to_process)}] 🍽️  {name}")
        rating = restaurant.get("rating", 0)
        reviews_count = restaurant.get("reviews_count", 0)
        print(f"   Rating: {rating} ⭐ ({reviews_count} reviews)")

        # Get vibe photos and reviews from SerpAPI
        print(f"   Fetching vibe photos and reviews...")
        vibe_data = get_vibe_photos_and_reviews(place_id, name)

        reviews = vibe_data["reviews"]
        photo_urls = vibe_data["photo_urls"]

        print(f"   Found: {len(reviews)} reviews, {len(photo_urls)} vibe photos")

        # Download images
        downloaded_files = []
        if photo_urls:
            print(f"   Downloading {len(photo_urls)} images...")
            for i, url in enumerate(photo_urls, 1):
                filename = f"{place_id}_{i}.jpg"
                if download_image(url, filename):
                    downloaded_files.append(filename)
            print(f"   ✅ Downloaded {len(downloaded_files)} images")

        # Build result entry
        result_entry = {
            "info": {
                "name": name,
                "place_id": place_id,
                "rating": restaurant.get("rating", 0),
                "reviews_count": restaurant.get("reviews_count", 0),
                "address": restaurant.get("address", ""),
                "phone": restaurant.get("phone", ""),
                "website": restaurant.get("website", ""),
                "category": restaurant.get("category", ""),
                "latitude": restaurant.get("latitude"),
                "longitude": restaurant.get("longitude"),
            },
            "reviews": reviews,
            "downloaded_files": downloaded_files,
        }

        results.append(result_entry)
        processed.add(place_id)

        # Save checkpoint every 10 restaurants
        if idx % 10 == 0:
            with open(RESULTS_FILE, "w") as f:
                json.dump(results, f, indent=2)
            with open(CHECKPOINT_FILE, "w") as f:
                json.dump({"processed": list(processed)}, f)
            print(f"   💾 Checkpoint saved ({len(processed)} total processed)")

        # Rate limiting
        time.sleep(2)

    # Final save
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"processed": list(processed)}, f)

    print("\n" + "=" * 60)
    print("✅ PROCESSING COMPLETE")
    print("=" * 60)
    print(f"🍽️  Total restaurants in results: {len(results)}")
    print(f"📝 Total reviews: {sum(len(r['reviews']) for r in results)}")
    print(f"📷 Total vibe photos: {sum(len(r['downloaded_files']) for r in results)}")
    print(f"\n💾 Saved to: {RESULTS_FILE}")
    print(f"\nNext: Load to database and generate embeddings")


if __name__ == "__main__":
    main()
