#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clean Pair Server - 깔끔하게 정리된 페어 서버
의존성 최소화, 안정성 우선
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import socket
import logging
import json
import os
from pathlib import Path
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Two Very Auto - Clean Pair Server",
    description="깔끔한 바카라 페어 감지 서버",
    version="2.0",
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

# 패킷 디렉토리 경로
PACKET_DIR = Path(__file__).parent.parent.parent / "packet"

def scan_packet_files():
    """패킷 파일 스캔"""
    try:
        if not PACKET_DIR.exists():
            logger.warning(f"패킷 디렉토리가 존재하지 않습니다: {PACKET_DIR}")
            return []
        
        json_files = list(PACKET_DIR.glob("*.json"))
        logger.info(f"스캔된 패킷 파일 수: {len(json_files)}")
        return json_files
    except Exception as e:
        logger.error(f"패킷 파일 스캔 실패: {e}")
        return []

def detect_pairs_in_file(file_path):
    """파일에서 페어 감지"""
    pairs = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return pairs
            
            # 각 라인을 JSON으로 파싱
            for line_num, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    data = json.loads(line)
                    # playerPair 또는 bankerPair가 true인 경우만 감지
                    if data.get('playerPair') or data.get('bankerPair'):
                        pair_types = []
                        if data.get('playerPair'):
                            pair_types.append({'type': 'Player', 'symbol': '[P]'})
                        if data.get('bankerPair'):
                            pair_types.append({'type': 'Banker', 'symbol': '[B]'})
                        
                        pairs.append({
                            'room': data.get('room', 'unknown'),
                            'round': data.get('round', 0),
                            'timestamp': data.get('eventTime', ''),
                            'pairs': pair_types,
                            'game_result': {
                                'winner': data.get('winner', 'Unknown'),
                                'playerScore': data.get('playerScore', 0),
                                'bankerScore': data.get('bankerScore', 0)
                            }
                        })
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"라인 {line_num} 처리 실패: {e}")
                    continue
    except Exception as e:
        logger.error(f"파일 {file_path} 처리 실패: {e}")
    
    return pairs

