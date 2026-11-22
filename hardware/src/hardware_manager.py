"""
하드웨어 통합 관리자 (Hardware Manager)
버튼 입력 수집과 LED 제어를 통합 관리하며, 프로토콜 메시지(button_event / led_command)를 처리합니다.
"""

import time
import uuid
from typing import Callable, Optional, Dict, Any
from .button_handler import ButtonHandler
from .led_controller import LEDController


class HardwareManager:
    def __init__(
        self,
        device_id: str = "pi01",
        on_send_event: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        :param device_id: 라즈베리파이 기기 ID
        :param on_send_event: 게임 엔진/백엔드로 button_event 메시지를 전송하는 콜백 함수
        """
        self.device_id = device_id
        self.on_send_event = on_send_event

        self.led_controller = LEDController()
        self.button_handler = ButtonHandler(on_button_press=self._handle_button_press)

    def _handle_button_press(self, button: str):
        """
        버튼 누름 감지 시 프로토콜에 맞춘 button_event 생성 및 전송
        """
        message = {
            "protocol_version": 1,
            "type": "button_event",
            "message_id": f"{self.device_id}-{uuid.uuid4().hex[:8]}",
            "device_id": self.device_id,
            "timestamp": time.time(),
            "payload": {
                "button": button,  # "A" | "B" | "C"
                "event": "press"
            }
        }

        if self.on_send_event:
            self.on_send_event(message)
        else:
            print(f"[HardwareManager] 생성된 이벤트 전송: {message}")

    def handle_led_command(self, message: Dict[str, Any]):
        """
        게임 엔진으로부터 수신한 led_command 메시지 처리
        """
        if message.get("type") != "led_command":
            return

        payload = message.get("payload", {})
        leds = payload.get("leds", {})
        self.led_controller.apply_led_command(leds)

    def set_connection_status(self, is_connected: bool):
        """
        네트워크 연결 상태 LED 간편 설정 (연결 정상: On, 이상: Blink)
        """
        mode = "on" if is_connected else "blink"
        self.led_controller.set_led("connection", mode=mode, period_ms=1000)

    def cleanup(self):
        """리소스 정리"""
        self.button_handler.cleanup()
        self.led_controller.cleanup()
