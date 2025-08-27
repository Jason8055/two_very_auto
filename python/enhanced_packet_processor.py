#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
대용량 패킷 실시간 처리 최적화 시스템
비동기 처리, 배치 처리, 메모리 최적화를 통한 고성능 패킷 처리
"""

import json
import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Deque
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from korean_encoding_fix import setup_korean_encoding, safe_print
from packet_decoder import BaccaratPacketDecoder
from pair_alert_channel import PairAlertChannel

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """처리 통계 정보"""
    packets_processed: int = 0
    pairs_detected: int = 0
    processing_time_ms: float = 0.0
    queue_size: int = 0
    error_count: int = 0
    throughput_per_sec: float = 0.0
    memory_usage_mb: float = 0.0


class EnhancedPacketProcessor:
    """대용량 패킷 실시간 처리 최적화 시스템"""
    
    def __init__(self, max_workers: int = 4, batch_size: int = 10, 
                 queue_size: int = 10000):
        """
        향상된 패킷 프로세서 초기화
        
        Args:
            max_workers: 최대 워커 스레드 수
            batch_size: 배치 처리 크기
            queue_size: 큐 최대 크기
        """
        self.max_workers = max_workers
        self.batch_size = batch_size
        
        # 처리 큐 (원형 버퍼 방식)
        self.packet_queue: Deque = deque(maxlen=queue_size)
        self.processing_queue = asyncio.Queue(maxsize=queue_size)
        
        # 구성 요소
        self.decoder = BaccaratPacketDecoder()
        self.alert_channel = PairAlertChannel(port=8767)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 처리 통계
        self.stats = ProcessingStats()
        self.performance_history = deque(maxlen=3600)  # 1시간 데이터
        
        # 콜백 함수들
        self.callbacks = {
            'on_packet_processed': [],
            'on_pair_detected': [],
            'on_error': [],
            'on_batch_complete': []
        }
        
        # 제어 플래그
        self.running = False
        self.processing_task = None
        
        # 메모리 관리
        self.memory_threshold_mb = 500  # 500MB 임계값
        self.cleanup_interval = 300  # 5분마다 정리
        
        logger.info(f"[Enhanced Processor] Initialized with {max_workers} workers, batch size {batch_size}")
    
    def register_callback(self, event: str, callback: Callable):
        """콜백 함수 등록"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
            logger.info(f"[Enhanced Processor] Registered callback for {event}")
    
    async def start_processing(self):
        """비동기 처리 시작"""
        try:
            self.running = True
            
            # 알림 채널 시작
            self.alert_channel.start_async_server()
            
            # 처리 태스크들 생성
            tasks = [
                asyncio.create_task(self._batch_processor()),
                asyncio.create_task(self._performance_monitor()),
                asyncio.create_task(self._memory_manager())
            ]
            
            # 모든 태스크 실행
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"[Enhanced Processor] Processing error: {e}")
        finally:
            self.running = False
    
    async def add_packet(self, packet_data: Dict[str, Any], priority: int = 0) -> bool:
        """
        패킷 추가 (우선순위 지원)
        
        Args:
            packet_data: 패킷 데이터
            priority: 우선순위 (높을수록 우선)
            
        Returns:
            추가 성공 여부
        """
        try:
            packet_item = {
                'data': packet_data,
                'priority': priority,
                'timestamp': time.time(),
                'attempts': 0
            }
            
            # 큐가 가득 찬 경우 우선순위 기반 교체
            if len(self.packet_queue) >= self.packet_queue.maxlen:
                # 낮은 우선순위 항목 찾아서 교체
                min_priority_idx = None
                min_priority = float('inf')
                
                for i, item in enumerate(self.packet_queue):
                    if item['priority'] < min_priority:
                        min_priority = item['priority']
                        min_priority_idx = i
                
                if min_priority_idx is not None and priority > min_priority:
                    # 기존 낮은 우선순위 항목 제거하고 새 항목 추가
                    del self.packet_queue[min_priority_idx]
                    self.packet_queue.append(packet_item)
                    return True
                else:
                    return False  # 추가 실패
            else:
                self.packet_queue.append(packet_item)
                return True
                
        except Exception as e:
            logger.error(f"[Enhanced Processor] Packet add error: {e}")
            return False
    
    async def _batch_processor(self):
        """배치 처리 메인 루프"""
        logger.info("[Enhanced Processor] Batch processor started")
        
        while self.running:
            try:
                # 배치 크기만큼 패킷 수집
                batch = []
                for _ in range(self.batch_size):
                    if self.packet_queue:
                        batch.append(self.packet_queue.popleft())
                    else:
                        break
                
                if batch:
                    # 우선순위 정렬
                    batch.sort(key=lambda x: x['priority'], reverse=True)
                    
                    # 배치 처리
                    await self._process_batch(batch)
                else:
                    # 큐가 비어있으면 짧게 대기
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"[Enhanced Processor] Batch processing error: {e}")
                self.stats.error_count += 1
    
    async def _process_batch(self, batch: List[Dict[str, Any]]):
        """배치 처리 실행"""
        start_time = time.time()
        
        try:
            # 병렬 처리를 위한 Future 생성
            futures = []
            
            for item in batch:
                future = self.executor.submit(
                    self._process_single_packet, 
                    item['data']
                )
                futures.append((future, item))
            
            # 결과 처리
            processed_count = 0
            pair_count = 0
            
            for future, item in futures:
                try:
                    result = future.result(timeout=1.0)  # 1초 타임아웃
                    
                    if result:
                        processed_count += 1
                        
                        # 페어 감지 확인
                        if self._has_pair(result):
                            pair_count += 1
                            # 알림 채널로 전송
                            await self.alert_channel.send_pair_alert(result)
                            
                            # 페어 콜백 실행
                            for callback in self.callbacks['on_pair_detected']:
                                try:
                                    callback(result)
                                except Exception as e:
                                    logger.warning(f"Pair callback error: {e}")
                        
                        # 처리 완료 콜백
                        for callback in self.callbacks['on_packet_processed']:
                            try:
                                callback(result)
                            except Exception as e:
                                logger.warning(f"Process callback error: {e}")
                    
                except Exception as e:
                    logger.warning(f"[Enhanced Processor] Single packet error: {e}")
                    self.stats.error_count += 1
                    
                    # 에러 콜백
                    for callback in self.callbacks['on_error']:
                        try:
                            callback(e, item)
                        except:
                            pass
            
            # 통계 업데이트
            processing_time = (time.time() - start_time) * 1000
            self.stats.packets_processed += processed_count
            self.stats.pairs_detected += pair_count
            self.stats.processing_time_ms = processing_time
            self.stats.queue_size = len(self.packet_queue)
            
            # 처리량 계산
            if processing_time > 0:
                self.stats.throughput_per_sec = (processed_count / processing_time) * 1000
            
            # 배치 완료 콜백
            for callback in self.callbacks['on_batch_complete']:
                try:
                    callback({
                        'processed': processed_count,
                        'pairs': pair_count,
                        'time_ms': processing_time
                    })
                except Exception as e:
                    logger.warning(f"Batch callback error: {e}")
            
        except Exception as e:
            logger.error(f"[Enhanced Processor] Batch processing failed: {e}")
            self.stats.error_count += 1
    
    def _process_single_packet(self, packet_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """단일 패킷 처리 (동기 함수 - 워커에서 실행)"""
        try:
            # JSON 패킷인지 확인
            if packet_data.get('type') == 'baccarat.encodedShoeState':
                games = self.decoder.parse_json_packet(packet_data)
                
                # 최신 게임만 반환 (메모리 절약)
                if games:
                    return games[-1]  # 가장 최근 게임
            
            return None
            
        except Exception as e:
            logger.warning(f"[Enhanced Processor] Packet processing error: {e}")
            return None
    
    def _has_pair(self, game_data: Dict[str, Any]) -> bool:
        """게임 데이터에 페어가 있는지 확인"""
        pair_info = game_data.get('pair_info', {})
        return pair_info.get('has_any_pair', False)
    
    async def _performance_monitor(self):
        """성능 모니터링"""
        logger.info("[Enhanced Processor] Performance monitor started")
        
        while self.running:
            try:
                # 메모리 사용량 측정
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.stats.memory_usage_mb = memory_mb
                
                # 성능 히스토리에 추가
                current_stats = {
                    'timestamp': datetime.now().isoformat(),
                    'packets_processed': self.stats.packets_processed,
                    'pairs_detected': self.stats.pairs_detected,
                    'throughput': self.stats.throughput_per_sec,
                    'queue_size': self.stats.queue_size,
                    'memory_mb': memory_mb,
                    'error_count': self.stats.error_count
                }
                
                self.performance_history.append(current_stats)
                
                # 30초마다 성능 로그
                if len(self.performance_history) % 30 == 0:
                    logger.info(f"[Performance] Processed: {self.stats.packets_processed}, "
                              f"Pairs: {self.stats.pairs_detected}, "
                              f"Queue: {self.stats.queue_size}, "
                              f"Memory: {memory_mb:.1f}MB")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"[Enhanced Processor] Performance monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _memory_manager(self):
        """메모리 관리"""
        logger.info("[Enhanced Processor] Memory manager started")
        
        while self.running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # 메모리 임계값 확인
                if self.stats.memory_usage_mb > self.memory_threshold_mb:
                    logger.warning(f"[Memory] High usage: {self.stats.memory_usage_mb:.1f}MB")
                    
                    # 정리 작업
                    self._cleanup_memory()
                
            except Exception as e:
                logger.error(f"[Enhanced Processor] Memory management error: {e}")
    
    def _cleanup_memory(self):
        """메모리 정리"""
        try:
            # 오래된 성능 히스토리 정리 (1시간 이전)
            current_time = time.time()
            cutoff_time = current_time - 3600  # 1시간
            
            cleaned_history = deque(maxlen=3600)
            for entry in self.performance_history:
                try:
                    entry_time = datetime.fromisoformat(entry['timestamp']).timestamp()
                    if entry_time > cutoff_time:
                        cleaned_history.append(entry)
                except:
                    continue
            
            old_size = len(self.performance_history)
            self.performance_history = cleaned_history
            
            # 큐 정리 (오래된 패킷 제거)
            current_queue = deque(maxlen=self.packet_queue.maxlen)
            for item in list(self.packet_queue):
                if current_time - item['timestamp'] < 60:  # 1분 이내 패킷만 유지
                    current_queue.append(item)
            
            old_queue_size = len(self.packet_queue)
            self.packet_queue = current_queue
            
            logger.info(f"[Memory] Cleanup complete - History: {old_size} -> {len(self.performance_history)}, "
                       f"Queue: {old_queue_size} -> {len(self.packet_queue)}")
            
        except Exception as e:
            logger.error(f"[Memory] Cleanup error: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        return {
            'current': {
                'packets_processed': self.stats.packets_processed,
                'pairs_detected': self.stats.pairs_detected,
                'processing_time_ms': self.stats.processing_time_ms,
                'throughput_per_sec': self.stats.throughput_per_sec,
                'queue_size': self.stats.queue_size,
                'memory_usage_mb': self.stats.memory_usage_mb,
                'error_count': self.stats.error_count,
                'running': self.running
            },
            'history_length': len(self.performance_history),
            'configuration': {
                'max_workers': self.max_workers,
                'batch_size': self.batch_size,
                'queue_maxsize': self.packet_queue.maxlen,
                'memory_threshold_mb': self.memory_threshold_mb
            }
        }
    
    def get_recent_performance_history(self, minutes: int = 10) -> List[Dict[str, Any]]:
        """최근 성능 히스토리 반환"""
        if not self.performance_history:
            return []
        
        cutoff_time = time.time() - (minutes * 60)
        recent_history = []
        
        for entry in self.performance_history:
            try:
                entry_time = datetime.fromisoformat(entry['timestamp']).timestamp()
                if entry_time > cutoff_time:
                    recent_history.append(entry)
            except:
                continue
        
        return recent_history
    
    async def stop_processing(self):
        """처리 중단"""
        logger.info("[Enhanced Processor] Stopping processing...")
        
        self.running = False
        
        # 스레드 풀 종료
        self.executor.shutdown(wait=True)
        
        logger.info("[Enhanced Processor] Processing stopped")


# 통합 테스트 함수
async def test_enhanced_processor():
    """향상된 패킷 프로세서 테스트"""
    safe_print("=== 향상된 패킷 프로세서 테스트 ===")
    
    processor = EnhancedPacketProcessor(max_workers=2, batch_size=5)
    
    # 콜백 등록
    def on_pair_detected(game_data):
        safe_print(f"[Test] Pair detected: {game_data.get('pair_info', {}).get('pair_type', 'Unknown')}")
    
    processor.register_callback('on_pair_detected', on_pair_detected)
    
    # 처리 시작
    processing_task = asyncio.create_task(processor.start_processing())
    
    # 테스트 데이터 추가
    test_packets = [
        {
            'type': 'baccarat.encodedShoeState',
            'args': {
                'history_v2': [
                    {
                        'winner': 'Player',
                        'playerScore': 4,
                        'bankerScore': 3,
                        'playerPair': True
                    }
                ],
                'tableId': 'test_table_1'
            },
            'time': int(time.time() * 1000)
        }
    ]
    
    for i, packet in enumerate(test_packets):
        success = await processor.add_packet(packet, priority=1)
        safe_print(f"[Test] Packet {i+1} added: {success}")
    
    # 잠시 처리 대기
    await asyncio.sleep(3)
    
    # 통계 확인
    stats = processor.get_performance_stats()
    safe_print(f"[Test] Performance stats: {stats}")
    
    # 정리
    await processor.stop_processing()


if __name__ == '__main__':
    try:
        asyncio.run(test_enhanced_processor())
    except KeyboardInterrupt:
        safe_print("[Test] Test interrupted by user")
    except Exception as e:
        safe_print(f"[Test] Test failed: {e}")