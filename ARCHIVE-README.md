# archive/unmerged-work

Rescue branch (2026-07-15): the unique files from old orphan branches that
never reached `main`, preserved here so the branches themselves could be
deleted. Nothing on this branch is deployed.

| Rescued from | Files | What it is |
|---|---|---|
| `claude/dive-trip-travel-agency-3zkhpi` | `drafts/articles/*.md` (7 destination articles: Egypt/Red Sea, GBR, Indonesia, Maldives v2, Mexico, Thailand, Zanzibar), `serverless/trip-concierge/*`, `trip-planner.json` | Unpublished article drafts + a trip-concierge Cloudflare-worker prototype |
| `claude/diving-destinations-global-klljx1` | `assets/gear/studio/hero/*.jpg` (16) | Gear colour-variant studio photos for the unfinished colour-swatch feature |
| `claude/3d-mask-prototype-video-rc2cne` | `assets/prototype-mask/*` (4) | 3D scuba-mask hologram prototype (scene + capture script + rendered webm) |
| (several old branches) | `diving-calendar-24-periods.md`, `map-A-osm-tiles.html`, `map-B-vector-offline.html` | Dead early prototypes, kept only for the record |

To resume any of this work: branch from `main`, `git checkout archive/unmerged-work -- <path>`.
