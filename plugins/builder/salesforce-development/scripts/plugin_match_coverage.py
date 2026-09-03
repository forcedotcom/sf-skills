#!/usr/bin/env python3
"""Report plugin-matching test coverage for the discovery catalog.

Every plugin in ``catalog/plugins.json`` opts in to discovery by declaring
``keywords`` + ``metadata.match.examplePrompts`` (see ``plugin_catalog.py``).
Those example prompts are the plugin owner's own statement of "a user who wants
me would say this." This module turns that statement into a *measured* coverage
signal: for every candidate plugin, does each of its own example prompts
actually route back to it through the real scorer?

It exists so that:

  * a contributor adding a plugin can run one command and see whether their
    example prompts match their plugin -- ``--report`` (human table) or
    ``--json`` (machine-readable);
  * CI can fail closed via ``--check`` (exit 1 on any regression) when: a plugin's
    own prompts stop routing to it, or the foundation plugin goes missing from the
    catalog (its exclusion becoming a rename/typo no-op). It is wired two ways: the
    sibling ``test/test_plugin_match_coverage.py`` unittest runs under
    ``npm run test:gates``, and ``--check`` itself runs as a named CI step, so the
    exact command the contributor docs point at is the command CI enforces. The
    two are kept in lockstep on catalog state (see
    ``foundation_missing_from_catalog``); one runtime-name anti-drift guard is
    deliberately gates-only (documented in ``main``);
  * nobody can *silently* add a plugin with no working matching: the check
    iterates the catalog itself, so a new entry is covered the moment it ships
    (a new plugin with prompts that don't route to it turns the build red).

Coverage is the positive (examplePrompts) direction, hard-gated: each of a
plugin's own example prompts MUST route back to it at ``high`` on the discovery
path (``require_anchor_terms=False``). Discovery is the LESS strict of the two
runtime paths: the anchor-gated proactive path (below) is a subset of it -- it
additionally drops any prompt that names no anchor term -- so clearing discovery
does NOT imply clearing proactive. That difference is exactly what the advisory
``proactive_gaps`` signal reports; it is never folded into the gate.

This is a regression + prompt-distinctiveness gate, not an independent
reachability proof. A plugin's example prompts are folded into its own scored
document, so a prompt shares tokens with its plugin by construction -- the gate
cannot prove a plugin is reachable from vocabulary it did not itself supply.
What it does catch: a prompt too generic to out-score the corpus (its
own terms stoplisted or shared too widely to reach ``high``), a scorer/threshold
regression that stops routing a once-covered prompt, and -- because it iterates
the catalog -- any newly added plugin whose prompts don't route to it.

Two scorer paths are measured, because the runtime uses both
(``_plugin_catalog_match`` in ``sf_context.py``):

  discovery  -- ``require_anchor_terms=False``: the explicit "/plugin-match"
                and reactive bypass-gate surfaces, where the user's own act of
                asking is the evidence. This is the HARD gate: every candidate
                plugin's every example prompt must reach that plugin at the
                ``high`` band here.
  proactive  -- ``require_anchor_terms=True``: the SessionStart /
                UserPromptSubmit surfaces, which additionally require one of the
                plugin's ``anchorTerms`` in the prompt so a generic word can
                never interrupt unprompted. This is a SOFT signal: a prompt that
                clears discovery but not proactive is reported as a proactive
                gap (usually an example prompt that names no anchor term), not a
                build failure -- anchor gating is a deliberate proactive-only
                tradeoff, but owners should see which of their prompts it drops.

The foundation plugin (``salesforce-development``) is excluded from the corpus
and from coverage: the runtime never recommends the plugin that is already
running it, so its example prompts are not a recommendation surface.

A third signal is reported but never gated: **match-text vs. shipped-skills
drift**. The scorer matches only curated marketplace text, never the skills a
plugin ships, so that text can silently fall out of sync (add a capability
skill, forget to advertise it). ``compute_drift`` flags, for every LOCAL plugin,
any shipped skill NONE of whose own tokens appear in the matcher text -- a skill
sharing no token with the match text is one the scorer can never route a user to
-- using the matcher's own tokenizer, so it can never disagree with real scoring.
It is advisory only: surfaced in ``--report``/``--json`` but never folded into
``is_clean`` or the ``--check`` exit code, and skipped quietly when run from a
packaged copy without the repo checkout.

``compute_coverage`` is pure over its inputs; the only I/O is loading the
catalog in ``main`` and reading SKILL.md frontmatter in ``compute_drift``.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple, Optional

try:
    import plugin_catalog as catalog_mod
except ImportError:
    _module_path = Path(__file__).resolve().parent / "plugin_catalog.py"
    _spec = importlib.util.spec_from_file_location("plugin_match_coverage_catalog", _module_path)
    if _spec is None or _spec.loader is None:
        raise
    catalog_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(catalog_mod)

# The plugin that is already running when discovery fires; never a candidate for
# recommending itself. Kept in sync with `_plugin_display_name()`'s value in
# sf_context.py by the anti-drift assertion in test_plugin_match_coverage.py.
FOUNDATION_PLUGIN = "salesforce-development"


class PromptCoverage(NamedTuple):
    """One example prompt's routing result on both scorer paths."""
    prompt: str
    discovery_own_high: bool          # own plugin reached `high` (anchor-ungated path)
    discovery_other_highs: tuple      # names of OTHER plugins also at `high` (recall context)
    proactive_own_high: bool          # own plugin reached `high` (anchor-gated path)
    proactive_present: bool           # own plugin appeared at all on the anchor-gated path


