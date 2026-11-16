#pragma once
// Pure C++17 menu model: no SDK dependency, so it is unit-tested on the host.
#include <functional>
#include <string>
#include <vector>

namespace forge::menu {

enum class EntryKind { Toggle, Slider, Action };

struct Entry {
    std::string id;
    std::string label;
    EntryKind kind = EntryKind::Toggle;
    bool on = false;
    float value = 0.f, min = 0.f, max = 1.f;
    std::function<void()> action;  // Action entries only
};

class MenuModel {
public:
    Entry& addToggle(std::string id, std::string label, bool initial);
    Entry& addSlider(std::string id, std::string label, float min, float max, float initial);
    Entry& addAction(std::string id, std::string label, std::function<void()> fn);

    Entry*       find(const std::string& id);
    const std::vector<Entry>& entries() const { return mEntries; }
    void clear() { mEntries.clear(); }

    bool toggle(const std::string& id);                 // false if id is not a toggle
    bool setSlider(const std::string& id, float value); // clamps into [min, max]
    bool press(const std::string& id);                  // runs an action entry

    // State is persisted as `id=on|off` / `id=<float>` lines (same style as the CLI).
    std::string serialize() const;
    void        applyState(const std::string& text);

private:
    std::vector<Entry> mEntries;
};

} // namespace forge::menu
