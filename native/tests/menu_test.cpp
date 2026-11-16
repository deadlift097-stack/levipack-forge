#include "../src/menu/MenuModel.h"
#include "../src/menu/PackScanner.h"

#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace forge::menu;
namespace fs = std::filesystem;

int main() {
    MenuModel m;
    m.addToggle("a.levipack", "a", true);
    m.addSlider("opacity", "Opacity", 0.f, 1.f, 5.f);  // clamped to 1
    int pressed = 0;
    m.addAction("go", "Go", [&] { ++pressed; });

    assert(m.find("opacity")->value == 1.f);
    assert(m.toggle("a.levipack") && !m.find("a.levipack")->on);
    assert(!m.toggle("opacity") && !m.toggle("missing"));
    assert(m.setSlider("opacity", -3.f) && m.find("opacity")->value == 0.f);
    assert(m.press("go") && pressed == 1 && !m.press("a.levipack"));

    MenuModel n;
    n.addToggle("a.levipack", "a", true);
    n.addSlider("opacity", "Opacity", 0.f, 1.f, 1.f);
    n.applyState(m.serialize());
    assert(!n.find("a.levipack")->on && n.find("opacity")->value == 0.f);

    fs::path dir = fs::temp_directory_path() / "forge_menu_test";
    fs::remove_all(dir);
    fs::create_directories(dir);
    std::ofstream(dir / "x.levipack") << "z";
    std::ofstream(dir / "y.levipack") << "z";
    std::ofstream(dir / "notes.txt") << "z";
    std::ofstream(dir / ".levipack-state") << "y.levipack=off\n";
    auto packs = scanPacks(dir);
    assert(packs.size() == 2 && packs[0].filename == "x.levipack" && packs[0].enabled);
    assert(!packs[1].enabled);
    packs[0].enabled = false;
    assert(writePackState(dir, packs) && !scanPacks(dir)[0].enabled);
    fs::remove_all(dir);
    std::cout << "menu tests passed\n";
}
