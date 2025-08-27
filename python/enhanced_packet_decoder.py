#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
향상된 패킷 디코더 - 실시간 JSON 처리 지원
기존 packet_decoder.py를 확장하여 실시간 스트리밍 데이터 처리 지원
"""

import json
import re
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
import asyncio
import threading
from queue import Queue, Empty

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BaccaratGameData:
    """바카라 게임 데이터 구조체"""
    game_id: str
    table_id: str
    game_count: int
    timestamp: float
    iso_timestamp: str
    player_score: int
    banker_score: int
    winner: str
    natural: bool = False
    player_pair: bool = False
    banker_pair: bool = False
    player_cards: List[str] = None
    banker_cards: List[str] = None
    encoded_history: str = ""
    source_file: str = ""
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.player_cards is None:
            self.player_cards = []
        if self.banker_cards is None:
            self.banker_cards = []


class EnhancedPacketDecoder:
    """향상된 패킷 디코더 - JSON 및 실시간 처리 지원"""
    
    def __init__(self):
        """디코더 초기화"""
        self.card_mapping = self._initialize_card_mapping()
        self.history_decoder = HistoryDecoder()
        self.statistics = {
            'total_processed': 0,
            'json_packets': 0,
            'text_packets': 0,
            'errors': 0,
            'last_update': datetime.now()
        }
        logger.info("향상된 패킷 디코더 초기화 완료")
    
    def _initialize_card_mapping(self) -> Dict[str, str]:
        """카드 매핑 초기화"""
        suits_map = {'H': '♥', 'D': '♦', 'C': '♣', 'S': '♠'}
        ranks_map = {'A': 'A', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', 
                    '7': '7', '8': '8', '9': '9', 'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K'}
        
        mapping = {}
        for suit_key, suit_symbol in suits_map.items():
            for rank_key, rank_value in ranks_map.items():
                card_code = f"{rank_key}{suit_key}"
                mapping[card_code] = f"{rank_value}{suit_symbol}"
        
        return mapping
    
    def parse_packet_file(self, file_path: str) -> List[BaccaratGameData]:
        """
        패킷 파일을 파싱하여 게임 데이터 반환
        JSON과 텍스트 형식을 모두 지원
        """
        start_time = time.time()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                logger.warning(f"빈 패킷 파일: {file_path}")
                return []
            
            # JSON 형식인지 확인
            games = []
            if content.strip().startswith('{') or content.strip().startswith('['):
                games = self._parse_json_content(content, file_path)
                self.statistics['json_packets'] += 1
            else:
                games = self._parse_text_content(content, file_path)
                self.statistics['text_packets'] += 1
            
            # 처리 시간 기록
            processing_time = time.time() - start_time
            for game in games:
                game.processing_time = processing_time
            
            self.statistics['total_processed'] += len(games)
            self.statistics['last_update'] = datetime.now()
            
            logger.info(f"📦 파일 처리 완료: {Path(file_path).name} - {len(games)}개 게임 ({processing_time:.3f}초)")
            return games
            
        except Exception as e:
            logger.error(f"패킷 파일 파싱 실패 {file_path}: {e}", exc_info=True)
            self.statistics['errors'] += 1
            return []
    
    def _parse_json_content(self, content: str, file_path: str) -> List[BaccaratGameData]:
        """JSON 형식 패킷 내용 파싱"""
        games = []
        
        try:
            # 여러 줄의 JSON 객체 처리
            lines = content.strip().split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    # JSON 라인 파싱
                    json_data = json.loads(line)
                    
                    # baccarat.encodedShoeState 타입 처리
                    if json_data.get('type') == 'baccarat.encodedShoeState':
                        parsed_games = self._parse_encoded_shoe_state(json_data, file_path, line_num)
                        games.extend(parsed_games)
                    
                    # 기타 JSON 형식 처리
                    else:
                        game_data = self._parse_generic_json(json_data, file_path, line_num)
                        if game_data:
                            games.append(game_data)
                
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON 파싱 오류 {file_path}:{line_num} - {e}")
                    continue
                except Exception as e:
                    logger.error(f"JSON 데이터 처리 오류 {file_path}:{line_num} - {e}")
                    continue
        
        except Exception as e:
            logger.error(f"JSON 콘텐츠 파싱 실패 {file_path}: {e}")
        
        return games
    
    def _parse_encoded_shoe_state(self, json_data: Dict[str, Any], file_path: str, line_num: int) -> List[BaccaratGameData]:
        """encodedShoeState JSON 데이터 파싱"""
        games = []
        
        try:
            args = json_data.get('args', {})
            history_v2 = args.get('history_v2', [])
            table_id = args.get('tableId', 'unknown')
            timestamp = json_data.get('time', 0) / 1000.0  # 밀리초를 초로 변환
            
            # 각 게임 기록을 처리
            for game_idx, game_record in enumerate(history_v2):
                try:
                    game_data = BaccaratGameData(
                        game_id=f"{table_id}_{game_idx + 1}",
                        table_id=table_id,
                        game_count=game_idx + 1,
                        timestamp=timestamp,
                        iso_timestamp=datetime.fromtimestamp(timestamp).isoformat(),
                        player_score=game_record.get('playerScore', 0),
                        banker_score=game_record.get('bankerScore', 0),
                        winner=game_record.get('winner', 'Unknown'),
                        natural=game_record.get('natural', False),
                        player_pair=game_record.get('playerPair', False),
                        banker_pair=game_record.get('bankerPair', False),
                        encoded_history=args.get('history', ''),
                        source_file=file_path
                    )
                    
                    games.append(game_data)
                
                except Exception as e:
                    logger.error(f"게임 레코드 처리 오류 {file_path}:{line_num}[{game_idx}] - {e}")
                    continue
        
        except Exception as e:
            logger.error(f"encodedShoeState 파싱 오류 {file_path}:{line_num} - {e}")
        
        return games
    
    def _parse_generic_json(self, json_data: Dict[str, Any], file_path: str, line_num: int) -> Optional[BaccaratGameData]:
        """일반 JSON 형식 파싱"""
        try:
            # 기본적인 JSON 구조에서 게임 데이터 추출
            game_data = BaccaratGameData(
                game_id=json_data.get('id', f"generic_{line_num}"),
                table_id=json_data.get('table', 'unknown'),
                game_count=json_data.get('game_count', 0),
                timestamp=json_data.get('timestamp', time.time()),
                iso_timestamp=datetime.fromtimestamp(json_data.get('timestamp', time.time())).isoformat(),
                player_score=json_data.get('player_score', 0),
                banker_score=json_data.get('banker_score', 0),
                winner=json_data.get('winner', 'Unknown'),
                source_file=file_path
            )
            
            return game_data
        
        except Exception as e:
            logger.error(f"일반 JSON 파싱 오류 {file_path}:{line_num} - {e}")
            return None
    
    def _parse_text_content(self, content: str, file_path: str) -> List[BaccaratGameData]:
        """텍스트 형식 패킷 내용 파싱 (기존 형식 지원)"""
        games = []
        
        # 기존 텍스트 패턴 처리
        pattern = r'(\w+)_(\d+)_(\d{14})_([A-Z]+)_([A-Z0-9 ]+)'
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            match = re.match(pattern, line)
            if match:
                table_name, game_id, timestamp_str, result, cards = match.groups()
                
                try:
                    # 시간 파싱
                    game_time = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                    
                    game_data = BaccaratGameData(
                        game_id=f"{table_name}_{game_id}",
                        table_id=table_name,
                        game_count=int(game_id),
                        timestamp=game_time.timestamp(),
                        iso_timestamp=game_time.isoformat(),
                        player_score=0,  # 텍스트에서 점수 계산 필요
                        banker_score=0,  # 텍스트에서 점수 계산 필요
                        winner=result,
                        source_file=file_path
                    )
                    
                    # 카드 정보 파싱
                    card_list = cards.split()
                    if len(card_list) >= 4:
                        game_data.player_cards = card_list[:2]
                        game_data.banker_cards = card_list[2:4]
                        
                        # 추가 카드 처리
                        if len(card_list) > 4:
                            if len(card_list) >= 5:
                                game_data.player_cards.append(card_list[4])
                            if len(card_list) >= 6:
                                game_data.banker_cards.append(card_list[5])
                        
                        # 점수 계산
                        game_data.player_score = self._calculate_score(game_data.player_cards)
                        game_data.banker_score = self._calculate_score(game_data.banker_cards)
                        
                        # 페어 체크
                        if len(game_data.player_cards) >= 2:
                            game_data.player_pair = self._is_pair(game_data.player_cards[0], game_data.player_cards[1])
                        if len(game_data.banker_cards) >= 2:
                            game_data.banker_pair = self._is_pair(game_data.banker_cards[0], game_data.banker_cards[1])
                    
                    games.append(game_data)
                
                except Exception as e:
                    logger.error(f"텍스트 데이터 처리 오류 {file_path}:{line_num} - {e}")
                    continue
            else:
                logger.warning(f"텍스트 패턴 불일치 {file_path}:{line_num}: {line}")
        
        return games
    
    def _calculate_score(self, cards: List[str]) -> int:
        """바카라 점수 계산"""
        total = 0
        for card in cards:
            if len(card) >= 1:
                rank = card[0]
                if rank in ['A']:
                    total += 1
                elif rank in ['2', '3', '4', '5', '6', '7', '8', '9']:
                    total += int(rank)
                elif rank in ['T', 'J', 'Q', 'K']:
                    total += 0
        return total % 10
    
    def _is_pair(self, card1: str, card2: str) -> bool:
        """두 카드가 페어인지 확인"""
        if len(card1) >= 1 and len(card2) >= 1:
            return card1[0] == card2[0]
        return False
    
    def parse_realtime_data(self, data: Union[str, Dict[str, Any]], source: str = "realtime") -> List[BaccaratGameData]:
        """실시간 데이터 파싱 (문자열 또는 딕셔너리)"""
        try:
            if isinstance(data, str):
                # JSON 문자열 파싱
                if data.strip().startswith('{'):
                    json_data = json.loads(data)
                    return self._parse_encoded_shoe_state(json_data, source, 1)
                else:
                    # 텍스트 형식 파싱
                    return self._parse_text_content(data, source)
            
            elif isinstance(data, dict):
                # 딕셔너리 직접 파싱
                if data.get('type') == 'baccarat.encodedShoeState':
                    return self._parse_encoded_shoe_state(data, source, 1)
                else:
                    game_data = self._parse_generic_json(data, source, 1)
                    return [game_data] if game_data else []
            
            else:
                logger.warning(f"지원하지 않는 데이터 형식: {type(data)}")
                return []
        
        except Exception as e:
            logger.error(f"실시간 데이터 파싱 오류: {e}", exc_info=True)
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """처리 통계 반환"""
        return {
            **self.statistics,
            'last_update': self.statistics['last_update'].isoformat(),
            'success_rate': (
                (self.statistics['total_processed'] / 
                 max(self.statistics['total_processed'] + self.statistics['errors'], 1)) * 100
            )
        }
    
    def reset_statistics(self):
        """통계 초기화"""
        self.statistics = {
            'total_processed': 0,
            'json_packets': 0,
            'text_packets': 0,
            'errors': 0,
            'last_update': datetime.now()
        }


class HistoryDecoder:
    """인코딩된 히스토리 문자열 디코더"""
    
    def __init__(self):
        self.history_mapping = self._initialize_history_mapping()
    
    def _initialize_history_mapping(self) -> Dict[str, Dict[str, str]]:
        """히스토리 매핑 테이블 초기화"""
        # 실제 인코딩 규칙에 맞게 수정 필요
        return {
            'winner': {'P': 'Player', 'B': 'Banker', 'T': 'Tie'},
            'natural': {'N': True, '': False},
            'pair': {'PP': 'PlayerPair', 'BP': 'BankerPair', 'BOTH': 'BothPair'}
        }
    
    def decode_history(self, encoded_history: str) -> List[Dict[str, Any]]:
        """인코딩된 히스토리 문자열을 게임 리스트로 변환"""
        # 실제 디코딩 로직 구현 필요
        # 현재는 샘플 구현
        try:
            games = []
            # 인코딩된 문자열을 파싱하여 게임 데이터 추출
            # 실제 구현 시 인코딩 규칙에 맞게 수정
            return games
        except Exception as e:
            logger.error(f"히스토리 디코딩 오류: {e}")
            return []


class RealtimePacketProcessor:
    """실시간 패킷 처리기"""
    
    def __init__(self, decoder: EnhancedPacketDecoder = None):
        self.decoder = decoder or EnhancedPacketDecoder()
        self.processing_queue = Queue()
        self.is_running = False
        self.worker_thread = None
        self.callbacks = []
    
    def add_callback(self, callback):
        """처리 완료 콜백 등록"""
        self.callbacks.append(callback)
    
    def start(self):
        """실시간 처리 시작"""
        if self.is_running:
            return
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("실시간 패킷 처리기 시작됨")
    
    def stop(self):
        """실시간 처리 중지"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        logger.info("실시간 패킷 처리기 중지됨")
    
    def process_data(self, data: Union[str, Dict[str, Any]], source: str = "realtime"):
        """데이터를 처리 큐에 추가"""
        self.processing_queue.put({
            'data': data,
            'source': source,
            'timestamp': time.time()
        })
    
    def _worker_loop(self):
        """워커 스레드 루프"""
        while self.is_running:
            try:
                # 큐에서 데이터 가져오기
                item = self.processing_queue.get(timeout=1.0)
                
                # 데이터 처리
                games = self.decoder.parse_realtime_data(item['data'], item['source'])
                
                # 콜백 호출
                for callback in self.callbacks:
                    try:
                        callback(games, item)
                    except Exception as e:
                        logger.error(f"콜백 실행 오류: {e}")
                
                self.processing_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"워커 루프 오류: {e}")


# 사용 예제
def example_callback(games: List[BaccaratGameData], item: Dict[str, Any]):
    """예제 콜백 함수"""
    logger.info(f"처리 완료: {len(games)}개 게임 - 소스: {item['source']}")
    for game in games:
        logger.info(f"  게임 {game.game_id}: {game.winner} (P:{game.player_score}, B:{game.banker_score})")


if __name__ == "__main__":
    # 테스트 코드
    decoder = EnhancedPacketDecoder()
    processor = RealtimePacketProcessor(decoder)
    processor.add_callback(example_callback)
    processor.start()
    
    try:
        # 샘플 테스트
        logger.info("실시간 패킷 처리기 테스트 시작")
        time.sleep(5)  # 5초 대기
    finally:
        processor.stop()