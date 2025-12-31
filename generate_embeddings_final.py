#!/usr/bin/env python3
"""
NYC VibeCheck Embeddings Generator - Text + Images
===================================================
Based on working DC code structure.
"""

import os
import sqlite3
import numpy as np
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import faiss
from pathlib import Path

# Try OpenAI CLIP first, fall back to open_clip
try:
    import clip
    USE_OPENAI_CLIP = True
except ImportError:
    import open_clip
    USE_OPENAI_CLIP = False

# ==============================================================================
# CONFIG
# ==============================================================================

OUTPUT_DIR = Path("./vibecheck_full_output")
DB_PATH = OUTPUT_DIR / "vibecheck.db"
IMAGE_DIR = OUTPUT_DIR / "images_compressed"  # Use compressed images
FAISS_PATH = OUTPUT_DIR / "vibecheck_index.faiss"
META_IDS_PATH = OUTPUT_DIR / "meta_ids.npy"
EMBEDDINGS_PATH = OUTPUT_DIR / "vibe_embeddings.npy"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_IMAGES_PER_RESTAURANT = 5

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("\n" + "=" * 60)
    print("🧠 NYC VIBECHECK EMBEDDINGS GENERATOR")
    print("=" * 60)
    print(f"Device: {DEVICE}")

    if not DB_PATH.exists():
        print(f"\n❌ Database not found: {DB_PATH}")
        return

    # Load models
    print("\n📦 Loading models...")
    print("   - SentenceTransformer for text...")
    text_model = SentenceTransformer("all-MiniLM-L6-v2", device=DEVICE)

    print("   - CLIP for images...")
    if USE_OPENAI_CLIP:
        clip_model, clip_preprocess = clip.load("ViT-B/32", device=DEVICE)
        print("     Using OpenAI CLIP")
    else:
        clip_model, _, clip_preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')
        clip_model = clip_model.to(DEVICE)
        print("     Using OpenCLIP")

    print("✅ Models loaded")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all restaurants
    print("\n📊 Loading restaurant data...")
    cursor.execute("SELECT id, name, place_id FROM restaurants")
    restaurants = cursor.fetchall()
    print(f"✅ Loaded {len(restaurants)} restaurants")

    # Generate embeddings
    embeddings = []
    meta_ids = []

    print("\n🔄 Generating embeddings...")
    for restaurant_id, name, place_id in tqdm(restaurants, desc="Processing"):

        # ============ TEXT EMBEDDING WITH CUISINE WEIGHTING ============
        cursor.execute("""
            SELECT review_text
            FROM reviews
            WHERE restaurant_id = ?
        """, (restaurant_id,))

        review_rows = cursor.fetchall()

        if review_rows:
            all_review_text = " ".join([r[0] for r in review_rows if r[0]])
            text_content = all_review_text
        else:
            text_content = name or ""

        # CUISINE keywords (3x boost - STRONG)
        CUISINE_KEYWORDS = {
            # Asian
            'chinese', 'japanese', 'korean', 'thai', 'vietnamese', 'indian',
            'filipino', 'indonesian', 'malaysian', 'burmese',
            # European
            'italian', 'french', 'spanish', 'greek', 'german', 'portuguese',
            'polish', 'russian',
            # Latin American
            'mexican', 'peruvian', 'brazilian', 'colombian', 'argentinian', 'cuban',
            # Middle Eastern / African
            'middle eastern', 'lebanese', 'turkish', 'moroccan', 'ethiopian', 'israeli',
            # Mediterranean
            'mediterranean',
            # Specific dishes/styles (very popular in NYC)
            'pizza', 'sushi', 'burger', 'bbq', 'steakhouse', 'seafood', 'ramen',
            'pho', 'tapas', 'dim sum', 'curry', 'pasta', 'noodles', 'dumplings',
            'bagels', 'deli', 'halal', 'soul food', 'cajun', 'creole',
            # Dietary
            'vegetarian', 'vegan'
        }

        # VIBE/ATMOSPHERE keywords (2x boost - moderate)
        VIBE_KEYWORDS = {
            # Romantic/Date
            'romantic', 'cozy', 'intimate', 'date', 'candlelit', 'ambiance', 'atmosphere',
            'date night',
            # Fancy/Casual
            'quiet', 'elegant', 'fancy', 'casual', 'fine dining',
            # Energy level
            'lively', 'energetic', 'relaxed', 'chill', 'vibey', 'loud', 'noisy',
            'buzzing', 'packed',
            # Style
            'trendy', 'hip', 'modern', 'rustic', 'charming', 'spacious',
            'bright', 'dark', 'dimly', 'instagram', 'instagrammable',
            # Outdoor/Seating
            'outdoor', 'patio', 'rooftop', 'garden', 'sidewalk', 'alfresco',
            'bar seating', 'counter seating',
            # Authenticity
            'fusion', 'authentic', 'traditional', 'homestyle', 'family-style',
            'hidden gem', 'local favorite', 'hole in the wall',
            # Group/Solo
            'group', 'solo', 'family', 'kids', 'friends',
            # Time/Speed
            'brunch', 'late night', 'quick', 'fast', 'happy hour'
        }

        # PRICE keywords (2x boost - moderate)
        PRICE_KEYWORDS = {
            'cheap', 'affordable', 'budget', 'inexpensive',
            'expensive', 'pricey', 'upscale', 'high-end',
            'value', 'deal', 'splurge', 'reasonable'
        }

        # MANHATTAN NEIGHBORHOOD keywords (2x boost - moderate)
        NEIGHBORHOOD_KEYWORDS = {
            # Manhattan ONLY
            'soho', 'tribeca', 'chinatown', 'financial district', 'fidi', 'battery park',
            'lower east side', 'les', 'east village', 'west village', 'greenwich village',
            'noho', 'nolita', 'bowery', 'chelsea', 'flatiron', 'gramercy', 'union square',
            'midtown', 'times square', 'hells kitchen', 'murray hill', 'kips bay',
            'upper east side', 'ues', 'upper west side', 'uws', 'morningside heights',
            'harlem', 'east harlem', 'washington heights', 'inwood',
            'manhattan', 'downtown', 'uptown'
        }

        # VENUE TYPE keywords (2x boost - moderate)
        VENUE_KEYWORDS = {
            'restaurant', 'bar', 'cafe', 'coffee shop', 'bakery', 'bistro', 'brasserie',
            'gastropub', 'pub', 'tavern', 'lounge', 'wine bar', 'cocktail bar',
            'speakeasy', 'dive bar', 'sports bar', 'brewery', 'food hall', 'food court',
            'diner', 'eatery', 'spot', 'joint', 'taqueria', 'pizzeria', 'trattoria',
            'osteria', 'ramen shop', 'noodle bar', 'sushi bar', 'izakaya', 'tapas bar',
            'steakhouse', 'grill', 'chophouse', 'seafood restaurant', 'oyster bar'
        }

        # Find keywords and boost them
        words_lower = text_content.lower().split()
        cuisine_words = [w for w in words_lower if w in CUISINE_KEYWORDS]
        vibe_words = [w for w in words_lower if w in VIBE_KEYWORDS]
        price_words = [w for w in words_lower if w in PRICE_KEYWORDS]
        neighborhood_words = [w for w in words_lower if w in NEIGHBORHOOD_KEYWORDS]
        venue_words = [w for w in words_lower if w in VENUE_KEYWORDS]

        # Also check for multi-word phrases
        text_lower = text_content.lower()
        for phrase in ['date night', 'fine dining', 'bar seating', 'counter seating',
                       'middle eastern', 'dim sum', 'soul food', 'coffee shop',
                       'financial district', 'lower east side', 'east village', 'west village',
                       'greenwich village', 'union square', 'times square', 'hells kitchen',
                       'upper east side', 'upper west side', 'morningside heights',
                       'east harlem', 'washington heights', 'battery park',
                       'hidden gem', 'local favorite', 'hole in the wall', 'happy hour',
                       'late night', 'family-style', 'wine bar', 'cocktail bar', 'dive bar',
                       'sports bar', 'food hall', 'food court', 'ramen shop', 'noodle bar',
                       'sushi bar', 'tapas bar', 'seafood restaurant', 'oyster bar']:
            if phrase in text_lower:
                if phrase in CUISINE_KEYWORDS:
                    cuisine_words.append(phrase)
                elif phrase in VIBE_KEYWORDS:
                    vibe_words.append(phrase)
                elif phrase in NEIGHBORHOOD_KEYWORDS:
                    neighborhood_words.append(phrase)
                elif phrase in VENUE_KEYWORDS:
                    venue_words.append(phrase)

        if cuisine_words:
            # Repeat cuisine words 2 more times (3x total - STRONG boost)
            text_content = text_content + " " + " ".join(cuisine_words * 2)

        if vibe_words:
            # Repeat vibe words 1 more time (2x total - moderate boost)
            text_content = text_content + " " + " ".join(vibe_words)

        if price_words:
            # Repeat price words 1 more time (2x total - moderate boost)
            text_content = text_content + " " + " ".join(price_words)

        if neighborhood_words:
            # Repeat neighborhood words 1 more time (2x total - moderate boost)
            text_content = text_content + " " + " ".join(neighborhood_words)

        if venue_words:
            # Repeat venue words 1 more time (2x total - moderate boost)
            text_content = text_content + " " + " ".join(venue_words)

        text_vec = text_model.encode(
            text_content,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        # ============ IMAGE EMBEDDING ============
        cursor.execute("""
            SELECT local_filename
            FROM vibe_photos
            WHERE restaurant_id = ? AND local_filename IS NOT NULL
            LIMIT ?
        """, (restaurant_id, MAX_IMAGES_PER_RESTAURANT))

        photo_rows = cursor.fetchall()

        if photo_rows:
            img_vecs = []

            for (filename,) in photo_rows:
                img_path = IMAGE_DIR / filename

                if img_path.exists():
                    try:
                        image = clip_preprocess(Image.open(img_path)).unsqueeze(0).to(DEVICE)
                        with torch.no_grad():
                            img_vec = clip_model.encode_image(image)
                        img_vec /= img_vec.norm(dim=-1, keepdim=True)
                        img_vec = img_vec.cpu().numpy()[0]
                        img_vecs.append(img_vec)
                    except Exception:
                        continue

            if img_vecs:
                img_vec = np.mean(img_vecs, axis=0).astype("float32")
                img_vec = img_vec / np.linalg.norm(img_vec)
            else:
                img_vec = np.zeros((512,), dtype="float32")
        else:
            img_vec = np.zeros((512,), dtype="float32")

        # ============ COMBINE EMBEDDINGS ============
        combined = np.concatenate([text_vec, img_vec]).astype("float32")
        embeddings.append(combined)
        meta_ids.append(restaurant_id)

    conn.close()

    # Stack embeddings
    embeddings = np.vstack(embeddings).astype("float32")
    print(f"\n✅ Generated {len(embeddings)} embeddings")
    print(f"   Dimension: {embeddings.shape[1]} (text: 384 + image: 512)")

    # Create FAISS index with IndexFlatIP (cosine similarity)
    print("\n🔍 Building FAISS index...")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # CRITICAL: Inner product for cosine similarity
    index.add(embeddings)

    # Save everything
    print("\n💾 Saving files...")
    faiss.write_index(index, str(FAISS_PATH))
    print(f"   ✅ FAISS index: {FAISS_PATH}")

    np.save(META_IDS_PATH, np.array(meta_ids))
    print(f"   ✅ Meta IDs: {META_IDS_PATH}")

    np.save(EMBEDDINGS_PATH, embeddings)
    print(f"   ✅ Embeddings: {EMBEDDINGS_PATH}")

    # Statistics
    cursor = sqlite3.connect(DB_PATH).cursor()
    cursor.execute("""
        SELECT COUNT(DISTINCT restaurant_id)
        FROM vibe_photos
        WHERE local_filename IS NOT NULL
    """)
    restaurants_with_images = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews")
    total_reviews = cursor.fetchone()[0]
    cursor.close()

    print("\n" + "=" * 60)
    print("📊 EMBEDDING STATISTICS")
    print("=" * 60)
    print(f"🍽️  Total restaurants: {len(meta_ids)}")
    print(f"📷 Restaurants with images: {restaurants_with_images}")
    print(f"📝 Total reviews processed: {total_reviews}")
    print(f"📐 Embedding dimension: {dim}")
    print(f"🔍 FAISS index type: IndexFlatIP (cosine similarity)")

    print("\n" + "=" * 60)
    print("✅ EMBEDDINGS GENERATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
