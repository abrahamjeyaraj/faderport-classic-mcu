#import <Cocoa/Cocoa.h>
#include "bridge.h"
#include <thread>
#include <atomic>

@interface AppDelegate : NSObject <NSApplicationDelegate> {
    NSStatusItem* _statusItem;
    NSMenuItem* _statusMenuItem;
    fp::Bridge* _bridge;
    std::atomic<bool> _running;
}
@end

@implementation AppDelegate

- (instancetype)init {
    self = [super init];
    _bridge = nullptr;
    _running = false;
    return self;
}

- (void)applicationDidFinishLaunching:(NSNotification*)notification {
    // Create status bar item with SF Symbol icon
    _statusItem = [[NSStatusBar systemStatusBar] statusItemWithLength:NSSquareStatusItemLength];
    NSImage* icon = [NSImage imageWithSystemSymbolName:@"slider.vertical.3"
                              accessibilityDescription:@"FaderPort MCU"];
    if (icon) {
        [icon setTemplate:YES]; // adapts to light/dark mode
        _statusItem.button.image = icon;
    } else {
        _statusItem.button.title = @"FP"; // fallback
    }

    NSMenu* menu = [[NSMenu alloc] init];

    _statusMenuItem = [menu addItemWithTitle:@"Starting..." action:nil keyEquivalent:@""];
    _statusMenuItem.enabled = NO;

    [menu addItem:[NSMenuItem separatorItem]];

    NSMenuItem* restart = [menu addItemWithTitle:@"Restart Bridge" action:@selector(doRestart:) keyEquivalent:@"r"];
    restart.target = self;

    [menu addItem:[NSMenuItem separatorItem]];

    NSMenuItem* about = [menu addItemWithTitle:@"About FaderPort MCU" action:@selector(doAbout:) keyEquivalent:@""];
    about.target = self;

    [menu addItem:[NSMenuItem separatorItem]];

    NSMenuItem* quit = [menu addItemWithTitle:@"Quit FaderPort MCU" action:@selector(doQuit:) keyEquivalent:@"q"];
    quit.target = self;

    _statusItem.menu = menu;

    NSLog(@"Menu bar created, starting bridge...");

    // Start bridge after a short delay to let the run loop settle
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 500 * NSEC_PER_MSEC),
                   dispatch_get_main_queue(), ^{
        [self startBridge];
    });
}

- (void)startBridge {
    if (_running) return;
    if (!_bridge) _bridge = new fp::Bridge();

    // Run bridge on background thread so menu bar stays responsive
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        @try {
            bool ok = self->_bridge->start("FaderPort");
            self->_running = ok;

            dispatch_async(dispatch_get_main_queue(), ^{
                if (ok) {
                    self->_statusMenuItem.title = @"✓ Bridge Active";
                    NSLog(@"Bridge started successfully");
                } else {
                    self->_statusMenuItem.title = @"✗ FaderPort not found";
                    NSImage* errIcon = [NSImage imageWithSystemSymbolName:@"exclamationmark.triangle"
                                                  accessibilityDescription:@"Error"];
                    if (errIcon) {
                        [errIcon setTemplate:YES];
                        self->_statusItem.button.image = errIcon;
                    }
                    NSLog(@"Bridge failed to start");
                }
            });
        } @catch (NSException* e) {
            NSLog(@"Bridge exception: %@", e);
            dispatch_async(dispatch_get_main_queue(), ^{
                self->_statusMenuItem.title = @"✗ Error";
            });
        }
    });
}

- (void)stopBridge {
    if (_running && _bridge) {
        _bridge->stop();
        _running = false;
        delete _bridge;
        _bridge = nullptr;
    }
}

- (void)doRestart:(id)sender {
    [self stopBridge];
    _statusMenuItem.title = @"Restarting...";
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 500 * NSEC_PER_MSEC),
                   dispatch_get_main_queue(), ^{
        [self startBridge];
    });
}

- (void)doAbout:(id)sender {
    NSAlert* alert = [[NSAlert alloc] init];
    alert.messageText = @"FaderPort MCU Bridge";
    alert.informativeText = @"Version 0.1.0\n\n"
        "MIDI bridge for the legacy PreSonus FaderPort.\n"
        "Translates FaderPort native protocol to Mackie Control Universal (MCU) "
        "for use with Logic Pro, Cubase, and other DAWs.\n\n"
        "© 2026 Abraham Jeyaraj";
    alert.alertStyle = NSAlertStyleInformational;
    [alert addButtonWithTitle:@"OK"];

    // Set the fader icon on the alert
    NSImage* icon = [NSImage imageWithSystemSymbolName:@"slider.vertical.3"
                              accessibilityDescription:@"FaderPort MCU"];
    if (icon) {
        NSImage* largeIcon = [icon copy];
        largeIcon.size = NSMakeSize(64, 64);
        alert.icon = largeIcon;
    }

    // Bring app to front for the dialog
    [NSApp activateIgnoringOtherApps:YES];
    [alert runModal];
}

- (void)doQuit:(id)sender {
    [self stopBridge];
    [NSApp terminate:nil];
}

- (void)applicationWillTerminate:(NSNotification*)notification {
    [self stopBridge];
}

- (void)dealloc {
    if (_bridge) { delete _bridge; _bridge = nullptr; }
}

@end

int main(int argc, const char* argv[]) {
    setbuf(stdout, nullptr);

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--list-ports") == 0) {
            RtMidiIn in; RtMidiOut out;
            printf("MIDI Input Ports:\n");
            for (unsigned j = 0; j < in.getPortCount(); j++)
                printf("  [%d] %s\n", j, in.getPortName(j).c_str());
            printf("\nMIDI Output Ports:\n");
            for (unsigned j = 0; j < out.getPortCount(); j++)
                printf("  [%d] %s\n", j, out.getPortName(j).c_str());
            return 0;
        }
    }

    @autoreleasepool {
        NSApplication* app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyAccessory];
        AppDelegate* delegate = [[AppDelegate alloc] init];
        app.delegate = delegate;
        [app run];
    }
    return 0;
}
