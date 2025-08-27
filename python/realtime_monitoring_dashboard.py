#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
실시간 모니터링 대시보드 v1.0
성능 메트릭과 시스템 상태의 실시간 시각화
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Blueprint, jsonify, request
from korean_encoding_fix import setup_korean_encoding, safe_print
from performance_monitor import get_performance_monitor

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

# Blueprint 생성
monitoring_api = Blueprint('monitoring_api', __name__, url_prefix='/api/monitoring')


@monitoring_api.route('/metrics', methods=['GET'])
def get_current_metrics():
    """현재 시스템 메트릭 조회"""
    try:
        monitor = get_performance_monitor()
        current_metrics = monitor.get_current_status()
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'metrics': current_metrics
        })
        
    except Exception as e:
        logger.error(f"메트릭 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@monitoring_api.route('/history', methods=['GET'])
def get_metrics_history():
    """메트릭 히스토리 조회"""
    try:
        monitor = get_performance_monitor()
        hours = request.args.get('hours', 1, type=int)
        
        # 시간 범위 제한
        hours = min(hours, 24)
        
        history = monitor.get_metrics_history(hours)
        
        return jsonify({
            'success': True,
            'hours': hours,
            'history': history
        })
        
    except Exception as e:
        logger.error(f"히스토리 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@monitoring_api.route('/alerts', methods=['GET'])
def get_active_alerts():
    """현재 활성 알림 조회"""
    try:
        monitor = get_performance_monitor()
        alerts = monitor.get_active_alerts()
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        })
        
    except Exception as e:
        logger.error(f"알림 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@monitoring_api.route('/health', methods=['GET'])
def get_system_health():
    """시스템 전체 건강도 조회"""
    try:
        monitor = get_performance_monitor()
        health_status = monitor.get_system_health()
        
        return jsonify({
            'success': True,
            'health': health_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"건강도 조회 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@monitoring_api.route('/stats/summary', methods=['GET'])
def get_stats_summary():
    """통계 요약 정보 조회"""
    try:
        monitor = get_performance_monitor()
        
        # 24시간 통계
        summary = {
            'uptime': monitor.get_uptime_stats(),
            'performance': monitor.get_performance_summary(),
            'ai_stats': monitor.get_ai_performance_stats(),
            'websocket_stats': monitor.get_websocket_stats(),
            'database_stats': monitor.get_database_stats()
        }
        
        return jsonify({
            'success': True,
            'summary': summary,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"통계 요약 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@monitoring_api.route('/thresholds', methods=['GET', 'POST'])
def manage_thresholds():
    """성능 임계값 관리"""
    try:
        monitor = get_performance_monitor()
        
        if request.method == 'GET':
            thresholds = monitor.get_thresholds()
            return jsonify({
                'success': True,
                'thresholds': thresholds
            })
        
        elif request.method == 'POST':
            new_thresholds = request.get_json()
            success = monitor.update_thresholds(new_thresholds)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': '임계값이 업데이트되었습니다'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '임계값 업데이트에 실패했습니다'
                }), 400
                
    except Exception as e:
        logger.error(f"임계값 관리 실패: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# HTML 대시보드 템플릿
MONITORING_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>실시간 모니터링 대시보드</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Noto Sans KR', sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f6fa;
        }
        
        .dashboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .metric-title {
            font-size: 18px;
            font-weight: bold;
            color: #2f3640;
            margin-bottom: 15px;
        }
        
        .metric-value {
            font-size: 32px;
            font-weight: bold;
            color: #4834d4;
            margin-bottom: 5px;
        }
        
        .metric-unit {
            color: #57606f;
            font-size: 14px;
        }
        
        .alert-panel {
            background: #ff3838;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        
        .alert-panel.active {
            display: block;
        }
        
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-good { background: #2ed573; }
        .status-warning { background: #ffa502; }
        .status-critical { background: #ff3838; }
        
        .refresh-info {
            text-align: center;
            color: #57606f;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="dashboard-header">
        <h1>🖥️ Two Very Auto 실시간 모니터링</h1>
        <p>시스템 성능과 상태를 실시간으로 모니터링합니다</p>
    </div>
    
    <div class="alert-panel" id="alertPanel">
        <div id="alertContent"></div>
    </div>
    
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">
                <span class="status-indicator" id="cpuStatus"></span>
                CPU 사용률
            </div>
            <div class="metric-value" id="cpuValue">0</div>
            <div class="metric-unit">%</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">
                <span class="status-indicator" id="memoryStatus"></span>
                메모리 사용률
            </div>
            <div class="metric-value" id="memoryValue">0</div>
            <div class="metric-unit">%</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">
                <span class="status-indicator" id="gameStatus"></span>
                처리된 게임 수
            </div>
            <div class="metric-value" id="gameValue">0</div>
            <div class="metric-unit">게임</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">
                <span class="status-indicator" id="pairStatus"></span>
                감지된 페어 수
            </div>
            <div class="metric-value" id="pairValue">0</div>
            <div class="metric-unit">페어</div>
        </div>
    </div>
    
    <div class="chart-container">
        <h3>시스템 성능 트렌드</h3>
        <canvas id="performanceChart" width="400" height="200"></canvas>
    </div>
    
    <div class="chart-container">
        <h3>게임 처리 현황</h3>
        <canvas id="gameChart" width="400" height="200"></canvas>
    </div>
    
    <div class="refresh-info">
        마지막 업데이트: <span id="lastUpdate">-</span> | 5초마다 자동 갱신
    </div>

    <script>
        // 차트 초기화
        const performanceCtx = document.getElementById('performanceChart').getContext('2d');
        const performanceChart = new Chart(performanceCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU %',
                    data: [],
                    borderColor: '#4834d4',
                    backgroundColor: 'rgba(72, 52, 212, 0.1)',
                    tension: 0.4
                }, {
                    label: '메모리 %',
                    data: [],
                    borderColor: '#ff3838',
                    backgroundColor: 'rgba(255, 56, 56, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
        
        const gameCtx = document.getElementById('gameChart').getContext('2d');
        const gameChart = new Chart(gameCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: '게임 처리량',
                    data: [],
                    backgroundColor: '#2ed573',
                    borderColor: '#27ae60',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        // 상태 표시 함수
        function updateStatus(elementId, value, thresholds) {
            const element = document.getElementById(elementId);
            element.className = 'status-indicator';
            
            if (value < thresholds.good) {
                element.classList.add('status-good');
            } else if (value < thresholds.warning) {
                element.classList.add('status-warning');
            } else {
                element.classList.add('status-critical');
            }
        }
        
        // 데이터 업데이트 함수
        async function updateDashboard() {
            try {
                const response = await fetch('/api/monitoring/metrics');
                const data = await response.json();
                
                if (data.success) {
                    const metrics = data.metrics;
                    
                    // 메트릭 값 업데이트
                    document.getElementById('cpuValue').textContent = metrics.cpu_percent.toFixed(1);
                    document.getElementById('memoryValue').textContent = metrics.memory_percent.toFixed(1);
                    document.getElementById('gameValue').textContent = metrics.games_processed || 0;
                    document.getElementById('pairValue').textContent = metrics.pairs_detected || 0;
                    
                    // 상태 표시기 업데이트
                    updateStatus('cpuStatus', metrics.cpu_percent, {good: 50, warning: 80});
                    updateStatus('memoryStatus', metrics.memory_percent, {good: 60, warning: 80});
                    
                    // 차트 데이터 업데이트
                    const now = new Date().toLocaleTimeString();
                    
                    if (performanceChart.data.labels.length > 20) {
                        performanceChart.data.labels.shift();
                        performanceChart.data.datasets[0].data.shift();
                        performanceChart.data.datasets[1].data.shift();
                    }
                    
                    performanceChart.data.labels.push(now);
                    performanceChart.data.datasets[0].data.push(metrics.cpu_percent);
                    performanceChart.data.datasets[1].data.push(metrics.memory_percent);
                    performanceChart.update();
                    
                    // 마지막 업데이트 시간
                    document.getElementById('lastUpdate').textContent = now;
                }
                
                // 알림 확인
                const alertResponse = await fetch('/api/monitoring/alerts');
                const alertData = await alertResponse.json();
                
                if (alertData.success && alertData.alerts.length > 0) {
                    const alertPanel = document.getElementById('alertPanel');
                    const alertContent = document.getElementById('alertContent');
                    alertContent.innerHTML = alertData.alerts.map(alert => 
                        `<strong>${alert.type}:</strong> ${alert.message}`
                    ).join('<br>');
                    alertPanel.classList.add('active');
                } else {
                    document.getElementById('alertPanel').classList.remove('active');
                }
                
            } catch (error) {
                console.error('대시보드 업데이트 실패:', error);
            }
        }
        
        // 5초마다 업데이트
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
"""


@monitoring_api.route('/dashboard', methods=['GET'])
def get_monitoring_dashboard():
    """모니터링 대시보드 HTML 페이지 반환"""
    from flask import render_template_string
    return render_template_string(MONITORING_DASHBOARD_TEMPLATE)


def register_monitoring_api(app):
    """Flask 앱에 모니터링 API 등록"""
    app.register_blueprint(monitoring_api)
    safe_print("✅ 실시간 모니터링 API 등록 완료")


if __name__ == "__main__":
    safe_print("🖥️ 실시간 모니터링 대시보드 테스트")
    # 개발용 테스트 코드 실행