#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 연결 모니터링 스크립트 (표준 라이브러리 사용)
Simple Connection Monitor
"""

import urllib.request
import urllib.error
import time
import json
from datetime import datetime

class SimpleMonitor:
    def __init__(self):
        self.servers = [
            {"name": "Simple Server", "url": "http://127.0.0.1:8005/health"},
            {"name": "Main Server", "url": "http://127.0.0.1:8006/health"},
            {"name": "System Status", "url": "http://127.0.0.1:8006/system-status"}
        ]
        self.stats = {
            "total_checks": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "response_times": [],
            "failures": []
        }
        
    def check_server(self, server):
        """개별 서버 연결 확인"""
        try:
            start_time = time.time()
            
            req = urllib.request.Request(server["url"])
            with urllib.request.urlopen(req, timeout=5) as response:
                response_time = (time.time() - start_time) * 1000  # ms
                
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    try:
                        json_data = json.loads(data)
                    except:
                        json_data = {"raw": data}
                    
                    self.stats["successful_connections"] += 1
                    self.stats["response_times"].append(response_time)
                    
                    print(f"✅ {server['name']}: {response.status} ({response_time:.1f}ms)")
                    return True, response_time, json_data
                else:
                    print(f"⚠️ {server['name']}: HTTP {response.status}")
                    self.stats["failed_connections"] += 1
                    return False, response_time, None
                    
        except urllib.error.URLError as e:
            print(f"❌ {server['name']}: 연결 실패 - {str(e)}")
            self.stats["failed_connections"] += 1
            self.stats["failures"].append({
                "server": server['name'],
                "time": datetime.now().strftime('%H:%M:%S'),
                "error": str(e)
            })
            return False, 0, None
        except Exception as e:
            print(f"❌ {server['name']}: 예외 발생 - {str(e)}")
            self.stats["failed_connections"] += 1
            self.stats["failures"].append({
                "server": server['name'],
                "time": datetime.now().strftime('%H:%M:%S'),
                "error": str(e)
            })
            return False, 0, None
    
    def monitor_connections(self, interval=10, duration=60):
        """연결 모니터링 실행"""
        print(f"🔍 연결 모니터링 시작 - {duration}초 동안 {interval}초 간격으로 확인")
        print(f"📡 모니터링 서버: {len(self.servers)}개")
        for server in self.servers:
            print(f"   - {server['name']}: {server['url']}")
        print("-" * 60)
        
        start_time = time.time()
        end_time = start_time + duration
        
        while time.time() < end_time:
            check_start = datetime.now()
            print(f"\n📊 연결 상태 확인 - {check_start.strftime('%H:%M:%S')}")
            
            successful = 0
            total_response_time = 0
            
            for server in self.servers:
                success, response_time, data = self.check_server(server)
                self.stats["total_checks"] += 1
                
                if success:
                    successful += 1
                    total_response_time += response_time
            
            # 현재 세션 통계
            avg_response_time = total_response_time / len(self.servers) if len(self.servers) > 0 else 0
            success_rate = (self.stats["successful_connections"] / self.stats["total_checks"] * 100) if self.stats["total_checks"] > 0 else 0
            
            print(f"""
🔗 현재 상태: {successful}/{len(self.servers)} 성공 (평균 {avg_response_time:.1f}ms)
📈 전체 통계: {self.stats['successful_connections']}/{self.stats['total_checks']} ({success_rate:.1f}% 성공률)
⏱️ 남은 시간: {int(end_time - time.time())}초
            """)
            
            if successful < len(self.servers):
                print(f"🚨 {len(self.servers) - successful}개 서버에서 연결 문제!")
            
            time.sleep(interval)
        
        self.generate_report()
    
    def generate_report(self):
        """모니터링 보고서 생성"""
        success_rate = (self.stats["successful_connections"] / self.stats["total_checks"] * 100) if self.stats["total_checks"] > 0 else 0
        avg_response_time = sum(self.stats["response_times"]) / len(self.stats["response_times"]) if self.stats["response_times"] else 0
        
        print(f"""
{'=' * 60}
📊 연결 안정성 모니터링 보고서
{'=' * 60}
총 확인 횟수: {self.stats['total_checks']}
성공적인 연결: {self.stats['successful_connections']}
실패한 연결: {self.stats['failed_connections']}
전체 성공률: {success_rate:.2f}%
평균 응답시간: {avg_response_time:.1f}ms
{'최대 응답시간: ' + str(max(self.stats['response_times'])) + 'ms' if self.stats['response_times'] else ''}
{'최소 응답시간: ' + str(min(self.stats['response_times'])) + 'ms' if self.stats['response_times'] else ''}

🎯 분석 결과:
{'✅ 연결이 안정적입니다!' if success_rate >= 95 else '⚠️ 연결 불안정성이 감지되었습니다!'}
{'✅ 응답 시간이 양호합니다!' if avg_response_time < 100 else '⚠️ 응답 시간이 느립니다!'}

🔍 실패 내역:
        """)
        
        if self.stats['failures']:
            for failure in self.stats['failures'][-5:]:  # 최근 5개만 표시
                print(f"   {failure['time']} - {failure['server']}: {failure['error']}")
        else:
            print("   실패 없음 🎉")
        
        print("=" * 60)

def main():
    """메인 모니터링 실행"""
    monitor = SimpleMonitor()
    
    try:
        # 1분 동안 10초 간격으로 모니터링
        monitor.monitor_connections(interval=10, duration=60)
    except KeyboardInterrupt:
        print("\n⏹️ 모니터링 사용자 중단")
        monitor.generate_report()

if __name__ == "__main__":
    main()