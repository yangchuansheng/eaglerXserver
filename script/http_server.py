#!/usr/bin/env python3
"""
HTTP Server — 端口 5201
- 静态文件服务（回退用）
- RCON 桥接 API（仅当设置 RCON_PASSWORD 环境变量时启用）
"""

import json
import os
import socket
import struct
import time
import gzip
import base64
import hmac
import hashlib
import subprocess
import re
import math
import ctypes
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from http.client import HTTPConnection
from urllib.parse import urlparse

PORT = 5201
WEB_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web')
SERVER_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server')

RCON_HOST = '127.0.0.1'
RCON_PORT = 25575
RCON_PASSWORD = os.environ.get('RCON_PASSWORD', '')
RCON_ENABLED = bool(RCON_PASSWORD)
MINECRAFT_VERSION = os.environ.get('MINECRAFT_VERSION', '')
DYNMAP_HOST = os.environ.get('DYNMAP_HOST', '127.0.0.1')
DYNMAP_PORT = int(os.environ.get('DYNMAP_PORT', '8123'))
AUTH_TOKEN_TTL = int(os.environ.get('ADMIN_AUTH_TOKEN_TTL', str(30 * 24 * 3600)))
_auth_secret_seed = os.environ.get('ADMIN_AUTH_SECRET') or f'eaglerx-admin::{RCON_PASSWORD}'
AUTH_SECRET = hashlib.sha256(_auth_secret_seed.encode('utf-8')).digest()
TMUX_SESSION = os.environ.get('TMUX_SESSION', 'mcserver')
SERVER_PANE = os.environ.get('TMUX_SERVER_PANE', f'{TMUX_SESSION}:0.1')
CUBIOMES_SHIM_PATH = os.environ.get('CUBIOMES_SHIM_PATH', '/usr/local/lib/libcubiomes_shim.so')
RCON_CONNECT_INTERVAL = float(os.environ.get('RCON_CONNECT_INTERVAL', '0.08'))
RCON_SOCKET_TIMEOUT = float(os.environ.get('RCON_SOCKET_TIMEOUT', '5'))

MIN_LONG = -(1 << 63)
MAX_LONG = (1 << 63) - 1

CUBIOMES_MC_VERSIONS = {
    '1.8': 11,
    '1.12': 15,
}

STRUCTURE_DEFS = [
    {'key': 'village', 'label': '村庄', 'type': 5},
    {'key': 'stronghold', 'label': '要塞（末地传送门）', 'type': None},
    {'key': 'desert_pyramid', 'label': '沙漠神殿', 'type': 1},
    {'key': 'monument', 'label': '海底神殿', 'type': 8},
    {'key': 'jungle_temple', 'label': '丛林神庙', 'type': 2},
    {'key': 'swamp_hut', 'label': '女巫小屋', 'type': 3},
    {'key': 'igloo', 'label': '雪屋', 'type': 4},
    {'key': 'mansion', 'label': '林地府邸', 'type': 9},
]

STRONGHOLD_COUNTS = {
    '1.8': 3,
    '1.12': 128,
}

MAX_STRUCTURE_RADIUS = 50000
MIN_STRUCTURE_RADIUS = 256
DEFAULT_STRUCTURE_RADIUS = 5000
DEFAULT_STRUCTURE_LIMIT = 8
MAX_STRUCTURE_LIMIT = 20

_cubiomes_bridge = None
_cubiomes_bridge_error = None
PLAYER_MARKER_CACHE_TTL = 2.0
_player_marker_cache = {
    'expires_at': 0.0,
    'players': [],
}
WORLD_STATE_CACHE_TTL = 1.5
_world_state_cache = {
    'expires_at': 0.0,
    'value': None,
}
_runtime_flags = {
    'save_enabled': True,
    'whitelist_enabled': None,
}

PANEL_GAMERULES = [
    'doDaylightCycle',
    'doWeatherCycle',
    'doFireTick',
    'doMobSpawning',
    'doMobLoot',
    'doEntityDrops',
    'doTileDrops',
    'keepInventory',
    'mobGriefing',
    'naturalRegeneration',
    'commandBlockOutput',
    'showDeathMessages',
]

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}

MANAGED_CONFIG = {
    'pvp': {'type': 'bool'},
    'allow-flight': {'type': 'bool'},
    'enable-command-block': {'type': 'bool'},
    'spawn-monsters': {'type': 'bool'},
    'spawn-animals': {'type': 'bool'},
    'spawn-npcs': {'type': 'bool'},
    'hardcore': {'type': 'bool'},
    'motd': {'type': 'str', 'max_length': 120},
    'max-players': {'type': 'int', 'min': 1, 'max': 200},
    'view-distance': {'type': 'int', 'min': 2, 'max': 32},
    'spawn-protection': {'type': 'int', 'min': 0, 'max': 128},
}


class CubiomesPos(ctypes.Structure):
    _fields_ = [
        ('x', ctypes.c_int),
        ('z', ctypes.c_int),
    ]


class CubiomesStructureConfig(ctypes.Structure):
    _fields_ = [
        ('salt', ctypes.c_int32),
        ('region_size', ctypes.c_int8),
        ('chunk_range', ctypes.c_int8),
        ('struct_type', ctypes.c_uint8),
        ('dim', ctypes.c_int8),
        ('rarity', ctypes.c_float),
    ]


