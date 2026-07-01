#!/usr/bin/env python3
import csv, json, sys, os, re, unicodedata

def slugify(name):
    s = unicodedata.normalize("NFD", name)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")   # strip accents
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s

HERE = os.path.dirname(os.path.abspath(__file__))   # repo/scripts
SCRATCH = os.path.join(HERE, "data")                # region JSON fragments live here
OUTDIR = os.path.dirname(HERE)                       # repo root (where the site files live)
sys.path.insert(0, HERE)                             # so build_csv / meta11 import

import build_csv          # exposes build_csv.destinations (orig 11)
from meta11 import META11

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# Representative dive-area coordinates [lat, lng] for the map view.
COORDS = {
 "Red Sea (Egypt)":[27.9,34.3],"Seychelles":[-4.68,55.49],"Raja Ampat":[-0.23,130.52],
 "Galapagos Islands":[-0.74,-90.31],"Sipadan Island":[4.11,118.63],"Maldives":[3.2,73.0],
 "Palau":[7.34,134.48],"Great Barrier Reef":[-16.9,146.1],"Truk (Chuuk) Lagoon":[7.42,151.78],
 "Cocos Island":[5.52,-87.06],"Komodo National Park":[-8.55,119.49],"Bonaire":[12.18,-68.31],
 "Cayman Islands":[19.34,-81.24],"Cozumel":[20.42,-86.92],"Bahamas":[24.7,-77.8],
 "Roatán":[16.33,-86.53],"Utila":[16.10,-86.93],"Bay Islands":[16.4,-86.4],
 "Great Blue Hole":[17.32,-87.53],"Silfra Fissure":[64.26,-21.12],"Azores":[38.4,-28.2],
 "Lundy Island":[51.18,-4.67],"Scapa Flow":[58.90,-3.18],"Medes Islands":[42.05,3.22],
 "Gozo & Malta":[36.05,14.30],"Vancouver Island":[50.3,-126.0],"Poor Knights Islands":[-35.46,174.74],
 "French Polynesia":[-16.0,-146.0],"Moorea":[-17.54,-149.83],"Fiji":[-17.8,178.1],
 "Maui & Kona":[20.0,-156.3],"Guadalcanal & Western Province":[-8.8,158.5],"Okinawa Islands":[24.4,123.8],
 "Lord Howe Island":[-31.55,159.08],"Socorro Island":[18.79,-110.97],"Apo Island & Dumaguete":[9.1,123.27],
 "Tubbataha Reefs Natural Park":[8.85,119.92],"Malapascua Island":[11.32,124.12],
 "Bunaken National Marine Park":[1.62,124.76],"Gili Islands & Lombok":[-8.35,116.04],
 "Similan Islands":[8.65,97.65],"Cenotes of Yucatán Peninsula":[20.3,-87.4],
 "Chagos Archipelago / BIOT":[-6.0,71.5],"Whitsunday Islands":[-19.9,149.1],"Heron Island":[-23.44,151.91],
 "Ningaloo Reef":[-22.0,113.9],"South West Rocks":[-30.93,153.07],"Aliwal Shoal":[-30.27,30.83],
 "Fernando de Noronha":[-3.85,-32.42],"Sea of Cortez":[24.4,-110.35],
}

# Parse a representative visibility in metres from a free-text conditions string.
# Returns an int (metres). Numbers below 5 are treated as sea-state (wave height),
# not visibility, and ignored. Falls back to qualitative wording.
_RANGE = re.compile(r'(\d+)\s*-\s*(\d+)\s*m')
_TO    = re.compile(r'to\s*(\d+)\s*m')
_PLUS  = re.compile(r'(\d+)\s*m\s*\+')
_SINGLE= re.compile(r'(\d+)\s*m')
def parse_visibility(text):
    t = (text or "").lower()
    nums = []
    for a, b in _RANGE.findall(t):
        a, b = int(a), int(b)
        if b >= 5:                      # ignore "1.5-3m" swell
            nums.append((a + b) / 2.0)
    for m in _PLUS.findall(t):
        if int(m) >= 5: nums.append(int(m))
    for m in _TO.findall(t):
        if int(m) >= 5: nums.append(int(m))
    if not nums:
        for m in _SINGLE.findall(t):
            if int(m) >= 5: nums.append(int(m))
    if nums:
        return int(round(max(nums) if max(nums) <= 50 else max(nums)))  # keep large (Silfra 100m)
    # qualitative fallback
    if "crystal" in t or "100m" in t: return 60
    if any(k in t for k in ("excellent","superb","top viz","best viz","outstanding")): return 32
    if any(k in t for k in ("good viz","clear","clearer","clearest")): return 24
    if any(k in t for k in ("reduced","lower","murky","green","plankton","runoff","poor","silt")): return 10
    if any(k in t for k in ("improving","recovering","variable","decent","moderate","settling")): return 16
    return 18

