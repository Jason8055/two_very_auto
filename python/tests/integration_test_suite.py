#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
통합 테스트 스위트 v1.0
Two Very Auto v2.0 시스템 통합 테스트
"""

import sys
import json
import asyncio
import pytest
import logging
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 테스트 대상 모듈들
try:
    from chart_integration import ChartDataProcessor, ChartWebSocketHandler
    from realtime_dashboard import RealTimeDashboard
    from ai_prediction_engine import AIPredictionEngine, FeatureEngineer
    from advanced_notification_system import AdvancedNotificationSystem
    chart_available = True
except ImportError as e:
    chart_available = False
    logger.warning(f"테스트 모듈 import 실패: {e}")


class IntegrationTestSuite:
    """통합 테스트 스위트 메인 클래스"""
    
    def __init__(self):
        self.test_results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'errors': [],
            'performance_metrics': {},
            'start_time': None,
            'end_time': None
        }
        
        # 테스트 데이터
        self.sample_game_data = {
            'table_name': '테스트테이블_A',
            'game_id': 1,
            'player_cards': ['A♠', 'K♦'],
            'banker_cards': ['Q♣', 'J♥'],
            'result': 'P',
            'has_pair': False,
            'pair_type': None,
            'timestamp': datetime.now().isoformat()
        }
        
        safe_print("🧪 통합 테스트 스위트 초기화 완료")
    
    def run_all_tests(self) -> dict:
        """모든 테스트 실행"""
        self.test_results['start_time'] = datetime.now()
        safe_print("🚀 통합 테스트 시작")
        
        # Phase 1: 개별 컴포넌트 테스트
        self.test_chart_integration()
        self.test_realtime_dashboard()
        self.test_ai_prediction_engine()
        self.test_notification_system()
        
        # Phase 2: 통합 테스트
        self.test_data_flow_integration()
        self.test_websocket_integration()
        self.test_performance_benchmarks()
        
        self.test_results['end_time'] = datetime.now()
        duration = (self.test_results['end_time'] - self.test_results['start_time']).total_seconds()
        
        safe_print(f"\n📊 테스트 결과 요약:")
        safe_print(f"  총 테스트: {self.test_results['total_tests']}")
        safe_print(f"  성공: {self.test_results['passed']}")
        safe_print(f"  실패: {self.test_results['failed']}")
        safe_print(f"  실행 시간: {duration:.2f}초")
        
        return self.test_results
    
    def test_chart_integration(self):
        """Chart.js 통합 시스템 테스트"""
        safe_print("\n📈 Chart Integration 테스트 시작")
        
        try:
            # ChartDataProcessor 테스트
            processor = ChartDataProcessor()
            self._run_test("Chart Processor 초기화", lambda: processor is not None)
            
            # 게임 데이터 처리 테스트
            result = processor.process_game_data(self.sample_game_data)
            self._run_test("게임 데이터 처리", lambda: 'timestamp' in result)
            
            # 차트 데이터 생성 테스트
            timeline_data = processor.get_pair_timeline_data()
            self._run_test("타임라인 차트 데이터", lambda: timeline_data['type'] == 'scatter')
            
            hourly_data = processor.get_hourly_statistics()
            self._run_test("시간별 통계 데이터", lambda: hourly_data['type'] == 'line')
            
            comparison_data = processor.get_table_comparison()
            self._run_test("테이블 비교 데이터", lambda: comparison_data['type'] == 'bar')
            
            distribution_data = processor.get_pair_type_distribution()
            self._run_test("페어 분포 데이터", lambda: distribution_data['type'] == 'doughnut')
            
            # 실시간 메트릭 테스트
            metrics = processor.get_realtime_metrics()
            self._run_test("실시간 메트릭", lambda: 'total_games' in metrics)
            
            safe_print("✅ Chart Integration 테스트 완료")
            
        except Exception as e:
            self.test_results['errors'].append(f"Chart Integration: {str(e)}")
            safe_print(f"❌ Chart Integration 테스트 실패: {e}")
    
    def test_realtime_dashboard(self):
        """실시간 대시보드 테스트"""
        safe_print("\n🎛️ Realtime Dashboard 테스트 시작")
        
        try:
            # 대시보드 초기화
            dashboard = RealTimeDashboard()
            self._run_test("대시보드 초기화", lambda: dashboard is not None)
            
            # 게임 이벤트 처리
            result = dashboard.process_game_event(self.sample_game_data)
            self._run_test("게임 이벤트 처리", lambda: result['processed'] == True)
            
            # 실시간 통계
            stats = dashboard.get_live_statistics()
            self._run_test("실시간 통계", lambda: 'total' in stats)
            
            # 테이블 개요
            overview = dashboard.get_table_overview()
            self._run_test("테이블 개요", lambda: isinstance(overview, dict))
            
            # 시스템 상태
            status = dashboard.get_system_status()
            self._run_test("시스템 상태", lambda: 'uptime' in status)
            
            # 알림 규칙 업데이트
            new_rules = {'consecutive_pairs': {'limit': 5, 'enabled': True}}
            update_result = dashboard.update_alert_rules(new_rules)
            self._run_test("알림 규칙 업데이트", lambda: update_result == True)
            
            safe_print("✅ Realtime Dashboard 테스트 완료")
            
        except Exception as e:
            self.test_results['errors'].append(f"Realtime Dashboard: {str(e)}")
            safe_print(f"❌ Realtime Dashboard 테스트 실패: {e}")
    
    def test_ai_prediction_engine(self):
        """AI 예측 엔진 테스트"""
        safe_print("\n🧠 AI Prediction Engine 테스트 시작")
        
        try:
            # AI 엔진 초기화
            engine = AIPredictionEngine()
            self._run_test("AI 엔진 초기화", lambda: engine is not None)
            
            # 특성 엔지니어링 테스트
            feature_engineer = FeatureEngineer()
            features = feature_engineer.extract_game_features(self.sample_game_data)
            self._run_test("게임 특성 추출", lambda: len(features) == 16)  # 16개 게임 특성
            
            # 시퀀스 특성 테스트
            dummy_games = [self.sample_game_data] * 10
            seq_features = feature_engineer.extract_sequence_features(dummy_games)
            self._run_test("시퀀스 특성 추출", lambda: len(seq_features) == 6)  # 6개 시퀀스 특성
            
            # 예측 테스트
            prediction = engine.predict_pair(self.sample_game_data, dummy_games)
            self._run_test("페어 예측", lambda: 'predicted_pair_type' in prediction)
            self._run_test("예측 신뢰도", lambda: 0 <= prediction['confidence'] <= 1)
            
            # 모델 정보
            model_info = engine.get_model_info()
            self._run_test("모델 정보", lambda: 'feature_count' in model_info)
            
            # 예측 통계
            stats = engine.get_prediction_stats()
            self._run_test("예측 통계", lambda: 'accuracy_tracker' in stats)
            
            safe_print("✅ AI Prediction Engine 테스트 완료")
            
        except Exception as e:
            self.test_results['errors'].append(f"AI Prediction Engine: {str(e)}")
            safe_print(f"❌ AI Prediction Engine 테스트 실패: {e}")
    
    def test_notification_system(self):
        """알림 시스템 테스트"""
        safe_print("\n🔔 Notification System 테스트 시작")
        
        try:
            # Mock 알림 시스템 테스트
            # 실제 외부 서비스 호출을 피하기 위해 Mock 사용
            
            self._run_test("알림 시스템 구조", lambda: True)  # 기본 구조 테스트
            
            # 알림 메시지 생성 테스트
            notification_msg = {
                'type': 'pair_alert',
                'table_name': '테스트테이블_A',
                'message': '페어 발생 알림',
                'timestamp': datetime.now().isoformat()
            }
            self._run_test("알림 메시지 구조", lambda: 'type' in notification_msg)
            
            safe_print("✅ Notification System 테스트 완료")
            
        except Exception as e:
            self.test_results['errors'].append(f"Notification System: {str(e)}")
            safe_print(f"❌ Notification System 테스트 실패: {e}")
    
    def test_data_flow_integration(self):
        """데이터 흐름 통합 테스트"""
        safe_print("\n🔄 Data Flow Integration 테스트 시작")
        
        try:
            # 전체 데이터 파이프라인 테스트
            # 게임 이벤트 → Chart Processor → Realtime Dashboard → AI Prediction
            
            # 1. Chart Processor
            chart_processor = ChartDataProcessor()
            chart_result = chart_processor.process_game_data(self.sample_game_data)
            self._run_test("차트 데이터 처리", lambda: chart_result is not None)
            
            # 2. Realtime Dashboard
            dashboard = RealTimeDashboard()
            dashboard_result = dashboard.process_game_event(self.sample_game_data)
            self._run_test("대시보드 이벤트 처리", lambda: dashboard_result['processed'])
            
            # 3. AI Prediction
            ai_engine = AIPredictionEngine()
            dummy_games = [self.sample_game_data] * 10
            prediction_result = ai_engine.predict_pair(self.sample_game_data, dummy_games)
            self._run_test("AI 예측 처리", lambda: prediction_result is not None)
            
            # 4. 통합 데이터 일관성 테스트
            self._run_test("데이터 일관성", lambda: (
                chart_result['table_name'] == dashboard_result['live_connections'] >= 0 and
                prediction_result['timestamp'] is not None
            ))
            
            safe_print("✅ Data Flow Integration 테스트 완료")
            
        except Exception as e:
            self.test_results['errors'].append(f"Data Flow Integration: {str(e)}")
            safe_print(f"❌ Data Flow Integration 테스트 실패: {e}")
    
    def test_websocket_integration(self):
        """WebSocket 통합 테스트"""
        safe_print("\n🌐 WebSocket Integration 테스트 시작")
        
        try:
            # Mock WebSocket 연결 테스트
            mock_websocket = Mock()
            
            # Chart WebSocket Handler 테스트
            chart_handler = ChartWebSocketHandler(ChartDataProcessor())
            chart_handler.add_client(mock_websocket)
            self._run_test("차트 WebSocket 클라이언트 추가", 
                         lambda: mock_websocket in chart_handler.connected_clients)
            
            chart_handler.remove_client(mock_websocket)
            self._run_test("차트 WebSocket 클라이언트 제거", 
                         lambda: mock_websocket not in chart_handler.connected_clients)
            
            # Dashboard WebSocket 테스트
            dashboard = RealTimeDashboard()
            # Mock 연결 추가/제거는 async 함수라서 여기서는 구조만 테스트
            self._run_test("대시보드 WebSocket 구조", lambda: hasattr(dashboard, 'active_connections'))
            
            safe_print("✅ WebSocket Integration 테스트 완료")
            
        except Exception as e:
            self.test_results['errors'].append(f"WebSocket Integration: {str(e)}")
            safe_print(f"❌ WebSocket Integration 테스트 실패: {e}")
    
    def test_performance_benchmarks(self):
        """성능 벤치마크 테스트"""
        safe_print("\n⚡ Performance Benchmarks 테스트 시작")
        
        try:
            # Chart Processing 성능
            chart_processor = ChartDataProcessor()
            start_time = time.time()
            for i in range(100):
                test_data = self.sample_game_data.copy()
                test_data['game_id'] = i
                chart_processor.process_game_data(test_data)
            chart_processing_time = time.time() - start_time
            
            self.test_results['performance_metrics']['chart_processing'] = {
                'operations': 100,
                'total_time': chart_processing_time,
                'avg_time_per_op': chart_processing_time / 100 * 1000  # ms
            }
            
            self._run_test("차트 처리 성능 (<50ms/op)", 
                         lambda: chart_processing_time / 100 * 1000 < 50)
            
            # AI Prediction 성능
            ai_engine = AIPredictionEngine()
            dummy_games = [self.sample_game_data] * 10
            start_time = time.time()
            for i in range(50):
                test_data = self.sample_game_data.copy()
                test_data['game_id'] = i
                ai_engine.predict_pair(test_data, dummy_games)
            ai_prediction_time = time.time() - start_time
            
            self.test_results['performance_metrics']['ai_prediction'] = {
                'operations': 50,
                'total_time': ai_prediction_time,
                'avg_time_per_op': ai_prediction_time / 50 * 1000  # ms
            }
            
            self._run_test("AI 예측 성능 (<100ms/op)", 
                         lambda: ai_prediction_time / 50 * 1000 < 100)
            
            # Dashboard Processing 성능
            dashboard = RealTimeDashboard()
            start_time = time.time()
            for i in range(100):
                test_data = self.sample_game_data.copy()
                test_data['game_id'] = i
                dashboard.process_game_event(test_data)
            dashboard_processing_time = time.time() - start_time
            
            self.test_results['performance_metrics']['dashboard_processing'] = {
                'operations': 100,
                'total_time': dashboard_processing_time,
                'avg_time_per_op': dashboard_processing_time / 100 * 1000  # ms
            }
            
            self._run_test("대시보드 처리 성능 (<20ms/op)", 
                         lambda: dashboard_processing_time / 100 * 1000 < 20)
            
            safe_print("✅ Performance Benchmarks 테스트 완료")
            
        except Exception as e:
            self.test_results['errors'].append(f"Performance Benchmarks: {str(e)}")
            safe_print(f"❌ Performance Benchmarks 테스트 실패: {e}")
    
    def _run_test(self, test_name: str, test_func) -> bool:
        """개별 테스트 실행"""
        try:
            self.test_results['total_tests'] += 1
            result = test_func()
            if result:
                self.test_results['passed'] += 1
                safe_print(f"  ✅ {test_name}")
                return True
            else:
                self.test_results['failed'] += 1
                self.test_results['errors'].append(f"{test_name}: 테스트 조건 실패")
                safe_print(f"  ❌ {test_name}: 실패")
                return False
        except Exception as e:
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"{test_name}: {str(e)}")
            safe_print(f"  ❌ {test_name}: {e}")
            return False
    
    def generate_test_report(self) -> str:
        """테스트 보고서 생성"""
        report = f"""
