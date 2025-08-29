#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Windows 작업 스케줄러 통합
백업 스케줄을 Windows 작업 스케줄러에 등록하여 시스템 레벨에서 관리
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 한국어 인코딩 설정
setup_korean_encoding()

class WindowsTaskScheduler:
    """Windows 작업 스케줄러 관리"""
    
    def __init__(self):
        self.task_folder = "\\TwoVeryAuto"
        self.python_exe = self._find_python_executable()
        self.project_dir = Path(__file__).parent.absolute()
        
        safe_print("📅 Windows 작업 스케줄러 관리자 초기화")
    
    def _find_python_executable(self) -> str:
        """Python 실행 파일 경로 찾기"""
        import sys
        return sys.executable
    
    def check_admin_privileges(self) -> bool:
        """관리자 권한 확인"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def create_task_xml(self, task_name: str, script_path: str, schedule_info: Dict[str, Any]) -> str:
        """작업 스케줄러 XML 생성"""
        
        # XML 템플릿
        task_xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{self._get_start_boundary(schedule_info)}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>{schedule_info.get('interval', 1)}</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{self.python_exe}</Command>
      <Arguments>"{script_path}"</Arguments>
      <WorkingDirectory>{self.project_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
        
        return task_xml
    
    def _get_start_boundary(self, schedule_info: Dict[str, Any]) -> str:
        """시작 시간 경계 계산"""
        time_str = schedule_info.get('time', '02:00')
        hour, minute = map(int, time_str.split(':'))
        
        # 내일부터 시작
        start_date = datetime.now() + timedelta(days=1)
        start_date = start_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return start_date.strftime('%Y-%m-%dT%H:%M:%S')
    
    def register_backup_tasks(self) -> Dict[str, bool]:
        """백업 작업들을 Windows 스케줄러에 등록"""
        
        if not self.check_admin_privileges():
            safe_print("⚠️ 관리자 권한이 필요합니다. 관리자로 다시 실행해주세요.")
            return {}
        
        # 백업 스케줄 설정 로드
        config_path = Path("backup_schedule_config.json")
        if not config_path.exists():
            safe_print("❌ 백업 스케줄 설정 파일이 없습니다")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            schedule_config = json.load(f)
        
        results = {}
        schedules = schedule_config.get('schedules', {})
        
        # 각 스케줄에 대해 작업 생성
        for schedule_name, schedule_info in schedules.items():
            if not schedule_info.get('enabled', True):
                continue
                
            task_name = f"TwoVeryAuto_{schedule_name}"
            script_path = self.project_dir / "run_scheduled_backup.py"
            
            # 백업 실행 스크립트 생성
            self._create_backup_execution_script(script_path, schedule_name, schedule_info)
            
            # Windows 작업 등록
            success = self._register_windows_task(task_name, script_path, schedule_info)
            results[schedule_name] = success
            
            if success:
                safe_print(f"✅ {schedule_name} 작업 등록 완료")
            else:
                safe_print(f"❌ {schedule_name} 작업 등록 실패")
        
        return results
    
    def _create_backup_execution_script(self, script_path: Path, schedule_name: str, schedule_info: Dict[str, Any]):
        """백업 실행 스크립트 생성"""
        
        script_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows 스케줄러용 백업 실행 스크립트
스케줄: {schedule_name}
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent))

# 로깅 설정
log_file = Path(__file__).parent / "logs" / f"backup_{schedule_name}_{{datetime.now().strftime('%Y%m%d')}}.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """백업 실행 메인 함수"""
    logger.info(f"백업 작업 시작: {schedule_name}")
    
    try:
        from cloud.backup_manager import get_backup_manager
        
        backup_manager = get_backup_manager()
        config_names = {schedule_info.get('configs', ['local_backup'])}
        
        results = []
        for config_name in config_names:
            logger.info(f"백업 실행: {{config_name}}")
            result = backup_manager.backup_database(config_name)
            results.append(result)
            
            if result.success:
                logger.info(f"✅ {{config_name}} 백업 성공 ({{result.size_mb:.1f}}MB)")
            else:
                logger.error(f"❌ {{config_name}} 백업 실패: {{result.error_message}}")
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"백업 작업 완료: {{success_count}}/{{len(results)}} 성공")
        
        # 성공률이 50% 미만이면 오류 코드 반환
        if success_count / len(results) < 0.5:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"백업 작업 오류: {{e}}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
    
    def _register_windows_task(self, task_name: str, script_path: Path, schedule_info: Dict[str, Any]) -> bool:
        """Windows 작업 스케줄러에 작업 등록"""
        
        try:
            # 작업 XML 생성
            task_xml = self.create_task_xml(task_name, str(script_path), schedule_info)
            
            # 임시 XML 파일 저장
            xml_file = Path(f"temp_{task_name}.xml")
            with open(xml_file, 'w', encoding='utf-16') as f:
                f.write(task_xml)
            
            # schtasks 명령어로 작업 생성
            cmd = [
                'schtasks',
                '/create',
                '/tn', f"{self.task_folder}\\{task_name}",
                '/xml', str(xml_file),
                '/f'  # 덮어쓰기
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            # 임시 파일 삭제
            xml_file.unlink(missing_ok=True)
            
            if result.returncode == 0:
                return True
            else:
                safe_print(f"작업 등록 오류: {result.stderr}")
                return False
                
        except Exception as e:
            safe_print(f"작업 등록 예외: {e}")
            return False
    
    def list_registered_tasks(self) -> List[Dict[str, Any]]:
        """등록된 백업 작업 목록 조회"""
        
        try:
            cmd = ['schtasks', '/query', '/fo', 'csv', '/tn', f"{self.task_folder}\\*"]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode != 0:
                return []
            
            # CSV 파싱
            import csv
            from io import StringIO
            
            tasks = []
            csv_reader = csv.DictReader(StringIO(result.stdout))
            
            for row in csv_reader:
                if 'TwoVeryAuto' in row.get('TaskName', ''):
                    tasks.append({
                        'name': row.get('TaskName', ''),
                        'status': row.get('Status', ''),
                        'next_run': row.get('Next Run Time', ''),
                        'last_run': row.get('Last Run Time', '')
                    })
            
            return tasks
            
        except Exception as e:
            safe_print(f"작업 목록 조회 오류: {e}")
            return []
    
    def remove_all_backup_tasks(self) -> bool:
        """모든 백업 작업 제거"""
        
        if not self.check_admin_privileges():
            safe_print("⚠️ 관리자 권한이 필요합니다")
            return False
        
        try:
            cmd = ['schtasks', '/delete', '/tn', f"{self.task_folder}\\*", '/f']
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                safe_print("✅ 모든 백업 작업 제거 완료")
                return True
            else:
                safe_print(f"작업 제거 오류: {result.stderr}")
                return False
                
        except Exception as e:
            safe_print(f"작업 제거 예외: {e}")
            return False
    
    def create_manual_setup_guide(self):
        """수동 설정 가이드 생성"""
        guide_content = '''# Windows 작업 스케줄러 수동 설정 가이드

## 1. 작업 스케줄러 열기
- Windows 키 + R → `taskschd.msc` 입력
- 또는 시작 메뉴에서 "작업 스케줄러" 검색

## 2. 새 폴더 만들기
- 작업 스케줄러 라이브러리 우클릭 → "새 폴더"
- 폴더명: `TwoVeryAuto`

## 3. 백업 작업 생성

### 일일 백업 작업
1. TwoVeryAuto 폴더 우클릭 → "기본 작업 만들기"
2. 이름: `TwoVeryAuto_DailyBackup`
3. 트리거: 매일
4. 시간: 오전 2시
5. 동작: 프로그램 시작
6. 프로그램: Python 경로 (예: C:\\Python311\\python.exe)
7. 인수: "F:\\two very auto 25.08.23\\run_scheduled_backup.py"
8. 시작 위치: "F:\\two very auto 25.08.23"

### 주간 백업 작업
1. 이름: `TwoVeryAuto_WeeklyBackup`
2. 트리거: 매주 (일요일)
3. 시간: 오전 1시
4. 나머지는 동일

## 4. 고급 설정
- 작업 속성 → 조건 탭
  - "컴퓨터가 배터리 전원을 사용하는 경우 시작 안 함" 해제
  - "네트워크를 사용할 수 있는 경우에만 시작" 체크
- 설정 탭
  - "요청 시 작업 실행 허용" 체크
  - "실행 시간 제한" 1시간으로 설정

## 5. 테스트
- 작업 우클릭 → "실행"으로 테스트 가능
- 기록 탭에서 실행 로그 확인

## Python 경로 찾기
명령 프롬프트에서 `where python` 실행하여 경로 확인
'''
        
        guide_path = Path("Windows_Task_Scheduler_Guide.md")
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        safe_print(f"📖 수동 설정 가이드 생성: {guide_path}")
        return str(guide_path)

    def run_task_now(self, task_name: str) -> bool:
        """작업 즉시 실행"""
        try:
            cmd = ['schtasks', '/run', '/tn', f"{self.task_folder}\\{task_name}"]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                safe_print(f"✅ 작업 실행 완료: {task_name}")
                return True
            else:
                safe_print(f"❌ 작업 실행 실패: {result.stderr}")
                return False
        except Exception as e:
            safe_print(f"작업 실행 예외: {e}")
            return False
    
    def enable_task(self, task_name: str) -> bool:
        """작업 활성화"""
        try:
            cmd = ['schtasks', '/change', '/tn', f"{self.task_folder}\\{task_name}", '/enable']
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                safe_print(f"✅ 작업 활성화: {task_name}")
                return True
            else:
                safe_print(f"❌ 작업 활성화 실패: {result.stderr}")
                return False
        except Exception as e:
            safe_print(f"작업 활성화 예외: {e}")
            return False
    
    def disable_task(self, task_name: str) -> bool:
        """작업 비활성화"""
        try:
            cmd = ['schtasks', '/change', '/tn', f"{self.task_folder}\\{task_name}", '/disable']
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                safe_print(f"⏸️ 작업 비활성화: {task_name}")
                return True
            else:
                safe_print(f"❌ 작업 비활성화 실패: {result.stderr}")
                return False
        except Exception as e:
            safe_print(f"작업 비활성화 예외: {e}")
            return False
    
    def get_task_history(self, task_name: str, days: int = 7) -> List[Dict[str, str]]:
        """작업 실행 기록 조회"""
        try:
            # PowerShell을 사용하여 이벤트 로그에서 작업 기록 조회
            ps_script = f'''
            Get-WinEvent -FilterHashtable @{{LogName="Microsoft-Windows-TaskScheduler/Operational"; StartTime=(Get-Date).AddDays(-{days})}} |
            Where-Object {{$_.Message -like "*{task_name}*"}} |
            Select-Object TimeCreated, Id, LevelDisplayName, Message |
            ConvertTo-Json
            '''
            
            result = subprocess.run(['powershell', '-Command', ps_script], 
                                  capture_output=True, text=True, shell=True, encoding='utf-8')
            
            if result.returncode == 0 and result.stdout.strip():
                import json
                events = json.loads(result.stdout)
                if not isinstance(events, list):
                    events = [events]
                
                history = []
                for event in events:
                    history.append({
                        'time': event.get('TimeCreated', ''),
                        'level': event.get('LevelDisplayName', ''),
                        'message': event.get('Message', '')[:200] + '...' if len(event.get('Message', '')) > 200 else event.get('Message', ''),
                        'event_id': str(event.get('Id', ''))
                    })
                
                return history
            else:
                return []
                
        except Exception as e:
            safe_print(f"작업 기록 조회 오류: {e}")
            return []
    
    def create_monitoring_script(self) -> str:
        """백업 모니터링 스크립트 생성"""
        monitoring_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Two Very Auto 백업 모니터링 스크립트
Windows 작업 스케줄러의 백업 작업 상태를 모니터링
"""

