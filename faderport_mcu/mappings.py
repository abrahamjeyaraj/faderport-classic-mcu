"""
Protocol constants and translation tables for the legacy PreSonus FaderPort
and Mackie Control Universal (MCU) protocol.

All magic numbers live here. Sources:
- Ardour libs/surfaces/faderport/ (GPLv2)
- MCU specification (publicly documented)
"""

# ---------------------------------------------------------------------------
# FaderPort native protocol constants
# ---------------------------------------------------------------------------

# MIDI status bytes (channel 1 = 0 offset)
FP_AFTERTOUCH = 0xA0  # buttons & LEDs
FP_CC = 0xB0          # fader (CC#0 MSB, CC#32 LSB)
FP_PITCHBEND = 0xE0   # pan encoder

# SysEx: Universal Device Inquiry
SYSEX_INQUIRY = [0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]

# Native mode activation: Note On, channel 2, note 0, velocity 100
NATIVE_MODE_ON = [0x91, 0x00, 0x64]

# Expected identity reply bytes (offsets 5-11)
FP_MANUFACTURER = (0x00, 0x01, 0x06)  # PreSonus
FP_FAMILY = (0x02, 0x00)
FP_MODEL = (0x01, 0x00)

# ---------------------------------------------------------------------------
# FaderPort button press IDs  (device → host, via Aftertouch A0 <id> 7F/00)
# ---------------------------------------------------------------------------
FP_BTN_USER = 0
FP_BTN_PUNCH = 1
FP_BTN_SHIFT = 2
FP_BTN_REWIND = 3
FP_BTN_FFWD = 4
FP_BTN_STOP = 5
FP_BTN_PLAY = 6
FP_BTN_RECENABLE = 7
FP_BTN_FPTTOUCH = 8   # "Touch" automation mode button
FP_BTN_WRITE = 9
FP_BTN_READ = 10
FP_BTN_MIX = 11
FP_BTN_PROJ = 12
FP_BTN_TRNS = 13
FP_BTN_UNDO = 14
FP_BTN_LOOP = 15
FP_BTN_REC = 16
FP_BTN_SOLO = 17
FP_BTN_MUTE = 18
FP_BTN_LEFT = 19      # Channel Down
FP_BTN_BANK = 20
FP_BTN_RIGHT = 21     # Channel Up
FP_BTN_OUTPUT = 22
FP_BTN_OFF = 23
FP_BTN_FOOTSWITCH = 126
FP_BTN_FADERTOUCH = 127

# ---------------------------------------------------------------------------
# FaderPort LED IDs  (host → device, via Aftertouch A0 <led_id> 01/00)
# NOTE: LED IDs differ from button press IDs!
# ---------------------------------------------------------------------------
FP_PRESS_TO_LED: dict[int, int] = {
    0: 7,    # User
    1: 6,    # Punch
    2: 5,    # Shift
    3: 4,    # Rewind
    4: 3,    # Fast Forward
    5: 2,    # Stop
    6: 1,    # Play
    7: 0,    # RecEnable
    8: 15,   # FP Touch
    9: 14,   # Write
    10: 13,  # Read
    11: 12,  # Mix
    12: 11,  # Proj
    13: 10,  # Trns
    14: 9,   # Undo
    15: 8,   # Loop
    16: 23,  # Rec
    17: 22,  # Solo
    18: 21,  # Mute
    19: 20,  # Left / Chan Down
    20: 19,  # Bank
    21: 18,  # Right / Chan Up
    22: 17,  # Output
    23: 16,  # Off
}

# Reverse lookup: LED ID → press ID
FP_LED_TO_PRESS: dict[int, int] = {v: k for k, v in FP_PRESS_TO_LED.items()}

# All LED IDs (for turning them all off on init)
ALL_LED_IDS = sorted(FP_PRESS_TO_LED.values())

# ---------------------------------------------------------------------------
# Mackie Control Universal (MCU) protocol constants
# ---------------------------------------------------------------------------

# MCU uses MIDI channel 1 (status byte offset 0)
MCU_NOTE_ON = 0x90
MCU_CC = 0xB0
MCU_PITCHBEND = 0xE0  # per-channel: 0xE0 = ch1, 0xE1 = ch2, etc.

# MCU button note numbers (Note On ch1, velocity 7F=press, 00=release)
MCU_REC_ARM = 0x00       # Rec/Arm ch1 (0x00-0x07 for ch1-8)
MCU_SOLO = 0x08          # Solo ch1 (0x08-0x0F for ch1-8)
MCU_MUTE = 0x10          # Mute ch1 (0x10-0x17 for ch1-8)
MCU_SELECT = 0x18        # Select ch1 (0x18-0x1F for ch1-8)
MCU_VPOT_PRESS = 0x20    # V-Pot press ch1 (0x20-0x27)
MCU_ASSIGN_TRACK = 40       # 0x28
MCU_ASSIGN_SEND = 41        # 0x29
MCU_ASSIGN_PAN = 42         # 0x2A
MCU_ASSIGN_PLUGIN = 43      # 0x2B
MCU_ASSIGN_EQ = 44          # 0x2C — Edit Channel Settings in Cubase
MCU_ASSIGN_INSTRUMENT = 45  # 0x2D — Edit Instrument in Cubase
MCU_BANK_LEFT = 0x2E
MCU_BANK_RIGHT = 0x2F
MCU_CHAN_LEFT = 0x30
MCU_CHAN_RIGHT = 0x31
MCU_FLIP = 0x32
MCU_GLOBAL_VIEW = 0x33
MCU_DISPLAY_NAME = 0x34
MCU_DISPLAY_SMPTE = 0x35
MCU_F1 = 0x36            # F1-F8: Screensets 1-8 in Logic Pro
MCU_F2 = 0x37
MCU_F3 = 0x38
MCU_F4 = 0x39
MCU_F5 = 0x3A
MCU_F6 = 0x3B
MCU_F7 = 0x3C
MCU_F8 = 0x3D
# Global View sub-buttons (track type filters)
MCU_GV_MIDI_TRACKS = 62       # 0x3E
MCU_GV_INPUTS = 63            # 0x3F
MCU_GV_AUDIO_TRACKS = 64      # 0x40
MCU_GV_AUDIO_INSTRUMENTS = 65  # 0x41
MCU_GV_AUX = 66               # 0x42
MCU_GV_BUSSES = 67            # 0x43
MCU_GV_OUTPUTS = 68           # 0x44
MCU_GV_USER = 69              # 0x45

