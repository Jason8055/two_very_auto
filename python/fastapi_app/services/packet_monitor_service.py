#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
패킷 폴더 실시간 모니터링 서비스
새로운 패킷 데이터가 생성되면 자동으로 디코딩하여 데이터베이스에 저장
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import aiofiles
import sqlite3
from concurrent.futures import ThreadPoolExecutor

# 패킷 디코더 임포트
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from packet_decoder import BaccaratPacketDecoder
from batch_packet_decoder import BatchPacketDecoder

logger = logging.getLogger(__name__)

class PacketFileHandler(FileSystemEventHandler):
    """패킷 파일 변경 이벤트 핸들러"""
    
    def __init__(self, monitor_service):
        self.monitor_service = monitor_service
        self.processed_files = set()
        
    def on_created(self, event):
        """새 파일 생성 시"""
        if not event.is_directory and event.src_path.endswith('.txt'):
            asyncio.create_task(self.monitor_service.process_new_file(event.src_path))
    
    def on_modified(self, event):
        """파일 수정 시"""
        if not event.is_directory and event.src_path.endswith('.txt'):
            # 같은 파일이 연속으로 수정되는 것을 방지
            if event.src_path not in self.processed_files:
                self.processed_files.add(event.src_path)
                asyncio.create_task(self.monitor_service.process_updated_file(event.src_path))
                
                # 5초 후 처리 완료로 표시 (같은 파일 재처리 허용)
                def remove_from_processed():
                    self.processed_files.discard(event.src_path)
                
                asyncio.get_event_loop().call_later(5.0, remove_from_processed)

