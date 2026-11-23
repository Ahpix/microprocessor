"""
버튼 실시간 진단 도구 (diagnose_buttons.py)
각 핀(GPIO 17, 27, 22)의 실시간 전압 레벨(HIGH/LOW)을 화면에 연속으로 출력하여
배선 오류, 접촉 불량, 핀 오결선을 즉시 찾아냅니다.

실행 방법:
  python3 tests/diagnose_buttons.py
"""

import os
os.environ.setdefault('LG_WD', '/tmp')

import sys
import time

# 모듈 import 경로 보정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
grandparent_dir = os.path.abspath(os.path.join(parent_dir, ".."))
for p in [parent_dir, grandparent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from hardware.src.config import BUTTON_PINS
except ModuleNotFoundError:
    from src.config import BUTTON_PINS

try:
    import RPi.GPIO as GPIO
    IS_RPI = True
except (ImportError, RuntimeError):
    IS_RPI = False

def main():
    print("=" * 65)
    print(" 🔍 버튼 실시간 핀 진단기 (Pin Status Monitor)")
    print("=" * 65)
    print(" - 풀업 저항 정상 상태 : 안 누름 = 1 (HIGH) / 누름 = 0 (LOW)")
    print(" - 만약 안 눌렀는데 0이다  -> 핀이 쇼트되었거나 스위치가 90도 돌아감")
    print(" - 눌렀는데도 계속 1이다   -> GND가 안 닿았거나 핀 번호가 틀림")
    print("=" * 65)

    if not IS_RPI:
        print("[오류] 실제 라즈베리파이 환경이 아닙니다. GPIO 제어가 불가능합니다.")
        return

    GPIO.setmode(GPIO.BCM)
    for name, pin in BUTTON_PINS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    print("\n실시간 감시 중... (종료: Ctrl+C)\n")
    print(" Button A (GPIO 17) | Button B (GPIO 27) | Button C (GPIO 22) ")
    print("---------------------------------------------------------------")

    prev_vals = {}

    try:
        while True:
            val_a = GPIO.input(BUTTON_PINS["A"])
            val_b = GPIO.input(BUTTON_PINS["B"])
            val_c = GPIO.input(BUTTON_PINS["C"])

            status_a = "누름 (0)" if val_a == 0 else "안누름 (1)"
            status_b = "누름 (0)" if val_b == 0 else "안누름 (1)"
            status_c = "누름 (0)" if val_c == 0 else "안누름 (1)"

            # 상태 변화가 있거나 누른 버튼이 있을 때 강조 출력
            any_pressed = (val_a == 0 or val_b == 0 or val_c == 0)
            mark = " 🔴 [감지됨!]" if any_pressed else ""

            # 터미널 한 줄 갱신 출력
            sys.stdout.write(f"\r  A: {status_a}  |  B: {status_b}  |  C: {status_c} {mark}   ")
            sys.stdout.flush()

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n[INFO] 진단을 종료합니다.")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
