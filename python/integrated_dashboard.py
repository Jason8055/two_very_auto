#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
통합 대시보드 시스템
모든 정보를 실시간으로 표시하는 웹 기반 대시보드
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import asdict

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from main_integration_service import MainIntegrationService, get_integration_service
from realtime_ai_integration import RealtimeAIIntegrator, PredictionResult
from ipc_communication import IntegratedIPCManager
from enhanced_packet_decoder import BaccaratGameData

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
dashboard_app = FastAPI(
    title="Two Very Auto - 통합 대시보드",
    description="실시간 바카라 패킷 모니터링 및 AI 예측 대시보드",
    version="1.0.0"
)

# 템플릿 설정
templates = Jinja2Templates(directory="templates")

# WebSocket 연결 관리
class WebSocketManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
        """클라이언트 연결"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            'connected_at': datetime.now(),
            'client_info': client_info or {},
            'id': uuid.uuid4().hex
        }
        logger.info(f"WebSocket 클라이언트 연결: {len(self.active_connections)}개 연결")
    
    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_info:
            del self.connection_info[websocket]
        logger.info(f"WebSocket 클라이언트 연결 해제: {len(self.active_connections)}개 연결")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """개별 메시지 전송"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"개별 메시지 전송 실패: {e}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """모든 클라이언트에게 브로드캐스트"""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message, ensure_ascii=False)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"브로드캐스트 실패: {e}")
                disconnected.append(connection)
        
        # 실패한 연결 정리
        for connection in disconnected:
            self.disconnect(connection)


# 전역 WebSocket 매니저
websocket_manager = WebSocketManager()


class DashboardDataManager:
    """대시보드 데이터 관리자"""
    
    def __init__(self):
        self.realtime_data = {
            'system_status': {},
            'packet_stats': {},
            'ai_predictions': {},
            'table_data': {},
            'recent_games': [],
            'alerts': []
        }
        
        self.max_recent_games = 100
        self.max_alerts = 50
    
    def update_system_status(self, status: Dict[str, Any]):
        """시스템 상태 업데이트"""
        self.realtime_data['system_status'] = {
            **status,
            'last_update': datetime.now().isoformat()
        }
    
    def update_packet_stats(self, stats: Dict[str, Any]):
        """패킷 통계 업데이트"""
        self.realtime_data['packet_stats'] = {
            **stats,
            'last_update': datetime.now().isoformat()
        }
    
    def add_prediction(self, prediction: PredictionResult):
        """AI 예측 결과 추가"""
        prediction_dict = asdict(prediction)
        self.realtime_data['ai_predictions'][prediction.table_id] = prediction_dict
    
    def add_game_data(self, game_data: BaccaratGameData):
        """게임 데이터 추가"""
        game_dict = asdict(game_data)
        
        # 최근 게임 목록에 추가
        self.realtime_data['recent_games'].insert(0, game_dict)
        if len(self.realtime_data['recent_games']) > self.max_recent_games:
            self.realtime_data['recent_games'] = self.realtime_data['recent_games'][:self.max_recent_games]
        
        # 테이블 데이터 업데이트
        table_id = game_data.table_id
        if table_id not in self.realtime_data['table_data']:
            self.realtime_data['table_data'][table_id] = {
                'table_id': table_id,
                'game_count': 0,
                'player_wins': 0,
                'banker_wins': 0,
                'ties': 0,
                'player_pairs': 0,
                'banker_pairs': 0,
                'last_game': None
            }
        
        table_data = self.realtime_data['table_data'][table_id]
        table_data['game_count'] += 1
        table_data['last_game'] = game_dict
        
        # 승부 통계 업데이트
        if game_data.winner == 'Player':
            table_data['player_wins'] += 1
        elif game_data.winner == 'Banker':
            table_data['banker_wins'] += 1
        elif game_data.winner == 'Tie':
            table_data['ties'] += 1
        
        # 페어 통계 업데이트
        if game_data.player_pair:
            table_data['player_pairs'] += 1
        if game_data.banker_pair:
            table_data['banker_pairs'] += 1
    
    def add_alert(self, alert_type: str, message: str, severity: str = 'info'):
        """알림 추가"""
        alert = {
            'id': uuid.uuid4().hex,
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }
        
        self.realtime_data['alerts'].insert(0, alert)
        if len(self.realtime_data['alerts']) > self.max_alerts:
            self.realtime_data['alerts'] = self.realtime_data['alerts'][:self.max_alerts]
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """전체 대시보드 데이터 반환"""
        return {
            **self.realtime_data,
            'last_update': datetime.now().isoformat(),
            'connected_clients': len(websocket_manager.active_connections)
        }


