#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
데모 API 라우터 - FastAPI
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
import asyncio
import random
import logging
from datetime import datetime
from typing import List

from models import DemoRequest, DemoResponse, GameData, PairType
from services.database import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter()

# 데이터베이스 의존성
async def get_db():
    db = DatabaseManager()
    await db.initialize()
    try:
        yield db
    finally:
        await db.close()

class DemoGameGenerator:
    """데모 게임 데이터 생성기"""
    
    @staticmethod
    def get_available_tables() -> List[str]:
        """사용 가능한 테이블 목록"""
        return ['table_001', 'table_002', 'table_003', 'table_004', 'table_005']
    
    @staticmethod
    def generate_cards() -> List[str]:
        """카드 생성"""
        values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        suits = ['♠', '♥', '♦', '♣']
        
        cards = []
        for _ in range(2):  # 기본 2장
            value = random.choice(values)
            suit = random.choice(suits)
            cards.append(f"{value}{suit}")
        
        return cards
    
    @classmethod
    async def generate_single_game(cls, 
                                 table_name: str = None,
                                 force_pair: bool = False,
                                 pair_probability: float = 0.25) -> GameData:
        """단일 게임 생성"""
        
        # 테이블명 선택
        if not table_name:
            table_name = random.choice(cls.get_available_tables())
        
        # 카드 생성
        player_cards = cls.generate_cards()
        banker_cards = cls.generate_cards()
        
        # 페어 결정
        has_pair = False
        pair_type = PairType.NO_PAIR
        pair_cards = None
        
        # 페어 검사
        player_values = [card[:-1] for card in player_cards]  # 슈트 제거
        banker_values = [card[:-1] for card in banker_cards]
        
        player_has_pair = len(set(player_values)) != len(player_values)
        banker_has_pair = len(set(banker_values)) != len(banker_values)
        
        # 강제 페어 또는 확률 기반 페어
        if force_pair or (not player_has_pair and not banker_has_pair and random.random() < pair_probability):
            # 플레이어 페어 강제 생성
            if not player_has_pair:
                same_value = random.choice(['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'])
                same_suit1 = random.choice(['♠', '♥', '♦', '♣'])
                same_suit2 = random.choice(['♠', '♥', '♦', '♣'])
                player_cards = [f"{same_value}{same_suit1}", f"{same_value}{same_suit2}"]
                player_has_pair = True
        
        # 페어 타입 결정
        if player_has_pair and banker_has_pair:
            has_pair = True
            pair_type = PairType.BOTH_PAIR
            pair_cards = player_cards + banker_cards
        elif player_has_pair:
            has_pair = True
            pair_type = PairType.PLAYER_PAIR
            pair_cards = [card for card in player_cards if card[:-1] in [c[:-1] for c in player_cards if player_cards.count(c[:-1]) > 1]]
        elif banker_has_pair:
            has_pair = True
            pair_type = PairType.BANKER_PAIR
            pair_cards = [card for card in banker_cards if card[:-1] in [c[:-1] for c in banker_cards if banker_cards.count(c[:-1]) > 1]]
        
        # 시뮬레이션 지연 (실제 게임 처리 시간)
        await asyncio.sleep(0.001)  # 1ms 지연
        
        return GameData(
            table_name=table_name,
            game_number=random.randint(1, 10000),
            player_cards=player_cards,
            banker_cards=banker_cards,
            has_pair=has_pair,
            pair_type=pair_type,
            pair_cards=pair_cards,
            game_time=datetime.now()
        )
    
    @classmethod
    async def generate_multiple_games(cls, 
                                    count: int,
                                    table_name: str = None,
                                    force_pairs: bool = False,
                                    pair_probability: float = 0.25) -> List[GameData]:
        """여러 게임 생성"""
        
        games = []
        tables = cls.get_available_tables()
        
        for i in range(count):
            # 테이블 로테이션
            selected_table = table_name or random.choice(tables)
            
            game = await cls.generate_single_game(
                table_name=selected_table,
                force_pair=force_pairs and i < count // 3,  # 1/3만 강제 페어
                pair_probability=pair_probability
            )
            games.append(game)
        
        return games

