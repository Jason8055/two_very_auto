#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Two Very Auto 통합 시스템 런처
모든 시스템 컴포넌트를 통합하여 시작하는 메인 런처
"""

import asyncio
import argparse
import logging
import os
import sys
import time
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 프로젝트 루트 디렉토리 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'python'))

from main_integration_service import MainIntegrationService, get_integration_service
from integrated_dashboard import dashboard_app, dashboard_controller
from realtime_ai_integration import RealtimeAIIntegrator
from ipc_communication import IntegratedIPCManager

# 로깅 설정
def setup_logging(log_level: str = 'INFO'):
    """로깅 시스템 설정"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 파일 핸들러
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f'two_very_auto_{datetime.now().strftime("%Y%m%d")}.log'
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)


class IntegratedTwoVeryAutoLauncher:
    """Two Very Auto 통합 런처"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or self._get_default_config()
        
        # 시스템 컴포넌트들
        self.integration_service = None
        self.dashboard_server = None
        self.ai_integrator = None
        self.ipc_manager = None
        
        self.is_running = False
        self.shutdown_requested = False
        
        self.logger.info("Two Very Auto 통합 런처 초기화 완료")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            'main_exe_path': 'two very auto.exe',
            'dashboard_host': '0.0.0.0',
            'dashboard_port': 8000,
            'fastapi_port': 8001,
            'fastapi_host': '0.0.0.0',
            'auto_start_main_exe': True,
            'auto_start_fastapi': True,
            'enable_dashboard': True,
            'enable_ai_integration': True,
            'enable_ipc': True,
            'packet_monitor_enabled': True,
            'ai_integration_enabled': True,
            'packet_folder': 'packet',
            'log_level': 'INFO',
            'health_check_interval': 30
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """설정 업데이트"""
        self.config.update(new_config)
        self.logger.info(f"설정 업데이트: {new_config}")
    
    async def start_all_services(self) -> bool:
        """모든 서비스 시작"""
        if self.is_running:
            self.logger.warning("서비스가 이미 실행 중입니다")
            return False
        
        try:
            self.logger.info("🚀 Two Very Auto 통합 시스템 시작")
            self.is_running = True
            
            startup_results = []
            
            # 1. IPC 통신 시스템 시작
            if self.config['enable_ipc']:
                if await self._start_ipc_system():
                    startup_results.append("✅ IPC 시스템")
                else:
                    startup_results.append("❌ IPC 시스템")
                    self.logger.error("IPC 시스템 시작 실패")
            
            # 2. AI 통합 시스템 시작
            if self.config['enable_ai_integration']:
                if await self._start_ai_system():
                    startup_results.append("✅ AI 통합 시스템")
                else:
                    startup_results.append("❌ AI 통합 시스템")
                    self.logger.error("AI 통합 시스템 시작 실패")
            
            # 3. 메인 통합 서비스 시작
            if await self._start_integration_service():
                startup_results.append("✅ 통합 서비스")
            else:
                startup_results.append("❌ 통합 서비스")
                self.logger.error("통합 서비스 시작 실패")
                return False
            
            # 4. 대시보드 서버 시작
            if self.config['enable_dashboard']:
                if await self._start_dashboard_server():
                    startup_results.append("✅ 대시보드 서버")
                else:
                    startup_results.append("❌ 대시보드 서버")
                    self.logger.error("대시보드 서버 시작 실패")
            
            # 5. 시스템 상태 모니터링 시작
            await self._start_health_monitoring()
            startup_results.append("✅ 상태 모니터링")
            
            self.logger.info("🎉 시스템 시작 완료:")
            for result in startup_results:
                self.logger.info(f"  {result}")
            
            # 시스템 정보 출력
            await self._print_system_info()
            
            return True
            
        except Exception as e:
            self.logger.error(f"서비스 시작 중 오류: {e}", exc_info=True)
            await self.stop_all_services()
            return False
    
    async def _start_ipc_system(self) -> bool:
        """IPC 통신 시스템 시작"""
        try:
            self.ipc_manager = IntegratedIPCManager()
            
            # 기본 메시지 핸들러 등록
            self.ipc_manager.register_handler('health_check', self._handle_health_check)
            self.ipc_manager.register_handler('system_status', self._handle_status_request)
            
            if self.ipc_manager.start():
                self.logger.info("✅ IPC 통신 시스템 시작됨")
                return True
            else:
                self.logger.error("❌ IPC 통신 시스템 시작 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"IPC 시스템 시작 오류: {e}")
            return False
    
    async def _start_ai_system(self) -> bool:
        """AI 통합 시스템 시작"""
        try:
            self.ai_integrator = RealtimeAIIntegrator()
            
            # 예측 결과 콜백 등록
            self.ai_integrator.add_prediction_callback(self._on_ai_prediction)
            
            if self.ai_integrator.start(self.ipc_manager):
                self.logger.info("✅ AI 통합 시스템 시작됨")
                return True
            else:
                self.logger.error("❌ AI 통합 시스템 시작 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"AI 시스템 시작 오류: {e}")
            return False
    
    async def _start_integration_service(self) -> bool:
        """메인 통합 서비스 시작"""
        try:
            self.integration_service = get_integration_service()
            
            # 설정 업데이트
            service_config = {
                'fastapi_host': self.config['fastapi_host'],
                'fastapi_port': self.config['fastapi_port'],
                'auto_start_main_exe': self.config['auto_start_main_exe'],
                'auto_start_fastapi': self.config['auto_start_fastapi'],
                'packet_monitor_enabled': self.config['packet_monitor_enabled'],
                'ai_integration_enabled': self.config['ai_integration_enabled']
            }
            
            self.integration_service.update_config(service_config)
            
            # 이벤트 콜백 등록
            self.integration_service.add_event_callback('service_started', self._on_service_event)
            self.integration_service.add_event_callback('packet_processed', self._on_packet_processed)
            self.integration_service.add_event_callback('main_exe_started', self._on_main_exe_started)
            
            # 메인 실행 파일 경로 설정
            main_exe_path = project_root / self.config['main_exe_path']
            if main_exe_path.exists():
                self.integration_service.main_exe_path = main_exe_path
            else:
                self.logger.warning(f"메인 실행 파일을 찾을 수 없음: {main_exe_path}")
            
            success = await self.integration_service.start_service()
            if success:
                self.logger.info("✅ 메인 통합 서비스 시작됨")
                return True
            else:
                self.logger.error("❌ 메인 통합 서비스 시작 실패")
                return False
                
        except Exception as e:
            self.logger.error(f"통합 서비스 시작 오류: {e}")
            return False
    
    async def _start_dashboard_server(self) -> bool:
        """대시보드 서버 시작"""
        try:
            import uvicorn
            from integrated_dashboard import create_dashboard_template, dashboard_controller
            
            # 대시보드 템플릿 생성
            create_dashboard_template()
            
            # 대시보드 컨트롤러 시작
            if not await dashboard_controller.start():
                self.logger.error("대시보드 컨트롤러 시작 실패")
                return False
            
            # 별도 스레드에서 대시보드 서버 실행
            def run_dashboard():
                try:
                    uvicorn.run(
                        dashboard_app,
                        host=self.config['dashboard_host'],
                        port=self.config['dashboard_port'],
                        log_level="warning",
                        access_log=False
                    )
                except Exception as e:
                    self.logger.error(f"대시보드 서버 실행 오류: {e}")
            
            import threading
            dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
            dashboard_thread.start()
            
            # 서버 시작 대기
            await asyncio.sleep(3)
            
            # 대시보드 URL 정보
            dashboard_url = f"http://{self.config['dashboard_host']}:{self.config['dashboard_port']}"
            self.logger.info(f"✅ 대시보드 서버 시작됨: {dashboard_url}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"대시보드 서버 시작 오류: {e}")
            return False
    
    async def _start_health_monitoring(self):
        """시스템 상태 모니터링 시작"""
        async def health_monitor():
            while self.is_running and not self.shutdown_requested:
                try:
                    await self._perform_health_check()
                    await asyncio.sleep(self.config['health_check_interval'])
                except Exception as e:
                    self.logger.error(f"상태 모니터링 오류: {e}")
                    await asyncio.sleep(10)
        
        asyncio.create_task(health_monitor())
        self.logger.info("✅ 시스템 상태 모니터링 시작됨")
    
    async def _perform_health_check(self):
        """시스템 상태 점검"""
        try:
            status_summary = {
                'timestamp': datetime.now().isoformat(),
                'components': {}
            }
            
            # 통합 서비스 상태
            if self.integration_service:
                service_status = self.integration_service.get_service_status()
                status_summary['components']['integration_service'] = {
                    'status': 'running' if service_status.get('service', {}).get('is_running', False) else 'stopped',
                    'uptime': service_status.get('service', {}).get('uptime_seconds', 0),
                    'total_games': service_status.get('statistics', {}).get('total_games_processed', 0)
                }
            
            # AI 시스템 상태
            if self.ai_integrator:
                ai_status = self.ai_integrator.get_system_status()
                status_summary['components']['ai_system'] = {
                    'status': 'running' if ai_status.get('is_running', False) else 'stopped',
                    'queue_size': ai_status.get('processing_queue_size', 0),
                    'callback_count': ai_status.get('callback_count', 0)
                }
            
            # IPC 시스템 상태
            if self.ipc_manager:
                status_summary['components']['ipc_system'] = {
                    'status': 'running' if self.ipc_manager.is_running else 'stopped'
                }
            
            # 주기적 상태 로깅 (5분마다)
            current_time = time.time()
            if not hasattr(self, '_last_status_log') or current_time - self._last_status_log > 300:
                self._last_status_log = current_time
                self.logger.info(f"📊 시스템 상태 요약: {status_summary}")
            
        except Exception as e:
            self.logger.error(f"상태 점검 중 오류: {e}")
    
    async def _print_system_info(self):
        """시스템 정보 출력"""
        dashboard_url = f"http://{self.config['dashboard_host']}:{self.config['dashboard_port']}"
        fastapi_url = f"http://localhost:{self.config['fastapi_port']}"
        
        info = f"""
