#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
카드 디코딩 통합 시스템
실제 암호화된 카드 정보를 디코딩하여 시스템에 통합
"""

import json
import re
import base64
import logging
from typing import Dict, List, Any, Optional, Tuple
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CardDecodingIntegration:
    """카드 디코딩 통합 시스템"""
    
    def __init__(self):
        """초기화"""
        # Evolution Gaming의 히스토리 인코딩 추정 규칙
        self.decoding_rules = self._initialize_decoding_rules()
        self.card_mapping = self._initialize_card_mapping()
        
        logger.info("[Card Decoding Integration] Initialized")
    
    def _initialize_decoding_rules(self) -> Dict[str, Any]:
        """디코딩 규칙 초기화"""
        return {
            # 발견된 패턴들
            'separators': ['&', '|', '#', '$', '%', '+', '=', ':', ';', '"', "'"],
            'encoding_types': [
                'evolution_compressed',  # Evolution Gaming 압축 형식
                'base64_variant',        # Base64 변형
                'custom_alphabet',       # 커스텀 알파벳
                'position_based'         # 위치 기반 인코딩
            ],
            # 실제 관찰된 샘플 패턴
            'sample_patterns': {
                'prefix_ampersand': r'^&[iI]',  # &i, &I로 시작
                'contains_quotes': r'["\']',    # 따옴표 포함
                'base64_like': r'[A-Za-z0-9+/=]+',  # Base64와 유사
                'mixed_symbols': r'[&|#$%+=\'"]+' 	# 혼합 심볼들
            }
        }
    
    def _initialize_card_mapping(self) -> Dict[str, Any]:
        """카드 매핑 초기화"""
        # 표준 52장 카드 매핑
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        
        # 카드 인덱스 매핑 (0-51)
        card_index_map = {}
        index = 0
        for suit in suits:
            for rank in ranks:
                card_index_map[index] = f"{rank}{suit}"
                index += 1
        
        # 바카라 점수 매핑
        baccarat_values = {}
        for rank in ranks:
            if rank in ['J', 'Q', 'K']:
                baccarat_values[rank] = 0
            elif rank == 'A':
                baccarat_values[rank] = 1
            else:
                baccarat_values[rank] = int(rank) if rank != '10' else 0
        
        return {
            'index_to_card': card_index_map,
            'card_to_index': {v: k for k, v in card_index_map.items()},
            'baccarat_values': baccarat_values,
            'suits': suits,
            'ranks': ranks
        }
    
    def decode_history_string(self, encoded_history: str, context_games: List[Dict] = None) -> Dict[str, Any]:
        """
        히스토리 문자열 디코딩 (실제 구현)
        
        Args:
            encoded_history: 암호화된 히스토리 문자열
            context_games: 컨텍스트 게임 데이터
            
        Returns:
            디코딩 결과
        """
        try:
            safe_print(f"🔍 카드 히스토리 디코딩: {encoded_history[:30]}...")
            
            decoding_result = {
                'original_encoded': encoded_history,
                'decoding_attempts': [],
                'best_match': None,
                'confidence_score': 0.0,
                'decoded_cards': []
            }
            
            # 여러 디코딩 방법 시도
            methods = [
                self._decode_evolution_format,
                self._decode_base64_variant,
                self._decode_position_based,
                self._decode_ascii_shift
            ]
            
            for method in methods:
                try:
                    result = method(encoded_history, context_games)
                    if result and result.get('success', False):
                        decoding_result['decoding_attempts'].append(result)
                        
                        # 최고 점수 업데이트
                        score = result.get('confidence', 0.0)
                        if score > decoding_result['confidence_score']:
                            decoding_result['confidence_score'] = score
                            decoding_result['best_match'] = result
                            decoding_result['decoded_cards'] = result.get('cards', [])
                
                except Exception as e:
                    logger.warning(f"디코딩 방법 실패: {method.__name__}: {e}")
                    continue
            
            return decoding_result
            
        except Exception as e:
            logger.error(f"히스토리 디코딩 실패: {e}")
            return {'error': str(e)}
    
    def _decode_evolution_format(self, encoded_history: str, context_games: List[Dict] = None) -> Dict[str, Any]:
        """Evolution Gaming 형식 디코딩"""
        try:
            # 패턴 분석: &iAKAQ=:'7&D'0'l&J\"LAW'&%\"AE%AAKB+1|\"v?6$a'*$[=|'=#&&i$+<`B1AE
            
            result = {
                'method': 'evolution_format',
                'success': False,
                'confidence': 0.0,
                'cards': [],
                'analysis': {}
            }
            
            # & 구분자로 분할
            if '&' in encoded_history:
                segments = encoded_history.split('&')
                result['analysis']['segments'] = segments
                result['analysis']['segment_count'] = len(segments)
                
                # 각 세그먼트 분석
                decoded_cards = []
                for i, segment in enumerate(segments):
                    if segment:  # 빈 세그먼트 제외
                        segment_cards = self._decode_segment_to_cards(segment)
                        if segment_cards:
                            decoded_cards.extend(segment_cards)
                
                if decoded_cards:
                    result['cards'] = decoded_cards
                    result['success'] = True
                    
                    # 컨텍스트와 비교하여 신뢰도 계산
                    if context_games:
                        confidence = self._calculate_confidence(decoded_cards, context_games)
                        result['confidence'] = confidence
                    else:
                        result['confidence'] = 0.5  # 기본 신뢰도
            
            return result
            
        except Exception as e:
            logger.error(f"Evolution 형식 디코딩 실패: {e}")
            return {'method': 'evolution_format', 'success': False, 'error': str(e)}
    
    def _decode_segment_to_cards(self, segment: str) -> List[Dict[str, Any]]:
        """세그먼트를 카드로 디코딩"""
        try:
            cards = []
            
            # 방법 1: Base64 디코딩 시도
            try:
                # 패딩 추가
                padded = segment
                while len(padded) % 4 != 0:
                    padded += '='
                
                decoded_bytes = base64.b64decode(padded)
                
                # 바이트를 카드 인덱스로 해석
                for byte_val in decoded_bytes:
                    if byte_val < 52:  # 유효한 카드 인덱스
                        card_info = self._index_to_card_info(byte_val)
                        if card_info:
                            cards.append(card_info)
            
            except:
                pass
            
            # 방법 2: 문자별 매핑
            if not cards and len(segment) > 0:
                for char in segment:
                    if char.isalnum():
                        # ASCII 값을 카드 인덱스로 변환 시도
                        ascii_val = ord(char)
                        card_index = ascii_val % 52  # 52로 나눈 나머지
                        card_info = self._index_to_card_info(card_index)
                        if card_info:
                            cards.append(card_info)
            
            return cards
            
        except Exception as e:
            logger.error(f"세그먼트 디코딩 실패: {e}")
            return []
    
    def _index_to_card_info(self, card_index: int) -> Optional[Dict[str, Any]]:
        """카드 인덱스를 카드 정보로 변환"""
        try:
            if 0 <= card_index < 52:
                card_str = self.card_mapping['index_to_card'][card_index]
                
                # 랭크와 수트 분리
                if len(card_str) >= 2:
                    if card_str[-1] in self.card_mapping['suits']:
                        suit = card_str[-1]
                        rank = card_str[:-1]
                        
                        return {
                            'index': card_index,
                            'card': card_str,
                            'rank': rank,
                            'suit': suit,
                            'baccarat_value': self.card_mapping['baccarat_values'].get(rank, 0)
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"카드 인덱스 변환 실패: {e}")
            return None
    
    def _decode_base64_variant(self, encoded_history: str, context_games: List[Dict] = None) -> Dict[str, Any]:
        """Base64 변형 디코딩"""
        try:
            result = {
                'method': 'base64_variant',
                'success': False,
                'confidence': 0.0,
                'cards': []
            }
            
            # URL-safe Base64 시도
            try:
                # 특수 문자 치환
                cleaned = encoded_history.replace('&', '+').replace('|', '/').replace('_', '/')
                
                # 패딩 추가
                while len(cleaned) % 4 != 0:
                    cleaned += '='
                
                decoded_bytes = base64.b64decode(cleaned)
                
                # 바이트를 카드로 변환
                cards = []
                for byte_val in decoded_bytes:
                    card_info = self._index_to_card_info(byte_val % 52)
                    if card_info:
                        cards.append(card_info)
                
                if cards:
                    result['cards'] = cards
                    result['success'] = True
                    result['confidence'] = 0.6
            
            except:
                pass
            
            return result
            
        except Exception as e:
            return {'method': 'base64_variant', 'success': False, 'error': str(e)}
    
    def _decode_position_based(self, encoded_history: str, context_games: List[Dict] = None) -> Dict[str, Any]:
        """위치 기반 디코딩"""
        try:
            result = {
                'method': 'position_based',
                'success': False,
                'confidence': 0.0,
                'cards': []
            }
            
            if context_games and len(context_games) > 0:
                # 각 게임에 대해 카드 2-6장 추정
                game_count = len(context_games)
                avg_cards_per_game = len(encoded_history) // game_count
                
                if 2 <= avg_cards_per_game <= 6:  # 합리적인 카드 수
                    cards = []
                    
                    # 문자열을 게임 수만큼 분할
                    for i in range(game_count):
                        start_idx = i * avg_cards_per_game
                        end_idx = min(start_idx + avg_cards_per_game, len(encoded_history))
                        
                        game_segment = encoded_history[start_idx:end_idx]
                        
                        # 각 문자를 카드로 변환
                        for char in game_segment:
                            ascii_val = ord(char)
                            card_index = ascii_val % 52
                            card_info = self._index_to_card_info(card_index)
                            if card_info:
                                cards.append(card_info)
                    
                    if cards:
                        result['cards'] = cards
                        result['success'] = True
                        result['confidence'] = 0.4
            
            return result
            
        except Exception as e:
            return {'method': 'position_based', 'success': False, 'error': str(e)}
    
    def _decode_ascii_shift(self, encoded_history: str, context_games: List[Dict] = None) -> Dict[str, Any]:
        """ASCII 시프트 디코딩"""
        try:
            result = {
                'method': 'ascii_shift',
                'success': False,
                'confidence': 0.0,
                'cards': []
            }
            
            # 다양한 시프트 값 시도
            for shift in [-32, -16, 0, 16, 32]:
                try:
                    cards = []
                    
                    for char in encoded_history:
                        ascii_val = ord(char) + shift
                        
                        # 유효한 범위 내에서만
                        if 0 <= ascii_val <= 127:
                            card_index = ascii_val % 52
                            card_info = self._index_to_card_info(card_index)
                            if card_info:
                                cards.append(card_info)
                    
                    if cards and len(cards) >= 4:  # 최소 4장 (플레이어2 + 뱅커2)
                        # 컨텍스트와 비교
                        confidence = 0.3
                        if context_games:
                            confidence = self._calculate_confidence(cards, context_games)
                        
                        if confidence > result['confidence']:
                            result['cards'] = cards
                            result['success'] = True
                            result['confidence'] = confidence
                            result['shift_used'] = shift
                
                except:
                    continue
            
            return result
            
        except Exception as e:
            return {'method': 'ascii_shift', 'success': False, 'error': str(e)}
    
    def _calculate_confidence(self, decoded_cards: List[Dict], context_games: List[Dict]) -> float:
        """디코딩된 카드와 컨텍스트의 일치도 계산"""
        try:
            if not decoded_cards or not context_games:
                return 0.0
            
            confidence_score = 0.0
            total_checks = 0
            
            # 카드 수 합리성 체크
            cards_per_game = len(decoded_cards) / len(context_games)
            if 2 <= cards_per_game <= 6:  # 바카라는 게임당 2-6장
                confidence_score += 0.2
            
            total_checks += 1
            
            # 점수 일치 체크
            if len(context_games) > 0 and len(decoded_cards) >= 4:
                game_cards_start = 0
                
                for game in context_games[:min(3, len(context_games))]:  # 최대 3게임만 체크
                    player_score = game.get('playerScore', 0)
                    banker_score = game.get('bankerScore', 0)
                    
                    # 예상 카드 수 (최소 4장)
                    expected_cards = 4 if not game.get('natural') else 4
                    
                    if game_cards_start + expected_cards <= len(decoded_cards):
                        game_cards = decoded_cards[game_cards_start:game_cards_start + expected_cards]
                        
                        # 플레이어 카드 (첫 2장)
                        player_cards = game_cards[:2]
                        banker_cards = game_cards[2:4]
                        
                        # 점수 계산
                        calc_player_score = sum(card.get('baccarat_value', 0) for card in player_cards) % 10
                        calc_banker_score = sum(card.get('baccarat_value', 0) for card in banker_cards) % 10
                        
                        # 일치도 확인
                        if calc_player_score == player_score:
                            confidence_score += 0.3
                        if calc_banker_score == banker_score:
                            confidence_score += 0.3
                        
                        total_checks += 2
                        game_cards_start += expected_cards
            
            # 평균 신뢰도 반환
            return min(1.0, confidence_score / max(1, total_checks))
            
        except Exception as e:
            logger.error(f"신뢰도 계산 실패: {e}")
            return 0.0
    
    def integrate_with_packet_decoder(self) -> str:
        """패킷 디코더와 통합하는 코드 생성"""
        integration_code = '''
# packet_decoder.py에 추가할 메서드

def decode_history_cards(self, encoded_history: str, history_v2: List[Dict]) -> List[Dict[str, Any]]:
    """
    암호화된 히스토리에서 실제 카드 정보 추출
    
    Args:
        encoded_history: 암호화된 히스토리 문자열
        history_v2: 게임 결과 데이터
        
    Returns:
        디코딩된 카드 정보 리스트
    """
    try:
        from card_decoding_integration import CardDecodingIntegration
        
        decoder = CardDecodingIntegration()
        result = decoder.decode_history_string(encoded_history, history_v2)
        
        if result.get('best_match') and result.get('confidence_score', 0) > 0.5:
            return result.get('decoded_cards', [])
        else:
            # 실패시 기존 방식 사용
            return self._generate_cards_from_score_fallback(history_v2)
    
    except Exception as e:
        logger.error(f"카드 히스토리 디코딩 실패: {e}")
        return self._generate_cards_from_score_fallback(history_v2)

def _generate_cards_from_score_fallback(self, history_v2: List[Dict]) -> List[Dict[str, Any]]:
    """기존 점수 기반 카드 생성 (폴백)"""
    cards = []
    for game in history_v2:
        # 기존 _generate_cards_from_score 로직 사용
        player_cards = self._generate_cards_from_score(
            game.get('playerScore', 0), 
            game.get('natural', False),
            game.get('playerPair', False)
        )
        banker_cards = self._generate_cards_from_score(
            game.get('bankerScore', 0),
            game.get('natural', False), 
            game.get('bankerPair', False)
        )
        
        cards.extend([
            {'type': 'player', 'cards': player_cards, 'game_index': len(cards)//2},
            {'type': 'banker', 'cards': banker_cards, 'game_index': len(cards)//2}
        ])
    
    return cards
'''
        
        return integration_code


# 테스트 함수
def test_card_decoding():
    """카드 디코딩 테스트"""
    safe_print("🎴 카드 디코딩 통합 시스템 테스트")
    
    integration = CardDecodingIntegration()
    
    # 실제 샘플 데이터
    sample_encoded = "&iAKAQ=:'7&D'0'l&J\"LAW'&%\"AE%AAKB+1|\"v?6$a'*$[=|'=#&&i$+<`B1AE"
    sample_games = [
        {"winner": "Banker", "playerScore": 3, "bankerScore": 7},
        {"winner": "Banker", "natural": True, "playerScore": 2, "bankerScore": 8},
        {"winner": "Player", "natural": True, "playerScore": 8, "bankerScore": 1}
    ]
    
    # 디코딩 수행
    result = integration.decode_history_string(sample_encoded, sample_games)
    
    safe_print(f"✅ 디코딩 결과:")
    safe_print(f"  - 시도된 방법: {len(result.get('decoding_attempts', []))}개")
    safe_print(f"  - 최고 신뢰도: {result.get('confidence_score', 0):.2f}")
    
    if result.get('best_match'):
        best = result['best_match']
        safe_print(f"  - 최적 방법: {best.get('method', 'Unknown')}")
        safe_print(f"  - 디코딩된 카드 수: {len(best.get('cards', []))}")
        
        # 처음 몇 장 카드 표시
        cards = best.get('cards', [])[:6]
        for i, card in enumerate(cards):
            safe_print(f"    {i+1}. {card.get('card', 'Unknown')} (값: {card.get('baccarat_value', 0)})")
    
    # 통합 코드 생성
    integration_code = integration.integrate_with_packet_decoder()
    safe_print(f"\n📝 통합 코드 생성 완료 ({len(integration_code)} 문자)")
    
    return result


if __name__ == '__main__':
    test_card_decoding()