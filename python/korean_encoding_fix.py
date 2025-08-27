#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
한국어 인코딩 문제 해결 유틸리티
UTF-8 환경 설정 및 콘솔 출력 최적화
"""

import sys
import os
import locale

def setup_korean_encoding():
    """
    한국어 인코딩 환경 설정
    Windows 콘솔에서 한글 출력 문제 해결
    """
    try:
        # 1. Python 기본 인코딩을 UTF-8로 설정
        if sys.version_info >= (3, 7):
            # Python 3.7+ 에서 UTF-8 모드 활성화
            if hasattr(sys, '_enablelegacywindowsfsencoding'):
                sys._enablelegacywindowsfsencoding = False
        
        # 2. 표준 입출력 인코딩 설정
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
            sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
        
        # 3. 로케일 설정 (한국어 지원)
        try:
            locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_ALL, 'Korean_Korea.65001')  # Windows UTF-8 코드페이지
            except locale.Error:
                pass  # 로케일 설정 실패해도 계속 진행
        
        # 4. 환경 변수 설정
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'
        
        print("한국어 인코딩 설정 완료")
        return True
        
    except Exception as e:
        print(f"인코딩 설정 실패: {e}")
        return False

def safe_print(text, fallback_encoding='cp949'):
    """
    안전한 한글 출력 함수
    UTF-8 실패시 시스템 인코딩으로 폴백
    """
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            # Windows 콘솔 인코딩으로 폴백
            encoded_text = text.encode(fallback_encoding, errors='ignore').decode(fallback_encoding)
            print(encoded_text)
        except:
            # 최후 수단: ASCII 안전 문자로 변환
            ascii_text = text.encode('ascii', errors='ignore').decode('ascii')
            print(f"[한글출력실패] {ascii_text}")

def get_console_encoding():
    """현재 콘솔 인코딩 확인"""
    try:
        encoding_info = {
            'stdout_encoding': sys.stdout.encoding,
            'stderr_encoding': sys.stderr.encoding,
            'filesystem_encoding': sys.getfilesystemencoding(),
            'default_encoding': sys.getdefaultencoding(),
            'locale_encoding': locale.getpreferredencoding()
        }
        return encoding_info
    except:
        return {}

if __name__ == "__main__":
    print("=== 한국어 인코딩 테스트 ===")
    
    # 현재 인코딩 상태 확인
    print("설정 전 인코딩 상태:")
    encodings = get_console_encoding()
    for key, value in encodings.items():
        print(f"  {key}: {value}")
    
    # 한국어 인코딩 설정 적용
    setup_korean_encoding()
    
    # 설정 후 상태 확인
    print("\n설정 후 인코딩 상태:")
    encodings = get_console_encoding()
    for key, value in encodings.items():
        print(f"  {key}: {value}")
    
    # 한글 출력 테스트
    print("\n=== 한글 출력 테스트 ===")
    test_texts = [
        "✅ 페어 감지 성공",
        "⚠️ 경고 메시지",  
        "🎯 Two Very Auto v2.0",
        "데이터베이스 초기화 완료",
        "바카라 모니터링 시스템"
    ]
    
    for text in test_texts:
        safe_print(text)
    
    print("\n한국어 인코딩 설정 및 테스트 완료")