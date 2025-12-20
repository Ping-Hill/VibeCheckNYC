#!/usr/bin/env python3
"""
NYC Manhattan Hybrid Scraper - Comprehensive Coverage
======================================================
Uses OUTSCRAPER for restaurant discovery + SERPAPI for vibe photos
Based on working DC implementation.

This gets ~2,000-3,000+ Manhattan restaurants with full cuisine diversity.
"""

import json
import os
import time
import requests
from pathlib import Path
from typing import Optional
from outscraper import ApiClient
from serpapi import GoogleSearch

# ==============================================================================
# CONFIG
# ==============================================================================

# API Keys (set via environment variables)
OUTSCRAPER_API_KEY = os.getenv("OUTSCRAPER_API_KEY", "")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")

# Output directories
OUTPUT_DIR = Path("./vibecheck_full_output")
IMAGE_DIR = OUTPUT_DIR / "images"
CHECKPOINT_FILE = OUTPUT_DIR / "checkpoint.json"
RESTAURANTS_FILE = OUTPUT_DIR / "all_restaurants.json"
RESULTS_FILE = OUTPUT_DIR / "vibecheck_results.json"

# Scraping limits
MIN_REVIEWS_NEEDED = 5
MIN_IMAGES_NEEDED = 5

# Quality filters (set high to get only good restaurants)
MIN_RATING = 3.5
MIN_REVIEW_COUNT = 20

# Manhattan neighborhood search queries
MANHATTAN_QUERIES = [
    # Lower Manhattan
    "restaurants in SoHo Manhattan NYC",
    "restaurants in Tribeca NYC",
    "restaurants in NoHo NYC",
    "restaurants in Nolita NYC",
    "restaurants in Little Italy NYC",
    "restaurants in Chinatown Manhattan NYC",
    "restaurants in Lower East Side NYC",
    "restaurants in Financial District NYC",
    "restaurants in Battery Park NYC",

    # Greenwich Village area
    "restaurants in Greenwich Village NYC",
    "restaurants in West Village NYC",
    "restaurants in East Village NYC",

    # Midtown West
    "restaurants in Chelsea Manhattan NYC",
    "restaurants in Hell's Kitchen NYC",
    "restaurants in Hudson Yards NYC",
    "restaurants in Theater District NYC",
    "restaurants in Times Square NYC",

    # Midtown East
    "restaurants in Midtown Manhattan NYC",
    "restaurants in Murray Hill NYC",
    "restaurants in Gramercy Park NYC",
    "restaurants in Flatiron District NYC",
    "restaurants in Kips Bay NYC",
    "restaurants in Tudor City NYC",

    # Upper East Side
    "restaurants in Upper East Side NYC",
    "restaurants in Yorkville NYC",
    "restaurants in Carnegie Hill NYC",
    "restaurants in Lenox Hill NYC",

    # Upper West Side
    "restaurants in Upper West Side NYC",
    "restaurants in Lincoln Square NYC",
    "restaurants in Manhattan Valley NYC",

    # Harlem
    "restaurants in Harlem NYC",
    "restaurants in East Harlem NYC",
    "restaurants in West Harlem NYC",
    "restaurants in Hamilton Heights NYC",
    "restaurants in Morningside Heights NYC",

    # Upper Manhattan
    "restaurants in Washington Heights NYC",
    "restaurants in Inwood NYC",

    # Special districts
    "restaurants in Meatpacking District NYC",
    "restaurants in Union Square NYC",
    "restaurants in Madison Square NYC",
    "restaurants in Koreatown NYC",

    # Cuisine-specific searches for diversity
    "indian restaurants Manhattan NYC",
    "chinese restaurants Manhattan NYC",
    "japanese restaurants Manhattan NYC",
    "thai restaurants Manhattan NYC",
    "korean restaurants Manhattan NYC",
    "mexican restaurants Manhattan NYC",
    "french restaurants Manhattan NYC",
    "italian restaurants Manhattan NYC",
    "spanish restaurants Manhattan NYC",
    "mediterranean restaurants Manhattan NYC",
]

# ==============================================================================
# STEP 1: OUTSCRAPER - Restaurant Discovery
# ==============================================================================

def get_all_manhattan_restaurants(client: ApiClient, limit: int = 100) -> list[dict]:
    """
    Use Outscraper to discover ALL Manhattan restaurants.
    This is the comprehensive discovery phase.
    """
    print("\n" + "=" * 60)
    print("🔍 PHASE 1: OUTSCRAPER DISCOVERY")
    print("=" * 60)
    print(f"Searching {len(MANHATTAN_QUERIES)} queries...")

    all_restaurants = {}

    for i, query in enumerate(MANHATTAN_QUERIES, 1):
        print(f"\n[{i}/{len(MANHATTAN_QUERIES)}] {query}")

        try:
            results = client.google_maps_search(
                query,
                limit=limit,
                language="en",
                region="us"
            )

            # Process results
            count = 0
            for page in results:
                for place in page:
                    # Use place_id as unique identifier
                    place_id = place.get("place_id")
                    if not place_id:
                        continue

                    # Skip if already found
                    if place_id in all_restaurants:
                        continue

                    # Apply quality filters
                    rating = place.get("rating", 0)
                    review_count = place.get("reviews", 0)

                    if rating < MIN_RATING or review_count < MIN_REVIEW_COUNT:
                        continue

                    # Store restaurant
                    all_restaurants[place_id] = {
                        "place_id": place_id,
                        "name": place.get("name", "Unknown"),
                        "rating": rating,
                        "reviews_count": review_count,
                        "address": place.get("full_address", ""),
                        "phone": place.get("phone", ""),
                        "website": place.get("site", ""),
                        "category": place.get("category", ""),
                        "latitude": place.get("latitude"),
                        "longitude": place.get("longitude"),
                    }
                    count += 1

            print(f"   Found {count} new restaurants (Total unique: {len(all_restaurants)})")

            # Rate limiting
            time.sleep(1)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    restaurants_list = list(all_restaurants.values())

    print("\n" + "=" * 60)
    print(f"✅ DISCOVERY COMPLETE: {len(restaurants_list)} unique restaurants")
    print("=" * 60)

    return restaurants_list

