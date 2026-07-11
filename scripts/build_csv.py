#!/usr/bin/env python3
import csv, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# For each destination: per-month dict with temp, currents, marine_life, conditions, rating.
# Optional 'half' overrides keyed by (month_index, 'early'/'late').
# Rating: Peak / Good / Shoulder / Low / Closed

destinations = []

# ---------------- RED SEA (EGYPT) ----------------
red_sea = {
 "name":"Red Sea (Egypt)",
 "currents":"Sheltered bays mild; offshore marine parks (Brothers, Daedalus, Elphinstone) strong unpredictable drift; winter N winds can cancel exposed sites",
 "months":{
  "Jan":(23,"Oceanic whitetip (south), threshers possible; reef & wreck focus","Clearest 'crystal' viz 20-40m; cool, occasional N wind","Good"),
  "Feb":(22,"Reef/wreck focus; oceanic whitetip south","Coldest water; clearest viz; calm-but-windy","Good"),
  "Mar":(22,"Big Fish season starts; mantas, early whale sharks late month","Warming; viz 20-40m","Peak"),
  "Apr":(24,"Big Fish season; mantas, early whale sharks","Warm, calm; ideal shoulder","Peak"),
  "May":(26,"Whale sharks building; hammerhead schooling begins (best May-Jul)","Warm, calm crossings","Peak"),
  "Jun":(28,"Whale shark peak begins; hammerheads building","Warm; calm; summer onset","Peak"),
  "Jul":(29,"Hammerhead schooling (Daedalus/Brothers), season tail; whale sharks","Hottest air; calmest crossings; slight plankton dip","Good"),
  "Aug":(30,"Hammerheads taper; coral spawning (lunar)","Warmest water ~30C shallows; calm","Good"),
  "Sep":(29,"Balanced: wrecks+reefs+pelagics; mantas, threshers begin","Warm, calm; connoisseur favorite","Peak"),
  "Oct":(27,"Oceanic whitetip & thresher building; mantas","Ideal warmth, calm seas","Peak"),
  "Nov":(25,"Oceanic whitetip + thresher PEAK (Brothers); mantas","Prime shark month; cooling","Peak"),
  "Dec":(24,"Threshers continue; oceanic whitetip south","Mild winter; clear viz; occasional wind","Good"),
 }
}
destinations.append(red_sea)

# ---------------- SEYCHELLES ----------------
seychelles = {
 "name":"Seychelles",
 "currents":"Inner islands (Mahe/Praslin) mild & beginner-friendly; SE trades May-Oct bring 20-30kt winds, surge, upwelling; outer islands/Aldabra liveaboard/permit only",
 "months":{
  "Jan":(28,"Hawksbill turtle nesting peak; eagle rays; whale sharks may linger","NW monsoon; warm, sheltered SE coasts","Good"),
  "Feb":(29,"Turtle nesting; reef life, eagle rays","Warm; calm NW monsoon","Good"),
  "Mar":(29,"Turtle nesting; early whale sharks (Amirantes late Mar)","Warm-water peak approaching","Good"),
  "Apr":(30,"Whale sharks (Amirantes Apr-May peak)","Transition: flat seas, best viz 25-35m, 30C","Peak"),
  "May":(28,"Whale shark peak (Amirantes); moving to inner waters","SE trades start; still good","Peak"),
  "Jun":(27,"Whale sharks through inner islands; trevally/jack schools","SE trades established; choppy exposed coasts","Good"),
  "Jul":(26,"Whale sharks; pelagic action outer chains","Coolest; thermocline ~24C; windy","Good"),
  "Aug":(26,"Whale shark aggregation building (Mahe NW/Beau Vallon); spinner dolphins","Cool, windy; sheltered coasts good","Good"),
  "Sep":(27,"Whale shark season opens in earnest; plankton blooms","Warming; trades easing","Good"),
  "Oct":(28,"Whale shark season peak (sightings rarer in recent years); mantas rising","Transition; seas settling, viz recovering","Peak"),
  "Nov":(28,"Whale sharks possible (rarer than historically); manta peak","Calm, clear; excellent all-round","Peak"),
  "Dec":(29,"Whale sharks tailing off; hawksbill nesting begins","Warm, calm NW monsoon","Good"),
 }
}
destinations.append(seychelles)

