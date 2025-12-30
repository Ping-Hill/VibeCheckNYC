"""
Fetch price levels from Google Places API for all restaurants.
Price levels: 0 = Free, 1 = $, 2 = $$, 3 = $$$, 4 = $$$$
"""
import sqlite3
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY')
DB_PATH = 'vibecheck_full_output/vibecheck.db'

def get_price_level(place_id):
    """Fetch price level from Google Places API."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        'place_id': place_id,
        'fields': 'price_level',
        'key': GOOGLE_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get('status') == 'OK':
            result = data.get('result', {})
            return result.get('price_level')
        else:
            print(f"API error for {place_id}: {data.get('status')}")
            return None
    except Exception as e:
        print(f"Error fetching {place_id}: {e}")
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all restaurants without price level
    cursor.execute("SELECT id, place_id, name FROM restaurants WHERE price_level IS NULL")
    restaurants = cursor.fetchall()

    print(f"Found {len(restaurants)} restaurants to update")

    updated = 0
    failed = 0

    for restaurant_id, place_id, name in restaurants:
        print(f"Fetching price for {name}...")

        price_level = get_price_level(place_id)

        if price_level is not None:
            cursor.execute(
                "UPDATE restaurants SET price_level = ? WHERE id = ?",
                (price_level, restaurant_id)
            )
            conn.commit()
            updated += 1
            print(f"  ✓ Updated: ${price_level * '$'}")
        else:
            failed += 1
            print(f"  ✗ Failed to get price")

        # Rate limiting - Google allows 1000 requests per day for free tier
        time.sleep(0.1)

        # Checkpoint every 100 restaurants
        if (updated + failed) % 100 == 0:
            print(f"\nProgress: {updated} updated, {failed} failed, {len(restaurants) - updated - failed} remaining\n")

    conn.close()

    print(f"\n✓ Complete: {updated} updated, {failed} failed")
    print(f"Price distribution:")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            CASE
                WHEN price_level = 1 THEN '$'
                WHEN price_level = 2 THEN '$$'
                WHEN price_level = 3 THEN '$$$'
                WHEN price_level = 4 THEN '$$$$'
                ELSE 'Unknown'
            END as price,
            COUNT(*) as count
        FROM restaurants
        GROUP BY price_level
        ORDER BY price_level
    """)

    for price, count in cursor.fetchall():
        print(f"  {price}: {count} restaurants")

    conn.close()

if __name__ == '__main__':
    main()
