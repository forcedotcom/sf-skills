# Script regression tests

Dependency-free (`unittest` only) and **network-free** — safe to run anywhere,
including CI without internet. They cover the bundled scanner, version resolver, semantic-version helpers,
worker observer, and shipped-artifact verifier:

| Test file | Guards |
|---|---|
| `test_semver.py` | SemVer §11 precedence — `11.0.0` ≠ `11.0.0-rc1`, no 3-component truncation, build metadata ignored. The lossy `parse_ver` bug. |
| `test_scan_usage.py` | Era keyed off the unified-core artifact, **not** off findings (a migrated v11 project produces findings but is `unified`/`already-modern`); version read from the umbrella artifact, resolved deterministically. iOS: era keyed off `SFMCSDK` (unified core) with `MarketingCloudSDK` kept as the engagement module; case-insensitive matching across Podfile CamelCase and Package.resolved lowercased identity; `-ios-sdk` repo-slug suffix accepted. |
| `test_resolve_versions.py` | HTTP 404/403 reports `networkReachable=true` (not "offline"); connection failure reports `false`; SSRF host allowlist rejects off-list hosts, look-alike suffixes, and non-http schemes. iOS: CocoaPods trunk JSON parsing (empty/malformed entries); Podfile / Package.swift scraping; SPM git-scheme gate rejects `file://` / `gopher://` before touching a subprocess. |
| `test_verify_known_issue.py` | iOS shipped Swift-interface defect detection, patched artifacts, missing artifacts, and declaration matching. |
| `test_observe_workers.py` | Stall detection works without `--now`; `done` needs evidence; `blocked` needs a flagged reason; `demoted` is terminal. |

## Run

```bash
# from the repo root
python3 -m unittest discover -s skills/sfmc-sdk-migrator/scripts/tests -p 'test_*.py' -v
```

`test_scan_usage.py` shells out to `scan_usage.py` as a subprocess (it exercises
the full CLI path), so run with the repo intact. The others import the modules
directly via `_bootstrap.py`, which puts `scripts/` on `sys.path`.
