"""
가상 Unity 클라이언트 테스트 스크립트 (mock_client.py)
실제 스마트폰 Unity 앱이 없어도 라즈베리파이 백엔드 WebSocket 서버와 연결하여
ping 전송, state 수신, 가상 버튼 입력 전송을 테스트할 수 있는 검증 도구입니다.

실행 방법:
  python3 -m backend.tests.mock_client
  또는
  python3 -m backend.tests.mock_client ws://<라즈베리파이IP>:8765
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
        except Exception:
            break


async def listen_loop(websocket):
    """서버로부터 오는 메시지 수신 및 화면 출력"""
    while True:
        try:
            message = await websocket.recv()
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "pong":
                # Heartbeat 응답 (조용히 무시 또는 점 출력)
                pass
            elif msg_type == "state":
                pet = data.get("payload", {}).get("pet", {})
                ui = data.get("payload", {}).get("ui", {})
                print(f"\n📩 [서버 브로드캐스트: STATE 수신]")
                print(f"   ❤️ 다마고치 '{pet.get('name')}' 상태:")
                print(f"     - 포만감: {pet.get('satiety'):>3}% | 행복도: {pet.get('happiness'):>3}% | 에너지: {pet.get('energy'):>3}%")
                print(f"     - 현재 모드: [{ui.get('mode')}] | 선택 메뉴: [{ui.get('selected_menu')}]")
                print(f"👉 조작 키 입력 (a: 메뉴이동 / b: 선택 / c: 취소) > ", end="", flush=True)
            elif msg_type == "ack":
                print(f"\n✅ [서버 ACK] 요청 처리 완료: {data.get('payload')}")
                print(f"👉 조작 키 입력 (a: 메뉴이동 / b: 선택 / c: 취소) > ", end="", flush=True)
            elif msg_type == "error":
                print(f"\n❌ [서버 ERROR] 오류 응답: {data.get('payload')}")
                print(f"👉 조작 키 입력 (a: 메뉴이동 / b: 선택 / c: 취소) > ", end="", flush=True)
            else:
                print(f"\n📩 [수신: {msg_type}] {data.get('payload')}")
                print(f"👉 조작 키 입력 (a: 메뉴이동 / b: 선택 / c: 취소) > ", end="", flush=True)

        except asyncio.CancelledError:
            break
        except websockets.exceptions.ConnectionClosed:
            print("\n[알림] 서버와의 연결이 종료되었습니다.")
            break


async def interactive_input_loop(websocket):
    """사용자가 터미널에서 a, b, c 키를 누르고 엔터를 치면 가상 스마트폰 버튼 이벤트를 서버로 전송"""
    loop = asyncio.get_running_loop()
    print("\n" + "=" * 60)
    print(" 📱 가상 스마트폰 조작 인터페이스 활성화")
    print("   [a + Enter] : 버튼 A (메뉴 이동)")
    print("   [b + Enter] : 버튼 B (선택 / 실행)")
    print("   [c + Enter] : 버튼 C (취소 / 초기화)")
    print("   [q + Enter] : 클라이언트 종료")
    print("=" * 60 + "\n")

    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            cmd = line.strip().lower()

            if cmd == "q":
                print("[종료] 클라이언트를 종료합니다.")
                await websocket.close()
                break

            button_map = {"a": "A", "b": "B", "c": "C"}
            if cmd in button_map:
                target_btn = button_map[cmd]
                btn_msg = {
                    "protocol_version": 1,
                    "type": "button_event",
                    "message_id": f"phone-btn-{uuid.uuid4().hex[:6]}",
                    "device_id": "phone01",
                    "timestamp": time.time(),
                    "payload": {
                        "button": target_btn,
                        "event": "press"
                    }
                }
                await websocket.send(json.dumps(btn_msg))
                print(f"📤 [스마트폰 화면 버튼 누름 전송] >> Button {target_btn}")
            else:
                print("알 수 없는 명령어입니다. (a, b, c 중 하나를 입력하세요)")

        except asyncio.CancelledError:
            break
        except Exception:
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

            # 2. 백그라운드 태스크 시작 (수신, 하트비트, 사용자 입력)
            listener_task = asyncio.create_task(listen_loop(websocket))
            heartbeat_task = asyncio.create_task(heartbeat_loop(websocket))
            input_task = asyncio.create_task(interactive_input_loop(websocket))

            done, pending = await asyncio.wait(
                [listener_task, heartbeat_task, input_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for t in pending:
                t.cancel()

    except ConnectionRefusedError:
        print(f"[오류] 서버({uri})에 연결할 수 없습니다. 백엔드 서버가 켜져 있는지 확인하세요.")
    except Exception as e:
        print(f"[오류 발생] {e}")


if __name__ == "__main__":
    target_uri = sys.argv[1] if len(sys.argv) > 1 else SERVER_URI
    try:
        asyncio.run(run_client(target_uri))
    except KeyboardInterrupt:
        print("\n[종료] 가상 클라이언트를 종료합니다.")
