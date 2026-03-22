#pragma once
// Protocol constants and translation tables for legacy PreSonus FaderPort
// and Mackie Control Universal (MCU) protocol.

#include <array>
#include <unordered_map>
#include <vector>
#include <cstdint>

namespace fp {

// ---------------------------------------------------------------------------
// FaderPort native protocol constants
// ---------------------------------------------------------------------------
constexpr uint8_t FP_AFTERTOUCH = 0xA0;
constexpr uint8_t FP_CC         = 0xB0;
constexpr uint8_t FP_PITCHBEND  = 0xE0;

// SysEx: Universal Device Inquiry
inline const std::vector<uint8_t> SYSEX_INQUIRY = {0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7};
// Native mode activation: Note On, channel 2, note 0, velocity 100
inline const std::vector<uint8_t> NATIVE_MODE_ON = {0x91, 0x00, 0x64};
inline const std::vector<uint8_t> NATIVE_MODE_OFF = {0x91, 0x00, 0x00};

// ---------------------------------------------------------------------------
// FaderPort button press IDs (device → host, via Aftertouch A0 <id> 01/00)
// ---------------------------------------------------------------------------
constexpr int FP_BTN_USER       = 0;
constexpr int FP_BTN_PUNCH      = 1;
constexpr int FP_BTN_SHIFT      = 2;
constexpr int FP_BTN_REWIND     = 3;
constexpr int FP_BTN_FFWD       = 4;
constexpr int FP_BTN_STOP       = 5;
constexpr int FP_BTN_PLAY       = 6;
constexpr int FP_BTN_RECENABLE  = 7;
constexpr int FP_BTN_FPTTOUCH   = 8;
constexpr int FP_BTN_WRITE      = 9;
constexpr int FP_BTN_READ       = 10;
constexpr int FP_BTN_MIX        = 11;
constexpr int FP_BTN_PROJ       = 12;
constexpr int FP_BTN_TRNS       = 13;
constexpr int FP_BTN_UNDO       = 14;
constexpr int FP_BTN_LOOP       = 15;
constexpr int FP_BTN_REC        = 16;
constexpr int FP_BTN_SOLO       = 17;
constexpr int FP_BTN_MUTE       = 18;
constexpr int FP_BTN_LEFT       = 19;
constexpr int FP_BTN_BANK       = 20;
constexpr int FP_BTN_RIGHT      = 21;
constexpr int FP_BTN_OUTPUT     = 22;
constexpr int FP_BTN_OFF        = 23;
constexpr int FP_BTN_FOOTSWITCH = 126;
constexpr int FP_BTN_FADERTOUCH = 127;

// ---------------------------------------------------------------------------
// FaderPort LED IDs (host → device) — differ from button press IDs!
// ---------------------------------------------------------------------------
inline const std::unordered_map<int,int> FP_PRESS_TO_LED = {
    {0, 7}, {1, 6}, {2, 5}, {3, 4}, {4, 3}, {5, 2}, {6, 1}, {7, 0},
    {8, 15}, {9, 14}, {10, 13}, {11, 12}, {12, 11}, {13, 10}, {14, 9}, {15, 8},
    {16, 23}, {17, 22}, {18, 21}, {19, 20}, {20, 19}, {21, 18}, {22, 17}, {23, 16},
};

inline std::vector<int> allLedIds() {
    std::vector<int> ids;
    for (auto& [k,v] : FP_PRESS_TO_LED) ids.push_back(v);
    std::sort(ids.begin(), ids.end());
    return ids;
}

// ---------------------------------------------------------------------------
// MCU protocol constants
// ---------------------------------------------------------------------------
constexpr uint8_t MCU_NOTE_ON   = 0x90;
constexpr uint8_t MCU_CC        = 0xB0;
constexpr uint8_t MCU_PITCHBEND = 0xE0;

// MCU button note numbers
constexpr int MCU_REC_ARM           = 0x00;
constexpr int MCU_SOLO              = 0x08;
constexpr int MCU_MUTE              = 0x10;
constexpr int MCU_SELECT            = 0x18;
constexpr int MCU_ASSIGN_EQ         = 44;   // Edit Channel Settings
constexpr int MCU_ASSIGN_INSTRUMENT = 45;   // Edit Instrument
constexpr int MCU_BANK_LEFT         = 0x2E;
constexpr int MCU_BANK_RIGHT        = 0x2F;
constexpr int MCU_GLOBAL_VIEW       = 0x33;
// Automation
constexpr int MCU_AUTO_READ         = 74;   // 0x4A
constexpr int MCU_AUTO_WRITE        = 75;   // 0x4B
constexpr int MCU_AUTO_TOUCH        = 77;   // 0x4D
constexpr int MCU_AUTO_LATCH        = 78;   // 0x4E
constexpr int MCU_UNDO              = 81;
constexpr int MCU_CYCLE             = 86;
constexpr int MCU_REPLACE           = 88;
constexpr int MCU_REWIND            = 91;
constexpr int MCU_FFWD              = 92;
constexpr int MCU_STOP              = 93;
constexpr int MCU_PLAY              = 94;
constexpr int MCU_RECORD            = 95;
constexpr int MCU_CURSOR_UP         = 96;
constexpr int MCU_CURSOR_DOWN       = 97;
constexpr int MCU_FADER_TOUCH_1     = 104;

// ---------------------------------------------------------------------------
// Translation tables
// ---------------------------------------------------------------------------
inline const std::unordered_map<int,int> FP_TO_MCU = {
    {FP_BTN_MUTE,      MCU_MUTE},
    {FP_BTN_SOLO,      MCU_SOLO},
    {FP_BTN_REC,       MCU_REC_ARM},
    {FP_BTN_PLAY,      MCU_PLAY},
    {FP_BTN_STOP,      MCU_STOP},
    {FP_BTN_REWIND,    MCU_REWIND},
    {FP_BTN_FFWD,      MCU_FFWD},
    {FP_BTN_LOOP,      MCU_CYCLE},
    {FP_BTN_LEFT,      MCU_CURSOR_UP},
    {FP_BTN_RIGHT,     MCU_CURSOR_DOWN},
    {FP_BTN_RECENABLE, MCU_RECORD},
    {FP_BTN_READ,      MCU_AUTO_READ},
    {FP_BTN_WRITE,     MCU_AUTO_WRITE},
    {FP_BTN_FPTTOUCH,  MCU_AUTO_TOUCH},
    {FP_BTN_PUNCH,     MCU_REPLACE},
    {FP_BTN_UNDO,      MCU_UNDO},
    {FP_BTN_MIX,       MCU_GLOBAL_VIEW},
    {FP_BTN_PROJ,      MCU_ASSIGN_EQ},
    {FP_BTN_TRNS,      MCU_ASSIGN_INSTRUMENT},
    {FP_BTN_FADERTOUCH,MCU_FADER_TOUCH_1},
};

// Reverse: MCU note → FaderPort LED ID
inline std::unordered_map<int,int> buildMcuToFpLed() {
    std::unordered_map<int,int> m;
    for (auto& [fp_press, mcu_note] : FP_TO_MCU) {
        auto it = FP_PRESS_TO_LED.find(fp_press);
        if (it != FP_PRESS_TO_LED.end())
            m[mcu_note] = it->second;
    }
    return m;
}
inline const std::unordered_map<int,int> MCU_TO_FP_LED = buildMcuToFpLed();

// Shift-modified mappings
inline const std::unordered_map<int,int> FP_SHIFT_TO_MCU = {
    {FP_BTN_BANK,  MCU_BANK_RIGHT},
    {FP_BTN_LEFT,  MCU_BANK_LEFT},
    {FP_BTN_RIGHT, MCU_BANK_RIGHT},
};

constexpr int FP_TO_MCU_BANK_DEFAULT = MCU_BANK_LEFT;
constexpr int MASTER_CHANNEL = 8;

} // namespace fp
