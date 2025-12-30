"""
VibeCheck Flask Application
============================
Main Flask backend for restaurant vibe search and visualization.
"""

import os
import sqlite3
from io import BytesIO
from pathlib import Path

try:
    import clip
except ImportError:
    import open_clip
    clip = None
import faiss
import numpy as np
import torch
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from PIL import Image
from sentence_transformers import SentenceTransformer

# ==============================================================================
# CONFIG
# ==============================================================================

# Get the app directory (where this file is located)
APP_DIR = Path(__file__).parent
# Data directory is one level up from app/
DATA_DIR = APP_DIR.parent / "data"

# Data file paths (NYC configuration)
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", APP_DIR.parent / "vibecheck_full_output"))
DB_PATH = Path(os.getenv("DB_PATH", APP_DIR.parent / "vibecheck_full_output" / "vibecheck.db"))
IMAGE_DIR = Path(os.getenv("IMAGE_DIR", APP_DIR.parent / "vibecheck_full_output" / "images_compressed"))
FAISS_PATH = Path(os.getenv("FAISS_PATH", OUTPUT_DIR / "vibecheck_index.faiss"))
META_PATH = Path(os.getenv("META_PATH", OUTPUT_DIR / "meta_ids.npy"))
VIBE_MAP_CSV = Path(os.getenv("VIBE_MAP_CSV", DATA_DIR / "vibe_map.csv"))

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ==============================================================================
# FLASK APP
# ==============================================================================

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
CORS(app)  # Enable CORS for React Native

# ==============================================================================
# LOAD MODELS (once at startup)
# ==============================================================================

print("Loading models...")
print(f"   Database: {DB_PATH}")
print(f"   FAISS index: {FAISS_PATH}")
print(f"   Images: {IMAGE_DIR}")

text_model = SentenceTransformer("all-MiniLM-L6-v2", device=DEVICE)
print("   ✅ Text model loaded")

# Load CLIP for image search
if clip is not None:
    clip_model, clip_preprocess = clip.load("ViT-B/32", device=DEVICE)
    USE_IMAGE_SEARCH = True
    print("   ✅ CLIP model loaded (image search enabled)")
else:
    clip_model, _, clip_preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')
    clip_model = clip_model.to(DEVICE)
    USE_IMAGE_SEARCH = True
    print("   ✅ OpenCLIP model loaded (image search enabled)")

# Load FAISS index (files are baked into Docker image)
if not FAISS_PATH.exists():
    raise RuntimeError(f"FAISS index missing at {FAISS_PATH}. Check deployment.")

if FAISS_PATH.stat().st_size < 1024:
    raise RuntimeError(f"FAISS index corrupted at {FAISS_PATH} (only {FAISS_PATH.stat().st_size} bytes)")

