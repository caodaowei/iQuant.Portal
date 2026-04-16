# iQuant 量化交易系统 - 系统设计文档

**版本**: v2.0  
**更新日期**: 2026-04-15  
**状态**: ✅ 生产就绪

---

## 📋 目录

1. [系统架构设计](#系统架构设计)
2. [模块设计](#模块设计)
3. [数据库设计](#数据库设计)
4. [接口设计](#接口设计)
5. [安全设计](#安全设计)
6. [性能设计](#性能设计)

---

## 系统架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ Web浏览器 │  │ 移动App  │  │ API调用  │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS / WebSocket
┌────────────────────────┴────────────────────────────────────┐
│                      接入层                                  │
│  ┌──────────────────────────────────────────────┐           │
│  │         Nginx (反向代理 + 负载均衡)            │           │
│  └──────────────────────────────────────────────┘           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                      应用层                                 │
│  ┌──────────────┐                                          │
│  │   FastAPI    │                                          │
│  │ (异步主服务)  │                                          │
│  └──────────────┘                                          │
│         │                                                   │
│  ┌──────┴──────┐                                           │
│  │ API 路由层   │                                           │
│  │ - Auth      │                                           │
│  │ - Strategy  │                                           │
│  │ - Backtest  │                                           │
│  │ - Trading   │                                            │
│  │ - Data      │                                            │
│  └─────────────┘                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                      业务逻辑层                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ 策略引擎  │ │ 回测引擎  │ │ 风控引擎  │ │ 交易执行  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │数据获取器 │ │AI分析系统│ │任务调度器 │                     │
│  └──────────┘ └──────────┘ └──────────┘                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                      数据访问层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ SQLAlchemy   │  │   Redis      │  │   Celery     │      │
│  │  (ORM层)     │  │  (缓存层)     │  │  (任务队列)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                      数据存储层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ PostgreSQL   │  │    Redis     │  │   File System│       │
│  │  (主数据库)   │  │  (缓存/消息)  │  │  (日志/报告)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈选型

#### 后端技术栈

| 层次     | 技术选型   | 版本   | 选型理由                       |
| -------- | ---------- | ------ | ------------------------------ |
| Web框架  | FastAPI    | 0.104+ | 原生异步、高性能、自动生成文档 |
| ORM      | SQLAlchemy | 2.0+   | 功能强大、支持异步             |
| 任务队列 | Celery     | 5.3+   | 分布式、可靠、生态成熟         |
| 缓存     | Redis      | 7.0+   | 高性能、数据结构丰富           |
| 数据库   | PostgreSQL | 15+    | ACID、JSONB、扩展性强          |

#### 前端技术栈

| 技术         | 版本 | 选型理由                |
| ------------ | ---- | ----------------------- |
| Vue.js       | 3.3+ | 渐进式、Composition API |
| TypeScript   | 5.0+ | 类型安全、开发体验好    |
| Vite         | 5.0+ | 极速构建、热更新快      |
| Element Plus | 2.4+ | 组件丰富、中文文档      |
| ECharts      | 5.4+ | 图表强大、中文支持好    |
| Pinia        | 2.1+ | 轻量、TypeScript友好    |

#### 运维技术栈

| 技术           | 用途       |
| -------------- | ---------- |
| Docker         | 容器化     |
| Docker Compose | 服务编排   |
| Prometheus     | 指标收集   |
| Grafana        | 可视化监控 |
| Loguru         | 结构化日志 |

---

## 模块设计

### 1. 数据管理模块设计

#### 1.1 类图

```
┌─────────────────────────────┐
│     DataFetcher             │
├─────────────────────────────┤
│ - sources: List[DataSource] │
│ - cache: CacheManager       │
├─────────────────────────────┤
│ + get_daily_data()          │
│ + get_stock_list()          │
│ + get_realtime_quote()      │
│ + sync_data()               │
└─────────────────────────────┘
           │
           │ uses
           ▼
┌─────────────────────────┐
│   DataSource (ABC)      │
├─────────────────────────┤
│ + get_daily_data()      │
│ + get_stock_list()      │
└─────────────────────────┘
     │              │
     │              │
┌────┴────┐   ┌────┴────┐
│TushareDS│   │AkShareDS│
└─────────┘   └─────────┘
```

#### 1.2 数据流图

```
用户请求
   │
   ▼
┌──────────┐
│检查缓存   │──── 命中 ────→ 返回缓存数据
└──────────┘
   │ 未命中
   ▼
┌──────────┐
│Tushare API│──── 成功 ────→ 写入缓存 → 返回数据
└──────────┘
   │ 失败
   ▼
┌──────────┐
│AkShare API│──── 成功 ────→ 写入缓存 → 返回数据
└──────────┘
   │ 失败
   ▼
返回错误
```

#### 1.3 缓存策略设计

**缓存Key设计规范**:

```
格式: {namespace}:{type}:{identifier}:{optional_params}

示例:
- stock:info:000001.SZ
- stock:daily:000001.SZ:2024-01-01:2024-12-31
- strategy:signal:ma_trend:000001.SZ
- backtest:result:strategy_123:2024-01-01_2024-12-31
```

**缓存失效策略**:

- TTL 自动过期
- 数据更新时主动清除
- LRU 淘汰策略

---

### 2. 策略引擎设计

#### 2.1 策略模式实现

```python
# 策略基类 (模板方法模式)
class TimingStrategy(ABC):
    def run(self, data):
        """模板方法 - 定义算法骨架"""
        indicators = self.calculate_indicators(data)
        signals = self.generate_signals(indicators)
        return self.filter_signals(signals)

    @abstractmethod
    def calculate_indicators(self, data):
        """子类实现具体指标计算"""
        pass

    @abstractmethod
    def generate_signals(self, indicators):
        """子类实现信号生成逻辑"""
        pass
```

#### 2.2 策略注册表模式

```python
class StrategyRegistry:
    """策略注册表 (注册表模式)"""

    _strategies = {}

    @classmethod
    def register(cls, strategy_class):
        """注册策略"""
        cls._strategies[strategy_class.code] = strategy_class

    @classmethod
    def get_strategy(cls, code):
        """获取策略实例"""
        strategy_class = cls._strategies.get(code)
        return strategy_class() if strategy_class else None
```

#### 2.3 信号聚合策略

**多数表决算法**:

```python
def majority_vote(signals):
    buy_count = sum(1 for s in signals if s.type in ['buy', 'strong_buy'])
    sell_count = sum(1 for s in signals if s.type in ['sell', 'strong_sell'])

    if buy_count > sell_count and buy_count >= threshold:
        return 'buy'
    elif sell_count > buy_count and sell_count >= threshold:
        return 'sell'
    return 'hold'
```

**加权平均算法**:

```python
def weighted_average(signals, weights):
    score = 0
    for signal, weight in zip(signals, weights):
        if signal.type == 'strong_buy':
            score += 1.0 * weight
        elif signal.type == 'buy':
            score += 0.5 * weight
        # ... 其他信号类型

    if score > 0.6:
        return 'strong_buy'
    elif score > 0.3:
        return 'buy'
    # ... 其他判断
```

---

### 3. 回测引擎设计

#### 3.1 事件驱动架构

```
┌──────────────────────────────────────────────┐
│              Event Loop                      │
├──────────────────────────────────────────────┤
│                                              │
│  ┌────────┐    ┌────────┐    ┌────────┐      │
│  │Market  │───→│Strategy│───→│ Order  │      │
│  │Event   │    │Signal  │    │ Event  │      │
│  └────────┘    └────────┘    └────────┘      │
│                                  │           │
│                          ┌───────┴───────┐   │
│                          │  Execution    │   │
│                          │  Report       │   │
│                          └───────┬───────┘   │
│                                  │           │
│                          ┌───────┴───────┐   │
│                          │   Position    │   │
│                          │   Update      │   │
│                          └───────────────┘   │
└──────────────────────────────────────────────┘
```

#### 3.2 核心类设计

```python
@dataclass
class BacktestState:
    """回测状态 (快照模式)"""
    date: date
    cash: float
    positions: Dict[str, Position]
    total_value: float

    def snapshot(self):
        """创建状态快照"""
        return copy.deepcopy(self)

class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_capital, commission_rate, slippage):
        self.state = BacktestState(date=start_date, cash=initial_capital)
        self.history = []  # 历史记录

    def run(self, strategy, data):
        """运行回测"""
        for date in data.dates:
            # 1. 更新市场数据
            market_data = data.get_date(date)

            # 2. 生成策略信号
            signal = strategy.generate_signal(market_data)

            # 3. 执行交易
            if signal:
                order = self.create_order(signal)
                trade = self.execute_order(order, market_data)

            # 4. 更新持仓
            self.update_positions()

            # 5. 记录状态
            self.history.append(self.state.snapshot())

        return self.calculate_performance()
```

---

### 4. 风控引擎设计

#### 4.1 责任链模式

```python
class RiskRule(ABC):
    """风控规则 (责任链节点)"""

    def __init__(self, next_rule=None):
        self.next_rule = next_rule

    def check(self, context):
        """检查风控规则"""
        result = self.do_check(context)

        if not result.passed and self.stop_on_violation:
            return result

        if self.next_rule:
            return self.next_rule.check(context)

        return result

    @abstractmethod
    def do_check(self, context):
        pass

# 构建责任链
chain = PositionLimitRule(
    next_rule=DrawdownLimitRule(
        next_rule=DailyLossLimitRule(
            next_rule=CashRatioRule()
        )
    )
)
```

#### 4.2 风控检查流程

```
交易请求
   │
   ▼
┌──────────────────┐
│ 持仓限额检查      │──── 失败 ────→ 拒绝交易
└──────────────────┘
   │ 通过
   ▼
┌──────────────────┐
│ 回撤限制检查      │──── 失败 ────→ 强制平仓
└──────────────────┘
   │ 通过
   ▼
┌──────────────────┐
│ 单日亏损检查      │──── 失败 ────→ 暂停交易
└──────────────────┘
   │ 通过
   ▼
┌──────────────────┐
│ 现金比例检查      │──── 警告 ────→ 提示风险
└──────────────────┘
   │ 通过
   ▼
允许交易
```

---

### 5. 任务队列设计

#### 5.1 Celery 任务设计

```python
# 任务配置
celery_app = Celery(
    'iquant',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Asia/Shanghai',
    enable_utc=True,
)

# 任务重试配置
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def sync_stock_data(self, stock_code):
    try:
        # 任务逻辑
        pass
    except Exception as exc:
        raise self.retry(exc=exc)
```

#### 5.2 任务状态机

```
PENDING → RECEIVED → STARTED → SUCCESS
                        ↓
                    FAILURE (可重试)
                        ↓
                  RETRY (最多3次)
                        ↓
                  FAILURE (最终)
```

---

## 数据库设计

### ER 图

```
┌──────────────┐       ┌──────────────────┐
│   stocks     │1     *│  stock_daily     │
├──────────────┤       ├──────────────────┤
│ code (PK)    │───────│ stock_code (FK)  │
│ name         │       │ trade_date       │
│ industry     │       │ open             │
│ market       │       │ high             │
└──────────────┘       │ low              │
                       │ close            │
                       │ volume           │
                       └──────────────────┘

┌──────────────┐       ┌──────────────────┐
│  strategies  │1     *│ backtest_results │
├──────────────┤       ├──────────────────┤
│ code (PK)    │───────│ strategy_code(FK)│
│ name         │       │ start_date       │
│ params       │       │ end_date         │
└──────────────┘       │ total_return     │
                       │ sharpe_ratio     │
                       └──────────────────┘

┌──────────────┐       ┌──────────────────┐
│   accounts   │1     *│    orders        │
├──────────────┤       ├──────────────────┤
│ id (PK)      │───────│ account_id (FK)  │
│ user_id      │       │ order_no (UK)    │
│ balance      │       │ stock_code       │
└──────────────┘       │ trade_type       │
                       │ status           │
                       └──────────────────┘
                              │1
                              │
                         ┌────┴────┐
                         │ trades  │
                         ├─────────┤
                         │trade_no │
                         │order_no │
                         │volume   │
                         │price    │
                         └─────────┘

┌──────────────┐       ┌──────────────────┐
│    users     │1     *│   audit_logs     │
├──────────────┤       ├──────────────────┤
│ id (PK)      │───────│ user_id (FK)     │
│ username     │       │ action           │
│ password_hash│       │ resource         │
│ role         │       │ created_at       │
└──────────────┘       └──────────────────┘
```

### 索引设计

```sql
-- 高频查询索引
CREATE INDEX idx_stock_daily_code_date
ON stock_daily (stock_code, trade_date DESC);

CREATE INDEX idx_orders_account_status
ON orders (account_id, status);

CREATE INDEX idx_trades_order_no
ON trades (order_no);

-- 部分索引 (常用查询)
CREATE INDEX idx_active_orders
ON orders (status)
WHERE status IN ('pending', 'partial_filled');

-- GIN 索引 (JSONB 查询)
CREATE INDEX idx_strategy_params_gin
ON strategies USING GIN (params);
```

---

## 接口设计

### RESTful API 设计规范

#### URL 命名规范

- 使用名词复数: `/api/strategies`
- 使用嵌套表示关系: `/api/strategies/{code}/execute`
- 使用连字符而非下划线: `/api/backtest-results`

#### HTTP 方法语义

- GET: 查询资源
- POST: 创建资源/执行操作
- PUT: 更新资源
- DELETE: 删除资源

#### 响应格式

**成功响应**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    ...
  }
}
```

**错误响应**:

```json
{
  "code": 400,
  "message": "Invalid parameters",
  "errors": [
    {
      "field": "stock_code",
      "message": "Invalid stock code format"
    }
  ]
}
```

### 认证机制

**JWT Token 结构**:

```
Header: { "alg": "HS256", "typ": "JWT" }
Payload: {
  "sub": "username",
  "role": "trader",
  "exp": 1234567890,
  "iat": 1234567000
}
Signature: HMACSHA256(...)
```

**Token 刷新流程**:

```
Access Token 过期
   │
   ▼
使用 Refresh Token 请求新 Access Token
   │
   ├── 成功 → 获取新 Access Token
   └── 失败 → 重新登录
```

---

## 安全设计

### 1. 认证与授权

#### JWT 安全配置

```python
SECRET_KEY = os.getenv('SECRET_KEY')  # 环境变量存储
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 密码哈希
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # 工作因子
)
```

#### RBAC 权限控制

```python
def require_role(required_role: UserRole):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not has_permission(current_user.role, required_role):
                raise HTTPException(status_code=403)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 2. API 防护

#### 限流策略

```python
# 基于 IP 的限流
limiter = Limiter(key_func=get_remote_address)

@app.get("/api/strategies")
@limiter.limit("100/minute")
async def get_strategies(request: Request):
    ...

# 基于用户的限流
@app.post("/api/trading/order")
@limiter.limit("10/minute")
async def submit_order(request: Request, user=Depends(get_current_user)):
    ...
```

#### IP 黑名单

```python
class IPFilterMiddleware:
    async def __call__(self, scope, receive, send):
        client_ip = scope["client"][0]
        if client_ip in self.blacklist:
            return JSONResponse(status_code=403)
        await self.app(scope, receive, send)
```

### 3. 数据加密

#### Fernet 加密

```python
class SecretsManager:
    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self.fernet.decrypt(encrypted.encode()).decode()

# 使用示例
secrets = SecretsManager()
encrypted_password = secrets.encrypt("db_password")
```

#### HTTPS 配置

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/domain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/domain/privkey.pem;

    # 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    add_header Strict-Transport-Security "max-age=31536000";
}
```

---

## 性能设计

### 1. 缓存策略

#### 多级缓存架构

```
L1: 应用内存缓存 (LRU, 5分钟)
  ↓ Miss
L2: Redis 缓存 (TTL, 1小时-7天)
  ↓ Miss
L3: 数据库查询 (索引优化)
```

#### 缓存预热策略

```python
# 系统启动时预热热点数据
async def warmup_cache():
    # 预热股票列表
    stock_list = await fetch_stock_list()
    cache_manager.set('stock:list:all', stock_list, 'stock_list')

    # 预热热门股票数据
    for code in POPULAR_STOCKS:
        data = await fetch_daily_data(code)
        cache_manager.set(f'stock:daily:{code}', data, 'daily_data')
```

### 2. 数据库优化

#### 连接池配置

```python
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,           # 连接池大小
    max_overflow=40,        # 最大溢出连接数
    pool_pre_ping=True,     # 连接前检测有效性
    pool_recycle=3600,      # 连接回收时间(秒)
)
```

#### 查询优化

```python
# ❌ N+1 查询
stocks = db.query(Stock).all()
for stock in stocks:
    prices = db.query(Price).filter_by(stock_code=stock.code).all()

# ✅ JOIN 查询
results = db.query(Stock, Price).join(
    Price, Stock.code == Price.stock_code
).all()
```

### 3. 异步优化

#### 并行执行

```python
# ❌ 串行执行
market_data = await market_analyst.analyze(code)
fundamental_data = await fundamentals_analyst.analyze(code)
news_data = await news_analyst.analyze(code)

# ✅ 并行执行
results = await asyncio.gather(
    market_analyst.analyze(code),
    fundamentals_analyst.analyze(code),
    news_analyst.analyze(code)
)
```

#### Background Tasks

```python
@app.post("/api/data/sync")
async def sync_data(background_tasks: BackgroundTasks):
    background_tasks.add_task(data_sync_service.full_sync)
    return {"status": "sync_started"}
```

### 4. 性能监控

#### Prometheus 指标

```python
# 请求延迟直方图
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# 业务指标
backtest_executions_total = Counter(
    'backtest_executions_total',
    'Total backtest executions',
    ['strategy', 'status']
)
```

---

## 附录

### A. 设计模式总结

| 设计模式   | 应用场景     | 实现位置                    |
| ---------- | ------------ | --------------------------- |
| 策略模式   | 多策略实现   | `strategies/timing/`        |
| 模板方法   | 策略基类     | `strategies/timing/base.py` |
| 单例模式   | 数据库管理器 | `core/database.py`          |
| 工厂模式   | 策略创建     | `strategies/registry.py`    |
| 观察者模式 | 事件驱动回测 | `core/backtest_engine.py`   |
| 责任链模式 | 风控规则链   | `core/risk_engine.py`       |
| 注册表模式 | 策略注册     | `strategies/registry.py`    |
| 适配器模式 | 多数据源适配 | `core/data_fetcher.py`      |

### B. 关键算法

详见各模块代码实现。

---

**文档维护**: Lingma (AI Assistant)  
**最后更新**: 2026-04-15
