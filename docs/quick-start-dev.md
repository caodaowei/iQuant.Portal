# iQuant 本地开发快速启动指南

**适用环境**: Windows  
**更新日期**: 2026-04-15

---

## 🚀 快速启动（推荐方式）

### 方式一：使用 Docker Compose（最简单）

由于您的基础设施已经在运行，只需启动后端服务即可。

#### 步骤 1: 检查基础设施状态

```powershell
# 检查 Docker 容器
docker compose ps

# 应该看到以下服务正在运行:
# ✅ postgres (数据库)
# ✅ redis (缓存)
# ⚠️  celery-worker (可能不健康，需要重启)
# ❌  iquant-fastapi (需要启动)
# ❌  iquant-flask (可选)
```

#### 步骤 2: 启动 FastAPI 后端服务

```powershell
# 在项目根目录执行
docker compose up -d iquant-fastapi

# 查看日志
docker compose logs -f iquant-fastapi
```

#### 步骤 3: 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| FastAPI 后端 | http://localhost:8000 | 主后端 API |
| API 文档 | http://localhost:8000/api/docs | Swagger UI |
| 系统状态 | http://localhost:8000/api/status | 健康检查 |
| 前端应用 | http://localhost:3000 | Vue 3 前端 (如果已启动) |

---

### 方式二：本地 Python 环境运行

如果您希望在本地 Python 环境中运行（便于调试），请按以下步骤操作。

#### 前置条件

1. **Python 3.9+** 已安装
2. **PostgreSQL** 运行在 `localhost:5433` (Docker)
3. **Redis** 运行在 `localhost:6379` (Docker)

#### 步骤 1: 激活 Python 环境

根据您的环境选择:

**如果使用 conda:**
```powershell
conda activate iQuant
```

**如果使用 venv:**
```powershell
.\venv\Scripts\Activate.ps1
```

**如果直接安装:**
```powershell
# 直接使用 python 命令
python --version
```

#### 步骤 2: 安装依赖

```powershell
pip install -r requirements.txt
```

如果遇到 TA-Lib 安装问题:
```powershell
# 从 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib 下载对应版本
pip install TA_Lib‑0.4.28‑cp39‑cp39‑win_amd64.whl
```

#### 步骤 3: 验证配置

检查 `config/.env` 文件中的配置是否正确:

```env
DB_HOST=localhost
DB_PORT=5433  # Docker 映射的端口
DB_NAME=iquant
DB_USER=iquant
DB_PASSWORD=iquant123

REDIS_HOST=localhost
REDIS_PORT=6379
```

#### 步骤 4: 执行数据库迁移（首次运行）

```powershell
# 连接到 Docker 中的 PostgreSQL
docker exec -i iquant-postgres psql -U iquant -d iquant -f /dev/stdin < db/migrations/001_create_base_tables.sql
docker exec -i iquant-postgres psql -U iquant -d iquant -f /dev/stdin < db/migrations/002_create_verification_table.sql
docker exec -i iquant-postgres psql -U iquant -d iquant -f /dev/stdin < db/migrations/003_create_timing_tables.sql
docker exec -i iquant-postgres psql -U iquant -d iquant -f /dev/stdin < db/migrations/004_create_backtest_tables.sql
docker exec -i iquant-postgres psql -U iquant -d iquant -f /dev/stdin < db/migrations/005_create_risk_tables.sql
docker exec -i iquant-postgres psql -U iquant -d iquant -f /dev/stdin < db/migrations/006_create_trading_tables.sql
docker exec -i iquant-postgres psql -U iquant -d iquant -f /dev/stdin < db/migrations/007_create_security_tables.sql
docker exec -i iquant-postgres psql -U iquant -d iquant -f /dev/stdin < db/migrations/008_performance_optimization.sql
```

#### 步骤 5: 启动 FastAPI 服务

