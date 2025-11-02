from operations.models import ProposedName


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
