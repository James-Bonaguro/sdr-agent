"""CSV export module for writing business search results to a local file."""

import csv
import os

HEADERS = [
    "Business Name",
    "City",
    "Website",
    "Google Rating",
    "Review Count",
    "Website Score",
    "Website Issues",
    "Missed Revenue Signal",
    "Ownership Type",
    "Niche",
    "Phone",
    "Address",
]


def export_to_csv(results: list[dict], output_path: str) -> str:
    """
    Write search results to a CSV file.

    Args:
        results: List of business result dicts.
        output_path: File path for the output CSV.

    Returns:
        Absolute path to the written CSV file.
    """
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        for r in results:
            writer.writerow(_result_to_row(r))

    return os.path.abspath(output_path)


def _result_to_row(result: dict) -> list[str]:
    """Convert a result dict to a row of cell values."""
    return [
        str(result.get("business_name", "")),
        str(result.get("city", "")),
        str(result.get("website", "")),
        str(result.get("google_rating", "")),
        str(result.get("review_count", "")),
        str(result.get("website_score", "")),
        str(result.get("website_issues", "")),
        str(result.get("missed_revenue_signal", "")),
        str(result.get("ownership_type", "")),
        str(result.get("niche", "")),
        str(result.get("phone", "")),
        str(result.get("address", "")),
    ]
