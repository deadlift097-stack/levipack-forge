# native/ - in-game mod menu (C++)

A LeviLauncher Android native mod that scans a `packs/` folder for `.levipack`
files and lists them in a mod menu with on/off toggles. State is stored in the
same `.levipack-state` file the `levipack menu` CLI uses, so both stay in sync.

## What is verified and what is not

| Part | Status |
|---|---|
| `src/menu/*` (menu model, pack scanner) | Compiled and unit-tested on the host (`ctest`) |
| `src/mod/ForgeMenuMod.*`, `src/main.cpp` | Written from the template README's lifecycle; **not compiled against the SDK** |
| `src/mod/PreloaderMenuAdapter.cpp` | Falls back to a log menu; the real `<pl/ModMenu.hpp>` binding is **not written** |

Before the first Android build, compare these with the official template
(<https://github.com/QYCottage/levilauncher-android-mod-template>):

1. `src/main.cpp`: the exact `PL_REGISTER_MOD(...)` arguments.
2. `src/mod/ForgeMenuMod.h`: base class (if any) and constructor shape.
3. `<pl/ModMenu.hpp>`: implement `PreloaderMenuHost : IMenuHost` in
   `PreloaderMenuAdapter.cpp` using the SDK's real toggle / button calls.

## Build (Android)

```
cmake -S native -B build-arm64 -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_HOME/ndk/28.2.13676358/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-28 -DANDROID_STL=c++_shared \
  -DPRELOADER_SDK_INCLUDE=/path/to/preloader-android/include
cmake --build build-arm64 --target levi_package
```

`levi_package` calls the Python `levipack pack` command, so the result is a
`forge_menu.levipack` you can import into LeviLauncher.

## Host tests

```
cmake -S native -B build-host && cmake --build build-host --target menu_test && ctest --test-dir build-host
```
(The host configure prints a warning about the missing SDK include; that is expected.)
