#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 예측 엔진 v2.0
딥러닝 기반 바카라 페어 예측 시스템
"""

# 표준 라이브러리
import json
import logging
from collections import deque, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# 서드파티 라이브러리
import numpy as np

# 로컬 모듈
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import tensorflow as tf
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix
    tf_available = True
    sklearn_available = True
    safe_print("✅ TensorFlow 사용 가능")
except ImportError:
    tf_available = False
    sklearn_available = False
    # Create dummy classes for fallback
    class StandardScaler:
        def fit(self, X): return self
        def transform(self, X): return X
        def fit_transform(self, X): return X
    class LabelEncoder:
        def fit(self, y): return self  
        def transform(self, y): return y
        def fit_transform(self, y): return y
    safe_print("⚠️ TensorFlow/Scikit-learn 미설치 - 기본 통계 모델 사용")


class FeatureEngineer:
    """페어 예측을 위한 특성 엔지니어링"""
    
    def __init__(self):
        self.card_values = {
            'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            '10': 10, 'J': 11, 'Q': 12, 'K': 13
        }
        self.suits = {'♠': 0, '♥': 1, '♦': 2, '♣': 3}
        
    def card_to_numeric(self, card: str) -> Tuple[int, int]:
        """카드를 숫자값과 슈트로 변환"""
        if len(card) < 2:
            return 0, 0
            
        value_str = card[:-1]
        suit = card[-1]
        
        value = self.card_values.get(value_str, 0)
        suit_num = self.suits.get(suit, 0)
        
        return value, suit_num
    
    def extract_game_features(self, game_data: Dict[str, Any]) -> np.ndarray:
        """단일 게임에서 특성 추출"""
        features = []
        
        # 플레이어 카드 특성
        player_cards = game_data.get('player_cards', [])
        banker_cards = game_data.get('banker_cards', [])
        
        # 카드 값과 슈트 추출
        player_values, player_suits = [], []
        banker_values, banker_suits = [], []
        
        for card in player_cards[:2]:  # 최대 2장
            value, suit = self.card_to_numeric(card)
            player_values.append(value)
            player_suits.append(suit)
        
        for card in banker_cards[:2]:  # 최대 2장
            value, suit = self.card_to_numeric(card)
            banker_values.append(value)
            banker_suits.append(suit)
        
        # 패딩 (2장 미만인 경우)
        while len(player_values) < 2:
            player_values.append(0)
            player_suits.append(0)
        while len(banker_values) < 2:
            banker_values.append(0)
            banker_suits.append(0)
        
        # 기본 카드 특성
        features.extend(player_values)  # [2개]
        features.extend(player_suits)   # [2개]
        features.extend(banker_values)  # [2개]
        features.extend(banker_suits)   # [2개]
        
        # 파생 특성
        # 1. 같은 값 여부 (페어 가능성)
        player_pair_potential = 1 if player_values[0] == player_values[1] and player_values[0] > 0 else 0
        banker_pair_potential = 1 if banker_values[0] == banker_values[1] and banker_values[0] > 0 else 0
        
        features.extend([player_pair_potential, banker_pair_potential])  # [2개]
        
        # 2. 카드 합계
        player_sum = sum(v % 10 for v in player_values if v > 0)  # 바카라 점수 계산
        banker_sum = sum(v % 10 for v in banker_values if v > 0)
        
        features.extend([player_sum, banker_sum])  # [2개]
        
        # 3. 슈트 분포
        all_suits = player_suits + banker_suits
        suit_counts = [all_suits.count(i) for i in range(4)]
        features.extend(suit_counts)  # [4개]
        
        # 4. 높은 카드 수 (10 이상)
        high_player = sum(1 for v in player_values if v >= 10)
        high_banker = sum(1 for v in banker_values if v >= 10)
        
        features.extend([high_player, high_banker])  # [2개]
        
        return np.array(features, dtype=np.float32)  # 총 16개 특성
    
    def extract_sequence_features(self, games: List[Dict[str, Any]], sequence_length: int = 10) -> np.ndarray:
        """연속된 게임들에서 시퀀스 특성 추출"""
        sequence_features = []
        
        # 최근 게임들의 결과 패턴
        recent_results = []
        recent_pairs = []
        
        for game in games[-sequence_length:]:
            # 게임 결과 (P=0, B=1, T=2)
            result = game.get('result', 'T')
            result_num = 0 if result == 'P' else 1 if result == 'B' else 2
            recent_results.append(result_num)
            
            # 페어 발생 여부
            pair_occurred = 1 if game.get('has_pair', False) else 0
            recent_pairs.append(pair_occurred)
        
        # 패딩
        while len(recent_results) < sequence_length:
            recent_results.insert(0, 2)  # T로 패딩
            recent_pairs.insert(0, 0)
        
        # 패턴 특성
        # 1. 연속 패턴 (같은 결과가 연속으로 나온 횟수)
        consecutive_pattern = 0
        for i in range(1, len(recent_results)):
            if recent_results[i] == recent_results[i-1]:
                consecutive_pattern += 1
            else:
                break
        
        # 2. 페어 간격 (마지막 페어 이후 게임 수)
        games_since_pair = 0
        for i, pair in enumerate(reversed(recent_pairs)):
            if pair == 1:
                games_since_pair = i
                break
        else:
            games_since_pair = sequence_length
        
        # 3. 페어 빈도 (최근 시퀀스에서 페어 발생률)
        pair_frequency = sum(recent_pairs) / len(recent_pairs)
        
        # 4. 결과 분포
        result_counts = [recent_results.count(i) / len(recent_results) for i in range(3)]
        
        sequence_features.extend([consecutive_pattern, games_since_pair, pair_frequency])
        sequence_features.extend(result_counts)
        
        return np.array(sequence_features, dtype=np.float32)  # 6개 특성


class PairPredictionModel:
    """페어 예측 딥러닝 모델"""
    
    def __init__(self, model_path: str = "pair_prediction_model.h5"):
        self.model_path = model_path
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        self.feature_engineer = FeatureEngineer()
        
        # 모델 메타데이터
        self.metadata = {
            'version': '2.0',
            'created_at': datetime.now().isoformat(),
            'features': 22,  # 16 (게임) + 6 (시퀀스)
            'classes': ['NO_PAIR', 'PLAYER_PAIR', 'BANKER_PAIR', 'BOTH_PAIR']
        }
        
        if tf_available:
            self._build_model()
            self._load_model()
    
    def _build_model(self):
        """딥러닝 모델 구성"""
        if not tf_available:
            return
        
        # 신경망 아키텍처
        model = tf.keras.Sequential([
            # 입력층
            tf.keras.layers.Dense(64, activation='relu', input_shape=(22,)),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.BatchNormalization(),
            
            # 은닉층 1
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dropout(0.4),
            tf.keras.layers.BatchNormalization(),
            
            # 은닉층 2
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.BatchNormalization(),
            
            # 은닉층 3
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            
            # 출력층 (4개 클래스: NO_PAIR, PLAYER_PAIR, BANKER_PAIR, BOTH_PAIR)
            tf.keras.layers.Dense(4, activation='softmax')
        ])
        
        # 컴파일
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy', 'precision', 'recall']
        )
        
        self.model = model
        safe_print(f"🧠 딥러닝 모델 구성 완료: {model.count_params():,}개 파라미터")
    
    def _load_model(self):
        """저장된 모델 로드"""
        if not tf_available:
            return
        
        try:
            model_file = Path(self.model_path)
            if model_file.exists():
                self.model = tf.keras.models.load_model(str(model_file))
                self.is_trained = True
                safe_print("✅ 기존 모델 로드 완료")
            else:
                safe_print("ℹ️ 새로운 모델 생성 필요")
                
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            self._build_model()
    
    def prepare_training_data(self, games_data: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """훈련 데이터 준비"""
        X, y = [], []
        sequence_length = 10
        
        for i in range(sequence_length, len(games_data)):
            current_game = games_data[i]
            recent_games = games_data[i-sequence_length:i]
            
            # 특성 추출
            game_features = self.feature_engineer.extract_game_features(current_game)
            sequence_features = self.feature_engineer.extract_sequence_features(recent_games)
            
            # 특성 결합
            combined_features = np.concatenate([game_features, sequence_features])
            X.append(combined_features)
            
            # 레이블 (실제 페어 타입)
            if current_game.get('has_pair', False):
                pair_type = current_game.get('pair_type', 'NO_PAIR')
                # 표준화된 레이블로 변환
                if pair_type in ['PP', 'PLAYER_PAIR']:
                    label = 'PLAYER_PAIR'
                elif pair_type in ['BP', 'BANKER_PAIR']:
                    label = 'BANKER_PAIR'
                elif pair_type in ['BOTH', 'BOTH_PAIR']:
                    label = 'BOTH_PAIR'
                else:
                    label = 'NO_PAIR'
            else:
                label = 'NO_PAIR'
            
            y.append(label)
        
        X = np.array(X)
        y = np.array(y)
        
        # 레이블 인코딩
        y_encoded = self.label_encoder.fit_transform(y)
        
        return X, y_encoded
    
    def train(self, games_data: List[Dict[str, Any]], validation_split: float = 0.2) -> Dict[str, Any]:
        """모델 훈련"""
        if not tf_available:
            safe_print("⚠️ TensorFlow 미사용 - 훈련 건너뛰기")
            return {'success': False, 'message': 'TensorFlow not available'}
        
        safe_print(f"🏋️ 모델 훈련 시작: {len(games_data)}개 게임 데이터")
        
        # 데이터 준비
        X, y = self.prepare_training_data(games_data)
        
        if len(X) < 50:
            return {'success': False, 'message': '훈련 데이터 부족 (최소 50개 필요)'}
        
        # 정규화
        X_scaled = self.scaler.fit_transform(X)
        
        # 훈련/검증 분할
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        # 조기 종료 및 모델 체크포인트
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_accuracy',
                patience=10,
                restore_best_weights=True
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7
            )
        ]
        
        # 훈련
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=100,
            batch_size=32,
            callbacks=callbacks,
            verbose=1
        )
        
        # 평가
        val_loss, val_accuracy, val_precision, val_recall = self.model.evaluate(X_val, y_val, verbose=0)
        
        # 모델 저장
        self.model.save(self.model_path)
        self.is_trained = True
        
        # 분류 보고서
        y_pred = np.argmax(self.model.predict(X_val), axis=1)
        class_report = classification_report(y_val, y_pred, target_names=self.metadata['classes'])
        
        training_results = {
            'success': True,
            'training_samples': len(X_train),
            'validation_samples': len(X_val),
            'val_accuracy': float(val_accuracy),
            'val_precision': float(val_precision),
            'val_recall': float(val_recall),
            'val_loss': float(val_loss),
            'epochs_trained': len(history.history['loss']),
            'classification_report': class_report
        }
        
        safe_print(f"✅ 훈련 완료 - 정확도: {val_accuracy:.3f}, 정밀도: {val_precision:.3f}")
        return training_results
    
    def predict(self, current_game: Dict[str, Any], recent_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """페어 예측"""
        try:
            if not tf_available or not self.is_trained:
                # 통계 기반 예측 (폴백)
                return self._statistical_prediction(current_game, recent_games)
            
            # 특성 추출
            game_features = self.feature_engineer.extract_game_features(current_game)
            sequence_features = self.feature_engineer.extract_sequence_features(recent_games)
            
            # 특성 결합 및 정규화
            combined_features = np.concatenate([game_features, sequence_features]).reshape(1, -1)
            X_scaled = self.scaler.transform(combined_features)
            
            # 예측
            prediction_probs = self.model.predict(X_scaled, verbose=0)[0]
            predicted_class = np.argmax(prediction_probs)
            
            # 클래스명 변환
            class_names = self.metadata['classes']
            predicted_pair_type = class_names[predicted_class]
            
            # 신뢰도 계산
            confidence = float(prediction_probs[predicted_class])
            
            # 각 클래스별 확률
            class_probabilities = {
                class_names[i]: float(prediction_probs[i])
                for i in range(len(class_names))
            }
            
            return {
                'predicted_pair_type': predicted_pair_type,
                'confidence': confidence,
                'probabilities': class_probabilities,
                'prediction_method': 'deep_learning',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"예측 오류: {e}")
            return self._statistical_prediction(current_game, recent_games)
    
    def _statistical_prediction(self, current_game: Dict[str, Any], recent_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """통계 기반 예측 (폴백)"""
        # 간단한 통계 모델
        player_cards = current_game.get('player_cards', [])
        banker_cards = current_game.get('banker_cards', [])
        
        # 페어 가능성 체크
        player_pair_chance = 0.0
        banker_pair_chance = 0.0
        
        if len(player_cards) >= 2:
            p_val1 = self.feature_engineer.card_to_numeric(player_cards[0])[0]
            p_val2 = self.feature_engineer.card_to_numeric(player_cards[1])[0]
            if p_val1 == p_val2:
                player_pair_chance = 0.85
        
        if len(banker_cards) >= 2:
            b_val1 = self.feature_engineer.card_to_numeric(banker_cards[0])[0]
            b_val2 = self.feature_engineer.card_to_numeric(banker_cards[1])[0]
            if b_val1 == b_val2:
                banker_pair_chance = 0.85
        
        # 최근 페어 빈도 고려
        recent_pair_rate = sum(1 for g in recent_games[-10:] if g.get('has_pair', False)) / 10.0
        base_pair_chance = max(0.05, recent_pair_rate * 1.2)
        
        # 예측 결정
        if player_pair_chance > 0.8 and banker_pair_chance > 0.8:
            predicted = 'BOTH_PAIR'
            confidence = min(player_pair_chance, banker_pair_chance)
        elif player_pair_chance > 0.8:
            predicted = 'PLAYER_PAIR'
            confidence = player_pair_chance
        elif banker_pair_chance > 0.8:
            predicted = 'BANKER_PAIR'
            confidence = banker_pair_chance
        else:
            predicted = 'NO_PAIR'
            confidence = 1.0 - base_pair_chance
        
        return {
            'predicted_pair_type': predicted,
            'confidence': confidence,
            'probabilities': {
                'NO_PAIR': 1.0 - base_pair_chance if predicted == 'NO_PAIR' else base_pair_chance,
                'PLAYER_PAIR': player_pair_chance,
                'BANKER_PAIR': banker_pair_chance,
                'BOTH_PAIR': min(player_pair_chance, banker_pair_chance) if player_pair_chance > 0.5 and banker_pair_chance > 0.5 else 0.01
            },
            'prediction_method': 'statistical',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        info = self.metadata.copy()
        info.update({
            'is_trained': self.is_trained,
            'tensorflow_available': tf_available,
            'model_file_exists': Path(self.model_path).exists(),
            'feature_count': 22
        })
        
        if tf_available and self.model:
            info['parameters'] = self.model.count_params()
        
        return info


class AIPredictionEngine:
    """AI 예측 엔진 메인 클래스"""
    
    def __init__(self, model_path: str = "pair_prediction_model.h5"):
        self.model = PairPredictionModel(model_path)
        self.prediction_history = deque(maxlen=1000)
        self.accuracy_tracker = {
            'correct_predictions': 0,
            'total_predictions': 0,
            'accuracy': 0.0
        }
        
        safe_print("🧠 AI 예측 엔진 초기화 완료")
    
    def train_model(self, games_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """모델 훈련"""
        return self.model.train(games_data)
    
    def predict_pair(self, current_game: Dict[str, Any], recent_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """페어 예측"""
        prediction = self.model.predict(current_game, recent_games)
        
        # 예측 히스토리에 추가
        prediction['game_id'] = current_game.get('game_id', 0)
        prediction['table_name'] = current_game.get('table_name', 'Unknown')
        self.prediction_history.append(prediction)
        
        return prediction
    
    def validate_prediction(self, game_id: int, actual_result: Dict[str, Any]):
        """예측 결과 검증"""
        # 해당 게임의 예측 찾기
        prediction = None
        for pred in reversed(self.prediction_history):
            if pred.get('game_id') == game_id:
                prediction = pred
                break
        
        if not prediction:
            return
        
        # 실제 결과와 비교
        actual_pair_type = 'NO_PAIR'
        if actual_result.get('has_pair', False):
            pair_type = actual_result.get('pair_type', 'NO_PAIR')
            if pair_type in ['PP', 'PLAYER_PAIR']:
                actual_pair_type = 'PLAYER_PAIR'
            elif pair_type in ['BP', 'BANKER_PAIR']:
                actual_pair_type = 'BANKER_PAIR'
            elif pair_type in ['BOTH', 'BOTH_PAIR']:
                actual_pair_type = 'BOTH_PAIR'
        
        # 정확도 업데이트
        is_correct = prediction['predicted_pair_type'] == actual_pair_type
        self.accuracy_tracker['total_predictions'] += 1
        if is_correct:
            self.accuracy_tracker['correct_predictions'] += 1
        
        self.accuracy_tracker['accuracy'] = (
            self.accuracy_tracker['correct_predictions'] / 
            self.accuracy_tracker['total_predictions']
        )
        
        # 예측에 검증 결과 추가
        prediction.update({
            'actual_result': actual_pair_type,
            'is_correct': is_correct,
            'validated_at': datetime.now().isoformat()
        })
    
    def get_prediction_stats(self) -> Dict[str, Any]:
        """예측 통계 반환"""
        return {
            'model_info': self.model.get_model_info(),
            'accuracy_tracker': self.accuracy_tracker,
            'recent_predictions': list(self.prediction_history)[-10:],
            'total_predictions': len(self.prediction_history)
        }


# 전역 인스턴스
ai_engine = None

def get_ai_prediction_engine() -> AIPredictionEngine:
    """전역 AI 예측 엔진 인스턴스 반환"""
    global ai_engine
    if ai_engine is None:
        ai_engine = AIPredictionEngine()
    return ai_engine


if __name__ == "__main__":
    # 테스트 코드
    safe_print("=== AI 예측 엔진 테스트 ===")
    
    engine = AIPredictionEngine()
    
    # 더미 게임 데이터 생성
    import random
    
    dummy_games = []
    tables = ['메인테이블_A', '메인테이블_B']
    cards = ['A♠', '2♥', '3♦', '4♣', '5♠', '6♥', '7♦', '8♣', '9♠', '10♥', 'J♦', 'Q♣', 'K♠']
    
    for i in range(200):
        game = {
            'table_name': random.choice(tables),
            'game_id': i + 1,
            'player_cards': random.sample(cards, 2),
            'banker_cards': random.sample(cards, 2),
            'result': random.choice(['P', 'B', 'T']),
            'has_pair': random.random() < 0.15,
            'pair_type': random.choice(['PP', 'BP', 'BOTH']) if random.random() < 0.15 else None
        }
        dummy_games.append(game)
    
    safe_print(f"📊 {len(dummy_games)}개 더미 게임 데이터 생성")
    
    # 모델 훈련 (TensorFlow 사용 가능한 경우)
    if tf_available:
        safe_print("🏋️ 모델 훈련 시작...")
        training_result = engine.train_model(dummy_games)
        if training_result['success']:
            safe_print(f"✅ 훈련 완료 - 정확도: {training_result['val_accuracy']:.3f}")
        else:
            safe_print(f"❌ 훈련 실패: {training_result['message']}")
    
    # 예측 테스트
    test_game = {
        'table_name': '테스트테이블',
        'game_id': 999,
        'player_cards': ['A♠', 'A♥'],  # 페어 가능성 높음
        'banker_cards': ['K♦', '7♣']
    }
    
    recent_games = dummy_games[-10:]  # 최근 10게임
    
    prediction = engine.predict_pair(test_game, recent_games)
    safe_print(f"\n🔮 예측 결과:")
    safe_print(f"  예측 타입: {prediction['predicted_pair_type']}")
    safe_print(f"  신뢰도: {prediction['confidence']:.3f}")
    safe_print(f"  방법: {prediction['prediction_method']}")
    
    # 통계 정보
    stats = engine.get_prediction_stats()
    safe_print(f"\n📈 모델 정보:")
    safe_print(f"  TensorFlow 사용: {stats['model_info']['tensorflow_available']}")
    safe_print(f"  훈련 상태: {stats['model_info']['is_trained']}")
    safe_print(f"  특성 수: {stats['model_info']['feature_count']}")
    
    safe_print("\n🎯 AI 예측 엔진 테스트 완료!")