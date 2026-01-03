#!/bin/bash

# Run database migration on startup
echo "Running database migration..."
python3 scripts/add_lat_lon_columns.py || echo "Migration failed or already applied"

# Start the server
exec gunicorn --bind 0.0.0.0:${PORT:-8080} --timeout 120 --workers 2 app.app:app
