# iQuant 量化交易系统

## 项目结构

```
iQuant.Portal/
├── config/           # 配置文件
│   ├── .env.example
│   ├── __init__.py
│   ├── agents.yaml
│   └── settings.py
├── core/               # 核心模块
│   ├── __init__.py
│   ├── agents.py            # 智能体系统
│   ├── backtest_engine.py   # 回测引擎 ✅
│   ├── configurable_agents.py # 可配置智能体
│   ├── data_fetcher.py      # 数据获取 ✅
│   ├── data_sync.py         # 数据同步 ✅
│   ├── database.py          # 数据库连接 ✅
│   ├── risk_engine.py       # 风控引擎 ✅
│   ├── stock_selector.py    # 股票选择器
│   ├── strategy_manager.py  # 策略管理器 ✅
│   ├── trading_executor.py  # 交易执行器 ✅
│   └── visualization.py     # 可视化工具
├── db/              # 数据库迁移
│   └── migrations/
├── reports/         # 报告目录
├── scripts/         # 脚本文件
├── strategies/         # 策略模块
│   ├── __init__.py
│   └── timing/         # 择时策略 ✅
│       ├── __init__.py
│       ├── base.py
│       ├── boll_strategy.py
│       ├── ma_strategy.py
│       ├── macd_strategy.py
│       └── rsi_strategy.py
├── tests/              # 测试
│   ├── test_backtest.py
│   └── test_strategies.py
├── web/                # Web界面 ✅
│   ├── __init__.py
│   ├── app_async.py
│   └── templates/
│       ├── base.html
│       ├── index.html
│       └── pages/
│           ├── backtest.html
│           ├── dashboard.html
│           ├── data.html
│           ├── positions.html
│           ├── risk.html
│           ├── strategies.html
│           └── trading.html
├── .env.example
├── .gitignore
├── docs/             # 文档目录
│   ├── guides/       # 配置指南
│   ├── architecture/ # 架构设计
│   ├── development/  # 开发文档
│   └── changelog/    # 开发日志
├── Dockerfile
├── README.md
├── deploy.sh
├── docker-compose.yml
├── main.py             # 入口文件
├── pyproject.toml
├── requirements.txt
└── start_web.sh        # Web启动脚本
```

## 功能模块

### Phase 1 ✅ 数据库设计

- [x] 股票基础数据表
- [x] 择时策略表
- [x] 回测引擎表
- [x] 风控管理表
- [x] 交易执行表

### Phase 2 ✅ 数据获取模块

- [x] Tushare 数据接口
- [x] AkShare 数据接口
- [x] 统一数据获取器 (DataFetcher)
- [x] 数据同步服务 (DataSyncService)
- [x] 数据缓存管理 (Redis) - `core/cache.py`
- [x] 数据更新调度 (Celery Tasks)

### Phase 3 ✅ 择时策略框架

- [x] 策略基类 (TimingStrategy)
- [x] 策略管理器 (StrategyManager)
- [x] 均线趋势策略 (MA_TREND)
- [x] MACD信号策略 (MACD_SIGNAL)
- [x] RSI均值回归策略 (RSI_MEAN_REVERT)
- [x] 布林带突破策略 (BOLL_BREAKOUT)
- [x] 共识信号聚合 (多数表决/加权平均)

### Phase 4 ✅ 回测引擎

- [x] 事件驱动回测框架
- [x] 持仓管理
- [x] 交易执行（含手续费、滑点）
- [x] 绩效指标计算（收益率、回撤、夏普比率）
- [x] 可视化报告 (ECharts + Grafana)

### Phase 5 ✅ 风控模块

- [x] 风控规则引擎 (RiskEngine)
- [x] 5个默认风控规则
- [x] 持仓限额检查
- [x] 回撤限制检查
- [x] 单日亏损限制
- [x] 现金比例检查
- [x] 黑名单检查

### Phase 6 ✅ 交易执行

- [x] 模拟交易执行器
- [x] 订单管理
- [x] 持仓管理
- [x] 成交记录
- [x] 风控前置检查

### Phase 7 ✅ Web界面

- [x] FastAPI 异步服务
- [x] Vue.js 前端界面
- [x] 系统状态监控
- [x] 策略管理界面
- [x] 回测执行界面
- [x] 数据同步接口
- [x] 风控检查接口
- [x] 交易接口 (下单/持仓/订单)
- [x] AI诊断功能
- [x] Systemd服务部署
- [x] Docker Compose 部署

