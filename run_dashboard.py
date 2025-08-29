#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
대시보드 서버 실행기
포트 자동 탐지 및 실행
"""

import socket
import sys
from pathlib import Path

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

def find_free_port(start_port=8888):
    """사용 가능한 포트 찾기"""
    for port in range(start_port, start_port + 10):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return None

def run_simple_server():
    """간단한 HTTP 서버 실행"""
    import http.server
    import socketserver
    from threading import Thread
    import webbrowser
    import time
    
    # 사용 가능한 포트 찾기
    port = find_free_port(8000)
    if not port:
        safe_print("❌ 사용 가능한 포트를 찾을 수 없습니다")
        return
    
    # HTML 콘텐츠 생성
    html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Two Very Auto - 백업 시스템 대시보드</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 0; padding: 40px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container { 
            max-width: 1000px; margin: 0 auto; 
            background: white; padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
        }
        .header { 
            text-align: center; margin-bottom: 40px;
            background: linear-gradient(135deg, #2c3e50, #3498db);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .header h1 { font-size: 3em; margin: 0; }
        .header p { font-size: 1.3em; margin: 10px 0; color: #666; }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .status-card {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 15px;
            padding: 25px;
            border-left: 5px solid #3498db;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .status-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        .card-title { 
            font-size: 1.3em; font-weight: 600; 
            color: #2c3e50; margin-bottom: 15px; 
        }
        .metric-value { 
            font-size: 2.5em; font-weight: 700; 
            color: #27ae60; margin-bottom: 10px; 
        }
        .metric-label { font-size: 1em; color: #7f8c8d; }
        
        .actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 40px 0;
        }
        .btn {
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            border: none;
            padding: 15px 25px;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            text-align: center;
            display: inline-block;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(52, 152, 219, 0.4);
        }
        .btn.success { background: linear-gradient(135deg, #27ae60, #229954); }
        .btn.warning { background: linear-gradient(135deg, #f39c12, #e67e22); }
        .btn.danger { background: linear-gradient(135deg, #e74c3c, #c0392b); }
        
        .info-panel {
            background: linear-gradient(135deg, #e8f8f5, #d5f4e6);
            border-radius: 15px;
            padding: 25px;
            margin: 30px 0;
            border-left: 5px solid #27ae60;
        }
        .info-panel h3 { margin-top: 0; color: #27ae60; }
        
        @media (max-width: 768px) {
            body { padding: 20px; }
            .container { padding: 20px; }
            .header h1 { font-size: 2em; }
            .status-grid { grid-template-columns: 1fr; }
            .actions { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎰 Two Very Auto</h1>
            <p>엔터프라이즈급 백업 시스템 관리 대시보드</p>
        </div>
        
        <div class="status-grid">
            <div class="status-card">
                <div class="card-title">💾 백업 시스템</div>
                <div class="metric-value">READY</div>
                <div class="metric-label">백업 시스템 준비 완료</div>
            </div>
            
            <div class="status-card">
                <div class="card-title">🔐 보안 상태</div>
                <div class="metric-value">ACTIVE</div>
                <div class="metric-label">보안 시스템 활성화</div>
            </div>
            
            <div class="status-card">
                <div class="card-title">📊 모니터링</div>
                <div class="metric-value">ON</div>
                <div class="metric-label">실시간 모니터링 중</div>
            </div>
            
            <div class="status-card">
                <div class="card-title">🌐 서버 상태</div>
                <div class="metric-value">ONLINE</div>
                <div class="metric-label">서버 정상 운영</div>
            </div>
        </div>
        
        <div class="actions">
            <button class="btn" onclick="alert('백업을 시작합니다!')">💾 백업 실행</button>
            <button class="btn success" onclick="alert('건전성 점검을 시작합니다!')">🏥 건전성 점검</button>
            <button class="btn warning" onclick="alert('테스트 알림을 전송합니다!')">📢 알림 테스트</button>
            <button class="btn" onclick="location.reload()">🔄 새로고침</button>
        </div>
        
        <div class="info-panel">
            <h3>✅ 서버 정상 작동 중</h3>
            <p><strong>접속 주소:</strong> http://127.0.0.1:""" + str(port) + """</p>
            <p><strong>실행 시간:</strong> <span id="runtime">0</span>초</p>
            <p><strong>상태:</strong> Two Very Auto 백업 시스템이 성공적으로 실행되었습니다!</p>
            
            <h4>📋 주요 기능</h4>
            <ul>
                <li>🔄 자동 백업 시스템 (AWS S3, Google Cloud, Azure 지원)</li>
                <li>🏥 백업 건전성 자동 점검</li>
                <li>📢 다채널 알림 시스템 (이메일, Slack, Discord, Teams)</li>
                <li>🔍 실시간 시스템 모니터링</li>
                <li>🔐 SSL 인증서 관리 및 보안 점검</li>
                <li>📊 대시보드 기반 관리 인터페이스</li>
            </ul>
            
            <h4>🚀 다음 단계</h4>
            <ol>
                <li>클라우드 인증 설정: <code>python cloud_auth_setup.py</code></li>
                <li>알림 시스템 설정: <code>python notification_system.py</code></li>
                <li>통합 모니터링 시작: <code>python integrated_monitoring.py --start</code></li>
                <li>전체 대시보드 실행: <code>python dashboard_server.py</code></li>
            </ol>
        </div>
    </div>
    
    <script>
        let startTime = Date.now();
        setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            document.getElementById('runtime').textContent = elapsed;
        }, 1000);
        
        // 환영 메시지
        setTimeout(() => {
            console.log('🎰 Two Very Auto 백업 시스템 대시보드에 오신 것을 환영합니다!');
            console.log('📊 시스템이 정상적으로 작동하고 있습니다.');
        }, 1000);
    </script>
</body>
</html>"""
    
    # HTML 파일 생성
    index_file = Path("index.html")
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # HTTP 서버 시작
    class MyHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.path = '/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
    
    httpd = socketserver.TCPServer(("", port), MyHandler)
    
    safe_print(f"🚀 Two Very Auto 백업 대시보드 서버 시작")
    safe_print(f"🌐 접속 주소: http://127.0.0.1:{port}")
    safe_print(f"📁 작업 디렉토리: {Path.cwd()}")
    safe_print("=" * 50)
    
    # 브라우저 자동 열기 (별도 스레드)
    def open_browser():
        time.sleep(2)
        try:
            webbrowser.open(f'http://127.0.0.1:{port}')
            safe_print("🌐 브라우저에서 대시보드를 열었습니다")
        except:
            safe_print("⚠️ 브라우저 자동 열기 실패, 수동으로 접속해주세요")
    
    Thread(target=open_browser).start()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        safe_print("\n⏹️ 서버를 종료합니다")
        httpd.shutdown()
        
        # HTML 파일 정리
        if index_file.exists():
            index_file.unlink()

if __name__ == "__main__":
    safe_print("🎰 Two Very Auto 백업 시스템 대시보드")
    safe_print("=" * 50)
    
    run_simple_server()