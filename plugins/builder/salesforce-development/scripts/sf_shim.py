#!/usr/bin/env python3
"""sf_shim — shared, dependency-free cross-platform command-building primitives.

Extracted so sf_context.py and sf_telemetry.py share ONE definition of the Windows
batch-shim invocation and the cmd.exe metacharacter refusal sets, instead of the
byte-for-byte duplicate that had already drifted (sf_telemetry's copy gated the shim
branch on os.name, inlined the metachar check, and called shutil.which directly).
This module imports nothing from either consumer, so it breaks the circular-import
excuse that motivated the duplication. The bash deploy gate keeps the SAME arg set.

It also holds the one lexical shell scanner (`scan_sf`) that both the Codex shell hook
and the deploy gate use to find literal CLI calls, their verb and their target org.
"""
from __future__ import annotations

import os
import re
import shlex
from typing import NamedTuple, Optional

# A resolved path ending in one of these is a Windows batch shim that must be
# launched through cmd.exe rather than exec'd directly.
_WINDOWS_SHIM_SUFFIXES = (".cmd", ".bat")

# cmd.exe re-parses the command line it is handed, so these characters keep shell
# meaning inside a batch-shim invocation even though we pass an argv array
# (list2cmdline quotes spaces/quotes, not these). We refuse them on the shim path
# instead of trying to quote them — a fully-correct cmd.exe quoter is notoriously
# hard, and every legitimate caller passes fixed subcommands/flags plus an org
# alias, none of which contain these.
#
# Two sets: ARGS are fully controlled (subcommands/flags/aliases) so we reject the
# widest set, including `(` `)` (grouping) and `!` (delayed expansion). The resolved
# shim PATH is system-provided and legitimately contains `(`/`)` (e.g.
# "C:\\Program Files (x86)\\..."), so its guard omits those — but still rejects the
# chars cmd.exe reparses even inside quotes (`%`, `!`), the quote-breaker (`"`), and
# the redirection/chaining set.
_CMD_ARG_METACHARACTERS = ("&", "|", "<", ">", "^", "%", '"', "!", "(", ")", "\n", "\r")
_CMD_PATH_METACHARACTERS = ("&", "|", "<", ">", "^", "%", '"', "!", "\n", "\r")


def _contains_any(value: str, chars) -> bool:
    return any(ch in value for ch in chars)


def is_windows_shim(path: str) -> bool:
    """True when a resolved path is a Windows batch shim needing a cmd wrapper."""
    return path.lower().endswith(_WINDOWS_SHIM_SUFFIXES)


def build_argv(resolved: str, args: Optional[list] = None) -> Optional[list]:
    """Given an ALREADY-RESOLVED executable path, return the spawnable argv, or None
    (fail closed) on the shim path when a cmd metacharacter would be reparsed.

    Resolution (NAME -> path) stays with each caller so their own resolver mocks
    keep working; this shared helper owns only the drift-prone shim-wrapping + the
    metacharacter refusal that had already diverged between the two copies.

    - A `.cmd`/`.bat` shim -> [COMSPEC, "/c", resolved, *args] (COMSPEC from env,
      fallback "cmd.exe"). Passing an argv array preserves argv boundaries but is NOT
      injection-proof for a batch shim (cmd.exe re-parses the serialized line), so we
      REFUSE (None) if the resolved shim PATH holds a reparse-dangerous char or any
      ARG holds a cmd metacharacter — rather than attempt an error-prone quoter.
    - Anything else -> [resolved, *args] for a direct shell=False spawn.
    """
    args = list(args) if args else []
    if is_windows_shim(resolved):
        if _contains_any(resolved, _CMD_PATH_METACHARACTERS) or any(
            _contains_any(str(a), _CMD_ARG_METACHARACTERS) for a in args
        ):
            return None
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        return [comspec, "/c", resolved, *args]
    return [resolved, *args]


