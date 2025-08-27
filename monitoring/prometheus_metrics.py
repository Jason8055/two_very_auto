#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - Prometheus 메트릭 수집 시스템
애플리케이션 성능 및 비즈니스 메트릭 수집
"""

import time
import psutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
from threading import Thread, Lock
import sqlite3

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest
    from prometheus_client.multiprocess import MultiProcessCollector
    from flask import Flask, Response
    PROMETHEUS_AVAILABLE = True
    safe_print("✅ Prometheus 클라이언트 사용 가능")
except ImportError:
    PROMETHEUS_AVAILABLE = False
    safe_print("⚠️ prometheus_client 라이브러리 미설치. pip install prometheus_client 실행 필요")


class MetricType(Enum):
    """메트릭 타입"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricDefinition:
    """메트릭 정의"""
    name: str
    metric_type: MetricType
    description: str
    labels: List[str]
    namespace: str = "two_very_auto"


class PrometheusMetrics:
    """Prometheus 메트릭 관리자"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.metrics: Dict[str, Any] = {}
        self.lock = Lock()
        
        # 애플리케이션 메트릭 정의
        self.metric_definitions = self._define_metrics()
        
        # 메트릭 초기화
        self._initialize_metrics()
        
        # 시스템 메트릭 수집 스레드
        self.system_collector_thread = None
        self.running = False
        
        safe_print("📊 Prometheus 메트릭 시스템 초기화 완료")
    
    def _define_metrics(self) -> List[MetricDefinition]:
        """메트릭 정의"""
        return [
            # HTTP 메트릭
            MetricDefinition(
                name="http_requests_total",
                metric_type=MetricType.COUNTER,
                description="Total HTTP requests",
                labels=["method", "endpoint", "status"]
            ),
            MetricDefinition(
                name="http_request_duration_seconds",
                metric_type=MetricType.HISTOGRAM,
                description="HTTP request duration in seconds",
                labels=["method", "endpoint"]
            ),
            MetricDefinition(
                name="http_requests_in_progress",
                metric_type=MetricType.GAUGE,
                description="Current HTTP requests in progress",
                labels=["method", "endpoint"]
            ),
            
            # 바카라 게임 메트릭
            MetricDefinition(
                name="baccarat_games_total",
                metric_type=MetricType.COUNTER,
                description="Total baccarat games played",
                labels=["outcome", "bet_type"]
            ),
            MetricDefinition(
                name="baccarat_bet_amount_total",
                metric_type=MetricType.COUNTER,
                description="Total bet amount in baccarat games",
                labels=["bet_type", "outcome"]
            ),
            MetricDefinition(
                name="baccarat_active_sessions",
                metric_type=MetricType.GAUGE,
                description="Current active baccarat sessions",
                labels=["session_type"]
            ),
            MetricDefinition(
                name="baccarat_prediction_accuracy",
                metric_type=MetricType.GAUGE,
                description="AI prediction accuracy rate",
                labels=["model_version", "prediction_type"]
            ),
            
            # WebSocket 메트릭
            MetricDefinition(
                name="websocket_connections_active",
                metric_type=MetricType.GAUGE,
                description="Current active WebSocket connections",
                labels=["room"]
            ),
            MetricDefinition(
                name="websocket_messages_total",
                metric_type=MetricType.COUNTER,
                description="Total WebSocket messages",
                labels=["direction", "event_type"]
            ),
            MetricDefinition(
                name="websocket_connection_duration_seconds",
                metric_type=MetricType.HISTOGRAM,
                description="WebSocket connection duration in seconds",
                labels=["disconnect_reason"]
            ),
            
            # AI 엔진 메트릭
            MetricDefinition(
                name="ai_predictions_total",
                metric_type=MetricType.COUNTER,
                description="Total AI predictions made",
                labels=["model_type", "confidence_level"]
            ),
            MetricDefinition(
                name="ai_model_inference_duration_seconds",
                metric_type=MetricType.HISTOGRAM,
                description="AI model inference time in seconds",
                labels=["model_type"]
            ),
            MetricDefinition(
                name="ai_model_accuracy",
                metric_type=MetricType.GAUGE,
                description="Current AI model accuracy",
                labels=["model_type", "time_window"]
            ),
            
            # 시스템 메트릭
            MetricDefinition(
                name="system_cpu_usage_percent",
                metric_type=MetricType.GAUGE,
                description="System CPU usage percentage",
                labels=["cpu_id"]
            ),
            MetricDefinition(
                name="system_memory_usage_bytes",
                metric_type=MetricType.GAUGE,
                description="System memory usage in bytes",
                labels=["memory_type"]
            ),
            MetricDefinition(
                name="system_disk_usage_bytes",
                metric_type=MetricType.GAUGE,
                description="System disk usage in bytes",
                labels=["device", "mountpoint"]
            ),
            
            # 데이터베이스 메트릭
            MetricDefinition(
                name="database_queries_total",
                metric_type=MetricType.COUNTER,
                description="Total database queries",
                labels=["operation", "table", "status"]
            ),
            MetricDefinition(
                name="database_query_duration_seconds",
                metric_type=MetricType.HISTOGRAM,
                description="Database query duration in seconds",
                labels=["operation", "table"]
            ),
            MetricDefinition(
                name="database_connections_active",
                metric_type=MetricType.GAUGE,
                description="Active database connections",
                labels=["database"]
            ),
        ]
    
    def _initialize_metrics(self):
        """메트릭 초기화"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        for metric_def in self.metric_definitions:
            metric_name = f"{metric_def.namespace}_{metric_def.name}"
            
            if metric_def.metric_type == MetricType.COUNTER:
                self.metrics[metric_def.name] = Counter(
                    metric_name, metric_def.description, metric_def.labels, registry=self.registry
                )
            elif metric_def.metric_type == MetricType.GAUGE:
                self.metrics[metric_def.name] = Gauge(
                    metric_name, metric_def.description, metric_def.labels, registry=self.registry
                )
            elif metric_def.metric_type == MetricType.HISTOGRAM:
                self.metrics[metric_def.name] = Histogram(
                    metric_name, metric_def.description, metric_def.labels, registry=self.registry
                )
            elif metric_def.metric_type == MetricType.SUMMARY:
                self.metrics[metric_def.name] = Summary(
                    metric_name, metric_def.description, metric_def.labels, registry=self.registry
                )
    
    def increment_counter(self, metric_name: str, labels: Optional[Dict[str, str]] = None, value: float = 1):
        """카운터 증가"""
        if not PROMETHEUS_AVAILABLE or metric_name not in self.metrics:
            return
        
        with self.lock:
            if labels:
                self.metrics[metric_name].labels(**labels).inc(value)
            else:
                self.metrics[metric_name].inc(value)
    
    def set_gauge(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """게이지 값 설정"""
        if not PROMETHEUS_AVAILABLE or metric_name not in self.metrics:
            return
        
        with self.lock:
            if labels:
                self.metrics[metric_name].labels(**labels).set(value)
            else:
                self.metrics[metric_name].set(value)
    
    def observe_histogram(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """히스토그램 관측값 추가"""
        if not PROMETHEUS_AVAILABLE or metric_name not in self.metrics:
            return
        
        with self.lock:
            if labels:
                self.metrics[metric_name].labels(**labels).observe(value)
            else:
                self.metrics[metric_name].observe(value)
    
    def time_function(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        """함수 실행 시간 측정 데코레이터"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.observe_histogram(metric_name, duration, labels)
            return wrapper
        return decorator
    
    def start_system_collection(self, interval: int = 10):
        """시스템 메트릭 수집 시작"""
        if self.system_collector_thread and self.system_collector_thread.is_alive():
            return
        
        self.running = True
        self.system_collector_thread = Thread(target=self._collect_system_metrics, args=(interval,))
        self.system_collector_thread.daemon = True
        self.system_collector_thread.start()
        
        safe_print(f"📈 시스템 메트릭 수집 시작 (간격: {interval}초)")
    
    def stop_system_collection(self):
        """시스템 메트릭 수집 중지"""
        self.running = False
        if self.system_collector_thread:
            self.system_collector_thread.join(timeout=5)
        safe_print("🛑 시스템 메트릭 수집 중지")
    
    def _collect_system_metrics(self, interval: int):
        """시스템 메트릭 수집 루프"""
        while self.running:
            try:
                # CPU 사용률
                cpu_percent = psutil.cpu_percent(interval=None, percpu=True)
                for i, percent in enumerate(cpu_percent):
                    self.set_gauge("system_cpu_usage_percent", percent, {"cpu_id": str(i)})
                
                # 메모리 사용률
                memory = psutil.virtual_memory()
                self.set_gauge("system_memory_usage_bytes", memory.used, {"memory_type": "used"})
                self.set_gauge("system_memory_usage_bytes", memory.available, {"memory_type": "available"})
                self.set_gauge("system_memory_usage_bytes", memory.total, {"memory_type": "total"})
                
                # 디스크 사용률
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        labels = {"device": partition.device, "mountpoint": partition.mountpoint}
                        self.set_gauge("system_disk_usage_bytes", usage.used, {**labels, "usage_type": "used"})
                        self.set_gauge("system_disk_usage_bytes", usage.free, {**labels, "usage_type": "free"})
                        self.set_gauge("system_disk_usage_bytes", usage.total, {**labels, "usage_type": "total"})
                    except PermissionError:
                        continue
                
                # 네트워크 통계
                net_io = psutil.net_io_counters()
                self.set_gauge("system_network_bytes_total", net_io.bytes_sent, {"direction": "sent"})
                self.set_gauge("system_network_bytes_total", net_io.bytes_recv, {"direction": "received"})
                
            except Exception as e:
                logger.error(f"시스템 메트릭 수집 오류: {e}")
            
            time.sleep(interval)
    
    def get_metrics_text(self) -> str:
        """메트릭을 Prometheus 텍스트 형식으로 반환"""
        if not PROMETHEUS_AVAILABLE:
            return "# Prometheus client not available\n"
        
        return generate_latest(self.registry).decode('utf-8')
    
    def record_baccarat_game(self, outcome: str, bet_type: str, bet_amount: float, 
                           prediction_correct: bool, model_version: str):
        """바카라 게임 결과 기록"""
        # 게임 수 카운터
        self.increment_counter("baccarat_games_total", {
            "outcome": outcome,
            "bet_type": bet_type
        })
        
        # 베팅 금액
        self.increment_counter("baccarat_bet_amount_total", {
            "bet_type": bet_type,
            "outcome": outcome
        }, bet_amount)
        
        # 예측 정확도 (간단한 구현)
        current_accuracy = self._calculate_prediction_accuracy(model_version)
        self.set_gauge("baccarat_prediction_accuracy", current_accuracy, {
            "model_version": model_version,
            "prediction_type": "outcome"
        })
    
    def _calculate_prediction_accuracy(self, model_version: str) -> float:
        """예측 정확도 계산 (실제 구현에서는 더 정교한 로직 필요)"""
        # 여기서는 간단한 예시, 실제로는 데이터베이스에서 최근 N개의 예측 결과를 조회
        return 0.75  # 75% 예시 정확도
    
    def record_websocket_connection(self, room: str, connected: bool):
        """WebSocket 연결 상태 기록"""
        current_count = getattr(self, f"_ws_count_{room}", 0)
        if connected:
            current_count += 1
        else:
            current_count = max(0, current_count - 1)
        
        setattr(self, f"_ws_count_{room}", current_count)
        self.set_gauge("websocket_connections_active", current_count, {"room": room})
    
    def record_websocket_message(self, direction: str, event_type: str):
        """WebSocket 메시지 기록"""
        self.increment_counter("websocket_messages_total", {
            "direction": direction,
            "event_type": event_type
        })
    
    def record_ai_prediction(self, model_type: str, confidence: float, inference_time: float):
        """AI 예측 기록"""
        confidence_level = "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low"
        
        self.increment_counter("ai_predictions_total", {
            "model_type": model_type,
            "confidence_level": confidence_level
        })
        
        self.observe_histogram("ai_model_inference_duration_seconds", inference_time, {
            "model_type": model_type
        })


class MetricsServer:
    """메트릭 서버"""
    
    def __init__(self, metrics: PrometheusMetrics, port: int = 8000):
        self.metrics = metrics
        self.port = port
        self.app = Flask(__name__)
        
        # 메트릭 엔드포인트 설정
        @self.app.route('/metrics')
        def metrics_endpoint():
            return Response(
                self.metrics.get_metrics_text(),
                mimetype='text/plain; version=0.0.4; charset=utf-8'
            )
        
        @self.app.route('/health')
        def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    def start(self, debug: bool = False):
        """메트릭 서버 시작"""
        safe_print(f"📊 메트릭 서버 시작: http://localhost:{self.port}/metrics")
        self.app.run(host='0.0.0.0', port=self.port, debug=debug)


# 전역 메트릭 인스턴스
_metrics_instance = None

def get_metrics() -> PrometheusMetrics:
    """메트릭 인스턴스 반환"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PrometheusMetrics()
    return _metrics_instance


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== Prometheus 메트릭 시스템 테스트 ===")
    
    metrics = get_metrics()
    
    # 시스템 메트릭 수집 시작
    metrics.start_system_collection(interval=5)
    
    # 테스트 메트릭 생성
    metrics.increment_counter("http_requests_total", {
        "method": "GET",
        "endpoint": "/api/status",
        "status": "200"
    })
    
    metrics.observe_histogram("http_request_duration_seconds", 0.123, {
        "method": "GET",
        "endpoint": "/api/status"
    })
    
    metrics.record_baccarat_game("player", "player", 100.0, True, "v1.0")
    metrics.record_ai_prediction("lstm", 0.85, 0.045)
    
    # 메트릭 출력
    safe_print("📊 생성된 메트릭:")
    print(metrics.get_metrics_text())
    
    # 메트릭 서버 시작 (테스트 시에는 주석 처리)
    # server = MetricsServer(metrics)
    # server.start()
    
    time.sleep(10)
    metrics.stop_system_collection()
    
    safe_print("🏁 Prometheus 메트릭 시스템 테스트 완료")