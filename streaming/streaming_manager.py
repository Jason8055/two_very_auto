#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 스트리밍 통합 관리자
모든 스트리밍 컴포넌트를 통합 관리하는 메인 시스템
"""

import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import threading
import asyncio

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    """스트리밍 시스템 설정"""
    redis_host: str = "localhost"
    redis_port: int = 6379
    websocket_host: str = "0.0.0.0"
    websocket_port: int = 5001
    enable_message_broker: bool = True
    enable_websocket: bool = True
    enable_event_streaming: bool = True
    enable_notifications: bool = True
    auto_start_services: bool = True
    monitoring_enabled: bool = True
    metrics_interval: int = 30


@dataclass
class ServiceStatus:
    """서비스 상태"""
    name: str
    status: str  # running, stopped, error
    started_at: Optional[datetime]
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}


class StreamingManager:
    """스트리밍 통합 관리자"""
    
    def __init__(self, config: Optional[StreamingConfig] = None):
        self.config = config or StreamingConfig()
        
        # 서비스 인스턴스들
        self._message_broker = None
        self._websocket_server = None
        self._event_streamer = None
        self._notification_system = None
        
        # 서비스 상태
        self.services: Dict[str, ServiceStatus] = {}
        
        # 관리자 상태
        self.manager_started = False
        self.start_time = None
        
        # 모니터링
        self.monitoring_thread = None
        self.monitoring_enabled = self.config.monitoring_enabled
        
        # 통합 메트릭
        self.total_messages_processed = 0
        self.total_connections = 0
        self.total_notifications_sent = 0
        
        safe_print("🎛️ 스트리밍 통합 관리자 초기화 완료")
    
    def initialize_services(self):
        """모든 서비스 초기화"""
        safe_print("🚀 스트리밍 서비스 초기화 시작")
        
        # Message Broker 초기화
        if self.config.enable_message_broker:
            self._initialize_message_broker()
        
        # WebSocket 서버 초기화
        if self.config.enable_websocket:
            self._initialize_websocket_server()
        
        # Event Streamer 초기화
        if self.config.enable_event_streaming:
            self._initialize_event_streamer()
        
        # Notification System 초기화
        if self.config.enable_notifications:
            self._initialize_notification_system()
        
        # 서비스 간 통합 설정
        self._setup_service_integration()
        
        safe_print("✅ 모든 스트리밍 서비스 초기화 완료")
    
    def _initialize_message_broker(self):
        """메시지 브로커 초기화"""
        try:
            from message_broker import get_message_broker
            
            self._message_broker = get_message_broker(
                redis_host=self.config.redis_host
            )
            
            if self._message_broker and self._message_broker.redis_client:
                # 기본 스트림들 생성
                default_streams = [
                    "baccarat_stream",
                    "ai_prediction_stream", 
                    "system_alert_stream",
                    "performance_stream",
                    "websocket_stream"
                ]
                
                for stream_name in default_streams:
                    self._message_broker.create_stream(stream_name)
                    self._message_broker.create_consumer_group(stream_name, f"{stream_name}_group")
                
                self.services["message_broker"] = ServiceStatus(
                    name="message_broker",
                    status="running",
                    started_at=datetime.now()
                )
                safe_print("✅ 메시지 브로커 초기화 완료")
            else:
                raise Exception("Redis 연결 실패")
                
        except Exception as e:
            self.services["message_broker"] = ServiceStatus(
                name="message_broker",
                status="error",
                started_at=None,
                error_message=str(e)
            )
            logger.error(f"메시지 브로커 초기화 실패: {e}")
    
    def _initialize_websocket_server(self):
        """WebSocket 서버 초기화"""
        try:
            from websocket_server import get_websocket_server
            
            self._websocket_server = get_websocket_server(
                host=self.config.websocket_host,
                port=self.config.websocket_port
            )
            
            if self._websocket_server and self._websocket_server.app:
                self.services["websocket_server"] = ServiceStatus(
                    name="websocket_server",
                    status="initialized",
                    started_at=datetime.now()
                )
                safe_print("✅ WebSocket 서버 초기화 완료")
            else:
                raise Exception("WebSocket 서버 초기화 실패")
                
        except Exception as e:
            self.services["websocket_server"] = ServiceStatus(
                name="websocket_server",
                status="error",
                started_at=None,
                error_message=str(e)
            )
            logger.error(f"WebSocket 서버 초기화 실패: {e}")
    
    def _initialize_event_streamer(self):
        """이벤트 스트리머 초기화"""
        try:
            from event_streamer import get_event_streamer
            
            self._event_streamer = get_event_streamer()
            
            # 게임 시스템 통합
            if self._event_streamer:
                self._event_streamer.integrate_with_game_system()
                
                self.services["event_streamer"] = ServiceStatus(
                    name="event_streamer",
                    status="running",
                    started_at=datetime.now()
                )
                safe_print("✅ 이벤트 스트리머 초기화 완료")
            else:
                raise Exception("이벤트 스트리머 생성 실패")
                
        except Exception as e:
            self.services["event_streamer"] = ServiceStatus(
                name="event_streamer",
                status="error",
                started_at=None,
                error_message=str(e)
            )
            logger.error(f"이벤트 스트리머 초기화 실패: {e}")
    
    def _initialize_notification_system(self):
        """알림 시스템 초기화"""
        try:
            from notification_system import get_notification_system
            
            self._notification_system = get_notification_system()
            
            if self._notification_system:
                self.services["notification_system"] = ServiceStatus(
                    name="notification_system",
                    status="running",
                    started_at=datetime.now()
                )
                safe_print("✅ 알림 시스템 초기화 완료")
            else:
                raise Exception("알림 시스템 생성 실패")
                
        except Exception as e:
            self.services["notification_system"] = ServiceStatus(
                name="notification_system",
                status="error",
                started_at=None,
                error_message=str(e)
            )
            logger.error(f"알림 시스템 초기화 실패: {e}")
    
    def _setup_service_integration(self):
        """서비스 간 통합 설정"""
        safe_print("🔗 서비스 통합 설정 시작")
        
        try:
            # Message Broker와 WebSocket 통합
            if self._message_broker and self._websocket_server:
                self._websocket_server.start_message_broker_integration()
            
            # Event Streamer와 Notification System 통합
            if self._event_streamer and self._notification_system:
                self._setup_event_notification_integration()
            
            # 바카라 게임 시스템 통합
            self._setup_baccarat_integration()
            
            safe_print("✅ 서비스 통합 설정 완료")
            
        except Exception as e:
            logger.error(f"서비스 통합 설정 실패: {e}")
    
    def _setup_event_notification_integration(self):
        """이벤트-알림 통합 설정"""
        try:
            from event_streamer import EventType
            
            def handle_critical_events(event):
                """중요 이벤트 알림 처리"""
                if event.priority >= 4:  # High priority events
                    # 관리자에게 알림 전송
                    if event.event_type == EventType.SYSTEM_STATUS:
                        self._notification_system.send_notification(
                            "admin",
                            "system_alert",
                            {"message": f"시스템 이벤트: {event.payload}"}
                        )
                    
                    elif event.event_type == EventType.AI_PREDICTION:
                        # 높은 신뢰도 예측 알림
                        confidence = event.payload.get("confidence", 0)
                        if confidence > 85:
                            self._notification_system.send_notification(
                                "ai_subscriber",
                                "ai_prediction",
                                event.payload
                            )
            
            # 이벤트 스트리머에 핸들러 등록
            self._event_streamer.subscribe("notification_handler", handle_critical_events)
            
        except Exception as e:
            logger.error(f"이벤트-알림 통합 설정 실패: {e}")
    
    def _setup_baccarat_integration(self):
        """바카라 게임 시스템 통합"""
        try:
            # 바카라 게임 이벤트 핸들러 생성
            def create_game_event_handler():
                from event_streamer import EventType
                
                def handle_game_result(result_data):
                    """게임 결과 처리"""
                    if self._event_streamer:
                        self._event_streamer.add_event(
                            EventType.GAME_RESULT,
                            "baccarat_game",
                            result_data,
                            priority=3,
                            tags=["game", "result"]
                        )
                    
                    # 결과 알림
                    if self._notification_system:
                        self._notification_system.send_notification(
                            "game_subscriber",
                            "game_result",
                            result_data
                        )
                
                def handle_ai_prediction(prediction_data):
                    """AI 예측 처리"""
                    if self._event_streamer:
                        self._event_streamer.add_event(
                            EventType.AI_PREDICTION,
                            "ai_engine",
                            prediction_data,
                            priority=4,
                            tags=["ai", "prediction"]
                        )
                
                return handle_game_result, handle_ai_prediction
            
            # 핸들러 생성 및 등록
            game_handler, ai_handler = create_game_event_handler()
            
            # 외부 시스템이 이 핸들러들을 사용할 수 있도록 저장
            self.game_event_handler = game_handler
            self.ai_prediction_handler = ai_handler
            
        except Exception as e:
            logger.error(f"바카라 통합 설정 실패: {e}")
    
    def start_all_services(self):
        """모든 서비스 시작"""
        if self.manager_started:
            safe_print("스트리밍 관리자가 이미 실행 중입니다")
            return
        
        safe_print("🚀 스트리밍 서비스 시작")
        
        # 서비스 초기화 (아직 안됐으면)
        if not self.services:
            self.initialize_services()
        
        # WebSocket 서버는 별도 스레드에서 실행
        if self._websocket_server:
            def run_websocket_server():
                try:
                    self.services["websocket_server"].status = "running"
                    self._websocket_server.run(debug=False)
                except Exception as e:
                    self.services["websocket_server"].status = "error"
                    self.services["websocket_server"].error_message = str(e)
                    logger.error(f"WebSocket 서버 실행 실패: {e}")
            
            websocket_thread = threading.Thread(target=run_websocket_server, daemon=True)
            websocket_thread.start()
        
        # 모니터링 시작
        if self.monitoring_enabled:
            self.start_monitoring()
        
        self.manager_started = True
        self.start_time = datetime.now()
        
        safe_print("✅ 모든 스트리밍 서비스 시작 완료")
    
    def stop_all_services(self):
        """모든 서비스 중지"""
        safe_print("🛑 스트리밍 서비스 중지")
        
        # 모니터링 중지
        self.monitoring_enabled = False
        
        # 각 서비스 중지
        try:
            if self._event_streamer:
                self._event_streamer.stop()
            
            if self._notification_system:
                self._notification_system.stop()
                
        except Exception as e:
            logger.error(f"서비스 중지 중 오류: {e}")
        
        # 상태 업데이트
        for service in self.services.values():
            if service.status == "running":
                service.status = "stopped"
        
        self.manager_started = False
        safe_print("✅ 모든 스트리밍 서비스 중지 완료")
    
    def start_monitoring(self):
        """시스템 모니터링 시작"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        def monitoring_worker():
            safe_print("📊 시스템 모니터링 시작")
            
            while self.monitoring_enabled:
                try:
                    self.update_service_metrics()
                    self.update_system_metrics()
                    
                    time.sleep(self.config.metrics_interval)
                    
                except Exception as e:
                    logger.error(f"모니터링 오류: {e}")
                    time.sleep(10)
        
        self.monitoring_thread = threading.Thread(target=monitoring_worker, daemon=True)
        self.monitoring_thread.start()
    
    def update_service_metrics(self):
        """서비스 메트릭 업데이트"""
        try:
            # Message Broker 메트릭
            if self._message_broker:
                broker_metrics = self._message_broker.get_metrics()
                if "message_broker" in self.services:
                    self.services["message_broker"].metrics = broker_metrics
            
            # WebSocket 서버 메트릭
            if self._websocket_server:
                websocket_stats = self._websocket_server.get_server_stats()
                if "websocket_server" in self.services:
                    self.services["websocket_server"].metrics = websocket_stats
            
            # Event Streamer 메트릭
            if self._event_streamer:
                stream_stats = self._event_streamer.get_stream_statistics()
                if "event_streamer" in self.services:
                    self.services["event_streamer"].metrics = stream_stats
            
            # Notification System 메트릭
            if self._notification_system:
                notification_stats = self._notification_system.get_system_statistics()
                if "notification_system" in self.services:
                    self.services["notification_system"].metrics = notification_stats
                    
        except Exception as e:
            logger.error(f"메트릭 업데이트 실패: {e}")
    
    def update_system_metrics(self):
        """전체 시스템 메트릭 업데이트"""
        try:
            # 통합 메트릭 계산
            total_messages = 0
            total_connections = 0
            total_notifications = 0
            
            if self._message_broker:
                broker_metrics = self._message_broker.get_metrics()
                total_messages += broker_metrics.get("messages_produced", 0)
                total_messages += broker_metrics.get("messages_consumed", 0)
            
            if self._websocket_server:
                websocket_stats = self._websocket_server.get_server_stats()
                total_connections = websocket_stats.get("connected_clients", 0)
            
            if self._notification_system:
                notification_stats = self._notification_system.get_system_statistics()
                total_notifications = notification_stats.get("notifications_sent", 0)
            
            self.total_messages_processed = total_messages
            self.total_connections = total_connections
            self.total_notifications_sent = total_notifications
            
        except Exception as e:
            logger.error(f"시스템 메트릭 업데이트 실패: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """전체 시스템 상태"""
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        running_services = len([s for s in self.services.values() if s.status == "running"])
        error_services = len([s for s in self.services.values() if s.status == "error"])
        
        return {
            "manager_status": "running" if self.manager_started else "stopped",
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": uptime,
            "total_services": len(self.services),
            "running_services": running_services,
            "error_services": error_services,
            "services": {
                name: {
                    "status": service.status,
                    "started_at": service.started_at.isoformat() if service.started_at else None,
                    "error_message": service.error_message,
                    "metrics": service.metrics
                }
                for name, service in self.services.items()
            },
            "system_metrics": {
                "total_messages_processed": self.total_messages_processed,
                "total_connections": self.total_connections,
                "total_notifications_sent": self.total_notifications_sent
            },
            "config": asdict(self.config)
        }
    
    def restart_service(self, service_name: str) -> bool:
        """특정 서비스 재시작"""
        if service_name not in self.services:
            return False
        
        safe_print(f"🔄 서비스 재시작: {service_name}")
        
        try:
            # 서비스별 재시작 로직
            if service_name == "message_broker":
                self._initialize_message_broker()
            elif service_name == "websocket_server":
                self._initialize_websocket_server()
            elif service_name == "event_streamer":
                self._initialize_event_streamer()
            elif service_name == "notification_system":
                self._initialize_notification_system()
            
            return self.services[service_name].status != "error"
            
        except Exception as e:
            logger.error(f"서비스 재시작 실패 ({service_name}): {e}")
            return False
    
    def health_check(self) -> Dict[str, bool]:
        """헬스 체크"""
        health = {}
        
        for service_name, service in self.services.items():
            health[service_name] = service.status == "running"
        
        health["overall"] = all(health.values())
        
        return health


# 전역 인스턴스
_streaming_manager = None

def get_streaming_manager(config: Optional[StreamingConfig] = None) -> StreamingManager:
    """스트리밍 관리자 인스턴스 반환"""
    global _streaming_manager
    if _streaming_manager is None:
        _streaming_manager = StreamingManager(config)
    return _streaming_manager


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 스트리밍 통합 관리자 테스트 ===")
    
    # 설정 생성
    config = StreamingConfig(
        redis_host="localhost",
        websocket_port=5001,
        auto_start_services=True,
        monitoring_enabled=True
    )
    
    # 관리자 생성 및 초기화
    manager = get_streaming_manager(config)
    manager.initialize_services()
    
    # 시스템 상태 확인
    status = manager.get_system_status()
    safe_print(f"📊 시스템 상태: {status['manager_status']}")
    safe_print(f"🔧 실행 중인 서비스: {status['running_services']}/{status['total_services']}")
    
    # 헬스 체크
    health = manager.health_check()
    safe_print(f"💚 전체 시스템 건강상태: {health['overall']}")
    
    # 서비스 상세 정보
    for service_name, service_info in status['services'].items():
        safe_print(f"  - {service_name}: {service_info['status']}")
    
    if input("스트리밍 시스템을 시작하시겠습니까? (y/N): ").lower() == 'y':
        try:
            manager.start_all_services()
            
            safe_print("시스템이 실행 중입니다. Ctrl+C로 종료하세요.")
            while True:
                time.sleep(5)
                
                # 주기적 상태 업데이트
                status = manager.get_system_status()
                uptime = status.get('uptime_seconds', 0)
                safe_print(f"📊 가동시간: {uptime:.0f}초, 연결: {manager.total_connections}개, 메시지: {manager.total_messages_processed}개")
                
        except KeyboardInterrupt:
            safe_print("사용자 중단 신호")
        
        finally:
            manager.stop_all_services()
    
    safe_print("🏁 스트리밍 통합 관리자 테스트 완료")