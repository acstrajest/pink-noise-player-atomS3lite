# AtomS3 Lite Pink-Noise Player

A portable MicroPython script that generates Paul Kellet pink noise for the **M5Stack AtomS3 Lite** (paired with Atom SPK and TailBattery).

## Hardware Setup

* **Main Unit:** M5Stack AtomS3 Lite
* **Audio Output:** M5Stack Atom SPK (Speaker module)
* **Power Source:** M5Stack TailBattery (Portable setup)

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

## Features

* **Real-time Pink Noise:** Generates 16-bit mono, 16 kHz Paul Kellet pink noise dynamically via I2S.
* **Zero External Dependencies:** Includes a custom `SimpleLED` class utilizing `machine.bitstream` (no `neopixel` library required).
* **Stable Audio Processing:** Built-in button debounce and chunked buffering to prevent audio crackles.

## Quick Start

1. Flash **MicroPython** firmware to your AtomS3 Lite.
2. Stack the **Atom SPK** and **TailBattery** onto the AtomS3 Lite.
3. Upload `main.py` (or the script) to the device and run it.
