import time
from typing import Dict, Any, Optional, List
from game_engine.core.constants import (
    BATTLE_PHASE_CHOOSING,
    BATTLE_PHASE_RESULT,
    BATTLE_PHASE_ENDED,
    END_REASON_HP_ZERO,
    END_REASON_TURN_LIMIT,
    END_REASON_DRAW,
    DEFAULT_MAX_HP,
    DEFAULT_MAX_TURNS,
    SELECTION_TIMEOUT_SECONDS,
    MOVE_ATTACK,
    MOVE_DEFEND,
    MOVE_SKILL,
    VALID_MOVES,
    DAMAGE_ATTACK_WIN,
    DAMAGE_DEFEND_WIN,
    DAMAGE_SKILL_WIN,
    DAMAGE_TIE,
)


class BattlePlayer:
    """배틀 참가자 상태 (protocol.md 10.3절 players 객체)"""

    def __init__(self, player_id: str, name: str, max_hp: int = DEFAULT_MAX_HP):
        self.player_id = player_id
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.skill_available = True
        self.has_chosen = False

        # 턴 내부 선택 정보 (결과 발표 전까지 비공개)
        self.current_move: Optional[str] = None
        self.auto_selected: bool = False
        self.used_skill_this_turn: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """protocol.md 10.3절 battle.players 항목 (상대에게 move를 노출하지 않음)"""
        return {
            "player_id": self.player_id,
            "name": self.name,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "skill_available": self.skill_available,
            "has_chosen": self.has_chosen,
        }


