let TOKEN = '';
const BASE = window.location.origin;
let CONFIG_CACHE = {};
const AUTH_TOKEN_KEY = 'eaglerx_admin_token';
const AUTH_TOKEN_EXP_KEY = 'eaglerx_admin_token_exp';
let PLAYERS_TIMER = null;
let TPS_TIMER = null;
let WORLD_INFO_TIMER = null;
let WORLD_INFO_REFRESH_HANDLE = null;
let WORLD_INFO_REFRESH_FORCE = false;
let RUNTIME_REFRESH_HANDLE = null;
let PAPER_REFRESHING = false;
let PAPER_STATUS = { state: 'checking', elapsed_seconds: null };
let PAPER_STATUS_TIMER = null;
const PAPER_MESSAGES = {
  checking: ['status.paper.checking', 'status.paper.checkingHint'],
  starting: ['status.paper.starting', 'status.paper.startingHint'],
  ready: ['status.paper.ready', ''],
  stopped: ['status.paper.stopped', 'status.paper.stoppedHint'],
  unavailable: ['status.paper.unavailable', 'status.paper.unavailableHint'],
  offline: ['status.paper.offline', 'status.paper.offlineHint'],
  disabled: ['status.rconDisabled', '']
};
let SERVER_INFO = { minecraftVersion: '', rconPort: '', bridgePort: '', nativeSeedFinderReady: false, serverVersionText: '' };
let CONNECTION_INFO = { state: 'loading' };
let WORLD_INFO_CACHE = null;
let WORLD_SEED = '';
let STRUCTURE_QUERY = { x: 0, z: 0, radius: 5000, limitPerType: 8 };
let LAST_STRUCTURE_RESULT = null;
let LAST_STRUCTURE_CONTEXT = null;
let ONLINE_PLAYERS = [];
let REFRESH_IN_FLIGHT = {};
let STATUS_STATE = { state: 'off', text: '' };
let VERSION_STATE = '';
let TPS_VALUES = [];
let ACTIVE_TOAST = null;
let CONSOLE_HISTORY = [];
let SOURCE_MESSAGE_KEYS = Object.create(null);
let SEED_STATE = { seed: '', hint: null, rawHint: null };
let STRUCTURE_STATUS_STATE = { text: null, summary: null, rawSummary: null };
let STRUCTURE_PLACEHOLDER_STATE = { text: null, rawPayload: null };
let PLUGIN_INVENTORY = null;
let PLUGIN_UPLOAD_IN_FLIGHT = false;
let PLUGIN_TRANSITION_IN_FLIGHT = false;
const CONNECTION_SOURCE_KEYS = {
  loading: 'status.connection.sourceLoading',
  configured: 'status.connection.sourceConfigured',
  inferred: 'status.connection.sourceInferred',
  invalid: 'status.connection.sourceError',
  unavailable: 'status.connection.sourceUnavailable'
};
const STRUCTURE_LABEL_KEYS = {
  village: 'structure.type.village',
  stronghold: 'structure.type.stronghold',
  desert_pyramid: 'structure.type.desert_pyramid',
  monument: 'structure.type.monument',
  jungle_temple: 'structure.type.jungle_temple',
  swamp_hut: 'structure.type.swamp_hut',
  igloo: 'structure.type.igloo',
  mansion: 'structure.type.mansion',
  spawn: 'structure.type.spawn'
};
const REFRESH_INTERVALS = {
  players: 20000,
  tps: 30000,
  world: 30000
};

function t(key, params) {
  return window.EaglerXI18n ? EaglerXI18n.t(key, params) : key;
}

function localize(source) {
  if (!window.EaglerXI18n) return String(source == null ? '' : source);
  var value = String(source == null ? '' : source);
  if (SOURCE_MESSAGE_KEYS[value]) return t(SOURCE_MESSAGE_KEYS[value]);
  var messages = EaglerXI18n.locales['zh-CN'].messages;
  var keys = Object.keys(messages);
  for (var index = 0; index < keys.length; index += 1) {
    if (messages[keys[index]] === value) {
      SOURCE_MESSAGE_KEYS[value] = keys[index];
      return t(keys[index]);
    }
  }
  return value;
}

function presentation(key, params) {
  return { key: key, params: params || {} };
}

function renderPresentation(value) {
  if (!value || typeof value !== 'object' || !value.key) return localize(value || '');
  var params = {};
  Object.keys(value.params || {}).forEach(function (name) {
    var param = value.params[name];
    params[name] = param && typeof param === 'object' && param.key ? renderPresentation(param) : String(param == null ? '' : param);
  });
  return t(value.key, params);
}

function formatNumber(value, options) {
  return new Intl.NumberFormat(EaglerXI18n.getLocale(), options).format(Number(value || 0));
}

function formatUiTime(date) {
  return new Intl.DateTimeFormat(EaglerXI18n.getLocale(), {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
  }).format(date || new Date());
}

function isRegisteredLocale(localeId) {
  return !!(window.EaglerXI18n && Object.prototype.hasOwnProperty.call(EaglerXI18n.locales, localeId));
}

function readLocalePreference() {
  var fallback = EaglerXI18n.DEFAULT_LOCALE;
  try {
    var stored = localStorage.getItem(EaglerXI18n.PREFERENCE_KEY);
    if (isRegisteredLocale(stored)) return stored;
    if (stored !== null) localStorage.removeItem(EaglerXI18n.PREFERENCE_KEY);
  } catch (e) { }
  return fallback;
}

function persistLocalePreference(localeId) {
  try {
    localStorage.setItem(EaglerXI18n.PREFERENCE_KEY, localeId);
  } catch (e) { }
}

function updateLocaleLabels() {
  var selector = document.getElementById('locale-select');
  if (!selector || !selector.options) return;
  Array.prototype.forEach.call(selector.options, function (option) {
    var locale = EaglerXI18n.locales[option.value];
    option.textContent = locale ? locale.label : option.value;
  });
}

function applyStaticLocale(localeId) {
  if (!window.EaglerXI18n) return;
  var activeLocale = EaglerXI18n.setLocale(isRegisteredLocale(localeId) ? localeId : EaglerXI18n.DEFAULT_LOCALE);
  var bindingAttributes = [
    ['data-i18n', 'textContent'],
    ['data-i18n-title', 'title'],
    ['data-i18n-placeholder', 'placeholder'],
    ['data-i18n-aria-label', 'aria-label']
  ];
  document.documentElement.lang = activeLocale;
  var documentTitle = document.querySelector('title[data-i18n]');
  document.title = EaglerXI18n.t(documentTitle ? documentTitle.getAttribute('data-i18n') : 'header.title');
  bindingAttributes.forEach(function (binding) {
    Array.prototype.forEach.call(document.querySelectorAll('[' + binding[0] + ']'), function (element) {
      var value = EaglerXI18n.t(element.getAttribute(binding[0]));
      if (binding[1] === 'textContent') element.textContent = value;
      else element.setAttribute(binding[1], value);
    });
  });
  var selector = document.getElementById('locale-select');
  if (selector) {
    selector.value = activeLocale;
    updateLocaleLabels();
  }
  rerenderLocalizedState();
}

function setupLocalePreference() {
  if (!window.EaglerXI18n) return;
  var selector = document.getElementById('locale-select');
  if (!selector) return;
  selector.textContent = '';
  Object.keys(EaglerXI18n.locales).forEach(function (localeId) {
    var option = document.createElement('option');
    option.value = localeId;
    option.textContent = EaglerXI18n.locales[localeId].label;
    selector.appendChild(option);
  });
  applyStaticLocale(readLocalePreference());
  selector.addEventListener('change', function () {
    var localeId = isRegisteredLocale(selector.value) ? selector.value : EaglerXI18n.DEFAULT_LOCALE;
    applyStaticLocale(localeId);
    persistLocalePreference(localeId);
  });
}

var LOADING_CARD_IDS = ['card-world','card-players','card-tps','card-rules','card-config','card-whitelist','card-seedmap','card-plugins'];
function setCardLoading(id,on){var el=document.getElementById(id);if(!el)return;if(on){el.classList.add('card-loading');el.style.position='relative'}else{el.classList.remove('card-loading')}}
function setAllCardsLoading(on){for(var i=0;i<LOADING_CARD_IDS.length;i++)setCardLoading(LOADING_CARD_IDS[i],on)}
function beginRefresh(name){if(REFRESH_IN_FLIGHT[name])return false;if(!paperReady()&&['players','tps','world','runtime','seedmap'].indexOf(name)!==-1)return false;REFRESH_IN_FLIGHT[name]=true;return true}
function endRefresh(name){REFRESH_IN_FLIGHT[name]=false}
function shouldAutoPoll(){return !document.hidden && !!TOKEN}

function renderConsoleEntry(entry) {
  const c = document.getElementById('console');
  const div = document.createElement('div');
  const ts = document.createElement('span');
  ts.className = 'ts';
  ts.textContent = formatUiTime(entry.date);
  div.appendChild(ts);
  const body = document.createElement('span');
  body.className = entry.cls || 'out';
  body.textContent = entry.kind === 'raw' ? entry.payload : (entry.key ? renderPresentation(entry) : localize(entry.source));
  div.appendChild(body);
  c.appendChild(div);
}

function renderConsoleHistory() {
  const c = document.getElementById('console');
  if (!c) return;
  var wasAtBottom = c.scrollTop + c.clientHeight >= c.scrollHeight - 2;
  c.textContent = '';
  CONSOLE_HISTORY.forEach(renderConsoleEntry);
  if (wasAtBottom) c.scrollTop = c.scrollHeight;
}

function log(msg, cls) {
  CONSOLE_HISTORY.push({ kind: 'client', source: String(msg == null ? '' : msg), cls: cls || 'out', date: new Date() });
  renderConsoleHistory();
}

function logClient(key, params, cls) {
  CONSOLE_HISTORY.push({ kind: 'client', key: key, params: params || {}, cls: cls || 'out', date: new Date() });
  renderConsoleHistory();
}

function logRaw(payload, cls) {
  CONSOLE_HISTORY.push({ kind: 'raw', payload: String(payload == null ? '' : payload), cls: cls || 'out', date: new Date() });
  renderConsoleHistory();
}

function renderToast() {
  const toastElement = document.getElementById('toast');
  if (!toastElement || !ACTIVE_TOAST) return;
  toastElement.textContent = ACTIVE_TOAST.raw != null ? ACTIVE_TOAST.raw : (ACTIVE_TOAST.key ? renderPresentation(ACTIVE_TOAST) : localize(ACTIVE_TOAST.source));
  if (Date.now() >= ACTIVE_TOAST.deadline) {
    toastElement.classList.remove('show');
    return;
  }
  toastElement.classList.add('show');
}

function toast(msg) {
  ACTIVE_TOAST = { source: String(msg == null ? '' : msg), deadline: Date.now() + 2000 };
  const toastElement = document.getElementById('toast');
  renderToast();
  clearTimeout(toastElement._t);
  toastElement._t = setTimeout(function () { toastElement.classList.remove('show'); }, 2000);
}

function toastClient(key, params) {
  ACTIVE_TOAST = { key: key, params: params || {}, deadline: Date.now() + 2000 };
  const toastElement = document.getElementById('toast');
  renderToast();
  clearTimeout(toastElement._t);
  toastElement._t = setTimeout(function () { toastElement.classList.remove('show'); }, 2000);
}

function toastRaw(payload) {
  ACTIVE_TOAST = { raw: String(payload == null ? '' : payload), deadline: Date.now() + 2000 };
  const toastElement = document.getElementById('toast');
  toastElement.textContent = ACTIVE_TOAST.raw;
  toastElement.classList.add('show');
  clearTimeout(toastElement._t);
  toastElement._t = setTimeout(function () { toastElement.classList.remove('show'); }, 2000);
}

async function copyText(value) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(value);
      return true;
    } catch (error) { }
  }
  var input = document.createElement('textarea');
  input.value = value;
  input.setAttribute('readonly', 'readonly');
  input.style.position = 'fixed';
  input.style.left = '-9999px';
  document.body.appendChild(input);
  try {
    input.select();
    return !!document.execCommand('copy');
  } finally {
    document.body.removeChild(input);
  }
}

function setStatus(state, text) {
  STATUS_STATE = { state: state, text: text || '' };
  renderStatus();
}

function renderStatus() {
  var state = STATUS_STATE.state;
  var text = renderPresentation(STATUS_STATE.text);
  if (!paperReady() && PAPER_STATUS.state !== 'disabled') {
    state = PAPER_STATUS.state === 'starting' || PAPER_STATUS.state === 'checking' ? 'auth' : 'off';
    text = t(paperTitleKey());
  }
  var d = document.getElementById('status-dot');
  d.className = state;
  document.getElementById('status-text').textContent = text;
  var heroConnection = document.getElementById('hero-connection');
  if (heroConnection) heroConnection.textContent = text || localize(state === 'on' ? '已连接' : '未连接');
}

function paperReady() {
  return PAPER_STATUS.state === 'ready';
}

function paperTitleKey() {
  if (PAPER_STATUS.state === 'starting' && PAPER_STATUS.elapsed_seconds >= 180) return 'status.paper.slow';
  return PAPER_MESSAGES[PAPER_STATUS.state][0];
}

function renderPaperStatus() {
  var banner = document.getElementById('paper-status');
  if (!banner) return;
  var waiting = !paperReady() && PAPER_STATUS.state !== 'disabled';
  var starting = PAPER_STATUS.state === 'starting';
  document.getElementById('world-health').textContent = t(paperTitleKey());
  document.getElementById('world-health').className = 'world-health ' + (paperReady() ? 'ready' : 'waiting');
  banner.classList.toggle('hidden', !waiting);
  banner.classList.toggle('paper-error', ['stopped', 'unavailable', 'offline'].indexOf(PAPER_STATUS.state) !== -1);
  if (waiting) {
    var title = t(paperTitleKey());
    var detailKey = starting && PAPER_STATUS.elapsed_seconds >= 180 ? 'status.paper.slowHint' : PAPER_MESSAGES[PAPER_STATUS.state][1];
    var detail = t(detailKey);
    var titleEl = document.getElementById('paper-status-title');
    var detailEl = document.getElementById('paper-status-detail');
    if (titleEl.textContent !== title) titleEl.textContent = title;
    if (detailEl.textContent !== detail) detailEl.textContent = detail;
    var seconds = Math.max(0, Number(PAPER_STATUS.elapsed_seconds) || 0);
    document.getElementById('paper-status-elapsed').textContent = starting && PAPER_STATUS.elapsed_seconds != null
      ? t('status.paper.elapsed', { minutes: formatNumber(Math.floor(seconds / 60)), seconds: formatNumber(seconds % 60) }) : '';
    document.getElementById('paper-status-progress').classList.toggle('hidden', !starting && PAPER_STATUS.state !== 'checking');
    setWorldInfoPlaceholder(t('status.paper.worldWaiting'));
    clearWorldControlState();
    document.getElementById('players').innerHTML = '<div class="empty-state">' + escapeHtml(t('status.paper.dataWaiting')) + '</div>';
    document.getElementById('tps-bars').innerHTML = '<div class="empty-state">' + escapeHtml(t('status.paper.dataWaiting')) + '</div>';
    ['hero-player-count', 'player-count', 'hero-tps'].forEach(function (id) { document.getElementById(id).textContent = '--'; });
  }
  document.querySelectorAll('[data-paper-controls], [data-paper-action]').forEach(function (element) { element.disabled = !paperReady(); });
  document.querySelectorAll('[onclick="restartServer()"]').forEach(function (element) {
    element.disabled = ['checking', 'starting', 'disabled'].indexOf(PAPER_STATUS.state) !== -1;
  });
  renderStatus();
}