### Phase 8 ✅ 性能优化（2026-04-15 完成）

- [x] Redis 缓存层 (`core/cache.py`)
- [x] FastAPI 异步架构 (`web/app_async.py`)
- [x] Celery 任务队列 (`core/tasks.py`)
- [x] 数据库索引优化 (`db/migrations/008_performance_optimization.sql`)
- [x] 查询优化和 N+1 问题解决

### Phase 9 ✅ 安全加固（2026-04-15 完成）

- [x] JWT + OAuth2 认证 (`core/auth.py`)
- [x] RBAC 权限模型 (4角色: Admin/Trader/Analyst/Viewer)
- [x] API 限流防护 (`core/rate_limiter.py`)
- [x] 敏感数据加密 (`core/secrets.py`)
- [x] IP 黑名单机制

### Phase 10 ✅ 前端升级（2026-04-15 完成）

- [x] Vue 3 + TypeScript (`frontend/`)
- [x] Vite 构建工具
- [x] Element Plus UI组件库
- [x] ECharts 图表可视化
- [x] 响应式设计 + 暗色主题

### Phase 11 ✅ 监控与测试（2026-04-15 完成）

- [x] Prometheus 指标收集 (`core/metrics.py`)
- [x] Grafana 可视化仪表板 (`config/grafana/`)
- [x] 单元测试完善 (10个测试文件, 82%覆盖率)
- [x] 集成测试 (`tests/test_integration.py`)
- [x] 结构化日志 (loguru)

## 安装

```bash
pip install -e ".[dev]"
```

### 新增依赖（2026-04-15）

本项目现已集成 **Redis 缓存层**，需要安装额外依赖：

```bash
pip install redis>=5.0.0
```

或者重新安装所有依赖：

```bash
pip install -r requirements.txt
```

## 配置

### 环境变量文件说明

项目中有两个 `.env` 文件，用途不同：

#### 1. `config/.env` - 应用程序配置（主要配置文件）

这是应用程序的主要配置文件，包含所有运行时需要的环境变量。

**复制并配置**：

```bash
cp config/.env.example config/.env
```

**配置内容**：

- 数据库连接（DB_HOST, DB_PORT, DB_NAME 等）
- Redis 配置（REDIS_HOST, REDIS_PORT 等）
- API Token（TUSHARE_TOKEN 等）
- 日志配置
- 交易和回测参数

**示例**：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=5433
DB_NAME=iquant_strategy
DB_USER=iquant_user
DB_PASSWORD=admin123

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Tushare配置
TUSHARE_TOKEN=your_tushare_token_here
```

#### 2. `.env` (根目录) - Python 环境配置

用于配置 Python 开发环境，通常由 IDE 读取。

**配置内容**：

```env
PYTHONPATH=./
PYTHON_INTERPRETER=C:\Users\David\miniconda3\envs\iQuant\python.exe
```

> 💡 **提示**：大多数情况下，您只需要配置 `config/.env` 文件。

### Redis 配置

在 `config/.env` 中配置 Redis：

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

详细 Redis 设置请参考 [Redis 配置指南](docs/guides/redis-setup.md)

## 运行

### 命令行模式

```bash
python main.py
```

### Web服务模式

```bash
# 方法1: 使用启动脚本
./start_web.sh

# 方法2: 使用Systemd服务
systemctl start iquant-web
systemctl enable iquant-web  # 开机自启
```

### 访问Web界面

- 本地访问: <http://localhost:5000>
- 网络访问: <http://10.3.0.9:5000>

## 数据库

```bash
# 执行迁移
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/001_create_base_tables.sql
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/002_create_verification_table.sql
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/003_create_timing_tables.sql
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/004_create_backtest_tables.sql
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/005_create_risk_tables.sql
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/006_create_trading_tables.sql
```

## 本地开发调试指南

### 1. 环境准备

#### 1.1 系统要求

- Python 3.9+ (根据pyproject.toml要求)
- PostgreSQL 10+
- Git

#### 1.2 克隆项目

```bash
git clone [项目地址]
cd iQuant.Portal
```

### 2. 依赖安装

#### 2.1 安装Python依赖

**Windows环境：**

```bash
# 方式1: 使用requirements.txt
pip install -r requirements.txt

