/* =========================================================
 * 智能商城系统 —— 前端交互逻辑（原生 JS，零依赖，离线可用）
 * 后端：Python 标准库 http.server 提供的 JSON REST API
 * ========================================================= */

'use strict';

/* ---------------- 全局状态 ---------------- */
let session = null;            // { id, username, name, role, coupon, balance, ... }
let currentProduct = null;     // 支付弹窗当前商品
let editingProductId = null;   // 正在编辑的商品 id（null = 新增）
let productCache = {};         // 商品缓存：id -> 商品对象
let adminProducts = [];        // 管理员商品列表缓存

const SESSION_KEY = 'mall_user';

/* ---------------- 小工具 ---------------- */
const $ = (id) => document.getElementById(id);

function on(id, ev, fn) {
  const el = $(id);
  if (el) el.addEventListener(ev, fn);
}

function show(el) { if (el) el.classList.remove('hidden'); }
function hide(el) { if (el) el.classList.add('hidden'); }

// HTML 转义，防止 XSS
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

// 金额两位小数
function fmt(n) {
  const x = Number(n);
  return (isFinite(x) ? x : 0).toFixed(2);
}

function showError(id, msg) {
  const el = $(id);
  if (el) { el.textContent = msg; el.classList.remove('hidden'); }
}

function clearError(id) {
  const el = $(id);
  if (el) { el.textContent = ''; el.classList.add('hidden'); }
}

function setCat(emoji) {
  const el = $('cat-mood');
  if (!el) return;
  const emojiEl = el.querySelector('.mood-emoji');
  if (emojiEl) emojiEl.textContent = emoji;
}

// 统一请求：自动序列化 JSON、解析 JSON，失败返回 {ok:false,message}
async function fetchJSON(url, options = {}) {
  const opts = Object.assign({}, options, {
    headers: Object.assign({ 'Content-Type': 'application/json' }, options.headers || {}),
  });
  if (opts.body && typeof opts.body === 'object') opts.body = JSON.stringify(opts.body);
  try {
    const res = await fetch(url, opts);
    return await res.json();
  } catch (e) {
    return { ok: false, message: '网络错误：' + e.message };
  }
}

/* ---------------- session ---------------- */
function saveSession(s) { localStorage.setItem(SESSION_KEY, JSON.stringify(s)); }
function loadSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null'); } catch (e) { return null; }
}
function clearSession() { localStorage.removeItem(SESSION_KEY); }

async function refreshSession() {
  if (!session) return;
  const data = await fetchJSON('/api/user/' + session.id + '/info');
  if (data.ok && data.user) {
    session = Object.assign({}, data.user, { role: session.role });
    saveSession(session);
  }
}

/* ---------------- 视图切换 ---------------- */
function switchForm(which) {
  const loginForm = $('login-form'), regForm = $('register-form');
  const gotoReg = $('goto-register'), gotoLogin = $('goto-login');
  if (which === 'register') {
    hide(loginForm); show(regForm);
    if (gotoReg) hide(gotoReg);
    if (gotoLogin) show(gotoLogin);
  } else {
    show(loginForm); hide(regForm);
    if (gotoReg) show(gotoReg);
    if (gotoLogin) hide(gotoLogin);
  }
}

function showView(view) {
  const loginView = $('view-login');
  const buyer = $('view-buyer'), admin = $('view-admin');

  if (loginView) loginView.classList.toggle('hidden', view !== 'login');
  if (buyer) buyer.classList.toggle('hidden', view !== 'buyer');
  if (admin) admin.classList.toggle('hidden', view !== 'admin');

  if (view === 'login') {
    switchForm('login');
    return;
  }

  if (view === 'buyer') {
    if (session && $('buyer-name')) $('buyer-name').textContent = session.name || session.username;
    switchBuyerTab('shop');
  } else {
    switchAdminTab('products');
  }
}

function switchBuyerTab(tab) {
  ['shop', 'orders', 'me'].forEach((t) => {
    const panel = $('tab-' + t), btn = $('tab-' + t + '-btn');
    if (panel) panel.classList.toggle('hidden', t !== tab);
    if (btn) btn.classList.toggle('active', t === tab);
  });
  if (tab === 'shop') {
    loadProducts($('search-input') ? $('search-input').value.trim() : '');
    loadRecommend();
  } else if (tab === 'orders') {
    loadOrders();
  } else if (tab === 'me') {
    loadMe();
  }
}

