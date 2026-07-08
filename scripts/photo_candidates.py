#!/usr/bin/env python3
"""Gather photo CANDIDATES for hand-picked destinations (owner photo review).

For each destination below, runs hand-tuned Commons queries and downloads up
to 5 distinct, filter-passing landscape photos to cands/<slug>_<i>.jpg plus a
cands/manifest.json with titles/credits/urls. Runs on GitHub's runners via
.github/workflows/photo-candidates.yml (the dev sandbox has no internet).
"""
import json, os, re, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_images import _get, strip_html, BAD_HINT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "DiveSZNCandidates/1.0 (https://github.com/DonLybero/Diving-site)"}
PER_DEST = 5

CANDIDATE_QUERIES = {
    "azores": ["Azores coastline landscape", "Sao Miguel Azores landscape", "Pico island Azores"],
    "bahamas": ["Exuma Bahamas aerial", "Bahamas beach aerial", "Nassau Bahamas coast"],
    "bay-islands": ["Roatan aerial", "West Bay Beach Roatan", "Bay Islands Honduras"],
    "cancun-playa-del-carmen": ["Cancun beach aerial", "Playa del Carmen beach", "Cancun hotel zone aerial"],
    "cocos-island": ["Isla del Coco", "Cocos Island Costa Rica landscape", "Cocos Island waterfall"],
    "coiba": ["Coiba island Panama", "Coiba National Park", "Coiba beach"],
    "fernando-de-noronha": ["Fernando de Noronha beach", "Morro Dois Irmaos Noronha", "Fernando de Noronha aerial"],
    "fiji": ["Fiji islands aerial", "Yasawa islands Fiji", "Fiji beach palm trees"],
    "french-polynesia": ["Bora Bora aerial lagoon", "Rangiroa atoll", "French Polynesia island aerial"],
    "fuvahmulah": ["Fuvahmulah island", "Fuvahmulah aerial", "Fuvahmulah Maldives beach"],
    "galapagos-islands": ["Bartolome island Galapagos", "Galapagos islands landscape", "Galapagos coastline"],
    "great-barrier-reef": ["Great Barrier Reef aerial", "Heart Reef Australia", "Great Barrier Reef island aerial"],
    "great-blue-hole": ["Great Blue Hole aerial", "Great Blue Hole Belize", "Lighthouse Reef atoll Belize"],
    "jupiter": ["Jupiter Inlet Lighthouse", "Jupiter Florida beach", "Jupiter Inlet aerial"],
    "koh-tao": ["Koh Tao viewpoint", "Koh Tao beach Thailand", "Koh Tao aerial"],
    "komodo-national-park": ["Padar island viewpoint", "Komodo island landscape", "Komodo National Park hills"],
    "layang-layang": ["Layang-Layang atoll", "Layang Layang Malaysia", "Swallow Reef"],
    "malapascua-island": ["Malapascua island beach", "Malapascua Philippines", "Malapascua bounty beach"],
    "maldives": ["Maldives atoll aerial", "Maldives island aerial", "Maldives beach island"],
    "malpelo-island": ["Malpelo island", "Isla Malpelo Colombia", "Malpelo rock"],
    "marsa-alam": ["Marsa Alam beach", "Marsa Alam coast Egypt", "Abu Dabbab beach"],
    "maui-kona": ["Maui coastline aerial", "Kona Hawaii coastline", "Maui beach landscape"],
    "mauritius": ["Le Morne Mauritius", "Mauritius aerial lagoon", "Mauritius beach landscape"],
    "muscat-daymaniyat-islands": ["Daymaniyat Islands Oman", "Muscat corniche", "Muscat coastline Oman"],
    "ningaloo-reef": ["Ningaloo coast aerial", "Turquoise Bay Exmouth", "Cape Range National Park coast"],
    "nusa-penida": ["Kelingking Beach Nusa Penida", "Nusa Penida cliffs", "Crystal Bay Nusa Penida"],
    "palau": ["Rock Islands Palau aerial", "Seventy Islands Palau", "Palau islands lagoon"],
    "phuket": ["Phang Nga Bay Thailand", "Phuket beach aerial", "Phuket viewpoint"],
    "poor-knights-islands": ["Poor Knights Islands", "Poor Knights Islands New Zealand", "Tutukaka coast"],
    "protea-banks": ["Margate beach South Africa", "KwaZulu-Natal south coast", "Shelly Beach KwaZulu-Natal"],
    "raja-ampat": ["Wayag Raja Ampat", "Pianemo Raja Ampat viewpoint", "Raja Ampat islands aerial"],
    "sea-of-cortez": ["Espiritu Santo island Baja", "Sea of Cortez coastline", "Baja California Sur coast"],
    "seychelles": ["Anse Source d'Argent", "La Digue Seychelles beach", "Seychelles granite beach"],
    "sharm-el-sheikh": ["Sharm El Sheikh coastline", "Naama Bay Sharm El Sheikh", "Ras Mohammed peninsula"],
    "similan-islands": ["Similan Islands beach", "Similan Islands sail rock viewpoint", "Similan Islands Thailand"],
    "sipadan-island": ["Sipadan island aerial", "Pulau Sipadan", "Sipadan beach"],
    "socorro-island": ["Socorro Island", "Revillagigedo Islands", "San Benedicto island"],
    "tofo": ["Tofo beach Mozambique", "Praia do Tofo", "Inhambane coastline"],
    "tubbataha-reefs-natural-park": ["Tubbataha reef aerial", "Tubbataha lighthouse islet", "Sulu Sea reef aerial"],
    "utila": ["Utila island Honduras", "Utila beach", "Utila aerial"],
    "whitsunday-islands": ["Whitehaven Beach aerial", "Hill Inlet Whitsundays", "Whitsunday Islands aerial"],
    "yap": ["Yap island Micronesia", "Yap coastline", "Colonia Yap"],
    "zanzibar": ["Nungwi beach Zanzibar", "Zanzibar beach dhow", "Stone Town Zanzibar waterfront"],
}

