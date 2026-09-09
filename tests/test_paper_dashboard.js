const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function dashboard() {
  const nodes = new Map();
  const storage = new Map();
  const calls = [];
  const fixture = { status: 200, configFailures: 0, calls, storage };
  function element(id) {
    if (!nodes.has(id)) {
      const classes = new Set();
      nodes.set(id, {
        textContent: '', innerHTML: '', value: '', style: {}, appendChild() {},
        classList: {
          add: name => classes.add(name), remove: name => classes.delete(name),
          contains: name => classes.has(name),
          toggle: (name, on) => on ? classes.add(name) : classes.delete(name),
        },
      });
    }
    return nodes.get(id);
  }
  const context = vm.createContext({
    console, Intl, Date, AbortSignal,
    window: { location: { origin: 'http://localhost:5201' }, console },
    document: { hidden: false, getElementById: element, createElement: () => element(Symbol()),
      querySelectorAll: () => [], addEventListener() {} },
    localStorage: { removeItem() {} },
    sessionStorage: { getItem: key => storage.get(key), removeItem: key => storage.delete(key) },
    setTimeout: fn => { queueMicrotask(fn); return 1; }, clearTimeout() {},
    setInterval: () => 1,
    fetch: async (url, options) => {
      const body = options && options.body ? JSON.parse(options.body) : {};
      calls.push([url, body]);
      if (url.endsWith('/api/status')) return {
        status: fixture.status, ok: fixture.status === 200,
        json: async () => ({ minecraft_version: '1.8', rcon_port: 25575, bridge_port: 5201,
          native_seed_finder_ready: true, paper: { state: 'ready', elapsed_seconds: null } }),
      };
      if (url.endsWith('/api/config')) {
        if (fixture.configFailures-- > 0) throw new Error('temporary outage');
        return { json: async () => ({ success: true, config: { motd: 'Saved MOTD' } }) };
      }
      return { json: async () => ({ success: true, response: body.command === 'list'
        ? 'There are 1/20 players online: FixturePlayer' : 'TPS: 20.0, 20.0, 20.0' }) };
    },
  });
  const root = path.join(__dirname, '..', 'web-1.8');
  vm.runInContext(fs.readFileSync(path.join(root, 'admin-i18n.js'), 'utf8'), context);
  context.EaglerXI18n = context.window.EaglerXI18n;
  vm.runInContext(fs.readFileSync(path.join(root, 'admin.js'), 'utf8').replace('setupLocalePreference();\ninit();', ''), context);
  for (const name of ['initNavigation', 'loadConnectionInfo', 'renderConnectionInfo', 'setSeedState',
    'log', 'logClient', 'toastClient', 'openLoginModal', 'refreshPlugins', 'refreshWorldInfo',
    'refreshRuntimeToggles', 'refreshServerVersion', 'refreshSeedMap']) {
    context[name] = async () => { calls.push([name]); };
  }
  fixture.context = context;
  fixture.element = element;
  fixture.evaluate = source => vm.runInContext(source, context);
  return fixture;
}

