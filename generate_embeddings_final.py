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
IMAGE_DIR = OUTPUT_DIR / "images"
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

        # Boost cuisine keywords by repeating them 3x
        CUISINE_KEYWORDS = {
            'indian', 'italian', 'french', 'chinese', 'japanese', 'mexican', 'thai', 'korean',
            'vietnamese', 'mediterranean', 'greek', 'spanish', 'american', 'pizza', 'sushi',
            'burger', 'bbq', 'steakhouse', 'seafood', 'vegetarian', 'vegan', 'ramen', 'pho'
        }

        # Find cuisine words in text and boost them
        words_lower = text_content.lower().split()
        cuisine_words = [w for w in words_lower if w in CUISINE_KEYWORDS]
        if cuisine_words:
            # Repeat cuisine words 2 more times (3x total)
            text_content = text_content + " " + " ".join(cuisine_words * 2)

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
