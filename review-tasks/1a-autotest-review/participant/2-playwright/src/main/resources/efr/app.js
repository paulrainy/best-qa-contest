'use strict';

// Заглушка ЕФР: вход, поиск клиента по паспорту, продуктовый профиль и карточка карты.
// Элементы помечены атрибутом data-testid — его по умолчанию ищет getByTestId в Playwright.

const API = 'api/';
const BLOCK_REASONS = ['Утеря', 'Кража', 'Компрометация', 'Подозрение на мошенничество'];
const REISSUE_REASONS = ['Повреждение', 'Истечение срока действия', 'Смена фамилии'];

const state = {
    client: null,
    card: null,
    tab: 'overview',
    busy: false,
    pollTimer: null,
    notificationTimer: null,
};

// ---------- Общее ----------

function session() {
    try {
        return JSON.parse(sessionStorage.getItem('efr.session'));
    } catch (e) {
        return null;
    }
}

async function api(path, options = {}) {
    const headers = {'Content-Type': 'application/json'};
    const s = session();
    if (s) headers.Authorization = 'Bearer ' + s.token;
    const response = await fetch(API + path, {
        method: options.method || 'GET',
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (response.status === 401 && s) {
        sessionStorage.removeItem('efr.session');
        navigate('#/login');
    }
    if (!response.ok) throw new Error(data.error || 'Ошибка ' + response.status);
    return data;
}

function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
        if (value === null || value === undefined || value === false) continue;
        if (key.startsWith('on')) el.addEventListener(key.substring(2), value);
        else if (key === 'className') el.className = value;
        else el.setAttribute(key, value === true ? '' : value);
    }
    for (const child of children.flat()) {
        if (child === null || child === undefined || child === false) continue;
        el.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return el;
}

function statusClass(status) {
    return {
        'Заблокирована': 'blocked',
        'Временно заблокирована': 'blocked',
        'Закрыта': 'closed',
        'В обработке': 'pending',
        'Обработка…': 'pending',
    }[status] || '';
}

function notify(text, kind) {
    const root = document.getElementById('notification-root');
    clearTimeout(state.notificationTimer);
    root.replaceChildren(h('div', {'data-testid': 'notification', role: 'alert', className: 'notification ' + kind}, text));
    state.notificationTimer = setTimeout(() => root.replaceChildren(), 8000);
}

// Смена маршрута: если адрес не меняется, hashchange не придёт — перерисовываем сами
function navigate(hash) {
    if (location.hash === hash) route();
    else location.hash = hash;
}

function closeOverlay() {
    document.getElementById('overlay-root').replaceChildren();
}

// ---------- Маршруты ----------

window.addEventListener('hashchange', route);
document.addEventListener('click', (e) => {
    if (!e.target.closest('[role=menu]') && !e.target.closest('[data-testid=actionsButton]')) closeMenu();
});

function route() {
    clearInterval(state.pollTimer);
    const s = session();
    renderUser(s);
    if (!s) {
        renderLogin();
        return;
    }
    const match = location.hash.match(/^#\/client\/(\d+)(?:\/card\/(\d{16}))?$/);
    if (match) {
        renderClient(match[1], match[2]);
    } else {
        renderSearch(null);
    }
}

function renderUser(s) {
    const el = document.getElementById('user');
    el.replaceChildren();
    if (s) {
        el.append(s.fullName + ' (' + s.login + ')', h('button', {
            onclick: () => {
                sessionStorage.removeItem('efr.session');
                navigate('#/login');
            }
        }, 'Выйти'));
    }
}

// ---------- Вход ----------

function renderLogin() {
    const error = h('div', {className: 'dialog-error', 'data-testid': 'loginError'});
    const form = h('form', {className: 'panel login', 'data-testid': 'login'},
        h('h1', {}, 'Вход в песочницу'),
        h('div', {className: 'field'}, h('label', {for: 'login'}, 'Логин'), h('input', {id: 'login', name: 'login', autocomplete: 'username'})),
        h('div', {className: 'field'}, h('label', {for: 'password'}, 'Пароль'), h('input', {id: 'password', name: 'password', type: 'password', autocomplete: 'current-password'})),
        error,
        h('button', {type: 'submit', className: 'primary'}, 'Войти'));
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        error.textContent = '';
        try {
            const s = await api('login', {method: 'POST', body: {login: form.login.value, password: form.password.value}});
            sessionStorage.setItem('efr.session', JSON.stringify(s));
            navigate('#/search');
        } catch (err) {
            error.textContent = err.message;
        }
    });
    document.getElementById('app').replaceChildren(form);
}

