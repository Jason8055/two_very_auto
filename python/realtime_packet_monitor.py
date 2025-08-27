#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
실시간 패킷 모니터링 시스템
packet 폴더를 실시간으로 감시하여 새로운 파일 및 데이터를 자동 처리
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
import threading
from queue import Queue, Empty

from packet_decoder import BaccaratPacketDecoder

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PacketFileHandler(FileSystemEventHandler):
    """패킷 파일 변경 감지 핸들러"""
    
    def __init__(self, monitor_instance):
        """핸들러 초기화"""
        self.monitor = monitor_instance
        self.last_processed = {}  # 파일별 마지막 처리 시간 추적
        
    def on_created(self, event):
        """새 파일 생성 시 호출"""
        if not event.is_directory and event.src_path.endswith('.txt'):
            logger.info(f"새 패킷 파일 감지됨: {event.src_path}")
            self.monitor.add_file_to_queue(event.src_path, 'created')
    
    def on_modified(self, event):
        """파일 수정 시 호출"""
        if not event.is_directory and event.src_path.endswith('.txt'):
            # 너무 자주 트리거되는 것을 방지
            current_time = time.time()
            last_time = self.last_processed.get(event.src_path, 0)
            
            if current_time - last_time >= 1.0:  # 1초 간격 제한
                logger.info(f"패킷 파일 수정 감지됨: {event.src_path}")
                self.monitor.add_file_to_queue(event.src_path, 'modified')
                self.last_processed[event.src_path] = current_time


class RealTimePacketMonitor:
    """실시간 패킷 모니터링 클래스"""
    
    def __init__(self, packet_root_path: str = "packet"):
        """모니터 초기화"""
        self.packet_root = Path(packet_root_path)
        self.decoder = BaccaratPacketDecoder()
        self.observer = Observer()
        self.file_handler = PacketFileHandler(self)
        self.file_queue = Queue()
        self.callbacks = []  # 데이터 처리 콜백 함수들
        self.is_running = False
        self.worker_thread = None
        
        # 현재 활성 날짜 폴더들 추적
        self.active_date_folders = set()
        self._scan_existing_folders()
        
        logger.info(f"실시간 패킷 모니터 초기화 완료: {self.packet_root}")
    
    def _scan_existing_folders(self):
        """기존 날짜 폴더들을 스캔하여 모니터링 대상에 추가"""
        if not self.packet_root.exists():
            logger.warning(f"패킷 폴더가 존재하지 않습니다: {self.packet_root}")
            return
        
        for item in self.packet_root.iterdir():
            if item.is_dir() and self._is_date_folder(item.name):
                self.active_date_folders.add(item.name)
                logger.info(f"기존 날짜 폴더 발견: {item.name}")
    
    def _is_date_folder(self, folder_name: str) -> bool:
        """폴더명이 날짜 형식인지 확인 (예: 20250809)"""
        try:
            datetime.strptime(folder_name, "%Y%m%d")
            return True
        except ValueError:
            return False
    
    def add_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """데이터 처리 콜백 함수 등록"""
        self.callbacks.append(callback)
        logger.info(f"콜백 함수 등록됨: {callback.__name__}")
    
    def add_file_to_queue(self, file_path: str, event_type: str):
        """처리할 파일을 큐에 추가"""
        self.file_queue.put({
            'file_path': file_path,
            'event_type': event_type,
            'timestamp': datetime.now()
        })
    
    def _worker_thread_func(self):
        """워커 스레드에서 파일 처리"""
        logger.info("패킷 파일 처리 워커 스레드 시작됨")
        
        while self.is_running:
            try:
                # 큐에서 파일 정보 가져오기 (타임아웃 1초)
                file_info = self.file_queue.get(timeout=1.0)
                
                # 파일 처리
                self._process_file(file_info)
                
                # 큐 작업 완료 알림
                self.file_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"파일 처리 중 오류 발생: {e}", exc_info=True)
    
    def _process_file(self, file_info: Dict[str, Any]):
        """개별 파일 처리"""
        file_path = file_info['file_path']
        event_type = file_info['event_type']
        
        try:
            # 파일 경로에서 날짜 폴더 추출
            path_obj = Path(file_path)
            parent_folder = path_obj.parent.name
            
            # 새로운 날짜 폴더 감지
            if self._is_date_folder(parent_folder) and parent_folder not in self.active_date_folders:
                self.active_date_folders.add(parent_folder)
                logger.info(f"🔔 새로운 날짜 폴더 감지됨: {parent_folder}")
                
                # 새 날짜 폴더 콜백 호출
                for callback in self.callbacks:
                    try:
                        callback('new_date_folder', {
                            'folder_name': parent_folder,
                            'folder_path': str(path_obj.parent),
                            'timestamp': datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"날짜 폴더 콜백 오류: {e}")
            
            # 파일이 존재하고 읽을 수 있는지 확인
            if not os.path.exists(file_path):
                logger.warning(f"파일이 존재하지 않습니다: {file_path}")
                return
            
            # 파일이 완전히 쓰여졌는지 확인 (잠깐 대기)
            time.sleep(0.1)
            
            # 패킷 데이터 디코딩
            decoded_data = self.decoder.parse_packet_file(file_path)
            
            if not decoded_data:
                logger.warning(f"디코딩된 데이터가 없습니다: {file_path}")
                return
            
            # 처리된 데이터 정보
            processed_info = {
                'file_path': file_path,
                'file_name': path_obj.name,
                'date_folder': parent_folder,
                'event_type': event_type,
                'data_count': len(decoded_data),
                'decoded_data': decoded_data,
                'timestamp': datetime.now().isoformat(),
                'processing_time': time.time() - file_info['timestamp'].timestamp()
            }
            
            logger.info(f"📦 파일 처리 완료: {path_obj.name} ({len(decoded_data)}개 레코드)")
            
            # 모든 콜백 함수 호출
            for callback in self.callbacks:
                try:
                    callback('packet_data', processed_info)
                except Exception as e:
                    logger.error(f"패킷 데이터 콜백 오류: {e}")
        
        except Exception as e:
            logger.error(f"파일 처리 중 오류 발생 - {file_path}: {e}", exc_info=True)
    
    def start(self):
        """모니터링 시작"""
        if self.is_running:
            logger.warning("모니터링이 이미 실행 중입니다.")
            return
        
        try:
            # 패킷 폴더가 존재하는지 확인
            if not self.packet_root.exists():
                logger.error(f"패킷 폴더가 존재하지 않습니다: {self.packet_root}")
                return False
            
            # 워커 스레드 시작
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_thread_func, daemon=True)
            self.worker_thread.start()
            
            # 파일 시스템 감시 시작
            self.observer.schedule(self.file_handler, str(self.packet_root), recursive=True)
            self.observer.start()
            
            logger.info("🚀 실시간 패킷 모니터링 시작됨")
            logger.info(f"📁 감시 중인 폴더: {self.packet_root.absolute()}")
            logger.info(f"📊 활성 날짜 폴더: {len(self.active_date_folders)}개")
            
            return True
            
        except Exception as e:
            logger.error(f"모니터링 시작 중 오류 발생: {e}", exc_info=True)
            return False
    
    def stop(self):
        """모니터링 중지"""
        if not self.is_running:
            logger.warning("모니터링이 실행되지 않고 있습니다.")
            return
        
        try:
            # 실행 중지 플래그 설정
            self.is_running = False
            
            # 파일 시스템 감시 중지
            self.observer.stop()
            self.observer.join(timeout=5.0)
            
            # 워커 스레드 종료 대기
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=5.0)
            
            # 남은 큐 작업들 처리
            try:
                while not self.file_queue.empty():
                    self.file_queue.get_nowait()
                    self.file_queue.task_done()
            except Empty:
                pass
            
            logger.info("⏹️ 실시간 패킷 모니터링 중지됨")
            
        except Exception as e:
            logger.error(f"모니터링 중지 중 오류 발생: {e}", exc_info=True)
    
    def get_status(self) -> Dict[str, Any]:
        """현재 모니터링 상태 반환"""
        return {
            'is_running': self.is_running,
            'packet_root': str(self.packet_root.absolute()),
            'active_date_folders': list(self.active_date_folders),
            'queue_size': self.file_queue.qsize(),
            'callback_count': len(self.callbacks),
            'observer_running': self.observer.is_alive() if hasattr(self.observer, 'is_alive') else False
        }


