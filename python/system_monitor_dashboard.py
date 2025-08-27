#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시스템 모니터링 대시보드
실시간 성능 메트릭, 리소스 사용률, 알림 시스템
"""

import psutil
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import asyncio
import websockets
import threading
from collections import deque


@dataclass
class SystemMetrics:
    """시스템 메트릭"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    uptime_hours: float


@dataclass
class AlertRule:
    """알림 규칙"""
    name: str
    metric: str
    threshold: float
    operator: str  # '>', '<', '>=', '<='
    enabled: bool = True
    cooldown_minutes: int = 5


class SystemMonitor:
    """시스템 모니터"""
    
    def __init__(self, data_retention_hours: int = 24):
        self.data_retention_hours = data_retention_hours
        self.metrics_history = deque(maxlen=data_retention_hours * 60)  # 1분마다 수집
        self.alert_rules = self._load_default_alert_rules()
        self.alert_history = deque(maxlen=1000)
        self.last_alert_times = {}
        
        # 로깅 설정
        self.logger = logging.getLogger(__name__)
        
        # WebSocket 클라이언트 관리
        self.websocket_clients = set()
        self.monitoring_active = False
    
    def _load_default_alert_rules(self) -> List[AlertRule]:
        """기본 알림 규칙 로드"""
        return [
            AlertRule("높은 CPU 사용률", "cpu_percent", 85.0, ">="),
            AlertRule("높은 메모리 사용률", "memory_percent", 90.0, ">="),
            AlertRule("높은 디스크 사용률", "disk_percent", 95.0, ">="),
            AlertRule("낮은 메모리", "memory_percent", 95.0, ">=", cooldown_minutes=1),
            AlertRule("프로세스 과다", "process_count", 500, ">="),
        ]
    
    def collect_metrics(self) -> SystemMetrics:
        """현재 시스템 메트릭 수집"""
        try:
            # CPU 및 메모리
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # 디스크 (루트 디렉토리 기준)
            disk = psutil.disk_usage('/')
            
            # 네트워크
            net_io = psutil.net_io_counters()
            
            # 프로세스 수
            process_count = len(psutil.pids())
            
            # 시스템 업타임
            boot_time = psutil.boot_time()
            uptime_hours = (time.time() - boot_time) / 3600
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_gb=memory.used / (1024**3),
                memory_total_gb=memory.total / (1024**3),
                disk_percent=disk.percent,
                disk_used_gb=disk.used / (1024**3),
                disk_total_gb=disk.total / (1024**3),
                network_bytes_sent=net_io.bytes_sent,
                network_bytes_recv=net_io.bytes_recv,
                process_count=process_count,
                uptime_hours=uptime_hours
            )
        except Exception as e:
            self.logger.error(f"메트릭 수집 실패: {e}")
            return None
    
    def check_alerts(self, metrics: SystemMetrics):
        """알림 규칙 확인"""
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
            
            try:
                metric_value = getattr(metrics, rule.metric)
                
                # 임계값 확인
                triggered = False
                if rule.operator == ">=" and metric_value >= rule.threshold:
                    triggered = True
                elif rule.operator == ">" and metric_value > rule.threshold:
                    triggered = True
                elif rule.operator == "<=" and metric_value <= rule.threshold:
                    triggered = True
                elif rule.operator == "<" and metric_value < rule.threshold:
                    triggered = True
                
                if triggered:
                    # 쿨다운 확인
                    now = datetime.now()
                    last_alert = self.last_alert_times.get(rule.name)
                    
                    if (last_alert is None or 
                        (now - last_alert).total_seconds() >= rule.cooldown_minutes * 60):
                        
                        self._trigger_alert(rule, metric_value, metrics.timestamp)
                        self.last_alert_times[rule.name] = now
            
            except AttributeError:
                self.logger.warning(f"잘못된 메트릭: {rule.metric}")
    
    def _trigger_alert(self, rule: AlertRule, value: float, timestamp: str):
        """알림 발생"""
        alert = {
            'rule_name': rule.name,
            'metric': rule.metric,
            'threshold': rule.threshold,
            'actual_value': value,
            'timestamp': timestamp,
            'severity': self._get_alert_severity(rule, value)
        }
        
        self.alert_history.append(alert)
        self.logger.warning(f"알림 발생: {rule.name} - {value:.2f} {rule.operator} {rule.threshold}")
        
        # WebSocket으로 실시간 알림 전송
        asyncio.create_task(self._broadcast_alert(alert))
    
    def _get_alert_severity(self, rule: AlertRule, value: float) -> str:
        """알림 심각도 결정"""
        if rule.metric in ['cpu_percent', 'memory_percent', 'disk_percent']:
            if value >= 95:
                return 'critical'
            elif value >= 85:
                return 'warning'
        return 'info'
    
    async def _broadcast_alert(self, alert: Dict):
        """WebSocket으로 알림 브로드캐스트"""
        if self.websocket_clients:
            message = json.dumps({
                'type': 'alert',
                'data': alert
            })
            
            # 연결이 끊긴 클라이언트 제거
            disconnected = set()
            for client in self.websocket_clients:
                try:
                    await client.send(message)
                except:
                    disconnected.add(client)
            
            self.websocket_clients -= disconnected
    
    async def _broadcast_metrics(self, metrics: SystemMetrics):
        """WebSocket으로 메트릭 브로드캐스트"""
        if self.websocket_clients:
            message = json.dumps({
                'type': 'metrics',
                'data': asdict(metrics)
            })
            
            disconnected = set()
            for client in self.websocket_clients:
                try:
                    await client.send(message)
                except:
                    disconnected.add(client)
            
            self.websocket_clients -= disconnected
    
    def start_monitoring(self, interval_seconds: int = 60):
        """모니터링 시작"""
        async def monitor_loop():
            self.monitoring_active = True
            self.logger.info(f"시스템 모니터링 시작 (간격: {interval_seconds}초)")
            
            while self.monitoring_active:
                try:
                    # 메트릭 수집
                    metrics = self.collect_metrics()
                    if metrics:
                        # 히스토리에 추가
                        self.metrics_history.append(metrics)
                        
                        # 알림 확인
                        self.check_alerts(metrics)
                        
                        # WebSocket 브로드캐스트
                        await self._broadcast_metrics(metrics)
                    
                    await asyncio.sleep(interval_seconds)
                    
                except Exception as e:
                    self.logger.error(f"모니터링 오류: {e}")
                    await asyncio.sleep(interval_seconds)
        
        # 이벤트 루프에서 실행
        asyncio.create_task(monitor_loop())
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        self.logger.info("시스템 모니터링 중지")
    
    def get_current_status(self) -> Dict:
        """현재 시스템 상태 반환"""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        latest = self.metrics_history[-1]
        recent_alerts = [alert for alert in self.alert_history 
                        if datetime.fromisoformat(alert['timestamp']) > 
                        datetime.now() - timedelta(minutes=30)]
        
        return {
            'status': 'healthy' if not recent_alerts else 'warning',
            'current_metrics': asdict(latest),
            'recent_alerts_count': len(recent_alerts),
            'active_connections': len(self.websocket_clients),
            'data_points': len(self.metrics_history)
        }
    
    def get_metrics_history(self, hours: int = 1) -> List[Dict]:
        """메트릭 히스토리 반환"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            asdict(metrics) for metrics in self.metrics_history
            if datetime.fromisoformat(metrics.timestamp) > cutoff
        ]
    
    def get_alert_history(self, hours: int = 24) -> List[Dict]:
        """알림 히스토리 반환"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if datetime.fromisoformat(alert['timestamp']) > cutoff
        ]
    
    async def websocket_handler(self, websocket, path):
        """WebSocket 연결 핸들러"""
        self.websocket_clients.add(websocket)
        self.logger.info(f"WebSocket 클라이언트 연결: {len(self.websocket_clients)}개")
        
        try:
            # 초기 상태 전송
            status = self.get_current_status()
            await websocket.send(json.dumps({
                'type': 'status',
                'data': status
            }))
            
            # 연결 유지
            async for message in websocket:
                # 클라이언트 명령 처리 (필요시)
                pass
                
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.websocket_clients.discard(websocket)
            self.logger.info(f"WebSocket 클라이언트 연결 해제: {len(self.websocket_clients)}개")