// ---------- Поиск клиента ----------

function searchForm() {
    const error = h('span', {className: 'search-error', 'data-testid': 'searchError'});
    const form = h('form', {className: 'panel search', 'data-testid': 'clientSearch'},
        h('div', {className: 'field'}, h('label', {for: 'passportSeries'}, 'Серия паспорта'), h('input', {id: 'passportSeries', name: 'passportSeries', maxlength: 4})),
        h('div', {className: 'field'}, h('label', {for: 'passportNumber'}, 'Номер паспорта'), h('input', {id: 'passportNumber', name: 'passportNumber', maxlength: 6})),
        h('button', {type: 'submit', className: 'primary'}, 'Найти'),
        error);
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        error.textContent = 'Поиск…';
        try {
            const params = new URLSearchParams({series: form.passportSeries.value.trim(), number: form.passportNumber.value.trim()});
            const client = await api('clients/search?' + params);
            navigate('#/client/' + client.clientId);
        } catch (err) {
            error.textContent = err.message;
        }
    });
    return form;
}

function renderSearch() {
    document.getElementById('app').replaceChildren(searchForm());
}

// ---------- Продуктовый профиль ----------

async function renderClient(clientId, cardDigits) {
    const app = document.getElementById('app');
    const profileSlot = h('div', {}, h('div', {className: 'panel loading'}, 'Загрузка профиля…'));
    const cardSlot = h('div', {});
    state.card = null;
    app.replaceChildren(searchForm(), h('div', {className: 'layout'}, profileSlot, cardSlot));
    try {
        state.client = await api('clients/' + clientId);
    } catch (err) {
        profileSlot.replaceChildren(h('div', {className: 'panel'}, err.message));
        return;
    }
    profileSlot.replaceChildren(productProfile(cardDigits));
    startPolling(clientId, cardDigits, profileSlot);

    if (cardDigits) {
        cardSlot.replaceChildren(h('div', {className: 'panel loading', 'data-testid': 'cardLoading'}, 'Загрузка карточки…'));
        try {
            state.card = await api('cards/' + cardDigits);
            if (state.card.clientId !== clientId) throw new Error('Карта не принадлежит клиенту');
        } catch (err) {
            cardSlot.replaceChildren(h('div', {className: 'panel'}, err.message));
            return;
        }
        state.tab = 'overview';
        cardSlot.replaceChildren(h('div', {className: 'panel', 'data-testid': 'cardProfile'}));
        renderCard();
    }
}

function productProfile(selectedDigits) {
    const c = state.client;
    return h('div', {className: 'panel', 'data-testid': 'productProfile'},
        h('p', {className: 'client-name', 'data-testid': 'clientName'}, c.fullName),
        h('p', {className: 'client-meta'},
            h('span', {'data-testid': 'clientPhone'}, c.phone), ' · паспорт ', c.passportSeries + ' ' + c.passportNumber),
        h('table', {},
            h('thead', {}, h('tr', {}, h('th', {}, 'Продукт'), h('th', {}, 'Номер'), h('th', {}, 'Статус'))),
            h('tbody', {}, c.cards.map(card => h('tr', {'data-testid': 'cardRow', className: card.digits === selectedDigits ? 'selected' : null},
                h('td', {}, card.type),
                h('td', {'data-testid': 'rowCardNumber'}, h('a', {href: '#/client/' + c.clientId + '/card/' + card.digits}, '•••• ' + card.lastDigits)),
                h('td', {'data-testid': 'rowStatus'}, h('span', {className: 'status ' + statusClass(card.status)}, card.status)))))));
}

// Автообновление профиля, пока новая карта заказывается в процессинге
function startPolling(clientId, selectedDigits, slot) {
    clearInterval(state.pollTimer);
    if (!state.client.cards.some(card => card.status === 'В обработке')) return;
    state.pollTimer = setInterval(async () => {
        try {
            state.client = await api('clients/' + clientId);
            slot.replaceChildren(productProfile(selectedDigits));
            if (!state.client.cards.some(card => card.status === 'В обработке')) clearInterval(state.pollTimer);
        } catch (e) {
            clearInterval(state.pollTimer);
        }
    }, 3000);
}

