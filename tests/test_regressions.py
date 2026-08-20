import hashlib
import hmac
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest


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


class I18nInventoryTests(unittest.TestCase):
    INVENTORY_PATHS = [
        ROOT / 'web-1.8' / 'admin-i18n-inventory.json',
        ROOT / 'web-1.12' / 'admin-i18n-inventory.json',
    ]
    ADMIN_ASSETS = ('admin.html', 'admin.js', 'admin.css')

    def load_inventory(self):
        return json.loads(self.INVENTORY_PATHS[0].read_text(encoding='utf-8'))

    def test_inventory_is_mirrored_and_valid_json(self):
        self.assertEqual(
            self.INVENTORY_PATHS[0].read_bytes(),
            self.INVENTORY_PATHS[1].read_bytes(),
        )
        self.assertIn('messages', self.load_inventory())

    def test_message_schema_and_source_locators(self):
        inventory = self.load_inventory()
        allowed_kinds = {'text', 'attribute', 'renderer', 'dialog', 'toast', 'log', 'state', 'client-prefix'}
        allowed_classifications = {'presentation', 'operational'}
        for key, message in inventory['messages'].items():
            with self.subTest(key=key):
                self.assertRegex(key, r'^(document|accessibility|header|nav|hero|section|card|action|option|dialog|field|validation|status|toast|console|world|operational)\.')
                self.assertIn(message['kind'], allowed_kinds)
                self.assertIn(message['classification'], allowed_classifications)
                source = message['source']
                self.assertEqual({'file', 'locator'}, set(source))
                self.assertIn(source['file'], {'admin.html', 'admin.js', 'admin.css'})
                content = (ROOT / 'web-1.8' / source['file']).read_text(encoding='utf-8')
                self.assertIn(source['locator'], content)

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
        self.assertRegex(source, r"function log\(msg, cls\)[\s\S]+?body\.textContent = msg")
        self.assertIn('function escapeHtml(s)', source)
        self.assertIn("String(s).replace(/[&<>'\"]", source)


if __name__ == '__main__':
    unittest.main()
