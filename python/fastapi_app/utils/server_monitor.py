#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server Status Monitoring System
서버 상태 실시간 모니터링 시스템
"""

import psutil
import asyncio
import time
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import threading

from utils.smart_output import info, success, warning, error, OutputLevel

class AlertLevel(Enum):
    """알림 레벨"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class SystemMetrics:
    """시스템 메트릭"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_sent_mb: float
    network_recv_mb: float
    active_connections: int = 0
    requests_per_minute: int = 0

@dataclass
class MonitoringThresholds:
    """모니터링 임계값"""
    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    memory_warning: float = 80.0
    memory_critical: float = 95.0
    disk_warning: float = 85.0
    disk_critical: float = 95.0

class ServerMonitor:
    """서버 모니터링"""
    
    def __init__(self, thresholds: MonitoringThresholds = None):
        self.thresholds = thresholds or MonitoringThresholds()
        self.metrics_history: List[SystemMetrics] = []
        self.max_history = 100
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_network = None
        
    def start_monitoring(self, interval: int = 30):
        """모니터링 시작"""
        if self.running:
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,)
        )
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        success("서버 모니터링 시작", 
                간격=f"{interval}초",
                CPU임계값=f"{self.thresholds.cpu_warning}%/{self.thresholds.cpu_critical}%",
                메모리임계값=f"{self.thresholds.memory_warning}%/{self.thresholds.memory_critical}%")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        info("서버 모니터링 중지")
    
    def _monitor_loop(self, interval: int):
        """모니터링 루프"""
        while self.running:
            try:
                metrics = self._collect_metrics()
                self._store_metrics(metrics)
                self._check_alerts(metrics)
                
                time.sleep(interval)
                
            except Exception as e:
                error("모니터링 오류", 오류=str(e))
                time.sleep(interval)
    
    def _collect_metrics(self) -> SystemMetrics:
        """시스템 메트릭 수집"""
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 메모리 정보
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        
        # 디스크 정보
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent if disk.total > 0 else 0
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        
        # 네트워크 정보
        network = psutil.net_io_counters()
        if self.last_network:
            network_sent_mb = (network.bytes_sent - self.last_network.bytes_sent) / (1024**2)
            network_recv_mb = (network.bytes_recv - self.last_network.bytes_recv) / (1024**2)
        else:
            network_sent_mb = 0.0
            network_recv_mb = 0.0
        self.last_network = network
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            memory_total_gb=memory_total_gb,
            disk_percent=disk_percent,
            disk_used_gb=disk_used_gb,
            disk_total_gb=disk_total_gb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb
        )
    
    def _store_metrics(self, metrics: SystemMetrics):
        """메트릭 저장"""
        self.metrics_history.append(metrics)
        
        # 히스토리 크기 제한
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)
    
    def _check_alerts(self, metrics: SystemMetrics):
        """알림 확인"""
        alerts = []
        
        # CPU 확인
        if metrics.cpu_percent >= self.thresholds.cpu_critical:
            alerts.append(("CPU 사용률 위험", f"{metrics.cpu_percent:.1f}%", AlertLevel.CRITICAL))
        elif metrics.cpu_percent >= self.thresholds.cpu_warning:
            alerts.append(("CPU 사용률 경고", f"{metrics.cpu_percent:.1f}%", AlertLevel.WARNING))
        
        # 메모리 확인
        if metrics.memory_percent >= self.thresholds.memory_critical:
            alerts.append(("메모리 사용률 위험", f"{metrics.memory_percent:.1f}%", AlertLevel.CRITICAL))
        elif metrics.memory_percent >= self.thresholds.memory_warning:
            alerts.append(("메모리 사용률 경고", f"{metrics.memory_percent:.1f}%", AlertLevel.WARNING))
        
        # 디스크 확인
        if metrics.disk_percent >= self.thresholds.disk_critical:
            alerts.append(("디스크 사용률 위험", f"{metrics.disk_percent:.1f}%", AlertLevel.CRITICAL))
        elif metrics.disk_percent >= self.thresholds.disk_warning:
            alerts.append(("디스크 사용률 경고", f"{metrics.disk_percent:.1f}%", AlertLevel.WARNING))
        
        # 알림 전송
        for title, value, level in alerts:
            if level == AlertLevel.CRITICAL:
                error(title, 값=value, 시간=metrics.timestamp.strftime("%H:%M:%S"))
            elif level == AlertLevel.WARNING:
                warning(title, 값=value, 시간=metrics.timestamp.strftime("%H:%M:%S"))
    
    def get_current_status(self) -> Optional[SystemMetrics]:
        """현재 상태 조회"""
        if not self.metrics_history:
            return None
        return self.metrics_history[-1]
    
    def get_status_summary(self) -> Dict:
        """상태 요약"""
        current = self.get_current_status()
        if not current:
            return {"status": "no_data"}
        
        # 상태 판정
        status = "healthy"
        if (current.cpu_percent >= self.thresholds.cpu_critical or
            current.memory_percent >= self.thresholds.memory_critical or
            current.disk_percent >= self.thresholds.disk_critical):
            status = "critical"
        elif (current.cpu_percent >= self.thresholds.cpu_warning or
              current.memory_percent >= self.thresholds.memory_warning or
              current.disk_percent >= self.thresholds.disk_warning):
            status = "warning"
        
        return {
            "status": status,
            "timestamp": current.timestamp.isoformat(),
            "cpu": {
                "percent": round(current.cpu_percent, 1),
                "status": self._get_resource_status(current.cpu_percent, 
                                                  self.thresholds.cpu_warning,
                                                  self.thresholds.cpu_critical)
            },
            "memory": {
                "percent": round(current.memory_percent, 1),
                "used_gb": round(current.memory_used_gb, 2),
                "total_gb": round(current.memory_total_gb, 2),
                "status": self._get_resource_status(current.memory_percent,
                                                  self.thresholds.memory_warning,
                                                  self.thresholds.memory_critical)
            },
            "disk": {
                "percent": round(current.disk_percent, 1),
                "used_gb": round(current.disk_used_gb, 2),
                "total_gb": round(current.disk_total_gb, 2),
                "status": self._get_resource_status(current.disk_percent,
                                                  self.thresholds.disk_warning,
                                                  self.thresholds.disk_critical)
            },
            "network": {
                "sent_mb": round(current.network_sent_mb, 2),
                "recv_mb": round(current.network_recv_mb, 2)
            }
        }
    
    def _get_resource_status(self, value: float, warning: float, critical: float) -> str:
        """리소스 상태 판정"""
        if value >= critical:
            return "critical"
        elif value >= warning:
            return "warning"
        else:
            return "normal"

class ConsoleMonitorWidget:
    """콘솔 모니터링 위젯"""
    
    def __init__(self, monitor: ServerMonitor):
        self.monitor = monitor
        self.running = False
        self.widget_thread: Optional[threading.Thread] = None
        
    def start_widget(self, refresh_interval: int = 5):
        """위젯 시작"""
        if self.running:
            return
            
        self.running = True
        self.widget_thread = threading.Thread(
            target=self._widget_loop,
            args=(refresh_interval,)
        )
        self.widget_thread.daemon = True
        self.widget_thread.start()
    
    def stop_widget(self):
        """위젯 중지"""
        self.running = False
        if self.widget_thread:
            self.widget_thread.join(timeout=2.0)
    
    def _widget_loop(self, refresh_interval: int):
        """위젯 루프"""
        while self.running:
            try:
                self._render_status()
                time.sleep(refresh_interval)
            except Exception as e:
                print(f"위젯 오류: {e}")
                time.sleep(refresh_interval)
    
    def _render_status(self):
        """상태 렌더링"""
        summary = self.monitor.get_status_summary()
        
        if summary.get("status") == "no_data":
            return
        
        # 상태 아이콘
        status_icons = {
            "healthy": "✅",
            "warning": "⚠️", 
            "critical": "🚨"
        }
        
        icon = status_icons.get(summary["status"], "❓")
        timestamp = datetime.fromisoformat(summary["timestamp"]).strftime("%H:%M:%S")
        
        # 간단한 상태 표시
        cpu = summary["cpu"]["percent"]
        memory = summary["memory"]["percent"]
        disk = summary["disk"]["percent"]
        
        status_line = (f"{icon} [{timestamp}] "
                      f"CPU: {cpu:5.1f}% | "
                      f"MEM: {memory:5.1f}% | "
                      f"DISK: {disk:5.1f}% | "
                      f"Status: {summary['status'].upper()}")
        
        # 이전 라인 지우고 새로 출력
        sys.stdout.write(f"\r{' ' * 100}\r{status_line}")
        sys.stdout.flush()

# 전역 모니터 인스턴스
_global_monitor: Optional[ServerMonitor] = None

def get_server_monitor() -> ServerMonitor:
    """전역 서버 모니터 가져오기"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = ServerMonitor()
    return _global_monitor

def start_server_monitoring(interval: int = 30, show_widget: bool = False):
    """서버 모니터링 시작"""
    monitor = get_server_monitor()
    monitor.start_monitoring(interval)
    
    if show_widget:
        widget = ConsoleMonitorWidget(monitor)
        widget.start_widget()
        return widget
    return None

def get_server_status() -> Dict:
    """서버 상태 조회"""
    monitor = get_server_monitor()
    return monitor.get_status_summary()

if __name__ == "__main__":
    # 테스트 코드
    print("Server Monitor 테스트 시작")
    
    # 모니터링 시작
    monitor = ServerMonitor()
    monitor.start_monitoring(2)
    
    # 위젯 시작
    widget = ConsoleMonitorWidget(monitor)
    widget.start_widget(1)
    
    try:
        # 30초 동안 실행
        time.sleep(30)
    except KeyboardInterrupt:
        print("\n모니터링 중지")
    finally:
        widget.stop_widget()
        monitor.stop_monitoring()
        print("\n테스트 완료")