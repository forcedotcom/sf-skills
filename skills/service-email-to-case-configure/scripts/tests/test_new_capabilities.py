"""Tests for the three capabilities added for the Email-to-Case steel thread:

  1. Production-org safety gate (enforce_production_gate / --confirm-production).
  2. API-version derivation with a 67.0 floor (resolve_api_version).
  3. Act-3 verify-cases proof step (verify_cases / --verify-cases).

All org I/O is mocked via FakeOrg — no live org required.
"""
from __future__ import annotations

import tempfile
import unittest

from . import _bootstrap
from ._fakeorg import FakeOrg
from ._run import Input, run_main, write_input

apply_mod = _bootstrap.load_apply()

ADMIN = "admin@acme.com"
AUTH = "authuser@fake.example.com"


def _fresh(**kw):
    kw.setdefault("case_settings",
                  {"fullName": "Case",
                   "defaultCaseOwner": ADMIN,
                   "defaultCaseOwnerType": "User",
                   "defaultCaseUser": ADMIN,
                   "emailToCase": {"enableEmailToCase": False}})
    kw.setdefault("active_users", [ADMIN, AUTH])
    return FakeOrg(**kw)


def _apply(org, extra_argv, addr=True):
    b = Input().with_default_toggles()
    if addr:
        b = b.address(addressType="EmailToCase", routingName="Support",
                      caseOrigin="Email", casePriority="Medium")
    src = b.build()
    with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
        path = write_input(d, src)
        argv = ["--target-org", "x", "--input", path]
        if addr:
            argv += ["--routing-email", "support@acme.com"]
        return run_main(apply_mod, argv + extra_argv)


class ApiVersionDerivation(unittest.TestCase):
    """resolve_api_version: floor at DEFAULT_API_VERSION, ride newer orgs."""

    def test_floors_below_default(self):
        self.assertEqual(apply_mod.resolve_api_version("62.0"), "67.0")

    def test_equal_to_floor(self):
        self.assertEqual(apply_mod.resolve_api_version("67.0"), "67.0")

    def test_rides_newer_org(self):
        self.assertEqual(apply_mod.resolve_api_version("68.0"), "68.0")

    def test_rides_much_newer_org(self):
        self.assertEqual(apply_mod.resolve_api_version("70.0"), "70.0")

    def test_none_falls_back_to_floor(self):
        self.assertEqual(apply_mod.resolve_api_version(None), "67.0")

    def test_garbage_falls_back_to_floor(self):
        self.assertEqual(apply_mod.resolve_api_version("not-a-version"), "67.0")

    def test_summary_reports_derived_version(self):
        org = _fresh(org_api_version="70.0")
        summary = _apply(org, [])
        self.assertEqual(summary["apiVersion"], "70.0")

    def test_summary_reports_floored_version(self):
        org = _fresh(org_api_version="60.0")
        summary = _apply(org, [])
        self.assertEqual(summary["apiVersion"], "67.0")


class ProductionGate(unittest.TestCase):
    """enforce_production_gate: block prod writes unless --confirm-production."""

    def test_sandbox_writes_without_confirmation(self):
        org = _fresh(is_sandbox=True)
        summary = _apply(org, [])
        self.assertFalse(summary["orgInfo"]["isProduction"])
        self.assertEqual(summary["verified"]["routingAddressCount"], 1)

    def test_trial_writes_without_confirmation(self):
        org = _fresh(is_sandbox=False, is_trial=True, org_type="Trial")
        summary = _apply(org, [])
        self.assertFalse(summary["orgInfo"]["isProduction"])
        self.assertEqual(summary["verified"]["routingAddressCount"], 1)

    def test_production_blocked_without_confirmation(self):
        org = _fresh(is_sandbox=False, is_trial=False,
                     org_type="Professional Edition")
        with self.assertRaises(SystemExit):
            _apply(org, [])
        # nothing was written
        self.assertEqual(org.writes, [])

    def test_production_writes_with_confirmation(self):
        org = _fresh(is_sandbox=False, is_trial=False,
                     org_type="Professional Edition")
        summary = _apply(org, ["--confirm-production"])
        self.assertTrue(summary["orgInfo"]["isProduction"])
        self.assertEqual(summary["verified"]["routingAddressCount"], 1)

    def test_unreadable_org_row_blocked_without_confirmation(self):
        org = _fresh(is_sandbox=None)
        with self.assertRaises(SystemExit):
            _apply(org, [])
        self.assertEqual(org.writes, [])

    def test_unreadable_org_row_writes_with_confirmation(self):
        org = _fresh(is_sandbox=None)
        summary = _apply(org, ["--confirm-production"])
        self.assertEqual(summary["verified"]["routingAddressCount"], 1)


