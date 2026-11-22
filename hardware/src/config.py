"""
하드웨어 조작기 설정 모듈 (Pin Configuration & Constants)
라즈베리파이 GPIO BCM 핀 번호 및 타이밍 설정을 관리합니다.
"""

# ==========================================
# GPIO 핀 매핑 (BCM 번호 기준)
# ==========================================

# 버튼 3개 (Active LOW: 내부 풀업 사용)
PIN_BTN_A = 17   # 방향키 1 (메뉴 이동 / 이전)
PIN_BTN_B = 27   # 선택 버튼 (결정 / 확인)
PIN_BTN_C = 22   # 방향키 2 (취소 / 뒤로가기)

BUTTON_PINS = {
    "A": PIN_BTN_A,
    "B": PIN_BTN_B,
    "C": PIN_BTN_C,
}

# LED 4개 (Active HIGH: 전류 제한 저항 220Ω 필수)
PIN_LED_SATIETY   = 23   # 배고픔 (포만감)
PIN_LED_HAPPINESS = 24   # 행복도
PIN_LED_ENERGY    = 25   # 에너지
PIN_LED_CONN      = 5    # 서버 연결 상태

LED_PINS = {
    "satiety": PIN_LED_SATIETY,
    "happiness": PIN_LED_HAPPINESS,
    "energy": PIN_LED_ENERGY,
    "connection": PIN_LED_CONN,
}

# ==========================================
# 타이밍 및 디바운스 설정
# ==========================================
DEBOUNCE_TIME_MS = 200      # 버튼 채터링 방지 디바운스 시간 (밀리초)
DEFAULT_BLINK_PERIOD_MS = 1000  # LED 깜빡임 기본 주기 (1초)
