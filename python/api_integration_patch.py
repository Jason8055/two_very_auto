#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API 통합 패치 v1.0
기존 웹 서버에 새로운 기능들을 통합하는 패치
"""

from flask import Flask
from korean_encoding_fix import setup_korean_encoding, safe_print

# 새로운 API 모듈들 임포트
from notification_settings_api import register_notification_api
from realtime_monitoring_dashboard import register_monitoring_api

# 한국어 인코딩 설정
setup_korean_encoding()


def apply_api_integration_patch(app: Flask):
    """기존 Flask 앱에 새로운 API들을 통합"""
    try:
        # 1. 알림 설정 API 등록
        register_notification_api(app)
        
        # 2. 실시간 모니터링 API 등록
        register_monitoring_api(app)
        
        # 3. 멀티 카지노 API 엔드포인트 추가
        from multi_casino_manager import get_multi_casino_manager
        from flask import Blueprint, jsonify, request
        
        # 멀티 카지노 API Blueprint
        casino_api = Blueprint('casino_api', __name__, url_prefix='/api/casinos')
        
        @casino_api.route('', methods=['GET'])
        def get_all_casinos():
            """모든 카지노 상태 조회"""
            manager = get_multi_casino_manager()
            casinos = manager.get_all_casino_status()
            return jsonify({'success': True, 'casinos': casinos})
        
        @casino_api.route('/<casino_id>/connect', methods=['POST'])
        def connect_casino(casino_id):
            """카지노 연결"""
            manager = get_multi_casino_manager()
            success = manager.connect_casino(casino_id)
            return jsonify({'success': success})
        
        @casino_api.route('/<casino_id>/disconnect', methods=['POST'])
        def disconnect_casino(casino_id):
            """카지노 연결 해제"""
            manager = get_multi_casino_manager()
            success = manager.disconnect_casino(casino_id)
            return jsonify({'success': success})
        
        @casino_api.route('/comparison', methods=['GET'])
        def get_casino_comparison():
            """카지노 간 비교 분석"""
            manager = get_multi_casino_manager()
            comparison = manager.get_casino_comparison()
            return jsonify({'success': True, 'comparison': comparison})
        
        @casino_api.route('/recommended', methods=['GET'])
        def get_recommended_casino():
            """추천 카지노 조회"""
            manager = get_multi_casino_manager()
            recommended = manager.get_recommended_casino()
            return jsonify({'success': True, 'recommended': recommended})
        
        # Blueprint 등록
        app.register_blueprint(casino_api)
        
        # 4. 새로운 네비게이션 메뉴 추가
        @app.route('/advanced-settings')
        def advanced_settings():
            """고급 설정 페이지"""
            return '''
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>고급 설정 - Two Very Auto</title>
                <style>
                    body { font-family: 'Noto Sans KR', sans-serif; margin: 20px; }
                    .settings-container { max-width: 800px; margin: 0 auto; }
                    .setting-section { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .setting-title { font-size: 18px; font-weight: bold; color: #4f46e5; margin-bottom: 15px; }
                    .nav-link { display: inline-block; margin: 10px 20px 10px 0; padding: 10px 20px; background: #4f46e5; color: white; text-decoration: none; border-radius: 5px; }
                    .nav-link:hover { background: #3730a3; }
                </style>
            </head>
            <body>
                <div class="settings-container">
                    <h1>🎛️ Two Very Auto 고급 설정</h1>
                    
                    <div class="setting-section">
                        <div class="setting-title">📱 알림 시스템</div>
                        <p>개인화된 알림 프로필과 설정을 관리합니다</p>
                        <a href="/api/notifications/dashboard" class="nav-link">알림 설정 관리</a>
                    </div>
                    
                    <div class="setting-section">
                        <div class="setting-title">🖥️ 성능 모니터링</div>
                        <p>시스템 성능과 상태를 실시간으로 모니터링합니다</p>
                        <a href="/api/monitoring/dashboard" class="nav-link">모니터링 대시보드</a>
                    </div>
                    
                    <div class="setting-section">
                        <div class="setting-title">🎰 멀티 카지노</div>
                        <p>여러 카지노를 동시에 모니터링하고 관리합니다</p>
                        <a href="/casino-manager" class="nav-link">카지노 관리</a>
                    </div>
                    
                    <div class="setting-section">
                        <div class="setting-title">🔧 시스템 도구</div>
                        <a href="/" class="nav-link">메인 대시보드</a>
                        <a href="/api/monitoring/metrics" class="nav-link">실시간 메트릭 (JSON)</a>
                        <a href="/api/notifications/profiles" class="nav-link">알림 프로필 (JSON)</a>
                        <a href="/api/casinos" class="nav-link">카지노 상태 (JSON)</a>
                    </div>
                </div>
            </body>
            </html>
            '''
        
        @app.route('/casino-manager')
        def casino_manager():
            """카지노 관리 페이지"""
            return '''
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>카지노 관리 - Two Very Auto</title>
                <style>
                    body { font-family: 'Noto Sans KR', sans-serif; margin: 20px; background: #f5f6fa; }
                    .manager-container { max-width: 1200px; margin: 0 auto; }
                    .casino-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                    .casino-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    .casino-status { display: inline-block; padding: 5px 15px; border-radius: 20px; color: white; font-size: 12px; margin-bottom: 10px; }
                    .status-connected { background: #2ed573; }
                    .status-disconnected { background: #ff3838; }
                    .status-error { background: #ffa502; }
                    .casino-stats { display: flex; justify-content: space-between; margin: 15px 0; }
                    .stat-item { text-align: center; }
                    .stat-value { font-size: 24px; font-weight: bold; color: #4f46e5; }
                    .stat-label { font-size: 12px; color: #666; }
                    .action-buttons { margin-top: 15px; }
                    .btn { padding: 8px 16px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; }
                    .btn-primary { background: #4f46e5; color: white; }
                    .btn-success { background: #2ed573; color: white; }
                    .btn-danger { background: #ff3838; color: white; }
                    .comparison-section { background: white; padding: 20px; border-radius: 10px; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                </style>
            </head>
            <body>
                <div class="manager-container">
                    <h1>🎰 멀티 카지노 관리자</h1>
                    <p>여러 카지노를 동시에 모니터링하고 성능을 비교합니다</p>
                    
                    <div class="casino-grid" id="casinoGrid">
                        <!-- 카지노 카드들이 여기에 동적으로 로드됩니다 -->
                    </div>
                    
                    <div class="comparison-section">
                        <h2>📊 카지노 성능 비교</h2>
                        <div id="comparisonChart">
                            <canvas id="performanceChart" width="400" height="200"></canvas>
                        </div>
                        <div id="recommendedCasino" style="margin-top: 15px; padding: 15px; background: #e8f4f8; border-radius: 8px;">
                            <!-- 추천 카지노 정보가 여기에 표시됩니다 -->
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 20px;">
                        <button onclick="location.href='/advanced-settings'" class="btn btn-primary">고급 설정으로 돌아가기</button>
                        <button onclick="location.href='/'" class="btn btn-success">메인 대시보드</button>
                    </div>
                </div>
                
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <script>
                    // 카지노 데이터 로드
                    async function loadCasinoData() {
                        try {
                            const response = await fetch('/api/casinos');
                            const data = await response.json();
                            
                            if (data.success) {
                                displayCasinos(data.casinos);
                            }
                        } catch (error) {
                            console.error('카지노 데이터 로드 실패:', error);
                        }
                    }
                    
                    // 카지노 카드 표시
                    function displayCasinos(casinos) {
                        const grid = document.getElementById('casinoGrid');
                        grid.innerHTML = '';
                        
                        casinos.forEach(casino => {
                            const statusClass = casino.is_active ? 'connected' : 'disconnected';
                            const statusText = casino.is_active ? '연결됨' : '연결 안됨';
                            
                            const card = document.createElement('div');
                            card.className = 'casino-card';
                            card.innerHTML = `
                                <div class="casino-status status-${statusClass}">${statusText}</div>
                                <h3>${casino.config.name || casino.casino_id}</h3>
                                <div class="casino-stats">
                                    <div class="stat-item">
                                        <div class="stat-value">${casino.games_processed}</div>
                                        <div class="stat-label">게임 처리</div>
                                    </div>
                                    <div class="stat-item">
                                        <div class="stat-value">${casino.pairs_detected}</div>
                                        <div class="stat-label">페어 감지</div>
                                    </div>
                                    <div class="stat-item">
                                        <div class="stat-value">${casino.average_games_per_hour.toFixed(1)}</div>
                                        <div class="stat-label">시간당 게임</div>
                                    </div>
                                </div>
                                <div class="action-buttons">
                                    ${casino.is_active ? 
                                        `<button class="btn btn-danger" onclick="disconnectCasino('${casino.casino_id}')">연결 해제</button>` :
                                        `<button class="btn btn-success" onclick="connectCasino('${casino.casino_id}')">연결</button>`
                                    }
                                </div>
                            `;
                            grid.appendChild(card);
                        });
                    }
                    
                    // 카지노 연결
                    async function connectCasino(casinoId) {
                        try {
                            const response = await fetch(`/api/casinos/${casinoId}/connect`, {method: 'POST'});
                            const data = await response.json();
                            if (data.success) {
                                loadCasinoData(); // 데이터 새로고침
                            }
                        } catch (error) {
                            console.error('카지노 연결 실패:', error);
                        }
                    }
                    
                    // 카지노 연결 해제
                    async function disconnectCasino(casinoId) {
                        try {
                            const response = await fetch(`/api/casinos/${casinoId}/disconnect`, {method: 'POST'});
                            const data = await response.json();
                            if (data.success) {
                                loadCasinoData(); // 데이터 새로고침
                            }
                        } catch (error) {
                            console.error('카지노 연결 해제 실패:', error);
                        }
                    }
                    
                    // 추천 카지노 로드
                    async function loadRecommendation() {
                        try {
                            const response = await fetch('/api/casinos/recommended');
                            const data = await response.json();
                            
                            if (data.success && data.recommended) {
                                document.getElementById('recommendedCasino').innerHTML = 
                                    `<strong>🎯 추천 카지노:</strong> ${data.recommended} (최적 성능)`;
                            } else {
                                document.getElementById('recommendedCasino').innerHTML = 
                                    '<em>현재 연결된 카지노가 없습니다</em>';
                            }
                        } catch (error) {
                            console.error('추천 카지노 로드 실패:', error);
                        }
                    }
                    
                    // 초기 데이터 로드
                    loadCasinoData();
                    loadRecommendation();
                    
                    // 5초마다 데이터 갱신
                    setInterval(() => {
                        loadCasinoData();
                        loadRecommendation();
                    }, 5000);
                </script>
            </body>
            </html>
            '''
        
        safe_print("✅ API 통합 패치 적용 완료")
        safe_print("📋 새로 추가된 엔드포인트:")
        safe_print("   - /api/notifications/* (알림 설정 API)")
        safe_print("   - /api/monitoring/* (성능 모니터링 API)")
        safe_print("   - /api/casinos/* (멀티 카지노 API)")
        safe_print("   - /advanced-settings (고급 설정 페이지)")
        safe_print("   - /casino-manager (카지노 관리 페이지)")
        
        return True
        
    except Exception as e:
        safe_print(f"❌ API 통합 패치 실패: {e}")
        return False


if __name__ == "__main__":
    # 테스트용 Flask 앱 생성
    from flask import Flask
    test_app = Flask(__name__)
    
    success = apply_api_integration_patch(test_app)
    if success:
        safe_print("🧪 API 통합 패치 테스트 성공")
        
        # 등록된 엔드포인트 출력
        safe_print("\n📍 등록된 엔드포인트:")
        for rule in test_app.url_map.iter_rules():
            safe_print(f"   {rule.methods} {rule.rule}")
    else:
        safe_print("❌ API 통합 패치 테스트 실패")