# Modifier keys
MCU_MODIFIER_SHIFT = 70       # 0x46
MCU_MODIFIER_OPTION = 71      # 0x47
MCU_MODIFIER_CONTROL = 72     # 0x48
MCU_MODIFIER_CMD = 73         # 0x49

# Automation
MCU_AUTO_READ = 74             # 0x4A
MCU_AUTO_WRITE = 75            # 0x4B
MCU_AUTO_TRIM = 76             # 0x4C
MCU_AUTO_TOUCH = 77            # 0x4D
MCU_AUTO_LATCH = 78            # 0x4E
MCU_AUTO_GROUP = 79            # 0x4F

# Utility
MCU_SAVE = 80                  # 0x50
MCU_UNDO = 81                  # 0x51
MCU_CANCEL = 82                # 0x52
MCU_ENTER = 83                 # 0x53

# Transport & Markers
MCU_MARKERS = 84               # 0x54
MCU_NUDGE = 85                 # 0x55
MCU_CYCLE = 86                 # 0x56 — Loop
MCU_DROP = 87                  # 0x57
MCU_REPLACE = 88               # 0x58
MCU_CLICK = 89                 # 0x59
MCU_SOLO_MAIN = 90             # 0x5A
MCU_REWIND = 91                # 0x5B
MCU_FFWD = 92                  # 0x5C
MCU_STOP = 93                  # 0x5D
MCU_PLAY = 94                  # 0x5E
MCU_RECORD = 95                # 0x5F

# Navigation
MCU_CURSOR_UP = 96             # 0x60
MCU_CURSOR_DOWN = 97           # 0x61
MCU_CURSOR_LEFT = 98           # 0x62
MCU_CURSOR_RIGHT = 99          # 0x63
MCU_ZOOM = 100                 # 0x64
MCU_SCRUB = 101                # 0x65

# Fader touch (per channel)
MCU_FADER_TOUCH_1 = 104        # 0x68 — ch1-8 = 104-111, master = 112

# MCU V-Pot CC numbers (relative mode: 0x01 = CW, 0x41 = CCW)
MCU_VPOT_CC_1 = 0x10  # 0x10-0x17 for V-Pots 1-8

# MCU V-Pot relative values
MCU_VPOT_CW = 0x01
MCU_VPOT_CCW = 0x41

# ---------------------------------------------------------------------------
# Translation tables: FaderPort press ID ↔ MCU note
# ---------------------------------------------------------------------------

FP_TO_MCU: dict[int, int] = {
    FP_BTN_MUTE: MCU_MUTE,
    FP_BTN_SOLO: MCU_SOLO,
    FP_BTN_REC: MCU_REC_ARM,
    FP_BTN_PLAY: MCU_PLAY,
    FP_BTN_STOP: MCU_STOP,
    FP_BTN_REWIND: MCU_REWIND,
    FP_BTN_FFWD: MCU_FFWD,
    FP_BTN_LOOP: MCU_CYCLE,
    FP_BTN_LEFT: MCU_CURSOR_UP,      # Navigate track up (auto-banks)
    FP_BTN_RIGHT: MCU_CURSOR_DOWN,   # Navigate track down (auto-banks)
    FP_BTN_RECENABLE: MCU_RECORD,
    FP_BTN_PUNCH: MCU_REPLACE,
    # FP_BTN_OUTPUT handled specially in bridge (master mode toggle)
    FP_BTN_UNDO: MCU_UNDO,          # Native MCU Undo (note 81)
    FP_BTN_MIX: MCU_GLOBAL_VIEW,    # Global View — mixer view toggle
    FP_BTN_PROJ: MCU_ASSIGN_EQ,         # Edit Channel Settings
    FP_BTN_TRNS: MCU_ASSIGN_INSTRUMENT, # Edit Instrument
    FP_BTN_FADERTOUCH: MCU_FADER_TOUCH_1,
}

# Reverse: MCU note → FaderPort press ID
MCU_TO_FP: dict[int, int] = {v: k for k, v in FP_TO_MCU.items()}

# MCU note → FaderPort LED ID (for DAW LED feedback → hardware)
MCU_TO_FP_LED: dict[int, int] = {
    mcu_note: FP_PRESS_TO_LED[fp_press]
    for fp_press, mcu_note in FP_TO_MCU.items()
    if fp_press in FP_PRESS_TO_LED
}

# Shift-modified mappings (when Shift is held)
FP_SHIFT_TO_MCU: dict[int, int] = {
    FP_BTN_BANK: MCU_BANK_RIGHT,    # Bank alone = left, Shift+Bank = right
    FP_BTN_LEFT: MCU_BANK_LEFT,     # Shift+Left = Bank Left (jump 8)
    FP_BTN_RIGHT: MCU_BANK_RIGHT,   # Shift+Right = Bank Right (jump 8)
}

# Default (unshifted) Bank mapping
FP_TO_MCU_BANK_DEFAULT = MCU_BANK_LEFT