EXCLUDE = {}
TOPSIDE_EXCLUDE = __import__("re").compile(
    r"(scuba|diver|diving|underwater|snorkel|coral|shark|manta|\bray\b|turtle|wreck|nudibranch|moray|barracuda|aquarium|jellyfish|dolphin|whale|seal\b|fish\b)", __import__("re").I)


def search_files(q, limit=20):
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
           "&list=search&srnamespace=6&srlimit=%d&srsearch=" % limit + urllib.parse.quote(q))
    j = _get(url)
    hits = (((j or {}).get("query") or {}).get("search")) or []
    return [h["title"] for h in hits if not BAD_HINT.search(h.get("title", ""))]


def file_info(titles):
    """title -> (thumb_url, credit, w, h) for usable landscape jpg/png."""
    out = {}
    for i in range(0, len(titles), 20):
        batch = "|".join(titles[i:i + 20])
        info = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                "&prop=imageinfo&iiprop=url|mime|size|extmetadata&iiurlwidth=960&titles="
                + urllib.parse.quote(batch))
        j = _get(info)
        pages = (((j or {}).get("query") or {}).get("pages")) or {}
        for page in pages.values():
            t = page.get("title", "")
            ii = (page.get("imageinfo") or [{}])[0]
            if ii.get("mime", "") not in ("image/jpeg", "image/png"):
                continue
            w, h = ii.get("width", 0), ii.get("height", 0)
            if w < 800 or h < 450 or h > w * 1.1:
                continue
            img = ii.get("thumburl") or ii.get("url")
            if not img:
                continue
            meta = ii.get("extmetadata") or {}
            artist = strip_html((meta.get("Artist") or {}).get("value", "")) or "Wikimedia Commons"
            lic = strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
            out[t] = (img, f"Photo: {artist}" + (f" ({lic})" if lic else "") + " via Wikimedia Commons")
    return out


def grab(url, path):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                blob = r.read()
            with open(path, "wb") as f:
                f.write(blob)
            time.sleep(0.4)
            return True
        except Exception:
            time.sleep(3 * (attempt + 1))
    return False


def main():
    data = json.load(open(os.path.join(ROOT, "diving-destinations.json")))
    current = {d["slug"]: (d.get("image") or "") for d in data["destinations"]}
    os.makedirs("cands", exist_ok=True)
    manifest = {}
    for slug, queries in CANDIDATE_QUERIES.items():
        picked, seen = [], set()
        for q in queries:
            if len(picked) >= PER_DEST:
                break
            titles = [t for t in search_files(q) if t not in seen]
            ex = EXCLUDE.get(slug) or TOPSIDE_EXCLUDE
            titles = [t for t in titles if not ex.search(t)]
            info = file_info(titles[:12])
            for t in titles:
                if t not in info or len(picked) >= PER_DEST:
                    continue
                url, credit = info[t]
                if url == current.get(slug):
                    continue                      # don't re-offer the photo being replaced
                if any(p["title"] == t for p in picked):
                    continue
                seen.add(t)
                idx = len(picked) + 1
                path = f"cands/{slug}_{idx}.jpg"
                if grab(url, path):
                    picked.append({"title": t, "url": url, "credit": credit, "file": path})
                    print(f"  {slug} #{idx}: {t[:70]}")
        manifest[slug] = picked
        print(f"{slug}: {len(picked)} candidates")
    with open("cands/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
