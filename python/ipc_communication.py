#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
프로세스 간 통신(IPC) 시스템
two very auto.exe와 Python 시스템 간 실시간 데이터 공유
"""

import asyncio
import json
import logging
import mmap
import os
import socket
import struct
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
import queue
import tempfile

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IPCMessage:
    """IPC 메시지 구조"""
    message_id: str
    message_type: str
    timestamp: float
    sender: str
    receiver: str
    data: Dict[str, Any]
    priority: int = 0  # 0=일반, 1=높음, 2=긴급
    
    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(asdict(self), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'IPCMessage':
        """JSON 문자열에서 복원"""
        data = json.loads(json_str)
        return cls(**data)


class SharedMemoryManager:
    """공유 메모리 관리자"""
    
    def __init__(self, memory_size: int = 1024 * 1024):  # 1MB
        """공유 메모리 초기화"""
        self.memory_size = memory_size
        self.temp_file = None
        self.mmap_obj = None
        self.lock = threading.Lock()
        self.is_initialized = False
    
    def initialize(self, create: bool = True) -> bool:
        """공유 메모리 초기화"""
        try:
            # 안전한 파일 경로 사용
            project_root = Path(__file__).parent.parent
            memory_file = project_root / "temp" / "shared_memory.dat"
            
            # temp 디렉토리 생성
            memory_file.parent.mkdir(exist_ok=True)
            
            if create or not memory_file.exists():
                # 공유 메모리 파일 생성
                with open(memory_file, 'wb') as f:
                    f.write(b'\x00' * self.memory_size)
            
            # 메모리 매핑
            self.temp_file = open(memory_file, 'r+b')
            self.mmap_obj = mmap.mmap(self.temp_file.fileno(), 0)
            self.is_initialized = True
            
            logger.info(f"✅ 공유 메모리 초기화 완료: {memory_file} ({self.memory_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"공유 메모리 초기화 실패: {e}")
            logger.error(f"공유 메모리 초기화 실패")
            return False
    
    def write_data(self, data: bytes, offset: int = 0) -> bool:
        """데이터 쓰기"""
        if not self.is_initialized:
            return False
        
        try:
            with self.lock:
                if offset + len(data) > self.memory_size:
                    logger.warning(f"데이터 크기 초과: {len(data)} bytes")
                    return False
                
                self.mmap_obj.seek(offset)
                self.mmap_obj.write(data)
                self.mmap_obj.flush()
                return True
        
        except Exception as e:
            logger.error(f"공유 메모리 쓰기 실패: {e}")
            return False
    
    def read_data(self, size: int, offset: int = 0) -> Optional[bytes]:
        """데이터 읽기"""
        if not self.is_initialized:
            return None
        
        try:
            with self.lock:
                if offset + size > self.memory_size:
                    logger.warning(f"읽기 범위 초과: {size} bytes at offset {offset}")
                    return None
                
                self.mmap_obj.seek(offset)
                return self.mmap_obj.read(size)
        
        except Exception as e:
            logger.error(f"공유 메모리 읽기 실패: {e}")
            return None
    
    def close(self):
        """공유 메모리 정리"""
        try:
            if self.mmap_obj:
                self.mmap_obj.close()
            if self.temp_file:
                self.temp_file.close()
            self.is_initialized = False
            logger.info("공유 메모리 정리 완료")
        except Exception as e:
            logger.error(f"공유 메모리 정리 오류: {e}")


class NamedPipeServer:
    """Named Pipe 서버 (Windows)"""
    
    def __init__(self, pipe_name: str = r"\\.\pipe\TwoVeryAutoPipe"):
        self.pipe_name = pipe_name
        self.is_running = False
        self.server_thread = None
        self.message_callbacks = []
    
    def add_callback(self, callback: Callable[[IPCMessage], None]):
        """메시지 콜백 등록"""
        self.message_callbacks.append(callback)
    
    def start(self) -> bool:
        """파이프 서버 시작"""
        if self.is_running:
            return True
        
        try:
            self.is_running = True
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            logger.info(f"✅ Named Pipe 서버 시작: {self.pipe_name}")
            return True
        
        except Exception as e:
            logger.error(f"Named Pipe 서버 시작 실패: {e}")
            return False
    
    def stop(self):
        """파이프 서버 중지"""
        self.is_running = False
        if self.server_thread:
            self.server_thread.join(timeout=5.0)
        logger.info("Named Pipe 서버 중지됨")
    
    def _server_loop(self):
        """서버 루프 (Windows용)"""
        try:
            import win32pipe
            import win32file
            import pywintypes
            
            while self.is_running:
                try:
                    # Named Pipe 생성
                    pipe = win32pipe.CreateNamedPipe(
                        self.pipe_name,
                        win32pipe.PIPE_ACCESS_DUPLEX,
                        win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                        1, 65536, 65536, 0, None
                    )
                    
                    if pipe == -1:
                        logger.error("Named Pipe 생성 실패")
                        break
                    
                    # 클라이언트 연결 대기
                    win32pipe.ConnectNamedPipe(pipe, None)
                    logger.info("클라이언트 연결됨")
                    
                    # 메시지 수신 루프
                    while self.is_running:
                        try:
                            # 메시지 읽기
                            result, data = win32file.ReadFile(pipe, 4096)
                            if result == 0 and data:
                                message_str = data.decode('utf-8')
                                message = IPCMessage.from_json(message_str)
                                
                                # 콜백 호출
                                for callback in self.message_callbacks:
                                    try:
                                        callback(message)
                                    except Exception as e:
                                        logger.error(f"콜백 실행 오류: {e}")
                        
                        except pywintypes.error as e:
                            if e.winerror == 109:  # ERROR_BROKEN_PIPE
                                logger.info("클라이언트 연결 끊김")
                                break
                            else:
                                logger.error(f"파이프 읽기 오류: {e}")
                                break
                    
                    # 파이프 정리
                    win32file.CloseHandle(pipe)
                
                except Exception as e:
                    logger.error(f"파이프 서버 오류: {e}")
                    time.sleep(1)
        
        except ImportError:
            logger.warning("Windows API를 사용할 수 없습니다. TCP 소켓 사용을 권장합니다.")
        except Exception as e:
            logger.error(f"파이프 서버 루프 오류: {e}")


class TCPIPCServer:
    """TCP 기반 IPC 서버 (크로스 플랫폼)"""
    
    def __init__(self, host: str = 'localhost', port: int = 9876):
        self.host = host
        self.port = port
        self.is_running = False
        self.server_socket = None
        self.server_thread = None
        self.client_connections = {}
        self.message_callbacks = []
        self.message_queue = queue.PriorityQueue()
    
    def add_callback(self, callback: Callable[[IPCMessage], None]):
        """메시지 콜백 등록"""
        self.message_callbacks.append(callback)
    
    def start(self) -> bool:
        """TCP IPC 서버 시작"""
        if self.is_running:
            return True
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.is_running = True
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
            logger.info(f"✅ TCP IPC 서버 시작: {self.host}:{self.port}")
            return True
        
        except Exception as e:
            logger.error(f"TCP IPC 서버 시작 실패: {e}")
            return False
    
    def stop(self):
        """TCP IPC 서버 중지"""
        self.is_running = False
        
        # 모든 클라이언트 연결 종료
        for client_id, conn in list(self.client_connections.items()):
            try:
                conn.close()
            except Exception:
                pass
        
        # 서버 소켓 종료
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        
        # 서버 스레드 종료 대기
        if self.server_thread:
            self.server_thread.join(timeout=5.0)
        
        logger.info("TCP IPC 서버 중지됨")
    
    def _server_loop(self):
        """서버 메인 루프"""
        while self.is_running:
            try:
                # 클라이언트 연결 수락
                client_socket, client_address = self.server_socket.accept()
                client_id = f"{client_address[0]}:{client_address[1]}_{uuid.uuid4().hex[:8]}"
                
                self.client_connections[client_id] = client_socket
                logger.info(f"클라이언트 연결: {client_id}")
                
                # 클라이언트 처리 스레드 시작
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_id, client_socket),
                    daemon=True
                )
                client_thread.start()
            
            except Exception as e:
                if self.is_running:
                    logger.error(f"클라이언트 수락 오류: {e}")
                    time.sleep(1)
    
    def _handle_client(self, client_id: str, client_socket: socket.socket):
        """클라이언트 처리"""
        try:
            while self.is_running:
                # 메시지 길이 읽기 (4바이트)
                length_data = self._recv_all(client_socket, 4)
                if not length_data:
                    break
                
                message_length = struct.unpack('!I', length_data)[0]
                
                # 메시지 본체 읽기
                message_data = self._recv_all(client_socket, message_length)
                if not message_data:
                    break
                
                # 메시지 파싱
                try:
                    message_str = message_data.decode('utf-8')
                    message = IPCMessage.from_json(message_str)
                    message.sender = client_id  # 발신자 정보 추가
                    
                    logger.debug(f"메시지 수신: {message.message_type} from {client_id}")
                    
                    # 콜백 호출
                    for callback in self.message_callbacks:
                        try:
                            callback(message)
                        except Exception as e:
                            logger.error(f"콜백 실행 오류: {e}")
                
                except Exception as e:
                    logger.error(f"메시지 파싱 오류: {e}")
        
        except Exception as e:
            logger.error(f"클라이언트 처리 오류 {client_id}: {e}")
        
        finally:
            # 클라이언트 정리
            try:
                client_socket.close()
                del self.client_connections[client_id]
                logger.info(f"클라이언트 연결 해제: {client_id}")
            except Exception as e:
                logger.error(f"클라이언트 정리 오류 {client_id}: {e}")
    
    def _recv_all(self, sock: socket.socket, length: int) -> Optional[bytes]:
        """지정된 길이만큼 데이터 수신"""
        data = b''
        while len(data) < length:
            try:
                chunk = sock.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
            except Exception:
                return None
        return data
    
    def send_message(self, message: IPCMessage, client_id: str = None) -> bool:
        """메시지 전송"""
        try:
            message_json = message.to_json()
            message_bytes = message_json.encode('utf-8')
            message_length = len(message_bytes)
            
            # 길이 헤더 + 메시지 본체
            full_message = struct.pack('!I', message_length) + message_bytes
            
            if client_id:
                # 특정 클라이언트에게 전송
                if client_id in self.client_connections:
                    try:
                        self.client_connections[client_id].send(full_message)
                        return True
                    except Exception as e:
                        logger.error(f"메시지 전송 실패 to {client_id}: {e}")
                        return False
                else:
                    logger.warning(f"클라이언트를 찾을 수 없음: {client_id}")
                    return False
            else:
                # 모든 클라이언트에게 브로드캐스트
                success_count = 0
                for cid, conn in list(self.client_connections.items()):
                    try:
                        conn.send(full_message)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"브로드캐스트 실패 to {cid}: {e}")
                
                return success_count > 0
        
        except Exception as e:
            logger.error(f"메시지 전송 준비 오류: {e}")
            return False


class IPCClient:
    """IPC 클라이언트"""
    
    def __init__(self, host: str = 'localhost', port: int = 9876):
        self.host = host
        self.port = port
        self.socket = None
        self.is_connected = False
        self.client_id = f"client_{uuid.uuid4().hex[:8]}"
    
    def connect(self) -> bool:
        """서버에 연결"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            
            logger.info(f"✅ IPC 서버에 연결됨: {self.host}:{self.port}")
            return True
        
        except Exception as e:
            logger.error(f"IPC 서버 연결 실패: {e}")
            return False
    
    def disconnect(self):
        """서버 연결 해제"""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
        self.is_connected = False
        logger.info("IPC 서버 연결 해제됨")
    
    def send_message(self, message: IPCMessage) -> bool:
        """메시지 전송"""
        if not self.is_connected:
            return False
        
        try:
            message.sender = self.client_id
            message_json = message.to_json()
            message_bytes = message_json.encode('utf-8')
            message_length = len(message_bytes)
            
            # 길이 헤더 + 메시지 본체
            full_message = struct.pack('!I', message_length) + message_bytes
            self.socket.send(full_message)
            
            logger.debug(f"메시지 전송: {message.message_type}")
            return True
        
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")
            self.is_connected = False
            return False


