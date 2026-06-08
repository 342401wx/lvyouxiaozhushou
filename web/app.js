const state = {
  config: null,
  user: null,
  memory: [],
  intent: null,
  plan: null,
  intercityPreview: null,
  amap: null,
  map: null,
  largeMap: null,
  activeStopKey: '',
  memoryOpen: false,
};

const appShell = document.querySelector('#app-shell');
const authScreen = document.querySelector('#auth-screen');
const authMessage = document.querySelector('#auth-message');
const loginForm = document.querySelector('#login-form');
const registerForm = document.querySelector('#register-form');
const loginTab = document.querySelector('#login-tab');
const registerTab = document.querySelector('#register-tab');
const userBadge = document.querySelector('#user-badge');
const logoutBtn = document.querySelector('#logout-btn');
const memoryList = document.querySelector('#memory-list');
const memoryMeta = document.querySelector('#memory-meta');
const memoryToggleBtn = document.querySelector('#memory-toggle-btn');
const memoryListPanel = document.querySelector('#memory-list-panel');
const refreshMemoryBtn = document.querySelector('#refresh-memory-btn');
const intentForm = document.querySelector('#intent-form');
const intentSubmitBtn = document.querySelector('#intent-submit-btn');
const intentSection = document.querySelector('#intent-section');
const resultSection = document.querySelector('#result-section');
const mapNode = document.querySelector('#map');
const largeMapNode = document.querySelector('#map-large');
const toolStatus = document.querySelector('#tool-status');
const drawer = document.querySelector('#detail-drawer');
const drawerContent = document.querySelector('#drawer-content');
const mapModal = document.querySelector('#map-modal');
const demoMode = new URLSearchParams(window.location.search).get('demo') === '1';
const intercityModes = ['未确定', '高铁/火车', '飞机', '长途大巴', '自驾', '骑行'];
const localTransportModes = ['公共交通优先', '步行优先', '共享单车优先', '打车优先', '自驾'];
const accommodationModes = ['经济型酒店', '舒适型酒店', '豪华酒店', '民宿'];

document.querySelector('#drawer-close').addEventListener('click', closeDrawer);
document.querySelector('#fit-map-btn').addEventListener('click', () => renderMap());
document.querySelector('#expand-map-btn').addEventListener('click', openMapModal);
document.querySelector('#fit-large-map-btn').addEventListener('click', () => renderMap(largeMapNode));
document.querySelector('#map-modal-close').addEventListener('click', closeMapModal);
loginTab.addEventListener('click', () => setAuthMode('login'));
registerTab.addEventListener('click', () => setAuthMode('register'));
loginForm.addEventListener('submit', (event) => submitAuth(event, 'login'));
registerForm.addEventListener('submit', (event) => submitAuth(event, 'register'));
logoutBtn.addEventListener('click', logout);
refreshMemoryBtn.addEventListener('click', loadMemory);
memoryToggleBtn.addEventListener('click', toggleMemoryPanel);
drawer.addEventListener('click', (event) => {
  if (event.target === drawer) closeDrawer();
});
mapModal.addEventListener('click', (event) => {
  if (event.target === mapModal) closeMapModal();
});

intentForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  setLoading(intentSubmitBtn, true, '识别中');
  try {
    const message = new FormData(intentForm).get('message');
    const response = await fetch('/api/intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: message }),
    });
    if (response.status === 401) {
      showAuth('登录状态已过期，请重新登录。');
      return;
    }
    const result = await response.json();
    if (!result.success) throw new Error(result.message || '识别失败');
    state.intent = result.data;
    state.plan = null;
    state.intercityPreview = null;
    state.activeStopKey = '';
    closeDrawer();
    resetMap();
    renderIntentCards();
    renderIntentPreview();
    if (demoMode) {
      window.setTimeout(() => generatePlanFromIntent(), 400);
    }
    loadMemory();
  } catch (error) {
    intentSection.innerHTML = `<div class="intent-message warn">识别失败：${escapeHtml(error.message)}</div>`;
  } finally {
    setLoading(intentSubmitBtn, false, '整理需求');
  }
});

init();

async function init() {
  const authenticated = await restoreAuth();
  if (!authenticated) return;
  try {
    const response = await fetch('/api/config');
    state.config = await response.json();
    const chips = [];
    chips.push(state.config.has_tourism_index ? '资料已就绪' : '缺少资料索引');
    chips.push(state.config.has_amap_web_service ? '地图服务已配置' : '地图服务待配置');
    chips.push(state.config.has_deepseek ? '需求整理已配置' : '需求整理待配置');
    toolStatus.textContent = chips[0];
    if (!state.config.has_amap_web_service || !state.config.has_deepseek) {
      toolStatus.classList.add('warn');
    }
  } catch {
    toolStatus.textContent = '配置读取失败';
    toolStatus.classList.add('warn');
  }
  await loadMemory();
  if (demoMode) {
    intentForm.elements.message.value = '我从重庆出发，想去成都玩2天，预算1200，不确定包不包括高铁，想看历史和美食，住民宿，路线不要太赶。';
    window.setTimeout(() => intentForm.requestSubmit(), 300);
  }
}

async function restoreAuth() {
  try {
    const response = await fetch('/api/auth/me');
    const result = await response.json();
    if (result.authenticated && result.user) {
      state.user = result.user;
      showApp();
      return true;
    }
  } catch {
    // Fall through to login screen.
  }
  showAuth();
  return false;
}

function showApp() {
  authScreen.classList.add('hidden');
  appShell.classList.remove('locked');
  userBadge.textContent = state.user ? `当前账号：${state.user.username}` : '未登录';
}

function showAuth(message = '') {
  appShell.classList.add('locked');
  authScreen.classList.remove('hidden');
  if (message) setAuthMessage(message, 'error');
}

function setAuthMode(mode) {
  const isRegister = mode === 'register';
  registerForm.classList.toggle('hidden', !isRegister);
  loginForm.classList.toggle('hidden', isRegister);
  registerTab.classList.toggle('active', isRegister);
  loginTab.classList.toggle('active', !isRegister);
  setAuthMessage('', '');
}

