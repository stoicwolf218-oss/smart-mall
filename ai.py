# -*- coding: utf-8 -*-
"""智能推荐 / 销量预测 / 灰度发布

对应原 C 版的 predict_sales / ai_recommend / in_gray / set_gray_percent。
用简单的统计规则代替“真·机器学习”，代码短、可解释、可复现。
"""
from collections import Counter
from datetime import datetime
from typing import List

from models import Product, Order, User


def in_gray(user_id: int, gray_percent: int = 10) -> bool:
    """灰度判定：user_id % 100 < gray_percent（与原 C 版一致，默认 10%）。"""
    return (user_id % 100) < gray_percent


def predict_sales(orders: List[Order], days: int = 7) -> dict:
    """销量预测：按最近 N 天平均日销量 × 未来 7 天线性外推。

    返回：
      {"avg_daily": float, "prediction": float, "days": int, "note": str}
    """
    if not orders:
        return {"avg_daily": 0.0, "prediction": 0.0, "days": days,
                "note": "暂无历史订单，无法预测。"}
    # 订单时间格式：YYYY-MM-DD HH:MM:SS，取日期部分
    dates = [o.order_date[:10] for o in orders]
    today = datetime.now().strftime("%Y-%m-%d")
    recent = [d for d in dates if d >= _days_ago(days)]
    span = max(len(set(dates)), 1)
    avg_daily = len(orders) / span
    prediction = round(avg_daily * days, 1)
    note = f"基于 {len(orders)} 笔历史订单，平均日销量约 {avg_daily:.1f} 单"
    return {"avg_daily": round(avg_daily, 2), "prediction": prediction,
            "days": days, "note": note}


def ai_recommend(user: User, products: List[Product], orders: List[Order]) -> List[Product]:
    """个性化推荐：
    1) 优先推荐“用户历史购买过相同分类、且在售、未过期、有库存”的商品；
    2) 不足则用“最热销商品”补齐。
    """
    # 用户历史购买过的分类
    my_orders = [o for o in orders if o.buyer_id == user.id]
    fav_categories = Counter(o.product_name for o in my_orders)  # 历史商品名作为兴趣
    on_sale = [p for p in products if p.is_on_sale and not p.is_expired and p.quantity > 0]

    def score(p: Product):
        s = 0
        if p.name in fav_categories:
            s += 100
        # 热销度：历史买过该商品的次数越多，权重越高
        s += fav_categories.get(p.name, 0) * 10
        return s

    ranked = sorted(on_sale, key=score, reverse=True)
    return ranked[:5]


def _days_ago(n: int) -> str:
    from datetime import timedelta
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")
