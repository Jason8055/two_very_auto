#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
딥러닝 분석 관련 API 라우트
페어 패턴 분석, AI 예측, 고급 통계 제공
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

# 로컬 모듈
from ..services.deep_learning_analysis_service import DeepLearningAnalysisService, get_deep_learning_analysis_service
from ..services.optimized_database import OptimizedDatabase, get_database_service
from ..services.async_ai_engine import AsyncAIEngine, get_async_ai_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analysis", tags=["딥러닝 분석"])


@router.get("/patterns/{table_name}")
async def analyze_table_patterns(
    table_name: str,
    days: int = Query(7, ge=1, le=30, description="분석 기간 (일)"),
    include_prediction: bool = Query(True, description="예측 분석 포함 여부"),
    force_refresh: bool = Query(False, description="캐시 무시하고 새로 분석"),
    analysis_service: DeepLearningAnalysisService = Depends(get_deep_learning_analysis_service)
):
    """
    특정 테이블의 페어 패턴 딥러닝 분석
    
    Args:
        table_name: 분석할 테이블명 (예: "스피드바카라A")
        days: 분석할 일수
        include_prediction: AI 예측 분석 포함 여부
        force_refresh: 캐시 무시하고 새로 분석
        analysis_service: 딥러닝 분석 서비스
        
    Returns:
        테이블별 상세 패턴 분석 결과
    """
    try:
        logger.info(f"테이블 {table_name} 패턴 분석 요청 (기간: {days}일)")
        
        # 캐시 강제 갱신
        if force_refresh:
            await analysis_service.cleanup_cache()
        
        # 패턴 분석 수행
        analysis_result = await analysis_service.analyze_pair_patterns(
            table_name=table_name,
            days=days,
            include_prediction=include_prediction
        )
        
        return {
            "status": "success",
            "data": analysis_result,
            "meta": {
                "requested_table": table_name,
                "analysis_period": days,
                "prediction_included": include_prediction,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"패턴 분석 실패 {table_name}: {e}")
        raise HTTPException(status_code=500, detail=f"패턴 분석 실패: {str(e)}")


@router.get("/predictions/next")
async def get_next_game_predictions(
    table_name: str = Query(..., description="예측할 테이블명"),
    prediction_count: int = Query(5, ge=1, le=10, description="예측할 게임 수"),
    confidence_threshold: float = Query(0.6, ge=0.0, le=1.0, description="최소 신뢰도"),
    analysis_service: DeepLearningAnalysisService = Depends(get_deep_learning_analysis_service),
    db: OptimizedDatabase = Depends(get_database_service)
):
    """
    다음 게임들에 대한 AI 페어 예측
    
    Args:
        table_name: 예측할 테이블명
        prediction_count: 예측할 게임 수
        confidence_threshold: 최소 신뢰도 기준
        analysis_service: 딥러닝 분석 서비스
        db: 데이터베이스 서비스
        
    Returns:
        향후 게임들에 대한 페어 예측 결과
    """
    try:
        logger.info(f"테이블 {table_name} 다음 {prediction_count}게임 예측 요청")
        
        # 최근 게임 데이터 조회
        recent_games = await db.get_recent_games(table_name=table_name, limit=50)
        
        if len(recent_games) < 20:
            raise HTTPException(
                status_code=400,
                detail="예측을 위한 충분한 히스토리 데이터가 없습니다 (최소 20게임 필요)"
            )
        
        # 패턴 분석 수행 (예측 포함)
        analysis_result = await analysis_service.analyze_pair_patterns(
            table_name=table_name,
            days=7,
            include_prediction=True
        )
        
        if analysis_result.get('status') != 'success':
            raise HTTPException(status_code=500, detail="패턴 분석 실패")
        
        # 예측 데이터 추출
        prediction_analysis = analysis_result.get('prediction_analysis', {})
        future_predictions = prediction_analysis.get('future_predictions', [])
        
        # 신뢰도 필터링
        filtered_predictions = [
            pred for pred in future_predictions
            if pred.get('confidence', 0) >= confidence_threshold
        ]
        
        # 예측 요약 생성
        prediction_summary = _generate_prediction_summary(filtered_predictions, recent_games)
        
        return {
            "status": "success",
            "data": {
                "table_name": table_name,
                "predictions": filtered_predictions[:prediction_count],
                "summary": prediction_summary,
                "model_info": prediction_analysis.get('model_info', {}),
                "confidence_threshold": confidence_threshold,
                "recent_accuracy": prediction_analysis.get('test_results', {}).get('accuracy', 0)
            },
            "meta": {
                "total_predictions": len(filtered_predictions),
                "requested_count": prediction_count,
                "data_source_games": len(recent_games),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"예측 생성 실패 {table_name}: {e}")
        raise HTTPException(status_code=500, detail=f"예측 생성 실패: {str(e)}")


@router.get("/performance/comparison")
async def compare_table_performance(
    tables: str = Query(..., description="비교할 테이블명들 (쉼표로 구분)"),
    days: int = Query(7, ge=1, le=30, description="비교 기간 (일)"),
    analysis_service: DeepLearningAnalysisService = Depends(get_deep_learning_analysis_service)
):
    """
    여러 테이블의 성능 비교 분석
    
    Args:
        tables: 비교할 테이블명들 (예: "스피드바카라A,스피드바카라B")
        days: 비교 기간
        analysis_service: 딥러닝 분석 서비스
        
    Returns:
        테이블 간 성능 비교 결과
    """
    try:
        table_list = [table.strip() for table in tables.split(',')]
        
        if len(table_list) < 2:
            raise HTTPException(status_code=400, detail="최소 2개 테이블이 필요합니다")
        
        if len(table_list) > 5:
            raise HTTPException(status_code=400, detail="최대 5개 테이블까지 비교 가능합니다")
        
        logger.info(f"테이블 성능 비교: {table_list} ({days}일)")
        
        # 각 테이블별 분석 수행
        comparison_results = {}
        
        for table_name in table_list:
            analysis_result = await analysis_service.analyze_pair_patterns(
                table_name=table_name,
                days=days,
                include_prediction=True
            )
            comparison_results[table_name] = analysis_result
        
        # 비교 메트릭 계산
        comparison_metrics = _calculate_comparison_metrics(comparison_results)
        
        # 순위 생성
        rankings = _generate_table_rankings(comparison_results)
        
        return {
            "status": "success",
            "data": {
                "comparison_period": {
                    "days": days,
                    "from": (datetime.now() - timedelta(days=days)).isoformat(),
                    "to": datetime.now().isoformat()
                },
                "table_results": comparison_results,
                "comparison_metrics": comparison_metrics,
                "rankings": rankings,
                "summary": _generate_comparison_summary(comparison_results, rankings)
            },
            "meta": {
                "compared_tables": table_list,
                "total_tables": len(table_list),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"테이블 성능 비교 실패: {e}")
        raise HTTPException(status_code=500, detail=f"성능 비교 실패: {str(e)}")


@router.get("/trends/historical")
async def get_historical_trends(
    table_name: Optional[str] = Query(None, description="특정 테이블 (없으면 전체)"),
    period: str = Query("week", regex="^(day|week|month)$", description="분석 기간 단위"),
    trend_type: str = Query("pair_rate", regex="^(pair_rate|frequency|patterns)$", description="트렌드 타입"),
    analysis_service: DeepLearningAnalysisService = Depends(get_deep_learning_analysis_service),
    db: OptimizedDatabase = Depends(get_database_service)
):
    """
    히스토리컬 트렌드 분석
    
    Args:
        table_name: 분석할 테이블 (없으면 전체)
        period: 분석 기간 단위 (day, week, month)
        trend_type: 트렌드 타입 (pair_rate, frequency, patterns)
        analysis_service: 딥러닝 분석 서비스
        db: 데이터베이스 서비스
        
    Returns:
        히스토리컬 트렌드 분석 결과
    """
    try:
        logger.info(f"히스토리컬 트렌드 분석: {table_name or 'ALL'} ({period}, {trend_type})")
        
        # 기간 설정
        period_mapping = {
            'day': 1,
            'week': 7,
            'month': 30
        }
        days = period_mapping[period]
        
        # 트렌드 데이터 수집
        if table_name:
            trend_data = await _collect_table_trends(table_name, days, trend_type, db)
        else:
            trend_data = await _collect_global_trends(days, trend_type, db)
        
        # 트렌드 분석 수행
        trend_analysis = _analyze_trends(trend_data, period, trend_type)
        
        # 예측 트렌드 생성
        future_trend = _predict_future_trend(trend_data, trend_analysis)
        
        return {
            "status": "success",
            "data": {
                "table_name": table_name or "전체",
                "period": period,
                "trend_type": trend_type,
                "historical_data": trend_data,
                "trend_analysis": trend_analysis,
                "future_prediction": future_trend,
                "insights": _generate_trend_insights(trend_analysis, trend_type)
            },
            "meta": {
                "analysis_days": days,
                "data_points": len(trend_data),
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"트렌드 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"트렌드 분석 실패: {str(e)}")


@router.post("/model/train")
async def trigger_model_training(
    background_tasks: BackgroundTasks,
    table_name: Optional[str] = Query(None, description="훈련할 테이블 (없으면 전체)"),
    force_retrain: bool = Query(False, description="강제 재훈련"),
    analysis_service: DeepLearningAnalysisService = Depends(get_deep_learning_analysis_service),
    ai_engine: AsyncAIEngine = Depends(get_async_ai_engine)
):
    """
    AI 모델 훈련 트리거
    
    Args:
        background_tasks: 백그라운드 작업 관리자
        table_name: 특정 테이블 훈련 (없으면 전체 데이터)
        force_retrain: 강제 재훈련 여부
        analysis_service: 딥러닝 분석 서비스
        ai_engine: AI 엔진
        
    Returns:
        모델 훈련 시작 결과
    """
    try:
        logger.info(f"AI 모델 훈련 요청: {table_name or 'ALL'} (강제훈련: {force_retrain})")
        
        # 백그라운드에서 훈련 실행
        background_tasks.add_task(
            _background_model_training,
            analysis_service,
            ai_engine,
            table_name,
            force_retrain
        )
        
        # 현재 모델 상태
        current_stats = analysis_service.get_analysis_stats()
        
        return {
            "status": "success",
            "message": "AI 모델 훈련이 백그라운드에서 시작되었습니다.",
            "data": {
                "training_target": table_name or "전체 데이터",
                "force_retrain": force_retrain,
                "current_model_stats": current_stats,
                "estimated_duration": "5-15분 예상"
            },
            "meta": {
                "training_started": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"모델 훈련 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 훈련 시작 실패: {str(e)}")


@router.get("/model/status")
async def get_model_status(
    analysis_service: DeepLearningAnalysisService = Depends(get_deep_learning_analysis_service),
    ai_engine: AsyncAIEngine = Depends(get_async_ai_engine)
):
    """
    AI 모델 상태 조회
    
    Args:
        analysis_service: 딥러닝 분석 서비스
        ai_engine: AI 엔진
        
    Returns:
        현재 AI 모델 상태 정보
    """
    try:
        # 분석 서비스 통계
        analysis_stats = analysis_service.get_analysis_stats()
        
        # AI 엔진 정보
        ai_stats = await ai_engine.get_engine_status()
        
        return {
            "status": "success",
            "data": {
                "analysis_service": analysis_stats,
                "ai_engine": ai_stats,
                "system_health": {
                    "analysis_service_active": True,
                    "ai_engine_active": ai_stats.get('active', False),
                    "model_trained": analysis_stats.get('ai_engine_stats', {}).get('is_trained', False),
                    "last_training": analysis_stats.get('last_training'),
                    "cache_status": f"{analysis_stats.get('cache_size', 0)}개 항목 캐시됨"
                },
                "recommendations": _generate_model_recommendations(analysis_stats, ai_stats)
            },
            "meta": {
                "status_check_time": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"모델 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 상태 조회 실패: {str(e)}")


# 유틸리티 함수들

def _generate_prediction_summary(predictions: list, recent_games: list) -> Dict[str, Any]:
    """예측 요약 생성"""
    try:
        if not predictions:
            return {"message": "신뢰도 기준을 만족하는 예측이 없습니다"}
        
        # 예측 분포
        prediction_distribution = {}
        total_confidence = 0
        
        for pred in predictions:
            pair_type = pred.get('predicted_pair_type', 'NO_PAIR')
            prediction_distribution[pair_type] = prediction_distribution.get(pair_type, 0) + 1
            total_confidence += pred.get('confidence', 0)
        
        avg_confidence = total_confidence / len(predictions) if predictions else 0
        
        # 최고 신뢰도 예측
        best_prediction = max(predictions, key=lambda x: x.get('confidence', 0))
        
        return {
            "total_predictions": len(predictions),
            "average_confidence": round(avg_confidence, 3),
            "prediction_distribution": prediction_distribution,
            "best_prediction": {
                "type": best_prediction.get('predicted_pair_type'),
                "confidence": best_prediction.get('confidence'),
                "game_sequence": best_prediction.get('game_sequence')
            },
            "recent_pattern": f"최근 {len(recent_games)}게임 중 {sum(1 for g in recent_games if g.get('has_pair', False))}개 페어"
        }
        
    except Exception as e:
        logger.error(f"예측 요약 생성 실패: {e}")
        return {"error": "예측 요약 생성 실패"}


def _calculate_comparison_metrics(comparison_results: Dict[str, Any]) -> Dict[str, Any]:
    """테이블 비교 메트릭 계산"""
    try:
        metrics = {
            "pair_rates": {},
            "prediction_accuracy": {},
            "data_quality": {},
            "volatility": {}
        }
        
        for table_name, result in comparison_results.items():
            if result.get('status') != 'success':
                continue
                
            pattern_analysis = result.get('pattern_analysis', {})
            prediction_analysis = result.get('prediction_analysis', {})
            
            # 페어율
            basic_stats = pattern_analysis.get('basic_stats', {})
            metrics["pair_rates"][table_name] = basic_stats.get('pair_rate', 0)
            
            # 예측 정확도
            if prediction_analysis and prediction_analysis.get('status') == 'success':
                test_results = prediction_analysis.get('test_results', {})
                metrics["prediction_accuracy"][table_name] = test_results.get('accuracy', 0)
            
            # 데이터 품질
            metrics["data_quality"][table_name] = basic_stats.get('total_games', 0)
            
            # 변동성
            advanced_metrics = pattern_analysis.get('advanced_metrics', {})
            volatility_analysis = advanced_metrics.get('volatility_analysis', {})
            metrics["volatility"][table_name] = volatility_analysis.get('volatility', 0)
        
        return metrics
        
    except Exception as e:
        logger.error(f"비교 메트릭 계산 실패: {e}")
        return {}


def _generate_table_rankings(comparison_results: Dict[str, Any]) -> Dict[str, list]:
    """테이블 순위 생성"""
    try:
        rankings = {
            "by_pair_rate": [],
            "by_prediction_accuracy": [],
            "by_data_volume": [],
            "overall": []
        }
        
        table_scores = {}
        
        for table_name, result in comparison_results.items():
            if result.get('status') != 'success':
                continue
            
            pattern_analysis = result.get('pattern_analysis', {})
            prediction_analysis = result.get('prediction_analysis', {})
            basic_stats = pattern_analysis.get('basic_stats', {})
            
            score = 0
            
            # 페어율 점수
            pair_rate = basic_stats.get('pair_rate', 0)
            rankings["by_pair_rate"].append((table_name, pair_rate))
            score += pair_rate
            
            # 예측 정확도 점수
            accuracy = 0
            if prediction_analysis and prediction_analysis.get('status') == 'success':
                test_results = prediction_analysis.get('test_results', {})
                accuracy = test_results.get('accuracy', 0)
            rankings["by_prediction_accuracy"].append((table_name, accuracy))
            score += accuracy
            
            # 데이터 볼륨 점수
            data_volume = basic_stats.get('total_games', 0)
            rankings["by_data_volume"].append((table_name, data_volume))
            score += min(100, data_volume / 10)  # 최대 100점
            
            table_scores[table_name] = score
        
        # 정렬
        for category in rankings:
            if category != "overall":
                rankings[category].sort(key=lambda x: x[1], reverse=True)
        
        # 종합 순위
        rankings["overall"] = sorted(table_scores.items(), key=lambda x: x[1], reverse=True)
        
        return rankings
        
    except Exception as e:
        logger.error(f"순위 생성 실패: {e}")
        return {}


def _generate_comparison_summary(comparison_results: Dict[str, Any], rankings: Dict[str, list]) -> Dict[str, Any]:
    """비교 요약 생성"""
    try:
        if not rankings.get("overall"):
            return {"message": "비교 가능한 데이터가 없습니다"}
        
        best_table = rankings["overall"][0][0]
        worst_table = rankings["overall"][-1][0]
        
        # 최고 테이블 정보
        best_result = comparison_results[best_table]
        best_stats = best_result.get('pattern_analysis', {}).get('basic_stats', {})
        
        return {
            "best_performing_table": best_table,
            "worst_performing_table": worst_table,
            "performance_gap": round(rankings["overall"][0][1] - rankings["overall"][-1][1], 2),
            "best_table_stats": {
                "pair_rate": best_stats.get('pair_rate', 0),
                "total_games": best_stats.get('total_games', 0),
                "confidence_score": best_result.get('confidence_score', 0)
            },
            "recommendation": f"{best_table}가 가장 안정적인 패턴을 보이고 있습니다."
        }
        
    except Exception as e:
        logger.error(f"비교 요약 생성 실패: {e}")
        return {"error": "비교 요약 생성 실패"}


async def _collect_table_trends(table_name: str, days: int, trend_type: str, db: OptimizedDatabase) -> list:
    """테이블별 트렌드 데이터 수집"""
    try:
        # 일별 데이터 수집
        trend_data = []
        
        for day_offset in range(days):
            date = datetime.now() - timedelta(days=day_offset)
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            # 해당 날짜의 데이터 조회
            day_games = await db.get_games_between_dates(table_name, day_start, day_end)
            
            if trend_type == "pair_rate":
                total_games = len(day_games)
                pair_games = sum(1 for g in day_games if g.get('has_pair', False))
                value = (pair_games / total_games * 100) if total_games > 0 else 0
                
            elif trend_type == "frequency":
                value = sum(1 for g in day_games if g.get('has_pair', False))
                
            else:  # patterns
                # 패턴 다양성 점수
                pair_types = set(g.get('pair_type') for g in day_games if g.get('has_pair', False))
                value = len(pair_types)
            
            trend_data.append({
                "date": day_start.isoformat(),
                "value": value,
                "games_count": len(day_games)
            })
        
        return list(reversed(trend_data))  # 시간순 정렬
        
    except Exception as e:
        logger.error(f"테이블 트렌드 수집 실패: {e}")
        return []


async def _collect_global_trends(days: int, trend_type: str, db: OptimizedDatabase) -> list:
    """전체 트렌드 데이터 수집"""
    try:
        # 전체 테이블에 대한 트렌드 수집
        trend_data = []
        
        for day_offset in range(days):
            date = datetime.now() - timedelta(days=day_offset)
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            # 해당 날짜의 전체 데이터 조회
            day_games = await db.get_games_between_dates(None, day_start, day_end)
            
            if trend_type == "pair_rate":
                total_games = len(day_games)
                pair_games = sum(1 for g in day_games if g.get('has_pair', False))
                value = (pair_games / total_games * 100) if total_games > 0 else 0
                
            elif trend_type == "frequency":
                value = sum(1 for g in day_games if g.get('has_pair', False))
                
            else:  # patterns
                pair_types = set(g.get('pair_type') for g in day_games if g.get('has_pair', False))
                value = len(pair_types)
            
            trend_data.append({
                "date": day_start.isoformat(),
                "value": value,
                "games_count": len(day_games),
                "active_tables": len(set(g.get('table_name') for g in day_games))
            })
        
        return list(reversed(trend_data))
        
    except Exception as e:
        logger.error(f"전체 트렌드 수집 실패: {e}")
        return []


def _analyze_trends(trend_data: list, period: str, trend_type: str) -> Dict[str, Any]:
    """트렌드 분석"""
    try:
        if not trend_data:
            return {"error": "분석할 데이터가 없습니다"}
        
        values = [item["value"] for item in trend_data]
        
        # 기본 통계
        import numpy as np
        
        trend_analysis = {
            "average": round(np.mean(values), 2),
            "minimum": min(values),
            "maximum": max(values),
            "std_deviation": round(np.std(values), 2),
            "trend_direction": "stable"
        }
        
        # 트렌드 방향 분석
        if len(values) >= 3:
            recent_avg = np.mean(values[-3:])
            early_avg = np.mean(values[:3])
            
            diff = recent_avg - early_avg
            if diff > trend_analysis["std_deviation"]:
                trend_analysis["trend_direction"] = "increasing"
            elif diff < -trend_analysis["std_deviation"]:
                trend_analysis["trend_direction"] = "decreasing"
        
        # 변동성 평가
        cv = trend_analysis["std_deviation"] / trend_analysis["average"] if trend_analysis["average"] > 0 else 0
        
        if cv < 0.1:
            trend_analysis["volatility"] = "low"
        elif cv < 0.3:
            trend_analysis["volatility"] = "medium"
        else:
            trend_analysis["volatility"] = "high"
        
        return trend_analysis
        
    except Exception as e:
        logger.error(f"트렌드 분석 실패: {e}")
        return {"error": "트렌드 분석 실패"}


def _predict_future_trend(trend_data: list, trend_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """미래 트렌드 예측"""
    try:
        if not trend_data or len(trend_data) < 3:
            return {"prediction": "insufficient_data"}
        
        # 단순 선형 예측
        values = [item["value"] for item in trend_data]
        
        # 최근 3일 평균과 전체 평균 비교
        recent_avg = sum(values[-3:]) / 3
        overall_avg = trend_analysis.get("average", 0)
        
        if recent_avg > overall_avg * 1.1:
            prediction = "증가 추세 지속 예상"
            confidence = "medium"
        elif recent_avg < overall_avg * 0.9:
            prediction = "감소 추세 지속 예상"
            confidence = "medium"
        else:
            prediction = "안정적 패턴 유지 예상"
            confidence = "high"
        
        return {
            "prediction": prediction,
            "confidence": confidence,
            "expected_range": {
                "min": round(recent_avg * 0.8, 2),
                "max": round(recent_avg * 1.2, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"미래 트렌드 예측 실패: {e}")
        return {"prediction": "예측 불가", "error": str(e)}


def _generate_trend_insights(trend_analysis: Dict[str, Any], trend_type: str) -> list:
    """트렌드 인사이트 생성"""
    insights = []
    
    try:
        trend_direction = trend_analysis.get("trend_direction", "stable")
        volatility = trend_analysis.get("volatility", "medium")
        average = trend_analysis.get("average", 0)
        
        # 트렌드 방향별 인사이트
        if trend_direction == "increasing":
            if trend_type == "pair_rate":
                insights.append("페어 발생률이 증가하고 있습니다. 이는 카드 분배 패턴의 변화를 시사할 수 있습니다.")
            elif trend_type == "frequency":
                insights.append("페어 발생 빈도가 높아지고 있습니다. 베팅 전략 조정을 고려해보세요.")
        
        elif trend_direction == "decreasing":
            if trend_type == "pair_rate":
                insights.append("페어 발생률이 감소 추세입니다. 일시적 현상일 수 있으니 지속적인 모니터링이 필요합니다.")
        
        # 변동성별 인사이트
        if volatility == "high":
            insights.append("높은 변동성이 관찰됩니다. 예측의 불확실성이 크므로 신중한 접근이 필요합니다.")
        elif volatility == "low":
            insights.append("안정적인 패턴을 보이고 있어 예측 신뢰도가 높습니다.")
        
        # 평균값 기반 인사이트
        if trend_type == "pair_rate" and average > 15:
            insights.append("일반적인 페어 발생률(약 11%)보다 높은 수준입니다.")
        elif trend_type == "pair_rate" and average < 8:
            insights.append("평균 이하의 페어 발생률을 보이고 있습니다.")
        
        return insights
        
    except Exception as e:
        logger.error(f"트렌드 인사이트 생성 실패: {e}")
        return ["인사이트 생성 중 오류가 발생했습니다."]


async def _background_model_training(analysis_service: DeepLearningAnalysisService,
                                   ai_engine: AsyncAIEngine,
                                   table_name: Optional[str],
                                   force_retrain: bool):
    """백그라운드 모델 훈련"""
    try:
        logger.info("백그라운드 모델 훈련 시작")
        
        # 훈련 데이터 수집
        if table_name:
            # 특정 테이블 데이터
            training_data = await analysis_service._collect_games_data(
                table_name, 
                datetime.now() - timedelta(days=30)
            )
        else:
            # 전체 테이블 데이터 (임시 구현)
            training_data = analysis_service._generate_test_data("ALL", 500)
        
        if len(training_data) < 50:
            logger.warning("훈련 데이터 부족으로 훈련을 건너뜁니다")
            return
        
        # 모델 훈련 실행
        training_result = await analysis_service._train_model_if_needed(training_data)
        
        if training_result.get('success'):
            logger.info(f"백그라운드 모델 훈련 완료: {training_result.get('val_accuracy', 0):.3f}")
        else:
            logger.error(f"백그라운드 모델 훈련 실패: {training_result.get('error', 'Unknown error')}")
        
    except Exception as e:
        logger.error(f"백그라운드 모델 훈련 중 오류: {e}")


def _generate_model_recommendations(analysis_stats: Dict[str, Any], ai_stats: Dict[str, Any]) -> list:
    """모델 추천사항 생성"""
    recommendations = []
    
    try:
        # 훈련 상태 확인
        is_trained = analysis_stats.get('ai_engine_stats', {}).get('is_trained', False)
        if not is_trained:
            recommendations.append("모델이 훈련되지 않았습니다. 모델 훈련을 실행하세요.")
        
        # 훈련 빈도 확인
        last_training = analysis_stats.get('last_training')
        if last_training:
            from datetime import datetime
            last_train_date = datetime.fromisoformat(last_training)
            days_since_training = (datetime.now() - last_train_date).days
            
            if days_since_training > 7:
                recommendations.append(f"마지막 훈련 후 {days_since_training}일이 경과했습니다. 재훈련을 고려하세요.")
        
        # 성능 확인
        successful_predictions = analysis_stats.get('successful_predictions', 0)
        total_analyses = analysis_stats.get('total_analyses', 0)
        
        if total_analyses > 10 and successful_predictions / total_analyses < 0.7:
            recommendations.append("예측 성공률이 낮습니다. 모델 파라미터 조정이 필요할 수 있습니다.")
        
        # 캐시 상태
        cache_size = analysis_stats.get('cache_size', 0)
        if cache_size > 100:
            recommendations.append("분석 캐시가 많이 쌓여있습니다. 주기적으로 정리하세요.")
        
        if not recommendations:
            recommendations.append("모든 시스템이 정상적으로 작동하고 있습니다.")
        
        return recommendations
        
    except Exception as e:
        logger.error(f"모델 추천사항 생성 실패: {e}")
        return ["추천사항 생성 중 오류가 발생했습니다."]