class VerifyCasesMode(unittest.TestCase):
    """verify_cases / --verify-cases: proof requires an Email-origin Case with a
    linked incoming EmailMessage."""

    def _run_verify(self, org, extra=None):
        # --verify-cases needs no input write, but main() requires --input; a
        # throwaway file satisfies argparse (it isn't parsed in this mode).
        src = Input().with_default_toggles().build()
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            return run_main(apply_mod, ["--target-org", "x", "--input", path,
                                        "--verify-cases", *(extra or [])])

    def test_proven_when_case_and_incoming_message(self):
        org = _fresh(
            cases=[{"Id": "500x1", "CaseNumber": "00001001", "Origin": "Email",
                    "SuppliedEmail": "ext@customer.com", "Subject": "Help",
                    "Status": "New", "CreatedDate": "2026-08-18T10:00:00Z"}],
            email_messages=[{"Id": "02sx1", "ParentId": "500x1",
                             "Incoming": True, "FromAddress": "ext@customer.com",
                             "Subject": "Help",
                             "MessageDate": "2026-08-18T10:00:00Z"}])
        summary = self._run_verify(org)
        self.assertTrue(summary["proven"])
        self.assertEqual(summary["caseCount"], 1)
        self.assertEqual(summary["incomingEmailMessageCount"], 1)
        self.assertTrue(summary["cases"][0]["hasIncomingEmailMessage"])

    def test_no_cases_fails_closed(self):
        org = _fresh(cases=[], email_messages=[])
        with self.assertRaises(SystemExit):
            self._run_verify(org)

    def test_case_without_incoming_message_fails_closed(self):
        org = _fresh(
            cases=[{"Id": "500x1", "CaseNumber": "00001001", "Origin": "Email",
                    "SuppliedEmail": "ext@customer.com", "Subject": "Help",
                    "Status": "New", "CreatedDate": "2026-08-18T10:00:00Z"}],
            email_messages=[])  # no linked incoming email
        with self.assertRaises(SystemExit):
            self._run_verify(org)

    def test_supplied_email_filter_narrows_cases(self):
        org = _fresh(
            cases=[
                {"Id": "500x1", "CaseNumber": "1", "Origin": "Email",
                 "SuppliedEmail": "ext@customer.com", "Subject": "A",
                 "Status": "New", "CreatedDate": "2026-08-18T10:00:00Z"},
                {"Id": "500x2", "CaseNumber": "2", "Origin": "Email",
                 "SuppliedEmail": "other@somewhere.com", "Subject": "B",
                 "Status": "New", "CreatedDate": "2026-08-18T11:00:00Z"}],
            email_messages=[{"Id": "02sx1", "ParentId": "500x1",
                             "Incoming": True, "MessageDate": "x"}])
        summary = self._run_verify(org, ["--supplied-email", "ext@customer.com"])
        self.assertEqual(summary["caseCount"], 1)
        self.assertEqual(summary["cases"][0]["suppliedEmail"], "ext@customer.com")
        self.assertTrue(summary["proven"])

    def test_verify_cases_does_not_write(self):
        org = _fresh(
            cases=[{"Id": "500x1", "CaseNumber": "1", "Origin": "Email",
                    "SuppliedEmail": "ext@customer.com", "Subject": "A",
                    "Status": "New", "CreatedDate": "x"}],
            email_messages=[{"Id": "02sx1", "ParentId": "500x1",
                             "Incoming": True, "MessageDate": "x"}])
        self._run_verify(org)
        self.assertEqual(org.writes, [])


if __name__ == "__main__":
    unittest.main()
