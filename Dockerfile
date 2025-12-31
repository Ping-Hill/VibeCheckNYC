FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy neighborhood mapping to root for imports
COPY neighborhood_mapping.py ./

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Copy ALL vibecheck data (database, embeddings, images)
# This avoids path-level failures and is more deterministic
# Cache bust: 2025-12-29-17:45 - Updated DB with price_level and neighborhood
COPY vibecheck_full_output/ ./vibecheck_full_output/

# Expose port
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV OUTPUT_DIR=/app/vibecheck_full_output
ENV DB_PATH=/app/vibecheck_full_output/vibecheck.db
ENV FAISS_PATH=/app/vibecheck_full_output/vibecheck_index.faiss
ENV META_PATH=/app/vibecheck_full_output/meta_ids.npy

# Run the application using startup script
CMD ["/app/start.sh"]
