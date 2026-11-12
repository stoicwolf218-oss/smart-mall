# -*- coding: utf-8 -*-
"""checkout 模块的自动化测试（Exercise 2 学生折扣）。"""

from checkout import apply_student_discount


def test_student_receives_10_percent_discount():
    assert apply_student_discount(100, True) == 90.0


def test_non_student_pays_original_price():
    assert apply_student_discount(100, False) == 100.0


def test_student_discount_on_small_total():
    assert apply_student_discount(4.5, True) == 4.05


if __name__ == "__main__":
    test_student_receives_10_percent_discount()
    test_non_student_pays_original_price()
    test_student_discount_on_small_total()
    print("All checkout tests passed.")
