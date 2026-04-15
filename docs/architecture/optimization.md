# iQuant.Portal 架构优化方案

## 📋 优化概览

基于现有架构分析，本方案针对**生产环境部署**场景进行**深度架构改造**，涵盖性能、安全、测试、前端四大核心领域。

---

## 🎯 一、性能与并发优化

### 1.1 Redis 缓存层

#### 现状问题
- Redis 配置存在但未实际使用
- 重复数据查询频繁（股票列表、历史行情）
- AI 诊断结果未缓存，每次重新计算

#### 优化方案
```python
# core/cache.py - 新增缓存管理器
class CacheManager:
    """统一缓存管理层"""

    def __init__(self, redis_url: str):
        self.redis = redis.Redis.from_url(redis_url)

    # 缓存策略
    - 股票基础信息: TTL 24h
    - 日线行情数据: TTL 1h
    - 策略信号结果: TTL 30min
    - AI 诊断报告: TTL 6h
    - 回测结果: TTL 7d

    # 缓存失效策略
    - 数据同步后自动清除相关缓存
    - 支持手动刷新指定 key
    - LRU 淘汰策略
```

**实施步骤**:
1. 实现 `CacheManager` 类
2. 在 `DataFetcher` 中集成缓存读写
3. 在 `agents.py` 中添加诊断结果缓存
4. 在 `backtest_engine.py` 中缓存回测结果
5. 添加缓存监控指标（命中率、内存使用）

**预期收益**:
- API 响应时间降低 60-80%
- 数据库查询减少 70%
- AI 诊断速度提升 90%（缓存命中时）

---

### 1.2 异步 I/O 优化

#### 现状问题
- Flask 同步阻塞，无法处理高并发
- 数据获取、AI 分析等 I/O 密集型操作串行执行
- 长时间任务（数据同步、回测）阻塞主线程

#### 优化方案

**方案 A: 迁移到 FastAPI + asyncio（推荐）**
```python
# web/app_async.py - FastAPI 应用
from fastapi import FastAPI, BackgroundTasks
import asyncio

app = FastAPI()

@app.get("/api/v2/diagnosis/{code}")
async def diagnose_stock(code: str):
    """异步 AI 诊断"""
    # 并行执行多个分析师
    tasks = [
        market_analyst.analyze(code),
        fundamentals_analyst.analyze(code),
        news_analyst.analyze(code)
    ]
    results = await asyncio.gather(*tasks)
    return manager.aggregate(results)

@app.post("/api/data/sync")
async def sync_data(background_tasks: BackgroundTasks):
    """后台任务数据同步"""
    background_tasks.add_task(data_sync_service.full_sync)
    return {"status": "sync_started"}
```

**方案 B: 保持 Flask + Celery 任务队列**
```python
# tasks.py - Celery 任务
from celery import Celery

celery_app = Celery('iquant', broker='redis://localhost:6379/0')

@celery_app.task(bind=True, max_retries=3)
def sync_stock_data(self, stock_code: str):
    """异步数据同步任务"""
    try:
        data_fetcher.sync_daily_data(stock_code)
    except Exception as exc:
        raise self.retry(exc=exc)
```

**对比分析**:
| 维度 | FastAPI + asyncio | Flask + Celery |
|------|-------------------|----------------|
| 性能 | ⭐⭐⭐⭐⭐ 原生异步 | ⭐⭐⭐ 进程间通信开销 |
| 复杂度 | ⭐⭐⭐ 学习曲线平缓 | ⭐⭐⭐⭐ 需维护消息队列 |
| 兼容性 | ⭐⭐ 需重构路由代码 | ⭐⭐⭐⭐⭐ 最小改动 |
| 生态 | ⭐⭐⭐⭐ 新兴框架 | ⭐⭐⭐⭐⭐ 成熟稳定 |

**推荐**: **方案 A (FastAPI)** - 长期收益更大，符合现代 Python Web 趋势

**实施步骤**:
1. 安装 FastAPI + Uvicorn
2. 逐步迁移 Flask 路由到 FastAPI（按模块）
3. 将 I/O 操作改为 async/await
4. 使用 `asyncio.gather()` 并行执行独立任务
5. 性能测试对比（ab/wrk 压测）

