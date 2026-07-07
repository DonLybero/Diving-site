#!/usr/bin/env python3
"""Bake one representative photo per marine-life encounter into marine-life.json.

Source: Wikimedia Commons keyword search (freely licensed, no API key). Each
encounter gets hand-tuned queries so we land on a strong, correctly-licensed
landscape photo of the animal in the water rather than a map or a specimen shot.

Writes onto each experience:
  image         — ready-to-use image URL (~960px wide)
  image_credit  — human-readable attribution string
  image_source  — "wikimedia"

Idempotent: skips experiences that already have `image` unless --force is passed.
Runs on machines with internet (GitHub Actions) — this repo's sandbox is
firewalled, so run it via .github/workflows/fetch-marine-images.yml.

Usage: python3 scripts/fetch_marine_images.py [--force]
"""
import json, os, sys, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "marine-life.json")
FORCE = "--force" in sys.argv
UA = "DiveSZNImageFetcher/1.0 (https://github.com/DonLybero/Diving-site; static-site image baker)"

# File names that are clearly not what we want.
BAD_HINT = re.compile(r"(locator|location|map|flag|coat_of_arms|logo|icon|diagram|"
                      r"\.svg$|chart|seal|emblem|stamp|banknote|coin_|drawing|"
                      r"illustration|painting|sketch|diagram|distribution|range_|"
                      r"skeleton|jaw|teeth|specimen|museum|dissect|embryo|fossil|"
                      r"anatomy|logo|sign_|graph|"
                      # old book/plate scans (Internet Archive / Biodiversity Heritage)
                      r"fish_and_game|book_images|biodiversity_heritage|_bhl_|plate_|"
                      # 'orca' the Iberian megalithic tomb, not the whale
                      r"dolmen|menhir|megalith|pendilhe|cromlech|neolith|\banta\b|\bantas\b|tomb|"
                      # captive animals in parks/aquaria — we want wild encounters
                      r"marineland|seaworld|sea_world|aquarium|dolphinarium|captiv|_zoo_|"
                      # landed / dead catch — never a fresh-off-the-boat fisheries shot
                      r"caught|landed|deck|fisher|bycatch|longline|hooked|gutted|carcass|"
                      r"trophy|for_sale|fish_market|on_boat|_boat_|dead_|dries|drying|hanging|"
                      # other charismatic animals that must not be the subject (we have no
                      # turtle/dolphin encounter, so a file naming one is the wrong photo)
                      r"turtle|chelon|testudin|dolphin|tortoise)", re.I)

# Upload sources that are almost always scanned book plates, not photos — skip
# even if the file name looks innocent.
BAD_ARTIST = re.compile(r"(internet archive book images|biodiversity heritage)", re.I)

# Titles that ARE what we want; used to rank hits (in the water beats a beach).
GOOD_HINT = re.compile(r"(underwater|diver|diving|snorkel|school|shoal|baitball|"
                       r"bait_ball|swimming|reef|ocean|sea|cage)", re.I)

# A candidate file title MUST name the species — stops the search from falling
# through to a loosely-related "whale"/"ray"/"shark" photo when good matches are
# scarce (e.g. a right whale for orcas, or a stingray for mantas).
REQUIRE = {
    "whale-sharks":      re.compile(r"(whale.?shark|rhincodon)", re.I),
    "manta-rays":        re.compile(r"(manta|mobula|devil.?ray)", re.I),
    "hammerhead-sharks": re.compile(r"(hammerhead|sphyrna)", re.I),
    "thresher-sharks":   re.compile(r"(thresher|alopias)", re.I),
    "mola-mola":         re.compile(r"(mola|sunfish)", re.I),
    "sea-lions":         re.compile(r"(sea.?lion|zalophus|otari)", re.I),
    "sardine-run":       re.compile(r"(sardine|bait.?ball)", re.I),
    "great-white":       re.compile(r"(great.?white|white.?shark|carcharodon)", re.I),
    "orcas":             re.compile(r"(orca|killer.?whale|orcinus)", re.I),
}

