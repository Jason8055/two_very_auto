#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main 실행 파일 통합 서비스
two very auto.exe와 Python 백엔드 시스템 연동
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import threading
import time
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import socket
import psutil

from realtime_packet_monitor import RealTimePacketMonitor, AsyncPacketMonitor
from enhanced_packet_decoder import EnhancedPacketDecoder, BaccaratGameData
import uvicorn

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ProcessManager:
    """프로세스 관리자"""
    
    def __init__(self):
        self.processes = {}
        self.is_running = False
        
    def start_process(self, name: str, cmd: List[str], cwd: str = None) -> bool:
        """프로세스 시작"""
        try:
            if name in self.processes:
                logger.warning(f"프로세스가 이미 실행 중: {name}")
                return False
                
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.processes[name] = {
                'process': process,
                'cmd': cmd,
                'start_time': datetime.now(),
                'status': 'running'
            }
            
            logger.info(f"✅ 프로세스 시작됨: {name} (PID: {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"프로세스 시작 실패 {name}: {e}")
            return False
    
    def stop_process(self, name: str) -> bool:
        """프로세스 중지"""
        try:
            if name not in self.processes:
                logger.warning(f"프로세스를 찾을 수 없음: {name}")
                return False
                
            process_info = self.processes[name]
            process = process_info['process']
            
            if process.poll() is None:  # 프로세스가 실행 중
                process.terminate()
                
                # 5초간 대기 후 강제 종료
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    
            process_info['status'] = 'stopped'
            logger.info(f"⏹️ 프로세스 중지됨: {name}")
            return True
            
        except Exception as e:
            logger.error(f"프로세스 중지 실패 {name}: {e}")
            return False
    
    def get_process_status(self, name: str) -> Dict[str, Any]:
        """프로세스 상태 반환"""
        if name not in self.processes:
            return {'status': 'not_found'}
            
        process_info = self.processes[name]
        process = process_info['process']
        
        try:
            # 프로세스가 살아있는지 확인
            if process.poll() is None:
                # CPU 및 메모리 사용량 가져오기 (가능한 경우)
                try:
                    p = psutil.Process(process.pid)
                    cpu_percent = p.cpu_percent()
                    memory_info = p.memory_info()
                    
                    return {
                        'status': 'running',
                        'pid': process.pid,
                        'start_time': process_info['start_time'].isoformat(),
                        'cpu_percent': cpu_percent,
                        'memory_mb': memory_info.rss / 1024 / 1024,
                        'cmd': process_info['cmd']
                    }
                except psutil.NoSuchProcess:
                    process_info['status'] = 'stopped'
                    
            return {
                'status': process_info['status'],
                'start_time': process_info['start_time'].isoformat(),
                'cmd': process_info['cmd']
            }
            
        except Exception as e:
            logger.error(f"프로세스 상태 확인 실패 {name}: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def stop_all(self):
        """모든 프로세스 중지"""
        for name in list(self.processes.keys()):
            self.stop_process(name)


class MainIntegrationService:
    """Main 통합 서비스 - 모든 시스템 통합 관리"""
    
    def __init__(self, main_exe_path: str = "two very auto.exe"):
        """서비스 초기화"""
        self.main_exe_path = Path(main_exe_path).absolute()
        self.process_manager = ProcessManager()
        self.packet_monitor = RealTimePacketMonitor()
        self.packet_decoder = EnhancedPacketDecoder()
        self.is_running = False
        
        # 설정
        self.config = {
            'fastapi_host': '0.0.0.0',
            'fastapi_port': 8001,
            'websocket_port': 8765,
            'auto_start_main_exe': True,
            'auto_start_fastapi': True,
            'packet_monitor_enabled': True,
            'ai_integration_enabled': True
        }
        
        # 콜백 및 이벤트 핸들러
        self.event_callbacks = {}
        self.stats = {
            'start_time': None,
            'total_games_processed': 0,
            'main_exe_restarts': 0,
            'fastapi_restarts': 0
        }
        
        logger.info("Main 통합 서비스 초기화 완료")
    
    def add_event_callback(self, event_type: str, callback: Callable):
        """이벤트 콜백 등록"""
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
    
    def _fire_event(self, event_type: str, data: Dict[str, Any]):
        """이벤트 발생"""
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"이벤트 콜백 실행 오류 {event_type}: {e}")
    
    def _packet_data_handler(self, event_type: str, data: Dict[str, Any]):
        """패킷 데이터 처리 핸들러"""
        try:
            if event_type == 'packet_data':
                # 통계 업데이트
                self.stats['total_games_processed'] += data.get('data_count', 0)
                
                # 이벤트 발생
                self._fire_event('packet_processed', {
                    'file_name': data.get('file_name'),
                    'data_count': data.get('data_count'),
                    'processing_time': data.get('processing_time'),
                    'timestamp': data.get('timestamp')
                })
                
                logger.info(f"📊 패킷 처리됨: {data.get('file_name')} - {data.get('data_count')}개 게임")
                
            elif event_type == 'new_date_folder':
                self._fire_event('new_date_detected', data)
                logger.info(f"📅 새 날짜 폴더: {data.get('folder_name')}")
        
        except Exception as e:
            logger.error(f"패킷 데이터 핸들러 오류: {e}")
    
    async def start_service(self) -> bool:
        """통합 서비스 시작"""
        if self.is_running:
            logger.warning("서비스가 이미 실행 중입니다")
            return False
        
        try:
            logger.info("🚀 Two Very Auto 통합 서비스 시작")
            self.is_running = True
            self.stats['start_time'] = datetime.now()
            
            # 1. 패킷 모니터링 시작
            if self.config['packet_monitor_enabled']:
                self.packet_monitor.add_callback(self._packet_data_handler)
                if self.packet_monitor.start():
                    logger.info("✅ 패킷 모니터링 시작됨")
                else:
                    logger.error("❌ 패킷 모니터링 시작 실패")
                    return False
            
            # 2. FastAPI 서버 시작 (백그라운드)
            if self.config['auto_start_fastapi']:
                await self._start_fastapi_background()
            
            # 3. Main 실행 파일 시작
            if self.config['auto_start_main_exe']:
                self._start_main_exe()
            
            # 4. 상태 모니터링 시작
            self._start_health_monitor()
            
            logger.info("🎉 통합 서비스 시작 완료")
            self._fire_event('service_started', {'timestamp': datetime.now().isoformat()})
            
            return True
            
        except Exception as e:
            logger.error(f"서비스 시작 중 오류: {e}", exc_info=True)
            await self.stop_service()
            return False
    
    async def _start_fastapi_background(self):
        """FastAPI 서버 백그라운드 시작"""
        def run_fastapi():
            try:
                # 현재 디렉토리를 fastapi_app으로 변경
                import os
                original_cwd = os.getcwd()
                fastapi_dir = Path(__file__).parent / 'fastapi_app'
                os.chdir(fastapi_dir)
                
                # sys.path 추가
                sys.path.insert(0, str(fastapi_dir))
                
                try:
                    from main import app as fastapi_app
                    uvicorn.run(
                        fastapi_app,
                        host=self.config['fastapi_host'],
                        port=self.config['fastapi_port'],
                        log_level="warning"
                    )
                finally:
                    # 원래 디렉토리로 복원
                    os.chdir(original_cwd)
                    
            except Exception as e:
                logger.error(f"FastAPI 서버 실행 오류: {e}")
        
        # 별도 스레드에서 FastAPI 실행
        fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
        fastapi_thread.start()
        
        # 서버가 시작될 때까지 잠시 대기
        await asyncio.sleep(2)
        
        # 서버 상태 확인
        if await self._check_fastapi_health():
            logger.info(f"✅ FastAPI 서버 시작됨: http://{self.config['fastapi_host']}:{self.config['fastapi_port']}")
        else:
            logger.warning("⚠️ FastAPI 서버 상태 확인 실패")
    
    async def _check_fastapi_health(self) -> bool:
        """FastAPI 서버 상태 확인"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{self.config['fastapi_host']}:{self.config['fastapi_port']}/docs", timeout=5) as response:
                    return response.status == 200
        except Exception:
            return False
    
    def _start_main_exe(self) -> bool:
        """Main 실행 파일 시작"""
        try:
            if not self.main_exe_path.exists():
                logger.error(f"Main 실행 파일을 찾을 수 없음: {self.main_exe_path}")
                return False
            
            # 실행 파일의 작업 디렉토리 설정
            work_dir = self.main_exe_path.parent
            
            success = self.process_manager.start_process(
                "main_exe",
                [str(self.main_exe_path)],
                cwd=str(work_dir)
            )
            
            if success:
                logger.info(f"✅ Main 실행 파일 시작됨: {self.main_exe_path.name}")
                self._fire_event('main_exe_started', {
                    'exe_path': str(self.main_exe_path),
                    'timestamp': datetime.now().isoformat()
                })
            
            return success
            
        except Exception as e:
            logger.error(f"Main 실행 파일 시작 실패: {e}")
            return False
    
    def _start_health_monitor(self):
        """상태 모니터링 스레드 시작"""
        def health_monitor_loop():
            while self.is_running:
                try:
                    # Main 실행 파일 상태 확인
                    main_status = self.process_manager.get_process_status("main_exe")
                    
                    if main_status.get('status') == 'not_found' and self.config['auto_start_main_exe']:
                        logger.warning("Main 실행 파일이 중지됨. 재시작 시도...")
                        self._start_main_exe()
                        self.stats['main_exe_restarts'] += 1
                    
                    # 30초마다 체크
                    time.sleep(30)
                    
                except Exception as e:
                    logger.error(f"상태 모니터링 오류: {e}")
                    time.sleep(10)
        
        health_thread = threading.Thread(target=health_monitor_loop, daemon=True)
        health_thread.start()
        logger.info("✅ 상태 모니터링 시작됨")
    
    async def stop_service(self):
        """통합 서비스 중지"""
        if not self.is_running:
            logger.warning("서비스가 실행되지 않고 있습니다")
            return
        
        try:
            logger.info("⏹️ 통합 서비스 중지 시작")
            self.is_running = False
            
            # 1. 패킷 모니터링 중지
            if hasattr(self.packet_monitor, 'is_running') and self.packet_monitor.is_running:
                self.packet_monitor.stop()
                logger.info("✅ 패킷 모니터링 중지됨")
            
            # 2. 모든 프로세스 중지
            self.process_manager.stop_all()
            logger.info("✅ 모든 프로세스 중지됨")
            
            # 3. 이벤트 발생
            self._fire_event('service_stopped', {
                'timestamp': datetime.now().isoformat(),
                'total_runtime': (datetime.now() - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
            })
            
            logger.info("🎉 통합 서비스 중지 완료")
            
        except Exception as e:
            logger.error(f"서비스 중지 중 오류: {e}", exc_info=True)
    
    def get_service_status(self) -> Dict[str, Any]:
        """서비스 전체 상태 반환"""
        try:
            return {
                'service': {
                    'is_running': self.is_running,
                    'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                    'uptime_seconds': (datetime.now() - self.stats['start_time']).total_seconds() if self.stats['start_time'] else 0
                },
                'processes': {
                    'main_exe': self.process_manager.get_process_status('main_exe')
                },
                'packet_monitor': self.packet_monitor.get_status() if hasattr(self.packet_monitor, 'get_status') else {},
                'statistics': self.stats,
                'config': self.config
            }
        except Exception as e:
            logger.error(f"상태 조회 오류: {e}")
            return {'error': str(e)}
    
    def update_config(self, new_config: Dict[str, Any]):
        """설정 업데이트"""
        self.config.update(new_config)
        logger.info(f"설정 업데이트됨: {new_config}")
        self._fire_event('config_updated', {'config': self.config})


# 글로벌 서비스 인스턴스
_integration_service = None


def get_integration_service() -> MainIntegrationService:
    """통합 서비스 인스턴스 반환 (싱글톤)"""
    global _integration_service
    if _integration_service is None:
        _integration_service = MainIntegrationService()
    return _integration_service


# 시그널 핸들러 설정 (Graceful Shutdown)
def signal_handler(signum, frame):
    """시그널 핸들러 - 우아한 종료"""
    logger.info(f"시그널 수신: {signum}. 서비스를 안전하게 종료합니다...")
    service = get_integration_service()
    if service.is_running:
        asyncio.create_task(service.stop_service())
    sys.exit(0)


# 메인 실행 부분
async def main():
    """메인 실행 함수"""
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 통합 서비스 시작
    service = get_integration_service()
    
    # 이벤트 콜백 등록 (예제)
    def log_event(event_data):
        logger.info(f"이벤트 발생: {event_data}")
    
    service.add_event_callback('service_started', log_event)
    service.add_event_callback('packet_processed', log_event)
    service.add_event_callback('main_exe_started', log_event)
    
    try:
        # 서비스 시작
        success = await service.start_service()
        
        if not success:
            logger.error("서비스 시작 실패")
            return
        
        # 서비스 실행 유지
        while service.is_running:
            await asyncio.sleep(1)
            
            # 주기적으로 상태 출력 (60초마다)
            if int(time.time()) % 60 == 0:
                status = service.get_service_status()
                logger.info(f"📊 서비스 상태: 업타임 {status['service']['uptime_seconds']:.1f}초, "
                           f"처리된 게임 {status['statistics']['total_games_processed']}개")
    
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"메인 루프 오류: {e}", exc_info=True)
    finally:
        await service.stop_service()


if __name__ == "__main__":
    # 현재 디렉토리를 프로젝트 루트로 변경
    os.chdir(Path(__file__).parent.parent)
    
    # 비동기 실행
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("프로그램이 중단되었습니다.")