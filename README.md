# AtomS3 Lite Pink-Noise Player

A portable MicroPython script that generates real-time Paul Kellet pink noise for the M5Stack AtomS3 Lite (paired with Atomic SPK Base and ATOM TailBAT).

## Hardware Setup

- **Main Unit:** M5Stack AtomS3 Lite
- **Audio Output:** Atomic SPK Base – I2S audio module with a built-in 3.5mm headphone jack for private listening
- **Power Source:** ATOM TailBAT (Portable setup)

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

- **Single Click:** Toggle Play / Stop / Wake up
  - 🟢 **Green:** Stopped
  - 🔵 **Blue:** Playing
- **Double Click:** Start 30-Minute Off-Timer
  - 🟣 **Pink:** Timer Active (Plays for 30 minutes, then stops automatically)
- **Long Press (Hold):** Adjust Volume (Non-linear smooth transition)
  - 🟡 **Yellow:** Adjusting Volume (Cycles smoothly between min and max volume)

> **Note on Volume Control:**
> Volume changes dynamically following a cosine wave (S-curve) profile, making volume shifts feel natural and smooth to human hearing. Releasing the button sets the current volume.

## Power Management & Sleep Cycle

To eliminate idle background hum and conserve battery, the device features an automated power-down sequence:

1. **Timer Expiration:** After 30 minutes of playback, audio stops immediately and I2S is deallocated to ensure complete silence.
2. **1-Minute Standby Mode (⚪ Dim White LED):** The device enters a light standby mode for 60 seconds, allowing you to easily resume playback with a single click.
3. **Deep Sleep Transition:** If inactive for 1 minute in standby, the LED turns off and the device enters Deep Sleep (ultra-low power state).
4. **Instant Wake-up:** Pressing the built-in button (GPIO 41) instantly wakes the device from Deep Sleep, returning it to the initial stopped state (🟢 Green LED).

## Features

- **Real-time Pink Noise:** Generates 16-bit mono, 16 kHz Paul Kellet pink noise dynamically via I2S using hardware TRNG (`os.urandom`).
- **Smooth Volume Control:** Intuitive 1-button volume adjustment using a non-blocking state machine and cosine interpolation.
- **Smart Power Saving:** Automated transition from Playback → 1-min Standby → Deep Sleep with GPIO wake-up.
- **Zero External Dependencies:** Includes a custom `SimpleLED` class utilizing `machine.bitstream` (no `neopixel` library required).
- **Crackle-Free Audio:** Non-blocking button logic ensuring uninterrupted sound during control interactions.

## Quick Start

1. Flash MicroPython firmware to your AtomS3 Lite.
2. Stack the Atomic SPK Base and ATOM TailBAT onto the AtomS3 Lite.
3. Upload `main.py` (or the script) to the device and run it.

## FAQ

**Q. How do I set the sleep timer?**  
A. Double-click the button while playing. The LED will turn **Pink**, indicating that the 30-minute timer has started. Single-clicking during timer mode cancels the timer and continues normal playback.

**Q. How do I change the volume?**  
A. While playing audio, press and hold the built-in button. The LED will turn **Yellow**, and the volume will smoothly sweep up and down. Release the button when it reaches your desired volume.

**Q. How do I wake the device from Deep Sleep?**  
A. Simply click the built-in button once. The device will reset and boot up into the stopped state (🟢 Green LED).

**Q. Can I use standard earphones?**  
A. Yes! This player is tuned to work well even with standard, low-cost earphones (like typical 100-yen shop ones). No special high-impedance headphones are required—just plug in and enjoy.