class IntegratedIPCManager:
    """통합 IPC 관리자"""
    
    def __init__(self):
        self.shared_memory = SharedMemoryManager()
        self.tcp_server = TCPIPCServer()
        self.message_handlers = {}
        self.is_running = False
    
    def register_handler(self, message_type: str, handler: Callable[[IPCMessage], Optional[IPCMessage]]):
        """메시지 핸들러 등록"""
        self.message_handlers[message_type] = handler
        logger.info(f"메시지 핸들러 등록: {message_type}")
    
    def start(self) -> bool:
        """IPC 관리자 시작"""
        try:
            # 공유 메모리 초기화
            if not self.shared_memory.initialize(create=True):
                logger.error("공유 메모리 초기화 실패")
                return False
            
            # TCP 서버 시작
            self.tcp_server.add_callback(self._handle_message)
            if not self.tcp_server.start():
                logger.error("TCP IPC 서버 시작 실패")
                return False
            
            self.is_running = True
            logger.info("✅ 통합 IPC 관리자 시작 완료")
            return True
        
        except Exception as e:
            logger.error(f"IPC 관리자 시작 실패: {e}")
            return False
    
    def stop(self):
        """IPC 관리자 중지"""
        self.is_running = False
        self.tcp_server.stop()
        self.shared_memory.close()
        logger.info("통합 IPC 관리자 중지됨")
    
    def _handle_message(self, message: IPCMessage):
        """메시지 처리"""
        try:
            logger.debug(f"메시지 처리: {message.message_type} from {message.sender}")
            
            # 핸들러 실행
            if message.message_type in self.message_handlers:
                handler = self.message_handlers[message.message_type]
                response = handler(message)
                
                # 응답 메시지가 있으면 전송
                if response:
                    response.receiver = message.sender
                    self.tcp_server.send_message(response, message.sender)
            else:
                logger.warning(f"알 수 없는 메시지 타입: {message.message_type}")
        
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")
    
    def broadcast_message(self, message_type: str, data: Dict[str, Any]) -> bool:
        """메시지 브로드캐스트"""
        try:
            message = IPCMessage(
                message_id=uuid.uuid4().hex,
                message_type=message_type,
                timestamp=time.time(),
                sender="ipc_manager",
                receiver="*",
                data=data
            )
            
            return self.tcp_server.send_message(message)
        
        except Exception as e:
            logger.error(f"메시지 브로드캐스트 오류: {e}")
            return False


