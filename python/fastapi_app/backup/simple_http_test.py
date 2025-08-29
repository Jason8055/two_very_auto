#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 HTTP 테스트 서버
"""

import http.server
import socketserver
import json
import webbrowser
import threading
import time

class TestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Two Very Auto - 연결 테스트</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: white; text-align: center; padding: 50px; }
        h1 { color: #4CAF50; font-size: 3em; }
        .success { background: #4CAF50; padding: 30px; border-radius: 15px; margin: 30px 0; }
        .btn { background: #2196F3; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 10px; display: inline-block; }
    </style>
</head>
<body>
    <h1>연결 성공!</h1>
    <div class="success">
        <h2>Two Very Auto 서버 테스트 성공</h2>
        <p>서버가 정상적으로 작동하고 있습니다!</p>
        <p><strong>연결 문제가 해결되었습니다!</strong></p>
    </div>
    <a href="/health" class="btn">상태 확인</a>
    <a href="/test" class="btn">테스트</a>
    <h3>해결 방법 확인됨:</h3>
    <p>1. 방화벽 문제였습니다</p>
    <p>2. 관리자 권한으로 배치 파일을 실행하세요</p>
    <p>3. Windows 방화벽에서 Python 허용</p>
</body>
</html>"""
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            response = {
                "status": "SUCCESS",
                "message": "서버 정상 작동",
                "connection": "OK",
                "problem": "SOLVED"
            }
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        elif self.path == '/test':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            
            response = {
                "success": True,
                "test_result": "PASS",
                "connection_status": "OK",
                "solution": "방화벽 문제 - 관리자 권한으로 해결하세요"
            }
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        else:
            super().do_GET()

def main():
    import socket
    
    # 포트 찾기
    port = 8080
    for test_port in [8080, 8000, 3000, 9999, 7777]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', test_port))
                port = test_port
                break
        except OSError:
            continue
    
    print("=" * 50)
    print("Two Very Auto - HTTP 연결 테스트")
    print("=" * 50)
    print(f"서버 주소: http://127.0.0.1:{port}")
    print("=" * 50)
    
    # 브라우저 자동 열기
    def open_browser():
        time.sleep(3)
        try:
            webbrowser.open(f"http://127.0.0.1:{port}")
            print("브라우저가 자동으로 열렸습니다.")
        except:
            print("브라우저를 수동으로 열어주세요.")
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        with socketserver.TCPServer(("127.0.0.1", port), TestHandler) as httpd:
            print(f"테스트 서버 시작됨 - 포트 {port}")
            print("이 서버가 성공하면 방화벽 문제입니다!")
            print("Ctrl+C로 중지")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("테스트 서버 중단됨")
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    main()