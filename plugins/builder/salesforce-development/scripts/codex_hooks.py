#!/usr/bin/env python3
"""Codex lifecycle boundary over the existing Salesforce plugin runtime.

The pending command is inspected and forwarded as data, never executed here.
Project-sensitive hooks use only an absolute, accessible event cwd.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time
import stat

_RUNTIME_UNAVAILABLE = False
try:
    import sf_context as context
    import sf_telemetry as telemetry
    import codex_edit_advisory as edit_advice
    import codex_startup
    import sf_shim as shim
    from sf_shim import literal_sf_commands as sf_segments
except Exception:
    _RUNTIME_UNAVAILABLE = True

ROOT = Path(__file__).resolve().parent.parent


def deny(reason: str) -> dict:
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": "[salesforce-development · Codex adapter] " + reason,
    }}


def invoke(handler, payload: dict, *args) -> dict:
    """Give one handler its own copy of the same event and capture one JSON reply."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
        original = sys.stdin
        try:
            sys.stdin = io.StringIO(json.dumps(payload))
            handler(*args)
        finally:
            sys.stdin = original
    value = json.loads(output.getvalue() or '{}')
    if not isinstance(value, dict):
        raise ValueError("hook reply is not an object")
    return value


def external(relative: str, payload: dict, *args, timeout: int) -> dict:
    result = codex_startup.run_renderer(
        [str(ROOT / relative), *args], timeout=timeout, input=json.dumps(payload),
    )
    if result.returncode:
        raise ValueError("hook callback failed")
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise ValueError("hook reply is not an object")
    return value


def merge(outputs: list[dict], event: str) -> dict:
    result: dict = {"continue": True}
    messages, contexts = [], []
    for output in outputs:
        specific = output.get("hookSpecificOutput") or {}
        if specific.get("permissionDecision") == "deny":
            return output
        if output.get("systemMessage"):
            messages.append(output["systemMessage"])
        if specific.get("additionalContext"):
            contexts.append(specific["additionalContext"])
    if messages:
        result["systemMessage"] = '\n'.join(messages)
    if contexts:
        result["hookSpecificOutput"] = {
            "hookEventName": event, "additionalContext": '\n'.join(contexts),
        }
    return result



def _shell_command(payload: dict):
    """The pending shell command, or None when the payload shape is unrecognized."""
    tool_input = payload.get('tool_input')
    if tool_input is None:
        tool_input = payload.get('toolInput')
    if tool_input is None:
        return ''
    if isinstance(tool_input, dict):
        command = tool_input.get('command')
        if isinstance(command, str):
            return command
        if command is None:
            return ''
    return None


def _workdir_differs(payload: dict) -> bool:
    """Whether the tool runs in a directory other than the event cwd."""
    tool_input = payload.get('tool_input') or payload.get('toolInput') or {}
    event_cwd = Path(payload['cwd']).resolve()
    for key in ('workdir', 'cwd'):
        value = tool_input.get(key)
        if value in (None, ''):
            continue
        if not isinstance(value, str) or (event_cwd / value).resolve() != event_cwd:
            return True
    return False


