"""Migration from version 2.0.0 to 2.1.0."""

from services.migrations.base_migration import BaseMigration


class Migration200To210(BaseMigration):
    """Migration from 2.0.0 to 2.1.0."""

    old_version = "2_0_0"
    new_version = "2_1_0"

    def migrate_settings(self, old: dict, new: dict) -> dict:
        """Migrate settings.yaml from 2.0.0 to 2.1.0."""
        # Add hardware_scan_performed flag
        if "hardware_scan_performed" not in old:
            # We set it to False so that the hardware scan runs once on next startup
            old["hardware_scan_performed"] = False
            self.log("- added new property: hardware_scan_performed (set to False)")

        return old
