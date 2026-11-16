# 다마고치 통신 프로토콜

- 규격 버전: `1`
- 상태: 팀 구현 합의를 위한 v1 기준안
- 대상: 라즈베리파이 하드웨어 모듈, 게임 엔진·WebSocket 서버, Unity 클라이언트, 상대 파이
- 근거: 프로젝트 발표 자료의 버튼 3개, LED 4개, 선택적 배터리 모듈, WebSocket 연결 및 호스트 판정 배틀 구성

이 문서에서 **필수**는 반드시 지킬 규칙, **권장**은 기본 구현 방침이다. 발표 자료에서 미확정된 동작은 이 문서의 제안값이며, 변경 시 팀원 간 합의하고 문서를 함께 수정한다.

## 1. 구조와 책임

```text
버튼·배터리 → 하드웨어 모듈 → 게임 엔진 → 상태 → Unity
                   ↑             ↓
                   └── LED 명령 ─┘
                                 ↕
                           상대 파이(배틀)
```

- 게임 엔진이 캐릭터 상태의 유일한 작성자다.
- 하드웨어 모듈은 디바운스를 거친 물리 버튼 입력과 측정값만 전달한다.
- 버튼을 메뉴 이동·확인·공격 등으로 해석하는 책임은 엔진에 있다.
- Unity는 서버 상태를 표시한다. 클라이언트가 보낸 능력치·HP를 서버가 그대로 적용해서는 안 된다.
- 배틀 상태와 판정은 호스트가 관리한다.
- 하드웨어 모듈과 엔진이 같은 파이 프로세스에 있다면 함수·큐로 전달해도 된다. 아래 JSON의 필드 의미는 그대로 유지한다. GPIO 정보를 외부 WebSocket에 공개할 필요는 없다.

## 2. 전송과 공통 형식

- 외부 연결은 WebSocket을 사용한다. 접속 주소·포트는 배포 설정으로 관리하며 이 규격에 고정하지 않는다.
- 인코딩은 UTF-8, WebSocket 텍스트 메시지 하나에 JSON 객체 하나다.
- JSON 표준을 따른다. 주석, 후행 쉼표, `NaN`, `Infinity`는 금지한다.
- 키 이름은 `snake_case`를 사용한다.
- 모든 시각은 Unix timestamp **초 단위** 숫자다. 소수점을 허용한다. 밀리초와 혼용하지 않는다.
- 지속시간은 필드명에 단위를 표기한다. 예: `period_ms`, `timeout_seconds`.