# Host-provided session ids become private runtime-file keys; anything else is
# ignored so correlation fails closed instead of sharing a global namespace.
_HOST_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def host_session_id(explicit: object = "", client: str = "claude",
                    environ: Optional[dict] = None) -> str:
    """Resolve one host session identity with a single precedence order.

    An explicit event/argument id wins. Otherwise Codex uses the per-thread
    ``CODEX_THREAD_ID`` before the root-shared ``CODEX_SESSION_ID`` so subagent
    threads never share consent or telemetry state with the root thread, and
    Claude Code uses ``CLAUDE_CODE_SESSION_ID``. The first present environment
    value decides; an invalid one resolves to "" rather than falling through.
    """
    if isinstance(explicit, str) and explicit:
        return explicit
    env = os.environ if environ is None else environ
    names = ("CODEX_THREAD_ID", "CODEX_SESSION_ID") if client == "codex" else (
        "CLAUDE_CODE_SESSION_ID",)
    for name in names:
        value = env.get(name, "")
        if value:
            return value if isinstance(value, str) and _HOST_SESSION_ID.fullmatch(value) else ""
    return ""


def no_color_env() -> dict:
    """Child env with color forced off. Claude Code exports FORCE_COLOR=3 to hook
    processes, and `sf ... --json` then emits ANSI-colorized JSON even when piped, so
    the JSON parse silently fails (forcedotcom/sf-skills#349). The bash deploy gate
    sets the same two variables in sf_cli()."""
    return {**os.environ, "FORCE_COLOR": "0", "NO_COLOR": "1"}


# subprocess.CREATE_NO_WINDOW, spelled out because the subprocess constant only
# exists on Windows builds of Python.
_CREATE_NO_WINDOW = 0x08000000


def no_window_kwargs() -> dict:
    """Spawn kwargs that keep a console child (`cmd.exe /c sf.cmd`, npm, node) from
    opening a console window on Windows. A hook process without a console of its
    own (the DETACHED telemetry sender, or a hook its host launched without one)
    otherwise gives every such child a new, visible cmd.exe window. Output is
    captured through pipes, so the child needs no console. Empty off Windows, so
    POSIX spawns are unchanged."""
    return {"creationflags": _CREATE_NO_WINDOW} if os.name == "nt" else {}


_ASSIGNMENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
_REDIRECT = re.compile(r'(?:[<>]+[&|]?|&>+)')
_SEPARATOR_CHARS = '();|&'
# Tokens that can precede the executed command in a segment. Wrappers in
# _ARG_WRAPPERS may carry their own options, so the CLI name is searched after them.
_PREFIXES = frozenset({'!', '{', '}', 'command', 'exec', 'builtin', 'time', 'env', 'nohup',
                       'setsid', 'sudo', 'nice', 'timeout', 'xargs', 'watch', 'stdbuf',
                       'ionice', 'unbuffer',
                       'if', 'elif', 'while', 'until', 'then', 'else', 'do'})
_ARG_WRAPPERS = frozenset({'command', 'exec', 'env', 'nohup', 'setsid', 'sudo', 'nice',
                           'time', 'timeout', 'xargs', 'watch', 'stdbuf', 'ionice',
                           'unbuffer'})
_SHELLS = frozenset({'bash', 'sh', 'zsh', 'dash', 'ksh'})
_SHELL_COMMAND_OPTION = re.compile(r'-[A-Za-z]*c[A-Za-z]*')
# Interpreters that run code delivered as an argument, `env -S` (which re-splits a
# string into a command) and `find -exec` (which runs a nested command) are as opaque
# to the lexical scan as `sh -c`.
_INTERPRETERS = re.compile(r'(?:python[0-9.]*|node|nodejs|deno|bun|perl|ruby|php)')
_INTERPRETER_CODE_OPTION = re.compile(r'-[A-Za-z]*[ce][A-Za-z]*|--eval|--command|--print')
_ENV_SPLIT_OPTION = re.compile(r'-[A-Za-z]*S[A-Za-z]*|--split-string(?:=.*)?')
_FIND_EXEC_OPTION = re.compile(r'-(?:exec|execdir|ok|okdir)')
_COMMAND_ID = re.compile(r'[A-Za-z][A-Za-z0-9-]*(?::[A-Za-z][A-Za-z0-9-]*)+')
_NPX_CLI = re.compile(r'@salesforce/cli(?:@\S*)?')
_LITERAL_ORG = re.compile(r'[^\s$`\'"\\]+')
_TARGET_FLAGS = ('--target-org', '--targetusername')