# ---------------- RAJA AMPAT ----------------
raja = {
 "name":"Raja Ampat",
 "currents":"Drift diving central; strongest at Dampier Strait (Cape Kri, Sardine Reef, Blue Magic) driving nutrient upwellings; plankton/current build from May",
 "months":{
  "Jan":(29,"Manta peak (Manta Sandy/Ridge); wobbegongs, walking sharks, pygmy seahorses","Peak NW monsoon; viz 20-30m+; secondary rain spike","Peak"),
  "Feb":(28,"Manta peak (strongest); record reef biodiversity","Coolest; calm; viz good","Peak"),
  "Mar":(28,"Late manta peak; macro","Calm NW monsoon; viz >30m","Peak"),
  "Apr":(28,"Manta season tail; reef biodiversity","Season tail; still calm","Good"),
  "May":(27,"Macro & night diving shine; mantas scattered","Transition; currents/plankton building","Shoulder"),
  "Jun":(28,"Macro, night dives; reef life","SE monsoon; rough, viz dropping","Low"),
  "Jul":(28,"Macro, critters; reef sharks","Low season: rough 1.5-3m, wettest; liveaboards pause","Low"),
  "Aug":(28,"Macro, night diving","Stormy; low season; many liveaboards reposition","Low"),
  "Sep":(28,"Macro; reef life; mantas returning late","Transition; conditions improving","Shoulder"),
  "Oct":(29,"Season opens; mantas building","Calm seas return; viz 25-40m","Good"),
  "Nov":(29,"Manta season opens (Manta Sandy/Ridge)","Warm; calm; thermocline ~22C deep Misool","Good"),
  "Dec":(30,"Manta peak begins; warmest, calm","Peak season; viz 20-30m+; secondary rain","Peak"),
 }
}
destinations.append(raja)

# ---------------- GALAPAGOS ----------------
galapagos = {
 "name":"Galapagos Islands",
 "currents":"Notoriously strong - 4 converging currents; negative entries, down-currents, surge; Darwin & Wolf advanced/liveaboard-only; Gordon's Rocks 'washing machine'",
 "months":{
  "Jan":(24,"Mantas; hammerhead schools (smaller); sea lions, iguanas","Warm season; calm, smooth crossings; viz 15-30m","Good"),
  "Feb":(26,"Mantas, eagle rays; warmest period","Warmest; calm; better viz","Good"),
  "Mar":(26,"Mantas; calm-water megafauna","Warm peak; calm crossings","Good"),
  "Apr":(26,"Mantas increasing; eagle rays","Warm; calm; good viz","Good"),
  "May":(25,"Mantas peak; last warm month","Transition; calm; good viz","Good"),
  "Jun":(23,"Whale sharks arriving; hammerheads building; penguins active","Cool season begins; choppier; viz dropping","Peak"),
  "Jul":(22,"Whale sharks; big hammerhead schools","Cooling; rough crossings; greener water","Peak"),
  "Aug":(21,"Whale shark + hammerhead PEAK (Darwin/Wolf); mola mola","Coldest begins; cold thermoclines; rough; viz 5-20m","Peak"),
  "Sep":(21,"Peak megafauna: whale sharks, hammerheads, mola","Coldest; rough; low viz but peak animals","Peak"),
  "Oct":(21,"Whale sharks tapering (still peak); hammerheads; mola","Cool; rough; plankton-green","Peak"),
  "Nov":(22,"Hammerheads; mola; megafauna tapering","Transition; warming begins","Good"),
  "Dec":(23,"Mantas returning; hammerheads","Warm season begins; calmer","Good"),
 }
}
destinations.append(galapagos)

