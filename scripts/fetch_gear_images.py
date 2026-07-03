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
        m = OG.search(text) or OG2.search(text)
        if not m:
            return None
        img = m.group(1)
        if img.startswith("//"):
            img = "https:" + img
        if not img.startswith("http"):
            return None
        return img if is_live_image(img) else None
    except Exception:
        return None

def main():
    with open(GUIDE) as f:
        doc = json.load(f)
    fixed = kept = failed = 0
    for cat in doc["categories"]:
        for it in cat["items"]:
            cur = it.get("image") or ""
            if cur and not FORCE and is_live_image(cur):
                kept += 1
                continue
            found = None
            for opt in it.get("options", []):
                found = page_image(opt.get("url", ""))
                if found:
                    break
            if found:
                it["image"] = found
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
