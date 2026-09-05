import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import http.server
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
START_SCRIPT = ROOT / 'script' / 'start_server.sh'
HTTP_SERVER_PATH = ROOT / 'script' / 'http_server.py'
RELEASE_METADATA_PATH = ROOT / 'script' / 'prepare_release.py'

os.environ['RCON_PASSWORD'] = 'test-password'
os.environ['ADMIN_AUTH_SECRET'] = 'test-auth-secret'
spec = importlib.util.spec_from_file_location('eaglerx_http_server', HTTP_SERVER_PATH)
http_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(http_server)

release_spec = importlib.util.spec_from_file_location('eaglerx_release_metadata', RELEASE_METADATA_PATH)
release_metadata = importlib.util.module_from_spec(release_spec)
release_spec.loader.exec_module(release_metadata)


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


def load_locale_catalogs():
    script = """
const fs = require('fs'); const vm = require('vm'); const window = { console: { warn: function() {} } };
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), { window: window });
console.log(JSON.stringify(window.EaglerXI18n.locales));
"""
    result = subprocess.run(
        ['node', '-e', script, str(ROOT / 'web-1.8' / 'admin-i18n.js')],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    return json.loads(result.stdout)


def referenced_message_keys():
    """Message keys referenced by the admin shell and its script."""
    html = (ROOT / 'web-1.8' / 'admin.html').read_text(encoding='utf-8')
    source = (ROOT / 'web-1.8' / 'admin.js').read_text(encoding='utf-8')
    keys = set(re.findall(r'data-i18n(?:-(?:title|placeholder|aria-label))?="([^"]+)"', html))
    keys |= set(re.findall(r"\b(?:t|presentation|logClient|toastClient)\(\s*'([^']+)'", source))
    keys |= set(re.findall(r"'((?:hero|status|console|dialog|validation|toast|seed|structure)\.[A-Za-z0-9_.-]+)'", source))
    return keys


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


class ConnectionInfoTests(unittest.TestCase):
    def test_public_game_url_contract(self):
        self.assertEqual(
            {
                'success': True,
                'source': 'configured',
                'game_url': 'https://play.example.com/eagler/?region=us',
            },
            http_server.connection_info_payload('https://play.example.com/eagler/?region=us'),
        )
        self.assertEqual(
            {'success': True, 'source': 'inferred', 'game_url': ''},
            http_server.connection_info_payload(''),
        )
        for value in (
            'ws://play.example.com',
            '/relative',
            'https://user:secret@play.example.com',
            'https://play.example.com/#fragment',
            'https://play.example.com/ bad',
            'https://play.example.com:0',
            'https://%zz/',
            'https://foo<bar.example/',
            'https://play.example.com\\evil',
        ):
            with self.subTest(value=value):
                payload = http_server.connection_info_payload(value)
                self.assertEqual((False, 'invalid_public_game_url'), (payload['success'], payload['code']))

    def test_connection_info_route_is_public(self):
        handler = http_server.Handler.__new__(http_server.Handler)
        handler.path = '/api/connection-info'
        handler.responses = []
        handler._json = lambda code, data, headers=None: handler.responses.append((code, data))
        cases = (
            ('https://play.example.com/', 200, {'success': True, 'source': 'configured', 'game_url': 'https://play.example.com/'}),
            ('', 200, {'success': True, 'source': 'inferred', 'game_url': ''}),
            ('https://%zz/', 422, {'success': False, 'code': 'invalid_public_game_url'}),
        )
        for value, status, expected in cases:
            with self.subTest(value=value), mock.patch.object(http_server, 'RCON_ENABLED', False), mock.patch.object(
                http_server, 'PUBLIC_GAME_URL', value
            ):
                handler.responses.clear()
                handler.do_GET()
                self.assertEqual(status, handler.responses[0][0])
                self.assertEqual(expected, {key: handler.responses[0][1][key] for key in expected})


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

    def test_restart_uses_rcon_readiness_for_shell_panes(self):
        with mock.patch.object(
            http_server, 'server_pane_dead', side_effect=[False, True, False]
        ), mock.patch.object(
            http_server, 'rcon_send', side_effect=['stopping', 'ready']
        ) as rcon, mock.patch.object(
            http_server, 'tmux_run'
        ) as tmux, mock.patch.object(
            http_server, 'clear_plugin_restart_marker'
        ) as clear_marker:
            self.assertTrue(http_server.restart_server_process())
        rcon.assert_has_calls([
            mock.call('stop', retries=1),
            mock.call('version', retries=1),
        ])
        tmux.assert_called_once_with([
            'respawn-pane', '-k', '-t', http_server.SERVER_PANE,
            f'cd "{http_server.SERVER_ROOT}"; exec ./run.sh',
        ])
        clear_marker.assert_called_once_with()

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

    def test_startup_initializes_and_activates_persistent_plugin_repository(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_dir = root / 'app'
            server_dir = app_dir / 'server-1.8'
            (server_dir / 'plugins' / 'ExamplePlugin').mkdir(parents=True)
            (server_dir / 'plugins' / 'Example.jar').write_bytes(b'bundled plugin')
            (server_dir / 'plugins' / 'ExamplePlugin' / 'config.yml').write_text('configured', encoding='utf-8')
            (server_dir / 'server.properties').write_text('level-name=world\n', encoding='utf-8')
            (app_dir / 'web-1.8').mkdir(parents=True)
            (app_dir / 'bungee').mkdir(parents=True)
            (app_dir / 'bungee' / 'run.sh').write_text('#!/bin/sh\n', encoding='utf-8')
            (app_dir / 'script').mkdir(parents=True)
            (app_dir / 'script' / 'http_server.py').write_text('#!/usr/bin/env python3\n', encoding='utf-8')
            shutil.copy2(ROOT / 'script' / 'plugin_repository.py', app_dir / 'script' / 'plugin_repository.py')
            fake_bin = root / 'bin'
            fake_bin.mkdir()
            fake_tmux = fake_bin / 'tmux'
            fake_tmux.write_text('#!/bin/sh\nexit 1\n', encoding='utf-8')
            fake_tmux.chmod(0o755)
            data_root = root / 'persistent'
            env = os.environ.copy()
            env.update({
                'APP_DIR': str(app_dir),
                'IMAGE_APP_DIR': str(app_dir),
                'MINECRAFT_VERSION': '1.8',
                'RCON_PASSWORD': '',
                'PERSISTENT_DATA_ROOT': str(data_root),
                'PATH': str(fake_bin) + os.pathsep + env.get('PATH', ''),
            })
            result = subprocess.run(
                [str(START_SCRIPT)], cwd=ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=10, check=False,
            )
            repository = data_root / 'plugins-1.8'
            self.assertNotEqual(0, result.returncode)
            self.assertIn('[plugins] repository initialized', result.stdout)
            self.assertTrue((repository / '.eaglerx-plugin-repository').is_file())
            self.assertTrue((server_dir / 'plugins').is_symlink())
            self.assertEqual(b'bundled plugin', (repository / 'enabled' / 'Example.jar').read_bytes())
            self.assertEqual('configured', (repository / 'enabled' / 'ExamplePlugin' / 'config.yml').read_text(encoding='utf-8'))


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
    ASSETS = ('admin.html', 'admin.js', 'admin.css', 'admin-i18n.js', 'eaglercraft-server.svg')
    STATIC_BINDING_CONTRACT_SHA256 = '81932d15555a002425a1eab3decd55ccd0330bcf684da9a7e1bc59c33257abd0'

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
        html = self.HTML_PATH.read_text(encoding='utf-8')
        self.assertIn('@media (prefers-reduced-motion: reduce)', css)
        for stat_id in ('hero-connection', 'hero-player-count', 'hero-tps'):
            self.assertIn(f'id="{stat_id}"', html)
        for asset in self.ASSETS:
            self.assertEqual((ROOT / 'web-1.8' / asset).read_bytes(), (ROOT / 'web-1.12' / asset).read_bytes())

    def test_changed_assets_are_cache_busted_and_bootstrap_is_local_only(self):
        html = self.HTML_PATH.read_text(encoding='utf-8')
        versions = re.findall(r'(?:admin\.css|admin-i18n\.js|admin\.js)\?v=([^" ]+)', html)
        self.assertEqual(3, len(versions))
        self.assertEqual(1, len(set(versions)))
        self.assertNotEqual('cobalt-20260822', versions[0])

        index = (ROOT / 'web-1.12' / 'index.html').read_text(encoding='utf-8')
        self.assertRegex(index, r'src="bootstrap\.js\?v=[^" ]+"')
        bootstrap = (ROOT / 'web-1.12' / 'bootstrap.js').read_text(encoding='utf-8')
        self.assertNotIn('raw.githubusercontent.com', bootstrap)
        self.assertIn('if(!b.ok)', bootstrap)

    def test_static_bindings_have_bilingual_catalog_keys(self):
        catalogs = load_locale_catalogs()
        bindings = sorted(re.findall(
            r'\b(data-i18n(?:-(?:title|placeholder|aria-label))?)="([^"]+)"',
            self.HTML_PATH.read_text(encoding='utf-8'),
        ))
        fingerprint = hashlib.sha256(json.dumps(bindings, separators=(',', ':')).encode('utf-8')).hexdigest()
        self.assertEqual(self.STATIC_BINDING_CONTRACT_SHA256, fingerprint, f'{len(bindings)} static bindings')
        html_keys = {key for _attribute, key in bindings}
        self.assertTrue(html_keys)
        for key in html_keys:
            with self.subTest(key=key):
                self.assertIn(key, catalogs['en']['messages'])
                self.assertIn(key, catalogs['zh-CN']['messages'])


class AdminAssetBoundaryTests(unittest.TestCase):
    ADMIN_ASSETS = ('admin.html', 'admin.js', 'admin.css', 'admin-i18n.js', 'eaglercraft-server.svg')

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
    ASSETS = ('admin.html', 'admin.js', 'admin.css', 'admin-i18n.js', 'eaglercraft-server.svg')

    def test_referenced_dynamic_keys_are_bilingual_and_mirrors(self):
        catalogs = load_locale_catalogs()
        for key in referenced_message_keys():
            with self.subTest(key=key):
                for locale_id in ('en', 'zh-CN'):
                    self.assertTrue(catalogs[locale_id]['messages'].get(key, '').strip(), f'{locale_id} {key}')
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

    def assert_catalog_contract(self, catalogs):
        referenced = referenced_message_keys()
        self.assertTrue(referenced)
        for locale_id in ('en', 'zh-CN'):
            catalog = catalogs[locale_id]
            for key, value in catalog.items():
                self.assertIsInstance(value, str)
                self.assertTrue(value.strip(), key)
            for key in referenced:
                self.assertIn(key, catalog)
        self.assertEqual(set(catalogs['en']), set(catalogs['zh-CN']))
        self.assertFalse([
            value for value in catalogs['en'].values()
            if re.search(r'[\u4e00-\u9fff]', value)
        ])
        source = (ROOT / 'web-1.8' / 'admin.js').read_text(encoding='utf-8')
        han_fragments = set(re.findall(r'[\u4e00-\u9fff]+', source))
        self.assertEqual([], sorted(han_fragments - set(catalogs['zh-CN'].values())))

    def test_registry_metadata_catalog_coverage_and_parity(self):
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
        self.assert_catalog_contract(result['catalogs'])
        self.assertEqual(self.RUNTIME_PATHS[0].read_bytes(), self.RUNTIME_PATHS[1].read_bytes())

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
    RELEASE_ASSETS = ('admin.html', 'admin.js', 'admin.css', 'admin-i18n.js', 'eaglercraft-server.svg')

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
        subprocess.run(
            [sys.executable, str(ROOT / 'script' / 'sync_admin_assets.py'), '--check'],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
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

    def test_bilingual_catalog_and_runtime_contract(self):
        for root in self.ROOTS:
            with self.subTest(root=root.name):
                runtime = self.runtime(root)
                catalogs = runtime['catalogs']
                self.assertEqual(set(catalogs['en']), set(catalogs['zh-CN']), root.name)
                for key in referenced_message_keys():
                    with self.subTest(root=root.name, key=key):
                        for locale_id in ('en', 'zh-CN'):
                            self.assertTrue(catalogs[locale_id].get(key, '').strip(), f'{root.name}: {locale_id} {key}')
                self.assertFalse([
                    value for value in catalogs['en'].values()
                    if re.search(r'[\u4e00-\u9fff]', value)
                ], root.name)

                self.assertEqual(['en', 'en', 'eaglerx_admin_locale'], runtime['defaults'], root.name)
                self.assertEqual(['en', 'zh-CN'], runtime['ids'], root.name)
                self.assertEqual(['English', '简体中文'], runtime['labels'], root.name)
                self.assertEqual('EaglercraftX Admin Console', runtime['fallback'], root.name)
                self.assertEqual('[[missing:release.contract.unknown]]', runtime['missing'], root.name)
                self.assertEqual('请填写“<strong>FixtureAlex</strong>”。', runtime['interpolation'], root.name)
                self.assertEqual(('zh-CN', 'zh-CN'), (runtime['selected'], runtime['current']), root.name)
                self.assertEqual(['[EaglerX i18n] missing key: release.contract.unknown'], runtime['warnings'], root.name)
    def test_release_tag_and_channel_contract(self):
        tags = ['v1.12.2', 'v2.2', 'v2.2.1', 'v2.3-beta', 'release-3.0']
        commit = 'a' * 40
        self.assertEqual('v2.2.1', release_metadata.highest_release_tag(tags))
        self.assertEqual(
            {
                'release_tag': 'v2.2.1',
                'version': '2.2.1',
                'commit': commit,
                'short_sha': commit[:12],
                'sha_tag': f'sha-{commit[:12]}',
                'promote_latest': 'true',
            },
            release_metadata.release_outputs('v2.2.1', tags, 'push', commit),
        )
        self.assertEqual(
            'false',
            release_metadata.release_outputs('v2.2', tags, 'workflow_dispatch', commit)['promote_latest'],
        )
        with self.assertRaises(ValueError):
            release_metadata.parse_release_tag('v2.3-beta')

    def test_release_workflow_contract(self):
        workflow = (ROOT / '.github' / 'workflows' / 'release.yml').read_text(encoding='utf-8')
        action_refs = re.findall(r'^\s*uses:\s+[^@\s]+@([0-9a-f]+)', workflow, re.MULTILINE)
        self.assertTrue(action_refs)
        self.assertTrue(all(len(reference) == 40 for reference in action_refs))
        self.assertIn('ghcr.io/yangchuansheng/eaglerx1.8server', workflow)
        self.assertIn('--build --live', workflow)
        self.assertIn('actions/attest@', workflow)
        self.assertIn('retention-days: 30', workflow)
        self.assertNotIn('setup-qemu', workflow)
        self.assertNotIn('build-push-action', workflow)


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
