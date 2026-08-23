import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest import mock
import zipfile
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MODULE_PATH = ROOT / 'script' / 'plugin_repository.py'
spec = importlib.util.spec_from_file_location('eaglerx_plugin_repository_tests', PLUGIN_MODULE_PATH)
plugin_repository = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_repository)


class PluginRepositoryTests(unittest.TestCase):
    def make_source(self, root, name='Bundled.jar', payload=b'bundled'):
        source = root / 'bundled-plugins'
        (source / 'ExamplePlugin').mkdir(parents=True)
        (source / name).write_bytes(payload)
        (source / 'ExamplePlugin' / 'config.yml').write_text('keep this data', encoding='utf-8')
        return source

    def test_initialization_activation_and_authoritative_reuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_source(root)
            repository = root / 'data' / 'plugins-1.8'
            plugin_repository.init_repository(source, repository, '1.8')
            plugin_repository.activate_repository(source, repository, '1.8')

            self.assertTrue((repository / plugin_repository.MARKER_FILENAME).is_file())
            self.assertTrue(source.is_symlink())
            self.assertEqual(b'bundled', (repository / 'enabled' / 'Bundled.jar').read_bytes())
            self.assertEqual('keep this data', (repository / 'enabled' / 'ExamplePlugin' / 'config.yml').read_text(encoding='utf-8'))

            (repository / 'enabled' / 'Bundled.jar').unlink()
            (repository / 'enabled' / 'NewImage.jar').write_bytes(b'new image package')
            plugin_repository.init_repository(source, repository, '1.8')
            self.assertFalse((repository / 'enabled' / 'Bundled.jar').exists())
            self.assertTrue((repository / 'enabled' / 'NewImage.jar').exists())

    def test_versions_are_isolated_and_existing_target_entry_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_18 = self.make_source(root / 'v18', 'Shared.jar', b'18')
            source_112 = self.make_source(root / 'v112', 'Shared.jar', b'112')
            repository_18 = root / 'data' / 'plugins-1.8'
            repository_112 = root / 'data' / 'plugins-1.12'
            (repository_18 / 'enabled').mkdir(parents=True)
            (repository_18 / 'enabled' / 'Shared.jar').write_bytes(b'operator package')

            plugin_repository.init_repository(source_18, repository_18, '1.8')
            plugin_repository.init_repository(source_112, repository_112, '1.12')

            self.assertEqual(b'operator package', (repository_18 / 'enabled' / 'Shared.jar').read_bytes())
            self.assertEqual(b'112', (repository_112 / 'enabled' / 'Shared.jar').read_bytes())
            self.assertNotEqual(repository_18, repository_112)

    def test_unsafe_migration_stops_without_changing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_source(root)
            repository = root / 'data' / 'plugins-1.8'
            outside = root / 'outside'
            outside.mkdir(parents=True)
            repository.mkdir(parents=True)
            (repository / 'enabled').symlink_to(outside, target_is_directory=True)

            with self.assertRaises(plugin_repository.RepositoryError):
                plugin_repository.init_repository(source, repository, '1.8')
            self.assertTrue((source / 'Bundled.jar').is_file())
            self.assertEqual(b'bundled', (source / 'Bundled.jar').read_bytes())
            self.assertFalse((repository / plugin_repository.MARKER_FILENAME).exists())

    def test_malformed_authoritative_marker_stops_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_source(root)
            repository = root / 'data' / 'plugins-1.8'
            plugin_repository.init_repository(source, repository, '1.8')
            (repository / plugin_repository.MARKER_FILENAME).write_text('[]', encoding='utf-8')

            with self.assertRaises(plugin_repository.RepositoryError):
                plugin_repository.init_repository(source, repository, '1.8')
            self.assertTrue((source / 'Bundled.jar').is_file())
            self.assertFalse((repository / 'enabled' / 'Bundled.jar').is_symlink())

    def test_inventory_is_sorted_and_restart_marker_transitions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.make_source(root)
            repository = root / 'data' / 'plugins-1.12'
            plugin_repository.init_repository(source, repository, '1.12')
            (repository / 'enabled' / 'zeta.jar').write_bytes(b'z')
            (repository / 'disabled' / 'alpha.jar').write_bytes(b'a')

            entries = plugin_repository.list_repository(repository, '1.12')
            self.assertEqual(['alpha.jar', 'Bundled.jar', 'zeta.jar'], [entry['filename'] for entry in entries])
            self.assertFalse(plugin_repository.pending_restart(repository))
            plugin_repository.mark_pending_restart(repository)
            self.assertTrue(plugin_repository.pending_restart(repository))
            plugin_repository.clear_pending_restart(repository)
            self.assertFalse(plugin_repository.pending_restart(repository))


class PluginApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['RCON_PASSWORD'] = 'plugin-test-password'
        os.environ['ADMIN_AUTH_SECRET'] = 'plugin-test-secret'
        os.environ['MINECRAFT_VERSION'] = '1.8'
        path = ROOT / 'script' / 'http_server.py'
        spec = importlib.util.spec_from_file_location('eaglerx_http_server_plugin_tests', path)
        cls.http_server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.http_server)

    def make_handler(self, payload):
        handler = self.http_server.Handler.__new__(self.http_server.Handler)
        body = json.dumps(payload).encode('utf-8')
        handler.headers = {'Content-Length': str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler.connection = type('Connection', (), {'gettimeout': lambda self: None, 'settimeout': lambda self, value: None})()
        handler.responses = []
        handler._json = lambda code, data, headers=None: handler.responses.append((code, data, headers))
        handler._read_json_body = lambda: payload
        return handler

    def test_list_requires_token_and_returns_inventory_contract(self):
        server = self.http_server
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.mkdir()
            (source / 'A.jar').write_bytes(b'a')
            repository = root / 'plugins-1.8'
            server.MINECRAFT_VERSION = '1.8'
            server.PLUGIN_REPOSITORY_ROOT = str(repository)
            plugin_repository.init_repository(source, repository, '1.8')
            token, _ = server.create_auth_token()

            unauthenticated = self.make_handler({'action': 'list'})
            unauthenticated._handle_plugins()
            self.assertEqual((403, 'token required'), (unauthenticated.responses[0][0], unauthenticated.responses[0][1]['error']))

            authenticated = self.make_handler({'action': 'list', 'token': token})
            authenticated._handle_plugins()
            status, body, _ = authenticated.responses[0]
            self.assertEqual(200, status)
            self.assertEqual('1.8', body['minecraft_version'])
            self.assertEqual(64 * 1024 * 1024, body['upload_limit'])
            self.assertEqual(['A.jar'], [entry['filename'] for entry in body['entries']])
            self.assertFalse(body['pending_restart'])


class PluginUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = PluginApiTests.http_server

    @staticmethod
    def jar_bytes(include_plugin_yml=True, payload=b'plugin'):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            if include_plugin_yml:
                archive.writestr('plugin.yml', 'name: FixturePlugin\nmain: fixture.Main\nversion: 1\n')
            archive.writestr('fixture/Main.class', payload)
        return stream.getvalue()

    def make_repository(self, root):
        source = root / 'source'
        source.mkdir()
        (source / 'A.jar').write_bytes(b'a')
        repository = root / 'plugins-1.8'
        plugin_repository.init_repository(source, repository, '1.8')
        self.server.MINECRAFT_VERSION = '1.8'
        self.server.PLUGIN_REPOSITORY_ROOT = str(repository)
        return repository

    def make_handler(self, body, filename='Upload.jar', token=None, content_length=None):
        handler = self.server.Handler.__new__(self.server.Handler)
        token = token or self.server.create_auth_token()[0]
        handler.headers = {
            'Authorization': 'Bearer ' + token,
            'Content-Length': str(len(body) if content_length is None else content_length),
            'X-Plugin-Filename': filename,
        }
        handler.rfile = io.BytesIO(body)
        handler.connection = type('Connection', (), {
            'gettimeout': lambda self: None,
            'settimeout': lambda self, value: None,
        })()
        handler.responses = []
        handler._json = lambda code, data, headers=None: handler.responses.append((code, data, headers))
        return handler

    def assert_no_upload_temp(self, repository):
        self.assertFalse(any(item.name.startswith(plugin_repository.UPLOAD_TEMP_PREFIX) for item in repository.iterdir()))

    def test_authenticated_jar_upload_publishes_atomically_and_marks_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            repository = self.make_repository(Path(temp))
            token, _ = self.server.create_auth_token()
            body = self.jar_bytes()
            handler = self.make_handler(body, token=token)
            handler._handle_plugin_upload(urlparse('/api/plugins/upload'))

            status, response, _ = handler.responses[0]
            self.assertEqual(201, status)
            self.assertTrue(response['success'])
            self.assertEqual('Upload.jar', response['filename'])
            self.assertTrue((repository / 'enabled' / 'Upload.jar').is_file())
            self.assertTrue(plugin_repository.pending_restart(repository))
            self.assert_no_upload_temp(repository)
            self.assertNotIn(token, repr(response))
            self.assertNotIn(str(repository), repr(response))

    def test_upload_auth_filename_and_body_boundaries_are_distinct(self):
        with tempfile.TemporaryDirectory() as temp:
            repository = self.make_repository(Path(temp))
            body = self.jar_bytes()
            missing_auth = self.make_handler(body)
            missing_auth.headers.pop('Authorization')
            missing_auth._handle_plugin_upload(urlparse('/api/plugins/upload'))
            self.assertEqual((403, 'token required'), (missing_auth.responses[0][0], missing_auth.responses[0][1]['error']))

            for filename in ('../bad.jar', 'nested/bad.jar', 'bad.jar\x00', '.hidden.jar', 'BAD.JAR', 'bad.zip', 'enabled'):
                handler = self.make_handler(body, filename=filename)
                handler._handle_plugin_upload(urlparse('/api/plugins/upload'))
                self.assertEqual(400, handler.responses[0][0], filename)
                self.assertEqual('invalid_filename', handler.responses[0][1]['code'], filename)

            empty = self.make_handler(b'', filename='Empty.jar')
            empty._handle_plugin_upload(urlparse('/api/plugins/upload'))
            self.assertEqual('empty_upload', empty.responses[0][1]['code'])

            incomplete = self.make_handler(body[:-1], filename='Incomplete.jar', content_length=len(body))
            incomplete._handle_plugin_upload(urlparse('/api/plugins/upload'))
            self.assertEqual('incomplete_upload', incomplete.responses[0][1]['code'])

            oversized = self.make_handler(b'', filename='Large.jar', content_length=plugin_repository.UPLOAD_LIMIT + 1)
            oversized._handle_plugin_upload(urlparse('/api/plugins/upload'))
            self.assertEqual((413, 'upload_too_large'), (oversized.responses[0][0], oversized.responses[0][1]['code']))

            timed_out = self.make_handler(body, filename='Timeout.jar')
            timed_out.rfile = type('TimeoutStream', (), {
                'read': lambda self, size: (_ for _ in ()).throw(socket.timeout('timed out')),
            })()
            timed_out._handle_plugin_upload(urlparse('/api/plugins/upload'))
            self.assertEqual((408, 'upload_timeout'), (timed_out.responses[0][0], timed_out.responses[0][1]['code']))

            disconnected = self.make_handler(body, filename='Disconnected.jar')
            disconnected.rfile = type('DisconnectedStream', (), {
                'read': lambda self, size: (_ for _ in ()).throw(ConnectionResetError('reset')),
            })()
            disconnected._handle_plugin_upload(urlparse('/api/plugins/upload'))
            self.assertEqual((400, 'upload_connection_failed'), (disconnected.responses[0][0], disconnected.responses[0][1]['code']))
            self.assert_no_upload_temp(repository)

    def test_archive_validation_duplicate_and_failure_cleanup_preserve_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            repository = self.make_repository(Path(temp))
            before = (repository / 'enabled' / 'A.jar').read_bytes()
            invalid = self.make_handler(self.jar_bytes(include_plugin_yml=False), filename='Invalid.jar')
            invalid._handle_plugin_upload(urlparse('/api/plugins/upload'))
            self.assertEqual((400, 'invalid_archive'), (invalid.responses[0][0], invalid.responses[0][1]['code']))
            self.assertEqual(before, (repository / 'enabled' / 'A.jar').read_bytes())
            self.assertFalse((repository / 'enabled' / 'Invalid.jar').exists())
            self.assert_no_upload_temp(repository)

            (repository / 'disabled' / 'Existing.jar').write_bytes(b'disabled')
            duplicate = self.make_handler(self.jar_bytes(), filename='existing.jar')
            duplicate._handle_plugin_upload(urlparse('/api/plugins/upload'))
            self.assertEqual((409, 'duplicate_filename'), (duplicate.responses[0][0], duplicate.responses[0][1]['code']))
            self.assertEqual(b'disabled', (repository / 'disabled' / 'Existing.jar').read_bytes())
            self.assert_no_upload_temp(repository)

    def test_concurrent_same_name_uploads_publish_one_and_conflict_one(self):
        with tempfile.TemporaryDirectory() as temp:
            repository = self.make_repository(Path(temp))
            body = self.jar_bytes()
            token, _ = self.server.create_auth_token()
            handlers = [self.make_handler(body, token=token) for _ in range(2)]

            def run(handler):
                handler._handle_plugin_upload(urlparse('/api/plugins/upload'))
                return handler.responses[0][0]

            threads = [threading.Thread(target=run, args=(handler,)) for handler in handlers]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)

            self.assertEqual([201, 409], sorted(handler.responses[0][0] for handler in handlers))
            self.assertEqual(1, len(list((repository / 'enabled').glob('Upload.jar'))))
            self.assertTrue(plugin_repository.pending_restart(repository))
            self.assert_no_upload_temp(repository)


class PluginRestartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = PluginApiTests.http_server

    def make_repository(self, root):
        source = root / 'source'
        source.mkdir()
        (source / 'A.jar').write_bytes(b'a')
        repository = root / 'plugins-1.8'
        plugin_repository.init_repository(source, repository, '1.8')
        plugin_repository.mark_pending_restart(repository)
        return repository

    def test_successful_controlled_restart_clears_pending_marker(self):
        server = self.server
        with tempfile.TemporaryDirectory() as temp:
            repository = self.make_repository(Path(temp))
            original_root = server.PLUGIN_REPOSITORY_ROOT
            original_version = server.MINECRAFT_VERSION
            server.PLUGIN_REPOSITORY_ROOT = str(repository)
            server.MINECRAFT_VERSION = '1.8'
            try:
                with mock.patch.object(server, 'server_pane_dead', return_value=False), \
                        mock.patch.object(server, 'server_pane_command', return_value='java'), \
                        mock.patch.object(server, 'wait_for_server_stop', return_value='dead'), \
                        mock.patch.object(server, 'rcon_send', return_value=''), \
                        mock.patch.object(server, 'tmux_run', return_value=''):
                    self.assertTrue(server.restart_server_process())
                self.assertFalse(plugin_repository.pending_restart(repository))
            finally:
                server.PLUGIN_REPOSITORY_ROOT = original_root
                server.MINECRAFT_VERSION = original_version

    def test_failed_controlled_restart_keeps_pending_marker(self):
        server = self.server
        with tempfile.TemporaryDirectory() as temp:
            repository = self.make_repository(Path(temp))
            original_root = server.PLUGIN_REPOSITORY_ROOT
            original_version = server.MINECRAFT_VERSION
            server.PLUGIN_REPOSITORY_ROOT = str(repository)
            server.MINECRAFT_VERSION = '1.8'
            try:
                with mock.patch.object(server, 'server_pane_dead', side_effect=[False, True]), \
                        mock.patch.object(server, 'server_pane_command', return_value='java'), \
                        mock.patch.object(server, 'wait_for_server_stop', return_value='dead'), \
                        mock.patch.object(server, 'rcon_send', side_effect=RuntimeError('RCON unavailable')), \
                        mock.patch.object(server, 'tmux_run', return_value=''):
                    with self.assertRaises(RuntimeError):
                        server.restart_server_process()
                self.assertTrue(plugin_repository.pending_restart(repository))
            finally:
                server.PLUGIN_REPOSITORY_ROOT = original_root
                server.MINECRAFT_VERSION = original_version


if __name__ == '__main__':
    unittest.main()
