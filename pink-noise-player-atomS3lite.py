import os
import struct
import time
import machine
import math
from machine import I2S, Pin

# ==========================================
# Configuration
# ==========================================
BCLK_PIN = 5   # Bit Clock
DATA_PIN = 38  # Data Out
WS_PIN = 39    # LRCK (Word Select)
BTN_PIN = 41   # AtomS3 Lite built-in button
LED_PIN = 35   # AtomS3 Lite built-in RGB LED pin

VOLUME_MIN = 0
VOLUME_MAX = 1500
VOLUME_STEP = 50

# ==========================================
# Custom LED Controller (No neopixel module required)
# ==========================================
# Directly controls the RGB LED using standard bitstream functionality 
# without relying on external libraries.
class SimpleLED:
    def __init__(self, pin_num):
        self.pin = Pin(pin_num, Pin.OUT)
        self.buf = bytearray(3)
        
    def set_color(self, r, g, b, brightness=1.0):
        # WS2812 expects data in Green -> Red -> Blue (GRB) order
        self.buf[0] = int(g * brightness)
        self.buf[1] = int(r * brightness)
        self.buf[2] = int(b * brightness)
        # Send raw timing signals using machine.bitstream
        machine.bitstream(self.pin, 0, (400, 850, 800, 450), self.buf)

# ==========================================
# Non-blocking Button Handler
# ==========================================
class ButtonHandler:
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
        
        if val == 0: # Pressed
            if self.state == 0: # Just pressed
                self.press_time = now
                self.state = 1
                self.long_press_triggered = False
            elif self.state == 1: # Holding
                if not self.long_press_triggered and time.ticks_diff(now, self.press_time) > 1000:
                    self.long_press_triggered = True
                    event = 'LONG'
                elif self.long_press_triggered:
                    event = 'HOLDING'
            elif self.state == 2: # Second press (Double click detected early)
                self.state = 3
        else: # Released
            if self.state == 1:
                self.release_time = now
                if not self.long_press_triggered:
                    self.state = 2 # Wait to see if it's a double click
                else:
                    self.state = 0 # End of long press
            elif self.state == 2:
                if time.ticks_diff(now, self.release_time) > 250: # Timeout -> Single click
                    self.state = 0
                    event = 'SINGLE'
            elif self.state == 3: # Released after double click
                self.state = 0
                event = 'DOUBLE'
                
        return event


# ==========================================
# Initialize I2S, Button, and LED
# ==========================================
audio_out = I2S(
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

btn = ButtonHandler(BTN_PIN)

# Initialize custom LED instance
led = SimpleLED(LED_PIN)

# LED color definitions (R, G, B)
COLOR_STOP = (0, 5, 0)    # Stopped state: Green (Dimmed for power saving)
COLOR_PLAY = (0, 0, 5)    # Playing state: Blue (Dimmed for power saving)
COLOR_VOL = (10, 10, 0)   # Volume adjust: Yellow

# Set initial status to Green (Stopped)
led.set_color(*COLOR_STOP)

CHUNK_SAMPLES = 2048
CHUNK_BYTES = CHUNK_SAMPLES * 2
noise_buf = bytearray(CHUNK_BYTES)
silent_buf = bytearray(CHUNK_BYTES)

filter_state = [0, 0, 0, 0, 0, 0, 0]

# ==========================================
# Pink Noise Generator (Paul Kellet Algorithm)
# ==========================================
def generate_paul_kellet_noise(raw_bytes, out_buf, vol, state):
    _b0, _b1, _b2, _b3, _b4, _b5, _b6 = state
    _pack_into = struct.pack_into
    
    for i in range(len(raw_bytes)):
        white = raw_bytes[i] - 128
        
        _b0 = (32731 * _b0 + 1819 * white) >> 15
        _b1 = (32549 * _b1 + 2460 * white) >> 15
        _b2 = (31752 * _b2 + 5041 * white) >> 15
        _b3 = (28393 * _b3 + 10174 * white) >> 15
        _b4 = (18022 * _b4 + 17464 * white) >> 15
        _b5 = (-24956 * _b5 - 554 * white) >> 15
        
        out = _b0 + _b1 + _b2 + _b3 + _b4 + _b5 + _b6 + ((white * 17570) >> 15)
        _b6 = (white * 3798) >> 15
        
        out = (out * vol) >> 9
        
        if out > 32767: out = 32767
        elif out < -32768: out = -32768
        
        _pack_into('<h', out_buf, i * 2, out)
        
    state[0] = _b0; state[1] = _b1; state[2] = _b2
    state[3] = _b3; state[4] = _b4; state[5] = _b5; state[6] = _b6

# ==========================================
# Main Loop
# ==========================================
is_playing = False
current_volume = 1200
vol_phase = math.acos(1 - 2 * (current_volume - VOLUME_MIN) / (VOLUME_MAX - VOLUME_MIN))
vol_direction = 1
_urandom = os.urandom

print("Ready: Press AtomS3 Lite button to Play/Stop (LED status active)")

while True:
    event = btn.update()
    
    if event == 'SINGLE':
        is_playing = not is_playing
        if is_playing:
            print(f"Playing pink noise... (Vol: {current_volume})")
        else:
            print("Stopped")
            
    elif event == 'HOLDING':
        if is_playing:
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
        if is_playing:
            vol_direction = 1
            
    # LED Updates
    if event == 'HOLDING' or event == 'LONG':
        if is_playing:
            led.set_color(*COLOR_VOL)
    else:
        if is_playing:
            led.set_color(*COLOR_PLAY)
        else:
            led.set_color(*COLOR_STOP)
                
    if is_playing:
        generate_paul_kellet_noise(_urandom(CHUNK_SAMPLES), noise_buf, current_volume, filter_state)
        audio_out.write(noise_buf)
    else:
        audio_out.write(silent_buf)