# Alternate spellings of the deploy/delete commands, longest first.
_COMMAND_ALIASES = (
    (('force', 'source', 'deploy', 'report'), ('project', 'deploy', 'report')),
    (('force', 'source', 'deploy', 'cancel'), ('project', 'deploy', 'cancel')),
    (('force', 'mdapi', 'deploy', 'report'), ('project', 'deploy', 'report')),
    (('force', 'mdapi', 'deploy', 'cancel'), ('project', 'deploy', 'cancel')),
    (('deploy', 'metadata', 'validate'), ('project', 'deploy', 'validate')),
    (('deploy', 'metadata', 'quick'), ('project', 'deploy', 'quick')),
    (('deploy', 'metadata', 'cancel'), ('project', 'deploy', 'cancel')),
    (('deploy', 'metadata', 'report'), ('project', 'deploy', 'report')),
    (('deploy', 'metadata', 'resume'), ('project', 'deploy', 'resume')),
    (('deploy', 'metadata', 'preview'), ('project', 'deploy', 'preview')),
    (('force', 'source', 'deploy'), ('project', 'deploy', 'start')),
    (('force', 'source', 'push'), ('project', 'deploy', 'start')),
    (('force', 'source', 'delete'), ('project', 'delete', 'source')),
    (('force', 'mdapi', 'deploy'), ('project', 'deploy', 'start')),
    (('deploy', 'metadata'), ('project', 'deploy', 'start')),
)

# Raw-text sign of a deploy/delete, used only to refuse commands whose execution
# the lexical scan cannot follow (see scan_sf's `opaque`).
SF_MUTATION_HINT = re.compile(
    r'(?:\b(?:sf|sfdx)(?:\.cmd|\.exe)?\b|@salesforce/cli)'
    r'(?:\S*\s+deploy\b'
    r'|.*?(?:\bproject\b.*?(?<!\w)(?<!\w-)(?:deploy|delete)(?!-?\w)'
    r'|\bproject:(?:deploy|delete)\b'
    r'|\bdeploy[:\s]+metadata\b'
    r'|\bforce[:\s]+(?:source[:\s]+(?:deploy|delete|push)|mdapi[:\s]+deploy)\b))',
    re.IGNORECASE | re.DOTALL,
)


class SfCall(NamedTuple):
    """One literal CLI invocation in command position."""
    argv: list    # normalized: argv[0] == 'sf', alias spellings mapped to `project ...`
    prefix: list  # assignments and wrapper tokens before the CLI name
    xargs: bool   # run through xargs, whose stdin can append arguments


class SfScan(NamedTuple):
    calls: list
    segments: list  # every command segment's tokens, redirections removed
    unparsed: bool  # a line could not be lexed and was split on whitespace
    opaque: bool    # some execution the lexer cannot follow (eval, sh -c, `...`, ...)
    # A segment looks like a deploy/delete but holds no literal CLI call: an unknown wrapper,
    # or text that only mentions one. Judged per segment, so a traceable call elsewhere in
    # the line never vouches for it.
    untraced: bool = False
    # A deploy/delete call sits inside a construct that can run it more than once (a
    # loop, a function body, `watch`), so one confirmation or one verification could
    # cover several executions.
    repeating: bool = False


def _strip_suffix(value: str, suffix: str) -> str:
    return value[:-len(suffix)] if suffix and value.endswith(suffix) else value


def _command_name(token: str) -> str:
    name = token.replace(chr(92), '/').rsplit('/', 1)[-1].lower()
    for suffix in ('.cmd', '.exe', '.bat'):
        name = _strip_suffix(name, suffix)
    return name


_PUNCTUATION = '();<>|&'
# Private-use stand-ins for punctuation that is quoted or escaped, so the lexer sees an
# ordinary word and the argument is not mistaken for a separator or redirection.
_PROTECTED = {char: chr(0xE000 + index) for index, char in enumerate(_PUNCTUATION)}
_UNPROTECT = {value: key for key, value in _PROTECTED.items()}


def _protect_punctuation(text: str) -> str:
    """Hide punctuation that bash treats as an ordinary character.

    Walks the text the way bash does: outside quotes a backslash escapes the next
    character (so `\\\\;` is an escaped backslash followed by a real separator), and a
    quoted run made only of punctuation (`";"`) is a word, not a separator. Everything
    else is left for the lexer.
    """
    out, index, length = [], 0, len(text)
    while index < length:
        char = text[index]
        if char == '\\' and index + 1 < length:
            following = text[index + 1]
            if following in _PROTECTED:
                out.append('\x00' + _PROTECTED[following])
            else:
                out.append(char + following)
            index += 2
        elif char in '"\'':
            end = index + 1
            while end < length and text[end] != char:
                end += 2 if char == '"' and text[end] == '\\' else 1
            if end >= length:
                out.append(text[index:])
                break
            content = text[index + 1:end]
            if content and all(item in _PROTECTED for item in content):
                out.append('\x00' + ''.join(_PROTECTED[item] for item in content))
            else:
                out.append(text[index:end + 1])
            index = end + 1
        else:
            out.append(char)
            index += 1
    return ''.join(out)


