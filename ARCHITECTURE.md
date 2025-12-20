# VibeCheck Architecture Documentation

## Overview

VibeCheck is a multimodal restaurant recommendation system that searches by ambience/vibe instead of traditional filters.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                        │
│  Flask Web App (app/app.py) or FastAPI (api/main.py)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   RECOMMENDATION ENGINE                      │
│              (src/vibecheck/recommender.py)                 │
│                                                              │
│  • encode_query() - Converts text/image to 896-dim vector   │
│  • search() - FAISS similarity search                       │
│  • get_recommendations() - Fetch & rank results             │
└──────────────┬────────────────────┬─────────────────────────┘
               │                    │
               ▼                    ▼
┌──────────────────────┐  ┌────────────────────────┐
│  EMBEDDING MODELS     │  │   VECTOR INDEX         │
│  (models.py)          │  │   (FAISS)              │
│                       │  │                        │
│  • CLIP (ViT-B/32)   │  │  • IndexFlatL2         │
│    512-dim image     │  │  • L2 distance search  │
│  • Sentence-BERT     │  │  • ~2700 restaurants   │
│    384-dim text      │  │                        │
│  • Combined: 896-dim │  │  data/                 │
│                       │  │  vibecheck_index.faiss │
└──────────────────────┘  └─────────┬──────────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │   DATABASE        │
                          │   (SQLite)        │
                          │                   │
                          │  • restaurants    │
                          │  • vibe_photos    │
                          │  • vibe_analysis  │
                          │  • reviews        │
                          │  • vibe_map_data  │
                          │                   │
                          │  data/            │
                          │  vibecheck.db     │
                          └───────────────────┘
```

## Data Flow

### Search Query Flow

```
1. USER INPUT
   └─> Text: "cozy romantic dim lighting"
   └─> Image: [uploaded photo]

2. ENCODING (src/vibecheck/recommender.py)
   ├─> Text Encoder (Sentence-BERT)
   │   └─> 384-dimensional vector
   ├─> Image Encoder (CLIP)
   │   └─> 512-dimensional vector
   └─> Concatenate
       └─> 896-dimensional query vector

3. SEARCH (FAISS)
   ├─> Compute L2 distances to all restaurants
   ├─> Return top-k nearest neighbors
   └─> Convert distance to similarity score: 1/(1+distance)

4. ENRICHMENT (database.py)
   ├─> Fetch restaurant metadata from SQLite
   ├─> Add photos, reviews, vibes
   └─> Return ranked results

5. DISPLAY
   └─> Render results in web interface
```

### Data Preparation Flow

```
1. DATA COLLECTION
   Script: scripts/serpapi_full_scraper.py
   └─> SerpAPI Google Maps queries
       ├─> Restaurant metadata (name, address, rating)
       ├─> Vibe photos (interior/atmosphere)
       └─> Reviews (for vibe analysis)
   └─> Output: vibecheck_full_output/

2. EMBEDDING GENERATION
   Script: src/vibecheck/embeddings/generator.py
   ├─> Load restaurant photos
   ├─> Encode with CLIP → 512-dim vectors
   ├─> Encode reviews with BERT → 384-dim vectors
   ├─> Concatenate → 896-dim embeddings
   └─> Save: data/embeddings.npy

3. INDEX BUILDING
   Script: src/vibecheck/embeddings/generator.py
   ├─> Load embeddings
   ├─> Create FAISS index (IndexFlatL2)
   ├─> Add all restaurant vectors
   └─> Save: data/vibecheck_index.faiss

4. DATABASE LOADING
   Script: scripts/load_sql.py
   ├─> Parse scraped JSON data
   ├─> Create SQLite tables
   ├─> Insert restaurants, photos, reviews, vibes
   └─> Save: data/vibecheck.db

5. VISUALIZATION (Optional)
   Script: src/vibecheck/analysis/vibe_mapper.py
   ├─> Load 896-dim embeddings
   ├─> UMAP reduction → 2D coordinates
   ├─> HDBSCAN clustering → vibe groups
   └─> Save: data/vibe_map.csv
