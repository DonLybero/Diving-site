# DiveSZN Growth Plan — 12-Month Roadmap

**Goal:** make DiveSZN one of the leading diving websites. **Owner:** solo. **Constraints:** static site, no backend, GitHub Pages, everything published is real and researched.

## Positioning

DiveSZN's edge is the one asset no incumbent has: 1224 comparable, scored destination-months across 102 destinations and 725 named sites, with a published formula. Every competitor season page is prose written by someone selling the trip — Liveaboard.com's calendar is a lead-gen veneer, ZuBlu's finder is a lead form, PADI's ratings aren't comparable across destinations. DiveSZN holds no inventory and books nothing, so independence is a positioning claim none of them can copy without breaking their business model. The strategy: expose the dataset as crawlable, extractable pages at every query intersection (destination × month × species), make the planner queryable and re-visitable, and monetize in trust order — gear affiliate first, stay/liveaboard links second — while measuring everything with free, cookieless tools.

## Fix the foundation (before growth work)

A verified technical audit has run; findings are listed separately under six categories. Work through them in this order, because everything below inherits from them:

1. **session-code** — correctness defects in `index.html` / `diving-calendar.js` / build scripts. Broken engine behavior undermines the "transparent scoring" claim; fix first.
2. **seo** — crawlability, metadata, canonical/sitemap issues. Prerequisite for the entire programmatic plan; a page generated onto a broken SEO base is wasted build work.
3. **perf** — page weight and load path. "Best time to dive X" queries lose ~37% CTR to AI Overviews already; slow pages forfeit the remainder.
4. **a11y** — the tonal palette, tab interactions, and data tables must work for keyboard and screen-reader users; also a quiet ranking factor.
5. **brand** — palette-sync drift (the TONAL maps in `index.html` and `build_pages.py`), coral misuse, editorial-rule violations. Trust density is the revenue ceiling; inconsistency spends it.
6. **ux-flows** — planner → destination → buy/stay paths. These are the conversion routes every later item feeds.

Timebox: two focused weeks. Nothing in "Now" ships until session-code and seo are clear.

## Now (this month)

**1. Complete the launch checklist as one batch: company → domain → affiliate programs.** The `AFFILIATE` config exists but every ID is empty — 346 buy links currently earn nothing. Register diveszn.com, apply to Awin (Tradeinn ~5%), AvantLink, Dive Right In (5%, 30-day cookie), Amazon Associates, eBay EPN; paste IDs; rebuild the standalone. Critically, port `affLink()` into `build_pages.py` so the 124 static gear pages — the crawlable, rankable surface — stop linking raw retailer URLs. Every month of SEO work before this is done sends traffic to unmonetized links.

**2. Ship cookieless outbound-click analytics.** Cloudflare Web Analytics or GoatCounter (both free, no consent banner) plus a click event on every `rel="sponsored"` link tagged `{retailer, item, page-type}` and every "Stays near…" link tagged `{destination, month}`. This baseline decides where 6-month effort goes; without it, "success = affiliate revenue" is unmeasurable.

**3. Register the diveszn.com domain property in Search Console** the day DNS resolves, and submit the regenerated sitemap.

**4. Verdict sentences + structured data.** Add one machine-generated, extractable sentence per destination-month ("March in Socorro: Peak — 26°C, 30m visibility, humpbacks and giant mantas") to all 102 destination pages and 12 month hubs, generated from the canonical JSON so it never drifts. Add `Dataset`, `FAQPage`, and `BreadcrumbList` JSON-LD in `build_pages.py`. Travel AI Overview presence grew +381% after the March 2025 core update, and AIOs cite structured month data, not paragraphs — this is the cheapest high-leverage move on the list.

## 90 days

Generator sprints first (one build, hundreds of pages), then the two front-end features that make the data shareable.