def _deploy_gate(mode: str, payload: dict, target: str, confirmed: bool) -> dict:
    """Run the shared gate on the command this hook already parsed."""
    args = [mode, '--matched', '--target', target, '--client', 'codex']
    if confirmed:
        args.append('--confirmed')
    output = external('scripts/sf-deploy-gate', payload, *args, timeout=35)
    if (output.get('systemMessage')
            or output.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny'):
        return output
    return deny('The deploy gate did not evaluate this command.')


def pre_shell(payload: dict) -> dict:
    command = _shell_command(payload)
    if command is None:
        if shim.mutation_hint(json.dumps(payload.get('tool_input', payload.get('toolInput')),
                                         default=str)):
            return deny('This shell request has an unrecognized shape, so its Salesforce CLI '
                        'command cannot be checked. Run it as one plain shell command.')
        command = ''
    scan = shim.scan_sf(command)
    # A command that looks like a deploy/delete must resolve to a literal sf call that the
    # gate can verify. Any other wrapper, interpreter or quoting the scan cannot follow is
    # refused, including text that only mentions such a command.
    if scan.untraced or (shim.mutation_hint(command) and (
            scan.opaque or scan.unparsed
            or not any(shim.mutation_verb(call.argv) for call in scan.calls))):
        return deny('Run deploy/delete as a literal sf command, not through eval, a nested '
                    'shell, command substitution, xargs, a heredoc or another wrapper, so its '
                    'target org can be verified.')
    if scan.repeating:
        return deny('Run deploy/delete as one plain top-level sf command, not inside a loop, '
                    'function or `watch`, so each run is verified and confirmed.')
    outputs = [edit_advice.pre_shell_advice(payload)]
    spend_confirmation, target = False, ''
    mutations = [call for call in scan.calls if shim.mutation_verb(call.argv)]
    if mutations:
        if _workdir_differs(payload) or shim.mutation_context_is_ambiguous(command):
            return deny('Run deploy/delete without inline directory, environment, config changes '
                        'or shell-expanded arguments. Use the tool cwd and a literal target org.')
        if len(mutations) != 1:
            return deny('Run one deploy/delete command per shell call so each org is verified.')
        call = mutations[0]
        targets, ambiguous = shim.target_orgs(call.argv)
        if ambiguous or call.xargs:
            return deny('The target org of this deploy/delete cannot be read. Pass one literal '
                        '--target-org <alias>.')
        if len(targets) > 1:
            return deny('Conflicting target-org flags cannot be verified safely.')
        explicit = targets[0] if targets else ''
        with contextlib.ExitStack() as stack:
            if explicit:
                original = dict(os.environ)
                os.environ['SF_TARGET_ORG'] = explicit
                os.environ['SFDX_TARGET_ORG'] = explicit
                stack.callback(lambda: (os.environ.clear(), os.environ.update(original)))
            outputs.append(invoke(lambda: context.cmd_verify_org(command_verified=True), payload))
            if merge(outputs, 'PreToolUse').get('hookSpecificOutput', {}).get('permissionDecision') == 'deny':
                return outputs[-1]
            target = explicit or context.get_target_org_detailed()[0]
        if not target:
            return deny("No target org configured. Run 'sf config set target-org <alias>' "
                        "before deploying.")
        verb = shim.mutation_verb(call.argv)
        if verb in ('deploy-start', 'deploy-quick'):
            # Peek now, spend later: the confirmation is consumed only after every
            # check below has allowed this command.
            confirmed = context._peek_prod_deploy_confirmation(payload.get('session_id'), target)
            outputs.append(_deploy_gate('prod-check', payload, target, confirmed))
            # The gate reports whether its allow relied on the confirmation (the target is
            # production); a confirmation for any other org is never spent.
            spend_confirmation = confirmed and bool(outputs[-1].get('prodConfirmationUsed'))
        elif verb == 'delete':
            outputs.append(_deploy_gate('destructive', payload, target, False))
        if outputs[-1].get('hookSpecificOutput', {}).get('permissionDecision') == 'deny':
            return outputs[-1]
    argvs = [call.argv for call in scan.calls]
    if any(s[1:3] == ['project', 'generate'] or s[1:4] == ['template', 'generate', 'project']
           for s in argvs):
        outputs.append(invoke(context.cmd_scaffold_gate, payload))
    if any(s[1:4] in (['project', 'deploy', 'start'], ['project', 'deploy', 'validate'])
           for s in argvs):
        try:
            outputs.append(external('bin/lsp-precheck', payload, timeout=45))
        except (OSError, subprocess.SubprocessError, ValueError):
            # Diagnostics has the same fail-open posture as the shared precheck.
            outputs.append({'continue': True})
    result = merge(outputs, 'PreToolUse')
    if (spend_confirmation
            and result.get('hookSpecificOutput', {}).get('permissionDecision') != 'deny'
            and not context._consume_prod_deploy_confirmation(payload.get('session_id'), target)):
        return deny('The production deploy confirmation was already used. Ask the user to '
                    f'reply "confirm production deploy to {target}" again.')
    return result


def post_shell(payload: dict) -> dict:
    outcome = shell_outcome(payload.get('tool_response'))
    if outcome is None:
        # A running unified-exec session or opaque result cannot mint success.
        return {"continue": True}
    normalized = dict(payload, tool_response={"exit_code": 0 if outcome == 'success' else 1})
    if outcome == 'success':
        return invoke(context.cmd_post_bash, normalized)
    telemetry.capture_event('command_invoked', 'failure', normalized)
    command = context._hook_command(normalized)
    if any(shim.mutation_verb(s) in ('deploy-start', 'deploy-quick', 'deploy-other')
           for s in sf_segments(command)):
        return invoke(context.cmd_post_deploy_failure, normalized)
    if context._is_final_synchronous_apex_test(command):
        return invoke(context.cmd_post_test_failure, normalized)
    return {"continue": True}


def shell_outcome(response) -> str | None:
    """Classify host result metadata, never arbitrary command stdout."""
    if isinstance(response, dict):
        if context._hook_reports_failure({'tool_response': response}):
            return 'failure'
        for key in ('exit_code', 'exitCode', 'returncode'):
            if type(response.get(key)) is int:
                return 'success' if response[key] == 0 else 'failure'
        return None
    # Codex shell post-hooks provide raw stdout strings without exit status. Even a
    # JSON-looking string or an apparent exit header can be command output.
    return None


# Recovery waits for a full day of inactivity and limits each startup's work.
_RECOVERY_AGE_SECONDS = 24 * 60 * 60
_RECOVERY_SCAN_LIMIT = 256
_RECOVERY_SEND_LIMIT = 16


def record_plugin_root() -> None:
    """Record this install for the MCP bootstrap; never fail or change the hook output."""
    try:
        import codex_mcp_launcher
        codex_mcp_launcher.record_plugin_root(ROOT)
    except Exception:
        pass


def recover_stale_buffers(session_id: str) -> None:
    """Claim inactive buffers once and hand them to the consent-gated sender."""
    try:
        if (not telemetry._in_sf_project() or not telemetry._is_enabled()
                or (not telemetry._is_ci() and not telemetry._notice_shown())):
            return
        current = telemetry._session_buffer(session_id)
        cutoff = time.time() - _RECOVERY_AGE_SECONDS
        sent = 0
        generation = telemetry._consent_generation()
        cursor = telemetry._STATE_DIR / 'codex-telemetry-recovery-cursor'
        try:
            after = cursor.read_text()[:255]
        except (OSError, UnicodeDecodeError):
            after = ''
        # The cursor is the last name examined in sorted order. Claiming a buffer
        # removes it from the directory, which would shift a positional offset past
        # entries that were never examined.
        names = sorted(name for name in os.listdir(telemetry._STATE_DIR) if name > after)
        examined = ''
        for scanned, name in enumerate(names):
            # Name order seeks the persisted batch; metadata reads and detached
            # hand-offs are bounded independently.
            if scanned >= _RECOVERY_SCAN_LIMIT or sent >= _RECOVERY_SEND_LIMIT:
                telemetry._write_private(cursor, examined)
                break
            examined = name
            if not (name.startswith(telemetry._BUFFER_PREFIX + '-') and name.endswith('.jsonl')):
                continue
            buffer = telemetry._STATE_DIR / name
            if buffer == current:
                continue
            try:
                info = buffer.lstat()
            except OSError:
                continue
            if (not stat.S_ISREG(info.st_mode) or not info.st_size
                    or info.st_mtime > cutoff):
                continue
            # A unique snapshot and atomic rename give concurrent sweepers
            # exclusive ownership of the original records.
            fd, snapshot_name = tempfile.mkstemp(dir=telemetry._STATE_DIR,
                                                 prefix='telemetry-snapshot-', suffix='.jsonl')
            os.close(fd)
            snapshot = Path(snapshot_name)
            try:
                os.replace(buffer, snapshot)
                sent += 1
                snapshot.chmod(0o600)
                if (not telemetry._is_enabled()
                        or telemetry._consent_generation() != generation
                        or (not telemetry._is_ci() and not telemetry._notice_shown())
                        or not telemetry._spawn_sender(snapshot)):
                    snapshot.unlink(missing_ok=True)
            except Exception:
                snapshot.unlink(missing_ok=True)
        else:
            telemetry._write_private(cursor, '')
    except Exception:
        pass


def dispatch(event: str, payload: dict) -> dict:
    os.environ['SF_AGENT_CLIENT'] = 'codex'
    # Codex currently exposes ANSI SGR control codes from hook systemMessage
    # output as literal text. Force the shared renderers and their startup
    # subprocess to use their existing plain-text path for this host.
    os.environ['NO_COLOR'] = '1'
    payload = dict(payload)
    payload['session_id'] = telemetry.session_identity(payload)
    raw = payload.get('cwd')
    valid = isinstance(raw, str) and Path(raw).is_absolute()
    try:
        if not valid:
            raise OSError('missing absolute cwd')
        context._activate_host_working_directory(payload, 'codex')
        if Path.cwd().resolve() != Path(raw).resolve():
            raise OSError('inaccessible cwd')
    except OSError:
        command = context._hook_command(payload)
        scan = shim.scan_sf(command)
        protected = (any(shim.mutation_verb(call.argv)
                         or call.argv[1:3] == ['project', 'generate']
                         or call.argv[1:4] == ['template', 'generate', 'project']
                         for call in scan.calls)
                     or shim.mutation_hint(command))
        if event == 'PreToolUse' and protected:
            return deny('An absolute, accessible project cwd is required for Salesforce CLI checks.')
        return {"continue": True}
    if event == 'PreToolUse':
        if payload.get('tool_name') == 'apply_patch':
            return edit_advice.pre_edit(payload)
        return pre_shell(payload)
    if event == 'PostToolUse':
        if str(payload.get('tool_name', '')).startswith('mcp__'):
            response = payload.get('tool_response')
            if not isinstance(response, dict):
                return {'continue': True}
            failed = response.get('isError') is True
            telemetry.capture_event('mcp_tool_used', 'failure' if failed else 'success', payload)
            return {"continue": True}
        return post_shell(payload)
    if event == 'SessionStart':
        recover_stale_buffers(payload['session_id'])
        record_plugin_root()
        output = merge([invoke(telemetry.cmd_capture, payload,
                               ['sf-context', 'telemetry-capture', 'session_start']),
                        codex_startup.presentation(payload)], 'SessionStart')
        if output.get('systemMessage'):
            # Keep Codex's dedicated startup renderer in the same one-banner
            # session state as Claude's shared SessionStart renderer. Without these
            # markers, UserPromptSubmit treats the first user turn as a new welcome
            # opportunity and repaints the entire lockup.
            marker_session = context._plugin_session_id(payload['session_id'], 'codex')
            context._record_welcomed(marker_session)
            context._record_entered(marker_session)
        if telemetry._in_sf_project():
            output['hookSpecificOutput'] = {
                'hookEventName': 'SessionStart', 'additionalContext':
                'Salesforce Development is active in an SFDX project. '
                'Check installed Salesforce skills first and use the matching workflow. '
                'For this plugin’s packaged skill commands, resolve ${CLAUDE_PLUGIN_ROOT} and other '
                'package-relative executables against the installed Salesforce Development '
                'plugin root ' + str(ROOT) + '. Do not set Claude environment variables. '
                'Prefix each plugin runtime command with SF_AGENT_CLIENT=codex; hook '
                'subprocess environment changes do not persist in later shell tools. '
                'For other plugins, resolve their own package root from the loaded skill path. '
                'If a workflow requires an unavailable child skill, do not invent its '
                'implementation. Use supported plugin discovery/install with explicit '
                'user consent, then stop and request a fresh Codex session and resubmission. '
                'Verify the required skills in that fresh session before continuing; '
                'an on-disk install alone does not establish activation. '
                'If no skill applies, use SF CLI with --json; use direct Salesforce APIs '
                'only when neither a skill nor the CLI satisfies the task. '
                'Before org operations, verify the connected org and its environment; '
                'use an explicit target org when selecting a different org. '
                'For delegated work, name the owning skill and target org in the handoff. '
                'Production deployment and metadata deletion require explicit developer '
                'confirmation. Route production changes through platform-metadata-deploy\'s '
                'validate-then-quick-deploy path, and deletions through platform-destructive-deploy. '
                'Run code analysis on generated Apex before proposing deployment and '
                'explain governor-limit risks for bulk operations. '
                'Automatic deployment after file edits is disabled. '
                'These are primary-session instructions, not automatic activation of a '
                'Claude persona or a delegated Codex worker. Codex cannot verify installed '
                'skill invocation; skills-first advice does not enforce a dispatch ledger.',
            }
        return output
    if event == 'SessionEnd':
        return invoke(telemetry.cmd_flush, payload, ['sf-context', 'telemetry-flush'])
    if event == 'Stop':
        return feedback_nudge(payload)
    if event == 'SubagentStart':
        payload['tool_input'] = {'agent_type': payload.get('agent_type', '')}
        telemetry.capture_event('agent_dispatched', '', payload)
    return {"continue": True}


def codex_guidance(output: dict) -> dict:
    """Point scaffold guidance at an entrypoint in the installed package."""
    entry = shlex.quote(str(ROOT / 'scripts/sf-context'))
    def rewrite(value):
        if isinstance(value, dict):
            return {key: rewrite(item) for key, item in value.items()}
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, str):
            return value.replace('/salesforce-development:setup', entry + ' check-tools')
        return value
    return rewrite(output)


