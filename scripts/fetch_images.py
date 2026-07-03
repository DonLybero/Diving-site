#!/usr/bin/env python3
"""Bake one representative photo per destination into diving-destinations.json.

Source order per destination:
  1. Pexels   (needs env PEXELS_API_KEY) — best quality, keyword search.
  2. Wikimedia Commons geosearch by the destination's coordinates — localized,
     freely licensed, no key required.

Writes three fields onto each destination:
  image         — a ready-to-use image URL (~800px wide)
  image_credit  — human-readable attribution string
  image_source  — "pexels" | "wikimedia"

Idempotent: skips destinations that already have `image` unless --force is passed.
Network runs on machines with internet (e.g. GitHub Actions) — this repo's build
sandbox is firewalled, so run it via .github/workflows/fetch-images.yml.

Usage:
  PEXELS_API_KEY=xxxx python3 scripts/fetch_images.py [--force]
"""
import json, os, sys, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "diving-destinations.json")
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
FORCE = "--force" in sys.argv
UA = "DiveSZNImageFetcher/1.0 (https://github.com/DonLybero/Diving-site; static-site image baker)"

# File names that are clearly not scenery — skip these from Wikimedia geosearch.
BAD_HINT = re.compile(r"(locator|location|map|flag|coat_of_arms|logo|icon|diagram|"
                      r"\.svg$|chart|seal|emblem|iss0\d|view_of_earth|airport|aeropuerto|"
                      r"mosque|church|cathedral|museum|plaque|statue|monument|inauguration|"
                      r"bicycle|bus_|railway|station|street|road_|casent|herbarium|specimen|"
                      r"stamp|banknote|coin_|graffiti|hotel|restaurant|_table|thumbnail|"
                      r"legends_of|illustration|drawing|painting|poster|book_|experimental|"
                      r"operations|bognor)", re.I)

# Titles that clearly ARE what we want; used to rank search hits.
GOOD_HINT = re.compile(r"(underwater|reef|coral|diving|diver|snorkel|wreck|lagoon|atoll|"
                       r"beach|bay|sea|ocean|island|shark|turtle|manta|ray|fish|aerial|"
                       r"coast|shore|cenote|kelp|anemone)", re.I)

# Hand-tuned Commons search queries for destinations the generic queries miss.
DEST_QUERIES = {
    "Maui & Kona": ["Molokini crater aerial", "Hawaii coral reef underwater", "Maui underwater turtle"],
    "Okinawa Islands": ["Kerama Islands underwater", "Okinawa coral reef", "Zamami island sea"],
    "Truk (Chuuk) Lagoon": ["Chuuk Lagoon shipwreck underwater", "Fujikawa Maru", "Truk Lagoon wreck diving"],
    "Lundy Island": ["Lundy island coast", "Lundy grey seal", "Lundy Devon sea"],
    "Vancouver Island": ["British Columbia kelp forest underwater", "Vancouver Island coast aerial", "Pacific Northwest diving"],
    "South West Rocks": ["Fish Rock Cave", "grey nurse shark Australia", "South West Rocks NSW beach"],
    "Chagos Archipelago / BIOT": ["Chagos reef", "Diego Garcia lagoon", "Salomon Atoll Chagos"],
    "Guadalcanal & Western Province": ["Solomon Islands coral reef", "Solomon Islands underwater", "Marovo Lagoon"],
}