async function submitAuth(event, mode) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  const username = String(new FormData(form).get('username') || '').trim();
  const password = String(new FormData(form).get('password') || '');
  const validationMessage = validateAuthFields(username, password);
  if (validationMessage) {
    setAuthMessage(validationMessage, 'error');
    return;
  }

  setLoading(button, true, mode === 'register' ? '注册中' : '登录中');
  try {
    const response = await fetch(`/api/auth/${mode}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const result = await response.json();
    if (!result.success) throw new Error(result.message || '认证失败');
    state.user = result.user;
    setAuthMessage(result.message || '成功', 'ok');
    form.reset();
    await init();
  } catch (error) {
    setAuthMessage(error.message, 'error');
  } finally {
    setLoading(button, false, mode === 'register' ? '注册并登录' : '登录');
  }
}

function validateAuthFields(username, password) {
  const usernamePattern = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]{6,}$/;
  const passwordPattern = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]{8,}$/;
  if (!usernamePattern.test(username)) return '账号需为英文和数字组合，至少 6 位。';
  if (!passwordPattern.test(password)) return '密码需为英文和数字组合，至少 8 位。';
  return '';
}

function setAuthMessage(message, type) {
  authMessage.textContent = message || '';
  authMessage.classList.toggle('error', type === 'error');
  authMessage.classList.toggle('ok', type === 'ok');
}

async function logout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch {
    // Local state cleanup is enough if the network request fails.
  }
  state.user = null;
  state.memory = [];
  state.intent = null;
  state.plan = null;
  state.intercityPreview = null;
  intentSection.innerHTML = '';
  resultSection.innerHTML = '<div class="empty-state"><h2>先写下旅行想法</h2><p>登录后填写需求并生成行程。</p></div>';
  resetMap();
  renderMemory();
  showAuth('已退出登录。');
}

async function loadMemory() {
  if (!state.user) return;
  try {
    const response = await fetch('/api/memory');
    if (response.status === 401) {
      showAuth('登录状态已过期，请重新登录。');
      return;
    }
    const result = await response.json();
    state.memory = result.data || [];
    renderMemory();
  } catch {
    memoryList.innerHTML = '<p class="muted">记忆读取失败，稍后再试。</p>';
  }
}

function renderMemory() {
  if (!memoryList) return;
  if (!state.user) {
    updateMemoryMeta('登录后显示当前账号的记录');
    memoryList.innerHTML = '<p class="muted">登录后显示当前账号的历史记录。</p>';
    syncMemoryPanelState();
    return;
  }
  if (!state.memory.length) {
    updateMemoryMeta('暂无记录');
    memoryList.innerHTML = '<p class="muted">这个账号还没有记录，生成一次攻略后会自动保存。</p>';
    syncMemoryPanelState();
    return;
  }
  const latest = state.memory[0];
  updateMemoryMeta(`${state.memory.length} 条 · 最近 ${formatMemoryTime(latest.created_at)}`);
  memoryList.innerHTML = state.memory.map((item) => `
    <article class="memory-item">
      <div>
        <strong>${escapeHtml(item.kind === 'plan' ? '攻略' : '需求')} · ${escapeHtml(item.title)}</strong>
        <span>${escapeHtml(item.summary)}</span>
      </div>
      <time>${escapeHtml(formatMemoryTime(item.created_at))}</time>
    </article>
  `).join('');
  syncMemoryPanelState();
}

function updateMemoryMeta(text) {
  if (memoryMeta) memoryMeta.textContent = text;
}

function toggleMemoryPanel() {
  state.memoryOpen = !state.memoryOpen;
  syncMemoryPanelState();
}

function syncMemoryPanelState() {
  if (!memoryToggleBtn || !memoryListPanel) return;
  memoryToggleBtn.setAttribute('aria-expanded', state.memoryOpen ? 'true' : 'false');
  memoryListPanel.classList.toggle('collapsed', !state.memoryOpen);
  const toggleText = memoryToggleBtn.querySelector('.memory-toggle-text');
  if (toggleText) toggleText.textContent = state.memoryOpen ? '收起' : '展开';
}

function formatMemoryTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
}

function setLoading(button, isLoading, label) {
  button.disabled = isLoading;
  button.classList.toggle('loading', isLoading);
  button.querySelector('.btn-label').textContent = label;
}

function renderIntentCards() {
  const intent = state.intent;
  if (!intent) {
    intentSection.innerHTML = '';
    return;
  }
  const needsBudgetScope = intent.budget_includes_intercity_transport === null || intent.budget_includes_intercity_transport === undefined;
  const needsIntercityMode = !intent.intercity_options || !intent.intercity_options.length || intent.intercity_transportation === '未确定';
  const confirmLabel = confirmIntentButtonLabel();
  intentSection.innerHTML = `
    <div class="intent-card-set">
      ${(intent.cards || []).map(renderIntentCard).join('')}
    </div>
    ${needsBudgetScope ? renderBudgetScopeChooser() : ''}
    ${needsIntercityMode ? renderIntercityChooser() : ''}
    ${renderIntercityPreplanChooser()}
    <div class="intent-message warn hidden" id="intent-edit-error"></div>
    <div class="confirm-row">
      <button class="ghost-btn" type="button" id="revise-intent-btn">重新识别</button>
      <button class="primary-btn" type="button" id="confirm-intent-btn">
        <span class="btn-label">${escapeHtml(confirmLabel)}</span>
        <span class="btn-loader" aria-hidden="true"></span>
      </button>
    </div>
  `;
  document.querySelector('#confirm-intent-btn').addEventListener('click', () => generatePlanFromIntent());
  document.querySelector('#revise-intent-btn').addEventListener('click', () => {
    intentForm.elements.message.focus();
  });
  intentSection.querySelectorAll('[data-budget-scope]').forEach((button) => {
    button.addEventListener('click', () => updateBudgetScope(button.dataset.budgetScope));
  });
  intentSection.querySelectorAll('[data-intercity-mode]').forEach((button) => {
    button.addEventListener('click', () => updateIntercityMode(button.dataset.intercityMode));
  });
  bindIntercityPreplanControls();
  bindIntentEditors();
}

function renderIntentCard(card) {
  const key = card.key;
  return `
    <article class="intent-card editable ${card.tone || 'plain'}">
      <label for="intent-field-${escapeHtml(key)}">${escapeHtml(card.label)}</label>
      ${renderIntentControl(key)}
      ${card.note ? `<span>${escapeHtml(card.note)}</span>` : ''}
    </article>
  `;
}

function renderIntentControl(key) {
  const value = getIntentFieldValue(key);
  if (key === 'original_text') {
    return `<textarea id="intent-field-${key}" class="intent-input textarea" data-intent-field="${key}" rows="5">${escapeHtml(value)}</textarea>`;
  }
  if (key === 'days') {
    return `<input id="intent-field-${key}" class="intent-input" data-intent-field="${key}" type="number" min="1" max="7" value="${escapeHtml(value)}">`;
  }
  if (key === 'budget') {
    return `<input id="intent-field-${key}" class="intent-input" data-intent-field="${key}" type="number" min="0" step="50" placeholder="可不填" value="${value ? escapeHtml(value) : ''}">`;
  }
  if (key === 'start_date' || key === 'return_date') {
    return `<input id="intent-field-${key}" class="intent-input" data-intent-field="${key}" type="date" value="${escapeHtml(value)}">`;
  }
  if (key === 'intercity_transportation') {
    return renderSelectControl(key, intercityModes, value || '未确定');
  }
  if (key === 'transportation') {
    return renderSelectControl(key, localTransportModes, value || '公共交通优先');
  }
  if (key === 'accommodation') {
    return renderSelectControl(key, accommodationModes, value || '经济型酒店');
  }
  const placeholders = {
    city: '例如：铜陵',
    origin: '可不填，例如：六安',
    interests: '例如：观光、历史、美食',
    requested_places: '可不填；只写明确地点',
    mobility_constraints: '例如：不打车、少走路',
  };
  return `<input id="intent-field-${key}" class="intent-input" data-intent-field="${key}" type="text" placeholder="${escapeHtml(placeholders[key] || '可编辑')}" value="${escapeHtml(value)}">`;
}

function renderSelectControl(key, options, value) {
  return `
    <select id="intent-field-${key}" class="intent-input" data-intent-field="${key}">
      ${options.map((option) => `<option value="${escapeHtml(option)}" ${option === value ? 'selected' : ''}>${escapeHtml(option)}</option>`).join('')}
    </select>
  `;
}

function getIntentFieldValue(key) {
  const intent = state.intent || {};
  const values = {
    original_text: intent.original_text || intent.free_text || '',
    city: intent.city || '',
    origin: intent.origin || '',
    days: intent.days || 1,
    start_date: intent.start_date || '',
    return_date: intent.return_date || '',
    budget: intent.budget || '',
    intercity_transportation: intent.intercity_transportation || '未确定',
    interests: (intent.interests || []).join('、'),
    requested_places: (intent.requested_places || []).join('、'),
    transportation: intent.local_transportation || intent.transportation || '公共交通优先',
    mobility_constraints: (intent.mobility_constraints || []).join('、'),
    accommodation: intent.accommodation || '经济型酒店',
  };
  return values[key] ?? '';
}

function bindIntentEditors() {
  intentSection.querySelectorAll('[data-intent-field]').forEach((control) => {
    const eventName = control.tagName === 'SELECT' ? 'change' : 'input';
    control.addEventListener(eventName, () => {
      updateIntentField(control.dataset.intentField, control.value);
      hideIntentEditError();
      if (!state.plan) renderIntentPreview();
    });
  });
}

function updateIntentField(key, value, options = {}) {
  if (!state.intent) return;
  const shouldClearIntercitySelection = options.clearIntercitySelection !== false;
  const clearsIntercitySelection = ['city', 'origin', 'days', 'start_date', 'return_date', 'intercity_transportation'].includes(key);
  const previousIntercityValue = clearsIntercitySelection
    ? String(key === 'intercity_transportation' ? state.intent.intercity_transportation || '' : state.intent[key] || '')
    : '';
  const text = String(value || '').trim();
  if (key === 'original_text') {
    state.intent.original_text = text;
    state.intent.free_text = text;
  } else if (key === 'days') {
    state.intent.days = Math.max(1, Math.min(7, Number.parseInt(text || '1', 10) || 1));
    state.intent.return_date = computeReturnDate(state.intent.start_date, state.intent.days, state.intent.return_date_policy);
  } else if (key === 'budget') {
    state.intent.budget = Math.max(0, Number.parseInt(text || '0', 10) || 0);
    state.intent.budget_is_explicit = Boolean(state.intent.budget);
  } else if (key === 'interests') {
    state.intent.interests = splitListValue(text);
  } else if (key === 'requested_places') {
    state.intent.requested_places = splitListValue(text);
  } else if (key === 'mobility_constraints') {
    state.intent.mobility_constraints = splitListValue(text);
  } else if (key === 'transportation') {
    state.intent.transportation = text || '公共交通优先';
    state.intent.local_transportation = state.intent.transportation;
  } else if (key === 'start_date') {
    state.intent.start_date = text;
    state.intent.return_date = computeReturnDate(state.intent.start_date, state.intent.days, state.intent.return_date_policy);
  } else if (key === 'return_date') {
    state.intent.return_date = text;
  } else {
    state.intent[key] = text;
  }

  const nextIntercityValue = clearsIntercitySelection
    ? String(key === 'intercity_transportation' ? state.intent.intercity_transportation || '' : state.intent[key] || '')
    : '';
  const intercitySelectionChanged = clearsIntercitySelection && previousIntercityValue !== nextIntercityValue;
  if (key === 'intercity_transportation') {
    state.intent.intercity_options = text && text !== '未确定' ? [text] : [];
  }
  if (intercitySelectionChanged && shouldClearIntercitySelection) {
    state.intercityPreview = null;
    clearSelectedTrainTicketSelection();
  }
  updateIntentCardValue(key);
  syncPlanPayloadFromIntent();
}

function splitListValue(value) {
  return String(value || '')
    .split(/[、,，\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function computeReturnDate(startDate, days, policy = 'last_day') {
  if (!startDate) return '';
  const date = new Date(`${startDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return '';
  const offset = Math.max(0, Number.parseInt(days || '1', 10) - 1) + (policy === 'next_day_after_last_day' ? 1 : 0);
  date.setDate(date.getDate() + offset);
  return date.toISOString().slice(0, 10);
}

function formatDateDisplay(value) {
  return String(value || '').replace(/-/g, '.') || '未确定';
}

function updateIntentCardValue(key) {
  const card = (state.intent.cards || []).find((item) => item.key === key);
  if (!card) return;
  if (key === 'days') card.value = `${state.intent.days}天`;
  else if (key === 'start_date') card.value = formatDateDisplay(state.intent.start_date);
  else if (key === 'return_date') card.value = formatDateDisplay(state.intent.return_date);
  else if (key === 'budget') card.value = state.intent.budget ? `${state.intent.budget}元` : '未提供';
  else if (key === 'interests') card.value = (state.intent.interests || []).join('、');
  else if (key === 'requested_places') card.value = (state.intent.requested_places || []).join('、') || '未指定';
  else if (key === 'transportation') card.value = state.intent.local_transportation || state.intent.transportation;
  else if (key === 'mobility_constraints') card.value = (state.intent.mobility_constraints || []).join('、') || '无硬性限制';
  else card.value = getIntentFieldValue(key) || '未指定';
}

function syncPlanPayloadFromIntent() {
  if (!state.intent) return;
  const localTransportation = state.intent.local_transportation || state.intent.transportation || '公共交通优先';
  state.intent.plan_payload = {
    ...(state.intent.plan_payload || {}),
    city: state.intent.city || '',
    origin: state.intent.origin || '',
    days: state.intent.days || 1,
    start_date: state.intent.start_date || '',
    return_date: state.intent.return_date || computeReturnDate(state.intent.start_date, state.intent.days, state.intent.return_date_policy),
    return_date_policy: state.intent.return_date_policy || 'last_day',
    budget: state.intent.budget || 0,
    budget_is_explicit: Boolean(state.intent.budget),
    budget_scope: state.intent.budget_scope || '未说明是否包含往返城际交通',
    budget_includes_intercity_transport: state.intent.budget_includes_intercity_transport,
    budget_includes_long_distance: state.intent.budget_includes_long_distance,
    intercity_transportation: state.intent.intercity_transportation || '未确定',
    intercity_options: state.intent.intercity_options || [],
    interests: state.intent.interests || [],
    requested_places: state.intent.requested_places || [],
    transportation: localTransportation,
    local_transportation: localTransportation,
    mobility_constraints: state.intent.mobility_constraints || [],
    accommodation: state.intent.accommodation || '经济型酒店',
    free_text: state.intent.free_text || state.intent.original_text || '',
    intercity_departure_time: state.intent.intercity_departure_time || state.intent.plan_payload?.intercity_departure_time || '',
  };
}

function intercitySelectionSignature() {
  if (!state.intent) return '';
  return JSON.stringify({
    city: state.intent.city || '',
    origin: state.intent.origin || '',
    days: Number.parseInt(state.intent.days || '1', 10) || 1,
    start_date: state.intent.start_date || '',
    return_date: state.intent.return_date || computeReturnDate(state.intent.start_date, state.intent.days, state.intent.return_date_policy),
    intercity_transportation: state.intent.intercity_transportation || '未确定',
  });
}

function syncIntentFromControls(options = {}) {
  const clearIntercitySelectionOnChange = options.clearIntercitySelectionOnChange !== false;
  const previousIntercitySignature = intercitySelectionSignature();
  intentSection.querySelectorAll('[data-intent-field]').forEach((control) => {
    updateIntentField(control.dataset.intentField, control.value, { clearIntercitySelection: false });
  });
  if (clearIntercitySelectionOnChange && previousIntercitySignature !== intercitySelectionSignature()) {
    state.intercityPreview = null;
    clearSelectedTrainTicketSelection();
    syncPlanPayloadFromIntent();
  }
}

function showIntentEditError(message) {
  const errorNode = document.querySelector('#intent-edit-error');
  if (!errorNode) return;
  errorNode.textContent = message;
  errorNode.classList.remove('hidden');
}

function hideIntentEditError() {
  const errorNode = document.querySelector('#intent-edit-error');
  if (errorNode) errorNode.classList.add('hidden');
}

function renderBudgetScopeChooser() {
  const budgetText = state.intent && state.intent.budget ? `${formatNumber(state.intent.budget)}元` : '这类';
  return `
    <div class="clarify-card">
      <strong>预算范围</strong>
      <p>${escapeHtml(budgetText)}预算容易有歧义，先确认它是否包含高铁、飞机、大巴、自驾等往返城际交通。</p>
      <div class="segmented-row">
        <button class="ghost-btn" type="button" data-budget-scope="local">只算当地游玩</button>
        <button class="ghost-btn" type="button" data-budget-scope="all">包含城际交通</button>
      </div>
    </div>
  `;
}

function renderIntercityChooser() {
  return `
    <div class="clarify-card">
      <strong>城际交通</strong>
      <p>从出发地到目的地可以按不同方式估算，确认后会影响预算。</p>
      <div class="mode-grid">
        ${['高铁/火车', '飞机', '长途大巴', '自驾', '骑行'].map((mode) => `
          <button class="ghost-btn" type="button" data-intercity-mode="${mode}">${mode}</button>
        `).join('')}
      </div>
    </div>
  `;
}

function updateBudgetScope(scope) {
  if (!state.intent) return;
  if (scope === 'all') {
    state.intent.budget_scope = '包含往返城际交通';
    state.intent.budget_includes_intercity_transport = true;
    state.intent.budget_includes_long_distance = true;
  } else {
    state.intent.budget_scope = '仅目的地内消费，不含往返城际交通';
    state.intent.budget_includes_intercity_transport = false;
    state.intent.budget_includes_long_distance = false;
  }
  const budgetCard = (state.intent.cards || []).find((card) => card.key === 'budget');
  if (budgetCard) {
    budgetCard.note = state.intent.budget_scope;
    budgetCard.tone = 'plain';
  }
  state.intent.plan_payload.budget_scope = state.intent.budget_scope;
  state.intent.plan_payload.budget_includes_intercity_transport = state.intent.budget_includes_intercity_transport;
  state.intent.plan_payload.budget_includes_long_distance = state.intent.budget_includes_long_distance;
  syncPlanPayloadFromIntent();
  renderIntentCards();
  if (!state.plan) renderIntentPreview();
}

function updateIntercityMode(mode) {
  if (!state.intent) return;
  state.intent.intercity_transportation = mode;
  state.intent.intercity_options = [mode];
  const card = (state.intent.cards || []).find((item) => item.key === 'intercity_transportation');
  if (card) {
    card.value = mode;
    card.tone = 'plain';
  }
  state.intent.plan_payload.intercity_transportation = mode;
  state.intent.plan_payload.intercity_options = [mode];
  clearSelectedTrainTicketSelection();
  state.intercityPreview = null;
  syncPlanPayloadFromIntent();
  renderIntentCards();
  if (!state.plan) renderIntentPreview();
}

function selectedIntercityMode() {
  return state.intent ? state.intent.intercity_transportation || '未确定' : '未确定';
}

function hasSelectedTrainTicket() {
  const value = state.intent && state.intent.plan_payload && state.intent.plan_payload.selected_train_index;
  return value !== undefined && value !== null && value !== '';
}

function hasSelectedReturnTrainTicket() {
  const value = state.intent && state.intent.plan_payload && state.intent.plan_payload.selected_return_train_index;
  return value !== undefined && value !== null && value !== '';
}

function needsReturnTrainTicketSelection() {
  const option = trainOptionFromPreview();
  return Boolean(option && (option.return_train_tickets || []).some((ticket) => ticket && ticket.available));
}

function clearSelectedTrainTicketSelection() {
  if (!state.intent || !state.intent.plan_payload) return;
  delete state.intent.plan_payload.selected_train_index;
  delete state.intent.plan_payload.selected_train_ticket;
  delete state.intent.plan_payload.selected_return_train_index;
  delete state.intent.plan_payload.selected_return_train_ticket;
}

function confirmIntentButtonLabel() {
  const mode = selectedIntercityMode();
  if (mode === '高铁/火车') {
    if (!state.intercityPreview) return '查询往返车次';
    if (!hasSelectedTrainTicket()) return '请选择去程车次';
    if (needsReturnTrainTicketSelection() && !hasSelectedReturnTrainTicket()) return '请选择返程车次';
  }
  if (mode === '自驾' && !(state.intent && state.intent.intercity_departure_time)) {
    return '确认出发时间';
  }
  return '确认并生成攻略';
}

function renderIntercityPreplanChooser() {
  const mode = selectedIntercityMode();
  if (mode === '高铁/火车') return renderTrainPreplanChooser();
  if (mode === '自驾') return renderDrivingDepartureChooser();
  return '';
}

function renderTrainPreplanChooser() {
  const option = trainOptionFromPreview();
  const tickets = option ? option.train_tickets || [] : [];
  const returnTickets = option ? option.return_train_tickets || [] : [];
  const startDate = state.intent && state.intent.plan_payload ? state.intent.plan_payload.start_date || state.intent.start_date : '';
  const returnDate = state.intent && state.intent.plan_payload ? state.intent.plan_payload.return_date || state.intent.return_date : '';
  if (!option) {
    return `
      <div class="clarify-card compact-flow-card">
        <strong>往返城际</strong>
        <p>高铁/火车需要先查询去程和返程车次，选好后再生成攻略。</p>
        <p class="muted">去程 ${escapeHtml(formatDateDisplay(startDate))} · 返程 ${escapeHtml(formatDateDisplay(returnDate))}</p>
      </div>
    `;
  }
  if (!tickets.length) {
    return `
      <div class="clarify-card compact-flow-card">
        <strong>往返城际</strong>
        <p class="muted">去程 ${escapeHtml(formatDateDisplay(option.query_date || startDate))} · 返程 ${escapeHtml(formatDateDisplay(option.return_query_date || returnDate))}</p>
        <p>${escapeHtml(option.ticket_query_error || '暂未查到可选择车次，请换交通方式或稍后再试。')}</p>
      </div>
    `;
  }
  const selectedIndex = hasSelectedTrainTicket() ? Number(state.intent.plan_payload.selected_train_index) : -1;
  const selectedTicket = selectedIndex >= 0 ? tickets[selectedIndex] || state.intent.plan_payload.selected_train_ticket : null;
  const selectedReturnIndex = hasSelectedReturnTrainTicket() ? Number(state.intent.plan_payload.selected_return_train_index) : -1;
  const selectedReturnTicket = selectedReturnIndex >= 0 ? returnTickets[selectedReturnIndex] || state.intent.plan_payload.selected_return_train_ticket : null;
  return `
    <div class="clarify-card compact-flow-card">
      <strong>往返城际</strong>
      <p class="muted">去程 ${escapeHtml(formatDateDisplay(option.query_date || startDate))} · 返程 ${escapeHtml(formatDateDisplay(option.return_query_date || returnDate))}</p>
      <label class="field-label" for="train-ticket-select">去程车次</label>
      <select class="intent-input" id="train-ticket-select">
        <option value="">请选择车次</option>
        ${tickets.map((ticket, index) => `
          <option value="${index}" ${index === selectedIndex ? 'selected' : ''} ${ticket.available ? '' : 'disabled'}>
            ${escapeHtml(trainTicketOptionLabel(ticket))}
          </option>
        `).join('')}
      </select>
      ${selectedTicket ? renderTrainTicketSummary(selectedTicket) : ''}
      ${returnTickets.length ? `
        <label class="field-label" for="return-train-ticket-select">返程车次</label>
        <select class="intent-input" id="return-train-ticket-select">
          <option value="">请选择返程车次</option>
          ${returnTickets.map((ticket, index) => `
            <option value="${index}" ${index === selectedReturnIndex ? 'selected' : ''} ${ticket.available ? '' : 'disabled'}>
              ${escapeHtml(trainTicketOptionLabel(ticket))}
            </option>
          `).join('')}
        </select>
        ${selectedReturnTicket ? renderTrainTicketSummary(selectedReturnTicket) : ''}
      ` : `<p class="muted warn-text">${escapeHtml(option.return_ticket_query_error || '暂未查到返程车次候选，返程费用先按参考估算。')}</p>`}
    </div>
  `;
}

function renderDrivingDepartureChooser() {
  const value = state.intent && (state.intent.intercity_departure_time || state.intent.plan_payload?.intercity_departure_time || '');
  const option = drivingOptionFromPreview();
  return `
    <div class="clarify-card compact-flow-card">
      <strong>城际到达</strong>
      <label class="field-label" for="intercity-departure-time">自驾出发时间</label>
      <input class="intent-input" id="intercity-departure-time" type="time" value="${escapeHtml(value)}" placeholder="08:00">
      ${option && option.arrive_time ? `<p class="muted">预计 ${escapeHtml(option.arrive_time)} 到达，单程约 ${escapeHtml(option.duration_text)}。</p>` : ''}
    </div>
  `;
}

function bindIntercityPreplanControls() {
  const trainSelect = document.querySelector('#train-ticket-select');
  if (trainSelect) {
    trainSelect.addEventListener('change', () => {
      if (!state.intent || !state.intent.plan_payload) return;
      if (trainSelect.value === '') {
        delete state.intent.plan_payload.selected_train_index;
        delete state.intent.plan_payload.selected_train_ticket;
      } else {
        selectTrainTicketFromOption(trainOptionFromPreview(), Number(trainSelect.value));
      }
      hideIntentEditError();
      renderIntentCards();
      if (!state.plan) renderIntentPreview();
    });
  }
  const returnTrainSelect = document.querySelector('#return-train-ticket-select');
  if (returnTrainSelect) {
    returnTrainSelect.addEventListener('change', () => {
      if (!state.intent || !state.intent.plan_payload) return;
      if (returnTrainSelect.value === '') {
        delete state.intent.plan_payload.selected_return_train_index;
        delete state.intent.plan_payload.selected_return_train_ticket;
      } else {
        selectReturnTrainTicketFromOption(trainOptionFromPreview(), Number(returnTrainSelect.value));
      }
      hideIntentEditError();
      renderIntentCards();
      if (!state.plan) renderIntentPreview();
    });
  }
  const departureInput = document.querySelector('#intercity-departure-time');
  if (departureInput) {
    departureInput.addEventListener('input', () => {
      if (!state.intent) return;
      state.intent.intercity_departure_time = departureInput.value;
      syncPlanPayloadFromIntent();
      state.intercityPreview = null;
      hideIntentEditError();
      updateConfirmButtonLabel();
      if (!state.plan) renderIntentPreview();
    });
  }
}

function updateConfirmButtonLabel() {
  const label = document.querySelector('#confirm-intent-btn .btn-label');
  if (label) label.textContent = confirmIntentButtonLabel();
}

function trainOptionFromPreview() {
  const options = state.intercityPreview && state.intercityPreview.options;
  return (options || []).find((item) => item.mode === '高铁/火车');
}

function drivingOptionFromPreview() {
  const options = state.intercityPreview && state.intercityPreview.options;
  return (options || []).find((item) => item.mode === '自驾');
}

function trainTicketOptionLabel(ticket) {
  const parts = [
    ticket.train_code || '车次待确认',
    `${ticket.depart_time || '--'}→${ticket.arrive_time || '--'}`,
    ticket.transfer_note || '',
    ticket.seat_type ? `${ticket.seat_type} ¥${formatNumber(ticket.one_way_cost)}` : '',
  ];
  return parts.filter(Boolean).join(' · ');
}

function selectTrainTicketFromOption(option, index) {
  if (!state.intent || !state.intent.plan_payload || !option) return false;
  const ticket = (option.train_tickets || [])[index];
  if (!ticket || !ticket.available) return false;
  state.intent.plan_payload.selected_train_index = index;
  state.intent.plan_payload.selected_train_ticket = compactTrainTicket(ticket);
  return true;
}

function selectReturnTrainTicketFromOption(option, index) {
  if (!state.intent || !state.intent.plan_payload || !option) return false;
  const ticket = (option.return_train_tickets || [])[index];
  if (!ticket || !ticket.available) return false;
  state.intent.plan_payload.selected_return_train_index = index;
  state.intent.plan_payload.selected_return_train_ticket = compactTrainTicket(ticket);
  return true;
}

function compactTrainTicket(ticket) {
  if (!ticket || typeof ticket !== 'object') return null;
  const keys = [
    'train_code',
    'seat_type',
    'ticket_status',
    'depart_time',
    'arrive_time',
    'duration_min',
    'duration_text',
    'from_station',
    'to_station',
    'one_way_cost',
    'round_trip_cost',
    'transfer_note',
    'query_date',
    'available',
    'arrival_day_offset',
  ];
  const compact = {};
  keys.forEach((key) => {
    if (ticket[key] !== undefined && ticket[key] !== null && ticket[key] !== '') compact[key] = ticket[key];
  });
  if (Array.isArray(ticket.segments)) {
    compact.segments = ticket.segments
      .map((segment) => compactTrainTicket(segment))
      .filter(Boolean);
  }
  return compact;
}

function ensureSelectedTrainTicketPayload() {
  if (!state.intent || !state.intent.plan_payload || !hasSelectedTrainTicket()) return;
  if (state.intent.plan_payload.selected_train_ticket) return;
  const option = trainOptionFromPreview();
  const index = Number(state.intent.plan_payload.selected_train_index);
  const ticket = option && (option.train_tickets || [])[index];
  if (ticket) state.intent.plan_payload.selected_train_ticket = compactTrainTicket(ticket);
}

function ensureSelectedReturnTrainTicketPayload() {
  if (!state.intent || !state.intent.plan_payload || !hasSelectedReturnTrainTicket()) return;
  if (state.intent.plan_payload.selected_return_train_ticket) return;
  const option = trainOptionFromPreview();
  const index = Number(state.intent.plan_payload.selected_return_train_index);
  const ticket = option && (option.return_train_tickets || [])[index];
  if (ticket) state.intent.plan_payload.selected_return_train_ticket = compactTrainTicket(ticket);
}

function renderIntentPreview() {
  const intent = state.intent;
  if (!intent) return;
  resultSection.innerHTML = `
    <section class="day-card">
      <h2>需求确认</h2>
      <p class="muted">${escapeHtml(intent.original_text)}</p>
      <div class="tool-row">
        <span class="tool-chip">目的地：${escapeHtml(intent.city || '待填写')}</span>
        <span class="tool-chip">天数：${intent.days}天</span>
        <span class="tool-chip">去程：${escapeHtml(formatDateDisplay(intent.start_date))}</span>
        <span class="tool-chip">返程：${escapeHtml(formatDateDisplay(intent.return_date))}</span>
        <span class="tool-chip ${intent.budget_includes_intercity_transport == null ? 'warn' : ''}">预算：${escapeHtml(formatBudgetSummary(intent.budget))}</span>
        <span class="tool-chip">城际：${escapeHtml(intent.intercity_transportation || '未确定')}</span>
        <span class="tool-chip">当地：${escapeHtml(intent.local_transportation || intent.transportation)}</span>
        <span class="tool-chip">偏好：${escapeHtml((intent.interests || []).join('、'))}</span>
      </div>
      ${(intent.mobility_constraints || []).length ? `<p class="muted">交通约束：${escapeHtml(intent.mobility_constraints.join('、'))}</p>` : ''}
      <p class="muted">${escapeHtml(intent.budget_scope)}</p>
    </section>
  `;
}

async function generatePlanFromIntent() {
  if (!state.intent) return;
  syncIntentFromControls();
  if (!validateIntentBeforePlan()) return;
  ensureSelectedTrainTicketPayload();
  ensureSelectedReturnTrainTicketPayload();
  const button = document.querySelector('#confirm-intent-btn');
  const mode = selectedIntercityMode();
  if (mode === '高铁/火车' && !hasSelectedTrainTicket()) {
    if (!state.intercityPreview) {
      await loadIntercityPreview(button);
      return;
    }
    showIntentEditError('请先在下拉栏里选择具体车次。');
    return;
  }
  if (mode === '高铁/火车' && needsReturnTrainTicketSelection() && !hasSelectedReturnTrainTicket()) {
    showIntentEditError('请先在下拉栏里选择返程车次。');
    return;
  }
  if (mode === '自驾' && !state.intent.intercity_departure_time) {
    showIntentEditError('请先选择自驾出发时间。');
    return;
  }
  await submitPlanRequest(state.intent.plan_payload, button, '生成中', '确认并生成攻略');
}

async function loadIntercityPreview(button = null) {
  syncPlanPayloadFromIntent();
  if (button) setLoading(button, true, '查询中');
  try {
    const response = await fetch('/api/intercity-options', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state.intent.plan_payload),
    });
    if (response.status === 401) {
      showAuth('登录状态已过期，请重新登录。');
      return;
    }
    const result = await response.json();
    if (!result.success) throw new Error(result.message || '城际交通查询失败');
    state.intercityPreview = result.data;
    renderIntentCards();
    renderIntentPreview();
  } catch (error) {
    showIntentEditError(error.message);
  } finally {
    if (button) setLoading(button, false, confirmIntentButtonLabel());
  }
}

