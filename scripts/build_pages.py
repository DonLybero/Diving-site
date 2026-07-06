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
import json, os, html, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://donlybero.github.io/Diving-site/"
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
RCOLOR = {"Peak":"#16a34a","Good":"#0ea5e9","Shoulder":"#eab308","Low":"#f97316","Closed":"#64748b"}
TODAY = "2026-07-01"

CSS = """
:root{--bg:#f4f9f9;--panel:#ffffff;--ink:#0e2f37;--muted:#61838a;--accent:#0e9c92;--coral:#ff7a59;--line:#d7e5e7;
--serif:Georgia,'Iowan Old Style','Times New Roman',serif;--mono:ui-monospace,'SF Mono',Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;
background:linear-gradient(180deg,#ffffff,#e9f2f3);color:var(--ink);min-height:100vh}
a{color:var(--accent)}h1,h2{font-family:var(--serif);font-weight:600}
.topbar{display:flex;align-items:center;gap:11px;padding:10px 18px;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line)}
.topbar a{display:inline-flex;align-items:center;gap:11px;text-decoration:none;color:var(--ink)}
.topbar .name{font-family:var(--serif);font-size:1.3rem}.topbar .name b{color:var(--accent);font-weight:600}
.topbar .tag{color:var(--muted);font-size:.62rem;font-family:var(--mono);letter-spacing:.24em;text-transform:uppercase}
.hero{position:relative;padding:64px 18px 40px;text-align:center;background-size:cover;background-position:center 40%;border-bottom:1px solid var(--line)}
.hero h1{font-size:clamp(1.9rem,5vw,3rem);margin:0;color:#fff}.hero p{color:#e8f7f5;max-width:60ch;margin:10px auto 0}
.hero .credit{position:absolute;right:10px;bottom:6px;font-size:.6rem;color:rgba(233,247,246,.55);font-family:var(--mono)}
.wrap{max-width:900px;margin:0 auto;padding:20px 16px 60px}
.best{background:linear-gradient(90deg,#e3f5ec,#f2f9f9);border:1px solid #b7dfcb;border-radius:10px;padding:10px 12px;margin:14px 0;font-size:.92rem}
.kv{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin:14px 0}
.kv div{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px 10px}
.kv span{display:block;color:var(--muted);font-size:.68rem;text-transform:uppercase;letter-spacing:.5px}
.kv b{font-family:var(--mono)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 16px}
.chip{font-size:.74rem;background:#eef5f6;border:1px solid var(--line);border-radius:6px;padding:3px 9px;color:#175e66;font-family:var(--mono)}
table{width:100%;border-collapse:collapse;font-size:.85rem;margin-top:8px}
th,td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--muted);font-size:.68rem;text-transform:uppercase;letter-spacing:.5px}
.badge{font-size:.7rem;padding:2px 8px;border-radius:6px;font-weight:700;font-family:var(--mono);color:#04202b;white-space:nowrap}
.num{font-family:var(--mono);color:#0b6b74;white-space:nowrap}
.cta{display:inline-block;background:var(--coral);color:#2a0f06;border-radius:8px;padding:10px 16px;font-weight:700;text-decoration:none;margin:16px 0}
.meta{color:var(--muted);font-size:.8rem}
footer{color:var(--muted);font-size:.74rem;text-align:center;padding:24px 16px;line-height:1.7;border-top:1px solid var(--line);margin-top:30px}
.dirlist{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:8px}
.dirlist li{background:var(--panel);border:1px solid var(--line);border-radius:10px}
.dirlist a{display:block;padding:10px 12px;text-decoration:none;color:var(--ink)}
.dirlist small{display:block;color:var(--muted)}
.packbox{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--coral);border-radius:12px;padding:14px 16px;margin:18px 0}
.pack-head{font-family:var(--mono);font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;color:var(--coral);margin-bottom:6px}
.pack-body{margin:0 0 11px;color:#33565e;font-size:.92rem;line-height:1.6}
.pack-ctas{display:flex;flex-wrap:wrap;gap:8px}
.pack-cta{display:inline-block;background:var(--coral);color:#2a0f06;border-radius:9px;padding:9px 15px;font-size:.83rem;font-weight:700;text-decoration:none}
.pack-cta.ghost{background:#fff;color:#b3492f;border:1px solid #e6bcb0}
.hero.plain{background:linear-gradient(135deg,#0e2f37,#0b7d75);padding:48px 18px 34px}
.hero.plain h1{color:#fff}.hero.plain p{color:#d7f0ec}
.artlist{list-style:none;padding:0;margin:14px 0}
.artlist li{border-bottom:1px solid var(--line)}
.artlist a{display:grid;grid-template-columns:120px 1fr;gap:16px;align-items:center;padding:16px 0;text-decoration:none;color:var(--ink)}
.artlist .th{height:88px;border-radius:8px;background:#f4f8f8;display:flex;align-items:center;justify-content:center;overflow:hidden}
.artlist .th img{max-width:92%;max-height:92%;object-fit:contain}
.artlist h3{margin:2px 0 4px;font-size:1.2rem}.artlist p{margin:0;color:var(--muted);font-size:.86rem}
.gentry{display:grid;grid-template-columns:230px 1fr;gap:20px;padding:22px 0;border-bottom:1px solid var(--line);align-items:start}
.gphoto{height:170px;border-radius:10px;background:#f4f8f8;display:flex;align-items:center;justify-content:center;overflow:hidden}
.gphoto img{max-width:92%;max-height:92%;object-fit:contain}
.gentry h3{margin:0 0 8px;font-size:1.3rem}
.greview{color:#33565e;line-height:1.7;margin:0 0 10px}
.gspecs{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px;margin:0 0 12px}
.gspecs div{background:#f0f6f7;border:1px solid var(--line);border-radius:8px;padding:6px 10px}
.gspecs dt{color:var(--muted);font-size:.6rem;text-transform:uppercase;letter-spacing:.5px;margin:0}
.gspecs dd{margin:2px 0 0;font-family:var(--mono);font-size:.76rem;color:#0b6b74}
.buybox{background:#f6fbfb;border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-top:6px}
.buy-top{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;margin-bottom:9px}
.buy-lead{font-family:var(--mono);font-size:.62rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.buy-from{font-family:var(--serif)}.buy-from b{color:var(--coral);font-family:var(--mono)}
.buy-live{font-size:.68rem;color:var(--muted)}
.tipbox{background:#f2f9f9;border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:14px 0}
.tipbox ul{margin:6px 0 0;padding-left:18px}.tipbox li{margin:4px 0;color:#33565e;font-size:.9rem}
@media(max-width:640px){.gentry{grid-template-columns:1fr}.artlist a{grid-template-columns:90px 1fr}.gspecs{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""

FLUKE = ('<svg width="34" height="22" viewBox="0 0 120 70" aria-hidden="true"><path d="M60 62 C56 51 53 46 46 41 '
         'C35 32 18 24 6 22 C16 28 33 37 48 41 C53 42 56 43 60 47 C64 43 67 42 72 41 C87 37 104 28 114 22 '
         'C102 24 85 32 74 41 C67 46 64 51 60 62 Z" fill="#2fe0d6"/></svg>')

def esc(s): return html.escape(str(s or ""), quote=True)

def topbar(prefix="../"):
    return (f'<div class="topbar"><a href="{prefix}index.html">'+FLUKE+
            '<span class="name">Dive<b>SZN</b></span></a></div>')

def footer_html(prefix="../"):
    return ('<footer><b style="font-family:var(--serif);color:var(--ink)">DiveSZN</b> · seasonal dive planning, verified against '
            'dive operators, park authorities and liveaboard calendars.<br>Water temperatures are typical monthly ranges (±1°C); '
            'marine-life timing shifts year to year — always confirm with a local dive centre.<br>'
            f'<a href="{prefix}index.html">Dive planner</a> · <a href="{prefix}destinations/index.html">Destinations</a> · '
            f'<a href="{prefix}gear/index.html">Gear guides</a> · <a href="{prefix}how-we-score.html">How we score</a> · '
            f'<a href="{prefix}about.html">About</a> · <a href="{prefix}privacy.html">Privacy</a></footer>')

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

def pack_box(d):
    """Contextual gear cross-sell — maps water/wetsuit to the wetsuit thickness
    guide (mirrors packBox in index.html). Links deep-link into the SPA gear tab."""
    w = (d.get("wetsuit") or "").lower()
    dry = "drysuit" in w
    th = [int(x) for x in re.findall(r"([2357])\s*mm", w)]
    rng = re.search(r"([2357])\s*-\s*([2357])\s*mm", w)
    if rng:
        th += [int(rng.group(1)), int(rng.group(2))]
    th = sorted(set(th))
    primary = th[0] if th else None
    secondary = th[-1] if len(th) > 1 else None
    temps = [t for t in (d.get("monthly_temp_c") or {}).values() if isinstance(t, (int, float))]
    tpart = (f"sits around <b>{sorted(temps)[len(temps)//2]}°C</b>" if temps else "varies by season")

    def cta(mm, label, ghost=False):
        return (f'<a class="pack-cta{" ghost" if ghost else ""}" '
                f'href="../index.html#gear-wetsuits-{mm}mm">{label}</a>')

    if dry:
        body = ("The water here is cold enough that most divers use a <b>drysuit</b>. "
                "If you dive wet, a <b>7&nbsp;mm</b> and a hood are the warmest option.")
        ctas = cta(7, "See the warmest 7&nbsp;mm wetsuits &rarr;")
    elif primary:
        extra = (f" A <b>{secondary}&nbsp;mm</b> is worth packing for winter or deeper, repeat dives."
                 if secondary and secondary != primary else "")
        body = f"Water {tpart} here, so a <b>{primary}&nbsp;mm wetsuit</b> is the right call.{extra}"
        ctas = cta(primary, f"See the best {primary}&nbsp;mm wetsuits &rarr;")
        if secondary and secondary != primary:
            ctas += cta(secondary, f"See the best {secondary}&nbsp;mm &rarr;", ghost=True)
    else:
        return ""
    return (f'<div class="packbox"><div class="pack-head">What to pack here</div>'
            f'<p class="pack-body">{body}</p><div class="pack-ctas">{ctas}</div></div>')


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
  <p style="max-width:78ch;line-height:1.65;color:#33565e">{esc(dest_intro(d))}</p>
  <div class="best">&#127942; <b>Best months:</b> {esc(", ".join(peak) or "—")} &nbsp;·&nbsp; <b>Recommended window:</b> {esc(d["best_months"])}{closed_line}</div>
  <div class="kv">
    <div><span>Water type</span>{esc(d["water_type"])}</div>
    <div><span>Difficulty</span>{esc(d["difficulty"])}</div>
    <div><span>Access</span>{esc(d["access"])}</div>
    <div><span>Wetsuit</span><b>{esc(d["wetsuit"])}</b></div>
    <div><span>Current strength</span><b>{esc(d["current_strength"])}</b>{cur_note}</div>
    <div style="grid-column:1/-1"><span>Currents detail</span>{esc(d["currents"])}</div>
  </div>
  {pack_box(d)}
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

# ---------------------------------------------------------------- gear pages
def gear_slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def fmtp(p):
    return f"${p:.2f}" if p % 1 else f"${int(p)}"

def _partner_tier(store):
    return 0 if re.search(r"amazon|ebay|scuba\.com|leisurepro|tradeinn|diveinn|scubastore", (store or "").lower()) else 1

def order_offers(options):
    s = sorted(options or [], key=lambda o: o["price_usd"])
    if not s:
        return s
    lo = s[0]["price_usd"]; band = lo * 0.05 or 1
    return sorted(s, key=lambda o: (int((o["price_usd"] - lo) // band), _partner_tier(o["store"]), o["price_usd"]))

def buy_box(item):
    offers = order_offers(item.get("options"))[:3]
    lo = min((o["price_usd"] for o in item.get("options") or []), default=None)
    btns = "".join(
        f'<a class="pack-cta{"" if i == 0 else " ghost"}" href="{esc(o["url"])}" '
        f'target="_blank" rel="noopener sponsored">Buy at {esc(o["store"])}</a>'
        for i, o in enumerate(offers))
    frm = f'<span class="buy-from">from <b>{fmtp(lo)}</b></span>' if lo is not None else ""
    return (f'<div class="buybox"><div class="buy-top"><span class="buy-lead">Where to buy</span>{frm}'
            f'<span class="buy-live">indicative — check the live price at the retailer</span></div>'
            f'<div class="pack-ctas">{btns}</div></div>')

def gear_entry(item, prefix):
    img = item.get("image") or ""
    imgtag = f'<img src="{prefix}{esc(img)}" alt="{esc(item["name"])}" loading="lazy">' if img else ""
    specs = ""
    if item.get("specs"):
        specs = ('<dl class="gspecs">'
                 + "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in item["specs"].items())
                 + "</dl>")
    return (f'<div class="gentry"><div class="gphoto">{imgtag}</div>'
            f'<div><h3>{item.get("rank", "")}. {esc(item["name"])}</h3>'
            f'<p class="greview">{esc(item.get("review") or item.get("blurb"))}</p>{specs}{buy_box(item)}</div></div>')

def content_shell(title, desc, url, prefix, hero_sub, inner, ld=None):
    ldtag = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    h1 = esc(title.split(" | ")[0].split(" — ")[0])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{esc(url)}">
{ldtag}
<style>{CSS}</style>
</head>
<body>
{topbar(prefix)}
<header class="hero plain"><h1>{h1}</h1>{f'<p>{esc(hero_sub)}</p>' if hero_sub else ''}</header>
<main class="wrap">{inner}</main>
{footer_html(prefix)}
</body></html>"""

