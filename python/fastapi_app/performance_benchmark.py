#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI vs Flask 성능 벤치마크 테스트
"""

import requests
import time
import statistics
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any
import sys

class PerformanceBenchmark:
    """성능 벤치마크 테스트 클래스"""
    
    def __init__(self):
        self.fastapi_url = "http://127.0.0.1:8002"
        self.flask_url = "http://127.0.0.1:5557"  # 기존 Flask minimal API
        
    def single_request_test(self, url: str, endpoint: str, method: str = "GET", data: Dict = None, timeout: int = 10) -> Dict[str, Any]:
        """단일 요청 테스트"""
        start_time = time.time()
        
        try:
            if method.upper() == "POST":
                response = requests.post(f"{url}{endpoint}", json=data, timeout=timeout)
            else:
                response = requests.get(f"{url}{endpoint}", timeout=timeout)
            
            end_time = time.time()
            
            return {
                'success': True,
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'content_length': len(response.content),
                'success_api': response.status_code == 200
            }
            
        except Exception as e:
            end_time = time.time()
            return {
                'success': False,
                'error': str(e),
                'response_time': end_time - start_time,
                'content_length': 0,
                'success_api': False
            }
    
    def concurrent_test(self, url: str, endpoint: str, method: str = "GET", data: Dict = None, 
                       num_requests: int = 10, max_workers: int = 5) -> List[Dict[str, Any]]:
        """동시 요청 테스트"""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for _ in range(num_requests):
                future = executor.submit(self.single_request_test, url, endpoint, method, data)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=15)
                    results.append(result)
                except Exception as e:
                    results.append({
                        'success': False,
                        'error': f"Future error: {str(e)}",
                        'response_time': 0,
                        'content_length': 0,
                        'success_api': False
                    })
        
        return results
    
    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """결과 분석"""
        if not results:
            return {'error': 'No results to analyze'}
        
        successful_results = [r for r in results if r['success'] and r['success_api']]
        
        if not successful_results:
            return {
                'total_requests': len(results),
                'successful_requests': 0,
                'failed_requests': len(results),
                'success_rate': 0.0,
                'error': 'No successful requests'
            }
        
        response_times = [r['response_time'] for r in successful_results]
        
        return {
            'total_requests': len(results),
            'successful_requests': len(successful_results),
            'failed_requests': len(results) - len(successful_results),
            'success_rate': len(successful_results) / len(results) * 100,
            'avg_response_time': statistics.mean(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'median_response_time': statistics.median(response_times),
            'std_response_time': statistics.stdev(response_times) if len(response_times) > 1 else 0,
            'requests_per_second': len(successful_results) / sum(response_times) if sum(response_times) > 0 else 0,
            'avg_content_length': statistics.mean([r['content_length'] for r in successful_results])
        }
    
    def test_server_availability(self, url: str, name: str) -> bool:
        """서버 가용성 테스트"""
        try:
            print(f"Testing {name} server availability...")
            response = requests.get(f"{url}/", timeout=5)
            print(f"{name} server: Status {response.status_code}")
            return response.status_code in [200, 404]  # 404도 서버 동작 중으로 간주
        except Exception as e:
            print(f"{name} server not available: {e}")
            return False
    
    def run_demo_api_benchmark(self) -> Dict[str, Any]:
        """데모 API 벤치마크"""
        print("\n=== Demo API Performance Benchmark ===")
        
        demo_data = {"game_count": 5}
        
        results = {}
        
        # FastAPI 테스트
        if self.test_server_availability(self.fastapi_url, "FastAPI"):
            print("\nTesting FastAPI Demo API...")
            
            # 단일 요청 테스트
            single_result = self.single_request_test(
                self.fastapi_url, "/api/demo", "POST", demo_data
            )
            print(f"FastAPI Single Request: {single_result['response_time']:.3f}s")
            
            # 동시 요청 테스트
            concurrent_results = self.concurrent_test(
                self.fastapi_url, "/api/demo", "POST", demo_data, 
                num_requests=10, max_workers=3
            )
            
            fastapi_analysis = self.analyze_results(concurrent_results)
            results['fastapi'] = fastapi_analysis
            
            print(f"FastAPI Concurrent Test:")
            print(f"  Success Rate: {fastapi_analysis.get('success_rate', 0):.1f}%")
            print(f"  Avg Response Time: {fastapi_analysis.get('avg_response_time', 0):.3f}s")
            print(f"  Requests/sec: {fastapi_analysis.get('requests_per_second', 0):.2f}")
        else:
            results['fastapi'] = {'error': 'FastAPI server not available'}
        
        # Flask 테스트 (기존 minimal API가 실행 중인 경우)
        if self.test_server_availability(self.flask_url, "Flask"):
            print("\nTesting Flask Demo API...")
            
            # Flask는 다른 엔드포인트 구조를 가질 수 있음
            flask_endpoints = ["/api/minimal-demo", "/api/demo"]
            flask_success = False
            
            for endpoint in flask_endpoints:
                try:
                    single_result = self.single_request_test(
                        self.flask_url, endpoint, "POST", demo_data
                    )
                    if single_result['success_api']:
                        print(f"Flask Single Request: {single_result['response_time']:.3f}s")
                        
                        concurrent_results = self.concurrent_test(
                            self.flask_url, endpoint, "POST", demo_data,
                            num_requests=10, max_workers=3
                        )
                        
                        flask_analysis = self.analyze_results(concurrent_results)
                        results['flask'] = flask_analysis
                        
                        print(f"Flask Concurrent Test:")
                        print(f"  Success Rate: {flask_analysis.get('success_rate', 0):.1f}%")
                        print(f"  Avg Response Time: {flask_analysis.get('avg_response_time', 0):.3f}s")
                        print(f"  Requests/sec: {flask_analysis.get('requests_per_second', 0):.2f}")
                        
                        flask_success = True
                        break
                except:
                    continue
            
            if not flask_success:
                results['flask'] = {'error': 'Flask demo API not accessible'}
        else:
            results['flask'] = {'error': 'Flask server not available'}
        
        return results
    
    def compare_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """결과 비교"""
        if 'fastapi' not in results or 'flask' not in results:
            return {'error': 'Cannot compare - one or both servers not available'}
        
        fastapi_data = results['fastapi']
        flask_data = results['flask']
        
        if 'error' in fastapi_data or 'error' in flask_data:
            return {
                'fastapi_status': 'error' if 'error' in fastapi_data else 'ok',
                'flask_status': 'error' if 'error' in flask_data else 'ok',
                'fastapi_error': fastapi_data.get('error'),
                'flask_error': flask_data.get('error')
            }
        
        # 성능 비교
        comparison = {
            'performance_comparison': {
                'fastapi_faster': fastapi_data['avg_response_time'] < flask_data['avg_response_time'],
                'speed_improvement': (
                    (flask_data['avg_response_time'] - fastapi_data['avg_response_time']) 
                    / flask_data['avg_response_time'] * 100
                    if flask_data['avg_response_time'] > 0 else 0
                ),
                'throughput_improvement': (
                    (fastapi_data['requests_per_second'] - flask_data['requests_per_second']) 
                    / flask_data['requests_per_second'] * 100
                    if flask_data['requests_per_second'] > 0 else 0
                )
            },
            'detailed_comparison': {
                'fastapi': {
                    'avg_response_time': fastapi_data['avg_response_time'],
                    'requests_per_second': fastapi_data['requests_per_second'],
                    'success_rate': fastapi_data['success_rate']
                },
                'flask': {
                    'avg_response_time': flask_data['avg_response_time'],
                    'requests_per_second': flask_data['requests_per_second'],
                    'success_rate': flask_data['success_rate']
                }
            }
        }
        
        return comparison
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """전체 벤치마크 실행"""
        print("=" * 60)
        print("FastAPI vs Flask Performance Benchmark")
        print("=" * 60)
        
        # 데모 API 벤치마크
        demo_results = self.run_demo_api_benchmark()
        
        # 결과 비교
        comparison = self.compare_results(demo_results)
        
        # 결과 출력
        print("\n=== Performance Comparison Results ===")
        
        if 'error' in comparison:
            print(f"Comparison Error: {comparison['error']}")
            if 'fastapi_error' in comparison:
                print(f"FastAPI Error: {comparison['fastapi_error']}")
            if 'flask_error' in comparison:
                print(f"Flask Error: {comparison['flask_error']}")
        elif 'performance_comparison' in comparison:
            perf_comp = comparison['performance_comparison']
            detailed = comparison['detailed_comparison']
            
            print(f"FastAPI vs Flask:")
            print(f"  FastAPI is {'faster' if perf_comp['fastapi_faster'] else 'slower'}")
            print(f"  Speed improvement: {perf_comp['speed_improvement']:+.1f}%")
            print(f"  Throughput improvement: {perf_comp['throughput_improvement']:+.1f}%")
            
            print(f"\nDetailed Metrics:")
            print(f"  FastAPI: {detailed['fastapi']['avg_response_time']:.3f}s avg, "
                  f"{detailed['fastapi']['requests_per_second']:.2f} req/s")
            print(f"  Flask: {detailed['flask']['avg_response_time']:.3f}s avg, "
                  f"{detailed['flask']['requests_per_second']:.2f} req/s")
        else:
            print("Limited comparison available - showing FastAPI results only:")
            if 'fastapi' in demo_results and 'error' not in demo_results['fastapi']:
                fastapi_data = demo_results['fastapi']
                print(f"FastAPI Performance:")
                print(f"  Avg Response Time: {fastapi_data['avg_response_time']:.3f}s")
                print(f"  Requests/sec: {fastapi_data['requests_per_second']:.2f}")
                print(f"  Success Rate: {fastapi_data['success_rate']:.1f}%")
            
            if 'flask' in demo_results:
                flask_data = demo_results['flask']
                if 'error' in flask_data:
                    print(f"Flask Server: {flask_data['error']}")
                else:
                    print(f"Flask Performance:")
                    print(f"  Avg Response Time: {flask_data['avg_response_time']:.3f}s")
                    print(f"  Requests/sec: {flask_data['requests_per_second']:.2f}")
        
        # 결과 저장
        full_results = {
            'demo_api_results': demo_results,
            'comparison': comparison,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_config': {
                'concurrent_requests': 10,
                'max_workers': 3,
                'timeout': 10
            }
        }
        
        with open('performance_benchmark_results.json', 'w', encoding='utf-8') as f:
            json.dump(full_results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\nResults saved to performance_benchmark_results.json")
        
        return full_results

def main():
    """메인 실행 함수"""
    benchmark = PerformanceBenchmark()
    results = benchmark.run_full_benchmark()
    
    # 간단한 결과 요약
    print("\n=== Benchmark Summary ===")
    if 'comparison' in results and 'performance_comparison' in results['comparison']:
        perf = results['comparison']['performance_comparison']
        print(f"FastAPI Performance: {'+' if perf['speed_improvement'] > 0 else ''}{perf['speed_improvement']:.1f}% speed improvement")
        print(f"FastAPI Throughput: {'+' if perf['throughput_improvement'] > 0 else ''}{perf['throughput_improvement']:.1f}% throughput improvement")
    else:
        print("Performance comparison not available - check server availability")

if __name__ == "__main__":
    main()