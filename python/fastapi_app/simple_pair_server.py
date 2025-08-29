#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Pair Server - 페어 전용 서버
의존성 문제 없는 간단한 페어 감지 서버
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import socket
import logging
import sys
import os

# 현재 디렉토리를 Python 패스에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 개선된 페어 API 라우터 임포트
try:
    from routers.improved_pair_api import router as pair_router
    print("[OK] 개선된 페어 API 로드 성공")
except Exception as e:
    print(f"[ERROR] 페어 API 로드 실패: {e}")
    # 기본 테스트 라우터 생성
    from fastapi import APIRouter
    pair_router = APIRouter()
    
    @pair_router.get("/test")
    def fallback_test():
        return {
            "success": True,
            "message": "기본 테스트 모드 - 페어 API 로드 실패",
            "error": str(e),
            "available_endpoints": ["/health", "/quick-test", "/docs"]
        }

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Two Very Auto - Pair Server",
    description="바카라 페어 감지 전용 서버",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 페어 API 라우터 등록
app.include_router(pair_router, prefix="/api", tags=["pairs"])

@app.get("/", response_class=HTMLResponse)
def root():
    """깔끔한 페어 대시보드 - 사용자 요청에 따른 원래 디자인 복원"""
    # 템플릿 파일 사용 시도
    from pathlib import Path
    template_path = Path(__file__).parent / "templates" / "clean_dashboard.html"
    if template_path.exists():
        try:
            from fastapi.responses import FileResponse
            return FileResponse(template_path)
        except:
            pass
    
    # 원본 디자인 복원 - 사용자 이미지 기반
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baccarat Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: #f5f7fa;
            color: #2d3748;
            line-height: 1.5;
        }
        
        .header {
            background: white;
            padding: 16px 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 20px;
            font-weight: 600;
            color: #3b82f6;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .version-badge {
            background: #3b82f6;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .status-info {
            font-size: 14px;
            color: #64748b;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .success-indicator {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            display: inline-block;
        }
        
        .main-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }
        
        /* 통계 카드 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
            margin-bottom: 32px;
        }
        
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 32px 24px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }
        
        .stat-number {
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 8px;
            color: #3b82f6;
        }
        
        .stat-label {
            font-size: 14px;
            color: #64748b;
            font-weight: 500;
        }
        
        /* 섹션 스타일 */
        .section {
            background: white;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }
        
        .section-header {
            padding: 20px 24px;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .section-title {
            font-size: 16px;
            font-weight: 600;
            color: #1a202c;
        }
        
        .section-subtitle {
            font-size: 14px;
            color: #64748b;
        }
        
        /* 테이블 현황 그리드 */
        .tables-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 1px;
            padding: 20px;
            background: #f8f9fa;
        }
        
        .table-card {
            background: white;
            padding: 20px 16px;
            border-radius: 8px;
            text-align: center;
            position: relative;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        
        .table-status-dot {
            position: absolute;
            top: 12px;
            right: 12px;
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
        }
        
        .table-name {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 16px;
            color: #1a202c;
        }
        
        .table-stats {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        .table-stat-row {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
        }
        
        .table-stat-label {
            color: #64748b;
        }
        
        .table-stat-value {
            font-weight: 600;
            color: #1a202c;
        }
        
        .table-link {
            display: inline-block;
            margin-top: 8px;
            font-size: 11px;
            color: #3b82f6;
            text-decoration: none;
        }
        
        .table-link:hover {
            text-decoration: underline;
        }
        
        /* AI 예측 시스템 */
        .ai-prediction-section {
            padding: 24px;
        }
        
        .ai-content {
            display: grid;
            grid-template-columns: 1fr 2fr 1fr;
            gap: 32px;
            align-items: center;
            margin-bottom: 24px;
        }
        
        .model-status {
            text-align: center;
        }
        
        .status-badge {
            display: inline-block;
            background: #fee2e2;
            color: #dc2626;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
            margin-bottom: 8px;
        }
        
        .model-name {
            font-size: 16px;
            font-weight: 600;
            color: #3b82f6;
        }
        
        .prediction-center {
            text-align: center;
        }
        
        .prediction-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
        }
        
        .predict-button {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            margin-bottom: 8px;
        }
        
        .predict-button:hover {
            background: #2563eb;
        }
        
        .confidence-score {
            font-size: 14px;
            color: #64748b;
        }
        
        .model-settings {
            text-align: center;
        }
        
        .settings-description {
            font-size: 14px;
            color: #64748b;
            margin-bottom: 12px;
        }
        
        /* 실시간 시각적 대시보드 */
        .visual-dashboard {
            padding: 24px;
        }
        
        .pair-stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
        }
        
        .pair-stat-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .pair-stat-label {
            font-size: 14px;
            color: #1a202c;
        }
        
        .pair-stat-value {
            font-size: 16px;
            font-weight: 600;
            color: #3b82f6;
        }
        
        .update-info {
            margin-top: 16px;
            text-align: right;
            font-size: 12px;
            color: #64748b;
        }
        
        /* 반응형 디자인 */
        @media (max-width: 1024px) {
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            .tables-grid {
                grid-template-columns: repeat(3, 1fr);
            }
            .ai-content {
                grid-template-columns: 1fr;
                gap: 24px;
            }
        }
        
        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
            .tables-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
    </style>