def feedback_nudge(payload: dict) -> dict:
    sid = telemetry.session_identity(payload)
    if (not sid or not context._feedback_enabled()
            or telemetry._feedback_ineligibility_reason() is not None
            or context._feedback_already_nudged(sid)):
        return {"continue": True}
    # Only scrubbed, allowlisted activity is evidence here. Raw transcript prose
    # cannot prove execution; shell activity awaits a host exit-status contract.
    try:
        with telemetry._session_buffer(sid).open() as source:
            substantive = any(json.loads(line).get('event') in
                              {'mcp_tool_used', 'command_invoked', 'skill_dispatched'}
                              for line in source)
    except (OSError, ValueError):
        substantive = False
    if not substantive or not context._record_feedback_nudge(sid):
        return {"continue": True}
    entry = shlex.quote(str(ROOT / 'scripts/sf-context'))
    return {"continue": True, "hookSpecificOutput": {
        "hookEventName": "Stop", "additionalContext":
        "Optional Salesforce plugin feedback: ask the user for an integer rating from 1 to 5. "
        "If they choose to submit it, run SF_AGENT_CLIENT=codex " + entry +
        " feedback-record RATING, replacing RATING with that integer. "
        "Only the numeric rating is recorded; never pass comments. "
        "Offered once per session when SFDX_FEEDBACK=1; skip if mid-task.",
    }}


