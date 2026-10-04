import os
import struct
import time
import machine
import esp32
import math
from machine import I2S, Pin

# ==========================================
# System Configuration & Pin Assignments
# ==========================================
BCLK_PIN = 5   # I2S Bit Clock
DATA_PIN = 38  # I2S Data Out
WS_PIN = 39    # I2S Word Select (LRCK)
BTN_PIN = 41   # Built-in Push Button
LED_PIN = 35   # Built-in RGB LED (WS2812)

VOLUME_MIN = 0
VOLUME_MAX = 1500
VOLUME_STEP = 50

# ------------------------------------------
# Application State Definitions
# ------------------------------------------
STATE_STOPPED = 0   # Playback stopped
STATE_PLAYING = 1   # Active playback
STATE_TIMER   = 2   # Sleep timer running
STATE_FADEOUT = 3   # Gradual volume fadeout
STATE_STANDBY = 4   # Low-power standby awaiting sleep

# ==========================================
# Custom WS2812 LED Driver
# ==========================================
class SimpleLED:
    """Bare-metal RGB LED controller using hardware bitstream generation."""
    def __init__(self, pin_num):
        self.pin = Pin(pin_num, Pin.OUT)
        self.buf = bytearray(3)
        
    def set_color(self, r, g, b, brightness=1.0):
        # WS2812 protocol requires GRB byte order
        self.buf[0] = int(g * brightness)
        self.buf[1] = int(r * brightness)
        self.buf[2] = int(b * brightness)
        machine.bitstream(self.pin, 0, (400, 850, 800, 450), self.buf)

# ==========================================
# Asynchronous Button Event Detector
# ==========================================
class ButtonHandler:
    """Non-blocking debounced button handler with multi-click detection."""
    def __init__(self, pin_num):
        self.pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
        self.state = 0
        self.press_time = 0
        self.release_time = 0
        self.long_press_triggered = False
        
    def update(self):
        now = time.ticks_ms()
        val = self.pin.value()
        event = None
        
        if val == 0:  # Button active (LOW)
            if self.state == 0:
                self.press_time = now
                self.state = 1
                self.long_press_triggered = False
            elif self.state == 1:
                if not self.long_press_triggered and time.ticks_diff(now, self.press_time) > 1000:
                    self.long_press_triggered = True
                    event = 'LONG'
                elif self.long_press_triggered:
                    event = 'HOLDING'
            elif self.state == 2:
                self.state = 3
        else:  # Button released (HIGH)
            if self.state == 1:
                self.release_time = now
                if not self.long_press_triggered:
                    self.state = 2
                else:
                    self.state = 0
            elif self.state == 2:
                if time.ticks_diff(now, self.release_time) > 250:
                    self.state = 0
                    event = 'SINGLE'
            elif self.state == 3:
                self.state = 0
                event = 'DOUBLE'
                
        return event

# ==========================================
# Peripheral Initialization
# ==========================================
def init_i2s():
    """Configure and initialize the hardware I2S peripheral."""
    return I2S(
        0,
        sck=Pin(BCLK_PIN),
        ws=Pin(WS_PIN),
        sd=Pin(DATA_PIN),
        mode=I2S.TX,
        bits=16,
        format=I2S.MONO,
        rate=16000,
        ibuf=8192
    )

audio_out = init_i2s()
btn = ButtonHandler(BTN_PIN)
led = SimpleLED(LED_PIN)

# Color Palette Definitions (R, G, B)
COLOR_STOP    = (0, 5, 0)    # Emerald Green (Stopped)
COLOR_PLAY    = (0, 0, 5)    # Sapphire Blue (Playing)
COLOR_VOL     = (10, 10, 0)  # Amber Yellow  (Volume Adjust)
COLOR_TIMER   = (10, 0, 5)   # Magenta Pink  (Timer Active)
COLOR_STANDBY = (2, 2, 2)   # Muted White   (Standby Mode)

led.set_color(*COLOR_STOP)

CHUNK_SAMPLES = 2048
CHUNK_BYTES = CHUNK_SAMPLES * 2
noise_buf = bytearray(CHUNK_BYTES)
silent_buf = bytearray(CHUNK_BYTES)

filter_state = [0, 0, 0, 0, 0, 0, 0]

# ==========================================
# Audio DSP Core: Paul Kellet Pink Noise
# ==========================================
def generate_paul_kellet_noise(raw_bytes, out_buf, vol, state):
    """Generate 16-bit pink noise using Paul Kellet's IIR filter array."""
    _b0, _b1, _b2, _b3, _b4, _b5, _b6 = state
    _pack_into = struct.pack_into
    
    for i in range(len(raw_bytes)):
        white = raw_bytes[i] - 128
        
        # Cascaded IIR filter calculation (Fixed-point arithmetic)
        _b0 = (32731 * _b0 + 1819 * white) >> 15
        _b1 = (32549 * _b1 + 2460 * white) >> 15
        _b2 = (31752 * _b2 + 5041 * white) >> 15
        _b3 = (28393 * _b3 + 10174 * white) >> 15
        _b4 = (18022 * _b4 + 17464 * white) >> 15
        _b5 = (-24956 * _b5 - 554 * white) >> 15
        
        out = _b0 + _b1 + _b2 + _b3 + _b4 + _b5 + _b6 + ((white * 17570) >> 15)
        _b6 = (white * 3798) >> 15
        
        # Volume scaling
        out = (out * vol) >> 9
        
        # Hard clipping protection
        if out > 32767: out = 32767
        elif out < -32768: out = -32768
        
        _pack_into('<h', out_buf, i * 2, out)
        
    state[0] = _b0; state[1] = _b1; state[2] = _b2
    state[3] = _b3; state[4] = _b4; state[5] = _b5; state[6] = _b6