function setPaperStatus(status) {
  var previous = PAPER_STATUS.state;
  PAPER_STATUS = status && Object.prototype.hasOwnProperty.call(PAPER_MESSAGES, status.state)
    ? status : { state: 'unavailable', elapsed_seconds: null };
  if (!paperReady()) {
    WORLD_INFO_CACHE = null;
    setAllCardsLoading(false);
  }
  renderPaperStatus();
  renderConnectionInfo();
  if (paperReady() && previous !== 'ready' && TOKEN && STATUS_STATE.state === 'on') {
    toastClient('status.paper.ready');
    refreshPaperDashboard();
  }
}

async function refreshPaperStatus() {
  if (!beginRefresh('paper')) return;
  try {
    var response = await fetch(BASE + '/api/status', { cache: 'no-store', signal: AbortSignal.timeout(8000) });
    if (response.status === 404) {
      if (PAPER_STATUS.state !== 'disabled') logClient('console.rconDisabled', {}, 'warn');
      SERVER_INFO = { minecraftVersion: '', rconPort: '', bridgePort: '', nativeSeedFinderReady: false, serverVersionText: '' };
      setPaperStatus({ state: 'disabled' });
      setStatus('off', presentation('status.rconDisabled'));
      setVersion(presentation('status.rconDisabled'));
      setSeedState('', presentation('status.rconSeedHint'));
      return;
    }
    if (!response.ok) throw new Error('status unavailable');
    var data = await response.json();
    SERVER_INFO.minecraftVersion = data.minecraft_version || '';
    SERVER_INFO.rconPort = data.rcon_port || '';
    SERVER_INFO.bridgePort = data.bridge_port || '';
    SERVER_INFO.nativeSeedFinderReady = !!data.native_seed_finder_ready;
    setVersion((SERVER_INFO.minecraftVersion ? 'MC ' + SERVER_INFO.minecraftVersion + ' · ' : '') + (SERVER_INFO.rconPort ? 'RCON:' + SERVER_INFO.rconPort : 'RCON'));
    setPaperStatus(data.paper);
    if (TOKEN && STATUS_STATE.state !== 'on' && !(await restoreStoredAuth())) openLoginModal();
  } catch (error) {
    setPaperStatus({ state: 'offline', elapsed_seconds: null });
  } finally {
    endRefresh('paper');
  }
}

document.addEventListener('click', function (event) {
  if (!paperReady() && event.target.closest('[data-paper-controls]')) {
    event.preventDefault();
    event.stopImmediatePropagation();
    toastClient('status.paper.dataWaiting');
  }
}, true);

function setVersion(value) {
  VERSION_STATE = value || '';
  renderVersion();
}

function renderVersion() {
  document.getElementById('ver-tag').textContent = renderPresentation(VERSION_STATE) || '--';
}

function renderWorkspace(focus) {
  var links = Array.from(document.querySelectorAll('.control-nav-link'));
  var link = links.find(function (item) { return item.hash === window.location.hash; }) || links[0];
  if (!link) return;
  var target = link.hash.slice(1);
  document.body.setAttribute('data-workspace', target);
  document.getElementById('workspace-select').value = target;
  links.forEach(function (item) {
    item.classList.toggle('is-active', item === link);
    if (item === link) item.setAttribute('aria-current', 'page');
    else item.removeAttribute('aria-current');
  });
  document.querySelectorAll('.workspace-section').forEach(function (section) {
    var visible = section.id === target || (target === 'overview' && ['status-section', 'runtime-section'].includes(section.id));
    section.classList.toggle('hidden', !visible);
  });
  var heading = document.getElementById('workspace-title');
  heading.textContent = target === 'overview' ? t('design.overview') : link.textContent.trim();
  var descriptionKey = 'design.hint.' + target;
  document.getElementById('workspace-description').textContent = t(descriptionKey);
  if (focus) {
    heading.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: 'instant' });
  }
}

function initNavigation() {
  document.querySelector('.skip-link').addEventListener('click', function (event) {
    event.preventDefault();
    document.getElementById('workspace-title').focus();
  });
  document.getElementById('workspace-select').addEventListener('change', function (event) {
    window.location.hash = event.target.value;
  });
  document.querySelectorAll('.control-nav-link, .card-link').forEach(function (link) {
    link.addEventListener('click', function (event) {
      event.preventDefault();
      if (link.hash !== window.location.hash) window.history.pushState(null, '', link.hash);
      renderWorkspace(true);
    });
  });
  window.addEventListener('hashchange', function () { renderWorkspace(true); });
  renderWorkspace(false);
}

async function init() {
  initNavigation();
  renderPaperStatus();
  loadConnectionInfo();
  await refreshPaperStatus();
  if (PAPER_STATUS.state === 'disabled') return;
  if (!PAPER_STATUS_TIMER) {
    PAPER_STATUS_TIMER = setInterval(function () { if (!document.hidden) refreshPaperStatus(); }, 5000);
  }
  setSeedState('', defaultSeedHint());
  if (PAPER_STATUS.state !== 'offline') log('RCON 已启用，管理面板准备就绪', 'info');
  if (!(await restoreStoredAuth())) openLoginModal();
}

async function pluginRequest(payload) {
  var r = await fetch(BASE + '/api/plugins', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildAuthPayload(payload))
  });
  var d = await r.json();
  if (!d.success && isAuthError(d.error)) handleAuthFailure(d.error);
  return d;
}

function updatePluginUploadSelection(showSelection) {
  var input = document.getElementById('plugin-upload-input');
  var button = document.getElementById('plugin-upload-btn');
  var status = document.getElementById('plugin-upload-status');
  var file = input && input.files && input.files[0];
  if (button) button.disabled = PLUGIN_UPLOAD_IN_FLIGHT || !TOKEN || !file;
  if (showSelection !== false && status && !PLUGIN_UPLOAD_IN_FLIGHT && !PLUGIN_TRANSITION_IN_FLIGHT && file) status.textContent = file.name;
}

function setPluginUploadStatus(value, cls) {
  var status = document.getElementById('plugin-upload-status');
  if (!status) return;
  status.className = 'plugin-upload-status' + (cls ? ' ' + cls : '');
  status.textContent = String(value || '');
}

function uploadPlugin() {
  var input = document.getElementById('plugin-upload-input');
  var file = input && input.files && input.files[0];
  if (!TOKEN) {
    handleAuthFailure('token required');
    return;
  }
  if (!file) {
    setPluginUploadStatus(t('status.plugin.uploadNoFile'), 'error');
    return;
  }
  if (PLUGIN_UPLOAD_IN_FLIGHT) return;

  var progress = document.getElementById('plugin-upload-progress');
  var button = document.getElementById('plugin-upload-btn');
  var xhr = new XMLHttpRequest();
  PLUGIN_UPLOAD_IN_FLIGHT = true;
  if (button) button.disabled = true;
  if (progress) {
    progress.value = 0;
    progress.classList.remove('hidden');
  }
  setPluginUploadStatus(t('status.plugin.uploading'), '');
  xhr.open('POST', BASE + '/api/plugins/upload', true);
  xhr.timeout = 35000;
  xhr.setRequestHeader('Authorization', 'Bearer ' + TOKEN);
  xhr.setRequestHeader('X-Plugin-Filename', file.name);
  xhr.setRequestHeader('Content-Type', 'application/java-archive');
  xhr.upload.onprogress = function (event) {
    if (!progress || !event.lengthComputable) return;
    progress.value = Math.round(event.loaded / event.total * 100);
  };
  xhr.onload = function () {
    var data = null;
    try { data = JSON.parse(xhr.responseText || '{}'); } catch (e) { data = {}; }
    if (xhr.status === 401 || xhr.status === 403 || isAuthError(data.error)) {
      handleAuthFailure(data.error || 'token expired');
      return;
    }
    if (xhr.status >= 200 && xhr.status < 300 && data.success) {
      setPluginUploadStatus(t('status.plugin.uploadSuccess', { filename: file.name }), 'success');
      input.value = '';
      refreshPlugins();
      return;
    }
    setPluginUploadStatus(data.error || t('status.plugin.uploadFailed'), 'error');
  };
  xhr.onerror = function () { setPluginUploadStatus(t('status.plugin.uploadConnectionFailed'), 'error'); };
  xhr.ontimeout = function () { setPluginUploadStatus(t('status.plugin.uploadTimeout'), 'error'); };
  xhr.onloadend = function () {
    PLUGIN_UPLOAD_IN_FLIGHT = false;
    if (progress) {
      if (xhr.status >= 200 && xhr.status < 300) progress.value = 100;
      setTimeout(function () { progress.classList.add('hidden'); }, 800);
    }
    updatePluginUploadSelection(false);
  };
  xhr.send(file);
}

function formatPluginBytes(value) {
  var bytes = Math.max(0, Number(value || 0));
  if (bytes < 1024) return formatNumber(bytes) + ' B';
  if (bytes < 1024 * 1024) return formatNumber(bytes / 1024, { maximumFractionDigits: 1 }) + ' KB';
  return formatNumber(bytes / (1024 * 1024), { maximumFractionDigits: 1 }) + ' MB';
}

function formatPluginModified(value) {
  var date = new Date(value);
  return isNaN(date.getTime()) ? String(value || '--') : new Intl.DateTimeFormat(EaglerXI18n.getLocale(), { dateStyle: 'short', timeStyle: 'short' }).format(date);
}

function pluginTransitionError(data) {
  var code = String(data && data.code || '');
  if (code === 'missing_resource') return t('status.plugin.missing');
  if (code === 'state_conflict') return t('status.plugin.stale');
  if (code === 'destination_conflict') return t('status.plugin.destinationConflict');
  return String(data && data.error || t('status.plugin.transitionFailed'));
}

async function transitionPlugin(button) {
  if (!button || PLUGIN_TRANSITION_IN_FLIGHT || !TOKEN) return;
  var filename = button.getAttribute('data-plugin-filename') || '';
  var action = button.getAttribute('data-plugin-action') || '';
  if (!filename || (action !== 'enable' && action !== 'disable')) return;

  PLUGIN_TRANSITION_IN_FLIGHT = true;
  button.disabled = true;
  setPluginUploadStatus(t('status.plugin.transitioning'), '');
  try {
    var d = await pluginRequest({
      action: action,
      filename: filename,
      expected_enabled: action === 'disable'
    });
    if (d.success) {
      setPluginUploadStatus(t('status.plugin.transitionSuccess', { filename: filename }), 'success');
      await refreshPlugins();
      return;
    }
    if (!isAuthError(d.error)) {
      setPluginUploadStatus(pluginTransitionError(d), 'error');
      await refreshPlugins();
    }
  } catch (e) {
    setPluginUploadStatus(t('status.plugin.transitionFailed'), 'error');
    await refreshPlugins();
  } finally {
    PLUGIN_TRANSITION_IN_FLIGHT = false;
    renderPluginInventory();
  }
}

async function deletePlugin(button) {
  if (!button || PLUGIN_TRANSITION_IN_FLIGHT || !TOKEN) return;
  var filename = button.getAttribute('data-plugin-filename') || '';
  var expectedEnabled = button.getAttribute('data-plugin-enabled') === 'true';
  if (!filename) return;

  PLUGIN_TRANSITION_IN_FLIGHT = true;
  try {
    var confirmed = await showActionDialog({
      kicker: presentation('status.plugin.deleteKicker'),
      title: presentation('status.plugin.deleteTitle', { filename: filename }),
      description: presentation('status.plugin.deleteDescription', { filename: filename }),
      confirmText: presentation('status.plugin.deleteConfirm'),
      danger: true,
      fields: [],
      previewText: function () { return t('status.plugin.deletePreview', { filename: filename }); }
    });
    if (!confirmed) return;
    button.disabled = true;
    setPluginUploadStatus(t('status.plugin.transitioning'), '');
    var d = await pluginRequest({
      action: 'delete',
      filename: filename,
      expected_enabled: expectedEnabled
    });
    if (d.success) {
      setPluginUploadStatus(t('status.plugin.deleteSuccess', { filename: filename }), 'success');
      await refreshPlugins();
      return;
    }
    if (!isAuthError(d.error)) {
      setPluginUploadStatus(pluginTransitionError(d), 'error');
      await refreshPlugins();
    }
  } catch (e) {
    setPluginUploadStatus(t('status.plugin.transitionFailed'), 'error');
    await refreshPlugins();
  } finally {
    PLUGIN_TRANSITION_IN_FLIGHT = false;
    renderPluginInventory();
  }
}

