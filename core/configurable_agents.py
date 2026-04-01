"""
iQuant 可配置多智能体系统

支持通过配置文件定义多个 Agent，合并生成报告
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime
import json
import yaml
from pathlib import Path
from loguru import logger


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"


class AgentType(Enum):
    """Agent 类型"""
    MARKET_ANALYST = "market_analyst"           # 技术面分析师
    FUNDAMENTALS_ANALYST = "fundamentals_analyst"  # 基本面分析师
    NEWS_ANALYST = "news_analyst"               # 舆情分析师
    SENTIMENT_ANALYST = "sentiment_analyst"     # 情绪分析师
    RISK_ANALYST = "risk_analyst"               # 风险分析师
    SECTOR_ANALYST = "sector_analyst"           # 行业分析师
    CUSTOM = "custom"                           # 自定义分析师


@dataclass
class AgentConfig:
    """Agent 配置"""
    name: str
    agent_type: str
    enabled: bool = True
    weight: float = 1.0
    params: Dict[str, Any] = field(default_factory=dict)
    prompt_template: Optional[str] = None
    model: Optional[str] = None


@dataclass
class AnalysisReport:
    """分析报告"""
    agent_name: str
    agent_type: str
    content: str
    score: int
    key_points: List[str] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class MergedReport:
    """合并后的报告"""
    title: str
    summary: str
    overall_score: int
    decision: str
    confidence: int
    sections: List[Dict[str, Any]]
    action_plan: Dict[str, Any]
    risk_warnings: List[str]
    contributing_agents: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.agent_type = config.agent_type
        self.weight = config.weight
        self.params = config.params
    
    @abstractmethod
    def analyze(self, code: str, context: Dict = None) -> AnalysisReport:
        """执行分析"""
        pass
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.config.enabled


class MarketAnalystAgent(BaseAgent):
    """技术面分析师 Agent"""
    
    def analyze(self, code: str, context: Dict = None) -> AnalysisReport:
        """技术面分析"""
        logger.info(f"[{self.name}] 分析 {code} 技术面")
        
        try:
            from core.data_fetcher import data_fetcher
            from strategies.timing import MATrendStrategy, MACDStrategy, RSIStrategy, BollingerStrategy
            
            days = self.params.get('days', 60)
            df = data_fetcher.get_stock_daily(code, days=days)
            
            if df.empty:
                return AnalysisReport(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    content="无法获取数据",
                    score=50,
                    key_points=["数据获取失败"]
                )
            
            # 运行技术指标策略
            strategies_to_run = self.params.get('strategies', ['MA', 'MACD', 'RSI'])
            signals = []
            
            if 'MA' in strategies_to_run:
                ma_strategy = MATrendStrategy()
                latest_ma = ma_strategy.get_latest_signal(df)
                if latest_ma:
                    signals.append(('MA', latest_ma.signal_type, latest_ma.reason))
            
            if 'MACD' in strategies_to_run:
                macd_strategy = MACDStrategy()
                latest_macd = macd_strategy.get_latest_signal(df)
                if latest_macd:
                    signals.append(('MACD', latest_macd.signal_type, latest_macd.reason))
            
            if 'RSI' in strategies_to_run:
                rsi_strategy = RSIStrategy()
                latest_rsi = rsi_strategy.get_latest_signal(df)
                if latest_rsi:
                    signals.append(('RSI', latest_rsi.signal_type, latest_rsi.reason))
            
            if 'BOLL' in strategies_to_run:
                boll_strategy = BollingerStrategy()
                latest_boll = boll_strategy.get_latest_signal(df)
                if latest_boll:
                    signals.append(('BOLL', latest_boll.signal_type, latest_boll.reason))
            
            # 计算得分
            buy_count = sum(1 for _, signal_type, _ in signals if signal_type == 'BUY')
            sell_count = sum(1 for _, signal_type, _ in signals if signal_type == 'SELL')
            total = len(signals) if signals else 1
            
            score = 50 + (buy_count - sell_count) * (50 / max(total, 1))
            score = max(0, min(100, int(score)))
            
            # 生成信号
            if buy_count > sell_count:
                signal = "看涨"
            elif sell_count > buy_count:
                signal = "看跌"
            else:
                signal = "中性"
            
            # 关键价位
            current_price = df['close'].iloc[-1]
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            ma60 = df['close'].rolling(60).mean().iloc[-1]
            
            key_points = [f"{name}: {signal_type}" for name, signal_type, _ in signals]
            key_points.extend([
                f"当前价格: {current_price:.2f}",
                f"20日均线: {ma20:.2f}",
                f"60日均线: {ma60:.2f}",
            ])
            
            content = f"""## {self.name} - 技术面分析