class BattleManager:
    """
    호스트 판정 1:1 배틀 매니저 (protocol.md 10절 전면 준수)
    - 상성: attack > skill, skill > defend, defend > attack
    - 5초 타임아웃 미선택 시 자동 defend
    - 스킬 사용 후 다음 1턴 재사용 불가(쿨다운)
    """

    def __init__(
        self,
        battle_id: str,
        host_device_id: str,
        host_player_id: str,
        host_name: str,
        guest_player_id: str,
        guest_name: str,
        host_max_hp: int = DEFAULT_MAX_HP,
        guest_max_hp: int = DEFAULT_MAX_HP,
    ):
        self.battle_id = battle_id
        self.host_device_id = host_device_id

        self.phase = BATTLE_PHASE_CHOOSING
        self.turn = 1
        self.max_turns = DEFAULT_MAX_TURNS
        self.selection_timeout_seconds = SELECTION_TIMEOUT_SECONDS

        # 플레이어 등록 (정확히 2명)
        self.players: Dict[str, BattlePlayer] = {
            host_player_id: BattlePlayer(host_player_id, host_name, host_max_hp),
            guest_player_id: BattlePlayer(guest_player_id, guest_name, guest_max_hp),
        }
        self.host_player_id = host_player_id
        self.guest_player_id = guest_player_id

        self.winner_player_id: Optional[str] = None
        self.end_reason: Optional[str] = None

        # 타임아웃 계산용 마감 시각 (monotonic 기반 판정 및 timestamp 초 노출)
        self.deadline_mono: float = time.monotonic() + self.selection_timeout_seconds
        self.deadline: float = time.time() + self.selection_timeout_seconds

        # 마지막 턴 결과 캐시 (protocol.md 10.5 result)
        self.last_turn_result: Optional[Dict[str, Any]] = None

    def choose(self, player_id: str, move: str, turn: int) -> Dict[str, Any]:
        """
        플레이어의 턴 선택 처리 (protocol.md 10.4 choose)
        반환값: {"success": bool, "error_code": Optional[str], "message": Optional[str]}
        """
        if self.phase != BATTLE_PHASE_CHOOSING:
            return {"success": False, "error_code": "INVALID_STATE", "message": "Not in choosing phase"}

        if turn != self.turn:
            return {"success": False, "error_code": "STALE_TURN", "message": f"Expected turn {self.turn}, got {turn}"}

        if player_id not in self.players:
            return {"success": False, "error_code": "NOT_AUTHORIZED", "message": "Unknown player"}

        if move not in VALID_MOVES:
            return {"success": False, "error_code": "INVALID_PAYLOAD", "message": "Invalid move"}

        player = self.players[player_id]

        if player.has_chosen:
            return {"success": False, "error_code": "INVALID_STATE", "message": "Move already chosen for this turn"}

        if move == MOVE_SKILL and not player.skill_available:
            return {"success": False, "error_code": "SKILL_COOLDOWN", "message": "Skill is on cooldown"}

        # 선택 저장
        player.current_move = move
        player.has_chosen = True
        player.auto_selected = False

        # 양쪽 모두 선택 완료 시 즉시 턴 확정 판정
        if all(p.has_chosen for p in self.players.values()):
            self._resolve_turn()

        return {"success": True, "error_code": None, "message": "Accepted"}

    def check_timeout(self) -> bool:
        """선택 마감 시간 초과 검사 및 자동 defend 처리"""
        if self.phase != BATTLE_PHASE_CHOOSING:
            return False

        if time.monotonic() >= self.deadline_mono:
            # 미선택 플레이어는 자동 defend
            for player in self.players.values():
                if not player.has_chosen:
                    player.current_move = MOVE_DEFEND
                    player.has_chosen = True
                    player.auto_selected = True

            self._resolve_turn()
            return True

        return False

    def _resolve_turn(self):
        """턴 결과 판정 (protocol.md 10.7 상성 및 데미지)"""
        p1 = self.players[self.host_player_id]
        p2 = self.players[self.guest_player_id]

        m1 = p1.current_move
        m2 = p2.current_move

        p1_dmg_taken = 0
        p2_dmg_taken = 0

        if m1 == m2:
            # 같은 선택이면 양쪽 5 데미지
            p1_dmg_taken = DAMAGE_TIE
            p2_dmg_taken = DAMAGE_TIE
        elif (
            (m1 == MOVE_ATTACK and m2 == MOVE_SKILL) or
            (m1 == MOVE_SKILL and m2 == MOVE_DEFEND) or
            (m1 == MOVE_DEFEND and m2 == MOVE_ATTACK)
        ):
            # p1 승리
            damage = (
                DAMAGE_ATTACK_WIN if m1 == MOVE_ATTACK else
                DAMAGE_SKILL_WIN if m1 == MOVE_SKILL else
                DAMAGE_DEFEND_WIN
            )
            p2_dmg_taken = damage
        else:
            # p2 승리
            damage = (
                DAMAGE_ATTACK_WIN if m2 == MOVE_ATTACK else
                DAMAGE_SKILL_WIN if m2 == MOVE_SKILL else
                DAMAGE_DEFEND_WIN
            )
            p1_dmg_taken = damage

        # 데미지 적용 (HP 0 미만으로 내려가지 않음)
        p1.hp = max(0, p1.hp - p1_dmg_taken)
        p2.hp = max(0, p2.hp - p2_dmg_taken)

        # 스킬 쿨다운 관리 (스킬 사용 시 다음 턴 skill_available=False)
        p1_skill_next = not (m1 == MOVE_SKILL)
        p2_skill_next = not (m2 == MOVE_SKILL)

        # 결과 페이로드 캐싱 (protocol.md 10.5 result 규격)
        self.last_turn_result = {
            "battle_id": self.battle_id,
            "turn": self.turn,
            "players": [
                {
                    "player_id": p1.player_id,
                    "move": m1,
                    "auto_selected": p1.auto_selected,
                    "damage_taken": p1_dmg_taken,
                    "hp": p1.hp,
                    "skill_available_next_turn": p1_skill_next,
                },
                {
                    "player_id": p2.player_id,
                    "move": m2,
                    "auto_selected": p2.auto_selected,
                    "damage_taken": p2_dmg_taken,
                    "hp": p2.hp,
                    "skill_available_next_turn": p2_skill_next,
                },
            ],
        }

        # 쿨다운 상태 갱신
        p1.skill_available = p1_skill_next
        p2.skill_available = p2_skill_next

        # 승패 종료 조건 검사
        if p1.hp <= 0 or p2.hp <= 0:
            self.phase = BATTLE_PHASE_ENDED
            self.deadline = None
            if p1.hp <= 0 and p2.hp <= 0:
                self.winner_player_id = None
                self.end_reason = END_REASON_DRAW
            elif p1.hp <= 0:
                self.winner_player_id = p2.player_id
                self.end_reason = END_REASON_HP_ZERO
            else:
                self.winner_player_id = p1.player_id
                self.end_reason = END_REASON_HP_ZERO
        elif self.turn >= self.max_turns:
            self.phase = BATTLE_PHASE_ENDED
            self.deadline = None
            if p1.hp > p2.hp:
                self.winner_player_id = p1.player_id
                self.end_reason = END_REASON_TURN_LIMIT
            elif p2.hp > p1.hp:
                self.winner_player_id = p2.player_id
                self.end_reason = END_REASON_TURN_LIMIT
            else:
                self.winner_player_id = None
                self.end_reason = END_REASON_DRAW
        else:
            self.phase = BATTLE_PHASE_RESULT

    def next_turn(self):
        """결과 확인 후 다음 턴 진행"""
        if self.phase != BATTLE_PHASE_RESULT:
            return

        self.turn += 1
        self.phase = BATTLE_PHASE_CHOOSING

        for p in self.players.values():
            p.has_chosen = False
            p.current_move = None
            p.auto_selected = False

        self.deadline_mono = time.monotonic() + self.selection_timeout_seconds
        self.deadline = time.time() + self.selection_timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        """protocol.md 10.3 state.battle 규격"""
        return {
            "battle_id": self.battle_id,
            "host_device_id": self.host_device_id,
            "phase": self.phase,
            "turn": self.turn,
            "max_turns": self.max_turns,
            "selection_timeout_seconds": self.selection_timeout_seconds,
            "deadline": self.deadline if self.phase == BATTLE_PHASE_CHOOSING else None,
            "players": [p.to_dict() for p in self.players.values()],
            "winner_player_id": self.winner_player_id,
            "end_reason": self.end_reason,
        }
