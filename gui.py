# -*- coding: utf-8 -*-
"""Tkinter 图形界面

入口逻辑：登录 -> 买家面板 / 管理员面板；支持注册、选购、优惠券、
支付网关弹窗、订单查询、管理员后台（商品管理 / 用户管理 / 预测 / 灰度 / 备份）。
"""
import tkinter as tk
from tkinter import ttk, messagebox

from mall import Mall
from payment import PayMethod
from cat import CatMood, mood_text


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.mall = Mall()
        self.title("智能商城系统 · 深度修复版")
        self.geometry("960x680")
        self.minsize(880, 600)
        self.current_user = None
        self.show_login()

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    # ---------- 登录 ----------
    def show_login(self):
        self._clear()
        self.current_user = None
        frm = ttk.Frame(self, padding=40)
        frm.pack(expand=True)

        ttk.Label(frm, text="智能商城系统", font=("Microsoft YaHei", 24, "bold")).pack(pady=(0, 4))
        ttk.Label(frm, text="请登录（管理员账号：admin / 123456）",
                  foreground="#666").pack(pady=(0, 20))

        ttk.Label(frm, text="用户名").pack(anchor="w")
        self._username = tk.StringVar()
        ttk.Entry(frm, textvariable=self._username, width=30).pack(pady=(2, 10))

        ttk.Label(frm, text="密码").pack(anchor="w")
        self._password = tk.StringVar()
        ttk.Entry(frm, textvariable=self._password, width=30, show="*").pack(pady=(2, 16))

        btn = ttk.Frame(frm)
        btn.pack()
        ttk.Button(btn, text="登录", width=12, command=self._do_login).pack(side="left", padx=6)
        ttk.Button(btn, text="注册", width=12, command=self.show_register).pack(side="left", padx=6)

        ttk.Label(frm, text="🐱 " + mood_text(CatMood.HAPPY), font=("Segoe UI Emoji", 12)).pack(pady=(24, 0))

    def _do_login(self):
        username = self._username.get().strip()
        password = self._password.get().strip()
        kind, user, msg = self.mall.login(username, password)
        if kind is None:
            messagebox.showerror("登录失败", msg)
            return
        if kind == "admin":
            self.show_admin(user)
        else:
            self.current_user = user
            self.show_buyer(user)

    # ---------- 注册 ----------
    def show_register(self):
        self._clear()
        frm = ttk.Frame(self, padding=40)
        frm.pack(expand=True)

        ttk.Label(frm, text="注册新用户", font=("Microsoft YaHei", 20, "bold")).pack(pady=(0, 16))
        ttk.Label(frm, text="用户名").pack(anchor="w")
        self._r_username = tk.StringVar()
        ttk.Entry(frm, textvariable=self._r_username, width=30).pack(pady=(2, 8))
        ttk.Label(frm, text="密码").pack(anchor="w")
        self._r_password = tk.StringVar()
        ttk.Entry(frm, textvariable=self._r_password, width=30, show="*").pack(pady=(2, 8))
        ttk.Label(frm, text="姓名").pack(anchor="w")
        self._r_name = tk.StringVar()
        ttk.Entry(frm, textvariable=self._r_name, width=30).pack(pady=(2, 16))

        btn = ttk.Frame(frm)
        btn.pack()
        ttk.Button(btn, text="提交注册", width=12, command=self._do_register).pack(side="left", padx=6)
        ttk.Button(btn, text="返回登录", width=12, command=self.show_login).pack(side="left", padx=6)

    def _do_register(self):
        ok, msg, user = self.mall.register(
            self._r_username.get().strip(), self._r_password.get().strip(),
            self._r_name.get().strip())
        if ok:
            messagebox.showinfo("注册成功", msg)
            self.show_login()
        else:
            messagebox.showerror("注册失败", msg)

    # ---------- 买家面板 ----------
    def show_buyer(self, user):
        self._clear()
        self.current_user = user
        top = ttk.Frame(self, padding=(16, 12))
        top.pack(fill="x")
        ttk.Label(top, text=f"👤 {user.name}（{user.username}）",
                  font=("Microsoft YaHei", 13, "bold")).pack(side="left")
        self._mood_var = tk.StringVar(value=mood_text(CatMood.HAPPY))
        ttk.Label(top, textvariable=self._mood_var,
                  font=("Segoe UI Emoji", 12)).pack(side="left", padx=20)
        ttk.Label(top, textvariable=self._buyer_balance_var(),
                  font=("Microsoft YaHei", 11)).pack(side="left")
        ttk.Button(top, text="退出登录", command=self.show_login).pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=8)
        nb.add(self._buyer_shop_tab(nb), text="🛒 选购商品")
        nb.add(self._buyer_orders_tab(nb), text="📦 我的订单")
        nb.add(self._buyer_me_tab(nb), text="👤 个人中心")

    def _buyer_balance_var(self):
        u = self.current_user
        v = tk.StringVar()
        v.set(f"余额 ¥{u.balance:.2f}  优惠券 ¥{u.coupon:.2f}"
              f"{'  [VIP]' if u.is_vip else ''}")
        return v

    def _buyer_shop_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        bar = ttk.Frame(tab)
        bar.pack(fill="x")
        ttk.Label(bar, text="搜索：").pack(side="left")
        self._shop_kw = tk.StringVar()
        ttk.Entry(bar, textvariable=self._shop_kw, width=24).pack(side="left", padx=4)
        ttk.Button(bar, text="搜索", command=self._shop_refresh).pack(side="left", padx=4)
        ttk.Button(bar, text="显示全部", command=lambda: (self._shop_kw.set(""), self._shop_refresh())).pack(side="left")

        cols = ("id", "名称", "分类", "价格", "库存", "保质期至", "状态")
        tree = ttk.Treeview(tab, columns=cols, show="headings", height=12)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=100, anchor="center")
        tree.column("名称", width=180, anchor="w")
        tree.pack(fill="both", expand=True, pady=8)
        self._shop_tree = tree

        buy = ttk.Frame(tab)
        buy.pack(fill="x")
        ttk.Label(buy, text="购买数量：").pack(side="left")
        self._buy_qty = tk.IntVar(value=1)
        ttk.Spinbox(buy, from_=1, to=999, textvariable=self._buy_qty, width=6).pack(side="left", padx=4)
        self._buy_coupon = tk.BooleanVar(value=True)
        ttk.Checkbutton(buy, text="使用优惠券", variable=self._buy_coupon).pack(side="left", padx=10)
        ttk.Button(buy, text="🛍 购买", command=self._do_buy).pack(side="left", padx=10)
        ttk.Label(buy, text="（购买时选择支付方式：余额 / 支付宝 / 微信 / 银行卡）",
                  foreground="#888").pack(side="left", padx=6)

        self._shop_refresh()
        return tab

    def _shop_refresh(self):
        tree = self._shop_tree
        tree.delete(*tree.get_children())
        kw = self._shop_kw.get().strip()
        items = self.mall.search_name(kw) if kw else self.mall.list_products()
        for p in items:
            if p.is_expired:
                status = "已过期"
            elif not p.is_on_sale:
                status = "已下架"
            elif p.quantity <= 0:
                status = "缺货"
            else:
                status = "在售"
            tree.insert("", "end", iid=str(p.id), values=(
                p.id, p.name, p.category, f"¥{p.price:.2f}", p.quantity,
                p.expired_date, status))

    def _do_buy(self):
        sel = self._shop_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一件商品。")
            return
        pid = int(sel[0])
        product = self.mall.find_product(pid)
        if not product:
            return
        qty = self._buy_qty.get()
        use_coupon = self._buy_coupon.get()

        total = round(product.price * qty, 2)
        discount = min(self.current_user.coupon, total) if use_coupon else 0.0
        final = round(total - discount, 2)

        dlg = PaymentDialog(self, product, qty, total, discount, final)
        self.wait_window(dlg)
        if not dlg.result:
            return
        method = dlg.method
        card_no = dlg.card_no

        res = self.mall.buy(self.current_user.id, pid, qty, use_coupon, method, card_no)
        if res["ok"]:
            self._refresh_buyer_ui()
            self._mood_var.set(mood_text(CatMood.HAPPY, "支付成功，喵~"))
            messagebox.showinfo("购买成功",
                f"{res['message']}\n订单号：{res['order_id']}\n交易号：{res['txn_id']}\n"
                f"实付：¥{res['final']:.2f}")
        else:
            self._mood_var.set(mood_text(CatMood.SAD, "支付失败喵..."))
            messagebox.showerror("购买失败", res["message"])

    def _buyer_orders_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        cols = ("订单号", "商品", "单价", "数量", "实付", "支付方式", "下单时间")
        tree = ttk.Treeview(tab, columns=cols, show="headings", height=15)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=110, anchor="center")
        tree.column("商品", width=180, anchor="w")
        tree.pack(fill="both", expand=True)
        self._orders_tree = tree
        ttk.Button(tab, text="🔄 刷新", command=self._orders_refresh).pack(pady=6)
        self._orders_refresh()
        return tab

    def _orders_refresh(self):
        tree = self._orders_tree
        tree.delete(*tree.get_children())
        for o in self.mall.user_orders(self.current_user.id):
            tree.insert("", "end", values=(
                o.order_id, o.product_name, f"¥{o.price:.2f}", o.quantity,
                f"¥{o.total:.2f}", o.payment_method, o.order_date))

    def _buyer_me_tab(self, nb):
        tab = ttk.Frame(nb, padding=24)
        self._me_label = ttk.Label(tab, font=("Microsoft YaHei", 12))
        self._me_label.pack(anchor="w", pady=8)

        row = ttk.Frame(tab)
        row.pack(anchor="w", pady=6)
        ttk.Label(row, text="充值金额：").pack(side="left")
        self._recharge_amt = tk.DoubleVar(value=100.0)
        ttk.Spinbox(row, from_=1, to=99999, textvariable=self._recharge_amt,
                    width=10).pack(side="left", padx=4)
        ttk.Button(row, text="充值", command=self._do_recharge).pack(side="left", padx=8)

        row2 = ttk.Frame(tab)
        row2.pack(anchor="w", pady=6)
        ttk.Label(row2, text="原密码：").pack(side="left")
        self._old_pw = tk.StringVar()
        ttk.Entry(row2, textvariable=self._old_pw, width=14, show="*").pack(side="left", padx=4)
        ttk.Label(row2, text="新密码：").pack(side="left")
        self._new_pw = tk.StringVar()
        ttk.Entry(row2, textvariable=self._new_pw, width=14, show="*").pack(side="left", padx=4)
        ttk.Button(row2, text="修改密码", command=self._do_change_pw).pack(side="left", padx=8)

        ttk.Label(tab, text="💡 AI 推荐（根据你的购买历史）",
                  font=("Microsoft YaHei", 11, "bold")).pack(anchor="w", pady=(16, 4))
        self._rec_tree = ttk.Treeview(tab, columns=("id", "名称", "分类", "价格"),
                                      show="headings", height=5)
        for c in ("id", "名称", "分类", "价格"):
            self._rec_tree.heading(c, text=c)
            self._rec_tree.column(c, width=120, anchor="center")
        self._rec_tree.column("名称", width=200, anchor="w")
        self._rec_tree.pack(fill="x", pady=4)
        self._me_refresh()
        return tab

    def _me_refresh(self):
        u = self.mall.find_user(self.current_user.id)
        self.current_user = u
        self._me_label.config(text=(
            f"姓名：{u.name}\n用户名：{u.username}\n"
            f"余额：¥{u.balance:.2f}\n优惠券：¥{u.coupon:.2f}\n"
            f"累计消费：¥{u.total_spent:.2f}   订单数：{u.order_count}\n"
            f"VIP：{'是' if u.is_vip else '否'}   注册时间：{u.register_date}"))
        self._rec_tree.delete(*self._rec_tree.get_children())
        for p in self.mall.recommend(u.id):
            self._rec_tree.insert("", "end", values=(p.id, p.name, p.category, f"¥{p.price:.2f}"))

    def _do_recharge(self):
        amt = self._recharge_amt.get()
        ok, msg = self.mall.recharge(self.current_user.id, amt)
        (messagebox.showinfo if ok else messagebox.showerror)("充值", msg)
        self._refresh_buyer_ui()

    def _do_change_pw(self):
        ok, msg = self.mall.change_password(self.current_user.id,
                                            self._old_pw.get(), self._new_pw.get())
        (messagebox.showinfo if ok else messagebox.showerror)("修改密码", msg)

    def _refresh_buyer_ui(self):
        # 直接重建买家界面，以同步余额 / 优惠券 / 订单
        self.show_buyer(self.current_user)

    # ---------- 管理员面板 ----------
    def show_admin(self, admin_user=None):
        self._clear()
        top = ttk.Frame(self, padding=(16, 12))
        top.pack(fill="x")
        ttk.Label(top, text="🛠 管理员后台",
                  font=("Microsoft YaHei", 14, "bold")).pack(side="left")
        ttk.Button(top, text="退出", command=self.show_login).pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=8)
        nb.add(self._admin_products_tab(nb), text="📦 商品管理")
        nb.add(self._admin_users_tab(nb), text="👥 用户管理")
        nb.add(self._admin_data_tab(nb), text="📊 数据 / 支付 / 系统")

    def _admin_products_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        cols = ("ID", "名称", "分类", "价格", "库存", "保质期至", "状态")
        tree = ttk.Treeview(tab, columns=cols, show="headings", height=10)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=110, anchor="center")
        tree.column("名称", width=170, anchor="w")
        tree.pack(fill="both", expand=True, pady=6)
        self._adm_tree = tree

        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=4)
        ttk.Button(bar, text="➕ 新增商品", command=self._adm_add_product).pack(side="left", padx=4)
        ttk.Button(bar, text="✏️ 修改选中", command=self._adm_modify_product).pack(side="left", padx=4)
        ttk.Button(bar, text="🗑 删除选中", command=self._adm_delete_product).pack(side="left", padx=4)
        ttk.Button(bar, text="⏰ 检测过期", command=self._adm_check_expired).pack(side="left", padx=4)
        ttk.Button(bar, text="🧹 清空零库存", command=self._adm_clear_zero).pack(side="left", padx=4)
        ttk.Button(bar, text="🧹 清空过期", command=self._adm_clear_expired).pack(side="left", padx=4)
        ttk.Button(bar, text="🔄 刷新", command=self._adm_products_refresh).pack(side="left", padx=4)
        self._adm_products_refresh()
        return tab

    def _adm_products_refresh(self):
        tree = self._adm_tree
        tree.delete(*tree.get_children())
        for p in self.mall.list_products():
            status = "已过期" if p.is_expired else ("已下架" if not p.is_on_sale else
                    ("缺货" if p.quantity <= 0 else "在售"))
            tree.insert("", "end", iid=str(p.id), values=(
                p.id, p.name, p.category, f"¥{p.price:.2f}", p.quantity,
                p.expired_date, status))

    def _adm_add_product(self):
        self._product_edit_dialog(new=True)

    def _adm_modify_product(self):
        sel = self._adm_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一件商品。")
            return
        self._product_edit_dialog(new=False, pid=int(sel[0]))

    def _adm_delete_product(self):
        sel = self._adm_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一件商品。")
            return
        pid = int(sel[0])
        if messagebox.askyesno("确认", f"确定删除商品 ID {pid} 吗？"):
            ok, msg = self.mall.delete_product(pid)
            (messagebox.showinfo if ok else messagebox.showerror)("删除商品", msg)
            self._adm_products_refresh()

    def _adm_check_expired(self):
        n = self.mall.check_expired()
        messagebox.showinfo("检测过期", f"共检测到 {n} 件过期商品。")
        self._adm_products_refresh()

    def _adm_clear_zero(self):
        n = self.mall.clear_zero_stock()
        messagebox.showinfo("清空零库存", f"已删除 {n} 件零库存商品。")
        self._adm_products_refresh()

    def _adm_clear_expired(self):
        n = self.mall.clear_all_expired()
        messagebox.showinfo("清空过期", f"已删除 {n} 件过期商品。")
        self._adm_products_refresh()

    def _product_edit_dialog(self, new, pid=None):
        dlg = tk.Toplevel(self)
        dlg.title("新增商品" if new else f"修改商品 {pid}")
        dlg.geometry("420x480")
        frm = ttk.Frame(dlg, padding=16)
        frm.pack(fill="both", expand=True)

        p = self.mall.find_product(pid) if not new else None
        fields = {}
        labels = [
            ("id", "商品 ID", "1001" if new else str(p.id)),
            ("category", "分类", p.category if p else ""),
            ("name", "名称", p.name if p else ""),
            ("price", "价格", str(p.price) if p else ""),
            ("year", "生产年", str(p.year) if p else str(2026)),
            ("month", "生产月", str(p.month) if p else str(1)),
            ("day", "生产日", str(p.day) if p else str(1)),
            ("shelf_life", "保质期(天)", str(p.shelf_life) if p else ""),
            ("quantity", "库存", str(p.quantity) if p else ""),
        ]
        for key, label, default in labels:
            ttk.Label(frm, text=label).pack(anchor="w")
            var = tk.StringVar(value=default)
            ttk.Entry(frm, textvariable=var).pack(fill="x", pady=(2, 8))
            fields[key] = var
        if not new:
            fields["id"].config(state="disabled")

        def submit():
            try:
                pid_val = int(fields["id"].get())
                price = float(fields["price"].get())
                year = int(fields["year"].get())
                month = int(fields["month"].get())
                day = int(fields["day"].get())
                shelf_life = int(fields["shelf_life"].get())
                qty = int(fields["quantity"].get())
            except ValueError:
                messagebox.showerror("输入错误", "请检查数字字段是否填写正确。", parent=dlg)
                return
            if new:
                ok, msg = self.mall.add_product(
                    pid_val, fields["category"].get(), fields["name"].get(), price,
                    year, month, day, shelf_life, qty)
            else:
                ok, msg = self.mall.modify_product(
                    pid, category=fields["category"].get(), name=fields["name"].get(),
                    price=price, quantity=qty, shelf_life=shelf_life)
            (messagebox.showinfo if ok else messagebox.showerror)("商品", msg, parent=dlg)
            if ok:
                dlg.destroy()
                self._adm_products_refresh()

        ttk.Button(frm, text="保存", command=submit).pack(pady=10)

    def _admin_users_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)
        cols = ("ID", "用户名", "姓名", "余额", "优惠券", "累计消费", "订单数", "VIP")
        tree = ttk.Treeview(tab, columns=cols, show="headings", height=12)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=90, anchor="center")
        tree.column("用户名", width=110, anchor="w")
        tree.pack(fill="both", expand=True, pady=6)
        self._adm_users_tree = tree

        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=4)
        ttk.Button(bar, text="💵 为选中用户充值", command=self._adm_recharge_user).pack(side="left", padx=4)
        ttk.Button(bar, text="🎫 发放优惠券", command=self._adm_add_coupon).pack(side="left", padx=4)
        ttk.Button(bar, text="🗑 删除用户", command=self._adm_delete_user).pack(side="left", padx=4)
        ttk.Button(bar, text="🔄 刷新", command=self._adm_users_refresh).pack(side="left", padx=4)
        self._adm_users_refresh()
        return tab

    def _adm_users_refresh(self):
        tree = self._adm_users_tree
        tree.delete(*tree.get_children())
        for u in self.mall.users:
            tree.insert("", "end", iid=str(u.id), values=(
                u.id, u.username, u.name, f"¥{u.balance:.2f}", f"¥{u.coupon:.2f}",
                f"¥{u.total_spent:.2f}", u.order_count, "是" if u.is_vip else "否"))

    def _selected_user_id(self, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一名用户。")
            return None
        return int(sel[0])

    def _adm_recharge_user(self):
        uid = self._selected_user_id(self._adm_users_tree)
        if not uid:
            return
        amt = self._ask_number("充值金额")
        if amt is None:
            return
        ok, msg = self.mall.recharge(uid, amt)
        (messagebox.showinfo if ok else messagebox.showerror)("充值", msg)
        self._adm_users_refresh()

    def _adm_add_coupon(self):
        uid = self._selected_user_id(self._adm_users_tree)
        if not uid:
            return
        amt = self._ask_number("优惠券金额")
        if amt is None:
            return
        ok, msg = self.mall.add_coupon(uid, amt)
        (messagebox.showinfo if ok else messagebox.showerror)("优惠券", msg)
        self._adm_users_refresh()

    def _adm_delete_user(self):
        uid = self._selected_user_id(self._adm_users_tree)
        if not uid:
            return
        if messagebox.askyesno("确认", f"确定删除用户 ID {uid} 吗？"):
            ok, msg = self.mall.delete_user(uid)
            (messagebox.showinfo if ok else messagebox.showerror)("删除用户", msg)
            self._adm_users_refresh()

    def _ask_number(self, title):
        dlg = tk.Toplevel(self)
        dlg.title(title)
        frm = ttk.Frame(dlg, padding=16)
        frm.pack()
        ttk.Label(frm, text=title + "：").pack(side="left")
        var = tk.DoubleVar()
        ttk.Entry(frm, textvariable=var, width=12).pack(side="left", padx=6)
        result = {}
        ttk.Button(frm, text="确定",
                   command=lambda: (result.setdefault("v", var.get()), dlg.destroy())).pack(side="left")
        self.wait_window(dlg)
        return result.get("v")

    def _admin_data_tab(self, nb):
        tab = ttk.Frame(nb, padding=10)

        left = ttk.Frame(tab)
        left.pack(side="left", fill="both", expand=True)
        ttk.Label(left, text="📈 销量预测", font=("Microsoft YaHei", 11, "bold")).pack(anchor="w")
        self._pred_label = ttk.Label(left, font=("Microsoft YaHei", 10))
        self._pred_label.pack(anchor="w", pady=4)
        ttk.Button(left, text="刷新预测", command=self._adm_predict).pack(anchor="w", pady=4)

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(left, text="🧪 灰度发布", font=("Microsoft YaHei", 11, "bold")).pack(anchor="w")
        gray = ttk.Frame(left)
        gray.pack(anchor="w", pady=4)
        ttk.Label(gray, text="灰度比例(%)：").pack(side="left")
        self._gray_var = tk.IntVar(value=self.mall.gray_percent)
        ttk.Spinbox(gray, from_=0, to=100, textvariable=self._gray_var, width=6).pack(side="left", padx=4)
        ttk.Button(gray, text="应用", command=self._adm_set_gray).pack(side="left", padx=6)

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(left, text="💾 数据备份 / 恢复", font=("Microsoft YaHei", 11, "bold")).pack(anchor="w")
        bf = ttk.Frame(left)
        bf.pack(anchor="w", pady=4)
        ttk.Button(bf, text="立即备份", command=self._adm_backup).pack(side="left", padx=4)
        ttk.Button(bf, text="恢复备份", command=self._adm_restore).pack(side="left", padx=4)

        right = ttk.Frame(tab)
        right.pack(side="right", fill="both", expand=True)
        ttk.Label(right, text="💳 支付流水（支付网关）",
                  font=("Microsoft YaHei", 11, "bold")).pack(anchor="w")
        cols = ("交易号", "订单号", "金额", "方式", "状态", "时间")
        tree = ttk.Treeview(right, columns=cols, show="headings", height=12)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor="center")
        tree.column("交易号", width=150)
        tree.pack(fill="both", expand=True, pady=6)
        self._pay_tree = tree
        ttk.Button(right, text="🔄 刷新流水", command=self._adm_payments_refresh).pack(pady=4)
        self._adm_payments_refresh()
        self._adm_predict()
        return tab

    def _adm_predict(self):
        r = self.mall.predict_sales()
        self._pred_label.config(text=(
            f"{r['note']}\n未来 {r['days']} 天预计销量：{r['prediction']} 单"))

    def _adm_set_gray(self):
        ok, msg = self.mall.set_gray_percent(self._gray_var.get())
        (messagebox.showinfo if ok else messagebox.showerror)("灰度发布", msg)

    def _adm_backup(self):
        messagebox.showinfo("备份", self.mall.backup())

    def _adm_restore(self):
        if messagebox.askyesno("确认", "确定从 latest_backup/ 恢复数据吗？当前数据将被覆盖。"):
            ok, msg = self.mall.restore()
            (messagebox.showinfo if ok else messagebox.showerror)("恢复", msg)
            self._adm_products_refresh()
            self._adm_users_refresh()
            self._adm_payments_refresh()

    def _adm_payments_refresh(self):
        tree = self._pay_tree
        tree.delete(*tree.get_children())
        for t in self.mall.list_payments():
            tree.insert("", "end", values=(
                t.transaction_id, t.order_id, f"¥{t.amount:.2f}", t.method,
                t.status, t.time))


