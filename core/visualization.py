"""可视化模块"""
import json
from typing import List, Optional

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_backtest_chart(
    nav_data: List[dict],
    benchmark_data: Optional[List[dict]] = None,
    trades: Optional[List[dict]] = None,
) -> str:
    """创建回测结果图表
    
    Args:
        nav_data: 净值数据列表
        benchmark_data: 基准数据列表
        trades: 交易记录列表
    
    Returns:
        Plotly图表JSON
    """
    # 创建子图
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=('净值曲线', '日收益率', '回撤'),
    )
    
    dates = [d['date'] for d in nav_data]
    nav_values = [d['nav'] for d in nav_data]
    
    # 1. 净值曲线
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=nav_values,
            mode='lines',
            name='策略净值',
            line=dict(color='#667eea', width=2),
        ),
        row=1, col=1
    )
    
    # 添加基准线
    if benchmark_data:
        bench_dates = [d['date'] for d in benchmark_data]
        bench_values = [d['nav'] for d in benchmark_data]
        fig.add_trace(
            go.Scatter(
                x=bench_dates,
                y=bench_values,
                mode='lines',
                name='基准净值',
                line=dict(color='#94a3b8', width=1.5, dash='dash'),
            ),
            row=1, col=1
        )
    
    # 添加买卖点标记
    if trades:
        buy_dates = []
        buy_prices = []
        sell_dates = []
        sell_prices = []
        
        for trade in trades:
            trade_date = trade.get('date')
            # 找到对应日期的净值
            for i, d in enumerate(nav_data):
                if d['date'] == trade_date:
                    if trade['type'] == 'buy':
                        buy_dates.append(trade_date)
                        buy_prices.append(nav_values[i])
                    else:
                        sell_dates.append(trade_date)
                        sell_prices.append(nav_values[i])
                    break
        
        if buy_dates:
            fig.add_trace(
                go.Scatter(
                    x=buy_dates,
                    y=buy_prices,
                    mode='markers',
                    name='买入',
                    marker=dict(color='green', size=10, symbol='triangle-up'),
                ),
                row=1, col=1
            )
        
        if sell_dates:
            fig.add_trace(
                go.Scatter(
                    x=sell_dates,
                    y=sell_prices,
                    mode='markers',
                    name='卖出',
                    marker=dict(color='red', size=10, symbol='triangle-down'),
                ),
                row=1, col=1
            )
    
    # 2. 日收益率
    daily_returns = [d.get('daily_return', 0) * 100 for d in nav_data]
    colors = ['green' if r >= 0 else 'red' for r in daily_returns]
    
    fig.add_trace(
        go.Bar(
            x=dates,
            y=daily_returns,
            name='日收益率',
            marker_color=colors,
            opacity=0.7,
        ),
        row=2, col=1
    )
    
    # 3. 回撤
    drawdowns = [d.get('drawdown', 0) * 100 for d in nav_data]
    
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=drawdowns,
            mode='lines',
            name='回撤',
            fill='tozeroy',
            line=dict(color='red', width=1),
            fillcolor='rgba(255, 0, 0, 0.2)',
        ),
        row=3, col=1
    )
    
    # 更新布局
    fig.update_layout(
        title='回测结果分析',
        showlegend=True,
        height=800,
        template='plotly_white',
        hovermode='x unified',
    )
    
    # 更新y轴标签
    fig.update_yaxes(title_text='净值', row=1, col=1)
    fig.update_yaxes(title_text='收益率(%)', row=2, col=1)
    fig.update_yaxes(title_text='回撤(%)', row=3, col=1)
    
    return fig.to_json()


def create_strategy_comparison_chart(
    strategy_results: List[dict],
) -> str:
    """创建策略对比图表
    
    Args:
        strategy_results: 多个策略的回测结果
    
    Returns:
        Plotly图表JSON
    """
    fig = go.Figure()
    
    metrics = ['total_return', 'annualized_return', 'max_drawdown', 'sharpe_ratio']
    metric_names = ['总收益率', '年化收益', '最大回撤', '夏普比率']
    
    for strategy in strategy_results:
        values = [
            strategy.get('total_return', 0) * 100,
            strategy.get('annualized_return', 0) * 100,
            strategy.get('max_drawdown', 0) * 100,
            strategy.get('sharpe_ratio', 0),
        ]
        
        fig.add_trace(go.Bar(
            name=strategy['strategy'],
            x=metric_names,
            y=values,
            text=[f'{v:.2f}' for v in values],
            textposition='auto',
        ))
    
    fig.update_layout(
        title='策略绩效对比',
        barmode='group',
        height=500,
        template='plotly_white',
        yaxis_title='数值',
    )
    
    return fig.to_json()


def create_risk_gauge_chart(
    current_value: float,
    threshold_value: float,
    title: str,
) -> str:
    """创建风险仪表盘
    
    Args:
        current_value: 当前值
        threshold_value: 阈值
        title: 标题
    
    Returns:
        Plotly图表JSON
    """
    # 计算百分比
    percentage = min(current_value / threshold_value * 100, 100) if threshold_value > 0 else 0
    
    # 确定颜色
    if percentage < 50:
        color = 'green'
    elif percentage < 80:
        color = 'yellow'
    else:
        color = 'red'
    
    fig = go.Figure(go.Indicator(
        mode='gauge+number+delta',
        value=current_value * 100,
        number={'suffix': '%'},
        title={'text': title},
        delta={'reference': threshold_value * 100, 'suffix': '%'},
        gauge={
            'axis': {'range': [0, max(threshold_value * 150, current_value * 100)]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, threshold_value * 50], 'color': 'lightgreen'},
                {'range': [threshold_value * 50, threshold_value * 80], 'color': 'yellow'},
                {'range': [threshold_value * 80, threshold_value * 100], 'color': 'orange'},
                {'range': [threshold_value * 100, threshold_value * 150], 'color': 'red'},
            ],
            'threshold': {
                'line': {'color': 'red', 'width': 4},
                'thickness': 0.75,
                'value': threshold_value * 100,
            },
        },
    ))
    
    fig.update_layout(
        height=300,
        template='plotly_white',
    )
    
    return fig.to_json()
