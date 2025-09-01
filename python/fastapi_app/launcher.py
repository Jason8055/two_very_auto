#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Two Very Auto - 원클릭 GUI 런처
사용자 친화적인 그래픽 인터페이스로 서버 실행
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
import webbrowser
import threading
import time
from pathlib import Path

class TwoVeryAutoLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎯 Two Very Auto - 서버 런처")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # 현재 실행 중인 서버 프로세스
        self.server_process = None
        self.is_running = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI 구성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 제목
        title_label = ttk.Label(
            main_frame, 
            text="🎯 Two Very Auto",
            font=("맑은 고딕", 20, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="실시간 바카라 페어 감지 및 알림 시스템",
            font=("맑은 고딕", 10)
        )
        subtitle_label.pack(pady=(0, 20))
        
        # 상태 표시
        self.status_frame = ttk.LabelFrame(main_frame, text="서버 상태", padding="10")
        self.status_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.status_label = ttk.Label(
            self.status_frame,
            text="🔴 서버 정지됨",
            font=("맑은 고딕", 12, "bold")
        )
        self.status_label.pack()
        
        self.url_label = ttk.Label(
            self.status_frame,
            text="서버가 실행되면 URL이 표시됩니다",
            font=("맑은 고딕", 9),
            foreground="gray"
        )
        self.url_label.pack()
        
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 서버 시작/종료 버튼
        self.start_button = ttk.Button(
            button_frame,
            text="🚀 서버 시작",
            command=self.toggle_server,
            style="Accent.TButton"
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 브라우저 열기 버튼
        self.browser_button = ttk.Button(
            button_frame,
            text="🌐 브라우저 열기",
            command=self.open_browser,
            state=tk.DISABLED
        )
        self.browser_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 종료 버튼
        exit_button = ttk.Button(
            button_frame,
            text="❌ 종료",
            command=self.on_closing
        )
        exit_button.pack(side=tk.RIGHT)
        
        # 로그 출력 영역
        log_frame = ttk.LabelFrame(main_frame, text="서버 로그", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 로그 텍스트 위젯
        self.log_text = tk.Text(
            log_frame,
            height=10,
            font=("Consolas", 9),
            bg="black",
            fg="green"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 스크롤바
        scrollbar = ttk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
        
        # 초기 로그 메시지
        self.log_message("Two Very Auto 런처 시작됨")
        self.log_message("🎯 서버 시작 버튼을 클릭하세요")
        
        # 윈도우 종료 이벤트 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def log_message(self, message):
        """로그 메시지 출력"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\\n"
        
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.root.update()
    
    def toggle_server(self):
        """서버 시작/종료 토글"""
        if not self.is_running:
            self.start_server()
        else:
            self.stop_server()
    
    def start_server(self):
        """서버 시작"""
        try:
            self.log_message("🚀 서버 시작 중...")
            
            # main.py 파일 경로 확인
            main_py = Path(__file__).parent / "main.py"
            if not main_py.exists():
                messagebox.showerror("오류", f"main.py 파일을 찾을 수 없습니다: {main_py}")
                return
            
            # 서버 프로세스 시작
            self.server_process = subprocess.Popen(
                [sys.executable, str(main_py)],
                cwd=str(main_py.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # 콘솔 창 숨기기
            )
            
            self.is_running = True
            self.update_ui_running()
            
            # 서버 출력 모니터링 (별도 스레드)
            threading.Thread(target=self.monitor_server, daemon=True).start()
            
            # 3초 후 브라우저 자동 열기
            threading.Thread(target=self.auto_open_browser, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"❌ 서버 시작 실패: {e}")
            messagebox.showerror("서버 시작 실패", str(e))
    
    def stop_server(self):
        """서버 종료"""
        if self.server_process:
            self.log_message("🛑 서버 종료 중...")
            self.server_process.terminate()
            self.server_process.wait()
            self.server_process = None
        
        self.is_running = False
        self.update_ui_stopped()
        self.log_message("✅ 서버가 종료되었습니다")
    
    def monitor_server(self):
        """서버 출력 모니터링"""
        while self.is_running and self.server_process:
            try:
                line = self.server_process.stdout.readline()
                if line:
                    # 중요한 메시지만 로그에 표시
                    if any(keyword in line.lower() for keyword in 
                           ['error', 'warning', 'uvicorn running', '서버', 'started']):
                        self.log_message(line.strip())
                elif self.server_process.poll() is not None:
                    break
            except:
                break
    
    def auto_open_browser(self):
        """3초 후 브라우저 자동 열기"""
        time.sleep(3)
        if self.is_running:
            self.open_browser()
    
    def open_browser(self):
        """브라우저 열기"""
        try:
            webbrowser.open("http://127.0.0.1:8000")
            self.log_message("🌐 브라우저에서 페이지를 열었습니다")
        except Exception as e:
            self.log_message(f"❌ 브라우저 열기 실패: {e}")
    
    def update_ui_running(self):
        """실행 중 UI 업데이트"""
        self.status_label.config(text="🟢 서버 실행 중", foreground="green")
        self.url_label.config(text="http://127.0.0.1:8000", foreground="blue")
        self.start_button.config(text="🛑 서버 종료")
        self.browser_button.config(state=tk.NORMAL)
    
    def update_ui_stopped(self):
        """정지 중 UI 업데이트"""
        self.status_label.config(text="🔴 서버 정지됨", foreground="red")
        self.url_label.config(text="서버가 실행되면 URL이 표시됩니다", foreground="gray")
        self.start_button.config(text="🚀 서버 시작")
        self.browser_button.config(state=tk.DISABLED)
    
    def on_closing(self):
        """프로그램 종료 처리"""
        if self.is_running:
            result = messagebox.askyesno(
                "종료 확인", 
                "서버가 실행 중입니다. 종료하시겠습니까?"
            )
            if result:
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """런처 실행"""
        try:
            # 테마 설정 (가능한 경우)
            style = ttk.Style()
            if "vista" in style.theme_names():
                style.theme_use("vista")
        except:
            pass
        
        self.root.mainloop()

if __name__ == "__main__":
    # Windows 인코딩 설정
    if sys.platform == "win32":
        os.system("chcp 65001 >nul 2>&1")
    
    launcher = TwoVeryAutoLauncher()
    launcher.run()