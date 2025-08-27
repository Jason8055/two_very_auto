#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
성능 모니터링 시스템 v1.0
시스템 메트릭, AI 성능, WebSocket 연결 상태 실시간 모니터링
"""

import sys
import json
import asyncio
import psutil
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from pathlib import Path
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemMetricsCollector:
    """시스템 메트릭 수집기"""
    
    def __init__(self, max_history: int = 300):  # 5분간 데이터 (1초 간격)
        self.max_history = max_history
        self.metrics_history = {
            'cpu_percent': deque(maxlen=max_history),
            'memory_usage': deque(maxlen=max_history),
            'disk_io': deque(maxlen=max_history),
            'network_io': deque(maxlen=max_history),
            'process_count': deque(maxlen=max_history),
            'timestamps': deque(maxlen=max_history)
        }
        
        self.process = psutil.Process()
        self.start_time = datetime.now()
        
    def collect_metrics(self) -> Dict[str, Any]:
        """현재 시스템 메트릭 수집"""
        timestamp = datetime.now()
        
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 메모리 사용률
            memory = psutil.virtual_memory()
            process_memory = self.process.memory_info()
            
            # 디스크 I/O
            disk_io = psutil.disk_io_counters()
            
            # 네트워크 I/O
            network_io = psutil.net_io_counters()
            
            # 프로세스 수
            process_count = len(psutil.pids())
            
            metrics = {
                'timestamp': timestamp.isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count(),
                    'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'process_rss': process_memory.rss,
                    'process_vms': process_memory.vms
                },
                'disk': {
                    'read_bytes': disk_io.read_bytes if disk_io else 0,
                    'write_bytes': disk_io.write_bytes if disk_io else 0,
                    'read_count': disk_io.read_count if disk_io else 0,
                    'write_count': disk_io.write_count if disk_io else 0
                },
                'network': {
                    'bytes_sent': network_io.bytes_sent if network_io else 0,
                    'bytes_recv': network_io.bytes_recv if network_io else 0,
                    'packets_sent': network_io.packets_sent if network_io else 0,
                    'packets_recv': network_io.packets_recv if network_io else 0
                },
                'system': {
                    'process_count': process_count,
                    'uptime': (timestamp - self.start_time).total_seconds(),
                    'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
                }
            }
            
            # 히스토리에 추가
            self.metrics_history['cpu_percent'].append(cpu_percent)
            self.metrics_history['memory_usage'].append(memory.percent)
            self.metrics_history['disk_io'].append(disk_io.read_bytes + disk_io.write_bytes if disk_io else 0)
            self.metrics_history['network_io'].append(network_io.bytes_sent + network_io.bytes_recv if network_io else 0)
            self.metrics_history['process_count'].append(process_count)
            self.metrics_history['timestamps'].append(timestamp.isoformat())
            
            return metrics
            
        except Exception as e:
            logger.error(f"메트릭 수집 오류: {e}")
            return {}
    
    def get_trend_analysis(self) -> Dict[str, Any]:
        """트렌드 분석 데이터 반환"""
        if len(self.metrics_history['cpu_percent']) < 10:
            return {'status': 'insufficient_data'}
        
        # 최근 30개 데이터 포인트로 트렌드 분석
        recent_cpu = list(self.metrics_history['cpu_percent'])[-30:]
        recent_memory = list(self.metrics_history['memory_usage'])[-30:]
        
        return {
            'cpu': {
                'current': recent_cpu[-1] if recent_cpu else 0,
                'average': sum(recent_cpu) / len(recent_cpu),
                'max': max(recent_cpu),
                'min': min(recent_cpu),
                'trend': 'increasing' if recent_cpu[-1] > recent_cpu[0] else 'decreasing'
            },
            'memory': {
                'current': recent_memory[-1] if recent_memory else 0,
                'average': sum(recent_memory) / len(recent_memory),
                'max': max(recent_memory),
                'min': min(recent_memory),
                'trend': 'increasing' if recent_memory[-1] > recent_memory[0] else 'decreasing'
            }
        }
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """시스템 알림 생성"""
        alerts = []
        
        if not self.metrics_history['cpu_percent']:
            return alerts
        
        current_cpu = self.metrics_history['cpu_percent'][-1]
        current_memory = self.metrics_history['memory_usage'][-1]
        
        # CPU 사용률 경고
        if current_cpu > 90:
            alerts.append({
                'type': 'high_cpu',
                'severity': 'critical',
                'message': f'CPU 사용률이 {current_cpu:.1f}%로 매우 높습니다',
                'value': current_cpu,
                'threshold': 90,
                'timestamp': datetime.now().isoformat()
            })
        elif current_cpu > 80:
            alerts.append({
                'type': 'high_cpu',
                'severity': 'warning',
                'message': f'CPU 사용률이 {current_cpu:.1f}%로 높습니다',
                'value': current_cpu,
                'threshold': 80,
                'timestamp': datetime.now().isoformat()
            })
        
        # 메모리 사용률 경고
        if current_memory > 95:
            alerts.append({
                'type': 'high_memory',
                'severity': 'critical',
                'message': f'메모리 사용률이 {current_memory:.1f}%로 매우 높습니다',
                'value': current_memory,
                'threshold': 95,
                'timestamp': datetime.now().isoformat()
            })
        elif current_memory > 85:
            alerts.append({
                'type': 'high_memory',
                'severity': 'warning',
                'message': f'메모리 사용률이 {current_memory:.1f}%로 높습니다',
                'value': current_memory,
                'threshold': 85,
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts


class AIPerformanceTracker:
    """AI 성능 추적기"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.prediction_history = deque(maxlen=max_history)
        self.training_history = deque(maxlen=50)  # 최근 50번 훈련 기록
        
        self.performance_metrics = {
            'total_predictions': 0,
            'correct_predictions': 0,
            'prediction_times': deque(maxlen=100),
            'accuracy_over_time': deque(maxlen=100),
            'confidence_distribution': defaultdict(int)
        }
    
    def track_prediction(self, prediction_data: Dict[str, Any], execution_time: float):
        """예측 성능 추적"""
        timestamp = datetime.now()
        
        # 예측 기록 추가
        prediction_record = {
            'timestamp': timestamp.isoformat(),
            'predicted_type': prediction_data.get('predicted_pair_type'),
            'confidence': prediction_data.get('confidence', 0),
            'execution_time': execution_time,
            'method': prediction_data.get('prediction_method', 'unknown')
        }
        
        self.prediction_history.append(prediction_record)
        self.performance_metrics['total_predictions'] += 1
        self.performance_metrics['prediction_times'].append(execution_time)
        
        # 신뢰도 분포 업데이트
        confidence_bucket = int(prediction_data.get('confidence', 0) * 10) / 10
        self.performance_metrics['confidence_distribution'][confidence_bucket] += 1
    
    def track_validation(self, prediction_id: str, actual_result: str, was_correct: bool):
        """예측 검증 결과 추적"""
        if was_correct:
            self.performance_metrics['correct_predictions'] += 1
        
        # 정확도 계산
        if self.performance_metrics['total_predictions'] > 0:
            accuracy = self.performance_metrics['correct_predictions'] / self.performance_metrics['total_predictions']
            self.performance_metrics['accuracy_over_time'].append(accuracy)
    
    def track_training(self, training_result: Dict[str, Any]):
        """모델 훈련 결과 추적"""
        training_record = {
            'timestamp': datetime.now().isoformat(),
            'training_samples': training_result.get('training_samples', 0),
            'validation_samples': training_result.get('validation_samples', 0),
            'val_accuracy': training_result.get('val_accuracy', 0),
            'val_precision': training_result.get('val_precision', 0),
            'val_recall': training_result.get('val_recall', 0),
            'epochs_trained': training_result.get('epochs_trained', 0),
            'success': training_result.get('success', False)
        }
        
        self.training_history.append(training_record)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """AI 성능 요약 반환"""
        total_predictions = self.performance_metrics['total_predictions']
        
        if total_predictions == 0:
            return {
                'status': 'no_predictions',
                'message': '예측 데이터가 없습니다'
            }
        
        # 평균 실행 시간
        avg_prediction_time = 0
        if self.performance_metrics['prediction_times']:
            avg_prediction_time = sum(self.performance_metrics['prediction_times']) / len(self.performance_metrics['prediction_times'])
        
        # 현재 정확도
        current_accuracy = 0
        if total_predictions > 0:
            current_accuracy = self.performance_metrics['correct_predictions'] / total_predictions
        
        # 최근 정확도 트렌드
        recent_accuracy_trend = 'stable'
        if len(self.performance_metrics['accuracy_over_time']) >= 10:
            recent_accuracies = list(self.performance_metrics['accuracy_over_time'])[-10:]
            if recent_accuracies[-1] > recent_accuracies[0]:
                recent_accuracy_trend = 'improving'
            elif recent_accuracies[-1] < recent_accuracies[0]:
                recent_accuracy_trend = 'declining'
        
        return {
            'total_predictions': total_predictions,
            'current_accuracy': current_accuracy,
            'accuracy_trend': recent_accuracy_trend,
            'avg_prediction_time': avg_prediction_time,
            'prediction_speed': 'fast' if avg_prediction_time < 0.05 else 'normal' if avg_prediction_time < 0.1 else 'slow',
            'confidence_distribution': dict(self.performance_metrics['confidence_distribution']),
            'recent_training': list(self.training_history)[-5:] if self.training_history else []
        }


