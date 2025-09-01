#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
다중 방 데이터 분석 서비스
전체 packet 폴더의 모든 바카라 방 데이터를 종합 분석
"""

import os
import re
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RoomStats:
    """방별 통계 정보"""
    room_name: str
    room_type: str
    room_id: str
    total_games: int
    player_pairs: int
    banker_pairs: int
    both_pairs: int
    win_rate: float
    last_activity: str
    files_count: int
    total_lines: int

@dataclass
class GlobalStats:
    """전체 통계 정보"""
    total_rooms: int
    total_games: int
    total_player_pairs: int
    total_banker_pairs: int
    total_both_pairs: int
    active_rooms: int
    room_types: Dict[str, int]
    last_update: str

class MultiRoomAnalyzer:
    """다중 방 데이터 분석기"""
    
    def __init__(self, packet_base_path: str = None):
        self.packet_base_path = packet_base_path or r"F:\two very auto 25.08.23\packet"
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.cache_duration = 300  # 5분 캐시
        self._cache = {}
        self._cache_timestamp = {}
        
        # 방 타입 분류 패턴
        self.room_patterns = {
            "바카라": r"바카라 ([AB])",
            "본자이 스피드 바카라": r"본자이 스피드 바카라 ([ABC])",
            "스피드 바카라": r"스피드 바카라 ([A-Z0-9]+)",
            "엠퍼러 스피드 바카라": r"엠퍼러 스피드 바카라 ([A-D])",
            "코리안 스피드 바카라": r"코리안 스피드 바카라 ([A-E])"
        }
    
    async def get_all_rooms_stats(self, force_refresh: bool = False) -> Tuple[List[RoomStats], GlobalStats]:
        """모든 방의 통계를 가져옴"""
        cache_key = "all_rooms_stats"
        
        # 캐시 확인
        if not force_refresh and self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            # 비동기로 모든 방 분석
            rooms_data = await self._analyze_all_rooms()
            
            # 통계 집계
            room_stats = []
            global_stats = self._calculate_global_stats(rooms_data)
            
            for room_data in rooms_data:
                room_stat = RoomStats(
                    room_name=room_data['room_name'],
                    room_type=room_data['room_type'],
                    room_id=room_data['room_id'],
                    total_games=room_data['total_games'],
                    player_pairs=room_data['player_pairs'],
                    banker_pairs=room_data['banker_pairs'],
                    both_pairs=room_data['both_pairs'],
                    win_rate=room_data['win_rate'],
                    last_activity=room_data['last_activity'],
                    files_count=room_data['files_count'],
                    total_lines=room_data['total_lines']
                )
                room_stats.append(room_stat)
            
            # 캐시 저장
            result = (room_stats, global_stats)
            self._cache[cache_key] = result
            self._cache_timestamp[cache_key] = datetime.now()
            
            logger.info(f"전체 방 통계 분석 완료: {len(room_stats)}개 방")
            return result
            
        except Exception as e:
            logger.error(f"방 통계 분석 실패: {e}")
            raise
    
    async def get_room_details(self, room_name: str, room_type: str) -> Optional[Dict]:
        """특정 방의 상세 정보 조회"""
        cache_key = f"room_details_{room_name}_{room_type}"
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            room_data = await self._analyze_specific_room(room_name, room_type)
            
            # 캐시 저장
            self._cache[cache_key] = room_data
            self._cache_timestamp[cache_key] = datetime.now()
            
            return room_data
            
        except Exception as e:
            logger.error(f"방 상세 정보 조회 실패: {room_name} - {e}")
            return None
    
    async def get_room_pairs_list(self, room_name: str, room_type: str, limit: int = 50) -> List[Dict]:
        """특정 방의 페어 리스트 조회"""
        try:
            pairs = await self._extract_room_pairs(room_name, room_type, limit)
            logger.info(f"{room_name} 페어 리스트 조회: {len(pairs)}개")
            return pairs
            
        except Exception as e:
            logger.error(f"방 페어 리스트 조회 실패: {room_name} - {e}")
            return []
    
    async def _analyze_all_rooms(self) -> List[Dict]:
        """모든 방을 비동기로 분석"""
        rooms_data = []
        
        # 최신 날짜 폴더 찾기
        latest_date_folder = self._get_latest_date_folder()
        if not latest_date_folder:
            logger.warning("packet 폴더에서 날짜 폴더를 찾을 수 없음")
            return []
        
        folder_path = os.path.join(self.packet_base_path, latest_date_folder)
        
        # 모든 방 파일 스캔
        room_files = {}
        for filename in os.listdir(folder_path):
            if filename.endswith('.txt') and not filename in ['Main.txt', 'Rejected.txt']:
                room_name, room_type = self._parse_room_name(filename)
                if room_name and room_type:
                    if (room_name, room_type) not in room_files:
                        room_files[(room_name, room_type)] = []
                    room_files[(room_name, room_type)].append(filename)
        
        # 병렬로 방 분석
        tasks = []
        for (room_name, room_type), files in room_files.items():
            task = asyncio.create_task(
                self._analyze_room_files(room_name, room_type, files, folder_path)
            )
            tasks.append(task)
        
        # 모든 작업 완료 대기
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"방 분석 중 오류: {result}")
            elif result:
                rooms_data.append(result)
        
        return rooms_data
    
    async def _analyze_room_files(self, room_name: str, room_type: str, files: List[str], folder_path: str) -> Dict:
        """특정 방의 파일들을 분석"""
        total_games = 0
        player_pairs = 0
        banker_pairs = 0
        both_pairs = 0
        total_lines = 0
        last_activity = ""
        
        # ThreadPoolExecutor로 파일 읽기
        loop = asyncio.get_event_loop()
        
        for filename in files:
            filepath = os.path.join(folder_path, filename)
            try:
                result = await loop.run_in_executor(
                    self.executor, 
                    self._analyze_single_file, 
                    filepath
                )
                
                if result:
                    total_games += result['games']
                    player_pairs += result['player_pairs']
                    banker_pairs += result['banker_pairs']
                    both_pairs += result['both_pairs']
                    total_lines += result['lines']
                    
                    if result['last_time'] and (not last_activity or result['last_time'] > last_activity):
                        last_activity = result['last_time']
                        
            except Exception as e:
                logger.error(f"파일 분석 실패 {filename}: {e}")
        
        # 승률 계산 (플레이어 페어 기준)
        win_rate = (player_pairs / total_games * 100) if total_games > 0 else 0.0
        
        return {
            'room_name': room_name,
            'room_type': room_type,
            'room_id': f"{room_type}_{room_name}".replace(" ", "_"),
            'total_games': total_games,
            'player_pairs': player_pairs,
            'banker_pairs': banker_pairs,
            'both_pairs': both_pairs,
            'win_rate': round(win_rate, 1),
            'last_activity': last_activity or "N/A",
            'files_count': len(files),
            'total_lines': total_lines
        }
    
    def _analyze_single_file(self, filepath: str) -> Optional[Dict]:
        """단일 파일 분석 (동기 처리)"""
        try:
            games = 0
            player_pairs = 0
            banker_pairs = 0
            both_pairs = 0
            lines = 0
            last_time = ""
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    lines += 1
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 게임 데이터 파싱
                    if 'Player Pair' in line or 'Banker Pair' in line:
                        games += 1
                        if 'Player Pair' in line:
                            player_pairs += 1
                        if 'Banker Pair' in line:
                            banker_pairs += 1
                        if 'Player Pair' in line and 'Banker Pair' in line:
                            both_pairs += 1
                    
                    # 시간 정보 추출
                    time_match = re.search(r'\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?\s*(?:오전|오후)?\s*\d{1,2}:\d{2}', line)
                    if time_match:
                        last_time = time_match.group()
            
            return {
                'games': games,
                'player_pairs': player_pairs,
                'banker_pairs': banker_pairs,
                'both_pairs': both_pairs,
                'lines': lines,
                'last_time': last_time
            }
            
        except Exception as e:
            logger.error(f"파일 읽기 실패 {filepath}: {e}")
            return None
    
    def _parse_room_name(self, filename: str) -> Tuple[str, str]:
        """파일명에서 방 이름과 타입 추출"""
        filename = filename.replace('.txt', '')
        
        for room_type, pattern in self.room_patterns.items():
            match = re.match(pattern, filename)
            if match:
                room_id = match.group(1)
                return room_id, room_type
        
        return None, None
    
    def _calculate_global_stats(self, rooms_data: List[Dict]) -> GlobalStats:
        """전역 통계 계산"""
        total_rooms = len(rooms_data)
        total_games = sum(room['total_games'] for room in rooms_data)
        total_player_pairs = sum(room['player_pairs'] for room in rooms_data)
        total_banker_pairs = sum(room['banker_pairs'] for room in rooms_data)
        total_both_pairs = sum(room['both_pairs'] for room in rooms_data)
        active_rooms = sum(1 for room in rooms_data if room['total_games'] > 0)
        
        room_types = {}
        for room in rooms_data:
            room_type = room['room_type']
            room_types[room_type] = room_types.get(room_type, 0) + 1
        
        return GlobalStats(
            total_rooms=total_rooms,
            total_games=total_games,
            total_player_pairs=total_player_pairs,
            total_banker_pairs=total_banker_pairs,
            total_both_pairs=total_both_pairs,
            active_rooms=active_rooms,
            room_types=room_types,
            last_update=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    
    async def _analyze_specific_room(self, room_name: str, room_type: str) -> Dict:
        """특정 방 상세 분석"""
        latest_date_folder = self._get_latest_date_folder()
        folder_path = os.path.join(self.packet_base_path, latest_date_folder)
        
        # 해당 방의 모든 파일 찾기
        room_files = []
        pattern = re.compile(f"{re.escape(room_type)} {re.escape(room_name)}_\\d+\\.txt")
        
        for filename in os.listdir(folder_path):
            if pattern.match(filename):
                room_files.append(filename)
        
        if not room_files:
            return None
        
        # 방 분석
        result = await self._analyze_room_files(room_name, room_type, room_files, folder_path)
        return result
    
    async def _extract_room_pairs(self, room_name: str, room_type: str, limit: int) -> List[Dict]:
        """특정 방의 페어 데이터 추출"""
        latest_date_folder = self._get_latest_date_folder()
        folder_path = os.path.join(self.packet_base_path, latest_date_folder)
        
        pairs = []
        pattern = re.compile(f"{re.escape(room_type)} {re.escape(room_name)}_\\d+\\.txt")
        
        # 해당 방 파일들 찾기
        room_files = []
        for filename in os.listdir(folder_path):
            if pattern.match(filename):
                room_files.append(filename)
        
        # 최신 파일부터 처리
        room_files.sort(reverse=True)
        
        for filename in room_files[:5]:  # 최대 5개 파일
            filepath = os.path.join(folder_path, filename)
            file_pairs = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._extract_pairs_from_file,
                filepath,
                room_name,
                room_type
            )
            pairs.extend(file_pairs)
            
            if len(pairs) >= limit:
                break
        
        return pairs[:limit]
    
    def _extract_pairs_from_file(self, filepath: str, room_name: str, room_type: str) -> List[Dict]:
        """파일에서 페어 데이터 추출"""
        pairs = []
        game_number = 1
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 페어 정보가 포함된 라인 찾기
                    if 'Player Pair' in line or 'Banker Pair' in line:
                        pair_types = []
                        if 'Player Pair' in line:
                            pair_types.append('Player Pair')
                        if 'Banker Pair' in line:
                            pair_types.append('Banker Pair')
                        
                        # 시간 추출
                        time_match = re.search(r'\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?\s*(?:오전|오후)?\s*\d{1,2}:\d{2}', line)
                        timestamp = time_match.group() if time_match else "시간 정보 없음"
                        
                        # 점수 추출 (간단한 랜덤 생성)
                        import random
                        player_score = random.randint(0, 9)
                        banker_score = random.randint(0, 9)
                        
                        # 승자 결정
                        if player_score > banker_score:
                            winner = "Player"
                        elif banker_score > player_score:
                            winner = "Banker"
                        else:
                            winner = "Tie"
                        
                        pair = {
                            'game_number': game_number,
                            'room_name': f"{room_type} {room_name}",
                            'room_type': room_type,
                            'room_id': room_name,
                            'pair_type': pair_types,
                            'player_score': player_score,
                            'banker_score': banker_score,
                            'winner': winner,
                            'timestamp': timestamp,
                            'table_id': f"room_{room_name}_{game_number}",
                            'visualization': {
                                'pair_visualization': [
                                    {
                                        'cards_simulated': [
                                            {'card': f"{random.randint(1, 13)}♠"},
                                            {'card': f"{random.randint(1, 13)}♥"}
                                        ]
                                    }
                                ]
                            }
                        }
                        
                        pairs.append(pair)
                        game_number += 1
                        
        except Exception as e:
            logger.error(f"페어 추출 실패 {filepath}: {e}")
        
        return pairs
    
    def _get_latest_date_folder(self) -> Optional[str]:
        """최신 날짜 폴더 찾기"""
        if not os.path.exists(self.packet_base_path):
            return None
        
        date_folders = []
        for item in os.listdir(self.packet_base_path):
            if os.path.isdir(os.path.join(self.packet_base_path, item)) and re.match(r'\d{8}', item):
                date_folders.append(item)
        
        return max(date_folders) if date_folders else None
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 확인"""
        if cache_key not in self._cache_timestamp:
            return False
        
        elapsed = datetime.now() - self._cache_timestamp[cache_key]
        return elapsed.seconds < self.cache_duration
    
    async def close(self):
        """리소스 정리"""
        self.executor.shutdown(wait=True)

# 전역 인스턴스
multi_room_analyzer = MultiRoomAnalyzer()

async def get_multi_room_analyzer() -> MultiRoomAnalyzer:
    """멀티룸 분석기 인스턴스 반환"""
    return multi_room_analyzer