# AtomS3 Lite Focus Sound & Pink Noise Player

A portable MicroPython script that generates real-time Paul Kellet pink noise and realistic ambient rain sound for the M5Stack AtomS3 Lite (paired with Atomic SPK Base and ATOM TailBAT).

Features dynamic sound synthesis, seamless equal-power crossfading, multi-phase focus timer, and low-power standby modes.

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

- **Single Click:** Toggle Continuous Pink Noise Playback / Stop / Exit Standby
  - 🟢 **Emerald Green:** Stopped / Initial State
  - 🔵 **Sapphire Blue:** Continuous Pink Noise Playback
- **Double Click:** Start Focus Sound Mix (30-Minute Session)
  - 🌹 **Rose Pink:** Phase 1 – Pink Noise (0–14 min)
  - 🟢/🌹 **Transition:** Equal-power Crossfade (14–15 min)
  - 🌲 **Forest Green:** Phase 2 – Ambient Rain Noise (15–29 min)
  - 🌲 **Dimming Green:** Phase 3 – Final Fadeout (29–30 min)
- **Long Press (Hold):** Adjust Volume (Non-linear smooth transition)
  - 🟡 **Amber Yellow:** Adjusting Volume (Cycles smoothly between min and max volume)

> **Note on Volume Control:**
> Volume changes dynamically following a cosine wave (S-curve) profile, making volume shifts feel natural and smooth to human hearing. Releasing the button locks in the current volume setting.

---

## Focus Sound Mix (30-Minute Timer Mode)

Double-clicking the button starts a structured **30-minute focus and relaxation sequence**:

```
[0m] ----------------- [14m] ------- [15m] ----------------- [29m] ------- [30m]
      Pink Noise           Crossfade       Ambient Rain         Fadeout     Light Sleep
      (Rose Pink)          (Pink->Green)   (Forest Green)       (Dimming)   (Off)
```

1. **Phase 1 (0 to 14 min):** High-focus Pink Noise to block distractions.
2. **Crossfade Phase (14 to 15 min):** 60-second seamless equal-power crossfade ($g_A^2 + g_B^2 = 1$) from Pink Noise to Ambient Rain.
3. **Phase 2 (15 to 29 min):** Relaxing Ambient Rain noise with dynamic low-frequency oscillations (LFO) simulating gentle wind and rain swells.
4. **Phase 3 (29 to 30 min):** Smooth 60-second exponential volume fadeout and synchronized LED dimming.
5. **Standby & Light Sleep:** The audio safely deinitializes, avoiding pops, and transitions into a 24-hour light sleep state.

---

## Power Management & Sleep Cycle

To eliminate background noise and preserve battery on the ATOM TailBAT:

1. **Session Completion:** After the 30-minute Focus Sound Mix finishes, audio output is deactivated and pins are reconfigured to input mode to eliminate leakage current.
2. **Pre-sleep Standby Mode (⚪ Muted White LED):** Brief stabilization period prior to entering sleep.
3. **24-Hour Light Sleep Mode (LED OFF):** Low-power hardware standby. 
4. **Instant Wake-up & Reset:** Pressing the built-in button (GPIO 41) immediately triggers a hardware wake-up interrupt and resets the device back to the initial stopped state (🟢 Emerald Green LED). Alternatively, turn off the power switch on the TailBAT for a complete shutdown.

---

## Advanced Features & DSP Core

- **Paul Kellet 7-Pole Pink Noise:** DSP filter generating high-quality 16-bit 16kHz mono pink noise dynamically from hardware TRNG (`os.urandom`).
- **Cascaded Ambient Rain Synthesizer:** Real-time rain simulation combining a 1st-stage LPF (~900Hz shower body), 2nd-stage LPF (~350Hz distant rumble), high-pass droplet texture, and a 0.08Hz LFO swell generator.
- **Single-Pass Equal-Power Crossfade:** Custom integer-math synthesis engine ensuring constant perceived volume during noise transitions without audio dropouts.
- **Verification / Test Mode:** Includes a `TEST_MODE` flag in the script configuration to compress the 30-minute timeline into a 30-second test run (15s phases + 3s transitions) for rapid debugging.
- **Custom WS2812 Driver:** Lightweight `SimpleLED` implementation using native `machine.bitstream` (no external `neopixel` package required).

---

## Quick Start

1. Flash MicroPython firmware (v1.19 or later recommended) to your M5Stack AtomS3 Lite.
2. Stack the Atomic SPK Base and ATOM TailBAT onto the AtomS3 Lite.
3. Upload `pink-noise-player-atomS3lite-alt.py` to the device (rename to `main.py` for auto-boot) and run.

---

## FAQ

**Q. How do I enable the 30-second verification mode?**  
A. Set `TEST_MODE = True` near the top of the python code. This reduces the phase durations to 15 seconds each, allowing quick testing of crossfading, fadeout, and sleep behavior.

**Q. How do I cancel the focus session?**  
A. Single-click the button during a timer session. It will immediately cancel the timeline and switch back to continuous Pink Noise mode (🔵 Blue LED).

**Q. How do I wake the unit after a session finishes?**  
A. Simply press the built-in button. The GPIO interrupt will wake the ESP32-S3 from light sleep and execute a clean hardware reset back to the initial stopped state.
