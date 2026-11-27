"""Helpers to drive the apply-casesettings.py flow in tests: write a temp
CaseSettings input file and run the agent flow against a FakeOrg. The script's
fail() calls sys.exit(1) and argparse may sys.exit(2); both surface as SystemExit
for the test to assert on.
"""
from __future__ import annotations

from pathlib import Path


def write_input(tmpdir: str, xml: str) -> str:
    path = Path(tmpdir) / "Case.settings-meta.xml"
    path.write_text(xml, encoding="utf-8")
    return str(path)


def run_main(apply_mod, argv):
    """Run the agent flow for ``argv`` (the old single-command flag set) against
    the active FakeOrg and return the combined JSON summary. Failures surface as
    SystemExit, as they would stop the agent."""
    from . import _agent
    assert _agent.ACTIVE is not None, "wrap the call in org.patch(apply_mod)"
    return _agent.run_flow(_agent.ACTIVE, apply_mod, list(argv))


class Input:
    """Fluent builder for a CaseSettings source XML string."""

    def __init__(self):
        self._top = {}
        self._e2c = {"enableEmailToCase": "true",
                     "enableOnDemandEmailToCase": "true"}
        self._addrs = []

    def top(self, **kv):
        self._top.update(kv)
        return self

    def e2c(self, **kv):
        self._e2c.update(kv)
        return self

    def no_e2c_defaults(self):
        self._e2c = {"enableEmailToCase": "true",
                     "enableOnDemandEmailToCase": "true"}
        return self

    def with_default_toggles(self):
        self._e2c.update({
            "enableHtmlEmail": "true",
            "notifyOwnerOnNewCaseEmail": "true",
            "enableE2CDeduplicateAttachments": "true",
            "showWordCountInComposer": "true",
        })
        self._top["enableDraftEmails"] = "true"
        return self

    def address(self, **kv):
        self._addrs.append(kv)
        return self

    def build(self) -> str:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<CaseSettings xmlns="http://soap.sforce.com/2006/04/metadata">']
        for k, v in self._top.items():
            lines.append(f"    <{k}>{v}</{k}>")
        lines.append("    <emailToCase>")
        for k, v in self._e2c.items():
            lines.append(f"        <{k}>{v}</{k}>")
        for addr in self._addrs:
            lines.append("        <routingAddresses>")
            for k, v in addr.items():
                lines.append(f"            <{k}>{v}</{k}>")
            lines.append("        </routingAddresses>")
        lines.append("    </emailToCase>")
        lines.append("</CaseSettings>")
        return "\n".join(lines) + "\n"