async function reloadClient() {
    state.client = await api('clients/' + state.client.clientId);
    const profile = document.querySelector('[data-testid=productProfile]');
    const fresh = productProfile(state.card && state.card.digits);
    profile.replaceWith(fresh);
    startPolling(state.client.clientId, state.card && state.card.digits, fresh.parentElement);
}

// ---------- Карточка карты ----------

function renderCard() {
    const root = document.querySelector('[data-testid=cardProfile]');
    if (!root) return;
    const card = state.card;
    const status = state.busy ? 'Обработка…' : card.status;

    const actions = h('div', {className: 'card-actions'});
    if (!state.busy && card.status === 'Активна') {
        actions.append(h('button', {className: 'danger', onclick: openBlockDialog}, 'Заблокировать'));
        actions.append(h('button', {onclick: openTemporaryBlockDialog}, 'Временная блокировка'));
    }
    if (!state.busy && card.status === 'Временно заблокирована') {
        actions.append(h('button', {className: 'primary', onclick: openRemoveTemporaryBlockDialog}, 'Снять временную блокировку'));
    }
    if (!state.busy && card.status === 'Заблокирована') {
        actions.append(h('button', {className: 'primary', onclick: openUnblockDialog}, 'Разблокировать'));
    }
    actions.append(h('button', {'data-testid': 'actionsButton', 'aria-haspopup': 'menu', onclick: toggleMenu, disabled: state.busy}, 'Действия'));

    const tabs = [['overview', 'Обзор'], ['limits', 'Лимиты'], ['history', 'История']];
    if (card.requisitesAvailable) tabs.push(['requisites', 'Реквизиты']);

    root.replaceChildren(
        h('div', {className: 'card-head'},
            h('div', {},
                h('p', {className: 'card-title'}, 'Дебетовая карта •••• ' + card.lastDigits),
                h('span', {className: 'status ' + statusClass(status), 'data-testid': 'cardStatus'}, status),
                card.blockReason && !state.busy
                    ? h('span', {className: 'reason'}, 'Причина: ', h('span', {'data-testid': 'blockReason'}, card.blockReason))
                    : null,
                card.status === 'Заблокирована' && card.blockReason === 'Компрометация' && !state.busy
                    ? h('div', {className: 'banner', 'data-testid': 'reissueBanner'}, 'Карта будет перевыпущена автоматически')
                    : null),
            actions),
        h('div', {className: 'tabs', role: 'tablist'}, tabs.map(([id, title]) =>
            h('div', {role: 'tab', 'aria-selected': String(state.tab === id), tabindex: 0, onclick: () => selectTab(id)}, title))),
        h('div', {role: 'tabpanel', 'data-testid': 'tabPanel'}));
    renderTab();
}

function selectTab(id) {
    state.tab = id;
    renderCard();
}

function renderTab() {
    const panel = document.querySelector('[data-testid=tabPanel]');
    const card = state.card;
    if (state.tab === 'overview') {
        panel.replaceChildren(h('dl', {},
            h('dt', {}, 'Остаток'), h('dd', {'data-testid': 'cardBalance'}, card.balance),
            h('dt', {}, 'Тип'), h('dd', {}, 'Дебетовая, МИР'),
            h('dt', {}, 'Срок действия'), h('dd', {}, card.expiry)));
    } else if (state.tab === 'limits') {
        panel.replaceChildren(limitsForm());
    } else if (state.tab === 'history') {
        loadHistory(panel);
    } else if (state.tab === 'requisites') {
        panel.replaceChildren(h('dl', {'data-testid': 'requisites'},
            h('dt', {}, 'Номер карты'), h('dd', {'data-testid': 'cardNumber'}, '•••• ' + card.lastDigits),
            h('dt', {}, 'Держатель'), h('dd', {'data-testid': 'holder'}, card.holderName),
            h('dt', {}, 'Срок действия'), h('dd', {'data-testid': 'expiry'}, card.expiry),
            h('dt', {}, 'Номер счёта'), h('dd', {'data-testid': 'account'}, card.accountNumber)));
    }
}