@router.post("/demo", response_model=DemoResponse)
async def create_demo_data(
    request: DemoRequest = DemoRequest(),
    background_tasks: BackgroundTasks = None,
    db: DatabaseManager = Depends(get_db)
):
    """
    데모 데이터 생성 API
    
    - **game_count**: 생성할 게임 수 (1-100)
    - **table_name**: 특정 테이블명 (선택사항)
    - **force_pairs**: 강제 페어 생성 여부
    - **pair_probability**: 페어 확률 (0.0-1.0)
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"🎯 데모 데이터 생성 시작: {request.game_count}게임")
        
        # 게임 데이터 생성
        games = await DemoGameGenerator.generate_multiple_games(
            count=request.game_count,
            table_name=request.table_name,
            force_pairs=request.force_pairs,
            pair_probability=request.pair_probability
        )
        
        # 데이터베이스에 저장
        game_ids = await db.add_games_batch(games)
        
        # 통계 계산
        pairs_found = sum(1 for game in games if game.has_pair)
        tables_affected = list(set(game.table_name for game in games))
        
        # 페어 상세 정보
        pair_details = []
        for game in games:
            if game.has_pair:
                pair_details.append({
                    'table_name': game.table_name,
                    'pair_type': game.pair_type.value,
                    'pair_cards': game.pair_cards,
                    'game_time': game.game_time.isoformat()
                })
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        success_message = f"{request.game_count}개 게임 생성 ({pairs_found}개 페어) - FastAPI 비동기"
        logger.info(f"✅ 데모 데이터 생성 완료: {success_message}")
        
        # 실시간 페어 알림 처리
        if pairs_found > 0:
            if background_tasks:
                background_tasks.add_task(process_pair_notifications, pair_details)
            
            # 즉시 WebSocket 알림 전송
            try:
                from routers.websocket_router import get_websocket_manager
                websocket_manager = get_websocket_manager()
                
                if websocket_manager.get_connection_count() > 0:
                    # 페어 알림 브로드캐스트
                    await websocket_manager.broadcast_to_subscribers('pairs', {
                        'type': 'pair_alert',
                        'data': {
                            'pairs_found': pairs_found,
                            'pair_details': pair_details,
                            'tables_affected': tables_affected,
                            'alert_time': datetime.now().isoformat(),
                            'severity': 'high' if pairs_found >= 3 else 'normal'
                        }
                    })
                    
                    logger.info(f"Pair alert broadcasted: {pairs_found} pairs found")
            except Exception as e:
                logger.error(f"WebSocket pair alert failed: {e}")
        
        return DemoResponse(
            success=True,
            message=success_message,
            games_added=request.game_count,
            pairs_found=pairs_found,
            processing_time=round(processing_time, 3),
            mode="fastapi_async",
            tables_affected=tables_affected,
            pair_details=pair_details,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"❌ 데모 데이터 생성 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"데모 데이터 생성 중 오류 발생: {str(e)}"
        )

@router.post("/demo/bulk", response_model=DemoResponse)
async def create_bulk_demo_data(
    requests: List[DemoRequest],
    background_tasks: BackgroundTasks = None,
    db: DatabaseManager = Depends(get_db)
):
    """
    대량 데모 데이터 생성 API
    
    여러 요청을 한번에 처리하여 효율성 향상
    """
    start_time = datetime.now()
    
    try:
        logger.info(f"🎯 대량 데모 데이터 생성 시작: {len(requests)}개 요청")
        
        all_games = []
        total_games = 0
        
        # 모든 요청 처리
        for request in requests:
            games = await DemoGameGenerator.generate_multiple_games(
                count=request.game_count,
                table_name=request.table_name,
                force_pairs=request.force_pairs,
                pair_probability=request.pair_probability
            )
            all_games.extend(games)
            total_games += request.game_count
        
        # 일괄 데이터베이스 저장
        game_ids = await db.add_games_batch(all_games)
        
        # 통계 계산
        pairs_found = sum(1 for game in all_games if game.has_pair)
        tables_affected = list(set(game.table_name for game in all_games))
        
        # 페어 상세 정보
        pair_details = []
        for game in all_games:
            if game.has_pair:
                pair_details.append({
                    'table_name': game.table_name,
                    'pair_type': game.pair_type.value,
                    'pair_cards': game.pair_cards,
                    'game_time': game.game_time.isoformat()
                })
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        success_message = f"{total_games}개 게임 대량 생성 ({pairs_found}개 페어) - FastAPI 대량 처리"
        logger.info(f"✅ 대량 데모 데이터 생성 완료: {success_message}")
        
        return DemoResponse(
            success=True,
            message=success_message,
            games_added=total_games,
            pairs_found=pairs_found,
            processing_time=round(processing_time, 3),
            mode="fastapi_bulk_async",
            tables_affected=tables_affected,
            pair_details=pair_details,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"❌ 대량 데모 데이터 생성 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"대량 데모 데이터 생성 중 오류 발생: {str(e)}"
        )

async def process_pair_notifications(pair_details: List[dict]):
    """백그라운드 페어 알림 처리"""
    try:
        logger.info(f"🔔 페어 알림 처리 시작: {len(pair_details)}개")
        
        for pair in pair_details:
            # 실제로는 WebSocket, 이메일, 푸시 알림 등으로 전송
            logger.info(f"🎯 페어 알림: {pair['table_name']} - {pair['pair_type']}")
            await asyncio.sleep(0.1)  # 시뮬레이션 지연
        
        logger.info("✅ 페어 알림 처리 완료")
        
    except Exception as e:
        logger.error(f"❌ 페어 알림 처리 실패: {e}")

@router.get("/demo/generators/status")
async def get_generator_status():
    """데모 생성기 상태 확인"""
    return {
        "available_tables": DemoGameGenerator.get_available_tables(),
        "default_pair_probability": 0.25,
        "max_games_per_request": 100,
        "features": [
            "비동기 게임 생성",
            "배치 처리 지원",
            "페어 강제 생성",
            "테이블별 분산 처리",
            "실시간 알림 연동"
        ]
    }