def gear_page(cat, prefix="../"):
    slug = gear_slug(cat["category"])
    title = f'{cat.get("title") or ("Top " + cat["category"])} | DiveSZN'
    url = BASE + "gear/" + slug + ".html"
    intro = cat.get("article_intro") or ""
    parts = [f'<p class="greview" style="max-width:80ch">{esc(intro)}</p>'] if intro else []
    if cat.get("thickness_groups"):
        for g in cat["thickness_groups"]:
            head = esc(g.get("label") or g["thickness"]) + (f' · {esc(g["water"])}' if g.get("water") else "")
            parts.append(f'<h2 id="{esc(g["thickness"])}">{head}</h2>')
            if g.get("article_intro"):
                parts.append(f'<p class="greview" style="max-width:80ch">{esc(g["article_intro"])}</p>')
            tips = "".join(f"<li>{esc(t)}</li>" for t in (g.get("tips") or []))
            if tips:
                parts.append(f'<div class="tipbox"><b>What to look for</b><ul>{tips}</ul></div>')
            parts += [gear_entry(it, prefix) for it in g["items"]]
    else:
        tips = "".join(f"<li>{esc(t)}</li>" for t in (cat.get("tips") or []))
        if tips:
            parts.append(f'<div class="tipbox"><b>What to look for</b><ul>{tips}</ul></div>')
        parts += [gear_entry(it, prefix) for it in cat["items"]]
    parts.append(f'<p class="meta"><a href="index.html">&larr; All gear buyer&#8217;s guides</a></p>')
    desc = (intro or f'The best {cat["category"].lower()} for scuba diving in 2026.')[:300]
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": cat.get("title"),
          "description": desc, "url": url}
    return content_shell(title, desc, url, prefix, None, "".join(parts), ld)

