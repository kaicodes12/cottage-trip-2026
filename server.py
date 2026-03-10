#!/usr/bin/env python3
"""
Cottage Trip Server — serves the site + provides a /api/scrape endpoint
for adding new Airbnb listings on the fly.

Usage: python3 server.py
Then open http://localhost:8080
"""

import http.server
import json
import os
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup

PORT = 8080
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

PLATFORM_ASSET = "adafb11b-41e9-49d3-908e-049dfd6934b6"
REVIEW_ASSET = "AirbnbPlatformAssets"


def deep_search(obj, key, results=None):
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


def scrape_airbnb(url):
    """Scrape an Airbnb listing and return structured data."""
    # Normalize URL to just the /rooms/ID part
    match = re.search(r'/rooms/(\d+)', url)
    if not match:
        return {"error": "Invalid Airbnb URL. Must contain /rooms/<id>"}

    listing_id = match.group(1)
    clean_url = f"https://www.airbnb.ca/rooms/{listing_id}"

    try:
        resp = requests.get(clean_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Failed to fetch listing: {e}"}

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Extract JSON data
    data = None
    for script_id in ["data-deferred-state-0", "data-deferred-state", "data-state"]:
        tag = soup.find("script", id=script_id)
        if tag and tag.string:
            try:
                data = json.loads(tag.string)
                break
            except json.JSONDecodeError:
                continue

    if not data:
        for tag in soup.find_all("script", type="application/json"):
            if tag.string and len(tag.string) > 5000:
                try:
                    data = json.loads(tag.string)
                    break
                except json.JSONDecodeError:
                    continue

    # Extract photos
    photos = []
    if data:
        base_urls = deep_search(data, "baseUrl")
        for u in base_urls:
            if isinstance(u, str) and ("muscache.com" in u or "airbnbimg" in u):
                clean = re.sub(r'\?.*', '', u)
                if clean not in photos and PLATFORM_ASSET not in clean and REVIEW_ASSET not in clean:
                    photos.append(clean + "?im_w=720")

    if not photos:
        for meta in soup.find_all("meta", property="og:image"):
            u = meta.get("content", "")
            if u:
                photos.append(u)
        for img in soup.find_all("img"):
            src = img.get("src", "") or img.get("data-src", "")
            if src and ("muscache.com" in src or "airbnbimg" in src):
                clean = re.sub(r'\?.*', '', src)
                if clean not in photos and PLATFORM_ASSET not in clean:
                    photos.append(clean + "?im_w=720")

    photos = photos[:10]

    # Extract title
    title = ""
    title_tag = soup.find("meta", property="og:title")
    if title_tag:
        title = title_tag.get("content", "").split(" - ")[0].strip()
    elif soup.title:
        title = soup.title.string.split(" - ")[0].strip()

    # Extract location
    location = ""
    if title_tag:
        parts = title_tag.get("content", "").split(" - ")
        if len(parts) > 1:
            location = parts[-1].strip()

    # Parse beds/baths from title
    beds = 4
    baths = 2
    m = re.search(r'(\d+)\s*bedroom', title)
    if m:
        beds = int(m.group(1))
    m = re.search(r'([\d.]+)\s*bath', title)
    if m:
        baths = float(m.group(1))
        if baths == int(baths):
            baths = int(baths)

    # Extract from JSON
    guests = 10
    rating = None
    reviews = 0

    if data:
        g = deep_search(data, "personCapacity")
        if g and isinstance(g[0], int):
            guests = g[0]

        r = deep_search(data, "overallRating")
        if r:
            rating = r[0]

        rc = deep_search(data, "reviewCount")
        if rc:
            reviews = rc[0]

    if rating is None:
        rating = 0

    # Amenities
    amenities = {
        "🛁 Hot Tub": False,
        "🏊 Lake": False,
        "🔥 Fire Pit": False,
        "🍖 BBQ": False,
        "🛶 Dock": False,
        "🧖 Sauna": False,
    }
    if data:
        amenity_titles = deep_search(data, "title")
        for a in amenity_titles:
            if not isinstance(a, str) or len(a) > 50:
                continue
            al = a.lower()
            if "hot tub" in al:
                amenities["🛁 Hot Tub"] = True
            if "lake" in al or "lakefront" in al:
                amenities["🏊 Lake"] = True
            if "fire pit" in al:
                amenities["🔥 Fire Pit"] = True
            if "bbq" in al or "grill" in al:
                amenities["🍖 BBQ"] = True
            if "dock" in al:
                amenities["🛶 Dock"] = True
            if "sauna" in al:
                amenities["🧖 Sauna"] = True

    # Simplify title (remove "Cottage in X · ★4.9 · 3 bedrooms..." → just a nice name)
    nice_title = title
    if "·" in title:
        # Like "Cottage in Port Franks · ★5.0 · 3 bedrooms · 4 beds · 2 baths"
        parts = [p.strip() for p in title.split("·")]
        # Use the first part as the title
        nice_title = parts[0]

    return {
        "success": True,
        "listing_id": listing_id,
        "title": nice_title,
        "location": location or "Ontario, ON",
        "beds": beds,
        "baths": baths,
        "guests": guests,
        "rating": rating,
        "reviews": reviews,
        "amenities": amenities,
        "photos": photos,
        "url": clean_url,
    }


class CottageHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/scrape":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            url = payload.get("url", "").strip()
            if not url or "/rooms/" not in url:
                self.send_json(400, {"error": "Please provide a valid Airbnb listing URL"})
                return

            print(f"  Scraping: {url}")
            result = scrape_airbnb(url)

            if "error" in result:
                self.send_json(500, result)
            else:
                print(f"  ✓ {result['title']} — {len(result['photos'])} photos")
                self.send_json(200, result)
        else:
            self.send_json(404, {"error": "Not found"})

    def send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        # Quieter logging — skip static file requests
        if "POST" in str(args):
            super().log_message(format, *args)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with http.server.HTTPServer(("", PORT), CottageHandler) as httpd:
        print(f"🏕️  Cottage Trip Server running at http://localhost:{PORT}")
        print(f"   Serving files from {os.getcwd()}")
        print(f"   API endpoint: POST /api/scrape")
        print()
        httpd.serve_forever()