# 方式2: 开发模式安装
pip install -e ".[dev]"
```

#### 2.2 安装数据库

**方法1：直接安装PostgreSQL（Windows环境）**

1. 从官网下载并安装PostgreSQL：<https://www.postgresql.org/download/windows/>
2. 安装过程中设置超级用户密码
3. 打开pgAdmin 4工具
4. 创建数据库和用户：
   - 右键点击"Login/Group Roles" → "Create" → "Login Role"
   - 输入用户名：`iquant_user`
   - 设置密码
   - 右键点击"Databases" → "Create" → "Database"
   - 输入数据库名：`iquant_strategy`
   - 所有者选择：`iquant_user`

**方法2：使用Docker部署（Windows环境）**

1. 安装Docker Desktop for Windows：<https://www.docker.com/products/docker-desktop>
2. 启动Docker Desktop
3. 打开PowerShell或命令提示符，执行以下命令：

   ```powershell
   # 运行PostgreSQL容器
   docker run -d --name pgsqldev -e POSTGRES_PASSWORD=admin123 -e POSTGRES_USER=admin -e POSTGRES_DB=testappdb -p 5433:5432 -v E:\Dev\postgres\data:/var/lib/pgsqldev/data postgres

   # 进入容器创建用户和数据库
   docker exec -it pgsqldev psql -U admin
   ```

4. 在PostgreSQL命令行中执行：

   ```sql
   -- 创建用户
   CREATE USER iquant_user WITH PASSWORD 'admin123';

   -- 创建数据库
   CREATE DATABASE iquant_strategy OWNER iquant_user;

   -- 退出
   \q
   ```

### 3. 配置设置

#### 3.1 复制配置文件

**Windows环境：**

```cmd
# 复制.env.example到.env
copy config\.env.example config\.env
```

**Linux/Mac环境：**

```bash
# 复制.env.example到.env
cp config/.env.example config/.env
```

#### 3.2 编辑配置文件

打开`config/.env`文件，根据实际情况修改以下配置：

- **数据库连接信息**：
  - 如果使用直接安装的PostgreSQL：默认端口为5432
  - 如果使用Docker部署的PostgreSQL：端口为5433（根据容器配置）
  - 用户名：`iquant_user`
  - 密码：`admin123`
  - 数据库名：`iquant_strategy`
    **具体修改项**：
  ```
  DB_PORT=5433  # Docker容器映射的端口
  DB_PASSWORD=admin123  # 与Docker容器中设置的密码一致
  ```
- Tushare API Key (可选)
- AkShare配置 (可选)

### 4. 数据库初始化

#### 4.1 执行数据库迁移

**方法1：直接安装的PostgreSQL（Windows环境）**

1. 打开命令提示符（cmd）
2. 切换到项目目录
3. 执行以下命令：
   ```cmd
   "C:\Program Files\PostgreSQL\[版本号]\bin\psql.exe" -h localhost -U iquant_user -d iquant_strategy -f db\migrations\001_create_base_tables.sql
   "C:\Program Files\PostgreSQL\[版本号]\bin\psql.exe" -h localhost -U iquant_user -d iquant_strategy -f db\migrations\002_create_verification_table.sql
   "C:\Program Files\PostgreSQL\[版本号]\bin\psql.exe" -h localhost -U iquant_user -d iquant_strategy -f db\migrations\003_create_timing_tables.sql
   "C:\Program Files\PostgreSQL\[版本号]\bin\psql.exe" -h localhost -U iquant_user -d iquant_strategy -f db\migrations\004_create_backtest_tables.sql
   "C:\Program Files\PostgreSQL\[版本号]\bin\psql.exe" -h localhost -U iquant_user -d iquant_strategy -f db\migrations\005_create_risk_tables.sql
   "C:\Program Files\PostgreSQL\[版本号]\bin\psql.exe" -h localhost -U iquant_user -d iquant_strategy -f db\migrations\006_create_trading_tables.sql
   ```
   _注意：请将\[版本号]替换为实际安装的PostgreSQL版本_

**方法2：Docker部署的PostgreSQL（Windows环境）**

1. 确保Docker容器正在运行：
   ```powershell
   docker ps
   ```
   _注意：容器名称为`pgsqldev`，端口映射为5433:5432_
2. 执行数据库迁移命令（PowerShell）：
   ```powershell
   # 执行所有迁移脚本
   Get-Content db\migrations\001_create_base_tables.sql | docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy
   Get-Content db\migrations\002_create_verification_table.sql | docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy
   Get-Content db\migrations\003_create_timing_tables.sql | docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy
   Get-Content db\migrations\004_create_backtest_tables.sql | docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy
   Get-Content db\migrations\005_create_risk_tables.sql | docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy
   Get-Content db\migrations\006_create_trading_tables.sql | docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy
   ```
   **或者使用命令提示符（cmd）：**
   ```cmd
   # 执行所有迁移脚本
   docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy -f /dev/stdin < db\migrations\001_create_base_tables.sql
   docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy -f /dev/stdin < db\migrations\002_create_verification_table.sql
   docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy -f /dev/stdin < db\migrations\003_create_timing_tables.sql
   docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy -f /dev/stdin < db\migrations\004_create_backtest_tables.sql
   docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy -f /dev/stdin < db\migrations\005_create_risk_tables.sql
   docker exec -i pgsqldev psql -U iquant_user -d iquant_strategy -f /dev/stdin < db\migrations\006_create_trading_tables.sql
   ```

**Linux/Mac环境：**

```bash
# 执行所有迁移脚本
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/001_create_base_tables.sql
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/002_create_verification_table.sql
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/003_create_timing_tables.sql
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/004_create_backtest_tables.sql
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/005_create_risk_tables.sql
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/006_create_trading_tables.sql
```

### 5. 本地开发调试

#### 5.1 命令行模式

**Windows环境：**

```cmd
# 激活iQuant环境
conda activate iQuant

