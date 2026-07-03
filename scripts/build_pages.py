#!/usr/bin/env python3
"""Generate static, crawlable per-destination pages for SEO.

Reads diving-destinations.json and writes:
  destinations/<slug>.html    one full page per destination (no JS required)
  destinations/index.html     A-Z directory of all destinations
  sitemap.xml                 root + directory + every destination page
  robots.txt                  allow-all + sitemap pointer

The SPA (index.html) stays the interactive app; these pages give search
engines one indexable URL per destination with the same researched data.
Re-run after any data change:  python3 scripts/build_pages.py
"""
import json, os, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://donlybero.github.io/Diving-site/"
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
RCOLOR = {"Peak":"#16a34a","Good":"#0ea5e9","Shoulder":"#eab308","Low":"#f97316","Closed":"#64748b"}
TODAY = "2026-07-01"

CSS = """
:root{--bg:#04202b;--panel:#0a3340;--ink:#e9f7f6;--muted:#86c2c6;--accent:#2fe0d6;--coral:#ff7a59;--line:#155060;
--serif:Georgia,'Iowan Old Style','Times New Roman',serif;--mono:ui-monospace,'SF Mono',Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;
background:linear-gradient(180deg,#062a36,#03171f);color:var(--ink);min-height:100vh}
a{color:var(--accent)}h1,h2{font-family:var(--serif);font-weight:600}
.topbar{display:flex;align-items:center;gap:11px;padding:10px 18px;background:rgba(4,26,34,.92);border-bottom:1px solid var(--line)}
.topbar a{display:inline-flex;align-items:center;gap:11px;text-decoration:none;color:var(--ink)}
.topbar .name{font-family:var(--serif);font-size:1.3rem}.topbar .name b{color:var(--accent);font-weight:600}
.topbar .tag{color:var(--muted);font-size:.62rem;font-family:var(--mono);letter-spacing:.24em;text-transform:uppercase}
.hero{position:relative;padding:64px 18px 40px;text-align:center;background-size:cover;background-position:center 40%;border-bottom:1px solid var(--line)}
.hero h1{font-size:clamp(1.9rem,5vw,3rem);margin:0}.hero p{color:#d6f3f0;max-width:60ch;margin:10px auto 0}
.hero .credit{position:absolute;right:10px;bottom:6px;font-size:.6rem;color:rgba(233,247,246,.55);font-family:var(--mono)}
.wrap{max-width:900px;margin:0 auto;padding:20px 16px 60px}
.best{background:linear-gradient(90deg,#0c4d3d,#0a3340);border:1px solid #1c7a63;border-radius:10px;padding:10px 12px;margin:14px 0;font-size:.92rem}
.kv{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin:14px 0}
.kv div{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 10px}
.kv span{display:block;color:var(--muted);font-size:.68rem;text-transform:uppercase;letter-spacing:.5px}
.kv b{font-family:var(--mono)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 16px}
.chip{font-size:.74rem;background:#06262f;border:1px solid var(--line);border-radius:6px;padding:3px 9px;color:#bfe7e3;font-family:var(--mono)}
table{width:100%;border-collapse:collapse;font-size:.85rem;margin-top:8px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--muted);font-size:.68rem;text-transform:uppercase;letter-spacing:.5px}
.badge{font-size:.7rem;padding:2px 8px;border-radius:6px;font-weight:700;font-family:var(--mono);color:#04202b;white-space:nowrap}
.num{font-family:var(--mono);color:#bdeee8;white-space:nowrap}
.cta{display:inline-block;background:var(--coral);color:#2a0f06;border-radius:8px;padding:10px 16px;font-weight:700;text-decoration:none;margin:16px 0}
.meta{color:var(--muted);font-size:.8rem}
footer{color:var(--muted);font-size:.74rem;text-align:center;padding:24px 16px;line-height:1.7;border-top:1px solid var(--line);margin-top:30px}
.dirlist{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:8px}
.dirlist li{background:var(--panel);border:1px solid var(--line);border-radius:10px}
.dirlist a{display:block;padding:10px 12px;text-decoration:none;color:var(--ink)}
.dirlist small{display:block;color:var(--muted)}
"""

