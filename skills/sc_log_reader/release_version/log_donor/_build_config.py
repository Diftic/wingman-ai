"""Build-time injected configuration for the log donor.

These values are internal implementation details, not user-facing settings.
They live here (rather than in default_config.yaml custom_properties) so they
do not appear in the skill's settings panel.

The DONOR_WORKER_TOKEN placeholder is replaced by update_release.py from the
DONOR_TOKEN_BUILD env var when building release_version/. In the dev tree the
placeholder remains and any donation attempt will fail with 401 against the
real Worker, which is the correct dev behavior.

A self-hoster forking this skill can edit these constants in their installed
copy to point at a different Worker / state location.
"""

from __future__ import annotations


DONOR_WORKER_URL = "https://sc-log-donate.lars-erik-vaagen.workers.dev"
DONOR_WORKER_TOKEN = "c3a4219631628ee3a6022b7eb945afad"
DONOR_STATE_DB_PATH = "${APPDATA}/Wingman/sc_log_reader/donor_state.sqlite"