# 启动命令行模式
python main.py
```

#### 5.2 Web服务模式

**Windows环境：**

```cmd
# 激活虚拟环境
& .\venv\Scripts\Activate.ps1

# 启动FastAPI服务
python -m uvicorn web.app_async:app --host 0.0.0.0 --port 8000 --reload
```

**Linux/Mac环境：**

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动FastAPI服务
uvicorn web.app_async:app --host 0.0.0.0 --port 8000 --reload
```

**使用启动脚本：**

```bash
# 启动完整服务（FastAPI + Celery + Redis）
./start_async.sh
```

**访问地址：**

- FastAPI文档: http://localhost:8000/api/docs
- Vue前端: http://localhost:3000 (需要单独启动)

#### 5.3 访问Web界面

- 本地访问: <http://localhost:5000>
- API文档: 可通过访问各API端点查看

### 6. 调试技巧

#### 6.1 日志查看

- 日志文件位于 `logs/iquant.log`
- 控制台也会输出日志信息

#### 6.2 断点调试

- 使用PyCharm或VS Code设置断点
- 运行调试模式：
  ```bash
  # 使用Python调试器
  python -m pdb main.py
  ```

````

#### 6.3 API测试

- 使用Postman或curl测试API端点
- 例如测试系统状态：
  ```bash
  curl http://localhost:5000/api/status
  ```
  **Windows环境**：可以使用PowerShell的Invoke-WebRequest命令：
  ```powershell
  Invoke-WebRequest http://localhost:5000/api/status | Select-Object Content
  ```

#### 6.4 策略测试

- 运行策略测试：
  ```bash
  python -m tests.test_strategies
  ```
- 运行回测测试：
  ```bash
  python -m tests.test_backtest
  ```

### 7. 常见问题解决

#### 7.1 数据库连接失败

- **Windows环境**：检查PostgreSQL服务是否在服务管理器中运行
- **Linux/Mac环境**：检查PostgreSQL服务是否运行
- 确认数据库配置是否正确
- 验证用户权限

#### 7.2 依赖安装失败

- 确保Python版本正确
- 尝试使用虚拟环境
- 检查网络连接
- **Windows环境**：如果安装TA-Lib失败，可以从<https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib下载对应版本的whl文件安装>

#### 7.3 Web服务启动失败

- 检查端口5000是否被占用
- 查看日志文件中的错误信息
- 确认数据库连接正常

### 8. 开发工作流

1. **修改代码**：在相应模块中进行代码修改
2. **运行测试**：确保修改不会破坏现有功能
3. **启动服务**：测试修改后的功能
4. **提交代码**：遵循Git提交规范

### 9. 项目结构说明

