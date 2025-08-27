#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Next Generation System v1.0
AsyncIO 네이티브 지원, WebSocket 실시간 통신, 자동 API 문서화
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
import asyncio
import json
import random
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
import aiosqlite
from contextlib import asynccontextmanager
import re
from typing import Union

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Pydantic Models ===

class TableMetadata(BaseModel):
    name_kr: str = Field(..., description="한국어 테이블명")
    type: str = Field(..., description="테이블 유형 (일반/VIP)")
    limit: str = Field(..., description="베팅 한도")

class GameData(BaseModel):
    table_name: str = Field(..., description="테이블명")
    game_number: int = Field(..., description="게임번호")
    player_cards: List[str] = Field(..., description="플레이어 카드")
    banker_cards: List[str] = Field(..., description="뱅커 카드")
    has_pair: bool = Field(False, description="페어 발생 여부")
    pair_type: Optional[str] = Field(None, description="페어 유형")
    timestamp: Optional[datetime] = Field(None, description="생성 시간")

class DemoRequest(BaseModel):
    game_count: int = Field(10, ge=1, le=50, description="생성할 게임 수")
    table_preference: Optional[str] = Field(None, description="선호 테이블")

class DemoResponse(BaseModel):
    success: bool
    message: str
    games_added: int
    pairs_found: int
    processing_time: float
    mode: str = "fastapi_async"
    table_distribution: Dict[str, int] = Field(default_factory=dict)

class StatsResponse(BaseModel):
    success: bool
    stats: Dict[str, Union[int, float, Dict]]
    timestamp: datetime

class WebSocketMessage(BaseModel):
    type: str = Field(..., description="메시지 유형")
    data: Dict = Field(..., description="메시지 데이터")
    timestamp: datetime = Field(default_factory=datetime.now)

class PacketData(BaseModel):
    packet_content: str = Field(..., description="패킷 데이터 내용")
    source: str = Field("manual", description="데이터 소스")

class PacketResponse(BaseModel):
    success: bool
    games_processed: int
    pairs_found: int
    processing_time: float
    message: str

# === Packet Decoder ===

class BaccaratPacketDecoder:
    """패킷 데이터 디코더"""
    
    def __init__(self):
        self.card_suits = {'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs', 'S': 'Spades'}
        self.card_ranks = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
                          '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13}
    
    def parse_packet_content(self, content: str) -> List[GameData]:
        """패킷 내용을 파싱하여 게임 데이터 추출"""
        games = []
        pattern = r'(\w+)_(\d+)_(\d{14})_([A-Z]+)_([A-Z0-9 ]+)'
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            match = re.match(pattern, line)
            if match:
                table_name, game_id, timestamp, result, cards = match.groups()
                game_data = self._create_game_data(table_name, game_id, timestamp, result, cards)
                if game_data:
                    games.append(game_data)
            else:
                logger.warning(f"잘못된 패킷 형식 라인 {line_num}: {line}")
        
        return games
    
    def _create_game_data(self, table_name: str, game_id: str, timestamp: str, result: str, cards: str) -> Optional[GameData]:
        """게임 데이터 객체 생성"""
        try:
            game_time = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
            card_list = cards.split()
            
            if len(card_list) < 4:
                return None
            
            player_cards = card_list[:2]
            banker_cards = card_list[2:4]
            
            # 추가 카드 처리
            if len(card_list) > 4:
                if len(card_list) >= 5:
                    player_cards.append(card_list[4])
                if len(card_list) >= 6:
                    banker_cards.append(card_list[5])
            
            # 페어 정보 계산
            player_has_pair = len(player_cards) >= 2 and player_cards[0][0] == player_cards[1][0]
            banker_has_pair = len(banker_cards) >= 2 and banker_cards[0][0] == banker_cards[1][0]
            
            has_pair = player_has_pair or banker_has_pair
            pair_type = None
            
            if player_has_pair and banker_has_pair:
                pair_type = 'BOTH_PAIR'
            elif player_has_pair:
                pair_type = 'PLAYER_PAIR'
            elif banker_has_pair:
                pair_type = 'BANKER_PAIR'
            
            return GameData(
                table_name=table_name,
                game_number=int(game_id),
                player_cards=player_cards,
                banker_cards=banker_cards,
                has_pair=has_pair,
                pair_type=pair_type,
                timestamp=game_time
            )
            
        except Exception as e:
            logger.error(f"게임 데이터 생성 실패: {e}")
            return None