class CubiomesBridge:
    def __init__(self, library_path):
        self.library_path = library_path
        self.lib = ctypes.CDLL(library_path)

        self.lib.cm_get_structure_config.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(CubiomesStructureConfig),
        ]
        self.lib.cm_get_structure_config.restype = ctypes.c_int

        self.lib.cm_get_structure_pos.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(CubiomesPos),
        ]
        self.lib.cm_get_structure_pos.restype = ctypes.c_int

        self.lib.cm_is_structure_viable.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint32,
        ]
        self.lib.cm_is_structure_viable.restype = ctypes.c_int

        self.lib.cm_get_spawn.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_int,
            ctypes.POINTER(CubiomesPos),
        ]
        self.lib.cm_get_spawn.restype = ctypes.c_int

        self.lib.cm_get_strongholds.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_int,
            ctypes.POINTER(CubiomesPos),
        ]
        self.lib.cm_get_strongholds.restype = ctypes.c_int

    def get_structure_config(self, mc_version, structure_type):
        config = CubiomesStructureConfig()
        if not self.lib.cm_get_structure_config(mc_version, structure_type, ctypes.byref(config)):
            return None
        return {
            'salt': int(config.salt),
            'region_size': int(config.region_size),
            'chunk_range': int(config.chunk_range),
            'struct_type': int(config.struct_type),
            'dim': int(config.dim),
            'rarity': float(config.rarity),
        }

    def get_structure_pos(self, mc_version, seed, structure_type, region_x, region_z):
        pos = CubiomesPos()
        if not self.lib.cm_get_structure_pos(mc_version, structure_type, seed, region_x, region_z, ctypes.byref(pos)):
            return None
        return {'x': int(pos.x), 'z': int(pos.z)}

    def is_structure_viable(self, mc_version, seed, structure_type, block_x, block_z, flags=0):
        return bool(self.lib.cm_is_structure_viable(mc_version, seed, structure_type, block_x, block_z, flags))

    def get_spawn(self, mc_version, seed, approx=True):
        pos = CubiomesPos()
        if not self.lib.cm_get_spawn(mc_version, seed, 1 if approx else 0, ctypes.byref(pos)):
            return None
        return {'x': int(pos.x), 'z': int(pos.z)}

    def get_strongholds(self, mc_version, seed, count):
        if count <= 0:
            return []
        buf = (CubiomesPos * count)()
        written = int(self.lib.cm_get_strongholds(mc_version, seed, count, buf))
        return [
            {'x': int(buf[i].x), 'z': int(buf[i].z)}
            for i in range(max(0, written))
        ]


def _server_properties_path():
    return os.path.join(SERVER_ROOT, 'server.properties')


def read_server_properties():
    props = {}
    path = _server_properties_path()
    if not os.path.exists(path):
        return props
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            props[key] = value
    return props


def get_level_name():
    level_name = str(read_server_properties().get('level-name', '')).strip()
    return level_name or 'world'


def get_level_world_dir():
    return os.path.join(SERVER_ROOT, get_level_name())


def get_level_playerdata_dir():
    return os.path.join(get_level_world_dir(), 'playerdata')


def write_server_properties(updates):
    path = _server_properties_path()
    lines = []
    seen = set()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for raw in f.readlines():
                line = raw.rstrip('\n')
                if '=' in line and not line.startswith('#'):
                    key, _ = line.split('=', 1)
                    if key in updates:
                        lines.append(f'{key}={updates[key]}\n')
                        seen.add(key)
                    else:
                        lines.append(raw)
                else:
                    lines.append(raw)
    for key, value in updates.items():
        if key not in seen:
            lines.append(f'{key}={value}\n')
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def normalize_config_value(key, value):
    spec = MANAGED_CONFIG[key]
    if spec['type'] == 'bool':
        if isinstance(value, bool):
            return 'true' if value else 'false'
        value = str(value).strip().lower()
        if value not in ('true', 'false'):
            raise ValueError(f'{key} must be true/false')
        return value
    if spec['type'] == 'int':
        iv = int(str(value).strip())
        if iv < spec['min'] or iv > spec['max']:
            raise ValueError(f'{key} out of range ({spec["min"]}-{spec["max"]})')
        return str(iv)
    if spec['type'] == 'str':
        sv = str(value).replace('\r', ' ').replace('\n', ' ').strip()
        if len(sv) > spec.get('max_length', 255):
            raise ValueError(f'{key} too long')
        return sv
    raise ValueError(f'unsupported config type for {key}')


def get_managed_config_values():
    props = read_server_properties()
    result = {}
    for key in MANAGED_CONFIG:
        result[key] = props.get(key, '')
    return result


def extract_seed_value(raw):
    text = str(raw or '').strip()
    if not text:
        return ''
    match = re.search(r'-?\d+', text)
    return match.group(0) if match else ''


def resolve_world_seed():
    last_error = ''
    if RCON_ENABLED:
        try:
            response = rcon_send('seed')
            seed = extract_seed_value(response)
            if seed:
                return {
                    'seed': seed,
                    'source': 'rcon',
                }
            last_error = response or 'seed unavailable'
        except Exception as e:
            last_error = str(e)

    props = read_server_properties()
    configured_seed = str(props.get('level-seed', '')).strip()
    if configured_seed:
        return {
            'seed': configured_seed,
            'source': 'server.properties',
        }

    raise RuntimeError(last_error or 'seed unavailable')


def clamp_int(value, default, min_value, max_value):
    try:
        ivalue = int(str(value).strip())
    except Exception:
        ivalue = default
    return max(min_value, min(max_value, ivalue))


def java_string_hashcode(text):
    value = 0
    for ch in text:
        value = (31 * value + ord(ch)) & 0xffffffff
    if value >= 0x80000000:
        value -= 0x100000000
    return value