class PluginCoverage(NamedTuple):
    name: str
    anchor_terms: tuple
    prompts: tuple            # of PromptCoverage

    @property
    def discovery_covered(self) -> bool:
        """The hard invariant for this plugin: every own prompt routes to it at
        high on the discovery path."""
        return (
            len(self.prompts) > 0
            and all(p.discovery_own_high for p in self.prompts)
        )

    @property
    def discovery_failures(self) -> list:
        return [p for p in self.prompts if not p.discovery_own_high]

    @property
    def proactive_gaps(self) -> list:
        """Prompts that clear discovery but the anchor-gated proactive path drops
        (usually: the prompt names no anchor term). Soft signal, not a failure."""
        return [p for p in self.prompts if not p.proactive_own_high]


class CoverageReport(NamedTuple):
    plugins: tuple  # of PluginCoverage, sorted by name (candidates only)
    foundation: str
    foundation_present: bool  # was the foundation actually IN the scored catalog?

    @property
    def total_prompts(self) -> int:
        return sum(len(pc.prompts) for pc in self.plugins)

    @property
    def discovery_covered_plugins(self) -> list:
        return [pc for pc in self.plugins if pc.discovery_covered]

    @property
    def discovery_failing_plugins(self) -> list:
        return [pc for pc in self.plugins if not pc.discovery_covered]

    @property
    def proactive_gap_plugins(self) -> list:
        return [pc for pc in self.plugins if pc.proactive_gaps]

    @property
    def is_clean(self) -> bool:
        """True when every candidate plugin clears the hard discovery invariant
        (its own example prompts route back to it at high)."""
        return len(self.plugins) > 0 and not self.discovery_failing_plugins

    @property
    def foundation_missing_from_catalog(self) -> bool:
        """True when the named foundation plugin is NOT actually present in the
        scored catalog. The foundation is excluded from the candidate corpus
        precisely because the runtime never recommends the plugin that is already
        running -- but that exclusion is only meaningful if the name really names
        something. If it is absent (a rename, a typo, a dropped entry), the
        exclusion silently becomes a no-op and every coverage check runs against
        a subtly wrong corpus.

        This is deliberately kept OUT of ``is_clean`` (which stays a pure
        per-candidate signal) but gated on by ``--check`` -- mirroring the
        ``test_foundation_is_present_in_catalog``
        unittest guard, so ``--check`` can't be green while ``npm run test:gates``
        is red on a foundation rename that touches only ``catalog/plugins.json``.
        (A rename that touches ``plugin.json``/``sf_context.py`` but leaves the
        catalog intact is a separate, deliberately gates-only check -- see the
        note in ``main``.)"""
        return not self.foundation_present


