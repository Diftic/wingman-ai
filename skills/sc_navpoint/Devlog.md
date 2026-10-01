# SC NavPoint: Devlog

## 2026-09-20: Wingman AI 3.2.2 API update

Installed and packaged NavPoint v4.9.0.26 using the supported v3 threading/speech
interfaces and lazy frame-name loading. See
[WINGMAN_3_2_2_2026-09-20.md](WINGMAN_3_2_2_2026-09-20.md) for evidence and restart checks.

## 2026-09-19: Automatic startup and Accountant-style dashboard card

Packaged v4.9.0.25 with auto_activate enabled, a compact three-line announcement,
the computer link only, and Accountant's smaller QR image. Delayed startup delivery
uses the same Wingman helper as Accountant. See
[STARTUP_CARD_2026-09-19.md](STARTUP_CARD_2026-09-19.md) for verification and artifact.

## 2026-09-19: Fix activation with SC Log Reader loaded

Released v4.9.0.24 with a unique navpoint_location_names module name and an upgrade
cleanup for NavPoint's old conflicting filename. Reproduced the tester's error,
then verified both module load orders and fresh/update installations from the ZIP.
See [IMPORT_COLLISION_2026-09-19.md](IMPORT_COLLISION_2026-09-19.md) for scope and evidence.

## 2026-09-17: Package the live-test installer

Built the versioned ZIP with installer.bat using the same AppData/Robocopy
installation pattern as sc_log_reader and sc_accountant. Included an install.bat
alias, tester instructions, V8 assets and the bundled native dependency. Removed
V5/V6 model directories from both packaging manifests. The builder now fails on
missing inputs and preserves existing artifacts rather than deleting them.

Fresh-install/update checks ran against isolated AppData; actual user installation
and saved data were untouched. See [INSTALLER_PACKAGE_2026-09-17.md](INSTALLER_PACKAGE_2026-09-17.md)
for the artifact, verification and rebuild instructions.

## 2026-09-17: Remove the unused Vision adapter

Removed screenshot-to-model plumbing, extraction prompts, completion parsing and
prompt-example rejection filters. V8 remains the sole live reader; shared
coordinate checks remain intact. Migrated coordinate tests to structured payloads
and retired tests exclusive to the deleted adapter. The cleaned source is in the
release and installed skill, with backups and manifest verification complete.