```

## Directory Structure

```
VibeCheck/
├── config.py                      # ⚙️  Centralized configuration
│
├── app/                           # 🌐 Flask Web Application
│   ├── app.py                    # Main server (PRIMARY)
│   ├── templates/                # HTML templates
│   └── static/                   # CSS, JS, assets
│
├── api/                          # 🔌 FastAPI Backend
│   └── main.py                   # REST API endpoints
│
├── src/vibecheck/               # 🧠 Core ML Pipeline
│   ├── embeddings/
│   │   ├── generator.py         # Generate embeddings
│   │   └── models.py            # Model loading/caching
│   ├── analysis/
│   │   └── vibe_mapper.py       # UMAP + HDBSCAN clustering
│   ├── recommender.py           # Search engine
│   ├── database.py              # SQLite interface
│   └── monitoring/
│       └── evidently_monitor.py # Model monitoring
│
├── scripts/                      # 🛠️  Utilities
│   ├── serpapi_full_scraper.py  # Data collection
│   └── load_sql.py              # Database import
│
├── data/                        # 💾 Data Files (gitignored)
│   ├── vibecheck.db            # SQLite database
│   ├── vibecheck_index.faiss   # FAISS index
│   ├── embeddings.npy          # Pre-computed vectors
│   ├── meta_ids.npy            # ID mapping
│   ├── vibe_map.csv            # UMAP coordinates
│   └── images/                 # Restaurant photos
│
├── vibecheck_full_output/       # 📥 Scraper Output (gitignored)
│   ├── checkpoint.json         # Resume state
│   ├── vibecheck_results.json  # Scraped data
│   └── images/                 # Downloaded photos
│
└── vibecheck/                   # 🚀 Deployment Submodule (Fly.io)
```

## Key Components

### 1. Configuration ([config.py](config.py))

**Purpose:** Single source of truth for all paths and settings

**Key Exports:**
- `DATA_DIR`, `SCRAPER_OUTPUT_DIR` - Directory paths
- `DB_PATH`, `FAISS_INDEX_PATH` - Data file locations
- `SEARCH_QUERIES` - City-specific search queries (DC/NYC)
- `TEXT_MODEL`, `CLIP_MODEL` - Model identifiers
- `MIN_REVIEWS_NEEDED`, `MIN_IMAGES_NEEDED` - Scraper requirements

**Usage:**
```python
from config import DATA_DIR, SEARCH_QUERIES, DEVICE
```

### 2. Scraper ([scripts/serpapi_full_scraper.py](scripts/serpapi_full_scraper.py))

**Purpose:** Collect restaurant data from Google Maps via SerpAPI

**Process:**
1. Search by neighborhood (queries from `config.SEARCH_QUERIES`)
2. For each restaurant:
   - Get place details (name, address, rating, coordinates)
   - Download 5+ vibe photos (interior category)
   - Fetch 5+ reviews
   - Analyze reviews for vibe keywords
3. Save to `vibecheck_full_output/`
4. Checkpoint system allows resume on API quota exhaustion

**Key Functions:**
- `search_restaurants_serpapi()` - Discover restaurants
- `get_vibe_photos_serpapi()` - Download ambience photos
- `get_reviews_serpapi()` - Fetch reviews
- `analyze_vibes()` - Extract vibe keywords from reviews

### 3. Embedding Generator ([src/vibecheck/embeddings/generator.py](src/vibecheck/embeddings/generator.py))

**Purpose:** Convert restaurant photos and reviews into dense vectors

**Process:**
1. Load restaurant data from scraper output
2. Encode photos with CLIP (ViT-B/32) → 512-dim
3. Encode text with Sentence-BERT → 384-dim
4. Concatenate → 896-dim combined embedding
5. Build FAISS index for similarity search
6. Save embeddings and index

**Output Files:**
- `data/embeddings.npy` - NumPy array of shape (N, 896)
- `data/vibecheck_index.faiss` - FAISS index
- `data/meta_ids.npy` - Restaurant ID mapping

### 4. Recommender ([src/vibecheck/recommender.py](src/vibecheck/recommender.py))

**Purpose:** Core search engine for finding similar restaurants

**Key Methods:**
- `encode_query(text, image)` - Convert query to 896-dim vector
- `search(query_vec, top_k)` - FAISS similarity search
- `search_by_text(text, top_k)` - Text-only search
- `search_by_image(image, top_k)` - Image-only search
- `search_multimodal(text, image, top_k)` - Combined search

**Similarity Scoring:**
```python
# FAISS returns L2 distances
distance = faiss_index.search(query_vector, k)