function switchAdminTab(tab) {
  ['products', 'users', 'data'].forEach((t) => {
    const panel = $('tab-' + t), btn = $('tab-' + t + '-btn');
    if (panel) panel.classList.toggle('hidden', t !== tab);
    if (btn) btn.classList.toggle('active', t === tab);
  });
  if (tab === 'products') loadAdminProducts();
  else if (tab === 'users') loadAdminUsers();
  else if (tab === 'data') loadPayments();
}

/* ---------------- 登录 / 注册 ---------------- */
async function handleLogin() {
  const username = ($('login-username') ? $('login-username').value : '').trim();
  const password = $('login-password') ? $('login-password').value : '';
  if (!username || !password) { showError('login-error', '请输入用户名和密码'); return; }
  clearError('login-error');

  const data = await fetchJSON('/api/login', { method: 'POST', body: { username, password } });
  if (!data.ok) { showError('login-error', data.message || '登录失败'); setCat('😿'); return; }

  session = Object.assign({}, data.user || {}, { role: data.role });
  saveSession(session);
  setCat('😺');
  if ($('login-password')) $('login-password').value = '';

  if (session.role === 'admin') showView('admin');
  else showView('buyer');
}

async function handleRegister() {
  const username = ($('register-username') ? $('register-username').value : '').trim();
  const password = $('register-password') ? $('register-password').value : '';
  const name = ($('register-name') ? $('register-name').value : '').trim();
  if (!username || !password || !name) { showError('register-error', '请完整填写用户名、密码和姓名'); return; }
  clearError('register-error');

  const isStudent = $('register-student') ? $('register-student').checked : false;

  const data = await fetchJSON('/api/register', { method: 'POST', body: { username, password, name, is_student: isStudent } });
  if (!data.ok) { showError('register-error', data.message || '注册失败'); return; }

  alert(data.message || '注册成功，请登录');
  switchForm('login');
  if ($('login-username')) $('login-username').value = username;
  if ($('register-password')) $('register-password').value = '';
  if ($('register-student')) $('register-student').checked = false;
}

function logout() {
  clearSession();
  session = null;
  showView('login');
}

/* ---------------- 买家：商品 ---------------- */
function cacheProducts(list, withQuantity) {
  (list || []).forEach((p) => {
    if (withQuantity) productCache[p.id] = p;
    else if (!productCache[p.id]) {
      productCache[p.id] = { id: p.id, name: p.name, category: p.category, price: p.price, quantity: 9999 };
    }
  });
}

async function loadProducts(search) {
  const q = search ? ('?search=' + encodeURIComponent(search)) : '';
  const data = await fetchJSON('/api/products' + q);
  if (!data.ok) { alert(data.message || '加载商品失败'); return; }
  renderProducts(data.products || []);
}

function renderProducts(products) {
  cacheProducts(products, true);
  const el = $('product-grid');
  if (!el) return;
  if (!products || !products.length) { el.innerHTML = '<p class="empty">暂无商品</p>'; return; }
  el.innerHTML = products.map((p) => `
    <div class="product-card">
      <h4>${esc(p.name)}</h4>
      <div class="product-cat">${esc(p.category)}</div>
      <div class="product-price">¥${fmt(p.price)}</div>
      <div class="product-stock">库存 ${p.quantity}</div>
      <button ${p.quantity > 0 ? `onclick="openPayment(${p.id})"` : 'disabled'}>购买</button>
    </div>
  `).join('');
}

async function loadRecommend() {
  if (!session) return;
  const data = await fetchJSON('/api/user/' + session.id + '/recommend');
  const el = $('recommend-grid');
  if (!el) return;
  if (!data.ok) { el.innerHTML = '<p class="empty">' + esc(data.message || '暂无推荐') + '</p>'; return; }
  renderRecommend(data.items || []);
}

function renderRecommend(items) {
  cacheProducts(items, false);
  const el = $('recommend-grid');
  if (!el) return;
  if (!items || !items.length) { el.innerHTML = '<p class="empty">暂无推荐</p>'; return; }
  el.innerHTML = items.map((it) => `
    <div class="product-card rec-card">
      ${it.tag ? `<span class="badge badge-${esc(it.tag)}">${esc(it.tag)}</span>` : ''}
      <h4>${esc(it.name)}</h4>
      <div class="product-cat">${esc(it.category)}</div>
      <div class="product-price">¥${fmt(it.price)}</div>
      <button onclick="openPayment(${it.id})">购买</button>
    </div>
  `).join('');
}

