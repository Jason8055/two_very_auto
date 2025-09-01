#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal test to check route registration
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
from pathlib import Path

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/comprehensive-dashboard", response_class=HTMLResponse)
async def comprehensive_dashboard():
    """종합 바카라 방 통계 대시보드"""
    template_path = Path(__file__).parent / "templates" / "comprehensive_dashboard.html"
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read(), status_code=200)
    else:
        return HTMLResponse(content="<h1>종합 통계 대시보드</h1><p>템플릿을 찾을 수 없습니다.</p>", status_code=404)

@app.get("/test")
async def test():
    return {"message": "Test route works"}

if __name__ == "__main__":
    print("Available routes:")
    for route in app.routes:
        print(f"  {route.path} - {route.methods if hasattr(route, 'methods') else 'N/A'}")
    
    uvicorn.run(app, host="127.0.0.1", port=8099)