#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
통합 시스템 관리자
모든 개선된 시스템을 한 번에 관리하는 메인 컨트롤러
"""

import asyncio
import threading
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from packet_archive_manager import PacketArchiveManager
from system_monitor_dashboard import SystemMonitor, start_websocket_server
from automated_maintenance import AutomatedMaintenance


class SystemManager:
    """통합 시스템 관리자"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 구성요소 초기화
        self.packet_manager = PacketArchiveManager()
        self.system_monitor = SystemMonitor()
        self.maintenance_system = AutomatedMaintenance()
        
        # 실행 상태
        self.running = False
        self.threads = []
        
        # 신호 처리기 설정
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """신호 처리기"""
        self.logger.info(f"종료 신호 수신 ({signum})")
        self.stop_all_systems()
    
    def start_packet_archiving(self):
        """패킷 아카이빙 시스템 시작"""
        self.logger.info("패킷 아카이빙 시스템 시작")
        
        def archiving_worker():
            self.packet_manager.start_auto_archiving(interval_hours=24)
        
        thread = threading.Thread(target=archiving_worker, daemon=True)
        thread.start()
        self.threads.append(('packet_archiving', thread))
    
    def start_system_monitoring(self):
        """시스템 모니터링 시작"""
        self.logger.info("시스템 모니터링 시작")
        
        def monitoring_worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 모니터링 시작
            self.system_monitor.start_monitoring(interval_seconds=30)
            
            # WebSocket 서버 시작
            async def websocket_server():
                import websockets
                server = await websockets.serve(
                    self.system_monitor.websocket_handler, "localhost", 8765
                )
                self.logger.info("시스템 모니터링 WebSocket 서버 시작: ws://localhost:8765")
                await server.wait_closed()
            
            loop.run_until_complete(websocket_server())
        
        thread = threading.Thread(target=monitoring_worker, daemon=True)
        thread.start()
        self.threads.append(('system_monitoring', thread))
    
    def start_maintenance_scheduler(self):
        """유지보수 스케줄러 시작"""
        self.logger.info("자동 유지보수 스케줄러 시작")
        
        def maintenance_worker():
            self.maintenance_system.start_scheduler()
        
        thread = threading.Thread(target=maintenance_worker, daemon=True)
        thread.start()
        self.threads.append(('maintenance_scheduler', thread))
    
    def get_system_status(self) -> Dict:
        """전체 시스템 상태 반환"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'running': self.running,
            'components': {}
        }
        
        try:
            # 시스템 모니터 상태
            status['components']['system_monitor'] = self.system_monitor.get_current_status()
            
            # 패킷 매니저 상태
            archivable_dirs = self.packet_manager.get_archivable_directories()
            status['components']['packet_manager'] = {
                'archivable_directories': len(archivable_dirs),
                'total_archives': len(self.packet_manager.metadata)
            }
            
            # 유지보수 시스템 상태
            status['components']['maintenance'] = self.maintenance_system.get_maintenance_report()
            
            # 활성 스레드
            active_threads = [(name, thread.is_alive()) for name, thread in self.threads]
            status['active_threads'] = active_threads
            
        except Exception as e:
            status['error'] = str(e)
            self.logger.error(f"상태 수집 실패: {e}")
        
        return status
    
    def run_initial_optimization(self):
        """초기 시스템 최적화 실행"""
        self.logger.info("초기 시스템 최적화 시작")
        
        try:
            # 1. 패킷 데이터 아카이빙 (dry-run으로 확인)
            archivable = self.packet_manager.get_archivable_directories()
            if archivable:
                self.logger.info(f"아카이빙 가능한 디렉토리: {len(archivable)}개")
                results = self.packet_manager.archive_old_data(dry_run=True)
                estimated_savings = results['total_original_size'] // 1024 // 1024
                self.logger.info(f"예상 절약 공간: {estimated_savings}MB")
                
                # 실제 아카이빙 실행 (사용자 확인 없이)
                if estimated_savings > 100:  # 100MB 이상만
                    self.logger.info("대용량 데이터 아카이빙 실행")
                    actual_results = self.packet_manager.archive_old_data()
                    self.logger.info(f"실제 절약 공간: {actual_results['space_saved']//1024//1024}MB")
            
            # 2. 초기 건강 상태 점검
            health = self.maintenance_system.health_check()
            self.logger.info(f"시스템 건강 상태: {health['status']}")
            
            if health['warnings']:
                for warning in health['warnings']:
                    self.logger.warning(warning)
            
            # 3. 임시 파일 정리
            cleanup_results = self.maintenance_system.cleanup_temp_files()
            if cleanup_results['files_cleaned'] > 0:
                self.logger.info(
                    f"임시 파일 정리: {cleanup_results['files_cleaned']}개, "
                    f"{cleanup_results['space_freed_mb']}MB"
                )
        
        except Exception as e:
            self.logger.error(f"초기 최적화 실패: {e}")
    
    def start_all_systems(self):
        """모든 시스템 시작"""
        if self.running:
            self.logger.warning("시스템이 이미 실행 중입니다")
            return
        
        self.logger.info("=== Two Very Auto 통합 시스템 시작 ===")
        self.running = True
        
        # 초기 최적화
        self.run_initial_optimization()
        
        # 개별 시스템 시작
        self.start_packet_archiving()
        self.start_system_monitoring()
        self.start_maintenance_scheduler()
        
        self.logger.info("모든 시스템이 성공적으로 시작되었습니다")
        self.logger.info("시스템 상태 확인: http://localhost:8765")
        
        # 상태 출력
        status = self.get_system_status()
        self.logger.info(f"활성 구성요소: {len([t for n, t in self.threads if t.is_alive()])}개")
    
    def stop_all_systems(self):
        """모든 시스템 중지"""
        if not self.running:
            return
        
        self.logger.info("시스템 종료 중...")
        self.running = False
        
        # 시스템 모니터 중지
        self.system_monitor.stop_monitoring()
        
        # 스레드 종료 대기
        for name, thread in self.threads:
            if thread.is_alive():
                self.logger.info(f"{name} 스레드 종료 대기...")
                thread.join(timeout=5)
        
        self.logger.info("모든 시스템이 안전하게 종료되었습니다")
    
    def run_interactive_mode(self):
        """대화형 모드 실행"""
        self.start_all_systems()
        
        try:
            while self.running:
                try:
                    command = input("\n명령어 입력 (help, status, stop): ").strip().lower()
                    
                    if command == 'help':
                        print("\n사용 가능한 명령어:")
                        print("  status  - 시스템 상태 확인")
                        print("  archive - 수동 아카이빙 실행")
                        print("  health  - 건강 상태 점검")
                        print("  clean   - 임시 파일 정리")
                        print("  stop    - 시스템 종료")
                        print("  help    - 이 도움말")
                    
                    elif command == 'status':
                        status = self.get_system_status()
                        print(f"\n시스템 상태: {'실행 중' if status['running'] else '중지됨'}")
                        print(f"활성 스레드: {len([t for n, t in status['active_threads'] if t])}")
                        
                        if 'system_monitor' in status['components']:
                            monitor_status = status['components']['system_monitor']
                            print(f"모니터링: {monitor_status['status']}, 연결: {monitor_status.get('active_connections', 0)}개")
                    
                    elif command == 'archive':
                        print("패킷 데이터 아카이빙 실행 중...")
                        results = self.packet_manager.archive_old_data()
                        print(f"아카이빙 완료: {len(results['archived'])}개 처리, {results['space_saved']//1024//1024}MB 절약")
                    
                    elif command == 'health':
                        health = self.maintenance_system.health_check()
                        print(f"\n시스템 건강 상태: {health['status']}")
                        if health['warnings']:
                            for warning in health['warnings']:
                                print(f"  경고: {warning}")
                    
                    elif command == 'clean':
                        print("임시 파일 정리 실행 중...")
                        results = self.maintenance_system.cleanup_temp_files()
                        print(f"정리 완료: {results['files_cleaned']}개 파일, {results['space_freed_mb']}MB")
                    
                    elif command == 'stop':
                        break
                    
                    else:
                        print("알 수 없는 명령어입니다. 'help'를 입력하세요.")
                
                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
        
        finally:
            self.stop_all_systems()


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Two Very Auto 통합 시스템 관리자')
    parser.add_argument('--mode', choices=['interactive', 'daemon', 'status'], 
                       default='interactive', help='실행 모드')
    parser.add_argument('--optimize-only', action='store_true', help='최적화만 실행하고 종료')
    
    args = parser.parse_args()
    
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    manager = SystemManager()
    
    try:
        if args.optimize_only:
            manager.run_initial_optimization()
        
        elif args.mode == 'interactive':
            manager.run_interactive_mode()
        
        elif args.mode == 'daemon':
            manager.start_all_systems()
            # 백그라운드에서 계속 실행
            try:
                while manager.running:
                    import time
                    time.sleep(60)
            except KeyboardInterrupt:
                pass
        
        elif args.mode == 'status':
            manager.start_all_systems()
            import time
            time.sleep(2)  # 시스템 초기화 대기
            status = manager.get_system_status()
            
            print(f"\n=== Two Very Auto 시스템 상태 ===")
            print(f"실행 상태: {'실행 중' if status['running'] else '중지됨'}")
            print(f"타임스탬프: {status['timestamp']}")
            
            if 'components' in status:
                print(f"\n구성요소 상태:")
                for component, info in status['components'].items():
                    if isinstance(info, dict) and 'status' in info:
                        print(f"  {component}: {info['status']}")
            
            manager.stop_all_systems()
    
    except Exception as e:
        logging.error(f"시스템 실행 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()