def compute_coverage(catalog_data: dict, *, foundation: str = FOUNDATION_PLUGIN) -> CoverageReport:
    """Measure, for every candidate plugin, whether its own example prompts route
    back to it through the real scorer. Pure: no I/O, operates on the given
    catalog dict.

    The scoreable corpus is every plugin except ``foundation`` (mirroring the
    runtime's own exclusion of the plugin that is currently running). Each
    prompt is scored against that same corpus on both scorer paths.
    """
    plugins = [p for p in catalog_data.get("plugins", []) if isinstance(p, dict)]
    corpus_plugins = [p for p in plugins if p.get("name") != foundation]
    corpus = {**catalog_data, "plugins": corpus_plugins}
    foundation_present = any(p.get("name") == foundation for p in plugins)

    results = []
    for plugin in sorted(corpus_plugins, key=lambda p: p.get("name") or ""):
        name = plugin.get("name")
        anchor_terms = tuple(plugin.get("match", {}).get("anchorTerms") or ())
        prompt_results = []
        for prompt in plugin.get("match", {}).get("examplePrompts", []):
            discovery = catalog_mod.score_prompt_against_catalog(
                prompt, corpus, require_anchor_terms=False
            )
            proactive = catalog_mod.score_prompt_against_catalog(
                prompt, corpus, require_anchor_terms=True
            )
            d_by = {m.plugin.get("name"): m for m in discovery}
            p_by = {m.plugin.get("name"): m for m in proactive}
            own_d = d_by.get(name)
            own_p = p_by.get(name)
            other_highs = tuple(
                sorted(
                    m.plugin.get("name")
                    for m in discovery
                    if m.band == "high" and m.plugin.get("name") != name
                )
            )
            prompt_results.append(
                PromptCoverage(
                    prompt=prompt,
                    discovery_own_high=(own_d is not None and own_d.band == "high"),
                    discovery_other_highs=other_highs,
                    proactive_own_high=(own_p is not None and own_p.band == "high"),
                    proactive_present=(own_p is not None),
                )
            )
        results.append(PluginCoverage(
            name=name,
            anchor_terms=anchor_terms,
            prompts=tuple(prompt_results),
        ))

    return CoverageReport(
        plugins=tuple(results), foundation=foundation, foundation_present=foundation_present
    )


def report_to_dict(report: CoverageReport, drift: Optional[list] = None) -> dict:
    """Machine-readable coverage snapshot (for --json / dashboards).

    ``drift`` (a list of SkillDrift, from ``compute_drift``) is included as an
    advisory ``drift`` block when supplied; omitted entirely when None (e.g. run
    from a packaged copy with no repo checkout)."""
    snapshot = {
        "foundation": report.foundation,
        "summary": {
            "candidatePlugins": len(report.plugins),
            "discoveryCoveredPlugins": len(report.discovery_covered_plugins),
            "discoveryFailingPlugins": [pc.name for pc in report.discovery_failing_plugins],
            "proactiveGapPlugins": [pc.name for pc in report.proactive_gap_plugins],
            "totalExamplePrompts": report.total_prompts,
            # `clean` is the per-candidate discovery invariant ONLY. The foundation
            # axis is a separate gate (see foundation_missing_from_catalog), so a
            # consumer reading `clean` alone can disagree with `--check`'s exit code.
            # Both axes are surfaced here, plus `checkWouldPass` = the combined
            # verdict `--check` actually exits on, so a dashboard need not re-derive it.
            "clean": report.is_clean,
            "foundationPresent": report.foundation_present,
            "checkWouldPass": report.is_clean and not report.foundation_missing_from_catalog,
        },
        "plugins": [
            {
                "name": pc.name,
                "anchorTerms": list(pc.anchor_terms),
                "examplePrompts": len(pc.prompts),
                "discoveryCovered": pc.discovery_covered,
                "discoveryFailures": [p.prompt for p in pc.discovery_failures],
                "proactiveGaps": [p.prompt for p in pc.proactive_gaps],
            }
            for pc in report.plugins
        ],
    }
    if drift is not None:
        # Advisory only -- never reflected in summary.clean.
        snapshot["drift"] = {
            "driftingPlugins": [d.name for d in drift if d.is_local and d.unrepresented],
            "plugins": [
                {
                    "name": d.name,
                    "isLocal": d.is_local,
                    "skillCount": d.skill_count,
                    "unrepresented": list(d.unrepresented),
                    "note": d.note,
                }
                for d in drift
            ],
        }
    return snapshot


