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
# Owner-approved tonal (single-hue) season palette — used on every generated
# page (destinations, month hubs, marine ribbons). Keep in sync with the
# TONAL map in index.html.
TONAL = {"Peak":"#0e7569","Good":"#5cb8ab","Shoulder":"#dfa826","Low":"#cfe4e0","Closed":"#b9c6c9"}
# Badge/ink pairing on the tonal fills (all pairs >=4.5:1)
TONAL_TEXT = {"Peak":"#ffffff","Good":"#0e2f37","Shoulder":"#0e2f37","Low":"#0e2f37","Closed":"#0e2f37"}
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
    """Parse the editorial MONTH_INTROS ledes out of index.html so the SPA
    stays the single source of truth. Fails loudly if the shape changes —
    a silent {} would strip the owner-written ledes from all 12 month hubs."""
    m = re.search(r"var MONTH_INTROS=\{(.*?)\};", _index_src(), re.S)
    if not m:
        raise RuntimeError("MONTH_INTROS not found in index.html")
    intros = {}
    for im in re.finditer(r'(\w{3}):"((?:[^"\\]|\\.)*)"', m.group(1)):
        intros[im.group(1)] = _junesc(im.group(2))
    missing = [mo for mo in MONTHS if not intros.get(mo)]
    if missing:
        raise RuntimeError(f"MONTH_INTROS parsed incomplete (missing {', '.join(missing)})")
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
:root{--bg:#f4f9f9;--panel:#ffffff;--ink:#0e2f37;--muted:#4a6a71;--accent:#0e9c92;--cta:#0b7d75;--cta-deep:#06333c;--line:#d7e5e7;
--serif:'Fraunces',Georgia,'Iowan Old Style','Times New Roman',serif;
--sans:'Plus Jakarta Sans',system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
--mono:'JetBrains Mono',ui-monospace,'SF Mono',Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;font-family:var(--sans);
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
.cta{display:inline-block;background:linear-gradient(135deg,var(--cta),var(--cta-deep));color:#eafaf8;border-radius:8px;padding:10px 16px;font-weight:700;text-decoration:none;margin:16px 0}
.meta{color:var(--muted);font-size:.8rem}
footer{color:var(--muted);font-size:.74rem;text-align:center;padding:40px 16px 28px;line-height:1.7;border-top:1px solid var(--line);margin-top:56px}
.foot-mark{font-family:var(--serif);font-weight:600;font-size:clamp(2.6rem,9vw,5.2rem);line-height:1;letter-spacing:-.03em;color:var(--ink);margin:0 0 4px}
.foot-mark b{color:var(--accent)}
.foot-tag{font-family:var(--mono);font-size:.64rem;letter-spacing:.24em;text-transform:uppercase;color:var(--muted)}
.foot-nav{display:flex;flex-wrap:wrap;justify-content:center;gap:6px 22px;margin:22px 0 6px}
.foot-nav a{font-family:var(--mono);font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink);text-decoration:none}
.foot-nav a:hover{color:var(--accent)}
footer .disclosure{max-width:780px;margin:14px auto 0;color:var(--muted);font-size:.78rem}
.dirlist{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:8px}
.dirlist li{background:var(--panel);border:1px solid var(--line);border-radius:10px}
.dirlist a{display:block;padding:10px 12px;text-decoration:none;color:var(--ink)}
.dirlist small{display:block;color:var(--muted)}
.packbox{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:12px;padding:14px 16px;margin:18px 0}
.pack-head{font-family:var(--mono);font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;color:var(--cta);margin-bottom:6px}
.pack-body{margin:0 0 11px;color:#33565e;font-size:.92rem;line-height:1.6}
.pack-ctas{display:flex;flex-wrap:wrap;gap:8px}
.pack-cta{display:inline-block;background:linear-gradient(135deg,var(--cta),var(--cta-deep));color:#eafaf8;border-radius:9px;padding:9px 15px;font-size:.83rem;font-weight:700;text-decoration:none}
.pack-cta.ghost{background:#fff;color:#0b7d75;border:1px solid #b9d2d0}
.staybox{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:12px;padding:14px 16px;margin:18px 0}
.prof-essays{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin:18px 0 4px}
.prof-essay{background:linear-gradient(165deg,#ffffff,#f2f9f9);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.prof-essay h2{margin:0 0 8px;font-size:1.12rem}
.prof-essay p{margin:0;color:#33565e;line-height:1.7;font-size:.95rem}
.gitem-kicker{font-family:var(--mono);letter-spacing:.08em;text-transform:uppercase;font-size:.68rem}
.gitem-kicker a{color:var(--accent);text-decoration:none}
.gitem-stage{margin:10px 0 26px}
/* the photo card carries a studio-toned band below the product (its bg matches
   the hero canvas bottom), and the white banner floats ON that band — on the
   photo, under the gear, with the photo background behind it (owner spec) */
.gitem-photo{margin:0;border-radius:16px;overflow:hidden;border:1px solid var(--line);
  background:#e9ebed;padding-bottom:22px}
.gitem-photo img{display:block;width:100%;height:auto}
.gitem-banner{display:flex;flex-wrap:wrap;align-items:center;gap:14px 30px;background:#fff;
  border:1px solid var(--line);border-radius:14px;padding:16px 22px;margin:-30px 22px 0;position:relative;
  box-shadow:0 18px 36px -24px rgba(13,60,70,.3)}
@media(max-width:760px){.gitem-photo img{object-fit:contain}
  .gitem-banner{margin:-16px 12px 0;padding:14px 16px}}
.gitem-id b{font-family:var(--serif);font-size:1.15rem;display:block}
.gitem-price{font-family:var(--mono);font-size:.9rem;color:var(--ink)}
.gitem-price b{color:var(--ink);font-size:1.15rem;font-family:var(--mono);font-variant-numeric:tabular-nums;display:inline}
.gitem-id small{display:block;color:var(--muted);font-size:.64rem;margin-top:2px}
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
.gverdict{display:grid;grid-template-columns:1fr 1fr;gap:34px;margin:26px 0 30px}
@media(max-width:640px){.gverdict{grid-template-columns:1fr;gap:20px}}
.gverdict h3{font-family:var(--mono);font-size:.68rem;letter-spacing:.22em;text-transform:uppercase;
  color:var(--accent);border-top:1px solid var(--line);padding-top:12px;margin:0 0 10px;font-weight:600}
.gverdict .gv-con h3{color:var(--muted)}
.gverdict ul{margin:0;padding:0;list-style:none}
.gverdict li{padding:8px 0;border-bottom:1px solid var(--line);font-size:.9rem;line-height:1.55;color:var(--ink)}
.gverdict li:last-child{border-bottom:none}
.gspecs{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px;margin:0 0 12px}
.gspecs div{background:#f0f6f7;border:1px solid var(--line);border-radius:8px;padding:6px 10px}
.gspecs dt{color:var(--muted);font-size:.6rem;text-transform:uppercase;letter-spacing:.5px;margin:0}
.gspecs dd{margin:2px 0 0;font-family:var(--mono);font-size:.76rem;color:#0b6b74;min-width:0;overflow-wrap:anywhere}
.buybox{background:#f6fbfb;border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-top:6px}
.buy-top{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;margin-bottom:9px}
.buy-lead{font-family:var(--mono);font-size:.62rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.buy-from{font-family:var(--serif)}.buy-from b{color:var(--ink);font-family:var(--mono);font-variant-numeric:tabular-nums}
.buy-live{font-size:.68rem;color:var(--muted)}
.tipbox{background:#f2f9f9;border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:14px 0}
.tipbox ul{margin:6px 0 0;padding-left:18px}.tipbox li{margin:4px 0;color:#33565e;font-size:.9rem}
@media(max-width:640px){.gentry{grid-template-columns:1fr}.artlist a{grid-template-columns:90px 1fr}.gspecs{grid-template-columns:repeat(2,minmax(0,1fr))}}
.region-head{font-family:var(--serif);font-size:1.5rem;margin:34px 0 2px;padding-top:22px;border-top:2px solid var(--line)}
.region-lede{color:var(--muted);font-size:.9rem;margin:2px 0 8px}
.dphoto img{width:100%;height:100%;max-width:none;max-height:none;object-fit:cover}
.badge.sm{font-size:.66rem}
"""

# ---------------------------------------------------- shared design language
# The owner-approved destination redesign (2026-07) factored into a shared
# block: page gradient, sticky blurred topbar, photo hero with scrim + mono
# kicker + serif title, white 18px-radius cards with soft shadows and hover
# lifts, mono kickers in --accent-deep, reveal hooks. A page opts in with
# <body class="v2">; destination-only parts (season calendar, fact cards,
# dive-site table…) stay in DEST_CSS under .dest2.
V2_CSS = """
body.v2{--muted:#4a6a71;--ink-soft:#33565e;--accent-deep:#0b7d75;
  background:linear-gradient(180deg,#eef7f6 0%,#f4f9fb 40%,#eef4f8 100%)}
.v2 a{color:var(--accent-deep)}
.v2 .topbar{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.92);
  -webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border-bottom:1px solid rgba(14,117,105,.10)}
.rev{will-change:opacity,transform}
.kick{font-family:var(--mono);font-size:.72rem;letter-spacing:.22em;text-transform:uppercase;
  color:var(--accent-deep);margin:16px 0 10px}
/* photo hero — the gradient shows through if the photo 404s (onerror hides only the img) */
.hero2{position:relative;margin-top:4px;border-radius:20px;overflow:hidden;height:520px;
  box-shadow:0 16px 44px rgba(18,51,47,.14);background:linear-gradient(160deg,#0e2f37,#0b7d75)}
.hero2>img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.hero2-scrim{position:absolute;inset:0;background:linear-gradient(180deg,rgba(8,32,29,0) 45%,rgba(8,32,29,.62) 100%);pointer-events:none}
.hero2-bar{position:absolute;left:40px;right:40px;bottom:34px;display:flex;align-items:flex-end;
  justify-content:space-between;gap:16px 24px;flex-wrap:wrap}
.hero2-kicker{font-family:var(--mono);font-size:.8rem;letter-spacing:2.5px;color:#a8e6db;text-transform:uppercase;margin-bottom:8px}
.hero2 h1{font-family:var(--serif);font-size:clamp(2.3rem,4.8vw,3.6rem);font-weight:600;color:#fff;margin:0;
  line-height:1.05;text-shadow:0 2px 20px rgba(8,32,29,.4)}
.hero2-sub{color:#e8f7f5;max-width:62ch;margin:10px 0 0;font-size:1.02rem;line-height:1.6;
  text-shadow:0 1px 14px rgba(8,32,29,.5)}
.hero2-pills{display:flex;gap:10px;padding-bottom:6px;flex-wrap:wrap}
.hero2-pills span{background:rgba(255,255,255,.16);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);
  border:1px solid rgba(255,255,255,.28);color:#fff;font-size:.88rem;font-weight:600;padding:8px 16px;
  border-radius:999px;white-space:nowrap}
.credit2{position:absolute;right:12px;top:12px;width:24px;height:24px;border-radius:50%;
  background:rgba(8,32,29,.45);color:rgba(255,255,255,.9);font-size:.74rem;font-family:var(--mono);
  display:flex;align-items:center;justify-content:center;cursor:help}
.hero2-hub{height:400px;margin-bottom:26px}
.hero2-hub h1{font-size:clamp(2rem,4.4vw,3rem)}
@media(max-width:640px){.hero2{height:320px;border-radius:14px}
  .hero2-bar{left:18px;right:18px;bottom:16px;flex-direction:column;align-items:flex-start;gap:10px}
  .hero2-pills{padding-bottom:0}.hero2-pills span{font-size:.78rem;padding:6px 12px}
  .hero2-hub{height:300px;margin-bottom:18px}.hero2-sub{font-size:.88rem}}
/* card language */
.v2 .gentry{background:#fff;border:none;border-radius:18px;padding:20px 22px;margin:16px 0;
  box-shadow:0 8px 30px rgba(18,51,47,.06);transition:transform .25s ease,box-shadow .25s ease}
.v2 .gentry:hover{transform:translateY(-3px);box-shadow:0 14px 36px rgba(18,51,47,.10)}
.v2 .gentry h3,.v2 .artlist h3{font-family:var(--serif)}
.v2 .gphoto{border-radius:12px}
.v2 .artlist li{background:#fff;border:none;border-radius:16px;margin:0 0 14px;
  box-shadow:0 6px 22px rgba(18,51,47,.05);transition:transform .25s ease,box-shadow .25s ease}
.v2 .artlist li:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(18,51,47,.09)}
.v2 .artlist a{padding:14px 16px}
.v2 .artlist .th{border-radius:10px}
.v2 .dirlist{gap:14px}
.v2 .dirlist li{background:#fff;border:none;border-radius:16px;box-shadow:0 6px 22px rgba(18,51,47,.05);
  transition:transform .25s ease,box-shadow .25s ease}
.v2 .dirlist li:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(18,51,47,.09)}
.v2 .dirlist a{padding:13px 16px}
.v2 .dirlist b{font-family:var(--serif);font-size:1.02rem}
.v2 .dirlist small{font-family:var(--mono);font-size:.68rem;margin-top:4px}
.v2 .tipbox{background:#fff;border:none;border-radius:16px;padding:16px 20px;
  box-shadow:0 6px 22px rgba(18,51,47,.05)}
.v2 .tipbox>b{font-family:var(--mono);font-size:.7rem;letter-spacing:.18em;text-transform:uppercase;color:var(--accent-deep)}
.tablecard{background:#fff;border-radius:18px;box-shadow:0 8px 30px rgba(18,51,47,.06);
  padding:8px 20px 14px;overflow-x:auto;margin:14px 0}
.v2 .region-head{border-top:none;padding-top:8px;margin:38px 0 2px}
.v2 .region-head::before{content:"";display:block;width:64px;height:3px;border-radius:2px;
  margin-bottom:12px;background:linear-gradient(90deg,var(--accent),transparent)}
.v2 .cta,.v2 .pack-cta{background:var(--cta-deep);transition:background .2s ease,transform .2s ease}
.v2 .cta{border-radius:12px;padding:13px 22px;color:#fff}
.v2 .cta:hover,.v2 .pack-cta:hover{background:var(--cta);transform:translateY(-2px)}
.v2 .pack-cta.ghost{background:#fff;color:#0e7569;border-color:#bfe0da}
.v2 .pack-cta.ghost:hover{background:#0e7569;color:#fff;border-color:#0e7569}
.v2 .hero.plain{background:linear-gradient(160deg,#0e2f37,#0b7d75)}
@media(max-width:640px){.v2 .gentry{padding:16px 14px}.v2 .artlist a{padding:11px 12px}}
@media(prefers-reduced-motion:reduce){.v2 .gentry,.v2 .artlist li,.v2 .dirlist li,.v2 .cta,.v2 .pack-cta{transition:none}}
"""

# ------------------------------------------------------- destination redesign
# Owner-approved Tofo redesign (2026-07), applied to every destination page.
# Destination-specific parts only — the shared language lives in V2_CSS.
DEST_CSS = """
.dest2 h1,.dest2 h2,.dest2 h3{font-family:var(--serif)}
.dest2 .wrap{max-width:1240px;padding:24px 32px 64px}
.dest2 .dback{margin:0 0 12px;font-family:var(--mono);font-size:.74rem;letter-spacing:.08em;text-transform:uppercase}
.dest2 .dback a{color:var(--accent-deep);text-decoration:none}
.dest2 .dback a:hover{color:var(--cta-deep);text-decoration:underline}
.dest2 .sec-h{font-size:2rem;font-weight:600;letter-spacing:-.01em;margin:0 0 20px;color:var(--ink)}
/* intro */
.lead2{font-size:1.22rem;line-height:1.75;color:var(--ink-soft);max-width:1160px;margin:34px 0 0}
.lead2sub{font-size:1.02rem;line-height:1.7;color:var(--ink-soft);max-width:1160px;margin:14px 0 0}
/* expect / encounter cards */
.dest2 .prof-essays{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin:30px 0 0}
.dest2 .prof-essay{background:#fff;border:none;border-radius:18px;padding:28px 32px;
  box-shadow:0 8px 30px rgba(18,51,47,.06);transition:transform .25s ease,box-shadow .25s ease}
.dest2 .prof-essay:hover{transform:translateY(-4px);box-shadow:0 16px 40px rgba(18,51,47,.10)}
.dest2 .prof-essay h2{font-size:1.63rem;font-weight:600;margin:0 0 14px;color:var(--ink)}
.dest2 .prof-essay p{margin:0;font-size:1.03rem;line-height:1.8;color:var(--ink-soft)}
@media(max-width:860px){.dest2 .prof-essays{grid-template-columns:1fr}}
/* best-months strip */
.best2{margin-top:22px;background:linear-gradient(90deg,#e2f3f0,#eaf6f6);border:1px solid #cfe8e3;
  border-radius:14px;padding:16px 24px;display:flex;align-items:center;gap:14px 36px;flex-wrap:wrap}
.pair{display:flex;align-items:baseline;gap:8px}
.lbl{font-family:var(--mono);font-size:.75rem;letter-spacing:1.2px;text-transform:uppercase;color:var(--muted)}
.pair .val{font-size:1rem;font-weight:600;color:var(--ink)}
/* season calendar */
.cal{margin-top:44px}
.calgrid{display:grid;grid-template-columns:repeat(12,1fr);gap:6px;max-width:820px}
.calm{appearance:none;-webkit-appearance:none;background:none;border:0;padding:0;margin:0;cursor:pointer;
  font:inherit;display:block;width:100%}
.calbar{display:block;height:36px;border-radius:8px;border:2.5px solid transparent;
  transition:transform .2s ease,filter .2s ease,border-color .15s ease}
.calm:hover .calbar{transform:translateY(-3px);filter:brightness(1.06)}
.calm.on .calbar{border-color:var(--ink)}
.calm:focus-visible .calbar{outline:2px solid var(--accent-deep);outline-offset:2px}
.callab{display:block;text-align:center;margin-top:6px;font-family:var(--mono);font-size:.68rem;
  letter-spacing:1px;color:var(--muted)}
.calm.on .callab{color:var(--ink);font-weight:700}
@media(max-width:640px){.calgrid{gap:4px}.calbar{height:30px;border-radius:6px;border-width:2px}
  .callab{font-size:.58rem;letter-spacing:.3px}}
.calread{margin-top:16px;max-width:820px;background:#fff;border:1px solid #ddeeea;border-radius:14px;padding:18px 24px;
  display:flex;align-items:center;gap:14px 40px;flex-wrap:wrap}
.cr-id{display:flex;align-items:center;gap:12px}
.cr-swatch{width:14px;height:14px;border-radius:4px;display:inline-block;flex:none}
.cr-month{font-family:var(--serif);font-size:1.3rem;font-weight:600;color:var(--ink)}
.cr-chip{font-size:.85rem;font-weight:600;color:#0e7569;background:#e2f3f0;padding:4px 12px;border-radius:999px}
.cr-note{flex:1 1 240px}
.cr-note .cr-val{font-weight:400;color:var(--ink-soft);font-size:.95rem}
.cr-val{font-size:1rem;font-weight:600;color:var(--ink)}
.callegend{margin-top:14px;max-width:820px;display:flex;align-items:center;gap:10px 22px;flex-wrap:wrap}
.lg{display:flex;align-items:center;gap:7px;font-size:.85rem;color:var(--ink-soft)}
.lg i{width:13px;height:13px;border-radius:4px;display:inline-block;border:1px solid rgba(18,51,47,.08)}
.calmore{margin-top:10px}
.calmore summary{list-style:none;cursor:pointer;text-align:right;font-size:.9rem;font-weight:600;color:var(--accent-deep)}
.calmore summary::-webkit-details-marker{display:none}
.calmore summary:hover{color:var(--cta-deep);text-decoration:underline}
.calmore[open] summary{margin-bottom:6px}
/* fact cards */
.facts{margin-top:36px;display:grid;grid-template-columns:repeat(5,1fr);gap:16px}
.fact{background:#fff;border-radius:16px;padding:20px 22px;box-shadow:0 6px 22px rgba(18,51,47,.05);
  transition:transform .25s ease,box-shadow .25s ease;min-width:0}
.fact:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(18,51,47,.09)}
.fact .lbl{display:block;font-size:.72rem;letter-spacing:1.4px;margin-bottom:10px}
.fact b{display:block;font-size:1.1rem;font-weight:600;color:var(--ink);line-height:1.4}
.fact small{display:block;font-size:.83rem;color:var(--muted);margin-top:6px;line-height:1.5}
@media(max-width:980px){.facts{grid-template-columns:repeat(2,1fr)}}
/* pack / stay cards */
.dest2 .packbox,.dest2 .staybox{background:#fff;border:none;border-radius:18px;padding:26px 32px;
  margin:22px 0 0;box-shadow:0 8px 30px rgba(18,51,47,.06);display:flex;align-items:center;
  justify-content:space-between;gap:14px 24px;flex-wrap:wrap}
.dest2 .pack-head,.dest2 .stay-head{flex-basis:100%;font-family:var(--mono);font-size:.75rem;
  letter-spacing:2px;text-transform:uppercase;color:var(--accent-deep);margin:0 0 2px}
.dest2 .pack-body{margin:0;font-size:1.13rem;line-height:1.6;color:var(--ink-soft);flex:1 1 320px}
.dest2 .pack-ctas{display:flex;gap:10px;flex-wrap:wrap}
.dest2 .pack-cta{display:inline-block;background:var(--cta-deep);color:#fff;font-size:.98rem;font-weight:600;
  padding:14px 26px;border-radius:12px;text-decoration:none;transition:background .2s ease,transform .2s ease}
.dest2 .pack-cta:hover{background:var(--cta);transform:translateY(-2px)}
.dest2 .pack-cta.ghost{background:#fff;color:#0e7569;border:1.5px solid #bfe0da}
.dest2 .pack-cta.ghost:hover{background:#0e7569;color:#fff;border-color:#0e7569}
/* sea life tags */
.sealife{margin-top:34px}
.sealife .sl-h{font-size:1rem;color:var(--muted);margin-bottom:12px}
.tags{display:flex;gap:10px;flex-wrap:wrap}
.tag{font-family:var(--mono);font-size:.85rem;color:#0e7569;background:#fff;border:1.5px solid #bfe0da;
  padding:9px 18px;border-radius:999px;text-decoration:none;transition:background .2s ease,color .2s ease,border-color .2s ease}
a.tag:hover{background:#0e7569;color:#fff;border-color:#0e7569;text-decoration:none}
span.tag{color:var(--ink-soft);border-color:#d3e5e2}
/* dive sites */
.sites2{margin-top:44px}
.sites2 .sec-h{margin:0 0 6px}
.sites2 .sec-h em{font-style:normal;color:var(--accent-deep)}
.sites2 .sub{font-size:1rem;color:var(--muted);margin:0 0 20px}
.sitewrap{overflow-x:auto;border-radius:18px;box-shadow:0 8px 30px rgba(18,51,47,.06)}
.sitetable{min-width:840px;background:#fff}
.srow{display:grid;grid-template-columns:170px 130px 92px 158px 1fr;gap:20px;padding:20px 28px;
  border-bottom:1px solid #eef5f3;align-items:start;transition:background .2s ease}
.srow:hover{background:#f7fbfa}
.srow:last-child{border-bottom:none}
.srow.head{padding:16px 28px;background:#f4faf9;border-bottom:1px solid #e3f0ed}
.srow.head:hover{background:#f4faf9}
.srow.head .lbl{font-size:.72rem;letter-spacing:1.4px}
.s-name{font-size:1.05rem;font-weight:700;color:var(--ink)}
.s-type span{font-family:var(--mono);font-size:.8rem;color:var(--ink-soft);background:#eef5f3;
  border:1px solid #ddeae6;padding:4px 10px;border-radius:8px;display:inline-block}
.s-depth{font-family:var(--mono);font-size:.9rem;color:#0e7569;white-space:nowrap}
.s-level{display:flex;align-items:center;gap:8px}
.dots{display:flex;gap:3px;flex:none}
.dots i{width:9px;height:9px;border-radius:50%;background:#d5e6e2;display:inline-block}
.dots i.f{background:#0e7569}
.s-level em{font-style:normal;font-size:.92rem;color:var(--ink-soft)}
.s-why{font-size:.95rem;line-height:1.65;color:var(--ink-soft)}
/* verification + permalink */
.endnote{margin:30px 0 0;display:flex;flex-direction:column;gap:12px}
.verline{font-size:.97rem;color:var(--muted)}
.permalink{font-size:1.03rem;font-weight:600;color:var(--accent-deep);text-decoration:none}
.permalink:hover{color:var(--cta-deep);text-decoration:underline}
.dest2 .related{margin-top:36px}
@media(max-width:640px){.dest2 .wrap{padding:16px 14px 48px}
  .dest2 .prof-essay{padding:22px 20px}
  .dest2 .packbox,.dest2 .staybox{padding:20px 18px}
  .srow{padding:16px 18px;gap:14px}.srow.head{padding:12px 18px}}
@media(prefers-reduced-motion:reduce){.dest2 .prof-essay,.fact,.calbar,.dest2 .pack-cta,.tag,.srow{transition:none}}
"""

# Shared scroll-in reveals (progressive enhancement): elements carrying .rev
# fade/slide in on first intersection. Elements already in view are never
# hidden (no flash), and prefers-reduced-motion switches the whole thing off.
REVEAL_JS = """
(function(){
  document.documentElement.classList.add('js');
  if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  if(!('IntersectionObserver' in window))return;
  var els=[].slice.call(document.querySelectorAll('.rev'));
  if(!els.length)return;
  var io=new IntersectionObserver(function(es){
    es.forEach(function(e){
      if(!e.isIntersecting)return;
      var t=e.target;
      t.style.opacity='1';t.style.transform='none';
      setTimeout(function(){t.style.opacity='';t.style.transform='';t.style.transition=''},760);
      io.unobserve(t);
    });
  },{threshold:.08});
  els.forEach(function(t){
    if(t.getBoundingClientRect().top<window.innerHeight*.9)return; // already in view — never hide
    t.style.opacity='0';t.style.transform='translateY(26px)';
    t.style.transition='opacity .7s ease, transform .7s cubic-bezier(.22,1,.36,1)';
    io.observe(t);
  });
})();
"""

# Progressive enhancement: content is fully visible without JS (the readout is
# server-rendered on January); JS re-points it at the visitor's current month,
# wires hover/click/focus, and adds the calendar entrance animation (skipped
# under prefers-reduced-motion). Scroll reveals come from the shared REVEAL_JS.
DEST_JS = """
(function(){
  var C={Peak:'#0e7569',Good:'#5cb8ab',Shoulder:'#dfa826',Low:'#cfe4e0',Closed:'#b9c6c9'};
  var bars=[].slice.call(document.querySelectorAll('.calm'));
  function el(id){return document.getElementById(id)}
  function set(i){
    bars.forEach(function(b,j){b.classList.toggle('on',j===i);b.setAttribute('aria-pressed',j===i?'true':'false')});
    var d=bars[i].dataset;
    el('crSwatch').style.background=C[d.rating]||'#b9c6c9';
    el('crMonth').textContent=d.month;
    el('crChip').textContent=d.rating;
    el('crTemp').textContent=d.temp;
    el('crViz').textContent=d.viz;
    el('crNote').textContent=d.note;
  }
  bars.forEach(function(b,i){
    b.addEventListener('mouseenter',function(){set(i)});
    b.addEventListener('click',function(){set(i)});
    b.addEventListener('focus',function(){set(i)});
  });
  if(bars.length===12)set(new Date().getMonth());
  if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  if(!('IntersectionObserver' in window))return;
  var cbs=[].slice.call(document.querySelectorAll('.calbar'));
  if(cbs.length&&cbs[0].getBoundingClientRect().top>window.innerHeight*.95){
    cbs.forEach(function(b){
      b.style.transformOrigin='bottom';b.style.transform='scaleY(0.15)';b.style.opacity='0';
      b.style.transition='opacity .45s ease, transform .55s cubic-bezier(.22,1,.36,1)';
    });
    var bio=new IntersectionObserver(function(es){
      es.forEach(function(e){
        if(!e.isIntersecting)return;
        cbs.forEach(function(b,i){
          setTimeout(function(){b.style.transform='scaleY(1)';b.style.opacity='1'},i*55);
          setTimeout(function(){b.style.transform='';b.style.opacity='';b.style.transition=''},i*55+620);
        });
        bio.disconnect();
      });
    },{threshold:.3});
    bio.observe(cbs[0]);
  }
})();
"""

FONTS_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
              '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
              '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,'
              '500;9..144,600;9..144,700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:'
              'wght@400;500;700&display=swap">')

FLUKE = ('<svg width="34" height="22" viewBox="0 0 120 70" aria-hidden="true"><path d="M60 62 C56 51 53 46 46 41 '
         'C35 32 18 24 6 22 C16 28 33 37 48 41 C53 42 56 43 60 47 C64 43 67 42 72 41 C87 37 104 28 114 22 '
         'C102 24 85 32 74 41 C67 46 64 51 60 62 Z" fill="#2fe0d6"/></svg>')

def esc(s): return html.escape(str(s or ""), quote=True)

def meta_desc(s, limit=160):
    """SERP-length description (~155-160 chars): whole sentences when one ends
    inside the budget, otherwise a word-boundary cut with an ellipsis — never
    a mid-word fragment. The same string feeds <meta name=description>,
    og:description and JSON-LD, so truncate once, here."""
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    last = None
    for m in re.finditer(r"[.!?](?=\s)", cut):
        last = m
    if last and last.end() >= limit * 0.55:   # keep useful length — no one-clause stubs
        return cut[:last.end()]
    return cut.rsplit(" ", 1)[0].rstrip(",;:·—&- ") + "…"

def topbar(prefix="../"):
    return (f'<div class="topbar"><a href="{prefix}index.html">'+FLUKE+
            '<span class="name">Dive<b>SZN</b></span></a></div>')

def footer_html(prefix="../"):
    # Nav labels mirror the app footer in index.html — keep the two in sync.
    return ('<footer>'
            '<div class="foot-mark">Dive<b>SZN</b></div>'
            '<div class="foot-tag">Your diving buddy</div>'
            '<div class="foot-nav">'
            f'<a href="{prefix}index.html">Dive planner</a>'
            f'<a href="{prefix}destinations/index.html">Destination guides</a>'
            f'<a href="{prefix}months/index.html">Best by month</a>'
            f'<a href="{prefix}marine-life/index.html">Marine life</a>'
            f'<a href="{prefix}gear/index.html">Gear guides</a>'
            f'<a href="{prefix}how-we-score.html">How we score</a>'
            f'<a href="{prefix}about.html">About</a>'
            f'<a href="{prefix}privacy.html">Privacy</a></div>'
            '<div class="disclosure">Seasonal data is compiled from dive operators, liveaboard calendars and ocean '
            'sea-temperature sources; water temperatures are typical monthly ranges (±1°C) and marine-life timing '
            'shifts year to year with plankton and lunar cycles. Always confirm current conditions with a local '
            'dive centre before travelling.</div>'
            '<div class="disclosure"><b>Affiliate disclosure:</b> DiveSZN may earn a commission when you buy gear '
            'or book a trip through our links, at no extra cost to you. Gear prices are indicative as of our '
            'research date — the retailer shows the live price. We link only to authorised retailers and trusted '
            'operators, and commissions never influence our rankings.</div>'
            '</footer>')

def photo_hero(kicker, title, sub="", img="", credit="", pills="", pos=""):
    """Shared photo hero (hub variant of the destination hero2): photo with
    scrim, mono kicker, serif title, optional sub-line/pills, tooltip-only
    photo credit. Degrades gracefully — onerror hides only the <img>, the
    gradient + scrim + title always render. pos = optional object-position
    focal point (e.g. "50% 22%") so cover crops keep the subject in frame."""
    credit_s = (f'<span class="credit2" title="{esc(credit)}">&#9432;</span>'
                if img and credit else "")
    pos_s = f' style="object-position:{esc(pos)}"' if pos else ""
    img_s = (f'<img src="{esc(img)}" alt=""{pos_s} onerror="this.style.display=\'none\'">'
             if img else "")
    # Owner ruling (2026-07): no sentences on photos — the sub param is
    # accepted for compatibility but never rendered on the hero.
    pills_s = f'<div class="hero2-pills">{pills}</div>' if pills else ""
    return (f'<header class="hero2 hero2-hub rev">{img_s}<div class="hero2-scrim"></div>{credit_s}'
            f'<div class="hero2-bar"><div><div class="hero2-kicker">{esc(kicker)}</div>'
            f'<h1>{esc(title)}</h1></div>{pills_s}</div></header>')

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
    return (f'<div class="packbox rev"><div class="pack-head">What to pack here</div>'
            f'<p class="pack-body">{body}</p><div class="pack-ctas">{ctas}</div></div>')


LIVEABOARD_SLUG = {
 "Sharm El Sheikh": "egypt/red-sea", "Hurghada": "egypt/red-sea",
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
    return (f'<div class="staybox rev"><div class="stay-head">Where to stay</div>'
            f'<p class="pack-body">{body}</p><div class="pack-ctas">{ctas}</div></div>')


def essays_block(d):
    """Editorial 'what to expect / what you'll encounter' cards (same as the SPA profile)."""
    cards = ""
    if d.get("underwater"):
        cards += f'<div class="prof-essay rev"><h2>What to expect down there</h2><p>{esc(d["underwater"])}</p></div>'
    if d.get("encounters"):
        cards += f'<div class="prof-essay rev"><h2>What you&#8217;ll encounter</h2><p>{esc(d["encounters"])}</p></div>'
    return f'<div class="prof-essays">{cards}</div>' if cards else ""


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

# ------------------------------------------------- destination page helpers
def _cap(s):
    s = (s or "").strip()
    return s[:1].upper() + s[1:] if s else s

def _trunc(s, n=90):
    """Clean word-boundary truncation — shortens real data, never invents."""
    s = (s or "").strip()
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(",;:· ")
    return cut + "…"

def _fact_split(s, maxlen=24):
    """Short fact-card value + sub-line detail from a free-text data field."""
    s = (s or "").strip().rstrip(".")
    head, tail = s, ""
    m = re.search(r"[(,;]", s)
    if m:
        head = s[:m.start()].strip()
        tail = s[m.start() + 1:].strip().rstrip(")").strip()
        if m.group(0) == "(" and ")" in tail:
            tail = tail.replace(")", "", 1)  # drop the paren we split open
    if len(head) > maxlen:
        cut = head[:maxlen].rsplit(" ", 1)[0]
        rest = head[len(cut):].strip()
        tail = (rest + (" — " + tail if tail else "")).strip()
        head = cut
    return _cap(head), _cap(_trunc(tail, 88))

def _wetsuit_fact(w):
    """'5mm' style short value; the full wetsuit note becomes the sub-line."""
    w = (w or "").strip()
    m = re.search(r"\d\s*(?:-|–|to )?\s*\d?\s*mm", w)
    dry = w.lower().find("drysuit")
    if dry != -1 and (not m or dry < m.start()):
        head = "Drysuit"
    elif m:
        head = re.sub(r"\s+", "", m.group(0))
    else:
        return _fact_split(w)
    tail = _trunc(w, 88)
    if tail.lower() == head.lower():
        tail = ""
    return head, _cap(tail)

def _level_dots(level):
    l = (level or "intermediate").lower()
    n = 3 if ("tec" in l or "advanced" in l) else (2 if "intermediate" in l else 1)
    dots = "".join('<i class="f"></i>' if k <= n else "<i></i>" for k in (1, 2, 3))
    return f'<span class="s-level"><span class="dots">{dots}</span><em>{esc(level or "intermediate")}</em></span>'

def _species_tag(s):
    """Signature-species chip; links to the marine-life guide when one exists."""
    sl = s.lower()
    for exp in EXPERIENCES:
        if any(k.lower() in sl for k in exp.get("keywords", [])):
            if os.path.exists(os.path.join(ROOT, "marine-life", exp["slug"] + ".html")):
                return f'<a class="tag" href="../marine-life/{exp["slug"]}.html">{esc(s)}</a>'
            break
    return f'<span class="tag">{esc(s)}</span>'

def _pretty_months(t):
    return re.sub(r"([A-Z][a-z]{2})-([A-Z][a-z]{2})", r"\1–\2", t)

def _month_note(mm):
    return _cap(_trunc(mm.get("marine_life") or mm.get("conditions") or "", 90))

def page(d, top_month=None):
    slug = d["slug"]; url = BASE + "destinations/" + slug + ".html"
    peak = [m for m in MONTHS if d["monthly"][m]["rating"] == "Peak"]
    closed = [m for m in MONTHS if d["monthly"][m]["rating"] == "Closed"]
    desc = meta_desc(f'{d["name"]} diving season guide: best months {d["best_months"]}. Month-by-month water temperature, '
                     f'visibility, currents ({d["current_strength"].lower()}) and marine life. {d["highlights"]}')
    img = d.get("image") or ""

    # ---- hero (photo with scrim + fact pills; plain gradient when no photo)
    country, region = d["country"], d["region"]
    loc = region if country.lower() in region.lower() else f"{region} · {country}"
    credit = (f'<span class="credit2" title="{esc(d.get("image_credit"))}">&#9432;</span>'
              if img and d.get("image_credit") else "")
    # Owner ruling (2026-07): destination heroes carry the name only —
    # no kicker line, no sentences on the photo.
    if img:
        hero = (f'<header class="hero2 rev">'
                f'<img src="{esc(img)}" alt="{esc(d["name"])}" onerror="this.style.display=\'none\'">'
                f'<div class="hero2-scrim"></div>{credit}'
                f'<div class="hero2-bar"><div>'
                f'<h1>{esc(d["name"])}</h1></div></div>'
                f'</header>')
    else:
        hero = (f'<header class="hero plain" style="border-radius:20px">'
                f'<h1>{esc(d["name"])}</h1></header>')

    # ---- season calendar: 12 tonal bars + interactive readout
    cells = ""
    for i, m in enumerate(MONTHS):
        mm = d["monthly"][m]; rating = mm["rating"]
        t = d["monthly_temp_c"].get(m)
        temp = f"{t}°C" if t is not None else "—"
        viz = f'{mm.get("visibility_m")} m' if mm.get("visibility_m") else "—"
        note = _month_note(mm)
        aria = f"{MONTH_FULL[m]}: {rating}. Water {temp}, visibility {viz}"
        cells += (f'<button type="button" class="calm{" on" if i == 0 else ""}" '
                  f'data-month="{MONTH_FULL[m]}" data-rating="{rating}" data-temp="{esc(temp)}" '
                  f'data-viz="{esc(viz)}" data-note="{esc(note)}" '
                  f'aria-pressed="{"true" if i == 0 else "false"}" aria-label="{esc(aria)}">'
                  f'<span class="calbar" style="background:{TONAL[rating]}"></span>'
                  f'<span class="callab">{m}</span></button>')
    j = d["monthly"]["Jan"]; jt = d["monthly_temp_c"].get("Jan")
    jtemp = f"{jt}°C" if jt is not None else "—"
    jviz = f'{j.get("visibility_m")} m' if j.get("visibility_m") else "—"
    readout = (f'<div class="calread">'
               f'<div class="cr-id"><span class="cr-swatch" id="crSwatch" style="background:{TONAL[j["rating"]]}"></span>'
               f'<span class="cr-month" id="crMonth">January</span>'
               f'<span class="cr-chip" id="crChip">{j["rating"]}</span></div>'
               f'<div class="pair"><span class="lbl">Water</span><span class="cr-val" id="crTemp">{jtemp}</span></div>'
               f'<div class="pair"><span class="lbl">Visibility</span><span class="cr-val" id="crViz">{jviz}</span></div>'
               f'<div class="pair cr-note"><span class="lbl">Highlights</span><span class="cr-val" id="crNote">{esc(_month_note(j))}</span></div>'
               f'</div>')
    legend = "".join(f'<span class="lg"><i style="background:{TONAL[r]}"></i>{r}</span>'
                     for r in ("Peak", "Good", "Shoulder", "Low", "Closed"))
    rows = ""
    for m in MONTHS:
        mm = d["monthly"][m]
        t = d["monthly_temp_c"].get(m)
        rows += (f'<tr><td><b>{m}</b></td>'
                 f'<td><span class="badge" style="background:{TONAL[mm["rating"]]};color:{TONAL_TEXT[mm["rating"]]}">{mm["rating"]}</span></td>'
                 f'<td class="num">{t if t is not None else "—"}°C</td>'
                 f'<td class="num">{mm.get("visibility_m") or "—"}m</td>'
                 f'<td>{esc(mm["marine_life"])}</td><td>{esc(mm["conditions"])}</td></tr>')
    detail = ('<details class="calmore"><summary>+ Full month-by-month detail</summary>'
              '<div style="overflow:auto;background:#fff;border:1px solid #ddeeea;border-radius:14px;padding:6px 18px 14px"><table>'
              '<thead><tr><th>Month</th><th>Rating</th><th>Water</th><th>Viz</th><th>Sea life expected</th><th>Conditions</th></tr></thead>'
              f'<tbody>{rows}</tbody></table></div></details>')
    calendar = (f'<section class="cal rev"><h2 class="sec-h">When should you dive {esc(d["name"])}?</h2>'
                f'<div class="calgrid">{cells}</div>{readout}'
                f'<div class="callegend">{legend}</div>{detail}</section>')

    # ---- best-months strip (mono label / value pairs)
    pairs = [f'<span class="pair"><span class="lbl">Best months</span><span class="val">{esc(", ".join(peak) or "—")}</span></span>']
    if top_month:
        pairs.append(f'<span class="pair"><span class="lbl">Top month</span><span class="val">{esc(top_month[0])} (score {top_month[1]})</span></span>')
    pairs.append(f'<span class="pair"><span class="lbl">Window</span><span class="val">{esc(_pretty_months(d["best_months"]))}</span></span>')
    if closed:
        pairs.append(f'<span class="pair"><span class="lbl">Closed</span><span class="val">{esc(", ".join(closed))}</span></span>')
    best_strip = f'<div class="best2 rev">{"".join(pairs)}</div>'

    # ---- fact cards (short value + sub-line detail, all from data)
    temps = [t for t in d["monthly_temp_c"].values() if t is not None]
    tmin, tmax = min(temps), max(temps)
    wv, ws = _fact_split(d["water_type"])
    if not ws:
        ws = f"{tmin}–{tmax}°C across the year" if tmin != tmax else f"around {tmin}°C year-round"
    dv, ds = _fact_split(d["difficulty"])
    av, asub = _fact_split(d["access"])
    suitv, suits = _wetsuit_fact(d["wetsuit"])
    curv = _cap(d["current_strength"])
    curs = _cap(_trunc(d.get("current_note") or d.get("currents") or "", 88))
    facts = "".join(
        f'<div class="fact rev"><span class="lbl">{lbl}</span><b>{esc(v)}</b>'
        + (f'<small>{esc(s)}</small>' if s else "") + "</div>"
        for lbl, v, s in (("Water type", wv, ws), ("Difficulty", dv, ds), ("Access", av, asub),
                          ("Wetsuit", suitv, suits), ("Current strength", curv, curs)))

    # ---- signature sea life (links into marine-life guides where they exist)
    species = "".join(_species_tag(s) for s in d.get("signature_species", []))
    sealife = (f'<div class="sealife rev"><div class="sl-h">Signature sea life</div>'
               f'<div class="tags">{species}</div></div>') if species else ""

    # ---- dive sites grid
    sites = d.get("dive_sites") or []
    sites_block = ""
    if sites:
        head = ('<div class="srow head">'
                + "".join(f'<span class="lbl">{h}</span>' for h in
                          ("Site", "Type", "Depth", "Level", "Why it&#8217;s known"))
                + "</div>")
        srows = "".join(
            f'<div class="srow rev"><span class="s-name">{esc(s.get("name"))}</span>'
            f'<span class="s-type"><span>{esc(_cap(s.get("type") or "Reef"))}</span></span>'
            f'<span class="s-depth">{esc(s.get("depth") or "—")}</span>'
            f'{_level_dots(s.get("level"))}'
            f'<span class="s-why">{esc(s.get("blurb"))}</span></div>'
            for s in sites)
        sites_block = (f'<section class="sites2 rev"><h2 class="sec-h">Recognised dive sites <em>({len(sites)})</em></h2>'
                       f'<p class="sub">Depths are typical published ranges — always confirm with your operator.</p>'
                       f'<div class="sitewrap"><div class="sitetable">{head}{srows}</div></div></section>')

    # ---- structured data (unchanged)
    ld = {
        "@type": "TouristDestination",
        "name": d["name"] + " scuba diving", "description": desc, "url": url,
        "touristType": "Scuba divers",
    }
    if d.get("coordinates", {}).get("lat") is not None:
        ld["geo"] = {"@type": "GeoCoordinates", "latitude": d["coordinates"]["lat"], "longitude": d["coordinates"]["lng"]}
    if img: ld["image"] = img
    if sites:
        ld["containsPlace"] = [{"@type": "TouristAttraction", "name": s.get("name")} for s in sites]
    og_img = f'<meta property="og:image" content="{esc(img)}">' if img else ""
    verline = (f'<div class="verline">&#10003; Data verified {esc(d.get("last_verified"))}'
               f' · source confidence: {esc(d.get("data_confidence"))}</div>' if d.get("last_verified") else "")
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
{FONTS_LINK}
<style>{CSS}{V2_CSS}{DEST_CSS}</style>
</head>
<body class="v2 dest2">
{topbar()}
<main class="wrap">
  <p class="dback"><a href="../index.html#destinations" onclick="if(document.referrer.indexOf(location.host)>-1){{history.back();return false;}}">&larr; Back to destinations</a></p>
  {hero}
  {f'<p class="lead2 rev">{esc(d["description"])}</p>' if d.get("description") else ""}
  <p class="lead2sub rev">{esc(dest_intro(d))}</p>
  {essays_block(d)}
  {best_strip}
  {calendar}
  <div class="facts">{facts}</div>
  {pack_box(d)}
  {stay_box(d)}
  {sealife}
  {sites_block}
  <div class="endnote rev">
    {verline}
    <a class="permalink" href="../index.html">Plan a dive trip here — open the DiveSZN planner &rarr;</a>
  </div>
  <div class="related rev">{related_block(d)}</div>
</main>
{footer_html()}
<script>{DEST_JS}{REVEAL_JS}</script>
</body></html>"""

def index_page(dests):
    url = BASE + "destinations/index.html"
    items = ""
    ordered = sorted(dests, key=lambda x: x["name"].lower())
    for d in ordered:
        peak = ", ".join(m for m in MONTHS if d["monthly"][m]["rating"] == "Peak") or "—"
        items += (f'<li><a href="{d["slug"]}.html"><b>{esc(d["name"])}</b>'
                  f'<small>{esc(d["country"])} · peak: {esc(peak)}</small></a></li>')
    desc = "Season guides for the world's scuba diving destinations: best months, water temperature, visibility, currents and marine life."
    ld = graph_ld({"@type": "CollectionPage", "name": "Dive destination season guides",
                   "description": desc, "url": url,
                   "mainEntity": {"@type": "ItemList", "numberOfItems": len(ordered),
                                  "itemListElement": [
                                      {"@type": "ListItem", "position": i + 1, "name": d["name"],
                                       "url": BASE + "destinations/" + d["slug"] + ".html"}
                                      for i, d in enumerate(ordered)]}},
                  crumbs([("Home", BASE), ("Destinations", url)]))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>All Dive Destinations — Season Guides | DiveSZN</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{FONTS_LINK}
<style>{CSS}{V2_CSS}</style>
</head>
<body class="v2">
{topbar()}
<main class="wrap">
  <p class="kick">Destination directory</p>
  <h1 style="margin-top:0">Dive destination season guides</h1>
  <p class="meta">{desc}</p>
  <ul class="dirlist rev">{items}</ul>
  <a class="cta" href="../index.html">Open the interactive dive planner &rarr;</a>
</main>
{footer_html()}
<script>{REVEAL_JS}</script>
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
    photo = (f'<figure class="gitem-photo"><img id="gimg" src="{prefix}{esc(hero_path)}" '
             f'alt="{esc(item["name"])}" onerror="this.style.display=\'none\'"></figure>' if hero_path else "")
    stage_open = '<div class="gitem-stage">' if hero_path else ""
    stage_close = "</div>" if hero_path else ""
    offers = order_offers(item.get("options"))
    lo = min((o["price_usd"] for o in item.get("options") or []), default=None)
    btns = "".join(
        f'<a class="pack-cta{"" if i == 0 else " ghost"}" href="{esc(o["url"])}" target="_blank" '
        f'rel="noopener sponsored">{esc(o["store"])} · {fmtp(o["price_usd"])}</a>'
        for i, o in enumerate(offers[:3]))
    banner = (f'<div class="gitem-banner">'
              f'<div class="gitem-id"><b>{esc(item["name"])}</b>'
              f'<span class="gitem-price">{f"from <b>{fmtp(lo)}</b>" if lo is not None else ""}</span>'
              f'<small>indicative — the retailer shows the live price</small></div>'
              f'<div class="pack-ctas">{btns}</div></div>')
    # the banner sits INSIDE the photo card (owner spec: on the photo, bottom
    # side, with the studio background behind and below it — never a separate
    # card under the photo); with no photo it degrades to the plain banner
    photo_with_banner = (photo.replace("</figure>", banner + "</figure>")
                         if photo else banner)
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
    verdict = ""
    if item.get("pros") or item.get("cons"):
        pros_lis = "".join(f"<li>{esc(p)}</li>" for p in item.get("pros") or [])
        cons_lis = "".join(f"<li>{esc(c)}</li>" for c in item.get("cons") or [])
        verdict = ('<div class="gverdict">'
                   + (f'<div class="gv-pro"><h3>Where it wins</h3><ul>{pros_lis}</ul></div>' if pros_lis else "")
                   + (f'<div class="gv-con"><h3>Where it falls short</h3><ul>{cons_lis}</ul></div>' if cons_lis else "")
                   + '</div>')
    inner = (f'<p class="meta gitem-kicker">{kicker}</p>'
             f'{stage_open}{photo_with_banner}{stage_close}'
             f'<h2>What makes it good?</h2>'
             f'<p class="greview" style="max-width:80ch">{esc(review)}</p>'
             f'{verdict}'
             f'{specs}{related}'
             f'<p class="meta"><a href="{cat_slug}.html">&larr; Back to {esc(cat_title)}</a></p>')
    desc = meta_desc(item.get("blurb") or review)
    ld = graph_ld({"@type": "WebPage", "name": item["name"], "url": url, "description": desc},
                  crumbs([("Home", BASE), ("Gear guides", BASE + "gear/index.html"),
                          (cat_title, BASE + "gear/" + cat_slug + ".html"), (item["name"], url)]),
                  product_ld(item))
    return content_shell(f'{item["name"]} Review | DiveSZN', desc, url, prefix,
                         item.get("blurb") or "", inner, ld)


def _cat_items(cat):
    items = list(cat.get("items") or [])
    for g in cat.get("thickness_groups") or []:
        items += g.get("items") or []
    return items

def gear_entry(item, prefix):
    img = item.get("image") or ""
    imgtag = (f'<img src="{prefix}{esc(img)}" alt="{esc(item["name"])}" loading="lazy" '
              f'onerror="this.style.display=\'none\'">' if img else "")
    specs = ""
    if item.get("specs"):
        specs = ('<dl class="gspecs">'
                 + "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in item["specs"].items())
                 + "</dl>")
    slug = gear_slug(item["name"])
    return (f'<div class="gentry rev"><div class="gphoto"><a href="{slug}.html">{imgtag}</a></div>'
            f'<div><h3>{item.get("rank", "")}. <a class="gitem-link" href="{slug}.html">{esc(item["name"])}</a></h3>'
            f'<p class="greview">{esc(item.get("review") or item.get("blurb"))}</p>{specs}{buy_box(item)}'
            f'<p class="meta" style="margin-top:8px"><a href="{slug}.html">Full page: photos, specs &amp; prices &rarr;</a></p></div></div>')

def content_shell(title, desc, url, prefix, hero_sub, inner, ld=None, hero_html=None,
                  extra_css="", extra_js=""):
    """Shared page shell. Default: plain gradient hero band with the page h1.
    Pass hero_html (built with photo_hero) to get the photo-hero treatment
    inside the content column instead — the plain hero is then skipped.
    extra_css/extra_js let a page family (marine encounter files) append its
    scoped styles/enhancement without growing every other page."""
    ldtag = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    h1 = esc(title.split(" | ")[0].split(" — ")[0])
    if hero_html:
        body = f'<main class="wrap">{hero_html}{inner}</main>'
    else:
        body = (f'<header class="hero plain"><h1>{h1}</h1>'
                f'{f"<p>{esc(hero_sub)}</p>" if hero_sub else ""}</header>'
                f'<main class="wrap">{inner}</main>')
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{esc(url)}">
{ldtag}
{FONTS_LINK}
<style>{CSS}{V2_CSS}{extra_css}</style>
</head>
<body class="v2">
{topbar(prefix)}
{body}
{footer_html(prefix)}
<script>{REVEAL_JS}{extra_js}</script>
</body></html>"""

def gear_page(cat, prefix="../"):
    slug = gear_slug(cat["category"])
    title = f'{cat.get("title") or ("Top " + cat["category"])} | DiveSZN'
    url = BASE + "gear/" + slug + ".html"
    intro = cat.get("article_intro") or ""
    parts = ['<p class="kick">Gear buyer&#8217;s guide</p>']
    if intro:
        parts.append(f'<p class="greview" style="max-width:80ch">{esc(intro)}</p>')
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
    desc = meta_desc(intro or f'The best {cat["category"].lower()} for scuba diving in 2026.')
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
        thumb = (f'<img src="{prefix}{esc(img)}" alt="" loading="lazy" '
                 f'onerror="this.style.display=\'none\'">' if img else "")
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
                th = (f'<span class="gbthumb"><img src="{prefix}{esc(img)}" alt="" loading="lazy" '
                      f'onerror="this.style.display=\'none\'"></span>'
                      if img else '<span class="gbthumb"></span>')
                frm = f"from {fmtp(lo)}" if lo is not None else ""
                brows += (f'<a class="gbrow" href="{gear_slug(it["name"])}.html">{th}'
                          f'<span><b>{esc(it["name"])}</b><small>{frm}</small></span></a>')
            cols += f'<div class="gbcol"><b class="gbrand">{esc(b)}</b>{brows}</div>'
        gslug = gear_slug(cat["category"])
        bsec += (f'<section class="dregion rev"><h3><span>{esc(cat["category"])}</span>'
                 f'<span class="bcount">{n} product{"" if n == 1 else "s"} · '
                 f'<a href="{gslug}.html" style="color:var(--accent)">guide &rarr;</a></span></h3>'
                 f'<div class="gbgrid">{cols}</div></section>')
    desc = "DiveSZN scuba gear — every product under its brand, plus ranked buyer's guides for masks, fins, regulators, BCDs, dive computers and wetsuits."
    inner = (f'<p class="kick">The gear hub</p>'
             f'<p class="greview" style="max-width:80ch">{esc(gear.get("intro") or "")}</p>'
             f'{bsec}'
             f'<h2 style="margin-top:40px">The buyer&#8217;s guides (articles)</h2><ul class="artlist rev">{rows}</ul>'
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

def privacy_page():
    """Privacy policy through the shared v2 shell (legal copy preserved
    verbatim) — generated so it can never drift from the design system again."""
    url = BASE + "privacy.html"
    inner = """
<div class="legal">
<div class="updated">Last updated: 6 July 2026</div>

<div class="lead">DiveSZN has no accounts, no sign-up and no forms — we don't ask you for
  personal information and we never sell any. The only data involved comes from our host's
  standard server logs and from cookies set by the retailers and affiliate networks we link
  to. This page explains that in full.</div>

<p>DiveSZN ("we", "us", "the site") operates this website. This policy explains what
  information is collected when you visit, how it is used, and the choices you have.</p>

<h2>1. Information we collect</h2>
<p><strong>Information you give us:</strong> None. There is no registration, login, newsletter
  or contact form on DiveSZN. If you choose to email us, we receive whatever you include in
  that message.</p>
<p><strong>Information collected automatically:</strong> The site is hosted on GitHub Pages.
  Like all web hosts, GitHub's servers automatically log basic technical data for each
  request — such as your IP address, browser type, referring page and the pages you view.
  This is handled by GitHub under
  <a href="https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener">its own privacy statement</a>;
  we do not maintain a database of it.</p>
<p><strong>Cookies:</strong> DiveSZN itself does not set advertising or analytics cookies.
  Cookies may be set by the third-party affiliate networks below <strong>only when you click
  an outbound "Buy" link</strong>.</p>

<h2>2. Affiliate links</h2>
<p>DiveSZN is reader-supported. Many "Buy" links are affiliate links: if you click through and
  make a purchase, we may earn a commission <strong>at no extra cost to you</strong>. To credit
  that referral, the retailer or affiliate network sets a cookie in your browser at the moment
  you click. The networks we use are:</p>
<ul>
  <li><strong>Amazon Associates</strong> — as an Amazon Associate, DiveSZN earns from qualifying purchases.</li>
  <li><strong>AvantLink</strong> (for retailers such as Scuba.com and LeisurePro)</li>
  <li><strong>Awin</strong> (for retailers such as Tradeinn, Diveinn and Scubastore)</li>
  <li><strong>eBay Partner Network</strong></li>
  <li><strong>Skimlinks</strong>, which may affiliate other outbound retailer links automatically</li>
</ul>
<p>Each network processes click and purchase data under its own privacy policy. Prices shown on
  DiveSZN are indicative; the retailer's live price and checkout are governed by that retailer.</p>

<h2>3. Advertising</h2>
<p>DiveSZN does not currently serve third-party advertising. If we introduce advertising in
  future, we will update this policy to disclose the ad provider, the use of any advertising
  cookies, how to manage them, and how consent is handled for visitors in the EU and UK.</p>

<h2>4. Analytics</h2>
<p>We do not use Google Analytics or any other third-party analytics or measurement cookies.
  If that changes, this section will be updated to name the tool, describe what it collects,
  and explain how to opt out.</p>

<h2>5. How information is used</h2>
<p>The limited data above is used only to keep the site running and secure (host logs) and to
  credit affiliate referrals (network cookies). We do not build profiles of you, run email
  marketing, or sell or rent any information to anyone.</p>

<h2>6. Legal bases (EU and UK visitors — GDPR)</h2>
<p>Where GDPR or UK GDPR applies, we rely on our <strong>legitimate interests</strong> for
  essential hosting logs and site security, and on <strong>consent</strong> for affiliate
  cookies, which are set only when you actively choose to click an outbound link.</p>

<h2>7. Your rights</h2>
<p>Depending on where you live, you may have the right to access, correct, delete or restrict
  the processing of your personal data, and to object or withdraw consent (GDPR / UK GDPR), or
  to know about and opt out of any "sale" or "sharing" of personal information (California
  CCPA / CPRA). DiveSZN does not sell personal information. Because we hold no user database,
  many requests are best directed to the relevant third party (GitHub or an affiliate network),
  but you can contact us using the details below and we will help where we can.</p>

<h2>8. International transfers</h2>
<p>Our host and the affiliate networks operate globally, so data may be processed in countries
  including the United States. Those providers maintain their own safeguards for such transfers.</p>

<h2>9. Data retention</h2>
<p>We keep no personal data of our own. Host logs and third-party cookies are retained according
  to those providers' own schedules.</p>

<h2>10. Children's privacy</h2>
<p>DiveSZN is a scuba-diving resource intended for adults and is not directed at children under
  13 (or 16 in the EU). We do not knowingly collect data from children.</p>

<h2>11. Security</h2>
<p>The site is static — no database and no user input — which removes most common data-security
  risks, and it is served over HTTPS.</p>

<h2>12. Changes to this policy</h2>
<p>We may update this policy as the site evolves, for example when advertising or analytics is
  added. The "Last updated" date at the top reflects the current version.</p>

<h2>13. Contact</h2>
<p>Questions about this policy can be sent to
  <a href="mailto:privacy@diveszn.com">privacy@diveszn.com</a>.</p>
</div>
"""
    desc = ("How DiveSZN handles data: no accounts, no forms, no analytics — only standard host "
            "logs and affiliate-network cookies set when you click a Buy link.")
    ld = {"@context": "https://schema.org", "@type": "WebPage", "name": "Privacy Policy",
          "description": desc, "url": url}
    css = ("\n.legal{max-width:780px}"
           ".legal .updated{color:var(--muted);font-size:.85rem;font-family:var(--mono);margin:2px 0 8px}"
           ".legal .lead{background:#fff;border:1px solid var(--line);border-left:3px solid var(--accent);"
           "border-radius:12px;padding:16px 18px;margin:18px 0 6px;color:#33565e;"
           "box-shadow:0 6px 22px rgba(18,51,47,.05)}"
           ".legal p,.legal ul{color:#33565e;line-height:1.65}"
           ".legal li{margin:5px 0}.legal h2{margin:30px 0 8px}.legal strong{color:var(--ink)}\n")
    return content_shell("Privacy Policy | DiveSZN", desc, url, "", None, inner, ld, extra_css=css)

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
# "The encounter files": nine numbered cover stories over the seasonal data.
# Every count/season on these pages is computed from diving-destinations.json
# (where_when + marine_pulse) — nothing invented. Fully server-rendered; the
# tiny MARINE_JS enhancement is additive only (now-ring + live in-season stat).
RATING_RANK = {"Peak": 0, "Good": 1, "Shoulder": 2, "Low": 3, "Closed": 9}
RANK_WORD = {0: "Peak", 1: "Good", 2: "Shoulder", 3: "Low"}

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

def marine_pulse(dests, keywords):
    """Per month: destinations carrying the species + best rating among them.
    Mirror of marinePulse() in index.html — keep in sync."""
    kws = [k.lower() for k in keywords]
    out = []
    for m in MONTHS:
        count, best = 0, 9
        for d in dests:
            t = (d["monthly"][m].get("marine_life") or "").lower()
            if any(k in t for k in kws):
                count += 1
                best = min(best, RATING_RANK.get(d["monthly"][m]["rating"], 9))
        out.append({"count": count, "best": best})
    return out

def _month_runs(mons):
    """['May','Jun','Jul','Sep'] -> 'MAY–JUL, SEP' (Dec–Jan runs wrap).
    Mirror of marineRuns() in index.html — keep in sync."""
    idx = sorted(MONTHS.index(m) for m in mons)
    runs = []
    for i in idx:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][1] == 11:
        runs[-1][1] = runs[0][1] + 12
        runs.pop(0)
    out = [MONTHS[a % 12].upper() if a == b else f"{MONTHS[a % 12].upper()}–{MONTHS[b % 12].upper()}"
           for a, b in runs]
    if len(out) > 6:
        out = out[:6] + [f"+{len(out) - 6}"]
    return ", ".join(out)

def _mode_word(mode):
    return re.sub(r"\s*diving\s*$", "", (mode or ""), flags=re.I).strip().split()[0].upper()

def _marine_modes(exp):
    return sorted({_mode_word(b["mode"]) for b in exp.get("beyond_scuba") or []})

def _marine_verb(short):
    words = re.findall(r"[a-z]+", (short or "").lower())
    w = words[-1] if words else ""
    return "show" if re.search(r"[^s]s$", w) else "shows"


def mini_ribbon_html(x, months):
    """12-cell tonal season ribbon for one ledger row, with the dive-computer
    readout in each in-season cell's title. data-r lets MARINE_JS add the
    current-month ring after load (additive only)."""
    cells = ""
    for m in MONTHS:
        mm = x["monthly"][m]
        if m in months:
            t = f'{m} · {mm["rating"]}'
            tc = x["monthly_temp_c"].get(m)
            if tc is not None:
                t += f" · {tc}°C"
            if mm.get("visibility_m") is not None:
                t += f' · {mm["visibility_m"]} m'
            cells += (f'<i style="background:{TONAL[mm["rating"]]}" data-r="{mm["rating"]}" '
                      f'title="{esc(t)}"></i>')
        else:
            cells += f'<i style="background:var(--line)" title="{m}"></i>'
    return f'<div class="mini-ribbon">{cells}</div>'

def marine_pulse_html(exp, pulse):
    """Static season pulse: 12 tonal cells with readout titles. Informational
    only — the scrubber is the app's job (no links, no JS required)."""
    cells = ""
    for i, m in enumerate(MONTHS):
        p = pulse[i]
        if p["count"]:
            word = RANK_WORD.get(p["best"], "")
            title = f'{m.upper()} · {word.upper()} · {p["count"]} DESTINATION{"" if p["count"] == 1 else "S"}'
            bar = f'<span class="mp-bar" style="background:{TONAL.get(word, "#b9c6c9")}"></span>'
        else:
            title = f"{m.upper()} · OUT OF SEASON"
            bar = '<span class="mp-bar" style="background:var(--line)"></span>'
        cells += f'<span class="mp-cell" title="{title}">{bar}<span class="mp-lab">{m[0]}</span></span>'
    return ('<div class="mpulse rev"><p class="mpulse-cap">Where it is in the water, month by month</p>'
            f'<div class="mpulse-grid">{cells}</div>{MARINE_CAVEAT}</div>')

def marine_hatch_html(exp):
    """Hatched outline pulse for beyond-scuba-only species (great white,
    orcas): cells from beyond_scuba[].months — never a rating colour."""
    by_mon = {}
    for b in exp.get("beyond_scuba") or []:
        for m in b.get("months") or []:
            by_mon.setdefault(m, set()).add(_mode_word(b["mode"]))
    cells = ""
    for m in MONTHS:
        modes = sorted(by_mon.get(m) or [])
        title = f'{m.upper()} · {" · ".join(modes)}' if modes else f"{m.upper()} · OUT OF SEASON"
        bar = ('<span class="mp-bar hx"></span>' if modes
               else '<span class="mp-bar" style="background:var(--line)"></span>')
        cells += f'<span class="mp-cell" title="{title}">{bar}<span class="mp-lab">{m[0]}</span></span>'
    kicker = " · ".join(_marine_modes(exp))
    return ('<div class="mpulse rev"><p class="mpulse-cap">Surface &amp; cage seasons — not scuba'
            + (f'<span class="mp-mode">{kicker}</span>' if kicker else "")
            + f'</p><div class="mpulse-grid">{cells}</div>{MARINE_CAVEAT}</div>')

MARINE_CAVEAT = ('<p class="mpulse-cav">Timing shifts year to year — '
                 'confirm dates with your operator.</p>')

def marine_stat_html(rows, pulse):
    """Build-stable stat strip (no client-date claims baked). MARINE_JS may
    swap cell 1 to the live 'IN SEASON NOW · n'; if it fails, this stands."""
    n = len(rows)
    peak = [MONTHS[i] for i, p in enumerate(pulse) if p["count"] and p["best"] == 0]
    widest = max(range(12), key=lambda i: pulse[i]["count"])
    return ('<div class="mstat">'
            f'<div id="mstatLive">SEASONS AT · <b>{n}</b> DESTINATION{"" if n == 1 else "S"}</div>'
            f'<div>PEAK MONTHS · <b>{_month_runs(peak) if peak else "—"}</b></div>'
            f'<div>WIDEST MONTH · <b>{MONTHS[widest].upper()}</b></div></div>')

def marine_sentence(exp, rows):
    """Build-stable computed sentence — fixed template, injected names/counts,
    no date-dependent claims. Top picks: best rating, then the longest season
    (ratings tie across many Peak rows — season length keeps the 'longest and
    strongest' claim honest), then name."""
    n = len(rows)
    short, verb = exp["short"], _marine_verb(exp["short"])
    if n == 1:
        return f'Across the year, {short} {verb} at one of our destinations — {rows[0][1]["name"]}.'
    picks = sorted(rows, key=lambda r: (r[0], -len(r[2]), r[1]["name"]))[:3]
    top = _join_list(x["name"] for _, x, _ in picks)
    return (f'Across the year, {short} {verb} at {n} of our destinations; '
            f'the longest and strongest seasons are {top}.')

def _marine_beyond(exp):
    if not exp.get("beyond_scuba"):
        return ""
    brows = "".join(
        f'<tr><td><b>{esc(b["name"])}</b><div class="meta">{esc(b["country"])} · {esc(b["mode"])}</div></td>'
        f'<td>{esc(", ".join(b["months"]))}</td>'
        f'<td><a class="pack-cta ghost" href="https://www.getyourguide.com/s/?q={urllib.parse.quote(b["q"])}" '
        f'target="_blank" rel="noopener sponsored">Book &rarr;</a></td></tr>'
        for b in exp["beyond_scuba"])
    return (f'<h2>Beyond scuba — snorkel &amp; cage encounters</h2>'
            f'<p class="greview" style="max-width:78ch">{esc(exp.get("beyond_intro") or "Some of the best encounters with this animal do not run on scuba — they are snorkel or cage-diving trips. If that is the experience you are after, these are the places to book it.")}</p>'
            f'<div class="tablecard rev"><table><thead><tr><th>Where</th><th>Season</th><th></th></tr></thead>'
            f'<tbody>{brows}</tbody></table></div>')

def _marine_notes(exp):
    tips = exp.get("tips") or []
    if not tips:
        return ""
    lis = "".join(f"<li>{esc(t)}</li>" for t in tips)
    return f'<h2>Field notes</h2><ol class="mnotes rev">{lis}</ol>'

def _marine_teasers(idx):
    def card(e, kick):
        posi = f' style="object-position:{esc(e["image_pos"])}"' if e.get("image_pos") else ""
        img = (f'<img src="{esc(e["image"])}" alt="" loading="lazy"{posi} '
               f'onerror="this.style.display=\'none\'">' if e.get("image") else "")
        return (f'<a class="mteaser" href="{e["slug"]}.html">{img}'
                f'<span class="mcover-scrim"></span><span class="mcover-txt">'
                f'<span class="mkick">{kick}</span>'
                f'<span class="mcover-title">{esc(e["title"])}</span></span></a>')
    prev_e = EXPERIENCES[(idx - 1) % len(EXPERIENCES)]
    next_e = EXPERIENCES[(idx + 1) % len(EXPERIENCES)]
    return f'<div class="mteasers rev">{card(prev_e, "Previous")}{card(next_e, "Next encounter")}</div>'

# Encounter-file styles, appended only on the 10 marine pages (extra_css) and
# scoped by the .mfile wrapper / m-prefixed classes. Mirrors the app's marine
# CSS in index.html — keep the two in visual sync.
MARINE_CSS = """
.mkick{display:block;font-family:var(--mono);font-size:.62rem;letter-spacing:.2em;text-transform:uppercase;color:#a8e6db}
.mwall{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:18px 0}
.mwall>.mcover.lead{grid-column:1/-1;height:clamp(300px,30vw,380px)}
.mcover{position:relative;display:block;border-radius:14px;overflow:hidden;border:1px solid var(--line);
  background:linear-gradient(160deg,#0e2f37,#0b7d75);
  height:clamp(200px,24vw,250px);box-shadow:0 6px 22px rgba(18,51,47,.05);transition:box-shadow .2s ease,border-color .2s ease}
.mcover:hover{border-color:var(--accent);box-shadow:0 12px 30px rgba(18,51,47,.12)}
.mcover:focus-visible{outline:2px solid #0b7d75;outline-offset:2px}
.mcover img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.mcover-scrim{position:absolute;inset:0;background:linear-gradient(180deg,rgba(8,32,29,0) 30%,rgba(8,32,29,.76) 100%)}
.mcover-txt{position:absolute;left:20px;right:20px;bottom:16px;color:#fff}
.mcover-title{display:block;font-family:var(--serif);font-weight:600;line-height:1.1;font-size:1.3rem;margin:6px 0 2px;color:#fff;
  text-shadow:0 2px 16px rgba(8,32,29,.4)}
.mcover.lead .mcover-title{font-size:clamp(1.6rem,4vw,2.4rem)}
.mstatus{display:block;font-family:var(--mono);font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;color:#bfe9e4;margin-top:8px}
@media(max-width:640px){.mwall{grid-template-columns:1fr}.mcover,.mwall>.mcover.lead{height:300px}
  .mkick{font-size:.58rem}.mcover.lead .mcover-title{font-size:2.2rem}}
.mstat{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid var(--line);border-bottom:1px solid var(--line);margin:18px 0 8px}
.mstat>div{padding:12px 8px 12px 14px;font-family:var(--mono);font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);line-height:1.6}
.mstat>div:first-child{padding-left:0}
.mstat>div+div{border-left:1px solid var(--line)}
.mstat b{color:var(--ink);font-weight:600}
@media(max-width:640px){.mstat{grid-template-columns:1fr}.mstat>div{padding:10px 0}.mstat>div+div{border-left:none;border-top:1px solid var(--line)}}
.mlede{font-size:1.05rem;line-height:1.75;color:#33565e;max-width:66ch}
.mlede::first-letter{float:left;font-family:var(--serif);font-weight:600;font-size:3.35em;line-height:.8;padding:6px 10px 0 0;color:#0b7d75}
.mpulse{margin:26px 0 10px}
.mpulse-cap{font-family:var(--mono);font-size:.64rem;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
.mpulse-cap .mp-mode{color:#0b7d75;margin-left:10px}
.mpulse-grid{display:grid;grid-template-columns:repeat(12,1fr);gap:4px;max-width:820px}
.mp-cell{display:block;padding:2px 0 5px}
.mp-bar{display:block;height:28px;border-radius:6px}
.mp-bar.hx{background:repeating-linear-gradient(45deg,transparent 0 3px,var(--line) 3px 4px);border:1px solid var(--line)}
.mp-lab{display:block;text-align:center;margin-top:5px;font-family:var(--mono);font-size:.58rem;letter-spacing:1px;color:var(--muted)}
.mpulse-cav{font-family:var(--mono);font-size:.62rem;color:var(--muted);margin:8px 0 0}
.msent{color:#33565e;line-height:1.7;max-width:80ch}
.mini-ribbon{display:grid;grid-template-columns:repeat(12,1fr);gap:3px;min-width:180px;max-width:260px;margin-top:4px}
.mini-ribbon i{display:block;height:12px;border-radius:3px}
.mini-ribbon i.now{box-shadow:0 0 0 1.5px #fff,0 0 0 3px var(--ink)}
.mnow{color:#0e7569}
.mnotes{list-style:none;margin:12px 0 4px;padding:0;counter-reset:mn;max-width:80ch}
.mnotes li{counter-increment:mn;display:flex;gap:16px;padding:13px 0;border-top:1px solid var(--line);color:#33565e;line-height:1.65;font-size:.95rem}
.mnotes li:last-child{border-bottom:1px solid var(--line)}
.mnotes li::before{content:counter(mn,decimal-leading-zero);font-family:var(--mono);font-size:.72rem;color:#0b7d75;padding-top:4px;letter-spacing:.08em}
.mnote-ed{font-family:var(--serif);font-style:italic;font-size:1.08rem;line-height:1.7;color:#33565e;max-width:70ch;border-left:3px solid #bcd7d9;padding-left:16px;margin:18px 0}
.mteasers{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:28px 0 8px}
@media(max-width:480px){.mteasers{grid-template-columns:1fr}}
.mteaser{position:relative;display:block;height:130px;border-radius:12px;overflow:hidden;border:1px solid var(--line);
  background:linear-gradient(160deg,#0e2f37,#0b7d75);
  transition:box-shadow .2s ease,border-color .2s ease}
.mteaser:hover{border-color:var(--accent);box-shadow:0 12px 30px rgba(18,51,47,.12)}
.mteaser:focus-visible{outline:2px solid #0b7d75;outline-offset:2px}
.mteaser img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.mteaser .mcover-txt{left:14px;right:14px;bottom:12px}
.mteaser .mcover-title{font-size:1.15rem}
@media(prefers-reduced-motion:reduce){.mcover,.mteaser{transition:none}}
"""

# Additive enhancement on species pages: ring the current month on each ledger
# ribbon, tag those rows "in season now", and swap the first stat cell to the
# live count. Never reorders, never hides content; the page is complete
# without it (guarded — the build-stable stat stands if anything fails).
MARINE_JS = """
(function(){try{
  var mi=new Date().getMonth(),n=0;
  [].slice.call(document.querySelectorAll('.mfile .mini-ribbon')).forEach(function(rb){
    var c=rb.children[mi];
    if(!c||!c.getAttribute('data-r'))return;
    c.className='now';n++;
    var tr=c.closest&&c.closest('tr');
    var meta=tr&&tr.querySelector('.meta');
    if(meta){var b=document.createElement('b');b.className='mnow';b.textContent=' · in season now';meta.appendChild(b);}
  });
  var s=document.getElementById('mstatLive');
  if(s)s.innerHTML='IN SEASON NOW · <b>'+n+'</b> DESTINATION'+(n===1?'':'S');
}catch(e){}})();
"""

def marine_article(exp, dests, prefix="../"):
    url = BASE + "marine-life/" + exp["slug"] + ".html"
    idx = EXPERIENCES.index(exp)
    rows = where_when(dests, exp["keywords"])
    pulse = marine_pulse(dests, exp["keywords"])
    lede = f'<p class="mlede rev">{esc(exp["intro"])}</p>'
    if rows:
        # scuba cover story: stat strip → drop-cap lede → pulse → computed
        # sentence → ribbon ledger → field notes → beyond scuba → CTA → teasers
        body_rows = "".join(
            f'<tr><td><b><a href="{prefix}destinations/{x["slug"]}.html">{esc(x["name"])}</a></b>'
            f'<div class="meta">{esc(x["country"])}</div></td>'
            f'<td>{mini_ribbon_html(x, months)}</td></tr>'
            for best, x, months in rows)
        table = (f'<h2>Where &amp; when to dive it</h2>'
                 f'<p class="greview" style="max-width:78ch">Pulled live from our seasonal data — the destinations where '
                 f'{esc(exp["short"])} shows in the water, and the months to catch it.</p>'
                 f'<div class="tablecard rev"><table><thead><tr><th>Destination</th><th>Best months</th></tr></thead>'
                 f'<tbody>{body_rows}</tbody></table></div>')
        core = (marine_stat_html(rows, pulse) + lede
                + marine_pulse_html(exp, pulse)
                + f'<p class="msent">{esc(marine_sentence(exp, rows))}</p>'
                + table + _marine_notes(exp) + _marine_beyond(exp))
    else:
        # beyond-scuba species (great white, orcas): no stat strip, no ledger —
        # editor's note + hatched surface-season pulse, beyond table as primary
        note = esc(exp.get("no_data") or "This is an opportunistic encounter — "
                   "none of our current destinations has a fixed season for it yet.")
        hatch = marine_hatch_html(exp) if exp.get("beyond_scuba") else ""
        core = (lede + f'<p class="mnote-ed rev">{note}</p>' + hatch
                + _marine_beyond(exp) + _marine_notes(exp))
    inner = ('<div class="mfile">' + core
             + f'<a class="cta" href="{prefix}index.html">Plan a trip around it — open the dive planner &rarr;</a>'
             + _marine_teasers(idx) + '</div>')
    hero = photo_hero("Marine life",
                      exp["title"], "",
                      exp.get("image") or "", exp.get("image_credit") or "",
                      pos=exp.get("image_pos") or "")
    art = {"@type": "Article", "headline": exp["title"], "description": exp["desc"], "url": url,
           "author": {"@type": "Organization", "name": "DiveSZN"},
           "publisher": {"@type": "Organization", "name": "DiveSZN", "url": BASE}}
    if exp.get("image"):
        art["image"] = exp["image"]
    ld = graph_ld(art, crumbs([("Home", BASE), ("Marine life", BASE + "marine-life/index.html"),
                               (exp["title"], url)]))
    return content_shell(exp["title"] + " | DiveSZN", exp["desc"], url, prefix, exp.get("hero_sub"), inner, ld,
                         hero_html=hero, extra_css=MARINE_CSS, extra_js=MARINE_JS if rows else "")

def marine_index_page(dests, prefix="../"):
    url = BASE + "marine-life/index.html"
    def _mcover(e, i, lead=False):
        rows = where_when(dests, e["keywords"])
        if rows:
            status = f'SEASONS AT · {len(rows)} DESTINATION{"" if len(rows) == 1 else "S"}'
        else:
            modes = _marine_modes(e)
            status = " · ".join(modes) + " ONLY" if modes else ""
        posi = f' style="object-position:{esc(e["image_pos"])}"' if e.get("image_pos") else ""
        img = (f'<img src="{esc(e["image"])}" alt="" loading="lazy"{posi} '
               f'onerror="this.style.display=\'none\'">' if e.get("image") else "")
        return (f'<a class="mcover{" lead" if lead else ""}" href="{e["slug"]}.html">{img}'
                f'<span class="mcover-scrim"></span><span class="mcover-txt">'
                f'<span class="mcover-title">{esc(e["title"])}</span>'
                + (f'<span class="mstatus">{status}</span>' if status else "")
                + '</span></a>')
    wall = (_mcover(EXPERIENCES[0], 0, lead=True)
            + "".join(_mcover(e, i + 1) for i, e in enumerate(EXPERIENCES[1:])))
    desc = ("Diving with the ocean's headline animals — whale sharks, mantas, hammerheads, mola mola, "
            "sea lions and more — the best destinations and seasons for each.")
    inner = (f'<div class="mfile"><p class="greview" style="max-width:80ch">The ocean&#8217;s headline encounters — what they are, and '
             f'where and when to dive them, pulled live from DiveSZN&#8217;s seasonal data.</p>'
             f'<h2>Encounters</h2><div class="mwall rev">{wall}</div>'
             f'<a class="cta" href="../index.html">Open the dive planner &rarr;</a></div>')
    ld = graph_ld({"@type": "CollectionPage", "name": "Marine life encounters",
                   "description": desc, "url": url},
                  crumbs([("Home", BASE), ("Marine life", url)]))
    lead = next((e for e in EXPERIENCES if e.get("image")), None)
    hero = photo_hero("Marine life guides", "Marine Life",
                      "Whale sharks to orcas — what they are, and where and when to dive them.",
                      (lead or {}).get("image", ""), (lead or {}).get("image_credit", ""))
    return content_shell("Marine Life — Dive With the Ocean's Icons | DiveSZN", desc, url, prefix,
                         "Whale sharks to orcas — what they are, and where and when to dive them.", inner, ld,
                         hero_html=hero, extra_css=MARINE_CSS)

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
        photo = (f'<div class="gphoto dphoto"><img src="{esc(img)}" alt="{esc(r["name"])}" loading="lazy" '
                 f'onerror="this.style.display=\'none\'"></div>'
                 if img else '<div class="gphoto dphoto"></div>')
        chips = (f'<span class="badge sm" style="background:{TONAL[r["rating"]]};'
                 f'color:{TONAL_TEXT[r["rating"]]}">{r["rating"]}</span> '
                 f'<span class="chip">{r["water_temp_c"] if r["water_temp_c"] is not None else "—"}°C</span> '
                 f'<span class="chip">{r.get("visibility_m") or "—"}m viz</span>'
                 + (f' <span class="chip">{esc(r["current_strength"])} current</span>' if r.get("current_strength") else ""))
        expect = (f'<b>What to expect in {full}:</b> {esc(mm["marine_life"])}.'
                  + (f' <b>Conditions:</b> {esc(mm["conditions"])}.' if mm.get("conditions") else ""))
        return (f'<div class="gentry rev">{photo}<div>'
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
        sections += (f'<h2 class="region-head rev">{esc(g)}</h2><p class="region-lede">{esc(lede)}</p>'
                     + "".join(block(r) for r in rs))

    mi = MONTHS.index(month)
    prev_m, next_m = MONTH_FULL[MONTHS[(mi + 11) % 12]], MONTH_FULL[MONTHS[(mi + 1) % 12]]
    pager = (f'<p class="meta" style="display:flex;justify-content:space-between;gap:12px">'
             f'<a href="{prev_m.lower()}.html">&larr; {prev_m}</a>'
             f'<a href="index.html">All months</a>'
             f'<a href="{next_m.lower()}.html">{next_m} &rarr;</a></p>')
    top3 = ", ".join(r["name"] for r in rows[:3])
    desc = meta_desc(f"The best scuba diving in {full}: {top3} and more — season ratings, water temperature, visibility and the marine life in season.")
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
    # photo hero: the month's lead destination photo (the top-ranked pick with one)
    lead_img = lead_credit = ""
    for r in rows:
        d0 = dests_by_name[r["name"]]
        if d0.get("image"):
            lead_img, lead_credit = d0["image"], d0.get("image_credit") or ""
            break
    hero = photo_hero("Monthly dive guide", f"Best Scuba Diving in {full}",
                      f"Where the water is at its best in {full}, region by region.",
                      lead_img, lead_credit)
    return content_shell(f"Best Scuba Diving in {full} — Where to Dive | DiveSZN", desc, url, "../",
                         f"Where the water is at its best in {full}, region by region.", inner, ld,
                         hero_html=hero)

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
        th = (f'<div class="th photo"><img src="{esc(img)}" alt="" loading="lazy" '
              f'onerror="this.style.display=\'none\'"></div>'
              if img else '<div class="th"></div>')
        rows += (f'<li><a href="{full.lower()}.html">{th}'
                 f'<div><h3>Best diving in {full}</h3><p>{esc(teaser)}</p></div></a></li>')
    desc = "Month-by-month guides to the world's best scuba diving — where the season, marine life and visibility line up for each month of the year."
    inner = (f'<p class="greview" style="max-width:80ch">Twelve guides, one per month — every destination scored for '
             f'that month and grouped by region, so your travel dates pick the spot.</p>'
             f'<h2>Guides</h2><ul class="artlist rev">{rows}</ul>'
             f'<a class="cta" href="../index.html">Open the dive planner &rarr;</a>')
    ld = graph_ld({"@type": "CollectionPage", "name": "Best scuba diving by month", "description": desc, "url": url},
                  crumbs([("Home", BASE), ("Best diving by month", url)]))
    # hero photo: the current month's lead destination photo
    now_m = MONTHS[datetime.date.today().month - 1]
    hero_img = hero_credit = ""
    for r in month_ranked(rankings, now_m, dests_by_name):
        d0 = dests_by_name[r["name"]]
        if d0.get("image"):
            hero_img, hero_credit = d0["image"], d0.get("image_credit") or ""
            break
    hero = photo_hero("Best diving by month", "Best Scuba Diving by Month",
                      "Where to dive in January through December.", hero_img, hero_credit)
    return content_shell("Best Scuba Diving by Month | DiveSZN", desc, url, "../",
                         "Where to dive in January through December.", inner, ld, hero_html=hero)

def main():
    with open(os.path.join(ROOT, "diving-destinations.json")) as f:
        dests = json.load(f)["destinations"]
    with open(os.path.join(ROOT, "gear-guide.json")) as f:
        gear = json.load(f)
    with open(os.path.join(ROOT, "diving-rankings.json")) as f:
        rankings = json.load(f)
    dests_by_name = {d["name"]: d for d in dests}
    _SLUGS.update({d["name"]: d["slug"] for d in dests})
    # top-scoring month per destination, straight from the prebuilt rankings
    # (never recompute the score here — the formula lives in the engine)
    top_months = {}
    for per in rankings["periods"]:
        for r in per["ranked"]:
            cur = top_months.get(r["name"])
            if cur is None or r["score"] > cur[1]:
                top_months[r["name"]] = (per["month"], r["score"])
    outdir = os.path.join(ROOT, "destinations")
    os.makedirs(outdir, exist_ok=True)
    for d in dests:
        with open(os.path.join(outdir, d["slug"] + ".html"), "w", encoding="utf-8") as f:
            f.write(page(d, top_months.get(d["name"])))
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
        f.write(marine_index_page(dests))

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
<meta name="robots" content="noindex">
<link rel="canonical" href="{esc(url)}">{FONTS_LINK}
<style>{CSS}{V2_CSS}</style></head><body class="v2">
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
    with open(os.path.join(ROOT, "privacy.html"), "w", encoding="utf-8") as f:
        f.write(privacy_page())

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
          f"{len(gear_slugs)} gear pages + index, about + how-we-score + privacy, "
          f"sitemap.xml ({len(urls)} URLs), robots.txt")

if __name__ == "__main__":
    main()
