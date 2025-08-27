#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal Demo API Server - AsyncIO 충돌 완전 회피
순수 Flask + SQLite로 데모 데이터 기능만 구현
"""

from flask import Flask, jsonify, request, render_template_string
import json
import random
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask 앱 초기화
app = Flask(__name__)

# 미니멀 HTML 템플릿
MINIMAL_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Two Very Auto - 데모 테스트</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .btn { background: #007bff; color: white; border: none; padding: 12px 20px; border-radius: 4px; cursor: pointer; font-size: 16px; margin: 10px; }
        .btn:hover { background: #0056b3; }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
        .results { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 4px; border-left: 4px solid #007bff; }
        .pair-alert { color: #dc3545; font-weight: bold; }
        .success { color: #28a745; }
        .log { background: #000; color: #00ff00; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 12px; height: 300px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎲 Two Very Auto - AsyncIO Safe Demo</h1>
        <p>AsyncIO 충돌 없는 순수 Flask 데모 API 테스트</p>
        
        <div>
            <button class="btn" onclick="addDemoData()" id="demoBtn">
                📊 데모 데이터 추가
            </button>
            <button class="btn" onclick="getStats()">
                📈 통계 조회 (생성 데이터)
            </button>
            <button class="btn" onclick="getRealData()" style="background: #28a745;">
                🎯 실제 페어 데이터
            </button>
            <button class="btn" onclick="clearLogs()">
                🧹 로그 지우기
            </button>
        </div>
        
        <div class="results" id="results">
            <h3>📋 결과</h3>
            <div id="output">테스트 결과가 여기에 표시됩니다.</div>
        </div>
        
        <div>
            <h3>📝 실시간 로그</h3>
            <div class="log" id="logs"></div>
        </div>
    </div>

    <script>
        let isRunning = false;

        function log(message) {
            const logs = document.getElementById('logs');
            const timestamp = new Date().toLocaleTimeString();
            logs.innerHTML += `[${timestamp}] ${message}\\n`;
            logs.scrollTop = logs.scrollHeight;
        }

        function clearLogs() {
            document.getElementById('logs').innerHTML = '';
            log('🧹 로그 초기화됨');
        }

        async function addDemoData() {
            if (isRunning) return;
            
            const btn = document.getElementById('demoBtn');
            const output = document.getElementById('output');
            
            isRunning = true;
            btn.disabled = true;
            btn.textContent = '⏳ 처리 중...';
            
            log('🎯 데모 데이터 추가 요청 시작');
            
            try {
                const response = await fetch('/api/minimal-demo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    output.innerHTML = `
                        <div class="success">✅ ${data.message}</div>
                        <p><strong>게임 추가:</strong> ${data.games_added}개</p>
                        <p><strong>페어 발견:</strong> ${data.pairs_found}개</p>
                        <p><strong>처리 시간:</strong> ${data.processing_time || 'N/A'}</p>
                        <p><strong>모드:</strong> ${data.mode || 'minimal'}</p>
                    `;
                    
                    log(`✅ 성공: ${data.games_added}게임, ${data.pairs_found}페어`);
                    
                    // 페어가 발견된 경우
                    if (data.pairs_found > 0) {
                        log(`🎯 페어 발견: ${data.pairs_found}개!`);
                    }
                } else {
                    output.innerHTML = `<div style="color: #dc3545;">❌ 오류: ${data.error}</div>`;
                    log(`❌ 오류: ${data.error}`);
                }
                
            } catch (error) {
                output.innerHTML = `<div style="color: #dc3545;">❌ 연결 오류: ${error.message}</div>`;
                log(`❌ 연결 오류: ${error.message}`);
            }
            
            isRunning = false;
            btn.disabled = false;
            btn.textContent = '📊 데모 데이터 추가';
        }

        async function getStats() {
            log('📈 통계 조회 요청');
            
            try {
                const response = await fetch('/api/minimal-stats');
                const data = await response.json();
                
                if (data.success) {
                    const output = document.getElementById('output');
                    
                    // 테이블별 통계 HTML 생성
                    let tableBreakdown = '';
                    if (data.stats.table_breakdown) {
                        tableBreakdown = '<h4>📋 테이블별 현황</h4>';
                        for (const [tableName, tableData] of Object.entries(data.stats.table_breakdown)) {
                            const metadata = tableData.metadata;
                            const vipIcon = metadata.type === 'VIP' ? '👑' : metadata.type === '프리미엄' ? '✨' : '🎰';
                            tableBreakdown += `
                                <div style="margin: 10px 0; padding: 15px; border: 2px solid ${metadata.type === 'VIP' ? '#FFD700' : metadata.type === '프리미엄' ? '#C0C0C0' : '#ddd'}; border-radius: 8px; background: ${metadata.type === 'VIP' ? '#FFF8DC' : metadata.type === '프리미엄' ? '#F8F8FF' : '#F9F9F9'};">
                                    <div style="font-weight: bold; font-size: 1.1em; color: ${metadata.type === 'VIP' ? '#B8860B' : metadata.type === '프리미엄' ? '#4169E1' : '#333'};">
                                        ${vipIcon} ${metadata.name_kr} (${tableName})
                                    </div>
                                    <div style="margin: 5px 0; color: #666;">
                                        📍 ${metadata.location} | 👥 수용: ${metadata.capacity} | 🎭 ${metadata.vip_level}
                                    </div>
                                    <div style="margin: 5px 0;">
                                        게임: ${tableData.games}개 | 페어: ${tableData.pairs}개 | 페어율: ${tableData.pair_rate}%
                                    </div>
                                    <div style="font-size: 0.9em; color: #888;">
                                        💰 ${metadata.limit} | ✨ ${metadata.features}
                                    </div>
                                    <div style="font-size: 0.8em; color: #999;">
                                        마지막 활동: ${tableData.last_activity || '없음'}
                                    </div>
                                </div>
                            `;
                        }
                    }
                    
                    output.innerHTML = `
                        <div class="success">📊 전체 통계</div>
                        <p><strong>총 게임:</strong> ${data.stats.total_games}개</p>
                        <p><strong>총 페어:</strong> ${data.stats.total_pairs}개</p>
                        <p><strong>전체 페어율:</strong> ${data.stats.pair_rate}%</p>
                        <p><strong>활성 테이블:</strong> ${data.stats.active_tables}개</p>
                        <p><strong>데이터베이스:</strong> ${data.stats.db_size} KB</p>
                        ${tableBreakdown}
                    `;
                    log(`📊 전체통계: ${data.stats.total_games}게임, ${data.stats.total_pairs}페어, ${data.stats.active_tables}개 테이블 활성`);
                } else {
                    log(`❌ 통계 조회 실패: ${data.error}`);
                }
                
            } catch (error) {
                log(`❌ 통계 조회 오류: ${error.message}`);
            }
        }

        async function getRealData() {
            log('🎯 실제 baccarat_data.json 데이터 조회 요청');
            
            try {
                const response = await fetch('/api/real-data');
                const data = await response.json();
                
                if (data.success) {
                    const output = document.getElementById('output');
                    
                    // 실제 vs 생성 데이터 비교
                    let comparisonHtml = `
                        <div style="background: #e8f5e8; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                            <h4 style="color: #28a745; margin: 0 0 10px 0;">🎯 실제 페어 데이터 (baccarat_data.json)</h4>
                            <p><strong>데이터 소스:</strong> ${data.source}</p>
                            <p><strong>마지막 업데이트:</strong> ${data.stats.data_updated || '정보없음'}</p>
                        </div>
                    `;
                    
                    // 테이블별 실제 데이터 HTML 생성
                    let realTableBreakdown = '<h4>📋 실제 테이블별 페어 현황</h4>';
                    for (const [tableName, tableData] of Object.entries(data.stats.table_breakdown)) {
                        const metadata = tableData.metadata;
                        const vipIcon = metadata.type === 'VIP' ? '👑' : metadata.type === '프리미엄' ? '✨' : '🎰';
                        
                        // 최근 페어 정보
                        let recentPairsHtml = '';
                        if (tableData.recent_pairs && tableData.recent_pairs.length > 0) {
                            recentPairsHtml = '<div style="margin-top: 10px;"><strong>최근 페어:</strong>';
                            tableData.recent_pairs.forEach(pair => {
                                recentPairsHtml += `<div style="font-size: 0.8em; color: #666; margin: 2px 0;">
                                    🎯 ${pair.pair_type} - ${pair.pair_cards?.join(', ') || 'N/A'} (${new Date(pair.game_time).toLocaleString()})
                                </div>`;
                            });
                            recentPairsHtml += '</div>';
                        }
                        
                        realTableBreakdown += `
                            <div style="margin: 10px 0; padding: 15px; border: 2px solid ${metadata.type === 'VIP' ? '#FFD700' : metadata.type === '프리미엄' ? '#C0C0C0' : '#28a745'}; border-radius: 8px; background: ${metadata.type === 'VIP' ? '#FFF8DC' : metadata.type === '프리미엄' ? '#F8F8FF' : '#F0FFF0'};">
                                <div style="font-weight: bold; font-size: 1.1em; color: ${metadata.type === 'VIP' ? '#B8860B' : metadata.type === '프리미엄' ? '#4169E1' : '#28a745'};">
                                    ${vipIcon} ${metadata.name_kr} (${tableName}) 
                                    <span style="background: #28a745; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">실제 데이터</span>
                                </div>
                                <div style="margin: 5px 0; color: #666;">
                                    📍 ${metadata.location} | 👥 수용: ${metadata.capacity} | 🎭 ${metadata.vip_level}
                                </div>
                                <div style="margin: 5px 0;">
                                    게임: ${tableData.games}개 | 페어: ${tableData.pairs}개 | <strong>페어율: ${tableData.pair_rate}%</strong>
                                </div>
                                <div style="font-size: 0.9em; color: #888;">
                                    💰 ${metadata.limit} | ✨ ${metadata.features}
                                </div>
                                <div style="font-size: 0.8em; color: #999;">
                                    마지막 게임: ${tableData.last_game_time || '없음'}
                                </div>
                                ${recentPairsHtml}
                            </div>
                        `;
                    }
                    
                    output.innerHTML = `
                        ${comparisonHtml}
                        <div class="success">📊 실제 페어 데이터 통계</div>
                        <p><strong>총 실제 게임:</strong> ${data.stats.total_games}개</p>
                        <p><strong>총 실제 페어:</strong> ${data.stats.total_pairs}개</p>
                        <p><strong>실제 페어율:</strong> <span style="color: #28a745; font-weight: bold; font-size: 1.2em;">${data.stats.pair_rate}%</span></p>
                        <p><strong>활성 테이블:</strong> ${data.stats.active_tables}개</p>
                        ${realTableBreakdown}
                    `;
                    log(`📊 실제 데이터: ${data.stats.total_games}게임, ${data.stats.total_pairs}페어, ${data.stats.pair_rate}% 페어율`);
                } else {
                    log(`❌ 실제 데이터 조회 실패: ${data.error}`);
                }
                
            } catch (error) {
                log(`❌ 실제 데이터 조회 오류: ${error.message}`);
            }
        }

        // 페이지 로드 시
        window.onload = function() {
            log('🚀 Minimal Demo API 준비됨');
            log('💡 AsyncIO 없는 순수 Flask 환경');
            log('🎯 "실제 페어 데이터" 버튼으로 baccarat_data.json 확인 가능');
        };
    </script>
</body>
</html>
"""

