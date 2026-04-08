"""
iQuant AI 多智能体系统

基于 TradingAgents 架构的 5 阶段分析流程
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
from loguru import logger


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"


class AgentRole(Enum):
    """Agent 角色"""
    MARKET_ANALYST = "market_analyst"
    FUNDAMENTALS_ANALYST = "fundamentals_analyst"
    NEWS_ANALYST = "news_analyst"
    BULLISH_RESEARCHER = "bullish_researcher"
    BEARISH_RESEARCHER = "bearish_researcher"
    RESEARCH_FACILITATOR = "research_facilitator"
    TRADER = "trader"
    AGGRESSIVE_RISK = "aggressive_risk"
    NEUTRAL_RISK = "neutral_risk"
    CONSERVATIVE_RISK = "conservative_risk"
    RISK_FACILITATOR = "risk_facilitator"
    MANAGER = "manager"


@dataclass
class AnalysisReport:
    """分析报告"""
    agent_name: str
    role: AgentRole
    content: str
    score: int
    key_points: List[str] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FinalDecision:
    """最终投资决策"""
    decision: SignalType
    code: str
    confidence: int
    action_plan: Dict[str, Any]
    reasoning: str
    risk_warning: str
    time_horizon: str
    supporting_reports: List[str] = field(default_factory=list)
    opposing_views: List[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(self, name: str, role: AgentRole):
        self.name = name
        self.role = role
        self.memory: List[Dict] = []
    
    @abstractmethod
    def analyze(self, code: str, context: Dict = None) -> AnalysisReport:
        """执行分析"""
        pass


class MarketAnalyst(BaseAgent):
    """技术面分析师"""
    
    def __init__(self):
        super().__init__("MarketAnalyst", AgentRole.MARKET_ANALYST)
    
    def analyze(self, code: str, context: Dict = None) -> AnalysisReport:
        """技术面分析"""
        logger.info(f"[{self.name}] 分析 {code} 技术面")
        
        try:
            from core.data_fetcher import data_fetcher
            from strategies.timing import MATrendStrategy, MACDStrategy, RSIStrategy
            
            df = data_fetcher.get_stock_daily(code, days=60)
            if df.empty:
                return AnalysisReport(
                    agent_name=self.name,
                    role=self.role,
                    content="无法获取数据",
                    score=0,
                    key_points=["数据获取失败"]
                )
            
            # 运行技术指标策略
            ma_strategy = MATrendStrategy()
            macd_strategy = MACDStrategy()
            rsi_strategy = RSIStrategy()
            
            latest_ma = ma_strategy.get_latest_signal(df)
            latest_macd = macd_strategy.get_latest_signal(df)
            latest_rsi = rsi_strategy.get_latest_signal(df)
            
            # 综合判断
            buy_signals = sum([
                1 if s and s.signal_type == 'BUY' else 0 
                for s in [latest_ma, latest_macd, latest_rsi]
            ])
            sell_signals = sum([
                1 if s and s.signal_type == 'SELL' else 0 
                for s in [latest_ma, latest_macd, latest_rsi]
            ])
            
            if buy_signals >= 2:
                signal = "看涨"
                score = 60 + buy_signals * 10
            elif sell_signals >= 2:
                signal = "看跌"
                score = 60 + sell_signals * 10
            else:
                signal = "中性"
                score = 50
            
            key_points = [
                f"均线策略: {latest_ma.signal_type if latest_ma else '无信号'}",
                f"MACD策略: {latest_macd.signal_type if latest_macd else '无信号'}",
                f"RSI策略: {latest_rsi.signal_type if latest_rsi else '无信号'}",
            ]
            
            content = f"""## 技术面分析报告

### 总体判断
**{signal}** (置信度: {score}%)

### 技术指标分析
- MA趋势: {latest_ma.reason if latest_ma else '无明确信号'}
- MACD: {latest_macd.reason if latest_macd else '无明确信号'}
- RSI: {latest_rsi.reason if latest_rsi else '无明确信号'}

