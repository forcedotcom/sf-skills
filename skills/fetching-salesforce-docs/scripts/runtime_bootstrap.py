from __future__ import annotations

import os
import sys
from pathlib import Path


def sf_docs_runtime_root() -> Path:
    return Path.home() / ".claude" / ".fetching-salesforce-docs-runtime"


def sf_docs_runtime_python() -> Path:
    root = sf_docs_runtime_root() / "venv"
    candidates = [
        root / "bin" / "python",
        root / "bin" / "python3",
        root / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if os.name != "nt" else candidates[-1]


def prepare_sf_docs_runtime_env(env: dict[str, str] | None = None) -> dict[str, str]:
    runtime_root = sf_docs_runtime_root()
    target = dict(env or os.environ)
    target.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(runtime_root / "ms-playwright"))
    target.setdefault("SF_DOCS_RUNTIME_ROOT", str(runtime_root))
    return target


def maybe_reexec_in_sf_docs_runtime(script_path: str) -> bool:
    runtime_python = sf_docs_runtime_python()
    os.environ.update(prepare_sf_docs_runtime_env())

    if os.environ.get("SF_DOCS_RUNTIME_ACTIVE") == "1":
        return False
    if not runtime_python.exists():
        return False

    try:
        current_python = Path(sys.executable).resolve()
        target_python = runtime_python.resolve()
        if current_python == target_python:
            os.environ["SF_DOCS_RUNTIME_ACTIVE"] = "1"
            return False
    except OSError:
        pass

    env = prepare_sf_docs_runtime_env()
    env["SF_DOCS_RUNTIME_ACTIVE"] = "1"
    os.execve(
        str(runtime_python),
        [str(runtime_python), str(Path(script_path).resolve()), *sys.argv[1:]],
        env,
    )
    return True
