"""Website analysis module for scoring lead quality and classifying ownership."""

import re
import logging
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 10
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_BROWSER_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ---------------------------------------------------------------------------
# Ownership classification patterns
# ---------------------------------------------------------------------------

# Footer / body patterns that signal the practice belongs to a larger group
_GROUP_PATTERNS = [
    r"a\s+proud\s+partner\s+of",
    r"proud\s+member\s+of",
    r"supported\s+by",
    r"managed\s+by",
    r"part\s+of\s+the\s+\w+\s+(family|network|group)",
    r"a\s+(portfolio|affiliated)\s+company",
    r"backed\s+by",
    r"an?\s+\w+\s+portfolio\s+company",
    r"\d{2,}\s+locations",
    r"\d{2,}\s+offices",
    r"nationwide\s+network",
    r"all\s+rights\s+reserved.*(?:management|partners|capital|holdings|group)",
    r"©.*(?:dental\s+care|management|partners|capital|holdings|group)\s+(?:llc|inc|corp)",
]

# Known DSO / group brands (dental-specific but expandable)
_KNOWN_GROUP_BRANDS = [
    "aspen dental",
    "heartland dental",
    "pacific dental",
    "dental care alliance",
    "smile brands",
    "dentalcorp",
    "mid-atlantic dental partners",
    "affordable care",
    "great expressions",
    "western dental",
    "birner dental",
    "interdent",
    "dental365",
    "mb2 dental",
    "north american dental group",
    "shore dental",
    "dental depot",
]

# Patterns suggesting independent ownership
_INDEPENDENT_PATTERNS = [
    r"family[\s-]owned",
    r"locally[\s-]owned",
    r"independently[\s-]owned",
    r"private\s+practice",
    r"sole\s+practitioner",
    r"owner[\s-]operated",
]

# ---------------------------------------------------------------------------
# Website quality scoring signals
# ---------------------------------------------------------------------------

_POSITIVE_SIGNALS = {
    "has_online_booking": (
        [r"book\s+(online|now|appointment)", r"schedule\s+(online|now|appointment)",
         r"request\s+appointment", r"online\s+scheduling"],
        15,
    ),
    "has_services_page": (
        [r"(our\s+)?services", r"treatments?\s+(we\s+offer|offered)"],
        10,
    ),
    "has_reviews_or_testimonials": (
        [r"testimonials?", r"patient\s+reviews", r"what\s+(our\s+)?(patients|clients)\s+say"],
        10,
    ),
    "has_team_page": (
        [r"(our|meet)\s+(the\s+)?(team|doctors?|staff|providers?)",
         r"about\s+(the\s+)?doctor"],
        5,
    ),
    "has_contact_form": (
        [r"contact\s+us", r"get\s+in\s+touch", r"send\s+(us\s+)?a?\s?message"],
        5,
    ),
    "has_insurance_info": (
        [r"(accepted\s+)?insurance", r"payment\s+options", r"financing"],
        5,
    ),
    "has_new_patient_info": (
        [r"new\s+patient", r"first\s+visit", r"welcome\s+new"],
        10,
    ),
    "has_blog": (
        [r"<a[^>]*href=[^>]*blog", r"/blog"],
        5,
    ),
}

_NEGATIVE_SIGNALS = {
    "has_broken_layout": (
        [r"lorem\s+ipsum", r"coming\s+soon", r"under\s+construction",
         r"site\s+not\s+found", r"page\s+not\s+found"],
        -20,
    ),
    "is_template_site": (
        [r"powered\s+by\s+wix", r"powered\s+by\s+squarespace",
         r"weebly\.com", r"wordpress\.com"],
        -5,
    ),
}


# ---------------------------------------------------------------------------
# Issue descriptions (what's MISSING, framed as a business problem)
# ---------------------------------------------------------------------------

_MISSING_ISSUE_MAP = {
    "has_online_booking": "No online booking flow visible - likely losing ready-to-book visitors",
    "has_reviews_or_testimonials": "No visible reviews/testimonials on site - not leveraging strong reputation",
    "has_services_page": "No clear services page - visitors can't quickly see what's offered",
    "has_team_page": "No team/provider page - missing trust-building for new patients",
    "has_new_patient_info": "No new patient info - friction for first-time visitors",
    "has_contact_form": "No clear contact form - making it hard for leads to reach out",
    "has_insurance_info": "No insurance/payment info - potential patients bouncing with unanswered questions",
}

