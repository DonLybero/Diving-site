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


HERO = (1680, 760)

# Group photos that show several colourways side by side: split into one
# cutout per colour (components ordered left-to-right in the source photo).
SPLITS = {
    "mares-avanti-quattro": ["Blue", "White", "Lime", "Pink", "Black", "Yellow"],
    "bare-2mm-sport-s-flex-shorty": ["Red", "Blue"],
}


def components_cc(cut, k):
    """Connected-component split (8-connectivity); small fragments (straps,
    buckles) merge into the nearest big component. None if count != k."""
    import numpy as np, collections
    a = (np.array(cut.split()[-1]) > 40).astype(np.uint8)
    H, W = a.shape
    lab = np.zeros_like(a, dtype=np.int32)
    cur = 0
    for sy in range(H):
        for sx in range(W):
            if a[sy, sx] and not lab[sy, sx]:
                cur += 1
                q = collections.deque([(sy, sx)]); lab[sy, sx] = cur
                while q:
                    y, x = q.popleft()
                    for ny in (y - 1, y, y + 1):
                        for nx in (x - 1, x, x + 1):
                            if 0 <= ny < H and 0 <= nx < W and a[ny, nx] and not lab[ny, nx]:
                                lab[ny, nx] = cur; q.append((ny, nx))
    total = int(a.sum())
    cents, sizes = {}, {}
    for i in range(1, cur + 1):
        m = lab == i
        sizes[i] = int(m.sum())
        ys, xs = np.where(m)
        cents[i] = (float(xs.mean()), float(ys.mean()))
    big = [i for i in sizes if sizes[i] >= total * 0.04]
    if len(big) != k:
        return None
    owner = {}
    for i in sizes:
        if i in big:
            owner[i] = i
        else:
            owner[i] = min(big, key=lambda b: (cents[b][0] - cents[i][0]) ** 2 + (cents[b][1] - cents[i][1]) ** 2)
    pieces = []
    for b in sorted(big, key=lambda b: cents[b][0]):
        m = np.isin(lab, [i for i in owner if owner[i] == b])
        ys, xs = np.where(m)
        piece = cut.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)).copy()
        pm = Image.fromarray((m[ys.min():ys.max() + 1, xs.min():xs.max() + 1] * 255).astype("uint8"))
        al = Image.composite(piece.split()[-1], Image.new("L", piece.size, 0), pm)
        piece.putalpha(al)
        pieces.append(piece)
    return pieces


def components(cut, k):
    """Split an RGBA group cutout into k left-to-right pieces by cutting at
    the k-1 emptiest vertical seams (column alpha valleys)."""
    import numpy as np
    a = np.array(cut.split()[-1]).astype(np.float64)
    col = a.sum(axis=0)
    W = len(col)
    n_seams = k - 1
    seams = []
    lo, hi = int(W * 0.08), int(W * 0.92)
    order = np.argsort(col[lo:hi]) + lo
    min_gap = W // (k * 2)
    for x in order:
        if all(abs(x - s) >= min_gap for s in seams):
            seams.append(int(x))
            if len(seams) == n_seams:
                break
    seams.sort()
    edges = [0] + seams + [W]
    parts = []
    for i in range(k):
        piece = cut.crop((edges[i], 0, edges[i + 1], cut.height))
        if piece.getbbox():
            parts.append(piece.crop(piece.getbbox()))
    return parts


def hero(cut):
    """Orbea-style hero: main product centred with shadows, flanked by two
    faded ghost 'shades' of itself cropped at the canvas edges."""
    W, H = HERO
    bbox = cut.getbbox()
    if not bbox:
        return None
    cut = cut.crop(bbox)
    scale = min(W * 0.34 / cut.width, H * 0.62 / cut.height)
    main = cut.resize((max(1, int(cut.width * scale)), max(1, int(cut.height * scale))), Image.LANCZOS)

    canvas = Image.new("RGB", HERO, (243, 244, 245))
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(255 * y / H))
    grad = grad.resize(HERO)
    canvas = Image.composite(Image.new("RGB", HERO, (233, 235, 237)), canvas, grad)

    ghost = main.resize((int(main.width * 0.82), int(main.height * 0.82)), Image.LANCZOS)
    g_alpha = ghost.split()[-1].point(lambda v: int(v * 0.14))
    gy = (H - ghost.height) // 2 - int(H * 0.04)
    for gx in (int(W * 0.045) - ghost.width // 2, int(W * 0.955) - ghost.width // 2):
        canvas.paste(ghost.convert("RGB"), (gx, gy), g_alpha)

    x, y = (W - main.width) // 2, (H - main.height) // 2 - int(H * 0.07)
    alpha = main.split()[-1]
    ambient = Image.new("L", HERO, 0)
    ambient.paste(alpha, (x, y + 28))
    ambient = ambient.filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.20))
    canvas.paste(Image.new("RGB", HERO, (24, 42, 48)), (0, 0), ambient)
    contact = Image.new("L", HERO, 0)
    contact.paste(alpha, (x, y + 12))
    contact = contact.filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.30))
    canvas.paste(Image.new("RGB", HERO, (14, 28, 33)), (0, 0), contact)
    canvas.paste(main, (x, y), main)
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
        base = os.path.splitext(name)[0]
        comp.save(os.path.join(DST, base + ".jpg"), quality=88)
        herodir = os.path.join(DST, "hero")
        os.makedirs(herodir, exist_ok=True)
        if base in SPLITS:
            names_ = SPLITS[base]
            parts = components_cc(cut, len(names_)) or components(cut, len(names_))
            if len(parts) != len(names_):
                print(f"  ! split {base}: expected {len(names_)} parts, got {len(parts)} — no split")
                hero(cut).save(os.path.join(herodir, base + ".jpg"), quality=88)
            else:
                for cname, piece in zip(names_, parts):
                    h = hero(piece)
                    h.save(os.path.join(herodir, f"{base}--{cname.lower()}.jpg"), quality=88)
                    print(f"    split: {base} -> {cname}")
                # default hero = first colour
                hero(parts[0]).save(os.path.join(herodir, base + ".jpg"), quality=88)
        else:
            hero(cut).save(os.path.join(herodir, base + ".jpg"), quality=88)
        done.append(name)
    print(f"studio: {len(done)} done · {len(skipped)} skipped (SKIP list) · {len(failed)} no uniform light bg")
    for n in skipped:
        print("  skip:", n)
    for n in failed:
        print("  FAIL:", n)


if __name__ == "__main__":
    main()
