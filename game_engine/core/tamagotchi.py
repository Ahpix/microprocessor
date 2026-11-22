import time
from typing import Dict, Any, Optional


class Tamagotchi:
    # ===== 밸런스 설정 (docs/protocol.md 및 README.md 기준) =====

    # 시간당 능력치 자연 감소량
    ENERGY_DECAY = 5    # 시간당 에너지 감소량
    SATIETY_DECAY = 5   # 시간당 포만감 감소량
    HAPPINESS_DECAY = 2 # 시간당 행복도 감소량

    # 행동에 따른 능력치 변화
    FEED_AMOUNT = 30

    PLAY_HAPPINESS = 20
    PLAY_SATIETY_COST = 15
    PLAY_ENERGY_COST = 15

    # 수면 설정
    SLEEP_DURATION = 60       # 수면 시간: 60초 (테스트용)
    SLEEP_ENERGY_RECOVERY = 30

    def __init__(self, name: str, pet_id: str = "pet01"):
        self.pet_id = pet_id
        self.name = name

        # 기본 능력치 (0 ~ 100 정수 유지 원칙)
        self.satiety: float = 100.0
        self.happiness: float = 50.0
        self.energy: float = 100.0

        # 생존 및 수면 상태
        self.is_alive: bool = True
        self.is_sleeping: bool = False
        self.sleep_end_time: Optional[float] = None

        # 마지막 갱신 시각 (Unix 초)
        self.last_update: float = time.time()

    # ===== 내부 공통 함수 =====

    def _clamp(self, value: float) -> float:
        return max(0.0, min(100.0, value))

    def _check_alive(self):
        """생존 여부 검사 (포만감이 0 이하로 떨어지면 사망 판정)"""
        if self.satiety <= 0:
            self.satiety = 0.0
            self.is_alive = False
            self.is_sleeping = False
            self.sleep_end_time = None

    def _update_stats(self):
        """시간 경과에 따른 상태 갱신 (프로토콜 규칙 준수)"""
        if not self.is_alive:
            return

        now = time.time()
        elapsed = now - self.last_update

        if elapsed <= 0:
            return

        elapsed_hours = elapsed / 3600.0

        self.satiety = self._clamp(
            self.satiety - self.SATIETY_DECAY * elapsed_hours
        )

        self.happiness = self._clamp(
            self.happiness - self.HAPPINESS_DECAY * elapsed_hours
        )

        # 수면 중 및 깨어있는 시간에 따른 에너지 처리
        awake_seconds = elapsed

        if self.is_sleeping:
            if self.sleep_end_time is not None:
                awake_seconds = max(
                    0.0, now - max(self.last_update, self.sleep_end_time)
                )

                # 수면이 종료되었으면 에너지 회복 및 기상
                if now >= self.sleep_end_time:
                    self.energy = self._clamp(
                        self.energy + self.SLEEP_ENERGY_RECOVERY
                    )
                    self.is_sleeping = False
                    self.sleep_end_time = None
            else:
                # 자동 기상 시간 지정이 없는 수면이면 깨어있는 시간 0
                awake_seconds = 0.0

        self.energy = self._clamp(
            self.energy - self.ENERGY_DECAY * awake_seconds / 3600.0
        )

        self.last_update = now
        self._check_alive()

    # ===== 육성 행동 함수 =====

    def feed(self) -> bool:
        """먹이 주기: 포만감 회복 (사망 상태나 수면 중에는 불가)"""
        self._update_stats()

        if not self.is_alive or self.is_sleeping:
            return False

        self.satiety = self._clamp(
            self.satiety + self.FEED_AMOUNT
        )
        return True

    def play(self) -> bool:
        """놀아주기: 행복도 상승, 포만감/에너지 소모 (사망 또는 수면 중 또는 에너지 부족 시 불가)"""
        self._update_stats()

        if not self.is_alive or self.is_sleeping or self.energy < self.PLAY_ENERGY_COST:
            return False

        self.happiness = self._clamp(
            self.happiness + self.PLAY_HAPPINESS
        )
        self.satiety = self._clamp(
            self.satiety - self.PLAY_SATIETY_COST
        )
        self.energy = self._clamp(
            self.energy - self.PLAY_ENERGY_COST
        )
        self._check_alive()
        return True

    def sleep(self) -> bool:
        """잠자기: 수면 상태 돌입 (사망 또는 이미 수면 중일 시 불가)"""
        self._update_stats()

        if not self.is_alive or self.is_sleeping:
            return False

        self.is_sleeping = True
        self.sleep_end_time = time.time() + self.SLEEP_DURATION
        return True

    def wake(self) -> bool:
        """깨우기: 수면 상태 해제 (protocol.md 5절 sleep 모드 B 버튼 대응)"""
        self._update_stats()

        if not self.is_alive or not self.is_sleeping:
            return False

        self.is_sleeping = False
        self.sleep_end_time = None
        return True

    # ===== 상태 조회 및 직렬화 =====

    def get_status(self) -> Dict[str, Any]:
        """기존 테스트 및 레거시 호환용 간이 상태 조회"""
        self._update_stats()

        return {
            "name": self.name,
            "satiety": round(self.satiety, 1),
            "happiness": round(self.happiness, 1),
            "energy": round(self.energy, 1),
            "is_sleeping": self.is_sleeping
        }

    def to_pet_dict(self) -> Dict[str, Any]:
        """docs/protocol.md의 4절 state.payload.pet 규격과 완전 일치하는 딕셔너리"""
        self._update_stats()

        return {
            "pet_id": self.pet_id,
            "name": self.name,
            "satiety": int(round(self.satiety)),
            "happiness": int(round(self.happiness)),
            "energy": int(round(self.energy)),
            "is_alive": self.is_alive,
            "is_sleeping": self.is_sleeping,
            "sleep_end_time": self.sleep_end_time if self.is_sleeping else None,
            "last_update": self.last_update
        }

    def get_battle_profile(self) -> Dict[str, Any]:
        """docs/protocol.md에 따른 배틀 초기 프로필 계산"""
        self._update_stats()

        max_hp = round(70 + self.satiety * 0.3)
        damage_multiplier = 1.0 + self.happiness * 0.002

        return {
            "max_hp": max_hp,
            "damage_multiplier": damage_multiplier
        }

    def to_dict(self) -> Dict[str, Any]:
        """save.json 저장용 딕셔너리 (하위 호환 및 신규 필드 포함)"""
        self._update_stats()

        return {
            "pet_id": self.pet_id,
            "name": self.name,
            "satiety": int(round(self.satiety)),
            "happiness": int(round(self.happiness)),
            "energy": int(round(self.energy)),
            "is_alive": self.is_alive,
            "is_sleeping": self.is_sleeping,
            "sleep_end_time": self.sleep_end_time if self.is_sleeping else None,
            "last_update": self.last_update
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tamagotchi":
        """딕셔너리에서 다마고치 복원 (save.json 호환)"""
        name = data.get("name", "Tama")
        pet_id = data.get("pet_id", "pet01")

        tama = cls(name=name, pet_id=pet_id)
        tama.satiety = float(data.get("satiety", 100))
        tama.happiness = float(data.get("happiness", 50))
        tama.energy = float(data.get("energy", 100))

        tama.is_alive = bool(data.get("is_alive", True))
        tama.is_sleeping = bool(data.get("is_sleeping", False))
        tama.sleep_end_time = data.get("sleep_end_time", None)
        tama.last_update = float(data.get("last_update", time.time()))

        # 불러온 시점의 오프라인 시간 경과 반영
        tama._update_stats()

        return tama