### 总体判断
**{signal}** (评分: {score}/100)

### 技术指标信号
{chr(10).join([f"- **{name}**: {signal_type} - {reason}" for name, signal_type, reason in signals])}

### 关键价位
- 当前价格: {current_price:.2f}
- 20日均线: {ma20:.2f} ({'上方' if current_price > ma20 else '下方'})
- 60日均线: {ma60:.2f} ({'上方' if current_price > ma60 else '下方'})

### 趋势判断
{'多头排列' if current_price > ma20 > ma60 else '空头排列' if current_price < ma20 < ma60 else '震荡整理'}
"""
            
            return AnalysisReport(
                agent_name=self.name,
                agent_type=self.agent_type,
                content=content,
                score=score,
                key_points=key_points,
                signals=[signal],
                metadata={
                    'current_price': current_price,
                    'ma20': ma20,
                    'ma60': ma60,
                    'signals': signals
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            return AnalysisReport(
                agent_name=self.name,
                agent_type=self.agent_type,
                content=f"分析失败: {e}",
                score=50,
                key_points=["分析异常"],
                risks=[str(e)]
            )


class FundamentalsAnalystAgent(BaseAgent):
    """基本面分析师 Agent"""
    
    def analyze(self, code: str, context: Dict = None) -> AnalysisReport:
        """基本面分析"""
        logger.info(f"[{self.name}] 分析 {code} 基本面")
        
        try:
            from core.database import db
            
            # 获取财务数据
            financial = db.fetch_one("""
                SELECT * FROM stock_financial
                WHERE code = %s
                ORDER BY report_date DESC
                LIMIT 1
            """, (code,))
            
            # 获取股票信息
            stock_info = db.fetch_one("""
                SELECT name, industry FROM stock_info WHERE code = %s
            """, (code,))
            
            if not financial:
                return AnalysisReport(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    content="无财务数据",
                    score=50,
                    key_points=["缺少财务数据"]
                )
            
            # 提取指标
            roe = financial.get('roe', 0) or 0
            roa = financial.get('roa', 0) or 0
            gross_margin = financial.get('gross_margin', 0) or 0
            net_margin = financial.get('net_margin', 0) or 0
            debt_ratio = financial.get('debt_ratio', 0) or 0
            revenue_yoy = financial.get('revenue_yoy', 0) or 0
            profit_yoy = financial.get('profit_yoy', 0) or 0
            
            # 计算得分
            score = 50
            key_points = []
            risks = []
            
            # ROE 评分
            if roe > 0.20:
                score += 15
                key_points.append(f"ROE优秀: {roe:.1%}")
            elif roe > 0.15:
                score += 10
                key_points.append(f"ROE良好: {roe:.1%}")
            elif roe > 0.10:
                score += 5
                key_points.append(f"ROE一般: {roe:.1%}")
            else:
                risks.append(f"ROE偏低: {roe:.1%}")
            
            # 毛利率评分
            if gross_margin > 0.40:
                score += 10
                key_points.append(f"毛利率优秀: {gross_margin:.1%}")
            elif gross_margin > 0.30:
                score += 5
                key_points.append(f"毛利率良好: {gross_margin:.1%}")
            
            # 负债率评分
            if debt_ratio < 0.40:
                score += 10
                key_points.append(f"负债率健康: {debt_ratio:.1%}")
            elif debt_ratio > 0.70:
                score -= 10
                risks.append(f"负债率偏高: {debt_ratio:.1%}")
            
            # 成长性评分
            if revenue_yoy > 0.20 and profit_yoy > 0.20:
                score += 10
                key_points.append(f"高成长: 营收{revenue_yoy:.1%}, 利润{profit_yoy:.1%}")
            elif revenue_yoy > 0 or profit_yoy > 0:
                score += 5
                key_points.append(f"正增长: 营收{revenue_yoy:.1%}, 利润{profit_yoy:.1%}")
            elif revenue_yoy < 0 and profit_yoy < 0:
                risks.append(f"业绩下滑: 营收{revenue_yoy:.1%}, 利润{profit_yoy:.1%}")
            
            score = max(0, min(100, score))
            
            # 信号判断
            if score >= 80:
                signal = "优质"
            elif score >= 65:
                signal = "良好"
            elif score >= 50:
                signal = "一般"
            else:
                signal = "较差"
            
            content = f"""## {self.name} - 基本面分析

