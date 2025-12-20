# NYC VibeCheck - Complete Roadmap

## What You Have RIGHT NOW

### 📁 Main Codebase (this folder)
```
VibeCheck/
├── config.py                    ⚙️  THE CONTROL CENTER - edit this!
├── app/app.py                   🌐 Flask web app (your UI)
├── api/main.py                  🔌 FastAPI (REST endpoints)
├── src/vibecheck/              🧠 ML pipeline (CLIP, BERT, FAISS)
├── scripts/
│   ├── serpapi_full_scraper.py 📥 Gets restaurant data from Google Maps
│   └── load_sql.py             💾 Loads scraped data into SQLite
├── data/                        💾 CURRENT DC DATA (will replace with NYC)
│   ├── vibecheck.db            - 2,700 DC restaurants
│   ├── vibecheck_index.faiss   - Search index
│   ├── vibe_embeddings.npy     - ML embeddings
│   └── images/                 - Restaurant photos
└── vibecheck/                   🚀 DEPLOYED version (Fly.io) - IGNORE FOR NOW
```

### 🚀 /vibecheck/ Subdirectory
**What it is:** Your PRODUCTION deployment (separate git repo)
- Points to HuggingFace Spaces: https://huggingface.co/spaces/Ping8787/vibecheck
- Has its own app.py (copy of main one)
- Has its own data/ with DC restaurants
- **IGNORE THIS FOR NYC BUILD** - you'll update it later after NYC works locally

**Should you delete it?** NO - keep it for deployment reference, but work in the MAIN folder

---

## NYC Data Collection - FULL PIPELINE

### STEP 1: Configure for NYC (1 minute)

Open `config.py` and change ONE line:

```python
# Line 194 - Change this:
SEARCH_QUERIES = DC_SEARCH_QUERIES

# To this:
SEARCH_QUERIES = NYC_SEARCH_QUERIES
```

**What this does:** Tells the scraper to search 60+ NYC neighborhoods instead of DC

---

### STEP 2: Scrape NYC Restaurants (2-3 weeks)

**What you get:**
- ✅ Restaurant names
- ✅ Addresses & coordinates (latitude/longitude)
- ✅ Ratings & review counts
- ✅ 5+ interior/atmosphere photos per restaurant
- ✅ 5+ reviews per restaurant
- ✅ Vibe keywords extracted from reviews

**How to run:**

```bash
# Set your SerpAPI key
export SERPAPI_API_KEY= "9722d2d975a64646042893d23633775d21a5ec8a5f9e4e10fe1a99726f3f5305"

# Run the scraper
cd "/Users/iphone10/Desktop/VibeCheck copy"
python scripts/serpapi_full_scraper.py
```

**What happens:**
1. Searches 60+ NYC neighborhoods
2. Finds ~6,000-10,000 restaurants
3. For each restaurant:
   - Downloads 5+ vibe photos
   - Fetches 5+ reviews
   - Analyzes reviews for vibe keywords (cozy, romantic, loud, etc.)
4. Saves to `vibecheck_full_output/`
   - `vibecheck_results.json` - All restaurant data
   - `images/` - Downloaded photos
   - `checkpoint.json` - Resume state (if API quota runs out)

**SerpAPI Quota:**
- ~3 API calls per restaurant
- ~6,000 restaurants × 3 = ~18,000 calls
- Free tier: 100 calls/month
- Paid tier: $50/month = 5,000 calls (~3 months for full NYC)
- Pro tier: $150/month = 15,000 calls (~1 month for full NYC)

**Resume capability:**
If you run out of quota, just re-run the script - it picks up where it left off!

---

### STEP 3: Generate ML Embeddings (2-4 hours)

**What this does:**
- Converts restaurant photos → 512-dim vectors (CLIP)
- Converts reviews → 384-dim vectors (BERT)
- Combines into 896-dim embeddings
- Builds FAISS search index

**How to run:**

```bash
cd "/Users/iphone10/Desktop/VibeCheck copy"
python src/vibecheck/embeddings/generator.py
```

**GPU recommended:** 2-4 hours with GPU, 12+ hours CPU-only

**Output:**
- `data/embeddings.npy` - All restaurant embeddings
- `data/vibecheck_index.faiss` - Search index
- `data/meta_ids.npy` - Restaurant ID mapping

---

### STEP 4: Load into Database (10 minutes)

**What this does:**
- Parses `vibecheck_full_output/vibecheck_results.json`
- Creates SQLite database with:
  - restaurants (id, name, rating, address, coordinates)
  - vibe_photos (images)
  - vibe_analysis (vibe keywords)
  - reviews (review text)

**How to run:**

```bash
python scripts/load_sql.py
```

**Output:**
- `data/vibecheck.db` - SQLite database with all NYC data

---

### STEP 5: Generate Visualizations (15 minutes)

