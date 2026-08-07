import os
import struct
import time
import machine
from machine import I2S, Pin

# ==========================================
# Configuration
# ==========================================
BCLK_PIN = 5
DATA_PIN = 38
WS_PIN = 39
BTN_PIN = 41
LED_PIN = 35

VOLUME = 1200          # 0〜32767
SAMPLE_RATE = 16000
NUM_GENERATORS = 10    # 8〜12推奨（多いほど低域が良くなるが負荷増）

# ==========================================
# Custom LED Controller
# ==========================================
class SimpleLED:
    def __init__(self, pin_num):
        self.pin = Pin(pin_num, Pin.OUT)
        self.buf = bytearray(3)
        
    def set_color(self, r, g, b):
        self.buf[0] = g
        self.buf[1] = r
        self.buf[2] = b
        machine.bitstream(self.pin, 0, (400, 850, 800, 450), self.buf)

# ==========================================
# Initialize
# ==========================================
audio_out = I2S(
    0,
    sck=Pin(BCLK_PIN),
    ws=Pin(WS_PIN),
    sd=Pin(DATA_PIN),
    mode=I2S.TX,
    bits=16,
    format=I2S.MONO,
    rate=SAMPLE_RATE,
    ibuf=8192
)

button = Pin(BTN_PIN, Pin.IN, Pin.PULL_UP)
led = SimpleLED(LED_PIN)

COLOR_STOP = (0, 30, 0)
COLOR_PLAY = (0, 0, 30)
led.set_color(*COLOR_STOP)

CHUNK_SAMPLES = 2048
CHUNK_BYTES = CHUNK_SAMPLES * 2
noise_buf = bytearray(CHUNK_BYTES)
silent_buf = bytearray(CHUNK_BYTES)

# ==========================================
# Voss-McCartney Pink Noise Generator
# ==========================================
class VossMcCartney:
    def __init__(self, num_gens=10):
        self.num_gens = num_gens
        self.generators = [0] * num_gens   # 各生成器の現在値
        self.running_sum = 0
        self.counter = 0
        self._urandom = os.urandom
        
        # 初期化（最初の値を入れておく）
        for i in range(num_gens):
            val = self._random_white()
            self.generators[i] = val
            self.running_sum += val

    def _random_white(self):
        # -128〜127のホワイトノイズを返す
        return self._urandom(1)[0] - 128

    def _trailing_zeros(self, n):
        # 末尾のゼロの数を数える（どの生成器を更新するか決める）
        if n == 0:
            return self.num_gens - 1
        count = 0
        while (n & 1) == 0:
            n >>= 1
            count += 1
            if count >= self.num_gens:
                break
        return count

    def generate(self, out_buf, vol):
        _pack_into = struct.pack_into
        gens = self.generators
        sum_val = self.running_sum
        cnt = self.counter
        n_gens = self.num_gens
        
        for i in range(CHUNK_SAMPLES):
            # どの生成器を更新するか
            idx = self._trailing_zeros(cnt)
            
            # 古い値を引いて新しい値を足す
            old = gens[idx]
            new = self._random_white()
            gens[idx] = new
            sum_val = sum_val - old + new
            
            # 毎サンプルのホワイトノイズも少し混ぜると高域が改善する（オプション）
            white = self._random_white()
            out = sum_val + white
            
            # 音量調整とクリッピング
            out = (out * vol) >> 8   # スケールは要調整
            
            if out > 32767:
                out = 32767
            elif out < -32768:
                out = -32768
            
            _pack_into('<h', out_buf, i * 2, out)
            
            cnt += 1
        
        self.running_sum = sum_val
        self.counter = cnt

# インスタンス生成
pink_gen = VossMcCartney(NUM_GENERATORS)

# ==========================================
# Main Loop
# ==========================================
is_playing = False

print("Ready: Press button to Play/Stop (Voss-McCartney)")

while True:
    if button.value() == 0:
        time.sleep_ms(50)
        if button.value() == 0:
            is_playing = not is_playing
            
            if is_playing:
                print("Playing pink noise (Voss-McCartney)...")
                led.set_color(*COLOR_PLAY)
            else:
                print("Stopped")
                led.set_color(*COLOR_STOP)
                
            while button.value() == 0:
                time.sleep_ms(10)
                
    if is_playing:
        pink_gen.generate(noise_buf, VOLUME)
        audio_out.write(noise_buf)
    else:
        audio_out.write(silent_buf)