# Classify overall current strength (Low / Medium / Strong) from the currents text.
# Phrases are chosen to avoid comparatives like "stronger" giving false positives.
def classify_current(text):
    t = (text or "").lower()
    strong = ("ripping","ferocious","down-current","downcurrent","down-welling","washing machine",
              "powerful","severe","knot","high-speed","notorious","surge","fast current","committed drift",
              "reef hook","rip ","strong current","strong tidal","strong drift","strong, ","strong and",
              "often strong","can be strong","strong oceanic","strong, unpredictable","strong-current")
    low = ("mild","gentle","calm","negligible","little current","light current","sheltered","benign",
           "no current","minimal","weak","relaxed","easy drift","mild to negligible","generally mild")
    medium = ("drift","moderate","tidal","variable")
    has_strong = any(k in t for k in strong)
    has_low = any(k in t for k in low)
    has_med = any(k in t for k in medium)
    if has_strong: return "Strong"
    if has_low:    return "Low"
    if has_med:    return "Medium"
    return "Medium"

def temp_to_int(t):
    if isinstance(t, int):
        return t
    if isinstance(t, str):
        # e.g. "29 / 26" -> 29 (north/central headline)
        head = t.split("/")[0].strip()
        try:
            return int(head)
        except ValueError:
            return None
    return None

# ---- Build the original 11 into the website schema ----
orig11 = []
for d in build_csv.destinations:
    name = d["name"]
    meta = META11[name]
    monthly = {}
    monthly_temp = {}
    for m in MONTHS:
        temp, life, cond, rating = d["months"][m]
        ti = temp_to_int(temp)
        if name == "Sipadan Island" and m == "Nov":
            ti = 28  # island closed but representative water temp
        monthly_temp[m] = ti
        monthly[m] = {"rating": rating, "marine_life": life, "conditions": cond}
    obj = {
        "name": name,
        "country": meta["country"],
        "region": meta["region"],
        "water_type": meta["water_type"],
        "difficulty": meta["difficulty"],
        "access": meta["access"],
        "monthly_temp_c": monthly_temp,
        "currents": d["currents"],
        "best_months": meta["best_months"],
        "wetsuit": meta["wetsuit"],
        "signature_species": meta["signature_species"],
        "highlights": meta["highlights"],
        "monthly": monthly,
    }
    orig11.append(obj)

# ---- Load the 5 researched JSON arrays ----
def load(fn):
    with open(os.path.join(SCRATCH, fn)) as f:
        return json.load(f)

new = []
for fn in ["caribbean.json","europe.json","pacific.json","seasia.json","australia.json"]:
    new.extend(load(fn))

# ---- Normalize all records ----
RATINGS = {"Peak","Good","Shoulder","Low","Closed"}
def normalize(rec):
    # clean monthly dicts -> keep only rating/marine_life/conditions
    mon = {}
    for m in MONTHS:
        src = rec.get("monthly", {}).get(m, {})
        cond = src.get("conditions","")
        mon[m] = {
            "rating": src.get("rating","Good") if src.get("rating") in RATINGS else "Good",
            "marine_life": src.get("marine_life",""),
            "conditions": cond,
            "visibility_m": parse_visibility(cond),
        }
    rec["monthly"] = mon
    # ensure temps are ints
    mt = {}
    for m in MONTHS:
        mt[m] = temp_to_int(rec.get("monthly_temp_c",{}).get(m))
    rec["monthly_temp_c"] = mt
    # coordinates for the map view
    rec["coordinates"] = {"lat": COORDS.get(rec["name"], [None, None])[0],
                          "lng": COORDS.get(rec["name"], [None, None])[1]}
    # overall current strength (Low / Medium / Strong)
    rec["current_strength"] = classify_current(rec.get("currents",""))
    # stable slug for the static per-destination pages
    rec["slug"] = slugify(rec["name"])
    return rec

all_dest = [normalize(r) for r in (orig11 + new)]

# de-dupe by name (keep first); guard against accidental repeats
seen, deduped = set(), []
for r in all_dest:
    if r["name"] in seen:
        continue
    seen.add(r["name"])
    deduped.append(r)
