WOW LOG READER v12.0.5  -  Community Tester Guide

Thanks for testing! This guide gets you installed and explains what to look
for and how to report back.


WHAT THIS IS

wow_log_reader is a Wingman AI skill that watches World of Warcraft's combat
log in real time and feeds events to your Wingman: encounters (boss pulls and
ends), zone changes, map changes, and player deaths.

This is the Phase 1 release. It uses the combat log only. The Phase 2 WoW
addon (for loot, quests, currency, and gear) is not included yet.

This build is qualified against World of Warcraft 12.0.5 (combat log version
22). If you are on a newer WoW patch, expect possible breakage and please
report it.


INSTALL

Requirements:
- Wingman AI desktop app, already installed
- World of Warcraft (retail), with combat logging enabled in-game
- Windows

Steps:

1. Unzip the package somewhere convenient (Desktop is fine).
2. Open the unzipped wow_log_reader folder.
3. Double-click install.bat. It copies the skill into:
   %AppData%\ShipBit\WingmanAI\custom_skills\wow_log_reader\
4. You should see "Install complete!" followed by "Press any key to continue..."
5. Restart Wingman AI.


ENABLE COMBAT LOGGING IN WOW

The skill cannot do anything until WoW is writing the combat log. To enable
it inside the game, type:

   /combatlog

Combat logging stays on until you toggle it off (or until you log out). The
game writes to:

   <your WoW install>\_retail_\Logs\WoWCombatLog-MMDDYY_HHMMSS.txt

A new file is created each time you enable combat logging.


VERIFY THE INSTALL WORKED

In your Wingman AI logs (or the console where Wingman runs), look for:

   WoW_LogReader: tailing combat log in <path>\Logs

If you see that line and the path matches your WoW install, you are good.

In the Wingman AI UI, open your wingman's settings, go to Skills, and confirm
"WoW Log Reader" is listed and enabled.


CONFIGURING THE SKILL

In skill settings:

- WoW Install Path: leave empty for auto-detect, or set explicitly to your
  WoW install root (the folder that contains _retail_, e.g.
  D:/Games/World of Warcraft). The skill resolves _retail_/Logs from there.

Restart the skill after changing the path.


WHAT TO TEST

You do not need to follow a script: just play normally and watch for these
behaviours.

- Skill loads cleanly: no Python tracebacks, no error dialogs.
- After a boss kill, ask your Wingman about the recent encounter: it should
  tell you the boss name, fight length, and result.
- After changing zones, ask "where am I?": it should answer with the zone
  you are currently in.
- After dying, ask about recent deaths: the death should be listed with
  approximate time and location.
- Stability over a long session: run for an hour or more; memory should stay
  flat, no slowdowns.
- Game restart resilience: log out of WoW, log back in (which creates a new
  combat log file), confirm the skill picks up the new file without needing
  Wingman to restart.

Voice queries to try:

- "Where am I in WoW?"
- "Tell me about my last boss fight"
- "How did the dungeon go?"
- "Did I die recently?"
- "What zone am I in?"


REPORTING BACK

For every issue, please include:

1. WoW version: retail / beta / PTR, and the build number if you know it.
2. OS and hardware: Windows version, GPU, RAM (rough is fine).
3. What you were doing: "I had just killed the second boss in Den of
   Nalorakk", etc.
4. What you expected vs what happened.
5. The combat log file if possible. Located at:
   <your WoW install>\_retail_\Logs\WoWCombatLog-MMDDYY_HHMMSS.txt
   These can be large (tens of MB); zip before sending.
6. Wingman AI log or console output if there is a Python traceback.

Severity:

- Critical: Wingman crashes, skill will not load, blocks other skills, any
  data loss.
- Major: Events missed, wrong data, performance issues.
- Minor: Cosmetic, edge cases, nice-to-haves.

Where to send it:

   [Tester feedback channel: fill in Discord link / email / Google Form]


KNOWN LIMITATIONS (Phase 1)

- Combat log only. No loot, quests, currencies, gear, talents, or
  reputation; those need the Phase 2 WoW addon.
- The skill does not know your character's name yet. The combat log does not
  reveal it through the Phase 1 events. The Phase 2 addon will fill this in.
- WoW only writes the combat log when you have enabled it via /combatlog. If
  the skill returns empty data, the most likely cause is that combat logging
  is not enabled in-game.
- Only events written to the combat log after combat logging starts are
  detected. Events from before /combatlog will not backfill.


THANKS

Feedback from this round goes directly into the regression test corpus and
the next patch (likely 12.0.5.1 if any critical or major issues land, or
12.0.6 when Blizzard ships the next WoW patch).

- Mallachi
