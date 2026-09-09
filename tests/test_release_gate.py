import importlib.util
import http.server
import io
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
import zipfile
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "script" / "release_gate.py"
spec = importlib.util.spec_from_file_location("eaglerx_release_gate_tests", GATE_PATH)
release_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_gate)


class ReleaseGateTests(unittest.TestCase):
    def test_fixture_plugin_is_a_readable_minimal_paper_archive(self):
        package = release_gate.fixture_jar_bytes()
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(
                ["plugin.yml", "gate/release/EaglerXReleaseGate.class"],
                archive.namelist(),
            )
            self.assertIn("main: gate.release.EaglerXReleaseGate", archive.read("plugin.yml").decode())
            self.assertTrue(archive.read("gate/release/EaglerXReleaseGate.class").startswith(b"\xca\xfe\xba\xbe"))

    def test_browser_evidence_parser_keeps_only_structured_rows(self):
        output = (
            b'browser-matrix-evidence {"boundary":"fixture","root":"web-1.8","locale":"en"}\n'
            b'browser-matrix-evidence raw secret output\n'
            b'browser-matrix-evidence deployment-boundary: live not exercised\n'
        )
        rows = release_gate.parse_browser_evidence(output)
        self.assertEqual(2, len(rows))
        self.assertEqual("web-1.8", rows[0]["root"])
        self.assertNotIn("secret", repr(rows))

    def test_browser_failure_stage_keeps_only_the_controlled_label(self):
        output = b"AssertionError: web-1.8:open-admin: untrusted fixture-secret"
        self.assertEqual(
            "browser-matrix-web-1.8-open-admin",
            release_gate.browser_failure_stage(output),
        )
        self.assertEqual("browser-matrix", release_gate.browser_failure_stage(b"fixture-secret"))

    def test_evidence_omits_credentials_and_plugin_data(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = release_gate.Evidence(temp, live_requested=False)
            evidence.emit({
                "kind": "fixture",
                "token": "fixture-token",
                "plugin_data": "fixture-data",
                "status": "pass",
            })
            row = json.loads(evidence.path.read_text(encoding="utf-8"))
            self.assertNotIn("token", row)
            self.assertNotIn("plugin_data", row)
            self.assertEqual("pass", row["status"])
            summary = evidence.finish("pass")
            self.assertFalse(summary["release_ready"])
            self.assertFalse(summary["credentials_recorded"])
            self.assertFalse(summary["plugin_data_recorded"])

    def test_docker_boundary_is_explicit_and_live_blocks(self):
        options = SimpleNamespace(live=False, build=False, image=None)
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(
            release_gate, "docker_available", return_value=False
        ):
            evidence = release_gate.Evidence(temp, live_requested=False)
            self.assertFalse(release_gate.run_docker_gate(options, evidence))
            self.assertEqual("skipped", evidence.rows[-1]["status"])

            options.live = True
            with self.assertRaises(release_gate.GateFailure):
                release_gate.run_docker_gate(options, evidence)
            self.assertEqual("blocked", evidence.rows[-1]["status"])

    def test_live_container_parses_the_random_host_port(self):
        container = release_gate.LiveContainer("fixture", "fixture", "/tmp", "1.8", "fixture")
        result = SimpleNamespace(stdout=b"127.0.0.1:49153\n")
        with mock.patch.object(release_gate, "run_command", return_value=result):
            self.assertEqual(49153, container.mapped_port())

    def test_live_container_stops_gracefully_before_removal(self):
        container = release_gate.LiveContainer("fixture", "fixture", "/tmp", "1.12", "fixture")
        with mock.patch.object(release_gate.subprocess, "run") as run:
            container.stop()
        self.assertEqual(
            [
                ["docker", "stop", "--time", "45", "fixture"],
                ["docker", "rm", "-f", "fixture"],
            ],
            [call.args[0] for call in run.call_args_list],
        )

    def test_restart_uses_the_long_running_api_timeout(self):
        container = SimpleNamespace(base_url="http://127.0.0.1:5201", version="1.8")
        with mock.patch.object(
            release_gate, "post_json", return_value=(200, {"success": True})
        ) as request, mock.patch.object(release_gate, "poll_until"):
            release_gate.restart_and_wait(container, "fixture-token", True)
        request.assert_called_once_with(
            container.base_url,
            "/api/system",
            "fixture-token",
            {"action": "restart_server"},
            timeout=380,
        )

    def test_restart_accepts_a_slow_successful_http_response(self):
        class SlowRestart(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                time.sleep(0.18)  # Scale a valid 180-second restart to milliseconds.
                try:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b'{"success": true}')
                except BrokenPipeError:
                    pass

            def log_message(self, *args):
                pass

        urlopen = release_gate.urllib.request.urlopen
        with http.server.HTTPServer(('127.0.0.1', 0), SlowRestart) as server:
            thread = threading.Thread(target=server.handle_request)
            thread.start()
            container = SimpleNamespace(
                base_url=f'http://127.0.0.1:{server.server_port}', version='1.8'
            )
            try:
                with mock.patch.object(release_gate.urllib.request, 'urlopen',
                    side_effect=lambda request, timeout: urlopen(request, timeout=timeout / 1000)
                ), mock.patch.object(release_gate, 'poll_until'):
                    release_gate.restart_and_wait(container, 'fixture-token', True)
            finally:
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
