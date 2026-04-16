# Docker Compose 部署指南

## 架构概述

本项目使用 Docker Compose 统一部署所有服务，确保应用、数据库和缓存作为一个整体管理。

```
┌─────────────────────────────────────────────────────┐
│              Docker Compose Stack                    │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐   ┌──────────────┐                │
│  │  iquant-     │   │   celery-    │                │
│  │  fastapi     │──▶│   worker     │                │
│  │  :8000       │   │              │                │
│  └──────┬───────┘   └──────┬───────┘                │
│         │                  │                         │
│         ▼                  ▼                         │
│  ┌──────────────┐   ┌──────────────┐                │
│  │   postgres   │   │    redis     │                │
│  │   :5432      │   │   :6379      │                │
│  └──────────────┘   └──────────────┘                │
│                                                      │
│  可选服务 (profiles):                                 │
│  ┌──────────────┐   ┌──────────────┐                │
│  │   flower     │   │  prometheus  │                │
│  │   :5555      │   │   :9090      │                │
│  └──────────────┘   └──────┬───────┘                │
│                            │                         │
│                   ┌────────▼───────┐                │
│                   │    grafana     │                │
│                   │    :3100       │                │
│                   └────────────────┘                │
└─────────────────────────────────────────────────────┘
```

## 端口分配

| 服务 | 容器内端口 | 主机端口 | 说明 |
|------|-----------|---------|------|
| FastAPI | 8000 | 8000 | 主后端 API |
| PostgreSQL | 5432 | 5433 | 数据库（外部访问用5433） |
| Redis | 6379 | 6379 | 缓存 |
| Celery Flower | 5555 | 5555 | 任务监控（可选） |
| Prometheus | 9090 | 9090 | 指标收集（可选） |
| Grafana | 3000 | 3100 | 可视化面板（可选） |

> **注意**: Grafana 使用 3100 端口以避免与前端 Vite (3000) 冲突

## 快速开始

### 1. 前置条件

```bash
# 检查 Docker 版本
docker --version        # 需要 >= 20.10
docker compose version  # 需要 >= 2.0

# 或者使用 docker-compose
docker-compose --version
```

### 2. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，设置必要的参数
# 默认配置已适用于 Docker Compose 环境
```

### 3. 启动所有服务

```bash
# 方式一：使用部署脚本（推荐）
./deploy.sh

# 方式二：手动使用 docker compose
docker compose build
docker compose up -d
```

### 4. 验证部署

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 健康检查
curl http://localhost:8000/api/status
```

### 5. 访问服务

- **API 文档**: http://localhost:8000/api/docs
- **FastAPI 状态**: http://localhost:8000/api/status
- **PostgreSQL**: localhost:5433 (外部连接)
- **Redis**: localhost:6379

## 常用命令

### 服务管理

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重启特定服务
docker compose restart iquant-fastapi

# 重新构建并启动
docker compose up -d --build

# 完全清理（包括数据卷）
docker compose down -v
```

### 日志查看

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f iquant-fastapi
docker compose logs -f postgres

# 查看最近 100 行
docker compose logs --tail=100 iquant-fastapi
```

### 进入容器

```bash
# 进入 FastAPI 容器
docker compose exec iquant-fastapi bash

# 进入数据库容器
docker compose exec postgres psql -U iquant

# 进入 Redis
docker compose exec redis redis-cli
```

### 数据库操作

```bash
# 备份数据库
docker compose exec postgres pg_dump -U iquant > backup.sql

# 恢复数据库
docker compose exec -T postgres psql -U iquant < backup.sql

# 查看数据库大小
docker compose exec postgres psql -U iquant -c "SELECT pg_size_pretty(pg_database_size('iquant'));"
```

## 可选服务

### 启用监控组件

```bash
# 启动 Celery Flower（任务监控）
docker compose --profile monitoring up -d flower

# 启动 Prometheus + Grafana
docker compose --profile monitoring up -d prometheus grafana

# 启动所有监控服务
docker compose --profile monitoring up -d
```

### 访问监控面板

- **Celery Flower**: http://localhost:5555
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3100
  - 用户名: `admin`
  - 密码: `admin` (或 `.env` 中设置的值)

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker compose logs iquant-fastapi

# 检查端口占用
netstat -tlnp | grep -E '8000|5433|6379'

# 检查容器健康状态
docker compose ps
```

### 数据库连接失败

```bash
# 检查数据库是否就绪
docker compose exec postgres pg_isready -U iquant

# 查看数据库日志
docker compose logs postgres

# 重置数据库（警告：会删除所有数据）
docker compose down -v
docker compose up -d postgres
```

### Redis 连接失败

```bash
# 检查 Redis 状态
docker compose exec redis redis-cli ping

# 查看 Redis 日志
docker compose logs redis
```

### 内存不足

```bash
# 限制服务内存（在 docker-compose.yml 中添加）
services:
  iquant-fastapi:
    deploy:
      resources:
        limits:
          memory: 512M
```

## 生产环境建议

1. **修改默认密码**: 更新 `.env` 中的 `DB_PASSWORD` 和 `GRAFANA_ADMIN_PASSWORD`
2. **使用外部卷**: 将数据卷挂载到持久化存储
3. **配置网络策略**: 限制不必要的端口暴露
4. **启用 HTTPS**: 使用反向代理（如 Nginx）添加 SSL
5. **定期备份**: 设置自动化数据库备份
6. **资源限制**: 为每个服务设置 CPU/内存限制

## 迁移指南

### 从独立容器迁移

如果您之前使用独立容器运行数据库和 Redis：

```bash
# 1. 备份现有数据
docker exec iquant-postgres pg_dump -U iquant > backup.sql
docker exec iquant-redis redis-cli BGSAVE

# 2. 停止独立容器
docker stop iquant-postgres iquant-redis
docker rm iquant-postgres iquant-redis

# 3. 使用 docker compose 启动
docker compose up -d

# 4. 恢复数据
docker compose exec -T postgres psql -U iquant < backup.sql
```

### 从本地开发迁移

```bash
# 1. 确保本地服务已停止
# 停止 Python 进程

# 2. 启动 docker compose
docker compose up -d

# 3. 更新前端代理配置
# frontend/vite.config.ts 中的 target 改为 http://localhost:8000
```
