"""Offline Codex MCP diagnostics, loaded only by the packaged launcher."""
import hashlib
import os
from pathlib import Path
import re
import types


# Pin the reviewed launcher so diagnostics can verify a separately selected install.
# Update this digest after reviewing changes to the LF-normalized codex_mcp_launcher.py source.
DIAGNOSTIC_LAUNCHER_SHA256 = 'b87167a8dc96e9669829d4877ee68d1be7020ec2d2b372909b6db65fe41263f8'


def diagnostic_text(value):
    """Bound context facts and strip controls/terminal escapes; never report org values."""
    if value is None:
        return None
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(value))
    return ''.join(c for c in text if c.isprintable())[:512]


def diagnostic(server, reason, guidance, *, status='error', invoking_root=None,
               selected_root=None):
    try:
        cwd = Path.cwd()
    except OSError:
        cwd = None
    return {'schema_version': 1, 'server': server, 'status': status,
            'reason': reason, 'guidance': guidance,
            'context': {'cwd': diagnostic_text(cwd),
                        'PWD': diagnostic_text(os.environ.get('PWD')),
                        'INIT_CWD': diagnostic_text(os.environ.get('INIT_CWD'))},
            'invoking_root': diagnostic_text(invoking_root),
            'selected_root': diagnostic_text(selected_root)}


def preflight(server, invoking_root, bootstrap):
    """Offline native resolution, then diagnostics from the selected installed launcher."""
    if server not in ('salesforce-metadata-experts', 'salesforce-metadata-grounding', bootstrap.H360,
                      'salesforce-lsp'):
        return diagnostic(diagnostic_text(server), 'unknown_server',
                          'Select one of the four bundled Salesforce MCP servers.',
                          invoking_root=invoking_root)
    home = Path.home()
    state = home / '.sf/salesforce-development'
    if server == bootstrap.H360:
        value = os.environ.get('SF_HEADLESS_360_ENABLED')
        enabled = (value.strip().lower() in ('1', 'true', 'enabled', 'on')
                   if value is not None else
                   bootstrap.read_json_object(state / 'headless-360.json').get('enabled') is True)
        if not enabled:
            return diagnostic(server, 'disabled', 'Off; no tools exposed.', status='off',
                              invoking_root=invoking_root)
    recorded = bootstrap.read_json_object(state / 'codex-plugin-root.json').get('plugin_root')
    codex_home = bootstrap.find_codex_home(os.environ, home)
    package = bootstrap.resolve_plugin_root(codex_home, recorded)
    if package is None:
        candidates = bootstrap.cache_candidates(codex_home)
        reason = ('installation_ambiguous' if len(candidates) > 1 else
                  'installation_invalid' if candidates or recorded else 'installation_missing')
        return diagnostic(server, reason, bootstrap.NOT_FOUND.strip(),
                          invoking_root=invoking_root)
    entry = package / 'scripts/codex_mcp_launcher.py'
    try:
        # Only the reviewed launcher snapshot may execute, never arbitrary cache code.
        # Git checkouts may use CRLF. Hash and execute the same LF-normalized bytes.
        source = entry.read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(source).hexdigest() != DIAGNOSTIC_LAUNCHER_SHA256:
            return diagnostic(server, 'diagnostics_unavailable',
                               'Selected installed launcher differs from the supported offline diagnostic implementation. Update the plugin and start a new session.',
                              invoking_root=invoking_root, selected_root=package)
        namespace = {'__file__': str(entry), '__name__': '_codex_launch_diagnostics'}
        exec(compile(source, str(entry), 'exec'), namespace)
        result = namespace['launch_preflight'](server, diagnostic_module=types.SimpleNamespace(
            diagnostic=diagnostic, diagnostic_text=diagnostic_text))
    except (OSError, RuntimeError, SyntaxError, ImportError, KeyError, ValueError,
            AttributeError, TypeError, RecursionError):
        return diagnostic(server, 'diagnostics_unavailable',
                          'Selected installed launcher diagnostics could not be read. Start a new session; reinstall if this persists.',
                          invoking_root=invoking_root, selected_root=package)
    result['invoking_root'] = diagnostic_text(invoking_root)
    result['selected_root'] = diagnostic_text(package)
    return result
