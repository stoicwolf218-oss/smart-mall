# -*- coding: utf-8 -*-
"""支付网关（新增模块）

模拟接入第三方支付渠道：余额支付 / 支付宝 / 微信支付 / 银行卡。
- 生成唯一交易号（txn_id）
- 模拟网关处理（余额：实时扣款；支付宝/微信：生成模拟二维码；银行卡：校验卡号）
- 记录每一笔交易，供管理员在“支付流水”里查看
"""
import time
from datetime import datetime
from enum import Enum

from models import PaymentRecord


class PayMethod(Enum):
    BALANCE = "余额支付"
    ALIPAY = "支付宝"
    WECHAT = "微信支付"
    BANK = "银行卡"


class PaymentResult:
    """支付结果"""
    def __init__(self, success: bool, txn_id: str, method: str,
                 amount: float, message: str):
        self.success = success
        self.txn_id = txn_id
        self.method = method
        self.amount = amount
        self.message = message


class PaymentGateway:
    """模拟支付网关。无真实资金流转，仅演示完整支付链路。"""

    def __init__(self):
        self._seq = int(time.time())

    def _next_txn_id(self) -> str:
        self._seq += 1
        return f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{self._seq % 10000:04d}"

    def pay(self, order_id: int, amount: float, method: PayMethod,
            balance: float = 0.0, card_no: str = "") -> PaymentResult:
        """发起一笔支付。

        amount < 0.01 时判定为无效金额；余额支付需校验余额；银行卡做简单校验。
        """
        amount = round(amount, 2)
        txn_id = self._next_txn_id()

        if amount <= 0:
            return PaymentResult(False, txn_id, method.value, amount, "支付金额无效。")

        if method is PayMethod.BALANCE:
            if balance < amount:
                return PaymentResult(False, txn_id, method.value, amount,
                                     f"余额不足（当前 {balance:.2f} 元）。请先充值或改用其他支付方式。")
            return PaymentResult(True, txn_id, method.value, amount, "余额支付成功。")

        if method is PayMethod.BANK:
            if not card_no or len(card_no.replace(" ", "")) < 12:
                return PaymentResult(False, txn_id, method.value, amount, "银行卡号无效。")
            return PaymentResult(True, txn_id, method.value, amount, "银行卡支付成功。")

        # 支付宝 / 微信支付：模拟“扫一扫/确认支付”成功
        label = "支付宝" if method is PayMethod.ALIPAY else "微信支付"
        return PaymentResult(True, txn_id, method.value, amount, f"{label}支付成功。")

    def record(self, storage, result: PaymentResult, order_id: int) -> None:
        """把交易结果写入支付流水文件。"""
        rec = PaymentRecord(
            transaction_id=result.txn_id,
            order_id=order_id,
            amount=result.amount,
            method=result.method,
            status="成功" if result.success else "失败",
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        storage.append_payment(rec)
