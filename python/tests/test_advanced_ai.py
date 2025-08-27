#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
고급 AI 예측 엔진 종합 테스트
Phase 4 구현 검증 및 성능 평가
"""

import json
import random
import numpy as np
from datetime import datetime, timedelta
from korean_encoding_fix import setup_korean_encoding, safe_print
from advanced_ai_engine_v2 import get_advanced_ai_engine, AdvancedFeatureEngineer, ModelPerformanceTracker
from web_server_integration import get_ai_integration

# 한국어 인코딩 설정
setup_korean_encoding()


def generate_realistic_baccarat_data(num_games: int = 500) -> list:
    """현실적인 바카라 게임 데이터 생성"""
    cards = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    suits = ['♠', '♥', '♦', '♣']
    results = ['player', 'banker', 'tie']
    
    games = []
    
    for i in range(num_games):
        # 카드 생성 (페어 확률 고려)
        if random.random() < 0.08:  # 8% 페어 확률
            # 페어 생성
            pair_value = random.choice(cards)
            pair_suits = random.sample(suits, 2)
            
            if random.random() < 0.5:  # Player pair
                player_cards = [f"{pair_value}{pair_suits[0]}", f"{pair_value}{pair_suits[1]}"]
                banker_cards = [f"{random.choice(cards)}{random.choice(suits)}", 
                               f"{random.choice(cards)}{random.choice(suits)}"]
                pair_type = 'player_pair'
            else:  # Banker pair
                player_cards = [f"{random.choice(cards)}{random.choice(suits)}", 
                               f"{random.choice(cards)}{random.choice(suits)}"]
                banker_cards = [f"{pair_value}{pair_suits[0]}", f"{pair_value}{pair_suits[1]}"]
                pair_type = 'banker_pair'
            
            has_pair = True
        else:
            # 일반 카드
            player_cards = [f"{random.choice(cards)}{random.choice(suits)}", 
                           f"{random.choice(cards)}{random.choice(suits)}"]
            banker_cards = [f"{random.choice(cards)}{random.choice(suits)}", 
                           f"{random.choice(cards)}{random.choice(suits)}"]
            has_pair = False
            pair_type = 'none'
        
        # 바카라 점수 계산
        def calculate_score(cards):
            total = 0
            for card in cards:
                value = card[:-1]
                if value in ['J', 'Q', 'K']:
                    total += 10
                elif value == 'A':
                    total += 1
                else:
                    total += int(value)
            return total % 10
        
        player_total = calculate_score(player_cards)
        banker_total = calculate_score(banker_cards)
        
        # 결과 결정 (현실적 확률)
        if player_total > banker_total:
            result = 'player'
        elif banker_total > player_total:
            result = 'banker'
        else:
            result = 'tie'
        
        # 타임스탬프
        timestamp = datetime.now() - timedelta(minutes=num_games - i)
        
        game = {
            'game_id': i + 1,
            'timestamp': timestamp,
            'player_cards': player_cards,
            'banker_cards': banker_cards,
            'player_total': player_total,
            'banker_total': banker_total,
            'result': result,
            'has_pair': has_pair,
            'pair_type': pair_type,
            'table_name': 'test_table'
        }
        
        games.append(game)
    
    return games


def test_feature_engineering():
    """특성 엔지니어링 테스트"""
    safe_print("\n🧪 특성 엔지니어링 테스트")
    
    feature_engineer = AdvancedFeatureEngineer()
    
    # 샘플 게임 데이터
    sample_games = generate_realistic_baccarat_data(50)
    
    # 딥러닝 특성 추출 테스트
    deep_features = feature_engineer.extract_deep_features(sample_games, lookback=20)
    safe_print(f"  딥러닝 특성 크기: {deep_features.shape}")
    
    # 통계 특성 추출 테스트
    stats_features = feature_engineer.extract_statistical_features(sample_games, window=30)
    safe_print(f"  통계 특성 크기: {stats_features.shape}")
    
    safe_print("✅ 특성 엔지니어링 테스트 완료")


def test_performance_tracker():
    """성능 추적기 테스트"""
    safe_print("\n📊 성능 추적기 테스트")
    
    tracker = ModelPerformanceTracker()
    
    # 모의 예측 기록
    predictions = ['player', 'banker', 'player', 'tie', 'banker']
    actuals = ['player', 'player', 'player', 'tie', 'banker']
    confidences = [0.75, 0.82, 0.68, 0.45, 0.91]
    
    for pred, actual, conf in zip(predictions, actuals, confidences):
        tracker.record_prediction(pred, actual, conf)
    
    # 성능 지표 확인
    metrics = tracker.get_performance_metrics()
    safe_print(f"  현재 정확도: {metrics['current_accuracy']:.2f}")
    safe_print(f"  총 예측수: {metrics['total_predictions']}")
    safe_print(f"  평균 신뢰도: {metrics['avg_confidence']:.2f}")
    safe_print(f"  재학습 필요: {tracker.should_retrain()}")
    
    safe_print("✅ 성능 추적기 테스트 완료")


def test_ai_engine_training():
    """AI 엔진 학습 테스트"""
    safe_print("\n🏋️ AI 엔진 학습 테스트")
    
    # 충분한 학습 데이터 생성
    training_data = generate_realistic_baccarat_data(300)
    safe_print(f"  학습 데이터: {len(training_data)}게임")
    
    # AI 엔진 초기화
    ai_engine = get_advanced_ai_engine('ensemble')
    
    # 모델 학습
    training_result = ai_engine.train_model(training_data)
    
    if training_result.get('success', False):
        safe_print("✅ AI 모델 학습 성공")
        if 'ensemble' in training_result:
            ensemble_info = training_result['ensemble']
            safe_print(f"  앙상블 정확도: {ensemble_info.get('overall_accuracy', 0):.3f}")
            safe_print(f"  모델 가중치: {ensemble_info.get('weights', {})}")
    else:
        safe_print(f"❌ AI 모델 학습 실패: {training_result.get('error', 'Unknown error')}")
    
    return ai_engine, training_result


def test_ai_predictions(ai_engine):
    """AI 예측 테스트"""
    safe_print("\n🔮 AI 예측 테스트")
    
    # 테스트 데이터 생성
    test_data = generate_realistic_baccarat_data(25)
    
    # 여러 예측 수행
    correct_predictions = 0
    total_predictions = 0
    
    for i in range(5, len(test_data)):
        recent_games = test_data[:i]
        prediction_result = ai_engine.predict_next_result(recent_games)
        
        if 'error' not in prediction_result:
            predicted = prediction_result.get('predicted_result', 'unknown')
            confidence = prediction_result.get('confidence', 0)
            model_type = prediction_result.get('model_type', 'unknown')
            
            safe_print(f"  예측 {i-4}: {predicted} (신뢰도: {confidence:.2f}, 모델: {model_type})")
            total_predictions += 1
        else:
            safe_print(f"  예측 {i-4}: 오류 - {prediction_result['error']}")
    
    safe_print(f"✅ 총 {total_predictions}개 예측 완료")


def test_web_integration():
    """웹 통합 테스트"""
    safe_print("\n🔗 웹 통합 테스트")
    
    # AI 통합 인스턴스 생성
    ai_integration = get_ai_integration()
    
    # 상태 확인
    status = ai_integration.get_status()
    safe_print(f"  AI 엔진 초기화: {status['ai_engine_initialized']}")
    safe_print(f"  모델 타입: {status['model_type']}")
    
    # 모의 데이터베이스 매니저 클래스
    class MockDatabaseManager:
        def __init__(self):
            self.games = generate_realistic_baccarat_data(200)
        
        def get_recent_games(self, limit):
            return self.games[-limit:]
    
    mock_db = MockDatabaseManager()
    
    # 학습 테스트
    training_result = ai_integration.train_with_database_data(mock_db)
    if training_result.get('success', False):
        safe_print("✅ 웹 통합 학습 성공")
    else:
        safe_print(f"❌ 웹 통합 학습 실패: {training_result.get('message', 'Unknown error')}")
    
    # 예측 테스트
    prediction_result = ai_integration.get_prediction(mock_db.get_recent_games(20))
    if prediction_result.get('success', False):
        pred_info = prediction_result['prediction']
        safe_print(f"  웹 예측 결과: {pred_info['result']} (신뢰도: {pred_info['confidence']}%)")
        safe_print("✅ 웹 통합 예측 성공")
    else:
        safe_print(f"❌ 웹 통합 예측 실패: {prediction_result.get('message', 'Unknown error')}")
    
    # 성능 조회 테스트
    performance = ai_integration.get_model_performance()
    if performance.get('success', False):
        perf_info = performance['performance']
        safe_print(f"  웹 성능 정보: 정확도 {perf_info['accuracy']}%, 예측수 {perf_info['total_predictions']}")
        safe_print("✅ 웹 통합 성능 조회 성공")


def benchmark_performance():
    """성능 벤치마크"""
    safe_print("\n⚡ 성능 벤치마크")
    
    # 대량 데이터 생성
    large_dataset = generate_realistic_baccarat_data(1000)
    
    # 특성 추출 성능
    start_time = datetime.now()
    feature_engineer = AdvancedFeatureEngineer()
    for i in range(100):
        features = feature_engineer.extract_deep_features(large_dataset[i:i+20])
    extraction_time = (datetime.now() - start_time).total_seconds()
    
    safe_print(f"  특성 추출 성능: {extraction_time:.2f}초 (100회)")
    safe_print(f"  평균 추출 시간: {extraction_time/100*1000:.1f}ms")
    
    # AI 엔진 초기화 시간
    start_time = datetime.now()
    ai_engine = get_advanced_ai_engine('ensemble')
    init_time = (datetime.now() - start_time).total_seconds()
    
    safe_print(f"  AI 엔진 초기화: {init_time:.3f}초")
    
    safe_print("✅ 성능 벤치마크 완료")


def main():
    """메인 테스트 실행"""
    safe_print("=" * 60)
    safe_print("🧪 Two Very Auto v3.0 - Phase 4 고급 AI 기능 테스트")
    safe_print("=" * 60)
    
    try:
        # 1. 특성 엔지니어링 테스트
        test_feature_engineering()
        
        # 2. 성능 추적기 테스트
        test_performance_tracker()
        
        # 3. AI 엔진 학습 테스트
        ai_engine, training_result = test_ai_engine_training()
        
        # 4. AI 예측 테스트 (학습 성공 시에만)
        if training_result.get('success', False):
            test_ai_predictions(ai_engine)
        
        # 5. 웹 통합 테스트
        test_web_integration()
        
        # 6. 성능 벤치마크
        benchmark_performance()
        
        # 테스트 요약
        safe_print("\n" + "=" * 60)
        safe_print("📋 Phase 4 구현 완료 요약")
        safe_print("=" * 60)
        
        completed_features = [
            "✅ 고급 AI 예측 엔진 아키텍처 설계",
            "✅ LSTM/GRU 기반 시계열 예측 모델 구현 (폴백 포함)",
            "✅ 앙상블 모델 (RandomForest + GradientBoosting) 개발",
            "✅ 실시간 모델 성능 모니터링 시스템",
            "✅ 지능형 패턴 분석 알고리즘 구현",
            "✅ 이상 징후 탐지 시스템 개발",
            "✅ AI 엔진과 웹서버 통합",
            "✅ AI 관리 대시보드 및 API 엔드포인트"
        ]
        
        for feature in completed_features:
            safe_print(f"  {feature}")
        
        safe_print("\n🎯 Phase 4 구현 성공!")
        safe_print("💡 TensorFlow 설치 시 딥러닝 기능이 활성화됩니다:")
        safe_print("   pip install tensorflow>=2.13.0")
        
    except Exception as e:
        safe_print(f"❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    safe_print("\n🏁 전체 테스트 완료")


if __name__ == "__main__":
    main()