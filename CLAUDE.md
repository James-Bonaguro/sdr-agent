# Intersection Strategies

## Project Overview

Intersection Strategies is a consulting firm focused on business automation. The main tool is the **SDR Agent** — a Python CLI that finds businesses via Google Maps, scores their websites, classifies ownership, and exports qualified leads to CSV or Google Sheets.

## Project Structure

```
intersection-strategies/
├── index.html              # Company landing page (static HTML/CSS/JS)
└── sdr-agent/              # SDR Agent CLI tool
    ├── requirements.txt
    ├── .env                # API keys (never commit)
    └── sdr_agent/
        ├── __main__.py     # Entry point
        ├── cli.py          # CLI args and main flow
        ├── search.py       # Google Maps Places API integration
        ├── analyzer.py     # Website quality scoring + ownership classification
        ├── csv_export.py   # CSV export
        └── sheets.py       # Google Sheets export
```

## Setup & Running

```bash
cd sdr-agent
pip install -r requirements.txt

# Set your API key
export GOOGLE_MAPS_API_KEY=your-key-here

# Run a search
python -m sdr_agent "dental offices" --location "Austin, TX"
```

### Key CLI flags

- `--location` (required) — city/area to search
- `--output` / `-o` — CSV output path (default: results.csv)
- `--sheet-id` — export to Google Sheets instead of CSV
- `--radius` — search radius in meters (default/max: 50000)
- `--max-results` — cap results (default/max: 60)
- `--no-enrich` — skip fetching phone/website details
- `--no-analyze` — skip website scoring and ownership classification

## Tech Stack

- Python 3.x with argparse CLI
- `googlemaps` — Places API + Geocoding
- `requests` + `beautifulsoup4` — website fetching and parsing
- `google-api-python-client` — Sheets export

## Conventions

- Keep modules small and focused (search, analyze, export are separate)
- Use the existing patterns: functions return lists of dicts, each dict is one business
- Error handling on all API calls — never let one failed request kill the whole run
- No unnecessary abstractions — keep it straightforward
- Print progress to stdout so the user knows what's happening

## Current Status

MVP is working. The pipeline is: search → enrich → analyze → export.

## Testing

No test suite yet. When adding tests, use pytest and put them in `sdr-agent/tests/`.
