#pragma once
#include "faderport.h"
#include "mcu.h"
#include "encoder.h"
#include <array>
#include <optional>

namespace fp {

class Bridge {
public:
    bool start(const std::string& portHint = "FaderPort");
    void stop();

private:
    // FaderPort → MCU
    void fpButton(int pressId, bool pressed);
    void fpFader(int value14bit);
    void fpEncoder(int pitchBendRaw);
    void fpFaderTouch(bool touched);

    // MCU → FaderPort
    void mcuLed(int mcuNote, bool on);
    void mcuFader(int channel, int value14bit);

    int activeChannel() const;

    FaderPort fp_;
    McuPort mcu_;
    EncoderFilter encoder_;

    bool shiftHeld_ = false;
    bool faderTouched_ = false;
    bool masterMode_ = false;
    int selectedChannel_ = 0;

    // Fader position cache: index 0-7 = tracks, 8 = master
    std::array<std::optional<int>, 9> faderCache_{};
};

} // namespace fp
