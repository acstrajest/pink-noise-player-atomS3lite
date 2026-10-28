import os
import struct
import time
import machine
import math
import random
from machine import I2S, Pin

# ==========================================
# Deep Sleep Configuration
# ==========================================
# セッション終了後、約1日（24時間）スリープ。
# 起床したら何もせず即再スリープする（実質的な停止状態）。
SLEEP_DURATION_MS = 24 * 60 * 60 * 1000  # 86,400,000 ms

# 起床判定は最優先で行う（LED点灯・I2S初期化より前）
if machine.reset_cause() == machine.DEEPSLEEP_RESET:
    # タイマー起床 → 何もせず即再スリープ
    machine.deepsleep(SLEEP_DURATION_MS)

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
# Session Timeline Configuration
# Focus Sound Mix: Pink Noise (15m) -> Ambient Rain (15m) -> Granular (15m) -> Fadeout (60s) -> Deep Sleep
# ------------------------------------------
# TEST_MODE: False = 45分セッション (本番用: 15分×3パート + 各60秒クロスフェード/フェードアウト)
#            True  = 45秒セッション (動作確認用: 15秒×3パート + 各3秒クロスフェード/フェードアウト)
TEST_MODE = False

if TEST_MODE:
    PHASE_DURATION_MS = 15 * 1000     # 15 seconds per sound phase
    CROSSFADE_MS      = 3 * 1000      # 3 seconds crossfade
    FADEOUT_MS        = 3 * 1000      # 3 seconds final fadeout
else:
    PHASE_DURATION_MS = 15 * 60 * 1000  # 15 minutes per sound phase
    CROSSFADE_MS      = 60 * 1000       # 60 seconds crossfade
    FADEOUT_MS        = 60 * 1000       # 60 seconds final fadeout

TOTAL_SESSION_MS = PHASE_DURATION_MS * 3

# Transition milestones
T1_START = PHASE_DURATION_MS - CROSSFADE_MS
T1_END   = PHASE_DURATION_MS
T2_START = PHASE_DURATION_MS * 2 - CROSSFADE_MS
T2_END   = PHASE_DURATION_MS * 2
T3_START = TOTAL_SESSION_MS - FADEOUT_MS
T3_END   = TOTAL_SESSION_MS

# ------------------------------------------
# Application State Definitions
# ------------------------------------------
STATE_STOPPED = 0   # 停止中
STATE_PLAYING = 1   # 通常再生中（シングルクリック: ピンクノイズ常時再生）
STATE_TIMER   = 2   # フォーカスミックスタイマー動作中（ダブルクリック: 45分セッション）
STATE_STANDBY = 3   # ディープスリープ移行前の待機状態

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
COLOR_STOP        = (0, 5, 0)     # エメラルドグリーン (停止中)
COLOR_PLAY        = (0, 0, 5)     # サファイアブルー   (通常ピンクノイズ再生)
COLOR_VOL         = (10, 10, 0)   # アンバーイエロー   (音量調整中)
COLOR_PHASE_PINK  = (12, 2, 5)    # ローズピンク       (タイマー Phase 1: ピンクノイズ)
COLOR_PHASE_ENV   = (1, 10, 3)    # フォレストグリーン (タイマー Phase 2: 環境音・雨)
COLOR_PHASE_GRAIN = (3, 4, 12)    # シアンインディゴ   (タイマー Phase 3: 粒状合成)
COLOR_STANDBY     = (1, 1, 1)     # 薄白色             (スリープ直前待機)

led.set_color(*COLOR_STOP)

CHUNK_SAMPLES = 2048
CHUNK_BYTES = CHUNK_SAMPLES * 2
noise_buf = bytearray(CHUNK_BYTES)
silent_buf = bytearray(CHUNK_BYTES)

# ==========================================
# DSP Core: Filter-based Real-time Generators
# ==========================================

# --- 1. ピンクノイズ生成器 (Paul Kellet 7-pole IIR) ---
pink_filter_state = [0, 0, 0, 0, 0, 0, 0]

def generate_pink_noise(raw_bytes, out_buf, vol, state, scale=256):
    """16ビット・ピンクノイズを直接出力バッファに生成。"""
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
        
        if scale != 256:
            out = (out * scale) >> 8
        out = (out * vol) >> 9
        if out > 32767: out = 32767
        elif out < -32768: out = -32768
        _pack_into('<h', out_buf, i * 2, out)
        
    state[0] = _b0; state[1] = _b1; state[2] = _b2
    state[3] = _b3; state[4] = _b4; state[5] = _b5; state[6] = _b6

