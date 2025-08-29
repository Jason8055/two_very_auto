#!/usr/bin/env python3
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
        cmd = ['schtasks', '/query', '/fo', 'csv', '/tn', '\\TwoVeryAuto\\*']
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
    safe_print(f"\n📅 등록된 백업 작업: {len(tasks)}개")
    
    for task in tasks:
        task_name = task['name'].replace('\\TwoVeryAuto\\', '')
        status_icon = "✅" if task['status'] == "Ready" else "❌"
        safe_print(f"  {status_icon} {task_name}: {task['status']}")
        safe_print(f"     다음 실행: {task['next_run']}")
        safe_print(f"     마지막 실행: {task['last_run']}")
        safe_print(f"     마지막 결과: {task['last_result']}")
    
    # 최근 백업 파일 확인
    recent_backups = check_recent_backups()
    safe_print(f"\n📦 최근 24시간 백업: {len(recent_backups)}개")
    
    for backup in recent_backups:
        safe_print(f"  📄 {backup['file']}")
        safe_print(f"     크기: {backup['size']}, 시간: {backup['time']}")
    
    if not recent_backups:
        safe_print("  ⚠️ 최근 24시간 내 백업이 없습니다")
    
    # 로그 파일 확인
    log_dir = Path("logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("backup_*.log"))
        safe_print(f"\n📋 로그 파일: {len(log_files)}개")
        
        for log_file in sorted(log_files)[-3:]:  # 최근 3개만
            safe_print(f"  📄 {log_file.name}")

if __name__ == "__main__":
    main()