class WebSocketConnectionMonitor:
    """WebSocket 연결 상태 모니터"""
    
    def __init__(self):
        self.connection_stats = {
            'chart_connections': {'active': 0, 'total_connected': 0, 'total_disconnected': 0},
            'dashboard_connections': {'active': 0, 'total_connected': 0, 'total_disconnected': 0},
            'connection_history': deque(maxlen=500),
            'message_stats': {
                'sent': 0,
                'received': 0,
                'failed': 0
            },
            'performance_metrics': {
                'avg_message_size': 0,
                'peak_connections': 0,
                'connection_duration_avg': 0
            }
        }
        
        self.active_connections = {}
    
    def track_connection(self, connection_type: str, connection_id: str, action: str):
        """WebSocket 연결 추적"""
        timestamp = datetime.now()
        
        connection_record = {
            'timestamp': timestamp.isoformat(),
            'connection_type': connection_type,
            'connection_id': connection_id,
            'action': action  # 'connect' or 'disconnect'
        }
        
        self.connection_stats['connection_history'].append(connection_record)
        
        if action == 'connect':
            self.connection_stats[f'{connection_type}_connections']['active'] += 1
            self.connection_stats[f'{connection_type}_connections']['total_connected'] += 1
            self.active_connections[connection_id] = {
                'type': connection_type,
                'connected_at': timestamp,
                'messages_sent': 0,
                'messages_received': 0
            }
            
            # 최대 동시 연결 수 업데이트
            total_active = sum(stats['active'] for stats in [
                self.connection_stats['chart_connections'],
                self.connection_stats['dashboard_connections']
            ])
            
            if total_active > self.connection_stats['performance_metrics']['peak_connections']:
                self.connection_stats['performance_metrics']['peak_connections'] = total_active
                
        elif action == 'disconnect':
            self.connection_stats[f'{connection_type}_connections']['active'] -= 1
            self.connection_stats[f'{connection_type}_connections']['total_disconnected'] += 1
            
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
    
    def track_message(self, connection_id: str, direction: str, message_size: int, success: bool):
        """메시지 전송/수신 추적"""
        if direction == 'sent':
            self.connection_stats['message_stats']['sent'] += 1
        elif direction == 'received':
            self.connection_stats['message_stats']['received'] += 1
        
        if not success:
            self.connection_stats['message_stats']['failed'] += 1
        
        # 연결별 메시지 카운트 업데이트
        if connection_id in self.active_connections:
            self.active_connections[connection_id][f'messages_{direction}'] += 1
        
        # 평균 메시지 크기 업데이트
        total_messages = self.connection_stats['message_stats']['sent'] + self.connection_stats['message_stats']['received']
        if total_messages > 0:
            current_avg = self.connection_stats['performance_metrics']['avg_message_size']
            new_avg = ((current_avg * (total_messages - 1)) + message_size) / total_messages
            self.connection_stats['performance_metrics']['avg_message_size'] = new_avg
    
    def get_connection_summary(self) -> Dict[str, Any]:
        """연결 상태 요약 반환"""
        total_active = (self.connection_stats['chart_connections']['active'] + 
                       self.connection_stats['dashboard_connections']['active'])
        
        # 평균 연결 지속 시간 계산
        avg_duration = 0
        if self.active_connections:
            durations = []
            current_time = datetime.now()
            for conn_info in self.active_connections.values():
                duration = (current_time - conn_info['connected_at']).total_seconds()
                durations.append(duration)
            avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'total_active_connections': total_active,
            'chart_connections': self.connection_stats['chart_connections']['active'],
            'dashboard_connections': self.connection_stats['dashboard_connections']['active'],
            'peak_connections': self.connection_stats['performance_metrics']['peak_connections'],
            'message_stats': self.connection_stats['message_stats'].copy(),
            'avg_message_size': self.connection_stats['performance_metrics']['avg_message_size'],
            'avg_connection_duration': avg_duration,
            'connection_health': 'excellent' if total_active > 0 and self.connection_stats['message_stats']['failed'] < 5 else 'good'
        }


