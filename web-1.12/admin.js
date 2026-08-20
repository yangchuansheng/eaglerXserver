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
let INITIAL_REFRESHING = false;
let SERVER_INFO = { minecraftVersion: '', rconPort: '', bridgePort: '', nativeSeedFinderReady: false, serverVersionText: '' };
let WORLD_INFO_CACHE = null;
let WORLD_SEED = '';
let STRUCTURE_QUERY = { x: 0, z: 0, radius: 5000, limitPerType: 8 };
let LAST_STRUCTURE_RESULT = null;
let LAST_STRUCTURE_CONTEXT = '';
let ONLINE_PLAYERS = [];
let REFRESH_IN_FLIGHT = {};
const REFRESH_INTERVALS = {
  players: 20000,
  tps: 30000,
  world: 30000
};

var LOADING_CARD_IDS = ['card-world','card-players','card-tps','card-rules','card-config','card-whitelist','card-seedmap'];
function setCardLoading(id,on){var el=document.getElementById(id);if(!el)return;if(on){el.classList.add('card-loading');el.style.position='relative'}else{el.classList.remove('card-loading')}}
function setAllCardsLoading(on){for(var i=0;i<LOADING_CARD_IDS.length;i++)setCardLoading(LOADING_CARD_IDS[i],on)}
function beginRefresh(name){if(REFRESH_IN_FLIGHT[name])return false;REFRESH_IN_FLIGHT[name]=true;return true}
function endRefresh(name){REFRESH_IN_FLIGHT[name]=false}
function shouldAutoPoll(){return !document.hidden && !!TOKEN}

function log(msg, cls) {
  const c = document.getElementById('console');
  const div = document.createElement('div');
  const ts = document.createElement('span');
  ts.className = 'ts';
  ts.textContent = new Date().toLocaleTimeString();
  div.appendChild(ts);
  const body = document.createElement('span');
  body.className = cls || 'out';
  body.textContent = msg;
  div.appendChild(body);
  c.appendChild(div);
  c.scrollTop = c.scrollHeight;
}

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._t);
  t._t = setTimeout(function () { t.classList.remove('show'); }, 2000);
}

function setStatus(state, text) {
  var d = document.getElementById('status-dot');
  d.className = state;
  document.getElementById('status-text').textContent = text;
}

function setVersion(v) {
  document.getElementById('ver-tag').textContent = v || '--';
}