faiss_index = faiss.read_index(str(FAISS_PATH))
meta_ids = np.load(META_PATH)
print(f"✅ Models loaded. FAISS index has {len(meta_ids)} restaurants.")

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def encode_query(text=None, image_file=None):
    """Encode text and/or image query into combined embedding with cuisine and vibe weighting."""
    # Cuisine keywords to boost (3x weight - STRONG)
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

    # Vibe/atmosphere keywords to boost (2x weight - moderate)
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

    # Price keywords to boost (2x weight - moderate)
    PRICE_KEYWORDS = {
        'cheap', 'affordable', 'budget', 'inexpensive',
        'expensive', 'pricey', 'upscale', 'high-end',
        'value', 'deal', 'splurge', 'reasonable'
    }

    # Detect if query contains keywords and boost them
    boosted_text = text or ""
    if boosted_text:
        words = boosted_text.lower().split()
        cuisine_words = [w for w in words if w in CUISINE_KEYWORDS]
        vibe_words = [w for w in words if w in VIBE_KEYWORDS]
        price_words = [w for w in words if w in PRICE_KEYWORDS]

        if cuisine_words:
            # Repeat cuisine words 2 more times (3x total - STRONG boost)
            boosted_text = boosted_text + " " + " ".join(cuisine_words * 2)

        if vibe_words:
            # Repeat vibe words 1 more time (2x total - moderate boost)
            boosted_text = boosted_text + " " + " ".join(vibe_words)

        if price_words:
            # Repeat price words 1 more time (2x total - moderate boost)
            boosted_text = boosted_text + " " + " ".join(price_words)

    # Text embedding (384 dimensions)
    text_vec = text_model.encode(
        boosted_text, convert_to_numpy=True, normalize_embeddings=True
    ).astype("float32")

    # Image embedding (512 dimensions)
    if image_file and USE_IMAGE_SEARCH:
        try:
            img = Image.open(BytesIO(image_file)).convert("RGB")
            img_tensor = clip_preprocess(img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                img_vec = clip_model.encode_image(img_tensor)
            img_vec /= img_vec.norm(dim=-1, keepdim=True)
            img_vec = img_vec.cpu().numpy()[0]
        except Exception as e:
            print(f"Error processing image: {e}")
            img_vec = np.zeros(512, dtype=np.float32)
    else:
        img_vec = np.zeros(512, dtype=np.float32)

    # Combine: 384 text + 512 image = 896 dimensions
    combined = np.concatenate([text_vec, img_vec]).astype("float32")
    return combined[None, :]


def get_restaurant_details(restaurant_id, review_limit=10):
    """Get full restaurant details from database."""
    conn = get_db()
    cursor = conn.cursor()

    # Get basic info
    cursor.execute(
        """
        SELECT id, name, rating, address, reviews_count, place_id, neighborhood, price_level
        FROM restaurants
        WHERE id = ?
    """,
        (restaurant_id,),
    )

    row = cursor.fetchone()
    if not row:
        return None

    restaurant = dict(row)

    # Get all photos (prioritize vibe photos which are usually interior/atmosphere shots)
    cursor.execute(
        """
        SELECT local_filename, photo_url
        FROM vibe_photos
        WHERE restaurant_id = ?
        ORDER BY
            CASE WHEN local_filename LIKE '%_vibe_%' THEN 0 ELSE 1 END,
            CASE WHEN photo_url IS NOT NULL THEN 0 ELSE 1 END,
            id
    """,
        (restaurant_id,),
    )

    photos = cursor.fetchall()
    # Return all photos for gallery/carousel
    restaurant["photos"] = [
        {"filename": p["local_filename"], "url": p["photo_url"]}
        for p in photos
    ] if photos else []

    # Keep first photo for backwards compatibility
    photo = photos[0] if photos else None
    restaurant["image_filename"] = photo["local_filename"] if photo else None
    restaurant["photo_filename"] = photo["local_filename"] if photo else None  # Keep for web compatibility
    restaurant["photo_url"] = photo["photo_url"] if photo else None

    # Get vibes
    cursor.execute(
        """
        SELECT vibe_name, mention_count
        FROM vibe_analysis
        WHERE restaurant_id = ?
        ORDER BY mention_count DESC
        LIMIT 3
    """,
        (restaurant_id,),
    )

    vibes = cursor.fetchall()
    restaurant["vibes"] = [
        {"name": v["vibe_name"], "count": v["mention_count"]} for v in vibes
    ]

    # Get reviews (configurable limit)
    cursor.execute(
        """
        SELECT review_text, likes
        FROM reviews
        WHERE restaurant_id = ?
        ORDER BY likes DESC
        LIMIT ?
    """,
        (restaurant_id, review_limit),
    )

    reviews = cursor.fetchall()
    # Always return full review text
    restaurant["reviews"] = [
        {"text": r["review_text"], "likes": r["likes"]} for r in reviews
    ]

    conn.close()
    return restaurant


def get_all_restaurants_for_map():
    """Get all restaurants with coordinates for map visualization."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.id, r.name, r.rating, r.address, r.review_count,
               vm.x, vm.y, vm.cluster
        FROM restaurants r
        LEFT JOIN (
            SELECT id, name, x, y, cluster
            FROM vibe_map_data
        ) vm ON r.name = vm.name
        WHERE r.rating IS NOT NULL
    """)

    restaurants = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return restaurants


def import_vibe_map_to_db():
    """Import vibe_map.csv into database for easier querying."""
    import pandas as pd

    if not VIBE_MAP_CSV.exists():
        return

    conn = get_db()
    df = pd.read_csv(VIBE_MAP_CSV)
    df.to_sql("vibe_map_data", conn, if_exists="replace", index=False)
    conn.close()
    print("✅ Imported vibe_map.csv to database")


# ==============================================================================
# ROUTES
# ==============================================================================


@app.route("/")
def index():
    """Main page - NYC version."""
    return render_template("index_nyc.html")


@app.route("/dc")
def index_dc():
    """DC landing page (legacy)."""
    return render_template("index.html")


@app.route("/nyc")
def index_nyc():
    """NYC landing page with mobile app features."""
    return render_template("index_nyc.html")


@app.route("/restaurant/<int:restaurant_id>")
def restaurant_detail(restaurant_id):
    """Restaurant detail page."""
    details = get_restaurant_details(restaurant_id, review_limit=10)
    if details:
        return render_template("restaurant.html", restaurant=details)
    return "Restaurant not found", 404


