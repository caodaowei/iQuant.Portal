#!/bin/bash
# Docker Compose 部署脚本 - 统一部署所有服务

set -e

echo "=== iQuant Portal Docker Compose 部署 ==="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose 未安装"
    exit 1
fi

# 确定 docker compose 命令
if command -v docker compose &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# 加载环境变量
if [ -f .env ]; then
    echo "加载环境变量文件: .env"
    export $(cat .env | grep -v '^#' | xargs)
fi

# 停止并清理旧服务
echo "停止旧服务..."
$COMPOSE_CMD down --remove-orphans 2>/dev/null || true

# 构建最新镜像
echo "构建 Docker 镜像..."
$COMPOSE_CMD build --no-cache

# 启动所有服务（不包含监控组件）
echo "启动服务..."
$COMPOSE_CMD up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 健康检查
echo "执行健康检查..."

# 检查 FastAPI
if curl -sf http://localhost:8000/api/status > /dev/null; then
    echo "✅ FastAPI 服务正常 (端口 8000)"
else
    echo "⚠️ FastAPI 服务可能未正常启动"
fi

# 检查数据库
if curl -sf http://localhost:8000/api/status | grep -q '"database":"connected"'; then
    echo "✅ 数据库连接正常"
else
    echo "⚠️ 数据库连接可能有问题"
fi

# 检查 Redis
if curl -sf http://localhost:8000/api/status | grep -q '"redis":"connected"'; then
    echo "✅ Redis 连接正常"
else
    echo "⚠️ Redis 连接可能有问题"
fi

echo ""
echo "=== 部署完成 ==="
echo ""
echo "服务访问地址:"
echo "  - 前端应用:     http://localhost:3000 (需单独启动 npm run dev)"
echo "  - FastAPI:      http://localhost:8000"
echo "  - API 文档:     http://localhost:8000/api/docs"
echo "  - PostgreSQL:   localhost:5432"
echo "  - Redis:        localhost:6379"
echo ""
echo "查看服务状态: $COMPOSE_CMD ps"
echo "查看日志:     $COMPOSE_CMD logs -f"
echo "停止服务:     $COMPOSE_CMD down"
echo ""
echo "可选服务:"
echo "  - Celery Flower (监控): $COMPOSE_CMD --profile monitoring up -d flower"
echo "  - Prometheus/Grafana:   $COMPOSE_CMD --profile monitoring up -d"
