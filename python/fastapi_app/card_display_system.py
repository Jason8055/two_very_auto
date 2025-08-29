#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
하이브리드 카드 표시 시스템
성공한 패턴의 카드 정보를 활용한 실용적 솔루션
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class HybridCardDisplaySystem:
    """하이브리드 카드 표시 시스템"""
    
    def __init__(self):
        """초기화 - 성공했던 패턴의 카드 데이터 로드"""
        self.demo_cards_database = self._initialize_demo_cards()
        self.display_modes = ['demo', 'hybrid', 'raw', 'enhanced']
        self.current_mode = 'hybrid'  # 기본 모드
        
        logger.info("하이브리드 카드 표시 시스템 초기화 완료")
    
    def _initialize_demo_cards(self) -> List[Dict[str, Any]]:
        """성공했던 패턴에서 얻은 실제 카드 데이터베이스"""
        return [
            {'card': '4♣', 'rank': '4', 'suit': '♣', 'baccarat_value': 4, 'index': 0},
            {'card': '7♦', 'rank': '7', 'suit': '♦', 'baccarat_value': 7, 'index': 1},
            {'card': 'J♠', 'rank': 'J', 'suit': '♠', 'baccarat_value': 0, 'index': 2},
            {'card': '2♠', 'rank': '2', 'suit': '♠', 'baccarat_value': 2, 'index': 3},
            {'card': '2♥', 'rank': '2', 'suit': '♥', 'baccarat_value': 2, 'index': 4},
            {'card': '8♣', 'rank': '8', 'suit': '♣', 'baccarat_value': 8, 'index': 5},
            {'card': '3♥', 'rank': '3', 'suit': '♥', 'baccarat_value': 3, 'index': 6},
            {'card': '9♥', 'rank': '9', 'suit': '♥', 'baccarat_value': 9, 'index': 7},
            {'card': '10♥', 'rank': '10', 'suit': '♥', 'baccarat_value': 0, 'index': 8},
            {'card': 'J♦', 'rank': 'J', 'suit': '♦', 'baccarat_value': 0, 'index': 9},
            {'card': '8♥', 'rank': '8', 'suit': '♥', 'baccarat_value': 8, 'index': 10},
            {'card': '10♥', 'rank': '10', 'suit': '♥', 'baccarat_value': 0, 'index': 11},
            {'card': '2♣', 'rank': '2', 'suit': '♣', 'baccarat_value': 2, 'index': 12},
            {'card': '2♠', 'rank': '2', 'suit': '♠', 'baccarat_value': 2, 'index': 13},
            {'card': 'A♠', 'rank': 'A', 'suit': '♠', 'baccarat_value': 1, 'index': 14},
            {'card': 'A♠', 'rank': 'A', 'suit': '♠', 'baccarat_value': 1, 'index': 15},
            {'card': '5♠', 'rank': '5', 'suit': '♠', 'baccarat_value': 5, 'index': 16},
            {'card': '10♥', 'rank': '10', 'suit': '♥', 'baccarat_value': 0, 'index': 17},
            {'card': '8♠', 'rank': '8', 'suit': '♠', 'baccarat_value': 8, 'index': 18},
            {'card': '5♣', 'rank': '5', 'suit': '♣', 'baccarat_value': 5, 'index': 19},
            {'card': 'K♦', 'rank': 'K', 'suit': '♦', 'baccarat_value': 0, 'index': 20},
            {'card': '6♥', 'rank': '6', 'suit': '♥', 'baccarat_value': 6, 'index': 21},
            {'card': '9♠', 'rank': '9', 'suit': '♠', 'baccarat_value': 9, 'index': 22},
            {'card': '3♦', 'rank': '3', 'suit': '♦', 'baccarat_value': 3, 'index': 23},
            {'card': '7♣', 'rank': '7', 'suit': '♣', 'baccarat_value': 7, 'index': 24},
            {'card': 'Q♥', 'rank': 'Q', 'suit': '♥', 'baccarat_value': 0, 'index': 25},
            {'card': '4♦', 'rank': '4', 'suit': '♦', 'baccarat_value': 4, 'index': 26},
            {'card': '6♠', 'rank': '6', 'suit': '♠', 'baccarat_value': 6, 'index': 27}
        ]
    
    def generate_card_info(self, game_data: Dict[str, Any], game_index: int, mode: str = None) -> Dict[str, Any]:
        """게임 데이터에 대한 카드 정보 생성"""
        display_mode = mode or self.current_mode
        
        if display_mode == 'demo':
            return self._generate_demo_cards(game_data, game_index)
        elif display_mode == 'hybrid':
            return self._generate_hybrid_cards(game_data, game_index)
        elif display_mode == 'enhanced':
            return self._generate_enhanced_cards(game_data, game_index)
        else:  # raw
            return self._generate_raw_cards(game_data, game_index)
    
    def _generate_demo_cards(self, game_data: Dict[str, Any], game_index: int) -> Dict[str, Any]:
        """데모 모드: 성공했던 패턴의 실제 카드 사용"""
        if game_index * 4 + 3 < len(self.demo_cards_database):
            start_idx = game_index * 4
            
            player_cards = [
                self.demo_cards_database[start_idx],
                self.demo_cards_database[start_idx + 1]
            ]
            banker_cards = [
                self.demo_cards_database[start_idx + 2],
                self.demo_cards_database[start_idx + 3]
            ]
            
            # 추가 카드 (자연승이 아닐 경우)
            if not game_data.get('natural', False) and start_idx + 5 < len(self.demo_cards_database):
                # 바카라 규칙에 따른 3번째 카드
                player_total = sum(c['baccarat_value'] for c in player_cards) % 10
                banker_total = sum(c['baccarat_value'] for c in banker_cards) % 10
                
                if player_total <= 5:  # Player가 3번째 카드를 받는 경우
                    player_cards.append(self.demo_cards_database[start_idx + 4])
                    
                if start_idx + 6 < len(self.demo_cards_database):
                    # Banker도 3번째 카드를 받을 수 있음
                    if (banker_total <= 2) or \
                       (banker_total == 3 and len(player_cards) == 3 and player_cards[2]['baccarat_value'] != 8) or \
                       (banker_total == 4 and len(player_cards) == 3 and player_cards[2]['baccarat_value'] in [2,3,4,5,6,7]) or \
                       (banker_total == 5 and len(player_cards) == 3 and player_cards[2]['baccarat_value'] in [4,5,6,7]) or \
                       (banker_total == 6 and len(player_cards) == 3 and player_cards[2]['baccarat_value'] in [6,7]):
                        banker_cards.append(self.demo_cards_database[start_idx + 5])
            
            return {
                'mode': 'demo',
                'status': 'success',
                'player_cards': [f"{c['rank']}{c['suit']}" for c in player_cards],
                'banker_cards': [f"{c['rank']}{c['suit']}" for c in banker_cards],
                'player_details': player_cards,
                'banker_details': banker_cards,
                'calculated_scores': {
                    'player': sum(c['baccarat_value'] for c in player_cards) % 10,
                    'banker': sum(c['baccarat_value'] for c in banker_cards) % 10
                },
                'note': '성공한 패턴의 실제 카드 데이터 사용'
            }
        
        return {'mode': 'demo', 'status': 'insufficient_data', 'note': '데모 카드 부족'}
    
    def _generate_hybrid_cards(self, game_data: Dict[str, Any], game_index: int) -> Dict[str, Any]:
        """하이브리드 모드: 실제 점수 + 데모 카드 조합"""
        demo_result = self._generate_demo_cards(game_data, game_index)
        
        if demo_result.get('status') == 'success':
            # 실제 점수와 데모 카드의 점수 비교
            actual_player = game_data.get('playerScore', 0)
            actual_banker = game_data.get('bankerScore', 0)
            
            calculated = demo_result.get('calculated_scores', {})
            calc_player = calculated.get('player', 0)
            calc_banker = calculated.get('banker', 0)
            
            score_match = (actual_player == calc_player) and (actual_banker == calc_banker)
            
            result = demo_result.copy()
            result.update({
                'mode': 'hybrid',
                'score_verification': {
                    'actual': {'player': actual_player, 'banker': actual_banker},
                    'calculated': {'player': calc_player, 'banker': calc_banker},
                    'match': score_match,
                    'accuracy': '정확' if score_match else '불일치'
                },
                'note': f'데모 카드 사용 (점수 {"일치" if score_match else "불일치"})'
            })
            
            # 점수가 일치하지 않으면 알려진 카드 조합으로 수정 시도
            if not score_match:
                result['corrected_cards'] = self._generate_cards_for_score(actual_player, actual_banker, game_data)
                result['note'] += ' - 점수 맞춤 카드 제공'
            
            return result
        
        # 데모 카드가 없으면 점수 기반 생성
        return self._generate_cards_for_score(
            game_data.get('playerScore', 0), 
            game_data.get('bankerScore', 0), 
            game_data
        )
    
    def _generate_cards_for_score(self, player_score: int, banker_score: int, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """점수에 맞는 카드 조합 생성"""
        import random
        
        # 카드 풀
        suits = ['♠', '♥', '♦', '♣']
        
        # 점수에 맞는 카드 조합 생성
        def create_hand_for_score(target_score: int, has_pair: bool = False) -> List[Dict]:
            cards = []
            
            if has_pair and target_score < 10:
                # 페어가 있는 경우
                if target_score == 0:
                    rank = random.choice(['10', 'J', 'Q', 'K'])
                    value = 0
                else:
                    rank = str(target_score)
                    value = target_score
                
                # 같은 랭크 2장
                suit1, suit2 = random.sample(suits, 2)
                cards = [
                    {'card': f'{rank}{suit1}', 'rank': rank, 'suit': suit1, 'baccarat_value': value},
                    {'card': f'{rank}{suit2}', 'rank': rank, 'suit': suit2, 'baccarat_value': value}
                ]
            else:
                # 일반적인 경우
                ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
                values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 0, 0, 0]
                
                # 2장으로 만들 수 있는 조합 찾기
                for _ in range(20):  # 최대 20번 시도
                    rank1 = random.choice(ranks)
                    rank2 = random.choice(ranks)
                    
                    val1 = values[ranks.index(rank1)]
                    val2 = values[ranks.index(rank2)]
                    
                    if (val1 + val2) % 10 == target_score:
                        suit1, suit2 = random.choices(suits, k=2)
                        cards = [
                            {'card': f'{rank1}{suit1}', 'rank': rank1, 'suit': suit1, 'baccarat_value': val1},
                            {'card': f'{rank2}{suit2}', 'rank': rank2, 'suit': suit2, 'baccarat_value': val2}
                        ]
                        break
                
                # 실패시 기본 조합
                if not cards:
                    if target_score == 0:
                        cards = [
                            {'card': 'K♠', 'rank': 'K', 'suit': '♠', 'baccarat_value': 0},
                            {'card': 'Q♥', 'rank': 'Q', 'suit': '♥', 'baccarat_value': 0}
                        ]
                    else:
                        suit1, suit2 = random.choices(suits, k=2)
                        cards = [
                            {'card': f'A{suit1}', 'rank': 'A', 'suit': suit1, 'baccarat_value': 1},
                            {'card': f'{target_score-1 if target_score > 1 else "A"}{suit2}', 
                             'rank': str(target_score-1) if target_score > 1 else 'A', 
                             'suit': suit2, 'baccarat_value': target_score-1 if target_score > 1 else 1}
                        ]
            
            return cards
        
        player_cards = create_hand_for_score(player_score, game_data.get('playerPair', False))
        banker_cards = create_hand_for_score(banker_score, game_data.get('bankerPair', False))
        
        return {
            'mode': 'score_based',
            'status': 'generated',
            'player_cards': [c['card'] for c in player_cards],
            'banker_cards': [c['card'] for c in banker_cards],
            'player_details': player_cards,
            'banker_details': banker_cards,
            'calculated_scores': {
                'player': sum(c['baccarat_value'] for c in player_cards) % 10,
                'banker': sum(c['baccarat_value'] for c in banker_cards) % 10
            },
            'note': '점수 기반 카드 생성'
        }
    
    def _generate_enhanced_cards(self, game_data: Dict[str, Any], game_index: int) -> Dict[str, Any]:
        """고급 모드: 모든 정보 포함"""
        hybrid_result = self._generate_hybrid_cards(game_data, game_index)
        
        # 추가 정보 포함
        enhanced_info = {
            'game_analysis': {
                'is_natural': game_data.get('natural', False),
                'has_pairs': game_data.get('playerPair', False) or game_data.get('bankerPair', False),
                'winner': game_data.get('winner', 'Unknown'),
                'win_margin': abs(game_data.get('playerScore', 0) - game_data.get('bankerScore', 0))
            },
            'card_statistics': {
                'total_cards': len(hybrid_result.get('player_details', [])) + len(hybrid_result.get('banker_details', [])),
                'high_cards': 0,  # 8, 9, 10, J, Q, K
                'low_cards': 0,   # A, 2, 3
                'mid_cards': 0    # 4, 5, 6, 7
            },
            'probabilities': {
                'natural_odds': '19.64%' if game_data.get('natural', False) else 'N/A',
                'pair_odds': '11.25%' if (game_data.get('playerPair', False) or game_data.get('bankerPair', False)) else 'N/A'
            }
        }
        
        # 카드 통계 계산
        all_cards = hybrid_result.get('player_details', []) + hybrid_result.get('banker_details', [])
        for card in all_cards:
            rank = card.get('rank', '')
            if rank in ['8', '9', '10', 'J', 'Q', 'K']:
                enhanced_info['card_statistics']['high_cards'] += 1
            elif rank in ['A', '2', '3']:
                enhanced_info['card_statistics']['low_cards'] += 1
            else:
                enhanced_info['card_statistics']['mid_cards'] += 1
        
        result = hybrid_result.copy()
        result.update({
            'mode': 'enhanced',
            'enhanced_info': enhanced_info,
            'note': f'{hybrid_result.get("note", "")} + 상세 분석'
        })
        
        return result
    
    def _generate_raw_cards(self, game_data: Dict[str, Any], game_index: int) -> Dict[str, Any]:
        """기본 모드: 인코딩된 정보만 표시"""
        return {
            'mode': 'raw',
            'status': 'encoded_only',
            'encoded_info': f"게임 {game_index + 1}번",
            'note': '인코딩된 형태로만 제공'
        }
    
    def get_available_modes(self) -> Dict[str, str]:
        """사용 가능한 표시 모드 목록"""
        return {
            'demo': '성공 패턴의 실제 카드 데이터 사용',
            'hybrid': '실제 점수 + 데모 카드 조합 (추천)',
            'enhanced': '모든 정보 + 상세 분석 포함',
            'raw': '기본 인코딩 정보만 표시'
        }
    
    def set_display_mode(self, mode: str) -> bool:
        """표시 모드 변경"""
        if mode in self.display_modes:
            self.current_mode = mode
            logger.info(f"카드 표시 모드를 '{mode}'로 변경")
            return True
        return False