/* ---------------- 买家：购买 / 支付弹窗 ---------------- */
const PAY_METHODS = ['余额支付', '支付宝', '微信支付', '银行卡'];

function openPayment(productId) {
  const p = productCache[productId];
  if (!p) return;
  currentProduct = p;

  const coupon = (session && session.coupon) || 0;
  const isStudent = !!(session && session.is_student);
  if ($('pay-title')) $('pay-title').textContent = '购买 - ' + p.name;
  if ($('pay-product-info')) {
    $('pay-product-info').innerHTML = `
      <p>商品：${esc(p.name)}（${esc(p.category)}）</p>
      <p>单价：¥${fmt(p.price)}　库存：${p.quantity}${isStudent ? '　<span class="student-tag">🎓 学生 9 折</span>' : ''}</p>
      <label>数量：<input type="number" id="pay-qty" min="1" max="${p.quantity || 1}" value="1" oninput="updatePayTotal()"></label>
      <label><input type="checkbox" id="pay-coupon" onchange="updatePayTotal()"> 使用优惠券（当前 ¥${fmt(coupon)}）</label>
      <p>应付：<span id="pay-total">¥${fmt(p.price)}</span></p>
    `;
  }
  if ($('pay-methods')) {
    $('pay-methods').innerHTML = PAY_METHODS.map((m, i) =>
      `<label><input type="radio" name="pay-method" value="${m}" ${i === 0 ? 'checked' : ''}> ${m}</label>`
    ).join('');
  }
  const cardInput = $('pay-card-input');
  if (cardInput) { cardInput.value = ''; cardInput.classList.add('hidden'); }

  show($('payment-modal'));
  updatePayTotal();
}

function updatePayTotal() {
  if (!currentProduct) return;
  const qtyEl = $('pay-qty');
  const couponEl = $('pay-coupon');
  const totalEl = $('pay-total');
  if (!totalEl) return;

  const qty = parseInt(qtyEl ? qtyEl.value : '1', 10) || 1;
  const useCoupon = couponEl ? couponEl.checked : false;
  const original = currentProduct.price * qty;
  let total = original;
  let studentDiscount = 0;
  if (session && session.is_student) {
    studentDiscount = original * 0.10;
    total = original - studentDiscount;
  }
  let discount = 0;
  if (useCoupon && session && session.coupon > 0) discount = Math.min(session.coupon, total);
  const final = total - discount;
  const parts = [];
  if (studentDiscount > 0) parts.push('学生 9 折 -¥' + fmt(studentDiscount));
  if (discount > 0) parts.push('券抵¥' + fmt(discount));
  totalEl.textContent = '¥' + fmt(final) +
    (parts.length ? `（原价¥${fmt(original)}，${parts.join('，')}）` : '');
}

function closePayment() {
  hide($('payment-modal'));
  currentProduct = null;
}

async function confirmPayment() {
  if (!currentProduct || !session) return;
  const qtyEl = $('pay-qty');
  const qty = parseInt(qtyEl ? qtyEl.value : '0', 10) || 0;
  if (qty < 1) { alert('请输入正确的购买数量'); return; }

  const couponEl = $('pay-coupon');
  const useCoupon = couponEl ? couponEl.checked : false;
  const checkedMethod = document.querySelector('#pay-methods input[name="pay-method"]:checked');
  const method = checkedMethod ? checkedMethod.value : '余额支付';
  const cardInput = $('pay-card-input');
  const card_no = cardInput ? cardInput.value.trim() : '';

  const body = { user_id: session.id, product_id: currentProduct.id, qty, use_coupon: useCoupon, method };
  if (method === '银行卡') body.card_no = card_no;

  const data = await fetchJSON('/api/buy', { method: 'POST', body });
  if (!data.ok) { setCat('😿'); alert(data.message || '购买失败'); return; }

  setCat('😺');
  alert('购买成功！订单号 ' + data.order_id + (data.txn_id ? '，交易号 ' + data.txn_id : ''));
  closePayment();
  await refreshSession();
  if (session.role !== 'admin') {
    await loadProducts($('search-input') ? $('search-input').value.trim() : '');
    await loadRecommend();
    await loadMe();
  }
}