### 总体判断
**{signal}** (评分: {score}/100)

### 核心财务指标
| 指标 | 数值 | 评价 |
|------|------|------|
| ROE | {roe:.1%} | {'优秀' if roe > 0.15 else '良好' if roe > 0.10 else '一般'} |
| ROA | {roa:.1%} | {'优秀' if roa > 0.10 else '良好' if roa > 0.05 else '一般'} |
| 毛利率 | {gross_margin:.1%} | {'优秀' if gross_margin > 0.40 else '良好' if gross_margin > 0.30 else '一般'} |
| 净利率 | {net_margin:.1%} | {'优秀' if net_margin > 0.20 else '良好' if net_margin > 0.10 else '一般'} |
| 负债率 | {debt_ratio:.1%} | {'健康' if debt_ratio < 0.50 else '偏高' if debt_ratio > 0.70 else '一般'} |
| 营收增长 | {revenue_yoy:.1%} | {'增长' if revenue_yoy > 0 else '下滑'} |
| 利润增长 | {profit_yoy:.1%} | {'增长' if profit_yoy > 0 else '下滑'} |

### 关键亮点
{chr(10).join(['- ✅ ' + kp for kp in key_points]) if key_points else '- 暂无突出亮点'}

### 风险提示
{chr(10).join(['- ⚠️ ' + r for r in risks]) if risks else '- 暂无重大风险'}
"""
            
            return AnalysisReport(
                agent_name=self.name,
                agent_type=self.agent_type,
                content=content,
                score=score,
                key_points=key_points,
                signals=[signal],
                risks=risks,
                metadata={
                    'roe': roe,
                    'gross_margin': gross_margin,
                    'debt_ratio': debt_ratio,
                    'industry': stock_info.get('industry') if stock_info else None
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            return AnalysisReport(
                agent_name=self.name,
                agent_type=self.agent_type,
                content=f"分析失败: {e}",
                score=50,
                key_points=["分析异常"],
                risks=[str(e)]
            )


class RiskAnalystAgent(BaseAgent):
    """风险分析师 Agent"""
    
    def analyze(self, code: str, context: Dict = None) -> AnalysisReport:
        """风险分析"""
        logger.info(f"[{self.name}] 分析 {code} 风险")
        
        try:
            from core.data_fetcher import data_fetcher
            from core.database import db
            
            days = self.params.get('days', 60)
            df = data_fetcher.get_stock_daily(code, days=days)
            
            risks = []
            key_points = []
            
            if not df.empty:
                # 计算波动率
                returns = df['close'].pct_change().dropna()
                volatility = returns.std() * (252 ** 0.5)  # 年化波动率
                
                if volatility > 0.50:
                    risks.append(f"高波动风险: 年化波动率{volatility:.1%}")
                elif volatility > 0.30:
                    key_points.append(f"中等波动: 年化波动率{volatility:.1%}")
                else:
                    key_points.append(f"低波动: 年化波动率{volatility:.1%}")
                
                # 计算最大回撤
                cummax = df['close'].cummax()
                drawdown = (df['close'] - cummax) / cummax
                max_drawdown = drawdown.min()
                
                if max_drawdown < -0.30:
                    risks.append(f"回撤风险: 近期最大回撤{max_drawdown:.1%}")
                
                # 计算Beta（简化版）
                # 这里假设市场收益为0，实际应该获取大盘数据
                
                current_price = df['close'].iloc[-1]
            else:
                volatility = 0
                max_drawdown = 0
                current_price = 0
            
            # 检查财务风险
            financial = db.fetch_one("""
                SELECT debt_ratio, current_ratio FROM stock_financial
                WHERE code = %s ORDER BY report_date DESC LIMIT 1
            """, (code,))
            
            if financial:
                debt_ratio = financial.get('debt_ratio', 0) or 0
                if debt_ratio > 0.80:
                    risks.append(f"高负债风险: 负债率{debt_ratio:.1%}")
            
            # 计算风险评分 (越低越安全)
            risk_score = 50
            risk_score += len(risks) * 10
            risk_score = min(100, risk_score)
            
            # 安全评分 (越高越安全)
            safety_score = 100 - risk_score
            
            if safety_score >= 80:
                signal = "低风险"
            elif safety_score >= 60:
                signal = "中等风险"
            else:
                signal = "高风险"
            
            content = f"""## {self.name} - 风险分析

