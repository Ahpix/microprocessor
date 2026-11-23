"""
백엔드 WebSocket 서버 메인 모듈 (server.py)
스마트폰 Unity 클라이언트와 WebSocket으로 연결하여
ping/pong 처리 및 전체 상태(state) 동기화, 버튼 입력을 처리합니다.
"""

import asyncio
import json
import time
import uuid
from typing import Set, Dict, Any, Optional

import websockets

from .config import SERVER_HOST, SERVER_PORT, PROTOCOL_VERSION, HEARTBEAT_TIMEOUT_SEC
from game_engine.core.engine import GameEngine
from game_engine.core.tamagotchi import Tamagotchi
from storage.save_manager import save_game, load_game


class TamagotchiServer:
    def __init__(self, engine: Optional[GameEngine] = None):
        # 1. 게임 엔진 초기화
        if engine is not None:
            self.engine = engine
        else:
            pet = load_game() or Tamagotchi(name="Tama", pet_id="pet01")
            self.engine = GameEngine(
                tamagotchi=pet,
                device_id="pi01",
                on_state_change=self._broadcast_state_sync
            )

        # 2. 연결된 클라이언트 소켓 집합
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.last_ping_time: float = time.time()
        self.running: bool = True

    def _broadcast_state_sync(self, state: Dict[str, Any]):
        """엔진 상태 변경 시 비동기 브로드캐스트 태스크 예약"""
        asyncio.create_task(self.broadcast_state())

    async def broadcast_state(self):
        """모든 접속 클라이언트에 state 메시지 전송"""
        if not self.clients:
            return

        state = self.engine.get_state()
        message = {
            "protocol_version": PROTOCOL_VERSION,
            "type": "state",
            "message_id": f"server-state-{uuid.uuid4().hex[:8]}",
            "device_id": self.engine.device_id,
            "timestamp": time.time(),
            "payload": state
        }
        raw_msg = json.dumps(message)
        await asyncio.gather(
            *[client.send(raw_msg) for client in self.clients],
            return_exceptions=True
        )

    async def handle_message(self, websocket: websockets.WebSocketServerProtocol, message_str: str):
        """수신된 JSON 메시지 파싱 및 처리"""
        try:
            data = json.loads(message_str)
        except Exception:
            err = {"protocol_version": PROTOCOL_VERSION, "type": "error", "payload": {"code": "INVALID_JSON"}}
            await websocket.send(json.dumps(err))
            return

        msg_type = data.get("type")
        msg_id = data.get("message_id", f"msg-{uuid.uuid4().hex[:6]}")
        payload = data.get("payload", {})

        # 1. Ping / Pong
        if msg_type == "ping":
            self.last_ping_time = time.time()
            self.engine.set_connection_status(True)
            pong_msg = {
                "protocol_version": PROTOCOL_VERSION,
                "type": "pong",
                "message_id": f"server-pong-{uuid.uuid4().hex[:6]}",
                "device_id": self.engine.device_id,
                "timestamp": time.time(),
                "payload": {"reply_to": msg_id, "battery": {"available": False, "percentage": None}}
            }
            await websocket.send(json.dumps(pong_msg))

        # 2. 전체 상태 요청 (state_request)
        elif msg_type == "state_request":
            state_msg = {
                "protocol_version": PROTOCOL_VERSION,
                "type": "state",
                "message_id": f"server-state-{uuid.uuid4().hex[:8]}",
                "device_id": self.engine.device_id,
                "timestamp": time.time(),
                "payload": self.engine.get_state()
            }
            await websocket.send(json.dumps(state_msg))

        # 3. 버튼 입력 (button_event)
        elif msg_type == "button_event":
            btn = payload.get("button")
            evt = payload.get("event", "press")
            res = self.engine.handle_button_event(button=btn, event=evt, message_id=msg_id)
            ack_msg = {
                "protocol_version": PROTOCOL_VERSION,
                "type": "ack" if res.get("status") == "accepted" else "error",
                "message_id": f"server-ack-{uuid.uuid4().hex[:6]}",
                "device_id": self.engine.device_id,
                "timestamp": time.time(),
                "payload": res
            }
            await websocket.send(json.dumps(ack_msg))

    async def client_handler(self, websocket: websockets.WebSocketServerProtocol):
        """클라이언트 개별 연결 생명주기 관리"""
        self.clients.add(websocket)
        print(f"[접속] 새로운 클라이언트 연결됨: {websocket.remote_address}")
        self.engine.set_connection_status(True)

        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            print(f"[해제] 클라이언트 연결 종료: {websocket.remote_address}")
            if not self.clients:
                self.engine.set_connection_status(False)

    async def heartbeat_watcher(self):
        """1초 주기로 ping 수신 여부를 검사하여 연결 끊김 감지"""
        while self.running:
            await asyncio.sleep(1.0)
            if self.clients and (time.time() - self.last_ping_time > HEARTBEAT_TIMEOUT_SEC):
                # 3초 이상 무응답 시 연결 끊김 처리
                self.engine.set_connection_status(False)

    async def tick_loop(self):
        """엔진 시간 경과 주기적 업데이트 및 자동 저장"""
        save_counter = 0
        while self.running:
            await asyncio.sleep(1.0)
            self.engine.update_tick()

            save_counter += 1
            if save_counter >= 15:
                save_counter = 0
                save_game(self.engine.tamagotchi)

    async def start(self):
        """서버 시작"""
        print("=" * 60)
        print(f" 🚀 다마고치 WebSocket 서버 실행 중...")
        print(f"  - 주소 : ws://{SERVER_HOST}:{SERVER_PORT}")
        print("=" * 60)

        server = await websockets.serve(self.client_handler, SERVER_HOST, SERVER_PORT)
        watcher_task = asyncio.create_task(self.heartbeat_watcher())
        tick_task = asyncio.create_task(self.tick_loop())

        try:
            await asyncio.Future()  # 무한 대기
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False
            server.close()
            await server.wait_closed()
            save_game(self.engine.tamagotchi)
            print("[INFO] 서버가 안전하게 종료되었습니다.")


def main():
    server = TamagotchiServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n[INFO] 사용자에 의해 서버를 종료합니다.")


if __name__ == "__main__":
    main()
