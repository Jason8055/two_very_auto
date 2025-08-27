#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Pattern Analysis Module v2.0
머신러닝 기반 고급 패턴 분석 및 예측 엔진
"""

import json
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import deque, Counter, defaultdict
import statistics
from dataclasses import dataclass

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PatternPrediction:
    """패턴 예측 결과"""
    pair_probability: float
    confidence: float
    expected_games_to_pair: int
    pattern_strength: float
    recommendation: str


class PatternAnalyzerV2:
    """머신러닝 기반 고급 패턴 분석 엔진 v2.0"""
    
    def __init__(self, database_manager=None):
        """패턴 분석기 v2.0 초기화"""
        self.db = database_manager
        self.pattern_cache = {}
        self.pattern_history = deque(maxlen=2000)  # 히스토리 확대
        self.ml_features_cache = {}
        
        # 패턴 가중치 설정
        self.weights = {
            'streak_weight': 0.25,
            'frequency_weight': 0.20,
            'time_weight': 0.15,
            'hot_cold_weight': 0.20,
            'ml_weight': 0.20
        }
        
        logger.info("[Pattern Analyzer v2.0] Initialized with ML capabilities")
    
    def analyze_comprehensive_patterns(self, table_name: str, 
                                     recent_games: List[Dict] = None, 
                                     games_limit: int = 200) -> Dict[str, Any]:
        """
        종합적인 패턴 분석 (v2.0 - ML 포함)
        
        Args:
            table_name: 테이블명
            recent_games: 최근 게임 데이터 (없으면 DB에서 조회)
            games_limit: 분석할 게임 수 제한
            
        Returns:
            종합 패턴 분석 결과
        """
        try:
            # 게임 데이터 준비
            if recent_games is None and self.db:
                recent_games = self.db.get_games(table_name=table_name, limit=games_limit)
            elif recent_games is None:
                return self._empty_pattern_result(table_name)
            
            if not recent_games:
                return self._empty_pattern_result(table_name)
            
            # 기본 패턴 분석
            base_patterns = self._analyze_base_patterns(recent_games)
            
            # 머신러닝 기반 고급 분석
            ml_analysis = self._analyze_ml_patterns(recent_games)
            
            # 시계열 분석
            temporal_patterns = self._analyze_temporal_patterns(recent_games)
            
            # 카드 기반 패턴
            card_patterns = self._analyze_card_patterns(recent_games)
            
            # 예측 모델
            prediction = self._generate_prediction(recent_games)
            
            # 종합 점수 계산
            pattern_score = self._calculate_pattern_score(
                base_patterns, ml_analysis, temporal_patterns, card_patterns
            )
            
            analysis_result = {
                'table_name': table_name,
                'analyzed_games': len(recent_games),
                'analysis_timestamp': datetime.now().isoformat(),
                'pattern_score': pattern_score,
                'base_patterns': base_patterns,
                'ml_analysis': ml_analysis,
                'temporal_patterns': temporal_patterns,
                'card_patterns': card_patterns,
                'prediction': {
                    'pair_probability': prediction.pair_probability,
                    'confidence': prediction.confidence,
                    'expected_games_to_pair': prediction.expected_games_to_pair,
                    'pattern_strength': prediction.pattern_strength,
                    'recommendation': prediction.recommendation
                },
                'insights': self._generate_insights(recent_games, prediction),
                'alerts': self._generate_pattern_alerts(recent_games, prediction)
            }
            
            # 캐시 및 히스토리 업데이트
            self.pattern_cache[table_name] = analysis_result
            self.pattern_history.append({
                'table_name': table_name,
                'timestamp': datetime.now(),
                'pattern_score': pattern_score,
                'prediction': prediction
            })
            
            # 데이터베이스에 분석 결과 저장
            if self.db:
                self.db.save_pattern_analysis(table_name, 'comprehensive', analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Comprehensive pattern analysis failed for {table_name}: {e}")
            return self._empty_pattern_result(table_name)
    
    def _analyze_base_patterns(self, games: List[Dict]) -> Dict[str, Any]:
        """기본 패턴 분석"""
        return {
            'streak_analysis': self._analyze_advanced_streaks(games),
            'pair_frequency': self._analyze_pair_frequency_v2(games),
            'hot_cold_periods': self._analyze_hot_cold_v2(games),
            'cyclical_patterns': self._analyze_cyclical_patterns(games)
        }
    
    def _analyze_advanced_streaks(self, games: List[Dict]) -> Dict[str, Any]:
        """고급 스트릭 분석"""
        streak_data = {
            'no_pair_streaks': {
                'current': 0,
                'longest': 0,
                'average': 0.0,
                'distribution': {},
                'trend': 'stable'
            },
            'pair_streaks': {
                'consecutive_pairs': 0,
                'pair_clusters': [],
                'cluster_frequency': 0.0
            },
            'result_patterns': {
                'PLAYER': {'streak': 0, 'max_streak': 0, 'frequency': 0.0},
                'BANKER': {'streak': 0, 'max_streak': 0, 'frequency': 0.0},
                'TIE': {'streak': 0, 'max_streak': 0, 'frequency': 0.0}
            },
            'pattern_strength': 0.0
        }
        
        if not games:
            return streak_data
        
        # 페어 없는 스트릭 상세 분석
        no_pair_streaks = []
        current_no_pair = 0
        pair_positions = []
        
        for i, game in enumerate(reversed(games)):
            has_pair = game.get('pair_info', {}).get('has_any_pair', False)
            
            if has_pair:
                pair_positions.append(i)
                if current_no_pair > 0:
                    no_pair_streaks.append(current_no_pair)
                    current_no_pair = 0
            else:
                current_no_pair += 1
        
        if current_no_pair > 0:
            no_pair_streaks.append(current_no_pair)
        
        # 스트릭 통계
        streak_data['no_pair_streaks']['current'] = current_no_pair
        streak_data['no_pair_streaks']['longest'] = max(no_pair_streaks) if no_pair_streaks else 0
        streak_data['no_pair_streaks']['average'] = statistics.mean(no_pair_streaks) if no_pair_streaks else 0.0
        
        # 스트릭 분포 분석
        streak_counts = Counter(no_pair_streaks)
        total_streaks = len(no_pair_streaks)
        streak_data['no_pair_streaks']['distribution'] = {
            str(k): v / total_streaks for k, v in streak_counts.items()
        } if total_streaks > 0 else {}
        
        # 트렌드 분석
        if len(no_pair_streaks) >= 5:
            recent_avg = statistics.mean(no_pair_streaks[-5:])
            overall_avg = statistics.mean(no_pair_streaks)
            
            if recent_avg > overall_avg * 1.2:
                streak_data['no_pair_streaks']['trend'] = 'increasing'
            elif recent_avg < overall_avg * 0.8:
                streak_data['no_pair_streaks']['trend'] = 'decreasing'
            else:
                streak_data['no_pair_streaks']['trend'] = 'stable'
        
        # 페어 클러스터 분석
        if pair_positions:
            clusters = self._find_pair_clusters(pair_positions)
            streak_data['pair_streaks']['pair_clusters'] = clusters
            streak_data['pair_streaks']['cluster_frequency'] = len(clusters) / len(games) * 100
        
        # 결과 패턴 분석
        result_counts = Counter(game.get('result', 'UNKNOWN') for game in games)
        total_games = len(games)
        
        for result in ['PLAYER', 'BANKER', 'TIE']:
            count = result_counts.get(result, 0)
            streak_data['result_patterns'][result]['frequency'] = count / total_games if total_games > 0 else 0.0
        
        # 패턴 강도 계산
        streak_data['pattern_strength'] = self._calculate_streak_pattern_strength(
            no_pair_streaks, pair_positions, len(games)
        )
        
        return streak_data
    
    def _analyze_pair_frequency_v2(self, games: List[Dict]) -> Dict[str, Any]:
        """페어 빈도 고급 분석"""
        frequency_data = {
            'overall_frequency': 0.0,
            'type_frequencies': {
                'PLAYER_PAIR': 0.0,
                'BANKER_PAIR': 0.0,
                'BOTH_PAIR': 0.0
            },
            'frequency_trend': 'stable',
            'recent_vs_historical': 0.0,
            'frequency_variance': 0.0,
            'optimal_frequency': 0.118  # 바카라 이론상 페어 확률
        }
        
        if not games:
            return frequency_data
        
        total_games = len(games)
        
        # 전체 페어 빈도
        pair_games = [g for g in games if g.get('pair_info', {}).get('has_any_pair', False)]
        frequency_data['overall_frequency'] = len(pair_games) / total_games
        
        # 타입별 빈도
        for game in pair_games:
            pair_type = game.get('pair_info', {}).get('pair_type', '')
            if pair_type in frequency_data['type_frequencies']:
                frequency_data['type_frequencies'][pair_type] += 1 / total_games
        
        # 시간대별 빈도 변화 분석
        if total_games >= 20:
            mid_point = total_games // 2
            recent_games = games[:mid_point]
            historical_games = games[mid_point:]
            
            recent_frequency = len([g for g in recent_games 
                                  if g.get('pair_info', {}).get('has_any_pair', False)]) / len(recent_games)
            historical_frequency = len([g for g in historical_games 
                                      if g.get('pair_info', {}).get('has_any_pair', False)]) / len(historical_games)
            
            frequency_data['recent_vs_historical'] = (recent_frequency - historical_frequency) / historical_frequency if historical_frequency > 0 else 0.0
            
            # 트렌드 분석
            if recent_frequency > historical_frequency * 1.2:
                frequency_data['frequency_trend'] = 'increasing'
            elif recent_frequency < historical_frequency * 0.8:
                frequency_data['frequency_trend'] = 'decreasing'
        
        # 빈도 분산 계산 (안정성 측정)
        if total_games >= 10:
            window_size = min(10, total_games // 5)
            window_frequencies = []
            
            for i in range(0, total_games - window_size + 1, window_size):
                window_games = games[i:i + window_size]
                window_pairs = len([g for g in window_games if g.get('pair_info', {}).get('has_any_pair', False)])
                window_frequencies.append(window_pairs / window_size)
            
            if len(window_frequencies) > 1:
                frequency_data['frequency_variance'] = statistics.variance(window_frequencies)
        
        return frequency_data
    
    def _analyze_hot_cold_v2(self, games: List[Dict]) -> Dict[str, Any]:
        """핫/콜드 주기 고급 분석"""
        hot_cold_data = {
            'current_phase': 'normal',
            'phase_duration': 0,
            'hot_periods': [],
            'cold_periods': [],
            'cycle_analysis': {
                'average_hot_duration': 0.0,
                'average_cold_duration': 0.0,
                'cycle_predictability': 0.0
            },
            'temperature_score': 0.0  # -100(매우 차가움) ~ +100(매우 뜨거움)
        }
        
        if len(games) < 20:
            return hot_cold_data
        
        # 온도 점수 계산을 위한 윈도우 분석
        window_size = min(20, len(games) // 5)
        window_frequencies = []
        
        for i in range(0, len(games) - window_size + 1, window_size // 2):
            window_games = games[i:i + window_size]
            window_pairs = len([g for g in window_games if g.get('pair_info', {}).get('has_any_pair', False)])
            window_frequencies.append(window_pairs / window_size)
        
        if not window_frequencies:
            return hot_cold_data
        
        # 기준 빈도 (이론적 페어 확률)
        baseline_frequency = 0.118
        
        # 핫/콜드 주기 식별
        hot_threshold = baseline_frequency * 1.5
        cold_threshold = baseline_frequency * 0.5
        
        current_phase = 'normal'
        phase_start = 0
        hot_periods = []
        cold_periods = []
        
        for i, freq in enumerate(window_frequencies):
            if freq > hot_threshold and current_phase != 'hot':
                if current_phase == 'cold':
                    cold_periods.append({'start': phase_start, 'end': i, 'duration': i - phase_start})
                current_phase = 'hot'
                phase_start = i
            elif freq < cold_threshold and current_phase != 'cold':
                if current_phase == 'hot':
                    hot_periods.append({'start': phase_start, 'end': i, 'duration': i - phase_start})
                current_phase = 'cold'
                phase_start = i
            elif cold_threshold <= freq <= hot_threshold and current_phase != 'normal':
                if current_phase == 'hot':
                    hot_periods.append({'start': phase_start, 'end': i, 'duration': i - phase_start})
                elif current_phase == 'cold':
                    cold_periods.append({'start': phase_start, 'end': i, 'duration': i - phase_start})
                current_phase = 'normal'
                phase_start = i
        
        hot_cold_data['current_phase'] = current_phase
        hot_cold_data['phase_duration'] = len(window_frequencies) - phase_start
        hot_cold_data['hot_periods'] = hot_periods
        hot_cold_data['cold_periods'] = cold_periods
        
        # 주기 분석
        if hot_periods:
            hot_cold_data['cycle_analysis']['average_hot_duration'] = statistics.mean([p['duration'] for p in hot_periods])
        if cold_periods:
            hot_cold_data['cycle_analysis']['average_cold_duration'] = statistics.mean([p['duration'] for p in cold_periods])
        
        # 온도 점수 계산 (최근 빈도 vs 기준 빈도)
        recent_frequency = window_frequencies[-1] if window_frequencies else baseline_frequency
        temperature_ratio = recent_frequency / baseline_frequency
        hot_cold_data['temperature_score'] = min(100, max(-100, (temperature_ratio - 1) * 100))
        
        return hot_cold_data
    
    def _analyze_cyclical_patterns(self, games: List[Dict]) -> Dict[str, Any]:
        """순환 패턴 분석"""
        cyclical_data = {
            'cycle_length': 0,
            'cycle_strength': 0.0,
            'current_cycle_position': 0,
            'predicted_next_events': [],
            'seasonality_detected': False
        }
        
        if len(games) < 30:
            return cyclical_data
        
        # 페어 발생 간격 분석
        pair_intervals = []
        last_pair_index = None
        
        for i, game in enumerate(games):
            if game.get('pair_info', {}).get('has_any_pair', False):
                if last_pair_index is not None:
                    pair_intervals.append(i - last_pair_index)
                last_pair_index = i
        
        if len(pair_intervals) < 5:
            return cyclical_data
        
        # 주기성 감지
        interval_counter = Counter(pair_intervals)
        most_common_interval = interval_counter.most_common(1)[0][0]
        
        if interval_counter[most_common_interval] >= len(pair_intervals) * 0.3:  # 30% 이상 동일한 간격
            cyclical_data['cycle_length'] = most_common_interval
            cyclical_data['cycle_strength'] = interval_counter[most_common_interval] / len(pair_intervals)
            cyclical_data['seasonality_detected'] = True
            
            # 현재 사이클 위치 계산
            if last_pair_index is not None:
                cyclical_data['current_cycle_position'] = len(games) - last_pair_index - 1
        
        return cyclical_data
    
    def _analyze_ml_patterns(self, games: List[Dict]) -> Dict[str, Any]:
        """머신러닝 기반 패턴 분석"""
        ml_analysis = {
            'feature_importance': {},
            'pattern_clusters': [],
            'anomaly_detection': {
                'anomalous_games': [],
                'anomaly_score': 0.0
            },
            'sequence_patterns': {
                'frequent_sequences': [],
                'rare_sequences': []
            }
        }
        
        if len(games) < 50:
            ml_analysis['insufficient_data'] = True
            return ml_analysis
        
        try:
            # 특성 벡터 생성
            features = self._extract_ml_features(games)
            
            # 클러스터링 분석 (간단한 k-means 유사)
            clusters = self._simple_clustering(features)
            ml_analysis['pattern_clusters'] = clusters
            
            # 시퀀스 패턴 마이닝
            sequences = self._extract_game_sequences(games)
            ml_analysis['sequence_patterns'] = self._analyze_sequences(sequences)
            
            # 이상 탐지
            anomalies = self._detect_anomalies(features, games)
            ml_analysis['anomaly_detection'] = anomalies
            
        except Exception as e:
            logger.error(f"ML analysis failed: {e}")
            ml_analysis['error'] = str(e)
        
        return ml_analysis
    
    def _analyze_temporal_patterns(self, games: List[Dict]) -> Dict[str, Any]:
        """시간 기반 패턴 분석"""
        temporal_data = {
            'time_of_day_patterns': {},
            'day_of_week_patterns': {},
            'hourly_distribution': {},
            'peak_hours': [],
            'low_activity_periods': []
        }
        
        try:
            # 시간별 분포 분석
            hourly_pairs = defaultdict(int)
            hourly_games = defaultdict(int)
            
            for game in games:
                game_time_str = game.get('game_time', '')
                if game_time_str:
                    try:
                        # ISO 형식 파싱
                        game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
                        hour = game_time.hour
                        
                        hourly_games[hour] += 1
                        if game.get('pair_info', {}).get('has_any_pair', False):
                            hourly_pairs[hour] += 1
                            
                    except:
                        continue
            
            # 시간대별 페어 비율 계산
            for hour in range(24):
                if hourly_games[hour] > 0:
                    pair_rate = hourly_pairs[hour] / hourly_games[hour]
                    temporal_data['hourly_distribution'][hour] = {
                        'games': hourly_games[hour],
                        'pairs': hourly_pairs[hour],
                        'pair_rate': pair_rate
                    }
            
            # 피크 시간대 식별
            if temporal_data['hourly_distribution']:
                sorted_hours = sorted(temporal_data['hourly_distribution'].items(),
                                    key=lambda x: x[1]['pair_rate'], reverse=True)
                temporal_data['peak_hours'] = [hour for hour, data in sorted_hours[:3]]
                temporal_data['low_activity_periods'] = [hour for hour, data in sorted_hours[-3:]]
                
        except Exception as e:
            logger.error(f"Temporal analysis failed: {e}")
        
        return temporal_data
    
    def _analyze_card_patterns(self, games: List[Dict]) -> Dict[str, Any]:
        """카드 기반 패턴 분석"""
        card_data = {
            'rank_patterns': {},
            'suit_patterns': {},
            'card_combinations': {},
            'pair_inducing_cards': []
        }
        
        try:
            rank_pair_frequency = defaultdict(int)
            suit_pair_frequency = defaultdict(int)
            total_pairs = 0
            
            for game in games:
                if game.get('pair_info', {}).get('has_any_pair', False):
                    total_pairs += 1
                    pair_cards = game.get('pair_info', {}).get('pair_cards', [])
                    
                    for card in pair_cards:
                        if len(card) >= 2:
                            rank = card[0]
                            suit = card[1]
                            rank_pair_frequency[rank] += 1
                            suit_pair_frequency[suit] += 1
            
            # 랭크별 페어 빈도
            if total_pairs > 0:
                card_data['rank_patterns'] = {
                    rank: count / total_pairs for rank, count in rank_pair_frequency.items()
                }
                card_data['suit_patterns'] = {
                    suit: count / total_pairs for suit, count in suit_pair_frequency.items()
                }
            
            # 페어를 유발하는 카드 조합 분석
            if rank_pair_frequency:
                most_frequent_ranks = sorted(rank_pair_frequency.items(), 
                                           key=lambda x: x[1], reverse=True)[:5]
                card_data['pair_inducing_cards'] = [
                    {'rank': rank, 'frequency': freq, 'probability': freq / total_pairs}
                    for rank, freq in most_frequent_ranks
                ]
                
        except Exception as e:
            logger.error(f"Card pattern analysis failed: {e}")
        
        return card_data
    
    def _generate_prediction(self, games: List[Dict]) -> PatternPrediction:
        """ML 기반 예측 생성"""
        try:
            if len(games) < 20:
                return PatternPrediction(
                    pair_probability=0.118,  # 이론적 확률
                    confidence=0.1,
                    expected_games_to_pair=8,
                    pattern_strength=0.0,
                    recommendation="데이터 부족 - 더 많은 게임 필요"
                )
            
            # 최근 패턴 기반 예측
            recent_games = games[:30]  # 최근 30게임
            recent_pairs = len([g for g in recent_games if g.get('pair_info', {}).get('has_any_pair', False)])
            recent_frequency = recent_pairs / len(recent_games)
            
            # 스트릭 기반 조정
            current_no_pair_streak = 0
            for game in games:
                if game.get('pair_info', {}).get('has_any_pair', False):
                    break
                current_no_pair_streak += 1
            
            # 기본 확률에서 조정
            base_probability = 0.118
            
            # 빈도 기반 조정
            frequency_factor = recent_frequency / base_probability
            
            # 스트릭 기반 조정 (길수록 확률 증가)
            streak_factor = min(2.0, 1.0 + (current_no_pair_streak * 0.02))
            
            # 최종 확률 계산
            predicted_probability = min(0.5, base_probability * frequency_factor * streak_factor)
            
            # 신뢰도 계산
            confidence = min(0.9, 0.3 + (len(games) / 500))
            
            # 예상 게임 수
            if predicted_probability > 0:
                expected_games = int(1 / predicted_probability)
            else:
                expected_games = 15
            
            # 패턴 강도
            pattern_strength = abs(recent_frequency - base_probability) / base_probability
            
            # 추천사항 생성
            if predicted_probability > base_probability * 1.5:
                recommendation = "높은 페어 확률 - 적극적 관찰 권장"
            elif predicted_probability < base_probability * 0.5:
                recommendation = "낮은 페어 확률 - 보수적 접근 권장"
            elif current_no_pair_streak > 15:
                recommendation = "장기 스트릭 - 페어 발생 가능성 주의"
            else:
                recommendation = "정상 범위 - 일반적인 패턴 유지"
            
            return PatternPrediction(
                pair_probability=predicted_probability,
                confidence=confidence,
                expected_games_to_pair=expected_games,
                pattern_strength=pattern_strength,
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.error(f"Prediction generation failed: {e}")
            return PatternPrediction(
                pair_probability=0.118,
                confidence=0.0,
                expected_games_to_pair=8,
                pattern_strength=0.0,
                recommendation=f"예측 오류: {str(e)}"
            )
    
    def _extract_ml_features(self, games: List[Dict]) -> List[List[float]]:
        """ML을 위한 특성 벡터 추출"""
        features = []
        
        for i, game in enumerate(games):
            feature_vector = [
                # 1. 페어 여부
                1.0 if game.get('pair_info', {}).get('has_any_pair', False) else 0.0,
                
                # 2. 결과 (PLAYER=0, BANKER=1, TIE=2)
                {'PLAYER': 0.0, 'BANKER': 1.0, 'TIE': 2.0}.get(game.get('result', 'PLAYER'), 0.0),
                
                # 3. 게임 순서 (정규화)
                i / len(games),
                
                # 4. 이전 게임들의 페어 빈도 (윈도우 5)
                self._get_recent_pair_frequency(games, i, 5),
                
                # 5. 이전 게임들의 페어 빈도 (윈도우 10)
                self._get_recent_pair_frequency(games, i, 10),
            ]
            
            features.append(feature_vector)
        
        return features
    
    def _get_recent_pair_frequency(self, games: List[Dict], current_index: int, window_size: int) -> float:
        """최근 윈도우에서 페어 빈도 계산"""
        start_index = max(0, current_index - window_size)
        window_games = games[start_index:current_index]
        
        if not window_games:
            return 0.0
        
        pair_count = len([g for g in window_games if g.get('pair_info', {}).get('has_any_pair', False)])
        return pair_count / len(window_games)
    
    def _simple_clustering(self, features: List[List[float]]) -> List[Dict[str, Any]]:
        """간단한 클러스터링 (K-means 유사)"""
        if len(features) < 10:
            return []
        
        try:
            # NumPy가 없으므로 간단한 거리 기반 클러스터링
            clusters = []
            cluster_centers = []
            
            # 첫 번째 중심점들 선택
            n_clusters = min(3, len(features) // 10)
            step = len(features) // n_clusters
            
            for i in range(n_clusters):
                center_index = i * step
                cluster_centers.append(features[center_index])
                clusters.append({
                    'center': features[center_index],
                    'members': [],
                    'size': 0
                })
            
            # 각 점을 가장 가까운 클러스터에 할당
            for i, point in enumerate(features):
                min_distance = float('inf')
                closest_cluster = 0
                
                for j, center in enumerate(cluster_centers):
                    distance = self._euclidean_distance(point, center)
                    if distance < min_distance:
                        min_distance = distance
                        closest_cluster = j
                
                clusters[closest_cluster]['members'].append(i)
                clusters[closest_cluster]['size'] += 1
            
            return clusters
            
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return []
    
    def _euclidean_distance(self, point1: List[float], point2: List[float]) -> float:
        """유클리드 거리 계산"""
        return sum((a - b) ** 2 for a, b in zip(point1, point2)) ** 0.5
    
    def _detect_anomalies(self, features: List[List[float]], games: List[Dict]) -> Dict[str, Any]:
        """이상 패턴 감지"""
        anomaly_data = {
            'anomalous_games': [],
            'anomaly_score': 0.0,
            'anomaly_threshold': 0.95
        }
        
        if len(features) < 20:
            return anomaly_data
        
        try:
            # 각 특성의 평균과 표준편차 계산
            feature_stats = []
            for i in range(len(features[0])):
                feature_values = [f[i] for f in features]
                mean_val = statistics.mean(feature_values)
                std_val = statistics.stdev(feature_values) if len(feature_values) > 1 else 0.0
                feature_stats.append((mean_val, std_val))
            
            # 각 게임의 이상 점수 계산
            anomaly_scores = []
            for i, (feature_vector, game) in enumerate(zip(features, games)):
                score = 0.0
                
                for j, (value, (mean_val, std_val)) in enumerate(zip(feature_vector, feature_stats)):
                    if std_val > 0:
                        z_score = abs((value - mean_val) / std_val)
                        score += z_score
                
                anomaly_scores.append((i, score, game))
            
            # 임계값 이상인 게임들을 이상으로 분류
            threshold = statistics.mean([score for _, score, _ in anomaly_scores]) + \
                       2 * statistics.stdev([score for _, score, _ in anomaly_scores]) if len(anomaly_scores) > 1 else 0
            
            anomalous_games = [(i, score, game) for i, score, game in anomaly_scores if score > threshold]
            
            anomaly_data['anomalous_games'] = [
                {
                    'game_index': i,
                    'anomaly_score': score,
                    'game_id': game.get('game_id'),
                    'reason': '통계적 이상치'
                }
                for i, score, game in anomalous_games[:5]  # 상위 5개만
            ]
            
            anomaly_data['anomaly_score'] = len(anomalous_games) / len(games) if games else 0.0
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
        
        return anomaly_data
    
    def _calculate_pattern_score(self, base_patterns: Dict, ml_analysis: Dict, 
                                temporal_patterns: Dict, card_patterns: Dict) -> float:
        """종합 패턴 점수 계산"""
        try:
            # 각 분석 결과에서 점수 추출
            streak_score = base_patterns.get('streak_analysis', {}).get('pattern_strength', 0.0)
            frequency_score = abs(base_patterns.get('pair_frequency', {}).get('recent_vs_historical', 0.0))
            hot_cold_score = abs(base_patterns.get('hot_cold_periods', {}).get('temperature_score', 0.0)) / 100
            temporal_score = len(temporal_patterns.get('peak_hours', [])) / 24  # 정규화
            
            # 가중 평균
            total_score = (
                streak_score * self.weights['streak_weight'] +
                frequency_score * self.weights['frequency_weight'] +
                hot_cold_score * self.weights['hot_cold_weight'] +
                temporal_score * self.weights['time_weight']
            )
            
            return min(1.0, total_score)
            
        except Exception as e:
            logger.error(f"Pattern score calculation failed: {e}")
            return 0.0
    
    def _generate_insights(self, games: List[Dict], prediction: PatternPrediction) -> List[str]:
        """인사이트 생성"""
        insights = []
        
        if not games:
            return ["데이터 부족으로 인사이트를 생성할 수 없습니다."]
        
        # 최근 페어 빈도 분석
        recent_pairs = len([g for g in games[:20] if g.get('pair_info', {}).get('has_any_pair', False)])
        recent_frequency = recent_pairs / min(20, len(games))
        
        if recent_frequency > 0.15:
            insights.append(f"📈 최근 페어 발생률이 높습니다 ({recent_frequency:.1%})")
        elif recent_frequency < 0.08:
            insights.append(f"📉 최근 페어 발생률이 낮습니다 ({recent_frequency:.1%})")
        
        # 스트릭 분석
        current_no_pair_streak = 0
        for game in games:
            if game.get('pair_info', {}).get('has_any_pair', False):
                break
            current_no_pair_streak += 1
        
        if current_no_pair_streak > 20:
            insights.append(f"⚡ 현재 {current_no_pair_streak}게임 연속 페어 없음 - 주의 깊게 관찰 필요")
        elif current_no_pair_streak > 10:
            insights.append(f"⏰ 현재 {current_no_pair_streak}게임 연속 페어 없음")
        
        # 예측 기반 인사이트
        if prediction.confidence > 0.7:
            if prediction.pair_probability > 0.15:
                insights.append("🎯 높은 페어 확률이 예측됩니다")
            elif prediction.pair_probability < 0.08:
                insights.append("🔍 낮은 페어 확률이 예측됩니다")
        
        return insights if insights else ["일반적인 패턴을 보이고 있습니다."]
    
    def _generate_pattern_alerts(self, games: List[Dict], prediction: PatternPrediction) -> List[Dict[str, Any]]:
        """패턴 기반 알림 생성"""
        alerts = []
        
        # 장기 스트릭 알림
        current_no_pair_streak = 0
        for game in games:
            if game.get('pair_info', {}).get('has_any_pair', False):
                break
            current_no_pair_streak += 1
        
        if current_no_pair_streak > 25:
            alerts.append({
                'type': 'long_streak',
                'severity': 'high',
                'message': f'{current_no_pair_streak}게임 연속 페어 없음 - 임계치 도달',
                'value': current_no_pair_streak
            })
        elif current_no_pair_streak > 15:
            alerts.append({
                'type': 'streak_watch',
                'severity': 'medium',
                'message': f'{current_no_pair_streak}게임 연속 페어 없음 - 관찰 필요',
                'value': current_no_pair_streak
            })
        
        # 높은 확률 알림
        if prediction.confidence > 0.8 and prediction.pair_probability > 0.2:
            alerts.append({
                'type': 'high_probability',
                'severity': 'high',
                'message': f'페어 확률 {prediction.pair_probability:.1%} - 높은 가능성',
                'value': prediction.pair_probability
            })
        
        return alerts
    
    def _find_pair_clusters(self, pair_positions: List[int]) -> List[Dict[str, Any]]:
        """페어 클러스터 찾기"""
        if len(pair_positions) < 2:
            return []
        
        clusters = []
        current_cluster = [pair_positions[0]]
        
        for i in range(1, len(pair_positions)):
            if pair_positions[i] - pair_positions[i-1] <= 5:  # 5게임 이내면 같은 클러스터
                current_cluster.append(pair_positions[i])
            else:
                if len(current_cluster) >= 2:
                    clusters.append({
                        'positions': current_cluster,
                        'size': len(current_cluster),
                        'span': current_cluster[-1] - current_cluster[0]
                    })
                current_cluster = [pair_positions[i]]
        
        # 마지막 클러스터 처리
        if len(current_cluster) >= 2:
            clusters.append({
                'positions': current_cluster,
                'size': len(current_cluster),
                'span': current_cluster[-1] - current_cluster[0]
            })
        
        return clusters
    
    def _extract_game_sequences(self, games: List[Dict]) -> List[str]:
        """게임 시퀀스 추출"""
        sequences = []
        
        for game in games:
            # 간단한 시퀀스 패턴 (결과 + 페어 여부)
            result = game.get('result', 'U')[0]  # P, B, T, U
            has_pair = '1' if game.get('pair_info', {}).get('has_any_pair', False) else '0'
            sequences.append(result + has_pair)
        
        return sequences
    
    def _analyze_sequences(self, sequences: List[str]) -> Dict[str, Any]:
        """시퀀스 패턴 분석"""
        if len(sequences) < 10:
            return {'frequent_sequences': [], 'rare_sequences': []}
        
        # 3-gram 분석
        trigrams = []
        for i in range(len(sequences) - 2):
            trigram = ''.join(sequences[i:i+3])
            trigrams.append(trigram)
        
        trigram_counts = Counter(trigrams)
        total_trigrams = len(trigrams)
        
        # 빈발 시퀀스 (상위 20%)
        frequent_threshold = max(1, total_trigrams * 0.02)  # 2% 이상
        frequent_sequences = [
            {'sequence': seq, 'count': count, 'frequency': count / total_trigrams}
            for seq, count in trigram_counts.items() if count >= frequent_threshold
        ]
        
        # 희귀 시퀀스 (1회만 등장)
        rare_sequences = [
            {'sequence': seq, 'count': 1, 'frequency': 1 / total_trigrams}
            for seq, count in trigram_counts.items() if count == 1
        ]
        
        return {
            'frequent_sequences': sorted(frequent_sequences, key=lambda x: x['count'], reverse=True)[:10],
            'rare_sequences': rare_sequences[:10]
        }
    
    def _calculate_streak_pattern_strength(self, no_pair_streaks: List[int], 
                                         pair_positions: List[int], total_games: int) -> float:
        """스트릭 패턴 강도 계산"""
        if not no_pair_streaks or total_games == 0:
            return 0.0
        
        # 표준편차 기반 패턴 강도
        if len(no_pair_streaks) > 1:
            mean_streak = statistics.mean(no_pair_streaks)
            std_streak = statistics.stdev(no_pair_streaks)
            cv = std_streak / mean_streak if mean_streak > 0 else 0  # 변동계수
            
            # 변동계수가 낮을수록 패턴이 강함
            pattern_strength = 1 / (1 + cv) if cv > 0 else 1.0
        else:
            pattern_strength = 0.5
        
        return min(1.0, pattern_strength)
    
    def _empty_pattern_result(self, table_name: str = 'unknown') -> Dict[str, Any]:
        """빈 패턴 결과 반환"""
        return {
            'table_name': table_name,
            'analyzed_games': 0,
            'analysis_timestamp': datetime.now().isoformat(),
            'pattern_score': 0.0,
            'base_patterns': {},
            'ml_analysis': {'insufficient_data': True},
            'temporal_patterns': {},
            'card_patterns': {},
            'prediction': {
                'pair_probability': 0.118,
                'confidence': 0.0,
                'expected_games_to_pair': 8,
                'pattern_strength': 0.0,
                'recommendation': '데이터 부족'
            },
            'insights': ['충분한 데이터가 없습니다.'],
            'alerts': []
        }


if __name__ == '__main__':
    # 테스트 실행
    print("Testing Pattern Analyzer v2.0...")
    
    analyzer = PatternAnalyzerV2()
    
    # 더미 게임 데이터 생성
    dummy_games = []
    for i in range(50):
        dummy_games.append({
            'game_id': i + 1,
            'game_time': datetime.now().isoformat(),
            'result': ['PLAYER', 'BANKER', 'TIE'][i % 3],
            'pair_info': {
                'has_any_pair': i % 7 == 0,  # 7게임마다 페어
                'pair_type': 'PLAYER_PAIR' if i % 7 == 0 else None
            }
        })
    
    # 패턴 분석 실행
    result = analyzer.analyze_comprehensive_patterns('test_table', dummy_games)
    
    print(f"✅ 분석 완료: {result['analyzed_games']}게임")
    print(f"📊 패턴 점수: {result['pattern_score']:.3f}")
    print(f"🎯 예측 확률: {result['prediction']['pair_probability']:.1%}")
    print(f"💡 추천사항: {result['prediction']['recommendation']}")
    print(f"🔍 인사이트 수: {len(result['insights'])}")
    
    print("\n패턴 분석기 v2.0 테스트 완료!")