FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치 (레이어 캐싱 최적화)
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY ../*.py .
COPY ../static ./static
COPY ../datas ./datas

# 비root 사용자 생성 및 권한 설정
RUN useradd -m -u 1000 aura && \
    chown -R aura:aura /app

USER aura

# 포트 노출
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 서버 실행
CMD ["python", "main.py"]