import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

setup_korean_encoding()

def check_backup_tasks():
    """백업 작업 상태 확인"""
    try:
        cmd = ['schtasks', '/query', '/fo', 'csv', '/tn', '\\\\TwoVeryAuto\\\\*']
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        
        if result.returncode != 0:
            safe_print("❌ 백업 작업을 찾을 수 없습니다")
            return []
        
        import csv
        from io import StringIO
        
        tasks = []
        csv_reader = csv.DictReader(StringIO(result.stdout))
        
        for row in csv_reader:
            if 'TwoVeryAuto' in row.get('TaskName', ''):
                task_info = {
                    'name': row.get('TaskName', ''),
                    'status': row.get('Status', ''),
                    'next_run': row.get('Next Run Time', ''),
                    'last_run': row.get('Last Run Time', ''),
                    'last_result': row.get('Last Result', '')
                }
                tasks.append(task_info)
        
        return tasks
        
    except Exception as e:
        safe_print(f"작업 상태 확인 오류: {e}")
        return []

def check_recent_backups():
    """최근 백업 파일 확인"""
    backup_dir = Path("temp_backups")
    if not backup_dir.exists():
        return []
    
    recent_backups = []
    cutoff_time = datetime.now() - timedelta(hours=24)
    
    for backup_file in backup_dir.glob("*.tar.gz"):
        if backup_file.stat().st_mtime > cutoff_time.timestamp():
            recent_backups.append({
                'file': backup_file.name,
                'size': f"{backup_file.stat().st_size / (1024*1024):.1f}MB",
                'time': datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return recent_backups

def main():
    """모니터링 메인 함수"""
    safe_print("=== Two Very Auto 백업 모니터링 ===")
    safe_print(f"모니터링 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 작업 스케줄러 상태 확인
    tasks = check_backup_tasks()
    safe_print(f"\\n📅 등록된 백업 작업: {len(tasks)}개")
    
    for task in tasks:
        task_name = task['name'].replace('\\\\TwoVeryAuto\\\\', '')
        status_icon = "✅" if task['status'] == "Ready" else "❌"
        safe_print(f"  {status_icon} {task_name}: {task['status']}")
        safe_print(f"     다음 실행: {task['next_run']}")
        safe_print(f"     마지막 실행: {task['last_run']}")
        safe_print(f"     마지막 결과: {task['last_result']}")
    
    # 최근 백업 파일 확인
    recent_backups = check_recent_backups()
    safe_print(f"\\n📦 최근 24시간 백업: {len(recent_backups)}개")
    
    for backup in recent_backups:
        safe_print(f"  📄 {backup['file']}")
        safe_print(f"     크기: {backup['size']}, 시간: {backup['time']}")
    
    if not recent_backups:
        safe_print("  ⚠️ 최근 24시간 내 백업이 없습니다")
    
    # 로그 파일 확인
    log_dir = Path("logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("backup_*.log"))
        safe_print(f"\\n📋 로그 파일: {len(log_files)}개")
        
        for log_file in sorted(log_files)[-3:]:  # 최근 3개만
            safe_print(f"  📄 {log_file.name}")

if __name__ == "__main__":
    main()
'''
        
        script_path = Path("backup_monitoring.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(monitoring_script)
        
        safe_print(f"📊 모니터링 스크립트 생성: {script_path}")
        return str(script_path)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Windows 작업 스케줄러 관리")
    parser.add_argument("--register", action="store_true", help="백업 작업 등록")
    parser.add_argument("--list", action="store_true", help="등록된 작업 목록")
    parser.add_argument("--remove-all", action="store_true", help="모든 작업 제거")
    parser.add_argument("--run-task", metavar="TASK", help="특정 작업 실행")
    parser.add_argument("--enable-task", metavar="TASK", help="작업 활성화")
    parser.add_argument("--disable-task", metavar="TASK", help="작업 비활성화")
    parser.add_argument("--history", metavar="TASK", help="작업 실행 기록")
    parser.add_argument("--create-guide", action="store_true", help="수동 설정 가이드 생성")
    parser.add_argument("--create-monitor", action="store_true", help="모니터링 스크립트 생성")
    
    args = parser.parse_args()
    
    scheduler = WindowsTaskScheduler()
    
    safe_print("=== Windows 작업 스케줄러 관리 ===")
    
    # 관리자 권한 확인
    is_admin = scheduler.check_admin_privileges()
    safe_print(f"관리자 권한: {'✅ 있음' if is_admin else '❌ 없음'}")
    safe_print(f"Python 경로: {scheduler.python_exe}")
    safe_print(f"프로젝트 경로: {scheduler.project_dir}")
    
    if args.register:
        if is_admin:
            results = scheduler.register_backup_tasks()
            success_count = sum(results.values())
            safe_print(f"\\n📊 등록 결과: {success_count}/{len(results)} 성공")
        else:
            safe_print("❌ 관리자 권한이 필요합니다")
    elif args.list:
        tasks = scheduler.list_registered_tasks()
        safe_print(f"\\n등록된 작업 수: {len(tasks)}")
        for task in tasks:
            safe_print(f"  📅 {task['name']}: {task['status']}")
            safe_print(f"     다음 실행: {task['next_run']}")
            safe_print(f"     마지막 실행: {task['last_run']}")
    elif args.remove_all:
        if scheduler.remove_all_backup_tasks():
            safe_print("✅ 모든 작업 제거 완료")
    elif args.run_task:
        scheduler.run_task_now(args.run_task)
    elif args.enable_task:
        scheduler.enable_task(args.enable_task)
    elif args.disable_task:
        scheduler.disable_task(args.disable_task)
    elif args.history:
        history = scheduler.get_task_history(args.history)
        safe_print(f"\\n📊 {args.history} 실행 기록 (최근 7일):")
        for record in history[:10]:  # 최근 10개만
            safe_print(f"  {record['time']} [{record['level']}] {record['message']}")
    elif args.create_guide:
        guide_path = scheduler.create_manual_setup_guide()
        safe_print(f"📖 수동 설정 가이드: {guide_path}")
    elif args.create_monitor:
        monitor_path = scheduler.create_monitoring_script()
        safe_print(f"📊 모니터링 스크립트: {monitor_path}")
    else:
        # 기본 상태 표시
        tasks = scheduler.list_registered_tasks()
        safe_print(f"\\n등록된 작업 수: {len(tasks)}")
        
        for task in tasks:
            safe_print(f"  - {task['name']}: {task['status']}")
        
        if is_admin and not tasks:
            choice = input("\\n백업 작업을 등록하시겠습니까? (Y/n): ").strip().lower()
            if choice != 'n':
                results = scheduler.register_backup_tasks()
                success_count = sum(results.values())
                safe_print(f"\\n📊 등록 결과: {success_count}/{len(results)} 성공")
        elif not is_admin:
            safe_print("\\n💡 사용 가능한 명령어:")
            safe_print("  --list           : 작업 목록")
            safe_print("  --create-guide   : 수동 설정 가이드")
            safe_print("  --create-monitor : 모니터링 스크립트")