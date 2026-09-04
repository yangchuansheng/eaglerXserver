#!/usr/bin/env python3
"""Run the dependency-free EaglercraftX release gate.

The default gate runs repository checks, server regression tests, and the
browser matrix.  ``--live`` adds a mounted Docker/Paper smoke test for both
supported versions, including controlled restart and container replacement.
Evidence is intentionally limited to statuses, hashes, sizes, and boundaries.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ("1.8", "1.12")
WEB_ASSETS = (
    "admin.html",
    "admin.js",
    "admin.css",
    "admin-i18n.js",
    "eaglercraft-server.svg",
)
MOUNT_BOUNDARY = "/eaglerX-1.8-server"
PLUGIN_NAME = "EaglerXReleaseGate"
PLUGIN_FILENAME = "EaglerXReleaseGate-{version}.jar"
DOCKER_IMAGE_DEFAULT = "eaglerx-release-gate"
BROWSER_EVIDENCE_PREFIX = "browser-matrix-evidence "
FIXTURE_JAR_BASE64 = ROOT / "tests" / "fixtures" / "EaglerXReleaseGate.jar.b64"
FORBIDDEN_EVIDENCE_KEYS = frozenset({
    "password",
    "token",
    "secret",
    "authorization",
    "raw",
    "response",
    "command",
    "plugin_data",
})


class GateFailure(RuntimeError):
    """A check failed; details stay out of persisted evidence."""

    def __init__(self, stage, output=b""):
        super().__init__(stage)
        self.stage = str(stage)
        self.output = output if isinstance(output, bytes) else str(output).encode("utf-8", "replace")


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value):
    raw = value if isinstance(value, bytes) else str(value).encode("utf-8", "replace")
    return hashlib.sha256(raw).hexdigest()


def _safe_value(value):
    if isinstance(value, dict):
        return {
            str(key): _safe_value(item)
            for key, item in value.items()
            if str(key).casefold() not in FORBIDDEN_EVIDENCE_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class Evidence:
    """Append JSONL rows and write one small run summary."""

    def __init__(self, base_dir, live_requested):
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{os.getpid()}"
        self.run_dir = Path(base_dir) / run_id
        self.run_dir.mkdir(parents=True, exist_ok=False)
        self.path = self.run_dir / "evidence.jsonl"
        self.rows = []
        self.started_at = utc_now()
        self.live_requested = bool(live_requested)

    def emit(self, row):
        row = _safe_value(row)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
        self.rows.append(row)

    def finish(self, status, live_exercised=False):
        summary = {
            "schema": 1,
            "status": status,
            "release_ready": bool(status == "pass" and live_exercised),
            "started_at": self.started_at,
            "finished_at": utc_now(),
            "git_revision": git_revision(),
            "live_requested": self.live_requested,
            "live_exercised": bool(live_exercised),
            "credentials_recorded": False,
            "plugin_data_recorded": False,
            "evidence_rows": len(self.rows),
        }
        (self.run_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return summary


def git_revision():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def run_command(args, stage, timeout=300, cwd=ROOT):
    try:
        result = subprocess.run(
            [str(part) for part in args],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise GateFailure(stage, str(error)) from error
    if result.returncode:
        raise GateFailure(stage, result.stdout + result.stderr)
    return result


def check_static_release(evidence):
    for version in VERSIONS:
        server_jar = ROOT / f"server-{version}" / "server.jar"
        web_root = ROOT / f"web-{version}"
        if not server_jar.is_file() or not web_root.is_dir():
            raise GateFailure(f"layout-{version}")
    mirror_hashes = {}
    for asset in WEB_ASSETS:
        canonical = ROOT / "web-1.8" / asset
        mirror = ROOT / "web-1.12" / asset
        if not canonical.is_file() or not mirror.is_file() or canonical.read_bytes() != mirror.read_bytes():
            raise GateFailure(f"mirrored-asset-{asset}")
        mirror_hashes[asset] = {
            "sha256": digest(canonical.read_bytes()),
            "bytes": canonical.stat().st_size,
        }
    evidence.emit({
        "kind": "static-release",
        "status": "pass",
        "server_versions": ["Paper 1.8.8", "Paper 1.12.2"],
        "web_roots": ["web-1.8", "web-1.12"],
        "mirrored_assets": mirror_hashes,
    })


def run_server_regression(evidence):
    run_command(
        [sys.executable, "-m", "unittest", "tests.test_regressions", "tests.test_plugin_inventory"],
        "server-regression",
        timeout=300,
    )
    evidence.emit({"kind": "server-regression", "status": "pass"})


def parse_browser_evidence(output):
    rows = []
    for line in output.decode("utf-8", "replace").splitlines():
        if not line.startswith(BROWSER_EVIDENCE_PREFIX):
            continue
        payload = line[len(BROWSER_EVIDENCE_PREFIX):].strip()
        if payload.startswith("{"):
            try:
                row = json.loads(payload)
            except json.JSONDecodeError:
                raise GateFailure("browser-evidence-format")
            if isinstance(row, dict) and row.get("boundary"):
                rows.append(row)
        elif payload.startswith("deployment-boundary:"):
            rows.append({"boundary": payload})
    return rows


def browser_failure_stage(output):
    match = re.search(
        rb"AssertionError: (web-1\.(?:8|12):[a-z0-9-]+):",
        output,
    )
    if not match:
        return "browser-matrix"
    return "browser-matrix-" + match.group(1).decode("ascii").replace(":", "-")


def run_browser_matrix(evidence):
    try:
        result = run_command(
            [sys.executable, "-m", "unittest", "tests.test_browser_release_matrix"],
            "browser-matrix",
            timeout=600,
        )
    except GateFailure as error:
        raise GateFailure(browser_failure_stage(error.output), error.output) from error
    rows = parse_browser_evidence(result.stdout + result.stderr)
    roots = {row.get("root") for row in rows if row.get("root")}
    locales = {row.get("locale") for row in rows if row.get("locale")}
    if not {"web-1.8", "web-1.12"}.issubset(roots) or not {"en", "zh-CN"}.issubset(locales):
        raise GateFailure("browser-evidence-coverage")
    for row in rows:
        evidence.emit({"kind": "browser-matrix-evidence", "status": "pass", **row})
    evidence.emit({
        "kind": "browser-matrix",
        "status": "pass",
        "web_roots": sorted(roots),
        "locales": sorted(locales),
        "evidence_rows": len(rows),
        "boundary": "deterministic Mock Admin API; live Docker/Paper boundary is separate",
    })


def docker_available():
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def inspect_image(image):
    result = run_command(
        ["docker", "image", "inspect", "--format", "{{json .}}", image],
        "docker-image-inspect",
        timeout=60,
    )
    try:
        data = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GateFailure("docker-image-inspect-format", result.stdout) from error
    image_id = str(data.get("Id", ""))
    if not image_id.startswith("sha256:"):
        raise GateFailure("docker-image-id")
    return {
        "image_id": image_id,
        "created": str(data.get("Created", "")),
        "size_bytes": int(data.get("Size", 0) or 0),
        "tags": [str(tag) for tag in data.get("RepoTags", []) if isinstance(tag, str)],
    }


def check_image_layout(image, evidence):
    command = (
        "test -f /opt/eaglerX-1.8-server-image/server-1.8/server.jar "
        "&& test -f /opt/eaglerX-1.8-server-image/server-1.12/server.jar "
        "&& test -d /opt/eaglerX-1.8-server-image/web-1.8 "
        "&& test -d /opt/eaglerX-1.8-server-image/web-1.12"
    )
    run_command(
        ["docker", "run", "--rm", "--entrypoint", "/bin/sh", image, "-c", command],
        "docker-image-layout",
        timeout=120,
    )
    evidence.emit({
        "kind": "docker-image-layout",
        "status": "pass",
        "image": image,
        "contains_versions": ["1.8", "1.12"],
    })


def fixture_jar_bytes():
    return base64.b64decode(FIXTURE_JAR_BASE64.read_text(encoding="ascii").strip(), validate=True)


def json_request(base_url, path, method="GET", payload=None, headers=None, timeout=10):
    body = None
    request_headers = {"Cache-Control": "no-store"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request_headers.update(headers or {})
    request = urllib.request.Request(base_url + path, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        try:
            raw = error.read()
        finally:
            error.close()
        status = error.code
    except (OSError, urllib.error.URLError):
        return 0, {}
    try:
        payload_data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload_data = {}
    return status, payload_data if isinstance(payload_data, dict) else {}


def post_json(base_url, path, token, payload, timeout=10):
    data = dict(payload)
    data["token"] = token
    return json_request(base_url, path, "POST", data, timeout=timeout)


def upload_package(container, token, filename, package, stage):
    request = urllib.request.Request(
        container.base_url + "/api/plugins/upload",
        data=package,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/java-archive",
            "X-Plugin-Filename": filename,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        raise GateFailure(stage, str(error)) from error
    if status != 201 or not isinstance(body, dict) or body.get("success") is not True:
        raise GateFailure(stage)
    return body


def poll_until(stage, callback, predicate, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = callback()
        if predicate(value):
            return value
        time.sleep(1)
    raise GateFailure(stage)


class LiveContainer:
    def __init__(self, image, name, mount, version, password):
        self.image = image
        self.name = name
        self.mount = Path(mount)
        self.version = version
        self.password = password
        self.port = None

    def start(self):
        result = run_command(
            [
                "docker", "run", "-d", "--name", self.name,
                "-p", "127.0.0.1::5201",
                "-e", f"MINECRAFT_VERSION={self.version}",
                "-e", f"RCON_PASSWORD={self.password}",
                "-e", f"ADMIN_AUTH_SECRET={secrets.token_urlsafe(32)}",
                "-v", f"{self.mount}:{MOUNT_BOUNDARY}",
                self.image,
            ],
            f"live-start-{self.version}",
            timeout=120,
        )
        if not result.stdout.strip():
            raise GateFailure(f"live-start-{self.version}", result.stdout + result.stderr)
        self.port = poll_until(
            f"live-port-{self.version}",
            self.mapped_port,
            lambda value: value is not None,
            30,
        )
        poll_until(
            f"live-api-{self.version}",
            lambda: json_request(self.base_url, "/api/status"),
            lambda value: value[0] == 200 and value[1].get("success") is True,
            180,
        )

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.port}"

    def mapped_port(self):
        try:
            result = run_command(["docker", "port", self.name, "5201/tcp"], "live-port-query", timeout=15)
        except GateFailure:
            return None
        match = re.search(r":(\d+)\s*$", result.stdout.decode("utf-8", "replace"), re.MULTILINE)
        return int(match.group(1)) if match else None

    def stop(self):
        for command, timeout in (
            (["docker", "stop", "--time", "45", self.name], 60),
            (["docker", "rm", "-f", self.name], 30),
        ):
            try:
                subprocess.run(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=timeout,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                pass


def login(container):
    status, body = json_request(
        container.base_url,
        "/api/login",
        "POST",
        {"password": container.password},
    )
    token = body.get("token") if status == 200 else None
    if not body.get("success") or not isinstance(token, str) or not token:
        raise GateFailure(f"live-login-{container.version}")
    return token


def runtime_command(container, token, command):
    status, body = post_json(container.base_url, "/api/rcon", token, {"command": command})
    if status != 200 or body.get("success") is not True:
        raise GateFailure(f"live-rcon-{container.version}")
    return str(body.get("response", ""))


def inventory(container, token):
    status, body = post_json(container.base_url, "/api/plugins", token, {"action": "list"})
    if status != 200 or body.get("success") is not True:
        raise GateFailure(f"live-plugin-list-{container.version}")
    return body


def restart_and_wait(container, token, present):
    status, body = post_json(
        container.base_url,
        "/api/system",
        token,
        {"action": "restart_server"},
        timeout=130,
    )
    if status != 200 or body.get("success") is not True:
        raise GateFailure(f"live-restart-{container.version}")
    poll_until(
        f"live-paper-plugin-{container.version}",
        lambda: try_runtime_command(container, token, "plugins"),
        lambda output: output is not None and (PLUGIN_NAME.casefold() in output.casefold()) is present,
        120,
    )
    poll_until(
        f"live-restart-marker-{container.version}",
        lambda: try_inventory(container, token),
        lambda data: data.get("pending_restart") is False,
        30,
    )


def try_runtime_command(container, token, command):
    try:
        return runtime_command(container, token, command)
    except GateFailure:
        return None


def try_inventory(container, token):
    try:
        return inventory(container, token)
    except GateFailure:
        return {}


def run_live_version(image, image_info, version, evidence):
    fixture = fixture_jar_bytes()
    filename = PLUGIN_FILENAME.format(version=version)
    with tempfile.TemporaryDirectory(prefix=f"eaglerx-release-gate-{version.replace('.', '')}-") as mount_dir:
        mount = Path(mount_dir)
        first = LiveContainer(
            image,
            f"eaglerx-gate-{os.getpid()}-{version.replace('.', '')}-a",
            mount,
            version,
            secrets.token_urlsafe(32),
        )
        replacement = None
        try:
            first.start()
            status, status_body = json_request(first.base_url, "/api/status")
            if status != 200 or status_body.get("minecraft_version") != version:
                raise GateFailure(f"live-version-{version}")
            token = login(first)
            poll_until(
                f"live-paper-version-{version}",
                lambda: try_runtime_command(first, token, "version"),
                lambda output: isinstance(output, str) and "paper" in output.casefold(),
                120,
            )

            list_body = inventory(first, token)
            if list_body.get("upload_limit") != 64 * 1024 * 1024:
                raise GateFailure(f"live-upload-limit-{version}")

            upload_package(first, token, filename, fixture, f"live-upload-{version}")
            if not inventory(first, token).get("pending_restart"):
                raise GateFailure(f"live-upload-marker-{version}")
            restart_and_wait(first, token, True)

            # A package move changes the next Paper classpath only after restart.
            status, body = post_json(first.base_url, "/api/plugins", token, {
                "action": "disable", "filename": filename, "expected_enabled": True,
            })
            if status != 200 or body.get("success") is not True:
                raise GateFailure(f"live-disable-{version}")
            if PLUGIN_NAME.casefold() not in (try_runtime_command(first, token, "plugins") or "").casefold():
                raise GateFailure(f"live-disable-before-restart-{version}")
            restart_and_wait(first, token, False)

            status, body = post_json(first.base_url, "/api/plugins", token, {
                "action": "enable", "filename": filename, "expected_enabled": False,
            })
            if status != 200 or body.get("success") is not True:
                raise GateFailure(f"live-enable-{version}")
            if PLUGIN_NAME.casefold() in (try_runtime_command(first, token, "plugins") or "").casefold():
                raise GateFailure(f"live-enable-before-restart-{version}")
            restart_and_wait(first, token, True)

            repository = mount / "server-data" / f"plugins-{version}"
            data_dir = repository / "enabled" / PLUGIN_NAME
            data_dir.mkdir(parents=True, exist_ok=True)
            sentinel = data_dir / "release-gate-state.bin"
            sentinel.write_bytes(b"release-gate sentinel")
            status, body = post_json(first.base_url, "/api/plugins", token, {
                "action": "delete", "filename": filename, "expected_enabled": True,
            })
            if status != 200 or body.get("success") is not True or body.get("plugin", {}).get("data_retained") is not True:
                raise GateFailure(f"live-delete-{version}")
            runtime_plugins = try_runtime_command(first, token, "plugins") or ""
            if not sentinel.is_file() or PLUGIN_NAME.casefold() not in runtime_plugins.casefold():
                raise GateFailure(f"live-delete-before-restart-{version}")
            restart_and_wait(first, token, False)
            if not sentinel.is_file():
                raise GateFailure(f"live-delete-data-retention-{version}")

            upload_package(first, token, filename, fixture, f"live-reinstall-{version}")
            restart_and_wait(first, token, True)
            if not sentinel.is_file():
                raise GateFailure(f"live-reinstall-data-retention-{version}")

            first.stop()
            replacement = LiveContainer(
                image,
                f"eaglerx-gate-{os.getpid()}-{version.replace('.', '')}-b",
                mount,
                version,
                secrets.token_urlsafe(32),
            )
            replacement.start()
            replacement_token = login(replacement)
            status, replacement_status = json_request(replacement.base_url, "/api/status")
            if status != 200 or replacement_status.get("minecraft_version") != version:
                raise GateFailure(f"live-replacement-version-{version}")
            poll_until(
                f"live-replacement-repository-{version}",
                lambda: try_inventory(replacement, replacement_token),
                lambda data: any(item.get("filename") == filename and item.get("enabled") is True for item in data.get("entries", [])) and data.get("pending_restart") is False,
                120,
            )
            poll_until(
                f"live-replacement-paper-{version}",
                lambda: try_runtime_command(replacement, replacement_token, "plugins"),
                lambda output: output is not None and PLUGIN_NAME.casefold() in output.casefold(),
                120,
            )
            if not sentinel.is_file():
                raise GateFailure(f"live-replacement-data-{version}")

            evidence.emit({
                "kind": "live-paper-smoke",
                "status": "pass",
                "image_id": image_info["image_id"],
                "version": version,
                "mount_boundary": MOUNT_BOUNDARY,
            })
        finally:
            if replacement is not None:
                replacement.stop()
            first.stop()


def run_docker_gate(args, evidence):
    available = docker_available()
    if not available:
        evidence.emit({
            "kind": "docker-boundary",
            "status": "skipped" if not args.live and not args.build else "blocked",
            "reason": "Docker daemon unavailable",
            "live_exercised": False,
        })
        if args.live or args.build:
            raise GateFailure("docker-unavailable")
        return False

    image = args.image
    if args.build:
        if not image:
            image = f"{DOCKER_IMAGE_DEFAULT}:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
        run_command(["docker", "build", "--tag", image, str(ROOT)], "docker-build", timeout=args.timeout)
        info = inspect_image(image)
        evidence.emit({
            "kind": "docker-build",
            "status": "pass",
            "image": image,
            **info,
        })
    elif args.live:
        if not image:
            raise GateFailure("live-image-required")
        info = inspect_image(image)
        evidence.emit({
            "kind": "docker-image",
            "status": "pass",
            "image": image,
            **info,
        })

    if args.build or args.live:
        check_image_layout(image, evidence)
    if not args.live:
        return False
    failures = []
    for version in VERSIONS:
        try:
            run_live_version(image, info, version, evidence)
        except GateFailure as error:
            failures.append(error.stage)
            evidence.emit({
                "kind": "live-paper-smoke",
                "status": "fail",
                "stage": error.stage,
                "image_id": info["image_id"],
                "version": version,
                "mount_boundary": MOUNT_BOUNDARY,
                "error_sha256": digest(error.output),
                "error_bytes": len(error.output),
            })
    if failures:
        raise GateFailure("live-paper-smoke")
    return True


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--evidence-dir", default=ROOT / "artifacts" / "release-gate", type=Path)
    result.add_argument("--image", help="Docker image to inspect/run")
    result.add_argument("--build", action="store_true", help="Build and inspect an image before the live gate")
    result.add_argument("--live", action="store_true", help="Run mounted Docker/Paper smoke for both versions")
    result.add_argument("--timeout", type=int, default=900, help="Docker build timeout in seconds")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.live and not args.image and not args.build:
        parser().error("--live requires --image IMAGE or --build")

    evidence = Evidence(args.evidence_dir, args.live)
    live_exercised = False
    try:
        run_command([sys.executable, "-m", "compileall", "-q", "script", "tests"], "syntax")
        evidence.emit({"kind": "syntax", "status": "pass", "scope": ["script", "tests"]})
        check_static_release(evidence)
        run_server_regression(evidence)
        run_browser_matrix(evidence)
        live_exercised = run_docker_gate(args, evidence)
        summary = evidence.finish("pass", live_exercised)
        if summary["release_ready"]:
            print(f"release-gate: PASS ({evidence.run_dir})")
        else:
            print(f"release-gate: PASS WITH LIVE BOUNDARY ({evidence.run_dir})")
        return 0
    except GateFailure as error:
        evidence.emit({
            "kind": "gate",
            "status": "fail",
            "stage": error.stage,
            "error_sha256": digest(error.output),
            "error_bytes": len(error.output),
        })
        evidence.finish("fail", live_exercised)
        print(f"release-gate: FAIL ({error.stage}; evidence: {evidence.run_dir})", file=sys.stderr)
        return 1
    except Exception as error:
        raw = str(error).encode("utf-8", "replace")
        evidence.emit({
            "kind": "gate",
            "status": "fail",
            "stage": "unexpected-error",
            "error_sha256": digest(raw),
            "error_bytes": len(raw),
        })
        evidence.finish("fail", live_exercised)
        print(f"release-gate: FAIL (unexpected-error; evidence: {evidence.run_dir})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
