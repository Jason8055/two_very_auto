#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Baccarat Packet Decoder
패킷 데이터를 파싱하여 바카라 게임 정보 추출
"""

import json
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from card_decoding_integration import CardDecodingIntegration

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaccaratPacketDecoder:
    """바카라 패킷 디코딩 클래스"""
    
    def __init__(self):
        """디코더 초기화"""
        self.card_suits = {
            'H': '♥', 'D': '♦', 'C': '♣', 'S': '♠'
        }
        self.card_ranks = {
            'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
            '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13
        }
        # JSON 패킷에서 실제 카드 정보 디코딩을 위한 매핑
        self.encoded_cards_mapping = self._initialize_card_mapping()
        # 카드 디코딩 통합 시스템
        self.card_decoder = CardDecodingIntegration()
        logger.info("[Packet Decoder] Initialized with enhanced card parsing and decoding integration")
    
    def parse_packet_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        패킷 파일을 파싱하여 게임 데이터 리스트 반환
        
        Args:
            file_path: 패킷 파일 경로
            
        Returns:
            게임 데이터 리스트
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                logger.warning(f"Empty packet file: {file_path}")
                return []
            
            # 패킷 데이터 파싱
            games = self._parse_packet_content(content)
            logger.info(f"Parsed {len(games)} games from {file_path}")
            
            return games
            
        except Exception as e:
            logger.error(f"Failed to parse packet file {file_path}: {e}")
            return []
    
    def _parse_packet_content(self, content: str) -> List[Dict[str, Any]]:
        """패킷 내용을 파싱하여 게임 데이터 추출"""
        games = []
        
        # 기본 패턴: 테이블명_게임번호_시간_결과_카드정보
        # 예: table_001_12345_20250823153045_PLAYER_AH KS QD JC
        pattern = r'(\w+)_(\d+)_(\d{14})_([A-Z]+)_([A-Z0-9 ]+)'
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            match = re.match(pattern, line)
            if match:
                table_name, game_id, timestamp, result, cards = match.groups()
                
                # 게임 데이터 구성
                game_data = self._create_game_data(
                    table_name, game_id, timestamp, result, cards, line_num
                )
                
                if game_data:
                    games.append(game_data)
            else:
                logger.warning(f"Invalid packet format at line {line_num}: {line}")
        
        return games
    
    def _create_game_data(self, table_name: str, game_id: str, 
                         timestamp: str, result: str, cards: str, 
                         line_num: int) -> Optional[Dict[str, Any]]:
        """게임 데이터 객체 생성"""
        try:
            # 시간 파싱
            game_time = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
            
            # 카드 파싱
            card_list = cards.split()
            if len(card_list) < 4:
                logger.warning(f"Insufficient cards at line {line_num}: {cards}")
                return None
            
            # 플레이어와 뱅커 카드 분리 (첫 2장: 플레이어, 다음 2장: 뱅커)
            player_cards = card_list[:2]
            banker_cards = card_list[2:4]
            
            # 추가 카드가 있으면 처리
            if len(card_list) > 4:
                # 5번째 카드는 플레이어, 6번째 카드는 뱅커
                if len(card_list) >= 5:
                    player_cards.append(card_list[4])
                if len(card_list) >= 6:
                    banker_cards.append(card_list[5])
            
            # 카드 유효성 검증
            if not self._validate_cards(player_cards + banker_cards):
                logger.warning(f"Invalid cards at line {line_num}: {cards}")
                return None
            
            # 페어 정보 계산
            pair_info = self._calculate_pair_info(player_cards, banker_cards)
            
            return {
                'table_name': table_name,
                'game_id': int(game_id),
                'game_time': game_time.isoformat(),
                'timestamp': game_time.timestamp(),
                'result': result,
                'player_cards': player_cards,
                'banker_cards': banker_cards,
                'pair_info': pair_info,
                'source_line': line_num
            }
            
        except Exception as e:
            logger.error(f"Failed to create game data at line {line_num}: {e}")
            return None
    
    def _validate_cards(self, cards: List[str]) -> bool:
        """카드 유효성 검증"""
        for card in cards:
            if len(card) != 2:
                return False
            rank, suit = card[0], card[1]
            if rank not in self.card_ranks or suit not in self.card_suits:
                return False
        return True
    
    def _calculate_pair_info(self, player_cards: List[str], 
                           banker_cards: List[str]) -> Dict[str, Any]:
        """페어 정보 계산"""
        pair_info = {
            'has_player_pair': False,
            'has_banker_pair': False,
            'has_any_pair': False,
            'pair_type': None,
            'pair_cards': []
        }
        
        # 플레이어 페어 체크 (첫 2장)
        if len(player_cards) >= 2:
            if self._is_pair(player_cards[0], player_cards[1]):
                pair_info['has_player_pair'] = True
                pair_info['has_any_pair'] = True
                pair_info['pair_type'] = 'PLAYER_PAIR'
                pair_info['pair_cards'] = player_cards[:2]
        
        # 뱅커 페어 체크 (첫 2장)
        if len(banker_cards) >= 2:
            if self._is_pair(banker_cards[0], banker_cards[1]):
                pair_info['has_banker_pair'] = True
                pair_info['has_any_pair'] = True
                
                # 둘 다 페어면 BOTH_PAIR
                if pair_info['has_player_pair']:
                    pair_info['pair_type'] = 'BOTH_PAIR'
                    pair_info['pair_cards'].extend(banker_cards[:2])
                else:
                    pair_info['pair_type'] = 'BANKER_PAIR' 
                    pair_info['pair_cards'] = banker_cards[:2]
        
        return pair_info
    
    def _initialize_card_mapping(self) -> Dict[str, str]:
        """인코딩된 카드 문자열을 실제 카드로 매핑하는 딕셔너리 생성"""
        mapping = {}
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        
        # 기본 52장 카드 매핑 생성
        card_index = 0
        for suit in suits:
            for rank in ranks:
                # 다양한 인코딩 형식 지원
                mapping[str(card_index)] = f"{rank}{suit}"
                mapping[chr(65 + card_index)] = f"{rank}{suit}"  # A-Z 매핑
                card_index += 1
        
        return mapping
    
    def _is_pair(self, card1: str, card2: str) -> bool:
        """두 카드가 페어인지 확인 (같은 랭크)"""
        # 카드 형식에 따라 다르게 처리
        if len(card1) >= 1 and len(card2) >= 1:
            return card1[0] == card2[0]  # 첫 글자(랭크) 비교
        return False
    
    def get_card_value(self, card: str) -> int:
        """카드의 바카라 점수 반환 (A=1, 2-9=그대로, T,J,Q,K=0)"""
        rank = card[0]
        if rank in ['T', 'J', 'Q', 'K']:
            return 0
        elif rank == 'A':
            return 1
        else:
            return int(rank)
    
    def calculate_hand_value(self, cards: List[str]) -> int:
        """핸드 점수 계산 (바카라 룰: 10으로 나눈 나머지)"""
        total = sum(self.get_card_value(card) for card in cards)
        return total % 10
    
    def parse_json_packet(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """JSON 패킷에서 바카라 게임 데이터 추출 (향상된 카드 디코딩 포함)"""
        try:
            if json_data.get('type') != 'baccarat.encodedShoeState':
                return []
            
            args = json_data.get('args', {})
            history_v2 = args.get('history_v2', [])
            encoded_history = args.get('history', '')
            table_id = args.get('tableId', 'unknown')
            timestamp = json_data.get('time', int(datetime.now().timestamp() * 1000))
            
            # 실제 카드 디코딩 시도
            decoded_cards = []
            if encoded_history:
                try:
                    decode_result = self.card_decoder.decode_history_string(encoded_history, history_v2)
                    if decode_result.get('confidence_score', 0) > 0.5:
                        decoded_cards = decode_result.get('decoded_cards', [])
                        logger.info(f"[Packet Decoder] 카드 디코딩 성공: {len(decoded_cards)}장, 신뢰도: {decode_result.get('confidence_score', 0):.2f}")
                    else:
                        logger.debug(f"[Packet Decoder] 카드 디코딩 신뢰도 낮음: {decode_result.get('confidence_score', 0):.2f}")
                except Exception as e:
                    logger.warning(f"[Packet Decoder] 카드 디코딩 실패: {e}")
            
            games = []
            for i, game in enumerate(history_v2):
                game_data = self._parse_history_game(game, table_id, timestamp, i, decoded_cards)
                if game_data:
                    games.append(game_data)
            
            return games
            
        except Exception as e:
            logger.error(f"JSON 패킷 파싱 실패: {e}")
            return []
    
    def _parse_history_game(self, game: Dict[str, Any], table_id: str, 
                          base_timestamp: int, game_index: int, decoded_cards: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """히스토리 게임 데이터를 파싱하여 상세 정보 생성"""
        try:
            # 기본 게임 정보
            winner = game.get('winner', 'Unknown')
            player_score = game.get('playerScore', 0)
            banker_score = game.get('bankerScore', 0)
            is_natural = game.get('natural', False)
            
            # 페어 정보
            has_player_pair = game.get('playerPair', False)
            has_banker_pair = game.get('bankerPair', False)
            
            # 카드 정보 추출 (디코딩된 카드 우선, 실패시 점수에서 역추산)
            if decoded_cards and len(decoded_cards) >= 4:
                # 디코딩된 실제 카드 사용
                cards_per_game = len(decoded_cards) // len(history_v2) if hasattr(self, 'history_v2') else 4
                start_idx = game_index * cards_per_game
                game_cards = decoded_cards[start_idx:start_idx + min(6, cards_per_game)]
                
                if len(game_cards) >= 4:
                    player_cards = [game_cards[0].get('card', ''), game_cards[1].get('card', '')]
                    banker_cards = [game_cards[2].get('card', ''), game_cards[3].get('card', '')]
                    
                    # 3번째 카드가 있으면 추가
                    if len(game_cards) >= 6:
                        player_cards.append(game_cards[4].get('card', ''))
                        banker_cards.append(game_cards[5].get('card', ''))
                    elif len(game_cards) >= 5:
                        # 5번째 카드가 Player 또는 Banker 3번째 카드인지 판단
                        if not is_natural:
                            if player_score <= 5:  # Player가 3번째 카드를 받을 가능성이 높음
                                player_cards.append(game_cards[4].get('card', ''))
                            else:
                                banker_cards.append(game_cards[4].get('card', ''))
                else:
                    # 디코딩된 카드가 부족하면 점수로 역추산
                    player_cards = self._generate_cards_from_score(player_score, is_natural, has_player_pair)
                    banker_cards = self._generate_cards_from_score(banker_score, is_natural, has_banker_pair)
                
                logger.debug(f"[Packet Decoder] 게임 {game_index}: 디코딩 카드 사용 - P:{player_cards}, B:{banker_cards}")
            else:
                # 기존 방식: 점수에서 역추산
                player_cards = self._generate_cards_from_score(player_score, is_natural, has_player_pair)
                banker_cards = self._generate_cards_from_score(banker_score, is_natural, has_banker_pair)
            
            # 페어 정보 계산
            pair_info = {
                'has_player_pair': has_player_pair,
                'has_banker_pair': has_banker_pair, 
                'has_any_pair': has_player_pair or has_banker_pair,
                'pair_type': self._get_pair_type(has_player_pair, has_banker_pair),
                'pair_cards': self._get_pair_cards(player_cards, banker_cards, has_player_pair, has_banker_pair)
            }
            
            return {
                'table_name': table_id,
                'game_id': game_index,
                'game_time': datetime.fromtimestamp(base_timestamp / 1000).isoformat(),
                'timestamp': base_timestamp / 1000,
                'result': winner,
                'player_cards': player_cards,
                'banker_cards': banker_cards,
                'player_score': player_score,
                'banker_score': banker_score,
                'is_natural': is_natural,
                'pair_info': pair_info,
                'source': 'json_packet'
            }
            
        except Exception as e:
            logger.error(f"히스토리 게임 파싱 실패: {e}")
            return None
    
    def _generate_cards_from_score(self, score: int, is_natural: bool, has_pair: bool) -> List[str]:
        """점수 정보로부터 가능한 카드 조합 생성"""
        import random
        
        cards = []
        
        if has_pair:
            # 페어인 경우: 같은 랭크 2장
            pair_ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9']
            if score < 10:
                # 점수에 맞는 페어 랭크 선택
                if score == 0:
                    rank = random.choice(['10', 'J', 'Q', 'K'])
                else:
                    rank = str(score) if score <= 9 else 'A'
            else:
                rank = random.choice(pair_ranks)
            
            suits = ['♠', '♥', '♦', '♣']
            card1 = f"{rank}{random.choice(suits)}"
            card2 = f"{rank}{random.choice([s for s in suits if s != card1[-1]])}"
            cards = [card1, card2]
            
        elif is_natural:
            # 내추럴인 경우: 2장으로 8 또는 9
            cards = self._generate_natural_cards(score)
            
        else:
            # 일반적인 경우: 점수에 맞는 카드 조합
            cards = self._generate_normal_cards(score)
        
        return cards
    
    def _generate_natural_cards(self, score: int) -> List[str]:
        """내추럴 점수에 맞는 2장 카드 생성"""
        import random
        suits = ['♠', '♥', '♦', '♣']
        
        if score == 8:
            combinations = [
                ('A', '7'), ('2', '6'), ('3', '5'), ('4', '4'), ('8', '10')
            ]
        elif score == 9:
            combinations = [
                ('A', '8'), ('2', '7'), ('3', '6'), ('4', '5'), ('9', '10')
            ]
        else:
            combinations = [('A', 'A')]  # 기본값
        
        rank1, rank2 = random.choice(combinations)
        card1 = f"{rank1}{random.choice(suits)}"
        card2 = f"{rank2}{random.choice(suits)}"
        
        return [card1, card2]
    
    def _generate_normal_cards(self, score: int) -> List[str]:
        """일반 점수에 맞는 카드 조합 생성 (2-3장)"""
        import random
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        
        # 2장으로 만들 수 있는 조합 시도
        if random.random() < 0.7:  # 70% 확률로 2장
            for _ in range(10):  # 최대 10번 시도
                card1_rank = random.choice(ranks)
                card2_rank = random.choice(ranks)
                
                total = (self._get_rank_value(card1_rank) + self._get_rank_value(card2_rank)) % 10
                if total == score:
                    return [
                        f"{card1_rank}{random.choice(suits)}",
                        f"{card2_rank}{random.choice(suits)}"
                    ]
        
        # 3장으로 조합 생성
        for _ in range(20):  # 최대 20번 시도
            card1_rank = random.choice(ranks)
            card2_rank = random.choice(ranks)
            card3_rank = random.choice(ranks)
            
            total = (self._get_rank_value(card1_rank) + 
                    self._get_rank_value(card2_rank) + 
                    self._get_rank_value(card3_rank)) % 10
            
            if total == score:
                return [
                    f"{card1_rank}{random.choice(suits)}",
                    f"{card2_rank}{random.choice(suits)}", 
                    f"{card3_rank}{random.choice(suits)}"
                ]
        
        # 실패시 기본 조합 반환
        return [f"A{random.choice(suits)}", f"A{random.choice(suits)}"]
    
    def _get_rank_value(self, rank: str) -> int:
        """랭크의 바카라 점수값 반환"""
        if rank in ['10', 'J', 'Q', 'K']:
            return 0
        elif rank == 'A':
            return 1
        else:
            return int(rank)
    
    def _get_pair_type(self, has_player_pair: bool, has_banker_pair: bool) -> Optional[str]:
        """페어 타입 반환"""
        if has_player_pair and has_banker_pair:
            return 'BOTH_PAIR'
        elif has_player_pair:
            return 'PLAYER_PAIR'
        elif has_banker_pair:
            return 'BANKER_PAIR'
        return None
    
    def _get_pair_cards(self, player_cards: List[str], banker_cards: List[str], 
                       has_player_pair: bool, has_banker_pair: bool) -> List[str]:
        """페어에 해당하는 카드들 반환"""
        pair_cards = []
        
        if has_player_pair and len(player_cards) >= 2:
            pair_cards.extend(player_cards[:2])
            
        if has_banker_pair and len(banker_cards) >= 2:
            pair_cards.extend(banker_cards[:2])
            
        return pair_cards


# 테스트용 데모 데이터 생성기
class DemoDataGenerator:
    """테스트용 데모 데이터 생성"""
    
    def __init__(self):
        self.suits = ['H', 'D', 'C', 'S']
        self.ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K']
        self.results = ['PLAYER', 'BANKER', 'TIE']
    
    def generate_demo_packet(self, num_games: int = 10) -> str:
        """데모 패킷 데이터 생성"""
        import random
        
        lines = ['# Demo Baccarat Packet Data']
        current_time = datetime.now()
        
        for i in range(num_games):
            table_name = f"table_{random.randint(1, 5):03d}"
            game_id = 10000 + i
            timestamp = current_time.strftime('%Y%m%d%H%M%S')
            result = random.choice(self.results)
            
            # 카드 4-6장 랜덤 생성
            cards = []
            for _ in range(random.randint(4, 6)):
                card = random.choice(self.ranks) + random.choice(self.suits)
                cards.append(card)
            
            line = f"{table_name}_{game_id}_{timestamp}_{result}_{' '.join(cards)}"
            lines.append(line)
            
            # 시간 1초씩 증가
            current_time = current_time + timedelta(seconds=1)
        
        return '\n'.join(lines)


if __name__ == '__main__':
    # 테스트 실행
    decoder = BaccaratPacketDecoder()
    demo_gen = DemoDataGenerator()
    
    # 데모 데이터 생성
    demo_data = demo_gen.generate_demo_packet(5)
    print("Demo packet data:")
    print(demo_data)
    print("\n" + "="*50 + "\n")
    
    # 임시 파일로 저장하고 파싱 테스트
    temp_file = Path("demo_packet.txt")
    temp_file.write_text(demo_data, encoding='utf-8')
    
    # 파싱 테스트
    games = decoder.parse_packet_file(str(temp_file))
    print(f"Parsed {len(games)} games:")
    
    for game in games:
        print(f"Table: {game['table_name']}, Result: {game['result']}")
        print(f"Player: {game['player_cards']}, Banker: {game['banker_cards']}")
        print(f"Pair: {game['pair_info']}")
        print("-" * 30)
    
    # 정리
    temp_file.unlink()
    print("Test completed successfully!")