all_dest = deduped

# stable sort: by region, then name
all_dest.sort(key=lambda r: (r["region"], r["name"]))

# ---- Preserve baked destination images (written into the output JSON by
# scripts/fetch_images.py / the fetch-images workflow, not present in sources) ----
_prev_path = os.path.join(OUTDIR, "diving-destinations.json")
if os.path.exists(_prev_path):
    with open(_prev_path) as f:
        _prev = {d["name"]: d for d in json.load(f).get("destinations", [])}
    kept = 0
    for r in all_dest:
        p = _prev.get(r["name"])
        if p and p.get("image"):
            for k in ("image", "image_credit", "image_source"):
                if p.get(k) is not None:
                    r[k] = p[k]
            kept += 1
    print(f"Preserved baked images for {kept} destinations")

# ---- Apply human/agent verification verdicts (scripts/data/verification.json) ----
# Shape: {"<name>": {"current_strength": "Low|Medium|Strong", "current_note": "...",
#                    "confidence": "high|medium|low", "verified": "YYYY-MM"}}
_ver_path = os.path.join(SCRATCH, "verification.json")
if os.path.exists(_ver_path):
    with open(_ver_path) as f:
        VER = json.load(f)
    applied = 0
    for r in all_dest:
        v = VER.get(r["name"])
        if not v:
            continue
        if v.get("current_strength") in ("Low", "Medium", "Strong"):
            r["current_strength"] = v["current_strength"]
        if v.get("current_note"):
            r["current_note"] = v["current_note"]
        r["data_confidence"] = v.get("confidence", "medium")
        r["last_verified"] = v.get("verified")
        applied += 1
    print(f"Applied verification verdicts for {applied} destinations")

# ---- Write master JSON ----
master = {
    "title": "World Diving Calendar",
    "description": "Year-round diving conditions for global destinations, organized by month. "
                   "Each destination includes monthly surface water temperature (degC), currents, "
                   "marine-life highlights, conditions/visibility and a season rating "
                   "(Peak / Good / Shoulder / Low / Closed).",
    "rating_legend": {
        "Peak": "Best conditions and/or signature marine life",
        "Good": "Reliable, enjoyable diving",
        "Shoulder": "Transitional - variable conditions",
        "Low": "Divable but rough / low-viz / off-season",
        "Closed": "Not accessible (park closure or no operators)"
    },
    "months": MONTHS,
    "destination_count": len(all_dest),
    "destinations": all_dest,
}
with open(os.path.join(OUTDIR,"diving-destinations.json"),"w") as f:
    json.dump(master, f, indent=2, ensure_ascii=False)
print("Wrote diving-destinations.json with", len(all_dest), "destinations")

# ---- Regenerate the long-format CSV (all destinations x 24 periods) ----
cols = ["Destination","Country","Region","Period_No","Month","Half","Water_Temp_C","Visibility_m",
        "Rating","Marine_Life_Highlights","Conditions_Visibility","Currents",
        "Difficulty","Access","Wetsuit","Best_Months"]
with open(os.path.join(OUTDIR,"diving-calendar-24-periods.csv"),"w",newline="") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for d in all_dest:
        pno = 0
        for m in MONTHS:
            mm = d["monthly"][m]
            for half in ["early","late"]:
                pno += 1
                w.writerow([
                    d["name"], d["country"], d["region"], pno, m, half,
                    d["monthly_temp_c"][m] if d["monthly_temp_c"][m] is not None else "",
                    mm["visibility_m"],
                    mm["rating"], mm["marine_life"], mm["conditions"], d["currents"],
                    d["difficulty"], d["access"], d["wetsuit"], d["best_months"],
                ])
print("Wrote diving-calendar-24-periods.csv")

# ---- Regenerate the pivot grid CSV (24 periods x destinations = rating) ----
grid_cols = ["Period_No","Month","Half"] + [d["name"] for d in all_dest]
with open(os.path.join(OUTDIR,"diving-calendar-grid.csv"),"w",newline="") as f:
    w = csv.writer(f)
    w.writerow(grid_cols)
    pno = 0
    for m in MONTHS:
        for half in ["early","late"]:
            pno += 1
            row = [pno, m, half] + [d["monthly"][m]["rating"] for d in all_dest]
            w.writerow(row)
print("Wrote diving-calendar-grid.csv")

# summary
from collections import Counter
print("Regions:", dict(Counter(d["region"] for d in all_dest)))