def resolve_numeric_world_seed(seed_text):
    text = str(seed_text or '').strip()
    if not text:
        raise ValueError('seed unavailable')
    try:
        value = int(text, 10)
        if MIN_LONG <= value <= MAX_LONG:
            return value, 'numeric'
    except ValueError:
        pass
    return java_string_hashcode(text), 'string-hash'


def get_cubiomes_bridge():
    global _cubiomes_bridge, _cubiomes_bridge_error
    if _cubiomes_bridge is not None:
        return _cubiomes_bridge
    if _cubiomes_bridge_error is not None:
        raise RuntimeError(_cubiomes_bridge_error)
    if not os.path.exists(CUBIOMES_SHIM_PATH):
        _cubiomes_bridge_error = f'cubiomes shim not found: {CUBIOMES_SHIM_PATH}'
        raise RuntimeError(_cubiomes_bridge_error)
    try:
        _cubiomes_bridge = CubiomesBridge(CUBIOMES_SHIM_PATH)
        return _cubiomes_bridge
    except Exception as e:
        _cubiomes_bridge_error = f'failed to load cubiomes shim: {e}'
        raise RuntimeError(_cubiomes_bridge_error)


def _distance_to(center_x, center_z, x, z):
    return int(round(math.hypot(x - center_x, z - center_z)))


def _region_bounds(center, radius, region_size):
    region_blocks = int(region_size) * 16
    min_region = (center - radius) // region_blocks
    max_region = (center + radius) // region_blocks
    return min_region, max_region, region_blocks


def _search_structure_group(bridge, cubiomes_mc, seed_value, center_x, center_z, radius, limit_per_type, struct_def):
    config = bridge.get_structure_config(cubiomes_mc, struct_def['type'])
    if not config:
        return None

    min_region_x, max_region_x, region_blocks = _region_bounds(center_x, radius, config['region_size'])
    min_region_z, max_region_z, _ = _region_bounds(center_z, radius, config['region_size'])

    entries = []
    for region_x in range(min_region_x, max_region_x + 1):
        for region_z in range(min_region_z, max_region_z + 1):
            pos = bridge.get_structure_pos(cubiomes_mc, seed_value, struct_def['type'], region_x, region_z)
            if not pos:
                continue
            distance = _distance_to(center_x, center_z, pos['x'], pos['z'])
            if distance > radius:
                continue
            if not bridge.is_structure_viable(cubiomes_mc, seed_value, struct_def['type'], pos['x'], pos['z'], 0):
                continue
            entries.append({
                'x': pos['x'],
                'z': pos['z'],
                'distance': distance,
                'region_x': region_x,
                'region_z': region_z,
            })

    if not entries:
        return None

    entries.sort(key=lambda item: (item['distance'], item['x'], item['z']))
    return {
        'key': struct_def['key'],
        'label': struct_def['label'],
        'region_size_blocks': region_blocks,
        'total_found': len(entries),
        'entries': entries[:limit_per_type],
    }


def build_structure_search(seed_info, mc_version, center_x, center_z, radius, limit_per_type):
    if mc_version not in CUBIOMES_MC_VERSIONS:
        raise RuntimeError(f'unsupported minecraft version: {mc_version}')

    bridge = get_cubiomes_bridge()
    cubiomes_mc = CUBIOMES_MC_VERSIONS[mc_version]
    numeric_seed, numeric_seed_kind = resolve_numeric_world_seed(seed_info['seed'])
    structure_labels = {item['key']: item['label'] for item in STRUCTURE_DEFS}

    groups = []
    total_matches = 0
    for struct_def in STRUCTURE_DEFS:
        if struct_def['key'] == 'stronghold':
            continue
        group = _search_structure_group(
            bridge,
            cubiomes_mc,
            numeric_seed,
            center_x,
            center_z,
            radius,
            limit_per_type,
            struct_def,
        )
        if group:
            total_matches += group['total_found']
            groups.append(group)

    strongholds = []
    for pos in bridge.get_strongholds(cubiomes_mc, numeric_seed, STRONGHOLD_COUNTS.get(mc_version, 0)):
        distance = _distance_to(center_x, center_z, pos['x'], pos['z'])
        if distance > radius:
            continue
        strongholds.append({
            'x': pos['x'],
            'z': pos['z'],
            'distance': distance,
        })
    if strongholds:
        strongholds.sort(key=lambda item: (item['distance'], item['x'], item['z']))
        groups.append({
            'key': 'stronghold',
            'label': structure_labels.get('stronghold', '要塞'),
            'total_found': len(strongholds),
            'entries': strongholds[:limit_per_type],
        })
        total_matches += len(strongholds)

    spawn = bridge.get_spawn(cubiomes_mc, numeric_seed, approx=True)
    if spawn:
        spawn['distance'] = _distance_to(center_x, center_z, spawn['x'], spawn['z'])

    ordered_groups = []
    for struct_def in STRUCTURE_DEFS:
        matched = None
        for group in groups:
            if group['key'] == struct_def['key']:
                matched = group
                break
        if matched:
            ordered_groups.append(matched)

    return {
        'seed': seed_info['seed'],
        'seed_source': seed_info['source'],
        'effective_seed': str(numeric_seed),
        'effective_seed_kind': numeric_seed_kind,
        'minecraft_version': mc_version,
        'center': {'x': center_x, 'z': center_z},
        'radius': radius,
        'limit_per_type': limit_per_type,
        'spawn': spawn,
        'groups': ordered_groups,
        'total_matches': total_matches,
    }


