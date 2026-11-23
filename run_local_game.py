#!/usr/bin/env python3
"""
🎮 다마고치 로컬 통합 실행기 (run_local_game.py)
하드웨어(물리 버튼 3개 + LED 4개)와 게임 엔진(GameEngine + Tamagotchi)을
직접 연동하여 라즈베리파이에서 다마고치를 플레이하는 통합 실행 스크립트입니다.

실행 방법:
  python3 run_local_game.py
"""

import os
import sys

# 1. 라즈베리파이 OS (Debian Bookworm) lgpio 알림 파이프 권한 오류 방지
os.environ.setdefault('LG_WD', '/tmp')

# 2. 프로젝트 루트 경로 보정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import time
import threading
from typing import Dict, Any

from game_engine.core.engine import GameEngine
from game_engine.core.tamagotchi import Tamagotchi
from storage.save_manager import save_game, load_game
from hardware.src.hardware_manager import HardwareManager


class LocalGameRunner:
    def __init__(self):
        self.running = True
        self.lock = threading.Lock()
        self.last_action_message = "게임이 시작되었습니다! 버튼을 눌러 조작해 보세요."

        # 1. 저장 데이터 불러오기 또는 신규 캐릭터 생성
        saved_pet = load_game()
        if saved_pet:
            self.pet = saved_pet
            self.last_action_message = f"저장된 다마고치 '{self.pet.name}'를 성공적으로 불러왔습니다!"
        else:
            self.pet = Tamagotchi(name="Tama", pet_id="pet01")
            self.last_action_message = "새로운 다마고치 'Tama'가 태어났습니다!"

        # 2. 하드웨어 매니저 초기화
        self.hw = HardwareManager(
            device_id="pi01",
            on_send_event=self._on_hardware_button_event
        )

        # 3. 게임 엔진 초기화 (이벤트 콜백 연결)
        self.engine = GameEngine(
            tamagotchi=self.pet,
            device_id="pi01",
            on_state_change=self._on_engine_state_change,
            on_led_command=self._on_engine_led_command
        )

        # 초기 LED 상태 적용
        initial_leds = self.engine.generate_led_command()
        self.hw.handle_led_command(initial_leds)

    def _on_hardware_button_event(self, event_dict: Dict[str, Any]):
        """물리 버튼이 눌렸을 때 호출되는 콜백"""
        payload = event_dict.get("payload", {})
        button = payload.get("button")
        event = payload.get("event", "press")
        message_id = event_dict.get("message_id")

        if button:
            res = self.engine.handle_button_event(button=button, event=event, message_id=message_id)
            with self.lock:
                self._update_action_message(button, res)
            self._render_ui()

    def _update_action_message(self, button: str, result: Dict[str, Any]):
        """버튼 입력 결과를 사람이 읽기 쉬운 메시지로 갱신"""
        state = self.engine.get_state()
        mode = state["ui"]["mode"]
        menu = state["ui"]["selected_menu"]

        if result.get("status") == "error":
            self.last_action_message = f"[경고] 조작 불가: {result.get('message', '동작 실패')}"
            return

        if button == "A":
            self.last_action_message = f"[버튼 A] 메뉴 이동 ➔ 현재 선택: '{menu}'"
        elif button == "B":
            if mode == "sleep":
                self.last_action_message = "[버튼 B] 다마고치를 흔들어 깨웠습니다! ⏰"
            else:
                self.last_action_message = f"[버튼 B] '{menu}' 실행 완료! ✨"
        elif button == "C":
            self.last_action_message = "[버튼 C] 메뉴 선택 취소 (기본 메뉴 복귀)"

    def _on_engine_state_change(self, state: Dict[str, Any]):
        """엔진 상태 변경 시 화면 갱신"""
        self._render_ui()

    def _on_engine_led_command(self, led_cmd: Dict[str, Any]):
        """엔진에서 LED 명령이 생성되면 하드웨어로 전달"""
        self.hw.handle_led_command(led_cmd)

    def _make_progress_bar(self, value: int, max_val: int = 100, length: int = 15) -> str:
        filled = int(length * (value / max_val))
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}] {value:>3}%"

    def _render_ui(self):
        """콘솔 화면에 다마고치 상태와 메뉴를 실시간으로 출력"""
        with self.lock:
            state = self.engine.get_state()
            pet = state["pet"]
            ui = state["ui"]
            leds = self.engine.generate_led_command().get("payload", {}).get("leds", {})
            if not leds:
                leds = self.engine.generate_led_command().get("leds", {})

        # 터미널 화면 클리어 (ANSI Escape Code)
        sys.stdout.write("\033[H\033[J")

        # 다마고치 캐릭터 기분/상태 이모지
        if not pet["is_alive"]:
            mood_icon = "💀 (사망)"
        elif pet["is_sleeping"]:
            mood_icon = "💤 (수면 중... Zzz)"
        elif pet["satiety"] <= 30:
            mood_icon = "🥺 (배고파요!)"
        elif pet["happiness"] >= 70:
            mood_icon = "🥰 (아주 행복함!)"
        else:
            mood_icon = "🐣 (보통)"

        # LED 상태 표시 아이콘
        def led_tag(name: str) -> str:
            cfg = leds.get(name, {})
            mode = cfg.get("mode", "off")
            if mode == "on":
                return "🟢 ON   "
            elif mode == "blink":
                return "🟡 BLINK(경고!)"
            return "⚪ OFF  "

        # 메뉴 하이라이트 표시
        current_menu = ui["selected_menu"]
        def menu_box(m_name: str, label: str) -> str:
            if ui["mode"] == "sleep":
                return f"  [ {label} (수면 중) ]"
            if current_menu == m_name:
                return f"👉 [ {label} ] 👈"
            return f"   [ {label} ]"

        out = []
        out.append("=" * 65)
        out.append(f"  🐣 다마고치 하드웨어 조작기 로컬 플레이어  |  이름: {pet['name']} {mood_icon}")
        out.append("=" * 65)
        out.append(f"  포만감 (Satiety)   : {self._make_progress_bar(pet['satiety'])}   LED: {led_tag('satiety')}")
        out.append(f"  행복도 (Happiness) : {self._make_progress_bar(pet['happiness'])}   LED: {led_tag('happiness')}")
        out.append(f"  에너지 (Energy)    : {self._make_progress_bar(pet['energy'])}   LED: {led_tag('energy')}")
        out.append(f"  서버 연결 상태     : {'정상 연결':<24} LED: {led_tag('connection')}")
        out.append("-" * 65)
        out.append(f"  현재 모드: [{ui['mode'].upper()}]")
        out.append("  선택 메뉴:")
        out.append(f"    {menu_box('feed', '1. 먹이주기 (FEED)')}")
        out.append(f"    {menu_box('play', '2. 놀아주기 (PLAY)')}")
        out.append(f"    {menu_box('sleep', '3. 잠자기   (SLEEP)')}")
        out.append(f"    {menu_box('battle', '4. 대전하기 (BATTLE)')}")
        out.append("-" * 65)
        out.append(f"  📢 알림: {self.last_action_message}")
        out.append("=" * 65)
        out.append("  [물리 버튼 안내]")
        out.append("    🔘 버튼 A (#17) : 메뉴 이동 (다음 메뉴 선택)")
        out.append("    🔘 버튼 B (#27) : 선택 / 실행 (먹이/놀기/잠자기)")
        out.append("    🔘 버튼 C (#22) : 취소 / 기본 메뉴 복귀")
        out.append("  (종료하려면 Ctrl+C를 누르세요. 현재 상태가 자동 저장됩니다.)")
        out.append("=" * 65)

        sys.stdout.write("\n".join(out) + "\n")
        sys.stdout.flush()

    def _tick_loop(self):
        """1초마다 시간 경과(자연 배고픔/피로)를 반영하는 백그라운드 스레드"""
        save_counter = 0
        while self.running:
            time.sleep(1.0)
            if not self.running:
                break

            # 1초 경과 틱 적용
            self.engine.update_tick()
            self._render_ui()

            # 15초마다 자동 저장
            save_counter += 1
            if save_counter >= 15:
                save_counter = 0
                save_game(self.engine.tamagotchi)

    def start(self):
        """게임 실행"""
        # 백그라운드 틱 스레드 시작
        tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        tick_thread.start()

        self._render_ui()

        # 메인 루프 대기 (Ctrl+C 인터럽트 감지)
        try:
            while self.running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\n[INFO] 게임 종료 요청을 수신했습니다.")
        finally:
            self.running = False
            print("[INFO] 다마고치 상태를 저장하고 하드웨어를 안전하게 정리합니다...")
            save_game(self.engine.tamagotchi)
            self.hw.cleanup()
            print(f"[INFO] '{self.pet.name}'의 상태가 'data/save.json'에 안전하게 저장되었습니다!")
            print("[INFO] 게임이 성공적으로 종료되었습니다. 안녕히 가세요! 🐣")


if __name__ == "__main__":
    runner = LocalGameRunner()
    runner.start()