# --- 2. 環境音（雨音）生成器 (多段カスケードLPF + 高域テクスチャ + LFOうねり) ---
env_lpf1 = 0
env_lpf2 = 0
env_lfo_phase = 0.0

def generate_env_noise(raw_bytes, out_buf, vol, scale=256):
    """フィルターとLFOスウェルを駆使した自然な雨の環境音を直接出力バッファに生成。"""
    global env_lpf1, env_lpf2, env_lfo_phase
    _pack_into = struct.pack_into
    
    # チャンク周期(~128ms)ごとにLFOを進めて緩やかな雨脚・風のうねりを表現 (~0.08Hz)
    env_lfo_phase += 0.064
    if env_lfo_phase > 628.3:
        env_lfo_phase = 0.0
    lfo_mod = int(256 + 46 * math.sin(env_lfo_phase))  # 0.82 〜 1.18倍のうねり
    
    eff_scale = (scale * lfo_mod) >> 8
    lp1 = env_lpf1
    lp2 = env_lpf2
    
    for i in range(len(raw_bytes)):
        white_in = (raw_bytes[i] - 128) << 6
        
        # 1段目LPF (~900Hz: 雨音の主体)
        lp1 += (10500 * (white_in - lp1)) >> 15
        # 2段目LPF (~350Hz: 遠くの地鳴り・低域の包まれ感)
        lp2 += (4200 * (lp1 - lp2)) >> 15
        # 高域シェルフ成分 (かすかな雨粒の滴り)
        high = (white_in - lp1) >> 4
        
        rain = (lp1 + lp2 + high) >> 1
        out_env = (rain * 22) >> 6
        if eff_scale != 256:
            out_env = (out_env * eff_scale) >> 8
        out = (out_env * vol) >> 9
        
        if out > 32767: out = 32767
        elif out < -32768: out = -32768
        _pack_into('<h', out_buf, i * 2, out)
        
    env_lpf1 = lp1
    env_lpf2 = lp2

# --- 3. 粒状合成（Granular Texture）生成器 (Chamberlin SVF レゾナントフィルターバンク) ---
grain1_f = 1200; grain1_q = 2800; grain1_env = 0; grain1_step = 12; grain1_state = 0
grain2_f = 2400; grain2_q = 3200; grain2_env = 0; grain2_step = 8; grain2_state = 0

grain1_low = 0; grain1_band = 0
grain2_low = 0; grain2_band = 0

def _update_grain_parameters():
    """マイクログレイン（粒子）の周波数とエンベロープ状態を更新。"""
    global grain1_f, grain1_q, grain1_env, grain1_step, grain1_state
    global grain2_f, grain2_q, grain2_env, grain2_step, grain2_state
    
    # グレイン1: 低〜中音域の粒子
    if grain1_state == 0:
        grain1_f = random.randint(600, 2200)
        grain1_q = random.randint(2200, 3600)
        grain1_step = random.randint(18, 36)
        grain1_env = 0
        grain1_state = 1
    elif grain1_state == 1:
        grain1_env += grain1_step * 32
        if grain1_env >= 256:
            grain1_env = 256
            grain1_state = 2
    elif grain1_state == 2:
        grain1_env -= grain1_step * 16
        if grain1_env <= 0:
            grain1_env = 0
            grain1_state = 0
            
    # グレイン2: 中〜高音域の微粒子
    if grain2_state == 0:
        grain2_f = random.randint(1400, 3400)
        grain2_q = random.randint(2400, 4200)
        grain2_step = random.randint(14, 28)
        grain2_env = 0
        grain2_state = 1
    elif grain2_state == 1:
        grain2_env += grain2_step * 32
        if grain2_env >= 256:
            grain2_env = 256
            grain2_state = 2
    elif grain2_state == 2:
        grain2_env -= grain2_step * 14
        if grain2_env <= 0:
            grain2_env = 0
            grain2_state = 0

