# -*- coding: utf-8 -*-
"""Web 服务器（标准库 http.server，零第三方依赖）

- 提供 REST API（JSON）
- 托管 static/ 下的前端页面
运行：python app.py  → 浏览器打开 http://localhost:8000
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from mall import Mall
from storage import Storage
from payment import PayMethod

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

mall = Mall(Storage(data_dir=os.path.join(BASE_DIR, "data")))

PORT = int(os.environ.get("PORT", "8000"))


# ---------- 工具 ----------
def _json(handler, status, data):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _ok(handler, **kw):
    _json(handler, 200, {"ok": True, **kw})


def _fail(handler, msg, status=200):
    _json(handler, status, {"ok": False, "message": msg})


def _read_json(handler):
    try:
        length = int(handler.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(handler.rfile.read(length).decode("utf-8"))
    except Exception:
        return {}


def _int(d, key, default=0):
    v = d.get(key, default)
    if isinstance(v, list):
        v = v[0] if v else default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _float(d, key, default=0.0):
    v = d.get(key, default)
    if isinstance(v, list):
        v = v[0] if v else default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _bool(d, key, default=False):
    v = d.get(key, default)
    if isinstance(v, list):
        v = v[0] if v else default
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "on", "yes")
    return bool(v)


def _user_dict(u):
    return {
        "id": u.id, "username": u.username, "name": u.name,
        "coupon": u.coupon, "balance": u.balance,
        "total_spent": u.total_spent, "order_count": u.order_count,
        "is_vip": u.is_vip, "register_date": u.register_date,
        "is_student": u.is_student,
    }


def _product_dict(p):
    return {
        "id": p.id, "category": p.category, "name": p.name,
        "price": p.price, "year": p.year, "month": p.month, "day": p.day,
        "shelf_life": p.shelf_life, "expired_date": p.expired_date,
        "is_expired": p.is_expired, "is_on_sale": p.is_on_sale,
        "quantity": p.quantity,
    }


def _order_dict(o):
    return {
        "order_id": o.order_id, "product_id": o.product_id,
        "product_name": o.product_name, "price": o.price,
        "quantity": o.quantity, "total": o.total,
        "order_date": o.order_date, "buyer_id": o.buyer_id,
        "payment_method": o.payment_method,
    }


_METHODS = {
    "余额支付": PayMethod.BALANCE,
    "支付宝": PayMethod.ALIPAY,
    "微信支付": PayMethod.WECHAT,
    "银行卡": PayMethod.BANK,
}


class Handler(BaseHTTPRequestHandler):
    # 静默默认日志
    def log_message(self, *args):
        pass

    # ---------- 路由 ----------
    def _route(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)
        return path, qs

    def do_GET(self):
        path, qs = self._route()
        try:
            self._get(path, qs)
        except Exception as e:
            _fail(self, f"服务器错误：{e}", 500)

    def do_POST(self):
        path, qs = self._route()
        data = _read_json(self)
        try:
            self._post(path, qs, data)
        except Exception as e:
            _fail(self, f"服务器错误：{e}", 500)

    def do_PUT(self):
        path, qs = self._route()
        data = _read_json(self)
        try:
            self._put(path, qs, data)
        except Exception as e:
            _fail(self, f"服务器错误：{e}", 500)

    def do_DELETE(self):
        path, qs = self._route()
        try:
            self._delete(path, qs)
        except Exception as e:
            _fail(self, f"服务器错误：{e}", 500)

    # ---------- 静态文件 ----------
    def _serve_static(self):
        if self.path == "/" or self.path == "":
            rel = "index.html"
        else:
            rel = self.path.lstrip("/")
        # 只允许访问 static 目录，防路径穿越
        fp = os.path.normpath(os.path.join(STATIC_DIR, rel))
        if not fp.startswith(STATIC_DIR) or not os.path.isfile(fp):
            self.send_error(404)
            return
        ext = os.path.splitext(fp)[1].lower()
        ctype = {".html": "text/html; charset=utf-8",
                 ".css": "text/css; charset=utf-8",
                 ".js": "application/javascript; charset=utf-8",
                 ".png": "image/png", ".jpg": "image/jpeg",
                 ".svg": "image/svg+xml", ".ico": "image/x-icon"}.get(ext, "application/octet-stream")
        with open(fp, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------- GET ----------
    def _get(self, path, qs):
        if not path.startswith("/api"):
            return self._serve_static()

        if path == "/api/products":
            all_ = qs.get("all", ["0"])[0] == "1"
            kw = qs.get("search", [""])[0]
            prods = mall.list_products() if all_ else \
                [p for p in mall.list_products() if p.is_on_sale and not p.is_expired]
            if kw:
                prods = [p for p in prods if kw in p.name]
            return _ok(self, products=[_product_dict(p) for p in prods])

        if path == "/api/admin/users":
            return _ok(self, users=[_user_dict(u) for u in mall.users])

        if path == "/api/admin/payments":
            pays = mall.list_payments()
            return _ok(self, payments=[
                {"transaction_id": t.transaction_id, "order_id": t.order_id,
                 "amount": t.amount, "method": t.method, "status": t.status,
                 "time": t.time} for t in pays])

        if path == "/api/predict":
            pid = _int(qs, "product_id", 0)
            return _ok(self, result=mall.predict_sales(pid))

        # /api/user/<id>/info  /api/user/<id>/orders  /api/user/<id>/recommend
        parts = path.split("/")
        if len(parts) >= 5 and parts[2] == "user":
            uid = int(parts[3])
            if parts[4] == "info":
                u = mall.find_user(uid)
                return _ok(self, user=_user_dict(u)) if u else _fail(self, "用户不存在")
            if parts[4] == "orders":
                return _ok(self, orders=[_order_dict(o) for o in mall.user_orders(uid)])
            if parts[4] == "recommend":
                return _ok(self, items=mall.recommend(uid))

        return _fail(self, "未知接口", 404)

    # ---------- POST ----------
    def _post(self, path, qs, d):
        if path == "/api/register":
            ok, msg, u = mall.register(d.get("username", ""), d.get("password", ""),
                                       d.get("name", ""),
                                       is_student=_bool(d, "is_student"))
            if ok:
                return _ok(self, message=msg, user=_user_dict(u))
            return _fail(self, msg)

        if path == "/api/login":
            role, u, msg = mall.login(d.get("username", ""), d.get("password", ""))
            if role is None:
                return _fail(self, msg)
            return _ok(self, role=role, user=_user_dict(u) if u else None, message=msg)

        if path == "/api/buy":
            method = _METHODS.get(d.get("method", ""), PayMethod.BALANCE)
            res = mall.buy(_int(d, "user_id"), _int(d, "product_id"),
                           _int(d, "qty"), bool(d.get("use_coupon", True)),
                           method, d.get("card_no", ""))
            if res["ok"]:
                return _ok(self, **res)
            return _fail(self, res["message"])

        if path == "/api/admin/products":
            ok, msg = mall.add_product(
                d.get("category", ""), d.get("name", ""), _float(d, "price"),
                _int(d, "year"), _int(d, "month"), _int(d, "day"),
                _int(d, "shelf_life"), _int(d, "quantity"),
                bool(d.get("is_on_sale", True)))
            return _ok(self, message=msg) if ok else _fail(self, msg)

        if path == "/api/admin/products/check_expired":
            return _ok(self, count=mall.check_expired())

        if path == "/api/admin/products/clear_zero":
            return _ok(self, count=mall.clear_zero_stock())

        if path == "/api/admin/products/clear_expired":
            return _ok(self, count=mall.clear_all_expired())

        if path == "/api/admin/gray":
            ok, msg = mall.set_gray_percent(_int(d, "percent"))
            return _ok(self, message=msg) if ok else _fail(self, msg)

        if path == "/api/admin/backup":
            return _ok(self, message=mall.backup())

        if path == "/api/admin/restore":
            ok, msg = mall.restore()
            return _ok(self, message=msg) if ok else _fail(self, msg)

        if path == "/api/admin/password":
            ok, msg = mall.change_admin_password(d.get("old", ""), d.get("new", ""))
            return _ok(self, message=msg) if ok else _fail(self, msg)

        # /api/admin/users/<id>/recharge  /api/admin/users/<id>/coupon
        # /api/user/<id>/recharge  /api/user/<id>/change_password
        parts = path.split("/")
        if len(parts) >= 5:
            if parts[2] == "admin" and parts[3] == "users" and parts[5] == "recharge":
                ok, msg = mall.recharge(int(parts[4]), _float(d, "amount"))
                return _ok(self, message=msg) if ok else _fail(self, msg)
            if parts[2] == "admin" and parts[3] == "users" and parts[5] == "coupon":
                ok, msg = mall.add_coupon(int(parts[4]), _float(d, "amount"))
                return _ok(self, message=msg) if ok else _fail(self, msg)
            if parts[2] == "user" and parts[4] == "recharge":
                ok, msg = mall.recharge(int(parts[3]), _float(d, "amount"))
                return _ok(self, message=msg) if ok else _fail(self, msg)
            if parts[2] == "user" and parts[4] == "change_password":
                ok, msg = mall.change_password(int(parts[3]), d.get("old", ""), d.get("new", ""))
                return _ok(self, message=msg) if ok else _fail(self, msg)

        return _fail(self, "未知接口", 404)

    # ---------- PUT ----------
    def _put(self, path, qs, d):
        parts = path.split("/")
        if len(parts) >= 5 and parts[2] == "admin" and parts[3] == "products":
            pid = int(parts[4])
            kwargs = {}
            for k in ("category", "name"):
                if d.get(k):
                    kwargs[k] = d[k]
            for k in ("price", "quantity", "shelf_life", "year", "month", "day"):
                if d.get(k) is not None:
                    kwargs[k] = _float(d, k) if k == "price" else _int(d, k)
            if "on_sale" in d:
                kwargs["on_sale"] = bool(d["on_sale"])
            ok, msg = mall.modify_product(pid, **kwargs)
            return _ok(self, message=msg) if ok else _fail(self, msg)
        return _fail(self, "未知接口", 404)

    # ---------- DELETE ----------
    def _delete(self, path, qs):
        parts = path.split("/")
        if len(parts) >= 5 and parts[2] == "admin" and parts[3] == "products":
            ok, msg = mall.delete_product(int(parts[4]))
            return _ok(self, message=msg) if ok else _fail(self, msg)
        if len(parts) >= 5 and parts[2] == "admin" and parts[3] == "users":
            ok, msg = mall.delete_user(int(parts[4]))
            return _ok(self, message=msg) if ok else _fail(self, msg)
        return _fail(self, "未知接口", 404)


def main():
    print("=" * 50)
    print("  智能商城系统 Web 版已启动")
    print(f"  请用浏览器打开： http://localhost:{PORT}")
    print("  默认账号：admin/123456（管理员）  user1/123456（买家）")
    print("  按 Ctrl+C 停止服务")
    print("=" * 50)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止服务。")
        server.server_close()


if __name__ == "__main__":
    main()
