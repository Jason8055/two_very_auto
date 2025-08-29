#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
대시보드 서버 테스트 및 검증 도구
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

def test_api_endpoint(url, name):
    """API 엔드포인트 테스트"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            safe_print(f"✅ {name}: 정상 응답 ({response.status_code})")
            try:
                data = response.json()
                if isinstance(data, dict):
                    safe_print(f"   📊 데이터 키: {list(data.keys())[:5]}")
            except:
                safe_print(f"   📄 HTML 페이지 (길이: {len(response.text)} chars)")
            return True
        else:
            safe_print(f"⚠️ {name}: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        safe_print(f"❌ {name}: 연결 실패 - 서버가 실행 중인지 확인하세요")
        return False
    except Exception as e:
        safe_print(f"❌ {name}: 오류 - {e}")
        return False

def test_post_endpoint(url, name, data=None):
    """POST API 엔드포인트 테스트"""
    try:
        response = requests.post(url, json=data, timeout=15)
        if response.status_code == 200:
            safe_print(f"✅ {name}: 정상 응답 ({response.status_code})")
            try:
                result = response.json()
                if result.get('success'):
                    safe_print(f"   🎯 작업 성공: {result.get('message', 'N/A')}")
                else:
                    safe_print(f"   ⚠️ 작업 실패: {result.get('error', 'N/A')}")
            except:
                pass
            return True
        else:
            safe_print(f"⚠️ {name}: HTTP {response.status_code}")
            return False
    except Exception as e:
        safe_print(f"❌ {name}: 오류 - {e}")
        return False

def comprehensive_dashboard_test():
    """종합 대시보드 테스트"""
    safe_print("🎰 Two Very Auto 대시보드 종합 검증 시작")
    safe_print("=" * 60)
    
    # 기본 서버들 확인
    servers_to_test = [
        ("http://127.0.0.1:8888", "메인 FastAPI 서버"),
        ("http://127.0.0.1:8889", "대체 FastAPI 서버"), 
        ("http://127.0.0.1:8000", "간단 HTTP 서버")
    ]
    
    active_server = None
    for server_url, server_name in servers_to_test:
        safe_print(f"\n📡 {server_name} 연결 테스트...")
        if test_api_endpoint(server_url, f"{server_name} 홈페이지"):
            active_server = server_url
            break
    
    if not active_server:
        safe_print("\n❌ 활성화된 서버를 찾을 수 없습니다!")
        safe_print("서버를 먼저 시작해주세요:")
        safe_print("  python dashboard_server.py")
        safe_print("  또는")
        safe_print("  python run_dashboard.py")
        return False
    
    safe_print(f"\n🎯 활성 서버: {active_server}")
    safe_print("=" * 60)
    
    # API 엔드포인트 테스트 (FastAPI 서버인 경우만)
    if ':8000' not in active_server:
        safe_print("\n📊 API 엔드포인트 테스트...")
        
        api_tests = [
            ("/api/status", "시스템 상태"),
            ("/api/backups", "백업 히스토리"),
            ("/api/configs", "시스템 설정"),
            ("/api/logs", "시스템 로그"),
            ("/api/system/health", "시스템 건강도"),
            ("/api/setup/status", "설정 상태"),
            ("/api/security/status", "보안 상태")
        ]
        
        success_count = 0
        for endpoint, name in api_tests:
            if test_api_endpoint(f"{active_server}{endpoint}", name):
                success_count += 1
        
        safe_print(f"\n📈 API 성공률: {success_count}/{len(api_tests)} ({success_count/len(api_tests)*100:.1f}%)")
        
        # POST 엔드포인트 테스트 (주의: 실제 작업을 수행함)
        safe_print("\n⚡ 액션 API 테스트...")
        if input("실제 백업/테스트를 수행하시겠습니까? (y/n): ").lower() == 'y':
            post_tests = [
                ("/api/notifications/test", "알림 테스트"),
                ("/api/security/scan", "보안 스캔"),
                ("/api/backup/run", "백업 실행")
            ]
            
            for endpoint, name in post_tests:
                safe_print(f"\n🔄 {name} 실행 중...")
                test_post_endpoint(f"{active_server}{endpoint}", name)
                time.sleep(2)  # 서버 부하 방지
    else:
        safe_print("\n📄 HTML 대시보드 서버 - API 테스트는 FastAPI 서버에서만 가능합니다")
    
    # WebSocket 연결 테스트 (FastAPI만)
    if ':8000' not in active_server:
        safe_print("\n🔗 WebSocket 연결 테스트...")
        try:
            import websocket
            ws_url = active_server.replace('http', 'ws') + '/ws'
            safe_print(f"WebSocket URL: {ws_url}")
            
            def on_open(ws):
                safe_print("✅ WebSocket 연결 성공")
                ws.send("ping")
            
            def on_message(ws, message):
                safe_print(f"📨 WebSocket 메시지: {message}")
                ws.close()
            
            def on_error(ws, error):
                safe_print(f"❌ WebSocket 오류: {error}")
            
            ws = websocket.WebSocketApp(ws_url, 
                                      on_open=on_open,
                                      on_message=on_message, 
                                      on_error=on_error)
            ws.run_forever(timeout=5)
            
        except ImportError:
            safe_print("⚠️ WebSocket 테스트를 위해 'pip install websocket-client' 필요")
        except Exception as e:
            safe_print(f"⚠️ WebSocket 테스트 실패: {e}")
    
    safe_print("\n" + "=" * 60)
    safe_print("🎯 대시보드 검증 완료!")
    safe_print(f"🌐 대시보드 접속: {active_server}")
    if ':8000' not in active_server:
        safe_print(f"📚 API 문서: {active_server}/docs")
    safe_print("=" * 60)
    
    return True

def quick_health_check():
    """빠른 상태 확인"""
    safe_print("🏥 빠른 상태 확인...")
    
    servers = [
        "http://127.0.0.1:8888",
        "http://127.0.0.1:8889", 
        "http://127.0.0.1:8000"
    ]
    
    for server in servers:
        try:
            response = requests.get(server, timeout=3)
            if response.status_code == 200:
                safe_print(f"✅ 서버 활성: {server}")
                return server
        except:
            continue
    
    safe_print("❌ 활성 서버 없음")
    return None

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        active = quick_health_check()
        if active:
            safe_print(f"대시보드 접속: {active}")
    else:
        comprehensive_dashboard_test()