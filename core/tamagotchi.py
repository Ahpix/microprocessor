import time


class Tamagotchi:
    # ===== 밸런스 설정 (테스트용 임시 수치) =====

    # 시간당 능력치 감소량
    ENERGY_DECAY = 5  # 시간당 에너지 감소량
    SATIETY_DECAY = 5
    HAPPINESS_DECAY = 2

    # 행동에 따른 능력치 변화
    FEED_AMOUNT = 30

    PLAY_HAPPINESS = 20
    PLAY_SATIETY_COST = 15
    PLAY_ENERGY_COST = 15

    # 수면 설정
    SLEEP_DURATION = 60       # 수면 시간: 60초 (테스트용)
    SLEEP_ENERGY_RECOVERY = 30

    def __init__(self, name):
        self.name = name

        # 기본 능력치
        self.satiety = 100
        self.happiness = 50
        self.energy = 100

        # 수면 상태
        self.is_sleeping = False
        self.sleep_end_time = None

        # 마지막 갱신 시각
        self.last_update = time.time()

    # ===== 공통 함수 =====

    def _clamp(self, value):
        return max(0, min(100, value))

    def _update_stats(self):
        now = time.time()
        elapsed = now - self.last_update

        if elapsed <= 0:
            return

        elapsed_hours = elapsed / 3600

        self.satiety = self._clamp(
            self.satiety - self.SATIETY_DECAY * elapsed_hours
        )

        self.happiness = self._clamp(
            self.happiness - self.HAPPINESS_DECAY * elapsed_hours
        )

        # 깨어 있는 시간에만 에너지 감소
        awake_seconds = elapsed

        if self.is_sleeping:
            awake_seconds = max(
                0, now - max(self.last_update, self.sleep_end_time)
            )

            # 수면이 종료되었으면 에너지 회복
            if now >= self.sleep_end_time:
                self.energy = self._clamp(
                    self.energy + self.SLEEP_ENERGY_RECOVERY
                )

                self.is_sleeping = False
                self.sleep_end_time = None

        self.energy = self._clamp(
            self.energy - self.ENERGY_DECAY * awake_seconds / 3600
        )

        self.last_update = now

    # ===== 행동 함수 =====

    def feed(self):
        self._update_stats()

        if self.is_sleeping:
            return False

        self.satiety = self._clamp(
            self.satiety + self.FEED_AMOUNT
        )

        return True

    def play(self):
        self._update_stats()

        if self.is_sleeping or self.energy < self.PLAY_ENERGY_COST:
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

        return True

    def sleep(self):
        self._update_stats()

        if self.is_sleeping:
            return False

        self.is_sleeping = True
        self.sleep_end_time = time.time() + self.SLEEP_DURATION

        return True

    # ===== 상태 확인 =====

    def get_status(self):
        self._update_stats()

        return {
            "name": self.name,
            "satiety": round(self.satiety, 1),
            "happiness": round(self.happiness, 1),
            "energy": round(self.energy, 1),
            "is_sleeping": self.is_sleeping
        }

    # ===== 배틀 능력치 =====

    def get_battle_profile(self):
        self._update_stats()

        max_hp = round(70 + self.satiety * 0.3)

        damage_multiplier = (
            1.0 + self.happiness * 0.002
        )

        return {
            "max_hp": max_hp,
            "damage_multiplier": damage_multiplier
        }


    # ===== 데이터 변환 =====

    def to_dict(self):
        """현재 다마고치 상태를 딕셔너리로 변환"""

        self._update_stats()

        return {
            "name": self.name,
            "satiety": self.satiety,
            "happiness": self.happiness,
            "energy": self.energy,
            "is_sleeping": self.is_sleeping,
            "sleep_end_time": self.sleep_end_time,
            "last_update": self.last_update
        }

    @classmethod
    def from_dict(cls, data):
        """딕셔너리에서 다마고치 복원"""

        tama = cls(data["name"])

        tama.satiety = data["satiety"]
        tama.happiness = data["happiness"]
        tama.energy = data["energy"]

        tama.is_sleeping = data["is_sleeping"]
        tama.sleep_end_time = data["sleep_end_time"]
        tama.last_update = data["last_update"]

        # 불러온 시점의 시간 경과 반영
        tama._update_stats()

        return tama
