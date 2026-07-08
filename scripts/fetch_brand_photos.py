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


# ---------------------------------------------------------------------------
# Variant mode: per-colour photos for items listed in scripts/data/colorwork.json
#   {"<item>": {"urls": [...], "colors": [...], "platform": "...", "base": "<file base>"}}
# Output: brandshots/variants/<base>--<colour-slug>.<ext> + brandshots/variants/manifest.json
# ---------------------------------------------------------------------------
CWORK = os.path.join(ROOT, "scripts", "data", "colorwork.json")


def norm_color(c):
    c = re.sub(r"\b(lens|mirrored?|tint(ed)?)\b", "", c.lower())
    return re.sub(r"[^a-z0-9]+", "", c)


def match_color(extracted, wanted):
    """Map an extracted colour label onto one of our colour names (or None)."""
    ne = norm_color(extracted)
    if not ne:
        return None
    byn = {norm_color(w): w for w in wanted}
    if ne in byn:
        return byn[ne]
    for nw, w in byn.items():
        if nw and (nw in ne or ne in nw):
            return w
    return None


def html_unescape(s):
    return (s.replace("&quot;", '"').replace("&#034;", '"').replace("&#039;", "'")
             .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))


def woo_variations(url):
    """WooCommerce puts the full variation list (attributes + image) in the
    add-to-cart form's data-product_variations attribute."""
    html = get(url)
    if not html:
        return {}
    m = re.search(r'data-product_variations="([^"]+)"', html)
    if not m:
        return {}
    try:
        variations = json.loads(html_unescape(m.group(1)))
    except Exception:
        return {}
    out = {}
    for v in variations if isinstance(variations, list) else []:
        attrs = v.get("attributes") or {}
        cname = None
        for k, val in attrs.items():
            if "color" in k.lower() or "colour" in k.lower():
                cname = val
        img = (v.get("image") or {}).get("full_src") or (v.get("image") or {}).get("src")
        if cname and img:
            out.setdefault(cname.replace("-", " "), norm_img(img, url))
    return out


def woo_store_api(url):
    """WooCommerce Store API fallback: /wp-json/wc/store/v1/products?slug=…"""
    p = urllib.parse.urlparse(url)
    slug = [s for s in p.path.split("/") if s][-1]
    j = get(f"{p.scheme}://{p.netloc}/wp-json/wc/store/v1/products?slug={slug}")
    if not j:
        return {}
    try:
        prods = json.loads(j)
    except Exception:
        return {}
    out = {}
    for prod in prods if isinstance(prods, list) else []:
        for v in prod.get("variations") or []:
            cname = None
            for a in v.get("attributes") or []:
                if "color" in (a.get("name") or "").lower():
                    cname = a.get("value")
            if not cname or cname in out:
                continue
            vj = get(f"{p.scheme}://{p.netloc}/wp-json/wc/store/v1/products/{v['id']}")
            if not vj:
                continue
            try:
                vd = json.loads(vj)
            except Exception:
                continue
            imgs = vd.get("images") or []
            if imgs:
                out[cname.replace("-", " ")] = imgs[0].get("src")
            time.sleep(0.3)
    return out


def prestashop_combinations(url):
    """PrestaShop keeps per-combination images in the product JSON blob
    (data-product attribute or `var combinations`)."""
    html = get(url)
    if not html:
        return {}
    out = {}
    m = re.search(r'data-product="([^"]+)"', html)
    if m:
        try:
            data = json.loads(html_unescape(m.group(1)))
            imgs_by_id = {}
            for im in data.get("images") or []:
                src = ((im.get("bySize") or {}).get("large_default") or {}).get("url") or im.get("large", {}).get("url")
                if src:
                    imgs_by_id[im.get("id_image") or im.get("id")] = src
            for comb in (data.get("combinations") or {}).values() if isinstance(data.get("combinations"), dict) else []:
                cname = comb.get("attributes_values")
                if isinstance(cname, dict):
                    cname = " / ".join(str(v) for v in cname.values())
                iid = (comb.get("associated_images") or [None])[0]
                if cname and iid in imgs_by_id:
                    out.setdefault(cname, imgs_by_id[iid])
        except Exception:
            pass
    return out


