#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 FastAPI 테스트
"""

from fastapi import FastAPI
import asyncio

# 매우 간단한 앱
app = FastAPI(title="Simple Test")

@app.get("/")
async def root():
    return {"message": "Hello FastAPI"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/demo")
async def demo():
    # 간단한 지연
    await asyncio.sleep(0.1)
    return {
        "success": True,
        "games_added": 5,
        "pairs_found": 1,
        "processing_time": 0.1,
        "mode": "simple_test"
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting simple FastAPI test on port 8001...")
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")