#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
단순한 대시보드 테스트 서버
8000번 포트 접속 문제 해결용
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Two Very Auto - 테스트 대시보드")

@app.get("/", response_class=HTMLResponse)
async def test_dashboard():
    """테스트 대시보드 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Two Very Auto - 테스트 대시보드</title>
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #1e3c72, #2a5298);
                color: white;
                min-height: 100vh;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                text-align: center;
            }
            .header {
                background: rgba(255, 255, 255, 0.1);
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
                backdrop-filter: blur(10px);
            }
            .status-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .status-card {
                background: rgba(255, 255, 255, 0.15);
                padding: 20px;
                border-radius: 10px;
                backdrop-filter: blur(5px);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .status-ok {
                border-left: 5px solid #28a745;
            }
            .status-error {
                border-left: 5px solid #dc3545;
            }
            .btn {
                display: inline-block;
                padding: 12px 24px;
                margin: 10px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                transition: all 0.3s ease;
            }
            .btn:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }
            h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎰 Two Very Auto</h1>
                <p>바카라 페어 추적 시스템 - 통합 대시보드</p>
                <p><strong>상태:</strong> ✅ 테스트 대시보드 실행 중</p>
            </div>
            
            <div class="status-grid">
                <div class="status-card status-ok">
                    <h3>🌐 웹서버</h3>
                    <p>포트: 8000</p>
                    <p>상태: 정상</p>
                </div>
                
                <div class="status-card status-error">
                    <h3>🔧 API 서버</h3>
                    <p>포트: 8001</p>
                    <p>상태: 연결 대기</p>
                </div>
                
                <div class="status-card status-ok">
                    <h3>📊 데이터베이스</h3>
                    <p>SQLite</p>
                    <p>상태: 준비됨</p>
                </div>
                
                <div class="status-card status-error">
                    <h3>🤖 AI 시스템</h3>
                    <p>예측 엔진</p>
                    <p>상태: 비활성화</p>
                </div>
            </div>
            
            <div style="margin-top: 40px;">
                <a href="/health" class="btn">💚 상태 확인</a>
                <a href="/test" class="btn">🧪 연결 테스트</a>
            </div>
            
            <div style="margin-top: 30px; font-size: 0.9em; opacity: 0.8;">
                <p>🕐 서버 시작 시각: {current_time}</p>
                <p>연결이 성공하면 이 페이지가 표시됩니다!</p>
            </div>
        </div>
        
        <script>
            // 간단한 상태 업데이트
            setInterval(() => {
                document.querySelector('title').innerHTML += '.';
                if (document.querySelector('title').innerHTML.includes('......')) {
                    document.querySelector('title').innerHTML = 'Two Very Auto - 테스트 대시보드';
                }
            }, 2000);
        </script>
    </body>
    </html>
    """.replace('{current_time}', 'Test Server Running')
    
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """상태 확인"""
    return {
        "status": "healthy",
        "message": "테스트 대시보드가 정상적으로 작동하고 있습니다!",
        "port": 8000,
        "test": "success"
    }

@app.get("/test")
async def connection_test():
    """연결 테스트"""
    return {
        "connection": "success",
        "message": "8000번 포트 연결이 정상입니다!",
        "dashboard": "accessible"
    }

if __name__ == "__main__":
    print("=" * 60)
    print("Two Very Auto 테스트 대시보드 시작")
    print("=" * 60)
    print("URL: http://localhost:8000")
    print("상태 확인: http://localhost:8000/health")
    print("연결 테스트: http://localhost:8000/test")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )