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
                      r"operations|bognor|"
                      # scientific journal figures / plates (e.g. 'Figure 46a', DOI-coded files)
                      r"figure|_fig|plate_|zootaxa|zookeys|pensoft|10\.3897|\.e\d{4,}|holotype|paratype|"
                      # dead catch / captivity — destination heroes must be alive and wild
                      r"caught|landed|_deck|fishery|bycatch|longline|fish_market|aquarium|marineland|"
                      r"banner|miskiy|masjid|diving_mask|snorkel_tube|submarine)", re.I)

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
    "South West Rocks": ["Grey nurse shark Fish Rock", "Grey nurse shark Australia underwater",
                         "Fish Rock Cave NSW", "Smoky Cape lighthouse", "Trial Bay Gaol beach"],
    "Chagos Archipelago / BIOT": ["Chagos reef", "Diego Garcia lagoon", "Salomon Atoll Chagos"],
    "Guadalcanal & Western Province": ["Marovo Lagoon", "Gizo Solomon Islands", "Solomon Islands lagoon aerial", "Honiara coast"],
    "Malpelo Island": ["Isla de Malpelo", "Malpelo Island Colombia", "Malpelo scalloped hammerhead",
                       "Malpelo island aerial", "Malpelo Fauna and Flora Sanctuary"],
    "Ningaloo Reef": ["Whale shark Ningaloo", "Ningaloo Reef underwater", "Ningaloo coral",
                      "Whale shark Exmouth Western Australia", "Ningaloo Reef aerial"],
    "Protea Banks": ["Ragged-tooth shark Aliwal Shoal", "Ragged tooth shark South Africa",
                     "Sand tiger shark wreck underwater", "Carcharias taurus underwater"],
    "Fuvahmulah": ["Tiger shark underwater diver", "Tiger shark Fuvahmulah", "Galeocerdo cuvier underwater",
                   "Tiger shark Maldives", "Fuvahmulah beach"],
    "Yap": ["Manta ray Yap Micronesia", "Yap manta ray", "Reef manta ray underwater",
            "Manta alfredi cleaning station"],
    "Kaş": ["Kaputaş Beach", "Kaputas beach Turkey", "Kaş Turkey aerial", "Kekova underwater ruins"],
    "Cocos Island": ["Hammerhead sharks Cocos Island", "Scalloped hammerhead school underwater",
                     "Isla del Coco Costa Rica", "Cocos Island Costa Rica aerial"],
    "Great Blue Hole": ["Great Blue Hole Belize aerial", "Great Blue Hole Belize",
                        "Lighthouse Reef Belize"],
    "Bat Islands": ["Bull shark Carcharhinus leucas underwater", "Bull shark underwater diver",
                    "Bull shark Bahamas underwater", "Islas Murcielago Costa Rica beach"],
    "Coiba": ["Granito de Oro Coiba", "Coiba beach Panama", "Isla Coiba Panama",
              "Coiba National Park Panama", "Coiba island beach"],
    "Cancún & Playa del Carmen": ["Playa Delfines", "Cancun beach", "Cancun Zona Hotelera aerial",
                                  "Isla Mujeres beach", "Playa del Carmen beach"],
    "Koh Tao": ["Ko Nang Yuan", "Nangyuan island Thailand", "Koh Tao beach Thailand",
                "Koh Tao Thailand island", "Sail Rock Koh Tao"],
    "Phuket": ["Racha Yai underwater", "Phuket Racha island", "Koh Phi Phi cliffs sea",
               "Shark Point Phuket underwater", "Phuket beach aerial"],
    "Bali": ["USAT Liberty wreck Tulamben", "Tulamben wreck diving", "Liberty wreck Bali underwater",
             "Menjangan island underwater", "Amed Bali coast"],
    "Tenerife": ["Green turtle Tenerife underwater", "El Puertito turtle Tenerife",
                 "Tenerife underwater volcanic reef", "Los Gigantes cliffs Tenerife"],
    "Zanzibar": ["Mnemba Atoll", "Zanzibar Nungwi beach dhow", "Mnemba island aerial",
                 "Zanzibar reef underwater", "Zanzibar dhow"],
    "Mallorca": ["Cala Figuera Mallorca", "Cap de Formentor Mallorca", "Sa Calobra Mallorca",
                 "Mallorca sea cave", "Mallorca cala turquoise"],
    "Muscat & Daymaniyat Islands": ["Daymaniyat Islands Oman", "Dimaniyat islands",
                                    "Bandar Khayran Oman", "Muscat coast Oman", "Oman coast aerial sea"],
    "Sharm El Sheikh": ["Ras Muhammad underwater", "Ras Mohammed reef", "Tiran island reef",
                        "Sharm el-Sheikh reef underwater", "Naama Bay"],
    "Hurghada": ["Giftun island", "Hurghada reef underwater", "Abu Nuhas wreck",
                            "El Gouna lagoon aerial", "Hurghada coast Red Sea"],
    "Marsa Alam": ["Elphinstone Reef", "Abu Dabbab", "dugong Marsa Alam", "Marsa Alam reef underwater",
                   "spinner dolphins Sataya"],
    "Dahab": ["Blue Hole Dahab", "Dahab lagoon Sinai", "Dahab canyon diving", "Dahab coast",
              "Blue Hole Sinai aerial"],
}

