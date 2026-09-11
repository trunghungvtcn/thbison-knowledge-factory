"""Narrow compatibility boundary for immutable legacy path manifests."""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import unicodedata


class LegacyManifestPathError(ValueError):
    """A legacy locator cannot be mapped safely into its authorized root."""


def _parts(locator: str, dialect: str) -> tuple[str, ...]:
    if not isinstance(locator, str) or not locator or any(ord(ch) < 32 for ch in locator):
        raise LegacyManifestPathError("INVALID_PATH")
    if dialect == "windows-relative-v1":
        value = PureWindowsPath(locator)
        if value.is_absolute() or value.drive or value.root or locator.startswith(("/", "\\")):
            raise LegacyManifestPathError("ABSOLUTE_PATH")
        parts = value.parts
    elif dialect == "posix-relative-v1":
        if "\\" in locator:
            raise LegacyManifestPathError("SEPARATOR_ALIAS")
        value = PurePosixPath(locator)
        if value.is_absolute() or locator.startswith("/"):
            raise LegacyManifestPathError("ABSOLUTE_PATH")
        parts = value.parts
    else:
        raise LegacyManifestPathError("UNSUPPORTED_PATH_DIALECT")
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise LegacyManifestPathError("PATH_TRAVERSAL")
    if any(":" in part for part in parts):
        raise LegacyManifestPathError("WINDOWS_DEVICE_OR_ADS")
    return tuple(parts)


def resolve_manifest_entries(root: Path, entries: dict[str, str], *, dialect: str) -> dict[str, Path]:
    """Resolve every entry before any caller reads bytes.

    Case and Unicode aliases are rejected up front so a manifest cannot silently
    target the same file differently on Windows and POSIX.
    """
    if not isinstance(entries, dict):
        raise LegacyManifestPathError("MANIFEST_TYPE")
    authorized = Path(root).resolve()
    resolved: dict[str, Path] = {}
    identities: dict[str, str] = {}
    for locator in entries:
        parts = _parts(locator, dialect)
        identity = "/".join(unicodedata.normalize("NFC", part).casefold() for part in parts)
        if identity in identities:
            raise LegacyManifestPathError(f"PATH_COLLISION:{identities[identity]}:{locator}")
        candidate = authorized.joinpath(*parts).resolve()
        try:
            contained = os.path.commonpath((str(authorized), str(candidate))) == str(authorized)
        except ValueError:
            contained = False
        if not contained:
            raise LegacyManifestPathError(f"PATH_TRAVERSAL:{locator}")
        identities[identity] = locator
        resolved[locator] = candidate
    return resolved