function renderPluginInventory() {
  var title = document.getElementById('plugin-title');
  var note = document.getElementById('plugin-note');
  var version = document.getElementById('plugin-version');
  var list = document.getElementById('plugin-list');
  var banner = document.getElementById('plugin-restart-banner');
  var restartText = document.getElementById('plugin-restart-text');
  var restartButton = document.getElementById('plugin-restart-btn');
  var warningTitle = document.getElementById('plugin-upload-warning-title');
  var warningText = document.getElementById('plugin-upload-warning-text');
  var fileLabel = document.getElementById('plugin-upload-file-label');
  var uploadButton = document.getElementById('plugin-upload-btn');
  if (!title || !note || !version || !list || !banner || !restartText || !restartButton) return;
  title.textContent = t('status.plugin.title');
  note.textContent = t('status.plugin.note');
  if (warningTitle) warningTitle.textContent = t('status.plugin.warningTitle');
  if (warningText) warningText.textContent = t('status.plugin.warningText');
  if (fileLabel) fileLabel.firstChild.textContent = t('status.plugin.chooseFile');
  if (uploadButton) uploadButton.textContent = t('status.plugin.upload');
  updatePluginUploadSelection(false);
  if (!PLUGIN_INVENTORY) {
    version.textContent = 'MC --';
    banner.classList.add('hidden');
    list.innerHTML = '<div class="empty-state">' + escapeHtml(t('status.plugin.login')) + '</div>';
    return;
  }
  var activeVersion = String(PLUGIN_INVENTORY.minecraft_version || SERVER_INFO.minecraftVersion || '--');
  version.textContent = t('status.plugin.version', { version: activeVersion });
  restartText.textContent = t('status.plugin.pending', { version: activeVersion });
  restartButton.textContent = t('status.plugin.restart');
  banner.classList.toggle('hidden', !PLUGIN_INVENTORY.pending_restart);
  var entries = PLUGIN_INVENTORY.entries || [];
  if (!entries.length) {
    list.innerHTML = '<div class="empty-state">' + escapeHtml(t('status.plugin.empty')) + '</div>';
    return;
  }
  var rows = ['<div class="plugin-table">', '<div class="plugin-row plugin-header"><span>' + escapeHtml(t('status.plugin.package')) + '</span><span>' + escapeHtml(t('status.plugin.state')) + '</span><span>' + escapeHtml(t('status.plugin.size')) + '</span><span>' + escapeHtml(t('status.plugin.modified')) + '</span><span>' + escapeHtml(t('status.plugin.action')) + '</span></div>'];
  entries.forEach(function (entry) {
    var enabled = !!entry.enabled;
    var action = enabled ? 'disable' : 'enable';
    var actionLabel = enabled ? t('status.plugin.disableAction') : t('status.plugin.enableAction');
    rows.push('<div class="plugin-row"><span class="plugin-name" title="' + escapeHtml(entry.filename || '') + '">' + escapeHtml(entry.filename || '') + '</span><span class="plugin-state' + (enabled ? '' : ' disabled') + '">' + escapeHtml(enabled ? t('status.plugin.enabled') : t('status.plugin.disabled')) + '</span><span class="plugin-meta">' + escapeHtml(formatPluginBytes(entry.size)) + '</span><span class="plugin-meta">' + escapeHtml(formatPluginModified(entry.modified_at)) + '</span><span class="plugin-actions"><button class="pill-btn plugin-action" type="button" data-plugin-action="' + action + '" data-plugin-filename="' + escapeHtml(entry.filename || '') + '">' + escapeHtml(actionLabel) + '</button><button class="pill-btn plugin-delete-action danger-btn" type="button" data-plugin-filename="' + escapeHtml(entry.filename || '') + '" data-plugin-enabled="' + String(enabled) + '">' + escapeHtml(t('status.plugin.deleteAction')) + '</button></span></div>');
  });
  rows.push('</div>');
  list.innerHTML = rows.join('');
  list.querySelectorAll('.plugin-action').forEach(function (button) {
    button.addEventListener('click', function () { transitionPlugin(button); });
  });
  list.querySelectorAll('.plugin-delete-action').forEach(function (button) {
    button.addEventListener('click', function () { deletePlugin(button); });
  });
}

async function refreshPlugins() {
  if (!TOKEN || !beginRefresh('plugins')) return;
  setCardLoading('card-plugins', true);
  try {
    var d = await pluginRequest({ action: 'list' });
    if (d.success) {
      PLUGIN_INVENTORY = d;
      renderPluginInventory();
    }
  } catch (e) {
    logClient('console.requestFailed', { error: e.message }, 'warn');
  } finally {
    setCardLoading('card-plugins', false);
    endRefresh('plugins');
  }
}

async function configRequest(payload) {
  var r = await fetch(BASE + '/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildAuthPayload(payload))
  });
  var d = await r.json();
  if (!d.success && isAuthError(d.error)) handleAuthFailure(d.error);
  return d;
}

async function systemRequest(payload) {
  var r = await fetch(BASE + '/api/system', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildAuthPayload(payload))
  });
  var d = await r.json();
  if (!d.success && isAuthError(d.error)) handleAuthFailure(d.error);
  return d;
}

async function seedRequest(payload) {
  var r = await fetch(BASE + '/api/seed', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildAuthPayload(payload))
  });
  var d = await r.json();
  if (!d.success && isAuthError(d.error)) handleAuthFailure(d.error);
  return d;
}

async function structuresRequest(payload) {
  var r = await fetch(BASE + '/api/structures', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildAuthPayload(payload))
  });
  var d = await r.json();
  if (!d.success && isAuthError(d.error)) handleAuthFailure(d.error);
  return d;
}

async function playerLocationRequest(payload) {
  var r = await fetch(BASE + '/api/player-location', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildAuthPayload(payload))
  });
  var d = await r.json();
  if (!d.success && isAuthError(d.error)) handleAuthFailure(d.error);
  return d;
}

async function worldStateRequest(payload) {
  var r = await fetch(BASE + '/api/world-state', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildAuthPayload(payload || {}))
  });
  var d = await r.json();
  if (!d.success && isAuthError(d.error)) handleAuthFailure(d.error);
  return d;
}

async function runtimeStateRequest(payload) {
  var r = await fetch(BASE + '/api/runtime-state', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildAuthPayload(payload || {}))
  });
  var d = await r.json();
  if (!d.success && isAuthError(d.error)) handleAuthFailure(d.error);
  return d;
}

var _modalCb = null;
var ACTION_DIALOG = null;
function getStoredToken() {
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_TOKEN_EXP_KEY);
    var token = sessionStorage.getItem(AUTH_TOKEN_KEY) || '';
    var exp = parseInt(sessionStorage.getItem(AUTH_TOKEN_EXP_KEY) || '0', 10);
    if (exp && Date.now() / 1000 >= exp) {
      clearStoredToken();
      return '';
    }
    return token;
  } catch (e) {
    return '';
  }
}

function saveStoredToken(token, expiresAt) {
  try {
    sessionStorage.setItem(AUTH_TOKEN_KEY, token || '');
    if (expiresAt) sessionStorage.setItem(AUTH_TOKEN_EXP_KEY, String(expiresAt));
  } catch (e) { }
}

function clearStoredToken() {
  try {
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
    sessionStorage.removeItem(AUTH_TOKEN_EXP_KEY);
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_TOKEN_EXP_KEY);
  } catch (e) { }
}

function clearAuthState() {
  TOKEN = '';
}

function clearWorldControlState() {
  document.getElementById('control-world-time').textContent = '--:--';
  document.querySelectorAll('[data-weather], [data-time]').forEach(function (button) { button.removeAttribute('aria-pressed'); });
  document.querySelectorAll('[data-world-setting]').forEach(function (select) { select.value = ''; });
}

function resetAuthUi() {
  setStatus('auth', '请输入密码');
  PLUGIN_INVENTORY = null;
  renderPluginInventory();
  ONLINE_PLAYERS = [];
  WORLD_INFO_CACHE = null;
  TPS_VALUES = [];
  clearWorldControlState();
  document.getElementById('player-count').textContent = '0';
  var heroPlayerCount = document.getElementById('hero-player-count');
  if (heroPlayerCount) heroPlayerCount.textContent = '0';
  document.getElementById('players').innerHTML = '<div class="empty-state">请先登录后查看玩家列表</div>';
  document.getElementById('tps-bars').innerHTML = '<div class="empty-state">请先登录后查看 TPS</div>';
  var heroTps = document.getElementById('hero-tps');
  if (heroTps) heroTps.textContent = '--';
  setWorldInfoPlaceholder('请先登录后查看世界基础信息');
  setSeedState('', '请先登录后读取世界种子');
  setStructureSource('');
}

function defaultSeedHint() {
  return presentation(SERVER_INFO.nativeSeedFinderReady ? 'seed.defaultHintReady' : 'seed.defaultHintUnavailable');
}

function getSeedMapVersion() {
  var version = String(SERVER_INFO.minecraftVersion || '').trim();
  if (/^1\.12/.test(version)) return '1.12';
  if (/^1\.8/.test(version)) return '1.8';
  return version || '1.12';
}

function buildSeedMapUrl() {
  if (!WORLD_SEED) return '';
  return 'https://mcseedmap.net/' + encodeURIComponent(getSeedMapVersion()) + '/map?seed=' + encodeURIComponent(WORLD_SEED);
}

function updateSeedMapLink() {
  var versionEl = document.getElementById('seedmap-version-tag');
  var linkEl = document.getElementById('seedmap-link');
  var openBtn = document.getElementById('seed-open-btn');
  var overlayOpenBtn = document.getElementById('seed-overlay-open-btn');
  var url = buildSeedMapUrl();
  if (versionEl) versionEl.textContent = 'MC ' + getSeedMapVersion();
  if (linkEl) {
    if (url) {
      linkEl.href = url;
      linkEl.textContent = url;
      linkEl.classList.remove('disabled');
    } else {
      linkEl.href = 'javascript:void(0)';
      linkEl.textContent = localize('读取种子后可在新标签页打开 mcseedmap.net');
      linkEl.classList.add('disabled');
    }
  }
  if (openBtn) openBtn.disabled = !WORLD_SEED;
  if (overlayOpenBtn) overlayOpenBtn.disabled = !WORLD_SEED;
}

function openSeedMapInNewTab() {
  if (!WORLD_SEED) {
    toast('暂未读取到世界种子');
    return;
  }
  var url = buildSeedMapUrl();
  if (!url) return;
  var win = window.open(url, '_blank', 'noopener,noreferrer');
  if (!win) toast('浏览器拦截了新标签页，请允许弹窗后重试');
}

function openStructureOverlay() {
  var overlay = document.getElementById('structure-overlay');
  if (overlay) overlay.classList.remove('hidden');
}

function closeStructureOverlay() {
  var overlay = document.getElementById('structure-overlay');
  if (overlay) overlay.classList.add('hidden');
}

function structureOverlayBackdrop(event) {
  if (event.target && event.target.id === 'structure-overlay') closeStructureOverlay();
}

function openLatestStructureResults() {
  if (!LAST_STRUCTURE_RESULT) {
    toast('还没有最近一次结构搜索结果');
    return;
  }
  openStructureOverlay();
}

async function openStructureSearchDialog(preset) {
  if (!TOKEN) return;
  if (!WORLD_SEED) {
    toast('暂未读取到世界种子');
    return;
  }
  if (!SERVER_INFO.nativeSeedFinderReady) {
    toast('原生结构查找组件还没装进镜像');
    return;
  }
  var current = getStructureQuery(preset || STRUCTURE_QUERY);
  var playerPlaceholder = ONLINE_PLAYERS[0] || 'Steve';
  var values = await showActionDialog({
    kicker: '原生结构查找',
    title: '搜索附近',
    description: '支持两种方式：1）直接输入中心坐标；2）填写在线玩家名，按该玩家当前位置附近搜索。若填写了玩家名，会优先使用玩家实时坐标。',
    confirmText: '开始搜索',
    fields: [
      textField('player', '在线玩家（可选）', playerPlaceholder, { hint: '填了就按该玩家当前位置搜索；留空则使用下面的 X/Z 坐标', list: ONLINE_PLAYERS.slice() }),
      textField('x', '中心 X', '0', { type: 'number', value: String(current.x || 0), hint: '留空时默认为当前搜索中心；若填写了玩家名，这个值会被忽略' }),
      textField('z', '中心 Z', '0', { type: 'number', value: String(current.z || 0), hint: '留空时默认为当前搜索中心；若填写了玩家名，这个值会被忽略' }),
      textField('radius', '搜索半径', '5000', { type: 'number', value: String(current.radius || 5000), required: true, hint: '建议 2000 - 10000，范围 256 - 50000' })
    ],
    previewText: function (input) {
      var query = getStructureQuery(input || current);
      var player = input && input.player ? String(input.player).trim() : '';
      if (player) return t('structure.playerPreview', { player: player, radius: formatNumber(query.radius) });
      return t('structure.coordinatesPreview', { x: formatNumber(query.x), z: formatNumber(query.z), radius: formatNumber(query.radius) });
    }
  });
  if (!values) return;
  var playerName = String(values.player || '').trim();
  if (playerName) {
    setStructureSource(presentation('structure.sourcePlayer', { player: playerName }));
    setStructureStatus('正在读取玩家位置...', presentation('structure.playerSummary', { player: playerName }));
    renderStructurePlaceholder(presentation('structure.readingPlayer', { player: playerName }));
    try {
      var playerLocation = await fetchDynmapPlayerLocation(playerName);
      var playerSourceText = presentation('structure.sourcePlayerLocation', { player: playerLocation.name, world: playerLocation.world, x: formatNumber(playerLocation.x), z: formatNumber(playerLocation.z), source: playerLocation.source === 'playerdata' ? presentation('structure.sourcePlayerdata') : 'Dynmap' });
      setStructureSource(playerSourceText);
      await refreshStructureFinder({
        x: playerLocation.x,
        z: playerLocation.z,
        radius: values.radius,
        limitPerType: STRUCTURE_QUERY.limitPerType,
        sourceText: playerSourceText
      });
      setStructureStatus('原生结构查找完成', presentation('structure.playerRangeSummary', { player: playerLocation.name, radius: formatNumber(getStructureQuery({ radius: values.radius }).radius) }));
      return;
    } catch (e) {
      setStructureStatus(presentation('status.playerLookupFailed'), '', e.message || 'unknown');
      renderStructurePlaceholder(presentation('status.playerLookupFailed'), e.message || 'unknown');
      if (e.message) toastRaw(e.message); else toastClient('toast.playerLocationFailed');
      return;
    }
  }
  var coordinateQuery = getStructureQuery(values);
  await refreshStructureFinder({
    x: coordinateQuery.x,
    z: coordinateQuery.z,
    radius: coordinateQuery.radius,
    limitPerType: coordinateQuery.limitPerType,
    sourceText: presentation('structure.sourceCoordinates', { x: formatNumber(coordinateQuery.x), z: formatNumber(coordinateQuery.z) })
  });
}

async function fetchJson(url) {
  var response = await fetch(url, { credentials: 'same-origin' });
  if (!response.ok) throw new Error('请求失败: ' + response.status);
  return response.json();
}

async function fetchDynmapPlayerLocation(playerName) {
  var target = String(playerName || '').trim();
  if (!target) throw new Error('玩家名不能为空');
  var d = await playerLocationRequest({ player: target });
  if (!d.success) throw new Error(d.error || ('没找到玩家“' + target + '”的位置'));
  return {
    name: d.name || target,
    world: d.world || 'world',
    x: Math.round(Number(d.x || 0)),
    y: Math.round(Number(d.y || 0)),
    z: Math.round(Number(d.z || 0)),
    source: d.source || 'unknown'
  };
}

function setSeedState(seed, hint) {
  WORLD_SEED = seed || '';
  SEED_STATE = { seed: WORLD_SEED, hint: hint || defaultSeedHint(), rawHint: arguments.length > 2 ? arguments[2] : null };
  renderSeedState();
  if (!WORLD_SEED) {
    LAST_STRUCTURE_RESULT = null;
    setStructureStatus('等待读取世界种子', '');
    setStructureSource('');
    setSpawnCard(null);
    renderStructurePlaceholder('读取种子后可直接在这里查看原生结构坐标');
  }
}

