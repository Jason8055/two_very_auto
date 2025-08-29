#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
백업 시스템 관리 대시보드 서버
FastAPI 기반 실시간 백업 상태 모니터링 및 관리
"""

import os
import json
import asyncio
import logging
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 로컬 모듈
import sys
sys.path.append(str(Path(__file__).parent / 'python'))
from python.korean_encoding_fix import setup_korean_encoding, safe_print

# 백업 시스템 모듈
from cloud.backup_manager import get_backup_manager
from cloud.restore_system import get_restore_system
from cloud.secure_config_manager import get_secure_config_manager
from notification_system import get_notification_system
from backup_health_checker import BackupHealthChecker
from integrated_monitoring import IntegratedMonitoringSystem
from safe_security_wrapper import get_safe_security_wrapper

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title="Two Very Auto - 백업 시스템 대시보드",
    description="엔터프라이즈급 백업 시스템 관리 대시보드",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 및 템플릿 설정
static_dir = Path(__file__).parent / "static"
template_dir = Path(__file__).parent / "templates"

static_dir.mkdir(exist_ok=True)
template_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(template_dir))

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.copy():
            try:
                await connection.send_json(message)
            except:
                self.active_connections.remove(connection)

manager = ConnectionManager()

# 글로벌 서비스 인스턴스들
backup_manager = get_backup_manager()
restore_system = get_restore_system()
secure_config = get_secure_config_manager()
notification_system = get_notification_system()
health_checker = BackupHealthChecker()
monitoring_system = IntegratedMonitoringSystem()

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """대시보드 홈페이지"""
    return templates.TemplateResponse("backup_dashboard.html", {"request": request})

@app.get("/api/status")
async def get_system_status():
    """시스템 전체 상태 조회"""
    try:
        # 백업 상태
        backup_status = backup_manager.get_backup_status()
        
        # 복원 지점 상태
        restore_points = restore_system.discover_restore_points()
        restore_status = {
            "available_points": len(restore_points),
            "latest_backup": restore_points[0].timestamp.isoformat() if restore_points else None,
            "total_size_mb": sum(rp.size_mb for rp in restore_points)
        }
        
        # 보안 상태
        security_report = secure_config.get_security_report()
        
        # 알림 상태
        notification_config = notification_system.config
        enabled_channels = []
        if notification_config.get("email", {}).get("enabled"):
            enabled_channels.append("이메일")
        if notification_config.get("slack", {}).get("enabled"):
            enabled_channels.append("Slack")
        if notification_config.get("discord", {}).get("enabled"):
            enabled_channels.append("Discord")
        
        # 디스크 공간
        import shutil
        total, used, free = shutil.disk_usage(Path.cwd())
        disk_status = {
            "total_gb": total / (1024**3),
            "used_gb": used / (1024**3),
            "free_gb": free / (1024**3),
            "used_percent": (used / total) * 100
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "backup": backup_status,
            "restore": restore_status,
            "security": {
                "ssl_valid": security_report["ssl_certificate"]["exists"],
                "ssl_days_left": security_report["ssl_certificate"].get("days_until_expiry"),
                "encryption_enabled": security_report["encryption_enabled"],
                "configured_providers": security_report["configured_providers"]
            },
            "notifications": {
                "enabled_channels": enabled_channels,
                "total_channels": len(enabled_channels)
            },
            "system": {
                "disk": disk_status,
                "uptime": "N/A"  # Windows에서는 복잡함
            }
        }
        
    except Exception as e:
        logger.error(f"상태 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backups")
async def get_backup_history():
    """백업 히스토리 조회"""
    try:
        # 복원 지점 목록
        restore_points = restore_system.discover_restore_points()
        
        backups = []
        for rp in restore_points:
            backups.append({
                "id": rp.backup_id,
                "provider": rp.provider,
                "timestamp": rp.timestamp.isoformat(),
                "size_mb": rp.size_mb,
                "type": rp.backup_type,
                "age_hours": (datetime.now() - rp.timestamp).total_seconds() / 3600
            })
        
        return {
            "backups": backups,
            "total_count": len(backups),
            "total_size_mb": sum(b["size_mb"] for b in backups),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"백업 히스토리 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backup/run")
async def run_backup(config_name: str = "local_backup"):
    """수동 백업 실행"""
    try:
        safe_print(f"수동 백업 시작: {config_name}")
        
        result = backup_manager.backup_database(config_name)
        
        # WebSocket으로 실시간 업데이트
        await manager.broadcast({
            "type": "backup_started",
            "config": config_name,
            "timestamp": datetime.now().isoformat()
        })
        
        if result.success:
            await manager.broadcast({
                "type": "backup_completed",
                "config": config_name,
                "size_mb": result.size_mb,
                "duration": result.duration_seconds,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"{config_name} 백업 완료",
                "result": {
                    "backup_id": result.backup_id,
                    "size_mb": result.size_mb,
                    "duration_seconds": result.duration_seconds,
                    "file_path": result.file_path
                }
            }
        else:
            await manager.broadcast({
                "type": "backup_failed",
                "config": config_name,
                "error": result.error_message,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": False,
                "message": f"{config_name} 백업 실패",
                "error": result.error_message
            }
            
    except Exception as e:
        logger.error(f"백업 실행 오류: {e}")
        await manager.broadcast({
            "type": "backup_error",
            "config": config_name,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backup/test-restore")
async def test_restore(backup_id: str):
    """백업 복원 테스트"""
    try:
        restore_points = restore_system.discover_restore_points()
        target_point = None
        
        for rp in restore_points:
            if rp.backup_id == backup_id:
                target_point = rp
                break
        
        if not target_point:
            raise HTTPException(status_code=404, detail="백업을 찾을 수 없습니다")
        
        # 임시 복원 테스트
        test_result = await health_checker.test_single_backup(target_point)
        
        await manager.broadcast({
            "type": "restore_test_completed",
            "backup_id": backup_id,
            "success": test_result["success"],
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "message": "복원 테스트 완료",
            "result": test_result
        }
        
    except Exception as e:
        logger.error(f"복원 테스트 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/health-check")
async def run_health_check():
    """백업 건전성 종합 점검"""
    try:
        await manager.broadcast({
            "type": "health_check_started",
            "timestamp": datetime.now().isoformat()
        })
        
        health_report = await health_checker.run_comprehensive_health_check()
        
        await manager.broadcast({
            "type": "health_check_completed",
            "status": health_report["overall_status"],
            "test_count": len(health_report["test_results"]),
            "warnings": len(health_report["warnings"]),
            "errors": len(health_report["errors"]),
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "message": "건전성 점검 완료",
            "report": health_report
        }
        
    except Exception as e:
        logger.error(f"건전성 점검 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications/test")
async def test_notification():
    """테스트 알림 전송"""
    try:
        results = await notification_system.send_notification(
            level="success",
            title="대시보드 테스트 알림",
            message="Two Very Auto 대시보드에서 전송한 테스트 알림입니다.",
            details={
                "테스트_시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "발신자": "백업 대시보드",
                "상태": "정상"
            }
        )
        
        return {
            "success": True,
            "message": "테스트 알림 전송 완료",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"알림 테스트 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/configs")
async def get_configurations():
    """시스템 설정 조회"""
    try:
        # 백업 설정
        backup_configs = list(backup_manager.backup_configs.keys())
        
        # 스케줄 설정
        schedule_config = {}
        schedule_file = Path("backup_schedule_config.json")
        if schedule_file.exists():
            with open(schedule_file, 'r', encoding='utf-8') as f:
                schedule_config = json.load(f)
        
        # 알림 설정
        notification_config = notification_system.config
        
        # 모니터링 설정
        monitoring_config = monitoring_system.monitoring_config
        
        return {
            "backup_providers": backup_configs,
            "schedules": schedule_config.get("schedules", {}),
            "notifications": {
                "enabled": notification_config.get("enabled", False),
                "channels": {
                    "email": notification_config.get("email", {}).get("enabled", False),
                    "slack": notification_config.get("slack", {}).get("enabled", False),
                    "discord": notification_config.get("discord", {}).get("enabled", False),
                    "teams": notification_config.get("teams", {}).get("enabled", False)
                }
            },
            "monitoring": {
                "enabled": monitoring_config.get("enabled", False),
                "check_intervals": monitoring_config.get("check_intervals", {}),
                "thresholds": monitoring_config.get("thresholds", {})
            }
        }
        
    except Exception as e:
        logger.error(f"설정 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
async def get_recent_logs(limit: int = 100):
    """최근 로그 조회"""
    try:
        logs = []
        
        # 백업 히스토리 파일에서 로그 읽기
        history_file = Path("backup_history.json")
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                backup_history = json.load(f)
                
            for record in backup_history[-limit:]:
                logs.append({
                    "timestamp": record.get("timestamp", ""),
                    "type": "backup",
                    "level": "success" if record.get("success_count", 0) > 0 else "error",
                    "message": f"{record.get('backup_type', 'backup')} - {record.get('success_count', 0)}/{record.get('total_count', 0)} 성공",
                    "details": record
                })
        
        # 건전성 점검 리포트에서 로그 읽기
        reports_dir = Path("backup_health_reports")
        if reports_dir.exists():
            for report_file in sorted(reports_dir.glob("*.json"))[-10:]:  # 최근 10개
                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                    
                    status = report.get("overall_status", "unknown")
                    level = {
                        "healthy": "success",
                        "good": "success", 
                        "warning": "warning",
                        "critical": "error"
                    }.get(status, "info")
                    
                    logs.append({
                        "timestamp": report.get("timestamp", ""),
                        "type": "health_check",
                        "level": level,
                        "message": f"건전성 점검 - {status.upper()}",
                        "details": {
                            "tests": len(report.get("test_results", {})),
                            "warnings": len(report.get("warnings", [])),
                            "errors": len(report.get("errors", []))
                        }
                    })
                except:
                    continue
        
        # 타임스탬프 기준 정렬
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {
            "logs": logs[:limit],
            "total_count": len(logs)
        }
        
    except Exception as e:
        logger.error(f"로그 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 연결 엔드포인트"""
    await manager.connect(websocket)
    try:
        while True:
            # 클라이언트로부터 메시지 수신 (keepalive)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 정적 파일 생성