# Visually-vetted Commons files, tried before any search — for encounters where
# search keeps landing on technically-correct but weak photos (e.g. the orca
# result was a grainy 1970s surface scan). Exact file titles, best first.
PINNED = {
    "orcas": ["File:Killerwhales jumping.jpg",
              "File:Orca porpoising.jpg",
              "File:Type C Orcas.jpg",
              "File:Orcinus orca surfacing near Unimak Island.jpg"],
}

# Hand-tuned Commons search queries per encounter slug (best first).
QUERIES = {
    "whale-sharks":      ["Whale shark diving", "Rhincodon typus underwater",
                          "Whale shark snorkeler", "Whale shark Ningaloo"],
    "manta-rays":        ["Manta ray diving", "Manta birostris underwater",
                          "Reef manta ray", "Manta ray cleaning station"],
    "hammerhead-sharks": ["Scalloped hammerhead shark underwater", "Hammerhead shark school diving",
                          "Sphyrna lewini underwater", "Hammerhead sharks Galapagos Darwin"],
    "thresher-sharks":   ["Thresher shark Malapascua underwater", "Pelagic thresher Monad Shoal",
                          "Thresher shark reef diver", "Alopias pelagicus swimming underwater",
                          "Pelagic thresher shark diving"],
    "mola-mola":         ["Mola mola diver", "Ocean sunfish underwater",
                          "Mola mola Bali", "Ocean sunfish Mola"],
    "sea-lions":         ["Sea lion underwater diver", "California sea lion underwater",
                          "Sea lion snorkeling", "Sea lions swimming underwater"],
    "sardine-run":       ["Sardine baitball underwater", "Sardine bait ball",
                          "Sardine shoal underwater", "Sardinops school",
                          "Sardine run baitball South Africa"],
    "great-white":       ["Great white shark", "Carcharodon carcharias",
                          "Great white shark cage diving", "White shark underwater"],
    "orcas":             ["Orcinus orca underwater", "Killer whale ocean swimming",
                          "Killer whale Norway diving", "Orca whale sea"],
}


def _get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
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


def _commons_pick(titles):
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
            if BAD_ARTIST.search(artist):
                continue                                   # scanned book plate, not a photo
            lic = strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
            credit = f"Photo: {artist}" + (f" ({lic})" if lic else "") + " via Wikimedia Commons"
            return {"image": img, "image_credit": credit, "image_source": "wikimedia"}
    return None


def from_commons(slug, title):
    pinned = PINNED.get(slug)
    if pinned:
        got = _commons_pick(pinned)
        if got:
            print("    · pinned file")
            return got
    queries = QUERIES.get(slug) or [title]
    require = REQUIRE.get(slug)
    for q in queries:
        url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
               "&list=search&srnamespace=6&srlimit=25&srsearch=" + urllib.parse.quote(q))
        j = _get(url)
        hits = (((j or {}).get("query") or {}).get("search")) or []
        titles = [h["title"] for h in hits if not BAD_HINT.search(h.get("title", ""))]
        if require:
            titles = [t for t in titles if require.search(t)]
        titles.sort(key=lambda t: 0 if GOOD_HINT.search(t) else 1)
        got = _commons_pick(titles)
        if got:
            print(f"    · via \"{q}\"")
            return got
    return None


def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    exps = data.get("experiences", [])
    print(f"{len(exps)} encounters · force: {FORCE}")
    updated = 0
    for e in exps:
        name = e.get("title", e.get("slug", ""))
        if e.get("image") and not FORCE:
            continue
        got = from_commons(e.get("slug", ""), name)
        if got:
            e.update(got)
            updated += 1
            print(f"  ✓ {name:<22} {got['image'][:70]}")
        else:
            print(f"  · {name:<22} no image found")
        time.sleep(0.3)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Done — {updated} encounter image(s) written to marine-life.json")


if __name__ == "__main__":
    main()
