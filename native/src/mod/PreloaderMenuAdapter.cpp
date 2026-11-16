// The ONLY file that touches the launcher's mod-menu API (<pl/ModMenu.hpp>).
//
// I could not read that header while writing this project, so the real-menu
// branch below is intentionally not guessed. Until you map it, the mod falls
// back to LogMenuHost, which compiles everywhere and logs the menu entries.
//
// To wire the real menu: open <pl/ModMenu.hpp> in the preloader-android SDK,
// then implement `PreloaderMenuHost : IMenuHost` that, for every Entry in the
// MenuModel, registers the matching toggle / slider / button with the SDK and
// calls `onChange` from its callbacks.
#include "../menu/MenuHost.h"
#include "ForgeMenuMod.h"

#include <pl/Mod.hpp>

namespace forge {

std::unique_ptr<menu::IMenuHost> createMenuHost(ll::mod::NativeMod& self) {
    return std::make_unique<menu::LogMenuHost>(
        [&self](const std::string& line) { self.getLogger().debug(line); });
}

} // namespace forge
