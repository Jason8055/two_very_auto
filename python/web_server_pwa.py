#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto - PWA Web Server v2.0
SQLite + WebSocket + ML + PWA 통합 시스템
"""

# 표준 라이브러리
import json
import logging
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# 서드파티 라이브러리
from flask import Flask, jsonify, render_template_string, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO

# Windows 환경에서 UTF-8 인코딩 문제 해결
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        pass

# 로컬 모듈
from korean_encoding_fix import setup_korean_encoding, safe_print
from packet_decoder import BaccaratPacketDecoder, DemoDataGenerator
from pair_tracker_v2 import PairTrackerV2
from database_manager import DatabaseManager
from websocket_manager import WebSocketManager
from pattern_analyzer_v2 import PatternAnalyzerV2
from notification_system import NotificationSystem
# from advanced_notification_system import get_notification_system  # 🚫 AsyncIO 충돌 방지
from chart_integration import get_chart_processor, get_chart_websocket_handler
from realtime_dashboard import get_realtime_dashboard
from ai_prediction_engine import get_ai_prediction_engine

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask 앱 생성
app = Flask(__name__)
app.config['SECRET_KEY'] = 'two-very-auto-pwa-v2-secret-2024'
CORS(app, origins="*")
# SocketIO 임시 비활성화로 asyncio 충돌 테스트
logger.info("SocketIO 임시 비활성화 - asyncio 충돌 테스트")
socketio = None
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', 
#                    ping_timeout=30, ping_interval=10)

# PWA 전용 보안 헤더
@app.after_request
def add_pwa_headers(response):
    """PWA를 위한 보안 헤더 추가"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # PWA에 최적화된 CSP
    response.headers['Content-Security-Policy'] = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.socket.io https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' ws: wss:; "
        "manifest-src 'self';"
    )
    
    # PWA 캐싱 헤더
    if request.endpoint in ['pwa_manifest', 'pwa_service_worker']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    elif 'api' in request.path:
        response.headers['Cache-Control'] = 'no-cache'
    else:
        response.headers['Cache-Control'] = 'public, max-age=3600'
    
    return response

# 전역 객체 초기화
decoder = BaccaratPacketDecoder()
tracker = PairTrackerV2("baccarat_monitor_pwa_v2.db")
db_manager = DatabaseManager("baccarat_monitor_pwa_v2.db")
pattern_analyzer = PatternAnalyzerV2(db_manager)
notification_system = NotificationSystem()
advanced_notification = None  # 🚫 AsyncIO 충돌 방지로 완전 비활성화
chart_processor = get_chart_processor()
chart_ws_handler = get_chart_websocket_handler()
realtime_dashboard = get_realtime_dashboard()
ai_engine = get_ai_prediction_engine()
ws_manager = WebSocketManager(socketio) if socketio else None

# 🚫 고급 알림 시스템 완전 비활성화 (AsyncIO 충돌 방지)
logger.info("🚫 고급 알림 시스템 완전 비활성화 - AsyncIO 충돌 방지")
# if ws_manager:
#     advanced_notification.set_websocket_manager(ws_manager)  # 비활성화

# 새로운 API 기능들 통합
from api_integration_patch import apply_api_integration_patch
api_patch_success = apply_api_integration_patch(app)

# 멀티 카지노 관리자 초기화
from multi_casino_manager import get_multi_casino_manager
multi_casino_manager = get_multi_casino_manager()
multi_casino_manager.start_monitoring()

# 사용자 알림 프로필 시스템 초기화
from user_notification_profiles import get_notification_manager
notification_profile_manager = get_notification_manager()

safe_print("🚀 Two Very Auto v3.0 고급 기능 통합 완료")
if api_patch_success:
    safe_print("✅ 모든 API 패치 성공적으로 적용됨")
else:
    safe_print("⚠️ 일부 API 패치 적용 실패")