@app.get("/", response_class=HTMLResponse)
def root():
    """깔끔한 페어 대시보드"""
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baccarat Monitor v2.0 - Clean</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #f8fafc;
            color: #1e293b;
            line-height: 1.6;
        }
        .header {
            background: white;
            padding: 1rem 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-bottom: 1px solid #e2e8f0;
        }
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .logo h1 {
            font-size: 1.5rem;
            font-weight: 600;
            color: #1e293b;
        }
        .version {
            background: #3b82f6;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
            margin-left: 12px;
        }
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #10b981;
            font-weight: 500;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .main-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
            border: 1px solid #e2e8f0;
        }
        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .stat-label {
            color: #64748b;
            font-size: 0.875rem;
            font-weight: 500;
        }
        .stat-card:nth-child(1) .stat-number { color: #3b82f6; }
        .stat-card:nth-child(2) .stat-number { color: #10b981; }
        .stat-card:nth-child(3) .stat-number { color: #f59e0b; }
        .stat-card:nth-child(4) .stat-number { color: #8b5cf6; }
        .section {
            background: white;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            margin-bottom: 2rem;
        }
        .section-header {
            padding: 1.5rem 2rem;
            border-bottom: 1px solid #e2e8f0;
        }
        .section-title {
            font-size: 1.125rem;
            font-weight: 600;
            color: #1e293b;
        }
        .pair-history {
            max-height: 400px;
            overflow-y: auto;
        }
        .pair-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            border-bottom: 1px solid #f1f5f9;
        }
        .pair-item:hover {
            background: #f8fafc;
        }
        .pair-info {
            display: flex;
            flex-direction: column;
        }
        .pair-table {
            font-weight: 600;
            color: #1e293b;
        }
        .pair-details {
            font-size: 0.875rem;
            color: #64748b;
        }
        .pair-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .badge-player { background: #fef2f2; color: #dc2626; }
        .badge-banker { background: #eff6ff; color: #2563eb; }
        .loading {
            text-align: center;
            padding: 2rem;
            color: #64748b;
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="header-content">
            <div class="logo">
                <h1>Baccarat Monitor<span class="version">v2.0</span></h1>
            </div>
            <div class="status">
                <div class="status-dot"></div>
                <span id="lastUpdate">업데이트: 실시간</span>
            </div>
        </div>
    </header>

    <div class="main-container">
        <!-- 실시간 통계 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="totalGames">0</div>
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

        <!-- 최근 페어 내역 -->
        <div class="section">
            <div class="section-header">
                <span class="section-title">📋 최근 페어 내역</span>
            </div>
            <div class="pair-history" id="pairHistory">
                <div class="loading">페어 데이터를 불러오는 중...</div>
            </div>
        </div>
    </div>

    <script>
        // 페이지 로드 시 초기화
        document.addEventListener('DOMContentLoaded', function() {
            updateDashboard();
            setInterval(updateDashboard, 30000); // 30초마다 업데이트
        });
        
        async function updateDashboard() {
            try {
                const response = await fetch('/api/pairs');
                const data = await response.json();
                
                if (data.success) {
                    // 통계 업데이트
                    document.getElementById('totalGames').textContent = data.scan_info.files_scanned;
                    document.getElementById('totalPairs').textContent = data.summary.total_pairs;
                    document.getElementById('activeTables').textContent = data.summary.rooms.length;
                    
                    const pairRate = data.scan_info.files_scanned > 0 ? 
                        ((data.summary.total_pairs / data.scan_info.files_scanned) * 100).toFixed(1) : 0.0;
                    document.getElementById('pairRate').textContent = pairRate + '%';
                    
                    // 페어 내역 업데이트
                    let html = '';
                    data.pairs_list.slice(0, 20).forEach(pair => {
                        const pairTypes = pair.pairs.map(p => {
                            const badgeClass = p.type === 'Player' ? 'badge-player' : 'badge-banker';
                            return `<span class="pair-badge ${badgeClass}">${p.symbol}</span>`;
                        }).join(' ');
                        
                        html += `
                            <div class="pair-item">
                                <div class="pair-info">
                                    <div class="pair-table">${pair.room} - 회차 ${pair.round}</div>
                                    <div class="pair-details">${pair.timestamp} • ${pair.game_result.winner} 승</div>
                                </div>
                                <div>${pairTypes}</div>
                            </div>
                        `;
                    });
                    
                    document.getElementById('pairHistory').innerHTML = html || '<div class="loading">페어 데이터가 없습니다.</div>';
                }
                
                document.getElementById('lastUpdate').textContent = 
                    `업데이트: ${new Date().toLocaleTimeString('ko-KR')}`;
                    
            } catch (error) {
                console.error('대시보드 업데이트 실패:', error);
                document.getElementById('pairHistory').innerHTML = '<div class="loading">데이터 로드 실패</div>';
            }
        }
    </script>
</body>
</html>
    """)

@app.get("/api/pairs")
def get_pairs():
    """페어 데이터 조회"""
    try:
        # 패킷 파일 스캔
        packet_files = scan_packet_files()
        all_pairs = []
        
        # 각 파일에서 페어 감지
        for file_path in packet_files[:50]:  # 최대 50개 파일만 처리
            pairs = detect_pairs_in_file(file_path)
            all_pairs.extend(pairs)
        
        # 최신 순으로 정렬
        all_pairs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 통계 계산
        rooms = set(pair['room'] for pair in all_pairs)
        player_pairs = sum(1 for pair in all_pairs if any(p['type'] == 'Player' for p in pair['pairs']))
        banker_pairs = sum(1 for pair in all_pairs if any(p['type'] == 'Banker' for p in pair['pairs']))
        
        return {
            "success": True,
            "pairs_list": all_pairs,
            "summary": {
                "total_pairs": len(all_pairs),
                "player_pairs": player_pairs,
                "banker_pairs": banker_pairs,
                "rooms": list(rooms)
            },
            "scan_info": {
                "files_scanned": len(packet_files),
                "packets_processed": len([p for p in all_pairs]),
                "scan_time": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"페어 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "pairs_list": [],
            "summary": {"total_pairs": 0, "player_pairs": 0, "banker_pairs": 0, "rooms": []},
            "scan_info": {"files_scanned": 0, "packets_processed": 0, "scan_time": datetime.now().isoformat()}
        }

@app.get("/health")
def health():
    """서버 상태 확인"""
    return {
        "status": "healthy",
        "message": "Clean Pair Server 정상 작동",
        "version": "2.0",
        "timestamp": datetime.now().isoformat()
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
    
    print("=" * 60)
    print("Two Very Auto - Clean Pair Server")
    print("=" * 60)
    print(f"깔끔한 설계, 최소 의존성")
    print(f"실시간 페어 감지")
    print(f"직관적인 대시보드")
    print("=" * 60)
    print(f"메인 URL: http://{host}:{port}")
    print(f"상태 확인: http://{host}:{port}/health")
    print(f"API 문서: http://{host}:{port}/docs")
    print(f"페어 API: http://{host}:{port}/api/pairs")
    print("=" * 60)
    print("서버 시작 중...")
    print("=" * 60)
    
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
        print("\n서버가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n서버 시작 실패: {e}")
        input("엔터키를 눌러 종료하세요...")