# SDR Agent — Business Search CLI

Search for businesses using Google Maps Places API and export leads to CSV.

## Setup

### 1. Install dependencies

```bash
cd sdr-agent
pip install -r requirements.txt
```

### 2. Google Maps API key

Get an API key from the [Google Cloud Console](https://console.cloud.google.com/apis/credentials) with the **Places API** and **Geocoding API** enabled.

```bash
export GOOGLE_MAPS_API_KEY=your-key-here
```

On Windows (PowerShell):
```powershell
$env:GOOGLE_MAPS_API_KEY="your-key-here"
```

## Usage

```bash
python -m sdr_agent "dental offices" --location "Austin, TX"
```

This saves results to `results.csv` in the current directory.

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `query` | Search query (e.g. "plumbers", "SaaS companies") | *required* |
| `--location` | Location to search around | *required* |
| `--output`, `-o` | Output CSV file path | results.csv |
| `--radius` | Search radius in meters | 50000 |
| `--max-results` | Max results to return | 60 |
| `--no-enrich` | Skip fetching phone/website details | false |
| `--google-api-key` | Google Maps API key | `$GOOGLE_MAPS_API_KEY` |

### Examples

Search for restaurants in San Francisco:
```bash
python -m sdr_agent "restaurants" --location "San Francisco, CA"
```

Save to a specific file:
```bash
python -m sdr_agent "restaurants" --location "San Francisco, CA" -o sf_restaurants.csv
```

Quick search without phone/website enrichment:
```bash
python -m sdr_agent "law firms" --location "New York, NY" --no-enrich
```

Search within a smaller radius (5km):
```bash
python -m sdr_agent "gyms" --location "Chicago, IL" --radius 5000
```

## Output

Results are saved as a CSV file with the following columns:

- Name
- Address
- Phone
- Website
- Rating
- Total Ratings
- Business Status
- Types
- Google Maps URL
