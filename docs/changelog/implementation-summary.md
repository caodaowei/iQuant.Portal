# Prometheus + Grafana 监控系统实施总结

## 实施概览

本次实施为 iQuant 量化交易系统添加了完整的 Prometheus + Grafana 监控体系，实现了应用程序性能监控（APM）、业务指标追踪和可视化 Dashboard。

---

## 新增文件清单

### 1. 核心监控模块

| 文件 | 说明 | 行数 |
|------|------|------|
| `core/metrics.py` | Prometheus 指标收集和中间件 | ~350 |
| `config/prometheus.yml` | Prometheus 配置文件 | ~35 |

### 2. Grafana 配置

| 文件 | 说明 |
|------|------|
| `config/grafana/provisioning/datasources.yml` | 数据源自动配置 |
| `config/grafana/provisioning/dashboards.yml` | Dashboard 自动加载配置 |
| `config/grafana/dashboards/iquant-overview.json` | 系统监控总览 Dashboard |

### 3. 启动脚本

| 文件 | 说明 |
|------|------|
| `start_monitoring.sh` | Linux/Mac 启动脚本 |
| `start_monitoring.bat` | Windows 启动脚本 |

### 4. 文档

| 文件 | 说明 |
|------|------|
| `MONITORING.md` | 监控系统使用指南 |
| `IMPLEMENTATION_SUMMARY.md` | 本实施总结 |

---

## 修改文件清单

### 1. FastAPI 应用 (`web/app_async.py`)

**修改内容：**
- 导入 `core.metrics` 模块
- 添加 `PrometheusMiddleware` 中间件
- 添加 `/metrics` 端点
- 在业务端点中添加指标收集：
  - `/api/backtest/async` - 回测执行计数
  - `/api/backtest/sync` - 回测成功/失败计数 + 持续时间
  - `/api/diagnosis/{stock_code}/async` - AI 诊断计数
  - `/api/diagnosis/{stock_code}/sync` - AI 诊断缓存命中/成功/失败
  - `/api/data/sync/{stock_code}` - 单只股票同步计数
  - `/api/data/sync/batch` - 批量同步计数
  - `/api/stock-selection` - 选股成功/失败计数
  - `/api/risk/check` - 风控检查通过/拒绝计数

**代码变更量：** +80 行

### 2. Docker 配置 (`docker-compose.yml`)

**新增服务：**
- `iquant-fastapi` - FastAPI 主应用（端口 8000）
- `iquant-flask` - Flask 应用（端口 5000，profile: flask）
- `celery-worker` - Celery 异步任务处理
- `flower` - Celery 监控面板（端口 5555，profile: monitoring）
- `prometheus` - Prometheus 监控（端口 9090，profile: monitoring）
- `grafana` - Grafana 可视化（端口 3000，profile: monitoring）

**新增卷：**
- `prometheus_data` - Prometheus 数据存储
- `grafana_data` - Grafana 配置和 Dashboard 存储

**代码变更量：** +120 行

### 3. Dockerfile

**修改内容：**
- 添加 `curl` 用于健康检查
- 暴露端口改为 8000（FastAPI）
- 健康检查端点改为 `/health`
- 默认启动命令改为 Uvicorn + FastAPI

**代码变更量：** +10 行

---

## 收集的指标分类

### HTTP 请求指标（7 个）

1. `http_requests_total` - 请求总数（Counter）
2. `http_request_duration_seconds` - 请求延迟（Histogram）
3. `http_request_size_bytes` - 请求大小（Histogram）
4. `http_response_size_bytes` - 响应大小（Histogram）

### 业务指标（6 个）

5. `backtest_executions_total` - 回测执行次数
6. `ai_diagnosis_total` - AI 诊断次数
7. `data_sync_total` - 数据同步次数
8. `stock_selection_total` - 选股执行次数
9. `risk_check_total` - 风控检查次数
10. `celery_tasks_total` - Celery 任务计数
11. `celery_task_duration_seconds` - Celery 任务持续时间

### 缓存指标（2 个）

12. `cache_operations_total` - 缓存操作计数
13. `cache_hit_ratio` - 缓存命中率

### 数据库指标（5 个）

14. `db_query_duration_seconds` - 查询延迟
15. `db_slow_queries_total` - 慢查询计数
16. `db_connection_pool_size` - 连接池大小
17. `db_connection_pool_active` - 活跃连接数
18. `db_connection_pool_available` - 可用连接数

### Redis 指标（2 个）

19. `redis_connection_status` - 连接状态
20. `redis_command_duration_seconds` - 命令执行时间

### 系统指标（2 个）

21. `app_uptime_seconds` - 应用运行时间
22. `active_users` - 活跃用户数

**总计：22 个监控指标**

---

## Grafana Dashboard 面板

### HTTP 请求概览（6 个面板）

1. QPS (每秒请求数) - 时序图
2. 请求延迟分布 - 热力图
3. HTTP 状态码分布 - 饼图
4. P95/P99 延迟 - 统计面板
5. 应用运行时间 - 统计面板

### 业务指标（3 个面板）

6. 回测执行次数 - 时序图
7. AI 诊断次数 - 时序图
8. 数据同步次数 - 时序图

### 缓存性能（2 个面板）

9. 缓存命中率 - 仪表盘
10. 缓存操作统计 - 时序图

### 数据库性能（3 个面板）

