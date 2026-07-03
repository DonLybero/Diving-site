#!/usr/bin/env python3
"""Resolve and validate product images for gear-guide.json.

Runs on GitHub's runners (internet access) via .github/workflows/
fetch-gear-images.yml — the dev sandbox cannot reach retailer sites.

For every item: verify the existing image URL still serves an image; if
missing/broken, fetch the item's retailer product pages (cheapest first)
and extract og:image / twitter:image. Writes gear-guide.json in place.

Usage: python3 scripts/fetch_gear_images.py [--force]  (--force revalidates all)
"""
import json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE = os.path.join(ROOT, "gear-guide.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
FORCE = "--force" in sys.argv
LOCALIZE = "--localize" in sys.argv
ASSETS = os.path.join(ROOT, "assets", "gear")

# og:image results that are site chrome, not the product
BAD_IMG = re.compile(r"(logo|favicon|sprite|placeholder|banner|social|opengraph_default|og-image)", re.I)

# Extra product pages to try (manufacturer first) for items the retailer
# option pages could not provide a usable image for.
EXTRA_PAGES = {
    "Scubapro Seawing Nova": ["https://divecatalog.com/products/scubapro-seawing-nova-open-heel-scuba-diving-fin",
                              "https://lancasterscuba.com/products/spfnseawingnova"],
    "TUSA HyFlex Switch": ["https://divecatalog.com/products/tusa-hyflex-switch-fins",
                           "https://divecatalog.com/products/tusa-hyflex-switch-open-heel-scuba-diving-fins",
                           "https://tusa.com/us-en/TUSA/Fins/TUSA_HyFlex_Switch"],
    "Scubapro Go Sport": ["https://divecatalog.com/products/scubapro-go-sport-fins",
                          "https://divecatalog.com/products/scubapro-go-sport-travel-open-heel-scuba-diving-fin",
                          "https://divecatalog.com/products/scubapro-go-sport-open-heel-scuba-diving-fins"],
    "Atomic Aquatics T3": ["https://www.atomicaquatics.com/products/regulators/t3/",
                           "https://www.diverdans.com/product/atomic-t3-regulator/"],
    "Sherwood SR2": ["https://divecatalog.com/products/sherwood-sr2-din-regulator",
                     "https://www.scubatoys.com/products/3361-sherwood-sr2-regulator/",
                     "https://coralseascuba.com/sherwood-sr2-dive-regulator-scuba-diving-srb2000/"],
    "Cressi Travelight": ["https://store.cressi.com/products/travelight-bcd",
                          "https://cressiamerica.com/products/travelight",
                          "https://www.scuba.com/p-crstl/cressi-travelight-bcd"],
    "Mares Dragon SLS": ["https://www.mares.com/en/dragon-sls-417241",
                         "https://lancasterscuba.com/products/mares-dragon-sls-bcd"],
    "Suunto Zoop Novo": ["https://www.suunto.com/en-us/Products/dive-computers-and-instruments/suunto-zoop-novo/suunto-zoop-novo-black/",
                         "https://www.scuba.com/p-sunzn/suunto-zoop-novo-dive-computer"],
    "Cressi Leonardo": ["https://store.cressi.com/products/leonardo",
                        "https://www.scuba.com/p-crsleo/cressi-leonardo-dive-computer"],
}

SHOPIFY_IMG = re.compile(r'src="(https?://[^"]+/cdn/shop/(?:products|files)/[^"]+\.(?:jpe?g|png|webp)[^"]*)"', re.I)

def http_get(url, binary=False, limit=1_500_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read(limit)
        ctype = r.headers.get("Content-Type", "")
    return data, ctype

def is_live_image(url):
    try:
        data, ctype = http_get(url, binary=True, limit=40_000)
        return ctype.startswith("image/") and len(data) > 4000
    except Exception:
        return False

OG = re.compile(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)', re.I)
OG2 = re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']', re.I)

def page_image(url):
    try:
        html, ctype = http_get(url)
        if "html" not in ctype:
            return None
        text = html.decode("utf-8", "ignore")
        candidates = []
        m = OG.search(text) or OG2.search(text)
        if m:
            candidates.append(m.group(1))
        candidates += SHOPIFY_IMG.findall(text)[:3]
        for img in candidates:
            if img.startswith("//"):
                img = "https:" + img
            if not img.startswith("http") or BAD_IMG.search(img):
                continue
            if is_live_image(img):
                return img
        return None
    except Exception:
        return None


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def localize(item):
    """Download the item's image into assets/gear/ and point the data at it."""
    url = item.get("image") or ""
    if not url.startswith("http"):
        return
    try:
        data, ctype = http_get(url, limit=4_000_000)
        ext = ".png" if "png" in ctype else ".jpg"
        os.makedirs(ASSETS, exist_ok=True)
        fn = slugify(item["name"]) + ext
        with open(os.path.join(ASSETS, fn), "wb") as f:
            f.write(data)
        item["image"] = "assets/gear/" + fn
        print(f"    ↓ localized → assets/gear/{fn} ({len(data)//1024}KB)")
    except Exception as e:
        print(f"    ! localize failed ({e}) — keeping remote URL")

def main():
    with open(GUIDE) as f:
        doc = json.load(f)
    fixed = kept = failed = 0
    for cat in doc["categories"]:
        for it in cat["items"]:
            cur = it.get("image") or ""
            if cur.startswith("assets/") and not FORCE:
                kept += 1
                continue
            if cur.startswith("http") and BAD_IMG.search(cur):
                cur = ""                                     # logos don't count as images
            if cur and not FORCE and is_live_image(cur):
                if LOCALIZE:
                    localize(it)
                kept += 1
                continue
            found = None
            for page in EXTRA_PAGES.get(it["name"], []) + [o.get("url", "") for o in it.get("options", [])]:
                found = page_image(page)
                if found:
                    break
            if found:
                it["image"] = found
                if LOCALIZE:
                    localize(it)
                fixed += 1
                print(f"  ✓ {it['name']} ← {found[:80]}")
            else:
                if cur and not is_live_image(cur):
                    it["image"] = ""       # drop broken URL → icon fallback
                failed += 1
                print(f"  ✗ {it['name']}: no image found")
    with open(GUIDE, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    print(f"kept {kept}, fixed {fixed}, unresolved {failed}")

if __name__ == "__main__":
    main()
