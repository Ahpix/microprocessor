"""
버튼 3개 단독 동작 테스트 스크립트 (test_buttons.py)
실제 라즈베리파이에서 실행하여 버튼 3개(A, B, C)가 정상적으로 인식되고
디바운스가 올바르게 동작하는지 확인합니다.

실행 방법:
  python -m hardware.tests.test_buttons
  또는
  python test_buttons.py (hardware/tests 디렉터리 내)
"""

import sys
import os
import time

# 상위 src 모듈 import 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from hardware.src.button_handler import ButtonHandler
from hardware.src.config import BUTTON_PINS

def on_press(button_name: str):
    button_role = {
        "A": "방향키 1 (메뉴 이동 / 이전)",
        "B": "선택 버튼 (결정 / 확인)",
        "C": "방향키 2 (취소 / 뒤로가기)"
    }.get(button_name, "알 수 없음")

    print(f"\n[EVENT] 버튼 눌림 감지! >> Button {button_name} ({button_role})")
    print(f"        -> GPIO Pin: {BUTTON_PINS[button_name]} | Time: {time.strftime('%H:%M:%S')}")

def main():
    print("=" * 60)
    print(" 🕹️  다마고치 조작기 - 버튼 3개 단독 테스트 시작")
    print("=" * 60)
    print("각 버튼을 눌러보세요. (종료하려면 Ctrl+C를 누르세요)")
    for btn, pin in BUTTON_PINS.items():
        print(f" - Button {btn}: GPIO BCM {pin}")
    print("-" * 60)

    handler = ButtonHandler(on_button_press=on_press)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] 테스트를 종료합니다. GPIO를 정리합니다...")
    finally:
        handler.cleanup()
        print("[INFO] 정리 완료.")

if __name__ == "__main__":
    main()
