#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - WebSocket 실시간 통신 서버
Flask-SocketIO 기반 실시간 양방향 통신
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    from flask import Flask
    from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
    import eventlet
    eventlet.monkey_patch()
    SOCKETIO_AVAILABLE = True
    safe_print("✅ Flask-SocketIO 라이브러리 사용 가능")
except ImportError:
    SOCKETIO_AVAILABLE = False
    safe_print("⚠️ Flask-SocketIO 미설치. pip install flask-socketio eventlet 실행 필요")


@dataclass
class ClientConnection:
    """클라이언트 연결 정보"""
    session_id: str
    user_id: Optional[str]
    rooms: Set[str]
    connected_at: datetime
    last_activity: datetime
    metadata: Dict[str, Any]


@dataclass 
class RoomInfo:
    """룸 정보"""
    room_id: str
    room_type: str  # public, private, game_specific
    members: Set[str]
    created_at: datetime
    metadata: Dict[str, Any]


class WebSocketServer:
    """WebSocket 실시간 통신 서버"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5001,
                 cors_allowed_origins: str = "*"):
        self.host = host
        self.port = port
        self.cors_allowed_origins = cors_allowed_origins
        
        # Flask 앱 및 SocketIO
        self.app = None
        self.socketio = None
        
        # 연결 관리
        self.clients: Dict[str, ClientConnection] = {}
        self.rooms: Dict[str, RoomInfo] = {}
        self.user_sessions: Dict[str, Set[str]] = defaultdict(set)  # user_id -> session_ids
        
        # 메시지 통계
        self.messages_sent = 0
        self.messages_received = 0
        self.connections_total = 0
        
        # 메시지 브로커 연결
        self._message_broker = None
        
        if SOCKETIO_AVAILABLE:
            self.initialize_app()
        
        safe_print("🔌 WebSocket 서버 초기화 완료")
    
    def initialize_app(self):
        """Flask 앱 및 SocketIO 초기화"""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'two-very-auto-websocket-secret'
        
        # SocketIO 설정
        self.socketio = SocketIO(
            self.app,
            cors_allowed_origins=self.cors_allowed_origins,
            async_mode='eventlet',
            logger=False,
            engineio_logger=False,
            ping_timeout=60,
            ping_interval=25
        )
        
        # 이벤트 핸들러 등록
        self.register_event_handlers()
        
        # 룸 생성
        self.create_default_rooms()
    
    def create_default_rooms(self):
        """기본 룸 생성"""
        default_rooms = [
            ("baccarat_live", "public", "바카라 실시간 게임"),
            ("ai_predictions", "public", "AI 예측 결과"),
            ("system_alerts", "public", "시스템 알림"),
            ("admin_room", "private", "관리자 전용")
        ]
        
        for room_id, room_type, description in default_rooms:
            self.rooms[room_id] = RoomInfo(
                room_id=room_id,
                room_type=room_type,
                members=set(),
                created_at=datetime.now(),
                metadata={"description": description}
            )
    
    def register_event_handlers(self):
        """SocketIO 이벤트 핸들러 등록"""
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            """클라이언트 연결"""
            session_id = self.socketio.request.sid
            user_id = auth.get('user_id') if auth else None
            
            # 연결 정보 저장
            client = ClientConnection(
                session_id=session_id,
                user_id=user_id,
                rooms=set(),
                connected_at=datetime.now(),
                last_activity=datetime.now(),
                metadata=auth or {}
            )
            
            self.clients[session_id] = client
            
            if user_id:
                self.user_sessions[user_id].add(session_id)
            
            self.connections_total += 1
            
            # 클라이언트에 연결 확인 전송
            emit('connected', {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'server_info': {
                    'version': '3.0',
                    'features': ['real_time_baccarat', 'ai_predictions', 'alerts']
                }
            })
            
            safe_print(f"🔌 클라이언트 연결: {session_id} (user: {user_id})")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """클라이언트 연결 해제"""
            session_id = self.socketio.request.sid
            
            if session_id in self.clients:
                client = self.clients[session_id]
                
                # 룸에서 제거
                for room_id in client.rooms.copy():
                    self.leave_room_internal(session_id, room_id)
                
                # 사용자 세션에서 제거
                if client.user_id:
                    self.user_sessions[client.user_id].discard(session_id)
                    if not self.user_sessions[client.user_id]:
                        del self.user_sessions[client.user_id]
                
                # 클라이언트 제거
                del self.clients[session_id]
                
                safe_print(f"🔌 클라이언트 연결 해제: {session_id}")
        
        @self.socketio.on('join_room')
        def handle_join_room(data):
            """룸 참가"""
            session_id = self.socketio.request.sid
            room_id = data.get('room_id')
            
            if room_id and self.join_room_internal(session_id, room_id):
                emit('room_joined', {
                    'room_id': room_id,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                emit('error', {'message': f'룸 참가 실패: {room_id}'})
        
        @self.socketio.on('leave_room')
        def handle_leave_room(data):
            """룸 퇴장"""
            session_id = self.socketio.request.sid
            room_id = data.get('room_id')
            
            if room_id and self.leave_room_internal(session_id, room_id):
                emit('room_left', {
                    'room_id': room_id,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                emit('error', {'message': f'룸 퇴장 실패: {room_id}'})
        
        @self.socketio.on('send_message')
        def handle_send_message(data):
            """메시지 전송"""
            session_id = self.socketio.request.sid
            room_id = data.get('room_id')
            message = data.get('message')
            message_type = data.get('type', 'chat')
            
            if not room_id or not message:
                emit('error', {'message': '룸 ID 또는 메시지가 필요합니다'})
                return
            
            # 클라이언트가 해당 룸에 있는지 확인
            if session_id not in self.clients or room_id not in self.clients[session_id].rooms:
                emit('error', {'message': '해당 룸에 참가하지 않았습니다'})
                return
            
            # 메시지 브로드캐스트
            self.broadcast_to_room(room_id, 'message', {
                'room_id': room_id,
                'message': message,
                'type': message_type,
                'sender': session_id,
                'user_id': self.clients[session_id].user_id,
                'timestamp': datetime.now().isoformat()
            })
            
            self.messages_received += 1
        
        @self.socketio.on('get_room_list')
        def handle_get_room_list():
            """룸 목록 조회"""
            room_list = []
            for room_id, room_info in self.rooms.items():
                if room_info.room_type == 'public':
                    room_list.append({
                        'room_id': room_id,
                        'type': room_info.room_type,
                        'members_count': len(room_info.members),
                        'description': room_info.metadata.get('description', ''),
                        'created_at': room_info.created_at.isoformat()
                    })
            
            emit('room_list', {'rooms': room_list})
        
        @self.socketio.on('ping')
        def handle_ping():
            """핑 응답"""
            session_id = self.socketio.request.sid
            if session_id in self.clients:
                self.clients[session_id].last_activity = datetime.now()
            
            emit('pong', {'timestamp': datetime.now().isoformat()})
    
    def join_room_internal(self, session_id: str, room_id: str) -> bool:
        """내부 룸 참가 처리"""
        try:
            if session_id not in self.clients:
                return False
            
            if room_id not in self.rooms:
                return False
            
            # SocketIO 룸 참가
            join_room(room_id, sid=session_id)
            
            # 내부 상태 업데이트
            self.clients[session_id].rooms.add(room_id)
            self.rooms[room_id].members.add(session_id)
            
            # 룸에 참가 알림
            self.broadcast_to_room(room_id, 'user_joined', {
                'room_id': room_id,
                'session_id': session_id,
                'user_id': self.clients[session_id].user_id,
                'members_count': len(self.rooms[room_id].members),
                'timestamp': datetime.now().isoformat()
            }, exclude=session_id)
            
            safe_print(f"👥 룸 참가: {session_id} -> {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"룸 참가 실패: {e}")
            return False
    
    def leave_room_internal(self, session_id: str, room_id: str) -> bool:
        """내부 룸 퇴장 처리"""
        try:
            if session_id not in self.clients:
                return False
            
            if room_id not in self.rooms:
                return False
            
            # SocketIO 룸 퇴장
            leave_room(room_id, sid=session_id)
            
            # 내부 상태 업데이트
            self.clients[session_id].rooms.discard(room_id)
            self.rooms[room_id].members.discard(session_id)
            
            # 룸에 퇴장 알림
            self.broadcast_to_room(room_id, 'user_left', {
                'room_id': room_id,
                'session_id': session_id,
                'user_id': self.clients[session_id].user_id,
                'members_count': len(self.rooms[room_id].members),
                'timestamp': datetime.now().isoformat()
            })
            
            safe_print(f"👥 룸 퇴장: {session_id} <- {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"룸 퇴장 실패: {e}")
            return False
    
    def broadcast_to_room(self, room_id: str, event: str, data: Dict[str, Any],
                         exclude: Optional[str] = None):
        """룸에 메시지 브로드캐스트"""
        try:
            if room_id not in self.rooms:
                return
            
            self.socketio.emit(event, data, room=room_id, skip_sid=exclude)
            self.messages_sent += 1
            
        except Exception as e:
            logger.error(f"룸 브로드캐스트 실패: {e}")
    
    def broadcast_to_user(self, user_id: str, event: str, data: Dict[str, Any]):
        """특정 사용자의 모든 세션에 메시지 전송"""
        if user_id not in self.user_sessions:
            return
        
        for session_id in self.user_sessions[user_id]:
            try:
                self.socketio.emit(event, data, room=session_id)
                self.messages_sent += 1
            except Exception as e:
                logger.error(f"사용자 브로드캐스트 실패 ({user_id}): {e}")
    
    def broadcast_to_all(self, event: str, data: Dict[str, Any]):
        """모든 연결된 클라이언트에 브로드캐스트"""
        try:
            self.socketio.emit(event, data, broadcast=True)
            self.messages_sent += len(self.clients)
            
        except Exception as e:
            logger.error(f"전체 브로드캐스트 실패: {e}")
    
    def cleanup_inactive_clients(self, timeout_seconds: int = 300):
        """비활성 클라이언트 정리"""
        cutoff_time = datetime.now()
        inactive_clients = []
        
        for session_id, client in self.clients.items():
            inactive_duration = (cutoff_time - client.last_activity).total_seconds()
            if inactive_duration > timeout_seconds:
                inactive_clients.append(session_id)
        
        for session_id in inactive_clients:
            try:
                disconnect(sid=session_id)
                safe_print(f"🧹 비활성 클라이언트 정리: {session_id}")
            except Exception as e:
                logger.error(f"클라이언트 정리 실패: {e}")
        
        return len(inactive_clients)
    
    def get_server_stats(self) -> Dict[str, Any]:
        """서버 통계 정보"""
        return {
            "connected_clients": len(self.clients),
            "total_connections": self.connections_total,
            "active_rooms": len([r for r in self.rooms.values() if r.members]),
            "total_rooms": len(self.rooms),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "unique_users": len(self.user_sessions),
            "room_details": {
                room_id: {
                    "members_count": len(room.members),
                    "type": room.room_type,
                    "created_at": room.created_at.isoformat()
                }
                for room_id, room in self.rooms.items()
            }
        }
    
    @property
    def message_broker(self):
        """메시지 브로커 가져오기"""
        if self._message_broker is None:
            try:
                from message_broker import get_message_broker
                self._message_broker = get_message_broker()
            except ImportError:
                pass
        return self._message_broker
    
    def start_message_broker_integration(self):
        """메시지 브로커와 통합 시작"""
        if not self.message_broker:
            return
        
        # 메시지 핸들러 등록
        from message_broker import MessageType
        
        def handle_baccarat_update(message):
            self.broadcast_to_room("baccarat_live", "baccarat_update", message.payload)
        
        def handle_ai_prediction(message):
            self.broadcast_to_room("ai_predictions", "ai_prediction", message.payload)
        
        def handle_system_alert(message):
            self.broadcast_to_all("system_alert", message.payload)
        
        self.message_broker.register_handler(MessageType.BACCARAT_UPDATE, handle_baccarat_update)
        self.message_broker.register_handler(MessageType.AI_PREDICTION, handle_ai_prediction)
        self.message_broker.register_handler(MessageType.SYSTEM_ALERT, handle_system_alert)
        
        # 컨슈머 시작
        self.message_broker.start_consumer("websocket_stream", "websocket_group", "websocket_consumer")
        
        safe_print("🔗 메시지 브로커 통합 완료")
    
    def run(self, debug: bool = False):
        """WebSocket 서버 실행"""
        if not SOCKETIO_AVAILABLE:
            safe_print("❌ Flask-SocketIO 라이브러리가 필요합니다")
            return
        
        # 메시지 브로커 통합
        self.start_message_broker_integration()
        
        # 정리 작업 스케줄러
        def cleanup_scheduler():
            while True:
                time.sleep(300)  # 5분마다
                self.cleanup_inactive_clients()
        
        cleanup_thread = threading.Thread(target=cleanup_scheduler, daemon=True)
        cleanup_thread.start()
        
        safe_print(f"🚀 WebSocket 서버 시작: http://{self.host}:{self.port}")
        self.socketio.run(self.app, host=self.host, port=self.port, debug=debug)


# 전역 인스턴스
_websocket_server = None

def get_websocket_server(host: str = "0.0.0.0", port: int = 5001) -> WebSocketServer:
    """WebSocket 서버 인스턴스 반환"""
    global _websocket_server
    if _websocket_server is None:
        _websocket_server = WebSocketServer(host=host, port=port)
    return _websocket_server


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== WebSocket 서버 테스트 ===")
    
    server = get_websocket_server()
    
    if SOCKETIO_AVAILABLE:
        # 상태 정보 출력
        stats = server.get_server_stats()
        safe_print(f"📊 서버 상태: {stats}")
        
        # 서버 시작 (개발 모드)
        if input("WebSocket 서버를 시작하시겠습니까? (y/N): ").lower() == 'y':
            server.run(debug=True)
    
    else:
        safe_print("❌ Flask-SocketIO 라이브러리 설치 필요: pip install flask-socketio eventlet")
    
    safe_print("🏁 WebSocket 서버 테스트 완료")