def _lex(text: str) -> list:
    tokens = _lex_protected(_protect_punctuation(text))
    # A protected word keeps a leading NUL, so it never reads as punctuation.
    return [''.join(_UNPROTECT.get(char, char) for char in token) for token in tokens]


def _lex_protected(text: str) -> list:
    lex = shlex.shlex(text, posix=True, punctuation_chars=_PUNCTUATION)
    lex.whitespace_split = True
    # Bash only starts a comment at a word boundary; a mid-word `#` (URLs) is
    # literal. Reading comment text as words over-matches, the safe direction.
    lex.commenters = ''
    return list(lex)


def _fallback_tokens(text: str) -> list:
    tokens = []
    for line in text.split('\n'):
        tokens.extend(word.strip('\'"') for word in line.split())
        tokens.append(';')
    return [token for token in tokens if token]


class _State:
    def __init__(self):
        self.segments = []
        self.unparsed = False
        self.opaque = False


def _add_segments(tokens: list, state: _State) -> list:
    """Split one logical line into segments; return its pending heredocs."""
    heredocs = []
    current, fed = [], False
    redirect = heredoc = False
    for token in [*tokens, ';']:
        if _REDIRECT.fullmatch(token):
            if current and current[-1].isdigit():
                current.pop()
            if token == '<<<':
                state.opaque = True
            redirect, heredoc = True, token == '<<'
            continue
        if redirect:
            if heredoc:
                strip_tabs = token.startswith('-')
                heredocs.append((token[1:] if strip_tabs else token, strip_tabs))
                fed = True
            redirect = False
            continue
        if token and all(c in _SEPARATOR_CHARS for c in token):
            if current:
                state.segments.append((current, fed))
            current, fed = [], False
        else:
            current.append(token)
    return heredocs


def _scan_text(text: str, heredoc_bodies: str, depth: int, state: _State) -> None:
    lines = text.split('\n')
    index, buffer = 0, None
    while index < len(lines):
        buffer = lines[index] if buffer is None else buffer + '\n' + lines[index]
        index += 1
        try:
            tokens = _lex(buffer)
        except ValueError:
            if index < len(lines):
                continue  # a quoted newline: the logical line continues
            tokens = _fallback_tokens(buffer)
            state.unparsed = True
        buffer = None
        for delimiter, strip_tabs in _add_segments(tokens, state):
            body = []
            while index < len(lines):
                line = lines[index]
                index += 1
                if (line.lstrip('\t') if strip_tabs else line) == delimiter:
                    break
                body.append(line)
            if heredoc_bodies == 'scan' and depth < 2:
                _scan_text('\n'.join(body), heredoc_bodies, depth + 1, state)


def _normalize_sf(args: list) -> list:
    words = []
    for index, token in enumerate(args):
        if token.startswith('-'):
            words.extend(args[index:])
            break
        words.extend(token.split(':') if _COMMAND_ID.fullmatch(token) else [token])
    lowered = [word.lower() for word in words]
    for alias, canonical in _COMMAND_ALIASES:
        if tuple(lowered[:len(alias)]) == alias:
            return ['sf', *canonical, *words[len(alias):]]
    if lowered[:1] == ['deploy'] and (len(words) == 1 or words[1].startswith('-')):
        return ['sf', 'project', 'deploy', 'start', *words[1:]]
    return ['sf', *words]


