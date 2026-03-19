#pragma once
#include <RtMidi.h>
#include <functional>
#include <memory>
#include <string>
#include <cstdint>

namespace fp {

class FaderPort {
public:
    // Callbacks
    std::function<void(int pressId, bool pressed)> onButton;
    std::function<void(int value14bit)> onFader;
    std::function<void(int pitchBendRaw)> onEncoder;
    std::function<void(bool touched)> onFaderTouch;

    FaderPort() = default;
    ~FaderPort();

    bool connect(const std::string& portHint = "FaderPort");
    void disconnect();
    void initialize();

    void setLed(int ledId, bool on);
    void setFader(int value14bit);

private:
    void midiCallback(double deltaTime, std::vector<uint8_t>* message);
    static void midiCallbackStatic(double dt, std::vector<uint8_t>* msg, void* ud);
    void send(const std::vector<uint8_t>& msg);
    void allLedsOff();
    static int findPort(RtMidi& midi, const std::string& hint);

    std::unique_ptr<RtMidiIn> midiIn_;
    std::unique_ptr<RtMidiOut> midiOut_;
    int faderMsb_ = 0;
    bool connected_ = false;
};

} // namespace fp