@app.route("/api/search", methods=["POST"])
def search():
    """Search for restaurants by text and/or image."""
    try:
        # Support both JSON and form data
        if request.is_json:
            data = request.get_json()
            query_text = data.get("query", "")
            top_k = int(data.get("k", 20))
            query_image = None
            # Price filter: 1 = $, 2 = $$, 3 = $$$, 4 = $$$$
            price_filter = data.get("price_level")  # Can be single value or list
        else:
            query_text = request.form.get("text", "")
            query_image = request.files.get("image")
            top_k = int(request.form.get("top_k", 9))
            price_filter = request.form.get("price_level")

        if not query_text and not query_image:
            return jsonify({"error": "Please provide text or image query"}), 400

        # Extract neighborhood from query if present
        try:
            from neighborhood_mapping import normalize_neighborhood_query
        except ImportError:
            from app.neighborhood_mapping import normalize_neighborhood_query
        neighborhood_filter = normalize_neighborhood_query(query_text)

        # Read image file if provided
        image_bytes = query_image.read() if query_image else None

        # Encode query
        query_vec = encode_query(query_text, image_bytes)

        # Search FAISS index (get more results if filtering by neighborhood)
        search_k = top_k * 5 if neighborhood_filter else top_k
        distances, indices = faiss_index.search(query_vec, search_k)

        # Get restaurant details and filter by neighborhood and price if specified
        results = []
        for idx, distance in zip(indices[0], distances[0], strict=False):
            restaurant_id = int(meta_ids[idx])
            details = get_restaurant_details(restaurant_id)

            if details:
                # Filter by neighborhood if detected in query
                if neighborhood_filter:
                    if details.get("neighborhood") != neighborhood_filter:
                        continue

                # Filter by price level if specified
                if price_filter is not None:
                    restaurant_price = details.get("price_level")
                    # Handle both single value and list of values
                    if isinstance(price_filter, list):
                        if restaurant_price not in price_filter:
                            continue
                    else:
                        if restaurant_price != int(price_filter):
                            continue

                details["similarity_score"] = float(distance)
                results.append(details)

                # Stop once we have enough results
                if len(results) >= top_k:
                    break

        return jsonify({"results": results})

    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/restaurant/<int:restaurant_id>")
def get_restaurant(restaurant_id):
    """Get details for a specific restaurant."""
    details = get_restaurant_details(restaurant_id)
    if details:
        return jsonify(details)
    return jsonify({"error": "Restaurant not found"}), 404


@app.route("/api/map-data")
def map_data():
    """Get all restaurant data for map visualization."""
    try:
        restaurants = get_all_restaurants_for_map()
        return jsonify({"restaurants": restaurants})
    except Exception as e:
        print(f"Map data error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/vibe-stats")
@app.route("/api/top-vibes")
def vibe_stats():
    """Get overall vibe statistics with top restaurants for each vibe."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT vibe_name, SUM(mention_count) as total
        FROM vibe_analysis
        GROUP BY vibe_name
        ORDER BY total DESC
        LIMIT 20
    """)

    vibes = []
    for row in cursor.fetchall():
        vibe_name = row[0]
        total_count = row[1]

        # Get top 5 restaurants with this vibe
        cursor.execute("""
            SELECT r.id, r.name, r.rating, va.mention_count
            FROM vibe_analysis va
            JOIN restaurants r ON va.restaurant_id = r.id
            WHERE va.vibe_name = ?
            ORDER BY va.mention_count DESC, r.rating DESC
            LIMIT 5
        """, (vibe_name,))

        restaurants = [
            {
                "id": r[0],
                "name": r[1],
                "rating": r[2],
                "mention_count": r[3]
            }
            for r in cursor.fetchall()
        ]

        vibes.append({
            "name": vibe_name,
            "count": total_count,
            "restaurants": restaurants
        })

    conn.close()
    return jsonify({"vibes": vibes})


@app.route("/images/<path:filename>")
def serve_image(filename):
    """Serve restaurant images."""
    from flask import send_from_directory

    return send_from_directory(IMAGE_DIR, filename)


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    # Import vibe map data to database on startup
    import_vibe_map_to_db()

    # Get port from environment or use 8080 as default (5000 often used by AirPlay on macOS)
    port = int(os.getenv("FLASK_PORT", 8080))

    print("\n" + "=" * 60)
    print("🍽️  VIBECHECK FLASK APP STARTING")
    print("=" * 60)
    print(f"📊 Loaded {len(meta_ids)} restaurants")
    print(f"🌐 Server starting at http://localhost:{port}")
    print("=" * 60 + "\n")

    app.run(debug=True, host="0.0.0.0", port=port)