# 샘플 메시지 핸들러들
def handle_packet_data(message: IPCMessage) -> Optional[IPCMessage]:
    """패킷 데이터 처리 핸들러"""
    try:
        packet_data = message.data
        logger.info(f"패킷 데이터 수신: {packet_data.get('file_name')} - {packet_data.get('data_count')}개")
        
        # 처리 결과 응답
        return IPCMessage(
            message_id=uuid.uuid4().hex,
            message_type="packet_data_ack",
            timestamp=time.time(),
            sender="ipc_manager",
            receiver=message.sender,
            data={"status": "processed", "original_id": message.message_id}
        )
    
    except Exception as e:
        logger.error(f"패킷 데이터 처리 오류: {e}")
        return None


def handle_status_request(message: IPCMessage) -> Optional[IPCMessage]:
    """상태 요청 처리 핸들러"""
    try:
        status_data = {
            "server_status": "running",
            "timestamp": time.time(),
            "uptime": time.time() - message.timestamp
        }
        
        return IPCMessage(
            message_id=uuid.uuid4().hex,
            message_type="status_response",
            timestamp=time.time(),
            sender="ipc_manager",
            receiver=message.sender,
            data=status_data
        )
    
    except Exception as e:
        logger.error(f"상태 요청 처리 오류: {e}")
        return None


# 사용 예제
if __name__ == "__main__":
    # IPC 관리자 테스트
    ipc_manager = IntegratedIPCManager()
    
    # 핸들러 등록
    ipc_manager.register_handler("packet_data", handle_packet_data)
    ipc_manager.register_handler("status_request", handle_status_request)
    
    try:
        if ipc_manager.start():
            logger.info("IPC 관리자가 시작되었습니다. Ctrl+C로 중지하세요.")
            
            while True:
                time.sleep(1)
        else:
            logger.error("IPC 관리자 시작 실패")
    
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    finally:
        ipc_manager.stop()