def _segment_is_opaque(tokens: list, command: list, fed: bool) -> bool:
    name = _command_name(command[0]) if command else ''
    if name in {'eval', 'source', '.', 'xargs'}:
        return True
    if name in _SHELLS and (fed or not any(not t.startswith('-') for t in command[1:])):
        return True  # a shell reading a heredoc or stdin
    if command and '$' in command[0]:
        return True  # a variable in command position can name the CLI
    for index, token in enumerate(tokens):
        word = _command_name(token)
        later = tokens[index + 1:]
        if word in {'eval', 'xargs'}:
            return True
        if word in _SHELLS and any(_SHELL_COMMAND_OPTION.fullmatch(t) for t in later):
            return True
        if _INTERPRETERS.fullmatch(word) and any(_INTERPRETER_CODE_OPTION.fullmatch(t) for t in later):
            return True
        if word == 'env' and any(_ENV_SPLIT_OPTION.fullmatch(t) for t in later):
            return True
        if word == 'find' and any(_FIND_EXEC_OPTION.fullmatch(t) for t in later):
            return True
    return False


def _sf_call(tokens: list) -> tuple:
    """Return (SfCall or None, command tokens after prefixes)."""
    current, prefix, xargs = list(tokens), [], False
    while current and (_ASSIGNMENT.match(current[0]) or _command_name(current[0]) in _PREFIXES):
        name = _command_name(current[0])
        prefix.append(current.pop(0))
        xargs = xargs or name == 'xargs'
        if name in _ARG_WRAPPERS:
            for index, arg in enumerate(current):
                if _command_name(arg) in {'sf', 'sfdx', 'npx'}:
                    prefix.extend(current[:index])
                    current = current[index:]
                    break
    if not current:
        return None, current
    name = _command_name(current[0])
    if name in {'sf', 'sfdx'}:
        return SfCall(_normalize_sf(current[1:]), prefix, xargs), current
    if name == 'npx':
        for index, arg in enumerate(current[1:], 1):
            # `npx sf ...`/`npx sfdx ...` name the CLI's binary; `npx @salesforce/cli ...`
            # (optionally followed by the binary name) names its package.
            if _NPX_CLI.fullmatch(arg) or _command_name(arg) in {'sf', 'sfdx'}:
                rest = current[index + 1:]
                if _NPX_CLI.fullmatch(arg) and rest and _command_name(rest[0]) in {'sf', 'sfdx'}:
                    rest = rest[1:]
                return SfCall(_normalize_sf(rest), prefix, xargs), current
            if not arg.startswith('-'):
                break
    return None, current


_OPAQUE_MUTATION_WORD = re.compile(r'\b(?:deploy|delete|force:source:push)\b', re.IGNORECASE)
# `name()` followed by a brace or subshell body; the lexer drops the empty parentheses.
_FUNCTION_DEFINITION = re.compile(r'[\w.:@-]\s*\(\s*\)')
_LOOP_WORDS = frozenset({'while', 'until', 'for', 'select', 'function'})
_CLI_NAMES = frozenset({'sf', 'sfdx', 'npx'})


def _runs_repeatedly(tokens: list) -> bool:
    """Whether `watch` wraps the CLI call in this segment."""
    for token in tokens:
        name = _command_name(token)
        if name in _CLI_NAMES:
            return False
        if name == 'watch':
            return True
    return False


def _in_repeat_construct(segments: list, index: int) -> bool:
    """Whether the segment is inside a loop or a function body.

    The lexer flattens nesting, so any loop keyword or function definition earlier in the
    line is treated as enclosing the call; over-matching only denies a command that can be
    rewritten as one plain call.
    """
    for position in range(index):
        head = segments[position][:1]
        if head and head[0] in _LOOP_WORDS:
            return True
        # `name(){ ... }`: a lone word followed by a brace group.
        if (len(segments[position]) == 1 and position + 1 < len(segments)
                and segments[position + 1][:1] == ['{']):
            return True
    return False


