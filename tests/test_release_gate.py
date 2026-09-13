import importlib.util
import http.server
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
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


class DocumentationGateTests(unittest.TestCase):
    """Check documentation through the same entry point used by releases."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "docs", self.root / "docs")
        shutil.copytree(ROOT / "script", self.root / "script")
        for name in ("README.md", "AGENTS.md"):
            shutil.copy2(ROOT / name, self.root / name)
        declaration = (self.root / "docs/compatibility.md").read_text()
        self.tag = re.search(r"^Verified Release Version: `(v[^`]+)`$", declaration, re.M).group(1)
        self.version = self.tag[1:]

    def run_gate(self, *args):
        result = subprocess.run(
            ["bash", "script/release_gate.sh", "--docs-only", "--evidence-dir", "evidence", *args],
            cwd=self.root, capture_output=True, text=True, timeout=15,
        )
        summaries = list((self.root / "evidence").glob("*/summary.json"))
        self.assertEqual(1, len(summaries), result.stderr)
        summary = json.loads(summaries[0].read_text())
        rows = [json.loads(line) for line in summaries[0].with_name("evidence.jsonl").read_text().splitlines()]
        return result, summary, rows

    def test_current_documentation_passes_without_claiming_live_verification(self):
        result, summary, rows = self.run_gate()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(summary["release_ready"])
        self.assertTrue(any(row["kind"] == "documentation" and row["status"] == "pass" for row in rows))

    def test_stale_translated_image_fails_with_an_actionable_location(self):
        path = self.root / "docs/readme/README.zh-CN.md"
        path.write_text(path.read_text().replace(f"eaglerx1.8server:{self.version}", "eaglerx1.8server:0.0.0", 1))
        result, summary, rows = self.run_gate()
        self.assertEqual(1, result.returncode)
        self.assertEqual("fail", summary["status"])
        issue = next(row for row in rows if row["kind"] == "documentation")
        self.assertEqual("docs/readme/README.zh-CN.md", issue["path"])
        self.assertGreater(issue["line"], 1)
        self.assertIn(self.tag, result.stderr)

    def test_missing_quick_start_fails_even_when_other_current_examples_remain(self):
        path = self.root / "README.md"
        text = path.read_text()
        start = text.index("<!-- release-doc:quick-start:start -->")
        end = text.index("<!-- release-doc:quick-start:end -->") + len("<!-- release-doc:quick-start:end -->")
        path.write_text(text[:start] + text[end:])
        result, _, _ = self.run_gate()
        self.assertEqual(1, result.returncode)
        self.assertIn("quick-start", result.stderr)

    def test_tag_context_overrides_the_declared_local_release(self):
        result, _, _ = self.run_gate("--release-tag", "v99.99.99")
        self.assertEqual(1, result.returncode)
        self.assertIn("docs/compatibility.md", result.stderr)
        self.assertIn("v99.99.99", result.stderr)

    def test_current_tag_passes(self):
        result, _, _ = self.run_gate("--release-tag", self.tag)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_historical_and_migration_references_preserve_their_original_versions(self):
        path = self.root / "README.md"
        with path.open("a") as stream:
            for role in ("historical", "migration-source"):
                stream.write(f"\n<!-- release-doc:{role}:start -->\n"
                             "`ghcr.io/yangchuansheng/eaglerx1.8server:2.2.4`\n"
                             f"<!-- release-doc:{role}:end -->\n")
            stream.write("\nGame Version: `1.8`; Paper `1.8.8`; Java `17.0.12`; LoginSecurity `3.2.0`.\n")
        (self.root / "docs/verification/v2.2.4.md").write_text("Historical release `2.2.4`.\n")
        result, _, _ = self.run_gate()
        self.assertEqual(0, result.returncode, result.stderr)

    def test_unmarked_old_image_guidance_fails(self):
        path = self.root / "AGENTS.md"
        path.write_text(path.read_text() + "\nUse `ghcr.io/yangchuansheng/eaglerx1.8server:2.2.4`.\n")
        result, _, _ = self.run_gate()
        self.assertEqual(1, result.returncode)
        self.assertIn("AGENTS.md:", result.stderr)

    def test_missing_verification_record_fails(self):
        (self.root / f"docs/verification/{self.tag}.md").unlink()
        result, _, _ = self.run_gate()
        self.assertEqual(1, result.returncode)
        self.assertIn(f"docs/verification/{self.tag}.md", result.stderr)

    def test_broken_translated_evidence_link_fails(self):
        path = self.root / "docs/readme/README.fr.md"
        path.write_text(path.read_text().replace(f"../verification/{self.tag}.md", f"missing/verification/{self.tag}.md"))
        result, _, _ = self.run_gate()
        self.assertEqual(1, result.returncode)
        self.assertIn("link destination", result.stderr)


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