# 샘플 콜백 함수들
def sample_data_callback(event_type: str, data: Dict[str, Any]):
    """샘플 데이터 처리 콜백"""
    if event_type == 'new_date_folder':
        logger.info(f"🔔 새 날짜 폴더 감지: {data['folder_name']}")
    elif event_type == 'packet_data':
        logger.info(f"📦 패킷 데이터 처리: {data['file_name']} - {data['data_count']}개 레코드")


# 비동기 래퍼 클래스
class AsyncPacketMonitor:
    """비동기 패킷 모니터 래퍼"""
    
    def __init__(self, packet_root_path: str = "packet"):
        self.monitor = RealTimePacketMonitor(packet_root_path)
        self.async_callbacks = []
    
    def add_async_callback(self, callback: Callable[[str, Dict[str, Any]], Any]):
        """비동기 콜백 함수 등록"""
        self.async_callbacks.append(callback)
        
        # 동기 래퍼 함수 생성 및 등록
        def sync_wrapper(event_type: str, data: Dict[str, Any]):
            # 새 이벤트 루프에서 비동기 함수 실행
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(callback(event_type, data))
                loop.close()
            except Exception as e:
                logger.error(f"비동기 콜백 실행 오류: {e}")
        
        self.monitor.add_callback(sync_wrapper)
    
    async def start_async(self):
        """비동기 방식으로 모니터링 시작"""
        return self.monitor.start()
    
    async def stop_async(self):
        """비동기 방식으로 모니터링 중지"""
        self.monitor.stop()
    
    def get_status(self):
        """현재 상태 반환"""
        return self.monitor.get_status()


# 사용 예제 및 테스트 함수
def test_monitor():
    """모니터 테스트 함수"""
    monitor = RealTimePacketMonitor()
    
    # 샘플 콜백 등록
    monitor.add_callback(sample_data_callback)
    
    try:
        # 모니터링 시작
        if monitor.start():
            logger.info("모니터링이 성공적으로 시작되었습니다.")
            logger.info("테스트를 위해 packet 폴더에 파일을 추가하거나 수정해보세요.")
            
            # 10초간 실행
            time.sleep(10)
            
        else:
            logger.error("모니터링 시작에 실패했습니다.")
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    finally:
        monitor.stop()


if __name__ == "__main__":
    # 테스트 실행
    test_monitor()