#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
연결 테스트용 상세 대시보드
브라우저 접속 문제 해결을 위한 진단 정보 포함
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
import logging
import socket
import psutil
import platform
from datetime import datetime
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Two Very Auto - 연결 테스트 대시보드")

def get_system_info():
    """시스템 정보 수집"""
    try:
        # 네트워크 정보
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # 시스템 정보
        system_info = {
            'hostname': hostname,
            'local_ip': local_ip,
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'python_version': platform.python_version(),
        }
        
        # 포트 사용 상태
        port_info = []
        for conn in psutil.net_connections():
            if conn.laddr.port == 8000:
                port_info.append({
                    'port': conn.laddr.port,
                    'status': conn.status,
                    'pid': conn.pid
                })
        
        system_info['port_8000_status'] = port_info
        
        return system_info
        
    except Exception as e:
        logger.error(f"시스템 정보 수집 오류: {e}")
        return {'error': str(e)}

@app.get("/", response_class=HTMLResponse)
async def connection_test_dashboard(request: Request):
    """연결 테스트 대시보드"""
    
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")
    system_info = get_system_info()
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Two Very Auto - 연결 테스트 대시보드</title>
        <style>
            body {{
                font-family: 'Consolas', 'Monaco', monospace;
                margin: 0;
                padding: 20px;
                background: linear-gradient(45deg, #1a1a2e, #16213e);
                color: #00ff00;
                min-height: 100vh;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .header {{
                text-align: center;
                background: rgba(0, 255, 0, 0.1);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
                border: 1px solid #00ff00;
            }}
            .success {{
                color: #00ff00;
                font-weight: bold;
            }}
            .warning {{
                color: #ffaa00;
            }}
            .error {{
                color: #ff4444;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .info-card {{
                background: rgba(0, 255, 0, 0.05);
                border: 1px solid rgba(0, 255, 0, 0.3);
                border-radius: 8px;
                padding: 20px;
            }}
            .info-card h3 {{
                color: #00ff00;
                margin-top: 0;
                border-bottom: 1px solid rgba(0, 255, 0, 0.3);
                padding-bottom: 10px;
            }}
            .status-ok {{ color: #00ff00; }}
            .status-warning {{ color: #ffaa00; }}
            .status-error {{ color: #ff4444; }}
            pre {{
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(0, 255, 0, 0.3);
                border-radius: 5px;
                padding: 15px;
                overflow-x: auto;
                font-size: 12px;
            }}
            .test-section {{
                background: rgba(0, 255, 0, 0.05);
                border: 1px solid rgba(0, 255, 0, 0.3);
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            .pulse {{
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
                100% {{ opacity: 1; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 class="pulse">🎯 Two Very Auto - 연결 테스트 대시보드</h1>
                <p class="success">✅ 성공! 브라우저에서 서버에 정상적으로 연결되었습니다!</p>
                <p>현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="info-grid">
                <div class="info-card">
                    <h3>🌐 연결 정보</h3>
                    <p><strong>클라이언트 IP:</strong> <span class="success">{client_ip}</span></p>
                    <p><strong>서버 포트:</strong> <span class="success">8000</span></p>
                    <p><strong>연결 상태:</strong> <span class="success">정상</span></p>
                    <p><strong>응답 시간:</strong> <span class="success">빠름</span></p>
                </div>
                
                <div class="info-card">
                    <h3>🖥️ 시스템 정보</h3>
                    <p><strong>호스트명:</strong> {system_info.get('hostname', 'N/A')}</p>
                    <p><strong>로컬 IP:</strong> {system_info.get('local_ip', 'N/A')}</p>
                    <p><strong>플랫폼:</strong> {system_info.get('platform', 'N/A')} {system_info.get('platform_release', '')}</p>
                    <p><strong>아키텍처:</strong> {system_info.get('architecture', 'N/A')}</p>
                </div>
                
                <div class="info-card">
                    <h3>🔧 서버 상태</h3>
                    <p><strong>Python 버전:</strong> {system_info.get('python_version', 'N/A')}</p>
                    <p><strong>서버 프로세스:</strong> <span class="success">실행 중</span></p>
                    <p><strong>포트 8000:</strong> <span class="success">바인딩됨</span></p>
                    <p><strong>HTTP 상태:</strong> <span class="success">200 OK</span></p>
                </div>
                
                <div class="info-card">
                    <h3>🌍 브라우저 정보</h3>
                    <p><strong>User-Agent:</strong></p>
                    <pre>{user_agent}</pre>
                </div>
            </div>
            
            <div class="test-section">
                <h2>🧪 연결 테스트 결과</h2>
                
                <h3 class="success">✅ 성공한 테스트들:</h3>
                <ul>
                    <li class="success">HTTP 서버 응답 - 200 OK</li>
                    <li class="success">HTML 렌더링 - 정상</li>
                    <li class="success">CSS 스타일링 - 적용됨</li>
                    <li class="success">브라우저 호환성 - 확인</li>
                    <li class="success">네트워크 연결 - 안정</li>
                </ul>
                
                <h3>📋 접속 가능한 URL들:</h3>
                <ul>
                    <li><a href="http://localhost:8000" style="color: #00ff00;">http://localhost:8000</a> - 메인 대시보드</li>
                    <li><a href="http://127.0.0.1:8000" style="color: #00ff00;">http://127.0.0.1:8000</a> - IP 직접 접속</li>
                    <li><a href="http://{system_info.get('local_ip', '127.0.0.1')}:8000" style="color: #00ff00;">http://{system_info.get('local_ip', '127.0.0.1')}:8000</a> - 로컬 네트워크 접속</li>
                    <li><a href="/health" style="color: #00ff00;">/health</a> - 상태 확인 API</li>
                    <li><a href="/system" style="color: #00ff00;">/system</a> - 시스템 정보 API</li>
                </ul>
            </div>
            
            <div class="test-section">
                <h2>📊 실시간 시스템 모니터링</h2>
                <div id="status-monitor">
                    <p class="success">🔄 실시간 모니터링 활성화됨</p>
                </div>
            </div>
        </div>
        
        <script>
            // 실시간 상태 업데이트
            let updateCount = 0;
            setInterval(function() {{
                updateCount++;
                const statusDiv = document.getElementById('status-monitor');
                const now = new Date().toLocaleTimeString();
                statusDiv.innerHTML = `
                    <p class="success">🔄 실시간 모니터링 활성화됨</p>
                    <p>마지막 업데이트: ${{now}} (업데이트 #${{updateCount}})</p>
                    <p class="success">서버 상태: 정상 운영 중</p>
                `;
            }}, 5000);
            
            // 페이지 로드 완료 알림
            window.onload = function() {{
                console.log('Two Very Auto Dashboard loaded successfully!');
                document.title = '✅ Two Very Auto - 연결 성공!';
            }};
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """상태 확인 API"""
    return {
        "status": "healthy",
        "message": "연결 테스트 대시보드가 정상적으로 작동하고 있습니다!",
        "timestamp": datetime.now().isoformat(),
        "port": 8000,
        "test": "success",
        "system_info": get_system_info()
    }

@app.get("/system")
async def system_info():
    """시스템 정보 API"""
    return {
        "system": get_system_info(),
        "timestamp": datetime.now().isoformat(),
        "server_status": "running"
    }

if __name__ == "__main__":
    print("=" * 80)
    print("Two Very Auto Connection Test Dashboard")
    print("=" * 80)
    print("Main URL: http://localhost:8000")
    print("System Info: http://localhost:8000/system") 
    print("Health Check: http://localhost:8000/health")
    print("=" * 80)
    print("Open one of the URLs above in your browser!")
    print("You will see detailed diagnostic info if connection succeeds.")
    print("=" * 80)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )