#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Main Application - Two Very Auto (Safe Version)
안전한 버전으로 점진적 초기화
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import traceback

# 기본 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="Two Very Auto - FastAPI",
    description="Baccarat Pair Tracking System with AsyncIO Support",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 초기화 상태 추적
initialization_status = {
    "database": False,
    "cache": False,
    "notifications": False,
    "monitoring": False,
    "ai_engine": False,
    "packet_monitor": False,
    "deep_learning": False,
    "startup_complete": False
}

# 모든 라우터 포함
try:
    # 기존 라우터들
    from routers import demo, stats, websocket_router, notifications, ai_predictions, database_performance
    
    # 새로운 라우터들
    from routes.pair_routes import router as pair_router
    from routes.analysis_routes import router as analysis_router
    
    # 기본 라우터 등록
    app.include_router(demo.router, prefix="/api", tags=["demo"])
    app.include_router(stats.router, prefix="/api", tags=["stats"])
    
    # 새로운 기능 라우터 등록
    app.include_router(pair_router, tags=["페어 데이터"])
    app.include_router(analysis_router, tags=["딥러닝 분석"])
    
    # WebSocket 라우터 등록
    from routes.websocket_routes import router as websocket_router
    app.include_router(websocket_router, tags=["실시간 통신"])
    
    logger.info("✅ 모든 라우터 로드 완료 (페어 데이터, 딥러닝 분석 포함)")
except Exception as e:
    logger.warning(f"⚠️ 일부 라우터 로드 실패: {e}")