async def create_dashboard_files():
    """대시보드 템플릿과 정적 파일 생성"""
    
    # CSS 파일 생성
    css_content = """
/* Two Very Auto 백업 대시보드 스타일 */
:root {
    --primary-color: #2c3e50;
    --secondary-color: #3498db;
    --success-color: #27ae60;
    --warning-color: #f39c12;
    --danger-color: #e74c3c;
    --light-bg: #ecf0f1;
    --dark-text: #2c3e50;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: var(--light-bg);
    color: var(--dark-text);
    line-height: 1.6;
}

.dashboard {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    color: white;
    padding: 30px;
    border-radius: 10px;
    margin-bottom: 30px;
    text-align: center;
}

.header h1 {
    font-size: 2.5em;
    margin-bottom: 10px;
}

.header p {
    font-size: 1.2em;
    opacity: 0.9;
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.status-card {
    background: white;
    border-radius: 10px;
    padding: 25px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    border-left: 5px solid var(--secondary-color);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.status-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.15);
}

.status-card.success {
    border-left-color: var(--success-color);
}

.status-card.warning {
    border-left-color: var(--warning-color);
}

.status-card.error {
    border-left-color: var(--danger-color);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.card-title {
    font-size: 1.3em;
    font-weight: 600;
    color: var(--primary-color);
}

.status-badge {
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 0.9em;
    font-weight: 500;
    text-transform: uppercase;
}

.badge-success {
    background-color: var(--success-color);
    color: white;
}

.badge-warning {
    background-color: var(--warning-color);
    color: white;
}

.badge-error {
    background-color: var(--danger-color);
    color: white;
}

.metric {
    margin-bottom: 10px;
}

.metric-label {
    font-weight: 500;
    color: var(--primary-color);
    margin-bottom: 5px;
}

.metric-value {
    font-size: 1.8em;
    font-weight: 700;
    color: var(--secondary-color);
}

.actions {
    margin-top: 30px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
}

.btn {
    padding: 12px 24px;
    border: none;
    border-radius: 8px;
    font-size: 1em;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
    display: inline-block;
    text-align: center;
}

.btn-primary {
    background-color: var(--secondary-color);
    color: white;
}

.btn-primary:hover {
    background-color: #2980b9;
}

.btn-success {
    background-color: var(--success-color);
    color: white;
}

.btn-success:hover {
    background-color: #229954;
}

.btn-warning {
    background-color: var(--warning-color);
    color: white;
}

.btn-warning:hover {
    background-color: #e67e22;
}

.logs-section {
    margin-top: 40px;
}

.logs-container {
    background: white;
    border-radius: 10px;
    padding: 25px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    max-height: 400px;
    overflow-y: auto;
}

.log-entry {
    padding: 10px;
    border-bottom: 1px solid #ecf0f1;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.log-entry:last-child {
    border-bottom: none;
}

.log-message {
    font-weight: 500;
}

.log-timestamp {
    font-size: 0.9em;
    color: #7f8c8d;
}

.loading {
    text-align: center;
    padding: 20px;
    color: var(--primary-color);
}

.connection-status {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 10px 15px;
    border-radius: 5px;
    font-weight: 500;
    z-index: 1000;
}

.connected {
    background-color: var(--success-color);
    color: white;
}

.disconnected {
    background-color: var(--danger-color);
    color: white;
}

.progress-bar {
    width: 100%;
    height: 8px;
    background-color: #ecf0f1;
    border-radius: 4px;
    overflow: hidden;
    margin-top: 10px;
}

.progress-fill {
    height: 100%;
    background-color: var(--secondary-color);
    transition: width 0.3s ease;
}

@media (max-width: 768px) {
    .dashboard {
        padding: 15px;
    }
    
    .header {
        padding: 20px;
    }
    
    .header h1 {
        font-size: 2em;
    }
    
    .status-grid {
        grid-template-columns: 1fr;
    }
    
    .actions {
        grid-template-columns: 1fr;
    }
}
"""
    
    css_file = static_dir / "dashboard.css"
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(css_content)
    
    safe_print(f"✅ CSS 파일 생성: {css_file}")

