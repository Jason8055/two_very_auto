#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최소한의 테스트 서버 - 바인딩 문제 해결용
"""

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
import socket
import time

app = FastAPI(title="Minimal Test Server")

@app.get("/")
async def root():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Two Very Auto - 연결 테스트 성공!</title>
        <meta charset="utf-8">
    </head>
    <body style="font-family: Arial; text-align: center; margin: 50px; background: #1a1a2e; color: white;">
        <h1>🎉 연결 성공!</h1>
        <p>Two Very Auto 서버가 정상적으로 작동하고 있습니다.</p>
        <div style="margin: 30px;">
            <a href="/health" style="background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px;">상태 확인</a>
            <a href="/test" style="background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px;">테스트</a>
        </div>
    </body>
    </html>
    """)

@app.get("/health")
async def health():
    return JSONResponse({
        "status": "healthy",
        "message": "서버가 정상 작동 중입니다",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.get("/test")
async def test():
    return JSONResponse({
        "success": True,
        "message": "테스트 성공!",
        "connection": "OK",
        "server": "minimal_test"
    })

def find_available_port():
    """사용 가능한 포트 찾기"""
    for port in [8080, 8000, 3000, 9999, 7777, 5000]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # 모든 인터페이스에 바인딩 시도
                s.bind(('0.0.0.0', port))
                print(f"포트 {port} 사용 가능")
                return port
        except OSError:
            print(f"포트 {port} 사용 중")
            continue
    return None

if __name__ == "__main__":
    print("=" * 50)
    print("Minimal Test Server - 바인딩 문제 해결")
    print("=" * 50)
    
    port = find_available_port()
    if not port:
        print("ERROR: 사용 가능한 포트 없음")
        exit(1)
    
    print(f"서버 시작: http://127.0.0.1:{port}")
    print(f"외부 접속: http://0.0.0.0:{port}")
    print("=" * 50)
    
    try:
        # 0.0.0.0으로 모든 인터페이스에 바인딩
        uvicorn.run(
            app,
            host="0.0.0.0",  # 모든 인터페이스에 바인딩
            port=port,
            reload=False,
            access_log=True,
            log_level="info"
        )
    except Exception as e:
        print(f"서버 시작 실패: {e}")
        print("대안: 127.0.0.1로 바인딩 시도")
        try:
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=port,
                reload=False,
                access_log=True,
                log_level="info"
            )
        except Exception as e2:
            print(f"127.0.0.1 바인딩도 실패: {e2}")
            print("수동 해결 필요")