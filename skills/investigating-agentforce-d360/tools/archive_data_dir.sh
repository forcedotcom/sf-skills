#!/usr/bin/env bash
#
# Stop-hook helper — archive the most-recently-modified session dir under
# ~/.claude/data/investigating-agentforce-d360/ into a tarball for
# compliance / retro purposes.
#
# This is a USER-LEVEL hook (in ~/.claude/settings.json), opt-in.
# Archiving sessions is a per-team preference; users who want it wire it
# up, users who don't, don't.
#
# Behavior:
#   - Find the most-recently-touched <sid>/ directory under DATA_ROOT
#   - Tar + gzip it into ~/.claude/data/investigating-agentforce-d360-archive/
#     with filename <sid>-<YYYY-MM-DD-HHMMSS>.tar.gz
#   - Silent no-op if no session dir exists, or the latest is already
#     archived (same mtime as the most-recent archive)
#   - Never deletes the source; archiving only
#
# Exit codes: always 0 — Stop hooks block session exit only if non-zero.
#
set -eu

DATA_ROOT="$HOME/.claude/data/investigating-agentforce-d360"
ARCHIVE_ROOT="$HOME/.claude/data/investigating-agentforce-d360-archive"

[ -d "$DATA_ROOT" ] || exit 0

# Find the most-recently-modified session dir.
#
# Layout (per scripts/_shared/paths.py):
#     DATA_ROOT/<org_id_15>/<agent_api_name>__<agent_version>/<session_id>/
# That's three levels deep — using `find -mindepth 3 -maxdepth 3` is the
# portable way to address the right level without globbing the org-id or
# agent levels (which would archive an entire org's worth of sessions
# under a filename pretending to be one session id).
#
# `find -printf` is GNU-only, so we sort by mtime via `stat` for portability.
# `find ... -depth 3 -type d` lists the right level on both macOS (BSD find)
# and Linux (GNU find).
LATEST=""
LATEST_MTIME=0
while IFS= read -r d; do
    [ -d "$d" ] || continue
    mt=$(stat -f %m "$d" 2>/dev/null || stat -c %Y "$d" 2>/dev/null || echo 0)
    if [ "$mt" -gt "$LATEST_MTIME" ]; then
        LATEST_MTIME=$mt
        LATEST="$d"
    fi
done < <(find "$DATA_ROOT" -mindepth 3 -maxdepth 3 -type d 2>/dev/null)

[ -n "$LATEST" ] || exit 0
[ -d "$LATEST" ] || exit 0

SID=$(basename "$LATEST")
TS=$(date +"%Y-%m-%d-%H%M%S")
mkdir -p "$ARCHIVE_ROOT"
TARBALL="$ARCHIVE_ROOT/${SID}-${TS}.tar.gz"

# Skip if an archive for this sid created within the last minute already
# exists — avoids redundant tarring on rapid session starts/stops.
#
# `-mmin -1` is the portable "modified within the last 1 minute" form on
# both BSD find (macOS) and GNU find (Linux). Earlier `-mtime -1m` was a
# silent foot-gun: BSD interpreted `m` as MONTHS (matched ~30 days), and
# GNU rejected the unit suffix entirely.
RECENT=$(find "$ARCHIVE_ROOT" -name "${SID}-*.tar.gz" -mmin -1 2>/dev/null | head -1)
[ -n "$RECENT" ] && exit 0

# Tar the session dir relative to its parent (the agent dir) so the archive
# unpacks as just `<session_id>/` without the org/agent path prefix. `--`
# guards against any future SID that ever started with `-`. On failure,
# remove the partial tarball so the next hook invocation retries cleanly
# instead of treating a corrupt 0-byte file as a recent dedup hit.
PARENT=$(dirname "$LATEST")
if ! tar --no-absolute-names -C "$PARENT" -czf "$TARBALL" -- "$SID" 2>/dev/null; then
    rm -f "$TARBALL" 2>/dev/null
fi
exit 0