# PWA 전용 HTML 템플릿
PWA_DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="ko" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="Baccarat Monitor">
    
    <!-- PWA Meta Tags -->
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTkyIiBoZWlnaHQ9IjE5MiIgdmlld0JveD0iMCAwIDE5MiAxOTIiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjE5MiIgaGVpZ2h0PSIxOTIiIHJ4PSIyNCIgZmlsbD0iIzRmNDZlNSIvPjwvc3ZnPg==">
    <meta name="theme-color" content="#4f46e5">
    
    <title>Baccarat Monitor v2.0 - PWA</title>
    
    <!-- External Resources -->
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    <script src="https://unpkg.com/feather-icons"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    
    <style>
        /* PWA 최적화 CSS */
        :root {
            --primary-color: #4f46e5;
            --bg-light: #f8fafc;
            --bg-dark: #0f1419;
            --surface-light: #ffffff;
            --surface-dark: #1a1f2e;
            --text-light: #1f2937;
            --text-dark: #f9fafb;
            --border-light: #e5e7eb;
            --border-dark: #374151;
        }
        
        [data-theme="light"] {
            --bg-color: var(--bg-light);
            --surface-color: var(--surface-light);
            --text-color: var(--text-light);
            --border-color: var(--border-light);
        }
        
        [data-theme="dark"] {
            --bg-color: var(--bg-dark);
            --surface-color: var(--surface-dark);
            --text-color: var(--text-dark);
            --border-color: var(--border-dark);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            transition: all 0.3s ease;
            user-select: none;
            -webkit-user-select: none;
            -webkit-touch-callout: none;
            -webkit-tap-highlight-color: transparent;
        }
        
        /* PWA 안전 영역 */
        .safe-area {
            padding-left: env(safe-area-inset-left);
            padding-right: env(safe-area-inset-right);
            padding-top: env(safe-area-inset-top);
            padding-bottom: env(safe-area-inset-bottom);
        }
        
        .container {
            max-width: 100%;
            margin: 0 auto;
            padding: 10px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        /* 모바일 친화적 헤더 */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: var(--surface-color);
            border-radius: 12px;
            margin-bottom: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            position: sticky;
            top: 10px;
            z-index: 100;
        }
        
        .title {
            font-size: 18px;
            font-weight: 700;
            color: var(--primary-color);
        }
        
        .version-badge {
            background: var(--primary-color);
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10px;
            margin-left: 8px;
        }
        
        /* 컨트롤 버튼 */
        .controls {
            display: flex;
            gap: 8px;
        }
        
        .btn {
            padding: 8px 12px;
            border: none;
            border-radius: 8px;
            background: var(--primary-color);
            color: white;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 4px;
            touch-action: manipulation;
        }
        
        .btn:hover, .btn:active {
            opacity: 0.9;
            transform: scale(0.98);
        }
        
        .btn-icon {
            width: 16px;
            height: 16px;
        }
        
        .btn-secondary {
            background: var(--border-color);
            color: var(--text-color);
        }
        
        /* 반응형 메트릭 그리드 */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .metric-card {
            background: var(--surface-color);
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .metric-card:active {
            transform: scale(0.98);
        }
        
        .metric-value {
            font-size: 24px;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 4px;
        }
        
        .metric-label {
            font-size: 11px;
            color: var(--text-color);
            opacity: 0.7;
        }
        
        .metric-change {
            font-size: 10px;
            margin-top: 4px;
        }
        
        .metric-change.positive {
            color: #10b981;
        }
        
        .metric-change.negative {
            color: #ef4444;
        }
        
        /* 테이블 섹션 */
        .tables-section {
            flex: 1;
            background: var(--surface-color);
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .section-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 15px;
            color: var(--text-color);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .tables-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 12px;
        }
        
        @media (max-width: 768px) {
            .tables-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .table-card {
            padding: 15px;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            background: var(--bg-color);
            transition: all 0.2s ease;
            position: relative;
        }
        
        .table-card:active {
            transform: scale(0.98);
            border-color: var(--primary-color);
        }
        
        .table-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .table-name {
            font-weight: 600;
            font-size: 14px;
            color: var(--text-color);
        }
        
        .table-status {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
        }
        
        .table-status.inactive {
            background: #6b7280;
        }
        
        .table-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            font-size: 12px;
        }
        
        .table-stat {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
        }
        
        .table-stat-label {
            opacity: 0.7;
        }
        
        .table-stat-value {
            font-weight: 600;
            color: var(--primary-color);
        }
        
        /* 상태 표시기 */
        .status-indicator {
            position: fixed;
            top: env(safe-area-inset-top, 20px);
            right: env(safe-area-inset-right, 20px);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 500;
            z-index: 1000;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }
        
        .status-online {
            background: rgba(16, 185, 129, 0.9);
            color: white;
        }
        
        .status-offline {
            background: rgba(239, 68, 68, 0.9);
            color: white;
        }
        
        /* 토스트 알림 */
        .toast-container {
            position: fixed;
            top: env(safe-area-inset-top, 60px);
            right: env(safe-area-inset-right, 20px);
            z-index: 1001;
            max-width: 300px;
        }
        
        .toast {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
            transform: translateX(100%);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .toast.show {
            transform: translateX(0);
        }
        
        .toast.success {
            border-left: 4px solid #10b981;
        }
        
        .toast.error {
            border-left: 4px solid #ef4444;
        }
        
        .toast.info {
            border-left: 4px solid #3b82f6;
        }
        
        .toast-title {
            font-weight: 600;
            font-size: 12px;
            margin-bottom: 4px;
        }
        
        .toast-message {
            font-size: 11px;
            opacity: 0.8;
        }
        
        /* 풀업 새로고침 */
        .pull-to-refresh {
            position: absolute;
            top: -60px;
            left: 50%;
            transform: translateX(-50%);
            padding: 15px;
            background: var(--surface-color);
            border-radius: 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            z-index: 200;
        }
        
        .pull-to-refresh.active {
            top: 20px;
        }
        
        /* 애니메이션 */
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.05); opacity: 0.8; }
        }
        
        .pulse-animation {
            animation: pulse 1.5s ease-in-out;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        .spin {
            animation: spin 1s linear infinite;
        }
        
        /* AI 섹션 스타일 */
        .ai-section {
            margin: 20px 0;
        }
        
        .ai-dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 16px;
        }
        
        .ai-status-card, .ai-prediction-card, .ai-training-card {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease;
        }
        
        .ai-status-card:hover, .ai-prediction-card:hover, .ai-training-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        
        .ai-status-header, .prediction-header, .training-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        
        .ai-status-title, .prediction-title, .training-title {
            font-weight: 600;
            color: var(--text-color);
        }
        
        .ai-status-indicator {
            font-size: 0.875rem;
            font-weight: 500;
            padding: 4px 8px;
            border-radius: 6px;
            background: var(--bg-light);
        }
        
        .ai-status-indicator.active {
            background: rgba(16, 185, 129, 0.1);
            color: #10b981;
        }
        
        .ai-status-indicator.pending {
            background: rgba(245, 158, 11, 0.1);
            color: #f59e0b;
        }
        
        .ai-status-indicator.statistical {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
        }
        
        .ai-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
        }
        
        .ai-metric {
            text-align: center;
        }
        
        .ai-metric-label {
            display: block;
            font-size: 0.75rem;
            color: var(--text-color);
            opacity: 0.7;
            margin-bottom: 4px;
        }
        
        .ai-metric-value {
            display: block;
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--primary-color);
        }
        
        .prediction-results {
            min-height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .prediction-placeholder {
            color: var(--text-color);
            opacity: 0.6;
            text-align: center;
            font-style: italic;
        }
        
        .prediction-result {
            width: 100%;
        }
        
        .prediction-main {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        
        .prediction-type {
            font-size: 1.25rem;
            font-weight: 600;
            padding: 8px 16px;
            border-radius: 8px;
        }
        
        .prediction-type.no_pair {
            background: rgba(148, 163, 184, 0.1);
            color: #64748b;
        }
        
        .prediction-type.player_pair {
            background: rgba(16, 185, 129, 0.1);
            color: #10b981;
        }
        
        .prediction-type.banker_pair {
            background: rgba(59, 130, 246, 0.1);
            color: #3b82f6;
        }
        
        .prediction-type.both_pair {
            background: rgba(245, 158, 11, 0.1);
            color: #f59e0b;
        }
        
        .prediction-confidence {
            font-weight: 600;
            color: var(--primary-color);
        }
        
        .prediction-probabilities {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin-bottom: 16px;
        }
        
        .prob-item {
            display: flex;
            justify-content: space-between;
            padding: 8px;
            background: var(--bg-light);
            border-radius: 6px;
            font-size: 0.875rem;
        }
        
        .prob-label {
            color: var(--text-color);
        }
        
        .prob-value {
            font-weight: 600;
            color: var(--primary-color);
        }
        
        .prediction-meta {
            display: flex;
            justify-content: space-between;
            padding-top: 12px;
            border-top: 1px solid var(--border-color);
        }
        
        .prediction-meta small {
            color: var(--text-color);
            opacity: 0.7;
        }
        
        .training-info {
            color: var(--text-color);
            opacity: 0.8;
            margin-bottom: 16px;
        }
        
        .training-progress {
            margin-top: 16px;
        }
        
        .progress-bar {
            width: 100%;
            height: 6px;
            background: var(--bg-light);
            border-radius: 3px;
            overflow: hidden;
            margin-bottom: 8px;
        }
        
        .progress-fill {
            height: 100%;
            background: var(--primary-color);
            border-radius: 3px;
            animation: progressAnimation 2s ease-in-out infinite;
        }
        
        .progress-text {
            text-align: center;
            font-size: 0.875rem;
            color: var(--text-color);
            opacity: 0.8;
        }
        
        @keyframes progressAnimation {
            0% { width: 0%; }
            50% { width: 70%; }
            100% { width: 100%; }
        }
        
        @media (max-width: 768px) {
            .ai-dashboard {
                grid-template-columns: 1fr;
            }
            
            .ai-metrics {
                grid-template-columns: 1fr;
                gap: 12px;
            }
            
            .prediction-probabilities {
                grid-template-columns: 1fr;
            }
            
            .prediction-main {
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }
        }
        
        /* 오프라인 표시 */
        .offline-banner {
            position: fixed;
            bottom: env(safe-area-inset-bottom, 0);
            left: 0;
            right: 0;
            background: #fbbf24;
            color: #92400e;
            text-align: center;
            padding: 8px;
            font-size: 12px;
            font-weight: 500;
            transform: translateY(100%);
            transition: transform 0.3s ease;
            z-index: 1000;
        }
        
        .offline-banner.show {
            transform: translateY(0);
        }
        
        /* 빈 상태 */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            opacity: 0.6;
        }
        
        .empty-state svg {
            width: 48px;
            height: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        }
        
        .empty-state h3 {
            font-size: 16px;
            margin-bottom: 8px;
        }
        
        .empty-state p {
            font-size: 12px;
            margin-bottom: 16px;
        }
        
        /* 로딩 상태 */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            backdrop-filter: blur(5px);
        }
        
        .loading-spinner {
            width: 40px;
            height: 40px;
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        /* PWA 설치 프롬프트 */
        .install-prompt {
            position: fixed;
            bottom: env(safe-area-inset-bottom, 20px);
            left: 20px;
            right: 20px;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            transform: translateY(100%);
            transition: all 0.3s ease;
            z-index: 1000;
        }
        
        .install-prompt.show {
            transform: translateY(0);
        }
        
        .install-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 15px;
        }
        
        .install-text {
            flex: 1;
        }
        
        .install-title {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 4px;
        }
        
        .install-desc {
            font-size: 12px;
            opacity: 0.7;
        }
        
        .install-actions {
            display: flex;
            gap: 8px;
        }
        
        .install-btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .install-btn.primary {
            background: var(--primary-color);
            color: white;
        }
        
        .install-btn.secondary {
            background: transparent;
            color: var(--text-color);
            border: 1px solid var(--border-color);
        }
    </style>
