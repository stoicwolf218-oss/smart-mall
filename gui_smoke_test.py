# -*- coding: utf-8 -*-
"""GUI 构建冒烟测试：验证 tkinter 可用，且各窗口能正常构建。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import tkinter
    print("tkinter TkVersion:", tkinter.TkVersion)
except Exception as e:
    print("tkinter 不可用:", e)
    sys.exit(1)

import gui
from gui import PaymentDialog

app = gui.App()
app.update_idletasks()
print("登录界面 OK")

# 买家界面
u = app.mall.find_user_by_name("user1")
app.show_buyer(u)
app.update_idletasks()
print("买家界面 OK")

# 管理员界面
app.show_admin()
app.update_idletasks()
print("管理员界面 OK")

# 支付弹窗
prod = app.mall.find_product(101)
dlg = PaymentDialog(app, prod, 2, 9.0, 0.0, 9.0)
dlg.update_idletasks()
dlg.destroy()
print("支付弹窗 OK")

app.destroy()
print("GUI SMOKE TEST PASSED ✅")