# Convert to similarity score (0-1 range)
similarity = 1 / (1 + distance)
```

### 5. Database ([src/vibecheck/database.py](src/vibecheck/database.py))

**Purpose:** SQLite interface for restaurant metadata

**Schema:**

```sql
restaurants (
  id INTEGER PRIMARY KEY,
  name TEXT,
  rating REAL,
  address TEXT,
  reviews_count INTEGER,
  place_id TEXT,
  latitude REAL,
  longitude REAL
)

vibe_photos (
  id INTEGER PRIMARY KEY,
  restaurant_id INTEGER,
  local_filename TEXT,
  photo_url TEXT,
  FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
)

vibe_analysis (
  id INTEGER PRIMARY KEY,
  restaurant_id INTEGER,
  vibe_name TEXT,
  mention_count INTEGER,
  FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
)

reviews (
  id INTEGER PRIMARY KEY,
  restaurant_id INTEGER,
  review_text TEXT,
  rating REAL,
  likes INTEGER,
  FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
)

vibe_map_data (
  id INTEGER,
  name TEXT,
  rating REAL,
  address TEXT,
  review_count INTEGER,
  x REAL,  -- UMAP x-coordinate
  y REAL,  -- UMAP y-coordinate
  cluster INTEGER,  -- HDBSCAN cluster ID
  top_vibe TEXT
)
```

### 6. Vibe Mapper ([src/vibecheck/analysis/vibe_mapper.py](src/vibecheck/analysis/vibe_mapper.py))

**Purpose:** Dimensionality reduction and clustering for visualization

**Process:**
1. Load 896-dim embeddings
2. UMAP reduction to 2D (preserves local structure)
3. HDBSCAN clustering (automatic vibe group discovery)
4. Save coordinates and cluster assignments

**Output:**
- `data/vibe_map.csv` - Columns: id, name, x, y, cluster, top_vibe

**Parameters:**
- UMAP: `n_neighbors=10, min_dist=0.05, metric='cosine'`
- HDBSCAN: `min_cluster_size=5, min_samples=2`

### 7. Web Applications

**Flask App ([app/app.py](app/app.py))** - Primary Interface
- Routes: `/`, `/restaurant/<id>`, `/vibe/<name>`, `/api/search`
- Loads models at startup (CLIP, BERT, FAISS)
- Serves restaurant images from `data/images/`
- Geographic map visualization
- UMAP cluster visualization

**FastAPI Backend ([api/main.py](api/main.py))** - REST API
- OpenAPI documentation at `/docs`
- Endpoints: `/search`, `/restaurant/{id}`, `/vibes`
- JSON responses for integration

## Model Details

### CLIP (Vision-Language Model)

**Model:** OpenAI CLIP ViT-B/32
- **Architecture:** Vision Transformer with 32×32 patch size
- **Output:** 512-dimensional embeddings
- **Training:** Contrastive learning on 400M image-text pairs
- **Use Case:** Encode restaurant interior photos

**Inference:**
```python
import clip
model, preprocess = clip.load("ViT-B/32", device="cuda")

# Encode image
image = preprocess(pil_image).unsqueeze(0)
with torch.no_grad():
    image_features = model.encode_image(image)
    image_features /= image_features.norm()  # L2 normalize
```

### Sentence-BERT (Text Encoder)

**Model:** all-MiniLM-L6-v2
- **Architecture:** 6-layer MiniLM transformer
- **Output:** 384-dimensional embeddings
- **Training:** Sentence similarity tasks
- **Use Case:** Encode text queries and reviews

**Inference:**
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")

# Encode text
text_embedding = model.encode(
    "cozy romantic dim lighting",
    convert_to_numpy=True,
    normalize_embeddings=True  # L2 normalize
)
```

### FAISS (Similarity Search)

**Index Type:** IndexFlatL2 (exact L2 distance)
- **Distance Metric:** Euclidean (L2)
- **Search Time:** O(n) - exhaustive search
- **Accuracy:** 100% (exact nearest neighbors)
- **Alternative:** IndexIVFFlat for approximate search on large datasets

**Usage:**
```python
import faiss
import numpy as np

# Build index
dimension = 896
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)  # embeddings: (N, 896)

# Search
distances, indices = index.search(query_vector, k=10)
```

### UMAP (Dimensionality Reduction)