def _read_json_file(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _find_player_cache_entry(player_name):
    target = str(player_name or '').strip()
    if not target:
        raise RuntimeError('player name required')
    usercache_path = os.path.join(SERVER_ROOT, 'usercache.json')
    entries = _read_json_file(usercache_path, [])
    if not isinstance(entries, list):
        entries = []

    exact = None
    lower_target = target.lower()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get('name') or '').strip()
        if not name:
            continue
        if name == target:
            exact = entry
            break
        if exact is None and name.lower() == lower_target:
            exact = entry
    if exact:
        return exact
    raise RuntimeError(f'在 usercache.json 里没找到玩家“{target}”')


def _parse_online_player_names(list_response):
    text = str(list_response or '').strip()
    if not text:
        return []
    if ':' not in text:
        return []
    names_part = text.split(':', 1)[1].strip()
    if not names_part:
        return []
    result = []
    seen = set()
    for raw in names_part.split(','):
        name = str(raw or '').strip()
        if not name:
            continue
        lower = name.lower()
        if lower in seen:
            continue
        seen.add(lower)
        result.append(name)
    return result


def _list_online_players():
    if not RCON_ENABLED:
        return []
    try:
        response = rcon_send('list', retries=1)
    except Exception:
        return []
    return _parse_online_player_names(response)


def _build_dynmap_player_markers():
    global _player_marker_cache
    now = time.time()
    if _player_marker_cache['expires_at'] > now:
        return list(_player_marker_cache['players'])

    players = []
    online_names = _list_online_players()
    if online_names:
        try:
            rcon_send('save-all', retries=1)
            time.sleep(0.2)
        except Exception:
            pass

    for name in online_names:
        location = None
        try:
            location = _resolve_player_location_from_playerdata(name)
        except Exception:
            try:
                location = _resolve_player_location_from_dynmap(name)
            except Exception:
                location = None
        if not location:
            continue
        players.append({
            'type': 'player',
            'name': location['name'],
            'account': location['name'],
            'world': location['world'],
            'x': location['x'],
            'y': location['y'],
            'z': location['z'],
            'health': 20,
            'armor': 0,
            'sort': 0,
        })

    _player_marker_cache = {
        'expires_at': now + PLAYER_MARKER_CACHE_TTL,
        'players': players,
    }
    return list(players)


def _patch_dynmap_world_state(target_path, body):
    if not target_path.startswith('/up/world/'):
        return body
    parts = target_path.split('?', 1)[0].strip('/').split('/')
    if len(parts) < 4:
        return body
    world_name = str(parts[2] or '').strip()
    if not world_name:
        return body
    try:
        world_state = json.loads(body.decode('utf-8', errors='replace'))
    except Exception:
        return body
    if not isinstance(world_state, dict):
        return body

    dynmap_players = world_state.get('players')
    dynmap_players = dynmap_players if isinstance(dynmap_players, list) else []
    merged = []
    seen = set()
    for player in dynmap_players:
        if not isinstance(player, dict):
            continue
        name = str(player.get('account') or player.get('name') or '').strip().lower()
        if name:
            seen.add(name)
        merged.append(player)

    for player in _build_dynmap_player_markers():
        if str(player.get('world') or '').strip() != world_name:
            continue
        key = str(player.get('account') or player.get('name') or '').strip().lower()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        merged.append(player)

    world_state['players'] = merged
    return json.dumps(world_state, ensure_ascii=False).encode('utf-8')


def _query_daytime_via_rcon():
    response = str(rcon_send('time query daytime', retries=1) or '')
    matches = re.findall(r'\d+', response)
    if not matches:
        raise RuntimeError('unable to parse daytime from rcon response')
    return int(matches[-1])


def _parse_bool_from_output(raw):
    text = str(raw or '').strip().lower()
    match = re.search(r'\b(true|false)\b', text)
    if match:
        return match.group(1) == 'true'
    if 'enabled' in text:
        return True
    if 'disabled' in text:
        return False
    raise RuntimeError(f'unable to parse bool from response: {raw}')


def _query_gamerule_value(name):
    return _parse_bool_from_output(rcon_send(f'gamerule {name}', retries=1))


def _current_whitelist_enabled(props=None):
    global _runtime_flags
    props = props or read_server_properties()
    cached = _runtime_flags.get('whitelist_enabled')
    if cached is not None:
        return bool(cached)
    return str(props.get('white-list', 'false')).strip().lower() == 'true'


def resolve_runtime_panel_state():
    props = read_server_properties()
    gamerules = {}
    commands = [f'gamerule {name}' for name in PANEL_GAMERULES]
    responses = []
    try:
        responses = rcon_send_many(commands, retries=1) if RCON_ENABLED else []
    except Exception:
        responses = []
    for index, name in enumerate(PANEL_GAMERULES):
        try:
            gamerules[name] = _parse_bool_from_output(responses[index])
        except Exception:
            gamerules[name] = None
    return {
        'gamerules': gamerules,
        'save_enabled': bool(_runtime_flags.get('save_enabled', True)),
        'whitelist_enabled': _current_whitelist_enabled(props),
        'pvp_enabled': str(props.get('pvp', 'true')).strip().lower() == 'true',
    }


def observe_runtime_command(command):
    global _runtime_flags
    cmd = str(command or '').strip().lower()
    if not cmd:
        return
    if re.match(r'^save-on(?:\s|$)', cmd):
        _runtime_flags['save_enabled'] = True
    elif re.match(r'^save-off(?:\s|$)', cmd):
        _runtime_flags['save_enabled'] = False
    elif re.match(r'^whitelist\s+on(?:\s|$)', cmd):
        _runtime_flags['whitelist_enabled'] = True
    elif re.match(r'^whitelist\s+off(?:\s|$)', cmd):
        _runtime_flags['whitelist_enabled'] = False


