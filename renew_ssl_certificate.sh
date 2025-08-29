#!/bin/bash
# SSL 인증서 갱신 스크립트
# 사용 전 환경에 맞게 수정 필요

echo "==================================="
echo "SSL 인증서 갱신 스크립트"
echo "==================================="

# 기존 인증서 백업
BACKUP_DIR="ssl_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "server.crt" ]; then
    cp server.crt "$BACKUP_DIR/"
    echo "✅ 기존 CRT 파일 백업"
fi

if [ -f "server.key" ]; then
    cp server.key "$BACKUP_DIR/"
    echo "✅ 기존 KEY 파일 백업"
fi

if [ -f "server.pfx" ]; then
    cp server.pfx "$BACKUP_DIR/"
    echo "✅ 기존 PFX 파일 백업"
fi

echo "📁 백업 디렉터리: $BACKUP_DIR"

# 방법 1: Let's Encrypt (Certbot) 사용 예시
echo "방법 1: Let's Encrypt 갱신 (수정 필요)"
echo "# certbot renew --cert-name your-domain.com"
echo "# certbot certonly --standalone -d your-domain.com"

# 방법 2: 자체 서명 인증서 생성 (개발용)
echo "방법 2: 자체 서명 인증서 생성 (개발용)"
echo "openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes"
echo "openssl pkcs12 -export -out server.pfx -inkey server.key -in server.crt"

# 방법 3: 상용 CA 인증서 설치
echo "방법 3: 상용 CA 인증서 설치"
echo "# 1. CSR 생성: openssl req -new -newkey rsa:2048 -nodes -keyout server.key -out server.csr"
echo "# 2. CA에 CSR 제출하여 인증서 발급 받기"
echo "# 3. 발급받은 인증서를 server.crt로 저장"
echo "# 4. PFX 파일 생성: openssl pkcs12 -export -out server.pfx -inkey server.key -in server.crt"

echo "==================================="
echo "갱신 후 다음 명령어로 인증서 확인:"
echo "python ssl_cert_manager.py"
echo "==================================="
