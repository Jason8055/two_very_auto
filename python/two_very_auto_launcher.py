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

class TwoVeryAutoLauncher:
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
        
        self.logger.info("Two Very Auto 런처 초기화 완료")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            'main_exe_path': 'two very auto.exe',
            'dashboard_host': '0.0.0.0',
            'dashboard_port': 8000,
            'fastapi_port': 8001,
            'auto_start_main_exe': True,
            'enable_dashboard': True,
            'enable_ai_integration': True,
            'enable_ipc': True,
            'packet_folder': 'packet',
            'log_level': 'INFO',
            'health_check_interval': 30
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """설정 업데이트"""
        self.config.update(new_config)
        self.logger.info(f"설정 업데이트: {new_config}")
    
    async def start_all_services(self) -> bool:
        """설정 파일 로드"""
        default_config = {
            'auto_open_browser': True,
            'startup_delay': 2,
            'check_interval': 5,
            'max_retries': 3,
            'enabled_services': ['enhanced_processor', 'pair_alert_channel', 'web_server', 'static_server'],
            'window_title': 'Two Very Auto v3.2 - 통합 런처',
            'last_updated': datetime.now().isoformat()
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 기본값으로 누락된 키 채우기
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                logger.warning(f"설정 파일 로드 실패, 기본값 사용: {e}")
        
        return default_config
    
    def save_config(self):
        """설정 파일 저장"""
        try:
            self.config['last_updated'] = datetime.now().isoformat()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("설정 파일 저장 완료")
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
    
    def print_banner(self):
        """시작 배너 출력"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                    Two Very Auto v3.2                       ║
║                   통합 런처 시스템                            ║
╠══════════════════════════════════════════════════════════════╣
║  🎯 실시간 바카라 모니터링 시스템                             ║
║  📊 현대적 대시보드 인터페이스                                ║
║  🔔 스마트 알림 시스템                                        ║
║  📱 PWA 지원 모바일 친화적                                    ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)
        print(f"작업 디렉토리: {self.base_dir}")
        print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 64)
    
    def check_dependencies(self):
        """의존성 확인"""
        logger.info("의존성 확인 중...")
        
        # Python 버전 확인
        python_version = sys.version_info
        if python_version < (3, 7):
            logger.error(f"Python 3.7+ 필요, 현재 버전: {python_version}")
            return False
        
        # 필수 모듈 확인
        required_modules = ['flask', 'flask_cors']
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            logger.error(f"필수 모듈 누락: {missing_modules}")
            logger.info("다음 명령어로 설치하세요: pip install " + " ".join(missing_modules))
            return False
        
        # 필수 파일 확인
        required_files = [
            'enhanced_packet_processor.py',
            'pair_alert_channel.py', 
            'packet_decoder.py',
            'web_server.py',
            'pair_tracker.py',
            'modern_dashboard.html'
        ]
        
        missing_files = []
        for file in required_files:
            if not (self.base_dir / file).exists():
                missing_files.append(file)
        
        if missing_files:
            logger.warning(f"선택적 파일 누락: {missing_files}")
        
        logger.info("의존성 확인 완료")
        return True
    
    def start_python_service(self, service_info):
        """Python 서비스 시작"""
        file_path = self.base_dir / service_info['file']
        
        if not file_path.exists():
            logger.warning(f"파일을 찾을 수 없음: {file_path}")
            return None
        
        try:
            cmd = [sys.executable, str(file_path)]
            process = subprocess.Popen(
                cmd,
                cwd=self.base_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            logger.info(f"{service_info['name']} 시작됨 (PID: {process.pid})")
            return process
            
        except Exception as e:
            logger.error(f"{service_info['name']} 시작 실패: {e}")
            return None
    
    def start_http_server(self, service_info):
        """HTTP 정적 파일 서버 시작"""
        try:
            import http.server
            import socketserver
            from functools import partial
            
            port = service_info['port']
            
            def run_server():
                try:
                    # 현재 디렉토리를 기준으로 HTTP 서버 시작
                    Handler = partial(http.server.SimpleHTTPRequestHandler)
                    
                    with socketserver.TCPServer(("", port), Handler) as httpd:
                        logger.info(f"HTTP 서버 시작됨: http://127.0.0.1:{port}")
                        httpd.serve_forever()
                        
                except Exception as e:
                    logger.error(f"HTTP 서버 오류: {e}")
            
            # 별도 스레드에서 서버 실행
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            return server_thread
            
        except Exception as e:
            logger.error(f"HTTP 서버 시작 실패: {e}")
            return None
    
    def wait_for_service(self, service_info, timeout=30):
        """서비스가 준비될 때까지 대기"""
        if 'url' not in service_info:
            time.sleep(2)  # URL이 없으면 2초만 대기
            return True
        
        import urllib.request
        import urllib.error
        
        url = service_info['url']
        start_time = time.time()
        
        logger.info(f"{service_info['name']} 준비 대기 중... ({url})")
        
        while time.time() - start_time < timeout:
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    if response.getcode() == 200:
                        logger.info(f"{service_info['name']} 준비 완료")
                        return True
            except (urllib.error.URLError, urllib.error.HTTPError):
                pass
            
            time.sleep(1)
        
        logger.warning(f"{service_info['name']} 준비 시간 초과")
        return False
    
    def start_services(self):
        """모든 서비스 시작"""
        logger.info("서비스 시작 중...")
        
        # 우선순위 순으로 정렬
        sorted_services = sorted(
            self.executables.items(),
            key=lambda x: x[1].get('priority', 999)
        )
        
        for service_name, service_info in sorted_services:
            # 활성화된 서비스만 시작
            if service_name not in self.config['enabled_services']:
                logger.info(f"{service_info['name']} 비활성화됨 (건너뛰기)")
                continue
            
            logger.info(f"{service_info['name']} 시작 중...")
            
            process = None
            if service_info['type'] == 'python':
                process = self.start_python_service(service_info)
            elif service_info['type'] == 'http_server':
                process = self.start_http_server(service_info)
            
            if process:
                self.processes.append({
                    'name': service_info['name'],
                    'process': process,
                    'info': service_info
                })
                
                # 서비스 준비 대기
                if self.wait_for_service(service_info):
                    # 자동으로 브라우저에서 열기
                    if (service_info.get('auto_open', False) and 
                        self.config['auto_open_browser'] and 
                        'url' in service_info):
                        
                        logger.info(f"브라우저에서 열기: {service_info['url']}")
                        webbrowser.open(service_info['url'])
                        time.sleep(1)  # 브라우저 열기 간격
            else:
                if service_info.get('required', False):
                    logger.error(f"필수 서비스 시작 실패: {service_info['name']}")
                    return False
            
            # 서비스 간 시작 지연
            time.sleep(self.config['startup_delay'])
        
        return True
    
    def monitor_services(self):
        """서비스 상태 모니터링"""
        logger.info("서비스 모니터링 시작")
        
        while self.running:
            time.sleep(self.config['check_interval'])
            
            for service in self.processes[:]:  # 복사본으로 반복
                if hasattr(service['process'], 'poll'):  # subprocess인 경우
                    if service['process'].poll() is not None:
                        logger.warning(f"{service['name']} 프로세스 종료됨")
                        self.processes.remove(service)
                elif hasattr(service['process'], 'is_alive'):  # Thread인 경우
                    if not service['process'].is_alive():
                        logger.warning(f"{service['name']} 스레드 종료됨")
                        self.processes.remove(service)
    
    def show_status(self):
        """실행 중인 서비스 상태 표시"""
        print("\n" + "=" * 60)
        print("📊 서비스 상태")
        print("=" * 60)
        
        if not self.processes:
            print("실행 중인 서비스가 없습니다.")
            return
        
        for service in self.processes:
            status = "🟢 실행중"
            if hasattr(service['process'], 'poll'):
                if service['process'].poll() is not None:
                    status = "🔴 중지됨"
            elif hasattr(service['process'], 'is_alive'):
                if not service['process'].is_alive():
                    status = "🔴 중지됨"
            
            print(f"{status} {service['name']}")
            
            # URL이 있으면 표시
            if 'url' in service['info']:
                print(f"   → {service['info']['url']}")
    
    def show_urls(self):
        """접속 가능한 URL들 표시"""
        print("\n" + "=" * 60)
        print("🌐 접속 URL")
        print("=" * 60)
        
        urls = []
        for service in self.processes:
            if 'url' in service['info']:
                urls.append({
                    'name': service['name'],
                    'url': service['info']['url']
                })
        
        if urls:
            for url_info in urls:
                print(f"• {url_info['name']}")
                print(f"  {url_info['url']}")
                print()
        else:
            print("접속 가능한 URL이 없습니다.")
    
    def cleanup(self):
        """정리 작업"""
        logger.info("서비스 종료 중...")
        self.running = False
        
        for service in self.processes:
            try:
                if hasattr(service['process'], 'terminate'):  # subprocess
                    service['process'].terminate()
                    service['process'].wait(timeout=5)
                    logger.info(f"{service['name']} 종료됨")
                elif hasattr(service['process'], 'join'):  # Thread
                    logger.info(f"{service['name']} 스레드 종료 대기 중...")
            except Exception as e:
                logger.warning(f"{service['name']} 종료 중 오류: {e}")
        
        # 설정 저장
        self.save_config()
        logger.info("Two Very Auto 런처 종료됨")
    
    def interactive_menu(self):
        """대화형 메뉴"""
        while self.running:
            try:
                print("\n" + "=" * 60)
                print("📋 Two Very Auto 런처 메뉴")
                print("=" * 60)
                print("1. 서비스 상태 보기")
                print("2. 접속 URL 보기")
                print("3. 브라우저에서 메인 대시보드 열기")
                print("4. 브라우저에서 현대적 대시보드 열기")
                print("5. 페어 알림 채널 상태")
                print("6. 설정 보기")
                print("0. 종료")
                print("=" * 60)
                
                choice = input("선택하세요 (0-6): ").strip()
                
                if choice == '1':
                    self.show_status()
                elif choice == '2':
                    self.show_urls()
                elif choice == '3':
                    webbrowser.open('http://127.0.0.1:5555')
                    print("메인 대시보드를 브라우저에서 열었습니다.")
                elif choice == '4':
                    webbrowser.open('http://127.0.0.1:8080/modern_dashboard.html')
                    print("현대적 대시보드를 브라우저에서 열었습니다.")
                elif choice == '5':
                    print("\n🔔 페어 알림 채널 상태:")
                    print("  WebSocket 서버: ws://127.0.0.1:8765")
                    print("  실시간 페어 감지 및 알림 전송")
                    print("  연결 테스트: 브라우저 개발자 도구에서")
                    print("    const ws = new WebSocket('ws://127.0.0.1:8765');")
                elif choice == '6':
                    print("\n현재 설정:")
                    for key, value in self.config.items():
                        print(f"  {key}: {value}")
                elif choice == '0':
                    break
                else:
                    print("잘못된 선택입니다. 0-6 사이의 숫자를 입력하세요.")
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"메뉴 오류: {e}")
    
    def run(self):
        """메인 실행 함수"""
        try:
            # 배너 출력
            self.print_banner()
            
            # 의존성 확인
            if not self.check_dependencies():
                input("엔터 키를 눌러 종료하세요...")
                return False
            
            # 서비스 시작
            if not self.start_services():
                logger.error("핵심 서비스 시작 실패")
                input("엔터 키를 눌러 종료하세요...")
                return False
            
            self.running = True
            
            # 서비스 모니터링 스레드 시작
            monitor_thread = threading.Thread(target=self.monitor_services, daemon=True)
            monitor_thread.start()
            
            # 시작 완료 메시지
            print("\n🎉 Two Very Auto 시스템이 성공적으로 시작되었습니다!")
            self.show_urls()
            
            # 대화형 메뉴 실행
            self.interactive_menu()
            
            return True
            
        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단됨")
            return True
        except Exception as e:
            logger.error(f"런처 실행 오류: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """메인 함수"""
    # Windows에서 콘솔 창 제목 설정
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW("Two Very Auto v3.2 - 통합 런처")
        except:
            pass
    
    # 런처 실행
    launcher = TwoVeryAutoLauncher()
    success = launcher.run()
    
    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()