╔══════════════════════════════════════════════════════════╗
║                 Two Very Auto 통합 시스템                 ║
╠══════════════════════════════════════════════════════════╣
║ 🎯 대시보드: {dashboard_url:<40} ║
║ 🔧 API 서버: {fastapi_url:<40} ║
║ 📁 패킷 폴더: {str(project_root / self.config['packet_folder']):<37} ║
║ 🤖 AI 통합: {'✅ 활성화' if self.config['enable_ai_integration'] else '❌ 비활성화':<40} ║
║ 🔗 IPC 통신: {'✅ 활성화' if self.config['enable_ipc'] else '❌ 비활성화':<39} ║
╚══════════════════════════════════════════════════════════╝

시스템이 성공적으로 시작되었습니다!
웹 브라우저에서 {dashboard_url} 에 접속하여 실시간 대시보드를 확인하세요.
"""
        self.logger.info(info)
    
    async def stop_all_services(self):
        """모든 서비스 중지"""
        if not self.is_running:
            return
        
        try:
            self.logger.info("⏹️ 모든 서비스 중지 시작")
            self.shutdown_requested = True
            self.is_running = False
            
            # 1. 대시보드 컨트롤러 중지
            if hasattr(dashboard_controller, 'stop'):
                await dashboard_controller.stop()
                self.logger.info("✅ 대시보드 컨트롤러 중지됨")
            
            # 2. 통합 서비스 중지
            if self.integration_service:
                await self.integration_service.stop_service()
                self.logger.info("✅ 통합 서비스 중지됨")
            
            # 3. AI 시스템 중지
            if self.ai_integrator:
                self.ai_integrator.stop()
                self.logger.info("✅ AI 통합 시스템 중지됨")
            
            # 4. IPC 매니저 중지
            if self.ipc_manager:
                self.ipc_manager.stop()
                self.logger.info("✅ IPC 시스템 중지됨")
            
            self.logger.info("🎉 모든 서비스가 안전하게 중지되었습니다")
            
        except Exception as e:
            self.logger.error(f"서비스 중지 중 오류: {e}", exc_info=True)
    
    # 이벤트 콜백 메서드들
    def _on_service_event(self, event_data: Dict[str, Any]):
        """서비스 이벤트 처리"""
        self.logger.info(f"🔔 서비스 이벤트: {event_data}")
    
    def _on_packet_processed(self, event_data: Dict[str, Any]):
        """패킷 처리 이벤트"""
        self.logger.debug(f"📦 패킷 처리됨: {event_data.get('file_name')} - {event_data.get('data_count')}개")
    
    def _on_main_exe_started(self, event_data: Dict[str, Any]):
        """메인 실행 파일 시작 이벤트"""
        self.logger.info(f"🎯 Main 실행 파일 시작됨: {event_data.get('exe_path')}")
    
    def _on_ai_prediction(self, prediction_result):
        """AI 예측 결과 처리"""
        self.logger.debug(f"🧠 AI 예측: 테이블 {prediction_result.table_id} - "
                         f"페어확률 {prediction_result.any_pair_probability:.2%}")
    
    # IPC 메시지 핸들러들
    def _handle_health_check(self, message):
        """헬스 체크 요청 처리"""
        return {
            'status': 'healthy' if self.is_running else 'stopped',
            'timestamp': datetime.now().isoformat(),
            'uptime': time.time() - getattr(self, '_start_time', time.time())
        }
    
    def _handle_status_request(self, message):
        """시스템 상태 요청 처리"""
        try:
            if self.integration_service:
                return self.integration_service.get_service_status()
            else:
                return {'error': '통합 서비스를 사용할 수 없습니다'}
        except Exception as e:
            self.logger.error(f"상태 요청 처리 오류: {e}")
            return {'error': str(e)}


# 시그널 핸들러
launcher_instance = None

def signal_handler(signum, frame):
    """시그널 핸들러 - 우아한 종료"""
    global launcher_instance
    logger = logging.getLogger(__name__)
    logger.info(f"시그널 수신: {signum}. 시스템을 안전하게 종료합니다...")
    
    if launcher_instance:
        asyncio.create_task(launcher_instance.stop_all_services())
    
    sys.exit(0)


async def main():
    """메인 실행 함수"""
    global launcher_instance
    
    # 명령줄 인수 파싱
    parser = argparse.ArgumentParser(description='Two Very Auto 통합 시스템 런처')
    parser.add_argument('--config', help='설정 파일 경로 (JSON)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    parser.add_argument('--dashboard-port', type=int, default=8000, help='대시보드 포트 (기본값: 8000)')
    parser.add_argument('--api-port', type=int, default=8001, help='API 서버 포트 (기본값: 8001)')
    parser.add_argument('--no-main-exe', action='store_true', help='메인 실행 파일 자동 시작 비활성화')
    parser.add_argument('--no-dashboard', action='store_true', help='대시보드 서버 비활성화')
    parser.add_argument('--no-ai', action='store_true', help='AI 통합 기능 비활성화')
    
    args = parser.parse_args()
    
    # 로깅 설정
    logger = setup_logging(args.log_level)
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 설정 로드 - 기본 설정부터 시작
    launcher_temp = IntegratedTwoVeryAutoLauncher()
    config = launcher_temp._get_default_config()
    
    # 설정 파일이 있으면 덮어쓰기
    if args.config and Path(args.config).exists():
        try:
            import json
            with open(args.config, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                config.update(file_config)
            logger.info(f"설정 파일 로드됨: {args.config}")
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
    
    # 명령줄 인수를 설정에 반영
    if args.dashboard_port:
        config['dashboard_port'] = args.dashboard_port
    if args.api_port:
        config['fastapi_port'] = args.api_port
    if args.no_main_exe:
        config['auto_start_main_exe'] = False
    if args.no_dashboard:
        config['enable_dashboard'] = False
    if args.no_ai:
        config['enable_ai_integration'] = False
    
    config['log_level'] = args.log_level
    
    # 런처 생성 및 시작
    launcher_instance = IntegratedTwoVeryAutoLauncher(config)
    
    try:
        logger.info("🚀 Two Very Auto 통합 시스템 런처 시작")
        
        # 모든 서비스 시작
        success = await launcher_instance.start_all_services()
        
        if not success:
            logger.error("❌ 시스템 시작 실패")
            return
        
        launcher_instance._start_time = time.time()
        
        # 시스템 실행 유지
        while launcher_instance.is_running and not launcher_instance.shutdown_requested:
            await asyncio.sleep(1)
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"메인 루프 오류: {e}", exc_info=True)
    finally:
        if launcher_instance:
            await launcher_instance.stop_all_services()


if __name__ == "__main__":
    # 작업 디렉토리를 프로젝트 루트로 변경
    os.chdir(project_root)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"실행 중 오류 발생: {e}")
        sys.exit(1)