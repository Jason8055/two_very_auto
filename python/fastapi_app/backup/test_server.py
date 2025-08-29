#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 테스트 서버 - 연결 문제 해결용
"""

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import socket
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(title="Test Server", version="1.0.0")

@app.get("/")
async def root():
    """메인 페이지"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>Two Very Auto - Test Server</title>
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
            .btn { 
                background: #4CAF50; 
                color: white; 
                padding: 10px 20px; 
                text-decoration: none; 
                border-radius: 5px; 
                margin: 10px; 
                display: inline-block; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Two Very Auto - Test Server</h1>
            <p>서버가 정상적으로 작동하고 있습니다!</p>
            <div>
                <a href="/health" class="btn">상태 확인</a>
                <a href="/test" class="btn">테스트</a>
                <a href="/pair-dashboard" class="btn">페어 대시보드</a>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """상태 확인"""
    return JSONResponse({
        "status": "healthy",
        "message": "테스트 서버가 정상적으로 작동 중입니다",
        "server": "test_server",
        "version": "1.0.0"
    })

@app.get("/test")
async def test():
    """테스트 엔드포인트"""
    return JSONResponse({
        "success": True,
        "message": "테스트 성공!",
        "data": {
            "test1": "OK",
            "test2": "OK",
            "connection": "SUCCESS"
        }
    })

@app.get("/pair-dashboard")
async def pair_dashboard():
    """페어 대시보드"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>페어 대시보드 - 테스트</title>
        <style>
            body { font-family: Arial, sans-serif; background: #1a1a2e; color: white; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: rgba(255,255,255,0.1); padding: 20px; margin: 10px; border-radius: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>페어 대시보드 - 테스트 모드</h1>
            <div class="card">
                <h3>연결 테스트 성공!</h3>
                <p>서버가 정상적으로 작동하고 있습니다.</p>
                <p>이제 메인 서버로 전환할 수 있습니다.</p>
            </div>
            <div class="card">
                <h3>다음 단계</h3>
                <p>1. main.py 서버 시작</p>
                <p>2. 페어 감지 시스템 테스트</p>
                <p>3. 실제 패킷 데이터 확인</p>
            </div>
        </div>
    </body>
    </html>
    """)

def find_available_port():
    """사용 가능한 포트 찾기"""
    preferred_ports = [8080, 8000, 3000, 9999, 7777, 5000]
    
    for port in preferred_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                logger.info(f"포트 {port} 사용 가능")
                return port
        except OSError:
            logger.info(f"포트 {port} 사용 중")
            continue
    
    return None

if __name__ == "__main__":
    print("Two Very Auto - 테스트 서버")
    print("=" * 40)
    
    # 포트 찾기
    port = find_available_port()
    if not port:
        print("ERROR: 사용 가능한 포트를 찾을 수 없습니다.")
        exit(1)
    
    print(f"테스트 서버 시작: http://127.0.0.1:{port}")
    print("=" * 40)
    
    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            reload=False,
            access_log=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n테스트 서버가 중단되었습니다.")
    except Exception as e:
        print(f"\n테스트 서버 오류: {e}")