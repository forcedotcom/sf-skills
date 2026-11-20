#!/usr/bin/env python3
"""Launch a bundled MCP server in one bounded project and explicit org."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SERVERS = {
    "salesforce-metadata-experts": ("scripts/sf-mcp-proxy.bundled.js", "metadata-experts"),
    "salesforce-metadata-grounding": ("scripts/sf-mcp-proxy.bundled.js", "metadata-grounding"),
    "salesforce-headless-360": (
        "scripts/sf-headless-360-optin.js",
        "scripts/sf-mcp-proxy.bundled.js",
        "headless-360",
    ),
    "salesforce-lsp": ("bin/sf-lsp-host.bundled.js",),
}


def _headless_360_enabled(environment: dict[str, str]) -> bool:
    """Explicit environment overrides the saved user opt-in; otherwise default off."""
    if "SF_HEADLESS_360_ENABLED" in environment:
        return environment["SF_HEADLESS_360_ENABLED"].strip().lower() in {
            "1", "true", "enabled", "on",
        }
    return _saved_headless_360_enabled()


def _headless_360_config_path() -> Path:
    return Path.home() / ".sf/salesforce-development/headless-360.json"


def _saved_headless_360_config() -> dict:
    try:
        with _headless_360_config_path().open(encoding="utf-8") as stream:
            text = stream.read(8193)
        if len(text) > 8192:
            return {}
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, ValueError, RecursionError):
        return {}


def _saved_headless_360_enabled() -> bool:
    return _saved_headless_360_config().get("enabled") is True


def _plugin_root_file_path() -> Path:
    return Path.home() / ".sf/salesforce-development/codex-plugin-root.json"


def _load_sibling(filename):
    """Load a bundled Python module by path, including under python -I."""
    import runpy
    import types
    path = Path(__file__).resolve().with_name(filename)
    try:
        return types.SimpleNamespace(**runpy.run_path(str(path)))
    except (OSError, ImportError, SyntaxError, RecursionError):
        return None


def resolve_installed_root() -> Path | None:
    """The package the Codex MCP bootstrap would run for this user right now."""
    bootstrap = _load_sibling("codex_mcp_bootstrap.py")
    if bootstrap is None:
        return None
    recorded = bootstrap.read_json_object(_plugin_root_file_path()).get("plugin_root")
    return bootstrap.resolve_plugin_root(
        bootstrap.find_codex_home(dict(os.environ), Path.home()), recorded)


def _headless_360_launcher_registered() -> bool:
    """A selected installation is sufficient; the invoking package may be older."""
    return resolve_installed_root() is not None


def _write_json_atomically(path: Path, payload: dict) -> None:
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream)
            stream.write("\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def record_plugin_root(package: Path | None = None) -> bool:
    """Record this install for the bootstrap. Never raises; skips an unchanged file."""
    try:
        package = (package or Path(__file__).resolve().parent.parent).resolve(strict=True)
        version = json.loads((package / ".codex-plugin/plugin.json").read_text(
            encoding="utf-8"))["version"]
        if not isinstance(version, str) or not version:
            return False
        payload = {"plugin_root": str(package), "version": version}
        path = _plugin_root_file_path()
        try:
            if json.loads(path.read_text(encoding="utf-8")) == payload:
                return True
        except (OSError, UnicodeError, ValueError, RecursionError):
            pass
        _write_json_atomically(path, payload)
        return True
    except (OSError, UnicodeError, ValueError, RecursionError, KeyError, TypeError):
        return False


def configure_headless_360(action: str) -> int:
    """Save only the local Codex preference. Never contact or configure an org."""
    if action not in {"enable", "disable", "status"}:
        print("Usage: codex_mcp_launcher.py --headless-360 enable|disable|status", file=sys.stderr)
        return 2
    path = _headless_360_config_path()
    if action != "status":
        try:
            # Keep "plugin_root": the previous release's inline bootstrap in
            # .codex-plugin/plugin.json reads it from this file, so removing it
            # would break rolling back to that release.
            _write_json_atomically(path, {
                "enabled": action == "enable",
                "plugin_root": str(Path(__file__).resolve().parent.parent)})
        except OSError:
            print("codex_mcp_launcher: could not save the local H360 setting", file=sys.stderr)
            return 2
        record_plugin_root()
    print(json.dumps({"enabled": _headless_360_enabled(dict(os.environ)),
                      "saved_enabled": _saved_headless_360_enabled(),
                      "launcher_registered": _headless_360_launcher_registered(),
                      "environment_override": "SF_HEADLESS_360_ENABLED" in os.environ,
                      "restart_required": action != "status"}))
    return 0


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _nvm_bin(environment: dict[str, str], home: Path) -> Path | None:
    """nvm has no stable shim directory: use NVM_BIN, else the highest installed version."""
    raw = environment.get("NVM_BIN")
    if raw and os.path.isabs(raw) and _is_executable_file(Path(raw) / "node"):
        return Path(raw)
    versions = home / ".nvm/versions/node"
    try:
        entries = [entry for entry in versions.iterdir() if _is_executable_file(entry / "bin" / "node")]
    except OSError:
        return None

    def order(entry: Path) -> tuple:
        parts = re.findall(r"\d+", entry.name)
        return (tuple(int(part) for part in parts), entry.name)

    return max(entries, key=order) / "bin" if entries else None


IS_WINDOWS = os.name == "nt"
SYSTEM_NODE_DIRS = (Path("/opt/homebrew/bin"), Path("/usr/local/bin"))


def _find_node(directories: list[Path]) -> str | None:
    # A qualified executable also avoids an implicit cwd search on Windows.
    filename = "node.exe" if IS_WINDOWS else "node"
    for directory in directories:
        node = shutil.which(str(directory / filename))
        if node:
            return node
    return None


def resolve_node(environment: dict[str, str]) -> str | None:
    """Use absolute PATH entries first, then user installs, nvm and system dirs."""
    inherited = environment.get("PATH", os.defpath).split(os.pathsep)
    directories = [Path(entry) for entry in inherited if Path(entry).is_absolute()]
    environment["PATH"] = os.pathsep.join(map(str, directories))
    node = _find_node(directories)
    if node:
        return node
    if IS_WINDOWS:
        fallback = []
        for key, suffix in (("NVM_SYMLINK", ()), ("LOCALAPPDATA", ("Volta", "bin")),
                            ("PROGRAMFILES", ("nodejs",))):
            base = Path(environment.get(key, ""))
            if base.is_absolute():
                fallback.append(base.joinpath(*suffix))
    else:
        home = Path.home()
        fallback = [home / ".local/bin", home / ".volta/bin", home / ".asdf/shims",
                    home / ".local/share/mise/shims"]
        nvm = _nvm_bin(environment, home)
        if nvm is not None:
            fallback.append(nvm)
        fallback.extend(SYSTEM_NODE_DIRS)
    extra = [path for path in fallback if path.is_absolute() and path.is_dir()]
    node = _find_node(extra)
    if node:
        # The proxy launches CLI children using the same sanitized search path.
        environment["PATH"] = os.pathsep.join(map(str, directories + extra))
    return node


def _resolved_dir(raw: str | None) -> Path | None:
    if not raw:
        return None
    try:
        candidate = Path(raw).resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    return candidate if candidate.is_dir() else None


def _find_ancestor_project(start: Path, *, plugin_root: Path,
                           boundary: Path | None = None) -> Path | None:
    for directory in (start, *start.parents):
        if boundary is not None and directory != boundary and boundary not in directory.parents:
            break
        if directory == plugin_root or plugin_root in directory.parents:
            break
        if (directory / "sfdx-project.json").is_file():
            return directory
    return None


def _find_nested_project(root: Path, *, plugin_root: Path, max_depth: int = 3) -> Path | None:
    """Accept one project only after a complete, bounded scan proves uniqueness."""
    frontier = [root]
    found = None
    scanned = 0
    for _ in range(max_depth + 1):
        next_frontier: list[Path] = []
        for directory in frontier:
            if directory == plugin_root or plugin_root in directory.parents:
                continue
            if (directory / "sfdx-project.json").is_file():
                if found is not None:
                    return None
                found = directory
                continue
            try:
                for entry in directory.iterdir():
                    scanned += 1
                    if scanned > 4096:
                        return None
                    if entry.is_dir() and not entry.is_symlink():
                        # Older Python versions classify NTFS junctions as directories.
                        # Our root is canonical, so a redirected child resolves elsewhere.
                        if IS_WINDOWS and entry.resolve(strict=True) != entry:
                            continue
                        next_frontier.append(entry)
            except (OSError, RuntimeError):
                return None
        frontier = next_frontier
        if not frontier:
            break
    return found


def resolve_project_cwd(*, plugin_root: Path, environment: dict[str, str],
                        process_cwd: Path | None = None) -> Path | None:
    """Resolve one nearest project without escaping the Codex workspace boundary."""
    plugin_root = plugin_root.resolve()
    if "CODEX_WORKSPACE_ROOT" in environment:
        workspace_root = _resolved_dir(environment.get("CODEX_WORKSPACE_ROOT"))
        if workspace_root is None:
            return None
        for raw in (str(process_cwd) if process_cwd else None,
                    environment.get("PWD"), environment.get("INIT_CWD")):
            candidate = _resolved_dir(raw)
            if candidate is None:
                continue
            found = _find_ancestor_project(candidate, plugin_root=plugin_root,
                                           boundary=workspace_root)
            if found is not None:
                return found
        return (
            _find_ancestor_project(workspace_root, plugin_root=plugin_root,
                                   boundary=workspace_root)
            or _find_nested_project(workspace_root, plugin_root=plugin_root)
        )
    if process_cwd is not None:
        candidate = process_cwd.resolve()
        if candidate != plugin_root and plugin_root not in candidate.parents:
            # Native Codex inherits the selected thread cwd. A Dock-launched app's
            # PWD/INIT_CWD can be stale, so never use those to escape this context.
            return _find_ancestor_project(candidate, plugin_root=plugin_root)
    for key in ("INIT_CWD", "PWD"):
        candidate = _resolved_dir(environment.get(key))
        if candidate is None:
            continue
        found = _find_ancestor_project(candidate, plugin_root=plugin_root)
        if found is not None:
            return found
    return None


# Project-local CLI config files and the keys that name the default org, most
# authoritative first: the current CLI's `.sf/config.json` wins over the legacy file.
_PROJECT_ORG_CONFIG = (
    (".sf/config.json", "target-org"),
    (".sfdx/sfdx-config.json", "defaultusername"),
)


def _project_target_org(project: Path | None) -> str | None:
    if project is None:
        return None
    for relative, key in _PROJECT_ORG_CONFIG:
        value = _project_target_org_file(project / relative, key)
        if value is not None:
            return value
    return None


def resolve_target_org(environment: dict[str, str], project: Path | None = None) -> str | None:
    """Return exactly one org: the explicit environment value, else the project's.

    Explicit SF_TARGET_ORG/SFDX_TARGET_ORG values must agree. Without either, the
    selected project's own CLI config is used: `.sf/config.json` takes precedence over
    the legacy `.sfdx/sfdx-config.json` when both name an org. Global (home-directory)
    defaults are never consulted.
    """
    values = {
        value.strip()
        for key in ("SF_TARGET_ORG", "SFDX_TARGET_ORG")
        if (value := environment.get(key)) and value.strip()
    }
    if values:
        return next(iter(values)) if len(values) == 1 else None
    return _project_target_org(project)


def _prepare_launch(server_name: str, environment: dict[str, str], plugin_root: Path,
                    *, dry_run: bool = False) -> dict:
    """One preparation path for launch and offline checks; only the caller executes it."""
    result = {"status": "ready", "reason": "ready", "guidance":
              "Local prerequisites ready; confirm process startup and tools in the host MCP UI."}
    def fail(reason, guidance):
        result.update(status="error", reason=reason, guidance=guidance)
        return result

    if server_name not in SERVERS:
        return fail("unknown_server", "Select one of the four bundled Salesforce MCP servers.")
    enabled = server_name != "salesforce-headless-360" or _headless_360_enabled(environment)
    if not enabled and dry_run:
        result.update(status="off", reason="disabled", guidance="Off; no tools exposed.")
        return result
    if server_name == "salesforce-headless-360":
        environment["SF_HEADLESS_360_ENABLED"] = "enabled" if enabled else "disabled"
    if enabled:
        try:
            cwd = Path.cwd()
        except OSError:
            return fail("cwd_unavailable", "The working directory is unavailable. Reopen the Salesforce DX project.")
        project = resolve_project_cwd(plugin_root=plugin_root, environment=environment, process_cwd=cwd)
        if project is None:
            return fail("project_missing", "no Salesforce project in the bounded workspace. Select the Salesforce DX project folder for this Codex session.")
        result["project"] = project
        values = {environment[key].strip() for key in ("SF_TARGET_ORG", "SFDX_TARGET_ORG")
                  if environment.get(key, "").strip()}
        if len(values) > 1:
            result["org_source"] = "SF_TARGET_ORG+SFDX_TARGET_ORG"
            return fail("org_conflict", "Align or remove conflicting SF_TARGET_ORG and SFDX_TARGET_ORG in the environment starting Codex; local target-org cannot override this conflict.")
        target_org = resolve_target_org(environment, project)
        if target_org is None:
            return fail("org_missing", "no single target org: none configured. Run `sf config set target-org <alias>` locally in the project, or set SF_TARGET_ORG in the environment starting Codex.")
        if values:
            result["org_source"] = "+".join(key for key in ("SF_TARGET_ORG", "SFDX_TARGET_ORG")
                                            if environment.get(key, "").strip())
        else:
            result["org_source"] = next((relative for relative, key in _PROJECT_ORG_CONFIG
                if _project_target_org_file(project / relative, key) is not None), "project_config_changed")
        environment.update(CODEX_WORKSPACE_ROOT=str(project), SF_TARGET_ORG=target_org,
                           SFDX_TARGET_ORG=target_org)
    server = SERVERS[server_name]
    assets = server[:2] if server_name == "salesforce-headless-360" else server[:1]
    for asset in assets:
        try:
            executable = (plugin_root / asset).resolve()
            available = executable.is_file() and plugin_root in executable.parents
        except (OSError, RuntimeError):
            available = False
        if not available:
            result["missing_asset"] = asset
            return fail("asset_missing", "Bundled server asset missing; reinstall the plugin if a new session does not restore it.")
    launch_args = [str((plugin_root / server[0]).resolve()), *server[1:]]
    if server_name == "salesforce-headless-360":
        launch_args[1] = str((plugin_root / server[1]).resolve())
    node = resolve_node(environment)
    if node is None:
        return fail("node_missing", "Node.js not found. Install Node.js on PATH or in a supported user/system bin directory; see the plugin README.")
    result.update(node=node, launch_args=launch_args)
    return result


def _project_target_org_file(path: Path, key: str) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError):
        return None
    value = data.get(key) if isinstance(data, dict) else None
    return value.strip() if isinstance(value, str) and value.strip() else None


def launch_preflight(server_name: str, *, diagnostic_module) -> dict:
    """Check this selected package without exec, chdir, environment or config writes."""
    root = Path(__file__).resolve().parent.parent
    prepared = _prepare_launch(server_name, dict(os.environ), root, dry_run=True)
    result = diagnostic_module.diagnostic(server_name, prepared["reason"], prepared["guidance"],
                                  status=prepared["status"], selected_root=root)
    for key in ("project", "org_source", "node", "missing_asset"):
        if key in prepared:
            result[key] = diagnostic_module.diagnostic_text(prepared[key])
    return result


def native_preflight(server_name: str) -> dict:
    """Diagnose the installation the native entry selects, not necessarily this package."""
    bootstrap = _load_sibling("codex_mcp_bootstrap.py")
    diagnostics = _load_sibling("codex_mcp_diagnostics.py")
    if bootstrap is None or diagnostics is None:
        return {"schema_version": 1, "server": server_name[:128], "status": "error",
                "reason": "diagnostics_unavailable", "guidance":
                "Bundled launch diagnostics unavailable. Start a new session; reinstall if this persists."}
    return diagnostics.preflight(server_name, Path(__file__).resolve().parent.parent, bootstrap)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) == 2 and args[0] == "--headless-360":
        return configure_headless_360(args[1])
    if len(args) == 2 and args[1] == "--dry-run":
        result = native_preflight(args[0])
        print(json.dumps(result))
        return 2 if result["status"] == "error" else 0
    if len(args) != 1 or args[0] not in SERVERS:
        print("codex_mcp_launcher: unknown server", file=sys.stderr)
        return 2
    plugin_root = Path(__file__).resolve().parent.parent
    environment = dict(os.environ)
    server_name = args[0]
    prepared = _prepare_launch(server_name, environment, plugin_root)
    if prepared["status"] == "error":
        print("codex_mcp_launcher: " + prepared["guidance"], file=sys.stderr)
        return 2
    for key in ("SF_HEADLESS_360_ENABLED", "CODEX_WORKSPACE_ROOT", "SF_TARGET_ORG", "SFDX_TARGET_ORG", "PATH"):
        if key in environment:
            os.environ[key] = environment[key]
    if "project" in prepared:
        os.chdir(prepared["project"])
    node, launch_args = prepared["node"], prepared["launch_args"]
    try:
        if IS_WINDOWS:
            # Keep the stdio server attached and let subprocess quote argv for CreateProcess.
            return subprocess.run([node, *launch_args], check=False).returncode
        os.execvp(node, [node, *launch_args])
        return 0
    except OSError as exc:
        print(f"codex_mcp_launcher: unable to start node: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
