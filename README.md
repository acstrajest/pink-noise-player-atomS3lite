# AtomS3 Lite Pink-Noise Player

A MicroPython script (`pink-noise-player-atomS3lite.py`) that generates Paul Kellet pink noise and outputs it over I2S (16-bit mono, 16 kHz) for the M5Stack AtomS3 Lite.

## Features
- **Audio Output:** Generates Paul Kellet pink noise via I2S (16-bit mono, 16 kHz).
- **Hardware Control:** Uses device pins for BCLK/WS/DATA and a hardware button to toggle playback (includes debounce and chunked buffering).
- **Custom LED Driver:** Includes a `SimpleLED` class utilizing `machine.bitstream` to drive the WS2812-style LED without needing external modules.
- **Status Indicators:** 
  - 🟢 **Stopped:** Green
  - 🔵 **Playing:** Blue (outputs a silent buffer when stopped).
