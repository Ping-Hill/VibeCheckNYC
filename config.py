"""
VibeCheck Configuration
=======================
Centralized configuration for all data paths and settings.
"""

from pathlib import Path
import os

# ==============================================================================
# BASE DIRECTORIES
# ==============================================================================

# Project root directory
ROOT_DIR = Path(__file__).parent

# Main data directory (all processed data, embeddings, FAISS index, database)
DATA_DIR = ROOT_DIR / "data"

# Raw scraped data output (from SerpAPI scraper)
SCRAPER_OUTPUT_DIR = ROOT_DIR / "vibecheck_full_output"

# ==============================================================================
# DATA FILES
# ==============================================================================

# Database
DB_PATH = DATA_DIR / "vibecheck.db"

# Image storage
IMAGE_DIR = DATA_DIR / "images"
RESTAURANT_IMAGES_DIR = IMAGE_DIR / "restaurant_images"

# FAISS index and metadata
FAISS_INDEX_PATH = DATA_DIR / "vibecheck_index.faiss"
META_IDS_PATH = DATA_DIR / "meta_ids.npy"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"

# Visualization data
VIBE_MAP_CSV = DATA_DIR / "vibe_map.csv"

# ==============================================================================
# SCRAPER OUTPUT FILES
# ==============================================================================

SCRAPER_IMAGES_DIR = SCRAPER_OUTPUT_DIR / "images"
CHECKPOINT_FILE = SCRAPER_OUTPUT_DIR / "checkpoint.json"
RESTAURANTS_FILE = SCRAPER_OUTPUT_DIR / "all_restaurants.json"
VIBECHECK_RESULTS_FILE = SCRAPER_OUTPUT_DIR / "vibecheck_results.json"

# ==============================================================================
# MODEL SETTINGS
# ==============================================================================

# Model identifiers
TEXT_MODEL = "all-MiniLM-L6-v2"
CLIP_MODEL = "ViT-B/32"

# Device selection
import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ==============================================================================
# SCRAPER SETTINGS
# ==============================================================================

# Minimum requirements per restaurant
MIN_REVIEWS_NEEDED = 5
MIN_IMAGES_NEEDED = 5

# Quality filter thresholds - basically no filter (include everything)
MIN_RATING = 0.0  # No minimum rating
MIN_REVIEW_COUNT = 1  # Just needs 1 review

# API keys (set via environment variables)
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
OUTSCRAPER_API_KEY = os.getenv("OUTSCRAPER_API_KEY", "")

# ==============================================================================
# SEARCH QUERIES - MANHATTAN ONLY
# ==============================================================================

# Manhattan-only search queries for comprehensive coverage
SEARCH_QUERIES = [
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
]

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        DATA_DIR,
        IMAGE_DIR,
        RESTAURANT_IMAGES_DIR,
        SCRAPER_OUTPUT_DIR,
        SCRAPER_IMAGES_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    print(f"✅ Ensured all directories exist")

def get_config_summary():
    """Print configuration summary."""
    return f"""
VibeCheck NYC Configuration Summary
====================================
Data Directory: {DATA_DIR}
Database: {DB_PATH}
FAISS Index: {FAISS_INDEX_PATH}
Scraper Output: {SCRAPER_OUTPUT_DIR}
Device: {DEVICE}
Search Location: NYC
Total Search Queries: {len(SEARCH_QUERIES)}
"""

if __name__ == "__main__":
    print(get_config_summary())
    ensure_directories()
