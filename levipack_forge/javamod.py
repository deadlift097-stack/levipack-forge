"""Read identifying metadata and asset lists out of a Java Minecraft mod (.jar)."""
from __future__ import annotations

import json
import re
import tomllib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class JavaModInfo:
    loader: str
    mod_id: str
    name: str
    version: str
    authors: list[str] = field(default_factory=list)
    description: str = ""
    icon: str | None = None
    entrypoints: list[str] = field(default_factory=list)
    class_count: int = 0
    mixin_configs: list[str] = field(default_factory=list)
    asset_files: list[str] = field(default_factory=list)
    data_files: list[str] = field(default_factory=list)


def slugify(text: str, fallback: str = "mod") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or fallback


def _jar_version(z: zipfile.ZipFile) -> str:
    try:
        text = z.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
    except KeyError:
        return "0.0.0"
    m = re.search(r"^Implementation-Version:\s*(\S+)", text, re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def _clean_version(value, z: zipfile.ZipFile) -> str:
    value = str(value or "").strip()
    return _jar_version(z) if not value or "${" in value else value


def _names(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    out: list[str] = []
    if isinstance(value, dict):
        value = list(value.keys())
    for item in value:
        if isinstance(item, dict):
            item = item.get("name") or item.get("id") or ""
        if str(item).strip():
            out.append(str(item).strip())
    return out


def _flatten_entrypoints(raw) -> list[str]:
    found: list[str] = []
    if isinstance(raw, dict):
        for kind, items in raw.items():
            for item in items if isinstance(items, list) else [items]:
                value = item.get("value") if isinstance(item, dict) else item
                if value:
                    found.append(f"{kind}: {value}")
    elif isinstance(raw, list):
        found.extend(str(x) for x in raw)
    elif raw:
        found.append(str(raw))
    return found


def _icon_from(value) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and value:
        biggest = max(value, key=lambda k: int(k) if str(k).isdigit() else 0)
        return str(value[biggest])
    return None


def _read_json(z: zipfile.ZipFile, name: str):
    return json.loads(z.read(name).decode("utf-8-sig"))


def _fabric(z, jar: Path):
    d = _read_json(z, "fabric.mod.json")
    return JavaModInfo(
        "fabric", str(d.get("id", jar.stem)), str(d.get("name", d.get("id", jar.stem))),
        _clean_version(d.get("version"), z), _names(d.get("authors")),
        str(d.get("description", "")), _icon_from(d.get("icon")),
        _flatten_entrypoints(d.get("entrypoints")),
    )


def _quilt(z, jar: Path):
    q = _read_json(z, "quilt.mod.json").get("quilt_loader", {})
    meta = q.get("metadata", {})
    return JavaModInfo(
        "quilt", str(q.get("id", jar.stem)), str(meta.get("name", q.get("id", jar.stem))),
        _clean_version(q.get("version"), z), _names(meta.get("contributors")),
        str(meta.get("description", "")), _icon_from(meta.get("icon")),
        _flatten_entrypoints(q.get("entrypoints")),
    )


def _forge_toml(z, jar: Path, member: str, loader: str):
    d = tomllib.loads(z.read(member).decode("utf-8-sig"))
    mods = d.get("mods") or [{}]
    m = mods[0]
    authors = _names(m.get("authors") or d.get("authors"))
    return JavaModInfo(
        loader, str(m.get("modId", jar.stem)), str(m.get("displayName", m.get("modId", jar.stem))),
        _clean_version(m.get("version"), z), authors, str(m.get("description", "")).strip(),
        m.get("logoFile") or d.get("logoFile"),
    )


def _mcmod_info(z, jar: Path):
    d = _read_json(z, "mcmod.info")
    if isinstance(d, dict):
        d = d.get("modList", [])
    m = d[0] if d else {}
    return JavaModInfo(
        "forge-legacy", str(m.get("modid", jar.stem)), str(m.get("name", m.get("modid", jar.stem))),
        _clean_version(m.get("version"), z), _names(m.get("authorList") or m.get("authors")),
        str(m.get("description", "")), m.get("logoFile"),
    )


def _plugin_yml(z, jar: Path):
    text = z.read("plugin.yml").decode("utf-8-sig")

    def field_(key: str) -> str:
        m = re.search(rf"^{key}:\s*['\"]?(.+?)['\"]?\s*$", text, re.MULTILINE)
        return m.group(1) if m else ""

    name = field_("name") or jar.stem
    authors = _names(field_("author") or field_("authors").strip("[]"))
    entry = field_("main")
    return JavaModInfo(
        "bukkit", slugify(name), name, _clean_version(field_("version"), z), authors,
        field_("description"), None, [f"main: {entry}"] if entry else [],
    )


def read_jar(jar: Path | str) -> JavaModInfo:
    """Detect the loader, read metadata, and inventory classes and assets."""
    jar = Path(jar)
    try:
        z = zipfile.ZipFile(jar)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"{jar} is not a valid .jar/.zip file") from exc
    with z:
        names = z.namelist()
        info: JavaModInfo | None = None
        try:
            if "fabric.mod.json" in names:
                info = _fabric(z, jar)
            elif "quilt.mod.json" in names:
                info = _quilt(z, jar)
            elif "META-INF/neoforge.mods.toml" in names:
                info = _forge_toml(z, jar, "META-INF/neoforge.mods.toml", "neoforge")
            elif "META-INF/mods.toml" in names:
                info = _forge_toml(z, jar, "META-INF/mods.toml", "forge")
            elif "mcmod.info" in names:
                info = _mcmod_info(z, jar)
            elif "plugin.yml" in names:
                info = _plugin_yml(z, jar)
        except (json.JSONDecodeError, tomllib.TOMLDecodeError, KeyError, IndexError):
            info = None  # malformed metadata: fall through to the generic result
        if info is None:
            info = JavaModInfo("unknown", slugify(jar.stem), jar.stem, _jar_version(z))
        info.mod_id = slugify(info.mod_id, slugify(jar.stem))
        info.class_count = sum(1 for n in names if n.endswith(".class"))
        info.mixin_configs = sorted(n for n in names if n.endswith(".mixins.json"))
        info.asset_files = sorted(n for n in names if n.startswith("assets/") and not n.endswith("/"))
        info.data_files = sorted(n for n in names if n.startswith("data/") and not n.endswith("/"))
        if info.icon and info.icon not in names:
            info.icon = None
    return info


def extract_member(jar: Path | str, member: str) -> bytes:
    with zipfile.ZipFile(jar) as z:
        return z.read(member)
