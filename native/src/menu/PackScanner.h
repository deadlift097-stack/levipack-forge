#pragma once
// Lists *.levipack files in a folder (the pack container) and reads the shared
// `.levipack-state` file written by the `levipack menu` CLI.
#include <filesystem>
#include <string>
#include <vector>

namespace forge::menu {

struct PackItem {
    std::string filename;
    bool enabled = true;
};

std::vector<PackItem> scanPacks(const std::filesystem::path& dir);
bool writePackState(const std::filesystem::path& dir, const std::vector<PackItem>& items);

} // namespace forge::menu
