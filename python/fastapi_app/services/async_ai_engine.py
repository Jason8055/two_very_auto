#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Async AI Prediction Engine - FastAPI
비동기 AI 예측 엔진 with 캐싱 및 성능 최적화
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import pickle
from pathlib import Path
import hashlib
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np

# AI 예측 엔진 import
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from ai_prediction_engine import AIPredictionEngine, get_ai_prediction_engine

logger = logging.getLogger(__name__)

class AsyncAIPredictionEngine:
    """비동기 AI 예측 엔진"""
    
    def __init__(self, 
                 model_path: str = "pair_prediction_model.h5",
                 cache_size: int = 1000,
                 cache_ttl_minutes: int = 30,
                 max_workers: int = 2):
        
        self.model_path = model_path
        self.cache_size = cache_size
        self.cache_ttl_minutes = cache_ttl_minutes
        
        # 예측 캐시 (입력 해시 → 예측 결과)
        self.prediction_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # 성능 메트릭
        self.metrics = {
            'total_predictions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_prediction_time': 0.0,
            'prediction_times': deque(maxlen=100),
            'accuracy_tracker': {
                'correct_predictions': 0,
                'total_predictions': 0,
                'accuracy': 0.0
            },
            'model_stats': {}
        }
        
        # 비동기 처리를 위한 ThreadPoolExecutor
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 동기 AI 엔진 인스턴스
        self.sync_engine: Optional[AIPredictionEngine] = None
        self._engine_lock = asyncio.Lock()
        
        # 백그라운드 작업
        self.background_tasks = set()
        self.running = False
    
    async def initialize(self):
        """비동기 초기화"""
        async with self._engine_lock:
            if self.sync_engine is None:
                # ThreadPool에서 동기 엔진 초기화
                loop = asyncio.get_event_loop()
                self.sync_engine = await loop.run_in_executor(
                    self.executor, 
                    get_ai_prediction_engine
                )
                logger.info("🧠 Async AI 예측 엔진 초기화 완료")
        
        # 백그라운드 작업 시작
        await self.start_background_tasks()
    
    async def start_background_tasks(self):
        """백그라운드 작업 시작"""
        if self.running:
            return
        
        self.running = True
        
        # 캐시 정리 작업
        cache_cleanup_task = asyncio.create_task(self._cache_cleanup_worker())
        self.background_tasks.add(cache_cleanup_task)
        cache_cleanup_task.add_done_callback(self.background_tasks.discard)
        
        # 메트릭 업데이트 작업
        metrics_task = asyncio.create_task(self._metrics_worker())
        self.background_tasks.add(metrics_task)
        metrics_task.add_done_callback(self.background_tasks.discard)
        
        logger.info("🚀 AI 엔진 백그라운드 작업 시작")
    
    async def stop_background_tasks(self):
        """백그라운드 작업 중지"""
        self.running = False
        
        # 모든 백그라운드 작업 취소
        for task in self.background_tasks:
            task.cancel()
        
        # 작업 완료 대기
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # ThreadPool 정리
        self.executor.shutdown(wait=True)
        
        logger.info("⏹️ AI 엔진 백그라운드 작업 중지")
    
    def _generate_cache_key(self, current_game: Dict[str, Any], recent_games: List[Dict[str, Any]]) -> str:
        """캐시 키 생성"""
        # 입력 데이터를 해시로 변환
        cache_data = {
            'current_game': {
                'player_cards': current_game.get('player_cards', []),
                'banker_cards': current_game.get('banker_cards', [])
            },
            'recent_games': [
                {
                    'player_cards': g.get('player_cards', []),
                    'banker_cards': g.get('banker_cards', []),
                    'result': g.get('result', ''),
                    'has_pair': g.get('has_pair', False),
                    'pair_type': g.get('pair_type', '')
                }
                for g in recent_games[-10:]  # 최근 10게임만 사용
            ]
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 검사"""
        if cache_key not in self.cache_timestamps:
            return False
        
        cache_time = self.cache_timestamps[cache_key]
        expiry_time = cache_time + timedelta(minutes=self.cache_ttl_minutes)
        
        return datetime.now() < expiry_time
    
    async def predict_pair_async(self, current_game: Dict[str, Any], recent_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """비동기 페어 예측"""
        start_time = datetime.now()
        
        try:
            # 엔진 초기화 확인
            if self.sync_engine is None:
                await self.initialize()
            
            # 캐시 키 생성
            cache_key = self._generate_cache_key(current_game, recent_games)
            
            # 캐시 확인
            if cache_key in self.prediction_cache and self._is_cache_valid(cache_key):
                self.metrics['cache_hits'] += 1
                cached_result = self.prediction_cache[cache_key].copy()
                cached_result['cache_hit'] = True
                cached_result['prediction_time'] = 0.001  # 캐시 히트는 매우 빠름
                
                logger.info(f"💾 캐시에서 예측 반환: {cached_result['predicted_pair_type']} (신뢰도: {cached_result['confidence']:.3f})")
                return cached_result
            
            # 캐시 미스 - 실제 예측 수행
            self.metrics['cache_misses'] += 1
            
            # ThreadPool에서 동기 예측 실행
            loop = asyncio.get_event_loop()
            prediction_result = await loop.run_in_executor(
                self.executor,
                self.sync_engine.predict_pair,
                current_game,
                recent_games
            )
            
            # 예측 시간 계산
            prediction_time = (datetime.now() - start_time).total_seconds()
            prediction_result['prediction_time'] = prediction_time
            prediction_result['cache_hit'] = False
            prediction_result['cache_key'] = cache_key
            
            # 캐시에 저장
            self.prediction_cache[cache_key] = prediction_result.copy()
            self.cache_timestamps[cache_key] = datetime.now()
            
            # 캐시 크기 제한
            await self._cleanup_cache_if_needed()
            
            # 메트릭 업데이트
            self.metrics['total_predictions'] += 1
            self.metrics['prediction_times'].append(prediction_time)
            
            if self.metrics['prediction_times']:
                self.metrics['avg_prediction_time'] = sum(self.metrics['prediction_times']) / len(self.metrics['prediction_times'])
            
            logger.info(f"🔮 예측 완료: {prediction_result['predicted_pair_type']} (신뢰도: {prediction_result['confidence']:.3f}, 시간: {prediction_time:.3f}s)")
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"❌ 비동기 예측 실패: {e}")
            
            # 폴백 예측
            fallback_result = {
                'predicted_pair_type': 'NO_PAIR',
                'confidence': 0.5,
                'probabilities': {
                    'NO_PAIR': 0.5,
                    'PLAYER_PAIR': 0.16,
                    'BANKER_PAIR': 0.16,
                    'BOTH_PAIR': 0.18
                },
                'prediction_method': 'fallback',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'prediction_time': (datetime.now() - start_time).total_seconds(),
                'cache_hit': False
            }
            
            return fallback_result
    
    async def _cleanup_cache_if_needed(self):
        """캐시 크기 제한"""
        if len(self.prediction_cache) > self.cache_size:
            # 가장 오래된 항목들 제거
            sorted_items = sorted(
                self.cache_timestamps.items(),
                key=lambda x: x[1]
            )
            
            remove_count = len(self.prediction_cache) - int(self.cache_size * 0.8)
            for cache_key, _ in sorted_items[:remove_count]:
                self.prediction_cache.pop(cache_key, None)
                self.cache_timestamps.pop(cache_key, None)
    
    async def _cache_cleanup_worker(self):
        """캐시 정리 워커"""
        while self.running:
            try:
                await asyncio.sleep(300)  # 5분마다 실행
                
                now = datetime.now()
                expired_keys = []
                
                for cache_key, timestamp in self.cache_timestamps.items():
                    if (now - timestamp).total_seconds() > (self.cache_ttl_minutes * 60):
                        expired_keys.append(cache_key)
                
                # 만료된 캐시 제거
                for key in expired_keys:
                    self.prediction_cache.pop(key, None)
                    self.cache_timestamps.pop(key, None)
                
                if expired_keys:
                    logger.info(f"🗑️ 만료된 캐시 {len(expired_keys)}개 정리 완료")
                
            except Exception as e:
                logger.error(f"❌ 캐시 정리 워커 오류: {e}")
                await asyncio.sleep(60)
    
    async def _metrics_worker(self):
        """메트릭 업데이트 워커"""
        while self.running:
            try:
                await asyncio.sleep(60)  # 1분마다 실행
                
                # 동기 엔진에서 통계 가져오기
                if self.sync_engine:
                    loop = asyncio.get_event_loop()
                    sync_stats = await loop.run_in_executor(
                        self.executor,
                        self.sync_engine.get_prediction_stats
                    )
                    self.metrics['model_stats'] = sync_stats
                
            except Exception as e:
                logger.error(f"❌ 메트릭 워커 오류: {e}")
                await asyncio.sleep(30)
    
    async def train_model_async(self, games_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """비동기 모델 훈련"""
        if self.sync_engine is None:
            await self.initialize()
        
        logger.info(f"🏋️ 비동기 모델 훈련 시작: {len(games_data)}개 게임")
        
        start_time = datetime.now()
        
        try:
            # ThreadPool에서 동기 훈련 실행
            loop = asyncio.get_event_loop()
            training_result = await loop.run_in_executor(
                self.executor,
                self.sync_engine.train_model,
                games_data
            )
            
            training_time = (datetime.now() - start_time).total_seconds()
            training_result['training_time'] = training_time
            
            # 훈련 완료 후 캐시 클리어
            self.prediction_cache.clear()
            self.cache_timestamps.clear()
            
            logger.info(f"✅ 비동기 모델 훈련 완료 (시간: {training_time:.2f}s)")
            return training_result
            
        except Exception as e:
            logger.error(f"❌ 비동기 모델 훈련 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'training_time': (datetime.now() - start_time).total_seconds()
            }
    
    async def validate_prediction_async(self, game_id: int, actual_result: Dict[str, Any]):
        """비동기 예측 검증"""
        if self.sync_engine is None:
            return
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self.sync_engine.validate_prediction,
            game_id,
            actual_result
        )
        
        # 정확도 메트릭 업데이트
        if hasattr(self.sync_engine, 'accuracy_tracker'):
            self.metrics['accuracy_tracker'] = self.sync_engine.accuracy_tracker
    
    async def get_prediction_stats_async(self) -> Dict[str, Any]:
        """비동기 예측 통계"""
        stats = {
            'cache_stats': {
                'cache_size': len(self.prediction_cache),
                'cache_hits': self.metrics['cache_hits'],
                'cache_misses': self.metrics['cache_misses'],
                'cache_hit_rate': self.metrics['cache_hits'] / max(1, self.metrics['cache_hits'] + self.metrics['cache_misses']),
                'cache_ttl_minutes': self.cache_ttl_minutes
            },
            'performance_stats': {
                'total_predictions': self.metrics['total_predictions'],
                'avg_prediction_time': self.metrics['avg_prediction_time'],
                'recent_prediction_times': list(self.metrics['prediction_times'])
            },
            'accuracy_stats': self.metrics['accuracy_tracker'],
            'model_stats': self.metrics['model_stats'],
            'timestamp': datetime.now().isoformat()
        }
        
        return stats
    
    async def batch_predict_async(self, predictions_data: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        """배치 예측 (병렬 처리)"""
        if not predictions_data:
            return []
        
        logger.info(f"📊 배치 예측 시작: {len(predictions_data)}개 요청")
        
        # 병렬 예측 실행
        tasks = [
            self.predict_pair_async(current_game, recent_games)
            for current_game, recent_games in predictions_data
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ 배치 예측 {i} 실패: {result}")
                processed_results.append({
                    'predicted_pair_type': 'NO_PAIR',
                    'confidence': 0.0,
                    'error': str(result),
                    'prediction_method': 'batch_error'
                })
            else:
                processed_results.append(result)
        
        logger.info(f"✅ 배치 예측 완료: {len(processed_results)}개 결과")
        return processed_results
    
    async def preload_predictions_async(self, games_data: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]):
        """예측 결과 미리 계산 (워밍업)"""
        logger.info(f"🔥 예측 워밍업 시작: {len(games_data)}개")
        
        # 배치로 미리 계산하여 캐시에 저장
        await self.batch_predict_async(games_data)
        
        logger.info(f"✅ 예측 워밍업 완료: 캐시 크기 {len(self.prediction_cache)}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """캐시 정보"""
        return {
            'cache_size': len(self.prediction_cache),
            'cache_capacity': self.cache_size,
            'cache_hit_rate': self.metrics['cache_hits'] / max(1, self.metrics['cache_hits'] + self.metrics['cache_misses']),
            'cache_ttl_minutes': self.cache_ttl_minutes,
            'oldest_cache_age': min([
                (datetime.now() - timestamp).total_seconds() / 60
                for timestamp in self.cache_timestamps.values()
            ]) if self.cache_timestamps else 0,
            'cache_keys': list(self.prediction_cache.keys())[:10]  # 처음 10개만
        }

# 전역 비동기 AI 엔진 인스턴스
async_ai_engine: Optional[AsyncAIPredictionEngine] = None

async def get_async_ai_engine() -> AsyncAIPredictionEngine:
    """전역 비동기 AI 엔진 반환"""
    global async_ai_engine
    if async_ai_engine is None:
        async_ai_engine = AsyncAIPredictionEngine()
        await async_ai_engine.initialize()
    return async_ai_engine