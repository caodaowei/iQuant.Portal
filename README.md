# iQuant 量化交易系统

## 项目结构

```
iquant/
├── config/           # 配置文件
├── core/               # 核心模块
│   ├── database.py          # 数据库连接 ✅
│   ├── data_fetcher.py      # 数据获取 ✅
│   ├── data_sync.py         # 数据同步 ✅
│   ├── strategy_manager.py  # 策略管理器 ✅
│   ├── backtest_engine.py   # 回测引擎 ✅
│   ├── risk_engine.py       # 风控引擎 ✅
│   └── trading_executor.py  # 交易执行器 ✅
├── data/            # 数据目录
├── db/              # 数据库迁移
│   └── migrations/
├── models/          # 数据模型
├── strategies/         # 策略模块
│   └── timing/         # 择时策略 ✅
│       ├── base.py
│       ├── ma_strategy.py
│       ├── macd_strategy.py
│       ├── rsi_strategy.py
│       └── boll_strategy.py
├── utils/              # 工具函数
├── tests/              # 测试
├── web/                # Web界面 ✅
│   ├── app.py
│   └── templates/
│       └── index.html
├── main.py             # 入口文件
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
- [ ] 数据缓存管理 (Redis)
- [ ] 数据更新调度

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
- [ ] 可视化报告

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
- [x] Flask Web服务
- [x] 系统状态监控
- [x] 策略管理界面
- [x] 回测执行界面
- [x] 数据同步接口
- [x] 风控检查接口
- [x] 交易接口 (下单/持仓/订单)
- [x] Systemd服务部署

## 安装

```bash
pip install -e ".[dev]"
```

## 配置

复制 `.env.example` 到 `.env` 并填写配置：

```bash
cp config/.env.example config/.env
```

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
- 本地访问: http://localhost:5000
- 网络访问: http://10.3.0.9:5000

## 数据库

```bash
# 执行迁移
psql -h localhost -U iquant_user -d iquant_strategy -f db/migrations/001_create_base_tables.sql
```
