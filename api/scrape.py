"""Vercel serverless function — scrapes an Airbnb listing URL."""
import json
import re
from http.server import BaseHTTPRequestHandler

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
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
    match = re.search(r'/rooms/(\d+)', url)
    if not match:
        return {"error": "Invalid Airbnb URL"}

    listing_id = match.group(1)
    clean_url = f"https://www.airbnb.ca/rooms/{listing_id}"

    try:
        resp = requests.get(clean_url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Failed to fetch: {e}"}

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    data = None
    for sid in ["data-deferred-state-0", "data-deferred-state", "data-state"]:
        tag = soup.find("script", id=sid)
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

    photos = []
    if data:
        for u in deep_search(data, "baseUrl"):
            if isinstance(u, str) and "muscache.com" in u:
                clean = re.sub(r'\?.*', '', u)
                if clean not in photos and PLATFORM_ASSET not in clean and REVIEW_ASSET not in clean:
                    photos.append(clean + "?im_w=720")
    if not photos:
        for meta in soup.find_all("meta", property="og:image"):
            u = meta.get("content", "")
            if u:
                photos.append(u)

    title = ""
    title_tag = soup.find("meta", property="og:title")
    if title_tag:
        title = title_tag.get("content", "").split(" - ")[0].strip()
    elif soup.title:
        title = soup.title.string.split(" - ")[0].strip()

    location = ""
    if title_tag:
        parts = title_tag.get("content", "").split(" - ")
        if len(parts) > 1:
            location = parts[-1].strip()

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

    guests, rating, reviews = 10, 0, 0
    if data:
        g = deep_search(data, "personCapacity")
        if g and isinstance(g[0], int):
            guests = g[0]
        r = deep_search(data, "overallRating")
        if r and r[0]:
            rating = r[0]
        rc = deep_search(data, "reviewCount")
        if rc:
            reviews = rc[0]

    amenities = {"🛁 Hot Tub": False, "🏊 Lake": False, "🔥 Fire Pit": False, "🍖 BBQ": False, "🛶 Dock": False, "🧖 Sauna": False}
    if data:
        for a in deep_search(data, "title"):
            if not isinstance(a, str) or len(a) > 50:
                continue
            al = a.lower()
            if "hot tub" in al: amenities["🛁 Hot Tub"] = True
            if "lake" in al: amenities["🏊 Lake"] = True
            if "fire pit" in al: amenities["🔥 Fire Pit"] = True
            if "bbq" in al or "grill" in al: amenities["🍖 BBQ"] = True
            if "dock" in al: amenities["🛶 Dock"] = True
            if "sauna" in al: amenities["🧖 Sauna"] = True

    nice_title = title.split("·")[0].strip() if "·" in title else title

    return {
        "success": True,
        "listing_id": listing_id,
        "title": nice_title,
        "location": location or "Ontario, ON",
        "beds": beds, "baths": baths, "guests": guests,
        "rating": rating, "reviews": reviews,
        "amenities": amenities,
        "photos": photos[:10],
        "url": clean_url,
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._json(400, {"error": "Invalid JSON"})
            return

        url = payload.get("url", "").strip()
        if not url or "/rooms/" not in url:
            self._json(400, {"error": "Provide a valid Airbnb listing URL"})
            return

        result = scrape_airbnb(url)
        self._json(500 if "error" in result else 200, result)

    def _json(self, code, data):
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