# 보안 관련 API 엔드포인트
@app.get("/api/security/status")
async def get_security_status():
    """보안 상태 확인 - 안전한 버전"""
    try:
        security_wrapper = get_safe_security_wrapper()
        return await security_wrapper.get_security_status()
    except Exception as e:
        logger.error(f"보안 상태 확인 오류: {e}")
        # 안전한 fallback 응답
        return {
            "status": "unknown",
            "total_issues": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "last_scan": datetime.now().isoformat(),
            "warning": "보안 모듈을 로드할 수 없습니다",
            "recommendations": [
                "수동으로 보안 스캔 실행 권장",
                "시스템 재시작 후 다시 시도"
            ]
        }

@app.post("/api/security/scan")
async def run_security_scan():
    """보안 스캔 실행 - 안전한 버전"""
    try:
        security_wrapper = get_safe_security_wrapper()
        return await security_wrapper.run_security_scan()
    except Exception as e:
        logger.error(f"보안 스캔 오류: {e}")
        raise HTTPException(status_code=500, detail=f"보안 스캔 오류: {str(e)}")

@app.post("/api/security/harden")
async def apply_security_hardening():
    """보안 강화 적용 - 안전한 버전"""
    try:
        security_wrapper = get_safe_security_wrapper()
        return await security_wrapper.apply_security_hardening()
    except Exception as e:
        logger.error(f"보안 강화 오류: {e}")
        raise HTTPException(status_code=500, detail=f"보안 강화 오류: {str(e)}")

