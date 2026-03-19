cmake_minimum_required(VERSION 3.14)
project(faderport_mcu VERSION 0.1.0 LANGUAGES CXX OBJCXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Fetch RtMidi
include(FetchContent)
FetchContent_Declare(
    rtmidi
    GIT_REPOSITORY https://github.com/thestk/rtmidi.git
    GIT_TAG        6.0.0
)
FetchContent_MakeAvailable(rtmidi)

# Shared source files (bridge core)
set(BRIDGE_SOURCES
    src/bridge.cpp
    src/faderport.cpp
    src/mcu.cpp
    src/encoder.cpp
)

# --- CLI version ---
add_executable(faderport_mcu_cli
    src/main.cpp
    ${BRIDGE_SOURCES}
)
target_link_libraries(faderport_mcu_cli PRIVATE rtmidi)
target_include_directories(faderport_mcu_cli PRIVATE src)

# --- macOS menu bar (tray) app ---
if(APPLE)
    add_executable(FaderPortMCU MACOSX_BUNDLE
        src/app_macos.mm
        ${BRIDGE_SOURCES}
    )
    target_link_libraries(FaderPortMCU PRIVATE rtmidi
        "-framework Cocoa"
        "-framework CoreMIDI"
        "-framework CoreAudio"
        "-framework CoreFoundation"
    )
    target_include_directories(FaderPortMCU PRIVATE src)

    # App bundle settings
    set_target_properties(FaderPortMCU PROPERTIES
        MACOSX_BUNDLE_BUNDLE_NAME "FaderPort MCU"
        MACOSX_BUNDLE_BUNDLE_VERSION "${PROJECT_VERSION}"
        MACOSX_BUNDLE_SHORT_VERSION_STRING "${PROJECT_VERSION}"
        MACOSX_BUNDLE_GUI_IDENTIFIER "com.faderport.mcu"
        MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/Info.plist.in"
    )

    # Also link frameworks for CLI on macOS
    target_link_libraries(faderport_mcu_cli PRIVATE
        "-framework CoreMIDI"
        "-framework CoreAudio"
        "-framework CoreFoundation"
    )
endif()

install(TARGETS faderport_mcu_cli RUNTIME DESTINATION bin)