def resolve_world_state(force_refresh=False):
    global _world_state_cache
    now = time.time()
    if not force_refresh and _world_state_cache['expires_at'] > now and _world_state_cache['value']:
        return dict(_world_state_cache['value'])

    if RCON_ENABLED and force_refresh:
        try:
            rcon_send('save-all', retries=1)
            time.sleep(0.2)
        except Exception:
            pass

    level_name = get_level_name()
    level_dat_path = os.path.join(SERVER_ROOT, level_name, 'level.dat')
    if not os.path.exists(level_dat_path):
        raise RuntimeError(f'level.dat not found: {level_dat_path}')

    root = _load_nbt_file(level_dat_path)
    data = root.get('Data') if isinstance(root, dict) else None
    if not isinstance(data, dict):
        raise RuntimeError('invalid level.dat payload')

    try:
        daytime = _query_daytime_via_rcon() if RCON_ENABLED else int(data.get('DayTime', data.get('Time', 0)) or 0) % 24000
    except Exception:
        daytime = int(data.get('DayTime', data.get('Time', 0)) or 0) % 24000

    result = {
        'world': level_name,
        'servertime': daytime,
        'hasStorm': bool(int(data.get('raining', 0) or 0)),
        'isThundering': bool(int(data.get('thundering', 0) or 0)),
        'rainTime': int(data.get('rainTime', 0) or 0),
        'thunderTime': int(data.get('thunderTime', 0) or 0),
        'timestamp': int(now * 1000),
    }
    _world_state_cache = {
        'expires_at': now + WORLD_STATE_CACHE_TTL,
        'value': result,
    }
    return dict(result)


def _read_nbt_string(stream):
    length_b = stream.read(2)
    if len(length_b) != 2:
        raise EOFError('unexpected eof while reading nbt string length')
    length = struct.unpack('>H', length_b)[0]
    raw = stream.read(length)
    if len(raw) != length:
        raise EOFError('unexpected eof while reading nbt string data')
    return raw.decode('utf-8', errors='replace')


def _read_nbt_payload(stream, tag_type):
    if tag_type == 0:
        return None
    if tag_type == 1:
        return struct.unpack('>b', stream.read(1))[0]
    if tag_type == 2:
        return struct.unpack('>h', stream.read(2))[0]
    if tag_type == 3:
        return struct.unpack('>i', stream.read(4))[0]
    if tag_type == 4:
        return struct.unpack('>q', stream.read(8))[0]
    if tag_type == 5:
        return struct.unpack('>f', stream.read(4))[0]
    if tag_type == 6:
        return struct.unpack('>d', stream.read(8))[0]
    if tag_type == 7:
        length = struct.unpack('>i', stream.read(4))[0]
        return stream.read(max(0, length))
    if tag_type == 8:
        return _read_nbt_string(stream)
    if tag_type == 9:
        child_type_b = stream.read(1)
        if len(child_type_b) != 1:
            raise EOFError('unexpected eof while reading nbt list type')
        child_type = child_type_b[0]
        length = struct.unpack('>i', stream.read(4))[0]
        return [_read_nbt_payload(stream, child_type) for _ in range(max(0, length))]
    if tag_type == 10:
        result = {}
        while True:
            tag_type_b = stream.read(1)
            if len(tag_type_b) != 1:
                raise EOFError('unexpected eof while reading nbt compound type')
            child_type = tag_type_b[0]
            if child_type == 0:
                break
            name = _read_nbt_string(stream)
            result[name] = _read_nbt_payload(stream, child_type)
        return result
    if tag_type == 11:
        length = struct.unpack('>i', stream.read(4))[0]
        return [struct.unpack('>i', stream.read(4))[0] for _ in range(max(0, length))]
    if tag_type == 12:
        length = struct.unpack('>i', stream.read(4))[0]
        return [struct.unpack('>q', stream.read(8))[0] for _ in range(max(0, length))]
    raise RuntimeError(f'unsupported nbt tag type: {tag_type}')


def _load_nbt_file(path):
    with gzip.open(path, 'rb') as stream:
        root_type_b = stream.read(1)
        if len(root_type_b) != 1:
            raise RuntimeError('empty nbt file')
        root_type = root_type_b[0]
        if root_type != 10:
            raise RuntimeError(f'unexpected root nbt type: {root_type}')
        _read_nbt_string(stream)
        return _read_nbt_payload(stream, root_type)


def _dimension_to_world_name(dimension):
    base = get_level_name()
    mapping = {
        -1: f'{base}_nether',
        0: base,
        1: f'{base}_the_end',
    }
    try:
        return mapping.get(int(dimension), base)
    except Exception:
        return base


def _resolve_player_location_from_playerdata(player_name):
    entry = _find_player_cache_entry(player_name)
    uuid = str(entry.get('uuid') or '').strip()
    name = str(entry.get('name') or player_name).strip() or str(player_name or '').strip()
    if not uuid:
        raise RuntimeError(f'玩家“{name}”没有可用 UUID')

    playerdata_path = os.path.join(get_level_playerdata_dir(), uuid + '.dat')
    if not os.path.exists(playerdata_path):
        raise RuntimeError(f'玩家“{name}”暂无 playerdata 存档')

    data = _load_nbt_file(playerdata_path)
    pos = data.get('Pos') if isinstance(data, dict) else None
    if not isinstance(pos, list) or len(pos) < 3:
        raise RuntimeError(f'玩家“{name}”的 playerdata 中没有 Pos 坐标')

    return {
        'name': name,
        'world': _dimension_to_world_name(data.get('Dimension', 0)),
        'x': int(round(float(pos[0]))),
        'y': int(round(float(pos[1]))),
        'z': int(round(float(pos[2]))),
        'source': 'playerdata',
    }