# Matches the raw event text when the shared scanner is unavailable. It is broader than
# `shim.mutation_hint`; over-matching only costs a denied call that can be rerun.
_FALLBACK_MUTATION_HINT = re.compile(
    r'(?:\bsf(?:dx)?\b|@salesforce/cli).*(?:deploy|delete|push)', re.IGNORECASE | re.DOTALL)


def _shell_text(raw_event: str) -> str:
    """The text of the shell command in a raw hook event, '' for non-shell tools."""
    try:
        event = json.loads(raw_event)
        tool_input = event.get('tool_input', event.get('toolInput'))
    except (ValueError, AttributeError):
        # Not parseable: the shape is unknown, so scan everything.
        return raw_event
    if not isinstance(tool_input, dict):
        return '' if tool_input is None else json.dumps(tool_input, default=str)
    name = str(event.get('tool_name', event.get('toolName', '')))
    if name in ('apply_patch', 'Write', 'Edit') or name.startswith('mcp__'):
        return ''
    command = tool_input.get('command')
    return command if isinstance(command, str) else json.dumps(tool_input, default=str)


def _may_mutate_org(raw_event: str) -> bool:
    text = _shell_text(raw_event)
    if _FALLBACK_MUTATION_HINT.search(text):
        return True
    return not _RUNTIME_UNAVAILABLE and shim.mutation_hint(text)


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ''
    raw_event = ''
    try:
        # Bytes first, so an undecodable event still reaches the fail-closed scan.
        stream = getattr(sys.stdin, 'buffer', None)
        raw_event = (stream.read().decode('utf-8', 'replace') if stream is not None
                     else sys.stdin.read())
        payload = json.loads(raw_event)
        if not isinstance(payload, dict):
            raise ValueError('invalid hook event')
        if _RUNTIME_UNAVAILABLE:
            raise RuntimeError('hook runtime unavailable')
        result = dispatch(event, payload)
        rendered = json.dumps(codex_guidance(result))
    except Exception:
        # Fail closed only for a call that could deploy or delete; every other tool
        # call, in any directory, proceeds with a visible warning.
        if event == 'PreToolUse' and _may_mutate_org(raw_event):
            result = deny('Safety checks could not complete, so this possible Salesforce '
                          'deploy/delete was not run. Repair the plugin hook, then retry.')
        elif event == 'PreToolUse':
            result = {"continue": True, "systemMessage":
                      'Salesforce Development safety checks could not run for this tool call.'}
        else:
            result = {"continue": True}
        rendered = json.dumps(result)
    print(rendered)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
