"""
백엔드 WebSocket 서버 설정 모듈 (config.py)
"""

# 서버 네트워크 설정
SERVER_HOST = "0.0.0.0"       # 모든 네트워크 인터페이스에서 수신 대기
SERVER_PORT = 8765            # WebSocket 기본 통신 포트

# 프로토콜 및 타임아웃 설정
PROTOCOL_VERSION = 1
HEARTBEAT_INTERVAL_SEC = 1.0  # Unity ping 권장 주기
HEARTBEAT_TIMEOUT_SEC = 3.0   # Heartbeat 타임아웃 판정 기준 (3초 무응답 시 연결 끊김)
MESSAGE_CACHE_TTL_SEC = 60.0  # 중복 요청 message_id 캐시 유지 시간