# For tricky names, a candidate file title MUST match this pattern (keeps
# "Rocks" from matching a West Virginia highway, "reef" from matching Aruba).
DEST_REQUIRE = {
    "Guadalcanal & Western Province": re.compile(r"(solomon|marovo|gizo|munda|roviana|guadalcanal|honiara|tulagi)", re.I),
    "South West Rocks": re.compile(r"(grey.?nurse|fish.?rock|trial.?bay|smoky.?cape|arakoon)", re.I),
    "Malpelo Island": re.compile(r"malpelo", re.I),
    "Ningaloo Reef": re.compile(r"(ningaloo|whale.?shark|exmouth|coral.?bay)", re.I),
    # Place-name only: generic species matches (tiger shark, raggie) let
    # wrong-place photos through — Fuvahmulah once got a Tiger Beach
    # (Bahamas) shot, Protea Banks an Aliwal Shoal one (photo audit 2026-07).
    "Protea Banks": re.compile(r"protea", re.I),
    "Fuvahmulah": re.compile(r"fuvahmulah", re.I),
    "Yap": re.compile(r"(yap|manta)", re.I),
    "Kaş": re.compile(r"(kaş|kas|kaputa|kekova|antalya|lycia|meis)", re.I),
    "Cocos Island": re.compile(r"(cocos|isla_del_coco|hammerhead|sphyrna)", re.I),
    "Great Blue Hole": re.compile(r"(blue.?hole|lighthouse.?reef|belize)", re.I),
    "Bat Islands": re.compile(r"(murci|bat.?island|bull.?shark|leucas|guanacaste|santa.?rosa)", re.I),
    "Coiba": re.compile(r"coiba", re.I),
    "Cancún & Playa del Carmen": re.compile(r"(subacu|cancun|manchones|isla_mujeres|playa_del_carmen|riviera_maya)", re.I),
    "Koh Tao": re.compile(r"(koh.?tao|nang.?yuan|sail.?rock|chumphon)", re.I),
    "Phuket": re.compile(r"(phuket|racha|phi.?phi|shark.?point)", re.I),
    "Bali": re.compile(r"(tulamben|liberty|menjangan|amed|bali)", re.I),
    "Tenerife": re.compile(r"(tenerife|puertito|gigantes|turtle|chelonia)", re.I),
    "Zanzibar": re.compile(r"(zanzibar|mnemba|nungwi|unguja)", re.I),
    "Mallorca": re.compile(r"(mallorca|majorca|formentor|calobra|cala|dragonera)", re.I),
    "Muscat & Daymaniyat Islands": re.compile(r"(daymaniyat|dimaniyat|bandar|muscat|oman)", re.I),
    "Sharm El Sheikh": re.compile(r"(sharm|ras.?m(o|u)hamm|tiran|naama)", re.I),
    "Hurghada": re.compile(r"(hurghada|giftun|gouna|abu.?nuhas|carnatic|giannis)", re.I),
    "Marsa Alam": re.compile(r"(marsa.?alam|elphinstone|abu.?dabbab|sataya|dugong)", re.I),
    "Dahab": re.compile(r"(dahab|blue.?hole|sinai)", re.I),
}


