"""
LED 제어 모듈 (LED Controller)
다마고치 상태를 나타내는 4개의 LED(배고픔, 행복도, 에너지, 연결)를 제어합니다.
모드: 'on', 'off', 'blink' 지원
"""

import os
# 라즈베리파이 OS (Bookworm) lgpio 알림 파이프 권한 오류 방지
os.environ.setdefault('LG_WD', '/tmp')

import time
import threading
from typing import Dict, Any
from .config import LED_PINS, DEFAULT_BLINK_PERIOD_MS

try:
    import RPi.GPIO as GPIO
    IS_RPI = True
except (ImportError, RuntimeError):
    IS_RPI = False


class LEDController:
    def __init__(self):
        self._states = {
            name: {"mode": "off", "period_ms": DEFAULT_BLINK_PERIOD_MS}
            for name in LED_PINS
        }
        self._running = True
        self._lock = threading.Lock()
        self._setup_gpio()

        # LED 깜빡임(Blink)을 비동기로 처리하는 백그라운드 스레드
        self._blink_thread = threading.Thread(target=self._blink_worker, daemon=True)
        self._blink_thread.start()

    def _setup_gpio(self):
        if not IS_RPI:
            print("[LEDController] RPi.GPIO 모듈이 감지되지 않았습니다. (가상/시뮬레이션 모드로 동작)")
            return

        GPIO.setmode(GPIO.BCM)
        for pin in LED_PINS.values():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

    def set_led(self, led_name: str, mode: str, period_ms: int = DEFAULT_BLINK_PERIOD_MS):
        """
        특정 LED 상태 변경
        :param led_name: 'satiety' | 'happiness' | 'energy' | 'connection'
        :param mode: 'on' | 'off' | 'blink'
        :param period_ms: blink 모드일 때 깜빡임 주기 (ms)
        """
        if led_name not in LED_PINS:
            print(f"[LEDController] 알 수 없는 LED 이름: {led_name}")
            return

        with self._lock:
            self._states[led_name] = {"mode": mode, "period_ms": period_ms}

        if mode == "on":
            self._write_pin(led_name, True)
        elif mode == "off":
            self._write_pin(led_name, False)

    def apply_led_command(self, leds_payload: Dict[str, Any]):
        """
        프로토콜의 led_command payload를 한 번에 적용
        예: { "satiety": {"mode": "on"}, ... }
        """
        for name, config in leds_payload.items():
            mode = config.get("mode", "off")
            period_ms = config.get("period_ms", DEFAULT_BLINK_PERIOD_MS)
            self.set_led(name, mode, period_ms)

    def _write_pin(self, led_name: str, high: bool):
        if IS_RPI:
            pin = LED_PINS[led_name]
            GPIO.output(pin, GPIO.HIGH if high else GPIO.LOW)
        else:
            state_str = "ON" if high else "OFF"
            # 시뮬레이션 로그 (디버그용)
            # print(f"[LED Simulation] {led_name} -> {state_str}")

    def _blink_worker(self):
        """깜빡임(Blink) 상태인 LED들을 주기적으로 토글하는 작업자 스레드"""
        tick_interval = 0.05  # 50ms마다 상태 체크
        blink_states = {name: False for name in LED_PINS}
        last_toggle_times = {name: time.time() for name in LED_PINS}

        while self._running:
            now = time.time()
            with self._lock:
                current_states = dict(self._states)

            for name, cfg in current_states.items():
                if cfg["mode"] == "blink":
                    half_period = (cfg["period_ms"] / 1000.0) / 2.0
                    if now - last_toggle_times[name] >= half_period:
                        blink_states[name] = not blink_states[name]
                        last_toggle_times[name] = now
                        self._write_pin(name, blink_states[name])

            time.sleep(tick_interval)

    def cleanup(self):
        self._running = False
        if IS_RPI:
            for pin in LED_PINS.values():
                GPIO.output(pin, GPIO.LOW)
            GPIO.cleanup(list(LED_PINS.values()))