</head>
<body class="safe-area">
    <!-- 상태 표시기 -->
    <div class="status-indicator" id="connection-status">🔄 연결 중...</div>
    
    <!-- 토스트 컨테이너 -->
    <div class="toast-container" id="toast-container"></div>
    
    <!-- 오프라인 배너 -->
    <div class="offline-banner" id="offline-banner">
        📡 오프라인 모드 - 캐시된 데이터를 표시 중입니다
    </div>
    
    <!-- PWA 설치 프롬프트 -->
    <div class="install-prompt" id="install-prompt">
        <div class="install-content">
            <div class="install-text">
                <div class="install-title">앱으로 설치하기</div>
                <div class="install-desc">홈 화면에 추가하여 더 편리하게 사용하세요</div>
            </div>
            <div class="install-actions">
                <button class="install-btn primary" id="install-btn">설치</button>
                <button class="install-btn secondary" id="dismiss-install">나중에</button>
            </div>
        </div>
    </div>
    
    <!-- 로딩 오버레이 -->
    <div class="loading-overlay" id="loading-overlay" style="display: none;">
        <div class="loading-spinner"></div>
    </div>
    
    <!-- 풀투리프레시 -->
    <div class="pull-to-refresh" id="pull-to-refresh">
        <i data-feather="refresh-cw" class="spin"></i>
        새로고침하려면 당겨주세요
    </div>
    
    <div class="container">
        <!-- 헤더 -->
        <header class="header">
            <div>
                <h1 class="title">
                    Baccarat Monitor
                    <span class="version-badge">v2.0</span>
                </h1>
                <div id="last-update" style="font-size: 10px; opacity: 0.6; margin-top: 2px;"></div>
            </div>
            <div class="controls">
                <button class="btn btn-secondary" onclick="toggleTheme()" id="theme-btn" title="테마 변경">
                    <i data-feather="sun" id="theme-icon" class="btn-icon"></i>
                </button>
                <button class="btn" onclick="refreshData()" title="새로고침">
                    <i data-feather="refresh-cw" class="btn-icon"></i>
                </button>
                <button class="btn" onclick="addDemoData()" title="데모 데이터">
                    <i data-feather="plus" class="btn-icon"></i>
                </button>
            </div>
        </header>
        
        <!-- 메트릭 그리드 -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value" id="total-games">{{ global_stats.total_games or 0 }}</div>
                <div class="metric-label">전체 게임</div>
                <div class="metric-change" id="games-change"></div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="total-pairs">{{ global_stats.total_pairs or 0 }}</div>
                <div class="metric-label">총 페어</div>
                <div class="metric-change" id="pairs-change"></div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="active-tables">{{ active_tables or 0 }}</div>
                <div class="metric-label">활성 테이블</div>
                <div class="metric-change" id="tables-change"></div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="pair-rate">
                    {% if global_stats.total_games and global_stats.total_games > 0 %}
                        {{ "%.1f"|format((global_stats.total_pairs or 0) / global_stats.total_games * 100) }}%
                    {% else %}
                        0.0%
                    {% endif %}
                </div>
                <div class="metric-label">페어율</div>
                <div class="metric-change" id="rate-change"></div>
            </div>
        </div>
        
        <!-- 테이블 섹션 -->
        <section class="tables-section">
            <h2 class="section-title">
                <i data-feather="grid" style="width: 20px; height: 20px;"></i>
                테이블 현황
                <span style="margin-left: auto; font-size: 12px; opacity: 0.6;" id="table-count">
                    {{ tables|length if tables else 0 }}개 테이블
                </span>
            </h2>
            
            <div class="tables-grid" id="tables-grid">
                {% if tables %}
                    {% for table_name, table_info in tables.items() %}
                    <div class="table-card" data-table="{{ table_name }}">
                        <div class="table-header">
                            <div class="table-name">{{ table_name }}</div>
                            <div class="table-status" title="활성 상태"></div>
                        </div>
                        <div class="table-stats">
                            <div class="table-stat">
                                <span class="table-stat-label">게임</span>
                                <span class="table-stat-value">{{ table_info.total_games }}</span>
                            </div>
                            <div class="table-stat">
                                <span class="table-stat-label">페어</span>
                                <span class="table-stat-value">{{ table_info.pair_count }}</span>
                            </div>
                            <div class="table-stat">
                                <span class="table-stat-label">페어율</span>
                                <span class="table-stat-value">{{ "%.1f"|format(table_info.statistics.pair_rate * 100) }}%</span>
                            </div>
                            <div class="table-stat">
                                <span class="table-stat-label">마지막 페어 이후</span>
                                <span class="table-stat-value">{{ table_info.games_since_last_pair }}게임</span>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <i data-feather="database" style="width: 48px; height: 48px; margin-bottom: 16px; opacity: 0.5;"></i>
                        <h3>테이블 데이터가 없습니다</h3>
                        <p>데모 데이터를 추가해서 시작해보세요</p>
                        <button class="btn" onclick="addDemoData()">
                            <i data-feather="plus" class="btn-icon"></i>
                            데모 데이터 추가
                        </button>
                    </div>
                {% endif %}
            </div>
        </section>
        
        <!-- 차트 및 시각화 섹션 -->
        <section class="charts-section">
            <h2 class="section-title">
                <i data-feather="bar-chart-2" style="width: 20px; height: 20px;"></i>
                실시간 시각화 대시보드
            </h2>
            
            <!-- 차트 컨테이너가 동적으로 여기에 추가됩니다 -->
            <div id="charts-container"></div>
        </section>
        
        <!-- AI 예측 섹션 -->
        <section class="ai-section">
            <h2 class="section-title">
                <i data-feather="brain" style="width: 20px; height: 20px;"></i>
                AI 페어 예측 시스템
            </h2>
            
            <div class="ai-dashboard">
                <!-- AI 모델 상태 -->
                <div class="ai-status-card">
                    <div class="ai-status-header">
                        <div class="ai-status-title">모델 상태</div>
                        <div class="ai-status-indicator" id="ai-status">🧠 로딩 중...</div>
                    </div>
                    <div class="ai-metrics">
                        <div class="ai-metric">
                            <span class="ai-metric-label">정확도</span>
                            <span class="ai-metric-value" id="ai-accuracy">-</span>
                        </div>
                        <div class="ai-metric">
                            <span class="ai-metric-label">예측 수</span>
                            <span class="ai-metric-value" id="ai-predictions">-</span>
                        </div>
                        <div class="ai-metric">
                            <span class="ai-metric-label">방법</span>
                            <span class="ai-metric-value" id="ai-method">-</span>
                        </div>
                    </div>
                </div>
                
                <!-- 실시간 예측 결과 -->
                <div class="ai-prediction-card">
                    <div class="prediction-header">
                        <div class="prediction-title">실시간 예측</div>
                        <button class="btn btn-sm" onclick="requestAIPrediction()">
                            <i data-feather="zap" class="btn-icon"></i>
                            예측 요청
                        </button>
                    </div>
                    <div class="prediction-results" id="prediction-results">
                        <div class="prediction-placeholder">
                            AI 예측 결과가 여기에 표시됩니다
                        </div>
                    </div>
                </div>
                
                <!-- AI 훈련 컨트롤 -->
                <div class="ai-training-card">
                    <div class="training-header">
                        <div class="training-title">모델 훈련</div>
                        <button class="btn btn-secondary" onclick="trainAIModel()">
                            <i data-feather="cpu" class="btn-icon"></i>
                            훈련 시작
                        </button>
                    </div>
                    <div class="training-status" id="training-status">
                        <div class="training-info">최신 데이터로 AI 모델을 재훈련할 수 있습니다</div>
                        <div class="training-progress" id="training-progress" style="display: none;">
                            <div class="progress-bar">
                                <div class="progress-fill"></div>
                            </div>
                            <div class="progress-text">훈련 중...</div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    </div>
    
    <script>
        // PWA 및 Service Worker 등록
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js')
                    .then(registration => {
                        console.log('SW registered: ', registration);
                    })
                    .catch(registrationError => {
                        console.log('SW registration failed: ', registrationError);
                    });
            });
        }
        
        // PWA 설치 프롬프트
        let deferredPrompt;
        let installPromptShown = false;
        
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            
            // 나중에 설치 프롬프트 표시
            if (!installPromptShown) {
                setTimeout(() => {
                    showInstallPrompt();
                }, 5000); // 5초 후 표시
            }
        });
        
        function showInstallPrompt() {
            const installPrompt = document.getElementById('install-prompt');
            if (installPrompt && deferredPrompt) {
                installPrompt.classList.add('show');
                installPromptShown = true;
            }
        }
        
        document.getElementById('install-btn').addEventListener('click', () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choiceResult) => {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('User accepted the A2HS prompt');
                        showToast('설치됨', '앱이 홈 화면에 추가되었습니다', 'success');
                    }
                    deferredPrompt = null;
                    hideInstallPrompt();
                });
            }
        });
        
        document.getElementById('dismiss-install').addEventListener('click', () => {
            hideInstallPrompt();
        });
        
        function hideInstallPrompt() {
            const installPrompt = document.getElementById('install-prompt');
            if (installPrompt) {
                installPrompt.classList.remove('show');
            }
        }
        
        // WebSocket 연결
        const socket = io();
        let currentTheme = localStorage.getItem('theme') || 'light';
        let isOnline = navigator.onLine;
        let lastData = null;
        
        // 테마 초기화
        document.documentElement.setAttribute('data-theme', currentTheme);
        updateThemeIcon();
        
        // 네트워크 상태 감지
        window.addEventListener('online', () => {
            isOnline = true;
            hideOfflineBanner();
            showToast('연결됨', '인터넷 연결이 복구되었습니다', 'success');
        });
        
        window.addEventListener('offline', () => {
            isOnline = false;
            showOfflineBanner();
            showToast('오프라인', '오프라인 모드로 전환됩니다', 'info');
        });
        
        // WebSocket 이벤트
        socket.on('connect', () => {
            console.log('✅ Connected to server');
            updateConnectionStatus('online');
            showToast('연결됨', 'WebSocket 연결 성공', 'success');
        });
        
        socket.on('disconnect', () => {
            console.log('❌ Disconnected from server');
            updateConnectionStatus('offline');
            if (isOnline) {
                showToast('연결 해제', '서버와의 연결이 끊어졌습니다', 'error');
            }
        });
        
        socket.on('connection_established', (data) => {
            console.log('🔗 Connection established:', data);
            socket.emit('subscribe', { type: 'pair_alerts' });
            socket.emit('subscribe', { type: 'stats_update' });
        });
        
        socket.on('pair_alert', (data) => {
            console.log('🎯 Pair Alert:', data);
            showToast('페어 발생!', data.message, 'success');
            
            // 햅틱 피드백 (지원하는 경우)
            if ('vibrate' in navigator) {
                navigator.vibrate([100, 50, 100]);
            }
            
            // 시각적 효과
            const pairCard = document.getElementById('total-pairs');
            if (pairCard) {
                pairCard.parentElement.classList.add('pulse-animation');
                setTimeout(() => pairCard.parentElement.classList.remove('pulse-animation'), 2000);
            }
            
            // 데이터 자동 새로고침
            setTimeout(refreshData, 1000);
        });
        
        socket.on('stats_update', (data) => {
            console.log('📊 Stats Update:', data);
            updateDashboard(data.stats);
            updateLastUpdateTime();
        });
        
        // 풀투리프레시 구현
        let startY = 0;
        let isDragging = false;
        let pullDistance = 0;
        const pullThreshold = 60;
        
        document.addEventListener('touchstart', (e) => {
            if (window.scrollY === 0) {
                startY = e.touches[0].pageY;
                isDragging = true;
            }
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            
            const currentY = e.touches[0].pageY;
            pullDistance = Math.max(0, currentY - startY);
            
            if (pullDistance > 0) {
                e.preventDefault();
                const pullProgress = Math.min(pullDistance / pullThreshold, 1);
                const pullElement = document.getElementById('pull-to-refresh');
                
                if (pullElement) {
                    if (pullDistance > pullThreshold) {
                        pullElement.classList.add('active');
                    } else {
                        pullElement.classList.remove('active');
                    }
                }
            }
        }, { passive: false });
        
        document.addEventListener('touchend', () => {
            if (isDragging && pullDistance > pullThreshold) {
                refreshData();
                showToast('새로고침', '최신 데이터를 불러옵니다', 'info');
            }
            
            const pullElement = document.getElementById('pull-to-refresh');
            if (pullElement) {
                pullElement.classList.remove('active');
            }
            
            isDragging = false;
            pullDistance = 0;
        }, { passive: true });
        
        // 함수들
        function updateDashboard(data) {
            if (data.global_stats) {
                const prevData = lastData ? lastData.global_stats : null;
                
                updateElement('total-games', data.global_stats.total_games || 0);
                updateElement('total-pairs', data.global_stats.total_pairs || 0);
                updateElement('active-tables', data.active_tables || 0);
                
                // 변화량 표시
                if (prevData) {
                    updateChange('games-change', data.global_stats.total_games - prevData.total_games);
                    updateChange('pairs-change', data.global_stats.total_pairs - prevData.total_pairs);
                }
                
                // 페어율 계산
                if (data.global_stats.total_games > 0) {
                    const rate = ((data.global_stats.total_pairs || 0) / data.global_stats.total_games * 100).toFixed(1);
                    updateElement('pair-rate', rate + '%');
                }
            }
            
            // 테이블 정보 업데이트
            updateTablesGrid(data.tables || {});
            
            lastData = data;
        }
        
        function updateElement(id, value) {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = typeof value === 'number' ? value.toLocaleString() : value;
            }
        }
        
        function updateChange(id, change) {
            const element = document.getElementById(id);
            if (element && change !== 0) {
                element.textContent = change > 0 ? `+${change}` : `${change}`;
                element.className = `metric-change ${change > 0 ? 'positive' : 'negative'}`;
            }
        }
        
        function updateTablesGrid(tables) {
            const grid = document.getElementById('tables-grid');
            const countElement = document.getElementById('table-count');
            
            if (countElement) {
                countElement.textContent = `${Object.keys(tables).length}개 테이블`;
            }
            
            if (!grid || Object.keys(tables).length === 0) return;
            
            // 테이블 카드 업데이트
            Object.entries(tables).forEach(([tableName, tableInfo]) => {
                const card = grid.querySelector(`[data-table="${tableName}"]`);
                if (card) {
                    const stats = card.querySelectorAll('.table-stat-value');
                    if (stats.length >= 4) {
                        stats[0].textContent = tableInfo.total_games;
                        stats[1].textContent = tableInfo.pair_count;
                        stats[2].textContent = `${(tableInfo.statistics.pair_rate * 100).toFixed(1)}%`;
                        stats[3].textContent = `${tableInfo.games_since_last_pair}게임`;
                    }
                    
                    // 상태 업데이트
                    const status = card.querySelector('.table-status');
                    if (status) {
                        const lastGameTime = tableInfo.last_game_time;
                        const isActive = lastGameTime && new Date() - new Date(lastGameTime) < 5 * 60 * 1000; // 5분
                        status.className = `table-status ${isActive ? '' : 'inactive'}`;
                    }
                }
            });
        }
        
        function updateConnectionStatus(status) {
            const statusElement = document.getElementById('connection-status');
            if (statusElement) {
                statusElement.className = `status-indicator status-${status}`;
                statusElement.textContent = status === 'online' ? '🟢 실시간 연결' : '🔴 연결 끊어짐';
            }
        }
        
        function updateLastUpdateTime() {
            const element = document.getElementById('last-update');
            if (element) {
                element.textContent = `업데이트: ${new Date().toLocaleTimeString()}`;
            }
        }
        
        function showToast(title, message, type = 'info', duration = 4000) {
            let container = document.getElementById('toast-container');
            
            // 컨테이너가 없으면 생성
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 10000;
                    max-width: 350px;
                    pointer-events: none;
                `;
                document.body.appendChild(container);
            }
            
            const toast = document.createElement('div');
            const toastId = 'toast-' + Date.now();
            toast.id = toastId;
            toast.className = `toast ${type}`;
            
            // 타입별 색상과 아이콘 설정
            const typeConfig = {
                error: { bg: '#ef4444', icon: 'alert-circle' },
                success: { bg: '#10b981', icon: 'check-circle' },
                warning: { bg: '#f59e0b', icon: 'alert-triangle' },
                info: { bg: '#3b82f6', icon: 'info' }
            };
            
            const config = typeConfig[type] || typeConfig.info;
            
            toast.style.cssText = `
                background: ${config.bg};
                color: white;
                padding: 16px;
                border-radius: 8px;
                margin-bottom: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                transform: translateX(100%);
                transition: all 0.3s ease;
                cursor: pointer;
                pointer-events: all;
                display: flex;
                align-items: flex-start;
                gap: 12px;
                min-height: 60px;
            `;
            
            toast.innerHTML = `
                <i data-feather="${config.icon}" style="width: 20px; height: 20px; flex-shrink: 0; margin-top: 2px;"></i>
                <div style="flex: 1;">
                    <div style="font-weight: 600; margin-bottom: 4px;">${title}</div>
                    <div class="toast-message" style="font-size: 14px; line-height: 1.4;">${message}</div>
                </div>
                <button onclick="removeToast('${toastId}')" style="background: none; border: none; color: white; cursor: pointer; padding: 0; margin: 0; font-size: 18px; line-height: 1;">&times;</button>
            `;
            
            container.appendChild(toast);
            
            // 아이콘 렌더링
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
            
            // 토스트 표시 애니메이션
            setTimeout(() => {
                toast.style.transform = 'translateX(0)';
            }, 100);
            
            // 자동 제거 (에러 메시지는 더 오래 표시)
            const autoRemoveDelay = type === 'error' ? duration * 2 : duration;
            setTimeout(() => {
                removeToast(toastId);
            }, autoRemoveDelay);
            
            // 클릭으로 제거
            toast.addEventListener('click', () => removeToast(toastId));
        }
        
        function removeToast(toastId) {
            const toast = document.getElementById(toastId);
            if (toast) {
                toast.style.transform = 'translateX(100%)';
                setTimeout(() => toast.remove(), 300);
            }
        }
        
        function showOfflineBanner() {
            const banner = document.getElementById('offline-banner');
            if (banner) {
                banner.classList.add('show');
            }
        }
        
        function hideOfflineBanner() {
            const banner = document.getElementById('offline-banner');
            if (banner) {
                banner.classList.remove('show');
            }
        }
        
        function showLoading(message = '로딩 중...') {
            const overlay = document.getElementById('loading-overlay');
            if (overlay) {
                overlay.style.display = 'flex';
                // 로딩 메시지 업데이트
                const loadingText = overlay.querySelector('.loading-text');
                if (loadingText) {
                    loadingText.textContent = message;
                }
            } else {
                // 오버레이가 없으면 동적으로 생성
                createLoadingOverlay(message);
            }
        }
        
        function hideLoading() {
            const overlay = document.getElementById('loading-overlay');
            if (overlay) {
                overlay.style.display = 'none';
            }
        }
        
        function createLoadingOverlay(message = '로딩 중...') {
            // 기존 오버레이 제거
            const existingOverlay = document.getElementById('loading-overlay');
            if (existingOverlay) {
                existingOverlay.remove();
            }
            
            const overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-content">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">${message}</div>
                </div>
                <style>
                .loading-content {
                    text-align: center;
                    color: white;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }
                .loading-spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid rgba(255,255,255,0.3);
                    border-radius: 50%;
                    border-top-color: #3b82f6;
                    animation: spin 1s ease-in-out infinite;
                    margin: 0 auto 15px;
                }
                .loading-text {
                    font-size: 16px;
                    font-weight: 500;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                </style>
            `;
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                backdrop-filter: blur(5px);
            `;
            
            document.body.appendChild(overlay);
        }
        
        function toggleTheme() {
            currentTheme = currentTheme === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', currentTheme);
            localStorage.setItem('theme', currentTheme);
            updateThemeIcon();
            showToast('테마 변경', `${currentTheme === 'light' ? '라이트' : '다크'} 모드로 변경됨`, 'info');
        }
        
        function updateThemeIcon() {
            const icon = document.getElementById('theme-icon');
            if (icon) {
                icon.setAttribute('data-feather', currentTheme === 'light' ? 'sun' : 'moon');
                feather.replace();
            }
        }
        
        function refreshData() {
            if (!isOnline) {
                showToast('오프라인', '오프라인 모드에서는 새로고침할 수 없습니다', 'info');
                return;
            }
            
            showLoading();
            
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateDashboard(data.data);
                        updateLastUpdateTime();
                        showToast('새로고침', '최신 데이터를 불러왔습니다', 'success');
                    }
                })
                .catch(error => {
                    showToast('오류', '데이터 로드 중 오류가 발생했습니다', 'error');
                })
                .finally(() => {
                    hideLoading();
                });
        }
        
        function addDemoData() {
            console.log('🎯 데모 데이터 추가 함수 호출됨');
            console.log('🔍 현재 상태 체크:', {
                isOnline: isOnline,
                navigatorOnline: navigator.onLine,
                addDemoDataRunning: window.addDemoDataRunning
            });
            
            // 중복 실행 방지
            if (window.addDemoDataRunning) {
                console.warn('⚠️ 데모 데이터 추가가 이미 진행 중입니다');
                showToast('진행 중', '데모 데이터 추가가 이미 진행 중입니다', 'info');
                return;
            }
            
            // 실행 중 플래그 설정
            window.addDemoDataRunning = true;
            
            try {
                // 오프라인 상태 확인
                if (!isOnline) {
                    console.warn('⚠️ 오프라인 상태로 인해 데모 데이터 추가 불가');
                    showToast('오프라인', '오프라인 모드에서는 데모 데이터를 추가할 수 없습니다', 'info');
                    window.addDemoDataRunning = false; // 플래그 해제
                    return;
                }
                
                // 버튼 상태 업데이트
                const demoButtons = document.querySelectorAll('button[onclick="addDemoData()"]');
                console.log(`🔍 찾은 버튼 개수: ${demoButtons.length}`);
                
                demoButtons.forEach(btn => {
                    btn.disabled = true;
                    btn.innerHTML = '⏳ 추가중...';
                    btn.classList.add('loading');
                });
                
                // 로딩 표시 (진행 상태별 메시지)
                showLoading('🎲 데모 데이터 생성 중...');
                showToast('시작', '데모 데이터를 생성하고 있습니다...', 'info', 2000);
                console.log('📡 데모 데이터 API 요청 시작');
                
                // 상태 확인을 위한 디버깅 정보
                console.log('🔧 디버깅 정보:', {
                    온라인상태: navigator.onLine,
                    현재URL: window.location.href,
                    버튼개수: demoButtons.length,
                    현재시간: new Date().toISOString(),
                    실행플래그: window.addDemoDataRunning
                });
            } catch (initError) {
                console.error('❌ 초기화 중 오류:', initError);
                showToast('오류', '초기화 중 오류가 발생했습니다', 'error');
                window.addDemoDataRunning = false;
                return;
            }
            
            // API 요청 시작
            const startTime = Date.now();
            
            fetch('/api/demo', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => {
                console.log(`📊 API 응답 상태: ${response.status} ${response.statusText}`);
                console.log(`⏱️ 응답 시간: ${Date.now() - startTime}ms`);
                
                // 서버 처리 중 상태 업데이트
                showLoading('📡 서버 응답 처리 중...');
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return response.json();
            })
            .then(data => {
                console.log('📝 API 응답 데이터:', data);
                
                // 데이터 처리 중 상태 업데이트
                showLoading('✨ 결과 처리 중...');
                
                if (data && data.success === true) {
                    const message = data.message || '데모 데이터가 성공적으로 추가되었습니다';
                    const gamesAdded = data.games_added || 0;
                    const pairsFound = data.pairs_found || 0;
                    
                    console.log(`✅ 성공: ${gamesAdded}개 게임, ${pairsFound}개 페어`);
                    
                    // 상세한 성공 메시지
                    const detailedMessage = `${gamesAdded}개 게임 추가${pairsFound > 0 ? `, ${pairsFound}개 페어 발견` : ''}`;
                    showToast('데모 데이터 추가 완료', detailedMessage, 'success', 5000);
                    
                    // 데이터 새로고침 상태 표시
                    showLoading('🔄 화면 업데이트 중...');
                    
                    // 즉시 데이터 새로고침 (에러 처리 포함)
                    console.log('🔄 페이지 데이터 즉시 새로고침 시작');
                    try {
                        refreshData();
                    } catch (refreshError) {
                        console.error('🔄 데이터 새로고침 중 오류:', refreshError);
                        showToast('새로고침 오류', '데이터는 추가되었지만 새로고침에 실패했습니다', 'warning');
                    }
                    
                } else if (data && data.success === false) {
                    // API는 200을 반환했지만 success: false인 경우
                    const errorMsg = data.message || data.error || '알 수 없는 서버 오류가 발생했습니다';
                    console.error('❌ API 실패:', errorMsg);
                    showToast('데모 데이터 추가 실패', errorMsg, 'error');
                } else {
                    // 예상치 못한 응답 형식
                    console.error('❌ 예상치 못한 응답 형식:', data);
                    showToast('응답 오류', '서버에서 예상치 못한 응답을 받았습니다', 'warning');
                }
            })
            .catch(error => {
                console.error('❌ 데모 데이터 추가 오류:', error);
                
                // 에러 타입별 상세 처리
                let errorMessage = '데모 데이터 추가 중 오류가 발생했습니다';
                let errorType = 'error';
                
                if (error.name === 'TypeError') {
                    if (error.message.includes('fetch')) {
                        errorMessage = '서버 연결에 실패했습니다. 네트워크 상태를 확인해주세요.';
                        errorType = 'warning';
                    } else if (error.message.includes('JSON')) {
                        errorMessage = '서버 응답을 처리할 수 없습니다. 잠시 후 다시 시도해주세요.';
                    }
                } else if (error.message.includes('HTTP 50')) {
                    errorMessage = `서버 내부 오류: ${error.message}`;
                } else if (error.message.includes('HTTP 40')) {
                    errorMessage = `요청 오류: ${error.message}`;
                }
                
                showToast('요청 실패', errorMessage, errorType);
                
                // 자동 재시도는 제거하고 수동 재시도만 유지
                console.log('🔧 재시도가 필요한 경우 버튼을 다시 클릭해주세요');
            })
            .finally(() => {
                const totalTime = Date.now() - startTime;
                console.log(`🏁 데모 데이터 요청 완료 (총 ${totalTime}ms)`);
                
                // 상태 초기화
                window.addDemoDataRunning = false;
                hideLoading();
                
                // 버튼 상태 복원
                const demoButtons = document.querySelectorAll('button[onclick="addDemoData()"]');
                setTimeout(() => {
                    demoButtons.forEach(btn => {
                        btn.disabled = false;
                        btn.innerHTML = '<i data-feather="plus"></i> 데모 데이터 추가';
                        btn.classList.remove('loading');
                    });
                    
                    // feather 아이콘 다시 로드
                    if (typeof feather !== 'undefined') {
                        feather.replace();
                    }
                }, 500);
            });
        }
        
        // 상태 리셋 함수 (디버깅용)
        function resetDemoDataState() {
            console.log('🔄 데모 데이터 상태 강제 리셋');
            
            // 플래그 해제
            window.addDemoDataRunning = false;
            
            // 버튼 상태 복원
            const demoButtons = document.querySelectorAll('button[onclick="addDemoData()"]');
            demoButtons.forEach(btn => {
                btn.disabled = false;
                btn.innerHTML = '<i data-feather="plus"></i> 데모 데이터 추가';
                btn.classList.remove('loading');
            });
            
            // 로딩 숨김
            hideLoading();
            
            // feather 아이콘 다시 로드
            if (typeof feather !== 'undefined') {
                feather.replace();
            }
            
            showToast('상태 리셋', '데모 데이터 추가 상태가 리셋되었습니다', 'info');
            console.log('✅ 상태 리셋 완료');
        }
        
        // 디버깅 및 테스트 함수들
        function testApiConnection() {
            console.log('API 연결 테스트 시작');
            showToast('연결 테스트', 'API 연결을 테스트하고 있습니다...', 'info');
            
            fetch('/api/status')
                .then(response => {
                    console.log(`API 상태 응답: ${response.status} ${response.statusText}`);
                    return response.json();
                })
                .then(data => {
                    console.log('API 상태 데이터:', data);
                    if (data.status === 'ok') {
                        showToast('연결 성공', 'API 서버가 정상적으로 응답합니다', 'success');
                    } else {
                        showToast('연결 문제', 'API 서버 응답에 문제가 있습니다', 'warning');
                    }
                })
                .catch(error => {
                    console.error('API 연결 테스트 실패:', error);
                    showToast('연결 실패', 'API 서버에 연결할 수 없습니다', 'error');
                });
        }
        
        function showDebugInfo() {
            const debugInfo = {
                '온라인 상태': navigator.onLine ? '온라인' : '오프라인',
                '현재 URL': window.location.href,
                '사용자 에이전트': navigator.userAgent.substring(0, 50) + '...',
                '현재 시간': new Date().toLocaleString(),
                '로컬 저장소 지원': typeof(Storage) !== "undefined" ? '지원' : '미지원',
                '서비스 워커 지원': 'serviceWorker' in navigator ? '지원' : '미지원'
            };
            
            let infoText = '시스템 디버그 정보:\\n\\n';
            for (const [key, value] of Object.entries(debugInfo)) {
                infoText += `${key}: ${value}\\n`;
            }
            
            console.log('디버그 정보:', debugInfo);
            alert(infoText);
        }
        
        // 키보드 단축키 추가
        document.addEventListener('keydown', (event) => {
            // Ctrl + Shift + D: 디버그 정보 표시
            if (event.ctrlKey && event.shiftKey && event.key === 'D') {
                event.preventDefault();
                showDebugInfo();
            }
            
            // Ctrl + Shift + T: API 연결 테스트
            if (event.ctrlKey && event.shiftKey && event.key === 'T') {
                event.preventDefault();
                testApiConnection();
            }
            
            // Ctrl + Shift + A: 데모 데이터 추가
            if (event.ctrlKey && event.shiftKey && event.key === 'A') {
                event.preventDefault();
                console.log('🎯 키보드 단축키로 데모 데이터 추가 실행');
                addDemoData();
            }
            
            // Ctrl + Shift + R: 강제 상태 리셋 (디버깅용)
            if (event.ctrlKey && event.shiftKey && event.key === 'R') {
                event.preventDefault();
                console.log('🔄 강제 상태 리셋 실행');
                resetDemoDataState();
            }
        });
        
        // 초기화
        document.addEventListener('DOMContentLoaded', () => {
            feather.replace();
            updateLastUpdateTime();
            
            // 초기 네트워크 상태 확인
            if (!isOnline) {
                showOfflineBanner();
            }
            
            // 개발 모드 안내 (콘솔)
            console.log('%c🎯 Two Very Auto v3.1 - 바카라 모니터링 시스템', 'color: #10b981; font-size: 16px; font-weight: bold;');
            console.log('%c키보드 단축키:', 'color: #3b82f6; font-size: 14px; font-weight: bold;');
            console.log('Ctrl + Shift + D: 디버그 정보');
            console.log('Ctrl + Shift + T: API 연결 테스트');
            console.log('Ctrl + Shift + A: 데모 데이터 추가');
            console.log('Ctrl + Shift + R: 상태 강제 리셋');
            console.log('%c데모 데이터 추가 디버깅이 활성화되었습니다', 'color: #f59e0b;');
            
            // 주기적 상태 확인 (30초마다)
            setInterval(() => {
                if (socket.connected) {
                    socket.emit('ping');
                }
            }, 30000);
            
            // 페이지 가시성 변경 시 데이터 새로고침
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden && isOnline && socket.connected) {
                    refreshData();
                }
            });
        });
        
        // 시각화 컴포넌트 스크립트 포함
        const visualizationScript = document.createElement('script');
        visualizationScript.src = '/static/visualization_components.js';
        visualizationScript.onerror = () => {
            console.warn('시각화 컴포넌트를 로드할 수 없습니다. 인라인 스크립트를 사용합니다.');
            // 인라인으로 기본 시각화 매니저 포함
            // (실제 시각화 컴포넌트가 로드되지 않은 경우 기본 동작)
        };
        document.head.appendChild(visualizationScript);
        
        // 테마 시스템과 모바일 향상 기능 스크립트 포함
        const themeScript = document.createElement('link');
        themeScript.rel = 'stylesheet';
        themeScript.href = '/static/theme_system.css';
        document.head.appendChild(themeScript);
        
        const mobileScript = document.createElement('script');
        mobileScript.src = '/static/mobile_enhancements.js';
        document.head.appendChild(mobileScript);
        
        // AI 기능 관련 함수들
        async function loadAIStats() {
            try {
                const response = await fetch('/api/ai/stats');
                const data = await response.json();
                
                if (data.success) {
                    const stats = data.stats;
                    const modelInfo = stats.model_info;
                    const accuracyTracker = stats.accuracy_tracker;
                    
                    // AI 상태 업데이트
                    const statusElement = document.getElementById('ai-status');
                    if (modelInfo.tensorflow_available && modelInfo.is_trained) {
                        statusElement.textContent = '🟢 활성화됨';
                        statusElement.className = 'ai-status-indicator active';
                    } else if (modelInfo.tensorflow_available) {
                        statusElement.textContent = '🟡 훈련 필요';
                        statusElement.className = 'ai-status-indicator pending';
                    } else {
                        statusElement.textContent = '🔴 통계모드';
                        statusElement.className = 'ai-status-indicator statistical';
                    }
                    
                    // 메트릭 업데이트
                    document.getElementById('ai-accuracy').textContent = 
                        accuracyTracker.accuracy > 0 ? (accuracyTracker.accuracy * 100).toFixed(1) + '%' : '-';
                    document.getElementById('ai-predictions').textContent = 
                        accuracyTracker.total_predictions || '-';
                    document.getElementById('ai-method').textContent = 
                        modelInfo.tensorflow_available ? 'Deep Learning' : 'Statistical';
                }
            } catch (error) {
                console.error('AI 통계 로드 오류:', error);
            }
        }
        
        async function requestAIPrediction() {
            try {
                const button = event.target.closest('button');
                button.disabled = true;
                button.innerHTML = '<i data-feather="loader" class="btn-icon spin"></i> 예측 중...';
                
                // 더미 게임 데이터로 예측 요청
                const testGame = {
                    table_name: '메인테이블_A',
                    game_id: Date.now(),
                    player_cards: ['A♠', 'K♥'],
                    banker_cards: ['Q♦', '7♣']
                };
                
                const response = await fetch('/api/ai/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ current_game: testGame })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    displayPredictionResult(data.prediction);
                } else {
                    showToast('예측 요청 실패', 'error');
                }
                
            } catch (error) {
                console.error('AI 예측 요청 오류:', error);
                showToast('예측 요청 중 오류 발생', 'error');
            } finally {
                const button = event.target.closest('button');
                button.disabled = false;
                button.innerHTML = '<i data-feather="zap" class="btn-icon"></i> 예측 요청';
                feather.replace();
            }
        }
        
        function displayPredictionResult(prediction) {
            const resultsContainer = document.getElementById('prediction-results');
            
            const pairTypeNames = {
                'NO_PAIR': '페어 없음',
                'PLAYER_PAIR': '플레이어 페어',
                'BANKER_PAIR': '뱅커 페어',
                'BOTH_PAIR': '양쪽 페어'
            };
            
            const pairTypeName = pairTypeNames[prediction.predicted_pair_type] || prediction.predicted_pair_type;
            const confidence = (prediction.confidence * 100).toFixed(1);
            
            resultsContainer.innerHTML = `
                <div class="prediction-result">
                    <div class="prediction-main">
                        <div class="prediction-type ${prediction.predicted_pair_type.toLowerCase()}">${pairTypeName}</div>
                        <div class="prediction-confidence">신뢰도: ${confidence}%</div>
                    </div>
                    <div class="prediction-probabilities">
                        ${Object.entries(prediction.probabilities).map(([type, prob]) => `
                            <div class="prob-item">
                                <span class="prob-label">${pairTypeNames[type] || type}</span>
                                <span class="prob-value">${(prob * 100).toFixed(1)}%</span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="prediction-meta">
                        <small>방법: ${prediction.prediction_method === 'deep_learning' ? '딥러닝' : '통계적'}</small>
                        <small>시간: ${new Date(prediction.timestamp).toLocaleTimeString()}</small>
                    </div>
                </div>
            `;
        }
        
        async function trainAIModel() {
            try {
                const button = event.target.closest('button');
                const progressContainer = document.getElementById('training-progress');
                
                button.disabled = true;
                button.innerHTML = '<i data-feather="loader" class="btn-icon spin"></i> 훈련 중...';
                progressContainer.style.display = 'block';
                
                const response = await fetch('/api/ai/train', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ limit: 500 })
                });
                
                const data = await response.json();
                
                if (data.success && data.training_result.success) {
                    showToast('모델 훈련 완료!', 'success');
                    loadAIStats(); // 통계 새로고침
                } else {
                    showToast(data.training_result?.message || '훈련 실패', 'error');
                }
                
            } catch (error) {
                console.error('AI 훈련 오류:', error);
                showToast('훈련 중 오류 발생', 'error');
            } finally {
                const button = event.target.closest('button');
                const progressContainer = document.getElementById('training-progress');
                
                button.disabled = false;
                button.innerHTML = '<i data-feather="cpu" class="btn-icon"></i> 훈련 시작';
                progressContainer.style.display = 'none';
                feather.replace();
            }
        }
        
        // 페이지 로드 시 AI 통계 로드
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(loadAIStats, 1000);
        });
    </script>
