#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
실시간 AI 통합 시스템
딥러닝 예측과 실시간 패킷 데이터 연결
"""

import asyncio
import json
import logging
import threading
import time
from collections import deque, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
import numpy as np
from queue import Queue, Empty

from enhanced_packet_decoder import EnhancedPacketDecoder, BaccaratGameData
from ipc_communication import IntegratedIPCManager, IPCMessage
import uuid

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AI 라이브러리 로딩
try:
    import tensorflow as tf
    from sklearn.preprocessing import StandardScaler
    AI_AVAILABLE = True
    logger.info("✅ AI 라이브러리 사용 가능")
except ImportError:
    AI_AVAILABLE = False
    logger.warning("⚠️ AI 라이브러리 없음 - 통계적 예측 사용")


@dataclass
class PredictionResult:
    """예측 결과 구조체"""
    prediction_id: str
    table_id: str
    game_count: int
    timestamp: float
    
    # 페어 예측 결과
    player_pair_probability: float
    banker_pair_probability: float
    any_pair_probability: float
    
    # 승부 예측 결과
    player_win_probability: float
    banker_win_probability: float
    tie_probability: float
    
    # 신뢰도
    confidence_score: float
    model_type: str
    
    # 추가 정보
    pattern_strength: float
    historical_accuracy: float
    sample_size: int


@dataclass
class GamePattern:
    """게임 패턴 분석 결과"""
    pattern_id: str
    pattern_type: str  # 'streak', 'alternating', 'random'
    strength: float
    confidence: float
    last_games: List[str]
    trend_direction: str  # 'up', 'down', 'stable'


class FeatureExtractor:
    """실시간 특성 추출기"""
    
    def __init__(self):
        self.card_values = {
            'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
            '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13
        }
        self.suits = {'♠': 0, '♥': 1, '♦': 2, '♣': 3, 'H': 1, 'D': 2, 'C': 3, 'S': 0}
    
    def extract_features(self, game_data: BaccaratGameData, history: List[BaccaratGameData]) -> np.ndarray:
        """게임 데이터에서 특성 추출"""
        features = []
        
        try:
            # 1. 기본 게임 정보
            features.extend([
                game_data.player_score / 9.0,  # 정규화
                game_data.banker_score / 9.0,
                float(game_data.natural),
                float(game_data.player_pair),
                float(game_data.banker_pair)
            ])
            
            # 2. 카드 정보 (있는 경우)
            player_card_features = self._extract_card_features(game_data.player_cards)
            banker_card_features = self._extract_card_features(game_data.banker_cards)
            features.extend(player_card_features)
            features.extend(banker_card_features)
            
            # 3. 히스토리 패턴 (최근 10게임)
            history_features = self._extract_history_features(history[-10:])
            features.extend(history_features)
            
            # 4. 시간 패턴
            time_features = self._extract_time_features(game_data)
            features.extend(time_features)
            
            return np.array(features, dtype=np.float32)
        
        except Exception as e:
            logger.error(f"특성 추출 오류: {e}")
            # 기본 특성 반환 (44개 특성)
            return np.zeros(44, dtype=np.float32)
    
    def _extract_card_features(self, cards: List[str]) -> List[float]:
        """카드 특성 추출 (8개 특성)"""
        features = []
        
        # 최대 2장의 카드 처리
        for i in range(2):
            if i < len(cards) and len(cards[i]) >= 2:
                card = cards[i]
                value = self._get_card_value(card[:-1])
                suit = self.suits.get(card[-1], 0)
                
                features.extend([value / 13.0, suit / 3.0])  # 정규화
            else:
                features.extend([0.0, 0.0])  # 패딩
        
        # 카드 간 관계 (4개 특성)
        if len(cards) >= 2:
            card1_val = self._get_card_value(cards[0][:-1]) if len(cards[0]) >= 2 else 0
            card2_val = self._get_card_value(cards[1][:-1]) if len(cards[1]) >= 2 else 0
            
            features.extend([
                float(card1_val == card2_val),  # 같은 값
                abs(card1_val - card2_val) / 12.0,  # 값 차이
                float(cards[0][-1] == cards[1][-1]) if len(cards[0]) >= 2 and len(cards[1]) >= 2 else 0,  # 같은 슈트
                (card1_val + card2_val) % 10 / 9.0  # 바카라 합계
            ])
        else:
            features.extend([0.0, 0.0, 0.0, 0.0])
        
        return features
    
    def _get_card_value(self, card_str: str) -> int:
        """카드 값 가져오기"""
        return self.card_values.get(card_str, 0)
    
    def _extract_history_features(self, history: List[BaccaratGameData]) -> List[float]:
        """히스토리 패턴 특성 (20개 특성)"""
        if not history:
            return [0.0] * 20
        
        features = []
        
        # 승부 패턴
        wins = [game.winner for game in history]
        player_wins = wins.count('Player') / len(wins) if wins else 0
        banker_wins = wins.count('Banker') / len(wins) if wins else 0
        ties = wins.count('Tie') / len(wins) if wins else 0
        
        features.extend([player_wins, banker_wins, ties])
        
        # 페어 패턴
        player_pairs = sum(1 for game in history if game.player_pair) / len(history)
        banker_pairs = sum(1 for game in history if game.banker_pair) / len(history)
        any_pairs = sum(1 for game in history if game.player_pair or game.banker_pair) / len(history)
        
        features.extend([player_pairs, banker_pairs, any_pairs])
        
        # 연속 패턴
        if len(wins) >= 2:
            streaks = self._calculate_streaks(wins)
            features.extend([
                streaks['max_player'] / 10.0,
                streaks['max_banker'] / 10.0,
                streaks['current'] / 10.0,
                float(streaks['alternating'])
            ])
        else:
            features.extend([0.0, 0.0, 0.0, 0.0])
        
        # 점수 패턴 (최근 5게임)
        recent_games = history[-5:]
        if recent_games:
            avg_player_score = sum(game.player_score for game in recent_games) / len(recent_games) / 9.0
            avg_banker_score = sum(game.banker_score for game in recent_games) / len(recent_games) / 9.0
            naturals_rate = sum(1 for game in recent_games if game.natural) / len(recent_games)
            
            features.extend([avg_player_score, avg_banker_score, naturals_rate])
        else:
            features.extend([0.0, 0.0, 0.0])
        
        # 추가 패턴 특성 (패딩으로 20개 맞추기)
        while len(features) < 20:
            features.append(0.0)
        
        return features[:20]
    
    def _calculate_streaks(self, wins: List[str]) -> Dict[str, Any]:
        """연속 패턴 계산"""
        if not wins:
            return {'max_player': 0, 'max_banker': 0, 'current': 0, 'alternating': False}
        
        max_player, max_banker = 0, 0
        current_streak = 1
        current_type = wins[0]
        
        # 연속 패턴 분석
        for i in range(1, len(wins)):
            if wins[i] == current_type and wins[i] != 'Tie':
                current_streak += 1
            else:
                if current_type == 'Player':
                    max_player = max(max_player, current_streak)
                elif current_type == 'Banker':
                    max_banker = max(max_banker, current_streak)
                
                current_streak = 1
                current_type = wins[i]
        
        # 마지막 연속 처리
        if current_type == 'Player':
            max_player = max(max_player, current_streak)
        elif current_type == 'Banker':
            max_banker = max(max_banker, current_streak)
        
        # 교대 패턴 감지
        alternating = True
        if len(wins) >= 4:
            for i in range(len(wins) - 1):
                if wins[i] == wins[i + 1] and wins[i] != 'Tie':
                    alternating = False
                    break
        
        return {
            'max_player': max_player,
            'max_banker': max_banker,
            'current': current_streak if current_type in ['Player', 'Banker'] else 0,
            'alternating': alternating
        }
    
    def _extract_time_features(self, game_data: BaccaratGameData) -> List[float]:
        """시간 기반 특성 (1개 특성)"""
        # 시간 기반 특성 (시간대별 패턴 등)
        game_time = datetime.fromtimestamp(game_data.timestamp)
        hour_normalized = game_time.hour / 23.0  # 시간 정규화
        
        return [hour_normalized]


class StatisticalPredictor:
    """통계적 예측 모델 (AI 라이브러리 없을 때 사용)"""
    
    def __init__(self):
        self.history_window = 50
        self.pattern_weights = {
            'streak': 0.3,
            'alternating': 0.2,
            'frequency': 0.3,
            'recent': 0.2
        }
    
    def predict(self, game_history: List[BaccaratGameData], table_id: str) -> PredictionResult:
        """통계적 예측 수행"""
        try:
            if not game_history:
                return self._default_prediction(table_id)
            
            recent_history = game_history[-self.history_window:]
            
            # 페어 확률 계산
            pair_probs = self._calculate_pair_probabilities(recent_history)
            
            # 승부 확률 계산
            win_probs = self._calculate_win_probabilities(recent_history)
            
            # 패턴 강도 계산
            pattern_strength = self._calculate_pattern_strength(recent_history)
            
            return PredictionResult(
                prediction_id=uuid.uuid4().hex,
                table_id=table_id,
                game_count=len(game_history),
                timestamp=time.time(),
                
                player_pair_probability=pair_probs['player'],
                banker_pair_probability=pair_probs['banker'],
                any_pair_probability=pair_probs['any'],
                
                player_win_probability=win_probs['player'],
                banker_win_probability=win_probs['banker'],
                tie_probability=win_probs['tie'],
                
                confidence_score=min(len(recent_history) / self.history_window, 1.0),
                model_type='statistical',
                pattern_strength=pattern_strength,
                historical_accuracy=0.85,  # 기본값
                sample_size=len(recent_history)
            )
        
        except Exception as e:
            logger.error(f"통계적 예측 오류: {e}")
            return self._default_prediction(table_id)
    
    def _calculate_pair_probabilities(self, history: List[BaccaratGameData]) -> Dict[str, float]:
        """페어 확률 계산"""
        if not history:
            return {'player': 0.08, 'banker': 0.08, 'any': 0.15}  # 기본 확률
        
        player_pairs = sum(1 for game in history if game.player_pair)
        banker_pairs = sum(1 for game in history if game.banker_pair)
        any_pairs = sum(1 for game in history if game.player_pair or game.banker_pair)
        
        total = len(history)
        
        # 최근 게임에 가중치 부여
        recent_weight = 0.3
        if len(history) >= 10:
            recent_games = history[-10:]
            recent_player_pairs = sum(1 for game in recent_games if game.player_pair)
            recent_banker_pairs = sum(1 for game in recent_games if game.banker_pair)
            recent_any_pairs = sum(1 for game in recent_games if game.player_pair or game.banker_pair)
            
            player_prob = (player_pairs / total) * (1 - recent_weight) + (recent_player_pairs / 10) * recent_weight
            banker_prob = (banker_pairs / total) * (1 - recent_weight) + (recent_banker_pairs / 10) * recent_weight
            any_prob = (any_pairs / total) * (1 - recent_weight) + (recent_any_pairs / 10) * recent_weight
        else:
            player_prob = player_pairs / total
            banker_prob = banker_pairs / total
            any_prob = any_pairs / total
        
        return {
            'player': max(0.01, min(0.5, player_prob)),
            'banker': max(0.01, min(0.5, banker_prob)),
            'any': max(0.02, min(0.7, any_prob))
        }
    
    def _calculate_win_probabilities(self, history: List[BaccaratGameData]) -> Dict[str, float]:
        """승부 확률 계산"""
        if not history:
            return {'player': 0.45, 'banker': 0.46, 'tie': 0.09}  # 기본 확률
        
        wins = [game.winner for game in history]
        player_wins = wins.count('Player')
        banker_wins = wins.count('Banker')
        ties = wins.count('Tie')
        
        total = len(wins)
        
        return {
            'player': player_wins / total,
            'banker': banker_wins / total,
            'tie': ties / total
        }
    
    def _calculate_pattern_strength(self, history: List[BaccaratGameData]) -> float:
        """패턴 강도 계산"""
        if len(history) < 5:
            return 0.5
        
        wins = [game.winner for game in history if game.winner != 'Tie']
        if len(wins) < 3:
            return 0.5
        
        # 연속성 점수
        consecutive_count = 0
        for i in range(len(wins) - 1):
            if wins[i] == wins[i + 1]:
                consecutive_count += 1
        
        consecutiveness = consecutive_count / (len(wins) - 1)
        
        # 교대성 점수
        alternating_count = 0
        for i in range(len(wins) - 1):
            if wins[i] != wins[i + 1]:
                alternating_count += 1
        
        alternation = alternating_count / (len(wins) - 1)
        
        # 패턴 강도 = 연속성과 교대성 중 높은 값
        pattern_strength = max(consecutiveness, alternation)
        
        return max(0.1, min(0.9, pattern_strength))
    
    def _default_prediction(self, table_id: str) -> PredictionResult:
        """기본 예측 결과"""
        return PredictionResult(
            prediction_id=uuid.uuid4().hex,
            table_id=table_id,
            game_count=0,
            timestamp=time.time(),
            
            player_pair_probability=0.08,
            banker_pair_probability=0.08,
            any_pair_probability=0.15,
            
            player_win_probability=0.45,
            banker_win_probability=0.46,
            tie_probability=0.09,
            
            confidence_score=0.5,
            model_type='default',
            pattern_strength=0.5,
            historical_accuracy=0.5,
            sample_size=0
        )


class RealTimeAIEngine:
    """실시간 AI 예측 엔진"""
    
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.statistical_predictor = StatisticalPredictor()
        
        # 게임 히스토리 저장 (테이블별)
        self.game_histories = defaultdict(deque)
        self.max_history_size = 1000
        
        # 예측 결과 캐시
        self.prediction_cache = {}
        self.cache_ttl = 300  # 5분
        
        # 통계 정보
        self.stats = {
            'total_predictions': 0,
            'cache_hits': 0,
            'prediction_times': deque(maxlen=100)
        }
        
        # AI 모델 (있는 경우)
        self.ai_model = None
        self.scaler = None
        
        if AI_AVAILABLE:
            self._initialize_ai_model()
        
        logger.info("실시간 AI 엔진 초기화 완료")
    
    def _initialize_ai_model(self):
        """AI 모델 초기화"""
        try:
            # 사전 훈련된 모델 로드 시도
            model_path = Path("models/baccarat_prediction_model.h5")
            if model_path.exists():
                self.ai_model = tf.keras.models.load_model(str(model_path))
                logger.info("✅ AI 모델 로드 완료")
            else:
                logger.info("사전 훈련된 모델이 없습니다. 통계적 모델 사용")
        
        except Exception as e:
            logger.error(f"AI 모델 초기화 실패: {e}")
    
    def add_game_data(self, game_data: BaccaratGameData):
        """새 게임 데이터 추가"""
        table_id = game_data.table_id
        
        # 히스토리에 추가
        self.game_histories[table_id].append(game_data)
        
        # 최대 크기 유지
        if len(self.game_histories[table_id]) > self.max_history_size:
            self.game_histories[table_id].popleft()
        
        # 캐시 무효화
        cache_key = f"{table_id}_prediction"
        if cache_key in self.prediction_cache:
            del self.prediction_cache[cache_key]
    
    def predict(self, table_id: str, force_refresh: bool = False) -> Optional[PredictionResult]:
        """예측 수행"""
        start_time = time.time()
        
        try:
            # 캐시 확인
            cache_key = f"{table_id}_prediction"
            if not force_refresh and cache_key in self.prediction_cache:
                cached_result, cache_time = self.prediction_cache[cache_key]
                if time.time() - cache_time < self.cache_ttl:
                    self.stats['cache_hits'] += 1
                    return cached_result
            
            # 게임 히스토리 가져오기
            history = list(self.game_histories.get(table_id, []))
            
            if not history:
                logger.warning(f"테이블 {table_id}의 히스토리가 없습니다")
                return None
            
            # 예측 수행
            if self.ai_model and AI_AVAILABLE:
                prediction = self._ai_predict(history, table_id)
            else:
                prediction = self.statistical_predictor.predict(history, table_id)
            
            # 캐시에 저장
            self.prediction_cache[cache_key] = (prediction, time.time())
            
            # 통계 업데이트
            self.stats['total_predictions'] += 1
            self.stats['prediction_times'].append(time.time() - start_time)
            
            logger.debug(f"예측 완료: {table_id} (소요시간: {time.time() - start_time:.3f}초)")
            return prediction
        
        except Exception as e:
            logger.error(f"예측 수행 오류 {table_id}: {e}")
            return None
    
    def _ai_predict(self, history: List[BaccaratGameData], table_id: str) -> PredictionResult:
        """AI 모델 예측"""
        try:
            # 특성 추출 (최신 게임 기준)
            latest_game = history[-1]
            features = self.feature_extractor.extract_features(latest_game, history[:-1])
            
            # 모델 예측
            features_reshaped = features.reshape(1, -1)
            if self.scaler:
                features_reshaped = self.scaler.transform(features_reshaped)
            
            predictions = self.ai_model.predict(features_reshaped, verbose=0)[0]
            
            # 예측 결과 해석 (모델 구조에 따라 조정 필요)
            return PredictionResult(
                prediction_id=uuid.uuid4().hex,
                table_id=table_id,
                game_count=len(history),
                timestamp=time.time(),
                
                player_pair_probability=float(predictions[0]) if len(predictions) > 0 else 0.08,
                banker_pair_probability=float(predictions[1]) if len(predictions) > 1 else 0.08,
                any_pair_probability=float(predictions[2]) if len(predictions) > 2 else 0.15,
                
                player_win_probability=float(predictions[3]) if len(predictions) > 3 else 0.45,
                banker_win_probability=float(predictions[4]) if len(predictions) > 4 else 0.46,
                tie_probability=float(predictions[5]) if len(predictions) > 5 else 0.09,
                
                confidence_score=min(len(history) / 100, 1.0),
                model_type='neural_network',
                pattern_strength=self.statistical_predictor._calculate_pattern_strength(history),
                historical_accuracy=0.9,  # 실제 정확도로 교체 필요
                sample_size=len(history)
            )
        
        except Exception as e:
            logger.error(f"AI 예측 오류: {e}")
            return self.statistical_predictor.predict(history, table_id)
    
    def get_table_analysis(self, table_id: str) -> Dict[str, Any]:
        """테이블 분석 정보 반환"""
        history = list(self.game_histories.get(table_id, []))
        
        if not history:
            return {'error': 'No data available'}
        
        # 기본 통계
        wins = [game.winner for game in history]
        player_wins = wins.count('Player')
        banker_wins = wins.count('Banker')
        ties = wins.count('Tie')
        
        # 페어 통계
        player_pairs = sum(1 for game in history if game.player_pair)
        banker_pairs = sum(1 for game in history if game.banker_pair)
        
        return {
            'table_id': table_id,
            'total_games': len(history),
            'player_wins': player_wins,
            'banker_wins': banker_wins,
            'ties': ties,
            'player_pairs': player_pairs,
            'banker_pairs': banker_pairs,
            'win_rates': {
                'player': player_wins / len(history) if history else 0,
                'banker': banker_wins / len(history) if history else 0,
                'tie': ties / len(history) if history else 0
            },
            'pair_rates': {
                'player': player_pairs / len(history) if history else 0,
                'banker': banker_pairs / len(history) if history else 0
            },
            'last_update': history[-1].timestamp if history else None
        }
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """엔진 통계 반환"""
        avg_prediction_time = (
            sum(self.stats['prediction_times']) / len(self.stats['prediction_times'])
            if self.stats['prediction_times'] else 0
        )
        
        return {
            'total_predictions': self.stats['total_predictions'],
            'cache_hits': self.stats['cache_hits'],
            'cache_hit_rate': (
                self.stats['cache_hits'] / self.stats['total_predictions']
                if self.stats['total_predictions'] > 0 else 0
            ),
            'avg_prediction_time_ms': avg_prediction_time * 1000,
            'active_tables': len(self.game_histories),
            'total_games_tracked': sum(len(history) for history in self.game_histories.values()),
            'ai_model_available': self.ai_model is not None,
            'cache_size': len(self.prediction_cache)
        }


class RealtimeAIIntegrator:
    """실시간 AI 통합 관리자"""
    
    def __init__(self):
        self.ai_engine = RealTimeAIEngine()
        self.packet_decoder = EnhancedPacketDecoder()
        self.ipc_manager = None
        
        # 콜백 및 이벤트
        self.prediction_callbacks = []
        
        # 처리 큐
        self.processing_queue = Queue()
        self.is_running = False
        self.worker_thread = None
        
        logger.info("실시간 AI 통합 시스템 초기화 완료")
    
    def add_prediction_callback(self, callback: Callable[[PredictionResult], None]):
        """예측 결과 콜백 등록"""
        self.prediction_callbacks.append(callback)
    
    def start(self, ipc_manager: IntegratedIPCManager = None) -> bool:
        """통합 시스템 시작"""
        try:
            self.ipc_manager = ipc_manager
            
            # 워커 스레드 시작
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            
            logger.info("✅ 실시간 AI 통합 시스템 시작됨")
            return True
        
        except Exception as e:
            logger.error(f"AI 통합 시스템 시작 실패: {e}")
            return False
    
    def stop(self):
        """통합 시스템 중지"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        logger.info("실시간 AI 통합 시스템 중지됨")
    
    def process_packet_data(self, event_type: str, data: Dict[str, Any]):
        """패킷 데이터 처리"""
        if event_type == 'packet_data':
            self.processing_queue.put({
                'type': 'packet_data',
                'data': data,
                'timestamp': time.time()
            })
    
    def _worker_loop(self):
        """워커 스레드 메인 루프"""
        logger.info("AI 워커 스레드 시작됨")
        
        while self.is_running:
            try:
                # 큐에서 작업 가져오기
                item = self.processing_queue.get(timeout=1.0)
                
                if item['type'] == 'packet_data':
                    self._process_packet_item(item)
                
                self.processing_queue.task_done()
            
            except Empty:
                continue
            except Exception as e:
                logger.error(f"워커 루프 오류: {e}")
    
    def _process_packet_item(self, item: Dict[str, Any]):
        """패킷 아이템 처리"""
        try:
            packet_data = item['data']
            decoded_games = packet_data.get('decoded_data', [])
            
            for game_data in decoded_games:
                # BaccaratGameData 객체로 변환
                if isinstance(game_data, dict):
                    baccarat_game = self._dict_to_game_data(game_data)
                else:
                    baccarat_game = game_data
                
                # AI 엔진에 데이터 추가
                self.ai_engine.add_game_data(baccarat_game)
                
                # 예측 수행
                prediction = self.ai_engine.predict(baccarat_game.table_id)
                
                if prediction:
                    # 콜백 호출
                    for callback in self.prediction_callbacks:
                        try:
                            callback(prediction)
                        except Exception as e:
                            logger.error(f"예측 콜백 오류: {e}")
                    
                    # IPC로 예측 결과 브로드캐스트
                    if self.ipc_manager:
                        self.ipc_manager.broadcast_message(
                            'ai_prediction',
                            asdict(prediction)
                        )
        
        except Exception as e:
            logger.error(f"패킷 아이템 처리 오류: {e}")
    
    def _dict_to_game_data(self, game_dict: Dict[str, Any]) -> BaccaratGameData:
        """딕셔너리를 BaccaratGameData로 변환"""
        from enhanced_packet_decoder import BaccaratGameData
        
        return BaccaratGameData(
            game_id=game_dict.get('game_id', 'unknown'),
            table_id=game_dict.get('table_id', 'unknown'),
            game_count=game_dict.get('game_count', 0),
            timestamp=game_dict.get('timestamp', time.time()),
            iso_timestamp=game_dict.get('iso_timestamp', datetime.now().isoformat()),
            player_score=game_dict.get('player_score', 0),
            banker_score=game_dict.get('banker_score', 0),
            winner=game_dict.get('winner', 'Unknown'),
            natural=game_dict.get('natural', False),
            player_pair=game_dict.get('player_pair', False),
            banker_pair=game_dict.get('banker_pair', False),
            player_cards=game_dict.get('player_cards', []),
            banker_cards=game_dict.get('banker_cards', []),
            source_file=game_dict.get('source_file', '')
        )
    
    def get_prediction(self, table_id: str) -> Optional[PredictionResult]:
        """특정 테이블의 예측 결과 반환"""
        return self.ai_engine.predict(table_id)
    
    def get_table_analysis(self, table_id: str) -> Dict[str, Any]:
        """테이블 분석 정보 반환"""
        return self.ai_engine.get_table_analysis(table_id)
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 반환"""
        return {
            'ai_engine_stats': self.ai_engine.get_engine_stats(),
            'processing_queue_size': self.processing_queue.qsize(),
            'is_running': self.is_running,
            'callback_count': len(self.prediction_callbacks)
        }


# 샘플 예측 콜백
def log_prediction_callback(prediction: PredictionResult):
    """예측 결과 로깅 콜백"""
    logger.info(f"🎯 예측 결과 - 테이블 {prediction.table_id}: "
                f"페어확률 P:{prediction.player_pair_probability:.2f} "
                f"B:{prediction.banker_pair_probability:.2f} "
                f"(신뢰도: {prediction.confidence_score:.2f})")


# 사용 예제
if __name__ == "__main__":
    # AI 통합 시스템 테스트
    integrator = RealtimeAIIntegrator()
    integrator.add_prediction_callback(log_prediction_callback)
    
    try:
        if integrator.start():
            logger.info("AI 통합 시스템이 시작되었습니다")
            
            # 테스트용 샘플 데이터
            sample_game = BaccaratGameData(
                game_id="test_1",
                table_id="table_A",
                game_count=1,
                timestamp=time.time(),
                iso_timestamp=datetime.now().isoformat(),
                player_score=7,
                banker_score=5,
                winner="Player",
                player_pair=True,
                banker_pair=False,
                player_cards=['AH', 'KS'],
                banker_cards=['5D', 'QC']
            )
            
            # AI 엔진에 데이터 추가 및 예측
            integrator.ai_engine.add_game_data(sample_game)
            prediction = integrator.get_prediction("table_A")
            
            if prediction:
                logger.info(f"테스트 예측 완료: {prediction.model_type}")
            
            time.sleep(5)
        else:
            logger.error("AI 통합 시스템 시작 실패")
    
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    finally:
        integrator.stop()