def format_report(report: CoverageReport) -> str:
    """Human-readable coverage table."""
    lines = []
    lines.append("Plugin-matching coverage (per plugin, own example prompts → own plugin)")
    lines.append(f"corpus: every catalog plugin except the foundation ({report.foundation})")
    lines.append("")
    lines.append(f"  {'plugin':30} {'discovery':11} {'proactive':11} anchorTerms")
    lines.append(f"  {'':30} {'(hard gate)':11} {'(anchor)':11}")
    lines.append("  " + "-" * 78)
    for pc in report.plugins:
        n = len(pc.prompts)
        d_ok = sum(1 for p in pc.prompts if p.discovery_own_high)
        p_ok = sum(1 for p in pc.prompts if p.proactive_own_high)
        d_cell = f"{d_ok}/{n}"
        p_cell = f"{p_ok}/{n}"
        flag = "" if pc.discovery_covered else "  ✗ FAIL"
        anchors = ",".join(pc.anchor_terms) if pc.anchor_terms else "(none)"
        lines.append(f"  {pc.name:30} {d_cell:11} {p_cell:11} {anchors}{flag}")
    lines.append("  " + "-" * 78)

    covered = len(report.discovery_covered_plugins)
    total = len(report.plugins)
    lines.append("")
    lines.append(
        f"discovery coverage (HARD gate): {covered}/{total} candidate plugins fully covered, "
        f"{report.total_prompts} example prompts measured"
    )
    # Foundation presence is the OTHER hard axis --check gates on (its absence
    # makes excluding it a no-op). Surface it here so the table matches --json.
    foundation_state = "present" if report.foundation_present else "MISSING"
    lines.append(
        f"foundation ({report.foundation}) in catalog: {foundation_state}"
    )
    verdict = "PASS" if (report.is_clean and not report.foundation_missing_from_catalog) else "FAIL"
    lines.append(f"--check verdict: {verdict}")
    if report.discovery_failing_plugins:
        lines.append("")
        lines.append("✗ DISCOVERY FAILURES (a plugin's own example prompt does not route to it at high):")
        for pc in report.discovery_failing_plugins:
            for p in pc.discovery_failures:
                context = f" (other high: {', '.join(p.discovery_other_highs)})" if p.discovery_other_highs else ""
                lines.append(f"    {pc.name}: {p.prompt!r}{context}")

    if report.proactive_gap_plugins:
        lines.append("")
        lines.append(
            "⚠ proactive gaps (clears discovery, but the anchor-gated SessionStart/UserPromptSubmit"
        )
        lines.append(
            "  path drops it — usually the prompt names no anchorTerm; add an anchor term to the"
        )
        lines.append("  prompt or broaden the plugin's anchorTerms to close it):")
        for pc in report.proactive_gap_plugins:
            for p in pc.proactive_gaps:
                where = "absent" if not p.proactive_present else "medium-only"
                lines.append(f"    {pc.name} [{where}]: {p.prompt!r}  (anchorTerms: {', '.join(pc.anchor_terms) or 'none'})")
    else:
        lines.append("proactive path: every example prompt reaches its plugin on the anchor-gated path too")

    return "\n".join(lines) + "\n"


# ── Match-text vs. shipped-skills drift (advisory) ──────────────────────────
#
# Plugin matching scores ONLY curated marketplace text (description / keywords /
# examplePrompts), never the skills a plugin actually ships. That decoupling is
# deliberate -- a skill edit can never silently change a match score. The cost of
# it is the inverse risk: a plugin's curated match text can drift out of sync with
# the skills it ships (add a capability skill, forget to advertise it; delete a
# skill, keep advertising it). Nothing lexically ties the two, so this section
# flags the drift as a warning. It is deterministic and lexical (reusing the
# matcher's own `_tokenize`/`_plugin_document_tokens`), and it can only inspect
# LOCAL plugins whose skills live in this repo -- external (git-url/object-source)
# plugins are reported as skipped, never silently.
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)
_YAML_SCALAR_RE = re.compile(r"^(name|description)\s*:\s*(.+?)\s*$")
_MAX_SKILL_MD_BYTES = 1024 * 1024


class SkillDrift(NamedTuple):
    name: str
    is_local: bool          # source is a relative path in this repo (vs. an external object)
    skill_count: int
    unrepresented: tuple    # skill dir names sharing no token with the match text
    note: str               # populated for skipped/empty cases, else ""


