#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimized Database Service - FastAPI
고성능 비동기 데이터베이스 서비스 with 연결 풀링 및 쿼리 최적화
"""

import aiosqlite
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from contextlib import asynccontextmanager
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import threading
import time

from models.game import GameData, TableStats, TableMetadata, TableType, VIPLevel, PairType
from services.advanced_cache import get_cache, CacheStrategy, SerializationType

logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """쿼리 성능 메트릭"""
    query_type: str
    execution_time: float
    rows_affected: int
    cache_hit: bool
    timestamp: datetime

class ConnectionPool:
    """비동기 SQLite 연결 풀"""
    
    def __init__(self, db_path: str, pool_size: int = 10, timeout: float = 30.0):
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self.connections: List[aiosqlite.Connection] = []
        self.available: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self.lock = asyncio.Lock()
        self.initialized = False
    
    async def initialize(self):
        """연결 풀 초기화"""
        if self.initialized:
            return
        
        async with self.lock:
            if self.initialized:
                return
            
            for _ in range(self.pool_size):
                conn = await aiosqlite.connect(
                    self.db_path,
                    timeout=self.timeout,
                    isolation_level=None  # Autocommit mode
                )
                
                # WAL 모드 활성화 (성능 향상)
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                await conn.execute("PRAGMA cache_size=10000")
                await conn.execute("PRAGMA temp_store=MEMORY")
                await conn.execute("PRAGMA mmap_size=268435456")  # 256MB
                
                self.connections.append(conn)
                await self.available.put(conn)
            
            self.initialized = True
            logger.info(f"🔗 데이터베이스 연결 풀 초기화 완료: {self.pool_size}개 연결")
    
    @asynccontextmanager
    async def get_connection(self):
        """연결 풀에서 연결 가져오기"""
        if not self.initialized:
            await self.initialize()
        
        try:
            conn = await asyncio.wait_for(self.available.get(), timeout=self.timeout)
            yield conn
        finally:
            await self.available.put(conn)
    
    async def close_all(self):
        """모든 연결 종료"""
        async with self.lock:
            while self.connections:
                conn = self.connections.pop()
                await conn.close()
            
            # 큐 비우기
            while not self.available.empty():
                try:
                    self.available.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            self.initialized = False
            logger.info("🔗 데이터베이스 연결 풀 종료 완료")

class OptimizedDatabaseManager:
    """최적화된 데이터베이스 매니저"""
    
    def __init__(self, 
                 db_path: str = "baccarat_optimized.db",
                 pool_size: int = 10,
                 enable_metrics: bool = True,
                 batch_size: int = 1000):
        
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self.enable_metrics = enable_metrics
        self.batch_size = batch_size
        
        # 연결 풀
        self.pool = ConnectionPool(str(self.db_path), pool_size)
        
        # 캐시 레이어들
        self.query_cache = get_cache(
            "db_queries",
            max_memory_mb=50,
            default_ttl=300,  # 5분
            strategy=CacheStrategy.LRU,
            serialize_type=SerializationType.COMPRESSED_PICKLE
        )
        
        self.stats_cache = get_cache(
            "db_stats", 
            max_memory_mb=20,
            default_ttl=60,   # 1분
            strategy=CacheStrategy.TTL
        )
        
        # 메트릭 수집
        self.metrics = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_query_time': 0.0,
            'query_times': [],
            'queries_by_type': {},
            'recent_queries': []
        } if enable_metrics else {}
        
        # 배치 작업 큐
        self.batch_queue: asyncio.Queue = asyncio.Queue()
        self.batch_worker_task: Optional[asyncio.Task] = None
        self.running = False
        
        # 인덱스 최적화 정보
        self.optimized_indexes = {
            'games': [
                ('idx_table_name_time', ['table_name', 'game_time']),
                ('idx_has_pair_time', ['has_pair', 'game_time']),
                ('idx_composite_stats', ['table_name', 'has_pair', 'game_time']),
                ('idx_game_number', ['table_name', 'game_number'])
            ],
            'pair_alerts': [
                ('idx_alert_table_time', ['table_name', 'alert_time']),
                ('idx_alert_severity', ['severity'])
            ]
        }
        
        self._initialized = False
    
    async def initialize(self):
        """데이터베이스 초기화"""
        if self._initialized:
            return
        
        try:
            logger.info(f"🚀 최적화된 데이터베이스 초기화 시작: {self.db_path}")
            
            # 연결 풀 초기화
            await self.pool.initialize()
            
            # 테이블 및 인덱스 생성
            await self._create_optimized_tables()
            await self._create_optimized_indexes()
            
            # 메타데이터 초기화
            await self._initialize_metadata()
            
            # 캐시 시스템 시작
            await self.query_cache.start_background_tasks()
            await self.stats_cache.start_background_tasks()
            
            # 배치 워커 시작
            await self._start_batch_worker()
            
            # 데이터베이스 분석 및 최적화
            await self._analyze_and_optimize()
            
            self._initialized = True
            logger.info("✅ 최적화된 데이터베이스 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def _create_optimized_tables(self):
        """최적화된 테이블 생성"""
        async with self.pool.get_connection() as db:
            # 게임 데이터 테이블 (최적화된 스키마)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY,
                    table_id TEXT,
                    table_name TEXT NOT NULL,
                    game_number INTEGER NOT NULL,
                    winner TEXT NOT NULL,
                    player_score INTEGER DEFAULT 0,
                    banker_score INTEGER DEFAULT 0,
                    player_pair BOOLEAN DEFAULT 0,
                    banker_pair BOOLEAN DEFAULT 0,
                    natural BOOLEAN DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date TEXT,
                    source_file TEXT,
                    -- 기존 호환 필드들 (선택적)
                    player_cards TEXT,
                    banker_cards TEXT,
                    player_sum INTEGER,
                    banker_sum INTEGER,
                    has_pair BOOLEAN DEFAULT 0,
                    pair_type TEXT,
                    pair_cards TEXT,
                    game_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    -- 미리 계산된 통계 필드들
                    game_result TEXT,  -- P, B, T
                    is_natural BOOLEAN DEFAULT 0,
                    total_cards INTEGER
                )
            """)
            
            # 테이블 메타데이터 (변경사항 없음)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS table_metadata (
                    table_name TEXT PRIMARY KEY,
                    name_kr TEXT NOT NULL,
                    name_en TEXT NOT NULL,
                    table_type TEXT NOT NULL,
                    vip_level TEXT NOT NULL,
                    betting_limit TEXT NOT NULL,
                    location TEXT NOT NULL,
                    capacity TEXT NOT NULL,
                    features TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) WITHOUT ROWID
            """)
            
            # 페어 알림 히스토리 (최적화됨)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pair_alerts (
                    id INTEGER PRIMARY KEY,
                    alert_id TEXT UNIQUE NOT NULL,
                    table_name TEXT NOT NULL,
                    pair_type TEXT NOT NULL,
                    pair_cards TEXT NOT NULL,
                    game_data TEXT NOT NULL,
                    alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    severity TEXT DEFAULT 'normal',
                    processed BOOLEAN DEFAULT 0,
                    -- 추가 최적화 필드
                    alert_date DATE GENERATED ALWAYS AS (DATE(alert_time)) STORED,
                    alert_hour INTEGER GENERATED ALWAYS AS (strftime('%H', alert_time)) STORED
                ) WITHOUT ROWID
            """)
            
            # 통계 캐시 테이블 (물리적 캐시)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stats_cache (
                    cache_key TEXT PRIMARY KEY,
                    cache_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                ) WITHOUT ROWID
            """)
            
            await db.commit()
    
    async def _create_optimized_indexes(self):
        """최적화된 인덱스 생성"""
        async with self.pool.get_connection() as db:
            for table_name, indexes in self.optimized_indexes.items():
                for index_name, columns in indexes:
                    try:
                        columns_str = ', '.join(columns)
                        await db.execute(f"""
                            CREATE INDEX IF NOT EXISTS {index_name} 
                            ON {table_name} ({columns_str})
                        """)
                        logger.debug(f"📊 인덱스 생성: {index_name}")
                    except Exception as e:
                        logger.error(f"❌ 인덱스 생성 실패 {index_name}: {e}")
            
            # 추가 최적화 인덱스들
            optimize_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_games_date ON games (DATE(game_time))",
                "CREATE INDEX IF NOT EXISTS idx_games_hour ON games (strftime('%H', game_time))",
                "CREATE INDEX IF NOT EXISTS idx_alerts_processed ON pair_alerts (processed, alert_time)",
                "CREATE INDEX IF NOT EXISTS idx_stats_expires ON stats_cache (expires_at)"
            ]
            
            for index_sql in optimize_indexes:
                try:
                    await db.execute(index_sql)
                except Exception as e:
                    logger.error(f"❌ 추가 인덱스 생성 실패: {e}")
            
            await db.commit()
            logger.info("📊 데이터베이스 인덱스 최적화 완료")
    
    async def _analyze_and_optimize(self):
        """데이터베이스 분석 및 최적화"""
        async with self.pool.get_connection() as db:
            try:
                # SQLite 통계 업데이트
                await db.execute("ANALYZE")
                
                # 자동 VACUUM 설정
                await db.execute("PRAGMA auto_vacuum=INCREMENTAL")
                
                # 최적화 정보 수집
                cursor = await db.execute("PRAGMA optimize")
                
                logger.info("🔧 데이터베이스 분석 및 최적화 완료")
                
            except Exception as e:
                logger.error(f"❌ 데이터베이스 최적화 실패: {e}")
    
    async def _initialize_metadata(self):
        """테이블 메타데이터 초기화 (기존과 동일)"""
        default_metadata = {
            'table_001': {
                'name_kr': '스피드바카라A',
                'name_en': 'Speed Baccarat A',
                'table_type': TableType.STANDARD.value,
                'vip_level': VIPLevel.STANDARD.value,
                'betting_limit': '1만~50만원',
                'location': '메인플로어 1층',
                'capacity': '7명',
                'features': '30초 라운드, 일반 접근'
            },
            'table_002': {
                'name_kr': '스피드바카라B', 
                'name_en': 'Speed Baccarat B',
                'table_type': TableType.STANDARD.value,
                'vip_level': VIPLevel.STANDARD.value,
                'betting_limit': '1만~50만원',
                'location': '메인플로어 1층',
                'capacity': '7명',
                'features': '30초 라운드, 일반 접근'
            },
            'table_003': {
                'name_kr': 'VIP룸1',
                'name_en': 'VIP Room 1', 
                'table_type': TableType.VIP.value,
                'vip_level': VIPLevel.DIAMOND.value,
                'betting_limit': '50만~1000만원',
                'location': 'VIP플로어 3층',
                'capacity': '6명',
                'features': '프라이빗 룸, 전담 딜러'
            }
        }
        
        async with self.pool.get_connection() as db:
            for table_name, metadata in default_metadata.items():
                await db.execute("""
                    INSERT OR IGNORE INTO table_metadata 
                    (table_name, name_kr, name_en, table_type, vip_level, 
                     betting_limit, location, capacity, features)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    table_name, metadata['name_kr'], metadata['name_en'],
                    metadata['table_type'], metadata['vip_level'],
                    metadata['betting_limit'], metadata['location'],
                    metadata['capacity'], metadata['features']
                ))
            
            await db.commit()
    
    async def _start_batch_worker(self):
        """배치 처리 워커 시작"""
        if self.batch_worker_task:
            return
        
        self.running = True
        self.batch_worker_task = asyncio.create_task(self._batch_worker())
        logger.info("🔄 배치 처리 워커 시작")
    
    async def _batch_worker(self):
        """배치 처리 워커"""
        batch_buffer = []
        last_flush = time.time()
        
        while self.running:
            try:
                # 대기 중인 작업 수집 (최대 1초 대기)
                try:
                    item = await asyncio.wait_for(self.batch_queue.get(), timeout=1.0)
                    batch_buffer.append(item)
                except asyncio.TimeoutError:
                    pass
                
                # 배치 실행 조건 확인
                should_flush = (
                    len(batch_buffer) >= self.batch_size or
                    (batch_buffer and time.time() - last_flush > 5.0)  # 5초마다 강제 플러시
                )
                
                if should_flush and batch_buffer:
                    await self._execute_batch(batch_buffer)
                    batch_buffer.clear()
                    last_flush = time.time()
                
            except Exception as e:
                logger.error(f"❌ 배치 워커 오류: {e}")
                await asyncio.sleep(1)
        
        # 남은 배치 처리
        if batch_buffer:
            await self._execute_batch(batch_buffer)
    
    async def _execute_batch(self, batch_items: List[Tuple[str, tuple]]):
        """배치 실행"""
        if not batch_items:
            return
        
        start_time = time.time()
        
        try:
            async with self.pool.get_connection() as db:
                # 쿼리 타입별로 그룹화
                query_groups = {}
                for query, params in batch_items:
                    if query not in query_groups:
                        query_groups[query] = []
                    query_groups[query].append(params)
                
                # 그룹별로 배치 실행
                total_affected = 0
                for query, param_list in query_groups.items():
                    await db.executemany(query, param_list)
                    total_affected += len(param_list)
                
                await db.commit()
                
                execution_time = time.time() - start_time
                logger.info(f"📦 배치 처리 완료: {total_affected}개 작업 (시간: {execution_time:.3f}s)")
                
        except Exception as e:
            logger.error(f"❌ 배치 실행 실패: {e}")
    
    async def add_game_optimized(self, game: GameData) -> int:
        """최적화된 게임 추가"""
        start_time = time.time()
        
        # 미리 계산된 값들
        player_sum = self._calculate_baccarat_sum(game.player_cards)
        banker_sum = self._calculate_baccarat_sum(game.banker_cards)
        game_result = self._determine_game_result(player_sum, banker_sum)
        is_natural = player_sum >= 8 or banker_sum >= 8
        total_cards = len(game.player_cards) + len(game.banker_cards)
        
        query = """
            INSERT INTO games 
            (table_name, game_number, player_cards, banker_cards, 
             player_sum, banker_sum, has_pair, pair_type, pair_cards, 
             game_time, game_result, is_natural, total_cards)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            game.table_name, game.game_number,
            ','.join(game.player_cards), ','.join(game.banker_cards),
            player_sum, banker_sum,
            game.has_pair, game.pair_type.value if game.pair_type else None,
            ','.join(game.pair_cards) if game.pair_cards else None,
            game.game_time, game_result, is_natural, total_cards
        )
        
        async with self.pool.get_connection() as db:
            cursor = await db.execute(query, params)
            await db.commit()
            game_id = cursor.lastrowid
        
        # 캐시 무효화
        await self._invalidate_related_caches(game.table_name)
        
        # 메트릭 기록
        if self.enable_metrics:
            execution_time = time.time() - start_time
            await self._record_query_metric('INSERT', execution_time, 1, False)
        
        return game_id
    
    async def add_games_batch_optimized(self, games: List[GameData]) -> List[int]:
        """최적화된 배치 게임 추가"""
        if not games:
            return []
        
        start_time = time.time()
        game_ids = []
        
        # 배치 크기별로 분할 처리
        for i in range(0, len(games), self.batch_size):
            batch = games[i:i + self.batch_size]
            batch_ids = await self._process_game_batch(batch)
            game_ids.extend(batch_ids)
        
        # 영향받은 테이블들의 캐시 무효화
        affected_tables = set(game.table_name for game in games)
        for table_name in affected_tables:
            await self._invalidate_related_caches(table_name)
        
        # 메트릭 기록
        if self.enable_metrics:
            execution_time = time.time() - start_time
            await self._record_query_metric('BATCH_INSERT', execution_time, len(games), False)
        
        logger.info(f"📦 배치 게임 추가 완료: {len(games)}개 (시간: {execution_time:.3f}s)")
        return game_ids
    
    async def _process_game_batch(self, games: List[GameData]) -> List[int]:
        """게임 배치 처리"""
        query = """
            INSERT INTO games 
            (table_name, game_number, player_cards, banker_cards, 
             player_sum, banker_sum, has_pair, pair_type, pair_cards, 
             game_time, game_result, is_natural, total_cards)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params_list = []
        for game in games:
            player_sum = self._calculate_baccarat_sum(game.player_cards)
            banker_sum = self._calculate_baccarat_sum(game.banker_cards)
            game_result = self._determine_game_result(player_sum, banker_sum)
            is_natural = player_sum >= 8 or banker_sum >= 8
            total_cards = len(game.player_cards) + len(game.banker_cards)
            
            params_list.append((
                game.table_name, game.game_number,
                ','.join(game.player_cards), ','.join(game.banker_cards),
                player_sum, banker_sum,
                game.has_pair, game.pair_type.value if game.pair_type else None,
                ','.join(game.pair_cards) if game.pair_cards else None,
                game.game_time, game_result, is_natural, total_cards
            ))
        
        game_ids = []
        async with self.pool.get_connection() as db:
            await db.executemany(query, params_list)
            
            # 마지막 게임부터 역순으로 ID 계산 (SQLite 특성 활용)
            cursor = await db.execute("SELECT last_insert_rowid()")
            last_id = (await cursor.fetchone())[0]
            
            game_ids = list(range(last_id - len(games) + 1, last_id + 1))
            
            await db.commit()
        
        return game_ids
    
    def _calculate_baccarat_sum(self, cards: List[str]) -> int:
        """바카라 점수 계산"""
        total = 0
        for card in cards:
            # 카드에서 숫자 부분 추출
            value_str = card[:-1]  # 마지막 문자(슈트) 제거
            
            if value_str in ['J', 'Q', 'K']:
                value = 0
            elif value_str == 'A':
                value = 1
            else:
                try:
                    value = int(value_str)
                    if value == 10:
                        value = 0
                except:
                    value = 0
            
            total += value
        
        return total % 10
    
    def _determine_game_result(self, player_sum: int, banker_sum: int) -> str:
        """게임 결과 결정"""
        if player_sum > banker_sum:
            return 'P'
        elif banker_sum > player_sum:
            return 'B'
        else:
            return 'T'
    
    async def get_table_stats_optimized(self, table_name: str, use_cache: bool = True) -> Optional[TableStats]:
        """최적화된 테이블 통계 조회"""
        cache_key = f'optimized_table_stats:{table_name}'
        
        # 캐시 확인
        if use_cache:
            cached_stats = await self.stats_cache.get(cache_key)
            if cached_stats is not None:
                if self.enable_metrics:
                    await self._record_query_metric('SELECT_CACHED', 0.001, 0, True)
                return cached_stats
        
        start_time = time.time()
        
        async with self.pool.get_connection() as db:
            # 최적화된 단일 쿼리로 모든 통계 조회
            cursor = await db.execute("""
                WITH game_stats AS (
                    SELECT 
                        COUNT(*) as games,
                        COUNT(CASE WHEN has_pair = 1 THEN 1 END) as pairs,
                        MAX(game_time) as last_game_time,
                        COUNT(CASE WHEN game_result = 'P' THEN 1 END) as player_wins,
                        COUNT(CASE WHEN game_result = 'B' THEN 1 END) as banker_wins,
                        COUNT(CASE WHEN game_result = 'T' THEN 1 END) as ties,
                        COUNT(CASE WHEN is_natural = 1 THEN 1 END) as naturals,
                        AVG(total_cards) as avg_cards
                    FROM games 
                    WHERE table_name = ?
                ),
                recent_pairs AS (
                    SELECT pair_type, pair_cards, game_time
                    FROM games 
                    WHERE table_name = ? AND has_pair = 1 
                    ORDER BY game_time DESC 
                    LIMIT 5
                )
                SELECT 
                    gs.games, gs.pairs, gs.last_game_time,
                    gs.player_wins, gs.banker_wins, gs.ties, gs.naturals, gs.avg_cards,
                    GROUP_CONCAT(rp.pair_type || '|' || rp.pair_cards || '|' || rp.game_time, ';') as recent_pairs_data
                FROM game_stats gs
                LEFT JOIN recent_pairs rp ON 1=1
            """, (table_name, table_name))
            
            row = await cursor.fetchone()
            if not row or row[0] == 0:
                return None
            
            games, pairs, last_game_time, player_wins, banker_wins, ties, naturals, avg_cards, recent_pairs_data = row
            
            # 메타데이터 조회
            cursor = await db.execute("""
                SELECT name_kr, name_en, table_type, vip_level, 
                       betting_limit, location, capacity, features
                FROM table_metadata WHERE table_name = ?
            """, (table_name,))
            
            metadata_row = await cursor.fetchone()
            if not metadata_row:
                return None
            
            metadata = TableMetadata(
                name_kr=metadata_row[0],
                name_en=metadata_row[1],
                table_type=TableType(metadata_row[2]),
                vip_level=VIPLevel(metadata_row[3]),
                betting_limit=metadata_row[4],
                location=metadata_row[5],
                capacity=metadata_row[6],
                features=metadata_row[7]
            )
            
            # 최근 페어 파싱
            recent_pairs = []
            if recent_pairs_data:
                pairs_data = recent_pairs_data.split(';')
                for pair_data in pairs_data:
                    if pair_data:
                        parts = pair_data.split('|')
                        if len(parts) == 3:
                            recent_pairs.append({
                                'pair_type': parts[0],
                                'pair_cards': parts[1].split(',') if parts[1] else [],
                                'game_time': parts[2]
                            })
            
            pair_rate = (pairs / games * 100) if games > 0 else 0.0
            
            table_stats = TableStats(
                table_name=table_name,
                games=games,
                pairs=pairs,
                pair_rate=round(pair_rate, 2),
                last_game_time=datetime.fromisoformat(last_game_time) if last_game_time else None,
                recent_pairs=recent_pairs,
                metadata=metadata
            )
            
            # 확장 통계 정보 추가
            table_stats.additional_stats = {
                'player_wins': player_wins,
                'banker_wins': banker_wins,
                'ties': ties,
                'naturals': naturals,
                'avg_cards': round(avg_cards, 2) if avg_cards else 0,
                'win_rates': {
                    'player': round((player_wins / games * 100), 2) if games > 0 else 0,
                    'banker': round((banker_wins / games * 100), 2) if games > 0 else 0,
                    'tie': round((ties / games * 100), 2) if games > 0 else 0
                }
            }
            
            # 캐시에 저장
            if use_cache:
                await self.stats_cache.set(cache_key, table_stats, ttl=300)  # 5분
            
            # 메트릭 기록
            if self.enable_metrics:
                execution_time = time.time() - start_time
                await self._record_query_metric('SELECT_STATS', execution_time, 1, False)
            
            return table_stats
    
    async def _invalidate_related_caches(self, table_name: str):
        """관련 캐시 무효화"""
        cache_patterns = [
            f'optimized_table_stats:{table_name}',
            'optimized_all_table_stats',
            'system_stats_optimized'
        ]
        
        for pattern in cache_patterns:
            await self.stats_cache.delete(pattern)
    
    async def _record_query_metric(self, query_type: str, execution_time: float, rows_affected: int, cache_hit: bool):
        """쿼리 메트릭 기록"""
        if not self.enable_metrics:
            return
        
        self.metrics['total_queries'] += 1
        if cache_hit:
            self.metrics['cache_hits'] += 1
        else:
            self.metrics['cache_misses'] += 1
        
        self.metrics['query_times'].append(execution_time)
        if len(self.metrics['query_times']) > 1000:
            self.metrics['query_times'] = self.metrics['query_times'][-500:]
        
        if self.metrics['query_times']:
            self.metrics['avg_query_time'] = sum(self.metrics['query_times']) / len(self.metrics['query_times'])
        
        # 쿼리 타입별 통계
        if query_type not in self.metrics['queries_by_type']:
            self.metrics['queries_by_type'][query_type] = {'count': 0, 'total_time': 0}
        
        self.metrics['queries_by_type'][query_type]['count'] += 1
        self.metrics['queries_by_type'][query_type]['total_time'] += execution_time
        
        # 최근 쿼리 기록 (최대 100개)
        self.metrics['recent_queries'].append({
            'type': query_type,
            'time': execution_time,
            'rows': rows_affected,
            'cache_hit': cache_hit,
            'timestamp': datetime.now().isoformat()
        })
        
        if len(self.metrics['recent_queries']) > 100:
            self.metrics['recent_queries'] = self.metrics['recent_queries'][-50:]
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """시스템 전체 통계 (최적화됨)"""
        cache_key = 'system_stats_optimized'
        
        # 캐시 확인
        cached_stats = await self.stats_cache.get(cache_key)
        if cached_stats is not None:
            return cached_stats
        
        start_time = time.time()
        
        async with self.pool.get_connection() as db:
            # 전체 시스템 통계를 한 번의 쿼리로 조회
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(CASE WHEN has_pair = 1 THEN 1 END) as total_pairs,
                    COUNT(DISTINCT table_name) as active_tables,
                    COUNT(CASE WHEN DATE(game_time) = DATE('now') THEN 1 END) as today_games,
                    COUNT(CASE WHEN has_pair = 1 AND DATE(game_time) = DATE('now') THEN 1 END) as today_pairs,
                    MAX(game_time) as last_activity,
                    MIN(game_time) as first_game
                FROM games
            """)
            
            stats_row = await cursor.fetchone()
            
            system_stats = {
                'total_games': stats_row[0] or 0,
                'total_pairs': stats_row[1] or 0,
                'active_tables': stats_row[2] or 0,
                'today_games': stats_row[3] or 0,
                'today_pairs': stats_row[4] or 0,
                'last_activity': stats_row[5],
                'first_game': stats_row[6],
                'overall_pair_rate': round((stats_row[1] / stats_row[0] * 100), 2) if stats_row[0] > 0 else 0,
                'database_stats': {
                    'connection_pool_size': self.pool_size,
                    'cache_hit_rate': self.metrics.get('cache_hits', 0) / max(1, self.metrics.get('total_queries', 1)) if self.enable_metrics else 0,
                    'avg_query_time': self.metrics.get('avg_query_time', 0) if self.enable_metrics else 0
                },
                'timestamp': datetime.now().isoformat()
            }
        
        # 캐시에 저장 (1분)
        await self.stats_cache.set(cache_key, system_stats, ttl=60)
        
        # 메트릭 기록
        if self.enable_metrics:
            execution_time = time.time() - start_time
            await self._record_query_metric('SYSTEM_STATS', execution_time, 1, False)
        
        return system_stats
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 조회"""
        if not self.enable_metrics:
            return {'metrics_disabled': True}
        
        return {
            'query_metrics': self.metrics,
            'cache_metrics': {
                'query_cache': self.query_cache.get_stats(),
                'stats_cache': self.stats_cache.get_stats()
            },
            'database_metrics': {
                'connection_pool_size': self.pool_size,
                'batch_queue_size': self.batch_queue.qsize(),
                'worker_running': self.running
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """데이터베이스 헬스 체크"""
        try:
            start_time = time.time()
            
            async with self.pool.get_connection() as db:
                cursor = await db.execute("SELECT 1")
                result = await cursor.fetchone()
            
            connection_time = time.time() - start_time
            
            return {
                'healthy': True,
                'connection_time': connection_time,
                'pool_initialized': self.pool.initialized,
                'connections_available': self.pool.available.qsize(),
                'cache_status': {
                    'query_cache_size': len(self.query_cache.prediction_cache),
                    'stats_cache_size': len(self.stats_cache.prediction_cache)
                },
                'metrics_enabled': self.enable_metrics,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def bulk_insert_games(self, games_data: List[Dict[str, Any]]):
        """게임 데이터 대량 삽입 (고성능)"""
        if not games_data:
            return
        
        start_time = time.time()
        
        try:
            async with self.pool.get_connection() as conn:
                # 트랜잭션 시작
                await conn.execute("BEGIN TRANSACTION")
                
                try:
                    # 배치 삽입 쿼리
                    insert_sql = """
                    INSERT OR REPLACE INTO games (
                        table_id, table_name, game_number, winner, 
                        player_score, banker_score, player_pair, banker_pair,
                        natural, timestamp, date, source_file
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    
                    # 데이터 준비
                    batch_data = [
                        (
                            game.get('table_id', 'unknown'),
                            game.get('table_name', 'unknown'),
                            game.get('game_number', 0),
                            game.get('winner', 'Unknown'),
                            game.get('player_score', 0),
                            game.get('banker_score', 0),
                            int(game.get('player_pair', False)),
                            int(game.get('banker_pair', False)),
                            int(game.get('natural', False)),
                            game.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                            game.get('date', datetime.now().strftime('%Y%m%d')),
                            game.get('source_file', 'unknown')
                        ) for game in games_data
                    ]
                    
                    # 배치 실행
                    await conn.executemany(insert_sql, batch_data)
                    
                    # 트랜잭션 커밋
                    await conn.execute("COMMIT")
                    
                    logger.info(f"✅ 대량 삽입 완료: {len(games_data)}개 게임")
                    
                    # 관련 캐시 무효화
                    if games_data and 'table_name' in games_data[0]:
                        await self._invalidate_related_caches(games_data[0]['table_name'])
                    
                    # 메트릭 기록
                    if self.enable_metrics:
                        execution_time = time.time() - start_time
                        await self._record_query_metric('BULK_INSERT', execution_time, len(games_data), False)
                
                except Exception as e:
                    # 롤백
                    await conn.execute("ROLLBACK")
                    raise e
                    
        except Exception as e:
            logger.error(f"❌ 대량 삽입 오류: {e}")
            raise

    async def close(self):
        """데이터베이스 연결 종료"""
        try:
            # 배치 워커 중지
            self.running = False
            if self.batch_worker_task:
                self.batch_worker_task.cancel()
                try:
                    await self.batch_worker_task
                except asyncio.CancelledError:
                    pass
            
            # 캐시 중지
            await self.query_cache.stop_background_tasks()
            await self.stats_cache.stop_background_tasks()
            
            # 연결 풀 종료
            await self.pool.close_all()
            
            logger.info("🔚 최적화된 데이터베이스 서비스 종료 완료")
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 종료 중 오류: {e}")

# 전역 최적화된 데이터베이스 매니저 인스턴스
optimized_db_manager: Optional[OptimizedDatabaseManager] = None

async def get_optimized_db_manager() -> OptimizedDatabaseManager:
    """전역 최적화된 데이터베이스 매니저 반환"""
    global optimized_db_manager
    if optimized_db_manager is None:
        optimized_db_manager = OptimizedDatabaseManager()
        await optimized_db_manager.initialize()
    return optimized_db_manager