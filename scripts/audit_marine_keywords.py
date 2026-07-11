#!/usr/bin/env python3
"""Audit the marine-life keyword matching that drives every "where & when"
surface (app ledger/pulse, static species pages, marine index counts).

For each species in marine-life.json it prints every (destination, month,
matched keyword, full monthly marine_life sentence) hit produced by the exact
matching rule the site uses (case-insensitive plain substring — mirror of
marineWhereWhen()/marinePulse() in index.html and where_when()/marine_pulse()
in scripts/build_pages.py).

It also flags SUSPECT hits where the keyword only matches inside a longer
word (no word boundary), e.g. 'mola' inside 'Molasses' or 'orca' inside
'Mallorca' — those are false positives to review by eye.

Read-only: this script never edits data. If it surfaces a bad monthly string,
fix it in a separate commit and rebuild rankings with a zero-diff check
(monthly strings feed the scoring engine).

Usage:  python3 scripts/audit_marine_keywords.py [--suspect-only]
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    suspect_only = "--suspect-only" in sys.argv
    with open(os.path.join(ROOT, "marine-life.json"), encoding="utf-8") as f:
        experiences = json.load(f)["experiences"]
    with open(os.path.join(ROOT, "diving-destinations.json"), encoding="utf-8") as f:
        dests = json.load(f)["destinations"]

    total = suspects = 0
    for exp in experiences:
        kws = [k.lower() for k in exp["keywords"]]
        print(f"\n=== {exp['slug']}  (keywords: {', '.join(exp['keywords'])}) " + "=" * 30)
        hits = 0
        for d in dests:
            for m in MONTHS:
                text = (d["monthly"][m].get("marine_life") or "")
                low = text.lower()
                matched = [k for k in kws if k in low]
                if not matched:
                    continue
                hits += 1
                total += 1
                # word-boundary sanity: a substring hit that isn't the word
                # itself (plurals allowed) is suspect — e.g. 'mola' in
                # 'Molasses', 'orca' in 'Mallorca'
                loose = [k for k in matched
                         if not re.search(r"\b" + re.escape(k) + r"(?:e?s|'s)?\b", low)]
                flag = " !! SUSPECT (substring-only match)" if loose else ""
                if loose:
                    suspects += 1
                if suspect_only and not loose:
                    continue
                print(f"  {d['name']:<34} {m}  [{', '.join(matched)}]{flag}")
                print(f"      \"{text}\"")
        print(f"  -- {hits} destination-month hits")
    print(f"\nTOTAL: {total} hits across {len(experiences)} species; "
          f"{suspects} suspect (substring-only) — review those by eye.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
