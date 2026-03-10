# 🏕️ Squad Cottage Trip 2026 — Project Brief

This is a single-page web app for a group of ~10 friends planning a 3-night Ontario cottage trip in June 2026. The site helps the squad browse, vote on, react to, and compare Airbnb listings — all in one shareable HTML file.

---

## 🗂️ Project Structure

```
cottage-trip-project/
├── index.html        ← The entire app (single-file, no dependencies except Google Fonts)
└── CLAUDE.md         ← This file
```

---

## 🎨 Design System

**Aesthetic:** Warm cottage-core — earthy, cozy, editorial. Inspired by Ontario wilderness and cabin life.

**Fonts (Google Fonts):**
- `Lora` — serif display font for headings and prices
- `Nunito` — sans-serif body font for UI, labels, buttons

**Color Palette (CSS variables in `:root`):**
| Variable | Value | Usage |
|---|---|---|
| `--cream` | `#faf5ec` | Page background |
| `--parchment` | `#f0e8d5` | Section backgrounds, amenity bg |
| `--bark` | `#6b4c36` | Dark brown text, accents |
| `--bark-light` | `#9b7456` | Softer brown |
| `--forest` | `#2c4a34` | Primary dark green (nav, footer, headers) |
| `--forest-light` | `#3d6347` | Lighter green |
| `--moss` | `#5a7a4a` | Amenity checkmarks |
| `--rust` | `#b5491e` | CTA buttons, area labels, accents |
| `--rust-light` | `#d4622d` | Hover state for rust |
| `--gold` | `#c9913d` | Leaderboard bars, badges |
| `--gold-light` | `#e2b05a` | Hero accent, nav labels |
| `--lake` | `#4a7fa0` | Compare mode, per-person price |
| `--lake-light` | `#6ba3c0` | Compare hover |
| `--sand` | `#e8d9bc` | Card borders, dividers |
| `--mist` | `#e8efe4` | Vibe tag backgrounds |
| `--charcoal` | `#2a2a28` | Compare panel background |
| `--text` | `#3a3028` | Main body text |
| `--text-soft` | `#7a6a58` | Secondary text |
| `--card-bg` | `#fffdf8` | Card background |

---

## ⚙️ Architecture

**Single HTML file** — no build tool, no bundler, no npm. Paste into any browser or VS Code Live Server.

**State (plain JS objects at top of `<script>`):**
- `LISTINGS` — array of 8 listing objects (the source of truth)
- `groupSize` — integer, default 10 (adjustable in nav)
- `sortMode` — `'default' | 'votes' | 'price' | 'kais'`
- `compareMode` — boolean, toggles compare UI
- `compareSelected` — array of up to 3 listing IDs
- `votes` — `{ [id]: 'up' | 'down' | null }`
- `saved` — `{ [id]: boolean }`
- `reactions` — `{ [id]: { [emoji]: count, myReacts: Set } }`
- `comments` — `{ [id]: string[] }`
- `photoIdx` — `{ [id]: number }` (current gallery photo index)

**Key functions:**
- `render()` — full re-render of listings grid + leaderboard
- `renderCard(listing, delay)` — returns HTML string for one card
- `renderLeaderboard()` — updates the vote leaderboard section
- `buildHero()` — injects hero slideshow slides + dots
- `buildMap()` — draws SVG pins on the Ontario map
- `doVote(id, dir)` — toggles vote, calls render()
- `toggleCompareMode()` — toggles compare UI state
- `openCompare()` — builds + shows the compare modal
- `openLightbox(id, idx)` — opens fullscreen photo viewer
- `changeGroup(delta)` — adjusts groupSize, updates per-person prices inline

---

## 🏠 Listings Data (`LISTINGS` array)

Each listing object has this shape:

```js
{
  id: Number,
  title: String,
  area: String,          // e.g. "Grand Bend"
  location: String,      // e.g. "Grand Bend, ON"
  beds: Number,
  baths: Number,
  guests: Number,        // max capacity
  price: Number,         // per night in CAD
  rating: Number,        // e.g. 4.92
  reviews: Number,
  driveHr: String,       // e.g. "2h 25m"
  driveColor: String,    // hex — green/gold/red based on drive time
  kaisPick: Boolean,     // true = gets ⭐ Kai's Pick badge
  mapX: Number,          // SVG x coordinate on the Ontario map (0–800)
  mapY: Number,          // SVG y coordinate on the Ontario map (0–400)
  vibes: String[],       // e.g. ["🏖️ Beachfront", "♨️ Hot Tub"]
  amenities: {           // key = display label, value = boolean
    "🛁 Hot Tub": Boolean,
    "🏊 Lake": Boolean,
    "🔥 Fire Pit": Boolean,
    "🍖 BBQ": Boolean,
    "🛶 Dock": Boolean,
    "🧖 Sauna": Boolean,
  },
  url: String,           // Airbnb listing URL
  photos: String[],      // Array of image URLs (currently Unsplash placeholders)
}
```