**Purpose:** Reduce 896D embeddings to 2D for visualization

**Parameters:**
- `n_neighbors=10` - Local structure preservation
- `min_dist=0.05` - Minimum separation between points
- `metric='cosine'` - Distance metric

**Properties:**
- Preserves both local and global structure
- Non-linear dimensionality reduction
- Faster than t-SNE for large datasets

### HDBSCAN (Clustering)

**Purpose:** Discover natural vibe groups without specifying cluster count

**Parameters:**
- `min_cluster_size=5` - Minimum restaurants per cluster
- `min_samples=2` - Robustness to noise

**Output:**
- Cluster labels (0, 1, 2, ...) for each restaurant
- Label -1 indicates noise/outliers

## Configuration for NYC

To adapt for New York City restaurants:

### 1. Update Search Location

```python
# config.py (Line ~194)
SEARCH_QUERIES = NYC_SEARCH_QUERIES  # Switch from DC_SEARCH_QUERIES
```

NYC queries already configured (60+ neighborhoods):
- Manhattan: SoHo, Greenwich Village, East Village, Chelsea, Tribeca, ...
- Brooklyn: Williamsburg, DUMBO, Park Slope, Greenpoint, ...
- Queens: Astoria, Long Island City, Flushing, ...
- Bronx: Mott Haven, Riverdale, Fordham, ...
- Staten Island: St. George, Stapleton

### 2. Run Data Pipeline

```bash
# Step 1: Scrape NYC restaurants
python scripts/serpapi_full_scraper.py
# Output: vibecheck_full_output/ with ~6,000+ NYC restaurants

# Step 2: Generate embeddings
python src/vibecheck/embeddings/generator.py
# Output: data/embeddings.npy, data/vibecheck_index.faiss

# Step 3: Load database
python scripts/load_sql.py
# Output: data/vibecheck.db

# Step 4: Generate visualizations
python src/vibecheck/analysis/vibe_mapper.py
# Output: data/vibe_map.csv

# Step 5: Launch app
python app/app.py
```

**No code changes required** - only config update and data regeneration!

## Performance Characteristics

### Search Performance

| Operation | Time (CPU) | Time (GPU) |
|-----------|-----------|-----------|
| Text encoding (BERT) | ~20ms | ~5ms |
| Image encoding (CLIP) | ~100ms | ~20ms |
| FAISS search (k=10) | ~10ms | ~5ms |
| Database fetch | ~50ms | ~50ms |
| **Total query time** | ~180ms | ~80ms |

### Scalability

| Dataset Size | FAISS Index Size | Memory | Search Time |
|-------------|------------------|--------|-------------|
| 2,700 (DC) | 1.9MB | ~100MB | 10ms |
| 10,000 | 7MB | ~350MB | 20ms |
| 50,000 | 35MB | ~1.7GB | 50ms |
| 100,000+ | Use IndexIVFFlat | ~3GB | 10-30ms |

## Monitoring & MLOps

**MLflow Integration:**
- Tracks embedding generation experiments
- Logs model parameters, metrics, artifacts
- UI: `mlflow ui` → http://localhost:5000

**DVC Pipeline:**
- Version control for data files
- Reproducible ML pipelines
- Command: `dvc repro` to regenerate all outputs

**Evidently Monitoring:**
- Detects embedding drift over time
- Data quality reports
- Command: `python scripts/generate_monitoring_report.py`

## Deployment

**Current Production:** Fly.io
- URL: https://vibecheck-app-1765337464.fly.dev/
- Region: iad (US East)
- Machine: 2 vCPU, 4GB RAM
- Models loaded in memory at startup

**Deployment Submodule:** `vibecheck/`
- Git submodule with Dockerfile and fly.toml
- Contains minimal production code (~175MB)
- Deploy: `cd vibecheck && flyctl deploy`

## Future Enhancements

**Performance:**
- [ ] GPU-accelerated FAISS on cloud instances
- [ ] Redis caching for frequent queries
- [ ] CDN for image serving

**Features:**
- [ ] Fine-tuned CLIP on restaurant-specific data
- [ ] User feedback for personalized results
- [ ] Multi-city support with location filtering

**Scale:**
- [ ] IVF index for millions of restaurants
- [ ] Distributed FAISS for horizontal scaling
- [ ] Real-time embedding updates
