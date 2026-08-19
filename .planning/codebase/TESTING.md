# Testing Patterns

**Analysis Date:** 2026-08-19

## Test Framework

**Runner:**
- No test runner or test configuration is present.
- No `tests/`, `test_*.py`, `*.test.*`, or `*.spec.*` files were detected.

**Assertion Library:**
- Not applicable. The repository has no assertion library or test dependency manifest.

**Run Commands:**
```bash
python3 -m py_compile script/http_server.py   # Python syntax check
bash -n script/start_server.sh build.sh        # Shell syntax checks
node --check web-1.12/admin.js                 # JavaScript syntax check when Node.js is available
docker build -t eaglerx1.8server .             # Image/build smoke check
```

## Test File Organization

**Location:**
- No automated test tree is present. Operational checks are implied by the scripts and Docker workflow documented in `README.md`.

**Naming:**
- Not applicable. Add focused tests under `tests/` using `test_*.py` for Python behavior and `*.test.js` for browser-independent JavaScript helpers if testing is introduced.

**Structure:**
```
tests/
├── test_http_server.py
└── test_startup_contract.py
```

## Test Structure

**Suite Organization:**
```python
# Pattern to use if tests are added; no equivalent exists in the repository today.
def test_normalize_config_value_rejects_unknown_key():
    with pytest.raises(ValueError):
        normalize_config_value('unknown', 'value')
```

**Patterns:**
- Current verification is command-level and manual: start the container with `MINECRAFT_VERSION`, verify the `web/` and `server/` symlinks, then exercise ports 5200/5201 and optional RCON through the admin UI.
- For new Python tests, isolate pure helpers such as `normalize_config_value()`, `resolve_numeric_world_seed()`, `_pack_rcon_packet()`, and token verification before testing live sockets or Minecraft processes.
- For endpoint tests, use a temporary server-properties file and mocked RCON/Dynmap boundaries; avoid requiring Paper, Waterfall, or the native cubiomes library for unit coverage.

## Mocking

**Framework:**
- No mocking framework is installed or configured.

**Patterns:**
```python
# Recommended seam for future tests: replace module boundary functions directly.
http_server.rcon_send = lambda command, retries=3: 'Seed: 123'
```

**What to Mock:**
- Mock socket/RCON calls, `HTTPConnection` Dynmap calls, filesystem roots, `subprocess`/tmux operations, and `ctypes.CDLL` loading when testing `script/http_server.py`.
- Mock browser `fetch`, timers, and DOM elements when testing extracted admin-panel logic from `web-1.12/admin.js`.

**What NOT to Mock:**
- Keep pure validation, seed conversion, packet packing, cache expiry decisions, and response-shape assertions real.
- Keep `script/start_server.sh` validation and symlink behavior in a temporary directory for an integration smoke test.

## Fixtures and Factories

**Test Data:**
```python
SERVER_PROPERTIES = {
    'level-name': 'world',
    'level-seed': '12345',
    'pvp': 'true',
}
```

**Location:**
- No fixtures or factories are present. Store reusable temporary server-property fixtures under `tests/fixtures/` if the test suite is added.

## Coverage

**Requirements:** None enforced. There is no coverage configuration or threshold.

**View Coverage:**
```bash
pytest --cov=script --cov-report=term-missing   # after adding pytest/pytest-cov
```

## Test Types

**Unit Tests:**
- Not currently used. Prioritize pure configuration, seed, authentication-token, RCON packet, and parser helpers in `script/http_server.py`.

**Integration Tests:**
- Not currently used. The highest-value integration check covers `script/start_server.sh` version selection, symlink safety, EULA/property mutation, and `script/http_server.py` HTTP responses with a temporary runtime directory.

**E2E Tests:**
- Not detected. The admin panel in `web-1.8/admin.js` and `web-1.12/admin.js` is currently verified through manual browser interaction against a running container.

## Common Patterns

**Async Testing:**
```javascript
await expect(fetchJson('/api/status')).resolves.toMatchObject({ success: true });
```

**Error Testing:**
```python
with pytest.raises(ValueError, match='out of range'):
    normalize_config_value('max-players', 0)
```

## CI/CD Practices

- No GitHub Actions, GitLab CI, Jenkins, or other CI configuration was detected.
- `build.sh` is the repository build wrapper: it enables shell fail-fast behavior, runs `docker build`, prints the image tag/size, and optionally pushes when the second argument is `push`.
- Dockerfile validation is the only repository-level build gate currently encoded; production startup is performed by `/usr/local/bin/eaglerx-start`, copied from `script/start_server.sh` in `Dockerfile`.
- Add CI in this order: shell/Python/JavaScript syntax checks, focused Python tests for pure helpers, then a Docker build smoke test. Keep live Paper/RCON tests in a separately provisioned integration job.

---

*Testing analysis: 2026-08-19*