class PacketMonitorService:
    """패킷 폴더 실시간 모니터링 서비스
packet 폴더의 JSON 문서를 실시간으로 감지하고 디코딩하여 데이터 처리
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import aiofiles

# 로컬 모듈 임포트
from ..models.game import GameData, PairType
from .optimized_database import OptimizedDatabase
from .async_ai_engine import AsyncAIEngine
from .notification_service import NotificationService

logger = logging.getLogger(__name__)


class PacketFileHandler(FileSystemEventHandler):
    """패킷 파일 변경 감지 핸들러"""
    
    def __init__(self, monitor_service):
        self.monitor_service = monitor_service
        super().__init__()
    
    def on_created(self, event):
        """새 파일 생성 시"""
        if not event.is_directory and event.src_path.endswith('.txt'):
            logger.info(f"새 패킷 파일 감지: {event.src_path}")
            asyncio.create_task(self.monitor_service.process_packet_file(event.src_path))
    
    def on_modified(self, event):
        """파일 수정 시"""
        if not event.is_directory and event.src_path.endswith('.txt'):
            logger.debug(f"패킷 파일 수정 감지: {event.src_path}")
            asyncio.create_task(self.monitor_service.process_packet_file(event.src_path))


class PacketMonitorService:
    """실시간 패킷 모니터링 및 처리 서비스"""
    
    def __init__(self, 
                 packet_folder: str = "F:/two very auto 25.08.23/packet",
                 db_service: Optional[OptimizedDatabase] = None,
                 ai_engine: Optional[AsyncAIEngine] = None,
                 notification_service: Optional[NotificationService] = None):
        """
        패킷 모니터링 서비스 초기화
        
        Args:
            packet_folder: 감시할 패킷 폴더 경로
            db_service: 데이터베이스 서비스
            ai_engine: AI 예측 엔진
            notification_service: 알림 서비스
        """
        self.packet_folder = Path(packet_folder)
        self.db_service = db_service
        self.ai_engine = ai_engine
        self.notification_service = notification_service
        
        # 파일 시스템 감시자 설정
        self.observer = Observer()
        self.file_handler = PacketFileHandler(self)
        
        # 처리 통계
        self.stats = {
            'files_processed': 0,
            'games_decoded': 0,
            'pairs_found': 0,
            'errors': 0,
            'last_processed': None
        }
        
        # 처리된 파일 추적 (중복 처리 방지)
        self.processed_files = set()
        
        logger.info(f"패킷 모니터링 서비스 초기화 완료: {self.packet_folder}")
    
    async def start_monitoring(self):
        """패킷 폴더 모니터링 시작"""
        try:
            # 기존 파일들 처음 로드
            await self._process_existing_files()
            
            # 실시간 감시 시작
            self.observer.schedule(
                self.file_handler,
                str(self.packet_folder),
                recursive=True
            )
            self.observer.start()
            
            logger.info(f"패킷 폴더 실시간 모니터링 시작: {self.packet_folder}")
            return True
            
        except Exception as e:
            logger.error(f"패킷 모니터링 시작 실패: {e}")
            return False
    
    async def stop_monitoring(self):
        """패킷 폴더 모니터링 중지"""
        try:
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join()
            logger.info("패킷 모니터링 중지 완료")
        except Exception as e:
            logger.error(f"패킷 모니터링 중지 실패: {e}")
    
    async def _process_existing_files(self):
        """기존 패킷 파일들 초기 처리"""
        try:
            # 최신 패킷 파일들 찾기
            packet_files = []
            
            # 날짜별 폴더 검색
            for date_folder in self.packet_folder.iterdir():
                if date_folder.is_dir() and date_folder.name.isdigit():
                    for file_path in date_folder.glob("*.txt"):
                        if "스피드" in file_path.name and "바카라" in file_path.name:
                            packet_files.append(file_path)
            
            # 최신 파일부터 처리 (최대 10개)
            packet_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            logger.info(f"기존 패킷 파일 {len(packet_files[:10])}개 처리 시작")
            
            for file_path in packet_files[:10]:
                await self.process_packet_file(str(file_path))
                
        except Exception as e:
            logger.error(f"기존 파일 처리 실패: {e}")
    
    async def process_packet_file(self, file_path: str):
        """개별 패킷 파일 처리"""
        try:
            file_key = f"{file_path}_{Path(file_path).stat().st_mtime}"
            if file_key in self.processed_files:
                return  # 이미 처리된 파일
            
            logger.info(f"패킷 파일 처리 시작: {file_path}")
            
            # 파일 내용 읽기
            content = await self._read_packet_file(file_path)
            if not content:
                return
            
            # JSON 데이터 추출 및 디코딩
            games_data = await self._decode_packet_content(content, file_path)
            
            if games_data:
                # 각 게임 데이터 처리
                for game_data in games_data:
                    await self._process_game_data(game_data)
                
                # 처리 통계 업데이트
                self.stats['files_processed'] += 1
                self.stats['games_decoded'] += len(games_data)
                self.stats['last_processed'] = datetime.now().isoformat()
                
                logger.info(f"패킷 파일 처리 완료: {len(games_data)}게임 디코딩")
            
            # 처리 완료 표시
            self.processed_files.add(file_key)
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"패킷 파일 처리 실패 {file_path}: {e}")
    
    async def _read_packet_file(self, file_path: str) -> Optional[str]:
        """패킷 파일 내용 읽기"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return content.strip()
        except Exception as e:
            logger.error(f"파일 읽기 실패 {file_path}: {e}")
            return None
    
    async def _decode_packet_content(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """패킷 내용에서 게임 데이터 디코딩"""
        try:
            games_data = []
            
            # JSON 라인별 처리
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    # JSON 데이터 파싱
                    json_data = json.loads(line)
                    
                    # 바카라 패킷인지 확인
                    if json_data.get('type') == 'baccarat.encodedShoeState':
                        decoded_games = await self._decode_baccarat_packet(json_data, file_path)
                        games_data.extend(decoded_games)
                        
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON 파싱 실패 {file_path}:{line_num}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"라인 처리 실패 {file_path}:{line_num}: {e}")
                    continue
            
            return games_data
            
        except Exception as e:
            logger.error(f"패킷 디코딩 실패 {file_path}: {e}")
            return []
    
    async def _decode_baccarat_packet(self, json_data: Dict[str, Any], file_path: str) -> List[Dict[str, Any]]:
        """바카라 패킷 데이터 디코딩"""
        try:
            games_data = []
            
            args = json_data.get('args', {})
            history_v2 = args.get('history_v2', [])
            table_id = args.get('tableId', 'unknown')
            timestamp = json_data.get('time', int(datetime.now().timestamp() * 1000))
            
            # 테이블명 추출 (스피드바카라A 형식)
            file_name = Path(file_path).stem
            if "스피드" in file_name and "바카라" in file_name:
                # 파일명에서 테이블명 추출
                if "_" in file_name:
                    table_name = file_name.split("_")[0]
                else:
                    table_name = "스피드바카라A"
            else:
                table_name = table_id
            
            # 각 게임 히스토리 처리
            for game_index, game in enumerate(history_v2):
                game_data = await self._parse_game_history(
                    game, table_name, timestamp, game_index
                )
                if game_data:
                    games_data.append(game_data)
            
            return games_data
            
        except Exception as e:
            logger.error(f"바카라 패킷 디코딩 실패: {e}")
            return []
    
    async def _parse_game_history(self, game: Dict[str, Any], table_name: str, 
                                base_timestamp: int, game_index: int) -> Optional[Dict[str, Any]]:
        """개별 게임 히스토리 파싱"""
        try:
            # 기본 게임 정보 추출
            winner = game.get('winner', 'Unknown')
            player_score = game.get('playerScore', 0)
            banker_score = game.get('bankerScore', 0)
            is_natural = game.get('natural', False)
            
            # 페어 정보 추출
            has_player_pair = game.get('playerPair', False)
            has_banker_pair = game.get('bankerPair', False)
            
            # 페어 타입 결정
            pair_type = PairType.NO_PAIR
            if has_player_pair and has_banker_pair:
                pair_type = PairType.BOTH_PAIR
            elif has_player_pair:
                pair_type = PairType.PLAYER_PAIR
            elif has_banker_pair:
                pair_type = PairType.BANKER_PAIR
            
            # 카드 정보 생성 (점수 기반)
            player_cards = self._generate_cards_from_score(player_score, is_natural, has_player_pair)
            banker_cards = self._generate_cards_from_score(banker_score, is_natural, has_banker_pair)
            
            # 페어 카드 추출
            pair_cards = []
            if has_player_pair:
                pair_cards.extend(player_cards[:2])
            if has_banker_pair:
                pair_cards.extend(banker_cards[:2])
            
            return {
                'table_name': table_name,
                'game_number': game_index + 1,
                'timestamp': datetime.fromtimestamp(base_timestamp / 1000).isoformat(),
                'result': winner,
                'player_cards': player_cards,
                'banker_cards': banker_cards,
                'player_score': player_score,
                'banker_score': banker_score,
                'has_pair': has_player_pair or has_banker_pair,
                'pair_type': pair_type,
                'pair_cards': pair_cards,
                'is_natural': is_natural
            }
            
        except Exception as e:
            logger.error(f"게임 히스토리 파싱 실패: {e}")
            return None
    
    def _generate_cards_from_score(self, score: int, is_natural: bool, has_pair: bool) -> List[str]:
        """점수 정보로부터 카드 조합 생성"""
        import random
        
        suits = ['♠', '♥', '♦', '♣']
        
        if has_pair:
            # 페어인 경우
            if score == 0:
                rank = random.choice(['10', 'J', 'Q', 'K'])
            elif score <= 9:
                rank = str(score)
            else:
                rank = 'A'
            
            suit1 = random.choice(suits)
            suit2 = random.choice([s for s in suits if s != suit1])
            return [f"{rank}{suit1}", f"{rank}{suit2}"]
        
        elif is_natural:
            # 내추럴 (8 또는 9)
            if score == 8:
                combinations = [('A', '7'), ('2', '6'), ('3', '5'), ('4', '4')]
            else:  # score == 9
                combinations = [('A', '8'), ('2', '7'), ('3', '6'), ('4', '5')]
            
            rank1, rank2 = random.choice(combinations)
            return [f"{rank1}{random.choice(suits)}", f"{rank2}{random.choice(suits)}"]
        
        else:
            # 일반적인 경우
            ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
            rank_values = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 0, 'J': 0, 'Q': 0, 'K': 0}
            
            # 2장으로 점수 만들기
            for _ in range(20):  # 최대 20번 시도
                rank1 = random.choice(ranks)
                rank2 = random.choice(ranks)
                total = (rank_values[rank1] + rank_values[rank2]) % 10
                if total == score:
                    return [f"{rank1}{random.choice(suits)}", f"{rank2}{random.choice(suits)}"]
            
            # 실패시 기본값
            return [f"A{random.choice(suits)}", f"{score-1 if score > 1 else 9}{random.choice(suits)}"]
    
    async def _process_game_data(self, game_data: Dict[str, Any]):
        """개별 게임 데이터 처리"""
        try:
            # 페어 감지 시 통계 업데이트
            if game_data.get('has_pair', False):
                self.stats['pairs_found'] += 1
                
                # 페어 알림 발송
                if self.notification_service:
                    await self.notification_service.send_notification({
                        'type': 'pair_detection',
                        'table_name': game_data['table_name'],
                        'pair_type': game_data['pair_type'],
                        'pair_cards': game_data['pair_cards'],
                        'game_time': game_data['timestamp'],
                        'priority': 'high'
                    })
            
            # 데이터베이스 저장
            if self.db_service:
                await self.db_service.save_game_data(game_data)
            
            # AI 예측 (백그라운드)
            if self.ai_engine and game_data.get('has_pair', False):
                asyncio.create_task(self._run_ai_analysis(game_data))
            
        except Exception as e:
            logger.error(f"게임 데이터 처리 실패: {e}")
    
    async def _run_ai_analysis(self, game_data: Dict[str, Any]):
        """AI 분석 실행 (비동기)"""
        try:
            # 최근 게임 데이터 조회
            if self.db_service:
                recent_games = await self.db_service.get_recent_games(
                    table_name=game_data['table_name'],
                    limit=20
                )
                
                # AI 예측 실행
                prediction = await self.ai_engine.predict_next_pair(
                    current_game=game_data,
                    recent_games=recent_games
                )
                
                logger.info(f"AI 페어 예측 완료: {prediction.get('predicted_pair_type')} "
                          f"(신뢰도: {prediction.get('confidence', 0):.2f})")
                
        except Exception as e:
            logger.error(f"AI 분석 실패: {e}")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """모니터링 통계 반환"""
        return {
            **self.stats,
            'monitoring_active': self.observer.is_alive() if hasattr(self, 'observer') else False,
            'processed_files_count': len(self.processed_files)
        }
    
    async def force_rescan(self):
        """강제 재스캔"""
        logger.info("패킷 폴더 강제 재스캔 시작")
        self.processed_files.clear()
        await self._process_existing_files()
        logger.info("패킷 폴더 강제 재스캔 완료")


# 전역 인스턴스
packet_monitor = None

def get_packet_monitor_service() -> PacketMonitorService:
    """전역 패킷 모니터링 서비스 인스턴스 반환"""
    global packet_monitor
    if packet_monitor is None:
        packet_monitor = PacketMonitorService()
    return packet_monitor