import hashlib
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOTS = (ROOT / 'web-1.8', ROOT / 'web-1.12')
MOCK_API_BOUNDARY = 'browser-release-matrix: deterministic local Mock Admin API'
DEPLOYMENT_BOUNDARY = 'deployment-boundary: live Docker/Paper/Waterfall/RCON not exercised'


def fixture_text(*code_points):
    return ''.join(chr(point) for point in code_points)


class MockAdminServer:
    def __init__(self, web_root):
        self.web_root = Path(web_root).resolve()
        if self.web_root not in {path.resolve() for path in WEB_ROOTS}:
            raise AssertionError(f'unsupported direct web root: {self.web_root}')
        self.fixture_password = secrets.token_urlsafe(24)
        self.token = secrets.token_urlsafe(24)
        self.raw_response = fixture_text(32, 32, 70, 105, 120, 116, 117, 114, 101, 32, 114, 97, 119, 32, 111, 117, 116, 112, 117, 116, 10, 85, 110, 105, 99, 111, 100, 101, 32, 10003, 32, 60, 111, 112, 97, 113, 117, 101, 32, 118, 97, 108, 117, 101, 62, 32, 32)
        self.controlled_error = fixture_text(70, 105, 120, 116, 117, 114, 101, 32, 98, 97, 99, 107, 101, 110, 100, 32, 101, 114, 114, 111, 114, 58, 32, 60, 114, 101, 99, 111, 118, 101, 114, 121, 45, 114, 101, 113, 117, 105, 114, 101, 100, 62, 32, 10003)
        self.plugin_entries = [
            {'filename': 'FixturePlugin.jar', 'enabled': True, 'size': 4096, 'modified_at': '2026-08-23T01:02:03Z'},
            {'filename': 'DisabledPlugin.jar', 'enabled': False, 'size': 2048, 'modified_at': '2026-08-22T01:02:03Z'},
        ]
        self.uploaded_plugin_names = set()
        self.expire_next_upload = False
        self.plugin_conflict_next = False
        self.plugin_pending_restart = True
        self.restart_failure_next = False
        self.restart_success_next = False
        self.records = []
        self.server = None
        self.thread = None
        self.ready = threading.Event()

    @property
    def base_url(self):
        return f'http://127.0.0.1:{self.server.server_port}'

    def record(self, method, route, status, command='', raw=''):
        entry = {'method': method, 'route': route, 'status': status, 'command': command}
        if raw:
            raw_bytes = raw if isinstance(raw, bytes) else raw.encode('utf-8')
            entry['raw_sha256'] = hashlib.sha256(raw_bytes).hexdigest()
            entry['raw_bytes'] = len(raw_bytes)
        self.records.append(entry)

    def __enter__(self):
        fixture = self

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(fixture.web_root), **kwargs)

            def log_message(self, *_args):
                pass

            def json(self, status, payload, command='', raw=''):
                body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
                fixture.record(self.command, self.path.split('?', 1)[0], status, command, raw)
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)

            def read_json(self):
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    return json.loads(self.rfile.read(length).decode('utf-8')) if length else {}
                except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                    return None

            def authorized(self, payload):
                return payload is not None and secrets.compare_digest(str(payload.get('token', '')), fixture.token)

            def do_GET(self):
                if self.path == '/api/status':
                    self.json(200, {
                        'success': True,
                        'minecraft_version': '1.8.8',
                        'rcon_port': 25575,
                        'bridge_port': 5201,
                        'native_seed_finder_ready': True,
                    })
                    return
                if self.path in ('/admin', '/admin/'):
                    fixture.record('GET', self.path, 302)
                    self.send_response(302)
                    self.send_header('Location', '/admin.html')
                    self.end_headers()
                    return
                super().do_GET()

            def do_POST(self):
                route = self.path.split('?', 1)[0]
                if route == '/api/plugins/upload':
                    try:
                        length = int(self.headers.get('Content-Length', '0'))
                    except ValueError:
                        fixture.record(self.command, route, 400)
                        self.json(400, {'success': False, 'error': 'invalid content length'})
                        return
                    raw = self.rfile.read(length)
                    if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + fixture.token):
                        self.json(403, {'success': False, 'error': 'token required'}, raw=raw)
                        return
                    if fixture.expire_next_upload:
                        fixture.expire_next_upload = False
                        self.json(403, {'success': False, 'error': 'token expired'}, raw=raw)
                        return
                    filename = self.headers.get('X-Plugin-Filename', '')
                    if filename.casefold() in {name.casefold() for name in fixture.uploaded_plugin_names}:
                        self.json(409, {'success': False, 'error': 'plugin filename already exists'}, raw=raw)
                        return
                    fixture.uploaded_plugin_names.add(filename)
                    fixture.plugin_entries.append({'filename': filename, 'enabled': True, 'size': length, 'modified_at': '2026-08-23T02:03:04Z'})
                    fixture.plugin_pending_restart = True
                    self.json(201, {'success': True, 'filename': filename, 'pending_restart': True}, raw=raw)
                    return
                payload = self.read_json()
                if payload is None:
                    self.json(400, {'success': False, 'error': 'invalid json'})
                    return
                if route == '/api/login':
                    if secrets.compare_digest(str(payload.get('password', '')), fixture.fixture_password):
                        self.json(200, {'success': True, 'token': fixture.token, 'expires_at': int(time.time()) + 3600})
                    else:
                        self.json(403, {'success': False, 'error': 'password mismatch'})
                    return
                if route not in {
                    '/api/rcon', '/api/config', '/api/world-state', '/api/runtime-state',
                    '/api/seed', '/api/structures', '/api/player-location', '/api/plugins',
                    '/api/system',
                }:
                    self.json(404, {'success': False, 'error': 'not found'})
                    return
                if not self.authorized(payload):
                    self.json(403, {'success': False, 'error': 'token required'})
                    return
                if route == '/api/rcon':
                    command = str(payload.get('command', '')).strip()
                    responses = {
                        'list': 'There are 1/20 players online: FixtureAlex',
                        'tps': 'TPS from last 1m, 5m, 15m: 20.0, 19.9, 19.8',
                        'version': 'This server is running FixturePaper 1.8.8',
                        'op FixtureAlex': 'Made FixtureAlex a server operator',
                        'raw-fixture': fixture.raw_response,
                    }
                    if command == 'controlled-error':
                        self.json(200, {'success': False, 'error': fixture.controlled_error}, command, fixture.controlled_error)
                    elif command in responses:
                        self.json(200, {'success': True, 'response': responses[command]}, command, responses[command])
                    else:
                        self.json(200, {'success': True, 'response': f'Fixture accepted command: {command}'}, command)
                    return
                if route == '/api/config':
                    if payload.get('action', 'get') == 'get':
                        self.json(200, {'success': True, 'config': {
                            'pvp': 'true', 'allow-flight': 'false', 'max-players': '20',
                            'motd': 'Fixture MOTD', 'view-distance': '10', 'spawn-protection': '16',
                        }})
                    else:
                        self.json(200, {'success': True, 'updated': payload.get('updates', {}), 'message': 'Fixture configuration saved'})
                    return
                if route == '/api/plugins':
                    action = str(payload.get('action', 'list')).strip().lower()
                    if action in ('enable', 'disable', 'delete'):
                        filename = str(payload.get('filename', ''))
                        entry = next((item for item in fixture.plugin_entries if item.get('filename') == filename), None)
                        if not entry:
                            self.json(404, {'success': False, 'error': 'plugin package unavailable', 'code': 'missing_resource'})
                            return
                        if fixture.plugin_conflict_next:
                            fixture.plugin_conflict_next = False
                            self.json(409, {'success': False, 'error': 'plugin state changed', 'code': 'state_conflict'})
                            return
                        expected = payload.get('expected_enabled')
                        if isinstance(expected, bool) and entry['enabled'] != expected:
                            self.json(409, {'success': False, 'error': 'plugin state changed', 'code': 'state_conflict'})
                            return
                        if action == 'delete':
                            fixture.plugin_entries.remove(entry)
                            fixture.plugin_pending_restart = True
                            self.json(200, {
                                'success': True,
                                'action': action,
                                'filename': filename,
                                'plugin': entry,
                                'data_retained': True,
                                'pending_restart': True,
                            })
                            return
                        target = action == 'enable'
                        if entry['enabled'] == target:
                            self.json(409, {'success': False, 'error': 'plugin state changed', 'code': 'state_conflict'})
                            return
                        entry['enabled'] = target
                        fixture.plugin_pending_restart = True
                        self.json(200, {'success': True, 'action': action, 'filename': filename, 'plugin': entry, 'pending_restart': True})
                        return
                    self.json(200, {
                        'success': True,
                        'minecraft_version': '1.8',
                        'entries': fixture.plugin_entries,
                        'pending_restart': fixture.plugin_pending_restart,
                        'upload_limit': 64 * 1024 * 1024,
                    })
                    return
                if route == '/api/system':
                    if payload.get('action') != 'restart_server':
                        self.json(400, {'success': False, 'error': 'invalid action'})
                    elif fixture.restart_failure_next:
                        fixture.restart_failure_next = False
                        self.json(500, {'success': False, 'error': 'fixture restart failed'})
                    else:
                        fixture.plugin_pending_restart = False if fixture.restart_success_next else fixture.plugin_pending_restart
                        fixture.restart_success_next = False
                        self.json(200, {'success': True, 'restart_in_progress': True})
                    return
                if route == '/api/world-state':
                    self.json(200, {'success': True, 'world': 'fixture-world', 'servertime': 6000, 'hasStorm': False, 'isThundering': False, 'timestamp': 1700000000000})
                    return
                if route == '/api/runtime-state':
                    self.json(200, {'success': True, 'gamerules': {'doDaylightCycle': True}, 'save_enabled': True, 'whitelist_enabled': False, 'pvp_enabled': True})
                    return
                if route == '/api/seed':
                    self.json(200, {'success': True, 'seed': '246813579', 'source': 'rcon', 'minecraft_version': '1.8.8'})
                    return
                if route == '/api/structures':
                    injected_label = 'Village" onmouseover="window.__structureInjected=true" data-review="'
                    self.json(200, {
                        'success': True,
                        'spawn': {'x': 0, 'z': 0, 'distance': 0},
                        'center': {'x': 12, 'z': -8},
                        'radius': 5000,
                        'total_matches': 2,
                        'groups': [
                            {'key': 'village', 'label': injected_label, 'total_found': 1, 'entries': [{'x': 32, 'z': 48, 'distance': 72}]},
                            {'key': 'custom', 'label': injected_label, 'total_found': 1, 'entries': [{'x': -16, 'z': 64, 'distance': 80}]},
                        ],
                        'effective_seed_kind': 'numeric',
                    })
                    return
                self.json(200, {'success': True, 'player': 'FixtureAlex', 'world': 'fixture-world', 'x': 12.5, 'y': 64, 'z': -8.25, 'source': 'playerdata'})

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        def serve():
            self.ready.set()
            self.server.serve_forever()

        self.thread = threading.Thread(target=serve, daemon=True)
        self.thread.start()
        if not self.ready.wait(timeout=5):
            raise AssertionError(f'{self.web_root.name}: mock server did not become ready')
        return self

    def __exit__(self, _type, _value, _traceback):
        try:
            self.server.shutdown()
            self.server.server_close()
        finally:
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                raise AssertionError(f'{self.web_root.name}: mock server thread did not stop')


