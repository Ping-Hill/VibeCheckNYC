# VibeCheck NYC - Project Summary

## Project Overview
VibeCheck NYC is a restaurant discovery app for New York City that uses AI-powered semantic search to find restaurants based on vibes, atmosphere, and dining preferences. Users can search for things like "romantic italian" or "cozy brunch spot" and get relevant results.

## Architecture

### Backend (Flask API - Deployed on Railway)
- **Location**: `/Users/iphone10/Desktop/VibeCheck copy/`
- **Deployment**: Railway (https://web-production-c67df.up.railway.app)
- **Main App**: `app/app.py`
- **Database**: SQLite at `vibecheck_full_output/vibecheck.db`
- **Search Engine**: FAISS vector search with text embeddings
- **Image Storage**: AWS S3 bucket `vibecheck-nyc-images`

### Mobile App (React Native + Expo)
- **Location**: `/Users/iphone10/Desktop/VibeCheckMobile/`
- **Framework**: React Native with Expo
- **API Client**: `src/services/api.js`
- **Backend URL**: https://web-production-c67df.up.railway.app

## Key File Paths

### Backend Files
```
/Users/iphone10/Desktop/VibeCheck copy/
├── app/
│   ├── app.py                          # Main Flask application
│   └── templates/
│       ├── index_nyc.html              # Web frontend homepage
│       └── restaurant.html             # Restaurant detail page
├── vibecheck_full_output/
│   ├── vibecheck.db                    # SQLite database (3,708 restaurants)
│   ├── vibecheck_index.faiss           # FAISS search index
│   ├── vibe_embeddings.npy             # Text embeddings (384-dim)
│   ├── meta_ids.npy                    # Restaurant ID mappings
│   ├── images_compressed/              # Local image files (14,150 images)
│   └── vibecheck_results.json          # Source data
└── scripts/                            # Data processing scripts
```

### Mobile App Files
```
/Users/iphone10/Desktop/VibeCheckMobile/
├── src/
│   ├── services/
│   │   └── api.js                      # API client (connects to Railway)
│   ├── screens/
│   │   ├── SearchScreen.js             # Search interface
│   │   ├── DetailsScreen.js            # Restaurant details
│   │   └── ...
│   └── utils/
│       └── imageHelper.js              # S3 image URL helper
├── package.json
└── App.js
```

## Database Schema

### Tables
1. **restaurants** (3,708 records)
   - id, name, place_id, address, rating, reviews_count, neighborhood, price_level

2. **reviews** (55,660 records - 15 per restaurant)
   - id, restaurant_id, review_text, likes

3. **vibe_photos** (14,150 records)
   - id, restaurant_id, photo_url, local_filename

4. **vibe_analysis**
   - restaurant_id, vibe_name, mention_count

## Image Storage (AWS S3)

### Bucket Details
- **Bucket**: `vibecheck-nyc-images`
- **Region**: `us-east-1`
- **Path**: `images/`
- **Total Images**: 14,150 high-quality images
- **Storage Size**: ~13.4 GB
- **Quality Threshold**: All images >100KB (blurry images <100KB were deleted)
- **Public Access**: Enabled via bucket policy

### Image URL Format
```
https://vibecheck-nyc-images.s3.us-east-1.amazonaws.com/images/{filename}
```

### Image Naming Conventions
Two formats exist:
1. **Place ID format**: `ChIJABC123xyz_1.jpg` (13,470 images)
2. **Name format**: `Restaurant_Name_vibe_1.jpg` (680 images)

## Search Technology

### Embeddings
- **Model**: SentenceTransformer `all-MiniLM-L6-v2`
- **Dimensions**: 384 (text-only, no image embeddings for speed)
- **Index Type**: FAISS (Facebook AI Similarity Search)

### Keyword Boosting
Reviews are boosted for semantic search:
- Cuisine keywords: 3x boost (italian, mexican, japanese, etc.)
- Vibe keywords: 2x boost (romantic, cozy, trendy, etc.)
- Price keywords: 2x boost ($, $$, $$$, $$$$)
- Neighborhood keywords: 2x boost (Manhattan neighborhoods only)
- Venue keywords: 2x boost (rooftop, bar, cafe, etc.)

### Search Process
1. User enters query (e.g., "romantic italian")
2. Query is embedded using text model
3. FAISS finds top 50 similar restaurants
4. Results filtered by neighborhood/price if specified
5. Returns restaurants with photos, reviews, and vibes

## API Endpoints

### Railway Backend (Flask)
```
POST /api/search
  Body: {"query": "romantic italian", "k": 50, "price_level": [1,2,3,4]}
  Returns: {"results": [...restaurants with reviews and photos...]}

GET /api/restaurant/{id}
  Returns: Full restaurant details with all 15 reviews and photos

GET /api/top-vibes
  Returns: Most common vibes across all restaurants

GET /
  Returns: Web frontend (index_nyc.html)

GET /restaurant/{id}
  Returns: Restaurant detail page (restaurant.html)
```

## Recent Fixes & Changes

### Database Cleanup (Dec 31, 2025)
1. ✅ Fixed database corruption - reviews were assigned to wrong restaurants
2. ✅ Rebuilt database from source JSON with deduplication
3. ✅ Fixed photo routing - exact matching by place_id and name
4. ✅ Deleted 2 invalid restaurants (Little Italy Sign, Bollywood Rasoi)
5. ✅ Removed 3,442 blurry images (<100KB) from S3 and database
6. ✅ Increased review limit from 10 to 15 per restaurant

### Current Stats
- **Restaurants**: 3,708
- **Restaurants with photos**: 3,667 (98.9%)
- **Total reviews**: 55,660 (avg 15 per restaurant)
- **Total photos**: 14,150 (avg 3.8 per restaurant)
- **Duplicate photos**: 0 (all unique)

## How to Deploy

### Railway Backend
```bash
cd "/Users/iphone10/Desktop/VibeCheck copy"
git add .
git commit -m "Your message"
git push  # Automatically deploys to Railway
```

### Mobile App (Expo)
```bash
cd /Users/iphone10/Desktop/VibeCheckMobile
npx expo start
# Scan QR code with Expo Go app on phone
```

## Environment & Dependencies

### Backend Requirements
- Python 3.11+
- Flask
- FAISS
- SentenceTransformers
- SQLite3
- boto3 (AWS S3)

### Mobile Requirements
- Node.js
- Expo CLI
- React Native
- Axios

## Git Repository
- **Remote**: github.com:Ping-Hill/VibeCheckNYC.git
- **Branch**: main
- **Railway**: Auto-deploys on push to main

## S3 Configuration

### Upload Images to S3
```bash
cd "/Users/iphone10/Desktop/VibeCheck copy"
python3 scripts/upload_to_s3_final.py
```

### Bucket Policy (Public Read)
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::vibecheck-nyc-images/images/*"
  }]
}
```

## Common Issues & Solutions

### Mobile App: "Request timed out"
- **Cause**: Slow network or backend taking too long
- **Solution**: Increase axios timeout in `src/services/api.js` (currently 30s)
- **Alternative**: Use tunnel mode: `npx expo start --tunnel`

### Images not loading
- **Check**: S3 bucket policy allows public read
- **Check**: Image filenames in database match actual S3 files
- **Check**: Browser/app cache - hard refresh

### Search returns wrong results
- **Check**: Embeddings match FAISS index dimensions (384-dim text-only)
- **Check**: Database has correct review-to-restaurant mappings
- **Solution**: Regenerate embeddings if needed

## Important Notes

1. **Image Quality**: All images >100KB kept, <100KB deleted (blurry threshold)
2. **Review Source**: Restored from Dec 22 backup (had 15 reviews vs 5 in JSON)
3. **Embeddings**: Text-only (384-dim) for speed - no image embeddings currently
4. **Photo Routing**: Fixed to exact match - no duplicates across restaurants
5. **Mobile API**: Points to Railway, images from S3 (not bundled with app)

## Next Steps / TODO

- [ ] Consider raising image quality threshold to 200-300KB if needed
- [ ] Add image embeddings for visual search (would need regeneration)
- [ ] Fix remaining blurry images if user reports specific ones
- [ ] Test mobile app thoroughly on device
- [ ] Consider adding more neighborhoods beyond Manhattan
