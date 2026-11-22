"""
버튼 3개 단독 동작 테스트 스크립트 (test_buttons.py)
실제 라즈베리파이에서 실행하여 버튼 3개(A, B, C)가 정상적으로 인식되고
디바운스가 올바르게 동작하는지 확인합니다.

어디서든 실행 가능:
  1) hardware 디렉터리 내:
     python3 tests/test_buttons.py
     또는
     python3 -m tests.test_buttons
  2) 프로젝트 루트(microprocessor) 내:
     python3 -m hardware.tests.test_buttons
"""

import os
import sys

# 1. 라즈베리파이 OS (Debian Bookworm) lgpio 알림 파이프 권한 오류 방지
os.environ.setdefault('LG_WD', '/tmp')

# 2. 실행 위치(루트 또는 hardware 폴더 내부)에 구애받지 않도록 sys.path 보정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
grandparent_dir = os.path.abspath(os.path.join(parent_dir, ".."))

for p in [parent_dir, grandparent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

# 3. 유연한 모듈 import
try:
    from hardware.src.button_handler import ButtonHandler
    from hardware.src.config import BUTTON_PINS
except ModuleNotFoundError:
    from src.button_handler import ButtonHandler
    from src.config import BUTTON_PINS

import time

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
