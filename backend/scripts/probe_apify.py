"""One-off exploration: call apify/facebook-ads-scraper for Bellroy and dump raw output.

Purpose: inspect actual field names before writing normalization code.
Run: from backend/, `uv run python -m scripts.probe_apify`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from apify_client import ApifyClient

# Import our settings so the API token comes from .env
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings  # noqa: E402


ACTOR_ID = "apify/facebook-ads-scraper"

INPUT = {
    "startUrls": [
        {"url": "https://www.facebook.com/bellroy.official/"}
    ],
    "resultsLimit": 2,
    "isDetailsPerAd": False,
    "includeAboutPage": False,
    "onlyTotal": False,
}

OUTPUT_PATH = Path(__file__).parent / "probe_output.json"


def main() -> None:
    client = ApifyClient(settings.apify_api_token)

    print(f"Calling actor {ACTOR_ID} with input:")
    print(json.dumps(INPUT, indent=2))
    print("\nThis can take 30-90 seconds. Waiting for run to finish...")

    run = client.actor(ACTOR_ID).call(run_input=INPUT)

    if run is None:
        raise RuntimeError("Apify actor run returned None")

    print(f"\nRun finished. Status: {run.get('status')}")
    print(f"Dataset ID: {run.get('defaultDatasetId')}")

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"\nTotal items in dataset: {len(items)}")

    if not items:
        print("\n⚠  Zero items returned. Check the startUrls and actor run logs in Apify Console.")
        return

    OUTPUT_PATH.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved full output to: {OUTPUT_PATH}")

    print("\n--- First item (pretty-printed) ---")
    print(json.dumps(items[0], indent=2, default=str)[:5000])
    print("\n... (truncated if over 5000 chars; full content is in probe_output.json)")


if __name__ == "__main__":
    main()