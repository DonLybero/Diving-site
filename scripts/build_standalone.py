#!/usr/bin/env python3
"""Bundle the modular site into ONE self-contained file (diving-site.html)
that opens by double-click — no web server, no external requests.
Inlines Leaflet CSS/JS, the calendar engine, the destinations data and the
world-land outline (as window.__DEST_DATA__ / window.__LAND_DATA__)."""
import json, os

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root

def read(p):
    with open(os.path.join(OUT, p), encoding="utf-8") as f:
        return f.read()

html   = read("index.html")
lcss   = read("vendor/leaflet.css")
ljs    = read("vendor/leaflet.js")
engine = read("diving-calendar.js")
data   = json.loads(read("diving-destinations.json"))
land   = json.loads(read("vendor/world-land.geojson"))
try:
    gear = json.loads(read("gear-guide.json"))
except FileNotFoundError:
    gear = None
try:
    marine = json.loads(read("marine-life.json"))
except FileNotFoundError:
    marine = None

# Gear photos live in the repo (assets/gear/…); relative paths break when the
# single file is opened from an arbitrary folder, so point them at the live
# site (destination/marine photos already load from the web the same way).
ASSET_BASE = "https://donlybero.github.io/Diving-site/"
def _absolutize_images(node):
    if isinstance(node, dict):
        img = node.get("image")
        if isinstance(img, str) and img and not img.startswith(("http://", "https://", "data:")):
            node["image"] = ASSET_BASE + img.lstrip("./")
        for v in node.values():
            _absolutize_images(v)
    elif isinstance(node, list):
        for v in node:
            _absolutize_images(v)
if gear:
    _absolutize_images(gear)

# The hero video, its poster and the crew photo are repo-relative in index.html;
# rewrite them to the live site for the same reason as the gear photos.
html = html.replace("'assets/video/", "'" + ASSET_BASE + "assets/video/")
html = html.replace('poster="assets/video/', 'poster="' + ASSET_BASE + 'assets/video/')
html = html.replace("'assets/crew.jpg'", "'" + ASSET_BASE + "assets/crew.jpg'")

# 1) inline Leaflet CSS
html = html.replace('<link rel="stylesheet" href="vendor/leaflet.css">',
                    '<style>\n'+lcss+'\n</style>')
# 2) embed data BEFORE leaflet/engine scripts, then inline leaflet + engine
embed = ('<script>window.__DEST_DATA__=' + json.dumps(data, ensure_ascii=False) +
         ';\nwindow.__LAND_DATA__=' + json.dumps(land, ensure_ascii=False) +
         ';\nwindow.__GEAR_DATA__=' + json.dumps(gear, ensure_ascii=False) +
         ';\nwindow.__MARINE_DATA__=' + json.dumps(marine, ensure_ascii=False) + ';</script>\n')
# the app lazy-loads Leaflet from vendor/ on demand; the standalone build
# inlines it at the marker instead (file:// can't fetch), so `typeof L` is
# already defined and withLeaflet() short-circuits
html = html.replace('<!-- standalone:leaflet -->',
                    embed + '<script>\n' + ljs + '\n</script>')
html = html.replace('<script src="diving-calendar.js"></script>',
                    '<script>\n' + engine + '\n</script>')

out = os.path.join(OUT, "diving-site.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("Wrote", out, "(", round(os.path.getsize(out)/1024), "KB )")