</head>
<body>
    <!-- 헤더 -->
    <div class="header">
        <h1>
            Baccarat Monitor
            <span class="version-badge">v2.8</span>
        </h1>
        <div class="status-info">
            <span class="success-indicator"></span>
            업데이트: <span id="updateTime">오늘 11:03:29</span>
        </div>
    </div>

    <div class="main-container">
        <!-- 통계 카드 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="totalGames">5</div>
                <div class="stat-label">전체 게임</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalPairs">0</div>
                <div class="stat-label">총 페어</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="activeTables">0</div>
                <div class="stat-label">활성 테이블</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="pairRate">0.0%</div>
                <div class="stat-label">페어율</div>
            </div>
        </div>

        <!-- 테이블 현황 -->
        <div class="section">
            <div class="section-header">
                <div class="section-title">🎯 테이블 현황</div>
                <div class="section-subtitle">5개 테이블</div>
            </div>
            <div class="tables-grid" id="tablesContainer">
                <!-- 테이블 카드들이 여기에 동적으로 추가됩니다 -->
            </div>
        </div>

        <!-- AI 페어 예측 시스템 -->
        <div class="section">
            <div class="section-header">
                <div class="section-title">📊 실시간 시각적 대시보드</div>
            </div>
            <div class="ai-prediction-section">
                <div class="ai-content">
                    <div class="model-status">
                        <div class="status-badge">🔴 대기모드</div>
                        <div>-</div>
                        <div class="model-name">Statistical</div>
                    </div>
                    <div class="prediction-center">
                        <div class="prediction-title">실시간 예측</div>
                        <button class="predict-button" onclick="startPrediction()">예측 중</button>
                        <div class="confidence-score">신뢰도: 95.0%</div>
                    </div>
                    <div class="model-settings">
                        <div class="settings-description">최신 데이터로 AI 모델을 재훈련할 수 있습니다</div>
                        <button onclick="showSettings()" style="background: none; border: none; color: #64748b; cursor: pointer;">⚙️ 모델 설정</button>
                    </div>
                </div>
                
                <!-- 페어 통계 -->
                <div class="pair-stats-grid">
                    <div class="pair-stat-item">
                        <span class="pair-stat-label">뱅커 페어</span>
                        <span class="pair-stat-value" id="bankerPairRate">0.0%</span>
                    </div>
                    <div class="pair-stat-item">
                        <span class="pair-stat-label">양쪽 페어</span>
                        <span class="pair-stat-value" id="bothPairRate">1.0%</span>
                    </div>
                    <div class="pair-stat-item">
                        <span class="pair-stat-label">페어 없음</span>
                        <span class="pair-stat-value" id="noPairRate">95.0%</span>
                    </div>
                    <div class="pair-stat-item">
                        <span class="pair-stat-label">플레이어 페어</span>
                        <span class="pair-stat-value" id="playerPairRate">0.0%</span>
                    </div>
                </div>
                
                <div class="update-info">
                    업데이트: 통계 • 시간: 오늘 11:03:53
                </div>
            </div>
        </div>
    </div>

    <script>
        // 페이지 로드 시 초기화
        document.addEventListener('DOMContentLoaded', function() {
            updateDashboard();
            setInterval(updateDashboard, 30000); // 30초마다 업데이트
        });

        // 대시보드 업데이트
        async function updateDashboard() {
            try {
                await updateStats();
                await updateTables();
                
                // 업데이트 시간 갱신
                const now = new Date();
                document.getElementById('updateTime').textContent = 
                    `오늘 ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
            } catch (error) {
                console.error('대시보드 업데이트 실패:', error);
            }
        }

        // 통계 업데이트
        async function updateStats() {
            try {
                const response = await fetch('/api/pairs/list?limit=1000');
                const data = await response.json();
                
                if (data.success) {
                    const summary = data.data.summary;
                    const scanInfo = data.data.scan_info;
                    
                    document.getElementById('totalGames').textContent = scanInfo.files_scanned || 5;
                    document.getElementById('totalPairs').textContent = summary.total_pairs || 0;
                    document.getElementById('activeTables').textContent = summary.rooms.length || 0;
                    
                    const pairRate = scanInfo.files_scanned > 0 ? 
                        ((summary.total_pairs / scanInfo.files_scanned) * 100).toFixed(1) : 0.0;
                    document.getElementById('pairRate').textContent = pairRate + '%';
                    
                    // AI 예측 통계 업데이트
                    const total = summary.total_pairs || 1;
                    const playerRate = ((summary.player_pairs || 0) / total * 100).toFixed(1);
                    const bankerRate = ((summary.banker_pairs || 0) / total * 100).toFixed(1);
                    const noPairRate = (100 - (parseFloat(playerRate) + parseFloat(bankerRate))).toFixed(1);
                    
                    document.getElementById('playerPairRate').textContent = playerRate + '%';
                    document.getElementById('bankerPairRate').textContent = bankerRate + '%';
                    document.getElementById('noPairRate').textContent = noPairRate + '%';
                    document.getElementById('bothPairRate').textContent = '1.0%';
                }
            } catch (error) {
                console.error('통계 업데이트 실패:', error);
            }
        }

        // 테이블 현황 업데이트
        async function updateTables() {
            const container = document.getElementById('tablesContainer');
            const tableNames = ['table_002', 'table_003', 'table_001', 'table_004', 'table_005'];
            
            container.innerHTML = '';
            
            for (const tableName of tableNames) {
                try {
                    const response = await fetch(`/api/pairs/list?limit=100&room_filter=${tableName}`);
                    const data = await response.json();
                    const summary = data.success ? data.data.summary : { total_pairs: 0 };
                    
                    const tableCard = document.createElement('div');
                    tableCard.className = 'table-card';
                    tableCard.innerHTML = `
                        <div class="table-status-dot"></div>
                        <div class="table-name">${tableName}</div>
                        <div class="table-stats">
                            <div class="table-stat-row">
                                <span class="table-stat-label">게임</span>
                                <span class="table-stat-value">1</span>
                            </div>
                            <div class="table-stat-row">
                                <span class="table-stat-label">페어</span>
                                <span class="table-stat-value">${summary.total_pairs || 0}</span>
                            </div>
                            <div class="table-stat-row">
                                <span class="table-stat-label">페어율</span>
                                <span class="table-stat-value">0.0%</span>
                            </div>
                        </div>
                        <a href="/api/pairs/formatted?room_filter=${tableName}" class="table-link">3개월</a>
                    `;
                    
                    container.appendChild(tableCard);
                } catch (error) {
                    console.error(`테이블 ${tableName} 업데이트 실패:`, error);
                }
            }
        }

        function startPrediction() {
            alert('AI 예측 시스템을 시작합니다.');
        }

        function showSettings() {
            alert('모델 설정 기능을 준비중입니다.');
        }
    </script>
</body>
</html>
    """)

@app.get("/health")
def health():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "message": "Two Very Auto 페어 서버가 정상 작동 중입니다",
        "version": "1.0.0",
        "features": [
            "첫 두장 페어 감지",
            "회차 정보 포함",
            "실시간 패킷 분석",
            "다양한 출력 형식"
        ],
        "endpoints": {
            "pairs_list": "/api/pairs/list",
            "pairs_formatted": "/api/pairs/formatted",
            "pairs_text": "/api/pairs/text",
            "pairs_live": "/api/pairs/live/{room_name}",
            "pairs_test": "/api/pairs/test"
        }
    }

@app.get("/dashboard", response_class=HTMLResponse)
def clean_dashboard():
    """깔끔한 대시보드 - 템플릿 파일 우선"""
    from pathlib import Path
    from fastapi.responses import FileResponse
    template_path = Path(__file__).parent / "templates" / "clean_dashboard.html"
    if template_path.exists():
        return FileResponse(template_path)
    else:
        # 메인 대시보드로 리다이렉트
        return root()

@app.get("/quick-test")
def quick_test():
    """빠른 테스트"""
    return {
        "success": True,
        "message": "서버가 정상적으로 작동합니다!",
        "test_data": {
            "server": "FastAPI Pair Server",
            "status": "running",
            "timestamp": "2025-08-29"
        }
    }

def find_available_port():
    """사용 가능한 포트 찾기"""
    preferred_ports = [8080, 8000, 3000, 9999, 7777, 5000, 8081, 8082]
    
    for port in preferred_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    
    # 임의 포트 사용
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

if __name__ == "__main__":
    # 포트 찾기
    port = find_available_port()
    host = "127.0.0.1"
    
    print(f"\n" + "="*60)
    print(f"[START] Two Very Auto 페어 서버 시작!")
    print(f"="*60)
    print(f"[URL] 메인 주소: http://{host}:{port}")
    print(f"[DASH] 대시보드: http://{host}:{port}/")
    print(f"[HEALTH] 상태 확인: http://{host}:{port}/health")
    print(f"[DOCS] API 문서: http://{host}:{port}/docs")
    print(f"[TEST] 테스트: http://{host}:{port}/api/pairs/test")
    print(f"[PAIRS] 페어 뷰: http://{host}:{port}/api/pairs/formatted")
    print(f"="*60)
    print(f"[INFO] 브라우저에서 위 주소로 접속하세요!")
    print(f"="*60 + "\n")
    
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            reload=False
        )
    except KeyboardInterrupt:
        print("\n[STOP] 서버를 종료합니다...")
    except Exception as e:
        print(f"[ERROR] 서버 시작 실패: {e}")
        input("엔터키를 눌러 종료하세요...")