function limitsForm() {
    const card = state.card;
    const editable = card.status === 'Активна' && !state.busy;
    const row = (name, title, hint) => h('div', {className: 'field'},
        h('label', {for: name}, title),
        h('input', {id: name, name, value: card.limits[name], inputmode: 'numeric', disabled: !editable}),
        h('span', {className: 'hint'}, hint));
    const form = h('form', {className: 'limits', 'data-testid': 'limits'},
        row('cashLimit', 'Снятие наличных, в месяц', 'не больше 500 000 ₽'),
        row('onlineLimit', 'Покупки в интернете, в месяц', 'от 0 (запрещены) до 300 000 ₽'),
        row('transferLimit', 'Переводы, в месяц', 'не больше 1 000 000 ₽'),
        h('button', {type: 'submit', className: 'primary', disabled: !editable}, 'Сохранить'));
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const button = form.querySelector('button');
        button.disabled = true;
        try {
            state.card = await api('cards/' + card.digits + '/limits', {
                method: 'POST',
                body: {cashLimit: form.cashLimit.value, onlineLimit: form.onlineLimit.value, transferLimit: form.transferLimit.value},
            });
            notify('Лимит изменён', 'success');
            renderTab();
        } catch (err) {
            notify(err.message, 'error');
            button.disabled = false;
        }
    });
    return form;
}

async function loadHistory(panel) {
    panel.replaceChildren(h('div', {className: 'loading'}, 'Загрузка истории…'));
    const digits = state.card.digits;
    try {
        const data = await api('cards/' + digits + '/history');
        if (state.tab !== 'history' || !state.card || state.card.digits !== digits) return;
        panel.replaceChildren(h('table', {'data-testid': 'history'},
            h('thead', {}, h('tr', {}, h('th', {}, 'Дата'), h('th', {}, 'Операция'), h('th', {}, 'Пользователь'))),
            h('tbody', {}, data.records.map(r => h('tr', {'data-testid': 'historyRow'},
                h('td', {}, r.date), h('td', {}, r.operation), h('td', {}, r.user))))));
    } catch (err) {
        panel.replaceChildren(h('div', {className: 'loading'}, err.message));
    }
}

// ---------- Меню «Действия» ----------

function toggleMenu(e) {
    e.stopPropagation();
    if (document.querySelector('[role=menu]')) {
        closeMenu();
        return;
    }
    const card = state.card;
    const active = card.status === 'Активна';
    const pinHint = card.status === 'Заблокирована' ? 'Недоступно для заблокированной карты' : 'Недоступно для карты в этом статусе';

    const reissue = menuItem('Перевыпустить', active, null, () => {
        closeMenu();
        openReissueDialog();
    });
    const pin = menuItem('Сменить ПИН-код', active, pinHint, () => {
        closeMenu();
        notify('Ссылка на смену ПИН-кода отправлена клиенту в СМС', 'success');
    });
    const close = menuItem('Закрыть карту', active, null, () => {
        closeMenu();
        openCloseDialog();
    });
    e.currentTarget.parentElement.append(h('div', {role: 'menu'}, reissue, pin, close));
}

function menuItem(title, enabled, disabledHint, action) {
    const item = h('div', {role: 'menuitem', 'aria-disabled': String(!enabled), tabindex: enabled ? 0 : -1}, title);
    if (enabled) {
        item.addEventListener('click', action);
    } else if (disabledHint) {
        item.addEventListener('mouseenter', () => item.append(h('div', {role: 'tooltip'}, disabledHint)));
        item.addEventListener('mouseleave', () => item.querySelectorAll('[role=tooltip]').forEach(t => t.remove()));
    }
    return item;
}

function closeMenu() {
    document.querySelectorAll('[role=menu]').forEach(m => m.remove());
}

// ---------- Окна подтверждения ----------