**预期收益**:
- 并发处理能力提升 5-10 倍
- API 吞吐量从 100 req/s 提升到 500+ req/s
- 长任务不再阻塞请求

---

### 1.3 任务队列系统

#### 现状问题
- 数据同步、批量回测等耗时操作同步执行
- 无任务状态追踪和重试机制
- 失败任务无告警

#### 优化方案
```python
# core/task_queue.py
from celery import Celery, states
from celery.result import AsyncResult

celery_app = Celery(
    'iquant',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

# 任务定义
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_backtest_task(self, strategy_codes: list, start_date: str, end_date: str):
    """异步回测任务"""
    try:
        engine = BacktestEngine()
        result = engine.run_multi_strategy(strategy_codes, start_date, end_date)
        return {"status": "completed", "result_id": result.id}
    except Exception as exc:
        self.update_state(state=states.FAILURE, meta={"error": str(exc)})
        raise self.retry(exc=exc)

# 任务状态查询
@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    return {
        "status": result.status,
        "result": result.result if result.ready() else None
    }
```

**实施步骤**:
1. 集成 Celery + Redis Broker
2. 迁移耗时任务到 Celery（数据同步、回测、选股）
3. 实现任务状态查询 API
4. 前端添加任务进度条
5. 配置任务失败告警（邮件/钉钉）

**预期收益**:
- 主线程零阻塞
- 任务可追踪、可重试
- 支持分布式任务执行

---

### 1.4 数据库优化

#### 现状问题
- 缺少查询优化（N+1 查询问题）
- 索引覆盖不全
- 无读写分离

#### 优化方案

**1.4.1 查询优化**
```python
# 优化前：N+1 查询
stocks = db.execute("SELECT * FROM stocks WHERE industry = '科技'")
for stock in stocks:
    prices = db.execute("SELECT * FROM stock_daily WHERE stock_code = %s", stock.code)

# 优化后：JOIN 查询
query = """
    SELECT s.*, sd.trade_date, sd.close
    FROM stocks s
    JOIN stock_daily sd ON s.code = sd.stock_code
    WHERE s.industry = '科技' AND sd.trade_date >= %s
"""
results = db.execute(query, (start_date,))
```

**1.4.2 索引优化**
```sql
-- 新增复合索引
CREATE INDEX idx_stock_daily_code_date ON stock_daily (stock_code, trade_date DESC);
CREATE INDEX idx_trade_orders_account_status ON trade_orders (account_id, status);
CREATE INDEX idx_position_details_account_value ON position_details (account_id, market_value DESC);

-- 部分索引（常用查询）
CREATE INDEX idx_active_orders ON trade_orders (status) WHERE status IN ('pending', 'partial_filled');
```

**1.4.3 读写分离（可选）**
```python
# core/database.py
class DatabaseManager:
    def __init__(self):
        self.master_engine = create_engine(MASTER_DB_URL)  # 写操作
        self.slave_engine = create_engine(SLAVE_DB_URL)    # 读操作

    def execute_read(self, query):
        with self.slave_engine.connect() as conn:
            return conn.execute(text(query))

    def execute_write(self, query):
        with self.master_engine.connect() as conn:
            result = conn.execute(text(query))
            conn.commit()
            return result
```

**实施步骤**:
1. 分析慢查询日志（开启 PostgreSQL slow query log）
2. 添加缺失索引
3. 重构 N+1 查询为 JOIN 或批量查询
4. 启用 SQLAlchemy 查询缓存（baked queries）
5. （可选）配置主从复制 + 读写分离

**预期收益**:
- 查询速度提升 3-5 倍
- 数据库 CPU 使用率降低 40%
- 支持更高并发读取

---

## 🔒 二、安全性增强

### 2.1 用户认证与权限管理

#### 现状问题
- Web 界面无登录认证
- API 接口完全开放
- 无操作审计日志

#### 优化方案

**技术选型**: JWT + OAuth2
```python
# core/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.get_user(username)
    if user is None:
        raise credentials_exception
    return user
```

