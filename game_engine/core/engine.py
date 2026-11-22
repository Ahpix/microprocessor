from __future__ import annotations
import time
import threading
from typing import Dict, Any, Optional, Callable, TYPE_CHECKING
from game_engine.core.tamagotchi import Tamagotchi
from game_engine.core.constants import (
    MODE_HOME,
    MODE_SLEEP,
    MODE_MINI_GAME,
    MODE_BATTLE,
    VALID_MODES,
    MENU_FEED,
    MENU_PLAY,
    MENU_SLEEP,
    MENU_BATTLE,
    HOME_MENU_SEQUENCE,
    BUTTON_A,
    BUTTON_B,
    BUTTON_C,
    LED_THRESHOLD,
    LED_BLINK_PERIOD_MS,
    MOVE_ATTACK,
    MOVE_DEFEND,
    MOVE_SKILL,
)

if TYPE_CHECKING:
    from game_engine.battle.battle_manager import BattleManager


class GameEngine:
    """
    게임 엔진 코어 컨트롤러 (protocol.md 4~7절 및 9절 준수)
    - 캐릭터 상태 및 생명주기 관리
    - 모드 FSM (home, sleep, mini_game, battle)
    - 버튼 입력 A/B/C 처리 및 디스패치
    - state 스냅샷 및 state_version 단조 증가 관리
    - led_command 생성
    - 스레드 안전성(threading.Lock) 보장
    """

    def __init__(
        self,
        tamagotchi: Optional[Tamagotchi] = None,
        device_id: str = "pi01",
        on_state_change: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_led_command: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.lock = threading.Lock()
        self.device_id = device_id
        self.tamagotchi = tamagotchi if tamagotchi is not None else Tamagotchi("Tama", pet_id="pet01")

        # UI 모드 및 선택 메뉴 (protocol.md 4절)
        # 불변조건: mode가 home일 때만 selected_menu가 문자열, 그 외에는 None
        self.mode = MODE_HOME
        self.selected_menu = MENU_FEED

        # 배틀 매니저
        self.battle_manager: Optional[BattleManager] = None

        # 상태 버전 (클라이언트에 보이는 상태가 변경될 때마다 증가)
        self.state_version = 1

        # 연결 상태 (Heartbeat 기준)
        self.is_connected = True

        # 최근 처리한 message_id 캐시 (중복 방지: protocol.md 9절 최소 60초)
        self._processed_message_ids: Dict[str, float] = {}

        # 이벤트 콜백
        self.on_state_change = on_state_change
        self.on_led_command = on_led_command

    def _mark_state_changed(self):
        """상태 변경 플래그: state_version 증가 및 등록된 콜백 실행"""
        self.state_version += 1

        if self.on_state_change:
            try:
                self.on_state_change(self._get_state_unlocked())
            except Exception:
                pass

        if self.on_led_command:
            try:
                self.on_led_command(self._generate_led_command_unlocked())
            except Exception:
                pass

    def _get_state_unlocked(self) -> Dict[str, Any]:
        # 수면 중이면서 수면 시간이 종료되었는지 검사하여 모드 자동 동기화
        if self.mode == MODE_SLEEP and not self.tamagotchi.is_sleeping:
            self.mode = MODE_HOME
            self.selected_menu = MENU_FEED

        battle_data = self.battle_manager.to_dict() if self.battle_manager else None

        return {
            "state_version": self.state_version,
            "pet": self.tamagotchi.to_pet_dict(),
            "ui": {
                "mode": self.mode,
                "selected_menu": self.selected_menu if self.mode == MODE_HOME else None,
            },
            "battle": battle_data,
        }

    def get_state(self) -> Dict[str, Any]:
        """protocol.md 4절 전체 게임 상태 (state) 반환"""
        with self.lock:
            return self._get_state_unlocked()

    def _generate_led_command_unlocked(self) -> Dict[str, Any]:
        pet = self.tamagotchi.to_pet_dict()

        def _get_stat_led(val: int) -> Dict[str, Any]:
            if not pet["is_alive"]:
                return {"mode": "off"}
            if val > LED_THRESHOLD:
                return {"mode": "on"}
            return {"mode": "blink", "period_ms": LED_BLINK_PERIOD_MS}

        conn_led = (
            {"mode": "on"}
            if self.is_connected
            else {"mode": "blink", "period_ms": LED_BLINK_PERIOD_MS}
        )

        return {
            "leds": {
                "satiety": _get_stat_led(pet["satiety"]),
                "happiness": _get_stat_led(pet["happiness"]),
                "energy": _get_stat_led(pet["energy"]),
                "connection": conn_led,
            }
        }

    def generate_led_command(self) -> Dict[str, Any]:
        """protocol.md 7절 LED 출력 명령 생성"""
        with self.lock:
            return self._generate_led_command_unlocked()

    def set_connection_status(self, is_connected: bool):
        """연결 상태 변경 (연결 LED 갱신)"""
        with self.lock:
            if self.is_connected != is_connected:
                self.is_connected = is_connected
                self._mark_state_changed()

    def update_tick(self):
        """
        주기적 엔진 틱 (1초 주기 호출 권장)
        - 시간 경과 감쇄 반영
        - 수면 자동 기상 확인
        - 배틀 5초 타임아웃 검사
        """
        with self.lock:
            was_sleeping = self.tamagotchi.is_sleeping
            self.tamagotchi._update_stats()

            # 수면이 시간 만료로 자동 종료된 경우 모드 복귀
            if was_sleeping and not self.tamagotchi.is_sleeping and self.mode == MODE_SLEEP:
                self.mode = MODE_HOME
                self.selected_menu = MENU_FEED
                self._mark_state_changed()
                return

            # 배틀 타임아웃 검사
            if self.battle_manager and self.mode == MODE_BATTLE:
                if self.battle_manager.check_timeout():
                    self._mark_state_changed()

    def handle_button_event(self, button: str, event: str = "press", message_id: Optional[str] = None) -> Dict[str, Any]:
        """
        버튼 입력 처리 (protocol.md 5절 및 9절 중복 방지)
        반환: {"status": "accepted" | "duplicate" | "error", "error_code": Optional[str], "message": Optional[str]}
        """
        if event != "press":
            return {"status": "error", "code": "INVALID_PAYLOAD", "message": "Only 'press' event is supported in v1"}

        if button not in (BUTTON_A, BUTTON_B, BUTTON_C):
            return {"status": "error", "code": "INVALID_PAYLOAD", "message": "Button must be A, B, or C"}

        with self.lock:
            # 중복 message_id 검사 (최근 60초)
            now = time.monotonic()
            if message_id:
                # 60초 초과된 과거 캐시 정리
                self._processed_message_ids = {
                    mid: ts for mid, ts in self._processed_message_ids.items() if now - ts < 60.0
                }
                if message_id in self._processed_message_ids:
                    return {"status": "duplicate", "message": "Duplicate request"}
                self._processed_message_ids[message_id] = now

            # 사망 캐릭터 가드 (protocol.md 4절: 사망한 캐릭터의 일반 육성·배틀 입력 거절)
            if not self.tamagotchi.is_alive:
                return {"status": "error", "code": "INVALID_STATE", "message": "Pet is not alive"}

            # 모드별 입력 처리
            changed = False
            if self.mode == MODE_HOME:
                changed = self._handle_button_home(button)
            elif self.mode == MODE_SLEEP:
                changed = self._handle_button_sleep(button)
            elif self.mode == MODE_BATTLE:
                changed = self._handle_button_battle(button)
            elif self.mode == MODE_MINI_GAME:
                changed = False

            if changed:
                self._mark_state_changed()

            return {"status": "accepted"}

    def _handle_button_home(self, button: str) -> bool:
        """홈 모드 입력 처리: protocol.md 5절 표 기준"""
        if button == BUTTON_A:
            # A: 다음 메뉴 (feed -> play -> sleep -> battle -> feed)
            idx = HOME_MENU_SEQUENCE.index(self.selected_menu) if self.selected_menu in HOME_MENU_SEQUENCE else 0
            self.selected_menu = HOME_MENU_SEQUENCE[(idx + 1) % len(HOME_MENU_SEQUENCE)]
            return True

        elif button == BUTTON_B:
            # B: 선택 / 확인
            if self.selected_menu == MENU_FEED:
                return self.tamagotchi.feed()

            elif self.selected_menu == MENU_PLAY:
                return self.tamagotchi.play()

            elif self.selected_menu == MENU_SLEEP:
                if self.tamagotchi.sleep():
                    self.mode = MODE_SLEEP
                    self.selected_menu = None
                    return True
                return False

            elif self.selected_menu == MENU_BATTLE:
                # 배틀 모드 진입 요청 (호스트 또는 대기 상태)
                return False

        elif button == BUTTON_C:
            # C: 취소 / 상태 보기 -> feed로 되돌리고 상태 리프레시
            self.selected_menu = MENU_FEED
            return True

        return False

    def _handle_button_sleep(self, button: str) -> bool:
        """수면 모드 입력 처리: protocol.md 5절 (B로 깨우기, A/C 동작 없음)"""
        if button == BUTTON_B:
            if self.tamagotchi.wake():
                self.mode = MODE_HOME
                self.selected_menu = MENU_FEED
                return True
        return False

    def _handle_button_battle(self, button: str) -> bool:
        """배틀 모드 입력 처리: protocol.md 5절 (A=attack, B=defend, C=skill)"""
        if not self.battle_manager:
            return False

        move_map = {
            BUTTON_A: MOVE_ATTACK,
            BUTTON_B: MOVE_DEFEND,
            BUTTON_C: MOVE_SKILL,
        }
        move = move_map.get(button)
        if not move:
            return False

        res = self.battle_manager.choose(
            player_id=self.tamagotchi.pet_id,
            move=move,
            turn=self.battle_manager.turn,
        )
        return res.get("success", False)

    # ===== 배틀 생명주기 관리 =====

    def start_battle(self, battle_manager: BattleManager):
        """배틀 시작 및 모드 전환"""
        with self.lock:
            self.battle_manager = battle_manager
            self.mode = MODE_BATTLE
            self.selected_menu = None
            self._mark_state_changed()

    def end_battle(self):
        """배틀 종료 후 홈 모드로 복귀 (protocol.md 10.6절)"""
        with self.lock:
            self.battle_manager = None
            self.mode = MODE_HOME
            self.selected_menu = MENU_FEED
            self._mark_state_changed()
