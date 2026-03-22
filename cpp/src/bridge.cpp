#include "bridge.h"
#include "mappings.h"
#include <cstdio>
#include <thread>
#include <chrono>

namespace fp {

bool Bridge::start(const std::string& portHint) {
    if (!fp_.connect(portHint)) return false;
    if (!mcu_.open()) { fp_.disconnect(); return false; }

    fp_.onButton     = [this](int id, bool p) { fpButton(id, p); };
    fp_.onFader      = [this](int v) { fpFader(v); };
    fp_.onEncoder    = [this](int v) { fpEncoder(v); };
    fp_.onFaderTouch = [this](bool t) { fpFaderTouch(t); };
    mcu_.onLed       = [this](int n, bool on) { mcuLed(n, on); };
    mcu_.onFader     = [this](int ch, int v) { mcuFader(ch, v); };

    fp_.initialize();

    // Request initial fader positions
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    printf("[Bridge] Requesting initial fader positions...\n");
    for (int ch = 0; ch < 9; ch++) {
        mcu_.sendFaderTouch(ch, true);
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
        mcu_.sendFaderTouch(ch, false);
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }

    printf("[Bridge] Active — FaderPort <-> MCU translation running\n");
    return true;
}

void Bridge::stop() {
    fp_.disconnect();
    mcu_.close();
    printf("[Bridge] Stopped\n");
}

int Bridge::activeChannel() const {
    return masterMode_ ? MASTER_CHANNEL : selectedChannel_;
}

// ---- FaderPort → MCU ----

void Bridge::fpButton(int pressId, bool pressed) {
    // Shift
    if (pressId == FP_BTN_SHIFT) {
        shiftHeld_ = pressed;
        return;
    }

    // Output = master fader toggle
    if (pressId == FP_BTN_OUTPUT) {
        if (!pressed) return;
        masterMode_ = !masterMode_;
        auto it = FP_PRESS_TO_LED.find(FP_BTN_OUTPUT);
        if (it != FP_PRESS_TO_LED.end())
            fp_.setLed(it->second, masterMode_);
        printf("[Bridge] Master mode %s\n", masterMode_ ? "ON" : "OFF");
        return;
    }

    // Shift-modified
    if (shiftHeld_) {
        auto it = FP_SHIFT_TO_MCU.find(pressId);
        if (it != FP_SHIFT_TO_MCU.end()) {
            mcu_.sendButton(it->second, pressed);
            return;
        }
    }

    // Bank default
    if (pressId == FP_BTN_BANK) {
        mcu_.sendButton(FP_TO_MCU_BANK_DEFAULT, pressed);
        return;
    }

    // Standard mapping
    auto it = FP_TO_MCU.find(pressId);
    if (it != FP_TO_MCU.end()) {
        int mcuNote = it->second;

        // Per-channel buttons: offset by selected channel
        // Mute (0x10-0x17), Solo (0x08-0x0F), Rec Arm (0x00-0x07)
        if (mcuNote == MCU_MUTE || mcuNote == MCU_SOLO || mcuNote == MCU_REC_ARM)
            mcuNote += selectedChannel_;

        mcu_.sendButton(mcuNote, pressed);
    }
}

void Bridge::fpFader(int value14bit) {
    mcu_.sendFader(activeChannel(), value14bit);
}

void Bridge::fpEncoder(int pitchBendRaw) {
    auto dir = encoder_.process(pitchBendRaw);
    if (dir.has_value())
        mcu_.sendVpot(selectedChannel_, dir.value());
}

void Bridge::fpFaderTouch(bool touched) {
    faderTouched_ = touched;
    mcu_.sendFaderTouch(activeChannel(), touched);
}

// ---- MCU → FaderPort ----

void Bridge::mcuLed(int mcuNote, bool on) {
    // Track Select LEDs to know selected channel
    if (mcuNote >= 0x18 && mcuNote <= 0x1F && on) {
        int oldCh = selectedChannel_;
        selectedChannel_ = mcuNote - 0x18;
        if (selectedChannel_ != oldCh && !masterMode_ && !faderTouched_) {
            auto& cached = faderCache_[selectedChannel_];
            if (cached.has_value()) {
                fp_.setFader(cached.value());
            }
        }
    }

    // Per-channel LED feedback: check if this is mute/solo/rec for the selected channel
    int ledNote = mcuNote;
    // Mute range 0x10-0x17: show LED only if it's for our selected channel
    if (mcuNote >= 0x10 && mcuNote <= 0x17) {
        if ((mcuNote - 0x10) == selectedChannel_)
            ledNote = MCU_MUTE;  // Map back to base for LED lookup
        else
            return;  // Not our channel, ignore
    }
    // Solo range 0x08-0x0F
    else if (mcuNote >= 0x08 && mcuNote <= 0x0F) {
        if ((mcuNote - 0x08) == selectedChannel_)
            ledNote = MCU_SOLO;
        else
            return;
    }
    // Rec Arm range 0x00-0x07
    else if (mcuNote >= 0x00 && mcuNote <= 0x07) {
        if (mcuNote == selectedChannel_)
            ledNote = MCU_REC_ARM;
        else
            return;
    }

    auto it = MCU_TO_FP_LED.find(ledNote);
    if (it != MCU_TO_FP_LED.end())
        fp_.setLed(it->second, on);
}

void Bridge::mcuFader(int channel, int value14bit) {
    // Cache position
    if (channel >= 0 && channel <= 8)
        faderCache_[channel] = value14bit;

    // Only move physical fader if active channel
    if (channel != activeChannel()) return;
    if (faderTouched_) return;

    fp_.setFader(value14bit);
}

} // namespace fp