@app.get("/api/system/health")
async def get_system_health():
    """시스템 전체 건강 상태 - 안전한 버전"""
    health_score = 100
    components = {}
    
    try:
        # 백업 상태 (안전한 방식)
        try:
            backup_manager = get_backup_manager()
            backup_configs = list(backup_manager.backup_configs.keys())
            components["backup_system"] = {
                "status": "active",
                "configs_count": len(backup_configs),
                "available_configs": backup_configs
            }
        except Exception as e:
            logger.warning(f"백업 시스템 상태 확인 실패: {e}")
            health_score -= 20
            components["backup_system"] = {"status": "unknown", "error": str(e)}
        
        # 모니터링 상태 (안전한 방식)
        try:
            monitoring = IntegratedMonitoringSystem()
            system_status = monitoring.get_system_status()
            
            disk_usage = system_status.get("disk_usage", 0)
            if disk_usage > 80:
                health_score -= 10
            
            components["monitoring"] = {
                "status": "active" if system_status.get("services_running") else "inactive",
                "disk_usage": disk_usage,
                "memory_usage": system_status.get("memory_usage", 0)
            }
        except Exception as e:
            logger.warning(f"모니터링 시스템 상태 확인 실패: {e}")
            health_score -= 15
            components["monitoring"] = {"status": "unknown", "error": str(e)}
        
        # 알림 상태 (안전한 방식)
        try:
            notification = get_notification_system()
            components["notifications"] = {
                "status": "configured",
                "enabled": notification.config.get("enabled", False)
            }
        except Exception as e:
            logger.warning(f"알림 시스템 상태 확인 실패: {e}")
            health_score -= 10
            components["notifications"] = {"status": "unknown", "error": str(e)}
        
        # 보안 상태 (안전한 방식)
        try:
            security_wrapper = get_safe_security_wrapper()
            security_status = await security_wrapper.get_security_status()
            security_issues_count = security_status.get("total_issues", 0)
            
            if security_issues_count > 0:
                health_score -= security_issues_count * 3  # 더 관대한 감점
            
            components["security"] = {
                "status": "warning" if security_issues_count > 0 else "secure",
                "issues_count": security_issues_count,
                "module_available": security_status.get("security_module_available", False)
            }
        except Exception as e:
            logger.warning(f"보안 시스템 상태 확인 실패: {e}")
            health_score -= 5  # 보안 모듈은 선택사항
            components["security"] = {"status": "unknown", "error": str(e)}
        
        health_status = "excellent" if health_score >= 90 else \
                       "good" if health_score >= 70 else \
                       "warning" if health_score >= 50 else "critical"
        
        return {
            "health_score": max(0, health_score),
            "health_status": health_status,
            "components": components,
            "last_check": datetime.now().isoformat(),
            "server_stability": "enhanced"
        }
        
    except Exception as e:
        logger.error(f"시스템 건강 상태 확인 오류: {e}")
        # 완전한 fallback 응답
        return {
            "health_score": 50,
            "health_status": "warning",
            "components": {
                "system": {"status": "partially_available", "error": str(e)}
            },
            "last_check": datetime.now().isoformat(),
            "server_stability": "degraded",
            "message": "시스템 상태를 완전히 확인할 수 없지만 기본 서비스는 사용 가능합니다"
        }

