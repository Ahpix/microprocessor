"""
가상 Unity 클라이언트 테스트 스크립트 (mock_client.py)
실제 스마트폰 Unity 앱이 없어도 라즈베리파이 백엔드 WebSocket 서버와 연결하여
ping 전송, state 수신, 가상 버튼 입력 전송을 테스트할 수 있는 검증 도구입니다.

실행 방법:
  python3 -m backend.tests.mock_client
  또는
  python3 mock_client.py (ws://<서버IP>:8765 지정 가능)
"""

import asyncio
import json
import time
import sys
import uuid

try:
    import websockets
except ImportError:
    print("[오류] websockets 라이브러리가 필요합니다: pip install websockets")
    sys.exit(1)


SERVER_URI = "ws://localhost:8765"


async def heartbeat_loop(websocket):
    """1초마다 서버로 ping 전송"""
    while True:
        try:
            ping_msg = {
                "protocol_version": 1,
                "type": "ping",
                "message_id": f"phone-ping-{uuid.uuid4().hex[:6]}",
                "device_id": "phone01",
                "timestamp": time.time(),
                "payload": {}
            }
            await websocket.send(json.dumps(ping_msg))
            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[Heartbeat 오류] {e}")
            break


async def listen_loop(websocket):
    """서버로부터 오는 메시지 수신 및 화면 출력"""
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "pong":
                # print("  [수신] pong (Heartbeat 정상)")
                pass
            elif msg_type == "state":
                pet = data.get("payload", {}).get("pet", {})
                ui = data.get("payload", {}).get("ui", {})
                print(f"\n[수신: STATE] 다마고치 상태 갱신!")
                print(f"  - 포만감: {pet.get('satiety')} | 행복도: {pet.get('happiness')} | 에너지: {pet.get('energy')}")
                print(f"  - 모드: {ui.get('mode')} | 선택메뉴: {ui.get('selected_menu')}")
            else:
                print(f"\n[수신: {msg_type}] {data.get('payload')}")

        except asyncio.CancelledError:
            break
        except websockets.exceptions.ConnectionClosed:
            print("\n[알림] 서버와의 연결이 종료되었습니다.")
            break


async def run_client(uri: str = SERVER_URI):
    print(f"[{uri}] 백엔드 서버에 연결을 시도합니다...")
    try:
        async with websockets.connect(uri) as websocket:
            print("[성공] WebSocket 서버에 성공적으로 연결되었습니다!")

            # 1. 최초 접속 직후 전체 상태 요청 (state_request)
            req_msg = {
                "protocol_version": 1,
                "type": "state_request",
                "message_id": f"phone-req-{uuid.uuid4().hex[:6]}",
                "device_id": "phone01",
                "timestamp": time.time(),
                "payload": {}
            }
            await websocket.send(json.dumps(req_msg))
            print("[송신] 초기 상태 요청(state_request) 전송 완료")

            # 2. 백그라운드 리스너 및 하트비트 시작
            listener_task = asyncio.create_task(listen_loop(websocket))
            heartbeat_task = asyncio.create_task(heartbeat_loop(websocket))

            # 3. 콘솔 대기 루프
            await asyncio.gather(listener_task, heartbeat_task)

    except ConnectionRefusedError:
        print(f"[오류] 서버({uri})에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인하세요.")
    except Exception as e:
        print(f"[오류 발생] {e}")


if __name__ == "__main__":
    target_uri = sys.argv[1] if len(sys.argv) > 1 else SERVER_URI
    try:
        asyncio.run(run_client(target_uri))
    except KeyboardInterrupt:
        print("\n[종료] 가상 클라이언트를 종료합니다.")
