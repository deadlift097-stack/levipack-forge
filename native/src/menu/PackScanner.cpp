#include "PackScanner.h"

#include <algorithm>
#include <fstream>
#include <map>
#include <system_error>

namespace forge::menu {
namespace fs = std::filesystem;

static const char* kStateFile = ".levipack-state";

std::vector<PackItem> scanPacks(const fs::path& dir) {
    std::map<std::string, bool> state;
    {
        std::ifstream in(dir / kStateFile);
        std::string line;
        while (std::getline(in, line)) {
            auto eq = line.find('=');
            if (eq == std::string::npos) continue;
            std::string v = line.substr(eq + 1);
            while (!v.empty() && (v.back() == '\r' || v.back() == ' ')) v.pop_back();
            state[line.substr(0, eq)] = (v != "off");
        }
    }
    std::vector<PackItem> items;
    std::error_code ec;
    for (fs::directory_iterator it(dir, ec), end; !ec && it != end; it.increment(ec)) {
        if (!it->is_regular_file(ec) || it->path().extension() != ".levipack") continue;
        PackItem p;
        p.filename = it->path().filename().string();
        auto s = state.find(p.filename);
        p.enabled = (s == state.end()) ? true : s->second;
        items.push_back(std::move(p));
    }
    std::sort(items.begin(), items.end(),
              [](const PackItem& a, const PackItem& b) { return a.filename < b.filename; });
    return items;
}

bool writePackState(const fs::path& dir, const std::vector<PackItem>& items) {
    std::ofstream out(dir / kStateFile, std::ios::trunc);
    if (!out) return false;
    for (const PackItem& p : items) out << p.filename << '=' << (p.enabled ? "on" : "off") << '\n';
    return static_cast<bool>(out);
}

} // namespace forge::menu