class PerformanceMonitor:
    """메인 성능 모니터링 시스템"""
    
    def __init__(self):
        self.system_metrics = SystemMetricsCollector()
        self.ai_performance = AIPerformanceTracker()
        self.websocket_monitor = WebSocketConnectionMonitor()
        
        self.is_monitoring = False
        self.monitoring_thread = None
        self.monitoring_interval = 1.0  # 1초 간격
        
        self.alert_callbacks = []
        self.performance_thresholds = {
            'cpu_warning': 80,
            'cpu_critical': 90,
            'memory_warning': 85,
            'memory_critical': 95,
            'ai_accuracy_warning': 0.7,
            'prediction_time_warning': 0.1
        }
        
        safe_print("📊 성능 모니터링 시스템 초기화 완료")
    
    def start_monitoring(self):
        """모니터링 시작"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        safe_print("🔄 성능 모니터링 시작")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
        safe_print("⏹️ 성능 모니터링 중지")
    
    def _monitoring_loop(self):
        """모니터링 루프"""
        while self.is_monitoring:
            try:
                # 시스템 메트릭 수집
                self.system_metrics.collect_metrics()
                
                # 알림 체크
                alerts = self._check_all_alerts()
                for alert in alerts:
                    self._trigger_alert(alert)
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")
                time.sleep(5)  # 오류 시 5초 대기
    
    def _check_all_alerts(self) -> List[Dict[str, Any]]:
        """모든 알림 조건 확인"""
        alerts = []
        
        # 시스템 알림
        alerts.extend(self.system_metrics.get_alerts())
        
        # AI 성능 알림
        ai_summary = self.ai_performance.get_performance_summary()
        if ai_summary.get('current_accuracy', 1) < self.performance_thresholds['ai_accuracy_warning']:
            alerts.append({
                'type': 'low_ai_accuracy',
                'severity': 'warning',
                'message': f'AI 예측 정확도가 {ai_summary["current_accuracy"]:.1%}로 낮습니다',
                'value': ai_summary['current_accuracy'],
                'threshold': self.performance_thresholds['ai_accuracy_warning'],
                'timestamp': datetime.now().isoformat()
            })
        
        if ai_summary.get('avg_prediction_time', 0) > self.performance_thresholds['prediction_time_warning']:
            alerts.append({
                'type': 'slow_prediction',
                'severity': 'warning',
                'message': f'AI 예측 속도가 {ai_summary["avg_prediction_time"]:.3f}초로 느립니다',
                'value': ai_summary['avg_prediction_time'],
                'threshold': self.performance_thresholds['prediction_time_warning'],
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    def _trigger_alert(self, alert: Dict[str, Any]):
        """알림 트리거"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"알림 콜백 오류: {e}")
    
    def add_alert_callback(self, callback):
        """알림 콜백 추가"""
        self.alert_callbacks.append(callback)
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """종합 상태 보고서"""
        system_trend = self.system_metrics.get_trend_analysis()
        ai_summary = self.ai_performance.get_performance_summary()
        websocket_summary = self.websocket_monitor.get_connection_summary()
        
        # 전체 시스템 상태 평가
        system_health = 'excellent'
        health_issues = []
        
        if system_trend.get('cpu', {}).get('current', 0) > 85:
            system_health = 'warning'
            health_issues.append('높은 CPU 사용률')
        
        if system_trend.get('memory', {}).get('current', 0) > 90:
            system_health = 'critical'
            health_issues.append('높은 메모리 사용률')
        
        if ai_summary.get('current_accuracy', 1) < 0.8:
            system_health = 'warning'
            health_issues.append('낮은 AI 정확도')
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_health': system_health,
            'health_issues': health_issues,
            'system_metrics': system_trend,
            'ai_performance': ai_summary,
            'websocket_status': websocket_summary,
            'monitoring_status': {
                'is_active': self.is_monitoring,
                'monitoring_duration': time.time() - (time.time() if not hasattr(self, '_start_time') else self._start_time),
                'alert_callbacks': len(self.alert_callbacks)
            }
        }
    
    def export_performance_report(self) -> str:
        """성능 보고서 내보내기"""
        status = self.get_comprehensive_status()
        
        report = f"""
# Two Very Auto v2.0 - 성능 모니터링 보고서

## 보고서 정보
- **생성 시간**: {status['timestamp']}
- **전체 상태**: {status['overall_health'].upper()}

## 시스템 메트릭
### CPU
- **현재 사용률**: {status['system_metrics'].get('cpu', {}).get('current', 0):.1f}%
- **평균 사용률**: {status['system_metrics'].get('cpu', {}).get('average', 0):.1f}%
- **최대 사용률**: {status['system_metrics'].get('cpu', {}).get('max', 0):.1f}%
- **트렌드**: {status['system_metrics'].get('cpu', {}).get('trend', 'unknown')}

### 메모리
- **현재 사용률**: {status['system_metrics'].get('memory', {}).get('current', 0):.1f}%
- **평균 사용률**: {status['system_metrics'].get('memory', {}).get('average', 0):.1f}%
- **최대 사용률**: {status['system_metrics'].get('memory', {}).get('max', 0):.1f}%
- **트렌드**: {status['system_metrics'].get('memory', {}).get('trend', 'unknown')}

## AI 성능
- **총 예측 수**: {status['ai_performance'].get('total_predictions', 0):,}
- **현재 정확도**: {status['ai_performance'].get('current_accuracy', 0):.1%}
- **정확도 트렌드**: {status['ai_performance'].get('accuracy_trend', 'unknown')}
- **평균 예측 시간**: {status['ai_performance'].get('avg_prediction_time', 0):.3f}초
- **예측 속도**: {status['ai_performance'].get('prediction_speed', 'unknown')}

## WebSocket 연결
- **활성 연결 수**: {status['websocket_status'].get('total_active_connections', 0)}
- **최대 동시 연결**: {status['websocket_status'].get('peak_connections', 0)}
- **평균 연결 지속 시간**: {status['websocket_status'].get('avg_connection_duration', 0):.1f}초
- **연결 상태**: {status['websocket_status'].get('connection_health', 'unknown')}

## 메시지 통계
- **전송 메시지**: {status['websocket_status'].get('message_stats', {}).get('sent', 0):,}
- **수신 메시지**: {status['websocket_status'].get('message_stats', {}).get('received', 0):,}
- **실패 메시지**: {status['websocket_status'].get('message_stats', {}).get('failed', 0):,}
- **평균 메시지 크기**: {status['websocket_status'].get('avg_message_size', 0):.1f} bytes
"""
        
        if status['health_issues']:
            report += "\n## 주의사항\n"
            for issue in status['health_issues']:
                report += f"- ⚠️ {issue}\n"
        
        return report


