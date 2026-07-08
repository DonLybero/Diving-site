#!/usr/bin/env python3
"""Health-check every retailer buy link in gear-guide.json.

Runs on GitHub's runners (internet access) via .github/workflows/
check-buy-links.yml — the dev sandbox cannot reach retailer sites.

For every option URL (flat category items + wetsuit thickness_groups):
HEAD the URL (falling back to GET when HEAD is refused) with a realistic
browser User-Agent, small thread-pool concurrency and a per-domain
politeness delay. A link is DEAD when the final status is >= 400 or the
connection fails after 2 retries; a link that resolves to a different
URL is flagged REDIRECT (worth a look — retailers often redirect retired
products to category pages that still return 200).

Report-only: writes buy-link-report.json, appends a Markdown summary to
$GITHUB_STEP_SUMMARY when set, and always exits 0.

Usage: python3 scripts/check_buy_links.py [--out report.json]
"""
import json
import os
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urlsplit, urlunsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE = os.path.join(ROOT, "gear-guide.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 25          # seconds per request
RETRIES = 2           # extra attempts after a connection failure
WORKERS = 4           # thread-pool size (across domains)
DOMAIN_DELAY = 2.0    # min seconds between two requests to the same domain


def extract_urls(doc):
    """Every buy link in a gear-guide document, with its context.

    Returns a list of dicts: {category, group, item, store, price_usd, url}.
    Handles both flat categories (cat["items"]) and the Wetsuits category
    (cat["thickness_groups"][i]["items"]).
    """
    links = []

    def take(cat_name, group, item):
        for opt in item.get("options", []) or []:
            url = (opt.get("url") or "").strip()
            if not url:
                continue
            links.append({
                "category": cat_name,
                "group": group,
                "item": item.get("name", "?"),
                "store": opt.get("store", "?"),
                "price_usd": opt.get("price_usd"),
                "url": url,
            })

    for cat in doc.get("categories", []):
        cat_name = cat.get("category", "?")
        for item in cat.get("items", []) or []:
            take(cat_name, "", item)
        for grp in cat.get("thickness_groups", []) or []:
            for item in grp.get("items", []) or []:
                take(cat_name, grp.get("thickness", ""), item)
    return links


class _NoRaise(urllib.request.HTTPErrorProcessor):
    """Return 4xx/5xx responses instead of raising, still follow redirects."""

    def http_response(self, request, response):
        if 300 <= response.code < 400:
            return super().http_response(request, response)
        return response

    https_response = http_response


_OPENER = urllib.request.build_opener(
    _NoRaise, urllib.request.HTTPSHandler(context=ssl.create_default_context()))

_domain_locks = {}
_domain_last = {}
_registry_lock = threading.Lock()


def _polite_wait(domain):
    with _registry_lock:
        lock = _domain_locks.setdefault(domain, threading.Lock())
    with lock:
        wait = _domain_last.get(domain, 0) + DOMAIN_DELAY - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _domain_last[domain] = time.monotonic()


def _request(url, method):
    req = urllib.request.Request(url, headers=dict(HEADERS), method=method)
    with _OPENER.open(req, timeout=TIMEOUT) as resp:
        if method == "GET":
            resp.read(65536)  # enough to prove the page serves
        return resp.getcode(), resp.geturl()


def _normalize(url):
    """Comparison form: scheme/host lowercased, trailing slash trimmed."""
    s = urlsplit(url)
    path = s.path.rstrip("/") or "/"
    return urlunsplit((s.scheme.lower(), s.netloc.lower(), path, s.query, ""))


def check_url(url):
    """HEAD (GET fallback) with retries. Returns a result dict."""
    domain = urlparse(url).netloc
    error = None
    for attempt in range(1 + RETRIES):
        for method in ("HEAD", "GET"):
            _polite_wait(domain)
            try:
                code, final = _request(url, method)
            except (urllib.error.URLError, TimeoutError, ConnectionError,
                    ssl.SSLError, OSError) as e:
                error = str(getattr(e, "reason", e)) or e.__class__.__name__
                continue  # try GET, then the retry loop
            if method == "HEAD" and code in (400, 403, 405, 500, 501, 503):
                continue  # some retailers refuse HEAD — confirm with GET
            state = "DEAD" if code >= 400 else (
                "REDIRECT" if _normalize(final) != _normalize(url) else "OK")
            return {"state": state, "status": code, "final_url": final,
                    "method": method, "error": None}
        if attempt < RETRIES:
            time.sleep(2.0 * (attempt + 1))
    return {"state": "DEAD", "status": None, "final_url": None,
            "method": None, "error": error or "connection failed"}


def main():
    out_path = os.path.join(ROOT, "buy-link-report.json")
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]

    with open(GUIDE) as f:
        links = extract_urls(json.load(f))
    print(f"Checking {len(links)} buy links "
          f"({len({urlparse(l['url']).netloc for l in links})} domains)…")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda l: check_url(l["url"]), links))
    for link, res in zip(links, results):
        link.update(res)
        mark = {"OK": " ", "REDIRECT": "~", "DEAD": "!"}[res["state"]]
        print(f" {mark} [{res['status'] or 'ERR'}] {link['store']:<14} "
              f"{link['item']}: {link['url']}")

    counts = {s: sum(1 for l in links if l["state"] == s)
              for s in ("OK", "REDIRECT", "DEAD")}
    report = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "total": len(links), "counts": counts, "links": links}
    with open(out_path, "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print(f"\n{counts['OK']} ok, {counts['REDIRECT']} redirected, "
          f"{counts['DEAD']} dead — report: {out_path}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("## Buy-link health\n\n")
            f.write(f"**{counts['OK']} ok · {counts['REDIRECT']} redirected · "
                    f"{counts['DEAD']} dead** of {len(links)} links\n\n")
            bad = [l for l in links if l["state"] != "OK"]
            if not bad:
                f.write("All buy links resolve cleanly.\n")
            else:
                f.write("| State | Status | Category | Item | Store | URL | Note |\n")
                f.write("|---|---|---|---|---|---|---|\n")
                for l in bad:
                    cat = l["category"] + (f" {l['group']}" if l["group"] else "")
                    note = (l["error"] or
                            (f"→ {l['final_url']}" if l["state"] == "REDIRECT"
                             else "")).replace("|", "\\|")
                    f.write(f"| {l['state']} | {l['status'] or 'ERR'} | {cat} "
                            f"| {l['item']} | {l['store']} | {l['url']} "
                            f"| {note} |\n")
    return 0  # report-only: dead links never fail the run


if __name__ == "__main__":
    sys.exit(main())
