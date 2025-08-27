#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - Grafana 대시보드 관리자
대시보드 자동 생성 및 관리 시스템
"""

import json
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


class PanelType(Enum):
    """패널 타입"""
    GRAPH = "graph"
    STAT = "stat"
    TABLE = "table"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    BAR_GAUGE = "bargauge"
    LOGS = "logs"
    TEXT = "text"


class DataSourceType(Enum):
    """데이터 소스 타입"""
    PROMETHEUS = "prometheus"
    ELASTICSEARCH = "elasticsearch"
    MYSQL = "mysql"
    POSTGRES = "postgres"


@dataclass
class PanelConfig:
    """패널 설정"""
    title: str
    panel_type: PanelType
    query: str
    datasource: str
    x: int = 0
    y: int = 0
    width: int = 12
    height: int = 8
    unit: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    thresholds: Optional[List[Dict[str, Any]]] = None


@dataclass
class DashboardConfig:
    """대시보드 설정"""
    title: str
    tags: List[str]
    panels: List[PanelConfig]
    refresh_interval: str = "30s"
    time_range: str = "1h"


class GrafanaDashboardManager:
    """Grafana 대시보드 관리자"""
    
    def __init__(self, 
                 grafana_url: str = "http://localhost:3000",
                 api_key: Optional[str] = None,
                 username: str = "admin",
                 password: str = "admin"):
        self.grafana_url = grafana_url.rstrip('/')
        self.api_key = api_key
        self.username = username
        self.password = password
        
        # 세션 설정
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        else:
            self.session.auth = (username, password)
        
        # 대시보드 템플릿
        self.dashboard_templates = self._create_dashboard_templates()
        
        safe_print("📊 Grafana 대시보드 관리자 초기화 완료")
    
    def _create_dashboard_templates(self) -> Dict[str, DashboardConfig]:
        """대시보드 템플릿 생성"""
        return {
            "system_overview": self._create_system_overview_dashboard(),
            "application_performance": self._create_application_performance_dashboard(),
            "baccarat_business": self._create_baccarat_business_dashboard(),
            "security_monitoring": self._create_security_monitoring_dashboard(),
            "infrastructure": self._create_infrastructure_dashboard()
        }
    
    def _create_system_overview_dashboard(self) -> DashboardConfig:
        """시스템 개요 대시보드"""
        panels = [
            # CPU 사용률
            PanelConfig(
                title="CPU 사용률",
                panel_type=PanelType.GRAPH,
                query='avg(two_very_auto_system_cpu_usage_percent) by (cpu_id)',
                datasource="prometheus",
                x=0, y=0, width=12, height=8,
                unit="percent",
                max_value=100
            ),
            
            # 메모리 사용률
            PanelConfig(
                title="메모리 사용률",
                panel_type=PanelType.GRAPH,
                query='two_very_auto_system_memory_usage_bytes{memory_type="used"} / two_very_auto_system_memory_usage_bytes{memory_type="total"} * 100',
                datasource="prometheus",
                x=0, y=8, width=12, height=8,
                unit="percent",
                max_value=100
            ),
            
            # 디스크 사용률
            PanelConfig(
                title="디스크 사용률",
                panel_type=PanelType.BAR_GAUGE,
                query='two_very_auto_system_disk_usage_bytes{usage_type="used"} / two_very_auto_system_disk_usage_bytes{usage_type="total"} * 100',
                datasource="prometheus",
                x=0, y=16, width=12, height=8,
                unit="percent",
                max_value=100
            ),
            
            # 네트워크 트래픽
            PanelConfig(
                title="네트워크 트래픽",
                panel_type=PanelType.GRAPH,
                query='rate(two_very_auto_system_network_bytes_total[5m])',
                datasource="prometheus",
                x=0, y=24, width=12, height=8,
                unit="Bps"
            )
        ]
        
        return DashboardConfig(
            title="시스템 개요",
            tags=["system", "overview"],
            panels=panels
        )
    
    def _create_application_performance_dashboard(self) -> DashboardConfig:
        """애플리케이션 성능 대시보드"""
        panels = [
            # HTTP 요청 수
            PanelConfig(
                title="HTTP 요청/초",
                panel_type=PanelType.GRAPH,
                query='rate(two_very_auto_http_requests_total[5m])',
                datasource="prometheus",
                x=0, y=0, width=12, height=8,
                unit="reqps"
            ),
            
            # HTTP 응답 시간
            PanelConfig(
                title="HTTP 응답 시간",
                panel_type=PanelType.GRAPH,
                query='histogram_quantile(0.95, rate(two_very_auto_http_request_duration_seconds_bucket[5m]))',
                datasource="prometheus",
                x=0, y=8, width=12, height=8,
                unit="s"
            ),
            
            # 활성 WebSocket 연결
            PanelConfig(
                title="활성 WebSocket 연결",
                panel_type=PanelType.STAT,
                query='two_very_auto_websocket_connections_active',
                datasource="prometheus",
                x=0, y=16, width=6, height=8
            ),
            
            # AI 예측 처리 시간
            PanelConfig(
                title="AI 모델 추론 시간",
                panel_type=PanelType.GRAPH,
                query='histogram_quantile(0.95, rate(two_very_auto_ai_model_inference_duration_seconds_bucket[5m]))',
                datasource="prometheus",
                x=6, y=16, width=6, height=8,
                unit="s"
            ),
            
            # 데이터베이스 쿼리 시간
            PanelConfig(
                title="데이터베이스 쿼리 시간",
                panel_type=PanelType.GRAPH,
                query='histogram_quantile(0.95, rate(two_very_auto_database_query_duration_seconds_bucket[5m]))',
                datasource="prometheus",
                x=0, y=24, width=12, height=8,
                unit="s"
            )
        ]
        
        return DashboardConfig(
            title="애플리케이션 성능",
            tags=["application", "performance"],
            panels=panels
        )
    
    def _create_baccarat_business_dashboard(self) -> DashboardConfig:
        """바카라 비즈니스 대시보드"""
        panels = [
            # 게임 수
            PanelConfig(
                title="시간당 게임 수",
                panel_type=PanelType.GRAPH,
                query='rate(two_very_auto_baccarat_games_total[1h])',
                datasource="prometheus",
                x=0, y=0, width=12, height=8,
                unit="games/h"
            ),
            
            # 결과별 게임 분포
            PanelConfig(
                title="게임 결과 분포",
                panel_type=PanelType.BAR_GAUGE,
                query='sum(two_very_auto_baccarat_games_total) by (outcome)',
                datasource="prometheus",
                x=0, y=8, width=6, height=8
            ),
            
            # AI 예측 정확도
            PanelConfig(
                title="AI 예측 정확도",
                panel_type=PanelType.GAUGE,
                query='two_very_auto_baccarat_prediction_accuracy',
                datasource="prometheus",
                x=6, y=8, width=6, height=8,
                unit="percent",
                min_value=0,
                max_value=100,
                thresholds=[
                    {"color": "red", "value": 50},
                    {"color": "yellow", "value": 70},
                    {"color": "green", "value": 80}
                ]
            ),
            
            # 베팅 금액 트렌드
            PanelConfig(
                title="베팅 금액 트렌드",
                panel_type=PanelType.GRAPH,
                query='rate(two_very_auto_baccarat_bet_amount_total[5m])',
                datasource="prometheus",
                x=0, y=16, width=12, height=8,
                unit="currency"
            ),
            
            # 활성 세션
            PanelConfig(
                title="활성 바카라 세션",
                panel_type=PanelType.STAT,
                query='two_very_auto_baccarat_active_sessions',
                datasource="prometheus",
                x=0, y=24, width=6, height=8
            )
        ]
        
        return DashboardConfig(
            title="바카라 비즈니스 메트릭",
            tags=["business", "baccarat"],
            panels=panels
        )
    
    def _create_security_monitoring_dashboard(self) -> DashboardConfig:
        """보안 모니터링 대시보드"""
        panels = [
            # 보안 이벤트 로그
            PanelConfig(
                title="보안 이벤트",
                panel_type=PanelType.LOGS,
                query='{"query": {"bool": {"must": [{"term": {"category": "security"}}]}}}',
                datasource="elasticsearch",
                x=0, y=0, width=24, height=12
            ),
            
            # 로그인 시도 실패
            PanelConfig(
                title="로그인 실패율",
                panel_type=PanelType.GRAPH,
                query='{"query": {"bool": {"must": [{"term": {"category": "security"}}, {"term": {"metadata.event_type": "login_failed"}}]}}}',
                datasource="elasticsearch",
                x=0, y=12, width=12, height=8
            ),
            
            # 의심스러운 IP
            PanelConfig(
                title="의심스러운 IP 주소",
                panel_type=PanelType.TABLE,
                query='{"query": {"bool": {"must": [{"term": {"category": "security"}}, {"range": {"@timestamp": {"gte": "now-1h"}}}]}}, "aggs": {"suspicious_ips": {"terms": {"field": "metadata.ip_address", "size": 10}}}}',
                datasource="elasticsearch",
                x=12, y=12, width=12, height=8
            )
        ]
        
        return DashboardConfig(
            title="보안 모니터링",
            tags=["security", "monitoring"],
            panels=panels
        )
    
    def _create_infrastructure_dashboard(self) -> DashboardConfig:
        """인프라 대시보드"""
        panels = [
            # Docker 컨테이너 상태
            PanelConfig(
                title="Docker 컨테이너 상태",
                panel_type=PanelType.STAT,
                query='up{job="docker"}',
                datasource="prometheus",
                x=0, y=0, width=6, height=8
            ),
            
            # Redis 연결
            PanelConfig(
                title="Redis 연결 수",
                panel_type=PanelType.GRAPH,
                query='redis_connected_clients',
                datasource="prometheus",
                x=6, y=0, width=6, height=8
            ),
            
            # PostgreSQL 연결
            PanelConfig(
                title="PostgreSQL 연결 수",
                panel_type=PanelType.GRAPH,
                query='pg_stat_activity_count',
                datasource="prometheus",
                x=12, y=0, width=6, height=8
            ),
            
            # Kubernetes 파드 상태
            PanelConfig(
                title="Kubernetes 파드 상태",
                panel_type=PanelType.TABLE,
                query='kube_pod_info',
                datasource="prometheus",
                x=18, y=0, width=6, height=8
            )
        ]
        
        return DashboardConfig(
            title="인프라 모니터링",
            tags=["infrastructure", "kubernetes"],
            panels=panels
        )
    
    def _create_panel_json(self, panel: PanelConfig, panel_id: int) -> Dict[str, Any]:
        """패널 JSON 생성"""
        base_panel = {
            "id": panel_id,
            "title": panel.title,
            "type": panel.panel_type.value,
            "gridPos": {
                "x": panel.x,
                "y": panel.y,
                "w": panel.width,
                "h": panel.height
            },
            "datasource": panel.datasource,
            "targets": [
                {
                    "expr": panel.query if panel.datasource == "prometheus" else "",
                    "query": json.loads(panel.query) if panel.datasource == "elasticsearch" and panel.query.startswith('{') else panel.query,
                    "refId": "A"
                }
            ]
        }
        
        # 패널 타입별 특별 설정
        if panel.panel_type == PanelType.GRAPH:
            base_panel["yAxes"] = [
                {
                    "unit": panel.unit or "short",
                    "min": panel.min_value,
                    "max": panel.max_value
                },
                {
                    "unit": "short"
                }
            ]
        
        elif panel.panel_type == PanelType.STAT:
            base_panel["fieldConfig"] = {
                "defaults": {
                    "unit": panel.unit or "short",
                    "min": panel.min_value,
                    "max": panel.max_value
                }
            }
        
        elif panel.panel_type == PanelType.GAUGE:
            base_panel["fieldConfig"] = {
                "defaults": {
                    "unit": panel.unit or "short",
                    "min": panel.min_value or 0,
                    "max": panel.max_value or 100,
                    "thresholds": {
                        "steps": panel.thresholds or [
                            {"color": "green", "value": None},
                            {"color": "red", "value": 80}
                        ]
                    }
                }
            }
        
        return base_panel
    
    def _create_dashboard_json(self, config: DashboardConfig) -> Dict[str, Any]:
        """대시보드 JSON 생성"""
        panels = []
        for i, panel in enumerate(config.panels):
            panels.append(self._create_panel_json(panel, i + 1))
        
        return {
            "dashboard": {
                "title": config.title,
                "tags": config.tags,
                "timezone": "Asia/Seoul",
                "refresh": config.refresh_interval,
                "time": {
                    "from": f"now-{config.time_range}",
                    "to": "now"
                },
                "timepicker": {
                    "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h"]
                },
                "panels": panels,
                "editable": True,
                "gnetId": None,
                "graphTooltip": 0,
                "hideControls": False,
                "links": [],
                "schemaVersion": 16,
                "style": "dark",
                "templating": {
                    "list": []
                },
                "version": 1
            },
            "overwrite": True
        }
    
    def test_connection(self) -> bool:
        """Grafana 연결 테스트"""
        try:
            response = self.session.get(f"{self.grafana_url}/api/health")
            if response.status_code == 200:
                safe_print("✅ Grafana 연결 성공")
                return True
            else:
                safe_print(f"❌ Grafana 연결 실패: {response.status_code}")
                return False
        except Exception as e:
            safe_print(f"❌ Grafana 연결 오류: {e}")
            return False
    
    def create_datasource(self, name: str, ds_type: DataSourceType, url: str, **kwargs) -> bool:
        """데이터 소스 생성"""
        datasource_config = {
            "name": name,
            "type": ds_type.value,
            "url": url,
            "access": "proxy",
            "isDefault": kwargs.get("is_default", False)
        }
        
        # 데이터 소스별 추가 설정
        if ds_type == DataSourceType.ELASTICSEARCH:
            datasource_config.update({
                "database": kwargs.get("index_pattern", "*"),
                "jsonData": {
                    "esVersion": 70,
                    "timeField": "@timestamp",
                    "interval": "Daily"
                }
            })
        
        try:
            response = self.session.post(
                f"{self.grafana_url}/api/datasources",
                json=datasource_config
            )
            
            if response.status_code in [200, 409]:  # 409는 이미 존재
                safe_print(f"✅ 데이터 소스 생성/업데이트: {name}")
                return True
            else:
                safe_print(f"❌ 데이터 소스 생성 실패: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"데이터 소스 생성 오류: {e}")
            return False
    
    def create_dashboard(self, template_name: str) -> bool:
        """대시보드 생성"""
        if template_name not in self.dashboard_templates:
            safe_print(f"❌ 알 수 없는 템플릿: {template_name}")
            return False
        
        config = self.dashboard_templates[template_name]
        dashboard_json = self._create_dashboard_json(config)
        
        try:
            response = self.session.post(
                f"{self.grafana_url}/api/dashboards/db",
                json=dashboard_json
            )
            
            if response.status_code == 200:
                safe_print(f"✅ 대시보드 생성: {config.title}")
                return True
            else:
                safe_print(f"❌ 대시보드 생성 실패: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"대시보드 생성 오류: {e}")
            return False
    
    def create_all_dashboards(self) -> bool:
        """모든 대시보드 생성"""
        success_count = 0
        
        for template_name in self.dashboard_templates.keys():
            if self.create_dashboard(template_name):
                success_count += 1
        
        safe_print(f"📊 대시보드 생성 완료: {success_count}/{len(self.dashboard_templates)}개")
        return success_count == len(self.dashboard_templates)
    
    def setup_datasources(self) -> bool:
        """기본 데이터 소스 설정"""
        datasources = [
            ("Prometheus", DataSourceType.PROMETHEUS, "http://prometheus:9090", {"is_default": True}),
            ("Elasticsearch", DataSourceType.ELASTICSEARCH, "http://elasticsearch:9200", {"index_pattern": "two-very-auto-*"}),
        ]
        
        success_count = 0
        for name, ds_type, url, kwargs in datasources:
            if self.create_datasource(name, ds_type, url, **kwargs):
                success_count += 1
        
        return success_count == len(datasources)
    
    def export_dashboard_config(self, output_dir: Path):
        """대시보드 설정을 파일로 내보내기"""
        output_dir.mkdir(exist_ok=True)
        
        for template_name, config in self.dashboard_templates.items():
            dashboard_json = self._create_dashboard_json(config)
            
            output_file = output_dir / f"{template_name}_dashboard.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dashboard_json, f, indent=2, ensure_ascii=False)
            
            safe_print(f"📁 대시보드 설정 내보내기: {output_file}")


def setup_grafana_dashboards(grafana_url: str = "http://localhost:3000",
                           api_key: Optional[str] = None) -> bool:
    """Grafana 대시보드 전체 설정"""
    safe_print("📊 Grafana 대시보드 설정 시작")
    
    manager = GrafanaDashboardManager(grafana_url=grafana_url, api_key=api_key)
    
    # 연결 테스트
    if not manager.test_connection():
        return False
    
    # 데이터 소스 설정
    if not manager.setup_datasources():
        safe_print("⚠️ 일부 데이터 소스 설정 실패")
    
    # 대시보드 생성
    success = manager.create_all_dashboards()
    
    if success:
        safe_print("✅ Grafana 대시보드 설정 완료")
    else:
        safe_print("⚠️ 일부 대시보드 생성 실패")
    
    return success


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== Grafana 대시보드 관리자 테스트 ===")
    
    manager = GrafanaDashboardManager()
    
    # 설정 파일 내보내기
    output_dir = Path("grafana_dashboards")
    manager.export_dashboard_config(output_dir)
    
    safe_print("🏁 Grafana 대시보드 관리자 테스트 완료")