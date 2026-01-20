#!/bin/bash

# AURA Docker Build Script
# This script builds the Docker image for the AURA service

set -e  # Exit on error

echo "🔨 Building AURA Docker Image..."

# Change to parent directory (project root)
cd "$(dirname "$0")/.."

# Build image with proper context
docker build \
  -f docker/Dockerfile \
  -t aura-server:latest \
  -t aura-server:$(date +%Y%m%d-%H%M%S) \
  .

echo "✅ Build complete!"
echo ""
echo "📦 Available images:"
docker images | grep aura-server

echo ""
echo "🚀 To run the container, use: cd docker && ./docker-run.sh"
