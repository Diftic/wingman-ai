# SC Navigator - Development Log

## Version: 4.9.0.0 (2026-07-18)

All four SC skills aligned to game version 4.9.0 by user decision; VERSION and skill_installer_config.json bumped to 4.9.0.0, SC_TARGET_VERSION and __sc_target_version__ to 4.9.0. The bundled location dataset was already the 4.9.0-LIVE extraction; this is the formal version-line move. In-game requalification against 4.9.0 is still pending.

## Version: 4.8.0.2 (4.9.0 dataset refresh, 2026-07-18)

The data is now the scunpacked-data `starmap_positions.json` extraction tagged
`4.9.0-LIVE.12232306` (commit `4764726896973204a798325ed0f9ed7253e995e5`),
curated to quantum-travel destinations with distances computed at runtime.
Version stays on the 4.8.0 line (dataset-source update only; no in-game
requalification against 4.9.0 has happened yet); within-patch updates append a
dotted suffix (4.8.0.3, ...). See [`skills/Versioning.md`](../Versioning.md).

**CAVEAT.** The geometry is the 4.9.0-LIVE extraction (changelist 12232306); the
current live game is the 4.9.0 hotfix (changelist 12248363), so the extraction
trails the installed build by one hotfix. Computed straight-line distances have
NOT been validated in-game yet. Treat them as best-available estimates until an
in-game check is done. The version stays on the 4.8.0 line per Versioning.md
because no in-game requalification against the current live patch has happened;
the rename to a 4.9.x.x line happens at formal requalification, not on a
data-source refresh.

## 2026-07-18 - Dataset refresh to 4.9.0 (4.8.0.2)

Refreshed the location dataset from the scunpacked-data 4.9.0 dump and bumped the
within-patch suffix to 4.8.0.2. Only `build_locations.py`'s `SOURCE_COMMIT` and
`GAME_VERSION` changed; `SYSTEM_DISPLAY` and `EXPECTED_LINKS` stayed as-is
because 4.9.0 adds no new star systems.

**Source.** commit `4764726896973204a798325ed0f9ed7253e995e5`, game version
`4.9.0-LIVE.12232306` (upstream dump dated 2026-07-16). Input sha256
`7d3001d3c4f6bfde4816abd93e59bb3d9f28e0bbe17f5e94911e897fc8c83232`. The prior
4.8.0-LIVE.11875683 dataset was copied aside before rebuilding.

**Counts.** 1774 entities read, 531 kept (was 522). Stanton 386 (+1: `UGF_OldSecDep`),
Pyro 127 (no change), Nyx 18 (+8: five `QV Breaker Station BRK-*` and three
`Transit Point Glaciem Alpha/Bravo/Charlie`). No locations removed. Every
location present in both versions kept identical coordinates (zero drift over
1000 m), so this is a pure addition, not a geometry shift. Gateway topology
unchanged: the same three system pairs (Stanton<->Pyro, Stanton<->Nyx,
Pyro<->Nyx), so the `EXPECTED_LINKS` tripwire passed.

**Propagation.** `update_release.py` refreshed `release_version/` (data +
version-bumped `__init__.py`/`main.py`); the AppData live install got the new
`data/sc_locations.json` plus `__init__.py`/`main.py` version bumps by hand.
Verified `data/sc_locations.json` byte-identical across dev, release_version, and
live install. Version bumped 4.8.0.1 -> 4.8.0.2 in dev/release/live
`__init__.py` and `main.py`, and in the dev `skill_installer_config.json`.

**Verification.** Full suite green: `python -m pytest skills/sc_navigator -q` ->
37 passed. The metadata-count smoke test asserts `500 <= location_count <= 540`;
531 is inside that band, so no test change was needed.

**Requalification still pending.** This is a data-source refresh only. In-game
validation of computed distances against the live client has NOT been done, and
the extraction (changelist 12232306) trails the installed 4.9.0 hotfix
(changelist 12248363) by one build. The 4.9.x.x rename waits for formal
requalification per Versioning.md.

## 2026-07-12 - Full coordinate rebuild (4.8.0.1)