**权限模型**: RBAC (Role-Based Access Control)
```python
# 角色定义
class UserRole(str, Enum):
    ADMIN = "admin"          # 管理员：所有权限
    TRADER = "trader"        # 交易员：策略执行、下单
    ANALYST = "analyst"      # 分析师：查看数据、回测
    VIEWER = "viewer"        # 观察者：只读权限

# 权限装饰器
def require_role(required_role: UserRole):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if current_user.role != required_role and current_user.role != UserRole.ADMIN:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# 使用示例
@app.post("/api/trading/order")
@require_role(UserRole.TRADER)
async def submit_order(order: OrderRequest, current_user: User = Depends(get_current_user)):
    ...
```

**数据库表设计**:
```sql
-- users 表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- audit_logs 表
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100),
    ip_address VARCHAR(45),
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs (user_id, created_at DESC);
```

**实施步骤**:
1. 创建用户表和审计日志表
2. 实现注册/登录/登出 API
3. 添加 JWT 中间件
4. 为敏感 API 添加权限检查
5. 前端添加登录页面和 Token 管理
6. 记录关键操作审计日志

**预期收益**:
- 防止未授权访问
- 操作可追溯
- 符合金融系统安全规范

---

### 2.2 API 限流与防护

#### 现状问题
- 无 API 调用频率限制
- 易受 DDoS 攻击
- 无 IP 黑名单机制

#### 优化方案
```python
# middleware/rate_limiter.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# FastAPI 集成
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 使用示例
@app.get("/api/strategies")
@limiter.limit("100/minute")
async def get_strategies(request: Request):
    ...

@app.post("/api/trading/order")
@limiter.limit("10/minute")  # 交易接口更严格
async def submit_order(request: Request, order: OrderRequest):
    ...
```

**IP 黑名单**:
```python
# middleware/ip_filter.py
class IPFilterMiddleware:
    def __init__(self, app):
        self.app = app
        self.blacklist = set()  # 可从数据库加载

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            client_host = scope["client"][0]
            if client_host in self.blacklist:
                response = JSONResponse(status_code=403, content={"detail": "IP blocked"})
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
```

**实施步骤**:
1. 集成 `slowapi` 限流中间件
2. 为不同 API 设置合理限流规则
3. 实现 IP 黑名单管理界面
4. 添加异常访问告警

**预期收益**:
- 防止 API 滥用
- 抵御简单 DDoS 攻击
- 保护后端资源

---

### 2.3 数据加密

#### 现状问题
- 敏感配置明文存储（数据库密码、Tushare Token）
- 用户密码未加盐哈希
- API 通信未强制 HTTPS

#### 优化方案

**1. 配置加密**:
```python
# config/secrets.py
from cryptography.fernet import Fernet

class SecretsManager:
    def __init__(self, key_file: str = ".secret.key"):
        if not os.path.exists(key_file):
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
        else:
            with open(key_file, 'rb') as f:
                key = f.read()
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, encrypted_value: str) -> str:
        return self.fernet.decrypt(encrypted_value.encode()).decode()

# .env 中使用
# DATABASE_PASSWORD=FERNET_ENCRYPTED_VALUE
```

**2. 密码哈希** (已在 2.1 中实现):
- 使用 `bcrypt` 算法
- 自动加盐
- 工作因子调整为 12（平衡安全性和性能）

**3. HTTPS 强制**:
```nginx
# nginx.conf
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
    }
}
```

**实施步骤**:
1. 实现 SecretsManager
2. 加密现有敏感配置
3. 强制 HTTPS（Let's Encrypt 免费证书）
4. 添加 HSTS 头
5. 定期轮换密钥

**预期收益**:
- 敏感数据泄露风险降低 90%
- 符合 GDPR/网络安全法要求
- 防止中间人攻击

---

## 🧪 三、测试与质量保障

### 3.1 单元测试完善

#### 现状问题
- 仅覆盖策略和回测模块
- 缺少 Mock 外部依赖
- 无边界条件测试

#### 优化方案

**测试结构**:
```
tests/
├── unit/                    # 单元测试
│   ├── test_data_fetcher.py
│   ├── test_strategies.py
│   ├── test_backtest_engine.py
│   ├── test_risk_engine.py
│   ├── test_trading_executor.py
│   ├── test_agents.py
│   └── test_auth.py
├── integration/             # 集成测试
│   ├── test_api_endpoints.py
│   ├── test_database.py
│   └── test_task_queue.py
├── e2e/                     # 端到端测试
│   └── test_user_workflow.py
├── fixtures/                # 测试数据
│   ├── sample_stocks.json
│   └── mock_market_data.csv
└── conftest.py              # Pytest 配置
```

