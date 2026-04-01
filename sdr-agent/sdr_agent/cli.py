"""CLI entry point for the SDR Agent business search tool."""

import argparse
import os
import sys

import googlemaps

from .analyzer import analyze_businesses
from .csv_export import export_to_csv
from .search import enrich_results, search_businesses
# from .sheets import export_to_sheet


def main():
    parser = argparse.ArgumentParser(
        description="SDR Agent — Search for businesses, score leads, and export."
    )
    parser.add_argument(
        "query",
        help="Search query (e.g. 'dental offices', 'plumbers', 'SaaS companies')",
    )
    parser.add_argument(
        "--location",
        required=True,
        help="Location to search around (e.g. 'Austin, TX', 'San Francisco, CA')",
    )
    parser.add_argument(
        "--radius",
        type=int,
        default=50000,
        help="Search radius in meters (default: 50000, max: 50000)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=60,
        help="Maximum number of results (default: 60, max: 60)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="results.csv",
        help="Output CSV file path (default: results.csv)",
    )
    parser.add_argument(
        "--sheet-id",
        help="Google Spreadsheet ID — if provided, results export to Sheets instead of CSV",
    )
    parser.add_argument(
        "--worksheet",
        default="Sheet1",
        help="Worksheet tab name when exporting to Sheets (default: Sheet1)",
    )
    parser.add_argument(
        "--google-api-key",
        default=os.environ.get("GOOGLE_MAPS_API_KEY"),
        help="Google API key (or set GOOGLE_MAPS_API_KEY env var)",
    )
    parser.add_argument(
        "--sheets-api-key",
        default=os.environ.get("GOOGLE_SHEETS_API_KEY"),
        help="Separate API key for Sheets (defaults to --google-api-key if not set)",
    )
    parser.add_argument(
        "--niche",
        default=None,
        help="Business niche label (e.g. 'med spa', 'dental'). Auto-inferred from query if not set.",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip fetching detailed info (phone, website) for each result",
    )
    parser.add_argument(
        "--no-analyze",
        action="store_true",
        help="Skip website quality scoring and ownership classification",
    )

    args = parser.parse_args()

    if not args.google_api_key:
        print("Error: Google API key is required.")
        print("Set GOOGLE_MAPS_API_KEY env var or pass --google-api-key.")
        sys.exit(1)

    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=args.google_api_key)

    # Search for businesses
    print(f"Searching for '{args.query}' near {args.location}...")
    results = search_businesses(
        client=gmaps,
        query=args.query,
        location=args.location,
        radius=args.radius,
        max_results=args.max_results,
    )
    print(f"Found {len(results)} results.")

    if not results:
        print("No results found. Try broadening your search.")
        sys.exit(0)

    # Assign niche to each result
    niche = args.niche or _infer_niche(args.query)
    for r in results:
        r["niche"] = niche

    # Enrich with details (phone, website)
    if not args.no_enrich:
        print("Fetching detailed info for each business...")
        results = enrich_results(gmaps, results)

    # Analyze websites for quality scoring and ownership classification
    if not args.no_analyze:
        print("Analyzing websites (scoring quality, classifying ownership)...")
        results = analyze_businesses(results)
        _print_analysis_summary(results)

    # Export results
    # if args.sheet_id:
    #     sheets_key = args.sheets_api_key or args.google_api_key
    #     print("Exporting to Google Sheets...")
    #     url = export_to_sheet(
    #         api_key=sheets_key,
    #         spreadsheet_id=args.sheet_id,
    #         results=results,
    #         worksheet_name=args.worksheet,
    #     )
    #     print(f"Done! {len(results)} businesses exported to: {url}")
    # else:
    print(f"Saving results to {args.output}...")
    path = export_to_csv(results, args.output)
    print(f"Done! {len(results)} businesses saved to: {path}")


def _infer_niche(query: str) -> str:
    """Best-effort niche label from the search query."""
    q = query.lower()
    for keyword, label in [
        ("med spa", "med spa"),
        ("medspa", "med spa"),
        ("dental", "dental"),
        ("dentist", "dental"),
        ("chiro", "chiropractic"),
        ("dermatolog", "dermatology"),
        ("plastic surg", "plastic surgery"),
        ("cosmetic", "cosmetic"),
        ("veterinar", "veterinary"),
        ("optometr", "optometry"),
        ("orthodont", "orthodontics"),
    ]:
        if keyword in q:
            return label
    # Fall back to the raw query
    return query.strip()


def _print_analysis_summary(results: list[dict]) -> None:
    """Print a brief summary of the analysis results."""
    independent = sum(1 for r in results if r.get("ownership_type") == "Independent")
    group = sum(1 for r in results if r.get("ownership_type") == "Group/DSO")
    unknown = sum(1 for r in results if r.get("ownership_type") == "Unknown")

    scored = [r for r in results if r.get("website_score", 0) > 0]
    avg_score = sum(r["website_score"] for r in scored) / len(scored) if scored else 0
    low_score = sum(1 for r in scored if r["website_score"] < 50)

    print(f"\n  Ownership:  {independent} Independent | {group} Group/DSO | {unknown} Unknown")
    print(f"  Websites:   avg score {avg_score:.0f}/100 | {low_score} low-scoring leads (prime targets)\n")


if __name__ == "__main__":
    main()
