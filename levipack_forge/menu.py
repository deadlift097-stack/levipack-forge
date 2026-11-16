"""Interactive terminal mod menu for a pack container."""
from __future__ import annotations

from typing import Callable

from . import container
from .registry import PackRegistry

HELP = "Commands: <n> toggle | i <n> inspect | r rescan | q quit"


def render(registry: PackRegistry) -> str:
    entries = registry.scan()
    lines = [f"LeviPack menu - {registry.root}", ""]
    if not entries:
        lines.append("  (no .levipack files here yet)")
    for i, e in enumerate(entries, 1):
        mark = "on " if e.enabled else "off"
        lines.append(f" {i:>2}. [{mark}] {e.title}")
    lines += ["", HELP]
    return "\n".join(lines)


def run_menu(registry: PackRegistry,
             read: Callable[[str], str] = input,
             write: Callable[[str], None] = print) -> None:
    write(render(registry))
    while True:
        try:
            raw = read("> ").strip()
        except EOFError:
            return
        if raw in ("q", "quit", "exit"):
            return
        if raw in ("", "r"):
            write(render(registry))
            continue
        try:
            if raw.startswith("i "):
                entry = registry.resolve(raw[2:].strip())
                info = container.inspect(entry.path)
                write(f"{entry.filename}: {info.manifest['name']} {info.manifest['version']}")
                for m in info.members:
                    write(f"  {m.size:>9}  {m.sha256[:12]}  {m.name}")
            else:
                entry = registry.toggle(raw)
                write(f"{entry.filename} is now {'on' if entry.enabled else 'off'}")
        except (LookupError, container.LevipackError) as exc:
            write(f"! {exc}")
