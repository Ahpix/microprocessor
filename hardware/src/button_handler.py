"""
버튼 입력 처리 모듈 (Button Handler)
물리 버튼 3개 (A, B, C)의 입력을 디바운싱하여 press 이벤트를 발생시킵니다.
"""

import time
from typing import Callable, Optional
from .config import BUTTON_PINS, DEBOUNCE_TIME_MS

try:
    import RPi.GPIO as GPIO
    IS_RPI = True
except (ImportError, RuntimeError):
    IS_RPI = False


class ButtonHandler:
    def __init__(self, on_button_press: Optional[Callable[[str], None]] = None):
        """
        :param on_button_press: 버튼이 눌렸을 때 호출할 콜백 함수 (인자: button_name 'A' | 'B' | 'C')
        """
        self.on_button_press = on_button_press
        self.last_press_time = {btn: 0.0 for btn in BUTTON_PINS}
        self._setup_gpio()

    def _setup_gpio(self):
        if not IS_RPI:
            print("[ButtonHandler] RPi.GPIO 모듈이 감지되지 않았습니다. (가상/시뮬레이션 모드로 동작)")
            return

        GPIO.setmode(GPIO.BCM)
        for btn_name, pin in BUTTON_PINS.items():
            # 내부 풀업 저항 활성화 (Active LOW)
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                pin,
                GPIO.FALLING,
                callback=lambda ch, name=btn_name: self._handle_gpio_interrupt(name),
                bouncetime=DEBOUNCE_TIME_MS
            )

    def _handle_gpio_interrupt(self, btn_name: str):
        now = time.time()
        # 2차 소프트웨어 디바운스 확인 (초 단위)
        if now - self.last_press_time[btn_name] < (DEBOUNCE_TIME_MS / 1000.0):
            return

        self.last_press_time[btn_name] = now
        self._dispatch_event(btn_name)

    def _dispatch_event(self, btn_name: str):
        if self.on_button_press:
            self.on_button_press(btn_name)
        else:
            print(f"[ButtonHandler] 버튼 누름 감지: {btn_name}")

    def cleanup(self):
        if IS_RPI:
            for pin in BUTTON_PINS.values():
                try:
                    GPIO.remove_event_detect(pin)
                except Exception:
                    pass
            GPIO.cleanup(list(BUTTON_PINS.values()))
