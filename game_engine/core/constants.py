"""
게임 엔진 및 프로토콜 공통 상수 정의 (docs/protocol.md 기준)
"""

# 프로토콜 버전
PROTOCOL_VERSION = 1

# UI 모드 (ui.mode)
MODE_HOME = "home"
MODE_SLEEP = "sleep"
MODE_MINI_GAME = "mini_game"
MODE_BATTLE = "battle"

VALID_MODES = {MODE_HOME, MODE_SLEEP, MODE_MINI_GAME, MODE_BATTLE}

# 홈 메뉴 (ui.selected_menu) - 순환 순서: feed -> play -> sleep -> battle -> feed
MENU_FEED = "feed"
MENU_PLAY = "play"
MENU_SLEEP = "sleep"
MENU_BATTLE = "battle"

HOME_MENU_SEQUENCE = [MENU_FEED, MENU_PLAY, MENU_SLEEP, MENU_BATTLE]

# 버튼 종류
BUTTON_A = "A"
BUTTON_B = "B"
BUTTON_C = "C"

VALID_BUTTONS = {BUTTON_A, BUTTON_B, BUTTON_C}

# 배틀 동작 (battle move)
MOVE_ATTACK = "attack"
MOVE_DEFEND = "defend"
MOVE_SKILL = "skill"

VALID_MOVES = {MOVE_ATTACK, MOVE_DEFEND, MOVE_SKILL}

# 배틀 페이즈 (battle.phase)
BATTLE_PHASE_CHOOSING = "choosing"
BATTLE_PHASE_RESULT = "result"
BATTLE_PHASE_ENDED = "ended"
BATTLE_PHASE_RECONNECT_WAIT = "reconnect_wait"
BATTLE_PHASE_MINI_GAME = "mini_game"

# 배틀 종료 사유 (battle.end_reason)
END_REASON_HP_ZERO = "hp_zero"
END_REASON_TURN_LIMIT = "turn_limit"
END_REASON_DRAW = "draw"
END_REASON_DISCONNECT = "disconnect"

# 배틀 기본 밸런스 설정 (protocol.md 10.7절)
DEFAULT_MAX_HP = 100
DEFAULT_MAX_TURNS = 10
SELECTION_TIMEOUT_SECONDS = 5

DAMAGE_ATTACK_WIN = 20   # attack > skill
DAMAGE_DEFEND_WIN = 15   # defend > attack
DAMAGE_SKILL_WIN = 30    # skill > defend
DAMAGE_TIE = 5           # 같은 선택 시 양측 데미지

# LED 임계값 (protocol.md 7절)
LED_THRESHOLD = 30
LED_BLINK_PERIOD_MS = 1000
