#!/usr/bin/env python3
"""
Download case data from CourtListener API v4.

Usage:
    export CL_TOKEN='your-api-token'
    python scripts/download_courtlistener.py --start-date 2020-01-01 --n-cases 500
    
Get your API token from: https://www.courtlistener.com/help/api/rest/v4/
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import RAW_DATA_DIR, ensure_directories


# =============================================================================
# Configuration
# =============================================================================

CL_TOKEN = os.getenv("CL_TOKEN", "")
BASE_URL = "https://www.courtlistener.com/api/rest/v4"

SCOTUS_COURT = "scotus"
PAGE_SIZE = 100
DEFAULT_CASE_DELAY = 0.3
DEFAULT_PAGE_DELAY = 1.0

HEADERS = {
    "Authorization": f"Token {CL_TOKEN}",
    "User-Agent": "CaseLawGPT-Research/1.0",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# =============================================================================
# Utility Functions
# =============================================================================

def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def validate_date(date_str: str) -> str:
    """Validate date string is YYYY-MM-DD."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Date must be in YYYY-MM-DD format") from exc
    return date_str


# =============================================================================
# API Functions
# =============================================================================

def build_opinion_query_params(start_date: str, page_size: int) -> dict:
    """Build query params for SCOTUS opinions since start_date."""
    params = {
        "cluster__docket__court": SCOTUS_COURT,
        "fields": "id,cluster,type,html_with_citations,plain_text",
        "page_size": page_size,
        "ordering": "date_filed",
    }
    if start_date:
        # CourtListener expects filters on the cluster's filed date; include both
        # styles to avoid silent no-ops if one changes server-side.
        params["cluster__date_filed_min"] = start_date
        params["cluster__date_filed__gte"] = start_date
    return params


def fetch_count_from_url(url: str) -> int:
    """Follow CourtListener count link to get numeric total."""
    response = None
    try:
        response = SESSION.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        nested_count = data.get("count", 0)
        try:
            return int(nested_count)
        except (TypeError, ValueError):
            snippet = json.dumps(data)[:400] if isinstance(data, dict) else str(data)[:400]
            print(f"  Unexpected nested count value {nested_count!r}; response snippet: {snippet}")
            return 0
    except Exception as e:
        status = f" (HTTP {response.status_code})" if response is not None else ""
        snippet = ""
        try:
            data = response.json() if response is not None else None
            snippet = json.dumps(data)[:400] if isinstance(data, dict) else str(data)[:400]
        except Exception:
            pass
        print(f"  Error fetching count from {url}{status}: {e}. {f'Snippet: {snippet}' if snippet else ''}")
        return 0


