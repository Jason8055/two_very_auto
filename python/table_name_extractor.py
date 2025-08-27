#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
테이블명 추출 시스템
패킷 파일명과 테이블ID에서 한국어 테이블명을 추출하고 매핑
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from korean_encoding_fix import setup_korean_encoding, safe_print
from datetime import datetime

# 한국어 인코딩 설정
setup_korean_encoding()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TableNameExtractor:
    """테이블명 추출 및 매핑 시스템"""
    
    def __init__(self):
        """초기화"""
        self.table_mappings = self._initialize_table_mappings()
        self.name_patterns = self._initialize_name_patterns()
        
        logger.info("[Table Name Extractor] 테이블명 추출 시스템 초기화 완료")
    
    def _initialize_table_mappings(self) -> Dict[str, Dict[str, str]]:
        """테이블 매핑 정보 초기화"""
        return {
            # Evolution Gaming 기본 바카라 테이블
            'baccarat': {
                'A': '바카라 A',
                'B': '바카라 B',
                'C': '바카라 C',
                'D': '바카라 D',
                'E': '바카라 E',
                'F': '바카라 F',
                'G': '바카라 G',
                'H': '바카라 H',
                'I': '바카라 I',
                'J': '바카라 J',
                'K': '바카라 K',
                'L': '바카라 L',
                'M': '바카라 M',
                'N': '바카라 N',
                'O': '바카라 O',
                'P': '바카라 P',
                'Q': '바카라 Q',
                'R': '바카라 R',
                'S': '바카라 S',
                'T': '바카라 T',
                'U': '바카라 U',
                'V': '바카라 V',
                'W': '바카라 W',
                'X': '바카라 X',
                'Y': '바카라 Y',
                'Z': '바카라 Z'
            },
            
            # 스피드 바카라 테이블
            'speed_baccarat': {
                'A': '스피드 바카라 A',
                'B': '스피드 바카라 B',
                'C': '스피드 바카라 C',
                'D': '스피드 바카라 D',
                'E': '스피드 바카라 E',
                'F': '스피드 바카라 F',
                'G': '스피드 바카라 G',
                'H': '스피드 바카라 H',
                'I': '스피드 바카라 I',
                'J': '스피드 바카라 J',
                'N': '스피드 바카라 N',
                'Q': '스피드 바카라 Q',
                'R': '스피드 바카라 R',
                'S': '스피드 바카라 S',
                'T': '스피드 바카라 T',
                'U': '스피드 바카라 U',
                'V': '스피드 바카라 V',
                'W': '스피드 바카라 W',
                'X': '스피드 바카라 X',
                'Z': '스피드 바카라 Z',
                '1': '스피드 바카라 1',
                '2': '스피드 바카라 2',
                '3': '스피드 바카라 3',
                '5': '스피드 바카라 5',
                '6': '스피드 바카라 6',
                '7': '스피드 바카라 7',
                '8': '스피드 바카라 8',
                '9': '스피드 바카라 9',
                '10': '스피드 바카라 10',
                '11': '스피드 바카라 11',
                '12': '스피드 바카라 12'
            },
            
            # 본자이 스피드 바카라 테이블
            'bonsai_speed': {
                'A': '본자이 스피드 바카라 A',
                'B': '본자이 스피드 바카라 B',
                'C': '본자이 스피드 바카라 C'
            },
            
            # 엠퍼러 스피드 바카라 테이블
            'emperor_speed': {
                'A': '엠퍼러 스피드 바카라 A',
                'B': '엠퍼러 스피드 바카라 B',
                'C': '엠퍼러 스피드 바카라 C',
                'D': '엠퍼러 스피드 바카라 D'
            },
            
            # 코리안 스피드 바카라 테이블
            'korean_speed': {
                'A': '코리안 스피드 바카라 A',
                'B': '코리안 스피드 바카라 B',
                'C': '코리안 스피드 바카라 C',
                'D': '코리안 스피드 바카라 D',
                'E': '코리안 스피드 바카라 E'
            }
        }
    
    def _initialize_name_patterns(self) -> List[Dict[str, str]]:
        """파일명 패턴 정의"""
        return [
            {
                'pattern': r'^바카라 ([A-Z])_\d+\.txt$',
                'type': 'baccarat',
                'format': '바카라 {table_id}'
            },
            {
                'pattern': r'^스피드 바카라 ([A-Z0-9]+)_\d+\.txt$',
                'type': 'speed_baccarat',
                'format': '스피드 바카라 {table_id}'
            },
            {
                'pattern': r'^본자이 스피드 바카라 ([A-Z])_\d+\.txt$',
                'type': 'bonsai_speed',
                'format': '본자이 스피드 바카라 {table_id}'
            },
            {
                'pattern': r'^엠퍼러 스피드 바카라 ([A-Z])_\d+\.txt$',
                'type': 'emperor_speed',
                'format': '엠퍼러 스피드 바카라 {table_id}'
            },
            {
                'pattern': r'^코리안 스피드 바카라 ([A-Z])_\d+\.txt$',
                'type': 'korean_speed',
                'format': '코리안 스피드 바카라 {table_id}'
            }
        ]
    
    def extract_table_name_from_filename(self, filename: str) -> Optional[Dict[str, str]]:
        """
        파일명에서 테이블명 추출
        
        Args:
            filename: 패킷 파일명
            
        Returns:
            테이블 정보 딕셔너리 (name_kr, name_en, table_id, table_type)
        """
        try:
            for pattern_info in self.name_patterns:
                pattern = pattern_info['pattern']
                match = re.match(pattern, filename)
                
                if match:
                    table_id = match.group(1)
                    table_type = pattern_info['type']
                    
                    # 한국어 테이블명 생성
                    if table_type in self.table_mappings:
                        name_kr = self.table_mappings[table_type].get(table_id)
                        if name_kr:
                            return {
                                'name_kr': name_kr,
                                'name_en': f"{table_type.replace('_', ' ').title()} {table_id}",
                                'table_id': table_id,
                                'table_type': table_type,
                                'filename': filename
                            }
                    
                    # 매핑에 없으면 기본 형식 사용
                    name_kr = pattern_info['format'].format(table_id=table_id)
                    return {
                        'name_kr': name_kr,
                        'name_en': f"{table_type.replace('_', ' ').title()} {table_id}",
                        'table_id': table_id,
                        'table_type': table_type,
                        'filename': filename
                    }
            
            # 패턴에 맞지 않으면 None 반환
            return None
            
        except Exception as e:
            logger.error(f"파일명 파싱 실패 {filename}: {e}")
            return None
    
    def extract_table_name_from_packet_data(self, packet_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        패킷 데이터에서 테이블 정보 추출
        
        Args:
            packet_data: JSON 패킷 데이터
            
        Returns:
            테이블 정보 딕셔너리
        """
        try:
            if packet_data.get('type') != 'baccarat.encodedShoeState':
                return None
            
            args = packet_data.get('args', {})
            table_id = args.get('tableId', '')
            
            if not table_id:
                return None
            
            # 테이블ID를 기반으로 테이블명 추론
            table_info = self._infer_table_from_id(table_id)
            
            if table_info:
                table_info['packet_table_id'] = table_id
            
            return table_info
            
        except Exception as e:
            logger.error(f"패킷 데이터에서 테이블명 추출 실패: {e}")
            return None
    
    def _infer_table_from_id(self, table_id: str) -> Optional[Dict[str, str]]:
        """
        테이블ID에서 테이블 정보 추론
        
        Args:
            table_id: Evolution Gaming 테이블ID
            
        Returns:
            추론된 테이블 정보
        """
        try:
            # Evolution Gaming의 테이블ID 패턴 분석
            # 예: oytmvb9m1zysmc44 -> 바카라 테이블로 추론
            
            # 기본적으로는 바카라 테이블로 가정
            # 실제로는 더 복잡한 매핑 로직이 필요할 수 있음
            
            # 테이블ID의 길이나 패턴으로 구분 시도
            if len(table_id) > 10:
                # 긴 ID는 일반적으로 Evolution Gaming의 표준 바카라
                return {
                    'name_kr': '바카라 테이블',
                    'name_en': 'Baccarat Table',
                    'table_id': 'Unknown',
                    'table_type': 'baccarat',
                    'inferred': True,
                    'confidence': 0.7
                }
            
            return None
            
        except Exception as e:
            logger.error(f"테이블ID 추론 실패 {table_id}: {e}")
            return None
    
    def scan_packet_directory(self, packet_dir: str) -> Dict[str, Dict[str, str]]:
        """
        패킷 디렉토리를 스캔하여 모든 테이블명 추출
        
        Args:
            packet_dir: 패킷 디렉토리 경로
            
        Returns:
            파일명별 테이블 정보 매핑
        """
        try:
            packet_path = Path(packet_dir)
            table_info_map = {}
            
            safe_print(f"📁 패킷 디렉토리 스캔: {packet_path}")
            
            # 모든 하위 디렉토리 검색
            for date_dir in packet_path.iterdir():
                if date_dir.is_dir():
                    safe_print(f"  📂 날짜 디렉토리: {date_dir.name}")
                    
                    for packet_file in date_dir.glob("*.txt"):
                        table_info = self.extract_table_name_from_filename(packet_file.name)
                        
                        if table_info:
                            file_key = f"{date_dir.name}/{packet_file.name}"
                            table_info_map[file_key] = table_info
                            safe_print(f"    📄 {packet_file.name} → {table_info['name_kr']}")
            
            safe_print(f"✅ 총 {len(table_info_map)}개 테이블 파일 발견")
            return table_info_map
            
        except Exception as e:
            logger.error(f"패킷 디렉토리 스캔 실패: {e}")
            return {}
    
    def generate_table_metadata(self, table_info_map: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        테이블 메타데이터 생성
        
        Args:
            table_info_map: 스캔된 테이블 정보
            
        Returns:
            테이블 메타데이터
        """
        try:
            metadata = {
                'total_tables': len(table_info_map),
                'table_types': {},
                'table_mapping': {},
                'scan_timestamp': str(datetime.now())
            }
            
            # 테이블 타입별 통계
            for file_key, table_info in table_info_map.items():
                table_type = table_info.get('table_type', 'unknown')
                
                if table_type not in metadata['table_types']:
                    metadata['table_types'][table_type] = {
                        'count': 0,
                        'tables': []
                    }
                
                metadata['table_types'][table_type]['count'] += 1
                metadata['table_types'][table_type]['tables'].append({
                    'file': file_key,
                    'name_kr': table_info['name_kr'],
                    'table_id': table_info['table_id']
                })
                
                # 매핑 정보
                metadata['table_mapping'][file_key] = table_info
            
            return metadata
            
        except Exception as e:
            logger.error(f"테이블 메타데이터 생성 실패: {e}")
            return {}
    
    def save_table_metadata(self, metadata: Dict[str, Any], output_file: str) -> bool:
        """
        테이블 메타데이터를 파일로 저장
        
        Args:
            metadata: 테이블 메타데이터
            output_file: 출력 파일 경로
            
        Returns:
            저장 성공 여부
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            safe_print(f"💾 테이블 메타데이터 저장: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"메타데이터 저장 실패: {e}")
            return False
    
    def load_table_metadata(self, metadata_file: str) -> Optional[Dict[str, Any]]:
        """
        저장된 테이블 메타데이터 로드
        
        Args:
            metadata_file: 메타데이터 파일 경로
            
        Returns:
            로드된 메타데이터
        """
        try:
            if not Path(metadata_file).exists():
                return None
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            safe_print(f"📂 테이블 메타데이터 로드: {metadata_file}")
            return metadata
            
        except Exception as e:
            logger.error(f"메타데이터 로드 실패: {e}")
            return None


# 테스트 및 실행 함수
def test_table_name_extraction():
    """테이블명 추출 테스트"""
    safe_print("🧪 테이블명 추출 시스템 테스트")
    
    extractor = TableNameExtractor()
    
    # 테스트 파일명들
    test_filenames = [
        "바카라 A_08.txt",
        "스피드 바카라 1_15.txt", 
        "본자이 스피드 바카라 A_12.txt",
        "엠퍼러 스피드 바카라 C_20.txt",
        "코리안 스피드 바카라 B_09.txt",
        "알수없는파일.txt"
    ]
    
    safe_print("\n📋 파일명 테스트:")
    for filename in test_filenames:
        result = extractor.extract_table_name_from_filename(filename)
        if result:
            safe_print(f"  ✅ {filename} → {result['name_kr']}")
        else:
            safe_print(f"  ❌ {filename} → 인식 실패")
    
    # 실제 패킷 디렉토리 스캔
    packet_dir = "F:/two very auto 25.08.23/packet"
    safe_print(f"\n📁 실제 패킷 디렉토리 스캔: {packet_dir}")
    
    table_info_map = extractor.scan_packet_directory(packet_dir)
    
    if table_info_map:
        # 메타데이터 생성
        from datetime import datetime
        metadata = extractor.generate_table_metadata(table_info_map)
        
        # 메타데이터 저장
        metadata_file = "table_metadata.json"
        extractor.save_table_metadata(metadata, metadata_file)
        
        safe_print(f"\n📊 테이블 타입별 통계:")
        for table_type, info in metadata.get('table_types', {}).items():
            safe_print(f"  - {table_type}: {info['count']}개")
    
    return table_info_map


if __name__ == '__main__':
    test_table_name_extraction()