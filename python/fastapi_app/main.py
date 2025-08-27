#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Main Application - Two Very Auto
AsyncIO 네이티브 지원으로 기존 충돌 해결
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from pathlib import Path
from datetime import datetime

from routers import demo, stats, websocket_router, notifications, ai_predictions, database_performance, pair_notifications
from services.database import DatabaseManager
from services.optimized_database import OptimizedDatabaseManager
from services.cache_manager import cache_manager
from services.notification_service import notification_service, WebSocketNotificationChannel, LogNotificationChannel
from services.pair_notification_service import pair_notification_service
from services.pair_broadcast_service import pair_broadcast_service, BroadcastChannelType
from services.connection_monitor import connection_monitor
from services.async_ai_engine import get_async_ai_engine
from services.advanced_cache import init_all_caches, stop_all_caches
# from models.response import HealthCheckResponse  # Unused import

# 로깅 설정
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

# 데이터베이스 매니저 초기화
db_manager = DatabaseManager()
optimized_db_manager = OptimizedDatabaseManager()

# 라우터 포함
app.include_router(demo.router, prefix="/api", tags=["demo"])
app.include_router(stats.router, prefix="/api", tags=["stats"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(pair_notifications.router, prefix="/api/pair-notifications", tags=["pair-notifications"])
app.include_router(ai_predictions.router, prefix="/api/ai", tags=["ai-predictions"])
app.include_router(database_performance.router, prefix="/api/database", tags=["database-performance"])
app.include_router(websocket_router.router, prefix="/ws", tags=["websocket"])

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 이벤트"""
    logger.info("FastAPI server starting...")
    
    try:
        # 데이터베이스 초기화
        await db_manager.initialize()
        await optimized_db_manager.initialize()
        logger.info("Database initialization completed (Standard + Optimized)")
        
        # 캐시 시스템 초기화
        await cache_manager.warm_up(db_manager)
        await cache_manager.start_background_cleanup()
        
        # 고급 캐시 시스템 초기화
        await init_all_caches()
        logger.info("Cache system initialized with warm-up data (Standard + Advanced)")
        
        # 알림 시스템 초기화
        from routers.websocket_router import get_websocket_manager
        websocket_manager = get_websocket_manager()
        
        # 알림 채널 등록
        notification_service.register_channel(WebSocketNotificationChannel(websocket_manager))
        notification_service.register_channel(LogNotificationChannel())
        
        # 알림 서비스 시작
        await notification_service.start()
        logger.info("Notification system initialized and started")
        
        # 페어 알림 시스템 초기화
        await pair_notification_service.start()
        logger.info("Pair notification service initialized and started")
        
        # 페어 브로드캐스트 시스템 초기화
        pair_broadcast_service.register_channel(BroadcastChannelType.WEBSOCKET, websocket_manager)
        await pair_broadcast_service.start()
        logger.info("Pair broadcast service initialized and started")
        
        # 연결 모니터링 시작
        await connection_monitor.start_monitoring()
        logger.info("Connection monitoring started")
        
        # AI 예측 엔진 초기화
        ai_engine = await get_async_ai_engine()
        logger.info("Async AI prediction engine initialized")
        
        # 환영 알림 전송
        await notification_service.send_system_warning(
            "서버 시작",
            "FastAPI 서버가 성공적으로 시작되었습니다.",
            {
                "version": "2.0.0", 
                "features": ["AsyncIO", "WebSocket", "AI예측", "실시간알림", "실시간페어알림", "DB최적화", "고급캐시"],
                "optimizations": ["연결풀링", "쿼리최적화", "배치처리", "성능모니터링", "페어감지", "브로드캐스트"]
            }
        )
        
        # 백그라운드 작업 시작
        asyncio.create_task(background_monitoring())
        logger.info("Background monitoring started")
        
        logger.info("FastAPI server startup completed successfully")
        
    except Exception as e:
        logger.error(f"FastAPI server startup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 이벤트"""
    logger.info("FastAPI server shutting down...")
    
    # 페어 브로드캐스트 서비스 중지
    await pair_broadcast_service.stop()
    logger.info("Pair broadcast service stopped")
    
    # 페어 알림 서비스 중지
    await pair_notification_service.stop()
    logger.info("Pair notification service stopped")
    
    # 알림 서비스 중지
    await notification_service.stop()
    logger.info("Notification service stopped")
    
    # 연결 모니터링 중지
    await connection_monitor.stop_monitoring()
    logger.info("Connection monitoring stopped")
    
    # 고급 캐시 시스템 중지
    await stop_all_caches()
    logger.info("Advanced cache system stopped")
    
    # AI 예측 엔진 중지
    if get_async_ai_engine:
        try:
            ai_engine = await get_async_ai_engine()
            await ai_engine.stop_background_tasks()
            logger.info("Async AI prediction engine stopped")
        except Exception as e:
            logger.error(f"Error stopping AI engine: {e}")
    
    await db_manager.close()
    await optimized_db_manager.close()
    logger.info("Database connections closed (Standard + Optimized)")

@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 대시보드 페이지"""
    template_path = Path(__file__).parent / "templates" / "dashboard.html"
    if template_path.exists():
        return FileResponse(template_path)
    
    # 폴백 HTML
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>Two Very Auto FastAPI</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin: 50px; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
            .btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Two Very Auto - FastAPI</h1>
            <p>AsyncIO 지원 바카라 페어 추적 시스템</p>
            <p><strong>상태:</strong> ✅ 서비스 정상 운영</p>
            <a href="/docs" class="btn">📖 API 문서</a>
            <a href="/health" class="btn">💚 상태 확인</a>
        </div>
    </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    try:
        logger.info("Health check requested")
        
        # 데이터베이스 상태 확인
        db_status = await db_manager.health_check()
        logger.info(f"Database status: {db_status}")
        
        response = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "version": "2.0.0",
            "database_status": db_status,
            "services": {
                "api": "running",
                "websocket": "running",
                "background_tasks": "running"
            }
        }
        logger.info(f"Health check completed successfully")
        return response
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

async def background_monitoring():
    """백그라운드 모니터링 작업"""
    logger.info("Background monitoring started")
    
    # WebSocket 매니저 import
    from routers.websocket_router import get_websocket_manager
    websocket_manager = get_websocket_manager()
    
    while True:
        try:
            # 30초마다 시스템 상태 확인
            await asyncio.sleep(30)
            
            # 시스템 통계 수집
            basic_stats = await get_system_stats()
            
            # 연결된 클라이언트가 있는 경우만 상세 통계 수집
            if websocket_manager.get_connection_count() > 0:
                try:
                    # 데이터베이스 통계 수집
                    detailed_stats = await db_manager.get_system_stats()
                    
                    # 실시간 업데이트 브로드캐스트
                    await websocket_manager.broadcast_to_subscribers('stats', {
                        'type': 'stats_update',
                        'data': {
                            'stats': detailed_stats,
                            'system_info': basic_stats,
                            'update_time': datetime.now().isoformat(),
                            'connected_clients': websocket_manager.get_connection_count()
                        }
                    })
                    
                    logger.info(f"System stats broadcasted to {websocket_manager.get_connection_count()} clients")
                except Exception as e:
                    logger.error(f"Stats broadcast error: {e}")
            
            logger.info(f"System monitoring: {basic_stats.get('status', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Background monitoring error: {e}")
            await asyncio.sleep(60)  # 오류 시 1분 대기

async def get_system_stats():
    """시스템 통계 수집"""
    try:
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "running",
            "uptime": "monitoring",
            "database_connections": 1
        }
    except Exception as e:
        logger.error(f"System stats collection error: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    import socket
    
    # 서버 설정
    host = "127.0.0.1"
    port = 8080
    
    # 포트 가용성 체크
    def check_port(h, p):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((h, p))
                return True
            except:
                return False
    
    # 사용 가능한 포트 찾기
    if not check_port(host, port):
        for test_port in [8080, 8000, 3000, 9999, 7777]:
            if check_port(host, test_port):
                port = test_port
                break
    
    print("=" * 60)
    print("Two Very Auto FastAPI Server")
    print("=" * 60)
    print("AsyncIO native support")
    print("Real-time WebSocket communication")
    print("Automatic API documentation")  
    print("Type safety guaranteed")
    print("High-performance async processing")
    print("=" * 60)
    print(f"URL: http://{host}:{port}")
    print(f"API docs: http://{host}:{port}/docs")
    print(f"Health check: http://{host}:{port}/health")
    print("=" * 60)
    
    try:
        # uvicorn 직접 설정
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            reload=False,
            access_log=True,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
    except KeyboardInterrupt:
        print("\n서버가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n서버 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()