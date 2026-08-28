"""Helpers to drive apply-casesettings.py main() in tests: write a temp
CaseSettings input file and invoke main() with an argv, capturing the JSON
summary it prints. main() calls fail()->sys.exit(1) on error, and argparse may
sys.exit(2); both surface as SystemExit for the test to assert on.
"""
from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


def write_input(tmpdir: str, xml: str) -> str:
    path = Path(tmpdir) / "Case.settings-meta.xml"
    path.write_text(xml, encoding="utf-8")
    return str(path)


def run_main(apply_mod, argv):
    """Run main() with the given argv (excluding program name). Returns the
    parsed JSON summary dict printed to stdout. Raises SystemExit as-is."""
    buf = io.StringIO()
    with mock.patch("sys.argv", ["apply-casesettings.py", *argv]):
        with redirect_stdout(buf):
            apply_mod.main()
    out = buf.getvalue().strip()
    return json.loads(out) if out else {}


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
