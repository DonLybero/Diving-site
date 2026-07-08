#!/usr/bin/env python3
"""Fetch official product photos (and per-colour variant photos) from gear
manufacturers' own product pages.

Input:  scripts/data/brand_pages.json
        {"<item name>": {"url": "https://brand.com/...", "shopify": true}}
Output: brandshots/<item-slug>/<n>__<colour-or-main>.<ext> + brandshots/manifest.json

Two extraction strategies:
  - Shopify stores (URL contains /products/): GET <url>.json — the product
    JSON lists options, variants and images; when a "Color" option exists we
    map each colour value to its variant image.
  - Anything else: parse the HTML for JSON-LD Product blocks (image + color
    fields) and og:image as a fallback.

Runs on GitHub runners (the dev sandbox is firewalled) via
.github/workflows/fetch-brand-photos.yml.
"""
import json, os, re, sys, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "scripts", "data", "brand_pages.json")
OUT = "brandshots"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
      "Accept-Language": "en"}


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def get(url, binary=False, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            return data if binary else data.decode("utf-8", "replace")
        except Exception as e:
            if i == tries - 1:
                print(f"    ! {url.split('//')[-1][:60]}: {e}")
                return None
            time.sleep(2 * (i + 1))


def norm_img(u, base):
    if not u:
        return None
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        p = urllib.parse.urlparse(base)
        return f"{p.scheme}://{p.netloc}{u}"
    return u


def from_shopify(url):
    j = get(url.rstrip("/") + ".json")
    if not j:
        return None
    try:
        p = json.loads(j)["product"]
    except Exception:
        return None
    out = {"main": None, "colors": {}}
    imgs = p.get("images") or []
    if imgs:
        out["main"] = imgs[0].get("src")
    copt = None
    for i, o in enumerate(p.get("options") or []):
        if (o.get("name") or "").strip().lower() in ("color", "colour"):
            copt = i + 1
    if copt:
        img_by_id = {im["id"]: im.get("src") for im in imgs}
        for v in p.get("variants") or []:
            cname = v.get(f"option{copt}")
            if cname and v.get("image_id") and cname not in out["colors"]:
                src = img_by_id.get(v["image_id"])
                if src:
                    out["colors"][cname] = src
    return out


def from_html(url):
    html = get(url)
    if not html:
        return None
    out = {"main": None, "colors": {}}
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            for n in ([node] + (node.get("@graph") or [] if isinstance(node, dict) else [])):
                if not isinstance(n, dict) or n.get("@type") not in ("Product", ["Product"]):
                    continue
                img = n.get("image")
                if isinstance(img, list):
                    img = img[0] if img else None
                if isinstance(img, dict):
                    img = img.get("url")
                if img and not out["main"]:
                    out["main"] = norm_img(img, url)
                col = n.get("color")
                if isinstance(col, str) and col and img:
                    out["colors"].setdefault(col, norm_img(img, url))
    if not out["main"]:
        m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html) or \
            re.search(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', html)
        if m:
            out["main"] = norm_img(m.group(1), url)
    return out


def main():
    with open(SRC, encoding="utf-8") as f:
        pages = json.load(f)
    os.makedirs(OUT, exist_ok=True)
    manifest = {}
    for name, info in pages.items():
        url = (info or {}).get("url")
        if not url:
            continue
        slug = slugify(name)
        print(f"{name} -> {url[:70]}")
        res = (from_shopify(url) if "/products/" in url else None) or from_html(url)
        if not res or not (res.get("main") or res.get("colors")):
            print("    · nothing extracted")
            continue
        d = os.path.join(OUT, slug)
        os.makedirs(d, exist_ok=True)
        entry = {"url": url, "main": None, "colors": {}}
        def save(img_url, label, idx):
            ext = os.path.splitext(urllib.parse.urlparse(img_url).path)[1].lower() or ".jpg"
            if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                ext = ".jpg"
            fn = f"{idx}__{slugify(label)}{ext}"
            blob = get(img_url.split("?")[0] + ("?width=1600" if "cdn.shopify" in img_url else ""), binary=True)
            if not blob or len(blob) < 5000:
                return None
            with open(os.path.join(d, fn), "wb") as f:
                f.write(blob)
            time.sleep(0.4)
            return f"{slug}/{fn}"
        if res.get("main"):
            entry["main"] = save(res["main"], "main", 0)
        for i, (cname, curl) in enumerate(sorted((res.get("colors") or {}).items()), 1):
            p = save(curl, cname, i)
            if p:
                entry["colors"][cname] = p
        manifest[name] = entry
        print(f"    · main={'yes' if entry['main'] else 'no'} colors={list(entry['colors'])}")
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    got = sum(1 for e in manifest.values() if e.get("main") or e.get("colors"))
    print(f"Done: {got}/{len(pages)} items with photos")


if __name__ == "__main__":
    main()