async function submitPlanRequest(payload, button = null, loadingText = '生成中', resetText = '确认并生成攻略') {
  if (button) setLoading(button, true, loadingText);
  try {
    const response = await fetch('/api/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (response.status === 401) {
      showAuth('登录状态已过期，请重新登录。');
      return;
    }
    const result = await response.json();
    if (!result.success) throw new Error(result.message || '规划失败');
    state.plan = result.data;
    state.activeStopKey = '';
    renderPlan();
    await renderMap();
    loadMemory();
  } catch (error) {
    resultSection.innerHTML = `<div class="empty-state"><h2>生成失败</h2><p>${escapeHtml(error.message)}</p></div>`;
  } finally {
    if (button) setLoading(button, false, resetText);
  }
}

function validateIntentBeforePlan() {
  if (!state.intent.city) {
    showIntentEditError('请先填写目的地城市，再生成攻略。');
    return false;
  }
  if (!state.intent.days) {
    showIntentEditError('请先填写行程天数。');
    return false;
  }
  return true;
}

function resetMap(targetNode = mapNode) {
  targetNode.innerHTML = '<div class="map-empty">确认需求后显示点位和路线</div>';
}

function renderPlan() {
  const plan = state.plan;
  if (!plan) return;
  const budgetClass = plan.budget.is_over_budget ? 'budget-over' : 'budget-ok';
  resultSection.innerHTML = `
    <div class="summary-grid">
      <div class="summary-card"><strong>城市</strong><span>${escapeHtml(plan.city)}</span></div>
      ${plan.origin ? `<div class="summary-card"><strong>出发地</strong><span>${escapeHtml(plan.origin)}</span></div>` : ''}
      <div class="summary-card"><strong>行程</strong><span>${plan.days_count}天</span></div>
      <div class="summary-card"><strong>费用估算</strong><span class="${budgetClass}">¥${formatNumber(plan.budget.total)}</span></div>
      <div class="summary-card"><strong>城际交通</strong><span>${escapeHtml(plan.intercity_transportation || '未涉及')}</span></div>
      <div class="summary-card"><strong>住宿</strong><span>${escapeHtml(plan.accommodation)}</span></div>
    </div>
    <div class="tool-row">
      ${toolChip('资料库', plan.tool_status.rag)}
      ${toolChip('路线服务', plan.tool_status.amap_web_service)}
      ${toolChip('地图显示', plan.tool_status.amap_js)}
      ${toolChip('需求整理', plan.tool_status.deepseek)}
      ${intercityStatusChip(plan.tool_status.intercity_transport)}
      <span class="tool-chip">交通偏好：已考虑</span>
      <span class="tool-chip">景区状态：${plan.tool_status.scenic_status === 'web-search' ? '已核验' : '参考公告'}</span>
      <span class="tool-chip">路线：按距离估算</span>
    </div>
    ${plan.budget_note ? `<section class="day-card compact-card"><h2>预算范围</h2><p class="muted">${escapeHtml(plan.budget_note)}</p></section>` : ''}
    ${renderBudgetBreakdown(plan.budget)}
    ${renderIntercityTransport(plan.intercity_transport)}
    ${renderMobilityPolicy(plan.mobility_policy)}
    ${renderScenicStatusSummary(plan.scenic_status_summary)}
    <section class="day-card">
      <h2>总体建议</h2>
      <p class="muted">${escapeHtml(plan.overall_suggestions)}</p>
    </section>
    ${renderWeather(plan.weather_info)}
    ${plan.days.map(renderDay).join('')}
    ${renderHotelInsights(plan.hotel_review_insights)}
    ${renderRagContext(plan.rag_context)}
  `;
  bindPlanInteractions();
}