Executed the rebuild sketched in the review below. The pre-4.7 static distance
matrix (`data/sc_distances.json`, 364 locations, ~4.7 MB) and the TSP optimizer
`route_optimizer.py` are gone; distances are now computed at query time from raw
meter coordinates. Quantum travel is straight-line, so Euclidean distance is the
correct model; results are reported in Gigameters (meters / 1e9).

**Data build.** New dev tool `build_locations.py` curates
`starmap_positions.json` into `data/sc_locations.json`. Curation keeps entities
that are `qt_valid and not hidden` (540), drops jump-point junk (names starting
"jumppoint", 18 of them), leaving 522 locations: Stanton 385, Pyro 127, Nyx 10.
The build is deterministic (input sha256 recorded in metadata; two runs diff
clean) and asserts its invariants: no junk survives, names are unique within a
system (duplicates across systems are allowed and expected), and the derived
topology is exactly the three system pairs.

**Gateway links by name, not by connections[].** The source `connections` block
has only two rows and is incomplete, so it is not used for routing. Links are
derived from the gateway naming convention instead: a location "<X> Gateway" in
system S implies a link S to X when system X exists and holds a reciprocal
"<S> Gateway". This yields Stanton<->Pyro, Stanton<->Nyx, Pyro<->Nyx. "Terra
Gateway" in Stanton finds no Terra system and stays a plain location with no
link.

**Resolver.** Because names duplicate across systems, every location carries a
display key: the plain name when globally unique, else "Name (System)". All
routes, legs, and tool output speak in display keys. `resolve_location` tries,
in order: exact display key, exact name, normalized exact (lowercased,
non-alphanumeric stripped, so "Area 18" reaches "Area18" and "GrimHEX" reaches
"Grim HEX"), the alias map, then a unique normalized substring. A system
argument filters the pool first. Outcomes are matched, ambiguous (returns the
tied display keys), or not found, carried in a small result object so the tools
render helpful errors rather than raising.

**TSP fixes** (folding the review findings): the 2-opt inner edge stops at
`j == n - 2`, so open routes gain no phantom closing edge, while a closed route
(return_to_start) carries the start as a real duplicated last element and keeps
cycle semantics; distance checks are strict `is None` so a legitimate 0.0 Gm leg
between co-located points is never treated as missing; nearest-neighbor with no
pinned start now tries every waypoint as a candidate start and keeps the best
before 2-opt (the old code silently started at `waypoints[0]`); unreachable legs
are flagged `"unreachable": true`, named in a top-level `warnings` list, and
excluded from the total instead of being priced 0.0.

**Rename and cleanup.** The optimizer module is `sc_nav_route_optimizer.py`
(was `route_optimizer.py`); the generic name collided with other skills' modules
on the shared `sys.path`. The dead one/two-hop gateway search and the
`GATEWAY_PAIRS` table (which contradicted the data) are gone with the matrix.
Both release manifests were updated in lockstep: `skill_installer_config.json`
files list and `update_release.py` RELEASE_FILES both swap the module;
`build_locations.py` and `tests/` are dev-only and not shipped.

**Tests.** A pytest suite under `tests/` covers curation rules, resolver paths,
Euclidean and zero-distance correctness, cross-system leg composition with the
via list, a three-system multi-hop chain, unreachable handling, the open-route
2-opt regression and closed-route cycle case, brute-force optimality, multi-start
NN beating a first-waypoint start, and a real-data smoke over the built file.

**Honest residuals.** (a) The straight-line Euclidean model for QT travel is
assumed, not validated in-game. (b) The geometry is 4.8.0-LIVE while the live
game is 4.8.3; no newer starmap extraction exists. (c) The 2026-07-11 indefinite
hold was lifted by Lars on 2026-07-12; this rebuild is that call.