def _resolve_player_location_from_dynmap(player_name):
    target = str(player_name or '').strip()
    if not target:
        raise RuntimeError('player name required')

    conn = HTTPConnection(DYNMAP_HOST, DYNMAP_PORT, timeout=5)
    try:
        conn.request('GET', '/up/configuration')
        resp = conn.getresponse()
        cfg = json.loads(resp.read().decode('utf-8', errors='replace'))
        worlds = cfg.get('worlds') if isinstance(cfg, dict) else []
        worlds = worlds if isinstance(worlds, list) else []

        for world in worlds:
            world_name = str((world or {}).get('name') or '').strip()
            if not world_name:
                continue
            conn.request('GET', '/up/world/' + world_name + '/0')
            world_resp = conn.getresponse()
            world_state = json.loads(world_resp.read().decode('utf-8', errors='replace'))
            players = world_state.get('players') if isinstance(world_state, dict) else []
            players = players if isinstance(players, list) else []
            for player in players:
                if not isinstance(player, dict):
                    continue
                name = str(player.get('account') or player.get('name') or '').strip()
                if not name:
                    continue
                if name == target or name.lower() == target.lower():
                    return {
                        'name': name,
                        'world': world_name,
                        'x': int(round(float(player.get('x', 0) or 0))),
                        'y': int(round(float(player.get('y', 0) or 0))),
                        'z': int(round(float(player.get('z', 0) or 0))),
                        'source': 'dynmap',
                    }
    finally:
        conn.close()
    raise RuntimeError(f'Dynmap 里没找到在线玩家“{target}”')


def resolve_player_location(player_name):
    last_errors = []
    try:
        return _resolve_player_location_from_dynmap(player_name)
    except Exception as e:
        last_errors.append(f'dynmap: {e}')

    try:
        rcon_send('save-all', retries=1)
        time.sleep(0.25)
    except Exception as e:
        last_errors.append(f'save-all: {e}')

    try:
        return _resolve_player_location_from_playerdata(player_name)
    except Exception as e:
        last_errors.append(f'playerdata: {e}')

    raise RuntimeError('；'.join(last_errors))


def _b64url_encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _b64url_decode(raw):
    padded = raw + '=' * (-len(raw) % 4)
    return base64.urlsafe_b64decode(padded.encode('ascii'))


def create_auth_token():
    now = int(time.time())
    header = _b64url_encode(json.dumps({
        'alg': 'HS256',
        'typ': 'JWT'
    }, separators=(',', ':')).encode('utf-8'))
    payload = _b64url_encode(json.dumps({
        'iat': now,
        'exp': now + AUTH_TOKEN_TTL,
        'kind': 'admin'
    }, separators=(',', ':')).encode('utf-8'))
    signing_input = f'{header}.{payload}'.encode('ascii')
    signature = _b64url_encode(hmac.new(AUTH_SECRET, signing_input, hashlib.sha256).digest())
    return f'{header}.{payload}.{signature}', now + AUTH_TOKEN_TTL


