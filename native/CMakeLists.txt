cmake_minimum_required(VERSION 3.22)
project(forge_menu LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Same option names as the LeviLauncher Android mod template.
set(MOD_ID "forge_menu" CACHE STRING "Mod id")
set(MOD_NAME "Forge Menu" CACHE STRING "Display name")
set(MOD_AUTHOR "levipack-forge" CACHE STRING "Author")
set(MOD_VERSION "0.1.0" CACHE STRING "Version")
set(MOD_LIBRARY_NAME "forge_menu" CACHE STRING "Shared library base name")
set(MOD_MINECRAFT_VERSIONS "[\"1.21.*\"]" CACHE STRING "JSON array of version patterns")
set(MOD_ICON "" CACHE STRING "Icon file name inside the levipack (optional)")

# Path to the preloader-android SDK `include` directory (the one containing pl/).
set(PRELOADER_SDK_INCLUDE "" CACHE PATH "preloader-android SDK include directory")
# Optional: preloader library to link, if the SDK ships one.
set(PRELOADER_LIBRARY "" CACHE FILEPATH "preloader library to link (optional)")

add_library(${MOD_LIBRARY_NAME} SHARED
    src/main.cpp
    src/mod/ForgeMenuMod.cpp
    src/mod/PreloaderMenuAdapter.cpp
    src/menu/MenuModel.cpp
    src/menu/PackScanner.cpp)

if(PRELOADER_SDK_INCLUDE)
    target_include_directories(${MOD_LIBRARY_NAME} PRIVATE "${PRELOADER_SDK_INCLUDE}")
else()
    message(WARNING "PRELOADER_SDK_INCLUDE is not set; <pl/Mod.hpp> will not be found.")
endif()
if(PRELOADER_LIBRARY)
    target_link_libraries(${MOD_LIBRARY_NAME} PRIVATE "${PRELOADER_LIBRARY}")
endif()

configure_file(manifest.json.in "${CMAKE_BINARY_DIR}/pack/manifest.json" @ONLY)

# Host-only unit tests for the SDK-independent menu code: `ctest`
enable_testing()
add_executable(menu_test tests/menu_test.cpp src/menu/MenuModel.cpp src/menu/PackScanner.cpp)
add_test(NAME menu_test COMMAND menu_test)

# `cmake --build <dir> --target levi_package` -> <dir>/<MOD_ID>.levipack
find_package(Python3 COMPONENTS Interpreter)
if(Python3_FOUND)
    add_custom_target(levi_package
        COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${CMAKE_SOURCE_DIR}/.."
                ${Python3_EXECUTABLE} -m levipack_forge pack "${CMAKE_BINARY_DIR}/pack"
                --lib "$<TARGET_FILE:${MOD_LIBRARY_NAME}>"
                -o "${CMAKE_BINARY_DIR}/${MOD_ID}.levipack"
        DEPENDS ${MOD_LIBRARY_NAME}
        COMMENT "Packaging ${MOD_ID}.levipack")
endif()