# ==============================================================================
# STEP 2: SERPAPI - Vibe Photos & Reviews
# ==============================================================================

def get_vibe_photos_and_reviews(place_id: str, name: str) -> dict:
    """
    Use SerpAPI to fetch vibe photos and reviews for a restaurant.
    Returns dict with reviews and photo URLs.
    """
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

        # Extract photo URLs from reviews
        photo_urls = []
        review_data = []

        for review in reviews[:MIN_REVIEWS_NEEDED]:
            # Get review text
            text = review.get("snippet", "")
            if text:
                review_data.append({
                    "text": text,
                    "rating": review.get("rating", 0),
                    "date": review.get("date", ""),
                })

            # Get vibe photos from this review
            images = review.get("images", [])
            for img in images:
                # Handle both dict and string formats
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
# MAIN PIPELINE
# ==============================================================================

def load_checkpoint() -> set:
    """Load checkpoint of processed restaurant IDs."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
            return set(data.get("processed", []))
    return set()

def save_checkpoint(processed: set):
    """Save checkpoint."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"processed": list(processed)}, f)

def main():
    print("\n" + "=" * 60)
    print("🗽 NYC MANHATTAN HYBRID SCRAPER")
    print("=" * 60)
    print("Strategy: Outscraper discovery + SerpAPI vibe photos")
    print(f"Quality threshold: ≥{MIN_RATING} stars, ≥{MIN_REVIEW_COUNT} reviews")

    # Check API keys
    if not OUTSCRAPER_API_KEY:
        print("\n❌ OUTSCRAPER_API_KEY not set!")
        print("   Get key from: https://outscraper.com/")
        print("   Then: export OUTSCRAPER_API_KEY='your_key_here'")
        return

    if not SERPAPI_API_KEY:
        print("\n❌ SERPAPI_API_KEY not set!")
        print("   Get key from: https://serpapi.com/")
        print("   Then: export SERPAPI_API_KEY='your_key_here'")
        return

    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    # PHASE 1: Outscraper Discovery
    print("\n🔍 Initializing Outscraper client...")
    outscraper_client = ApiClient(api_key=OUTSCRAPER_API_KEY)

    # Check if we already have restaurants list
    if RESTAURANTS_FILE.exists():
        print(f"\n📂 Loading existing restaurants from {RESTAURANTS_FILE}")
        with open(RESTAURANTS_FILE) as f:
            all_restaurants = json.load(f)
        print(f"✅ Loaded {len(all_restaurants)} restaurants")
    else:
        all_restaurants = get_all_manhattan_restaurants(outscraper_client)

        # Save restaurant list
        with open(RESTAURANTS_FILE, "w") as f:
            json.dump(all_restaurants, f, indent=2)
        print(f"\n💾 Saved restaurant list to {RESTAURANTS_FILE}")

    # PHASE 2: SerpAPI vibe photos & reviews
    print("\n" + "=" * 60)
    print("📸 PHASE 2: SERPAPI VIBE PHOTOS & REVIEWS")
    print("=" * 60)

    processed = load_checkpoint()
    results = []

    # Load existing results if any
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            results = json.load(f)

    for idx, restaurant in enumerate(all_restaurants, 1):
        place_id = restaurant.get("place_id", "")
        name = restaurant.get("name", "Unknown")

        if not place_id:
            continue

        # Skip if already processed
        if place_id in processed:
            print(f"[{idx}/{len(all_restaurants)}] ⏭️  {name} (already processed)")
            continue

        print(f"\n[{idx}/{len(all_restaurants)}] 🍽️  {name}")
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
            save_checkpoint(processed)
            print(f"   💾 Checkpoint saved ({len(processed)}/{len(all_restaurants)})")

        # Rate limiting
        time.sleep(2)

    # Final save
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    save_checkpoint(processed)

    print("\n" + "=" * 60)
    print("✅ SCRAPING COMPLETE")
    print("=" * 60)
    print(f"🍽️  Total restaurants: {len(results)}")
    print(f"📝 Total reviews: {sum(len(r['reviews']) for r in results)}")
    print(f"📷 Total vibe photos: {sum(len(r['downloaded_files']) for r in results)}")
    print(f"\n💾 Saved to: {RESULTS_FILE}")
    print(f"\nNext step: python generate_nyc_embeddings.py")


if __name__ == "__main__":
    main()
