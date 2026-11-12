# -*- coding: utf-8 -*-
"""Checkout 结算模块（学生折扣）

对应 Exercise 2 的核心功能：对学生顾客在结算时给予 10% 优惠。
smart-mall 的购买流程（mall.py 的 buy）复用本模块的
apply_student_discount，保证折扣规则集中、可测试。
"""

STUDENT_DISCOUNT_RATE = 0.90


def apply_student_discount(total, is_student):
    """学生享受 10% 优惠。

    Args:
        total: 原价总额（元）。
        is_student: 是否为在校学生。

    Returns:
        学生返回 9 折后的金额；非学生返回原价。
    """
    if is_student:
        return total * STUDENT_DISCOUNT_RATE
    return total