class PaymentDialog(tk.Toplevel):
    """支付网关弹窗：选择支付方式，模拟网关扣款。"""

    def __init__(self, master, product, qty, total, discount, final):
        super().__init__(master)
        self.title("收银台 · 支付网关")
        self.geometry("400x420")
        self.resizable(False, False)
        self.result = False
        self.method = PayMethod.BALANCE
        self.card_no = ""

        frm = ttk.Frame(self, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="确认订单", font=("Microsoft YaHei", 13, "bold")).pack(anchor="w")
        ttk.Label(frm, text=(
            f"商品：{product.name}\n数量：{qty} 件\n"
            f"原价合计：¥{total:.2f}\n优惠券抵扣：-¥{discount:.2f}\n"
            f"应付金额：¥{final:.2f}"),
            font=("Microsoft YaHei", 11)).pack(anchor="w", pady=8)

        ttk.Separator(frm, orient="horizontal").pack(fill="x", pady=8)
        ttk.Label(frm, text="选择支付方式", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w")

        self._method_var = tk.StringVar(value=PayMethod.BALANCE.value)
        for m in PayMethod:
            ttk.Radiobutton(frm, text=m.value, value=m.value,
                            variable=self._method_var,
                            command=self._on_method_change).pack(anchor="w")

        self._card_frame = ttk.Frame(frm)
        ttk.Label(self._card_frame, text="银行卡号：").pack(side="left")
        self._card_var = tk.StringVar()
        ttk.Entry(self._card_frame, textvariable=self._card_var, width=22).pack(side="left", padx=4)

        self._hint = ttk.Label(frm, text="", foreground="#888")
        self._hint.pack(anchor="w", pady=6)

        ttk.Button(frm, text="💳 确认支付", command=self._confirm).pack(pady=12)
        self._on_method_change()

    def _on_method_change(self):
        m = self._method_var.get()
        if m == PayMethod.BANK.value:
            self._card_frame.pack(anchor="w", pady=4)
            self._hint.config(text="模拟网关：校验卡号长度后放行。")
        elif m == PayMethod.ALIPAY.value or m == PayMethod.WECHAT.value:
            self._card_frame.pack_forget()
            self._hint.config(text="模拟网关：已生成支付二维码（演示直接成功）。")
        else:
            self._card_frame.pack_forget()
            self._hint.config(text="使用账户余额支付，余额不足将失败。")

    def _confirm(self):
        m = self._method_var.get()
        for method in PayMethod:
            if method.value == m:
                self.method = method
                break
        self.card_no = self._card_var.get().strip()
        self.result = True
        self.destroy()
