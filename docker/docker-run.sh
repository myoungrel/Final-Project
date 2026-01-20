#!/bin/bash

set -e  # Exit on error

echo "🚀 Starting AURA Docker Container..."

# 기존 컨테이너 중지 및 삭제
if docker ps -a | grep -q aura; then
    echo "🛑 Stopping existing container..."
    docker stop aura 2>/dev/null || true
    docker rm aura 2>/dev/null || true
fi

# 이미지 존재 확인
if ! docker images | grep -q aura-server; then
    echo "❌ Error: aura-server image not found!"
    echo "💡 Please build the image first: ./docker-build.sh"
    exit 1
fi

# 새 컨테이너 실행 (상위 디렉토리 기준)
echo "🐳 Starting new container..."
docker run -d \
  --name aura \
  -p 8000:8000 \
  --env-file ../.env \
  -v $(pwd)/../chroma_db_voyage:/app/chroma_db_voyage \
  -v $(pwd)/../index_cache_voyage.pkl:/app/index_cache_voyage.pkl \
  -v $(pwd)/../datas:/app/datas \
  --restart unless-stopped \
  aura-server:latest

echo "✅ Container started!"
echo ""
echo "⏳ Waiting for service to be ready..."
sleep 5

# Health check
for i in {1..10}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "✅ Service is healthy!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "⚠️  Service health check failed. Check logs:"
        docker logs aura --tail 50
        exit 1
    fi
    echo "   Attempt $i/10..."
    sleep 3
done

echo ""
echo "📊 Container Status:"
docker ps | grep aura

echo ""
echo "🌐 Server running at: http://localhost:8000"
echo "📝 View logs: docker logs -f aura"
echo "🛑 Stop container: docker stop aura"
