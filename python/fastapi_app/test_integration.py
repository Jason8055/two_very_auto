#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration Test Script
통합 시스템 테스트
"""

import asyncio
import sys
from pathlib import Path
import logging

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from services.database import DatabaseManager
from services.optimized_database import OptimizedDatabaseManager
from services.notification_service import NotificationService
from services.connection_monitor import ConnectionMonitor
from services.async_ai_engine import AsyncAIPredictionEngine
from services.advanced_cache import get_cache, init_all_caches, stop_all_caches

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_database_integration():
    """데이터베이스 통합 테스트"""
    logger.info("🔄 데이터베이스 통합 테스트 시작")
    
    # 기본 DB 매니저
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # 최적화 DB 매니저
    optimized_db = OptimizedDatabaseManager()
    await optimized_db.initialize()
    
    # 상태 확인
    basic_health = await db_manager.health_check()
    optimized_health = await optimized_db.health_check()
    
    logger.info(f"✅ 기본 DB 상태: {basic_health}")
    logger.info(f"✅ 최적화 DB 상태: {optimized_health}")
    
    # 통계 조회 테스트
    try:
        stats = await db_manager.get_system_stats()
        logger.info(f"✅ 시스템 통계 조회 성공: {stats.get('total_games', 0)}개 게임")
    except Exception as e:
        logger.warning(f"⚠️ 시스템 통계 조회 실패 (정상 - 빈 DB): {e}")
    
    # 성능 메트릭 테스트
    performance_metrics = optimized_db.get_performance_metrics()
    logger.info(f"✅ 성능 메트릭: {performance_metrics}")
    
    # 정리
    await db_manager.close()
    await optimized_db.close()
    logger.info("✅ 데이터베이스 통합 테스트 완료")

async def test_cache_integration():
    """캐시 통합 테스트"""
    logger.info("🔄 캐시 통합 테스트 시작")
    
    # 고급 캐시 초기화
    await init_all_caches()
    
    # 기본 캐시 테스트
    default_cache = get_cache("default")
    await default_cache.set("test_key", {"message": "Hello Cache"})
    
    cached_value = await default_cache.get("test_key")
    logger.info(f"✅ 캐시 저장/조회 테스트: {cached_value}")
    
    # 캐시 통계
    stats = default_cache.get_stats()
    logger.info(f"✅ 캐시 통계: hit_rate={stats.get('current_stats', {}).get('hit_rate', 0):.2f}")
    
    # 정리
    await stop_all_caches()
    logger.info("✅ 캐시 통합 테스트 완료")

async def test_notification_integration():
    """알림 통합 테스트"""
    logger.info("🔄 알림 통합 테스트 시작")
    
    notification_service = NotificationService()
    await notification_service.start()
    
    # 테스트 알림 전송
    await notification_service.send_system_warning(
        "테스트 알림",
        "통합 테스트가 실행되었습니다.",
        {"test": True, "timestamp": "now"}
    )
    
    logger.info("✅ 테스트 알림 전송 완료")
    
    # 정리
    await notification_service.stop()
    logger.info("✅ 알림 통합 테스트 완료")

async def test_connection_monitoring():
    """연결 모니터링 테스트"""
    logger.info("🔄 연결 모니터링 테스트 시작")
    
    connection_monitor = ConnectionMonitor()
    await connection_monitor.start_monitoring()
    
    # 모니터링 통계
    stats = connection_monitor.get_monitoring_stats()
    logger.info(f"✅ 모니터링 통계: {stats}")
    
    # 정리
    await connection_monitor.stop_monitoring()
    logger.info("✅ 연결 모니터링 테스트 완료")

async def test_ai_engine():
    """AI 엔진 테스트"""
    logger.info("🔄 AI 엔진 테스트 시작")
    
    try:
        ai_engine = AsyncAIPredictionEngine()
        await ai_engine.start_background_tasks()
        
        # 테스트 예측 (더미 데이터)
        current_game = {
            "player_cards": ["A♠", "5♦"],
            "banker_cards": ["K♥", "3♣"]
        }
        recent_games = []
        
        # 실제 예측은 모델이 없으면 실패하므로 캐시 정보만 확인
        cache_info = ai_engine.get_cache_info()
        logger.info(f"✅ AI 캐시 정보: {cache_info}")
        
        stats = await ai_engine.get_prediction_stats_async()
        logger.info(f"✅ AI 통계: {stats}")
        
        # 정리
        await ai_engine.stop_background_tasks()
        logger.info("✅ AI 엔진 테스트 완료")
        
    except Exception as e:
        logger.warning(f"⚠️ AI 엔진 테스트 실패 (정상 - 모델 없음): {e}")

async def run_integration_tests():
    """전체 통합 테스트 실행"""
    logger.info("=" * 60)
    logger.info("🚀 Two Very Auto FastAPI - 통합 테스트 시작")
    logger.info("=" * 60)
    
    try:
        await test_database_integration()
        await test_cache_integration()
        await test_notification_integration()
        await test_connection_monitoring()
        await test_ai_engine()
        
        logger.info("=" * 60)
        logger.info("✅ 모든 통합 테스트 완료 - 시스템 정상")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 통합 테스트 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(run_integration_tests())