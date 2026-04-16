"""投资账本 API 路由"""
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Path, Body
from loguru import logger

from core.ledger_service import get_ledger_service

router = APIRouter(prefix="/api/ledger", tags=["投资账本"])
ledger_service = get_ledger_service()


# ==================== 账户管理 ====================

@router.get("/accounts")
async def get_accounts():
    """获取所有交易账户列表"""
    try:
        accounts = ledger_service.get_accounts()
        return {
            "accounts": accounts,
            "count": len(accounts),
        }
    except Exception as e:
        logger.error(f"获取账户列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account/{account_id}")
async def get_account(account_id: int):
    """获取单个账户详情"""
    try:
        summary = ledger_service.get_account_summary(account_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取账户详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts")
async def create_account(
    account_name: str = Body(..., description="账户名称"),
    account_type: str = Body(..., description="账户类型"),
    initial_capital: float = Body(..., description="初始资金"),
    is_default: bool = Body(False, description="是否默认账户"),
):
    """创建新交易账户"""
    try:
        account = ledger_service.create_account(
            account_name=account_name,
            account_type=account_type,
            initial_capital=initial_capital,
            is_default=is_default,
        )
        return account
    except Exception as e:
        logger.error(f"创建账户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/accounts/{account_id}")
async def update_account(
    account_id: int,
    account_name: Optional[str] = Body(None, description="账户名称"),
    account_type: Optional[str] = Body(None, description="账户类型"),
    is_default: Optional[bool] = Body(None, description="是否默认账户"),
):
    """更新账户信息"""
    try:
        account = ledger_service.update_account(
            account_id=account_id,
            account_name=account_name,
            account_type=account_type,
            is_default=is_default,
        )
        return account
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新账户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int):
    """删除交易账户"""
    try:
        ledger_service.delete_account(account_id)
        return {"message": "账户删除成功"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除账户失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 持仓信息 ====================

@router.get("/positions")
async def get_positions(
    account_id: int = Query(..., description="账户ID"),
):
    """获取当前持仓列表（含实时行情）"""
    try:
        positions = ledger_service.get_positions_with_quotes(account_id)
        return {
            "positions": positions,
            "count": len(positions),
        }
    except Exception as e:
        logger.error(f"获取持仓列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/position/{stock_code}")
async def get_position_detail(
    account_id: int = Query(..., description="账户ID"),
    stock_code: str = Path(..., description="股票代码"),
):
    """获取单只股票持仓详情"""
    try:
        positions = ledger_service.get_positions_with_quotes(account_id)
        position = next((p for p in positions if p["stock_code"] == stock_code), None)
        
        if not position:
            raise HTTPException(status_code=404, detail=f"未找到 {stock_code} 的持仓")
        
        return position
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取持仓详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 交易记录 ====================

@router.get("/trades")
async def get_trade_history(
    account_id: int = Query(..., description="账户ID"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    stock_code: Optional[str] = Query(None, description="股票代码筛选"),
    trade_type: Optional[str] = Query(None, description="交易类型筛选 buy/sell"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
):
    """获取成交历史记录（支持分页和筛选）"""
    try:
        result = ledger_service.get_trade_history(
            account_id=account_id,
            limit=limit,
            offset=offset,
            stock_code=stock_code,
            trade_type=trade_type,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error(f"获取交易历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_order_history(
    account_id: int = Query(..., description="账户ID"),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="订单状态筛选"),
):
    """获取订单历史记录"""
    # TODO: 实现订单历史查询
    return {
        "orders": [],
        "total": 0,
        "message": "订单历史功能开发中",
    }


# ==================== 资产变化 ====================

@router.get("/assets/history")
async def get_asset_history(
    account_id: int = Query(..., description="账户ID"),
    days: int = Query(90, ge=1, le=365, description="天数"),
):
    """获取资产历史数据（用于净值曲线）"""
    try:
        history = ledger_service.get_asset_history(account_id, days)
        return {
            "history": history,
            "count": len(history),
        }
    except Exception as e:
        logger.error(f"获取资产历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 盈亏分析 ====================

@router.get("/pnl/summary")
async def get_pnl_summary(
    account_id: int = Query(..., description="账户ID"),
):
    """获取盈亏汇总统计"""
    try:
        stats = ledger_service.get_pnl_statistics(account_id)
        return stats
    except Exception as e:
        logger.error(f"获取盈亏统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pnl/daily")
async def get_daily_pnl(
    account_id: int = Query(..., description="账户ID"),
    days: int = Query(30, ge=1, le=365, description="天数"),
):
    """获取每日盈亏明细"""
    try:
        daily_pnl = ledger_service.get_daily_pnl(account_id, days)
        return {
            "daily_pnl": daily_pnl,
            "count": len(daily_pnl),
        }
    except Exception as e:
        logger.error(f"获取每日盈亏失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pnl/by-stock")
async def get_pnl_by_stock(
    account_id: int = Query(..., description="账户ID"),
):
    """按股票统计盈亏"""
    try:
        pnl_by_stock = ledger_service.get_pnl_by_stock(account_id)
        return {
            "pnl_by_stock": pnl_by_stock,
            "count": len(pnl_by_stock),
        }
    except Exception as e:
        logger.error(f"获取股票盈亏统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 资金流水 ====================

@router.get("/capital-flows")
async def get_capital_flows(
    account_id: int = Query(..., description="账户ID"),
    limit: int = Query(50, ge=1, le=500, description="返回数量"),
    flow_type: Optional[str] = Query(None, description="流水类型筛选"),
):
    """获取资金流水记录"""
    try:
        flows = ledger_service.get_capital_flows(
            account_id=account_id,
            limit=limit,
            flow_type=flow_type,
        )
        return {
            "flows": flows,
            "count": len(flows),
        }
    except Exception as e:
        logger.error(f"获取资金流水失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