**5. "Best time to dive [destination]" pages — 102 pages from `build_pages.py`.** The highest-intent query family is held by commercially conflicted prose (Liveaboard.com, individual operators). Emit `best-time/<slug>.html`: 12-month tonal calendar, per-month verdict sentences, computed best/shoulder/avoid windows, visible score breakdown, FAQ schema. Link each from its destination page and its top-3 month hubs.

**6. Month hubs become queryable, not listicles.** The "where to dive in [month]" SERP is rotating 5-item listicles (scubadiving.com, PADI Blog) with no persistent tool. Upgrade the 12 `months/*.html` pages to full scored rankings of all non-Closed destinations, with region and marine-life sub-sections rendered from the existing keyword matching. Refresh titles annually with the year — ZuBlu's Dive Annual proves the pattern.

**7. Internal-linking spine.** Destination page → its best-time page, top-3 month hubs, and species pages; species pages → their strongest month×destination cells; regenerate the sitemap. Topical authority is the solo-site substitute for PADI's domain authority. Target: zero orphan pages, every page ≤3 clicks from home.

**8. Destination Compare (2–3 side-by-side, month-by-month).** Nobody lets divers compare Raja Ampat vs Komodo vs Tubbataha with visible scores. Reuse the shipped gear-compare pattern; write compare state to the URL so links are shareable — ScubaBoard threads are the demand signal, and shared compare URLs are how DiveSZN enters them without posting a word itself.

**9. "My Season" shortlist via localStorage + URL.** A diver pins four destinations; every revisit shows their calendar strip first. Zero backend, and it converts one-shot search traffic into the return visits that make a planner a habit.

**10. Liveaboard/stay module on destination pages.** `liveaboard_aff` is configured but has no consumer — the 10–20%-commission category has zero surface. Add a quiet "Book this season" module below the season calendar (coral CTA per brand rules; the data earns the click first).

## 6 months

**11. Species × month matrix (Encounter Files v2).** Marine-life-first planning is split across PADI/Girls-that-Scuba-style listicles with no matrix product. Expand the 9 species pages with a sortable destination × 12-month pulse table, then generate "[Species] in [Month]" pages only where data supports ≥3 destinations — concrete or silent, no thin cells. Grow species coverage toward 15–20 (hammerheads, thresher, mola mola already exist as keywords). These long-tails convert to booking clicks best.

**12. Shoulder-season franchise — modules first, pages only if they earn it.** The value angle ("still good, cheaper, emptier") is unserved and matches the fewer-but-longer-trips trend. Sequence to resolve the drafts' conflict: (a) a "value windows" toggle in the planner (engine flag kept identical in `diving-calendar.js` and `build_rankings.py`); (b) a computed "still-good months" module inside each existing month hub, with stay CTAs — reuse hub authority rather than diluting it; (c) standalone regional shoulder pages only if the modules show clicks and rankings after a quarter.

**13. Wetsuit-by-temperature recommender.** Per-month temps and the wetsuit field already exist. "Galápagos in August → 7mm → cheapest-first table" is the only feature that connects planner intent directly to the 346 buy links; no competitor bridges season data and gear commerce.

**14. Publish the independence claim.** Extend `how-we-score.html` into "How we make money": no inventory, no bookings, same earnings whether you pick Peak or Shoulder. Link it from every buy box. Affiliate disclosure written as a trust asset, not fine print.

**15. Linkable-asset program.** Offer the season grid CSV (already built) on a "Data" page with a citation line; pitch it to dive clubs and travel-data roundups. divingseasons.com — the closest pure-data competitor — is a low-authority blog; this is where DiveSZN takes "dive season calendar." Target +20 referring domains. (The third-party-naming rule governs site copy, not outreach email.)

**16. "Best diving in the world" flagship.** One annually refreshed page built from `diving-rankings.json` with the methodology visible, linking every destination. The SERP is soft — only Bluewater has a defensible list — and this is the natural link-earning target for item 15's outreach.

**17. Return hooks without a backend.** Per-destination `.ics` files ("Peak season opens — add to calendar") and an RSS feed for month hubs, generated at build time. Zero ops, and the only alert mechanism a static site can honestly run.

