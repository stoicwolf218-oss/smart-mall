# 智能商城系统（Python Web 版 + 支付网关 + 现代网页界面）

> 由 C 语言「智能商城系统」shop_v3.c 忠实翻译为 Python，并新增：
> **支付网关**（余额/支付宝/微信/银行卡）、**现代网页界面**（HTML/CSS/JS）。
> 零第三方依赖，`python app.py` 一键启动，浏览器直接使用。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## ✨ 功能特性

### 🎨 现代网页界面
- 漂亮的卡片式商城界面（渐变配色、圆角、动效、响应式布局）
- 登录/注册、买家工作台、管理员后台三大界面
- 小猫情绪反馈 🐱（购买成功 😺 / 失败 😿）

### 🛒 买家功能
- 浏览在售商品、搜索、AI 智能推荐
- 下单：优惠券抵扣 + **支付网关**（余额 / 支付宝 / 微信 / 银行卡）
- 我的订单、账户充值、修改密码、个人中心

### 🛠 管理员功能（16 项）
- 商品管理：录入（ID 自动分配）/ 列表 / 搜索 / 修改 / 删除
- 过期检查、下架零库存、下架过期商品
- 用户管理：列表 / 充值 / 发券 / 删除
- **销量预测**：最小二乘线性回归，未来 7 天逐日预测 + 20% 安全库存备货量
- **灰度发布**：按 `user_id % 100` 控制比例，灰度新用户首次登录送 3 元券（防刷）
- 数据备份 / 恢复、支付流水查看、修改管理员密码（持久化）

### 💳 支付网关
- 四种支付方式：余额 / 支付宝 / 微信 / 银行卡
- 生成唯一交易号，模拟余额校验、卡号校验
- 每笔交易写入 `data/payments.json`，管理员可查看流水

### 🧠 优惠券与 VIP（对齐 shop_v3.c）
| 场景 | 优惠券 |
|------|--------|
| 注册 | 送 5 元 |
| 实付每满 200 元 | 送 5 元（约 2.5% 返券） |
| 累计消费满 500 升 VIP | 送 20 元 |
| 灰度新用户首次登录 | 送 3 元 |

---

## 🚀 快速开始

### 环境要求
- Python **3.8+**（只用标准库 `http.server` / `json`，**无需安装任何第三方库**）

### 运行
```bash
# 在项目目录下
python app.py
```
然后浏览器打开：**http://localhost:8000**

（Windows 也可直接双击 `app.py`；想换端口用 `PORT=9000 python app.py`）

### 内置账号
| 角色   | 用户名 | 密码    |
|--------|--------|---------|
| 管理员 | admin  | 123456  |
| 买家   | user1  | 123456  |
| 买家   | user2  | 123456  |

> 也可点「注册」新建账号（新用户送 5 元优惠券）。

---

## 🧱 项目结构

```
smart-mall/
├── app.py          # Web 服务器（REST API + 静态文件，标准库 http.server）
├── mall.py         # 核心业务逻辑（商品/用户/购买/优惠券/灰度/备份）
├── payment.py      # 支付网关（余额/支付宝/微信/银行卡）
├── ai.py           # 销量预测（最小二乘）/ AI 推荐 / 灰度
├── cat.py          # 小猫情绪系统
├── models.py       # 数据模型（Product/User/Order/PaymentRecord）
├── storage.py      # JSON 持久化（原子写入 + 管理员密码 admin.txt）
├── static/         # 前端（index.html / styles.css / app.js）
├── data/           # 运行后自动生成的数据（JSON）
├── requirements.txt
├── LICENSE         # MIT
└── README.md
```

---

## 📊 数据存储

数据以 JSON 存于 `data/`，原子写入（临时文件 + `os.replace`），防崩溃丢数据。

- `products.json` 商品 · `users.json` 用户 · `orders.json` 订单
- `counter.json` 订单号 · `payments.json` 支付流水 · `admin.txt` 管理员密码

管理员后台提供一键备份 / 恢复（备份到 `latest_backup/`）。

---

## 🔧 技术说明

- 后端：Python 标准库 `http.server`（`ThreadingHTTPServer`），RESTful JSON API
- 前端：原生 HTML/CSS/JS（零依赖，离线可用），单页应用
- 业务逻辑忠实对齐 shop_v3.c：优惠券 5/满200送5/满500送20、灰度默认关闭、最小二乘预测、AI 推荐（新用户 TOP3 / 老用户偏好+热销）

---

## 📄 许可证

[MIT License](LICENSE) © 2026 stoicwolf218
