"""Single authoritative presentation table for RenameStatus string labels."""

from pydantic import BaseModel

from operations.models import RenameStatus


class RenameStatusPresentation(BaseModel, frozen=True):
    cli_label: str
    table_label: str


RENAME_STATUS_PRESENTATION: dict[RenameStatus, RenameStatusPresentation] = {
    RenameStatus.RENAMED: RenameStatusPresentation(cli_label="proposed", table_label="✓ rename"),
    RenameStatus.UNCHANGED: RenameStatusPresentation(cli_label="unchanged", table_label="= unchanged"),
    RenameStatus.COLLISION: RenameStatusPresentation(cli_label="collision-resolved", table_label="⚠ collision"),
    RenameStatus.ERROR: RenameStatusPresentation(cli_label="error", table_label="✗ error"),
}