- `config/` - 配置文件
- `core/` - 核心模块（数据库、数据获取、策略管理等）
- `strategies/` - 策略实现
- `web/` - Web应用
- `tests/` - 测试代码
- `db/migrations/` - 数据库迁移脚本

### 10. 技术栈

#### 后端框架

- **Web 服务**: FastAPI (异步)
- **任务队列**: Celery + Redis Broker
- **Python**: 3.9+

#### 数据库与缓存

- **主数据库**: PostgreSQL 15
- **缓存层**: Redis 7
- **ORM**: SQLAlchemy

#### 数据与分析

- **数据源**: Tushare, AkShare
- **数据分析**: Pandas, NumPy, TA-Lib
- **可视化**: ECharts, Matplotlib

#### 前端技术

- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI组件**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router

#### 安全与认证

- **认证**: JWT + OAuth2
- **权限**: RBAC (4角色模型)
- **加密**: Fernet 对称加密
- **限流**: slowapi

#### 监控与日志

- **指标收集**: Prometheus
- **可视化**: Grafana
- **日志**: Loguru (结构化日志)

#### 部署与运维

- **容器化**: Docker + Docker Compose
- **服务编排**: 5个容器 (FastAPI, Celery, PostgreSQL, Redis, Flower)
- **配置管理**: Pydantic, python-dotenv

## 📚 文档导航

项目文档已整理到 `docs/` 目录，按类别组织：

### 📖 配置指南 (docs/guides/)

- [部署指南](docs/guides/deployment.md) - 系统部署和运维
- [Supabase 配置](docs/guides/supabase-setup.md) - Supabase 认证服务配置
- [Redis 配置](docs/guides/redis-setup.md) - Redis 缓存服务配置

### 🏗️ 架构设计 (docs/architecture/)

- [架构优化](docs/architecture/optimization.md) - 系统架构设计和优化方案

### 💻 开发文档 (docs/development/)

- [测试指南](docs/development/testing.md) - 测试框架和使用方法
- [安全指南](docs/development/security.md) - 安全最佳实践

### 📝 开发日志 (docs/changelog/)

Quest 开发过程中产生的技术文档（按时间正序，从早到晚）：

| 更新时间         | 文档                                                                      |
| ---------------- | ------------------------------------------------------------------------- |
| 2026-04-15 11:09 | [异步实现](docs/changelog/async-implementation.md) - 异步编程模型实现     |
| 2026-04-15 11:32 | [数据库优化](docs/changelog/db-optimization.md) - 数据库性能优化          |
| 2026-04-15 11:45 | [监控方案](docs/changelog/monitoring.md) - 系统监控和告警                 |
| 2026-04-15 11:50 | [实现总结](docs/changelog/implementation-summary.md) - 功能实现总览       |
| 2026-04-15 12:43 | [代码清理](docs/changelog/code-cleanup.md) - 代码重构和清理记录           |
| 2026-04-15 12:49 | [最终清理](docs/changelog/final-code-cleanup.md) - 最终代码清理报告       |
| 2026-04-15 14:01 | [缓存实现](docs/changelog/cache-implementation.md) - Redis 缓存层实现总结 |

### 🌐 前端文档

- [前端项目说明](frontend/README.md) - Vue 3 前端项目文档

---

> 💡 **提示**: 新加入项目的开发者建议先阅读 [README.md](README.md) 了解项目概况，然后根据需求查阅相应的配置指南。

---

## 🚀 快速开始（本地开发）

### 方式一：Docker Compose 部署（推荐）

使用 Docker Compose 可以一键启动所有服务（后端、数据库、Redis），无需单独安装依赖。

#### 前置条件

- Docker >= 20.10
- Docker Compose >= 2.0

#### 启动步骤

```bash
# 1. 克隆项目
git clone <repo-url>
cd iQuant.Portal

# 2. 配置环境变量（可选，已有默认配置）
cp .env.example .env

# 3. 启动所有服务（后端 + PostgreSQL + Redis）
./deploy.sh

# 或者手动执行
docker compose build
docker compose up -d
```

#### 访问服务

| 服务         | 地址                               | 说明         |
| ------------ | ---------------------------------- | ------------ |
| FastAPI 后端 | <http://localhost:8000>            | 主后端 API   |
| API 文档     | <http://localhost:8000/api/docs>   | Swagger UI   |
| 系统状态     | <http://localhost:8000/api/status> | 健康检查     |
| PostgreSQL   | localhost:5433                     | 外部访问端口 |
| Redis        | localhost:6379                     | 缓存服务     |

