#!/usr/bin/env python3
"""Turn raw gear product photos into uniform 'studio' shots (Orbea-style):
product knocked out of its background, centred on a light studio canvas with
a tight contact shadow plus a wide ambient shadow.

Reads  assets/gear/<name>.{jpg,png,webp}
Writes assets/gear/studio/<name>.jpg   (1200x900, quality 88)

Only photos whose background can be safely removed are processed:
  - PNGs with a real alpha channel use it directly;
  - photos with a near-uniform LIGHT background (sampled at the corners) get
    a color-distance knockout.
Photos with dark/busy backgrounds, lifestyle scenes or embedded retailer
logos are skipped and listed, so they can be replaced at the source instead
of shipping a bad cutout.

Usage: python3 scripts/studio_gear.py [--only name.jpg]
"""
import os, sys, glob
from PIL import Image, ImageFilter, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "gear")
DST = os.path.join(SRC, "studio")

CANVAS = (1200, 900)
FIT = (0.80, 0.74)              # max product width/height as canvas fraction
BG_TOP, BG_BOT = (248, 249, 250), (236, 238, 240)

# photos that must not be auto-processed (lifestyle scenes, retailer logos,
# dark studio backgrounds where a black product can't be separated)
SKIP = {
    "o-neill-reactor-2.jpg",                # surf lifestyle shot
    "mares-reef.jpg",                       # beach lifestyle shot
    "atomic-aquatics-splitfin.png",         # retailer logo card — replace at source
    "garmin-descent-mk3i.png",              # retailer logo card — replace at source
    "scubapro-everflex-yulex-steamer.jpg",  # marketing infographic with callout text
    "bare-reactive.jpg",                    # black-on-black studio
    "garmin-descent-g1.jpg",                # black background
    "scubapro-level.jpg",                   # grey-on-grey — cutout fringes
    "fourth-element-proteus-ii.jpg",        # black background pair
}


def corner_bg(im, pad=6):
    """Median corner colour if the four corners agree (near-uniform bg)."""
    w, h = im.size
    spots = [(pad, pad), (w - pad, pad), (pad, h - pad), (w - pad, h - pad)]
    cols = [im.getpixel(p)[:3] for p in spots]
    avg = tuple(sum(c[i] for c in cols) // 4 for i in range(3))
    spread = max(max(abs(c[i] - avg[i]) for i in range(3)) for c in cols)
    return avg if spread <= 26 else None


def knockout(im):
    """Alpha from colour distance to the (light, uniform) background."""
    bg = corner_bg(im)
    if bg is None or (0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]) < 200:
        return None
    px = im.convert("RGB")
    a = Image.new("L", im.size, 0)
    src, dst = px.load(), a.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b = src[x, y]
            d = abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2])
            dst[x, y] = 255 if d > 90 else (0 if d < 36 else int((d - 36) * 255 / 54))
    a = a.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    out = px.convert("RGBA")
    out.putalpha(a)
    return out


def studio(cut):
    """Compose the cutout on the studio canvas with two shadows."""
    W, H = CANVAS
    bbox = cut.getbbox()
    if not bbox:
        return None
    cut = cut.crop(bbox)
    scale = min(W * FIT[0] / cut.width, H * FIT[1] / cut.height)
    cut = cut.resize((max(1, int(cut.width * scale)), max(1, int(cut.height * scale))), Image.LANCZOS)

    canvas = Image.new("RGB", CANVAS, BG_TOP)
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(255 * y / H))
    grad = grad.resize(CANVAS)
    canvas = Image.composite(Image.new("RGB", CANVAS, BG_BOT), canvas, grad)

    x = (W - cut.width) // 2
    y = (H - cut.height) // 2 - 14
    alpha = cut.split()[-1]

    ambient = Image.new("L", CANVAS, 0)
    ambient.paste(alpha, (x, y + 30))
    ambient = ambient.filter(ImageFilter.GaussianBlur(34)).point(lambda v: int(v * 0.20))
    canvas.paste(Image.new("RGB", CANVAS, (24, 42, 48)), (0, 0), ambient)

    contact = Image.new("L", CANVAS, 0)
    contact.paste(alpha, (x, y + 13))
    contact = contact.filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.30))
    canvas.paste(Image.new("RGB", CANVAS, (14, 28, 33)), (0, 0), contact)

    canvas.paste(cut, (x, y), cut)
    return canvas


def main():
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    os.makedirs(DST, exist_ok=True)
    done, skipped, failed = [], [], []
    for path in sorted(glob.glob(os.path.join(SRC, "*.*"))):
        name = os.path.basename(path)
        if only and name != only:
            continue
        if name in SKIP:
            skipped.append(name)
            continue
        im = Image.open(path)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            cut = im if im.getextrema()[-1][0] < 250 else knockout(im.convert("RGB"))
        else:
            cut = knockout(im.convert("RGB"))
        if cut is None:
            failed.append(name)
            continue
        comp = studio(cut)
        if comp is None:
            failed.append(name)
            continue
        out = os.path.join(DST, os.path.splitext(name)[0] + ".jpg")
        comp.save(out, quality=88)
        done.append(name)
    print(f"studio: {len(done)} done · {len(skipped)} skipped (SKIP list) · {len(failed)} no uniform light bg")
    for n in skipped:
        print("  skip:", n)
    for n in failed:
        print("  FAIL:", n)


if __name__ == "__main__":
    main()