## 12 months

**18. Dive-site pages, staged.** Generate pages for the top ~150 of 725 sites where data is rich (depth, level, character, parent seasonality), batching ~25/month, starting with the destinations analytics shows earning traffic. Site-level queries are operator-held and thin; 725 researched sites is the moat competitors can't script. Extend toward site-level seasonality (which sites work in which months) as research hours allow — pure labor, exactly what a scored-data brand defends.

**19. Trip-window optimizer.** "10 days in November, medium budget, want mantas" → ranked windows across all 1224 destination-months, URL-shareable. This is the tool ScubaBoard threads prove nobody built, and it feeds stay links directly.

**20. Curated liveaboard/stay listings inside the Dive Planner**, held to gear-guide research standard: per-destination, per-season, cheapest-first, quiet ink-mono prices. Converts the product people actually use into the primary booking surface.

**21. Gear comparison SERP play.** `Product`/`Offer` schema on gear pages plus "best [category] under $X" cut pages from existing data — the gear SERP is single-retailer affiliates and ad-heavy magazines; nobody shows honest cross-retailer prices.

**22. Quarterly ritual, permanent:** price refresh, `check-buy-links.yml` dead-link triage, verdict-sentence review, annual title refresh on hubs and the flagship, and a revenue read-through (clicks × program EPC by surface). Kill or double down per surface on the data.

## What NOT to do

- **No backend, accounts, or email capture infrastructure.** Every feature above works statically; the moment ops exist, the solo model breaks.
- **No display ads or sponsored posts.** They fund scubadiving.com and destroy its UX; independence is the product.
- **No paid acquisition.** The dataset compounds; ad spend doesn't.
- **No thin pages.** Skip species-months with fewer than 3 destinations, sites without rich data. Concrete or silent.
- **No forum or community build-out.** Participate in existing ones via shareable URLs instead.
- **No new destinations before depth.** 102 well-scored beats 150 shallow; expand only after site-level work proves out.
- **Honor the editorial rules throughout:** scuba only, no third parties named in site copy, no destination counts in taglines, prices in quiet ink mono, coral only for buy/booking CTAs.

## Measurement (free tier only)

**North star:** monthly affiliate revenue. **Leading indicators**, in causal order:

| What | Tool | Cadence |
|---|---|---|
| Outbound buy/stay clicks by `{page-type, retailer/destination, month}` | Cloudflare Web Analytics or GoatCounter custom events (free, cookieless) | Weekly |
| Non-brand impressions and position for "best time to dive X", "best diving in [month]" | Google Search Console, diveszn.com domain property (free) | Weekly |
| Indexed page count vs generated page count | Search Console coverage report | Monthly |
| AIO/featured-snippet citations for 10 tracked queries | Manual SERP spot-check (incognito, logged sheet) | Monthly |
| Referring domains | Search Console links report | Monthly |
| Returning-visitor share, shortlist adoption, compare-URL entrances | Analytics events | Monthly |
| Dead buy links | Existing `check-buy-links.yml` GitHub Action | Continuous |
| Affiliate EPC by program and surface | Program dashboards (Awin, AvantLink, Amazon) | Quarterly |

Decision rule: any surface (page type or feature) that shows no click growth after two quarters of full deployment gets frozen; effort moves to the best-performing surface. The first 30 days of click data — gear pages vs destination pages vs planner — set the priority weighting between items 11–17.

---

## Appendix — July 2026 audit backlog (not yet fixed)

Confirmed but deferred (need network access or an owner decision):

