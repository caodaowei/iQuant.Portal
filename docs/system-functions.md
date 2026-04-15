# iQuant 量化交易系统 - 系统功能文档

**版本**: v2.0  
**更新日期**: 2026-04-15  
**状态**: ✅ 生产就绪

---

## 📋 目录

1. [系统概述](#系统概述)
2. [核心功能模块](#核心功能模块)
3. [功能详细说明](#功能详细说明)
4. [API 接口清单](#api-接口清单)
5. [用户角色与权限](#用户角色与权限)

---

## 系统概述

iQuant 是一个基于 Python 的量化交易系统，提供从数据获取、策略开发、回测验证到交易执行的完整量化投资解决方案。

### 技术特点

- **双架构支持**: FastAPI (异步) + Flask (同步)
- **多数据源**: Tushare + AkShare 自动降级
- **智能缓存**: Redis 7层缓存策略
- **异步任务**: Celery 分布式任务队列
- **实时监控**: Prometheus + Grafana
- **安全认证**: JWT + OAuth2 + RBAC

---

## 核心功能模块

### 1. 数据管理模块

#### 1.1 数据获取 (DataFetcher)

**功能描述**: 统一的数据获取接口，支持多数据源自动切换和智能缓存。

**核心特性**:
- ✅ 多数据源支持 (Tushare, AkShare)
- ✅ 自动降级机制 (主数据源失败时自动切换)
- ✅ Redis 缓存层 (7种缓存策略)
- ✅ 数据标准化处理
- ✅ 断点续传支持

**支持的数据类型**:
| 数据类型 | 说明 | 缓存TTL | 更新频率 |
|---------|------|---------|---------|
| 股票基础信息 | 股票代码、名称、行业等 | 24h | 每日 |
| 日线行情数据 | OHLCV 数据 | 1h | 实时 |
| 指数数据 | 主要指数行情 | 1h | 实时 |
| 股票列表 | 全市场股票列表 | 24h | 每日 |
| 财务数据 | 财务报表数据 | 7d | 季度 |

**代码位置**: [`core/data_fetcher.py`](../core/data_fetcher.py)

#### 1.2 数据同步服务 (DataSyncService)

**功能描述**: 自动化数据同步服务，支持定时任务和增量更新。

**核心功能**:
- ✅ 全量数据同步
- ✅ 增量数据更新
- ✅ 数据质量检查
- ✅ 异常数据修复
- ✅ 同步进度追踪

**同步策略**:
```python
# 定时同步任务
- 每日收盘后自动同步当日数据 (15:30)
- 每小时更新实时行情
- 每周日更新股票列表
- 每季度更新财务数据
```

**代码位置**: [`core/data_sync.py`](../core/data_sync.py)

#### 1.3 缓存管理 (CacheManager)

**功能描述**: 统一的 Redis 缓存管理层，提供多种序列化策略和自动过期机制。

**缓存策略**:
| 缓存类型 | Key 前缀 | TTL | 序列化方式 | 应用场景 |
|---------|---------|-----|-----------|---------|
| 股票信息 | `stock:info:` | 24h | JSON | 股票基本信息查询 |
| 日线数据 | `stock:daily:` | 1h | Pickle | K线数据查询 |
| 策略信号 | `strategy:signal:` | 30min | JSON | 策略信号缓存 |
| AI诊断 | `ai:diagnosis:` | 6h | JSON | AI分析报告 |
| 回测结果 | `backtest:result:` | 7d | Pickle | 回测报告缓存 |
| 指数数据 | `index:data:` | 1h | Pickle | 指数行情 |
| 股票列表 | `stock:list:` | 24h | JSON | 股票列表查询 |

**核心方法**:
```python
cache_manager.get(key, cache_type)      # 获取缓存
cache_manager.set(key, value, cache_type)  # 设置缓存
cache_manager.delete(key)               # 删除缓存
cache_manager.clear_pattern(pattern)    # 批量清除
cache_manager.get_stats()               # 缓存统计
```

**代码位置**: [`core/cache.py`](../core/cache.py)

---

### 2. 策略引擎模块

#### 2.1 策略框架 (TimingStrategy)

**功能描述**: 标准化的择时策略开发框架，提供统一的策略接口和信号生成机制。

**策略基类**:
```python
class TimingStrategy(ABC):
    def calculate_indicators(data) -> DataFrame  # 计算技术指标
    def generate_signal(data) -> TimingSignal    # 生成交易信号
    def run(market_data) -> List[TimingSignal]   # 运行策略
```

**信号类型**:
- `strong_buy`: 强烈买入
- `buy`: 买入
- `hold`: 持有
- `sell`: 卖出
- `strong_sell`: 强烈卖出

**代码位置**: [`strategies/timing/base.py`](../strategies/timing/base.py)

#### 2.2 内置策略库

##### MA 均线趋势策略 (MA_TREND)

**策略逻辑**: 基于多条均线的排列关系判断趋势方向

**参数配置**:
- 短期均线周期: 5日
- 中期均线周期: 20日
- 长期均线周期: 60日

**信号规则**:
- 金叉 (短线上穿长线): 买入信号
- 死叉 (短线下穿长线): 卖出信号
- 多头排列 (短>中>长): 强烈买入
- 空头排列 (短<中<长): 强烈卖出

**代码位置**: [`strategies/timing/ma_strategy.py`](../strategies/timing/ma_strategy.py)

##### MACD 信号策略 (MACD_SIGNAL)

**策略逻辑**: 基于 MACD 指标的柱状图和信号线交叉

**参数配置**:
- 快线周期: 12日
- 慢线周期: 26日
- 信号线周期: 9日

**信号规则**:
- DIF 上穿 DEA: 买入
- DIF 下穿 DEA: 卖出
- 红柱放大: 强势买入
- 绿柱放大: 强势卖出

**代码位置**: [`strategies/timing/macd_strategy.py`](../strategies/timing/macd_strategy.py)

##### RSI 均值回归策略 (RSI_MEAN_REVERT)

**策略逻辑**: 基于 RSI 超买超卖指标的均值回归

**参数配置**:
- RSI 周期: 14日
- 超买阈值: 70
- 超卖阈值: 30

**信号规则**:
- RSI < 30: 超卖，买入信号
- RSI > 70: 超买，卖出信号
- RSI < 20: 严重超卖，强烈买入
- RSI > 80: 严重超买，强烈卖出

**代码位置**: [`strategies/timing/rsi_strategy.py`](../strategies/timing/rsi_strategy.py)

##### BOLL 布林带突破策略 (BOLL_BREAKOUT)

**策略逻辑**: 基于布林带上下轨的突破信号

**参数配置**:
- 均线周期: 20日
- 标准差倍数: 2

**信号规则**:
- 价格突破上轨: 买入信号
- 价格跌破下轨: 卖出信号
- 带宽收窄后突破: 强烈信号
- 价格回归中轨: 平仓信号

**代码位置**: [`strategies/timing/boll_strategy.py`](../strategies/timing/boll_strategy.py)

##### 线性回归策略 (LINEAR_REGRESSION)

**策略逻辑**: 基于价格线性回归趋势预测

**参数配置**:
- 回归窗口: 30日
- 趋势阈值: 0.05

**代码位置**: [`strategies/timing/linear_regression_strategy.py`](../strategies/timing/linear_regression_strategy.py)

##### 斜率成交量策略 (SLOPE_VOLUME)

**策略逻辑**: 结合价格斜率和成交量变化

**参数配置**:
- 斜率窗口: 20日
- 成交量均线: 10日

**代码位置**: [`strategies/timing/slope_volume_strategy.py`](../strategies/timing/slope_volume_strategy.py)

#### 2.3 策略管理器 (StrategyManager)

**功能描述**: 统一管理所有策略的注册、加载和执行。

**核心功能**:
- ✅ 策略动态注册
- ✅ 策略参数配置
- ✅ 多策略并行执行
- ✅ 信号聚合 (多数表决/加权平均)
- ✅ 策略性能追踪

**共识信号聚合**:
```python
# 多数表决
if buy_signals > sell_signals and buy_signals >= threshold:
    signal = "buy"

# 加权平均
weighted_score = sum(signal.strength * weight for signal, weight in signals)
```

**代码位置**: [`core/strategy_manager.py`](../core/strategy_manager.py)

---

### 3. 回测引擎模块

#### 3.1 事件驱动回测框架 (BacktestEngine)

**功能描述**: 基于事件驱动的高性能回测引擎，支持单策略和多策略回测。

**核心特性**:
- ✅ 事件驱动架构
- ✅ 精确的交易模拟
- ✅ 手续费和滑点计算
- ✅ 持仓管理
- ✅ 绩效指标计算

**回测流程**:
```
初始化 → 加载数据 → 逐日迭代 → 策略信号 → 交易执行 → 持仓更新 → 绩效计算
```

**代码位置**: [`core/backtest_engine.py`](../core/backtest_engine.py)

#### 3.2 持仓管理 (Position)

**数据结构**:
```python
@dataclass
class Position:
    stock_code: str          # 股票代码
    stock_name: str          # 股票名称
    volume: int              # 持仓数量
    avg_cost: float          # 平均成本
    total_cost: float        # 总成本
    current_price: float     # 当前价格
    market_value: float      # 市值
    floating_pnl: float      # 浮动盈亏
    floating_pnl_rate: float # 浮动盈亏率
```

#### 3.3 绩效指标

**收益率指标**:
- 总收益率: `(最终资产 - 初始资金) / 初始资金`
- 年化收益率: `总收益率 * 365 / 回测天数`
- 日收益率: 每日资产变化率

**风险指标**:
- 最大回撤: `max((峰值 - 谷值) / 峰值)`
- 夏普比率: `(年化收益 - 无风险利率) / 收益标准差`
- 胜率: `盈利交易次数 / 总交易次数`
- 盈亏比: `平均盈利 / 平均亏损`

**交易指标**:
- 总交易次数
- 持仓天数
- 换手率

---

### 4. 风控引擎模块

#### 4.1 风控规则引擎 (RiskEngine)

**功能描述**: 可配置的风控规则引擎，支持多级风控检查。

**核心特性**:
- ✅ 规则动态配置
- ✅ 多级风控 (低/中/高/严重)
- ✅ 实时风控检查
- ✅ 风控报告生成

**代码位置**: [`core/risk_engine.py`](../core/risk_engine.py)

#### 4.2 内置风控规则

##### 规则1: 持仓限额检查 (POSITION_LIMIT)

**检查项**:
- 单股持仓上限: 总资产的 20%
- 总持仓上限: 总资产的 80%
- 行业集中度: 单一行业不超过 40%

**风控级别**: high  
**触发动作**: 禁止开新仓

##### 规则2: 回撤限制检查 (DRAWDOWN_LIMIT)

**检查项**:
- 单日最大回撤: 5%
- 累计最大回撤: 15%
- 连续亏损天数: 5天

**风控级别**: critical  
**触发动作**: 强制平仓

##### 规则3: 单日亏损限制 (DAILY_LOSS_LIMIT)

**检查项**:
- 单日最大亏损: 3%
- 连续3日亏损: 5%

**风控级别**: high  
**触发动作**: 暂停交易

##### 规则4: 现金比例检查 (CASH_RATIO)

**检查项**:
- 最低现金比例: 10%
- 理想现金比例: 20-30%

**风控级别**: medium  
**触发动作**: 警告提示

##### 规则5: 黑名单检查 (BLACKLIST)

**检查项**:
- ST 股票
- 退市风险股票
- 手动添加的黑名单

**风控级别**: critical  
**触发动作**: 禁止交易

---

### 5. 交易执行模块

#### 5.1 交易执行器 (TradingExecutor)

**功能描述**: 模拟交易执行器，支持订单管理和成交回报。

**核心功能**:
- ✅ 订单创建和提交
- ✅ 订单状态追踪
- ✅ 成交回报处理
- ✅ 持仓实时更新
- ✅ 风控前置检查

**订单类型**:
- 市价单 (market): 按当前市场价格立即成交
- 限价单 (limit): 指定价格成交

**订单状态**:
- `pending`: 待提交
- `submitted`: 已提交
- `filled`: 完全成交
- `partial_filled`: 部分成交
- `cancelled`: 已撤单
- `rejected`: 被拒绝

**代码位置**: [`core/trading_executor.py`](../core/trading_executor.py)

#### 5.2 交易费用计算

**手续费**:
- 买入: `成交金额 * 佣金率 (默认 0.025%)`
- 卖出: `成交金额 * 佣金率 + 印花税 (0.1%)`
- 最低佣金: 5元

**滑点**:
- 默认滑点: 0.1%
- 买入价格: `市价 * (1 + 滑点)`
- 卖出价格: `市价 * (1 - 滑点)`

---

### 6. AI 智能分析模块

#### 6.1 多智能体系统 (MultiAgentSystem)

**功能描述**: 基于多个专业分析师的智能决策系统。

**分析师角色**:
1. **市场分析师 (MarketAnalyst)**: 技术面分析
2. **基本面分析师 (FundamentalsAnalyst)**: 财务数据分析
3. **新闻分析师 (NewsAnalyst)**: 舆情分析
4. **量化分析师 (QuantAnalyst)**: 量化指标分析

**工作流程**:
```
输入股票代码 → 各分析师独立分析 → 汇总分析结果 → 综合决策 → 输出投资建议
```

**输出内容**:
- 投资评级 (强烈推荐/推荐/中性/回避/强烈回避)
- 置信度 (0-100%)
- 目标价位
- 风险提示
- 详细分析报告

**代码位置**: [`core/agents.py`](../core/agents.py)

---

### 7. Web 应用模块

#### 7.1 FastAPI 异步服务

**功能描述**: 基于 FastAPI 的高性能异步 API 服务。

**服务地址**: `http://localhost:8000`  
**API 文档**: `http://localhost:8000/api/docs`

**核心路由**:
- `/api/auth/*`: 认证相关
- `/api/strategies`: 策略管理
- `/api/backtest`: 回测执行
- `/api/trading`: 交易执行
- `/api/data/*`: 数据同步
- `/api/diagnosis/*`: AI 诊断

**代码位置**: [`web/app_async.py`](../web/app_async.py)

#### 7.2 Flask 同步服务

**功能描述**: 基于 Flask 的同步 Web 服务（兼容旧版）。

**服务地址**: `http://localhost:5000`

**代码位置**: [`web/app.py`](../web/app.py)

#### 7.3 Vue 3 前端应用

**功能描述**: 基于 Vue 3 + TypeScript 的现代化前端应用。

**技术栈**:
- Vue 3 Composition API
- TypeScript
- Vite 构建工具
- Element Plus UI
- ECharts 图表库
- Pinia 状态管理

**页面功能**:
- Dashboard: 系统概览
- Strategies: 策略管理
- Backtest: 回测分析
- Trading: 交易执行
- Data: 数据同步
- Risk: 风控监控

**代码位置**: [`frontend/`](../frontend/)

---

### 8. 任务队列模块

#### 8.1 Celery 异步任务

**功能描述**: 基于 Celery + Redis 的分布式任务队列。

**任务类型**:
1. **sync_stock_data**: 股票数据同步
2. **run_backtest**: 回测任务
3. **run_ai_diagnosis**: AI 诊断任务

**任务特性**:
- ✅ 异步执行
- ✅ 自动重试 (最多3次)
- ✅ 任务状态追踪
- ✅ 失败告警

**代码位置**: 
- [`core/tasks.py`](../core/tasks.py)
- [`celery_worker.py`](../celery_worker.py)

#### 8.2 Flower 监控面板

**功能描述**: Celery 任务的可视化监控面板。

**访问地址**: `http://localhost:5555`

**监控内容**:
- 任务执行状态
- 任务执行时间
- Worker 状态
- 任务队列长度

---

### 9. 监控与日志模块

#### 9.1 Prometheus 指标收集

**功能描述**: 应用程序性能指标 (APM) 收集。

**监控指标**:

**HTTP 请求指标**:
- `http_requests_total`: 请求总数 (按方法、端点、状态码)
- `http_request_duration_seconds`: 请求延迟分布
- `http_request_size_bytes`: 请求大小
- `http_response_size_bytes`: 响应大小

**业务指标**:
- `backtest_executions_total`: 回测执行次数
- `ai_diagnosis_total`: AI 诊断次数
- `data_sync_total`: 数据同步次数
- `stock_selection_total`: 选股次数
- `risk_check_total`: 风控检查次数

**系统指标**:
- `cache_hits_total`: 缓存命中数
- `cache_misses_total`: 缓存未命中数
- `cache_hit_rate`: 缓存命中率
- `db_pool_active`: 数据库活跃连接数
- `redis_connected`: Redis 连接状态

**代码位置**: [`core/metrics.py`](../core/metrics.py)

#### 9.2 Grafana 仪表板

**功能描述**: 可视化监控仪表板。

**访问地址**: `http://localhost:3100`

**预设仪表板**:
- iQuant 系统总览
- API 性能监控
- 数据库监控
- 缓存监控
- Celery 任务监控

**配置文件**: [`config/grafana/`](../config/grafana/)

#### 9.3 结构化日志

**日志框架**: Loguru

**日志级别**:
- DEBUG: 调试信息
- INFO: 一般信息
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

**日志输出**:
- 控制台输出 (彩色格式化)
- 文件输出 (`logs/iquant.log`)
- 日志轮转 (每天一个文件，保留30天)

---

### 10. 安全认证模块

#### 10.1 JWT 认证

**功能描述**: 基于 JWT 的用户认证系统。

**Token 类型**:
- Access Token: 30分钟有效期
- Refresh Token: 7天有效期

**加密算法**: HS256

**代码位置**: [`core/auth.py`](../core/auth.py)

#### 10.2 RBAC 权限模型

**用户角色**:

| 角色 | 权限 | 适用场景 |
|------|------|---------|
| Admin | 所有权限 | 系统管理员 |
| Trader | 策略执行、下单交易 | 交易员 |
| Analyst | 查看数据、运行回测 | 分析师 |
| Viewer | 只读权限 | 观察者 |

**权限控制**:
```python
@app.post("/api/trading/order")
@require_role(UserRole.TRADER)
async def submit_order(...):
    ...
```

#### 10.3 API 限流

**限流策略**:
- 默认限流: 200次/分钟
- 交易接口: 10次/分钟
- 数据同步: 5次/分钟
- AI 诊断: 30次/分钟

**IP 黑名单**: 支持动态添加/移除被封禁 IP

**代码位置**: [`core/rate_limiter.py`](../core/rate_limiter.py)

#### 10.4 数据加密

**加密方式**: Fernet 对称加密

**加密内容**:
- 数据库密码
- API Token
- 敏感配置

**密钥管理**: `.secret.key` 文件存储

**代码位置**: [`core/secrets.py`](../core/secrets.py)

---

## API 接口清单

### 认证接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | 公开 |
| POST | `/api/auth/login` | 用户登录 | 公开 |
| POST | `/api/auth/refresh` | 刷新 Token | 公开 |
| POST | `/api/auth/logout` | 用户登出 | 认证 |

### 策略接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/strategies` | 获取策略列表 | 认证 |
| GET | `/api/strategies/{code}` | 获取策略详情 | 认证 |
| POST | `/api/strategies/{code}/execute` | 执行策略 | Trader+ |
| PUT | `/api/strategies/{code}/params` | 更新策略参数 | Admin |

### 回测接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/backtest/run` | 运行回测 | Analyst+ |
| GET | `/api/backtest/results` | 获取回测结果 | 认证 |
| GET | `/api/backtest/results/{id}` | 获取回测详情 | 认证 |
| DELETE | `/api/backtest/results/{id}` | 删除回测结果 | Admin |

### 交易接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/trading/order` | 提交订单 | Trader+ |
| GET | `/api/trading/orders` | 获取订单列表 | 认证 |
| GET | `/api/trading/positions` | 获取持仓列表 | 认证 |
| GET | `/api/trading/account` | 获取账户信息 | 认证 |
| POST | `/api/trading/cancel/{order_no}` | 撤销订单 | Trader+ |

### 数据接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/data/sync` | 触发数据同步 | Admin |
| GET | `/api/data/sync/status` | 获取同步状态 | 认证 |
| GET | `/api/data/stocks` | 获取股票列表 | 认证 |
| GET | `/api/data/daily/{code}` | 获取日线数据 | 认证 |

### AI 诊断接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/diagnosis/{code}` | AI 股票诊断 | Analyst+ |
| GET | `/api/diagnosis/{code}/report` | 获取诊断报告 | Analyst+ |

### 风控接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/risk/check` | 执行风控检查 | 认证 |
| GET | `/api/risk/rules` | 获取风控规则 | 认证 |
| PUT | `/api/risk/rules/{code}` | 更新风控规则 | Admin |

### 监控接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/status` | 系统健康检查 | 公开 |
| GET | `/metrics` | Prometheus 指标 | 公开 |
| GET | `/api/tasks/{task_id}` | 获取任务状态 | 认证 |

---

## 用户角色与权限

### 角色定义

```
Admin (管理员)
  ├── 所有系统权限
  ├── 用户管理
  ├── 系统配置
  └── 数据管理

Trader (交易员)
  ├── 策略执行
  ├── 下单交易
  ├── 查看持仓
  └── 查看订单

Analyst (分析师)
  ├── 查看数据
  ├── 运行回测
  ├── AI 诊断
  └── 查看报告

Viewer (观察者)
  └── 只读权限
```

### 权限矩阵

| 功能 | Admin | Trader | Analyst | Viewer |
|------|-------|--------|---------|--------|
| 用户管理 | ✅ | ❌ | ❌ | ❌ |
| 系统配置 | ✅ | ❌ | ❌ | ❌ |
| 策略管理 | ✅ | ✅ | ⚠️ 只读 | ⚠️ 只读 |
| 策略执行 | ✅ | ✅ | ❌ | ❌ |
| 回测运行 | ✅ | ✅ | ✅ | ❌ |
| 交易下单 | ✅ | ✅ | ❌ | ❌ |
| 数据同步 | ✅ | ❌ | ❌ | ❌ |
| AI 诊断 | ✅ | ✅ | ✅ | ❌ |
| 查看报告 | ✅ | ✅ | ✅ | ✅ |
| 风控配置 | ✅ | ❌ | ❌ | ❌ |

---

## 附录

### A. 数据库表结构

详见 [`db/migrations/`](../db/migrations/) 目录下的迁移脚本。

### B. 配置文件说明

详见 [`config/.env.example`](../config/.env.example)。

### C. 依赖包清单

详见 [`requirements.txt`](../requirements.txt)。

---

**文档维护**: Lingma (AI Assistant)  
**最后更新**: 2026-04-15
