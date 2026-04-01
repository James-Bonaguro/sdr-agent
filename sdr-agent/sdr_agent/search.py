"""Google Maps Places API search module for finding businesses."""

import googlemaps


def geocode_location(client: googlemaps.Client, location: str) -> tuple[float, float]:
    """Convert a location string to lat/lng coordinates."""
    results = client.geocode(location)
    if not results:
        raise ValueError(f"Could not geocode location: {location}")
    loc = results[0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def search_businesses(
    client: googlemaps.Client,
    query: str,
    location: str,
    radius: int = 50000,
    max_results: int = 60,
) -> list[dict]:
    """
    Search for businesses using Google Maps Places Text Search.

    Args:
        client: Initialized googlemaps client.
        query: Search query (e.g. "dental offices", "restaurants").
        location: Location string (e.g. "Austin, TX").
        radius: Search radius in meters (max 50000).
        max_results: Maximum number of results to return (max 60).

    Returns:
        List of business dicts with extracted fields.
    """
    lat, lng = geocode_location(client, location)

    all_results = []
    response = client.places(
        query=query,
        location=(lat, lng),
        radius=radius,
    )
    all_results.extend(response.get("results", []))

    # Follow pagination (up to 3 pages of 20 results each)
    while (
        "next_page_token" in response
        and len(all_results) < max_results
    ):
        import time
        time.sleep(2)  # Required delay before using next_page_token
        response = client.places(
            query=query,
            location=(lat, lng),
            radius=radius,
            page_token=response["next_page_token"],
        )
        all_results.extend(response.get("results", []))

    return [_extract_fields(r) for r in all_results[:max_results]]


def get_place_details(client: googlemaps.Client, place_id: str) -> dict:
    """Fetch detailed info for a single place."""
    result = client.place(
        place_id,
        fields=[
            "name",
            "formatted_address",
            "formatted_phone_number",
            "website",
            "rating",
            "user_ratings_total",
            "business_status",
            "type",
            "url",
        ],
    )
    return result.get("result", {})


def enrich_results(
    client: googlemaps.Client, results: list[dict]
) -> list[dict]:
    """Enrich search results with detailed place info (phone, website)."""
    enriched = []
    for r in results:
        place_id = r.get("place_id")
        if not place_id:
            enriched.append(r)
            continue
        details = get_place_details(client, place_id)
        r["phone"] = details.get("formatted_phone_number", "")
        r["website"] = details.get("website", "")
        r["google_maps_url"] = details.get("url", "")
        enriched.append(r)
    return enriched


def _extract_city(address: str) -> str:
    """Parse city from a formatted address like '123 Main St, Orland Park, IL 60462, USA'."""
    parts = [p.strip() for p in address.split(",")]
    # Typical Google format: street, city, state+zip, country
    if len(parts) >= 3:
        return parts[-3]
    if len(parts) == 2:
        return parts[0]
    return ""


def _extract_fields(place: dict) -> dict:
    """Extract relevant fields from a Places API result."""
    address = place.get("formatted_address", "")
    return {
        "business_name": place.get("name", ""),
        "address": address,
        "city": _extract_city(address),
        "google_rating": place.get("rating", ""),
        "review_count": place.get("user_ratings_total", ""),
        "place_id": place.get("place_id", ""),
        "phone": "",
        "website": "",
        "google_maps_url": "",
        "niche": "",
    }
