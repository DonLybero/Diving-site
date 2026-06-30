# Metadata for the original 11 destinations, to convert build_csv.py data into the
# website JSON schema. Keyed by the name used in build_csv.py.
META11 = {
 "Red Sea (Egypt)": dict(
   country="Egypt", region="Red Sea / Middle East", water_type="tropical",
   difficulty="beginner-advanced", access="shore/day-boat/liveaboard",
   best_months="Mar-May & Sep-Nov", wetsuit="3mm summer / 5-7mm winter",
   signature_species=["oceanic whitetip shark","scalloped hammerhead","whale shark","manta ray","spinner dolphin"],
   highlights="Year-round reefs & wrecks; offshore shark reefs (Brothers/Daedalus/Elphinstone)."),
 "Seychelles": dict(
   country="Seychelles", region="Indian Ocean", water_type="tropical",
   difficulty="beginner", access="shore/day-boat/liveaboard",
   best_months="Apr-May & Oct-Nov", wetsuit="3mm",
   signature_species=["whale shark","manta ray","hawksbill turtle","reef shark","eagle ray"],
   highlights="Granite-boulder reefs; whale shark season Aug-Nov; calm transition-month diving."),
 "Raja Ampat": dict(
   country="Indonesia", region="Coral Triangle / SE Asia", water_type="tropical",
   difficulty="intermediate", access="liveaboard/resort",
   best_months="Oct-Apr (Dec-Feb peak)", wetsuit="3mm",
   signature_species=["manta ray","wobbegong shark","walking (epaulette) shark","pygmy seahorse"],
   highlights="Most biodiverse reefs on Earth; manta peak Dec-Mar."),
 "Galapagos Islands": dict(
   country="Ecuador", region="Eastern Pacific", water_type="temperate-tropical",
   difficulty="advanced", access="liveaboard",
   best_months="Jun-Nov (big animals) / Dec-May (calm)", wetsuit="5-7mm + hood/gloves",
   signature_species=["whale shark","scalloped hammerhead","Galapagos shark","sea lion","marine iguana","mola mola"],
   highlights="Big-animal mecca; whale sharks & hammerhead schools at Darwin/Wolf."),
 "Sipadan Island": dict(
   country="Malaysia", region="Celebes Sea / SE Asia", water_type="tropical",
   difficulty="intermediate", access="day-boat (permit required)",
   best_months="Mar-Jun & Sep-Oct (CLOSED November)", wetsuit="3mm",
   signature_species=["green turtle","hawksbill turtle","chevron barracuda","bumphead parrotfish","reef shark"],
   highlights="Turtle & barracuda-tornado wall; island closed every November."),
 "Maldives": dict(
   country="Maldives", region="Indian Ocean", water_type="tropical",
   difficulty="beginner-intermediate", access="liveaboard/resort",
   best_months="Dec-Apr (clear water) / May-Nov (mantas & whale sharks)", wetsuit="3mm",
   signature_species=["manta ray","whale shark","grey reef shark","scalloped hammerhead","tiger shark"],
   highlights="Monsoon-driven channel drifts; Hanifaru manta aggregation Jul-Oct."),
 "Palau": dict(
   country="Palau", region="Micronesia / Pacific", water_type="tropical",
   difficulty="intermediate-advanced", access="day-boat/liveaboard",
   best_months="Dec-Apr (Feb-Apr peak)", wetsuit="3mm",
   signature_species=["grey reef shark","manta ray","bumphead parrotfish","spawning red snapper","whale shark"],
   highlights="Blue Corner drift & reef-hook diving; lunar spawning aggregations."),
 "Great Barrier Reef": dict(
   country="Australia", region="Coral Sea / Australia", water_type="tropical",
   difficulty="beginner", access="day-boat/liveaboard",
   best_months="Jun-Oct", wetsuit="3mm summer / 5mm winter",
   signature_species=["dwarf minke whale","potato cod","green turtle","reef shark","manta ray"],
   highlights="World's largest reef; dwarf minke whales Jun-Jul; coral spawning Nov."),
 "Truk (Chuuk) Lagoon": dict(
   country="Micronesia (FSM)", region="Micronesia / Pacific", water_type="tropical",
   difficulty="intermediate-advanced (wrecks)", access="liveaboard",
   best_months="Dec-Apr", wetsuit="3mm (5mm for deep repeats)",
   signature_species=["WWII wrecks (artificial reef)","reef shark","turtle","eagle ray"],
   highlights="World's premier WWII wreck dive; 50+ ships in a calm lagoon."),
 "Cocos Island": dict(
   country="Costa Rica", region="Eastern Pacific", water_type="tropical-temperate",
   difficulty="advanced", access="liveaboard",
   best_months="Jun-Nov (hammerheads) / Dec-May (visibility)", wetsuit="5-7mm + hood",
   signature_species=["scalloped hammerhead","whale shark","tiger shark","mobula ray","silky shark"],
   highlights="Hammerhead-school mecca; remote 36h crossing, strong currents/thermoclines."),
 "Komodo National Park": dict(
   country="Indonesia", region="Coral Triangle / SE Asia", water_type="tropical",
   difficulty="intermediate-advanced", access="liveaboard/day-boat",
   best_months="Apr-Oct (May best) / Dec-Feb (south mantas)", wetsuit="5mm",
   signature_species=["manta ray","mola mola","reef shark","macro critters"],
   highlights="Strong tidal drifts; warm north vs cold-upwelling south; mantas year-round by zone."),
}
