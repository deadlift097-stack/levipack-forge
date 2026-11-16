#pragma once
#include "../menu/MenuHost.h"
#include "../menu/MenuModel.h"

#include <filesystem>
#include <memory>

namespace ll::mod { class NativeMod; }

namespace forge {

std::unique_ptr<menu::IMenuHost> createMenuHost(ll::mod::NativeMod& self);

// Native mod: scans a folder of .levipack files and exposes an in-game mod menu
// to turn each one on/off. State is shared with the `levipack menu` CLI.
class ForgeMenuMod {
public:
    ForgeMenuMod();
    bool load();
    bool enable();
    bool disable();
    bool unload();
    ll::mod::NativeMod& getSelf() { return mSelf; }

private:
    void rebuildMenu();
    void persist();

    ll::mod::NativeMod&               mSelf;
    menu::MenuModel                   mMenu;
    std::unique_ptr<menu::IMenuHost>  mHost;
    std::filesystem::path             mPackDir;
};

} // namespace forge
