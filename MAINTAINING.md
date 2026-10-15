# Maintaining this fork (Diftic/wingman-ai)

This fork's `main` = **ShipBit `develop` + two files**:

    skills/sc_log_reader/updates/instructions.json
    skills/sc_log_reader/updates/item_names.json

## ⚠️ The rules file is live
ShipBit's Wingman Core (`services/sc_gamelog/rules.py`, 3.2.5+) downloads it from
`https://raw.githubusercontent.com/Diftic/wingman-ai/main/skills/sc_log_reader/updates/instructions.json`
for **every user**. Every commit to it on `main` is a release.

- Never move, rename or delete it. Older clients have the URL built in.
- Bump `revision` with every change; keep the `maintainer` block.
- Validate the JSON before pushing.

## ⚠️ The item-name table is live (3.2.9+)
Core (`services/sc_gamelog/item_names.py`) downloads
`https://raw.githubusercontent.com/Diftic/wingman-ai/main/skills/sc_log_reader/updates/item_names.json`
alongside the rules and keeps the higher revision of it and the table it ships.
It turns the class names shops log (`SHLD_BEHR_S03_7CA_SCItem`) into in-game
names (`7CA 'Nargun'`). Older Cores never fetch it.

- Rebuild it per game patch with `build_item_names.py` (Log Reader R&D repo,
  `sc_log_reader/tools/`): extract `english/global.ini` from `Data.p4k` with unp4k,
  pass `--sc-bridge` for names by GUID, and **a `--revision` higher than the
  published one**, or Core keeps the old table.
- Fixes for how shops write class names go in its `strip_suffixes`, not in code.
- Never move or rename it; at most 4 MB.

## Where everything else lives
| Thing | Repo |
|---|---|
| Reader code, Accountant | ShipBit `wingman-ai` `develop` (`services/sc_gamelog/`, `skills/sc_accountant/`) — owned by ShipBit, changes only via PR **with their agreement** |
| NavPoint, Factory Assistant, Log Reader R&D, other own skills | `Diftic/wingman-skills` (private) |
| Old states of this fork | tags `archive/*` |

## Sync with ShipBit (read-only on their side)
    git fetch upstream
    git switch main
    git rebase upstream/develop      # keeps the rules-file commit on top
    git push --force-with-lease origin main

`upstream` push is disabled locally on purpose.
