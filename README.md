# AtomS3 Lite Focus Sound & Pink Noise Player

A portable MicroPython pink noise and focus sound player for the M5Stack AtomS3 Lite (paired with Atomic SPK Base and ATOM TailBAT).

This repository contains **two versions** of the player depending on your preference for simplicity or multi-phase audio generation:

1. **`pink-noise-player-atomS3lite.py` (Standard / Simple Version):**  
   A dedicated, straightforward pink noise machine. Focuses purely on continuous Paul Kellet pink noise with a standard 30-minute sleep timer and smooth volume control.
2. **`pink-noise-player-atomS3lite-alt.py` (Focus Sound Mix / Feature-Rich Version):**  
   An advanced 30-minute focus session generator that smoothly crossfades from pure Pink Noise into realistic Ambient Rain sound before fading out into sleep.

---

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

---

## Version Comparison & How to Choose

### 1. Simple Version (`pink-noise-player-atomS3lite.py`)
*If you prefer a classic, distraction-free noise machine for sleep or pure study, use this code.*

* **Single Click:** Toggle Play / Stop / Exit Standby
  * 🟢 **Emerald Green:** Stopped / Initial State
  * 🔵 **Sapphire Blue:** Continuous Pink Noise
* **Double Click:** Start 30-Minute Sleep Timer
  * 🟣 **Magenta Pink:** Timer Active (Plays pink noise for 30 min, then 60s fadeout $\rightarrow$ standby)
* **Hold Button:** Adjust Volume (Smooth S-curve cosine profile)
  * 🟡 **Amber Yellow:** Adjusting Volume

---

### 2. Focus Sound Mix Version (`pink-noise-player-atomS3lite-alt.py`)
*If you want a dynamic focus session that transitions into relaxing rain sound, use this code.*

* **Single Click:** Toggle Continuous Pink Noise / Stop / Exit Standby
  * 🟢 **Emerald Green:** Stopped / Initial State
  * 🔵 **Sapphire Blue:** Continuous Pink Noise
* **Double Click:** Start Focus Sound Mix (30-Minute Structured Session)
  * 🌹 **Rose Pink:** Phase 1 – Pure Pink Noise (0–14 min)
  * 🟢/🌹 **Transition:** Equal-Power Crossfade (14–15 min)
  * 🌲 **Forest Green:** Phase 2 – Ambient Rain Sound (15–29 min)
  * 🌲 **Dimming Green:** Phase 3 – Final Volume Fadeout (29–30 min)
* **Hold Button:** Adjust Volume (Smooth S-curve cosine profile)
  * 🟡 **Amber Yellow:** Adjusting Volume

#### Focus Sound Mix Timeline (30-Min Session)
```
[0m] ----------------- [14m] ------- [15m] ----------------- [29m] ------- [30m]
      Pink Noise           Crossfade       Ambient Rain         Fadeout     Light Sleep
      (Rose Pink)          (Pink->Green)   (Forest Green)       (Dimming)   (Off)
```

---

## Power Management & Sleep Cycle

Both versions include automatic power-down logic designed to conserve battery on the ATOM TailBAT and eliminate idle speaker hum:

1. **Session Completion:** After timer/session expiration, hardware audio is safely deinitialized (`audio_out.deinit()`) with a silent buffer flush to prevent pop noise.
2. **Pre-sleep Standby Mode (⚪ Muted White LED):** Brief stabilization period before sleep.
3. **Low-Power Sleep (LED OFF):** Deep sleep (Simple Version) or Light Sleep with pin leakage protection (Focus Sound Mix Version).
4. **Instant Wake-up & Reset:** Pressing the built-in button (GPIO 41) triggers a hardware interrupt, waking and resetting the device to its initial stopped state (🟢 Emerald Green LED).

---

## Quick Start

1. Flash MicroPython firmware to your M5Stack AtomS3 Lite.
2. Stack the Atomic SPK Base and ATOM TailBAT onto the AtomS3 Lite.
3. Choose your preferred script:
   - For pure & simple pink noise: Upload `pink-noise-player-atomS3lite.py` (rename to `main.py`).
   - For the multi-phase sound mix: Upload `pink-noise-player-atomS3lite-alt.py` (rename to `main.py`).
4. Run the code and enjoy!

---

## FAQ

**Q. How do I change the volume?**  
A. While audio is playing in either version, press and hold the built-in button. The LED turns **Amber Yellow**, and the volume sweeps up and down smoothly following a cosine curve. Release the button at your desired level.

**Q. Which version should I use for sleeping?**  
A. The **Simple Version** (`pink-noise-player-atomS3lite.py`) is recommended for sleeping, as it maintains a constant, uninterrupted sound profile until fading out. The **Focus Sound Mix Version** (`pink-noise-player-atomS3lite-alt.py`) is ideal for work, study, or meditation sessions.

**Q. Can I test the Focus Sound Mix timeline quickly?**  
A. Yes! Open `pink-noise-player-atomS3lite-alt.py` and set `TEST_MODE = True`. This compresses the 30-minute session into a 30-second run (15s phases + 3s transitions) for rapid verification.
