"""Plays the agent's part of the SKILL.md flow against a ``FakeOrg``.

The script only prints requests and validates responses; the agent does the
dispatching. ``run_flow`` performs that loop in-process - for each request the
script prints it hands the request to ``FakeOrg.dispatch``, saves the envelope to
a file, and feeds the file to the next subcommand - then folds the subcommand
outputs into one summary so scenario tests can assert on the end state.

Order matches SKILL.md: gate, initial read, lookups, Phase A write,
fresh read, Phase B write, final read, verify. Any subcommand failure surfaces as
SystemExit exactly as it would stop the agent.
"""
from __future__ import annotations

import argparse
import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ACTIVE = None


class Active:
    """Context manager that makes ``run_main`` use a FakeOrg."""

    def __init__(self, org):
        self.org = org

    def __enter__(self):
        global ACTIVE
        ACTIVE = self.org
        return self

    def __exit__(self, *exc):
        global ACTIVE
        ACTIVE = None
        return False


def _flow_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input")
    ap.add_argument("--routing-email", action="append", default=[])
    ap.add_argument("--owner-type")
    ap.add_argument("--owner-value")
    ap.add_argument("--automated-type")
    ap.add_argument("--automated-value")
    ap.add_argument("--system-user-email")
    ap.add_argument("--overwrite-support-settings", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--verify-cases", action="store_true")
    ap.add_argument("--supplied-email")
    ap.add_argument("--confirm-production", action="store_true")
    return ap


class Flow:
    def __init__(self, org, mod, tmp):
        self.org, self.mod, self.tmp = org, mod, Path(tmp)
        self.n = 0

    def script(self, argv):
        """Run one subcommand; return its parsed JSON stdout."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.mod.main(argv)
        out = buf.getvalue().strip()
        return json.loads(out) if out else {}

    def save(self, name, data):
        self.n += 1
        path = self.tmp / f"{self.n:02d}-{name}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def dispatch_all(self, requests, name):
        return [self.save(name, self.org.dispatch(r)) for r in requests]

    def fetch(self, argv, name):
        """Run `requests ...` and dispatch what it prints; return saved paths."""
        reqs = self.script(["requests", *argv])["requests"]
        return self.dispatch_all(reqs, name)

    def write(self, request):
        path = self.save("write", self.org.dispatch(request))
        self.script(["check-write", "--response", path])


def run_flow(org, mod, argv):
    a = _flow_parser().parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        f = Flow(org, mod, tmp)
        if a.verify_cases:
            return _verify_cases(f, a)
        if not a.input:
            raise SystemExit(1)
        ver = []
        if a.verify_only:
            current = f.fetch(["settings", *ver], "current")[0]
            return f.script(["read", "--response", current])

        summary = {"phaseA": {}, "phaseB": []}
        gate_file = f.fetch(["org", *ver], "org")[0]
        gate = ["gate", "--org", gate_file]
        if a.confirm_production:
            gate.append("--confirm-production")
        summary["orgInfo"] = f.script(gate)["orgInfo"]

        emails = [x for e in a.routing_email for x in ("--routing-email", e)]
        support = []
        for flag, val in (("--owner-type", a.owner_type),
                          ("--owner-value", a.owner_value),
                          ("--automated-type", a.automated_type),
                          ("--automated-value", a.automated_value),
                          ("--system-user-email", a.system_user_email)):
            if val:
                support += [flag, val]
        if a.overwrite_support_settings:
            support.append("--overwrite-support-settings")
        base = ["--input", a.input, *ver, *emails]

        initial = f.fetch(["settings", *ver], "initial")[0]
        lookups = f.script(["requests", "lookups", "--current", initial,
                            *base, *support])["requests"]
        lookup_flags = []
        for req, path in zip(lookups, f.dispatch_all(lookups, "lookup")):
            flag = "--users" if "FROM User" in req["query_params"]["q"] \
                else "--queues"
            lookup_flags += [flag, path]

        out = f.script(["phase-a", "--current", initial, *base, *support,
                        *lookup_flags])
        summary["phaseA"] = out["summary"]["phaseA"]
        summary["supportSettings"] = out["summary"]["supportSettings"]
        f.write(out["request"])

        current = f.fetch(["settings", *ver], "after-a")[0]
        out = f.script(["phase-b", "--current", current, *base, *support,
                        *lookup_flags])
        if "request" in out:
            f.write(out["request"])

        after = f.fetch(["settings", *ver], "after")[0]
        verified = f.script(["verify", "--initial", initial, "--after", after,
                             *base, *support, *lookup_flags])
        summary["verified"] = verified["verified"]
        summary["phaseB"] = verified["phaseB"]
        return summary


def _verify_cases(f, a):
    cases = f.fetch(["cases", *(["--supplied-email", a.supplied_email]
                                if a.supplied_email else [])], "cases")[0]
    msgs = f.fetch(["messages", "--cases-response", cases], "messages")
    argv = ["cases", "--cases", cases]
    if msgs:
        argv += ["--messages", msgs[0]]
    if a.supplied_email:
        argv += ["--supplied-email", a.supplied_email]
    return f.script(argv)
