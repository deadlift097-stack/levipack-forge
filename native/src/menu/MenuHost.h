#pragma once
// Boundary between our menu model and the launcher's mod-menu API.
#include "MenuModel.h"

#include <functional>
#include <string>

namespace forge::menu {

class IMenuHost {
public:
    virtual ~IMenuHost() = default;
    // Present `model` to the player. `onChange` must be called after any edit.
    virtual void show(MenuModel& model, std::function<void()> onChange) = 0;
    virtual void hide() = 0;
};

// Always available; writes the menu to a log sink. Used on the host and as a
// fallback when <pl/ModMenu.hpp> is not on the include path.
class LogMenuHost : public IMenuHost {
public:
    explicit LogMenuHost(std::function<void(const std::string&)> sink) : mSink(std::move(sink)) {}
    void show(MenuModel& model, std::function<void()>) override {
        for (const Entry& e : model.entries()) mSink("[menu] " + e.label);
    }
    void hide() override {}
private:
    std::function<void(const std::string&)> mSink;
};

} // namespace forge::menu
