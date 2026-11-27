#!/usr/bin/env python3
"""
semver.py — One version-comparison implementation for the whole toolchain.

Why this exists: target_options.py and resolve_versions.py each grew their own
`parse_ver` that (a) truncated to three components and (b) threw away any
pre-release / qualifier tag. Both bugs collapse distinct versions into one: with
the old code `11.0.0` and `11.0.0-rc1` parse to the SAME tuple `(11, 0, 0)` and
compare equal, so the downgrade guard reads a real backward step ("you asked for
the rc, you're on the final") as "already current" and a coherence check passes
a version that was never released. Version math is load-bearing for this skill's
honesty guarantees, so it lives in ONE place and follows SemVer precedence.

Precedence rules implemented (SemVer §11, the parts that bite SFMC versions):
  • Release identifiers compare numerically, field by field. Missing trailing
    fields are treated as 0, so `11.0` == `11.0.0` (a length difference alone is
    not a difference in precedence).
  • A version WITH a pre-release tag has LOWER precedence than the same release
    WITHOUT one: `11.0.0-rc1` < `11.0.0`. They are never equal.
  • Pre-release identifiers compare field by field: numeric identifiers compare
    numerically and rank below alphanumeric ones; a smaller set of fields ranks
    below a larger set when all preceding fields are equal (`rc` < `rc.1`).
  • Build metadata (`+...`) is ignored for precedence, per spec.

Two things kept for compatibility with the callers' old expectations:
  • `release_tuple(v)` returns the 3-component tuple the old `parse_ver` did, for
    the places that only ever wanted "major.minor.patch" for display/grouping.
    It does NOT decide precedence — use compare()/the Version type for that.
  • Non-numeric junk in a release field degrades to 0 rather than raising, so a
    malformed catalog entry can't crash a migration mid-flight.
"""
import functools
import re

_PRERELEASE_SPLIT = re.compile(r"[.]")


def _to_int_or_str(token):
    """Numeric pre-release identifiers compare as ints; everything else as str."""
    return int(token) if token.isdigit() else token


@functools.total_ordering
class Version:
    """A parsed, comparable version. Immutable enough for use as a sort key.

    `release` is the full tuple of numeric components (NOT truncated to 3).
    `prerelease` is a tuple of identifiers (ints for numeric ones, strs
    otherwise); an EMPTY tuple means this is a final release, which ranks ABOVE
    any pre-release of the same numbers.
    """

    __slots__ = ("raw", "release", "prerelease", "build")

    def __init__(self, raw):
        self.raw = str(raw).strip()
        self.release, self.prerelease, self.build = _parse(self.raw)

    def is_prerelease(self):
        return bool(self.prerelease)

    def _cmp_key(self, other):
        """Return (self_key, other_key) padded to equal release length."""
        n = max(len(self.release), len(other.release))
        a_rel = self.release + (0,) * (n - len(self.release))
        b_rel = other.release + (0,) * (n - len(other.release))
        return a_rel, b_rel

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        a_rel, b_rel = self._cmp_key(other)
        # Build metadata is ignored for precedence (SemVer §10).
        return a_rel == b_rel and self.prerelease == other.prerelease

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        a_rel, b_rel = self._cmp_key(other)
        if a_rel != b_rel:
            return a_rel < b_rel
        # Same release numbers: a pre-release ranks below a final release.
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        # Both pre-releases (or both final): compare identifier by identifier.
        return _cmp_prerelease(self.prerelease, other.prerelease) < 0

    def __hash__(self):
        return hash((self.release, self.prerelease))

    def __repr__(self):
        return f"Version({self.raw!r})"


def _parse(raw):
    """'11.0.0-rc.1+build.5' -> ((11,0,0), ('rc',1), 'build.5'). Tolerant."""
    s = raw.lstrip("vV").strip()

    build = ""
    if "+" in s:
        s, build = s.split("+", 1)

    prerelease = ()
    if "-" in s:
        # First hyphen separates release from pre-release. SFMC uses forms like
        # 11.0.0-rc1, 11.0.0-beta, 3.1.1-SNAPSHOT.
        core, pre = s.split("-", 1)
        prerelease = tuple(_to_int_or_str(tok) for tok in _PRERELEASE_SPLIT.split(pre) if tok)
    else:
        core = s

    release = []
    for part in core.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        release.append(int(digits) if digits else 0)
    # Never return an empty release; a bare or unparseable string is (0,).
    return tuple(release) or (0,), prerelease, build


def _cmp_prerelease(a, b):
    """SemVer §11.4 pre-release comparison. Returns -1 / 0 / 1."""
    for x, y in zip(a, b):
        xi, yi = isinstance(x, int), isinstance(y, int)
        if xi and yi:
            if x != y:
                return -1 if x < y else 1
        elif xi != yi:
            # Numeric identifiers always have lower precedence than alphanumeric.
            return -1 if xi else 1
        else:  # both strings
            if x != y:
                return -1 if x < y else 1
    # All shared fields equal: the one with MORE fields has higher precedence.
    if len(a) != len(b):
        return -1 if len(a) < len(b) else 1
    return 0


def parse(v):
    """Public constructor. `parse('11.0.0') -> Version`."""
    return Version(v)


def compare(a, b):
    """-1 if a<b, 0 if equal precedence, 1 if a>b. Accepts strings or Versions."""
    va = a if isinstance(a, Version) else Version(a)
    vb = b if isinstance(b, Version) else Version(b)
    if va < vb:
        return -1
    if vb < va:
        return 1
    return 0


def key(v):
    """Sort key: `sorted(versions, key=semver.key)` orders by precedence."""
    return v if isinstance(v, Version) else Version(v)


def release_tuple(v):
    """Legacy 3-component (major, minor, patch) tuple, for display/grouping only.

    This is the shape the old `parse_ver` returned. It deliberately drops the
    pre-release tag and pads/truncates to 3, so DO NOT use it for precedence
    (that's what Version / compare() are for) — only for "which major.minor line
    is this in" grouping where the tag genuinely doesn't matter.
    """
    ver = v if isinstance(v, Version) else Version(v)
    rel = ver.release + (0, 0, 0)
    return rel[:3]