def generate_granular_noise(raw_bytes, out_buf, vol, scale=256):
    """共振フィルターバンクによる粒子感あふれる粒状合成ノイズを直接出力バッファに生成。"""
    global grain1_low, grain1_band, grain2_low, grain2_band
    _update_grain_parameters()
    _pack_into = struct.pack_into
    
    g1_low = grain1_low; g1_band = grain1_band
    g2_low = grain2_low; g2_band = grain2_band
    f1 = grain1_f; q1 = grain1_q; env1 = grain1_env
    f2 = grain2_f; q2 = grain2_q; env2 = grain2_env
    
    for i in range(len(raw_bytes)):
        white = (raw_bytes[i] - 128) << 7
        
        # レゾナント SVF 1 (State Variable Filter)
        g1_low += (f1 * g1_band) >> 14
        high1 = white - g1_low - ((q1 * g1_band) >> 14)
        g1_band += (f1 * high1) >> 14
        
        # レゾナント SVF 2
        g2_low += (f2 * g2_band) >> 14
        high2 = white - g2_low - ((q2 * g2_band) >> 14)
        g2_band += (f2 * high2) >> 14
        
        # 粒子の包絡線合成と背景ノイズフロアのブレンド
        grain_out = ((g1_band * env1) >> 8) + ((g2_band * env2) >> 8)
        val = (grain_out >> 1) + (white >> 2)
        out_grain = val >> 3
        
        if scale != 256:
            out_grain = (out_grain * scale) >> 8
        out = (out_grain * vol) >> 9
        
        if out > 32767: out = 32767
        elif out < -32768: out = -32768
        _pack_into('<h', out_buf, i * 2, out)
        
    grain1_low = g1_low; grain1_band = g1_band
    grain2_low = g2_low; grain2_band = g2_band

# --- 4. 高速シングルパス・等電力クロスフェード合成器 ---
def generate_crossfade_pink_env(raw_bytes, out_buf, vol, g_pink, g_env, state):
    """ピンクノイズから環境音へのシームレスな等電力クロスフェード生成。"""
    global env_lpf1, env_lpf2, env_lfo_phase
    _b0, _b1, _b2, _b3, _b4, _b5, _b6 = state
    _pack_into = struct.pack_into
    
    env_lfo_phase += 0.064
    if env_lfo_phase > 628.3: env_lfo_phase = 0.0
    lfo_mod = int(256 + 46 * math.sin(env_lfo_phase))
    eff_env_gain = (g_env * lfo_mod) >> 8
    
    lp1 = env_lpf1
    lp2 = env_lpf2
    
    for i in range(len(raw_bytes)):
        w = raw_bytes[i] - 128
        
        # ピンクノイズ
        _b0 = (32731 * _b0 + 1819 * w) >> 15
        _b1 = (32549 * _b1 + 2460 * w) >> 15
        _b2 = (31752 * _b2 + 5041 * w) >> 15
        _b3 = (28393 * _b3 + 10174 * w) >> 15
        _b4 = (18022 * _b4 + 17464 * w) >> 15
        _b5 = (-24956 * _b5 - 554 * w) >> 15
        out_pink = _b0 + _b1 + _b2 + _b3 + _b4 + _b5 + _b6 + ((w * 17570) >> 15)
        _b6 = (w * 3798) >> 15
        
        # 環境音（雨音）
        w_in = w << 6
        lp1 += (10500 * (w_in - lp1)) >> 15
        lp2 += (4200 * (lp1 - lp2)) >> 15
        high = (w_in - lp1) >> 4
        rain = (lp1 + lp2 + high) >> 1
        out_env = (rain * 22) >> 6
        
        # 等電力ブレンド
        val = ((out_pink * g_pink) >> 8) + ((out_env * eff_env_gain) >> 8)
        out = (val * vol) >> 9
        if out > 32767: out = 32767
        elif out < -32768: out = -32768
        _pack_into('<h', out_buf, i * 2, out)
        
    state[0] = _b0; state[1] = _b1; state[2] = _b2
    state[3] = _b3; state[4] = _b4; state[5] = _b5; state[6] = _b6
    env_lpf1 = lp1
    env_lpf2 = lp2

def generate_crossfade_env_grain(raw_bytes, out_buf, vol, g_env, g_grain):
    """環境音から粒状合成へのシームレスな等電力クロスフェード生成。"""
    global env_lpf1, env_lpf2, env_lfo_phase
    global grain1_low, grain1_band, grain2_low, grain2_band
    _update_grain_parameters()
    _pack_into = struct.pack_into
    
    env_lfo_phase += 0.064
    if env_lfo_phase > 628.3: env_lfo_phase = 0.0
    lfo_mod = int(256 + 46 * math.sin(env_lfo_phase))
    eff_env_gain = (g_env * lfo_mod) >> 8
    
    lp1 = env_lpf1
    lp2 = env_lpf2
    g1_low = grain1_low; g1_band = grain1_band
    g2_low = grain2_low; g2_band = grain2_band
    f1 = grain1_f; q1 = grain1_q; env1 = grain1_env
    f2 = grain2_f; q2 = grain2_q; env2 = grain2_env
    
    for i in range(len(raw_bytes)):
        w = raw_bytes[i] - 128
        
        # 環境音（雨音）
        w_in = w << 6
        lp1 += (10500 * (w_in - lp1)) >> 15
        lp2 += (4200 * (lp1 - lp2)) >> 15
        high = (w_in - lp1) >> 4
        rain = (lp1 + lp2 + high) >> 1
        out_env = (rain * 22) >> 6
        
        # 粒状合成
        white_g = w << 7
        g1_low += (f1 * g1_band) >> 14
        high1 = white_g - g1_low - ((q1 * g1_band) >> 14)
        g1_band += (f1 * high1) >> 14
        
        g2_low += (f2 * g2_band) >> 14
        high2 = white_g - g2_low - ((q2 * g2_band) >> 14)
        g2_band += (f2 * high2) >> 14
        
        grain_out = ((g1_band * env1) >> 8) + ((g2_band * env2) >> 8)
        val = (grain_out >> 1) + (white_g >> 2)
        out_grain = val >> 3
        
        # 等電力ブレンド
        val = ((out_env * eff_env_gain) >> 8) + ((out_grain * g_grain) >> 8)
        out = (val * vol) >> 9
        if out > 32767: out = 32767
        elif out < -32768: out = -32768
        _pack_into('<h', out_buf, i * 2, out)
        
    env_lpf1 = lp1
    env_lpf2 = lp2
    grain1_low = g1_low; grain1_band = g1_band
    grain2_low = g2_low; grain2_band = g2_band

