# 🌐 백엔드 WebSocket 서버 개발 가이드 및 아키텍처 명세서

**담당자**: 백엔드 파트 (송승현 / 김경호 / 유건 협의)  
**플랫폼**: 라즈베리파이 (Python 3.10+ / `websockets`, `asyncio`)  
**역할**: Unity 스마트폰 앱 및 상대 라즈베리파이와 실시간 양방향 통신을 처리하는 WebSocket 서버 구축

---

## 1. 개요 및 설계 원칙

본 백엔드 모듈은 라즈베리파이에서 실행되며, **스마트폰(Unity 클라이언트)** 및 **상대 라즈베리파이(1:1 배틀)**와의 실시간 JSON 패킷 중계를 담당합니다.

> **핵심 설계 원칙 (Separation of Concerns)**
> - **게임 로직 비개입**: 캐릭터 수치 계산, 먹이주기 효과, 배틀 데미지 판정 등은 모두 `game_engine`에 위임하며, 백엔드는 메시지 수신·검증·전달·세션 관리만 전담합니다.
> - **프로토콜 표준 준수**: 모든 메시지는 `docs/protocol.md`의 v1 규격을 100% 엄격하게 준수합니다. (UTF-8, 단일 JSON 객체 per 텍스트 프레임, Unix 초 단위 타임스탬프)
> - **비동기 I/O 기반 고성능 처리**: `asyncio`와 `websockets` 라이브러리를 사용하여 단일 프로세스/스레드 내에서 다중 클라이언트 접속을 지연 없이 처리합니다.

---

## 2. 시스템 아키텍처 및 메시지 흐름도

```text
 ┌──────────────────────┐         WebSocket (JSON)         ┌─────────────────────────┐
 │   Unity 스마트폰 앱   │ <=============================> │   backend (WebSocket)   │
 │   (Frontend Client)  │   ping / state_request / 버튼   │   - 세션 관리 & 라우팅  │
 └──────────────────────┘                                  └───────────┬─────────────┘
                                                                       │
                         ┌─────────────────────────────────────────────┼─────────────────────────────┐
                         │                                             │                             │
                         ▼                                             ▼                             ▼
              ┌─────────────────────┐                       ┌─────────────────────┐       ┌──────────────────────┐
              │    game_engine      │                       │     hardware        │       │  상대 라즈베리파이   │
              │  (상태 계산 및 규칙) │                       │ (버튼 입력 & LED출력) │       │   (1:1 배틀 Peer)    │
              └─────────────────────┘                       └─────────────────────┘       └──────────────────────┘
```

---

## 3. 핵심 구현 기능 목록

### 3.1 연결 및 세션 관리 (`connection_manager.py`)
- **접속 주소**: `ws://<라즈베리파이_IP>:8765` (호스트 바인딩: `0.0.0.0`)
- **주 클라이언트 식별**: 접속한 소켓 중 스마트폰 Unity 앱을 주 클라이언트로 등록.
- **브로드캐스트 (Broadcast)**: 게임 엔진의 상태가 변경(`state`)되면 접속된 모든 대상에게 최신 상태 전송.

### 3.2 메시지 라우터 (`router.py`)
수신한 JSON 메시지의 `type`에 따라 적절한 처리기로 분기합니다:

| 수신 메시지 `type` | 발신처 | 백엔드 처리 동작 |
|:---|:---:|:---|
| **`ping`** | Unity | 즉시 **`pong`** 응답 (배터리 정보 포함) 및 Heartbeat 타임스탬프 갱신 |
| **`state_request`** | Unity | `game_engine.get_state()`를 조회하여 최신 **`state`** 메시지로 즉시 응답 |
| **`button_event`** | Unity / HW | `game_engine.handle_button_event()`를 호출하여 게임 상태 갱신 트리거 |
| **`battle_invite`** | 상대 파이 | 배틀 신청 수신 ➔ 호스트 엔진에 전달 및 `accept` 발급 |
| **`choose`** | 상대 파이 | 턴 선택 커맨드 수신 ➔ 호스트 배틀 매니저에 전달 |

