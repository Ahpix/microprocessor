"""
LED 4개 단독 동작 테스트 스크립트 (test_leds.py)
실제 라즈베리파이에서 실행하여 LED 4개(배고픔, 행복도, 에너지, 연결)가
순차 점등(On), 깜빡임(Blink), 소등(Off) 상태를 정상 수행하는지 확인합니다.

실행 방법:
  python -m hardware.tests.test_leds
  또는
  python test_leds.py (hardware/tests 디렉터리 내)
"""

import sys
import os
import time

# 상위 src 모듈 import 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from hardware.src.led_controller import LEDController
from hardware.src.config import LED_PINS

def main():
    print("=" * 60)
    print(" 💡 다마고치 조작기 - LED 4개 단독 기능 테스트 시작")
    print("=" * 60)
    for name, pin in LED_PINS.items():
        print(f" - LED '{name}': GPIO BCM {pin}")
    print("-" * 60)

    controller = LEDController()

    try:
        # Step 1: 순차 점등 (ON)
        print("\n[STEP 1] 4개 LED 순차 점등 (ON) 테스트...")
        for name in LED_PINS:
            print(f" >> '{name}' LED ON")
            controller.set_led(name, "on")
            time.sleep(1)

        # Step 2: 깜빡임 (BLINK)
        print("\n[STEP 2] 4개 LED 깜빡임 (BLINK - 500ms 주기) 테스트 (3초간)...")
        for name in LED_PINS:
            controller.set_led(name, "blink", period_ms=500)
        time.sleep(3)

        # Step 3: 프로토콜 명령 시뮬레이션
        print("\n[STEP 3] 게임 상태 시뮬레이션 명령 적용...")
        print("  - satiety: ON (충분)")
        print("  - happiness: ON (충분)")
        print("  - energy: BLINK (피로 경고!)")
        print("  - connection: ON (정상 연결)")
        sample_command = {
            "satiety": {"mode": "on"},
            "happiness": {"mode": "on"},
            "energy": {"mode": "blink", "period_ms": 1000},
            "connection": {"mode": "on"}
        }
        controller.apply_led_command(sample_command)
        time.sleep(4)

        # Step 4: 전체 소등 (OFF)
        print("\n[STEP 4] 전체 소등 (OFF)...")
        for name in LED_PINS:
            controller.set_led(name, "off")
        time.sleep(1)

        print("\n[SUCCESS] LED 기능 테스트가 성공적으로 완료되었습니다!")

    except KeyboardInterrupt:
        print("\n[INFO] 사용자에 의해 중단되었습니다.")
    finally:
        controller.cleanup()
        print("[INFO] GPIO 정리가 완료되었습니다.")

if __name__ == "__main__":
    main()
