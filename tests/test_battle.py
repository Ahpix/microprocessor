import pytest
from game_engine.battle.battle_manager import BattleManager
from game_engine.core.constants import (
    BATTLE_PHASE_CHOOSING,
    BATTLE_PHASE_RESULT,
    BATTLE_PHASE_ENDED,
    MOVE_ATTACK,
    MOVE_DEFEND,
    MOVE_SKILL,
    END_REASON_HP_ZERO,
)


def test_battle_flow_and_rps_rules():
    # p1: attack, p2: skill -> attack wins (p2 takes 20 dmg)
    bm = BattleManager(
        battle_id="b01",
        host_device_id="pi01",
        host_player_id="pet01",
        host_name="Tama",
        guest_player_id="pet02",
        guest_name="Mochi",
        host_max_hp=100,
        guest_max_hp=100,
    )

    assert bm.phase == BATTLE_PHASE_CHOOSING
    assert bm.turn == 1

    # p1 선택
    res1 = bm.choose("pet01", MOVE_ATTACK, turn=1)
    assert res1["success"] is True
    assert bm.players["pet01"].has_chosen is True
    # 선택 도중에는 상대에게 move가 노출되지 않음
    assert bm.to_dict()["players"][0]["has_chosen"] is True
    assert "move" not in bm.to_dict()["players"][0]

    # p2 선택 -> 양쪽 선택 완료로 즉시 result 단계 전환
    res2 = bm.choose("pet02", MOVE_SKILL, turn=1)
    assert res2["success"] is True
    assert bm.phase == BATTLE_PHASE_RESULT

    # p1(공격) > p2(스킬): p2 데미지 20
    assert bm.players["pet01"].hp == 100
    assert bm.players["pet02"].hp == 80

    # p2는 스킬을 사용했으므로 다음 턴 skill_available=False
    assert bm.players["pet02"].skill_available is False
    assert bm.players["pet01"].skill_available is True


def test_skill_cooldown():
    bm = BattleManager(
        battle_id="b02",
        host_device_id="pi01",
        host_player_id="pet01",
        host_name="Tama",
        guest_player_id="pet02",
        guest_name="Mochi",
    )

    # 1턴: p1이 skill 사용
    bm.choose("pet01", MOVE_SKILL, turn=1)
    bm.choose("pet02", MOVE_ATTACK, turn=1)  # attack > skill

    bm.next_turn()
    assert bm.turn == 2
    assert bm.phase == BATTLE_PHASE_CHOOSING

    # 2턴: p1이 다시 skill 시도 시 거절 (SKILL_COOLDOWN)
    res = bm.choose("pet01", MOVE_SKILL, turn=2)
    assert res["success"] is False
    assert res["error_code"] == "SKILL_COOLDOWN"

    # 다른 선택(defend)은 정상 수락
    res_defend = bm.choose("pet01", MOVE_DEFEND, turn=2)
    assert res_defend["success"] is True


def test_timeout_auto_defend(monkeypatch):
    bm = BattleManager(
        battle_id="b03",
        host_device_id="pi01",
        host_player_id="pet01",
        host_name="Tama",
        guest_player_id="pet02",
        guest_name="Mochi",
    )

    # p1만 선택
    bm.choose("pet01", MOVE_ATTACK, turn=1)

    # 타임아웃 강제 경과 시뮬레이션
    bm.deadline_mono = 0.0

    assert bm.check_timeout() is True
    assert bm.phase == BATTLE_PHASE_RESULT

    # p2는 자동 defend 선택되어 p2(defend) > p1(attack)으로 p1이 15 데미지 입음
    assert bm.players["pet02"].auto_selected is True
    assert bm.players["pet01"].hp == 85
    assert bm.players["pet02"].hp == 100