**What this does:**
- UMAP: Reduces 896-dim → 2D coordinates
- HDBSCAN: Discovers vibe clusters
- Creates map visualization data

**How to run:**

```bash
python src/vibecheck/analysis/vibe_mapper.py
```

**Output:**
- `data/vibe_map.csv` - 2D coordinates + cluster assignments

---

### STEP 6: Launch NYC VibeCheck! (1 minute)

**Run the app:**

```bash
python app/app.py
```

**Visit:** http://localhost:8080

**What you'll see:**
- Search by text: "cozy romantic dim lighting"
- Search by image: Upload reference photo
- Browse by vibe: "Romantic/Date Night"
- Map view: All NYC restaurants with coordinates
- UMAP view: 2D cluster visualization

---

## What Each File Does

### 🔧 config.py - THE CONTROL CENTER
**Purpose:** Single source of truth for everything

**Key settings:**
```python
# Search location (DC or NYC)
SEARCH_QUERIES = NYC_SEARCH_QUERIES  # ← CHANGE THIS

# Scraper requirements
MIN_REVIEWS_NEEDED = 5
MIN_IMAGES_NEEDED = 5

# Data paths
DATA_DIR = ROOT_DIR / "data"
SCRAPER_OUTPUT_DIR = ROOT_DIR / "vibecheck_full_output"
DB_PATH = DATA_DIR / "vibecheck.db"
```

---

### 📥 scripts/serpapi_full_scraper.py - DATA COLLECTOR
**Purpose:** Scrape restaurants from Google Maps

**What it does:**
1. Searches each neighborhood in `SEARCH_QUERIES`
2. For each restaurant:
   - Gets metadata (name, address, rating, coordinates)
   - Downloads 5+ interior photos
   - Fetches 5+ reviews
   - Analyzes reviews for vibe keywords
3. Saves everything to `vibecheck_full_output/`

**Key functions:**
- `search_restaurants_serpapi()` - Find restaurants
- `get_vibe_photos_serpapi()` - Download photos
- `get_reviews_serpapi()` - Fetch reviews
- `analyze_vibes()` - Extract vibe keywords

**Resume feature:** Uses `checkpoint.json` to resume on API quota exhaustion

---

### 🧠 src/vibecheck/embeddings/generator.py - ML EMBEDDINGS
**Purpose:** Convert photos + text into searchable vectors

**What it does:**
1. Loads restaurant photos from `vibecheck_full_output/images/`
2. Encodes each photo with CLIP → 512-dim vector
3. Encodes review text with BERT → 384-dim vector
4. Concatenates → 896-dim combined embedding
5. Builds FAISS index for similarity search

**Models used:**
- CLIP: OpenAI ViT-B/32 (image encoder)
- Sentence-BERT: all-MiniLM-L6-v2 (text encoder)

**Output files:**
- `data/embeddings.npy` - NumPy array (N × 896)
- `data/vibecheck_index.faiss` - FAISS search index
- `data/meta_ids.npy` - Restaurant IDs

---

### 💾 scripts/load_sql.py - DATABASE LOADER
**Purpose:** Import scraped data into SQLite

**What it does:**
1. Reads `vibecheck_full_output/vibecheck_results.json`
2. Creates SQLite tables:
   - `restaurants` (metadata)
   - `vibe_photos` (image paths)
   - `vibe_analysis` (vibe keywords)
   - `reviews` (review text)
3. Inserts all data

**Output:** `data/vibecheck.db` (SQLite database)

---

### 🌐 app/app.py - FLASK WEB APP (PRIMARY)
**Purpose:** Main web interface

**Features:**
- Search by text/image
- Restaurant detail pages
- Browse by vibe
- Geographic map (uses latitude/longitude)
- UMAP cluster visualization
- Serves images

**Endpoints:**
- `GET /` - Search interface
- `POST /api/search` - Search restaurants
- `GET /restaurant/<id>` - Detail page
- `GET /vibe/<name>` - Browse by vibe
- `GET /api/map-data` - Get coordinates for map
- `GET /api/umap-data` - Get UMAP visualization

**How it works:**
1. User searches: "cozy romantic dim lighting"
2. Encodes query with BERT+CLIP → 896-dim vector
3. FAISS finds k-nearest restaurants
4. Fetches details from SQLite
5. Returns ranked results

---

### 🔌 api/main.py - FASTAPI BACKEND
**Purpose:** REST API for integrations

**Endpoints:**
- `POST /search` - Search restaurants (JSON)
- `GET /restaurant/{id}` - Get details
- `GET /vibes` - List all vibes

**Use case:** If you want to build a mobile app or integrate with other services

---

### 📊 src/vibecheck/analysis/vibe_mapper.py - VISUALIZATIONS
**Purpose:** Create 2D map of restaurant embeddings

**What it does:**
1. Loads 896-dim embeddings
2. UMAP reduces to 2D (x, y coordinates)
3. HDBSCAN clusters into vibe groups
4. Saves coordinates + cluster labels

