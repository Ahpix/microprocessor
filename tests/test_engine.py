import pytest
from game_engine.core.tamagotchi import Tamagotchi
from game_engine.core.engine import GameEngine
from game_engine.core.constants import (
    MODE_HOME,
    MODE_SLEEP,
    MODE_BATTLE,
    MENU_FEED,
    MENU_PLAY,
    MENU_SLEEP,
    MENU_BATTLE,
    BUTTON_A,
    BUTTON_B,
    BUTTON_C,
)
from game_engine.battle.battle_manager import BattleManager


def test_initial_state():
    engine = GameEngine()
    state = engine.get_state()

    assert state["state_version"] == 1
    assert state["ui"]["mode"] == MODE_HOME
    assert state["ui"]["selected_menu"] == MENU_FEED
    assert state["battle"] is None
    assert state["pet"]["pet_id"] == "pet01"


def test_home_menu_navigation():
    engine = GameEngine()

    # A 누르면 메뉴 순환: feed -> play -> sleep -> battle -> feed
    engine.handle_button_event(BUTTON_A)
    assert engine.selected_menu == MENU_PLAY

    engine.handle_button_event(BUTTON_A)
    assert engine.selected_menu == MENU_SLEEP

    engine.handle_button_event(BUTTON_A)
    assert engine.selected_menu == MENU_BATTLE

    engine.handle_button_event(BUTTON_A)
    assert engine.selected_menu == MENU_FEED

    # C 누르면 feed로 초기화
    engine.handle_button_event(BUTTON_A)
    assert engine.selected_menu == MENU_PLAY
    engine.handle_button_event(BUTTON_C)
    assert engine.selected_menu == MENU_FEED


def test_sleep_mode_and_wake():
    engine = GameEngine()

    # Sleep 메뉴로 이동 후 선택
    engine.handle_button_event(BUTTON_A)  # play
    engine.handle_button_event(BUTTON_A)  # sleep
    engine.handle_button_event(BUTTON_B)  # 선택 -> 수면 돌입

    assert engine.mode == MODE_SLEEP
    assert engine.selected_menu is None
    assert engine.tamagotchi.is_sleeping is True

    # 수면 중 A, C는 무시됨
    engine.handle_button_event(BUTTON_A)
    assert engine.mode == MODE_SLEEP
    engine.handle_button_event(BUTTON_C)
    assert engine.mode == MODE_SLEEP

    # B 누르면 깨우기 동작 -> 홈 복귀
    engine.handle_button_event(BUTTON_B)
    assert engine.mode == MODE_HOME
    assert engine.selected_menu == MENU_FEED
    assert engine.tamagotchi.is_sleeping is False


def test_led_command_generation():
    engine = GameEngine()
    led_cmd = engine.generate_led_command()

    # 기본 상태: satiety 100, happiness 50, energy 100 -> 전부 ON (> 30)
    assert led_cmd["leds"]["satiety"]["mode"] == "on"
    assert led_cmd["leds"]["happiness"]["mode"] == "on"
    assert led_cmd["leds"]["energy"]["mode"] == "on"
    assert led_cmd["leds"]["connection"]["mode"] == "on"

    # 스탯 30 이하 시 blink 확인
    engine.tamagotchi.satiety = 20
    led_cmd = engine.generate_led_command()
    assert led_cmd["leds"]["satiety"]["mode"] == "blink"
    assert led_cmd["leds"]["satiety"]["period_ms"] == 1000

    # 연결 해제 시 connection blink 확인
    engine.set_connection_status(False)
    led_cmd = engine.generate_led_command()
    assert led_cmd["leds"]["connection"]["mode"] == "blink"

    # 사망 시 캐릭터 LED는 off
    engine.tamagotchi.is_alive = False
    led_cmd = engine.generate_led_command()
    assert led_cmd["leds"]["satiety"]["mode"] == "off"
    assert led_cmd["leds"]["happiness"]["mode"] == "off"
    assert led_cmd["leds"]["energy"]["mode"] == "off"


def test_duplicate_message_id_rejection():
    engine = GameEngine()
    msg_id = "test-msg-001"

    res1 = engine.handle_button_event(BUTTON_A, message_id=msg_id)
    assert res1["status"] == "accepted"

    # 같은 message_id로 재전송 시 duplicate 반환 및 중복 적용 차단
    res2 = engine.handle_button_event(BUTTON_A, message_id=msg_id)
    assert res2["status"] == "duplicate"