**QA (same day, independent of the implementation).** Suite re-run green (37
passed). Independent rebuild of the dataset from the pinned input is
byte-identical to the shipped file. main.py tool wiring, which the test suite
cannot reach, was exercised directly against the real dataset: all ten probes
passed (resolution incl. "area 18"/"grimhex"/display keys, ambiguity payloads,
co-located 0.0, 10-waypoint mixed-system route, closed route, find_location).
Strong corroboration for residual (a): five same-system pairs and one
gateway-composed cross-system pair agree with the old field-measured matrix to
within 0.02 Gm (e.g. Lorville to Area18 22.882 vs 22.88; Lorville to Ruin
Station 112.357 vs 112.35), so the Euclidean model matches how the old
distances were produced. Curation filter disconfirmation probe: the 81 hidden
qt_valid Nyx entities are clinics, 45 identically-named generic QV stations,
and UNINITIALIZED entries; excluding them is correct. Known low-severity
limitations, accepted: open-route 2-opt never repositions the final free stop
(multi-start NN mitigates); trivial start/end-only routes report algorithm
"brute_force"; the live wingman-host load (validate() plus tool registration)
still needs one Wingman restart check.

## 2026-07-12 - Review + data-source findings (advisory, no code changes)

Lars lifted the hold for a look. Full code review plus a verified data-source
research pass. Decision on the rebuild is still pending; the hold below stands
until he calls it.

### Code review findings (fold into any refresh)

1. **Gateway routing is dead code.** The bundled matrix is all-pairs (132,132
   directed pairs, 100% populated, cross-system included), so the direct lookup
   in `get_distance` always succeeds and the one/two-hop gateway search
   (`route_optimizer.py:69-115`) never executes. `via_gateways` is never
   populated; the config prompt's "mention which gateway" can never fire.
2. **GATEWAY_PAIRS contradicts the data** (`route_optimizer.py:13-17`). It
   assumes gateways in Nyx; the dataset has exactly four gateway locations and
   none are in Nyx (Nyx Gateway, Pyro Gateway, Terra Gateway in Stanton;
   Stanton Gateway in Pyro). Latent today (masked by finding 1), breaks
   immediately if the dataset is ever regenerated per-system.
3. **2-opt treats open routes as closed cycles** (`route_optimizer.py:301-312`).
   Index wraparound (`route[i-1]` at i=0, `route[0]` at j+1=len) injects a
   phantom closing edge, so any route with more than 8 waypoints is optimized
   as if returning to start. Valid but suboptimal orderings.
4. **Legitimate 0.0 distances treated as falsy.** `route_optimizer.py:274` uses
   `or float("inf")` (and `_two_opt` uses `or 0`); the data has real 0.0 pairs
   (the gateway jump itself). Needs explicit `is None` checks.
5. **Unreachable legs silently priced 0.0** in `optimize_route` (line 207): a
   None distance drops the leg cost with no error flag. Dead under the full
   matrix, live failure mode under any partial dataset.
6. **Data corruption baked in:** three corrupt gateway self-distance rows
   (e.g. Nyx Gateway to itself = 44.18 Gm); Port Olisar still present (removed
   in 3.23, and it is the example route in `default_config.yaml`); "Checkmate"
   and "Checkmate Station" duplicate the same Pyro station; JSON metadata wrong
   twice (claims same-system-only and 134,322 routes; actual all-pairs, 132,135).
7. Minor: no pytest suite for `RouteOptimizer` (pure logic; findings 3 and 4
   are exactly what tests catch); generic `route_optimizer` module name on
   `sys.path` is the known sibling-cache collision class (rename e.g.
   `sc_nav_route_optimizer` on next touch); `main.py:72` overclaims "picks the
   best start" (true only for the brute-force path).

### Coverage gap, quantified (4.8.0 game data)

Bundled dataset: 364 locations (Stanton 287, Pyro 75, Nyx 2). Current game
files: 1,250 starmap entities, 818 QT-valid destinations (Stanton 550, Pyro
171, Nyx 97). Roughly half the universe is missing; Nyx is essentially absent.

### Donor data source (verified 2026-07-12)