@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 대시보드 페이지"""
    template_path = Path(__file__).parent / "templates" / "dashboard.html"
    if template_path.exists():
        return FileResponse(template_path)
    
    # 전체 시스템 상태를 보여주는 대시보드
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Two Very Auto FastAPI Dashboard</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }}
            .container {{ 
                max-width: 1200px; margin: 0 auto; padding: 20px; 
            }}
            .header {{
                text-align: center; color: white; margin-bottom: 30px;
            }}
            .header h1 {{
                font-size: 2.5em; margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            .status-grid {{
                display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px; margin-bottom: 30px;
            }}
            .status-card {{
                background: white; border-radius: 10px; padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }}
            .status-card:hover {{ transform: translateY(-5px); }}
            .status-card h3 {{ color: #667eea; margin-bottom: 15px; }}
            .status-indicator {{
                display: inline-block; width: 12px; height: 12px;
                border-radius: 50%; margin-right: 8px;
            }}
            .status-ok {{ background: #4CAF50; }}
            .status-loading {{ background: #FF9800; }}
            .status-error {{ background: #F44336; }}
            .nav-buttons {{
                display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px; margin-top: 30px;
            }}
            .btn {{
                display: block; background: #667eea; color: white; 
                padding: 15px 20px; text-decoration: none; border-radius: 8px;
                text-align: center; font-weight: bold; transition: background 0.3s;
            }}
            .btn:hover {{ background: #5a67d8; }}
            .btn.secondary {{ background: #48bb78; }}
            .btn.secondary:hover {{ background: #38a169; }}
            .features {{
                background: rgba(255,255,255,0.9); border-radius: 10px;
                padding: 20px; margin-top: 30px;
            }}
            .features h2 {{ color: #667eea; margin-bottom: 15px; }}
            .feature-list {{
                display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 15px;
            }}
            .feature-item {{
                background: #f8f9fa; padding: 15px; border-radius: 8px;
                border-left: 4px solid #667eea;
            }}
            .timestamp {{ 
                text-align: center; color: rgba(255,255,255,0.8); 
                margin-top: 20px; font-size: 0.9em; 
            }}
        </style>
        <script>
            async function updateStatus() {{
                try {{
                    const response = await fetch('/system-status');
                    const data = await response.json();
                    
                    // 상태 업데이트 로직
                    Object.keys(data.services || {{}}).forEach(service => {{
                        const indicator = document.getElementById(service + '-status');
                        if (indicator) {{
                            const status = data.services[service];
                            indicator.className = 'status-indicator ' + 
                                (status === 'ok' ? 'status-ok' : 
                                 status === 'loading' ? 'status-loading' : 'status-error');
                        }}
                    }});
                    
                    document.getElementById('last-update').textContent = 
                        '마지막 업데이트: ' + new Date().toLocaleTimeString('ko-KR');
                }} catch (error) {{
                    console.error('상태 업데이트 실패:', error);
                }}
            }}
            
            // 5초마다 상태 업데이트
            setInterval(updateStatus, 5000);
            
            // 페이지 로드 시 즉시 업데이트
            window.addEventListener('load', updateStatus);
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Two Very Auto</h1>
                <p>AsyncIO 지원 바카라 페어 추적 시스템 v2.0.0</p>
            </div>
            
            <div class="status-grid">
                <div class="status-card">
                    <h3>🗄️ 데이터베이스 시스템</h3>
                    <p><span id="database-status" class="status-indicator status-{'ok' if initialization_status['database'] else 'loading'}"></span>
                    {"연결됨" if initialization_status['database'] else "초기화 중"}</p>
                    <small>SQLite + 최적화 연결 풀</small>
                </div>
                
                <div class="status-card">
                    <h3>💾 캐시 시스템</h3>
                    <p><span id="cache-status" class="status-indicator status-{'ok' if initialization_status['cache'] else 'loading'}"></span>
                    {"활성화" if initialization_status['cache'] else "로딩 중"}</p>
                    <small>LRU + TTL + 압축 지원</small>
                </div>
                
                <div class="status-card">
                    <h3>🔔 알림 시스템</h3>
                    <p><span id="notifications-status" class="status-indicator status-{'ok' if initialization_status['notifications'] else 'loading'}"></span>
                    {"실행 중" if initialization_status['notifications'] else "준비 중"}</p>
                    <small>WebSocket + 로그 채널</small>
                </div>
                
                <div class="status-card">
                    <h3>📊 모니터링</h3>
                    <p><span id="monitoring-status" class="status-indicator status-{'ok' if initialization_status['monitoring'] else 'loading'}"></span>
                    {"활성" if initialization_status['monitoring'] else "시작 중"}</p>
                    <small>실시간 연결 추적</small>
                </div>
                
                <div class="status-card">
                    <h3>🧠 AI 예측 엔진</h3>
                    <p><span id="ai_engine-status" class="status-indicator status-{'ok' if initialization_status['ai_engine'] else 'loading'}"></span>
                    {"준비됨" if initialization_status['ai_engine'] else "로딩 중"}</p>
                    <small>비동기 예측 + 캐싱</small>
                </div>
                
                <div class="status-card">
                    <h3>⚡ 서버 상태</h3>
                    <p><span class="status-indicator status-ok"></span>정상 운영</p>
                    <small>AsyncIO 고성능 처리</small>
                </div>
            </div>
            
            <div class="nav-buttons">
                <a href="/docs" class="btn">📖 API 문서</a>
                <a href="/api/pairs/" class="btn secondary">🎯 페어 모니터링</a>
                <a href="/health" class="btn secondary">💚 상태 확인</a>
                <a href="/system-status" class="btn">📊 시스템 현황</a>
                <a href="/redoc" class="btn">📚 ReDoc</a>
            </div>
            
            <div class="features">
                <h2>🛠️ 주요 기능</h2>
                <div class="feature-list">
                    <div class="feature-item">
                        <strong>🎯 실시간 바카라 추적</strong>
                        <p>페어 패턴 감지 및 실시간 알림</p>
                    </div>
                    <div class="feature-item">
                        <strong>🤖 AI 예측 시스템</strong>
                        <p>딥러닝 기반 페어 패턴 분석 및 예측</p>
                    </div>
                    <div class="feature-item">
                        <strong>📁 실시간 패킷 처리</strong>
                        <p>패킷 폴더 모니터링 및 자동 디코딩</p>
                    </div>
                    <div class="feature-item">
                        <strong>📊 딥러닝 분석</strong>
                        <p>고급 패턴 분석 및 트렌드 예측</p>
                    </div>
                    <div class="feature-item">
                        <strong>📡 WebSocket 통신</strong>
                        <p>실시간 양방향 데이터 스트리밍</p>
                    </div>
                    <div class="feature-item">
                        <strong>⚡ 고성능 캐싱</strong>
                        <p>다중 전략 캐싱 및 자동 최적화</p>
                    </div>
                    <div class="feature-item">
                        <strong>🔍 성능 모니터링</strong>
                        <p>실시간 성능 메트릭 및 통계</p>
                    </div>
                    <div class="feature-item">
                        <strong>🛡️ 안전한 아키텍처</strong>
                        <p>비동기 처리 및 오류 복구 시스템</p>
                    </div>
                </div>
            </div>
            
            <div class="timestamp">
                <p id="last-update">시스템 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    try:
        logger.info("Health check requested")
        
        response = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "version": "2.0.0",
            "initialization": initialization_status,
            "services": {
                "api": "running",
                "websocket": "ready" if initialization_status["monitoring"] else "loading",
                "background_tasks": "running" if initialization_status["startup_complete"] else "loading"
            },
            "features": [
                "AsyncIO 네이티브 지원",
                "실시간 WebSocket 통신", 
                "AI 예측 시스템",
                "고급 캐싱 전략",
                "데이터베이스 최적화",
                "성능 모니터링"
            ]
        }
        
        logger.info("Health check completed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

@app.get("/system-status")
async def system_status():
    """시스템 상태 상세 정보"""
    try:
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "initialization_status": initialization_status,
            "services": {
                "database": "ok" if initialization_status["database"] else "loading",
                "cache": "ok" if initialization_status["cache"] else "loading", 
                "notifications": "ok" if initialization_status["notifications"] else "loading",
                "monitoring": "ok" if initialization_status["monitoring"] else "loading",
                "ai_engine": "ok" if initialization_status["ai_engine"] else "loading"
            },
            "uptime": "running",
            "performance": {
                "memory_usage": "normal",
                "response_time": "< 100ms",
                "active_connections": 1
            }
        }
    except Exception as e:
        logger.error(f"System status error: {e}")
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}

@app.get("/initialize/{service}")
async def initialize_service(service: str, background_tasks: BackgroundTasks):
    """개별 서비스 초기화"""
    if service not in initialization_status:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if initialization_status[service]:
        return {"message": f"{service} is already initialized", "status": "ok"}
    
    # 백그라운드에서 초기화 실행
    background_tasks.add_task(_initialize_service, service)
    
    return {
        "message": f"{service} initialization started",
        "status": "loading",
        "check_url": "/system-status"
    }

async def _initialize_service(service_name: str):
    """개별 서비스 초기화 로직"""
    try:
        logger.info(f"🔄 {service_name} 초기화 시작")
        
        if service_name == "database":
            from services.database import DatabaseManager
            from services.optimized_database import OptimizedDatabaseManager
            
            db_manager = DatabaseManager()
            optimized_db_manager = OptimizedDatabaseManager() 
            
            await db_manager.initialize()
            await optimized_db_manager.initialize()
            
            initialization_status["database"] = True
            logger.info("✅ Database 초기화 완료")
            
        elif service_name == "cache":
            from services.cache_manager import cache_manager
            from services.advanced_cache import init_all_caches
            
            # 기본 캐시 초기화는 데이터베이스가 필요
            if initialization_status["database"]:
                await cache_manager.start_background_cleanup()
            
            await init_all_caches()
            initialization_status["cache"] = True
            logger.info("✅ Cache 초기화 완료")
            
        elif service_name == "notifications":
            from services.notification_service import notification_service
            
            await notification_service.start()
            initialization_status["notifications"] = True
            logger.info("✅ Notifications 초기화 완료")
            
        elif service_name == "monitoring":
            from services.connection_monitor import connection_monitor
            
            await connection_monitor.start_monitoring()
            initialization_status["monitoring"] = True
            logger.info("✅ Monitoring 초기화 완료")
            
        elif service_name == "ai_engine":
            from services.async_ai_engine import get_async_ai_engine
            
            ai_engine = await get_async_ai_engine()
            initialization_status["ai_engine"] = True
            logger.info("✅ AI Engine 초기화 완료")
            
        elif service_name == "packet_monitor":
            from services.packet_monitor_service import get_packet_monitor_service
            
            packet_monitor = get_packet_monitor_service()
            await packet_monitor.start_monitoring()
            initialization_status["packet_monitor"] = True
            logger.info("✅ Packet Monitor 초기화 완료")
            
        elif service_name == "deep_learning":
            from services.deep_learning_analysis_service import get_deep_learning_analysis_service
            
            dl_service = get_deep_learning_analysis_service()
            initialization_status["deep_learning"] = True
            logger.info("✅ Deep Learning Service 초기화 완료")
            
        # 모든 서비스가 초기화되면 startup_complete = True
        if all(initialization_status.values()):
            initialization_status["startup_complete"] = True
            logger.info("🎉 모든 서비스 초기화 완료!")
            
    except Exception as e:
        logger.error(f"❌ {service_name} 초기화 실패: {e}")
        logger.error(traceback.format_exc())

@app.get("/initialize-all")
async def initialize_all_services(background_tasks: BackgroundTasks):
    """모든 서비스 순차적 초기화"""
    services = ["database", "cache", "notifications", "monitoring", "ai_engine", "packet_monitor", "deep_learning"]
    
    for service in services:
        if not initialization_status[service]:
            background_tasks.add_task(_initialize_service, service)
    
    return {
        "message": "All services initialization started (페어 모니터링 및 딥러닝 분석 포함)",
        "services": services,
        "check_url": "/system-status"
    }

async def get_system_stats():
    """시스템 통계 수집"""
    try:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "running",
            "uptime": "monitoring",
            "services_initialized": sum(initialization_status.values()),
            "total_services": len(initialization_status)
        }
    except Exception as e:
        logger.error(f"System stats collection error: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("Two Very Auto FastAPI Server (Safe Mode)")
    print("=" * 60)
    print("AsyncIO native support")
    print("Progressive service initialization")
    print("Real-time monitoring dashboard")
    print("Full API documentation")
    print("=" * 60)
    print("URL: http://127.0.0.1:8006")
    print("API docs: http://127.0.0.1:8006/docs")
    print("Dashboard: http://127.0.0.1:8006/")
    print("Health: http://127.0.0.1:8006/health")
    print("=" * 60)
    print("초기화: http://127.0.0.1:8006/initialize-all")
    print("=" * 60)
    
    uvicorn.run(
        "main_safe:app",
        host="0.0.0.0",
        port=8006,
        reload=False,
        access_log=True
    )