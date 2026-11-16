import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from levipack_forge import container, converter
from levipack_forge.cli import main
from levipack_forge.javamod import read_jar
from levipack_forge.menu import run_menu
from levipack_forge.registry import PackRegistry

MANIFEST = {"type": "preload-native", "name": "Demo", "author": "me", "version": "1.0.0",
            "entry": "libdemo.so", "minecraft_versions": ["1.21.*"]}


def make_jar(path: Path, files: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        for k, v in files.items():
            z.writestr(k, v)
    return path


FABRIC = json.dumps({"id": "cool-mod", "name": "Cool Mod", "version": "2.3.1",
                     "authors": ["Ann", {"name": "Bob"}], "icon": "assets/cool/icon.png",
                     "entrypoints": {"main": ["com.cool.Main"]}}).encode()


class ContainerTests(unittest.TestCase):
    def test_roundtrip_and_determinism(self):
        with tempfile.TemporaryDirectory() as t:
            a = container.build(MANIFEST, {"libdemo.so": b"ELF"}, Path(t) / "a.levipack")
            b = container.build(MANIFEST, {"libdemo.so": b"ELF"}, Path(t) / "b.levipack")
            self.assertEqual(a.read_bytes(), b.read_bytes())
            info = container.inspect(a)
            self.assertEqual(info.manifest["name"], "Demo")
            self.assertEqual([m.name for m in info.members], ["libdemo.so", "manifest.json"])

    def test_missing_entry_and_bad_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(container.LevipackError):
                container.build(MANIFEST, {}, Path(t) / "x.levipack")
            with self.assertRaises(container.LevipackError):
                container.validate_manifest({"name": "x"})

    def test_unsafe_paths_rejected(self):
        for bad in ("../evil", "a/../../b", "/abs/../x", "C:/x"):
            with self.assertRaises(container.LevipackError):
                container.safe_member_name(bad)

    def test_unpack_blocks_traversal(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "evil.levipack"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("manifest.json", json.dumps(MANIFEST))
                z.writestr("../escape.txt", "x")
            with self.assertRaises(container.LevipackError):
                container.unpack(p, Path(t) / "dest")
            self.assertFalse((Path(t) / "escape.txt").exists())


class JavaModTests(unittest.TestCase):
    def test_fabric(self):
        with tempfile.TemporaryDirectory() as t:
            jar = make_jar(Path(t) / "cool.jar", {
                "fabric.mod.json": FABRIC, "A.class": b"x", "cool.mixins.json": b"{}",
                "assets/cool/icon.png": b"PNG", "assets/cool/lang/en_us.json": b"{}"})
            i = read_jar(jar)
            self.assertEqual((i.loader, i.mod_id, i.version), ("fabric", "cool_mod", "2.3.1"))
            self.assertEqual(i.authors, ["Ann", "Bob"])
            self.assertEqual(i.icon, "assets/cool/icon.png")
            self.assertEqual((i.class_count, len(i.asset_files)), (1, 2))

    def test_forge_placeholder_version_uses_manifest_mf(self):
        toml = b'[[mods]]\nmodId="fm"\ndisplayName="Forge Mod"\nversion="${file.jarVersion}"\nauthors="X, Y"\n'
        with tempfile.TemporaryDirectory() as t:
            jar = make_jar(Path(t) / "f.jar", {
                "META-INF/mods.toml": toml,
                "META-INF/MANIFEST.MF": b"Implementation-Version: 9.9\n"})
            i = read_jar(jar)
            self.assertEqual((i.loader, i.version, i.authors), ("forge", "9.9", ["X", "Y"]))

    def test_unknown_jar_falls_back(self):
        with tempfile.TemporaryDirectory() as t:
            i = read_jar(make_jar(Path(t) / "Weird Mod.jar", {"B.class": b"x"}))
            self.assertEqual((i.loader, i.mod_id), ("unknown", "weird_mod"))

    def test_not_a_zip(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "no.jar"
            p.write_bytes(b"nope")
            with self.assertRaises(ValueError):
                read_jar(p)


class ConvertTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.jar = make_jar(self.dir / "cool.jar", {
            "fabric.mod.json": FABRIC, "A.class": b"x",
            "assets/cool/icon.png": b"PNG", "assets/cool/lang/en_us.json": b"{}"})

    def tearDown(self):
        self.tmp.cleanup()

    def test_workspace_without_lib(self):
        r = converter.convert(self.jar, self.dir / "out")
        self.assertIsNone(r.levipack)
        self.assertEqual(r.manifest["entry"], "libcool_mod.so")
        self.assertTrue((r.workspace / "PORT_REPORT.md").exists())
        self.assertTrue((r.workspace / "java-assets/assets/cool/lang/en_us.json").exists())

    def test_final_levipack_with_lib(self):
        lib = self.dir / "libcool.so"
        lib.write_bytes(b"ELF")
        r = converter.convert(self.jar, self.dir / "out", lib=lib, minecraft_versions=["1.21.1"])
        info = container.inspect(r.levipack)
        self.assertEqual(info.manifest["entry"], "libcool.so")
        self.assertEqual(info.manifest["minecraft_versions"], ["1.21.1"])
        self.assertEqual(info.manifest["icon"], "icon.png")
        self.assertIn("libcool.so", [m.name for m in info.members])

    def test_cli_convert(self):
        rc = main(["convert", str(self.jar), "-o", str(self.dir / "o2")])
        self.assertEqual(rc, 0)
        self.assertEqual(main(["convert", str(self.dir / "missing.jar")]), 1)


class RegistryMenuTests(unittest.TestCase):
    def test_toggle_state_and_menu(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "packs"
            src = container.build(MANIFEST, {"libdemo.so": b"E"}, Path(t) / "demo.levipack")
            reg = PackRegistry(root)
            reg.add(src)
            (root / "broken.levipack").write_bytes(b"junk")
            names = [e.filename for e in reg.scan()]
            self.assertEqual(names, ["broken.levipack", "demo.levipack"])
            self.assertTrue(reg.scan()[1].enabled)
            reg.toggle("demo")
            self.assertFalse(reg.scan()[1].enabled)
            self.assertEqual((root / ".levipack-state").read_text(), "demo.levipack=off\n")
            out, cmds = [], iter(["2", "i 2", "9", "q"])
            run_menu(reg, lambda _p: next(cmds), out.append)
            joined = "\n".join(out)
            self.assertIn("demo.levipack is now on", joined)
            self.assertIn("manifest.json", joined)
            self.assertIn("! no unique pack", joined)

    def test_cli_pack_from_dir(self):
        with tempfile.TemporaryDirectory() as t:
            src = Path(t) / "src"
            src.mkdir()
            (src / "libx.so").write_bytes(b"E")
            out = Path(t) / "x.levipack"
            rc = main(["pack", str(src), "-o", str(out), "--name", "X", "--author", "a",
                       "--version", "0.1", "--mc", "1.21.*"])
            self.assertEqual(rc, 0)
            self.assertEqual(container.read_manifest(out)["entry"], "libx.so")


if __name__ == "__main__":
    unittest.main()
