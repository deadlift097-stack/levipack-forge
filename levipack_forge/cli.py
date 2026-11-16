"""Command line entry point: ``levipack <command>``."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, container, converter
from .menu import render, run_menu
from .registry import PackRegistry


def _parse_lib(spec: str) -> tuple[str, Path]:
    src, sep, dest = spec.partition(":")
    path = Path(src)
    if not path.is_file():
        raise container.LevipackError(f"library not found: {src}")
    return (dest if sep else path.name), path


def cmd_pack(a: argparse.Namespace) -> int:
    src = Path(a.source)
    manifest_path = src / container.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {}
    overrides = {"name": a.name, "author": a.author, "version": a.version,
                 "entry": a.entry, "icon": a.icon}
    manifest.update({k: v for k, v in overrides.items() if v is not None})
    manifest.setdefault("type", "preload-native")
    if a.mc:
        manifest["minecraft_versions"] = a.mc
    files = container.collect_dir(src)
    for spec in a.lib or []:
        dest, path = _parse_lib(spec)
        files[dest] = path
    manifest.setdefault("entry", next((n for n in files if n.endswith(".so")), None))
    out = a.output or f"{manifest.get('name', 'pack').replace(' ', '_')}.levipack"
    container.build(manifest, files, out)
    print(f"created {out}")
    return 0


def cmd_inspect(a: argparse.Namespace) -> int:
    info = container.inspect(a.pack)
    print(json.dumps(info.manifest, indent=2, ensure_ascii=False))
    for m in info.members:
        print(f"{m.size:>10}  {m.sha256[:16]}  {m.name}")
    return 0


def cmd_unpack(a: argparse.Namespace) -> int:
    for p in container.unpack(a.pack, a.dest):
        print(p)
    return 0


def cmd_convert(a: argparse.Namespace) -> int:
    result = converter.convert(a.jar, a.output, minecraft_versions=a.mc or None,
                               lib=a.lib, copy_assets=not a.no_assets)
    i = result.info
    print(f"{i.name} ({i.loader}) -> {result.workspace}")
    print(f"  {i.class_count} Java classes need a native re-implementation; see PORT_REPORT.md")
    print(f"  created {result.levipack}" if result.levipack else
          "  no --lib given: workspace written, levipack not built yet")
    return 0


def cmd_menu(a: argparse.Namespace) -> int:
    reg = PackRegistry(a.dir)
    if a.list:
        print(render(reg))
    elif a.enable or a.disable:
        entry = reg.set_enabled(a.enable or a.disable, bool(a.enable))
        print(f"{entry.filename} is now {'on' if entry.enabled else 'off'}")
    else:
        run_menu(reg)
    return 0


def cmd_add(a: argparse.Namespace) -> int:
    print(f"added {PackRegistry(a.dir).add(a.pack).filename}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="levipack", description="levipack-forge")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("pack", help="build a .levipack from a folder")
    s.add_argument("source")
    s.add_argument("-o", "--output")
    s.add_argument("--lib", action="append", help="SRC[:DEST] native library to include")
    s.add_argument("--name"); s.add_argument("--author"); s.add_argument("--version")
    s.add_argument("--entry"); s.add_argument("--icon")
    s.add_argument("--mc", action="append", help="Minecraft version pattern, repeatable")
    s.set_defaults(fn=cmd_pack)

    s = sub.add_parser("inspect", help="show manifest and file hashes")
    s.add_argument("pack"); s.set_defaults(fn=cmd_inspect)

    s = sub.add_parser("unpack", help="extract a .levipack safely")
    s.add_argument("pack"); s.add_argument("dest"); s.set_defaults(fn=cmd_unpack)

    s = sub.add_parser("convert", help="convert a Java mod .jar into a levipack workspace")
    s.add_argument("jar")
    s.add_argument("-o", "--output", default="out")
    s.add_argument("--lib", help="compiled native .so; builds the final .levipack")
    s.add_argument("--mc", action="append", help="target Minecraft version pattern")
    s.add_argument("--no-assets", action="store_true")
    s.set_defaults(fn=cmd_convert)

    s = sub.add_parser("add", help="copy a .levipack into a pack container folder")
    s.add_argument("pack"); s.add_argument("dir"); s.set_defaults(fn=cmd_add)

    s = sub.add_parser("menu", help="mod menu for a folder of levipacks")
    s.add_argument("dir")
    s.add_argument("--list", action="store_true")
    s.add_argument("--enable", metavar="PACK"); s.add_argument("--disable", metavar="PACK")
    s.set_defaults(fn=cmd_menu)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except (container.LevipackError, LookupError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
