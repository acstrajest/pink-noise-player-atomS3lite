# AtomS3 Lite Pink-Noise Player

A portable MicroPython script that generates Paul Kellet pink noise for the M5Stack AtomS3 Lite (paired with Atom SPK and TailBattery).

## Hardware Setup
- **Main Unit:** M5Stack AtomS3 Lite
- **Audio Output:** M5Stack Atom SPK (Speaker module)
- **Power Source:** M5Stack TailBattery (Portable setup)

## Pin Configuration
| Usage | GPIO Pin | Description |
| :--- | :--- | :--- |
| **BCLK** (Bit Clock) | GPIO 5 | I2S Audio |
| **WS** (Word Select) | GPIO 39 | I2S Audio |
| **DATA** (Data Out) | GPIO 38 | I2S Audio |
| **Button** (Built-in) | GPIO 41 | Toggle Play / Stop |
| **LED** (WS2812) | GPIO 35 | Status Indicator |

## Usage
Press the built-in button on the AtomS3 Lite to toggle playback:

- 🟢 **Stopped:** LED lights up green, outputs a silent buffer.
- 🔵 **Playing:** LED lights up blue, outputs pink noise.

## Features
- Generates 16-bit mono, 16 kHz Paul Kellet pink noise via I2S.
- Includes a custom `SimpleLED` class utilizing `machine.bitstream` without needing external modules.
- Built-in button debounce and chunked buffering for stable playback.
