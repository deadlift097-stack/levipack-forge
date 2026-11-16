# levipack-forge

Tools for LeviLauncher `.levipack` containers:

- **Build** a `.levipack` from a folder or from a compiled native mod
- **Container + mod menu**: manage a folder of levipacks and switch each on/off,
  from a terminal menu (`levipack menu`) or from the in-game native mod (`native/`)
- **Convert Java mods**: `levipack convert mod.jar` reads a Java mod's metadata and
  assets and prepares a levipack workspace

Pure Python 3.11+ standard library. No third-party dependencies.

## Install

```
pip install .
```

## Commands

```
levipack pack DIR -o my.levipack --lib build/libmymod.so [--name N --author A --version V --mc "1.21.*"]
levipack inspect my.levipack
levipack unpack my.levipack out/
levipack add my.levipack packs/        # copy into a container folder
levipack menu packs/                    # interactive on/off menu
levipack menu packs/ --list
levipack menu packs/ --disable my.levipack
levipack convert some-mod.jar -o out/ [--lib libport.so] [--mc 1.21.1]
```

## Converting Java mods: what it can and cannot do

A Java mod is bytecode for the Java Edition runtime. A LeviLauncher levipack of
type `preload-native` is a native Android library for Bedrock. There is no
automatic translation between the two, and this tool does not pretend there is.

`levipack convert` does the mechanical part:

1. Detects the loader (Fabric, Quilt, Forge, NeoForge, legacy Forge, Bukkit) and
   reads id, name, version, authors, description and icon.
2. Writes a ready `manifest.json` from that metadata.
3. Copies the icon and the jar's `assets/` folder into the workspace.
4. Writes `PORT_REPORT.md` listing the entrypoints and mixins you need to
   re-implement natively.
5. If you pass `--lib` (your compiled native port), builds the final `.levipack`.

## Container format

A `.levipack` is a ZIP with `manifest.json` at the root and the files it
references. Manifest keys (from the official template): `type`, `name`, `author`,
`version`, `entry`, `icon`, `minecraft_versions`. Archives are built
deterministically (fixed timestamps, sorted members).

**Assumption to check:** I could not read the template's `scripts/package.ps1`,
so file placement inside the archive (library at the root) is inferred from the
manifest. Build one pack with the official template, run `levipack inspect` on it
and compare the layout. Use `--lib SRC:DEST` to place files elsewhere.

## Layout

```
levipack_forge/   Python package (container, javamod, converter, registry, menu, cli)
native/           C++ in-game mod menu (CMake, host tests)
tests/            Python tests
```

## Tests

```
python -m unittest discover -s tests
```

MIT licensed.
