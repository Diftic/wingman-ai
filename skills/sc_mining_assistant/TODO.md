# TODO — SC Mining Assistant

## Next Session

- [ ] Test with multiple rock types (not just Iron) to validate Vision AI extraction
- [ ] Test at different resolutions (1080p, 1440p) — 5120x1440 validated
- [ ] Test folder watcher auto-scan pipeline (currently only upload tested)
- [ ] Verify edit modal Save button works end-to-end (PUT endpoint fixed)
- [ ] Fix Mining Interface UI issues (noted but deferred)

## Known Issues

- [ ] `submitted_by` uses `self.settings.user_name` — requires user to be logged into Wingman

## Phase 1 (MVP) — In Progress

- [x] Screenshot folder watcher (watchdog, OS-native events)
- [x] Screenshot load + hash + base64 encode (scanner.py)
- [x] SQLite database with schema migrations (database.py)
- [x] Database lock fix (connection reuse in insert_scan)
- [x] Mining Interface (FastAPI + SPA on port 7868)
- [x] Manual scan upload via Mining Interface (POST /api/scan)
- [x] Scan deletion via Mining Interface (DELETE /api/scans/{id})
- [x] Voice tools: capture_mining_scan, get_recent_scans, get_location_composition, show_mining_interface
- [x] Auto-activate on wingman boot
- [x] Submitted by = logged-in Wingman account name
- [x] Vision AI replaces local OCR (v1.0.0) — uses wingman's configured LLM provider
- [x] Validate full pipeline end-to-end with Vision AI (v1.1.0 — GPT-4o-mini, 5120x1440)
- [x] Full-resolution screenshot (no downscaling) — native JPEG passthrough
- [x] Server string extraction — full server ID preserved, version parsed in code
- [x] `resistance_modified` / `instability_modified` color detection — confirmed working
- [x] Null sanitization — handles Vision AI returning "null" strings
- [x] Upload processes immediately via async callback (not queued)
- [x] Wingman log output for all pipeline stages
- [x] Dual-image extraction (v1.2.0) — full screenshot + r_displayinfo crop for consistent reads
- [x] Bloom warning in prompt — covers all fields across both images
- [x] Database stored in AppData generated_files (matches SC_Accountant/SC_LogReader)
- [x] Skill class renamed SC_MiningAssistant (matches naming convention)
- [x] Scan edit modal (v1.3.0) — click scan row to edit all fields in popup
- [x] Screenshot link in edit modal — view original screenshot in new tab
- [x] Uploaded screenshots saved permanently to generated_files/screenshots/
- [x] PUT /api/scans/{id} endpoint for updating scan data
- [x] GET /api/scans/{id}/screenshot endpoint for serving screenshot images
- [x] Inert Materials auto-calculated (100% - sum of other minerals)
- [x] Two-column edit layout: scan data left, metadata right

## Phase 2 (Deferred)

- [ ] MCP community server sync
- [ ] Refinery data tools (port from Regolith skill)
- [ ] Best location / best refinery finders
- [ ] UEX price integration (reuse UEXCorp skill)

## Phase 3 — Server-Side Vision AI (Future)

- [ ] **Server-side Vision AI processing**: Move the Vision AI extraction from
  client-side to a central server. The skill becomes a passive background script
  that uploads screenshots to a web folder. The server runs Vision AI analysis
  asynchronously, leveraging OpenAI's batch/non-instant discount (~50% cost
  reduction). With lower cost per scan, larger models become viable (e.g.
  GPT-4.1-mini batch at ~$23/month for 1k scans/day), improving accuracy enough
  to eliminate the need for manual scan editing. The Mining Interface becomes a
  public website synced from the server database, enabling community-wide scan
  aggregation. Requires a webdev lead for production-grade auth, scalability,
  reliability, and frontend polish for thousands of users.

### Cost Analysis (2026-03-15)
```
Hosting: Hetzner CX22 — $5/month (2 vCPU, 4GB RAM, 40GB SSD + 100GB volume)
Resolution split: 15% ultrawide (5120x1440), 85% standard (2560x1440)
Avg tokens per scan: ~2,510 input, ~350 output (dual-image)

Model               Real-time/mo   Batch/mo (50% off)
GPT-4.1-nano         $11.74         $5.87
GPT-4o-mini          $17.60         $8.80
GPT-4.1-mini         $46.94         $23.47
GPT-4.1             $234.72        $117.36
GPT-4o              $293.40        $146.70

Recommended: GPT-4.1-mini batch — $23/mo, likely eliminates manual editing
Total server cost: ~$30-35/month for 1,000 scans/day
```

## Verified Extraction (v1.2.0, GPT-4o-mini, 5120x1440)

Consistent 100% accuracy with dual-image approach (full + r_displayinfo crop):
```
server_string:        ptu-use1b-sc-alpha-470-11445650-11383139-game29  ✓
game_version:         4.7.0 (parsed from alpha-470)                    ✓
server_timestamp:     Fri Mar 13 21:01:08 2026                         ✓
player_location:      NyxSolarSystem                                   ✓
ship_name:            MISC Prospector                                  ✓
rock_type:            Iron (ORE)                                       ✓
mass:                 36674                                            ✓
resistance:           0, modified=false                                ✓
instability:          27.99, modified=true                             ✓
difficulty:           Impossible                                       ✓
composition_scu:      44.37                                            ✓
minerals:             Iron 69.6% Q440, Inert Materials 30.4% Q0       ✓
```

## Abandoned Approaches

### Local OCR Pipeline (v0.2.0–v0.7.0, replaced in v1.0.0)
- EasyOCR → Windows OCR (winocr) → Vision AI
- EasyOCR: slow (~10s), missed % signs, GPU-heavy
- Windows OCR: fast (0.23s) but fragile — needed bloom subtraction, HUD prefix
  stripping, line reconstruction, fuzzy matching, manufacturer tolerance, location
  normalization. Every resolution/lighting change broke something.
- Vision AI: uses the wingman's configured LLM — handles all resolutions, lighting,
  and HUD overlap natively. No local preprocessing needed.

### Single-image Vision AI (v1.0.0–v1.1.0, replaced in v1.2.0)
- GPT-4o-mini inconsistent reading tiny r_displayinfo text from full 5120x1440 image
- Sometimes extracted all fields, sometimes returned null for location/ship/timestamp
- Resistance fluctuated (0, 2, 8, 28) due to bloom artifacts
- Fix: dual-image approach — cropped r_displayinfo sent as second image

### Qwen2-VL Vision Model (abandoned)
- Cloned skill as `sc_qwen_scan`, replaced EasyOCR with Qwen2-VL-2B-Instruct
- Problem: SC uses 10-11GB of 12GB VRAM — no room for a 2B VLM on GPU
- CPU inference too slow (~30-60s per crop)
- Conclusion: Local VLMs not viable for SC players' hardware constraints
