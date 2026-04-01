# iQuant 量化交易系统

基于 Python + Flask 的可配置多智能体量化交易系统。

## 特性

- **可配置多智能体系统**: 通过 YAML 配置多个 AI Agent
- **技术面分析**: MA/MACD/RSI/布林带策略
- **基本面分析**: ROE/毛利率/负债率等财务指标
- **风险分析**: 波动率/回撤/财务风险评估
- **情绪分析**: 基于价格和成交量的情绪判断
- **自动报告生成**: 合并多 Agent 分析结果

## 快速开始

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行 Web 服务
python web/app.py
```

### Docker 部署

```bash
# 构建镜像
docker build -t iquant-portal .

# 运行容器
docker run -p 5000:5000 iquant-portal
```

### Docker Compose

```bash
docker-compose up -d
```

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/v2/agents` | 查看 Agent 配置 |
| `GET /api/v2/diagnosis/<code>` | 股票诊断 (JSON) |
| `GET /api/v2/reports/<code>` | 股票报告 (HTML) |

## 配置

编辑 `config/agents.yaml` 自定义 Agent：

```yaml
agents:
  - name: "技术面分析师"
    agent_type: "market_analyst"
    enabled: true
    weight: 0.25
    params:
      days: 60
      strategies: ["MA", "MACD", "RSI"]
```

## 部署

自动部署通过 GitHub Actions 触发：
- Push 到 `master` 分支 → 自动构建并部署到服务器

## License

MIT
