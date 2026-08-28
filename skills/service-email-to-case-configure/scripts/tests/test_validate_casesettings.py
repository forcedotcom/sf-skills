"""Unit tests for validate-casesettings.py.

The validator checks a CaseSettings SOURCE file (the input to
apply-casesettings.py) for structural rules that must hold BEFORE applying —
independent of any org. These are pure, deterministic checks, so they are unit
tested here rather than covered by evals (evals score the LLM-authored artifact
against a gold, they do not assert on the validator's fail-closed behavior).

``validate(path)`` returns a list of human-readable error strings — empty means
the file passed. Each test writes a source file to a temp dir and asserts the
error list contains (or lacks) the expected message.
"""
from __future__ import annotations

import tempfile
import unittest

from . import _bootstrap
from ._run import Input, write_input

validate_mod = _bootstrap.load_validate()


def _errors(xml: str) -> list:
    """Write xml to a temp file, run validate(), return the error list."""
    with tempfile.TemporaryDirectory() as d:
        path = write_input(d, xml)
        return validate_mod.validate(path)


def _has(errors, needle) -> bool:
    return any(needle in e for e in errors)


# A minimal source file that should PASS: E2C on, on-demand on, one well-formed
# EmailToCase routing address, no owner fields, no emailAddress.
def _valid_src(**addr_over) -> str:
    addr = dict(addressType="EmailToCase", routingName="Support",
                caseOrigin="Email", casePriority="Medium")
    addr.update(addr_over)
    return Input().address(**addr).build()


class ValidSourceFile(unittest.TestCase):
    def test_minimal_valid_file_passes(self):
        self.assertEqual(_errors(_valid_src()), [])

    def test_valid_with_optional_toggles_passes(self):
        xml = (Input().with_default_toggles()
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        self.assertEqual(_errors(xml), [])

    def test_valid_with_user_case_owner_passes(self):
        self.assertEqual(
            _errors(_valid_src(caseOwner="agent@acme.com", caseOwnerType="User")),
            [])


class StructuralRules(unittest.TestCase):
    def test_not_well_formed_xml(self):
        errors = _errors("<CaseSettings>not closed")
        self.assertTrue(_has(errors, "not well-formed"))

    def test_wrong_root_element(self):
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<Foo xmlns="http://soap.sforce.com/2006/04/metadata"></Foo>\n')
        self.assertTrue(_has(_errors(xml), "Root element must be CaseSettings"))

    def test_missing_email_to_case_block(self):
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<CaseSettings xmlns="http://soap.sforce.com/2006/04/metadata">\n'
               '</CaseSettings>\n')
        self.assertTrue(_has(_errors(xml), "Missing <emailToCase> block"))


class RequiredToggles(unittest.TestCase):
    def test_on_demand_must_be_true(self):
        xml = (Input().e2c(enableOnDemandEmailToCase="false")
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        self.assertTrue(_has(_errors(xml), "enableOnDemandEmailToCase must be 'true'"))

    def test_enable_email_to_case_must_be_true(self):
        xml = (Input().e2c(enableEmailToCase="false")
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        self.assertTrue(_has(_errors(xml), "enableEmailToCase must be 'true'"))

    def test_non_boolean_toggle_flagged(self):
        xml = (Input().e2c(enableHtmlEmail="yes")
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        self.assertTrue(_has(_errors(xml),
                             "emailToCase.enableHtmlEmail must be 'true' or 'false'"))


class RoutingAddressRules(unittest.TestCase):
    def test_no_routing_address_flagged(self):
        self.assertTrue(_has(_errors(Input().build()), "No <routingAddresses> found"))

    def test_missing_required_address_field(self):
        # routingName omitted
        xml = Input().address(addressType="EmailToCase", caseOrigin="Email",
                              casePriority="Medium").build()
        self.assertTrue(_has(_errors(xml), "missing required field 'routingName'"))

    def test_email_address_in_source_rejected(self):
        # emailAddress must never be in the source file — supplied at apply time.
        xml = _valid_src(emailAddress="support@acme.com")
        self.assertTrue(_has(_errors(xml), "sets 'emailAddress'"))

    def test_readonly_field_rejected(self):
        xml = _valid_src(isVerified="true")
        self.assertTrue(_has(_errors(xml), "read-only field 'isVerified'"))

    def test_e2ceasy_address_type_rejected(self):
        xml = _valid_src(addressType="E2cEasy")
        self.assertTrue(_has(_errors(xml), "E2cEasy"))

    def test_invalid_address_type_rejected(self):
        xml = _valid_src(addressType="Bogus")
        self.assertTrue(_has(_errors(xml), "addressType 'Bogus' invalid"))

    def test_duplicate_routing_name_flagged(self):
        xml = (Input()
               .address(addressType="EmailToCase", routingName="Dup",
                        caseOrigin="Email", casePriority="Medium")
               .address(addressType="EmailToCase", routingName="Dup",
                        caseOrigin="Email", casePriority="High").build())
        self.assertTrue(_has(_errors(xml), "duplicate routingName 'Dup'"))


class PerAddressCaseOwnerRules(unittest.TestCase):
    def test_case_owner_without_type_rejected(self):
        xml = _valid_src(caseOwner="agent@acme.com")  # no caseOwnerType
        self.assertTrue(_has(_errors(xml), "sets caseOwner without caseOwnerType"))

    def test_case_owner_type_without_owner_rejected(self):
        xml = _valid_src(caseOwnerType="User")  # no caseOwner
        self.assertTrue(_has(_errors(xml), "sets caseOwnerType without caseOwner"))

    def test_placeholder_case_owner_rejected(self):
        xml = _valid_src(caseOwner="{CASE_OWNER_USERNAME}", caseOwnerType="User")
        self.assertTrue(_has(_errors(xml), "still the placeholder"))

    def test_invalid_case_owner_type_rejected(self):
        xml = _valid_src(caseOwner="agent@acme.com", caseOwnerType="Group")
        self.assertTrue(_has(_errors(xml),
                             "caseOwnerType must be 'User' or 'Queue'"))


class SupportSettingsRules(unittest.TestCase):
    def test_system_and_named_user_mutually_exclusive(self):
        xml = (Input().top(useSystemUserAsDefaultCaseUser="true",
                           defaultCaseUser="admin@acme.com")
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        self.assertTrue(_has(_errors(xml), "mutually exclusive"))

    def test_invalid_default_owner_type_rejected(self):
        xml = (Input().top(defaultCaseOwnerType="Group")
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        self.assertTrue(_has(_errors(xml),
                             "defaultCaseOwnerType must be 'User' or 'Queue'"))


if __name__ == "__main__":
    unittest.main()
