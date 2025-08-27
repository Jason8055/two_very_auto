#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto v3.0 - 알림 시스템
Prometheus AlertManager 통합 및 다중 채널 알림
"""

import json
import smtplib
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import threading
import time
from queue import Queue, Empty

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent / 'python'))
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """알림 심각도"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """알림 상태"""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"


class NotificationChannel(Enum):
    """알림 채널"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    DISCORD = "discord"


@dataclass
class AlertRule:
    """알림 규칙"""
    name: str
    description: str
    query: str
    severity: AlertSeverity
    threshold: float
    duration: str = "5m"
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None
    enabled: bool = True


@dataclass
class Alert:
    """알림"""
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    timestamp: datetime
    labels: Dict[str, str]
    annotations: Dict[str, str]
    value: Optional[float] = None
    fingerprint: Optional[str] = None
    generator_url: Optional[str] = None


@dataclass
class NotificationConfig:
    """알림 설정"""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any] = None


class PrometheusRuleManager:
    """Prometheus 알림 규칙 관리자"""
    
    def __init__(self, rules_file: Path = Path("prometheus_rules.yml")):
        self.rules_file = rules_file
        self.alert_rules = self._define_alert_rules()
        
        safe_print("⚠️ Prometheus 알림 규칙 관리자 초기화 완료")
    
    def _define_alert_rules(self) -> List[AlertRule]:
        """알림 규칙 정의"""
        return [
            # 시스템 알림
            AlertRule(
                name="HighCPUUsage",
                description="CPU 사용률이 높습니다",
                query='avg(two_very_auto_system_cpu_usage_percent) > 80',
                severity=AlertSeverity.WARNING,
                threshold=80,
                duration="5m",
                labels={"category": "system", "component": "cpu"},
                annotations={
                    "summary": "CPU 사용률이 {{ $value }}%입니다",
                    "description": "5분간 평균 CPU 사용률이 80%를 초과했습니다."
                }
            ),
            
            AlertRule(
                name="HighMemoryUsage",
                description="메모리 사용률이 높습니다",
                query='(two_very_auto_system_memory_usage_bytes{memory_type="used"} / two_very_auto_system_memory_usage_bytes{memory_type="total"}) * 100 > 90',
                severity=AlertSeverity.CRITICAL,
                threshold=90,
                duration="2m",
                labels={"category": "system", "component": "memory"},
                annotations={
                    "summary": "메모리 사용률이 {{ $value }}%입니다",
                    "description": "메모리 사용률이 90%를 초과했습니다. 즉시 확인이 필요합니다."
                }
            ),
            
            AlertRule(
                name="DiskSpaceLow",
                description="디스크 공간이 부족합니다",
                query='(two_very_auto_system_disk_usage_bytes{usage_type="used"} / two_very_auto_system_disk_usage_bytes{usage_type="total"}) * 100 > 85',
                severity=AlertSeverity.WARNING,
                threshold=85,
                duration="1m",
                labels={"category": "system", "component": "disk"},
                annotations={
                    "summary": "디스크 사용률이 {{ $value }}%입니다",
                    "description": "디스크 공간이 85%를 초과했습니다. 정리 또는 확장이 필요합니다."
                }
            ),
            
            # 애플리케이션 알림
            AlertRule(
                name="HighHttpErrorRate",
                description="HTTP 에러율이 높습니다",
                query='rate(two_very_auto_http_requests_total{status=~"5.."}[5m]) / rate(two_very_auto_http_requests_total[5m]) * 100 > 5',
                severity=AlertSeverity.CRITICAL,
                threshold=5,
                duration="3m",
                labels={"category": "application", "component": "http"},
                annotations={
                    "summary": "HTTP 5xx 에러율이 {{ $value }}%입니다",
                    "description": "HTTP 5xx 에러율이 5%를 초과했습니다. 애플리케이션 상태를 확인하세요."
                }
            ),
            
            AlertRule(
                name="SlowHttpRequests",
                description="HTTP 요청 응답이 느립니다",
                query='histogram_quantile(0.95, rate(two_very_auto_http_request_duration_seconds_bucket[5m])) > 2',
                severity=AlertSeverity.WARNING,
                threshold=2,
                duration="5m",
                labels={"category": "application", "component": "performance"},
                annotations={
                    "summary": "HTTP 응답 시간 P95가 {{ $value }}초입니다",
                    "description": "HTTP 요청의 95 백분위수 응답 시간이 2초를 초과했습니다."
                }
            ),
            
            AlertRule(
                name="WebSocketConnectionDrop",
                description="WebSocket 연결이 급격히 감소했습니다",
                query='rate(two_very_auto_websocket_connections_active[5m]) < -10',
                severity=AlertSeverity.WARNING,
                threshold=-10,
                duration="1m",
                labels={"category": "application", "component": "websocket"},
                annotations={
                    "summary": "WebSocket 연결 수가 급격히 감소했습니다",
                    "description": "WebSocket 연결 수가 분당 10개 이상 감소하고 있습니다."
                }
            ),
            
            # AI 엔진 알림
            AlertRule(
                name="LowPredictionAccuracy",
                description="AI 예측 정확도가 낮습니다",
                query='two_very_auto_baccarat_prediction_accuracy < 60',
                severity=AlertSeverity.WARNING,
                threshold=60,
                duration="10m",
                labels={"category": "business", "component": "ai"},
                annotations={
                    "summary": "AI 예측 정확도가 {{ $value }}%입니다",
                    "description": "AI 예측 정확도가 60% 미만입니다. 모델 재훈련이 필요할 수 있습니다."
                }
            ),
            
            AlertRule(
                name="SlowAiInference",
                description="AI 추론 시간이 느립니다",
                query='histogram_quantile(0.95, rate(two_very_auto_ai_model_inference_duration_seconds_bucket[5m])) > 1',
                severity=AlertSeverity.WARNING,
                threshold=1,
                duration="5m",
                labels={"category": "application", "component": "ai"},
                annotations={
                    "summary": "AI 추론 시간 P95가 {{ $value }}초입니다",
                    "description": "AI 모델 추론 시간이 1초를 초과했습니다."
                }
            ),
            
            # 데이터베이스 알림
            AlertRule(
                name="HighDatabaseConnections",
                description="데이터베이스 연결 수가 높습니다",
                query='two_very_auto_database_connections_active > 50',
                severity=AlertSeverity.WARNING,
                threshold=50,
                duration="5m",
                labels={"category": "database", "component": "connections"},
                annotations={
                    "summary": "데이터베이스 연결 수가 {{ $value }}개입니다",
                    "description": "활성 데이터베이스 연결 수가 50개를 초과했습니다."
                }
            ),
            
            AlertRule(
                name="SlowDatabaseQueries",
                description="데이터베이스 쿼리가 느립니다",
                query='histogram_quantile(0.95, rate(two_very_auto_database_query_duration_seconds_bucket[5m])) > 5',
                severity=AlertSeverity.WARNING,
                threshold=5,
                duration="5m",
                labels={"category": "database", "component": "performance"},
                annotations={
                    "summary": "데이터베이스 쿼리 시간 P95가 {{ $value }}초입니다",
                    "description": "데이터베이스 쿼리 응답 시간이 5초를 초과했습니다."
                }
            )
        ]
    
    def generate_prometheus_rules(self) -> Dict[str, Any]:
        """Prometheus 알림 규칙 YAML 생성"""
        groups = []
        
        # 카테고리별로 그룹화
        categories = {}
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
                
            category = rule.labels.get("category", "general") if rule.labels else "general"
            if category not in categories:
                categories[category] = []
            categories[category].append(rule)
        
        # 각 카테고리를 그룹으로 변환
        for category, rules in categories.items():
            group_rules = []
            for rule in rules:
                group_rules.append({
                    "alert": rule.name,
                    "expr": rule.query,
                    "for": rule.duration,
                    "labels": {
                        "severity": rule.severity.value,
                        **(rule.labels or {})
                    },
                    "annotations": {
                        "summary": rule.description,
                        **(rule.annotations or {})
                    }
                })
            
            groups.append({
                "name": f"two_very_auto_{category}",
                "interval": "30s",
                "rules": group_rules
            })
        
        return {
            "groups": groups
        }
    
    def save_prometheus_rules(self):
        """Prometheus 알림 규칙을 파일로 저장"""
        rules_config = self.generate_prometheus_rules()
        
        try:
            import yaml
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                yaml.dump(rules_config, f, default_flow_style=False, allow_unicode=True)
            
            safe_print(f"📋 Prometheus 규칙 저장: {self.rules_file}")
            
        except ImportError:
            # YAML 라이브러리가 없으면 JSON으로 저장
            json_file = self.rules_file.with_suffix('.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(rules_config, f, indent=2, ensure_ascii=False)
            
            safe_print(f"📋 Prometheus 규칙 저장 (JSON): {json_file}")


class NotificationManager:
    """알림 관리자"""
    
    def __init__(self):
        self.notification_configs = self._setup_notification_configs()
        self.notification_queue = Queue(maxsize=1000)
        self.worker_thread = None
        self.running = False
        
        # 알림 히스토리
        self.alert_history: List[Alert] = []
        self.max_history = 1000
        
        safe_print("📢 알림 관리자 초기화 완료")
    
    def _setup_notification_configs(self) -> Dict[NotificationChannel, NotificationConfig]:
        """알림 설정 구성"""
        return {
            NotificationChannel.EMAIL: NotificationConfig(
                channel=NotificationChannel.EMAIL,
                enabled=True,
                config={
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": "your-email@gmail.com",
                    "password": "your-app-password",
                    "from_address": "Two Very Auto <alerts@two-very-auto.com>",
                    "to_addresses": ["admin@two-very-auto.com"]
                }
            ),
            
            NotificationChannel.SLACK: NotificationConfig(
                channel=NotificationChannel.SLACK,
                enabled=True,
                config={
                    "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
                    "channel": "#alerts",
                    "username": "AlertBot"
                }
            ),
            
            NotificationChannel.WEBHOOK: NotificationConfig(
                channel=NotificationChannel.WEBHOOK,
                enabled=True,
                config={
                    "url": "https://your-webhook-endpoint.com/alerts",
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer your-token"
                    }
                }
            ),
            
            NotificationChannel.DISCORD: NotificationConfig(
                channel=NotificationChannel.DISCORD,
                enabled=False,
                config={
                    "webhook_url": "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL"
                }
            )
        }
    
    def start_worker(self):
        """알림 워커 스레드 시작"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_notifications)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        safe_print("🚀 알림 처리 워커 시작")
    
    def stop_worker(self):
        """알림 워커 스레드 중지"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        safe_print("🛑 알림 처리 워커 중지")
    
    def _process_notifications(self):
        """알림 처리 워커"""
        while self.running:
            try:
                alert = self.notification_queue.get(timeout=1)
                self._send_notifications(alert)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"알림 처리 오류: {e}")
    
    def _send_notifications(self, alert: Alert):
        """모든 활성화된 채널로 알림 전송"""
        for channel, config in self.notification_configs.items():
            if not config.enabled:
                continue
                
            try:
                if channel == NotificationChannel.EMAIL:
                    self._send_email_notification(alert, config)
                elif channel == NotificationChannel.SLACK:
                    self._send_slack_notification(alert, config)
                elif channel == NotificationChannel.WEBHOOK:
                    self._send_webhook_notification(alert, config)
                elif channel == NotificationChannel.DISCORD:
                    self._send_discord_notification(alert, config)
                    
            except Exception as e:
                logger.error(f"{channel.value} 알림 전송 실패: {e}")
    
    def _send_email_notification(self, alert: Alert, config: NotificationConfig):
        """이메일 알림 전송"""
        smtp_config = config.config
        
        # 이메일 내용 구성
        subject = f"[{alert.severity.value.upper()}] {alert.rule_name}"
        
        # HTML 템플릿
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: {'#ff4444' if alert.severity == AlertSeverity.CRITICAL else '#ffaa44' if alert.severity == AlertSeverity.WARNING else '#4444ff'}; 
                           color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h2 style="margin: 0;">🚨 {alert.severity.value.upper()} Alert</h2>
                    <p style="margin: 5px 0 0 0; font-size: 18px;">{alert.rule_name}</p>
                </div>
                
                <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <h3>알림 세부 정보</h3>
                    <p><strong>메시지:</strong> {alert.message}</p>
                    <p><strong>시간:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>상태:</strong> {alert.status.value}</p>
                    {f'<p><strong>값:</strong> {alert.value}</p>' if alert.value is not None else ''}
                </div>
                
                <div style="background: #f0f0f0; padding: 15px; border-radius: 5px;">
                    <h3>레이블</h3>
                    <ul>
                        {''.join([f'<li><strong>{k}:</strong> {v}</li>' for k, v in alert.labels.items()])}
                    </ul>
                </div>
                
                <div style="margin-top: 20px; text-align: center; color: #666;">
                    <p>Two Very Auto Monitoring System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 이메일 생성
        msg = MimeMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_config['from_address']
        msg['To'] = ', '.join(smtp_config['to_addresses'])
        
        html_part = MimeText(html_body, 'html')
        msg.attach(html_part)
        
        # SMTP 전송
        try:
            with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
                server.starttls()
                server.login(smtp_config['username'], smtp_config['password'])
                server.sendmail(
                    smtp_config['from_address'],
                    smtp_config['to_addresses'],
                    msg.as_string()
                )
                
        except Exception as e:
            logger.error(f"이메일 전송 실패: {e}")
    
    def _send_slack_notification(self, alert: Alert, config: NotificationConfig):
        """Slack 알림 전송"""
        slack_config = config.config
        
        # 심각도에 따른 색상
        color_map = {
            AlertSeverity.INFO: "good",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.CRITICAL: "danger",
            AlertSeverity.EMERGENCY: "danger"
        }
        
        payload = {
            "channel": slack_config['channel'],
            "username": slack_config['username'],
            "attachments": [
                {
                    "color": color_map[alert.severity],
                    "title": f"🚨 {alert.severity.value.upper()} Alert",
                    "title_link": alert.generator_url,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Rule",
                            "value": alert.rule_name,
                            "short": True
                        },
                        {
                            "title": "Status",
                            "value": alert.status.value,
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                            "short": True
                        }
                    ] + [
                        {
                            "title": k,
                            "value": v,
                            "short": True
                        } for k, v in alert.labels.items()
                    ],
                    "footer": "Two Very Auto Monitoring",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }
        
        response = requests.post(slack_config['webhook_url'], json=payload, timeout=10)
        response.raise_for_status()
    
    def _send_webhook_notification(self, alert: Alert, config: NotificationConfig):
        """웹훅 알림 전송"""
        webhook_config = config.config
        
        payload = {
            "alert": {
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "labels": alert.labels,
                "annotations": alert.annotations,
                "value": alert.value,
                "fingerprint": alert.fingerprint,
                "generator_url": alert.generator_url
            }
        }
        
        response = requests.post(
            webhook_config['url'],
            json=payload,
            headers=webhook_config.get('headers', {}),
            timeout=10
        )
        response.raise_for_status()
    
    def _send_discord_notification(self, alert: Alert, config: NotificationConfig):
        """Discord 알림 전송"""
        discord_config = config.config
        
        # 심각도에 따른 색상 (16진수)
        color_map = {
            AlertSeverity.INFO: 0x3498db,      # 파란색
            AlertSeverity.WARNING: 0xf39c12,   # 주황색
            AlertSeverity.CRITICAL: 0xe74c3c,  # 빨간색
            AlertSeverity.EMERGENCY: 0x8e44ad  # 보라색
        }
        
        embed = {
            "title": f"🚨 {alert.severity.value.upper()} Alert",
            "description": alert.message,
            "color": color_map[alert.severity],
            "fields": [
                {
                    "name": "Rule",
                    "value": alert.rule_name,
                    "inline": True
                },
                {
                    "name": "Status",
                    "value": alert.status.value,
                    "inline": True
                },
                {
                    "name": "Time",
                    "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    "inline": True
                }
            ],
            "footer": {
                "text": "Two Very Auto Monitoring"
            },
            "timestamp": alert.timestamp.isoformat()
        }
        
        # 레이블을 필드로 추가
        for k, v in alert.labels.items():
            if len(embed["fields"]) < 25:  # Discord 임베드 필드 제한
                embed["fields"].append({
                    "name": k,
                    "value": v,
                    "inline": True
                })
        
        payload = {
            "embeds": [embed]
        }
        
        response = requests.post(discord_config['webhook_url'], json=payload, timeout=10)
        response.raise_for_status()
    
    def send_alert(self, alert: Alert):
        """알림 전송"""
        if not self.running:
            self.start_worker()
        
        # 히스토리에 추가
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        # 큐에 추가
        try:
            self.notification_queue.put_nowait(alert)
            safe_print(f"📢 알림 큐에 추가: {alert.rule_name} ({alert.severity.value})")
        except:
            # 큐가 가득 찬 경우 로깅만
            logger.warning("알림 큐가 가득 참")
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """알림 히스토리 조회"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history 
            if alert.timestamp >= cutoff_time
        ]


class AlertingSystem:
    """통합 알림 시스템"""
    
    def __init__(self):
        self.rule_manager = PrometheusRuleManager()
        self.notification_manager = NotificationManager()
        
        safe_print("🚨 통합 알림 시스템 초기화 완료")
    
    def setup(self):
        """알림 시스템 설정"""
        # Prometheus 규칙 생성
        self.rule_manager.save_prometheus_rules()
        
        # 알림 워커 시작
        self.notification_manager.start_worker()
        
        safe_print("✅ 알림 시스템 설정 완료")
    
    def process_prometheus_webhook(self, webhook_data: Dict[str, Any]):
        """Prometheus AlertManager 웹훅 처리"""
        alerts = webhook_data.get('alerts', [])
        
        for alert_data in alerts:
            alert = Alert(
                rule_name=alert_data.get('labels', {}).get('alertname', 'Unknown'),
                severity=AlertSeverity(alert_data.get('labels', {}).get('severity', 'info')),
                status=AlertStatus(alert_data.get('status', 'firing')),
                message=alert_data.get('annotations', {}).get('summary', 'No description'),
                timestamp=datetime.fromisoformat(alert_data.get('startsAt', datetime.now().isoformat()).replace('Z', '+00:00')),
                labels=alert_data.get('labels', {}),
                annotations=alert_data.get('annotations', {}),
                fingerprint=alert_data.get('fingerprint'),
                generator_url=alert_data.get('generatorURL')
            )
            
            self.notification_manager.send_alert(alert)
    
    def send_test_alert(self):
        """테스트 알림 전송"""
        test_alert = Alert(
            rule_name="TestAlert",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.FIRING,
            message="알림 시스템 테스트입니다",
            timestamp=datetime.now(),
            labels={"category": "test", "component": "alerting"},
            annotations={"description": "알림 시스템 정상 작동 테스트"}
        )
        
        self.notification_manager.send_alert(test_alert)
        safe_print("📨 테스트 알림 전송 완료")
    
    def shutdown(self):
        """알림 시스템 종료"""
        self.notification_manager.stop_worker()
        safe_print("🚨 알림 시스템 종료 완료")


# 전역 알림 시스템 인스턴스
_alerting_system = None

def get_alerting_system() -> AlertingSystem:
    """알림 시스템 인스턴스 반환"""
    global _alerting_system
    if _alerting_system is None:
        _alerting_system = AlertingSystem()
    return _alerting_system


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 알림 시스템 테스트 ===")
    
    alerting = get_alerting_system()
    alerting.setup()
    
    # 테스트 알림 전송
    alerting.send_test_alert()
    
    # 몇 초 대기
    time.sleep(5)
    
    alerting.shutdown()
    
    safe_print("🏁 알림 시스템 테스트 완료")