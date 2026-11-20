import functools
import json
import os
from pathlib import Path
import re
import runpy
import sys

# Shared startup for all four Codex MCP servers. Codex starts a no-cwd entry in the
# session folder but expands no plugin-root placeholder, so this finds the installed
# plugin itself: Codex's active cache install first, then the root our own hook and
# setup recorded. It never runs a root whose manifests disagree.
H360 = 'salesforce-headless-360'
PLUGIN = 'salesforce-development'
LOCAL_VERSION = 'local'
MAX_U64 = 2 ** 64 - 1
NOT_FOUND = ('Salesforce Development: could not locate the installed plugin for this Codex session. '
             'Start a new Codex session in your Salesforce DX project. If this repeats, reinstall the plugin.\n')


def find_codex_home(environ, home):
    """Mirror Codex's find_codex_home; a bad CODEX_HOME falls back to ~/.codex."""
    value = environ.get('CODEX_HOME')
    if value and not value.startswith('~') and os.path.isabs(value):
        try:
            path = Path(value).resolve(strict=True)
            if path.is_dir():
                return path
        except (OSError, RuntimeError):
            pass
    return home / '.codex'


def _parse_semver(name):
    match = re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'
                         r'(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?', name)
    if match is None:
        return None
    core = tuple(int(part) for part in match.group(1, 2, 3))
    if max(core) > MAX_U64:
        return None
    pre = match.group(4).split('.') if match.group(4) is not None else None
    build = match.group(5).split('.') if match.group(5) is not None else None
    for part in (pre or []) + (build or []):
        if not re.fullmatch(r'[0-9A-Za-z-]+', part):
            return None
    for part in pre or []:
        if part.isdigit() and part != '0' and part.startswith('0'):
            return None
    return core, pre, build


def _identifier_key(part):
    # Numeric identifiers sort before alphanumeric ones; numerics by value, then length.
    return (0, int(part), len(part)) if part.isdigit() else (1, part, 0)


def _compare_identifiers(left, right):
    a, b = [_identifier_key(part) for part in left], [_identifier_key(part) for part in right]
    return (a > b) - (a < b)


def _compare_semver(left, right):
    if left[0] != right[0]:
        return -1 if left[0] < right[0] else 1
    if (left[1] is None) != (right[1] is None):
        return 1 if left[1] is None else -1
    if left[1] is not None:
        result = _compare_identifiers(left[1], right[1])
        if result:
            return result
    if (left[2] is None) != (right[2] is None):
        return -1 if left[2] is None else 1
    if left[2] is not None:
        return _compare_identifiers(left[2], right[2])
    return 0


def _compare_versions(left, right):
    """Mirror compare_plugin_versions: semver when both parse, else plain string order."""
    a, b = _parse_semver(left), _parse_semver(right)
    if a is not None and b is not None:
        return _compare_semver(a, b)
    return (left > right) - (left < right)


def active_version(directory):
    """Pick the version directory Codex treats as active (core-plugin-common installed.rs)."""
    names = []
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                name = entry.name
                try:
                    if (name in ('.', '..') or not re.fullmatch(r'[A-Za-z0-9.+_-]+', name)
                            or not entry.is_dir(follow_symlinks=False)):
                        continue
                except OSError:
                    continue
                names.append(name)
    except OSError:
        return None
    if LOCAL_VERSION in names:
        return directory / LOCAL_VERSION
    if not names:
        return None
    return directory / sorted(names, key=functools.cmp_to_key(_compare_versions))[-1]


