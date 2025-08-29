#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
매우 간단한 HTTP 서버 - 연결 테스트용
"""

import http.server
import socketserver
import socket
import webbrowser
import threading
import time

def find_available_port():
    """사용 가능한 포트 찾기"""
    for port in [8080, 8000, 3000, 9999, 7777, 5000, 8888, 7000]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                print(f"SUCCESS: 포트 {port} 사용 가능")
                return port
        except OSError:
            print(f"WARNING: 포트 {port} 사용 중")
            continue
    return None

class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html lang="ko">
            <head>
                <meta charset="UTF-8">
                <title>Two Very Auto - Simple Test</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        text-align: center; 
                        margin: 50px; 
                        background: #1a1a2e; 
                        color: white; 
                    }
                    .container { 
                        max-width: 600px; 
                        margin: 0 auto; 
                        padding: 30px; 
                        background: rgba(255,255,255,0.1); 
                        border-radius: 15px; 
                    }
                    .success { color: #4CAF50; font-size: 1.2em; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Two Very Auto - Simple Test Server</h1>
                    <div class="success">✅ 연결 성공!</div>
                    <p>서버가 정상적으로 작동하고 있습니다.</p>
                    <p>이제 FastAPI 서버를 시작할 수 있습니다.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/test':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = '{"status": "success", "message": "테스트 성공!", "server": "simple_http"}'
            self.wfile.write(response.encode('utf-8'))
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

def main():
    print("Two Very Auto - Simple Test Server")
    print("=" * 50)
    
    # 포트 찾기
    port = find_available_port()
    if not port:
        print("ERROR: 사용 가능한 포트를 찾을 수 없습니다.")
        return False
    
    try:
        # HTTP 서버 시작
        with socketserver.TCPServer(("127.0.0.1", port), SimpleHTTPRequestHandler) as httpd:
            print(f"SUCCESS: 서버 시작됨 - http://127.0.0.1:{port}")
            print("=" * 50)
            
            # 브라우저 자동 열기 (3초 후)
            def open_browser():
                time.sleep(3)
                try:
                    webbrowser.open(f'http://127.0.0.1:{port}')
                    print("브라우저가 자동으로 열렸습니다.")
                except:
                    print("브라우저를 수동으로 열어주세요.")
            
            threading.Thread(target=open_browser, daemon=True).start()
            
            print("서버를 중지하려면 Ctrl+C를 누르세요.")
            print("=" * 50)
            
            # 서버 실행
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n서버가 중단되었습니다.")
        return True
    except Exception as e:
        print(f"ERROR: 서버 오류: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("SUCCESS: 테스트 완료")
    else:
        print("ERROR: 테스트 실패")