function toolChip(label, enabled) {
  return `<span class="tool-chip ${enabled ? '' : 'warn'}">${label}：${enabled ? '可用' : '参考'}</span>`;
}

function intercityStatusChip(status) {
  const realtime = status === '12306-mcp' || status === '12306-mcp-no-ticket' || status === '12306-mcp-candidates';
  return `<span class="tool-chip ${realtime ? '' : 'warn'}">城际交通：${escapeHtml(intercityStatusLabel(status))}</span>`;
}

function intercityStatusLabel(status) {
  if (status === '12306-mcp-candidates') return '已查到候选车次';
  if (status === '12306-mcp') return '实时车次';
  if (status === '12306-mcp-no-ticket') return '已查询无直达';
  if (status === 'not-selected') return '未选择方式';
  return '参考估算';
}

function renderBudgetBreakdown(budget) {
  if (!budget) return '';
  return `
    <section class="day-card compact-card">
      <h2>费用拆分</h2>
      <div class="tool-row">
        <span class="tool-chip">城际交通 ¥${formatNumber(budget.total_intercity_transportation)}</span>
        <span class="tool-chip">当地交通 ¥${formatNumber(budget.total_transportation)}</span>
        <span class="tool-chip">住宿 ¥${formatNumber(budget.total_hotels)}</span>
        <span class="tool-chip">餐饮 ¥${formatNumber(budget.total_meals)}</span>
        <span class="tool-chip">门票/参考门票 ¥${formatNumber(budget.total_attractions)}</span>
      </div>
      <p class="muted">当前总费用${budget.intercity_included ? '已计入' : '未计入'}往返城际交通。</p>
    </section>
  `;
}