def validate_root(root):
    """Return the resolved package when both manifests agree and the launcher is a file."""
    try:
        package = Path(root).resolve(strict=True)
        manifest = json.loads((package / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        claude = json.loads((package / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))
        launcher = (package / 'scripts/codex_mcp_launcher.py').resolve(strict=True)
        if (isinstance(manifest, dict) and manifest.get('name') == PLUGIN
                and isinstance(claude, dict) and claude.get('name') == manifest['name']
                and isinstance(manifest.get('version'), str) and bool(manifest['version'])
                and manifest['version'] == claude.get('version')
                and package in launcher.parents and launcher.is_file()):
            return package
    except (OSError, UnicodeError, ValueError, RecursionError, RuntimeError):
        pass
    return None


def cache_candidates(codex_home):
    """One active install per marketplace under plugins/cache/*/salesforce-development."""
    found = []
    names = []
    try:
        with os.scandir(codex_home / 'plugins/cache') as markets:
            for entry in markets:
                try:
                    if entry.is_dir():
                        names.append(entry.name)
                except OSError:
                    continue
    except OSError:
        return found
    names.sort()
    for name in names:
        chosen = active_version(codex_home / 'plugins/cache' / name / PLUGIN)
        if chosen is not None:
            found.append(chosen)
    return found


def resolve_plugin_root(codex_home, recorded):
    """Find the installed package: active cache install, else the recorded root."""
    candidates = cache_candidates(codex_home)
    recorded_path = Path(recorded) if isinstance(recorded, str) and os.path.isabs(recorded) else None
    if len(candidates) == 1:
        return validate_root(candidates[0])
    if candidates:
        if recorded_path is None:
            return None
        try:
            wanted = recorded_path.resolve(strict=True)
            if any(wanted == path.resolve(strict=True) for path in candidates):
                return validate_root(wanted)
        except (OSError, RuntimeError):
            pass
        return None
    return validate_root(recorded_path) if recorded_path is not None else None


def read_json_object(path):
    try:
        with path.open(encoding='utf-8') as stream:
            raw = stream.read(8193)
        data = json.loads(raw) if len(raw) <= 8192 else {}
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, ValueError, RecursionError):
        return {}


def reply(value):
    try:
        print(json.dumps(value), flush=True)
    except BrokenPipeError:
        # The host closed its pipe; avoid an extra traceback during shutdown.
        os._exit(0)


def serve_disabled():
    sys.stderr.write('Headless 360 disabled; no auth or network request made.\n')
    # Default-off still completes an empty MCP handshake without auth or network work.
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except (ValueError, RecursionError):
            reply({'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Parse error'}})
            continue
        if not isinstance(request, dict):
            reply({'jsonrpc': '2.0', 'id': None, 'error': {'code': -32600, 'message': 'Invalid Request'}})
            continue
        if request.get('id') is None:
            continue
        method = request.get('method')
        if method == 'initialize':
            params = request.get('params')
            params = params if isinstance(params, dict) else {}
            result = {'protocolVersion': params.get('protocolVersion', '2025-06-18'),
                      'capabilities': {'tools': {}},
                      'serverInfo': {'name': 'salesforce-headless-360 (disabled)', 'version': '1.0.0'}}
        elif method == 'tools/list':
            result = {'tools': []}
        elif method == 'ping':
            result = {}
        else:
            reply({'jsonrpc': '2.0', 'id': request['id'],
                   'error': {'code': -32601, 'message': 'Headless 360 is disabled'}})
            continue
        reply({'jsonrpc': '2.0', 'id': request['id'], 'result': result})


def main():
    server = sys.argv[1] if len(sys.argv) > 1 else ''
    home = Path.home()
    state = home / '.sf/salesforce-development'
    if server == H360:
        value = os.environ.get('SF_HEADLESS_360_ENABLED')
        if value is not None:
            enabled = value.strip().lower() in ('1', 'true', 'enabled', 'on')
        else:
            enabled = read_json_object(state / 'headless-360.json').get('enabled') is True
        if not enabled:
            serve_disabled()
            return
    recorded = read_json_object(state / 'codex-plugin-root.json').get('plugin_root')
    package = resolve_plugin_root(find_codex_home(os.environ, home), recorded)
    if package is None:
        sys.stderr.write(NOT_FOUND)
        raise SystemExit(2)
    try:
        entry = (package / 'scripts/codex_mcp_launcher.py').resolve(strict=True)
    except (OSError, RuntimeError):
        sys.stderr.write(NOT_FOUND)
        raise SystemExit(2)
    sys.argv = [str(entry), server]
    runpy.run_path(str(entry), run_name='__main__')
    raise SystemExit(0)


if __name__ == '__main__':
    main()
