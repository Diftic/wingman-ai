"""Migration from version 2.0.0 to 2.1.0.

No config schema changes yet.

This migration is intentionally a no-op and preserves all existing config files.
"""

from services.migrations.base_migration import BaseMigration


class Migration200To210(BaseMigration):
    """Migration from 2.0.0 to 2.1.0."""

    old_version = "2_0_0"
    new_version = "2_1_0"
