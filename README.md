# AtomS3 Lite Pink-Noise Player

A portable MicroPython script that generates Paul Kellet pink noise for the M5Stack AtomS3 Lite (paired with Atomic SPK Base and ATOM TailBAT).

## Hardware Setup

* **Main Unit:** M5Stack AtomS3 Lite
* **Audio Output:** Atomic SPK Base – I2S audio module with a built-in 3.5mm headphone jack for private listening
* **Power Source:** ATOM TailBAT (Portable setup)

## Pin Configuration

| Function | GPIO Pin | Description |
| :--- | :--- | :--- |
| **BCLK** (Bit Clock) | GPIO 5 | I2S Audio |
| **WS** (Word Select / LRCK) | GPIO 39 | I2S Audio |
| **DATA** (Data Out) | GPIO 38 | I2S Audio |
| **Button** (Built-in) | GPIO 41 | Toggle Play / Stop |
| **LED** (WS2812) | GPIO 35 | Status Indicator |

## How to Use

Press the built-in button on the AtomS3 Lite to toggle playback:
* 🟢 **Stopped:** LED lights up green (outputs a silent buffer).
* 🔵 **Playing:** LED lights up blue (outputs pink noise).

Audio Output Options:
You can connect wired earphones/headphones to the headphone jack on the Atom SPK / Atomic SPK Base module.
For speaker output, the module also has a built-in speaker.

## Features

* **Real-time Pink Noise:** Generates 16-bit mono, 16 kHz Paul Kellet pink noise dynamically via I2S.
* **Zero External Dependencies:** Includes a custom `SimpleLED` class utilizing `machine.bitstream` (no `neopixel` library required).
* **Stable Audio Processing:** Built-in button debounce and chunked buffering to prevent audio crackles.

## Quick Start

1. Flash **MicroPython** firmware to your AtomS3 Lite.
2. Stack the **Atom SPK** and **TailBattery** onto the AtomS3 Lite.
3. Upload `main.py` (or the script) to the device and run it.

---

## FAQ

**Q. How do I change the volume?**
A. Edit the `VOLUME = 1200` line in `main.py` before uploading.

**Q. Why is there no volume control via button?**
A. To keep this device as a zero-friction "focus gear." 
Just flip the switch, and it instantly plays at your favorite pre-set volume—no extra clicks, no distraction.

About Earphones:
This player is tuned to work well even with standard, low-cost earphones (like typical 100-yen shop ones). No special high-impedance headphones are required—just plug in and enjoy.