function renderSeedState() {
  var valueEl = document.getElementById('seed-value');
  var hintEl = document.getElementById('seed-hint');
  var copyBtn = document.getElementById('seed-copy-btn');
  var openBtn = document.getElementById('seed-open-btn');
  var searchBtn = document.getElementById('seed-search-btn');
  var lastResultBtn = document.getElementById('seed-last-result-btn');
  if (valueEl) valueEl.textContent = SEED_STATE.seed || localize('未读取');
  if (hintEl) {
    hintEl.textContent = renderPresentation(SEED_STATE.hint);
    if (SEED_STATE.rawHint != null) {
      hintEl.appendChild(document.createTextNode(' '));
      var rawHint = document.createElement('span');
      rawHint.className = 'raw-output';
      rawHint.textContent = String(SEED_STATE.rawHint);
      hintEl.appendChild(rawHint);
    }
  }
  if (copyBtn) copyBtn.disabled = !SEED_STATE.seed;
  if (openBtn) openBtn.disabled = !SEED_STATE.seed;
  if (searchBtn) searchBtn.disabled = !SEED_STATE.seed || !SERVER_INFO.nativeSeedFinderReady;
  updateSeedMapLink();
  if (lastResultBtn) lastResultBtn.disabled = !LAST_STRUCTURE_RESULT;
}

function setWorldInfoPlaceholder(text, rawPayload) {
  var el = document.getElementById('world-info');
  if (!el) return;
  el.textContent = '';
  var message = document.createElement('div');
  message.className = 'empty-state';
  message.textContent = localize(text || '暂无世界信息');
  if (rawPayload != null) {
    var raw = document.createElement('span');
    raw.className = 'raw-output';
    raw.textContent = String(rawPayload);
    message.appendChild(raw);
  }
  el.appendChild(message);
}

function getServerVersionDisplay() {
  var text = String(SERVER_INFO.serverVersionText || '');
  if (text) return text;
  return SERVER_INFO.minecraftVersion ? ('MC ' + SERVER_INFO.minecraftVersion) : '--';
}

function hasWorldInfoPayload(info) {
  return !!(info && typeof info === 'object' && (
    typeof info.servertime !== 'undefined' ||
    typeof info.hasStorm !== 'undefined' ||
    typeof info.isThundering !== 'undefined'
  ));
}

function formatMinecraftClock(rawTicks) {
  var ticks = ((Number(rawTicks || 0) % 24000) + 24000) % 24000;
  var clock = (ticks + 6000) % 24000;
  var hours = Math.floor(clock / 1000);
  var minutes = Math.floor((clock % 1000) * 60 / 1000);
  return String(hours).padStart(2, '0') + ':' + String(minutes).padStart(2, '0');
}

function describeMinecraftPhase(rawTicks) {
  var ticks = ((Number(rawTicks || 0) % 24000) + 24000) % 24000;
  if (ticks < 1000) return '日出';
  if (ticks < 6000) return '白天';
  if (ticks < 12000) return '正午后';
  if (ticks < 13000) return '黄昏';
  if (ticks < 18000) return '夜晚';
  if (ticks < 23000) return '深夜';
  return '黎明前';
}

function renderWorldInfo(info) {
  if (!paperReady()) { renderPaperStatus(); return; }
  if (hasWorldInfoPayload(info)) WORLD_INFO_CACHE = info;
  var el = document.getElementById('world-info');
  if (!el) return;
  var world = WORLD_INFO_CACHE;
  if (!world) {
    setWorldInfoPlaceholder('正在读取世界状态...');
    return;
  }
  var weather = world && world.isThundering ? '雷暴' : (world && world.hasStorm ? '下雨' : '晴朗');
  document.querySelectorAll('[data-weather]').forEach(function (button) {
    var activeWeather = world.isThundering ? 'thunder' : world.hasStorm ? 'rain' : 'clear';
    button.setAttribute('aria-pressed', String(button.getAttribute('data-weather') === activeWeather));
  });
  document.querySelectorAll('[data-world-setting]').forEach(function (select) {
    var value = world[select.getAttribute('data-world-setting')];
    select.value = value == null ? '' : String(value);
  });
  var ticks = Number(world && typeof world.servertime !== 'undefined' ? world.servertime : 0);
  document.getElementById('control-world-time').textContent = formatMinecraftClock(ticks);
  document.querySelectorAll('[data-time]').forEach(function (button) {
    button.setAttribute('aria-pressed', String(ticks % 24000 === Number(button.getAttribute('data-time'))));
  });
  var cards = [
    { label: localize('天气'), value: localize(weather), meta: localize('雷暴') + ' · ' + localize(world.isThundering ? '进行中' : '无') },
    { label: localize('时间'), value: formatMinecraftClock(ticks), meta: localize(describeMinecraftPhase(ticks)) + ' · ' + formatNumber(ticks) + ' ticks' }
  ];
  el.innerHTML = '<div class="world-info-grid">' + cards.map(function (item) {
    return '<div class="world-info-item"><strong>' + escapeHtml(item.label) + '</strong><span>' + escapeHtml(item.value) + '</span><small>' + escapeHtml(item.meta) + '</small></div>';
  }).join('') + '</div>';
}

function rerenderWorldInfo() {
  if (!WORLD_INFO_CACHE) return;
  renderWorldInfo(WORLD_INFO_CACHE);
}

function renderPlayers() {
  if (!paperReady()) { renderPaperStatus(); return; }
  var el = document.getElementById('players');
  if (!el) return;
  var count = formatNumber(ONLINE_PLAYERS.length);
  document.getElementById('player-count').textContent = count;
  var heroPlayerCount = document.getElementById('hero-player-count');
  if (heroPlayerCount) heroPlayerCount.textContent = count;
  el.innerHTML = ONLINE_PLAYERS.length ? ONLINE_PLAYERS.map(function (name) {
    return '<div class="player-item">' + playerAvatar(name) + '<span class="player-name">' + escapeHtml(name) + '</span></div>';
  }).join('') : '<div class="empty-state">' + escapeHtml(localize('暂无在线玩家')) + '</div>';
}

function renderTPS() {
  if (!paperReady()) { renderPaperStatus(); return; }
  var el = document.getElementById('tps-bars');
  if (!el || !TPS_VALUES.length) return;
  var labels = [t('design.tps1m'), t('design.tps5m'), t('design.tps15m')];
  var heroTps = document.getElementById('hero-tps');
  if (heroTps) heroTps.textContent = formatNumber(TPS_VALUES[0], { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (heroTps) heroTps.className = 'tps-val ' + (TPS_VALUES[0] >= 19 ? 'good' : TPS_VALUES[0] >= 15 ? 'ok' : 'bad');
  el.innerHTML = TPS_VALUES.slice(1).map(function (value, index) {
    var cls = value >= 19 ? 'good' : value >= 15 ? 'ok' : 'bad';
    return '<div class="tps-row"><span class="tps-label">' + escapeHtml(labels[index + 1]) + '</span><span class="tps-val ' + cls + '">' + formatNumber(value, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '</span></div>';
  }).join('');
}

function rerenderLocalizedState() {
  if (!window.EaglerXI18n) return;
  renderWorkspace(false);
  var dialogSnapshot = captureActionDialogSnapshot();
  renderStatus();
  renderVersion();
  if (WORLD_INFO_CACHE) renderWorldInfo(WORLD_INFO_CACHE);
  if (ONLINE_PLAYERS || TOKEN) renderPlayers();
  if (TPS_VALUES.length) renderTPS();
  renderPluginInventory();
  renderConnectionInfo();
  renderSeedState();
  renderStructureStatus();
  renderStructureSource();
  updateSeedMapLink();
  if (LAST_STRUCTURE_RESULT) {
    var overlay = document.getElementById('structure-overlay');
    var wasOpen = overlay && !overlay.classList.contains('hidden');
    renderStructureResults(LAST_STRUCTURE_RESULT);
    if (!wasOpen && overlay) overlay.classList.add('hidden');
  } else {
    setSpawnCard(null);
    renderStructurePlaceholderState();
  }
  if (ACTION_DIALOG) renderActionDialog(dialogSnapshot);
  renderToast();
  renderConsoleHistory();
  renderPaperStatus();
}

function setToggleElementChecked(el, checked) {
  if (!el) return;
  var cb = el.querySelector('input[type=checkbox]');
  if (cb) cb.checked = !!checked;
}

function setTogglePending(el, pending) {
  if (!el) return;
  if (pending) {
    el.classList.add('is-pending');
    el.setAttribute('aria-busy', 'true');
  } else {
    el.classList.remove('is-pending');
    el.removeAttribute('aria-busy');
  }
}

function queueWorldInfoRefresh(delay, forceRefresh) {
  if (WORLD_INFO_REFRESH_HANDLE) clearTimeout(WORLD_INFO_REFRESH_HANDLE);
  WORLD_INFO_REFRESH_FORCE = WORLD_INFO_REFRESH_FORCE || !!forceRefresh;
  WORLD_INFO_REFRESH_HANDLE = setTimeout(function () {
    var force = WORLD_INFO_REFRESH_FORCE;
    WORLD_INFO_REFRESH_HANDLE = null;
    WORLD_INFO_REFRESH_FORCE = false;
    refreshWorldInfo(force);
  }, Math.max(0, delay || 0));
}

function queueRuntimeRefresh(delay) {
  if (RUNTIME_REFRESH_HANDLE) clearTimeout(RUNTIME_REFRESH_HANDLE);
  RUNTIME_REFRESH_HANDLE = setTimeout(function () {
    RUNTIME_REFRESH_HANDLE = null;
    refreshRuntimeToggles();
  }, Math.max(0, delay || 0));
}

function classifyCommandRefresh(cmd) {
  var text = String(cmd || '').trim().toLowerCase();
  return {
    world: /^(time\b|weather\b|difficulty\b|defaultgamemode\b)/.test(text),
    runtime: /^(gamerule\b|save-on\b|save-off\b|whitelist\b)/.test(text),
    config: /^(reload\b|restart\b|stop\b)/.test(text)
  };
}

function pickRuntimeToggleValue(data, kind, name) {
  if (!data || !data.success) return null;
  if (kind === 'gamerule') {
    return data.gamerules && data.gamerules[name] != null ? !!data.gamerules[name] : null;
  }
  if (kind === 'save') return !!data.save_enabled;
  if (kind === 'whitelist') return !!data.whitelist_enabled;
  return null;
}

async function waitForRuntimeToggleValue(kind, name, expected, el) {
  await new Promise(function (resolve) { setTimeout(resolve, 500); });
  try {
    var d = await runtimeStateRequest({});
    var actual = pickRuntimeToggleValue(d, kind, name);
    if (actual != null) {
      setToggleElementChecked(el, actual);
      if (actual === !!expected) return true;
    }
  } catch (e) {}
  return false;
}

async function refreshRuntimeToggles() {
  if (!TOKEN) return;
  if (!beginRefresh('runtime')) return;
  try {
    var d = await runtimeStateRequest({});
    if (!d.success) return;
    Object.keys(d.gamerules || {}).forEach(function (name) {
      if (d.gamerules[name] == null) return;
      setToggleElementChecked(document.querySelector('.toggle[data-rule="' + name + '"]'), d.gamerules[name]);
    });
    setToggleElementChecked(document.getElementById('autosave-toggle'), !!d.save_enabled);
    setToggleElementChecked(document.getElementById('whitelist-toggle'), !!d.whitelist_enabled);
    setToggleElementChecked(document.getElementById('pvp-unsupported-toggle'), !!d.pvp_enabled);
  } catch (e) {
    logClient('console.requestFailed', { error: e.message }, 'warn');
  } finally {
    setCardLoading('card-rules', false);
    setCardLoading('card-whitelist', false);
    endRefresh('runtime');
  }
}

async function refreshServerVersion() {
  if (!TOKEN || !paperReady()) return;
  try {
    var r = await fetch(BASE + '/api/rcon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildAuthPayload({ command: 'version' }))
    });
    var d = await r.json();
    if (d.success) {
      SERVER_INFO.serverVersionText = String(d.response || '');
      rerenderWorldInfo();
    } else if (isAuthError(d.error)) {
      handleAuthFailure(d.error);
    }
  } catch (e) { }
}

function setStructureStatus(text, summary, rawSummary) {
  STRUCTURE_STATUS_STATE = { text: text || '', summary: summary || '', rawSummary: rawSummary == null ? null : String(rawSummary) };
  renderStructureStatus();
}

function renderStructureStatus() {
  var status = document.getElementById('seedmap-status');
  var summaryEl = document.getElementById('seedmap-summary');
  if (status) status.textContent = renderPresentation(STRUCTURE_STATUS_STATE.text);
  if (summaryEl) {
    summaryEl.textContent = renderPresentation(STRUCTURE_STATUS_STATE.summary);
    if (STRUCTURE_STATUS_STATE.rawSummary != null) {
      summaryEl.appendChild(document.createTextNode(' '));
      var raw = document.createElement('span');
      raw.className = 'raw-output';
      raw.textContent = STRUCTURE_STATUS_STATE.rawSummary;
      summaryEl.appendChild(raw);
    }
  }
}

function setStructureSource(text) {
  LAST_STRUCTURE_CONTEXT = text || null;
  renderStructureSource();
}

function renderStructureSource() {
  var sourceEl = document.getElementById('seedmap-source');
  if (!sourceEl) return;
  if (LAST_STRUCTURE_CONTEXT) {
    sourceEl.textContent = renderPresentation(LAST_STRUCTURE_CONTEXT);
    sourceEl.classList.remove('hidden');
  } else {
    sourceEl.textContent = '';
    sourceEl.classList.add('hidden');
  }
}

function renderStructurePlaceholder(text, rawPayload) {
  STRUCTURE_PLACEHOLDER_STATE = { text: text || '', rawPayload: rawPayload == null ? null : String(rawPayload) };
  renderStructurePlaceholderState();
}

function renderStructurePlaceholderState() {
  var el = document.getElementById('seedmap-results');
  if (!el) return;
  el.textContent = '';
  var message = document.createElement('div');
  message.className = 'empty-state';
  message.textContent = renderPresentation(STRUCTURE_PLACEHOLDER_STATE.text || '暂无结果');
  if (STRUCTURE_PLACEHOLDER_STATE.rawPayload != null) {
    var raw = document.createElement('span');
    raw.className = 'raw-output';
    raw.textContent = STRUCTURE_PLACEHOLDER_STATE.rawPayload;
    message.appendChild(raw);
  }
  el.appendChild(message);
}

function structureLabelDescriptor(key, fallbackLabel) {
  var messageKey = STRUCTURE_LABEL_KEYS[String(key || '')];
  return messageKey ? presentation(messageKey) : String(fallbackLabel || t('structure.type.unknown'));
}

function getStructureLabel(key, fallbackLabel) {
  return renderPresentation(structureLabelDescriptor(key, fallbackLabel));
}

async function teleportPlayerToPoint(x, z, structureKey, fallbackLabel) {
  if (!TOKEN) return;
  var values = await showActionDialog({
    kicker: '世界传送',
    title: '传送玩家到此处',
    description: presentation('dialog.teleportPointDescription', { point: structureLabelDescriptor(structureKey, fallbackLabel) }),
    confirmText: '执行传送',
    fields: [
      playerField('玩家名', 'Steve')
    ],
    previewText: function (input) {
      var player = input && input.player ? input.player : '<玩家>';
      return 'spreadplayers ' + Number(x || 0) + ' ' + Number(z || 0) + ' 0 1 false ' + player;
    }
  });
  if (!values) return;
  send('spreadplayers ' + Number(x || 0) + ' ' + Number(z || 0) + ' 0 1 false ' + values.player);
}

function setSpawnCard(spawn, effectiveSeedKind) {
  var el = document.getElementById('seedmap-spawn');
  if (!el) return;
  if (!spawn) {
    el.innerHTML = '<div class="empty-state">' + escapeHtml(localize('搜索完成后会显示世界出生点')) + '</div>';
    return;
  }
  var note = effectiveSeedKind === 'string-hash'
    ? localize('当前世界种子是文本，Minecraft 会先做 Java String.hashCode 再参与结构计算。')
    : localize('以下出生点为 cubiomes 近似计算结果，通常足够用于面板内找结构。');
  el.innerHTML = '' +
    '<div class="seedmap-spawn-card">' +
      '<div class="seedmap-spawn-title"><strong>' + escapeHtml(localize('世界出生点')) + '</strong><span class="seedmap-spawn-meta">' + escapeHtml(localize('距离当前中心')) + ' ' + formatNumber(spawn.distance || 0) + ' ' + escapeHtml(localize('格')) + '</span></div>' +
      '<div class="seedmap-spawn-coords">X ' + escapeHtml(spawn.x) + ' / Z ' + escapeHtml(spawn.z) + '</div>' +
      '<div class="seedmap-inline-note"><div class="seedmap-inline-actions"><button class="pill-btn seedmap-mini-btn" type="button" onclick="fillStructureCenter(' + Number(spawn.x || 0) + ', ' + Number(spawn.z || 0) + ', true)">' + escapeHtml(localize('以出生点为中心重新搜索')) + '</button><button class="pill-btn seedmap-mini-btn" type="button" onclick="teleportPlayerToPoint(' + Number(spawn.x || 0) + ', ' + Number(spawn.z || 0) + ', \'spawn\', \'\')">' + escapeHtml(localize('传送玩家到此处')) + '</button></div></div>' +
      '<div class="seedmap-spawn-note">' + escapeHtml(note) + '</div>' +
    '</div>';
}

function getStructureQuery() {
  var raw = arguments.length ? arguments[0] : null;
  raw = raw || {};
  var x = parseInt(typeof raw.x !== 'undefined' ? raw.x : STRUCTURE_QUERY.x, 10);
  var z = parseInt(typeof raw.z !== 'undefined' ? raw.z : STRUCTURE_QUERY.z, 10);
  var radius = parseInt(typeof raw.radius !== 'undefined' ? raw.radius : STRUCTURE_QUERY.radius, 10);
  if (!isFinite(x)) x = 0;
  if (!isFinite(z)) z = 0;
  if (!isFinite(radius)) radius = 5000;
  radius = Math.max(256, Math.min(50000, radius));
  STRUCTURE_QUERY = { x: x, z: z, radius: radius, limitPerType: 8 };
  return STRUCTURE_QUERY;
}

async function fillStructureCenter(x, z, searchNow) {
  STRUCTURE_QUERY.x = parseInt(x, 10) || 0;
  STRUCTURE_QUERY.z = parseInt(z, 10) || 0;
  if (searchNow !== false) await openStructureSearchDialog(STRUCTURE_QUERY);
}

async function useSpawnAsCenter() {
  if (!LAST_STRUCTURE_RESULT || !LAST_STRUCTURE_RESULT.spawn) {
    toast('还没有出生点数据，请先查找结构');
    return;
  }
  await fillStructureCenter(LAST_STRUCTURE_RESULT.spawn.x, LAST_STRUCTURE_RESULT.spawn.z, true);
}

function renderStructureResults(data) {
  LAST_STRUCTURE_RESULT = data || null;
  setSpawnCard(data && data.spawn, data && data.effective_seed_kind);
  setStructureSource(LAST_STRUCTURE_CONTEXT || presentation('structure.sourceCoordinates', { x: formatNumber(data && data.center ? data.center.x : 0), z: formatNumber(data && data.center ? data.center.z : 0) }));
  setStructureStatus('原生结构查找完成', presentation('structure.resultSummary', { radius: formatNumber(data.radius), total: formatNumber(data.total_matches || 0) }));
  openStructureOverlay();

  var lastResultBtn = document.getElementById('seed-last-result-btn');
  if (lastResultBtn) lastResultBtn.disabled = !LAST_STRUCTURE_RESULT;

  var el = document.getElementById('seedmap-results');
  if (!el) return;
  if (!data || !data.groups || !data.groups.length) {
    el.innerHTML = '<div class="empty-state">' + escapeHtml(localize('当前范围内暂时没找到结构点位，你可以调整中心坐标或搜索半径后重试')) + '</div>';
    return;
  }

  el.innerHTML = data.groups.map(function (group) {
    var groupLabel = getStructureLabel(group.key, group.label);
    var structureKey = escapeHtml(JSON.stringify(String(group.key || '')));
    var fallbackLabel = escapeHtml(JSON.stringify(String(group.label || '')));
    var rows = (group.entries || []).map(function (entry) {
      return '' +
        '<div class="seedmap-row">' +
          '<div class="seedmap-coords">X ' + escapeHtml(entry.x) + ' / Z ' + escapeHtml(entry.z) + '</div>' +
          '<div class="seedmap-distance">' + escapeHtml(localize('距离')) + ' ' + formatNumber(entry.distance || 0) + ' ' + escapeHtml(localize('格')) + '</div>' +
          '<div class="seedmap-row-actions"><button class="pill-btn seedmap-mini-btn" type="button" onclick="fillStructureCenter(' + Number(entry.x || 0) + ', ' + Number(entry.z || 0) + ', true)">' + escapeHtml(localize('以此为中心')) + '</button><button class="pill-btn seedmap-mini-btn" type="button" onclick="teleportPlayerToPoint(' + Number(entry.x || 0) + ', ' + Number(entry.z || 0) + ', ' + structureKey + ', ' + fallbackLabel + ')">' + escapeHtml(localize('传送玩家到此处')) + '</button></div>' +
        '</div>';
    }).join('');
    return '' +
      '<div class="seedmap-group">' +
        '<div class="seedmap-group-head">' +
          '<strong>' + escapeHtml(groupLabel) + '</strong>' +
          '<span class="seedmap-group-meta">' + escapeHtml(localize('显示')) + ' ' + formatNumber((group.entries || []).length) + ' / ' + formatNumber(group.total_found || 0) + '</span>' +
        '</div>' +
        '<div class="seedmap-list">' + rows + '</div>' +
      '</div>';
  }).join('');
}

async function refreshStructureFinder(queryOverride) {
  if (!TOKEN) return;
  if (!WORLD_SEED) {
    toast('暂未读取到世界种子');
    return;
  }
  if (!SERVER_INFO.nativeSeedFinderReady) {
    toast('原生结构查找组件还没装进镜像');
    return;
  }
  var rawQuery = queryOverride || {};
  var query = getStructureQuery(rawQuery);
  var sourceText = rawQuery.sourceText
    ? rawQuery.sourceText
    : presentation('structure.sourceCoordinates', { x: formatNumber(query.x), z: formatNumber(query.z) });
  openStructureOverlay();
  setStructureSource(sourceText);
  setStructureStatus('正在计算结构坐标...', presentation('structure.coordinatesSummary', { x: formatNumber(query.x), z: formatNumber(query.z) }));
  renderStructurePlaceholder('正在调用后端原生结构算法，请稍候...');
  try {
    var d = await structuresRequest({
      x: query.x,
      z: query.z,
      radius: query.radius,
      limit_per_type: query.limitPerType
    });
    if (d.success) {
      renderStructureResults(d);
    } else if (!isAuthError(d.error)) {
      setStructureStatus('结构查找失败', '', d.error || 'unknown');
      renderStructurePlaceholder('结构查找失败', d.error || 'unknown');
      logClient('console.requestFailed', { error: d.error || 'unknown' }, 'warn');
    }
  } catch (e) {
    setStructureStatus('结构查找失败', '', e.message || 'network error');
    renderStructurePlaceholder('结构查找失败', e.message || 'network error');
    logClient('console.requestFailed', { error: e.message }, 'warn');
  }
}

function buildAuthPayload(payload) {
  var body = Object.assign({}, payload || {});
  if (TOKEN) body.token = TOKEN;
  return body;
}

function isAuthError(message) {
  return /password required|password mismatch|token/i.test(String(message || ''));
}

function sleep(ms) {
  return new Promise(function (resolve) { setTimeout(resolve, ms); });
}

function startAutoRefresh() {
  if (!PLAYERS_TIMER) PLAYERS_TIMER = setInterval(function () { if (shouldAutoPoll()) refreshPlayers(); }, REFRESH_INTERVALS.players);
  if (!TPS_TIMER) TPS_TIMER = setInterval(function () { if (shouldAutoPoll()) refreshTPS(); }, REFRESH_INTERVALS.tps);
  if (!WORLD_INFO_TIMER) WORLD_INFO_TIMER = setInterval(function () { if (shouldAutoPoll()) refreshWorldInfo(false); }, REFRESH_INTERVALS.world);
}

document.addEventListener('visibilitychange', function () {
  if (document.hidden) return;
  refreshPaperStatus();
  if (!TOKEN) return;
  refreshPlayers();
  refreshTPS();
  refreshWorldInfo(false);
  refreshRuntimeToggles();
});

async function refreshPaperDashboard() {
  if (PAPER_REFRESHING || !TOKEN || !paperReady()) return;
  PAPER_REFRESHING = true;
  var cards = LOADING_CARD_IDS.filter(function (id) { return id !== 'card-config' && id !== 'card-plugins'; });
  cards.forEach(function (id) { setCardLoading(id, true); });
  try {
    await refreshPlayers();
    await sleep(120);
    await refreshTPS();
    await sleep(120);
    await refreshWorldInfo(true);
    await sleep(120);
    await refreshRuntimeToggles();
    await sleep(120);
    await refreshServerVersion();
    await sleep(120);
    await refreshSeedMap();
  } finally {
    cards.forEach(function (id) { setCardLoading(id, false); });
    PAPER_REFRESHING = false;
  }
}

function finishAuthenticated(message) {
  setStatus('on', '已连接');
  log(message || '认证成功，RCON 已连接', 'info');
  startAutoRefresh();
  refreshConfig();
  refreshPlugins();
  if (paperReady()) refreshPaperDashboard();
  else renderPaperStatus();
}

async function loginWithPassword(pw) {
  try {
    var r = await fetch(BASE + '/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pw })
    });
    var d = await r.json();
    if (!d.success || !d.token) {
      clearAuthState();
      clearStoredToken();
      return { success: false, error: d.error || 'login failed' };
    }
    TOKEN = d.token;
    saveStoredToken(d.token, d.expires_at);
    return { success: true };
  } catch (e) {
    clearAuthState();
    return { success: false, error: e.message };
  }
}

async function restoreStoredAuth() {
  var storedToken = getStoredToken();
  if (!storedToken) {
    clearAuthState();
    setStatus('auth', '请输入密码');
    return false;
  }
  if (!beginRefresh('auth')) return true;
  if (!TOKEN) log('检测到浏览器已保存登录态，正在自动恢复连接', 'info');
  TOKEN = storedToken;
  setStatus('auth', '恢复登录中');
  try {
    var r = await fetch(BASE + '/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(8000),
      body: JSON.stringify(buildAuthPayload({ action: 'get' }))
    });
    var d = await r.json();
    if (TOKEN !== storedToken) return true;
    if (d.success) {
      finishAuthenticated('已从当前浏览器会话恢复登录');
      return true;
    }
    if (!isAuthError(d.error)) return true;
  } catch (e) { return true; }
  finally { endRefresh('auth'); }
  clearAuthState();
  clearStoredToken();
  setStatus('auth', '请输入密码');
  log('已保存的登录态失效，请重新输入密码', 'warn');
  return false;
}

function handleAuthFailure(message) {
  clearAuthState();
  clearStoredToken();
  if (_modalCb) return;
  resetAuthUi();
  setStatus('auth', '请重新登录');
  logClient('console.requestFailed', { error: message || localize('认证失败') }, 'warn');
  toast('登录态已失效，请重新认证');
  openLoginModal();
}

function logout() {
  clearAuthState();
  clearStoredToken();
  resetAuthUi();
  log('已退出登录，本地登录态已清除', 'info');
  toast('已退出登录');
  openLoginModal();
}

function showModal(cb) {
  _modalCb = cb;
  document.getElementById('modal-overlay').classList.remove('hidden');
  document.getElementById('modal-pw').value = '';
  document.getElementById('modal-pw').focus();
}
function modalConfirm() {
  var pw = document.getElementById('modal-pw').value.trim();
  document.getElementById('modal-overlay').classList.add('hidden');
  if (_modalCb) { _modalCb(pw); _modalCb = null; }
}
function modalCancel() {
  document.getElementById('modal-overlay').classList.add('hidden');
  if (_modalCb) { _modalCb(null); _modalCb = null; }
}

function openLoginModal() {
  if (_modalCb) return;
  setStatus('auth', '请输入密码');
  showModal(async function(pw) {
    if (!pw) {
      setStatus('off', '未认证');
      log('未输入密码 — 刷新页面或重新打开弹窗可再次认证', 'warn');
      return;
    }
    setStatus('auth', '验证中');
    log('正在验证密码并创建浏览器登录态', 'info');
    var result = await loginWithPassword(pw);
    if (result.success) {
      finishAuthenticated('认证成功，登录态将在当前浏览器会话中保持');
    } else {
      setStatus('off', '密码错误');
      logClient('console.requestFailed', { error: result.error || 'unknown' }, 'err');
      toast('密码错误或登录失败，请重试');
      setTimeout(openLoginModal, 0);
    }
  });
}

function normalizeDialogValue(value) {
  return String(value == null ? '' : value).trim();
}

function actionDialogBackdrop(event) {
  if (event.target && event.target.id === 'action-overlay') actionDialogCancel();
}

function getActionFieldElement(name) {
  return document.querySelector('#action-fields [data-field="' + name + '"]');
}

function collectActionValues() {
  var values = {};
  if (!ACTION_DIALOG) return values;
  (ACTION_DIALOG.config.fields || []).forEach(function (field) {
    var input = getActionFieldElement(field.name);
    values[field.name] = input ? normalizeDialogValue(input.value) : '';
  });
  return values;
}

function updateActionPreview() {
  var wrap = document.getElementById('action-preview-wrap');
  var code = document.getElementById('action-preview');
  if (!ACTION_DIALOG) {
    wrap.classList.add('hidden');
    code.textContent = '';
    return;
  }
  var config = ACTION_DIALOG.config;
  var values = collectActionValues();
  var preview = '';
  try {
    if (typeof config.previewText === 'function') {
      preview = config.previewText(values);
    } else if (typeof config.previewText === 'string') {
      preview = config.previewText;
    } else if (typeof config.buildCommand === 'function') {
      preview = config.buildCommand(values) || '';
    }
  } catch (e) {
    preview = '';
  }
  if (preview) {
    wrap.classList.remove('hidden');
    code.textContent = preview;
  } else {
    wrap.classList.add('hidden');
    code.textContent = '';
  }
}