_NEGATIVE_ISSUE_MAP = {
    "has_broken_layout": "Site has broken/placeholder content - seriously hurting credibility",
    "is_template_site": "Site feels outdated vs competitors - trust drop for new visitors",
}


def analyze_website(url: str, google_rating=None, review_count=None) -> dict:
    """
    Fetch a website and return quality score, issues, revenue signal, and ownership.

    Returns:
        Dict with keys:
            - website_score (int): 0-100 quality score
            - website_issues (str): top 3 actionable issues, pipe-delimited
            - missed_revenue_signal (str): one-line outreach hook
            - ownership_type (str): "Independent", "Group/DSO", or "Unknown"
    """
    result = {
        "website_score": 0,
        "website_issues": "",
        "missed_revenue_signal": "",
        "ownership_type": "Unknown",
    }

    if not url:
        result["website_issues"] = "No website found"
        result["missed_revenue_signal"] = _build_revenue_signal(
            google_rating, review_count, 0, ["no_website"], False
        )
        return result

    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        resp = requests.get(
            url,
            timeout=_REQUEST_TIMEOUT,
            headers=_BROWSER_HEADERS,
            allow_redirects=True,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.debug("Failed to fetch %s (attempt 1): %s — retrying with full browser headers", url, e)
        try:
            resp = requests.get(
                url,
                timeout=_REQUEST_TIMEOUT,
                headers=_BROWSER_HEADERS,
                allow_redirects=True,
            )
            resp.raise_for_status()
        except requests.RequestException as e2:
            logger.debug("Failed to fetch %s (attempt 2): %s", url, e2)
            result["website_issues"] = "Website unreachable"
            result["missed_revenue_signal"] = _build_revenue_signal(
                google_rating, review_count, 0, ["unreachable"], False
            )
            return result

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True).lower()
    html_lower = html.lower()

    # --- Quality scoring ---
    score = 30  # baseline: site exists and loads
    found_positive = set()
    found_negative = set()
    is_template = False

    # Check SSL
    if resp.url.startswith("https://"):
        score += 5

    # Positive signals
    for signal_name, (patterns, points) in _POSITIVE_SIGNALS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE) or re.search(pat, html_lower, re.IGNORECASE):
                score += points
                found_positive.add(signal_name)
                break

    # Negative signals
    for signal_name, (patterns, points) in _NEGATIVE_SIGNALS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE) or re.search(pat, html_lower, re.IGNORECASE):
                score += points
                found_negative.add(signal_name)
                if signal_name == "is_template_site":
                    is_template = True
                break

    result["website_score"] = max(0, min(100, score))

    # --- Build website_issues (top 3) ---
    issues = []

    # Negative signals first (most impactful)
    for sig in found_negative:
        if sig in _NEGATIVE_ISSUE_MAP:
            issues.append(_NEGATIVE_ISSUE_MAP[sig])

    # Missing positive signals (prioritized by point value)
    missing_sorted = sorted(
        [(name, pts) for name, (_, pts) in _POSITIVE_SIGNALS.items() if name not in found_positive],
        key=lambda x: -x[1],
    )
    for name, _ in missing_sorted:
        if name in _MISSING_ISSUE_MAP:
            issues.append(_MISSING_ISSUE_MAP[name])

    result["website_issues"] = " | ".join(issues[:3])

    # --- Build missed_revenue_signal ---
    missing_names = [name for name, _ in missing_sorted]
    result["missed_revenue_signal"] = _build_revenue_signal(
        google_rating, review_count, result["website_score"],
        missing_names + list(found_negative), is_template,
    )

    # --- Ownership classification ---
    ownership, _ = _classify_ownership(text, html_lower, url)
    result["ownership_type"] = ownership

    return result