### 关键价位
- 当前价格: {df['close'].iloc[-1]:.2f}
- 20日均线: {df['close'].rolling(20).mean().iloc[-1]:.2f}
"""
            
            return AnalysisReport(
                agent_name=self.name,
                role=self.role,
                content=content,
                score=score,
                key_points=key_points,
                signals=[signal]
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            return AnalysisReport(
                agent_name=self.name,
                role=self.role,
                content=f"分析失败: {e}",
                score=0,
                key_points=["分析异常"]
            )


class FundamentalsAnalyst(BaseAgent):
    """基本面分析师"""
    
    def __init__(self):
        super().__init__("FundamentalsAnalyst", AgentRole.FUNDAMENTALS_ANALYST)
    
    def analyze(self, code: str, context: Dict = None) -> AnalysisReport:
        """基本面分析"""
        logger.info(f"[{self.name}] 分析 {code} 基本面")
        
        try:
            from core.database import db
            
            financial = db.fetch_one("""
                SELECT * FROM stock_financial
                WHERE code = %s
                ORDER BY report_date DESC
                LIMIT 1
            """, (code,))
            
            if not financial:
                return AnalysisReport(
                    agent_name=self.name,
                    role=self.role,
                    content="无财务数据",
                    score=50,
                    key_points=["缺少财务数据"]
                )
            
            roe = financial.get('roe', 0) or 0
            gross_margin = financial.get('gross_margin', 0) or 0
            debt_ratio = financial.get('debt_ratio', 0) or 0
            
            score = 50
            key_points = []
            
            if roe > 0.15:
                score += 15
                key_points.append(f"ROE优秀: {roe:.1%}")
            elif roe > 0.10:
                score += 10
                key_points.append(f"ROE良好: {roe:.1%}")
            
            if gross_margin > 0.30:
                score += 10
                key_points.append(f"毛利率高: {gross_margin:.1%}")
            
            if debt_ratio < 0.60:
                score += 10
                key_points.append(f"负债率健康: {debt_ratio:.1%}")
            
            signal = "优质" if score >= 75 else "良好" if score >= 60 else "一般"
            
            content = f"""## 基本面分析报告

### 总体判断
**{signal}** (评分: {score}/100)

### 核心财务指标
- ROE: {roe:.1%}
- 毛利率: {gross_margin:.1%}
- 负债率: {debt_ratio:.1%}

### 关键亮点
{chr(10).join(['- ' + kp for kp in key_points])}
"""
            
            return AnalysisReport(
                agent_name=self.name,
                role=self.role,
                content=content,
                score=score,
                key_points=key_points,
                signals=[signal]
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            return AnalysisReport(
                agent_name=self.name,
                role=self.role,
                content=f"分析失败: {e}",
                score=50,
                key_points=["分析异常"]
            )


class NewsAnalyst(BaseAgent):
    """舆情分析师"""
    
    def __init__(self):
        super().__init__("NewsAnalyst", AgentRole.NEWS_ANALYST)
    
    def analyze(self, code: str, context: Dict = None) -> AnalysisReport:
        """舆情分析"""
        logger.info(f"[{self.name}] 分析 {code} 舆情")
        
        try:
            from core.data_fetcher import data_fetcher
            
            df = data_fetcher.get_stock_daily(code, days=20)
            if df.empty:
                return AnalysisReport(
                    agent_name=self.name,
                    role=self.role,
                    content="无数据",
                    score=50,
                    key_points=["数据不足"]
                )
            
            recent_return = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
            
            if recent_return > 0.10:
                sentiment = "积极"
                score = 70
            elif recent_return > 0:
                sentiment = "中性偏多"
                score = 60
            elif recent_return > -0.10:
                sentiment = "中性偏空"
                score = 40
            else:
                sentiment = "消极"
                score = 30
            
            content = f"""## 舆情面分析报告

### 市场情绪
**{sentiment}** (评分: {score}/100)

### 近期走势
- 20日涨跌幅: {recent_return:.1%}
- 市场情绪: {sentiment}
"""
            
            return AnalysisReport(
                agent_name=self.name,
                role=self.role,
                content=content,
                score=score,
                key_points=[f"20日涨跌: {recent_return:.1%}", f"市场情绪: {sentiment}"],
                signals=[sentiment]
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] 分析失败: {e}")
            return AnalysisReport(
                agent_name=self.name,
                role=self.role,
                content=f"分析失败: {e}",
                score=50,
                key_points=["分析异常"]
            )


class Manager(BaseAgent):
    """基金经理 - 最终决策者"""
    
    def __init__(self):
        super().__init__("Manager", AgentRole.MANAGER)
    
    def analyze(self, code: str, context: Dict = None) -> AnalysisReport:
        """做出最终决策"""
        logger.info(f"[{self.name}] 做出 {code} 最终决策")
        
        analyst_reports = context.get('analyst_reports', []) if context else []
        
        weights = {
            AgentRole.MARKET_ANALYST: 0.25,
            AgentRole.FUNDAMENTALS_ANALYST: 0.35,
            AgentRole.NEWS_ANALYST: 0.20,
        }
        
        weighted_score = 0
        for report in analyst_reports:
            weight = weights.get(report.role, 0.1)
            weighted_score += report.score * weight
        
        if weighted_score >= 70:
            decision = SignalType.BUY
            confidence = int(weighted_score)
        elif weighted_score >= 50:
            decision = SignalType.HOLD
            confidence = int(weighted_score)
        elif weighted_score >= 30:
            decision = SignalType.WATCH
            confidence = int(weighted_score)
        else:
            decision = SignalType.SELL
            confidence = int(100 - weighted_score)
        
        try:
            from core.data_fetcher import data_fetcher
            df = data_fetcher.get_stock_daily(code, days=5)
            current_price = df['close'].iloc[-1] if not df.empty else 0
        except:
            current_price = 0
        
        target_price = current_price * 1.15 if current_price > 0 else 0
        stop_loss = current_price * 0.92 if current_price > 0 else 0
        
        content = f"""# 最终投资决策报告

