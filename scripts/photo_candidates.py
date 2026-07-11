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
PER_DEST = 10

CANDIDATE_QUERIES = {
    # Owner round 2026-07-11 v2: Protea Banks hero — KZN south coast only.
    # "Shelly Beach" alone is ambiguous on Commons (Sydney beaches) — use
    # town names that only exist on this coast.
    "protea-banks": ["Margate beach South Africa", "Uvongo Beach",
                     "Uvongo KwaZulu-Natal", "Ramsgate KwaZulu-Natal",
                     "Port Shepstone", "Hibberdene", "Umzumbe",
                     "KwaZulu-Natal south coast"],
}

EXCLUDE = {}
OFFERED = {
    "bahamas": ["File:Bahamas 1989 (591) Great Exuma (24986096444).jpg", "File:Bahamas 1989 (589) Great Exuma (25497769082).jpg", "File:Bahamas 1989 (588) Great Exuma (25474038752).jpg", "File:Bahamas 1989 (592) Exuma (25249275789).jpg", "File:Bahamas 1989 (757) Exuma Islands (26229646886).jpg", "File:Bahamas 1989 (342) Eleuthera Harbour Island (24320422055).jpg", "File:Bahamas 1989 (343) Eleuthera Harbour Island (24211710172).jpg", "File:Bahamas 1989 (384) Eleuthera Spanish Wells, St. George's Cay (24470041926).jpg", "File:Bahamas 1989 (387) Eleuthera Spanish Wells, St. George's Cay (24422334811).jpg", "File:Bahamas 1989 (382) Eleuthera Spanish Wells, St. George's Cay (24484777015).jpg"],
    "bay-islands": ["File:Aerial view of West End, Roatan.jpg", "File:Aerial view of Coxen Hole, Roatan.jpg", "File:Roatan looking north towards West End.jpg", "File:West Bay Beach -Roatan -Honduras-23May2009.jpg", "File:West Bay Beach -Roatan -Honduras-23May2009-g.jpg", "File:West Bay Beach -Roatan -Honduras-23May2009-c.jpg", "File:West Bay Beach -Roatan -Honduras-23May2009-e.jpg", "File:West Bay Beach -Roatan -Honduras-23May2009-f.jpg", "File:West Bay Beach -Roatan -Honduras-23May2009-b.jpg", "File:West Bay Beach -Roatan -Honduras-23May2009-d.jpg"],
    "fiji": ["File:Denarau Island, Fiji, 2013 (4).jpg", "File:(Aerial view within Lau Islands, Fiji) - DPLA - 989763b50815d9f178c4fa35d37db744.jpg", "File:(Aerial view of island coastline within Lau Islands, Fiji) - DPLA - f5061f4c9d9bfc4e84d472836007c77c.jpg", "File:(Aerial view within Lau Islands, Fiji) - DPLA - 12024e0c8e93db30dd2768949350d564.jpg", "File:(Aerial view of island coastline within Lau Islands, Fiji) - DPLA - 8b343058f67792ba5d0f985d9f943a5b.jpg", "File:2004.03.20 Mamanucas Fiji.jpg", "File:Mamanuca island.jpg", "File:Mamanuca Islands - panoramio.jpg", "File:Mamanuca Islands.jpg", "File:Mamanuca Islands - panoramio (1).jpg"],
    "layang-layang": ["File:Swallow Reef10.jpg", "File:Swallow Reef, Spratly Islands.png", "File:Swallow Reef2.jpg", "File:Swallow Reef sea3.jpg", "File:Swallow Reef sea4.jpg", "File:Tizard Bank, Spratly Islands.png", "File:Dallas Reef, Spratly Islands.png", "File:Investigator Shoal, Spratly Islands.png", "File:Cornwallis South Reef, Spratly Islands.png", "File:1945. Aerial view of Seaside airstrip. Hemlock looper control project. Clatsop County, Oregon. (33113342780).jpg"],
    "malapascua-island": ["File:Malapascua (island), Tropical beach, Philippines.jpg", "File:Malapascua Island, Tropical sunset on the beach 2, Philippines.jpg", "File:Malapascua Island, Sunset on the beach 2, Philippines.jpg", "File:Malapascua (island), Bounty Beach, Philippines.jpg", "File:Malapascua (island), Palm trees on the sandy beach, Philippines.jpg", "File:Malapascua Island 1.jpg", "File:BRP Malapascua commissioning.jpg", "File:Malapascua, Filipino children on the beach, Philippines.jpg", "File:Malapascua, Silence, Visayan Sea, Philippines.jpg", "File:Malapascua (island), Philippines.jpg"],
    "marsa-alam": ["File:Marsa Alam R02.jpg", "File:Marsa Alam R05.jpg", "File:Marsa Alam R08.jpg", "File:\u00c4gypten, Marsa Alam 2H1A1738WI.jpg", "File:Sonnenuntergang in Marsa Alam 2H1A2138WI.jpg", "File:Marsa Alam R15.jpg", "File:Marsa Alam R10.jpg", "File:Marsa Alam, Egypt 2007feb08 byDanielCsorfoly.JPG", "File:Sonnenuntergang in Marsa Alam 2H1A2137WI.jpg", "File:Marsa-el-Alam aeroportul.jpg"],
    "muscat-daymaniyat-islands": ["File:Dimaniyat Islands 2.jpg", "File:Cherna ar\u00e1biga (Cephalopholis hemistiktos), islas Ad Dimaniyat, Om\u00e1n, 2024-08-13, DD 17.jpg", "File:Pez erizo moteado (Diodon hystrix), islas Ad Dimaniyat, Om\u00e1n, 2024-08-15, DD 76.jpg", "File:Apog\u00f3nido (Ostorhinchus aureus), islas Ad Dimaniyat, Om\u00e1n, 2024-08-15, DD 05.jpg", "File:Beach in Al Dimaniyyat Islands Nature Reserve in Oman (53697748816).jpg", "File:Tortuga carey (Eretmochelys imbricata), islas Ad Dimaniyat, Om\u00e1n, 2024-08-13, DD 69.jpg", "File:Bl\u00e9nido (Ecsenius pulcher), islas Ad Dimaniyat, Om\u00e1n, 2024-08-15, DD 53.jpg", "File:Pez cofre azul (Ostracion cyanurus), islas Ad Dimaniyat, Om\u00e1n, 2024-08-13, DD 98.jpg", "File:Tortuga carey (Eretmochelys imbricata), islas Ad Dimaniyat, Om\u00e1n, 2024-08-15, DD 15.jpg", "File:Morena leopardo (Gymnothorax favagineus), islas Ad Dimaniyat, Om\u00e1n, 2024-08-13, DD 84.jpg"],
    "sharm-el-sheikh": ["File:Sharm El-Sheikh, Egypt ESA24580842.jpeg", "File:\u041d\u0430\u0431\u043a.jpg", "File:Naama Bay R01.jpg", "File:Sharm el-Sheikh - Naama bay.jpg", "File:Sharm el Sheikh Naama Bay - panoramio (10).jpg", "File:Sharm el Sheikh R01.jpg", "File:Sharm El Sheikh El-Maya Bay - panoramio.jpg", "File:Sharm El Sheikh El-Maya Bay - panoramio (4).jpg", "File:Sharm El Sheikh El-Maya Bay - panoramio (3).jpg", "File:Sharm el Sheikh Naama Bay - panoramio (11).jpg"],
    "sipadan-island": ["File:Sipadan Island.jpg", "File:Sipadan Island Sabah Malaysia.jpg", "File:Sipadan Kapalai Malezya 2.JPG", "File:Beneath Sipadan Island.jpeg", "File:Pulau Sipadan.jpg", "File:Hawksbill Sipadan.jpg", "File:Plectorhinchus chaetodonoides.JPG", "File:PC220097 Chlorodesmis.jpg", "File:Simpadan Island Semporna.jpg", "File:P2020302.JPG"],
    "tofo": ["File:Praia do Tofo Moz view 2008.jpg", "File:Tofo Market taken from Tofo Beach.JPG", "File:Tofo - Flickr - Martijn.Munneke (1).jpg", "File:Tofo - Flickr - Martijn.Munneke.jpg", "File:Tofo (6331294533).jpg", "File:Heliotropium foertherianum at Tofo beach (14734433305).jpg", "File:Cine Teatro Tofo in Inhambane (Mozambique).jpg", "File:Tofo Danse - 2.jpg", "File:Praia do Tofo, RTW 2012 (8357003713).jpg", "File:Praia do Tofo, RTW 2012 (8358043966).jpg"],
    "utila": ["File:Utila beach.jpg", "File:Utila Hondoras beach.jpg", "File:Typical Traffic Jam.jpg", "File:Road Near Munchies, Utila, Honduras.jpg", "File:Utila, Islas de la Bah\u00eda.jpg"],
    "yap": ["File:Yap Trying on Clothing.jpg", "File:US patrol boats, from Guam, visit Yap, Micronesia - 190703-N-LN093-1116.jpg", "File:Pacific Partnership 2024-2 Band Performs at Gilman Elementary School in Yap, Federated States of Micronesia (8643664).jpg", "File:Pacific Partnership 2024-2 Band Performs at Gilman Elementary School in Yap, Federated States of Micronesia (8643667).jpg", "File:Pacific Partnership 2024-2 Band Performs at Gilman Elementary School in Yap, Federated States of Micronesia (8643669).jpg", "File:Pacific Partnership 2024-2 Band Performs at Gilman Elementary School in Yap, Federated States of Micronesia (8643673).jpg", "File:Pacific Partnership 2024-2 Band Performs at Gilman Elementary School in Yap, Federated States of Micronesia (8643665).jpg", "File:Pacific Partnership 2024-2 Band Performs at Gilman Elementary School in Yap, Federated States of Micronesia (8643666).jpg", "File:CDRUSINDOPACOM Travels to Yap, Pohnpei in the Federated States of Micronesia (7688262).jpg", "File:Colonia1 Yap NOAA.jpg"],
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



def category_files(place_q, limit=40):
    """Enumerate image files from Commons categories matching the place."""
    j = _get("https://commons.wikimedia.org/w/api.php?action=query&format=json"
             "&list=search&srnamespace=14&srlimit=4&srsearch=" + urllib.parse.quote(place_q))
    cats = [h["title"] for h in (((j or {}).get("query") or {}).get("search")) or []]
    titles = []
    for cat in cats[:3]:
        j2 = _get("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                  "&list=categorymembers&cmtype=file&cmlimit=%d&cmtitle=" % limit
                  + urllib.parse.quote(cat))
        for mem in (((j2 or {}).get("query") or {}).get("categorymembers")) or []:
            t = mem["title"]
            if re.search(r"\.(jpe?g|png)$", t, re.I) and not BAD_HINT.search(t):
                titles.append(t)
    return titles


def openverse(q, need, exclude_urls):
    """CC-licensed images from the Openverse index (cc0/by/by-sa only)."""
    out = []
    url = ("https://api.openverse.org/v1/images/?format=json&license=cc0,by,by-sa"
           "&extension=jpg&page_size=20&q=" + urllib.parse.quote(q))
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            j = json.loads(r.read())
    except Exception as e:
        print("  openverse fail:", e)
        return out
    for it in (j.get("results") or []):
        if len(out) >= need:
            break
        w, h = it.get("width") or 0, it.get("height") or 0
        u = it.get("url") or ""
        if w < 800 or h < 450 or (w and h and h > w * 1.1) or u in exclude_urls:
            continue
        lic = (it.get("license") or "").upper()
        creator = it.get("creator") or "Unknown"
        src_site = it.get("source") or "Openverse"
        out.append({"title": "ov:" + str(it.get("id") or u), "url": u,
                    "credit": f"Photo: {creator} ({lic}) via {src_site}"})
        time.sleep(1.2)
    return out


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
        if len(picked) < PER_DEST:
            ctitles = [t for t in category_files(queries[0])
                       if t not in seen and t not in set(OFFERED.get(slug, []))]
            ex = EXCLUDE.get(slug) or TOPSIDE_EXCLUDE
            ctitles = [t for t in ctitles if not ex.search(t)]
            info = file_info(ctitles[:24])
            for t in ctitles:
                if t not in info or len(picked) >= PER_DEST:
                    continue
                url, credit = info[t]
                seen.add(t)
                idx = len(picked) + 1
                path = f"cands/{slug}_{idx}.jpg"
                if grab(url, path):
                    picked.append({"title": t, "url": url, "credit": credit, "file": path})
                    print(f"  {slug} #{idx} (category): {t[:64]}")
        if len(picked) < PER_DEST:
            have = {p["url"] for p in picked}
            for c in openverse(queries[0], PER_DEST - len(picked), have):
                idx = len(picked) + 1
                path = f"cands/{slug}_{idx}.jpg"
                if grab(c["url"], path):
                    c["file"] = path
                    picked.append(c)
                    print(f"  {slug} #{idx} (openverse): {c['credit'][:64]}")
        manifest[slug] = picked
        print(f"{slug}: {len(picked)} candidates")
    with open("cands/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
