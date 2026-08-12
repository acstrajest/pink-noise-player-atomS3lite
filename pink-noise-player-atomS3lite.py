import os
import struct
import time
import machine
from machine import I2S, Pin

# ==========================================
# Configuration
# ==========================================
BCLK_PIN = 5   # Bit Clock
DATA_PIN = 38  # Data Out
WS_PIN = 39    # LRCK (Word Select)
BTN_PIN = 41   # AtomS3 Lite built-in button
LED_PIN = 35   # AtomS3 Lite built-in RGB LED pin

VOLUME = 1200  # Volume level (0 to 32767)

# ==========================================
# Custom LED Controller (No neopixel module required)
# ==========================================
# Directly controls the RGB LED using standard bitstream functionality 
# without relying on external libraries.
class SimpleLED:
    def __init__(self, pin_num):
        self.pin = Pin(pin_num, Pin.OUT)
        self.buf = bytearray(3)
        
    def set_color(self, r, g, b):
        # WS2812 expects data in Green -> Red -> Blue (GRB) order
        self.buf[0] = g
        self.buf[1] = r
        self.buf[2] = b
        # Send raw timing signals using machine.bitstream
        machine.bitstream(self.pin, 0, (400, 850, 800, 450), self.buf)

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

button = Pin(BTN_PIN, Pin.IN, Pin.PULL_UP)

# Initialize custom LED instance
led = SimpleLED(LED_PIN)

# LED color definitions (R, G, B)
COLOR_STOP = (0, 5, 0)    # Stopped state: Green (Dimmed for power saving)
COLOR_PLAY = (0, 0, 5)    # Playing state: Blue (Dimmed for power saving)

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
_urandom = os.urandom

print("Ready: Press AtomS3 Lite button to Play/Stop (LED status active)")

while True:
    if button.value() == 0:
        time.sleep_ms(50)
        if button.value() == 0:
            is_playing = not is_playing
            
            if is_playing:
                print("Playing pink noise...")
                led.set_color(*COLOR_PLAY)  # Switch to Blue
            else:
                print("Stopped")
                led.set_color(*COLOR_STOP)  # Switch to Green
                
            while button.value() == 0:
                time.sleep_ms(10)
                
    if is_playing:
        generate_paul_kellet_noise(_urandom(CHUNK_SAMPLES), noise_buf, VOLUME, filter_state)
        audio_out.write(noise_buf)
    else:
        audio_out.write(silent_buf)