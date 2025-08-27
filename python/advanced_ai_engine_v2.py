#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
고급 AI 예측 엔진 v2.0
딥러닝 + 앙상블 학습 기반 차세대 바카라 예측 시스템
"""

import json
import logging
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import deque, defaultdict
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logger = logging.getLogger(__name__)

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout, BatchNormalization, Input, Concatenate
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
    import joblib
    
    TF_AVAILABLE = True
    safe_print("✅ TensorFlow와 scikit-learn 사용 가능")
except ImportError as e:
    TF_AVAILABLE = False
    safe_print(f"⚠️ 딥러닝 라이브러리 미설치: {e}")
    safe_print("💡 설치 명령: pip install tensorflow>=2.13.0 scikit-learn>=1.3.0")
    
    # 폴백용 임포트 (기본 타입 힌트)
    try:
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.preprocessing import StandardScaler, LabelEncoder
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
        import joblib
        
        SKLEARN_AVAILABLE = True
        safe_print("✅ scikit-learn 사용 가능")
    except ImportError:
        SKLEARN_AVAILABLE = False
        safe_print("⚠️ scikit-learn 미설치")
    
    # 타입 힌트 폴백
    from typing import Any as Model


class ModelPerformanceTracker:
    """모델 성능 실시간 추적 시스템"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.predictions_history = deque(maxlen=max_history)
        self.accuracy_history = deque(maxlen=100)  # 최근 100회 정확도
        self.confidence_history = deque(maxlen=max_history)
        self.model_stats = {
            'total_predictions': 0,
            'correct_predictions': 0,
            'current_accuracy': 0.0,
            'avg_confidence': 0.0,
            'last_retrain': None,
            'model_version': '2.0'
        }
        
    def record_prediction(self, prediction: str, actual: str, confidence: float):
        """예측 결과 기록"""
        is_correct = prediction == actual
        
        self.predictions_history.append({
            'timestamp': datetime.now(),
            'prediction': prediction,
            'actual': actual,
            'confidence': confidence,
            'correct': is_correct
        })
        
        self.confidence_history.append(confidence)
        
        # 통계 업데이트
        self.model_stats['total_predictions'] += 1
        if is_correct:
            self.model_stats['correct_predictions'] += 1
        
        # 최근 100회 정확도 계산
        recent_predictions = list(self.predictions_history)[-100:]
        if recent_predictions:
            correct_count = sum(1 for p in recent_predictions if p['correct'])
            current_accuracy = correct_count / len(recent_predictions)
            self.accuracy_history.append(current_accuracy)
            self.model_stats['current_accuracy'] = current_accuracy
        
        # 평균 신뢰도 계산
        if self.confidence_history:
            self.model_stats['avg_confidence'] = np.mean(list(self.confidence_history))
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 지표 반환"""
        recent_accuracy = list(self.accuracy_history)[-10:] if self.accuracy_history else [0]
        
        return {
            'current_accuracy': self.model_stats['current_accuracy'],
            'overall_accuracy': self.model_stats['correct_predictions'] / max(self.model_stats['total_predictions'], 1),
            'avg_confidence': self.model_stats['avg_confidence'],
            'total_predictions': self.model_stats['total_predictions'],
            'recent_trend': np.mean(recent_accuracy),
            'confidence_stability': np.std(list(self.confidence_history)) if len(self.confidence_history) > 1 else 0,
            'model_version': self.model_stats['model_version'],
            'last_retrain': self.model_stats['last_retrain']
        }
    
    def should_retrain(self) -> bool:
        """재학습 필요 여부 판단"""
        if self.model_stats['total_predictions'] < 100:
            return False
            
        current_accuracy = self.model_stats['current_accuracy']
        
        # 정확도가 75% 미만이거나 신뢰도가 낮으면 재학습 권장
        if current_accuracy < 0.75:
            return True
            
        # 최근 성능이 하락 추세면 재학습 권장
        if len(self.accuracy_history) >= 10:
            recent_accuracies = list(self.accuracy_history)[-10:]
            trend = np.polyfit(range(len(recent_accuracies)), recent_accuracies, 1)[0]
            if trend < -0.01:  # 1% 하락 추세
                return True
                
        return False


class AdvancedFeatureEngineer:
    """고급 특성 엔지니어링"""
    
    def __init__(self):
        self.card_values = {
            'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            '10': 10, 'J': 11, 'Q': 12, 'K': 13
        }
        self.suit_values = {'♠': 0, '♥': 1, '♦': 2, '♣': 3}
        
    def extract_deep_features(self, games: List[Dict[str, Any]], lookback: int = 20) -> np.ndarray:
        """딥러닝용 고급 특성 추출"""
        if len(games) < lookback:
            games = games + [games[-1]] * (lookback - len(games))  # 패딩
        
        features = []
        
        for i, game in enumerate(games[-lookback:]):
            game_features = []
            
            # 1. 기본 카드 정보
            player_cards = game.get('player_cards', ['A', 'A'])
            banker_cards = game.get('banker_cards', ['A', 'A']) 
            
            # 카드 값 특성
            player_values = [self.card_values.get(card.replace('♠♥♦♣', ''), 1) for card in player_cards[:2]]
            banker_values = [self.card_values.get(card.replace('♠♥♦♣', ''), 1) for card in banker_cards[:2]]
            
            game_features.extend(player_values + [0] * (2 - len(player_values)))  # 패딩
            game_features.extend(banker_values + [0] * (2 - len(banker_values)))  # 패딩
            
            # 2. 계산된 점수
            player_total = game.get('player_total', 0)
            banker_total = game.get('banker_total', 0)
            game_features.extend([player_total, banker_total])
            
            # 3. 결과 원핫 인코딩
            result = game.get('result', 'tie')
            result_encoding = [1 if result == 'player' else 0,
                              1 if result == 'banker' else 0, 
                              1 if result == 'tie' else 0]
            game_features.extend(result_encoding)
            
            # 4. 페어 정보
            has_pair = 1 if game.get('has_pair', False) else 0
            pair_type_encoding = [0, 0, 0]  # [player_pair, banker_pair, both_pair]
            pair_type = game.get('pair_type', 'none')
            if pair_type == 'player_pair':
                pair_type_encoding[0] = 1
            elif pair_type == 'banker_pair':
                pair_type_encoding[1] = 1
            elif pair_type == 'both_pair':
                pair_type_encoding[2] = 1
                
            game_features.extend([has_pair] + pair_type_encoding)
            
            # 5. 시간 기반 특성
            timestamp = game.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            hour_sin = np.sin(2 * np.pi * timestamp.hour / 24)
            hour_cos = np.cos(2 * np.pi * timestamp.hour / 24)
            day_of_week = timestamp.weekday() / 6.0  # 0-1 정규화
            
            game_features.extend([hour_sin, hour_cos, day_of_week])
            
            features.append(game_features)
        
        return np.array(features, dtype=np.float32)
    
    def extract_statistical_features(self, games: List[Dict[str, Any]], window: int = 50) -> np.ndarray:
        """통계적 특성 추출"""
        if len(games) < window:
            games = games + [games[-1]] * (window - len(games))
        
        recent_games = games[-window:]
        
        # 결과 통계
        results = [game.get('result', 'tie') for game in recent_games]
        player_wins = results.count('player') / len(results)
        banker_wins = results.count('banker') / len(results)
        ties = results.count('tie') / len(results)
        
        # 페어 통계
        pairs = [1 if game.get('has_pair', False) else 0 for game in recent_games]
        pair_rate = np.mean(pairs)
        
        # 연속성 분석
        streaks = self._calculate_streaks(results)
        max_streak = max(streaks.values()) if streaks else 0
        
        # 점수 분포
        player_totals = [game.get('player_total', 0) for game in recent_games]
        banker_totals = [game.get('banker_total', 0) for game in recent_games]
        
        avg_player_total = np.mean(player_totals)
        avg_banker_total = np.mean(banker_totals)
        std_player_total = np.std(player_totals)
        std_banker_total = np.std(banker_totals)
        
        # 카드 패턴 분석
        card_patterns = self._analyze_card_patterns(recent_games)
        
        statistical_features = [
            player_wins, banker_wins, ties,
            pair_rate, max_streak,
            avg_player_total, avg_banker_total,
            std_player_total, std_banker_total
        ] + card_patterns
        
        return np.array(statistical_features, dtype=np.float32)
    
    def _calculate_streaks(self, results: List[str]) -> Dict[str, int]:
        """연속 패턴 계산"""
        streaks = {'player': 0, 'banker': 0, 'tie': 0}
        current_streak = {'type': None, 'length': 0}
        
        for result in reversed(results):  # 최신부터 역순
            if result == current_streak['type']:
                current_streak['length'] += 1
            else:
                if current_streak['type']:
                    streaks[current_streak['type']] = max(streaks[current_streak['type']], current_streak['length'])
                current_streak = {'type': result, 'length': 1}
        
        # 마지막 스트릭 처리
        if current_streak['type']:
            streaks[current_streak['type']] = max(streaks[current_streak['type']], current_streak['length'])
        
        return streaks
    
    def _analyze_card_patterns(self, games: List[Dict[str, Any]]) -> List[float]:
        """카드 패턴 분석"""
        card_counts = defaultdict(int)
        total_cards = 0
        
        for game in games:
            player_cards = game.get('player_cards', [])
            banker_cards = game.get('banker_cards', [])
            
            all_cards = player_cards + banker_cards
            for card in all_cards:
                card_value = card.replace('♠♥♦♣', '')
                card_counts[card_value] += 1
                total_cards += 1
        
        # 상위 5개 카드 빈도
        if total_cards > 0:
            top_cards = sorted(card_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            card_frequencies = [count / total_cards for _, count in top_cards]
            card_frequencies.extend([0.0] * (5 - len(card_frequencies)))  # 패딩
        else:
            card_frequencies = [0.0] * 5
        
        return card_frequencies


class LSTMPredictor:
    """LSTM 기반 시계열 예측 모델"""
    
    def __init__(self, sequence_length: int = 20, feature_dim: int = 16):
        self.sequence_length = sequence_length
        self.feature_dim = feature_dim
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        
    def build_model(self) -> Model:
        """LSTM 모델 구축"""
        inputs = Input(shape=(self.sequence_length, self.feature_dim))
        
        # LSTM 레이어들
        lstm1 = LSTM(128, return_sequences=True, dropout=0.2, recurrent_dropout=0.2)(inputs)
        lstm1_norm = BatchNormalization()(lstm1)
        
        lstm2 = LSTM(64, return_sequences=True, dropout=0.2, recurrent_dropout=0.2)(lstm1_norm)
        lstm2_norm = BatchNormalization()(lstm2)
        
        lstm3 = LSTM(32, dropout=0.2, recurrent_dropout=0.2)(lstm2_norm)
        lstm3_norm = BatchNormalization()(lstm3)
        
        # Dense 레이어들
        dense1 = Dense(64, activation='relu')(lstm3_norm)
        dense1_drop = Dropout(0.3)(dense1)
        dense1_norm = BatchNormalization()(dense1_drop)
        
        dense2 = Dense(32, activation='relu')(dense1_norm)
        dense2_drop = Dropout(0.2)(dense2)
        
        # 출력 레이어 (3클래스: player, banker, tie)
        outputs = Dense(3, activation='softmax')(dense2_drop)
        
        model = Model(inputs=inputs, outputs=outputs)
        
        # 컴파일
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def prepare_sequences(self, features: np.ndarray, labels: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """시계열 시퀀스 준비"""
        X, y = [], []
        
        for i in range(len(features) - self.sequence_length + 1):
            X.append(features[i:i + self.sequence_length])
            y.append(labels[i + self.sequence_length - 1])
        
        return np.array(X), np.array(y)
    
    def train(self, games_data: List[Dict[str, Any]], validation_split: float = 0.2) -> Dict[str, Any]:
        """모델 학습"""
        if not TF_AVAILABLE:
            return {'error': 'TensorFlow not available', 'success': False}
        
        safe_print("🧠 LSTM 모델 학습 시작...")
        
        # 특성 추출
        feature_engineer = AdvancedFeatureEngineer()
        all_features = []
        all_labels = []
        
        for i in range(len(games_data)):
            game_features = feature_engineer.extract_deep_features(games_data[max(0, i-self.sequence_length):i+1])
            if len(game_features) == self.sequence_length:
                all_features.append(game_features)
                
                result = games_data[i].get('result', 'tie')
                all_labels.append(result)
        
        if len(all_features) < 100:
            return {'error': 'Insufficient training data', 'success': False}
        
        X = np.array(all_features)
        
        # 라벨 인코딩
        y = self.label_encoder.fit_transform(all_labels)
        
        # 특성 정규화
        X_reshaped = X.reshape(-1, X.shape[-1])
        X_scaled = self.scaler.fit_transform(X_reshaped)
        X_scaled = X_scaled.reshape(X.shape)
        
        # 훈련/검증 분할
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=validation_split, random_state=42, stratify=y
        )
        
        # 모델 생성
        self.model = self.build_model()
        
        # 콜백 설정
        callbacks = [
            EarlyStopping(patience=15, restore_best_weights=True, monitor='val_accuracy'),
            ReduceLROnPlateau(patience=10, factor=0.5, min_lr=1e-7),
            ModelCheckpoint('models/lstm_best.h5', save_best_only=True, monitor='val_accuracy')
        ]
        
        # 학습
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=100,
            batch_size=32,
            callbacks=callbacks,
            verbose=1
        )
        
        self.is_trained = True
        
        # 성능 평가
        val_pred = self.model.predict(X_val)
        val_pred_classes = np.argmax(val_pred, axis=1)
        val_accuracy = accuracy_score(y_val, val_pred_classes)
        
        results = {
            'model_type': 'LSTM',
            'training_samples': len(X_train),
            'validation_samples': len(X_val),
            'final_accuracy': val_accuracy,
            'success': True,
            'training_history': {
                'loss': history.history['loss'][-10:],
                'accuracy': history.history['accuracy'][-10:],
                'val_loss': history.history['val_loss'][-10:],
                'val_accuracy': history.history['val_accuracy'][-10:]
            }
        }
        
        safe_print(f"✅ LSTM 모델 학습 완료 - 검증 정확도: {val_accuracy:.3f}")
        return results
    
    def predict(self, recent_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """예측 수행"""
        if not self.is_trained or not self.model:
            return {'error': 'Model not trained'}
        
        feature_engineer = AdvancedFeatureEngineer()
        features = feature_engineer.extract_deep_features(recent_games, self.sequence_length)
        
        if len(features) < self.sequence_length:
            return {'error': 'Insufficient data for prediction'}
        
        # 정규화
        features_reshaped = features.reshape(-1, features.shape[-1])
        features_scaled = self.scaler.transform(features_reshaped)
        features_scaled = features_scaled.reshape(features.shape)
        
        # 예측
        X = features_scaled.reshape(1, self.sequence_length, -1)
        prediction_probs = self.model.predict(X, verbose=0)[0]
        
        # 결과 디코딩
        predicted_class = np.argmax(prediction_probs)
        predicted_result = self.label_encoder.inverse_transform([predicted_class])[0]
        confidence = float(prediction_probs[predicted_class])
        
        return {
            'predicted_result': predicted_result,
            'confidence': confidence,
            'probabilities': {
                'player': float(prediction_probs[self.label_encoder.transform(['player'])[0]] if 'player' in self.label_encoder.classes_ else 0),
                'banker': float(prediction_probs[self.label_encoder.transform(['banker'])[0]] if 'banker' in self.label_encoder.classes_ else 0),
                'tie': float(prediction_probs[self.label_encoder.transform(['tie'])[0]] if 'tie' in self.label_encoder.classes_ else 0)
            },
            'model_type': 'LSTM'
        }


class EnsemblePredictor:
    """앙상블 예측 모델 (LSTM + RandomForest + GradientBoosting)"""
    
    def __init__(self):
        self.lstm_model = LSTMPredictor()
        self.rf_model = RandomForestClassifier(
            n_estimators=200, 
            max_depth=15, 
            random_state=42,
            n_jobs=-1
        )
        self.gb_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=8,
            random_state=42
        )
        self.statistical_scaler = StandardScaler()
        self.is_trained = False
        
        # 앙상블 가중치 (성능에 따라 동적 조정)
        self.model_weights = {
            'lstm': 0.5,
            'random_forest': 0.3,
            'gradient_boosting': 0.2
        }
    
    def train(self, games_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """앙상블 모델 학습"""
        if len(games_data) < 200:
            return {'error': 'Insufficient training data for ensemble', 'success': False}
        
        safe_print("🎯 앙상블 모델 학습 시작...")
        results = {}
        
        # 1. LSTM 모델 학습
        lstm_results = self.lstm_model.train(games_data)
        results['lstm'] = lstm_results
        
        # 2. 전통적 ML 모델용 특성 준비
        feature_engineer = AdvancedFeatureEngineer()
        statistical_features = []
        labels = []
        
        for i in range(50, len(games_data)):  # 충분한 히스토리가 있는 경우만
            features = feature_engineer.extract_statistical_features(games_data[max(0, i-50):i])
            statistical_features.append(features)
            labels.append(games_data[i].get('result', 'tie'))
        
        if len(statistical_features) < 100:
            return {'error': 'Insufficient statistical features', 'success': False}
        
        X_stat = np.array(statistical_features)
        y_stat = np.array(labels)
        
        # 특성 정규화
        X_stat_scaled = self.statistical_scaler.fit_transform(X_stat)
        
        # 훈련/테스트 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X_stat_scaled, y_stat, test_size=0.2, random_state=42, stratify=y_stat
        )
        
        # 3. Random Forest 학습
        self.rf_model.fit(X_train, y_train)
        rf_accuracy = self.rf_model.score(X_test, y_test)
        results['random_forest'] = {'accuracy': rf_accuracy}
        
        # 4. Gradient Boosting 학습
        self.gb_model.fit(X_train, y_train)
        gb_accuracy = self.gb_model.score(X_test, y_test)
        results['gradient_boosting'] = {'accuracy': gb_accuracy}
        
        # 5. 가중치 재조정 (성능에 기반)
        accuracies = {
            'lstm': lstm_results.get('final_accuracy', 0.33) if 'error' not in lstm_results else 0.33,
            'random_forest': rf_accuracy,
            'gradient_boosting': gb_accuracy
        }
        
        # 성능 기반 가중치 계산
        total_accuracy = sum(accuracies.values())
        if total_accuracy > 0:
            self.model_weights = {
                model: acc / total_accuracy for model, acc in accuracies.items()
            }
        
        self.is_trained = True
        
        results['ensemble'] = {
            'weights': self.model_weights,
            'overall_accuracy': sum(acc * weight for acc, weight in zip(accuracies.values(), self.model_weights.values())),
            'success': True
        }
        
        safe_print(f"✅ 앙상블 모델 학습 완료")
        safe_print(f"📊 모델 가중치: {self.model_weights}")
        
        return results
    
    def predict(self, recent_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """앙상블 예측"""
        if not self.is_trained:
            return {'error': 'Ensemble model not trained'}
        
        predictions = {}
        confidences = {}
        
        # 1. LSTM 예측
        lstm_pred = self.lstm_model.predict(recent_games)
        if 'error' not in lstm_pred:
            predictions['lstm'] = lstm_pred['predicted_result']
            confidences['lstm'] = lstm_pred['confidence']
        
        # 2. 통계적 특성 기반 예측
        if len(recent_games) >= 50:
            feature_engineer = AdvancedFeatureEngineer()
            stat_features = feature_engineer.extract_statistical_features(recent_games[-50:])
            stat_features_scaled = self.statistical_scaler.transform(stat_features.reshape(1, -1))
            
            # Random Forest 예측
            rf_pred = self.rf_model.predict(stat_features_scaled)[0]
            rf_prob = self.rf_model.predict_proba(stat_features_scaled)[0]
            predictions['random_forest'] = rf_pred
            confidences['random_forest'] = float(np.max(rf_prob))
            
            # Gradient Boosting 예측
            gb_pred = self.gb_model.predict(stat_features_scaled)[0]
            gb_prob = self.gb_model.predict_proba(stat_features_scaled)[0]
            predictions['gradient_boosting'] = gb_pred
            confidences['gradient_boosting'] = float(np.max(gb_prob))
        
        # 3. 앙상블 결합
        if len(predictions) == 0:
            return {'error': 'No valid predictions from sub-models'}
        
        # 가중 투표
        result_votes = defaultdict(float)
        total_weight = 0
        
        for model_name, predicted_result in predictions.items():
            weight = self.model_weights.get(model_name, 0) * confidences.get(model_name, 0.33)
            result_votes[predicted_result] += weight
            total_weight += weight
        
        # 최종 예측
        final_prediction = max(result_votes.items(), key=lambda x: x[1])[0]
        final_confidence = result_votes[final_prediction] / total_weight if total_weight > 0 else 0.33
        
        return {
            'predicted_result': final_prediction,
            'confidence': float(final_confidence),
            'sub_predictions': predictions,
            'sub_confidences': confidences,
            'model_weights': self.model_weights,
            'model_type': 'Ensemble'
        }


class AdvancedAIEngine:
    """고급 AI 예측 엔진 메인 클래스"""
    
    def __init__(self, model_type: str = 'ensemble'):
        self.model_type = model_type
        self.performance_tracker = ModelPerformanceTracker()
        
        # 모델 초기화
        if model_type == 'lstm':
            self.predictor = LSTMPredictor()
        elif model_type == 'ensemble':
            self.predictor = EnsemblePredictor()
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        self.is_initialized = False
        
        # 모델 저장 경로
        self.model_path = Path('models')
        self.model_path.mkdir(exist_ok=True)
        
        safe_print(f"🧠 고급 AI 엔진 초기화 완료 - 모델 타입: {model_type}")
    
    def train_model(self, games_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """모델 학습"""
        if len(games_data) < 100:
            return {'error': 'Insufficient training data', 'success': False, 'required': 100, 'provided': len(games_data)}
        
        safe_print(f"📚 {len(games_data)}개 게임 데이터로 모델 학습 시작")
        
        training_results = self.predictor.train(games_data)
        
        if 'error' not in training_results:
            self.is_initialized = True
            self.performance_tracker.model_stats['last_retrain'] = datetime.now().isoformat()
            
            # 모델 저장
            self._save_model()
            
            safe_print("✅ 모델 학습 및 저장 완료")
        
        return training_results
    
    def predict_next_result(self, recent_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """다음 게임 결과 예측"""
        if not self.is_initialized:
            return {'error': 'Model not initialized'}
        
        prediction = self.predictor.predict(recent_games)
        
        # 성능 추적 (실제 결과가 있는 경우)
        if len(recent_games) > 0:
            latest_game = recent_games[-1]
            if 'result' in latest_game and hasattr(self, 'last_prediction'):
                self.performance_tracker.record_prediction(
                    self.last_prediction.get('predicted_result', ''),
                    latest_game['result'],
                    self.last_prediction.get('confidence', 0.33)
                )
        
        # 예측 결과 저장 (다음 성능 평가용)
        self.last_prediction = prediction
        
        return prediction
    
    def get_model_performance(self) -> Dict[str, Any]:
        """모델 성능 지표 조회"""
        performance = self.performance_tracker.get_performance_metrics()
        performance['should_retrain'] = self.performance_tracker.should_retrain()
        performance['model_type'] = self.model_type
        
        return performance
    
    def _save_model(self):
        """모델 저장"""
        try:
            model_info = {
                'model_type': self.model_type,
                'trained_at': datetime.now().isoformat(),
                'performance': self.performance_tracker.get_performance_metrics()
            }
            
            with open(self.model_path / 'model_info.json', 'w', encoding='utf-8') as f:
                json.dump(model_info, f, ensure_ascii=False, indent=2)
            
            # scikit-learn 모델 저장
            if hasattr(self.predictor, 'rf_model') and self.predictor.rf_model:
                joblib.dump(self.predictor.rf_model, self.model_path / 'rf_model.pkl')
            
            if hasattr(self.predictor, 'gb_model') and self.predictor.gb_model:
                joblib.dump(self.predictor.gb_model, self.model_path / 'gb_model.pkl')
            
            safe_print("💾 모델 저장 완료")
            
        except Exception as e:
            safe_print(f"❌ 모델 저장 실패: {e}")


# 전역 인스턴스
_advanced_ai_engine = None

def get_advanced_ai_engine(model_type: str = 'ensemble') -> AdvancedAIEngine:
    """고급 AI 엔진 인스턴스 반환"""
    global _advanced_ai_engine
    if _advanced_ai_engine is None:
        _advanced_ai_engine = AdvancedAIEngine(model_type)
    return _advanced_ai_engine


if __name__ == "__main__":
    # 테스트 코드
    safe_print("🧪 고급 AI 엔진 테스트 시작")
    
    # 샘플 데이터 생성
    sample_games = []
    for i in range(300):
        game = {
            'timestamp': datetime.now() - timedelta(minutes=i),
            'player_cards': ['K', 'Q'],
            'banker_cards': ['A', '9'],
            'player_total': 0,  # K+Q = 20 -> 0
            'banker_total': 0,  # A+9 = 10 -> 0  
            'result': 'tie',
            'has_pair': False,
            'pair_type': 'none'
        }
        sample_games.append(game)
    
    # AI 엔진 테스트
    ai_engine = get_advanced_ai_engine('ensemble')
    
    if TF_AVAILABLE:
        # 모델 학습 테스트
        results = ai_engine.train_model(sample_games)
        safe_print(f"🎯 학습 결과: {results}")
        
        # 예측 테스트
        prediction = ai_engine.predict_next_result(sample_games[-20:])
        safe_print(f"🔮 예측 결과: {prediction}")
        
        # 성능 조회
        performance = ai_engine.get_model_performance()
        safe_print(f"📊 모델 성능: {performance}")
    
    safe_print("✅ 고급 AI 엔진 테스트 완료")