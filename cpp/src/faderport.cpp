#include "faderport.h"
#include "mappings.h"
#include <cstdio>
#include <thread>
#include <chrono>
#include <algorithm>

namespace fp {

FaderPort::~FaderPort() { disconnect(); }

bool FaderPort::connect(const std::string& portHint) {
    midiIn_ = std::make_unique<RtMidiIn>();
    midiOut_ = std::make_unique<RtMidiOut>();

    int inPort = findPort(*midiIn_, portHint);
    int outPort = findPort(*midiOut_, portHint);

    if (inPort < 0 || outPort < 0) {
        fprintf(stderr, "FaderPort not found. Available ports:\n");
        for (unsigned i = 0; i < midiIn_->getPortCount(); i++)
            fprintf(stderr, "  IN  [%d] %s\n", i, midiIn_->getPortName(i).c_str());
        for (unsigned i = 0; i < midiOut_->getPortCount(); i++)
            fprintf(stderr, "  OUT [%d] %s\n", i, midiOut_->getPortName(i).c_str());
        return false;
    }

    printf("[FP] Opening IN port %d, OUT port %d\n", inPort, outPort);
    midiIn_->openPort(inPort);
    midiOut_->openPort(outPort);
    midiIn_->ignoreTypes(false, true, true); // allow SysEx
    midiIn_->setCallback(&FaderPort::midiCallbackStatic, this);

    connected_ = true;
    return true;
}

void FaderPort::disconnect() {
    if (connected_) {
        allLedsOff();
        send(NATIVE_MODE_OFF);
    }
    if (midiIn_) midiIn_->closePort();
    if (midiOut_) midiOut_->closePort();
    connected_ = false;
}

void FaderPort::initialize() {
    if (!connected_) return;

    printf("[FP] Sending SysEx device inquiry...\n");
    send(SYSEX_INQUIRY);
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    printf("[FP] Activating native mode...\n");
    send(NATIVE_MODE_ON);
    std::this_thread::sleep_for(std::chrono::milliseconds(50));

    allLedsOff();
    printf("[FP] Initialized in native mode\n");
}

void FaderPort::setLed(int ledId, bool on) {
    send({FP_AFTERTOUCH, (uint8_t)(ledId & 0x7F), (uint8_t)(on ? 0x01 : 0x00)});
}

void FaderPort::setFader(int value14bit) {
    int value10 = (value14bit * 1023) / 16383;
    uint8_t msb = (value10 >> 7) & 0x7F;
    uint8_t lsb = value10 & 0x7F;
    send({FP_CC, 0x00, msb});
    send({FP_CC, 0x20, lsb});
}

void FaderPort::midiCallbackStatic(double dt, std::vector<uint8_t>* msg, void* ud) {
    static_cast<FaderPort*>(ud)->midiCallback(dt, msg);
}

void FaderPort::midiCallback(double, std::vector<uint8_t>* message) {
    if (!message || message->empty()) return;
    auto& msg = *message;
    uint8_t status = msg[0];
    uint8_t statusType = status & 0xF0;

    // SysEx
    if (status == 0xF0) return;

    // Aftertouch → button or fader touch
    if (statusType == 0xA0 && msg.size() >= 3) {
        int note = msg[1];
        bool active = msg[2] > 0;
        if (note == FP_BTN_FADERTOUCH) {
            if (onFaderTouch) onFaderTouch(active);
        } else {
            if (onButton) onButton(note, active);
        }
        return;
    }

    // CC → fader (14-bit)
    if (statusType == 0xB0 && msg.size() >= 3) {
        int ccNum = msg[1];
        int value = msg[2];
        if (ccNum == 0x00) {
            faderMsb_ = value;
        } else if (ccNum == 0x20) {
            int fullValue = (faderMsb_ << 7) | value;
            if (onFader) onFader(fullValue);
        }
        return;
    }

    // Pitch Bend → encoder
    if (statusType == 0xE0 && msg.size() >= 3) {
        int pbValue = (msg[2] << 7) | msg[1];
        if (onEncoder) onEncoder(pbValue);
        return;
    }
}

void FaderPort::send(const std::vector<uint8_t>& msg) {
    if (midiOut_) midiOut_->sendMessage(&msg);
}

void FaderPort::allLedsOff() {
    for (int ledId : allLedIds())
        setLed(ledId, false);
}

int FaderPort::findPort(RtMidi& midi, const std::string& hint) {
    std::string hintLower = hint;
    std::transform(hintLower.begin(), hintLower.end(), hintLower.begin(), ::tolower);
    for (unsigned i = 0; i < midi.getPortCount(); i++) {
        std::string name = midi.getPortName(i);
        std::string nameLower = name;
        std::transform(nameLower.begin(), nameLower.end(), nameLower.begin(), ::tolower);
        // Match hint but skip our own virtual port ("FaderPort MCU")
        if (nameLower.find(hintLower) != std::string::npos &&
            nameLower.find("mcu") == std::string::npos)
            return (int)i;
    }
    return -1;
}

} // namespace fp
