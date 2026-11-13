#!/usr/bin/env python3
"""Expose the shared deterministic command surfaces to explicit Codex requests."""
import argparse
import os
from pathlib import Path
import re

import sf_context


def startup_surface(root: Path) -> str:
    """The session-start banner from local facts only.

    It reads project metadata and the configured target alias without running
    the Salesforce CLI, git or MCP probes; the explicit welcome and status
    surfaces report live org, git and MCP state on request.
    """
    if not (root / 'sfdx-project.json').exists():
        return sf_context._render_no_project_surface()
    project = sf_context.project_meta()
    stats = sf_context.project_stats()
    target = sf_context._configured_target_alias(root) or ''
    state = sf_context._derive_journey_state(
        root, has_project=True, target=target,
        target_error='unprobed' if target else None, org_display=None)
    candidate = sf_context._select_inline_nudge(state, root, None, probe_git=False)
    if target:
        rest = sf_context._sanitize_dynamic_text(target) + ' — /salesforce-development:status'
    else:
        rest = 'none set — /salesforce-development:login'
    org_group = [[('org: ', 'body'), (sf_context._clip(rest, 73), 'muted')]]
    return sf_context.render_degraded_banner(
        org_group, project=project, stats=stats, git_line='git status unprobed',
        state=state, notice_lines=[], candidate=candidate,
        sensitivity_lines=(sf_context._plugin_match_sensitivity_notice_lines()
                           + sf_context._skills_first_notice_lines(include_option=False)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('org', 'project', 'startup', 'status', 'welcome'))
    args = parser.parse_args()
    os.environ['SF_AGENT_CLIENT'] = 'codex'
    cwd = Path.cwd().resolve()
    root = next((p for p in (cwd, *cwd.parents) if (p / 'sfdx-project.json').is_file()), cwd)
    os.chdir(root)
    if args.command == 'startup':
        surface = startup_surface(root)
    else:
        _, surface = sf_context._STATUS_FAMILY_PAINTERS['salesforce-development:' + args.command](root)
    surface = surface.replace('/salesforce-development:setup to scaffold one',
                              'ask to create an SFDX project')
    surface = re.sub(r'/salesforce-development:([a-z][a-z-]*)',
                     r'the Salesforce \1 workflow', surface)
    print(surface)


if __name__ == '__main__':
    main()
