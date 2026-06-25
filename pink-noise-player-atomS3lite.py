import os
import struct
import time
import machine
from machine import I2S, Pin

# ==========================================
# 設定
# ==========================================
BCLK_PIN = 5   # Bit Clock
DATA_PIN = 38  # Data Out
WS_PIN = 39    # LRCK (Word Select)
BTN_PIN = 41   # AtomS3 Lite 本体ボタン
LED_PIN = 35   # AtomS3 Lite 内蔵LEDピン

VOLUME = 1200  # 音量 (0〜32767)

# ==========================================
# カスタムLED制御 (neopixelモジュール不要版)
# ==========================================
# 外部モジュールを使わず、標準のパルス送信機能で直接LEDを光らせます
class SimpleLED:
    def __init__(self, pin_num):
        self.pin = Pin(pin_num, Pin.OUT)
        self.buf = bytearray(3)
        
    def set_color(self, r, g, b):
        # WS2812は 緑(G)→赤(R)→青(B) の順番でデータを送る仕様
        self.buf[0] = g
        self.buf[1] = r
        self.buf[2] = b
        # machine.bitstream機能を使ってLED信号を直接送信
        machine.bitstream(self.pin, 0, (400, 850, 800, 450), self.buf)

# ==========================================
# I2S・ボタン・LEDの初期化
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

# 自作したLEDクラスを初期化
led = SimpleLED(LED_PIN)

# LEDの色定義 (R, G, B)
COLOR_STOP = (0, 30, 0)   # 停止中：緑
COLOR_PLAY = (0, 0, 30)   # 再生中：青

# 起動直後は停止状態なので「緑」を点灯
led.set_color(*COLOR_STOP)

CHUNK_SAMPLES = 2048
CHUNK_BYTES = CHUNK_SAMPLES * 2
noise_buf = bytearray(CHUNK_BYTES)
silent_buf = bytearray(CHUNK_BYTES)

filter_state = [0, 0, 0, 0, 0, 0, 0]

# ==========================================
# ピンクノイズ生成関数 (Paul Kelletアルゴリズム)
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
# メインループ
# ==========================================
is_playing = False
_urandom = os.urandom

print("準備完了：AtomS3 Liteのボタンで再生/停止（LED連動）")

while True:
    if button.value() == 0:
        time.sleep_ms(50)
        if button.value() == 0:
            is_playing = not is_playing
            
            if is_playing:
                print("ピンクノイズ再生中...")
                led.set_color(*COLOR_PLAY)  # 青色に変更
            else:
                print("停止しました")
                led.set_color(*COLOR_STOP)  # 緑色に変更
                
            while button.value() == 0:
                time.sleep_ms(10)
                
    if is_playing:
        generate_paul_kellet_noise(_urandom(CHUNK_SAMPLES), noise_buf, VOLUME, filter_state)
        audio_out.write(noise_buf)
    else:
        audio_out.write(silent_buf)