Details: [VISION_CLEANUP_2026-09-17.md](VISION_CLEANUP_2026-09-17.md).
Current verification figures: [ledger/LEDGER.md](ledger/LEDGER.md#current-installed-build--2026-09-17).
Restart Wingman before testing. Corrected live Levski alignment remains pending.

## 2026-09-15: Live-test preparation, Levski calibration, V8-only cleanup

Current handover: [HANDOVER_2026-09-15.md](HANDOVER_2026-09-15.md).
Current verification figures: [ledger/LEDGER.md](ledger/LEDGER.md#current-installed-build--2026-09-17).

Installed the Wingman 2.1.1-compatible skill, added the observed Levski frame,
measured and implemented full site orientation calibration, and removed the
remaining uncalibrated direction fallbacks and compass output. V8 is the sole
runtime reader; its experimental selector and obsolete shipped glyph bank are
removed. Shared offline test helpers remain in the development checkout.

Automated verification and installation are complete. Live Levski alignment
after restart remains unverified. User paused until tomorrow. Logs, deployment
evidence and the waypoint database are archived in the handover's shutdown
snapshot. Wingman and Star Citizen were already closed; no shutdown action was
needed. Older entries below are historical and must not override this handover.


## 2026-08-11: `Supercalifragilistic.md` waves 0 to 2, and the main-menu gate

**Nothing committed, no release generated, the installed copy untouched. Suite
862 to 951.** Lars wrote `Supercalifragilistic.md`, which supersedes the
downloaded `star_citizen_r_displayinfo_coordinate_reader_plan.md`, and asked for
it to be executed. Work was delegated to named agents with QA by separate agents
that never saw the producers' reasoning.

### Wave 0, preservation and baseline: PASSED

Three trees hashed: dev 153 files, release 18, installed 19, with **release and
installed 17/17 identical**, differing only by the `install.bat` excluded by
design and two stale docs. Snapshot in the session scratchpad. Decision baseline
recorded over the whole corpus INCLUDING the day's live flights: 446 stack-only
frames, 0 legacy accepts lost, 0 Root disagreements, 0 continuity flags.

### Wave 1, contract cleanup: 4 items done, the 5th stopped on evidence

1. **`read_payload` is now `read_legacy_payload`.** It routes through the legacy
   parser only, so any future caller silently loses schema-1 stack support with
   no error and no failing test. `test_reader_entry_points.py` pins that no
   runtime module calls it and that the bare name never returns. Mutation-proven.
2. **The prompt was wrong in two ways.** It documented
   `list_navpoints(server_id, body)` when the tool takes `body` alone, and
   promised surface waypoints give "distance AND direction" when a schema-1 mark
   is a coarse Root-addressed record with no bearing and no arrival. The new
   `test_prompt_contract.py` derives its expectations from `inspect.signature`
   rather than pinning wording. Mutation-proven.
3. **`validate()` now walks all six declared custom properties**, not just
   `display`, with a test pinning code to YAML in BOTH directions. Safe because
   `ConfigManager.__merge_list` merges property lists BY ID, so a declared
   property always survives the merge; that same mechanism is why DELETING an id
   bricks the core.
4. **Printr: stopped, then decided.** The plan's "sync calls only with
   `server_only=True`" would silence eleven player-facing badges, several on a
   thread that cannot await. `Printr.print` already reaches the GUI from sync
   code via `ensure_async`, so the rule is stricter than the API needs. Lars
   decided: leave them visible. No bare `print` exists in runtime code.

**A project memory was corrected.** `reference_wingman_config_precedence` said a
repo prompt edit "changes nothing at runtime". `Laura.yaml` contains ZERO
occurrences of `prompt:`; the installed skill's `default_config.yaml` is the
base and the saved config merges on top. So the prompt fix DOES reach the player,
at install time.

### Wave 2: the observation model, the harness, and the first real baseline

`telemetry.py` is pure (imports only `__future__`, `dataclasses`, `typing` and
the already-pure `coordinate_stack`), carries all ten outcome states the plan
requires be unconfusable, and is in BOTH release manifests. Nothing in the
runtime imports it, which is Wave 2's exit gate.

**QA found two SURVIVING mutations**, a listed stop condition: deleting the
guard that a temporal rejection can never be authoritative, and making the
classifier report a stale fix as fresh, both left the suite green. It also found
a design flaw and a live hole: `is_authoritative` could not see age, so a dead
producer's last reading stayed authoritative forever while `freshness_state`
correctly called the same object stale; and feeding the retained stale
observation back in as a new attempt re-tagged it fresh with its ORIGINAL
timestamps. All closed, each mutation-proven with byte-identical restores.

**The benchmark baseline is in `ledger/LEDGER.md`** and is the most useful
measurement of the day. See it for the numbers; the headline is that the
alignment fit is 42.7% of a cold read, semantic parse is 0.1 ms, a fifth of all
reads pay a double decode via the self-heal path on exactly the scenes that
refuse, and the plan's 5 Hz gate is 2.3x out of reach before a grab is added.

**I got a claim wrong and an agent caught it.** I told Lars brightness formed a
clean monotonic curve across 23 sessions; I had picked four sessions that lined
up. `red-01` at background 52.0 accepts 74% while `starfield` at 53.0 accepts
0%, because `starfield` is STRUCTURED rather than bright. Corrected in the ledger.

### The main-menu gate, and the two ways the design analysis beat mine

Lars decided the main-menu phantom must be refused. The corpus settles the
discriminator with a **ten-order-of-magnitude** empty band: menu Root magnitude
1.740 m against a smallest-real 1.3889e10 m.

**My proposed placement would have been dead code.** `capture_payload` runs the
legacy parser first and the legacy payload wins at the menu, so a gate in
`stack_from_rows` refuses nothing. It belongs in `scanner.parse_payload`, the
single validation path, downstream of both parsers AND of the retained Vision
code.

**And "the Root magnitude" was too narrow.** The menu payload carries both a
stack and the legacy raw pair, so no real-pixel test can tell a one-source gate
from a two-source one; it must check every long-range vector, proven by
synthetic single-source payloads.

**One ordering decision, made after the gate broke a pre-existing test.** A test
proves the Root/Solar crosscheck bites by corrupting a payload to
`1.0km 2.0km 3.0km`, which is sub-floor, so the gate fired first and reported
`no_game_world` instead of `frame_mismatch`. Decided: **corruption is reported
as corruption.** A disagreeing pair means at least one number is wrong, so a
location claim derived from it is the weaker diagnosis. The gate now fires only
on vectors already proven internally consistent, the pre-existing test passes
UNCHANGED, and two new tests pin the ordering as a decision rather than an
accident.

**A prediction of mine was disproved by measurement.** I stated that inverting
the gate's comparison would leave the real-pixel test green. It fails too,
because inverting refuses the large real vectors and stops refusing the tiny
menu one. The agent's measurement stands over my prediction.


## 2026-08-10 (later): Wave 5 step 1, the corpus replay, and what it found

**Nothing committed, no release, installed copy untouched, no runtime file
changed.** One new dev tool, `ocr_dev/stack_replay.py`, which is not in either
release manifest and must not be (`ocr_dev/` is excluded by design).

### What was run, and why it was worth running

Every schema-1 fixture shipped in waves 0 to 4 was a transcription or a stored
decoded row: the exact evidence tier the ledger records the `OOC_` branch having
when it noted that branch had never run on real pixels. So the tool decodes each
retained PNG with the SHIPPING reader at `overlay_reader.POSITION_ROWS` and
feeds the decoded rows to both parsers, once per frame, so any difference
between them is the parsers' and not the decode's.

**19 sessions, 536 frames, 472 usable, 355 stacks, 341 with a candidate.** Zero
legacy accepts lost, zero Root disagreements over 109 frames carrying both, zero
unit-scale continuity flags over 309 pairs. Full numbers in `ledger/LEDGER.md`.

**The Pyro 3 surface change is real on real pixels.** `surface-01` is 90/90 by
the stack and 0/90 by the legacy parser, plus 92 more stack-only frames in
`fov-01` and `camdir-01`. 246 frames that could not be marked before, and none
lost.

### The finding that matters more than the pass

**In `dark-01` the local candidate is the ship.** No world container exists in
open space, so the outermost pre-Solar row is the Clipper, 12 of 12. The
decisive measurement needs no name, no scale and no Z, so nothing in
`REFUTED.md` touches it: **the candidate position held within 0.239 m while Root
travelled 1.913e9 m**. A frame the player sits still inside while it crosses 1.9
million km of the system is co-moving with their vehicle.

`REFUTED.md` now carries the ALWAYS form of the outermost-row rule as killed.
The rule itself is not dead: it holds in eight of the nine sessions that produce
a candidate, which is precisely why it is dangerous.

### The login phantom, and it is not ours

The main menu decodes a complete stack at (-0.00m, 0.04m, 1.74m), 5/5 in both
login sessions, accepted by BOTH parsers and reaching `KIND_OK` on the shipping
path. **The legacy parser accepts it too, so it predates schema 1.** This
resolves contradiction #4 on side A. No decision has been asked for or given on
whether to fix it.

### The skeptic pass changed the artifact

An agent that did not write the tool reproduced the run byte for byte, then
found four things the report was overstating, all now corrected in the tool
itself and recorded as boundaries in the ledger: it does not run
`scanner.parse_payload`; 175 frames were captured at 84 cells against the
shipping 88 and my header called them "the shipping window" anyway; "no
regression" covers the space branch only, since the legacy `OOC_` branch
accepted nothing at all; and the Root cross-check's two parsers share a
converter and a pre-filtered population.

It also produced a better argument than mine. I had leaned on the Z signature
for the movable-frame finding, which is awkward because Z pass-through is
refuted as a discriminator. The co-motion span was sitting unused in my own
JSON. **I verified it myself rather than adopting it on the agent's word**, and
the same measurement puts `surface-01` at 1.0e3 (a rotating body) and four other
sessions at exactly 1.000 (static world containers), so it is a description of
three regimes and NOT a proposed discriminator: a threshold on it would be the
scale rule already killed.

### Two defects in the tool, found before the full run

Its timestamp reader looked for index keys the logger does not write (the key is
`mono`), and it flagged discontinuities against a 1e9 m threshold I had invented
with no measured bound on legitimate quantum travel anywhere in this project.
Section 4 now flags only the unit-scale signature and reports the observed
extremes instead. A third was found by the skeptic: the first run silently
skipped seven sessions that use `shot_*.png` rather than `frame_*.png`.


## 2026-08-10: the coordinate-stack rework, waves 0 to 4 (implementation complete, evidence gate NOT passed)

Implemented from `COORDINATE_STACK_IMPLEMENTATION_PLAN.md`. Waves 0 to 4 are
done and green at **862 tests, up from the 678 baseline**. Waves 5 and 6 are not
started: both need a live flight and separate approval. **Nothing was committed,
no release was generated, and the installed AppData copy is untouched.**

### What changed, in one sentence

A newly marked waypoint is now addressed by the exact `Zone: Root Pos:` triple
plus the whole nested stack above it, and routed by a pure state machine that
never reads a zone name.

### The behaviour change that matters

**A Pyro 3 surface can be marked at all now.** The legacy parser refuses it
through `body_scale`, because Pyro names bodies without an `OOC_` prefix and the
space branch would otherwise emit a system-frame position for a player standing
on a rotating body. That refusal is correct and is **untouched**:
`payload_from_rows` still returns None for those rows, and no `local` or
`system` waypoint can be built from them. The coordinate stack reads the same
three rows, needs no name, and carries the capture on its own.

That split is deliberate and is why zero existing safety assertions moved.
`payload_from_rows` keeps its exact contract, roughly forty test call sites keep
reaching its guards, and the DISPATCH lives in a new function,
`overlay_fields.capture_payload`, which main.py now calls.

### New module

`coordinate_stack.py`, pure: no Wingman runtime, no OCR, no database, no
logging. Value objects, deterministic JSON, Euclidean distance and the routing
selector. **Every `raw_name` and `raw` value in it can be deleted or scrambled
without changing a routing decision**, and `test_coordinate_stack_router`
proves that by randomising them.

### The two ceilings

`LOCAL_TRACKING_MAX_M = 3_000_000.0`, a product invariant and not a YAML
property. Equality belongs to Root at BOTH ceilings; the comparisons are
strictly-less-than and a `<` turned `<=` is mutation-proven to fail a test.

### The evidence gate is CLOSED and the local path ships OFF

`LOCAL_TRACKING_ENABLED = False`. "The outermost row before SolarSystem is the
body or area frame" is an implementation hypothesis, not a measured identity.
It has never been checked against paired captures across two ships, a landed
ship against standing outside it, or a jump point, and if it selects a MOVABLE
container the skill would track a waypoint that flies away with whoever owns
that ship. Until the paired-capture matrix in the plan passes, every schema-1
waypoint routes on Root, which is correct everywhere and merely coarse up close.

Flipping that one constant is the whole rollout. The routing code, the boundary
tests and the arrival path for local tracking are all written and proven.

### Presentation

- ROOT APPROACH says "coarse" out loud in the guidance, because a rotating
  surface target's saved Root position is deliberately stale within a
  body-sized envelope.
- **Arrival can never be announced from a Root distance**, even at zero. Proven
  by driving the poll loop, with a positive control that proves the loop does
  call the arrival policy when a decision allows it.
- The ring draws NO bubble for a stack target in either mode and says
  `NO BEARING`. Enabling local tracking buys distance and arrival, not a
  bearing: the direction convention is still uncalibrated
  (`SPACE_DIRECTION_CALIBRATED = False`).
- The HUD page shows `ROOT APPROACH (coarse)` or `LOCAL`, computed server-side
  by the same pure selector, because two implementations of a routing rule
  cannot be kept in step.
- No new tool, no new custom property, no coordinates, labels, JSON or
  thresholds in any model-visible payload. Token-neutral.

### Schema v4, additive

Five columns added: `coordinate_schema`, `root_x/y/z`, `coordinate_stack`. A v2
or v3 database upgrades in ONE step off a single column list, so a user who
skipped the v3 build lands on the identical shape. Legacy rows get
`coordinate_schema = 0` and NULL Root, and **NULL Root is meaningful**: no Root
position was ever captured for them and synthesising one is mutation-proven to
fail a test. A corrupt `coordinate_stack` column leaves the row listable and
renamable and refuses only navigation.

### Two defects found and fixed in my own code

- `distance_m` overflowed on an extreme coordinate, which a corrupt stack column
  can reach, on the poll thread where a raise is a dead navigation loop. Now
  `math.dist`, which is built on `hypot`.
- The mutation harness gave different verdicts on consecutive runs, because
  bytecode caching keys on mtime and size and a mutation applied inside one
  filesystem timestamp left a stale `.pyc`. Fixed with `PYTHONDONTWRITEBYTECODE`
  plus a cache sweep before each run. **Four "escapes" in the first run were
  that bug, not real gaps**, which is worth recording: an unstable harness reads
  exactly like a weak test.

### 23 mutations, all caught, every file restored byte for byte

Two of the mutations I wrote first ESCAPED for a real reason rather than a bad
test: a damaged coordinate cell is refused by TWO independent layers (the row
regex and the unit conversion), so relaxing either alone changes nothing. Each
layer now has its own test, plus a both-layers mutation for the end-to-end
outcome.

Two further mutations were REMOVED as unprovable, and that is a finding rather
than a gap. The `stack_decision is None` guards on the legacy frame-id and
cross-body gates cannot be shown to matter, because a stack row carries an empty
`frame_id` and an empty `body`, so those gates cannot fire on one anyway. The
guards stay for explicitness; they are defence in depth, not the load-bearing
protection. The same is true of the stack branch in `ring_deflection`: a stack
target has neither a body nor a system frame, so no bubble was reachable for it
even before the branch existed.

### Five pre-existing test assertions changed, all one class

Every one pinned the schema version number 3 where the plan mandates an additive
v4. Old behaviour: `_SCHEMA_VERSION = 3` and `user_version == 3`. New behaviour:
4, with the v3 columns still present and every v3 row intact. The assertions'
intent is preserved and extended; `test_fresh_init_creates_schema_v4` now also
asserts the five new columns exist.

- `test_database.py::test_fresh_init_creates_schema_v3` → `_v4`
- `test_database.py::test_pre_v2_db_is_wiped` (version literal)
- `test_database.py::test_v2_to_v3_keeps_every_waypoint` → `test_v2_to_v4_...`
- `test_database.py::test_migration_is_idempotent` (version literal)
- `test_version_49022.py::test_space_waypoint_support_is_present`

One further test's FIXTURE changed rather than its assertion:
`test_capture_trace.py::test_the_gate_name_reaches_the_trace_file` used a
complete Pyro 3 stack, which no longer refuses a capture at all. It now uses the
same stack with an unreadable Root line, so a refusal still reaches the trace
and `body_scale` is still at the front of the reason where the grep expects it.
The new behaviour is pinned beside it by
`test_a_complete_pyro_3_stack_now_captures`.

### What is NOT done

- **Wave 5.** No corpus replay, no paired live captures, no live flight. The
  local-candidate hypothesis is untested against real pixels.
- **Wave 6.** No version bump, no `release_version` regeneration, no install, no
  commit, no PR. `release_version/` is deliberately the 2026-08-02 build and now
  differs from the dev tree; that is expected, not drift.
- `coordinate_stack.py` was added to BOTH release manifests, and a new parity
  test pins the two together. That lesson has cost this project three omissions.

## 2026-08-02 (late live review): open-space direction is implemented but still gated off

**Findings only; nothing changed outside this Devlog entry.** The player expects
direction for deep-space waypoints, and the live result withholding it is a
confirmed defect rather than missing overlay data.

The live Core log records the successful second `navigate_to("Space 1")` call
starting auto-tracking and returning distance while Laura says direction is
unavailable because of calibration limits. At the same time,
`generated_files/SC_NavPoint/navpoint_poll.log` records repeated successful
system-frame captures with coordinates, matching frame id and readable
`camdir`. The installed and dev copies of `navigation.py` have the same SHA-256
hash, ruling out a stale live install.

**Root cause:** `navigation.py` contains the later flown and tested
`system_camdir_orientation` implementation, but still sets
`SPACE_DIRECTION_CALIBRATED = False`. `space_guidance` therefore discards valid
CamDir and returns `"Direction not available in open space"`. Older tests pin
that obsolete suppression even though the version record describes the
system-frame convention as solved. Metadata is contradictory too: the
description promises open-space direction while the prompt requires distance
only, and `space_direction_test` is still presented as an unsafe calibration
switch. Laura accurately relayed the stale policy; this was not an LLM
inference error.

The future fix must cover every downstream consumer, not only the Boolean:

- `navigate_to`, the HUD server and the in-game ring all use the closed gate.
- `update_position` has no system-target guidance branch and reports the generic
  no-local-frame note for a valid deep-space position and target.
- The poll loop sends captures to the HUD and ring, then skips bearing,
  approach and arrival logic whenever `body` is empty, including when both
  position and target are valid members of the same system frame.
- The prompt, calibration property, suppression tests and ring-message tests
  encode the obsolete state and must change with the runtime behaviour.

**Status:** documented only. Open-space coordinates and CamDir are available
live; production suppresses direction through policy left over from before the
system-frame convention was solved.

## 2026-08-02 (night): the four Project Manager findings. 654 tests to 676, dev tree only.

Five steps against `FINDINGS_PLAN.md`. Nothing propagated: no `release_version/`
change, no live install, no version bump. Still `4.9.0.22`.

**FINDING 1, `update_position` reported a fix that did not exist.** A station
interior returns a TRUTHY payload with no coordinate frame in it. The falsy
guard let it through and the tool answered with `x`, `y` and `z` all null,
dressed as a successful reading. `mark_location` and `navigate_to` both refused
that payload already; this one did not. Now guarded on
`_capture_frame(pos_data) is None`, the shared helper, rather than a fourth
open-coded copy of the predicate. Keying it on `not pos_data.get("body")` would
have thrown away legitimate deep-space fixes, and a test pins that.

**FINDINGS 2 AND 4, the ring showed a clean face through a refused capture.**
`overlay_fields.ring_state` is the READER's verdict, written before the scanner
validates anything, so on every path where VALIDATION refused it still said
RING_OK. New `overlay_fields.ring_for_outcome(kind, reader_state)` maps the
final kind, applied where the outcome becomes final. For the five kinds the
reader answers correctly its verdict passes through, because `kind` alone cannot
reproduce the rows-based ACQUIRING-versus-GLARE split and those two ask the
player for opposite things.

The result publishes to a NEW field, `_last_ring_state`. `_reader_state` keeps
its exact three writes and values: it answers a different question and
`test_a_retry_that_succeeds_leaves_a_clean_ring` depends on it.

**FINDING 3, a caller could be told about another caller's capture.** The
capture lock releases when `_capture_position_local` returns, which is BEFORE
`asyncio.to_thread` hands the result back to the awaiting coroutine. An
unattended poll tick landing in that window overwrote `_last_outcome`,
`last_reject_reason` and the badge latches. The worst instance: `absent` is the
one kind carrying the console-command hint, and hints are relayed word for word,
so a tool whose own capture read the overlay perfectly could read out an
instruction to switch on something already on screen.

Fixed with a module-scope `contextvars` sink, because both capture seams have
signatures and return types pinned by tests and `CaptureOutcome` may not grow a
field. The fallback to the shared field is REQUIRED, not sloppiness: the test
doubles fill no sink. `test_a_replaced_capture_seam_still_reports_through_the_shared_field`
exists to stop it being deleted as dead code.

Step 4 extends the same reasoning to the duration on the success line, via a
`capture_ms` key measured inside the lock.

### User decisions, settled. Do not rediscover these as bugs.

- **D-1, the stale bubble is SUPPRESSED on a refusal.** Decided against the
  planning recommendation, then REAFFIRMED after three costs were stated: that
  it reverses the deliberate coexistence design (over terrain the reader refuses
  most frames, so the bubble strobes off and on while a two-second-old fix is
  still inside the freshness window); that suppression keys on ANY ring message,
  so the bubble also vanishes in GLARE, which over sunlit terrain is the common
  case; and that intermittent refusals therefore toggle it at up to about
  0.5 Hz. All accepted. It is a judgement about how the user flies.
- **D-2, `no_reader` reuses `RING_NO_SIGNAL`.** Known imperfection stated first
  and accepted: NO SIGNAL is the string tied to the console command, and that
  cannot help when the skill's own reader failed to load, so `no_reader` and
  `absent` are indistinguishable ON THE RING. Diagnosis is not lost: the tool
  result still carries `capture_kind: "no_reader"` and the poll log still records
  `REFUSED: reader=unavailable`. Do not "fix" without asking.
- **D-3, `ACQUIRING...` for all five reject reasons.** Known over-promise
  accepted: `implausible_body` is not transient, and its badge says looking again
  produces the same refusal while the ring says wait. The two channels disagree
  for that one reason.
- **P-1, the no-frame ring string is `INDOORS`.** `NO FRAME` was rejected. It
  names the player's SITUATION rather than the instrument's state, so the action
  is self-evident without a second sentence.
- **A-1, one pre-existing test REWRITTEN IN PLACE**, the third authorised such
  change in the project. `test_a_fresh_bubble_survives_a_reader_refusal` became
  `test_a_refusal_blanks_even_a_fresh_bubble`. Changed because the behaviour it
  guarded is no longer wanted, NOT because it was inconvenient, and its docstring
  says so and keeps the original strobing argument visible beside the inverted
  assertion.

### Two behaviour consequences, named rather than worked around

- **No `SPACE TEST (UNCALIBRATED)` line is written during a refusal any more.**
  `_sync_ring`'s space-test logging is guarded by `deflection is not None`, and
  suppression makes that None. Consistent, but it thins the calibration log
  during a refusal-heavy flight.
- **The bubble POPS, it does not fade.** `MessageFader` ramps the message over
  0.45 s and holds it 1.0 s, and four photosensitivity tests forbid the message
  to blink. The bubble has no equivalent: it clears on the next frame and snaps
  back deliberately so it never streaks in from the centre. Suppression therefore
  makes the bubble do what the message is forbidden to do, with the damping
  machinery present and unwired. Not a photosensitivity hazard (`poll_interval`
  is bounded 1 to 10 s, so about 0.5 Hz worst case against a roughly 3 to 60 Hz
  band) but a readability cost. **Which regime actually occurs is UNMEASURED:**
  the 62 to 100 per cent figures on record are CELL refusal rates, and no
  capture-level refusal rate exists in the evidence. Sustained refusal is an
  unambiguous improvement; alternating refusal is the ugly case. The diagnostic
  flight settles it, and there is no test for this by construction. Ready
  mitigations, each a contained change to the same line: suppress only the
  TERMINAL kinds (`no_frame`, `no_reader`), which cannot strobe by their nature;
  or debounce N consecutive refusals for the transient kinds; or wire the
  existing fader to the bubble. The first two need a companion flag beside
  `_last_ring_state`, because D-2 collapses `no_reader` onto NO SIGNAL alongside
  `absent`, so the ring string can no longer tell terminal from transient.

## 2026-08-02 (evening): the failure made legible. Three waves, 118 tests, nothing propagated.

Built under the OCR-only decision below. **It does not fix the reader.** There
has still been no successful field capture since 2026-07-31 22:07:10. What this
work does is make the failure legible and measurable, so the next live session
produces evidence instead of another refusal with no sub-reason. That is the
single most important thing to carry forward from today.

**WAVE 1, the evidence floor.** Per-attempt capture tracing. Poll log ROTATION
at 8 MB keeping one generation, chosen over a truncating cap because a cap
destroys exactly the evidence the log exists to hold. A frozen `CaptureOutcome`
dataclass in `overlay_fields.py` with ten `KIND_*` constants covering every
failure producer. A capture lock.

**WAVE 2, the diagnostics and the honesty fixes.** Per-cell refusal diagnostics
recording which of the two conditions lost each cell. A success baseline folded
into the existing success line rather than added as a new one. The refused-frame
dump. Nine per-kind user-facing failure messages replacing the single one. The
`navigate_to` silent-accept fix. The two badges that named "Vision AI" reworded.
The capture moved off the event loop with `asyncio.to_thread`.

**WAVE 3.** Metadata corrections, the `Laura.yaml` prompt and keywords deletion,
two defects found by the wave 2 validator, and the refused-frame dump switched
ON.

**THE TWO REFUSAL CONDITIONS ARE NOT THE SAME BUG, and the log recorded
neither.** `overlay_reader.py:569` refuses a cell when
`cost > REFUSE_COST or margin < REFUSE_MARGIN`. High cost means nothing in the
glyph bank matched. Low margin means two glyphs matched almost equally. The fix
for one is not the fix for the other. It now records which. A test pins both
constants AND the disjunction, because converting the `or` to `and` would halve
the guard without changing either number.

**MEASURED, and recorded as a HYPOTHESIS rather than a cause: the alignment
self-heal refit costs +310 ms per read**, 763.6 ms against 453.9 ms. It fires
whenever nothing decodes as trusted (`overlay_reader.py:725`), which in the
observed field failures is every read. That is roughly 1.5 s of an 11 s
five-attempt mark spent refitting an origin that was not wrong. It is a live
candidate for the unexplained per-attempt cost and nothing more than that until
live data says so. Instrumentation item I4 logs `from_cache` and `refit` so the
next session confirms or refutes it.

**MEASURED: the per-attempt gate walk costs 0.0022 ms** against an attempt of
about 459 ms, roughly one part in 210,000. Kept on that basis rather than on
taste.

**MEASURED, and it was nearly recorded as a regression: the apparent doubling of
suite time after wave 2 was machine variance.** The pre-change snapshot
benchmarked at 36.2 s on the same machine at the same moment against 34.1 s for
the new code. The instrumentation did not cost it.

**TESTS: 536 at baseline, 654 now, 118 added.** Exactly TWO pre-existing
assertions were changed in the whole project, both authorised spec changes:
`test_main_capture.py:430`, where the hint no longer appears for the no-frame
case, and the `SAVE_REFUSED_FRAMES` default-state assertion. Every other test
failure encountered was fixed in the code, not in the test.

**THE REFUSED-FRAME DUMP IS ON.** It writes for six kinds (`unusable`,
`absent`, `decode_error`, `gate`, `reject`, `unexplained`) and not for
`no_grab`, `no_reader` or `no_frame`. One PNG per failed capture, final attempt
only. Capped at 20 GLOBALLY across kinds, newest kept, **so one class can crowd
out another**. Crop only, local only, never transmitted. That coverage was
established by a probe driving the real capture path, after two validators
contradicted each other about it.

**`grep -c "r_displayinfo 2" main.py` went from 4 to 2:** the module docstring
and a single hint block, reachable from `KIND_ABSENT` only, pinned by tests
across all nine kinds. The hint no longer answers questions it cannot answer.

**`Laura.yaml`: the `prompt` key and the `discovery_keywords` block were
deleted.** Backup at
`AppData\Roaming\ShipBit\WingmanAI\backups\Laura.yaml.2026-08-02.bak`,
deliberately outside the configs tree because `config_manager.py:446` loads
every `*.yaml` there. All six custom properties survive with the user's tuned
values. A validator proved the merged config still validates against the REAL
`SkillConfig` Pydantic model from the 2.1.1 tree, which closes the 2026-08-01
startup-failure mechanism rather than merely avoiding it. **The deleted prompt
was byte-identical to the live `default_config.yaml` prompt, so this changes
nothing today.** Its effect is to stop future prompt edits from being runtime
no-ops.

**THE VISION PATH IS STILL NOT STRIPPED AND MUST NOT BE.** Beyond the earlier
reason, it is not dead code: roughly 40 test call sites reach still-live guards
through `_parse_json_response`, including the unit-suffix requirement, the
plausibility gate and the space-frame rules. Stripping it would break a large
fraction of the 654 tests and there is no git recovery for it.

**WHAT IS NOT DONE.**

- **NO VERSION BUMP.** Still `4.9.0.22` everywhere, by the user's decision.
- **NOTHING IS PROPAGATED.** `release_version/` and the AppData install are
  byte-identical to where they started. None of this reaches a live session
  until the user runs `update_release.py` then `release_version/install.bat`.
  Until then the stale "via Vision AI" description is still in force and the
  instrumentation does not run.
- **NOTHING IS COMMITTED.** The user manages the release flow.
- **The reader is not fixed.** Stated twice on purpose.
- Step 7 of the implementation plan, the retry policy decision, is BLOCKED on
  live data from the new instrumentation.
- The `pyro3` body-token plausibility question and non-`OOC_` surface routing
  remain open and untouched.

## 2026-08-02 (later): no Vision at all. The reader is the product now.

**DECISION, LARS: OCR ONLY. NO VISION.** Stated three times in one exchange:
"no, we will not use vision at all, only OCR" and "no visionAI at all". This
reverses "DECISION, LARS: BUILD THE ROUTER" in the entry below, taken earlier
the same day, which had itself reversed "Vision AI is OUT of this skill,
permanently" (2026-07-31). Three decisions on one question in three days, all
three kept in the record in the order they were taken.

The local deterministic reader is the only reader. No fallback of any kind, no
model in the loop, no router.

**THE COST WAS ON THE TABLE BEFORE THE DECISION, and he took it anyway.** The
local reader has produced ZERO successful field captures since 2026-07-31
22:07:10. Seven failures over two days, in at least two distinct shapes: the
2026-08-01 pair reported no sub-reason and took 1.1 s and 1.2 s, the 2026-08-02
pair reported `no_system_line` and took 11.1 s and 11.0 s. From
`navpoint_poll.log` and the core logs.

**CORRECTION, later on 2026-08-02: "at least two distinct shapes" is REFUTED and
the refutation is accepted.** The 08-01 lines lack the gate name and the
`attempts=` field, both of which the current code writes unconditionally, so
that build simply had neither the gate instrumentation nor the retry loop. That
is ONE failure mode observed through two builds, not two failure modes, and the
duration gap is the same arithmetic at one attempt against five. Treating it as
two would have sent the reader work chasing a phantom. The count, the dates and
the durations are unaffected. What does remain unexplained is that 11.1 s over
five attempts is about 2.2 s each against 1.1 s for the single-attempt build.

What follows from that is the whole shape of the work. With a router, fixing the
reader would have been an optimisation running beside a product that already
worked. Without one, fixing the reader IS the product, and every refusal is a
user-visible failure rather than a token cost.

**THE 62 TO 100 PER CENT REFUSAL RATE OVER SUNLIT TERRAIN IS NOT DISPROVED.** It
was measured on real ground on 2026-07-31 and it still stands, against a primary
use case of a ship on a surface. It is now an ACCEPTED cost rather than an
argument for a fallback. Its own instruction, "do not plan a Vision retirement;
plan a router", is void.

**THE INSTALLED CODE ALREADY MATCHES, which was checked by reading it and not by
reading these documents.** `_capture_position` at `main.py:382-405` calls
`self._capture_position_local(attempts)` and nothing else, and a grep across the
skill folder finds no non-test caller of `capture_screen_b64`,
`build_extraction_messages`, `parse_completion` or `_EXTRACTION_PROMPT`; every
reference outside `scanner.py` is a test or a docstring. The Vision path is
present but unreachable. So this decision moves the records and the plan into
line with runtime behaviour that was already OCR-only, rather than requiring a
change to it.

**THE STRIP STEP REMAINS UNTAKEN, and that is deliberate.** `scanner.py` still
holds the Vision path, the echo canaries, the plausibility gate and the
two-capture wipe confirmation. Ordering the strip LAST as the irreversible step
is the only reason this question could be answered three different ways in three
days at zero rebuild cost. It stays unticked in `TODO.md` and no agent should
take it without an explicit instruction from Lars. Recording this decision
changed documentation only; no code changed for it.

## 2026-08-02: the ledger, and the decision that had been blocking everything

Lars stopped the work: "I feel like we have been stumbling around in circles for
the past 2 days." He was right about the method and wrong about the mechanism,
and separating those two is what this entry records.

**HE WAS WRONG ABOUT REGRESSION, and this was checked rather than argued.** The
2026-08-02 failure at the Reclaimer was fed through the current code and then
re-run with ONLY the decode errors repaired and every gate untouched:

    as captured -> gate: no_system_line: no readable SolarSystem line
    repaired    -> (none, payload produced)

The frame fails UPSTREAM of every gate touched in two days. `_SYSTEM_RE` was
never modified. That location would have failed identically last week. Of the
four changes shipped on 08-01, three cannot break anything by construction
(instrumentation, a reorder affecting 0 of 6609 rows, a retry that only adds
attempts) and the fourth strictly RECOVERED 410 rows and reclassified none.

**HE WAS RIGHT ABOUT THE METHOD, and the mechanism is structural.** Three
sessions were spent inside `payload_from_rows` tuning which gate fires, while
the thing deciding whether the skill works sat one layer below it.

**THE ROOT CAUSE OF THE CIRCLING: the record is indexed by DATE, not by
QUESTION.** A correction gets filed where it was DISCOVERED and never reaches
where the number is USED. Nine headline numbers were revised in six days, every
one found by honest re-measurement, and several originals are still sitting in
the documents being read as current:

| quantity | first recorded | revised to |
|---|---|---|
| local read cost | 5.18 ms | 26.4 s, then 1.7 s, then 4.5 s |
| OCR accuracy | 98.33% | unreproducible, then 359/359 and 305/321 |
| precondition rejects | 9 of 153 | 7 of 153 |
| confidence headroom | 23.56 | 2.94 |
| block widening | "strictly negative" | a gain |
| P5 L2 scale | 41,726 km | 44,707 km |
| body displacement | 0.8 m | 0.000 m |
| trace capability | "names the gate" | names the branch |
| ship-on-surface data | "never captured" | captured 2026-07-13 |

**THE WORST CASE JUSTIFIED THE WHOLE PROJECT.** `LocalOcrPlan.md` §2.1 still
says local reading costs "0 tokens, 5.18 ms" and presents it as the reason to
build the reader. §2.3 shows that number timed a grab-and-threshold of the
CamDir strip. Line 948, nine hundred lines later inside a Phase 3 section,
records the actual reader at 23.6 to 26.4 s for a full read, and later 4.5 s per
capture with the game running, **slower than the ~3 s Vision call it replaced**.
The token argument does not survive its own document. The CORRECTNESS argument
does, and it is strong: four confabulation incidents in 2026, one of which
deleted six waypoints.

**DECISION, LARS: BUILD THE ROUTER. SUPERSEDED LATER THE SAME DAY by "no Vision
at all, only OCR"; see the entry above. Never implemented. Kept here because the
sequence is the record.** Vision returns as a fallback for frames
the local reader refuses. This reverses "Vision AI is OUT of this skill,
permanently" (2026-07-31), which had been sitting 80 lines from a measurement
taken the same night that said the opposite:

- "over sunlit terrain the reader refuses 62 to 100 per cent of cells.
  CONSEQUENCE: Vision stays required for daylit surfaces. Do not plan a Vision
  retirement; plan a router."
- "DECISION 2026-07-31: Vision AI is OUT of this skill, permanently."

The question meant to decide between them, "is the surface use case mostly
daylit", was logged as "the most important open item in the project" and was
never answered. **Lars answered it 2026-08-02: sometimes in a ship in space,
MOSTLY IN A SHIP ON A SURFACE, rarely on foot, NEVER inside a base, building or
cave.** So the skill's primary use case was served by a reader measured unable
to serve it, with the fallback deleted by decision.

Reversing is free ONLY because stripping the Vision path was ordered LAST as the
irreversible step and was never taken. That ordering saved a rebuild.
**It paid off a second time within hours:** this decision was itself reversed
later on 2026-08-02, again at zero rebuild cost, for exactly the same reason.
The strip is STILL not taken.

**"NEVER INSIDE A BASE, BUILDING OR CAVE" COLLAPSES A BLOCKER.** The nested
containers that stalled the local-frame routing rule since 07-31, the elevator's
transit carriage, hangar and cargo bay, are not cases that need solving. The
deepest realistic stack is `ship -> body -> SolarSystem -> Root`.

**THE LEDGER, at `ledger/`.** Three files, each readable in one sitting, indexed
by question. `LEDGER.md` holds the canonical numbers and 23 unresolved
contradictions; `REFUTED.md` holds every approach that failed with the evidence
that killed it; `CORPUS.md` holds what each capture actually shows, with
UNSTATED written wherever a source is silent. `TODO.md` points at it with the
rule: **one canonical row per quantity, change it there and nowhere else.**

Built by five agents reading in parallel (Devlog, TODO plus LocalOcrPlan, the
ocr_dev reports plus journal plus memory), all read-only, all instructed to mark
a claim UNSUPPORTED rather than invent evidence. Every load-bearing claim was
re-verified against the source before it entered the ledger.

**THE FINDING THAT ONLY EXISTED ONCE TWO CONTRADICTIONS SAT TOGETHER: the
15,000 km ceiling rests on two disputed numbers.** Its justification is the
empty band between the largest observed body and the smallest observed
container. Largest body is recorded as BOTH 330 km and 410 km, with the 410
having no stated source and no new body capture between the two entries.
Smallest container is recorded as BOTH 19,125 km and 28,000 km. The ceiling is
probably still fine, since P5 L2 at 44,707 km clears every candidate by 3x, but
its stated justification cannot be checked and anyone raising or defending it
must re-measure both endpoints first.

**I COMMITTED THE LEDGER'S OWN FAILURE MODE WHILE WRITING IT.** The 08-01
evening entry said `ocr_dev/reader.py` was aligned and verified case by case,
and 25 lines later said it was "Also unfixed". Both in one entry, written in one
sitting: the second was true when written and false forty minutes later, after
Lars asked for the alignment. Found only because an agent read 1400 lines end to
end. Corrected in place, logged as contradiction #17.

That settles a question this project had been treating as open. The problem is
not discipline. The discipline produced all nine corrections above. It still
could not connect a claim to its own later correction, because nothing in a
date-ordered document ever will.

**STATE:** 536 tests, three trees hash-identical 17/17, version 4.9.0.22 not
bumped, nothing committed. No code changed after the router decision, which was
deliberate: starting to build would have repeated the pattern that caused this.
**That restraint is why the OCR-only decision later the same day cost nothing.**
Had the router been built the same afternoon it was decided, it would have been
built and discarded inside one day.

## 2026-08-01 (evening): the Lagrange fix was correct, the instrumentation was not

The afternoon's body-scale window shipped and the live check failed anyway:
"wingman is unable to extract coordinates" at P5 L2. The window was suspected
for an hour. It was never the problem.

**MEASURED AT THE LOCATION, which is what settled it.** A 15 frame lossless
capture taken sitting at P5 L2 (`ocr_dev/captures/p5l2/`) says the container
reads **44,707 km**, roughly 3x the 15,000 km ceiling, correctly classified as a
container and not a body on all 15 frames with zero flicker. The body-scale gate
never fired once. **12 of the 15 frames produced a clean system-frame payload**,
SolarSystem and Root agreeing digit for digit. There is no blanket failure at
P5 L2 and there never was.

Correction while there: the ceiling comment recorded P5 L2 at 41,726 km, which
is its x axis rather than its largest component. Now 44,707 km. Both readings
sit far above the ceiling, so nothing moved.

**WHAT ACTUALLY REFUSED THE MARK: the phantom glyph, in a second consumer.**
The 3 failing frames all refused at `refused_above`, and the blocking row was
the CamDir line every time:

    '? CamDir: 179   0  133 FOV: 55 Focal: 3.00 FStop: 64.0'

`overlay_reader.row_kind` ANCHORED its label patterns at position 0. A star
inside the block decodes as a phantom glyph in the right-aligned text's blank
left margin, `^CamDir:` then fails, `kind` comes back None, and a CamDir row
with no kind cannot be cleared by `ooc_hypothesis_refuted`: it is not in
`_NOT_ZONE_KINDS` and carries no `Zone:` substring to refute by shape. So an
unreadable row sat above the SolarSystem line, the absence of an OOC line was
not established, and the capture refused. This is the SAME defect fixed in
`_largest_component` that afternoon, found in a second place hours later.

CONTROL, and it is what proves the mechanism: a frame with an untrusted CamDir
row but NO leading phantom (`FStop:?64.0`) passes. Untrustedness alone never
blocked. Losing `kind` did.

**THE REAL LESSON IS MINE, AND IT COST THE FIRST HOUR.** The afternoon shipped
`_trace_capture` specifically so a refusal would never again cost a probe
session, and `TODO.md` claimed it "names the gate". It did not. It named the
BRANCH. All five refusal gates inside `payload_from_rows` collapsed into one
sentence, `overlay read but no payload from N row(s)`, and each gate's real
reason went to `logger.info`, which reaches no file (verified: zero matches for
`Space capture refused` across every wingman-core log). A correct fix looked
suspect because the instrument could not tell five causes apart. Third time in
this skill that a diagnostic channel turned out to lead nowhere.

**FOUR CHANGES, all dev tree only.**

1. **Gate ids out of `payload_from_rows`.** Five stable constants
   (`GATE_NO_SYSTEM_LINE`, `GATE_REFUSED_ABOVE`, `GATE_BODY_SCALE`,
   `GATE_NO_COORDINATE`, `GATE_NO_ROOT`) surfaced through an internal
   `_payload_and_reason` returning `(payload, reason)`. `payload_from_rows`
   stays a thin wrapper so no existing caller or test changed. The refusal trace
   now names the gate AND dumps every decoded row with index, kind, trusted flag
   and raw text including `?` characters.
2. **`row_kind` SEARCHES for its label** instead of anchoring, the same fix
   `_largest_component` got. Measured rather than argued: over all 552 corpus
   files and 6609 decoded rows it moved 410 rows from no kind to their own and
   0 rows from one kind to a different kind, reproduced twice under two
   alignment regimes. 9 of 19 sessions were losing rows this way, so P5 L2 is
   where it was caught, not where it lived.
3. **`LABELS` reordered to put `zone` first.** Searching gave list order a
   safety meaning it never had under anchoring, and nobody had re-derived it.
   `zone` is the ONLY kind that does not clear `ooc_hypothesis_refuted`, and it
   sat behind `camdir`, the label printed on the adjacent line. Putting the sole
   gate-blocking label anywhere but first is the fail-open direction. Free to
   fix: 0 of 6609 rows carry two labels, so no observed behaviour changed.
4. **`mark_location` retries up to 5 grabs** (`MARK_CAPTURE_ATTEMPTS`, 60 ms
   apart). Marking is one-shot, so a refused frame costs the player the mark,
   unlike the poll loop which comes round again. `_capture_position(attempts=1)`
   by default, so the three poll call sites are unchanged and the loop still
   does one grab per tick. No guard weakens: each attempt is a full independent
   decode through every existing gate.

**THE SKEPTIC PASS EARNED ITS COST, and it changed the work.** An agent that did
not write the code was given the corpus claim and told to refute it. It
confirmed the zero, then said the zero was the WRONG METRIC:
`ooc_hypothesis_refuted` short-circuits on `kind` before reading text, and
`_NOT_ZONE_KINDS` is every kind except `zone`, so None and zone are
behaviourally identical to that gate and the dangerous transition hides inside
the benign 410, not in the flip column. Measured properly: **248 untrusted rows
move from BLOCKING to CLEARING**, the whole output-visible delta is 7 frames,
and all 7 are `local_frame: False` in genuinely open space. It then constructed
the fail-open row that motivated change 3. Item 3 exists only because the
producer was not allowed to be its own validator.

**MY OWN PROCESS FAILURES TONIGHT, both caught before they reached the user.**
I ran a negative control on the ordering tests by flipping the order and running
that ONE test file, got 8 errors, and nearly recorded it as proof the tests
bite. They were `ModuleNotFoundError: No module named 'api'`: that file cannot
import standalone and errors identically with the CORRECT order. The valid
control is the full suite, which fails exactly 5 tests under the old order and
passes 536 under the new one. Fifth trigger on the validate-negative-probes
lesson. Separately, the skeptic's first pasted adversarial row
(`... -22.1?89km CamD`) cannot flip at all, since it has no `CamDir:` substring;
I repeated it before checking and it is now replaced in the `LABELS` comment by
a row that genuinely flips.

**STATE:** 536 tests (was 483 at session start). Version NOT bumped, still
4.9.0.22.

**RELEASED AND INSTALLED the same session, on his instruction.** `ocr_dev/reader.py`
was aligned first, since it was the reason the tooling and the shipping reader
disagreed: it already called `re.search` but its patterns carried `^` anchors,
so it was anchored in effect, and it also still had `camdir` first. Both fixed,
and the two classifiers were then verified to agree case by case on the phantom
row, a two-label row, a SolarSystem row, a phantom Session row and an unlabelled
telemetry row. `harvest.py`, `learn.py` and `measure.py` import that module, so
the uppercase glyph harvest now measures what actually ships.

Install verified rather than assumed: `release_version` rebuilt 13/13, live
install hash-verified 17/17 against BOTH dev and release with 0 mismatches
(`install.bat` excluded by design), stale `__pycache__` cleared from the live
tree and `navpoint_ui`, `compileall` clean on every installed module, and the
INSTALLED `overlay_reader` behaviour-checked in isolation: zone-first, phantom
row returns `camdir`, two-label row returns `zone`. Installed `main.py` confirmed
to pass `attempts=MARK_CAPTURE_ATTEMPTS` at the mark path only, with all three
poll call sites still single-shot. Wingman was confirmed closed first by COMMAND
LINE, not by a guessed image name, and port 7869 was free. Rollback copy of the
previous live install kept in the session scratchpad as
`sc_navpoint-live-backup-2026-08-01-evening`.

**NONE OF IT HAS RUN IN GAME.** Wingman has not been restarted onto this code.

**WHAT IS STILL NOT ESTABLISHED, and it is the honest limit of tonight.** The
corpus is one player's 19 sessions, and none of the 7 frames whose output
changed had an `OOC_` line. The clearing path has therefore only ever been
exercised where clearing was CORRECT. The outstanding Stanton surface capture is
what would test it where it could do harm.

**CORRECTION, 2026-08-02, and it is an instance of this entry's own subject.**
This paragraph originally continued: "Also unfixed: `ocr_dev/reader.py` still
holds the anchored copy of `LABELS` ... the measurement tooling now disagrees
with the shipping reader." That was true when written and FALSE by the time the
entry was finished. The alignment was done later the same session and is
recorded 25 lines above, under RELEASED AND INSTALLED. The stale sentence was
never revisited, so one entry asserted both states.

Found by an agent reading this file end to end for the ledger. Nobody would have
caught it by reading normally, because the two statements are 25 lines apart and
both read as current. That is the whole reason `ledger/` exists: a correction
filed where it was discovered does not reach where the claim is used, **even
inside a single entry written in one sitting.**

## 2026-08-01 (afternoon): every capture at a Lagrange point was refused, and a star could switch the guard off

Reported as "skill does not detect the r_displayinfo section", with four failed
`mark_location` calls in the core log and nothing behind them. The overlay was
on screen the whole time.

**The capture path had no diagnostic at all, so the log could not answer it.**
`_capture_position_local` reported refusals through `logging.getLogger(...)`,
which does not reach `wingman-core.log` (the reason `_poll_trace` exists), and
the only file trace ran inside the poll loop, which never starts until a mark
succeeds. A failed mark was therefore unexplainable by construction, and the
first probe session existed only to recover information the skill already had
and threw away. Instrumentation shipped first, before any fix: seven refusal
branches, each naming the gate, with the grab region and the ink/periodicity
numbers on every line. The region is on the line because a capture aimed at the
wrong pixels and an overlay the player never enabled are otherwise identical.

That instrument answered the question on its first live firing:

```
capture REFUSED: overlay read but no payload from 8 row(s)
[present=True usable=True rows=8 region={'left': 4453, 'top': 0, 'width': 667,
'height': 175} ink=0.05295 periodicity=0.65656]
```

Same region and near-identical ink as an external probe that succeeded, so the
core was reading the right pixels and the refusal was downstream in
`payload_from_rows`. It also killed the DPI and process-difference theories
without another probe run.

**Root cause: `P5_L2` reports ~41,726 km from its own origin, and body scale was
an open-ended floor at 50 km.** So the Lagrange zone read as a planet surface
and `payload_from_rows` refused the space branch on every frame. The failures
began the moment Lars arrived at P5 L2 (the core log's own
`[Game Event] Arrived at: P5 L2`), and nothing about his actions changed.

**The worse defect, found while explaining an inconsistency.** An early probe
succeeded at the same spot, which should have been impossible. It succeeded
because a background star inside the 660 px block had decoded as a phantom
glyph in the right-aligned text's LEFT MARGIN, `?   Zone: P5_L2 Pos: ...`,
which no longer started with `Zone:`, so `_largest_component` returned `''` and
the body-scale guard silently did not fire. Verified both ways on one row text:
`body_scale=False` with the phantom, `True` without. A guard built after a
data-loss incident could be switched off by where the stars happened to be, and
it failed OPEN. That is the opposite of every other refusal in this module.

**Z pass-through was tried as the discriminator and is WRONG.** It looked
principled and `reference_sc_coordinate_frames` supports it, but that memory
lists `pyro3` at 184/184 matching: a rotating body passes Z through exactly as
a container does, because the transform is `system_z = body_z` for both. "World
-anchored" there means attached to the world, NOT non-rotating. The real Pyro 3
capture text in `test_body_scale_guard.py` caught it immediately. No test was
altered to accommodate it; the change was reverted instead.

**Shipped.** Body scale is now a WINDOW, `_BODY_SCALE_M` (50 km) to
`_CONTAINER_SCALE_M` (15,000 km). `_largest_component` SEARCHES for the `Zone:`
label instead of anchoring on it, and a zone row above the SolarSystem line
whose coordinates are unreadable now REFUSES instead of clearing, because
answering neither question is not the same as answering "safe".

| | observed | verdict |
|---|---|---|
| bodies (Pyro 3, Clio) | 123 km to 410 km | refuse, unchanged |
| containers (P5_02, P5 L2) | 19,125 km to 41,726 km | clear, REVERSED |

**The ceiling is a chosen threshold, not a measurement.** 15,000 km is the
highest value that still clears the smallest container observed, and high is
the safe direction since raising it only refuses more. The largest real body
scale is unmeasured. Any container between 15,000 and 19,125 km will refuse
until someone measures one.

**One test expectation was reversed deliberately, on Lars's explicit call.**
`P5_02` was asserted body-scale on the reasoning that a rest stop "is not open
space either". It now lives in a `CONTAINERS` fixture with the opposite
expectation and a comment recording the reversal. The Pyro 3 fixture, which is
what caught the Z error, was left untouched.

483 tests (was 464). Released and installed the same session, all three trees
hash-verified identical. Verified through the DEPLOYED copy: the real P5 L2
stack yields a payload, the real Pyro 3 stack still returns `None`.

**NOT verified live.** The final end-to-end check could not run: the overlay was
off by then (`overlay_is_present` False, ink `0.00000`), which is absence of
input, not a result. Wingman also needs a restart for any of this to take
effect.

**Incidental, unfixed:** the glyph bank refuses several uppercase letters.
`FOV:` reads `F??:`, `DRAK_Clipper` reads `????_?lipper`, `P5_L2` reads `P5_?2`.
Coordinates and the trusted SolarSystem/Root rows are unaffected, so it did not
cause this, but zone names keep coming back partly unreadable, which matters
directly for the local-frame routing rule that keys on the anchor token
VERBATIM.

## 2026-08-01 (midday): the HUD page could display navigation but never change it

Reported: on the browser HUD, "Clear target" does nothing and "delete navpoint"
does nothing. Both were reported as *nothing visibly changes on the page*, not
as a wrong result.

**The API was never at fault, and that took three probes to establish.** In
order, each one buying the evidence the last one could not:

| probe | what it exercised | result |
|---|---|---|
| `TestClient` | route handlers, no socket | every verb 200, row leaves the DB |
| `httpx` over a real socket | the network path, not the browser | every verb 200 |
| **real Edge over CDP** | the actual browser issuing the actual fetches | every verb 200, row leaves the DB |

The third probe matters because the first two were worthless for this question:
they bypass the browser entirely, and the report was about a browser. Driving
headless Edge against a live server showed `POST`, `PUT` and both `DELETE`s
returning 200 with the row genuinely gone. The installed copy in
`custom_skills\` was byte-identical to the dev tree, so drift was not it either.

**So on a LIVE server the old code worked, which forces the conclusion: the page
was not talking to a live server.** Nothing was listening on 7869 when this was
investigated. The HUD tab is opened once per Wingman run (`_hud_opened` guards
it in `navigate_to`) and is then kept open by hand across skill reloads and
restarts, so a tab outliving its server is the ordinary case, not an exotic one.

**And the page could not say so, by construction.** Three separate catches hid
it: `pollNavState` swallowed every failure with a bare `catch (_)`, so a dead
HUD froze on its last good read and looked healthy; `clearTarget` and
`deleteWaypoint` never checked `r.ok` at all and fell straight through to
"Target cleared" / "Deleted: X". A refused request and a successful one were
indistinguishable on screen. This is the `verify-the-diagnostic-channel` lesson
again: the page's silence was read as evidence and it was not evidence.

**A second, independent defect, found by reading and confirmed by test.** The
page was a mirror with buttons. `NavPointServer` held its own `_active_target`
and had no reference to the skill (true since the first committed version), so
its Clear, its Navigate and its delete moved only the server object. The skill
kept `_active_target`, its poll thread and the ring. Clearing on the page left
the skill navigating: poll loop capturing, ring guiding, arrival announcement
armed. Even with a live server, Clear only ever half-worked.

**What changed.**

- `navpoint_ui/app.py`: new `on_target_change` callback. Fired on set, on clear,
  and on deleting the *active* row (never on deleting another row). Wrapped so a
  raising callback cannot turn a completed state change into an HTTP error.
- `main.py`: `_on_hud_target_change` adopts the change. It runs on the server's
  thread, so it touches nothing needing an event loop: polling starts and stops
  through the existing `threading.Event`, the ring publishes under its own lock.
- `static/app.js`: `state.online`, `setOnline()`, `idleStatus()`. A failed poll
  flags the page offline instead of freezing quietly; `clearTarget` and
  `deleteWaypoint` check `r.ok` and report the status code; `setStatus` uses one
  timer instead of one per call, which previously clipped bursts of messages.
- `static/style.css`: `body.hud-offline` dims and desaturates the panels and
  turns the status bar red, so a page showing history cannot be mistaken for a
  page showing a feed.

**Verification.** 464 tests pass (was 453; 11 new across
`test_hud_target_control.py` and `test_app_js_offline.py`). Separately, real
Edge over CDP clicking the real DOM buttons: Clear empties the target card AND
the skill is told to stop; delete removes the card AND the row; killing the
server mid-session flips the page to `hud-offline` within two poll ticks and a
click then reports "Delete failed: no answer from the skill" instead of claiming
success. The pre-existing `F401` lint warnings in `main.py` are untouched and
predate this work.

**Not done, and it is a real gap:** the root cause of the reported session is
inferred, not observed. The deduction is sound (a live server answers, so a
non-answering server is the only way to get silence) but nobody watched it
happen. The offline banner is what settles it next time: banner means the skill
is gone, an `HTTP nnn` message means the skill answered and refused.

Build unchanged at 4.9.0.22.

**Released the same session, on request.** `update_release.py` rebuilt
`release_version/` from the dev tree (18/18 hash-verified) and `install.bat`
pushed it to `custom_skills\` (17/17 hash-verified; `install.bat` itself is
excluded by robocopy `/XF` by design). The release folder had drifted badly
before this: it was a 07-28 snapshot carrying a 59 KB `main.py` and missing
`overlay_fields.py`, `overlay_glyphs.npz` and `overlay_reader.py` outright, so
this sync was overdue independent of the HUD fix. The live install byte-compiles
and its `app.js` passes `node --check`. Robocopy does not purge, so a stale
`Devlog.md` and `TODO.md` from an earlier install remain in `custom_skills\`;
they are in neither manifest and Wingman does not read them.

## 2026-08-01 (early): a local-frame routing rule PROPOSED ON EVIDENCE, and deliberately not implemented

The decision left open at the close of 07-31 was taken to evidence rather than to
code. **Nothing in the skill changed. No file was edited, nothing was installed,
no test was added.** The two analysis reports are preserved beside this log as
`ocr_dev/zone-stacks-2026-08-01.md` and `ocr_dev/frame-drift-2026-08-01.md`, both
produced by driving the SHIPPED `overlay_reader` / `overlay_fields` unmodified
over every capture session on disk. They are dev-only and are in neither release
manifest by construction.

**THE PROPOSED RULE, one sentence:** the local anchor is the OUTERMOST container
row (the one nearest the SolarSystem row) whose Z component equals the
SolarSystem row's Z, compared in metres; if no such row exists the frame is the
system frame. Nothing keys on a name, a row index, or a magnitude.

**WHY Z.** SC's zone transform is a rotation about Z plus a translation in XY, so
a world-anchored container shares the system's Z axis exactly while a vehicle or
an interior, arbitrarily placed, does not. That transform was measured
independently on 2026-07-26, before this question existed. Over every frame where
a container row and the SolarSystem row both decoded all three axes:

| Z passes through | obs | Z never matches | obs |
|---|---|---|---|
| `pyro3` | 184 | `????_?lipper_742164815970` (ship) | 136 |
| `P5_?2` | 138 | `rs_cargo_001` | 97 |
| `glaciemring_segment_wtn-014` | 5 | `?an?ar_SmallFront_RestStop_Pyro_*` | 29 |
| `glaciemring_segment_wtn-018` | 2 | `?ransit?arria?e_ele?_util_*` | 26 |
| `?umppoint_pyro_ny` | 1 | `rsi_polaris_kaboos_ext` | 5 |
| | | `rs_int_ptn_set` (room) | 2 |

330 against 295, zero exceptions either way. The Stanton convention agrees on the
2026-07-13 transcription: `OOC_Stanton_4b_Clio` Z is `14.9327km` and the
SolarSystem Z is `14.9327km`, while the ship in the same stack reads `2.81m`.

**WHY IT MATTERS: only a rotating body's frame moves.** `pyro3`'s origin travels
through the system frame at a median **137.6 m/s** over 89 pairs (surface-01) and
148.9 m/s over 74 pairs (fov-01). In surface-01 the player stood still for 189 s
and moved **25.46 m** in the body frame against **26.039 km** in the system frame,
so a system-frame surface waypoint is wrong by roughly 8 km after a minute.
Everything else measured is static within noise: `P5_?2` 0.000 m/s over 111 pairs,
the rest-stop hangar 0.008, the cargo bay 0.000, and a parked ship 0.00 to 0.04 m
over 3 to 36 s across 8 pairs in four sessions. Ships reading 40 to 911 m/s are
under thrust, not slipping frames.

That asymmetry is what makes Z-routing safe in BOTH directions. Anchoring to a
Z-aligned container is right whether it is static (its frame is a rotated system
frame) or rotating (its frame is the only stable one). The two catastrophic
errors are anchoring to a vehicle and falling back to the system frame inside a
rotating body, and Z-identity excludes both.

**BOTH EARLIER CANDIDATES ARE REFUTED BY THE CORPUS.**
- The user's rule (row 2, or row 3 if row 2 is a ship) assumes the innermost
  container is the local frame or a ship. In preflight row 2 is a ROOM
  (`rs_int_ptn_set`, 0.73 km) and in red-01 it is a CARGO BAY (`rs_cargo_001`,
  86 m), so it keys waypoints to furniture. It is right on exactly the two cases
  it was designed for.
- The scale rule under-detects and over-refuses. `glaciemring_segment` is a
  world container at 1.46 to 2.10 km, far below any threshold that keeps ships
  out, so scale routes a station to the system frame. And `?umppoint_pyro_ny` is
  a 597 km container with a ship inside it in open space, so the shipped 50 km
  guard calls a jump point a body surface and refuses. The contested `P5_?2`
  turns out NOT to be a counterexample to scale: it does not drift, so anchoring
  to it is fine.

**A LIVE DEFECT FOUND WHILE DOING THIS**, unfixed: the 50 km guard in 4.9.0.22
falsely refuses captures at a jump point (dark-01 `frame_0001`). Cost, not
danger. Keep the guard anyway as the fail-closed backstop for the case where a
body row's Z is unreadable while its X still says 330 km, and for the day CIG
tilts a body's axis.

**THE REFUTATION GATE GETS BETTER, NOT WORSE.** Today `ooc_hypothesis_refuted`
proves a row is not an `OOC_` line from its leading characters, which are the
least readable part of the row. Under Z-routing the same fail-closed job is done
by the coordinate: a row whose Z decodes and does not match the system Z is
provably not an anchor. Coordinates decode far more often than leading capitals,
so the gate becomes simpler AND refuses fewer good captures.

**WHAT THE RULE TOUCHES, with one question opened and one closed.**
- The KEY becomes the anchor token stored VERBATIM, opaque, never parsed, matched
  as an exact string, and the capture refuses if the name did not decode trusted.
  Practical consequence: `P5_?2` never decodes cleanly in 154 frames, so the Pyro
  V rest stop refuses until that glyph is harvested.
- CLOSED: no `OOC_` stripping and no migration. The live database
  (`AppData/Roaming/ShipBit/WingmanAI/generated_files/SC_NavPoint/navpoints.db`)
  holds exactly ONE waypoint, `Mining Location 1`, frame `system`, body empty.
  There are zero local-frame waypoints to stay compatible with.
- OPEN, for the user: `scanner.py`'s `_KNOWN_SYSTEMS` plausibility gate requires
  `System_designator_Body` and so encodes one CIG team's convention as a universal
  law. `pyro3` passes only by the accident of its first four letters and
  `glaciemring_segment_wtn-018` fails outright. Recommendation is to remove it
  from the local path rather than widen it, since it exists to catch Vision
  confabulation and Vision is leaving this skill.
- `database` schema v2 needs no change; the `body` column keeps holding the key
  and only its documented meaning widens from "celestial body" to "anchor zone".

**THE USER'S CONSTRAINT, which decided the key design.** CIG's naming conventions
are per-team and will stay inconsistent until planet tech. This corpus shows
seven styles, including two different ones for ships (`DRAK_Clipper_698212607305`
against `rsi_polaris_kaboos_ext`). Geometry comes from the shared zone system;
names come from whoever owned that content. Written up as memory
`reference_sc_zone_naming`. The open risk it raises: a patch can rename a zone and
silently orphan every waypoint keyed to it. Cheap mitigation, NOT adopted and
flagged for decision, is to also store the SolarSystem coordinates on local
waypoints, which are decoded in the same frame anyway and are enough to identify
a renamed anchor even though they are only exact at the moment of capture.

**WHAT THE CAPTURES DO NOT SETTLE, stated plainly.**
1. Whether STATIONS drift. One usable pair, one station, 2 s apart, 0.001 m/s.
   That cannot separate a static station from a slowly orbiting one. The proposed
   rule is safe either way; the shipped scale rule depends on the answer.
2. The JUMP POINT: one frame, no pair, no drift rate at all.
3. The Stanton `OOC_` branch has STILL never run on real pixels. Z-identity there
   rests on a transcription.
4. The corpus is one body, one ship, one rest stop, one ring station, one jump
   point. Broad in frames, narrow in places.

**FOUR CAPTURES REQUESTED**, all with `--window=` (the equals form):
`station-still` (stand still inside a ring station, 5 min) settles station drift;
`jump-still` (parked at the Pyro-Nyx jump point, 5 min); `stanton-surface` (on
foot on a Stanton moon, dark ground, 3 min) gives the OOC branch real pixels, the
`O` phase 0 glyph and a second body; `city` (on foot in Lorville or New Babbage,
2 min) is the one case the rule is untested on, because if a city zone sits
between the room and the body and is itself Z-aligned then "outermost Z-aligned"
picks the city and not the body. If only two are possible, do `station-still` and
`city`.

**PROCESS NOTE ON MY OWN RELIABILITY.** I predicted the Z result and then
commissioned the agent that tested it, which is the wrong order for independence.
Two things reduce that worry without removing it: the transform was measured by a
different method on 2026-07-26, and the agent CORRECTED my hand derivation rather
than confirming it (the body-frame displacement between surface-01 `frame_0000`
and `frame_0038` is bit-identical at 0.000 m, not the 0.8 m I read off the
magnitudes). Neither analysis has been re-run by a second mind. A skeptic pass
over both reports, given the raw decodes and the claims but not my reasoning, is
the right next step before any code changes.

## 2026-07-31 (close): PYRO HAS NO `OOC_` PREFIX, which made the space branch unsafe on a surface

The user said it before the capture did: on Pyro 3 the second row reads
`Zone: pyro3 Pos:` with no `OOC_` anywhere. I checked the record first, found
`OOC_Stanton_4b_Clio` landed and `OOC_Stanton_2b_Daymar` on foot, and was
inclined to think he had compressed the string while reading a small overlay.
He was right and the record was simply Stanton-only.

**THE ACTUAL STACK ON PYRO 3, on foot, outside the ship, 90 frames:**

```
Zone: pyro3 Pos: 330.7421km 218.7408km 119.0037km
Zone: SolarSystem_745338555312 Pos: -16104284.9222km 7588008.0968km 119.0037km
Zone: Root Pos: -16104284.9222km 7588008.0968km 119.0037km
```

**WHY THIS WAS DANGEROUS.** Routing decides local-versus-system on the presence
of an `OOC_` line. With none present the reader concluded OPEN SPACE and emitted
a SYSTEM-frame position for a player standing on a rotating body: **62 of 62
frames**. That is the 2026-07-11 failure returning through a different door, and
it was live in the installed build. A surface point's system coordinates drift
with the body's rotation, measured on Daymar at 37.5 km over five minutes, so
the waypoint is right at capture and hundreds of metres wrong seconds later.
The refutation gate did not catch it and was right not to: `p` genuinely is not
`O`, so the row is provably not an OOC line. Both guards were individually
correct and the unsafe case walked through the gap between them.

**THE GUARD, deliberately scoped to refusing rather than routing.** A container
above the SolarSystem line whose own Pos is planetary in scale means the player
is standing on a world, whatever it is called. Scale survives naming where a
prefix does not:

| container | Pos from its own origin |
|---|---|
| ship `DRAK_Clipper` | 0.03 m to 12 m |
| room `rs_int_ptn_set` | 220 m to 600 m |
| station `glaciemring_segment` | 1.8 km |
| body `OOC_Stanton_4b_Clio` | 123 to 313 km |
| body `pyro3` | 219 to 330 km |

Nothing observed sits between 2 km and 100 km, so the threshold is 50 km, in the
middle of an empty band rather than near a boundary. Verified on the real
frames: **0 payloads emitted, 90 refused**, against 62 emitted before.

**A HOLE MY OWN TEST FOUND, and it was the one that mattered.** The first
version skipped untrusted rows. On Pyro 3 the body row decodes as
`Zone: p?ro3 Pos: 330.7421km ???.????km 119.0037km`: the NAME is unreadable, so
the refutation gate clears it, and the coordinate is perfectly readable and says
330 km. Skipping untrusted rows let the unsafe case straight through. The scale
check now runs on ANY row above SolarSystem and deliberately does NOT require a
whole clean line, unlike every accepting parser: this one decides to REFUSE, so
partial evidence is still evidence and permissiveness fails CLOSED.

**`y` PHASE 0 HARVESTED** from `surface-01/frame_0000`, green channel **0.0**,
the darkest source yet. Truth structural: the body is Pyro 3 and the row reads
`p?ro3`. ADD confirmed, occupancy gate passed, and the row now reads
`Zone: pyro3 Pos:` trusted. Bank 86 to 87 templates, backup at
`overlay_glyphs.bak-2026-07-31-before-y0.npz`.

**WHAT IS DELIBERATELY NOT DECIDED.** How local frames should be detected. The
user's proposal (row 1 CamDir, row 2 local coords, row 3 if row 2 is a ship)
covers the two cases the skill targets and is a good starting point, but
tonight's elevator capture had THREE container rows before SolarSystem, and my
own scale rule catches the rest-stop container `P5_02` at 28,000 km, which is
not a body either. Each rule breaks where the other holds. That decision sets
what a waypoint is keyed to and it is not a thing to settle at the end of a long
session. The guard above is safe under either answer.

**`O` PHASE 0 IS NO LONGER THE SURFACE BLOCKER.** It is only reachable from an
`OOC_` line, and Pyro has none. Stanton surfaces still do as of 2026-07-26, so
the glyph is still wanted eventually, but it is not what stands between this
skill and surface navigation. The routing rule is.

## 2026-07-31 (late): the reader is wired into main.py, installed live at 4.9.0.22, and clears 1 Hz on real pixels

**NOT YET TESTED IN GAME.** Everything below is headless measurement plus a
verified install. WingmanAI has not been restarted and no tool has been called
from inside the running skill. Do not read any of this as a requalification.

**THE MODEL IS OUT OF THE CAPTURE PATH.** `_capture_position` now delegates to a
new `_capture_position_local`, which grabs ONLY the overlay block, decodes it and
hands the payload to `NavPointScanner.parse_payload`, the same validation entry
point the Vision path used. It stays `async` because every caller awaits it and
that signature is the seam. The Vision code still exists in `scanner.py` and is
simply never called, so reverting is one line.

**A STRUCTURAL BUG THAT WOULD HAVE MADE THE WHOLE FEATURE INVISIBLE.** The poll
loop `continue`d on a failed capture BEFORE syncing the ring, and every other
path to `_sync_ring` runs only on success. The reader state would have been set
on every refusal and never displayed. Refusals would have been silent everywhere,
which is exactly what removing Vision made the ring responsible for saying out
loud. The failure branch now calls `_sync_ring()`.

**LIVE HEADLESS RESULT, the number the night was aimed at.** Eight consecutive
reads against the running game: 8 of 8 positions, zero refusals, ring state
clean, median **831 ms, or 1.20 Hz**, against the user's requirement of at least
one fix per second. Consecutive steps of 112 to 224 m with a stable frame id and
a steady Z, so the continuity check passes on live data.

**WHAT CLEARED THE BAR was reading fewer rows, not faster maths.** The first live
run managed only 0.7 Hz because `read` defaults to `MAX_ROWS` = 12, and rows 8
and beyond are the SECOND PITCH CLASS the reader never fits, so they refuse in
every capture and cost pure time. Measured with the game running: 12 rows
1795 ms, 10 rows 1303 ms, 8 rows 1033 ms, 6 rows 708 ms. New constant
`POSITION_ROWS = 8`. NOT lower than 8 on purpose: the line set shifts with
context, and the elevator capture earlier the same night ran the Zone stack down
to row 5, so 8 is margin rather than slack.

**PHOTOSENSITIVITY SAFETY, at the user's explicit instruction.** A message stays
on screen for a minimum of 1 second however briefly the reader asked for it. The
rule lives in a small `MessageFader` object in `ring_overlay`, NOT inline in the
render thread, so it can be tested rather than merely intended, and it sits in
the renderer so no caller can defeat it however fast it publishes state. On top
of the dwell there is a 0.45 s ramp, so transitions have no hard edge, and the
text only ever changes while faded out. Simulated against a reader flipping every
poll for 20 s: shortest visible period 1.03 s, 0.50 Hz of on-off cycles, against
a hazardous band that starts at 3 Hz. Two of the safety tests failed first and
both times the assertion was wrong rather than the code: appearing from nothing
at alpha 0.07 is the first step of a ramp, and a text swap at alpha 0 draws
nothing.

**A MAPPING BUG THE LIVE SMOKE TEST FOUND**, which is what headless runs are for.
A frame rejected by the capture precondition was reporting `NO SIGNAL`, because
the code passed empty rows and let the ink test decide, and a blown-out block has
plenty of near-white pixels with no row structure. That would have told the
player to type a console command they had already typed. `ring_state` now takes
`capture_usable` and returns `GLARE` whenever the precondition rejected the
frame, since that IS the definition of glare.

**BOTH RELEASE MANIFESTS UPDATED in the same change that wires main.py**:
`overlay_reader.py`, `overlay_fields.py` and `overlay_glyphs.npz` added to
`skill_installer_config.json` AND `update_release.py` RELEASE_FILES. This project
has a written lesson about omitting exactly that, from three separate incidents.

**INSTALL, verified rather than assumed.** WingmanAI confirmed closed with a
probe validated against a known positive first, after an unvalidated one cost an
hour earlier the same night. All 11 runtime files hash-identical to dev, every
installed `.py` compiles, stale `__pycache__` cleared, installed copy reports
4.9.0.22 (live was 4.9.0.8), 88 cells, POSITION_ROWS 8, 86 templates, the three
ring strings, and no `llm_call` anywhere in the capture path. Pre-install copy
backed up to the session scratchpad; `release_version` still holds a Vision
build, so rollback is a folder copy.

**28 TESTS FAILED after the switch and were RETARGETED, not weakened.** They
inject a fixture position through the Vision seam that no longer runs, and every
assertion is about what happens downstream of a position dict. The injection
moved to `_capture_position_local` and the assertions are untouched. One then
failed because the new stub froze the fixture where the original read it live on
each call, which several tests rely on to simulate the next capture landing
elsewhere; the test caught it and the stub was fixed. 439 tests green.

## 2026-07-31 (night): DECISION, Vision AI is removed from this skill permanently

User's call, taken immediately after the bright-terrain measurement below. **This
skill will never use Vision AI again.** When the local reader cannot read a
frame, the ring reports it to the player instead of falling back to a language
model.

NOTHING BELOW IS IMPLEMENTED YET. This entry records a decision and its design,
not shipped behaviour; the Vision path still exists in `scanner.py` and is still
what the live skill runs.

**Why this follows from the rest of the project.** Every confabulation incident
in this skill's history is a language model reading digits: the 07-20 example
echo, the 07-22 recombination, the 07-26 CamPos-gap invention, and the 07-26
server-token misread that deleted six waypoints. Removing Vision deletes the
canaries, the echo tripwire and the plausibility gate outright, because all three
exist only to police a model. It also removes about 3050 tokens per capture and
makes the whole skill deterministic.

**The cost, stated plainly because it is large.** With no fallback, availability
becomes usability. Over sunlit terrain the reader refuses 62 to 100 per cent of
cells (measured below), so on a daylit surface the ring will sit in a failure
state almost continuously, and surface navigation is the skill's entire purpose.
The decision stands with that understood; it makes the failure MESSAGE
load-bearing rather than cosmetic.

**THREE RING STATES, not one**, because the internal refusal reasons already
distinguish situations that need different reactions from the player, and a
single "compass malfunctioning" throws that away while also sending the player
hunting for a fault that does not exist. Text renders at the bottom centre of the
ring.

| state | shown when | what the player should do |
|---|---|---|
| `NO SIGNAL` | the overlay is not on screen at all | type `r_displayinfo 2` in the console |
| `GLARE` | the scene is too bright or too busy to read | look at darker ground, pitch the view down |
| `ACQUIRING…` | transient: position read but not yet confirmed | nothing, it recovers by itself |

**Mapping to the reasons the code already produces**, with the one gap named:
`capture_is_usable` rejecting on clipping maps to `GLARE`. The `no Root
cross-check` and `OOC not refuted` refusals map to `ACQUIRING…`, since both are
transient and self-correcting. `no position row` is AMBIGUOUS and is the gap: it
covers both "too bright to read" and "the overlay is not there", which are the
two states that most need telling apart, because one is fixed by looking
elsewhere and the other by typing a console command. A discriminator has to be
built, and the obvious candidate is ink presence: a glare frame contains
near-white glyph pixels that will not decode, while an absent overlay contains
none at all. That is a measurement, not yet a mechanism.

**Wording rationale, since it was deliberated.** `ACQUIRING…` implies the
instrument works and will recover, which is true, and stops the player debugging
a healthy skill. `GLARE` is the only candidate that gets the fix actually made,
because the most common refusal cause is one the player can correct in three
seconds. `NO SIGNAL` is unambiguous that the player must act. Rejected:
`COMPASS MALFUNCTIONING` and the whole instrument-fault register, because the
reader refusing is not a malfunction and the wording invites the player to go
looking for a broken thing.

## 2026-07-31 (night): the first live flight test, and the bright-terrain limit measured on real ground

236 frames captured across seven sessions. The headline is unflattering and it
is the answer the session existed to produce.

**IN SPACE THE READER IS NOW GOOD.** 20 frames of ordinary flight: 17 usable
(85 per cent), all 17 cross-checked, 0 emissions without an independent
cross-check, 0 continuity breaks, and Root agreed with SolarSystem digit for
digit on 17 of 17. Against 30 per cent on the stored corpus, which is pessimistic
by design since half of it is deliberately hostile captures.

**OVER SUNLIT TERRAIN IT IS UNUSABLE, and this is the finding.** A block grab
taken while the user flew over bright ground is PERFECTLY legible to a human and
to a vision model, and the reader refused 62 to 100 per cent of the cells in
every row (costs 7 to 17). GEOMETRY WAS RULED OUT FIRST, all three parts: the
character pitch measures 7.5 (column autocorrelation peaks equally at lags 7 and
8, which is the signature of a fractional pitch, not a broken one), the row pitch
is exactly 13, and a sweep of RIGHT_MARGIN from 0 to 21 puts the best cost at 7,
exactly where the reader already sits. The cause is the background: over that
terrain the DIMMEST channel sits at B median 62, against the reference red wall's
G median 2. There is no near-black channel anywhere in the frame for the
per-cell least-squares background solve to work against. So the bright-scene
limit is not an artefact of the deliberately extreme test captures; it is the
real behaviour over ordinary daylit ground, and **Vision remains required for
that regime.**

**THE CAPTURE TOOL'S FOCUS FILTER IS WRONG FOR THIS USER'S SETUP.** He runs SC
windowed borderless with the Claude terminal as an overlay on top and does not
alt-tab, so the game almost never holds foreground focus and `session_log.py`
skipped nearly every grab while he flew. The game is still fully visible and the
block is uncovered, verified by grabbing the region and looking at it, so an
unconditional grab is valid: pass `--window=`. Note the `=` form, because
`--window ""` as a separate token is dropped by PowerShell before argparse sees
it. An earlier session captured 150 frames with the same tool and the same flag,
which is exactly what made this look like a tool failure instead of a change in
window arrangement.

**PROCESS FAILURE, and the worst of the night because the lesson was already
written down.** I checked whether the background logger was alive with
`tasklist /FI "IMAGENAME eq python.exe"` and `Get-Process python`. Python from
the Microsoft Store runs as `python3.13.exe` here, so both matched nothing. I
declared the logger dead three times, invented two separate causes for a death
that never happened (a shell tearing down its children, then memory pressure),
stopped two healthy processes, and spent several minutes of the user's flying
time on it. `Get-CimInstance Win32_Process -Filter "ProcessId = N"` found all
three alive instantly. Check liveness by PID or command line, never by a guessed
image name, and for a capture tool prefer the direct evidence: watch the frame
count move. Logged to the existing negative-probe lesson as its fourth trigger.

**Corpus now on disk:** `preflight` 5, `dark-01` 20, `red-01` 150, `flight-01`
20, `bright-01` 11, `bright-02` 10, `terrain-01` 20. Only `red-01` and later
sessions carry the 675 px strip; earlier ones are 640 and decode slightly
clipped against the 667 px block.

## 2026-07-31 (evening): `k` phase 0 harvested, the block widened, the OOC gate turned into a refutation, and Root made mandatory

Five changes, all validated before they were written, plus the measurements that
justify each. 410 tests green (was 381). Nothing is wired into `main.py` yet, so
all of this is still contained.

**`k` PHASE 0 IS HARVESTED, from `red-01/frame_0024`.** The source was found by
hunting a red-lit area rather than a dark one, per the finding below. Gates, in
order: confirmed ADD not replace; occupancy gate re-run on the source row with 0
disagreements; template mean 0.182 against the existing `k` phase 1 at 0.191;
regression sweep over the corpus with 0 rows changed, 0 losing trust, 25 newly
trusted; and out-of-sample on six frames from three sessions, all now reading
`km`. The bank went 85 to 86 templates, written to `overlay_glyphs.npz` and
`ocr_dev/glyphs.npz` with `overlay_glyphs.bak-2026-07-31-before-k0.npz` holding
the previous state. TRUTH WAS STRUCTURAL, NOT INFERRED: `_TOKEN` admits only `m`
and `km`, so a single glyph before an `m` has exactly one possible identity.

**A LATENT TRUNCATION DEFECT, found by accident while reading harvest output.**
`BLOCK_WIDTH 600 / PITCH 7.5` is exactly 80, and `CELLS_PER_ROW` was 80, so an
81-character line lost its LEADING character in silence: a real deep-space
capture decoded as `one: SolarSystem_...`, which fails the `^Zone:` anchor and
refuses an otherwise perfect frame. It bites hardest where coordinates are
longest, which is deep space, which is where the space path is meant to work.
Widened to 88 cells / 660 px. Measured over 43 frames across 9 background
regimes: 84 to 92 cells all gain 4 trusted rows among the kinds the skill reads
and lose 1 telemetry row it does not; 96 gives the gain back and 104 loses 8,
because every extra cell lands on scenery to the left of the text and can refuse.
88 sits mid-plateau. FIRST MEASUREMENT OF THIS WAS WRONG and said widening was
strictly negative, because it counted ALL trusted rows including telemetry the
skill never reads. The metric was the error, not the data.

**THE POSITIONAL GATE IS NOW A REFUTATION, `ooc_hypothesis_refuted`.** The space
branch is a claim about absence, so an unreadable row above the SolarSystem line
blocked the capture. But the gate only ever needs to know whether that row COULD
be an OOC line, which is far weaker than reading it. A Pyro rest stop refused
purely because `H` and `g` have no template, even though the cells that DID
decode already prove `Hangar_SmallFront_RestStop_Pyro` is not `OOC_...`.
Refutation uses only confidently decoded characters, treats `?` as a wildcard,
and falls back to the system segment: an OOC token is `<System>_...` and the
scanner's plausibility gate already demands a known leading system, so a segment
that cannot spell one refutes the hypothesis under a rule the payload would be
judged by anyway. A row whose own label reads `CamDir:` or `ShardId:` is refuted
outright. Fails closed: anything it cannot disprove still blocks. The gate went
from a major blocker to 1 frame in 43.

**THE ROOT LINE IS NOW MANDATORY on the local reader's space path**, and this is
the failure-rate change rather than an availability one. `scanner.parse_payload`
runs its agreement check only `if root is not None`, which is right for a model
that can silently omit a field and WRONG for a deterministic reader, where an
absent Root line means an unreadable one. 3 of 16 usable frames were shipping
with no independent cross-check at all. Enforced in `overlay_fields`, not the
scanner, so the Vision path keeps its tolerance and the divergence is strictly
in the stricter direction.

**THE ALIGNMENT FIT IS CACHED**, which is what makes the rate target survive
load. `fit_alignment` searches 12 origins by 2 offsets by 3 colours and measured
1012 ms, 32 per cent of a cold read, returning the same origin frame after frame
because the overlay does not move. Cached on frame shape, refitted every 20
reads regardless, and SELF-HEALING: if a cached origin decodes nothing trusted,
it is dropped and refitted once, because a stale origin lands between rows and
is otherwise indistinguishable from a genuinely unreadable scene.

**RESULT, in the user's preferred polarity: failures, not successes.** Over 43
frames, 13 usable and ALL 13 cross-checked, so emissions without an independent
cross-check are 0, down from 3. Refusals are 30, all safe outcomes, split 8
clipped, 18 no position row, 3 no Root, 1 gate. Before tonight the same corpus
gave 4 usable. A refusal is a COST (one Vision fallback, about 3 s and 3000
tokens), not a failure; the failure line is unverified emissions, and detected
wrong values remain uncountable because the corpus has no truth strings.

**TIMING against the user's requirement of correct data at 1 Hz.** Grabbing the
block instead of the monitor is 4.3 ms against 104 ms, free and identical by
construction since all geometry is right-edge relative (`block_region`, pinned by
`test_block_grab_equivalence`). A CamDir-only read is 152 ms against 2181 ms for
ten rows, so 14x cheaper rather than the 10x a per-row model predicts. VERDICT:
facing clears 1 Hz comfortably even under load; a full position fix does not
survive a busy scene on its own, so the plan's split cadence (facing fast, zone
stack slow) is a requirement and not an optimisation. NOT BUILT: nothing drives
the reader from `main.py` yet. This work made the cadence affordable, not real.

**MEASUREMENT HYGIENE, because two numbers tonight were untrustworthy.** A live
benchmark returned warm SLOWER than cold, which is impossible, so the machine's
load had changed under it; identical work showed 1.8x spread. Absolute timings
from tonight should not be quoted, only ratios. Separately the existing corpus
strips are 640 px while the block is now 667, so `preflight`, `red-01` and
`dark-01` decode slightly clipped. `session_log.py` now IMPORTS the geometry from
`overlay_reader` instead of mirroring it, which is the actual cause: mirrored
constants let the capture tool and the reader disagree silently, and a corpus
that disagrees with the reader measures the wrong thing.

**`session_report.py` gained the outcome split and a failure-exposure section.**
"unreadable" was hiding four different causes, which made the column useless for
deciding what to fix. Outcomes are now mutually exclusive and asserted to account
for every frame.

## 2026-07-31: the gap is ONE glyph, phase synthesis is refuted, and harvesting needs red light rather than darkness

Preflight in a QV logistics station (a ring station, zone stack
`rs_int_ptn_set` -> `glaciemring_segment_wtn-018` -> `SolarSystem_732992724416`
-> `Root`, so no OOC line and the space path throughout). Five frames, zero
payloads. The reader itself was fine: CamDir, both inner zone lines, Session and
ShardId all decoded trusted at cost 3 to 5 with margins of 22 to 45.

**The whole refusal was one missing template.** Both the SolarSystem and the Root
line came back as `... -12512614.0058km 8268473.5244?m 471.45m`, one refused cell
each, and that cell is the `k` of the second `km`. The first `km` on the same
line decodes because it sits at the other phase. Mandatory unit suffixes then
refuse the capture rather than risk a 1000x error, which is the guard working
exactly as designed.

**THE SCOPE RESULT, from the user's reframe: do we actually need letters?** The
alphabet a COORDINATE reader needs is digits, dot, minus, `m` and `k`, at both
phases: 28 pairs. Twenty-seven are already in the bank, most with 100 to 300
observations across the corpus. Exactly one is absent, `k` phase 0, and it had
never been observed at all until this capture produced one. The other fourteen
gaps are letters no coordinate ever contains. So the coordinate path is one
glyph from complete, and the Stanton-versus-Pyro body analysis that preceded this
was chasing letters the numeric payload does not use.

**Where the reframe stops.** Letters stay load-bearing in two places. The body
token in `Zone: OOC_<body>` is the waypoint's key, what cross-body refusal
compares and what the plausibility gate checks, and it is open vocabulary. And
rows are identified BY LABEL, so `Zone:`, `Pos:`, `Root`, `SolarSystem_` and
`CamDir:` must decode; several of their characters have only ever been observed
at one phase, so a line length that flips a row's offset could demand the other.

**PHASE SYNTHESIS IS REFUTED, which closes the question the 2026-07-29 audit left
open.** If phase 0 and phase 1 were the same glyph resampled half a pixel apart,
every missing phase would be derivable and no capture would ever be needed. Four
methods were tried (linear and sinc, both directions) against 35 positive
controls, every character holding both phases, scored on the inner columns the
matcher actually uses. Best mean absolute error 0.1106, against 0.1196 for
applying NO shift at all: a true resample relation would have crushed that
baseline and it does not. The held-out test settles it: synthesise `k` phase 0
and run it at the real refused cell in this capture, whose truth is known from
the same line's other `km` and from Root agreeing with SolarSystem digit for
digit. All four methods leave the cell refused, with zero regressions elsewhere.
The two phases are separate rasterisations, not resamples, so **a missing phase
must be captured.**

**The offset model, and the user's proportional-width hypothesis.** He asked
whether the per-row offset might follow the letter/digit mix, letters and digits
having different widths. Measured over 117 trusted rows: length parity predicts
the offset for 109 of them, and all 8 exceptions are the SAME row, `ShardId:` at
n=31, which is the exception the 2026-07-30 note already recorded. Composition is
refuted as the driver, because within each parity class the digit fraction spans
0.28 to 0.65 under a single consistent offset; if width varied by character class
that spread would split the offsets. UNTESTED HYPOTHESIS with a clear mechanism:
`ShardId: pub_euw1b_12269732_090` is 31 characters as decoded, and a trailing
space would make the rendered line 32, which is even, which is exactly the 0.5 it
fits. That would mean the parity model is right and the measurement of `n` is
short by one on this row.

**HARVESTING NEEDS A NEAR-ZERO GREEN CHANNEL, NOT A DARK SCENE.** `harvest.py`
builds its coverage map from `frame[:,:,1]`, hardcoded, so what matters is that
one channel. The reference capture was never dark: the red wall measures R 89,
G 2, B 8, and it worked because that green view is a clean near-black backdrop
behind the same text. Measured on blank cells of the target row, `game-mid` gives
green mean 2.07, max 4.0, sd 1.11. The best frame from tonight's `dark-01` hunt
gives 11.34 mean, 17.0 max, sd 2.58 on its darkest channel, which is a dim GREY
area: every channel carries some light and none reaches zero. Flatness is already
adequate (sd 1.6 to 2.6); the level is not. The practical instruction is
therefore to seek RED lighting rather than darkness, and a bright red surface
beats a dark grey one.

**Consequence for the capture plan, and it is a real reduction.** The `k` needs no
planet. The SolarSystem and Root lines are present everywhere in the game and
this station already produced a phase-0 `k`; only the backdrop was wrong. The
planet trip is now needed solely for the first real-pixel test of the OOC branch
and for `O` phase 0, which is about NAMING bodies rather than reading
coordinates. Those are two separate errands, not one.

**Process failure worth not repeating.** I derived a phase rule, `phase =
(1 + i) mod 2` on the index from the left, validated it against ONE recorded
misread, and then built a twenty-body ranking table on top of it and gave the
user a recommendation from that table. The rule was wrong: the fitted offset
varies per row, and the rule makes a plainly false prediction elsewhere, that
`CamDir:` requires `D` phase 1, which is absent from the bank while that row
decodes clean and trusted in every capture. One confirming instance is not
validation, and the cheapest disconfirming check was available the whole time in
rows already on screen. The correct model was the one already recorded on
2026-07-30 and which I had talked myself out of.

## 2026-07-30: the session logger, and what 500 frames can and cannot measure

The user proposed capturing a long live session, around 500 images, to test
against. Worth separating carefully, because it is valuable for a different
question than the one that is blocking.

**It cannot close the alphabet gap, and no number of frames can.** A glyph's
sub-pixel phase is fixed by the parity of its own line's length, so a given body
name always renders its `O` at the same phase; and the reader is deterministic
on identical pixels, which I re-verified rather than trusted (a fresh reader on
the same frame gives identical text and identical costs to the last decimal).
500 frames in one place is one sample computed 500 times. One frame already
supplies 86 distinct (character, phase) pairs. Count was never the constraint;
two different locations is.

**What it does buy is the refusal rate in real play, which nobody has.** We know
the reader is perfect on a dark interior and blind on a blown sky. We do not
know what fraction of ordinary flying is which, and that fraction decides
whether the local reader REPLACES the Vision call or merely supplements it.

**The corpus has no truth strings, so accuracy stays unmeasurable, but three
checks need no labelling.** Root against SolarSystem (a tripwire, never a
verification, since both lines decoded the SAME wrong coordinate on the bright
capture). Root/SolarSystem aside, the valuable one is CONTINUITY: consecutive
positions must be continuous, so a dropped unit suffix is a factor of 1000, a
sign flip is a mirror and a digit substitution is a jump. That is the only check
available here that can catch a confident WRONG value, which is the failure
class that matters.

**Two tools, `session_log.py` and `session_report.py`, both dev-only.** Three
design points earned their place by measurement rather than by taste:

- Strips, not screens. All the reader's geometry is measured from the right
  edge, so a right-aligned 640x180 crop decodes byte-identically to the full
  frame (verified on three very different backgrounds), turning 11 MB per frame
  into about 170 KB. A 500-frame session is roughly 85 MB, not 5.5 GB.
- The deduplication cannot hash the whole strip, because the overlay's own FPS
  and frametime line changes every frame and a whole-strip hash would therefore
  never fire once. It hashes per row, and it LEARNS which row is telemetry from
  its change rate, because a count alone cannot tell "the frametime ticked" from
  "one coordinate digit changed": both are one row.
- The window filter fails OPEN. If the focused-window title cannot be read, it
  captures anyway and says so at startup, because a guard that silently captures
  nothing for ninety minutes is far worse than a few frames of desktop.

**Every detector was validated against known positives before use**, which is
the lesson from the probe that returned silence. The unit-scale detector fires
on a dropped `k` in either direction and stays silent on walking, on fast
flight, on an axis crossing zero and on a sign flip (that last one is the speed
check's job, and it is stated in the docstring rather than left implied). The
OOC finder fires on both `OOC_` and the confirmed misread `OuC_` and rejects the
ship zones `rsi_` and `DRAK_`, which the first version wrongly accepted. The
deduplicator was driven with a synthetic 60-frame session and kept every frame
of the six-frame movement burst while dropping the 34 static ones.

## 2026-07-30: Phase 2, the reader becomes a runtime module with its guards

The audit's four guards, the field parser and the join to the scanner are now
built and tested. `overlay_reader.py` (pixels to rows) and `overlay_fields.py`
(rows to fields) are runtime modules in the skill, with `overlay_glyphs.npz`
beside them. Nothing imports them from `main.py` yet, so they are deliberately
absent from both release manifests until it does. 381 tests.

**The join was written first, from real pixels, and it is the whole point.** The
reader's row dicts and `_capture_position`'s position data shared no code path,
and every test on either side supplied its own already-final fixture: the exact
shape of the July defect where scanner and guidance both tested green while the
join between them was never exercised. `test_join_real_capture_to_position_data`
drives a real 11 MB capture through the reader, the field parser and the scanner
into position data, and asserts the coordinates in metres.

**One validation path, not two.** `NavPointScanner._parse_json_response` was
split, and its second half is now the public `parse_payload(dict)`. The local
reader emits the SAME payload shape a Vision response carries, so it inherits
the echo canaries, the plausibility gate, the mandatory unit suffixes, the
SolarSystem/Root agreement check and the OOC/CamPos cross-check unchanged. A
guard added for either reader can no longer silently miss the other. What the
reader deliberately does NOT emit is `server_id`: it is deterministic on
identical pixels, so the live "three consecutive captures agreeing" rule
measures nothing but elapsed time when this reader feeds it, and a waypoint wipe
must not be driven from here.

**A hole in my own first rule, found by asking what an unreadable row could be.**
The space branch is a claim about ABSENCE (no OOC line, therefore system frame),
which needs more than a clean SolarSystem line. My first version blocked on
refused rows whose `kind` had decoded as `zone`, which misses the case that
matters: a row corrupted badly enough that even its `Zone:` label is unreadable.
The gate is now positional. The Zone stack nests inside out (ship, then the
body's `OOC_` zone, then SolarSystem, then Root), so an OOC line always sits
ABOVE the SolarSystem line, and ANY unreadable row above it refuses the capture.
Rows below Root are ignored by design, since rows 8 and beyond belong to a
second pitch class that refuses in every capture. Getting this wrong would store
a system-frame waypoint while standing on a rotating body: correct at capture
and metres wrong seconds later, which is the 2026-07-11 failure that closed the
stellar frame in the first place.

**Batching was not optional polish.** Phase 3 listed it as a speed item; it was
a blocker. The per-template Python loop took 17.3 s to read ten rows, which is
slower than the ~3 s Vision call it replaces, and it made a test suite
impossible. Stacking each phase's templates into arrays and scoring a cell in
one vectorised pass gives 1.7 s for identical output. Verified rather than
assumed, since the whole reader rests on this number: over 3400 template
comparisons on real cells the batched and scalar forms differ by at most
2.8e-14, and a test pins that. The recorded "16.13x and bit-identical" is close
on the ratio (this is about 10x end to end, since the alignment fit and the
image load do not batch) but bit-identical is too strong for this
implementation: the arithmetic is reordered, so the agreement is 1e-14, not 0.

**The precondition re-measured at 7 of 153, not the recorded 9.** Same
conclusion (it is not aggressive, and every reject is a genuinely blown-out
frame), and the number is now the shipped implementation's own. It varies with
how many rows are scanned: 6 at eight rows, 7 at twelve and twenty, 8 at
twenty-six. Recorded because a number in a note is a claim about a tool that may
have changed.

**NOT ESTABLISHED, and it is the same blocker as yesterday:** the local (OOC)
branch has never run on real pixels, because no lossless capture with an `OOC_`
line exists. Its tests are synthetic. Two captures on a body's surface against a
dark interior close both that gap and the three-pair alphabet gap at once.

**Speed, corrected the same evening, and the correction matters.** The 1.7 s
figure was measured on an idle machine. Re-measured with Star Citizen actually
running (26 GB resident, CPU at 84 per cent) the same frame takes 4.5 to 4.9 s,
and the strip is not the cause: full frame, strided view and contiguous copy all
land within 10 per cent of each other, so it is CPU contention. The reader only
ever runs with the game running, which makes 4.5 s the real number and makes it
SLOWER than the ~3 s Vision call it replaces. So caching the alignment fit
(about 37 per cent of the work) and cutting the six colour-and-offset
combinations per row are prerequisites for Phase 2 to be worth shipping, not
Phase 3 polish. My own hour-old number needed re-measuring under realistic
conditions, which is the same lesson as the audit's 16.13x and its 9 of 153.

## 2026-07-29: the local reader audited 25 ways, and what it actually protects

The reader reached 100 per cent on a clean in-game capture, so the next question
was not accuracy but trust: can it ever emit a wrong character while claiming
confidence. Twenty-five agents attacked that question in parallel from different
directions, each scoring against one contract so the results were comparable. The
metric was never accuracy. It was ACCEPTED-AND-WRONG: cost within the floor,
margin within the floor, character wrong. A refusal costs a Vision fallback. A
confident wrong digit is a waypoint in the wrong place.

**First, the measurement itself was broken.** The 98.33 per cent figure recorded
the previous evening could not be reproduced: the occupancy gate that certifies
truth strings reported 0 of 8 rows verified, because its blank test compared
pixel spread ACROSS the three channels, and a flat coloured wall produces that on
its own (the red interior wall is R 96, G 2). Measured WITHIN each channel and
maxed over the three, blank cells span 0 to 19 and inked cells 99 to 255 over 680
verified cells. With the gate repaired the clean capture reads 359 of 359, and
the bright capture 305 of 321.

**The reader does not lie on any unmodified input.** Zero wrong characters
emitted across 20 lossless frames and about 1470 ground-truth cells, plus
Gaussian noise to sigma 30, gamma 0.67 through 2.0, 144 synthetic background
combinations including stripes at the exact 8 px cell pitch, and 631 leave-one-out
trials with real templates deleted. Degradation always went to refusal, and the
fitted alignment stayed bit-identical throughout.

**Where it does lie, it is always the same population.** Three breaches exist,
all glyphs whose entire signal is a couple of pixels of ink:

| breach | trigger | cost / margin |
|---|---|---|
| `_` read as space | saturated background plus gamma 0.5, brightness +40 or +60, contrast 0.6 | 1.27 to 2.44 / 19 to 27 |
| `-` read as space (SIGN FLIP) | the sign's own cell dimmed to 30-42 per cent | 10.5 to 14.6 / 8.6 to 17.6 |
| nearest known-bad candidate of 28,234 | none needed, structural | 17.94 against a floor of 15 |

White text on a blown-out background carries information ONLY in its drop-shadow
notch, and the underscore's notch is the weakest in the alphabet. No confidence
floor can catch that: the blank template genuinely fits the pixels better,
because the pixels no longer hold the answer. Digits, which this project has
worried about since the first confabulation incident, turn out to be the LOOSEST
pairs in the alphabet under the classifier's own distance.

**Two guards close all three, and one of them is free.** A template-free ink test
(per-channel spread, threshold 50) refuses any cell that contains ink while
decoding as blank. It catches all three dimming breaches at spread 69 to 97,
agrees with the correct read at full brightness (spread 232), and produced no
false contradictions over 49 verified blank cells. It cannot catch the saturation
class, where the breached cells read spread 9.0 and 7.1, so that class needs a
capture-quality precondition BEFORE decoding. Note for whoever builds it: within
one row some underscores were erased while others survived at spread 190 to 255,
so a per-row statistic may be too coarse.

**Three things believed at the start of the day that are now false.** The
confidence floor's headroom is 2.94 cost units, not 23.56: the larger figure
counted only wrong top-1 picks, all high-cost outliers, and never saw the
near-misses among the 41 losing candidates per cell. `REFUSE_MARGIN` changes zero
decisions across 28,234 known-bad and 680 known-good samples, so `REFUSE_COST`
carries the entire guarantee. And `Zone: Root` agreeing with
`Zone: SolarSystem_<id>` is NOT a correctness check: the two lines share an
identical coordinate tail landing on the same x positions AND the same sub-pixel
phases, 13 px apart in one background regime, and on the bright capture both
independently decoded the SAME wrong coordinate. It remains a confabulation
tripwire. It was never a second source.

**The row layer is the real Phase 2 work, not the classifier.** Three demonstrated
gaps, none of which the confidence floor touches. Every frame carries two to four
rows all labelled `zone`, so taking the first match returns a different KIND of
line depending on game state, which is the row-index fragility the label rule
exists to prevent, moved up one level. Fabricated tokens (a made-up SolarSystem
id, a made-up shard token, a zone called `Root_Cellar_042`) are all accepted as
trusted at cost under 2.5, because the reader does no shape validation at all.
And a row rendered as `Zone: Root Pos:` with its coordinate region left as bare
background comes back trusted and correctly labelled at cost 0.00, because blank
cells decode as spaces for free. A minimum character count does not fix that last
one: the label alone is 15 characters. The gate has to be a per-kind FULL-shape
match on the whole line.

**The wipe rule does not survive a deterministic reader.** The live rule requires
three consecutive captures agreeing on a new shard token before deleting
waypoints, which assumes independence between the reads. The reader is
deterministic on identical pixels and the dangerous failure is driven by local
background level under one cell, so three frames a moment apart under the same
lighting decode the same wrong way. Repetition is worthless against a
lighting-deterministic error, which is exactly the class that deleted six
waypoints in July. The shard token's underscores are structural delimiters, so an
anchored shape regex does catch the confirmed erasure; the hex GUID and the digit
runs have no such protection.

**Phase 3 was planned on a number that measured the wrong thing.** The 5 ms
figure came from timing a grab-and-threshold of the CamDir strip. The actual
least-squares reader costs 26.4 s of CPU for a full 20-row read, about 0.031 Hz,
from 530,400 `match` calls at roughly 53 us each. Batching the per-template loop
into one numpy operation measured 16.13x and is BIT-IDENTICAL (maximum score
difference 0.0), caching the alignment removes a 6.4 s fit that came back
identical on all 20 frames, and grabbing the strip instead of the monitor saves
39 ms. Together the first two project to about 10.5 Hz, which clears the rate
target with no margin and misses the CPU target by eight to nine times.

**Two dev tools were silently broken.** `harvest.py` imported a `measure.py`
global that is only populated inside `main()`, so it died on every run since
measure grew a second capture, which is why the top-priority glyph gap was never
closed. `extend.py` rebuilt from the login base and would have discarded the
harvested bank on its next run. Both fixed. The alphabet gap itself turns out to
be three pairs rather than thirty, and a COVERAGE cost rather than a safety risk:
missing templates produce refusals, not wrong waypoints, measured 0 of 631.

**Held deliberately:** an attenuated shadow model beat the current hard three-way
OR on every axis, and four of eight alternative shadow shapes broke
`fit_alignment` outright rather than merely decoding worse, which the original
single-capture derivation could not have seen. Two captures is not enough to
re-fit a load-bearing parameter. It waits for a third, differently-lit capture,
the same one that closes the alphabet gap.

## 2026-07-28 evening: the ring is right, the READER is the bottleneck

The corrected convention was validated in flight and the ring was seen jittering
anyway. Both facts come from the same log, and together they redirect the whole
project.

**The convention is correct.** From a clean capture: the waypoint sat 1388 m away
at 158.4 degrees right of north, the ship faced 145.0 degrees right of north, so
the target belonged 13.4 degrees to the right. The ring computed +14.6 yaw with
+0.9 pitch, agreeing to **1.2 degrees**, and the hand check ignores pitch and
roll which accounts for about that much. Third independent validation after the
screenshot and the July marker, and the first one in flight.

**The reader is not.** Standing still, 73 captures, **24 corrupted (33%)**:

| corruption | rate | example |
|---|---|---|
| Z read 1000x too large | 22% | `9564.78` became `9564800.0` |
| frame_id digit wrong | 8% | `729494885314` became `729498485314` |
| CamDir yaw sign lost | 7% | `-142` became `+142` |
| Y sign lost | 5% | `-14361745365` became `+14361745365` |
| X digit dropped | 1% | `4333099756` became `433099756` |

Across 35 distinct (CamDir, position) inputs, **not one produced two different
outputs**: the maths is perfectly deterministic. The bubble jumps because its
inputs jump. The same aim gives yaw +14.6 four times running on clean data and
+81.8 on the capture where Z came back a thousand times too big. One misread
digit throws the bubble across the entire instrument.

**Decision: SPACE_DIRECTION_CALIBRATED stays False even though the maths is now
proven.** Opening it would give the VOICE a direction in open space, and the
voice would be wrong on one capture in three. A validated convention fed a
corrupted position is still a confident wrong direction. The gate opens when the
reader is deterministic, not when the geometry is.

**Local OCR started, Phase 1.** The grid is solved (pitch 7.496 px, phase 7.10,
right-aligned lines, verified to zero boundary ink) and a self-checking
labelling method is established. The classifier is not: 25% character error IN
SAMPLE against the JPEG corpus, which is a resolution-against-noise limit rather
than a tuning problem. Next action is one lossless `mss` capture, which section
2.3 of the plan predicted would be the easier case all along. Full detail and
every measured constant is in LocalOcrPlan.md so none of it needs rediscovering.

**My own process failure tonight:** four attempts at collapsing a glyph
clustering that was noise-limited from the start, when the first in-sample
failure should have sent me back to the plan's own note about JPEG. Logged
against the rule that three failed attempts at the same move means re-frame.

## Version: 4.9.0.22 (the system-frame CamDir convention, solved 2026-07-28)

CamDir is **(pitch, roll, yaw)** in the star system's frame, which is
left-handed with +X east, +Y north, +Z up and the origin at the star's centre.
Established by FLYING each vector and watching which coordinate moved, which is
a stronger instrument than reading the overlay and interpreting it:

| flown | reads | means |
|---|---|---|
| straight ahead, only Y rose | `0 0 0` | forward is +Y, north |
| nose up | `90 0 0` | index 0 is pitch, positive up |
| yaw right, facing east | `0 0 -90` | index 2 is yaw, positive is LEFT |
| roll right | `0 90 0` | index 1 is roll, positive right |

**The bug was a mirror, not an offset.** At CamDir zero the surface convention
returns forward `[1 0 0]` and right `[0 1 0]`; the truth is forward `[0 1 0]`
and right `[1 0 0]`. Forward and right are swapped, so no azimuth constant was
ever going to fix it, and my own first guess of "90 degrees" had the sign
inverted for exactly that reason. This is the gap the 2026-07-26 entry already
named: the surface solve validated the FORWARD vector only, because a compass
bearing is a forward direction, and right and up had never been tested against
anything. The yaw/pitch split was their first consumer.

`system_camdir_orientation` and `system_deflection` are new and used by
`space_guidance`; the surface functions are untouched, since they are validated
where they are used. Two functions rather than one with a mode flag: the frames
genuinely disagree, and a single function with a switch is one wrong argument
away from the confident wrong direction this gate exists to prevent.

**Two out-of-sample validations**, neither used in the derivation:

1. The same evening's screenshot. From the overlay's own coordinates the model
   reproduces the game's readout exactly: 15.0012 Gm against a displayed 15.00,
   azimuth -73.21 against a displayed -73.21, elevation 0.00 against 0.00, and
   the star 16.79 degrees to the LEFT of the crosshair, which is the side it
   appears on in the image.
2. The July marker. Swapping forward and right maps a computed yaw of t to
   90 - t, so the recorded failure of +108.7 resolves to -18.7 against its
   recorded truth of -18.8. Inside CamDir's own ~1 degree truncation floor.

**`SPACE_DIRECTION_CALIBRATED` is still False.** Two calculations agreeing is
not a third thing observed, and the flag's entire purpose is to refuse a
direction nobody has watched working. It flips after the ring is seen pointing
at a real waypoint in flight, not before.

**Tests: 357** (18 new). INSTALLED 2026-07-28, 14 runtime files hash-verified,
live reports 4.9.0.22, gate confirmed still closed in the installed copy.

## Version: 4.9.0.21 (space-direction calibration switch, 2026-07-28)

### FIELD MEASUREMENT 2026-07-28: the system-frame CamDir zero is +Y, not +X

User flew the vector rather than reading it, which is the stronger instrument:
holding CamDir at (0, 0, 0) and flying straight moved ONLY the Y coordinate,
in the positive direction. So in the system frame, CamDir (0, 0, 0) means
forward = (0, +1, 0).

`camdir_orientation` returns (1, 0, 0) for that triple, because the convention
was fitted in the body-fixed frame on a planet surface. The zero axis is
therefore wrong out here by 90 degrees before any other consideration.

This independently corroborates the July failure. That measurement reported yaw
+108.7 where the truth was -18.8; a forward direction rotated 90 degrees in
azimuth predicts -108.8, which agrees in magnitude to 0.1 degrees, well inside
CamDir's own integer-truncation floor of about 1 degree.

STILL OPEN, and the reason no constant has been written yet: sign. We computed
+108.7 where the 90 degree hypothesis predicts -108.8. Same magnitude, opposite
sign, which is equally consistent with a +Y axis plus a flipped yaw sign, or
with a -Y axis, or with azimuth measured the other way from the same axis. All
three are identical AT the anchor and diverge off it, so one off-axis
measurement decides it. Next flights: yaw 90 degrees from the zero attitude and
fly (which coordinate moves, and in which sign), then pitch up and fly.


The overlay works in flight (user confirmation, same evening: "circle shows up
exactly where intended"), and the missing bubble turned out to be the open-space
calibration debt, not a defect. Evidence: both waypoints in the live database
are `frame = system`, the poll log shows a clean capture at 18:42:04, and
`ring_deflection` refused it because `SPACE_DIRECTION_CALIBRATED` is False.

Two additions, so a calibration flight can happen at all.

**`space_direction_test` (config, default OFF).** Draws a system-frame bubble
from the uncalibrated convention. Contained deliberately: the spoken guidance
and the HUD page still withhold direction, only the ring draws, everything it
produces carries `uncalibrated: True`, and a one-time WARNING badge says not to
fly on it. Every other refusal (stale, wrong-session frame, missing CamDir,
cross-body) is untouched with the switch on, which is asserted rather than
assumed.

**Every successful capture now logs its raw numbers** to `navpoint_poll.log`
(frame, position, CamDir, body, zone, frame_id), file-only so the chat log is
not buried. Solving the convention needs (CamDir, known direction) pairs from
real flight; recording by default means an ordinary session produces them
instead of needing a special build after the fact.

The flight geometry the user proposed is what makes this work: mark a point,
back straight away from it along the line to a distant ship, and the mark, the
ship and the player are collinear. Crosshair on the ship therefore means the
mark is dead ahead, which is a known direction to compare the convention
against, not merely a pass or fail.

**Tests: 339** (9 new, all on containment of the switch). INSTALLED 2026-07-28,
14 runtime files hash-verified, live reports 4.9.0.21, switch ships OFF. Needs a
Wingman restart and the property turned on before it does anything.

## Version: 4.9.0.20 (the ring leaves the browser, 2026-07-28)

The ring now draws over the game itself, in a click-through layered window
anchored so its top meets the top centre of the screen. The browser HUD page
stays exactly as it was: it is the desk view (waypoint list, full readout), and
the overlay is the flight view.

**Why this and not the obvious alternatives.** The user pointed at
`SC_Signature_Scanner`'s overlay as the model. That one is a pywebview window
in a standalone app with its own venv, and the frozen Wingman 2.1.1 build has
neither `webview` nor `tkinter` (checked in `C:\Program Files\WingmanAI\_internal`;
PIL, numpy, mss and pygame are there). A standalone EXE like `wingman-player` or
`SC-HUD` would work but needs a build pipeline and a download URL, and the
Diftic account is still shadow-hidden, so it would ship undeliverable.

The path that survived came from inside Wingman itself:
`hud_server/overlay/overlay.py` is a 155 KB Win32 layered-window overlay driven
by ctypes and PIL, which proves the technique works inside this exact frozen
process and that PIL's pure-Python modules are bundled. `overlay_win32.py` is a
much smaller vendored copy of its `hud_server/platform/win32.py` primitives.
Vendored, not imported: that module is core code, it imports core services, and
it differs between the 3.1.2 dev tree and the 2.1.1 build that actually ships.

One deliberate divergence from the core's approach: it composites through a
magenta colour key, which can only express fully opaque or fully absent pixels.
The ring is antialiased and carries a soft glow, so a colour key would fringe
every curve. This uses `UpdateLayeredWindow` with premultiplied per-pixel alpha.

**Measured, not assumed** (probe run 2026-07-28 on the 5120x1440 primary):
- The window is on screen. An `mss` grab of the 220x220 box at the top centre
  (x=2450, y=0) found 530 bubble-green pixels, and row 0 carries ring pixels, so
  the ring does touch the top edge.
- The bubble lands where the maths says. Fed yaw +18.0 / pitch -6.0, the
  measured centroid was (134.3, 117.8) against a predicted (134.8, 118.3).
- It is click-through. `WindowFromPoint` over the ring centre and over its top
  edge both return the window behind it, never `ScNavPointRingOverlay`.
- 0.431 ms per rendered frame, so 30 fps costs about 1.3% of one core.
- The whole visibility state machine works on screen, measured as pixels
  differing from a captured bare-desktop baseline: dead ahead 3222, 35 degrees
  right 2829, no-fix face 1744, cleared 0, reacquired after clearing 2828,
  cleared again 0, stopped 0.

**A wasted hour worth recording.** The first state-machine probe counted
"bubble pixels" with a GREEN-only threshold, but the bubble changes colour with
offset by design, so at 35 degrees it is amber and the detector read zero. I
took that as "the ring never comes back after hiding", diagnosed a Win32
layered-surface bug that does not exist, and tried three fixes for it. Saved by
screenshotting to PNG and looking at the image, which showed the ring updating
perfectly. The measurement above is a difference against a captured baseline
instead, which cannot encode an expectation about how the ring should look.
Recorded in feedback_lesson_validate_negative_probe (third trigger).

**What is NOT proven, and the reason for saying so:** none of this was measured
against Star Citizen running. It must be borderless windowed; exclusive
fullscreen bypasses the desktop compositor and nothing can draw over it. DPI
scaling other than 100% is also untested. Both are live checks.

**Honest limit on the data, not the drawing.** The ring is smooth at 30 fps but
its INPUT still arrives at the 5s poll, so it glides between two-decade-old
fixes rather than tracking the camera. That is the LocalOcrPlan's problem, not
this one's, and it is the strongest argument yet for Phases 1 to 3 of that plan:
the surface is now built and waiting for a fast reader.

**Design.**
- `navigation.ring_deflection` is the single authority for whether a bubble may
  be drawn at all. It refuses on no target, no position, a stale or unstamped
  reading, missing coordinates, a cross-body target, no local frame, mixed
  frames, a system frame from another session, and the uncalibrated system-frame
  direction. Refusing shows the no-fix face: a bubble pointing somewhere
  invented is exactly the failure this skill has already paid for twice.
- `POSITION_FRESHNESS_S` moved into `navigation.py` and is re-exported by the
  HUD server, so the page, the server and the ring cannot drift apart on what
  counts as stale.
- `main._set_position` is now the only place that pushes a capture anywhere, so
  no path can refresh the HUD page while leaving the ring on an old fix. A test
  asserts there is exactly one `set_position` call site.
- The no-target face is a vector glyph rather than the browser's "?" character,
  which keeps the overlay free of any font dependency.
- Visibility follows the target: the ring appears when `navigate_to` sets one
  and disappears when navigation stops, is cleared, arrives, or the waypoint is
  deleted.
- Two new settings: `overlay_enabled` (default on) and `overlay_size` (default
  220 px, clamped 120-600). The monitor is the existing `display` property, on
  the reasoning that the ring belongs on the screen already being captured.

**INSTALLED 2026-07-28** to `custom_skills\sc_navpoint` with WingmanAiCore not
running. All 14 runtime files hash-verified byte-identical to dev, live reports
4.9.0.20 with SC_TARGET_VERSION 4.9.0, all live .py compile, and the INSTALLED
copy was proven to draw on screen (2875 pixels at the top centre with a target
set, 0 after clearing). Stale bytecode caches cleared before the copy. Needs a
Wingman restart. Rollback: the pre-install 4.9.0.19 live folder is backed up in
the session scratchpad, and `release_version/` now holds 4.9.0.20.

**Tests: 330** (46 new across `test_ring_deflection.py`, `test_ring_overlay.py`
and the version file). Two of them were wrong on the first run and the code was
right: a raw subtraction of two wrapped bearings read 270 for a 90 degree turn,
and the pulse was sampled half a period apart, where the sine returns the same
brightness. The green discriminator in the no-fix test is now a measured
threshold (accent peaks at G=164 / G-R=99, bubble reaches G=209 / G-R=208)
rather than a guessed one. Internal update, NOT a requalification. NOT yet
installed to the live environment.

## Version: 4.9.0.17 (navigate_to opens the HUD, 2026-07-26)

**Why the ring was never once seen, across every test tonight and every test
before:** the HUD is a browser page, opened only by the `show_navpoint_hud` tool
("show navigation HUD"). Nothing else ever called it. Navigation would start,
report a direction by voice, and never mention that its display was a page the
user had to know to ask for. Tonight's logs show only mark_location,
rename_navpoint and navigate_to, so the page was never open. Not a rendering bug:
there was nothing on screen to render into.

That also means the frame-aware HUD work in 4.9.0.11 is UNTESTED rather than
broken. I made the ring space-aware without first checking the page was on
screen, which was the wrong order.

`navigate_to` now opens the HUD once per activation (not per call, so repeated
navigation does not spawn tabs), survives a browser that refuses to open, and
returns `hud_url` plus a note saying the page cannot draw over a fullscreen game.
Explicit `show_navpoint_hud` still always opens. Four tests cover it.

**Standing limitation worth stating plainly:** a browser window cannot overlay a
fullscreen game. On a single monitor that means borderless windowed or a second
screen. This is the strongest argument yet for the in-game overlay the user
floated, and it is a stronger argument than I credited at the time.

**Tests: 272. INSTALLED 2026-07-26**, all 12 live runtime files hash-verified,
live reports 4.9.0.17.


## Version: 4.9.0.16 (DATA LOSS fixed: a misread server token deleted six waypoints, 2026-07-26)

The thread fix worked and immediately exposed two further defects. Trace:
```
23:24:38  poll THREAD started (interval 5s)
23:24:38  poll loop ENTERED
23:24:43  first poll tick (loop is alive)      <- the loop runs at last
23:24:46  position updated (1 ok / 0 failed)   <- captures work
23:25:35  poll stop requested
23:25:35  poll thread DIED: AttributeError: 'NoneType' object has no attribute 'body'
```
and in wingman-core.log at the same second:
```
23:25:35 [NavPoint] Server changed - 6 waypoint(s) from the previous session cleared.
```

**1. DATA LOSS: a garbled server token wiped six waypoints mid-session.** The
user had stopped nothing; the skill deleted his waypoints, cleared the active
target (which is what stopped navigation) and then crashed the loop. The Vision
model reads that long token inconsistently: the same server was read as
`pub-euw1b-5c-alpha-490-12286454-game-142` (an `s` as `5`) and as
`pub-euw1b-12269732_070` (structure lost). Two agreeing misreads satisfied the
two-capture confirmation added in v4.9.0.4 after the FIRST such incident on
2026-07-20, which proves repetition is not validation: a model misreads the same
way twice.

Fixed by validating SHAPE before believing the value. `_SERVER_ID_RE` requires
`pub-<region>-sc-alpha-<digits>-<digits>-game-<digits>`; both observed misreads
fail it and are now treated as UNREADABLE rather than as a different server, so
they can never wipe anything however often they repeat. A one-time badge tells
the user session tracking is degraded. Confirmations also rose from two to three.
Failing closed means the worst case is stale waypoints, never deleted ones.
Recorded as feedback_lesson_no_destructive_action_on_ocr.

Six regression tests cover it, parameterised over both real misreads plus empty,
truncated and junk tokens: five consecutive captures of a garbled token must
leave the database untouched.

**2. Mid-capture target race.** `target = self._active_target` was read after a
capture that takes ~3 seconds and then dereferenced without a re-check, so
anything clearing the target in that window (here, the wipe itself) crashed the
thread. The loop now re-reads the target after the capture and exits cleanly.
Predates the thread fix by a long way, but could never fire while the loop was
dead.

**Still open, and the user's own observation identified it:** the ring points the
wrong way in space ("up and to the left", we said "hard right"). The surface solve
only ever validated the FORWARD vector, because a compass bearing is a forward
direction; the camera's right and up axes have never been tested against
anything. Splitting a target into yaw and pitch is the first thing that uses
them, so a roll offset in the convention would leave `total_offset_deg` correct
while rotating the split. That predicts the magnitude is right and only the
direction is wrong, which matches what he saw. Needs a measurement against a
known direction, not a guess.

**Tests: 268. INSTALLED 2026-07-26**, all 12 live runtime files hash-verified,
live reports 4.9.0.16. Verified in the INSTALLED copy: the shape gate accepts a
real token and a short well-formed one, and rejects both observed misreads plus
an empty string; confirmations read 3.

## Version: 4.9.0.15 (ROOT CAUSE: the poll loop never ran, 2026-07-26)

**Auto-tracking, the arrival heads-up and the auto-stop have never worked since
they were written, in either coordinate frame.** Space waypoints only exposed it,
because on a surface you reissue a voice command and never notice the position
went stale.

**Evidence, from the file trace:**
```
23:14:06  poll task CREATED (interval 5s)
23:14:09  poll loop ENTERED
          <- "first poll tick" never appeared
```
The coroutine ran to its first `await asyncio.sleep(5)` and never resumed.

**Cause:** `asyncio.create_task` inside an `@tool` method schedules the task on
the event loop running that call, and Wingman does not keep that loop alive after
`navigate_to` returns. The task is silently abandoned: no exception, no log line.
Reduced to a two-line proof: `create_task` inside `asyncio.run(...)` yields 0
ticks once the loop closes, a dedicated thread yields all 5.

**Fix:** polling now runs on its own daemon thread with its own event loop, with
a `threading.Event` for cooperative stopping and sliced sleeps so a stop is
honoured in well under one interval instead of after it. `_poll_stopping()` uses
getattr so harnesses building the skill with `__new__` still work. This is the
SAME fix sc_log_reader needed for the SAME cause (dedicated Thread plus
new_event_loop per flush), so it is now the default pattern for background work
in a skill, not a workaround. Recorded in memory as
reference_wingman_skill_runtime.

**Six regression tests, and they can fail.** They start polling from inside
`asyncio.run`, let that loop close, and assert the loop keeps ticking. Verified
against the old mechanism: 0 ticks versus 5, matching the live trace exactly. A
version test also asserts the create_task CALL cannot return (the docstring still
names it, to explain why it is wrong).

**A process failure worth recording, mine.** The previous build (4.9.0.13)
instrumented this with `logger.warning`. A skill's Python logger output never
reaches wingman-core.log at all, so the run came back empty and I read that
emptiness as evidence the loop was dead. It was not evidence, it was a missing
measurement, and it cost a whole game session. The proof was already available:
`NavPoint database at ...` is a logger.info that runs every startup and appears
in no log file. 4.9.0.14 switched to a file plus printr, and I validated both
channels emit BEFORE shipping. Logged as
feedback_lesson_verify_diagnostic_channel.

**Tests: 261. INSTALLED 2026-07-26**, all 12 live runtime files hash-verified,
live reports 4.9.0.15 with no create_task call. Verified in the INSTALLED copy,
not just the dev tree: driven through the exact failure scenario it produced 4
ticks after the calling loop closed, where the bug produces 0.

## Version: 4.9.0.13 (diagnostic build: the poll loop is silent when it fails, 2026-07-26)

Second live test: the ring did not appear and position updates never happened.
Diagnosed by querying the live HUD endpoint directly rather than guessing.

**The server side is provably correct.** `GET /api/nav/state` returned the target
as frame `system`, the position with `system_frame` true and a MATCHING frame_id,
`camdir` present, and computed guidance: 6.699 km, "Turn right", offsets 53.2 /
1.1. The voice confirmed the same ("make a right turn and maintain level
elevation"). Extraction, storage, frame matching and guidance all work.

**One number explains both symptoms: `position_age_s` was 169.** The HUD refuses
to draw from a position older than POSITION_FRESHNESS_S (30s), so the ring was
blank BECAUSE the position was not refreshing. Not two bugs. The only capture was
the one navigate_to performed; roughly 36 polls in between produced nothing.

**Probably NOT space-specific.** The TODO checklist item "Auto-polling: deflection
ring glides on each update without voice command" has never been ticked, in
either frame, and neither have the arrival-alert items that depend on the same
loop. Space merely exposed it: on a surface you would reissue a voice command and
never notice.

**Precedent in this project.** sc_log_reader hit the same class of failure once
(notifications scheduled on the main event loop silently stopped processing) and
the fix was a dedicated Thread with `asyncio.new_event_loop()` per flush. This
loop uses `asyncio.create_task` from inside a tool call, so if Wingman runs tool
calls on a throwaway loop, the task dies with that loop, silently and forever.
That is the leading hypothesis, NOT yet confirmed.

**Why this build instruments instead of fixing.** Every failure path in
`_nav_polling_loop` logged at DEBUG, which is exactly why three minutes of
failures left no trace in the log. Capture exceptions and unusable positions now
log at WARNING with a running ok/failed count and the scanner's reject reason,
and the first success logs at INFO. One run then discriminates:
- NO "Nav poll" lines at all -> the loop is dead (event-loop hypothesis).
- Warnings naming a reason -> captures are being rejected, and by what.

Counters are loop-locals rather than instance state, since the test harnesses
build the skill with `__new__` and instance counters broke ten arrival tests.

**Also closed a real hole:** `frame_mismatch` was a SILENT rejection with no
badge, unlike every other reject reason. It now has one.

**Noted, unrelated but worth watching:** the stored waypoint's server_id
(`pub-euw1b-5c-alpha-490-12286454-game-142`) and the live position's
(`pub-euw1b-12269732_070`) differ substantially, so the model reads that long
token inconsistently between captures. The two-capture confirmation is what stops
that from wiping waypoints; the guard is doing its job on noisy input.

**Tests: 255. INSTALLED 2026-07-26**, all 12 live runtime files hash-verified,
live reports 4.9.0.13 with zero debug-only swallows left in the poll loop.

## Version: 4.9.0.12 (space CamDir, the ring's missing input, 2026-07-26)

Diagnosed straight from the live log, which named it exactly:

```
22:42:18 [Laura] Navigation set to "Space Location 1." Distance is approximately
3.9 kilometers; heading data is not available for this system frame.
```

**Cause: the scanner never extracted CamDir in the open-space branch.** The
prompt's open-space output spec did not ask for it, and the parse only ran on
the local-frame path, so `space_guidance` always received `camdir=None` and
returned distance only. The ring had nothing to draw. As the user put it,
without the ring the skill is worthless in space: distance alone cannot tell you
which way to fly.

Fixed: the open-space output spec now requires camdir with the same reasoning as
the local one, and `_camdir_from` is a single shared parse used by BOTH branches
rather than a second copy.

**This was a seam bug and worth naming as a class.** The scanner was tested. The
guidance was tested. Both were green. The join between them was not: the
`main.py` space fixtures supplied a `camdir` that the real scanner never
produced, so hand-written test data papered over the exact gap. Three new tests
now drive guidance from REAL scanner output instead of a hand-written dict, and
one asserts the open-space prompt branch requests camdir at all.

The same live log confirmed the 4.9.0.11 fixes work: *"Coordinates have been
logged for your current position in the Nyx system"*, spoken with no digits, and
mark/rename/navigate all completed without error.

**Tests: 255. INSTALLED 2026-07-26**, Wingman closed; all 12 live runtime files
hash-verified identical, live reports 4.9.0.12. Installed-copy check: camdir
survives extraction and guidance for a 3.9 km target now returns offsets
("Hard right", 92.4 off) instead of "Heading unavailable".

## Version: 4.9.0.11 (space waypoints: TTS and HUD fixes from the first live run, 2026-07-26)

First live use of 4.9.0.10 confirmed the core works (waypoint stored, retrieved,
distance correct) and surfaced two defects, both fixed here.

**1. The conversation model read raw coordinates aloud and the TTS switched to
Chinese mid-sentence.** Three separate sources fed it: the tool result carried a
formatted `X=... Y=... Z=...` string, `_navpoint_to_result_dict` carried raw x/y/z,
and the skill prompt explicitly said "tell the player the coordinates". Harmless
on a surface, where values are five or six digits; in the system frame each axis
is ELEVEN digits, so the model was speaking thirty-odd digits in a row.

Fixed at all three: the tool result now reports `coordinates: "logged"` and the
result dict omits x/y/z entirely (it gained `frame` instead), the prompt says to
confirm the coordinates are logged and NEVER read numbers aloud, and the
mark_location tool description says the same. The HUD is unaffected because it
receives coordinates through `database.navpoint_to_dict`, a separate serialiser
for a display that can actually use them. That separation is the reason this was
a safe fix rather than a trade-off.

**2. The HUD showed nothing for a space waypoint.** `sameBody()` in app.js
requires BOTH sides to carry a non-empty body, and space waypoints carry none, so
the ring always fell through to its no-target face. `navpoint_to_dict` did not
send `frame` either, so the browser could not have distinguished a space waypoint
from a broken row even in principle.

Fixed without building a separate overlay (kept as the user's last resort):
- `navpoint_to_dict` now carries `frame` and `frame_id`.
- The server computes system-frame guidance in `/api/nav/state` and the HUD
  renders it. Deliberately NOT ported into JavaScript: the CamDir trigonometry
  already exists in navigation.py, and two implementations of the same maths
  drift apart.
- app.js gained `isSystemFrame()`, a space branch that draws the ring from the
  server's yaw/pitch offsets, a "Deep space" tag in the waypoint list, and
  frame-appropriate messages replacing the old "NO LOCAL FRAME" catch-all.
- Open space has no north, so the bearing row shows the total offset ("92.4 off")
  rather than a compass heading. The HUD will visibly differ from the surface
  case, which is intended: inventing a bearing there would be a plausible lie.

**Tests: 251.** New ones lock both fixes: the HUD payload must carry the frame,
and the tool-result dict must NOT carry raw coordinates.

**INSTALLED 2026-07-26**, Wingman closed. Eight files copied; all 12 live runtime
files hash-verified identical; live reports 4.9.0.11. Installed-copy smoke test:
all .py compile, default_config.yaml parses, and a real deep-space capture stores
as frame `system` id 729494885309 and guides to a point 250 000 km away with a
92.4 degree offset and no invented compass bearing.

## Version: 4.9.0.10 (space waypoints, 2026-07-26)

Open-space waypoints alongside the existing surface ones, on the evidence from
this morning's paired probe: a point not attached to a rotating body keeps a
stable system-frame address (byte-identical over five minutes with the ship
parked, while a stationary Daymar surface point drifted through that same frame
at 122.7 m/s). The 2026-07-11 verdict that closed this scope tested a player
standing on a rotating body, so it never covered open space.

Note the version line: the fourth component is the WITHIN-PATCH counter, so this
is 4.9.0.10. I first bumped it to 4.9.1.0, which would have claimed
qualification against a Star Citizen 4.9.1 that does not exist; corrected before
release and now guarded by a test.

**Frames, not special cases.** A waypoint belongs to a frame: `local` (body-fixed,
the surface case, keyed by `body`) or `system` (the star system's frame, keyed by
the SolarSystem zone id). The OOC gate that already refuses stale-body misreads
becomes the router between them, so the gate is reused rather than weakened.

**scanner.py:** the open-space branch now reads the `Zone: SolarSystem_<id> Pos:`
line via the same unit-suffixed raw-token mechanism the surface path uses, so the
per-axis autoscaling hazard is handled by one piece of code for both. The `Zone:
Root` line duplicates SolarSystem digit for digit in every capture observed, so
the two are cross-checked and a disagreement rejects with
`last_reject_reason = "frame_mismatch"`. That validates the payload itself rather
than blacklisting known-bad values, which is a stronger guard than the canaries.
Absent Root is tolerated; the check is a bonus, not a requirement.

**database.py: schema v3, migrated ADDITIVELY.** v2 rows gain `frame` and
`frame_id` columns and stay exactly as they are, becoming explicit `local` rows.
The pre-v2 wipe path is untouched. Destroying valid surface waypoints to add a
column would have been unnecessary. `add_navpoint` requires a body for local rows
and a frame_id for system rows, because a system-frame coordinate without its
frame id cannot be told apart from a later session's.

**navigation.py:** `space_guidance` and `relative_deflection`. Open space has no
north, so no compass bearing is reported and `horizontal_bearing_deg` is
deliberately ABSENT rather than filled with a plausible-looking number. Instead
the full camera orientation is reconstructed from CamDir (`camdir_orientation`,
verified orthonormal and equal to the scipy rotation to 2.2e-16) and the target
is decomposed into yaw and pitch offsets relative to where the player actually
points. That needs no frame convention at all, which is exactly what aligning a
quantum vector wants. Flat Cartesian is correct here, unlike on a curved surface.

**main.py:** `_capture_frame` is the single place that decides which frame a
capture is in, and returns None when the capture proves nothing (never treated as
agreement). `navigate_to` refuses cross-frame targets with a message naming the
actual situation, refuses a system-frame target recorded under a DIFFERENT
SolarSystem zone id, and keeps the existing cross-body refusal for local rows.

**Tests: 243, up from 218.** New coverage includes the real deep-space capture as
a fixture, the Root tripwire, the missing-suffix refusal, deflection signs and
the zero-distance degradation, and all four cross-frame refusals.

**Bug caught by a test, worth recording:** `_build_guidance` reads
`elevation_instruction` unconditionally, and my first `space_guidance` omitted it
on the two fallback paths, so navigating to a waypoint you are standing on raised
a KeyError. Both keys are now always present. A degraded reading must degrade,
not crash.

**ASSUMPTION, not yet measured:** that CamDir in deep space is expressed in the
system frame. It is verified body-frame on a surface, and verified
container-stable between ship interior and surface, so this is the natural
extension rather than a guess, but it is untested. If it is wrong, distances
stay correct and only the direction offsets are affected. The in-game test is
simply whether the ring points back at a waypoint you have flown away from.

**INSTALLED to the live env 2026-07-26**, Wingman closed. Five files copied
(navigation, scanner, database, main, __init__); all 12 live runtime files
hash-verified identical to dev; live reports 4.9.0.10 with no false 4.9.1 claim.

The live DB was BACKED UP first (`navpoints.db.bak-before-schema-v3`) and the
migration was then run under observation rather than left to fire unseen at next
launch: user_version 2 -> 3, `frame` and `frame_id` added, row count unchanged.
The live table happened to be empty, so that run did not actually exercise data
preservation, which is the whole point of an additive migration. Four tests were
added to cover it against a hand-built v2 database holding rows: every waypoint
survives, rows become explicit `local` frame with coordinates and body untouched,
no wipe warning is logged, and re-running is idempotent. 247 tests.

Installed-copy smoke test, not just the dev tree: all .py compile, the real
deep-space capture parses through the installed extractor to
(-60077861178, 21737086462, 19428930448) m with frame_id 729494885309, and
guidance for a point 1e9 m away reports 1 000 000 km with a 92.4 degree offset
and no invented compass bearing.

Needs a full WingmanAiCore restart. Rollback: `release_version/` holds 4.9.0.7,
and the pre-migration DB backup sits beside the live database.

**Not released:** uncommitted per the skill release flow, and `release_version/`
deliberately NOT rebuilt.

## Version: 4.9.0.9 (CamDir to bearing implemented, 2026-07-26)

Implements the conversion verified earlier the same day, so heading is a
measured quantity instead of an assumed 0. Coded on the main loop (Opus 5) at the
user's direction; the model-split agreement stays suspended for this session
only.

**navigation.py, all additive:**
- `local_basis(position)` returns (up, north, east) in the body-fixed frame, and
  raises `LocalFrameUnavailable` at the body centre or a pole rather than
  returning a silently wrong basis.
- `camdir_view_vector(camdir)` applies the solved convention: Euler degrees about
  fixed axes in Y, X, Z order with the first component negated, evaluated as a
  closed-form expression rather than a matrix product, so the skill pulls in no
  numeric dependency at load time (numpy and scipy ARE both in requirements.txt
  and present in the frozen 2.1.1 build, so this is a weight choice, not a
  constraint).
- `camdir_to_bearing(camdir, position)` and `surface_bearing(from_pos, to_pos)`
  give a heading and a target bearing in the same true-compass convention, which
  is the only way their difference means anything.
- `calculate_bearing` gains `use_local_frame` (default False). When set, the
  horizontal bearing becomes a true compass bearing, falling back to the legacy
  flat-frame angle wherever no basis exists. Default-off keeps the documented
  short-range behaviour and every existing caller and test untouched.

**main.py:** `_capture_position` derives `heading` whenever the overlay supplied
a CamDir line and the capture has a local frame, and leaves heading UNSET (rather
than fabricating 0) when it cannot. All three `calculate_bearing` call sites now
pass `use_local_frame=True`; a version test asserts that count stays equal to the
number of call sites, so a future call site cannot silently mix conventions.

**Tests: 218, up from 190 at the start of the day.** The 22 new bearing tests use
the REAL field data as fixtures: all 39 frames from the three Daymar sweeps, each
asserted against the compass heading the game itself displayed. That is ground
truth rather than the author's expectations, which matters because two of my own
expectations were wrong when first written:
- I asserted reciprocal bearings differ by 180 degrees. They differ by 181.16,
  and the meridian convergence predicted by spherical geometry
  (`d_lon * sin(mean lat)`) is 1.16. The test now asserts the spherical value,
  which is a stronger check: a subtly wrong east or north axis would still pass a
  loose plus-or-minus-two-degree test.
- I asserted the same CamDir must give clearly different bearings at two
  different sites. For a view lying in the equatorial plane observed from two
  points ON the equator it gives exactly the same bearing, which is correct
  geometry. The test now asserts the spread across several separated positions.

Both corrections were to MY expectations, verified against theory, not
adjustments to make the implementation look good; the implementation did not
change in response to either.

**INSTALLED to the live env 2026-07-26**, Wingman closed: `navigation.py`,
`main.py`, `__init__.py` copied to custom_skills. All 12 live runtime files
hash-verified identical to the dev tree (`update_release.py` is the only
difference and is correctly dev-side). Live reports VERSION 4.9.0.9, exposes
`camdir_to_bearing` / `local_basis` / `surface_bearing`, wires heading in
`_capture_position`, shows 3 bearing call sites against 3 `use_local_frame=True`,
keeps the 4.9.0.8 pos_raw fix, and still has zero game-input capability. All
installed .py files compile, and the installed copy converts the real WolfPoint
frame to 2.69 degrees against the 0 the game displayed. Needs a full
WingmanAiCore restart. Rollback: `release_version/` still holds 4.9.0.7.

**Not released:** uncommitted per the skill release flow, and `release_version/`
deliberately NOT rebuilt, so it lags at 4.9.0.7 until the next release build.

## 2026-07-26 — SOLVED: CamDir is Euler angles in the BODY frame; bearing recovered to under 1 degree

The parked heading-semantics item is answered. Two clean 13-frame sweeps taken
standing OUTSIDE on the surface of Daymar, WolfPoint (20-28/20-29) and Nuen
(20-33/20-34), both perfect 30-degree sweeps with exact closure.

**The rule:**
```
euler   = (-camdir[0], camdir[1], camdir[2])   degrees
R       = rotation from euler, EXTRINSIC 'yxz', in the BODY-FIXED frame
forward = first column of R
bearing = atan2(forward . east, forward . north)  with the local basis at the
          player's position (up = r/|r|, north = tangent component of +Z, east
          = north x up)
```

**Accuracy.** Fitted at WolfPoint, then applied to Nuen with NOTHING refitted:

| site | latitude | bearing stdev | max error | constant bias |
|---|---|---|---|---|
| WolfPoint (fit) | 18.92 | 0.52 deg | 2.69 deg | +2.09 deg |
| Nuen (blind) | 4.96 | 0.80 deg | 2.16 deg | -0.52 deg |

CamDir prints truncated integers, so a few tenths of a degree is the floor and
both sites sit on it. Independent corroboration: the model recovers the view
elevation as -0.38 and -0.39 degrees mean (stdev 4.8 and 3.0), i.e. it works out
unaided that the player was holding roughly level, and it absorbs the wander
instead of breaking on it.

**Why every earlier model failed.** CamDir is referenced to the BODY's axes, not
to the local horizon, so converting it to a compass bearing REQUIRES the player's
position. Consequences that now make sense:
- `heading = k - camdir[2]` held in the Nyx hangar only because the local up
  there sat about 10 degrees off the reference axis, so the two frames nearly
  coincided. A small-angle accident, not a law. At WolfPoint (colatitude 71) the
  same fit oscillates between k = 233 and 294.
- camdir[0] correlates 0.974 with the view's elevation above the body's
  EQUATORIAL plane and shares its exact range of plus/minus the colatitude, which
  is why |camdir[0], camdir[1]| tracked each site's colatitude (about 10 in the
  Nyx hangar, 74 at WolfPoint, 79 and 92 at the two in-ship Daymar sites).
- camdir[2] advances unevenly (-10, -19, -60, -61, -19, -11 per 30-degree step)
  in exactly the rhythm of the view direction's equatorial azimuth, because it is
  measured about the body axis rather than the local vertical.

**Third site (Dunlow) closed the residual question: no position term is
justified.** Full three-site result, model fitted ONLY at WolfPoint:

| site | lat | lon | bias | stdev | max | elevation wander |
|---|---|---|---|---|---|---|
| WolfPoint | 18.92 | 90.89 | +2.09 | 0.52 | 2.69 | 4.78 |
| Nuen | 4.96 | 93.70 | -0.52 | 0.80 | 2.16 | 3.00 |
| Dunlow | 14.77 | 100.45 | -4.52 | 1.72 | 8.14 | 11.74 |

The per-site bias correlates -0.994 with longitude, which is NOT evidence: three
points against two candidate predictors fits almost anything, the same trap that
motivated using three sites in the first place. Splitting all 39 frames by how
well the level view was held settles it instead:

| frames | n | bias | stdev |
|---|---|---|---|
| \|elevation\| < 5 deg | 23 | -0.09 | 2.21 |
| \|elevation\| >= 5 deg | 16 | -2.28 | 3.36 |

Where the capture was clean the bias vanishes. Dunlow simply had the roughest
sweep (11.7 deg of wander against 3 to 5 elsewhere) and, coincidentally, the
largest longitude. **Conclusion: the conversion needs no position-dependent
correction beyond the local basis it already uses.** Accuracy is roughly 1 to 2
degrees with a level view, against a deflection ring that needs perhaps 5. Not
worth further flying.

**Method note:** this was only fittable because the ground truth (true view
direction from compass plus position) was known for all 13 orientations, which is
what turned "guess a model" into "solve for the convention".

## 2026-07-26 — ROOT CAUSE: the compass is container-relative, CamDir is not

Two frames at WolfPoint on Daymar, same facing, 70 seconds apart, one on foot
INSIDE the ship and one standing on the ground outside
(`20-23-11-26F` and `20-24-24-F80`).

| | inside ship | outside on the ground |
|---|---|---|
| CamDir | -74, 10, 73 | -73, 10, 76 |
| compass (measured) | 359.68 | 168.20 |
| innermost zone | DRAK_Clipper_737584760565 | OOC_Stanton_2b_Daymar |
| OOC position | -4339.31m 279.0975km 95.6796km | -4340.15m 279.0898km 95.6738km |

CamDir is unchanged, so the player did not turn; the position moved about a
metre. The compass moved 168.5 degrees. User's explanation, confirmed by the
numbers: **on foot inside a ship the compass zeroes on the ship's nose**, so the
gap is simply the bearing the ship was parked on.

**Consequences, in order of importance:**

1. **The compass is only a true local bearing when the player is not inside a
   vehicle.** Any calibration that pairs a compass reading with CamDir must be
   captured outside, standing on the surface.
2. **CamDir is container-stable.** It did not change when the innermost zone
   changed from the ship to the body. So one conversion should serve both on-foot
   and in-cockpit use, which is what the skill needs since players mark waypoints
   from both. ONE observation at ONE facing, so confirm across a couple of
   orientations before relying on it.
3. **This retroactively explains the three-location failure.** Every compass
   reading in those 39 frames was referenced to each ship's parked orientation,
   and the ship was parked differently at each site, so a stable quantity was
   being paired against a reference that moved between locations. Fitting it would
   have produced three confident and meaningless offsets. (The non-coplanarity of
   those sweeps is a SEPARATE defect, still unexplained: a ship-relative elevation
   reference would tilt the sweep plane, not unflatten it. Since the surface path
   works and is the real use case, it is not worth chasing.)

**First valid surface data point:** at WolfPoint, heading 168.20 with camdir[2] =
76 gives k = 244.20. Taking the in-ship compass at face value for the same frame
would have given 72.68, which is the size of error this caught.

**Protocol from here:** all heading-calibration frames are captured OUTSIDE, on
foot, standing on the surface. Three or four frames per site, three sites. The
coplanarity gate still applies before any offset is derived.

## 2026-07-26 — Three-location Daymar run: coordinates VALIDATED against ground truth, heading sweeps UNUSABLE

39 frames in three clusters of 13, `Screenshots\coordinate test\`, all on Daymar
in one session, positions supplied by Lars as a distance matrix.

**COORDINATE PIPELINE VALIDATED END TO END.** Positions read from the OOC line at
each site, drift between first and last frame at most 0.1 m:

| site | OOC position | \|r\| | elevation over the 295 km datum |
|---|---|---|---|
| Dunlow Ridge | -51.8856km 280.9415km 75.3107km | 295452.1 m | 452.1 m |
| Nuen Waste Mgmt | -18.9175km 293.3499km 25.5031km | 295063.5 m | 63.5 m |
| WolfPoint | **-4339.05m** 279.0968km 95.6796km | 295073.6 m | 73.6 m |

Distances computed from those coordinates against the user's figures: 61.005 vs
61.0, 51.759 vs 51.7, 73.078 vs 73.1 km. Errors of +5, +59 and -22 m on 51 to 73
km baselines, i.e. at the rounding limit of figures quoted to 0.1 km. The user's
numbers are STRAIGHT-LINE, not surface arc: arc values run 115 to 166 m high
consistently. This is ground truth from outside the codebase, so it validates the
v4.9.0.8 coordinate path in a way the author's own unit tests cannot.

Note WolfPoint's X printed in METRES (-4339.05m) while its Y and Z printed in km,
inside one line. That is the per-axis autoscaling occurring in a real capture at
a real site, and it is exactly the component that a pre-4.9.0.8 reader would have
been 1000x wrong on. The fix earns its keep on live data.

**HEADING SWEEPS UNUSABLE, and not because of the frame.** All three sweeps were
captured ON FOOT INSIDE THE SHIP (innermost zone `DRAK_Clipper_737584760565`,
confirmed visually: the frames show the cabin from behind the pilot seat). Under
those conditions neither model holds:
- `k = heading + camdir[2]` is not constant: 20, 32, 341, 321, 338, 1, 22, 34 ...
- treating CamDir as a body-frame direction vector gives bearings off by -10 to
  +150 degrees, and the best-fit plane normal sits 56.8 degrees from local up.

Diagnosis via coplanarity, which is decisive because a level 360 sweep must be
coplanar in ANY rigid frame (a frame change rotates the plane, it cannot unflatten
it), so this rules out "CamDir is expressed relative to the innermost zone" as the
explanation:

| sweep | RMS out-of-plane | third-component steps |
|---|---|---|
| 2026-07-26 hangar, on foot | 2.7 deg | -30 -29 -31 -32 -30 -31 -28 -30 ... |
| Daymar L1, inside ship | 15.9 deg | -18 -81 -50 -13 -7 -9 -18 -83 ... |
| Daymar L2, inside ship | 16.9 deg | -3 -4 -21 -139 -10 -3 -3 -4 ... |

The view was genuinely not level, wandering about 16 degrees RMS in elevation.
Probable cause: inside a cabin there is no horizon and the elevation reference
used outdoors does not serve the same purpose there. The step pattern in both
in-ship sets repeats with period 6 (that is, every 180 degrees of heading), which
is a real structure worth revisiting if this is ever modelled, but it is not
worth fitting from data whose control variable was not held.

**What is still needed:** the same sweep STANDING OUTSIDE ON THE SURFACE, which
is both the condition where the model worked and the actual use case for marking
a waypoint. The three positions are already measured and validated, so only the
sweeps need repeating: 3 to 4 frames per site is enough now that the slope is
known. Three sites remain necessary, since two can be fitted by any model with
two free parameters and therefore test nothing.

**Method note kept deliberately:** the coplanarity check is what stopped a fit
from being forced onto bad data. Any future sweep should be run through it before
any offset is derived from it.

## 2026-07-26 — SOLVED (in one environment): CamDir third component is yaw, heading = k - camdir[2]

13-frame 360 sweep by Lars, 30 degrees per step, elevation held at zero on the
in-game indicator, one position, closing back on the start. Frames
`ScreenShot-2026-07-26_15-51-53-F86` through `15-52-55-24D`. Compass headings
measured geometrically from label pixel positions (tool validated against three
hand reads first); CamDir read from the overlay line. Closure is exact: frame 13
returns to heading 0 with CamDir third component -85, identical to frame 1.

| heading | CamDir | | heading | CamDir |
|---|---|---|---|---|
| 0 | -10, 1, -85 | | 210 | 8, 3, 64 |
| 30 | -10, -3, -115 | | 240 | 5, 8, 34 |
| 60 | -7, -8, -144 | | 270 | 1, 10, 4 |
| 90 | -2, -10, -175 | | 300 | -4, 9, -26 |
| 120 | 3, -9, 153 | | 330 | -8, 6, -56 |
| 150 | 7, -6, 123 | | 360 = 0 | -11, 1, -85 |
| 180 | 9, -1, 92 | | | |

**Result: `heading = (k - camdir[2]) mod 360` with slope exactly -1.** Fitting k
over all 13 frames gives k = 274.15 with stdev 1.07 and a spread of 4.0; worst
residual against the measured compass is 2.15 degrees. CamDir prints truncated
integers, so roughly 1 degree is the noise floor and this is at it. The sign is
inverted: yaw counts the opposite way round from the compass.

**The pre-registered prediction was half wrong, usefully.** One component swept
(the third, yaw) as predicted, but the other two did NOT hold still. They rotate
as a pair of near-constant magnitude (8.5 to 11.1, mean about 9.8) whose phase
tracks the heading with a constant offset near 171 degrees. So holding the
in-game elevation indicator at zero does NOT produce camdir[0] = camdir[1] = 0:
the reference vertical CamDir is measured against sits about 10 degrees off the
local up at that spot. Any implementation assuming level view means zero pitch
and roll would be wrong. (Side effect: the pair's phase is a second, independent
heading estimate, but at plus or minus 5 degrees from integer quantization on
small values it is far worse than the third component's 2, so it is not worth
using.)

**SCOPE CAVEAT, and it matters: this was captured with NO local frame.** The zone
stack reads `Hangar_MediumFront_Kaboos_Nyx` -> `glaciemring_segment_wtn-020` ->
`SolarSystem` -> `Root`, with no `OOC_` line, so the sweep happened inside a
hangar in Nyx rather than on a planetary surface. The STRUCTURE (slope -1,
integer degrees, offset) is a sign-and-origin convention and is very likely
general. The OFFSET k = 274.15 is specific to that position and reference frame
and must NOT be hardcoded for surface waypoints. Repeating the same sweep while
standing on a body with an OOC line present is what calibrates the surface case,
and comparing two positions on the same body is what shows whether k is derivable
from position via the local north basis or has to be measured per location.

**Two incidental corroborations of earlier findings, from the same zone stack:**
- Z passes through nested frames unchanged again: the segment zone and the
  SolarSystem line both read 627.71m, matching the Daymar OOC-versus-SolarSystem
  Z identity found earlier the same day.
- Per-axis unit autoscaling in a single line again:
  `-14972522.5839km -914811.0449km 627.71m`, and 627.71 m being under the ~10 km
  boundary prints as metres, consistent with the bracket in the probe entry.

**One inference NOT supported:** the SolarSystem zone id here (729494885314)
differs from the Stanton session's (729494885309), but the two frames are in
different SYSTEMS, so the difference is consistent with one id per system rather
than evidence that the id tracks a session or shard instance. The zone-id frame
guard proposed earlier still works as a must-match check; this data does not
promote it to a session-change detector.

## Version: 4.9.0.8 (local XYZ moved to the OOC Pos line, 2026-07-26)

Fixes the break found the same day: SC 4.9 omits `CamPos Planet Zone` while on a
planet surface, and the 4.8-era prompt both required that line and explicitly
forbade the one line that does carry the data. On this build a surface mark had no
coordinate source at all, which is the probable root cause of the 2026-07-22
confabulation. Coded on the main loop (Opus 5) at the user's direction; the
standing model-split agreement was suspended for this session only.

**Prompt (`scanner.py`):**
- `pos_raw` is the new PRIMARY coordinate source: the three Pos values from the
  OOC zone line, copied VERBATIM as strings including each unit suffix. The
  prompt states plainly why, that dropping a "k" moves the waypoint by a factor
  of 1000, and requires null over a guess for an unreadable suffix.
- `x`/`y`/`z` are now documented as OPTIONAL and sourced from CamPos, since that
  line is absent in surface states. The instruction "Read x, y, z from the CamPos
  Planet Zone line, NEVER from the OOC zone Pos line" is GONE; a regression test
  asserts it cannot return.
- The model is told never to copy pos_raw into x/y/z or derive one from the other,
  because the software compares them as two independent readings.

**Parsing:**
- `_parse_length_m` converts one raw token to metres. The unit suffix is
  MANDATORY: an unsuffixed token returns None and the capture is refused rather
  than assumed to be metres. That is the whole point of the change.
- `_coords_from_pos_raw` / `_coords_from_campos` produce the two candidate
  triples. A partial CamPos triple is never used, since it can be neither stored
  nor cross-checked.
- When BOTH are present they must agree within 1.0 m (the OOC line prints 0.1 m
  resolution), else `last_reject_reason = "coord_mismatch"` and the payload is
  discarded. Two conflicting reads mean one is wrong, so neither is trusted.
- `pos_raw` present but unparseable sets `last_reject_reason = "unreadable_units"`
  instead of failing silently.
- CamPos-only payloads still work unchanged, so deep-space reads and older builds
  keep functioning. The change is additive.

**Echo defences extended to the new field:** `_ECHO_RAW_TOKENS` canaries every raw
Pos token printed in the prompt, and coordinate canary matching moved from exact
float equality to a 0.01 m tolerance so an echo of the km-form example is caught
after unit conversion as well as before it. Two new lock tests assert every
unit-suffixed value in a prompt OOC Pos line has a canary, which closes the hole
the vision-example-echo lesson named (an example value without a canary).

**Badges:** two new one-time WARNING badges, for `unreadable_units` and
`coord_mismatch`, following the existing per-reason badge pattern in
`_capture_position`.

**Tests: 190 passing, up from 153** (my own run, full suite from the repo root
with the skill on PYTHONPATH). 32 new in `tests/test_pos_raw_units.py`, including
the real 2026-07-26 Daymar reading as a regression fixture
(`9810.08m -174.2880km 238.0511km` must become 9810.08 / -174288.0 / 238051.1 m),
every rejection path, and a guard that the tolerance-based canary check does not
over-reject genuine nearby coordinates. `test_version_4907.py` was replaced by
`test_version_4908.py` per the per-bump convention, carrying the no-game-input
assertions forward because that is a standing decision and not a one-release
change.

**One existing test was edited**, which cuts against the fix-the-code-not-the-test
rule, so it is called out explicitly: `test_scanner_echo.py`'s
`test_echo_markers_and_coords_are_the_canaries` pins `_ECHO_COORDS` to an exact
literal as a tripwire against silently weakening echo detection. Adding canaries
trips it by design. Its intent (canaries must match the prompt's examples) is
preserved and strengthened, not relaxed: the literal now includes the new
canaries and two further lock tests were added alongside it.

**PROPOSED, not implemented, needs a second data point first:** a geometric
integrity gate. The Daymar capture satisfies `|pos| == radius + ElevationUnderCam
+ Altitude` to about 0.3 m (295.196 km against 295.000 km + 194.5625 m +
1.732055 m = 196.29 m versus a 196 m difference). Such a gate would have
deterministically rejected the 2026-07-22 payload, whose 356 km magnitude sat
nowhere near microTech's 1000 km radius, so it is the strongest confabulation
guard available. Held back because the semantics of ElevationUnderCam versus
Altitude rest on ONE observation, and a wrong tolerance or a wrong sum would
refuse legitimate marks in the field and cost a flight to diagnose. Confirm the
identity on a second body before implementing.

**INSTALLED to the live env 2026-07-26**, on the user's go, with Wingman closed:
`scanner.py`, `main.py`, `__init__.py` copied to
`AppData\Roaming\ShipBit\WingmanAI\custom_skills\sc_navpoint`. All 12 live runtime
files hash-verified identical to the dev tree (`update_release.py` is the only
difference and is correctly dev-side build tooling). Live reports VERSION 4.9.0.8,
carries the pos_raw primary rule, no longer carries the "NEVER from the OOC zone
Pos line" instruction, exposes both new badges, and still has zero game-input
capability (no pydirectinput import, no vendored package). Needs a full
WingmanAiCore restart, not a UI reload. Rollback path if needed:
`release_version/` still holds the 4.9.0.7 build.

**Not released:** uncommitted per the skill release flow, and `release_version/`
deliberately NOT rebuilt, so it lags at 4.9.0.7 until the next release build.

## Version: 4.9.0.7 (game-input capability removed, 2026-07-24)

User decision after the 4.9.0.6 live test: the skill must NEVER send input to
the game. AI-typed console commands could easily be read by CIG as cheating,
so the bar is zero autonomous input, not "probably fine". Removed in full:
enable_displayinfo and disable_displayinfo tools, _send_console_command,
_get_console_key + the console_key custom property, the pydirectinput import,
and the entire vendored pydirectinput-rgx 2.1.3 package (nothing else used it;
the vendoring rationale from v4.8.0.3 is obsolete). install.bat step 4 reworded
(no keystroke claim), pydirectinput echo line dropped, and both dev-side
manifests (skill_installer_config.json, update_release.py RELEASE_DIRS) lost
their pydirectinput entries.

The same live test showed the wingman LLM paraphrases tool hints and drops key
names (spoke "activate it in the game console" with no key at all, despite the
tilde text in the tool result). Countermeasures: both mark_location hints now
lead with "Relay this to the player word for word:" and state the skill cannot
enable the overlay itself; default_config.yaml lost the enable/disable tool
docs and example mappings, gained instruct-the-player guidance (exact key and
command) plus a prompt rule to relay a hint's key names and console commands
verbatim, never summarize.

Tests: test_console_key.py deleted with its subject; the two test_main_strings
assertions on the deleted tools replaced with player-guidance coverage;
test_version_4907.py replaces 4906 and adds a regression test pinning the
absence of pydirectinput, _send_console_command, and both tool definitions.
Suite 153/153 (was 160; net loss is the deleted console tests).

release_version REBUILT from the cleaned tree via update_release.py (13 files,
hash-verified against dev, no pydirectinput), so no distributable copy carries
the console-typing capability. Installed live 2026-07-24: main.py, __init__.py,
default_config.yaml copied, live pydirectinput\ folder deleted, all 12 runtime
files hash-verified, Wingman closed at the time. Coded by an Opus 4.8 agent,
spec and QA by Fable 5 (own 153/153 run, clean greps of dev, release, and live
trees).

## Version: 4.9.0.6 (console key hint fix, 2026-07-24)

Live testing showed the two "displayinfo not available" hints in mark_location
(and the prerequisites line in default_config.yaml) told the player to open the
console with F1. The Star Citizen console opens with the tilde key (~); the
skill's own enable_displayinfo already uses the backquote fallback, so the hint
text was simply wrong. Replaced "with F1" with "with the tilde key (~)" in
main.py (both hint blocks), default_config.yaml, and the release_version copies
of both (targeted edits, no release sync run; release_version otherwise stays
the 4.9.0.4 build). Bumped 4.9.0.5 -> 4.9.0.6 in main.py, __init__.py, and
skill_installer_config.json (version identifies code); tests\test_version_4905.py
replaced by test_version_4906.py per convention. Installed to the live env
2026-07-24 (main.py, __init__.py, default_config.yaml copied; all 15 runtime
files hash-verified identical, Wingman closed at the time). Coded by an Opus
4.8 agent, spec and QA by Fable 5 (own 160/160 suite run, grep both trees, no
F1 remains in the skill).

## Version: 4.9.0.5 (confabulation gate, fixed-pixel crop, metadata cleanup, 2026-07-22)

Internal update per skills/Versioning.md, NOT a requalification; SC_TARGET stays
4.9.0 and the in-game verification hold is unchanged. Coded by an Opus 4.8 agent,
spec and QA by Fable 5.

### The live incident (2026-07-22)

During the 4.9.0 requalification flight, mark_location stored a fully
confabulated waypoint. The player was in a hangar at an asteroid base in Nyx:
zone Hangar_LargeFront_Rest_Nyx, the overlay showed "No Current Planet", there
was NO OOC_ line, and the Planet:, CamPos Planet Zone:, and
Radius/ElevationUnderCam/Altitude lines were ENTIRELY ABSENT (not the stale
present-body case the prompt taught). The Vision model nonetheless returned
local_frame true with zone "Hangar_LargeTop_NewBabbage" (the one realistic
example string still left in the extraction prompt), a body_token that split to
system "LargeTop" / body "NewBabbage", invented coordinates (magnitude 356 km,
physically inside microTech whose radius is 1000 km), and a garbled server id.
The v4.9.0.4 exact-value echo tripwire did not fire because none of the exact
canary values appeared: the model recombined the example string rather than
reproducing an exact canary.

### What changed (four fixes)

- **Deterministic plausibility gate (scanner.py).** New module constant
  `_KNOWN_SYSTEMS = {"stanton", "pyro", "nyx"}` (extend when CIG ships a new
  system). In the local_frame true branch, after the echo tripwire, the
  body_token is split on "_"; if it has fewer than two segments OR its leading
  segment is not a known system, the capture is rejected (logger.warning naming
  the token, `last_reject_reason = "implausible_body"`, return None). This
  intentionally rejects single-token bodies: the old lenient split let a
  confabulated single word through as body == system, and a real OOC token is
  always System_designator_Body. The 2026-07-22 "LargeTop_NewBabbage" token is
  caught here even though no exact canary value appeared.
- **Canary the last realistic example.** The prompt's remaining realistic
  local-zone example "Hangar_LargeTop_NewBabbage" is replaced with the
  fictitious "Hangar_ExampleSize_ExampleCity", and that string joins
  `_ECHO_MARKERS`, so an echo of it now also trips the exact-value tripwire.
- **Fixed-pixel detail crop (scanner.py).** The overlay renders at a FIXED
  PIXEL size (measured ~800x350 px on 4.9.0), so the old fractional crop
  scaled wrongly with monitor size: on a 5120 px ultrawide the right-45% box
  was 2304 px downscaled to 900 px, shrinking the overlay text 2.56x and
  degrading legibility. The crop is now a fixed top-right box (default 1100x500,
  constants `_DETAIL_BOX_WIDTH` / `_DETAIL_BOX_HEIGHT`, overridable via the
  NavPointScanner constructor), clamped so it never exceeds the screen, sent at
  NATIVE resolution (no downscale, no upscale). Autocontrast is kept. The old
  `_CROP_RIGHT_FRACTION` / `_CROP_TOP_FRACTION` / `_DETAIL_WIDTH` constants and
  the resize code are gone. The context image (full screenshot at 1200 px wide)
  is unchanged.
- **Prompt reality update (scanner.py).** The LINE SHAPES header now reads
  "SC 4.8/4.9". The local-frame gate now states that in no-planet states (space
  stations, asteroid bases, deep space) the Planet:, CamPos Planet Zone:, and
  Radius/ElevationUnderCam/Altitude lines may be ENTIRELY ABSENT and a literal
  "No Current Planet" line may appear (both mean local_frame false), that
  "Current player location" can be a multi-word station form like
  "AsteroidClusterBase Nyx Social Keeger 001", and that a menu/loading state
  ("INVALID LOCATION ID", ServerTime "Thu Jan 1 ... 1970") returns the error
  object.

### Also

- **main.py:** a one-time WARNING chat badge mirrors the example_echo handling
  for the new "implausible_body" reject reason (guard `_implausible_badge_shown`).
  The mark_location no-local-frame refusal message is reworded to name space
  stations and deep space and to say off-planet waypoints are planned but not
  yet implemented (hint field unchanged). VERSION and the docstring line to
  4.9.0.5.
- **default_config.yaml metadata cleanup:** display_name loses "(Outdated)", the
  "Outdated" tag is removed, and the description is rewritten to describe the
  current surface-waypoint skill (no pre-4.7 / use-with-caution language). This
  is presentation only; the verification hold and auto_activate:false stand.
- **__init__.py / skill_installer_config.json:** version 4.9.0.5.

### Tests

160/160 (was 147). New `test_plausibility.py` (gate rejects the confabulated
"LargeTop_NewBabbage" token, single-token and empty tokens; accepts
Stanton/Pyro/Nyx case-insensitively; fixed-pixel crop geometry incl. clamping
and constructor override). Added: the new local-zone canary in
`test_scanner_echo.py` (plus the `_ECHO_MARKERS` assertion), and the reworded
refusal message in `test_main_capture.py`. `test_scanner.py`'s single-token test
was inverted from body==system to an implausible_body rejection (it encoded the
old lenient split we deliberately changed). `test_version_4904.py` was replaced
by `test_version_4905.py`.

## 2026-07-21 - Release packaging created (no version bump)

sc_navpoint was the only SC skill without release packaging; the live AppData
install had been synced by running the root install.bat directly. Added the
standard packaging, modeled on sc_navigator (coded by an Opus 4.8 agent, spec
and QA by Fable 5):

- `update_release.py`: syncs dev -> `release_version/`. RELEASE_FILES are the
  seven root runtime files (incl. install.bat); RELEASE_DIRS are `navpoint_ui/`
  and `pydirectinput/` (the vendored copy ships in the bundle). Unlike the
  navigator pattern, copytree excludes `__pycache__`/`*.pyc`/`.pytest_cache`
  because these dirs contain Python code.
- `skill_installer_config.json`: the third version-exposure location per
  skills/Versioning.md, previously missing here. version 4.9.0.4. Per the
  dual-manifest rule, any future runtime file must be added to BOTH this
  manifest and update_release.py.
- `release_version/` generated and verified byte-identical to the dev tree
  (16 files, no caches).

No runtime file changed, so the version stays 4.9.0.4.

## Version: 4.9.0.4 (Vision example-echo defense, 2026-07-20)

Internal update per skills/Versioning.md, NOT a requalification; SC_TARGET
stays 4.9.0 and the in-game verification hold is unchanged. Coded by an Opus 4.8
agent (implementation + spec tests), spec and QA by Fable 5.

### The live incident (2026-07-20)

In open space in Nyx (player location Nyxstar, no local frame), the Vision LLM
echoed the extraction prompt's worked example verbatim instead of reading the
overlay: it returned the example body (Clio), zone
(DRAK_Clipper_698212607305), CamPos coordinates
(123237.455097 / -313535.207901 / 14932.665921), and the example server_id. That
produced a phantom Clio waypoint. On the next capture the echoed server_id
differed from the stored one and tripped wipe-on-relog, which deleted the user's
renamed waypoint. Two failures compounded: the prompt taught the model real
values it could parrot, and a single unconfirmed server_id was enough to wipe.

### What changed (three fixes)

- **Canary example values in the Vision prompt.** Every concrete example value
  in `_EXTRACTION_PROMPT` (the LINE SHAPES block and the output JSON examples)
  is now an obviously-fictitious placeholder, keeping the line shapes and field
  structure intact: body token `OOC_ExampleSys_0x_ExampleBody`, ship zone
  `EXMP_ExampleShip_000000000000`, player location `ExampleSys0x` /
  `ExampleSolarSystem`, CamPos `111111.111111 -222222.222222 333333.333333`,
  server `pub-exam-ple-sc-alpha-000-00000000-game-00`, plus round CamDir,
  Radius/Elevation/Altitude, and SolarSystem/Root Pos values. The prompt now
  states the values are FAKE placeholders and adds an OUTPUT instruction: never
  emit an example value, use null for unreadable fields, return the error object
  when the overlay is unreadable.
- **Deterministic echo tripwire (scanner.py).** Module-level `_ECHO_MARKERS`
  (the canary strings) and `_ECHO_COORDS` (the canary coordinates). After a
  successful JSON parse, `_parse_json_response` rejects the capture (returns
  None) if body_token, zone, server_id, or location equals a canary string, or
  any of x/y/z equals a canary coordinate; it records
  `self.last_reject_reason = "example_echo"` (reset to None at the top of every
  call). `_capture_position` emits a one-time WARNING chat badge when a capture
  is rejected for that reason, telling the user the 4.9 overlay may not be
  readable yet.
- **Two-capture confirmation before wipe-on-relog (main.py + database.py).**
  Mirroring the arrival auto-stop, a server change is only acted on after TWO
  consecutive captures agree on the same new server_id. `_handle_server_change`
  now reads `database.get_stored_server_id()` (the stored session's server, the
  exact value `wipe_on_server_change` keys on); if the stored server is empty or
  equals the current one it clears any pending change and returns; the first
  differing capture records the new server as pending (logger.info, no badge);
  only a second consecutive capture agreeing on that server calls
  `wipe_on_server_change` and runs the existing post-wipe teardown. A single
  hallucinated server_id can no longer destroy waypoints.

### Tests

147/147 (was 128). New `test_scanner_echo.py` (canary string/coordinate
rejection, last_reject_reason set on trip and reset on a clean parse, real
`Stanton_4b_Clio` fixtures still parse, prompt regression guards) and
`test_server_change.py` (the two-capture gate matrix plus the once-only echo
badge). `test_version_4903.py` was replaced by `test_version_4904.py`. The
existing single-capture wipe tests in `test_main_capture.py` and the arrival
reset test in `test_arrival.py` were updated to the two-capture protocol.

## Version: 4.9.0.3 (mark-intent disambiguation, 2026-07-20)

Internal update per skills/Versioning.md, NOT a requalification; SC_TARGET
stays 4.9.0 and the in-game verification hold is unchanged. Spec-only, no
behavioural change to the marking pipeline.

### What changed

- **mark_location tool description hardened to an explicit ACTION contract.**
  In the 2026-07-14 live test the player said "mark a location" and the wingman
  answered by calling sc_log_reader's read-only get_current_game_state (which
  posted the location name) instead of marking a waypoint. The mark_location
  @tool description now states plainly that it is the ONLY correct tool for
  "mark location", "mark my location", "drop a waypoint", "save my position",
  "place a nav marker", "drop a pin", "remember this spot", and similar, and
  that reporting where the player is (for example via a game-state tool) does
  not mark anything. A companion read-only disclaimer was added on the
  sc_log_reader side so both tools point at the correct owner of the intent
  (details in that skill's DEVLOG).

## Version: 4.9.0.2 (arrival alert, configurable console key, 2026-07-19)

Internal update per skills/Versioning.md, NOT a requalification; SC_TARGET stays
4.9.0 and the in-game verification hold is unchanged. Coded by two Opus 4.8
agents (implementation + spec-only tests, SecondMind), spec and QA by Fable 5;
QA clean on the first round (128/128 tests in my own run, diff review, em-dash
and version scans; one cosmetic docstring correction by Fable). Spec: session
scratchpad navpoint-v4902-spec.md.

### What changed

- **Two-stage arrival alert (user decisions 2026-07-19).** Stage 1: while
  auto-tracking, a one-shot spoken heads-up ("Approaching {name}: {distance}
  to go") when the target comes within `arrival_alert_distance` (default
  1000 m, 0 disables). Stage 2: navigation ends automatically with an
  "Arrived at {name}. Navigation complete." announcement when TWO CONSECUTIVE
  polls read within `arrival_stop_distance` (default 250 m, 0 disables); the
  two-poll confirmation exists so a single Vision AI misread (the known
  bright-sky OCR hazard) cannot falsely terminate navigation. Polls with no
  bearing (capture failure, no local frame, body mismatch) neither count
  toward nor reset the confirmation streak; an out-of-zone reading resets it.
  Announcements use the proven upstream pattern (ats_telemetry):
  `threaded_execution(wingman.play_to_user)` + `add_assistant_message` +
  printr badge. The heads-up is suppressed when `navigate_to` already reports
  a distance inside the alert zone, and when the first in-zone reading is
  already inside the stop zone (arrival is imminent, no double announcement).
  Alert/streak state resets on every activation start and end (navigate_to,
  stop_navigation, delete of the active target, server-change wipe).
- **Configurable console key.** New `console_key` property (default
  backquote) for players who rebind the SC console. Used for both the opening
  and closing keypress in `_send_console_command`; an unrecognized
  pydirectinput key name falls back to backquote with a one-time WARNING
  badge.
- **HUD arrival tags.** `/api/nav/state` now carries both thresholds; the SPA
  shows a green ARRIVED (inside stop zone, takes precedence) or APPROACHING
  (inside alert zone) tag next to the distance readout, same mechanism as the
  STALE tag. The deflection ring is untouched.
- **Prompt block** gains a short paragraph telling the wingman these
  announcements come from the skill, not a tool call, so it must not repeat
  them.
- `tests/`: 74 -> 128 (arrival state machine incl. streak semantics, config
  getter clamping, console key fallback, nav-state threshold contract, app.js
  tag assertions + node --check, version consistency). Shared runtime stub
  factored into `tests/_stubs.py`.

### Decisions recorded

- Defaults chosen by the user: heads-up at 1 km, auto-stop at 250 m.
- Auto-stop requires two consecutive in-zone polls (Fable safeguard against
  OCR misreads); the harmless heads-up fires on a single reading.
- `update_position` carries no arrival logic (poll loop only).
- 0 and negative threshold values both collapse to 0.0 = disabled.

## Version: 4.9.0.1 (freshness window, wipe-on-relog, deflection ring, 2026-07-19)

Internal update per skills/Versioning.md, NOT a requalification; SC_TARGET stays
4.9.0 and the in-game verification hold is unchanged. Coded by two Opus 4.8
agents (implementation + spec-only tests, SecondMind), spec and QA by Fable 5;
QA clean on the first round (69/69 tests in my own run, diff review, em-dash and
version scans). Spec: session scratchpad navpoint-v4901-spec.md.

### What changed

- **Position freshness window (closes the 4.8.0.1 known issue).**
  `_capture_position` stamps `captured_at` on every capture; the HUD's
  `set_nav_target` only refuses cross-body targets from a position younger than
  `POSITION_FRESHNESS_S` (30 s, three missed polls at the 10 s max interval); a
  stale or unstamped position behaves like no position (the voice path stays
  the strict one, it always captures fresh). `/api/nav/state` carries a
  server-computed `position_age_s`; the SPA dims the position box with a STALE
  tag and never draws a bearing or the bubble from a stale reading. The nav
  panel re-renders every 2 s poll (not only on token bumps) so a position that
  simply stops updating visibly crosses the threshold.
- **Wipe-on-relog (user decision 2026-07-19; supersedes the parked cross-server
  stability verification).** Waypoints do not survive a server change. New
  `database.wipe_on_server_change`: a blank captured server never wipes
  (fail-safe against OCR garble); only a stored row with a non-empty server_id
  differing from the captured one proves a change, and then ALL rows are wiped,
  empty-server rows included. Hooked into every capture path; on wipe the user
  gets a WARNING chat badge, the active target is cleared and polling stops.
  Per-server keying is thereby resolved: the server_id column stays as wipe
  trigger and provenance only, and the server filter is gone from the HUD, the
  `/api/navpoints` endpoint, and the `list_navpoints` tool.
- **Deflection ring (replaces the compass target arrow).** User-defined
  instrument, mockup signed off 2026-07-19: a 12 px bubble inside a 70 px
  boundary circle, concentric when the target is dead ahead, wall contact at
  45 degrees or more off center (radial clamp, 58 px max travel). 2D including
  elevation (screen up = target above). Full color gradient driven by total
  offset alone (revised at user review): green up to 20 degrees (pulsing glow
  under 5), green-to-amber blend 20 to 45, amber-to-red blend 45 to 90, solid
  red beyond 90; while the bubble is pinned at the wall the continuing color
  shift encodes how far past the wall the target is. One rAF loop with 250 ms
  exponential smoothing on the angular offsets (color and position always
  agree), snap on reacquire, loop cancelled when no bubble is drawn. Cardinal
  letters (N/E/S/W) removed from the rose at mockup review; ticks, FWD
  triangle, and the '?' fallback face stay.
- **Default waypoint name convention (added at user review).** The no-name
  fallback in `mark_location` becomes `Location {N}, {body}` (e.g.
  "Location 1, Daymar"), replacing the row-count-based `Location {count+1}`
  which could collide after deletions and carried no location info. N is
  global across bodies: 1 + the highest surviving `Location <n>` name
  (case-insensitive scan over stored names). The guarantee is
  anti-collision, not a monotonic counter: a middle deletion never causes
  a duplicate live name, but deleting the current-highest waypoint frees
  its number (accepted at QA; a persistent high-water mark is not
  justified, and wipe-on-relog resets numbering anyway). `ask_for_name`
  is now an explicit auto-generated flag, so a user-chosen name starting
  with "Location" no longer triggers the name prompt.
- `tests/`: 45 -> 74 (freshness gate, all wipe semantics, capture-hook
  behavior, default-name convention, node --check on app.js); three tests
  targeting deleted server filter signatures replaced by
  signature-negative assertions, nothing weakened.

### Decisions recorded

- Freshness window fixed at 30 s, mirrored as a JS constant in the SPA.
- Wipe-all semantics: a proven server change also deletes empty-server rows;
  proof requires non-empty server ids on both sides.
- The ring is north-referenced (heading 0) until the parked camdir-to-heading
  verification lands; it becomes view-relative with zero UI change at that
  point, since it is driven by `horizontalOffset` from `calcBearing`.

## Version: 4.9.0.0 (2026-07-18)

All four SC skills aligned to game version 4.9.0 by user decision; VERSION (and the module docstring) and __version__ bumped to 4.9.0.0, SC_TARGET_VERSION and __sc_target_version__ to 4.9.0. In-game requalification against 4.9.0 is still pending; the verification hold in TODO.md is unchanged.

## Version: 4.8.0.3 (vendored pydirectinput, 2026-07-16)

First live activation of the skill in the packaged Wingman AI 2.1.1 app failed
with `ModuleNotFoundError: No module named 'pydirectinput'` (main.py import).
The dependency (pydirectinput-rgx 2.1.3) is listed in requirements.txt and is
present in the dev venv, so every dev test run passed and the gap was invisible
until a real end-user launch.

### Root cause

The frozen PyInstaller build under `C:\Program Files\WingmanAI\_internal` only
bundles the packages the Wingman core itself imports. The core never imports
pydirectinput, so the analyzer never pulled it into the frozen tree, and the
shipped binary has no copy of it. An earlier Devlog note called pydirectinput
"already a Wingman dependency"; that was true of requirements.txt (the source
checkout) but NOT of the shipped binary, which is the environment the skill
actually runs in.

### Fix

Vendored a pure-python copy of the package inside the skill directory:
`pydirectinput/__init__.py` (byte-identical to the venv 2.1.3 source),
`py.typed`, and `LICENSE.txt` (MIT). main.py already inserts the skill dir at
`sys.path` position 0 before the import, so the existing `import pydirectinput`
resolves the vendored copy with no statement change. In the dev environment the
vendored copy harmlessly shadows the identical venv version, so dev behaviour is
unchanged. Note that a stock (non-rgx) pydirectinput would not suffice: the
skill relies on `unicode_typewrite`, which exists only in the rgx fork, so the
vendored copy must stay pinned to pydirectinput-rgx.

## Version: 4.8.0.2 (Vision AI extraction recalibration, 2026-07-13)

The parked planet-tech-risky extraction work is implemented, built directly on
the same-day field inventory (`screenshots/overlay-field-inventory-2026-07-13.md`).
Coded by two Opus 4.8 agents (implementation + spec-only tests, SecondMind),
spec and QA by Fable 5; QA passed on the first round (45/45 tests, my own run;
diff review clean). Still NOT requalified: in-game verification remains, the
skill stays Outdated and auto_activate stays off.

### What changed

- `scanner.py`: `_EXTRACTION_PROMPT` fully rewritten for the real 4.8 overlay
  (level 2-4 tolerant). The local-frame gate is the OOC_* Zone-stack line;
  the prompt explicitly teaches the stale-body trap (Planet/CamPos/Radius/
  Altitude lines persist in space with garbage values). x/y/z come from
  `CamPos Planet Zone` (meters). New JSON contract: `error` /
  `local_frame:false` / `local_frame:true` + `body_token`. Parser derives
  body (last `_` token) and system (first token) deterministically, passes
  through zone/location/server_id, stores raw `camdir` 3-tuple when present,
  altitude/radius floats when present. `heading` is no longer emitted (the
  old 0-360 heading never existed in the overlay; consumers use
  `.get("heading", 0.0)` and keep working). Interim moon/planet mapping
  deleted. `ImageOps.autocontrast(cutoff=1)` applied to the detail crop
  (bright-sky washout mitigation).
- `main.py`: `enable_displayinfo` now types `r_displayinfo 2`; all level-4
  wording moved to level 2; version 4.8.0.2. Guard audit: all four x/y/z
  access clusters were already behind body/key guards from v4.8.0.1; no new
  guards needed (a `local_frame:false` result carries no x/y/z keys and an
  empty body, so existing guards refuse it).
- `default_config.yaml`: five r_displayinfo references now level 2 ("or
  higher" where natural). Outdated markers untouched.
- `tests/`: test_scanner.py rewritten to the new contract + new
  test_main_strings.py source audit; suite now 45 tests, all green. The old
  moon/planet interim-mapping tests were superseded by the spec, not
  weakened.

### Decisions recorded

- `enable_displayinfo` types level 2 (the minimal level with CamDir; least
  clutter). Advisory range for users remains 2-4.
- CamDir-to-heading conversion NOT implemented: heading semantics in the
  local frame are unverified (parked task). Raw camdir is stored so the
  conversion lands parser-side later without another prompt change.
- Missing `local_frame` key in an LLM response is treated as no-frame
  (fail-safe: refuse rather than risk a stale-body capture).

### Answered by the screenshot data (in-game confirmation still pending)

- A local frame EXISTS while flying above a surface (OOC line + meaningful
  CamPos throughout the descent), so in-flight guidance toward a surface
  waypoint is structurally possible.

## 2026-07-13 — First 4.8 overlay screenshots + r_displayinfo level decision

Lars captured the first batch of the parked overlay screenshots
(`screenshots/`, four shots, 5120x1440 JPG): one fixed scene (on foot,
New Babbage LargeTop hangar, microTech) at `r_displayinfo` levels 1 through 4
in timestamp order. A verbosity ladder, not the three contexts; those are
still to come.

Findings (Lars, from the full-res shots):

- Level 1 already shows the payload fields: nested `Zone:` stack with
  positions (innermost `Hangar_LargeTop_NewBabbage`, then OCC Stanton 4
  Microtech, then SolarSystem), `Current player location`, `CamPos Planet
  Zone`, `Radius` / `ElevationUnderCam` / `Altitude`.
- Level 2 adds the `CamDir` + FOV line at the top. CamDir is a MUST-HAVE
  (camera direction feeds bearing/heading work).
- Levels 3 and 4 only add VRAM info over level 2. Noise for our purposes.

**Decision (Lars): the skill advises `r_displayinfo` 2-4, minimum level 2.**
At recalibration this lands in: the five level-4 references in
`default_config.yaml` (description, prerequisites, tool docs), the
`enable_displayinfo` tool in `main.py` (currently types `r_displayinfo 4`;
whether it types 2 or stays 4 is a recalibration-session call, both are in
the advised range), and the module docstring. The Vision AI prompt must
tolerate the whole 2-4 range, meaning the VRAM lines may or may not be
present.

Also confirmed live this session: the "(Outdated)" skill-list label the user
spotted is the deliberate marker from `default_config.yaml`, working as
intended.

Still needed to unpark the recalibration (single fixed level, 4 is fine):
open space, in flight above a surface, and optionally on-foot outdoors (the
hangar shots carry an extra innermost zone line that open terrain likely
lacks; the prompt must handle both).

### Round 2 (same evening): SCREENSHOT BLOCKER CLEARED

Lars captured 36 more shots (22:08-22:19): one continuous journey at level 1
in a Drake Clipper: open space -> quantum to Clio (Stanton 4b) -> descent ->
landed. All three required contexts now exist. Full-resolution crop analysis
by an Opus agent, spot-validated by Fable 5 against the crops (QA clean),
written up in `screenshots/overlay-field-inventory-2026-07-13.md`. Key
results:

- **Local-frame discriminator:** presence of an `OOC_<System>_<body>` line in
  the Zone stack (equivalently `Current player location` = body token, not
  `*SolarSystem`). In open space the stack is Ship -> SolarSystem -> Root.
- **Stale-body trap:** `Planet:`, `CamPos Planet Zone`, `Radius`,
  `ElevationUnderCam`, `Altitude` are ALWAYS present; in open space they show
  the last/nearest body with garbage magnitudes (Altitude ~64,301 km). Field
  presence must never drive the capture decision; the extraction must gate on
  the OOC zone line.
- **Extraction targets:** body from `Planet:OOC_<body>` (status suffix
  stripped; it toggles non-monotonically and is meaningless), local XYZ from
  `CamPos Planet Zone` (meters, single unit), CamDir top line (level 2+ only).
- **Level correction:** the journey was level 1, which lacks CamDir entirely;
  level 2 also adds Session/ShardId/percentile/GI lines, not just CamDir (the
  earlier "only adds camera direction" note was incomplete; the 2-4 advisory
  stands, and level 2 is the recommended value).
- **Vision AI hazard:** white payload lines wash out against bright skies
  (dawn shot 22-18-49); plan a contrast preprocess on the crop.

The planet-tech-risky group is now UNBLOCKED on data. Remaining before code:
none. The extraction rework + prompt recalibration can be scheduled.

## Version: 4.8.0.1 (surface-only safe plumbing, 2026-07-12)

The planet-tech-safe half of the surface-only pivot is implemented. Version
bumped 4.8.0.0 to 4.8.0.1 per skills/Versioning.md: this is an internal update,
NOT a requalification, so the version does not move to the live SC patch. The
Vision AI recalibration and all in-game verification remain parked (see the
2026-07-12 decision entry below); the skill stays Outdated and auto_activate
stays off.

### What changed (coded by Opus 4.8 agents, QA by Fable 5)

- `database.py`: schema v2. A single required `body` column (the planet or moon
  owning the local frame) replaces `planet`/`moon`. Schema versioned via
  `PRAGMA user_version`; any pre-v2 database is dropped and rebuilt on init
  (pre-4.7 stellar waypoints are stale twice over, wipe not migrate; a warning
  is logged only when a non-empty table is wiped). `add_navpoint` raises
  `ValueError` on an empty body. `get_navpoints` gains a combinable,
  case-insensitive body filter; new `get_distinct_bodies()`.
- `scanner.py`: parse-side only. The result dict gains an interim
  `body` = moon over planet over empty mapping. The extraction prompt and
  capture logic are untouched (parked with the recalibration).
- `main.py`: `mark_location` refuses when no body is present (no local frame,
  open space). `navigate_to` captures position first and refuses a proven
  cross-body target without setting it; with no local frame it sets the target
  with approach guidance and a note. The poll loop feeds the HUD any valid
  position but never emits a bearing across frames. `update_position` reports
  body and explains missing bearings. `list_navpoints` gains a body filter.
- HUD (`navpoint_ui/`): `/api/navpoints` takes a body filter and returns
  distinct bodies; the SPA gets a body filter dropdown, always shows the
  waypoint's body, and shows guard states ("NO LOCAL FRAME (open space)",
  "Target on X, travel there first"); bearing/compass only when player and
  target share a body. `set_nav_target` returns 409 on a proven cross-body
  click.
- `default_config.yaml`: prompt block rewritten to surface-only semantics.
  Outdated markers, tags, description, and auto_activate untouched.
- New `tests/` suite (35 tests: schema v2 + wipe path, body validation and
  filters, scanner body mapping, navigation math sanity). All pass. Run them
  from the tests directory (`cd skills/sc_navpoint/tests && python -m pytest .`);
  from the repo root pytest imports the skill package, which needs the Wingman
  venv.

### Decisions recorded

- **Declared nav scope: short-range surface navigation** (back to a cave,
  wreck, outpost). The flat Cartesian math in navigation.py stays as-is; far
  targets on a curved surface yield chord distance and through-the-planet
  bearings, accepted for this scope and documented in the module docstring.
- **Per-server keying KEPT.** Dropping it requires the parked in-game
  verification that local frames are deterministic per body. The schema keeps
  `server_id` so removal later is a column drop, not a redesign.
- **Interim body derivation.** Until the parked prompt rework extracts the
  local-frame body explicitly, `body` is derived parse-side from the existing
  moon/planet extraction fields (moon wins as the more specific owner).

### Known issues introduced

- The HUD's 409 cross-body refusal compares against the last cached position,
  which can be stale (for example after traveling to another body without an
  active poll). The voice path is immune: `navigate_to` always captures fresh.
  Consider a position freshness window during requalification.

## Version: 4.8.0.0 (Star Citizen 4.8.0 live-test baseline, 2026-05-25)

Adopted the SC-patch versioning convention from
[`skills/Versioning.md`](../Versioning.md) and bumped to `4.8.0.0` for the
cross-skill 4.8.0 live-test baseline. Populated `__init__.py` with
`__version__` / `__sc_target_version__`; replaced the module-level
`SKILL_VERSION` constant with `VERSION` / `SC_TARGET_VERSION` class attributes
on `SC_NavPoint`; updated module docstring.

**CAVEAT — the version bump does NOT mean the skill is requalified.** The
OUTDATED status below still applies: Vision AI parsing of `r_displayinfo 4`
and per-server storage have not been re-validated against the 4.7+ client.
The version is being aligned now for SC-version-comparison consistency; an
end-to-end revival pass is still required.

## 2026-07-12 - Decision: partial hold lift, scope fixed to surface-only

Lars reopened the skill one day after the hold: scope is formally reduced to
navigation at planetary and moon surfaces only (confirms the 2026-07-11 field
test verdict; stellar/open-space remains permanently out of scope). The hold is
lifted **partially**, based on a code review that split the pivot work by
planet-tech redo risk:

**Planet-tech-safe (may proceed now):** local-frame semantics should survive
planet-tech, so design and plumbing work is not at redo risk.
- `database.py`: no frame/body concept exists. Surface-only makes the body the
  load-bearing key: a local XYZ is only meaningful relative to the body that
  owns the frame, so planet/moon go from informational strings to a required
  body key, and navigation must refuse cross-body targets.
- Existing stored waypoints are pre-4.7 stellar coordinates, stale twice over:
  wipe, do not migrate.
- Per-server keying may drop entirely if local frames are deterministic per
  body (hypothesis, still unverified in-game).
- `main.py` + UI: guard states for "no local frame present" (open space),
  body-based filtering in the HUD.
- Scope decision needed: `navigation.py` does flat Cartesian bearing math. In a
  body-fixed frame that is fine short-range, but a far target on a curved
  surface gets a bearing through the planet and a chord distance, not ground
  distance. Declaring short-range surface nav (back to a cave, wreck, outpost)
  as the scope keeps the math as-is.

**Planet-tech-risky (stays parked):** the Vision AI recalibration, which the
2026-07-11 hold was protecting. The `scanner.py` prompt rework (LOCAL set only,
refuse when absent) is cheap to write, but calibration iterations against the
live 4.8 overlay are the expensive, redo-prone part. Parked until the three
overlay screenshots are captured (on-surface, open space, in flight above a
surface) or Lars accepts the redo risk. Also parked: the in-game verification
items (heading semantics in local frame, cross-server stability, in-flight
local-frame availability).

TODO.md restructured to match this split.

## 2026-07-26 — CRITICAL: `CamPos Planet Zone` is GONE on the surface in 4.9, the surface extractor's XYZ source no longer exists

Found while reading the probe screenshots, not from a live mark. This is a
breaking change against the documented extraction rules and it very likely
explains the 2026-07-22 confabulation at its root.

**Observed on CL 12302499, both shots same session, same display level:**

Deep space, in a Drake Clipper (13-11-32), CamPos PRESENT with stale-body garbage:
```
Current player location : StantonSolarSystem
Planet:OOC_Stanton_2_Crusader  (Load Complete)
CamPos Planet Zone: 25956328796.289665 -40152564483.807266 19428930447.870174
Radius: 7450010.000000 ElevationUnderCam: 3.000000 Altitude 51601103324.170509
```

On foot on the Daymar surface (14-00-32), CamPos ABSENT:
```
Current player location : Stanton2b
Planet:OOC_Stanton_2b_Daymar (working) (Load Complete)
Radius: 295000.000000 ElevationUnderCam: 194.562500 Altitude 1.732055
XYPos: 12156.947554 -215982.917697 Page: 4 (+Z)
```

`Planet:OOC` is followed directly by `Radius`. Line counts confirm it is the one
and only difference: 28 text lines in the space shot against 27 on the surface,
and every other line is accounted for in both. Display level is identical (no
VRAM lines in either, so level 2 both), which rules out the obvious confound
that CamPos moved to a higher r_displayinfo level.

**This is the exact inverse of the documented rule.** The extraction rules in
`screenshots/overlay-field-inventory-2026-07-13.md` section 4 state that local
XYZ comes from `CamPos Planet Zone`, preferred over the OOC zone `Pos` line
because CamPos is single-unit metres, and that CamPos "is ALWAYS present, even in
deep space, with stale/garbage values". On 4.9 the always-present half is now
true only in space, which is the one place its value is useless.

**Not an on-foot behavior.** The 4.8 on-foot hangar shot
(`ScreenShot-2026-07-13_21-50-43-7E8.jpg`, New Babbage, microTech) has
`CamPos Planet Zone: 519474.308929 436066.432518 736357.378582` present and
correct, so being on foot did not remove it in 4.8. The change is in the client.

**Probable root cause of the 2026-07-22 confabulation.** That capture was on foot
and the journal recorded no CamPos line. The prompt asserts CamPos is always
present, so the model had no coordinate source, and it filled the gap from its
own worked example. The v4.9.0.5 plausibility gate catches the SYMPTOM (an
implausible body token) but the cause is a missing field, so recalibrating prompt
wording alone would not have fixed it.

**One capture still needed to pin the discriminator:** a 4.9 shot while seated in
a ship LANDED on a surface. CamPos present there means the rule is "absent on
foot in 4.9"; absent there means "absent in every surface state in 4.9". The
remediation is the same either way, since marking a cave on foot is the primary
use case and cannot require a cockpit.

**Remediation direction:** local XYZ must come from the `Zone: OOC_<body> Pos:`
line, which IS present on foot (today: `9810.08m -174.2880km 238.0511km`), with
CamPos demoted to an optional cross-check when it happens to appear. That line
carries the per-axis unit autoscaling described in the probe entry below, so the
unit-parsing work scoped for the space path is now REQUIRED for the surface path
too. It becomes shared infrastructure, which strengthens the case for doing both
frames in one change rather than sequentially.

## 2026-07-26 — RESULT: paired frame-stability probe PASSED, space scope is viable

Six screenshots, one session, CL 12302499, 5120x1440. Raw files in
`D:\Roberts Space Industries\StarCitizen\LIVE\Screenshots\` dated 2026-07-26
13-11-32 / 13-13-32 / 13-16-32 (run A, open space) and 14-00-32 / 14-03-16 /
14-05-38 (run B, Daymar surface). Read at native resolution from a 740x42 crop
of the Zone stack, upscaled 2x; every digit below is transcribed, not inferred.

**Run A, open space, Drake Clipper parked, ship-internal Pos constant at
`0.00m 11.57m 2.83m` (so the player never moved in the seat):**

```
all three shots: Zone: SolarSystem_729494885309 Pos: -60077861.1780km 21737086.4624km 19428930.4479km
```

Byte-identical across 5 minutes, i.e. stable to the last printed digit (0.1 m).

**Run B, standing on Daymar:**

| t | body frame (OOC_Stanton_2b_Daymar) | system frame (SolarSystem) |
|---|---|---|
| +0s | 9810.08m -174.2880km 238.0511km | -18930665.5623km -2610037.9730km 238.0511km |
| +164s | 9810.04m -174.2880km 238.0511km | -18930678.6315km -2610053.2858km 238.0511km |
| +306s | 9810.04m -174.2880km 238.0511km | -18930688.4737km -2610067.7097km 238.0511km |

Body frame: 4 cm of movement over 5 minutes (animation sway). System frame:
37.5394 km of drift, at a CONSTANT 122.75 / 122.97 / 122.68 m/s per interval,
with `dz` exactly 0.0000 km at every step.

**The outcome matrix came out exactly as predicted**, so the 2026-07-11 verdict
is now confirmed as correctly observed but scoped too broadly: the drift
mechanism is the rotating ATTACHMENT, not the stellar frame. A point that is not
attached to a rotating body has a stable system-frame address.

**Internal consistency checks, all passing** (these are why the result is
trusted rather than merely suggestive):
- Distance from the body centre computes to 295.196 km against the overlay's own
  `Radius: 295000.000000`, so the OOC frame origin IS the body centre and the
  player was on the surface.
- `dz` identically zero while X and Y move means the spin axis is the system Z
  axis.
- The Z component is identical on the OOC line and the SolarSystem line
  (238.0511km both), reproducing the 2026-07-13 Clio observation (14.9327km
  both). Resolved: body centres sit at system Z = 0 and the axes are aligned, so
  the body-to-system transform is a Z-axis rotation plus an XY translation, and
  Z passes through unchanged. The alternative reading (displayed Z is not a real
  system Z) is refuted, because run A shows a live system Z of 19428930.4479km.
- Tangential speed plus the 174.564 km distance from the spin axis implies a
  rotation period of 8941 s = 2 h 29 m. Computed from the six numbers only; if
  it matches Daymar's documented day, the kinematics are fully closed.

**Frame model, now evidence-backed:**
```
system_xy = rotate_Z(theta(t)) . body_xy + body_centre_xy(t)
system_z  = body_z
```

**HAZARD found, and it is the main cost of the feature: per-component unit
autoscaling.** The Zone `Pos:` lines pick a unit PER AXIS by magnitude, mixing
them inside one line (`9810.08m -174.2880km 238.0511km`). The threshold is
bracketed between 9.81 km (printed as metres) and 14.93 km (printed as km),
probably 10 km, not pinned. The surface path avoids this entirely by reading
`CamPos Planet Zone`, which is single-unit metres. A space path CANNOT avoid it:
there is no CamPos equivalent in deep space, so it must read the autoscaled line.
A dropped `m` suffix is a silent 1000x error carrying a plausible-looking value,
which is the exact failure shape of the 07-20 and 07-22 incidents. Any
implementation must capture the unit token per component and convert
deterministically in Python, never let the model pre-normalise.

**FREE DEFENCE found: `Zone: Root` duplicates `Zone: SolarSystem` digit for
digit** in all six shots today and in both 4.8 samples. Two separately rendered
lines that must agree gives a deterministic self-consistency tripwire at zero
cost, and a confabulating model cannot satisfy it by accident. This is a
stronger guard than the canary approach because it validates the actual payload
rather than checking for known-bad values.

Remaining before implementation: the cross-session origin check (record a space
landmark, relog, return, compare) is still unrun, and it decides whether stored
system-frame coordinates survive a session change. Nothing implemented, no
version change.

## 2026-07-25 — Finding: the 07-11 verdict does not cover open space (probe queued, nothing implemented)

Lars asked whether space-bound navigation could be added alongside planetside.
Re-reading the evidence says the question is genuinely open, for two reasons.

**1. The closing test never covered the case.** The 2026-07-11 field test found
stellar coordinates drift while standing still, and the mechanism it named is
body axial rotation. That applies to any point ON a body: the surface spins
under you, so your stellar address changes. A point in open space is not
attached to a rotating body and is not subject to that mechanism. The verdict
"locations in open space cannot be annotated" was inferred from a surface test.

**2. A usable field exists in space, and it is not the one we read.** The
verified 4.8 open-space transcription (field inventory section 2) carries
`Zone: SolarSystem_653869999737 Pos: 22445086.0353km 37122693.5258km 1634.91m`,
and the 4.9 open-space stack read (section 6) shows the same SolarSystem line.
`CamPos Planet Zone` is body-relative garbage in deep space, which is exactly
why capture is refused there, but the SolarSystem zone Pos line is a separate
field in a separate frame. Space support would therefore be a SECOND extraction
path (mixed km/m units, no OOC line, no body token) rather than a relaxation of
the existing one, and the OOC gate would stay as the discriminator between the
two rather than being weakened.

**Open question found while reading:** in the landed-on-Clio sample the OOC line
reads `123.2375km -313.5352km 14.9327km` and the SolarSystem line reads
`22476440.7100km 37091195.6577km 14.9327km`. X and Y transform between frames,
Z is identical to four decimals. Most likely body frames are translation-only
against the system frame with Stanton's bodies near Z=0; the alternative is that
the displayed Z is not a true system Z, which would make vertical unusable in
space. Not resolvable from the existing screenshots.

**Cost if the probe passes**, so it is priced before anyone commits: a frame
discriminator in the schema (local vs system), a second extraction path and
prompt, a plausibility gate variant for payloads that legitimately have no body
token (the current gate REQUIRES a known-system body token, so a space capture
fails it by construction), unit parsing for the mixed km/m line, HUD frame
handling, and a fresh set of confabulation defenses for the second payload
shape. That last item is the real cost given the 07-20 and 07-22 incidents:
every new extraction path is a new surface for the Vision model to invent
plausible numbers on.

**Planet-tech exposure differs by waypoint type**, which is new: a deep-space
point expressed in the star frame stays valid when bodies begin to orbit, so it
is MORE planet-tech-resilient than the surface case. But a waypoint whose value
is its proximity to something (a station, an asteroid base) goes stale as that
thing orbits away. Nyx, being stations and asteroid bases only, is mostly the
second kind.

**Probe design upgraded by Lars the same day:** run the identical t+0/+2/+5
protocol in space AND on a planet surface in ONE session, making the surface run
the positive control for the space run. This is strictly better than the
space-only probe: the surface run should show the local frame static and the
SolarSystem line drifting at the body's rotation rate, so a space run showing a
static SolarSystem line proves the drift mechanism is the rotating attachment
rather than the frame, instead of merely being consistent with it. It also
yields the drift rate, checkable against the body's known rotation period, and
it answers the Z question above from run B's shots at no extra cost (a surface
point on a body rotating about its own axis should keep Z while X and Y move).
Outcome matrix, confounds (residual ship velocity, moving inside the ship,
relogging between runs), and the surprise cases that would invalidate the
existing surface scope are written into TODO.md.

**Nothing implemented, no version change.** Probe added to TODO.md. Sequencing
recommendation: capture the probe data opportunistically, but do not build
against a second frame until the surface path is actually qualified on the
current client build, or we would be recalibrating two frames against an overlay
we have not yet proven we can read on CL 12302499.

## 2026-07-11 — Decision: INDEFINITE HOLD until planet-tech releases

Same-day follow-up to the field test below. Decision by Lars: the surface-only
pivot is shelved until CIG ships planet-tech (his estimate: late 2026 to early
2027). Rationale: no point building against the current overlay and coordinate
frames when planet-tech may rework them within 4-6 months; the Vision AI
recalibration is the expensive part and would likely have to be redone.

The field-test findings below remain the requalification baseline: on planet-tech
release, re-run the stationary frame test first (stellar vs local, static vs
dynamic), then resume the pivot checklist in TODO.md if local frames still hold.

## 2026-07-11 — Field test: coordinate frames on SC 4.8.x live — verdict: pivot to surface-only

In-game stationary test by Lars (stand still, watch `r_displayinfo` XYZ over time):

- The overlay now shows **two coordinate sets**: stellar and local.
- **Stellar coordinates are dynamic** even while standing still, because planets and
  moons rotate on their axis. A stored stellar XYZ goes stale continuously.
- **Local coordinates (on a planet or moon surface) are static.** A stored local XYZ
  remains valid over time.
- Forward-looking (CIG planet-tech, unreleased): moons will orbit planets and planets
  their star, making stellar coordinates even more dynamic. Lars's estimate from current
  dev speed (2026-07-11): initial release late 2026 to early 2027, with the actual
  content of the first patches highly debatable. Local (body-fixed) frames should be
  unaffected by orbital motion, so the surface-only pivot is expected to survive
  planet-tech (assumption, re-verify on release).

**Decision** (rule agreed 2026-07-11: dynamic frame → not viable, static frame →
highly valuable): the skill pivots to **surface-only waypoints in the local frame**.
Stellar-frame waypoints are permanently out of scope; locations in open space cannot
be annotated. Within that scope the skill is considered highly valuable and moves
from "on hold" to active requalification.

**Proposed revival direction (not yet implemented):**
- Rework the Vision AI extraction to target the LOCAL coordinate set only, and to
  refuse capture when no local frame is present (open space).
- Recalibrate scanner prompts against the 4.8 overlay layout (screenshots needed:
  one on-surface, one in space, one in flight above a surface).
- Verify heading semantics in the local frame before trusting the bearing/compass math.
- Test whether local coordinates are identical across servers; if the local frame is
  deterministic per body, per-server keying can likely be dropped (hypothesis, unverified).
- Test whether local coordinates remain available while flying above a surface
  (in the planet's physics grid); determines if in-flight guidance toward a surface
  waypoint is possible or if guidance starts only after landing zone entry.

## Status: OUTDATED — pre-SC 4.7 (2026-04-25)

This skill was built before Star Citizen patch 4.7, which delivered a major overhaul
of navigation points. The Vision AI parsing of `r_displayinfo 4` and the per-server
storage assumptions were calibrated against the pre-4.7 client, and have not been
re-validated against 4.7. Treat any waypoints, bearings, and zone/planet info this
skill produces as suspect until verified.

`auto_activate` has been turned off so the skill no longer loads by default — enable
it explicitly only when re-validating.

**To revive:** re-run end-to-end against SC 4.7, confirm Vision AI still extracts the
expected fields from `r_displayinfo 4` (overlay layout may have shifted), validate
bearing math against in-game distances, update Devlog status, and remove the
"Outdated" tag from `default_config.yaml`.

---

## v1.0.0 — 2026-03-20 — Initial release

### Overview
Mark and navigate to custom waypoints in Star Citizen using r_displayinfo 4 position data.
Vision AI extracts XYZ coordinates, zone, planet, system, and server ID from the live screen.

### Architecture

**Files:**
- `main.py` — SC_NavPoint skill class; 9 @tool methods
- `scanner.py` — mss screen capture, dual-image b64 encoding, LLM message builder, JSON parser
- `database.py` — SQLite CRUD (`navpoints` table); per-server storage
- `navigation.py` — bearing math, format_distance(), turn/elevation instruction generators
- `navpoint_ui/app.py` — FastAPI server (port 7869); REST API for waypoints + nav state
- `navpoint_ui/window.py` — stdlib webbrowser opener
- `navpoint_ui/static/` — SPA: waypoint list (left panel) + navigation compass (right panel)

**Tools (voice commands):**
| Tool | Trigger phrases |
|---|---|
| `enable_displayinfo` | "enable position overlay", "activate r_displayinfo" |
| `disable_displayinfo` | "disable position overlay", "hide debug overlay" |
| `mark_location` | "mark location", "drop waypoint", "save position" |
| `navigate_to` | "navigate to X", "guide me to X" |
| `update_position` | "update position", "refresh bearing", "how far" |
| `stop_navigation` | "stop navigation", "cancel navigation" |
| `show_navpoint_hud` | "show navigation HUD", "open waypoints" |
| `list_navpoints` | "list waypoints", "show saved locations" |
| `delete_navpoint` | "delete waypoint X" |
| `rename_navpoint` | "rename X to Y" |

### Key Technical Decisions

**Dual-image Vision AI extraction**
Send two images per LLM call: full screenshot (context, low detail) + top-right 45%×55%
crop (high detail). The crop isolates r_displayinfo without noise from the rest of the screen.
Crop is upscaled to 900px wide if smaller — improves text legibility on high-res displays.
Pattern proven in old SC_MiningAssistant (solved GPT-4o-mini inconsistency on tiny overlay text).
Learning from SC_Signature_Scanner: crop to the region of interest before OCR.

**Auto-polling loop**
`navigate_to()` calls `_start_nav_polling()` which launches an `asyncio.Task`.
The task loops every N seconds (configurable 1–10s, default 5s):
- Capture screen → extract position → `ui_server.set_position()` → increment `_update_token`
- Frontend polls `/api/nav/state` every 2s → sees token change → recalculates bearing → redraws compass
Stops on: `stop_navigation()`, `delete_navpoint()` (active target), `unload()`, or target cleared.

**Console command automation**
`_send_console_command(cmd)` async helper:
```
tilde → sleep 0.5s → unicode_typewrite(cmd) → enter → sleep 0.2s → tilde
```
Uses `pydirectinput.unicode_typewrite()` (already a Wingman dependency).
All calls via `asyncio.to_thread()` to keep the event loop unblocked.
Star Citizen must be the focused window when called.

**Coordinate system**
SC uses X/Z for horizontal plane, Y for vertical. Bearing: `atan2(dx, dz)`.
Heading offset from current heading for the compass arrow direction.

**Port assignment**
7862=hud, 7863=accountant, 7864-7867=log_reader, 7868=mining, 7869=navpoint

### Configuration
| Property | Default | Description |
|---|---|---|
| `display` | 1 | Monitor to capture (1-based) |
| `poll_interval` | 5 | Auto-tracking refresh interval in seconds (1–10) |

### Known Limitations / Future Work
- Coordinate units from r_displayinfo vary by game version — navigation math works correctly
  as long as both stored and current positions use the same unit (they always will)
- No "arrived" notification when within a threshold distance of the target
- No support for multiple active targets / route waypoints
- SC console key (tilde) is hardcoded — could become a configurable property if needed
