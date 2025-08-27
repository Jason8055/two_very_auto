#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 통합 모니터링 관리자
모든 모니터링 컴포넌트를 통합 관리하는 중앙 시스템
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 모니터링 모듈들
from prometheus_metrics import get_metrics, PrometheusMetrics, MetricsServer
from elk_logger import get_logging_manager, get_logger, StructuredLogger, LogCategory
from alerting_system import get_alerting_system, AlertingSystem, Alert, AlertSeverity, AlertStatus
from grafana_dashboards import GrafanaDashboardManager, setup_grafana_dashboards

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


class MonitoringComponent(Enum):
    """모니터링 컴포넌트"""
    PROMETHEUS = "prometheus"
    ELASTICSEARCH = "elasticsearch"
    GRAFANA = "grafana"
    ALERTMANAGER = "alertmanager"
    METRICS_SERVER = "metrics_server"


class HealthStatus(Enum):
    """헬스 상태"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """컴포넌트 헬스 상태"""
    component: MonitoringComponent
    status: HealthStatus
    message: str
    last_check: datetime
    details: Optional[Dict[str, Any]] = None


@dataclass
class SystemMetrics:
    """시스템 메트릭 요약"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_rx: float
    network_tx: float
    active_connections: int
    response_time_p95: float
    error_rate: float
    timestamp: datetime


