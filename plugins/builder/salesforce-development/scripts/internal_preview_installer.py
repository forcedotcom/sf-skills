#!/usr/bin/env python3
"""Guarded deterministic installer for explicitly authorized internal previews."""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable, Mapping, Optional

try:
    import capability_registry as registry
except ImportError:
    module_path = Path(__file__).resolve().parent / "capability_registry.py"
    spec = importlib.util.spec_from_file_location("internal_preview_capability_registry", module_path)
    if spec is None or spec.loader is None:
        raise
    registry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry)

INTERNAL_NOTICE = "INTERNAL PREVIEW — not publicly supported"
SOURCE_CHANNEL = "internal-preview"
CLI_VERSION = "skills@1.5.20"
DEFAULT_TIMEOUT_SECONDS = 120
MAX_STREAM_BYTES = 4000
# Trust boundary (#1030 adversarial review, finding 4): the npm_config_registry /
# npm_config_ca(file) keys below are forwarded on purpose so an internal user behind
# a corporate proxy/registry can install. The consequence is that the pinned
# `skills@1.5.20` spec carries no lockfile/integrity hash, so `npx` re-resolves it
# through whatever registry the environment points at — the version pin is an
# ergonomic default, NOT a supply-chain integrity guarantee. The post-install
# canonical-tree hash check (see _destination_hash / the postcondition below) rejects
# tampered *skill content*, but it does NOT constrain what the fetched CLI executes at
# install time; arbitrary code execution at install time is inherent to running any
# `npx` package and is out of scope for this gate. Do not read the pin+hash as
# defense against a hostile registry.
_SUBPROCESS_ENV_KEYS = {
    "PATH", "HOME", "USERPROFILE", "TMPDIR", "TMP", "TEMP",
    "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
    "npm_config_cache", "npm_config_prefix", "npm_config_userconfig", "npm_config_tmp",
    "NPM_CONFIG_CACHE", "NPM_CONFIG_PREFIX", "NPM_CONFIG_USERCONFIG", "NPM_CONFIG_TMP",
    "npm_config_registry", "NPM_CONFIG_REGISTRY", "npm_config_ca", "NPM_CONFIG_CA",
    "npm_config_cafile", "NPM_CONFIG_CAFILE", "LANG", "COMSPEC", "SystemRoot",
    "SYSTEMROOT", "PATHEXT",
}


class InstallerError(ValueError):
    """A safe, non-sensitive installer denial or postcondition failure."""


def _base(name: object) -> dict:
    return {
        "notice": INTERNAL_NOTICE,
        "name": name if isinstance(name, str) and registry.NAME_PATTERN.fullmatch(name) else None,
        "sourceChannel": SOURCE_CHANNEL,
        "freshSessionRequired": True,
    }


def _error(name: object, message: str, *, execution: Optional[dict] = None) -> tuple[int, dict]:
    result = {**_base(name), "status": "error", "message": message}
    if execution is not None:
        result["execution"] = execution
    return 1, result


def _read_holds(path: Path, authoring_names: set[str]) -> set[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise InstallerError("internal checkout is invalid") from exc
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("internal:"):
            continue
        value = stripped.split(":", 1)[1].strip()
        if value:
            try:
                parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError) as exc:
                raise InstallerError("internal checkout is invalid") from exc
            if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                raise InstallerError("internal checkout is invalid")
            held = set(parsed)
        else:
            held = set()
            for child in lines[index + 1:]:
                if child and not child[0].isspace():
                    break
                match = re.match(r"^\s+-\s+(['\"]?)([a-z0-9-]+)\1\s*$", child)
                if child.strip() and not match:
                    raise InstallerError("internal checkout is invalid")
                if match:
                    held.add(match.group(2))
        if any(not registry.NAME_PATTERN.fullmatch(item) for item in held) or held - authoring_names:
            raise InstallerError("internal checkout is invalid")
        return held
    raise InstallerError("internal checkout is invalid")


def _validate_checkout(repo_root: Path, plugin_root: Path) -> tuple[Path, Path, dict[str, Path], dict[str, Path], dict[str, dict], set[str]]:
    try:
        repo = Path(repo_root).resolve(strict=True)
        plugin = Path(plugin_root).resolve(strict=True)
        plugin.relative_to(repo)
    except (OSError, ValueError) as exc:
        raise InstallerError("internal checkout is invalid") from exc
    config = repo / "config.yml"
    skills = repo / "skills"
    if config.is_symlink() or not config.is_file() or skills.is_symlink() or not skills.is_dir():
        raise InstallerError("internal checkout is invalid")
    try:
        authoring = registry.skill_directories(skills)
        foundation = registry.skill_directories(plugin / "skills")
        manifest = registry.load_public_manifest(plugin / registry.PUBLIC_MANIFEST_RELATIVE)
        public = {row["name"]: row for row in manifest["skills"]}
        held = _read_holds(config, set(authoring))
    except (OSError, registry.RegistryError, InstallerError) as exc:
        raise InstallerError("internal checkout is invalid") from exc
    return repo, plugin, authoring, foundation, public, held


def _validate_project(cwd: Path) -> Path:
    raw = Path(cwd).absolute()
    try:
        if raw.is_symlink():
            raise InstallerError("current directory is not a valid Salesforce project")
        project = raw.resolve(strict=True)
    except OSError as exc:
        raise InstallerError("current directory is not a valid Salesforce project") from exc
    marker = project / "sfdx-project.json"
    if not project.is_dir() or marker.is_symlink() or not marker.is_file():
        raise InstallerError("current directory is not a valid Salesforce project")
    return project


