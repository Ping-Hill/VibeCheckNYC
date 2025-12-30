"""
NYC Neighborhood Mapping
Zip codes to neighborhoods with common variations
"""

# Zip code to canonical neighborhood name
ZIP_TO_NEIGHBORHOOD = {
    # Washington Heights - Inwood
    "10031": "Washington Heights",
    "10032": "Washington Heights",
    "10033": "Washington Heights",
    "10034": "Inwood",
    "10040": "Inwood",

    # Central Harlem - Morningside Heights
    "10026": "Central Harlem",
    "10027": "Morningside Heights",
    "10030": "Central Harlem",
    "10037": "Central Harlem",
    "10039": "Central Harlem",

    # East Harlem
    "10029": "East Harlem",
    "10035": "East Harlem",

    # Upper West Side
    "10023": "Upper West Side",
    "10024": "Upper West Side",
    "10025": "Upper West Side",

    # Upper East Side
    "10021": "Upper East Side",
    "10028": "Upper East Side",
    "10044": "Upper East Side",
    "10128": "Upper East Side",

    # Chelsea - Clinton
    "10001": "Chelsea",
    "10011": "Chelsea",
    "10018": "Hell's Kitchen",
    "10019": "Hell's Kitchen",
    "10020": "Midtown",
    "10036": "Hell's Kitchen",

    # Gramercy Park - Murray Hill
    "10010": "Gramercy",
    "10016": "Murray Hill",
    "10017": "Murray Hill",
    "10022": "Gramercy",

    # Greenwich Village - SoHo
    "10012": "SoHo",
    "10013": "Tribeca",
    "10014": "West Village",

    # Union Square - Lower East Side
    "10002": "Lower East Side",
    "10003": "East Village",
    "10009": "East Village",

    # Lower Manhattan
    "10004": "Financial District",
    "10005": "Financial District",
    "10006": "Financial District",
    "10007": "Financial District",
    "10038": "Lower Manhattan",
    "10280": "Battery Park City",
}

# Common variations and abbreviations
NEIGHBORHOOD_VARIATIONS = {
    "soho": "SoHo",
    "so ho": "SoHo",
    "south of houston": "SoHo",

    "tribeca": "Tribeca",
    "tri beca": "Tribeca",
    "triangle below canal": "Tribeca",

    "west village": "West Village",
    "greenwich village": "West Village",
    "the village": "West Village",

    "east village": "East Village",
    "ev": "East Village",

    "lower east side": "Lower East Side",
    "les": "Lower East Side",
    "lowereast": "Lower East Side",

    "upper east side": "Upper East Side",
    "ues": "Upper East Side",
    "uppereast": "Upper East Side",

    "upper west side": "Upper West Side",
    "uws": "Upper West Side",
    "upperwest": "Upper West Side",

    "hells kitchen": "Hell's Kitchen",
    "hell's kitchen": "Hell's Kitchen",
    "clinton": "Hell's Kitchen",

    "chelsea": "Chelsea",

    "gramercy": "Gramercy",
    "gramercy park": "Gramercy",

    "murray hill": "Murray Hill",

    "midtown": "Midtown",
    "midtown manhattan": "Midtown",

    "financial district": "Financial District",
    "fidi": "Financial District",
    "wall street": "Financial District",

    "battery park": "Battery Park City",
    "battery park city": "Battery Park City",

    "washington heights": "Washington Heights",
    "wash heights": "Washington Heights",

    "inwood": "Inwood",

    "harlem": "Central Harlem",
    "central harlem": "Central Harlem",

    "east harlem": "East Harlem",
    "spanish harlem": "East Harlem",
    "el barrio": "East Harlem",

    "morningside heights": "Morningside Heights",
    "morningside": "Morningside Heights",
}


def extract_zip_from_address(address):
    """Extract zip code from address string."""
    import re
    if not address:
        return None
    # Match 5-digit zip code
    match = re.search(r'\b(\d{5})\b', address)
    return match.group(1) if match else None


def get_neighborhood_from_zip(zip_code):
    """Get canonical neighborhood name from zip code."""
    return ZIP_TO_NEIGHBORHOOD.get(zip_code)


def normalize_neighborhood_query(query):
    """
    Normalize user's neighborhood query to canonical name.
    Handles case-insensitive matching and common variations.
    """
    query_lower = query.lower().strip()

    # Direct match
    if query_lower in NEIGHBORHOOD_VARIATIONS:
        return NEIGHBORHOOD_VARIATIONS[query_lower]

    # Check if query contains any neighborhood variation
    for variation, canonical in NEIGHBORHOOD_VARIATIONS.items():
        if variation in query_lower:
            return canonical

    return None