## 投资决策
**{decision.value.upper()}** (置信度: {confidence}%)

## 执行方案
- 当前价格: {current_price:.2f}
- 目标价格: {target_price:.2f}
- 止损价格: {stop_loss:.2f}
- 建议仓位: {'10%' if decision == SignalType.BUY else '5%' if decision == SignalType.HOLD else '0%'}
- 持有周期: 1-3个月

## 综合评分
{weighted_score:.0f}/100
"""
        
        return AnalysisReport(
            agent_name=self.name,
            role=self.role,
            content=content,
            score=confidence,
            key_points=[f"决策: {decision.value}", f"置信度: {confidence}%"],
            signals=[decision.value]
        )
    
    def make_final_decision(self, code: str, context: Dict) -> FinalDecision:
        """生成结构化最终决策"""
        report = self.analyze(code, context)
        
        signal_str = report.signals[0] if report.signals else "hold"
        decision_map = {
            "buy": SignalType.BUY,
            "sell": SignalType.SELL,
            "hold": SignalType.HOLD,
            "watch": SignalType.WATCH,
        }
        decision = decision_map.get(signal_str, SignalType.HOLD)
        
        try:
            from core.data_fetcher import data_fetcher
            df = data_fetcher.get_stock_daily(code, days=5)
            current_price = df['close'].iloc[-1] if not df.empty else 0
        except:
            current_price = 0
        
        return FinalDecision(
            decision=decision,
            code=code,
            confidence=report.score,
            action_plan={
                "entry_price": current_price,
                "target_price": current_price * 1.15 if current_price > 0 else 0,
                "stop_loss": current_price * 0.92 if current_price > 0 else 0,
                "position_size": 0.10 if decision == SignalType.BUY else 0.05,
            },
            reasoning=report.content,
            risk_warning="严格止损，控制仓位",
            time_horizon="1-3个月",
            supporting_reports=[r.agent_name for r in context.get('analyst_reports', []) if r.score > 60],
            opposing_views=[r.agent_name for r in context.get('analyst_reports', []) if r.score < 40],
        )


class MultiAgentSystem:
    """多智能体系统"""
    
    def __init__(self):
        self.market_analyst = MarketAnalyst()
        self.fundamentals_analyst = FundamentalsAnalyst()
        self.news_analyst = NewsAnalyst()
        self.manager = Manager()
    
    def diagnose(self, code: str) -> Dict:
        """执行完整诊断流程"""
        logger.info(f"开始多智能体诊断: {code}")
        
        # 阶段1: 分析师团队并行分析
        logger.info("阶段1: 分析师团队分析")
        market_report = self.market_analyst.analyze(code)
        fundamentals_report = self.fundamentals_analyst.analyze(code)
        news_report = self.news_analyst.analyze(code)
        
        analyst_reports = [market_report, fundamentals_report, news_report]
        
        # 阶段5: 基金经理最终决策
        logger.info("阶段5: 基金经理决策")
        context = {'analyst_reports': analyst_reports}
        final_report = self.manager.analyze(code, context)
        final_decision = self.manager.make_final_decision(code, context)
        
        result = {
            'code': code,
            'stages': {
                'stage1_analysts': [r.__dict__ for r in analyst_reports],
                'stage5_decision': final_report.__dict__,
            },
            'final_decision': final_decision,
            'reports': {
                'market': market_report,
                'fundamentals': fundamentals_report,
                'news': news_report,
                'final': final_report,
            }
        }
        
        logger.info(f"诊断完成: {code} -> {final_decision.decision.value}")
        return result


# 便捷函数
def diagnose_stock(code: str) -> Dict:
    """便捷诊断函数"""
    system = MultiAgentSystem()
    return system.diagnose(code)


if __name__ == "__main__":
    # 测试
    result = diagnose_stock("000001")
    print(json.dumps(result, indent=2, default=str))
