@echo off
echo ================================
echo 클라우드 백업 라이브러리 설치
echo ================================

echo AWS S3 백업을 위한 boto3 설치...
pip install boto3

echo Google Cloud Storage 백업을 위한 라이브러리 설치...
pip install google-cloud-storage

echo Azure Blob Storage 백업을 위한 라이브러리 설치...  
pip install azure-storage-blob

echo 백업 시스템 성능 향상을 위한 추가 라이브러리...
pip install tqdm
pip install python-dateutil

echo ================================
echo 설치 완료! 백업 시스템 테스트...
echo ================================

python cloud\backup_manager.py

pause