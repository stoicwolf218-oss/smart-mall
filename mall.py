# -*- coding: utf-8 -*-
"""商城核心业务层（对齐 shop_v3.c）

- 优惠券：注册送 5 元 / 实付满 200 送 5 元 / 升级 VIP(满 500) 送 20 元（按实付计算）
- 灰度发布：默认 0(关闭)，user_id%100 < 比例；灰度组内从未消费新用户首次登录送 3 元券
- 支付网关：余额 / 支付宝 / 微信 / 银行卡
- 充值限额 0.01~99999，购买数量 1~9999
- 销量预测：最小二乘线性回归（按商品）
"""
from datetime import date, datetime, timedelta
from typing import List, Optional

from models import Product, User, Order, PaymentRecord
from storage import Storage
from payment import PaymentGateway, PayMethod
import ai
import checkout


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


def _is_bad_money(x) -> bool:
    """校验金额：非有限 / <=0 / 超大 视为无效（对应 C 的 inf/nan 防护）。"""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return True
    return x != x or x <= 0 or x > 99999.0


class Mall:
    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or Storage()
        self.gateway = PaymentGateway()
        self.gray_percent = 0
        self.admin_password = self.storage.load_admin_password("123456")
        self.products: List[Product] = self.storage.load_products()
        self.users: List[User] = self.storage.load_users()
        self.orders: List[Order] = self.storage.load_orders()
        self._seed_if_empty()

    # ============ 内部工具 ============
    def _save_products(self):
        self.storage.save_products(self.products)

    def _save_users(self):
        self.storage.save_users(self.users)

    def _seed_if_empty(self):
        if self.users:
            return
        self.users = [
            User(1, "admin", "123456", "管理员", coupon=5.0, balance=100.0,
                 is_vip=True, register_date=_now()),
            User(2, "user1", "123456", "张三", coupon=5.0, balance=50.0,
                 register_date=_now()),
            User(3, "user2", "123456", "李四", coupon=5.0, balance=20.0,
                 register_date=_now()),
        ]
        self.products = [
            Product(101, "食品", "康师傅方便面", 4.5, 2026, 11, 12, 180,
                    expired_date="2027-05-11", is_on_sale=True, quantity=100),
            Product(102, "饮料", "可口可乐 330ml", 3.0, 2026, 11, 12, 365,
                    expired_date="2027-11-12", is_on_sale=True, quantity=200),
            Product(103, "日用品", "舒肤佳香皂", 5.5, 2026, 11, 12, 1080,
                    expired_date="2029-10-26", is_on_sale=True, quantity=80),
        ]
        self._save_products()
        self._save_users()

    # ============ 商品管理 ============
    def find_product(self, pid: int) -> Optional[Product]:
        for p in self.products:
            if p.id == pid:
                return p
        return None

    def _next_product_id(self) -> int:
        return max([p.id for p in self.products], default=100) + 1

    def add_product(self, category, name, price, year, month, day,
                    shelf_life, quantity, is_on_sale=True) -> tuple[bool, str]:
        """新增商品，ID 由系统自动分配。"""
        pid = self._next_product_id()
        exp = date(year, month, day) + timedelta(days=shelf_life)
        p = Product(pid, category, name, float(price), year, month, day,
                    shelf_life, expired_date=exp.strftime("%Y-%m-%d"),
                    is_expired=exp < date.today(), is_on_sale=bool(is_on_sale),
                    quantity=int(quantity))
        self.products.append(p)
        self._save_products()
        return True, f"已上架商品：{name}（ID {pid}）"

    def list_products(self, on_sale_only=False, in_stock_only=False) -> List[Product]:
        result = self.products
        if on_sale_only:
            result = [p for p in result if p.is_on_sale]
        if in_stock_only:
            result = [p for p in result if p.quantity > 0]
        return result

    def search_name(self, kw: str) -> List[Product]:
        kw = (kw or "").strip()
        if not kw:
            return list(self.products)
        return [p for p in self.products if kw in p.name]

    def modify_product(self, pid, category=None, name=None, price=None,
                       quantity=None, on_sale=None, shelf_life=None,
                       year=None, month=None, day=None) -> tuple[bool, str]:
        p = self.find_product(pid)
        if not p:
            return False, f"商品 ID {pid} 不存在。"
        if category:
            p.category = category
        if name:
            p.name = name
        if price is not None:
            p.price = float(price)
        if quantity is not None:
            p.quantity = int(quantity)
        if on_sale is not None:
            p.is_on_sale = bool(on_sale)
        if year is not None:
            p.year = int(year)
        if month is not None:
            p.month = int(month)
        if day is not None:
            p.day = int(day)
        if shelf_life is not None:
            p.shelf_life = int(shelf_life)
            p.expired_date = (date(p.year, p.month, p.day) +
                              timedelta(days=p.shelf_life)).strftime("%Y-%m-%d")
        # 库存为 0 自动下架
        if p.quantity == 0:
            p.is_on_sale = False
        self._save_products()
        return True, f"已修改商品：{p.name}"

    def delete_product(self, pid) -> tuple[bool, str]:
        p = self.find_product(pid)
        if not p:
            return False, f"商品 ID {pid} 不存在。"
        self.products.remove(p)
        self._save_products()
        return True, f"已删除商品：{p.name}"

    def check_expired(self) -> int:
        """批量检测过期：刷新 expired_date 与 is_expired。返回过期数量。"""
        today = date.today()
        cnt = 0
        for p in self.products:
            exp = date(p.year, p.month, p.day) + timedelta(days=p.shelf_life)
            p.expired_date = exp.strftime("%Y-%m-%d")
            p.is_expired = exp < today
            if p.is_expired:
                cnt += 1
        self._save_products()
        return cnt

    def clear_zero_stock(self) -> int:
        """下架库存为 0 的商品（保留记录）。返回下架数量。"""
        cnt = 0
        for p in self.products:
            if p.quantity == 0 and p.is_on_sale:
                p.is_on_sale = False
                cnt += 1
        self._save_products()
        return cnt

    def clear_all_expired(self) -> int:
        """下架所有已过期商品（保留记录）。返回下架数量。"""
        cnt = 0
        for p in self.products:
            if p.is_expired and p.is_on_sale:
                p.is_on_sale = False
                cnt += 1
        self._save_products()
        return cnt

    # ============ 用户管理 ============
    def find_user(self, uid: int) -> Optional[User]:
        for u in self.users:
            if u.id == uid:
                return u
        return None

    def find_user_by_name(self, username: str) -> Optional[User]:
        for u in self.users:
            if u.username == username:
                return u
        return None

    def register(self, username, password, name, is_student=False) -> tuple[bool, str, Optional[User]]:
        if not username or not password:
            return False, "用户名和密码不能为空。", None
        if " " in username or " " in password:
            return False, "用户名和密码不能包含空格。", None
        if self.find_user_by_name(username):
            return False, f"用户名 {username} 已被注册。", None
        new_id = max([u.id for u in self.users], default=0) + 1
        u = User(new_id, username, password, name, coupon=5.0, balance=0.0,
                 register_date=_now(), is_student=bool(is_student))
        self.users.append(u)
        self._save_users()
        tip = "学生享 9 折优惠。" if is_student else "新用户获赠 5 元优惠券。"
        return True, f"注册成功，欢迎 {name}！{tip}", u

    def login(self, username, password):
        """返回 (role, User|None, message)。role ∈ {admin, buyer, None}。"""
        if username == "admin" and password == self.admin_password:
            admin = self.find_user_by_name("admin")
            return "admin", admin, "管理员登录成功"
        u = self.find_user_by_name(username)
        if not u or u.password != password:
            return None, None, "用户名或密码错误。"
        # 灰度福利：灰度组内、从未消费、且未发放过 → 首次登录送 3 元券
        bonus = ""
        if (self.in_gray(u.id) and u.order_count == 0
                and u.total_spent < 0.01 and not u.gray_given):
            u.coupon = round(u.coupon + 3, 2)
            u.gray_given = True
            self._save_users()
            bonus = "（灰度福利：新用户专享 3 元优惠券已到账）"
        return "buyer", u, f"欢迎回来，{u.name}！" + bonus

    def change_password(self, uid, old, new) -> tuple[bool, str]:
        u = self.find_user(uid)
        if not u:
            return False, "用户不存在。"
        if u.password != old:
            return False, "原密码不正确。"
        if not new:
            return False, "新密码不能为空。"
        u.password = new
        self._save_users()
        return True, "密码修改成功。"

    def recharge(self, uid, amount) -> tuple[bool, str]:
        u = self.find_user(uid)
        if not u:
            return False, "用户不存在。"
        if _is_bad_money(amount):
            return False, "金额无效，请输入 0.01 ~ 99999 之间的数值。"
        u.balance = round(u.balance + float(amount), 2)
        self._save_users()
        return True, f"充值成功，{u.name} 当前余额 {u.balance:.2f} 元。"

    def add_coupon(self, uid, amount) -> tuple[bool, str]:
        u = self.find_user(uid)
        if not u:
            return False, "用户不存在。"
        if _is_bad_money(amount):
            return False, "优惠券金额无效。"
        u.coupon = round(u.coupon + float(amount), 2)
        self._save_users()
        return True, f"已发放 {float(amount):.2f} 元优惠券。"

    def delete_user(self, uid) -> tuple[bool, str]:
        u = self.find_user(uid)
        if not u:
            return False, "用户不存在。"
        if u.username == "admin":
            return False, "不能删除管理员账号。"
        self.users.remove(u)
        self._save_users()
        return True, f"已删除用户：{u.username}"

    # ============ 购买（优惠券抵扣 + 支付网关） ============
    def buy(self, uid, pid, qty, use_coupon, method: PayMethod,
            card_no="") -> dict:
        user = self.find_user(uid)
        if not user:
            return {"ok": False, "message": "用户不存在。"}
        product = self.find_product(pid)
        if not product:
            return {"ok": False, "message": "商品不存在。"}
        if qty <= 0 or qty > 9999:
            return {"ok": False, "message": "购买数量需在 1 ~ 9999 之间。"}

        # 轻量过期检查（按过期日判断，不依赖是否已扫描）
        if product.expired_date and product.expired_date < _today():
            product.is_expired = True
        if product.is_expired or not product.is_on_sale:
            return {"ok": False, "message": "商品已下架或已过期，无法购买。"}
        if product.quantity < qty:
            return {"ok": False, "message": f"库存不足，仅剩 {product.quantity} 件。"}

        original_total = round(product.price * qty, 2)
        # 学生折扣：复用 checkout.apply_student_discount（Exercise 2 核心功能）
        student_discount = 0.0
        if user.is_student:
            discounted = checkout.apply_student_discount(original_total, True)
            student_discount = round(original_total - discounted, 2)
        total = round(original_total - student_discount, 2)
        # 优惠券抵扣：券 ≥ 折后价 → 全抵（实付 0）；否则抵券额
        discount = 0.0
        if use_coupon and user.coupon > 0:
            discount = min(user.coupon, total)
        final = round(total - discount, 2)

        order_id = self.storage.next_order_id()
        txn_id = ""
        pay_message = ""
        pay_method_label = "优惠券抵扣"

        if final > 0:
            # —— 支付网关 ——
            result = self.gateway.pay(order_id, final, method,
                                      balance=user.balance, card_no=card_no)
            self.gateway.record(self.storage, result, order_id)
            if not result.success:
                return {"ok": False, "message": result.message}
            txn_id = result.txn_id
            pay_message = result.message
            pay_method_label = method.value
            if method is PayMethod.BALANCE:
                user.balance = round(user.balance - final, 2)
        else:
            pay_message = "优惠券全额抵扣，实付 0 元！"

        if discount > 0:
            user.coupon = round(user.coupon - discount, 2)

        product.quantity -= qty
        if product.quantity == 0:
            product.is_on_sale = False   # 库存归零自动下架

        order = Order(order_id, product.id, product.name, product.price, qty,
                      final, _now(), user.id, pay_method_label)
        self.storage.append_order(order)
        self.orders.append(order)
        self._update_purchase(user, final)
        self._save_products()
        self._save_users()
        return {
            "ok": True, "message": pay_message,
            "txn_id": txn_id, "order_id": order_id,
            "total": original_total, "student_discount": student_discount,
            "discount": discount, "final": final,
        }

    def _update_purchase(self, user: User, final: float):
        """按实付金额累计消费、升级 VIP、满 200 送 5 元券（对齐 v3）。"""
        if final <= 0 or final != final or final > 9999999.0:
            return
        user.total_spent = round(user.total_spent + final, 2)
        user.order_count += 1
        if user.total_spent >= 500 and not user.is_vip:
            user.is_vip = True
            user.coupon = round(user.coupon + 20, 2)
        # 每跨越 200 元门槛，送 5 元券（约 2.5% 返券率）
        new_coupon = int(user.total_spent / 200) - int((user.total_spent - final) / 200)
        if new_coupon > 0:
            user.coupon = round(user.coupon + new_coupon * 5, 2)

    def user_orders(self, uid) -> List[Order]:
        return [o for o in self.orders if o.buyer_id == uid]

    # ============ 智能 / 灰度 ============
    def recommend(self, uid) -> List[dict]:
        return ai.ai_recommend(uid, self.products, self.orders)

    def predict_sales(self, product_id) -> dict:
        return ai.predict_sales(self.orders, product_id)

    def in_gray(self, uid) -> bool:
        return ai.in_gray(uid, self.gray_percent)

    def set_gray_percent(self, pct) -> tuple[bool, str]:
        if not 0 <= pct <= 100:
            return False, "灰度比例需在 0~100 之间。"
        self.gray_percent = int(pct)
        return True, f"灰度发布比例已设为 {self.gray_percent}%。"

    # ============ 管理员密码 ============
    def change_admin_password(self, old, new) -> tuple[bool, str]:
        if old != self.admin_password:
            return False, "原密码不正确。"
        if not new:
            return False, "新密码不能为空。"
        self.admin_password = new
        self.storage.save_admin_password(new)
        return True, "管理员密码修改成功。"

    # ============ 支付流水 ============
    def list_payments(self) -> List[PaymentRecord]:
        return self.storage.load_payments()

    # ============ 备份 / 恢复 ============
    def backup(self) -> str:
        self.storage.backup()
        return "已备份到 latest_backup/ 目录。"

    def restore(self) -> tuple[bool, str]:
        self.storage.restore()
        self.products = self.storage.load_products()
        self.users = self.storage.load_users()
        self.orders = self.storage.load_orders()
        self.admin_password = self.storage.load_admin_password("123456")
        return True, "已从 latest_backup/ 恢复数据。"