# Visually-vetted exact Commons files, tried before any search (mirrors the
# marine fetcher's PINNED map) — for destinations where search keeps missing.
DEST_PINNED = {
    "Rio de Janeiro": ["File:Farol da Ilha Rasa Baía da Guanabara-RJ (52078588124).jpg"],
    "Salvador": ["File:Baia de Todos os Santos e Elevador Lacerda.jpg"],
    # Owner picks, 2026-07-12 round (19 touristic-city additions).
    "Antalya": ["File:Kemer beach, Antalya.jpg"],
    "Bodrum": ["File:Bodrum Castle 5.JPG"],
    "Fethiye": ["File:Kabak Valley - Fethiye.jpg"],
    "Rhodes": ["File:Aerial view of Tsambika Monastery and Tsambika Beach, Rhodes, Greece (51698552836).jpg"],
    "Corfu": ["File:Bay of Palaiokastritsa from Bellavista.JPG"],
    "Zakynthos": ["File:Shipwreck at Navagio Beach Zakynthos Greece (45557496695).jpg"],
    "Ibiza": ["File:Ibiza rock volcano (747230830).jpg"],
    "Gran Canaria": ["File:Las Canteras Beach - La Barra - Las Palmas Gran Canaria.jpg"],
    "Lanzarote": ["File:Papagayo-Strände, Luftbild.JPG"],
    "Puerto Galera": ["File:Muelle Bay, Puerto Galera, Oriental Mindoro, April 2023.jpg"],
    "Coron (Busuanga)": ["File:Kayangan Lake, Coron - Palawan.jpg"],
    "Panglao & Balicasag": ["File:Alona beach - panoramio.jpg"],
    "Moalboal": ["File:White Beach Moalboal.JPG"],
    "Naples": ["File:Isoletta della Gaiola (Napoli) 01.jpg"],
    "Sorrento & Capri": ["File:Ferry and yacht port of Sorrento - Campania - Italy - July 12th 2013 - 03.jpg"],
    "Taormina": ["File:Isola Bella-Taormina-Messina-Sicilia-Italy Creative Commons by gnuckx (3811732382).jpg"],
    "Arraial do Cabo": ["File:Oven S Beach Arraial Do Cabo (247765557).jpeg"],
    "Sharm El Sheikh": ["File:AlternativesCorals.jpg"],
    "Protea Banks": ["File:Tide Pool, Ramsgate Beach.jpg"],
    # Genuine Fuvahmulah shot (photo audit 2026-07: the previous hero was a
    # Tiger Beach, Bahamas file). No genuine Fuvahmulah underwater photo
    # exists on Commons; this topside harbour shot is the honest choice.
    "Fuvahmulah": ["File:The Sunset Point in Fuvahmulah Harbour - panoramio.jpg"],
    "Galapagos Islands": ["File:Sea lions (32819956607).jpg"],
    "Coiba": ["File:Kristallklares Wasser Coiba Panama (152311725).jpeg"],
    "Cancún & Playa del Carmen": ["File:Cancun aerial photo by safa.jpg",
                                  "File:Cancun from the air July 1985.jpg"],
    "Phuket": ["File:Maya Bay, Krabi, Thailand (Panorama).jpg",
               "File:Longtail Boat At Maya Bay, Krabi, Thailand.jpg",
               "File:Longtail boat at Maya bay.JPG"],
    # Owner-approved picks (photo review, 2026-07) — never let search replace these.
    "Marsa Alam": ["File:Unterwasserwelt im Roten Meer, Ägypten DSCF4057WI.jpg"],
    "Cenotes of Yucatán Peninsula": ["File:Cenote Ik Kil, Yucatan, Dec 2011 - 06.jpg"],
    "Red Sea (Egypt)": ["File:Unterwasserwelt im Roten Meer, Ägypten DSCF4057WI.jpg"],
    "Bonaire": ["File:Snorkeling Bari Reef, Bonaire (12840799335).jpg"],
    "Cenderawasih Bay": ["File:Hiu Paus yang kesepian.jpg"],
    "Chania (Crete)": ["File:Aerial view of Balos Lagoon on the island of Crete, Greece.jpg"],
    "Dubai & Fujairah": ["File:Pristine blue waters of Snoopy Island.jpg"],
    "Great Barrier Reef": ["File:Aerial View of Great Barrier Reef (Ank Kumar) 09.jpg"],
    "Lord Howe Island": ["File:Balls Pyramid, Lord Howe Marine Park 1008.jpg"],
    "Seychelles": ["File:Anse Source d'Argent 3-La Digue.jpg"],
    "Silfra Fissure": ["File:Cañón Silfra, Parque Nacional de Þingvellir, Suðurland, Islandia, 2014-08-16, DD 055.JPG"],
    "Ustica": ["File:Grotta verde.jpg"],
    "Vancouver Island": ["File:Diving Humpback Whale near Vancouver Island, Canada (54881205528).jpg"],
    "Whitsunday Islands": ["File:Whitehaven Beach - Northern End.jpg"],
}

