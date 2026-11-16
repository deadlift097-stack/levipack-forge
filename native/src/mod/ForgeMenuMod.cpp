// NOTE: written against the lifecycle shown in the LeviLauncher mod template
// README (NativeMod::current(), getSelf(), load/enable/disable/unload). Compare
// the base-class and registration form with the template's src/mod/MyMod.h and
// src/main.cpp before building; see native/README.md.
#include "ForgeMenuMod.h"

#include "../menu/PackScanner.h"

#include <pl/Mod.hpp>

namespace forge {

ForgeMenuMod::ForgeMenuMod() : mSelf(*ll::mod::NativeMod::current()) {}

bool ForgeMenuMod::load() {
    getSelf().getLogger().debug("forge-menu: loading");
    mPackDir = getSelf().getDataDir() / "packs";
    std::error_code ec;
    std::filesystem::create_directories(mPackDir, ec);
    mHost = createMenuHost(getSelf());
    rebuildMenu();
    return true;
}

void ForgeMenuMod::rebuildMenu() {
    mMenu.clear();
    for (const menu::PackItem& p : menu::scanPacks(mPackDir))
        mMenu.addToggle(p.filename, p.filename, p.enabled);
    mMenu.addAction("rescan", "Rescan packs", [this] { rebuildMenu(); });
}

void ForgeMenuMod::persist() {
    std::vector<menu::PackItem> items;
    for (const menu::Entry& e : mMenu.entries())
        if (e.kind == menu::EntryKind::Toggle) items.push_back({e.id, e.on});
    menu::writePackState(mPackDir, items);
}

bool ForgeMenuMod::enable() {
    getSelf().getLogger().debug("forge-menu: enabling");
    mHost->show(mMenu, [this] { persist(); });
    return true;
}

bool ForgeMenuMod::disable() {
    getSelf().getLogger().debug("forge-menu: disabling");
    persist();
    mHost->hide();
    return true;
}

bool ForgeMenuMod::unload() {
    getSelf().getLogger().debug("forge-menu: unloading");
    mHost.reset();
    return true;
}

} // namespace forge