FLUKE = ('<svg width="34" height="22" viewBox="0 0 120 70" aria-hidden="true"><path d="M60 62 C56 51 53 46 46 41 '
         'C35 32 18 24 6 22 C16 28 33 37 48 41 C53 42 56 43 60 47 C64 43 67 42 72 41 C87 37 104 28 114 22 '
         'C102 24 85 32 74 41 C67 46 64 51 60 62 Z" fill="#2fe0d6"/></svg>')

def esc(s): return html.escape(str(s or ""), quote=True)

def topbar():
    return ('<div class="topbar"><a href="../index.html">'+FLUKE+
            '<span><span class="name">Scuba<b>naut</b></span><br><span class="tag">Know before you go</span></span></a></div>')

def footer_html():
    return ('<footer><b style="font-family:var(--serif);color:var(--ink)">DiveSZN</b> · seasonal dive planning, verified against '
            'dive operators, park authorities and liveaboard calendars.<br>Water temperatures are typical monthly ranges (±1°C); '
            'marine-life timing shifts year to year — always confirm with a local dive centre.<br>'
            '<a href="index.html">All destinations</a> · <a href="../index.html">Open the dive planner</a></footer>')

# Pluralised wording for site-type breakdowns (mirrors destIntro in index.html)
SITE_PLURALS = {"Muck": "muck dives", "Shore": "shore dives", "Drift": "drift dives",
                "Shark dive": "shark dives", "Manta dive": "manta dives",
                "Blue hole": "blue holes", "Pass": "pass drifts", "Thila": "thilas"}

def _site_plural(t, n):
    if n == 1:
        return t.lower() + (" dive" if t in ("Drift", "Shore", "Muck") else "")
    return SITE_PLURALS.get(t, t.lower() + "s")

def _join_list(items):
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]

def dest_intro(d):
    """Data-generated overview paragraph (same wording logic as destIntro in index.html)."""
    temps = [t for t in d["monthly_temp_c"].values() if t is not None]
    tmin, tmax = min(temps), max(temps)
    vmax = max(d["monthly"][m].get("visibility_m") or 0 for m in MONTHS)
    peak = [m for m in MONTHS if d["monthly"][m]["rating"] == "Peak"]
    cur = (d.get("current_note") or d.get("currents") or "").rstrip(".")
    water = d["water_type"] if d["water_type"].endswith("water") else d["water_type"] + " water"
    suit = d["wetsuit"].split(";")[0].rstrip(".")
    p1 = (f'{d["name"]} is at its best {d["best_months"]}'
          + (f', with {_join_list(peak)} rating as peak season' if peak else "") + ". "
          + f'Expect {water} of {tmin if tmin == tmax else f"{tmin}–{tmax}"}°C '
          + f'(suit: {suit}), visibility up to ~{vmax}m, '
          + f'and {d["current_strength"].lower()} currents — {cur}.')
    sites = d.get("dive_sites") or []
    if not sites:
        return p1
    counts = {}
    for x in sites:
        t = x.get("type") or "Reef"
        counts[t] = counts.get(t, 0) + 1
    breakdown = _join_list(f"{n} {_site_plural(t, n)}"
                           for t, n in sorted(counts.items(), key=lambda kv: -kv[1]))
    order = {"beginner": 0, "intermediate": 1, "advanced": 2, "tec": 3}
    by_level = sorted(sites, key=lambda x: order.get(x.get("level"), 1))
    easy, hard = by_level[0], by_level[-1]
    hard_lvl = "technical-diving" if hard.get("level") == "tec" else hard.get("level", "advanced")
    p2 = (f' Divers here work {len(sites)} recognised sites — {breakdown} — ranging from '
          f'{easy["name"]}{" (" + easy["depth"] + ")" if easy.get("depth") else ""} for {easy.get("level", "beginner")} divers '
          f'up to {hard["name"]}{" (" + hard["depth"] + ")" if hard.get("depth") else ""}, {hard_lvl} territory.')
    return p1 + p2

