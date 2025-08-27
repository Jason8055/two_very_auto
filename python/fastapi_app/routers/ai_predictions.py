#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Predictions API Router - FastAPI
AI 예측 시스템 API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from pydantic import BaseModel

from services.async_ai_engine import get_async_ai_engine, AsyncAIPredictionEngine
from services.notification_service import get_notification_service, NotificationService
from models.response import BaseResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic 모델들
class PredictionRequest(BaseModel):
    current_game: Dict[str, Any]
    recent_games: List[Dict[str, Any]]
    table_name: Optional[str] = None

class BatchPredictionRequest(BaseModel):
    predictions: List[PredictionRequest]

class TrainingRequest(BaseModel):
    games_data: List[Dict[str, Any]]
    validation_split: Optional[float] = 0.2

class ValidationRequest(BaseModel):
    game_id: int
    actual_result: Dict[str, Any]

@router.post("/predict", response_model=BaseResponse)
async def predict_pair(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    ai_engine: AsyncAIPredictionEngine = Depends(get_async_ai_engine),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    페어 예측 수행
    
    - **current_game**: 현재 게임 데이터 (player_cards, banker_cards 포함)
    - **recent_games**: 최근 게임 이력 (최소 10개 권장)
    - **table_name**: 테이블 이름 (선택사항)
    """
    try:
        start_time = datetime.now()
        
        # 예측 수행
        prediction_result = await ai_engine.predict_pair_async(
            request.current_game,
            request.recent_games
        )
        
        # 테이블 이름 추가
        if request.table_name:
            prediction_result['table_name'] = request.table_name
        
        processing_time = (datetime.now() - start_time).total_seconds()
        prediction_result['api_processing_time'] = processing_time
        
        # 높은 신뢰도 예측에 대해 알림 전송 (백그라운드)
        if prediction_result.get('confidence', 0) > 0.8 and prediction_result.get('predicted_pair_type') != 'NO_PAIR':
            background_tasks.add_task(
                _send_prediction_notification,
                notification_service,
                prediction_result,
                request.table_name or "Unknown"
            )
        
        logger.info(f"🔮 예측 API 완료: {prediction_result['predicted_pair_type']} (신뢰도: {prediction_result['confidence']:.3f})")
        
        return BaseResponse(
            success=True,
            message="예측이 성공적으로 완료되었습니다.",
            data=prediction_result
        )
        
    except Exception as e:
        logger.error(f"❌ 예측 API 실패: {e}")
        raise HTTPException(status_code=500, detail=f"예측 실패: {str(e)}")

@router.post("/predict/batch", response_model=BaseResponse)
async def batch_predict_pairs(
    request: BatchPredictionRequest,
    ai_engine: AsyncAIPredictionEngine = Depends(get_async_ai_engine)
):
    """
    배치 예측 수행 (여러 게임 동시 예측)
    
    - **predictions**: 예측 요청 목록
    """
    try:
        if len(request.predictions) > 50:
            raise HTTPException(status_code=400, detail="배치 크기는 50개를 초과할 수 없습니다.")
        
        start_time = datetime.now()
        
        # 배치 데이터 준비
        batch_data = [
            (pred.current_game, pred.recent_games)
            for pred in request.predictions
        ]
        
        # 배치 예측 수행
        results = await ai_engine.batch_predict_async(batch_data)
        
        # 테이블 이름 추가
        for i, result in enumerate(results):
            if i < len(request.predictions) and request.predictions[i].table_name:
                result['table_name'] = request.predictions[i].table_name
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"📊 배치 예측 API 완료: {len(results)}개 결과 (시간: {processing_time:.3f}s)")
        
        return BaseResponse(
            success=True,
            message=f"{len(results)}개 예측이 성공적으로 완료되었습니다.",
            data={
                'predictions': results,
                'batch_size': len(results),
                'processing_time': processing_time,
                'avg_time_per_prediction': processing_time / len(results) if results else 0
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 배치 예측 API 실패: {e}")
        raise HTTPException(status_code=500, detail=f"배치 예측 실패: {str(e)}")

@router.post("/train", response_model=BaseResponse)
async def train_model(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    ai_engine: AsyncAIPredictionEngine = Depends(get_async_ai_engine),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    AI 모델 훈련 수행
    
    - **games_data**: 훈련 게임 데이터
    - **validation_split**: 검증 데이터 비율 (기본: 0.2)
    """
    try:
        if len(request.games_data) < 100:
            raise HTTPException(status_code=400, detail="훈련 데이터가 부족합니다. 최소 100개 게임 필요")
        
        logger.info(f"🏋️ 모델 훈련 API 시작: {len(request.games_data)}개 게임")
        
        # 백그라운드에서 훈련 시작 알림
        background_tasks.add_task(
            notification_service.send_system_warning,
            "AI 모델 훈련 시작",
            f"{len(request.games_data)}개 게임 데이터로 모델 훈련을 시작합니다.",
            {"games_count": len(request.games_data), "validation_split": request.validation_split}
        )
        
        # 모델 훈련 수행
        training_result = await ai_engine.train_model_async(request.games_data)
        
        # 훈련 완료 알림
        if training_result.get('success', False):
            background_tasks.add_task(
                notification_service.send_system_warning,
                "AI 모델 훈련 완료",
                f"모델 훈련이 완료되었습니다. 정확도: {training_result.get('val_accuracy', 0):.3f}",
                training_result
            )
        else:
            background_tasks.add_task(
                notification_service.send_system_warning,
                "AI 모델 훈련 실패",
                f"모델 훈련이 실패했습니다: {training_result.get('error', 'Unknown error')}",
                training_result
            )
        
        logger.info(f"🏋️ 모델 훈련 API 완료: 성공={training_result.get('success', False)}")
        
        return BaseResponse(
            success=training_result.get('success', False),
            message="모델 훈련 요청이 처리되었습니다." if training_result.get('success') else "모델 훈련이 실패했습니다.",
            data=training_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 모델 훈련 API 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 훈련 실패: {str(e)}")

@router.post("/validate", response_model=BaseResponse)
async def validate_prediction(
    request: ValidationRequest,
    ai_engine: AsyncAIPredictionEngine = Depends(get_async_ai_engine)
):
    """
    예측 결과 검증
    
    - **game_id**: 게임 ID
    - **actual_result**: 실제 결과 데이터
    """
    try:
        await ai_engine.validate_prediction_async(
            request.game_id,
            request.actual_result
        )
        
        return BaseResponse(
            success=True,
            message=f"게임 {request.game_id}의 예측 결과가 검증되었습니다.",
            data={
                'game_id': request.game_id,
                'validated_at': datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 예측 검증 API 실패: {e}")
        raise HTTPException(status_code=500, detail=f"예측 검증 실패: {str(e)}")

@router.get("/stats")
async def get_prediction_stats(
    ai_engine: AsyncAIPredictionEngine = Depends(get_async_ai_engine)
):
    """AI 예측 통계 조회"""
    try:
        stats = await ai_engine.get_prediction_stats_async()
        
        return {
            'success': True,
            'data': stats,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 예측 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

@router.get("/cache/info")
async def get_cache_info(
    ai_engine: AsyncAIPredictionEngine = Depends(get_async_ai_engine)
):
    """예측 캐시 정보 조회"""
    try:
        cache_info = ai_engine.get_cache_info()
        
        return {
            'success': True,
            'data': cache_info,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 캐시 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"캐시 정보 조회 실패: {str(e)}")

@router.post("/cache/clear", response_model=BaseResponse)
async def clear_prediction_cache(
    ai_engine: AsyncAIPredictionEngine = Depends(get_async_ai_engine)
):
    """예측 캐시 클리어"""
    try:
        cache_size_before = len(ai_engine.prediction_cache)
        
        ai_engine.prediction_cache.clear()
        ai_engine.cache_timestamps.clear()
        
        return BaseResponse(
            success=True,
            message=f"예측 캐시가 클리어되었습니다.",
            data={
                'cleared_items': cache_size_before,
                'current_cache_size': len(ai_engine.prediction_cache)
            }
        )
        
    except Exception as e:
        logger.error(f"❌ 캐시 클리어 실패: {e}")
        raise HTTPException(status_code=500, detail=f"캐시 클리어 실패: {str(e)}")

@router.post("/preload", response_model=BaseResponse)
async def preload_predictions(
    request: BatchPredictionRequest,
    background_tasks: BackgroundTasks,
    ai_engine: AsyncAIPredictionEngine = Depends(get_async_ai_engine)
):
    """
    예측 결과 미리 계산 (캐시 워밍업)
    
    - **predictions**: 미리 계산할 예측 요청 목록
    """
    try:
        if len(request.predictions) > 100:
            raise HTTPException(status_code=400, detail="프리로드 크기는 100개를 초과할 수 없습니다.")
        
        # 백그라운드에서 프리로드 수행
        background_tasks.add_task(
            _preload_predictions_task,
            ai_engine,
            request.predictions
        )
        
        return BaseResponse(
            success=True,
            message=f"{len(request.predictions)}개 예측 프리로드가 백그라운드에서 시작되었습니다.",
            data={
                'preload_count': len(request.predictions),
                'started_at': datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 예측 프리로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"프리로드 실패: {str(e)}")

@router.get("/health")
async def ai_health_check(
    ai_engine: AsyncAIPredictionEngine = Depends(get_async_ai_engine)
):
    """AI 예측 시스템 상태 확인"""
    try:
        stats = await ai_engine.get_prediction_stats_async()
        cache_info = ai_engine.get_cache_info()
        
        # 건강 상태 판단
        model_available = stats.get('model_stats', {}).get('model_info', {}).get('is_trained', False)
        cache_healthy = cache_info.get('cache_hit_rate', 0) > 0.1 or ai_engine.metrics['total_predictions'] < 10
        background_tasks_running = ai_engine.running
        
        overall_healthy = model_available and cache_healthy and background_tasks_running
        
        return {
            'success': True,
            'healthy': overall_healthy,
            'data': {
                'model_available': model_available,
                'cache_healthy': cache_healthy,
                'background_tasks_running': background_tasks_running,
                'cache_stats': cache_info,
                'performance_stats': stats.get('performance_stats', {}),
                'accuracy_stats': stats.get('accuracy_stats', {})
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ AI 시스템 상태 확인 실패: {e}")
        return {
            'success': False,
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

# 백그라운드 작업 함수들
async def _send_prediction_notification(
    notification_service: NotificationService,
    prediction_result: Dict[str, Any],
    table_name: str
):
    """예측 알림 전송 (백그라운드)"""
    try:
        await notification_service.send_ai_prediction(
            table_name=table_name,
            prediction=prediction_result
        )
    except Exception as e:
        logger.error(f"❌ 예측 알림 전송 실패: {e}")

async def _preload_predictions_task(
    ai_engine: AsyncAIPredictionEngine,
    predictions: List[PredictionRequest]
):
    """프리로드 작업 (백그라운드)"""
    try:
        batch_data = [
            (pred.current_game, pred.recent_games)
            for pred in predictions
        ]
        
        await ai_engine.preload_predictions_async(batch_data)
        logger.info(f"✅ 백그라운드 프리로드 완료: {len(predictions)}개")
        
    except Exception as e:
        logger.error(f"❌ 백그라운드 프리로드 실패: {e}")