</body>
</html>
'''

# PWA 라우트 정의
@app.route('/')
def pwa_dashboard():
    """PWA 메인 대시보드"""
    try:
        summary = tracker.get_all_tables_summary()
        
        return render_template_string(PWA_DASHBOARD_HTML, 
                                    global_stats=summary.get('global_stats', {}),
                                    tables=summary.get('tables', {}),
                                    active_tables=summary.get('active_tables', 0))
        
    except Exception as e:
        logger.error(f"PWA Dashboard error: {e}")
        return jsonify({'error': 'Dashboard load failed'}), 500

@app.route('/manifest.json')
def pwa_manifest():
    """PWA Manifest 파일 제공"""
    try:
        with open('static/pwa_manifest.json', 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        return jsonify(manifest_data)
    except Exception as e:
        logger.error(f"Manifest error: {e}")
        return jsonify({'error': 'Manifest not found'}), 404

@app.route('/sw.js')
def service_worker():
    """Service Worker 파일 제공"""
    try:
        return send_file('static/pwa_service_worker.js', mimetype='application/javascript')
    except Exception as e:
        logger.error(f"Service Worker error: {e}")
        return "console.log('Service Worker not found');", 404

@app.route('/pwa_offline.html')
def offline_page():
    """오프라인 페이지"""
    try:
        return send_file('static/pwa_offline.html')
    except Exception as e:
        return '''
        <!DOCTYPE html>
        <html><head><title>오프라인</title></head>
        <body style="text-align:center; padding:50px; font-family:Arial;">
        <h1>🔌 오프라인</h1><p>인터넷 연결을 확인해주세요.</p>
        </body></html>
        ''', 200

# API 라우트들 (기존과 동일하지만 PWA 최적화)
@app.route('/api/status')
def api_status():
    """PWA 최적화된 상태 API"""
    try:
        uptime = datetime.now() - datetime.now()  # 시작 시간 추가 필요
        
        return jsonify({
            'success': True,
            'status': 'running',
            'version': '2.0.0-PWA',
            'pwa_features': {
                'offline_support': True,
                'push_notifications': True,
                'background_sync': True
            },
            'websocket': ws_manager.get_connected_clients_info() if ws_manager else {'connected': 0, 'status': 'disabled'},
            'database': db_manager.get_database_info()
        })
        
    except Exception as e:
        logger.error(f"Status API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data')
def api_data():
    """PWA 캐시 친화적 데이터 API"""
    try:
        summary = tracker.get_all_tables_summary()
        recent_pairs = tracker.get_recent_pairs(limit=10)
        
        response_data = {
            'success': True,
            'data': summary,
            'recent_pairs': recent_pairs,
            'timestamp': datetime.now().isoformat(),
            'cache_version': 'v2.0'
        }
        
        response = jsonify(response_data)
        
        # PWA 캐시 헤더
        if request.headers.get('Cache-Control'):
            response.headers['Cache-Control'] = 'public, max-age=60'  # 1분 캐시
        
        return response
        
    except Exception as e:
        logger.error(f"Data API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/demo', methods=['POST'])
def api_demo():
    """PWA 친화적 데모 데이터 API - AsyncIO 충돌 방지 버전"""
    logger.info("데모 데이터 API 호출됨 (AsyncIO 안전 모드)")
    
    try:
        # 1단계: 데모 데이터 생성 (동기적으로만)
        logger.info("데모 데이터 생성 시작")
        demo_gen = DemoDataGenerator()
        demo_data = demo_gen.generate_demo_packet(5)  # 적은 수량으로 테스트
        
        if not demo_data:
            logger.error("데모 데이터 생성 실패")
            return jsonify({
                'success': False,
                'error': 'Demo data generation failed',
                'message': '데모 데이터 생성에 실패했습니다'
            }), 500
        
        # 2단계: 패킷 데이터 파싱
        logger.info("패킷 데이터 파싱 시작")
        games = decoder._parse_packet_content(demo_data)
        
        if not games:
            logger.error("패킷 데이터 파싱 실패")
            return jsonify({
                'success': False,
                'error': 'Packet parsing failed',
                'message': '패킷 데이터 파싱에 실패했습니다'
            }), 500
        
        # 3단계: 게임 데이터 처리 (AsyncIO 관련 기능 비활성화)
        processed_games = 0
        pair_count = 0
        
        for i, game in enumerate(games):
            try:
                # 기본 페어 트래킹만 수행 (동기적)
                result = tracker.track_game(game)
                
                # AsyncIO 관련 기능들은 모두 생략
                logger.debug(f"게임 {i+1} 처리 완료: {game.get('table_name', 'Unknown')} (AsyncIO 기능 비활성화)")
                
                processed_games += 1
                if result.get('has_pair'):
                    pair_count += 1
                    
            except Exception as e:
                logger.warning(f"게임 {i+1} 처리 중 오류 발생: {e}")
                continue
        
        # 4단계: 성공 응답 반환
        success_message = f'{processed_games}개 게임 추가 ({pair_count}개 페어) - AsyncIO 안전 모드'
        logger.info(f"데모 데이터 API 처리 완료: {success_message}")
        
        return jsonify({
            'success': True,
            'message': success_message,
            'games_added': processed_games,
            'total_games': len(games),
            'pairs_found': pair_count,
            'pwa_optimized': True,
            'async_safe_mode': True,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        error_message = f"데모 API 오류 (AsyncIO 안전 모드): {str(e)}"
        logger.error(error_message, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '데모 데이터 추가 중 서버 오류가 발생했습니다 (AsyncIO 안전 모드)',
            'async_safe_mode': True,
            'timestamp': datetime.now().isoformat()
        }), 500
    
    try:
        # AsyncIO 안전 모드로 데모 데이터 처리
        logger.info("📊 AsyncIO 안전 데모 데이터 처리 시작")
        
        # 1. 데모 데이터 생성 (동기 방식)
        demo_gen = DemoDataGenerator()
        demo_data = demo_gen.generate_demo_packet(10)  # 안정성을 위해 게임 수 감소
        
        if not demo_data:
            logger.error("❌ 데모 데이터 생성 실패")
            return jsonify({
                'success': False,
                'error': 'Demo data generation failed',
                'message': '데모 데이터 생성에 실패했습니다'
            }), 500
        
        # 2. 패킷 파싱 (동기 방식)
        games = decoder._parse_packet_content(demo_data)
        
        if not games:
            logger.error("❌ 패킷 데이터 파싱 실패")
            return jsonify({
                'success': False,
                'error': 'Packet parsing failed',
                'message': '패킷 데이터 파싱에 실패했습니다'
            }), 500
        
        logger.info(f"✅ {len(games)}개 게임 데이터 파싱 완료")
        
        # 3. 게임 데이터 처리 (AsyncIO 충돌 모듈 비활성화)
        pair_count = 0
        processed_games = 0
        
        for i, game in enumerate(games):
            try:
                # 페어 트래킹 (AsyncIO 안전)
                result = tracker.track_game(game)
                
                # 차트 데이터 처리 (동기 모드만)
                try:
                    chart_processor.process_game_data(game)
                    logger.debug(f"📈 차트 처리 완료: {game.get('table_name', 'Unknown')}")
                except Exception as chart_error:
                    logger.debug(f"⚠️ 차트 처리 오류 (무시됨): {chart_error}")
                
                # 실시간 대시보드 처리 건너뛰기 (AsyncIO 충돌 방지)
                logger.debug(f"⏭️ 실시간 대시보드 처리 비활성화: {game.get('table_name', 'Unknown')}")
                
                # AI 예측 처리 건너뛰기 (AsyncIO 충돌 방지)
                logger.debug(f"⏭️ AI 예측 처리 비활성화")
                
                # WebSocket 알림 건너뛰기 (AsyncIO 충돌 방지)
                if result.get('has_pair'):
                    pair_count += 1
                    logger.info(f"🎯 페어 발생: {game.get('table_name', 'Unknown')} - {result.get('pair_type', 'PAIR')}")
                
                processed_games += 1
                    
            except Exception as e:
                logger.warning(f"⚠️ 게임 {i+1} 처리 중 오류: {e}")
                continue
        
        # 4. 최종 통계 (동기 방식만)
        logger.info(f"✅ 게임 처리 완료: {processed_games}/{len(games)}개 성공, {pair_count}개 페어")
        
        # 5. 성공 응답
        success_message = f'{processed_games}개 게임 추가 ({pair_count}개 페어) - AsyncIO 안전 모드'
        logger.info(f"🎯 데모 데이터 API 처리 완료: {success_message}")
        
        return jsonify({
            'success': True,
            'message': success_message,
            'games_added': processed_games,
            'games_total': len(games),
            'pairs_found': pair_count,
            'mode': 'asyncio_safe',
            'pwa_optimized': True,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        error_message = f"데모 API 오류 (AsyncIO 안전 모드): {str(e)}"
        logger.error(error_message, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '데모 데이터 추가 중 서버 오류 (AsyncIO 충돌 방지 모드)',
            'mode': 'asyncio_safe',
            'timestamp': datetime.now().isoformat()
        }), 500

# PWA 추가 기능들
@app.route('/api/patterns/comprehensive/<table_name>')
def api_comprehensive_patterns(table_name):
    """종합 패턴 분석 API"""
    try:
        analysis = pattern_analyzer.analyze_comprehensive_patterns(table_name)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Pattern analysis error: {e}")
        return jsonify({'error': str(e)}), 500

# 고급 알림 시스템 API
@app.route('/api/notifications/config', methods=['GET', 'POST'])
def api_notification_config():
    """알림 설정 관리"""
    try:
        if request.method == 'GET':
            # 현재 설정 조회
            stats = advanced_notification.get_notification_stats()
            return jsonify({
                'success': True,
                'config': stats['channels'],
                'stats': stats
            })
        
        elif request.method == 'POST':
            # 설정 업데이트
            data = request.get_json()
            channel_name = data.get('channel')
            config = data.get('config', {})
            
            if not channel_name:
                return jsonify({'success': False, 'error': '채널 이름이 필요합니다'}), 400
                
            success = advanced_notification.update_channel_config(channel_name, config)
            
            return jsonify({
                'success': success,
                'message': f'{channel_name} 설정이 업데이트되었습니다' if success else '설정 업데이트 실패'
            })
            
    except Exception as e:
        logger.error(f"Notification config API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/test', methods=['POST'])
def api_test_notification():
    """테스트 알림 전송"""
    try:
        data = request.get_json()
        message_type = data.get('type', 'test')
        
        # 테스트 메시지 구성
        test_message = {
            'type': message_type,
            'text': '🧪 테스트 알림입니다',
            'data': {
                'table_name': '테스트테이블',
                'pair_type': 'PP',
                'game_number': 999,
                'test_mode': True
            },
            'priority': 'normal'
        }
        
        # 비동기 알림 전송을 동기적으로 실행 (asyncio 충돌 방지)
        # 🚫 AsyncIO 테스트 완전 비활성화 (AsyncIO 충돌 방지)
        logger.info("🚫 고급 알림 테스트 비활성화 - AsyncIO 충돌 방지")
        results = {'disabled': True, 'reason': 'AsyncIO conflict prevention'}
        # import asyncio  # 완전 비활성화
        
        success_count = sum(1 for r in results.values() if r) if results else 0
        total_count = len(results) if results else 0
        
        return jsonify({
            'success': True,
            'results': results,
            'summary': f'{success_count}/{total_count} 채널 성공'
        })
        
    except Exception as e:
        logger.error(f"Test notification API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/notifications/stats')
def api_notification_stats():
    """알림 통계 정보"""
    try:
        stats = advanced_notification.get_notification_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Notification stats API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================
# 정적 파일 서빙
# =============================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """정적 파일 서빙"""
    try:
        current_dir = Path(__file__).parent
        static_file = current_dir / filename
        
        if static_file.exists():
            return send_file(str(static_file))
        else:
            logger.warning(f"Static file not found: {filename}")
            return "File not found", 404
            
    except Exception as e:
        logger.error(f"Static file serving error: {e}")
        return "Internal server error", 500

# =============================================
# 시각화 및 차트 API 엔드포인트
# =============================================

@app.route('/api/charts/timeline')
def api_chart_timeline():
    """페어 발생 타임라인 차트 데이터"""
    try:
        hours = request.args.get('hours', 24, type=int)
        data = chart_processor.get_pair_timeline_data(hours)
        
        return jsonify({
            'success': True,
            'chart_data': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Timeline chart API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/charts/hourly')
def api_chart_hourly():
    """시간별 통계 차트 데이터"""
    try:
        hours = request.args.get('hours', 24, type=int)
        data = chart_processor.get_hourly_statistics(hours)
        
        return jsonify({
            'success': True,
            'chart_data': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Hourly chart API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/charts/comparison')
def api_chart_comparison():
    """테이블별 비교 차트 데이터"""
    try:
        data = chart_processor.get_table_comparison()
        
        return jsonify({
            'success': True,
            'chart_data': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Comparison chart API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/charts/distribution')
def api_chart_distribution():
    """페어 타입 분포 차트 데이터"""
    try:
        data = chart_processor.get_pair_type_distribution()
        
        return jsonify({
            'success': True,
            'chart_data': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Distribution chart API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/charts/metrics')
def api_chart_metrics():
    """실시간 메트릭 데이터"""
    try:
        data = chart_processor.get_realtime_metrics()
        
        return jsonify({
            'success': True,
            'metrics': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Metrics API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/live-stats')
def api_dashboard_live_stats():
    """실시간 대시보드 통계"""
    try:
        stats = realtime_dashboard.get_live_statistics()
        
        return jsonify({
            'success': True,
            'live_stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Live stats API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/table-overview')
def api_dashboard_table_overview():
    """테이블 개요 데이터"""
    try:
        overview = realtime_dashboard.get_table_overview()
        
        return jsonify({
            'success': True,
            'table_overview': overview,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Table overview API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/system-status')
def api_dashboard_system_status():
    """시스템 상태 정보"""
    try:
        status = realtime_dashboard.get_system_status()
        
        return jsonify({
            'success': True,
            'system_status': status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"System status API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/alert-rules', methods=['GET', 'POST'])
def api_dashboard_alert_rules():
    """알림 규칙 관리"""
    try:
        if request.method == 'POST':
            rules = request.json.get('rules', {})
            success = realtime_dashboard.update_alert_rules(rules)
            
            return jsonify({
                'success': success,
                'message': '알림 규칙 업데이트 완료' if success else '알림 규칙 업데이트 실패',
                'timestamp': datetime.now().isoformat()
            })
        
        else:
            return jsonify({
                'success': True,
                'alert_rules': realtime_dashboard.alert_rules,
                'timestamp': datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Alert rules API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# =============================================
# AI 예측 엔진 API 엔드포인트
# =============================================

@app.route('/api/ai/predict', methods=['POST'])
def api_ai_predict():
    """AI 페어 예측"""
    try:
        data = request.json
        current_game = data.get('current_game', {})
        table_name = current_game.get('table_name', 'Unknown')
        
        # 최근 게임 데이터 가져오기
        recent_games_data = db_manager.get_games(table_name=table_name, limit=20)
        recent_games = [
            {
                'table_name': g['table_name'],
                'game_id': g['game_id'],
                'player_cards': g.get('player_cards', '').split(', ') if g.get('player_cards') else [],
                'banker_cards': g.get('banker_cards', '').split(', ') if g.get('banker_cards') else [],
                'result': g.get('result', 'T'),
                'has_pair': g.get('has_pair', False),
                'pair_type': g.get('pair_type')
            }
            for g in recent_games_data
        ]
        
        # AI 예측 실행
        prediction = ai_engine.predict_pair(current_game, recent_games)
        
        return jsonify({
            'success': True,
            'prediction': prediction,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"AI prediction API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/train', methods=['POST'])
def api_ai_train():
    """AI 모델 훈련"""
    try:
        data = request.json
        table_name = data.get('table_name')
        limit = data.get('limit', 1000)
        
        # 훈련 데이터 가져오기
        if table_name:
            games_data = db_manager.get_games(table_name=table_name, limit=limit)
        else:
            games_data = db_manager.get_games(limit=limit)
        
        # 데이터 형식 변환
        training_data = []
        for game in games_data:
            training_game = {
                'table_name': game['table_name'],
                'game_id': game['game_id'],
                'player_cards': game.get('player_cards', '').split(', ') if game.get('player_cards') else [],
                'banker_cards': game.get('banker_cards', '').split(', ') if game.get('banker_cards') else [],
                'result': game.get('result', 'T'),
                'has_pair': game.get('has_pair', False),
                'pair_type': game.get('pair_type')
            }
            training_data.append(training_game)
        
        # 모델 훈련 실행
        training_result = ai_engine.train_model(training_data)
        
        return jsonify({
            'success': training_result.get('success', False),
            'training_result': training_result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"AI training API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/stats')
def api_ai_stats():
    """AI 예측 통계"""
    try:
        stats = ai_engine.get_prediction_stats()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"AI stats API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/validate', methods=['POST'])
def api_ai_validate():
    """AI 예측 검증"""
    try:
        data = request.json
        game_id = data.get('game_id')
        actual_result = data.get('actual_result', {})
        
        # 예측 검증
        ai_engine.validate_prediction(game_id, actual_result)
        
        return jsonify({
            'success': True,
            'message': '예측 검증 완료',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"AI validation API error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 🚫 async def start_background_services() 완전 비활성화 (AsyncIO 충돌 방지)
def start_background_services_sync():
    """동기 백그라운드 서비스 (AsyncIO 비활성화)"""
    logger.info("🚫 백그라운드 서비스 비활성화됨 - AsyncIO 충돌 방지")
    # 모든 async/await 호출 비활성화

def main():
    """PWA 웹서버 실행"""
    try:
        logger.info("Starting Two Very Auto PWA Dashboard v2.0...")
        
        # WebSocket 브로드캐스팅 시작 (임시 비활성화)
        logger.info("WebSocket 브로드캐스팅 임시 비활성화")
        # ws_manager.start_broadcasting()
        
        # 백그라운드 서비스 시작 (임시 비활성화 - asyncio 디버깅)
        logger.info("백그라운드 서비스 임시 비활성화 (asyncio 문제 해결)")
        # import asyncio
        # def start_bg_services():
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)
        #     loop.run_until_complete(start_background_services())
        
        # bg_thread = threading.Thread(target=start_bg_services, daemon=True)
        # bg_thread.start()
        
        # 초기 상태
        summary = tracker.get_all_tables_summary()
        logger.info(f"PWA System initialized - Tables: {summary.get('total_tables', 0)}")
        
        # Flask 서버 시작
        logger.info("Starting PWA web server with charts on http://127.0.0.1:5555")
        if socketio:
            socketio.run(
                app,
                host='127.0.0.1',
                port=5555,
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
        else:
            # SocketIO 없이 표준 Flask 서버 실행
            logger.info("SocketIO 비활성화됨 - 표준 Flask 서버 실행")
            app.run(
                host='127.0.0.1',
                port=5555,
                debug=False,
                use_reloader=False
            )
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Application error: {e}")
    finally:
        if ws_manager:
            ws_manager.stop_broadcasting()
        logger.info("PWA Application shutdown complete")

if __name__ == '__main__':
    main()