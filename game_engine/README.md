# 🐣 게임 엔진 (Game Engine) 개발 가이드 및 아키텍처 명세서

본 디렉터리는 **라즈베리파이 다마고치** 프로젝트의 핵심 게임 로직과 규칙 판정을 담당하는 `game_engine` 패키지입니다. `docs/protocol.md` 및 `README.md`의 표준 규격을 100% 준수하여 구현되었습니다.

---

## 1. 개요 및 설계 원칙

게임 엔진은 라즈베리파이 상에서 실행되며, 캐릭터의 생명주기 관리와 게임 진행 규칙을 전담합니다.

> **핵심 설계 원칙 (Separation of Concerns)**
> - **상태의 유일한 작성자**: 프론트엔드(Unity)나 하드웨어는 상태를 직접 수정하지 않으며, 게임 엔진만이 유일하게 캐릭터 상태(`state`)를 결정하고 갱신합니다.
> - **입력 해석의 책임**: 하드웨어 버튼 이벤트(`A`, `B`, `C`) 및 네트워크 요청을 현재 모드(홈, 수면, 배틀 등)에 맞게 해석·검증합니다.
> - **하드웨어 및 백엔드와의 분리**: 특정 통신 계층(WebSocket)이나 물리 핀 번호(GPIO)에 종속되지 않는 순수 도메인 엔진으로 동작합니다.

---

## 2. 디렉터리 구조

```text
game_engine/
├── __init__.py                # game_engine 패키지 초기화
├── README.md                  # [본 문서] 게임 엔진 아키텍처 및 모듈 가이드
├── core/
│   ├── __init__.py            # core 패키지 export (Tamagotchi, GameEngine)
│   ├── constants.py           # 프로토콜 공통 상수 (모드, 메뉴, 버튼, 밸런스, LED 임계값)
│   ├── tamagotchi.py          # 캐릭터 모델 (스탯, 육성 행동, 자연 감쇄, 생존/수면)
│   └── engine.py              # 최상위 게임 컨트롤러 (FSM, 버튼 디스패처, LED 명령, 스레드 동기화)
└── battle/
    ├── __init__.py            # battle 패키지 export (BattleManager, BattlePlayer)
    └── battle_manager.py      # 1:1 통신 배틀 엔진 (호스트 판정, 상성/데미지, 5초 타임아웃, 쿨다운)
```

---

## 3. 모듈별 상세 설명

### 3.1 `core/constants.py` (프로토콜 공통 상수)
`docs/protocol.md`에 정의된 모든 키값과 수치를 단일 모듈에서 관리합니다.

* **프로토콜 버전**: `PROTOCOL_VERSION = 1`
* **UI 모드 (`ui.mode`)**: `home`, `sleep`, `mini_game`, `battle`
* **홈 메뉴 순환 (`ui.selected_menu`)**: `feed` → `play` → `sleep` → `battle` → `feed`
* **버튼 식별자**: `A`, `B`, `C` (v1 지원 이벤트: `press`)
* **배틀 파라미터**: 
  - 기본 max_hp: `100`, 최대 턴 수: `10`
  - 턴 선택 제한 시간: `5초` (타임아웃 시 자동 defend)
  - 상성 데미지: 공격 승리 시 `20`, 방어 승리 시 `15`, 스킬 승리 시 `30`, 무승부 시 양측 `5`
* **LED 제어 임계값**: 스탯 `30` 이하 시 `blink` (주기 1000ms), 초과 시 `on`

---

### 3.2 `core/tamagotchi.py` (`Tamagotchi` 클래스)
다마고치 캐릭터의 순수 데이터 모델과 육성 규칙을 담당합니다.

* **관리 필드 (`protocol.md` 4절 준수)**:
  - `pet_id`: 캐릭터 고유 ID (기본값: `"pet01"`)
  - `name`: 캐릭터 이름
  - `satiety`, `happiness`, `energy`: 0 ~ 100 범위의 정수(int) 스탯
  - `is_alive`: 생존 상태 플래그 (포만감 고갈 시 `False` 판정)
  - `is_sleeping`: 수면 여부 플래그
  - `sleep_end_time`: 자동 기상 예정 Unix 시각 (초 단위)
  - `last_update`: 마지막 스탯 갱신 Unix 시각
* **주요 메서드**:
  - `feed() -> bool`: 포만감 회복 (+30). 수면 중 또는 사망 시 동작 불가.
  - `play() -> bool`: 행복도 상승 (+20), 포만감/에너지 소모 (-15).
  - `sleep() -> bool`: 60초간 수면 모드 돌입.
  - `wake() -> bool`: 수동 깨우기 (수면 중일 때 즉시 기상 처리).
  - `to_pet_dict() -> Dict[str, Any]`: 프로토콜의 `state.payload.pet` 스키마와 100% 호환되는 딕셔너리 반환.

