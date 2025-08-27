#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
대량 패킷 데이터 배치 처리 디코더
packet 폴더의 모든 데이터를 디코딩하여 정리
"""

import json
import asyncio
import aiofiles
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from dataclasses import dataclass
import re

# 기존 디코더 임포트
from packet_decoder import BaccaratPacketDecoder

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PacketFileInfo:
    """패킷 파일 정보"""
    file_path: Path
    table_name: str
    date: str
    hour: str
    file_size: int
    last_modified: float

@dataclass
class ProcessingResult:
    """처리 결과"""
    file_info: PacketFileInfo
    games_count: int
    pairs_count: int
    processing_time: float
    success: bool
    error: Optional[str] = None

class BatchPacketDecoder:
    """대량 패킷 데이터 배치 처리 디코더"""
    
    def __init__(self, packet_folder: str = "F:/two very auto 25.08.23/packet", 
                 db_path: str = "F:/two very auto 25.08.23/python/fastapi_app/baccarat_data.db"):
        """
        배치 디코더 초기화
        
        Args:
            packet_folder: 패킷 폴더 경로
            db_path: 데이터베이스 파일 경로
        """
        self.packet_folder = Path(packet_folder)
        self.db_path = Path(db_path)
        self.decoder = BaccaratPacketDecoder()
        
        # 처리 통계
        self.total_files = 0
        self.processed_files = 0
        self.total_games = 0
        self.total_pairs = 0
        self.failed_files = 0
        self.start_time = None
        
        logger.info(f"[Batch Decoder] 초기화 완료 - Packet: {self.packet_folder}, DB: {self.db_path}")
    
    async def discover_packet_files(self) -> List[PacketFileInfo]:
        """
        패킷 폴더에서 모든 파일을 검색하여 메타데이터 수집
        
        Returns:
            패킷 파일 정보 리스트
        """
        try:
            files_info = []
            
            if not self.packet_folder.exists():
                logger.error(f"패킷 폴더가 존재하지 않습니다: {self.packet_folder}")
                return []
            
            # 날짜별 폴더 순회
            for date_folder in self.packet_folder.iterdir():
                if not date_folder.is_dir() or not date_folder.name.isdigit():
                    continue
                
                date_str = date_folder.name
                logger.info(f"날짜 폴더 처리 중: {date_str}")
                
                # 해당 날짜의 모든 .txt 파일 처리
                txt_files = list(date_folder.glob("*.txt"))
                
                for file_path in txt_files:
                    # 파일명에서 테이블명과 시간 추출
                    table_name, hour = self._extract_table_info(file_path.name)
                    
                    if table_name and hour:
                        file_info = PacketFileInfo(
                            file_path=file_path,
                            table_name=table_name,
                            date=date_str,
                            hour=hour,
                            file_size=file_path.stat().st_size,
                            last_modified=file_path.stat().st_mtime
                        )
                        files_info.append(file_info)
                
                logger.info(f"날짜 {date_str}: {len(txt_files)}개 파일 발견")
            
            self.total_files = len(files_info)
            logger.info(f"총 {self.total_files}개 패킷 파일 발견")
            
            return files_info
            
        except Exception as e:
            logger.error(f"패킷 파일 검색 실패: {e}")
            return []
    
    def _extract_table_info(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        파일명에서 테이블명과 시간 정보 추출
        
        Args:
            filename: 파일명 (예: "스피드 바카라 A_08.txt")
            
        Returns:
            (테이블명, 시간) 튜플
        """
        try:
            # .txt 제거
            base_name = filename.replace('.txt', '')
            
            # 패턴 매칭: 테이블명_시간
            patterns = [
                r'(.+)_(\d{2})$',  # "스피드 바카라 A_08" 형태
                r'(.+)_(\d{2})\.txt$',  # 확장자 포함
            ]
            
            for pattern in patterns:
                match = re.match(pattern, filename.replace('.txt', ''))
                if match:
                    table_name = match.group(1).strip()
                    hour = match.group(2)
                    return table_name, hour
            
            # 매칭되지 않으면 None 반환
            return None, None
            
        except Exception as e:
            logger.warning(f"파일명 파싱 실패 {filename}: {e}")
            return None, None
    
    async def process_single_file(self, file_info: PacketFileInfo) -> ProcessingResult:
        """
        단일 파일 처리
        
        Args:
            file_info: 처리할 파일 정보
            
        Returns:
            처리 결과
        """
        start_time = datetime.now()
        
        try:
            # 파일이 너무 크면 스킵 (100MB 이상)
            if file_info.file_size > 100 * 1024 * 1024:
                logger.warning(f"파일 크기 초과로 스킵: {file_info.file_path} ({file_info.file_size / 1024 / 1024:.1f}MB)")
                return ProcessingResult(
                    file_info=file_info,
                    games_count=0,
                    pairs_count=0,
                    processing_time=0,
                    success=False,
                    error="파일 크기 초과"
                )
            
            # 파일 내용 읽기 (비동기)
            async with aiofiles.open(file_info.file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            if not content.strip():
                return ProcessingResult(
                    file_info=file_info,
                    games_count=0,
                    pairs_count=0,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    success=True,
                    error="빈 파일"
                )
            
            # 파일 형식 감지 및 처리
            games = await self._process_file_content(content, file_info)
            
            # 페어 개수 계산
            pairs_count = sum(1 for game in games if game.get('pair_info', {}).get('has_any_pair', False))
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ProcessingResult(
                file_info=file_info,
                games_count=len(games),
                pairs_count=pairs_count,
                processing_time=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"파일 처리 실패 {file_info.file_path}: {e}")
            
            return ProcessingResult(
                file_info=file_info,
                games_count=0,
                pairs_count=0,
                processing_time=processing_time,
                success=False,
                error=str(e)
            )
    
    async def _process_file_content(self, content: str, file_info: PacketFileInfo) -> List[Dict[str, Any]]:
        """
        파일 내용 처리 (JSON 또는 텍스트 형식)
        
        Args:
            content: 파일 내용
            file_info: 파일 정보
            
        Returns:
            게임 데이터 리스트
        """
        games = []
        
        try:
            # JSON 형식인지 확인
            lines = content.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # JSON 형식 시도
                if line.startswith('{') and line.endswith('}'):
                    try:
                        json_data = json.loads(line)
                        json_games = self.decoder.parse_json_packet(json_data)
                        
                        # 파일 정보로 보강
                        for game in json_games:
                            game['source_file'] = str(file_info.file_path)
                            game['source_date'] = file_info.date
                            game['source_hour'] = file_info.hour
                            # 테이블명이 없거나 generic한 경우 파일에서 추출한 것으로 대체
                            if not game.get('table_name') or game.get('table_name') == 'unknown':
                                game['table_name'] = file_info.table_name
                        
                        games.extend(json_games)
                        continue
                        
                    except json.JSONDecodeError:
                        pass
                
                # 일반 텍스트 형식 처리는 기존 decoder 사용
                # (현재는 JSON 위주로 처리)
            
            # JSON으로 처리되지 않았으면 전체를 텍스트로 처리
            if not games and content.strip():
                text_games = self.decoder._parse_packet_content(content)
                
                # 파일 정보로 보강
                for game in text_games:
                    game['source_file'] = str(file_info.file_path)
                    game['source_date'] = file_info.date
                    game['source_hour'] = file_info.hour
                    if not game.get('table_name'):
                        game['table_name'] = file_info.table_name
                
                games.extend(text_games)
            
            return games
            
        except Exception as e:
            logger.error(f"파일 내용 처리 실패: {e}")
            return []
    
    async def process_batch(self, files_info: List[PacketFileInfo], 
                          max_concurrent: int = 10, 
                          progress_callback=None) -> List[ProcessingResult]:
        """
        배치로 파일들을 병렬 처리
        
        Args:
            files_info: 처리할 파일 정보 리스트
            max_concurrent: 최대 동시 처리 개수
            progress_callback: 진행률 콜백 함수
            
        Returns:
            처리 결과 리스트
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def process_with_semaphore(file_info: PacketFileInfo):
            async with semaphore:
                result = await self.process_single_file(file_info)
                self.processed_files += 1
                
                if result.success:
                    self.total_games += result.games_count
                    self.total_pairs += result.pairs_count
                else:
                    self.failed_files += 1
                
                # 진행률 콜백 호출
                if progress_callback:
                    await progress_callback(self.processed_files, self.total_files, result)
                
                return result
        
        # 모든 파일을 병렬로 처리
        tasks = [process_with_semaphore(file_info) for file_info in files_info]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        clean_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"파일 처리 중 예외 발생 {files_info[i].file_path}: {result}")
                clean_results.append(ProcessingResult(
                    file_info=files_info[i],
                    games_count=0,
                    pairs_count=0,
                    processing_time=0,
                    success=False,
                    error=str(result)
                ))
            else:
                clean_results.append(result)
        
        return clean_results
    
    async def setup_database(self):
        """데이터베이스 테이블 설정"""
        try:
            # 데이터베이스 디렉토리 생성
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 게임 데이터 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS baccarat_games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    game_id INTEGER,
                    game_time TEXT,
                    timestamp REAL,
                    result TEXT,
                    player_cards TEXT,
                    banker_cards TEXT,
                    player_score INTEGER DEFAULT 0,
                    banker_score INTEGER DEFAULT 0,
                    is_natural BOOLEAN DEFAULT 0,
                    has_player_pair BOOLEAN DEFAULT 0,
                    has_banker_pair BOOLEAN DEFAULT 0,
                    has_any_pair BOOLEAN DEFAULT 0,
                    pair_type TEXT,
                    pair_cards TEXT,
                    source_file TEXT,
                    source_date TEXT,
                    source_hour TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(table_name, game_time, player_cards, banker_cards)
                )
            ''')
            
            # 인덱스 생성
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_table_time ON baccarat_games(table_name, game_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pairs ON baccarat_games(has_any_pair)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_date ON baccarat_games(source_date)')
            
            # 처리 로그 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    table_name TEXT,
                    source_date TEXT,
                    source_hour TEXT,
                    games_count INTEGER,
                    pairs_count INTEGER,
                    processing_time REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    processed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("데이터베이스 테이블 설정 완료")
            
        except Exception as e:
            logger.error(f"데이터베이스 설정 실패: {e}")
            raise
    
    async def save_to_database(self, results: List[ProcessingResult]):
        """
        처리 결과를 데이터베이스에 저장
        
        Args:
            results: 처리 결과 리스트
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            games_to_insert = []
            logs_to_insert = []
            
            for result in results:
                # 처리 로그 저장
                logs_to_insert.append((
                    str(result.file_info.file_path),
                    result.file_info.table_name,
                    result.file_info.date,
                    result.file_info.hour,
                    result.games_count,
                    result.pairs_count,
                    result.processing_time,
                    result.success,
                    result.error
                ))
                
                # 성공한 경우만 게임 데이터 저장
                if result.success and result.games_count > 0:
                    # 파일을 다시 읽어서 게임 데이터 추출 (메모리 효율성을 위해)
                    try:
                        async with aiofiles.open(result.file_info.file_path, 'r', encoding='utf-8') as f:
                            content = await f.read()
                        
                        games = await self._process_file_content(content, result.file_info)
                        
                        for game in games:
                            pair_info = game.get('pair_info', {})
                            games_to_insert.append((
                                game.get('table_name', result.file_info.table_name),
                                game.get('game_id'),
                                game.get('game_time'),
                                game.get('timestamp'),
                                game.get('result'),
                                json.dumps(game.get('player_cards', [])),
                                json.dumps(game.get('banker_cards', [])),
                                game.get('player_score', 0),
                                game.get('banker_score', 0),
                                game.get('is_natural', False),
                                pair_info.get('has_player_pair', False),
                                pair_info.get('has_banker_pair', False),
                                pair_info.get('has_any_pair', False),
                                pair_info.get('pair_type'),
                                json.dumps(pair_info.get('pair_cards', [])),
                                str(result.file_info.file_path),
                                result.file_info.date,
                                result.file_info.hour
                            ))
                    except Exception as e:
                        logger.error(f"게임 데이터 재추출 실패 {result.file_info.file_path}: {e}")
            
            # 배치 삽입
            if games_to_insert:
                cursor.executemany('''
                    INSERT OR IGNORE INTO baccarat_games (
                        table_name, game_id, game_time, timestamp, result,
                        player_cards, banker_cards, player_score, banker_score, is_natural,
                        has_player_pair, has_banker_pair, has_any_pair, pair_type, pair_cards,
                        source_file, source_date, source_hour
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', games_to_insert)
                
                logger.info(f"{len(games_to_insert)}개 게임 데이터 저장 완료")
            
            # 처리 로그 저장
            cursor.executemany('''
                INSERT OR REPLACE INTO processing_log (
                    file_path, table_name, source_date, source_hour,
                    games_count, pairs_count, processing_time, success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', logs_to_insert)
            
            conn.commit()
            conn.close()
            
            logger.info(f"{len(logs_to_insert)}개 처리 로그 저장 완료")
            
        except Exception as e:
            logger.error(f"데이터베이스 저장 실패: {e}")
            raise
    
    async def run_batch_processing(self, max_concurrent: int = 10, 
                                 filter_date: str = None, 
                                 filter_table: str = None):
        """
        전체 배치 처리 실행
        
        Args:
            max_concurrent: 최대 동시 처리 개수
            filter_date: 특정 날짜만 처리 (YYYYMMDD 형식)
            filter_table: 특정 테이블만 처리
        """
        self.start_time = datetime.now()
        
        try:
            logger.info("🚀 대량 패킷 데이터 배치 처리 시작")
            
            # 1. 데이터베이스 설정
            await self.setup_database()
            
            # 2. 파일 검색
            logger.info("📂 패킷 파일 검색 중...")
            files_info = await self.discover_packet_files()
            
            if not files_info:
                logger.warning("처리할 파일이 없습니다.")
                return
            
            # 3. 필터링
            if filter_date:
                files_info = [f for f in files_info if f.date == filter_date]
                logger.info(f"날짜 필터링: {len(files_info)}개 파일")
            
            if filter_table:
                files_info = [f for f in files_info if filter_table.lower() in f.table_name.lower()]
                logger.info(f"테이블 필터링: {len(files_info)}개 파일")
            
            self.total_files = len(files_info)
            
            # 4. 진행률 콜백 정의
            async def progress_callback(processed: int, total: int, result: ProcessingResult):
                progress = processed / total * 100 if total > 0 else 0
                
                if processed % 50 == 0 or processed == total:  # 50개마다 또는 완료시 출력
                    elapsed = (datetime.now() - self.start_time).total_seconds()
                    rate = processed / elapsed if elapsed > 0 else 0
                    
                    logger.info(f"진행률: {processed}/{total} ({progress:.1f}%) | "
                              f"처리율: {rate:.1f}파일/초 | "
                              f"게임: {self.total_games}개 | 페어: {self.total_pairs}개")
            
            # 5. 배치 처리 실행
            logger.info(f"⚡ {self.total_files}개 파일 병렬 처리 시작 (동시실행: {max_concurrent}개)")
            results = await self.process_batch(files_info, max_concurrent, progress_callback)
            
            # 6. 데이터베이스 저장
            logger.info("💾 데이터베이스 저장 중...")
            await self.save_to_database(results)
            
            # 7. 결과 요약
            self._print_summary()
            
        except Exception as e:
            logger.error(f"배치 처리 실패: {e}")
            raise
    
    def _print_summary(self):
        """처리 결과 요약 출력"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("📊 배치 처리 완료 요약")
        logger.info("=" * 60)
        logger.info(f"총 처리 시간: {elapsed:.1f}초")
        logger.info(f"처리된 파일: {self.processed_files}/{self.total_files}")
        logger.info(f"성공한 파일: {self.processed_files - self.failed_files}")
        logger.info(f"실패한 파일: {self.failed_files}")
        logger.info(f"추출된 게임: {self.total_games:,}개")
        logger.info(f"페어 발견: {self.total_pairs:,}개")
        
        if self.total_games > 0:
            pair_rate = self.total_pairs / self.total_games * 100
            logger.info(f"페어 발생률: {pair_rate:.2f}%")
        
        if elapsed > 0:
            logger.info(f"처리율: {self.processed_files / elapsed:.1f}파일/초")
            logger.info(f"게임 처리율: {self.total_games / elapsed:.1f}게임/초")
        
        logger.info("=" * 60)

async def main():
    """메인 실행 함수"""
    try:
        # 배치 디코더 생성
        decoder = BatchPacketDecoder()
        
        # 전체 배치 처리 실행
        await decoder.run_batch_processing(
            max_concurrent=15,  # 동시 처리 파일 수
            filter_date=None,    # 특정 날짜만 (None이면 전체)
            filter_table=None    # 특정 테이블만 (None이면 전체)
        )
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"실행 오류: {e}")

if __name__ == "__main__":
    # asyncio로 실행
    asyncio.run(main())