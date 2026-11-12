# -*- coding: utf-8 -*-
"""数据模型：商品 / 用户 / 订单 / 支付记录

由原 C 语言「智能商城系统」（shop_v2.c）翻译而来，改用 Python dataclass 表达，
并新增「支付网关」所需的支付记录模型。
"""
from dataclasses import dataclass


@dataclass
class Product:
    """商品"""
    id: int
    category: str
    name: str
    price: float
    year: int
    month: int
    day: int
    shelf_life: int
    expired_date: str = ""
    is_expired: bool = False
    is_on_sale: bool = True
    quantity: int = 0


@dataclass
class User:
    """用户（带余额 / 优惠券 / VIP）"""
    id: int
    username: str
    password: str
    name: str
    coupon: float = 5.0
    balance: float = 0.0
    total_spent: float = 0.0
    order_count: int = 0
    is_vip: bool = False
    register_date: str = ""
    gray_given: bool = False   # 灰度福利是否已发放（防反复登录重复赠券）
    is_student: bool = False   # 是否学生（享受 10% 学生折扣，对应 Exercise 2 的核心功能）


@dataclass
class Order:
    """订单"""
    order_id: int
    product_id: int
    product_name: str
    price: float
    quantity: int
    total: float            # 实付金额
    order_date: str
    buyer_id: int
    payment_method: str = "余额支付"   # 新增：支付网关记录实际支付方式


@dataclass
class PaymentRecord:
    """支付网关交易记录（新增）"""
    transaction_id: str
    order_id: int
    amount: float
    method: str
    status: str
    time: str
