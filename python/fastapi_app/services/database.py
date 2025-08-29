#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 비동기 데이터베이스 매니저
"""

import aiosqlite
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json

from models.game import GameData, TableStats, TableMetadata, TableType, VIPLevel, PairType
from services.cache_manager import cache_manager
from utils.smart_output import info, success, warning, error, progress, OutputContext

logger = logging.getLogger(__name__)

class DatabaseManager:
    """비동기 데이터베이스 매니저"""
    
    def __init__(self, db_path: str = "baccarat_fastapi.db"):
        self.db_path = Path(db_path)
        self.connection_pool = None
        self._initialized = False
    
    async def initialize(self):
        """데이터베이스 초기화"""
        if self._initialized:
            return
        
        try:
            with OutputContext("데이터베이스 초기화") as out:
                out.info("데이터베이스 연결 설정", {"파일": str(self.db_path)})
                
                # 데이터베이스 테이블 생성
                progress(1, 3, "테이블 스키마 생성")
                await self._create_tables()
                
                # 메타데이터 초기화
                progress(2, 3, "메타데이터 설정")
                await self._initialize_metadata()
                
                progress(3, 3, "초기화 완료")
                self._initialized = True
                out.success("데이터베이스 초기화 완료", 
                          {"테이블수": 5,
                          "연결상태": "활성"})
            
        except Exception as e:
            error("데이터베이스 초기화 실패", 
                  오류=str(e),
                  파일=str(self.db_path))
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def _create_tables(self):
        """테이블 생성"""
        async with aiosqlite.connect(self.db_path) as db:
            # 게임 데이터 테이블
            await db.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    game_number INTEGER NOT NULL,
                    player_cards TEXT NOT NULL,
                    banker_cards TEXT NOT NULL,
                    has_pair BOOLEAN DEFAULT 0,
                    pair_type TEXT,
                    pair_cards TEXT,
                    game_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 게임 테이블 인덱스 생성
            await db.execute("CREATE INDEX IF NOT EXISTS idx_table_name ON games (table_name)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_has_pair ON games (has_pair)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_game_time ON games (game_time)")
            
            # 테이블 메타데이터
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
                )
            """)
            
            # 페어 알림 히스토리
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pair_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    table_name TEXT NOT NULL,
                    pair_type TEXT NOT NULL,
                    pair_cards TEXT NOT NULL,
                    game_data TEXT NOT NULL,
                    alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    severity TEXT DEFAULT 'normal'
                )
            """)
            
            # 페어 알림 테이블 인덱스 생성
            await db.execute("CREATE INDEX IF NOT EXISTS idx_table_alert ON pair_alerts (table_name)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_alert_time ON pair_alerts (alert_time)")
            
            await db.commit()
    
    async def _initialize_metadata(self):
        """테이블 메타데이터 초기화"""
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
                'name_kr': '클래식바카라1',
                'name_en': 'Classic Baccarat 1',
                'table_type': TableType.PREMIUM.value,
                'vip_level': VIPLevel.GOLD.value,
                'betting_limit': '5만~200만원',
                'location': '골드라운지 2층',
                'capacity': '8명',
                'features': '전통 바카라, 골드 멤버십'
            },
            'table_004': {
                'name_kr': 'VIP룸1',
                'name_en': 'VIP Room 1',
                'table_type': TableType.VIP.value,
                'vip_level': VIPLevel.DIAMOND.value,
                'betting_limit': '50만~1000만원',
                'location': 'VIP플로어 3층',
                'capacity': '6명',
                'features': '프라이빗 룸, 전담 딜러, 개인 서비스'
            },
            'table_005': {
                'name_kr': 'VIP룸2',
                'name_en': 'VIP Room 2',
                'table_type': TableType.VIP.value,
                'vip_level': VIPLevel.PLATINUM.value,
                'betting_limit': '100만~2000만원',
                'location': 'VIP플로어 3층',
                'capacity': '6명',
                'features': '최고급 프라이빗 룸, 마스터 딜러, 전용 입구'
            }
        }
        
        async with aiosqlite.connect(self.db_path) as db:
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
    
    async def add_game(self, game: GameData) -> int:
        """게임 데이터 추가"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO games 
                (table_name, game_number, player_cards, banker_cards, 
                 has_pair, pair_type, pair_cards, game_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game.table_name, game.game_number,
                ','.join(game.player_cards), ','.join(game.banker_cards),
                game.has_pair, game.pair_type.value if game.pair_type else None,
                ','.join(game.pair_cards) if game.pair_cards else None,
                game.game_time
            ))
            
            await db.commit()
            return cursor.lastrowid
    
    async def add_games_batch(self, games: List[GameData]) -> List[int]:
        """배치 게임 데이터 추가"""
        game_ids = []
        
        async with aiosqlite.connect(self.db_path) as db:
            for game in games:
                cursor = await db.execute("""
                    INSERT INTO games 
                    (table_name, game_number, player_cards, banker_cards, 
                     has_pair, pair_type, pair_cards, game_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    game.table_name, game.game_number,
                    ','.join(game.player_cards), ','.join(game.banker_cards),
                    game.has_pair, game.pair_type.value if game.pair_type else None,
                    ','.join(game.pair_cards) if game.pair_cards else None,
                    game.game_time
                ))
                game_ids.append(cursor.lastrowid)
            
            await db.commit()
        
        # 캐시 무효화는 별도 기능으로 분리
        logger.info("Games added successfully to database")
        
        return game_ids
    
    async def _invalidate_stats_cache(self, affected_tables: List[str]):
        """통계 캐시 무효화"""
        try:
            # 시스템 전체 통계 캐시 삭제
            await cache_manager.delete('system_stats')
            await cache_manager.delete('all_table_stats')
            
            # 영향받은 테이블별 캐시 삭제
            for table_name in affected_tables:
                await cache_manager.delete(f'table_stats:{table_name}')
            
            logger.info(f"Cache invalidated for {len(affected_tables)} tables")
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
    
    async def get_table_stats(self, table_name: str, use_cache: bool = True) -> Optional[TableStats]:
        """특정 테이블 통계 조회 (캐싱 지원)"""
        cache_key = f'table_stats:{table_name}'
        
        # 캐시에서 먼저 조회 시도
        if use_cache:
            cached_stats, cache_hit = await cache_manager.get(cache_key, 'table_stats')
            if cache_hit:
                logger.debug(f"Table stats served from cache: {table_name}")
                return cached_stats
        
        async with aiosqlite.connect(self.db_path) as db:
            # 게임 통계
            cursor = await db.execute("""
                SELECT COUNT(*) as games, 
                       COUNT(CASE WHEN has_pair = 1 THEN 1 END) as pairs,
                       MAX(game_time) as last_game_time
                FROM games WHERE table_name = ?
            """, (table_name,))
            
            stats_row = await cursor.fetchone()
            if not stats_row:
                return None
            
            games, pairs, last_game_time = stats_row
            pair_rate = (pairs / games * 100) if games > 0 else 0.0
            
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
            
            # 최근 페어 조회
            cursor = await db.execute("""
                SELECT pair_type, pair_cards, game_time 
                FROM games 
                WHERE table_name = ? AND has_pair = 1 
                ORDER BY game_time DESC 
                LIMIT 5
            """, (table_name,))
            
            recent_pairs = []
            async for row in cursor:
                recent_pairs.append({
                    'pair_type': row[0],
                    'pair_cards': row[1].split(',') if row[1] else [],
                    'game_time': row[2]
                })
            
            table_stats = TableStats(
                table_name=table_name,
                games=games,
                pairs=pairs,
                pair_rate=round(pair_rate, 2),
                last_game_time=datetime.fromisoformat(last_game_time) if last_game_time else None,
                recent_pairs=recent_pairs,
                metadata=metadata
            )
            
            # 결과를 캐시에 저장
            if use_cache:
                await cache_manager.set(cache_key, table_stats, 'table_stats')
                logger.debug(f"Table stats cached: {table_name}")
            
            return table_stats
    
    async def get_all_table_stats(self, use_cache: bool = True) -> Dict[str, TableStats]:
        """모든 테이블 통계 조회 (캐싱 지원)"""
        cache_key = 'all_table_stats'
        
        # 캐시에서 먼저 조회 시도
        if use_cache:
            cached_stats, cache_hit = await cache_manager.get(cache_key, 'table_stats')
            if cache_hit:
                logger.debug("All table stats served from cache")
                return cached_stats
        
        async with aiosqlite.connect(self.db_path) as db:
            # 모든 테이블명 조회
            cursor = await db.execute("SELECT DISTINCT table_name FROM table_metadata")
            table_names = [row[0] async for row in cursor]
            
            stats = {}
            for table_name in table_names:
                table_stat = await self.get_table_stats(table_name, use_cache=use_cache)
                if table_stat:
                    stats[table_name] = table_stat
            
            # 결과를 캐시에 저장
            if use_cache and stats:
                await cache_manager.set(cache_key, stats, 'table_stats')
                logger.debug(f"All table stats cached: {len(stats)} tables")
            
            return stats
    
    async def get_system_stats(self, use_cache: bool = True) -> Dict[str, Any]:
        """시스템 전체 통계 조회 (캐싱 지원)"""
        cache_key = 'system_stats'
        
        # 캐시에서 먼저 조회 시도
        if use_cache:
            cached_stats, cache_hit = await cache_manager.get(cache_key, 'stats')
            if cache_hit:
                logger.debug("System stats served from cache")
                return cached_stats
        
        # 데이터베이스에서 조회
        start_time = datetime.now()
        async with aiosqlite.connect(self.db_path) as db:
            # 전체 통계 - 최적화된 쿼리
            cursor = await db.execute("""
                SELECT COUNT(*) as total_games,
                       COUNT(CASE WHEN has_pair = 1 THEN 1 END) as total_pairs,
                       COUNT(DISTINCT table_name) as active_tables
                FROM games
            """)
            
            row = await cursor.fetchone()
            total_games, total_pairs, active_tables = row
            
            global_pair_rate = (total_pairs / total_games * 100) if total_games > 0 else 0.0
            
            # 테이블별 상세 통계 (캐싱된 데이터 사용)
            table_breakdown = await self.get_all_table_stats(use_cache=use_cache)
            
            stats = {
                'total_games': total_games,
                'total_pairs': total_pairs,
                'global_pair_rate': round(global_pair_rate, 2),
                'active_tables': active_tables,
                'active_sessions': 0,
                'system_uptime': '운영중',
                'table_breakdown': {k: v.dict() for k, v in table_breakdown.items()},
                'last_updated': datetime.now().isoformat(),
                'query_time_ms': (datetime.now() - start_time).total_seconds() * 1000
            }
            
            # 결과를 캐시에 저장
            if use_cache:
                await cache_manager.set(cache_key, stats, 'stats')
                logger.debug(f"System stats cached, query time: {stats['query_time_ms']:.1f}ms")
            
            return stats
    
    async def get_db_size(self) -> float:
        """데이터베이스 파일 크기 (KB)"""
        try:
            if self.db_path.exists():
                return round(self.db_path.stat().st_size / 1024, 2)
            return 0.0
        except Exception as e:
            logger.error(f"❌ DB 크기 조회 실패: {e}")
            return 0.0
    
    async def health_check(self) -> str:
        """데이터베이스 상태 확인"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("SELECT 1")
                return "healthy"
        except Exception as e:
            logger.error(f"❌ 데이터베이스 상태 확인 실패: {e}")
            return "unhealthy"
    
    async def close(self):
        """연결 종료"""
        if self.connection_pool:
            self.connection_pool = None
        logger.info("🔄 데이터베이스 연결 정리 완료")