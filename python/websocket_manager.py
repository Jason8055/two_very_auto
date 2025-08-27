#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebSocket Manager v2.0
실시간 통신 및 알림 관리 시스템
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Callable
from flask_socketio import emit, disconnect
from collections import defaultdict, deque

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketManager:
    """실시간 WebSocket 통신 관리자"""
    
    def __init__(self, socketio_instance):
        """
        WebSocket 매니저 초기화
        
        Args:
            socketio_instance: Flask-SocketIO 인스턴스
        """
        self.socketio = socketio_instance
        
        # 연결된 클라이언트 관리
        self.connected_clients = set()
        self.client_info = {}  # 클라이언트별 상세 정보
        self.client_subscriptions = defaultdict(set)  # 구독 정보
        
        # 브로드캐스트 관리
        self.broadcast_queue = deque(maxlen=1000)
        self.broadcast_thread = None
        self.is_broadcasting = False
        
        # 실시간 데이터 캐시
        self.realtime_data = {
            'pairs': deque(maxlen=100),
            'stats': {},
            'alerts': deque(maxlen=50),
            'last_update': datetime.now()
        }
        
        # 성능 메트릭
        self.metrics = {
            'total_connections': 0,
            'current_connections': 0,
            'messages_sent': 0,
            'broadcast_queue_size': 0
        }
        
        # 이벤트 핸들러 등록
        self._register_handlers()
        
        logger.info("[WebSocket Manager] Initialized successfully")
    
    def _register_handlers(self) -> None:
        """SocketIO 이벤트 핸들러 등록"""
        
        @self.socketio.on('connect')
        def handle_connect(auth):
            """클라이언트 연결 처리"""
            client_id = self._get_client_id()
            
            self.connected_clients.add(client_id)
            self.client_info[client_id] = {
                'connected_at': datetime.now(),
                'ip_address': self._get_client_ip(),
                'user_agent': self._get_user_agent(),
                'subscriptions': set()
            }
            
            self.metrics['current_connections'] = len(self.connected_clients)
            self.metrics['total_connections'] += 1
            
            logger.info(f"Client connected: {client_id} (Total: {len(self.connected_clients)})")
            
            # 연결 확인 메시지 전송
            emit('connection_established', {
                'client_id': client_id,
                'server_time': datetime.now().isoformat(),
                'available_subscriptions': [
                    'pair_alerts',
                    'table_stats',
                    'system_status',
                    'performance_metrics'
                ]
            })
            
            # 초기 데이터 전송
            self._send_initial_data(client_id)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """클라이언트 연결 해제 처리"""
            client_id = self._get_client_id()
            
            if client_id in self.connected_clients:
                self.connected_clients.remove(client_id)
                
                # 구독 정보 정리
                for subscription in self.client_info.get(client_id, {}).get('subscriptions', set()):
                    self.client_subscriptions[subscription].discard(client_id)
                
                del self.client_info[client_id]
                
                self.metrics['current_connections'] = len(self.connected_clients)
                
                logger.info(f"Client disconnected: {client_id} (Remaining: {len(self.connected_clients)})")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """구독 요청 처리"""
            client_id = self._get_client_id()
            subscription_type = data.get('type')
            
            if client_id and subscription_type:
                self.client_subscriptions[subscription_type].add(client_id)
                self.client_info[client_id]['subscriptions'].add(subscription_type)
                
                emit('subscription_confirmed', {
                    'type': subscription_type,
                    'status': 'subscribed',
                    'timestamp': datetime.now().isoformat()
                })
                
                logger.debug(f"Client {client_id} subscribed to {subscription_type}")
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """구독 해제 처리"""
            client_id = self._get_client_id()
            subscription_type = data.get('type')
            
            if client_id and subscription_type:
                self.client_subscriptions[subscription_type].discard(client_id)
                self.client_info[client_id]['subscriptions'].discard(subscription_type)
                
                emit('subscription_confirmed', {
                    'type': subscription_type,
                    'status': 'unsubscribed',
                    'timestamp': datetime.now().isoformat()
                })
                
                logger.debug(f"Client {client_id} unsubscribed from {subscription_type}")
        
        @self.socketio.on('ping')
        def handle_ping(data):
            """핑 요청 처리 (연결 상태 확인)"""
            emit('pong', {
                'timestamp': datetime.now().isoformat(),
                'client_count': len(self.connected_clients)
            })
        
        @self.socketio.on('request_data')
        def handle_data_request(data):
            """데이터 요청 처리"""
            client_id = self._get_client_id()
            data_type = data.get('type')
            
            if data_type == 'recent_pairs':
                emit('data_response', {
                    'type': 'recent_pairs',
                    'data': list(self.realtime_data['pairs'])[-10:],
                    'timestamp': datetime.now().isoformat()
                })
            
            elif data_type == 'current_stats':
                emit('data_response', {
                    'type': 'current_stats',
                    'data': self.realtime_data['stats'],
                    'timestamp': datetime.now().isoformat()
                })
    
    def _get_client_id(self) -> str:
        """클라이언트 ID 생성"""
        from flask import request
        return f"{request.sid}"
    
    def _get_client_ip(self) -> str:
        """클라이언트 IP 주소 조회"""
        from flask import request
        return request.environ.get('REMOTE_ADDR', 'unknown')
    
    def _get_user_agent(self) -> str:
        """사용자 에이전트 조회"""
        from flask import request
        return request.environ.get('HTTP_USER_AGENT', 'unknown')
    
    def _send_initial_data(self, client_id: str) -> None:
        """새 클라이언트에게 초기 데이터 전송"""
        try:
            # 최근 페어 정보
            if self.realtime_data['pairs']:
                self.socketio.emit('recent_pairs_update', {
                    'pairs': list(self.realtime_data['pairs'])[-5:],
                    'timestamp': datetime.now().isoformat()
                }, room=client_id)
            
            # 현재 통계
            if self.realtime_data['stats']:
                self.socketio.emit('stats_update', {
                    'stats': self.realtime_data['stats'],
                    'timestamp': datetime.now().isoformat()
                }, room=client_id)
                
        except Exception as e:
            logger.error(f"Failed to send initial data to {client_id}: {e}")
    
    def start_broadcasting(self) -> None:
        """브로드캐스트 스레드 시작"""
        if not self.is_broadcasting:
            self.is_broadcasting = True
            self.broadcast_thread = threading.Thread(target=self._broadcast_worker, daemon=True)
            self.broadcast_thread.start()
            logger.info("Broadcast worker started")
    
    def stop_broadcasting(self) -> None:
        """브로드캐스트 스레드 중지"""
        self.is_broadcasting = False
        if self.broadcast_thread:
            self.broadcast_thread.join(timeout=5)
        logger.info("Broadcast worker stopped")
    
    def _broadcast_worker(self) -> None:
        """브로드캐스트 작업자 스레드"""
        while self.is_broadcasting:
            try:
                if self.broadcast_queue:
                    message = self.broadcast_queue.popleft()
                    self._process_broadcast_message(message)
                    
                    self.metrics['messages_sent'] += 1
                    
                time.sleep(0.1)  # 100ms 간격
                
            except Exception as e:
                logger.error(f"Broadcast worker error: {e}")
                time.sleep(1)
    
    def _process_broadcast_message(self, message: Dict[str, Any]) -> None:
        """브로드캐스트 메시지 처리"""
        try:
            msg_type = message.get('type')
            data = message.get('data')
            target_clients = message.get('clients', 'all')
            
            # 구독자에게만 전송
            if msg_type in self.client_subscriptions:
                target_clients = list(self.client_subscriptions[msg_type])
            
            if target_clients == 'all':
                self.socketio.emit(msg_type, data)
            else:
                for client_id in target_clients:
                    if client_id in self.connected_clients:
                        self.socketio.emit(msg_type, data, room=client_id)
                        
        except Exception as e:
            logger.error(f"Failed to process broadcast message: {e}")
    
    def broadcast_pair_alert(self, pair_data: Dict[str, Any]) -> None:
        """페어 알림 브로드캐스트"""
        # 실시간 데이터에 추가
        self.realtime_data['pairs'].append({
            'timestamp': datetime.now().isoformat(),
            'table_name': pair_data.get('table_name'),
            'pair_type': pair_data.get('pair_type'),
            'pair_cards': pair_data.get('pair_cards', []),
            'game_id': pair_data.get('game_id')
        })
        
        # 브로드캐스트 큐에 추가
        self.broadcast_queue.append({
            'type': 'pair_alert',
            'data': {
                'message': f"🎯 PAIR ALERT: {pair_data.get('pair_type')} at {pair_data.get('table_name')}!",
                'details': pair_data,
                'timestamp': datetime.now().isoformat(),
                'alert_level': 'high'
            }
        })
        
        logger.info(f"Pair alert queued: {pair_data.get('pair_type')} at {pair_data.get('table_name')}")
    
    def broadcast_stats_update(self, stats_data: Dict[str, Any]) -> None:
        """통계 업데이트 브로드캐스트"""
        self.realtime_data['stats'] = stats_data
        self.realtime_data['last_update'] = datetime.now()
        
        self.broadcast_queue.append({
            'type': 'stats_update',
            'data': {
                'stats': stats_data,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    def broadcast_system_alert(self, alert_data: Dict[str, Any]) -> None:
        """시스템 알림 브로드캐스트"""
        self.realtime_data['alerts'].append({
            'timestamp': datetime.now().isoformat(),
            'type': alert_data.get('type', 'info'),
            'message': alert_data.get('message', ''),
            'details': alert_data.get('details', {})
        })
        
        self.broadcast_queue.append({
            'type': 'system_alert',
            'data': {
                'alert': alert_data,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    def broadcast_performance_metrics(self, metrics_data: Dict[str, Any]) -> None:
        """성능 메트릭 브로드캐스트"""
        # WebSocket 메트릭 추가
        enhanced_metrics = {
            **metrics_data,
            'websocket': {
                'connected_clients': len(self.connected_clients),
                'total_connections': self.metrics['total_connections'],
                'messages_sent': self.metrics['messages_sent'],
                'queue_size': len(self.broadcast_queue)
            }
        }
        
        self.broadcast_queue.append({
            'type': 'performance_metrics',
            'data': {
                'metrics': enhanced_metrics,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    def send_to_client(self, client_id: str, event_type: str, data: Dict[str, Any]) -> bool:
        """특정 클라이언트에게 메시지 전송"""
        try:
            if client_id in self.connected_clients:
                self.socketio.emit(event_type, data, room=client_id)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            return False
    
    def get_connected_clients_info(self) -> Dict[str, Any]:
        """연결된 클라이언트 정보 조회"""
        clients_info = []
        
        for client_id in self.connected_clients:
            info = self.client_info.get(client_id, {})
            clients_info.append({
                'id': client_id,
                'connected_at': info.get('connected_at', '').isoformat() if info.get('connected_at') else '',
                'ip_address': info.get('ip_address', 'unknown'),
                'subscriptions': list(info.get('subscriptions', set())),
                'connection_duration': str(datetime.now() - info.get('connected_at', datetime.now())) if info.get('connected_at') else '0:00:00'
            })
        
        return {
            'total_clients': len(self.connected_clients),
            'clients': clients_info,
            'metrics': self.metrics,
            'queue_size': len(self.broadcast_queue)
        }
    
    def cleanup_disconnected_clients(self) -> int:
        """연결 해제된 클라이언트 정리"""
        cleaned_count = 0
        
        # 5분 이상 비활성 클라이언트 정리
        cutoff_time = datetime.now() - timedelta(minutes=5)
        
        for client_id in list(self.connected_clients):
            client_info = self.client_info.get(client_id, {})
            connected_at = client_info.get('connected_at')
            
            if not connected_at or connected_at < cutoff_time:
                try:
                    # 연결 확인
                    if not self.send_to_client(client_id, 'ping', {'timestamp': datetime.now().isoformat()}):
                        # 응답 없으면 제거
                        self.connected_clients.discard(client_id)
                        
                        # 구독 정보 정리
                        for subscription in client_info.get('subscriptions', set()):
                            self.client_subscriptions[subscription].discard(client_id)
                        
                        del self.client_info[client_id]
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.error(f"Error cleaning client {client_id}: {e}")
        
        if cleaned_count > 0:
            self.metrics['current_connections'] = len(self.connected_clients)
            logger.info(f"Cleaned {cleaned_count} disconnected clients")
        
        return cleaned_count
    
    def get_realtime_stats(self) -> Dict[str, Any]:
        """실시간 통계 조회"""
        return {
            'pairs': {
                'recent_count': len(self.realtime_data['pairs']),
                'last_pair': list(self.realtime_data['pairs'])[-1] if self.realtime_data['pairs'] else None
            },
            'alerts': {
                'recent_count': len(self.realtime_data['alerts']),
                'last_alert': list(self.realtime_data['alerts'])[-1] if self.realtime_data['alerts'] else None
            },
            'connections': {
                'current': len(self.connected_clients),
                'total': self.metrics['total_connections']
            },
            'performance': {
                'messages_sent': self.metrics['messages_sent'],
                'queue_size': len(self.broadcast_queue),
                'last_update': self.realtime_data['last_update'].isoformat()
            }
        }


if __name__ == '__main__':
    # 테스트는 실제 Flask-SocketIO와 함께 실행
    print("WebSocket Manager module loaded successfully")
    print("Use with Flask-SocketIO instance for full functionality")