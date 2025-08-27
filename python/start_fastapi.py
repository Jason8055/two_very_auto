#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Two Very Auto - FastAPI Startup Script
간편한 서버 시작을 위한 스크립트
"""

import uvicorn
import sys
import os
from pathlib import Path

def main():
    """FastAPI 서버 시작"""
    print("🚀 Two Very Auto - FastAPI Server Starting...")
    print("📋 Server Info:")
    print("   - URL: http://127.0.0.1:8001")
    print("   - API Docs: http://127.0.0.1:8001/docs")
    print("   - Redoc: http://127.0.0.1:8001/redoc")
    print("   - WebSocket: ws://127.0.0.1:8001/ws")
    print()
    
    try:
        # FastAPI 앱 실행
        uvicorn.run(
            "fastapi_next_gen:app",
            host="127.0.0.1",
            port=8001,
            reload=True,  # 개발 모드에서 자동 리로드
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()