def page(d):
    slug = d["slug"]; url = BASE + "destinations/" + slug + ".html"
    peak = [m for m in MONTHS if d["monthly"][m]["rating"] == "Peak"]
    closed = [m for m in MONTHS if d["monthly"][m]["rating"] == "Closed"]
    desc = (f'{d["name"]} diving season guide: best months {d["best_months"]}. Month-by-month water temperature, '
            f'visibility, currents ({d["current_strength"].lower()}) and marine life. {d["highlights"]}')[:300]
    img = d.get("image") or ""
    hero_bg = (f'background-image:linear-gradient(180deg,rgba(4,26,34,.66),rgba(3,23,31,.9)),url(\'{esc(img)}\');' if img else "")
    rows = ""
    for m in MONTHS:
        mm = d["monthly"][m]
        t = d["monthly_temp_c"].get(m)
        rows += (f'<tr><td><b>{m}</b></td>'
                 f'<td><span class="badge" style="background:{RCOLOR[mm["rating"]]}'
                 f'{";color:#fff" if mm["rating"] in ("Peak","Low","Closed") else ""}">{mm["rating"]}</span></td>'
                 f'<td class="num">{t if t is not None else "—"}°C</td>'
                 f'<td class="num">{mm.get("visibility_m") or "—"}m</td>'
                 f'<td>{esc(mm["marine_life"])}</td><td>{esc(mm["conditions"])}</td></tr>')
    species = "".join(f'<span class="chip">{esc(s)}</span>' for s in d.get("signature_species", []))
    ld = {
        "@context": "https://schema.org", "@type": "TouristDestination",
        "name": d["name"] + " scuba diving", "description": desc, "url": url,
        "touristType": "Scuba divers",
    }
    if d.get("coordinates", {}).get("lat") is not None:
        ld["geo"] = {"@type": "GeoCoordinates", "latitude": d["coordinates"]["lat"], "longitude": d["coordinates"]["lng"]}
    if img: ld["image"] = img
    sites = d.get("dive_sites") or []
    if sites:
        ld["containsPlace"] = [{"@type": "TouristAttraction", "name": s.get("name")} for s in sites]
    site_rows = "".join(
        f'<tr><td><b>{esc(s.get("name"))}</b></td><td><span class="chip">{esc(s.get("type") or "Reef")}</span></td>'
        f'<td class="num">{esc(s.get("depth") or "—")}</td>'
        f'<td class="num">{esc(s.get("level") or "intermediate")}</td>'
        f'<td>{esc(s.get("blurb"))}</td></tr>'
        for s in sites)
    sites_block = ""
    if site_rows:
        sites_block = (f'<h2>Recognised dive sites ({len(sites)})</h2>'
                       f'<p class="meta">Depths are typical published ranges — always confirm with your operator.</p>'
                       f'<div style="overflow:auto"><table>'
                       f'<thead><tr><th>Site</th><th>Type</th><th>Depth</th><th>Level</th><th>Why it&#8217;s known</th></tr></thead>'
                       f'<tbody>{site_rows}</tbody></table></div>')
    og_img = f'<meta property="og:image" content="{esc(img)}">' if img else ""
    verified = (f'<p class="meta">&#10003; Data verified {esc(d.get("last_verified"))}'
                f' · source confidence: {esc(d.get("data_confidence"))}</p>' if d.get("last_verified") else "")
    cur_note = f'<div class="meta" style="font-size:.7rem;margin-top:2px">{esc(d.get("current_note"))}</div>' if d.get("current_note") else ""
    closed_line = f' &nbsp;·&nbsp; <b>Closed:</b> {", ".join(closed)}' if closed else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(d["name"])} Diving Season & Calendar — Best Time to Dive | DiveSZN</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="article"><meta property="og:title" content="{esc(d["name"])} — Best Time to Dive">
<meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{esc(url)}">{og_img}
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style>
</head>
<body>
{topbar()}
<header class="hero" style="{hero_bg}">
  <h1>{esc(d["name"])}</h1>
  <p>{esc(d["country"])} · {esc(d["region"])} — {esc(d["highlights"])}</p>
  {f'<span class="credit">{esc(d.get("image_credit"))}</span>' if d.get("image_credit") else ""}
</header>
<main class="wrap">
  <p style="max-width:78ch;line-height:1.65;color:#d6f3f0">{esc(dest_intro(d))}</p>
  <div class="best">&#127942; <b>Best months:</b> {esc(", ".join(peak) or "—")} &nbsp;·&nbsp; <b>Recommended window:</b> {esc(d["best_months"])}{closed_line}</div>
  <div class="kv">
    <div><span>Water type</span>{esc(d["water_type"])}</div>
    <div><span>Difficulty</span>{esc(d["difficulty"])}</div>
    <div><span>Access</span>{esc(d["access"])}</div>
    <div><span>Wetsuit</span><b>{esc(d["wetsuit"])}</b></div>
    <div><span>Current strength</span><b>{esc(d["current_strength"])}</b>{cur_note}</div>
    <div style="grid-column:1/-1"><span>Currents detail</span>{esc(d["currents"])}</div>
  </div>
  <span class="meta">Signature sea life</span>
  <div class="chips">{species}</div>
  <h2>Month-by-month diving calendar</h2>
  <div style="overflow:auto"><table>
    <thead><tr><th>Month</th><th>Rating</th><th>Water</th><th>Viz</th><th>Sea life expected</th><th>Conditions</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  {sites_block}
  {verified}
  <a class="cta" href="../index.html">Plan a dive trip here — open the DiveSZN planner &rarr;</a>
</main>
{footer_html()}
</body></html>"""

def index_page(dests):
    items = ""
    for d in sorted(dests, key=lambda x: x["name"].lower()):
        peak = ", ".join(m for m in MONTHS if d["monthly"][m]["rating"] == "Peak") or "—"
        items += (f'<li><a href="{d["slug"]}.html"><b>{esc(d["name"])}</b>'
                  f'<small>{esc(d["country"])} · peak: {esc(peak)}</small></a></li>')
    desc = "Season guides for 50 world scuba diving destinations: best months, water temperature, visibility, currents and marine life."
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>All Dive Destinations — Season Guides | DiveSZN</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{BASE}destinations/index.html">
<style>{CSS}</style>
</head>
<body>
{topbar()}
<main class="wrap">
  <h1>Dive destination season guides</h1>
  <p class="meta">{desc}</p>
  <ul class="dirlist">{items}</ul>
  <a class="cta" href="../index.html">Open the interactive dive planner &rarr;</a>
</main>
{footer_html()}
</body></html>"""

def main():
    with open(os.path.join(ROOT, "diving-destinations.json")) as f:
        dests = json.load(f)["destinations"]
    outdir = os.path.join(ROOT, "destinations")
    os.makedirs(outdir, exist_ok=True)
    for d in dests:
        with open(os.path.join(outdir, d["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(page(d))
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page(dests))
    urls = [BASE, BASE + "destinations/index.html"] + [BASE + "destinations/" + d["slug"] + ".html" for d in dests]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sm += f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n"
    sm += "</urlset>\n"
    with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
        f.write(sm)
    with open(os.path.join(ROOT, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n")
    print(f"Wrote {len(dests)} destination pages + index, sitemap.xml ({len(urls)} URLs), robots.txt")

if __name__ == "__main__":
    main()
