// Registration. Mirrors the PL_REGISTER_MOD form used by the LeviLauncher mod
// template; verify the exact macro arguments against the template's main.cpp.
#include "mod/ForgeMenuMod.h"

#include <pl/Mod.hpp>

namespace {
forge::ForgeMenuMod& instance() {
    static forge::ForgeMenuMod mod;
    return mod;
}
} // namespace

PL_REGISTER_MOD(forge::ForgeMenuMod, instance());