# ---------------- SIPADAN ----------------
sipadan = {
 "name":"Sipadan Island",
 "currents":"Currents are the key variable (stronger=more action); Barracuda Point (barracuda tornado, dawn hammerheads), South Point (strongest, pelagics), Drop Off (gentle)",
 "months":{
  "Jan":(28,"Barracuda tornado, jackfish, reef sharks, turtles; CNY window","Cooler; N wind can cut viz to 10-20m","Good"),
  "Feb":(28,"Barracuda tornado, reef sharks, turtles","Cooler; N wind; viz variable","Good"),
  "Mar":(29,"Turtles (20+/dive), barracuda, reef sharks; nesting begins","Prime window opens; calm; viz 20-40m","Peak"),
  "Apr":(30,"Turtle nesting begins; barracuda tornado, bumpheads","Calm seas, excellent viz","Peak"),
  "May":(30,"Turtle nesting full swing; peak conditions","Peak: warmest, best viz, calmest","Peak"),
  "Jun":(30,"Turtles abundant; barracuda tornado, reef sharks","Peak conditions; viz 20-50m","Peak"),
  "Jul":(30,"Turtles; barracuda; occasional hammerheads (dawn)","Peak/late prime; warm, calm","Peak"),
  "Aug":(29,"Turtles; nesting tapers; reef sharks","S winds can briefly cut viz; still good","Good"),
  "Sep":(28,"Turtles, barracuda; 2nd prime window","Seas settle; viz outstanding 30m+","Peak"),
  "Oct":(28,"Barracuda tornado, turtles, reef sharks","2nd excellent window; viz 30-50m+","Peak"),
  "Nov":(0,"ISLAND CLOSED for conservation (nearby Mabul/Kapalai divable)","CLOSED all month (Sabah Parks)","Closed"),
  "Dec":(28,"Residents present; turtles, barracuda","Rainy onset; viz softer; slightly cooler","Good"),
 }
}
destinations.append(sipadan)

# ---------------- MALDIVES ----------------
maldives = {
 "name":"Maldives",
 "currents":"Monsoon-driven channel (kandu) drift; NE monsoon (Dec-Apr) dive east side for viz/pelagics, mantas west; SW monsoon (May-Nov) dive west side, mantas/whale sharks east; strongest at full/new moon",
 "months":{
  "Jan":(28,"Hammerheads Rasdhoo (dawn); Fuvahmulah tiger sharks; grey reef sharks","NE monsoon: best viz 30-40m, calm","Peak"),
  "Feb":(28,"Hammerheads Rasdhoo; Fuvahmulah tigers (peak)","Peak dry season; superb viz","Peak"),
  "Mar":(29,"Hammerheads Rasdhoo (Feb-May); Fuvahmulah tigers","Clear water; calm; all-round diving","Peak"),
  "Apr":(30,"Hammerhead season closing; manta activity strengthening","Warmest; tail of NE monsoon","Peak"),
  "May":(30,"Manta peak begins; whale sharks building","Transition; SW monsoon starts; viz dropping","Good"),
  "Jun":(29,"Manta peak; whale sharks (S Ari)","SW monsoon; plankton; viz 15-25m","Good"),
  "Jul":(29,"Whale shark peak (S Ari); Hanifaru manta aggregation begins","Plankton-rich; lower viz; stronger currents","Peak"),
  "Aug":(29,"Hanifaru Bay manta+whale-shark PEAK (100+ mantas)","Best Hanifaru activity; viz 10-25m; full/new moon best","Peak"),
  "Sep":(29,"Hanifaru manta peak; whale sharks","Hanifaru peak; lower viz; plankton soup","Peak"),
  "Oct":(29,"Hanifaru tail; whale sharks frequent; mantas","Mantas peak Jul-Oct; viz improving","Peak"),
  "Nov":(28,"Whale sharks (Jul-Nov); mantas around","End SW monsoon; viz improving","Good"),
  "Dec":(28,"Hammerheads Rasdhoo returning; Fuvahmulah tigers; grey reef sharks","NE monsoon: best viz returns 30-40m, calm","Peak"),
 }
}
destinations.append(maldives)

