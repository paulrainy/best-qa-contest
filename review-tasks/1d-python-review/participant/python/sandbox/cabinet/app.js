// Кабинет инвестора: одна страница, данные — из API invest-api
const STATUS = { NEW: 'Новое', EXECUTED: 'Исполнено' };
const ORDER_TYPE = { REFILL: 'Пополнение', WITHDRAW: 'Вывод' };
const AGREEMENT_TYPE = { BROKER: 'Брокерский договор', IIS: 'ИИС' };
const REPORT_STATUS = { ORDERED: 'Заказана', READY: 'Готова' };
const TARIFF = { INVESTOR: 'Инвестор', TRADER: 'Трейдер' };

const app = document.getElementById('app');
const notice = document.getElementById('notice');
let poller = null;

function token() { return sessionStorage.getItem('token'); }

async function api(method, path, body) {
  const response = await fetch('/api/v1' + path, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token() ? { Authorization: 'Bearer ' + token() } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();
  if (response.status === 401 && token()) { logout(); }
  if (!response.ok) { throw new Error(data.errorMessage || 'Ошибка ' + response.status); }
  return data;
}

function money(value) {
  const [int, frac] = Number(value).toFixed(2).split('.');
  return int.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ',' + frac + ' ₽';
}

function esc(text) {
  return String(text ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

function show(message, isError) {
  notice.textContent = message;
  notice.className = isError ? 'error' : '';
  notice.hidden = false;
}

function hideNotice() { notice.hidden = true; notice.textContent = ''; }

function logout() {
  sessionStorage.removeItem('token');
  location.hash = '#/login';
}

document.getElementById('logout').addEventListener('click', logout);

async function renderHeader() {
  const header = document.getElementById('header');
  header.hidden = !token();
  if (token()) {
    const profile = await api('GET', '/profile');
    header.querySelector('[data-testid=client-name]').textContent =
      [profile.lastName, profile.firstName, profile.middleName].filter(Boolean).join(' ');
  }
}

function renderLogin() {
  app.innerHTML = `
    <div class="card">
      <h1>Вход в кабинет</h1>
      <form id="login-form">
        <label for="login">Логин</label><input id="login" autocomplete="username">
        <label for="password">Пароль</label><input id="password" type="password" autocomplete="current-password">
        <div class="actions"><button type="submit">Войти</button></div>
      </form>
    </div>`;
  document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const data = await api('POST', '/auth/login', {
        login: document.getElementById('login').value, password: document.getElementById('password').value });
      sessionStorage.setItem('token', data.token);
      hideNotice();
      location.hash = '#/agreements';
    } catch (err) { show(err.message, true); }
  });
}

async function renderAgreements() {
  const agreements = await api('GET', '/agreements');
  app.innerHTML = `
    <h1>Мои договоры</h1>
    <div class="card"><table data-testid="agreements">
      <thead><tr><th>Договор</th><th>Тип</th><th>Остаток</th></tr></thead>
      <tbody>${agreements.map(a => `
        <tr data-testid="agreement-row">
          <td><a href="#/agreements/${a.id}">${esc(a.number)}</a></td>
          <td>${AGREEMENT_TYPE[a.type]}</td>
          <td data-testid="agreement-row-balance">${money(a.balance)}</td>
        </tr>`).join('')}</tbody>
    </table></div>`;
}

async function renderAgreement(id) {
  const agreement = await api('GET', '/agreements/' + id);
  app.innerHTML = `
    <h1>Договор ${esc(agreement.number)}</h1>
    <div class="card">
      Остаток: <span class="balance" data-testid="agreement-balance">${money(agreement.balance)}</span>
      <div class="actions">
        <button type="button" data-kind="refill">Пополнить</button>
        <button type="button" data-kind="withdraw" class="secondary">Вывести</button>
      </div>
      <form id="order-form" hidden>
        <label for="amount">Сумма, ₽</label><input id="amount" inputmode="decimal">
        <div class="actions">
          <button type="submit">Создать поручение</button>
          <button type="button" class="secondary" id="order-cancel">Отмена</button>
        </div>
      </form>
    </div>
    <div class="card"><h2>История поручений</h2><table data-testid="orders">
      <thead><tr><th>Дата</th><th>Операция</th><th>Сумма</th><th>Статус</th></tr></thead><tbody></tbody>
    </table></div>`;
  const form = document.getElementById('order-form');
  let kind = null;
  app.querySelectorAll('[data-kind]').forEach(button => button.addEventListener('click', () => {
    kind = button.dataset.kind;
    form.hidden = false;
    document.getElementById('amount').focus();
  }));
  document.getElementById('order-cancel').addEventListener('click', () => { form.hidden = true; });
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const amount = document.getElementById('amount').value.replace(/\s/g, '').replace(',', '.');
    try {
      await api('POST', `/agreements/${id}/${kind}`, { amount });
      show(kind === 'refill' ? 'Поручение на пополнение создано' : 'Поручение на вывод создано');
      form.hidden = true;
      document.getElementById('amount').value = '';
      await refreshAgreement(id);
    } catch (err) { show(err.message, true); }
  });
  await refreshAgreement(id);
  poller = setInterval(() => refreshAgreement(id).catch(() => {}), 1000);
}