def _skill_dir_for(source, repo_root: Path) -> Optional[Path]:
    """The on-disk ``skills/`` dir for a LOCAL plugin source, else None. Returns
    None both for an external (object) source and for a local source that ships
    no ``skills/`` dir -- the caller distinguishes the two via ``is_local``."""
    if not (isinstance(source, str) and source):
        return None
    skills_dir = (repo_root / source.lstrip("./")) / "skills"
    return skills_dir if skills_dir.is_dir() else None


def _read_frontmatter_terms(skill_md: Path) -> str:
    """The skill's own capability vocabulary: its ``name`` + ``description``
    frontmatter. Returns a space-joined string (empty if unreadable / no
    frontmatter)."""
    try:
        text = skill_md.read_text(encoding="utf-8")[:_MAX_SKILL_MD_BYTES]
    except (OSError, UnicodeError):
        return ""
    block = _FRONTMATTER_RE.match(text)
    if not block:
        return ""
    values = []
    for line in block.group(1).splitlines():
        found = _YAML_SCALAR_RE.match(line)
        if found:
            values.append(found.group(2).strip().strip('"').strip("'"))
    return " ".join(values)


def _drift_for_plugin(plugin: dict, repo_root: Path) -> SkillDrift:
    """One plugin's drift: for a LOCAL plugin, the shipped skills that share no
    token with any of its matcher text. External sources
    are skipped (their skills are not in this repo); a local plugin that ships no
    ``skills/`` dir is local-but-empty (still not a false external skip)."""
    name = plugin.get("name")
    source = plugin.get("source")
    is_local = isinstance(source, str) and bool(source)
    if not is_local:
        return SkillDrift(name, False, 0, (), "external source -- skills not in this repo, skipped")

    skills_dir = _skill_dir_for(source, repo_root)
    if skills_dir is None:
        return SkillDrift(name, True, 0, (), "local plugin ships no skills/ directory")

    match_vocab = set(catalog_mod._plugin_document_tokens(plugin))

    skill_dirs = sorted(p for p in skills_dir.iterdir() if (p / "SKILL.md").is_file())
    unrepresented = []
    for skill_dir in skill_dirs:
        raw = f"{skill_dir.name.replace('-', ' ')} {_read_frontmatter_terms(skill_dir / 'SKILL.md')}"
        # A skill is represented iff at least one of its own tokens appears in the
        # match text -- that shared token is exactly what lets the scorer route a
        # user to the plugin for that skill. We do NOT subtract the plugin's name
        # tokens: a plugin's name is not reliably present in its match text (7 of
        # the 15 real candidates omit a name token from theirs, e.g.
        # dx-org-lifecycle carries neither "dx" nor "org"), so subtracting them
        # both hid real drift (a skill whose only token is an absent name token
        # looked "covered") and manufactured false drift (a skill reachable via a
        # name token that IS in the match text looked unrepresented).
        skill_vocab = set(catalog_mod._tokenize(raw))
        if skill_vocab and not (skill_vocab & match_vocab):
            unrepresented.append(skill_dir.name)

    note = "" if skill_dirs else "no skills found on disk"
    return SkillDrift(name, True, len(skill_dirs), tuple(unrepresented), note)


def compute_drift(catalog_data: dict, repo_root: Path, *, foundation: str = FOUNDATION_PLUGIN) -> list:
    """Advisory drift over every candidate plugin (foundation excluded, matching
    ``compute_coverage``'s corpus). Pure except for reading SKILL.md files."""
    plugins = [p for p in catalog_data.get("plugins", []) if isinstance(p, dict)]
    corpus_plugins = [p for p in plugins if p.get("name") != foundation]
    return [
        _drift_for_plugin(plugin, repo_root)
        for plugin in sorted(corpus_plugins, key=lambda p: p.get("name") or "")
    ]


