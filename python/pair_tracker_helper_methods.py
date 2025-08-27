#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PairTrackerV2용 헬퍼 메서드들
"""

from typing import Dict, List, Any, Optional

def detect_pair_from_cards(game_data: Dict[str, Any]) -> bool:
    """카드 데이터에서 페어 여부 감지"""
    player_cards = game_data.get('player_cards', [])
    banker_cards = game_data.get('banker_cards', [])
    
    # 플레이어 페어 체크
    if len(player_cards) >= 2:
        if is_pair(player_cards[0], player_cards[1]):
            return True
            
    # 뱅커 페어 체크  
    if len(banker_cards) >= 2:
        if is_pair(banker_cards[0], banker_cards[1]):
            return True
            
    return False

def get_pair_type(game_data: Dict[str, Any]) -> Optional[str]:
    """페어 타입 결정 (PP, BP, 또는 None)"""
    player_cards = game_data.get('player_cards', [])
    banker_cards = game_data.get('banker_cards', [])
    
    has_player_pair = len(player_cards) >= 2 and is_pair(player_cards[0], player_cards[1])
    has_banker_pair = len(banker_cards) >= 2 and is_pair(banker_cards[0], banker_cards[1])
    
    if has_player_pair and has_banker_pair:
        return 'BOTH'
    elif has_player_pair:
        return 'PP'
    elif has_banker_pair:
        return 'BP'
    else:
        return None

def get_pair_cards(game_data: Dict[str, Any]) -> str:
    """페어 카드 정보 반환"""
    player_cards = game_data.get('player_cards', [])
    banker_cards = game_data.get('banker_cards', [])
    
    pair_cards = []
    
    # 플레이어 페어 카드
    if len(player_cards) >= 2 and is_pair(player_cards[0], player_cards[1]):
        pair_cards.extend(player_cards[:2])
        
    # 뱅커 페어 카드
    if len(banker_cards) >= 2 and is_pair(banker_cards[0], banker_cards[1]):
        pair_cards.extend(banker_cards[:2])
        
    return ', '.join(pair_cards) if pair_cards else ''

def is_pair(card1: str, card2: str) -> bool:
    """두 카드가 페어인지 확인 (랭크만 비교)"""
    if not card1 or not card2:
        return False
        
    # 카드 형식 처리: A♠ -> A, K♥ -> K
    # 첫 번째 문자부터 찾아서 랭크 추출
    rank1 = ''
    rank2 = ''
    
    for char in card1:
        if char.isalnum():  # 영숫자만 랭크로 간주
            rank1 += char
        else:
            break
            
    for char in card2:
        if char.isalnum():  # 영숫자만 랭크로 간주  
            rank2 += char
        else:
            break
    
    return rank1 == rank2 and rank1 != ''