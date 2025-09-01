#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Two Very Auto - EXE 런처
BAT 파일을 자동으로 실행하는 EXE 파일
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox
import webbrowser
import time
import threading
from pathlib import Path

class ExeLauncher:
    def __init__(self):
        # 현재 EXE 파일의 위치 기준으로 BAT 파일 경로 설정
        if getattr(sys, 'frozen', False):
            # PyInstaller로 컴파일된 경우
            self.exe_dir = Path(sys.executable).parent
        else:
            # 스크립트 실행의 경우
            self.exe_dir = Path(__file__).parent.parent
        
        # BAT 파일들 경로
        self.bat_files = {
            'detailed': self.exe_dir / '🚀 서버 시작.bat',
            'quick': self.exe_dir / 'python' / 'fastapi_app' / '빠른_서버_시작.bat',
            'current': self.exe_dir / 'python' / 'fastapi_app' / 'main.py'
        }
        
        self.create_gui()
    
    def create_gui(self):
        """간단한 GUI 생성"""
        self.root = tk.Tk()
        self.root.title("🎯 Two Very Auto - 서버 런처")
        self.root.geometry("450x300")
        self.root.resizable(False, False)
        
        # 아이콘 설정 (가능한 경우)
        try:
            self.root.iconbitmap(self.exe_dir / "icon.ico")
        except:
            pass
        
        # 메인 프레임
        main_frame = tk.Frame(self.root, bg='#2b3035', pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 제목
        title_label = tk.Label(
            main_frame,
            text="🎯 Two Very Auto",
            font=("맑은 고딕", 18, "bold"),
            bg='#2b3035',
            fg='#4ecdc4'
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = tk.Label(
            main_frame,
            text="실시간 바카라 페어 감지 및 알림 시스템",
            font=("맑은 고딕", 10),
            bg='#2b3035',
            fg='#ffffff'
        )
        subtitle_label.pack(pady=(0, 30))
        
        # 버튼들
        btn_frame = tk.Frame(main_frame, bg='#2b3035')
        btn_frame.pack(pady=20)
        
        # 즉시 실행 버튼 (가장 큰 버튼)
        instant_btn = tk.Button(
            btn_frame,
            text="🚀 즉시 서버 실행",
            font=("맑은 고딕", 14, "bold"),
            bg='#4ecdc4',
            fg='white',
            relief='flat',
            padx=30,
            pady=15,
            command=self.instant_launch
        )
        instant_btn.pack(pady=10)
        
        # 다른 옵션들
        options_frame = tk.Frame(btn_frame, bg='#2b3035')
        options_frame.pack(pady=20)
        
        detailed_btn = tk.Button(
            options_frame,
            text="📋 상세 실행",
            font=("맑은 고딕", 10),
            bg='#45b7d1',
            fg='white',
            relief='flat',
            padx=20,
            pady=10,
            command=self.detailed_launch
        )
        detailed_btn.pack(side=tk.LEFT, padx=5)
        
        quick_btn = tk.Button(
            options_frame,
            text="⚡ 빠른 실행",
            font=("맑은 고딕", 10),
            bg='#ff6b6b',
            fg='white',
            relief='flat',
            padx=20,
            pady=10,
            command=self.quick_launch
        )
        quick_btn.pack(side=tk.LEFT, padx=5)
        
        # 정보 표시
        info_frame = tk.Frame(main_frame, bg='#2b3035')
        info_frame.pack(pady=30)
        
        info_label = tk.Label(
            info_frame,
            text="💡 서버 실행 후 자동으로 브라우저가 열립니다\n🌐 주소: http://127.0.0.1:8000",
            font=("맑은 고딕", 9),
            bg='#2b3035',
            fg='#cccccc',
            justify=tk.CENTER
        )
        info_label.pack()
        
        # 종료 버튼
        exit_btn = tk.Button(
            main_frame,
            text="❌ 종료",
            font=("맑은 고딕", 9),
            bg='#666666',
            fg='white',
            relief='flat',
            padx=15,
            pady=5,
            command=self.root.quit
        )
        exit_btn.pack(pady=20)
    
    def instant_launch(self):
        """즉시 실행 - 가장 간단한 방법"""
        self.show_launching_message()
        threading.Thread(target=self._launch_python_direct, daemon=True).start()
    
    def detailed_launch(self):
        """상세 실행 - 풀 기능 BAT 파일 실행"""
        self.show_launching_message()
        threading.Thread(target=self._launch_bat_file, args=(self.bat_files['detailed'],), daemon=True).start()
    
    def quick_launch(self):
        """빠른 실행 - 간단 BAT 파일 실행"""
        self.show_launching_message()
        threading.Thread(target=self._launch_bat_file, args=(self.bat_files['quick'],), daemon=True).start()
    
    def show_launching_message(self):
        """실행 중 메시지 표시"""
        self.launch_window = tk.Toplevel(self.root)
        self.launch_window.title("서버 시작 중...")
        self.launch_window.geometry("300x150")
        self.launch_window.resizable(False, False)
        self.launch_window.configure(bg='#2b3035')
        
        # 창을 화면 중앙에 위치
        self.launch_window.transient(self.root)
        self.launch_window.grab_set()
        
        msg_frame = tk.Frame(self.launch_window, bg='#2b3035')
        msg_frame.pack(expand=True, fill=tk.BOTH)
        
        msg_label = tk.Label(
            msg_frame,
            text="🚀 서버 시작 중...\n\n잠시만 기다려주세요",
            font=("맑은 고딕", 12),
            bg='#2b3035',
            fg='#4ecdc4',
            justify=tk.CENTER
        )
        msg_label.pack(expand=True)
        
        # 3초 후 자동으로 창 닫기 및 브라우저 열기
        self.launch_window.after(3000, self._after_launch)
    
    def _launch_python_direct(self):
        """Python 스크립트 직접 실행"""
        try:
            main_py = self.bat_files['current']
            if main_py.exists():
                # Python 스크립트 직접 실행
                subprocess.Popen(
                    [sys.executable, str(main_py)],
                    cwd=str(main_py.parent),
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                self._show_error(f"main.py 파일을 찾을 수 없습니다: {main_py}")
        except Exception as e:
            self._show_error(f"서버 실행 실패: {e}")
    
    def _launch_bat_file(self, bat_path):
        """BAT 파일 실행"""
        try:
            if bat_path.exists():
                subprocess.Popen(
                    str(bat_path),
                    cwd=str(bat_path.parent),
                    shell=True
                )
            else:
                self._show_error(f"BAT 파일을 찾을 수 없습니다: {bat_path}")
        except Exception as e:
            self._show_error(f"BAT 파일 실행 실패: {e}")
    
    def _after_launch(self):
        """실행 후 처리"""
        try:
            self.launch_window.destroy()
            # 브라우저 자동 열기
            webbrowser.open("http://127.0.0.1:8000")
            # 런처 창 최소화
            self.root.iconify()
        except Exception as e:
            self._show_error(f"브라우저 열기 실패: {e}")
    
    def _show_error(self, message):
        """에러 메시지 표시"""
        if hasattr(self, 'launch_window'):
            try:
                self.launch_window.destroy()
            except:
                pass
        messagebox.showerror("오류", message)
    
    def run(self):
        """런처 실행"""
        self.root.mainloop()

def main():
    """메인 함수"""
    try:
        # Windows 인코딩 설정
        if sys.platform == "win32":
            os.system("chcp 65001 >nul 2>&1")
        
        # GUI 없이 바로 실행 옵션 (명령행 인수)
        if len(sys.argv) > 1:
            if sys.argv[1] == "--direct":
                # 직접 실행 모드
                exe_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent.parent
                main_py = exe_dir / 'python' / 'fastapi_app' / 'main.py'
                
                if main_py.exists():
                    subprocess.run([sys.executable, str(main_py)], cwd=str(main_py.parent))
                else:
                    print(f"오류: main.py 파일을 찾을 수 없습니다: {main_py}")
                return
        
        # GUI 모드
        launcher = ExeLauncher()
        launcher.run()
        
    except Exception as e:
        messagebox.showerror("런처 오류", f"예상치 못한 오류가 발생했습니다:\n{e}")

if __name__ == "__main__":
    main()