def gear_index_page(gear, prefix="../"):
    url = BASE + "gear/index.html"
    rows = ""
    for cat in gear["categories"]:
        slug = gear_slug(cat["category"])
        lead = (cat.get("items") or (cat.get("thickness_groups") or [{}])[0].get("items") or [{}])[0]
        img = lead.get("image") or ""
        thumb = f'<img src="{prefix}{esc(img)}" alt="" loading="lazy">' if img else ""
        teaser = ". ".join((cat.get("article_intro") or "").split(". ")[:2]).strip()
        rows += (f'<li><a href="{slug}.html"><div class="th">{thumb}</div>'
                 f'<div><h3>{esc(cat.get("title") or ("Top " + cat["category"]))}</h3>'
                 f'<p>{esc(teaser)}</p></div></a></li>')
    desc = "DiveSZN scuba gear buyer's guides — the best masks, fins, regulators, BCDs, dive computers and wetsuits, with specs and where to buy."
    inner = (f'<p class="greview" style="max-width:80ch">{esc(gear.get("intro") or "")}</p>'
             f'<h2>Buyer&#8217;s guides</h2><ul class="artlist">{rows}</ul>'
             f'<a class="cta" href="../index.html#gear">Open the interactive gear guide &rarr;</a>')
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "DiveSZN gear buyer's guides",
          "description": desc, "url": url}
    return content_shell("Scuba Diving Gear Buyer’s Guides 2026 | DiveSZN", desc, url, prefix,
                         "Independent picks, real specs, and where to buy — masks to wetsuits.", inner, ld)