def verify_auth_token(token):
    if not token:
        return False, 'token required'
    try:
        header, payload, signature = token.split('.', 2)
    except ValueError:
        return False, 'token invalid'
    signing_input = f'{header}.{payload}'.encode('ascii')
    expected = _b64url_encode(hmac.new(AUTH_SECRET, signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        return False, 'token invalid'
    try:
        payload_data = json.loads(_b64url_decode(payload).decode('utf-8'))
    except Exception:
        return False, 'token invalid'
    if payload_data.get('kind') != 'admin':
        return False, 'token invalid'
    if int(payload_data.get('exp', 0)) < int(time.time()):
        return False, 'token expired'
    return True, payload_data


def authenticate_request(data):
    token = str(data.get('token', '')).strip()
    if token:
        ok, detail = verify_auth_token(token)
        if ok:
            return True, None, 'token'
        return False, detail, None
    pw = data.get('password', '')
    if not pw:
        return False, 'password required', None
    if pw != RCON_PASSWORD:
        return False, 'password mismatch', None
    return True, None, 'password'


def tmux_run(args):
    result = subprocess.run(
        ['tmux'] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or 'tmux command failed').strip())
    return result.stdout.strip()


def server_pane_command():
    return tmux_run(['display-message', '-p', '-t', SERVER_PANE, '#{pane_current_command}'])


def wait_for_server_stop(timeout=60):
    deadline = time.time() + timeout
    last_cmd = ''
    while time.time() < deadline:
        last_cmd = server_pane_command().lower()
        if last_cmd not in ('java', 'java.bin'):
            return last_cmd
        time.sleep(1)
    raise RuntimeError(f'server did not stop in time (pane command: {last_cmd or "unknown"})')


def restart_server_process():
    current_cmd = server_pane_command().lower()
    if current_cmd in ('java', 'java.bin'):
        try:
            rcon_send('stop', retries=1)
        except Exception:
            tmux_run(['send-keys', '-t', SERVER_PANE, 'stop', 'C-m'])
        wait_for_server_stop(timeout=60)
    tmux_run(['send-keys', '-t', SERVER_PANE, f'cd "{SERVER_ROOT}"; ./run.sh', 'C-m'])


def _is_retryable_rcon_error(err):
    if isinstance(err, (socket.timeout, ConnectionResetError, BrokenPipeError, TimeoutError)):
        return True
    if isinstance(err, OSError) and getattr(err, 'errno', None) in (32, 104, 110, 111):
        return True
    text = str(err or '').lower()
    return 'connection reset by peer' in text or 'connection closed' in text

_rcon_lock = threading.Lock()
_last_rcon_connect_at = 0.0


def _pack_rcon_packet(pkt_id, pkt_type, body):
    body_b = body.encode('utf-8') + b'\x00\x00'
    length = 8 + len(body_b)
    return struct.pack('<iii', length, pkt_id, pkt_type) + body_b


def _recv_exact(sock, size):
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError('RCON connection closed')
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def _recv_rcon_packet(sock):
    length_b = _recv_exact(sock, 4)
    length = struct.unpack('<i', length_b)[0]
    if length < 10:
        raise RuntimeError('invalid RCON packet length')
    payload = _recv_exact(sock, length)
    pkt_id, pkt_type = struct.unpack('<ii', payload[:8])
    body = payload[8:-2]
    return pkt_id, pkt_type, body


def _wait_for_rcon_slot():
    global _last_rcon_connect_at
    if RCON_CONNECT_INTERVAL <= 0:
        return
    now = time.monotonic()
    delay = (_last_rcon_connect_at + RCON_CONNECT_INTERVAL) - now
    if delay > 0:
        time.sleep(delay)
    _last_rcon_connect_at = time.monotonic()


def _rcon_send_many_once(commands):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(RCON_SOCKET_TIMEOUT)
        sock.connect((RCON_HOST, RCON_PORT))
        sock.sendall(_pack_rcon_packet(1, 3, RCON_PASSWORD))
        auth_id, _, _ = _recv_rcon_packet(sock)
        if auth_id == -1:
            raise RuntimeError('RCON password rejected')

        results = []
        for index, command in enumerate(commands, start=2):
            sock.sendall(_pack_rcon_packet(index, 2, command))
            _, _, body = _recv_rcon_packet(sock)
            results.append(body.decode('utf-8', errors='replace').rstrip('\x00'))
        return results


def rcon_send_many(commands, retries=3):
    commands = [str(command or '').strip() for command in commands]
    commands = [command for command in commands if command]
    if not commands:
        return []
    last_err = None
    total_attempts = max(int(retries or 1), 1)
    for attempt in range(total_attempts):
        try:
            with _rcon_lock:
                _wait_for_rcon_slot()
                return _rcon_send_many_once(commands)
        except Exception as e:
            last_err = e
            if attempt < total_attempts - 1 and _is_retryable_rcon_error(e):
                time.sleep(0.35 + attempt * 0.35)
                continue
            raise
    raise last_err


def rcon_send(command, retries=3):
    results = rcon_send_many([command], retries=retries)
    return results[0] if results else ''


def rcon_http_status(err):
    return 503 if _is_retryable_rcon_error(err) else 500

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_ROOT, **kwargs)

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if RCON_ENABLED and parsed.path == '/api/login':
            self._handle_login()
        elif RCON_ENABLED and parsed.path == '/api/rcon':
            self._handle_rcon()
        elif RCON_ENABLED and parsed.path == '/api/config':
            self._handle_config()
        elif RCON_ENABLED and parsed.path == '/api/seed':
            self._handle_seed()
        elif RCON_ENABLED and parsed.path == '/api/structures':
            self._handle_structures()
        elif RCON_ENABLED and parsed.path == '/api/player-location':
            self._handle_player_location()
        elif RCON_ENABLED and parsed.path == '/api/runtime-state':
            self._handle_runtime_state()
        elif RCON_ENABLED and parsed.path == '/api/world-state':
            self._handle_world_state()
        elif RCON_ENABLED and parsed.path == '/api/system':
            self._handle_system()
        else:
            self._json(404, {'success': False, 'error': 'not found'})

    def do_GET(self):
        parsed = urlparse(self.path)
        if RCON_ENABLED and parsed.path == '/api/status':
            self._json(200, {
                'success': True,
                'rcon_host': RCON_HOST,
                'rcon_port': RCON_PORT,
                'bridge_port': PORT,
                'minecraft_version': MINECRAFT_VERSION,
                'native_seed_finder_ready': os.path.exists(CUBIOMES_SHIM_PATH),
            })
        elif parsed.path == '/admin' or parsed.path == '/admin/':
            self.path = '/admin.html'
            super().do_GET()
        elif parsed.path.startswith('/dynmap/'):
            self._proxy_dynmap(parsed.path, parsed.query)
        else:
            super().do_GET()

    def _handle_rcon(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json(400, {'success': False, 'error': 'invalid json'})
            return
        cmd = data.get('command', '').strip()
        if not cmd:
            self._json(400, {'success': False, 'error': 'command required'})
            return
        authed, error, auth_kind = authenticate_request(data)
        if not authed:
            self._json(403, {'success': False, 'error': error})
            return
        try:
            result = rcon_send(cmd)
            observe_runtime_command(cmd)
            self._json(200, {'success': True, 'response': result, 'auth_kind': auth_kind})
        except Exception as e:
            self._json(rcon_http_status(e), {'success': False, 'error': str(e)})

    def _handle_config(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json(400, {'success': False, 'error': 'invalid json'})
            return

        authed, error, _ = authenticate_request(data)
        if not authed:
            self._json(403, {'success': False, 'error': error})
            return

        action = data.get('action', 'get')
        if action == 'get':
            self._json(200, {'success': True, 'config': get_managed_config_values()})
            return
        if action != 'set':
            self._json(400, {'success': False, 'error': 'invalid action'})
            return

        updates = data.get('updates', {})
        if not isinstance(updates, dict) or not updates:
            self._json(400, {'success': False, 'error': 'updates required'})
            return

        normalized = {}
        try:
            for key, value in updates.items():
                if key not in MANAGED_CONFIG:
                    raise ValueError(f'unsupported key: {key}')
                normalized[key] = normalize_config_value(key, value)
            write_server_properties(normalized)
        except Exception as e:
            self._json(400, {'success': False, 'error': str(e)})
            return

        self._json(200, {
            'success': True,
            'updated': normalized,
            'restart_required': True,
            'message': '已写入 server.properties，重启服务器后生效'
        })

    def _handle_seed(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json(400, {'success': False, 'error': 'invalid json'})
            return

        authed, error, _ = authenticate_request(data)
        if not authed:
            self._json(403, {'success': False, 'error': error})
            return

        try:
            info = resolve_world_seed()
            self._json(200, {
                'success': True,
                'seed': info['seed'],
                'source': info['source'],
                'minecraft_version': MINECRAFT_VERSION,
            })
        except Exception as e:
            self._json(500, {'success': False, 'error': str(e)})

    def _handle_structures(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json(400, {'success': False, 'error': 'invalid json'})
            return

        authed, error, _ = authenticate_request(data)
        if not authed:
            self._json(403, {'success': False, 'error': error})
            return

        center_x = clamp_int(data.get('x', 0), 0, -30000000, 30000000)
        center_z = clamp_int(data.get('z', 0), 0, -30000000, 30000000)
        radius = clamp_int(data.get('radius', DEFAULT_STRUCTURE_RADIUS), DEFAULT_STRUCTURE_RADIUS, MIN_STRUCTURE_RADIUS, MAX_STRUCTURE_RADIUS)
        limit_per_type = clamp_int(data.get('limit_per_type', DEFAULT_STRUCTURE_LIMIT), DEFAULT_STRUCTURE_LIMIT, 1, MAX_STRUCTURE_LIMIT)

        try:
            seed_info = resolve_world_seed()
            result = build_structure_search(seed_info, MINECRAFT_VERSION, center_x, center_z, radius, limit_per_type)
            self._json(200, {'success': True, **result})
        except Exception as e:
            self._json(500, {'success': False, 'error': str(e)})

    def _handle_player_location(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json(400, {'success': False, 'error': 'invalid json'})
            return

        authed, error, _ = authenticate_request(data)
        if not authed:
            self._json(403, {'success': False, 'error': error})
            return

        player_name = str(data.get('player') or data.get('name') or '').strip()
        if not player_name:
            self._json(400, {'success': False, 'error': 'player required'})
            return

        try:
            location = resolve_player_location(player_name)
            self._json(200, {'success': True, **location})
        except Exception as e:
            self._json(500, {'success': False, 'error': str(e)})

    def _handle_world_state(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json(400, {'success': False, 'error': 'invalid json'})
            return

        authed, error, _ = authenticate_request(data)
        if not authed:
            self._json(403, {'success': False, 'error': error})
            return

        try:
            state = resolve_world_state(force_refresh=bool(data.get('force_refresh')))
            self._json(200, {'success': True, **state})
        except Exception as e:
            self._json(500, {'success': False, 'error': str(e)})

    def _handle_runtime_state(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json(400, {'success': False, 'error': 'invalid json'})
            return

        authed, error, _ = authenticate_request(data)
        if not authed:
            self._json(403, {'success': False, 'error': error})
            return

        try:
            state = resolve_runtime_panel_state()
            self._json(200, {'success': True, **state})
        except Exception as e:
            self._json(500, {'success': False, 'error': str(e)})

    def _handle_login(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json(400, {'success': False, 'error': 'invalid json'})
            return
        pw = data.get('password', '')
        if not pw:
            self._json(403, {'success': False, 'error': 'password required'})
            return
        if pw != RCON_PASSWORD:
            self._json(403, {'success': False, 'error': 'password mismatch'})
            return
        token, expires_at = create_auth_token()
        self._json(200, {
            'success': True,
            'token': token,
            'token_type': 'Bearer',
            'expires_in': AUTH_TOKEN_TTL,
            'expires_at': expires_at
        })

    def _handle_system(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._json(400, {'success': False, 'error': 'invalid json'})
            return

        authed, error, _ = authenticate_request(data)
        if not authed:
            self._json(403, {'success': False, 'error': error})
            return

        action = str(data.get('action', '')).strip()
        if action != 'restart_server':
            self._json(400, {'success': False, 'error': 'invalid action'})
            return

        try:
            restart_server_process()
            self._json(200, {
                'success': True,
                'message': '服务器正在重启，通常 10-30 秒后恢复连接',
                'restart_in_progress': True
            })
        except Exception as e:
            self._json(500, {'success': False, 'error': str(e)})

    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _proxy_dynmap(self, path, query):
        try:
            conn = HTTPConnection(DYNMAP_HOST, DYNMAP_PORT, timeout=5)
            target = path.replace('/dynmap', '', 1) or '/'
            if query:
                target += '?' + query
            conn.request('GET', target)
            resp = conn.getresponse()
            body = resp.read()
            patched_body = _patch_dynmap_world_state(target, body)
            self.send_response(resp.status)
            for key, val in resp.getheaders():
                if key.lower() not in ('transfer-encoding', 'content-length'):
                    self.send_header(key, val)
            self.send_header('Content-Length', str(len(patched_body)))
            self.end_headers()
            self.wfile.write(patched_body)
            conn.close()
        except Exception as e:
            self.send_error(502, f'Dynmap unavailable at {DYNMAP_HOST}:{DYNMAP_PORT}: {e}')

    def _send_cors_headers(self):
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)

    def log_message(self, format, *args):
        msg = format % args if args else format
        print(f'[http:5201] {msg}')


if __name__ == '__main__':
    os.chdir(WEB_ROOT)
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    status = 'RCON enabled' if RCON_ENABLED else 'RCON disabled'
    print(f'[http:5201] listening, {status}')
    server.serve_forever()
