#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Pair Detection System - Two Very Auto
실제 패킷 JSON 데이터에서 페어 정보를 정확히 감지하고 표시
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class EnhancedPairDetector:
    """향상된 페어 감지 시스템"""
    
    def __init__(self):
        self.suit_symbols = {'♠': 'Spades', '♥': 'Hearts', '♦': 'Diamonds', '♣': 'Clubs'}
        self.rank_values = {
            'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            '10': 0, 'J': 0, 'Q': 0, 'K': 0
        }
    
    def analyze_packet_data(self, packet_content: str) -> List[Dict[str, Any]]:
        """패킷 데이터에서 페어 정보를 분석"""
        results = []
        
        # 더 안전한 JSON 패킷 찾기 및 파싱
        try:
            # 중괄호 균형을 맞추는 JSON 추출
            json_objects = self._extract_balanced_json_objects(packet_content)
            
            for json_obj in json_objects:
                if '"type":"baccarat.encodedShoeState"' in json_obj:
                    try:
                        packet_data = json.loads(json_obj)
                        pair_info = self.extract_pair_info_from_json(packet_data)
                        if pair_info:
                            results.extend(pair_info)
                    except json.JSONDecodeError:
                        # JSON 파싱 실패를 조용히 처리
                        continue
        except Exception:
            # 모든 오류를 조용히 처리
            pass
        
        return results
    
    def _extract_balanced_json_objects(self, content: str) -> List[str]:
        """중괄호 균형을 맞추는 JSON 객체 추출"""
        json_objects = []
        brace_count = 0
        start_pos = -1
        
        for i, char in enumerate(content):
            if char == '{':
                if brace_count == 0:
                    start_pos = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_pos != -1:
                    json_obj = content[start_pos:i+1]
                    json_objects.append(json_obj)
                    start_pos = -1
        
        return json_objects
    
    def extract_pair_info_from_json(self, packet_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """JSON 데이터에서 페어 정보 추출"""
        pairs_found = []
        
        try:
            args = packet_data.get('args', {})
            history_v2 = args.get('history_v2', [])
            table_id = args.get('tableId', 'unknown')
            timestamp = packet_data.get('time', 0)
            
            for game_index, game_data in enumerate(history_v2):
                pair_detected = self.detect_pairs_in_game(game_data, game_index, table_id, timestamp)
                if pair_detected:
                    pairs_found.append(pair_detected)
        
        except Exception as e:
            logger.error(f"페어 정보 추출 실패: {e}")
        
        return pairs_found
    
    def detect_pairs_in_game(self, game_data: Dict[str, Any], game_index: int, table_id: str, timestamp: int) -> Optional[Dict[str, Any]]:
        """개별 게임에서 페어 감지"""
        
        # 페어 정보가 JSON에 명시적으로 표시됨
        player_pair = game_data.get('playerPair', False)
        banker_pair = game_data.get('bankerPair', False)
        
        if not (player_pair or banker_pair):
            return None
        
        # 페어 정보 구성
        pair_info = {
            'timestamp': datetime.fromtimestamp(timestamp / 1000).isoformat(),
            'table_id': table_id,
            'game_number': game_index + 1,
            'winner': game_data.get('winner', 'Unknown'),
            'player_score': game_data.get('playerScore', 0),
            'banker_score': game_data.get('bankerScore', 0),
            'natural': game_data.get('natural', False),
            'pair_type': [],
            'pair_details': {}
        }
        
        if player_pair:
            pair_info['pair_type'].append('Player Pair')
            pair_info['pair_details']['player_pair'] = {
                'detected': True,
                'description': '플레이어 첫 두 장이 같은 숫자',
                'symbol': '🔴 P',
                'color': 'red'
            }
        
        if banker_pair:
            pair_info['pair_type'].append('Banker Pair')
            pair_info['pair_details']['banker_pair'] = {
                'detected': True,
                'description': '뱅커 첫 두 장이 같은 숫자',
                'symbol': '🔵 B',
                'color': 'blue'
            }
        
        # 양쪽 페어인 경우
        if player_pair and banker_pair:
            pair_info['pair_type'] = ['Both Pairs']
            pair_info['pair_details']['both_pairs'] = {
                'detected': True,
                'description': '플레이어와 뱅커 모두 페어',
                'symbol': '🟡 Both',
                'color': 'gold',
                'rarity': 'Very Rare'
            }
        
        return pair_info
    
    def generate_card_visualization(self, pair_info: Dict[str, Any]) -> Dict[str, Any]:
        """페어에 대한 카드 시각화 생성"""
        
        # 실제 카드는 패킷에서 제공되지 않으므로 시뮬레이션
        # 하지만 페어 발생은 확실히 감지됨
        visualization = {
            'pair_confirmed': True,
            'game_info': {
                'game_number': pair_info['game_number'],
                'winner': pair_info['winner'],
                'player_score': pair_info['player_score'],
                'banker_score': pair_info['banker_score']
            },
            'pair_visualization': []
        }
        
        # 페어 타입별 시각화
        if 'player_pair' in pair_info['pair_details']:
            visualization['pair_visualization'].append({
                'type': 'Player Pair',
                'description': '플레이어 첫 두 장 같은 숫자 확인됨',
                'cards_simulated': self.simulate_pair_cards('player', pair_info['player_score']),
                'color': 'red',
                'icon': '🔴'
            })
        
        if 'banker_pair' in pair_info['pair_details']:
            visualization['pair_visualization'].append({
                'type': 'Banker Pair',
                'description': '뱅커 첫 두 장 같은 숫자 확인됨',
                'cards_simulated': self.simulate_pair_cards('banker', pair_info['banker_score']),
                'color': 'blue',
                'icon': '🔵'
            })
        
        return visualization
    
    def simulate_pair_cards(self, side: str, final_score: int) -> List[Dict[str, str]]:
        """페어 카드 시뮬레이션 (실제 카드 정보가 없으므로)"""
        
        # 최종 점수를 기반으로 가능한 페어 조합 추정
        possible_pairs = []
        
        # 0점 페어 (10, J, Q, K)
        if final_score == 0:
            possible_pairs = [
                [{'card': '10♠', 'rank': '10'}, {'card': '10♥', 'rank': '10'}],
                [{'card': 'J♠', 'rank': 'J'}, {'card': 'J♥', 'rank': 'J'}],
                [{'card': 'Q♠', 'rank': 'Q'}, {'card': 'Q♥', 'rank': 'Q'}],
                [{'card': 'K♠', 'rank': 'K'}, {'card': 'K♥', 'rank': 'K'}]
            ]
        
        # 1점 페어 (A)
        elif final_score == 2:  # A+A = 2
            possible_pairs = [[{'card': 'A♠', 'rank': 'A'}, {'card': 'A♥', 'rank': 'A'}]]
        
        # 4점 페어 (2)
        elif final_score == 4:  # 2+2 = 4
            possible_pairs = [[{'card': '2♠', 'rank': '2'}, {'card': '2♥', 'rank': '2'}]]
        
        # 6점 페어 (3)
        elif final_score == 6:  # 3+3 = 6
            possible_pairs = [[{'card': '3♠', 'rank': '3'}, {'card': '3♥', 'rank': '3'}]]
        
        # 8점 페어 (4)
        elif final_score == 8:  # 4+4 = 8
            possible_pairs = [[{'card': '4♠', 'rank': '4'}, {'card': '4♥', 'rank': '4'}]]
        
        # 기타 점수의 경우 일반적인 페어
        else:
            rank = str(min(final_score, 9))
            possible_pairs = [[{'card': f'{rank}♠', 'rank': rank}, {'card': f'{rank}♥', 'rank': rank}]]
        
        # 첫 번째 가능한 조합 반환
        return possible_pairs[0] if possible_pairs else []
    
    def process_packet_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """패킷 파일 전체 처리"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            pairs_found = self.analyze_packet_data(content)
            
            # 각 페어에 대해 시각화 추가
            enhanced_pairs = []
            for pair in pairs_found:
                pair['visualization'] = self.generate_card_visualization(pair)
                pair['source_file'] = str(file_path.name)
                enhanced_pairs.append(pair)
            
            return enhanced_pairs
            
        except Exception as e:
            logger.error(f"파일 처리 실패 {file_path}: {e}")
            return []
    
    def get_pair_statistics(self, pairs_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """페어 통계 생성"""
        if not pairs_data:
            return {'total_pairs': 0}
        
        player_pairs = sum(1 for p in pairs_data if 'player_pair' in p.get('pair_details', {}))
        banker_pairs = sum(1 for p in pairs_data if 'banker_pair' in p.get('pair_details', {}))
        both_pairs = sum(1 for p in pairs_data if 'both_pairs' in p.get('pair_details', {}))
        
        return {
            'total_pairs': len(pairs_data),
            'player_pairs': player_pairs,
            'banker_pairs': banker_pairs,
            'both_pairs': both_pairs,
            'pair_rate': len(pairs_data) / max(1, len(pairs_data)) * 100,
            'most_recent': pairs_data[-1]['timestamp'] if pairs_data else None
        }

# 전역 인스턴스
enhanced_pair_detector = EnhancedPairDetector()