# 전역 데이터 매니저
data_manager = DashboardDataManager()


class IntegratedDashboardController:
    """통합 대시보드 컨트롤러"""
    
    def __init__(self):
        self.integration_service = None
        self.ai_integrator = None
        self.ipc_manager = None
        self.is_running = False
        
        # 업데이트 태스크
        self.update_task = None
    
    async def start(self):
        """대시보드 컨트롤러 시작"""
        try:
            logger.info("통합 대시보드 컨트롤러 시작")
            
            # 통합 서비스 연결
            self.integration_service = get_integration_service()
            
            # AI 통합 시스템 초기화
            self.ai_integrator = RealtimeAIIntegrator()
            self.ai_integrator.add_prediction_callback(self._on_prediction_result)
            
            # IPC 매니저 초기화
            self.ipc_manager = IntegratedIPCManager()
            self.ipc_manager.register_handler('packet_data', self._handle_packet_data)
            self.ipc_manager.register_handler('ai_prediction', self._handle_ai_prediction)
            
            # 서비스들 시작
            if not self.ipc_manager.start():
                logger.error("IPC 매니저 시작 실패")
                return False
            
            if not self.ai_integrator.start(self.ipc_manager):
                logger.error("AI 통합 시스템 시작 실패")
                return False
            
            # 통합 서비스에 콜백 등록
            if self.integration_service:
                self.integration_service.add_event_callback('packet_processed', self._on_packet_processed)
                self.integration_service.add_event_callback('service_started', self._on_service_event)
                self.integration_service.add_event_callback('main_exe_started', self._on_service_event)
            
            self.is_running = True
            
            # 주기적 업데이트 태스크 시작
            self.update_task = asyncio.create_task(self._periodic_update())
            
            logger.info("✅ 통합 대시보드 컨트롤러 시작 완료")
            return True
        
        except Exception as e:
            logger.error(f"대시보드 컨트롤러 시작 실패: {e}")
            return False
    
    async def stop(self):
        """대시보드 컨트롤러 중지"""
        self.is_running = False
        
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        
        if self.ai_integrator:
            self.ai_integrator.stop()
        
        if self.ipc_manager:
            self.ipc_manager.stop()
        
        logger.info("통합 대시보드 컨트롤러 중지됨")
    
    def _on_packet_processed(self, event_data: Dict[str, Any]):
        """패킷 처리 이벤트 핸들러"""
        try:
            # 패킷 통계 업데이트
            data_manager.update_packet_stats({
                'total_processed': event_data.get('data_count', 0),
                'processing_time': event_data.get('processing_time', 0),
                'file_name': event_data.get('file_name', ''),
                'timestamp': event_data.get('timestamp', '')
            })
            
            # 실시간 브로드캐스트
            asyncio.create_task(websocket_manager.broadcast({
                'type': 'packet_processed',
                'data': event_data
            }))
        
        except Exception as e:
            logger.error(f"패킷 처리 이벤트 핸들러 오류: {e}")
    
    def _on_service_event(self, event_data: Dict[str, Any]):
        """서비스 이벤트 핸들러"""
        try:
            # 알림 추가
            data_manager.add_alert('system', f"서비스 이벤트: {event_data}", 'info')
            
            # 실시간 브로드캐스트
            asyncio.create_task(websocket_manager.broadcast({
                'type': 'service_event',
                'data': event_data
            }))
        
        except Exception as e:
            logger.error(f"서비스 이벤트 핸들러 오류: {e}")
    
    def _on_prediction_result(self, prediction: PredictionResult):
        """AI 예측 결과 핸들러"""
        try:
            # 예측 결과 저장
            data_manager.add_prediction(prediction)
            
            # 높은 확률의 페어 예측 시 알림
            if prediction.any_pair_probability > 0.3:
                data_manager.add_alert(
                    'prediction',
                    f"테이블 {prediction.table_id}: 페어 확률 {prediction.any_pair_probability:.1%}",
                    'warning'
                )
            
            # 실시간 브로드캐스트
            asyncio.create_task(websocket_manager.broadcast({
                'type': 'ai_prediction',
                'data': asdict(prediction)
            }))
        
        except Exception as e:
            logger.error(f"예측 결과 핸들러 오류: {e}")
    
    def _handle_packet_data(self, message):
        """IPC 패킷 데이터 핸들러"""
        try:
            # AI 통합 시스템으로 전달
            self.ai_integrator.process_packet_data('packet_data', message.data)
            return None
        
        except Exception as e:
            logger.error(f"IPC 패킷 데이터 핸들러 오류: {e}")
            return None
    
    def _handle_ai_prediction(self, message):
        """IPC AI 예측 핸들러"""
        try:
            prediction_data = message.data
            # 예측 결과를 PredictionResult로 변환하여 처리
            # (실제 구현 시 적절한 변환 로직 필요)
            return None
        
        except Exception as e:
            logger.error(f"IPC AI 예측 핸들러 오류: {e}")
            return None
    
    async def _periodic_update(self):
        """주기적 업데이트"""
        while self.is_running:
            try:
                # 시스템 상태 업데이트
                if self.integration_service:
                    status = self.integration_service.get_service_status()
                    data_manager.update_system_status(status)
                
                # AI 시스템 상태 업데이트
                if self.ai_integrator:
                    ai_status = self.ai_integrator.get_system_status()
                    data_manager.realtime_data['ai_status'] = ai_status
                
                # 전체 대시보드 데이터 브로드캐스트 (30초마다)
                dashboard_data = data_manager.get_dashboard_data()
                await websocket_manager.broadcast({
                    'type': 'dashboard_update',
                    'data': dashboard_data
                })
                
                await asyncio.sleep(30)  # 30초 간격
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"주기적 업데이트 오류: {e}")
                await asyncio.sleep(10)


