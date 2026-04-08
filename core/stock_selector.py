"""
iQuant 多因子选股策略

基于价值、质量、动量、波动四个维度的多因子选股模型
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger


class FactorType(Enum):
    """因子类型"""
    VALUE = "value"           # 价值因子
    QUALITY = "quality"       # 质量因子
    MOMENTUM = "momentum"     # 动量因子
    VOLATILITY = "volatility" # 波动因子


@dataclass
class FactorWeight:
    """因子权重配置"""
    factor_type: FactorType
    weight: float
    parameters: Dict


@dataclass
class StockScore:
    """股票评分结果"""
    code: str
    name: str
    industry: str
    total_score: float
    factor_scores: Dict[FactorType, float]
    rank: int
    metrics: Dict  # 原始指标


@dataclass
class StockUniverse:
    """股票池筛选条件"""
    exclude_st: bool = True
    min_list_days: int = 252  # 上市至少1年
    min_market_cap: float = 1e8  # 最小市值1亿
    markets: List[str] = None  # ['SH', 'SZ']


class FactorCalculator:
    """因子计算器"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def calculate_value_factors(self, codes: List[str], date: str) -> pd.DataFrame:
        """
        计算价值因子
        
        指标：
        - PE（市盈率）
        - PB（市净率）
        - 股息率
        """
        logger.info(f"计算价值因子: {len(codes)} 只股票")
        
        results = []
        for code in codes:
            try:
                # 获取最新财务数据
                financial = self._get_financial_data(code, date)
                if not financial:
                    continue
                
                # 获取当前价格
                price_data = self._get_price_data(code, date)
                if not price_data:
                    continue
                
                # 计算估值指标
                pe = self._calculate_pe(financial, price_data)
                pb = self._calculate_pb(financial, price_data)
                dividend_yield = self._calculate_dividend_yield(financial, price_data)
                
                results.append({
                    'code': code,
                    'pe': pe,
                    'pb': pb,
                    'dividend_yield': dividend_yield,
                })
            except Exception as e:
                logger.warning(f"计算 {code} 价值因子失败: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def calculate_quality_factors(self, codes: List[str], date: str) -> pd.DataFrame:
        """
        计算质量因子
        
        指标：
        - ROE（净资产收益率）
        - ROA（总资产收益率）
        - 毛利率
        - 净利率
        - 负债率
        """
        logger.info(f"计算质量因子: {len(codes)} 只股票")
        
        results = []
        for code in codes:
            try:
                # 获取财务数据（近3年）
                financials = self._get_financial_data_history(code, date, years=3)
                if not financials or len(financials) < 2:
                    continue
                
                # 计算平均 ROE
                roe_avg = np.mean([f.get('roe', 0) for f in financials if f.get('roe')])
                
                # 最新财务指标
                latest = financials[0]
                roa = latest.get('roa', 0)
                gross_margin = latest.get('gross_margin', 0)
                net_margin = latest.get('net_margin', 0)
                debt_ratio = latest.get('debt_ratio', 0)
                
                results.append({
                    'code': code,
                    'roe_avg': roe_avg,
                    'roa': roa,
                    'gross_margin': gross_margin,
                    'net_margin': net_margin,
                    'debt_ratio': debt_ratio,
                })
            except Exception as e:
                logger.warning(f"计算 {code} 质量因子失败: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def calculate_momentum_factors(self, codes: List[str], date: str) -> pd.DataFrame:
        """
        计算动量因子
        
        指标：
        - 近20日涨幅
        - 近60日涨幅
        - 相对强弱
        """
        logger.info(f"计算动量因子: {len(codes)} 只股票")
        
        results = []
        for code in codes:
            try:
                # 获取历史价格
                prices = self._get_price_history(code, date, days=60)
                if len(prices) < 20:
                    continue
                
                # 计算收益率
                current_price = prices[-1]
                price_20d = prices[-20] if len(prices) >= 20 else prices[0]
                price_60d = prices[0]
                
                return_20d = (current_price - price_20d) / price_20d if price_20d > 0 else 0
                return_60d = (current_price - price_60d) / price_60d if price_60d > 0 else 0
                
                results.append({
                    'code': code,
                    'return_20d': return_20d,
                    'return_60d': return_60d,
                })
            except Exception as e:
                logger.warning(f"计算 {code} 动量因子失败: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def calculate_volatility_factors(self, codes: List[str], date: str) -> pd.DataFrame:
        """
        计算波动因子
        
        指标：
        - 近20日波动率
        - 最大回撤
        """
        logger.info(f"计算波动因子: {len(codes)} 只股票")
        
        results = []
        for code in codes:
            try:
                # 获取历史价格
                prices = self._get_price_history(code, date, days=20)
                if len(prices) < 10:
                    continue
                
                # 计算波动率
                returns = np.diff(prices) / prices[:-1]
                volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
                
                # 计算最大回撤
                max_drawdown = self._calculate_max_drawdown(prices)
                
                results.append({
                    'code': code,
                    'volatility_20d': volatility,
                    'max_drawdown_20d': max_drawdown,
                })
            except Exception as e:
                logger.warning(f"计算 {code} 波动因子失败: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def _get_financial_data(self, code: str, date: str) -> Optional[Dict]:
        """获取财务数据"""
        try:
            from core.database import db
            result = db.fetch_one("""
                SELECT roe, roa, gross_margin, net_margin, debt_ratio,
                       eps, total_asset, net_asset, revenue, profit
                FROM stock_financial
                WHERE code = %s AND report_date <= %s
                ORDER BY report_date DESC
                LIMIT 1
            """, (code, date))
            return result
        except Exception as e:
            logger.warning(f"获取 {code} 财务数据失败: {e}")
            return None
    
    def _get_financial_data_history(self, code: str, date: str, years: int = 3) -> List[Dict]:
        """获取历史财务数据"""
        try:
            from core.database import db
            start_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=365*years)).strftime('%Y-%m-%d')
            results = db.fetch_all("""
                SELECT report_date, roe, roa, gross_margin, net_margin, debt_ratio
                FROM stock_financial
                WHERE code = %s AND report_date BETWEEN %s AND %s
                ORDER BY report_date DESC
            """, (code, start_date, date))
            return results
        except Exception as e:
            logger.warning(f"获取 {code} 历史财务数据失败: {e}")
            return []
    
    def _get_price_data(self, code: str, date: str) -> Optional[Dict]:
        """获取价格数据"""
        try:
            from core.database import db
            result = db.fetch_one("""
                SELECT close, volume, amount
                FROM stock_daily
                WHERE code = %s AND trade_date = %s
            """, (code, date))
            return result
        except Exception as e:
            logger.warning(f"获取 {code} 价格数据失败: {e}")
            return None
    
    def _get_price_history(self, code: str, date: str, days: int = 60) -> List[float]:
        """获取历史价格序列"""
        try:
            from core.database import db
            start_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=days*2)).strftime('%Y-%m-%d')
            results = db.fetch_all("""
                SELECT close
                FROM stock_daily
                WHERE code = %s AND trade_date BETWEEN %s AND %s
                ORDER BY trade_date ASC
            """, (code, start_date, date))
            return [r['close'] for r in results]
        except Exception as e:
            logger.warning(f"获取 {code} 历史价格失败: {e}")
            return []
    
    def _calculate_pe(self, financial: Dict, price_data: Dict) -> float:
        """计算市盈率"""
        eps = financial.get('eps', 0)
        price = price_data.get('close', 0)
        if eps and eps > 0:
            return price / eps
        return float('inf')
    
    def _calculate_pb(self, financial: Dict, price_data: Dict) -> float:
        """计算市净率"""
        net_asset = financial.get('net_asset', 0)
        total_asset = financial.get('total_asset', 0)
        price = price_data.get('close', 0)
        if net_asset and net_asset > 0:
            return price / net_asset
        return float('inf')
    
    def _calculate_dividend_yield(self, financial: Dict, price_data: Dict) -> float:
        """计算股息率（简化版）"""
        # 实际应该从分红数据计算
        return 0.02  # 默认2%
    
    def _calculate_max_drawdown(self, prices: List[float]) -> float:
        """计算最大回撤"""
        if not prices or len(prices) < 2:
            return 0
        peak = prices[0]
        max_dd = 0
        for price in prices:
            if price > peak:
                peak = price
            dd = (peak - price) / peak
            max_dd = max(max_dd, dd)
        return max_dd