def _get(url, headers=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                print(f"    ! request failed ({e})")
                return None
            time.sleep(1.5 * (i + 1))
    return None


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


# ---------------------------------------------------------------- Pexels
def from_pexels(name, country):
    if not PEXELS_KEY:
        return None
    queries = [f"{name} scuba diving", f"{name} underwater", f"{name} diving",
               name, f"{country} scuba diving"]
    for q in queries:
        url = ("https://api.pexels.com/v1/search?per_page=5&orientation=landscape&query="
               + urllib.parse.quote(q))
        j = _get(url, headers={"Authorization": PEXELS_KEY})
        photos = (j or {}).get("photos") or []
        if photos:
            p = photos[0]
            src = (p.get("src") or {})
            img = src.get("landscape") or src.get("large2x") or src.get("large")
            if img:
                credit = f"Photo by {p.get('photographer','Pexels')} on Pexels"
                return {"image": img, "image_credit": credit, "image_source": "pexels"}
    return None


# ---------------------------------------------------------------- Wikimedia
def _commons_pick(titles):
    """Fetch imageinfo for candidate file titles; return the first good one."""
    for i in range(0, len(titles), 10):
        batch = "|".join(titles[i:i + 10])
        info = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                "&prop=imageinfo&iiprop=url|mime|size|extmetadata&iiurlwidth=960&titles="
                + urllib.parse.quote(batch))
        j = _get(info)
        pages = (((j or {}).get("query") or {}).get("pages")) or {}
        for page in pages.values():
            ii = (page.get("imageinfo") or [{}])[0]
            if ii.get("mime", "") not in ("image/jpeg", "image/png"):
                continue
            w, h = ii.get("width", 0), ii.get("height", 0)
            if w < 800 or h < 450 or h > w * 1.1:      # need a usable landscape photo
                continue
            img = ii.get("thumburl") or ii.get("url")
            if not img:
                continue
            meta = ii.get("extmetadata") or {}
            artist = strip_html((meta.get("Artist") or {}).get("value", "")) or "Wikimedia Commons"
            lic = strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
            credit = f"Photo: {artist}" + (f" ({lic})" if lic else "") + " via Wikimedia Commons"
            return {"image": img, "image_credit": credit, "image_source": "wikimedia"}
    return None


def from_wikimedia_search(name, country):
    """Keyword search on Commons for marine/scenery photos of the destination."""
    base = re.sub(r"\s*\(.*?\)", "", name).strip()          # "Red Sea (Egypt)" -> "Red Sea"
    queries = DEST_QUERIES.get(name) or [
        f"{base} underwater", f"{base} reef", f"{base} scuba diving",
        f"{base} coral", f"{base} aerial island", f"{base} {country} sea"]
    for q in queries:
        url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
               "&list=search&srnamespace=6&srlimit=25&srsearch=" + urllib.parse.quote(q))
        j = _get(url)
        hits = (((j or {}).get("query") or {}).get("search")) or []
        titles = [h["title"] for h in hits if not BAD_HINT.search(h.get("title", ""))]
        # rank: titles with marine words first
        titles.sort(key=lambda t: 0 if GOOD_HINT.search(t) else 1)
        got = _commons_pick(titles)
        if got:
            return got
    return None


def from_wikimedia(coord):
    if not coord or coord.get("lat") is None or coord.get("lng") is None:
        return None
    geo = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&list=geosearch"
           "&gsnamespace=6&gsradius=10000&gslimit=25&gscoord="
           + f"{coord['lat']}|{coord['lng']}")
    j = _get(geo)
    hits = (((j or {}).get("query") or {}).get("geosearch")) or []
    titles = [h["title"] for h in hits if not BAD_HINT.search(h.get("title", ""))]
    for i in range(0, len(titles), 10):
        batch = "|".join(titles[i:i + 10])
        info = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                "&prop=imageinfo&iiprop=url|mime|extmetadata&iiurlwidth=800&titles="
                + urllib.parse.quote(batch))
        j = _get(info)
        pages = (((j or {}).get("query") or {}).get("pages")) or {}
        for page in pages.values():
            ii = (page.get("imageinfo") or [{}])[0]
            mime = ii.get("mime", "")
            if mime not in ("image/jpeg", "image/png"):
                continue
            img = ii.get("thumburl") or ii.get("url")
            if not img:
                continue
            meta = ii.get("extmetadata") or {}
            artist = strip_html((meta.get("Artist") or {}).get("value", "")) or "Wikimedia Commons"
            lic = strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
            credit = f"Photo: {artist}" + (f" ({lic})" if lic else "") + " via Wikimedia Commons"
            return {"image": img, "image_credit": credit, "image_source": "wikimedia"}
    return None


def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    dests = data.get("destinations", [])
    print(f"{len(dests)} destinations · Pexels key: {'yes' if PEXELS_KEY else 'no (Wikimedia only)'}"
          f" · force: {FORCE}")
    updated = 0
    for d in dests:
        name = d.get("name", "")
        if d.get("image") and not FORCE:
            continue
        got = (from_pexels(name, d.get("country", ""))
               or from_wikimedia_search(name, d.get("country", ""))
               or from_wikimedia(d.get("coordinates")))
        if got:
            d.update(got)
            updated += 1
            print(f"  ✓ {name:<28} [{got['image_source']}]")
        else:
            print(f"  · {name:<28} no image found")
        time.sleep(0.3)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Done — {updated} destination image(s) written to diving-destinations.json")


if __name__ == "__main__":
    main()