/* ---------------- 买家：订单 / 个人中心 ---------------- */
async function loadOrders() {
  if (!session) return;
  const data = await fetchJSON('/api/user/' + session.id + '/orders');
  const el = $('orders-list');
  if (!el) return;
  if (!data.ok) { el.innerHTML = '<p class="empty">' + esc(data.message || '加载订单失败') + '</p>'; return; }
  const orders = data.orders || [];
  if (!orders.length) { el.innerHTML = '<p class="empty">暂无订单</p>'; return; }
  el.innerHTML = orders.map((o) => `
    <div class="order-item">
      <div class="order-head"><span>订单号 ${esc(o.order_id)}</span><span>${esc(o.order_date || '')}</span></div>
      <div>${esc(o.product_name)} × ${o.quantity}</div>
      <div>单价 ¥${fmt(o.price)}　合计 ¥${fmt(o.total)}　支付方式：${esc(o.payment_method || '')}</div>
    </div>
  `).join('');
}

async function loadMe() {
  if (!session) return;
  const data = await fetchJSON('/api/user/' + session.id + '/info');
  if (!data.ok) { alert(data.message || '加载个人信息失败'); return; }
  const u = data.user;
  if (u) {
    session = Object.assign({}, u, { role: session.role });
    saveSession(session);
    if ($('buyer-name')) $('buyer-name').textContent = u.name || u.username;
  }
  renderMe(u);
}

function renderMe(u) {
  const el = $('me-info');
  if (!el || !u) return;
  el.innerHTML = `
    <p>姓名：${esc(u.name)}（${esc(u.username)}）</p>
    <p>余额：¥${fmt(u.balance)}　优惠券：¥${fmt(u.coupon)}</p>
    <p>身份：${u.is_student ? '🎓 学生（购物 9 折）' : '普通用户'}${u.is_vip ? ' · VIP 会员' : ''}</p>
    <p>累计消费：¥${fmt(u.total_spent)}　订单数：${u.order_count}</p>
    <p>注册时间：${esc(u.register_date || '')}</p>
  `;
}

async function recharge() {
  if (!session) return;
  const el = $('recharge-amount');
  const amount = parseFloat(el ? el.value : '');
  if (!(amount > 0)) { alert('请输入正确的充值金额'); return; }
  const data = await fetchJSON('/api/user/' + session.id + '/recharge', { method: 'POST', body: { amount } });
  if (!data.ok) { alert(data.message || '充值失败'); return; }
  alert(data.message || '充值成功');
  if (el) el.value = '';
  await loadMe();
}

async function changePassword() {
  if (!session) return;
  const oldPw = $('old-pw') ? $('old-pw').value : '';
  const newPw = $('new-pw') ? $('new-pw').value : '';
  if (!oldPw || !newPw) { alert('请填写原密码和新密码'); return; }
  const data = await fetchJSON('/api/user/' + session.id + '/change_password', { method: 'POST', body: { old: oldPw, new: newPw } });
  if (!data.ok) { alert(data.message || '修改失败'); return; }
  alert(data.message || '修改成功');
  if ($('old-pw')) $('old-pw').value = '';
  if ($('new-pw')) $('new-pw').value = '';
}

/* ---------------- 管理员：商品 ---------------- */
async function loadAdminProducts() {
  const data = await fetchJSON('/api/products?all=1');
  if (!data.ok) { alert(data.message || '加载商品失败'); return; }
  renderAdminProducts(data.products || []);
}

function renderAdminProducts(products) {
  adminProducts = products || [];
  const el = $('admin-product-tbody');
  if (!el) return;
  if (!adminProducts.length) { el.innerHTML = '<tr><td colspan="8">暂无商品</td></tr>'; return; }
  el.innerHTML = adminProducts.map((p) => {
    const status = p.is_expired
      ? '<span class="status expired">已过期</span>'
      : (p.is_on_sale ? '<span class="status on">在售</span>' : '<span class="status off">已下架</span>');
    return `<tr>
      <td>${p.id}</td>
      <td>${esc(p.category)}</td>
      <td>${esc(p.name)}</td>
      <td>¥${fmt(p.price)}</td>
      <td>${esc(p.expired_date || '')}</td>
      <td>${p.quantity}</td>
      <td>${status}</td>
      <td><button onclick="adminEditProduct(${p.id})">编辑</button> <button onclick="adminDeleteProduct(${p.id})">删除</button></td>
    </tr>`;
  }).join('');
}

