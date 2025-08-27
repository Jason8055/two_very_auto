#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chart.js 통합 시스템 v2.0
실시간 차트 데이터 처리 및 Chart.js 연동
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChartDataProcessor:
    """Chart.js용 데이터 처리기"""
    
    def __init__(self, max_data_points: int = 50):
        self.max_data_points = max_data_points
        self.data_cache = {
            'pair_timeline': deque(maxlen=max_data_points),
            'table_stats': {},
            'hourly_stats': defaultdict(lambda: {'pairs': 0, 'games': 0}),
            'daily_stats': defaultdict(lambda: {'pairs': 0, 'games': 0})
        }
        
    def process_game_data(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """게임 데이터를 차트용으로 변환"""
        table_name = game_data.get('table_name', 'Unknown')
        timestamp = datetime.now()
        
        # 시간별 통계 업데이트
        hour_key = timestamp.strftime('%Y-%m-%d %H:00')
        day_key = timestamp.strftime('%Y-%m-%d')
        
        self.data_cache['hourly_stats'][hour_key]['games'] += 1
        self.data_cache['daily_stats'][day_key]['games'] += 1
        
        # 페어 발생 처리
        chart_data = {
            'timestamp': timestamp.isoformat(),
            'table_name': table_name,
            'has_pair': game_data.get('has_pair', False),
            'pair_type': game_data.get('pair_type'),
            'game_id': game_data.get('game_id', 0)
        }
        
        # 페어 발생 시 추가 처리
        if game_data.get('has_pair', False):
            self.data_cache['hourly_stats'][hour_key]['pairs'] += 1
            self.data_cache['daily_stats'][day_key]['pairs'] += 1
            
            # 타임라인에 페어 이벤트 추가
            self.data_cache['pair_timeline'].append({
                'x': timestamp.isoformat(),
                'y': self._get_table_index(table_name),
                'table': table_name,
                'type': game_data.get('pair_type', 'UNKNOWN'),
                'game_id': game_data.get('game_id', 0)
            })
        
        # 테이블별 통계 업데이트
        if table_name not in self.data_cache['table_stats']:
            self.data_cache['table_stats'][table_name] = {
                'total_games': 0,
                'total_pairs': 0,
                'pair_types': defaultdict(int),
                'last_pair': None,
                'games_since_last_pair': 0
            }
        
        table_stats = self.data_cache['table_stats'][table_name]
        table_stats['total_games'] += 1
        
        if game_data.get('has_pair', False):
            table_stats['total_pairs'] += 1
            table_stats['pair_types'][game_data.get('pair_type', 'UNKNOWN')] += 1
            table_stats['last_pair'] = timestamp.isoformat()
            table_stats['games_since_last_pair'] = 0
        else:
            table_stats['games_since_last_pair'] += 1
            
        return chart_data
    
    def _get_table_index(self, table_name: str) -> int:
        """테이블명을 차트용 Y축 인덱스로 변환"""
        table_list = sorted(self.data_cache['table_stats'].keys())
        if table_name in table_list:
            return table_list.index(table_name)
        return len(table_list)
    
    def get_pair_timeline_data(self, hours: int = 24) -> Dict[str, Any]:
        """페어 발생 타임라인 데이터 (산점도)"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 최근 데이터 필터링
        filtered_data = [
            point for point in self.data_cache['pair_timeline']
            if datetime.fromisoformat(point['x']) > cutoff_time
        ]
        
        # 테이블별 색상 매핑
        tables = list(set(point['table'] for point in filtered_data))
        colors = ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4']
        table_colors = {table: colors[i % len(colors)] for i, table in enumerate(tables)}
        
        # Chart.js 형식으로 데이터 구성
        datasets = []
        for table in tables:
            table_data = [point for point in filtered_data if point['table'] == table]
            
            datasets.append({
                'label': table,
                'data': table_data,
                'backgroundColor': table_colors[table],
                'borderColor': table_colors[table],
                'borderWidth': 2,
                'pointRadius': 6,
                'pointHoverRadius': 8
            })
        
        return {
            'type': 'scatter',
            'data': {
                'datasets': datasets
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': f'페어 발생 타임라인 (최근 {hours}시간)'
                    },
                    'legend': {
                        'display': True,
                        'position': 'top'
                    }
                },
                'scales': {
                    'x': {
                        'type': 'time',
                        'time': {
                            'unit': 'hour'
                        },
                        'title': {
                            'display': True,
                            'text': '시간'
                        }
                    },
                    'y': {
                        'type': 'linear',
                        'title': {
                            'display': True,
                            'text': '테이블'
                        },
                        'ticks': {
                            'callback': f"function(value) {{ const tables = {json.dumps(tables)}; return tables[value] || value; }}"
                        }
                    }
                }
            }
        }
    
    def get_hourly_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """시간별 통계 데이터 (선형 차트)"""
        now = datetime.now()
        labels = []
        games_data = []
        pairs_data = []
        
        for i in range(hours):
            hour_time = now - timedelta(hours=i)
            hour_key = hour_time.strftime('%Y-%m-%d %H:00')
            labels.insert(0, hour_time.strftime('%H:00'))
            
            stats = self.data_cache['hourly_stats'].get(hour_key, {'games': 0, 'pairs': 0})
            games_data.insert(0, stats['games'])
            pairs_data.insert(0, stats['pairs'])
        
        return {
            'type': 'line',
            'data': {
                'labels': labels,
                'datasets': [
                    {
                        'label': '총 게임 수',
                        'data': games_data,
                        'borderColor': '#3b82f6',
                        'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                        'borderWidth': 2,
                        'fill': True,
                        'tension': 0.3
                    },
                    {
                        'label': '페어 발생',
                        'data': pairs_data,
                        'borderColor': '#ef4444',
                        'backgroundColor': 'rgba(239, 68, 68, 0.1)',
                        'borderWidth': 2,
                        'fill': True,
                        'tension': 0.3
                    }
                ]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': f'시간별 게임 & 페어 통계 (최근 {hours}시간)'
                    }
                },
                'scales': {
                    'y': {
                        'beginAtZero': True,
                        'title': {
                            'display': True,
                            'text': '횟수'
                        }
                    }
                }
            }
        }
    
    def get_table_comparison(self) -> Dict[str, Any]:
        """테이블별 비교 데이터 (막대 차트)"""
        tables = list(self.data_cache['table_stats'].keys())
        games_data = []
        pairs_data = []
        pair_rates = []
        
        for table in tables:
            stats = self.data_cache['table_stats'][table]
            games_data.append(stats['total_games'])
            pairs_data.append(stats['total_pairs'])
            
            # 페어율 계산
            rate = (stats['total_pairs'] / stats['total_games'] * 100) if stats['total_games'] > 0 else 0
            pair_rates.append(round(rate, 2))
        
        return {
            'type': 'bar',
            'data': {
                'labels': tables,
                'datasets': [
                    {
                        'label': '총 게임',
                        'data': games_data,
                        'backgroundColor': 'rgba(59, 130, 246, 0.8)',
                        'borderColor': '#3b82f6',
                        'borderWidth': 1,
                        'yAxisID': 'y'
                    },
                    {
                        'label': '페어 발생',
                        'data': pairs_data,
                        'backgroundColor': 'rgba(239, 68, 68, 0.8)',
                        'borderColor': '#ef4444',
                        'borderWidth': 1,
                        'yAxisID': 'y'
                    },
                    {
                        'label': '페어율 (%)',
                        'data': pair_rates,
                        'type': 'line',
                        'borderColor': '#10b981',
                        'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                        'borderWidth': 2,
                        'yAxisID': 'y1',
                        'fill': False
                    }
                ]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': '테이블별 게임 & 페어 통계'
                    }
                },
                'scales': {
                    'y': {
                        'type': 'linear',
                        'display': True,
                        'position': 'left',
                        'title': {
                            'display': True,
                            'text': '게임/페어 횟수'
                        }
                    },
                    'y1': {
                        'type': 'linear',
                        'display': True,
                        'position': 'right',
                        'title': {
                            'display': True,
                            'text': '페어율 (%)'
                        },
                        'grid': {
                            'drawOnChartArea': False
                        }
                    }
                }
            }
        }
    
    def get_pair_type_distribution(self) -> Dict[str, Any]:
        """페어 타입 분포 (도넛 차트)"""
        all_pair_types = defaultdict(int)
        
        for table_stats in self.data_cache['table_stats'].values():
            for pair_type, count in table_stats['pair_types'].items():
                all_pair_types[pair_type] += count
        
        # 한국어 레이블 매핑
        type_labels = {
            'PLAYER_PAIR': '플레이어 페어',
            'BANKER_PAIR': '뱅커 페어',
            'BOTH_PAIR': '양쪽 페어',
            'PP': '플레이어 페어',
            'BP': '뱅커 페어',
            'BOTH': '양쪽 페어'
        }
        
        labels = []
        data = []
        colors = ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6']
        
        for i, (pair_type, count) in enumerate(all_pair_types.items()):
            labels.append(type_labels.get(pair_type, pair_type))
            data.append(count)
        
        return {
            'type': 'doughnut',
            'data': {
                'labels': labels,
                'datasets': [{
                    'data': data,
                    'backgroundColor': colors[:len(data)],
                    'borderColor': '#ffffff',
                    'borderWidth': 2,
                    'hoverOffset': 4
                }]
            },
            'options': {
                'responsive': True,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': '페어 타입 분포'
                    },
                    'legend': {
                        'position': 'bottom'
                    }
                }
            }
        }
    
    def get_realtime_metrics(self) -> Dict[str, Any]:
        """실시간 메트릭 데이터"""
        total_games = sum(stats['total_games'] for stats in self.data_cache['table_stats'].values())
        total_pairs = sum(stats['total_pairs'] for stats in self.data_cache['table_stats'].values())
        
        # 최근 1시간 통계
        now = datetime.now()
        recent_hour = now.strftime('%Y-%m-%d %H:00')
        recent_stats = self.data_cache['hourly_stats'].get(recent_hour, {'games': 0, 'pairs': 0})
        
        # 활성 테이블 수 (최근 10분 내 활동)
        active_tables = 0
        for table_name, stats in self.data_cache['table_stats'].items():
            if stats.get('last_pair'):
                try:
                    last_pair_time = datetime.fromisoformat(stats['last_pair'])
                    if (now - last_pair_time).total_seconds() < 600:  # 10분
                        active_tables += 1
                except:
                    pass
        
        return {
            'total_games': total_games,
            'total_pairs': total_pairs,
            'pair_rate': round((total_pairs / total_games * 100) if total_games > 0 else 0, 2),
            'active_tables': active_tables,
            'total_tables': len(self.data_cache['table_stats']),
            'recent_hour': {
                'games': recent_stats['games'],
                'pairs': recent_stats['pairs']
            },
            'last_update': now.isoformat()
        }
    
    def export_chart_config(self, chart_type: str) -> str:
        """차트 설정을 JSON으로 내보내기"""
        try:
            if chart_type == 'timeline':
                data = self.get_pair_timeline_data()
            elif chart_type == 'hourly':
                data = self.get_hourly_statistics()
            elif chart_type == 'comparison':
                data = self.get_table_comparison()
            elif chart_type == 'distribution':
                data = self.get_pair_type_distribution()
            else:
                return json.dumps({'error': 'Unknown chart type'})
            
            return json.dumps(data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"Chart config export failed: {e}")
            return json.dumps({'error': str(e)})


class ChartWebSocketHandler:
    """실시간 차트 데이터 WebSocket 핸들러"""
    
    def __init__(self, chart_processor: ChartDataProcessor):
        self.chart_processor = chart_processor
        self.connected_clients = set()
        
    def add_client(self, websocket):
        """WebSocket 클라이언트 추가"""
        self.connected_clients.add(websocket)
        logger.info(f"Chart client connected. Total: {len(self.connected_clients)}")
        
    def remove_client(self, websocket):
        """WebSocket 클라이언트 제거"""
        self.connected_clients.discard(websocket)
        logger.info(f"Chart client disconnected. Total: {len(self.connected_clients)}")
        
    async def broadcast_chart_update(self, chart_type: str, data: Dict[str, Any]):
        """차트 업데이트를 모든 클라이언트에게 브로드캐스트"""
        if not self.connected_clients:
            return
            
        message = {
            'type': 'chart_update',
            'chart_type': chart_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        # 연결이 끊어진 클라이언트 제거
        disconnected = set()
        for client in self.connected_clients:
            try:
                await client.send(json.dumps(message, ensure_ascii=False))
            except:
                disconnected.add(client)
        
        for client in disconnected:
            self.connected_clients.discard(client)
    
    async def send_initial_data(self, websocket):
        """새 클라이언트에게 초기 차트 데이터 전송"""
        try:
            charts = {
                'timeline': self.chart_processor.get_pair_timeline_data(),
                'hourly': self.chart_processor.get_hourly_statistics(),
                'comparison': self.chart_processor.get_table_comparison(),
                'distribution': self.chart_processor.get_pair_type_distribution(),
                'metrics': self.chart_processor.get_realtime_metrics()
            }
            
            message = {
                'type': 'initial_charts',
                'charts': charts,
                'timestamp': datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(message, ensure_ascii=False))
            
        except Exception as e:
            logger.error(f"Failed to send initial chart data: {e}")


# 전역 인스턴스
chart_processor = ChartDataProcessor()
chart_websocket_handler = ChartWebSocketHandler(chart_processor)

def get_chart_processor() -> ChartDataProcessor:
    """전역 차트 프로세서 인스턴스 반환"""
    return chart_processor

def get_chart_websocket_handler() -> ChartWebSocketHandler:
    """전역 차트 WebSocket 핸들러 반환"""
    return chart_websocket_handler


if __name__ == "__main__":
    # 테스트 코드
    print("=== Chart Integration System Test ===")
    
    processor = ChartDataProcessor()
    
    # 테스트 데이터 생성
    import random
    tables = ['메인테이블_A', '메인테이블_B', 'VIP테이블_1']
    pair_types = ['PLAYER_PAIR', 'BANKER_PAIR', 'BOTH_PAIR']
    
    print("Generating test data...")
    for i in range(100):
        test_data = {
            'table_name': random.choice(tables),
            'has_pair': random.random() < 0.15,  # 15% 페어 확률
            'pair_type': random.choice(pair_types) if random.random() < 0.15 else None,
            'game_id': i + 1
        }
        processor.process_game_data(test_data)
    
    print("\n📊 Chart Data Generation Complete!")
    print(f"  Tables: {len(processor.data_cache['table_stats'])}")
    print(f"  Pair Events: {len(processor.data_cache['pair_timeline'])}")
    
    # 메트릭 출력
    metrics = processor.get_realtime_metrics()
    print(f"\n📈 Real-time Metrics:")
    print(f"  Total Games: {metrics['total_games']}")
    print(f"  Total Pairs: {metrics['total_pairs']}")
    print(f"  Pair Rate: {metrics['pair_rate']}%")
    print(f"  Active Tables: {metrics['active_tables']}/{metrics['total_tables']}")
    
    print("\n🎯 Chart Integration Test Complete!")