```powershell
# 开发模式（自动重载）
python -m uvicorn web.app_async:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
python -m uvicorn web.app_async:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 步骤 6: 启动 Celery Worker（可选，用于异步任务）

打开新的 PowerShell 窗口:

```powershell
celery -A celery_worker.celery worker --loglevel=info --concurrency=2
```

#### 步骤 7: 启动前端（可选）

打开新的 PowerShell 窗口:

```powershell
cd frontend
npm install  # 首次运行
npm run dev
```

---

## 🔧 常用开发命令

### 后端开发

```powershell
# 启动 FastAPI (开发模式)
python -m uvicorn web.app_async:app --reload

# 启动 Flask (兼容模式)
python -m flask --app web.app run --host 0.0.0.0 --port 5000

# 运行测试
pytest tests/ -v

# 运行单个测试
pytest tests/test_backtest_engine.py -v

# 检查代码质量
flake8 core/ web/

# 格式化代码
black core/ web/
```

### 前端开发

```powershell
cd frontend

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 类型检查
npm run type-check

# 代码格式化
npm run format
```

### Docker 管理

```powershell
# 查看所有容器
docker compose ps

# 查看日志
docker compose logs -f [service_name]

# 重启服务
docker compose restart [service_name]

# 停止所有服务
docker compose down

# 完全清理（包括数据卷）
docker compose down -v

# 重新构建并启动
docker compose up -d --build
```

---

## 🐛 故障排查

### 1. 数据库连接失败

**症状**: `Connection refused` 或 `Authentication failed`

**解决方案**:
```powershell
# 检查 PostgreSQL 是否运行
docker ps | findstr postgres

# 测试数据库连接
docker exec -it iquant-postgres psql -U iquant -d iquant -c "SELECT 1;"

# 查看数据库日志
docker logs iquant-postgres

# 确认端口映射
netstat -ano | findstr ":5433"
```

### 2. Redis 连接失败

**症状**: `Redis connection error`

**解决方案**:
```powershell
# 检查 Redis 是否运行
docker ps | findstr redis

# 测试 Redis 连接
docker exec -it iquantportal-redis-1 redis-cli ping

# 查看 Redis 日志
docker logs iquantportal-redis-1
```

### 3. 端口被占用

**症状**: `Address already in use`

**解决方案**:
```powershell
# 查看端口占用
netstat -ano | findstr ":8000"

# 停止占用进程
taskkill /F /PID <PID>

# 或者修改端口
python -m uvicorn web.app_async:app --port 8001
```

### 4. Celery Worker 不健康

**症状**: Celery worker 显示 unhealthy

**解决方案**:
```powershell
# 重启 Celery worker
docker compose restart celery-worker

# 查看日志
docker compose logs celery-worker

# 重新构建
docker compose up -d --build celery-worker
```

### 5. 前端无法连接后端

**症状**: API 请求失败

**解决方案**:
```powershell
# 检查前端代理配置
cat frontend/vite.config.ts

# 确保后端正在运行
curl http://localhost:8000/api/status

# 检查 CORS 配置
# 在 web/app_async.py 中确认 CORS 中间件配置
```

---

## 📝 开发工作流

### 典型开发流程

1. **启动基础设施**
   ```powershell
   docker compose up -d postgres redis
   ```

2. **启动后端服务**
   ```powershell
   python -m uvicorn web.app_async:app --reload
   ```

3. **启动前端服务**（如需）
   ```powershell
   cd frontend && npm run dev
   ```

4. **进行开发**
   - 修改代码
   - 浏览器自动刷新
   - 查看控制台日志

5. **运行测试**
   ```powershell
   pytest tests/ -v
   ```

6. **提交代码**
   ```powershell
   git add .
   git commit -m "feat: description"
   git push
   ```

---

## 🎯 下一步

- 📖 阅读 [系统功能文档](system-functions.md) 了解完整功能
- 📗 阅读 [系统设计文档](system-design.md) 理解系统设计
- 📙 阅读 [系统架构文档](system-architecture.md) 理解架构设计
- 🧪 运行测试确保功能正常
- 🚀 开始开发新功能或修复 bug

---

**文档维护**: Lingma (AI Assistant)  
**最后更新**: 2026-04-15
