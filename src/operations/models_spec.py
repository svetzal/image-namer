from operations.models import ProposedName


# --- ProposedName.filename_with_fallback ---

def should_use_fallback_extension_when_extension_is_empty():
    p = ProposedName(stem="new-name", extension="")
    assert p.filename_with_fallback(".png") == "new-name.png"


def should_normalize_extension_without_dot_in_fallback_method():
    p = ProposedName(stem="new-name", extension="jpg")
    assert p.filename_with_fallback(".png") == "new-name.jpg"


def should_keep_leading_dot_when_present_in_fallback_method():
    p = ProposedName(stem="new-name", extension=".jpg")
    assert p.filename_with_fallback(".png") == "new-name.jpg"


def should_ignore_fallback_when_extension_is_present():
    p = ProposedName(stem="photo", extension="webp")
    assert p.filename_with_fallback(".jpg") == "photo.webp"


def should_use_fallback_preserving_its_dot():
    p = ProposedName(stem="diagram", extension="")
    assert p.filename_with_fallback(".svg") == "diagram.svg"


# --- ProposedName.filename ---

def should_join_extension_with_dot_when_missing():
    p = ProposedName(stem="cat-photo--sleeping", extension="jpg")
    assert p.filename == "cat-photo--sleeping.jpg"


def should_keep_leading_dot_in_extension_when_present():
    p = ProposedName(stem="cat-photo--sleeping", extension=".png")
    assert p.filename == "cat-photo--sleeping.png"


def should_return_stem_when_extension_empty():
    p = ProposedName(stem="diagram--system-architecture", extension="")
    assert p.filename == "diagram--system-architecture"


def should_handle_unusual_extensions_verbatim():
    p = ProposedName(stem="scan--receipt-2023", extension="tiff")
    assert p.filename == "scan--receipt-2023.tiff"


def should_handle_empty_stem_gracefully():
    p = ProposedName(stem="", extension=".webp")
    assert p.filename == ".webp"
