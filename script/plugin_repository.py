#!/usr/bin/env python3
"""Persistent, version-scoped Paper plugin repository primitives."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import re
import tempfile
import uuid
import zipfile


VALID_VERSIONS = ("1.8", "1.12")
UPLOAD_LIMIT = 64 * 1024 * 1024
UPLOAD_TEMP_PREFIX = ".plugin-upload-"
UPLOAD_TEMP_SUFFIX = ".tmp"
MAX_PLUGIN_FILENAME_LENGTH = 255
MARKER_FILENAME = ".eaglerx-plugin-repository"
PENDING_RESTART_FILENAME = ".pending-restart"
LOCK_FILENAME = ".operation.lock"
REPOSITORY_SCHEMA = 1
INTERNAL_NAMES = frozenset({MARKER_FILENAME, PENDING_RESTART_FILENAME, LOCK_FILENAME, "enabled", "disabled"})

_operation_locks = {}
_operation_locks_guard = threading.Lock()


class RepositoryError(RuntimeError):
    """Raised when a repository cannot be prepared or safely inspected."""


class PluginUploadError(RepositoryError):
    """Raised when a custom plugin package cannot be published."""

    code = "plugin_upload_failed"


class PluginFilenameError(PluginUploadError):
    code = "invalid_filename"


class PluginArchiveError(PluginUploadError):
    code = "invalid_archive"


class PluginConflictError(PluginUploadError):
    code = "duplicate_filename"


_UPLOAD_TEMP_NAME_RE = re.compile(
    rf"^{re.escape(UPLOAD_TEMP_PREFIX)}[A-Za-z0-9_-]+{re.escape(UPLOAD_TEMP_SUFFIX)}$"
)


def validate_version(version):
    version = str(version or "").strip()
    if version not in VALID_VERSIONS:
        raise RepositoryError(f"unsupported Minecraft version: {version or '<empty>'}")
    return version


def repository_path(data_root, version):
    version = validate_version(version)
    root = Path(data_root).expanduser()
    if not str(root):
        raise RepositoryError("persistent data root is required")
    return root / f"plugins-{version}"


def repository_paths(repository):
    repository = Path(repository)
    return {
        "root": repository,
        "enabled": repository / "enabled",
        "disabled": repository / "disabled",
        "marker": repository / MARKER_FILENAME,
        "pending_restart": repository / PENDING_RESTART_FILENAME,
        "lock": repository / LOCK_FILENAME,
    }


def _lexists(path):
    return os.path.lexists(os.fspath(path))


def _is_upload_temp_name(name):
    return bool(_UPLOAD_TEMP_NAME_RE.fullmatch(str(name or "")))


def _safe_name(name, allow_internal=False):
    if not name or name in {".", ".."}:
        return False
    if "/" in name or "\\" in name or "\x00" in name:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        return False
    if name.startswith(".") and not (
        allow_internal and (name in INTERNAL_NAMES or _is_upload_temp_name(name))
    ):
        return False
    return True


def validate_plugin_filename(name):
    """Validate the single flat filename accepted by the upload boundary."""

    if not isinstance(name, str) or not name or name != name.strip():
        raise PluginFilenameError("plugin filename must be a plain basename")
    if len(name) > MAX_PLUGIN_FILENAME_LENGTH:
        raise PluginFilenameError("plugin filename is too long")
    if not _safe_name(name) or name.startswith("."):
        raise PluginFilenameError("plugin filename contains an unsafe character")
    if not name.endswith(".jar"):
        raise PluginFilenameError("plugin filename must end with lowercase .jar")
    if name.casefold() in {reserved.casefold() for reserved in INTERNAL_NAMES}:
        raise PluginFilenameError("plugin filename collides with repository state")
    return name


def validate_plugin_archive(path):
    """Require a readable ZIP/JAR containing one readable root-level plugin.yml."""

    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise PluginArchiveError("plugin package is not a regular file")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            plugin_descriptors = [
                info for info in archive.infolist()
                if info.filename == "plugin.yml" and not info.is_dir()
            ]
            if len(plugin_descriptors) != 1:
                raise PluginArchiveError("plugin package must contain one root-level plugin.yml")
            descriptor = plugin_descriptors[0]
            # ZIP symlink entries can point outside an eventual extraction target.
            if (descriptor.external_attr >> 16) & 0o170000 == 0o120000:
                raise PluginArchiveError("plugin descriptor is not a regular archive entry")
            with archive.open(descriptor, "r") as stream:
                while stream.read(1024 * 1024):
                    pass
            if archive.testzip() is not None:
                raise PluginArchiveError("plugin package contains unreadable archive data")
    except PluginArchiveError:
        raise
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise PluginArchiveError("plugin package must be a readable JAR archive") from error
    return True


def _ensure_real_directory(path, label):
    path = Path(path)
    if _lexists(path) and (path.is_symlink() or not path.is_dir()):
        raise RepositoryError(f"{label} is not a real directory")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise RepositoryError(f"cannot create {label}: {error.strerror or error}") from error
    if path.is_symlink() or not path.is_dir():
        raise RepositoryError(f"{label} is not a real directory")
    return path


def _validate_tree(path, label):
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        raise RepositoryError(f"{label} is not a real directory")
    for current, directories, files in os.walk(path, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in list(directories) + list(files):
            if not _safe_name(name):
                raise RepositoryError(f"unsafe entry in {label}: {name!r}")
            candidate = current_path / name
            if candidate.is_symlink():
                raise RepositoryError(f"symlink entry in {label}: {name!r}")
            try:
                candidate.stat(follow_symlinks=False)
            except OSError as error:
                raise RepositoryError(f"cannot inspect {label}: {error.strerror or error}") from error
            if not (candidate.is_dir() or candidate.is_file()):
                raise RepositoryError(f"unsupported entry in {label}: {name!r}")


def _validate_repository_layout(repository, version=None):
    paths = repository_paths(repository)
    root = paths["root"]
    if root.is_symlink() or not root.is_dir():
        raise RepositoryError("plugin repository is not a real directory")
    marker = paths["marker"]
    if marker.is_symlink() or not marker.is_file():
        raise RepositoryError("plugin repository marker is missing or unsafe")
    try:
        marker_data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RepositoryError("plugin repository marker is malformed") from error
    if not isinstance(marker_data, dict):
        raise RepositoryError("plugin repository marker is malformed")
    if marker_data.get("schema") != REPOSITORY_SCHEMA:
        raise RepositoryError("plugin repository marker has an unsupported schema")
    if version is not None and marker_data.get("minecraft_version") != validate_version(version):
        raise RepositoryError("plugin repository marker has the wrong Minecraft version")
    for entry in root.iterdir():
        if (
            entry.name not in INTERNAL_NAMES
            and not _is_upload_temp_name(entry.name)
        ) or not _safe_name(entry.name, allow_internal=True):
            raise RepositoryError("plugin repository contains unsafe or incomplete entries")
        if _is_upload_temp_name(entry.name) and (entry.is_symlink() or not entry.is_file()):
            raise RepositoryError("plugin repository contains unsafe upload state")
    for key in ("enabled", "disabled"):
        _ensure_real_directory(paths[key], f"plugin repository {key} state")
        _validate_tree(paths[key], f"plugin repository {key} state")
    return paths


def _repository_lock(repository):
    key = os.path.abspath(os.fspath(repository))
    with _operation_locks_guard:
        lock = _operation_locks.setdefault(key, threading.RLock())
    return lock


@contextmanager
def operation_lock(repository):
    """Serialize repository operations in-process and across helper processes."""

    repository = Path(repository)
    lock = _repository_lock(repository)
    with lock:
        _ensure_real_directory(repository, "plugin repository")
        lock_path = repository / LOCK_FILENAME
        try:
            with lock_path.open("a+", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError as error:
            raise RepositoryError(f"cannot lock plugin repository: {error.strerror or error}") from error


def _copy_entry(source, destination):
    source = Path(source)
    destination = Path(destination)
    temporary = destination.parent / f".{destination.name}.migration-{os.getpid()}-{uuid.uuid4().hex}"
    try:
        if source.is_dir():
            shutil.copytree(source, temporary, symlinks=False)
        else:
            shutil.copy2(source, temporary, follow_symlinks=False)
        if _lexists(destination):
            raise RepositoryError(f"migration destination appeared during copy: {destination.name}")
        os.replace(temporary, destination)
    except RepositoryError:
        raise
    except (OSError, shutil.Error) as error:
        raise RepositoryError(f"plugin repository migration failed for {source.name}: {error}") from error
    finally:
        if _lexists(temporary):
            if temporary.is_dir() and not temporary.is_symlink():
                shutil.rmtree(temporary, ignore_errors=True)
            else:
                try:
                    temporary.unlink()
                except OSError:
                    pass


def _write_json_atomic(path, payload):
    path = Path(path)
    temporary = path.parent / f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise RepositoryError(f"cannot persist plugin repository state: {error.strerror or error}") from error
    finally:
        if _lexists(temporary):
            try:
                temporary.unlink()
            except OSError:
                pass


def create_upload_temp(repository):
    """Create a private temporary upload artifact inside a validated repository."""

    repository = Path(repository)
    _validate_repository_layout(repository)
    try:
        fd, temporary = tempfile.mkstemp(
            prefix=UPLOAD_TEMP_PREFIX,
            suffix=UPLOAD_TEMP_SUFFIX,
            dir=os.fspath(repository),
        )
        os.close(fd)
        return Path(temporary)
    except OSError as error:
        raise PluginUploadError("cannot create upload temporary artifact") from error


def _remove_file(path):
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass


def _find_existing_plugin(repository_paths_data, filename):
    target_name = filename.casefold()
    for state in ("enabled", "disabled"):
        for entry in repository_paths_data[state].iterdir():
            if entry.name.casefold() == target_name:
                return entry
    return None


def _mark_pending_restart_locked(repository, reason):
    _write_json_atomic(repository_paths(repository)["pending_restart"], {
        "schema": 1,
        "reason": str(reason),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })


def publish_uploaded_plugin(repository, filename, temporary, version):
    """Validate and atomically publish one temporary upload under the repository lock."""

    version = validate_version(version)
    filename = validate_plugin_filename(filename)
    repository = Path(repository)
    temporary = Path(temporary)
    published = False
    try:
        if temporary.parent != repository or not temporary.is_file() or temporary.is_symlink():
            raise PluginUploadError("upload temporary artifact is invalid")
        if not _is_upload_temp_name(temporary.name):
            raise PluginUploadError("upload temporary artifact is invalid")
        validate_plugin_archive(temporary)

        with operation_lock(repository):
            paths = _validate_repository_layout(repository, version)
            if _find_existing_plugin(paths, filename) is not None:
                raise PluginConflictError("plugin filename already exists")
            target = paths["enabled"] / filename
            if _lexists(target):
                raise PluginConflictError("plugin filename already exists")
            try:
                os.replace(temporary, target)
                published = True
                try:
                    _mark_pending_restart_locked(repository, "plugin package uploaded")
                except Exception:
                    _remove_file(target)
                    published = False
                    raise
            except PluginUploadError:
                raise
            except OSError as error:
                raise PluginUploadError("cannot publish plugin package") from error

            stat = target.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")
            return {
                "filename": filename,
                "enabled": True,
                "size": stat.st_size,
                "bytes": stat.st_size,
                "modified_at": modified_at,
                "modified_time": modified_at,
                "mtime": stat.st_mtime,
                "pending_restart": True,
            }
    finally:
        if not published:
            _remove_file(temporary)


def init_repository(source, repository, version):
    """Copy bundled packages/data into an unmarked repository, then mark it authoritative."""

    version = validate_version(version)
    source = Path(source)
    repository = Path(repository)
    if _lexists(repository) and (repository.is_symlink() or not repository.is_dir()):
        raise RepositoryError("plugin repository path is a file or symlink")
    repository.parent.mkdir(parents=True, exist_ok=True)
    repository.mkdir(parents=True, exist_ok=True)

    marker = repository / MARKER_FILENAME
    if _lexists(marker):
        _validate_repository_layout(repository, version)
        return repository

    if source.is_symlink() or not source.is_dir():
        raise RepositoryError("bundled plugin source is missing or unsafe")
    _validate_tree(source, "bundled plugin source")

    try:
        with operation_lock(repository):
            if _lexists(marker):
                _validate_repository_layout(repository, version)
                return repository
            paths = repository_paths(repository)
            for entry in repository.iterdir():
                if entry.name not in INTERNAL_NAMES or not _safe_name(entry.name, allow_internal=True):
                    raise RepositoryError("plugin repository contains unsafe or incomplete entries")
            enabled = _ensure_real_directory(paths["enabled"], "plugin repository enabled state")
            disabled = _ensure_real_directory(paths["disabled"], "plugin repository disabled state")
            _validate_tree(enabled, "plugin repository enabled state")
            _validate_tree(disabled, "plugin repository disabled state")

            for source_entry in sorted(source.iterdir(), key=lambda item: item.name.casefold()):
                if not _safe_name(source_entry.name):
                    raise RepositoryError(f"unsafe bundled plugin entry: {source_entry.name!r}")
                enabled_target = enabled / source_entry.name
                disabled_target = disabled / source_entry.name
                if _lexists(enabled_target) or _lexists(disabled_target):
                    continue
                _copy_entry(source_entry, enabled_target)

            _write_json_atomic(marker, {
                "schema": REPOSITORY_SCHEMA,
                "minecraft_version": version,
                "initialized_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            })
            _validate_repository_layout(repository, version)
            return repository
    except RepositoryError:
        raise
    except OSError as error:
        raise RepositoryError(f"plugin repository initialization failed: {error.strerror or error}") from error


def activate_repository(source, repository, version):
    """Make the selected Paper server's plugins path point at the enabled state."""

    version = validate_version(version)
    paths = _validate_repository_layout(repository, version)
    source = Path(source)
    expected = paths["enabled"].resolve()
    source.parent.mkdir(parents=True, exist_ok=True)

    if source.is_symlink():
        if source.resolve() == expected:
            return source
        source.unlink()
    elif _lexists(source):
        if source.is_dir():
            backup = source.parent / f".plugins-image-{version}"
            if _lexists(backup):
                backup = source.parent / f".plugins-image-{version}-{uuid.uuid4().hex[:8]}"
            try:
                os.replace(source, backup)
            except OSError as error:
                raise RepositoryError(f"cannot preserve bundled plugin source: {error.strerror or error}") from error
        else:
            raise RepositoryError("Paper plugins path is a file")

    try:
        os.symlink(os.fspath(expected), source)
    except OSError as error:
        raise RepositoryError(f"cannot activate persistent plugin repository: {error.strerror or error}") from error
    if source.resolve() != expected:
        raise RepositoryError("persistent plugin repository activation verification failed")
    return source


