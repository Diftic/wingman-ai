"""
wow_log_reader - World of Warcraft Log Reader Skill

3-Layer Architecture:
- Layer 3 (combat_log_parser.py): Combat log reading and atomic event extraction
- Layer 2 (session_state.py): State combination and derived events
- Layer 1 (main.py): WingmanAI skill interface

Module names are deliberately unique (e.g. `combat_log_parser` rather than
`parser`) to avoid sys.modules collisions when this skill is loaded alongside
other skills that bare-import their own modules of the same generic names.

Note: Wingman loads main.py directly from custom_skills/ as a standalone
module, so this __init__.py is not evaluated in the live install. It exists
for dev-tree package consumers.
"""

# Version mirrors the WoW patch this skill is qualified against, so dependent
# skills can verify WoW-version compatibility. Within-patch updates append a
# dotted suffix (12.0.5.1, 12.0.5.2, ...).
__version__ = "12.0.5"
__wow_target_version__ = "12.0.5"


__all__ = [
    "__version__",
    "__wow_target_version__",
]
