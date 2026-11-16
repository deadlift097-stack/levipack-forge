"""Convert a Java mod (.jar) into a levipack-ready native-port workspace.

Honest scope: Java bytecode cannot be translated into a native Android mod, so
this does NOT turn Java logic into C++. What it does automatically:

* reads the jar's metadata (Fabric, Quilt, Forge, NeoForge, legacy Forge, Bukkit)
* generates a levipack ``manifest.json`` from it
* extracts the mod's icon and ``assets/`` into the workspace for re-use
* writes a port report listing what must be re-implemented by hand
* when you pass a compiled native library (``lib``), builds the final .levipack
"""
from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import container
from .javamod import JavaModInfo, extract_member, read_jar

DEFAULT_MC = ["1.21.*"]
ASSET_DIR = "java-assets"


@dataclass
class ConversionResult:
    info: JavaModInfo
    workspace: Path
    manifest: dict
    levipack: Path | None


def build_manifest(info: JavaModInfo, entry: str, minecraft_versions: list[str],
                   icon: str = "") -> dict:
    return {
        "type": "preload-native",
        "name": info.name,
        "author": ", ".join(info.authors) or "unknown",
        "version": info.version,
        "entry": entry,
        "icon": icon,
        "minecraft_versions": minecraft_versions,
    }


def _report(info: JavaModInfo, jar: Path, copied_assets: int) -> str:
    lines = [
        f"# Port report: {info.name}",
        "",
        f"- Source jar: `{jar.name}`",
        f"- Loader detected: **{info.loader}**",
        f"- Mod id: `{info.mod_id}`  |  version: `{info.version}`",
        f"- Authors: {', '.join(info.authors) or 'unknown'}",
        f"- Java classes: {info.class_count} (not convertible; re-implement natively)",
        f"- Mixin configs: {len(info.mixin_configs)}",
        f"- Assets copied to `{ASSET_DIR}/`: {copied_assets}",
        f"- Data files (recipes/tags/loot): {len(info.data_files)}",
        "",
    ]
    if info.description:
        lines += ["## Description", "", info.description, ""]
    if info.entrypoints:
        lines += ["## Java entrypoints to re-implement", ""]
        lines += [f"- `{e}`" for e in info.entrypoints]
        lines.append("")
    if info.mixin_configs:
        lines += ["## Mixins (behaviour patches to re-create as hooks)", ""]
        lines += [f"- `{m}`" for m in info.mixin_configs]
        lines.append("")
    lines += [
        "## Next steps",
        "",
        "1. Re-implement the behaviour as a native mod (see `native/` in levipack-forge).",
        "2. Build it for your ABI to get a `.so`.",
        f"3. `levipack convert {jar.name} --lib path/to/lib{info.mod_id}.so -o <dir>`",
        "   or `levipack pack <workspace> --lib ...` to produce the .levipack.",
        "",
        "Java textures, models, lang and sounds may need format conversion before",
        "Bedrock can use them.",
        "",
    ]
    return "\n".join(lines)


def convert(
    jar: Path | str,
    out_dir: Path | str,
    *,
    minecraft_versions: list[str] | None = None,
    lib: Path | str | None = None,
    copy_assets: bool = True,
) -> ConversionResult:
    jar = Path(jar)
    info = read_jar(jar)
    mc = minecraft_versions or list(DEFAULT_MC)
    workspace = Path(out_dir) / info.mod_id
    workspace.mkdir(parents=True, exist_ok=True)

    icon_name = ""
    if info.icon:
        icon_name = "icon" + (Path(info.icon).suffix or ".png")
        (workspace / icon_name).write_bytes(extract_member(jar, info.icon))

    copied = 0
    if copy_assets and info.asset_files:
        with zipfile.ZipFile(jar) as z:
            for member in info.asset_files:
                target = workspace / ASSET_DIR / container.safe_member_name(member)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(member))
                copied += 1

    entry = Path(lib).name if lib else f"lib{info.mod_id}.so"
    manifest = build_manifest(info, entry, mc, icon_name)
    (workspace / container.MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (workspace / "PORT_REPORT.md").write_text(_report(info, jar, copied), encoding="utf-8")

    pack_path = None
    if lib:
        files: dict[str, Path] = {entry: Path(lib)}
        if icon_name:
            files[icon_name] = workspace / icon_name
        pack_path = container.build(manifest, files, workspace / f"{info.mod_id}.levipack")
    return ConversionResult(info, workspace, manifest, pack_path)