function field(name) {
  const f = $('product-form');
  if (!f) return null;
  let el = f.elements ? f.elements[name] : null;
  if (!el) el = f.querySelector('[name="' + name + '"]');
  return el || null;
}

function setField(name, val) {
  const el = field(name);
  if (el && val !== undefined && val !== null) el.value = val;
}

function fillProductForm(p) {
  setField('category', p.category);
  setField('name', p.name);
  setField('price', p.price);
  setField('year', p.year);
  setField('month', p.month);
  setField('day', p.day);
  setField('shelf_life', p.shelf_life);
  setField('quantity', p.quantity);
  const os = field('is_on_sale');
  if (os) os.checked = !!p.is_on_sale;
}

function readProductForm() {
  const str = (n) => { const el = field(n); return el ? el.value.trim() : ''; };
  const num = (n) => { const v = parseFloat(str(n)); return isNaN(v) ? 0 : v; };
  const intv = (n) => { const v = parseInt(str(n), 10); return isNaN(v) ? 0 : v; };
  const os = field('is_on_sale');
  const onSale = os ? (os.type === 'checkbox' ? os.checked : (os.value === '1' || os.value === 'true' || os.value === 'on')) : true;
  // 后端新增用 is_on_sale、编辑用 on_sale，两者都传以兼容
  return {
    category: str('category'), name: str('name'), price: num('price'),
    year: intv('year'), month: intv('month'), day: intv('day'),
    shelf_life: intv('shelf_life'), quantity: intv('quantity'),
    is_on_sale: onSale, on_sale: onSale,
  };
}

function resetProductForm() {
  const f = $('product-form');
  if (f && f.reset) f.reset();
}

function adminEditProduct(id) {
  const p = adminProducts.find((x) => x.id === id);
  if (!p) return;
  editingProductId = id;
  fillProductForm(p);
  show($('product-form'));
}

async function adminDeleteProduct(id) {
  if (!confirm('确定删除该商品？')) return;
  const data = await fetchJSON('/api/admin/products/' + id, { method: 'DELETE' });
  if (!data.ok) { alert(data.message || '删除失败'); return; }
  alert(data.message || '删除成功');
  await loadAdminProducts();
}

async function saveProduct() {
  const p = readProductForm();
  if (!p.name || !p.category) { alert('请填写商品分类和名称'); return; }
  if (!(p.price >= 0)) { alert('请填写正确的价格'); return; }

  let data;
  if (editingProductId) {
    data = await fetchJSON('/api/admin/products/' + editingProductId, { method: 'PUT', body: p });
  } else {
    data = await fetchJSON('/api/admin/products', { method: 'POST', body: p });
  }
  if (!data.ok) { alert(data.message || '保存失败'); return; }
  alert(data.message || '保存成功');
  editingProductId = null;
  resetProductForm();
  hide($('product-form'));
  await loadAdminProducts();
}

/* ---------------- 管理员：过期 / 下架操作 ---------------- */
async function checkExpired() {
  const data = await fetchJSON('/api/admin/products/check_expired', { method: 'POST' });
  alert(data.ok ? ('检测完成，新标记 ' + data.count + ' 件商品已过期') : (data.message || '操作失败'));
  await loadAdminProducts();
}
async function clearZero() {
  if (!confirm('确定下架所有库存为 0 的商品？')) return;
  const data = await fetchJSON('/api/admin/products/clear_zero', { method: 'POST' });
  alert(data.ok ? ('已下架 ' + data.count + ' 件零库存商品') : (data.message || '操作失败'));
  await loadAdminProducts();
}
async function clearExpired() {
  if (!confirm('确定下架所有过期商品？')) return;
  const data = await fetchJSON('/api/admin/products/clear_expired', { method: 'POST' });
  alert(data.ok ? ('已下架 ' + data.count + ' 件过期商品') : (data.message || '操作失败'));
  await loadAdminProducts();
}