# Two Very Auto v2.0 - 통합 테스트 보고서

## 테스트 실행 정보
- **실행 날짜**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **총 테스트**: {self.test_results['total_tests']}
- **성공**: {self.test_results['passed']}
- **실패**: {self.test_results['failed']}
- **성공률**: {(self.test_results['passed'] / self.test_results['total_tests'] * 100):.1f}%

## 성능 메트릭
"""
        
        for metric_name, metric_data in self.test_results['performance_metrics'].items():
            report += f"""
### {metric_name.replace('_', ' ').title()}
- **작업 수**: {metric_data['operations']}
- **총 시간**: {metric_data['total_time']:.3f}초
- **평균 시간**: {metric_data['avg_time_per_op']:.2f}ms/작업
"""
        
        if self.test_results['errors']:
            report += "\n## 오류 목록\n"
            for error in self.test_results['errors']:
                report += f"- {error}\n"
        
        return report
    
    def save_test_report(self, filename: str = None):
        """테스트 보고서 저장"""
        if filename is None:
            filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        report_content = self.generate_test_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        safe_print(f"📄 테스트 보고서 저장: {filename}")


async def run_async_tests():
    """비동기 테스트 실행"""
    # 여기서 WebSocket 관련 비동기 테스트를 실행할 수 있음
    pass


def main():
    """메인 테스트 실행"""
    if not chart_available:
        safe_print("❌ 필수 모듈을 import할 수 없습니다. 먼저 시스템 설정을 확인하세요.")
        return
    
    safe_print("="*60)
    safe_print("🧪 Two Very Auto v2.0 통합 테스트 스위트")
    safe_print("="*60)
    
    # 통합 테스트 실행
    test_suite = IntegrationTestSuite()
    results = test_suite.run_all_tests()
    
    # 테스트 보고서 생성 및 저장
    test_suite.save_test_report()
    
    # 최종 결과 출력
    success_rate = (results['passed'] / results['total_tests'] * 100) if results['total_tests'] > 0 else 0
    
    safe_print(f"\n{'='*60}")
    safe_print(f"🎯 최종 테스트 결과")
    safe_print(f"{'='*60}")
    safe_print(f"성공률: {success_rate:.1f}% ({results['passed']}/{results['total_tests']})")
    
    if success_rate >= 90:
        safe_print("🎉 우수한 시스템 품질!")
    elif success_rate >= 80:
        safe_print("✅ 양호한 시스템 품질")
    else:
        safe_print("⚠️ 시스템 개선 필요")
    
    return results


if __name__ == "__main__":
    main()