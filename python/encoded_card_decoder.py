#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
바카라 암호화된 카드 정보 디코더
패킷의 "history" 필드에 인코딩된 카드 데이터를 디코딩
"""

import json
import base64
import logging
from typing import Dict, List, Any, Optional, Tuple
from korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EncodedCardDecoder:
    """암호화된 바카라 카드 정보 디코더"""
    
    def __init__(self):
        """디코더 초기화"""
        # 카드 심볼 매핑
        self.card_suits = {
            'H': '♥', 'D': '♦', 'C': '♣', 'S': '♠'
        }
        
        # 카드 랭크 매핑
        self.card_ranks = {
            'A': 'A', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', 
            '7': '7', '8': '8', '9': '9', 'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K'
        }
        
        # 바카라 점수 매핑
        self.baccarat_values = {
            'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            '10': 0, 'J': 0, 'Q': 0, 'K': 0
        }
        
        logger.info("[Encoded Card Decoder] Initialized successfully")
    
    def decode_history_string(self, encoded_history: str) -> Dict[str, Any]:
        """
        암호화된 히스토리 문자열 디코딩
        
        Args:
            encoded_history: 인코딩된 히스토리 문자열
            
        Returns:
            디코딩된 카드 정보
        """
        try:
            safe_print(f"[Decoder] 디코딩 시작: {encoded_history[:50]}...")
            
            # 여러 디코딩 방법 시도
            results = {
                'raw_string': encoded_history,
                'length': len(encoded_history),
                'analysis': {},
                'decoded_attempts': []
            }
            
            # 1. Base64 디코딩 시도
            base64_result = self._try_base64_decode(encoded_history)
            if base64_result:
                results['decoded_attempts'].append({
                    'method': 'base64',
                    'result': base64_result,
                    'success': True
                })
            
            # 2. URL 디코딩 시도
            url_result = self._try_url_decode(encoded_history)
            if url_result:
                results['decoded_attempts'].append({
                    'method': 'url',
                    'result': url_result,
                    'success': True
                })
            
            # 3. 커스텀 인코딩 분석
            custom_result = self._analyze_custom_encoding(encoded_history)
            results['analysis'] = custom_result
            
            # 4. 패턴 기반 디코딩
            pattern_result = self._try_pattern_decode(encoded_history)
            if pattern_result:
                results['decoded_attempts'].append({
                    'method': 'pattern',
                    'result': pattern_result,
                    'success': True
                })
            
            return results
            
        except Exception as e:
            logger.error(f"[Decoder] 디코딩 실패: {e}")
            return {
                'raw_string': encoded_history,
                'error': str(e),
                'success': False
            }
    
    def _try_base64_decode(self, encoded_string: str) -> Optional[Dict[str, Any]]:
        """Base64 디코딩 시도"""
        try:
            # 패딩 추가 (필요시)
            padded_string = encoded_string
            while len(padded_string) % 4 != 0:
                padded_string += '='
            
            # Base64 디코딩
            decoded_bytes = base64.b64decode(padded_string, validate=True)
            decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
            
            return {
                'decoded_bytes': decoded_bytes.hex(),
                'decoded_text': decoded_text,
                'printable_chars': ''.join(c for c in decoded_text if c.isprintable()),
                'byte_analysis': self._analyze_bytes(decoded_bytes)
            }
            
        except Exception as e:
            logger.debug(f"Base64 디코딩 실패: {e}")
            return None
    
    def _try_url_decode(self, encoded_string: str) -> Optional[Dict[str, Any]]:
        """URL 디코딩 시도"""
        try:
            import urllib.parse
            decoded = urllib.parse.unquote(encoded_string)
            
            if decoded != encoded_string:
                return {
                    'decoded_text': decoded,
                    'changes_made': True
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"URL 디코딩 실패: {e}")
            return None
    
    def _analyze_custom_encoding(self, encoded_string: str) -> Dict[str, Any]:
        """커스텀 인코딩 패턴 분석"""
        analysis = {
            'character_frequency': {},
            'special_chars': [],
            'numeric_chars': [],
            'alpha_chars': [],
            'possible_separators': [],
            'pattern_analysis': {}
        }
        
        try:
            # 문자 빈도 분석
            for char in encoded_string:
                analysis['character_frequency'][char] = analysis['character_frequency'].get(char, 0) + 1
            
            # 문자 타입 분류
            for char in set(encoded_string):
                if char.isdigit():
                    analysis['numeric_chars'].append(char)
                elif char.isalpha():
                    analysis['alpha_chars'].append(char)
                else:
                    analysis['special_chars'].append(char)
            
            # 가능한 구분자 찾기
            common_separators = ['&', '|', '#', '$', '%', '+', '=', ':', ';', ',']
            for sep in common_separators:
                if sep in encoded_string:
                    analysis['possible_separators'].append(sep)
            
            # 패턴 분석
            analysis['pattern_analysis'] = self._analyze_patterns(encoded_string)
            
            return analysis
            
        except Exception as e:
            logger.error(f"커스텀 인코딩 분석 실패: {e}")
            return analysis
    
    def _analyze_patterns(self, encoded_string: str) -> Dict[str, Any]:
        """문자열 패턴 분석"""
        patterns = {
            'repeating_sequences': [],
            'chunk_patterns': [],
            'possible_card_patterns': []
        }
        
        try:
            # 반복되는 시퀀스 찾기
            for length in range(2, min(6, len(encoded_string) // 2)):
                for i in range(len(encoded_string) - length):
                    chunk = encoded_string[i:i+length]
                    if encoded_string.count(chunk) > 1:
                        patterns['repeating_sequences'].append({
                            'sequence': chunk,
                            'count': encoded_string.count(chunk),
                            'length': length
                        })
            
            # 가능한 구분자로 청크 분석
            for separator in ['&', '|', '#', '$', '%', '+']:
                if separator in encoded_string:
                    chunks = encoded_string.split(separator)
                    if len(chunks) > 1:
                        patterns['chunk_patterns'].append({
                            'separator': separator,
                            'chunks': chunks,
                            'chunk_count': len(chunks),
                            'avg_chunk_length': sum(len(c) for c in chunks) / len(chunks)
                        })
            
            # 카드 패턴 추정 (52장 = 13랭크 × 4무늬)
            if len(encoded_string) > 10:
                # 가능한 카드 인코딩 방식 추정
                patterns['possible_card_patterns'] = self._estimate_card_encoding(encoded_string)
            
            return patterns
            
        except Exception as e:
            logger.error(f"패턴 분석 실패: {e}")
            return patterns
    
    def _estimate_card_encoding(self, encoded_string: str) -> List[Dict[str, Any]]:
        """카드 인코딩 방식 추정"""
        estimations = []
        
        try:
            # 방법 1: 각 문자가 카드를 나타내는 경우
            if len(encoded_string) >= 4:  # 최소 2장씩 × 2(플레이어/뱅커)
                estimations.append({
                    'method': 'single_char_per_card',
                    'estimated_cards': len(encoded_string),
                    'description': '각 문자가 하나의 카드를 나타냄'
                })
            
            # 방법 2: 2문자가 하나의 카드 (랭크+무늬)
            if len(encoded_string) % 2 == 0 and len(encoded_string) >= 8:
                estimations.append({
                    'method': 'two_char_per_card',
                    'estimated_cards': len(encoded_string) // 2,
                    'description': '2문자가 하나의 카드 (랭크+무늬)'
                })
            
            # 방법 3: Base-X 인코딩 (52진법 등)
            unique_chars = len(set(encoded_string))
            if unique_chars <= 52:
                estimations.append({
                    'method': f'base_{unique_chars}_encoding',
                    'unique_symbols': unique_chars,
                    'description': f'{unique_chars}진법 인코딩으로 카드 표현'
                })
            
            return estimations
            
        except Exception as e:
            logger.error(f"카드 인코딩 추정 실패: {e}")
            return []
    
    def _try_pattern_decode(self, encoded_string: str) -> Optional[Dict[str, Any]]:
        """패턴 기반 디코딩 시도"""
        try:
            results = []
            
            # Evolution Gaming 스타일 인코딩 추정
            if '&' in encoded_string or '|' in encoded_string:
                result = self._decode_evolution_style(encoded_string)
                if result:
                    results.append(result)
            
            # 커스텀 Base64 변형 시도
            if len(encoded_string) > 10:
                result = self._decode_custom_base64(encoded_string)
                if result:
                    results.append(result)
            
            if results:
                return {
                    'decoded_results': results,
                    'best_match': results[0] if results else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"패턴 기반 디코딩 실패: {e}")
            return None
    
    def _decode_evolution_style(self, encoded_string: str) -> Optional[Dict[str, Any]]:
        """Evolution Gaming 스타일 인코딩 디코딩"""
        try:
            # Evolution Gaming은 특별한 인코딩을 사용할 수 있음
            # 실제 카드 정보를 압축된 형태로 저장
            
            # 구분자 기반 분석
            separators = ['&', '|', '#', '$', '%', '+', '=']
            for sep in separators:
                if sep in encoded_string:
                    parts = encoded_string.split(sep)
                    if len(parts) > 1:
                        return {
                            'encoding_type': 'evolution_gaming',
                            'separator': sep,
                            'parts': parts,
                            'part_count': len(parts),
                            'description': 'Evolution Gaming 스타일 구분자 기반 인코딩'
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Evolution 스타일 디코딩 실패: {e}")
            return None
    
    def _decode_custom_base64(self, encoded_string: str) -> Optional[Dict[str, Any]]:
        """커스텀 Base64 변형 디코딩"""
        try:
            # 표준이 아닌 Base64 문자셋 사용 가능성
            custom_charsets = [
                'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',  # 표준
                'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_',  # URL-safe
                'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@',  # 커스텀
            ]
            
            for i, charset in enumerate(custom_charsets):
                try:
                    # 변환 테이블 생성
                    standard_charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
                    trans_table = str.maketrans(charset, standard_charset)
                    
                    # 변환 후 디코딩 시도
                    converted = encoded_string.translate(trans_table)
                    decoded_bytes = base64.b64decode(converted + '==')
                    decoded_text = decoded_bytes.decode('utf-8', errors='ignore')
                    
                    return {
                        'custom_base64_type': f'charset_{i}',
                        'converted_string': converted,
                        'decoded_text': decoded_text,
                        'decoded_bytes_hex': decoded_bytes.hex()
                    }
                    
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"커스텀 Base64 디코딩 실패: {e}")
            return None
    
    def _analyze_bytes(self, byte_data: bytes) -> Dict[str, Any]:
        """바이트 데이터 분석"""
        analysis = {
            'length': len(byte_data),
            'hex_dump': byte_data.hex(),
            'ascii_printable': ''.join(chr(b) if 32 <= b <= 126 else '.' for b in byte_data),
            'byte_patterns': [],
            'possible_interpretations': []
        }
        
        try:
            # 바이트 패턴 분석
            if len(byte_data) >= 4:
                # 4바이트씩 묶어서 분석 (카드 2장?)
                for i in range(0, len(byte_data), 4):
                    chunk = byte_data[i:i+4]
                    analysis['byte_patterns'].append({
                        'offset': i,
                        'hex': chunk.hex(),
                        'decimal': [b for b in chunk],
                        'possible_cards': self._bytes_to_cards(chunk)
                    })
            
            # 가능한 해석들
            if len(byte_data) % 2 == 0:
                analysis['possible_interpretations'].append({
                    'type': 'card_pairs',
                    'description': '각 2바이트가 카드 1장 (랭크+무늬)',
                    'card_count': len(byte_data) // 2
                })
            
            if len(byte_data) <= 52:
                analysis['possible_interpretations'].append({
                    'type': 'card_indices',
                    'description': '각 바이트가 카드 인덱스 (0-51)',
                    'card_count': len(byte_data)
                })
            
            return analysis
            
        except Exception as e:
            logger.error(f"바이트 분석 실패: {e}")
            return analysis
    
    def _bytes_to_cards(self, chunk: bytes) -> List[Dict[str, Any]]:
        """바이트 청크를 카드로 변환 시도"""
        possible_cards = []
        
        try:
            for byte_val in chunk:
                if byte_val < 52:  # 유효한 카드 인덱스 범위
                    suit_idx = byte_val // 13
                    rank_idx = byte_val % 13
                    
                    suits = ['♠', '♥', '♦', '♣']
                    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
                    
                    if suit_idx < 4 and rank_idx < 13:
                        possible_cards.append({
                            'byte_value': byte_val,
                            'suit': suits[suit_idx],
                            'rank': ranks[rank_idx],
                            'card': f"{ranks[rank_idx]}{suits[suit_idx]}",
                            'baccarat_value': self.baccarat_values.get(ranks[rank_idx], 0)
                        })
            
            return possible_cards
            
        except Exception as e:
            logger.error(f"바이트-카드 변환 실패: {e}")
            return []
    
    def analyze_with_context(self, encoded_history: str, history_v2: List[Dict]) -> Dict[str, Any]:
        """
        컨텍스트와 함께 인코딩 분석
        
        Args:
            encoded_history: 인코딩된 문자열
            history_v2: 해석된 게임 결과들
            
        Returns:
            컨텍스트 기반 분석 결과
        """
        try:
            # 기본 디코딩 수행
            decode_result = self.decode_history_string(encoded_history)
            
            # 게임 수와 인코딩 길이 비교
            game_count = len(history_v2)
            encoding_length = len(encoded_history)
            
            context_analysis = {
                'game_count': game_count,
                'encoding_length': encoding_length,
                'ratio': encoding_length / game_count if game_count > 0 else 0,
                'pattern_matching': [],
                'confidence_score': 0.0
            }
            
            # 패턴 매칭 분석
            for i, game in enumerate(history_v2):
                player_score = game.get('playerScore', 0)
                banker_score = game.get('bankerScore', 0)
                
                # 인코딩에서 해당 위치의 문자들 확인
                if i < len(encoded_history):
                    char = encoded_history[i]
                    context_analysis['pattern_matching'].append({
                        'game_index': i,
                        'player_score': player_score,
                        'banker_score': banker_score,
                        'encoded_char': char,
                        'ascii_val': ord(char),
                        'possible_correlation': self._check_correlation(char, player_score, banker_score)
                    })
            
            # 결합된 결과 반환
            return {
                'decode_result': decode_result,
                'context_analysis': context_analysis,
                'recommendations': self._generate_recommendations(decode_result, context_analysis)
            }
            
        except Exception as e:
            logger.error(f"컨텍스트 분석 실패: {e}")
            return {'error': str(e)}
    
    def _check_correlation(self, char: str, player_score: int, banker_score: int) -> Dict[str, Any]:
        """문자와 점수 간의 상관관계 확인"""
        correlations = {}
        
        try:
            ascii_val = ord(char)
            
            # 직접적 상관관계
            correlations['direct_player'] = ascii_val == player_score
            correlations['direct_banker'] = ascii_val == banker_score
            correlations['sum_correlation'] = ascii_val == (player_score + banker_score)
            
            # 오프셋 상관관계
            correlations['offset_correlations'] = []
            for offset in range(-10, 11):
                adjusted = ascii_val + offset
                if adjusted == player_score or adjusted == banker_score:
                    correlations['offset_correlations'].append({
                        'offset': offset,
                        'adjusted_value': adjusted,
                        'matches': 'player' if adjusted == player_score else 'banker'
                    })
            
            return correlations
            
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_recommendations(self, decode_result: Dict, context_analysis: Dict) -> List[str]:
        """분석 결과에 기반한 권장사항 생성"""
        recommendations = []
        
        try:
            # 디코딩 성공도에 따른 권장사항
            if decode_result.get('decoded_attempts'):
                recommendations.append("일부 디코딩 방법이 성공했습니다. 결과를 검토하세요.")
            
            # 패턴 분석 결과
            if context_analysis.get('ratio', 0) > 0:
                ratio = context_analysis['ratio']
                if ratio < 2:
                    recommendations.append("인코딩이 매우 압축적입니다. 각 문자가 여러 정보를 담고 있을 수 있습니다.")
                elif ratio > 10:
                    recommendations.append("인코딩이 상세합니다. 카드별 상세 정보가 포함되어 있을 수 있습니다.")
            
            # 상관관계 분석
            if context_analysis.get('pattern_matching'):
                correlations = [p.get('possible_correlation', {}) for p in context_analysis['pattern_matching']]
                if any(c.get('direct_player') or c.get('direct_banker') for c in correlations):
                    recommendations.append("ASCII 값과 점수 간에 직접적 상관관계가 발견되었습니다.")
            
            if not recommendations:
                recommendations.append("추가 분석이 필요합니다. 더 많은 데이터로 패턴을 확인하세요.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"권장사항 생성 실패: {e}")
            return ["분석 중 오류가 발생했습니다."]


# 테스트 실행 함수
def test_decoder_with_sample():
    """샘플 데이터로 디코더 테스트"""
    safe_print("=== 인코딩된 카드 디코더 테스트 ===")
    
    decoder = EncodedCardDecoder()
    
    # 샘플 인코딩 문자열
    sample_encoded = "&iAKAQ=:'7&D'0'l&J\"LAW'&%\"AE%AAKB+1|\"v?6$a'*$[=|'=#&&i$+<`B1AE"
    
    # 샘플 게임 결과
    sample_history_v2 = [
        {"winner": "Banker", "playerScore": 3, "bankerScore": 7},
        {"winner": "Banker", "natural": True, "playerScore": 2, "bankerScore": 8},
        {"winner": "Player", "natural": True, "playerScore": 8, "bankerScore": 1}
    ]
    
    # 분석 실행
    result = decoder.analyze_with_context(sample_encoded, sample_history_v2)
    
    safe_print(f"분석 결과:")
    safe_print(f"- 인코딩 길이: {len(sample_encoded)}")
    safe_print(f"- 게임 수: {len(sample_history_v2)}")
    safe_print(f"- 권장사항: {result.get('recommendations', [])}")
    
    return result


if __name__ == '__main__':
    test_decoder_with_sample()