"""风控规则引擎"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from config.settings import settings
from core.database import db


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    rule_code: str
    rule_name: str
    passed: bool
    current_value: float
    threshold_value: float
    message: str
    level: str  # 'low', 'medium', 'high', 'critical'


@dataclass
class RiskCheckReport:
    """风控检查报告"""
    check_time: datetime
    overall_status: str  # 'pass', 'warning', 'violation'
    results: List[RiskCheckResult]
    violation_count: int
    warning_count: int


class RiskRule:
    """风控规则基类"""
    
    def __init__(
        self,
        code: str,
        name: str,
        category: str,
        threshold: float,
        level: str = "medium",
        action: str = "warning",
    ):
        self.code = code
        self.name = name
        self.category = category
        self.threshold = threshold
        self.level = level
        self.action = action
    
    def check(self, context: dict) -> RiskCheckResult:
        """执行检查"""
        raise NotImplementedError


class PositionLimitRule(RiskRule):
    """持仓限额规则"""
    
    def check(self, context: dict) -> RiskCheckResult:
        """检查持仓比例"""
        position_ratio = float(context.get("position_ratio", 0))
        
        passed = position_ratio <= self.threshold
        
        return RiskCheckResult(
            rule_code=self.code,
            rule_name=self.name,
            passed=passed,
            current_value=position_ratio,
            threshold_value=self.threshold,
            message=f"持仓比例 {position_ratio:.2%} {'未超过' if passed else '超过'} 限制 {self.threshold:.2%}",
            level=self.level if not passed else "low",
        )


class DrawdownLimitRule(RiskRule):
    """回撤限制规则"""
    
    def check(self, context: dict) -> RiskCheckResult:
        """检查最大回撤"""
        drawdown = float(context.get("drawdown", 0))
        
        passed = drawdown <= self.threshold
        
        return RiskCheckResult(
            rule_code=self.code,
            rule_name=self.name,
            passed=passed,
            current_value=drawdown,
            threshold_value=self.threshold,
            message=f"当前回撤 {drawdown:.2%} {'未超过' if passed else '超过'} 限制 {self.threshold:.2%}",
            level=self.level if not passed else "low",
        )


class DailyLossLimitRule(RiskRule):
    """单日亏损限制规则"""
    
    def check(self, context: dict) -> RiskCheckResult:
        """检查单日亏损"""
        daily_loss = float(context.get("daily_loss", 0))
        daily_loss_ratio = float(context.get("daily_loss_ratio", 0))
        
        passed = daily_loss_ratio <= self.threshold
        
        return RiskCheckResult(
            rule_code=self.code,
            rule_name=self.name,
            passed=passed,
            current_value=daily_loss_ratio,
            threshold_value=self.threshold,
            message=f"单日亏损 {daily_loss_ratio:.2%} ({daily_loss:,.2f}) {'未超过' if passed else '超过'} 限制 {self.threshold:.2%}",
            level=self.level if not passed else "low",
        )


class CashRatioRule(RiskRule):
    """现金比例规则"""
    
    def check(self, context: dict) -> RiskCheckResult:
        """检查现金比例"""
        cash_ratio = float(context.get("cash_ratio", 0))
        
        passed = cash_ratio >= self.threshold
        
        return RiskCheckResult(
            rule_code=self.code,
            rule_name=self.name,
            passed=passed,
            current_value=cash_ratio,
            threshold_value=self.threshold,
            message=f"现金比例 {cash_ratio:.2%} {'不低于' if passed else '低于'} 要求 {self.threshold:.2%}",
            level=self.level if not passed else "low",
        )


class BlacklistRule(RiskRule):
    """黑名单规则"""
    
    def check(self, context: dict) -> RiskCheckResult:
        """检查是否在黑名单"""
        stock_code = context.get("stock_code", "")
        
        # 查询黑名单
        try:
            result = db.fetch_one(
                """SELECT 1 FROM trade_blacklist 
                   WHERE stock_code = :code 
                   AND (expiry_date IS NULL OR expiry_date >= CURRENT_DATE)
                   LIMIT 1""",
                {"code": stock_code}
            )
            in_blacklist = result is not None
        except Exception:
            in_blacklist = False
        
        passed = not in_blacklist
        
        return RiskCheckResult(
            rule_code=self.code,
            rule_name=self.name,
            passed=passed,
            current_value=1 if in_blacklist else 0,
            threshold_value=0,
            message=f"股票 {stock_code} {'在' if in_blacklist else '不在'}交易黑名单中",
            level="critical" if in_blacklist else "low",
        )


class RiskEngine:
    """风控引擎"""
    
    # 默认规则配置
    DEFAULT_RULES = [
        {
            "code": "MAX_POSITION_RATIO",
            "name": "单票持仓上限",
            "category": "position",
            "threshold": 0.10,
            "level": "high",
            "action": "block",
            "class": PositionLimitRule,
        },
        {
            "code": "MAX_DRAWDOWN",
            "name": "最大回撤限制",
            "category": "drawdown",
            "threshold": 0.20,
            "level": "critical",
            "action": "reduce",
            "class": DrawdownLimitRule,
        },
        {
            "code": "DAILY_LOSS_LIMIT",
            "name": "单日亏损限制",
            "category": "drawdown",
            "threshold": 0.05,
            "level": "high",
            "action": "block",
            "class": DailyLossLimitRule,
        },
        {
            "code": "MIN_CASH_RATIO",
            "name": "最低现金比例",
            "category": "position",
            "threshold": 0.10,
            "level": "medium",
            "action": "warning",
            "class": CashRatioRule,
        },
        {
            "code": "TRADE_BLACKLIST",
            "name": "交易黑名单检查",
            "category": "compliance",
            "threshold": 0,
            "level": "critical",
            "action": "block",
            "class": BlacklistRule,
        },
    ]
    
    def __init__(self):
        self.rules: Dict[str, RiskRule] = {}
        self._init_default_rules()
        logger.info("风控引擎初始化")
    
    def _init_default_rules(self):
        """初始化默认规则"""
        for rule_config in self.DEFAULT_RULES:
            rule_class = rule_config.pop("class")
            rule = rule_class(**rule_config)
            self.rules[rule.code] = rule
        
        logger.info(f"加载了 {len(self.rules)} 个默认规则")
    
    def add_rule(self, rule: RiskRule) -> None:
        """添加规则"""
        self.rules[rule.code] = rule
        logger.info(f"添加规则: {rule.code}")
    
    def remove_rule(self, code: str) -> None:
        """移除规则"""
        if code in self.rules:
            del self.rules[code]
            logger.info(f"移除规则: {code}")
    
    def check_all(self, context: dict) -> RiskCheckReport:
        """执行所有规则检查"""
        results = []
        violation_count = 0
        warning_count = 0
        
        for rule in self.rules.values():
            result = rule.check(context)
            results.append(result)
            
            if not result.passed:
                if result.level in ("high", "critical"):
                    violation_count += 1
                else:
                    warning_count += 1
        
        # 确定总体状态
        if violation_count > 0:
            overall_status = "violation"
        elif warning_count > 0:
            overall_status = "warning"
        else:
            overall_status = "pass"
        
        report = RiskCheckReport(
            check_time=datetime.now(),
            overall_status=overall_status,
            results=results,
            violation_count=violation_count,
            warning_count=warning_count,
        )
        
        # 记录到数据库
        self._save_check_report(report, context)
        
        return report
    
    def check_trade(
        self,
        stock_code: str,
        trade_type: str,
        volume: int,
        price: float,
        account_context: dict,
    ) -> RiskCheckReport:
        """检查交易"""
        context = {
            "stock_code": stock_code,
            "trade_type": trade_type,
            "volume": volume,
            "price": price,
            **account_context,
        }
        
        return self.check_all(context)
    
    def can_trade(self, report: RiskCheckReport) -> bool:
        """判断是否允许交易"""
        # 有关键违规则不允许交易
        for result in report.results:
            if not result.passed and result.level == "critical":
                return False
        
        return True
    
    def _save_check_report(self, report: RiskCheckReport, context: dict) -> None:
        """保存检查报告到数据库"""
        try:
            import json
            results_json = json.dumps([{
                "code": r.rule_code,
                "passed": r.passed,
                "message": r.message,
            } for r in report.results], ensure_ascii=False)
            
            db.execute("""
                INSERT INTO risk_checks 
                (check_type, overall_status, violation_count, check_results)
                VALUES (:type, :status, :count, :results)
            """, {
                "type": context.get("check_type", "periodic"),
                "status": report.overall_status,
                "count": report.violation_count,
                "results": results_json,
            })
        except Exception as e:
            logger.warning(f"保存风控报告失败: {e}")
    
    def get_rules(self) -> List[dict]:
        """获取所有规则"""
        return [
            {
                "code": rule.code,
                "name": rule.name,
                "category": rule.category,
                "threshold": rule.threshold,
                "level": rule.level,
                "action": rule.action,
            }
            for rule in self.rules.values()
        ]


# 全局风控引擎实例
risk_engine = RiskEngine()
