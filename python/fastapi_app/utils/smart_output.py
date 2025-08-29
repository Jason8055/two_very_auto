#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Output System - 지능형 출력 관리 시스템
사용자 친화적 콘솔 출력 + 체계적 로깅을 결합한 출력 시스템
"""

import logging
import sys
from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict
import colorama
from colorama import Fore, Back, Style

# colorama 초기화
colorama.init()

class OutputLevel(Enum):
    """출력 레벨 정의"""
    DEBUG = "debug"
    INFO = "info" 
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class SmartOutput:
    """지능형 출력 시스템"""
    
    def __init__(self, logger_name: str = None, enable_console: bool = True):
        self.logger = logging.getLogger(logger_name or __name__)
        self.enable_console = enable_console
        
        # 아이콘 매핑 (안전한 ASCII 버전)
        self.icons = {
            OutputLevel.DEBUG: "[DEBUG]",
            OutputLevel.INFO: "[INFO]",
            OutputLevel.SUCCESS: "[OK]", 
            OutputLevel.WARNING: "[WARN]",
            OutputLevel.ERROR: "[ERROR]",
            OutputLevel.CRITICAL: "[CRIT]"
        }
        
        # 색상 매핑
        self.colors = {
            OutputLevel.DEBUG: Fore.CYAN,
            OutputLevel.INFO: Fore.BLUE,
            OutputLevel.SUCCESS: Fore.GREEN,
            OutputLevel.WARNING: Fore.YELLOW, 
            OutputLevel.ERROR: Fore.RED,
            OutputLevel.CRITICAL: Fore.MAGENTA + Style.BRIGHT
        }
    
    def _format_console_message(self, level: OutputLevel, message: str, 
                              details: Optional[Dict[str, Any]] = None) -> str:
        """콘솔용 메시지 포맷팅"""
        icon = self.icons.get(level, "ℹ️")
        color = self.colors.get(level, Fore.WHITE)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 기본 메시지
        formatted = f"{color}{icon} [{timestamp}] {message}{Style.RESET_ALL}"
        
        # 세부 정보가 있으면 추가
        if details:
            detail_lines = []
            for key, value in details.items():
                detail_lines.append(f"    {Fore.LIGHTBLACK_EX}├─ {key}: {value}{Style.RESET_ALL}")
            if detail_lines:
                formatted += "\n" + "\n".join(detail_lines)
        
        return formatted
    
    def _log_to_system(self, level: OutputLevel, message: str, 
                      details: Optional[Dict[str, Any]] = None):
        """시스템 로그에 기록"""
        log_message = message
        if details:
            log_message += f" | {details}"
        
        # 로깅 레벨 매핑
        log_levels = {
            OutputLevel.DEBUG: self.logger.debug,
            OutputLevel.INFO: self.logger.info,
            OutputLevel.SUCCESS: self.logger.info,
            OutputLevel.WARNING: self.logger.warning,
            OutputLevel.ERROR: self.logger.error,
            OutputLevel.CRITICAL: self.logger.critical
        }
        
        log_func = log_levels.get(level, self.logger.info)
        log_func(log_message)
    
    def output(self, level: OutputLevel, message: str, 
              details: Optional[Dict[str, Any]] = None,
              console_only: bool = False):
        """통합 출력 함수"""
        # 콘솔 출력
        if self.enable_console:
            console_msg = self._format_console_message(level, message, details)
            print(console_msg)
        
        # 시스템 로그 기록 (console_only가 아닌 경우)
        if not console_only:
            self._log_to_system(level, message, details)
    
    # 편의 메서드들
    def debug(self, message: str, details: Dict[str, Any] = None):
        """디버그 메시지"""
        self.output(OutputLevel.DEBUG, message, details)
    
    def info(self, message: str, details: Dict[str, Any] = None):
        """정보 메시지"""
        self.output(OutputLevel.INFO, message, details)
    
    def success(self, message: str, details: Dict[str, Any] = None):
        """성공 메시지"""
        self.output(OutputLevel.SUCCESS, message, details)
    
    def warning(self, message: str, details: Dict[str, Any] = None):
        """경고 메시지"""
        self.output(OutputLevel.WARNING, message, details)
    
    def error(self, message: str, details: Dict[str, Any] = None):
        """오류 메시지"""
        self.output(OutputLevel.ERROR, message, details)
    
    def critical(self, message: str, details: Dict[str, Any] = None):
        """치명적 오류 메시지"""
        self.output(OutputLevel.CRITICAL, message, details)
    
    def server_status(self, status: str, port: int = None, url: str = None):
        """서버 상태 전용 출력"""
        details = {}
        if port:
            details["포트"] = port
        if url:
            details["URL"] = url
        
        if "시작" in status or "running" in status.lower():
            self.success(f"서버 {status}", details)
        elif "중지" in status or "stop" in status.lower():
            self.warning(f"서버 {status}", details)
        else:
            self.info(f"서버 {status}", details)
    
    def progress(self, current: int, total: int, message: str = ""):
        """진행률 표시"""
        percentage = (current / total * 100) if total > 0 else 0
        bar_length = 20
        filled = int(bar_length * current / total) if total > 0 else 0
        
        bar = "█" * filled + "░" * (bar_length - filled)
        progress_msg = f"{message} [{bar}] {current}/{total} ({percentage:.1f}%)"
        
        self.output(OutputLevel.INFO, progress_msg, console_only=True)
    
    def section_header(self, title: str):
        """섹션 헤더 출력"""
        separator = "=" * 60
        header_msg = f"\n{separator}\n>> {title}\n{separator}"
        try:
            print(f"{Fore.CYAN}{Style.BRIGHT}{header_msg}{Style.RESET_ALL}")
        except UnicodeEncodeError:
            # 인코딩 오류 시 기본 출력
            print(header_msg)
        self.logger.info(f"=== {title} ===")

# 전역 출력 인스턴스
output = SmartOutput("two_very_auto")

# 편의 함수들
def debug(message: str, **kwargs):
    """전역 디버그 출력"""
    output.debug(message, kwargs if kwargs else None)

def info(message: str, **kwargs):
    """전역 정보 출력"""  
    output.info(message, kwargs if kwargs else None)

def success(message: str, **kwargs):
    """전역 성공 출력"""
    output.success(message, kwargs if kwargs else None)

def warning(message: str, **kwargs):
    """전역 경고 출력"""
    output.warning(message, kwargs if kwargs else None)

def error(message: str, **kwargs):
    """전역 오류 출력"""
    output.error(message, kwargs if kwargs else None)

def critical(message: str, **kwargs):
    """전역 치명적 오류 출력"""
    output.critical(message, kwargs if kwargs else None)

def server_status(status: str, **kwargs):
    """전역 서버 상태 출력"""
    output.server_status(status, **kwargs)

def progress(current: int, total: int, message: str = ""):
    """전역 진행률 출력"""
    output.progress(current, total, message)

def section_header(title: str):
    """전역 섹션 헤더 출력"""
    output.section_header(title)

# 컨텍스트별 출력 매니저
class OutputContext:
    """출력 컨텍스트 매니저"""
    
    def __init__(self, context_name: str):
        self.output = SmartOutput(f"two_very_auto.{context_name}")
        self.context_name = context_name
    
    def __enter__(self):
        section_header(f"{self.context_name} 시작")
        return self.output
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.output.error(f"{self.context_name} 중 오류 발생", {
                "오류": str(exc_val),
                "타입": exc_type.__name__
            })
        else:
            self.output.success(f"{self.context_name} 완료")

if __name__ == "__main__":
    # 테스트 코드
    section_header("Smart Output System 테스트")
    
    debug("디버그 메시지 테스트")
    info("정보 메시지 테스트", 버전="2.0.0", 상태="정상")
    success("성공 메시지 테스트", 처리건수=150, 소요시간="1.2초")  
    warning("경고 메시지 테스트", 메모리사용량="85%")
    error("오류 메시지 테스트", 오류코드="E001")
    
    server_status("시작됨", port=8080, url="http://localhost:8080")
    
    # 진행률 테스트
    for i in range(0, 101, 20):
        progress(i, 100, "파일 처리 중")
    
    # 컨텍스트 매니저 테스트
    with OutputContext("데이터베이스 초기화"):
        info("연결 설정 중...")
        success("연결 완료")