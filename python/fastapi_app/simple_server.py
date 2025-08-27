#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 FastAPI 서버 - 연결 문제 해결을 위한 최소한의 서버
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Simple FastAPI Server", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Two Very Auto FastAPI Server", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Server is running successfully"}

@app.get("/test")
async def test():
    return {"test": "success", "data": {"timestamp": "now", "features": ["basic", "health", "test"]}}

if __name__ == "__main__":
    print("=" * 50)
    print("Simple FastAPI Server Starting")
    print("=" * 50)
    print("URL: http://127.0.0.1:8005")
    print("Health: http://127.0.0.1:8005/health")
    print("Test: http://127.0.0.1:8005/test")
    print("=" * 50)
    
    uvicorn.run(
        "simple_server:app",
        host="0.0.0.0",
        port=8005,
        reload=False,
        access_log=True
    )