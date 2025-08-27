#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quick test server for port 8000 connection testing
"""

import http.server
import socketserver
import webbrowser
import threading
import time

class QuickHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Two Very Auto - Port 8000 Test</title>
                <meta charset="utf-8">
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        text-align: center; 
                        padding: 50px;
                        background: #f0f0f0;
                    }
                    .success { color: green; font-size: 24px; }
                    .info { background: #e7f3ff; padding: 20px; margin: 20px; border-radius: 5px; }
                </style>
            </head>
            <body>
                <h1 class="success">✅ 연결 성공!</h1>
                <p class="success">8000번 포트 연결이 정상적으로 작동하고 있습니다!</p>
                
                <div class="info">
                    <h3>Connection Test Results</h3>
                    <p><strong>Port:</strong> 8000</p>
                    <p><strong>Status:</strong> Connected</p>
                    <p><strong>Server:</strong> Python HTTP Server</p>
                    <p><strong>Time:</strong> """ + time.strftime('%Y-%m-%d %H:%M:%S') + """</p>
                </div>
                
                <p>이 페이지가 보인다면 8000번 포트 연결 문제가 해결되었습니다!</p>
            </body>
            </html>
            """
            
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path == '/test':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = '{"status": "success", "port": 8000, "message": "Connection test successful!"}'
            self.wfile.write(response.encode('utf-8'))
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")

def start_server():
    try:
        PORT = 8000
        print("=" * 60)
        print("Two Very Auto - Quick Test Server")
        print("=" * 60)
        print(f"Starting server on port {PORT}...")
        
        with socketserver.TCPServer(("", PORT), QuickHandler) as httpd:
            print(f"✅ Server running on http://localhost:{PORT}")
            print(f"✅ Test URL: http://localhost:{PORT}/test")
            print("=" * 60)
            print("브라우저에서 http://localhost:8000 을 열어보세요!")
            print("Ctrl+C to stop the server")
            print("=" * 60)
            
            # 자동으로 브라우저 열기 (선택사항)
            def open_browser():
                time.sleep(2)
                try:
                    webbrowser.open(f'http://localhost:{PORT}')
                    print("브라우저를 자동으로 열었습니다.")
                except:
                    print("브라우저를 자동으로 열 수 없습니다. 수동으로 URL을 열어주세요.")
            
            browser_thread = threading.Thread(target=open_browser, daemon=True)
            browser_thread.start()
            
            httpd.serve_forever()
            
    except OSError as e:
        if e.errno == 10048:  # Address already in use
            print(f"❌ Error: Port {PORT} is already in use!")
            print("다른 프로세스가 8000번 포트를 사용하고 있습니다.")
            print("실행 중인 다른 서버를 종료하고 다시 시도해주세요.")
        else:
            print(f"❌ Server error: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")

if __name__ == "__main__":
    start_server()