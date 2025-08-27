#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
딥러닝 분석 통합 서비스
기존 AI 예측 엔진을 활용하여 패킷 데이터 특화 분석 제공
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from pathlib import Path
import json

# 기존 AI 엔진 임포트
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from ai_prediction_engine import AIPredictionEngine, get_ai_prediction_engine
from .optimized_database import OptimizedDatabase
from .async_ai_engine import AsyncAIEngine

logger = logging.getLogger(__name__)


class DeepLearningAnalysisService:
    """딥러닝 기반 바카라 페어 분석 서비스"""
    
    def __init__(self, 
                 db_service: Optional[OptimizedDatabase] = None,
                 ai_engine: Optional[AIPredictionEngine] = None):
        """
        딥러닝 분석 서비스 초기화
        
        Args:
            db_service: 데이터베이스 서비스
            ai_engine: AI 예측 엔진
        """
        self.db_service = db_service
        self.ai_engine = ai_engine or get_ai_prediction_engine()
        
        # 분석 결과 캐시
        self.analysis_cache = {}
        self.cache_ttl = 300  # 5분 캐시
        
        # 분석 통계
        self.analysis_stats = {
            'total_analyses': 0,
            'successful_predictions': 0,
            'cache_hits': 0,
            'training_sessions': 0,
            'last_training': None
        }
        
        logger.info("딥러닝 분석 서비스 초기화 완료")
    
    async def analyze_pair_patterns(self, 
                                  table_name: str, 
                                  days: int = 7,
                                  include_prediction: bool = True) -> Dict[str, Any]:
        """
        특정 테이블의 페어 패턴 딥러닝 분석
        
        Args:
            table_name: 분석할 테이블명
            days: 분석할 일수
            include_prediction: 예측 정보 포함 여부
            
        Returns:
            패턴 분석 결과
        """
        try:
            cache_key = f"pattern_analysis_{table_name}_{days}"
            
            # 캐시 확인
            if self._is_cache_valid(cache_key):
                self.analysis_stats['cache_hits'] += 1
                return self.analysis_cache[cache_key]
            
            logger.info(f"테이블 {table_name} 페어 패턴 분석 시작 ({days}일)")
            
            # 데이터 수집
            since_time = datetime.now() - timedelta(days=days)
            games_data = await self._collect_games_data(table_name, since_time)
            
            if not games_data:
                return {
                    'status': 'no_data',
                    'message': f'{table_name} 테이블에서 {days}일간 데이터가 없습니다.',
                    'analysis_time': datetime.now().isoformat()
                }
            
            # 패턴 분석 수행
            pattern_analysis = await self._analyze_patterns(games_data, table_name)
            
            # 예측 분석 (선택적)
            prediction_analysis = None
            if include_prediction:
                prediction_analysis = await self._perform_prediction_analysis(games_data, table_name)
            
            # 결과 구성
            analysis_result = {
                'status': 'success',
                'table_name': table_name,
                'analysis_period': {
                    'days': days,
                    'from': since_time.isoformat(),
                    'to': datetime.now().isoformat(),
                    'total_games': len(games_data)
                },
                'pattern_analysis': pattern_analysis,
                'prediction_analysis': prediction_analysis,
                'analysis_time': datetime.now().isoformat(),
                'confidence_score': self._calculate_confidence_score(pattern_analysis, len(games_data))
            }
            
            # 캐시 저장
            self.analysis_cache[cache_key] = analysis_result
            self.analysis_stats['total_analyses'] += 1
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"페어 패턴 분석 실패 {table_name}: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'analysis_time': datetime.now().isoformat()
            }
    
    async def _collect_games_data(self, table_name: str, since_time: datetime) -> List[Dict[str, Any]]:
        """게임 데이터 수집 및 전처리"""
        try:
            if not self.db_service:
                logger.warning("데이터베이스 서비스 없음 - 테스트 데이터 사용")
                return self._generate_test_data(table_name, 100)
            
            # 데이터베이스에서 게임 데이터 조회
            raw_games = await self.db_service.get_games_with_details(
                table_name=table_name,
                since=since_time,
                limit=1000
            )
            
            # AI 엔진 형식으로 변환
            games_data = []
            for game in raw_games:
                game_data = {
                    'table_name': game.get('table_name', table_name),
                    'game_id': game.get('game_id', 0),
                    'game_time': game.get('game_time', datetime.now().isoformat()),
                    'result': game.get('result', 'Unknown'),
                    'player_cards': game.get('player_cards', []),
                    'banker_cards': game.get('banker_cards', []),
                    'player_score': game.get('player_score', 0),
                    'banker_score': game.get('banker_score', 0),
                    'has_pair': game.get('has_pair', False),
                    'pair_type': game.get('pair_type'),
                    'pair_cards': game.get('pair_cards', []),
                    'is_natural': game.get('is_natural', False)
                }
                games_data.append(game_data)
            
            logger.info(f"수집된 게임 데이터: {len(games_data)}건")
            return games_data
            
        except Exception as e:
            logger.error(f"게임 데이터 수집 실패: {e}")
            return []
    
    async def _analyze_patterns(self, games_data: List[Dict[str, Any]], table_name: str) -> Dict[str, Any]:
        """게임 데이터의 패턴 분석"""
        try:
            # 기본 통계
            total_games = len(games_data)
            pair_games = [g for g in games_data if g.get('has_pair', False)]
            pair_rate = len(pair_games) / total_games if total_games > 0 else 0
            
            # 페어 타입별 분석
            pair_type_stats = {}
            for pair_type in ['PLAYER_PAIR', 'BANKER_PAIR', 'BOTH_PAIR']:
                type_pairs = [g for g in pair_games if g.get('pair_type') == pair_type]
                pair_type_stats[pair_type] = {
                    'count': len(type_pairs),
                    'rate': len(type_pairs) / total_games if total_games > 0 else 0,
                    'avg_interval': self._calculate_avg_interval(type_pairs, games_data)
                }
            
            # 시간대별 패턴
            hourly_pattern = self._analyze_hourly_patterns(pair_games)
            
            # 연속 패턴 분석
            sequence_patterns = self._analyze_sequence_patterns(games_data)
            
            # 카드 패턴 분석
            card_patterns = self._analyze_card_patterns(pair_games)
            
            # 승률과 페어의 상관관계
            win_correlation = self._analyze_win_pair_correlation(games_data)
            
            return {
                'basic_stats': {
                    'total_games': total_games,
                    'total_pairs': len(pair_games),
                    'pair_rate': round(pair_rate * 100, 2)
                },
                'pair_type_analysis': pair_type_stats,
                'hourly_patterns': hourly_pattern,
                'sequence_patterns': sequence_patterns,
                'card_patterns': card_patterns,
                'win_correlation': win_correlation,
                'advanced_metrics': self._calculate_advanced_metrics(games_data, pair_games)
            }
            
        except Exception as e:
            logger.error(f"패턴 분석 실패: {e}")
            return {'error': str(e)}
    
    async def _perform_prediction_analysis(self, games_data: List[Dict[str, Any]], 
                                         table_name: str) -> Dict[str, Any]:
        """예측 분석 수행"""
        try:
            if len(games_data) < 50:
                return {
                    'status': 'insufficient_data',
                    'message': '예측 분석을 위한 데이터가 부족합니다 (최소 50게임 필요)'
                }
            
            # 모델 훈련 (필요시)
            training_result = await self._train_model_if_needed(games_data)
            
            # 최근 게임들에 대한 예측 테스트
            test_games = games_data[-20:]  # 최근 20게임
            prediction_results = []
            
            for i, current_game in enumerate(test_games):
                if i < 10:  # 처음 10게임은 히스토리로 사용
                    continue
                
                # 이전 게임들을 히스토리로 사용
                recent_history = test_games[max(0, i-10):i]
                
                # 예측 수행
                prediction = self.ai_engine.predict_pair(current_game, recent_history)
                
                # 실제 결과와 비교
                actual_result = self._get_actual_pair_result(current_game)
                is_correct = prediction['predicted_pair_type'] == actual_result
                
                prediction_results.append({
                    'game_id': current_game.get('game_id'),
                    'predicted': prediction['predicted_pair_type'],
                    'actual': actual_result,
                    'confidence': prediction['confidence'],
                    'is_correct': is_correct,
                    'prediction_method': prediction['prediction_method']
                })
            
            # 예측 성능 분석
            correct_predictions = sum(1 for r in prediction_results if r['is_correct'])
            accuracy = correct_predictions / len(prediction_results) if prediction_results else 0
            
            # 신뢰도별 성능
            confidence_analysis = self._analyze_confidence_performance(prediction_results)
            
            # 향후 예측 (다음 5게임)
            future_predictions = await self._generate_future_predictions(games_data, 5)
            
            return {
                'status': 'success',
                'training_result': training_result,
                'test_results': {
                    'total_tests': len(prediction_results),
                    'correct_predictions': correct_predictions,
                    'accuracy': round(accuracy * 100, 2),
                    'detailed_results': prediction_results[-5:]  # 최근 5개만 표시
                },
                'confidence_analysis': confidence_analysis,
                'future_predictions': future_predictions,
                'model_info': self.ai_engine.get_prediction_stats()['model_info']
            }
            
        except Exception as e:
            logger.error(f"예측 분석 실패: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _train_model_if_needed(self, games_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """필요시 모델 재훈련"""
        try:
            model_info = self.ai_engine.get_prediction_stats()['model_info']
            
            # 훈련이 필요한 조건 체크
            needs_training = (
                not model_info.get('is_trained', False) or
                len(games_data) > 200 and 
                (self.analysis_stats['last_training'] is None or
                 (datetime.now() - datetime.fromisoformat(self.analysis_stats['last_training'])).days > 7)
            )
            
            if needs_training:
                logger.info("AI 모델 훈련 시작...")
                training_result = self.ai_engine.train_model(games_data)
                
                if training_result.get('success'):
                    self.analysis_stats['training_sessions'] += 1
                    self.analysis_stats['last_training'] = datetime.now().isoformat()
                    logger.info(f"모델 훈련 완료 - 정확도: {training_result.get('val_accuracy', 0):.3f}")
                
                return training_result
            else:
                return {
                    'success': True,
                    'message': '기존 훈련된 모델 사용',
                    'skipped': True
                }
                
        except Exception as e:
            logger.error(f"모델 훈련 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def _analyze_hourly_patterns(self, pair_games: List[Dict[str, Any]]) -> Dict[str, int]:
        """시간대별 페어 발생 패턴 분석"""
        hourly_counts = {}
        
        for game in pair_games:
            try:
                game_time = datetime.fromisoformat(game['game_time'].replace('Z', '+00:00'))
                hour = game_time.hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            except:
                continue
        
        return hourly_counts
    
    def _analyze_sequence_patterns(self, games_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """연속 패턴 분석"""
        try:
            # 페어 발생 간격 분석
            pair_indices = [i for i, g in enumerate(games_data) if g.get('has_pair', False)]
            intervals = [pair_indices[i] - pair_indices[i-1] for i in range(1, len(pair_indices))]
            
            # 연속 페어 패턴
            consecutive_pairs = 0
            max_consecutive = 0
            current_consecutive = 0
            
            for game in games_data:
                if game.get('has_pair', False):
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    if current_consecutive > 1:
                        consecutive_pairs += 1
                    current_consecutive = 0
            
            return {
                'avg_interval': np.mean(intervals) if intervals else 0,
                'min_interval': min(intervals) if intervals else 0,
                'max_interval': max(intervals) if intervals else 0,
                'consecutive_pair_sequences': consecutive_pairs,
                'max_consecutive_pairs': max_consecutive,
                'total_intervals': len(intervals)
            }
            
        except Exception as e:
            logger.error(f"시퀀스 패턴 분석 실패: {e}")
            return {}
    
    def _analyze_card_patterns(self, pair_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """카드 패턴 분석"""
        try:
            suit_patterns = {'♠': 0, '♥': 0, '♦': 0, '♣': 0}
            rank_patterns = {}
            
            for game in pair_games:
                pair_cards = game.get('pair_cards', [])
                for card in pair_cards:
                    if len(card) >= 2:
                        rank = card[:-1]
                        suit = card[-1]
                        
                        if suit in suit_patterns:
                            suit_patterns[suit] += 1
                        
                        rank_patterns[rank] = rank_patterns.get(rank, 0) + 1
            
            # 가장 흔한 패턴들
            most_common_suit = max(suit_patterns.items(), key=lambda x: x[1]) if suit_patterns else ('', 0)
            most_common_rank = max(rank_patterns.items(), key=lambda x: x[1]) if rank_patterns else ('', 0)
            
            return {
                'suit_distribution': suit_patterns,
                'rank_distribution': rank_patterns,
                'most_common_suit': most_common_suit[0],
                'most_common_rank': most_common_rank[0],
                'total_pair_cards': sum(suit_patterns.values())
            }
            
        except Exception as e:
            logger.error(f"카드 패턴 분석 실패: {e}")
            return {}
    
    def _analyze_win_pair_correlation(self, games_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """승부와 페어 발생의 상관관계 분석"""
        try:
            correlations = {
                'player_win_with_pair': 0,
                'banker_win_with_pair': 0,
                'tie_with_pair': 0,
                'total_wins': {'Player': 0, 'Banker': 0, 'Tie': 0},
                'pair_wins': {'Player': 0, 'Banker': 0, 'Tie': 0}
            }
            
            for game in games_data:
                result = game.get('result', 'Unknown')
                has_pair = game.get('has_pair', False)
                
                # 전체 승부 카운트
                if result in correlations['total_wins']:
                    correlations['total_wins'][result] += 1
                
                # 페어가 있는 경우의 승부
                if has_pair and result in correlations['pair_wins']:
                    correlations['pair_wins'][result] += 1
            
            # 상관관계 계산
            total_games = len(games_data)
            total_pairs = sum(1 for g in games_data if g.get('has_pair', False))
            
            if total_pairs > 0:
                for result in ['Player', 'Banker', 'Tie']:
                    pair_rate_with_result = (correlations['pair_wins'][result] / total_pairs * 100) if total_pairs > 0 else 0
                    overall_rate = (correlations['total_wins'][result] / total_games * 100) if total_games > 0 else 0
                    
                    correlations[f'{result.lower()}_correlation'] = round(pair_rate_with_result - overall_rate, 2)
            
            return correlations
            
        except Exception as e:
            logger.error(f"승부-페어 상관관계 분석 실패: {e}")
            return {}
    
    def _calculate_advanced_metrics(self, games_data: List[Dict[str, Any]], 
                                  pair_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """고급 메트릭 계산"""
        try:
            total_games = len(games_data)
            total_pairs = len(pair_games)
            
            if total_games == 0:
                return {}
            
            # 페어 클러스터링 분석
            pair_clustering = self._analyze_pair_clustering(games_data)
            
            # 예측 가능성 점수
            predictability_score = self._calculate_predictability_score(games_data)
            
            # 변동성 분석
            volatility_analysis = self._analyze_pair_volatility(games_data)
            
            return {
                'pair_clustering': pair_clustering,
                'predictability_score': predictability_score,
                'volatility_analysis': volatility_analysis,
                'efficiency_metrics': {
                    'data_quality': min(100, (total_games / 100) * 100),  # 최대 100%
                    'pattern_strength': min(100, (total_pairs / total_games) * 1000),  # 페어율 * 1000
                    'analysis_confidence': self._calculate_confidence_score({'basic_stats': {'total_pairs': total_pairs}}, total_games)
                }
            }
            
        except Exception as e:
            logger.error(f"고급 메트릭 계산 실패: {e}")
            return {}
    
    def _analyze_pair_clustering(self, games_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """페어 클러스터링 분석 - 페어들이 몰려서 나오는 패턴"""
        try:
            pair_positions = [i for i, g in enumerate(games_data) if g.get('has_pair', False)]
            
            if len(pair_positions) < 2:
                return {'clusters': 0, 'avg_cluster_size': 0}
            
            # 클러스터 감지 (5게임 이내 간격을 같은 클러스터로 간주)
            clusters = []
            current_cluster = [pair_positions[0]]
            
            for i in range(1, len(pair_positions)):
                if pair_positions[i] - pair_positions[i-1] <= 5:
                    current_cluster.append(pair_positions[i])
                else:
                    if len(current_cluster) > 1:
                        clusters.append(current_cluster)
                    current_cluster = [pair_positions[i]]
            
            if len(current_cluster) > 1:
                clusters.append(current_cluster)
            
            avg_cluster_size = np.mean([len(cluster) for cluster in clusters]) if clusters else 0
            
            return {
                'clusters': len(clusters),
                'avg_cluster_size': round(avg_cluster_size, 2),
                'largest_cluster': max([len(cluster) for cluster in clusters]) if clusters else 0
            }
            
        except Exception as e:
            logger.error(f"페어 클러스터링 분석 실패: {e}")
            return {}
    
    def _calculate_predictability_score(self, games_data: List[Dict[str, Any]]) -> float:
        """예측 가능성 점수 계산 (0-100)"""
        try:
            if len(games_data) < 20:
                return 0.0
            
            # 패턴의 규칙성 평가
            pair_intervals = []
            last_pair_index = None
            
            for i, game in enumerate(games_data):
                if game.get('has_pair', False):
                    if last_pair_index is not None:
                        pair_intervals.append(i - last_pair_index)
                    last_pair_index = i
            
            if not pair_intervals:
                return 0.0
            
            # 간격의 변동성이 낮을수록 예측 가능성 높음
            interval_std = np.std(pair_intervals)
            interval_mean = np.mean(pair_intervals)
            
            # 정규화된 변동성 (낮을수록 좋음)
            normalized_volatility = interval_std / interval_mean if interval_mean > 0 else 1
            
            # 예측 가능성 점수 (0-100)
            predictability = max(0, 100 - (normalized_volatility * 20))
            
            return round(predictability, 2)
            
        except Exception as e:
            logger.error(f"예측 가능성 점수 계산 실패: {e}")
            return 0.0
    
    def _analyze_pair_volatility(self, games_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """페어 발생의 변동성 분석"""
        try:
            # 시간 단위별 페어 발생률 변동성
            hourly_rates = {}
            
            for game in games_data:
                try:
                    game_time = datetime.fromisoformat(game['game_time'].replace('Z', '+00:00'))
                    hour = game_time.hour
                    
                    if hour not in hourly_rates:
                        hourly_rates[hour] = {'total': 0, 'pairs': 0}
                    
                    hourly_rates[hour]['total'] += 1
                    if game.get('has_pair', False):
                        hourly_rates[hour]['pairs'] += 1
                except:
                    continue
            
            # 시간대별 페어 비율 계산
            hourly_pair_rates = []
            for hour_data in hourly_rates.values():
                if hour_data['total'] > 0:
                    rate = hour_data['pairs'] / hour_data['total']
                    hourly_pair_rates.append(rate)
            
            if not hourly_pair_rates:
                return {'volatility': 0, 'stability': 'unknown'}
            
            volatility = np.std(hourly_pair_rates)
            mean_rate = np.mean(hourly_pair_rates)
            
            # 안정성 분류
            if volatility < 0.05:
                stability = 'very_stable'
            elif volatility < 0.1:
                stability = 'stable'
            elif volatility < 0.2:
                stability = 'moderate'
            else:
                stability = 'volatile'
            
            return {
                'volatility': round(volatility, 4),
                'mean_rate': round(mean_rate, 4),
                'stability': stability,
                'active_hours': len(hourly_rates)
            }
            
        except Exception as e:
            logger.error(f"변동성 분석 실패: {e}")
            return {}
    
    def _calculate_confidence_score(self, analysis_result: dict, data_size: int) -> float:
        """분석 결과의 신뢰도 점수 계산"""
        try:
            # 데이터 크기 기반 점수 (0-40점)
            size_score = min(40, (data_size / 500) * 40)
            
            # 페어 발생률 기반 점수 (0-30점)
            basic_stats = analysis_result.get('basic_stats', {})
            pair_rate = basic_stats.get('pair_rate', 0) / 100
            rate_score = min(30, pair_rate * 300)  # 10% 페어율일 때 30점
            
            # 패턴 다양성 점수 (0-30점)
            pattern_score = 20 if len(analysis_result) > 3 else 10
            
            total_score = size_score + rate_score + pattern_score
            return round(min(100, total_score), 1)
            
        except Exception as e:
            logger.error(f"신뢰도 점수 계산 실패: {e}")
            return 50.0
    
    async def _generate_future_predictions(self, games_data: List[Dict[str, Any]], 
                                         count: int = 5) -> List[Dict[str, Any]]:
        """향후 게임에 대한 예측 생성"""
        try:
            if len(games_data) < 10:
                return []
            
            recent_games = games_data[-20:]  # 최근 20게임 사용
            future_predictions = []
            
            for i in range(count):
                # 가상의 다음 게임 생성
                next_game = self._generate_hypothetical_game(games_data, i)
                
                # 예측 수행
                prediction = self.ai_engine.predict_pair(next_game, recent_games)
                
                future_predictions.append({
                    'game_sequence': len(games_data) + i + 1,
                    'predicted_pair_type': prediction['predicted_pair_type'],
                    'confidence': prediction['confidence'],
                    'probabilities': prediction.get('probabilities', {}),
                    'prediction_method': prediction['prediction_method']
                })
            
            return future_predictions
            
        except Exception as e:
            logger.error(f"미래 예측 생성 실패: {e}")
            return []
    
    def _generate_hypothetical_game(self, games_data: List[Dict[str, Any]], sequence: int) -> Dict[str, Any]:
        """가상의 게임 데이터 생성 (예측을 위한)"""
        import random
        
        # 최근 게임들의 평균적인 특성 사용
        recent_games = games_data[-10:]
        
        # 평균 점수 계산
        avg_player_score = np.mean([g.get('player_score', 0) for g in recent_games])
        avg_banker_score = np.mean([g.get('banker_score', 0) for g in recent_games])
        
        return {
            'table_name': games_data[-1].get('table_name', 'Unknown'),
            'game_id': games_data[-1].get('game_id', 0) + sequence + 1,
            'game_time': datetime.now().isoformat(),
            'player_score': int(avg_player_score),
            'banker_score': int(avg_banker_score),
            'player_cards': ['A♠', '9♥'],  # 임시 카드
            'banker_cards': ['K♦', '5♣'],  # 임시 카드
            'result': random.choice(['Player', 'Banker', 'Tie'])
        }
    
    def _analyze_confidence_performance(self, prediction_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """신뢰도별 예측 성능 분석"""
        try:
            confidence_ranges = {
                'high': {'min': 0.8, 'total': 0, 'correct': 0},
                'medium': {'min': 0.5, 'total': 0, 'correct': 0},
                'low': {'min': 0.0, 'total': 0, 'correct': 0}
            }
            
            for result in prediction_results:
                confidence = result['confidence']
                is_correct = result['is_correct']
                
                if confidence >= 0.8:
                    confidence_ranges['high']['total'] += 1
                    if is_correct:
                        confidence_ranges['high']['correct'] += 1
                elif confidence >= 0.5:
                    confidence_ranges['medium']['total'] += 1
                    if is_correct:
                        confidence_ranges['medium']['correct'] += 1
                else:
                    confidence_ranges['low']['total'] += 1
                    if is_correct:
                        confidence_ranges['low']['correct'] += 1
            
            # 정확도 계산
            for range_name, range_data in confidence_ranges.items():
                total = range_data['total']
                if total > 0:
                    range_data['accuracy'] = round((range_data['correct'] / total) * 100, 2)
                else:
                    range_data['accuracy'] = 0
            
            return confidence_ranges
            
        except Exception as e:
            logger.error(f"신뢰도 성능 분석 실패: {e}")
            return {}
    
    def _get_actual_pair_result(self, game: Dict[str, Any]) -> str:
        """게임의 실제 페어 결과 반환"""
        if not game.get('has_pair', False):
            return 'NO_PAIR'
        
        pair_type = game.get('pair_type')
        if pair_type in ['PLAYER_PAIR', 'BANKER_PAIR', 'BOTH_PAIR']:
            return pair_type
        
        return 'NO_PAIR'
    
    def _calculate_avg_interval(self, type_pairs: List[Dict[str, Any]], 
                              all_games: List[Dict[str, Any]]) -> float:
        """특정 페어 타입의 평균 발생 간격 계산"""
        try:
            if len(type_pairs) < 2:
                return 0.0
            
            # 페어 발생 위치 찾기
            pair_positions = []
            for i, game in enumerate(all_games):
                if game.get('pair_type') == type_pairs[0].get('pair_type'):
                    pair_positions.append(i)
            
            # 간격 계산
            if len(pair_positions) < 2:
                return 0.0
            
            intervals = [pair_positions[i] - pair_positions[i-1] for i in range(1, len(pair_positions))]
            return round(np.mean(intervals), 2)
            
        except Exception as e:
            logger.error(f"평균 간격 계산 실패: {e}")
            return 0.0
    
    def _generate_test_data(self, table_name: str, count: int) -> List[Dict[str, Any]]:
        """테스트용 게임 데이터 생성"""
        import random
        
        games = []
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        
        for i in range(count):
            has_pair = random.random() < 0.15  # 15% 확률로 페어
            
            game = {
                'table_name': table_name,
                'game_id': i + 1,
                'game_time': (datetime.now() - timedelta(hours=count-i)).isoformat(),
                'result': random.choice(['Player', 'Banker', 'Tie']),
                'player_score': random.randint(0, 9),
                'banker_score': random.randint(0, 9),
                'has_pair': has_pair,
                'is_natural': random.random() < 0.1
            }
            
            # 카드 생성
            if has_pair:
                # 페어 카드 생성
                rank = random.choice(ranks)
                suit1 = random.choice(suits)
                suit2 = random.choice([s for s in suits if s != suit1])
                
                if random.random() < 0.5:  # 플레이어 페어
                    game['pair_type'] = 'PLAYER_PAIR'
                    game['player_cards'] = [f"{rank}{suit1}", f"{rank}{suit2}"]
                    game['banker_cards'] = [f"{random.choice(ranks)}{random.choice(suits)}", 
                                          f"{random.choice(ranks)}{random.choice(suits)}"]
                else:  # 뱅커 페어
                    game['pair_type'] = 'BANKER_PAIR'
                    game['banker_cards'] = [f"{rank}{suit1}", f"{rank}{suit2}"]
                    game['player_cards'] = [f"{random.choice(ranks)}{random.choice(suits)}", 
                                          f"{random.choice(ranks)}{random.choice(suits)}"]
                
                game['pair_cards'] = [f"{rank}{suit1}", f"{rank}{suit2}"]
            else:
                game['pair_type'] = None
                game['player_cards'] = [f"{random.choice(ranks)}{random.choice(suits)}", 
                                      f"{random.choice(ranks)}{random.choice(suits)}"]
                game['banker_cards'] = [f"{random.choice(ranks)}{random.choice(suits)}", 
                                      f"{random.choice(ranks)}{random.choice(suits)}"]
                game['pair_cards'] = []
            
            games.append(game)
        
        return games
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 확인"""
        if cache_key not in self.analysis_cache:
            return False
        
        # TTL 확인 (간단 구현)
        return True  # 실제로는 타임스탬프 비교 필요
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """분석 서비스 통계 반환"""
        return {
            **self.analysis_stats,
            'cache_size': len(self.analysis_cache),
            'ai_engine_stats': self.ai_engine.get_prediction_stats() if self.ai_engine else {}
        }
    
    async def cleanup_cache(self):
        """캐시 정리"""
        self.analysis_cache.clear()
        logger.info("딥러닝 분석 캐시 정리 완료")


# 전역 인스턴스
deep_learning_service = None

def get_deep_learning_analysis_service() -> DeepLearningAnalysisService:
    """전역 딥러닝 분석 서비스 인스턴스 반환"""
    global deep_learning_service
    if deep_learning_service is None:
        deep_learning_service = DeepLearningAnalysisService()
    return deep_learning_service