**`github.com/StarCitizenWiki/scunpacked-data`, file `starmap_positions.json`**
(generated by `octfx/ScDataDumper` from Data.p4k): per entity uuid, name, type,
system, parent_uuid, hidden, qt_valid, and real x/y/z in meters (star at system
origin), plus `connections` (jump points with fuel_cost). Verified fresh:
commit 2026-06-02 tagged `4.8.0-LIVE.11875683`, repo pushed 2026-07-03. ~500 KB.
Alternatives checked and ruled out for geometry: UEX API (current to 4.8.3 but
catalog-only, crowdsourced scalar distances, no coordinates; already integrated
via the bundled uexcorp skill, useful for name cross-checks), star-citizen.wiki
REST API (same, no coordinates). Nothing else in the ecosystem publishes
coordinates.

### Recommended rebuild shape (pending decision)

Replace the precomputed matrix with ~800 coordinate triples and compute
distances at query time (QT travel is straight-line, Euclidean is the correct
model). This deletes the matrix, the dead gateway code, and finding-6 data
wholesale; cross-system legs come from the `connections` jump-point data
instead of hand-maintained GATEWAY_PAIRS. Refresh becomes re-downloading one
JSON per patch. Critically, this survives planet-tech: when orbits ship only
the position source changes (snapshot becomes ephemeris), the routing
architecture stays, which removes the original rationale for the hold (CIG has
published no orbital-mechanics design or ETA as of 2026-07). Remaining real
work item: name curation (filter `qt_valid and not hidden`, dedupe, alias
spoken names, cross-check against the uexcorp catalog). Fold findings 3, 4,
and 7 (tests, module rename) into the rebuild.

## 2026-07-11 — Decision: INDEFINITE HOLD until planet-tech releases

Decision by Lars, same reasoning as `sc_navpoint` (see its Devlog, same date):
CIG's planet-tech (his estimate: initial release late 2026 to early 2027) will
put moons and planets in orbital motion, which invalidates any static distance
matrix between locations. Regenerating `sc_distances.json` against the current
4.8.x universe now would be wasted work if the layout goes dynamic within
months. On planet-tech release: reassess whether a static distance dataset is
still meaningful (possibly per-system or time-invariant subsets); until then,
no data regeneration and no code work. The OUTDATED status below still applies.

## Status: OUTDATED — pre-SC 4.7 (2026-04-25)

RESOLVED by the 4.8.0.1 rebuild (see 2026-07-12 entry); retained for history.

This skill was built before Star Citizen patch 4.7, which delivered a major overhaul
of navigation points across the universe. The bundled `sc_distances.json` (364
locations, ~134K routes) reflects the pre-4.7 layout — locations, gateway pairs, and
distances are no longer accurate. The skill still runs and produces routes, but the
output should not be trusted for in-game decisions until the dataset is regenerated
against 4.7 nav data.

**To refresh:** rebuild `sc_distances.json` from current 4.7 location data, re-validate
the gateway pairs (Stanton ↔ Pyro ↔ Nyx etc.) against the new universe, update Devlog
status, and remove the "Outdated" tag from `default_config.yaml`.

---

## 2026-02-26 - Initial Implementation

### Task
Build a wingman-ai skill that provides traveling salesman route optimization for Star Citizen.

### Use Cases
- Multiple hauling contracts with pickup/delivery locations
- Selling mining ore to multiple buyer locations
- Buying ore from multiple seller locations
- General multi-stop route planning

### Architecture
- **Pattern**: @tool decorator (recommended by wingman-ai)
- **Algorithm**: Brute-force (<=8 waypoints) or Nearest Neighbor + 2-opt (9+)
- **Data**: Precomputed distance matrix (sc_distances.json, 364 locations, 134K routes, Gigameters)
- **Cross-system**: Routes through gateway pairs (Stanton-Pyro, Stanton-Nyx, Pyro-Nyx)

### Tools
1. `plan_route` - Optimize visit order for N waypoints (TSP)
2. `get_distance` - Distance lookup between two locations
3. `find_location` - Fuzzy location name search

### TODO
- [x] Create devlog.md
- [x] Copy distance data and set up package structure
- [x] Implement route_optimizer.py (RouteOptimizer class)
- [x] Create default_config.yaml
- [x] Create main.py (SC_Navigator skill class)
- [x] Test standalone
- [x] Update devlog with results