function renderIntercityTransport(intercity) {
  if (!intercity || !intercity.options || !intercity.options.length) return '';
  return `
    <section class="day-card">
      <h2>往返城际交通</h2>
      <p class="muted">${escapeHtml(intercity.summary)}</p>
      <div class="intercity-grid">
        ${intercity.options.map((option) => `
          <div class="mini-card ${option.not_recommended ? 'warn-card' : ''}">
            <strong>${escapeHtml(option.mode)}</strong>
            <p>往返约 ¥${formatNumber(option.estimated_cost)} · 去程 ¥${formatNumber(option.one_way_cost)} · ${escapeHtml(option.duration_text)}</p>
            ${option.query_date || option.return_query_date ? `<p class="muted">去程 ${escapeHtml(formatDateDisplay(option.query_date))} · 返程 ${escapeHtml(formatDateDisplay(option.return_query_date))}</p>` : ''}
            ${option.train_code ? `<p class="muted">去程：${escapeHtml(option.train_code)} · ${escapeHtml(option.seat_type || '座席待确认')} · ${escapeHtml(option.depart_time || '')}-${escapeHtml(option.arrive_time || '')}</p>` : ''}
            ${option.return_train_code ? `<p class="muted">返程：${escapeHtml(option.return_train_code)} · ${escapeHtml(option.return_seat_type || '座席待确认')} · ${escapeHtml(option.return_depart_time || '')}-${escapeHtml(option.return_arrive_time || '')}</p>` : ''}
            <p class="muted">来源：${escapeHtml(intercitySourceLabel(option))}</p>
            <p class="muted">${escapeHtml(option.notice)}</p>
            ${option.ticket_selection_required ? '<p class="muted warn-text">未选择具体车次前，首日时间按 08:30 开始；点击下方车次后会按到达时间重排。</p>' : ''}
            ${option.ticket_query_error ? `<p class="muted warn-text">当天车票查询：${escapeHtml(option.ticket_query_error)}</p>` : ''}
            ${option.return_ticket_query_error ? `<p class="muted warn-text">返程车票查询：${escapeHtml(option.return_ticket_query_error)}</p>` : ''}
            ${renderTrainTickets(option)}
          </div>
        `).join('')}
      </div>
    </section>
  `;
}

function renderTrainTickets(option) {
  const tickets = option.train_tickets || [];
  const returnTickets = option.return_train_tickets || [];
  if (!tickets.length && !returnTickets.length) return '';
  const selectedIndex = Number.isInteger(option.selected_train_index) ? option.selected_train_index : -1;
  const selectedTicket = selectedIndex >= 0 ? tickets[selectedIndex] : null;
  const selectedReturnIndex = Number.isInteger(option.selected_return_train_index) ? option.selected_return_train_index : -1;
  const selectedReturnTicket = selectedReturnIndex >= 0 ? returnTickets[selectedReturnIndex] : null;
  return `
    <div class="train-ticket-list compact-ticket-list">
      ${tickets.length ? `
        <label class="field-label" for="plan-train-ticket-select">去程车次候选</label>
        <select class="intent-input" id="plan-train-ticket-select" data-plan-train-select>
          <option value="">请选择去程车次</option>
          ${tickets.map((ticket, index) => `
            <option value="${index}" ${index === selectedIndex ? 'selected' : ''} ${ticket.available ? '' : 'disabled'}>
              ${escapeHtml(trainTicketOptionLabel(ticket))}
            </option>
          `).join('')}
        </select>
        ${selectedTicket ? renderTrainTicketSummary(selectedTicket) : ''}
        <button class="ghost-btn train-select-btn" type="button" data-train-ticket-apply>按所选去程重排</button>
      ` : ''}
      ${returnTickets.length ? `
        <label class="field-label" for="plan-return-train-ticket-select">返程车次候选</label>
        <select class="intent-input" id="plan-return-train-ticket-select" data-plan-return-train-select>
          <option value="">请选择返程车次</option>
          ${returnTickets.map((ticket, index) => `
            <option value="${index}" ${index === selectedReturnIndex ? 'selected' : ''} ${ticket.available ? '' : 'disabled'}>
              ${escapeHtml(trainTicketOptionLabel(ticket))}
            </option>
          `).join('')}
        </select>
        ${selectedReturnTicket ? renderTrainTicketSummary(selectedReturnTicket) : ''}
        <button class="ghost-btn train-select-btn" type="button" data-return-train-ticket-apply>按所选返程重算</button>
      ` : ''}
    </div>
  `;
}