# ==========================================
# Equal Power Crossfade Math
# ==========================================
def calculate_crossfade_gains(progress):
    """等電力クロスフェード曲線: gA^2 + gB^2 = 1 (progress: 0.0 〜 1.0)。"""
    p = max(0.0, min(1.0, progress))
    angle = p * (math.pi / 2.0)
    gain_a = int(math.cos(angle) * 256)
    gain_b = int(math.sin(angle) * 256)
    return gain_a, gain_b

# ==========================================
# Application Runtime & Finite State Machine
# ==========================================
current_state = STATE_STOPPED

current_volume = 1200
vol_phase = math.acos(1 - 2 * (current_volume - VOLUME_MIN) / (VOLUME_MAX - VOLUME_MIN))
vol_direction = 1
_urandom = os.urandom

session_start_ms = 0
standby_start_ms = 0

print(f"[SYS] Initialization complete. Mode: {'TEST (45s)' if TEST_MODE else 'NORMAL (45m)'}")

while True:
    event = btn.update()
    now_ms = time.ticks_ms()
    
    # ----------------------------------------------------
    # 1. Finite State Transitions (Button Events)
    # ----------------------------------------------------
    if event == 'SINGLE':
        if current_state == STATE_STANDBY:
            current_state = STATE_STOPPED
            audio_out = init_i2s()
            print("[EVENT] Standby exited -> STATE_STOPPED")
        elif current_state == STATE_TIMER:
            current_state = STATE_PLAYING
            print("[EVENT] Timer session overridden -> STATE_PLAYING")
        elif current_state == STATE_PLAYING:
            current_state = STATE_STOPPED
            print("[EVENT] Playback toggled -> STATE_STOPPED")
        elif current_state == STATE_STOPPED:
            current_state = STATE_PLAYING
            print(f"[EVENT] Playback toggled -> STATE_PLAYING (Vol: {current_volume})")
            
    elif event == 'DOUBLE':
        # Focus Sound Mix セッション起動 (Pink -> Ambient Rain -> Granular -> Fadeout -> Sleep)
        current_state = STATE_TIMER
        session_start_ms = time.ticks_ms()
        print(f"[EVENT] Focus Sound Mix started -> STATE_TIMER ({'45s' if TEST_MODE else '45m'})")
            
    elif event == 'HOLDING':
        if current_state in (STATE_PLAYING, STATE_TIMER):
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
        if current_state in (STATE_PLAYING, STATE_TIMER):
            vol_direction = 1

    # ----------------------------------------------------
    # 2. Focus Sound Mix Timeline & Audio Pipeline
    # ----------------------------------------------------
    if current_state == STATE_TIMER:
        elapsed = time.ticks_diff(now_ms, session_start_ms)
        
        # Phase 1: ピンクノイズ単独 (0 〜 14分)
        if elapsed < T1_START:
            generate_pink_noise(_urandom(CHUNK_SAMPLES), noise_buf, current_volume, pink_filter_state)
            audio_out.write(noise_buf)
            led.set_color(*COLOR_PHASE_PINK)
            
        # Phase 1 -> Phase 2 クロスフェード (ピンクノイズ -> 環境音, 14 〜 15分)
        elif elapsed < T1_END:
            p = (elapsed - T1_START) / CROSSFADE_MS
            g_pink, g_env = calculate_crossfade_gains(p)
            generate_crossfade_pink_env(_urandom(CHUNK_SAMPLES), noise_buf, current_volume, g_pink, g_env, pink_filter_state)
            audio_out.write(noise_buf)
            # LEDの色をピンクからグリーンへ滑らかに補間
            r = int(COLOR_PHASE_PINK[0] * (1 - p) + COLOR_PHASE_ENV[0] * p)
            g = int(COLOR_PHASE_PINK[1] * (1 - p) + COLOR_PHASE_ENV[1] * p)
            b = int(COLOR_PHASE_PINK[2] * (1 - p) + COLOR_PHASE_ENV[2] * p)
            led.set_color(r, g, b)
            
        # Phase 2: 環境音（雨）単独 (15 〜 29分)
        elif elapsed < T2_START:
            generate_env_noise(_urandom(CHUNK_SAMPLES), noise_buf, current_volume)
            audio_out.write(noise_buf)
            led.set_color(*COLOR_PHASE_ENV)
            
        # Phase 2 -> Phase 3 クロスフェード (環境音 -> 粒状合成, 29 〜 30分)
        elif elapsed < T2_END:
            p = (elapsed - T2_START) / CROSSFADE_MS
            g_env, g_grain = calculate_crossfade_gains(p)
            generate_crossfade_env_grain(_urandom(CHUNK_SAMPLES), noise_buf, current_volume, g_env, g_grain)
            audio_out.write(noise_buf)
            # LEDの色をグリーンからインディゴ/シアンへ滑らかに補間
            r = int(COLOR_PHASE_ENV[0] * (1 - p) + COLOR_PHASE_GRAIN[0] * p)
            g = int(COLOR_PHASE_ENV[1] * (1 - p) + COLOR_PHASE_GRAIN[1] * p)
            b = int(COLOR_PHASE_ENV[2] * (1 - p) + COLOR_PHASE_GRAIN[2] * p)
            led.set_color(r, g, b)
            
        # Phase 3: 粒状合成単独 (30 〜 44分)
        elif elapsed < T3_START:
            generate_granular_noise(_urandom(CHUNK_SAMPLES), noise_buf, current_volume)
            audio_out.write(noise_buf)
            led.set_color(*COLOR_PHASE_GRAIN)
            
        # Phase 4: 最終フェードアウト (粒状合成 -> ゼロ, 44 〜 45分)
        elif elapsed < T3_END:
            p = (elapsed - T3_START) / FADEOUT_MS
            fade_gain = int(math.cos(p * (math.pi / 2.0)) * 256)
            generate_granular_noise(_urandom(CHUNK_SAMPLES), noise_buf, current_volume, scale=fade_gain)
            audio_out.write(noise_buf)
            # LED輝度も音量に合わせて減光
            bright = max(0.0, 1.0 - p)
            led.set_color(COLOR_PHASE_GRAIN[0], COLOR_PHASE_GRAIN[1], COLOR_PHASE_GRAIN[2], brightness=bright)
            
        # セッション完了 -> スタンバイ & ディープスリープへ移行
        else:
            print("[STATE] Focus Sound Mix completed -> Preparing Deep Sleep")
            current_state = STATE_STANDBY
            standby_start_ms = now_ms
            # アンプのポップノイズ防止のため無音をフラッシュ
            for _ in range(10):
                audio_out.write(silent_buf)
            audio_out.deinit()
            led.set_color(*COLOR_STANDBY)

    elif current_state == STATE_PLAYING:
        # シングルクリックによる常時ピンクノイズ再生
        generate_pink_noise(_urandom(CHUNK_SAMPLES), noise_buf, current_volume, pink_filter_state)
        audio_out.write(noise_buf)
        if event in ('HOLDING', 'LONG'):
            led.set_color(*COLOR_VOL)
        else:
            led.set_color(*COLOR_PLAY)

    elif current_state == STATE_STOPPED:
        audio_out.write(silent_buf)
        led.set_color(*COLOR_STOP)

    elif current_state == STATE_STANDBY:
        # 数秒の安定待機後、タイマー起床のディープスリープへ移行
        if time.ticks_diff(now_ms, standby_start_ms) >= 3000:
            print(f"[POWER] Entering Deep Sleep for ~24h. Wake via timer only.")
            led.set_color(0, 0, 0)
            time.sleep_ms(50)
            # I2Sピン等を安全な状態に戻す（リーク低減）
            try:
                Pin(BCLK_PIN, Pin.IN)
                Pin(DATA_PIN, Pin.IN)
                Pin(WS_PIN, Pin.IN)
            except Exception:
                pass
            time.sleep_ms(100)
            machine.deepsleep(SLEEP_DURATION_MS)
        else:
            time.sleep_ms(50)