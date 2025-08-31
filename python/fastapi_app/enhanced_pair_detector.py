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
        # JSON 검증 패턴 미리 컴파일
        self.baccarat_pattern = re.compile(r'"type":\s*"baccarat\.encodedShoeState"')
        self.json_start_pattern = re.compile(r'\{["\s]')
    
    def analyze_packet_data(self, packet_content: str) -> List[Dict[str, Any]]:
        """패킷 데이터에서 페어 정보를 분석 (완전 무음 처리)"""
        results = []
        
        try:
            # 바카라 패킷이 없으면 즉시 반환
            if not self.baccarat_pattern.search(packet_content):
                return results
            
            # 스마트한 JSON 추출 및 파싱
            json_objects = self._extract_smart_json_objects(packet_content)
            
            for json_obj in json_objects:
                try:
                    # 빠른 기본 검증
                    if not self._is_valid_json_format(json_obj):
                        continue
                        
                    packet_data = json.loads(json_obj)
                    pair_info = self.extract_pair_info_from_json(packet_data)
                    if pair_info:
                        results.extend(pair_info)
                except:
                    # 모든 파싱 실패를 완전히 무시 (로그 없음)
                    pass
        except:
            # 모든 오류를 완전히 무시
            pass
        
        return results
    
    def _extract_smart_json_objects(self, content: str) -> List[str]:
        """스마트한 JSON 객체 추출 (성능 최적화)"""
        json_objects = []
        brace_count = 0
        start_pos = -1
        content_len = len(content)
        
        i = 0
        while i < content_len:
            char = content[i]
            if char == '{':
                if brace_count == 0:
                    start_pos = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_pos != -1:
                    json_obj = content[start_pos:i+1]
                    # 기본 바카라 체크만 수행
                    if '"type":"baccarat.encodedShoeState"' in json_obj:
                        json_objects.append(json_obj)
                    start_pos = -1
            i += 1
        
        return json_objects
    
    def _is_valid_json_format(self, json_str: str) -> bool:
        """JSON 문자열 기본 형식 검증 (파싱 전 빠른 체크)"""
        if not json_str or len(json_str) < 10:
            return False
        
        # 기본 중괄호 체크
        if not (json_str.startswith('{') and json_str.endswith('}')):
            return False
            
        # 중괄호 개수 체크
        if json_str.count('{') != json_str.count('}'):
            return False
            
        # 기본적인 JSON 패턴 체크
        if not self.json_start_pattern.match(json_str):
            return False
            
        return True
    
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
        """페어 카드 시뮬레이션 - 같은 무늬 같은 숫자 페어만 표시"""
        
        # 실제 페어는 같은 무늬의 같은 숫자여야 함
        # 점수를 기반으로 가능한 페어 카드 추정
        import random
        
        suits = ['♠', '♥', '♦', '♣']
        
        # 점수별 페어 가능 카드들
        if final_score == 0:
            # 0점이 되는 페어: 10-10, J-J, Q-Q, K-K
            ranks = ['10', 'J', 'Q', 'K']
            rank = random.choice(ranks)
        elif final_score == 2:
            # 2점이 되는 페어: A-A (1+1=2)
            rank = 'A'
        elif final_score == 4:
            # 4점이 되는 페어: 2-2 (2+2=4)
            rank = '2'
        elif final_score == 6:
            # 6점이 되는 페어: 3-3 (3+3=6)
            rank = '3'
        elif final_score == 8:
            # 8점이 되는 페어: 4-4 (4+4=8)
            rank = '4'
        else:
            # 기타 점수 (홀수 점수는 실제로 페어로 만들 수 없음)
            # 하지만 시뮬레이션을 위해 가장 가까운 값 사용
            if final_score <= 9:
                rank = str(final_score)
            else:
                rank = str(final_score % 10)
        
        # 같은 무늬 선택
        suit = random.choice(suits)
        
        # 같은 무늬의 같은 카드 2장 반환
        return [
            {'card': f'{rank}{suit}', 'rank': rank},
            {'card': f'{rank}{suit}', 'rank': rank}
        ]
    
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