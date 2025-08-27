#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 서버 실행 스크립트
"""

import sys
import asyncio
import logging
from pathlib import Path

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

try:
    import uvicorn
    from main import app
except ImportError as e:
    print(f"❌ 필수 패키지가 설치되지 않았습니다: {e}")
    print("다음 명령으로 설치하세요:")
    print("pip install -r requirements.txt")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("Two Very Auto - FastAPI Server Starting")
    print("=" * 70)
    print("+ AsyncIO Native Support - Conflict Resolution")
    print("+ Real-time WebSocket Communication")
    print("+ Automatic API Documentation")
    print("+ Type Safety Guaranteed")
    print("+ High-Performance Async Processing")
    print("+ Background Task Support")
    print("=" * 70)
    print("Main URL: http://127.0.0.1:8002")
    print("API Docs: http://127.0.0.1:8002/docs")
    print("ReDoc: http://127.0.0.1:8002/redoc")
    print("Health Check: http://127.0.0.1:8002/health")
    print("WebSocket: ws://127.0.0.1:8002/ws/realtime")
    print("=" * 70)
    print("Main API Endpoints:")
    print("  POST /api/demo - Generate demo data")
    print("  GET /api/stats - Get system statistics")
    print("  GET /api/stats/real-data - Get real data")
    print("  GET /api/stats/compare - Compare real vs demo")
    print("  WebSocket /ws/realtime - Real-time data stream")
    print("  WebSocket /ws/dashboard - Dashboard connection")
    print("=" * 70)
    
    try:
        # FastAPI 서버 실행
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8002,  # 포트 충돌 방지
            reload=False,  # 안정성을 위해 비활성화
            access_log=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        print(f"Server startup error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()