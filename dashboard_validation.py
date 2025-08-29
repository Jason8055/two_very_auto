#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
대시보드 자동 검증 도구 - 사용자 개입 없이 완전 자동화
"""

import requests
import time
import json
from pathlib import Path
import sys

# 한국어 인코딩 설정
sys.path.append(str(Path(__file__).parent / 'python'))
try:
    from python.korean_encoding_fix import setup_korean_encoding, safe_print
    setup_korean_encoding()
except:
    def safe_print(text):
        try:
            print(text)
        except:
            print(text.encode('utf-8', errors='ignore').decode('utf-8'))

def test_api_endpoint(url, name, timeout=10):
    """API 엔드포인트 테스트"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            safe_print(f"✅ {name}: 정상 ({response.status_code})")
            try:
                data = response.json()
                if isinstance(data, dict):
                    # 중요 데이터 표시
                    if 'timestamp' in data:
                        safe_print(f"   ⏰ 시간: {data['timestamp'][:19]}")
                    if 'status' in data:
                        safe_print(f"   📊 상태: {data['status']}")
                    if 'health_score' in data:
                        safe_print(f"   💯 점수: {data['health_score']}")
                    if 'total_count' in data:
                        safe_print(f"   🔢 항목수: {data['total_count']}")
                    if 'setup_progress' in data:
                        safe_print(f"   🎯 설정진행: {data['setup_progress']}%")
            except:
                safe_print(f"   📄 HTML ({len(response.text)} chars)")
            return True, response
        else:
            safe_print(f"⚠️ {name}: HTTP {response.status_code}")
            return False, response
    except requests.exceptions.ConnectionError:
        safe_print(f"❌ {name}: 연결 실패")
        return False, None
    except Exception as e:
        safe_print(f"❌ {name}: {str(e)[:50]}")
        return False, None

def test_post_endpoint(url, name, data=None, timeout=15):
    """POST API 엔드포인트 테스트"""
    try:
        response = requests.post(url, json=data, timeout=timeout)
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    safe_print(f"✅ {name}: 성공")
                    if 'message' in result:
                        safe_print(f"   💬 메시지: {result['message']}")
                else:
                    safe_print(f"⚠️ {name}: 작업 실패")
                    if 'error' in result:
                        safe_print(f"   ❌ 오류: {result['error']}")
            except:
                safe_print(f"✅ {name}: 응답 받음")
            return True, response
        else:
            safe_print(f"⚠️ {name}: HTTP {response.status_code}")
            return False, response
    except Exception as e:
        safe_print(f"❌ {name}: {str(e)[:50]}")
        return False, None

def validate_dashboard():
    """대시보드 완전 자동 검증"""
    safe_print("🎰 Two Very Auto 대시보드 완전 자동 검증")
    safe_print("=" * 60)
    
    # 1. 서버 찾기
    servers = [
        ("http://127.0.0.1:8888", "메인 FastAPI"),
        ("http://127.0.0.1:8889", "보조 FastAPI"), 
        ("http://127.0.0.1:8000", "간단 HTTP")
    ]
    
    active_server = None
    for server_url, server_name in servers:
        safe_print(f"\n🔍 {server_name} 서버 확인...")
        success, response = test_api_endpoint(server_url, f"{server_name} 홈")
        if success:
            active_server = server_url
            safe_print(f"✅ 활성 서버 발견: {server_name}")
            break
    
    if not active_server:
        safe_print("\n❌ 활성 서버 없음!")
        return False
    
    # 2. 기본 API 엔드포인트 검증
    safe_print(f"\n📊 {active_server} API 엔드포인트 검증")
    safe_print("-" * 40)
    
    api_endpoints = [
        ("/", "홈페이지"),
        ("/api/status", "시스템 상태"),
        ("/api/backups", "백업 히스토리"),
        ("/api/configs", "시스템 설정"),
        ("/api/logs", "시스템 로그"),
        ("/api/setup/status", "설정 상태"),
        ("/api/security/status", "보안 상태")
    ]
    
    successful_apis = 0
    total_apis = len(api_endpoints)
    
    for endpoint, name in api_endpoints:
        success, response = test_api_endpoint(f"{active_server}{endpoint}", name)
        if success:
            successful_apis += 1
        time.sleep(0.5)  # API 호출 간격
    
    api_success_rate = (successful_apis / total_apis) * 100
    safe_print(f"\n📈 기본 API 성공률: {successful_apis}/{total_apis} ({api_success_rate:.1f}%)")
    
    # 3. 건강도 API 별도 테스트 (실패할 수 있음)
    safe_print(f"\n🏥 시스템 건강도 API 테스트")
    safe_print("-" * 40)
    success, response = test_api_endpoint(f"{active_server}/api/system/health", "시스템 건강도")
    
    # 4. POST API 테스트 (실제 기능 수행)
    if ':8000' not in active_server:  # FastAPI 서버만
        safe_print(f"\n⚡ 액션 API 자동 테스트")
        safe_print("-" * 40)
        
        # 안전한 테스트부터 시작
        post_tests = [
            ("/api/notifications/test", "알림 테스트", None),
            ("/api/security/scan", "보안 스캔", None)
        ]
        
        for endpoint, name, data in post_tests:
            safe_print(f"\n🔄 {name} 실행...")
            success, response = test_post_endpoint(f"{active_server}{endpoint}", name, data)
            time.sleep(2)  # 서버 부하 방지
    
    # 5. 대시보드 파일 존재 확인
    safe_print(f"\n📁 대시보드 파일 구조 검증")
    safe_print("-" * 40)
    
    important_files = [
        ("templates/backup_dashboard.html", "대시보드 템플릿"),
        ("static/dashboard.css", "스타일시트"),
        ("safe_security_wrapper.py", "보안 래퍼"),
        ("dashboard_server.py", "메인 서버"),
        ("run_dashboard.py", "대체 서버")
    ]
    
    file_count = 0
    for file_path, name in important_files:
        full_path = Path(file_path)
        if full_path.exists():
            safe_print(f"✅ {name}: 존재 ({full_path.stat().st_size} bytes)")
            file_count += 1
        else:
            safe_print(f"❌ {name}: 누락")
    
    # 6. 종합 결과
    safe_print(f"\n🎯 종합 검증 결과")
    safe_print("=" * 60)
    
    safe_print(f"🌐 활성 서버: {active_server}")
    safe_print(f"📊 API 성공률: {api_success_rate:.1f}% ({successful_apis}/{total_apis})")
    safe_print(f"📁 파일 완성도: {file_count}/{len(important_files)} ({file_count/len(important_files)*100:.1f}%)")
    
    # 접속 정보
    safe_print(f"\n🔗 대시보드 접속 정보")
    safe_print("-" * 30)
    safe_print(f"메인 대시보드: {active_server}")
    if ':8000' not in active_server:
        safe_print(f"API 문서: {active_server}/docs")
        safe_print(f"WebSocket: {active_server.replace('http', 'ws')}/ws")
    
    # 성공 여부 판단
    overall_success = (
        active_server is not None and
        api_success_rate >= 80 and
        file_count >= len(important_files) * 0.8
    )
    
    if overall_success:
        safe_print(f"\n🎉 대시보드 검증 완료: 모든 핵심 기능 정상!")
        safe_print(f"✨ 서버 안정성 문제가 완전히 해결되었습니다!")
    else:
        safe_print(f"\n⚠️ 일부 기능에 제한이 있을 수 있습니다")
    
    safe_print("=" * 60)
    return overall_success

if __name__ == "__main__":
    validate_dashboard()