function renderTrainTicketSummary(ticket) {
  return `
    <div class="train-ticket-summary">
      <div class="train-ticket-head">
        <strong>${escapeHtml(ticket.train_code || '车次待确认')}</strong>
        <span>${escapeHtml(ticket.depart_time || '--')} → ${escapeHtml(ticket.arrive_time || '--')}</span>
      </div>
      <p class="muted">${escapeHtml(ticket.from_station || '')} → ${escapeHtml(ticket.to_station || '')} · ${escapeHtml(ticket.duration_text || '时长待确认')}</p>
      ${ticket.transfer_note ? `<p class="muted warn-text">${escapeHtml(ticket.transfer_note)}</p>` : ''}
      ${renderTrainTicketSegments(ticket)}
      <p>${ticket.available ? `可售：${escapeHtml(ticket.seat_type)} ¥${formatNumber(ticket.one_way_cost)}` : '当前未找到可售座席'}</p>
      <p class="muted">${escapeHtml(formatSeatSummary(ticket.seats || []))}</p>
    </div>
  `;
}

function renderTrainTicketSegments(ticket) {
  const segments = ticket.segments || [];
  if (!segments.length) return '';
  return `
    <div class="train-segment-list">
      ${segments.map((segment) => `
        <p class="muted">${escapeHtml(segment.train_code || '')}：${escapeHtml(segment.from_station || '')} ${escapeHtml(segment.depart_time || '--')} → ${escapeHtml(segment.to_station || '')} ${escapeHtml(segment.arrive_time || '--')}</p>
      `).join('')}
    </div>
  `;
}

function formatSeatSummary(seats) {
  if (!seats.length) return '座席信息待12306返回';
  return seats.slice(0, 4).map((seat) => `${seat.seat_name}${seat.available ? seat.status : '无票'} ¥${formatNumber(seat.price)}`).join(' / ');
}

function intercitySourceLabel(option) {
  const source = typeof option === 'string' ? option : option && option.source;
  if (source === '12306_mcp' && option && option.ticket_selection_required) return '已查到候选车次';
  if (source === '12306_mcp' && option && option.ticket_query_error) return '已查询，费用暂用参考估算';
  if (source === '12306_mcp') return '实时车次';
  return '距离与规则估算';
}

function renderMobilityPolicy(policy) {
  if (!policy) return '';
  return `
    <section class="day-card compact-card">
      <h2>当地交通约束</h2>
      <div class="tool-row">
        <span class="tool-chip">偏好：${escapeHtml(policy.preference || '公共交通优先')}</span>
        ${(policy.constraints || []).map((item) => `<span class="tool-chip warn">${escapeHtml(item)}</span>`).join('')}
      </div>
      ${(policy.notes || []).map((note) => `<p class="muted">${escapeHtml(note)}</p>`).join('')}
    </section>
  `;
}

function renderScenicStatusSummary(summary) {
  if (!summary) return '';
  return `
    <section class="day-card compact-card">
      <h2>景区票价与公告</h2>
      <p class="muted">${escapeHtml(summary.summary)}</p>
      ${(summary.warnings || []).map((item) => `<p class="muted">· ${escapeHtml(item)}</p>`).join('')}
    </section>
  `;
}

function renderWeather(weather) {
  if (!weather || !weather.length) return '';
  return `
    <section class="day-card">
      <div class="section-header"><h2>天气</h2></div>
      <div class="weather-strip">
        ${weather.map((item) => `
          <div class="weather-card">
            <strong>${escapeHtml(item.date)}</strong>
            <p>${escapeHtml(item.day_weather)} / ${escapeHtml(item.night_weather)}</p>
            <p class="muted">${item.day_temp}°C - ${item.night_temp}°C · ${escapeHtml(item.wind_direction)}风 ${escapeHtml(item.wind_power)}</p>
          </div>
        `).join('')}
      </div>
    </section>
  `;
}

function renderDay(day) {
  const scheduledStops = scheduledDayStops(day);
  const flowItems = scheduledStops.map((stop, index) => {
    const nextStop = scheduledStops[index + 1];
    const route = nextStop ? findRouteBetween(day, stop, nextStop, index) : null;
    return `${renderStop(day, stop)}${route ? renderRouteConnector(route) : ''}`;
  }).join('');
  return `
    <section class="day-card">
      <div class="day-header">
        <div>
          <h2>${escapeHtml(day.title)} · ${escapeHtml(day.theme)}</h2>
          <p class="day-theme">${escapeHtml(day.date)} · ${escapeHtml(day.transportation)} · ${escapeHtml(day.day_start_time || '--')} 至 ${escapeHtml(day.day_end_time || '--')}</p>
          ${day.time_note ? `<p class="muted">${escapeHtml(day.time_note)}</p>` : ''}
        </div>
        ${day.hotel ? `<span class="status-pill">入住：${escapeHtml(day.hotel.name)}</span>` : ''}
      </div>
      ${renderTimeline(day)}
      <div class="flow-list">
        ${flowItems}
      </div>
    </section>
  `;
}

function renderTimeline(day) {
  const items = day.timeline || [];
  if (!items.length) return '';
  return `
    <div class="timeline-list">
      ${items.map((item) => renderTimelineItem(item)).join('')}
    </div>
  `;
}

function renderTimelineItem(item) {
  const related = item.related || {};
  const meta = timelineMeta(item, related);
  return `
    <div class="timeline-item ${escapeHtml(item.type || 'other')}">
      <div class="timeline-time">${escapeHtml(item.time_range || item.start_time || '')}</div>
      <div class="timeline-body">
        <div class="timeline-title-row">
          <span class="timeline-type">${escapeHtml(timelineTypeLabel(item.type))}</span>
          <strong>${escapeHtml(item.title || '')}</strong>
        </div>
        ${item.description ? `<p class="muted">${escapeHtml(item.description)}</p>` : ''}
        ${meta ? `<p class="timeline-meta">${escapeHtml(meta)}</p>` : ''}
      </div>
    </div>
  `;
}

function timelineTypeLabel(type) {
  const labels = {
    arrival: '到达',
    buffer: '机动',
    backup: '备选',
    meal: '用餐',
    route: '交通',
    stop: '游玩',
  };
  return labels[type] || '安排';
}

function timelineMeta(item, related) {
  if (item.type === 'route') {
    const parts = [related.mode, related.duration_min ? `${related.duration_min}分钟` : '', related.distance_km ? `${related.distance_km}km` : ''];
    return parts.filter(Boolean).join(' · ');
  }
  if (item.type === 'meal') {
    return item.estimated_cost ? `人均约¥${formatNumber(item.estimated_cost)}` : '';
  }
  if (item.type === 'stop') {
    return [
      related.category,
      related.business_hours ? `参考营业 ${related.business_hours}` : '',
      item.estimated_cost ? `参考门票¥${formatNumber(item.estimated_cost)}` : '',
    ].filter(Boolean).join(' · ');
  }
  if (item.type === 'backup') {
    return [related.category, related.business_hours ? `参考营业 ${related.business_hours}` : '', '未排入固定时间'].filter(Boolean).join(' · ');
  }
  if (item.type === 'arrival' && related.train_code) {
    return `车次 ${related.train_code}`;
  }
  return '';
}

function renderStop(day, stop) {
  const key = stopKey(day.day_index, stop.order);
  const scenicStatus = stop.scenic_status || {};
  return `
    <article class="flow-stop-card ${state.activeStopKey === key ? 'active' : ''}" role="button" tabindex="0" data-stop-card="true" data-day="${day.day_index}" data-order="${stop.order}">
      <div class="stop-card-top">
        <span class="stop-index-badge">${day.day_index + 1}-${stop.order}</span>
        <div class="stop-title-block">
          <span class="stop-name">${escapeHtml(stop.name)}</span>
          <span class="stop-category-pill">${escapeHtml(stop.category)}</span>
        </div>
        <span class="stop-action">查看</span>
      </div>
      <p class="stop-summary">${escapeHtml(stop.description)}</p>
      <div class="stop-meta-grid">
        <span class="metric-chip">停留 ${stop.visit_duration} 分钟</span>
        ${stop.business_hours ? `<span class="metric-chip">参考营业 ${escapeHtml(stop.business_hours)}</span>` : ''}
        <span class="metric-chip ${ticketNeedsCheck(stop) ? 'warn' : ''}">${escapeHtml(formatTicketLabel(scenicStatus || stop.ticket_price))}</span>
        ${stop.scenic_status ? `<span class="metric-chip ${stop.scenic_status.needs_official_check ? 'warn' : ''}">${escapeHtml(stop.scenic_status.open_status)}</span>` : ''}
        <span class="metric-chip">点开看住宿</span>
      </div>
    </article>
  `;
}

function findRouteBetween(day, stop, nextStop, index) {
  return (day.routes || []).find((route) => route.from === stop.name && route.to === nextStop.name) || (day.routes || [])[index] || null;
}