### 总体评估
**{signal}** (安全评分: {safety_score}/100)

### 波动率分析
- 年化波动率: {volatility:.1% if volatility else 'N/A'}
- 近期最大回撤: {max_drawdown:.1% if max_drawdown else 'N/A'}

### 风险因素
{chr(10).join(['- 🔴 ' + r for r in risks]) if risks else '- ✅ 未发现重大风险'}

### 风控建议
- 建议仓位: {'<5%' if safety_score < 40 else '<10%' if safety_score < 60 else '<20%' if safety_score < 80 else '<30%'}
- 止损设置: {current_price * 0.90:.2f if current_price else 'N/A'} (-10%)
"""
            
            return AnalysisReport(
                agent_name=self.name,
                agent_type=self.agent_type,
                content=content,
                score=safety_score,
                key_points=key_points,
                signals=[signal],
                risks=risks,
                metadata={
                    'volatility': volatility,
                    'max_drawdown': max_drawdown
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            return AnalysisReport(
                agent_name=self.name,
                agent_type=self.agent_type,
                content=f"分析失败: {e}",
                score=50,
                key_points=["分析异常"],
                risks=[str(e)]
            )


class SentimentAnalystAgent(BaseAgent):
    """情绪分析师 Agent"""
    
    def analyze(self, code: str, context: Dict = None) -> AnalysisReport:
        """情绪分析（基于价格和成交量）"""
        logger.info(f"[{self.name}] 分析 {code} 情绪")
        
        try:
            from core.data_fetcher import data_fetcher
            
            days = self.params.get('days', 20)
            df = data_fetcher.get_stock_daily(code, days=days)
            
            if df.empty or len(df) < 5:
                return AnalysisReport(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    content="数据不足",
                    score=50,
                    key_points=["缺少近期数据"]
                )
            
            # 计算近期涨跌幅
            recent_return = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
            
            # 计算成交量变化
            avg_volume = df['volume'].mean()
            recent_volume = df['volume'].iloc[-5:].mean()
            volume_change = (recent_volume - avg_volume) / avg_volume if avg_volume > 0 else 0
            
            # 计算连续涨跌天数
            returns = df['close'].pct_change().dropna()
            up_days = sum(returns > 0)
            down_days = sum(returns < 0)
            
            # 情绪评分
            score = 50
            key_points = []
            
            if recent_return > 0.10:
                score += 20
                key_points.append(f"强势上涨: {recent_return:.1%}")
            elif recent_return > 0.05:
                score += 10
                key_points.append(f"温和上涨: {recent_return:.1%}")
            elif recent_return < -0.10:
                score -= 20
                key_points.append(f"明显下跌: {recent_return:.1%}")
            elif recent_return < -0.05:
                score -= 10
                key_points.append(f"温和下跌: {recent_return:.1%}")
            
            if volume_change > 0.50:
                score += 10
                key_points.append(f"放量: 成交量增加{volume_change:.0%}")
            elif volume_change < -0.30:
                score -= 5
                key_points.append(f"缩量: 成交量减少{abs(volume_change):.0%}")
            
            score = max(0, min(100, score))
            
            if score >= 70:
                sentiment = "积极"
            elif score >= 55:
                sentiment = "中性偏多"
            elif score >= 45:
                sentiment = "中性"
            elif score >= 30:
                sentiment = "中性偏空"
            else:
                sentiment = "消极"
            
            content = f"""## {self.name} - 市场情绪分析