async function init() {
  try {
    var r = await fetch(BASE + '/api/status');
    if (!r.ok) throw new Error();
    var d = await r.json();
    SERVER_INFO.minecraftVersion = d.minecraft_version || '';
    SERVER_INFO.rconPort = d.rcon_port || '';
    SERVER_INFO.bridgePort = d.bridge_port || '';
    SERVER_INFO.nativeSeedFinderReady = !!d.native_seed_finder_ready;
    setVersion((SERVER_INFO.minecraftVersion ? 'MC ' + SERVER_INFO.minecraftVersion + ' · ' : '') + (SERVER_INFO.rconPort ? 'RCON:' + SERVER_INFO.rconPort : 'RCON'));
    setSeedState('', defaultSeedHint());
    log('RCON 已启用，管理面板准备就绪', 'info');
    if (!(await restoreStoredAuth())) openLoginModal();
  } catch (e) {
    SERVER_INFO.minecraftVersion = '';
    SERVER_INFO.rconPort = '';
    SERVER_INFO.bridgePort = '';
    SERVER_INFO.nativeSeedFinderReady = false;
    SERVER_INFO.serverVersionText = '';
    setStatus('off', 'RCON 未启用');
    setVersion('RCON 关闭');
    setSeedState('', '启动容器时设置 RCON 后可读取世界种子');
    log('RCON 未启用 —— 启动容器时设置 -e RCON_PASSWORD=xxx 可开启', 'warn');
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

function resetAuthUi() {
  setStatus('auth', '请输入密码');
  ONLINE_PLAYERS = [];
  WORLD_INFO_CACHE = null;
  document.getElementById('player-count').textContent = '0';
  document.getElementById('players').innerHTML = '<div class="empty-state">请先登录后查看玩家列表</div>';
  document.getElementById('tps-bars').innerHTML = '<div class="empty-state">请先登录后查看 TPS</div>';
  setWorldInfoPlaceholder('请先登录后查看世界基础信息');
  setSeedState('', '请先登录后读取世界种子');
  setStructureSource('');
}

function defaultSeedHint() {
  if (!SERVER_INFO.nativeSeedFinderReady) return '登录后自动读取，可一键打开 mcseedmap.net；当前镜像未启用原生结构查找';
  return '登录后自动读取，可一键打开 mcseedmap.net，也可直接查村庄 / 神庙 / 要塞 / 出生点';
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
      linkEl.textContent = '读取种子后可在新标签页打开 mcseedmap.net';
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
      if (player) return '按玩家“' + player + '”当前位置搜索，半径 ' + formatNumber(query.radius) + ' 格';
      return '中心 X ' + formatNumber(query.x) + ' / Z ' + formatNumber(query.z) + '，半径 ' + formatNumber(query.radius) + ' 格';
    }
  });
  if (!values) return;
  var playerName = String(values.player || '').trim();
  if (playerName) {
    setStructureSource('搜索来源：按在线玩家“' + playerName + '”当前位置搜索');
    setStructureStatus('正在读取玩家位置...', '玩家 ' + playerName);
    renderStructurePlaceholder('正在通过 Dynmap 读取玩家“' + escapeHtml(playerName) + '”的实时坐标...');
    try {
      var playerLocation = await fetchDynmapPlayerLocation(playerName);
      var playerSourceText = '搜索来源：玩家“' + playerLocation.name + '”当前位置 · 世界 ' + playerLocation.world + ' · X ' + formatNumber(playerLocation.x) + ' / Z ' + formatNumber(playerLocation.z) + ' · 坐标来源 ' + (playerLocation.source === 'playerdata' ? '玩家存档快照' : 'Dynmap');
      setStructureSource(playerSourceText);
      await refreshStructureFinder({
        x: playerLocation.x,
        z: playerLocation.z,
        radius: values.radius,
        limitPerType: STRUCTURE_QUERY.limitPerType,
        sourceText: playerSourceText
      });
      setStructureStatus('原生结构查找完成', '玩家 ' + playerLocation.name + ' 附近 · 范围 ' + formatNumber(getStructureQuery({ radius: values.radius }).radius) + ' 格');
      return;
    } catch (e) {
      setStructureStatus('玩家定位失败', e.message || 'unknown');
      renderStructurePlaceholder('玩家定位失败：' + (e.message || 'unknown'));
      toast(e.message || '读取玩家位置失败');
      return;
    }
  }
  var coordinateQuery = getStructureQuery(values);
  await refreshStructureFinder({
    x: coordinateQuery.x,
    z: coordinateQuery.z,
    radius: coordinateQuery.radius,
    limitPerType: coordinateQuery.limitPerType,
    sourceText: '搜索来源：按坐标中心 X ' + formatNumber(coordinateQuery.x) + ' / Z ' + formatNumber(coordinateQuery.z)
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
  var valueEl = document.getElementById('seed-value');
  var hintEl = document.getElementById('seed-hint');
  var copyBtn = document.getElementById('seed-copy-btn');
  var openBtn = document.getElementById('seed-open-btn');
  var searchBtn = document.getElementById('seed-search-btn');
  var lastResultBtn = document.getElementById('seed-last-result-btn');
  if (valueEl) valueEl.textContent = WORLD_SEED || '未读取';
  if (hintEl) hintEl.textContent = hint || defaultSeedHint();
  if (copyBtn) copyBtn.disabled = !WORLD_SEED;
  if (openBtn) openBtn.disabled = !WORLD_SEED;
  if (searchBtn) searchBtn.disabled = !WORLD_SEED || !SERVER_INFO.nativeSeedFinderReady;
  updateSeedMapLink();
  if (!WORLD_SEED) {
    LAST_STRUCTURE_RESULT = null;
    setStructureStatus('等待读取世界种子', '');
    setStructureSource('');
    setSpawnCard(null);
    renderStructurePlaceholder('读取种子后可直接在这里查看原生结构坐标');
  }
  if (lastResultBtn) lastResultBtn.disabled = !LAST_STRUCTURE_RESULT;
}

function formatNumber(n) {
  return Number(n || 0).toLocaleString('zh-CN');
}

function setWorldInfoPlaceholder(text) {
  var el = document.getElementById('world-info');
  if (!el) return;
  el.innerHTML = '<div class="empty-state">' + escapeHtml(text || '暂无世界信息') + '</div>';
}

function describeEnabled(value, onText, offText) {
  var enabledText = onText || '开启';
  var disabledText = offText || '关闭';
  if (String(value).toLowerCase() === 'true') return enabledText;
  if (String(value).toLowerCase() === 'false') return disabledText;
  return '--';
}

function formatSpawnProtection(value) {
  if (value === '' || value == null || typeof value === 'undefined') return '--';
  var num = Number(value);
  if (!isFinite(num)) return String(value);
  return num <= 0 ? '关闭' : (formatNumber(num) + ' 格');
}

function getServerVersionDisplay() {
  var text = String(SERVER_INFO.serverVersionText || '').trim();
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
  if (hasWorldInfoPayload(info)) WORLD_INFO_CACHE = info;
  var el = document.getElementById('world-info');
  if (!el) return;
  var world = WORLD_INFO_CACHE;
  if (!world) {
    setWorldInfoPlaceholder('正在读取世界状态...');
    return;
  }
  var weather = world && world.isThundering ? '雷暴' : (world && world.hasStorm ? '下雨' : '晴朗');
  var ticks = Number(world && typeof world.servertime !== 'undefined' ? world.servertime : 0);
  var maxPlayers = CONFIG_CACHE['max-players'] || '--';
  var cards = [
    { label: '世界', value: '主世界' },
    { label: '游戏版本', value: SERVER_INFO.minecraftVersion ? ('MC ' + SERVER_INFO.minecraftVersion) : '--' },
    { label: '在线玩家', value: String(ONLINE_PLAYERS.length) + ' / ' + String(maxPlayers) },
    { label: '天气', value: weather },
    { label: '时间', value: formatMinecraftClock(ticks) },
    { label: '时段', value: describeMinecraftPhase(ticks) },
    { label: '游戏刻', value: formatNumber(ticks) },
    { label: '雷暴', value: world && world.isThundering ? '进行中' : '无' }
  ];
  el.innerHTML = '<div class="world-info-grid">' + cards.map(function (item) {
    return '<div class="world-info-item"><strong>' + escapeHtml(item.label) + '</strong><span>' + escapeHtml(item.value) + '</span></div>';
  }).join('') + '</div>';
}

function rerenderWorldInfo() {
  if (!WORLD_INFO_CACHE) return;
  renderWorldInfo(WORLD_INFO_CACHE);
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
    world: /^(time\b|weather\b)/.test(text),
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
    log('读取运行时状态失败: ' + e.message, 'warn');
  } finally {
    setCardLoading('card-rules', false);
    setCardLoading('card-whitelist', false);
    endRefresh('runtime');
  }
}