# ---------------------------------------------------------------- about / methodology
def about_page():
    url = BASE + "about.html"
    inner = """
<p class="greview" style="max-width:78ch">DiveSZN is a seasonal dive-trip planner. It scores world dive
destinations month by month so you can match your travel dates to the places where the season, the water and
the wildlife line up — and it pairs that with independent scuba-gear buyer&#8217;s guides so you arrive with
the right kit.</p>
<h2>How the data is made</h2>
<p class="greview" style="max-width:78ch">The seasonal calendar covers 50 destinations across twelve months —
water temperature, visibility, currents, marine-life timing and a season rating for each. It is compiled and
cross-checked against dive-operator and liveaboard calendars, marine-park authorities and ocean
sea-temperature sources, then hand-verified. Water temperatures are typical monthly ranges (±1&deg;C) and
marine-life timing shifts year to year with plankton and lunar cycles, so we always say the same thing: confirm
current conditions with a local dive centre before you travel.</p>
<h2>Our gear guides</h2>
<p class="greview" style="max-width:78ch">Gear picks are researched independently and chosen on the merits.
Prices shown are indicative as of our research date — the retailer always shows the live price. DiveSZN is
reader-supported: some &#8220;Buy&#8221; links are affiliate links and we may earn a commission at no extra cost
to you. Commissions never influence our rankings.</p>
<h2>Scuba only</h2>
<p class="greview" style="max-width:78ch">DiveSZN is written for scuba divers. Every recommendation, from a
destination&#8217;s best months to a wetsuit&#8217;s thickness, is framed around scuba diving.</p>
<h2>Get in touch</h2>
<p class="greview" style="max-width:78ch">Questions, corrections or partnership enquiries:
<a href="mailto:hello@diveszn.com">hello@diveszn.com</a>. See also our
<a href="privacy.html">Privacy Policy</a> and <a href="how-we-score.html">How we score</a> page.</p>
<a class="cta" href="index.html">Open the dive planner &rarr;</a>
"""
    desc = "About DiveSZN — a seasonal scuba dive-trip planner and independent gear buyer's guide. How our destination data is compiled and how we stay independent."
    ld = {"@context": "https://schema.org", "@type": "AboutPage", "name": "About DiveSZN", "description": desc, "url": url}
    return content_shell("About DiveSZN — Seasonal Dive Planner & Gear Guide", desc, url, "", None, inner, ld)