class AgentBrowser:
    ALLOWED_ACTIONS = ['launch', 'close', 'navigate', 'reload', 'snapshot', 'click', 'fill', 'type', 'press', 'focus', 'select', 'scroll', 'wait', 'get', 'viewport', 'screenshot', 'eval', 'evaluate', 'dialog', 'network', 'requests']

    def __init__(self, root_name, profile, policy, screenshot_dir, deadline):
        self.root_name = root_name
        self.session = f'phase4-{root_name.replace(".", "_")}-{__import__("os").getpid()}'
        self.profile = str(profile)
        self.policy = str(policy)
        self.screenshot_dir = str(screenshot_dir)
        self.deadline = deadline
        self.env = {
            **__import__('os').environ,
            'AGENT_BROWSER_CONTENT_BOUNDARIES': '1',
            'AGENT_BROWSER_MAX_OUTPUT': '4000',
            'AGENT_BROWSER_DEFAULT_TIMEOUT': '10000',
            'AGENT_BROWSER_ALLOWED_DOMAINS': '127.0.0.1,localhost,api.fontshare.com,cdn.fontshare.com,picsum.photos,fastly.picsum.photos',
            'AGENT_BROWSER_ACTION_POLICY': self.policy,
            'AGENT_BROWSER_SCREENSHOT_DIR': self.screenshot_dir,
        }

    def run(self, stage, *command):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f'{self.root_name}:{stage}: scenario deadline exceeded')
        invocation = ['agent-browser', '--session', self.session, '--session-name', self.session, '--profile', self.profile]
        result = subprocess.run(
            [*invocation, '--content-boundaries', '--max-output', '4000', '--action-policy', self.policy,
             '--screenshot-dir', self.screenshot_dir, *(str(part) for part in command)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.env,
            timeout=min(10, remaining),
            check=False,
        )
        if result.returncode:
            raise AssertionError(f'{self.root_name}:{stage}: agent-browser failed ({result.returncode})')
        return result.stdout

    def check(self, stage, expression):
        output = self.run(stage, 'eval', expression)
        if not any(line.strip().strip('"').lower() == 'true' for line in output.splitlines()):
            raise AssertionError(f'{self.root_name}:{stage}: browser assertion failed')

    def snapshot(self, stage):
        self.run(stage, 'snapshot', '-i')

    def batch(self, stage, commands):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f'{self.root_name}:{stage}: scenario deadline exceeded')
        invocation = ['agent-browser', '--session', self.session, '--session-name', self.session, '--profile', self.profile]
        result = subprocess.run(
            [*invocation, '--content-boundaries', '--max-output', '4000', '--action-policy', self.policy,
             '--screenshot-dir', self.screenshot_dir, 'batch', '--json'],
            input=json.dumps(commands), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=self.env, timeout=min(10, remaining), check=False,
        )
        if result.returncode:
            raise AssertionError(f'{self.root_name}:{stage}: browser batch failed ({result.returncode})')
        try:
            results = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise AssertionError(f'{self.root_name}:{stage}: browser batch returned invalid evidence') from error
        if any(not item.get('success') for item in results):
            raise AssertionError(f'{self.root_name}:{stage}: browser batch action failed')
        return result.stdout

    def close(self):
        for command in (
            ['agent-browser', '--session', self.session, 'close'],
            ['agent-browser', 'state', 'clear', self.session],
        ):
            try:
                subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True, timeout=10, check=False, env=self.env)
            except (OSError, subprocess.TimeoutExpired):
                pass


