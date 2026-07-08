#!/usr/bin/env python3
"""Find freely licensed diver/underwater videos via bot-friendly archives:
Wikimedia Commons category enumeration + the Internet Archive search API.
Downloads candidates and extracts preview frames for sandbox review.
Outputs: vidcands/<n>.<ext>, vidcands/<n>_f{1,2,3}.jpg, vidcands/manifest.json
"""
import json, os, re, subprocess, time, urllib.parse, urllib.request

UA = {"User-Agent": "DiveSZNVideoFetch/1.0 (https://github.com/DonLybero/Diving-site)"}
OUT = "vidcands"
MAX_BYTES = 120_000_000
CAP = 10

COMMONS_CATS = [
    "Category:Videos of scuba diving",
    "Category:Videos of underwater diving",
    "Category:Scuba diving videos",
    "Category:Videos of divers",
    "Category:Videos of snorkeling",  # entries often mislabelled; frames decide
]
BAD = re.compile(r"(interview|lecture|conference|memorial|presentation|slideshow|screencast)", re.I)


def get(url, binary=False, tries=3, timeout=90):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except Exception as e:
            if i == tries - 1:
                print(f"  ! {e} — {url[:90]}")
                return None
            time.sleep(2 * (i + 1))


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def frames(path, n, dur):
    for k, frac in ((1, .12), (2, .45), (3, .8)):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(max(0.5, dur * frac)),
                        "-i", path, "-frames:v", "1", "-vf", "scale=640:-2",
                        f"{OUT}/{n}_f{k}.jpg"], check=False)


def commons_candidates(manifest):
    n = len(manifest)
    for cat in COMMONS_CATS:
        if n >= CAP:
            break
        j = get("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                "&list=categorymembers&cmtype=file&cmlimit=100&cmtitle="
                + urllib.parse.quote(cat))
        members = ((j or {}).get("query", {}).get("categorymembers")) or []
        vids = [m["title"] for m in members
                if re.search(r"\.(webm|ogv|mp4)$", m["title"], re.I) and not BAD.search(m["title"])]
        print(f"{cat}: {len(vids)} video files")
        for t in vids:
            if n >= CAP:
                break
            j2 = get("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                     "&prop=imageinfo&iiprop=url|size|extmetadata&titles=" + urllib.parse.quote(t))
            for p in ((j2 or {}).get("query", {}).get("pages") or {}).values():
                ii = (p.get("imageinfo") or [{}])[0]
                size = ii.get("size", 0)
                dur = ii.get("duration") or 0
                if not ii.get("url") or size > MAX_BYTES or (dur and (dur < 3 or dur > 240)):
                    print(f"  reject {t[:60]} size={size//1_000_000}MB dur={dur}")
                    continue
                blob = get(ii["url"], binary=True, timeout=180)
                if not blob:
                    continue
                n += 1
                ext = os.path.splitext(ii["url"])[1] or ".webm"
                path = f"{OUT}/{n}{ext}"
                open(path, "wb").write(blob)
                meta = ii.get("extmetadata") or {}
                frames(path, n, dur or 10)
                manifest.append({"n": n, "source": "commons", "title": t,
                                 "bytes": size, "duration": dur,
                                 "license": strip_html((meta.get("LicenseShortName") or {}).get("value", "")),
                                 "artist": strip_html((meta.get("Artist") or {}).get("value", ""))})
                print(f"  #{n} {t[:64]} · {size//1_000_000}MB · {dur}s")
                time.sleep(0.5)


def archive_candidates(manifest):
    n = len(manifest)
    if n >= CAP:
        return
    q = urllib.parse.quote('(scuba OR "skin diving" OR frogman) AND mediatype:(movies)')
    j = get(f"https://archive.org/advancedsearch.php?q={q}&fl[]=identifier&fl[]=title"
            f"&rows=12&page=1&output=json")
    docs = ((j or {}).get("response", {}).get("docs")) or []
    print(f"archive.org: {len(docs)} results")
    for d in docs:
        if n >= CAP:
            break
        ident = d["identifier"]
        meta = get(f"https://archive.org/metadata/{ident}")
        files = (meta or {}).get("files") or []
        best = None
        for f in files:
            name = f.get("name", "")
            if re.search(r"(512kb\.mp4|\.mp4)$", name, re.I):
                sz = int(f.get("size") or 0)
                if sz and sz <= MAX_BYTES and (best is None or sz < best[1]):
                    best = (name, sz)
        if not best:
            continue
        url = f"https://archive.org/download/{ident}/{urllib.parse.quote(best[0])}"
        blob = get(url, binary=True, timeout=300)
        if not blob:
            continue
        n += 1
        path = f"{OUT}/{n}.mp4"
        open(path, "wb").write(blob)
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", path], capture_output=True, text=True)
        try:
            dur = float((probe.stdout or "").strip())
        except ValueError:
            dur = 60.0
        frames(path, n, dur)
        manifest.append({"n": n, "source": "archive.org", "title": d.get("title", ident),
                         "id": ident, "bytes": len(blob), "duration": dur,
                         "license": "public domain / archive.org", "artist": ident})
        print(f"  #{n} {ident} · {len(blob)//1_000_000}MB · {dur:.0f}s")
        time.sleep(0.5)


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = []
    commons_candidates(manifest)
    archive_candidates(manifest)
    with open(f"{OUT}/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"Done: {len(manifest)} candidates")


if __name__ == "__main__":
    main()