# Destinations that deliberately have NO hero photo: no genuine openly-
# licensed photo of the place exists (Commons audited 2026-07), so the page
# renders the branded gradient hero instead. Never auto-fill these — a
# wrong-place photo is worse than none. Remove from this set only when the
# owner supplies/approves a genuine shot.
DEST_NO_HERO = {   # submerged shoal, 8 km offshore; Commons has nothing genuine
}

# Exact-file rejects per destination — visually-audited duds that pass the
# generic filters (e.g. an aquarium sand tiger with no 'aquarium' in the name).
DEST_BLOCK = {
    "Dahab": re.compile(r"(rohscan|_scan|bearb)", re.I),
    "Protea Banks": re.compile(r"27287498303", re.I),
    "Kaş": re.compile(r"comertel", re.I),          # timestamped 2005 harbour snapshot
    "Bat Islands": re.compile(r"66636561", re.I),  # sunset-through-twigs panoramio
    "Coiba": re.compile(r"(coiba_banner|police|pickaback|prisoner|penal|_195\d|_196\d)", re.I),
    "Fuvahmulah": re.compile(r"kedeyre", re.I),
    "Cancún & Playa del Carmen": re.compile(r"(residencial|deir|mar[_ ]musa|monast|f\u00f3sil|fosil|cancun,[_ ]mexico)", re.I),
    "Koh Tao": re.compile(r"(arrivals|excellent[_ ]visibility)", re.I),
    "Phuket": re.compile(r"(surin|similan|phuket.?sea|night[_ ]fishing|fishing|24848021407)", re.I),
    "Bali": re.compile(r"(22093248545|magnificent[_ ]sea[_ ]anemone|filefish|anemone)", re.I),
    "Tenerife": re.compile(r"(babosa|felimare|nudibranch)", re.I),
    "Zanzibar": re.compile(r"(almeja|tridacna)", re.I),
    "Mallorca": re.compile(r"(7838116390|bro[_ ]?underwater)", re.I),
    "Muscat & Daymaniyat Islands": re.compile(r"(moral[_ ]eel|207977467)", re.I),
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
    pinned = DEST_PINNED.get(name)
    if pinned:
        got = _commons_pick(pinned)
        if got:
            print("    · pinned file")
            return got
    base = re.sub(r"\s*\(.*?\)", "", name).strip()          # "Red Sea (Egypt)" -> "Red Sea"
    require = DEST_REQUIRE.get(name)
    queries = DEST_QUERIES.get(name) or [
        f"{base} underwater", f"{base} reef", f"{base} scuba diving",
        f"{base} coral", f"{base} aerial island", f"{base} {country} sea"]
    for q in queries:
        url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
               "&list=search&srnamespace=6&srlimit=25&srsearch=" + urllib.parse.quote(q))
        j = _get(url)
        hits = (((j or {}).get("query") or {}).get("search")) or []
        titles = [h["title"] for h in hits if not BAD_HINT.search(h.get("title", ""))]
        block = DEST_BLOCK.get(name)
        if block:
            titles = [t for t in titles if not block.search(t)]
        if require:
            titles = [t for t in titles if require.search(t)]
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
        if name in DEST_NO_HERO:
            continue
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
        # indent=1 + trailing newline: matches build_master.py / the canonical
        # file's formatting so image runs don't reformat the whole JSON.
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"Done — {updated} destination image(s) written to diving-destinations.json")


if __name__ == "__main__":
    main()