const settle = () => new Promise(resolve => setImmediate(resolve));
const cases = {
  'world controls reflect measured state and clear during startup'() {
    const app = dashboard();
    const attributes = [{ 'data-weather': 'clear' }, { 'data-world-setting': 'difficulty', 'data-world-value': '2' },
      { 'data-world-setting': 'gamemode', 'data-world-value': '0' }, { 'data-time': '6000' }];
    const buttons = attributes.map(values => ({
      getAttribute: key => values[key], setAttribute: (key, value) => { values[key] = value; },
      removeAttribute: key => { delete values[key]; },
    }));
    app.context.document.querySelectorAll = selector => buttons.filter((button, index) =>
      selector.split(', ').some(part => attributes[index][part.slice(1, -1)] !== undefined));
    app.evaluate("PAPER_STATUS = { state: 'ready' }");
    app.context.renderWorldInfo({ servertime: 30000, hasStorm: false, difficulty: 2, gamemode: 0 });
    assert.equal(attributes[0]['aria-pressed'], 'true');
    assert.equal(attributes[3]['aria-pressed'], 'true');
    assert.equal(buttons[1].value, '2');
    assert.equal(buttons[2].value, '0');
    app.context.setDifficulty = mode => { app.calls.push(['difficulty', mode]); };
    buttons[1].value = '1';
    app.context.setWorldSetting(buttons[1]);
    assert.deepEqual(app.calls.pop(), ['difficulty', 'easy']);
    assert.equal(buttons[1].value, '2');
    buttons[1].value = 'custom';
    app.context.setWorldSetting(buttons[1]);
    assert.deepEqual(app.calls.pop(), ['difficulty', undefined]);
    assert.equal(app.element('control-world-time').textContent, '12:00');
    app.context.renderWorldInfo({ servertime: 6001, hasStorm: true });
    assert.equal(attributes[0]['aria-pressed'], 'false');
    assert.equal(attributes[3]['aria-pressed'], 'false');
    assert.equal(buttons[1].value, '');
    assert.equal(buttons[2].value, '');
    assert.equal(app.context.classifyCommandRefresh('defaultgamemode creative').world, true);
    app.context.setPaperStatus({ state: 'starting', elapsed_seconds: 1 });
    assert.ok(attributes.every(values => values['aria-pressed'] === undefined));
    assert.equal(app.element('control-world-time').textContent, '--:--');
    app.context.setPaperStatus({ state: 'ready' });
    app.context.renderWorldInfo({ servertime: 6000, hasStorm: false, difficulty: 2, gamemode: 0 });
    app.evaluate('TPS_VALUES = [20, 20, 20]');
    app.context.renderPluginInventory = () => {};
    app.context.resetAuthUi();
    assert.ok(attributes.every(values => values['aria-pressed'] === undefined));
    assert.equal(buttons[1].value, '');
    assert.equal(buttons[2].value, '');
    assert.equal(app.evaluate('TPS_VALUES.length'), 0);
  },
  async 'readiness recovery preserves configuration edits'() {
    const app = dashboard();
    app.evaluate("TOKEN = 'stored'; PAPER_STATUS = { state: 'starting', elapsed_seconds: 12 }");
    app.context.finishAuthenticated();
    await settle();
    app.element('cfg-motd').value = 'Unsaved MOTD';
    app.context.setPaperStatus({ state: 'ready' });
    await settle();
    assert.equal(app.element('cfg-motd').value, 'Unsaved MOTD');
    assert.equal(app.calls.filter(([url]) => url.endsWith('/api/config')).length, 1);
    assert.equal(app.calls.filter(([name]) => name === 'refreshPlugins').length, 1);
    assert.equal(app.element('card-config').classList.contains('card-loading'), false);
  },
  async 'status polling retries transient session restoration'() {
    const app = dashboard();
    app.storage.set('eaglerx_admin_token', 'stored');
    app.configFailures = 1;
    app.context.setPaperStatus({ state: 'ready' });
    assert.equal(await app.context.restoreStoredAuth(), true);
    assert.equal(app.evaluate('STATUS_STATE.state'), 'auth');
    await app.context.refreshPaperStatus();
    await settle();
    assert.equal(app.evaluate('STATUS_STATE.state'), 'on');
    assert.equal(app.element('cfg-motd').value, 'Saved MOTD');
    for (const name of ['refreshPlugins', 'refreshSeedMap']) {
      assert.equal(app.calls.filter(([called]) => called === name).length, 1);
    }
    await app.context.refreshPaperStatus();
    assert.equal(app.calls.filter(([name]) => name === 'openLoginModal').length, 0);
    app.evaluate("STATUS_STATE = { state: 'auth' }");
    app.context.fetch = async url => ({ status: 200, ok: true, json: async () =>
      url.endsWith('/api/status') ? { paper: { state: 'ready' } } : { success: false, error: 'token invalid' } });
    await app.context.refreshPaperStatus();
    assert.equal(app.evaluate('TOKEN'), '');
    assert.equal(app.storage.has('eaglerx_admin_token'), false);
    assert.equal(app.calls.filter(([name]) => name === 'openLoginModal').length, 1);
  },
  async 'initial and polled disabled status clear the same metadata'() {
    const initial = dashboard();
    initial.status = 404;
    await initial.context.init();
    const polled = dashboard();
    await polled.context.refreshPaperStatus();
    polled.evaluate("SERVER_INFO.serverVersionText = 'Old Paper'");
    polled.status = 404;
    await polled.context.refreshPaperStatus();
    assert.equal(polled.evaluate('JSON.stringify(SERVER_INFO)'), initial.evaluate('JSON.stringify(SERVER_INFO)'));
    assert.equal(polled.evaluate('PAPER_STATUS.state'), 'disabled');
    assert.equal(initial.calls.filter(([name]) => name === 'openLoginModal').length, 0);
  },
  async 'session restoration serializes probes and honors logout'() {
    const app = dashboard();
    app.storage.set('eaglerx_admin_token', 'stored');
    let complete, probes = 0;
    app.context.fetch = () => { probes++; return new Promise(resolve => { complete = resolve; }); };
    const pending = app.context.restoreStoredAuth();
    assert.equal(await app.context.restoreStoredAuth(), true);
    assert.equal(probes, 1);
    app.context.clearAuthState();
    complete({ json: async () => ({ success: true }) });
    await pending;
    assert.equal(app.evaluate('TOKEN'), '');
    assert.equal(app.evaluate('STATUS_STATE.state'), 'auth');
    assert.equal(app.evaluate('REFRESH_IN_FLIGHT.auth'), false);
    app.evaluate("TOKEN = 'stored'");
    app.storage.set('eaglerx_admin_token_exp', '1');
    assert.equal(await app.context.restoreStoredAuth(), false);
    assert.equal(app.evaluate('TOKEN'), '');
    assert.equal(probes, 1);
  },
  async 'player pixel identifiers are stable and contain only generated geometry'() {
    const app = dashboard();
    assert.equal(app.context.playerAvatar('Alex'), app.context.playerAvatar('alex'));
    assert.notEqual(app.context.playerAvatar('Alex'), app.context.playerAvatar('Steve'));
    assert.match(app.context.playerAvatar('Alex'), /viewBox="0 0 8 8"/);
    assert.doesNotMatch(app.context.playerAvatar('<script>'), /<script>/);
  },
  async 'late player and TPS responses preserve startup placeholders'() {
    for (const [method, id, state] of [['refreshPlayers', 'players', 'ONLINE_PLAYERS'], ['refreshTPS', 'tps-bars', 'TPS_VALUES']]) {
      for (const failed of [false, true]) {
        const app = dashboard();
        app.evaluate("TOKEN = 'stored'; PAPER_STATUS = { state: 'ready' }");
        let complete, reject;
        app.context.fetch = () => new Promise((resolve, fail) => { complete = resolve; reject = fail; });
        const pending = app.context[method]();
        app.context.setPaperStatus({ state: 'starting', elapsed_seconds: 1 });
        const waiting = app.element(id).innerHTML;
        if (failed) reject(new Error('connection reset'));
        else complete({ json: async () => ({ success: true, response: method === 'refreshPlayers'
          ? 'There are 1/20 players online: StalePlayer' : 'TPS: 19.0, 19.0, 19.0' }) });
        await pending;
        assert.equal(app.element(id).innerHTML, waiting, method + ': ' + (failed ? 'failure' : 'success'));
        assert.equal(app.evaluate(state + '.length'), 0);
        assert.equal(app.evaluate('Object.values(REFRESH_IN_FLIGHT).some(Boolean)'), false);
      }
    }
  },
};

(async () => {
  for (const [name, check] of Object.entries(cases)) {
    try {
      await check();
      console.log('PASS ' + name);
    } catch (error) {
      console.error('FAIL ' + name + ': ' + error.stack);
      process.exitCode = 1;
    }
  }
})();
