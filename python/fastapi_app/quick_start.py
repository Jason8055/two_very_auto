#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Start Server - 빠른 서버 시작용
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import socket
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(title="Two Very Auto - Quick Start", version="1.0.0")

@app.get("/", response_class=HTMLResponse)
def root():
    """메인 페이지"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Two Very Auto - Quick Start</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center; 
                margin: 50px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 90vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container { 
                background: rgba(255,255,255,0.1); 
                padding: 30px; 
                border-radius: 15px; 
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
                max-width: 600px;
            }
            .btn { 
                background: linear-gradient(45deg, #ff6b6b, #ff8e53); 
                color: white; 
                padding: 12px 24px; 
                text-decoration: none; 
                border-radius: 8px; 
                display: inline-block; 
                margin: 10px; 
                font-weight: bold;
                transition: transform 0.3s;
            }
            .btn:hover { 
                transform: translateY(-2px); 
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            }
            .status {
                background: rgba(76, 175, 80, 0.2);
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                border: 1px solid rgba(76, 175, 80, 0.5);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎰 Two Very Auto</h1>
            <h2>바카라 페어 감지 시스템</h2>
            
            <div class="status">
                <h3>✅ 서버 정상 작동</h3>
                <p>FastAPI Quick Start 서버가 성공적으로 실행되었습니다!</p>
            </div>
            
            <div>
                <h3>🔗 사용 가능한 기능</h3>
                <a href="/health" class="btn">💚 서버 상태</a>
                <a href="/docs" class="btn">📖 API 문서</a>
                <a href="/redoc" class="btn">📋 ReDoc</a>
            </div>
            
            <div style="margin-top: 30px;">
                <h3>🎯 새로운 페어 API</h3>
                <a href="/api/pairs/test" class="btn">🧪 페어 테스트</a>
                <a href="/api/pairs/formatted?limit=10" class="btn">📊 페어 대시보드</a>
            </div>
            
            <p style="margin-top: 30px; opacity: 0.8;">
                서버 시작 성공! 모든 기능이 정상적으로 작동합니다.
            </p>
        </div>
    </body>
    </html>
    """)

@app.get("/health")
def health():
    """헬스 체크"""
    return {
        "status": "healthy",
        "message": "Two Very Auto 서버가 정상 작동 중입니다",
        "version": "1.0.0"
    }

@app.get("/test")
def test():
    """테스트 엔드포인트"""
    return {
        "success": True,
        "message": "서버 테스트 성공!",
        "data": {
            "server": "FastAPI",
            "status": "running",
            "features": ["페어 감지", "실시간 알림", "대시보드"]
        }
    }

def find_available_port():
    """사용 가능한 포트 찾기"""
    preferred_ports = [8080, 8000, 3000, 9999, 7777, 5000]
    
    for port in preferred_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    
    # 임의 포트 사용
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

if __name__ == "__main__":
    # 포트 찾기
    port = find_available_port()
    host = "127.0.0.1"
    
    print(f"")
    print(f"🚀 Two Very Auto 서버 시작!")
    print(f"📍 주소: http://{host}:{port}")
    print(f"🎯 대시보드: http://{host}:{port}/")
    print(f"💚 상태 확인: http://{host}:{port}/health")
    print(f"📖 API 문서: http://{host}:{port}/docs")
    print(f"")
    
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        print(f"❌ 서버 시작 실패: {e}")
        input("엔터키를 눌러 종료하세요...")