function renderActionFields(fields) {
  var container = document.getElementById('action-fields');
  container.innerHTML = '';
  fields.forEach(function (field) {
    var label = document.createElement('label');
    label.className = 'dialog-field';

    var title = document.createElement('span');
    title.textContent = field.labelKey ? t(field.labelKey) : localize(field.label || field.name);
    label.appendChild(title);

    var input = document.createElement('input');
    input.className = 'dialog-input';
    input.type = field.type || 'text';
    input.autocomplete = 'off';
    input.placeholder = field.placeholderKey ? t(field.placeholderKey) : localize(field.placeholder || '');
    input.value = typeof field.value === 'undefined' ? '' : String(field.value);
    input.setAttribute('data-field', field.name);
    if (field.required) input.required = true;
    if (typeof field.min !== 'undefined') input.min = field.min;
    if (typeof field.max !== 'undefined') input.max = field.max;
    label.appendChild(input);
    if (Array.isArray(field.list) && field.list.length) {
      var listId = 'action-list-' + String(field.name || 'field').replace(/[^a-zA-Z0-9_-]/g, '-');
      var datalist = document.createElement('datalist');
      datalist.id = listId;
      var listValues = field.list.filter(function (item, index, arr) {
        return item && arr.indexOf(item) === index;
      });
      listValues.forEach(function (item) {
        var option = document.createElement('option');
        option.value = String(item);
        datalist.appendChild(option);
      });
      input.setAttribute('list', listId);
      label.appendChild(datalist);

      var suggestions = document.createElement('div');
      suggestions.className = 'dialog-suggestions hidden';
      label.appendChild(suggestions);

      var renderSuggestions = function (keyword) {
        var search = String(keyword || '').trim().toLowerCase();
        var filtered = listValues.filter(function (item) {
          return !search || String(item).toLowerCase().indexOf(search) >= 0;
        });
        suggestions.innerHTML = '';
        if (!filtered.length) {
          suggestions.classList.add('hidden');
          return;
        }
        filtered.forEach(function (item) {
          var btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'dialog-suggestion-btn';
          btn.textContent = String(item);
          btn.onmousedown = function (event) { event.preventDefault(); };
          btn.onclick = function () {
            input.value = String(item);
            suggestions.classList.add('hidden');
            input.focus();
            updateActionPreview();
          };
          suggestions.appendChild(btn);
        });
        suggestions.classList.remove('hidden');
      };

      input.onfocus = function () {
        renderSuggestions(input.value);
      };
      input.onblur = function () {
        setTimeout(function () {
          suggestions.classList.add('hidden');
        }, 120);
      };
      input.oninput = function () {
        updateActionPreview();
        renderSuggestions(input.value);
      };
    } else {
      input.oninput = updateActionPreview;
    }

    if (field.hint) {
      var hint = document.createElement('small');
      hint.className = 'dialog-hint';
      hint.textContent = field.hintKey ? t(field.hintKey) : localize(field.hint);
      label.appendChild(hint);
    }

    container.appendChild(label);
  });
}

function focusFirstActionField() {
  var first = document.querySelector('#action-fields .dialog-input');
  if (first) first.focus();
}

function showActionDialog(config) {
  return new Promise(function (resolve) {
    ACTION_DIALOG = { config: config || {}, resolve: resolve };
    renderActionDialog();
    setTimeout(focusFirstActionField, 0);
  });
}

function renderActionDialog(snapshot) {
  if (!ACTION_DIALOG) return;
  var config = ACTION_DIALOG.config;
  document.getElementById('action-kicker').textContent = config.kickerKey ? t(config.kickerKey) : (config.kicker ? renderPresentation(config.kicker) : t('dialog.action.defaultKicker'));
  document.getElementById('action-title').textContent = config.titleKey ? t(config.titleKey) : (config.title ? renderPresentation(config.title) : t('dialog.action.defaultTitle'));
  document.getElementById('action-desc').textContent = config.descriptionKey ? t(config.descriptionKey) : (config.description ? renderPresentation(config.description) : t('dialog.action.defaultDescription'));
  document.getElementById('action-confirm').textContent = config.confirmKey ? t(config.confirmKey) : (config.confirmText ? renderPresentation(config.confirmText) : t('dialog.action.confirm'));
  document.getElementById('action-confirm').classList.toggle('danger-btn', !!config.danger);
  renderActionFields(config.fields || []);
  document.getElementById('action-overlay').classList.remove('hidden');
  restoreActionDialogSnapshot(snapshot);
  updateActionPreview();
}

function captureActionDialogSnapshot() {
  if (!ACTION_DIALOG) return null;
  var active = document.activeElement;
  var fields = {};
  Array.prototype.forEach.call(document.querySelectorAll('#action-fields .dialog-input'), function (input) {
    fields[input.getAttribute('data-field')] = { value: input.value, checked: input.checked, selectedIndex: input.selectedIndex, required: input.required, min: input.min, max: input.max };
  });
  return {
    fields: fields,
    danger: document.getElementById('action-confirm').classList.contains('danger-btn'),
    focus: active && active.getAttribute ? active.getAttribute('data-field') : '',
    start: active && typeof active.selectionStart === 'number' ? active.selectionStart : null,
    end: active && typeof active.selectionEnd === 'number' ? active.selectionEnd : null,
    direction: active && active.selectionDirection ? active.selectionDirection : 'none'
  };
}

function restoreActionDialogSnapshot(snapshot) {
  if (!snapshot) return;
  Object.keys(snapshot.fields).forEach(function (name) {
    var input = getActionFieldElement(name);
    var saved = snapshot.fields[name];
    if (!input) return;
    input.value = saved.value;
    input.checked = saved.checked;
    input.required = saved.required;
    input.min = saved.min;
    input.max = saved.max;
    if (typeof saved.selectedIndex === 'number' && saved.selectedIndex >= 0) input.selectedIndex = saved.selectedIndex;
  });
  document.getElementById('action-confirm').classList.toggle('danger-btn', snapshot.danger);
  if (snapshot.focus) {
    var focused = getActionFieldElement(snapshot.focus);
    if (focused) {
      focused.focus();
      if (snapshot.start !== null && snapshot.end !== null && focused.setSelectionRange) focused.setSelectionRange(snapshot.start, snapshot.end, snapshot.direction);
    }
  }
}

function closeActionDialog(result) {
  var current = ACTION_DIALOG;
  ACTION_DIALOG = null;
  document.getElementById('action-overlay').classList.add('hidden');
  document.getElementById('action-fields').innerHTML = '';
  updateActionPreview();
  if (current && current.resolve) current.resolve(result);
}

function actionDialogCancel() {
  closeActionDialog(null);
}

function submitActionDialog(event) {
  if (event) event.preventDefault();
  if (!ACTION_DIALOG) return;
  var config = ACTION_DIALOG.config;
  var values = collectActionValues();
  var missingField = null;
  (config.fields || []).forEach(function (field) {
    if (!missingField && field.required && !normalizeDialogValue(values[field.name])) {
      missingField = field;
    }
  });
  if (missingField) {
    toastClient('validation.requiredField', { name: missingField.labelKey ? t(missingField.labelKey) : localize(missingField.label || missingField.name) });
    var input = getActionFieldElement(missingField.name);
    if (input) input.focus();
    return;
  }
  closeActionDialog(values);
}

document.addEventListener('keydown', function (event) {
  if (event.key === 'Escape' && ACTION_DIALOG) actionDialogCancel();
});

async function runDialogCommand(config) {
  var values = await showActionDialog(config);
  if (!values) return;
  var cmd = typeof config.buildCommand === 'function' ? config.buildCommand(values) : '';
  if (!cmd) return;
  var result = await send(cmd);
  if (result && result.success) toastClient('toast.commandSubmitted');
}

function playerField(label, placeholder) {
  return {
    name: 'player',
    label: label || '玩家名',
    placeholder: placeholder || ONLINE_PLAYERS[0] || 'Steve',
    required: true,
    list: ONLINE_PLAYERS.slice()
  };
}

function textField(name, label, placeholder, options) {
  var field = { name: name, label: label, placeholder: placeholder || '' };
  options = options || {};
  Object.keys(options).forEach(function (key) { field[key] = options[key]; });
  return field;
}

function buildCommandParts(parts) {
  return (parts || []).map(function (part) {
    return String(part == null ? '' : part).trim();
  }).filter(Boolean).join(' ');
}

async function opPlayer() {
  await runDialogCommand({
    kicker: '玩家管理',
    title: '授予 OP',
    description: '输入玩家名后，将发送管理员授权命令。',
    confirmText: '授予 OP',
    fields: [playerField('玩家名', 'Steve')],
    buildCommand: function (values) { return 'op ' + values.player; }
  });
}

async function deopPlayer() {
  await runDialogCommand({
    kicker: '玩家管理',
    title: '取消 OP',
    description: '输入玩家名后，将移除该玩家的管理员权限。',
    confirmText: '移除 OP',
    fields: [playerField('玩家名', 'Steve')],
    buildCommand: function (values) { return 'deop ' + values.player; }
  });
}

async function setPlayerGamemode(mode, label) {
  await runDialogCommand({
    kicker: '玩家管理',
    title: '切换到' + label + '模式',
    description: '输入玩家名后，将切换该玩家的游戏模式。',
    confirmText: '切换模式',
    fields: [playerField('玩家名', 'Steve')],
    buildCommand: function (values) { return 'gamemode ' + mode + ' ' + values.player; }
  });
}

async function clearPlayerInventory() {
  await runDialogCommand({
    kicker: '玩家管理',
    title: '清空玩家背包',
    description: '输入玩家名后，将清空该玩家的物品栏。',
    confirmText: '清空背包',
    fields: [playerField('玩家名', 'Steve')],
    buildCommand: function (values) { return 'clear ' + values.player; }
  });
}

async function killPlayer() {
  await runDialogCommand({
    kicker: '玩家管理',
    title: '击杀玩家',
    description: '输入玩家名后，将立即执行击杀命令。',
    confirmText: '立即击杀',
    danger: true,
    fields: [playerField('玩家名', 'Steve')],
    buildCommand: function (values) { return 'kill ' + values.player; }
  });
}

async function kickPlayer() {
  await runDialogCommand({
    kicker: '玩家管理',
    title: '踢出玩家',
    description: '可选填写踢出原因，留空则直接执行踢出。',
    confirmText: '踢出玩家',
    fields: [
      playerField('玩家名', 'Steve'),
      { name: 'reason', label: '原因', placeholder: '例如：请先阅读公告' }
    ],
    buildCommand: function (values) { return values.reason ? 'kick ' + values.player + ' ' + values.reason : 'kick ' + values.player; }
  });
}

async function locatePlayerInfo() {
  var values = await showActionDialog({
    kicker: '玩家管理',
    title: '查看玩家坐标',
    description: '读取玩家当前位置；优先走 Dynmap，找不到时会回退到玩家存档快照。',
    confirmText: '查看坐标',
    fields: [playerField('玩家名', ONLINE_PLAYERS[0] || 'Steve')],
    previewText: function (input) {
      return input && input.player ? ('查询玩家“' + input.player + '”的当前位置') : '';
    }
  });
  if (!values || !values.player) return;
  try {
    var info = await fetchDynmapPlayerLocation(values.player);
    var sourceText = info.source === 'playerdata' ? presentation('structure.sourcePlayerdata') : (info.source === 'dynmap' ? 'Dynmap' : info.source || 'unknown');
    logClient('console.playerCoordinates', { player: info.name, world: info.world, x: info.x, y: info.y, z: info.z, source: sourceText }, 'info');
    toastClient('toast.playerCoordinates', { player: info.name, x: info.x, y: info.y, z: info.z });
  } catch (e) {
    logClient('console.requestFailed', { error: e.message || 'unknown' }, 'err');
    if (e.message) toastRaw(e.message); else toast('读取玩家坐标失败');
  }
}

async function banPlayer() {
  await runDialogCommand({
    kicker: '玩家管理',
    title: '封禁玩家',
    description: '可选填写封禁原因，留空则直接执行封禁。',
    confirmText: '封禁玩家',
    danger: true,
    fields: [
      playerField('玩家名', 'Steve'),
      { name: 'reason', label: '原因', placeholder: '例如：作弊 / 恶意破坏' }
    ],
    buildCommand: function (values) { return values.reason ? 'ban ' + values.player + ' ' + values.reason : 'ban ' + values.player; }
  });
}

async function pardonPlayer() {
  await runDialogCommand({
    kicker: '玩家管理',
    title: '解除封禁',
    description: '输入玩家名后，将发送解除封禁命令。',
    confirmText: '解除封禁',
    fields: [playerField('玩家名', 'Steve')],
    buildCommand: function (values) { return 'pardon ' + values.player; }
  });
}

async function whitelistAddPlayer() {
  await runDialogCommand({
    kicker: '白名单管理',
    title: '添加白名单',
    description: '输入玩家名后，将该玩家加入白名单。',
    confirmText: '加入白名单',
    fields: [playerField('玩家名', 'Steve')],
    buildCommand: function (values) { return 'whitelist add ' + values.player; }
  });
}

async function whitelistRemovePlayer() {
  await runDialogCommand({
    kicker: '白名单管理',
    title: '移除白名单',
    description: '输入玩家名后，将该玩家从白名单中移除。',
    confirmText: '移出白名单',
    fields: [playerField('玩家名', 'Steve')],
    buildCommand: function (values) { return 'whitelist remove ' + values.player; }
  });
}

async function banIpAddress() {
  await runDialogCommand({
    kicker: '白名单管理',
    title: '封禁 IP 地址',
    description: '输入 IP 后会发送 ban-ip；原因可选，适合处理同一地址重复恶意登录。',
    confirmText: '封禁 IP',
    danger: true,
    fields: [
      textField('ip', 'IP 地址', '127.0.0.1', { required: true, hint: '示例：203.0.113.25' }),
      textField('reason', '原因（可选）', '例如：刷屏 / 恶意登录')
    ],
    buildCommand: function (values) {
      return values.reason ? ('ban-ip ' + values.ip + ' ' + values.reason) : ('ban-ip ' + values.ip);
    }
  });
}

async function pardonIpAddress() {
  await runDialogCommand({
    kicker: '白名单管理',
    title: '解除 IP 封禁',
    description: '输入 IP 后会发送 pardon-ip。',
    confirmText: '解除 IP 封禁',
    fields: [
      textField('ip', 'IP 地址', '127.0.0.1', { required: true })
    ],
    buildCommand: function (values) { return 'pardon-ip ' + values.ip; }
  });
}

async function teleportPlayerToPlayer() {
  await runDialogCommand({
    kicker: '世界传送',
    title: 'TP 玩家 → 玩家',
    description: '输入源玩家和目标玩家，执行玩家到玩家的传送。',
    confirmText: '执行传送',
    fields: [
      { name: 'player', label: '源玩家', placeholder: 'Steve', required: true },
      { name: 'target', label: '目标玩家', placeholder: 'Alex', required: true }
    ],
    buildCommand: function (values) { return 'tp ' + values.player + ' ' + values.target; }
  });
}

