#include "mcu.h"
#include "mappings.h"
#include <cstdio>
#include <thread>
#include <chrono>
#include <algorithm>

namespace fp {

McuPort::~McuPort() { close(); }

bool McuPort::open() {
    try {
        midiIn_ = std::make_unique<RtMidiIn>();
        midiIn_->openVirtualPort(VIRTUAL_PORT_NAME);
        midiIn_->ignoreTypes(false, true, true); // allow SysEx
        midiIn_->setCallback(&McuPort::midiCallbackStatic, this);

        midiOut_ = std::make_unique<RtMidiOut>();
        midiOut_->openVirtualPort(VIRTUAL_PORT_NAME);

        printf("[MCU] Virtual MIDI port '%s' created\n", VIRTUAL_PORT_NAME);
        initiateHandshake();
        return true;
    } catch (RtMidiError& e) {
        fprintf(stderr, "[MCU] Failed: %s\n", e.getMessage().c_str());
        return false;
    }
}

void McuPort::initiateHandshake() {
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    auto query = MCU_SYSEX_HEADER;
    query.push_back(0x01); // Host Connection Query
    query.insert(query.end(), MCU_SERIAL.begin(), MCU_SERIAL.end());
    query.push_back(0xF7);
    printf("[MCU] Sending Host Connection Query...\n");
    send(query);
}

void McuPort::close() {
    if (midiIn_) midiIn_->closePort();
    if (midiOut_) midiOut_->closePort();
}

void McuPort::sendButton(int mcuNote, bool pressed) {
    send({MCU_NOTE_ON, (uint8_t)(mcuNote & 0x7F), (uint8_t)(pressed ? 0x7F : 0x00)});
}

void McuPort::sendFader(int channel, int value14bit) {
    value14bit = std::clamp(value14bit, 0, 16383);
    uint8_t lsb = value14bit & 0x7F;
    uint8_t msb = (value14bit >> 7) & 0x7F;
    send({(uint8_t)(MCU_PITCHBEND | (channel & 0x0F)), lsb, msb});
}

void McuPort::sendFaderTouch(int channel, bool touched) {
    uint8_t note = 0x68 + (channel & 0x07);
    send({MCU_NOTE_ON, note, (uint8_t)(touched ? 0x7F : 0x00)});
}

void McuPort::sendVpot(int vpotNum, int direction) {
    uint8_t ccNum = 0x10 + (vpotNum & 0x07);
    uint8_t value = (direction > 0) ? 0x01 : 0x41;
    send({MCU_CC, ccNum, value});
}

void McuPort::handleSysex(const std::vector<uint8_t>& msg) {
    // Universal Identity Request: F0 7E 7F 06 01 F7
    if (msg.size() >= 6 && msg[1] == 0x7E && msg[2] == 0x7F && msg[3] == 0x06 && msg[4] == 0x01) {
        printf("[MCU] Universal Identity Request — sending MCU identity\n");
        send({0xF0, 0x7E, 0x7F, 0x06, 0x02,
              0x00, 0x00, 0x66, 0x14, 0x00, 0x01, 0x00,
              0x01, 0x00, 0x00, 0x00, 0xF7});
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        auto query = MCU_SYSEX_HEADER;
        query.push_back(0x01);
        query.insert(query.end(), MCU_SERIAL.begin(), MCU_SERIAL.end());
        query.push_back(0xF7);
        printf("[MCU] Sending Host Connection Query...\n");
        send(query);
        return;
    }

    // MCU SysEx: F0 00 00 66 14 <cmd> ...
    if (msg.size() < 7) return;
    if (msg[1] != 0x00 || msg[2] != 0x00 || msg[3] != 0x66 || msg[4] != 0x14) return;

    uint8_t cmd = msg[5];

    if (cmd == 0x00) { // Device Query
        printf("[MCU] Device query — sending Host Connection Query\n");
        auto reply = MCU_SYSEX_HEADER;
        reply.push_back(0x01);
        reply.insert(reply.end(), MCU_SERIAL.begin(), MCU_SERIAL.end());
        reply.push_back(0xF7);
        send(reply);
    } else if (cmd == 0x02) { // Host Connection Reply → send confirmation
        printf("[MCU] Host Connection Reply — sending confirmation\n");
        auto reply = MCU_SYSEX_HEADER;
        reply.push_back(0x03);
        if (msg.size() >= 13)
            reply.insert(reply.end(), msg.begin() + 6, msg.begin() + 13);
        else
            reply.insert(reply.end(), MCU_SERIAL.begin(), MCU_SERIAL.end());
        reply.push_back(0xF7);
        send(reply);
        printf("[MCU] Handshake complete!\n");
    } else if (cmd == 0x03) {
        printf("[MCU] Connection confirmed by DAW\n");
    }
}

void McuPort::midiCallbackStatic(double dt, std::vector<uint8_t>* msg, void* ud) {
    static_cast<McuPort*>(ud)->midiCallback(dt, msg);
}

void McuPort::midiCallback(double, std::vector<uint8_t>* message) {
    if (!message || message->empty()) return;
    auto& msg = *message;
    uint8_t status = msg[0];

    if (status == 0xF0) {
        handleSysex(msg);
        return;
    }

    uint8_t statusType = status & 0xF0;
    int channel = status & 0x0F;

    // Note On → LED feedback
    if (statusType == 0x90 && msg.size() >= 3) {
        if (onLed) onLed(msg[1], msg[2] > 0);
        return;
    }

    // Pitch Bend → fader motor
    if (statusType == 0xE0 && msg.size() >= 3) {
        int value = (msg[2] << 7) | msg[1];
        if (onFader) onFader(channel, value);
        return;
    }
}

void McuPort::send(const std::vector<uint8_t>& msg) {
    if (midiOut_) midiOut_->sendMessage(&msg);
}

} // namespace fp