# === WebSocket Manager ===

class WebSocketManager:
    """실시간 WebSocket 연결 관리"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """WebSocket 연결 수락"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            'client_id': client_id or f"client_{len(self.active_connections)}",
            'connected_at': datetime.now(),
            'message_count': 0
        }
        logger.info(f"✅ WebSocket 클라이언트 연결: {client_id} (총 {len(self.active_connections)}개)")
    
    def disconnect(self, websocket: WebSocket):
        """WebSocket 연결 해제"""
        if websocket in self.active_connections:
            client_info = self.connection_info.pop(websocket, {})
            self.active_connections.remove(websocket)
            logger.info(f"❌ WebSocket 클라이언트 연결 해제: {client_info.get('client_id')} (총 {len(self.active_connections)}개)")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """개별 클라이언트에게 메시지 전송"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
            if websocket in self.connection_info:
                self.connection_info[websocket]['message_count'] += 1
        except Exception as e:
            logger.error(f"개별 메시지 전송 실패: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """모든 연결된 클라이언트에게 브로드캐스트"""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message, ensure_ascii=False)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
                if connection in self.connection_info:
                    self.connection_info[connection]['message_count'] += 1
            except:
                disconnected.append(connection)
        
        # 끊어진 연결 정리
        for connection in disconnected:
            self.disconnect(connection)
        
        if disconnected:
            logger.warning(f"⚠️ {len(disconnected)}개 연결이 끊어져 정리됨")
    
    def get_connection_stats(self) -> Dict:
        """연결 통계 반환"""
        return {
            'active_connections': len(self.active_connections),
            'total_messages_sent': sum(info.get('message_count', 0) for info in self.connection_info.values()),
            'connections_info': [
                {
                    'client_id': info['client_id'],
                    'connected_at': info['connected_at'].isoformat(),
                    'message_count': info['message_count']
                }
                for info in self.connection_info.values()
            ]
        }

# === Database Manager ===

class AsyncDatabaseManager:
    """비동기 데이터베이스 관리자"""
    
    def __init__(self, db_path: str = "fastapi_demo.db"):
        self.db_path = db_path
    
    async def init_database(self):
        """데이터베이스 초기화"""
        async with aiosqlite.connect(self.db_path) as db:
            # 테이블 생성
            await db.execute("""
                CREATE TABLE IF NOT EXISTS games (
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
            
            # 인덱스 생성 (별도로)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_table_name ON games(table_name)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON games(created_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_has_pair ON games(has_pair)")
            
            await db.commit()
        logger.info(f"✅ FastAPI 데이터베이스 초기화 완료: {self.db_path}")
    
    async def save_game(self, game_data: GameData) -> int:
        """게임 데이터 저장"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO games (table_name, game_number, player_cards, banker_cards, has_pair, pair_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                game_data.table_name,
                game_data.game_number,
                ', '.join(game_data.player_cards),
                ', '.join(game_data.banker_cards),
                game_data.has_pair,
                game_data.pair_type
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_stats(self) -> Dict:
        """통계 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            # 전체 통계
            async with db.execute("SELECT COUNT(*) FROM games") as cursor:
                total_games = (await cursor.fetchone())[0]
            
            async with db.execute("SELECT COUNT(*) FROM games WHERE has_pair = 1") as cursor:
                total_pairs = (await cursor.fetchone())[0]
            
            # 테이블별 통계
            table_stats = {}
            table_names = ['table_001', 'table_002', 'table_003', 'table_004', 'table_005']
            
            for table_name in table_names:
                async with db.execute("SELECT COUNT(*) FROM games WHERE table_name = ?", (table_name,)) as cursor:
                    table_games = (await cursor.fetchone())[0]
                
                async with db.execute("SELECT COUNT(*) FROM games WHERE table_name = ? AND has_pair = 1", (table_name,)) as cursor:
                    table_pairs = (await cursor.fetchone())[0]
                
                async with db.execute("SELECT created_at FROM games WHERE table_name = ? ORDER BY created_at DESC LIMIT 1", (table_name,)) as cursor:
                    result = await cursor.fetchone()
                    last_activity = result[0] if result else None
                
                table_stats[table_name] = {
                    'games': table_games,
                    'pairs': table_pairs,
                    'pair_rate': round((table_pairs / table_games * 100) if table_games > 0 else 0, 2),
                    'last_activity': last_activity
                }
            
            # 파일 크기
            db_size = round(Path(self.db_path).stat().st_size / 1024, 2) if Path(self.db_path).exists() else 0
            
            return {
                'total_games': total_games,
                'total_pairs': total_pairs,
                'pair_rate': round((total_pairs / total_games * 100) if total_games > 0 else 0, 2),
                'db_size': db_size,
                'table_breakdown': table_stats,
                'active_tables': len([t for t in table_stats.values() if t['games'] > 0])
            }

# === Global Instances ===

websocket_manager = WebSocketManager()
db_manager = AsyncDatabaseManager()
packet_decoder = BaccaratPacketDecoder()

# === Startup/Shutdown ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작
    logger.info("🚀 FastAPI 차세대 시스템 시작")
    await db_manager.init_database()
    
    # 백그라운드 모니터링 시작
    asyncio.create_task(background_monitoring())
    
    yield
    
    # 종료
    logger.info("🔚 FastAPI 차세대 시스템 종료")

# === FastAPI App ===

app = FastAPI(
    title="Two Very Auto - Next Generation",
    description="AsyncIO 네이티브 바카라 모니터링 시스템",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 정적 파일 서빙 설정
try:
    app.mount("/static", StaticFiles(directory=".", html=True), name="static")
except Exception:
    # 정적 파일 디렉토리가 없을 경우 무시
    logger.warning("정적 파일 디렉토리 설정 실패 - 무시함")

# === WebSocket Endpoints ===

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """실시간 WebSocket 연결"""
    await websocket_manager.connect(websocket, client_id)
    
    try:
        # 초기 데이터 전송
        stats = await db_manager.get_stats()
        await websocket_manager.send_personal_message({
            'type': 'init',
            'data': stats,
            'message': f'환영합니다, {client_id}!'
        }, websocket)
        
        while True:
            # 클라이언트로부터 메시지 수신 대기
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 에코 응답
            await websocket_manager.send_personal_message({
                'type': 'echo',
                'data': message,
                'timestamp': datetime.now().isoformat()
            }, websocket)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

# === API Endpoints ===

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """메인 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Two Very Auto - Next Generation</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #333; margin: 0; font-size: 2.5em; }
            .header p { color: #666; font-size: 1.2em; margin: 10px 0; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }
            .feature { background: #f8f9fa; border-radius: 10px; padding: 20px; border-left: 4px solid #007bff; }
            .feature h3 { color: #007bff; margin: 0 0 10px 0; }
            .buttons { text-align: center; margin: 30px 0; }
            .btn { background: #007bff; color: white; border: none; padding: 15px 30px; border-radius: 8px; cursor: pointer; font-size: 16px; margin: 10px; text-decoration: none; display: inline-block; transition: all 0.3s; }
            .btn:hover { background: #0056b3; transform: translateY(-2px); }
            .btn.secondary { background: #28a745; }
            .btn.secondary:hover { background: #1e7e34; }
            .status { background: #e3f2fd; border-radius: 10px; padding: 20px; margin: 20px 0; }
            .websocket-status { color: #666; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Two Very Auto - Next Generation</h1>
                <p>AsyncIO 네이티브 바카라 모니터링 시스템</p>
            </div>
            
            <div class="features">
                <div class="feature">
                    <h3>⚡ AsyncIO 네이티브</h3>
                    <p>완전한 비동기 처리로 최고 성능 달성</p>
                </div>
                <div class="feature">
                    <h3>🌐 실시간 WebSocket</h3>
                    <p>실시간 데이터 스트림 및 알림</p>
                </div>
                <div class="feature">
                    <h3>📖 자동 API 문서화</h3>
                    <p>OpenAPI/Swagger 자동 생성</p>
                </div>
                <div class="feature">
                    <h3>🔧 타입 안전성</h3>
                    <p>Pydantic 모델로 데이터 검증</p>
                </div>
            </div>
            
            <div class="buttons">
                <a href="/docs" class="btn">📖 API 문서</a>
                <a href="/redoc" class="btn secondary">📚 ReDoc</a>
                <button class="btn" onclick="testDemo()">🎲 데모 테스트</button>
                <button class="btn" onclick="connectWebSocket()">🌐 WebSocket 연결</button>
                <button class="btn" onclick="testPacket()">📦 패킷 테스트</button>
                <a href="/static/realtime_dashboard.html" class="btn" target="_blank">📊 실시간 대시보드</a>
            </div>
            
            <div class="status" id="status">
                <h3>📊 시스템 상태</h3>
                <div id="statusContent">대기 중...</div>
            </div>
            
            <div class="status">
                <h3>🔗 WebSocket 연결</h3>
                <div class="websocket-status" id="wsStatus">연결 안됨</div>
                <div id="wsMessages" style="max-height: 200px; overflow-y: auto; margin-top: 10px;"></div>
            </div>
        </div>

        <script>
            let ws = null;
            
            async function testDemo() {
                const statusDiv = document.getElementById('statusContent');
                statusDiv.innerHTML = '<span style="color: #ff9800;">⏳ 데모 실행 중...</span>';
                
                try {
                    const response = await fetch('/api/demo', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ game_count: 15 })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        statusDiv.innerHTML = `
                            <span style="color: #4caf50;">✅ 데모 성공!</span><br>
                            게임 추가: ${data.games_added}개<br>
                            페어 발견: ${data.pairs_found}개<br>
                            처리 시간: ${data.processing_time}초<br>
                            모드: ${data.mode}
                        `;
                    } else {
                        statusDiv.innerHTML = `<span style="color: #f44336;">❌ 오류: ${data.error}</span>`;
                    }
                } catch (error) {
                    statusDiv.innerHTML = `<span style="color: #f44336;">❌ 연결 오류: ${error.message}</span>`;
                }
            }
            
            function connectWebSocket() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.close();
                    return;
                }
                
                const clientId = 'client_' + Math.random().toString(36).substring(7);
                ws = new WebSocket(`ws://127.0.0.1:8000/ws/${clientId}`);
                
                ws.onopen = function(event) {
                    document.getElementById('wsStatus').innerHTML = `<span style="color: #4caf50;">✅ 연결됨 (${clientId})</span>`;
                    addWsMessage('🔗 WebSocket 연결 성공', 'success');
                };
                
                ws.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    addWsMessage(`📨 ${message.type}: ${JSON.stringify(message.data, null, 2)}`, 'info');
                };
                
                ws.onclose = function(event) {
                    document.getElementById('wsStatus').innerHTML = '<span style="color: #f44336;">❌ 연결 끊어짐</span>';
                    addWsMessage('🔌 WebSocket 연결 종료', 'warning');
                };
                
                ws.onerror = function(error) {
                    addWsMessage(`❌ WebSocket 오류: ${error}`, 'error');
                };
            }
            
            async function testPacket() {
                const statusDiv = document.getElementById('statusContent');
                statusDiv.innerHTML = '<span style="color: #ff9800;">⏳ 패킷 테스트 중...</span>';
                
                try {
                    // 데모 패킷 생성
                    const demoResponse = await fetch('/api/packet/demo');
                    const demoData = await demoResponse.json();
                    
                    if (!demoData.success) {
                        throw new Error('데모 패킷 생성 실패');
                    }
                    
                    addWsMessage(`📦 데모 패킷 생성됨: ${demoData.lines_count}라인`, 'info');
                    
                    // 패킷 처리
                    const processResponse = await fetch('/api/packet/process', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            packet_content: demoData.packet_content,
                            source: 'demo_test'
                        })
                    });
                    
                    const processData = await processResponse.json();
                    
                    if (processData.success) {
                        statusDiv.innerHTML = `
                            <span style="color: #4caf50;">✅ 패킷 처리 성공!</span><br>
                            처리 게임: ${processData.games_processed}개<br>
                            발견 페어: ${processData.pairs_found}개<br>
                            처리 시간: ${processData.processing_time.toFixed(3)}초<br>
                            메시지: ${processData.message}
                        `;
                        addWsMessage(`✅ 패킷 처리 완료: ${processData.games_processed}게임, ${processData.pairs_found}페어`, 'success');
                    } else {
                        statusDiv.innerHTML = `<span style="color: #f44336;">❌ 패킷 처리 실패: ${processData.message}</span>`;
                        addWsMessage(`❌ 패킷 처리 실패: ${processData.message}`, 'error');
                    }
                    
                } catch (error) {
                    statusDiv.innerHTML = `<span style="color: #f44336;">❌ 패킷 테스트 오류: ${error.message}</span>`;
                    addWsMessage(`❌ 패킷 테스트 오류: ${error.message}`, 'error');
                }
            }
            
            function addWsMessage(message, type) {
                const messagesDiv = document.getElementById('wsMessages');
                const timestamp = new Date().toLocaleTimeString();
                const colorMap = {
                    success: '#4caf50',
                    info: '#2196f3',
                    warning: '#ff9800',
                    error: '#f44336'
                };
                
                messagesDiv.innerHTML += `
                    <div style="color: ${colorMap[type] || '#333'}; margin: 5px 0;">
                        [${timestamp}] ${message}
                    </div>
                `;
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    return html_content

@app.post("/api/demo", response_model=DemoResponse)
async def create_demo_data(request: DemoRequest, background_tasks: BackgroundTasks):
    """비동기 데모 데이터 생성"""
    start_time = datetime.now()
    
    logger.info(f"🎯 FastAPI 데모 API 호출: {request.game_count}게임 요청")
    
    # 비동기 데이터 생성
    games_data, table_distribution = await generate_demo_games_async(request.game_count, request.table_preference)
    
    # 데이터베이스 저장 및 페어 카운트
    pairs_found = 0
    for game_data in games_data:
        await db_manager.save_game(game_data)
        if game_data.has_pair:
            pairs_found += 1
    
    processing_time = (datetime.now() - start_time).total_seconds()
    
    # 백그라운드 작업: WebSocket 브로드캐스트
    background_tasks.add_task(broadcast_demo_update, len(games_data), pairs_found, table_distribution)
    
    response = DemoResponse(
        success=True,
        message=f"{len(games_data)}개 게임 추가 ({pairs_found}개 페어) - FastAPI 비동기",
        games_added=len(games_data),
        pairs_found=pairs_found,
        processing_time=processing_time,
        table_distribution=table_distribution
    )
    
    logger.info(f"✅ FastAPI 데모 완료: {response.message}")
    return response

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """통계 조회 API"""
    stats = await db_manager.get_stats()
    return StatsResponse(
        success=True,
        stats=stats,
        timestamp=datetime.now()
    )

@app.get("/api/websocket/stats")
async def get_websocket_stats():
    """WebSocket 연결 통계"""
    return {
        'success': True,
        'websocket_stats': websocket_manager.get_connection_stats(),
        'timestamp': datetime.now().isoformat()
    }

@app.post("/api/packet/process", response_model=PacketResponse)
async def process_packet_data(packet: PacketData, background_tasks: BackgroundTasks):
    """패킷 데이터 처리 API"""
    start_time = datetime.now()
    
    logger.info(f"🔍 패킷 데이터 처리 시작 (소스: {packet.source})")
    
    try:
        # 패킷 데이터 파싱
        games_data = packet_decoder.parse_packet_content(packet.packet_content)
        
        if not games_data:
            return PacketResponse(
                success=False,
                games_processed=0,
                pairs_found=0,
                processing_time=0.0,
                message="유효한 게임 데이터를 찾을 수 없습니다"
            )
        
        # 데이터베이스 저장
        pairs_found = 0
        for game_data in games_data:
            await db_manager.save_game(game_data)
            if game_data.has_pair:
                pairs_found += 1
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 백그라운드 작업: WebSocket 브로드캐스트
        background_tasks.add_task(
            broadcast_packet_update, 
            len(games_data), 
            pairs_found, 
            packet.source
        )
        
        response = PacketResponse(
            success=True,
            games_processed=len(games_data),
            pairs_found=pairs_found,
            processing_time=processing_time,
            message=f"{len(games_data)}개 게임 처리 완료 ({pairs_found}개 페어 발견) - {packet.source}"
        )
        
        logger.info(f"✅ 패킷 처리 완료: {response.message}")
        return response
        
    except Exception as e:
        logger.error(f"❌ 패킷 처리 오류: {e}")
        return PacketResponse(
            success=False,
            games_processed=0,
            pairs_found=0,
            processing_time=(datetime.now() - start_time).total_seconds(),
            message=f"패킷 처리 중 오류: {str(e)}"
        )

@app.get("/api/packet/demo")
async def generate_demo_packet():
    """데모 패킷 데이터 생성"""
    try:
        # 데모 패킷 데이터 생성
        current_time = datetime.now()
        lines = ['# FastAPI Demo Packet Data']
        
        for i in range(10):
            table_name = f"table_{random.randint(1, 5):03d}"
            game_id = 20000 + i
            timestamp = current_time.strftime('%Y%m%d%H%M%S')
            result = random.choice(['PLAYER', 'BANKER', 'TIE'])
            
            # 카드 4-6장 생성
            suits = ['H', 'D', 'C', 'S']
            ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K']
            cards = []
            
            for _ in range(random.randint(4, 6)):
                card = random.choice(ranks) + random.choice(suits)
                cards.append(card)
            
            # 30% 확률로 페어 생성
            if random.random() < 0.3:
                # 플레이어 페어 생성
                cards[0] = 'AH'
                cards[1] = 'AS'
            
            line = f"{table_name}_{game_id}_{timestamp}_{result}_{' '.join(cards)}"
            lines.append(line)
            
            current_time = current_time + timedelta(seconds=random.randint(1, 5))
        
        packet_content = '\n'.join(lines)
        
        return {
            'success': True,
            'packet_content': packet_content,
            'lines_count': len(lines) - 1,  # 헤더 제외
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 데모 패킷 생성 오류: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# === Background Tasks ===

async def generate_demo_games_async(count: int, table_preference: Optional[str] = None) -> tuple[List[GameData], Dict[str, int]]:
    """비동기 데모 게임 생성"""
    cards = ['A♠', '2♥', '3♦', '4♣', '5♠', '6♥', '7♦', '8♣', '9♠', '10♥', 'J♦', 'Q♣', 'K♠']
    table_names = ['table_001', 'table_002', 'table_003', 'table_004', 'table_005']
    
    if table_preference and table_preference in table_names:
        # 70% 확률로 선호 테이블 사용
        weighted_tables = [table_preference] * 7 + [t for t in table_names if t != table_preference] * 1
        table_names = weighted_tables
    
    games_data = []
    table_distribution = {}
    
    for i in range(count):
        # 비동기 처리 시뮬레이션
        await asyncio.sleep(0.001)
        
        # 게임 데이터 생성
        table_name = random.choice(table_names)
        player_cards = random.sample(cards, 2)
        banker_cards = random.sample(cards, 2)
        
        # 페어 감지
        player_values = [card[:-1] for card in player_cards]
        banker_values = [card[:-1] for card in banker_cards]
        
        has_pair = False
        pair_type = None
        
        player_has_pair = player_values[0] == player_values[1]
        banker_has_pair = banker_values[0] == banker_values[1]
        
        # 30% 확률로 강제 페어 (테스트용)
        if not player_has_pair and not banker_has_pair and random.random() < 0.3:
            player_cards = [cards[0], cards[0]]  # A♠ 페어
            player_has_pair = True
        
        if player_has_pair and banker_has_pair:
            has_pair, pair_type = True, 'BOTH_PAIR'
        elif player_has_pair:
            has_pair, pair_type = True, 'PLAYER_PAIR'
        elif banker_has_pair:
            has_pair, pair_type = True, 'BANKER_PAIR'
        
        game_data = GameData(
            table_name=table_name,
            game_number=random.randint(10000, 99999),
            player_cards=player_cards,
            banker_cards=banker_cards,
            has_pair=has_pair,
            pair_type=pair_type,
            timestamp=datetime.now()
        )
        
        games_data.append(game_data)
        table_distribution[table_name] = table_distribution.get(table_name, 0) + 1
    
    return games_data, table_distribution

async def broadcast_demo_update(games_added: int, pairs_found: int, table_distribution: Dict[str, int]):
    """데모 업데이트 브로드캐스트"""
    message = {
        'type': 'demo_update',
        'data': {
            'games_added': games_added,
            'pairs_found': pairs_found,
            'table_distribution': table_distribution,
            'message': f"{games_added}개 게임 추가, {pairs_found}개 페어 발견!"
        },
        'timestamp': datetime.now().isoformat()
    }
    
    await websocket_manager.broadcast(message)

async def broadcast_packet_update(games_processed: int, pairs_found: int, source: str):
    """패킷 처리 업데이트 브로드캐스트"""
    message = {
        'type': 'packet_update',
        'data': {
            'games_processed': games_processed,
            'pairs_found': pairs_found,
            'source': source,
            'message': f"{games_processed}개 패킷 게임 처리 완료 ({pairs_found}개 페어 발견) - {source}"
        },
        'timestamp': datetime.now().isoformat()
    }
    
    await websocket_manager.broadcast(message)

async def background_monitoring():
    """백그라운드 모니터링 작업"""
    logger.info("🔄 백그라운드 모니터링 시작")
    
    while True:
        try:
            await asyncio.sleep(30)  # 30초마다 실행
            
            # 통계 업데이트 브로드캐스트
            if websocket_manager.active_connections:
                stats = await db_manager.get_stats()
                await websocket_manager.broadcast({
                    'type': 'stats_update',
                    'data': stats,
                    'timestamp': datetime.now().isoformat()
                })
                
                logger.debug(f"📊 통계 브로드캐스트 완료: {len(websocket_manager.active_connections)}개 연결")
        
        except Exception as e:
            logger.error(f"❌ 백그라운드 모니터링 오류: {e}")
            await asyncio.sleep(60)  # 오류 시 1분 대기

# === Main ===

if __name__ == "__main__":
    import uvicorn
    
    print("FastAPI Next Generation System v1.0")
    print("=" * 60)
    print("AsyncIO 네이티브 바카라 모니터링 시스템")
    print("포트: 8001")
    print("URL: http://127.0.0.1:8001")
    print("API 문서: http://127.0.0.1:8001/docs")
    print("WebSocket: ws://127.0.0.1:8001/ws/{client_id}")
    print("=" * 60)
    
    uvicorn.run(
        "fastapi_next_gen:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
        log_level="info"
    )