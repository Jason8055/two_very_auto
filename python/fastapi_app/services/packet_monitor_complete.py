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
    """패킷 폴더 실시간 모니터링 서비스"""
    
    def __init__(self, packet_folder: str = "F:/two very auto 25.08.23/packet",
                 db_path: str = "F:/two very auto 25.08.23/python/fastapi_app/baccarat_data.db"):
        """
        패킷 모니터 서비스 초기화
        
        Args:
            packet_folder: 모니터링할 패킷 폴더
            db_path: 데이터베이스 경로
        """
        self.packet_folder = Path(packet_folder)
        self.db_path = Path(db_path)
        self.decoder = BaccaratPacketDecoder()
        self.batch_decoder = BatchPacketDecoder(str(packet_folder), str(db_path))
        
        # 모니터링 상태
        self.is_monitoring = False
        self.observer = None
        self.file_handler = None
        
        # 통계
        self.stats = {
            'files_processed': 0,
            'games_added': 0,
            'pairs_found': 0,
            'last_update': None,
            'errors': 0,
            'start_time': None
        }
        
        # 스레드 풀 (CPU 집약적 작업용)
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        logger.info(f"[Packet Monitor] 초기화 완료 - 폴더: {self.packet_folder}")
    
    async def start_monitoring(self):
        """실시간 모니터링 시작"""
        try:
            if self.is_monitoring:
                logger.info("패킷 모니터링이 이미 실행 중입니다")
                return
            
            # 데이터베이스 설정 확인
            await self.batch_decoder.setup_database()
            
            # 패킷 폴더 생성 (존재하지 않으면)
            self.packet_folder.mkdir(parents=True, exist_ok=True)
            
            # 파일 시스템 이벤트 핸들러 설정
            self.file_handler = PacketFileHandler(self)
            
            # 워치독 옵저버 설정
            self.observer = Observer()
            self.observer.schedule(self.file_handler, str(self.packet_folder), recursive=True)
            
            # 모니터링 시작
            self.observer.start()
            self.is_monitoring = True
            self.stats['start_time'] = datetime.now().isoformat()
            
            logger.info(f"✅ 패킷 폴더 실시간 모니터링 시작: {self.packet_folder}")
            
            # 기존 파일들에 대한 초기 처리 (선택사항)
            await self._process_existing_files()
            
        except Exception as e:
            logger.error(f"패킷 모니터링 시작 실패: {e}")
            raise
    
    async def stop_monitoring(self):
        """모니터링 중단"""
        try:
            if not self.is_monitoring:
                return
            
            if self.observer:
                self.observer.stop()
                self.observer.join()
            
            self.is_monitoring = False
            logger.info("📦 패킷 모니터링 중단됨")
            
        except Exception as e:
            logger.error(f"패킷 모니터링 중단 실패: {e}")
    
    async def process_new_file(self, file_path: str):
        """새로 생성된 파일 처리"""
        try:
            logger.info(f"🆕 새 패킷 파일 감지: {file_path}")
            
            # 파일이 완전히 쓰여질 때까지 잠시 대기
            await asyncio.sleep(1)
            
            await self._process_packet_file(file_path)
            
        except Exception as e:
            logger.error(f"새 파일 처리 실패 {file_path}: {e}")
            self.stats['errors'] += 1
    
    async def process_updated_file(self, file_path: str):
        """수정된 파일 처리"""
        try:
            logger.info(f"📝 패킷 파일 업데이트 감지: {file_path}")
            
            # 수정된 파일의 새로운 내용 처리
            await asyncio.sleep(0.5)  # 파일 쓰기 완료 대기
            await self._process_packet_file(file_path, is_update=True)
            
        except Exception as e:
            logger.error(f"수정된 파일 처리 실패 {file_path}: {e}")
            self.stats['errors'] += 1
    
    async def _process_packet_file(self, file_path: str, is_update: bool = False):
        """패킷 파일 처리 (디코딩 및 데이터베이스 저장)"""
        try:
            file_path = Path(file_path)
            
            # 파일 존재 확인
            if not file_path.exists():
                logger.warning(f"파일이 존재하지 않음: {file_path}")
                return
            
            # 파일 크기 확인 (너무 작으면 아직 쓰는 중일 수 있음)
            if file_path.stat().st_size < 10:
                logger.debug(f"파일 크기가 너무 작음, 대기: {file_path}")
                await asyncio.sleep(2)
                if file_path.stat().st_size < 10:
                    return
            
            # 파일 정보 추출
            table_name, hour = self.batch_decoder._extract_table_info(file_path.name)
            if not table_name or not hour:
                logger.warning(f"테이블명/시간 추출 실패: {file_path.name}")
                return
            
            # 날짜 추출 (부모 폴더명)
            date_str = file_path.parent.name
            
            # 패킷 파일 정보 생성
            from batch_packet_decoder import PacketFileInfo
            file_info = PacketFileInfo(
                file_path=file_path,
                table_name=table_name,
                date=date_str,
                hour=hour,
                file_size=file_path.stat().st_size,
                last_modified=file_path.stat().st_mtime
            )
            
            # 파일 처리
            result = await self.batch_decoder.process_single_file(file_info)
            
            if result.success:
                # 데이터베이스에 저장
                await self.batch_decoder.save_to_database([result])
                
                # 통계 업데이트
                self.stats['files_processed'] += 1
                self.stats['games_added'] += result.games_count
                self.stats['pairs_found'] += result.pairs_count
                self.stats['last_update'] = datetime.now().isoformat()
                
                logger.info(f"✅ 패킷 파일 처리 완료: {file_path.name} "
                          f"(게임: {result.games_count}, 페어: {result.pairs_count})")
                
                # 실시간 알림 (WebSocket을 통해 클라이언트에 전송)
                await self._broadcast_new_data(result, is_update)
                
            else:
                logger.error(f"❌ 패킷 파일 처리 실패: {file_path.name} - {result.error}")
                self.stats['errors'] += 1
            
        except Exception as e:
            logger.error(f"패킷 파일 처리 중 오류 {file_path}: {e}")
            self.stats['errors'] += 1
    
    async def _broadcast_new_data(self, result, is_update: bool = False):
        """새로운 데이터를 WebSocket 클라이언트들에게 브로드캐스트"""
        try:
            # WebSocket 매니저가 있으면 브로드캐스트
            try:
                from ..routes.websocket_routes import broadcast_new_pair, broadcast_stats_update
                
                if result.pairs_count > 0:
                    # 새로운 페어 발생 알림
                    pair_data = {
                        'table_name': result.file_info.table_name,
                        'date': result.file_info.date,
                        'hour': result.file_info.hour,
                        'pairs_count': result.pairs_count,
                        'games_count': result.games_count,
                        'is_update': is_update
                    }
                    await broadcast_new_pair(pair_data)
                
                # 통계 업데이트 알림
                stats_data = self.get_monitoring_stats()
                await broadcast_stats_update(stats_data)
                
            except ImportError:
                # WebSocket 모듈이 없으면 패스
                pass
                
        except Exception as e:
            logger.error(f"브로드캐스트 실패: {e}")
    
    async def _process_existing_files(self):
        """시작 시 기존 파일들의 최신 데이터 확인"""
        try:
            logger.info("🔍 기존 패킷 파일들의 최신 데이터 확인 중...")
            
            # 최근 2일치 폴더만 확인 (너무 많으면 시작이 늦어짐)
            now = datetime.now()
            recent_dates = [
                (now - timedelta(days=i)).strftime("%Y%m%d") 
                for i in range(2)
            ]
            
            processed_count = 0
            for date_str in recent_dates:
                date_folder = self.packet_folder / date_str
                if date_folder.exists():
                    txt_files = list(date_folder.glob("*.txt"))
                    
                    # 최근 수정된 파일들만 처리 (1시간 내)
                    recent_files = []
                    one_hour_ago = datetime.now().timestamp() - 3600
                    
                    for file_path in txt_files:
                        if file_path.stat().st_mtime > one_hour_ago:
                            recent_files.append(file_path)
                    
                    if recent_files:
                        logger.info(f"날짜 {date_str}: {len(recent_files)}개 최신 파일 처리 중...")
                        
                        # 병렬로 처리 (너무 많지 않게 제한)
                        tasks = []
                        for file_path in recent_files[:20]:  # 최대 20개만
                            task = self._process_packet_file(str(file_path))
                            tasks.append(task)
                        
                        await asyncio.gather(*tasks, return_exceptions=True)
                        processed_count += len(recent_files)
            
            if processed_count > 0:
                logger.info(f"✅ 기존 파일 처리 완료: {processed_count}개")
            else:
                logger.info("📝 처리할 최신 파일이 없습니다")
                
        except Exception as e:
            logger.error(f"기존 파일 처리 중 오류: {e}")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """모니터링 통계 반환"""
        stats = self.stats.copy()
        stats['is_monitoring'] = self.is_monitoring
        stats['monitored_folder'] = str(self.packet_folder)
        
        # 실행 시간 계산
        if stats['start_time']:
            start_time = datetime.fromisoformat(stats['start_time'])
            uptime = (datetime.now() - start_time).total_seconds()
            stats['uptime_seconds'] = uptime
            stats['uptime_formatted'] = str(timedelta(seconds=int(uptime)))
        
        return stats
    
    async def get_recent_activity(self, hours: int = 1) -> Dict[str, Any]:
        """최근 활동 내역 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 최근 N시간 내 처리된 파일들
            since_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT COUNT(*) as file_count,
                       SUM(games_count) as total_games,
                       SUM(pairs_count) as total_pairs,
                       COUNT(CASE WHEN success = 1 THEN 1 END) as success_count,
                       COUNT(CASE WHEN success = 0 THEN 1 END) as error_count
                FROM processing_log 
                WHERE processed_at >= ?
            ''', (since_time.isoformat(),))
            
            result = cursor.fetchone()
            
            # 테이블별 활동
            cursor.execute('''
                SELECT table_name, 
                       COUNT(*) as file_count,
                       SUM(games_count) as games,
                       SUM(pairs_count) as pairs
                FROM processing_log 
                WHERE processed_at >= ? AND success = 1
                GROUP BY table_name
                ORDER BY pairs DESC
                LIMIT 10
            ''', (since_time.isoformat(),))
            
            table_activity = cursor.fetchall()
            
            conn.close()
            
            return {
                'period_hours': hours,
                'summary': {
                    'files_processed': result[0] or 0,
                    'games_added': result[1] or 0,
                    'pairs_found': result[2] or 0,
                    'success_count': result[3] or 0,
                    'error_count': result[4] or 0
                },
                'table_activity': [
                    {
                        'table_name': row[0],
                        'file_count': row[1],
                        'games': row[2],
                        'pairs': row[3]
                    }
                    for row in table_activity
                ]
            }
            
        except Exception as e:
            logger.error(f"최근 활동 조회 실패: {e}")
            return {
                'error': str(e),
                'period_hours': hours
            }
    
    async def cleanup_old_logs(self, days: int = 30):
        """오래된 처리 로그 정리"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                DELETE FROM processing_log 
                WHERE processed_at < ?
            ''', (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"🧹 {deleted_count}개 오래된 처리 로그 정리 완료")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"로그 정리 실패: {e}")
            return 0

# 전역 서비스 인스턴스
_packet_monitor_service = None

def get_packet_monitor_service() -> PacketMonitorService:
    """패킷 모니터 서비스 인스턴스 반환 (싱글톤)"""
    global _packet_monitor_service
    if _packet_monitor_service is None:
        _packet_monitor_service = PacketMonitorService()
    return _packet_monitor_service

async def start_packet_monitoring():
    """패킷 모니터링 서비스 시작"""
    service = get_packet_monitor_service()
    await service.start_monitoring()

async def stop_packet_monitoring():
    """패킷 모니터링 서비스 중단"""
    service = get_packet_monitor_service()
    await service.stop_monitoring()

if __name__ == "__main__":
    # 테스트 실행
    async def main():
        service = PacketMonitorService()
        try:
            await service.start_monitoring()
            
            # 10초간 모니터링 테스트
            logger.info("10초간 모니터링 테스트...")
            await asyncio.sleep(10)
            
        except KeyboardInterrupt:
            logger.info("사용자 중단")
        finally:
            await service.stop_monitoring()
    
    asyncio.run(main())