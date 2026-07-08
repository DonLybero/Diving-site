#!/usr/bin/env python3
"""Find freely licensed diver-entry videos on Wikimedia Commons, download the
best candidates and extract preview frames (runner-only; sandbox is
firewalled). Results go to vidcands/ for review:
  vidcands/<n>.webm            the candidate video (capped size)
  vidcands/<n>_f{1,2,3}.jpg    frames at 15% / 45% / 75% of duration
  vidcands/manifest.json       title, credit, license, duration, size
"""
import json, os, re, subprocess, time, urllib.parse, urllib.request

UA = {"User-Agent": "DiveSZNVideoFetch/1.0 (https://github.com/DonLybero/Diving-site)"}
OUT = "vidcands"
MAX_BYTES = 90_000_000
QUERIES = [
    "scuba diver entry water",
    "scuba diver jumps boat",
    "backward roll scuba",
    "giant stride entry",
    "scuba diver jumping sea",
    "diver entering water boat",
    "scuba diving boat entry video",
]
BAD = re.compile(r"(freedif|snorkel|cliff|pool_jump|high.?div|olympic|platform)", re.I)


def get(url, binary=False, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except Exception as e:
            if i == tries - 1:
                print(f"  ! {e} — {url[:80]}")
                return None
            time.sleep(2 * (i + 1))


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def main():
    os.makedirs(OUT, exist_ok=True)
    seen, cands = set(), []
    for q in QUERIES:
        j = get("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                "&list=search&srnamespace=6&srlimit=20&srsearch="
                + urllib.parse.quote(f"{q} filetype:video"))
        for h in ((j or {}).get("query", {}).get("search") or []):
            t = h["title"]
            if t in seen or BAD.search(t) or not re.search(r"\.(webm|ogv|mp4)$", t, re.I):
                continue
            seen.add(t)
            cands.append(t)
    print(f"{len(cands)} unique candidates")
    manifest = []
    n = 0
    for t in cands:
        if n >= 8:
            break
        j = get("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                "&prop=imageinfo&iiprop=url|size|extmetadata&titles="
                + urllib.parse.quote(t))
        pages = (j or {}).get("query", {}).get("pages") or {}
        for p in pages.values():
            ii = (p.get("imageinfo") or [{}])[0]
            size = ii.get("size", 0)
            w = ii.get("width", 0)
            dur = ii.get("duration") or 0
            if not ii.get("url"):
                print(f"  reject(no url) {t[:60]}"); continue
            if size > MAX_BYTES:
                print(f"  reject(size {size//1_000_000}MB) {t[:60]}"); continue
            if w and w < 480:
                print(f"  reject(width {w}) {t[:60]}"); continue
            if dur and (dur < 3 or dur > 180):
                print(f"  reject(duration {dur}s) {t[:60]}"); continue
            meta = ii.get("extmetadata") or {}
            lic = strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
            artist = strip_html((meta.get("Artist") or {}).get("value", "")) or "Wikimedia Commons"
            blob = get(ii["url"], binary=True)
            if not blob:
                continue
            n += 1
            ext = os.path.splitext(ii["url"])[1] or ".webm"
            path = f"{OUT}/{n}{ext}"
            with open(path, "wb") as f:
                f.write(blob)
            d = dur or 10
            for k, frac in ((1, .15), (2, .45), (3, .75)):
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(d * frac),
                                "-i", path, "-frames:v", "1", "-vf", "scale=640:-2",
                                f"{OUT}/{n}_f{k}.jpg"], check=False)
            manifest.append({"n": n, "title": t, "file": path, "bytes": size,
                             "width": w, "duration": dur, "license": lic, "artist": artist})
            print(f"  #{n} {t[:70]} · {size//1_000_000}MB · {dur}s · {lic}")
            time.sleep(0.4)
    with open(f"{OUT}/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"Done: {n} candidates")


if __name__ == "__main__":
    main()