class StockSelector:
    """多因子选股器
    
    基于价值、质量、动量、波动四个维度的多因子模型
    默认权重：价值30%、质量30%、动量20%、波动20%
    """
    
    DEFAULT_WEIGHTS = [
        FactorWeight(FactorType.VALUE, 0.30, {'pe_threshold': 30, 'pb_threshold': 3}),
        FactorWeight(FactorType.QUALITY, 0.30, {'roe_threshold': 0.15, 'debt_threshold': 0.60}),
        FactorWeight(FactorType.MOMENTUM, 0.20, {'momentum_period': 20}),
        FactorWeight(FactorType.VOLATILITY, 0.20, {'vol_threshold': 0.40}),
    ]
    
    def __init__(self, db_connection=None, weights: List[FactorWeight] = None):
        self.db = db_connection
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.factor_calc = FactorCalculator(db_connection)
        
        # 创建权重字典方便查询
        self.weight_dict = {w.factor_type: w for w in self.weights}
    
    def filter_universe(
        self,
        date: str,
        universe: StockUniverse = None
    ) -> List[str]:
        """
        筛选股票池
        
        流程：
        1. 剔除ST、停牌、上市不足1年
        2. 按市值筛选
        """
        universe = universe or StockUniverse()
        logger.info(f"筛选股票池: {date}")
        
        try:
            from core.database import db
            
            # 基础筛选
            query = """
                SELECT DISTINCT s.code, s.name, s.list_date, s.industry
                FROM stock_info s
                WHERE 1=1
            """
            params = []
            
            # 排除ST
            if universe.exclude_st:
                query += " AND s.name NOT LIKE '%%ST%%'"
            
            # 上市时间筛选
            min_list_date = (datetime.strptime(date, '%Y-%m-%d') - 
                           timedelta(days=universe.min_list_days)).strftime('%Y-%m-%d')
            query += " AND s.list_date <= %s"
            params.append(min_list_date)
            
            # 市场筛选
            if universe.markets:
                markets_str = ','.join([f"'{m}'" for m in universe.markets])
                query += f" AND s.market IN ({markets_str})"
            
            results = db.fetch_all(query, tuple(params))
            
            codes = [r['code'] for r in results]
            logger.info(f"股票池筛选完成: {len(codes)} 只")
            return codes
            
        except Exception as e:
            logger.error(f"筛选股票池失败: {e}")
            return []
    
    def calculate_all_factors(self, codes: List[str], date: str) -> pd.DataFrame:
        """计算所有因子"""
        logger.info(f"开始计算所有因子: {len(codes)} 只股票")
        
        # 并行计算各因子
        value_df = self.factor_calc.calculate_value_factors(codes, date)
        quality_df = self.factor_calc.calculate_quality_factors(codes, date)
        momentum_df = self.factor_calc.calculate_momentum_factors(codes, date)
        volatility_df = self.factor_calc.calculate_volatility_factors(codes, date)
        
        # 合并所有因子
        merged = value_df
        for df in [quality_df, momentum_df, volatility_df]:
            if not df.empty:
                merged = merged.merge(df, on='code', how='outer')
        
        logger.info(f"因子计算完成: {len(merged)} 只股票")
        return merged
    
    def score_stocks(self, factor_data: pd.DataFrame) -> pd.DataFrame:
        """
        股票评分
        
        对每个因子进行标准化打分，然后加权汇总
        """
        logger.info("开始股票评分")
        
        if factor_data.empty:
            return pd.DataFrame()
        
        df = factor_data.copy()
        
        # 价值因子打分（越低越好）
        if 'pe' in df.columns:
            df['pe_score'] = self._normalize_inverse(df['pe'])
        if 'pb' in df.columns:
            df['pb_score'] = self._normalize_inverse(df['pb'])
        if 'dividend_yield' in df.columns:
            df['dividend_score'] = self._normalize(df['dividend_yield'])
        
        # 质量因子打分（越高越好）
        if 'roe_avg' in df.columns:
            df['roe_score'] = self._normalize(df['roe_avg'])
        if 'gross_margin' in df.columns:
            df['margin_score'] = self._normalize(df['gross_margin'])
        if 'debt_ratio' in df.columns:
            df['debt_score'] = self._normalize_inverse(df['debt_ratio'])
        
        # 动量因子打分（越高越好）
        if 'return_20d' in df.columns:
            df['momentum_score'] = self._normalize(df['return_20d'])
        
        # 波动因子打分（越低越好）
        if 'volatility_20d' in df.columns:
            df['volatility_score'] = self._normalize_inverse(df['volatility_20d'])
        
        # 计算各维度得分
        score_cols = []
        
        # 价值得分
        value_cols = [c for c in ['pe_score', 'pb_score', 'dividend_score'] if c in df.columns]
        if value_cols:
            df['value_score'] = df[value_cols].mean(axis=1)
            score_cols.append('value_score')
        
        # 质量得分
        quality_cols = [c for c in ['roe_score', 'margin_score', 'debt_score'] if c in df.columns]
        if quality_cols:
            df['quality_score'] = df[quality_cols].mean(axis=1)
            score_cols.append('quality_score')
        
        # 动量得分
        if 'momentum_score' in df.columns:
            df['momentum_score_final'] = df['momentum_score']
            score_cols.append('momentum_score_final')
        
        # 波动得分
        if 'volatility_score' in df.columns:
            df['volatility_score_final'] = df['volatility_score']
            score_cols.append('volatility_score_final')
        
        # 计算加权总分
        weights = {
            'value_score': 0.30,
            'quality_score': 0.30,
            'momentum_score_final': 0.20,
            'volatility_score_final': 0.20,
        }
        
        total_weight = sum(weights.get(c, 0) for c in score_cols)
        if total_weight > 0:
            df['total_score'] = sum(df.get(c, 0) * weights.get(c, 0) for c in score_cols) / total_weight
        else:
            df['total_score'] = 0
        
        # 排序
        df = df.sort_values('total_score', ascending=False).reset_index(drop=True)
        df['rank'] = range(1, len(df) + 1)
        
        logger.info(f"股票评分完成")
        return df
    
    def select(
        self,
        date: str,
        top_n: int = 20,
        universe: StockUniverse = None
    ) -> List[StockScore]:
        """
        执行选股
        
        流程：
        1. 筛选股票池
        2. 计算所有因子
        3. 评分排序
        4. 返回前N只
        """
        logger.info(f"开始选股: {date}, 目标数量: {top_n}")
        
        # 1. 筛选股票池
        codes = self.filter_universe(date, universe)
        if not codes:
            logger.warning("股票池为空")
            return []
        
        # 2. 计算因子
        factor_data = self.calculate_all_factors(codes, date)
        if factor_data.empty:
            logger.warning("因子数据为空")
            return []
        
        # 3. 评分
        scored = self.score_stocks(factor_data)
        if scored.empty:
            logger.warning("评分结果为空")
            return []
        
        # 4. 取前N只
        top_stocks = scored.head(top_n)
        
        # 5. 转换为 StockScore 对象
        results = []
        for _, row in top_stocks.iterrows():
            factor_scores = {
                FactorType.VALUE: row.get('value_score', 0),
                FactorType.QUALITY: row.get('quality_score', 0),
                FactorType.MOMENTUM: row.get('momentum_score_final', 0),
                FactorType.VOLATILITY: row.get('volatility_score_final', 0),
            }
            
            stock_score = StockScore(
                code=row['code'],
                name=row.get('name', ''),
                industry=row.get('industry', ''),
                total_score=row['total_score'],
                factor_scores=factor_scores,
                rank=int(row['rank']),
                metrics=row.to_dict()
            )
            results.append(stock_score)
        
        logger.info(f"选股完成: 选出 {len(results)} 只股票")
        return results
    
    def _normalize(self, series: pd.Series) -> pd.Series:
        """标准化（Z-score）"""
        if series.std() == 0:
            return pd.Series(0.5, index=series.index)
        return (series - series.mean()) / series.std()
    
    def _normalize_inverse(self, series: pd.Series) -> pd.Series:
        """反向标准化（值越小越好）"""
        return 1 - self._normalize(series)


# 便捷函数
def select_stocks(date: str = None, top_n: int = 20) -> List[StockScore]:
    """便捷选股函数"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    selector = StockSelector()
    return selector.select(date, top_n)


if __name__ == "__main__":
    # 测试
    results = select_stocks(top_n=10)
    for stock in results:
        print(f"{stock.rank}. {stock.code} {stock.name}")
        print(f"   总分: {stock.total_score:.2f}")
        print(f"   价值: {stock.factor_scores[FactorType.VALUE]:.2f}")
        print(f"   质量: {stock.factor_scores[FactorType.QUALITY]:.2f}")
        print(f"   动量: {stock.factor_scores[FactorType.MOMENTUM]:.2f}")
        print(f"   波动: {stock.factor_scores[FactorType.VOLATILITY]:.2f}")
        print()