def score_page():
    url = BASE + "how-we-score.html"
    inner = """
<p class="greview" style="max-width:78ch">Every destination gets a rating for every month of the year, and a
numeric score that ranks the best places to dive in any period. Here is exactly how that works — no black box.</p>
<h2>Season ratings</h2>
<p class="greview" style="max-width:78ch">Each month is rated <b>Peak</b>, <b>Good</b>, <b>Shoulder</b>,
<b>Low</b> or <b>Closed</b>, based on the destination&#8217;s water conditions, marine-life activity and
diveability that month.</p>
<h2>The score</h2>
<p class="greview" style="max-width:78ch">The ranking score is built from three parts:</p>
<div class="tipbox"><ul>
<li><b>Conditions base</b> — from the month&#8217;s season rating: Peak 100, Good 72, Shoulder 48, Low 22. Closed
months are excluded.</li>
<li><b>Marine-life bonus</b> — up to 25 points for the signature species and events expected that month
(sharks, mantas, whale sharks, spawning aggregations and so on).</li>
<li><b>Visibility bonus</b> — 0 to 18 points, scaled from typical visibility that month (about 5&nbsp;m adds
nothing; 35&nbsp;m or more adds the full 18).</li>
</ul></div>
<p class="greview" style="max-width:78ch">Add them up and you get a single comparable score, so &#8220;where is
diving best in October?&#8221; has an honest, repeatable answer. The identical formula runs in the interactive
planner and in our data pipeline, so on-page rankings and the calendar never disagree.</p>
<h2>Where the numbers come from</h2>
<p class="greview" style="max-width:78ch">Water temperature, visibility, currents and marine-life timing are
compiled and cross-checked against dive-operator and liveaboard calendars, marine-park authorities and ocean
sea-temperature sources, then hand-verified. They are typical ranges, not forecasts — always confirm current
conditions with a local dive centre.</p>
<a class="cta" href="index.html">See it in the dive planner &rarr;</a>
"""
    desc = "How DiveSZN scores dive destinations: season ratings (Peak/Good/Shoulder/Low/Closed) plus a transparent score from conditions, marine-life bonus and visibility."
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": "How DiveSZN scores dive destinations",
          "description": desc, "url": url}
    return content_shell("How We Score Dive Destinations | DiveSZN", desc, url, "", None, inner, ld)

