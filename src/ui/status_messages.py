"""Centralized user-facing status message strings for the UI layer."""

READY_TO_RENAME = "Ready to rename"
READY_FROM_CACHE = "Ready (from cache)"
READY_LOCKED = "Ready (filename locked by user)"
ALREADY_SUITABLE = "Current name is already suitable"
ALREADY_SUITABLE_CACHED = "Already suitable (cached)"
ALREADY_SUITABLE_LOCKED = "Already suitable (filename locked by user)"
ERROR_DURING_ANALYSIS = "Error during analysis"
LOADING_CACHED_DATA = "Loading cached data..."


def collision_resolved(final_name: str) -> str:
    return f"Collision resolved: {final_name}"


def ready_to_process(count: int) -> str:
    return f"Ready to process {count} images"