async function teleportPlayerToCoords() {
  await runDialogCommand({
    kicker: '世界传送',
    title: 'TP 到坐标',
    description: '输入玩家名和坐标，支持使用 ~ 相对坐标。',
    confirmText: '执行传送',
    fields: [
      playerField('玩家名', 'Steve'),
      { name: 'destination', label: '目标坐标', placeholder: '~ ~ ~', value: '~ ~ ~', required: true, hint: '示例：100 64 200 或 ~ ~1 ~' }
    ],
    buildCommand: function (values) { return 'tp ' + values.player + ' ' + values.destination; }
  });
}

async function teleportPlayerToTarget() {
  await runDialogCommand({
    kicker: '世界传送',
    title: 'TP 玩家 → 目标',
    description: '输入玩家名和目标玩家名，立即执行传送。',
    confirmText: '执行传送',
    fields: [
      playerField('玩家名', 'Steve'),
      { name: 'target', label: '目标玩家', placeholder: 'Alex', required: true }
    ],
    buildCommand: function (values) { return 'tp ' + values.player + ' ' + values.target; }
  });
}

async function setWorldSpawnCommand() {
  await runDialogCommand({
    kicker: '世界传送',
    title: '设置世界出生点',
    description: '可填写世界出生点坐标；留空时会使用执行命令者当前位置。',
    confirmText: '设置出生点',
    fields: [
      textField('location', '出生点坐标（可选）', '~ ~ ~', { hint: '例：100 64 200；留空则直接执行 setworldspawn' })
    ],
    buildCommand: function (values) {
      return buildCommandParts(['setworldspawn', values.location]);
    }
  });
}

async function setPlayerSpawnpointCommand() {
  await runDialogCommand({
    kicker: '世界传送',
    title: '设置玩家重生点',
    description: '请输入玩家名；坐标可选，留空时将把当前站位设为该玩家重生点。',
    confirmText: '设置重生点',
    fields: [
      playerField('玩家名', 'Steve'),
      textField('location', '重生点坐标（可选）', '~ ~ ~', { hint: '例：100 64 200；留空则只执行 spawnpoint 玩家名' })
    ],
    buildCommand: function (values) {
      return buildCommandParts(['spawnpoint', values.player, values.location]);
    }
  });
}

async function setWorldBorder() {
  var values = await showActionDialog({
    kicker: '世界传送',
    title: '设置世界边界',
    description: '支持可选设置边界中心，再设置边界直径和过渡时间。留空中心则只修改边界大小。',
    confirmText: '应用边界',
    fields: [
      textField('center', '边界中心（可选）', '0 0', { hint: '格式：X Z，例如 0 0；留空则不修改中心' }),
      textField('size', '边界直径', '2000', { required: true, hint: '填写最终直径，例如 2000' }),
      textField('seconds', '过渡秒数（可选）', '0', { hint: '0 表示立即生效；也可以填 30 表示 30 秒平滑变化' })
    ],
    previewText: function (input) {
      var parts = [];
      if (input && input.center) parts.push('worldborder center ' + input.center);
      parts.push(buildCommandParts(['worldborder', 'set', input && input.size, input && input.seconds && input.seconds !== '0' ? input.seconds : '']));
      return parts.filter(Boolean).join('  &&  ');
    }
  });
  if (!values) return;
  if (values.center) await send('worldborder center ' + values.center);
  await send(buildCommandParts(['worldborder', 'set', values.size, values.seconds && values.seconds !== '0' ? values.seconds : '']));
}

async function setTimeValue(value, label) {
  if (typeof value !== 'undefined' && value !== null && value !== '') {
    send('time set ' + value);
    return;
  }
  await runDialogCommand({
    kicker: '世界设置',
    title: '设置时间',
    description: '填写具体 tick 值；常用参考：0=日出，6000=正午，13000=黄昏，18000=午夜。',
    confirmText: '设置时间',
    fields: [
      textField('ticks', '时间 tick', '6000', { required: true, type: 'number', min: 0, hint: '可填任意非负整数，例如 1000 / 6000 / 18000' })
    ],
    previewText: function (input) {
      return input && input.ticks ? ('time set ' + input.ticks) : '';
    },
    buildCommand: function (values) { return 'time set ' + values.ticks; }
  });
}

function setWorldSetting(select) {
  var setting = select.getAttribute('data-world-setting');
  var modes = setting === 'difficulty' ? ['peaceful', 'easy', 'normal', 'hard'] : ['survival', 'creative', 'adventure', 'spectator'];
  var mode = modes[select.value];
  var current = WORLD_INFO_CACHE && WORLD_INFO_CACHE[setting];
  select.value = current == null ? '' : String(current);
  if (setting === 'difficulty') setDifficulty(mode);
  else setDefaultGamemode(mode);
}

async function setDifficulty(mode, label) {
  if (mode) {
    send('difficulty ' + mode);
    return;
  }
  await runDialogCommand({
    kicker: '世界设置',
    title: '设置难度',
    description: '可填写 peaceful / easy / normal / hard。',
    confirmText: '设置难度',
    fields: [
      textField('difficulty', '难度', 'normal', { required: true, list: ['peaceful', 'easy', 'normal', 'hard'], hint: '原版支持：peaceful / easy / normal / hard' })
    ],
    previewText: function (input) {
      return input && input.difficulty ? ('difficulty ' + input.difficulty) : '';
    },
    buildCommand: function (values) { return 'difficulty ' + values.difficulty; }
  });
}

async function setDefaultGamemode(mode, label) {
  if (mode) {
    send('defaultgamemode ' + mode);
    return;
  }
  await runDialogCommand({
    kicker: '世界设置',
    title: '设置默认游戏模式',
    description: '修改新进入服务器玩家的默认模式。',
    confirmText: '设置默认模式',
    fields: [
      textField('mode', '默认模式', 'survival', { required: true, list: ['survival', 'creative', 'adventure', 'spectator'], hint: '可填写 survival / creative / adventure / spectator' })
    ],
    previewText: function (input) {
      return input && input.mode ? ('defaultgamemode ' + input.mode) : '';
    },
    buildCommand: function (values) { return 'defaultgamemode ' + values.mode; }
  });
}

async function giveItemToPlayer() {
  await runDialogCommand({
    kicker: '命令工坊',
    title: '发放物品 / 方块',
    description: '支持填写物品 ID、数量、数据值和 NBT。适合 give、测试物资、快速发装备。',
    confirmText: '发放物品',
    fields: [
      playerField('玩家名', 'Steve'),
      textField('item', '物品 ID', 'minecraft:diamond_sword', { required: true }),
      textField('amount', '数量', '1'),
      textField('data', '数据值', '0'),
      textField('nbt', 'NBT（可选）', '{display:{Name:"Epic Blade"}}')
    ],
    buildCommand: function (values) {
      return buildCommandParts(['give', values.player, values.item, values.amount || '1', values.data, values.nbt]);
    }
  });
}

async function applyStatusEffect() {
  await runDialogCommand({
    kicker: '命令工坊',
    title: '添加状态效果',
    description: '支持填写效果名、持续时间、等级和是否隐藏粒子。',
    confirmText: '应用效果',
    fields: [
      playerField('玩家名', 'Steve'),
      textField('effect', '效果', 'speed', { required: true }),
      textField('seconds', '持续秒数', '30'),
      textField('amplifier', '等级', '1'),
      textField('hideParticles', '隐藏粒子（可选）', 'true / false')
    ],
    buildCommand: function (values) {
      return buildCommandParts(['effect', values.player, values.effect, values.seconds || '30', values.amplifier || '1', values.hideParticles]);
    }
  });
}

async function grantExperience() {
  await runDialogCommand({
    kicker: '命令工坊',
    title: '发放经验 / 等级',
    description: '数量字段支持直接写经验值，或在末尾加 L 表示等级，例如 5L。',
    confirmText: '发放经验',
    fields: [
      playerField('玩家名', 'Steve'),
      textField('amount', '数量', '5L', { required: true, hint: '例：100（经验点）或 5L（等级）' })
    ],
    buildCommand: function (values) {
      return buildCommandParts(['xp', values.amount, values.player]);
    }
  });
}

async function enchantPlayerItem() {
  await runDialogCommand({
    kicker: '命令工坊',
    title: '附魔玩家手持物品',
    description: '输入玩家名、附魔 ID/名称与等级，执行 enchant 命令。',
    confirmText: '执行附魔',
    fields: [
      playerField('玩家名', 'Steve'),
      textField('enchantment', '附魔', 'sharpness', { required: true, hint: '兼容填写名称或数字 ID' }),
      textField('level', '等级', '1')
    ],
    buildCommand: function (values) {
      return buildCommandParts(['enchant', values.player, values.enchantment, values.level || '1']);
    }
  });
}

async function summonEntity() {
  await runDialogCommand({
    kicker: '命令工坊',
    title: '召唤实体',
    description: '可指定实体类型、坐标与 NBT。适合召唤生物、掉落物、盔甲架等。',
    confirmText: '召唤实体',
    fields: [
      textField('entity', '实体', 'Zombie', { required: true }),
      textField('location', '坐标', '~ ~ ~', { value: '~ ~ ~', required: true }),
      textField('nbt', 'NBT（可选）', '{CustomName:"Boss"}')
    ],
    buildCommand: function (values) {
      return buildCommandParts(['summon', values.entity, values.location, values.nbt]);
    }
  });
}

async function setBlockCommand() {
  await runDialogCommand({
    kicker: '命令工坊',
    title: '放置方块',
    description: '支持 setblock 常用参数：坐标、方块 ID、数据值、模式与可选 NBT。',
    confirmText: '放置方块',
    fields: [
      textField('location', '坐标', '~ ~ ~', { value: '~ ~ ~', required: true }),
      textField('block', '方块 ID', 'minecraft:stone', { required: true }),
      textField('data', '数据值', '0'),
      textField('mode', '模式（可选）', 'replace / destroy / keep'),
      textField('nbt', 'NBT（可选）', '{Lock:"admin"}')
    ],
    buildCommand: function (values) {
      return buildCommandParts(['setblock', values.location, values.block, values.data, values.mode, values.nbt]);
    }
  });
}

async function fillAreaCommand() {
  await runDialogCommand({
    kicker: '命令工坊',
    title: '区域填充',
    description: '支持 fill 命令常用参数，可快速铺路、清区域、替换方块。',
    confirmText: '执行填充',
    fields: [
      textField('from', '起点坐标', '~ ~ ~', { value: '~ ~ ~', required: true }),
      textField('to', '终点坐标', '~10 ~5 ~10', { value: '~10 ~5 ~10', required: true }),
      textField('block', '方块 ID', 'minecraft:stone', { required: true }),
      textField('data', '数据值', '0'),
      textField('mode', '模式（可选）', 'replace / hollow / destroy / keep / outline'),
      textField('nbt', 'NBT（可选）', '{Lock:"admin"}')
    ],
    buildCommand: function (values) {
      return buildCommandParts(['fill', values.from, values.to, values.block, values.data, values.mode, values.nbt]);
    }
  });
}

async function runCustomCommandDialog() {
  await runDialogCommand({
    kicker: '命令工坊',
    title: '自定义命令',
    description: '这里可以填写任意原版 / Bukkit / Paper 命令模板；复杂命令也可以继续直接在左侧控制台输入。',
    confirmText: '发送命令',
    fields: [
      textField('command', '命令名', 'give', { required: true, hint: '不要带前导 / ，例如 give / gamerule / scoreboard' }),
      textField('args', '参数', 'Steve minecraft:diamond 1', { required: true })
    ],
    buildCommand: function (values) {
      return buildCommandParts([values.command, values.args]);
    }
  });
}

async function send(cmd, opts) {
  if (!TOKEN) { toast('请先登录'); openLoginModal(); return; }
  if (!paperReady()) {
    toastClient('status.paper.dataWaiting');
    return { success: false, code: 'paper_not_ready' };
  }
  opts = opts || {};
  logRaw(cmd, 'cmd');
  try {
    var r = await fetch(BASE + '/api/rcon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildAuthPayload({ command: cmd }))
    });
    var d = await r.json();
    if (d.success) {
      if (d.response) logRaw(d.response, 'out');
      else logClient('console.emptyOutput', {}, 'out');
      var effect = classifyCommandRefresh(cmd);
      if (!opts.skipAutoRefresh) {
        if (effect.world || effect.config) queueWorldInfoRefresh(500, true);
        if (effect.runtime || effect.config) queueRuntimeRefresh(500);
      }
      return d;
    } else {
      if (isAuthError(d.error)) {
        handleAuthFailure(d.error);
        return d;
      }
      logClient('console.requestFailed', { error: d.error || 'unknown' }, 'err');
      return d;
    }
  } catch (e) {
    logClient('console.requestFailed', { error: e.message }, 'err');
    return { success: false, error: e.message };
  }
}

function exec() {
  var inp = document.getElementById('cmd');
  var v = inp.value.trim();
  if (!v) return;
  inp.value = '';
  send(v);
}

function playerAvatar(name) {
  var hash = 5381;
  String(name).toLowerCase().split('').forEach(function (character) { hash = ((hash * 33) ^ character.charCodeAt(0)) >>> 0; });
  var pixels = '';
  for (var y = 0; y < 6; y++) {
    hash ^= hash << 13; hash ^= hash >>> 17; hash ^= hash << 5;
    for (var x = 0; x < 3; x++) {
      if ((hash >>> x) & 1) {
        pixels += '<path d="M' + (x + 1) + ' ' + (y + 1) + 'h1v1h-1zM' + (6 - x) + ' ' + (y + 1) + 'h1v1h-1z"/>';
      }
    }
  }
  return '<svg class="player-avatar" viewBox="0 0 8 8" aria-hidden="true" shape-rendering="crispEdges">' + pixels + '</svg>';
}

function escapeHtml(s) {
  return String(s).replace(/[&<>'"]/g, function (ch) {
    return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[ch];
  });
}

function syncConfigControls() {
  document.querySelectorAll('[data-config-key]').forEach(function (el) {
    var key = el.getAttribute('data-config-key');
    var cb = el.querySelector('input[type=checkbox]');
    if (!cb) return;
    cb.checked = String(CONFIG_CACHE[key]).toLowerCase() === 'true';
  });
  [
    ['motd', 'cfg-motd'],
    ['max-players', 'cfg-max-players'],
    ['view-distance', 'cfg-view-distance'],
    ['spawn-protection', 'cfg-spawn-protection']
  ].forEach(function (pair) {
    var value = CONFIG_CACHE[pair[0]];
    var input = document.getElementById(pair[1]);
    if (input && typeof value !== 'undefined') input.value = value;
  });
}