### File Structure
```
skills/sc_navigator/
├── main.py                     # SC_Navigator(Skill) - 3 @tool methods
├── route_optimizer.py          # RouteOptimizer class (TSP solver)
├── default_config.yaml         # Skill config, prompt, keywords
├── devlog.md                   # This file
└── data/
    └── sc_distances.json       # 364 locations, 134K routes (4.7 MB)
```

### Test Results (Standalone)
All tests pass. Performance is sub-millisecond for both algorithms.

**Brute-force (4 waypoints, start=Port Olisar):**
```
Port Olisar → Area 18 (42.29 Gm) → Lorville (22.88 Gm) → Everus Harbor (0.01 Gm) → New Babbage (38.40 Gm)
Total: 103.58 Gm | Algorithm: brute_force | Time: <1ms
```

**NN + 2-opt (10 waypoints incl. cross-system, start=Lorville):**
```
Lorville → Everus Harbor (0.01) → HUR-L1 (1.29) → ARC-L1 (20.59) → Area 18 (2.89)
→ Ruin Station (99.24) → Port Olisar (116.49) → CRU-L1 (1.91) → MIC-L1 (51.72) → New Babbage (4.35)
Total: 298.49 Gm | Algorithm: nearest_neighbor_2opt | Time: <1ms
```

**Round trip (Port Olisar → 3 stops → Port Olisar):**
```
Port Olisar → New Babbage (57.47) → Lorville (38.40) → Area 18 (22.88) → Port Olisar (42.29)
Total: 161.04 Gm
```

**Error handling:**
- Unknown locations reported clearly with name
- Case-insensitive resolution works ("lorville" → "Lorville")
- Fuzzy search finds partial matches ("lorv" → Lorville, "port" → Port Olisar, Port Tressler, etc.)

### Notes
- Cross-system distances (e.g. Lorville→Ruin Station) are available directly in the distance matrix from the original measured data, no gateway routing needed for those pairs
- GrimHEX is not in our location data (not in UEX API or route spreadsheet) - it may be listed under a different name or not yet catalogued
- Gateway routing (2-hop) is implemented for Stanton↔Pyro, Stanton↔Nyx, Pyro↔Nyx paths when direct distances aren't available

## 2026-02-26 - Prompt & Tool Description Update

### Changes
- **default_config.yaml**: Rewrote the wingman prompt to:
  - Clarify routes are one-way by default (start → destinations), not round trips
  - Add explicit presentation format with per-leg distances between each stop
  - Instruct wingman to only use `return_to_start=True` when the player explicitly requests it
  - Add gateway mention guidance for cross-system legs
- **main.py**: Updated `plan_route` tool description from "traveling salesman" to "one-way route" framing to avoid misleading the LLM into round-trip behavior

### Rationale
The LLM was not consistently presenting per-leg distances and the "traveling salesman" framing implied round trips by default. The route optimizer already defaults `return_to_start=False`, so this aligns the prompt with the actual behavior.

## 2026-02-26 - Skill Structure Fix (Release Build Compatibility)

### Problem
Skill failed to activate in the release build (PyInstaller exe) with:
`Error activating skill 'SC_Navigator': No module named 'skills.sc_navigator'`

### Root Cause
Non-bundled skills are loaded via `spec_from_file_location` in release builds, not `import_module`. Absolute imports like `from skills.sc_navigator.sc_navigator.route_optimizer import RouteOptimizer` fail because `skills.sc_navigator` isn't registered in the bundled Python import system. Bundled skills (e.g. uexcorp) don't hit this because `import_module` succeeds for them.

### Fix
1. **Flattened structure** — Removed nested `sc_navigator/sc_navigator/` sub-package. Moved `route_optimizer.py` and `data/` directly under `skills/sc_navigator/`.
2. **Adopted sys.path import pattern** — Following the regolith skill's proven approach: add the skill's own directory to `sys.path`, then import sibling modules by bare name. This works in both dev and release builds.

```python
# Before (broken in release):
from skills.sc_navigator.sc_navigator.route_optimizer import RouteOptimizer

# After (works everywhere):
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
from route_optimizer import RouteOptimizer
```

### Lesson
Non-bundled skills must avoid absolute `skills.xxx` imports for their own sub-modules. Use `sys.path` insertion + bare module names instead.
