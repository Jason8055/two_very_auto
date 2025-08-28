#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
과거 패킷 데이터 일괄 처리 서비스
패킷 폴더의 모든 과거 파일들을 순차적으로 처리하여 데이터베이스에 저장
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
import aiofiles
from concurrent.futures import ThreadPoolExecutor

# 로컬 모듈 임포트
import sys
import os
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.database import DatabaseManager
from services.optimized_database import OptimizedDatabaseManager

logger = logging.getLogger(__name__)

class HistoricalDataProcessor:
    """과거 패킷 데이터 일괄 처리기"""
    
    def __init__(self, packet_folder: str = None):
        self.packet_folder = Path(packet_folder) if packet_folder else Path(__file__).parent.parent.parent / "packet"
        self.db_manager = DatabaseManager()
        self.optimized_db_manager = OptimizedDatabaseManager()
        
        # 처리 통계
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "total_games": 0,
            "errors": 0,
            "start_time": None,
            "current_date": None
        }
        
        # 스레드 풀 (파일 I/O 병렬 처리)
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def initialize(self):
        """초기화"""
        logger.info("🚀 과거 데이터 처리기 초기화 시작")
        await self.db_manager.initialize()
        await self.optimized_db_manager.initialize()
        logger.info("✅ 데이터베이스 초기화 완료")
    
    async def process_all_historical_data(self, start_date: str = None, end_date: str = None):
        """모든 과거 데이터 처리"""
        try:
            self.stats["start_time"] = datetime.now()
            logger.info("🔄 과거 패킷 데이터 일괄 처리 시작")
            
            if not self.packet_folder.exists():
                logger.error(f"❌ 패킷 폴더를 찾을 수 없습니다: {self.packet_folder}")
                return
            
            # 날짜 폴더 목록 가져오기
            date_folders = self._get_date_folders(start_date, end_date)
            
            if not date_folders:
                logger.warning("⚠️ 처리할 날짜 폴더가 없습니다")
                return
            
            logger.info(f"📁 총 {len(date_folders)}개 날짜 폴더 발견: {[f.name for f in date_folders]}")
            
            # 각 날짜 폴더 처리
            for date_folder in date_folders:
                self.stats["current_date"] = date_folder.name
                await self.process_date_folder(date_folder)
                
                # 잠시 대기 (시스템 부하 완화)
                await asyncio.sleep(0.1)
            
            # 최종 통계 출력
            await self._print_final_stats()
            
        except Exception as e:
            logger.error(f"❌ 과거 데이터 처리 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _get_date_folders(self, start_date: str = None, end_date: str = None) -> List[Path]:
        """날짜 폴더 목록 가져오기 (필터링 포함)"""
        date_folders = []
        
        for folder in self.packet_folder.iterdir():
            if not folder.is_dir():
                continue
                
            # 날짜 형식 확인 (YYYYMMDD)
            if not re.match(r'^\d{8}$', folder.name):
                continue
            
            # 날짜 필터링
            if start_date and folder.name < start_date:
                continue
            if end_date and folder.name > end_date:
                continue
                
            date_folders.append(folder)
        
        # 날짜 순으로 정렬
        return sorted(date_folders, key=lambda x: x.name)
    
    async def process_date_folder(self, date_folder: Path):
        """특정 날짜 폴더 처리"""
        try:
            logger.info(f"📅 {date_folder.name} 폴더 처리 시작")
            
            # 패킷 파일들 찾기
            packet_files = self._find_packet_files(date_folder)
            
            if not packet_files:
                logger.warning(f"⚠️ {date_folder.name}에서 처리할 패킷 파일이 없습니다")
                return
            
            self.stats["total_files"] += len(packet_files)
            logger.info(f"📄 {len(packet_files)}개 패킷 파일 발견")
            
            # 파일별 처리
            processed_count = 0
            for packet_file in packet_files:
                try:
                    await self.process_packet_file(packet_file, date_folder.name)
                    processed_count += 1
                    self.stats["processed_files"] += 1
                    
                    # 진행 상황 출력 (100개마다)
                    if processed_count % 100 == 0:
                        logger.info(f"  ✅ {processed_count}/{len(packet_files)} 파일 처리 완료")
                        
                except Exception as e:
                    logger.error(f"❌ 파일 처리 오류 {packet_file.name}: {e}")
                    self.stats["errors"] += 1
                    
                # 시스템 부하 완화
                if processed_count % 50 == 0:
                    await asyncio.sleep(0.05)
            
            logger.info(f"✅ {date_folder.name} 폴더 처리 완료 ({processed_count}개 파일)")
            
        except Exception as e:
            logger.error(f"❌ 날짜 폴더 처리 오류 {date_folder.name}: {e}")
            self.stats["errors"] += 1
    
    def _find_packet_files(self, date_folder: Path) -> List[Path]:
        """패킷 파일 찾기"""
        packet_files = []
        
        # 바카라 관련 텍스트 파일들 찾기
        patterns = [
            "*바카라*.txt",
            "*스피드*.txt",
            "*본자이*.txt",
            "*엠퍼러*.txt",
            "*코리안*.txt"
        ]
        
        for pattern in patterns:
            packet_files.extend(date_folder.glob(pattern))
        
        # 중복 제거 및 정렬
        packet_files = sorted(list(set(packet_files)), key=lambda x: x.name)
        
        return packet_files
    
    async def process_packet_file(self, packet_file: Path, date_str: str):
        """개별 패킷 파일 처리"""
        try:
            # 파일 읽기 (비동기)
            content = await self._read_packet_file(packet_file)
            
            if not content:
                return
            
            # 게임 데이터 추출
            games_data = await self._extract_games_from_content(content, packet_file, date_str)
            
            if games_data:
                # 데이터베이스에 저장
                await self._save_games_to_database(games_data)
                self.stats["total_games"] += len(games_data)
            
        except Exception as e:
            logger.error(f"❌ 패킷 파일 처리 오류 {packet_file}: {e}")
            raise
    
    async def _read_packet_file(self, packet_file: Path) -> str:
        """패킷 파일 읽기 (비동기)"""
        try:
            async with aiofiles.open(packet_file, 'r', encoding='utf-8') as f:
                content = await f.read()
            return content.strip()
        except Exception as e:
            logger.error(f"❌ 파일 읽기 오류 {packet_file}: {e}")
            return ""
    
    async def _extract_games_from_content(self, content: str, packet_file: Path, date_str: str) -> List[Dict[str, Any]]:
        """패킷 내용에서 게임 데이터 추출"""
        games_data = []
        
        try:
            # JSON 라인별 처리
            lines = content.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # JSON 데이터 찾기
                if '"type":"baccarat.encodedShoeState"' in line and '"history_v2":' in line:
                    try:
                        # JSON 부분만 추출
                        json_start = line.find('{')
                        if json_start >= 0:
                            json_data = json.loads(line[json_start:])
                            
                            # 게임 데이터 변환
                            parsed_games = await self._parse_baccarat_data(json_data, packet_file.name, date_str)
                            games_data.extend(parsed_games)
                    
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON 파싱 오류 (무시): {e}")
                        continue
                    except Exception as e:
                        logger.error(f"게임 데이터 파싱 오류: {e}")
                        continue
            
        except Exception as e:
            logger.error(f"❌ 게임 데이터 추출 오류: {e}")
        
        return games_data
    
    async def _parse_baccarat_data(self, json_data: Dict, file_name: str, date_str: str) -> List[Dict[str, Any]]:
        """바카라 JSON 데이터를 게임 데이터로 변환"""
        games_data = []
        
        try:
            args = json_data.get('args', {})
            history_v2 = args.get('history_v2', [])
            table_id = args.get('tableId', 'unknown')
            timestamp = json_data.get('time', 0)
            
            # 테이블명 추출
            table_name = self._extract_table_name(file_name)
            
            # 각 게임 처리
            for game_index, game in enumerate(history_v2):
                try:
                    game_data = {
                        'table_id': table_id,
                        'table_name': table_name,
                        'game_number': game_index + 1,
                        'winner': game.get('winner', 'Unknown'),
                        'player_score': game.get('playerScore', 0),
                        'banker_score': game.get('bankerScore', 0),
                        'player_pair': game.get('playerPair', False),
                        'banker_pair': game.get('bankerPair', False),
                        'natural': game.get('natural', False),
                        'timestamp': self._calculate_game_timestamp(timestamp, game_index, date_str),
                        'date': date_str,
                        'source_file': file_name
                    }
                    
                    games_data.append(game_data)
                    
                except Exception as e:
                    logger.error(f"개별 게임 파싱 오류: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"바카라 데이터 파싱 오류: {e}")
        
        return games_data
    
    def _extract_table_name(self, file_name: str) -> str:
        """파일명에서 테이블명 추출"""
        # 확장자 제거
        name = file_name.replace('.txt', '')
        
        # 시간 부분 제거 (예: _08)
        name = re.sub(r'_\d{2}$', '', name)
        
        return name
    
    def _calculate_game_timestamp(self, base_timestamp: int, game_index: int, date_str: str) -> str:
        """게임 타임스탬프 계산"""
        try:
            if base_timestamp > 0:
                # 각 게임은 약 30초~1분 간격으로 추정
                game_offset = game_index * 45  # 45초 간격
                game_time = datetime.fromtimestamp(base_timestamp / 1000) - timedelta(seconds=game_offset)
            else:
                # 타임스탬프가 없으면 날짜 기준으로 추정
                base_date = datetime.strptime(date_str, '%Y%m%d')
                game_time = base_date + timedelta(minutes=game_index)
            
            return game_time.strftime('%Y-%m-%d %H:%M:%S')
            
        except Exception as e:
            logger.error(f"타임스탬프 계산 오류: {e}")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    async def _save_games_to_database(self, games_data: List[Dict[str, Any]]):
        """게임 데이터를 데이터베이스에 저장"""
        try:
            # 배치로 저장 (성능 향상)
            await self.optimized_db_manager.bulk_insert_games(games_data)
            
            # 일반 DB에도 저장 (호환성)
            for game_data in games_data:
                await self.db_manager.add_game(
                    table_id=game_data['table_id'],
                    winner=game_data['winner'],
                    player_score=game_data['player_score'],
                    banker_score=game_data['banker_score'],
                    player_pair=game_data['player_pair'],
                    banker_pair=game_data['banker_pair'],
                    timestamp=game_data['timestamp']
                )
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 저장 오류: {e}")
            raise
    
    async def _print_final_stats(self):
        """최종 통계 출력"""
        end_time = datetime.now()
        elapsed = end_time - self.stats["start_time"]
        
        logger.info("=" * 60)
        logger.info("📊 과거 데이터 처리 완료")
        logger.info("=" * 60)
        logger.info(f"⏱️ 처리 시간: {elapsed}")
        logger.info(f"📁 총 파일 수: {self.stats['total_files']}")
        logger.info(f"✅ 처리된 파일: {self.stats['processed_files']}")
        logger.info(f"🎮 추출된 게임: {self.stats['total_games']}")
        logger.info(f"❌ 오류 수: {self.stats['errors']}")
        
        if self.stats['processed_files'] > 0:
            success_rate = (self.stats['processed_files'] - self.stats['errors']) / self.stats['processed_files'] * 100
            logger.info(f"✨ 성공률: {success_rate:.1f}%")
            
            if self.stats['total_games'] > 0:
                games_per_file = self.stats['total_games'] / self.stats['processed_files']
                logger.info(f"📈 파일당 평균 게임 수: {games_per_file:.1f}")
        
        logger.info("=" * 60)
    
    async def close(self):
        """리소스 정리"""
        try:
            await self.db_manager.close()
            await self.optimized_db_manager.close()
            self.executor.shutdown(wait=True)
            logger.info("✅ 과거 데이터 처리기 정리 완료")
        except Exception as e:
            logger.error(f"❌ 정리 오류: {e}")

# 독립 실행 함수
async def process_historical_data_main():
    """메인 실행 함수"""
    processor = HistoricalDataProcessor()
    
    try:
        await processor.initialize()
        await processor.process_all_historical_data()
    
    except Exception as e:
        logger.error(f"❌ 메인 실행 오류: {e}")
    
    finally:
        await processor.close()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 과거 패킷 데이터 처리 시작")
    asyncio.run(process_historical_data_main())