async function refreshConfig() {
  if (!TOKEN) return;
  if (!beginRefresh('config')) return;
  setCardLoading('card-config', true);
  try {
    var d = await configRequest({ action: 'get' });
    if (d.success) {
      CONFIG_CACHE = d.config || {};
      syncConfigControls();
      rerenderWorldInfo();
    }
  } catch (e) {
    logClient('console.requestFailed', { error: e.message }, 'warn');
  } finally {
    setCardLoading('card-config', false);
    endRefresh('config');
  }
}

async function refreshPlayers() {
  if (!TOKEN) return;
  if (!beginRefresh('players')) return;
  try {
    var r = await fetch(BASE + '/api/rcon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildAuthPayload({ command: 'list' }))
    });
    var d = await r.json();
    if (d.success && paperReady()) {
      var resp = d.response || '';
      var m = resp.match(/(\d+)\/(\d+)/);
      if (m) {
        var namesStr = resp.split(':')[1] || '';
        var names = namesStr.trim() ? namesStr.split(',').map(function (s) { return s.trim(); }) : [];
        ONLINE_PLAYERS = names.slice();
        renderPlayers();
        rerenderWorldInfo();
      }
    } else if (isAuthError(d.error)) {
      handleAuthFailure(d.error);
    }
  } catch (e) {
    if (!paperReady()) { renderPaperStatus(); return; }
    ONLINE_PLAYERS = [];
    document.getElementById('player-count').textContent = formatNumber(0);
    var heroPlayerCount = document.getElementById('hero-player-count');
    if (heroPlayerCount) heroPlayerCount.textContent = '0';
    document.getElementById('players').innerHTML = '<div class="empty-state">' + escapeHtml(localize('读取在线玩家失败')) + '</div>';
  } finally {
    setCardLoading('card-players', false);
    endRefresh('players');
  }
}

async function refreshTPS() {
  if (!TOKEN) return;
  if (!beginRefresh('tps')) return;
  try {
    var r = await fetch(BASE + '/api/rcon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildAuthPayload({ command: 'tps' }))
    });
    var d = await r.json();
    if (d.success && paperReady()) {
      var resp = d.response || '';
      var tail = resp.split(':').pop() || resp;
      var ms = tail.match(/\*?\d+\.?\d*/g);
      if (ms && ms.length >= 3) {
        TPS_VALUES = ms.slice(-3).map(function (value) { return parseFloat(value.replace('*', '')); });
        renderTPS();
      }
    } else if (isAuthError(d.error)) {
      handleAuthFailure(d.error);
    }
  } catch (e) {
    if (!paperReady()) { renderPaperStatus(); return; }
    var heroTps = document.getElementById('hero-tps');
    if (heroTps) heroTps.textContent = '--';
    document.getElementById('tps-bars').innerHTML = '<div class="empty-state">' + escapeHtml(localize('读取 TPS 失败')) + '</div>';
  } finally {
    setCardLoading('card-tps', false);
    endRefresh('tps');
  }
}

async function refreshWorldInfo(forceRefresh) {
  if (!TOKEN) return;
  if (!beginRefresh('world')) return;
  try {
    var d = await worldStateRequest(forceRefresh ? { force_refresh: true } : {});
    if (!d.success) throw new Error(d.error || '世界状态返回为空');
    WORLD_INFO_CACHE = d;
    renderWorldInfo(d);
  } catch (e) {
    if (paperReady()) setWorldInfoPlaceholder('读取世界状态失败', e.message || 'unknown');
    else renderPaperStatus();
  } finally {
    setCardLoading('card-world', false);
    endRefresh('world');
  }
}

async function refreshSeedMap() {
  if (!TOKEN) return;
  if (!beginRefresh('seedmap')) return;
  setSeedState('', presentation('seed.reading'));
  try {
    var d = await seedRequest({});
    if (d.success) {
      var sourceText = d.source === 'server.properties' ? 'server.properties' : (d.source === 'rcon' ? 'RCON /seed' : '未知来源');
      LAST_STRUCTURE_RESULT = null;
      setSeedState(d.seed || '', presentation('seed.source', { source: sourceText, hint: defaultSeedHint() }));
      if (SERVER_INFO.nativeSeedFinderReady) {
        setSpawnCard(null);
        setStructureStatus('可开始搜索', '点击“搜索附近”后会弹出悬浮框');
        renderStructurePlaceholder('点击“搜索附近”后会弹出悬浮框，输入中心坐标和半径即可查询附近结构');
      } else {
        setStructureStatus('原生结构查找不可用', '需要重建并重启当前镜像');
        renderStructurePlaceholder('当前镜像里还没有原生结构组件，重建镜像后这里会直接显示结构坐标');
      }
    } else if (!isAuthError(d.error)) {
      setSeedState('', presentation('seed.readFailed'), d.error || 'unknown');
      logClient('console.requestFailed', { error: d.error || 'unknown' }, 'warn');
    }
  } catch (e) {
    setSeedState('', presentation('seed.readFailed'), e.message || 'unknown');
    logClient('console.requestFailed', { error: e.message }, 'warn');
  } finally {
    setCardLoading('card-seedmap', false);
    endRefresh('seedmap');
  }
}

async function copyWorldSeed() {
  if (!WORLD_SEED) {
    toast('暂未读取到世界种子');
    return;
  }
  try {
    if (!(await copyText(WORLD_SEED))) throw new Error('copy failed');
    toast('世界种子已复制');
  } catch (e) {
    toast('复制失败，请手动复制');
  }
}

function toggleDynmap() {
  var cb = document.getElementById('dynmap-toggle');
  cb.checked = !cb.checked;
  var frame = document.getElementById('dynmap-frame');
  var btn = document.getElementById('dynmap-full-btn');
  if (cb.checked) {
    frame.src = '/dynmap/';
    frame.style.display = 'block';
    btn.style.display = 'block';
  } else {
    frame.src = '';
    frame.style.display = 'none';
    btn.style.display = 'none';
  }
}

function fullscreenDynmap() {
  var frame = document.getElementById('dynmap-frame');
  if (!document.fullscreenElement) {
    frame.requestFullscreen().catch(function(){});
  } else {
    document.exitFullscreen();
  }
}

async function broadcast() {
  await runDialogCommand({
    kicker: '服务器广播',
    title: '发送公告广播',
    description: '输入要广播给全服玩家的内容。',
    confirmText: '发送广播',
    fields: [
      { name: 'message', label: '广播内容', placeholder: '服务器将在 5 分钟后重启', required: true }
    ],
    buildCommand: function (values) { return 'say ' + values.message; }
  });
}

async function messagePlayer() {
  await runDialogCommand({
    kicker: '玩家消息',
    title: '对某个玩家说话',
    description: '向指定玩家发送私聊消息，不会广播给全服。',
    confirmText: '发送私聊',
    fields: [
      playerField('玩家名', ONLINE_PLAYERS[0] || 'Steve'),
      { name: 'message', label: '消息内容', placeholder: '你好，先回主城一下', required: true }
    ],
    buildCommand: function (values) { return 'tell ' + values.player + ' ' + values.message; }
  });
}

async function stopServer() {
  var confirmed = await showActionDialog({
    kicker: '危险操作',
    title: '关闭服务器',
    description: '确定要发送 stop 命令吗？建议先点击“保存世界”再执行关服。',
    confirmText: '立即关服',
    danger: true,
    fields: [],
    previewText: 'stop'
  });
  if (confirmed) send('stop');
}

async function restartServer() {
  if (PAPER_STATUS.state === 'starting') { toastClient('status.paper.dataWaiting'); return; }
  var confirmed = await showActionDialog({
    kicker: '服务器维护',
    title: '重启 Minecraft 服务',
    description: '这会停止并重新拉起当前 Paper 服务进程，已修改的 server.properties 会在重启后生效。Bungee 和管理面板会继续运行。',
    confirmText: '立即重启',
    danger: true,
    fields: [],
    previewText: 'restart_server'
  });
  if (!confirmed) return;
  setPaperStatus({ state: 'starting', elapsed_seconds: 0 });
  try {
    var d = await systemRequest({ action: 'restart_server' });
    if (d.success) {
      if (d.message) logRaw(d.message, 'out');
      refreshPlugins();
    } else {
      logClient('console.requestFailed', { error: d.error || 'unknown' }, 'err');
      if (d.error) toastRaw(d.error); else toast('服务器重启失败');
    }
  } catch (e) {
    logClient('console.requestFailed', { error: e.message }, 'err');
    toast('服务器重启请求失败');
  } finally {
    refreshPaperStatus();
  }
}

async function toggleRule(name, el) {
  if (el && el.classList.contains('is-pending')) return;
  var cb = el.querySelector('input[type=checkbox]');
  if (!cb) return;
  var target = !cb.checked;
  setTogglePending(el, true);
  try {
    var d = await send('gamerule ' + name + ' ' + (target ? 'true' : 'false'), { skipAutoRefresh: true });
    if (!d || !d.success) return;
    await waitForRuntimeToggleValue('gamerule', name, target, el);
  } finally {
    setTogglePending(el, false);
  }
}

function toggleUnsupported(el, msg) {
  toast(msg || '该项不能通过 RCON 实时切换');
}

async function toggleConfigBool(el, msg) {
  var key = el.getAttribute('data-config-key');
  var cb = el.querySelector('input[type=checkbox]');
  if (!key || !cb || !TOKEN) return;
  cb.checked = !cb.checked;
  try {
    var d = await configRequest({
      action: 'set',
      updates: (function () { var x = {}; x[key] = cb.checked; return x; })()
    });
    if (d.success) {
      CONFIG_CACHE[key] = cb.checked ? 'true' : 'false';
      if (msg) toast(msg); else toastClient('toast.configSaved');
      logClient('console.configUpdated', { key: key, value: CONFIG_CACHE[key] }, 'info');
      if (d.message) logRaw(d.message, 'out');
    } else {
      cb.checked = !cb.checked;
      logClient('console.requestFailed', { error: d.error || 'unknown' }, 'err');
      if (d.error) toastRaw(d.error); else toast('配置更新失败');
    }
  } catch (e) {
    cb.checked = !cb.checked;
    logClient('console.requestFailed', { error: e.message }, 'err');
  }
}

async function saveConfigField(key, inputId, msg) {
  if (!TOKEN) return;
  var input = document.getElementById(inputId);
  if (!input) return;
  var value = input.value.trim();
  if (!value && key !== 'motd') {
    toast('请输入有效值');
    return;
  }
  try {
    var updates = {};
    updates[key] = value;
    var d = await configRequest({ action: 'set', updates: updates });
    if (d.success) {
      CONFIG_CACHE[key] = value;
      if (msg) toast(msg); else toastClient('toast.configSaved');
      logClient('console.configUpdated', { key: key, value: value }, 'info');
      if (d.message) logRaw(d.message, 'out');
    } else {
      logClient('console.requestFailed', { error: d.error || 'unknown' }, 'err');
      if (d.error) toastRaw(d.error); else toast('配置更新失败');
    }
  } catch (e) {
    logClient('console.requestFailed', { error: e.message }, 'err');
  }
}

async function toggleSave(el) {
  if (el && el.classList.contains('is-pending')) return;
  var cb = el.querySelector('input[type=checkbox]');
  if (!cb) return;
  var target = !cb.checked;
  setTogglePending(el, true);
  try {
    var d = await send(target ? 'save-on' : 'save-off', { skipAutoRefresh: true });
    if (!d || !d.success) return;
    await waitForRuntimeToggleValue('save', '', target, el);
  } finally {
    setTogglePending(el, false);
  }
}

async function toggleWL(el) {
  if (el && el.classList.contains('is-pending')) return;
  var cb = el.querySelector('input[type=checkbox]');
  if (!cb) return;
  var target = !cb.checked;
  setTogglePending(el, true);
  try {
    var d = await send(target ? 'whitelist on' : 'whitelist off', { skipAutoRefresh: true });
    if (!d || !d.success) return;
    await waitForRuntimeToggleValue('whitelist', '', target, el);
  } finally {
    setTogglePending(el, false);
  }
}

function buildConnectionInfo(gameUrl, state) {
  var game = new URL(String(gameUrl || ''));
  if (!/^https?:$/.test(game.protocol) || game.username || game.password || game.hash) throw new Error('invalid public game URL');
  var websocket = new URL(game.toString());
  websocket.protocol = game.protocol === 'https:' ? 'wss:' : 'ws:';
  var quickJoin = new URL(game.toString());
  quickJoin.searchParams.set('server', websocket.toString());
  return { state: state, websocketUrl: websocket.toString(), quickJoinUrl: quickJoin.toString() };
}

function inferredGameUrl() {
  var game = new URL(window.location.origin);
  game.protocol = 'http:';
  game.port = '5200';
  game.pathname = '/';
  game.search = '';
  game.hash = '';
  return game.toString();
}

function renderConnectionInfo() {
  var card = document.getElementById('card-connection');
  if (!card) return;
  var info = CONNECTION_INFO;
  var state = CONNECTION_SOURCE_KEYS[info.state] ? info.state : 'unavailable';
  var source = document.getElementById('connection-source');
  var address = document.getElementById('connection-address');
  var open = document.getElementById('connection-open');
  var copy = document.getElementById('connection-copy');
  source.textContent = t(CONNECTION_SOURCE_KEYS[state]);
  source.className = 'connection-source ' + state;
  address.textContent = info.websocketUrl || '--';
  address.title = info.websocketUrl || '';
  var canJoin = !!info.quickJoinUrl && (paperReady() || PAPER_STATUS.state === 'disabled');
  open.classList.toggle('disabled', !canJoin);
  open.setAttribute('aria-disabled', String(!canJoin));
  if (canJoin) open.href = info.quickJoinUrl; else open.removeAttribute('href');
  copy.disabled = !info.websocketUrl;
}

function connectionInfoFromPayload(payload) {
  if (!payload || !payload.success) {
    return { state: payload && payload.code === 'invalid_public_game_url' ? 'invalid' : 'unavailable' };
  }
  if (payload.source === 'configured') {
    try {
      return buildConnectionInfo(payload.game_url, 'configured');
    } catch (error) {
      return { state: 'invalid' };
    }
  }
  if (payload.source === 'inferred') {
    try {
      return buildConnectionInfo(inferredGameUrl(), 'inferred');
    } catch (error) {
      return { state: 'unavailable' };
    }
  }
  return { state: 'unavailable' };
}

async function loadConnectionInfo() {
  CONNECTION_INFO = { state: 'loading' };
  renderConnectionInfo();
  try {
    var response = await fetch(BASE + '/api/connection-info');
    var payload = await response.json();
    CONNECTION_INFO = connectionInfoFromPayload(response.ok ? payload : {
      success: false,
      code: payload && payload.code
    });
  } catch (error) {
    CONNECTION_INFO = { state: 'unavailable' };
  }
  renderConnectionInfo();
}

async function copyConnectionAddress() {
  var value = CONNECTION_INFO.websocketUrl;
  if (!value) return;
  try {
    if (!(await copyText(value))) throw new Error('copy failed');
    toastClient('toast.connectionCopied');
  } catch (error) {
    toastClient('toast.connectionCopyFailed');
  }
}

setupLocalePreference();
init();