/* ---------------- 管理员：用户 ---------------- */
async function loadAdminUsers() {
  const data = await fetchJSON('/api/admin/users');
  const el = $('admin-user-table');
  if (!el) return;
  if (!data.ok) { el.innerHTML = '<p class="error">' + esc(data.message || '加载失败') + '</p>'; return; }
  const users = data.users || [];
  const rows = users.map((u) => `
    <tr>
      <td>${u.id}</td>
      <td>${esc(u.username)}</td>
      <td>${esc(u.name)}</td>
      <td>¥${fmt(u.balance)}</td>
      <td>¥${fmt(u.coupon)}</td>
      <td>¥${fmt(u.total_spent)}</td>
      <td>${u.order_count}</td>
      <td>${u.is_vip ? '是' : '否'}</td>
      <td>
        <button onclick="adminRechargeUser(${u.id})">充值</button>
        <button onclick="adminCouponUser(${u.id})">发券</button>
        <button onclick="adminDeleteUser(${u.id})">删除</button>
      </td>
    </tr>`).join('');
  el.innerHTML = `<table class="data-table">
    <thead><tr><th>ID</th><th>用户名</th><th>姓名</th><th>余额</th><th>优惠券</th><th>累计消费</th><th>订单数</th><th>VIP</th><th>操作</th></tr></thead>
    <tbody>${rows || '<tr><td colspan="9">暂无用户</td></tr>'}</tbody>
  </table>`;
}

async function adminRechargeUser(id) {
  const amount = parseFloat(prompt('请输入充值金额：') || '');
  if (!(amount > 0)) { alert('金额无效'); return; }
  const data = await fetchJSON('/api/admin/users/' + id + '/recharge', { method: 'POST', body: { amount } });
  if (!data.ok) { alert(data.message || '充值失败'); return; }
  alert(data.message || '充值成功');
  await loadAdminUsers();
}

async function adminCouponUser(id) {
  const amount = parseFloat(prompt('请输入发券金额：') || '');
  if (!(amount > 0)) { alert('金额无效'); return; }
  const data = await fetchJSON('/api/admin/users/' + id + '/coupon', { method: 'POST', body: { amount } });
  if (!data.ok) { alert(data.message || '发券失败'); return; }
  alert(data.message || '发券成功');
  await loadAdminUsers();
}

async function adminDeleteUser(id) {
  if (!confirm('确定删除该用户？')) return;
  const data = await fetchJSON('/api/admin/users/' + id, { method: 'DELETE' });
  if (!data.ok) { alert(data.message || '删除失败'); return; }
  alert(data.message || '删除成功');
  await loadAdminUsers();
}

/* ---------------- 管理员：数据页 ---------------- */
async function predict() {
  const el = $('predict-product-id');
  const pid = parseInt(el ? el.value : '', 10);
  if (!pid) { alert('请输入商品 ID'); return; }
  const data = await fetchJSON('/api/predict?product_id=' + pid);
  renderPredict(data.ok ? data.result : { ok: false, message: data.message });
}

function renderPredict(r) {
  const el = $('predict-result');
  if (!el) return;
  if (!r || r.ok === false) {
    el.innerHTML = '<p class="error">' + esc((r && r.message) || '无法预测') + '</p>';
    return;
  }
  const days = (r.daily || []).map((d) => `<li>第 ${d.day} 天：预计 ${d.pred} 件</li>`).join('');
  el.innerHTML = `
    <p>商品 #${r.product_id}：历史共售 <strong>${r.total_sold}</strong> 件，日均 ${r.avg} 件，趋势 ${esc(r.trend)}（斜率 ${r.slope}）</p>
    <p>未来 7 天预测合计 <strong>${r.total_predict}</strong> 件，建议备货 <strong>${r.suggest_stock}</strong> 件</p>
    <ul>${days}</ul>
    ${r.note ? '<p class="note">' + esc(r.note) + '</p>' : ''}
  `;
}

async function setGray() {
  const el = $('gray-input');
  const percent = parseInt(el ? el.value : '', 10);
  if (isNaN(percent)) { alert('请输入灰度比例'); return; }
  const data = await fetchJSON('/api/admin/gray', { method: 'POST', body: { percent } });
  alert(data.message || '设置失败');
}

async function loadPayments() {
  const data = await fetchJSON('/api/admin/payments');
  const el = $('payments-table');
  if (!el) return;
  if (!data.ok) { el.innerHTML = '<p class="error">' + esc(data.message || '加载失败') + '</p>'; return; }
  const payments = data.payments || [];
  const rows = payments.map((p) => `
    <tr><td>${esc(p.transaction_id)}</td><td>${p.order_id}</td><td>¥${fmt(p.amount)}</td><td>${esc(p.method)}</td><td>${esc(p.status)}</td><td>${esc(p.time)}</td></tr>`).join('');
  el.innerHTML = `<table class="data-table">
    <thead><tr><th>交易号</th><th>订单号</th><th>金额</th><th>支付方式</th><th>状态</th><th>时间</th></tr></thead>
    <tbody>${rows || '<tr><td colspan="6">暂无流水</td></tr>'}</tbody>
  </table>`;
}