### 3.3 Heartbeat 감시 & 연결 LED 동기화 (`heartbeat_monitor.py`)
- Unity 클라이언트는 1초마다 `ping`을 전송합니다.
- 마지막 `ping` 수신 후 **3.0초 이상** 경과하면 연결 끊김(Disconnected)으로 판정합니다.
- 연결 끊김 감지 시:
  ```python
  game_engine.set_connection_status(False)
  ```
  ➔ 게임 엔진이 `led_command`를 발생시켜 **하드웨어의 서버연결 LED가 자동으로 깜빡임(Blink)**으로 전환됩니다.

---

## 4. 백엔드 디렉터리 구조

```text
backend/
├── README.md               # [본 문서] 백엔드 WebSocket 서버 아키텍처 및 가이드
├── requirements.txt        # 백엔드 의존성 (websockets>=12.0)
├── src/
│   ├── __init__.py
│   ├── config.py           # 서버 포트(8765), 바인딩 호스트, 타임아웃 상수 설정
│   ├── server.py           # WebSocket 서버 메인 루프 (연결 수락 및 생명주기)
│   ├── router.py           # 수신 메시지 타입(type)별 디스패처
│   ├── connection_manager.py # 클라이언트 세션 등록, 해제, 브로드캐스트 관리
│   └── heartbeat.py        # 1초 주기 ping 감시 및 연결 상태 판정
└── tests/
    ├── __init__.py
    └── mock_client.py      # Unity 앱 없이 백엔드 단독 테스트용 가상 클라이언트
```

---

## 5. 단계별 구축 가이드 (Roadmap)

### 📌 1단계: 최소 WebSocket 서버 구축 (Hello World & Ping/Pong)
- [ ] `websockets` 라이브러리를 이용해 `ws://0.0.0.0:8765` 서버 오픈
- [ ] 클라이언트가 접속하면 환영 로그 출력
- [ ] `{"type": "ping"}` 수신 시 프로토콜에 맞춘 `{"type": "pong"}` 즉시 반환 확인

### 📌 2단계: 게임 엔진 연동 및 `state_request` / `state` 처리
- [ ] `GameEngine` 인스턴스를 주입받아 초기화
- [ ] 클라이언트 접속 직후 `state_request` 수신 시 `engine.get_state()` 반환
- [ ] `engine.on_state_change` 콜백 등록 ➔ 캐릭터 상태 변경 시 모든 클라이언트에 `state` 자동 브로드캐스트

### 📌 3단계: `button_event` 입력 파이프라인 연결
- [ ] Unity 화면의 가상 버튼 또는 하드웨어 버튼 이벤트 수신 시 `engine.handle_button_event()` 호출
- [ ] 처리 성공 시 `ack` 반환, 중복/에러 시 `error` 반환

### 📌 4단계: Heartbeat 감시 루프 및 하드웨어 LED 연동
- [ ] 백그라운드 태스크로 1초마다 마지막 ping 시간 검사
- [ ] 3초 타임아웃 발생 시 `engine.set_connection_status(False)` 호출
- [ ] 재접속 시 `engine.set_connection_status(True)` 호출 및 전체 `state` 재전송

### 📌 5단계: 배틀 P2P 메시지 중계 (확장)
- [ ] 2번째 클라이언트(상대 라즈베리파이) 접속 지원
- [ ] `battle_invite` ➔ `accept` ➔ `choose` ➔ `result` ➔ `battle_end` 중계 흐름 구현

---

## 6. 가상 클라이언트(`mock_client.py`)를 통한 단독 테스트 방법

Unity 스마트폰 앱이 아직 완성되지 않았더라도, 아래 테스트 클라이언트를 실행하여 서버의 정상 동작을 즉시 검증할 수 있습니다:

```bash
# 1. 백엔드 서버 실행 (터미널 1)
python3 -m backend.src.server

# 2. 가상 스마트폰 클라이언트 실행 (터미널 2)
python3 -m backend.tests.mock_client
```