**示例测试**:
```python
# tests/unit/test_data_fetcher.py
import pytest
from unittest.mock import patch, MagicMock
from core.data_fetcher import DataFetcher

@pytest.fixture
def data_fetcher():
    return DataFetcher()

class TestDataFetcher:
    @patch('core.data_fetcher.TushareDataSource')
    def test_get_daily_data_success(self, mock_tushare, data_fetcher):
        """测试成功获取日线数据"""
        mock_df = MagicMock()
        mock_tushare.return_value.get_daily_data.return_value = mock_df

        result = data_fetcher.get_daily_data("000001.SZ", "20240101", "20240131")

        assert result is not None
        mock_tushare.return_value.get_daily_data.assert_called_once()

    @patch('core.data_fetcher.TushareDataSource')
    def test_get_daily_data_fallback(self, mock_tushare, data_fetcher):
        """测试 Tushare 失败时降级到 AkShare"""
        mock_tushare.return_value.get_daily_data.side_effect = Exception("API Error")

        with patch('core.data_fetcher.AkshareDataSource') as mock_akshare:
            mock_akshare.return_value.get_daily_data.return_value = MagicMock()
            result = data_fetcher.get_daily_data("000001.SZ", "20240101", "20240131")

            assert result is not None
            mock_akshare.return_value.get_daily_data.assert_called_once()

    def test_get_daily_data_invalid_code(self, data_fetcher):
        """测试无效股票代码"""
        with pytest.raises(ValueError, match="Invalid stock code"):
            data_fetcher.get_daily_data("INVALID", "20240101", "20240131")
```

**实施步骤**:
1. 为每个核心模块编写单元测试
2. 使用 `pytest-mock` Mock 外部依赖
3. 添加边界条件测试（空数据、异常输入）
4. 目标覆盖率：80%+
5. CI 中集成测试自动化

---

### 3.2 集成测试

#### 现状问题
- 无 API 端到端测试
- 数据库交互未测试
- 任务队列未测试

#### 优化方案
```python
# tests/integration/test_api_endpoints.py
import pytest
from httpx import AsyncClient
from web.app_async import app

@pytest.mark.asyncio
async def test_diagnosis_api():
    """测试 AI 诊断 API"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v2/diagnosis/000001.SZ")
        assert response.status_code == 200
        data = response.json()
        assert "recommendation" in data
        assert "confidence" in data

@pytest.mark.asyncio
async def test_submit_order_with_auth():
    """测试带认证的下单接口"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 登录获取 Token
        login_response = await client.post("/api/auth/login", json={
            "username": "trader1",
            "password": "secure_password"
        })
        token = login_response.json()["access_token"]

        # 提交订单
        order_response = await client.post(
            "/api/trading/order",
            json={"code": "000001.SZ", "side": "buy", "volume": 100},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert order_response.status_code == 200
```

**实施步骤**:
1. 配置测试数据库（隔离环境）
2. 编写 API 集成测试
3. 测试数据库事务回滚
4. 测试 Celery 任务执行
5. CI 中自动运行集成测试

---

### 3.3 性能测试

#### 优化工具
```bash
# 安装 wrk
brew install wrk  # macOS
sudo apt install wrk  # Linux

# 压测命令
wrk -t12 -c400 -d30s http://localhost:8000/api/strategies
```

**基准测试脚本**:
```python
# tests/performance/benchmark.py
import time
import asyncio
from locust import HttpUser, task, between

class ApiUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_strategies(self):
        self.client.get("/api/strategies")

    @task(2)
    def diagnose_stock(self):
        self.client.get("/api/v2/diagnosis/000001.SZ")

    @task(1)
    def run_backtest(self):
        self.client.post("/api/backtest", json={
            "strategy_codes": ["ma", "macd"],
            "start_date": "20240101",
            "end_date": "20241231"
        })
```

