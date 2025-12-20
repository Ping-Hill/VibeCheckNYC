# VibeCheck Backend Deployment

## 🚀 Recommended: Railway Dashboard (Easiest)

This is the easiest method - deploys directly from GitHub.

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### Step 2: Deploy on Railway Dashboard

1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account if not already connected
5. Select the `VibeCheck` repository
6. Railway will auto-detect Python and start deploying

### Step 3: Upload Data Files (Required!)

The database and embeddings are too large for git (~29MB total). You need to upload them manually.

**Option A: Use Railway CLI (Recommended)**
```bash
# Install Railway CLI (already done)
npm install -g @railway/cli

# Login to Railway (opens browser)
railway login

# Link to your project
railway link

# Upload data files
railway run -- mkdir -p data vibecheck_full_output

# Upload database (16MB)
railway run -- sh -c 'cat > vibecheck_full_output/vibecheck.db' < vibecheck_full_output/vibecheck.db

# Upload FAISS index (13MB)
railway run -- sh -c 'cat > data/vibecheck_index.faiss' < data/vibecheck_index.faiss

# Upload meta IDs (29KB)
railway run -- sh -c 'cat > data/meta_ids.npy' < data/meta_ids.npy
```

**Option B: Use Railway Volumes (Alternative)**
1. In Railway dashboard, go to your project
2. Click "Variables" tab
3. Add volume mounts:
   - `/app/data` → Upload `vibecheck_index.faiss` and `meta_ids.npy`
   - `/app/vibecheck_full_output` → Upload `vibecheck.db`

### Step 4: Generate Public Domain

1. In Railway dashboard, go to your project
2. Click "Settings" tab
3. Under "Domains", click "Generate Domain"
4. You'll get a URL like: `https://vibecheck-production.up.railway.app`

### Step 5: Test Deployment

```bash
# Replace with your Railway URL
curl https://vibecheck-production.up.railway.app/api/search \
  -X POST \
  -F "text=cozy italian" \
  -F "top_k=3"
```

---

## Alternative: Railway CLI Deployment

Use this if you prefer command-line deployment.

### 1. Install Railway CLI
```bash
npm install -g @railway/cli
```

### 2. Login to Railway
```bash
railway login
```

### 3. Initialize Project
```bash
railway init
```

### 4. Upload Database and Embeddings
```bash
# Create data directories
railway run -- mkdir -p data vibecheck_full_output

# Upload files (same as above)
railway run -- sh -c 'cat > vibecheck_full_output/vibecheck.db' < vibecheck_full_output/vibecheck.db
railway run -- sh -c 'cat > data/vibecheck_index.faiss' < data/vibecheck_index.faiss
railway run -- sh -c 'cat > data/meta_ids.npy' < data/meta_ids.npy
```

### 5. Deploy
```bash
railway up
```

### 6. Generate Domain
```bash
railway domain
```

## Testing the Deployment

Once deployed, test with:
```bash
curl https://your-app.railway.app/api/search -X POST -F "text=cozy italian" -F "top_k=3"
```

## React Native Configuration

In your React Native app, use:
```javascript
const API_URL = 'https://your-app.railway.app';
```

## Important Notes

- Database file: ~100MB (vibecheck.db)
- FAISS index: ~13MB
- Total upload: ~120MB
- First deployment will take 5-10 minutes (downloading PyTorch, etc.)
- Subsequent deploys: ~2-3 minutes
