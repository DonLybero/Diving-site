#!/usr/bin/env python3
"""Generate diving-rankings.json: precomputed top destinations for each of the
24 bi-monthly periods, using a transparent scoring system.

SCORE = rating_base + min(marine_excitement_bonus, BONUS_CAP) + visibility_bonus
  - rating_base rewards how good the diving conditions are that month.
  - marine_excitement_bonus rewards headline marine life active that month
    (whale sharks, hammerheads, mantas, whales, spawning events, etc.).
  - visibility_bonus rewards underwater visibility (0..VIZ_MAX points), scaled
    from the per-month visibility_m field (metres).
  - 'Closed' months are excluded from rankings entirely.
Ties broken by water comfort (closeness to 27 C) then name.
Keep this weight table identical to the one in diving-calendar.js.
"""
import json, os

OUTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

RATING_BASE = {"Peak":100, "Good":72, "Shoulder":48, "Low":22, "Closed":None}
BONUS_CAP = 25
COMFORT_TARGET = 27  # deg C, used only for tie-breaking
# Visibility scoring: scale visibility_m (metres) into 0..VIZ_MAX points.
VIZ_MIN, VIZ_REF, VIZ_MAX = 5, 35, 18  # <=5m -> 0 pts, >=35m -> 18 pts

def visibility_bonus(viz_m):
    if viz_m is None:
        return 0
    v = max(VIZ_MIN, min(viz_m, VIZ_REF))
    return int(round((v - VIZ_MIN) / (VIZ_REF - VIZ_MIN) * VIZ_MAX))

# Headline marine-life keywords -> bonus weight (presence-based, counted once each)
MARINE_WEIGHTS = [
    ("whale shark", 12), ("sardine run", 12),
    ("hammerhead", 10),
    ("manta", 9), ("minke", 9), ("tiger shark", 9),
    ("thresher", 9), ("oceanic whitetip", 9),
    ("mola", 8), ("mobula", 8), ("wall of shark", 8), ("shark wall", 8),
    ("humpback", 7), ("devil ray", 7), ("bull shark", 7),
    ("grouper spawn", 7), ("coral spawn", 7),
    ("barracuda tornado", 6), ("spawning", 6),
    ("sea lion", 5), ("aggregation", 5),
    ("grey reef shark", 4), ("silvertip", 4), ("turtle nesting", 4),
    ("dolphin", 3), ("nesting", 3),
    ("reef shark", 2), ("eagle ray", 2), ("seahorse", 2),
    ("frogfish", 2), ("mandarinfish", 2),
]

def marine_bonus(text):
    t = (text or "").lower()
    total = 0
    for kw, w in MARINE_WEIGHTS:
        if kw in t:
            total += w
    return min(total, BONUS_CAP)

def score_month(dest, month):
    mm = dest["monthly"][month]
    base = RATING_BASE.get(mm["rating"])
    if base is None:   # Closed
        return None
    return base + marine_bonus(mm["marine_life"]) + visibility_bonus(mm.get("visibility_m"))

def main():
    data = json.load(open(os.path.join(OUTDIR, "diving-destinations.json")))
    dests = data["destinations"]

    periods = []
    pno = 0
    for month in MONTHS:
        for half in ["early", "late"]:
            pno += 1
            ranked = []
            for d in dests:
                s = score_month(d, month)
                if s is None:
                    continue
                temp = d["monthly_temp_c"].get(month)
                ranked.append({
                    "name": d["name"],
                    "country": d["country"],
                    "region": d["region"],
                    "difficulty": d["difficulty"],
                    "access": d["access"],
                    "water_temp_c": temp,
                    "visibility_m": d["monthly"][month].get("visibility_m"),
                    "current_strength": d.get("current_strength"),
                    "rating": d["monthly"][month]["rating"],
                    "score": s,
                    "highlight": d["monthly"][month]["marine_life"],
                })
            # sort: score desc, then water comfort, then name
            ranked.sort(key=lambda r: (
                -r["score"],
                abs((r["water_temp_c"] if r["water_temp_c"] is not None else 99) - COMFORT_TARGET),
                r["name"],
            ))
            for i, r in enumerate(ranked, 1):
                r["rank"] = i
            periods.append({
                "period_no": pno,
                "month": month,
                "half": half,
                "label": f"{month} ({half})",
                "open_destinations": len(ranked),
                "ranked": ranked,
            })

    out = {
        "title": "World Diving Calendar - Period Rankings",
        "description": "Destinations ranked for each of the 24 bi-monthly periods. "
                       "Higher score = better diving conditions plus more headline marine life that period.",
        "scoring": {
            "rating_base": {k: v for k, v in RATING_BASE.items() if v is not None},
            "closed": "excluded from rankings",
            "marine_excitement_bonus": "sum of matched headline-species weights, capped at %d" % BONUS_CAP,
            "marine_weights": {kw: w for kw, w in MARINE_WEIGHTS},
            "visibility_bonus": "visibility_m scaled to 0..%d points (<=%dm -> 0, >=%dm -> %d)"
                                % (VIZ_MAX, VIZ_MIN, VIZ_REF, VIZ_MAX),
            "tie_breakers": ["water comfort (closeness to %d C)" % COMFORT_TARGET, "name"],
            "formula": "score = rating_base + min(sum(marine_weights matched), %d) + visibility_bonus"
                       % BONUS_CAP,
        },
        "period_count": len(periods),
        "periods": periods,
    }
    with open(os.path.join(OUTDIR, "diving-rankings.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("Wrote diving-rankings.json with", len(periods), "periods")

    # quick human-readable check: top 5 for a few sample periods
    for pno in (1, 15, 16, 21):  # Jan-early, Aug-early, Aug-late, Nov-early
        p = periods[pno-1]
        print(f"\n== Period {pno}: {p['label']} (top 5 of {p['open_destinations']}) ==")
        for r in p["ranked"][:5]:
            print(f"  {r['rank']}. {r['name']:<28} score {r['score']:>3}  "
                  f"[{r['rating']}] {r['highlight'][:45]}")

if __name__ == "__main__":
    main()
