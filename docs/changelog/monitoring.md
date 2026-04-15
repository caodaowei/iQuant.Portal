# iQuant 监控系统使用指南

本文档介绍如何使用 iQuant 系统的监控和可观测性功能。

## 目录

- [架构概览](#架构概览)
- [快速开始](#快速开始)
- [Prometheus 指标](#prometheus-指标)
- [Grafana Dashboard](#grafana-dashboard)
- [Celery Flower](#celery-flower)
- [日志系统](#日志系统)
- [告警配置](#告警配置)

---

## 架构概览

iQuant 监控系统基于以下组件构建：

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  FastAPI    │────▶│  Prometheus  │────▶│   Grafana   │
│  Application│     │   (Metrics)  │     │ (Dashboard) │
└─────────────┘     └──────────────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│   Celery    │────▶ Flower (Task Monitoring)
│   Worker    │
└─────────────┘
       │
       ▼
┌─────────────┐
│   Loguru    │────▶ File Logging (logs/iquant.log)
│   Logging   │
└─────────────┘
```

### 组件说明

| 组件 | 端口 | 用途 |
|------|------|------|
| FastAPI | 8000 | 主应用 + Metrics 端点 |
| Flask | 5000 | 模板渲染页面（可选） |
| Celery Worker | - | 异步任务处理 |
| Flower | 5555 | Celery 任务监控面板 |
| Prometheus | 9090 | 指标收集和存储 |
| Grafana | 3000 | 可视化 Dashboard |
| PostgreSQL | 5432 | 主数据库 |
| Redis | 6379 | 缓存 + 消息队列 |

---

## 快速开始

### 1. 启动完整监控栈

```bash
# 启动所有服务（包括监控组件）
docker-compose --profile monitoring up -d

# 仅启动核心服务（不含监控）
docker-compose up -d

# 启动核心服务 + Flask（不含监控）
docker-compose --profile flask up -d
```

### 2. 访问各个面板

| 服务 | URL | 默认凭据 |
|------|-----|----------|
| FastAPI API | http://localhost:8000 | - |
| API 文档 | http://localhost:8000/api/docs | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin / admin |
| Flower | http://localhost:5555 | - |

### 3. 验证指标收集

```bash
# 检查 metrics 端点
curl http://localhost:8000/metrics

# 应该看到 Prometheus 格式的指标输出
```

---

## Prometheus 指标

### HTTP 请求指标

| 指标名称 | 类型 | 标签 | 说明 |
|----------|------|------|------|
| `http_requests_total` | Counter | method, endpoint, status | HTTP 请求总数 |
| `http_request_duration_seconds` | Histogram | method, endpoint | 请求延迟分布 |
| `http_request_size_bytes` | Histogram | method, endpoint | 请求大小 |
| `http_response_size_bytes` | Histogram | method, endpoint | 响应大小 |

### 业务指标

| 指标名称 | 类型 | 标签 | 说明 |
|----------|------|------|------|
| `backtest_executions_total` | Counter | strategy, status | 回测执行次数 |
| `ai_diagnosis_total` | Counter | stock_code, status | AI 诊断次数 |
| `data_sync_total` | Counter | sync_type, status | 数据同步次数 |
| `stock_selection_total` | Counter | status | 选股执行次数 |
| `risk_check_total` | Counter | result | 风控检查次数 |
| `celery_tasks_total` | Counter | task_name, status | Celery 任务计数 |
| `celery_task_duration_seconds` | Histogram | task_name | Celery 任务持续时间 |

### 缓存指标

| 指标名称 | 类型 | 标签 | 说明 |
|----------|------|------|------|
| `cache_operations_total` | Counter | operation, namespace, result | 缓存操作计数 |
| `cache_hit_ratio` | Gauge | namespace | 缓存命中率 |

### 数据库指标

| 指标名称 | 类型 | 标签 | 说明 |
|----------|------|------|------|
| `db_query_duration_seconds` | Histogram | query_type | 数据库查询延迟 |
| `db_slow_queries_total` | Counter | query_type | 慢查询计数 |
| `db_connection_pool_size` | Gauge | pool_type | 连接池大小 |
| `db_connection_pool_active` | Gauge | pool_type | 活跃连接数 |
| `db_connection_pool_available` | Gauge | pool_type | 可用连接数 |

### Redis 指标

| 指标名称 | 类型 | 说明 |
|----------|------|------|
| `redis_connection_status` | Gauge | Redis 连接状态 (1=connected, 0=disconnected) |
| `redis_command_duration_seconds` | Histogram | Redis 命令执行时间 |

### 系统指标

| 指标名称 | 类型 | 说明 |
|----------|------|------|
| `app_uptime_seconds` | Gauge | 应用运行时间 |
| `active_users` | Gauge | 活跃用户数 |

---

## Grafana Dashboard

### 导入 Dashboard

Dashboard 配置文件位于 `config/grafana/dashboards/`，会自动加载到 Grafana。

当前提供的 Dashboard：

1. **iQuant 系统监控总览** (`iquant-overview.json`)
   - HTTP 请求 QPS 和延迟
   - 业务指标（回测、AI诊断、数据同步）
   - 缓存性能
   - 数据库性能
   - Redis 状态

### 自定义 Dashboard

1. 在 Grafana UI 中创建新 Dashboard
2. 使用 Prometheus 作为数据源
3. 保存后会自动同步到 `config/grafana/dashboards/` 目录

### 常用查询示例

```promql
# QPS (每秒请求数)
rate(http_requests_total[5m])

# P95 请求延迟
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 缓存命中率
cache_hit_ratio{namespace='total'}

# 回测成功率
rate(backtest_executions_total{status='success'}[5m]) / rate(backtest_executions_total[5m])

# 慢查询速率
rate(db_slow_queries_total[5m])

# 数据库连接池使用率
db_connection_pool_active{pool_type='master'} / db_connection_pool_size{pool_type='master'}
```

---

## Celery Flower

Flower 提供 Celery 任务队列的实时监控：

### 功能

- 实时查看任务状态（PENDING, STARTED, SUCCESS, FAILURE）
- 任务执行时间统计
- Worker 状态监控
- 任务重试和撤销

### 访问

```bash
# 启动 Flower
docker-compose --profile monitoring up flower -d

# 访问面板
open http://localhost:5555
```

---

## 日志系统

### 日志配置

日志使用 Loguru 库，配置在 `main.py` 的 `setup_logging()` 函数中。

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 日志文件 | `logs/iquant.log` | 应用日志文件 |
| 轮转大小 | 10 MB | 单文件最大大小 |
| 保留时间 | 30 天 | 日志保留期限 |
| 默认级别 | INFO | 可通过环境变量调整 |

### 日志级别

```bash
# 设置日志级别
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 查看日志

```bash
# 实时查看日志
tail -f logs/iquant.log

# Docker 日志
docker-compose logs -f iquant-fastapi
docker-compose logs -f celery-worker
```

### 结构化日志（未来扩展）

项目已安装 `structlog` 库，可用于更强大的结构化日志：

```python
import structlog

logger = structlog.get_logger()
logger.info("user_login", user_id=123, ip="192.168.1.1")
```

---

## 告警配置

### Prometheus 告警规则（待实现）

创建 `config/prometheus/rules.yml`：

```yaml
groups:
  - name: iquant_alerts
    rules:
      # 高错误率告警
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "高错误率检测"
          description: "5xx 错误率超过 10%"

      # 慢查询告警
      - alert: SlowQueries
        expr: rate(db_slow_queries_total[5m]) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "慢查询过多"
          description: "每分钟慢查询超过 1 次"

      # Redis 断连告警
      - alert: RedisDown
        expr: redis_connection_status == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis 连接断开"
```

### Grafana 告警

1. 在 Grafana Dashboard 中选择面板
2. 点击 "Alert" -> "Create Alert"
3. 配置告警条件和通知渠道

支持的通知我道：
- Email
- Slack
- Discord
- Webhook

---

## 故障排查

### Prometheus 无法抓取指标

```bash
# 检查 Prometheus 配置
docker exec -it iquant-prometheus cat /etc/prometheus/prometheus.yml

# 检查目标状态
# 访问 http://localhost:9090/targets

# 测试 metrics 端点
curl http://localhost:8000/metrics
```

### Grafana 无法连接 Prometheus

```bash
# 检查网络连通性
docker exec -it iquant-grafana ping prometheus

# 检查数据源配置
# 访问 http://localhost:3000/connections/datasources
```

### 指标缺失

```bash
# 检查 FastAPI 是否正常启动
docker-compose logs iquant-fastapi

# 检查中间件是否正确加载
# 查看 app_async.py 中的 PrometheusMiddleware 注册
```

---

## 最佳实践

1. **定期备份 Grafana Dashboard**
   ```bash
   cp -r config/grafana/dashboards/ backups/grafana-$(date +%Y%m%d)/
   ```

2. **监控磁盘使用**
   ```bash
   # Prometheus 数据保留 30 天
   # 定期检查 volume 使用情况
   docker system df
   ```

3. **设置合理的告警阈值**
   - 避免告警疲劳
   - 分级告警（warning/critical）
   - 配置通知静默时段

4. **生产环境安全**
   - 修改 Grafana 默认密码
   - 启用 HTTPS
   - 限制 Prometheus/Grafana 访问 IP

---

## 扩展阅读

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [FastAPI 监控最佳实践](https://fastapi.tiangolo.com/tutorial/middleware/)
- [Celery Flower 文档](https://flower.readthedocs.io/)
