#include "bridge.h"
#include <csignal>
#include <cstdio>
#include <cstring>
#include <thread>
#include <chrono>
#include <atomic>

static std::atomic<bool> running{true};

static void signalHandler(int) {
    running = false;
}

static void listPorts() {
    RtMidiIn in;
    RtMidiOut out;
    printf("MIDI Input Ports:\n");
    for (unsigned i = 0; i < in.getPortCount(); i++)
        printf("  [%d] %s\n", i, in.getPortName(i).c_str());
    printf("\nMIDI Output Ports:\n");
    for (unsigned i = 0; i < out.getPortCount(); i++)
        printf("  [%d] %s\n", i, out.getPortName(i).c_str());
}

int main(int argc, char* argv[]) {
    std::string portHint = "FaderPort";
    bool listOnly = false;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--list-ports") == 0) {
            listOnly = true;
        } else if (strcmp(argv[i], "--port") == 0 && i + 1 < argc) {
            portHint = argv[++i];
        }
    }

    if (listOnly) {
        listPorts();
        return 0;
    }

    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);

    setbuf(stdout, nullptr); // Disable output buffering

    printf("FaderPort MCU Bridge v0.1.0 (C++)\n");
    printf("========================================\n");

    fp::Bridge bridge;
    if (!bridge.start(portHint)) {
        printf("\nFailed to start. Is the FaderPort connected?\n");
        printf("Run with --list-ports to see available MIDI devices.\n");
        return 1;
    }

    printf("\nBridge active! Virtual MIDI port: 'FaderPort MCU'\n");
    printf("Select 'FaderPort MCU' as Mackie Control in your DAW.\n");
    printf("Press Ctrl+C to stop.\n\n");

    while (running) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    printf("\nShutting down...\n");
    bridge.stop();
    return 0;
}