async function backup() {
  const data = await fetchJSON('/api/admin/backup', { method: 'POST' });
  alert(data.message || '备份失败');
}

async function restore() {
  if (!confirm('确定从 latest_backup/ 恢复数据？当前数据将被覆盖。')) return;
  const data = await fetchJSON('/api/admin/restore', { method: 'POST' });
  alert(data.message || '恢复失败');
  if (data.ok) { await loadAdminProducts(); await loadAdminUsers(); await loadPayments(); }
}

async function adminChangePassword() {
  const oldPw = $('admin-old-pw') ? $('admin-old-pw').value : '';
  const newPw = $('admin-new-pw') ? $('admin-new-pw').value : '';
  if (!oldPw || !newPw) { alert('请填写原密码和新密码'); return; }
  const data = await fetchJSON('/api/admin/password', { method: 'POST', body: { old: oldPw, new: newPw } });
  if (!data.ok) { alert(data.message || '修改失败'); return; }
  alert(data.message || '修改成功');
  if ($('admin-old-pw')) $('admin-old-pw').value = '';
  if ($('admin-new-pw')) $('admin-new-pw').value = '';
}

/* ---------------- 初始化 ---------------- */
function init() {
  // 登录/注册切换
  on('to-register', 'click', () => switchForm('register'));
  on('to-login', 'click', () => switchForm('login'));
  on('login-btn', 'click', handleLogin);
  on('register-btn', 'click', handleRegister);
  // 阻止表单默认提交刷新页面（真正的提交由上面的按钮/函数处理）
  on('login-form', 'submit', (e) => e.preventDefault());
  on('register-form', 'submit', (e) => e.preventDefault());
  on('login-username', 'keydown', (e) => { if (e.key === 'Enter') handleLogin(); });
  on('login-password', 'keydown', (e) => { if (e.key === 'Enter') handleLogin(); });

  // 登出
  on('btn-logout', 'click', logout);

  // 买家 tab / 搜索 / 充值 / 改密
  on('tab-shop-btn', 'click', () => switchBuyerTab('shop'));
  on('tab-orders-btn', 'click', () => switchBuyerTab('orders'));
  on('tab-me-btn', 'click', () => switchBuyerTab('me'));
  on('search-btn', 'click', () => loadProducts($('search-input') ? $('search-input').value.trim() : ''));
  on('search-input', 'keydown', (e) => { if (e.key === 'Enter') loadProducts(e.target.value.trim()); });
  on('recharge-btn', 'click', recharge);
  on('change-pw-btn', 'click', changePassword);

  // 管理员 tab / 商品表单 / 过期 / 用户 / 数据
  on('tab-products-btn', 'click', () => switchAdminTab('products'));
  on('tab-users-btn', 'click', () => switchAdminTab('users'));
  on('tab-data-btn', 'click', () => switchAdminTab('data'));
  on('add-product-btn', 'click', () => {
    editingProductId = null;
    resetProductForm();
    show($('product-form'));
  });
  on('product-form', 'submit', (e) => { e.preventDefault(); saveProduct(); });
  on('btn-check-expired', 'click', checkExpired);
  on('btn-clear-zero', 'click', clearZero);
  on('btn-clear-expired', 'click', clearExpired);
  on('predict-btn', 'click', predict);
  on('gray-btn', 'click', setGray);
  on('backup-btn', 'click', backup);
  on('restore-btn', 'click', restore);
  on('admin-change-pw-btn', 'click', adminChangePassword);

  // 支付弹窗
  on('pay-confirm', 'click', confirmPayment);
  on('pay-cancel', 'click', closePayment);
  on('pay-methods', 'change', (e) => {
    if (e.target.name === 'pay-method') {
      const cardInput = $('pay-card-input');
      if (cardInput) cardInput.classList.toggle('hidden', e.target.value !== '银行卡');
    }
  });

  // 初始路由：无 session 显示登录页，否则进入对应视图
  session = loadSession();
  if (session) {
    setCat('😺');
    if (session.role === 'admin') showView('admin');
    else showView('buyer');
  } else {
    showView('login');
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
