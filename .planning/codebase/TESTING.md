# Testing Patterns

**Analysis Date:** 2026-08-20

## Test Framework

**Runner:**
- Python standard-library `unittest`; no external test dependency is required.
- Regression coverage lives in `tests/test_regressions.py`.

**Run Commands:**
```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m py_compile script/http_server.py
bash -n script/start_server.sh && bash -n build.sh
node --check web-1.12/admin.js
docker build -t eaglerx1.8server .
```

## Test Organization

`tests/test_regressions.py` groups checks by runtime boundary:

- `HttpBoundaryTests` covers JSON body limits, malformed payloads, and read timeouts.
- `AuthenticationTests` covers login lockout, token-only management access, malformed tokens, restart locking, and serialized property writes.
- `StartScriptTests` covers version validation, incomplete mount preservation, and active-path safety.
- `TmuxLifecycleTests` covers dead-pane detection and respawn when `tmux` is installed.
- `StartupOrderingTests` verifies Paper starts after the Bungee readiness check.

## Test Patterns

**Isolation:**
- Temporary directories protect repository and user data during startup-script checks.
- Fake connection and stream objects exercise HTTP parsing without binding a port.
- Module boundary functions are replaced directly when a test needs an isolated filesystem or process seam.

**Assertions:**
- Use `unittest.TestCase` assertions and `subTest()` for compact input-validation tables.
- Use `@unittest.skipUnless` for optional system tools such as `tmux`.

## Coverage

- No coverage threshold or coverage tool is configured.
- Current tests focus on security boundaries and startup regressions introduced by the management-plane hardening.
- Live Paper, Waterfall, RCON, Dynmap, native cubiomes, browser UI, and Docker runtime flows remain manual integration checks.

## CI/CD Practices

- No hosted CI configuration is present.
- The practical local gate is the `unittest` suite plus Python, Shell, and JavaScript syntax checks.
- `build.sh` remains the image build/push wrapper; `docker build` is the repository-level packaging smoke check.

---

*Testing analysis: 2026-08-20*