**The 8 listings:**
1. Georgian Bay A-Frame — Tiny Township (no kaisPick)
2. Lakefront Escape — Wasaga Beach (no kaisPick)
3. The Muskoka Manor — Gravenhurst (no kaisPick) — most amenities, highest price
4. Blue Mountains Retreat — Collingwood (no kaisPick)
5. Sauble Beach Stunner — Sauble Beach (**kaisPick = true**)
6. Grand Bend Beachfront — Grand Bend (no kaisPick)
7. The One — Grand Bend Estate — Grand Bend (**kaisPick = true**, Kai's #1)
8. Kawartha Lakes Hideaway — Fenelon Falls (no kaisPick)

**Seeded vote counts** (`SEED_VOTES` object):
- Listing 7 (The One): +6 votes
- Listing 5 (Sauble Beach): +3 votes
- Listing 3 (Muskoka): +2 votes
- Listings 6, 2: +1 vote each

---

## ✨ Features Checklist

| Feature | Status |
|---|---|
| Hero with auto-playing ambient slideshow | ✅ |
| Grain texture overlay | ✅ |
| Sticky nav with sort controls | ✅ |
| Group size adjuster (affects per-person price) | ✅ |
| Interactive Ontario SVG map with hover tooltips | ✅ |
| Drive time from Toronto on map + cards | ✅ |
| Listing cards with photo gallery (arrows + dots) | ✅ |
| Fullscreen photo lightbox (keyboard navigable) | ✅ |
| Vibe tags per listing | ✅ |
| Amenity checklist (hot tub, lake, BBQ, etc.) | ✅ |
| Per-person/per-night price calculator | ✅ |
| Total 3-night cost per listing | ✅ |
| 👍/👎 voting with live tally | ✅ |
| Emoji reaction strip with click-to-react | ✅ |
| Comment/note input per listing | ✅ |
| Save/wishlist toggle (❤️) | ✅ |
| ⭐ Kai's Pick badges | ✅ |
| 🏆 Squad Fave badge (auto when votes ≥ 4) | ✅ |
| Vote leaderboard section | ✅ |
| Compare mode (select 2–3 listings) | ✅ |
| Side-by-side compare modal with best-value highlights | ✅ |
| Sort by: default / top voted / cheapest / Kai's picks | ✅ |

---

## 🔧 Suggested Next Steps (for VS Code)

### 1. Replace placeholder photos with real Airbnb photos
In `LISTINGS`, each listing has a `photos: []` array currently using Unsplash URLs. Replace these with actual screenshots or downloaded photos from the Airbnb listings.

### 2. Refine listing data
Update `price`, `beds`, `baths`, `guests`, `rating`, `reviews`, `driveHr`, `amenities` with the exact real values from each Airbnb listing page.

### 3. Adjust map pin positions
The `mapX` and `mapY` values on each listing are approximate positions on the SVG map. Tune these to better match real geography.

### 4. Split into components (optional)
If you want to grow this into a proper project, consider splitting into:
- `index.html` — shell
- `styles.css` — extracted CSS
- `data.js` — listings data
- `app.js` — all JS logic

### 5. Add real-time vote sync (optional)
Currently votes/reactions/comments are in-memory only (lost on refresh). To persist across devices, add a lightweight backend:
- **Firebase Realtime DB** — easiest, free tier works great
- **Supabase** — Postgres-backed, also free
- **localStorage** — quick fix for single-device persistence

### 6. Deploy
This is a static site — drop `index.html` anywhere:
- **Netlify Drop** — drag and drop the file at netlify.com/drop
- **GitHub Pages** — push to a repo, enable Pages
- **Vercel** — `vercel deploy`

---

## 📋 Airbnb Listing URLs

| # | Title | URL |
|---|---|---|
| 1 | Georgian Bay A-Frame | https://www.airbnb.ca/rooms/1322779723776332921 |
| 2 | Lakefront Escape | https://www.airbnb.ca/rooms/1356182272072783043 |
| 3 | Muskoka Manor | https://www.airbnb.ca/rooms/40613745 |
| 4 | Blue Mountains Retreat | https://www.airbnb.ca/rooms/1573396745294436058 |
| 5 | Sauble Beach Stunner ⭐ | https://www.airbnb.ca/rooms/1385001401644874562 |
| 6 | Grand Bend Beachfront | https://www.airbnb.ca/rooms/581182022418368306 |
| 7 | The One — Grand Bend Estate ⭐ | https://www.airbnb.ca/rooms/1321080002066299067 |
| 8 | Kawartha Lakes Hideaway | https://www.airbnb.ca/rooms/1504300619694699840 |