def main():
    with open(os.path.join(ROOT, "diving-destinations.json")) as f:
        dests = json.load(f)["destinations"]
    with open(os.path.join(ROOT, "gear-guide.json")) as f:
        gear = json.load(f)
    outdir = os.path.join(ROOT, "destinations")
    os.makedirs(outdir, exist_ok=True)
    for d in dests:
        with open(os.path.join(outdir, d["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(page(d))
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page(dests))

    # gear buyer's guides (crawlable static pages)
    geardir = os.path.join(ROOT, "gear")
    os.makedirs(geardir, exist_ok=True)
    gear_slugs = []
    for cat in gear["categories"]:
        slug = gear_slug(cat["category"]); gear_slugs.append(slug)
        with open(os.path.join(geardir, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(gear_page(cat))
    with open(os.path.join(geardir, "index.html"), "w", encoding="utf-8") as f:
        f.write(gear_index_page(gear))

    # trust / info pages (root)
    with open(os.path.join(ROOT, "about.html"), "w", encoding="utf-8") as f:
        f.write(about_page())
    with open(os.path.join(ROOT, "how-we-score.html"), "w", encoding="utf-8") as f:
        f.write(score_page())

    urls = ([BASE, BASE + "about.html", BASE + "how-we-score.html",
             BASE + "destinations/index.html", BASE + "gear/index.html"]
            + [BASE + "gear/" + s + ".html" for s in gear_slugs]
            + [BASE + "destinations/" + d["slug"] + ".html" for d in dests])
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sm += f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n"
    sm += "</urlset>\n"
    with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
        f.write(sm)
    with open(os.path.join(ROOT, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n")
    print(f"Wrote {len(dests)} destination pages + index, {len(gear_slugs)} gear pages + index, "
          f"about + how-we-score, sitemap.xml ({len(urls)} URLs), robots.txt")

if __name__ == "__main__":
    main()
