#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 스트리밍 클라이언트
실시간 데이터 스트리밍 클라이언트 라이브러리
"""

import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import threading
from collections import deque
import uuid

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    import socketio
    import requests
    CLIENT_LIBS_AVAILABLE = True
    safe_print("✅ 클라이언트 라이브러리 사용 가능")
except ImportError:
    CLIENT_LIBS_AVAILABLE = False
    safe_print("⚠️ python-socketio, requests 라이브러리 미설치")


class ConnectionState(Enum):
    """연결 상태"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class ClientConfig:
    """클라이언트 설정"""
    server_url: str = "http://localhost:5001"
    user_id: Optional[str] = None
    auto_reconnect: bool = True
    reconnect_delay: int = 5
    max_reconnect_attempts: int = 10
    heartbeat_interval: int = 30
    message_queue_size: int = 1000
    timeout: int = 30


@dataclass
class StreamMessage:
    """스트림 메시지"""
    message_id: str
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    source: str = "server"


class StreamingClient:
    """실시간 스트리밍 클라이언트"""
    
    def __init__(self, config: ClientConfig):
        self.config = config
        self.client_id = str(uuid.uuid4())
        
        # 연결 관리
        self.connection_state = ConnectionState.DISCONNECTED
        self.socket_client = None
        self.reconnect_attempts = 0
        
        # 메시지 처리
        self.message_queue = deque(maxlen=config.message_queue_size)
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.message_history = deque(maxlen=1000)
        
        # 통계
        self.messages_received = 0
        self.messages_sent = 0
        self.connection_start_time = None
        self.last_heartbeat = None
        
        # 백그라운드 작업
        self.heartbeat_thread = None
        self.processing_thread = None
        self.running = False
        
        if CLIENT_LIBS_AVAILABLE:
            self.initialize_socket()
        
        safe_print(f"📡 스트리밍 클라이언트 초기화: {self.client_id}")
    
    def initialize_socket(self):
        """SocketIO 클라이언트 초기화"""
        try:
            self.socket_client = socketio.Client(
                reconnection=self.config.auto_reconnect,
                reconnection_delay=self.config.reconnect_delay,
                reconnection_attempts=self.config.max_reconnect_attempts,
                logger=False,
                engineio_logger=False
            )
            
            # 이벤트 핸들러 등록
            self.register_socket_handlers()
            
        except Exception as e:
            logger.error(f"SocketIO 클라이언트 초기화 실패: {e}")
    
    def register_socket_handlers(self):
        """Socket.IO 이벤트 핸들러 등록"""
        
        @self.socket_client.event
        def connect():
            """연결 성공"""
            self.connection_state = ConnectionState.CONNECTED
            self.connection_start_time = datetime.now()
            self.reconnect_attempts = 0
            
            # 인증 정보 전송
            if self.config.user_id:
                self.socket_client.emit('auth', {'user_id': self.config.user_id})
            
            safe_print(f"🔌 서버 연결 완료: {self.config.server_url}")
            
            # 연결 이벤트 핸들러 호출
            self._call_event_handlers('connect', {"timestamp": datetime.now().isoformat()})
        
        @self.socket_client.event
        def disconnect():
            """연결 해제"""
            self.connection_state = ConnectionState.DISCONNECTED
            safe_print("🔌 서버 연결 해제")
            
            # 연결 해제 이벤트 핸들러 호출
            self._call_event_handlers('disconnect', {"timestamp": datetime.now().isoformat()})
        
        @self.socket_client.event
        def connect_error(data):
            """연결 오류"""
            self.connection_state = ConnectionState.ERROR
            logger.error(f"연결 오류: {data}")
            
            # 오류 이벤트 핸들러 호출
            self._call_event_handlers('connect_error', {"error": str(data), "timestamp": datetime.now().isoformat()})
        
        @self.socket_client.event
        def connected(data):
            """서버 연결 확인 응답"""
            safe_print(f"✅ 서버 연결 확인: {data.get('session_id')}")
            self._call_event_handlers('connected', data)
        
        @self.socket_client.event
        def message(data):
            """일반 메시지"""
            self._handle_incoming_message('message', data)
        
        @self.socket_client.event
        def notification(data):
            """알림 메시지"""
            self._handle_incoming_message('notification', data)
        
        @self.socket_client.event
        def baccarat_update(data):
            """바카라 게임 업데이트"""
            self._handle_incoming_message('baccarat_update', data)
        
        @self.socket_client.event
        def ai_prediction(data):
            """AI 예측 결과"""
            self._handle_incoming_message('ai_prediction', data)
        
        @self.socket_client.event
        def system_alert(data):
            """시스템 알림"""
            self._handle_incoming_message('system_alert', data)
        
        @self.socket_client.event
        def stream_event(data):
            """스트림 이벤트"""
            self._handle_incoming_message('stream_event', data)
        
        @self.socket_client.event
        def pong(data):
            """핑퐁 응답"""
            self.last_heartbeat = datetime.now()
    
    def _handle_incoming_message(self, event_type: str, data: Dict[str, Any]):
        """수신 메시지 처리"""
        try:
            message = StreamMessage(
                message_id=data.get('id', str(uuid.uuid4())),
                event_type=event_type,
                data=data,
                timestamp=datetime.now(),
                source="server"
            )
            
            # 메시지 큐에 추가
            self.message_queue.append(message)
            self.message_history.append(message)
            self.messages_received += 1
            
            # 이벤트 핸들러 호출
            self._call_event_handlers(event_type, data)
            
        except Exception as e:
            logger.error(f"메시지 처리 실패: {e}")
    
    def _call_event_handlers(self, event_type: str, data: Dict[str, Any]):
        """이벤트 핸들러 호출"""
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"이벤트 핸들러 오류 ({event_type}): {e}")
    
    def connect(self) -> bool:
        """서버 연결"""
        if not CLIENT_LIBS_AVAILABLE:
            safe_print("❌ 클라이언트 라이브러리 필요")
            return False
        
        if self.connection_state == ConnectionState.CONNECTED:
            safe_print("이미 연결됨")
            return True
        
        try:
            self.connection_state = ConnectionState.CONNECTING
            
            # 인증 정보 준비
            auth_data = {}
            if self.config.user_id:
                auth_data['user_id'] = self.config.user_id
            
            # 서버 연결
            self.socket_client.connect(
                self.config.server_url,
                auth=auth_data,
                wait_timeout=self.config.timeout
            )
            
            # 백그라운드 작업 시작
            self.start_background_tasks()
            
            return True
            
        except Exception as e:
            logger.error(f"연결 실패: {e}")
            self.connection_state = ConnectionState.ERROR
            return False
    
    def disconnect(self):
        """서버 연결 해제"""
        try:
            self.running = False
            
            if self.socket_client and self.socket_client.connected:
                self.socket_client.disconnect()
            
            # 백그라운드 작업 중지
            self.stop_background_tasks()
            
            safe_print("🔌 연결 해제 완료")
            
        except Exception as e:
            logger.error(f"연결 해제 실패: {e}")
    
    def join_room(self, room_id: str) -> bool:
        """룸 참가"""
        if not self.socket_client or not self.socket_client.connected:
            return False
        
        try:
            self.socket_client.emit('join_room', {'room_id': room_id})
            safe_print(f"🏠 룸 참가 요청: {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"룸 참가 실패: {e}")
            return False
    
    def leave_room(self, room_id: str) -> bool:
        """룸 퇴장"""
        if not self.socket_client or not self.socket_client.connected:
            return False
        
        try:
            self.socket_client.emit('leave_room', {'room_id': room_id})
            safe_print(f"🏠 룸 퇴장 요청: {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"룸 퇴장 실패: {e}")
            return False
    
    def send_message(self, room_id: str, message: str, message_type: str = "chat") -> bool:
        """메시지 전송"""
        if not self.socket_client or not self.socket_client.connected:
            return False
        
        try:
            self.socket_client.emit('send_message', {
                'room_id': room_id,
                'message': message,
                'type': message_type
            })
            
            self.messages_sent += 1
            return True
            
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")
            return False
    
    def get_room_list(self) -> bool:
        """룸 목록 요청"""
        if not self.socket_client or not self.socket_client.connected:
            return False
        
        try:
            self.socket_client.emit('get_room_list')
            return True
            
        except Exception as e:
            logger.error(f"룸 목록 요청 실패: {e}")
            return False
    
    def add_event_handler(self, event_type: str, handler: Callable):
        """이벤트 핸들러 추가"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        safe_print(f"🔧 이벤트 핸들러 등록: {event_type}")
    
    def remove_event_handler(self, event_type: str, handler: Callable):
        """이벤트 핸들러 제거"""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    def get_messages(self, limit: int = 100) -> List[StreamMessage]:
        """최근 메시지 조회"""
        messages = list(self.message_queue)
        return messages[-limit:] if len(messages) > limit else messages
    
    def get_message_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """메시지 히스토리 조회"""
        history = list(self.message_history)
        recent_history = history[-limit:] if len(history) > limit else history
        
        return [
            {
                "message_id": msg.message_id,
                "event_type": msg.event_type,
                "data": msg.data,
                "timestamp": msg.timestamp.isoformat(),
                "source": msg.source
            }
            for msg in recent_history
        ]
    
    def start_background_tasks(self):
        """백그라운드 작업 시작"""
        if self.running:
            return
        
        self.running = True
        
        # 하트비트 스레드
        def heartbeat_worker():
            while self.running:
                try:
                    if self.socket_client and self.socket_client.connected:
                        self.socket_client.emit('ping')
                    
                    time.sleep(self.config.heartbeat_interval)
                    
                except Exception as e:
                    logger.error(f"하트비트 오류: {e}")
                    time.sleep(5)
        
        self.heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        
        safe_print("💓 백그라운드 작업 시작")
    
    def stop_background_tasks(self):
        """백그라운드 작업 중지"""
        self.running = False
        
        # 스레드 종료 대기
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2)
        
        safe_print("💓 백그라운드 작업 중지")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """연결 상태 정보"""
        uptime = None
        if self.connection_start_time:
            uptime = (datetime.now() - self.connection_start_time).total_seconds()
        
        last_heartbeat_ago = None
        if self.last_heartbeat:
            last_heartbeat_ago = (datetime.now() - self.last_heartbeat).total_seconds()
        
        return {
            "client_id": self.client_id,
            "state": self.connection_state.value,
            "server_url": self.config.server_url,
            "user_id": self.config.user_id,
            "connected": self.connection_state == ConnectionState.CONNECTED,
            "uptime_seconds": uptime,
            "reconnect_attempts": self.reconnect_attempts,
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "message_queue_size": len(self.message_queue),
            "last_heartbeat_ago": last_heartbeat_ago
        }
    
    def wait_for_connection(self, timeout: int = 30) -> bool:
        """연결 완료 대기"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.connection_state == ConnectionState.CONNECTED:
                return True
            elif self.connection_state == ConnectionState.ERROR:
                return False
            
            time.sleep(0.1)
        
        return False


class StreamingClientManager:
    """스트리밍 클라이언트 관리자"""
    
    def __init__(self):
        self.clients: Dict[str, StreamingClient] = {}
        self.default_config = ClientConfig()
        
        safe_print("📊 스트리밍 클라이언트 관리자 초기화")
    
    def create_client(self, client_id: str, config: Optional[ClientConfig] = None) -> StreamingClient:
        """클라이언트 생성"""
        if client_id in self.clients:
            safe_print(f"클라이언트 이미 존재: {client_id}")
            return self.clients[client_id]
        
        client_config = config or self.default_config
        client = StreamingClient(client_config)
        self.clients[client_id] = client
        
        safe_print(f"📡 클라이언트 생성: {client_id}")
        return client
    
    def get_client(self, client_id: str) -> Optional[StreamingClient]:
        """클라이언트 조회"""
        return self.clients.get(client_id)
    
    def remove_client(self, client_id: str) -> bool:
        """클라이언트 제거"""
        if client_id in self.clients:
            client = self.clients[client_id]
            client.disconnect()
            del self.clients[client_id]
            safe_print(f"📡 클라이언트 제거: {client_id}")
            return True
        return False
    
    def get_all_clients_status(self) -> Dict[str, Dict[str, Any]]:
        """모든 클라이언트 상태"""
        return {
            client_id: client.get_connection_status()
            for client_id, client in self.clients.items()
        }
    
    def disconnect_all(self):
        """모든 클라이언트 연결 해제"""
        for client in self.clients.values():
            client.disconnect()
        
        safe_print("📡 모든 클라이언트 연결 해제")


# 전역 인스턴스
_client_manager = None

def get_client_manager() -> StreamingClientManager:
    """클라이언트 관리자 인스턴스 반환"""
    global _client_manager
    if _client_manager is None:
        _client_manager = StreamingClientManager()
    return _client_manager


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 스트리밍 클라이언트 테스트 ===")
    
    if not CLIENT_LIBS_AVAILABLE:
        safe_print("❌ 클라이언트 라이브러리 설치 필요: pip install python-socketio requests")
        exit(1)
    
    # 클라이언트 설정
    config = ClientConfig(
        server_url="http://localhost:5001",
        user_id="test_client_user",
        auto_reconnect=True
    )
    
    # 클라이언트 생성
    client = StreamingClient(config)
    
    # 이벤트 핸들러 등록
    def on_baccarat_update(data):
        safe_print(f"🎰 바카라 업데이트: {data}")
    
    def on_ai_prediction(data):
        safe_print(f"🤖 AI 예측: {data}")
    
    def on_notification(data):
        safe_print(f"🔔 알림: {data}")
    
    client.add_event_handler("baccarat_update", on_baccarat_update)
    client.add_event_handler("ai_prediction", on_ai_prediction)
    client.add_event_handler("notification", on_notification)
    
    # 서버 연결
    safe_print("서버 연결 중...")
    if client.connect():
        safe_print("✅ 연결 성공")
        
        # 연결 대기
        if client.wait_for_connection():
            # 룸 참가
            client.join_room("baccarat_live")
            client.join_room("ai_predictions")
            
            # 상태 정보 출력
            status = client.get_connection_status()
            safe_print(f"📊 클라이언트 상태: {status}")
            
            # 메시지 수신 대기
            try:
                safe_print("메시지 수신 대기 중... (Ctrl+C로 종료)")
                while True:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                safe_print("사용자 중단")
        
        # 연결 해제
        client.disconnect()
    
    else:
        safe_print("❌ 연결 실패")
    
    safe_print("🏁 스트리밍 클라이언트 테스트 완료")