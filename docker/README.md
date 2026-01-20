# Docker 사용 가이드

## 📁 폴더 구조
```
docker/
├── Dockerfile          # Docker 이미지 빌드 설정
├── .dockerignore       # 빌드 시 제외할 파일
└── docker-run.sh       # 컨테이너 실행 스크립트
```

## 🚀 사용 방법

### 1. Docker 이미지 빌드

```bash
cd /home/enjoy/final
docker build -f docker/Dockerfile -t aura-server .
```

**주의:** `-f docker/Dockerfile` 옵션으로 Dockerfile 위치 지정

### 2. 컨테이너 실행

**방법 1: 스크립트 사용 (추천)**
```bash
cd docker
./docker-run.sh
```

**방법 2: 직접 실행**
```bash
docker run -d \
  --name aura \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/chroma_db_voyage:/app/chroma_db_voyage \
  -v $(pwd)/index_cache_voyage.pkl:/app/index_cache_voyage.pkl \
  -v $(pwd)/datas:/app/datas \
  aura-server
```

### 3. 컨테이너 관리

```bash
# 로그 확인
docker logs -f aura

# 컨테이너 중지
docker stop aura

# 컨테이너 시작
docker start aura

# 컨테이너 재시작
docker restart aura
```

## 🔄 코드 수정 후 재배포

```bash
# 프로젝트 루트에서
docker build -f docker/Dockerfile -t aura-server .
cd docker
./docker-run.sh
```

또는 한 줄로:
```bash
docker build -f docker/Dockerfile -t aura-server . && cd docker && ./docker-run.sh
```