**实施步骤**:
1. 建立性能基准（当前 QPS、延迟）
2. 每次优化后重新压测
3. 设置性能回归检测（CI 中自动对比）
4. 目标：P95 延迟 < 200ms，QPS > 500

---

## 🎨 四、前端体验升级

### 4.1 技术选型

**推荐方案**: Vue 3 + TypeScript + Vite

**理由**:
- ✅ 渐进式框架，学习曲线平缓
- ✅ TypeScript 提供类型安全
- ✅ Vite 极速开发体验
- ✅ 丰富的 UI 组件库（Element Plus / Ant Design Vue）
- ✅ 活跃的中文社区

**备选方案**: React 18 + TypeScript + Next.js
- 适合 SSR 场景
- 生态更丰富
- 学习成本略高

---

### 4.2 项目结构

```
frontend/
├── src/
│   ├── api/                  # API 调用封装
│   │   ├── strategies.ts
│   │   ├── backtest.ts
│   │   ├── trading.ts
│   │   └── auth.ts
│   ├── components/           # 通用组件
│   │   ├── StockChart.vue
│   │   ├── StrategyCard.vue
│   │   ├── BacktestResult.vue
│   │   └── OrderForm.vue
│   ├── views/                # 页面视图
│   │   ├── Dashboard.vue
│   │   ├── Strategies.vue
│   │   ├── Backtest.vue
│   │   ├── Trading.vue
│   │   └── Login.vue
│   ├── stores/               # Pinia 状态管理
│   │   ├── user.ts
│   │   ├── strategies.ts
│   │   └── trading.ts
│   ├── router/               # 路由配置
│   │   └── index.ts
│   ├── types/                # TypeScript 类型定义
│   │   ├── strategy.ts
│   │   ├── backtest.ts
│   │   └── trading.ts
│   ├── utils/                # 工具函数
│   │   ├── format.ts
│   │   └── validation.ts
│   ├── App.vue
│   └── main.ts
├── public/
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

### 4.3 核心功能实现

**1. 路由守卫（认证）**:
```typescript
// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/views/Login.vue') },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', component: () => import('@/views/Dashboard.vue') },
        { path: 'strategies', component: () => import('@/views/Strategies.vue') },
        { path: 'backtest', component: () => import('@/views/Backtest.vue') },
        { path: 'trading', component: () => import('@/views/Trading.vue') },
      ],
      meta: { requiresAuth: true }
    }
  ]
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else {
    next()
  }
})

export default router
```

**2. 实时数据更新（WebSocket）**:
```typescript
// composables/useWebSocket.ts
import { ref, onMounted, onUnmounted } from 'vue'

export function useWebSocket(url: string) {
  const data = ref<any>(null)
  const isConnected = ref(false)
  let ws: WebSocket | null = null

  const connect = () => {
    ws = new WebSocket(url)

    ws.onopen = () => {
      isConnected.value = true
    }

    ws.onmessage = (event) => {
      data.value = JSON.parse(event.data)
    }

    ws.onclose = () => {
      isConnected.value = false
      // 自动重连
      setTimeout(connect, 3000)
    }
  }

  onMounted(connect)
  onUnmounted(() => ws?.close())

  return { data, isConnected }
}
```

**3. 图表组件（ECharts）**:
```vue
<!-- components/StockChart.vue -->
<template>
  <div ref="chartRef" style="width: 100%; height: 400px"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const props = defineProps<{
  candlestickData: Array<[string, number, number, number, number]>
  volumeData: Array<[string, number]>
}>()

const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

onMounted(() => {
  chart = echarts.init(chartRef.value!)
  updateChart()
})

watch(() => props.candlestickData, updateChart)