@app.get("/api/setup/status")
async def get_setup_status():
    """설정 상태 확인"""
    try:
        status = {
            "environment_configured": Path(".env").exists(),
            "ssl_configured": Path("ssl_certificates").exists() and len(list(Path("ssl_certificates").glob("*"))) > 0,
            "backup_configured": len(get_backup_manager().backup_configs) > 0,
            "notifications_configured": get_notification_system().config.get("enabled", False),
            "scheduler_configured": Path("backup_schedule_config.json").exists(),
            "monitoring_configured": True  # 기본적으로 활성화
        }
        
        total_components = len(status)
        configured_components = sum(status.values())
        setup_progress = (configured_components / total_components) * 100
        
        return {
            "setup_progress": round(setup_progress, 1),
            "configured_components": configured_components,
            "total_components": total_components,
            "components": status,
            "next_steps": [
                step for step, configured in [
                    ("환경변수 설정", status["environment_configured"]),
                    ("SSL 인증서 설정", status["ssl_configured"]),
                    ("백업 설정", status["backup_configured"]),
                    ("알림 설정", status["notifications_configured"]),
                    ("스케줄러 설정", status["scheduler_configured"])
                ] if not configured
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"설정 상태 확인 오류: {str(e)}")

# 서버 시작 시 파일 생성 및 안전 초기화
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 안전한 초기화"""
    try:
        await create_dashboard_files()
        
        # 보안 모듈 단계적 초기화 (비동기)
        try:
            security_wrapper = get_safe_security_wrapper()
            # 백그라운드에서 느리게 초기화
            asyncio.create_task(security_wrapper._initialize_security_module())
        except Exception as e:
            logger.warning(f"보안 모듈 초기화 실패 (서버는 계속 실행): {e}")
        
        safe_print("🚀 백업 대시보드 서버 시작됨")
        
    except Exception as e:
        logger.error(f"서버 초기화 오류: {e}")
        # 초기화 실패에도 서버는 시작됨
        safe_print("⚠️ 서버 초기화 일부 실패 - 기본 기능만 사용 가능")

def find_available_port(start_port=8888, max_attempts=10):
    """사용 가능한 포트 찾기"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return None

def run_server_with_recovery():
    """서버 실행 및 자동 복구"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # 사용 가능한 포트 찾기
            port = find_available_port()
            if not port:
                safe_print("❌ 사용 가능한 포트를 찾을 수 없습니다")
                return False
            
            safe_print(f"🚀 Two Very Auto 백업 대시보드 서버 시작")
            safe_print(f"🌐 접속 주소: http://127.0.0.1:{port}")
            safe_print(f"📁 API 문서: http://127.0.0.1:{port}/docs")
            safe_print("=" * 60)
            
            # 서버 실행
            uvicorn.run(
                "dashboard_server:app",
                host="127.0.0.1",
                port=port,
                reload=False,
                log_level="info"
            )
            
            # 정상 종료
            return True
            
        except KeyboardInterrupt:
            safe_print("\n⏹️ 서버를 종료합니다")
            return True
            
        except Exception as e:
            retry_count += 1
            safe_print(f"⚠️ 서버 실행 오류 ({retry_count}/{max_retries}): {e}")
            
            if retry_count < max_retries:
                safe_print(f"🔄 5초 후 재시도합니다...")
                import time
                time.sleep(5)
            else:
                safe_print("❌ 서버 실행 실패 - 최대 재시도 횟수를 초과했습니다")
                return False
    
    return False

if __name__ == "__main__":
    success = run_server_with_recovery()
    if not success:
        safe_print("❌ 대시보드 서버를 시작할 수 없습니다")
        safe_print("🛠️ 대안 방안:")
        safe_print("   1. run_dashboard.py 실행: python run_dashboard.py")
        safe_print("   2. 수동 포트 지정: uvicorn dashboard_server:app --port 8889")
        exit(1)