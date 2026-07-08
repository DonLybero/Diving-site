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
import json, os, html, re, urllib.parse, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://donlybero.github.io/Diving-site/"
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
RCOLOR = {"Peak":"#16a34a","Good":"#0ea5e9","Shoulder":"#eab308","Low":"#f97316","Closed":"#64748b"}
MONTH_FULL = {"Jan":"January","Feb":"February","Mar":"March","Apr":"April","May":"May","Jun":"June",
              "Jul":"July","Aug":"August","Sep":"September","Oct":"October","Nov":"November","Dec":"December"}

def _index_src():
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        return f.read()

def _junesc(t):
    """Decode JS \\uXXXX escapes and escaped quotes; literal UTF-8 passes through."""
    t = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), t)
    return t.replace("\\'", "'").replace('\\"', '"')

def load_region_groups():
    """Parse REGION_GROUPS out of index.html so the SPA stays the single source
    of truth for the continent grouping. Fails loudly if the shape changes."""
    m = re.search(r"var REGION_GROUPS=\{(.*?)\};", _index_src(), re.S)
    if not m:
        raise RuntimeError("REGION_GROUPS not found in index.html")
    groups = {}
    for gm in re.finditer(r"'([^']+)'\s*:\s*\[(.*?)\]", m.group(1), re.S):
        names = re.findall(r"'((?:[^'\\]|\\.)*)'", gm.group(2))
        groups[gm.group(1)] = [_junesc(n) for n in names]
    if not groups:
        raise RuntimeError("REGION_GROUPS parsed empty")
    return groups

def load_month_intros():
    """Parse the editorial MONTH_INTROS ledes out of index.html (best effort)."""
    m = re.search(r"var MONTH_INTROS=\{(.*?)\};", _index_src(), re.S)
    if not m:
        return {}
    intros = {}
    for im in re.finditer(r'(\w{3}):"((?:[^"\\]|\\.)*)"', m.group(1)):
        intros[im.group(1)] = _junesc(im.group(2))
    return intros

REGION_GROUPS = load_region_groups()
DEST_GROUP = {n: g for g, names in REGION_GROUPS.items() for n in names}
MONTH_INTROS = load_month_intros()

def crumbs(pairs):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u}
        for i, (n, u) in enumerate(pairs)]}

def graph_ld(*nodes):
    return {"@context": "https://schema.org",
            "@graph": [{k: v for k, v in n.items() if k != "@context"} for n in nodes if n]}
