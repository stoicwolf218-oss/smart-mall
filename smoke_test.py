# -*- coding: utf-8 -*-
"""无界面冒烟测试：验证商城核心逻辑 + 支付网关。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mall import Mall
from payment import PayMethod
import tempfile

# 用临时目录，避免污染真实 data/
tmp = tempfile.mkdtemp(prefix="smoke_mall_")
from storage import Storage
mall = Mall(Storage(data_dir=tmp))

print("== 初始数据 ==")
print("商品数:", len(mall.list_products()), "用户数:", len(mall.users))

print("\n== 注册 ==")
ok, msg, u = mall.register("alice", "pw", "爱丽丝")
print(ok, msg, "-> 优惠券", u.coupon if u else None)

print("\n== 登录 ==")
kind, u2, msg = mall.login("alice", "pw")
print(kind, u2.username, msg)

print("\n== 充值 ==")
print(mall.recharge(u2.id, 200))

print("\n== 余额支付购买 ==")
res = mall.buy(u2.id, 101, 3, use_coupon=True, method=PayMethod.BALANCE)
print(res)

print("\n== 支付宝购买（不扣余额） ==")
res2 = mall.buy(u2.id, 102, 2, use_coupon=True, method=PayMethod.ALIPAY)
print(res2)

print("\n== 银行卡支付（卡号无效应失败） ==")
res3 = mall.buy(u2.id, 103, 1, use_coupon=False, method=PayMethod.BANK, card_no="123")
print(res3)

print("\n== 银行卡支付（有效卡号应成功） ==")
res4 = mall.buy(u2.id, 103, 1, use_coupon=False, method=PayMethod.BANK, card_no="6222021234567890")
print(res4)

print("\n== 余额不足应失败 ==")
mall.recharge(u2.id, 0)  # no-op
u2.balance = 0
mall._save_users()
res5 = mall.buy(u2.id, 101, 1, use_coupon=False, method=PayMethod.BALANCE)
print(res5)

print("\n== 订单 ==")
for o in mall.user_orders(u2.id):
    print(o.order_id, o.product_name, o.total, o.payment_method)

print("\n== 支付流水 ==")
for t in mall.list_payments():
    print(t.transaction_id, t.amount, t.method, t.status)

print("\n== 销量预测 ==")
print(mall.predict_sales())

print("\n== AI 推荐 ==")
for p in mall.recommend(u2.id):
    print(p.id, p.name)

print("\n== 灰度 ==")
print("user id 2 是否灰度:", mall.in_gray(2))

print("\n== 过期检测 ==")
print("过期商品数:", mall.check_expired())

print("\n== 备份/恢复 ==")
print(mall.backup())
print(mall.restore())

print("\nSMOKE TEST PASSED ✅")