async function refreshAgreement(id) {
  const [agreement, orders] = await Promise.all([api('GET', '/agreements/' + id), api('GET', `/agreements/${id}/orders`)]);
  const balance = app.querySelector('[data-testid=agreement-balance]');
  const body = app.querySelector('[data-testid=orders] tbody');
  if (!balance || !body) return;
  balance.textContent = money(agreement.balance);
  body.innerHTML = orders.map(o => `
    <tr data-testid="order-row">
      <td>${esc(o.createdAt)}</td><td>${ORDER_TYPE[o.type]}</td><td>${money(o.amount)}</td>
      <td data-testid="order-status">${STATUS[o.status]}</td>
    </tr>`).join('');
}

async function renderTaxReports() {
  const year = new Date().getFullYear();
  const years = [1, 2, 3, 4, 5].map(i => year - i);
  app.innerHTML = `
    <h1>Справки НДФЛ</h1>
    <div class="card"><form id="report-form">
      <label for="year">Год</label>
      <select id="year">${years.map(y => `<option value="${y}">${y}</option>`).join('')}</select>
      <div class="actions"><button type="submit">Заказать справку</button></div>
    </form></div>
    <div class="card"><table data-testid="tax-reports">
      <thead><tr><th>Год</th><th>Статус</th><th>Заказана</th></tr></thead><tbody></tbody>
    </table></div>`;
  document.getElementById('report-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const taxPeriod = Number(document.getElementById('year').value);
    try {
      await api('POST', '/tax-reports', { taxPeriod });
      show(`Справка за ${taxPeriod} год заказана`);
      await refreshTaxReports();
    } catch (err) { show(err.message, true); }
  });
  await refreshTaxReports();
  poller = setInterval(() => refreshTaxReports().catch(() => {}), 1000);
}

async function refreshTaxReports() {
  const reports = await api('GET', '/tax-reports');
  const body = app.querySelector('[data-testid=tax-reports] tbody');
  if (!body) return;
  body.innerHTML = reports.map(r => `
    <tr data-testid="tax-report-row">
      <td>${r.taxPeriod}</td><td data-testid="tax-report-status">${REPORT_STATUS[r.status]}</td><td>${esc(r.registeredAt)}</td>
    </tr>`).join('');
}

async function renderProfile() {
  const profile = await api('GET', '/profile');
  const target = profile.tariff === 'INVESTOR' ? 'TRADER' : 'INVESTOR';
  app.innerHTML = `
    <h1>Профиль</h1>
    <div class="card"><dl>
      <dt>ФИО</dt><dd>${esc([profile.lastName, profile.firstName, profile.middleName].filter(Boolean).join(' '))}</dd>
      <dt>Логин</dt><dd>${esc(profile.login)}</dd>
      <dt>Телефон</dt><dd>${esc(profile.phone)}</dd>
      <dt>Тариф</dt><dd data-testid="profile-tariff">${TARIFF[profile.tariff]}</dd>
    </dl>
    <div class="actions"><button type="button" id="change-tariff">Перейти на тариф «${TARIFF[target]}»</button></div></div>`;
  document.getElementById('change-tariff').addEventListener('click', async () => {
    if (!confirm(`Сменить тариф на «${TARIFF[target]}»?`)) return;
    try {
      await api('PATCH', '/profile/tariff', { tariff: target });
      await renderProfile();
      show(`Тариф изменён на «${TARIFF[target]}»`);
    } catch (err) { show(err.message, true); }
  });
}

async function route() {
  clearInterval(poller);
  const hash = location.hash || '#/agreements';
  if (!token() && hash !== '#/login') { location.hash = '#/login'; return; }
  try {
    await renderHeader();
    const agreement = hash.match(/^#\/agreements\/(\d+)$/);
    if (hash === '#/login') renderLogin();
    else if (agreement) await renderAgreement(agreement[1]);
    else if (hash === '#/tax-reports') await renderTaxReports();
    else if (hash === '#/profile') await renderProfile();
    else await renderAgreements();
  } catch (err) { show(err.message, true); }
}

window.addEventListener('hashchange', () => { hideNotice(); route(); });
route();
