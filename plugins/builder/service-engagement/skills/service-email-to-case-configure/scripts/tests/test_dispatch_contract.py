"""Contract tests for the dispatch-facing surface of apply-casesettings.py: the
requests it tells the agent to make, the response shapes it must parse, and the
guarantee that it never touches the network or the sf CLI itself.
"""
from __future__ import annotations

import ast
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from . import _bootstrap
from ._fakeorg import FakeOrg
from ._run import Input, run_main, write_input

apply_mod = _bootstrap.load_apply()


def _save(tmp, name, data):
    path = Path(tmp) / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


class NoDirectOrgAccess(unittest.TestCase):
    def test_script_imports_no_network_or_process_modules(self):
        tree = ast.parse(Path(apply_mod.__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {n.name.split(".")[0] for n in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertFalse(imported & {"subprocess", "urllib", "http", "socket",
                                     "requests"})


class RequestShapes(unittest.TestCase):
    def test_read_request_is_readonly_get_with_query_params(self):
        req = apply_mod.settings_read_request("69.0")
        self.assertEqual(req["tool"], "dispatch_readonly")
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["path"], "/services/data/v69.0/headless/metadata")
        self.assertEqual(req["query_params"],
                         {"type": "CaseSettings", "fullName": "Case"})

    def test_soql_is_in_query_params_not_the_path(self):
        req = apply_mod.org_request("67.0")
        self.assertEqual(req["tool"], "dispatch_readonly")
        self.assertNotIn("?", req["path"])
        self.assertIn("FROM Organization", req["query_params"]["q"])

    def test_write_request_uses_dispatch_put_with_owned_fields_only(self):
        import xml.etree.ElementTree as ET
        records = ET.fromstring(
            '<CaseSettings xmlns="http://soap.sforce.com/2006/04/metadata">'
            "<enableCaseFeed>true</enableCaseFeed>"
            "<enableDraftEmails>true</enableDraftEmails>"
            "<emailToCase><enableEmailToCase>true</enableEmailToCase>"
            "<routingAddresses><routingName>A</routingName>"
            "<isVerified>true</isVerified></routingAddresses></emailToCase>"
            "</CaseSettings>")
        req = apply_mod.settings_write_request("67.0", records, "t")
        self.assertEqual((req["tool"], req["method"]), ("dispatch", "PUT"))
        body = req["body"]
        self.assertEqual((body["type"], body["fullName"]),
                         ("CaseSettings", "Case"))
        self.assertNotIn("enableCaseFeed", body["xmlRep"])
        self.assertNotIn("isVerified", body["xmlRep"])
        self.assertIn("enableDraftEmails", body["xmlRep"])

    def test_soql_values_are_escaped(self):
        req = apply_mod.cases_request("67.0", "o'brien@x.com")
        self.assertIn("o\\'brien@x.com", req["query_params"]["q"])

    def test_lookup_queries_only_for_values_being_written(self):
        org = FakeOrg(case_settings={
            "fullName": "Case", "defaultCaseOwner": "a@x.com",
            "defaultCaseOwnerType": "User", "defaultCaseUser": "a@x.com",
            "emailToCase": {"enableEmailToCase": False}})
        src = Input().with_default_toggles().build()
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            inp = write_input(d, src)
            current = _save(d, "cur.json", org.dispatch(
                apply_mod.settings_read_request("67.0")))
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                apply_mod.main(["requests", "lookups", "--input", inp,
                                "--current", current])
        # Support Settings are all configured and nothing new is named: no lookups.
        self.assertEqual(json.loads(buf.getvalue())["requests"], [])


class ResponseShapes(unittest.TestCase):
    def test_unsupported_operation_bare_array(self):
        body = [{"errorCode": "UNSUPPORTED_OPERATION",
                 "message": "MetadataCrud does not support READ on type: X"}]
        msgs = apply_mod.error_messages(400, body)
        self.assertEqual(len(msgs), 1)
        self.assertIn("UNSUPPORTED_OPERATION", msgs[0])

    def test_rule_error_results_shape(self):
        body = {"results": [{"success": False, "errors": [
            {"statusCode": "INVALID_FIELD", "message": "needs E2C first"}]}]}
        self.assertEqual(apply_mod.error_messages(400, body),
                         ["INVALID_FIELD: needs E2C first"])

    def test_provisioning_failure_is_reported(self):
        body = {"results": [{"success": False, "errors": [
            {"statusCode": "UNKNOWN_EXCEPTION",
             "message": "We couldn't save your routing address"}]}]}
        msgs = apply_mod.error_messages(500, body)
        self.assertIn("couldn't save your routing address", msgs[0])

    def test_success_has_no_errors(self):
        body = {"results": [{"success": True, "fullName": "Case", "errors": []}]}
        self.assertEqual(apply_mod.error_messages(200, body), [])

    def test_bare_non_2xx_without_detail_still_errors(self):
        self.assertTrue(apply_mod.error_messages(502, {}))

    def _check_write(self, envelope):
        with tempfile.TemporaryDirectory() as d:
            path = _save(d, "w.json", envelope)
            with redirect_stdout(io.StringIO()):
                apply_mod.main(["check-write", "--response", path])

    def test_check_write_accepts_success(self):
        self._check_write({"status_code": 200, "body": {"results": [
            {"success": True, "fullName": "Case", "errors": []}]}})

    def test_check_write_rejects_400_and_500(self):
        for status in (400, 500):
            with self.assertRaises(SystemExit):
                self._check_write({"status_code": status, "body": {"results": [
                    {"success": False, "errors": [
                        {"statusCode": "X", "message": "boom"}]}]}})

    def test_check_write_rejects_success_status_without_success_result(self):
        with self.assertRaises(SystemExit):
            self._check_write({"status_code": 200, "body": {"results": []}})

    def test_read_failure_stops_the_flow(self):
        org = FakeOrg(case_settings={"fullName": "Case",
                                     "emailToCase": {"enableEmailToCase": False}})
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = _save(d, "r.json", {"status_code": 400, "body": [
                {"errorCode": "UNSUPPORTED_OPERATION", "message": "nope"}]})
            with self.assertRaises(SystemExit):
                apply_mod.main(["read", "--response", path])


class VersionResolution(unittest.TestCase):
    def test_default_paths_are_unversioned(self):
        req = apply_mod.settings_read_request(None)
        self.assertEqual(req["path"], "/services/data/headless/metadata")
        self.assertEqual(apply_mod.org_request(None)["path"], "/services/data/query")

    def test_flow_uses_dispatch_tools_only_for_writes_via_put(self):
        org = FakeOrg(case_settings={"fullName": "Case",
                                     "defaultCaseOwner": "a@x.com",
                                     "defaultCaseOwnerType": "User",
                                     "defaultCaseUser": "a@x.com",
                                     "emailToCase": {"enableEmailToCase": False}})
        src = Input().with_default_toggles().build()
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            run_main(apply_mod, ["--input", write_input(d, src)])
        puts = [c for c in org.calls if c[1] == "PUT"]
        self.assertTrue(puts)
        self.assertTrue(all(t == "dispatch" for t, _m, _p in puts))
        self.assertTrue(all(p.startswith("/services/data/")
                            for _t, m, p in org.calls if m != "GET"
                            or "/query" in p))


class SilentlyIgnoredSupportSetting(unittest.TestCase):
    """A 200 write that the org did not persist must fail verify."""

    def _settings(self, **fields):
        body = "".join(f"<{k}>{v}</{k}>" for k, v in fields.items())
        xml = ('<?xml version="1.0" encoding="UTF-8"?><CaseSettings xmlns='
               '"http://soap.sforce.com/2006/04/metadata"><emailToCase>'
               '<enableEmailToCase>true</enableEmailToCase></emailToCase>'
               f'{body}</CaseSettings>')
        return {"status_code": 200, "body": {"type": "CaseSettings",
                                             "fullName": "Case", "xmlRep": xml}}

    def _verify(self, after_fields):
        initial = self._settings(defaultCaseOwner="a@x.com",
                                 defaultCaseOwnerType="User",
                                 useSystemUserAsDefaultCaseUser="true")
        with tempfile.TemporaryDirectory() as d:
            files = {"initial": _save(d, "i.json", initial),
                     "after": _save(d, "a.json", self._settings(**after_fields)),
                     "users": _save(d, "u.json", {"status_code": 200, "body": {
                         "records": [{"Username": "u@x.com"}]}})}
            src = Path(d) / "in.xml"
            src.write_text(Input().build(), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                apply_mod.main(["verify", "--input", str(src),
                                "--initial", files["initial"],
                                "--after", files["after"],
                                "--users", files["users"],
                                "--overwrite-support-settings",
                                "--automated-type", "User",
                                "--automated-value", "u@x.com"])

    def test_ignored_automated_user_fails(self):
        with self.assertRaises(SystemExit):
            self._verify({"defaultCaseOwner": "a@x.com",
                          "defaultCaseOwnerType": "User",
                          "useSystemUserAsDefaultCaseUser": "true"})

    def test_persisted_automated_user_passes(self):
        self._verify({"defaultCaseOwner": "a@x.com", "defaultCaseOwnerType": "User",
                      "defaultCaseUser": "u@x.com",
                      "useSystemUserAsDefaultCaseUser": "false"})


class OutlookAddress(unittest.TestCase):
    """Outlook addresses take no emailAddress and require a caseOwner."""

    ADMIN = "admin@acme.com"

    def _org(self):
        return FakeOrg(active_users=[self.ADMIN],
                       case_settings={"fullName": "Case",
                                      "defaultCaseOwner": self.ADMIN,
                                      "defaultCaseOwnerType": "User",
                                      "defaultCaseUser": self.ADMIN,
                                      "emailToCase": {"enableEmailToCase": False}})

    def _src(self, outlook_owner=True):
        outlook = dict(addressType="Outlook", routingName="Sales Outlook",
                       caseOrigin="Email", casePriority="High")
        if outlook_owner:
            outlook.update(caseOwner=self.ADMIN, caseOwnerType="User")
        return (Input().address(addressType="EmailToCase", routingName="Support",
                                caseOrigin="Email", casePriority="Medium")
                .address(**outlook).build())

    def test_email_goes_to_the_email_address_only(self):
        org = self._org()
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            summary = run_main(apply_mod, ["--input", write_input(d, self._src()),
                                           "--routing-email", "a@acme.com"])
        addrs = org.state["emailToCase"]["routingAddresses"]
        by_type = {a["addressType"]: a for a in addrs}
        self.assertEqual(by_type["EmailToCase"]["emailAddress"], "a@acme.com")
        self.assertNotIn("emailAddress", by_type["Outlook"])
        self.assertEqual(summary["verified"]["routingAddressCount"], 2)

    def test_outlook_without_owner_fails_before_any_write(self):
        org = self._org()
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            with self.assertRaises(SystemExit):
                run_main(apply_mod, ["--input",
                                     write_input(d, self._src(outlook_owner=False)),
                                     "--routing-email", "a@acme.com"])
        self.assertEqual(org.writes, [])

    def test_email_count_ignores_outlook(self):
        org = self._org()
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            with self.assertRaises(SystemExit):
                run_main(apply_mod, ["--input", write_input(d, self._src()),
                                     "--routing-email", "a@acme.com",
                                     "--routing-email", "b@acme.com"])


class PhaseBNeedsAFreshRead(unittest.TestCase):
    """Phase B writes back the record it is given, so a read taken before Phase A
    landed must be refused rather than reverting Phase A's toggles."""

    def _phase_b(self, org, tmp, src):
        input_path = Path(tmp) / "source.xml"
        input_path.write_text(src, encoding="utf-8")
        read = org.dispatch(apply_mod.settings_read_request("69.0"))
        current = _save(tmp, "current.json", read)
        return ["phase-b", "--input", str(input_path), "--current", current,
                "--routing-email", "support@acme.com"]

    def _src(self):
        return (Input().with_default_toggles()
                .address(addressType="EmailToCase", routingName="Support",
                         caseOrigin="Email", casePriority="Medium").build())

    def test_a_read_from_before_phase_a_is_refused(self):
        org = FakeOrg(case_settings={"fullName": "Case",
                                     "emailToCase": {"enableEmailToCase": False}})
        with tempfile.TemporaryDirectory() as tmp:
            argv = self._phase_b(org, tmp, self._src())
            with self.assertRaises(SystemExit):
                apply_mod.main(argv)
        self.assertEqual(org.writes, [])

    def test_a_read_taken_after_phase_a_is_accepted(self):
        org = FakeOrg(case_settings={
            "fullName": "Case",
            "emailToCase": {"enableEmailToCase": True,
                            "enableOnDemandEmailToCase": True}})
        with tempfile.TemporaryDirectory() as tmp:
            argv = self._phase_b(org, tmp, self._src())
            buf = io.StringIO()
            with redirect_stdout(buf):
                apply_mod.main(argv)
        self.assertIn("request", json.loads(buf.getvalue()))


if __name__ == "__main__":
    unittest.main()