function dialog(id, title, body, onConfirm) {
    const error = h('div', {className: 'dialog-error', 'data-testid': 'dialogError', role: 'alert'});
    const confirm = h('button', {className: 'primary'}, 'Подтвердить');
    const cancel = h('button', {onclick: closeOverlay}, 'Отмена');
    const box = h('div', {role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': id + 'Title', 'data-testid': id},
        h('h3', {id: id + 'Title'}, title), body, error, h('div', {className: 'dialog-buttons'}, cancel, confirm));
    confirm.addEventListener('click', async () => {
        error.textContent = '';
        confirm.disabled = true;
        cancel.disabled = true;
        try {
            await onConfirm(error);
        } finally {
            confirm.disabled = false;
            cancel.disabled = false;
        }
    });
    document.getElementById('overlay-root').replaceChildren(h('div', {className: 'overlay'}, box));
}

function reasonSelect(name, title, reasons) {
    return h('div', {className: 'field'}, h('label', {for: name}, title),
        h('select', {id: name, name}, h('option', {value: ''}, 'Выберите причину'), reasons.map(r => h('option', {value: r}, r))));
}

function openBlockDialog() {
    dialog('blockDialog', 'Блокировка карты •••• ' + state.card.lastDigits, reasonSelect('blockReason', 'Причина блокировки', BLOCK_REASONS), async (error) => {
        const reason = document.querySelector('[name=blockReason]').value;
        if (!reason) {
            error.textContent = 'Выберите причину блокировки';
            return;
        }
        closeOverlay();
        // Блокировка уходит в процессинг: статус и причина появятся после его ответа
        await runCardOperation('block', {reason}, 'Карта заблокирована');
    });
}

function openTemporaryBlockDialog() {
    dialog('temporaryBlockDialog', 'Временная блокировка карты •••• ' + state.card.lastDigits,
        h('p', {}, 'Операции по карте будут недоступны, пока блокировку не снимут.'), async () => {
            closeOverlay();
            await runCardOperation('tempblock', {}, 'Карта временно заблокирована');
        });
}

function openRemoveTemporaryBlockDialog() {
    dialog('removeTemporaryBlockDialog', 'Снятие временной блокировки карты •••• ' + state.card.lastDigits,
        h('p', {}, 'Операции по карте снова станут доступны.'), async () => {
            closeOverlay();
            await runCardOperation('tempunblock', {}, 'Временная блокировка снята');
        });
}

function openCloseDialog() {
    const digits = state.card.digits;
    dialog('closeDialog', 'Закрыть карту *' + state.card.lastDigits + '?',
        h('p', {}, 'Карта будет закрыта без возможности восстановления.'), async (error) => {
            try {
                state.card = await api('cards/close', {method: 'POST', body: {cardNumber: digits}});
            } catch (err) {
                error.textContent = err.message;
                return;
            }
            closeOverlay();
            notify('Карта закрыта', 'success');
            renderCard();
            await reloadClient();
        });
}

function openUnblockDialog() {
    const body = h('div', {},
        h('p', {}, 'Разблокировку подтверждает старший менеджер.'),
        h('div', {className: 'field'}, h('label', {for: 'supervisorLogin'}, 'Логин старшего менеджера'), h('input', {id: 'supervisorLogin', name: 'supervisorLogin'})),
        h('div', {className: 'field'}, h('label', {for: 'supervisorPassword'}, 'Пароль старшего менеджера'), h('input', {id: 'supervisorPassword', name: 'supervisorPassword', type: 'password'})));
    dialog('unblockDialog', 'Разблокировка карты •••• ' + state.card.lastDigits, body, async (error) => {
        try {
            state.card = await api('cards/' + state.card.digits + '/unblock', {
                method: 'POST',
                body: {
                    supervisorLogin: document.querySelector('[name=supervisorLogin]').value,
                    supervisorPassword: document.querySelector('[name=supervisorPassword]').value,
                },
            });
        } catch (err) {
            error.textContent = err.message;
            return;
        }
        closeOverlay();
        notify('Карта разблокирована', 'success');
        renderCard();
        await reloadClient();
    });
}

function openReissueDialog() {
    dialog('reissueDialog', 'Перевыпуск карты •••• ' + state.card.lastDigits, reasonSelect('reissueReason', 'Причина перевыпуска', REISSUE_REASONS), async (error) => {
        const reason = document.querySelector('[name=reissueReason]').value;
        if (!reason) {
            error.textContent = 'Выберите причину перевыпуска';
            return;
        }
        closeOverlay();
        await runCardOperation('reissue', {reason}, 'Заявка на перевыпуск создана');
    });
}

async function runCardOperation(action, body, successText) {
    state.busy = true;
    renderCard();
    try {
        state.card = await api('cards/' + state.card.digits + '/' + action, {method: 'POST', body});
        notify(successText, 'success');
    } catch (err) {
        notify(err.message, 'error');
    } finally {
        state.busy = false;
        renderCard();
    }
    await reloadClient();
}

route();