TODAY = datetime.date.today().isoformat()

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
footer{color:var(--muted);font-size:.74rem;text-align:center;padding:40px 16px 28px;line-height:1.7;border-top:1px solid var(--line);margin-top:56px}
.foot-mark{font-family:var(--serif);font-weight:600;font-size:clamp(2.6rem,9vw,5.2rem);line-height:1;letter-spacing:-.03em;color:var(--ink);margin:0 0 4px}
.foot-mark b{color:var(--accent)}
.foot-tag{font-family:var(--mono);font-size:.64rem;letter-spacing:.24em;text-transform:uppercase;color:var(--muted)}
.foot-nav{display:flex;flex-wrap:wrap;justify-content:center;gap:6px 22px;margin:22px 0 6px}
.foot-nav a{font-family:var(--mono);font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink);text-decoration:none}
.foot-nav a:hover{color:var(--accent)}
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
.staybox{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:12px;padding:14px 16px;margin:18px 0}
.prof-essays{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin:18px 0 4px}
.prof-essay{background:linear-gradient(165deg,#ffffff,#f2f9f9);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.prof-essay h2{margin:0 0 8px;font-size:1.12rem}
.prof-essay p{margin:0;color:#33565e;line-height:1.7;font-size:.95rem}
.honest{background:#fff;border:1px solid var(--line-strong,#bcd7d9);border-radius:14px;padding:20px 22px;margin:26px 0 8px}
.honest-kicker{font-family:var(--mono);font-size:.62rem;letter-spacing:.22em;text-transform:uppercase;color:#0b7d75;margin-bottom:4px}
.honest h3{font-family:var(--serif);font-size:1.35rem;margin:0 0 12px}
.honest ul{list-style:none;margin:0;padding:0}
.honest li{padding:9px 0;border-top:1px solid var(--line);color:#33565e;font-size:.92rem;line-height:1.65;max-width:80ch}
.honest li b{color:var(--ink)}
.gitem-kicker{font-family:var(--mono);letter-spacing:.08em;text-transform:uppercase;font-size:.68rem}
.gitem-kicker a{color:var(--accent);text-decoration:none}
.gitem-stage{margin:10px 0 26px}
.gitem-photo{margin:0;border-radius:16px 16px 0 0;overflow:hidden;border:1px solid var(--line);border-bottom:none;background:#f4f5f6}
.gitem-photo img{display:block;width:100%;max-height:640px;object-fit:cover}
.gitem-banner{display:flex;flex-wrap:wrap;align-items:center;gap:14px 30px;background:#fff;
  border:1px solid var(--line);border-radius:0 0 16px 16px;padding:16px 22px;
  box-shadow:0 18px 36px -24px rgba(13,60,70,.3)}
@media(max-width:760px){.gitem-photo img{object-fit:contain}}
.gitem-id b{font-family:var(--serif);font-size:1.15rem;display:block}
.gitem-price{font-family:var(--mono);font-size:.9rem;color:var(--ink)}
.gitem-price b{color:var(--coral);font-size:1.15rem;font-family:var(--mono);display:inline}
.gitem-id small{display:block;color:var(--muted);font-size:.64rem;margin-top:2px}
.gitem-colors{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.csw{width:34px;height:34px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;
  cursor:pointer;border:1px solid var(--line)}
.csw i{width:26px;height:26px;border-radius:50%;display:block;border:1px solid rgba(0,0,0,.15)}
.csw.on{border:2px solid var(--ink)}
.csw:hover{border-color:var(--ink)}
.grel{list-style:none;margin:8px 0 0;padding:0}
.grel li{padding:8px 0;border-top:1px solid var(--line)}
.grel a{color:var(--ink);text-decoration:none;font-weight:600}
.grel a:hover{color:var(--accent)}
.grel small{color:var(--muted);font-family:var(--mono)}
.gitem-link{color:inherit;text-decoration:none}
.gitem-link:hover{color:var(--accent)}
.dregion{margin:26px 0 8px}
.dregion h3{display:flex;align-items:baseline;justify-content:space-between;font-family:var(--serif);font-size:1.4rem;font-weight:600;margin:0;padding-bottom:9px;border-bottom:2px solid var(--line-strong,#bcd7d9)}
.bcount{font-family:var(--mono);font-size:.7rem;color:var(--muted);font-weight:400;letter-spacing:.08em}
.gbgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px 26px;margin-top:14px;align-items:start}
.gbcol{min-width:0}
.gbrand{display:block;font-family:var(--mono);font-size:.62rem;letter-spacing:.14em;text-transform:uppercase;color:#0b7d75;margin:4px 0 2px}
.gbrow{display:flex;align-items:center;gap:12px;padding:7px 0;color:var(--ink);text-decoration:none}
.gbrow b{display:block;font-weight:600;font-size:.92rem}
.gbrow small{display:block;color:var(--muted);font-family:var(--mono);font-size:.68rem;letter-spacing:.04em}
.gbrow:hover b{color:var(--accent)}
.gbthumb{flex:0 0 74px;width:74px;height:52px;border-radius:8px;overflow:hidden;background:#f4f5f6;border:1px solid var(--line)}
.gbthumb img{width:100%;height:100%;object-fit:cover;display:block}
@media(max-width:640px){.gitem-photo img{max-height:340px}}
.stay-head{font-family:var(--mono);font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;color:#0b7d75;margin-bottom:6px}
.hero.plain{background:linear-gradient(135deg,#0e2f37,#0b7d75);padding:48px 18px 34px}
.hero.plain h1{color:#fff}.hero.plain p{color:#d7f0ec}
.artlist{list-style:none;padding:0;margin:14px 0}
.artlist li{border-bottom:1px solid var(--line)}
.artlist a{display:grid;grid-template-columns:120px 1fr;gap:16px;align-items:center;padding:16px 0;text-decoration:none;color:var(--ink)}
.artlist .th{height:88px;border-radius:8px;background:#f4f8f8;display:flex;align-items:center;justify-content:center;overflow:hidden}
.artlist .th img{max-width:92%;max-height:92%;object-fit:contain}
.artlist .th.photo{background:#dbe9ec}
.artlist .th.photo img{max-width:none;max-height:none;width:100%;height:100%;object-fit:cover}
.marine-hero{margin:0 0 18px;border-radius:12px;overflow:hidden;background:#dbe9ec}
.marine-hero img{display:block;width:100%;height:320px;object-fit:cover}
.marine-hero figcaption{font-family:var(--mono);font-size:.6rem;color:var(--muted);padding:6px 10px;background:#f3f9f9}
@media(max-width:640px){.marine-hero img{height:210px}}
.artlist h3{margin:2px 0 4px;font-size:1.2rem}.artlist p{margin:0;color:var(--muted);font-size:.86rem}
.gentry{display:grid;grid-template-columns:230px 1fr;gap:20px;padding:22px 0;border-bottom:1px solid var(--line);align-items:start}
.gphoto{height:170px;border-radius:10px;background:#f4f8f8;display:flex;align-items:center;justify-content:center;overflow:hidden}
.gphoto img{max-width:92%;max-height:92%;object-fit:contain}
.gentry h3{margin:0 0 8px;font-size:1.3rem}
.greview{color:#33565e;line-height:1.7;margin:0 0 10px}
.lede{font-family:var(--serif);font-size:clamp(1.3rem,2.6vw,1.7rem);line-height:1.45;color:var(--ink);max-width:34ch;margin:14px 0;letter-spacing:-.01em}
.lede::after{content:"";display:block;width:64px;height:3px;border-radius:2px;margin-top:16px;background:linear-gradient(90deg,var(--accent),transparent)}
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
.region-head{font-family:var(--serif);font-size:1.5rem;margin:34px 0 2px;padding-top:22px;border-top:2px solid var(--line)}
.region-lede{color:var(--muted);font-size:.9rem;margin:2px 0 8px}
.dphoto img{width:100%;height:100%;max-width:none;max-height:none;object-fit:cover}
.badge.sm{font-size:.66rem}
"""

FLUKE = ('<svg width="34" height="22" viewBox="0 0 120 70" aria-hidden="true"><path d="M60 62 C56 51 53 46 46 41 '
         'C35 32 18 24 6 22 C16 28 33 37 48 41 C53 42 56 43 60 47 C64 43 67 42 72 41 C87 37 104 28 114 22 '
         'C102 24 85 32 74 41 C67 46 64 51 60 62 Z" fill="#2fe0d6"/></svg>')

def esc(s): return html.escape(str(s or ""), quote=True)

def topbar(prefix="../"):
    return (f'<div class="topbar"><a href="{prefix}index.html">'+FLUKE+
            '<span class="name">Dive<b>SZN</b></span></a></div>')

def footer_html(prefix="../"):
    return ('<footer>'
            '<div class="foot-mark">Dive<b>SZN</b></div>'
            '<div class="foot-tag">Know the season before you book</div>'
            '<div class="foot-nav">'
            f'<a href="{prefix}index.html">Destinations</a>'
            f'<a href="{prefix}destinations/index.html">Season guides</a>'
            f'<a href="{prefix}months/index.html">Best by month</a>'
            f'<a href="{prefix}marine-life/index.html">Marine life</a>'
            f'<a href="{prefix}gear/index.html">Gear guides</a>'
            f'<a href="{prefix}how-we-score.html">How we score</a>'
            f'<a href="{prefix}about.html">About</a>'
            f'<a href="{prefix}privacy.html">Privacy</a></div>'
            '<div>Seasonal dive planning, verified against dive operators, park authorities and liveaboard calendars. '
            'Water temperatures are typical monthly ranges (±1°C); marine-life timing shifts year to year — '
            'always confirm with a local dive centre.</div>'
            '</footer>')

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
                f'href="../gear/wetsuits.html#{mm}mm">{label}</a>')

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


LIVEABOARD_SLUG = {
 "Sharm El Sheikh": "egypt/red-sea", "Hurghada & El Gouna": "egypt/red-sea",
 "Marsa Alam": "egypt/red-sea", "Dahab": "egypt/red-sea", "Maldives": "maldives", "Raja Ampat": "indonesia",
 "Komodo National Park": "indonesia", "Cocos Island": "costa-rica", "Galapagos Islands": "galapagos",
 "Socorro Island": "mexico", "Sea of Cortez": "mexico", "Seychelles": "seychelles", "Palau": "palau",
 "Truk (Chuuk) Lagoon": "micronesia", "Fiji": "fiji", "French Polynesia": "french-polynesia",
 "Guadalcanal & Western Province": "solomon-islands", "Similan Islands": "thailand",
 "Tubbataha Reefs Natural Park": "philippines", "Bahamas": "bahamas", "Bay Islands": "honduras",
 "Cayman Islands": "cayman-islands", "Great Blue Hole": "belize", "Great Barrier Reef": "australia",
 "Whitsunday Islands": "australia",
}

def stay_box(d):
    """Where-to-stay cross-sell — Booking.com search deep-link (raw; the SPA wraps
    with the affiliate id) + LiveAboard.com page for liveaboard-oriented sites."""
    name = re.sub(r"\s*\(.*?\)\s*", " ", d["name"]).strip()
    country = re.sub(r"\s*\(.*?\)\s*", " ", d.get("country", "")).strip()
    q = (name + ((" " + country) if country and country != name else "")).strip()
    booking = f"https://www.booking.com/searchresults.html?ss={urllib.parse.quote(q)}&selected_currency=USD"
    access = (d.get("access") or "").lower()
    live = "liveaboard" in access
    board_only = bool(re.match(r"^\s*liveaboard(\s*/\s*day-boat)?\s*$", access))
    slug = LIVEABOARD_SLUG.get(d["name"])
    la = f"https://www.liveaboard.com/diving/{slug}" if slug else "https://www.liveaboard.com/"

    def a(href, label, ghost=False):
        return (f'<a class="pack-cta{" ghost" if ghost else ""}" href="{esc(href)}" '
                f'target="_blank" rel="noopener sponsored">{label}</a>')

    book = a(booking, f"Find stays near {esc(name)} &rarr;", ghost=board_only)
    board = a(la, "Browse liveaboards &rarr;", ghost=not board_only) if live else ""
    if board_only:
        body = ("Diving here is liveaboard-based — you sleep aboard the boat. Book a liveaboard, "
                "or a gateway hotel for the nights either side.")
        ctas = board + book
    elif live:
        body = "Base yourself at a dive resort or hotel near the water — or see it all from a liveaboard."
        ctas = book + board
    else:
        body = "Base yourself at a dive resort or hotel close to the water."
        ctas = book
    return (f'<div class="staybox"><div class="stay-head">Where to stay</div>'
            f'<p class="pack-body">{body}</p><div class="pack-ctas">{ctas}</div></div>')


def essays_block(d):
    """Editorial 'what to expect / what you'll encounter' cards (same as the SPA profile)."""
    cards = ""
    if d.get("underwater"):
        cards += f'<div class="prof-essay"><h2>What to expect down there</h2><p>{esc(d["underwater"])}</p></div>'
    if d.get("encounters"):
        cards += f'<div class="prof-essay"><h2>What you&#8217;ll encounter</h2><p>{esc(d["encounters"])}</p></div>'
    return f'<div class="prof-essays">{cards}</div>' if cards else ""


def honest_block(d):
    """Radical-transparency panel: what we can't promise (mirrors honestBlock in index.html)."""
    items = [
        "<b>Seasons drift.</b> Marine-life timing shifts year to year with plankton blooms and lunar "
        "cycles — a peak landing a couple of weeks early or late is normal, not bad luck.",
        "<b>Temperatures are ranges.</b> Water figures here are typical monthly ranges (&plusmn;1&deg;C); "
        "an upwelling or a heatwave can step outside them.",
        "<b>Visibility is seasonal, not daily.</b> Wind, swell, rain and plankton move it day to day — "
        "read our metres as the month's typical form, not a promise for your dive.",
        "<b>Currents can run above the rating.</b> Conditions on the day decide — brief with your "
        "operator before the first dive, and sit one out if it's beyond your training.",
    ]
    closed = [m for m in MONTHS if d["monthly"][m]["rating"] == "Closed"]
    if closed:
        items.append(f"<b>Closed means closed.</b> {_join_list(closed)} {'are' if len(closed) > 1 else 'is'} "
                     "out of season here — weather windows or park rules, not a scheduling choice.")
    items.append("<b>A score compares, it doesn't guarantee.</b> We rank months from dive-operator and "
                 "liveaboard calendars so you can weigh destinations like for like — always confirm "
                 "current conditions with a local dive centre.")
    lis = "</li><li>".join(items)
    return ('<div class="honest"><div class="honest-kicker">The honest picture</div>'
            f'<h3>What can change on the day?</h3><ul><li>{lis}</li></ul></div>')


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

def related_block(d):
    """Internal links: month hubs for its peak months, same-region siblings,
    and marine-life guides for what swims here (distributes authority)."""
    parts = []
    peak = [m for m in MONTHS if d["monthly"][m]["rating"] == "Peak"]
    if peak:
        links = " · ".join(f'<a href="../months/{MONTH_FULL[m].lower()}.html">{MONTH_FULL[m]}</a>' for m in peak[:6])
        parts.append(f'<p class="meta"><b>Best months here:</b> {links}</p>')
    text = " ".join((d["monthly"][m].get("marine_life") or "") for m in MONTHS).lower() + \
           " " + " ".join(d.get("signature_species") or []).lower()
    seen = []
    for exp in EXPERIENCES:
        if any(k.lower() in text for k in exp.get("keywords", [])):
            seen.append(f'<a href="../marine-life/{exp["slug"]}.html">{esc(exp["title"])}</a>')
        if len(seen) >= 4:
            break
    if seen:
        parts.append(f'<p class="meta"><b>Dive with:</b> {" · ".join(seen)}</p>')
    group = DEST_GROUP.get(d["name"])
    if group:
        sibs = [n for n in REGION_GROUPS[group] if n != d["name"]][:3]
        if sibs:
            links = " · ".join(f'<a href="{_slug_of(n)}.html">{esc(n)}</a>' for n in sibs if _slug_of(n))
            if links:
                parts.append(f'<p class="meta"><b>More in {esc(group)}:</b> {links}</p>')
    if not parts:
        return ""
    return '<h2>Related guides</h2>' + "".join(parts)

_SLUGS = {}
def _slug_of(name):
    return _SLUGS.get(name)

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
        "@type": "TouristDestination",
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
<script type="application/ld+json">{json.dumps(graph_ld(ld, crumbs([("Home", BASE), ("Destinations", BASE + "destinations/index.html"), (d["name"], url)])), ensure_ascii=False)}</script>
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
  {f'<p style="max-width:78ch;line-height:1.7;color:#33565e;font-size:1.02rem">{esc(d["description"])}</p>' if d.get("description") else ""}
  <p style="max-width:78ch;line-height:1.65;color:#33565e">{esc(dest_intro(d))}</p>
  {essays_block(d)}
  <div class="best"><b>Best months:</b> {esc(", ".join(peak) or "—")} &nbsp;·&nbsp; <b>Recommended window:</b> {esc(d["best_months"])}{closed_line}</div>
  <div class="kv">
    <div><span>Water type</span>{esc(d["water_type"])}</div>
    <div><span>Difficulty</span>{esc(d["difficulty"])}</div>
    <div><span>Access</span>{esc(d["access"])}</div>
    <div><span>Wetsuit</span><b>{esc(d["wetsuit"])}</b></div>
    <div><span>Current strength</span><b>{esc(d["current_strength"])}</b>{cur_note}</div>
    <div style="grid-column:1/-1"><span>Currents detail</span>{esc(d["currents"])}</div>
  </div>
  {pack_box(d)}
  {stay_box(d)}
  <span class="meta">Signature sea life</span>
  <div class="chips">{species}</div>
  <h2>When should you dive {esc(d["name"])}?</h2>
  <div style="overflow:auto"><table>
    <thead><tr><th>Month</th><th>Rating</th><th>Water</th><th>Viz</th><th>Sea life expected</th><th>Conditions</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
  {sites_block}
  {honest_block(d)}
  {verified}
  {related_block(d)}
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
    desc = "Season guides for the world's scuba diving destinations: best months, water temperature, visibility, currents and marine life."
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


COLOR_HEX = {"black": "#16181a", "white": "#f4f4f2", "blue": "#2563eb", "lime": "#a3e635",
             "pink": "#ec4899", "yellow": "#facc15", "red": "#dc2626", "orange": "#ea580c",
             "green": "#16a34a", "grey": "#9ca3af", "gray": "#9ca3af", "silver": "#c9ced3",
             "purple": "#7c3aed", "turquoise": "#14b8a6", "navy": "#1e3a5f",
             "clear": "#e8edef", "aquamarine": "#7fd4c9", "lilac": "#b79bd6", "blk": "#16181a"}


def product_ld(item):
    opts = item.get("options") or []
    if not opts:
        return None
    prices = [o["price_usd"] for o in opts]
    node = {"@type": "Product", "name": item["name"],
            "offers": {"@type": "AggregateOffer", "priceCurrency": "USD",
                       "lowPrice": min(prices), "highPrice": max(prices), "offerCount": len(opts),
                       "offers": [{"@type": "Offer", "price": o["price_usd"], "priceCurrency": "USD",
                                   "url": o.get("url", ""),
                                   "seller": {"@type": "Organization", "name": o.get("store", "")}}
                                  for o in opts]}}
    blurb = item.get("review") or item.get("blurb")
    if blurb:
        node["description"] = blurb
    img = item.get("image") or ""
    if img:
        node["image"] = img if img.startswith("http") else BASE + img
    return node


def gear_item_page(cat, item, prefix="../"):
    """Orbea-style product page: studio photo, buy/colour banner, review, specs."""
    slug = gear_slug(item["name"])
    url = BASE + "gear/" + slug + ".html"
    cat_slug = gear_slug(cat["category"])
    cat_title = cat.get("title") or ("Top " + cat["category"])
    img = item.get("image") or ""
    base = os.path.splitext(os.path.basename(img))[0] if img else ""
    hero_path = f"assets/gear/studio/hero/{base}.jpg"
    if not os.path.exists(os.path.join(ROOT, hero_path)):
        hero_path = img
    cimgs = item.get("color_images") or {}
    colors = item.get("colors") or []
    first = colors[0] if colors and cimgs.get(colors[0]) else None
    hero_src = cimgs.get(first, hero_path) if first else hero_path
    photo = (f'<figure class="gitem-photo"><img id="gimg" src="{prefix}{esc(hero_src)}" '
             f'alt="{esc(item["name"])}"></figure>' if hero_src else "")
    stage_open = '<div class="gitem-stage">' if hero_src else ""
    stage_close = "</div>" if hero_src else ""
    offers = order_offers(item.get("options"))
    lo = min((o["price_usd"] for o in item.get("options") or []), default=None)
    btns = "".join(
        f'<a class="pack-cta{"" if i == 0 else " ghost"}" href="{esc(o["url"])}" target="_blank" '
        f'rel="noopener sponsored">{esc(o["store"])} · {fmtp(o["price_usd"])}</a>'
        for i, o in enumerate(offers[:3]))
    def swatch_bg(cname):
        toks = [t.strip().lower() for t in re.split(r"[/+]", cname) if t.strip()]
        toks = [t for t in toks if "lens" not in t and "mirror" not in t] or [t.strip().lower() for t in re.split(r"[/+]", cname)]
        hx = [COLOR_HEX[t] for t in toks[:2] if t in COLOR_HEX]
        if not hx:
            hx = ["#8899a0"]
        if len(hx) == 1:
            return f"background:{hx[0]}"
        return f"background:linear-gradient(135deg,{hx[0]} 50%,{hx[1]} 50%)"
    swatches, cjs = "", ""
    if colors:
        dots = ""
        for i, c in enumerate(colors):
            act = " on" if (cimgs and i == 0) else ""
            click = f' onclick="pickC(this,\'{esc(c)}\')" role="button" tabindex="0"' if cimgs.get(c) else ""
            dots += (f'<span class="csw{act}" title="{esc(c)}"{click}>'
                     f'<i style="{swatch_bg(c)}"></i></span>')
        swatches = f'<div class="gitem-colors">{dots}</div>'
        if cimgs:
            cmap = {c: prefix + p for c, p in cimgs.items()}
            cjs = ('<script>var GIMG=' + json.dumps(cmap, ensure_ascii=False) + ';'
                   'function pickC(el,c){var i=document.getElementById("gimg");'
                   'if(GIMG[c]){i.src=GIMG[c];}'
                   'var s=document.querySelectorAll(".csw");'
                   'for(var k=0;k<s.length;k++)s[k].className="csw";'
                   'el.className="csw on";}</script>')
    banner = (f'<div class="gitem-banner">'
              f'<div class="gitem-id"><b>{esc(item["name"])}</b>'
              f'<span class="gitem-price">{f"from <b>{fmtp(lo)}</b>" if lo is not None else ""}</span>'
              f'<small>indicative — the retailer shows the live price</small></div>'
              f'{swatches}'
              f'<div class="pack-ctas">{btns}</div></div>{cjs}')
    rank = item.get("rank")
    kicker = f'#{rank} in <a href="{cat_slug}.html">{esc(cat_title)}</a>' if rank else f'<a href="{cat_slug}.html">{esc(cat_title)}</a>'
    review = item.get("review") or item.get("blurb") or ""
    specs = ""
    if item.get("specs"):
        specs = ('<h2>Specs</h2><dl class="gspecs">'
                 + "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in item["specs"].items())
                 + "</dl>")
    siblings = [i for i in _cat_items(cat) if i["name"] != item["name"]][:4]
    related = ""
    if siblings:
        lis = ""
        for s in siblings:
            s_lo = min((o["price_usd"] for o in s.get("options") or []), default=None)
            frm = f' <small>from {fmtp(s_lo)}</small>' if s_lo is not None else ""
            lis += f'<li><a href="{gear_slug(s["name"])}.html">{esc(s["name"])}</a>{frm}</li>'
        related = f'<h2>Also in this guide</h2><ul class="grel">{lis}</ul>'
    inner = (f'<p class="meta gitem-kicker">{kicker}</p>'
             f'{stage_open}{photo}{banner}{stage_close}'
             f'<h2>What makes it good?</h2>'
             f'<p class="greview" style="max-width:80ch">{esc(review)}</p>'
             f'{specs}{related}'
             f'<p class="meta"><a href="{cat_slug}.html">&larr; Back to {esc(cat_title)}</a></p>')
    desc = (item.get("blurb") or review)[:160]
    ld = graph_ld({"@type": "WebPage", "name": item["name"], "url": url, "description": desc},
                  crumbs([("Home", BASE), ("Gear guides", BASE + "gear/index.html"),
                          (cat_title, BASE + "gear/" + cat_slug + ".html"), (item["name"], url)]),
                  product_ld(item))
    return content_shell(f'{item["name"]} Review & Best Price | DiveSZN', desc, url, prefix,
                         item.get("blurb") or "", inner, ld)


def _cat_items(cat):
    items = list(cat.get("items") or [])
    for g in cat.get("thickness_groups") or []:
        items += g.get("items") or []
    return items

def gear_entry(item, prefix):
    img = item.get("image") or ""
    imgtag = f'<img src="{prefix}{esc(img)}" alt="{esc(item["name"])}" loading="lazy">' if img else ""
    specs = ""
    if item.get("specs"):
        specs = ('<dl class="gspecs">'
                 + "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in item["specs"].items())
                 + "</dl>")
    slug = gear_slug(item["name"])
    return (f'<div class="gentry"><div class="gphoto"><a href="{slug}.html">{imgtag}</a></div>'
            f'<div><h3>{item.get("rank", "")}. <a class="gitem-link" href="{slug}.html">{esc(item["name"])}</a></h3>'
            f'<p class="greview">{esc(item.get("review") or item.get("blurb"))}</p>{specs}{buy_box(item)}'
            f'<p class="meta" style="margin-top:8px"><a href="{slug}.html">Full page: photos, specs &amp; prices &rarr;</a></p></div></div>')

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
    desc = (intro or f'The best {cat["category"].lower()} for scuba diving in 2026.')[:160]
    items = _cat_items(cat)
    coll = {"@type": "CollectionPage", "name": cat.get("title"), "description": desc, "url": url}
    bc = crumbs([("Home", BASE), ("Gear guides", BASE + "gear/index.html"),
                 (cat.get("title") or cat["category"], url)])
    ld = graph_ld(coll, bc, *[product_ld(i) for i in items])
    return content_shell(title, desc, url, prefix, None, "".join(parts), ld)

BRAND_NAMES = ["Apeks", "Aqua Lung", "Aqualung", "Atomic Aquatics", "BARE", "Bare", "Cressi",
               "Fourth Element", "Garmin", "Henderson", "Hollis", "Mares", "O'Neill", "Pinnacle",
               "ScubaPro", "Scubapro", "Shearwater", "Sherwood", "Suunto", "TUSA", "Waterproof",
               "xDeep", "Zeagle"]
BRAND_LABEL = {"Aqualung": "Aqua Lung", "ScubaPro": "Scubapro", "BARE": "Bare"}


def brand_of(name):
    for b in BRAND_NAMES:
        if name.lower().startswith(b.lower()):
            return BRAND_LABEL.get(b, b)
    return name.split()[0]


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
    bsec = ""
    for cat in gear["categories"]:
        brands, seen, n = {}, set(), 0
        for it in _cat_items(cat):
            if it["name"] in seen:
                continue
            seen.add(it["name"])
            n += 1
            lo = min((o["price_usd"] for o in it.get("options") or []), default=None)
            brands.setdefault(brand_of(it["name"]), []).append((it, lo))
        cols = ""
        for b in sorted(brands):
            brows = ""
            for it, lo in sorted(brands[b], key=lambda t: t[0]["name"]):
                img = it.get("image") or ""
                th = (f'<span class="gbthumb"><img src="{prefix}{esc(img)}" alt="" loading="lazy"></span>'
                      if img else '<span class="gbthumb"></span>')
                frm = f"from {fmtp(lo)}" if lo is not None else ""
                brows += (f'<a class="gbrow" href="{gear_slug(it["name"])}.html">{th}'
                          f'<span><b>{esc(it["name"])}</b><small>{frm}</small></span></a>')
            cols += f'<div class="gbcol"><b class="gbrand">{esc(b)}</b>{brows}</div>'
        gslug = gear_slug(cat["category"])
        bsec += (f'<section class="dregion"><h3><span>{esc(cat["category"])}</span>'
                 f'<span class="bcount">{n} product{"" if n == 1 else "s"} · '
                 f'<a href="{gslug}.html" style="color:var(--accent)">guide &rarr;</a></span></h3>'
                 f'<div class="gbgrid">{cols}</div></section>')
    desc = "DiveSZN scuba gear — every product under its brand, plus ranked buyer's guides for masks, fins, regulators, BCDs, dive computers and wetsuits."
    inner = (f'<p class="greview" style="max-width:80ch">{esc(gear.get("intro") or "")}</p>'
             f'{bsec}'
             f'<h2 style="margin-top:40px">The buyer&#8217;s guides (articles)</h2><ul class="artlist">{rows}</ul>'
             f'<a class="cta" href="../index.html#gear">Open the interactive gear guide &rarr;</a>')
    ld = graph_ld({"@type": "CollectionPage", "name": "DiveSZN gear buyer's guides",
                   "description": desc, "url": url},
                  crumbs([("Home", BASE), ("Gear guides", url)]))
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
<p class="greview" style="max-width:78ch">The seasonal calendar covers every destination on the site across all twelve months —
water temperature, visibility, currents, marine-life timing and a season rating for each. It is compiled and
cross-checked against dive-operator and liveaboard calendars, marine-park authorities and ocean
sea-temperature sources, then hand-verified. Water temperatures are typical monthly ranges (±1&deg;C) and
marine-life timing shifts year to year with plankton and lunar cycles, so we always say the same thing: confirm
current conditions with a local dive centre before you travel.</p>
<h2>Beyond the planner</h2>
<p class="greview" style="max-width:78ch">The same seasonal data powers our <a href="marine-life/index.html">marine-life
guides</a> — where and when to dive whale sharks, mantas, hammerheads and more — and the
<a href="months/index.html">month-by-month guides</a> that rank where diving is at its best for any travel date.</p>
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

# ---------------------------------------------------------------- marine life
RATING_RANK = {"Peak": 0, "Good": 1, "Shoulder": 2, "Low": 3, "Closed": 9}

with open(os.path.join(ROOT, "marine-life.json")) as _mf:
    EXPERIENCES = json.load(_mf)["experiences"]

def where_when(dests, keywords):
    kws = [k.lower() for k in keywords]
    rows = []
    for x in dests:
        months = [m for m in MONTHS
                  if any(k in (x["monthly"][m].get("marine_life") or "").lower() for k in kws)]
        if not months:
            continue
        best = min(RATING_RANK.get(x["monthly"][m]["rating"], 9) for m in months)
        rows.append((best, x, months))
    rows.sort(key=lambda r: (r[0], r[1]["name"]))
    return rows

def marine_article(exp, dests, prefix="../"):
    url = BASE + "marine-life/" + exp["slug"] + ".html"
    rows = where_when(dests, exp["keywords"])
    body_rows = "".join(
        f'<tr><td><b><a href="{prefix}destinations/{x["slug"]}.html">{esc(x["name"])}</a></b>'
        f'<div class="meta">{esc(x["country"])}</div></td><td>{esc(", ".join(months))}</td></tr>'
        for _, x, months in rows)
    if rows:
        table = (f'<h2>Where &amp; when to dive it</h2>'
                 f'<p class="greview" style="max-width:78ch">Pulled live from our seasonal data — the destinations where '
                 f'{esc(exp["short"])} shows in the water, and the months to catch it.</p>'
                 f'<div style="overflow:auto"><table><thead><tr><th>Destination</th><th>Best months</th></tr></thead>'
                 f'<tbody>{body_rows}</tbody></table></div>')
    else:
        table = (f'<h2>Where &amp; when to dive it</h2>'
                 f'<p class="greview" style="max-width:78ch">{esc(exp.get("no_data") or "This is an opportunistic encounter — none of our current destinations has a fixed season for it yet.")}</p>')
    # "Beyond scuba" — snorkel & cage experiences (not scuba, so not destinations),
    # an affiliate surface: book via a tours platform (raw here; wrap when the
    # experiences affiliate id is set).
    beyond = ""
    if exp.get("beyond_scuba"):
        brows = "".join(
            f'<tr><td><b>{esc(b["name"])}</b><div class="meta">{esc(b["country"])} · {esc(b["mode"])}</div></td>'
            f'<td>{esc(", ".join(b["months"]))}</td>'
            f'<td><a class="pack-cta ghost" href="https://www.getyourguide.com/s/?q={urllib.parse.quote(b["q"])}" '
            f'target="_blank" rel="noopener sponsored">Book &rarr;</a></td></tr>'
            for b in exp["beyond_scuba"])
        beyond = (f'<h2>Beyond scuba — snorkel &amp; cage encounters</h2>'
                  f'<p class="greview" style="max-width:78ch">{esc(exp.get("beyond_intro") or "Some of the best encounters with this animal do not run on scuba — they are snorkel or cage-diving trips. If that is the experience you are after, these are the places to book it.")}</p>'
                  f'<div style="overflow:auto"><table><thead><tr><th>Where</th><th>Season</th><th></th></tr></thead>'
                  f'<tbody>{brows}</tbody></table></div>')
    tips = "".join(f"<li>{esc(t)}</li>" for t in exp.get("tips", []))
    if exp.get("image"):
        cap = f'<figcaption>{esc(exp["image_credit"])}</figcaption>' if exp.get("image_credit") else ""
        hero_img = f'<figure class="marine-hero"><img src="{esc(exp["image"])}" alt="{esc(exp["title"])}">{cap}</figure>'
    else:
        hero_img = ""
    inner = (hero_img
             + f'<p class="greview" style="max-width:78ch">{esc(exp["intro"])}</p>'
             + table + beyond
             + (f'<div class="tipbox"><b>Good to know</b><ul>{tips}</ul></div>' if tips else "")
             + f'<a class="cta" href="{prefix}index.html">Plan a trip around it — open the dive planner &rarr;</a>')
    art = {"@type": "Article", "headline": exp["title"], "description": exp["desc"], "url": url,
           "author": {"@type": "Organization", "name": "DiveSZN"},
           "publisher": {"@type": "Organization", "name": "DiveSZN", "url": BASE}}
    if exp.get("image"):
        art["image"] = exp["image"]
    ld = graph_ld(art, crumbs([("Home", BASE), ("Marine life", BASE + "marine-life/index.html"),
                               (exp["title"], url)]))
    return content_shell(exp["title"] + " | DiveSZN", exp["desc"], url, prefix, exp.get("hero_sub"), inner, ld)

def marine_index_page(prefix="../"):
    url = BASE + "marine-life/index.html"
    def _mrow(e):
        if e.get("image"):
            th = '<div class="th photo"><img src="%s" alt="" loading="lazy"></div>' % esc(e["image"])
        else:
            th = '<div class="th"></div>'
        return ('<li><a href="%s.html">%s<div><h3>%s</h3><p>%s</p></div></a></li>'
                % (e["slug"], th, esc(e["title"]), esc(e.get("hero_sub", ""))))
    rows = "".join(_mrow(e) for e in EXPERIENCES)
    desc = ("Diving with the ocean's headline animals — whale sharks, manta rays, hammerheads, mola mola, "
            "sea lions and more — with the best destinations and seasons for each.")
    inner = (f'<p class="greview" style="max-width:80ch">The ocean&#8217;s headline encounters — what they are, and '
             f'where and when to dive them, pulled live from DiveSZN&#8217;s seasonal data.</p>'
             f'<h2>Encounters</h2><ul class="artlist">{rows}</ul>'
             f'<a class="cta" href="../index.html">Open the dive planner &rarr;</a>')
    ld = graph_ld({"@type": "CollectionPage", "name": "Marine life encounters",
                   "description": desc, "url": url},
                  crumbs([("Home", BASE), ("Marine life", url)]))
    return content_shell("Marine Life — Dive With the Ocean's Icons | DiveSZN", desc, url, prefix,
                         "Whale sharks to orcas — what they are, and where and when to dive them.", inner, ld)

# ---------------------------------------------------------------- month hubs
def month_ranked(rankings, month, dests_by_name):
    """Merge a month's two half-periods (max score per destination), keep
    Peak/Good, cap at 15 — the same selection the SPA's monthly guide makes."""
    best = {}
    for per in rankings["periods"]:
        if per["month"] != month:
            continue
        for r in per["ranked"]:
            cur = best.get(r["name"])
            if cur is None or r["score"] > cur["score"]:
                best[r["name"]] = r
    rows = sorted(best.values(), key=lambda r: -r["score"])
    rows = [r for r in rows if r["rating"] in ("Peak", "Good") and r["name"] in dests_by_name]
    # one destination per country per guide (no Fuvahmulah + Maldives double-spot)
    seen, out = set(), []
    for r in rows:
        if r["country"] in seen:
            continue
        seen.add(r["country"]); out.append(r)
    return out[:15]

def month_page(month, rankings, dests_by_name):
    full = MONTH_FULL[month]
    url = BASE + "months/" + full.lower() + ".html"
    rows = month_ranked(rankings, month, dests_by_name)
    groups, order = {}, []
    for r in rows:
        g = DEST_GROUP.get(r["name"]) or r["region"]
        if g not in groups:
            groups[g] = []; order.append(g)
        groups[g].append(r)

    def block(r):
        d = dests_by_name[r["name"]]
        mm = d["monthly"][month]
        ctry = f' <span class="meta">— {esc(r["country"])}</span>' if r["country"] and r["country"] != r["name"] else ""
        img = d.get("image") or ""
        photo = (f'<div class="gphoto dphoto"><img src="{esc(img)}" alt="{esc(r["name"])}" loading="lazy"></div>'
                 if img else '<div class="gphoto dphoto"></div>')
        chips = (f'<span class="badge sm" style="background:{RCOLOR[r["rating"]]}'
                 f'{";color:#fff" if r["rating"] in ("Peak","Low","Closed") else ""}">{r["rating"]}</span> '
                 f'<span class="chip">{r["water_temp_c"] if r["water_temp_c"] is not None else "—"}°C</span> '
                 f'<span class="chip">{r.get("visibility_m") or "—"}m viz</span>'
                 + (f' <span class="chip">{esc(r["current_strength"])} current</span>' if r.get("current_strength") else ""))
        expect = (f'<b>What to expect in {full}:</b> {esc(mm["marine_life"])}.'
                  + (f' <b>Conditions:</b> {esc(mm["conditions"])}.' if mm.get("conditions") else ""))
        return (f'<div class="gentry">{photo}<div>'
                f'<h3><a href="../destinations/{d["slug"]}.html" style="text-decoration:none;color:inherit">{esc(r["name"])}</a>{ctry}</h3>'
                f'<div class="chips" style="margin:2px 0 10px">{chips}</div>'
                f'<p class="greview">{esc(d.get("description") or d.get("highlights") or "")}</p>'
                f'<p class="greview">{expect}</p>'
                f'<a href="../destinations/{d["slug"]}.html">Full guide: {esc(r["name"])} &rarr;</a></div></div>')

    sections = ""
    for g in order:
        rs = groups[g]
        peak_n = sum(1 for r in rs if r["rating"] == "Peak")
        lede = (f'{rs[0]["name"]} carries the region this month.' if len(rs) == 1 else
                f'{len(rs)} picks, ' + ("all at peak season" if peak_n == len(rs) else f"{peak_n} at peak")
                + f' — {rs[0]["name"]} leads.')
        sections += (f'<h2 class="region-head">{esc(g)}</h2><p class="region-lede">{esc(lede)}</p>'
                     + "".join(block(r) for r in rs))

    mi = MONTHS.index(month)
    prev_m, next_m = MONTH_FULL[MONTHS[(mi + 11) % 12]], MONTH_FULL[MONTHS[(mi + 1) % 12]]
    pager = (f'<p class="meta" style="display:flex;justify-content:space-between;gap:12px">'
             f'<a href="{prev_m.lower()}.html">&larr; {prev_m}</a>'
             f'<a href="index.html">All months</a>'
             f'<a href="{next_m.lower()}.html">{next_m} &rarr;</a></p>')
    top3 = ", ".join(r["name"] for r in rows[:3])
    desc = f"The best scuba diving in {full}: {top3} and more — season ratings, water temperature, visibility and the marine life in season."[:160]
    intro = MONTH_INTROS.get(month) or ""
    cut = intro.find(". ")
    lede, rest = (intro[:cut + 1], intro[cut + 2:]) if cut > -1 else (intro, "")
    inner = (pager
             + (f'<p class="lede">{esc(lede)}</p>' if lede else "")
             + (f'<p class="greview" style="max-width:80ch">{esc(rest)}</p>' if rest else "")
             + sections + pager
             + f'<a class="cta" href="../index.html">Plan your {full} trip in the dive planner &rarr;</a>')
    ld = graph_ld({"@type": "CollectionPage", "name": f"Best scuba diving in {full}",
                   "description": desc, "url": url},
                  crumbs([("Home", BASE), ("Best diving by month", BASE + "months/index.html"), (full, url)]))
    return content_shell(f"Best Scuba Diving in {full} — Where to Dive | DiveSZN", desc, url, "../",
                         f"Where the water is at its best in {full}, region by region.", inner, ld)

def months_index_page(rankings, dests_by_name):
    url = BASE + "months/index.html"
    rows = ""
    used = set()   # each month gets a different destination photo — no repeats down the list
    for m in MONTHS:
        full = MONTH_FULL[m]
        ranked = month_ranked(rankings, m, dests_by_name)
        teaser = ", ".join(r["name"] for r in ranked[:3])
        img = ""
        for r in ranked:
            cand = dests_by_name[r["name"]].get("image") or ""
            if cand and cand not in used:
                img = cand; used.add(cand); break
        th = (f'<div class="th photo"><img src="{esc(img)}" alt="" loading="lazy"></div>'
              if img else '<div class="th"></div>')
        rows += (f'<li><a href="{full.lower()}.html">{th}'
                 f'<div><h3>Best diving in {full}</h3><p>{esc(teaser)}</p></div></a></li>')
    desc = "Month-by-month guides to the world's best scuba diving — where the season, marine life and visibility line up for each month of the year."[:160]
    inner = (f'<p class="greview" style="max-width:80ch">Twelve guides, one per month — every destination scored for '
             f'that month and grouped by region, so your travel dates pick the spot.</p>'
             f'<h2>Guides</h2><ul class="artlist">{rows}</ul>'
             f'<a class="cta" href="../index.html">Open the dive planner &rarr;</a>')
    ld = graph_ld({"@type": "CollectionPage", "name": "Best scuba diving by month", "description": desc, "url": url},
                  crumbs([("Home", BASE), ("Best diving by month", url)]))
    return content_shell("Best Scuba Diving by Month | DiveSZN", desc, url, "../",
                         "Where to dive in January through December.", inner, ld)

def main():
    with open(os.path.join(ROOT, "diving-destinations.json")) as f:
        dests = json.load(f)["destinations"]
    with open(os.path.join(ROOT, "gear-guide.json")) as f:
        gear = json.load(f)
    with open(os.path.join(ROOT, "diving-rankings.json")) as f:
        rankings = json.load(f)
    dests_by_name = {d["name"]: d for d in dests}
    _SLUGS.update({d["name"]: d["slug"] for d in dests})
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
    item_slugs = []
    for cat in gear["categories"]:
        slug = gear_slug(cat["category"]); gear_slugs.append(slug)
        with open(os.path.join(geardir, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(gear_page(cat))
        for item in _cat_items(cat):
            islug = gear_slug(item["name"])
            if islug in item_slugs:
                continue
            item_slugs.append(islug)
            with open(os.path.join(geardir, islug + ".html"), "w", encoding="utf-8") as f:
                f.write(gear_item_page(cat, item))
    with open(os.path.join(geardir, "index.html"), "w", encoding="utf-8") as f:
        f.write(gear_index_page(gear))

    # marine-life articles (data-generated where & when)
    marinedir = os.path.join(ROOT, "marine-life")
    os.makedirs(marinedir, exist_ok=True)
    for exp in EXPERIENCES:
        with open(os.path.join(marinedir, exp["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(marine_article(exp, dests))
    with open(os.path.join(marinedir, "index.html"), "w", encoding="utf-8") as f:
        f.write(marine_index_page())

    # legacy URLs for destinations that split into several (keep old links alive)
    LEGACY = {"red-sea-egypt": {"title": "Red Sea (Egypt)",
                                "heirs": ["sharm-el-sheikh", "hurghada-el-gouna", "marsa-alam", "dahab"]}}
    for old_slug, info in LEGACY.items():
        heirs = [d for d in dests if d["slug"] in info["heirs"]]
        if not heirs:
            continue
        links = "".join(f'<li><a href="{d["slug"]}.html"><b>{esc(d["name"])}</b>'
                        f'<small>{esc(d.get("highlights") or "")}</small></a></li>' for d in heirs)
        url = BASE + "destinations/" + old_slug + ".html"
        stub = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(info["title"])} Diving — Now Split by Resort Town | DiveSZN</title>
<meta name="description" content="Our {esc(info["title"])} guide is now split into dedicated destination guides.">
<link rel="canonical" href="{esc(url)}"><style>{CSS}</style></head><body>
{topbar()}
<main class="wrap"><h1>{esc(info["title"])} — now four destinations</h1>
<p class="meta">We split this guide so each resort town gets its own season calendar, dive sites and photos.</p>
<ul class="dirlist">{links}</ul></main>
{footer_html()}
</body></html>"""
        with open(os.path.join(outdir, old_slug + ".html"), "w", encoding="utf-8") as f:
            f.write(stub)

    # month hubs ("best diving in January" ... one per month)
    monthdir = os.path.join(ROOT, "months")
    os.makedirs(monthdir, exist_ok=True)
    for m in MONTHS:
        with open(os.path.join(monthdir, MONTH_FULL[m].lower() + ".html"), "w", encoding="utf-8") as f:
            f.write(month_page(m, rankings, dests_by_name))
    with open(os.path.join(monthdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(months_index_page(rankings, dests_by_name))

    # trust / info pages (root)
    with open(os.path.join(ROOT, "about.html"), "w", encoding="utf-8") as f:
        f.write(about_page())
    with open(os.path.join(ROOT, "how-we-score.html"), "w", encoding="utf-8") as f:
        f.write(score_page())

    urls = ([BASE, BASE + "about.html", BASE + "how-we-score.html", BASE + "privacy.html",
             BASE + "destinations/index.html", BASE + "gear/index.html", BASE + "months/index.html"]
            + [BASE + "months/" + MONTH_FULL[m].lower() + ".html" for m in MONTHS]
            + [BASE + "gear/" + s + ".html" for s in gear_slugs]
            + [BASE + "gear/" + s + ".html" for s in item_slugs]
            + [BASE + "marine-life/index.html"]
            + [BASE + "marine-life/" + e["slug"] + ".html" for e in EXPERIENCES]
            + [BASE + "destinations/" + d["slug"] + ".html" for d in dests])
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sm += f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n"
    sm += "</urlset>\n"
    with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
        f.write(sm)
    with open(os.path.join(ROOT, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n")
    print(f"Wrote {len(dests)} destination pages + index, 12 month hubs + index, "
          f"{len(gear_slugs)} gear pages + index, about + how-we-score, "
          f"sitemap.xml ({len(urls)} URLs), robots.txt")

if __name__ == "__main__":
    main()