#### 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 重启服务
docker compose restart

# 停止所有服务
docker compose down

# 完全清理（包括数据卷）
docker compose down -v
```

### 方式二：本地环境运行

如果您希望在本机直接运行（不使用 Docker），请按以下步骤操作。

#### 1. 启动基础设施

**PostgreSQL 数据库**

```bash
# 使用 Docker 启动（推荐）
docker run -d \
  --name iquant-postgres \
  -e POSTGRES_DB=iquant \
  -e POSTGRES_USER=iquant \
  -e POSTGRES_PASSWORD=iquant123 \
  -p 5432:5432 \
  postgres:15-alpine

# 或使用本地安装的 PostgreSQL
# 创建数据库和用户
psql -U postgres -c "CREATE DATABASE iquant;"
psql -U postgres -c "CREATE USER iquant WITH PASSWORD 'iquant123';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE iquant TO iquant;"
```

**Redis 缓存**

```bash
# 使用 Docker 启动（推荐）
docker run -d \
  --name iquant-redis \
  -p 6379:6379 \
  redis:7-alpine

# 或使用本地安装的 Redis
# redis-server
```

#### 2. 执行数据库迁移

```bash
# 进入项目根目录
cd iQuant.Portal

# 执行所有迁移脚本
psql -h localhost -U iquant -d iquant -f db/migrations/001_create_base_tables.sql
psql -h localhost -U iquant -d iquant -f db/migrations/002_create_verification_table.sql
psql -h localhost -U iquant -d iquant -f db/migrations/003_create_timing_tables.sql
psql -h localhost -U iquant -d iquant -f db/migrations/004_create_backtest_tables.sql
psql -h localhost -U iquant -d iquant -f db/migrations/005_create_risk_tables.sql
psql -h localhost -U iquant -d iquant -f db/migrations/006_create_trading_tables.sql
psql -h localhost -U iquant -d iquant -f db/migrations/007_create_security_tables.sql
psql -h localhost -U iquant -d iquant -f db/migrations/008_performance_optimization.sql
```

#### 3. 安装 Python 依赖

```bash
# 激活 conda 环境（如使用）
conda activate iQuant

# 安装依赖
pip install -r requirements.txt
```

#### 4. 配置环境变量

编辑 `config/.env` 文件：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=iquant
DB_USER=iquant
DB_PASSWORD=iquant123

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Tushare Token（可选）
TUSHARE_TOKEN=your_token_here
```

#### 5. 启动后端服务

```bash
# 方式一：使用 uvicorn 启动 FastAPI（推荐）
python -m uvicorn web.app_async:app --host 0.0.0.0 --port 8000 --reload
```

#### 6. 启动前端服务

```bash
# 进入前端目录
cd frontend

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev
```

前端将运行在 <http://localhost:3000，自动代理> API 请求到后端 8000 端口。

### 端口规划总结

| 服务           | 端口 | 说明                                |
| -------------- | ---- | ----------------------------------- |
| 前端 (Vite)    | 3000 | Vue.js 开发服务器                   |
| 后端 (FastAPI) | 8000 | 主后端 API                          |
| PostgreSQL     | 5432 | 数据库（内部）/ 5433（Docker 外部） |
| Redis          | 6379 | 缓存服务                            |
| Celery Flower  | 5555 | 任务监控（可选）                    |
| Prometheus     | 9090 | 指标收集（可选）                    |
| Grafana        | 3100 | 可视化面板（可选）                  |

### 故障排查

#### 后端无法连接数据库

```bash
# 检查数据库是否运行
docker ps | grep postgres

# 测试数据库连接
psql -h localhost -U iquant -d iquant -c "SELECT 1;"
```

#### Redis 连接失败

```bash
# 检查 Redis 是否运行
docker ps | grep redis

# 测试 Redis 连接
docker exec -it iquant-redis redis-cli ping
```

#### 端口被占用

```bash
# Windows: 查看端口占用
netstat -ano | findstr ":8000"

# Linux/Mac: 查看端口占用
lsof -i :8000

# 停止占用进程或修改端口配置
```

更多详细文档请参考 [Docker Compose 部署指南](docs/deployment/docker-deployment.md)。
````
