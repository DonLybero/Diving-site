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
    "azores": ["Sete Cidades lake", "Vila Franca islet", "Azores cliffs coast", "Sao Miguel coast"],
    "bahamas": ["Exuma sandbar", "Eleuthera beach Bahamas", "Bahamas turquoise aerial island", "Harbour Island Bahamas"],
    "bay-islands": ["Roatan West Bay beach", "Roatan beach palm", "Guanaja island", "Honduras Caribbean beach"],
    "cancun-playa-del-carmen": ["Cancun beach turquoise", "Playa del Carmen shore", "Isla Mujeres beach", "Riviera Maya coastline"],
    "coiba": ["Coiba", "Coiba island beach Panama", "Santa Catalina Panama coast", "Panama Pacific island"],
    "fiji": ["Mamanuca Islands", "Taveuni Fiji coast", "Fiji beach island palm", "Viti Levu coast"],
    "layang-layang": ["Layang-Layang", "Swallow Reef Layang", "Spratly Islands atoll", "atoll airstrip aerial"],
    "malapascua-island": ["Malapascua", "Logon Beach Malapascua", "Malapascua Cebu Philippines", "Visayas island beach"],
    "marsa-alam": ["Marsa Alam", "Port Ghalib marina", "Abu Dabbab", "Red Sea coast Egypt south"],
    "muscat-daymaniyat-islands": ["Daymaniyat", "Mutrah corniche Muscat", "Muscat coastline", "Oman islands sea"],
    "ningaloo-reef": ["Ningaloo", "Coral Bay Western Australia", "Exmouth Cape Range", "Ningaloo coast beach"],
    "protea-banks": ["Margate KwaZulu-Natal", "Uvongo beach", "Port Shepstone", "KwaZulu-Natal coast beach"],
    "seychelles": ["Anse Lazio Praslin", "Mahe Seychelles coast", "Seychelles islands aerial", "Anse Intendance"],
    "sharm-el-sheikh": ["Sharm el-Sheikh marina", "Sharm el-Sheikh bay", "Naama Bay", "Sinai coast Sharm"],
    "sipadan-island": ["Sipadan", "Semporna islands", "Mabul island Malaysia", "Celebes Sea island"],
    "socorro-island": ["Socorro Island Mexico", "Isla Socorro", "Revillagigedo Islands", "San Benedicto volcano"],
    "tofo": ["Tofo Mozambique", "Praia do Tofo beach", "Inhambane dunes coast", "Mozambique beach dunes"],
    "tubbataha-reefs-natural-park": ["Tubbataha", "Tubbataha ranger station", "Sulu Sea atoll aerial", "Philippines reef aerial islet"],
    "utila": ["Utila town Honduras", "Utila harbour", "Utila island dock", "Honduras island village"],
    "yap": ["Yap Micronesia", "Colonia Yap", "Yap island beach", "Micronesia island coast"],
}