def gallery_alt_match(url, wanted):
    """Last resort: product-gallery <img> tags whose alt text or file name
    carries one of the wanted colour names. Only exact-token matches."""
    html = get(url)
    if not html:
        return {}
    out = {}
    for m in re.finditer(r'<img[^>]+>', html):
        tag = m.group(0)
        srcm = re.search(r'(?:data-src|data-image|src)="([^"]+)"', tag)
        if not srcm:
            continue
        src = srcm.group(1)
        if src.startswith("data:") or ".svg" in src:
            continue
        altm = re.search(r'alt="([^"]*)"', tag)
        hay = ((altm.group(1) if altm else "") + " " +
               os.path.basename(urllib.parse.urlparse(src).path)).lower()
        toks = set(re.split(r"[^a-z0-9]+", hay))
        for w in wanted:
            parts = [t for t in re.split(r"[^a-z0-9]+", w.lower()) if t and t not in ("lens", "mirrored")]
            if parts and all(p in toks for p in parts) and w not in out:
                out[w] = norm_img(src, url)
    return out


def variant_mode():
    with open(CWORK, encoding="utf-8") as f:
        work = json.load(f)
    d = os.path.join(OUT, "variants")
    os.makedirs(d, exist_ok=True)
    manifest = {}
    for name, info in work.items():
        wanted = info["colors"]
        base = info["base"] or slugify(name)
        print(f"{name}  [{info.get('platform')}]")
        found = {}      # our-colour-name -> (img_url, strategy)
        for url in info.get("urls") or []:
            strategies = []
            if "/products/" in url:
                strategies.append(("shopify", lambda u=url: (from_shopify(u) or {}).get("colors") or {}))
            strategies += [("woo", lambda u=url: woo_variations(u)),
                           ("woo-api", lambda u=url: woo_store_api(u)),
                           ("presta", lambda u=url: prestashop_combinations(u)),
                           ("jsonld", lambda u=url: (from_html(u) or {}).get("colors") or {}),
                           ("alt", lambda u=url: gallery_alt_match(u, wanted))]
            for sname, fn in strategies:
                try:
                    got = fn() or {}
                except Exception as e:
                    print(f"    ! {sname}: {e}")
                    continue
                for cname, curl in got.items():
                    ours = cname if cname in wanted else match_color(cname, wanted)
                    if ours and ours not in found and curl:
                        found[ours] = (curl, sname)
                if len(found) == len(wanted):
                    break
            if len(found) == len(wanted):
                break
        entry = {"colors": {}, "missing": [c for c in wanted if c not in found]}
        seen_blobs = {}
        for cname, (curl, sname) in found.items():
            ext = os.path.splitext(urllib.parse.urlparse(curl).path)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                ext = ".jpg"
            fetch_url = curl.split("?")[0] + ("?width=1600" if "cdn.shopify" in curl else "")
            blob = get(fetch_url, binary=True)
            if not blob or len(blob) < 5000:
                entry["missing"].append(cname)
                continue
            h = hash(blob)
            if h in seen_blobs:
                # same photo for two colours = the site has no real per-colour
                # image; keep only the first
                entry["missing"].append(cname)
                continue
            seen_blobs[h] = cname
            fn = f"{base}--{slugify(cname)}{ext}"
            with open(os.path.join(d, fn), "wb") as f:
                f.write(blob)
            entry["colors"][cname] = {"file": f"variants/{fn}", "strategy": sname, "src": curl}
            time.sleep(0.4)
        manifest[name] = entry
        print(f"    · got {len(entry['colors'])}/{len(wanted)}: {list(entry['colors'])}")
    with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    full = sum(1 for e in manifest.values() if not e["missing"])
    some = sum(1 for e in manifest.values() if e["colors"])
    print(f"Done: {some}/{len(work)} items with at least one variant photo ({full} complete)")


def main():
    if os.path.exists(CWORK):
        os.makedirs(OUT, exist_ok=True)
        variant_mode()
        return
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
