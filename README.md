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
| **Button** (Built-in) | GPIO 41 | Multi-function Control |
| **LED** (WS2812) | GPIO 35 | Status Indicator |

## How to Use

Operate everything using the single built-in button on the AtomS3 Lite:

* **Single Click:** Toggle Play / Stop
  * 🟢 **Green:** Stopped
  * 🔵 **Blue:** Playing
* **Long Press (Hold):** Adjust Volume (Non-linear smooth transition)
  * 🟡 **Yellow:** Adjusting Volume (Cycles smoothly between min and max volume)

> **Note on Volume Control:**  
> Volume changes dynamically following a cosine wave (S-curve) profile, making volume shifts feel natural and smooth to human hearing. Releasing the button sets the current volume.

## Features

* **Real-time Pink Noise:** Generates 16-bit mono, 16 kHz Paul Kellet pink noise dynamically via I2S using hardware TRNG (`os.urandom`).
* **Smooth Smooth-Curve Volume Control:** Intuitive 1-button volume adjustment using a non-blocking button state machine and cosine interpolation.
* **Zero External Dependencies:** Includes a custom `SimpleLED` class utilizing `machine.bitstream` (no `neopixel` library required).
* **Stable Audio Processing:** Non-blocking input processing to ensure crackle-free audio playback during button presses.

## Quick Start

1. Flash **MicroPython** firmware to your AtomS3 Lite.
2. Stack the **Atomic SPK Base** and **ATOM TailBAT** onto the AtomS3 Lite.
3. Upload `main.py` (or the script) to the device and run it.

---

## FAQ

**Q. How do I change the volume?**  
A. While playing audio, simply **press and hold** the built-in button. The LED will turn **Yellow**, and the volume will smoothly sweep up and down. Release the button when it reaches your desired volume.

**Q. Can I use standard earphones?**  
A. Yes! This player is tuned to work well even with standard, low-cost earphones (like typical 100-yen shop ones). No special high-impedance headphones are required—just plug in and enjoy.

About Earphones:
This player is tuned to work well even with standard, low-cost earphones (like typical 100-yen shop ones). No special high-impedance headphones are required—just plug in and enjoy.
