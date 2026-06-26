"""File type detection by magic bytes and MIME-to-extension mapping."""

import unicodedata

from app.models.order import FileKind

# (magic_prefix, mime_type, default_kind)
_SIGNATURES: list[tuple[bytes, str, FileKind]] = [
    (b"\xff\xd8\xff", "image/jpeg", FileKind.photo),
    (b"\x89PNG\r\n\x1a\n", "image/png", FileKind.photo),
    (b"GIF87a", "image/gif", FileKind.photo),
    (b"GIF89a", "image/gif", FileKind.photo),
    (b"%PDF", "application/pdf", FileKind.other),
    # DWG: AutoCAD versions AC10xx – AC27xx
    (b"AC10", "image/vnd.dwg", FileKind.drawing),
    (b"AC12", "image/vnd.dwg", FileKind.drawing),
    (b"AC14", "image/vnd.dwg", FileKind.drawing),
    (b"AC15", "image/vnd.dwg", FileKind.drawing),
    (b"AC18", "image/vnd.dwg", FileKind.drawing),
    (b"AC21", "image/vnd.dwg", FileKind.drawing),
    (b"AC27", "image/vnd.dwg", FileKind.drawing),
]

# Map detected MIME to file extension (used for server-side key)
MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
    "image/vnd.dwg": ".dwg",
    "image/vnd.dxf": ".dxf",
}


class FileTypeError(ValueError):
    pass


def detect_type(data: bytes) -> tuple[str, FileKind]:
    """Return (mime_type, default_kind). Raise FileTypeError if not on whitelist."""
    # WebP: RIFF at byte 0, WEBP at byte 8
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", FileKind.photo

    for sig, mime, kind in _SIGNATURES:
        if data[: len(sig)] == sig:
            return mime, kind

    # DXF: text format, first line is a group code "  0" then "SECTION"
    head = data[:50]
    stripped = head.lstrip(b"\xef\xbb\xbf")  # strip BOM
    if stripped.lstrip()[:1] == b"0" and b"SECTION" in head:
        return "image/vnd.dxf", FileKind.drawing

    raise FileTypeError("File type not allowed")


def sanitize_filename(name: str) -> str:
    """Return a safe display-only filename (not used in filesystem paths)."""
    # Normalise unicode, strip control chars, collapse dots/slashes
    name = unicodedata.normalize("NFKC", name)
    name = "".join(c for c in name if unicodedata.category(c)[0] != "C")
    # Remove path separators to prevent display confusion
    name = name.replace("/", "_").replace("\\", "_")
    return name.strip() or "file"