def _inspect_project_path(path: Path, project: Path) -> bool:
    """Validate one existing project path without following its final component."""
    try:
        stat = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise InstallerError("project destination is unsafe") from exc
    if path.is_symlink() or not path.is_dir():
        raise InstallerError("project destination is unsafe")
    try:
        path.resolve(strict=True).relative_to(project)
    except (OSError, ValueError) as exc:
        raise InstallerError("project destination is unsafe") from exc
    return True


def _inspect_destination_chain(project: Path, destination: Path) -> bool:
    _inspect_project_path(project, project)
    _inspect_project_path(project / ".claude", project)
    _inspect_project_path(project / ".claude" / "skills", project)
    return _inspect_project_path(destination, project)


def _stream_bytes(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, str):
        return len(value.encode("utf-8", errors="replace"))
    try:
        return len(str(value).encode("utf-8", errors="replace"))
    except Exception:
        return 0


def _execution(returncode: Optional[int], stdout: object, stderr: object, *, timed_out: bool) -> dict:
    stdout_bytes = _stream_bytes(stdout)
    stderr_bytes = _stream_bytes(stderr)
    return {
        "exitCode": returncode,
        "timedOut": timed_out,
        "stdoutBytes": stdout_bytes,
        "stdoutTruncated": stdout_bytes > MAX_STREAM_BYTES,
        "stderrBytes": stderr_bytes,
        "stderrTruncated": stderr_bytes > MAX_STREAM_BYTES,
    }


def _subprocess_env(env: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value for key, value in env.items()
        if isinstance(value, str)
        and (key in _SUBPROCESS_ENV_KEYS or re.fullmatch(r"LC_[A-Z0-9_]+", key))
    }


def _destination_hash(destination: Path, project: Path, expected_name: str) -> str:
    try:
        if destination.is_symlink() or not destination.is_dir():
            raise InstallerError("project destination is not a real directory")
        resolved = destination.resolve(strict=True)
        resolved.relative_to(project)
        skill = registry.read_skill(resolved / "SKILL.md")
        if skill["name"] != expected_name:
            raise InstallerError("project destination frontmatter is invalid")
        return registry.canonical_tree_sha256(resolved, safety_root=project)
    except (OSError, ValueError, registry.RegistryError) as exc:
        if isinstance(exc, InstallerError):
            raise
        raise InstallerError("project destination validation failed") from exc


def install_internal_preview(
    name: object,
    *,
    repo_root: Path,
    plugin_root: Path,
    cwd: Path,
    env: Mapping[str, str],
    runner: Callable = subprocess.run,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[int, dict]:
    """Install one eligible authoring variant into the current project.

    The caller's explicit ``internal-preview install`` command is the user
    authorization. This function independently requires the existing env gate;
    it never adds or changes that gate itself.
    """
    if env.get("SF_SKILLS_INTERNAL_PREVIEW") != "1":
        return _error(name, "internal preview authorization denied")
    if not isinstance(name, str) or len(name) > 64 or not registry.NAME_PATTERN.fullmatch(name):
        return _error(name, "internal preview request denied")
    if not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 300:
        return _error(name, "internal preview request denied")
    try:
        repo, _plugin, authoring, foundation, public, held = _validate_checkout(repo_root, plugin_root)
        project = _validate_project(cwd)
        source = authoring.get(name)
        if source is None or name not in held or name in foundation:
            raise InstallerError("internal preview request denied")
        expected_hash = registry.canonical_tree_sha256(source, safety_root=repo)
        if name in public and public[name]["treeSha256"] == expected_hash:
            raise InstallerError("internal preview request denied")
        destination = project / ".claude" / "skills" / name
        destination.parent.relative_to(project)
        destination_exists = _inspect_destination_chain(project, destination)
    except InstallerError as exc:
        return _error(name, str(exc))
    except (OSError, ValueError, registry.RegistryError):
        return _error(name, "internal preview request denied")

    if destination_exists:
        try:
            if _destination_hash(destination, project, name) != expected_hash:
                raise InstallerError("project destination is not authoring-exact")
        except InstallerError:
            return _error(name, "internal preview request denied")
        return 0, {
            **_base(name),
            "status": "already-installed",
            "provenance": "authoring-exact",
            "skillsLockPresent": (project / "skills-lock.json").is_file(),
        }

    argv = [
        "npx", "--yes", CLI_VERSION, "add", str(repo / "skills"),
        "--skill", name, "--agent", "claude-code", "--copy", "--yes",
    ]
    try:
        completed = runner(
            argv,
            cwd=project,
            env=_subprocess_env(env),
            capture_output=True,
            shell=False,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        execution = _execution(None, exc.output, exc.stderr, timed_out=True)
        return _error(name, "internal preview installer timed out", execution=execution)
    except (OSError, ValueError):
        return _error(name, "internal preview installer could not start")
    except Exception:
        return _error(name, "internal preview installer returned malformed output")

    returncode = getattr(completed, "returncode", None)
    execution = _execution(
        returncode,
        getattr(completed, "stdout", None),
        getattr(completed, "stderr", None),
        timed_out=False,
    )
    if type(returncode) is not int:
        return _error(name, "internal preview installer returned malformed output", execution=execution)
    if returncode != 0:
        return _error(name, "internal preview installer failed", execution=execution)
    try:
        actual_hash = _destination_hash(destination, project, name)
    except InstallerError:
        return _error(name, "internal preview installation postcondition failed", execution=execution)
    if actual_hash != expected_hash:
        return _error(name, "internal preview installation content did not match authoring", execution=execution)
    return 0, {
        **_base(name),
        "status": "installed",
        "provenance": "authoring-exact",
        "skillsLockPresent": (project / "skills-lock.json").is_file(),
        "execution": execution,
    }
