#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Progress Display System
향상된 진행률 표시 시스템 - 실시간 진행률 바, 단계별 상태, ETA 계산
"""

import time
import sys
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Callable, Any
from dataclasses import dataclass
from enum import Enum
import asyncio

class ProgressStyle(Enum):
    """진행률 바 스타일"""
    SIMPLE = "simple"           # ████████░░░░
    DETAILED = "detailed"       # [████████░░░░] 80%
    PERCENTAGE = "percentage"   # 80% Complete
    ETA = "eta"                # 80% ETA: 2m 30s

@dataclass
class ProgressState:
    """진행률 상태"""
    current: int
    total: int
    start_time: float
    message: str
    substeps: List[str] = None
    
    @property
    def percentage(self) -> float:
        return (self.current / self.total * 100) if self.total > 0 else 0
    
    @property
    def eta_seconds(self) -> Optional[float]:
        if self.current <= 0:
            return None
        elapsed = time.time() - self.start_time
        rate = self.current / elapsed
        remaining = self.total - self.current
        return remaining / rate if rate > 0 else None

class EnhancedProgress:
    """향상된 진행률 표시기"""
    
    def __init__(self, total: int, message: str = "", style: ProgressStyle = ProgressStyle.DETAILED):
        self.state = ProgressState(0, total, time.time(), message)
        self.style = style
        self.width = 40
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def start(self):
        """진행률 표시 시작"""
        self.running = True
        self.thread = threading.Thread(target=self._display_loop)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        """진행률 표시 중지"""
        self.running = False
        if self.thread:
            self._stop_event.set()
            self.thread.join(timeout=1.0)
        self._clear_line()
        
    def update(self, current: int, message: str = None):
        """진행률 업데이트"""
        self.state.current = min(current, self.state.total)
        if message:
            self.state.message = message
            
    def add_substep(self, step: str):
        """서브 단계 추가"""
        if self.state.substeps is None:
            self.state.substeps = []
        self.state.substeps.append(step)
        
    def _display_loop(self):
        """표시 루프"""
        while self.running and not self._stop_event.is_set():
            self._render()
            self._stop_event.wait(0.1)  # 100ms 간격
    
    def _render(self):
        """진행률 렌더링"""
        line = self._format_progress_line()
        self._update_line(line)
    
    def _format_progress_line(self) -> str:
        """진행률 라인 포맷팅"""
        if self.style == ProgressStyle.SIMPLE:
            return self._format_simple()
        elif self.style == ProgressStyle.DETAILED:
            return self._format_detailed()
        elif self.style == ProgressStyle.PERCENTAGE:
            return self._format_percentage()
        elif self.style == ProgressStyle.ETA:
            return self._format_eta()
        else:
            return self._format_detailed()
    
    def _format_simple(self) -> str:
        """간단한 형태"""
        filled = int(self.width * self.state.current / self.state.total) if self.state.total > 0 else 0
        bar = "█" * filled + "░" * (self.width - filled)
        return f"{bar} {self.state.message}"
    
    def _format_detailed(self) -> str:
        """상세한 형태"""
        filled = int(self.width * self.state.current / self.state.total) if self.state.total > 0 else 0
        bar = "█" * filled + "░" * (self.width - filled)
        percentage = self.state.percentage
        return f"[{bar}] {percentage:5.1f}% {self.state.message} ({self.state.current}/{self.state.total})"
    
    def _format_percentage(self) -> str:
        """퍼센트 형태"""
        return f"{self.state.percentage:5.1f}% Complete - {self.state.message}"
    
    def _format_eta(self) -> str:
        """ETA 포함 형태"""
        filled = int(self.width * self.state.current / self.state.total) if self.state.total > 0 else 0
        bar = "█" * filled + "░" * (self.width - filled)
        percentage = self.state.percentage
        
        eta_str = ""
        if self.state.eta_seconds:
            eta_td = timedelta(seconds=int(self.state.eta_seconds))
            eta_str = f" ETA: {eta_td}"
            
        return f"[{bar}] {percentage:5.1f}%{eta_str} {self.state.message}"
    
    def _update_line(self, line: str):
        """라인 업데이트"""
        # 줄 길이를 터미널 너비로 제한
        max_width = 120
        if len(line) > max_width:
            line = line[:max_width-3] + "..."
            
        # 이전 라인 지우고 새 라인 출력
        sys.stdout.write(f"\r{line}")
        sys.stdout.flush()
    
    def _clear_line(self):
        """라인 지우기"""
        sys.stdout.write("\r" + " " * 120 + "\r")
        sys.stdout.flush()

class MultiStepProgress:
    """다단계 진행률 표시기"""
    
    def __init__(self, steps: List[str], style: ProgressStyle = ProgressStyle.ETA):
        self.steps = steps
        self.current_step = 0
        self.style = style
        self.progress: Optional[EnhancedProgress] = None
        self.step_start_times = {}
        
    def start_step(self, step_index: int, substeps: int = 100, message: str = ""):
        """단계 시작"""
        if step_index >= len(self.steps):
            return
            
        self.current_step = step_index
        step_name = self.steps[step_index]
        full_message = f"Step {step_index + 1}/{len(self.steps)}: {step_name} {message}".strip()
        
        if self.progress:
            self.progress.stop()
            
        self.progress = EnhancedProgress(substeps, full_message, self.style)
        self.progress.start()
        self.step_start_times[step_index] = time.time()
        
    def update_step(self, current: int, message: str = ""):
        """현재 단계 업데이트"""
        if self.progress:
            step_name = self.steps[self.current_step]
            full_message = f"Step {self.current_step + 1}/{len(self.steps)}: {step_name} {message}".strip()
            self.progress.update(current, full_message)
            
    def complete_step(self):
        """현재 단계 완료"""
        if self.progress:
            self.progress.update(self.progress.state.total, "완료")
            time.sleep(0.5)  # 완료 상태를 잠깐 보여줌
            self.progress.stop()
            
    def finish(self):
        """전체 완료"""
        if self.progress:
            self.progress.stop()
        print()  # 새 줄로 이동

# 컨텍스트 매니저
class ProgressContext:
    """진행률 컨텍스트 매니저"""
    
    def __init__(self, total: int, message: str = "", style: ProgressStyle = ProgressStyle.ETA):
        self.progress = EnhancedProgress(total, message, style)
        
    def __enter__(self):
        self.progress.start()
        return self.progress
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.progress.update(self.progress.state.total, "오류 발생")
        else:
            self.progress.update(self.progress.state.total, "완료")
        time.sleep(0.3)
        self.progress.stop()
        print()

# 비동기 진행률 표시
class AsyncProgress:
    """비동기 진행률 표시기"""
    
    def __init__(self, total: int, message: str = "", style: ProgressStyle = ProgressStyle.ETA):
        self.progress = EnhancedProgress(total, message, style)
        self.task: Optional[asyncio.Task] = None
        
    async def __aenter__(self):
        self.progress.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.progress.update(self.progress.state.total, "오류 발생")
        else:
            self.progress.update(self.progress.state.total, "완료")
        await asyncio.sleep(0.3)
        self.progress.stop()
        print()
        
    def update(self, current: int, message: str = ""):
        """진행률 업데이트"""
        self.progress.update(current, message)

# 편의 함수들
def show_progress(iterable, message: str = "", style: ProgressStyle = ProgressStyle.ETA):
    """이터러블에 대한 진행률 표시"""
    items = list(iterable)
    total = len(items)
    
    with ProgressContext(total, message, style) as progress:
        for i, item in enumerate(items, 1):
            yield item
            progress.update(i)

def timed_operation(func: Callable, total_steps: int, message: str = "") -> Any:
    """함수 실행을 진행률과 함께 표시"""
    with ProgressContext(total_steps, message) as progress:
        # 간단한 시뮬레이션 - 실제로는 func 내부에서 progress.update 호출
        for i in range(total_steps):
            time.sleep(0.1)  # 시뮬레이션
            progress.update(i + 1, f"처리 중... {i + 1}")
        return func() if callable(func) else func

if __name__ == "__main__":
    # 테스트 코드
    print("Enhanced Progress System 테스트")
    
    # 기본 진행률 테스트
    print("\n1. 기본 진행률 바:")
    with ProgressContext(100, "파일 처리", ProgressStyle.ETA) as progress:
        for i in range(101):
            progress.update(i, f"파일 {i}/100 처리 중")
            time.sleep(0.02)
    
    # 다단계 진행률 테스트
    print("\n2. 다단계 진행률:")
    multi = MultiStepProgress(["초기화", "데이터 로드", "처리", "정리"])
    
    multi.start_step(0, 50, "설정 파일 로드")
    for i in range(51):
        multi.update_step(i, f"설정 {i}/50")
        time.sleep(0.01)
    multi.complete_step()
    
    multi.start_step(1, 100, "데이터 읽기")  
    for i in range(101):
        multi.update_step(i, f"레코드 {i}/100")
        time.sleep(0.005)
    multi.complete_step()
    
    multi.finish()
    
    print("\n테스트 완료!")