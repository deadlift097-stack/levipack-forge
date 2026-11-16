#include "MenuModel.h"

#include <algorithm>
#include <cstdlib>
#include <sstream>

namespace forge::menu {

Entry& MenuModel::addToggle(std::string id, std::string label, bool initial) {
    Entry e;
    e.id = std::move(id);
    e.label = std::move(label);
    e.kind = EntryKind::Toggle;
    e.on = initial;
    mEntries.push_back(std::move(e));
    return mEntries.back();
}

Entry& MenuModel::addSlider(std::string id, std::string label, float lo, float hi, float initial) {
    Entry e;
    e.id = std::move(id);
    e.label = std::move(label);
    e.kind = EntryKind::Slider;
    e.min = lo;
    e.max = hi;
    e.value = std::clamp(initial, lo, hi);
    mEntries.push_back(std::move(e));
    return mEntries.back();
}

Entry& MenuModel::addAction(std::string id, std::string label, std::function<void()> fn) {
    Entry e;
    e.id = std::move(id);
    e.label = std::move(label);
    e.kind = EntryKind::Action;
    e.action = std::move(fn);
    mEntries.push_back(std::move(e));
    return mEntries.back();
}

Entry* MenuModel::find(const std::string& id) {
    auto it = std::find_if(mEntries.begin(), mEntries.end(),
                           [&](const Entry& e) { return e.id == id; });
    return it == mEntries.end() ? nullptr : &*it;
}

bool MenuModel::toggle(const std::string& id) {
    Entry* e = find(id);
    if (!e || e->kind != EntryKind::Toggle) return false;
    e->on = !e->on;
    return true;
}

bool MenuModel::setSlider(const std::string& id, float v) {
    Entry* e = find(id);
    if (!e || e->kind != EntryKind::Slider) return false;
    e->value = std::clamp(v, e->min, e->max);
    return true;
}

bool MenuModel::press(const std::string& id) {
    Entry* e = find(id);
    if (!e || e->kind != EntryKind::Action || !e->action) return false;
    e->action();
    return true;
}

std::string MenuModel::serialize() const {
    std::ostringstream out;
    for (const Entry& e : mEntries) {
        if (e.kind == EntryKind::Toggle) out << e.id << '=' << (e.on ? "on" : "off") << '\n';
        else if (e.kind == EntryKind::Slider) out << e.id << '=' << e.value << '\n';
    }
    return out.str();
}

void MenuModel::applyState(const std::string& text) {
    std::istringstream in(text);
    std::string line;
    while (std::getline(in, line)) {
        auto eq = line.find('=');
        if (eq == std::string::npos) continue;
        std::string key = line.substr(0, eq), val = line.substr(eq + 1);
        while (!val.empty() && (val.back() == '\r' || val.back() == ' ')) val.pop_back();
        Entry* e = find(key);
        if (!e) continue;
        if (e->kind == EntryKind::Toggle) e->on = (val != "off");
        else if (e->kind == EntryKind::Slider) e->value = std::clamp(
            static_cast<float>(std::atof(val.c_str())), e->min, e->max);
    }
}

} // namespace forge::menu