def _build_revenue_signal(
    google_rating, review_count, website_score, issues, is_template,
) -> str:
    """Generate a one-line missed revenue hook based on business data + website quality."""
    rating = _safe_float(google_rating)
    reviews = _safe_int(review_count)
    has_strong_reviews = rating is not None and rating >= 4.5
    has_high_volume = reviews is not None and reviews >= 50
    low_score = website_score < 50

    if "no_website" in issues:
        if has_strong_reviews:
            return f"Strong reviews ({rating}*, {reviews} reviews) but no website - invisible to online searchers"
        return "No website - missing all online traffic and bookings"

    if "unreachable" in issues:
        if has_strong_reviews:
            return f"Great reputation ({rating}*) but website is down - actively losing potential customers"
        return "Website unreachable - potential customers hitting a dead end"

    if has_strong_reviews and low_score:
        return f"Strong reviews ({rating}*) but outdated website likely under-converting traffic"

    if has_high_volume and "has_online_booking" in issues:
        return f"High review volume ({reviews} reviews) but no online booking flow visible"

    if has_strong_reviews and is_template:
        return f"Premium reputation ({rating}*) but website doesn't reflect it - template-based site"

    if has_strong_reviews and "has_reviews_or_testimonials" in issues:
        return f"Great Google reviews ({rating}*) but not showcased on website - missing social proof"

    if low_score:
        return "Website underperforming - likely losing visitors to competitors with stronger online presence"

    if "has_online_booking" in issues:
        return "No clear online booking - friction for ready-to-convert visitors"

    return "Website could better convert existing traffic into booked appointments"


def _safe_float(val) -> float | None:
    """Convert to float or return None."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> int | None:
    """Convert to int or return None."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _classify_ownership(text: str, html_lower: str, url: str) -> tuple[str, str]:
    """Classify whether the business is independent or group-owned."""
    group_signals = []
    independent_signals = []

    # Check against known group brands
    for brand in _KNOWN_GROUP_BRANDS:
        if brand in text:
            group_signals.append(f"Known brand: {brand}")

    # Check group patterns
    for pat in _GROUP_PATTERNS:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            snippet = match.group(0)[:80]
            group_signals.append(f'Pattern: "{snippet}"')

    # Check footer specifically (often where affiliation is disclosed)
    footer_text = _extract_footer_text(html_lower)
    if footer_text:
        for pat in _GROUP_PATTERNS:
            match = re.search(pat, footer_text, re.IGNORECASE)
            if match:
                snippet = match.group(0)[:80]
                signal = f'Footer: "{snippet}"'
                if signal not in group_signals:
                    group_signals.append(signal)

    # Check for multi-location indicators in URL / text
    if re.search(r"locations?\s*(?:near|finder|search)", text):
        group_signals.append("Has location finder")
    if re.search(r"find\s+a\s+(location|office|clinic)", text):
        group_signals.append("Has location finder")

    # Check independent patterns
    for pat in _INDEPENDENT_PATTERNS:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            independent_signals.append(f'Pattern: "{match.group(0)[:60]}"')

    # Domain heuristic: generic/branded domains may signal group
    domain = urlparse(url).netloc.lower()
    domain_name = domain.replace("www.", "").split(".")[0]
    # Domains with numbers (e.g. dental365) or very generic names can signal groups
    if re.search(r"\d{3,}", domain_name):
        group_signals.append(f"Numeric domain: {domain}")

    # Decision logic
    if group_signals and not independent_signals:
        return "Group/DSO", "; ".join(group_signals)
    if independent_signals and not group_signals:
        return "Independent", "; ".join(independent_signals)
    if group_signals and independent_signals:
        # Group signals are typically more reliable
        return "Group/DSO", "; ".join(group_signals + ["(also found independent signals)"])

    return "Unknown", "No clear signals found"


def _extract_footer_text(html_lower: str) -> str:
    """Try to extract footer section text from HTML."""
    soup = BeautifulSoup(html_lower, "html.parser")
    footer = soup.find("footer")
    if footer:
        return footer.get_text(separator=" ", strip=True)
    # Fallback: look for a div with footer-like class/id
    for attr in ("id", "class"):
        el = soup.find(attrs={attr: re.compile(r"footer", re.IGNORECASE)})
        if el:
            return el.get_text(separator=" ", strip=True)
    return ""


def analyze_businesses(results: list[dict]) -> list[dict]:
    """
    Run website analysis on a list of business results.

    Adds website_score, website_issues, missed_revenue_signal, and
    ownership_type to each result dict in-place.
    """
    for i, r in enumerate(results):
        url = r.get("website", "")
        logger.info("Analyzing %d/%d: %s", i + 1, len(results), url or "(no website)")
        analysis = analyze_website(
            url,
            google_rating=r.get("google_rating"),
            review_count=r.get("review_count"),
        )
        r.update(analysis)
    return results
