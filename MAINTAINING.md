# Maintaining this fork (Diftic/wingman-ai)

This fork's `main` = **ShipBit `develop` + one file**:

    skills/sc_log_reader/updates/instructions.json

## ⚠️ The rules file is live
ShipBit's Wingman Core (`services/sc_gamelog/rules.py`, 3.2.5+) downloads it from
`https://raw.githubusercontent.com/Diftic/wingman-ai/main/skills/sc_log_reader/updates/instructions.json`
for **every user**. Every commit to it on `main` is a release.

- Never move, rename or delete it. Older clients have the URL built in.
- Bump `revision` with every change; keep the `maintainer` block.
- Validate the JSON before pushing.

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
