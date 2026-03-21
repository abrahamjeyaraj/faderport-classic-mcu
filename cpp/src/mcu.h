#pragma once
#include <RtMidi.h>
#include <functional>
#include <memory>
#include <vector>
#include <cstdint>

namespace fp {

class McuPort {
public:
    // Callbacks from DAW
    std::function<void(int note, bool on)> onLed;
    std::function<void(int channel, int value14bit)> onFader;

    McuPort() = default;
    ~McuPort();

    bool open();
    void close();

    void sendButton(int mcuNote, bool pressed);
    void sendFader(int channel, int value14bit);
    void sendFaderTouch(int channel, bool touched);
    void sendVpot(int vpotNum, int direction, int speed = 3);

private:
    void handleSysex(const std::vector<uint8_t>& msg);
    void midiCallback(double deltaTime, std::vector<uint8_t>* message);
    static void midiCallbackStatic(double dt, std::vector<uint8_t>* msg, void* ud);
    void send(const std::vector<uint8_t>& msg);
    void initiateHandshake();

    std::unique_ptr<RtMidiIn> midiIn_;
    std::unique_ptr<RtMidiOut> midiOut_;

    static constexpr const char* VIRTUAL_PORT_NAME = "FaderPort MCU";
    static inline const std::vector<uint8_t> MCU_SYSEX_HEADER = {0xF0, 0x00, 0x00, 0x66, 0x14};
    static inline const std::vector<uint8_t> MCU_SERIAL = {0x46, 0x50, 0x4D, 0x43, 0x55, 0x30, 0x31};
};

} // namespace fp