```json
{
  "protocol_version": 1,
  "type": "button_event",
  "message_id": "pi01-run01-000001",
  "device_id": "pi01",
  "timestamp": 1794755306.6653366,
  "payload": {
    "button": "B",
    "event": "press"
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| protocol_version | integer | 예 | v1에서는 1 |
| type | string | 예 | 메시지 종류 |
| message_id | string | 예 | 송신자가 생성하는 고유 ID |
| device_id | string | 예 | 송신 기기 식별자 |
| timestamp | number | 예 | 메시지 생성 시각, Unix 초 |
| payload | object | 예 | 종류별 데이터. 데이터가 없어도 `{}` |

`message_id`는 UUID 또는 `기기 ID-실행 ID-순번` 형식을 권장한다. 재부팅 후에도 겹치지 않아야 한다. 동일 메시지를 재전송하면 원래 ID를 유지한다. `device_id`는 식별자일 뿐 인증 수단이 아니다.

표에서 필수로 정의한 필드는 생략할 수 없다. 선택 필드는 생략할 수 있지만, 명시적으로 `null`이 허용된 필드 외에는 `null`을 보내지 않는다. 수신자는 같은 버전의 알 수 없는 추가 필드를 무시한다.

## 3. 메시지 목록

| type | 방향 | 목적 |
|---|---|---|
| state | 엔진 → Unity | 전체 게임 상태 |
| state_request | Unity → 엔진 | 접속·재접속 후 전체 상태 요청 |
| button_event | 하드웨어 또는 Unity → 엔진 | A/B/C 입력 |
| hardware_status | 하드웨어 → 엔진 | 배터리 상태 |
| led_command | 엔진 → 하드웨어 | LED 출력 |
| ping | Unity → 파이 | 연결 확인 요청 |
| pong | 파이 → Unity | 연결 확인 응답 및 배터리 |
| ack | 수신자 → 송신자 | 입력·요청 처리 결과 |
| error | 수신자 → 송신자 | 잘못된 메시지·처리 실패 |
| battle_invite | 게스트 → 호스트 | 배틀 신청 |
| accept | 호스트 → 게스트 | 배틀 수락 및 식별자 발급 |
| mini_game | 호스트 → 참가자 | 미니게임 시작·진행·결과 |
| mini_game_input | 게스트 → 호스트 | 미니게임 버튼 입력 |
| choose | 게스트 → 호스트 | 배틀 턴 선택 |
| result | 호스트 → 참가자 | 확정 턴 결과 |
| battle_end | 호스트 → 참가자 | 최종 승패·무효 처리 |

아래 예시에서는 별도 표시가 없으면 공통 필드를 제외한 **payload만** 제시한다.

## 4. 게임 상태: state

```json
{
  "state_version": 42,
  "pet": {
    "pet_id": "pet01",
    "name": "Tama",
    "satiety": 70,
    "happiness": 80,
    "energy": 60,
    "is_alive": true,
    "is_sleeping": false,
    "sleep_end_time": null,
    "last_update": 1794755306.6653366
  },
  "ui": {
    "mode": "home",
    "selected_menu": "feed"
  },
  "battle": null
}
```

위 예시의 모든 필드는 필수다. 배틀이 없으면 `battle`은 `null`이다.

| 필드 | 타입·범위 | 규칙 |
|---|---|---|
| state_version | 0 이상의 integer | 클라이언트에 보이는 상태가 바뀔 때 증가. 변경 없이 재전송하면 유지 |
| pet.pet_id | string | 캐릭터 고유 ID |
| pet.name | string | 표시 이름 |
| pet.satiety | integer, 0~100 | 높을수록 배부름. hunger라는 별도 필드를 혼용하지 않음 |
| pet.happiness | integer, 0~100 | 높을수록 행복 |
| pet.energy | integer, 0~100 | 높을수록 에너지 충분 |
| pet.is_alive | boolean | 육성 캐릭터 생존 여부 |
| pet.is_sleeping | boolean | 수면 여부 |
| pet.sleep_end_time | number 또는 null | 자동 기상 예정 Unix 초. 자동 기상 미사용·비수면이면 null |
| pet.last_update | number | 시간 경과에 따른 상태 변화를 마지막으로 계산한 시각 |
| ui.mode | string | home / sleep / mini_game / battle |
| ui.selected_menu | string 또는 null | feed / play / sleep / battle. 홈이 아니면 null |
| battle | object 또는 null | 배틀 중 표시할 상태. 10절 참고 |

### 불변 조건

- `is_sleeping=false`이면 `sleep_end_time=null`이다.
- 수면 중이어도 자동 기상 기능이 없으면 `sleep_end_time=null`일 수 있다.
- `satiety`, `happiness`, `energy`는 엔진이 0~100으로 제한한다.
- 사망한 캐릭터의 일반 육성·배틀 입력은 거절한다. 초기화 기능은 v1 범위 밖이다.
- 배틀 HP 0은 패배를 뜻하며 육성 캐릭터의 사망을 뜻하지 않는다.
- 레벨·경험치·진화 및 표시 감정은 v1 필수가 아니다.

엔진은 유효한 상태 변경 후 `state` 전체를 전송한다. 부분 변경 메시지는 v1에서 사용하지 않는다. 클라이언트는 같은 연결에서 낮은 `state_version`을 무시한다. 엔진 재시작·재접속 후에는 최초 `state`를 새로운 기준으로 수용한다.

### state_request

payload는 `{}`다. 최초 연결·재접속 직후 요청하며, 서버는 현재 전체 `state`로 응답한다.

### 저장 파일과의 구분

네트워크 봉투 전체를 저장 파일로 사용할 필요는 없다. 현재의 평면 캐릭터 JSON은 `state.payload.pet`에 대응한다. `pet_id`, `is_alive`를 보완해 저장하고, 메뉴·연결 같은 일시 상태는 복원 시 초기화할 수 있다. 오프라인 경과 반영은 엔진이 `last_update`를 기준으로 계산한다. 감소 주기·감소량·최대 오프라인 반영 시간은 별도의 게임 밸런스 설정으로 정한다.

## 5. 버튼 입력: button_event

```json
{
  "button": "B",
  "event": "press"
}
```

두 필드는 필수다. `button`은 `A`, `B`, `C`만, `event`는 v1에서 `press`만 허용한다.

- 한 번 눌렀을 때 한 번 전송한다. 누르고 있는 동안 자동 반복하지 않는다.
- 디바운스는 하드웨어 계층에서 처리한다. 초기 설정은 30~50ms를 권장하되 실제 버튼으로 조정한다.
- GPIO 번호, HIGH/LOW, 풀업 방식은 하드웨어 내부 설정이다. 네트워크 규격에 포함하지 않는다.
- Unity가 화면 입력을 제공하면 동일한 `button_event`를 사용하며 자신의 `device_id`를 보낸다.
- 엔진은 수신 시점의 모드와 메뉴를 기준으로 순차 처리한다. 연결이 끊긴 동안 발생한 버튼을 재접속 후 몰아서 전송하지 않는다.

| 모드 | A | B | C |
|---|---|---|---|
| home | 다음 메뉴 | 선택·확인 | 취소·상태 보기 |
| mini_game | A 입력 | B 입력 | C 입력 |
| battle | attack | defend | skill |
| sleep | 동작 없음 | 깨우기 | 동작 없음 |

수면 중 B로 깨우기는 v1 제안 규칙이다. 홈 메뉴 순서는 `feed → play → sleep → battle → feed`로 한다. 홈의 C는 선택을 `feed`로 되돌리고 현재 상태를 다시 전송한다. 행동의 비용·보상과 실행 가능 조건은 엔진의 게임 규칙으로 관리한다.

## 6. 하드웨어 상태: hardware_status

```json
{
  "battery": {
    "available": true,
    "percentage": 85
  }
}
```

`battery`, `available`, `percentage`는 필수다.

- `available=true`이면 `percentage`는 유효한 0~100 정수다.
- 모듈 없음·읽기 실패·유효한 잔량 추정 미지원이면 `available=false`, `percentage=null`로 보낸다.
- 측정 불가를 0%로 보내지 않는다.
- 전압·전류 측정 모듈을 사용하더라도 잔량 % 추정 로직이 별도로 필요할 수 있다.
- 시작 시와 이후 약 5초마다 보고하는 것을 권장한다. 엔진은 최신 값을 보관해 `pong`에 포함한다.
- 마지막 보고 후 15초 이상 경과한 배터리 정보는 유효하지 않은 것으로 취급하고 `pong`에서 `available=false`, `percentage=null`로 표시한다.

모듈이 없을 때의 payload:

```json
{
  "battery": {
    "available": false,
    "percentage": null
  }
}
```

## 7. LED 출력: led_command

```json
{
  "leds": {
    "satiety": { "mode": "on" },
    "happiness": { "mode": "on" },
    "energy": { "mode": "blink", "period_ms": 1000 },
    "connection": { "mode": "on" }
  }
}
```

- `leds` 및 네 LED 항목은 필수다. 항상 네 개 전체를 보낸다.
- `mode`: `off`, `on`, `blink` 중 하나.
- `blink`이면 양의 정수 `period_ms`가 필수다. 그 외 모드에서는 생략한다.
- `period_ms`는 켜짐과 꺼짐을 합한 한 주기이며 듀티비는 50%다.
- 이전 깜빡임 작업은 새 명령 적용 시 교체한다. 중복 타이머를 만들지 않는다.

### v1 표시 정책

| LED | 조건 | 출력 |
|---|---|---|
| satiety / happiness / energy | 대응 값 > 30 | on |
| satiety / happiness / energy | 대응 값 ≤ 30 | blink, 1000ms |
| connection | 지정 Unity 클라이언트 heartbeat 정상 | on |
| connection | 미연결·heartbeat 이상 | blink, 1000ms |

상태 LED 임계값 30은 제안값이다. 사망 시 상태 LED 세 개는 `off`로 한다. 연결 LED는 별도로 동작한다. v1은 파이 하나당 주 Unity 클라이언트 하나를 가정한다.

네트워크가 끊어져도 연결 LED가 바뀌도록 파이 내부 heartbeat 감시기가 제어한다. 이 로컬 장애 표시가 일반 LED 명령보다 우선한다. 하드웨어 모듈이 엔진 명령을 받지 못하는 구조라면 별도 감시 경로를 구현해야 한다.

## 8. Heartbeat: ping / pong

Unity는 1초마다 `ping`을 보내고, 파이는 가능한 즉시 `pong`으로 응답한다.

ping payload:

```json
{}
```

pong payload:

```json
{
  "reply_to": "phone01-run01-000031",
  "battery": {
    "available": true,
    "percentage": 85
  }
}
```

- `reply_to`는 대응하는 ping의 `message_id`다.
- `battery` 형식은 6절과 같다. 측정 불가이면 null 규칙을 적용한다.
- Unity: 마지막 유효한 pong 수신 후 3초 이상이면 연결 이상.
- 파이: 마지막 유효한 ping 수신 후 3초 이상이면 연결 이상.
- 배터리 20% 이하이면 Unity에 경고를 표시한다. 측정 불가이면 %와 저전력 경고를 표시하지 않는다.
- timeout 계산에는 각 장치의 monotonic clock을 사용한다. 상대의 timestamp와 자신의 현재 시각을 빼서 판단하지 않는다.
- 이 메시지는 JSON 애플리케이션 메시지이며 WebSocket 자체 Ping/Pong 제어 프레임과 다르다.
- 재접속은 1, 2, 4, 8초 간격으로 증가시키고 이후 8초 간격으로 유지하는 방식을 권장한다.

## 9. 처리 확인·오류·동시성

### ack

상태 변경 요청(`button_event`, 배틀 신청·수락·입력·선택)에 처리 결과를 응답한다. `state`, `led_command`, `hardware_status`, `ping`, `pong`, `ack`, `error`에는 별도의 ack를 보내지 않는다. `state_request`에는 state가 응답이다.

```json
{
  "reply_to": "pi01-run01-000001",
  "status": "accepted"
}
```

`status`는 `accepted` 또는 `duplicate`다. `accepted`는 엔진이 해당 입력을 처리 대상으로 수락했다는 뜻이며, 실제 결과는 `state` 또는 배틀 결과 메시지로 확인한다. 적용 불가능한 요청에는 ack 대신 error를 보낸다.

### error

```json
{
  "reply_to": "pi01-run01-000001",
  "code": "INVALID_PAYLOAD",
  "message": "button must be A, B, or C"
}
```

`reply_to`는 원본 ID를 알 수 없으면 null이다. `code`와 `message`는 필수다. 프로그램은 문구가 아닌 code로 분기한다.

| code | 의미 |
|---|---|
| INVALID_JSON | JSON 파싱 실패 |
| UNSUPPORTED_VERSION | 지원하지 않는 protocol_version |
| UNKNOWN_TYPE | 지원하지 않는 type |
| INVALID_PAYLOAD | 필수 필드·타입·열거값·범위 오류 |
| INVALID_STATE | 현재 모드·생존·자원 조건에서 실행 불가 |
| STALE_TURN | 현재 배틀·턴·단계와 불일치 |
| SKILL_COOLDOWN | 스킬 재사용 대기 중 |
| NOT_AUTHORIZED | 해당 연결에 허용되지 않는 메시지 |
| INTERNAL_ERROR | 서버 처리 실패 |

### 중복·경합 처리

- 엔진은 상태 변경 입력을 큐 하나로 순차 처리하거나 동일한 잠금으로 보호한다. GPIO 콜백·tick·네트워크가 동시에 상태를 수정하지 않는다.
- 최근 처리 ID를 최소 60초 동안 보관해 같은 요청을 두 번 실행하지 않는다. 배틀 선택 기록은 해당 배틀 종료까지 보관한다.
- 중복 입력은 상태를 다시 바꾸지 않고 `ack.status=duplicate`로 응답한다. 원래 거절된 요청의 재전송에는 같은 오류를 반환한다.
- 버튼 이벤트는 자동 재전송하지 않는 것을 기본으로 한다. ack 유실이 발생해도 사용자가 새로 누른 입력은 새로운 ID를 사용한다.
- timeout 이후의 재시도를 허용하는 다른 요청은 같은 ID를 유지해야 한다. v1의 중복 방지는 실행 중 메모리 기준이며 서버 재시작을 넘는 exactly-once를 보장하지 않는다.
- 연결별 역할을 구분한다. Unity가 `led_command`, `hardware_status`, `result` 등을 보내는 것은 허용하지 않는다. 외부 기기를 허용하는 환경에서는 인증·전송 보안을 별도로 적용한다.

## 10. 배틀 확장 규격

육성·연결 구현을 먼저 완료한 뒤 이 절을 구현한다. 미구현 서버는 배틀 요청에 `INVALID_STATE`로 응답한다.

### 10.1 공통 원칙

- 게스트가 호스트에 신청하고, 호스트가 수락 시 `battle_id`를 발급한다.
- `player_id`는 참가자의 pet_id이며 호스트가 해당 연결에 묶어 검증한다. 게스트가 타인의 ID를 주장할 수 없다.
- 호스트 자신의 입력은 로컬 큐로 같은 검증 경로에 넣는다.
- 선택은 턴당 한 번만 수락한다. 중복 메시지는 재적용하지 않고, 다른 ID로 선택 변경을 시도하면 `INVALID_STATE`다.
- 선택 제한은 호스트 기준 5초다. 미선택은 자동 defend다.
- 스킬 사용 다음 턴에는 skill을 거절하고 `SKILL_COOLDOWN`을 응답한다. 마감 전 다른 선택을 받을 수 있고, 끝내 미선택이면 defend다.
- 선택 중 상대의 move는 전송하지 않는다. 양쪽 선택 확정 또는 timeout 후 result에 공개한다.
- v1은 신뢰하는 호스트 기반 시연용이다. 호스트의 선열람까지 막는 암호학적 동시 선택은 보장하지 않는다. 필요 시 commit-reveal을 별도 버전으로 추가한다.
- 파이 간 heartbeat도 ping/pong을 사용한다. 호스트가 1초마다 ping을 보내며 양쪽 모두 3초 무응답이면 연결 이상으로 본다.
- 연결 이상 시 판정을 멈추고 10초간 재연결을 기다린다. 재연결돼도 진행 중 배틀은 무효 종료하고 새 배틀을 시작한다. 10초 후에도 복구되지 않으면 로컬에서 무효 표시하며, 상대가 돌아오면 동일 무효 종료를 통지한다. 중단 턴 복원은 v1 범위 밖이다.

### 10.2 신청·수락

battle_invite payload:

```json
{
  "player_id": "pet02",
  "name": "Mochi"
}
```

accept payload:

```json
{
  "reply_to": "pi02-run01-000010",
  "battle_id": "battle001",
  "host_player_id": "pet01",
  "guest_player_id": "pet02"
}
```

모든 필드는 필수다. `reply_to`는 신청 메시지 ID다. 서버는 참가자 상태를 검증한다. 수락 후 호스트가 초기 battle 상태를 알린다. 거절은 `INVALID_STATE` 오류로 알린다.

### 10.3 state의 battle 객체

```json
{
  "battle_id": "battle001",
  "host_device_id": "pi01",
  "phase": "choosing",
  "turn": 3,
  "max_turns": 10,
  "selection_timeout_seconds": 5,
  "deadline": 1794755315.0,
  "players": [
    {
      "player_id": "pet01",
      "name": "Tama",
      "hp": 80,
      "max_hp": 100,
      "skill_available": true,
      "has_chosen": false
    },
    {
      "player_id": "pet02",
      "name": "Mochi",
      "hp": 65,
      "max_hp": 100,
      "skill_available": false,
      "has_chosen": true
    }
  ],
  "winner_player_id": null,
  "end_reason": null
}
```

위 필드는 모두 필수다. players는 정확히 두 명이며 hp는 0~max_hp 정수다.

- phase: `mini_game`, `choosing`, `result`, `reconnect_wait`, `ended`.
- turn: 배틀 시작 전 0, 정규 턴은 1~10.
- deadline: 호스트 시계의 선택 마감 Unix 초. 선택 단계가 아니면 null. 실제 timeout은 호스트 monotonic clock으로 판정한다.
- has_chosen은 선택 완료 여부만 노출하며 move는 노출하지 않는다.
- winner_player_id: 미종료·무승부·무효이면 null.
- end_reason: 미종료이면 null, 종료 시 `hp_zero`, `turn_limit`, `draw`, `disconnect` 중 하나.

클라이언트 countdown은 안내용이다. 기기 시계 오차가 있더라도 입력의 최종 수락 여부는 호스트가 결정한다.

### 10.4 choose

```json
{
  "battle_id": "battle001",
  "turn": 3,
  "player_id": "pet02",
  "move": "attack"
}
```

모든 필드는 필수다. move는 `attack`, `defend`, `skill`이다. 배틀 ID·턴·참가자·단계를 검증하고 과거·미래 턴 입력을 거절한다.

### 10.5 result

```json
{
  "battle_id": "battle001",
  "turn": 3,
  "players": [
    {
      "player_id": "pet01",
      "move": "skill",
      "auto_selected": false,
      "damage_taken": 0,
      "hp": 80,
      "skill_available_next_turn": false
    },
    {
      "player_id": "pet02",
      "move": "defend",
      "auto_selected": true,
      "damage_taken": 30,
      "hp": 35,
      "skill_available_next_turn": true
    }
  ]
}
```

모든 필드는 필수다. players는 두 명이다. `damage_taken`은 0 이상의 정수다. 게스트는 별도 데미지를 재계산해 덮어쓰지 않고 호스트 결과를 사용한다.

### 10.6 battle_end

```json
{
  "battle_id": "battle001",
  "winner_player_id": "pet01",
  "reason": "hp_zero",
  "players": [
    { "player_id": "pet01", "final_hp": 80, "happiness_delta": 0 },
    { "player_id": "pet02", "final_hp": 0, "happiness_delta": 0 }
  ]
}
```

모든 필드는 필수다. reason은 10.3절의 end_reason과 같다. 무승부·연결 끊김 무효는 winner_player_id가 null이다. `happiness_delta`는 실제 적용된 정수 변화량이다. 보상은 각 소유 엔진이 battle_id 기준 한 번만 적용하며, 무효 배틀에는 적용하지 않는다. 종료 후 최종 state를 전송하고 홈으로 돌아가면 battle을 null로 바꾼다.

### 10.7 v1 시연용 밸런스 결정

발표 자료의 수치는 조정 예정이므로 통합 테스트 기본값을 다음처럼 제안한다.

- 상성: attack이 skill에 승리, skill이 defend에 승리, defend가 attack에 승리.
- 승리한 선택이 attack이면 상대 20, defend이면 상대 15, skill이면 상대 30 데미지. 패한 쪽은 데미지를 주지 않는다.
- 같은 선택이면 양쪽 5 데미지.
- 기본 max_hp는 100, 최대 10턴. hp는 0 미만으로 내려가지 않는다.
- 한 명만 hp 0이면 상대 승리. 둘 다 0이면 무승부. 10턴 후 양쪽 생존이면 남은 hp가 높은 쪽 승리, 같으면 무승부.
- skill을 사용하면 승패와 무관하게 다음 1턴 사용 불가, 그다음 턴 사용 가능.
- 초기 통합 버전에서는 육성 보너스·보상은 0으로 둔다. 도입 시 계산식을 별도 설정으로 합의하며 확정 max_hp와 결과를 호스트가 전송한다.
- 발표 자료의 ‘동시 선택’과 미니게임 ‘선공’의 효과는 충돌 여지가 있으므로, 기본 배틀에서는 선공 효과를 적용하지 않는다. 필요 시 게임 규칙을 먼저 확정한다.

### 10.8 선택적 미니게임

초기 버전에서는 생략할 수 있다. 도입 시 아래 형식을 사용한다.

mini_game 시작 payload:

```json
{
  "battle_id": "battle001",
  "mini_game_id": "mini001",
  "phase": "start",
  "sequence": ["A", "C", "B", "A"],
  "timeout_seconds": 10
}
```

mini_game_input payload:

```json
{
  "battle_id": "battle001",
  "mini_game_id": "mini001",
  "player_id": "pet02",
  "input_index": 0,
  "button": "A"
}
```

mini_game 결과 payload:

```json
{
  "battle_id": "battle001",
  "mini_game_id": "mini001",
  "phase": "result",
  "winner_player_id": "pet02",
  "reason": "completed"
}
```

위 각 예시의 필드는 해당 phase에서 모두 필수다. sequence는 A/B/C 네 개이며 input_index는 0부터 시작한다. 호스트는 참가자별 다음 index만 수락한다. 잘못된 버튼은 진행을 증가시키지 않고 같은 index를 다시 입력하게 한다. 먼저 네 입력을 완료한 쪽이 승리하며, timeout까지 아무도 완료하지 못하면 winner_player_id=null, reason=`timeout`이다. reason은 `completed` 또는 `timeout`이다.

v1은 호스트 수신 순서로 판정하므로 네트워크 지연에 따른 공정성을 보장하지 않는다. 미니게임은 표시용 승패만 정하고 배틀 보너스는 적용하지 않는다. 선공·스킬 보너스는 팀 규칙 확정 후 추가한다.

## 11. 권장 구현 순서

1. 현재 캐릭터 JSON을 pet 필드 구조에 맞추고 state 전송.
2. button_event → 엔진 큐 → 상태 변경 → state 연결.
3. led_command 및 hardware_status 연동.
4. ping/pong, 연결 LED, 재접속 후 state_request 구현.
5. 중복·잘못된 입력·배터리 미장착 처리 테스트.
6. 호스트 배틀과 필요 시 미니게임 추가.

## 12. 통합 테스트 체크리스트

- [ ] 버튼 한 번 누름이 press 한 번으로 전달된다.
- [ ] 같은 B 입력이 홈에서는 확인, 배틀에서는 방어로 동작한다.
- [ ] satiety가 높을수록 배부른 상태로 모든 화면·LED에서 일치한다.
- [ ] 모든 상태 수치가 0~100을 유지한다.
- [ ] 수면 해제 시 is_sleeping=false, sleep_end_time=null이다.
- [ ] 배터리 미장착·읽기 실패·오래된 측정은 null로 표시한다.
- [ ] 3초 무응답 시 양쪽에서 연결 이상을 감지한다.
- [ ] 연결이 끊겨도 파이의 연결 LED가 자체적으로 깜빡인다.
- [ ] 재접속 시 오래된 버튼을 재생하지 않고 최신 state를 받는다.
- [ ] 같은 message_id가 두 번 와도 상태는 한 번만 바뀐다.
- [ ] 잘못된 JSON·버전·type·버튼·범위에 error를 반환한다.
- [ ] GPIO 입력·tick·네트워크 경합에서 상태 갱신이 유실되지 않는다.
- [ ] 배틀 timeout은 자동 방어이고 과거 턴 입력은 거절된다.
- [ ] 선택 중 상대 move가 노출되지 않는다.
- [ ] 배틀 HP 0이 육성 캐릭터 사망으로 이어지지 않는다.
- [ ] 배틀 종료·재전송에도 보상을 중복 적용하지 않는다.

## 13. 변경 정책

- 같은 버전에서는 기존 필드의 의미·타입·필수 여부를 바꾸지 않는다.
- 선택 필드 추가는 v1 안에서 가능하지만 수신자는 미지 필드를 무시해야 한다.
- 기존 필드 제거·이름 변경·단위 변경·열거값 해석 변경은 protocol_version을 올린다.
- 밸런스 수치 변경은 통신 규격 변경과 구분하고 모든 호스트에 동일 설정을 배포한다.
