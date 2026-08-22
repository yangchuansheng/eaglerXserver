import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import copy
import http.server
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
START_SCRIPT = ROOT / 'script' / 'start_server.sh'
HTTP_SERVER_PATH = ROOT / 'script' / 'http_server.py'

os.environ['RCON_PASSWORD'] = 'test-password'
os.environ['ADMIN_AUTH_SECRET'] = 'test-auth-secret'
spec = importlib.util.spec_from_file_location('eaglerx_http_server', HTTP_SERVER_PATH)
http_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(http_server)


class FakeConnection:
    def __init__(self):
        self.timeout = None

    def gettimeout(self):
        return self.timeout

    def settimeout(self, timeout):
        self.timeout = timeout


class TimeoutStream:
    def read(self, _length):
        raise socket.timeout()


def make_handler(content_length, body=b''):
    handler = http_server.Handler.__new__(http_server.Handler)
    handler.headers = {'Content-Length': content_length}
    handler.rfile = io.BytesIO(body)
    handler.connection = FakeConnection()
    handler.responses = []
    handler._json = lambda code, data, headers=None: handler.responses.append((code, data, headers))
    return handler


class HttpBoundaryTests(unittest.TestCase):
    def test_json_body_validation(self):
        cases = [
            ('-1', b'', 400, 'invalid content length'),
            (str(http_server.MAX_JSON_BODY + 1), b'', 413, 'request body too large'),
            ('1', b'{', 400, 'invalid json'),
            ('2', b'[]', 400, 'json object required'),
        ]
        for content_length, body, status, error in cases:
            with self.subTest(error=error):
                handler = make_handler(content_length, body)
                self.assertIsNone(handler._read_json_body())
                self.assertEqual((status, error), (handler.responses[0][0], handler.responses[0][1]['error']))

        body = b'{"command":"list"}'
        handler = make_handler(str(len(body)), body)
        self.assertEqual({'command': 'list'}, handler._read_json_body())
        self.assertEqual([], handler.responses)

    def test_json_read_timeout_restores_socket_timeout(self):
        handler = make_handler('2')
        handler.connection.timeout = 30
        handler.rfile = TimeoutStream()
        self.assertIsNone(handler._read_json_body())
        self.assertEqual(30, handler.connection.timeout)
        self.assertEqual(408, handler.responses[0][0])


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        with http_server._login_attempts_lock:
            http_server._login_attempts.clear()

    def test_fifth_failure_locks_for_ten_minutes(self):
        client_ip = '127.0.0.10'
        now = 1000
        for _ in range(http_server.LOGIN_MAX_FAILURES - 1):
            self.assertEqual(0, http_server.record_login_failure(client_ip, now))
        self.assertEqual(http_server.LOGIN_LOCKOUT_SECONDS, http_server.record_login_failure(client_ip, now))
        self.assertEqual(599, http_server.login_retry_after(client_ip, now + 1))
        self.assertEqual(0, http_server.login_retry_after(client_ip, now + http_server.LOGIN_LOCKOUT_SECONDS))

    def test_successful_login_clears_failures(self):
        client_ip = '127.0.0.11'
        http_server.record_login_failure(client_ip, 1000)
        handler = make_handler('0')
        handler.client_address = (client_ip, 12345)
        handler._read_json_body = lambda: {'password': http_server.RCON_PASSWORD}
        handler._handle_login()
        self.assertEqual(200, handler.responses[0][0])
        self.assertEqual(0, http_server.login_retry_after(client_ip, 1001))

    def test_empty_password_counts_toward_lockout(self):
        client_ip = '127.0.0.13'
        for _ in range(http_server.LOGIN_MAX_FAILURES):
            handler = make_handler('0')
            handler.client_address = (client_ip, 12345)
            handler._read_json_body = lambda: {'password': ''}
            handler._handle_login()
        self.assertEqual(429, handler.responses[0][0])
        self.assertEqual('too many login attempts', handler.responses[0][1]['error'])

    def test_unicode_password_login(self):
        original_password = http_server.RCON_PASSWORD
        try:
            http_server.RCON_PASSWORD = '管理密码'
            handler = make_handler('0')
            handler.client_address = ('127.0.0.12', 12345)
            handler._read_json_body = lambda: {'password': '管理密码'}
            handler._handle_login()
            self.assertEqual(200, handler.responses[0][0])
        finally:
            http_server.RCON_PASSWORD = original_password

    def test_management_api_accepts_tokens_only(self):
        self.assertEqual(
            (False, 'token required', None),
            http_server.authenticate_request({'password': http_server.RCON_PASSWORD}),
        )
        token, _ = http_server.create_auth_token()
        self.assertEqual((True, None, 'token'), http_server.authenticate_request({'token': token}))

    def test_malformed_signed_token_is_rejected(self):
        header = http_server._b64url_encode(b'{}')
        payload = http_server._b64url_encode(json.dumps({
            'kind': 'admin',
            'exp': 'invalid',
        }).encode('utf-8'))
        signing_input = f'{header}.{payload}'.encode('ascii')
        signature = http_server._b64url_encode(
            hmac.new(http_server.AUTH_SECRET, signing_input, hashlib.sha256).digest()
        )
        self.assertEqual((False, 'token invalid'), http_server.verify_auth_token(f'{header}.{payload}.{signature}'))
        self.assertEqual((False, 'token invalid'), http_server.verify_auth_token('é.a.b'))

    def test_restart_is_rejected_while_locked(self):
        with http_server._restart_lock:
            self.assertFalse(http_server.restart_server_process())

    def test_server_properties_write_uses_lock(self):
        original_path = http_server._server_properties_path
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / 'server.properties'
                path.write_text('pvp=false\n', encoding='utf-8')
                http_server._server_properties_path = lambda: str(path)
                finished = threading.Event()

                def write_config():
                    http_server.write_server_properties({'pvp': 'true'})
                    finished.set()

                with http_server._server_properties_lock:
                    thread = threading.Thread(target=write_config)
                    thread.start()
                    self.assertFalse(finished.wait(0.05))
                thread.join(timeout=1)
                self.assertTrue(finished.is_set())
                self.assertIn('pvp=true\n', path.read_text(encoding='utf-8'))
        finally:
            http_server._server_properties_path = original_path