### 情绪判断
**{sentiment}** (情绪评分: {score}/100)

### 近期走势
- {days}日涨跌幅: {recent_return:.1%}
- 上涨天数: {up_days}
- 下跌天数: {down_days}

### 成交量分析
- 平均成交量: {avg_volume:,.0f}
- 近期成交量: {recent_volume:,.0f}
- 变化: {volume_change:+.0%}

### 情绪解读
{'市场情绪积极，资金关注度提升' if score >= 70 else 
 '市场情绪温和，保持关注' if score >= 50 else 
 '市场情绪偏弱，谨慎观望' if score >= 30 else 
 '市场情绪低迷，注意风险'}
"""
            
            return AnalysisReport(
                agent_name=self.name,
                agent_type=self.agent_type,
                content=content,
                score=score,
                key_points=key_points,
                signals=[sentiment],
                metadata={
                    'recent_return': recent_return,
                    'volume_change': volume_change,
                    'up_days': up_days,
                    'down_days': down_days
                }
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            return AnalysisReport(
                agent_name=self.name,
                agent_type=self.agent_type,
                content=f"分析失败: {e}",
                score=50,
                key_points=["分析异常"]
            )


# Agent 工厂
AGENT_REGISTRY: Dict[str, Callable[[AgentConfig], BaseAgent]] = {
    'market_analyst': MarketAnalystAgent,
    'fundamentals_analyst': FundamentalsAnalystAgent,
    'risk_analyst': RiskAnalystAgent,
    'sentiment_analyst': SentimentAnalystAgent,
}


def create_agent(config: AgentConfig) -> Optional[BaseAgent]:
    """根据配置创建 Agent"""
    agent_class = AGENT_REGISTRY.get(config.agent_type)
    if agent_class:
        return agent_class(config)
    logger.warning(f"未知的 Agent 类型: {config.agent_type}")
    return None


class ConfigurableAgentSystem:
    """可配置多智能体系统"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.agents: List[BaseAgent] = []
        self.config_path = config_path or Path(__file__).parent.parent / "config" / "agents.yaml"
        self.load_config()
    
    def load_config(self):
        """加载 Agent 配置"""
        if not Path(self.config_path).exists():
            logger.info(f"配置文件不存在，使用默认配置: {self.config_path}")
            self._load_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.agents = []
            for agent_conf in config.get('agents', []):
                agent_config = AgentConfig(**agent_conf)
                agent = create_agent(agent_config)
                if agent:
                    self.agents.append(agent)
            
            logger.info(f"已加载 {len(self.agents)} 个 Agent")
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self._load_default_config()
    
    def _load_default_config(self):
        """加载默认配置"""
        default_agents = [
            AgentConfig(name="技术面分析师", agent_type="market_analyst", weight=0.25),
            AgentConfig(name="基本面分析师", agent_type="fundamentals_analyst", weight=0.30),
            AgentConfig(name="风险分析师", agent_type="risk_analyst", weight=0.20),
            AgentConfig(name="情绪分析师", agent_type="sentiment_analyst", weight=0.25),
        ]
        
        self.agents = [create_agent(conf) for conf in default_agents if create_agent(conf)]
        logger.info(f"已加载 {len(self.agents)} 个默认 Agent")
    
    def analyze(self, code: str) -> List[AnalysisReport]:
        """执行所有启用的 Agent 分析"""
        reports = []
        for agent in self.agents:
            if agent.is_enabled():
                try:
                    report = agent.analyze(code)
                    reports.append(report)
                except Exception as e:
                    logger.error(f"Agent {agent.name} 分析失败: {e}")
        return reports
    
    def merge_reports(self, code: str, reports: List[AnalysisReport]) -> MergedReport:
        """合并多个报告生成最终报告"""
        if not reports:
            return MergedReport(
                title=f"{code} 分析报告",
                summary="无可用分析结果",
                overall_score=50,
                decision="HOLD",
                confidence=0,
                sections=[],
                action_plan={},
                risk_warnings=["缺少分析数据"],
                contributing_agents=[]
            )
        
        # 计算加权得分
        total_weight = sum(r.weight for r in self.agents if r.is_enabled())
        weighted_score = sum(
            report.score * agent.weight 
            for report, agent in zip(reports, self.agents) 
            if agent.is_enabled()
        ) / total_weight if total_weight > 0 else 50
        
        overall_score = int(weighted_score)
        
        # 决策逻辑
        if overall_score >= 75:
            decision = "BUY"
            confidence = overall_score
        elif overall_score >= 60:
            decision = "HOLD"
            confidence = overall_score
        elif overall_score >= 40:
            decision = "WATCH"
            confidence = 100 - overall_score
        else:
            decision = "SELL"
            confidence = 100 - overall_score
        
        # 收集所有风险
        all_risks = []
        for report in reports:
            all_risks.extend(report.risks)
        
        # 生成执行方案
        try:
            from core.data_fetcher import data_fetcher
            df = data_fetcher.get_stock_daily(code, days=5)
            current_price = df['close'].iloc[-1] if not df.empty else 0
        except:
            current_price = 0
        
        position_size = {75: 0.20, 60: 0.10, 40: 0.05, 0: 0}.get(
            max([k for k in [75, 60, 40, 0] if overall_score >= k]), 0
        )
        
        action_plan = {
            "decision": decision,
            "current_price": round(current_price, 2) if current_price else None,
            "target_price": round(current_price * 1.15, 2) if current_price else None,
            "stop_loss": round(current_price * 0.92, 2) if current_price else None,
            "position_size": f"{position_size:.0%}",
            "time_horizon": "1-3个月"
        }
        
        # 生成摘要
        summary = f"""基于 {len(reports)} 个分析师的综合评估，{code} 的总体评分为 {overall_score}/100。
        
技术面、基本面、风险和情绪分析已完成。{f'发现 {len(all_risks)} 个风险因素，' if all_risks else '未发现重大风险，'}
建议操作: **{decision}** (置信度: {confidence}%)。
"""
        
        # 构建章节
        sections = []
        for report in reports:
            sections.append({
                "agent_name": report.agent_name,
                "agent_type": report.agent_type,
                "score": report.score,
                "content": report.content,
                "key_points": report.key_points
            })
        
        return MergedReport(
            title=f"{code} 综合分析报告",
            summary=summary,
            overall_score=overall_score,
            decision=decision,
            confidence=confidence,
            sections=sections,
            action_plan=action_plan,
            risk_warnings=all_risks[:5],  # 最多显示5个风险
            contributing_agents=[r.agent_name for r in reports]
        )
    
    def diagnose(self, code: str) -> Dict[str, Any]:
        """执行完整诊断并生成合并报告"""
        logger.info(f"开始可配置多智能体诊断: {code}")
        
        # 执行所有 Agent 分析
        reports = self.analyze(code)
        
        # 合并报告
        merged_report = self.merge_reports(code, reports)
        
        return {
            "code": code,
            "timestamp": datetime.now().isoformat(),
            "individual_reports": [
                {
                    "agent_name": r.agent_name,
                    "agent_type": r.agent_type,
                    "score": r.score,
                    "signals": r.signals,
                    "key_points": r.key_points,
                    "risks": r.risks
                }
                for r in reports
            ],
            "merged_report": {
                "title": merged_report.title,
                "summary": merged_report.summary,
                "overall_score": merged_report.overall_score,
                "decision": merged_report.decision,
                "confidence": merged_report.confidence,
                "action_plan": merged_report.action_plan,
                "risk_warnings": merged_report.risk_warnings,
                "contributing_agents": merged_report.contributing_agents,
                "sections": merged_report.sections
            }
        }


# 便捷函数
def diagnose_stock_with_config(code: str, config_path: Optional[str] = None) -> Dict:
    """使用配置诊断股票"""
    system = ConfigurableAgentSystem(config_path)
    return system.diagnose(code)


if __name__ == "__main__":
    # 测试
    result = diagnose_stock_with_config("000001")
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
