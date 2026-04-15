#!/bin/bash

# iQuant 异步服务启动脚本

echo "======================================"
echo "iQuant 异步服务启动"
echo "======================================"
echo ""

# 检查 Redis
echo "检查 Redis 连接..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis 未运行，请先启动 Redis"
    echo "   Docker: docker-compose up -d redis"
    echo "   本地: redis-server"
    exit 1
fi
echo "✓ Redis 已连接"
echo ""

# 启动 Celery Worker
echo "启动 Celery Worker..."
celery -A core.task_queue worker \
    --loglevel=info \
    --concurrency=4 \
    --pool=prefork \
    --hostname=worker1@%h \
    --queues=data_sync,backtest,ai_analysis &

CELERY_PID=$!
echo "✓ Celery Worker 已启动 (PID: $CELERY_PID)"
echo ""

# 启动 FastAPI
echo "启动 FastAPI 应用..."
uvicorn web.app_async:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload &

FASTAPI_PID=$!
echo "✓ FastAPI 已启动 (PID: $FASTAPI_PID)"
echo ""

echo "======================================"
echo "服务启动完成"
echo "======================================"
echo ""
echo "FastAPI 文档: http://localhost:8000/api/docs"
echo "任务监控: celery -A core.task_queue inspect active"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待中断信号
trap "kill $CELERY_PID $FASTAPI_PID; exit" INT TERM

wait
