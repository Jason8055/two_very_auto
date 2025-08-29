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

# Smart Output System 추가
from utils.smart_output import section_header, server_status, info, success, warning, error

from routers import demo, stats, websocket_router, notifications, ai_predictions, database_performance, pair_notifications, historical_games, packet_data, improved_pair_api
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
app.include_router(historical_games.router, prefix="/api/historical", tags=["historical-games"])
app.include_router(packet_data.router, prefix="/api", tags=["packet-data"])
app.include_router(improved_pair_api.router, prefix="/api", tags=["improved-pairs"])
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
            body { font-family: Arial, sans-serif; text-align: center; margin: 50px; background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; }
            .container { max-width: 800px; margin: 0 auto; padding: 30px; border: 1px solid rgba(255,255,255,0.3); border-radius: 15px; backdrop-filter: blur(10px); background: rgba(255,255,255,0.1); }
            .btn { background: linear-gradient(45deg, #ff6b6b, #ff8e53); color: white; padding: 15px 25px; text-decoration: none; border-radius: 8px; display: inline-block; margin: 10px; font-weight: bold; transition: all 0.3s; }
            .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
            .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
            .feature-card { background: rgba(255,255,255,0.15); padding: 20px; border-radius: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Two Very Auto - 페어 정보 시스템</h1>
            <p>🎰 실시간 바카라 페어 감지 및 알림 시스템</p>
            <p><strong>상태:</strong> ✅ 서비스 정상 운영</p>
            
            <div class="feature-grid">
                <div class="feature-card">
                    <h3>🎰 실시간 페어 감지</h3>
                    <p>플레이어, 뱅커, 양쪽 페어 실시간 감지</p>
                </div>
                <div class="feature-card">
                    <h3>📊 패턴 분석</h3>
                    <p>연속 페어, 교대 패턴, 희귀 패턴 분석</p>
                </div>
                <div class="feature-card">
                    <h3>🔔 실시간 알림</h3>
                    <p>WebSocket 기반 즉시 알림</p>
                </div>
                <div class="feature-card">
                    <h3>📈 상세 통계</h3>
                    <p>테이블별 페어 발생 통계</p>
                </div>
            </div>
            
            <div style="margin: 30px 0;">
                <a href="/pair-display" class="btn">🎯 페어 대시보드</a>
                <a href="/docs" class="btn">📖 API 문서</a>
                <a href="/health" class="btn">💚 상태 확인</a>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/pair-display", response_class=HTMLResponse)
async def pair_display():
    """페어 전용 대시보드 페이지"""
    template_path = Path(__file__).parent / "templates" / "pair_display.html"
    if template_path.exists():
        return FileResponse(template_path)
    else:
        # 새로운 향상된 페어 대시보드로 폴백
        return await enhanced_pair_dashboard()

@app.get("/pair-dashboard", response_class=HTMLResponse)
async def enhanced_pair_dashboard():
    """향상된 페어 정보 대시보드 - 실제 패킷 데이터 분석"""
    template_path = Path(__file__).parent / "templates" / "pair_dashboard.html"
    if template_path.exists():
        return FileResponse(template_path)
    else:
        raise HTTPException(status_code=404, detail="향상된 페어 대시보드 템플릿을 찾을 수 없습니다.")

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
    preferred_ports = [8080, 8000, 3000, 9999, 7777, 5000, 8081, 8082, 8083, 8084]
    port = None
    
    # 포트 가용성 체크
    def check_port(h, p):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((h, p))
                return True
            except:
                return False
    
    # 서버 시작 헤더
    section_header("Two Very Auto FastAPI Server 시작")
    
    # 사용 가능한 포트 찾기
    info("포트 검색 중...")
    for test_port in preferred_ports:
        if check_port(host, test_port):
            port = test_port
            success(f"포트 {port} 사용 가능", 상태="선택됨")
            break
        else:
            logger.debug(f"포트 {test_port} 사용 불가")
    
    # 모든 선호 포트가 사용 중인 경우 자동 할당
    if port is None:
        warning("모든 선호 포트 사용 중 - 자동 포트 할당 시도")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, 0))  # 0 = 자동 할당
            port = s.getsockname()[1]
            success(f"자동 할당된 포트", 포트=port)
    
    if port is None:
        error("사용 가능한 포트를 찾을 수 없습니다.")
        exit(1)
    
    # 서버 정보 표시
    info("🎯 Two Very Auto FastAPI Server - 페어 정보 시스템")
    info("✨ AsyncIO 네이티브 지원")  
    info("📡 실시간 WebSocket 통신")
    info("📚 자동 API 문서화")
    info("🛡️ 타입 안전성 보장")
    info("⚡ 고성능 비동기 처리")
    info("🎰 실시간 페어 감지 및 알림")
    info("📊 패턴 분석 및 통계")
    
    # 접속 정보
    success("서버 접속 정보", 
           메인_URL=f"http://{host}:{port}",
           페어_대시보드=f"http://{host}:{port}/pair-display", 
           API_문서=f"http://{host}:{port}/docs",
           상태_확인=f"http://{host}:{port}/health")
    
    info("🎮 실시간 페어 정보 확인 방법:")
    info(f"   1. 브라우저에서 http://{host}:{port} 접속")
    info(f"   2. 페어 전용 화면: http://{host}:{port}/pair-display")  
    info("   3. 실시간 WebSocket 알림 자동 수신")
    
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
        warning("서버가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        error("서버 실행 중 오류 발생", 오류=str(e))
        import traceback
        logger.error(traceback.format_exc())