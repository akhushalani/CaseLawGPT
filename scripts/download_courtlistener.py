#!/usr/bin/env python3
"""
Download case data from CourtListener API v4.

Usage:
    export CL_TOKEN='your-api-token'
    python scripts/download_courtlistener.py --n-cases 500
    
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

import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import RAW_DATA_DIR, ensure_directories


# =============================================================================
# Configuration
# =============================================================================

CL_TOKEN = os.getenv("CL_TOKEN", "")
BASE_URL = "https://www.courtlistener.com/api/rest/v4"

# Federal courts to fetch from
COURTS = [
    "scotus",  # Supreme Court
    "ca1", "ca2", "ca3", "ca4", "ca5",  # Circuit Courts
    "ca6", "ca7", "ca8", "ca9", "ca10", "ca11",
]

HEADERS = {
    "Authorization": f"Token {CL_TOKEN}",
    "User-Agent": "CaseLawGPT-Research/1.0",
}


# =============================================================================
# Utility Functions
# =============================================================================

def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# =============================================================================
# API Functions
# =============================================================================

def get_opinions_by_court(court: str, page_size: int = 20) -> list[dict]:
    """Fetch opinions from a specific court."""
    try:
        response = requests.get(
            f"{BASE_URL}/opinions/",
            params={
                "cluster__docket__court": court,
                "fields": "id,cluster,type,html_with_citations,plain_text",
                "page_size": page_size,
            },
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        print(f"  Error fetching opinions for {court}: {e}")
        return []


def get_cluster_details(cluster_url: str) -> dict:
    """Fetch cluster (case) details."""
    try:
        response = requests.get(cluster_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error fetching cluster: {e}")
        return {}


def get_docket_details(docket_url: str) -> dict:
    """Fetch docket details."""
    try:
        response = requests.get(docket_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error fetching docket: {e}")
        return {}


# =============================================================================
# Main Download Logic
# =============================================================================

def download_cases(n_cases: int = 300, output_dir: Path = RAW_DATA_DIR) -> int:
    """
    Download cases from CourtListener API.
    
    Args:
        n_cases: Target number of cases to download.
        output_dir: Directory to save case JSON files.
        
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
    
    print(f"Found {len(seen_ids)} existing cases")
    print(f"Downloading up to {n_cases} cases from CourtListener...\n")
    
    cases_per_court = max(1, n_cases // len(COURTS))
    
    for court in COURTS:
        if saved >= n_cases:
            break
        
        print(f"Fetching from {court}...")
        opinions = get_opinions_by_court(court, page_size=cases_per_court)
        
        for opinion in opinions:
            if saved >= n_cases:
                break
            
            opinion_id = opinion.get("id")
            case_id = f"cl-{opinion_id}"
            
            if case_id in seen_ids or not opinion_id:
                continue
            
            # Get opinion text
            text = opinion.get("html_with_citations") or opinion.get("plain_text") or ""
            text = strip_html(text)
            
            if len(text) < 500:
                continue
            
            # Get cluster info
            cluster_url = opinion.get("cluster")
            if not cluster_url:
                continue
            
            cluster = get_cluster_details(cluster_url)
            if not cluster:
                continue
            
            # Get docket info
            docket_url = cluster.get("docket")
            docket = get_docket_details(docket_url) if docket_url else {}
            
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
                "court": {"name": docket.get("court_id", court)},
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
            
            time.sleep(0.3)  # Rate limiting
        
        time.sleep(1)
    
    print(f"\nDone! Downloaded {saved} cases to {output_dir}")
    return saved


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download cases from CourtListener API"
    )
    parser.add_argument(
        "--n-cases",
        type=int,
        default=300,
        help="Number of cases to download",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help="Output directory for case files",
    )
    
    args = parser.parse_args()
    download_cases(args.n_cases, args.output_dir)