function renderRouteConnector(route) {
  return `
    <div class="flow-connector">
      <span class="connector-line" aria-hidden="true"></span>
      <div class="flow-route-card">
        <span class="route-mode">${escapeHtml(route.mode)}</span>
        <span class="route-text">${escapeHtml(route.from)} → ${escapeHtml(route.to)}</span>
        <span class="route-meta">${route.distance_km}km · ${route.duration_min}min · 约¥${formatNumber(route.estimated_cost)}${route.warnings && route.warnings.length ? ' · 有约束提醒' : ''}</span>
      </div>
    </div>
  `;
}

function renderHotelInsights(insights) {
  if (!insights || !insights.available) return '';
  const focusPoints = insights.focus_points || [];
  return `
    <section class="day-card">
      <h2>住宿评价参考</h2>
      <p class="muted">${escapeHtml(insights.summary)}</p>
      <p class="muted">具体评论摘录已放进每个酒店的详情里，点开“查看酒店信息”即可查看。</p>
      <div class="tool-row">
        ${focusPoints.map((item) => `<span class="tool-chip">${escapeHtml(item)}</span>`).join('')}
      </div>
    </section>
  `;
}

function renderRagContext(context) {
  if (!context || !context.length) return '';
  return `
    <section class="day-card">
      <h2>参考资料</h2>
      <div class="rag-grid">
        ${context.map((item) => `
          <div class="rag-card">
            <strong>${escapeHtml(item.title)} / ${escapeHtml(item.section)}</strong>
            <p class="muted">${escapeHtml(item.text)}</p>
          </div>
        `).join('')}
      </div>
    </section>
  `;
}

function bindPlanInteractions() {
  bindTrainTicketButtons();
  document.querySelectorAll('[data-stop-card]').forEach((card) => {
    const open = () => {
      const dayIndex = Number(card.dataset.day);
      const order = Number(card.dataset.order);
      const day = state.plan.days[dayIndex];
      const stop = day.stops.find((item) => item.order === order);
      if (stop) openDrawer(day, stop);
    };
    card.addEventListener('click', open);
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        open();
      }
    });
  });
}

function bindTrainTicketButtons() {
  document.querySelectorAll('[data-train-ticket-apply]').forEach((button) => {
    button.addEventListener('click', () => {
      const select = document.querySelector('[data-plan-train-select]');
      if (!select || select.value === '') return;
      selectTrainTicket(Number(select.value));
    });
  });
  document.querySelectorAll('[data-return-train-ticket-apply]').forEach((button) => {
    button.addEventListener('click', () => {
      const select = document.querySelector('[data-plan-return-train-select]');
      if (!select || select.value === '') return;
      selectReturnTrainTicket(Number(select.value));
    });
  });
}

async function selectTrainTicket(index) {
  const intercity = state.plan && state.plan.intercity_transport;
  if (!intercity || !state.intent) return;
  const option = (intercity.options || []).find((item) => item.mode === '高铁/火车' && item.train_tickets);
  if (!option) return;
  const ticket = (option.train_tickets || [])[index];
  if (!ticket || !ticket.available) return;

  syncIntentFromControls();
  state.intent.intercity_transportation = '高铁/火车';
  state.intent.intercity_options = ['高铁/火车'];
  syncPlanPayloadFromIntent();
  state.intent.plan_payload.selected_train_index = index;
  state.intent.plan_payload.selected_train_ticket = compactTrainTicket(ticket);
  state.intent.plan_payload.intercity_transportation = '高铁/火车';
  state.intent.plan_payload.intercity_options = ['高铁/火车'];

  const button = document.querySelector(`[data-train-ticket="${index}"]`);
  await submitPlanRequest(
    state.intent.plan_payload,
    button,
    '重排中',
    index === option.selected_train_index ? '已按此车次排时间' : '按此车次排时间',
  );
}

async function selectReturnTrainTicket(index) {
  const intercity = state.plan && state.plan.intercity_transport;
  if (!intercity || !state.intent) return;
  const option = (intercity.options || []).find((item) => item.mode === '高铁/火车' && item.return_train_tickets);
  if (!option) return;
  const ticket = (option.return_train_tickets || [])[index];
  if (!ticket || !ticket.available) return;

  syncIntentFromControls();
  state.intent.intercity_transportation = '高铁/火车';
  state.intent.intercity_options = ['高铁/火车'];
  syncPlanPayloadFromIntent();
  state.intent.plan_payload.selected_return_train_index = index;
  state.intent.plan_payload.selected_return_train_ticket = compactTrainTicket(ticket);
  state.intent.plan_payload.intercity_transportation = '高铁/火车';
  state.intent.plan_payload.intercity_options = ['高铁/火车'];

  const button = document.querySelector('[data-return-train-ticket-apply]');
  await submitPlanRequest(
    state.intent.plan_payload,
    button,
    '重排中',
    index === option.selected_return_train_index ? '已按此返程排费用' : '按此返程重算',
  );
}

function updateBudgetForIntercity(option) {
  const budget = state.plan && state.plan.budget;
  if (!budget) return;
  budget.total_intercity_transportation = Number(option.estimated_cost || 0);
  budget.total = budget.intercity_included ? Number(budget.local_total || 0) + budget.total_intercity_transportation : Number(budget.local_total || 0);
  budget.remaining = budget.budget_limit ? budget.budget_limit - budget.total : null;
  budget.is_over_budget = Boolean(budget.budget_limit && budget.total > budget.budget_limit);
}

function openDrawer(day, stop) {
  state.activeStopKey = stopKey(day.day_index, stop.order);
  drawerContent.innerHTML = `
    <p class="eyebrow">${escapeHtml(day.title)} · 第${stop.order}站</p>
    <h2>${escapeHtml(stop.name)}</h2>
    <p class="muted">${escapeHtml(stop.category)} · 建议停留 ${stop.visit_duration} 分钟</p>
    <h3>地点信息</h3>
    <p>${escapeHtml(stop.description)}</p>
    <p class="muted">地址：${escapeHtml(stop.address || '以地图查询为准')}</p>
    ${stop.business_hours ? `<p class="muted">参考营业/适游时间：${escapeHtml(stop.business_hours)}</p>` : ''}
    <p class="muted">坐标：${stop.location.longitude.toFixed(5)}, ${stop.location.latitude.toFixed(5)}</p>
    ${renderScenicStatus(stop.scenic_status)}
    ${renderDrawerRoute(day, stop)}
    <h3>附近住宿</h3>
    <div class="hotel-list">${(stop.nearby_hotels || []).map((hotel, index) => renderHotel(hotel, index)).join('')}</div>
  `;
  bindHotelDetailButtons(day, stop);
  drawer.classList.add('open');
  drawer.setAttribute('aria-hidden', 'false');
  renderPlan();
  renderMap();
}

function renderDrawerRoute(day, stop) {
  const previous = (day.routes || []).find((item) => item.to === stop.name);
  const next = (day.routes || []).find((item) => item.from === stop.name);
  if (!previous && !next) return '';
  return `
    <h3>站间交通</h3>
    ${previous ? `<p>${escapeHtml(previous.description)}</p>${renderRouteWarnings(previous)}` : ''}
    ${next ? `<p>${escapeHtml(next.description)}</p>${renderRouteWarnings(next)}` : ''}
  `;
}

function renderRouteWarnings(route) {
  if (!route || !route.warnings || !route.warnings.length) return '';
  return route.warnings.map((warning) => `<p class="muted">· ${escapeHtml(warning)}</p>`).join('');
}

function renderScenicStatus(status) {
  if (!status) return '';
  return `
    <h3>票价与公告</h3>
    <p class="muted">门票：${escapeHtml(formatTicketLabel(status))} · 状态：${escapeHtml(status.open_status)} · 来源：${escapeHtml(ticketSourceLabel(status.ticket_source || status.source))}</p>
    ${status.price_note ? `<p class="muted">${escapeHtml(status.price_note)}</p>` : ''}
    <p class="muted">${escapeHtml(status.announcement)}</p>
    ${status.web_source_url ? `<p class="muted">搜索来源：${escapeHtml(status.web_source_title || status.web_source_url)}</p>` : ''}
    <p class="muted">${escapeHtml(status.official_check_note || '景区是否开放请以景区官网或官方购票平台为准。')}</p>
  `;
}

function formatTicketLabel(value) {
  const status = typeof value === 'object' && value !== null ? value : null;
  const price = Number(status ? status.ticket_price : value || 0);
  const source = status ? status.ticket_source || status.source : '';
  if (price >= 1000) return '票价待核验';
  if (!price) {
    if (['web_search', 'knowledge_base', 'fallback_known', 'reference_estimate'].includes(source)) return '免费/无需门票';
    return '票价待核验';
  }
  return `${status && status.ticket_price_is_estimated ? '参考门票' : '门票'} ¥${formatNumber(price)}`;
}

function ticketNeedsCheck(stop) {
  const scenicStatus = stop.scenic_status || {};
  const price = Number(scenicStatus.ticket_price ?? stop.ticket_price ?? 0);
  return !price || price >= 1000 || scenicStatus.needs_official_check;
}

function ticketSourceLabel(source) {
  const labels = {
    web_search: '联网搜索',
    knowledge_base: '本地资料',
    fallback_known: '预设参考',
    fallback_rule: '规则参考',
    reference_estimate: '参考价估算',
  };
  return labels[source] || source || '参考信息';
}

function renderHotel(hotel, index) {
  return `
    <div class="hotel-mini">
      <strong>${escapeHtml(hotel.name)}</strong>
      <p class="muted">${escapeHtml(hotel.type)} · ${escapeHtml(hotel.price_range)} · ${escapeHtml(hotel.rating)}</p>
      <p class="muted">${escapeHtml(hotel.address)} · ${escapeHtml(hotel.distance)}</p>
      ${hotel.review_profile ? '<p class="muted">含住客评论详情</p>' : ''}
      <button class="hotel-detail-btn" type="button" data-hotel-index="${index}">查看酒店信息</button>
    </div>
  `;
}