# ---------------- PALAU ----------------
palau = {
 "name":"Palau",
 "currents":"Tidal, strongest at full/new moon; Blue Corner (reef hooks, viz 28m+ incoming), Ulong Channel (high-speed drift), German Channel (gentle, manta cleaning), Peleliu (dangerous down-currents, dry-season only)",
 "months":{
  "Jan":(28,"Moorish idol aggregation (full moon); mantas; grey reef sharks; whale sharks","Dry season; calm; viz >30m; Jellyfish Lake","Good"),
  "Feb":(28,"Snapper & moorish idol spawning (full moon); mantas; grey reef sharks","Coolest; calmest seas; viz 30-40m+","Peak"),
  "Mar":(29,"Grey-reef shark peak begins; bumphead spawning (new moon); mantas","Peak dry season; viz >30m","Peak"),
  "Apr":(29,"Grey-reef shark peak; bumphead spawning; mantas; whale sharks","Best month; calm; viz 30-40m+","Peak"),
  "May":(30,"Grey-reef shark peak; mantas feeding on plankton","Warmest; transition; often calmest","Good"),
  "Jun":(30,"Camouflage grouper spawn (Jun-Aug new moon); mantas; sharks","Wet season begins; warmest water","Good"),
  "Jul":(29,"Grouper spawning; mantas; reef sharks","Wettest month (~400mm); rougher; viz 15-20m","Low"),
  "Aug":(29,"Grouper spawning; mantas; pelagics","Wet; strong W winds; viz reduced","Low"),
  "Sep":(29,"Mantas; reef sharks; pelagics","Wet season; rougher seas","Shoulder"),
  "Oct":(29,"Mantas building; sharks","Transition; winds switching; often calm","Good"),
  "Nov":(29,"Mantas; whale sharks (Nov-Apr); Jellyfish Lake","Dry season returns; calming","Good"),
  "Dec":(28,"Mantas (German Channel); spawning; whale sharks","Dry season; calm; viz >30m","Good"),
 }
}
destinations.append(palau)

# ---------------- GREAT BARRIER REEF ----------------
gbr = {
 "name":"Great Barrier Reef",
 "currents":"Inner reefs mild; outer/Ribbon Reef walls drift dives timed to tides; Coral Sea/Osprey significant currents (North Horn shark feed); SS Yongala strong/severe current - slack tide only",
 "months":{
  "Jan":(30,"Green turtle nesting (Raine Is); reef life","Mid-summer wet; warmest; stinger season; cyclone risk","Good"),
  "Feb":(29,"Turtle nesting/hatching peak; reef life","Late summer wet; warm; stingers; cyclone risk","Good"),
  "Mar":(28,"Reef life; turtles","Early autumn wet tapering; stingers","Good"),
  "Apr":(27,"Reef life; turtles","Autumn; wet tapering; stinger season ending","Good"),
  "May":(26,"Reef life; manta plankton blooms begin; minke season starts","Dry begins; trade winds; reef 'as good as it gets'","Peak"),
  "Jun":(24,"DWARF MINKE WHALES (Ribbon Reefs); humpbacks; mantas","Dry; calm, clear; choppier crossings","Peak"),
  "Jul":(23,"Dwarf minke whales (peak); humpbacks; potato cod","Mid-winter; coldest; best viz; trade winds","Peak"),
  "Aug":(23,"Humpbacks; reef/hammerhead sharks (Osprey); potato cod","Often BEST month: dry, calm, clear; Coral Sea viz 40-100m","Peak"),
  "Sep":(24,"Humpbacks; sharks; potato cod","Early spring dry; calm, clear; fewer crowds","Peak"),
  "Oct":(25,"Reef sharks; potato cod; humpbacks tail","Spring dry; trades easing; calm seas, great viz","Peak"),
  "Nov":(27,"CORAL MASS SPAWNING (after full moon); turtle nesting begins","Late spring; warming; stinger season starts","Good"),
  "Dec":(28,"Green turtle nesting (Raine Is); coral spawning spill","Early summer wet; warm; stingers; cyclone risk","Good"),
 }
}
destinations.append(gbr)

