# AtomS3 Lite Pink-Noise Player

A MicroPython script that generates Paul Kellet pink noise and outputs it over I2S (16-bit mono, 16 kHz) for M5Stack AtomS3 Lite.

## Hardware Setup (または Requirements)
- **Main Unit:** M5Stack AtomS3 Lite
- **Audio:** M5Stack Atom SPK
- **Power:** TailBattery (Portable setup)

## Features
- Generates Paul Kellet pink noise via I2S.
- Hardware button to toggle playback (with debounce).
- Custom `SimpleLED` class (`machine.bitstream`) for WS2812 LED.
- Status indicator: Stopped (Green) / Playing (Blue).
- 
