# Coding Conventions

**Analysis Date:** 2026-08-19

## Naming Patterns

**Files:**
- Shell entrypoints use lowercase snake_case, for example `script/start_server.sh` and `script/http_server.py`.
- Browser assets use lowercase names, with the two version trees mirroring one another: `web-1.8/admin.js` and `web-1.12/admin.js`.

**Functions:**
- Python functions use snake_case. Private helpers use a leading underscore, for example `_read_json_file()` and `_handle_rcon()` in `script/http_server.py`.
- JavaScript uses camelCase for functions and variables, for example `fetchDynmapPlayerLocation()` and `REFRESH_IN_FLIGHT` in `web-1.12/admin.js`.
- Shell functions use lowercase snake_case, for example `safe_link_dir()` and `set_server_property()` in `script/start_server.sh`.

**Variables:**
- Python constants are uppercase (`RCON_PORT`, `MANAGED_CONFIG`); module state uses descriptive snake_case or uppercase configuration names in `script/http_server.py`.
- JavaScript shared state uses uppercase names (`PASSWORD`, `TOKEN`, `SERVER_INFO`), while local values use camelCase.
- Shell environment/configuration variables use uppercase (`APP_DIR`, `MINECRAFT_VERSION`); local function variables also use lowercase where scope is local.

**Types:**
- Python uses standard library classes and `ctypes.Structure` for the native bridge (`CubiomesPos`, `CubiomesStructureConfig`) in `script/http_server.py`.
- JavaScript is plain browser JavaScript with object literals and arrays; no TypeScript or runtime schema library is present.

## Code Style

**Formatting:**
- Python follows four-space indentation and standard-library imports grouped at the top of `script/http_server.py`.
- Shell scripts use two-space indentation in existing control blocks, quote paths and variable expansions, and begin executable entrypoints with a shebang.
- JavaScript mixes modern `const`/`let`/`async` syntax with legacy `var` and compressed helper functions in `web-1.12/admin.js`; preserve the local style when editing a mirrored admin file.
- No repository formatter configuration is present. `web-1.8/admin.js` and `web-1.12/admin.js` are maintained as matching copies for the two client versions.

**Linting:**
- No ESLint, Prettier, Ruff, Black, ShellCheck, or equivalent configuration is present.
- Syntax checks are the practical baseline: `python3 -m py_compile script/http_server.py`, `bash -n script/start_server.sh`, and `node --check web-1.12/admin.js` when Node.js is available.

## Import Organization

**Order:**
1. Python standard-library imports appear together at the top of `script/http_server.py`.
2. No third-party Python package imports or local Python package imports are used.
3. Browser JavaScript has no import statements; page scripts are loaded by HTML files such as `web-1.12/admin.html`.

**Path Aliases:**
- Not detected. Runtime paths are built from `__file__`, environment variables, and the active `web/` and `server/` symlinks in `script/http_server.py` and `script/start_server.sh`.

## Error Handling

**Patterns:**
- Shell entrypoints use `set -e` and explicit validation with an error message plus `exit 1` in `build.sh` and `script/start_server.sh`.
- `script/start_server.sh` validates required `MINECRAFT_VERSION`, allowed versions, and required version directories before mutating symlinks.
- Python request handlers translate malformed JSON and missing fields into HTTP 400, authentication failures into 403, and downstream RCON/Dynmap failures into 500/502 or retry-aware 503 responses in `script/http_server.py`.
- Python domain helpers raise `ValueError`/`RuntimeError` with user-facing messages; handlers catch boundary failures and serialize `{'success': False, 'error': ...}`.
- JavaScript async actions use `try/catch`, restore UI state on failure, and display errors through `log()` and `toast()` in `web-1.12/admin.js`.

## Logging

**Framework:** `print` in Python and JavaScript browser console/UI logging.

**Patterns:**
- HTTP access messages are formatted with the `[http:5201]` prefix by `Handler.log_message()` in `script/http_server.py`.
- Startup diagnostics use `[start]` prefixes in `script/start_server.sh`.
- The admin panel writes operational feedback to its in-page console via `log()` and transient notifications via `toast()` in `web-1.12/admin.js`.
- Preserve secrets out of logs; the existing API returns status and errors while keeping the RCON password out of response payloads.

## Comments

**When to Comment:**
- Comments explain deployment constraints and compatibility behavior, such as the legacy world-only persistence block in `script/start_server.sh`.
- Python module and section comments document externally visible server behavior, such as the port/API purpose at the top of `script/http_server.py`.
- Existing comments may be bilingual; retain concise comments for operational caveats rather than narrating obvious code.

**JSDoc/TSDoc:**
- Not detected. JavaScript behavior is communicated through function names and UI strings in `web-1.12/admin.js`.

## Function Design

**Size:** Small helpers isolate file parsing, validation, RCON packets, caching, and HTTP endpoint handling in `script/http_server.py`; endpoint methods remain grouped on `Handler`.

**Parameters:** Functions pass focused scalar values or small dictionaries. Configuration validation is centralized in `normalize_config_value()` and `MANAGED_CONFIG` in `script/http_server.py`.

**Return Values:** Helpers return plain dictionaries, lists, strings, booleans, or `None`; HTTP methods respond through `_json()` and do not return response objects.

## Module Design

**Exports:** There are no Python package exports. `script/http_server.py` is an executable module with module-level configuration, helpers, `Handler`, and a `__main__` startup block.

**Barrel Files:** Not detected.

---

*Convention analysis: 2026-08-19*