class MonitoringManager:
    """통합 모니터링 관리자"""
    
    def __init__(self, 
                 config_file: Path = Path("monitoring_config.json")):
        self.config_file = config_file
        self.config = self._load_config()
        
        # 컴포넌트 초기화
        self.metrics = get_metrics()
        self.logger = get_logger("monitoring_manager")
        self.alerting = get_alerting_system()
        
        # 상태 관리
        self.component_health: Dict[MonitoringComponent, ComponentHealth] = {}
        self.system_metrics_history: List[SystemMetrics] = []
        self.max_metrics_history = 1000
        
        # 서비스 인스턴스들
        self.metrics_server: Optional[MetricsServer] = None
        self.grafana_manager: Optional[GrafanaDashboardManager] = None
        
        # 모니터링 스레드
        self.monitoring_threads: List[threading.Thread] = []
        self.running = False
        
        # 컴포넌트별 설정
        self.health_check_interval = self.config.get("health_check_interval", 60)  # 1분
        self.metrics_collection_interval = self.config.get("metrics_collection_interval", 30)  # 30초
        
        safe_print("📊 통합 모니터링 관리자 초기화 완료")
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        default_config = {
            "prometheus": {
                "enabled": True,
                "url": "http://localhost:9090",
                "metrics_port": 8000
            },
            "elasticsearch": {
                "enabled": True,
                "hosts": ["http://localhost:9200"],
                "index_prefix": "two-very-auto"
            },
            "grafana": {
                "enabled": True,
                "url": "http://localhost:3000",
                "username": "admin",
                "password": "admin"
            },
            "alertmanager": {
                "enabled": True,
                "url": "http://localhost:9093",
                "webhook_port": 9094
            },
            "health_check_interval": 60,
            "metrics_collection_interval": 30,
            "retention": {
                "metrics_hours": 24,
                "logs_days": 7,
                "alerts_days": 30
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # 기본 설정과 병합
                default_config.update(user_config)
                
            except Exception as e:
                logger.error(f"설정 파일 로드 실패: {e}")
        
        return default_config
    
    def _save_config(self):
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
    
    def start(self):
        """모니터링 시스템 시작"""
        if self.running:
            safe_print("⚠️ 모니터링 시스템이 이미 실행 중입니다")
            return
        
        self.running = True
        safe_print("🚀 모니터링 시스템 시작")
        
        # 1. 메트릭 수집 시스템 시작
        if self.config["prometheus"]["enabled"]:
            self._start_metrics_collection()
        
        # 2. 로깅 시스템 시작 (이미 초기화됨)
        self.logger.info("모니터링 시스템 시작", LogCategory.SYSTEM)
        
        # 3. 알림 시스템 설정
        if self.config["alertmanager"]["enabled"]:
            self.alerting.setup()
        
        # 4. Grafana 대시보드 설정 (선택사항)
        if self.config["grafana"]["enabled"]:
            self._setup_grafana()
        
        # 5. 헬스 체크 시작
        self._start_health_checks()
        
        # 6. 시스템 메트릭 수집 시작
        self._start_system_metrics_collection()
        
        # 7. 메트릭 서버 시작
        self._start_metrics_server()
        
        safe_print("✅ 모니터링 시스템 시작 완료")
    
    def stop(self):
        """모니터링 시스템 중지"""
        if not self.running:
            return
        
        self.running = False
        safe_print("🛑 모니터링 시스템 중지")
        
        # 스레드 정리
        for thread in self.monitoring_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        # 메트릭 수집 중지
        self.metrics.stop_system_collection()
        
        # 알림 시스템 종료
        self.alerting.shutdown()
        
        # 로깅 시스템 종료
        get_logging_manager().shutdown()
        
        self.logger.info("모니터링 시스템 중지", LogCategory.SYSTEM)
        
        safe_print("✅ 모니터링 시스템 중지 완료")
    
    def _start_metrics_collection(self):
        """메트릭 수집 시작"""
        self.metrics.start_system_collection(
            interval=self.config.get("metrics_collection_interval", 30)
        )
        safe_print("📈 시스템 메트릭 수집 시작")
    
    def _start_metrics_server(self):
        """메트릭 서버 시작"""
        def run_server():
            try:
                self.metrics_server = MetricsServer(
                    self.metrics, 
                    port=self.config["prometheus"]["metrics_port"]
                )
                self.metrics_server.start(debug=False)
            except Exception as e:
                logger.error(f"메트릭 서버 시작 실패: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        self.monitoring_threads.append(server_thread)
        
        safe_print(f"📊 메트릭 서버 시작: 포트 {self.config['prometheus']['metrics_port']}")
    
    def _setup_grafana(self):
        """Grafana 설정"""
        try:
            grafana_config = self.config["grafana"]
            self.grafana_manager = GrafanaDashboardManager(
                grafana_url=grafana_config["url"],
                username=grafana_config.get("username", "admin"),
                password=grafana_config.get("password", "admin")
            )
            
            # 대시보드 설정은 별도 스레드에서
            def setup_dashboards():
                setup_grafana_dashboards(
                    grafana_url=grafana_config["url"],
                    api_key=grafana_config.get("api_key")
                )
            
            dashboard_thread = threading.Thread(target=setup_dashboards, daemon=True)
            dashboard_thread.start()
            self.monitoring_threads.append(dashboard_thread)
            
        except Exception as e:
            logger.error(f"Grafana 설정 실패: {e}")
    
    def _start_health_checks(self):
        """헬스 체크 시작"""
        def health_check_loop():
            while self.running:
                try:
                    self._perform_health_checks()
                except Exception as e:
                    logger.error(f"헬스 체크 오류: {e}")
                
                time.sleep(self.health_check_interval)
        
        health_thread = threading.Thread(target=health_check_loop, daemon=True)
        health_thread.start()
        self.monitoring_threads.append(health_thread)
        
        safe_print("🩺 헬스 체크 시작")
    
    def _start_system_metrics_collection(self):
        """시스템 메트릭 수집 시작"""
        def metrics_collection_loop():
            while self.running:
                try:
                    self._collect_system_metrics()
                except Exception as e:
                    logger.error(f"시스템 메트릭 수집 오류: {e}")
                
                time.sleep(self.metrics_collection_interval)
        
        metrics_thread = threading.Thread(target=metrics_collection_loop, daemon=True)
        metrics_thread.start()
        self.monitoring_threads.append(metrics_thread)
        
        safe_print("📊 시스템 메트릭 수집 시작")
    
    def _perform_health_checks(self):
        """헬스 체크 수행"""
        components_to_check = [
            (MonitoringComponent.PROMETHEUS, self._check_prometheus_health),
            (MonitoringComponent.ELASTICSEARCH, self._check_elasticsearch_health),
            (MonitoringComponent.GRAFANA, self._check_grafana_health),
            (MonitoringComponent.METRICS_SERVER, self._check_metrics_server_health),
        ]
        
        for component, check_func in components_to_check:
            try:
                health = check_func()
                self.component_health[component] = health
                
                # 상태 변화 시 로깅
                if health.status != HealthStatus.HEALTHY:
                    self.logger.warning(f"{component.value} 헬스 체크 이상", 
                                      LogCategory.SYSTEM,
                                      component=component.value,
                                      status=health.status.value,
                                      message=health.message)
                
            except Exception as e:
                health = ComponentHealth(
                    component=component,
                    status=HealthStatus.UNKNOWN,
                    message=f"헬스 체크 실패: {e}",
                    last_check=datetime.now()
                )
                self.component_health[component] = health
    
    def _check_prometheus_health(self) -> ComponentHealth:
        """Prometheus 헬스 체크"""
        try:
            import requests
            response = requests.get(
                f"{self.config['prometheus']['url']}/api/v1/query?query=up",
                timeout=5
            )
            
            if response.status_code == 200:
                return ComponentHealth(
                    component=MonitoringComponent.PROMETHEUS,
                    status=HealthStatus.HEALTHY,
                    message="Prometheus 정상 작동",
                    last_check=datetime.now(),
                    details={"targets": len(response.json().get("data", {}).get("result", []))}
                )
            else:
                return ComponentHealth(
                    component=MonitoringComponent.PROMETHEUS,
                    status=HealthStatus.CRITICAL,
                    message=f"HTTP {response.status_code}",
                    last_check=datetime.now()
                )
        except Exception as e:
            return ComponentHealth(
                component=MonitoringComponent.PROMETHEUS,
                status=HealthStatus.CRITICAL,
                message=f"연결 실패: {e}",
                last_check=datetime.now()
            )
    
    def _check_elasticsearch_health(self) -> ComponentHealth:
        """Elasticsearch 헬스 체크"""
        try:
            import requests
            response = requests.get(
                f"{self.config['elasticsearch']['hosts'][0]}/_cluster/health",
                timeout=5
            )
            
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status", "unknown")
                
                if status == "green":
                    health_status = HealthStatus.HEALTHY
                elif status == "yellow":
                    health_status = HealthStatus.WARNING
                else:
                    health_status = HealthStatus.CRITICAL
                
                return ComponentHealth(
                    component=MonitoringComponent.ELASTICSEARCH,
                    status=health_status,
                    message=f"클러스터 상태: {status}",
                    last_check=datetime.now(),
                    details={
                        "nodes": health_data.get("number_of_nodes", 0),
                        "shards": health_data.get("active_shards", 0)
                    }
                )
            else:
                return ComponentHealth(
                    component=MonitoringComponent.ELASTICSEARCH,
                    status=HealthStatus.CRITICAL,
                    message=f"HTTP {response.status_code}",
                    last_check=datetime.now()
                )
        except Exception as e:
            return ComponentHealth(
                component=MonitoringComponent.ELASTICSEARCH,
                status=HealthStatus.CRITICAL,
                message=f"연결 실패: {e}",
                last_check=datetime.now()
            )
    
    def _check_grafana_health(self) -> ComponentHealth:
        """Grafana 헬스 체크"""
        try:
            import requests
            response = requests.get(
                f"{self.config['grafana']['url']}/api/health",
                timeout=5
            )
            
            if response.status_code == 200:
                return ComponentHealth(
                    component=MonitoringComponent.GRAFANA,
                    status=HealthStatus.HEALTHY,
                    message="Grafana 정상 작동",
                    last_check=datetime.now()
                )
            else:
                return ComponentHealth(
                    component=MonitoringComponent.GRAFANA,
                    status=HealthStatus.CRITICAL,
                    message=f"HTTP {response.status_code}",
                    last_check=datetime.now()
                )
        except Exception as e:
            return ComponentHealth(
                component=MonitoringComponent.GRAFANA,
                status=HealthStatus.CRITICAL,
                message=f"연결 실패: {e}",
                last_check=datetime.now()
            )
    
    def _check_metrics_server_health(self) -> ComponentHealth:
        """메트릭 서버 헬스 체크"""
        try:
            import requests
            response = requests.get(
                f"http://localhost:{self.config['prometheus']['metrics_port']}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                return ComponentHealth(
                    component=MonitoringComponent.METRICS_SERVER,
                    status=HealthStatus.HEALTHY,
                    message="메트릭 서버 정상 작동",
                    last_check=datetime.now()
                )
            else:
                return ComponentHealth(
                    component=MonitoringComponent.METRICS_SERVER,
                    status=HealthStatus.CRITICAL,
                    message=f"HTTP {response.status_code}",
                    last_check=datetime.now()
                )
        except Exception as e:
            return ComponentHealth(
                component=MonitoringComponent.METRICS_SERVER,
                status=HealthStatus.CRITICAL,
                message=f"연결 실패: {e}",
                last_check=datetime.now()
            )
    
    def _collect_system_metrics(self):
        """시스템 메트릭 수집"""
        try:
            import psutil
            
            # CPU 사용률
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 디스크 사용률
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # 네트워크 I/O
            net_io = psutil.net_io_counters()
            
            # 시스템 메트릭 객체 생성
            metrics = SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_rx=net_io.bytes_recv,
                network_tx=net_io.bytes_sent,
                active_connections=len(psutil.net_connections()),
                response_time_p95=0.0,  # 실제 구현에서는 애플리케이션 메트릭에서 가져옴
                error_rate=0.0,  # 실제 구현에서는 애플리케이션 메트릭에서 가져옴
                timestamp=datetime.now()
            )
            
            # 히스토리에 추가
            self.system_metrics_history.append(metrics)
            if len(self.system_metrics_history) > self.max_metrics_history:
                self.system_metrics_history = self.system_metrics_history[-self.max_metrics_history:]
            
            # Prometheus 메트릭으로도 기록
            self.metrics.set_gauge("system_cpu_usage_percent", cpu_usage, {"cpu_id": "all"})
            self.metrics.set_gauge("system_memory_usage_percent", memory_usage)
            self.metrics.set_gauge("system_disk_usage_percent", disk_usage)
            
            # 로깅
            self.logger.system_metric("system_overview", {
                "cpu": cpu_usage,
                "memory": memory_usage,
                "disk": disk_usage
            })
            
        except Exception as e:
            logger.error(f"시스템 메트릭 수집 실패: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 전체 상태 조회"""
        # 최신 시스템 메트릭
        latest_metrics = self.system_metrics_history[-1] if self.system_metrics_history else None
        
        # 컴포넌트 헬스 상태 요약
        component_status = {}
        overall_health = HealthStatus.HEALTHY
        
        for component, health in self.component_health.items():
            component_status[component.value] = {
                "status": health.status.value,
                "message": health.message,
                "last_check": health.last_check.isoformat(),
                "details": health.details
            }
            
            # 전체 헬스 상태 결정 (가장 심각한 상태로)
            if health.status == HealthStatus.CRITICAL:
                overall_health = HealthStatus.CRITICAL
            elif health.status == HealthStatus.WARNING and overall_health == HealthStatus.HEALTHY:
                overall_health = HealthStatus.WARNING
        
        return {
            "overall_health": overall_health.value,
            "timestamp": datetime.now().isoformat(),
            "system_metrics": asdict(latest_metrics) if latest_metrics else None,
            "components": component_status,
            "uptime": self._get_uptime(),
            "monitoring_config": {
                "metrics_enabled": self.config["prometheus"]["enabled"],
                "logging_enabled": self.config["elasticsearch"]["enabled"],
                "alerting_enabled": self.config["alertmanager"]["enabled"],
                "dashboards_enabled": self.config["grafana"]["enabled"]
            }
        }
    
    def _get_uptime(self) -> Dict[str, Any]:
        """시스템 업타임 조회"""
        try:
            import psutil
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            return {
                "boot_time": boot_time.isoformat(),
                "uptime_seconds": int(uptime.total_seconds()),
                "uptime_formatted": str(uptime)
            }
        except Exception:
            return {"error": "업타임 조회 실패"}
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """메트릭 요약 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.system_metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": "데이터 없음"}
        
        # 통계 계산
        cpu_values = [m.cpu_usage for m in recent_metrics]
        memory_values = [m.memory_usage for m in recent_metrics]
        disk_values = [m.disk_usage for m in recent_metrics]
        
        return {
            "period_hours": hours,
            "data_points": len(recent_metrics),
            "cpu_usage": {
                "current": cpu_values[-1],
                "average": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory_usage": {
                "current": memory_values[-1],
                "average": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values)
            },
            "disk_usage": {
                "current": disk_values[-1],
                "average": sum(disk_values) / len(disk_values),
                "max": max(disk_values),
                "min": min(disk_values)
            }
        }
    
    def trigger_test_alert(self):
        """테스트 알림 발생"""
        self.alerting.send_test_alert()
        safe_print("📨 테스트 알림 발생")
    
    def export_monitoring_config(self, output_path: Path):
        """모니터링 설정 내보내기"""
        export_data = {
            "config": self.config,
            "component_health": {
                k.value: asdict(v) for k, v in self.component_health.items()
            },
            "system_status": self.get_system_status(),
            "export_timestamp": datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        safe_print(f"📤 모니터링 설정 내보내기: {output_path}")


# 전역 모니터링 관리자 인스턴스
_monitoring_manager = None

def get_monitoring_manager() -> MonitoringManager:
    """모니터링 관리자 인스턴스 반환"""
    global _monitoring_manager
    if _monitoring_manager is None:
        _monitoring_manager = MonitoringManager()
    return _monitoring_manager


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 통합 모니터링 관리자 테스트 ===")
    
    manager = get_monitoring_manager()
    
    try:
        # 모니터링 시스템 시작
        manager.start()
        
        # 상태 확인
        time.sleep(10)
        status = manager.get_system_status()
        safe_print(f"📊 시스템 상태: {status['overall_health']}")
        
        # 메트릭 요약
        metrics_summary = manager.get_metrics_summary()
        safe_print(f"📈 메트릭 요약: {metrics_summary.get('data_points', 0)}개 데이터 포인트")
        
        # 테스트 알림
        manager.trigger_test_alert()
        
        # 설정 내보내기
        manager.export_monitoring_config(Path("monitoring_export.json"))
        
        # 잠시 실행
        time.sleep(30)
        
    finally:
        manager.stop()
    
    safe_print("🏁 통합 모니터링 관리자 테스트 완료")