# ==========================================
# Application Runtime & Finite State Machine
# ==========================================
current_state = STATE_STOPPED

current_volume = 1200
vol_phase = math.acos(1 - 2 * (current_volume - VOLUME_MIN) / (VOLUME_MAX - VOLUME_MIN))
vol_direction = 1
_urandom = os.urandom

timer_start_ms = 0
TIMER_DURATION_MS = 30 * 60 * 1000  # 30-minute operational timeout

fadeout_start_ms = 0
fadeout_start_vol = 0
FADEOUT_DURATION_MS = 60 * 1000     # 60-second fadeout duration

standby_start_ms = 0

print("[SYS] Initialization complete. Entering main state loop.")

while True:
    event = btn.update()
    
    # ----------------------------------------------------
    # 1. Finite State Transitions (Button Events)
    # ----------------------------------------------------
    if event == 'SINGLE':
        if current_state == STATE_STANDBY:
            current_state = STATE_STOPPED
            audio_out = init_i2s()
            print("[EVENT] Standby exited -> STATE_STOPPED")
        elif current_state in (STATE_TIMER, STATE_FADEOUT):
            if current_state == STATE_FADEOUT:
                current_volume = fadeout_start_vol
            current_state = STATE_PLAYING
            print("[EVENT] Timer/Fadeout overridden -> STATE_PLAYING")
        elif current_state == STATE_PLAYING:
            current_state = STATE_STOPPED
            print("[EVENT] Playback toggled -> STATE_STOPPED")
        elif current_state == STATE_STOPPED:
            current_state = STATE_PLAYING
            print(f"[EVENT] Playback toggled -> STATE_PLAYING (Vol: {current_volume})")
            
    elif event == 'DOUBLE':
        if current_state == STATE_PLAYING:
            current_state = STATE_TIMER
            timer_start_ms = time.ticks_ms()
            print("[EVENT] Timer triggered -> STATE_TIMER (30m)")
            
    elif event == 'HOLDING':
        if current_state in (STATE_PLAYING, STATE_TIMER, STATE_FADEOUT):
            phase_step = math.pi / ((VOLUME_MAX - VOLUME_MIN) / VOLUME_STEP)
            vol_phase += phase_step * vol_direction
            
            if vol_phase >= math.pi:
                vol_phase = math.pi
                vol_direction = -1
            elif vol_phase <= 0:
                vol_phase = 0
                vol_direction = 1
                
            current_volume = int(VOLUME_MIN + (VOLUME_MAX - VOLUME_MIN) * (1 - math.cos(vol_phase)) / 2)
                
    elif event == 'LONG':
        if current_state in (STATE_PLAYING, STATE_TIMER, STATE_FADEOUT):
            vol_direction = 1

    # ----------------------------------------------------
    # 2. Automated State Transitions (Timer & Lifecycle)
    # ----------------------------------------------------
    now_ms = time.ticks_ms()
    
    if current_state == STATE_TIMER:
        if time.ticks_diff(now_ms, timer_start_ms) >= TIMER_DURATION_MS:
            print("[STATE] Timer elapsed -> STATE_FADEOUT")
            current_state = STATE_FADEOUT
            fadeout_start_ms = now_ms
            fadeout_start_vol = current_volume

    elif current_state == STATE_FADEOUT:
        elapsed = time.ticks_diff(now_ms, fadeout_start_ms)
        if elapsed >= FADEOUT_DURATION_MS:
            print("[STATE] Fadeout completed -> STATE_STANDBY")
            current_state = STATE_STANDBY
            standby_start_ms = now_ms
            
            # Flush pipeline with silence before disabling hardware audio
            for _ in range(10):
                audio_out.write(silent_buf)
            audio_out.deinit()
        else:
            ratio = elapsed / FADEOUT_DURATION_MS
            current_volume = int(fadeout_start_vol * (1.0 - ratio))

    elif current_state == STATE_STANDBY:
        if time.ticks_diff(now_ms, standby_start_ms) >= 60000:
            print("[POWER] Standby timeout -> Entering Deep Sleep")
            led.set_color(0, 0, 0)
            wake_pin = Pin(BTN_PIN, Pin.IN, Pin.PULL_UP)
            try:
                esp32.wake_on_ext0(pin=wake_pin, level=esp32.WAKEUP_ALL_LOW)
            except Exception as e:
                print("[WARN] Wake configuration failed:", e)
            time.sleep_ms(100)
            machine.deepsleep()

    # ----------------------------------------------------
    # 3. Peripheral Hardware Dispatch (LED & Audio Output)
    # ----------------------------------------------------
    # --- Status LED Dispatch ---
    if event in ('HOLDING', 'LONG') and current_state in (STATE_PLAYING, STATE_TIMER, STATE_FADEOUT):
        led.set_color(*COLOR_VOL)
    elif current_state == STATE_STOPPED:
        led.set_color(*COLOR_STOP)
    elif current_state == STATE_PLAYING:
        led.set_color(*COLOR_PLAY)
    elif current_state in (STATE_TIMER, STATE_FADEOUT):
        led.set_color(*COLOR_TIMER)
    elif current_state == STATE_STANDBY:
        led.set_color(*COLOR_STANDBY)

    # --- Audio Pipeline Dispatch ---
    if current_state in (STATE_PLAYING, STATE_TIMER, STATE_FADEOUT):
        generate_paul_kellet_noise(_urandom(CHUNK_SAMPLES), noise_buf, current_volume, filter_state)
        audio_out.write(noise_buf)
    elif current_state == STATE_STOPPED:
        audio_out.write(silent_buf)
    elif current_state == STATE_STANDBY:
        time.sleep_ms(20)