def get_opinion_count(start_date: str) -> int:
    """Fetch total count of SCOTUS opinions on/after start_date."""
    response = None
    try:
        params = build_opinion_query_params(start_date, page_size=1)
        params["count"] = "on"
        response = SESSION.get(
            f"{BASE_URL}/opinions/",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        count_raw = data.get("count", 0)
        if isinstance(count_raw, str) and count_raw.startswith("http"):
            return fetch_count_from_url(count_raw)
        try:
            return int(count_raw)
        except (TypeError, ValueError):
            snippet = json.dumps(data)[:400] if isinstance(data, dict) else str(data)[:400]
            print(f"  Unexpected count value {count_raw!r}; response snippet: {snippet}")
            return 0
    except Exception as e:
        status = f" (HTTP {response.status_code})" if response is not None else ""
        detail = ""
        try:
            detail_json = response.json() if response is not None else None
            if isinstance(detail_json, dict) and "detail" in detail_json:
                detail = f" Detail: {detail_json.get('detail')}"
        except Exception:
            pass
        print(f"  Error fetching count for SCOTUS cases{status}: {e}.{detail}")
        return 0


def iter_scotus_opinions(
    start_date: str,
    page_size: int = PAGE_SIZE,
    page_delay: float = DEFAULT_PAGE_DELAY,
    max_retries: int = 5,
):
    """Iterate over SCOTUS opinions on/after start_date with retry/backoff."""
    next_url = f"{BASE_URL}/opinions/"
    params = build_opinion_query_params(start_date, page_size)
    while next_url:
        data = None
        for attempt in range(1, max_retries + 1):
            try:
                response = SESSION.get(next_url, params=params, timeout=45)
                response.raise_for_status()
                data = response.json()
                break
            except Exception as e:
                if attempt >= max_retries:
                    print(f"  Error fetching opinions page after {max_retries} attempts: {e}")
                    return
                delay = min(5 * attempt, 15)
                print(f"  Error fetching opinions page (attempt {attempt}/{max_retries}): {e}. Retrying in {delay}s...")
                time.sleep(delay)
                continue

        if not data:
            return

        for opinion in data.get("results", []):
            yield opinion

        next_url = data.get("next")
        params = None
        if next_url and page_delay > 0:
            time.sleep(page_delay)


def get_cluster_details(cluster_url: str) -> dict:
    """Fetch cluster (case) details."""
    try:
        response = SESSION.get(cluster_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error fetching cluster: {e}")
        return {}


def get_docket_details(docket_url: str) -> dict:
    """Fetch docket details."""
    try:
        response = SESSION.get(docket_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error fetching docket: {e}")
        return {}


# =============================================================================
# Main Download Logic
# =============================================================================

def download_cases(
    start_date: str,
    n_cases: int | None = None,
    output_dir: Path = RAW_DATA_DIR,
    auto_confirm: bool = False,
    page_size: int = PAGE_SIZE,
    case_delay: float = DEFAULT_CASE_DELAY,
    page_delay: float = DEFAULT_PAGE_DELAY,
) -> int:
    """
    Download SCOTUS cases from CourtListener API.
    
    Args:
        start_date: Earliest decision date (inclusive) in YYYY-MM-DD.
        n_cases: Optional cap on number of cases to download. Defaults to all.
        output_dir: Directory to save case JSON files.
        auto_confirm: Skip the confirmation prompt when True.
        page_size: API page size for opinions (max allowed by API is 100).
        case_delay: Sleep between cases (seconds).
        page_delay: Sleep between pages (seconds).
        
    Returns:
        Number of cases successfully downloaded.
    """
    ensure_directories()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not CL_TOKEN:
        print("=" * 60)
        print("ERROR: No CL_TOKEN environment variable set!")
        print()
        print("To fix:")
        print("1. Register at https://www.courtlistener.com/register/")
        print("2. Get token from https://www.courtlistener.com/help/api/rest/v4/")
        print("3. Run: export CL_TOKEN='your-token-here'")
        print("=" * 60)
        return 0
    
    saved = 0
    seen_ids = set()
    
    # Check for existing cases
    for f in output_dir.glob("*.json"):
        seen_ids.add(f.stem)
    
    total_available = get_opinion_count(start_date)
    if total_available <= 0:
        print(f"No SCOTUS cases found on/after {start_date}. Nothing to do.")
        return 0

    target_total = total_available if n_cases is None else min(total_available, n_cases)
    if target_total <= 0:
        print("Target case count is zero after applying filters. Nothing to download.")
        return 0

    print(f"Query matches {total_available} SCOTUS cases on/after {start_date}.")
    if n_cases is not None and n_cases < total_available:
        print(f"Limiting download to first {target_total} cases.")
    print(f"Found {len(seen_ids)} existing cases in {output_dir} (will skip duplicates).")

    if not auto_confirm:
        proceed = input(f"Continue and download up to {target_total} cases? [y/N]: ").strip().lower()
        if proceed not in {"y", "yes"}:
            print("Aborted by user.")
            return 0
    else:
        print("Auto-confirm enabled; proceeding without prompt.")

    skipped = {
        "duplicate_or_missing_id": 0,
        "short_text": 0,
        "missing_cluster": 0,
        "missing_docket": 0,
        "other": 0,
    }

    for opinion in iter_scotus_opinions(start_date, page_size=page_size, page_delay=page_delay):
        if saved >= target_total:
            break
        
        opinion_id = opinion.get("id")
        case_id = f"cl-{opinion_id}"
        
        if case_id in seen_ids or not opinion_id:
            skipped["duplicate_or_missing_id"] += 1
            continue
        
        # Get opinion text
        text = opinion.get("html_with_citations") or opinion.get("plain_text") or ""
        text = strip_html(text)
        
        if len(text) < 500:
            skipped["short_text"] += 1
            continue
        
        # Get cluster info
        cluster_url = opinion.get("cluster")
        if not cluster_url:
            skipped["missing_cluster"] += 1
            continue
        
        cluster = get_cluster_details(cluster_url)
        if not cluster:
            skipped["missing_cluster"] += 1
            continue
        
        # Get docket info
        docket_url = cluster.get("docket")
        docket = get_docket_details(docket_url) if docket_url else {}
        if not docket:
            skipped["missing_docket"] += 1
        
        # Extract citation
        citations = cluster.get("citations", [])
        cite_str = citations[0].get("cite", "") if citations else ""
        
        # Normalize opinion type
        opinion_type = opinion.get("type", "010combined")
        if "dissent" in opinion_type.lower():
            opinion_type_clean = "dissenting"
        elif "concur" in opinion_type.lower():
            opinion_type_clean = "concurring"
        else:
            opinion_type_clean = "majority"
        
        # Format for ingestion
        case_data = {
            "id": case_id,
            "name": cluster.get("case_name", "Unknown"),
            "name_abbreviation": cluster.get(
                "case_name_short", 
                cluster.get("case_name", "")[:100]
            ),
            "citations": [{"cite": cite_str}],
            "court": {"name": docket.get("court_id", SCOTUS_COURT)},
            "jurisdiction": {"name": "United States"},
            "decision_date": cluster.get("date_filed", ""),
            "casebody": {
                "opinions": [{"type": opinion_type_clean, "text": text}]
            },
        }
        
        # Save to file
        filepath = output_dir / f"{case_id}.json"
        with open(filepath, "w") as f:
            json.dump(case_data, f, indent=2)
        
        seen_ids.add(case_id)
        saved += 1
        print(f"  [{saved}] {case_data['name'][:60]}")
        
        if case_delay > 0:
            time.sleep(case_delay)  # Rate limiting

    print(f"\nDone! Downloaded {saved} cases to {output_dir}")
    print("Skip summary:", skipped)
    return saved


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download SCOTUS cases from CourtListener API"
    )
    parser.add_argument(
        "--start-date",
        required=True,
        type=validate_date,
        help="Earliest decision date (inclusive) in YYYY-MM-DD",
    )
    parser.add_argument(
        "--n-cases",
        type=int,
        default=None,
        help="Optional cap on number of cases to download (default: all matching)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Output directory for case files",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=PAGE_SIZE,
        help="API page size (max 100)",
    )
    parser.add_argument(
        "--case-delay",
        type=float,
        default=DEFAULT_CASE_DELAY,
        help="Delay between cases in seconds (set 0 for fastest)",
    )
    parser.add_argument(
        "--page-delay",
        type=float,
        default=DEFAULT_PAGE_DELAY,
        help="Delay between pages in seconds (set 0 for fastest)",
    )
    
    args = parser.parse_args()
    download_cases(
        start_date=args.start_date,
        n_cases=args.n_cases,
        output_dir=args.output_dir,
        auto_confirm=args.yes,
        page_size=args.page_size,
        case_delay=args.case_delay,
        page_delay=args.page_delay,
    )