def list_repository(repository, version):
    version = validate_version(version)
    paths = _validate_repository_layout(repository, version)
    entries = {}
    for enabled in (True, False):
        state_path = paths["enabled"] if enabled else paths["disabled"]
        for item in state_path.iterdir():
            if not _safe_name(item.name) or not item.name.casefold().endswith(".jar"):
                continue
            if item.is_symlink() or not item.is_file():
                raise RepositoryError(f"unsafe plugin package entry: {item.name!r}")
            if item.name in entries:
                raise RepositoryError(f"plugin package has duplicate repository state: {item.name!r}")
            stat = item.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat().replace("+00:00", "Z")
            entries[item.name] = {
                "filename": item.name,
                "enabled": enabled,
                "size": stat.st_size,
                "bytes": stat.st_size,
                "modified_at": modified_at,
                "modified_time": modified_at,
                "mtime": stat.st_mtime,
            }
    return sorted(entries.values(), key=lambda entry: entry["filename"].casefold())


def pending_restart(repository):
    paths = repository_paths(repository)
    marker = paths["pending_restart"]
    if marker.is_symlink():
        raise RepositoryError("pending restart marker is unsafe")
    return marker.is_file()


def mark_pending_restart(repository, reason="plugin repository changed"):
    repository = Path(repository)
    _validate_repository_layout(repository)
    with operation_lock(repository):
        _mark_pending_restart_locked(repository, reason)


def clear_pending_restart(repository):
    repository = Path(repository)
    _validate_repository_layout(repository)
    with operation_lock(repository):
        marker = repository / PENDING_RESTART_FILENAME
        if marker.is_symlink():
            raise RepositoryError("pending restart marker is unsafe")
        try:
            marker.unlink(missing_ok=True)
        except OSError as error:
            raise RepositoryError(f"cannot clear pending restart marker: {error.strerror or error}") from error


def _cli():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--source", required=True)
    init_parser.add_argument("--repository", required=True)
    init_parser.add_argument("--version", required=True)

    activate_parser = subparsers.add_parser("activate")
    activate_parser.add_argument("--source", required=True)
    activate_parser.add_argument("--repository", required=True)
    activate_parser.add_argument("--version", required=True)

    args = parser.parse_args()
    try:
        if args.command == "init":
            init_repository(args.source, args.repository, args.version)
            print(f"[plugins] repository initialized for Minecraft {validate_version(args.version)}")
        else:
            activate_repository(args.source, args.repository, args.version)
            print(f"[plugins] persistent repository active for Minecraft {validate_version(args.version)}")
        return 0
    except RepositoryError as error:
        print(f"[plugins] ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
