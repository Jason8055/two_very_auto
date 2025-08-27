#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Room Information System
실제 카지노 환경에 맞는 정확한 방명 정보 시스템
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedRoomManager:
    """향상된 방명 정보 관리자"""
    
    def __init__(self, data_file_path: str = "baccarat_data.json"):
        self.data_file_path = Path(data_file_path)
        
        # 실제 카지노 방명 정보 (ID → 실제 방명 매핑)
        self.room_mapping = {
            'table_001': {
                'room_id': 'table_001',
                'display_name': '프리미엄 홀 A',
                'korean_name': '프리미엄 홀 A',
                'english_name': 'Premium Hall A',
                'room_type': '일반',
                'vip_level': 'Standard',
                'betting_limits': {
                    'min': 10000,
                    'max': 100000,
                    'display': '1만~10만원'
                },
                'features': ['일반 접근', '표준 서비스', '기본 딜러'],
                'location': '메인플로어 1층',
                'capacity': 8,
                'description': '일반 고객을 위한 표준 바카라 테이블'
            },
            'table_002': {
                'room_id': 'table_002',
                'display_name': '프리미엄 홀 B',
                'korean_name': '프리미엄 홀 B',
                'english_name': 'Premium Hall B',
                'room_type': '일반',
                'vip_level': 'Standard',
                'betting_limits': {
                    'min': 10000,
                    'max': 100000,
                    'display': '1만~10만원'
                },
                'features': ['일반 접근', '표준 서비스', '기본 딜러'],
                'location': '메인플로어 1층',
                'capacity': 8,
                'description': '일반 고객을 위한 표준 바카라 테이블'
            },
            'table_003': {
                'room_id': 'table_003',
                'display_name': '골드 라운지',
                'korean_name': '골드 라운지',
                'english_name': 'Gold Lounge',
                'room_type': '프리미엄',
                'vip_level': 'Gold',
                'betting_limits': {
                    'min': 20000,
                    'max': 200000,
                    'display': '2만~20만원'
                },
                'features': ['골드 멤버 우선', '프리미엄 서비스', '숙련된 딜러'],
                'location': '메인플로어 2층',
                'capacity': 6,
                'description': '프리미엄 고객을 위한 고급 바카라 테이블'
            },
            'table_004': {
                'room_id': 'table_004',
                'display_name': 'VIP 살롱 다이아몬드',
                'korean_name': 'VIP 살롱 다이아몬드',
                'english_name': 'VIP Salon Diamond',
                'room_type': 'VIP',
                'vip_level': 'Diamond',
                'betting_limits': {
                    'min': 100000,
                    'max': 1000000,
                    'display': '10만~100만원'
                },
                'features': ['VIP 전용', '개인 서비스', '마스터 딜러', '개인 웨이터'],
                'location': 'VIP플로어 3층',
                'capacity': 4,
                'description': 'VIP 다이아몬드 고객 전용 프라이빗 바카라 살롱'
            },
            'table_005': {
                'room_id': 'table_005',
                'display_name': 'VIP 살롱 플래티넘',
                'korean_name': 'VIP 살롱 플래티넘',
                'english_name': 'VIP Salon Platinum',
                'room_type': 'VIP',
                'vip_level': 'Platinum',
                'betting_limits': {
                    'min': 100000,
                    'max': 1000000,
                    'display': '10만~100만원'
                },
                'features': ['VIP 전용', '개인 서비스', '마스터 딜러', '개인 웨이터', '전용 입구'],
                'location': 'VIP플로어 3층',
                'capacity': 4,
                'description': 'VIP 플래티넘 고객 전용 최고급 프라이빗 바카라 살롱'
            }
        }
        
        logger.info("✅ Enhanced Room Manager 초기화 완료")
    
    def get_room_info(self, room_id: str) -> Dict[str, Any]:
        """방 ID로 상세 방 정보 조회"""
        return self.room_mapping.get(room_id, {
            'room_id': room_id,
            'display_name': f'알 수 없는 방 ({room_id})',
            'korean_name': f'알 수 없는 방 ({room_id})',
            'english_name': f'Unknown Room ({room_id})',
            'room_type': '일반',
            'vip_level': 'Standard',
            'betting_limits': {'min': 0, 'max': 0, 'display': '정보없음'},
            'features': [],
            'location': '정보없음',
            'capacity': 0,
            'description': '방 정보를 찾을 수 없습니다'
        })
    
    def get_display_name(self, room_id: str) -> str:
        """방 ID의 표시용 이름 반환"""
        room_info = self.get_room_info(room_id)
        return room_info['display_name']
    
    def get_korean_name(self, room_id: str) -> str:
        """방 ID의 한국어 이름 반환"""
        room_info = self.get_room_info(room_id)
        return room_info['korean_name']
    
    def load_baccarat_data_with_room_names(self) -> Dict[str, Any]:
        """baccarat_data.json을 불러와서 실제 방명 정보 추가"""
        try:
            if not self.data_file_path.exists():
                logger.warning(f"데이터 파일이 존재하지 않음: {self.data_file_path}")
                return {}
            
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 각 테이블에 실제 방명 정보 추가
            enhanced_data = data.copy()
            
            if 'tables' in enhanced_data:
                for table_id, table_data in enhanced_data['tables'].items():
                    room_info = self.get_room_info(table_id)
                    
                    # 방명 정보를 테이블 데이터에 추가
                    table_data['room_info'] = room_info
                    table_data['display_name'] = room_info['display_name']
                    table_data['korean_name'] = room_info['korean_name']
                    table_data['room_type'] = room_info['room_type']
                    table_data['betting_limits'] = room_info['betting_limits']
            
            logger.info(f"✅ {len(enhanced_data.get('tables', {}))}개 테이블에 방명 정보 추가 완료")
            return enhanced_data
            
        except Exception as e:
            logger.error(f"❌ 데이터 로드 실패: {e}")
            return {}
    
    def get_room_summary(self) -> List[Dict[str, Any]]:
        """모든 방 정보 요약 반환"""
        summary = []
        
        for room_id, room_info in self.room_mapping.items():
            summary.append({
                'room_id': room_id,
                'display_name': room_info['display_name'],
                'korean_name': room_info['korean_name'],
                'room_type': room_info['room_type'],
                'vip_level': room_info['vip_level'],
                'betting_range': room_info['betting_limits']['display'],
                'location': room_info['location'],
                'capacity': room_info['capacity']
            })
        
        return summary
    
    def get_rooms_by_type(self, room_type: str) -> List[Dict[str, Any]]:
        """방 타입별 방 목록 반환"""
        rooms = []
        
        for room_id, room_info in self.room_mapping.items():
            if room_info['room_type'].lower() == room_type.lower():
                rooms.append({
                    'room_id': room_id,
                    'display_name': room_info['display_name'],
                    'korean_name': room_info['korean_name'],
                    'betting_range': room_info['betting_limits']['display'],
                    'features': room_info['features']
                })
        
        return rooms
    
    def format_room_display(self, room_id: str, include_details: bool = False) -> str:
        """방 정보를 표시용 문자열로 포맷"""
        room_info = self.get_room_info(room_id)
        
        if not include_details:
            return f"{room_info['display_name']} ({room_info['betting_limits']['display']})"
        
        return f"""
🏛️ {room_info['display_name']}
📍 위치: {room_info['location']}
💰 베팅한도: {room_info['betting_limits']['display']}
👥 수용인원: {room_info['capacity']}명
🎭 등급: {room_info['vip_level']}
✨ 특징: {', '.join(room_info['features'])}
📝 설명: {room_info['description']}
        """.strip()