async function refreshServerVersion() {
  if (!TOKEN) return;
  try {
    var r = await fetch(BASE + '/api/rcon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildAuthPayload({ command: 'version' }))
    });
    var d = await r.json();
    if (d.success) {
      SERVER_INFO.serverVersionText = String(d.response || '').replace(/\s+/g, ' ').trim();
      rerenderWorldInfo();
    } else if (isAuthError(d.error)) {
      handleAuthFailure(d.error);
    }
  } catch (e) { }
}

function escapeJsSingleQuoted(s) {
  return String(s == null ? '' : s).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function setStructureStatus(text, summary) {
  var status = document.getElementById('seedmap-status');
  var summaryEl = document.getElementById('seedmap-summary');
  if (status) status.textContent = text || '';
  if (summaryEl) summaryEl.textContent = summary || '';
}

function setStructureSource(text) {
  var sourceEl = document.getElementById('seedmap-source');
  LAST_STRUCTURE_CONTEXT = text || '';
  if (!sourceEl) return;
  if (LAST_STRUCTURE_CONTEXT) {
    sourceEl.textContent = LAST_STRUCTURE_CONTEXT;
    sourceEl.classList.remove('hidden');
  } else {
    sourceEl.textContent = '';
    sourceEl.classList.add('hidden');
  }
}

function renderStructurePlaceholder(text) {
  var el = document.getElementById('seedmap-results');
  if (!el) return;
  el.innerHTML = '<div class="empty-state">' + escapeHtml(text || '暂无结果') + '</div>';
}

async function teleportPlayerToPoint(x, z, label) {
  if (!TOKEN) return;
  var pointLabel = String(label || '该点位');
  var values = await showActionDialog({
    kicker: '世界传送',
    title: '传送玩家到此处',
    description: '将玩家安全传送到“' + pointLabel + '”附近的地表。这里不再直接用 tp 到固定 Y，而是用 spreadplayers 让玩家落到附近安全地面，避免卡地下或悬空。',
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
    el.innerHTML = '<div class="empty-state">搜索完成后会显示世界出生点</div>';
    return;
  }
  var note = effectiveSeedKind === 'string-hash'
    ? '当前世界种子是文本，Minecraft 会先做 Java String.hashCode 再参与结构计算。'
    : '以下出生点为 cubiomes 近似计算结果，通常足够用于面板内找结构。';
  var spawnLabel = escapeJsSingleQuoted('世界出生点');
  el.innerHTML = '' +
    '<div class="seedmap-spawn-card">' +
      '<div class="seedmap-spawn-title"><strong>世界出生点</strong><span class="seedmap-spawn-meta">距离当前中心 ' + formatNumber(spawn.distance || 0) + ' 格</span></div>' +
      '<div class="seedmap-spawn-coords">X ' + escapeHtml(spawn.x) + ' / Z ' + escapeHtml(spawn.z) + '</div>' +
      '<div class="seedmap-inline-note"><div class="seedmap-inline-actions"><button class="pill-btn seedmap-mini-btn" type="button" onclick="fillStructureCenter(' + Number(spawn.x || 0) + ', ' + Number(spawn.z || 0) + ', true)">以出生点为中心重新搜索</button><button class="pill-btn seedmap-mini-btn" type="button" onclick="teleportPlayerToPoint(' + Number(spawn.x || 0) + ', ' + Number(spawn.z || 0) + ', \'' + spawnLabel + '\')">传送玩家到此处</button></div></div>' +
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
  setStructureSource(LAST_STRUCTURE_CONTEXT || ('搜索来源：按坐标中心 X ' + formatNumber(data && data.center ? data.center.x : 0) + ' / Z ' + formatNumber(data && data.center ? data.center.z : 0)));
  setStructureStatus('原生结构查找完成', '范围 ' + formatNumber(data.radius) + ' 格 · 共 ' + formatNumber(data.total_matches || 0) + ' 个点位');
  openStructureOverlay();

  var lastResultBtn = document.getElementById('seed-last-result-btn');
  if (lastResultBtn) lastResultBtn.disabled = !LAST_STRUCTURE_RESULT;

  var el = document.getElementById('seedmap-results');
  if (!el) return;
  if (!data || !data.groups || !data.groups.length) {
    el.innerHTML = '<div class="empty-state">当前范围内暂时没找到结构点位，你可以调整中心坐标或搜索半径后重试</div>';
    return;
  }

  el.innerHTML = data.groups.map(function (group) {
    var rows = (group.entries || []).map(function (entry) {
      var teleportLabel = escapeJsSingleQuoted(String(group.label || '该点位'));
      return '' +
        '<div class="seedmap-row">' +
          '<div class="seedmap-coords">X ' + escapeHtml(entry.x) + ' / Z ' + escapeHtml(entry.z) + '</div>' +
          '<div class="seedmap-distance">距离 ' + formatNumber(entry.distance || 0) + ' 格</div>' +
          '<div class="seedmap-row-actions"><button class="pill-btn seedmap-mini-btn" type="button" onclick="fillStructureCenter(' + Number(entry.x || 0) + ', ' + Number(entry.z || 0) + ', true)">以此为中心</button><button class="pill-btn seedmap-mini-btn" type="button" onclick="teleportPlayerToPoint(' + Number(entry.x || 0) + ', ' + Number(entry.z || 0) + ', \'' + teleportLabel + '\')">传送玩家到此处</button></div>' +
        '</div>';
    }).join('');
    return '' +
      '<div class="seedmap-group">' +
        '<div class="seedmap-group-head">' +
          '<strong>' + escapeHtml(group.label) + '</strong>' +
          '<span class="seedmap-group-meta">显示 ' + formatNumber((group.entries || []).length) + ' / ' + formatNumber(group.total_found || 0) + '</span>' +
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
  var sourceText = typeof rawQuery.sourceText === 'string' && rawQuery.sourceText
    ? rawQuery.sourceText
    : '搜索来源：按坐标中心 X ' + formatNumber(query.x) + ' / Z ' + formatNumber(query.z);
  openStructureOverlay();
  setStructureSource(sourceText);
  setStructureStatus('正在计算结构坐标...', '中心 X ' + formatNumber(query.x) + ' / Z ' + formatNumber(query.z));
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
      setStructureStatus('结构查找失败', d.error || 'unknown');
      renderStructurePlaceholder('结构查找失败：' + (d.error || 'unknown'));
      log('结构查找失败: ' + (d.error || 'unknown'), 'warn');
    }
  } catch (e) {
    setStructureStatus('结构查找失败', e.message || 'network error');
    renderStructurePlaceholder('结构查找失败：' + (e.message || 'network error'));
    log('结构查找失败: ' + e.message, 'warn');
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
  if (document.hidden || !TOKEN) return;
  refreshPlayers();
  refreshTPS();
  refreshWorldInfo(false);
  refreshRuntimeToggles();
});

async function runInitialDashboardRefreshes() {
  if (INITIAL_REFRESHING) return;
  INITIAL_REFRESHING = true;
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
    await refreshConfig();
    await sleep(120);
    await refreshSeedMap();
  } finally {
    INITIAL_REFRESHING = false;
  }
}

function finishAuthenticated(message) {
  setStatus('on', '已连接');
  log(message || '认证成功，RCON 已连接', 'info');
  setAllCardsLoading(true);
  startAutoRefresh();
  runInitialDashboardRefreshes();
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
    setStatus('auth', '请输入密码');
    return false;
  }
  TOKEN = storedToken;
  setStatus('auth', '恢复登录中');
  log('检测到浏览器已保存登录态，正在自动恢复连接', 'info');
  try {
    var r = await fetch(BASE + '/api/rcon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildAuthPayload({ command: 'list' }))
    });
    var d = await r.json();
    if (d.success) {
      finishAuthenticated('已从当前浏览器会话恢复登录');
      return true;
    }
  } catch (e) { }
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
  log('登录态已失效：' + (message || '认证失败') + '，请重新输入密码', 'warn');
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
      log('认证失败：' + (result.error || 'unknown'), 'err');
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
    title.textContent = field.label || field.name;
    label.appendChild(title);

    var input = document.createElement('input');
    input.className = 'dialog-input';
    input.type = field.type || 'text';
    input.autocomplete = 'off';
    input.placeholder = field.placeholder || '';
    input.value = typeof field.value === 'undefined' ? '' : String(field.value);
    input.setAttribute('data-field', field.name);
    if (field.required) input.setAttribute('data-required', 'true');
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
      hint.textContent = field.hint;
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
    document.getElementById('action-kicker').textContent = config.kicker || '快捷操作';
    document.getElementById('action-title').textContent = config.title || '输入参数';
    document.getElementById('action-desc').textContent = config.description || '请填写命令参数';
    document.getElementById('action-confirm').textContent = config.confirmText || '确定';
    document.getElementById('action-confirm').classList.toggle('danger-btn', !!config.danger);
    renderActionFields(config.fields || []);
    document.getElementById('action-overlay').classList.remove('hidden');
    updateActionPreview();
    setTimeout(focusFirstActionField, 0);
  });
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
    toast('请填写“' + (missingField.label || missingField.name) + '”');
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
  send(cmd);
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
    var sourceText = info.source === 'playerdata' ? '玩家存档快照' : (info.source === 'dynmap' ? 'Dynmap' : info.source || 'unknown');
    log('玩家坐标 [' + info.name + ']: 世界=' + info.world + ' X=' + info.x + ' Y=' + info.y + ' Z=' + info.z + '（来源：' + sourceText + '）', 'info');
    toast(info.name + ' @ ' + info.x + ', ' + info.y + ', ' + info.z);
  } catch (e) {
    log('读取玩家坐标失败: ' + (e.message || 'unknown'), 'err');
    toast(e.message || '读取玩家坐标失败');
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
  opts = opts || {};
  log('> ' + cmd, 'cmd');
  try {
    var r = await fetch(BASE + '/api/rcon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildAuthPayload({ command: cmd }))
    });
    var d = await r.json();
    if (d.success) {
      log(d.response || '(无输出)', 'out');
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
      log('错误: ' + (d.error || 'unknown'), 'err');
      return d;
    }
  } catch (e) {
    log('请求失败: ' + e.message, 'err');
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

function playerColor(i) {
  var cols = ['#5090f0', '#7c4dff', '#3ecf8e', '#f0a040', '#f05454', '#2dd4bf', '#f472b6', '#82b1ff'];
  return cols[i % cols.length];
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
  try {
    var d = await configRequest({ action: 'get' });
    if (d.success) {
      CONFIG_CACHE = d.config || {};
      syncConfigControls();
      rerenderWorldInfo();
    }
  } catch (e) {
    log('读取 server.properties 失败: ' + e.message, 'warn');
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
    if (d.success) {
      var el = document.getElementById('players');
      var resp = d.response || '';
      var m = resp.match(/(\d+)\/(\d+)/);
      if (m) {
        document.getElementById('player-count').textContent = m[1];
        var namesStr = resp.split(':')[1] || '';
        var names = namesStr.trim() ? namesStr.split(',').map(function (s) { return s.trim(); }) : [];
        ONLINE_PLAYERS = names.slice();
        if (names.length) {
          el.innerHTML = names.map(function (n, i) {
            var safe = escapeHtml(n);
            var initial = escapeHtml(n.charAt(0) || '?');
            return '<div class="player-item"><div class="player-avatar" style="background:' + playerColor(i) + '">' + initial + '</div><span class="player-name">' + safe + '</span></div>';
          }).join('');
        } else {
          el.innerHTML = '<div class="empty-state">暂无在线玩家</div>';
          document.getElementById('player-count').textContent = '0';
          ONLINE_PLAYERS = [];
        }
        rerenderWorldInfo();
      }
    } else if (isAuthError(d.error)) {
      handleAuthFailure(d.error);
    }
  } catch (e) {
    ONLINE_PLAYERS = [];
    document.getElementById('player-count').textContent = '0';
    document.getElementById('players').innerHTML = '<div class="empty-state">读取在线玩家失败</div>';
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
    if (d.success) {
      var el = document.getElementById('tps-bars');
      var resp = d.response || '';
      var tail = resp.split(':').pop() || resp;
      var ms = tail.match(/\*?\d+\.?\d*/g);
      if (ms && ms.length >= 3) {
        var labels = ['1m', '5m', '15m'];
        el.innerHTML = ms.slice(-3).map(function (v, i) {
          v = parseFloat(v.replace('*', ''));
          var pct = Math.min(100, v * 5);
          var cls = v >= 19 ? 'good' : v >= 15 ? 'ok' : 'bad';
          return '<div class="tps-row"><span class="tps-label">' + labels[i] + '</span><div class="tps-track"><div class="tps-fill ' + cls + '" style="width:' + pct + '%"></div></div><span class="tps-val">' + v.toFixed(1) + '</span></div>';
        }).join('');
      }
    } else if (isAuthError(d.error)) {
      handleAuthFailure(d.error);
    }
  } catch (e) {
    document.getElementById('tps-bars').innerHTML = '<div class="empty-state">读取 TPS 失败</div>';
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
    setWorldInfoPlaceholder('读取世界状态失败：' + (e.message || 'unknown'));
  } finally {
    setCardLoading('card-world', false);
    endRefresh('world');
  }
}

async function refreshSeedMap() {
  if (!TOKEN) return;
  if (!beginRefresh('seedmap')) return;
  setSeedState('', '正在读取当前世界种子...');
  try {
    var d = await seedRequest({});
    if (d.success) {
      var sourceText = d.source === 'server.properties' ? 'server.properties' : (d.source === 'rcon' ? 'RCON /seed' : '未知来源');
      LAST_STRUCTURE_RESULT = null;
      setSeedState(d.seed || '', '来源：' + sourceText + ' · ' + defaultSeedHint());
      if (SERVER_INFO.nativeSeedFinderReady) {
        setSpawnCard(null);
        setStructureStatus('可开始搜索', '点击“搜索附近”后会弹出悬浮框');
        renderStructurePlaceholder('点击“搜索附近”后会弹出悬浮框，输入中心坐标和半径即可查询附近结构');
      } else {
        setStructureStatus('原生结构查找不可用', '需要重建并重启当前镜像');
        renderStructurePlaceholder('当前镜像里还没有原生结构组件，重建镜像后这里会直接显示结构坐标');
      }
    } else if (!isAuthError(d.error)) {
      setSeedState('', '读取种子失败：' + (d.error || 'unknown'));
      log('读取世界种子失败: ' + (d.error || 'unknown'), 'warn');
    }
  } catch (e) {
    setSeedState('', '读取种子失败：' + e.message);
    log('读取世界种子失败: ' + e.message, 'warn');
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
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(WORLD_SEED);
    } else {
      var input = document.createElement('textarea');
      input.value = WORLD_SEED;
      input.setAttribute('readonly', 'readonly');
      input.style.position = 'fixed';
      input.style.left = '-9999px';
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
    }
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
  try {
    var d = await systemRequest({ action: 'restart_server' });
    if (d.success) {
      toast(d.message || '服务器正在重启');
      log(d.message || '服务器正在重启，稍后会恢复连接', 'warn');
      setStatus('auth', '重启中');
      setTimeout(refreshPlayers, 12000);
      setTimeout(refreshTPS, 16000);
      setTimeout(refreshSeedMap, 16000);
      setTimeout(function () {
        if (TOKEN) setStatus('on', '已连接');
      }, 18000);
    } else {
      log('服务器重启失败: ' + (d.error || 'unknown'), 'err');
      toast(d.error || '服务器重启失败');
    }
  } catch (e) {
    log('服务器重启请求失败: ' + e.message, 'err');
    toast('服务器重启请求失败');
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
      toast(msg || d.message || '配置已保存，重启后生效');
      log((msg || ('配置已更新: ' + key)) + ' [' + CONFIG_CACHE[key] + ']', 'info');
    } else {
      cb.checked = !cb.checked;
      log('配置更新失败: ' + (d.error || 'unknown'), 'err');
      toast(d.error || '配置更新失败');
    }
  } catch (e) {
    cb.checked = !cb.checked;
    log('配置请求失败: ' + e.message, 'err');
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
      toast(msg || d.message || '配置已保存，重启后生效');
      log((msg || ('配置已更新: ' + key)) + ' [' + value + ']', 'info');
    } else {
      log('配置更新失败: ' + (d.error || 'unknown'), 'err');
      toast(d.error || '配置更新失败');
    }
  } catch (e) {
    log('配置请求失败: ' + e.message, 'err');
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

init();