function bindHotelDetailButtons(day, stop) {
  drawerContent.querySelectorAll('[data-hotel-index]').forEach((button) => {
    button.addEventListener('click', () => {
      const hotel = (stop.nearby_hotels || [])[Number(button.dataset.hotelIndex)];
      if (hotel) openHotelDetail(day, stop, hotel);
    });
  });
}

function openHotelDetail(day, stop, hotel) {
  const insights = state.plan.hotel_review_insights;
  const reviewProfile = hotel.review_profile || hotelReviewProfileFromInsights(insights);
  const coordinate = hotel.location
    ? `${Number(hotel.location.longitude).toFixed(5)}, ${Number(hotel.location.latitude).toFixed(5)}`
    : '以地图查询为准';
  drawerContent.innerHTML = `
    <button class="back-btn" type="button" id="hotel-back">返回地点</button>
    <p class="eyebrow">${escapeHtml(stop.name)}附近住宿</p>
    <h2>${escapeHtml(hotel.name)}</h2>
    <p class="muted">${escapeHtml(hotel.type)} · ${escapeHtml(hotel.distance)} · ${escapeHtml(hotel.source || 'fallback')}</p>
    <h3>酒店信息</h3>
    <p class="muted">价格：${escapeHtml(hotel.price_range || '暂无价格')}</p>
    <p class="muted">评分：${escapeHtml(hotel.rating || '暂无评分')}</p>
    <p class="muted">地址：${escapeHtml(hotel.address || '以地图查询为准')}</p>
    <p class="muted">电话：${escapeHtml(hotel.tel || '暂无电话')}</p>
    <p class="muted">坐标：${escapeHtml(coordinate)}</p>
    ${renderHotelReviewProfile(reviewProfile)}
  `;
  document.querySelector('#hotel-back').addEventListener('click', () => openDrawer(day, stop));
}

function hotelReviewProfileFromInsights(insights) {
  if (!insights || !insights.available) return null;
  return {
    title: '住客评论参考',
    summary: insights.summary,
    focus_points: insights.focus_points || [],
    sections: insights.detail_sections || [],
    booking_tips: insights.booking_tips || [],
    source_note: '评论摘录来自本地酒店评论资料；具体酒店请以订房平台的最新评价、实拍图和退改规则为准。',
  };
}

function renderHotelReviewProfile(profile) {
  if (!profile) return '';
  const sections = profile.sections || [];
  const focusPoints = profile.focus_points || [];
  const tips = profile.booking_tips || [];
  return `
    <h3>${escapeHtml(profile.title || '住客评论参考')}</h3>
    <p class="muted">${escapeHtml(profile.summary || '')}</p>
    ${focusPoints.length ? `
      <div class="tool-row review-focus-row">
        ${focusPoints.map((item) => `<span class="tool-chip">${escapeHtml(item)}</span>`).join('')}
      </div>
    ` : ''}
    <div class="review-section-list">
      ${sections.map(renderHotelReviewSection).join('')}
    </div>
    ${tips.length ? `
      <div class="review-tip-box">
        <strong>订房前重点核对</strong>
        ${tips.map((tip) => `<p class="muted">· ${escapeHtml(tip)}</p>`).join('')}
      </div>
    ` : ''}
    ${profile.source_note ? `<p class="muted">${escapeHtml(profile.source_note)}</p>` : ''}
  `;
}

function renderHotelReviewSection(section) {
  const examples = section.examples || [];
  return `
    <section class="review-section ${section.tone === 'risk' ? 'risk' : ''}">
      <div class="review-section-head">
        <strong>${escapeHtml(section.title || '评论摘录')}</strong>
        <span>${escapeHtml(reviewToneLabel(section.tone))}</span>
      </div>
      <p class="muted">${escapeHtml(section.takeaway || '')}</p>
      ${examples.map(renderHotelReviewExample).join('')}
    </section>
  `;
}

function renderHotelReviewExample(example) {
  const cues = example.cues || [];
  return `
    <blockquote class="review-example">
      <div class="review-example-head">
        <span>${escapeHtml(example.rating ? `${example.rating}/5` : '评分未标注')}</span>
        <span>${cues.map((item) => escapeHtml(item)).join(' · ')}</span>
      </div>
      <p>${escapeHtml(example.excerpt || '')}</p>
    </blockquote>
  `;
}

function reviewToneLabel(tone) {
  if (tone === 'risk') return '避坑';
  if (tone === 'mixed') return '需核对';
  return '可参考';
}

function closeDrawer() {
  drawer.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
}

async function openMapModal() {
  mapModal.classList.add('open');
  mapModal.setAttribute('aria-hidden', 'false');
  if (state.plan) {
    window.setTimeout(() => renderMap(largeMapNode), 80);
  } else {
    resetMap(largeMapNode);
  }
}

function closeMapModal() {
  mapModal.classList.remove('open');
  mapModal.setAttribute('aria-hidden', 'true');
}

async function renderMap(targetNode = mapNode) {
  if (!state.plan) return;
  if (state.config && state.config.amap_js_key) {
    try {
      await renderAmap(targetNode);
      return;
    } catch (error) {
      console.warn('AMap render failed, using fallback map.', error);
    }
  }
  renderFallbackMap(targetNode);
}

async function loadAmap() {
  if (window.AMap) return window.AMap;
  if (!state.config || !state.config.amap_js_key) throw new Error('No AMap JS key');
  if (state.config.amap_security_js_code) {
    window._AMapSecurityConfig = { securityJsCode: state.config.amap_security_js_code };
  }
  await new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(state.config.amap_js_key)}`;
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
  return window.AMap;
}

async function renderAmap(targetNode = mapNode) {
  const AMap = await loadAmap();
  targetNode.innerHTML = '';
  const map = new AMap.Map(targetNode, {
    zoom: 12,
    viewMode: '2D',
    mapStyle: 'amap://styles/normal',
  });
  if (targetNode === largeMapNode) state.largeMap = map;
  else state.map = map;
  const points = collectStops();
  const overlays = [];
  points.forEach((item) => {
    const marker = new AMap.Marker({
      position: [item.stop.location.longitude, item.stop.location.latitude],
      label: { content: `${item.day.day_index + 1}-${item.stop.order}`, direction: 'top' },
      title: item.stop.name,
    });
    marker.on('click', () => openDrawer(item.day, item.stop));
    overlays.push(marker);
  });
  map.add(overlays);
  const dayGroups = groupBy(points, (item) => item.day.day_index);
  Object.values(dayGroups).forEach((group) => {
    const path = group.map((item) => [item.stop.location.longitude, item.stop.location.latitude]);
    if (path.length > 1) {
      map.add(new AMap.Polyline({ path, strokeColor: '#116a72', strokeWeight: 5, strokeOpacity: 0.82 }));
    }
  });
  if (overlays.length) map.setFitView(overlays, false, [50, 50, 50, 50]);
}

function renderFallbackMap(targetNode = mapNode) {
  const points = collectStops();
  const bounds = getBounds(points);
  targetNode.innerHTML = '<svg class="fallback-map-svg"></svg>';
  const svg = targetNode.querySelector('svg');
  const dayGroups = groupBy(points, (item) => item.day.day_index);
  Object.values(dayGroups).forEach((group) => {
    for (let i = 0; i < group.length - 1; i += 1) {
      const a = project(group[i].stop.location, bounds);
      const b = project(group[i + 1].stop.location, bounds);
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', `${a.x}%`);
      line.setAttribute('y1', `${a.y}%`);
      line.setAttribute('x2', `${b.x}%`);
      line.setAttribute('y2', `${b.y}%`);
      line.setAttribute('stroke', '#116a72');
      line.setAttribute('stroke-width', '3');
      line.setAttribute('stroke-linecap', 'round');
      svg.appendChild(line);
    }
  });
  points.forEach((item) => {
    const point = project(item.stop.location, bounds);
    const marker = document.createElement('button');
    marker.type = 'button';
    marker.className = 'map-marker';
    marker.textContent = `${item.day.day_index + 1}-${item.stop.order}`;
    marker.style.left = `${point.x}%`;
    marker.style.top = `${point.y}%`;
    marker.title = item.stop.name;
    marker.addEventListener('click', () => openDrawer(item.day, item.stop));
    targetNode.appendChild(marker);
  });
}

function collectStops() {
  if (!state.plan) return [];
  return state.plan.days.flatMap((day) => scheduledDayStops(day).map((stop) => ({ day, stop })));
}

function scheduledDayStops(day) {
  return (day.stops || []).filter((stop) => stop.scheduled !== false);
}

function getBounds(points) {
  const lons = points.map((item) => item.stop.location.longitude);
  const lats = points.map((item) => item.stop.location.latitude);
  return {
    minLon: Math.min(...lons),
    maxLon: Math.max(...lons),
    minLat: Math.min(...lats),
    maxLat: Math.max(...lats),
  };
}

function project(location, bounds) {
  const lonSpan = Math.max(bounds.maxLon - bounds.minLon, 0.01);
  const latSpan = Math.max(bounds.maxLat - bounds.minLat, 0.01);
  return {
    x: 8 + ((location.longitude - bounds.minLon) / lonSpan) * 84,
    y: 92 - ((location.latitude - bounds.minLat) / latSpan) * 84,
  };
}

function groupBy(items, getKey) {
  return items.reduce((acc, item) => {
    const key = getKey(item);
    acc[key] = acc[key] || [];
    acc[key].push(item);
    return acc;
  }, {});
}

function stopKey(dayIndex, order) {
  return `${dayIndex}-${order}`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN');
}

function formatBudgetSummary(value) {
  const amount = Number(value || 0);
  return amount ? `${formatNumber(amount)}元` : '未提供';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
