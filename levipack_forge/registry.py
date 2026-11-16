"""A folder of .levipack files plus an on/off state file (the pack 'container')."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import container

STATE_FILE = ".levipack-state"  # lines of `<filename>=on|off`; same format the native menu reads


@dataclass
class PackEntry:
    filename: str
    path: Path
    manifest: dict | None
    enabled: bool
    error: str | None = None

    @property
    def title(self) -> str:
        if self.manifest:
            return f"{self.manifest['name']} {self.manifest['version']} ({self.manifest['author']})"
        return f"{self.filename} [invalid: {self.error}]"


class PackRegistry:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict[str, bool]:
        state: dict[str, bool] = {}
        path = self.root / STATE_FILE
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                key, sep, value = line.partition("=")
                if sep and key.strip():
                    state[key.strip()] = value.strip().lower() != "off"
        return state

    def _save_state(self, state: dict[str, bool]) -> None:
        body = "".join(f"{k}={'on' if v else 'off'}\n" for k, v in sorted(state.items()))
        (self.root / STATE_FILE).write_text(body, encoding="utf-8")

    def scan(self) -> list[PackEntry]:
        state = self._load_state()
        entries = []
        for path in sorted(self.root.glob("*.levipack")):
            try:
                manifest, error = container.read_manifest(path), None
            except container.LevipackError as exc:
                manifest, error = None, str(exc)
            entries.append(PackEntry(path.name, path, manifest,
                                     state.get(path.name, True), error))
        return entries

    def add(self, levipack: Path | str) -> PackEntry:
        src = Path(levipack)
        container.read_manifest(src)
        dest = self.root / src.name
        dest.write_bytes(src.read_bytes())
        return next(e for e in self.scan() if e.filename == dest.name)

    def resolve(self, ref: str) -> PackEntry:
        entries = self.scan()
        if ref.isdigit() and 1 <= int(ref) <= len(entries):
            return entries[int(ref) - 1]
        hits = [e for e in entries if e.filename == ref] or \
               [e for e in entries if e.filename.startswith(ref)]
        if len(hits) != 1:
            raise LookupError(f"no unique pack matches {ref!r}")
        return hits[0]

    def set_enabled(self, ref: str, enabled: bool) -> PackEntry:
        entry = self.resolve(ref)
        state = self._load_state()
        state[entry.filename] = enabled
        self._save_state(state)
        entry.enabled = enabled
        return entry

    def toggle(self, ref: str) -> PackEntry:
        return self.set_enabled(ref, not self.resolve(ref).enabled)