EXCLUDE = {}
OFFERED = {
    "azores": ["File:Vista de Furnas, isla de San Miguel, Azores, Portugal, 2020-07-29, DD 82-90 PAN.jpg", "File:S\u00e3o Miguel, Azores ESA399763.jpg", "File:Landscape of Sao Miguel island - Azores - panoramio.jpg", "File:Landscape of Sao Miguel island - Azores - panoramio (2).jpg", "File:Landscape of Sao Miguel island - Azores - panoramio (3).jpg"],
    "bahamas": ["File:Bahamas 1989 (591) Great Exuma (24986096444).jpg", "File:Bahamas 1989 (589) Great Exuma (25497769082).jpg", "File:Bahamas 1989 (588) Great Exuma (25474038752).jpg", "File:Bahamas 1989 (592) Exuma (25249275789).jpg", "File:Bahamas 1989 (757) Exuma Islands (26229646886).jpg"],
    "bay-islands": ["File:Aerial view of West End, Roatan.jpg", "File:Aerial view of Coxen Hole, Roatan.jpg", "File:Roatan looking north towards West End.jpg", "File:West Bay Beach -Roatan -Honduras-23May2009.jpg", "File:West Bay Beach -Roatan -Honduras-23May2009-g.jpg"],
    "cancun-playa-del-carmen": ["File:Cancun beach aerial - Luftbild (19853282239).jpg", "File:Cancun beach aerial - Luftbild (19853298089).jpg", "File:Cancun beach aerial - Luftbild (18632391933).jpg", "File:Cancun beach aerial - Luftbild (18632395003).jpg", "File:Aerial cancun beach - Luftbild (20045211881).jpg"],
    "coiba": ["File:Coiba and Jicar\u00f3n Island.jpg", "File:Coiba National Park, Panama (View from Isla Coiba) (8371374375).jpg", "File:Coiba Panama (152311733).jpeg", "File:Isla de Coiba - Granite de Oro - Pacific Ocean Islands off Panama - panoramio (28).jpg", "File:A police officer goes ashore pickaback, Coiba Island, 1956 (8231825221).jpg"],
    "fiji": ["File:Denarau Island, Fiji, 2013 (4).jpg", "File:(Aerial view within Lau Islands, Fiji) - DPLA - 989763b50815d9f178c4fa35d37db744.jpg", "File:(Aerial view of island coastline within Lau Islands, Fiji) - DPLA - f5061f4c9d9bfc4e84d472836007c77c.jpg", "File:(Aerial view within Lau Islands, Fiji) - DPLA - 12024e0c8e93db30dd2768949350d564.jpg", "File:(Aerial view of island coastline within Lau Islands, Fiji) - DPLA - 8b343058f67792ba5d0f985d9f943a5b.jpg"],
    "layang-layang": ["File:Swallow Reef10.jpg", "File:Swallow Reef, Spratly Islands.png", "File:Swallow Reef2.jpg", "File:Swallow Reef sea3.jpg", "File:Swallow Reef sea4.jpg"],
    "malapascua-island": ["File:Malapascua (island), Tropical beach, Philippines.jpg", "File:Malapascua Island, Tropical sunset on the beach 2, Philippines.jpg", "File:Malapascua Island, Sunset on the beach 2, Philippines.jpg", "File:Malapascua (island), Bounty Beach, Philippines.jpg", "File:Malapascua (island), Palm trees on the sandy beach, Philippines.jpg"],
    "marsa-alam": ["File:Marsa Alam R02.jpg", "File:Marsa Alam R05.jpg", "File:Marsa Alam R08.jpg", "File:\u00c4gypten, Marsa Alam 2H1A1738WI.jpg", "File:Sonnenuntergang in Marsa Alam 2H1A2138WI.jpg"],
    "muscat-daymaniyat-islands": ["File:Dimaniyat Islands 2.jpg", "File:Cherna ar\u00e1biga (Cephalopholis hemistiktos), islas Ad Dimaniyat, Om\u00e1n, 2024-08-13, DD 17.jpg", "File:Pez erizo moteado (Diodon hystrix), islas Ad Dimaniyat, Om\u00e1n, 2024-08-15, DD 76.jpg", "File:Apog\u00f3nido (Ostorhinchus aureus), islas Ad Dimaniyat, Om\u00e1n, 2024-08-15, DD 05.jpg", "File:Beach in Al Dimaniyyat Islands Nature Reserve in Oman (53697748816).jpg"],
    "ningaloo-reef": ["File:Tsitsikamma National Park (ZA), Kanus an der K\u00fcste -- 2024 -- 1990.jpg", "File:Cape Town (ZA), Cape Peninsula National Park, Cape of Good Hope -- 2024 -- 3276.jpg", "File:Cape Town (ZA), Cape Peninsula National Park, Cape of Good Hope -- 2024 -- 3305.jpg", "File:Tsitsikamma National Park (ZA), K\u00fcste -- 2024 -- 1971.jpg", "File:Tsitsikamma National Park (ZA), K\u00fcste -- 2024 -- 2065.jpg"],
    "protea-banks": ["File:Margate, South Africa.jpg", "File:Uvongo Beach, KZN.jpg", "File:View from flat 21 Rondevoux, for holiday rental, -27 039 312 2242 www.margateholidays.com-Margate-rondevoux-21 - panoramio.jpg", "File:Coelacanth off Pumula on the KwaZulu-Natal South Coast, South Africa, on 22 November 2019.png", "File:Uvongo, KZN.jpg"],
    "seychelles": ["File:Anse Source d'Argent 2-La Digue.jpg", "File:Anse Source d'Argent - La Digue - Seychelles - 04.jpg", "File:Anse Source d'Argent - La Digue - Seychelles - 10.jpg", "File:Anse Source d'Argent - La Digue - Seychelles - 03.jpg", "File:Anse Source d'Argent - La Digue - Seychelles - 02.jpg"],
    "sharm-el-sheikh": ["File:Sharm El-Sheikh, Egypt ESA24580842.jpeg", "File:\u041d\u0430\u0431\u043a.jpg", "File:Naama Bay R01.jpg", "File:Sharm el-Sheikh - Naama bay.jpg", "File:Sharm el Sheikh Naama Bay - panoramio (10).jpg"],
    "sipadan-island": ["File:Sipadan Island.jpg", "File:Sipadan Island Sabah Malaysia.jpg", "File:Sipadan Kapalai Malezya 2.JPG", "File:Beneath Sipadan Island.jpeg", "File:Pulau Sipadan.jpg"],
    "socorro-island": ["File:Socorro Island, satellite image.png", "File:Socorro Island.jpg", "File:ISLA SOCORRO - panoramio.jpg", "File:NASA-Socorro-Island.jpg", "File:Iglesia Nuestra Se\u00f1ora del Socorro - Tejeda.jpg"],
    "tofo": ["File:Praia do Tofo Moz view 2008.jpg", "File:Tofo Market taken from Tofo Beach.JPG", "File:Tofo - Flickr - Martijn.Munneke (1).jpg", "File:Tofo - Flickr - Martijn.Munneke.jpg", "File:Tofo (6331294533).jpg"],
    "tubbataha-reefs-natural-park": [],
    "utila": ["File:Utila beach.jpg", "File:Utila Hondoras beach.jpg", "File:Typical Traffic Jam.jpg", "File:Road Near Munchies, Utila, Honduras.jpg", "File:Utila, Islas de la Bah\u00eda.jpg"],
    "yap": ["File:Yap Trying on Clothing.jpg", "File:US patrol boats, from Guam, visit Yap, Micronesia - 190703-N-LN093-1116.jpg", "File:Pacific Partnership 2024-2 Band Performs at Gilman Elementary School in Yap, Federated States of Micronesia (8643664).jpg", "File:Pacific Partnership 2024-2 Band Performs at Gilman Elementary School in Yap, Federated States of Micronesia (8643667).jpg", "File:Pacific Partnership 2024-2 Band Performs at Gilman Elementary School in Yap, Federated States of Micronesia (8643669).jpg"],
}
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
            titles = [t for t in titles if not ex.search(t) and t not in set(OFFERED.get(slug, []))]
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