# 전역 모니터 인스턴스
system_monitor = SystemMonitor()


def start_websocket_server(host: str = "localhost", port: int = 8765):
    """WebSocket 서버 시작"""
    async def main():
        # 모니터링 시작
        system_monitor.start_monitoring(interval_seconds=30)
        
        # WebSocket 서버 시작
        server = await websockets.serve(
            system_monitor.websocket_handler, host, port
        )
        
        logging.info(f"시스템 모니터링 WebSocket 서버 시작: ws://{host}:{port}")
        await server.wait_closed()
    
    asyncio.run(main())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='시스템 모니터링 대시보드')
    parser.add_argument('--action', choices=['monitor', 'status', 'server'], 
                       default='monitor', help='실행할 작업')
    parser.add_argument('--host', default='localhost', help='WebSocket 서버 호스트')
    parser.add_argument('--port', type=int, default=8765, help='WebSocket 서버 포트')
    
    args = parser.parse_args()
    
    if args.action == 'monitor':
        # 일회성 모니터링
        metrics = system_monitor.collect_metrics()
        if metrics:
            print(f"\n시스템 상태 ({metrics.timestamp})")
            print(f"  CPU: {metrics.cpu_percent:.1f}%")
            print(f"  메모리: {metrics.memory_percent:.1f}% ({metrics.memory_used_gb:.1f}GB/{metrics.memory_total_gb:.1f}GB)")
            print(f"  디스크: {metrics.disk_percent:.1f}% ({metrics.disk_used_gb:.1f}GB/{metrics.disk_total_gb:.1f}GB)")
            print(f"  프로세스: {metrics.process_count}개")
            print(f"  업타임: {metrics.uptime_hours:.1f}시간")
    
    elif args.action == 'status':
        status = system_monitor.get_current_status()
        print(f"\n시스템 모니터 상태: {status['status']}")
        if status['status'] != 'no_data':
            print(f"  데이터 포인트: {status['data_points']}개")
            print(f"  최근 알림: {status['recent_alerts_count']}개")
            print(f"  활성 연결: {status['active_connections']}개")
    
    elif args.action == 'server':
        start_websocket_server(args.host, args.port)