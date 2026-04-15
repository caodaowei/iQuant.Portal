# iQuant 量化交易系统 - 系统架构文档

**版本**: v2.0  
**更新日期**: 2026-04-15  
**状态**: ✅ 生产就绪

---

## 📋 目录

1. [架构概述](#架构概述)
2. [部署架构](#部署架构)
3. [技术架构](#技术架构)
4. [数据架构](#数据架构)
5. [安全架构](#安全架构)
6. [运维架构](#运维架构)

---

## 架构概述

### 系统定位

iQuant 是一个企业级量化交易系统，提供从数据采集、策略研发、回测验证到交易执行的完整解决方案。

### 设计原则

1. **高可用性**: 服务冗余、故障自动恢复
2. **高性能**: 异步处理、多级缓存、数据库优化
3. **可扩展性**: 微服务化、水平扩展能力
4. **安全性**: 多层防护、数据加密、权限控制
5. **可维护性**: 模块化设计、完善文档、自动化测试

### 架构演进

```
V1.0 (单体架构)
  └─ Flask + SQLite + 同步处理

V1.5 (分层架构)  
  ├─ Flask + PostgreSQL
  ├─ 策略引擎 + 回测引擎
  └─ 简单缓存

V2.0 (现代架构) ← 当前版本
  ├─ FastAPI (异步) + Flask (兼容)
  ├─ PostgreSQL + Redis + Celery
  ├─ Vue 3 前端
  └─ Prometheus + Grafana 监控

V3.0 (规划中)
  ├─ 微服务架构
  ├─ Kubernetes 编排
  ├─ 消息队列 (Kafka)
  └─ AI 增强策略
```

---

## 部署架构

### 开发环境

```
┌─────────────────────────────────────┐
│         开发者工作站                 │
├─────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐        │
│  │ VS Code  │  │ PyCharm  │        │
│  └──────────┘  └──────────┘        │
│         │              │             │
│  ┌──────┴──────────────┴──────┐    │
│  │   Python Virtual Env      │    │
│  │   - FastAPI/Flask         │    │
│  │   - PostgreSQL (Docker)   │    │
│  │   - Redis (Docker)        │    │
│  └───────────────────────────┘    │
└─────────────────────────────────────┘
```

### 测试环境

```
┌──────────────────────────────────────────┐
│          Docker Compose 环境              │
├──────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐         │
│  │  FastAPI   │  │   Flask    │         │
│  │  :8000     │  │   :5000    │         │
│  └────────────┘  └────────────┘         │
│         │               │                │
│  ┌──────┴───────────────┴──────┐        │
│  │      Celery Worker           │        │
│  └─────────────────────────────┘        │
│         │                               │
│  ┌──────┴───────────────┐              │
│  │  PostgreSQL :5432    │              │
│  │  Redis      :6379    │              │
│  └──────────────────────┘              │
└──────────────────────────────────────────┘
```

### 生产环境

```
                         ┌─────────────┐
                         │   Users     │
                         └──────┬──────┘
                                │
                    ┌───────────┴───────────┐
                    │   Load Balancer       │
                    │   (Nginx/HAProxy)     │
                    └───────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
    ┌─────────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐
    │  FastAPI Node1 │ │ FastAPI     │ │ FastAPI     │
    │  (Primary)     │ │ Node2       │ │ Node3       │
    └────────┬───────┘ └──────┬──────┘ └──────┬──────┘
             │                │                │
             └────────────────┼────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────┴──────┐ ┌────┴──────┐ ┌─────┴──────┐
    │ PostgreSQL     │ │  Redis    │ │   Celery   │
    │ Primary        │ │ Cluster   │ │ Workers    │
    └────────┬───────┘ └───────────┘ └────────────┘
             │
    ┌────────┴───────┐
    │ PostgreSQL     │
    │ Replica        │
    └────────────────┘
```

### Docker Compose 服务编排

```yaml
# docker-compose.yml 核心服务
services:
  # 应用服务
  iquant-fastapi:      # FastAPI 主应用
    replicas: 1-3      # 可水平扩展
    resources:
      limits:
        cpus: '2'
        memory: 4G
  
  iquant-flask:        # Flask 兼容服务
    profiles: [flask]  # 可选启动
  
  celery-worker:       # Celery 工作进程
    deploy:
      replicas: 2-4    # 根据任务量扩展
  
  # 基础设施
  postgres:            # PostgreSQL 数据库
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:               # Redis 缓存
    volumes:
      - redis_data:/data
  
  # 监控服务
  prometheus:          # 指标收集
    profiles: [monitoring]
  
  grafana:             # 可视化面板
    profiles: [monitoring]
  
  flower:              # Celery 监控
    profiles: [monitoring]
```

---

## 技术架构

### 后端架构

#### 1. Web 层

**FastAPI 异步服务** (`web/app_async.py`)

```python
# 核心特性
- 原生 async/await 支持
- 自动 API 文档生成 (Swagger/OpenAPI)
- Pydantic 数据验证
- 依赖注入系统
- 中间件支持

# 性能指标
- QPS: 500-800 req/s
- P95 延迟: < 100ms
- 并发连接: 1000+
```

**Flask 同步服务** (`web/app.py`)

```python
# 用途
- 兼容旧版代码
- 模板渲染页面
- 渐进式迁移过渡

# 计划
- V2.0: 双轨运行
- V2.5: 逐步废弃
- V3.0: 完全移除
```

#### 2. 业务逻辑层

```
core/
├── data_fetcher.py       # 数据获取器
├── cache.py              # 缓存管理器
├── strategy_manager.py   # 策略管理器
├── backtest_engine.py    # 回测引擎
├── risk_engine.py        # 风控引擎
├── trading_executor.py   # 交易执行器
├── agents.py             # AI 智能体
├── tasks.py              # Celery 任务
├── auth.py               # 认证授权
├── rate_limiter.py       # API 限流
├── secrets.py            # 数据加密
└── metrics.py            # 监控指标
```

#### 3. 数据访问层

**SQLAlchemy ORM**
```python
# 异步 Session
async with AsyncSession(engine) as session:
    result = await session.execute(query)
    return result.scalars().all()

# 连接池配置
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

**Redis 客户端**
```python
# 连接池
redis_pool = redis.ConnectionPool.from_url(
    REDIS_URL,
    max_connections=50,
    decode_responses=False
)

# 使用示例
async with redis.Redis(connection_pool=redis_pool) as r:
    await r.setex(key, ttl, value)
```

### 前端架构

#### Vue 3 项目结构

```
frontend/
├── src/
│   ├── api/              # API 调用封装
│   │   ├── auth.ts
│   │   ├── strategies.ts
│   │   ├── backtest.ts
│   │   └── trading.ts
│   ├── components/       # 通用组件
│   │   ├── StockChart.vue
│   │   ├── StrategyCard.vue
│   │   └── OrderForm.vue
│   ├── views/            # 页面视图
│   │   ├── Dashboard.vue
│   │   ├── Strategies.vue
│   │   ├── Backtest.vue
│   │   └── Trading.vue
│   ├── stores/           # Pinia 状态管理
│   │   ├── user.ts
│   │   └── strategies.ts
│   ├── router/           # 路由配置
│   │   └── index.ts
│   ├── types/            # TypeScript 类型
│   ├── utils/            # 工具函数
│   ├── App.vue
│   └── main.ts
├── package.json
├── vite.config.ts
└── tsconfig.json
```

#### 状态管理 (Pinia)

```typescript
// stores/strategies.ts
export const useStrategyStore = defineStore('strategies', {
  state: () => ({
    strategies: [],
    loading: false,
    error: null
  }),
  
  actions: {
    async fetchStrategies() {
      this.loading = true
      try {
        this.strategies = await api.getStrategies()
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    }
  }
})
```

#### 路由守卫

```typescript
// router/index.ts
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else if (to.meta.requiresRole && !hasRole(userStore.role, to.meta.requiresRole)) {
    next('/403')
  } else {
    next()
  }
})
```

### 任务队列架构

#### Celery 拓扑

```
┌──────────────┐
│   Clients    │  (FastAPI/Flask)
└──────┬───────┘
       │ Publish
       ▼
┌──────────────┐
│   Redis      │  (Broker)
│   Broker     │
└──────┬───────┘
       │ Consume
       ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Worker 1   │  │   Worker 2   │  │   Worker 3   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │ Store Results
                         ▼
                  ┌──────────────┐
                  │   Redis      │  (Backend)
                  │   Backend    │
                  └──────────────┘
```

#### 任务类型与优先级

| 任务类型 | 优先级 | 队列 | 并发数 | 超时 |
|---------|-------|------|-------|------|
| 数据同步 | High | data_sync | 4 | 300s |
| 回测执行 | Medium | backtest | 2 | 600s |
| AI 诊断 | Low | diagnosis | 2 | 120s |

---

## 数据架构

### 数据流图

```
外部数据源
(Tushare/AkShare)
      │
      ▼
┌─────────────┐
│ DataFetcher │ ──── Miss ────→ 调用 API
└──────┬──────┘
       │ Hit
       ▼
┌─────────────┐
│ Redis Cache │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ PostgreSQL  │ ────→ 持久化存储
└─────────────┘
       │
       ▼
┌─────────────┐
│ 业务模块     │ (策略/回测/交易)
└─────────────┘
```

### 数据存储策略

#### 热数据 (Redis)
- 股票实时行情 (TTL: 1h)
- 策略信号缓存 (TTL: 30min)
- 用户会话 (TTL: 30min)
- 热点查询结果 (TTL: 可变)

**容量规划**: 
- 初始: 2GB
- 增长: 10GB/年
- 淘汰策略: LRU

#### 温数据 (PostgreSQL - 主库)
- 最近1年行情数据
- 活跃策略配置
- 近期回测结果
- 当前持仓和订单

**容量规划**:
- 初始: 50GB
- 增长: 100GB/年

#### 冷数据 (PostgreSQL - 归档)
- 历史行情数据 (>1年)
- 已完成回测
- 历史交易记录
- 审计日志

**归档策略**:
- 按月归档
- 压缩存储
- 可在线查询

### 数据备份策略

```
每日备份 (增量)
  ├─ 时间: 凌晨 2:00
  ├─ 保留: 7天
  └─ 存储: S3/本地

每周备份 (全量)
  ├─ 时间: 周日 3:00
  ├─ 保留: 4周
  └─ 存储: S3/本地

每月备份 (全量)
  ├─ 时间: 月初 4:00
  ├─ 保留: 12个月
  └─ 存储: 异地存储
```

---

## 安全架构

### 多层防护体系

```
┌─────────────────────────────────────────┐
│          Layer 1: 网络层                 │
│  - Firewall                              │
│  - DDoS Protection                       │
│  - IP Whitelist                          │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│          Layer 2: 接入层                 │
│  - HTTPS/TLS                            │
│  - Nginx Rate Limiting                  │
│  - WAF (Web Application Firewall)       │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│          Layer 3: 应用层                 │
│  - JWT Authentication                   │
│  - RBAC Authorization                   │
│  - API Rate Limiting                    │
│  - Input Validation                     │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────┴──────────────────────┐
│          Layer 4: 数据层                 │
│  - SQL Injection Prevention             │
│  - Data Encryption                      │
│  - Access Control                       │
└─────────────────────────────────────────┘
```

### 认证流程

```
用户登录
   │
   ▼
验证用户名密码
   │
   ├── 失败 → 返回错误
   │
   ▼
生成 JWT Token
   ├─ Access Token (30min)
   └─ Refresh Token (7days)
   │
   ▼
返回 Token
   │
   ▼
后续请求携带 Token
   │
   ▼
验证 Token
   ├─ 有效 → 处理请求
   └─ 过期 → 使用 Refresh Token 刷新
```

### 数据安全

#### 敏感数据加密

```python
# 加密存储
class SecretsManager:
    def store_db_password(self, password):
        encrypted = self.fernet.encrypt(password.encode())
        save_to_env('DB_PASSWORD_ENCRYPTED', encrypted)
    
    def get_db_password(self):
        encrypted = read_from_env('DB_PASSWORD_ENCRYPTED')
        return self.fernet.decrypt(encrypted).decode()
```

#### 数据传输加密

```nginx
# Nginx SSL 配置
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

---

## 运维架构

### 监控体系

#### 三层监控

```
┌─────────────────────────────────────┐
│      业务监控                        │
│  - API QPS                           │
│  - 成功率                            │
│  - 业务指标 (回测次数、交易量)        │
└─────────────────────────────────────┘
              │
┌─────────────┴───────────────────────┐
│      应用监控                        │
│  - 响应时间 (P50/P95/P99)           │
│  - 错误率                            │
│  - 缓存命中率                        │
│  - 数据库连接池                      │
└─────────────────────────────────────┘
              │
┌─────────────┴───────────────────────┐
│      基础设施监控                     │
│  - CPU 使用率                        │
│  - 内存使用率                        │
│  - 磁盘 I/O                         │
│  - 网络流量                          │
└─────────────────────────────────────┘
```

#### Grafana 仪表板

**预设仪表板**:
1. **系统总览**: 关键业务指标
2. **API 性能**: 请求延迟、QPS、错误率
3. **数据库监控**: 连接数、查询性能、慢查询
4. **缓存监控**: 命中率、内存使用、Key 数量
5. **Celery 监控**: 任务队列、执行时间、失败率

### 日志体系

#### 日志分级

```python
# DEBUG: 调试信息
logger.debug(f"Cache hit for key: {key}")

# INFO: 一般信息
logger.info(f"Backtest completed: {result.total_return}")

# WARNING: 警告信息
logger.warning(f"Cache miss rate high: {miss_rate}%")

# ERROR: 错误信息
logger.error(f"Database connection failed: {error}")

# CRITICAL: 严重错误
logger.critical(f"System out of memory")
```

#### 日志聚合

```
应用日志
   │
   ▼
Filebeat (日志收集)
   │
   ▼
Logstash (日志处理)
   │
   ▼
Elasticsearch (日志存储)
   │
   ▼
Kibana (日志可视化)
```

### 告警策略

#### 告警规则

| 指标 | 阈值 | 级别 | 通知方式 |
|------|------|------|---------|
| API 错误率 | > 5% | Critical | 电话 + 短信 |
| P95 延迟 | > 500ms | Warning | 邮件 |
| 数据库连接池 | > 80% | Warning | 邮件 |
| 缓存命中率 | < 50% | Info | 钉钉 |
| 磁盘使用率 | > 85% | Warning | 邮件 |
| CPU 使用率 | > 90% | Critical | 电话 + 短信 |

### CI/CD 流程

```
代码提交
   │
   ▼
GitHub Actions
   │
   ├── 代码检查 (Lint)
   ├── 单元测试 (pytest)
   ├── 集成测试
   └── 构建 Docker 镜像
   │
   ▼
推送镜像到 Registry
   │
   ▼
部署到测试环境
   │
   ├── 自动化测试
   └── 人工验收
   │
   ▼
部署到生产环境
   │
   ├── 蓝绿部署
   └── 健康检查
```

---

## 附录

### A. 技术债务

| 项目 | 影响 | 优先级 | 计划解决版本 |
|------|------|-------|------------|
| Flask 兼容层 | 中 | 低 | V2.5 |
| 旧版前端模板 | 低 | 低 | V3.0 |
| 单体架构限制 | 中 | 中 | V3.0 |

### B. 未来规划

#### V2.5 (2026-Q3)
- [ ] 移除 Flask 兼容层
- [ ] WebSocket 实时行情推送
- [ ] 移动端 App
- [ ] 更多量化策略

#### V3.0 (2026-Q4)
- [ ] 微服务拆分
- [ ] Kubernetes 编排
- [ ] Kafka 消息队列
- [ ] AI 增强策略推荐
- [ ] 多租户支持

### C. 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Vue 3 官方文档](https://vuejs.org/)
- [Celery 最佳实践](https://docs.celeryq.dev/)
- [Prometheus 监控](https://prometheus.io/docs/)

---

**文档维护**: Lingma (AI Assistant)  
**最后更新**: 2026-04-15