class StartScriptTests(unittest.TestCase):
    def run_start(self, app_dir, image_dir, version):
        env = os.environ.copy()
        env.update({
            'APP_DIR': str(app_dir),
            'IMAGE_APP_DIR': str(image_dir),
            'MINECRAFT_VERSION': version,
            'RCON_PASSWORD': '',
        })
        return subprocess.run(
            [str(START_SCRIPT)],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
            check=False,
        )

    def test_invalid_version_exits_before_mount_initialization(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_dir = root / 'app'
            image_dir = root / 'image'
            image_dir.mkdir()
            (image_dir / 'payload').write_text('image data', encoding='utf-8')
            result = self.run_start(app_dir, image_dir, '2.0')
            self.assertNotEqual(0, result.returncode)
            self.assertFalse(app_dir.exists())

    def test_nonempty_incomplete_mount_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_dir = root / 'app'
            image_dir = root / 'image'
            app_dir.mkdir()
            image_dir.mkdir()
            marker = app_dir / 'world.dat'
            marker.write_text('keep me', encoding='utf-8')
            (image_dir / 'payload').write_text('image data', encoding='utf-8')
            result = self.run_start(app_dir, image_dir, '1.8')
            self.assertNotEqual(0, result.returncode)
            self.assertEqual('keep me', marker.read_text(encoding='utf-8'))
            self.assertFalse((app_dir / 'payload').exists())

    def test_active_path_regular_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            (app_dir / 'server-1.8').mkdir()
            (app_dir / 'web-1.8').mkdir()
            (app_dir / 'bungee').mkdir()
            (app_dir / 'script').mkdir()
            (app_dir / 'bungee' / 'run.sh').write_text('', encoding='utf-8')
            (app_dir / 'script' / 'http_server.py').write_text('', encoding='utf-8')
            active_path = app_dir / 'web'
            active_path.write_text('keep me', encoding='utf-8')
            result = self.run_start(app_dir, app_dir, '1.8')
            self.assertNotEqual(0, result.returncode)
            self.assertEqual('keep me', active_path.read_text(encoding='utf-8'))


@unittest.skipUnless(shutil.which('tmux'), 'tmux is required')
class TmuxLifecycleTests(unittest.TestCase):
    def test_dead_pane_can_be_detected_and_respawned(self):
        with tempfile.TemporaryDirectory() as socket_dir:
            env = os.environ.copy()
            env['TMUX_TMPDIR'] = socket_dir
            session = f'eaglerx-test-{os.getpid()}'

            def tmux(*args):
                return subprocess.run(
                    ['tmux', *args],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                ).stdout.strip()

            try:
                first_pane = tmux('new-session', '-d', '-P', '-F', '#{pane_id}', '-s', session, '-n', 'services')
                tmux('set-window-option', '-t', first_pane, 'remain-on-exit', 'on')
                second_pane = tmux('split-window', '-d', '-h', '-P', '-F', '#{pane_id}', '-t', first_pane, 'sleep 30')
                self.assertNotEqual(first_pane, second_pane)
                tmux('respawn-pane', '-k', '-t', first_pane, 'exit 7')
                deadline = time.time() + 3
                while tmux('display-message', '-p', '-t', first_pane, '#{pane_dead}') != '1':
                    self.assertLess(time.time(), deadline)
                    time.sleep(0.05)
                tmux('respawn-pane', '-k', '-t', first_pane, 'sleep 30')
                self.assertEqual('0', tmux('display-message', '-p', '-t', first_pane, '#{pane_dead}'))
            finally:
                subprocess.run(['tmux', 'kill-session', '-t', session], env=env, check=False)


class StartupOrderingTests(unittest.TestCase):
    def test_paper_starts_after_bungee_readiness_check(self):
        source = START_SCRIPT.read_text(encoding='utf-8')
        readiness = re.search(r'(?m)^\s*if ! wait_for_port 127\.0\.0\.1 5200 60; then$', source)
        paper_start = re.search(r'(?m)^\s*SERVER_PANE="\$\(tmux split-window', source)
        self.assertIsNotNone(readiness)
        self.assertIsNotNone(paper_start)
        self.assertLess(readiness.start(), paper_start.start())


class StaticShellLocaleTests(unittest.TestCase):
    HTML_PATH = ROOT / 'web-1.8' / 'admin.html'
    JS_PATH = ROOT / 'web-1.8' / 'admin.js'
    CSS_PATH = ROOT / 'web-1.8' / 'admin.css'
    ASSETS = ('admin.html', 'admin.js', 'admin.css', 'admin-i18n.js', 'admin-i18n-inventory.json')

    def test_english_first_paint_and_script_order(self):
        html = self.HTML_PATH.read_text(encoding='utf-8')
        self.assertIn('<html lang="en">', html)
        self.assertIn('<title data-i18n="document.surface.adminhtml.l6.c21">EaglercraftX Admin Console</title>', html)
        self.assertIn('<label for="locale-select" data-i18n="header.localeLabel">Language</label>', html)
        self.assertRegex(html, r'<select id="locale-select" name="locale"[^>]*>.*value="en".*value="zh-CN"')
        self.assertLess(html.index('admin-i18n.js'), html.index('admin.js?v='))

    def test_locale_lifecycle_is_guarded_and_dom_only(self):
        source = self.JS_PATH.read_text(encoding='utf-8')
        self.assertIn('EaglerXI18n.PREFERENCE_KEY', source)
        self.assertIn("['data-i18n', 'textContent']", source)
        self.assertIn("['data-i18n-title', 'title']", source)
        self.assertIn("['data-i18n-placeholder', 'placeholder']", source)
        self.assertIn("['data-i18n-aria-label', 'aria-label']", source)
        handler = re.search(r"selector\.addEventListener\('change', function \(\) \{([\s\S]*?)\n  \}\);", source)
        self.assertIsNotNone(handler)
        self.assertNotRegex(handler.group(1), r'\b(init|fetch|send|setInterval|setTimeout)\s*\(')
        self.assertLess(source.rindex('setupLocalePreference();'), source.rindex('init();'))

    def test_locale_recovery_and_current_session_write_failure(self):
        script = """
const fs = require('fs');
const vm = require('vm');
function run(stored, throwOnWrite) {
  const listeners = {};
  const selector = { value: '', textContent: '', options: [], appendChild: function(option) { this.options.push(option); }, addEventListener: function(name, callback) { listeners[name] = callback; } };
  const storage = { value: stored, removed: false, getItem: function() { return this.value; }, removeItem: function() { this.removed = true; this.value = null; }, setItem: function(_, value) { if (throwOnWrite) throw new Error('blocked'); this.value = value; } };
  const document = { documentElement: {}, title: '', getElementById: function(id) { return id === 'locale-select' ? selector : null; }, querySelector: function() { return null; }, querySelectorAll: function() { return []; }, createElement: function() { return {}; }, addEventListener: function() {} };
  const window = { console: { warn: function() {} }, location: { origin: 'http://localhost:5201' } };
  const context = { window, document, localStorage: storage, console };
  vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
  context.EaglerXI18n = window.EaglerXI18n;
  const source = fs.readFileSync(process.argv[2], 'utf8').replace('setupLocalePreference();\\ninit();', 'rerenderLocalizedState = function() {}; setupLocalePreference();');
  vm.runInNewContext(source, context);
  const initialLang = document.documentElement.lang;
  selector.value = 'zh-CN'; listeners.change();
  return { selected: selector.value, initialLang: initialLang, lang: document.documentElement.lang, stored: storage.value, removed: storage.removed, labels: selector.options.map(function(option) { return [option.value, option.textContent]; }) };
}
console.log(JSON.stringify({ valid: run('zh-CN', false), invalid: run('stale', false), blocked: run(null, true) }));
"""
        result = subprocess.run(
            ['node', '-e', script, str(ROOT / 'web-1.8' / 'admin-i18n.js'), str(self.JS_PATH)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        data = json.loads(result.stdout)
        self.assertEqual('zh-CN', data['valid']['lang'])
        self.assertEqual('en', data['invalid']['initialLang'])
        self.assertTrue(data['invalid']['removed'])
        self.assertEqual('zh-CN', data['blocked']['lang'])
        self.assertEqual([['en', 'English'], ['zh-CN', '简体中文']], data['valid']['labels'])

    def test_selector_responsive_dimensions_and_mirrors(self):
        css = self.CSS_PATH.read_text(encoding='utf-8')
        self.assertRegex(css, r'#locale-select\s*\{[^}]*height:\s*38px')
        mobile = re.search(r'@media \(max-width: 520px\) \{([\s\S]*)', css)
        self.assertIsNotNone(mobile)
        self.assertRegex(mobile.group(1), r'#locale-select\s*\{[^}]*height:\s*44px')
        for asset in self.ASSETS:
            self.assertEqual((ROOT / 'web-1.8' / asset).read_bytes(), (ROOT / 'web-1.12' / asset).read_bytes())

    def test_static_binding_contract_has_exact_sources_and_bilingual_keys(self):
        inventory = json.loads((ROOT / 'web-1.8' / 'admin-i18n-inventory.json').read_text(encoding='utf-8'))
        contract = inventory['staticBindingContract']
        html_lines = self.HTML_PATH.read_text(encoding='utf-8').splitlines()
        script = """
const fs = require('fs'); const vm = require('vm'); const window = { console: { warn: function() {} } };
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), { window: window });
console.log(JSON.stringify({ en: window.EaglerXI18n.locales.en.messages, zh: window.EaglerXI18n.locales['zh-CN'].messages }));
"""
        result = subprocess.run(['node', '-e', script, str(ROOT / 'web-1.8' / 'admin-i18n.js')], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        catalogs = json.loads(result.stdout)
        self.assertEqual({'data-i18n', 'data-i18n-title', 'data-i18n-placeholder', 'data-i18n-aria-label'}, {binding[1] for binding in contract['bindings']})
        binding_count = len(re.findall(r'data-i18n(?:-(?:title|placeholder|aria-label))?="[^"]+"', self.HTML_PATH.read_text(encoding='utf-8')))
        self.assertEqual(len(contract['bindings']), binding_count)
        for key, attribute, line, column, literal in contract['bindings']:
            with self.subTest(key=key, line=line):
                line_text = html_lines[line - 1]
                self.assertEqual(contract['bindingLines'][str(line)], line_text)
                self.assertTrue(literal)
                self.assertEqual(literal, line_text[column - 1:column - 1 + len(literal)])
                self.assertIn(f'{attribute}="{key}"', line_text)
                self.assertIn(key, catalogs['en'])
                self.assertIn(key, catalogs['zh'])


class I18nInventoryTests(unittest.TestCase):
    INVENTORY_PATHS = [
        ROOT / 'web-1.8' / 'admin-i18n-inventory.json',
        ROOT / 'web-1.12' / 'admin-i18n-inventory.json',
    ]
    ADMIN_ASSETS = ('admin.html', 'admin.js', 'admin.css')
    SOURCE_FILES = ('admin.js',)
    SURFACE_FIELDS = {'id', 'source', 'messageKey', 'kind', 'classification'}
    SOURCE_FIELDS = {'file', 'line', 'column', 'literal', 'lineText'}
    ALLOWED_KINDS = {'text', 'attribute', 'renderer', 'dialog', 'toast', 'log', 'state', 'client-prefix'}
    ALLOWED_CLASSIFICATIONS = {'presentation', 'operational'}

    def load_inventory(self):
        return json.loads(self.INVENTORY_PATHS[0].read_text(encoding='utf-8'))

    def extract_source_tuples(self):
        return {
            (filename, line_number, match.start() + 1, match.group(), line_text)
            for filename in self.SOURCE_FILES
            for line_number, line_text in enumerate(
                (ROOT / 'web-1.8' / filename).read_text(encoding='utf-8').splitlines(),
                1,
            )
            for match in re.finditer(r'[\u4e00-\u9fff]+', line_text)
        }

    @classmethod
    def surface_tuple(cls, surface):
        source = surface['source']
        return (
            source['file'],
            source['line'],
            source['column'],
            source['literal'],
            source['lineText'],
        )

    def assert_source_surface_contract(self, inventory):
        self.assertNotIn('sourceCoverage', inventory)
        self.assertEqual({'version', 'scope', 'dynamicBindingContract', 'staticBindingContract', 'surfaces', 'messages'}, set(inventory))
        self.assertEqual(4, inventory['version'])
        self.assertIsInstance(inventory['surfaces'], list)
        self.assertIsInstance(inventory['messages'], dict)

        surfaces = inventory['surfaces']
        surface_tuples = set()
        surface_ids = set()
        presentation_keys = []
        js_surface_count = 0
        for surface in surfaces:
            self.assertEqual(self.SURFACE_FIELDS, set(surface))
            self.assertEqual(self.SOURCE_FIELDS, set(surface['source']))
            self.assertIn(surface['kind'], self.ALLOWED_KINDS)
            self.assertIn(surface['classification'], self.ALLOWED_CLASSIFICATIONS)
            self.assertTrue(surface['id'])
            self.assertTrue(surface['messageKey'])
            self.assertNotIn(surface['id'], surface_ids)
            surface_ids.add(surface['id'])

            source = surface['source']
            if source['file'] != 'admin.js':
                continue
            js_surface_count += 1
            self.assertIn(source['literal'], source['lineText'])
            source_tuple = self.surface_tuple(surface)
            self.assertNotIn(source_tuple, surface_tuples)
            surface_tuples.add(source_tuple)
            message = inventory['messages'].get(surface['messageKey'])
            self.assertIsNotNone(message)
            self.assertEqual(surface['kind'], message['kind'])
            self.assertEqual(surface['classification'], message['classification'])
            if surface['classification'] == 'presentation':
                presentation_keys.append(surface['messageKey'])

        self.assertEqual(625, js_surface_count)

        inventory_presentation_keys = {
            key for key, message in inventory['messages'].items()
            if message['classification'] == 'presentation'
        }
        self.assertTrue(set(presentation_keys).issubset(inventory_presentation_keys))

    def test_inventory_is_mirrored_and_valid_json(self):
        self.assertEqual(
            self.INVENTORY_PATHS[0].read_bytes(),
            self.INVENTORY_PATHS[1].read_bytes(),
        )
        self.assertIn('surfaces', self.load_inventory())

    def test_message_schema_and_source_locators(self):
        inventory = self.load_inventory()
        for key, message in inventory['messages'].items():
            with self.subTest(key=key):
                self.assertRegex(key, r'^(document|accessibility|header|nav|hero|section|card|action|option|dialog|field|validation|status|toast|console|world|operational)\.')
                self.assertIn(message['kind'], self.ALLOWED_KINDS)
                self.assertIn(message['classification'], self.ALLOWED_CLASSIFICATIONS)
                source = message['source']
                self.assertIn(source['file'], {'admin.html', 'admin.js', 'admin.css'})
                if message['classification'] == 'operational':
                    self.assertEqual({'file', 'locator'}, set(source))
                    content = (ROOT / 'web-1.8' / source['file']).read_text(encoding='utf-8')
                    self.assertIn(source['locator'], content)
                else:
                    self.assertEqual(self.SOURCE_FIELDS, set(source))

    def test_client_authored_source_coverage_is_regressible(self):
        self.assert_source_surface_contract(self.load_inventory())

    def test_source_surface_contract_rejects_missing_duplicate_and_corrupt_mappings(self):
        inventory = self.load_inventory()
        cases = []

        js_index = next(index for index, surface in enumerate(inventory['surfaces']) if surface['source']['file'] == 'admin.js')
        missing = copy.deepcopy(inventory)
        missing['surfaces'].pop(js_index)
        cases.append(('missing', missing))

        duplicate = copy.deepcopy(inventory)
        duplicate['surfaces'].append(copy.deepcopy(duplicate['surfaces'][0]))
        cases.append(('duplicate', duplicate))

        for field, value in (('literal', '损坏'),):
            corrupt = copy.deepcopy(inventory)
            corrupt['surfaces'][js_index]['source'][field] = value
            cases.append((field, corrupt))

        for field, value in (('messageKey', 'document.missing'), ('kind', 'log'), ('classification', 'operational')):
            corrupt = copy.deepcopy(inventory)
            corrupt['surfaces'][js_index][field] = value
            cases.append((field, corrupt))

        for name, corrupt in cases:
            with self.subTest(name=name):
                with self.assertRaises(AssertionError):
                    self.assert_source_surface_contract(corrupt)

    def test_admin_assets_remain_mirrored(self):
        for asset in self.ADMIN_ASSETS:
            with self.subTest(asset=asset):
                self.assertEqual(
                    (ROOT / 'web-1.8' / asset).read_bytes(),
                    (ROOT / 'web-1.12' / asset).read_bytes(),
                )

    def test_operational_boundaries_keep_raw_values_and_safe_sinks(self):
        source = (ROOT / 'web-1.8' / 'admin.js').read_text(encoding='utf-8')
        self.assertRegex(source, r"async function setDifficulty\(mode, label\)[\s\S]+?send\('difficulty ' \+ mode\)")
        self.assertRegex(source, r"async function setPlayerGamemode\(mode, label\)[\s\S]+?return 'gamemode ' \+ mode \+ ' ' \+ values\.player")
        self.assertIn('function logRaw(payload, cls)', source)
        self.assertIn("body.textContent = entry.kind === 'raw' ? entry.payload", source)
        self.assertIn("SERVER_INFO.serverVersionText = String(d.response || '')", source)
        self.assertIn('function escapeHtml(s)', source)
        self.assertIn("String(s).replace(/[&<>'\"]", source)


class DynamicLocaleRendererTests(unittest.TestCase):
    ASSETS = ('admin.html', 'admin.js', 'admin.css', 'admin-i18n.js', 'admin-i18n-inventory.json')

    def test_dynamic_contract_catalogs_and_mirrors(self):
        inventory = json.loads((ROOT / 'web-1.8' / 'admin-i18n-inventory.json').read_text(encoding='utf-8'))
        contract = inventory['dynamicBindingContract']
        source = (ROOT / 'web-1.8' / 'admin.js').read_text(encoding='utf-8')
        self.assertEqual(1, contract['version'])
        for name in contract['renderers'] + contract['descriptors'] + contract['formatters'] + contract['rawSinks']:
            with self.subTest(name=name):
                self.assertIn(name, source)
        script = """
const fs = require('fs'); const vm = require('vm'); const window = { console: { warn: function() {} } };
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), { window: window });
console.log(JSON.stringify(window.EaglerXI18n.locales));
"""
        result = subprocess.run(['node', '-e', script, str(ROOT / 'web-1.8' / 'admin-i18n.js')], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        catalogs = json.loads(result.stdout)
        for key in contract['keys']:
            self.assertTrue(catalogs['en']['messages'][key].strip())
            self.assertTrue(catalogs['zh-CN']['messages'][key].strip())
        for asset in self.ASSETS:
            self.assertEqual((ROOT / 'web-1.8' / asset).read_bytes(), (ROOT / 'web-1.12' / asset).read_bytes())

    def test_cache_only_rerender_and_raw_payload_identity(self):
        source = (ROOT / 'web-1.8' / 'admin.js').read_text(encoding='utf-8')
        rerender = re.search(r'function rerenderLocalizedState\(\) \{([\s\S]*?)\n\}', source)
        self.assertIsNotNone(rerender)
        self.assertNotRegex(rerender.group(1), r'\b(fetch|send|init|setInterval|setTimeout|queueWorldInfoRefresh|queueRuntimeRefresh|startAutoRefresh|runInitialDashboardRefreshes)\s*\(')
        self.assertIn('rerenderLocalizedState();', source)
        self.assertIn('Intl.NumberFormat(EaglerXI18n.getLocale()', source)
        self.assertIn('Intl.DateTimeFormat(EaglerXI18n.getLocale()', source)
        self.assertIn("hourCycle: 'h23'", source)
        self.assertIn('captureActionDialogSnapshot', source)
        self.assertIn('restoreActionDialogSnapshot', source)
        self.assertIn('selectedIndex: input.selectedIndex', source)
        self.assertIn('input.required = saved.required', source)
        self.assertIn('input.min = saved.min', source)
        self.assertIn('input.max = saved.max', source)
        self.assertIn('focused.setSelectionRange', source)
        self.assertIn('ACTIVE_TOAST.deadline', source)
        self.assertIn('entry.payload', source)
        self.assertIn('SEED_STATE', source)
        self.assertIn('STRUCTURE_STATUS_STATE', source)
        self.assertIn('renderSeedState();', rerender.group(1))
        self.assertIn('renderStructureStatus();', rerender.group(1))
        self.assertIn('renderStructureSource();', rerender.group(1))
        self.assertNotIn("logRaw(d.response || t('console.emptyOutput')", source)
        self.assertIn("if (d.response) logRaw(d.response, 'out');", source)
        self.assertIn("else logClient('console.emptyOutput', {}, 'out');", source)

    def test_node_vm_keeps_raw_console_bytes(self):
        script = """
const fs = require('fs'); const vm = require('vm');
function node() { return { children: [], classList: { add: function(){}, remove: function(){} }, appendChild: function(child) { this.children.push(child); }, textContent: '', scrollTop: 0, scrollHeight: 0, clientHeight: 0 }; }
const consoleNode = node();
const document = { hidden: false, documentElement: {}, title: '', getElementById: function(id) { return id === 'console' ? consoleNode : node(); }, querySelector: function() { return null; }, querySelectorAll: function() { return []; }, createElement: node, addEventListener: function() {} };
const window = { location: { origin: 'http://localhost:5201' }, console: { warn: function() {} } };
const context = { window: window, document: document, localStorage: { getItem: function(){ return null; }, setItem: function(){}, removeItem: function(){} }, setTimeout: function(){ return 1; }, clearTimeout: function(){}, setInterval: function(){ return 1; }, clearInterval: function(){}, Intl: Intl, Date: Date, console: console };
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
context.EaglerXI18n = window.EaglerXI18n;
let source = fs.readFileSync(process.argv[2], 'utf8');
source = source.replace('setupLocalePreference();\\ninit();', "EaglerXI18n.setLocale('en'); logRaw('  <tag>' + String.fromCharCode(10) + 'raw ✓  ', 'out'); console.log(JSON.stringify({ payload: CONSOLE_HISTORY[0].payload, locale: EaglerXI18n.getLocale(), clock: formatMinecraftClock(18000) }));");
vm.runInNewContext(source, context);
"""
        result = subprocess.run(['node', '-e', script, str(ROOT / 'web-1.8' / 'admin-i18n.js'), str(ROOT / 'web-1.8' / 'admin.js')], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        data = json.loads(result.stdout)
        self.assertEqual('  <tag>\nraw ✓  ', data['payload'])
        self.assertEqual('en', data['locale'])
        self.assertEqual('00:00', data['clock'])


class I18nRuntimeTests(unittest.TestCase):
    RUNTIME_PATHS = [
        ROOT / 'web-1.8' / 'admin-i18n.js',
        ROOT / 'web-1.12' / 'admin-i18n.js',
    ]
    INVENTORY_PATH = ROOT / 'web-1.8' / 'admin-i18n-inventory.json'

    def run_runtime(self, body):
        script = """
const fs = require('fs');
const vm = require('vm');
const warnings = [];
const window = { console: { warn: function (message) { warnings.push(message); } } };
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), { window: window });
const i18n = window.EaglerXI18n;
%s
""" % body
        result = subprocess.run(
            ['node', '-e', script, str(self.RUNTIME_PATHS[0])],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return json.loads(result.stdout)

    def assert_catalog_contract(self, inventory, catalogs):
        presentation_keys = [
            surface['messageKey'] for surface in inventory['surfaces']
            if surface['classification'] == 'presentation'
        ]
        expected = (
            set(presentation_keys)
            | {binding[0] for binding in inventory['staticBindingContract']['bindings']}
            | set(inventory['dynamicBindingContract']['keys'])
        )
        self.assertTrue(set(presentation_keys).issubset({
            key for key, message in inventory['messages'].items()
            if message['classification'] == 'presentation'
        }))
        for locale_id in ('en', 'zh-CN'):
            catalog = catalogs[locale_id]
            self.assertEqual(expected, set(catalog))
            for key, value in catalog.items():
                self.assertIsInstance(value, str)
                self.assertTrue(value.strip(), key)
        self.assertEqual(set(catalogs['en']), set(catalogs['zh-CN']))
        for key, message in inventory['messages'].items():
            if message['classification'] == 'operational':
                self.assertNotIn(key, catalogs['en'])
                self.assertNotIn(key, catalogs['zh-CN'])

    def test_registry_metadata_catalog_coverage_and_parity(self):
        inventory = json.loads(self.INVENTORY_PATH.read_text(encoding='utf-8'))
        result = self.run_runtime("""
console.log(JSON.stringify({
  defaults: [i18n.DEFAULT_LOCALE, i18n.FALLBACK_LOCALE, i18n.PREFERENCE_KEY],
  locales: Object.keys(i18n.locales),
  labels: [i18n.locales.en.label, i18n.locales['zh-CN'].label],
  catalogs: {
    en: i18n.locales.en.messages,
    'zh-CN': i18n.locales['zh-CN'].messages
  }
}));
""")
        self.assertEqual(['en', 'en', 'eaglerx_admin_locale'], result['defaults'])
        self.assertEqual(['en', 'zh-CN'], result['locales'])
        self.assertEqual(['English', '简体中文'], result['labels'])
        self.assert_catalog_contract(inventory, result['catalogs'])
        self.assertEqual(self.RUNTIME_PATHS[0].read_bytes(), self.RUNTIME_PATHS[1].read_bytes())

    def test_catalog_contract_rejects_missing_extra_and_operational_keys(self):
        inventory = json.loads(self.INVENTORY_PATH.read_text(encoding='utf-8'))
        catalogs = self.run_runtime("""
console.log(JSON.stringify({
  en: i18n.locales.en.messages,
  'zh-CN': i18n.locales['zh-CN'].messages
}));
""")
        presentation_key = inventory['surfaces'][0]['messageKey']
        operational_key = next(
            key for key, message in inventory['messages'].items()
            if message['classification'] == 'operational'
        )

        missing = copy.deepcopy(catalogs)
        missing['en'].pop(presentation_key)
        extra = copy.deepcopy(catalogs)
        extra['en']['document.unmapped'] = 'Unmapped'
        operational = copy.deepcopy(catalogs)
        operational['zh-CN'][operational_key] = '操作值'

        for name, corrupt in (('missing', missing), ('extra', extra), ('operational', operational)):
            with self.subTest(name=name):
                with self.assertRaises(AssertionError):
                    self.assert_catalog_contract(inventory, corrupt)

    def test_fallback_missing_diagnostic_and_plain_text_interpolation(self):
        result = self.run_runtime("""
i18n.setLocale('zh-CN');
delete i18n.locales['zh-CN'].messages['header.title'];
const fallback = i18n.t('header.title');
const interpolation = i18n.t('validation.requiredField', { name: '<strong>Alex</strong>' });
const first = i18n.t('missing.key');
const second = i18n.t('missing.key');
const selected = i18n.setLocale('invalid-locale');
console.log(JSON.stringify({ fallback: fallback, interpolation: interpolation, first: first, second: second, selected: selected, warnings: warnings }));
""")
        self.assertEqual('EaglercraftX Admin Console', result['fallback'])
        self.assertEqual('请填写“<strong>Alex</strong>”。', result['interpolation'])
        self.assertEqual('[[missing:missing.key]]', result['first'])
        self.assertEqual(result['first'], result['second'])
        self.assertEqual('en', result['selected'])
        self.assertEqual(['[EaglerX i18n] missing key: missing.key'], result['warnings'])

    def test_stable_keys_render_composites_without_han(self):
        result = self.run_runtime("""
i18n.setLocale('en');
const samples = [
  i18n.t('console.rconDisabled'),
  i18n.t('structure.sourcePlayerLocation', { player: 'FixtureAlex', world: 'fixture-world', x: '12.5', z: '-8.25', source: 'Dynmap' }),
  i18n.t('structure.coordinatesSummary', { x: '0', z: '0' }),
  i18n.t('console.playerCoordinates', { player: 'FixtureAlex', world: 'fixture-world', x: '12', y: '64', z: '-8', source: 'player data snapshot' }),
  i18n.t('structure.type.village'),
  i18n.t('structure.sourcePlayerdata'),
  i18n.t('toast.commandSubmitted')
];
console.log(JSON.stringify(samples));
""")
        self.assertEqual([
            'RCON is disabled. Start the container with -e RCON_PASSWORD=xxx to enable it.',
            'Search source: player “FixtureAlex” · world fixture-world · X 12.5 / Z -8.25 · coordinate source Dynmap',
            'Center X 0 / Z 0',
            'Player coordinates [FixtureAlex]: world=fixture-world X=12 Y=64 Z=-8 (source: player data snapshot)',
            'Village',
            'player data snapshot',
            'Command submitted.',
        ], result)
        self.assertTrue(all(not re.search(r'[\u4e00-\u9fff]', value) for value in result))


class ReleaseContractTests(unittest.TestCase):
    ROOTS = (ROOT / 'web-1.8', ROOT / 'web-1.12')
    RELEASE_ASSETS = ('admin.html', 'admin.js', 'admin.css', 'admin-i18n.js', 'admin-i18n-inventory.json')

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def runtime(root):
        script = """
const fs = require('fs');
const vm = require('vm');
const warnings = [];
const window = { console: { warn: function(message) { warnings.push(message); } } };
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), { window: window });
const i18n = window.EaglerXI18n;
const catalogs = {
  en: Object.assign({}, i18n.locales.en.messages),
  'zh-CN': Object.assign({}, i18n.locales['zh-CN'].messages)
};
i18n.setLocale('zh-CN');
delete i18n.locales['zh-CN'].messages['header.title'];
const fallback = i18n.t('header.title');
const interpolation = i18n.t('validation.requiredField', { name: '<strong>FixtureAlex</strong>' });
const missing = i18n.t('release.contract.unknown');
const selected = i18n.setLocale('zh-CN');
const current = i18n.getLocale();
console.log(JSON.stringify({
  defaults: [i18n.DEFAULT_LOCALE, i18n.FALLBACK_LOCALE, i18n.PREFERENCE_KEY],
  catalogs: catalogs,
  ids: Object.keys(i18n.locales),
  labels: [i18n.locales.en.label, i18n.locales['zh-CN'].label],
  fallback: fallback,
  interpolation: interpolation,
  missing: missing,
  selected: selected,
  current: current,
  warnings: warnings
}));
"""
        result = subprocess.run(
            ['node', '-e', script, str(root / 'admin-i18n.js')],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return json.loads(result.stdout)

    def test_release_assets_are_exact_mirrors_with_sha256_evidence(self):
        canonical, mirror = self.ROOTS
        for asset in self.RELEASE_ASSETS:
            with self.subTest(asset=asset):
                canonical_path = canonical / asset
                mirror_path = mirror / asset
                self.assertEqual(
                    canonical_path.read_bytes(),
                    mirror_path.read_bytes(),
                    f'{asset}: web-1.8 sha256={self.digest(canonical_path)} '
                    f'web-1.12 sha256={self.digest(mirror_path)}',
                )

    def test_full_bilingual_locale_catalog_inventory_and_runtime_contract(self):
        for root in self.ROOTS:
            with self.subTest(root=root.name):
                inventory = json.loads((root / 'admin-i18n-inventory.json').read_text(encoding='utf-8'))
                runtime = self.runtime(root)
                catalogs = runtime['catalogs']
                static_keys = {binding[0] for binding in inventory['staticBindingContract']['bindings']}
                dynamic_keys = set(inventory['dynamicBindingContract']['keys'])
                source = (root / 'admin.js').read_text(encoding='utf-8')
                runtime_keys = set(re.findall(
                    r"['\"]((?:hero|status|console|dialog|validation|toast|seed|structure)\.[A-Za-z0-9_.-]+)['\"]",
                    source,
                ))
                inventory_keys = {
                    key for key, message in inventory['messages'].items()
                    if message['classification'] == 'presentation'
                }
                referenced_keys = static_keys | dynamic_keys | inventory_keys

                self.assertEqual(runtime_keys, dynamic_keys, root.name)
                self.assertEqual(referenced_keys, set(catalogs['en']), root.name)
                self.assertEqual(referenced_keys, set(catalogs['zh-CN']), root.name)

                self.assertEqual(['en', 'en', 'eaglerx_admin_locale'], runtime['defaults'], root.name)
                self.assertEqual(['en', 'zh-CN'], runtime['ids'], root.name)
                self.assertEqual(['English', '简体中文'], runtime['labels'], root.name)
                self.assertEqual('EaglercraftX Admin Console', runtime['fallback'], root.name)
                self.assertEqual('[[missing:release.contract.unknown]]', runtime['missing'], root.name)
                self.assertEqual('请填写“<strong>FixtureAlex</strong>”。', runtime['interpolation'], root.name)
                self.assertEqual(('zh-CN', 'zh-CN'), (runtime['selected'], runtime['current']), root.name)
                self.assertEqual(['[EaglerX i18n] missing key: release.contract.unknown'], runtime['warnings'], root.name)
                for key in referenced_keys:
                    with self.subTest(root=root.name, key=key):
                        for locale_id in ('en', 'zh-CN'):
                            self.assertTrue(catalogs[locale_id].get(key, '').strip(), f'{root.name}: {locale_id} {key}')
                for key, message in inventory['messages'].items():
                    if message['classification'] == 'operational':
                        self.assertNotIn(key, catalogs['en'], f'{root.name}: operational key {key} in en catalog')
                        self.assertNotIn(key, catalogs['zh-CN'], f'{root.name}: operational key {key} in zh-CN catalog')


class DirectRootStaticServer:
    ALLOWED_ROOTS = (ROOT / 'web-1.8', ROOT / 'web-1.12')

    def __init__(self, web_root):
        self.web_root = web_root.resolve()
        self.server = None
        self.thread = None

    def __enter__(self):
        allowed_roots = {path.resolve() for path in self.ALLOWED_ROOTS}
        if self.web_root not in allowed_roots:
            raise AssertionError(f'unsupported direct web root: {self.web_root}')

        root = self.web_root

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(root), **kwargs)

            def do_GET(self):
                if self.path in ('/admin', '/admin/'):
                    self.send_response(302)
                    self.send_header('Location', '/admin.html')
                    self.end_headers()
                    return
                super().do_GET()

            def log_message(self, *_args):
                pass

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    @property
    def base_url(self):
        return f'http://127.0.0.1:{self.server.server_port}'

    def __exit__(self, _type, _value, _traceback):
        try:
            self.server.shutdown()
            self.server.server_close()
        finally:
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                raise AssertionError(f'{self.web_root.name}: static server thread did not stop')


class ServedAdminStaticTests(unittest.TestCase):
    ROOTS = (ROOT / 'web-1.8', ROOT / 'web-1.12')
    RELEASE_ASSETS = ReleaseContractTests.RELEASE_ASSETS

    @staticmethod
    def request(url, follow=True):
        opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
        return opener.open(url, timeout=5)

    def test_direct_root_admin_entrypoints_and_release_assets(self):
        for root in self.ROOTS:
            with self.subTest(root=root.name), DirectRootStaticServer(root) as server:
                with self.request(server.base_url + '/') as response:
                    self.assertEqual(200, response.status, f'{root.name} /')
                    self.assertTrue(response.read(), f'{root.name} /: empty response')
                for route in ('/admin.html',):
                    with self.subTest(root=root.name, route=route):
                        with self.request(server.base_url + route) as response:
                            body = response.read().decode('utf-8')
                            self.assertEqual(200, response.status, f'{root.name} {route}')
                            self.assertIn('EaglercraftX Admin Console', body, f'{root.name} {route}')
                            self.assertIn('id="locale-select"', body, f'{root.name} {route}')
                            self.assertIn('admin.css', body, f'{root.name} {route}')
                            self.assertIn('admin-i18n.js', body, f'{root.name} {route}')
                            self.assertIn('admin.js?v=', body, f'{root.name} {route}')
                            self.assertLess(body.index('admin-i18n.js'), body.index('admin.js?v='), f'{root.name} {route}')
                for route in ('/admin', '/admin/'):
                    with self.subTest(root=root.name, route=route):
                        with self.assertRaises(urllib.error.HTTPError) as raised:
                            self.request(server.base_url + route, follow=False)
                        self.assertEqual(302, raised.exception.code, f'{root.name} {route}')
                        self.assertEqual('/admin.html', raised.exception.headers['Location'], f'{root.name} {route}')
                        raised.exception.close()
                        with self.request(server.base_url + route) as response:
                            self.assertEqual(200, response.status, f'{root.name} {route}')
                for asset in self.RELEASE_ASSETS:
                    route = '/' + asset
                    with self.subTest(root=root.name, route=route):
                        with self.request(server.base_url + route) as response:
                            self.assertEqual(200, response.status, f'{root.name} {route}')
                            self.assertTrue(response.read(), f'{root.name} {route}: empty response')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


if __name__ == '__main__':
    unittest.main()
