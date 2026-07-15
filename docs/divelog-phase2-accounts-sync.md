# DiveSZN Dive Log — Phase 2: accounts + sync

**Status:** approved direction (owner, 2026-07-15) · implementation **blocked on
the launch checklist** (company + diveszn.com domain — HANDOFF §9) · builds on
`docs/divelog-prd.md` (v1, client-side) without rewriting any of it.

## 1. Why (the one-paragraph case)

The dive log exists because divers switching computers lose their history to
brand silos — a real, recurring pain that peaks at the exact moment a diver is
buying a new dive computer (DiveSZN's highest-intent affiliate audience). v1
solves the *rescue*; Phase 2 makes DiveSZN the *permanent home*: an account
turns "I fixed my problem once" into "this is my logbook", with cross-device
sync and a backup that survives a cleared browser. Registered, returning
divers are the audience the whole site monetizes.

## 2. Goals

1. A visitor can use the dive log exactly as today with **no account** — signing
   in is an upgrade, never a wall. (This deliberately diverges from the v1
   draft's "feature requires login"; the tool's acquisition power is its zero
   friction at the migration moment.)
2. Signing in syncs the logbook to the account: same dives on laptop and phone,
   surviving device loss and cleared browser data.
3. Original uploaded files are stored (privately) with each import, so improved
   parsers can re-run on originals later.
4. Every unsupported-format rejection is logged (format guess + the app name
   the user volunteers) — the parser roadmap, ranked by real demand.
5. One person can run it: managed services only, no servers to patch.

## 3. Non-goals (Phase 2)

- No social features, no public profiles (dives stay `visibility: 'private'`;
  the field exists for later).
- No native app. The PWA (manifest + offline shell) ships alongside Phase 2;
  native waits for retention numbers that justify it.
- No paid tier. No deco/planning tools (safety liability — permanent non-goal).

## 4. Architecture

**Stack:** Supabase (EU region — Frankfurt or London; UK/EU audience) for
auth + Postgres + file storage. The static site stays on GitHub Pages; the
dive log page talks to Supabase directly from the browser via `supabase-js`
(vendored like Leaflet/fxp) — **no app server at all**. Row-Level Security is
the authorization layer.

**Auth:** Supabase Auth with email magic link + Google. No passwords ever.
Requires the real domain (magic-link emails from `@diveszn.com`, OAuth redirect
URLs) — hence blocked on the launch checklist.

**The swap point (already built):** `lib/divelog/store.js` defines the store
interface; v1 ships `IndexedDBStore` + `MemoryStore`. Phase 2 adds
`SyncedStore`, which wraps the local store — parsers, pipeline, dedupe and UI
do not change. That was the whole point of the interface.

### Local-first sync model

IndexedDB remains the source the UI reads — instant loads, fully offline
(dive boats have no signal). Sync reconciles in the background:

- Every dive row carries `updatedAt` (server timestamp on write) and
  `deletedAt` (tombstone). Client keeps a `lastSyncedAt` cursor.
- **Push:** local changes queue in an `outbox` object store; flushed on
  reconnect/interval. **Pull:** `select … where updated_at > lastSyncedAt`.
- **Conflicts:** last-write-wins per dive (single-user data; the realistic
  conflict is "edited on phone, then on laptop" — LWW matches expectation).
  Duplicate protection on merge reuses `findDuplicates()` so the same dive
  imported on two devices before first sync collapses cleanly.
- Sign-in with an existing local log → one-time merge (same dedupe pass),
  preview shown before anything uploads. Sign-out → local copy stays unless
  the user chooses "remove from this device".

### Postgres schema (RLS: `user_id = auth.uid()` on every table)

```
dives    (id uuid pk, user_id, payload jsonb,          -- CanonicalDive verbatim
          started_at timestamptz generated for indexing,
          updated_at timestamptz, deleted_at timestamptz)
imports  (id uuid pk, user_id, file_name, parser_id, counts jsonb,
          original_path text,                          -- Supabase Storage object
          created_at, updated_at)
rejections (id, user_id nullable, detected text, ext text, app_hint text,
          created_at)                                  -- the format-demand log
settings (user_id pk, payload jsonb, updated_at)       -- units, csv mappings
```

`payload jsonb` keeps the canonical model authoritative in one place (the JS
types), avoids column churn as parsers grow, and the v1 decision "samples
inline on the dive" carries straight over. Typed columns exist only where the
server needs to index/filter.

**Storage:** bucket `import-originals`, path `user_id/import_id/filename`,
private; signed URLs only; 20 MB object cap (matches the parse cap).

**GDPR:** account deletion = one RPC that deletes rows + storage objects, then
the auth user. Export-everything = the UDDF download that already exists.
Privacy policy gains an accounts section (entity name comes from the company —
same launch batch).

## 5. UX changes (small on purpose)

- Logbook header gains a quiet "Sign in to sync" (signed out) / account menu
  with sync status dot (signed in). No other layout changes.
- First sign-in with local dives → merge preview ("14 dives here, 212 in your
  account — 3 duplicates collapse"). Import/commit flow is untouched.
- Unsupported-format rejection message gains an optional one-field form:
  "which app made this file?" → `rejections` row. No email, no friction.

## 6. Sequencing & effort

| Step | Depends on | Size |
|---|---|---|
| 1. Supabase project (EU), schema + RLS migrations, buckets | company + domain (launch batch) | half-day |
| 2. Vendored supabase-js + auth UI (magic link, Google) | 1 | 1 session |
| 3. `SyncedStore` + outbox + merge-on-signin, against MemoryStore-style contract tests | 2 | 1–2 sessions |
| 4. Original-file upload on commit; rejections logging | 2 | half-session |
| 5. PWA shell (ships independently — no backend needed) | nothing | half-session |
| 6. Privacy policy + account-deletion flow | 1, entity name | half-session |

**Success metrics** (unchanged from v1 PRD §12, now measurable): accounts
created via the dive log entry point; % of visitors completing ≥1 import;
import success rate ≥ 80%; rejection log = parser roadmap. Retention (90-day
returning rate of logbook owners) is the number that later decides the native
app question.

## 7. Decisions taken here (so session 1 doesn't relitigate)

1. **Anonymous-first, account-optional** — reversal of the v1 draft's
   login-required stance, deliberate (see §2.1).
2. **No app server** — supabase-js direct from the browser + RLS. If a real
   server becomes necessary (webhooks, heavy re-parsing), it slots behind the
   same store interface later.
3. **LWW conflicts, per dive** — CRDTs are overkill for single-user data.
4. **`payload jsonb`** over wide columns — canonical model lives in JS.
5. **Sync unit = whole dive** (samples included). A 360-point profile is a few
   KB; not worth a samples table until proven otherwise.
