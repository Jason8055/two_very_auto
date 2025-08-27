#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI 서버 테스트 클라이언트
"""

import requests
import json
import time
import sys
from typing import Dict, Any

class FastAPITester:
    """FastAPI 서버 테스트 클라이언트"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8002"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def test_health_check(self) -> bool:
        """헬스체크 테스트"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS: Health check - Status: {data.get('status', 'unknown')}")
                return True
            else:
                print(f"ERROR: Health check failed - Status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"ERROR: Health check exception - {e}")
            return False
    
    def test_demo_api(self) -> bool:
        """데모 API 테스트"""
        try:
            payload = {
                "game_count": 5,
                "pair_probability": 0.3
            }
            
            response = self.session.post(
                f"{self.base_url}/api/demo", 
                data=json.dumps(payload),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS: Demo API - Games: {data.get('games_added', 0)}, Pairs: {data.get('pairs_found', 0)}")
                return True
            else:
                print(f"ERROR: Demo API failed - Status code: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"ERROR Details: {error_data}")
                except:
                    print(f"ERROR Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"ERROR: Demo API exception - {e}")
            return False
    
    def test_stats_api(self) -> bool:
        """통계 API 테스트"""
        try:
            response = self.session.get(f"{self.base_url}/api/stats", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get('stats', {})
                print(f"SUCCESS: Stats API - Games: {stats.get('total_games', 0)}, Pairs: {stats.get('total_pairs', 0)}")
                return True
            else:
                print(f"ERROR: Stats API failed - Status code: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"ERROR: Stats API exception - {e}")
            return False
    
    def test_performance_comparison(self) -> Dict[str, Any]:
        """성능 비교 테스트"""
        print("\n=== Performance Comparison Test ===")
        
        # FastAPI 데모 API 성능 측정
        fastapi_times = []
        for i in range(3):
            start_time = time.time()
            success = self.test_demo_api()
            end_time = time.time()
            
            if success:
                fastapi_times.append(end_time - start_time)
                print(f"FastAPI Test {i+1}: {end_time - start_time:.3f}s")
            else:
                print(f"FastAPI Test {i+1}: Failed")
        
        if fastapi_times:
            avg_fastapi_time = sum(fastapi_times) / len(fastapi_times)
            print(f"FastAPI Average Response Time: {avg_fastapi_time:.3f}s")
            
            return {
                'fastapi_times': fastapi_times,
                'fastapi_average': avg_fastapi_time,
                'successful_tests': len(fastapi_times),
                'total_tests': 3
            }
        else:
            print("No successful FastAPI tests")
            return {'error': 'No successful tests'}
    
    def run_all_tests(self) -> Dict[str, bool]:
        """모든 테스트 실행"""
        print("=== FastAPI Server Test Suite ===")
        
        results = {}
        
        print("\n1. Testing Health Check...")
        results['health'] = self.test_health_check()
        
        print("\n2. Testing Demo API...")
        results['demo'] = self.test_demo_api()
        
        print("\n3. Testing Stats API...")  
        results['stats'] = self.test_stats_api()
        
        print("\n4. Performance Testing...")
        perf_results = self.test_performance_comparison()
        results['performance'] = perf_results
        
        print("\n=== Test Results Summary ===")
        passed = sum(1 for k, v in results.items() if k != 'performance' and v)
        total = len([k for k in results.keys() if k != 'performance'])
        print(f"Tests Passed: {passed}/{total}")
        
        for test_name, result in results.items():
            if test_name != 'performance':
                status = "PASS" if result else "FAIL"
                print(f"  {test_name}: {status}")
        
        return results

def main():
    """메인 실행 함수"""
    if len(sys.argv) > 1 and sys.argv[1] == '--wait':
        print("Waiting 3 seconds for server to start...")
        time.sleep(3)
    
    tester = FastAPITester()
    
    print("Testing FastAPI server connection...")
    
    # 서버 연결 대기
    for attempt in range(5):
        if tester.test_health_check():
            break
        print(f"Attempt {attempt + 1}: Server not ready, waiting...")
        time.sleep(1)
    else:
        print("ERROR: Cannot connect to FastAPI server")
        print("Make sure the server is running on http://127.0.0.1:8000")
        return
    
    # 모든 테스트 실행
    results = tester.run_all_tests()
    
    # 결과 저장
    with open('test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print("\nTest results saved to test_results.json")

if __name__ == "__main__":
    main()