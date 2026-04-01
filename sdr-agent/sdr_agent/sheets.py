"""Google Sheets export module using the Sheets API with an API key."""

from googleapiclient.discovery import build

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


def export_to_sheet(
    api_key: str,
    spreadsheet_id: str,
    results: list[dict],
    worksheet_name: str = "Sheet1",
) -> str:
    """
    Write search results to a Google Sheet using an API key.

    The spreadsheet must be shared as "Anyone with the link can edit".

    Args:
        api_key: Google API key with Sheets API enabled.
        spreadsheet_id: ID of the target Google Spreadsheet.
        results: List of business result dicts.
        worksheet_name: Name of the worksheet tab to write to.

    Returns:
        URL of the updated spreadsheet.
    """
    service = build("sheets", "v4", developerKey=api_key)
    sheets = service.spreadsheets()

    rows = [HEADERS] + [_result_to_row(r) for r in results]

    # Clear existing content then write new data
    range_name = f"{worksheet_name}!A1"
    sheets.values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"{worksheet_name}",
        body={},
    ).execute()

    sheets.values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="RAW",
        body={"values": rows},
    ).execute()

    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"


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
