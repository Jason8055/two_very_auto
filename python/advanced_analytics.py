#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
고급 분석 도구 v1.0
히트맵, 패턴 인사이트, 예측 정확도 분석, 테이블 성과 분석
"""

# 표준 라이브러리
import json
import logging
import sys
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# 서드파티 라이브러리
import numpy as np
import pandas as pd

# 로컬 모듈
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HeatmapGenerator:
    """히트맵 생성기"""
    
    def __init__(self):
        self.color_schemes = {
            'red_blue': ['#0d47a1', '#1976d2', '#42a5f5', '#ffffff', '#ffab91', '#ff5722', '#d32f2f'],
            'green_red': ['#2e7d32', '#4caf50', '#81c784', '#ffffff', '#ffab91', '#ff5722', '#d32f2f'],
            'viridis': ['#440154', '#31688e', '#35b779', '#fde725']
        }
    
    def generate_time_based_heatmap(self, game_data: List[Dict[str, Any]], 
                                  metric: str = 'pair_frequency') -> Dict[str, Any]:
        """시간 기반 히트맵 생성"""
        try:
            # 시간별 데이터 집계
            hourly_data = defaultdict(lambda: defaultdict(int))
            daily_totals = defaultdict(int)
            
            for game in game_data:
                if 'timestamp' not in game:
                    continue
                
                timestamp = pd.to_datetime(game['timestamp'])
                hour = timestamp.hour
                day = timestamp.strftime('%Y-%m-%d')
                table = game.get('table_name', 'Unknown')
                
                if metric == 'pair_frequency':
                    if game.get('has_pair', False):
                        hourly_data[day][hour] += 1
                    daily_totals[day] += 1
                elif metric == 'game_count':
                    hourly_data[day][hour] += 1
                elif metric == 'pair_intensity':
                    # 페어 타입에 따른 강도
                    pair_type = game.get('pair_type', '')
                    intensity = self._get_pair_intensity(pair_type)
                    if game.get('has_pair', False):
                        hourly_data[day][hour] += intensity
            
            # 정규화 및 히트맵 데이터 생성
            days = sorted(hourly_data.keys())[-30:]  # 최근 30일
            hours = list(range(24))
            
            heatmap_data = []
            max_value = 0
            
            for day in days:
                row_data = []
                for hour in hours:
                    if metric == 'pair_frequency':
                        # 페어 발생률 (백분율)
                        total_games = daily_totals.get(day, 1)
                        pair_count = hourly_data[day][hour]
                        value = (pair_count / total_games * 100) if total_games > 0 else 0
                    else:
                        value = hourly_data[day][hour]
                    
                    row_data.append(round(value, 2))
                    max_value = max(max_value, value)
                
                heatmap_data.append({
                    'day': day,
                    'values': row_data
                })
            
            return {
                'type': 'time_heatmap',
                'metric': metric,
                'data': heatmap_data,
                'hours': hours,
                'days': days,
                'max_value': max_value,
                'color_scheme': self.color_schemes['red_blue'],
                'title': self._get_heatmap_title(metric),
                'unit': self._get_metric_unit(metric)
            }
            
        except Exception as e:
            logger.error(f"시간 기반 히트맵 생성 실패: {e}")
            return {}
    
    def generate_table_performance_heatmap(self, game_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """테이블별 성과 히트맵 생성"""
        try:
            # 테이블별 시간대별 데이터 집계
            table_hourly = defaultdict(lambda: defaultdict(lambda: {'games': 0, 'pairs': 0}))
            
            for game in game_data:
                if 'timestamp' not in game:
                    continue
                
                timestamp = pd.to_datetime(game['timestamp'])
                hour = timestamp.hour
                table = game.get('table_name', 'Unknown')
                
                table_hourly[table][hour]['games'] += 1
                if game.get('has_pair', False):
                    table_hourly[table][hour]['pairs'] += 1
            
            # 히트맵 데이터 생성
            tables = sorted(table_hourly.keys())
            hours = list(range(24))
            
            heatmap_data = []
            max_pair_rate = 0
            
            for table in tables:
                row_data = []
                for hour in hours:
                    stats = table_hourly[table][hour]
                    pair_rate = (stats['pairs'] / stats['games'] * 100) if stats['games'] > 0 else 0
                    row_data.append(round(pair_rate, 1))
                    max_pair_rate = max(max_pair_rate, pair_rate)
                
                heatmap_data.append({
                    'table': table,
                    'values': row_data
                })
            
            return {
                'type': 'table_performance_heatmap',
                'data': heatmap_data,
                'tables': tables,
                'hours': hours,
                'max_value': max_pair_rate,
                'color_scheme': self.color_schemes['green_red'],
                'title': '테이블별 시간대별 페어 발생률',
                'unit': '%'
            }
            
        except Exception as e:
            logger.error(f"테이블 성과 히트맵 생성 실패: {e}")
            return {}
    
    def generate_correlation_heatmap(self, features: np.ndarray, 
                                   feature_names: List[str]) -> Dict[str, Any]:
        """특성 상관관계 히트맵 생성"""
        try:
            # 상관관계 매트릭스 계산
            correlation_matrix = np.corrcoef(features.T)
            
            # 히트맵 데이터 생성
            heatmap_data = []
            for i, name_i in enumerate(feature_names):
                row_data = []
                for j, name_j in enumerate(feature_names):
                    correlation = correlation_matrix[i][j]
                    row_data.append(round(correlation, 3))
                
                heatmap_data.append({
                    'feature': name_i,
                    'values': row_data
                })
            
            return {
                'type': 'correlation_heatmap',
                'data': heatmap_data,
                'features': feature_names,
                'title': 'AI 모델 특성 상관관계',
                'color_scheme': self.color_schemes['red_blue'],
                'min_value': -1,
                'max_value': 1,
                'unit': ''
            }
            
        except Exception as e:
            logger.error(f"상관관계 히트맵 생성 실패: {e}")
            return {}
    
    def _get_pair_intensity(self, pair_type: str) -> float:
        """페어 타입별 강도 반환"""
        intensity_map = {
            'PLAYER_PAIR': 1.0,
            'BANKER_PAIR': 1.0,
            'BOTH_PAIR': 2.0,
            'PP': 1.0,
            'BP': 1.0,
            'BOTH': 2.0
        }
        return intensity_map.get(pair_type, 0.5)
    
    def _get_heatmap_title(self, metric: str) -> str:
        """메트릭별 히트맵 제목 반환"""
        titles = {
            'pair_frequency': '시간대별 페어 발생률',
            'game_count': '시간대별 게임 수',
            'pair_intensity': '시간대별 페어 강도'
        }
        return titles.get(metric, '시간대별 분석')
    
    def _get_metric_unit(self, metric: str) -> str:
        """메트릭별 단위 반환"""
        units = {
            'pair_frequency': '%',
            'game_count': '게임',
            'pair_intensity': '강도'
        }
        return units.get(metric, '')


class PatternInsightAnalyzer:
    """패턴 인사이트 분석기"""
    
    def __init__(self):
        self.pattern_cache = {}
        self.insight_templates = {
            'streak_pattern': "연속 {pattern} 패턴이 {frequency:.1f}% 빈도로 발생합니다",
            'time_pattern': "{time_range} 시간대에 페어 발생률이 {rate:.1f}%로 {trend}",
            'table_performance': "{table}에서 가장 {performance} 성과를 보입니다 ({value:.1f}%)",
            'prediction_accuracy': "AI 예측 정확도가 {period}에 {accuracy:.1f}%로 {trend}"
        }
    
    def analyze_sequential_patterns(self, game_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """연속 패턴 분석"""
        try:
            # 게임 결과 시퀀스 생성
            sequences = []
            current_sequence = []
            
            for game in sorted(game_data, key=lambda x: x.get('timestamp', '')):
                result = game.get('result', 'T')
                
                if current_sequence and current_sequence[-1] != result:
                    if len(current_sequence) >= 2:
                        sequences.append({
                            'pattern': current_sequence[0],
                            'length': len(current_sequence)
                        })
                    current_sequence = [result]
                else:
                    current_sequence.append(result)
            
            # 패턴 분석
            pattern_stats = defaultdict(lambda: defaultdict(int))
            for seq in sequences:
                pattern_stats[seq['pattern']][seq['length']] += 1
            
            # 인사이트 생성
            insights = []
            total_sequences = len(sequences)
            
            for pattern, lengths in pattern_stats.items():
                for length, count in lengths.items():
                    if length >= 3 and count >= 3:  # 3회 이상 연속, 3번 이상 발생
                        frequency = (count / total_sequences) * 100
                        insight = {
                            'type': 'streak_pattern',
                            'pattern': f"{length}회 연속 {pattern}",
                            'frequency': frequency,
                            'count': count,
                            'significance': 'high' if frequency > 5 else 'medium' if frequency > 2 else 'low',
                            'message': self.insight_templates['streak_pattern'].format(
                                pattern=f"{length}회 연속 {pattern}",
                                frequency=frequency
                            )
                        }
                        insights.append(insight)
            
            return {
                'type': 'sequential_patterns',
                'insights': insights,
                'total_sequences': total_sequences,
                'pattern_distribution': dict(pattern_stats)
            }
            
        except Exception as e:
            logger.error(f"연속 패턴 분석 실패: {e}")
            return {}
    
    def analyze_time_patterns(self, game_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """시간 패턴 분석"""
        try:
            # 시간대별 페어 발생률 계산
            hourly_stats = defaultdict(lambda: {'games': 0, 'pairs': 0})
            
            for game in game_data:
                if 'timestamp' not in game:
                    continue
                
                timestamp = pd.to_datetime(game['timestamp'])
                hour = timestamp.hour
                
                hourly_stats[hour]['games'] += 1
                if game.get('has_pair', False):
                    hourly_stats[hour]['pairs'] += 1
            
            # 시간대별 페어 발생률
            hourly_rates = {}
            for hour, stats in hourly_stats.items():
                rate = (stats['pairs'] / stats['games'] * 100) if stats['games'] > 0 else 0
                hourly_rates[hour] = rate
            
            # 인사이트 생성
            insights = []
            
            if hourly_rates:
                # 최고/최저 시간대
                best_hour = max(hourly_rates.items(), key=lambda x: x[1])
                worst_hour = min(hourly_rates.items(), key=lambda x: x[1])
                avg_rate = sum(hourly_rates.values()) / len(hourly_rates)
                
                # 최고 시간대 인사이트
                if best_hour[1] > avg_rate * 1.2:
                    insights.append({
                        'type': 'time_pattern',
                        'time_range': f"{best_hour[0]:02d}:00-{best_hour[0]+1:02d}:00",
                        'rate': best_hour[1],
                        'trend': '높습니다',
                        'significance': 'high',
                        'message': self.insight_templates['time_pattern'].format(
                            time_range=f"{best_hour[0]:02d}시",
                            rate=best_hour[1],
                            trend='높습니다'
                        )
                    })
                
                # 최저 시간대 인사이트
                if worst_hour[1] < avg_rate * 0.8:
                    insights.append({
                        'type': 'time_pattern',
                        'time_range': f"{worst_hour[0]:02d}:00-{worst_hour[0]+1:02d}:00",
                        'rate': worst_hour[1],
                        'trend': '낮습니다',
                        'significance': 'medium',
                        'message': self.insight_templates['time_pattern'].format(
                            time_range=f"{worst_hour[0]:02d}시",
                            rate=worst_hour[1],
                            trend='낮습니다'
                        )
                    })
            
            return {
                'type': 'time_patterns',
                'insights': insights,
                'hourly_rates': hourly_rates,
                'peak_hours': sorted(hourly_rates.items(), key=lambda x: x[1], reverse=True)[:3]
            }
            
        except Exception as e:
            logger.error(f"시간 패턴 분석 실패: {e}")
            return {}
    
    def analyze_table_patterns(self, game_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """테이블 패턴 분석"""
        try:
            # 테이블별 통계 계산
            table_stats = defaultdict(lambda: {'games': 0, 'pairs': 0, 'pair_types': Counter()})
            
            for game in game_data:
                table = game.get('table_name', 'Unknown')
                table_stats[table]['games'] += 1
                
                if game.get('has_pair', False):
                    table_stats[table]['pairs'] += 1
                    pair_type = game.get('pair_type', 'UNKNOWN')
                    table_stats[table]['pair_types'][pair_type] += 1
            
            # 테이블별 페어 발생률 계산
            table_rates = {}
            for table, stats in table_stats.items():
                rate = (stats['pairs'] / stats['games'] * 100) if stats['games'] > 0 else 0
                table_rates[table] = rate
            
            # 인사이트 생성
            insights = []
            
            if table_rates:
                # 최고 성과 테이블
                best_table = max(table_rates.items(), key=lambda x: x[1])
                worst_table = min(table_rates.items(), key=lambda x: x[1])
                
                if len(table_rates) > 1:
                    insights.append({
                        'type': 'table_performance',
                        'table': best_table[0],
                        'performance': '높은',
                        'value': best_table[1],
                        'significance': 'high',
                        'message': self.insight_templates['table_performance'].format(
                            table=best_table[0],
                            performance='높은',
                            value=best_table[1]
                        )
                    })
                    
                    insights.append({
                        'type': 'table_performance',
                        'table': worst_table[0],
                        'performance': '낮은',
                        'value': worst_table[1],
                        'significance': 'medium',
                        'message': self.insight_templates['table_performance'].format(
                            table=worst_table[0],
                            performance='낮은',
                            value=worst_table[1]
                        )
                    })
            
            return {
                'type': 'table_patterns',
                'insights': insights,
                'table_rates': table_rates,
                'table_rankings': sorted(table_rates.items(), key=lambda x: x[1], reverse=True),
                'detailed_stats': dict(table_stats)
            }
            
        except Exception as e:
            logger.error(f"테이블 패턴 분석 실패: {e}")
            return {}
    
    def generate_comprehensive_insights(self, game_data: List[Dict[str, Any]], 
                                      prediction_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """종합 인사이트 생성"""
        try:
            all_insights = []
            
            # 각종 패턴 분석
            sequential_analysis = self.analyze_sequential_patterns(game_data)
            time_analysis = self.analyze_time_patterns(game_data)
            table_analysis = self.analyze_table_patterns(game_data)
            
            # 인사이트 수집
            if sequential_analysis.get('insights'):
                all_insights.extend(sequential_analysis['insights'])
            
            if time_analysis.get('insights'):
                all_insights.extend(time_analysis['insights'])
            
            if table_analysis.get('insights'):
                all_insights.extend(table_analysis['insights'])
            
            # 예측 정확도 분석 (데이터가 있는 경우)
            if prediction_data:
                prediction_insights = self._analyze_prediction_accuracy(prediction_data)
                all_insights.extend(prediction_insights)
            
            # 중요도별 정렬
            significance_order = {'high': 3, 'medium': 2, 'low': 1}
            all_insights.sort(key=lambda x: significance_order.get(x.get('significance', 'low'), 1), 
                            reverse=True)
            
            # 요약 통계
            total_games = len(game_data)
            total_pairs = sum(1 for game in game_data if game.get('has_pair', False))
            overall_pair_rate = (total_pairs / total_games * 100) if total_games > 0 else 0
            
            return {
                'timestamp': datetime.now().isoformat(),
                'insights': all_insights[:10],  # 상위 10개 인사이트
                'summary': {
                    'total_games': total_games,
                    'total_pairs': total_pairs,
                    'overall_pair_rate': round(overall_pair_rate, 2),
                    'analysis_period': self._get_analysis_period(game_data),
                    'insight_count': len(all_insights)
                },
                'detailed_analyses': {
                    'sequential': sequential_analysis,
                    'time': time_analysis,
                    'table': table_analysis
                }
            }
            
        except Exception as e:
            logger.error(f"종합 인사이트 생성 실패: {e}")
            return {}
    
    def _analyze_prediction_accuracy(self, prediction_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """예측 정확도 분석"""
        insights = []
        
        try:
            if not prediction_data:
                return insights
            
            # 최근 예측 정확도 계산
            recent_predictions = prediction_data[-100:]  # 최근 100개
            correct_predictions = sum(1 for pred in recent_predictions 
                                    if pred.get('is_correct', False))
            
            if recent_predictions:
                accuracy = (correct_predictions / len(recent_predictions)) * 100
                
                # 정확도 트렌드 분석
                if len(prediction_data) >= 200:
                    older_predictions = prediction_data[-200:-100]
                    older_correct = sum(1 for pred in older_predictions 
                                      if pred.get('is_correct', False))
                    older_accuracy = (older_correct / len(older_predictions)) * 100
                    
                    trend = '향상되었습니다' if accuracy > older_accuracy else '감소했습니다'
                    significance = 'high' if abs(accuracy - older_accuracy) > 5 else 'medium'
                    
                    insights.append({
                        'type': 'prediction_accuracy',
                        'period': '최근 100회 예측',
                        'accuracy': accuracy,
                        'trend': trend,
                        'significance': significance,
                        'message': self.insight_templates['prediction_accuracy'].format(
                            period='최근',
                            accuracy=accuracy,
                            trend=trend
                        )
                    })
            
        except Exception as e:
            logger.error(f"예측 정확도 분석 실패: {e}")
        
        return insights
    
    def _get_analysis_period(self, game_data: List[Dict[str, Any]]) -> str:
        """분석 기간 반환"""
        if not game_data:
            return "데이터 없음"
        
        try:
            timestamps = [pd.to_datetime(game['timestamp']) 
                         for game in game_data if 'timestamp' in game]
            
            if not timestamps:
                return "시간 정보 없음"
            
            start_time = min(timestamps)
            end_time = max(timestamps)
            period = (end_time - start_time).days
            
            return f"{period}일간"
            
        except Exception:
            return "기간 계산 실패"


class PredictionAccuracyAnalyzer:
    """예측 정확도 분석기"""
    
    def __init__(self):
        self.accuracy_history = []
    
    def analyze_prediction_performance(self, prediction_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """예측 성능 분석"""
        try:
            if not prediction_data:
                return {'error': '예측 데이터가 없습니다'}
            
            # 전체 통계
            total_predictions = len(prediction_data)
            correct_predictions = sum(1 for pred in prediction_data 
                                    if pred.get('is_correct', False))
            overall_accuracy = (correct_predictions / total_predictions) * 100
            
            # 신뢰도별 정확도
            confidence_accuracy = self._analyze_confidence_accuracy(prediction_data)
            
            # 시간대별 정확도
            hourly_accuracy = self._analyze_hourly_accuracy(prediction_data)
            
            # 페어 타입별 정확도
            pair_type_accuracy = self._analyze_pair_type_accuracy(prediction_data)
            
            # 최근 트렌드
            trend_analysis = self._analyze_accuracy_trend(prediction_data)
            
            return {
                'overall_statistics': {
                    'total_predictions': total_predictions,
                    'correct_predictions': correct_predictions,
                    'overall_accuracy': round(overall_accuracy, 2),
                    'performance_grade': self._get_performance_grade(overall_accuracy)
                },
                'confidence_analysis': confidence_accuracy,
                'hourly_analysis': hourly_accuracy,
                'pair_type_analysis': pair_type_accuracy,
                'trend_analysis': trend_analysis,
                'recommendations': self._generate_recommendations(
                    overall_accuracy, confidence_accuracy, trend_analysis
                )
            }
            
        except Exception as e:
            logger.error(f"예측 성능 분석 실패: {e}")
            return {'error': str(e)}
    
    def _analyze_confidence_accuracy(self, prediction_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """신뢰도별 정확도 분석"""
        confidence_buckets = defaultdict(lambda: {'total': 0, 'correct': 0})
        
        for pred in prediction_data:
            confidence = pred.get('confidence', 0)
            bucket = self._get_confidence_bucket(confidence)
            
            confidence_buckets[bucket]['total'] += 1
            if pred.get('is_correct', False):
                confidence_buckets[bucket]['correct'] += 1
        
        # 정확도 계산
        confidence_results = {}
        for bucket, stats in confidence_buckets.items():
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            confidence_results[bucket] = {
                'accuracy': round(accuracy, 1),
                'predictions': stats['total'],
                'correct': stats['correct']
            }
        
        return confidence_results
    
    def _analyze_hourly_accuracy(self, prediction_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """시간대별 정확도 분석"""
        hourly_stats = defaultdict(lambda: {'total': 0, 'correct': 0})
        
        for pred in prediction_data:
            if 'timestamp' not in pred:
                continue
            
            try:
                timestamp = pd.to_datetime(pred['timestamp'])
                hour = timestamp.hour
                
                hourly_stats[hour]['total'] += 1
                if pred.get('is_correct', False):
                    hourly_stats[hour]['correct'] += 1
                    
            except Exception:
                continue
        
        # 시간대별 정확도
        hourly_results = {}
        for hour, stats in hourly_stats.items():
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            hourly_results[hour] = {
                'accuracy': round(accuracy, 1),
                'predictions': stats['total']
            }
        
        return hourly_results
    
    def _analyze_pair_type_accuracy(self, prediction_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """페어 타입별 정확도 분석"""
        type_stats = defaultdict(lambda: {'total': 0, 'correct': 0})
        
        for pred in prediction_data:
            predicted_type = pred.get('predicted_pair_type', 'NO_PAIR')
            
            type_stats[predicted_type]['total'] += 1
            if pred.get('is_correct', False):
                type_stats[predicted_type]['correct'] += 1
        
        # 타입별 정확도
        type_results = {}
        for pair_type, stats in type_stats.items():
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            type_results[pair_type] = {
                'accuracy': round(accuracy, 1),
                'predictions': stats['total'],
                'correct': stats['correct']
            }
        
        return type_results
    
    def _analyze_accuracy_trend(self, prediction_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """정확도 트렌드 분석"""
        # 시간순 정렬
        sorted_data = sorted(prediction_data, 
                           key=lambda x: x.get('timestamp', ''))
        
        # 구간별 정확도 계산
        segment_size = max(50, len(sorted_data) // 10)  # 최소 50개씩
        segments = []
        
        for i in range(0, len(sorted_data), segment_size):
            segment = sorted_data[i:i+segment_size]
            correct = sum(1 for pred in segment if pred.get('is_correct', False))
            accuracy = (correct / len(segment) * 100) if segment else 0
            
            segments.append({
                'start_index': i,
                'end_index': i + len(segment),
                'accuracy': round(accuracy, 1),
                'predictions': len(segment)
            })
        
        # 트렌드 계산
        if len(segments) >= 2:
            recent_accuracy = segments[-1]['accuracy']
            older_accuracy = segments[0]['accuracy']
            trend = 'improving' if recent_accuracy > older_accuracy else 'declining' if recent_accuracy < older_accuracy else 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'segments': segments,
            'trend': trend,
            'improvement_rate': segments[-1]['accuracy'] - segments[0]['accuracy'] if len(segments) >= 2 else 0
        }
    
    def _get_confidence_bucket(self, confidence: float) -> str:
        """신뢰도 구간 반환"""
        if confidence >= 0.9:
            return 'very_high'
        elif confidence >= 0.8:
            return 'high'
        elif confidence >= 0.7:
            return 'medium'
        elif confidence >= 0.6:
            return 'low'
        else:
            return 'very_low'
    
    def _get_performance_grade(self, accuracy: float) -> str:
        """성능 등급 반환"""
        if accuracy >= 90:
            return 'excellent'
        elif accuracy >= 80:
            return 'good'
        elif accuracy >= 70:
            return 'fair'
        elif accuracy >= 60:
            return 'poor'
        else:
            return 'very_poor'
    
    def _generate_recommendations(self, overall_accuracy: float,
                                confidence_accuracy: Dict[str, Any],
                                trend_analysis: Dict[str, Any]) -> List[str]:
        """개선 권장사항 생성"""
        recommendations = []
        
        # 전체 정확도 기반 권장사항
        if overall_accuracy < 70:
            recommendations.append("전체 예측 정확도가 낮습니다. 모델 재훈련을 고려하세요.")
        elif overall_accuracy < 80:
            recommendations.append("예측 정확도 향상을 위해 추가 특성을 고려해보세요.")
        
        # 신뢰도 분석 기반 권장사항
        if confidence_accuracy:
            high_conf_acc = confidence_accuracy.get('high', {}).get('accuracy', 0)
            low_conf_acc = confidence_accuracy.get('low', {}).get('accuracy', 0)
            
            if high_conf_acc < 80:
                recommendations.append("고신뢰도 예측의 정확도가 낮습니다. 신뢰도 계산 방식을 검토하세요.")
            
            if low_conf_acc > high_conf_acc:
                recommendations.append("신뢰도와 정확도의 상관관계를 재검토하세요.")
        
        # 트렌드 분석 기반 권장사항
        if trend_analysis.get('trend') == 'declining':
            recommendations.append("예측 정확도가 감소 추세입니다. 모델 성능 점검이 필요합니다.")
        elif trend_analysis.get('trend') == 'improving':
            recommendations.append("예측 정확도가 향상되고 있습니다. 현재 설정을 유지하세요.")
        
        return recommendations


class AdvancedAnalyticsEngine:
    """고급 분석 엔진 통합 클래스"""
    
    def __init__(self):
        self.heatmap_generator = HeatmapGenerator()
        self.pattern_analyzer = PatternInsightAnalyzer()
        self.prediction_analyzer = PredictionAccuracyAnalyzer()
        
        safe_print("📈 고급 분석 엔진 초기화 완료")
    
    def generate_comprehensive_analysis(self, game_data: List[Dict[str, Any]], 
                                      prediction_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """종합 분석 보고서 생성"""
        try:
            analysis_start = datetime.now()
            
            # 히트맵 생성
            time_heatmap = self.heatmap_generator.generate_time_based_heatmap(game_data, 'pair_frequency')
            table_heatmap = self.heatmap_generator.generate_table_performance_heatmap(game_data)
            
            # 패턴 인사이트
            insights = self.pattern_analyzer.generate_comprehensive_insights(game_data, prediction_data)
            
            # 예측 정확도 분석
            prediction_analysis = {}
            if prediction_data:
                prediction_analysis = self.prediction_analyzer.analyze_prediction_performance(prediction_data)
            
            analysis_duration = (datetime.now() - analysis_start).total_seconds()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'analysis_duration': round(analysis_duration, 2),
                'data_summary': {
                    'game_count': len(game_data),
                    'prediction_count': len(prediction_data) if prediction_data else 0,
                    'analysis_period': self.pattern_analyzer._get_analysis_period(game_data)
                },
                'heatmaps': {
                    'time_based': time_heatmap,
                    'table_performance': table_heatmap
                },
                'insights': insights,
                'prediction_analysis': prediction_analysis,
                'recommendations': self._generate_overall_recommendations(insights, prediction_analysis)
            }
            
        except Exception as e:
            logger.error(f"종합 분석 실패: {e}")
            return {'error': str(e)}
    
    def _generate_overall_recommendations(self, insights: Dict[str, Any], 
                                        prediction_analysis: Dict[str, Any]) -> List[str]:
        """전체 권장사항 생성"""
        recommendations = []
        
        # 인사이트 기반 권장사항
        high_significance_insights = [
            insight for insight in insights.get('insights', [])
            if insight.get('significance') == 'high'
        ]
        
        if len(high_significance_insights) >= 3:
            recommendations.append("중요한 패턴이 여러 개 발견되었습니다. 전략 조정을 고려하세요.")
        
        # 예측 성능 기반 권장사항
        if prediction_analysis and 'recommendations' in prediction_analysis:
            recommendations.extend(prediction_analysis['recommendations'])
        
        return recommendations


# 전역 인스턴스
advanced_analytics = AdvancedAnalyticsEngine()

def get_advanced_analytics() -> AdvancedAnalyticsEngine:
    """고급 분석 엔진 인스턴스 반환"""
    return advanced_analytics


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== 고급 분석 도구 테스트 ===")
    
    import random
    from datetime import datetime, timedelta
    
    # 더미 게임 데이터 생성
    dummy_games = []
    start_time = datetime.now() - timedelta(days=7)
    
    for i in range(1000):
        game_time = start_time + timedelta(minutes=random.randint(1, 60))
        has_pair = random.random() < 0.15  # 15% 페어 확률
        
        dummy_game = {
            'table_name': random.choice(['테이블_A', '테이블_B', 'VIP_테이블']),
            'game_id': i + 1,
            'timestamp': game_time.isoformat(),
            'result': random.choice(['P', 'B', 'T']),
            'has_pair': has_pair,
            'pair_type': random.choice(['PLAYER_PAIR', 'BANKER_PAIR']) if has_pair else None
        }
        dummy_games.append(dummy_game)
    
    safe_print(f"📊 {len(dummy_games)}개 더미 게임 데이터 생성")
    
    # 분석 엔진 테스트
    engine = AdvancedAnalyticsEngine()
    
    # 히트맵 생성 테스트
    heatmap = engine.heatmap_generator.generate_time_based_heatmap(dummy_games)
    safe_print(f"📈 히트맵 생성: {heatmap.get('type', '실패')}")
    
    # 패턴 분석 테스트
    insights = engine.pattern_analyzer.generate_comprehensive_insights(dummy_games)
    safe_print(f"💡 인사이트 {len(insights.get('insights', []))}개 생성")
    
    # 종합 분석 테스트
    analysis = engine.generate_comprehensive_analysis(dummy_games)
    safe_print(f"🎯 종합 분석 완료 (소요시간: {analysis.get('analysis_duration', 0)}초)")
    
    safe_print("🎯 고급 분석 도구 테스트 완료!")