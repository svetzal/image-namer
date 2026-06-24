"""Single authoritative UI projection table for RenameStatus terminal outcomes."""

from typing import Callable

from pydantic import BaseModel, ConfigDict

from operations.models import RenameStatus
from ui import status_messages as msg
from ui.models.ui_models import ItemStatus


class RenameStatusUI(BaseModel):
    """UI projection for a single RenameStatus terminal outcome."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    ui_status: ItemStatus
    fresh_message: Callable[[str], str]
    cached_message: str
    locked_message: str
    stat_field: str


RENAME_STATUS_UI: dict[RenameStatus, RenameStatusUI] = {
    RenameStatus.RENAMED: RenameStatusUI(
        ui_status=ItemStatus.READY,
        fresh_message=lambda _f: msg.READY_TO_RENAME,
        cached_message=msg.READY_FROM_CACHE,
        locked_message=msg.READY_LOCKED,
        stat_field="renamed",
    ),
    RenameStatus.UNCHANGED: RenameStatusUI(
        ui_status=ItemStatus.UNCHANGED,
        fresh_message=lambda _f: msg.ALREADY_SUITABLE,
        cached_message=msg.ALREADY_SUITABLE_CACHED,
        locked_message=msg.ALREADY_SUITABLE_LOCKED,
        stat_field="unchanged",
    ),
    RenameStatus.COLLISION: RenameStatusUI(
        ui_status=ItemStatus.COLLISION,
        fresh_message=msg.collision_resolved,
        cached_message=msg.READY_FROM_CACHE,
        locked_message=msg.READY_LOCKED,
        stat_field="renamed",
    ),
    RenameStatus.ERROR: RenameStatusUI(
        ui_status=ItemStatus.ERROR,
        fresh_message=lambda _f: msg.ERROR_DURING_ANALYSIS,
        cached_message=msg.ERROR_DURING_ANALYSIS,
        locked_message=msg.ERROR_DURING_ANALYSIS,
        stat_field="errors",
    ),
}
