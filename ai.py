# -*- coding: utf-8 -*-
"""智能推荐 / 销量预测 / 灰度发布（对齐 shop_v3.c）

对应原 C 版 v3：
- predict_sales：按商品，最小二乘线性回归 y = a + b*x，输出历史分析 + 未来7天逐日 + 20%安全库存备货量
- ai_recommend：全自动推荐（新用户 → 全站热销 TOP3；老用户 → 偏好种类未买[偏好] + 热销补充[热销]）
- in_gray：user_id % 100 < gray_percent
"""
from typing import List

from models import Product, Order


def in_gray(user_id: int, gray_percent: int = 0) -> bool:
    """灰度判定：user_id % 100 < gray_percent（v3 默认 0 = 关闭）。"""
    return (user_id % 100) < gray_percent


def predict_sales(orders: List[Order], product_id: int, days: int = 7) -> dict:
    """销量预测（最小二乘线性回归）。

    以订单流全局序号为时间轴 x，该商品销量为 y，拟合 y = a + b*x，
    外推未来 `days` 天，并按 1.2 倍给出安全库存备货量。
    """
    if not orders:
        return {"ok": False, "message": "暂无订单数据，无法预测。"}

    # 按订单追加顺序生成全局序号，仅统计该商品的销量点
    points = []          # (x=全局序号, y=销量)
    order_seq = 0
    for o in orders:
        order_seq += 1
        if o.product_id == product_id:
            points.append((order_seq, o.quantity))

    if not points:
        return {"ok": False, "product_id": product_id,
                "message": "该商品无销售记录，无法预测。"}

    n = len(points)
    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    sum_xy = sum(p[0] * p[1] for p in points)
    sum_xx = sum(p[0] * p[0] for p in points)

    denom = n * sum_xx - sum_x * sum_x
    b = (n * sum_xy - sum_x * sum_y) / denom if denom != 0 else 0.0
    a = (sum_y - b * sum_x) / n

    avg = sum_y / n
    total_sold = int(sum_y)
    trend = "↑ 上升" if b > 0.5 else ("↓ 下降" if b < -0.5 else "→ 平稳")

    daily = []
    total_predict = 0.0
    for day in range(1, days + 1):
        x_next = order_seq + day
        pred = max(a + b * x_next, 0.0)
        daily.append({"day": day, "pred": round(pred, 1)})
        total_predict += pred

    return {
        "ok": True,
        "product_id": product_id,
        "n": n,
        "total_sold": total_sold,
        "avg": round(avg, 1),
        "trend": trend,
        "slope": round(b, 3),
        "intercept": round(a, 2),
        "daily": daily,
        "total_predict": round(total_predict, 1),
        "suggest_stock": round(total_predict * 1.2),
        "note": "历史订单少于 3 条，预测结果仅供参考。" if n < 3 else "",
    }


def ai_recommend(user_id: int, products: List[Product],
                 orders: List[Order]) -> List[dict]:
    """AI 智能推荐（全自动，无需输入）。

    返回 [{id, name, category, price, tag, sales}, ...]
    tag: "偏好"（同类未买）/ "热销"（热销未买）/ ""（在售兜底）
    """
    # 统计全局销量 + 该用户已购商品
    sales = {}          # product_id -> 总销量
    bought_ids = set()
    for o in orders:
        sales[o.product_id] = sales.get(o.product_id, 0) + o.quantity
        if o.buyer_id == user_id:
            bought_ids.add(o.product_id)

    by_id = {p.id: p for p in products}
    on_sale_ids = [p.id for p in products
                   if p.is_on_sale and not p.is_expired and p.quantity > 0]

    # 用户偏好种类（去重）
    bought_cats = []
    for pid in bought_ids:
        p = by_id.get(pid)
        if p and p.category not in bought_cats:
            bought_cats.append(p.category)

    # 销量从高到低排序
    ranked_pids = sorted(sales, key=lambda pid: sales[pid], reverse=True)

    def pick(pid):
        p = by_id.get(pid)
        return p if (p and pid in on_sale_ids) else None

    result = []

    if not bought_ids:
        # 新用户：全站热销 TOP3
        for pid in ranked_pids:
            p = pick(pid)
            if p and len(result) < 3:
                result.append(_rec(p, "热销", sales[pid]))
        if not result:
            # 无销售数据：展示在售商品兜底
            for pid in on_sale_ids:
                if len(result) >= 3:
                    break
                result.append(_rec(by_id[pid], "", 0))
    else:
        # 老用户：偏好同类未买（最多3） + 热销未买（补到5）
        for pid in ranked_pids:
            if pid in bought_ids or len(result) >= 3:
                continue
            p = pick(pid)
            if p and p.category in bought_cats:
                result.append(_rec(p, "偏好", sales[pid]))
        for pid in ranked_pids:
            if len(result) >= 5:
                break
            if pid in bought_ids:
                continue
            p = pick(pid)
            if p and p.category not in bought_cats:
                result.append(_rec(p, "热销", sales[pid]))

    return result


def _rec(p: Product, tag: str, sales: int) -> dict:
    return {
        "id": p.id, "name": p.name, "category": p.category,
        "price": p.price, "tag": tag, "sales": sales,
    }