def scan_sf(command: str, *, heredoc_bodies: str = 'skip') -> SfScan:
    """Lexically scan a shell command for literal CLI calls in command position.

    ``heredoc_bodies='skip'`` treats heredoc bodies as data (a script being
    written); ``'scan'`` also reads them as commands. Expansion, evaluation and
    interpreter-delivered commands are not followed; they set ``opaque``.
    """
    if not isinstance(command, str):
        command = ''
    text = command.replace('\\\n', '').replace("$'", "'").replace('$"', '"')
    state = _State()
    _scan_text(text, heredoc_bodies, 0, state)
    opaque = state.opaque or any(mark in text for mark in ('`', '$(', '<(', '>('))
    calls = []
    untraced = repeating = False
    segments = [tokens for tokens, _ in state.segments]
    for index, (tokens, fed) in enumerate(state.segments):
        call, rest = _sf_call(tokens)
        if call is not None:
            calls.append(call)
            if mutation_verb(call.argv) and (
                    _in_repeat_construct(segments, index) or _runs_repeatedly(tokens)):
                repeating = True
        else:
            if _segment_is_opaque(tokens, rest, fed):
                opaque = True
            if mutation_hint(' '.join(tokens)):
                untraced = True
    if not repeating and _FUNCTION_DEFINITION.search(text) and any(
            mutation_verb(call.argv) for call in calls):
        repeating = True
    # An execution the lexer cannot follow, next to a deploy/delete word, is refused even
    # when quote-splitting or a variable keeps the text from reading as an `sf` call.
    if opaque and any(_OPAQUE_MUTATION_WORD.search(token)
                      for tokens in segments for token in tokens):
        untraced = True
    return SfScan(calls, segments, state.unparsed, opaque, untraced, repeating)


def literal_sf_commands(command: str) -> list:
    """Normalized argv of each literal CLI call in shell command position."""
    return [call.argv for call in scan_sf(command).calls]


def mutation_verb(argv: list) -> Optional[str]:
    """Classify a normalized argv: deploy-start, deploy-quick, deploy-other, delete or None."""
    if argv[1:3] == ['project', 'deploy']:
        sub = argv[3] if len(argv) > 3 else ''
        if sub.startswith('-'):
            return 'deploy-start'
        return {'start': 'deploy-start', 'quick': 'deploy-quick'}.get(sub, 'deploy-other')
    if argv[1:3] == ['project', 'delete']:
        return 'delete'
    return None


def target_orgs(argv: list) -> tuple:
    """Return (distinct literal target orgs in order, ambiguous) for one call."""
    targets, ambiguous = [], False
    index = 1
    while index < len(argv):
        token, value = argv[index], None
        if token in _TARGET_FLAGS or token in ('-o', '-u'):
            if index + 1 < len(argv) and not argv[index + 1].startswith('-'):
                value = argv[index + 1]
                index += 1
            else:
                ambiguous = True
        elif any(token.startswith(flag + '=') for flag in _TARGET_FLAGS):
            value = token.split('=', 1)[1]
        elif token[:2] in ('-o', '-u') and not token.startswith('--'):
            value = token[3:] if token[2:3] == '=' else token[2:]
        if value is not None:
            if _LITERAL_ORG.fullmatch(value):
                targets.append(value)
            else:
                ambiguous = True
        index += 1
    return list(dict.fromkeys(targets)), ambiguous


def inline_prod_confirmation(call: SfCall) -> bool:
    """The Claude override marker, honored only on the call itself.

    A leading ``CONFIRM_PROD=1`` assignment of this call, or a
    ``--I-CONFIRM-PROD`` argument before any comment word.
    """
    if 'CONFIRM_PROD=1' in call.prefix:
        return True
    for token in call.argv[1:]:
        if token.startswith('#'):
            return False
        if token == '--I-CONFIRM-PROD':
            return True
    return False


def mutation_hint(text: str) -> bool:
    return bool(SF_MUTATION_HINT.search(text))


def mutation_context_is_ambiguous(command: str) -> bool:
    """Refuse context changes that the event cwd/environment cannot describe."""
    scan = scan_sf(command)
    if scan.unparsed:
        return True
    for argv in scan.segments:
        if any('$' in token or '`' in token or
               (_ASSIGNMENT.match(token) and token != 'CONFIRM_PROD=1')
               for token in argv):
            return True
        for index, token in enumerate(argv):
            name = _command_name(token)
            if name == 'exec' and index + 1 < len(argv) and argv[index + 1].startswith('-'):
                return True
            if token == 'CONFIRM_PROD=1':
                continue
            if name in {'!', '{', 'command', 'builtin', 'exec', 'if', 'elif', 'then',
                        'else', 'do', 'while', 'until'} or token.startswith('-'):
                continue
            if (name in {'cd', 'pushd', 'popd', 'export', 'unset', 'source', '.',
                         'env', 'sudo', 'nice', 'setsid', 'nohup', 'time'}
                    or _ASSIGNMENT.match(token)):
                return True
            break
    return any(argv[1:3] in (['config', 'set'], ['config', 'unset'])
               for argv in literal_sf_commands(command))