# 전역 컨트롤러
dashboard_controller = IntegratedDashboardController()


# API 엔드포인트들
@dashboard_app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """대시보드 홈페이지"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@dashboard_app.get("/api/dashboard/data")
async def get_dashboard_data():
    """대시보드 데이터 API"""
    return JSONResponse(data_manager.get_dashboard_data())


@dashboard_app.get("/api/system/status")
async def get_system_status():
    """시스템 상태 API"""
    if dashboard_controller.integration_service:
        return JSONResponse(dashboard_controller.integration_service.get_service_status())
    return JSONResponse({"error": "Integration service not available"})


@dashboard_app.get("/api/ai/predictions/{table_id}")
async def get_table_predictions(table_id: str):
    """테이블별 AI 예측 API"""
    try:
        if dashboard_controller.ai_integrator:
            prediction = dashboard_controller.ai_integrator.get_prediction(table_id)
            if prediction:
                return JSONResponse(asdict(prediction))
        
        return JSONResponse({"error": "No prediction available"}, status_code=404)
    
    except Exception as e:
        logger.error(f"예측 조회 오류: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@dashboard_app.get("/api/tables/{table_id}/analysis")
async def get_table_analysis(table_id: str):
    """테이블 분석 API"""
    try:
        if dashboard_controller.ai_integrator:
            analysis = dashboard_controller.ai_integrator.get_table_analysis(table_id)
            return JSONResponse(analysis)
        
        return JSONResponse({"error": "AI integrator not available"}, status_code=503)
    
    except Exception as e:
        logger.error(f"테이블 분석 오류: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@dashboard_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 엔드포인트"""
    await websocket_manager.connect(websocket)
    
    try:
        # 연결 시 현재 데이터 전송
        dashboard_data = data_manager.get_dashboard_data()
        await websocket_manager.send_personal_message({
            'type': 'initial_data',
            'data': dashboard_data
        }, websocket)
        
        # 클라이언트 메시지 수신 루프
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 메시지 타입별 처리
            if message.get('type') == 'ping':
                await websocket_manager.send_personal_message({
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }, websocket)
            
            elif message.get('type') == 'get_prediction':
                table_id = message.get('table_id')
                if table_id and dashboard_controller.ai_integrator:
                    prediction = dashboard_controller.ai_integrator.get_prediction(table_id)
                    if prediction:
                        await websocket_manager.send_personal_message({
                            'type': 'prediction_result',
                            'data': asdict(prediction)
                        }, websocket)
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
        websocket_manager.disconnect(websocket)