def init_minimal_db():
    """미니멀 데이터베이스 초기화"""
    db_path = "minimal_demo.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 간단한 게임 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS minimal_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            game_number INTEGER,
            player_cards TEXT,
            banker_cards TEXT,
            has_pair BOOLEAN DEFAULT 0,
            pair_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ 미니멀 데이터베이스 초기화 완료: {db_path}")

def load_real_table_names():
    """실제 시스템의 테이블명 로드"""
    try:
        baccarat_data_path = Path(__file__).parent / "baccarat_data.json"
        if baccarat_data_path.exists():
            with open(baccarat_data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                table_names = list(data.get('tables', {}).keys())
                logger.info(f"✅ 실제 테이블명 로드: {table_names}")
                return table_names
    except Exception as e:
        logger.warning(f"⚠️ 테이블명 로드 실패: {e}")
    
    # 폴백: 기본 테이블명
    return ['table_001', 'table_002', 'table_003', 'table_004', 'table_005']

def get_enhanced_table_metadata(table_name: str) -> Dict[str, str]:
    """향상된 테이블 메타데이터 반환"""
    table_info = {
        'table_001': {
            'name_kr': '프리미엄 홀 A', 
            'name_en': 'Premium Hall A',
            'type': '일반', 
            'vip_level': 'Standard',
            'limit': '1만~10만원',
            'location': '메인플로어 1층',
            'capacity': '8명',
            'features': '일반 접근, 표준 서비스'
        },
        'table_002': {
            'name_kr': '프리미엄 홀 B', 
            'name_en': 'Premium Hall B',
            'type': '일반', 
            'vip_level': 'Standard',
            'limit': '1만~10만원',
            'location': '메인플로어 1층',
            'capacity': '8명',
            'features': '일반 접근, 표준 서비스'
        },
        'table_003': {
            'name_kr': '골드 라운지', 
            'name_en': 'Gold Lounge',
            'type': '프리미엄', 
            'vip_level': 'Gold',
            'limit': '2만~20만원',
            'location': '메인플로어 2층',
            'capacity': '6명',
            'features': '골드 멤버 우선, 프리미엄 서비스'
        },
        'table_004': {
            'name_kr': 'VIP 살롱 다이아몬드', 
            'name_en': 'VIP Salon Diamond',
            'type': 'VIP', 
            'vip_level': 'Diamond',
            'limit': '10만~100만원',
            'location': 'VIP플로어 3층',
            'capacity': '4명',
            'features': 'VIP 전용, 개인 서비스, 마스터 딜러'
        },
        'table_005': {
            'name_kr': 'VIP 살롱 플래티넘', 
            'name_en': 'VIP Salon Platinum',
            'type': 'VIP', 
            'vip_level': 'Platinum',
            'limit': '10만~100만원',
            'location': 'VIP플로어 3층',
            'capacity': '4명',
            'features': 'VIP 전용, 개인 서비스, 마스터 딜러, 전용 입구'
        }
    }
    return table_info.get(table_name, {
        'name_kr': f'알 수 없는 방 ({table_name})', 
        'name_en': f'Unknown Room ({table_name})',
        'type': '일반', 
        'vip_level': 'Standard',
        'limit': '정보없음',
        'location': '정보없음',
        'capacity': '정보없음',
        'features': '정보없음'
    })

def generate_demo_game():
    """단일 데모 게임 생성 - 실제 테이블명 사용"""
    cards = ['A♠', '2♥', '3♦', '4♣', '5♠', '6♥', '7♦', '8♣', '9♠', '10♥', 'J♦', 'Q♣', 'K♠']
    table_names = load_real_table_names()
    
    # 카드 선택
    player_cards = random.sample(cards, 2)
    banker_cards = random.sample(cards, 2)
    
    # 페어 감지 (테스트용 확률 증가)
    player_values = [card[:-1] for card in player_cards]  # 슈트 제거
    banker_values = [card[:-1] for card in banker_cards]
    
    has_pair = False
    pair_type = None
    
    # 실제 페어 체크
    player_has_pair = player_values[0] == player_values[1]
    banker_has_pair = banker_values[0] == banker_values[1]
    
    # 테스트용: 25% 확률로 강제 페어 생성
    if not player_has_pair and not banker_has_pair and random.random() < 0.25:
        # 강제로 플레이어 페어 생성
        player_cards = [cards[0], cards[0]]  # 같은 값 카드로 변경
        player_has_pair = True
    
    # 페어 타입 결정
    if player_has_pair and banker_has_pair:
        has_pair = True
        pair_type = 'BOTH_PAIR'
    elif player_has_pair:
        has_pair = True
        pair_type = 'PLAYER_PAIR'
    elif banker_has_pair:
        has_pair = True
        pair_type = 'BANKER_PAIR'
    
    return {
        'table_name': random.choice(table_names),
        'game_number': random.randint(1, 10000),
        'player_cards': ', '.join(player_cards),
        'banker_cards': ', '.join(banker_cards),
        'has_pair': has_pair,
        'pair_type': pair_type
    }

@app.route('/')
def index():
    """메인 페이지"""
    return render_template_string(MINIMAL_TEMPLATE)

@app.route('/api/minimal-demo', methods=['POST'])
def minimal_demo_api():
    """미니멀 데모 API - AsyncIO 없음"""
    start_time = datetime.now()
    logger.info("🎯 미니멀 데모 API 호출됨")
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect("minimal_demo.db")
        cursor = conn.cursor()
        
        # 5-15개 게임 생성
        game_count = random.randint(5, 15)
        pair_count = 0
        
        for i in range(game_count):
            game = generate_demo_game()
            
            cursor.execute("""
                INSERT INTO minimal_games 
                (table_name, game_number, player_cards, banker_cards, has_pair, pair_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                game['table_name'], game['game_number'],
                game['player_cards'], game['banker_cards'],
                game['has_pair'], game['pair_type']
            ))
            
            if game['has_pair']:
                pair_count += 1
                logger.info(f"🎯 페어 발생: {game['table_name']} - {game['pair_type']}")
        
        conn.commit()
        conn.close()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        success_message = f'{game_count}개 게임 추가 ({pair_count}개 페어) - 미니멀 모드'
        
        logger.info(f"✅ 미니멀 데모 완료: {success_message}")
        
        return jsonify({
            'success': True,
            'message': success_message,
            'games_added': game_count,
            'pairs_found': pair_count,
            'processing_time': f'{processing_time:.2f}s',
            'mode': 'minimal_safe',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 미니멀 데모 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '데모 데이터 처리 중 오류 발생',
            'mode': 'minimal_safe',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/real-data', methods=['GET'])
def real_baccarat_data_api():
    """실제 baccarat_data.json 페어 데이터 API"""
    try:
        baccarat_data_path = Path(__file__).parent / "baccarat_data.json"
        
        if not baccarat_data_path.exists():
            return jsonify({
                'success': False,
                'error': 'baccarat_data.json 파일이 없습니다',
                'timestamp': datetime.now().isoformat()
            }), 404
        
        with open(baccarat_data_path, 'r', encoding='utf-8') as f:
            real_data = json.load(f)
        
        # 실제 데이터 파싱
        enhanced_stats = {}
        total_real_games = 0
        total_real_pairs = 0
        
        for table_id, table_data in real_data.get('tables', {}).items():
            games = table_data.get('total_games', 0)
            pairs = table_data.get('pair_count', 0)
            pair_rate = (pairs / games * 100) if games > 0 else 0
            
            # 향상된 메타데이터
            table_metadata = get_enhanced_table_metadata(table_id)
            
            enhanced_stats[table_id] = {
                'games': games,
                'pairs': pairs,
                'pair_rate': round(pair_rate, 2),
                'last_game_time': table_data.get('last_game_time'),
                'recent_pairs': table_data.get('recent_pairs', []),
                'metadata': table_metadata,
                'source': 'real_data'  # 실제 데이터 표시
            }
            
            total_real_games += games
            total_real_pairs += pairs
        
        global_pair_rate = (total_real_pairs / total_real_games * 100) if total_real_games > 0 else 0
        
        return jsonify({
            'success': True,
            'source': 'baccarat_data.json (실제 데이터)',
            'stats': {
                'total_games': total_real_games,
                'total_pairs': total_real_pairs,
                'pair_rate': round(global_pair_rate, 2),
                'active_tables': len([t for t in enhanced_stats.values() if t['games'] > 0]),
                'table_breakdown': enhanced_stats,
                'data_updated': real_data.get('global_stats', {}).get('last_updated'),
                'db_size': 0  # JSON 파일이므로 0
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 실제 데이터 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/minimal-stats', methods=['GET'])
def minimal_stats_api():
    """미니멀 통계 API - 테이블별 상세 정보 포함"""
    try:
        conn = sqlite3.connect("minimal_demo.db")
        cursor = conn.cursor()
        
        # 전체 통계
        cursor.execute("SELECT COUNT(*) FROM minimal_games")
        total_games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM minimal_games WHERE has_pair = 1")
        total_pairs = cursor.fetchone()[0]
        
        pair_rate = round((total_pairs / total_games * 100) if total_games > 0 else 0, 2)
        
        # 테이블별 통계
        table_stats = {}
        table_names = load_real_table_names()
        
        for table_name in table_names:
            cursor.execute("SELECT COUNT(*) FROM minimal_games WHERE table_name = ?", (table_name,))
            table_games = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM minimal_games WHERE table_name = ? AND has_pair = 1", (table_name,))
            table_pairs = cursor.fetchone()[0]
            
            cursor.execute("SELECT created_at FROM minimal_games WHERE table_name = ? ORDER BY created_at DESC LIMIT 1", (table_name,))
            last_activity = cursor.fetchone()
            last_activity = last_activity[0] if last_activity else None
            
            table_metadata = get_enhanced_table_metadata(table_name)
            
            table_stats[table_name] = {
                'games': table_games,
                'pairs': table_pairs,
                'pair_rate': round((table_pairs / table_games * 100) if table_games > 0 else 0, 2),
                'last_activity': last_activity,
                'metadata': table_metadata
            }
        
        # 파일 크기
        db_path = Path("minimal_demo.db")
        db_size = round(db_path.stat().st_size / 1024, 2) if db_path.exists() else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_games': total_games,
                'total_pairs': total_pairs,
                'pair_rate': pair_rate,
                'db_size': db_size,
                'table_breakdown': table_stats,
                'active_tables': len([t for t in table_stats.values() if t['games'] > 0])
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ 미니멀 통계 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print("Minimal Demo API Server - AsyncIO Safe")
    print("=" * 50)
    print("AsyncIO 충돌을 완전히 회피한 순수 Flask 서버")
    print("포트: 5557")
    print("URL: http://127.0.0.1:5557")
    print("=" * 50)
    
    # 데이터베이스 초기화
    init_minimal_db()
    
    # Flask 서버 실행
    app.run(host='127.0.0.1', port=5557, debug=False)