def create_enhanced_room_api_response(room_manager: EnhancedRoomManager) -> Dict[str, Any]:
    """향상된 방 정보 API 응답 생성"""
    enhanced_data = room_manager.load_baccarat_data_with_room_names()
    
    if not enhanced_data:
        return {
            'success': False,
            'error': 'baccarat_data.json 파일을 찾을 수 없습니다',
            'timestamp': datetime.now().isoformat()
        }
    
    # 통계 재계산 (실제 방명 포함)
    tables_with_room_info = {}
    
    for table_id, table_data in enhanced_data.get('tables', {}).items():
        room_info = room_manager.get_room_info(table_id)
        
        tables_with_room_info[table_id] = {
            # 기존 데이터
            'total_games': table_data.get('total_games', 0),
            'pair_count': table_data.get('pair_count', 0),
            'pair_rate': table_data.get('statistics', {}).get('pair_rate', 0),
            'last_game_time': table_data.get('last_game_time'),
            
            # 향상된 방명 정보
            'room_info': {
                'display_name': room_info['display_name'],
                'korean_name': room_info['korean_name'],
                'english_name': room_info['english_name'],
                'room_type': room_info['room_type'],
                'vip_level': room_info['vip_level'],
                'betting_limits': room_info['betting_limits'],
                'location': room_info['location'],
                'capacity': room_info['capacity'],
                'features': room_info['features']
            }
        }
    
    return {
        'success': True,
        'tables': tables_with_room_info,
        'global_stats': enhanced_data.get('global_stats', {}),
        'room_summary': room_manager.get_room_summary(),
        'room_types': {
            '일반': room_manager.get_rooms_by_type('일반'),
            '프리미엄': room_manager.get_rooms_by_type('프리미엄'),
            'VIP': room_manager.get_rooms_by_type('VIP')
        },
        'timestamp': datetime.now().isoformat()
    }


if __name__ == '__main__':
    # 테스트 실행
    room_manager = EnhancedRoomManager()
    
    print("Enhanced Room Information System")
    print("=" * 60)
    
    # 방 정보 요약
    print("방 정보 요약:")
    for room in room_manager.get_room_summary():
        print(f"  • {room['display_name']} ({room['room_type']}) - {room['betting_range']}")
    
    print("\n상세 방 정보:")
    for room_id in ['table_001', 'table_004', 'table_005']:
        room_info = room_manager.get_room_info(room_id)
        print(f"  {room_info['display_name']} - {room_info['location']}")
        print(f"  베팅한도: {room_info['betting_limits']['display']}")
        print(f"  등급: {room_info['vip_level']}")
        print()
    
    # API 응답 테스트
    print("API 응답 테스트:")
    api_response = create_enhanced_room_api_response(room_manager)
    if api_response['success']:
        print(f"성공: {len(api_response['tables'])}개 테이블 정보 로드 성공")
        print(f"총 {api_response['global_stats'].get('total_games', 0)}개 게임, {api_response['global_stats'].get('total_pairs', 0)}개 페어")
    else:
        print(f"실패: {api_response['error']}")