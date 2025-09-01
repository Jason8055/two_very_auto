#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 서버 테스트 스크립트
"""

import uvicorn
from main import app
import requests
import time

def test_routes():
    # 서버 시작 후 잠시 대기
    time.sleep(2)
    
    base_url = "http://127.0.0.1:8095"
    
    # 테스트할 라우트들
    routes_to_test = [
        "/",
        "/health", 
        "/comprehensive-dashboard",
        "/main-dashboard",
        "/room-details"
    ]
    
    for route in routes_to_test:
        try:
            response = requests.get(f"{base_url}{route}", timeout=5)
            print(f"Route {route}: Status {response.status_code}")
        except Exception as e:
            print(f"Route {route}: Error - {e}")

if __name__ == "__main__":
    print("Starting FastAPI server on port 8095...")
    
    # 서버 시작
    try:
        uvicorn.run(app, host="127.0.0.1", port=8095, log_level="info")
    except KeyboardInterrupt:
        print("Server stopped")