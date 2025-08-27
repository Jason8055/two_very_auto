#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
웹페이지 테이블명 통합 시스템
실시간 대시보드에 한국어 테이블명을 제공하는 API 엔드포인트 구현
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Flask, jsonify, request
from flask_cors import CORS
from korean_encoding_fix import setup_korean_encoding, safe_print
from table_name_extractor import TableNameExtractor
from packet_decoder import BaccaratPacketDecoder

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # CORS 허용


class WebTableIntegration:
    """웹페이지용 테이블명 통합 시스템"""
    
    def __init__(self):
        """초기화"""
        self.extractor = TableNameExtractor()
        self.decoder = BaccaratPacketDecoder()
        self.table_metadata = self._load_table_metadata()
        self.table_cache = {}  # 테이블명 캐시
        
        logger.info("[Web Table Integration] 웹페이지 테이블명 통합 시스템 초기화 완료")
    
    def _load_table_metadata(self) -> Dict[str, Any]:
        """저장된 테이블 메타데이터 로드"""
        try:
            metadata = self.extractor.load_table_metadata("table_metadata.json")
            if metadata:
                safe_print(f"📂 테이블 메타데이터 로드: {metadata.get('total_tables', 0)}개 테이블")
                return metadata
            else:
                safe_print("⚠️ 테이블 메타데이터 없음, 새로 생성")
                return self._generate_fresh_metadata()
        except Exception as e:
            logger.error(f"메타데이터 로드 실패: {e}")
            return {}
    
    def _generate_fresh_metadata(self) -> Dict[str, Any]:
        """새로운 테이블 메타데이터 생성"""
        try:
            # 패킷 디렉토리 스캔
            packet_dir = "F:/two very auto 25.08.23/packet"
            table_info_map = self.extractor.scan_packet_directory(packet_dir)
            
            if table_info_map:
                # 메타데이터 생성 및 저장
                metadata = self.extractor.generate_table_metadata(table_info_map)
                self.extractor.save_table_metadata(metadata, "table_metadata.json")
                return metadata
            
            return {}
        except Exception as e:
            logger.error(f"새 메타데이터 생성 실패: {e}")
            return {}
    
    def get_table_name_korean(self, table_id: str, filename: str = None) -> str:
        """
        테이블ID와 파일명으로 한국어 테이블명 반환
        
        Args:
            table_id: Evolution Gaming 테이블ID 또는 파일 기반 테이블ID
            filename: 패킷 파일명 (선택사항)
            
        Returns:
            한국어 테이블명
        """
        try:
            # 캐시 확인
            cache_key = f"{table_id}_{filename or 'unknown'}"
            if cache_key in self.table_cache:
                return self.table_cache[cache_key]
            
            korean_name = "알수없음"
            
            # 방법 1: 파일명에서 추출
            if filename:
                table_info = self.extractor.extract_table_name_from_filename(filename)
                if table_info:
                    korean_name = table_info['name_kr']
                    self.table_cache[cache_key] = korean_name
                    return korean_name
            
            # 방법 2: 메타데이터에서 검색
            if self.table_metadata.get('table_mapping'):
                for file_key, table_info in self.table_metadata['table_mapping'].items():
                    if table_info.get('table_id') == table_id or table_info.get('name_kr'):
                        korean_name = table_info['name_kr']
                        self.table_cache[cache_key] = korean_name
                        return korean_name
            
            # 방법 3: 테이블ID에서 추론
            inferred_info = self.extractor._infer_table_from_id(table_id)
            if inferred_info and inferred_info.get('confidence', 0) > 0.5:
                korean_name = inferred_info['name_kr']
            
            self.table_cache[cache_key] = korean_name
            return korean_name
            
        except Exception as e:
            logger.error(f"한국어 테이블명 조회 실패: {e}")
            return "알수없음"
    
    def enhance_stats_with_korean_names(self, stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        통계 데이터에 한국어 테이블명 추가
        
        Args:
            stats_data: 기존 통계 데이터
            
        Returns:
            한국어 테이블명이 포함된 향상된 통계 데이터
        """
        try:
            enhanced_stats = stats_data.copy()
            
            # table_breakdown에 한국어 이름 추가
            if 'table_breakdown' in enhanced_stats:
                for table_id, table_data in enhanced_stats['table_breakdown'].items():
                    if 'metadata' not in table_data:
                        table_data['metadata'] = {}
                    
                    # 한국어 테이블명 추가
                    korean_name = self.get_table_name_korean(table_id)
                    table_data['metadata']['name_kr'] = korean_name
                    table_data['metadata']['table_id'] = table_id
                    table_data['metadata']['display_name'] = f"{korean_name} ({table_id})"
            
            return enhanced_stats
            
        except Exception as e:
            logger.error(f"통계 데이터 향상 실패: {e}")
            return stats_data
    
    def get_table_list_with_korean_names(self) -> List[Dict[str, Any]]:
        """
        한국어 이름이 포함된 전체 테이블 목록 반환
        
        Returns:
            테이블 목록 (한국어명 포함)
        """
        try:
            table_list = []
            
            if self.table_metadata.get('table_mapping'):
                for file_key, table_info in self.table_metadata['table_mapping'].items():
                    table_list.append({
                        'file_key': file_key,
                        'table_id': table_info.get('table_id', 'Unknown'),
                        'name_kr': table_info.get('name_kr', '알수없음'),
                        'name_en': table_info.get('name_en', 'Unknown'),
                        'table_type': table_info.get('table_type', 'unknown'),
                        'filename': table_info.get('filename', ''),
                    })
            
            # 테이블 타입별로 정렬
            table_list.sort(key=lambda x: (x['table_type'], x['table_id']))
            
            return table_list
            
        except Exception as e:
            logger.error(f"테이블 목록 조회 실패: {e}")
            return []


# 전역 통합 시스템 인스턴스
web_integration = WebTableIntegration()


# Flask API 엔드포인트들

@app.route('/api/table-names', methods=['GET'])
def get_table_names():
    """전체 테이블명 목록 API"""
    try:
        table_list = web_integration.get_table_list_with_korean_names()
        
        return jsonify({
            'success': True,
            'total_tables': len(table_list),
            'tables': table_list,
            'table_types': list(set(t['table_type'] for t in table_list))
        })
    
    except Exception as e:
        logger.error(f"테이블명 목록 API 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/table-name/<table_id>', methods=['GET'])
def get_single_table_name(table_id):
    """단일 테이블명 조회 API"""
    try:
        filename = request.args.get('filename', None)
        korean_name = web_integration.get_table_name_korean(table_id, filename)
        
        return jsonify({
            'success': True,
            'table_id': table_id,
            'name_kr': korean_name,
            'filename': filename
        })
    
    except Exception as e:
        logger.error(f"단일 테이블명 조회 API 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/enhance-stats', methods=['POST'])
def enhance_stats():
    """통계 데이터에 한국어 테이블명 추가 API"""
    try:
        stats_data = request.json
        if not stats_data:
            return jsonify({
                'success': False,
                'error': '통계 데이터가 필요합니다'
            }), 400
        
        enhanced_stats = web_integration.enhance_stats_with_korean_names(stats_data)
        
        return jsonify({
            'success': True,
            'enhanced_stats': enhanced_stats
        })
    
    except Exception as e:
        logger.error(f"통계 향상 API 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/table-metadata', methods=['GET'])
def get_table_metadata():
    """테이블 메타데이터 조회 API"""
    try:
        return jsonify({
            'success': True,
            'metadata': web_integration.table_metadata,
            'cache_size': len(web_integration.table_cache)
        })
    
    except Exception as e:
        logger.error(f"메타데이터 조회 API 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/refresh-metadata', methods=['POST'])
def refresh_metadata():
    """테이블 메타데이터 새로고침 API"""
    try:
        # 메타데이터 새로 생성
        web_integration.table_metadata = web_integration._generate_fresh_metadata()
        web_integration.table_cache.clear()  # 캐시 초기화
        
        return jsonify({
            'success': True,
            'message': '테이블 메타데이터가 새로고침되었습니다',
            'total_tables': web_integration.table_metadata.get('total_tables', 0)
        })
    
    except Exception as e:
        logger.error(f"메타데이터 새로고침 API 실패: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크 API"""
    return jsonify({
        'status': 'healthy',
        'service': 'web-table-integration',
        'timestamp': datetime.now().isoformat(),
        'table_cache_size': len(web_integration.table_cache),
        'metadata_loaded': bool(web_integration.table_metadata)
    })


# 개발용 테스트 함수
def test_web_integration():
    """웹 통합 시스템 테스트"""
    safe_print("🧪 웹 테이블 통합 시스템 테스트")
    
    # 테이블명 조회 테스트
    test_cases = [
        ("oytmvb9m1zysmc44", "바카라 A_15.txt"),
        ("unknown_id", "스피드 바카라 1_10.txt"),
        ("test_id", None)
    ]
    
    for table_id, filename in test_cases:
        korean_name = web_integration.get_table_name_korean(table_id, filename)
        safe_print(f"  📋 {table_id} ({filename or 'No file'}) → {korean_name}")
    
    # 통계 데이터 향상 테스트
    sample_stats = {
        'table_breakdown': {
            'baccarat_a': {'games': 100, 'pairs': 12, 'pair_rate': 12.0},
            'speed_1': {'games': 85, 'pairs': 8, 'pair_rate': 9.4}
        }
    }
    
    enhanced = web_integration.enhance_stats_with_korean_names(sample_stats)
    safe_print(f"\n📊 향상된 통계 데이터:")
    for table_id, data in enhanced['table_breakdown'].items():
        metadata = data.get('metadata', {})
        safe_print(f"  - {table_id}: {metadata.get('name_kr', 'N/A')}")


if __name__ == '__main__':
    safe_print("🚀 웹 테이블 통합 시스템 시작")
    
    # 테스트 실행
    test_web_integration()
    
    # Flask 서버 시작
    safe_print("\n🌐 Flask API 서버 시작 (포트: 5558)")
    app.run(host='0.0.0.0', port=5558, debug=True)