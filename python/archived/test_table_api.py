#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
테이블명 API 시스템 테스트
Flask API 서버 기능 검증
"""

import requests
import json
from korean_encoding_fix import setup_korean_encoding, safe_print
from web_table_integration import WebTableIntegration

# 한국어 인코딩 설정
setup_korean_encoding()

def test_table_integration_directly():
    """웹 테이블 통합 시스템 직접 테스트"""
    safe_print("🧪 웹 테이블 통합 시스템 직접 테스트")
    
    # 통합 시스템 생성
    integration = WebTableIntegration()
    
    # 1. 테이블명 조회 테스트
    safe_print("\n📋 테이블명 조회 테스트:")
    test_cases = [
        ("oytmvb9m1zysmc44", "바카라 A_15.txt"),
        ("unknown_id", "스피드 바카라 1_10.txt"),
        ("test_id", "본자이 스피드 바카라 A_05.txt"),
        ("another_id", None)
    ]
    
    for table_id, filename in test_cases:
        korean_name = integration.get_table_name_korean(table_id, filename)
        safe_print(f"  - {table_id} ({filename or 'No file'}) → {korean_name}")
    
    # 2. 테이블 목록 조회 테스트
    safe_print("\n📄 테이블 목록 조회 테스트:")
    table_list = integration.get_table_list_with_korean_names()
    safe_print(f"  총 {len(table_list)}개 테이블 발견")
    
    # 테이블 타입별 통계
    type_stats = {}
    for table in table_list[:10]:  # 처음 10개만 표시
        table_type = table['table_type']
        type_stats[table_type] = type_stats.get(table_type, 0) + 1
        safe_print(f"  - {table['name_kr']} ({table['table_type']})")
    
    safe_print(f"\n📊 테이블 타입별 통계:")
    for table_type, count in type_stats.items():
        safe_print(f"  - {table_type}: {count}개")
    
    # 3. 통계 데이터 향상 테스트
    safe_print("\n🔧 통계 데이터 향상 테스트:")
    sample_stats = {
        'total_games': 1500,
        'total_pairs': 180,
        'pair_rate': 12.0,
        'table_breakdown': {
            'baccarat_a': {
                'games': 400,
                'pairs': 48,
                'pair_rate': 12.0,
                'metadata': {}
            },
            'speed_1': {
                'games': 350,
                'pairs': 42,
                'pair_rate': 12.0,
                'metadata': {}
            },
            'bonsai_a': {
                'games': 300,
                'pairs': 36,
                'pair_rate': 12.0,
                'metadata': {}
            }
        }
    }
    
    enhanced_stats = integration.enhance_stats_with_korean_names(sample_stats)
    
    safe_print("  향상된 테이블 정보:")
    for table_id, table_data in enhanced_stats['table_breakdown'].items():
        metadata = table_data.get('metadata', {})
        name_kr = metadata.get('name_kr', '알수없음')
        display_name = metadata.get('display_name', table_id)
        safe_print(f"    - {table_id}: {name_kr} | 표시명: {display_name}")
    
    return True

def test_api_endpoints():
    """API 엔드포인트 테스트 (서버가 실행중일 때)"""
    base_url = "http://127.0.0.1:5558"
    
    safe_print("🌐 API 엔드포인트 테스트")
    
    # 헬스 체크
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            safe_print(f"✅ 헬스 체크: {data['status']}")
            safe_print(f"  - 서비스: {data['service']}")
            safe_print(f"  - 캐시 크기: {data['table_cache_size']}")
            safe_print(f"  - 메타데이터 로드됨: {data['metadata_loaded']}")
        else:
            safe_print(f"❌ 헬스 체크 실패: {response.status_code}")
            return False
    except Exception as e:
        safe_print(f"❌ API 서버 연결 실패: {e}")
        safe_print("  → 서버가 실행중이 아닙니다. 직접 테스트만 수행합니다.")
        return False
    
    # 테이블명 목록 조회
    try:
        response = requests.get(f"{base_url}/api/table-names", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                safe_print(f"✅ 테이블명 목록: {data['total_tables']}개")
                safe_print(f"  - 테이블 타입: {', '.join(data['table_types'])}")
            else:
                safe_print(f"❌ API 응답 오류: {data.get('error', 'Unknown')}")
        else:
            safe_print(f"❌ 테이블명 목록 조회 실패: {response.status_code}")
    except Exception as e:
        safe_print(f"❌ 테이블명 목록 API 오류: {e}")
    
    # 단일 테이블명 조회
    try:
        response = requests.get(f"{base_url}/api/table-name/test_table?filename=바카라 A_15.txt", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                safe_print(f"✅ 단일 테이블명: {data['name_kr']}")
            else:
                safe_print(f"❌ 단일 테이블명 오류: {data.get('error', 'Unknown')}")
    except Exception as e:
        safe_print(f"❌ 단일 테이블명 API 오류: {e}")
    
    # 통계 향상 테스트
    try:
        test_stats = {
            'table_breakdown': {
                'baccarat_a': {'games': 100, 'pairs': 12, 'pair_rate': 12.0},
                'speed_1': {'games': 85, 'pairs': 8, 'pair_rate': 9.4}
            }
        }
        
        response = requests.post(f"{base_url}/api/enhance-stats", 
                               json=test_stats,
                               headers={'Content-Type': 'application/json'},
                               timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                enhanced = data['enhanced_stats']
                safe_print("✅ 통계 향상 성공:")
                for table_id, table_data in enhanced['table_breakdown'].items():
                    metadata = table_data.get('metadata', {})
                    safe_print(f"  - {table_id}: {metadata.get('name_kr', 'N/A')}")
            else:
                safe_print(f"❌ 통계 향상 오류: {data.get('error', 'Unknown')}")
        else:
            safe_print(f"❌ 통계 향상 API 실패: {response.status_code}")
    except Exception as e:
        safe_print(f"❌ 통계 향상 API 오류: {e}")
    
    return True

if __name__ == '__main__':
    safe_print("🚀 테이블명 API 시스템 테스트 시작\n")
    
    # 직접 테스트 실행
    test_table_integration_directly()
    
    safe_print("\n" + "="*60 + "\n")
    
    # API 테스트 실행
    test_api_endpoints()
    
    safe_print("\n✅ 테스트 완료")