# ---------------- TRUK LAGOON ----------------
truk = {
 "name":"Truk (Chuuk) Lagoon",
 "currents":"Sheltered lagoon - mild to negligible; mild current only on some wrecks/passes; far calmer than open ocean; near-uniform temp surface-to-depth (no thermocline)",
 "months":{
  "Jan":(29,"Coral-encrusted wrecks (266+ fish sp); reef sharks, turtles, rays","Drier season; calm; best viz 24-32m","Peak"),
  "Feb":(29,"Wreck reefs; reef sharks (deep wrecks); turtles","Drier; calm; coolest but ~28C; best viz","Peak"),
  "Mar":(28,"Wreck marine life; sharks, rays, turtles","Drier season; calm seas; good viz","Peak"),
  "Apr":(28,"Wreck reefs; sharks, turtles, occasional manta","Dry sweet spot; calm; viz good","Peak"),
  "May":(28,"Wreck marine life; reef fish schools","Transition to wet; wettest month; choppier","Good"),
  "Jun":(30,"Wreck reefs; sharks, turtles","Wet season; warm; viz 10-18m","Good"),
  "Jul":(29,"Wreck marine life; reef life","Wet; frequent rain; cheaper deals","Good"),
  "Aug":(29,"Wreck reefs; sharks, rays","Wet; windy shoulder; viz lower","Good"),
  "Sep":(29,"Wreck marine life; reef fish","Wet season; choppier surface","Good"),
  "Oct":(29,"Wreck reefs; sharks, turtles","Warm; windy shoulder; viz improving","Good"),
  "Nov":(30,"Wreck marine life; reef life","Among warmest; viz best when not raining","Good"),
  "Dec":(29,"Coral-encrusted wrecks; sharks, turtles, rays","Drier season begins; calm; viz improving","Peak"),
 }
}
destinations.append(truk)

# ---------------- COCOS ISLAND ----------------
cocos = {
 "name":"Cocos Island",
 "currents":"Strong (1-4kt) + surge; advanced & liveaboard-only (~36h crossing); reef-hook hanging at Bajo Alcyone; Dirty Rock sheltered; currents strengthen wet season (Jun-Nov upwelling)",
 "months":{
  "Jan":(28,"Tiger sharks; mobula schools; silky sharks; hammerheads (steady)","Dry: viz >30m, calm crossings; thermocline to ~22C","Good"),
  "Feb":(28,"Tiger sharks; mobula schools; silkies; Galapagos/whitetip sharks","Dry; best viz; calm; warmer","Good"),
  "Mar":(28,"Tiger sharks; mobula schools; dolphins","Dry; viz >30m; calm","Good"),
  "Apr":(29,"Tiger sharks; mobulas; silkies; hammerheads","Warmest; dry; calm; great viz","Good"),
  "May":(28,"Mobula schools tail; whale sharks (plankton rising)","Dry/transition; viz still good","Good"),
  "Jun":(26,"Hammerheads building; whale sharks; mantas","Wet begins; currents strengthen; viz dropping","Peak"),
  "Jul":(25,"Hammerhead schools; whale sharks; mantas","Wet; rougher crossings; green water","Peak"),
  "Aug":(25,"HAMMERHEAD nirvana (100-500+); whale sharks; mantas","Wet peak; thermocline (rare to 6C); viz 10-25m","Peak"),
  "Sep":(25,"Hammerhead peak; whale sharks; mantas","Wet peak; rough; low viz but peak action","Peak"),
  "Oct":(25,"Hammerhead/whale-shark peak; mantas","Wet peak; rough crossings; green water","Peak"),
  "Nov":(26,"Hammerheads tail; whale sharks; mantas","Wet ends; currents easing","Good"),
  "Dec":(27,"Tiger sharks; mobula schools building; silkies","Dry begins; viz improving; calmer","Good"),
 }
}
destinations.append(cocos)