- **P0 (a11y)** Gear compare modal has no focus management, dialog semantics, or Escape handling: opening leaves keyboard focus behind the overlay, there is no focus trap, no focus return to the trigger, no role="dialog"/aria-modal, and
- **P2 (perf)** All 102 destination static pages hotlink their single hero image from upload.wikimedia.org (960px, eager-loaded, no width/height attributes) — a third-party DNS+TLS handshake on the critical path of every SEO landing page
- **P2 (seo)** Destination hero images, og:image and JSON-LD image all hotlink upload.wikimedia.org (homepage og:image too), so rich-result/image-search eligibility depends on a third-party host that rate-limits hotlinking, and image-s
- **P2 (brand)** Brand contract vs implementation mismatch on the revenue CTA color: docs mandate coral #ff7a59 strictly for buy/booking CTAs (the primary success metric per PRODUCT.md), but coral exists nowhere in the codebase — buy/boo
- **P0 (ux-flows)** The primary money CTA ('Stays near X' booking link) is styled as the visually weakest element on every planner and search result card - muted gray, 13px, weight 500, 20px tall - while the secondary 'Full guide' link righ
- **P1 (ux-flows)** On destination pages the only booking link sits 56-59% down the page (absTop 2211/3982px desktop, 3793/6467px mobile for fuvahmulah.html) with nothing above the fold and no sticky/repeat CTA; it is also styled identicall

P3 findings (unverified, fix opportunistically):

- (session-code) The pin runway is recomputed from window.innerHeight on every scroll event, so on mobile the URL-bar collapse/expand changes innerHeight mid-scroll and mutates the pin wrapper's he
- (perf) assets/gear/ ships 39 MB to the GitHub Pages artifact but the site only references assets/gear/studio/*.jpg (~100-130 KB each); the top-level original PNGs — including zeagle-range
- (seo) sitemap.xml stamps <lastmod> with today's date on all 236 URLs every build, so every page always claims to have changed today — Google learns to distrust the signal and freshness p
- (seo) og:image is missing on all months/, gear/ and marine-life/ pages (destinations have it), so shares and Discover surfacing for the highest-commercial-intent hub pages render without
- (seo) Gear Product JSON-LD omits "brand" (a standard Search Console warning that suppresses merchant-listing eligibility) even though the brand is the first word of every product name an
- (seo) diving-site.html (the full offline single-file app) is deployed and crawlable at /Diving-site/diving-site.html with a title identical to the homepage; its canonical→/ mitigates dup
- (data) Third-party org names PADI and DAN live in gear-guide.json (YouTube channels list); not rendered on any page today, but the data ships embedded in diving-site.html (__GEAR_DATA__) 
- (data) Scoring parity VERIFIED identical today (constants RATING_BASE/BONUS_CAP=25/VIZ 5-35-18, the 34-entry marine weight table, and longest-first consume-on-match logic all match; empir
- (data) Clean-bill items from the requested checks (documented so they are not re-audited): no missing/null monthly temps or visibility, no curly apostrophes/quotes, no specs saying 'Both'
- (brand) A third hard-coded copy of the tonal palette lives in the map legend HTML, outside the RCOLOR map that the code comment declares the app's ONLY source for rating colors — currently
- (brand) Season pulse and ribbon fall back to an invented non-palette gray #94a3b8 for unrecognized rating words, contradicting the 'never invent new rating colors' rule; build_pages.py use
- (brand) Retail price table colors prices with an off-token teal instead of the mandated quiet ink mono — not coral (the hard rule holds), but tinted and using a hex that matches no design 
- (brand) The .crew-credit pattern renders a visible attribution string directly on the crew photo (contradicting tooltip-only attribution), and .gear-rank requests font-weight:800 which no 
- (ux-flows) Search tab dead ends: an unmatched query shows only 'No matches.' with no reset, no suggestions and no link to browse - the planner empty state got a Reset button this session but 
- (ux-flows) Hero headline, tagline and CTA are invisible for 1.35-1.75s on every Home load (heroRise animation delays), so repeat visitors and slow-connection users stare at the video band wit
- (monetization) The homepage's pinned stats slide (this session's count-up work) sits between the hero CTA and the first conversion content, adding a full pinned-scroll interlude before the 'Where
- (monetization) Marine-life 'Book →' trip links go to GetYourGuide, a network absent from the AFFILIATE config entirely — a monetized-looking CTA (already rel=sponsored) with no affiliate program 
