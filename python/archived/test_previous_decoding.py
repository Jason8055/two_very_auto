#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이전 카드 디코딩 시스템의 정확한 출력 확인
"""

import sys
import os

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    os.system("chcp 65001 >nul 2>&1")
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from card_decoding_integration import CardDecodingIntegration
from encoded_card_decoder import EncodedCardDecoder

def test_previous_decoding_output():
    """이전 디코딩 시스템의 정확한 출력 테스트"""
    print("🔍 이전 카드 디코딩 시스템 정확성 검증")
    print("=" * 60)
    
    # 실제 샘플 데이터
    sample_encoded = "&iAKAQ=:'7&D'0'l&J\"LAW'&%\"AE%AAKB+1|\"v?6$a'*$[=|'=#&&i$+<`B1AE"
    sample_games = [
        {"winner": "Banker", "playerScore": 3, "bankerScore": 7},
        {"winner": "Banker", "natural": True, "playerScore": 2, "bankerScore": 8}, 
        {"winner": "Player", "natural": True, "playerScore": 8, "bankerScore": 1}
    ]
    
    print(f"📊 테스트 데이터:")
    print(f"  인코딩 문자열: {sample_encoded}")
    print(f"  길이: {len(sample_encoded)} 문자")
    print(f"  게임 수: {len(sample_games)}개")
    
    # 1. CardDecodingIntegration 테스트
    print(f"\n🎯 CardDecodingIntegration 결과:")
    integration = CardDecodingIntegration()
    result = integration.decode_history_string(sample_encoded, sample_games)
    
    if result.get('best_match') and result.get('decoded_cards'):
        best_match = result['best_match']
        cards = best_match.get('cards', [])
        
        print(f"  ✅ 성공! 디코딩된 카드:")
        for i, card in enumerate(cards[:20]):  # 처음 20장만
            card_str = card.get('card', 'Unknown')
            rank = card.get('rank', '?')
            suit = card.get('suit', '?')  
            value = card.get('baccarat_value', 0)
            print(f"    {i+1:2d}. {card_str} (랭크:{rank}, 무늬:{suit}, 바카라값:{value})")
        
        if len(cards) > 20:
            print(f"    ... 총 {len(cards)}장 중 처음 20장만 표시")
        
        print(f"  🎲 방법: {best_match.get('method', 'Unknown')}")
        print(f"  📊 신뢰도: {result.get('confidence_score', 0):.2f}")
    else:
        print(f"  ❌ 디코딩 실패")
    
    # 2. EncodedCardDecoder 테스트
    print(f"\n🎯 EncodedCardDecoder 결과:")
    decoder = EncodedCardDecoder()
    decode_result = decoder.analyze_with_context(sample_encoded, sample_games)
    
    if decode_result.get('decode_result') and decode_result['decode_result'].get('decoded_attempts'):
        attempts = decode_result['decode_result']['decoded_attempts']
        print(f"  ✅ 성공한 디코딩 방법: {len(attempts)}개")
        
        for i, attempt in enumerate(attempts):
            method = attempt.get('method', 'Unknown')
            print(f"    방법 {i+1}: {method}")
            
            if method == 'base64' and attempt.get('result'):
                base64_result = attempt['result']
                if base64_result.get('byte_analysis') and base64_result['byte_analysis'].get('possible_interpretations'):
                    interpretations = base64_result['byte_analysis']['possible_interpretations']
                    print(f"      가능한 해석: {len(interpretations)}개")
                    for interp in interpretations:
                        print(f"        - {interp.get('description', 'Unknown')}")
    else:
        print(f"  ❌ 디코딩 실패")
    
    # 3. 실제 카드 매핑 확인
    print(f"\n🃏 실제 카드 매핑 검증:")
    print(f"  무늬 매핑: ♠ ♥ ♦ ♣")
    print(f"  랭크 매핑: A 2 3 4 5 6 7 8 9 10 J Q K")
    
    # 바카라 점수 검증
    if result.get('best_match') and result['best_match'].get('cards'):
        cards = result['best_match']['cards']
        if len(cards) >= 4:
            print(f"\n🎰 점수 검증 (처음 게임):")
            player_cards = cards[:2]
            banker_cards = cards[2:4]
            
            player_total = sum(card.get('baccarat_value', 0) for card in player_cards) % 10
            banker_total = sum(card.get('baccarat_value', 0) for card in banker_cards) % 10
            
            print(f"  Player 카드: {[card.get('card') for card in player_cards]} = {player_total}")
            print(f"  Banker 카드: {[card.get('card') for card in banker_cards]} = {banker_total}")
            print(f"  예상 점수: P:{sample_games[0]['playerScore']}, B:{sample_games[0]['bankerScore']}")
            
            if player_total == sample_games[0]['playerScore'] and banker_total == sample_games[0]['bankerScore']:
                print(f"  ✅ 점수 일치!")
            else:
                print(f"  ⚠️ 점수 불일치")

if __name__ == "__main__":
    test_previous_decoding_output()