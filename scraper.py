#!/usr/bin/env python3
"""
Airbnb Listing Scraper for Squad Cottage Trip 2026
Scrapes photos and listing details from Airbnb URLs.
Outputs JSON ready to paste into index.html LISTINGS array.

Usage:
  pip install requests beautifulsoup4
  python scraper.py
  python scraper.py --url https://www.airbnb.ca/rooms/12345  # single listing
  python scraper.py --download-photos                         # also download images
"""

import argparse
import json
import os
import re
import sys
import time
import random
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Run:\n  pip install requests beautifulsoup4")
    sys.exit(1)


# ── All 8 listing URLs from CLAUDE.md ──────────────────────────────────────────
DEFAULT_URLS = [
    ("Georgian Bay A-Frame",        "https://www.airbnb.ca/rooms/1322779723776332921"),
    ("Lakefront Escape",            "https://www.airbnb.ca/rooms/1356182272072783043"),
    ("Muskoka Manor",               "https://www.airbnb.ca/rooms/40613745"),
    ("Blue Mountains Retreat",      "https://www.airbnb.ca/rooms/1573396745294436058"),
    ("Sauble Beach Stunner",        "https://www.airbnb.ca/rooms/1385001401644874562"),
    ("Grand Bend Beachfront",       "https://www.airbnb.ca/rooms/581182022418368306"),
    ("The One — Grand Bend Estate", "https://www.airbnb.ca/rooms/1321080002066299067"),
    ("Kawartha Lakes Hideaway",     "https://www.airbnb.ca/rooms/1504300619694699840"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}

PHOTO_DIR = "photos"


def fetch_page(url: str) -> str | None:
    """Fetch raw HTML from an Airbnb listing page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  ✗ Failed to fetch: {e}")
        return None


def extract_deferred_state(html: str) -> dict | None:
    """Extract the big JSON blob Airbnb embeds in a <script id='data-deferred-state-0'> tag."""
    soup = BeautifulSoup(html, "html.parser")

    # Primary: data-deferred-state-0 (most common)
    for script_id in ["data-deferred-state-0", "data-deferred-state", "data-state"]:
        tag = soup.find("script", id=script_id)
        if tag and tag.string:
            try:
                return json.loads(tag.string)
            except json.JSONDecodeError:
                continue

    # Fallback: search all script tags for large JSON blobs containing listing data
    for tag in soup.find_all("script", type="application/json"):
        if tag.string and len(tag.string) > 5000:
            try:
                data = json.loads(tag.string)
                return data
            except json.JSONDecodeError:
                continue

    return None


def deep_search(obj, key, results=None):
    """Recursively search a nested dict/list for all values matching a key."""
    if results is None:
        results = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                results.append(v)
            deep_search(v, key, results)
    elif isinstance(obj, list):
        for item in obj:
            deep_search(item, key, results)
    return results


def extract_photos_from_json(data: dict) -> list[str]:
    """Pull photo URLs from the deferred state JSON."""
    photos = []

    # Look for photo URLs in common Airbnb JSON structures
    # They typically appear under keys like 'baseUrl', 'url' with image dimensions
    base_urls = deep_search(data, "baseUrl")
    for url in base_urls:
        if isinstance(url, str) and ("muscache.com" in url or "airbnbimg" in url):
            # Normalize to a good resolution
            clean = re.sub(r'\?.*', '', url)
            if clean not in photos:
                photos.append(clean)

    # Also check 'url' keys that look like photos
    if not photos:
        all_urls = deep_search(data, "url")
        for url in all_urls:
            if isinstance(url, str) and ("muscache.com" in url or "airbnbimg" in url):
                clean = re.sub(r'\?.*', '', url)
                if clean not in photos:
                    photos.append(clean)

    return photos[:20]  # cap at 20 photos


def extract_photos_from_html(html: str) -> list[str]:
    """Fallback: extract photo URLs from meta tags and img elements."""
    soup = BeautifulSoup(html, "html.parser")
    photos = []

    # og:image meta tags
    for meta in soup.find_all("meta", property="og:image"):
        url = meta.get("content", "")
        if url and url not in photos:
            photos.append(url)

    # img tags with airbnb CDN sources
    for img in soup.find_all("img"):
        src = img.get("src", "") or img.get("data-src", "")
        if src and ("muscache.com" in src or "airbnbimg" in src):
            clean = re.sub(r'\?.*', '', src)
            if clean not in photos:
                photos.append(clean)

    return photos[:20]


def extract_listing_details(data: dict, html: str) -> dict:
    """Extract structured listing info (beds, baths, price, etc.)."""
    info = {}
    soup = BeautifulSoup(html, "html.parser")

    # Title from <title> or og:title
    title_tag = soup.find("meta", property="og:title")
    if title_tag:
        info["title"] = title_tag.get("content", "").split(" - ")[0].strip()
    elif soup.title:
        info["title"] = soup.title.string.split(" - ")[0].strip()

    # Description
    desc_tag = soup.find("meta", property="og:description")
    if desc_tag:
        info["description"] = desc_tag.get("content", "")

    # Location from og:title (usually "Title - Location")
    if title_tag:
        parts = title_tag.get("content", "").split(" - ")
        if len(parts) > 1:
            info["location"] = parts[-1].strip()

    # Try to pull structured data from JSON
    if data:
        # Beds
        beds = deep_search(data, "bedCount")
        if beds:
            info["beds"] = beds[0] if isinstance(beds[0], int) else None

        # Baths
        baths = deep_search(data, "bathroomCount")
        if baths:
            info["baths"] = baths[0] if isinstance(baths[0], (int, float)) else None

        # Guests
        guests = deep_search(data, "personCapacity")
        if guests:
            info["guests"] = guests[0] if isinstance(guests[0], int) else None

        # Rating
        ratings = deep_search(data, "overallRating")
        if ratings:
            info["rating"] = ratings[0]

        # Review count
        review_counts = deep_search(data, "reviewCount")
        if review_counts:
            info["reviews"] = review_counts[0]

        # Price
        prices = deep_search(data, "priceString")
        if prices and isinstance(prices[0], str):
            nums = re.findall(r'[\d,]+', prices[0])
            if nums:
                info["price_per_night"] = int(nums[0].replace(",", ""))

        if "price_per_night" not in info:
            prices = deep_search(data, "price")
            for p in prices:
                if isinstance(p, (int, float)) and 50 < p < 5000:
                    info["price_per_night"] = int(p)
                    break

        # Amenities
        amenity_names = deep_search(data, "title")
        amenity_list = [a for a in amenity_names if isinstance(a, str) and len(a) < 50]
        amenity_keywords = {
            "Hot tub": "🛁 Hot Tub",
            "hot tub": "🛁 Hot Tub",
            "Lake": "🏊 Lake",
            "Lakefront": "🏊 Lake",
            "lake access": "🏊 Lake",
            "Fire pit": "🔥 Fire Pit",
            "fire pit": "🔥 Fire Pit",
            "BBQ": "🍖 BBQ",
            "bbq": "🍖 BBQ",
            "grill": "🍖 BBQ",
            "Dock": "🛶 Dock",
            "dock": "🛶 Dock",
            "Sauna": "🧖 Sauna",
            "sauna": "🧖 Sauna",
        }
        found_amenities = {}
        for a in amenity_list:
            for keyword, label in amenity_keywords.items():
                if keyword.lower() in a.lower():
                    found_amenities[label] = True
        if found_amenities:
            info["amenities"] = found_amenities

    return info


def download_photos(photos: list[str], listing_id: str) -> list[str]:
    """Download photos to local directory, return local paths."""
    listing_dir = os.path.join(PHOTO_DIR, listing_id)
    os.makedirs(listing_dir, exist_ok=True)
    local_paths = []

    for i, url in enumerate(photos):
        ext = ".jpg"
        filename = f"photo_{i+1}{ext}"
        filepath = os.path.join(listing_dir, filename)

        if os.path.exists(filepath):
            local_paths.append(filepath)
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
            local_paths.append(filepath)
            print(f"    ↓ {filename} ({len(resp.content)//1024}KB)")
        except requests.RequestException as e:
            print(f"    ✗ Failed to download photo {i+1}: {e}")

    return local_paths


def scrape_listing(url: str, label: str, do_download: bool = False) -> dict:
    """Scrape a single Airbnb listing."""
    print(f"\n{'─'*60}")
    print(f"  Scraping: {label}")
    print(f"  URL: {url}")

    # Extract listing ID from URL
    match = re.search(r'/rooms/(\d+)', url)
    listing_id = match.group(1) if match else "unknown"

    html = fetch_page(url)
    if not html:
        return {"id": listing_id, "url": url, "label": label, "error": "Failed to fetch"}

    # Try JSON extraction first
    data = extract_deferred_state(html)
    if data:
        print("  ✓ Found embedded JSON data")
    else:
        print("  ⚠ No embedded JSON — falling back to HTML parsing")

    # Extract photos
    photos = []
    if data:
        photos = extract_photos_from_json(data)
    if not photos:
        photos = extract_photos_from_html(html)
    print(f"  📷 Found {len(photos)} photos")

    # Extract listing details
    details = extract_listing_details(data or {}, html)
    print(f"  📋 Extracted fields: {', '.join(details.keys()) or 'none'}")

    # Download photos if requested
    local_photos = []
    if do_download and photos:
        print(f"  ↓ Downloading photos to {PHOTO_DIR}/{listing_id}/")
        local_photos = download_photos(photos, listing_id)

    result = {
        "listing_id": listing_id,
        "url": url,
        "label": label,
        "photos": photos,
        **details,
    }
    if local_photos:
        result["local_photos"] = local_photos

    return result


def main():
    parser = argparse.ArgumentParser(description="Scrape Airbnb listings for cottage trip")
    parser.add_argument("--url", type=str, help="Scrape a single URL instead of all defaults")
    parser.add_argument("--download-photos", action="store_true", help="Download photos locally")
    parser.add_argument("--output", type=str, default="scraped_listings.json", help="Output JSON file")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between requests (seconds)")
    args = parser.parse_args()

    print("🏕️  Airbnb Scraper — Squad Cottage Trip 2026")
    print("=" * 60)

    if args.url:
        urls = [("Custom Listing", args.url)]
    else:
        urls = DEFAULT_URLS

    results = []
    for i, (label, url) in enumerate(urls):
        result = scrape_listing(url, label, do_download=args.download_photos)
        results.append(result)

        # Polite delay between requests
        if i < len(urls) - 1:
            delay = args.delay + random.uniform(0, 2)
            print(f"  ⏳ Waiting {delay:.1f}s...")
            time.sleep(delay)

    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ Done! Results saved to {args.output}")
    print(f"   {len(results)} listings scraped")

    total_photos = sum(len(r.get("photos", [])) for r in results)
    print(f"   {total_photos} total photo URLs found")

    # Print quick summary
    print(f"\n{'─'*60}")
    print("Summary:")
    for r in results:
        photo_count = len(r.get("photos", []))
        price = r.get("price_per_night", "?")
        guests = r.get("guests", "?")
        rating = r.get("rating", "?")
        print(f"  {r['label']:<30} | ${price}/night | {guests} guests | ★{rating} | {photo_count} photos")


if __name__ == "__main__":
    main()