# ---------------- KOMODO ----------------
komodo = {
 "name":"Komodo National Park",
 "currents":"Tidal, strongest at full/new moon; powerful drift; Castle Rock/Crystal Rock (reef-hook pinnacles), Batu Bolong (ferocious flank currents), The Cauldron/Shotgun (committed drift); downcurrents at pinnacles. N warm/calm, S cold upwelling/rough",
 # Komodo temps: store as "N/S"
 "months":{
  "Jan":("29 / 26","South mantas PEAK (Manta Alley); hammerheads (south); macro explosion","Wet; lower viz (5-15m), choppier north; Dec can be 30m+","Good"),
  "Feb":("29 / 26","South manta PEAK (Jan-Feb); macro (Rhinopias, frogfish); hammerheads","Wet; lower viz; southern manta aggregations largest","Good"),
  "Mar":("29 / 25","South mantas; hammerheads (to early Apr); rich macro","Wet tapering; viz improving","Good"),
  "Apr":("28 / 25","N/Central mantas active; whale sharks (Apr-Jun); reef sharks","Dry begins; SWEET SPOT; manageable currents","Peak"),
  "May":("28 / 25","N/Central mantas; whale sharks; reef sharks","Dry; SINGLE BEST MONTH; clear, calm, fewer crowds","Peak"),
  "Jun":("28 / 23","N/Central mantas; whale sharks; reef sharks","Dry; clear; upwelling builds south","Peak"),
  "Jul":("27 / 21","N mantas; reef sharks; mola season nears","Dry; best N viz; peak cold upwelling south; busy","Peak"),
  "Aug":("27 / 20","MOLA MOLA peak (south stations); N mantas; reef sharks","Dry; N viz up to 30m; south cold/green; busiest","Peak"),
  "Sep":("27 / 22","Mola mola; N/Central mantas; reef sharks","Dry; great N viz; upwelling south","Peak"),
  "Oct":("28 / 24","Mola tail; N mantas (Karang Makassar); reef sharks","Dry ends; calm; good viz","Peak"),
  "Nov":("28 / 25","South mantas building (Manta Alley); reef sharks","Wet begins; viz lowering","Good"),
  "Dec":("29 / 26","South manta peak begins; macro; reef sharks; dragons active","Wet; lower viz but can be 30m+; choppier north","Good"),
 }
}
destinations.append(komodo)

# ---------------- BUILD CSV (only when run directly) ----------------
# IMPORTANT: build_master.py imports this module for `destinations` only.
# The legacy 11-destination CSVs below would overwrite the published
# 83-destination CSVs at import time, so they are gated behind __main__.
def _write_legacy_csvs():
    rows = []
    # We iterate period order: for each month, early then late, but to keep a single "Destination then period" sort
    # the user can sort however; we'll output Destination-major, period order.
    for d in destinations:
        pno = 0
        for mi,m in enumerate(MONTHS):
            temp,life,cond,rating = d["months"][m]
            for half in ["early","late"]:
                pno += 1
                rows.append({
                    "Period_No": pno,
                    "Month": m,
                    "Half": half,
                    "Destination": d["name"],
                    "Water_Temp_C": temp,
                    "Currents": d["currents"],
                    "Marine_Life_Highlights": life,
                    "Conditions_Visibility": cond,
                    "Rating": rating,
                })

    cols = ["Destination","Period_No","Month","Half","Water_Temp_C","Rating","Marine_Life_Highlights","Conditions_Visibility","Currents"]
    out = os.path.join(_ROOT, "diving-calendar-24-periods.csv")
    with open(out,"w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k:r[k] for k in cols})

    print("Wrote", len(rows), "rows to", out)

    # ---------------- BUILD PIVOT GRID (24 periods x destinations) ----------------
    periods = []
    for mi,m in enumerate(MONTHS):
        for half in ["early","late"]:
            periods.append((m,half))

    grid_cols = ["Period_No","Month","Half"] + [d["name"] for d in destinations]
    out2 = os.path.join(_ROOT, "diving-calendar-grid.csv")
    with open(out2,"w",newline="") as f:
        w = csv.writer(f)
        w.writerow(grid_cols)
        for i,(m,half) in enumerate(periods, start=1):
            row = [i,m,half]
            for d in destinations:
                temp,life,cond,rating = d["months"][m]
                row.append(rating)
            w.writerow(row)
    print("Wrote pivot grid to", out2)

if __name__ == "__main__":
    _write_legacy_csvs()
