#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Performance API Router - FastAPI
데이터베이스 성능 모니터링 및 최적화 API
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from pydantic import BaseModel

from services.optimized_database import OptimizedDatabaseManager, get_optimized_db_manager
from models.response import BaseResponse

logger = logging.getLogger(__name__)
router = APIRouter()

class DatabaseConfig(BaseModel):
    """데이터베이스 설정"""
    pool_size: Optional[int] = None
    cache_size: Optional[int] = None
    wal_mode: Optional[bool] = None

class QueryPerformanceRequest(BaseModel):
    """쿼리 성능 테스트 요청"""
    query_type: str  # "table_stats", "system_stats", "game_insert", "batch_insert"
    iterations: int = 100

@router.get("/health")
async def database_health_check(
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """데이터베이스 상태 확인"""
    try:
        start_time = datetime.now()
        
        # 연결 테스트
        is_healthy = await db_manager.health_check()
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # 연결 풀 상태
        pool_stats = db_manager.get_connection_pool_stats()
        
        # 성능 메트릭
        performance_stats = db_manager.get_performance_metrics()
        
        return {
            "success": True,
            "healthy": is_healthy == "healthy",
            "response_time_ms": round(response_time, 2),
            "connection_pool": pool_stats,
            "performance_metrics": performance_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 상태 확인 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")

@router.get("/performance/metrics")
async def get_performance_metrics(
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """데이터베이스 성능 메트릭 조회"""
    try:
        metrics = db_manager.get_performance_metrics()
        pool_stats = db_manager.get_connection_pool_stats()
        
        return BaseResponse(
            success=True,
            message="성능 메트릭을 성공적으로 조회했습니다.",
            data={
                "performance_metrics": metrics,
                "connection_pool_stats": pool_stats,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 성능 메트릭 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Performance metrics failed: {str(e)}")

@router.get("/performance/query-stats")
async def get_query_statistics(
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """쿼리 통계 조회"""
    try:
        stats = await db_manager.get_query_statistics()
        
        return BaseResponse(
            success=True,
            message="쿼리 통계를 성공적으로 조회했습니다.",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"❌ 쿼리 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Query statistics failed: {str(e)}")

@router.post("/performance/test")
async def test_query_performance(
    request: QueryPerformanceRequest,
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """쿼리 성능 테스트"""
    try:
        if request.iterations > 1000:
            raise HTTPException(status_code=400, detail="최대 1000회까지 테스트할 수 있습니다.")
        
        logger.info(f"🔬 성능 테스트 시작: {request.query_type} ({request.iterations}회)")
        
        test_results = await db_manager.benchmark_query_performance(
            request.query_type,
            request.iterations
        )
        
        return BaseResponse(
            success=True,
            message=f"{request.query_type} 성능 테스트가 완료되었습니다.",
            data=test_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 성능 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Performance test failed: {str(e)}")

@router.post("/optimize/vacuum")
async def vacuum_database(
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """데이터베이스 VACUUM 수행"""
    try:
        start_time = datetime.now()
        
        # 데이터베이스 크기 측정 (전)
        size_before = await db_manager.get_database_size_mb()
        
        # VACUUM 수행
        await db_manager.vacuum_database()
        
        # 데이터베이스 크기 측정 (후)
        size_after = await db_manager.get_database_size_mb()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        space_saved = size_before - size_after
        
        logger.info(f"🧹 데이터베이스 VACUUM 완료 - 시간: {processing_time:.2f}s, 절약: {space_saved:.2f}MB")
        
        return BaseResponse(
            success=True,
            message="데이터베이스 VACUUM이 완료되었습니다.",
            data={
                "processing_time_seconds": round(processing_time, 2),
                "size_before_mb": round(size_before, 2),
                "size_after_mb": round(size_after, 2),
                "space_saved_mb": round(space_saved, 2),
                "space_saved_percent": round((space_saved / size_before * 100), 2) if size_before > 0 else 0
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 VACUUM 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Database vacuum failed: {str(e)}")

@router.post("/optimize/reindex")
async def reindex_database(
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """데이터베이스 인덱스 재구성"""
    try:
        start_time = datetime.now()
        
        await db_manager.reindex_database()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"🔄 데이터베이스 인덱스 재구성 완료 - 시간: {processing_time:.2f}s")
        
        return BaseResponse(
            success=True,
            message="데이터베이스 인덱스 재구성이 완료되었습니다.",
            data={
                "processing_time_seconds": round(processing_time, 2),
                "reindex_completed_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 인덱스 재구성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Database reindex failed: {str(e)}")

@router.post("/optimize/analyze")
async def analyze_database(
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """데이터베이스 통계 갱신 (ANALYZE)"""
    try:
        start_time = datetime.now()
        
        await db_manager.analyze_database()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return BaseResponse(
            success=True,
            message="데이터베이스 통계 갱신이 완료되었습니다.",
            data={
                "processing_time_seconds": round(processing_time, 2),
                "analyze_completed_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Database analyze failed: {str(e)}")

@router.get("/size")
async def get_database_size(
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """데이터베이스 크기 정보"""
    try:
        size_mb = await db_manager.get_database_size_mb()
        
        return BaseResponse(
            success=True,
            message="데이터베이스 크기 정보를 조회했습니다.",
            data={
                "size_mb": round(size_mb, 2),
                "size_kb": round(size_mb * 1024, 2),
                "measured_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 데이터베이스 크기 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Database size query failed: {str(e)}")

@router.get("/pool/stats")
async def get_connection_pool_stats(
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """연결 풀 통계"""
    try:
        stats = db_manager.get_connection_pool_stats()
        
        return BaseResponse(
            success=True,
            message="연결 풀 통계를 조회했습니다.",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"❌ 연결 풀 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Connection pool stats failed: {str(e)}")

@router.post("/pool/warm-up")
async def warm_up_connection_pool(
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """연결 풀 워밍업"""
    try:
        start_time = datetime.now()
        
        await db_manager.warm_up_connections()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        pool_stats = db_manager.get_connection_pool_stats()
        
        return BaseResponse(
            success=True,
            message="연결 풀 워밍업이 완료되었습니다.",
            data={
                "processing_time_seconds": round(processing_time, 2),
                "pool_stats": pool_stats,
                "warmed_up_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 연결 풀 워밍업 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Connection pool warm-up failed: {str(e)}")

@router.get("/tables/info")
async def get_table_information(
    db_manager: OptimizedDatabaseManager = Depends(get_optimized_db_manager)
):
    """테이블 정보 조회"""
    try:
        table_info = await db_manager.get_table_information()
        
        return BaseResponse(
            success=True,
            message="테이블 정보를 조회했습니다.",
            data=table_info
        )
        
    except Exception as e:
        logger.error(f"❌ 테이블 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Table information failed: {str(e)}")