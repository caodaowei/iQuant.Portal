#!/bin/bash
# 手动部署脚本

set -e

echo "=== iQuant Portal 部署脚本 ==="

# 配置
IMAGE_NAME="ghcr.io/caodaowei/iquant.portal"
CONTAINER_NAME="iquant-portal"
PORT="5000"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    exit 1
fi

# 拉取最新镜像
echo "拉取最新镜像..."
docker pull ${IMAGE_NAME}:latest

# 停止旧容器
if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo "停止旧容器..."
    docker stop ${CONTAINER_NAME}
    docker rm ${CONTAINER_NAME}
fi

# 启动新容器
echo "启动新容器..."
docker run -d \
    --name ${CONTAINER_NAME} \
    -p ${PORT}:5000 \
    --restart unless-stopped \
    -e DB_HOST=${DB_HOST:-localhost} \
    -e DB_PORT=${DB_PORT:-5432} \
    -e DB_NAME=${DB_NAME:-iquant} \
    -e DB_USER=${DB_USER:-iquant} \
    -e DB_PASSWORD=${DB_PASSWORD:-} \
    ${IMAGE_NAME}:latest

# 等待服务启动
sleep 5

# 健康检查
if curl -sf http://localhost:${PORT}/api/status > /dev/null; then
    echo "✅ 部署成功! 服务运行在 http://localhost:${PORT}"
else
    echo "⚠️ 服务可能未正常启动，请检查日志:"
    docker logs ${CONTAINER_NAME}
fi
