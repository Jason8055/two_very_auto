#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Connection Monitoring Service - FastAPI
다중 클라이언트 연결 모니터링 및 관리
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import psutil
import time

logger = logging.getLogger(__name__)

class ClientType(Enum):
    """클라이언트 타입"""
    DASHBOARD = "dashboard"
    API_CLIENT = "api_client"
    MOBILE_APP = "mobile_app"
    ADMIN_PANEL = "admin_panel"
    MONITORING = "monitoring"
    UNKNOWN = "unknown"

class ConnectionStatus(Enum):
    """연결 상태"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ACTIVE = "active"
    IDLE = "idle"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"

@dataclass
class ClientMetrics:
    """클라이언트 메트릭"""
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors_count: int = 0
    last_activity: Optional[datetime] = None
    response_times: List[float] = field(default_factory=list)
    
    def add_response_time(self, response_time: float):
        """응답 시간 추가"""
        self.response_times.append(response_time)
        # 최근 100개만 유지
        if len(self.response_times) > 100:
            self.response_times.pop(0)
    
    def get_avg_response_time(self) -> float:
        """평균 응답 시간"""
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
    
    def get_max_response_time(self) -> float:
        """최대 응답 시간"""
        return max(self.response_times) if self.response_times else 0.0

@dataclass
class ClientInfo:
    """클라이언트 정보"""
    client_id: str
    client_type: ClientType
    status: ConnectionStatus
    connected_at: datetime
    last_ping: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    subscriptions: Set[str] = field(default_factory=set)
    metrics: ClientMetrics = field(default_factory=ClientMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_connection_duration(self) -> timedelta:
        """연결 지속 시간"""
        return datetime.now() - self.connected_at
    
    def get_idle_time(self) -> timedelta:
        """유휴 시간"""
        if self.last_activity:
            return datetime.now() - self.last_activity
        return self.get_connection_duration()
    
    def is_stale(self, max_idle_minutes: int = 30) -> bool:
        """오래된 연결인지 확인"""
        return self.get_idle_time().total_seconds() > (max_idle_minutes * 60)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            'client_id': self.client_id,
            'client_type': self.client_type.value,
            'status': self.status.value,
            'connected_at': self.connected_at.isoformat(),
            'last_ping': self.last_ping.isoformat() if self.last_ping else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'subscriptions': list(self.subscriptions),
            'connection_duration': str(self.get_connection_duration()),
            'idle_time': str(self.get_idle_time()),
            'metrics': {
                'messages_sent': self.metrics.messages_sent,
                'messages_received': self.metrics.messages_received,
                'bytes_sent': self.metrics.bytes_sent,
                'bytes_received': self.metrics.bytes_received,
                'errors_count': self.metrics.errors_count,
                'avg_response_time': self.metrics.get_avg_response_time(),
                'max_response_time': self.metrics.get_max_response_time(),
                'response_time_samples': len(self.metrics.response_times)
            },
            'metadata': self.metadata
        }

class ConnectionMonitor:
    """연결 모니터링 서비스"""
    
    def __init__(self):
        self.clients: Dict[str, ClientInfo] = {}
        self.connection_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # 설정
        self.ping_interval = 30  # 30초마다 ping
        self.max_idle_time = 30  # 30분 후 stale 처리
        self.cleanup_interval = 60  # 1분마다 정리
        
        # 통계
        self.stats = {
            'total_connections': 0,
            'total_disconnections': 0,
            'peak_concurrent_connections': 0,
            'avg_connection_duration': 0.0,
            'by_client_type': {},
            'by_status': {},
            'system_metrics': {}
        }
    
    def register_client(self, client_id: str, websocket, client_type: ClientType = ClientType.UNKNOWN, 
                       ip_address: str = None, user_agent: str = None) -> ClientInfo:
        """클라이언트 등록"""
        now = datetime.now()
        
        client_info = ClientInfo(
            client_id=client_id,
            client_type=client_type,
            status=ConnectionStatus.CONNECTED,
            connected_at=now,
            last_activity=now,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.clients[client_id] = client_info
        self.stats['total_connections'] += 1
        
        # 피크 동시 접속자 수 업데이트
        current_count = len(self.clients)
        if current_count > self.stats['peak_concurrent_connections']:
            self.stats['peak_concurrent_connections'] = current_count
        
        # 연결 이력 추가
        self._add_connection_event('connected', client_info)
        
        logger.info(f"🔗 클라이언트 등록: {client_id} ({client_type.value}) - 총 {current_count}개 연결")
        return client_info
    
    def unregister_client(self, client_id: str):
        """클라이언트 해제"""
        if client_id in self.clients:
            client_info = self.clients[client_id]
            client_info.status = ConnectionStatus.DISCONNECTED
            
            # 연결 이력 추가
            self._add_connection_event('disconnected', client_info)
            
            # 통계 업데이트
            self.stats['total_disconnections'] += 1
            
            # 클라이언트 제거
            del self.clients[client_id]
            
            logger.info(f"🔗 클라이언트 해제: {client_id} - 총 {len(self.clients)}개 연결")
    
    def update_client_activity(self, client_id: str, activity_type: str = "message", 
                              bytes_sent: int = 0, bytes_received: int = 0, response_time: float = None):
        """클라이언트 활동 업데이트"""
        if client_id not in self.clients:
            return
        
        client_info = self.clients[client_id]
        now = datetime.now()
        
        client_info.last_activity = now
        client_info.status = ConnectionStatus.ACTIVE
        
        # 메트릭 업데이트
        if activity_type == "message_sent":
            client_info.metrics.messages_sent += 1
        elif activity_type == "message_received":
            client_info.metrics.messages_received += 1
        
        client_info.metrics.bytes_sent += bytes_sent
        client_info.metrics.bytes_received += bytes_received
        
        if response_time is not None:
            client_info.metrics.add_response_time(response_time)
        
        client_info.metrics.last_activity = now
    
    def update_client_ping(self, client_id: str):
        """클라이언트 ping 업데이트"""
        if client_id in self.clients:
            self.clients[client_id].last_ping = datetime.now()
    
    def add_client_subscription(self, client_id: str, subscription: str):
        """클라이언트 구독 추가"""
        if client_id in self.clients:
            self.clients[client_id].subscriptions.add(subscription)
    
    def remove_client_subscription(self, client_id: str, subscription: str):
        """클라이언트 구독 제거"""
        if client_id in self.clients:
            self.clients[client_id].subscriptions.discard(subscription)
    
    def get_client_info(self, client_id: str) -> Optional[ClientInfo]:
        """클라이언트 정보 조회"""
        return self.clients.get(client_id)
    
    def get_all_clients(self) -> List[ClientInfo]:
        """모든 클라이언트 정보"""
        return list(self.clients.values())
    
    def get_clients_by_type(self, client_type: ClientType) -> List[ClientInfo]:
        """타입별 클라이언트 조회"""
        return [client for client in self.clients.values() if client.client_type == client_type]
    
    def get_clients_by_subscription(self, subscription: str) -> List[ClientInfo]:
        """구독별 클라이언트 조회"""
        return [client for client in self.clients.values() if subscription in client.subscriptions]
    
    def get_connection_count(self) -> int:
        """현재 연결 수"""
        return len(self.clients)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """연결 통계"""
        now = datetime.now()
        
        # 타입별 통계
        type_stats = {}
        status_stats = {}
        
        total_duration = 0
        active_count = 0
        
        for client in self.clients.values():
            # 타입별
            type_key = client.client_type.value
            type_stats[type_key] = type_stats.get(type_key, 0) + 1
            
            # 상태별
            status_key = client.status.value
            status_stats[status_key] = status_stats.get(status_key, 0) + 1
            
            # 평균 연결 시간 계산
            duration = client.get_connection_duration().total_seconds()
            total_duration += duration
            
            if client.status == ConnectionStatus.ACTIVE:
                active_count += 1
        
        # 시스템 메트릭
        system_metrics = self._get_system_metrics()
        
        avg_duration = total_duration / len(self.clients) if self.clients else 0
        
        stats = {
            'current_connections': len(self.clients),
            'active_connections': active_count,
            'peak_concurrent_connections': self.stats['peak_concurrent_connections'],
            'total_connections': self.stats['total_connections'],
            'total_disconnections': self.stats['total_disconnections'],
            'avg_connection_duration_seconds': avg_duration,
            'by_client_type': type_stats,
            'by_status': status_stats,
            'system_metrics': system_metrics,
            'timestamp': now.isoformat()
        }
        
        self.stats.update({
            'by_client_type': type_stats,
            'by_status': status_stats,
            'avg_connection_duration': avg_duration,
            'system_metrics': system_metrics
        })
        
        return stats
    
    def get_detailed_client_list(self) -> List[Dict[str, Any]]:
        """상세 클라이언트 목록"""
        return [client.to_dict() for client in self.clients.values()]
    
    def get_connection_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """연결 이력"""
        return self.connection_history[-limit:] if limit else self.connection_history
    
    async def start_monitoring(self):
        """모니터링 시작"""
        if self.running:
            return
        
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🔍 연결 모니터링 서비스 시작")
    
    async def stop_monitoring(self):
        """모니터링 중지"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("🔍 연결 모니터링 서비스 중지")
    
    async def _monitoring_loop(self):
        """모니터링 루프"""
        logger.info("🔄 연결 모니터링 루프 시작")
        
        while self.running:
            try:
                # 유휴 클라이언트 검사
                await self._check_idle_clients()
                
                # 정리 작업
                await self._cleanup_stale_connections()
                
                # 통계 업데이트
                self.get_connection_stats()
                
                # 주기적 대기
                await asyncio.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"❌ 연결 모니터링 오류: {e}")
                await asyncio.sleep(10)
    
    async def _check_idle_clients(self):
        """유휴 클라이언트 검사"""
        now = datetime.now()
        idle_clients = []
        
        for client_id, client_info in self.clients.items():
            idle_time = client_info.get_idle_time()
            
            if idle_time.total_seconds() > 300:  # 5분 유휴
                if client_info.status != ConnectionStatus.IDLE:
                    client_info.status = ConnectionStatus.IDLE
                    logger.info(f"💤 클라이언트 유휴 상태: {client_id} (유휴시간: {idle_time})")
            
            if client_info.is_stale(self.max_idle_time):
                idle_clients.append(client_id)
        
        # 오래된 연결 정리 (실제 WebSocket 연결은 외부에서 처리)
        for client_id in idle_clients:
            logger.warning(f"🗑️ 오래된 연결 감지: {client_id}")
            client_info = self.clients[client_id]
            client_info.status = ConnectionStatus.ERROR
            self._add_connection_event('stale_detected', client_info)
    
    async def _cleanup_stale_connections(self):
        """오래된 연결 정리"""
        # 연결 이력 정리
        if len(self.connection_history) > self.max_history_size:
            self.connection_history = self.connection_history[-self.max_history_size//2:]
    
    def _add_connection_event(self, event_type: str, client_info: ClientInfo):
        """연결 이벤트 추가"""
        event = {
            'event_type': event_type,
            'client_id': client_info.client_id,
            'client_type': client_info.client_type.value,
            'timestamp': datetime.now().isoformat(),
            'connection_duration': str(client_info.get_connection_duration()) if event_type == 'disconnected' else None,
            'ip_address': client_info.ip_address
        }
        
        self.connection_history.append(event)
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """시스템 메트릭 수집"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available // (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free // (1024 * 1024 * 1024),
                'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ 시스템 메트릭 수집 실패: {e}")
            return {}

# 전역 연결 모니터 인스턴스
connection_monitor = ConnectionMonitor()

async def get_connection_monitor() -> ConnectionMonitor:
    """연결 모니터 의존성"""
    return connection_monitor