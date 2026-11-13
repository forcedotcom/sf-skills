"""Codex advisory-only adaptation of shared Salesforce skill routing.

Patch structure follows the bundled LWC parser contract. No patch is executed,
file contents read, dispatch ledger fabricated, or deployment initiated here.
"""
from __future__ import annotations
from pathlib import Path
import shlex
import sf_context as context
import sf_telemetry as telemetry
from sf_shim import literal_sf_commands

ROOT = Path(__file__).resolve().parents[1]


def patch_paths(patch: str) -> list[tuple[str, str | None, str, str]]:
    """Parse apply_patch structure, returning surviving add/update destinations.

    Context and added lines retain their prefix, so header-like file contents
    cannot become paths. Reject the entire patch if its structure is malformed.
    """
    if not isinstance(patch, str):
        raise ValueError("Patch must be text")
    if len(patch) > 1_000_000:
        raise ValueError("Patch exceeds advisory budget")
    lines = patch.strip().splitlines()
    if len(lines) < 3 or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise ValueError("Invalid patch envelope")
    paths = []
    i = 1
    while i < len(lines) - 1:
        header = lines[i]
        kind = next((k for k in ("Add", "Update", "Delete")
                     if header.startswith(f"*** {k} File: ")), None)
        if kind is None:
            raise ValueError("Invalid patch file header")
        source = header.split(": ", 1)[1]
        if not source or "\x00" in source:
            raise ValueError("Invalid patch path")
        destination = source
        i += 1
        if kind == "Update" and i < len(lines) - 1 and lines[i].startswith("*** Move to: "):
            destination = lines[i][13:]
            if not destination or "\x00" in destination:
                raise ValueError("Invalid move destination")
            i += 1
        body = []
        while i < len(lines) - 1 and not any(lines[i].startswith(f"*** {k} File: ") for k in ("Add", "Update", "Delete")):
            body.append(lines[i])
            i += 1
        if kind == "Delete" and body:
            raise ValueError("Delete section has a body")
        if kind == "Add" and any(not line.startswith("+") for line in body):
            raise ValueError("Invalid add section")
        if kind == "Update":
            if not body:
                raise ValueError("Update requires content")
            content, header, ended = False, False, False
            for line in body:
                if ended:
                    if not line.strip():
                        continue
                    if line == "@@" or line.startswith("@@ "):
                        ended = False
                    else:
                        raise ValueError("Content after end-of-file marker")
                if line == "*** End of File":
                    if not content:
                        raise ValueError("Empty update chunk")
                    ended = True
                elif line == "@@" or line.startswith("@@ "):
                    if header and not content:
                        raise ValueError("Empty update chunk")
                    header, content = True, False
                elif not line or line.startswith((" ", "+", "-")):
                    content = True
                else:
                    raise ValueError("Invalid update section")
            if not content:
                raise ValueError("Empty update chunk")
        # Include both sides for containment checks; deleted/old paths are not read.
        paths.append((source, destination if kind != "Delete" else None, kind,
                      "\n".join(line[1:] for line in body if line.startswith("+"))))
        if len(paths) > 256:
            raise ValueError("Patch exceeds advisory file budget")
    return paths


def contained_path(root: Path, name: str) -> Path:
    root = root.resolve()
    path = (root / name).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("Patch path escapes event cwd") from None
    if path == root:
        raise ValueError("Patch path escapes event cwd")
    return path



def advice(matches: list[tuple[str, str]]) -> dict:
    if context._skills_first_mode(include_option=False) == 'off':
        return {'continue': True}
    hints = []
    for skill, reason in matches:
        if skill == 'the matching platform metadata skill':
            skill = 'installed Salesforce metadata skills (check for a matching workflow)'
        elif not (ROOT / 'skills' / skill / 'SKILL.md').is_file():
            continue
        if skill in hints:
            continue
        hints.append(skill)
    if not hints:
        return {'continue': True}
    return {'continue': True, 'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'additionalContext':
        'Salesforce skills-first advisory: check ' + ', '.join(hints) +
        ' before continuing this operation. Use a matching installed skill when it applies; '
        'continue the current workflow if that skill already owns this step. '
        'This advisory does not prove skill invocation and does not block the tool. '
        'Automatic deployment after edits is disabled.',
    }}


def pre_edit(payload: dict) -> dict:
    try:
        if not telemetry._in_sf_project():
            return {'continue': True}
        inputs = payload.get('tool_input')
        if not isinstance(inputs, dict):
            raise ValueError('Invalid edit input')
        root = Path(payload['cwd']).resolve(strict=True)
        entries = patch_paths(inputs.get('command'))
        matches = []
        for source, destination, kind, content in entries:
            contained_path(root, source)
            if destination is None:
                continue
            contained_path(root, destination)
            match = context._skills_first_match('Write' if kind == 'Add' else 'Edit',
                                                {'file_path': destination, 'content': content})
            if match:
                matches.append(match)
            if source != destination:
                original_match = context._skills_first_match('Edit', {'file_path': source})
                if original_match:
                    matches.append(original_match)
        return advice(matches)
    except (KeyError, OSError, TypeError, ValueError):
        try:
            if context._skills_first_mode(include_option=False) == 'off':
                return {'continue': True}
        except Exception:
            pass
        return {'continue': True, 'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'additionalContext':
            'Salesforce edit advice unavailable: the patch paths or project cwd could not '
            'be verified. Check the installed owning skill explicitly. '
            'This advisory does not block edits; automatic deployment is disabled.',
        }}


def pre_shell_advice(payload: dict) -> dict:
    if not telemetry._in_sf_project():
        return {'continue': True}
    matches = []
    for argv in literal_sf_commands(context._hook_command(payload)):
        match = context._skills_first_match('Bash', {'command': shlex.join(argv[:4])})
        if match:
            matches.append(match)
    return advice(matches)