class MockAdminServerTests(unittest.TestCase):
    def test_browser_assertion_omits_page_output(self):
        browser = object.__new__(AgentBrowser)
        browser.root_name = 'web-1.8'
        browser.run = lambda *_args: 'untrusted raw <fixture-secret>'
        with self.assertRaises(AssertionError) as raised:
            browser.check('sanitized-failure', 'false')
        self.assertNotIn('fixture-secret', str(raised.exception))

    def request(self, server, route, payload=None):
        data = None if payload is None else json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(server.base_url + route, data=data, method='GET' if data is None else 'POST')
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as error:
            try:
                return error.code, json.loads(error.read().decode('utf-8'))
            finally:
                error.close()

    def test_routes_authentication_and_sanitized_raw_recording(self):
        with MockAdminServer(WEB_ROOTS[0]) as server:
            status, body = self.request(server, '/api/status')
            self.assertEqual((200, True), (status, body['success']))
            status, body = self.request(server, '/api/login', {'password': 'wrong'})
            self.assertEqual((403, False), (status, body['success']))
            status, body = self.request(server, '/api/login', {'password': server.fixture_password})
            self.assertEqual((200, True), (status, body['success']))
            token = body['token']
            for route, payload in (
                ('/api/rcon', {'command': 'list'}), ('/api/config', {'action': 'get'}),
                ('/api/world-state', {}), ('/api/runtime-state', {}), ('/api/seed', {}),
                ('/api/structures', {'x': 0, 'z': 0}), ('/api/player-location', {'player': 'FixtureAlex'}),
            ):
                status, body = self.request(server, route, payload)
                self.assertEqual((403, False), (status, body['success']))
                payload['token'] = token
                status, body = self.request(server, route, payload)
                self.assertEqual((200, True), (status, body['success']))
            status, body = self.request(server, '/api/rcon', {'token': token, 'command': 'raw-fixture'})
            self.assertEqual((200, server.raw_response), (status, body['response']))
            raw_record = server.records[-1]
            self.assertEqual(hashlib.sha256(server.raw_response.encode('utf-8')).hexdigest(), raw_record['raw_sha256'])
            self.assertEqual(len(server.raw_response.encode('utf-8')), raw_record['raw_bytes'])
            self.assertNotIn('raw', raw_record)
            self.assertNotIn(server.token, repr(server.records))


class BrowserReleaseMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        doctor = subprocess.run(['agent-browser', 'doctor'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30, check=False)
        if doctor.returncode or 'Launch test\n  pass' not in doctor.stdout:
            raise RuntimeError('agent-browser prerequisite failed: run agent-browser doctor and install a usable local Chrome')

    def setUp(self):
        self.evidence = []

    def emit_evidence(self, root, stage, locale, route, viewport='', raw='', error='', screenshot=''):
        row = {
            'boundary': MOCK_API_BOUNDARY,
            'root': root.name,
            'stage': stage,
            'locale': locale,
            'route': route,
        }
        if viewport:
            row['viewport'] = viewport
        if raw:
            row['raw_sha256'] = hashlib.sha256(raw.encode('utf-8')).hexdigest()
            row['raw_bytes'] = len(raw.encode('utf-8'))
        if error:
            row['error_sha256'] = hashlib.sha256(error.encode('utf-8')).hexdigest()
            row['error_bytes'] = len(error.encode('utf-8'))
        if screenshot:
            row['screenshot_sha256'] = screenshot
        self.evidence.append(row)
        print(f'browser-matrix-evidence {json.dumps(row, ensure_ascii=True, sort_keys=True)}')

    def assert_recorded(self, server, route, command=None):
        self.assertTrue(any(record['route'] == route and (command is None or record['command'] == command) for record in server.records), f'{server.web_root.name}: expected recorded route {route}')

    def run_root_scenario(self, root):
        stage = 'setup'
        deadline = time.monotonic() + 60
        temp = tempfile.TemporaryDirectory(prefix=f'phase4-{root.name}-')
        server = MockAdminServer(root)
        browser = None
        try:
            temp_path = Path(temp.name)
            policy = temp_path / 'policy.json'
            policy.write_text(json.dumps({'default': 'deny', 'allow': AgentBrowser.ALLOWED_ACTIONS}), encoding='utf-8')
            screenshots = temp_path / 'screenshots'
            screenshots.mkdir()
            profile = temp_path / 'profile'
            profile.mkdir()
            with server:
                browser = AgentBrowser(root.name, profile, policy, screenshots, deadline)
                stage = 'open-admin'
                browser.batch(stage, [['open', server.base_url + '/admin'], ['snapshot', '-i']])
                browser.check(stage, "document.documentElement.lang === 'en' && document.title === 'EaglercraftX Admin Console' && document.querySelector('#locale-select').value === 'en' && Array.from(document.querySelector('#locale-select').options).map(x => x.textContent).join('|') === 'English|简体中文'")
                self.emit_evidence(root, stage, 'en', '/admin')
                stage = 'authenticate'
                browser.batch(stage, [['fill', '#modal-pw', server.fixture_password], ['click', '#modal-btns .btn-ok'], ['wait', '1200'], ['snapshot', '-i']])
                browser.check(stage, "document.querySelector('#players').innerText.includes('FixtureAlex') && document.querySelector('#world-info').innerText.includes('1.8.8') && document.querySelector('#cfg-motd').value === 'Fixture MOTD' && document.querySelector('#plugin-version').textContent === 'MC 1.8' && document.querySelector('#plugin-list').textContent.includes('FixturePlugin.jar') && document.querySelector('#plugin-list').textContent.includes('DisabledPlugin.jar') && !document.querySelector('#plugin-restart-banner').classList.contains('hidden')")
                for route in ('/api/login', '/api/rcon', '/api/world-state', '/api/runtime-state', '/api/config', '/api/seed', '/api/plugins'):
                    self.assert_recorded(server, route)
                self.emit_evidence(root, stage, 'en', '/api/login')
                stage = 'plugin-upload'
                browser.run(stage, 'eval', "(() => { const input = document.querySelector('#plugin-upload-input'); const data = new Uint8Array([80,75,3,4,1,2,3,4,80,75,5,6]); const file = new File([data], 'FixtureUpload.jar', { type: 'application/java-archive' }); const transfer = new DataTransfer(); transfer.items.add(file); input.files = transfer.files; updatePluginUploadSelection(); return true; })()")
                browser.check(stage, "document.querySelector('#plugin-upload-btn').disabled === false && document.querySelector('#plugin-upload-warning-text').textContent.includes('executes code')")
                browser.run(stage, 'eval', "uploadPlugin(); true")
                browser.run(stage, 'wait', 500)
                browser.check(stage, "document.querySelector('#plugin-upload-status').textContent.includes('Uploaded FixtureUpload.jar') && document.querySelector('#plugin-list').textContent.includes('FixtureUpload.jar') && !document.querySelector('#plugin-restart-banner').classList.contains('hidden')")
                self.assert_recorded(server, '/api/plugins/upload')
                stage = 'plugin-upload-duplicate-and-expiry'
                browser.run(stage, 'select', '#locale-select', 'zh-CN')
                browser.check(stage, "document.querySelector('#plugin-upload-warning-text').textContent.includes('Paper') && document.querySelector('#plugin-upload-btn').textContent === '上传插件'")
                browser.run(stage, 'eval', "(() => { const input = document.querySelector('#plugin-upload-input'); const file = new File([new Uint8Array([80,75,3,4])], 'FixtureUpload.jar', { type: 'application/java-archive' }); const transfer = new DataTransfer(); transfer.items.add(file); input.files = transfer.files; updatePluginUploadSelection(); return true; })()")
                browser.run(stage, 'eval', 'uploadPlugin(); true')
                browser.run(stage, 'wait', 1000)
                browser.check(stage, "document.querySelector('#plugin-upload-status').textContent.includes('plugin filename already exists')")
                server.expire_next_upload = True
                browser.run(stage, 'eval', "(() => { const input = document.querySelector('#plugin-upload-input'); const file = new File([new Uint8Array([80,75,3,4,5])], 'FixtureExpiry.jar', { type: 'application/java-archive' }); const transfer = new DataTransfer(); transfer.items.add(file); input.files = transfer.files; updatePluginUploadSelection(); return true; })()")
                browser.run(stage, 'eval', 'uploadPlugin(); true')
                browser.run(stage, 'wait', 300)
                browser.check(stage, "!document.querySelector('#modal-overlay').classList.contains('hidden') && document.querySelector('#status-text').textContent.includes('请输入密码')")
                browser.run(stage, 'fill', '#modal-pw', server.fixture_password)
                browser.run(stage, 'click', '#modal-btns .btn-ok')
                browser.run(stage, 'wait', 1000)
                browser.check(stage, "document.querySelector('#plugin-upload-warning-text').textContent.includes('Paper') && document.querySelector('#plugin-list').textContent.includes('FixtureUpload.jar')")
                self.assert_recorded(server, '/api/plugins/upload')
                stage = 'plugin-lifecycle'
                browser.run(stage, 'select', '#locale-select', 'en')
                browser.check(stage, "document.querySelectorAll('.plugin-action').length === 3")
                browser.run(stage, 'eval', "(() => { const button = Array.from(document.querySelectorAll('.plugin-action')).find((item) => item.dataset.pluginFilename === 'FixturePlugin.jar'); button.click(); return true; })()")
                browser.run(stage, 'wait', 1000)
                browser.check(stage, "document.querySelector('#plugin-status') === null || (document.querySelector('#plugin-list').textContent.includes('Disabled') && document.querySelector('.plugin-action[data-plugin-action=enable]'))")
                browser.check(stage, "!document.querySelector('#plugin-restart-banner').classList.contains('hidden')")
                server.plugin_conflict_next = True
                browser.run(stage, 'eval', "(() => { const button = Array.from(document.querySelectorAll('.plugin-action')).find((item) => item.dataset.pluginFilename === 'FixturePlugin.jar'); button.click(); return true; })()")
                browser.run(stage, 'wait', 1000)
                browser.check(stage, "document.querySelector('#plugin-upload-status').textContent.includes('Plugin state changed')")
                browser.check(stage, "document.querySelectorAll('.plugin-action[data-plugin-action=enable]').length >= 1")
                browser.run(stage, 'eval', "(() => { const button = Array.from(document.querySelectorAll('.plugin-action')).find((item) => item.dataset.pluginFilename === 'FixturePlugin.jar'); button.click(); return true; })()")
                browser.run(stage, 'wait', 1000)
                browser.check(stage, "document.querySelectorAll('.plugin-action').length === 3")
                browser.run(stage, 'eval', "(() => { const button = Array.from(document.querySelectorAll('.plugin-delete-action')).find((item) => item.dataset.pluginFilename === 'FixturePlugin.jar'); button.click(); return true; })()")
                browser.run(stage, 'wait', 200)
                browser.check(stage, "!document.querySelector('#action-overlay').classList.contains('hidden') && document.querySelector('#action-title').textContent.includes('FixturePlugin.jar') && document.querySelector('#action-desc').textContent.includes('Plugin data') && document.querySelector('#action-preview').textContent.includes('FixturePlugin.jar')")
                browser.run(stage, 'click', '#action-overlay .btn-cancel')
                browser.check(stage, "document.querySelector('#plugin-list').textContent.includes('FixturePlugin.jar')")
                browser.run(stage, 'select', '#locale-select', 'zh-CN')
                browser.run(stage, 'eval', "(() => { const button = Array.from(document.querySelectorAll('.plugin-delete-action')).find((item) => item.dataset.pluginFilename === 'FixturePlugin.jar'); button.click(); return true; })()")
                browser.run(stage, 'wait', 200)
                browser.check(stage, "document.querySelector('#action-title').textContent.includes('FixturePlugin.jar') && document.querySelector('#action-desc').textContent.includes('插件数据')")
                browser.run(stage, 'click', '#action-overlay .btn-cancel')
                browser.run(stage, 'select', '#locale-select', 'en')
                browser.run(stage, 'eval', "(() => { const button = Array.from(document.querySelectorAll('.plugin-delete-action')).find((item) => item.dataset.pluginFilename === 'FixturePlugin.jar'); button.click(); return true; })()")
                browser.run(stage, 'wait', 200)
                browser.run(stage, 'click', '#action-confirm')
                browser.run(stage, 'wait', 1000)
                browser.check(stage, "!document.querySelector('#plugin-list').textContent.includes('FixturePlugin.jar') && document.querySelector('#plugin-upload-status').textContent.includes('Removed FixturePlugin.jar') && !document.querySelector('#plugin-restart-banner').classList.contains('hidden')")
                self.assert_recorded(server, '/api/plugins')
                stage = 'plugin-restart-marker'
                server.restart_failure_next = True
                browser.run(stage, 'eval', "systemRequest({ action: 'restart_server' }).then(function () { return refreshPlugins(); }); true")
                browser.run(stage, 'wait', 500)
                browser.check(stage, "!document.querySelector('#plugin-restart-banner').classList.contains('hidden')")
                server.restart_success_next = True
                browser.run(stage, 'eval', "systemRequest({ action: 'restart_server' }).then(function () { return refreshPlugins(); }); true")
                browser.run(stage, 'wait', 500)
                browser.check(stage, "document.querySelector('#plugin-restart-banner').classList.contains('hidden')")
                server.plugin_pending_restart = True
                browser.run(stage, 'eval', "refreshPlugins(); true")
                browser.run(stage, 'wait', 300)
                self.assert_recorded(server, '/api/system')
                browser.run(stage, 'select', '#locale-select', 'zh-CN')
                stage = 'locale-persist'
                browser.batch(stage, [['snapshot', '-i']])
                browser.check(stage, "document.documentElement.lang === 'zh-CN' && localStorage.getItem('eaglerx_admin_locale') === 'zh-CN' && document.querySelector('#locale-select').value === 'zh-CN'")
                browser.check(stage, "document.querySelector('#ver-tag').textContent.includes('RCON:25575') && document.querySelector('#seedmap-spawn').textContent.includes('搜索完成后会显示世界出生点')")
                browser.check(stage, "document.querySelector('#plugin-title').textContent === '插件仓库'")
                browser.check(stage, "document.querySelector('#plugin-restart-text').textContent.includes('待重启插件变更')")
                browser.batch(stage, [['reload'], ['wait', '500'], ['snapshot', '-i']])
                browser.check(stage, "document.documentElement.lang === 'zh-CN' && document.querySelector('#locale-select').value === 'zh-CN'")
                browser.check(stage, "document.querySelector('#hero-connection').textContent.includes('已连接') && document.querySelector('#world-info').textContent.includes('世界') && document.querySelector('#players').textContent.includes('FixtureAlex')")
                self.emit_evidence(root, stage, 'zh-CN', '/admin')
                browser.run(stage, 'select', '#locale-select', 'en')
                stage = 'dialog-validation-recovery'
                browser.run(stage, 'eval', '(() => { opPlayer(); return true; })()')
                browser.run(stage, 'wait', 200)
                browser.snapshot(stage)
                browser.run(stage, 'eval', '(() => { submitActionDialog({ preventDefault: function() {} }); return true; })()')
                browser.check(stage, "document.querySelector('#toast').textContent.includes('Please complete')")
                browser.run(stage, 'fill', '#action-fields [data-field="player"]', 'FixtureAlex')
                browser.run(stage, 'focus', '#action-fields [data-field="player"]')
                browser.run(stage, 'eval', "(function(){const e=document.querySelector('#action-fields [data-field=player]');e.setSelectionRange(0, 7);return true;}())")
                browser.run(stage, 'select', '#locale-select', 'zh-CN')
                browser.snapshot(stage)
                browser.check(stage, "(function(){const e=document.querySelector('#action-fields [data-field=player]');return e.value === 'FixtureAlex' && document.activeElement === e && e.selectionStart === 0 && e.selectionEnd === 7 && !document.querySelector('#action-preview-wrap').classList.contains('hidden');}())")
                browser.run(stage, 'click', '#action-confirm')
                browser.run(stage, 'wait', 300)
                browser.snapshot(stage)
                self.assert_recorded(server, '/api/rcon', 'op FixtureAlex')
                browser.check(stage, "document.querySelector('#console').textContent.includes('Made FixtureAlex a server operator')")
                browser.check(stage, "document.querySelector('#toast').textContent.includes('命令已提交')")
                self.emit_evidence(root, stage, 'zh-CN', '/api/rcon')
                stage = 'structure-localization-safety'
                browser.run(stage, 'set', 'viewport', '1440', '900')
                browser.run(stage, 'wait', 1500)
                browser.check(stage, "!document.querySelector('#seed-search-btn').disabled")
                browser.run(stage, 'eval', "(() => { document.querySelector('#seed-search-btn').scrollIntoView({ block: 'center', behavior: 'instant' }); return true; })()")
                browser.run(stage, 'click', '#seed-search-btn')
                browser.run(stage, 'wait', 200)
                browser.run(stage, 'fill', '#action-fields [data-field="player"]', 'FixtureAlex')
                browser.snapshot(stage)
                browser.run(stage, 'click', '#action-confirm')
                browser.run(stage, 'wait', 500)
                browser.snapshot(stage)
                self.assert_recorded(server, '/api/player-location')
                self.assert_recorded(server, '/api/structures')
                browser.run(stage, 'select', '#locale-select', 'en')
                browser.snapshot(stage)
                browser.check(stage, "(() => { const headings = Array.from(document.querySelectorAll('.seedmap-group-head strong')).map(e => e.textContent); const source = document.querySelector('#seedmap-source').textContent; return headings[0] === 'Village' && source.includes('player data snapshot') && !source.includes('玩家存档快照') && !document.querySelector('#seedmap-results [onmouseover]') && window.__structureInjected !== true; })()")
                browser.run(stage, 'eval', '(() => { locatePlayerInfo(); return true; })()')
                browser.run(stage, 'wait', 200)
                browser.run(stage, 'fill', '#action-fields [data-field="player"]', 'FixtureAlex')
                browser.run(stage, 'click', '#action-confirm')
                browser.run(stage, 'wait', 300)
                browser.check(stage, "document.querySelector('#console').textContent.includes('Player coordinates [FixtureAlex]') && !document.querySelector('#console').textContent.includes('玩家坐标 [FixtureAlex]')")
                self.emit_evidence(root, stage, 'en', '/api/structures')
                stage = 'raw-error-recovery'
                browser.run(stage, 'eval', "send('raw-fixture').then(function() { return true; })")
                browser.snapshot(stage)
                raw_literal = json.dumps(server.raw_response)
                browser.check(stage, f"Array.from(document.querySelectorAll('#console .out')).some(e => e.textContent === {raw_literal})")
                self.assert_recorded(server, '/api/rcon', 'raw-fixture')
                browser.run(stage, 'eval', "send('controlled-error').then(function() { return true; })")
                browser.snapshot(stage)
                error_literal = json.dumps(server.controlled_error)
                browser.check(stage, f"document.querySelector('#console').textContent.includes('Request failed') && document.querySelector('#console').textContent.includes({error_literal})")
                browser.run(stage, 'eval', "send('list').then(function() { return true; })")
                browser.snapshot(stage)
                browser.check(stage, "document.querySelector('#console').textContent.includes('There are 1/20 players online: FixtureAlex')")
                self.assert_recorded(server, '/api/rcon', 'list')
                self.emit_evidence(root, stage, 'en', '/api/rcon', raw=server.raw_response, error=server.controlled_error)
                for width, height, name in ((1440, 900, 'desktop'), (375, 812, 'mobile')):
                    stage = f'viewport-{name}'
                    browser.run(stage, 'set', 'viewport', str(width), str(height))
                    image = screenshots / f'{name}.png'
                    browser.run(stage, 'screenshot', str(image))
                    browser.check(stage, "(function(){const s=document.querySelector('#locale-select'), p=document.querySelector('#cmd-bar button');return s.getBoundingClientRect().width > 0 && p.getBoundingClientRect().width > 0 && document.documentElement.scrollWidth <= window.innerWidth;}())")
                    self.assertTrue(image.is_file(), f'{root.name}: missing {name} screenshot')
                    screenshot_digest = hashlib.sha256(image.read_bytes()).hexdigest()
                    self.assertTrue(screenshot_digest, f'{root.name}: empty {name} screenshot digest')
                    self.emit_evidence(root, stage, 'en', '/admin.html', f'{width}x{height}', screenshot=screenshot_digest)
                stage = 'network-boundary'
                network_output = browser.run(stage, 'network', 'requests', '--json')
                try:
                    network_payload = json.loads(network_output)
                except json.JSONDecodeError as error:
                    raise AssertionError(f'{root.name}: network evidence is not JSON') from error
                network_data = network_payload.get('data', {}) if isinstance(network_payload, dict) else {}
                network_records = network_payload if isinstance(network_payload, list) else network_data.get('requests', [])
                network_urls = [record.get('url', '') for record in network_records if isinstance(record, dict)]
                self.assertTrue(network_urls, f'{root.name}: missing browser network evidence')
                allowed_origins = (server.base_url, 'https://api.fontshare.com/', 'https://cdn.fontshare.com/', 'https://picsum.photos/', 'https://fastly.picsum.photos/')
                self.assertTrue(all(url.startswith(allowed_origins) for url in network_urls), f'{root.name}: browser left the allowed origins')
                self.assertTrue(all(record['route'].startswith('/api/') or record['route'] in ('/admin', '/admin/') for record in server.records), f'{root.name}: unexpected mock route')
                self.assertTrue(any(record.get('raw_sha256') for record in server.records), f'{root.name}: missing sanitized raw evidence')
                self.emit_evidence(root, stage, 'en', '/api/rcon')
        except Exception as error:
            raise AssertionError(f'{root.name}:{stage}: {error}') from error
        finally:
            if browser:
                browser.close()
            temp.cleanup()

    def test_admin_acceptance_for_both_web_roots(self):
        for root in WEB_ROOTS:
            with self.subTest(root=root.name):
                self.run_root_scenario(root)
        self.evidence.append({'boundary': DEPLOYMENT_BOUNDARY})
        print(f'browser-matrix-evidence {DEPLOYMENT_BOUNDARY}')
        self.assertEqual(19, len(self.evidence))
        self.assertEqual({'boundary': DEPLOYMENT_BOUNDARY}, self.evidence[-1])


if __name__ == '__main__':
    unittest.main()
