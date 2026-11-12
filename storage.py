# -*- coding: utf-8 -*-
"""文件持久化（JSON + 原子写入）

对应原 C 版的 products.txt / users.txt / orders.txt / order_counter.txt，
这里统一放进 data/ 目录，用 JSON 保存；每次写入都先写临时文件再 os.replace() 原子替换，
避免中途崩溃导致数据全损（等价于原 C 版的 products_tmp.txt + rename 安全写入）。
"""
import os
import json
from dataclasses import asdict
from typing import List

from models import Product, User, Order, PaymentRecord


def _atomic_write(path: str, data: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
    os.replace(tmp, path)


class Storage:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.products_path = os.path.join(data_dir, "products.json")
        self.users_path = os.path.join(data_dir, "users.json")
        self.orders_path = os.path.join(data_dir, "orders.json")
        self.counter_path = os.path.join(data_dir, "counter.json")
        self.payments_path = os.path.join(data_dir, "payments.json")

    # ---------- 商品 ----------
    def load_products(self) -> List[Product]:
        if not os.path.exists(self.products_path):
            return []
        with open(self.products_path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        return [Product(**r) for r in rows]

    def save_products(self, products: List[Product]) -> None:
        rows = [asdict(p) for p in products]
        _atomic_write(self.products_path, json.dumps(rows, ensure_ascii=False, indent=2))

    # ---------- 用户 ----------
    def load_users(self) -> List[User]:
        if not os.path.exists(self.users_path):
            return []
        with open(self.users_path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        return [User(**r) for r in rows]

    def save_users(self, users: List[User]) -> None:
        rows = [asdict(u) for u in users]
        _atomic_write(self.users_path, json.dumps(rows, ensure_ascii=False, indent=2))

    # ---------- 订单 ----------
    def load_orders(self) -> List[Order]:
        if not os.path.exists(self.orders_path):
            return []
        with open(self.orders_path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        return [Order(**r) for r in rows]

    def append_order(self, order: Order) -> None:
        orders = self.load_orders()
        orders.append(order)
        rows = [asdict(o) for o in orders]
        _atomic_write(self.orders_path, json.dumps(rows, ensure_ascii=False, indent=2))

    # ---------- 订单号计数器 ----------
    def next_order_id(self) -> int:
        if os.path.exists(self.counter_path):
            with open(self.counter_path, "r", encoding="utf-8") as f:
                n = json.load(f).get("next", 1)
        else:
            n = 1
        _atomic_write(self.counter_path, json.dumps({"next": n + 1}))
        return n

    # ---------- 支付记录（新增） ----------
    def load_payments(self) -> List[PaymentRecord]:
        if not os.path.exists(self.payments_path):
            return []
        with open(self.payments_path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        return [PaymentRecord(**r) for r in rows]

    def append_payment(self, rec: PaymentRecord) -> None:
        payments = self.load_payments()
        payments.append(rec)
        rows = [asdict(p) for p in payments]
        _atomic_write(self.payments_path, json.dumps(rows, ensure_ascii=False, indent=2))

    # ---------- 备份 / 恢复 ----------
    def backup(self, backup_dir: str = "latest_backup") -> None:
        os.makedirs(backup_dir, exist_ok=True)
        for name in ("products.json", "users.json", "orders.json",
                     "counter.json", "payments.json"):
            src = os.path.join(self.data_dir, name)
            if os.path.exists(src):
                with open(src, "r", encoding="utf-8") as f:
                    data = f.read()
                with open(os.path.join(backup_dir, name), "w", encoding="utf-8") as f:
                    f.write(data)

    def restore(self, backup_dir: str = "latest_backup") -> bool:
        for name in ("products.json", "users.json", "orders.json",
                     "counter.json", "payments.json"):
            src = os.path.join(backup_dir, name)
            if os.path.exists(src):
                with open(src, "r", encoding="utf-8") as f:
                    data = f.read()
                _atomic_write(os.path.join(self.data_dir, name), data)
        return True
