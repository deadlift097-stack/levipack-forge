"""Reading and writing .levipack containers.

A .levipack is a ZIP archive with a ``manifest.json`` at its root plus the
files that manifest refers to (for native mods: the ``entry`` shared library).
The manifest keys follow the LeviLauncher Android mod template.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Union

MANIFEST_NAME = "manifest.json"
REQUIRED_KEYS = ("type", "name", "author", "version", "entry", "minecraft_versions")
# Fixed timestamp so identical inputs always produce byte-identical archives.
_FIXED_TIME = (2020, 1, 1, 0, 0, 0)

Payload = Union[bytes, str, Path]


class LevipackError(ValueError):
    """Raised for malformed manifests, unsafe paths or unreadable containers."""


@dataclass(frozen=True)
class MemberInfo:
    name: str
    size: int
    sha256: str


@dataclass(frozen=True)
class PackInfo:
    manifest: dict
    members: tuple[MemberInfo, ...]


def validate_manifest(manifest: Mapping) -> dict:
    missing = [k for k in REQUIRED_KEYS if k not in manifest]
    if missing:
        raise LevipackError(f"manifest is missing keys: {', '.join(missing)}")
    for key in ("type", "name", "author", "version", "entry"):
        if not isinstance(manifest[key], str) or not manifest[key].strip():
            raise LevipackError(f"manifest key {key!r} must be a non-empty string")
    versions = manifest["minecraft_versions"]
    if not isinstance(versions, list) or not versions or not all(
        isinstance(v, str) and v for v in versions
    ):
        raise LevipackError("minecraft_versions must be a non-empty list of strings")
    return dict(manifest)


def safe_member_name(name: str) -> str:
    """Normalise an archive path and reject anything that could escape a folder."""
    cleaned = name.replace("\\", "/").lstrip("/")
    parts = PurePosixPath(cleaned).parts
    if not parts or any(p in ("..", "") for p in parts) or ":" in parts[0]:
        raise LevipackError(f"unsafe archive path: {name!r}")
    return "/".join(parts)


def _as_bytes(payload: Payload) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return Path(payload).read_bytes()


def _write(z: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=_FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, data)


def build(
    manifest: Mapping,
    files: Mapping[str, Payload],
    out: Path | str,
    *,
    require_entry: bool = True,
) -> Path:
    """Create a .levipack at ``out`` from a manifest and a {member: payload} map."""
    manifest = validate_manifest(manifest)
    members = {safe_member_name(k): v for k, v in files.items()}
    if MANIFEST_NAME in members:
        raise LevipackError("manifest.json is generated; do not pass it as a file")
    if require_entry and safe_member_name(manifest["entry"]) not in members:
        raise LevipackError(f"entry file {manifest['entry']!r} was not supplied")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        _write(z, MANIFEST_NAME, text.encode("utf-8"))
        for name in sorted(members):
            _write(z, name, _as_bytes(members[name]))
    return out


def collect_dir(root: Path | str) -> dict[str, Path]:
    """Map every file under ``root`` (except manifest.json) to its member name."""
    root = Path(root)
    found: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if rel != MANIFEST_NAME:
                found[rel] = path
    return found


def read_manifest(path: Path | str) -> dict:
    try:
        with zipfile.ZipFile(path) as z:
            return validate_manifest(json.loads(z.read(MANIFEST_NAME)))
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, OSError) as exc:
        raise LevipackError(f"{path}: not a valid levipack ({exc})") from exc


def inspect(path: Path | str) -> PackInfo:
    manifest = read_manifest(path)
    members = []
    with zipfile.ZipFile(path) as z:
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            if info.is_dir():
                continue
            digest = hashlib.sha256(z.read(info)).hexdigest()
            members.append(MemberInfo(info.filename, info.file_size, digest))
    return PackInfo(manifest, tuple(members))


def unpack(path: Path | str, dest: Path | str) -> list[Path]:
    """Extract a levipack, refusing any member that would land outside ``dest``."""
    dest = Path(dest).resolve()
    written: list[Path] = []
    read_manifest(path)
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            target = (dest / safe_member_name(info.filename)).resolve()
            if dest not in target.parents:
                raise LevipackError(f"unsafe archive path: {info.filename!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(info))
            written.append(target)
    return written