function updateChart() {
  const option: EChartsOption = {
    xAxis: { type: 'category' },
    yAxis: [
      { scale: true },
      { scale: true, gridIndex: 1, height: '20%' }
    ],
    series: [
      {
        type: 'candlestick',
        data: props.candlestickData
      },
      {
        type: 'bar',
        yAxisIndex: 1,
        data: props.volumeData
      }
    ]
  }
  chart?.setOption(option)
}
</script>
```

**实施步骤**:
1. 初始化 Vue 3 项目（`npm create vue@latest`）
2. 安装依赖（Vue Router, Pinia, Element Plus, ECharts）
3. 逐页迁移现有功能（Dashboard → Strategies → Backtest → Trading）
4. 实现响应式布局和暗色主题
5. 添加 loading 状态和错误处理
6. 性能优化（代码分割、懒加载）
7. 部署到 CDN 或与后端一起打包

**预期收益**:
- 用户体验显著提升（SPA 无刷新跳转）
- 开发效率提高（组件复用）
- 移动端适配更好
- 可维护性增强（TypeScript 类型检查）

---

## 📊 五、监控与日志体系

### 5.1 应用监控

**Prometheus + Grafana**:
```python
# middleware/metrics.py
from prometheus_client import Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        REQUEST_DURATION.observe(time.time() - start_time)
        return response

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

**Grafana 仪表板**:
- API QPS、延迟分布
- 数据库连接池使用率
- Redis 命中率
- Celery 任务队列长度
- 错误率趋势

---

### 5.2 日志系统

**结构化日志**:
```python
# core/logging_config.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# 使用示例
logger = structlog.get_logger()
logger.info("order_submitted", order_id="ORD123", user_id=42, amount=10000)
```

**日志聚合**: ELK Stack (Elasticsearch + Logstash + Kibana)
- 集中存储所有日志
- 全文搜索和过滤
- 异常告警规则

---

## 🚀 六、实施路线图

### Phase 1: 基础设施加固（第 1-2 周）
- [ ] 集成 Redis 缓存
- [ ] 实现用户认证系统
- [ ] 添加 API 限流
- [ ] 配置 HTTPS
- [ ] 建立监控体系

### Phase 2: 性能优化（第 3-4 周）
- [ ] 迁移到 FastAPI
- [ ] 实现异步 I/O
- [ ] 集成 Celery 任务队列
- [ ] 数据库查询优化
- [ ] 压力测试与调优

### Phase 3: 前端重构（第 5-7 周）
- [ ] 搭建 Vue 3 项目
- [ ] 迁移核心页面
- [ ] 实现实时数据推送
- [ ] 移动端适配
- [ ] 性能优化

### Phase 4: 测试完善（第 8-9 周）
- [ ] 补充单元测试（80%+ 覆盖率）
- [ ] 编写集成测试
- [ ] 建立 CI/CD 流水线
- [ ] 自动化部署脚本

### Phase 5: 文档与培训（第 10 周）
- [ ] 编写 API 文档（Swagger/OpenAPI）
- [ ] 更新部署指南
- [ ] 录制使用教程
- [ ] 代码审查规范

---

## 📈 七、预期收益总结

| 维度 | 优化前 | 优化后 | 提升幅度 |
|------|--------|--------|----------|
| API 响应时间 | 500ms | 100ms | ⬇️ 80% |
| 并发能力 | 100 req/s | 500+ req/s | ⬆️ 5x |
| 缓存命中率 | 0% | 70%+ | ⬆️ 70% |
| 测试覆盖率 | 30% | 80%+ | ⬆️ 50% |
| 安全性评分 | C | A+ | ⬆️ 2 级 |
| 用户体验 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⬆️ 显著 |
| 部署效率 | 手动 30min | 自动 5min | ⬇️ 83% |

---

## ⚠️ 八、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| FastAPI 迁移成本高 | 中 | 分模块渐进式迁移，保持向后兼容 |
| 前端重构周期长 | 高 | 优先迁移核心页面，旧版保留作为 fallback |
| Redis 单点故障 | 中 | 配置 Redis Sentinel 或 Cluster |
| 数据迁移丢失 | 高 | 完整备份 + 灰度发布 + 快速回滚预案 |
| 团队学习曲线 | 中 | 提供培训文档 + 代码审查 + Pair Programming |

---

## 📝 九、下一步行动

1. **立即开始**: 创建优化分支 `git checkout -b feature/architecture-optimization`
2. **优先级排序**: 从 Phase 1 开始，按顺序推进
3. **里程碑检查**: 每周末 review 进度，调整计划
4. **持续集成**: 每完成一个子任务即合并到主分支并部署测试环境

---

**文档版本**: v1.0  
**最后更新**: 2026-04-15  
**负责人**: Lingma (AI Assistant)
