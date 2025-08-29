#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이전 성공 패턴 분석 및 현재 적용 도구
"""

import sys
import os
import json

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from card_decoding_integration import CardDecodingIntegration
from pathlib import Path

class SuccessfulPatternAnalyzer:
    """성공했던 패턴 분석 및 재적용 도구"""
    
    def __init__(self):
        self.successful_patterns = {
            # 이전에 성공했던 패턴
            'evolution_base64_variant': {
                'pattern': '&iAKAQ=:\'7&D\'0\'l&J"LAW\'&%"AE%AAKB+1|"v?6$a\'*$[=|\'=#&&i$+<`B1AE',
                'length': 62,
                'method': 'base64_variant', 
                'confidence': 0.60,
                'decoded_cards': 28,
                'characteristics': {
                    'starts_with_ampersand': True,
                    'contains_equals': True,
                    'has_quotes': True,
                    'has_base64_chars': True,
                    'separator_pattern': '&'
                }
            }
        }
        
        print("🔍 성공했던 패턴 분석 도구 초기화")
    
    def analyze_current_vs_successful(self, current_pattern: str):
        """현재 패턴과 성공 패턴 비교 분석"""
        print(f"\n📊 패턴 비교 분석:")
        print(f"=" * 60)
        
        successful = self.successful_patterns['evolution_base64_variant']
        
        print(f"🟢 성공했던 패턴:")
        print(f"  문자열: {successful['pattern'][:50]}...")
        print(f"  길이: {successful['length']}")
        print(f"  방법: {successful['method']}")
        print(f"  신뢰도: {successful['confidence']}")
        print(f"  카드수: {successful['decoded_cards']}")
        
        print(f"\n🔴 현재 패턴:")
        print(f"  문자열: {current_pattern[:50]}...")
        print(f"  길이: {len(current_pattern)}")
        
        # 특성 비교
        current_chars = {
            'starts_with_ampersand': current_pattern.startswith('&'),
            'contains_equals': '=' in current_pattern,
            'has_quotes': '"' in current_pattern or "'" in current_pattern,
            'has_base64_chars': self._has_base64_chars(current_pattern),
            'separator_pattern': self._find_main_separator(current_pattern)
        }
        
        print(f"\n🔍 특성 비교:")
        for key, success_val in successful['characteristics'].items():
            current_val = current_chars.get(key, 'Unknown')
            match = "✅" if success_val == current_val else "❌"
            print(f"  {key}: {success_val} vs {current_val} {match}")
        
        return self._calculate_similarity(successful['characteristics'], current_chars)
    
    def _has_base64_chars(self, pattern: str) -> bool:
        """Base64 문자 포함 여부 확인"""
        base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
        pattern_chars = set(pattern)
        return len(pattern_chars.intersection(base64_chars)) > len(pattern_chars) * 0.5
    
    def _find_main_separator(self, pattern: str) -> str:
        """주요 구분자 찾기"""
        separators = ['&', '|', '#', '$', '%', '+', '=', ':', ';', '"', "'"]
        separator_counts = {sep: pattern.count(sep) for sep in separators if sep in pattern}
        
        if separator_counts:
            return max(separator_counts.items(), key=lambda x: x[1])[0]
        return 'none'
    
    def _calculate_similarity(self, success_chars: dict, current_chars: dict) -> float:
        """유사도 계산"""
        matches = sum(1 for key in success_chars if success_chars[key] == current_chars.get(key))
        total = len(success_chars)
        return matches / total if total > 0 else 0.0
    
    def generate_transformation_strategies(self, current_pattern: str, similarity: float):
        """변환 전략 생성"""
        print(f"\n🚀 변환 전략 ({similarity:.2%} 유사도):")
        print(f"=" * 60)
        
        strategies = []
        
        if similarity < 0.3:
            print(f"🔄 전면적 변환 필요:")
            strategies.extend([
                "1. 현재 패턴을 성공 패턴 형식으로 변환",
                "2. 구분자 통일 (&를 주 구분자로)",
                "3. Base64 형식으로 재인코딩",
                "4. 따옴표 패턴 적용"
            ])
        elif similarity < 0.6:
            print(f"🔧 부분 변환 필요:")
            strategies.extend([
                "1. 주요 구분자 패턴 적용",
                "2. 인코딩 방식 조정",
                "3. 특수문자 패턴 맞춤"
            ])
        else:
            print(f"✨ 미세 조정:")
            strategies.extend([
                "1. 디코딩 알고리즘 파라미터 조정",
                "2. 신뢰도 임계값 낮춤",
                "3. 추가 디코딩 방법 적용"
            ])
        
        for strategy in strategies:
            print(f"  {strategy}")
        
        return strategies
    
    def implement_demo_data_system(self):
        """성공 패턴 기반 데모 데이터 시스템 구현"""
        print(f"\n🎯 데모 데이터 시스템 구현:")
        print(f"=" * 60)
        
        demo_data = {
            'encoded_history': self.successful_patterns['evolution_base64_variant']['pattern'],
            'history_v2': [
                {"winner": "Banker", "playerScore": 3, "bankerScore": 7, "playerPair": False, "bankerPair": False},
                {"winner": "Banker", "natural": True, "playerScore": 2, "bankerScore": 8, "playerPair": False, "bankerPair": False}, 
                {"winner": "Player", "natural": True, "playerScore": 8, "bankerScore": 1, "playerPair": False, "bankerPair": False}
            ]
        }
        
        # 데모 데이터로 디코딩 테스트
        decoder = CardDecodingIntegration()
        result = decoder.decode_history_string(demo_data['encoded_history'], demo_data['history_v2'])
        
        if result.get('best_match') and result['best_match'].get('cards'):
            cards = result['best_match']['cards']
            print(f"✅ 데모 데이터 성공:")
            print(f"  방법: {result['best_match']['method']}")
            print(f"  신뢰도: {result['confidence_score']:.2f}")
            print(f"  카드 수: {len(cards)}")
            
            print(f"\n🃏 데모 카드 정보:")
            for i, card in enumerate(cards[:12]):
                print(f"    {i+1:2d}. {card.get('card', 'Unknown')} ({card.get('baccarat_value', 0)}점)")
            
            return {
                'success': True,
                'demo_data': demo_data,
                'decoded_result': result,
                'cards': cards
            }
        else:
            print(f"❌ 데모 데이터도 실패")
            return {'success': False}
    
    def create_hybrid_card_system(self, demo_result: dict):
        """하이브리드 카드 정보 시스템 생성"""
        print(f"\n🔀 하이브리드 카드 시스템 생성:")
        print(f"=" * 60)
        
        if not demo_result.get('success'):
            print(f"❌ 데모 결과 없음, 기본 시스템 사용")
            return None
        
        cards = demo_result['cards']
        hybrid_system = {
            'decoded_cards_available': True,
            'cards_database': [],
            'fallback_enabled': True
        }
        
        # 카드 데이터베이스 생성
        for i, card in enumerate(cards):
            hybrid_system['cards_database'].append({
                'index': i,
                'card': card.get('card', 'Unknown'),
                'rank': card.get('rank', '?'),
                'suit': card.get('suit', '?'),
                'baccarat_value': card.get('baccarat_value', 0),
                'usage_example': f"게임 {i//4 + 1}, {'Player' if i%4 < 2 else 'Banker'} {i%2 + 1}번째"
            })
        
        print(f"✅ 카드 데이터베이스 생성: {len(hybrid_system['cards_database'])}장")
        
        # 샘플 출력
        print(f"\n🎮 게임별 카드 배치 예시:")
        for game_idx in range(min(3, len(cards)//4)):
            start_idx = game_idx * 4
            player_cards = cards[start_idx:start_idx+2]
            banker_cards = cards[start_idx+2:start_idx+4]
            
            print(f"  게임 {game_idx+1}:")
            print(f"    Player: {[c.get('card', '?') for c in player_cards]}")
            print(f"    Banker: {[c.get('card', '?') for c in banker_cards]}")
        
        return hybrid_system

def main():
    """메인 실행 함수"""
    print("🎴 이전 성공 패턴 분석 및 재적용 도구")
    print("=" * 80)
    
    analyzer = SuccessfulPatternAnalyzer()
    
    # 현재 실제 패턴 (실제 패킷에서 발견된)
    current_pattern = "$a#L\"F=@%\")\&uAQ$g&'$x\"X=:&o&W\"F'CA]BO#\A8(NL:%;%}>\%^$t'=$TH+\"j&3#b%Z,]AEA8?6$+#2#P%\"#,B+B%%j1L&'<`$t&u<Z<`B7&c?6G{+^2,'h%^'["
    
    # 1. 패턴 비교 분석
    similarity = analyzer.analyze_current_vs_successful(current_pattern)
    
    # 2. 변환 전략 생성
    strategies = analyzer.generate_transformation_strategies(current_pattern, similarity)
    
    # 3. 데모 데이터 시스템 구현
    demo_result = analyzer.implement_demo_data_system()
    
    # 4. 하이브리드 시스템 생성
    if demo_result.get('success'):
        hybrid_system = analyzer.create_hybrid_card_system(demo_result)
        
        print(f"\n💡 구현 제안:")
        print(f"=" * 60)
        print(f"1. 🎲 데모 모드: 성공한 패턴의 카드 정보 표시")
        print(f"2. 🔀 하이브리드 모드: 실제 + 데모 데이터 조합")
        print(f"3. 🔧 디코딩 개선: 현재 패턴에 성공 알고리즘 적용")
        print(f"4. 📊 A/B 테스트: 두 방식 동시 표시")
        
        return {
            'analysis_complete': True,
            'similarity': similarity,
            'strategies': strategies,
            'demo_result': demo_result,
            'hybrid_system': hybrid_system
        }
    
    return {'analysis_complete': False}

if __name__ == "__main__":
    result = main()