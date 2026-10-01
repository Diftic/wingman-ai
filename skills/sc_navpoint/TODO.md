# SC NavPoint — TODO

Current installed package: [v4.9.0.26 for Wingman 3.2.2](WINGMAN_3_2_2_2026-09-20.md).
Full Wingman restart and live navigation check pending.

Latest package: [v4.9.0.25](STARTUP_CARD_2026-09-19.md). Install and restart Wingman
to check automatic activation and the compact card after its startup delay.

## Tester retry — 2026-09-19

Use [v4.9.0.24](IMPORT_COLLISION_2026-09-19.md) for the SC Log Reader import-collision
fix. Fully close Wingman, install the new ZIP and restart before retrying activation.

## Current next session — 2026-09-17

The [live-test installer ZIP](INSTALLER_PACKAGE_2026-09-17.md) is ready for testing.

Start with [HANDOVER_2026-09-15.md](HANDOVER_2026-09-15.md), which supersedes
historical installation/status statements below.
The [Vision cleanup](VISION_CLEANUP_2026-09-17.md) is now installed; restart Wingman
to load it before continuing the live checks.

- Confirm the final installed build loads in a restarted Wingman and that the
  experimental reader selector is gone.
- Perform Levski calibration with movement in multiple directions, then validate
  the dot against Landing Deck 4. The corrected live flight is still pending.
- Recheck planetary and open-space navigation, arrival, concise speech and the
  dashboard/QR presentation before broader live-test release.
- Preserve saved waypoints, session evidence and unrelated repository changes.

## READ THE LEDGER FIRST: `ledger/`
Built 2026-08-02 because this file and `Devlog.md` are chronological and
append-only, so a correction gets filed where it was DISCOVERED and never
reaches where the number is USED. Nine headline numbers were revised in six
days and several originals are still sitting in these documents being read as
current.

| file | answers |
|---|---|
| `ledger/LEDGER.md` | what is the current number, and what the sources disagree about |
| `ledger/REFUTED.md` | what was tried and failed, and must NOT be retried |
| `ledger/CORPUS.md` | what capture data exists, and what each one actually shows |

**RULE: one canonical row per quantity.** If you change a number, change it in
`ledger/LEDGER.md` and nowhere else. Do not restate a number in this file; cite
the ledger.

## 2026-08-11: `Supercalifragilistic.md` WAVES 0 TO 2 DONE. TWO GATES NEED LARS.

Suite **862 to 951**. Nothing committed, no release, installed copy untouched.
Full account in `Devlog.md` (2026-08-11); all numbers in `ledger/LEDGER.md`.

### THE TWO THINGS THAT NEED LARS, and nothing in waves 3 to 7 needs anything else

1. **WAVE 3 SHUTDOWN SEMANTICS. The plan and the code contradict each other and
   both cannot be honoured.** §18 Wave 3 asks the capture provider to be stopped
   AND JOINED. `main._stop_nav_polling` deliberately does NOT join, commented "a
   capture in flight can take seconds; the thread is a daemon". Joining risks
   Wingman hanging on exit for the length of a capture (measured up to 1.9 s on
   stored frames, likely worse live). Not joining lets shutdown leave work in
   flight, which is what the plan wants to prevent. **`unload` has ZERO tests**,
   so there is no existing behaviour to defer to. Wave 3 cannot start until this
   is chosen.
2. **THE STANTON FLIGHT**, still outstanding from 2026-08-10. Two landings,
   microTech and Crusader, each with a STEP OUTSIDE while the capture runs and a
   turn toward dark sky before holding still for a minute. It is the only thing
   that can give the `OOC_` branch its first real pixels. Pyro cannot answer for
   Stanton: separate design templates, Lars's own point and it is correct.

### What shipped into the dev tree today