# 전역 인스턴스
performance_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """전역 성능 모니터 인스턴스 반환"""
    return performance_monitor


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 성능 모니터링 시스템 테스트 ===")
    
    monitor = PerformanceMonitor()
    
    # 알림 콜백 추가
    def alert_handler(alert):
        safe_print(f"🚨 알림: {alert['message']}")
    
    monitor.add_alert_callback(alert_handler)
    
    # 모니터링 시작
    monitor.start_monitoring()
    
    # 5초 동안 테스트
    safe_print("📊 5초간 모니터링 테스트...")
    time.sleep(5)
    
    # 상태 확인
    status = monitor.get_comprehensive_status()
    safe_print(f"\n시스템 상태: {status['overall_health']}")
    safe_print(f"CPU 사용률: {status['system_metrics'].get('cpu', {}).get('current', 0):.1f}%")
    safe_print(f"메모리 사용률: {status['system_metrics'].get('memory', {}).get('current', 0):.1f}%")
    
    # 보고서 저장
    report = monitor.export_performance_report()
    with open(f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", 'w', encoding='utf-8') as f:
        f.write(report)
    safe_print("📄 성능 보고서 저장 완료")
    
    # 모니터링 중지
    monitor.stop_monitoring()
    safe_print("🎯 성능 모니터링 테스트 완료!")