**Output:** `data/vibe_map.csv`
- Columns: id, name, x, y, cluster, top_vibe

**Use case:** Interactive scatter plot showing restaurant clusters by vibe

---

### 🎯 src/vibecheck/recommender.py - SEARCH ENGINE
**Purpose:** Core search logic

**Key methods:**
- `encode_query(text, image)` - Convert query to 896-dim vector
- `search(query_vec, k)` - FAISS similarity search
- `search_by_text()` - Text-only search
- `search_by_image()` - Image-only search
- `search_multimodal()` - Combined text+image

**How similarity works:**
```python
# FAISS returns L2 distances
distances, indices = faiss_index.search(query_vec, k)

# Convert to similarity score (0-1)
similarity = 1 / (1 + distance)
```

---

### 💾 src/vibecheck/database.py - DATABASE INTERFACE
**Purpose:** SQLite operations

**Key methods:**
- `get_restaurant_by_id()` - Fetch details
- `get_restaurants_by_vibe()` - Filter by vibe
- `get_all_coordinates()` - Map data
- `search_restaurants()` - Query wrapper

**Schema:**
```sql
restaurants: id, name, rating, address, latitude, longitude
vibe_photos: restaurant_id, local_filename, photo_url
vibe_analysis: restaurant_id, vibe_name, mention_count
reviews: restaurant_id, review_text, likes
```

---

## Do You Need the API?

**Short answer:** NO, not required

**Flask app (app/app.py):**
- ✅ Has search UI built-in
- ✅ Shows maps with coordinates
- ✅ Displays photos, reviews, vibes
- ✅ Everything you need to use VibeCheck

**FastAPI (api/main.py):**
- 📱 Only if you want to build integrations
- 📱 Only if you need pure JSON endpoints
- 📱 Optional for most use cases

**For NYC build:** Just use Flask app

---

## NYC Data Summary

When you complete the pipeline, you'll have:

### In `vibecheck_full_output/`:
- `vibecheck_results.json` - Raw scraped data
  - ~6,000-10,000 NYC restaurants
  - Names, addresses, coordinates
  - Ratings, review counts
  - Vibe keywords
- `images/` - 30,000-50,000 restaurant photos
- `checkpoint.json` - Resume state

### In `data/`:
- `vibecheck.db` - SQLite database
  - All restaurant metadata
  - Photos, reviews, vibes
  - Geographic coordinates (lat/lon)
- `vibecheck_index.faiss` - Search index
  - 6,000-10,000 restaurant embeddings
  - FAISS L2 index
- `embeddings.npy` - Raw embeddings (N × 896)
- `meta_ids.npy` - Restaurant ID mapping
- `vibe_map.csv` - UMAP coordinates
  - x, y positions for visualization
  - Cluster assignments
- `images/` - Symlink or copy of photos

---

## Timeline Estimate

| Step | Time | Bottleneck |
|------|------|------------|
| 1. Config change | 1 min | None |
| 2. Scraping | 2-3 weeks | SerpAPI quota |
| 3. Embeddings | 2-4 hrs | GPU access |
| 4. Database | 10 min | None |
| 5. Visualization | 15 min | None |
| 6. Launch app | 1 min | None |

**Total:** 2-3 weeks (mostly waiting on SerpAPI quota)

**Fast-track:** If you have SerpAPI Pro ($150/month), you can do it in 1-2 days

---

## Quick Start Commands

```bash
# 1. Configure for NYC
# Edit config.py line 194: SEARCH_QUERIES = NYC_SEARCH_QUERIES

# 2. Set API key
export SERPAPI_API_KEY="your_key_here"

# 3. Run pipeline
cd "/Users/iphone10/Desktop/VibeCheck copy"
python scripts/serpapi_full_scraper.py          # 2-3 weeks
python src/vibecheck/embeddings/generator.py    # 2-4 hours
python scripts/load_sql.py                      # 10 minutes
python src/vibecheck/analysis/vibe_mapper.py    # 15 minutes

# 4. Launch
python app/app.py
# Visit http://localhost:8080
```

---

## What About /vibecheck/?

**Leave it alone for now.**

It's your DEPLOYED production version (Fly.io/HuggingFace).

**After NYC works locally:**
1. Copy NYC data to `vibecheck/data/`
2. Deploy: `cd vibecheck && flyctl deploy`

**For now:** Work in the main folder, ignore vibecheck/ submodule

---

## Need Help?

- **System design:** Read [ARCHITECTURE.md](ARCHITECTURE.md)
- **Cleanup details:** Read [CLEANUP_SUMMARY.md](CLEANUP_SUMMARY.md)
- **Fast track:** Read [QUICK_START_NYC.md](QUICK_START_NYC.md)
- **Scraper issues:** Check `vibecheck_full_output/checkpoint.json`

---

**READY TO BUILD NYC VIBECHECK!** 🗽