- `telemetry.py`, pure, all ten outcome states, in BOTH release manifests, and
  **no runtime consumer imports it** (Wave 2's exit gate).
- `ocr_dev/bench_reader.py` and `ocr_dev/baseline-2026-08-11.md`, the first real
  performance baseline. **Read its contamination caveat before quoting a
  millisecond.**
- The main-menu refusal gate in `scanner.parse_payload`, reason id
  `no_game_world`, constant `_MIN_WORLD_ROOT_M = 1e6`. Both endpoints are in the
  ledger so the threshold is re-derivable rather than trusted.
- Wave 1 contract fixes: `read_legacy_payload` rename, the corrected prompt, and
  full custom-property validation.

### Known and deliberately NOT fixed

- **`update_position` returns raw x/y/z to the model** (`main.py:2689-2698`),
  which the plan's §4.3 forbids. Lars decided: fix in **Wave 7**, where the
  model-boundary work is already scheduled. Two smaller leaks in the same family:
  `capture_kind` on every refusal, and `route_reason`/`bearing` from
  `navigate_to`.
- The eleven player-facing Printr badges stay VISIBLE (Lars's decision).
- Two pre-existing `ruff` F401 warnings in `main.py`.

## DECISION 2026-08-10: THE COORDINATE STACK IS IMPLEMENTED, WAVES 0 TO 4

`COORDINATE_STACK_IMPLEMENTATION_PLAN.md` waves 0 to 4 are done, 862 tests green
from a 678 baseline, 23 mutations caught. Nothing committed, no release
generated, the installed copy untouched. Full account in `Devlog.md`
(2026-08-10) and the numbers in `ledger/LEDGER.md`.

**A newly marked waypoint is now addressed by Root and the whole nested stack,
and routed by a pure state machine that never reads a zone name.** A Pyro 3
surface, the primary use case, can be marked at all for the first time.

### THE ONE THING BLOCKING THE ROLLOUT

`coordinate_stack.LOCAL_TRACKING_ENABLED = False`. Local tracking ships OFF
because "the row immediately before SolarSystem is the body or area frame" has
never been measured. Flipping that single constant is the whole rollout; the
routing code, every boundary test and the local arrival path are written and
mutation-proven.

The paired-capture matrix that would open it is in the plan's
"Local-candidate evidence gate" section. Until then every schema-1 waypoint
routes on Root, which is correct everywhere and merely coarse up close.

### WAVE 5 STEP 1 IS DONE, 2026-08-10. STEP 2 IS A FLIGHT.

The corpus replay ran: 19 sessions, 536 frames, 355 stacks, **0 regressions, 0
Root disagreements, 0 continuity flags**, and the Pyro 3 surface change is real
on real pixels (`surface-01` 90/90 stack, 0/90 legacy). Tool at
`ocr_dev/stack_replay.py`; numbers in `ledger/LEDGER.md`, "Corpus replay", with
the four boundaries that make them narrower than they look.

**IT ALSO FOUND THE THING THE GATE EXISTS FOR.** In `dark-01` the local
candidate IS the ship: candidate position span 0.239 m while Root span
1.913e9 m. `ledger/REFUTED.md` now carries "the outermost row before SolarSystem
is ALWAYS the body or area frame" as killed AS A UNIVERSAL. Do not flip
`LOCAL_TRACKING_ENABLED` on the strength of the eight sessions where it holds.

### NEXT, IN ORDER

1. **Wave 5 step 2, the paired-capture matrix. This is flying, not code**, and
   it is the only thing that can open `LOCAL_TRACKING_ENABLED`. Eight rows in
   the plan's "Local-candidate evidence gate", currently 0 for 8. The corpus
   cannot supply any of them: it holds ONE ship and its only jump-point frame
   refused.
2. Then ask for approval for a supervised live flight. Live testing must not
   install an unreleased dev tree.
3. **Wave 6.** Version bump, `release_version` regeneration through
   `update_release.py`, then install, all separately approved.

**OPEN, NEEDS A DECISION FROM LARS, and it is not a schema-1 defect.** The main
menu emits a phantom but complete stack at (-0.00m, 0.04m, 1.74m) that reaches
`KIND_OK` on the shipping path. Both parsers accept it, so it predates the
stack rework. Resolves contradiction #4. Nobody has decided whether to fix it.

`release_version/` is deliberately the 2026-08-02 build and now differs from the
dev tree. That is expected, not drift.


Everything below this line is the historical working record. It contains stale
sections that supersede each other IN PLACE, and only three of them are
self-labelled. Trust the ledger over this file where they disagree.

## Next session starts here

### DECISION 2026-08-02 (later the same day): NO VISION AT ALL. OCR ONLY.
Lars's call, stated three times in one exchange: "no, we will not use vision at
all, only OCR" and "no visionAI at all". It SUPERSEDES "DECISION 2026-08-02:
BUILD THE ROUTER" immediately below, which had itself reversed "DECISION
2026-07-31: Vision AI is OUT of this skill, permanently". That is three
decisions on the same question in three days. All three are kept below in the
order they were taken, because the sequence is the record.

**THE SHAPE NOW:** the local deterministic reader is the ONLY reader. No
fallback of any kind, no model in the loop, no router.

**THE COST, put to Lars before he decided and accepted by him.** The local
reader has produced ZERO successful field captures since 2026-07-31 22:07:10.
Seven failures over two days:

- the 2026-08-01 pair reported no sub-reason and took 1.1 s and 1.2 s;
- the 2026-08-02 pair reported `no_system_line` and took 11.1 s and 11.0 s.

**CORRECTION, later on 2026-08-02: "two distinct shapes" is REFUTED.** The 08-01
lines lack the gate name and the `attempts=` field, both of which the current
code writes unconditionally, so that build had neither the gate instrumentation
nor the retry loop. ONE failure mode seen through two builds, not two, and the
duration gap is one attempt against five. The count, the dates and the durations
are unaffected. Still unexplained: 11.1 s over five attempts is about 2.2 s
each against 1.1 s for the single-attempt build.

With no fallback, fixing the reader is not a side investigation running beside a
working product. It IS the product.

**THE 62 TO 100 PER CENT MEASUREMENT STILL STANDS.** Nothing here disproves it.
Over sunlit terrain the reader refuses 62 to 100 per cent of cells, that is
measured on real ground, and the primary use case is a ship on a surface. The
constraint is ACCEPTED, not removed. Its own instruction, "do not plan a Vision
retirement; plan a router", is void as of this decision.

**WHAT THE INSTALLED CODE DOES TODAY, read rather than assumed.** `_capture_position`
at `main.py:382-405` calls `self._capture_position_local(attempts)` and nothing
else, and a grep across the skill folder finds no non-test caller of
`capture_screen_b64`, `build_extraction_messages`, `parse_completion` or
`_EXTRACTION_PROMPT`; every reference outside `scanner.py` is a test or a
docstring. So the Vision path is PRESENT but UNREACHABLE, and 4.9.0.22 as
installed already behaves as OCR-only. This decision changes the records and the
plan, not the runtime behaviour.

**THE VISION PATH IS STILL NOT STRIPPED, and no agent may strip it.** The
unticked strip item further down this file stays unticked and stays last. It is
the irreversible step, and leaving it untaken is the only reason this question
could be decided three times in three days at zero rebuild cost. Do not delete
`scanner.py`'s Vision code without an explicit instruction from Lars.

### BUILT 2026-08-02 evening: the failure is now legible. NOTHING IS PROPAGATED.
Three waves under the decision above. Full record in Devlog 2026-08-02
(evening). The new quantities below are not yet in `ledger/`; take them from the
Devlog entry until they are.

**FIRST ACTION FOR THE NEXT SESSION, and nothing works before it.**
`release_version/` and the AppData install are BYTE-IDENTICAL to where they
started. Run `update_release.py`, then `release_version/install.bat`, then
restart Wingman. Until that happens the instrumentation does not run, and the
stale "via Vision AI" description is still what the live skill shows.

**THIS DOES NOT FIX THE READER.** There has still been no successful field
capture since 2026-07-31 22:07:10. The work makes the failure legible and
measurable so the next live session yields evidence instead of another refusal
with no sub-reason. Say it plainly to whoever reads this next.

Built: per-attempt capture tracing, poll log rotation at 8 MB keeping one
generation, a frozen `CaptureOutcome` with ten `KIND_*` constants, a capture
lock; then per-cell refusal diagnostics, a success baseline, the refused-frame
dump, nine per-kind failure messages replacing one, the `navigate_to`
silent-accept fix, the two "Vision AI" badges reworded, and the capture moved
off the event loop with `asyncio.to_thread`; then the metadata corrections, the
`Laura.yaml` deletion, two validator-found defects, and the dump switched ON.

- **Tests 536 to 654**, 118 added. Exactly two pre-existing assertions changed,
  both authorised: `test_main_capture.py:430` and the `SAVE_REFUSED_FRAMES`
  default-state assertion. Every other failure was fixed in the code.
- **`navigate_to` no longer silently accepts.** It used to set the target, start
  the poll thread, open the HUD and say "Bearing tracking begins once a local
  frame on {body} is available" on a TOTAL capture failure. It now refuses and
  sets nothing. A validator reproduced the old behaviour by reverting the gate.
- **The `r_displayinfo 2` hint is down from 4 sites to 2**, the module docstring
  and one hint block reachable from `KIND_ABSENT` only, pinned by tests across
  all nine kinds.
- **The two refusal conditions are now distinguished in the log.**
  `overlay_reader.py:569` refuses on `cost > REFUSE_COST or margin <
  REFUSE_MARGIN`; high cost means nothing matched, low margin means two glyphs
  matched almost equally, and the fix for one is not the fix for the other. A
  test pins both constants AND the disjunction, since `or` to `and` would halve
  the guard without changing either number.
- **HYPOTHESIS with a measurement, not a cause:** the alignment self-heal refit
  costs +310 ms per read (763.6 against 453.9 ms) and fires whenever nothing
  decodes as trusted (`overlay_reader.py:725`), which in the observed failures
  is every read. Roughly 1.5 s of an 11 s five-attempt mark. Instrumentation
  item I4 logs `from_cache` and `refit` so live data settles it.
- The refused-frame dump is ON for six kinds (`unusable`, `absent`,
  `decode_error`, `gate`, `reject`, `unexplained`) and not for `no_grab`,
  `no_reader`, `no_frame`. One PNG per failed capture, final attempt only,
  capped at 20 GLOBALLY, so **one class can crowd out another**. Crop only,
  local only, never transmitted.
- `Laura.yaml`: `prompt` and `discovery_keywords` deleted, backup outside the
  configs tree because `config_manager.py:446` loads every `*.yaml` there. All
  six custom properties survive with the user's values. The deleted prompt was
  byte-identical to the live `default_config.yaml` prompt, so nothing changes
  today; it stops future prompt edits from being no-ops.

**STILL NOT DONE:** no version bump (still `4.9.0.22`, the user's decision),
nothing propagated, nothing committed, the reader not fixed. Step 7 of the
implementation plan (retry policy) is BLOCKED on live data from the new
instrumentation. The `pyro3` body-token plausibility question and non-`OOC_`
surface routing remain open and untouched.

### SUPERSEDED 2026-08-02: BUILD THE ROUTER. Vision comes back as a fallback.
**THIS DECISION IS REVERSED. See "DECISION 2026-08-02 (later the same day): NO
VISION AT ALL. OCR ONLY." directly above.** It was never implemented, so nothing
built has to be undone.

Original entry follows, kept for the record.

Lars's call, and it SUPERSEDES "DECISION 2026-07-31: Vision AI is OUT of this
skill, permanently" further down this file. That decision and the measurement
that contradicts it had both been sitting in this file, 80 lines apart, since
2026-07-31, neither referencing the other:

- line ~405, measured on real ground: over sunlit terrain the reader refuses
  **62 to 100 per cent of cells**. "CONSEQUENCE: Vision stays required for
  daylit surfaces. Do not plan a Vision retirement; plan a router."
- line ~322, the same night: "Vision AI is OUT of this skill, permanently."

The question that was supposed to settle it, "is the surface use case mostly
daylit", was logged as "the most important open item in the project" and was
never answered.

**IT IS ANSWERED NOW (Lars, 2026-08-02):** sometimes in a ship in space, MOSTLY
IN A SHIP ON A SURFACE, rarely on foot, NEVER inside a base, building or cave.

So the skill's primary use case is the one the reader was measured unable to
serve, and the fallback had been removed by decision. That, and not any gate,
is why marking works at one location and not at others.

**THE SHAPE:** the local reader keeps everything it can read (space, night,
shadow) at zero tokens; Vision covers only frames the reader REFUSES. Every
confabulation defence in `scanner.py` stays, because a model is back in the
loop: the echo canaries, the plausibility gate, the two-capture wipe
confirmation, the mandatory unit suffixes. None of it was deleted, since
stripping the Vision path was deliberately left as the LAST and irreversible
step and was never taken. That decision to defer is what makes this reversible
today.

**A COMPLICATION, recorded rather than smoothed over.** The 2026-08-02 failure
that triggered this was in SPACE, not on a surface: the Reclaimer frame decoded
with scattered `?` across all eight rows, which is the background-solve failure
mode, in the regime the reader is recorded at 85 per cent usable. That 85 per
cent is 20 frames of one flight. Either that scene was unusually hostile behind
the block, or the space figure does not generalise. UNRESOLVED, and it means the
router's trigger rate is unknown in both regimes.

**NEVER inside a base, building or cave** also collapses the nested-container
problem that blocked the local-frame routing rule since 2026-07-31: the elevator
capture's transit carriage, hangar and cargo bay are not cases that need
solving. The deepest realistic stack is ship -> body -> SolarSystem -> Root.

### OPEN: four fixes are INSTALLED at 4.9.0.22 and none has run in game
Installed 2026-08-01 evening. 536 tests pass. All three trees hash-verified
identical (17 files, 0 mismatches), stale `__pycache__` cleared, every installed
module byte-compiles, and the installed classifier was behaviour-checked rather
than assumed: `LABELS` is zone-first, the phantom row `'? CamDir: ...'` returns
`camdir`, and a two-label row returns `zone`. Version NOT bumped.
**WINGMAN NEEDS A RESTART.** Rollback copy of the previous live install is in
this session's scratchpad as `sc_navpoint-live-backup-2026-08-01-evening`.

**FIRST ACTION.** Restart Wingman, sit at P5 L2 with `r_displayinfo 2` up, say
"mark this location". Expect a waypoint. The reader already produced a clean
payload on 12 of 15 frames there before the fix, so this should now be reliable
rather than merely likely.

**IF IT REFUSES, the log finally answers it.** Grep `capture REFUSED` in
`generated_files/SC_NavPoint/navpoint_poll.log`. The line NOW names the gate
(one of `no_system_line`, `refused_above`, `body_scale`, `no_coordinate`,
`no_root`) and is followed by a dump of all 8 decoded rows with kind, trusted
flag and raw text. That is what was missing this session and it cost an hour.
A mark that needed more than one grab logs `read on attempt N of 5`, so a rising
attempt count is the early warning that the refusal rate has grown.

**THEN CONFIRM THE GUARD STILL BITES.** On a planet surface (Pyro 3) marking
must still REFUSE. Two changes this session moved in the permissive direction
(label search, and the afternoon's scale window), so this is the case that
proves neither went too far.

**THE ONE THING THE BENCH CANNOT REACH:** the label-search change moved 248
untrusted rows from BLOCKING to CLEARING the space branch. All 7 frames whose
output actually changed were genuinely open space, so the clearing path has
only ever been exercised where clearing was CORRECT. The outstanding Stanton
surface capture (on foot, dark ground, `Zone: OOC_` visible) is what would test
it where it could do harm, and it also closes `O` phase 0.

### RESOLVED 2026-08-01 evening: the Lagrange fix was correct all along
The afternoon's body-scale window was never the problem. Measured on a fresh
15 frame capture taken AT P5 L2 (`ocr_dev/captures/p5l2/`): the container reads
44,707 km, roughly 3x the 15,000 km ceiling, correctly classified as a container
and not a body on all 15 frames with zero flicker. The body-scale gate never
fired. 12 of the 15 frames produced a clean system-frame payload.

**WHAT ACTUALLY REFUSED THE MARK, and it is the phantom glyph again.** The
3 failing frames all refused at the `refused_above` gate, caused by a background
star decoding as a phantom glyph in the blank left margin of the CamDir row:

    '? CamDir: 179   0  133 FOV: 55 Focal: 3.00 FStop: 64.0'

`overlay_reader.row_kind` ANCHORED its label patterns at position 0, so a leading
phantom left `kind` as None, and a CamDir row with no kind cannot be cleared by
`ooc_hypothesis_refuted` (it is not in `_NOT_ZONE_KINDS` and has no `Zone:`
substring to test by shape). So an unreadable row sat above the SolarSystem line,
the absence of an OOC line was not established, and the capture refused. This is
the SAME defect fixed in `_largest_component` the same afternoon, in a second
consumer. Control: a frame with an untrusted CamDir row but NO leading phantom
passes, so untrustedness alone never blocked. Losing `kind` did.

**THE CORRECTION TO MY OWN NOTE, which cost this session's first hour.** The
line above used to claim the trace "names the gate". IT DID NOT. It named the
BRANCH. All five refusal gates inside `payload_from_rows` collapsed into one
sentence, `overlay read but no payload from N row(s)`, and each gate's real
reason went to `logger.info`, which reaches no file (verified: zero matches for
`Space capture refused` in every wingman-core log). So the instrumentation
shipped to make refusals explainable was one level short of the question, and a
correct fix looked suspect for an hour. Fixed this session, see below.

**Two things are outstanding:**
1. **The 15,000 km ceiling is a chosen threshold, not a measurement.** It sits
   in the empty band between the largest body observed (410 km) and the
   smallest container observed (19,125 km). The largest REAL body scale is
   unmeasured. If a capture ever refuses on a body-looking row above 15,000 km,
   raise it; raising only ever refuses more, which is the safe direction. A
   container between 15,000 and 19,125 km will refuse until measured.
2. **The drift test was the better discriminator and was not taken.** Deciding
   by behaviour (a rotating body's frame drifts 137.6 m/s, containers are
   static within noise) needs no threshold guess and cannot be fooled by an
   unfamiliar body size. Costs a second capture and a delay before marking.
   Worth revisiting if the ceiling ever needs defending.

**Do NOT reach for Z pass-through here.** It was tried this session and
reverted: `pyro3` passes Z through too (184/184), so it cannot separate a
rotating body from a static container. See the Devlog entry and
`reference_sc_coordinate_frames`, which now records the same caveat.

### OPEN: the glyph bank refuses several uppercase letters
`FOV:` reads `F??:`, `DRAK_Clipper` reads `????_?lipper`, `P5_L2` reads `P5_?2`.
Coordinates and the SolarSystem/Root rows decode trusted, so captures work, but
zone NAMES come back partly unreadable. This blocks the local-frame routing
rule directly, since that rule keys a waypoint to the anchor token stored
verbatim and must refuse when the name did not decode trusted. Harvest the
missing phases from a capture: at minimum `O`, `V`, `D`, `R`, `A`, `K`, `C`, `L`.


### OPEN: the HUD fix is INSTALLED but has never run against the real game
Fixed and released 2026-08-01 midday (Devlog `2026-08-01 (midday)`): the page's
Clear, Navigate and delete now reach the skill through `on_target_change`, and
the page flags itself `hud-offline` instead of freezing silently when the skill
is gone. 464 tests pass, verified end to end with real Edge over CDP,
release_version 18/18 and live install 17/17 hash-verified. Version NOT bumped;
still 4.9.0.22.

**Two things are outstanding, in order:**
1. **No live run yet.** Everything above was proven against a standalone server
   on the bench, never against Wingman driving the real skill. First live check:
   restart Wingman, open the HUD, set a target, press Clear, and confirm the
   RING goes dark too. The ring is the half that used to keep guiding, and it is
   the half no bench test can exercise.
   **Open the HUD page fresh; do not reuse an old tab.** A tab from a previous
   run is the suspected cause of the original report.
2. **Root cause inferred, not observed.** The reported silence is explained by
   the page outliving its server, deduced from a live server answering every
   verb correctly in real Edge. Nobody watched the failing session. Next time it
   happens the page itself decides it: the red OFFLINE banner means the skill is
   gone, an `HTTP nnn` status message means the skill answered and refused.

Also noted, not acted on: `saveRename` has the same unchecked-response habit the
two fixed buttons had. It is now covered by the offline banner (a dead server
flags the whole page) but it will still claim a rename succeeded if a live
server refuses one.


### START HERE next session: the routing rule is PROPOSED, waiting on Lars
Nothing was implemented on 2026-08-01. No file changed, no test was added, the
live build is still 4.9.0.22 with 453 tests. Full evidence in Devlog
`2026-08-01 (early)` and in `ocr_dev/zone-stacks-2026-08-01.md` and
`ocr_dev/frame-drift-2026-08-01.md`.

**THE PROPOSAL:** the local anchor is the OUTERMOST container row (nearest the
SolarSystem row) whose Z equals the SolarSystem row's Z in metres; no such row
means the system frame. Nothing keys on names, row indices or magnitude. It
separates world containers from vehicles and interiors 330 to 295 with zero
exceptions, and it is safe in both directions because only a rotating body's
frame drifts (`pyro3` at 137.6 m/s over 89 pairs; everything else static within
noise).

**BOTH OLDER CANDIDATES ARE REFUTED.** The row-index rule keys to a room in
preflight and a cargo bay in red-01. The scale rule misses the 1.46 km ring
station and falsely refuses at a 597 km jump point (that false refusal is LIVE in
4.9.0.22; it is a cost, not a danger, and the guard should stay as a backstop).

**TWO THINGS BLOCK IMPLEMENTATION, in order:**
1. Lars's decision on `scanner.py`'s `_KNOWN_SYSTEMS` plausibility gate. It
   requires `System_designator_Body`, which encodes one CIG team's convention;
   `pyro3` passes by accident and `glaciemring_segment_wtn-018` fails.
   Recommendation is to remove it from the local path, not widen it.
2. A skeptic pass over both evidence reports by an agent that did not produce
   them and does not get my reasoning. I predicted the Z result and then
   commissioned the agent that tested it, which is the wrong order.

**FOUR CAPTURES OUTSTANDING**, all with `--window=` (the equals form, or it
captures nothing):
- `station-still`, stand still inside a ring station, 5 min. Settles whether
  stations drift, which is the thinnest part of the evidence (one pair, 2 s).
- `city`, on foot in Lorville or New Babbage, 2 min. The one case the rule is
  untested on: if a city zone sits between the room and the body and is itself
  Z-aligned, "outermost Z-aligned" picks the city and not the body.
- `stanton-surface`, on foot on a Stanton moon over dark ground, 3 min. First
  real pixels for the `OOC_` branch, plus `O` phase 0 and a second body.
- `jump-still`, parked at the Pyro-Nyx jump point, 5 min.
If only two are possible: `station-still` and `city`.

**DECIDED AND CLOSED on 2026-08-01:** the key is the anchor token stored VERBATIM,
opaque, never parsed, exact-string matched, and the capture refuses if the name
did not decode trusted. No `OOC_` stripping, no migration: the live database holds
exactly one waypoint (`Mining Location 1`, frame `system`, body empty), so there
are zero local-frame waypoints to be compatible with. Driving reason is Lars's
constraint that CIG names are per-team and stay inconsistent until planet tech;
see memory `reference_sc_zone_naming`. Open risk left with him: a patch can rename
a zone and orphan its waypoints, mitigable by also storing the SolarSystem
coordinates, which is a schema change and was NOT adopted.

The paste-ready prompt further down was written before any of this and its
"THE DECISION" section is now stale. The finding and the guard it describes are
unchanged and still correct.

### Original 2026-07-31 framing (finding and guard unchanged, decision superseded)
This was the one open design decision and everything surface-related waits on it.
Full evidence in Devlog 2026-07-31 (close). 453 tests green, installed live.

**The finding:** Pyro does NOT use the `OOC_` prefix. On Pyro 3, on foot, the
stack is `Zone: pyro3 Pos: 330.74km 218.74km 119.00km` -> SolarSystem -> Root.
Stanton still used `OOC_` as of 2026-07-26 (`OOC_Stanton_2b_Daymar`,
`OOC_Stanton_4b_Clio`), so BOTH conventions are live and a rule must handle both.

**Already done, and safe under any answer:** a container above the SolarSystem
line whose own Pos is >= 50 km means the player is on a body, so the space
branch REFUSES instead of emitting a system-frame fix. Verified on the real
Pyro 3 frames: 0 emitted, 90 refused, against 62 emitted before. This only
refuses; it decides no routing.

**The two candidate rules, and where each breaks:**
- USER'S (2026-07-31): row 1 is CamDir, row 2 is the local coords, unless row 2
  is a ship in which case row 3 is. Covers on-foot and in-ship, which is the
  targeted scope. BREAKS on nested interiors: the elevator capture had three
  container rows (transit carriage, hangar, `P5_02`) before SolarSystem.
- SCALE (mine): the outermost container before SolarSystem, if its Pos is
  body-scale. BREAKS on `P5_02` at 28,000 km, which is a rest-stop container and
  not a body, so it would be misrouted as a local frame.
- Neither is obviously right. Do not pick one at the end of a session.

**What the decision touches, which is why it needs care:** the waypoint KEY
(currently `body_token` from the OOC line), the plausibility gate in scanner.py
(requires `System_designator_Body`, which `pyro3` fails by construction), and
`database` schema v2's required `body` column.

**Data available to decide with, all on disk:** `captures/surface-01` (90 frames,
Pyro 3 on foot), the elevator and station captures, and the 4.8 field inventory
in `screenshots/overlay-field-inventory-2026-07-13.md` which has the landed-on-
Clio stack verbatim.

#### Paste-ready prompt to open that session

```
sc_navpoint: decide and implement how a LOCAL FRAME is detected.

Read first, in this order:
  skills/sc_navpoint/TODO.md      section "START HERE 2026-08-01"
  skills/sc_navpoint/Devlog.md    entry "2026-07-31 (close)"
Do not re-derive what those already record.

THE PROBLEM
The skill routes local-vs-system on the presence of an `OOC_` zone line. That
assumption is wrong. Pyro does not use the prefix: on Pyro 3, on foot, the stack
is `Zone: pyro3 Pos: 330.74km 218.74km 119.00km` -> SolarSystem -> Root. Stanton
DID still use `OOC_` as of 2026-07-26. Both conventions are live, so a rule must
handle both. Consequence before it was guarded: the reader concluded open space
and emitted a SYSTEM-frame position while the player stood on a rotating body,
62 frames of 62, which is the 2026-07-11 failure through a different door.

ALREADY SAFE, DO NOT REDO
A guard refuses the space branch when a container above the SolarSystem line has
a Pos >= 50 km. Verified on real frames: 0 emitted, 90 refused. It only REFUSES
and decides no routing, so it stays correct under any rule you pick. Keep it.

THE DECISION
Two candidates, each breaks where the other holds:
  A (Lars): row 1 is CamDir, row 2 is the local coords, unless row 2 is a ship
    in which case row 3 is. Breaks on nested interiors: the elevator capture has
    three containers (transit carriage, hangar, P5_02) before SolarSystem.
  B (scale): outermost container before SolarSystem if its Pos is body-scale.
    Breaks on P5_02 at 28,000 km, a rest-stop container that is not a body.
Test any candidate against ALL of these before proposing it:
  ocr_dev/captures/surface-01   90 frames, Pyro 3, on foot, no OOC line
  ocr_dev/captures/red-01       elevator, three nested containers
  ocr_dev/captures/flight-01    open space in a ship
  ocr_dev/captures/preflight    ring station
  screenshots/overlay-field-inventory-2026-07-13.md  landed-on-Clio stack, has OOC

WHAT IT TOUCHES, which is why it needs care
  the waypoint KEY (currently body_token from the OOC line)
  scanner.py plausibility gate (requires System_designator_Body; `pyro3` fails it)
  database schema v2 (body is a required column)

HOW I WANT YOU TO WORK
  Delegate implementation, tests and analysis scripts to agents. Keep framing,
    reading diffs, running tests and irreversible calls on the main loop.
  No hints. Say the actual request, recommendation, or doubt, including about
    your own reliability.
  Validate every probe against a known positive before trusting a negative.
    Four probes silently lied on 2026-07-31.
  Changes stay inside skills/. Never commit. Never claim success without
    showing the output that proves it.
  Both release manifests must be updated in the same change as any new runtime
    file: skill_installer_config.json AND update_release.py RELEASE_FILES.

Propose the rule and your evidence BEFORE implementing it. If the captures do
not settle it, say so and tell me exactly what to capture in game.
```

### NEXT VERSION: remove `space_direction_test` entirely (user, 2026-07-31)
Not a switch flip, which is why it is not bundled into the current fix. Removing
it touches: the `space_direction_test` config property, `_get_space_direction_test`
and `_log_space_test` in main.py, and the `allow_uncalibrated_space` parameter
threaded through `navigation.ring_deflection` and `navigation.ring_status` plus
`space_guidance`. The `SPACE_DIRECTION_CALIBRATED` gate itself STAYS: it is what
makes the ring withhold a direction it cannot support, and with the test switch
gone it becomes the only thing standing between the player and a bubble that was
measured 108.7 degrees out. Removing the switch means the uncalibrated space
bearing can never be drawn at all, which also makes `RING_NO_BEARING` the
permanent open-space behaviour until a calibration flight happens.

### FIX WRITTEN, NOT INSTALLED (2026-07-31): `NO BEARING` for uncalibrated space
Wingman was running, so the copy was refused. `navigation.py` and
`overlay_fields.py` are newer in dev than in `custom_skills`.
The bug: with `space_direction_test` OFF, `ring_deflection` correctly withholds
direction in open space, and `ring_status` then fell through to `ACQUIRING...`,
which promises a fix that is structurally incapable of arriving and would sit on
screen forever. New `RING_NO_BEARING` state, chosen only when the frame really is
the uncalibrated system case; a stale local fix still says `ACQUIRING...`.
441 tests.

### 2026-07-31 LATE: WIRED AND INSTALLED LIVE at 4.9.0.22. Needs a Wingman restart.
LIVE ENV IS UPDATED (was 4.9.0.8). NOT tested in game yet: nothing has run inside
Wingman. Full detail in Devlog 2026-07-31 (late). 439 tests green.

- **Install verified, not assumed:** all 11 runtime files hash-identical to dev,
  every installed `.py` compiles, stale `__pycache__` cleared, installed copy
  reports 4.9.0.22 / 88 cells / POSITION_ROWS 8 / 86 templates / the three ring
  strings / no `llm_call` in the capture path. Wingman was confirmed closed with
  a probe validated against a known positive FIRST.
- **Rollback:** pre-install copy at the session scratchpad
  `sc_navpoint-live-backup`; `release_version` still holds a Vision build.
- **Live headless result:** 8/8 positions, zero refusals, median 831 ms =
  **1.20 Hz**, meeting the user's "at least one fix per second" bar. Steps of
  112 to 224 m, stable frame id, steady Z.
- **What cleared the bar was READING FEWER ROWS.** `POSITION_ROWS = 8`; rows 8+
  are the second pitch class and refuse in every capture. 12 rows 1795 ms,
  10 rows 1303 ms, 8 rows 1033 ms. Do not go below 8: the elevator capture ran
  the Zone stack to row 5.
- **Photosensitivity:** a message holds for a minimum of 1 second, enforced by
  `ring_overlay.MessageFader` in the RENDERER so no caller can defeat it. Worst
  case measured at 0.50 Hz of on-off cycles against a 3 Hz hazard threshold.
- IN-GAME CHECKS STILL OWED: `mark_location` (must refuse cleanly, never a
  phantom waypoint), `navigate_to` and the bubble, `GLARE` over a bright scene,
  `NO SIGNAL` with `r_displayinfo 0`, and above all whether the ring behaves
  CALMLY. Every strobe protection is proven in simulation and none has been seen
  on a real screen.

### SUPERSEDED 2026-08-02: Vision AI is OUT of this skill, permanently
**THIS DECISION IS REVERSED. See "DECISION 2026-08-02: BUILD THE ROUTER" at the
top of this file.** That reversal was ITSELF superseded later the same day by
"DECISION 2026-08-02 (later the same day): NO VISION AT ALL. OCR ONLY.", which
is the operative decision. Read the top of the file for the current position;
the outcome now resembles this 07-31 entry, but it is not this entry.

It was taken on 2026-07-31 in the opposite direction to a
measurement made the same night and recorded 80 lines below it (sunlit terrain
refuses 62 to 100 per cent of cells; "Vision stays required for daylit
surfaces"). Neither entry referenced the other, and the question that was meant
to decide between them was never answered until 2026-08-02.

It was NEVER IMPLEMENTED, which is the only reason reversing it is free:
stripping the Vision path was deliberately ordered LAST because it is
irreversible, and that ordering is what saved this.

The THREE RING STATES below are NOT superseded and stay exactly as they are.
They tell the player why a frame could not be read, which is still needed: the
router falls back to Vision, it does not make refusals invisible.

Original entry follows, kept for the record.

User's call. NOT IMPLEMENTED YET; `scanner.py` still holds the Vision path and it
is still what the live skill runs. Rationale and full design in Devlog
2026-07-31 (night), "DECISION".

When the local reader cannot read a frame, the ring tells the player instead of
falling back to a model. Three states, rendered bottom centre of the ring:

| state | shown when | player action |
|---|---|---|
| `NO SIGNAL` | overlay not on screen at all | type `r_displayinfo 2` |
| `GLARE` | scene too bright or busy to read | look at darker ground |
| `ACQUIRING…` | transient, position not yet confirmed | none, self-corrects |

Work this implies, in order:
- [x] **DONE 2026-07-31: the `NO SIGNAL` vs `GLARE` discriminator.**
      `overlay_reader.overlay_is_present` requires BOTH near-white ink
      (`> 0.005`) and row periodicity at ROW_PITCH (`> 0.15`). Ink alone is not
      enough: a blown sky is over 50 per cent near-white with no text in it, so
      the periodicity term is what makes it survive brightness. Tuned over 61
      overlay-present blocks and 132 scenery regions: 59/61 and 127/132.
      `overlay_fields.ring_state(rows, payload, overlay_present)` picks the
      message; ACQUIRING is chosen when a position line decoded but the payload
      was still refused, since that is transient. 420 tests.
      **VALIDATED ON BOTH SIDES 2026-07-31** with 20 frames captured live at
      `r_displayinfo 0` (`captures/nosignal-01`), replacing the cropped-scenery
      proxy: 57/60 present, 20/20 absent, zero false positives at any threshold
      from 0.05 to 0.3. The 3 misses are one fully blown block, which the capture
      precondition catches first so it never reaches here, and two login crops
      too short to hold row structure.
      **THE PROXY WAS HIDING A REAL BUG, which is why the real frames mattered.**
      The first `overlay_row_periodicity` was a single-lag autocorrelation, and
      ANY smooth profile correlates strongly with itself at every lag. A bright
      diagonal streak across the block scored 0.763, indistinguishable from text,
      and one of the live overlay-off frames read as GLARE because of it. Now
      measured as the pitch lag MINUS the mean of off-pitch lags, which cancels
      anything smooth. Regression test keeps a synthetic streak.
      Strings are ASCII on purpose (`ACQUIRING...`, not an ellipsis) because the
      ring renders through PIL and a missing glyph would show as a box.
- [x] **DONE 2026-07-31: state surfaced and rendered.** `navigation.ring_status`
      wraps `ring_deflection` and returns `(deflection, message)` so the two can
      never disagree; `ring_deflection` remains the single authority on whether a
      bubble may be drawn. `RingOverlay.set_state` gained a `message` argument
      and `RingRenderer.frame` draws it bottom centre in amber with a dark halo,
      cached per string. 433 tests.
      **DELIBERATE DEVIATION from the earlier note in this file:** a FRESH bubble
      and a message DO coexist. Blanking the bubble on every refusal would strobe
      it off and on over terrain, where most frames refuse, while a two-second-old
      fix is still inside the freshness window and worth pointing at. The bubble
      answers "where is it", the message answers "why is that not updating". A
      STALE bearing is still impossible, because `ring_deflection` returns None
      past the freshness window regardless of any message.
      Verified by rendering all four states to PNG and looking at them, and by a
      test asserting the message alters NO pixel in the bubble's half of the ring.
      `_MESSAGE_MARGIN` is 6 reference px, which sits close to the bottom edge;
      raise it if it ever looks cramped at another ring size.
- [ ] Then, and only then, strip the Vision path: `scanner.py`'s extraction
      prompt, the echo canaries, the plausibility gate and the two-capture wipe
      confirmation all exist to police a language model and become dead weight.
      Do this LAST; it is the irreversible step.
      **STILL DELIBERATELY NOT TAKEN as of 2026-08-02**, after the decision on
      this question changed three times in three days. Leaving it untaken is
      what made each of those changes cost nothing. NO AGENT MAY TAKE IT without
      an explicit instruction from Lars, and the OCR-only decision at the top of
      this file is NOT that instruction.
      **AND IT IS NOT DEAD CODE, which is a second and independent reason.**
      Roughly 40 test call sites reach still-live guards through
      `_parse_json_response`, including the unit-suffix requirement, the
      plausibility gate and the space-frame rules. Stripping would break a large
      fraction of the 654 tests, and there is no git recovery for it.
- [ ] Re-check `parse_payload`'s remaining guards still make sense with no model
      in the loop (the unit-suffix requirement and Root agreement DO; they guard
      the reader, not the model).

**Consequence to keep in view:** with no fallback, availability becomes
usability, and over sunlit terrain the reader currently refuses 62 to 100 per
cent of cells. On a daylit surface the ring will sit in a failure state almost
continuously. That makes the message load-bearing, and it makes the daylight
question below the most important open item in the project.

### 2026-07-31 NIGHT: live flight test done. Space is good, sunlit ground is not.
Read this first. Full reasoning in Devlog 2026-07-31 (night).

- **In space the reader is ready:** 20 frames of ordinary flight gave 17 usable
  (85 per cent), all cross-checked, 0 unverified emissions, 0 continuity breaks,
  17/17 Root agreement.
- **Over sunlit terrain it is UNUSABLE and this is now measured on real ground,**
  not on a deliberately extreme test capture: 62 to 100 per cent of cells refuse
  per row while the same frame is perfectly legible to a human. Geometry was
  ruled out first (pitch 7.5 confirmed by autocorrelation, row pitch 13,
  RIGHT_MARGIN sweep best at 7). Cause is that the dimmest channel over that
  terrain is B median 62 against the reference red wall's G median 2, so the
  per-cell background solve has nothing near-black to work against.
  **CONSEQUENCE: Vision stays required for daylit surfaces.** Do not plan a
  Vision retirement; plan a router.
  **THE MEASUREMENT STANDS. ITS INSTRUCTION IS VOID (2026-08-02).** Lars decided
  OCR only, no fallback, no router, with this refusal rate in front of him. The
  62 to 100 per cent figure is not disproved and must not be quietly dropped; it
  is an accepted cost. See the OCR-only decision at the top of this file.
- **NEXT QUESTION, and it decides the architecture:** is the surface use case
  (the whole point of the skill) mostly daylit? If so the local reader serves
  space and night/shadow only, and the split is permanent rather than temporary.
  Worth answering before any more optimisation work.
- **CAPTURE TOOL: always pass `--window=` for this user.** He runs SC windowed
  borderless with the terminal as an overlay and does not alt-tab, so the game
  rarely holds focus and the default filter skips nearly every grab. The `=` form
  matters: `--window ""` is dropped by PowerShell before argparse sees it.
  Verify a session by watching the FRAME COUNT climb, never by checking whether a
  process exists (Python is `python3.13.exe` here, which broke that check three
  times in one night).
- Corpus on disk: `preflight` 5, `dark-01` 20, `red-01` 150, `flight-01` 20,
  `bright-01` 11, `bright-02` 10, `terrain-01` 20. Sessions before `terrain-01`
  used a 640 px strip against the 667 px block, so they decode slightly clipped.
- Still owed, untouched by the whole day: the OOC branch has never run on real
  pixels, and `O` phase 0 is still missing. Both need a body surface, and the
  terrain finding means the capture should be at NIGHT or in shadow.

### 2026-07-31 EVENING: harvested, widened, gated, and ready for a live test
Supersedes the block below on the `k` question, which is CLOSED. Full reasoning
in Devlog 2026-07-31 (evening). 410 tests green. Nothing wired into `main.py`.

- **`k` phase 0 is harvested** from `red-01/frame_0024` and validated four ways
  (ADD not replace, occupancy gate, 0 regressions over the corpus, out-of-sample
  on six frames). Bank is 86 templates; previous state kept in
  `overlay_glyphs.bak-2026-07-31-before-k0.npz`.
- **Block widened to 88 cells / 660 px.** An 81-character line used to lose its
  leading `Z` in silence. Do not widen further: 96 gives the gain back and 104
  loses 8 trusted rows, because extra cells land on scenery.
- **The OOC gate is now a refutation** (`ooc_hypothesis_refuted`), so an
  unreadable ship or station zone name no longer blocks a space capture it was
  never evidence against. Down from a major blocker to 1 frame in 43.
- **The Root line is MANDATORY** on the local reader's space path. This is the
  failure-rate change: emissions without an independent cross-check went 3 to 0.
  Deliberately NOT enforced in `scanner.py`, so the Vision path keeps its
  tolerance for an omitted field.
- **The alignment fit is cached** (32 per cent of a cold read), keyed on frame
  shape, refitted every 20 reads, and self-healing when a cached origin decodes
  nothing.
- **Scoreboard, in the user's polarity:** 13 usable of 43, all 13 cross-checked,
  0 unverified emissions, 30 safe refusals (8 clipped, 18 no position row, 3 no
  Root, 1 gate). Was 4 usable before tonight.
- **The 1 Hz requirement:** facing clears it comfortably (CamDir-only read is
  152 ms, 14x cheaper than ten rows); a full position fix does not survive a busy
  scene alone, so the split cadence is REQUIRED. It is NOT built; this work only
  made it affordable.
- **Do not quote tonight's absolute timings.** A live benchmark returned warm
  slower than cold, and identical work showed 1.8x spread. Ratios only.
- Existing corpus strips are 640 px against a 667 px block, so `preflight`,
  `red-01` and `dark-01` decode slightly clipped. `session_log.py` now imports
  the geometry instead of mirroring it, so new captures are correct.
- **Unresolved, worth a glance:** `ocr_dev/glyphs.npz` and the six zero-byte junk
  files vanished from `ocr_dev/` around 18:11 with no command run that deletes.
  No data lost (the file was byte-identical to the surviving copy, and it has
  been recreated), but the cause is unknown.
- **Open from the widening:** `login` went from producing a valid-looking space
  payload to producing none. Plausibly a fix, since a phantom payload from the
  main menu was already logged as a concern, but it is NOT verified either way.

### 2026-07-31: the blocker is ONE glyph, and it needs RED LIGHT not darkness
Read this before the capture-session block below, which it partly supersedes.
Full reasoning in Devlog 2026-07-31.

- **The coordinate alphabet is one template short.** Digits, dot, minus, `m`, `k`
  at both phases is 28 pairs; 27 are in the bank with 100 to 300 observations
  each. The only absent one is **`k` phase 0**. The other 14 gaps are letters no
  coordinate contains. Tonight's station preflight refused all five frames on
  exactly this one cell, in the `km` of the second component, on both the
  SolarSystem and the Root line.
- **PHASE SYNTHESIS IS REFUTED.** Do not retry it. Four methods (linear and sinc,
  both directions) over 35 positive controls: best mean error 0.1106 against
  0.1196 for no shift at all. Held out against the real refused cell, all four
  still refuse, zero regressions. The phases are separate rasterisations, so a
  missing phase MUST be captured. This closes the question the 07-29 audit left
  open.
- **HARVEST WANTS A NEAR-ZERO GREEN CHANNEL, NOT A DARK SCENE.** `harvest.py`
  reads `frame[:,:,1]` hardcoded. The reference `game-mid` is a RED WALL at
  R 89 / G 2 / B 8, not a dark room: blank-cell green mean 2.07, max 4.0, sd 1.11.
  The `dark-01` hunt reached only 11.34 mean / 17.0 max / sd 2.58 on its best
  channel, because a dim GREY area lights every channel a little and zeroes none.
  Seek red lighting; a bright red surface beats a dark grey one. Flatness is
  already fine, only the level is wrong.
- **The `k` needs NO PLANET.** SolarSystem and Root lines are everywhere and the
  station already produced a phase-0 `k`. The planet trip is now a SEPARATE
  errand, needed only for the first real-pixel test of the OOC branch and for
  `O` phase 0, which is about naming bodies rather than reading coordinates.
- Whether a frame carries a phase-0 `k` depends on the coordinate digit counts,
  so if a good red-lit spot lands on the wrong parity, take a few steps and hold
  again.
- Corpus so far: `captures/dark-01`, 20 frames, all carrying a phase-0 `k`, all
  too bright in green. Keep for the refusal statistics, useless for harvest.
- **Offset model, corrected back:** length parity predicts the fitted offset on
  109 of 117 trusted rows, and all 8 exceptions are `ShardId:` at n=31. The
  letter/digit composition hypothesis is refuted (digit fraction spans 0.28 to
  0.65 within a parity class under one offset). UNTESTED: a trailing space would
  make ShardId 32 characters, which is even, which is the 0.5 it fits.
- **Do not re-derive a phase rule from one confirming instance.** A
  `phase = (1 + i) mod 2` rule was fitted to a single recorded misread and a
  whole body-ranking recommendation was built on it before anyone checked that it
  wrongly predicts `CamDir:` needs `D` phase 1, which is absent while that row
  decodes clean in every capture.

### DONE 2026-07-30: Phase 2's reader side, guards, parser and the join
`overlay_reader.py` (pixels to rows), `overlay_fields.py` (rows to fields) and
`overlay_glyphs.npz` now live in the skill directory as runtime files, with all
four guards, the fail-closed field parser and the join test. 381 tests. See
Devlog 2026-07-30. State to carry forward:
- Nothing imports them yet, so they are deliberately absent from BOTH release
  manifests. Add them to `skill_installer_config.json` AND `update_release.py`
  RELEASE_FILES in the same commit that wires `main.py`, never later.
- `NavPointScanner.parse_payload(dict)` is the shared validation entry point.
  The reader emits the Vision payload shape on purpose: one validation path, so
  a guard added for either reader cannot miss the other.
- **WIRING TRAP, measured 2026-07-30, do not reuse the Vision capture path.**
  The reader needs its own raw `mss` grab. `capture_screen_b64` produces images
  built for a language model, and both of its transforms destroy this reader:
  `_detail_crop` applies `ImageOps.autocontrast(cutoff=1)`, and the context
  image is resized to 1200 px wide (a 4.27x downscale on a 5120 px monitor).
  Fed the `game-mid` frame, native reads 8 of 8 rows trusted; autocontrasted it
  reads 0 of 8, and downscaled-then-restored 0 of 8. The model solves for the
  background by least squares in raw 0-255 units, so a contrast stretch changes
  the quantity being solved for and a resample mixes neighbouring cells (the
  drop shadow already bleeds exactly one column, which is why the outer column
  of each 8 px cell is masked). It does fail closed in both cases, refusing
  rather than emitting wrong digits, but a reader that refuses every frame is a
  reader that never replaces anything.
- The reader never emits `server_id`, so it can never drive a waypoint wipe.
- The LOCAL (OOC) branch is tested only against synthetic rows. It has never run
  on real pixels, because no lossless capture with an `OOC_` line exists. That
  is the same blocker as the alphabet gap, and the captures below close both.
- Speed, CORRECTED 2026-07-30 evening and it changes the Phase 3 priority:
  1.7 s per capture on an IDLE machine, but 4.5 to 4.9 s with Star Citizen
  actually running (measured with the game at 26 GB and the CPU at 84 per cent).
  The reader only ever runs with the game running, so 4.5 s is the real figure,
  and it is SLOWER than the ~3 s Vision call it replaces. Caching the alignment
  fit (~37 per cent of the work) and reading fewer colour/offset combinations
  per row are now REQUIRED for Phase 2 to be worth shipping, not Phase 3 polish.
  Run `session_report.py` after quitting the game: 500 frames is about 15
  minutes idle against about 40 with the game up.
- The precondition rejects 7 of 153 real screenshots as measured by the shipped
  code, not the 9 in the audit note.
- Open, low priority: a capture at the LOGIN SCREEN produces a valid-looking
  space payload (`SolarSystem_200000000001`, coordinates near zero). The Vision
  path behaves the same way, so this is not a regression, but marking a waypoint
  from the main menu now takes one deterministic read.

### The capture session
PARTLY SUPERSEDED 2026-07-31, see the block above: this is no longer "the only
blocking item" and it is no longer one errand. The `k` phase 0 harvest needs red
lighting anywhere at all, including in space; the OOC branch test and `O` phase 0
still need a body surface. Everything below still applies to the surface half.

PLANNED FOR 2026-07-31 (deferred from 07-30: humidity, and lightning near the
house forced a shutdown). Nothing was lost; all tools are on disk and tested.

SETTLED BEFORE THE DEFERRAL: the location is ON FOOT, ON A PLANET, in a complex
area with a messy background. That is the best available case, because it does
all three jobs in one session: refusal statistics from the messy background, the
FIRST REAL-PIXEL TEST of the local (OOC) branch, which today exists only against
synthetic rows, and the alphabet gap if a dark pause fits the route.

RUN IT AS ONE SESSION (user decision 2026-07-30). The passive logger covers the
whole session while the two surface stops happen inside it, so one flight
answers both questions. Tools built and self-tested the same day.

STEP 0, DO NOT SKIP: type `r_displayinfo 2` in the console manually (the skill
never types into the game, by the 2026-07-24 decision), then prove the setup
before spending a session on it. This project has already lost a full game
session to an unverified probe.

```
cd skills/sc_navpoint/ocr_dev
python session_log.py --label preflight --interval 2 --max-frames 5 --delay 12
python session_report.py --label preflight
```

Alt-tab back to the game during the 12 second delay. Five frames is enough to
confirm the overlay sits where the reader expects it. THEN the real run:

```
cd skills/sc_navpoint/ocr_dev
python session_log.py --label session-01 --interval 3 --max-frames 600 --minutes 90
```

At 3 s in a complex area almost nothing deduplicates, so 600 frames is about 30
minutes of walking. Two DARK pauses inside it, a decent walk apart: stand still
facing a dark wall or interior with the overlay up, a few seconds each. The
distance matters because different coordinates print different digit counts,
which shifts where each character lands and therefore its sub-pixel phase.

Then play normally. It grabs a right-aligned 640x180 strip (byte-identical
decode to the full screen, about 170 KB rather than 11 MB), captures only while
the Star Citizen window has focus, and skips frames whose only change was the
telemetry row, learning WHICH row that is from its change rate rather than
assuming an index. Somewhere in the session, stand on a body's surface facing a
DARK interior with `Zone: OOC_` visible, at TWO different locations, and hold
still a few seconds each. Afterwards:

```
python session_report.py --label session-01
```

which reports refusal rate by background regime, continuity breaks (the only
check that can catch a confident WRONG value without truth strings), the
Root/SolarSystem tripwire, and ranked harvest candidates for the alphabet gap.
Every detector in it was validated against known positives before use, since a
broken detector and a clean corpus look identical.

WHAT THE 500 FRAMES DO AND DO NOT BUY. They give the refusal rate in real play,
which nobody has and which decides whether the reader replaces Vision or merely
supplements it. They CANNOT give a character accuracy number, because the corpus
has no truth strings, and they cannot close the alphabet gap by volume: phase is
fixed by the parity of a line's own length, so 500 frames at one location are
one sample computed 500 times (the reader is deterministic on identical pixels,
re-verified 2026-07-30). Only the two surface stops close it.

TWO captures, not three. The high-frequency background question the
`starfield` row asks was answered on 2026-07-30 by the capture that landed in
`captures/starfield`, which is the Nyx glacier ring rather than a star field:
dark teal with bright ice debris, block mean 68.9, p95 213, 2.1 per cent
clipped. That is genuinely high frequency and it is what forced the ink guard's
threshold to become hybrid. A literal star field is still welcome as a different
mechanism, but nothing waits on it.

All of them: `r_displayinfo 2` or higher typed manually by the
player, nothing covering the top-right block, and captured LOSSLESS with the dev
tool, never the game's screenshot key (that writes JPEG). From
`skills/sc_navpoint/ocr_dev`:
`python capture_overlay.py --label <name> --delay 12 --shots 5`.

| label | where to be | what it settles |
|---|---|---|
| `surface-a` | on a named body's surface, `Zone: OOC_...` line visible, facing a DARK wall or interior | closes `k` phase 0, `O` phase 0, `u` phase 1, the entire measured alphabet gap |
| `surface-b` | same, at a DIFFERENT location on any body | the single `O` per frame is a coin flip between the two phases, and repeating one standing position cannot change it, since identical digits give identical phases |
| `starfield` | open space, dense bright stars filling the TOP-RIGHT of the screen behind the block, ideally one star bright enough to nearly clip on its own | the one background never tested: whether the ink guard's zero false positives over 2756 blank cells survives a HIGH-FREQUENCY background. A single bright star pixel inside a blank cell's 6-column window could push its spread past the threshold with no ink present |

Not a bright sky for the surface pair: harvesting a coverage map needs a channel
whose background sits near zero, and the blown-sky capture measures 211/255 on
green, which is unusable. A dark interior worked because its green channel sat at
2/255.

Optional fourth if the mood strikes, `hud-edge`: the block sitting over a bright
cockpit reticle, icon or frame line. Same question as the starfield
(high-contrast non-text structure behind blank cells) by a different mechanism.

The surface pair also supplies the third differently-lit frame needed to settle
two held decisions, the attenuated shadow model and the MASK width. See
LocalOcrPlan.md, "REMAINING before Phase 2", items 1, 6 and 7.

### Then, in order
1. **Phase 2, with FOUR guards that are now specified rather than assumed.**
   Calibrations and evidence in LocalOcrPlan.md items 0 to 15; do not re-derive
   them, and do not loosen `REFUSE_COST` above 17 (orange's proven digit floor is
   17.13 and the nearest known-bad candidate of 28234 sits at 17.94).
   - capture precondition: reject if any row is 15 per cent clipped, on FIXED
     geometry, never on the reader's own fitted origin
   - ink contradiction: `max(50, 6 * row background median spread)` against a
     blank decode. The hybrid form is essential; a flat 50 misfires on 14.6 per
     cent of blanks over a structured background, and 98 per cent of real play IS
     structured
   - flat-white: spread under 5, mean at or above 250, at least 40 above the row's
     own background
   - structural: per-kind FULL-line shape match. Most of this already exists on
     the consumer side, so the work is one fail-closed field parser that emits
     three unit-suffixed tokens or nothing
   The first test to write is NOT a guard test. It is a JOIN test driving
   `_capture_position` from real reader output, because the reader's row dict and
   pos_data share no code path today and every existing test on either side
   supplies its own already-final fixture. That is the same shape as the July
   defect where scanner and guidance both tested green and the join between them
   was never exercised.
2. **Phase 3 is ACCURACY-FIRST** (user decision 2026-07-30, about 5 Hz is enough).
   Batching the per-template loop is DONE (2026-07-30) and was a prerequisite
   rather than a speed item: 17.3 s to read ten rows became 1.7 s, and the two
   forms agree to 2.8e-14, so the recorded "bit-identical" is too strong. Still
   to do: cache the alignment (fit was identical across all 20 frames,
   re-validate periodically) and grab the strip not the monitor (42.9 ms to
   4.1 ms). Then spend the freed budget
   on a five-grab MEDIAN cost estimate, never a min-cost vote. Candidate-alphabet
   restriction and the parallel pipeline are both dropped, with reasons recorded.
3. The space-direction gate (`SPACE_DIRECTION_CALIBRATED`) opens only after the
   reader is deterministic. The geometry is already validated three ways. NOTE:
   the LOCAL reader is now proven deterministic (five runs over one screengrab
   give bit-identical output), so this gate's precondition is met the moment the
   reader becomes the position source; it was the VISION path that corrupted one
   capture in three.
4. `space_direction_test` is currently ON in the live config. It draws the ring
   in open space from a convention that is now known to be correct, but fed by
   the Vision reader that corrupts one capture in three, so the bubble jitters.

### Audit results worth not rediscovering (2026-07-29)
- The reader never emitted a wrong character on any unmodified capture: 20
  lossless frames, about 1470 truth cells, plus noise to sigma 30, gamma 0.67 to
  2.0, and 144 synthetic backgrounds including stripes at the exact cell pitch.
  Degradation always goes to refusal and the alignment fit never broke.
- Every breach found under perturbation is a LOW-INK glyph (underscore, hyphen).
  Digits are the safest class in the alphabet, which inverts the old assumption.
- `Zone: Root` agreeing with `Zone: SolarSystem` is NOT a correctness check. Both
  lines decoded the same wrong coordinate on the bright capture, because they
  share x positions, phases and background. Confabulation tripwire only.
- The confidence floor's real headroom is 2.94 cost units. `REFUSE_MARGIN` is
  inert across 28234 known-bad samples: `REFUSE_COST` carries the guarantee.
- Two dev tools were silently broken and are fixed: `harvest.py` imported a
  `measure.py` global that is only filled inside `main()`, so it died on every
  run since measure grew a second capture; `extend.py` rebuilt from the login
  base and would have discarded the harvested bank on its next run.
- `measure.py`'s blank test compared spread ACROSS channels, which a flat
  coloured wall produces by itself, so it certified nothing. Per-channel spread
  separates blank (0-19) from ink (99-255) over 680 cells.


v4.9.0.20 (2026-07-28): the ring is now drawn OVER THE GAME, in a click-through
Win32 layered window anchored to the top centre of the screen, instead of only
on a browser page that cannot appear over a game. This is LocalOcrPlan Phase 4,
taken ahead of Phases 1 to 3 by user decision; the rendering surface no longer
blocks anything. Proven by probe: on screen, correctly placed, click-through,
0.431 ms per frame. NOT proven with Star Citizen running, and it needs
borderless windowed. 330 tests. Internal update, NOT a requalification, NOT
installed live.

Open follow-ups from this change:
- [ ] Live check with SC running borderless: does the ring appear over the game,
      and does it survive alt-tab and a resolution change.
- [ ] The ring glides at 30 fps but its INPUT is the 5s poll, so it is smooth
      between stale fixes. Fixing that is the local reader below, not the
      overlay.
- [ ] Untested at DPI scaling other than 100%.
- [ ] The browser page still computes its own ring feed in JavaScript while the
      overlay uses `navigation.ring_deflection`. Same inputs, two
      implementations; fold the page onto the Python one when the page's ring is
      next touched.

## Next major work: replace Vision AI with a local reader
See [`LocalOcrPlan.md`](LocalOcrPlan.md) (2026-07-27). Decided with the user
after the 2026-07-26 session: the current reader costs ~3050 tokens per capture
(~2.2 M/hour at the 5s interval, ~110 M/hour at the 10 Hz the ring needs), and
every confabulation incident in this skill's history is a language model reading
digits. Local reading measured at 5.18 ms with effectively deterministic glyph
rendering (NCC 0.949-0.999 for identical text over varying backgrounds), and the
labelled validation corpus already exists on disk. Phases: reader offline ->
position source -> raise the rate -> (separately) standalone overlay, because a
browser page cannot draw over a fullscreen game, which is why the ring has never
once been visible.


v4.9.0.8 (2026-07-26): local XYZ moved off `CamPos Planet Zone`, which SC 4.9
omits on a planet surface, onto the OOC zone `Pos:` line via unit-suffixed
`pos_raw` tokens converted in Python. Unit suffixes are mandatory (a missing one
refuses the capture rather than risk a 1000x error), the two readings are
cross-checked when both exist, and the echo canaries now cover raw tokens and
survive unit conversion. 190 tests. Internal update, NOT a requalification.
NOT installed: the live env runs 4.9.0.7, which cannot mark on a surface on this
build. See Devlog for the full rationale and for one PROPOSED geometric gate
(`|pos| == radius + elevation`) deliberately held back pending a second
observation.

## Status
PARTIAL HOLD LIFT (2026-07-12). Scope is fixed to surface-only navigation at
planetary and moon surfaces in the static local frame (2026-07-11 field test;
stellar coordinates dynamic, permanently out of scope). The planet-tech-safe
plumbing is IMPLEMENTED as of 2026-07-12 (v4.8.0.1, see Devlog); the Vision AI
recalibration and all in-game verification stay parked until the overlay
screenshots exist or Lars accepts the planet-tech redo risk (release estimated
late 2026 to early 2027). Split rationale in Devlog.md (2026-07-12 entry).
`auto_activate` stays disabled.

Version aligned to the 4.9.0 line (v4.9.0.0) on 2026-07-18 by user decision (all four SC skills moved together); in-game requalification against 4.9.0 remains pending and the verification hold above is unchanged.

Release packaging exists as of 2026-07-21 (update_release.py +
skill_installer_config.json + release_version/, see Devlog); keep both
manifests in sync when adding runtime files.

v4.9.0.7 (2026-07-24): ALL game-input capability removed by user decision (CIG
cheat-risk): enable_displayinfo/disable_displayinfo tools, _send_console_command,
console_key property, and the vendored pydirectinput package deleted. The skill
now only instructs the player (hints reworded to relay-verbatim manual steps);
prompt gained a relay-hints-verbatim rule. release_version rebuilt from the
cleaned tree; installed live same day.

v4.9.0.6 (2026-07-24): console key hint corrected (F1 -> tilde) in the two
mark_location error hints and the default_config.yaml prerequisites line; no
behavioral change. Installed to the live env same day.

v4.9.0.5 (2026-07-22): confabulation gate + fixed-pixel crop + metadata cleanup
(see Devlog). During the 4.9.0 requalification flight the Vision model, in a Nyx
asteroid-base hangar with no OOC_ line and the planet lines entirely absent,
recombined the prompt's last realistic example into a plausible-looking
local-frame payload; the exact-value echo tripwire missed it. Added a
deterministic plausibility gate (body_token must be System_designator_Body
leading with a known system: stanton/pyro/nyx, else implausible_body reject +
one-time badge), canaried the last realistic example
(Hangar_ExampleSize_ExampleCity), replaced the fractional detail crop with a
fixed-pixel native-resolution box (the overlay is fixed-pixel; a fractional crop
shrank text 2.56x on ultrawide), updated the prompt for the observed 4.9
no-planet reality, and reworded the no-frame refusal. Also cleared the stale
"Outdated" metadata from default_config.yaml (presentation only; the
verification hold and auto_activate:false stand). 160/160 tests. Internal
update, NOT a requalification.

v4.9.0.4 (2026-07-20): Vision example-echo defense (see Devlog). Prompt example
values replaced with obvious canaries, deterministic echo tripwire in the
scanner (rejects a parroted example, one-time chat badge), and two-capture
confirmation before wipe-on-relog so a single hallucinated server_id can no
longer delete waypoints. 147/147 tests. Internal update, NOT a requalification.

v4.9.0.3 (2026-07-20): mark_location description hardened against the
game-state intent hijack (see Devlog). Internal update, NOT a requalification.

v4.9.0.2 (2026-07-19): two-stage arrival alert (spoken heads-up at 1 km,
auto-stop of navigation at 250 m confirmed by two consecutive polls; both
configurable, 0 disables), configurable console key with backquote fallback,
HUD ARRIVED/APPROACHING tags. 128/128 tests. Internal update, NOT a
requalification.

v4.9.0.1 (2026-07-19): position freshness window (30s, closes the stale-409
known issue), wipe-on-relog on proven server change (SUPERSEDES the cross-server
stability verification; per-server keying resolved, server filter removed from
HUD and tools), and the deflection ring HUD instrument (bubble-in-circle,
concentric = dead ahead, wall contact = 45 deg+, full green-amber-red gradient
by total offset, north-referenced until the parked heading verification lands).
69/69 tests. Internal update, NOT a requalification.

v4.8.0.1 — surface-only safe plumbing landed (body-keyed schema v2, cross-body
refusal, no-local-frame guards, HUD body filter, tests/). Still NOT requalified
against the live SC patch; do not bump to the SC version until the parked
verification runs.

v4.8.0.3 (2026-07-16): Vendored pydirectinput-rgx 2.1.3 into the skill dir
(pure-python __init__.py + py.typed + LICENSE.txt) after the first live
activation crashed with ModuleNotFoundError: the frozen Wingman build bundles
only what the core imports, so it lacked the package. Import unchanged; the
existing sys.path insert resolves the vendored copy.

v4.8.0.2 (2026-07-13) — Vision AI extraction recalibrated to the real 4.8
overlay (OOC_* local-frame gate, CamPos Planet Zone coordinates, level 2-4,
autocontrast preprocess; 45/45 tests). Remaining before requalification is
IN-GAME only: live guard tests, heading semantics, cross-server stability.

## Pivot Tasks: planet-tech-safe (DONE 2026-07-12, v4.8.0.1)
- [x] Decide declared nav scope: DECIDED short-range surface navigation; flat
      Cartesian bearing math in navigation.py kept as-is (far targets on a
      curved surface get through-the-planet bearings and chord distance,
      accepted and documented)
- [x] Rework database schema: body is a required key (schema v2 via PRAGMA
      user_version; ValueError on empty body)
- [x] Navigation and HUD refuse cross-body targets; HUD filters by body
- [x] Wipe stored pre-4.7 stellar waypoints (pre-v2 DBs dropped and rebuilt on
      init; no migration; warning logged when a non-empty table is wiped)
- [x] Guard states in main.py and UI for "no local frame present" (open space)
- [x] Decide fate of per-server keying: KEPT for now; drop only after the
      parked in-game verification proves local frames deterministic per body

## Pivot Tasks: planet-tech-risky (UNBLOCKED 2026-07-13; screenshots done)
- [x] Collect 4.8 overlay screenshots: on-surface, in open space, in flight above
      a surface. DONE 2026-07-13 (40 shots in `screenshots/`: hangar level
      ladder 1-4 + full space->Clio journey at level 1). Analyzed and
      validated; field inventory + extraction rules in
      `screenshots/overlay-field-inventory-2026-07-13.md`.
- [x] Apply the r_displayinfo 2-4 decision. DONE 2026-07-13, v4.8.0.2: docs
      reworded to level 2 ("or higher" where natural), enable_displayinfo
      types `r_displayinfo 2`, prompt tolerates the level 2-4 line variance.
      PARTLY SUPERSEDED v4.9.0.7: enable_displayinfo is gone, so nothing types
      the command; the level tolerance in the prompt still applies.
- [x] Rework scanner extraction to read the LOCAL coordinate set only; refuse
      capture when no local frame is present. DONE 2026-07-13, v4.8.0.2:
      OOC_* Zone-stack gate (never field presence: stale-body trap), XYZ from
      CamPos Planet Zone (meters), deterministic body/system split from
      body_token, raw camdir stored (heading no longer emitted),
      autocontrast preprocess on the detail crop. 45/45 tests green.
      See Devlog 4.8.0.2.
- [x] HEADING SEMANTICS VERIFIED 2026-07-26, three surface sweeps on Daymar.
      `euler = (-camdir[0], camdir[1], camdir[2])`, extrinsic `yxz`, in the
      BODY-FIXED frame; forward = first column; project onto the local basis at
      the player's position for a bearing. Fitted at WolfPoint, applied blind at
      Nuen and Dunlow. Accuracy about 1 to 2 deg with a level view; no
      position-dependent correction needed beyond the local basis. Full
      derivation, the three refuted models, and the capture-quality analysis are
      in the Devlog entries of that date.
- [x] CamDir -> heading conversion: IMPLEMENTED v4.9.0.9 (2026-07-26).
      `navigation.camdir_to_bearing` plus `local_basis` and `surface_bearing`;
      `_capture_position` populates `heading` when CamDir is present and leaves
      it unset otherwise; all three `calculate_bearing` call sites now use
      `use_local_frame=True` so a real heading is compared against a real
      bearing. 218 tests, the new ones asserting against the measured in-game
      compass across all 39 field frames. NOT yet installed (live runs 4.9.0.8).
      REMAINING for the ring itself: confirm in game that the deflection ring
      now points correctly, which is a requalification-checklist item rather
      than more code.
      SUPERSEDED HYPOTHESIS (user, 2026-07-19, from a live space screenshot,
      CamDir: -24 -19 -41): ordering (pitch, roll, yaw) with heading =
      camdir[2]. REFUTED 2026-07-26 by paired CamDir-plus-compass frames on
      Daymar (compass headings measured geometrically from label positions,
      sub-degree, tool validated against hand reads):

      | frame | CamDir | compass |
      |---|---|---|
      | 14:00:32 | 8, 33, 159 | 70.40 deg |
      | 14:03:16 | 35, 0, -126 | 358.28 deg |
      | 14:05:38 | 35, 0, -120 | 358.19 deg |

      NO component is the heading: the last two frames have the SAME compass
      heading (identical label pixel positions) but third components differing
      by 6, so that component tracks something that does not change bearing,
      almost certainly pitch since the player was stationary. Conversely the
      first frame differs from the second by 72 deg of bearing while no
      component differs by 72.

      ALSO REFUTED the same day: treating CamDir as a direction vector in the
      body-fixed frame and projecting onto a local north/east basis built from
      the player position (9810.08, -174288.0, 238051.1). That predicts ~205 deg
      for the 14:03:16 frame against a measured 358 deg. The basis itself checked
      out (east came back unit-length and orthogonal), so the arithmetic is sound
      and the interpretation is wrong. Component semantics are therefore UNKNOWN,
      not merely untransformed.

      STRUCTURAL REASON they can never match: a compass bearing only exists
      relative to a position, because north on a sphere points in a different
      direction in space at every latitude and longitude. The compass is measured
      in a local tangent frame rebuilt at each point; CamDir is reported in a
      frame that does not know where the player stands. Any conversion MUST take
      position as an input.

      SWEEP RUN AND ANALYSED 2026-07-26, see Devlog entry of that date.
      ANSWER: `heading = (k - camdir[2]) mod 360`, slope exactly -1 (yaw counts
      the opposite way from the compass), k = 274.15 (stdev 1.07, worst residual
      2.15 deg) at the sweep position. 13 frames, 30 deg steps, exact closure.
      camdir[0] and camdir[1] do NOT hold still at level view: they rotate as a
      ~10 deg magnitude pair, so the CamDir reference vertical is about 10 deg off
      local up. Never assume level view means zero pitch and roll.
      STILL BLOCKING the surface conversion: the sweep was inside
      `Hangar_MediumFront_Kaboos_Nyx` with NO OOC line, so k is calibrated for a
      station frame and NOT for a planetary local frame.

      THREE-LOCATION SURFACE PROTOCOL (user, 2026-07-26), the deciding test:
      - THREE positions on ONE body, same session, no relog, OOC line present at
        each. Three rather than two because a position-to-offset model has two or
        more free parameters, so TWO measurements fit any such model perfectly and
        test nothing. The third produces a residual, which is what turns a fit
        into a test.
      - PLACEMENT decides whether the data can answer the question. Spread the
        three as widely as the body allows and vary BOTH latitude and longitude:
        three points sharing a latitude leave the latitude term untested, three
        sharing a longitude leave the longitude term untested. On Daymar (R = 295
        km) one degree of arc is 5.15 km and the fit noise is about 1 deg, so
        neighbours a few km apart produce a sub-noise difference and prove
        nothing. Aim for 50 km minimum between any pair (about 10 deg), 150 km
        (about 30 deg) for an unambiguous result.
      - PER LOCATION: 3 to 4 frames spread around the circle is now enough, since
        the slope is pinned at -1 and k falls out of a single frame as
        `heading + camdir[2]`; extra frames only average down the noise. Spend the
        saved effort on the aiming shots below.
      - AIMING SHOTS: from each location, face each of the other two directly and
        capture. Six frames total. These give ground-truth bearings straight off
        the compass, independent of every assumption in the extraction chain, and
        they close the parked "validate bearing/compass math between two known
        surface points" item in this same file.
      - FREE BONUS CHECK, no extra capture: the interior angles of the spherical
        triangle (each the difference of the two bearings measured at that vertex)
        must sum to 180 deg PLUS the spherical excess, E = area / R^2. A triangle
        with 150 km legs on Daymar gives roughly 6 deg of excess against about 2.6
        deg of combined measurement noise, so it is detectable and it validates
        that the local tangent frames are mutually consistent across the body,
        which is exactly the assumption the offset model rests on.
      - ALSO VALIDATES 4.9.0.8 END TO END: direct-line distances computed from the
        extracted pos_raw coordinates must match the known distances between the
        locations. That is ground truth from outside the code, unlike the unit
        tests, which encode the author's own assumptions.

      PREDICTIONS, recorded before the data: if yaw is referenced to a fixed body
      axis, each location's k is computable from its position via the local north
      basis, and pairwise k differences track the longitude differences. Holding
      across all three means the conversion needs no per-location calibration
      anywhere on any body, and the ring becomes correct rather than
      north-referenced by assumption. Differences that are real but not
      position-predicted mean per-location calibration, which changes the design
      and is worth knowing BEFORE anything is built.

      ORIGINAL EXPERIMENT SPEC (user, 2026-07-26), kept for the re-run: full 360
      on foot, elevation held at zero, screenshot every 30 deg (the compass is
      labelled every 30), one position, no relog. Predictions were recorded
      BEFORE the data, so the analysis could not be fitted after the fact:
        - exactly ONE component sweeps the full range (yaw); the other two stay
          near-constant (pitch held, roll zero upright). Two movers means neither
          the Euler nor the vector reading covers it.
        - if that component plots against measured heading as a straight line of
          slope +/-1, the conversion is heading = +/-yaw + constant AT THIS
          POSITION, and the constant carries the position dependence.
        - if it is not linear with unit slope, CamDir is a vector and the vector
          fit gets tried against the sweep instead.
      Step precision does not matter: the true heading is read off each frame.
      A second sweep at a very different latitude supplies the second constraint
      on the position term. Analysis tooling ready and validated (batch crop plus
      geometric label measurement; it reproduces all three hand-measured headings
      above, after a first version returned a plausible 35.8 deg for the 358 deg
      frame because a chat-text blob corrupted the label spacing).
- [ ] Verify heading semantics in the local frame; validate bearing/compass math
      between two known surface points (IN-GAME)
- [x] Cross-server stability of local coordinates: SUPERSEDED 2026-07-19 by
      the wipe-on-relog decision (waypoints do not survive a proven server
      change; server_id stays as wipe trigger + provenance only), so the
      verification is no longer needed
- [x] Local-frame availability while flying above a surface: ANSWERED YES by
      the 2026-07-13 screenshot data (OOC line + meaningful CamPos through the
      whole descent), so in-flight guidance toward a surface waypoint is
      structurally possible; confirm skill behavior live at requalification
- [ ] Update default_config.yaml description/tags and remove Outdated markers
      only after end-to-end re-validation

## Verified Patterns
- sys.path.insert pattern required for all sibling imports (confirmed working)
- @tool decorator supports async methods (confirmed in vision_ai skill)
- mss screen capture + PIL.Image.frombytes("RGB", ..., "raw", "BGRX") pattern from vision_ai skill
- FastAPI explicit static route (no aiofiles) from sc_accountant pattern

## Testing Checklist
- [ ] mark_location — r_displayinfo 4 visible, captures correct XYZ
- [ ] mark_location with no r_displayinfo: the wingman must relay the hint
      VERBATIM, naming the tilde key and telling the player to type it manually
      (v4.9.0.7 relay-verbatim rule; the 4.9.0.6 live test showed the LLM
      paraphrasing the hint and dropping the key name)
- [ ] navigate_to — bearing calculation, deflection ring direction and gradient
- [ ] Auto-polling — deflection ring glides on each update without voice command
      NOTE 2026-07-26: this never worked before v4.9.0.15. `asyncio.create_task`
      in a tool call was silently abandoned when that call's event loop stopped,
      so the loop ran to its first await and stopped forever. Polling now runs on
      its own thread with its own event loop. The arrival heads-up and auto-stop
      items below ride the SAME loop, so they were equally dead and are equally
      untested in the field.
- [ ] stop_navigation — polling task actually cancels
- [ ] HUD — waypoint list renders, body filter works, ring draws
- [ ] HUD — click waypoint → set as nav target → ring updates
- [ ] HUD — stale position (stop polling, wait 30s+): position box dims with
      STALE tag, ring drops to the '?' face, no bearing shown
- [ ] Wipe-on-relog — relog to a new server, first capture wipes old waypoints
      and posts the WARNING chat badge
- [ ] poll_interval setting — change to 2s, confirm faster updates
- [ ] Arrival heads-up — approach a target, expect one spoken "Approaching"
      announcement near 1 km, no repeats
- [ ] Arrival auto-stop — close within 250 m, expect "Arrived" announcement
      and navigation ending only after two polls (10s at default interval);
      HUD shows APPROACHING then ARRIVED tags on the distance readout

## Probe: paired frame-stability test (2026-07-25, decides space scope)
Cheap data capture only, NOT a scope commitment. Piggyback on any flight.
Design is Lars's (2026-07-25): run the SAME protocol in space AND on a planet
in one session, so the surface run is the positive control for the space run.

**Protocol, both runs identical.** `r_displayinfo 2`, stay completely still,
capture the overlay at t+0, t+2min, t+5min. No stopwatch needed: the overlay
carries `ServerTime:` and `UniverseTime:` lines, which timestamp each shot from
inside the game and give exact deltas.

**RESULT 2026-07-26: PASSED, both runs, exactly the predicted matrix.** Full
transcription, computations, and consistency checks in Devlog 2026-07-26.
Headline: space system-frame coordinates byte-identical over 5 min; Daymar
surface body-frame static (4 cm) while its system frame drifted 37.5 km at a
constant 122.7 m/s with dz exactly 0. The drift mechanism is the rotating
attachment, not the frame. Space waypoints are viable in the system frame.

- [x] RUN A, open space: park well away from any body, far enough that NO
      `OOC_*` line appears in the Zone stack. Confirm speed reads 0 before t+0.
      DONE 13:11:32/13:13:32/13:16:32, stack was Clipper -> SolarSystem -> Root
      with no OOC line, ship-internal Pos constant so the player never moved.
- [x] RUN B, planet surface: on foot, standing still, on a named body.
      DONE 14:00:32/14:03:16/14:05:38 on Daymar. Implied rotation period
      2 h 29 m, and distance from body centre 295.196 km against the overlay's
      own Radius 295.000 km, so the geometry closes on itself.

**Confounds that silently ruin it, all avoidable:**
- Residual ship velocity in run A. Engines off is not the same as at rest;
  a decoupled drift shows up as a clean linear change and looks exactly like
  frame instability. Verify speed 0, not just hands off the throttle.
- Moving inside the ship in run A. The coordinate is the PLAYER position, not
  the ship's, so walking around the cabin between shots registers as drift.
  Stay in the seat. Looking around is fine, CamDir is not position.
- Do not relog or change server between the two runs, or the cross-session
  question contaminates the stability question. One session, both runs.

**What each cell proves** (read the `Zone: SolarSystem_<id> Pos:` line in both
runs, plus the `OOC_*` and `CamPos Planet Zone` lines in run B):

| | local frame (OOC / CamPos) | system frame (SolarSystem) |
|---|---|---|
| run B, surface | expect STATIC | expect DRIFT, rate = body rotation |
| run A, space | absent by design | expect STATIC (the hypothesis) |

That exact pattern is the airtight result: the frame was never the problem, the
rotating attachment was. Space waypoints then live in the system frame, surface
waypoints stay in the local frame, and the two never mix.

Surprises to catch rather than explain away:
- Surface SolarSystem does NOT drift: contradicts the 2026-07-11 finding, and
  the whole coordinate model needs rework before anything is built.
- Surface local DOES drift: serious, invalidates the existing surface scope.
- Space SolarSystem drifts LINEARLY: almost certainly residual velocity, retry.
  Drifts erratically: the system frame origin itself is unstable, scope closes.

- [x] Vertical check: RESOLVED 2026-07-26. Z identical on the OOC and
      SolarSystem lines (238.0511km both), reproducing the Clio sample, and
      unchanged across all three shots while X and Y moved. Body centres sit at
      system Z = 0 with aligned axes, so the transform is a Z-axis rotation plus
      an XY translation and Z passes through untouched. Vertical IS usable: run
      A showed a live system Z of 19428930.4479km, so it is a real coordinate.
      Frame model: `system_xy = rotate_Z(theta(t)) . body_xy + centre_xy(t)`,
      `system_z = body_z`.
- [x] Cross-session origin check: DROPPED 2026-07-26, not needed. User decision:
      waypoints are only ever stored within a session, so cross-session
      continuity is not a requirement. This is already enforced in code, not just
      intent: `database.py wipe_on_server_change` deletes waypoints whose stored
      non-empty server_id differs from the current one, `main.py
      _handle_server_change` requires two consecutive captures agreeing on the
      new server before wiping, and a blank server line never wipes. The space
      path inherits this unchanged, because the overlay's `Server:` line IS
      present in open space (confirmed in the 2026-07-20 4.9 observation), so no
      new wipe logic is needed.
      RESIDUAL, narrow and accepted unless it proves otherwise: the wipe triggers
      on server CHANGE, so relogging into the SAME server would not fire it. If
      the frame origin were session-scoped rather than shard-scoped, coordinates
      would go stale silently in that one case. Cheap optional hardening, worth
      taking because it costs nothing: store the `SolarSystem_<id>` zone id
      alongside the coordinates and require a match on read. Observed ids differ
      per session so far (729494885309 on 2026-07-26, 653869999737 on
      2026-07-13), which HINTS the id tracks the frame instance, but that is two
      data points, so treat the id as an extra signal and not a replacement for
      the server guard. It can never cause a false wipe, so the downside is zero.

## Design constraints for a space path (from the 2026-07-26 probe)
- **Per-component unit autoscaling is the main hazard.** Zone `Pos:` lines pick
  the unit PER AXIS by magnitude and mix them in one line
  (`9810.08m -174.2880km 238.0511km`); threshold bracketed between 9.81 km and
  14.93 km, probably 10 km, not pinned. The surface path avoids this by reading
  single-unit-metres `CamPos Planet Zone`; a space path cannot, because deep
  space has no CamPos equivalent. A dropped `m` is a silent 1000x error with a
  plausible-looking value, the exact failure shape of the 07-20 and 07-22
  incidents. Capture the unit token per component and convert in Python; never
  let the model pre-normalise.
- **Free confabulation tripwire: `Zone: Root` duplicates `Zone: SolarSystem`
  digit for digit** in all six 2026-07-26 shots and both 4.8 samples. Require
  the two to agree and reject the parse otherwise. Stronger than canaries, since
  it validates the actual payload instead of checking for known-bad values.
- The OOC gate stays exactly as it is and becomes the router: OOC line present
  means surface path and local frame, absent means space path and system frame.
- **Server identity is coarser than frame identity.** SC lets the player pick a
  region, never a server, and a region holds many servers (user, 2026-07-26), so
  a relog lands somewhere semi-arbitrary and the existing wipe fires on nearly
  every relog by itself. That is the session scoping working as intended. The
  gap is the other direction: the overlay line is
  `Server: <token>, restarts N, pop. [shard N, srv N]` (scanner.py prompt) and
  the scanner extracts ONLY the token, so a server that RESTARTS keeps its token
  while its entity ids, and therefore plausibly its frame origin, are renewed.
  Prefer the `SolarSystem_<id>` zone id as the frame guard rather than adding
  restarts/shard/srv: the zone id is the identity of the very frame the
  coordinates are expressed in, and it sits on a line the space path must read
  anyway, so it adds ZERO extraction surface, whereas pulling three more fields
  off the Server line would add confabulation surface for weaker evidence.
- The existing plausibility gate REQUIRES a known-system body token, so a space
  payload fails it by construction. A space-side equivalent is needed before any
  space capture can be trusted.

**Delivery:** drop the raw screenshots in this folder. No cropping needed, the
analysis side crops the top-right block at full resolution (the 5120x1440
downscale legibility hazard from v4.9.0.5 applies to reading them too).

Why this is worth asking: the 2026-07-11 verdict closed the stellar frame
because coordinates drifted while standing still, and the mechanism given was
body axial rotation. That applies to points ON a body. A point in open space is
not attached to a rotating body, so the test never covered it. Note also that
the space capture would read a DIFFERENT field than the surface path
(`Zone: SolarSystem Pos`, mixed km/m units) because `CamPos Planet Zone` is
body-relative garbage in deep space.

## Known Issues
- The 4.8-calibrated Vision prompt keeps misreading the 4.9 overlay. On
  2026-07-20 it echoed its worked example verbatim in open space (Nyx), tripwired
  in v4.9.0.4 (canary values + exact echo rejection + two-capture wipe
  confirmation). On 2026-07-22, in a Nyx asteroid-base hangar with the planet
  lines entirely absent, it RECOMBINED the last realistic example into a
  plausible-looking local-frame payload that the exact-value tripwire missed;
  addressed in v4.9.0.5 (deterministic plausibility gate on body_token +
  canaried that example + prompt updated for the no-planet reality). Both
  incidents point the same way: the 4.9 overlay text differs enough that the
  model falls back to the prompt when it cannot read it, so a full 4.9 overlay
  recalibration is still owed at requalification. The fixed-pixel native crop
  (v4.9.0.5) should improve legibility and is the first thing to re-check live.
- [FIXED v4.9.0.1] HUD cross-body refusal (409 on set_nav_target) compared
  against the last cached position with no age check; a 30s freshness window
  now gates the refusal and the SPA's bearing/ring rendering.
- [RESOLVED v4.8.0.2] scanner `body` was an interim parse-side mapping (moon
  over planet); the real local-frame body extraction (OOC_* body_token split)
  landed with the extraction recalibration.
- Unit tests must be run from the tests directory
  (`cd skills/sc_navpoint/tests && python -m pytest .`); from the repo root
  pytest imports the skill package, which needs the Wingman venv.

## Planned Features
- [x] Arrival alert: DONE v4.9.0.2 (two-stage: heads-up 1 km + auto-stop 250 m,
      both configurable)
- [x] Console key configurable: DONE v4.9.0.2 (`console_key` property,
      backquote fallback). REMOVED in v4.9.0.7 together with all game-input
      capability; the property no longer exists and the skill never types into
      the console. The player enables `r_displayinfo` manually.
- RETIRED 2026-07-19: bundle MinersRefuge coordinate data (nearest known
  location to any navpoint). MinersRefuge was a discontinued SC mining-data
  project (Lars, 2026-07-19), so the source no longer exists; same-day
  research also found NO alternative source publishing structured local
  body-fixed XYZ for surface POIs (UEX get_poi has no coordinate fields,
  scunpacked-data top level has no POI placement file, community cave
  writeups are Orbital-Marker-relative prose). Revive only if a local-frame
  POI dataset ever appears.