11. 数据库查询延迟 - 时序图
12. 数据库连接池 - 时序图
13. 慢查询计数 - 统计面板

### 其他（2 个面板）

14. Redis 状态 - 统计面板
15. 风控检查统计 - 时序图

**总计：15 个监控面板**

---

## 使用方式

### 快速启动

```bash
# Windows
start_monitoring.bat full

# Linux/Mac
chmod +x start_monitoring.sh
./start_monitoring.sh full
```

### 访问面板

| 服务 | URL | 凭据 |
|------|-----|------|
| FastAPI API | http://localhost:8000 | - |
| API 文档 | http://localhost:8000/api/docs | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin |
| Flower | http://localhost:5555 | - |

### 验证指标

```bash
curl http://localhost:8000/metrics
```

---

## 技术亮点

### 1. 自动化指标收集中间件

`PrometheusMiddleware` 自动拦截所有 HTTP 请求，无需手动埋点：
- 自动提取端点路径（将 ID 替换为 `{id}`）
- 自动记录请求计数、延迟、大小
- 零侵入式设计

### 2. 多维度业务指标

每个业务操作都记录了成功/失败状态：
- 回测：按策略类型和状态分类
- AI 诊断：按股票代码和缓存命中分类
- 数据同步：按同步类型（单只/批量）分类

### 3. 容器化部署

使用 Docker Compose profiles 实现灵活部署：
- `default` - 核心服务
- `flask` - Flask 应用（可选）
- `monitoring` - 监控组件（可选）

### 4. Grafana 自动配置

- 数据源自动注册（Prometheus）
- Dashboard 自动加载
- 支持 UI 修改后自动同步

### 5. 健康检查

所有服务都配置了健康检查：
- FastAPI: HTTP `/health` 端点
- PostgreSQL: `pg_isready` 命令
- Redis: `redis-cli ping` 命令

---

## 架构优势

### 可观测性三层

1. **Metrics（指标）** - Prometheus + Grafana
   - 定量数据分析
   - 趋势预测
   - 告警触发

2. **Logging（日志）** - Loguru
   - 详细事件记录
   - 问题排查
   - 审计追踪

3. **Tracing（追踪）** - 未来扩展
   - 分布式追踪
   - 调用链分析
   - 性能瓶颈定位

### 监控粒度

- **应用层** - HTTP 请求、业务逻辑
- **中间件层** - 缓存、数据库、消息队列
- **基础设施层** - CPU、内存、磁盘、网络（可通过 Node Exporter 扩展）

---

## 后续优化建议

### 短期（1-2 周）

1. **添加告警规则**
   - 创建 `config/prometheus/rules.yml`
   - 配置高错误率、慢查询、Redis 断连告警
   - 集成邮件/Slack 通知

2. **完善 Celery 监控**
   - 在 `core/tasks.py` 中添加任务级别指标
   - 记录任务重试次数
   - 跟踪任务队列长度

3. **增强日志系统**
   - 启用 `structlog` 结构化日志
   - 添加日志聚合（Loki 或 ELK）
   - 实现日志告警

### 中期（1 个月）

1. **分布式追踪**
   - 集成 OpenTelemetry
   - 添加 Jaeger 或 Zipkin
   - 实现端到端调用链追踪

2. **前端监控**
   - 添加前端性能指标
   - 用户行为追踪
   - 错误率监控

3. **A/B 测试框架**
   - 基于指标的实验平台
   - 策略效果对比

### 长期（3 个月）

1. **机器学习运维（MLOps）**
   - 模型性能监控
   - 数据漂移检测
   - 自动重新训练触发

2. **容量规划**
   - 基于历史数据的资源预测
   - 自动扩缩容配置
   - 成本优化

---

## 注意事项

### 生产环境部署

1. **安全性**
   - 修改 Grafana 默认密码
   - 启用 HTTPS/TLS
   - 限制 Prometheus/Grafana 访问 IP
   - 使用 Docker secrets 管理敏感信息

2. **性能**
   - 调整 Prometheus 抓取间隔
   - 配置数据保留策略（当前 30 天）
   - 监控磁盘使用情况

3. **高可用**
   - Prometheus Federation
   - Grafana HA 模式
   - 负载均衡配置

### 资源需求

| 组件 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| Prometheus | 0.5 core | 512 MB | 10 GB |
| Grafana | 0.25 core | 256 MB | 2 GB |
| FastAPI | 0.5 core | 512 MB | - |
| Celery Worker | 1 core | 1 GB | - |
| **总计** | **~2.25 cores** | **~2.3 GB** | **~12 GB** |

---

## 参考资料

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [FastAPI 监控最佳实践](https://fastapi.tiangolo.com/tutorial/middleware/)
- [Celery Flower 文档](https://flower.readthedocs.io/)
- [Loguru 文档](https://loguru.readthedocs.io/)

---

## 变更日志

### v1.0.0 (2026-04-15)

- ✅ 实现 Prometheus 指标收集中间件
- ✅ 添加 22 个监控指标
- ✅ 配置 Prometheus + Grafana 容器化部署
- ✅ 创建 Grafana Dashboard（15 个面板）
- ✅ 集成 Celery Flower 监控
- ✅ 编写完整的使用文档
- ✅ 提供便捷的启动脚本

---

**实施完成！** 🎉

现在您可以通过访问 http://localhost:3000 查看完整的系统监控 Dashboard。
