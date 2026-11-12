# -*- coding: utf-8 -*-
"""商城核心业务层

把原 C 版「智能商城系统」的全部功能翻译成 Python，并接入支付网关：
- 商品增删改查 / 保质期过期检测 / 清空零库存 / 清空过期
- 用户注册 / 登录 / 改密 / 充值 / 删除 / 优惠券 / VIP
- 买家：选购 -> 用券 -> 支付网关付款 -> 生成订单 -> 累计消费
- 管理员：销量预测 / 智能推荐 / 灰度发布 / 备份恢复 / 支付流水
"""
from datetime import date, datetime, timedelta
from typing import List, Optional

from models import Product, User, Order, PaymentRecord
from storage import Storage
from payment import PaymentGateway, PayMethod, PaymentResult
from ai import in_gray as _in_gray, predict_sales as _predict_sales, ai_recommend as _ai_recommend


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


class Mall:
    def __init__(self, storage: Optional[Storage] = None):
        self.storage = storage or Storage()
        self.gateway = PaymentGateway()
        self.gray_percent = 10
        self.admin_password = "123456"
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
            User(1, "admin", "123456", "管理员", coupon=10.0, balance=100.0,
                 is_vip=True, register_date=_now()),
            User(2, "user1", "123456", "张三", coupon=10.0, balance=50.0,
                 register_date=_now()),
            User(3, "user2", "123456", "李四", coupon=10.0, balance=20.0,
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

    def add_product(self, pid, category, name, price, year, month, day,
                    shelf_life, quantity) -> tuple[bool, str]:
        if self.find_product(pid):
            return False, f"商品 ID {pid} 已存在。"
        exp = date(year, month, day) + timedelta(days=shelf_life)
        p = Product(pid, category, name, float(price), year, month, day,
                    shelf_life, expired_date=exp.strftime("%Y-%m-%d"),
                    is_expired=exp < date.today(), is_on_sale=True,
                    quantity=int(quantity))
        self.products.append(p)
        self._save_products()
        return True, f"已上架商品：{name}"

    def list_products(self, on_sale_only=False, in_stock_only=False) -> List[Product]:
        result = self.products
        if on_sale_only:
            result = [p for p in result if p.is_on_sale]
        if in_stock_only:
            result = [p for p in result if p.quantity > 0]
        return result

    def search_name(self, kw: str) -> List[Product]:
        kw = kw.strip()
        return [p for p in self.products if kw in p.name]

    def modify_product(self, pid, category=None, name=None, price=None,
                       quantity=None, on_sale=None, shelf_life=None) -> tuple[bool, str]:
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
        if shelf_life is not None:
            p.shelf_life = int(shelf_life)
            p.expired_date = (date(p.year, p.month, p.day) +
                              timedelta(days=p.shelf_life)).strftime("%Y-%m-%d")
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
        before = len(self.products)
        self.products = [p for p in self.products if p.quantity > 0]
        self._save_products()
        return before - len(self.products)

    def clear_all_expired(self) -> int:
        before = len(self.products)
        self.products = [p for p in self.products if not p.is_expired]
        self._save_products()
        return before - len(self.products)

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

    def register(self, username, password, name) -> tuple[bool, str, Optional[User]]:
        if not username or not password:
            return False, "用户名和密码不能为空。", None
        if self.find_user_by_name(username):
            return False, f"用户名 {username} 已被注册。", None
        new_id = max([u.id for u in self.users], default=0) + 1
        u = User(new_id, username, password, name, coupon=10.0, balance=0.0,
                 register_date=_now())
        self.users.append(u)
        self._save_users()
        return True, f"注册成功，欢迎 {name}！新用户获赠 10 元优惠券。", u

    def login(self, username, password):
        """返回 (is_admin, User|None, message)。管理员账号走管理面板。"""
        if username == "admin" and password == self.admin_password:
            admin = self.find_user_by_name("admin")
            return "admin", admin, "管理员登录成功"
        u = self.find_user_by_name(username)
        if not u or u.password != password:
            return None, None, "用户名或密码错误。"
        return "buyer", u, f"欢迎回来，{u.name}！"

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
        if amount <= 0:
            return False, "充值金额必须大于 0。"
        u.balance = round(u.balance + amount, 2)
        self._save_users()
        return True, f"充值成功，{u.name} 当前余额 {u.balance:.2f} 元。"

    def add_coupon(self, uid, amount) -> tuple[bool, str]:
        u = self.find_user(uid)
        if not u:
            return False, "用户不存在。"
        u.coupon = round(u.coupon + amount, 2)
        self._save_users()
        return True, f"已发放 {amount:.2f} 元优惠券。"

    def delete_user(self, uid) -> tuple[bool, str]:
        u = self.find_user(uid)
        if not u:
            return False, "用户不存在。"
        if u.username == "admin":
            return False, "不能删除管理员账号。"
        self.users.remove(u)
        self._save_users()
        return True, f"已删除用户：{u.username}"

    # ============ 购买（核心：接入支付网关） ============
    def buy(self, uid, pid, qty, use_coupon, method: PayMethod,
            card_no="") -> dict:
        user = self.find_user(uid)
        if not user:
            return {"ok": False, "message": "用户不存在。"}
        product = self.find_product(pid)
        if not product:
            return {"ok": False, "message": "商品不存在。"}
        if not product.is_on_sale:
            return {"ok": False, "message": "该商品已下架。"}
        self.check_expired()
        product = self.find_product(pid)  # 刷新过期状态后重新取
        if product.is_expired:
            return {"ok": False, "message": "该商品已过期，无法购买。"}
        if qty <= 0:
            return {"ok": False, "message": "购买数量必须大于 0。"}
        if product.quantity < qty:
            return {"ok": False, "message": f"库存不足，仅剩 {product.quantity} 件。"}

        total = round(product.price * qty, 2)
        discount = 0.0
        if use_coupon:
            discount = min(user.coupon, total)
        final = round(total - discount, 2)

        # —— 支付网关 ——
        order_id = self.storage.next_order_id()
        result = self.gateway.pay(order_id, final, method,
                                  balance=user.balance, card_no=card_no)
        self.gateway.record(self.storage, result, order_id)
        if not result.success:
            return {"ok": False, "message": result.message}

        # 支付成功：扣券 / 扣余额 / 减库存 / 生成订单
        if use_coupon and discount > 0:
            user.coupon = round(user.coupon - discount, 2)
        if method is PayMethod.BALANCE:
            user.balance = round(user.balance - final, 2)
        product.quantity -= qty

        order = Order(order_id, product.id, product.name, product.price, qty,
                      final, _now(), user.id, method.value)
        self.storage.append_order(order)
        self.orders.append(order)
        self._update_purchase(user, final)
        self._save_products()
        self._save_users()
        return {
            "ok": True, "message": result.message,
            "txn_id": result.txn_id, "order_id": order_id,
            "total": total, "discount": discount, "final": final,
        }

    def _update_purchase(self, user: User, final: float):
        user.total_spent = round(user.total_spent + final, 2)
        user.order_count += 1
        bonus = int(final // 100) * 10          # 每满 100 元送 10 元券
        if bonus > 0:
            user.coupon = round(user.coupon + bonus, 2)
        if not user.is_vip and user.total_spent >= 500:   # 满 500 升 VIP 送 50 元券
            user.is_vip = True
            user.coupon = round(user.coupon + 50, 2)

    def user_orders(self, uid) -> List[Order]:
        return [o for o in self.orders if o.buyer_id == uid]

    # ============ 智能 / 灰度 ============
    def recommend(self, uid) -> List[Product]:
        user = self.find_user(uid)
        if not user:
            return []
        return _ai_recommend(user, self.products, self.orders)

    def predict_sales(self, days=7) -> dict:
        return _predict_sales(self.orders, days)

    def in_gray(self, uid) -> bool:
        return _in_gray(uid, self.gray_percent)

    def set_gray_percent(self, pct) -> tuple[bool, str]:
        if not 0 <= pct <= 100:
            return False, "灰度比例需在 0~100 之间。"
        self.gray_percent = int(pct)
        return True, f"灰度发布比例已设为 {self.gray_percent}%。"

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
        return True, "已从 latest_backup/ 恢复数据。"