def format_drift(rows: list) -> str:
    """Human-readable drift section (advisory)."""
    lines = []
    local = [r for r in rows if r.is_local]
    external = [r for r in rows if not r.is_local]
    drifting = [r for r in local if r.unrepresented]

    lines.append("")
    lines.append(
        f"Match-text vs. shipped-skills drift (advisory): "
        f"{len(local) - len(drifting)}/{len(local)} local plugins aligned"
        + (f", {len(external)} external plugin(s) skipped" if external else "")
    )
    if drifting:
        lines.append("")
        for row in drifting:
            for skill in row.unrepresented:
                lines.append(
                    f"  ⚠ {row.name}: skill {skill!r} ships but shares no token with any "
                    f"matcher text -- the plugin cannot be recommended for it"
                )
    if external:
        lines.append("")
        for row in external:
            lines.append(f"  – {row.name}: {row.note}")
    lines.append("")
    lines.append(
        "Drift is advisory: a skill edit can never change a match score (matching scores "
        "curated marketplace text only), but that text can fall out of sync with shipped skills. "
        "Close a warning by adding the capability's vocabulary to the plugin's description / "
        "keywords / examplePrompts in .claude-plugin/marketplace.json."
    )
    return "\n".join(lines) + "\n"


def _load_report() -> CoverageReport:
    plugin_root = Path(__file__).resolve().parent.parent
    catalog_data = catalog_mod.load_catalog(plugin_root)
    return compute_coverage(catalog_data)


def _load_drift() -> list:
    """Compute drift against the repo checkout, or return [] when unavailable
    (a packaged copy has no repo root -- drift is a repo-only signal)."""
    plugin_root = Path(__file__).resolve().parent.parent
    try:
        repo_root = catalog_mod._repo_root(plugin_root)
    except catalog_mod.PluginCatalogError:
        return []
    catalog_data = catalog_mod.load_catalog(plugin_root)
    return compute_drift(catalog_data, repo_root)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--report", action="store_true", help="print the human-readable coverage table (default)")
    modes.add_argument("--json", action="store_true", help="print the machine-readable coverage snapshot")
    modes.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any candidate plugin's own example prompts fail the hard discovery invariant",
    )
    options = parser.parse_args(argv)
    try:
        report = _load_report()
    except catalog_mod.PluginCatalogError as exc:
        print(f"plugin-match coverage error: {exc}", file=sys.stderr)
        return 1

    if options.json:
        # Drift is repo-only and advisory; include the block when a checkout is
        # available, omit it (rather than error) when run from a packaged copy.
        print(json.dumps(report_to_dict(report, _load_drift() or None), ensure_ascii=False, indent=2))
        return 0

    if options.check:
        # --check gates on the discovery invariant AND on one "the gate itself is
        # meaningful" guard -- the foundation actually being present in the catalog
        # (so its exclusion is real, not a rename/typo no-op). It mirrors the sibling
        # unittest guard (test_foundation_is_present_in_catalog) so this
        # contributor-facing command can no longer report green while
        # `npm run test:gates` reports red on the same catalog state -- the
        # silent-divergence class of bug.
        #
        # DELIBERATELY gates-only (NOT mirrored here): the runtime-name anti-drift
        # guard (test_foundation_name_matches_runtime_display_name) asserts the
        # foundation name in .claude-plugin/plugin.json and the presence of
        # `_plugin_display_name` in sf_context.py. --check reads only
        # catalog/plugins.json by design (it is the contributor-facing matching
        # gate), so that maintainer-refactor check stays in the unittest suite run
        # by `npm run test:gates`, not here. Recorded so the divergence is
        # intentional, not another latent silent gap.
        if report.foundation_missing_from_catalog:
            print(format_report(report), file=sys.stderr)
            print(
                f"✗ plugin-match coverage: the foundation plugin {report.foundation!r} is not "
                "present in catalog/plugins.json, so excluding it from the candidate corpus is a "
                "no-op (likely a rename or dropped entry). Restore it, or update FOUNDATION_PLUGIN "
                "to match a real rename.",
                file=sys.stderr,
            )
            return 1
        if report.is_clean:
            print(
                f"✓ plugin-match coverage: all {len(report.plugins)} candidate plugins' example "
                f"prompts route to them at high ({report.total_prompts} prompts)."
            )
            return 0
        print(format_report(report), file=sys.stderr)
        print("✗ plugin-match coverage: discovery invariant violated (see above).", file=sys.stderr)
        return 1

    # Default (--report or no flag): print the table, then the advisory drift
    # section when a repo checkout is available.
    print(format_report(report), end="")
    drift = _load_drift()
    if drift:
        print(format_drift(drift), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
