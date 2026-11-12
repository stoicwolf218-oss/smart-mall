# -*- coding: utf-8 -*-
"""无界面冒烟测试：验证 v3 商城核心逻辑 + 支付网关。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage import Storage
from mall import Mall
from payment import PayMethod

mall = Mall(Storage(data_dir=tempfile.mkdtemp(prefix="smoke_v3_")))

print("== 初始 ==", "商品", len(mall.products), "用户", len(mall.users))

print("\n== 注册（应送 5 元券）==")
ok, msg, u = mall.register("alice", "pw", "爱丽丝")
print(ok, msg, "| 券:", u.coupon)

print("\n== 灰度默认 0（应 False）==")
print("in_gray(alice id):", mall.in_gray(u.id))

print("\n== 开启灰度 100%，新用户首次登录应送 3 元 ==")
mall.set_gray_percent(100)
kind, u2, msg = mall.login("alice", "pw")
print(msg, "| 券:", u2.coupon)
kind, u2, msg = mall.login("alice", "pw")   # 再次登录不应重复送
print("再次登录:", msg, "| 券:", u2.coupon, "（应仍为 8）")

print("\n== 充值 200 ==")
print(mall.recharge(u2.id, 200))

print("\n== 余额购买 3 件方便面(4.5*3=13.5)，用券 8 元 → 实付 5.5 ==")
res = mall.buy(u2.id, 101, 3, True, PayMethod.BALANCE)
print(res)

print("\n== 支付宝购买（不扣余额） ==")
print(mall.buy(u2.id, 102, 2, False, PayMethod.ALIPAY))

print("\n== 满 200 送 5 元券：充值到够，一次性买 200 元 ==")
mall.recharge(u2.id, 1000)
u2 = mall.find_user(u2.id)
before = u2.coupon
print("购买前券:", before, "| 累计消费:", u2.total_spent)
res = mall.buy(u2.id, 101, 45, False, PayMethod.BALANCE)  # 45*4.5=202.5
u2 = mall.find_user(u2.id)
print("购买 202.5 元后 → 券:", u2.coupon, "累计:", u2.total_spent, "VIP:", u2.is_vip)

print("\n== 满 500 升 VIP 送 20 ==")
res = mall.buy(u2.id, 103, 60, False, PayMethod.BALANCE)  # 60*5.5=330
u2 = mall.find_user(u2.id)
print("累计:", u2.total_spent, "VIP:", u2.is_vip, "券:", u2.coupon)

print("\n== 销量预测（最小二乘，商品 101） ==")
print(mall.predict_sales(101))

print("\n== AI 推荐 ==")
for r in mall.recommend(u2.id):
    print(r)

print("\n== 充值限额（应拒绝 -1 / 100000）==")
print(mall.recharge(u2.id, -1))
print(mall.recharge(u2.id, 100000))

print("\n== 管理员密码持久化 ==")
print(mall.change_admin_password("123456", "newpw"))
print("新密码登录:", mall.login("admin", "newpw")[0])

print("\nSMOKE TEST PASSED ✅")
