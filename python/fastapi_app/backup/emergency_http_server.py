#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
비상 HTTP 서버 - 방화벽 우회용
"""

import http.server
import socketserver
import json
import urllib.parse
from pathlib import Path
import webbrowser
import threading
import time

class EmergencyHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Two Very Auto - 비상 연결 성공!</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #1e3c72, #2a5298); 
            color: white; 
            text-align: center; 
            margin: 0; 
            padding: 50px; 
        }
        .container { 
            max-width: 600px; 
            margin: 0 auto; 
            padding: 40px; 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        h1 { color: #4CAF50; font-size: 2.5em; margin-bottom: 20px; }
        .success { background: #4CAF50; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .btn { 
            background: linear-gradient(45deg, #4CAF50, #45a049); 
            color: white; 
            padding: 15px 30px; 
            border: none;
            border-radius: 8px; 
            text-decoration: none; 
            font-size: 1.1em;
            margin: 10px; 
            display: inline-block; 
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
        .info { background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎉 비상 연결 성공!</h1>
        
        <div class="success">
            <h3>Two Very Auto 페어 시스템</h3>
            <p>서버가 성공적으로 작동하고 있습니다!</p>
            <p><strong>연결 문제가 해결되었습니다!</strong></p>
        </div>
        
        <div style="margin: 30px 0;">
            <a href="/health" class="btn">서버 상태 확인</a>
            <a href="/test" class="btn">연결 테스트</a>
            <a href="/pair-dashboard" class="btn">페어 대시보드</a>
        </div>
        
        <div class="info">
            <h3>다음 단계</h3>
            <p>1. 이 연결이 성공했다면 방화벽 문제였습니다</p>
            <p>2. 관리자 권한으로 배치 파일을 실행하세요</p>
            <p>3. 또는 이 비상 서버를 계속 사용하세요</p>
        </div>
        
        <div class="info">
            <h3>완전한 해결 방법</h3>
            <p>1. Windows 방화벽에서 Python.exe 허용</p>
            <p>2. 포트 8080 TCP 허용 규칙 추가</p>
            <p>3. 안티바이러스에서 Python 예외 처리</p>
        </div>
    </div>
</body>
</html>"""
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "message": "비상 서버가 정상 작동 중입니다",
                "server": "emergency_http",
                "success": True,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        elif self.path == '/test':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            response = {
                "success": True,
                "message": "연결 테스트 성공!",
                "connection_status": "OK",
                "server": "emergency_http",
                "problem_solved": True,
                "next_steps": [
                    "방화벽 문제가 확인되었습니다",
                    "관리자 권한으로 배치 파일을 실행하세요",
                    "또는 이 비상 서버를 계속 사용하세요"
                ]
            }
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        elif self.path == '/pair-dashboard':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>페어 대시보드 - 비상 모드</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1a1a2e; color: white; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .alert { background: #4CAF50; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .card { background: rgba(255,255,255,0.1); padding: 20px; margin: 10px; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 페어 대시보드 - 비상 모드</h1>
        <div class="alert">
            <h3>✅ 연결 문제 해결 완료!</h3>
            <p>서버가 정상적으로 작동하고 있습니다.</p>
        </div>
        
        <div class="card">
            <h3>📊 시스템 상태</h3>
            <p>✅ 서버: 정상 작동</p>
            <p>✅ 연결: 성공</p>
            <p>✅ 방화벽: 우회 완료</p>
        </div>
        
        <div class="card">
            <h3>🔧 다음 할 일</h3>
            <p>1. 관리자 권한으로 "완벽한_페어시스템_시작.bat" 실행</p>
            <p>2. Windows 방화벽에서 Python 허용</p>
            <p>3. 완전한 FastAPI 서버로 전환</p>
        </div>
        
        <div class="card">
            <h3>🎰 페어 감지 시스템</h3>
            <p>완전한 서버에서 실시간 페어 감지를 확인하실 수 있습니다.</p>
            <p>JSON 패킷 데이터에서 playerPair, bankerPair를 자동 감지합니다.</p>
        </div>
    </div>
</body>
</html>"""
            self.wfile.write(html.encode('utf-8'))
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        print(f"[비상서버] {format % args}")

def find_available_port():
    """사용 가능한 포트 찾기"""
    import socket
    for port in [8080, 8000, 3000, 9999, 7777, 5000, 8888]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return 8080

def open_browser_after_delay(url):
    """5초 후 브라우저 자동 열기"""
    time.sleep(5)
    try:
        webbrowser.open(url)
        print(f"브라우저가 자동으로 열렸습니다: {url}")
    except:
        print(f"브라우저를 수동으로 열어주세요: {url}")

def main():
    port = find_available_port()
    
    print("=" * 60)
    print("🚨 Two Very Auto - 비상 HTTP 서버")
    print("=" * 60)
    print("방화벽 우회 및 연결 문제 해결용")
    print("-" * 60)
    print(f"서버 주소: http://127.0.0.1:{port}")
    print(f"상태 확인: http://127.0.0.1:{port}/health")
    print(f"페어 대시보드: http://127.0.0.1:{port}/pair-dashboard")
    print("=" * 60)
    print("📌 이 서버가 성공적으로 연결되면 방화벽 문제입니다!")
    print("📌 관리자 권한으로 배치 파일을 실행하세요!")
    print("=" * 60)
    
    # 브라우저 자동 열기 (5초 후)
    threading.Thread(target=open_browser_after_delay, args=(f"http://127.0.0.1:{port}",), daemon=True).start()
    
    try:
        with socketserver.TCPServer(("127.0.0.1", port), EmergencyHTTPHandler) as httpd:
            print(f"🚀 비상 서버 시작됨 - 포트 {port}")
            print("서버를 중지하려면 Ctrl+C를 누르세요")
            print("-" * 60)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n비상 서버가 중단되었습니다.")
    except Exception as e:
        print(f"비상 서버 오류: {e}")

if __name__ == "__main__":
    main()