# 대시보드 시작/중지 이벤트
@dashboard_app.on_event("startup")
async def startup_event():
    """대시보드 시작 이벤트"""
    logger.info("통합 대시보드 시작")
    await dashboard_controller.start()


@dashboard_app.on_event("shutdown")
async def shutdown_event():
    """대시보드 종료 이벤트"""
    logger.info("통합 대시보드 종료")
    await dashboard_controller.stop()


# 대시보드 HTML 템플릿 생성
def create_dashboard_template():
    """대시보드 HTML 템플릿 생성"""
    template_dir = Path("templates")
    template_dir.mkdir(exist_ok=True)
    
    dashboard_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Two Very Auto - 통합 대시보드</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .status-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .status-card h3 { color: #333; margin-bottom: 15px; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        .metric { display: flex; justify-content: space-between; padding: 8px 0; }
        .metric-value { font-weight: bold; color: #667eea; }
        .table-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .table-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .prediction-box { background: #f8f9ff; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #667eea; }
        .alert { padding: 10px; margin: 5px 0; border-radius: 5px; }
        .alert-info { background: #d1ecf1; color: #0c5460; }
        .alert-warning { background: #fff3cd; color: #856404; }
        .alert-success { background: #d4edda; color: #155724; }
        .connection-status { position: fixed; top: 10px; right: 10px; padding: 10px; border-radius: 5px; color: white; }
        .connected { background: #28a745; }
        .disconnected { background: #dc3545; }
        @media (max-width: 768px) { .status-grid, .table-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div id="connection-status" class="connection-status disconnected">연결 중...</div>
    
    <div class="container">
        <div class="header">
            <h1>🎯 Two Very Auto 통합 대시보드</h1>
            <p>실시간 바카라 패킷 모니터링 및 AI 예측 시스템</p>
        </div>
        
        <div class="status-grid">
            <div class="status-card">
                <h3>📊 시스템 상태</h3>
                <div id="system-status">
                    <div class="metric"><span>서비스 상태:</span><span class="metric-value" id="service-status">확인 중...</span></div>
                    <div class="metric"><span>업타임:</span><span class="metric-value" id="uptime">-</span></div>
                    <div class="metric"><span>Main 실행파일:</span><span class="metric-value" id="main-exe-status">-</span></div>
                    <div class="metric"><span>패킷 모니터:</span><span class="metric-value" id="packet-monitor-status">-</span></div>
                </div>
            </div>
            
            <div class="status-card">
                <h3>📦 패킷 통계</h3>
                <div id="packet-stats">
                    <div class="metric"><span>총 처리된 게임:</span><span class="metric-value" id="total-games">0</span></div>
                    <div class="metric"><span>활성 테이블:</span><span class="metric-value" id="active-tables">0</span></div>
                    <div class="metric"><span>평균 처리시간:</span><span class="metric-value" id="avg-processing-time">0ms</span></div>
                    <div class="metric"><span>마지막 업데이트:</span><span class="metric-value" id="last-packet-update">-</span></div>
                </div>
            </div>
            
            <div class="status-card">
                <h3>🤖 AI 예측 상태</h3>
                <div id="ai-stats">
                    <div class="metric"><span>총 예측 수행:</span><span class="metric-value" id="total-predictions">0</span></div>
                    <div class="metric"><span>캐시 적중률:</span><span class="metric-value" id="cache-hit-rate">0%</span></div>
                    <div class="metric"><span>평균 예측시간:</span><span class="metric-value" id="avg-prediction-time">0ms</span></div>
                    <div class="metric"><span>AI 모델:</span><span class="metric-value" id="ai-model-status">통계적</span></div>
                </div>
            </div>
            
            <div class="status-card">
                <h3>🚨 최근 알림</h3>
                <div id="recent-alerts" style="max-height: 200px; overflow-y: auto;">
                    <p>알림이 없습니다.</p>
                </div>
            </div>
        </div>
        
        <div class="table-grid" id="tables-container">
            <!-- 테이블 카드들이 여기에 동적으로 추가됩니다 -->
        </div>
    </div>

    <script>
        // WebSocket 연결
        const ws = new WebSocket(`ws://localhost:8000/ws`);
        const connectionStatus = document.getElementById('connection-status');
        
        ws.onopen = function() {
            connectionStatus.textContent = '🟢 연결됨';
            connectionStatus.className = 'connection-status connected';
        };
        
        ws.onclose = function() {
            connectionStatus.textContent = '🔴 연결 끊김';
            connectionStatus.className = 'connection-status disconnected';
        };
        
        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);
            handleMessage(message);
        };
        
        // 메시지 처리
        function handleMessage(message) {
            switch(message.type) {
                case 'initial_data':
                case 'dashboard_update':
                    updateDashboard(message.data);
                    break;
                case 'packet_processed':
                    updatePacketStats(message.data);
                    break;
                case 'ai_prediction':
                    updatePrediction(message.data);
                    break;
            }
        }
        
        // 대시보드 업데이트
        function updateDashboard(data) {
            // 시스템 상태 업데이트
            if (data.system_status) {
                const status = data.system_status;
                document.getElementById('service-status').textContent = status.service?.is_running ? '✅ 실행중' : '❌ 중지';
                document.getElementById('uptime').textContent = formatUptime(status.service?.uptime_seconds || 0);
                document.getElementById('main-exe-status').textContent = status.processes?.main_exe?.status || '알 수 없음';
                document.getElementById('packet-monitor-status').textContent = status.packet_monitor?.is_running ? '✅ 실행중' : '❌ 중지';
            }
            
            // AI 통계 업데이트
            if (data.ai_status?.ai_engine_stats) {
                const aiStats = data.ai_status.ai_engine_stats;
                document.getElementById('total-predictions').textContent = aiStats.total_predictions || 0;
                document.getElementById('cache-hit-rate').textContent = Math.round((aiStats.cache_hit_rate || 0) * 100) + '%';
                document.getElementById('avg-prediction-time').textContent = Math.round(aiStats.avg_prediction_time_ms || 0) + 'ms';
                document.getElementById('ai-model-status').textContent = aiStats.ai_model_available ? '🧠 딥러닝' : '📊 통계적';
            }
            
            // 알림 업데이트
            if (data.alerts) {
                updateAlerts(data.alerts);
            }
            
            // 테이블 데이터 업데이트
            if (data.table_data) {
                updateTables(data.table_data, data.ai_predictions);
            }
        }
        
        // 패킷 통계 업데이트
        function updatePacketStats(data) {
            document.getElementById('last-packet-update').textContent = new Date().toLocaleTimeString();
        }
        
        // 알림 업데이트
        function updateAlerts(alerts) {
            const alertsContainer = document.getElementById('recent-alerts');
            if (alerts.length === 0) {
                alertsContainer.innerHTML = '<p>알림이 없습니다.</p>';
                return;
            }
            
            const alertsHtml = alerts.slice(0, 5).map(alert => 
                `<div class="alert alert-${alert.severity}">
                    <strong>${alert.type}:</strong> ${alert.message}
                    <small>(${new Date(alert.timestamp).toLocaleTimeString()})</small>
                </div>`
            ).join('');
            
            alertsContainer.innerHTML = alertsHtml;
        }
        
        // 테이블 업데이트
        function updateTables(tableData, predictions = {}) {
            const container = document.getElementById('tables-container');
            container.innerHTML = '';
            
            Object.values(tableData).forEach(table => {
                const prediction = predictions[table.table_id];
                const tableCard = createTableCard(table, prediction);
                container.appendChild(tableCard);
            });
        }
        
        // 테이블 카드 생성
        function createTableCard(table, prediction) {
            const card = document.createElement('div');
            card.className = 'table-card';
            
            const totalGames = table.game_count || 0;
            const playerWinRate = totalGames > 0 ? Math.round((table.player_wins / totalGames) * 100) : 0;
            const bankerWinRate = totalGames > 0 ? Math.round((table.banker_wins / totalGames) * 100) : 0;
            
            card.innerHTML = `
                <h3>🎲 ${table.table_id}</h3>
                <div class="metric"><span>총 게임:</span><span class="metric-value">${totalGames}</span></div>
                <div class="metric"><span>플레이어 승률:</span><span class="metric-value">${playerWinRate}%</span></div>
                <div class="metric"><span>뱅커 승률:</span><span class="metric-value">${bankerWinRate}%</span></div>
                <div class="metric"><span>플레이어 페어:</span><span class="metric-value">${table.player_pairs || 0}</span></div>
                <div class="metric"><span>뱅커 페어:</span><span class="metric-value">${table.banker_pairs || 0}</span></div>
                
                ${prediction ? `
                    <div class="prediction-box">
                        <h4>🤖 AI 예측</h4>
                        <div class="metric"><span>페어 확률:</span><span class="metric-value">${Math.round(prediction.any_pair_probability * 100)}%</span></div>
                        <div class="metric"><span>플레이어 승률:</span><span class="metric-value">${Math.round(prediction.player_win_probability * 100)}%</span></div>
                        <div class="metric"><span>뱅커 승률:</span><span class="metric-value">${Math.round(prediction.banker_win_probability * 100)}%</span></div>
                        <div class="metric"><span>신뢰도:</span><span class="metric-value">${Math.round(prediction.confidence_score * 100)}%</span></div>
                    </div>
                ` : '<p style="color: #888;">예측 데이터 없음</p>'}
            `;
            
            return card;
        }
        
        // 유틸리티 함수
        function formatUptime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
        
        // 주기적 핑 전송
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'ping'}));
            }
        }, 30000);
    </script>
</body>
</html>
    """
    
    with open(template_dir / "dashboard.html", "w", encoding="utf-8") as f:
        f.write(dashboard_html)
    
    logger.info("대시보드 HTML 템플릿 생성 완료")


# 대시보드 서버 실행 함수
def run_dashboard_server(host: str = "0.0.0.0", port: int = 8000):
    """대시보드 서버 실행"""
    # 템플릿 생성
    create_dashboard_template()
    
    # 서버 실행
    uvicorn.run(
        dashboard_app,
        host=host,
        port=port,
        log_level="info",
        reload=False
    )


if __name__ == "__main__":
    # 단독 실행 시 대시보드 서버 시작
    run_dashboard_server()