---

### 3.3 `core/engine.py` (`GameEngine` 클래스)
하드웨어 및 백엔드와의 접점이 되는 최상위 게임 오케스트레이터입니다.

* **모드 상태 머신 (FSM) & 버튼 해석**:
  | 현재 모드 | 버튼 A | 버튼 B | 버튼 C |
  |:---:|:---:|:---:|:---:|
  | **home** | 다음 메뉴 순환 | 현재 메뉴 선택/실행 | 선택 초기화 (`feed`로 복귀) |
  | **sleep** | 동작 없음 | 깨우기 (`wake`) 후 홈 복귀 | 동작 없음 |
  | **battle** | 공격 (`attack`) 선택 | 방어 (`defend`) 선택 | 스킬 (`skill`) 선택 |
* **LED 제어 명령 생성 (`generate_led_command`)**:
  - 캐릭터 스탯(30 기준)과 연결 상태를 분석하여 하드웨어 제어 규격의 `led_command` JSON 생성
* **중복 요청 방지 및 안정성**:
  - 프로토콜 9절에 따라 최근 60초간 처리한 `message_id`를 캐싱하여 중복 요청 시 `{"status": "duplicate"}` 반환
  - `threading.Lock`을 적용하여 GPIO 콜백, 웹소켓 요청 쓰레드, 1초 주기 틱 타이머 간의 데이터 경합 방지

---

### 3.4 `battle/battle_manager.py` (`BattleManager` 클래스)
라즈베리파이 간 1:1 대전(호스트 기준)의 턴제 배틀 규칙을 판정합니다.

* **턴 관리 및 타임아웃**:
  - 턴당 5초 카운트다운 (`monotonic` 시계 기준 정확한 판정).
  - 마감 시간 초과 시 미선택 플레이어는 자동으로 `defend` 선택 처리 (`auto_selected = True`).
* **상성 가위바위보 규칙**:
  - `attack` > `skill` (승자 공격: 20 데미지)
  - `skill` > `defend` (승자 스킬: 30 데미지)
  - `defend` > `attack` (승자 방어: 15 데미지)
  - 무승부: 양측 5 데미지
* **스킬 쿨다운**:
  - 스킬 사용 시 다음 1턴 동안 `skill_available = False`로 변경되며, 재사용 시도시 `SKILL_COOLDOWN` 에러 반환.
* **비공개 선택 원칙**:
  - 턴 선택 진행 중에는 상대의 move를 노출하지 않고 `has_chosen` 완료 여부만 전달.
* **승패 판정**:
  - 어느 한 쪽의 HP가 0이 되거나 10턴 초과 시 승자 확정 (`end_reason`: `hp_zero`, `turn_limit`, `draw`).
  - *주의: 배틀 HP 0은 캐릭터의 육성 생존(`is_alive`)과 무관합니다.*

---

## 4. 백엔드 및 하드웨어 연동 예시

### 4.1 엔진 초기화 및 상태 구독
```python
from game_engine.core.engine import GameEngine
from game_engine.core.tamagotchi import Tamagotchi

# 상태 변경 및 LED 명령 발생 시 실행할 콜백 등록
def on_state_updated(state_data):
    # Unity 클라이언트로 WebSocket 브로드캐스트
    pass

def on_led_command_generated(led_command):
    # hardware_manager.handle_led_command(led_command) 호출
    pass

engine = GameEngine(
    tamagotchi=Tamagotchi("Tama"),
    on_state_change=on_state_updated,
    on_led_command=on_led_command_generated
)
```

### 4.2 버튼 이벤트 전달
```python
# 하드웨어 GPIO 콜백 또는 Unity button_event 수신 시
result = engine.handle_button_event(
    button="A", 
    event="press", 
    message_id="pi01-hw-000001"
)
```

### 4.3 주기적 틱(Tick) 실행
```python
# 백엔드의 1초 주기 타이머 루프에서 호출
engine.update_tick()
```

---

## 5. 단위 테스트 실행

프로젝트 루트 디렉터리에서 `pytest` 명령을 통해 모든 단위 테스트를 실행할 수 있습니다:

```bash
pytest
```
*테스트 스위트(`tests/`)에서 캐릭터 육성, 모드 FSM, LED 제어 생성, 1:1 배틀 상성 및 쿨다운, JSON 저장/로드 등 17개 항목을 전수 검증합니다.*
