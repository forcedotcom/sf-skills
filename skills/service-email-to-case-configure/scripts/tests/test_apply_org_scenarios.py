"""End-to-end scenario tests for apply-casesettings.py against a FakeOrg.

Covers the org-state matrix requested for this skill:
  1. Org with NO support settings and NO email-to-case toggles.
  2. Org with support settings already set but NO email-to-case toggles.
  3. Org with support settings + enableEmailToCase, but NO on-demand toggle.
  4. Org with all required toggles but NO routing address.
  5. Org with all required toggles + an existing routing address — a NEW address
     is CREATED, the existing one is preserved (not edited).
  6. Support-settings resolution with User, Queue, and System.
  7. Per-address caseOwner supplied vs not; User- and Queue-type owners.

Plus the optional-toggle guarantees:
  * optional toggles ARE written to the org when present in the source file;
  * when the user opts OUT of a toggle (it is absent from the source file), it
    is NOT written and the org keeps its current value.

All org I/O is mocked via FakeOrg — no live org required.
"""
from __future__ import annotations

import tempfile
import unittest

from . import _bootstrap
from ._fakeorg import FakeOrg, last_e2c_write, top_level_keys_written
from ._run import Input, run_main, write_input

apply_mod = _bootstrap.load_apply()

# Fields the skill defaults ON (opt-out model); used to assert opt-out behavior.
DEFAULT_E2C_TOGGLES = ["enableHtmlEmail", "notifyOwnerOnNewCaseEmail",
                       "enableE2CDeduplicateAttachments",
                       "showWordCountInComposer"]

ADMIN = "admin@acme.com"
AUTH = "authuser@fake.example.com"  # matches FakeOrg.auth_username


def fresh_org(**kw):
    """Org with nothing configured: E2C off, no addresses, no support settings."""
    kw.setdefault("case_settings",
                  {"fullName": "Case",
                   "emailToCase": {"enableEmailToCase": False}})
    return FakeOrg(**kw)


# The three mutually-exclusive automated-user fields. The platform merges
# top-level fields, so the ONLY layer the script can guarantee they are
# non-contradictory on a type switch is the payload it sends — hence tests
# assert on the write payload, not the FakeOrg's post-merge state.
AUTOMATED_USER_FIELDS = ("defaultCaseUser", "useSystemUserAsDefaultCaseUser",
                         "systemUserEmail")


def automated_user_payload(org):
    """The automated-user fields carried by the Phase A updateMetadata write."""
    for w in org.writes:
        if any(f in w for f in AUTOMATED_USER_FIELDS):
            return {f: w[f] for f in AUTOMATED_USER_FIELDS if f in w}
    return {}


class Scenario1_NoSupportNoToggles(unittest.TestCase):
    """No support settings, no toggles: skill must set support settings from
    supplied values and enable the toggles + address."""

    def test_sets_owner_toggles_and_address(self):
        org = fresh_org(active_users=[ADMIN, AUTH])
        src = (Input().with_default_toggles()
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium",
                        saveEmailHeaders="true").build())
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            summary = run_main(apply_mod, [
                "--target-org", "x", "--input", path,
                "--routing-email", "support@acme.com",
                "--owner-type", "User", "--owner-value", ADMIN,
                "--automated-type", "User", "--automated-value", ADMIN,
            ])
        # support settings set from input
        self.assertEqual(org.state["defaultCaseOwner"], ADMIN)
        self.assertEqual(org.state["defaultCaseOwnerType"], "User")
        self.assertEqual(org.state["defaultCaseUser"], ADMIN)
        # toggles + on-demand live
        e2c = org.state["emailToCase"]
        self.assertTrue(e2c["enableEmailToCase"])
        self.assertTrue(e2c["enableOnDemandEmailToCase"])
        # address created
        self.assertEqual(summary["phaseB"][0]["status"], "created")
        self.assertEqual(summary["verified"]["routingAddressCount"], 1)


class Scenario2_SupportSetNoToggles(unittest.TestCase):
    """Support settings already configured: they are PRESERVED (no flags), and
    the toggles are enabled."""

    def test_preserves_existing_support_settings(self):
        org = fresh_org(active_users=[ADMIN, AUTH])
        org.state.update({"defaultCaseOwner": ADMIN,
                          "defaultCaseOwnerType": "User",
                          "defaultCaseUser": ADMIN})
        src = (Input().with_default_toggles()
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            summary = run_main(apply_mod, [
                "--target-org", "x", "--input", path,
                "--routing-email", "support@acme.com",
            ])
        self.assertEqual(summary["supportSettings"]["action"],
                         "preserved-existing")
        # unchanged
        self.assertEqual(org.state["defaultCaseOwner"], ADMIN)
        self.assertTrue(org.state["emailToCase"]["enableOnDemandEmailToCase"])


class Scenario2b_PartialSupportSettings(unittest.TestCase):
    """Default Case Owner and Automated Case User are independent — an org can
    have one configured and the other not. Each is preserved or set on its own:
    supplying only the missing field succeeds; the configured field is left
    untouched; overwriting a configured field still requires the flag."""

    ADMIN2 = "admin2@acme.com"

    def _run(self, org, extra):
        src = (Input().with_default_toggles()
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            return run_main(apply_mod, [
                "--target-org", "x", "--input", path,
                "--routing-email", "support@acme.com", *extra])

    def test_owner_set_supply_only_automated_user(self):
        # Owner already configured, automated user NOT. Supplying only the
        # automated user must succeed and preserve the existing owner untouched.
        org = fresh_org(active_users=[ADMIN, AUTH])
        org.state.update({"defaultCaseOwner": ADMIN,
                          "defaultCaseOwnerType": "User"})
        summary = self._run(org, ["--automated-type", "User",
                                  "--automated-value", ADMIN])
        ss = summary["supportSettings"]
        self.assertEqual(ss["ownerAction"], "preserved")
        self.assertEqual(ss["automatedUserAction"], "set-from-input")
        # owner preserved, automated user set
        self.assertEqual(org.state["defaultCaseOwner"], ADMIN)
        self.assertEqual(org.state["defaultCaseUser"], ADMIN)

    def test_automated_user_set_supply_only_owner(self):
        # Automated user already configured, owner NOT. Supplying only the owner
        # must succeed and preserve the existing automated user untouched.
        org = fresh_org(active_users=[ADMIN, self.ADMIN2, AUTH])
        org.state.update({"defaultCaseUser": ADMIN,
                          "useSystemUserAsDefaultCaseUser": False})
        summary = self._run(org, ["--owner-type", "User",
                                  "--owner-value", self.ADMIN2])
        ss = summary["supportSettings"]
        self.assertEqual(ss["ownerAction"], "set-from-input")
        self.assertEqual(ss["automatedUserAction"], "preserved")
        self.assertEqual(org.state["defaultCaseOwner"], self.ADMIN2)
        self.assertEqual(org.state["defaultCaseUser"], ADMIN)  # preserved

    def test_owner_set_supplying_owner_does_not_overwrite_without_flag(self):
        # Owner already configured; caller supplies a DIFFERENT owner but no
        # --overwrite-support-settings. The existing owner must be preserved
        # (the supplied value is ignored, not written).
        org = fresh_org(active_users=[ADMIN, self.ADMIN2, AUTH])
        org.state.update({"defaultCaseOwner": ADMIN,
                          "defaultCaseOwnerType": "User"})
        summary = self._run(org, ["--owner-type", "User",
                                  "--owner-value", self.ADMIN2,
                                  "--automated-type", "User",
                                  "--automated-value", ADMIN])
        ss = summary["supportSettings"]
        self.assertEqual(ss["ownerAction"], "preserved")
        self.assertEqual(org.state["defaultCaseOwner"], ADMIN)  # NOT ADMIN2

    def test_overwrite_flag_replaces_configured_owner(self):
        # With --overwrite-support-settings, a configured owner IS replaced.
        org = fresh_org(active_users=[ADMIN, self.ADMIN2, AUTH])
        org.state.update({"defaultCaseOwner": ADMIN,
                          "defaultCaseOwnerType": "User"})
        summary = self._run(org, ["--owner-type", "User",
                                  "--owner-value", self.ADMIN2,
                                  "--automated-type", "User",
                                  "--automated-value", ADMIN,
                                  "--overwrite-support-settings"])
        ss = summary["supportSettings"]
        self.assertEqual(ss["ownerAction"], "overwrote-existing")
        self.assertEqual(ss["action"], "overwrote-existing")
        self.assertEqual(org.state["defaultCaseOwner"], self.ADMIN2)

    # --- --overwrite-support-settings is scoped PER FIELD ---
    # A single global overwrite flag must NOT force a rewrite of the field the
    # caller did not supply input for. Overwriting only the owner leaves a
    # configured automated user untouched, and vice versa.

    def test_overwrite_owner_only_preserves_configured_automated_user(self):
        # BOTH configured. Caller overwrites ONLY the owner (supplies only owner
        # input) with the flag set. The automated user must be PRESERVED — not
        # rewritten and not demanding input.
        org = fresh_org(active_users=[ADMIN, self.ADMIN2, AUTH])
        org.state.update({"defaultCaseOwner": ADMIN,
                          "defaultCaseOwnerType": "User",
                          "defaultCaseUser": ADMIN,
                          "useSystemUserAsDefaultCaseUser": False})
        summary = self._run(org, ["--owner-type", "User",
                                  "--owner-value", self.ADMIN2,
                                  "--overwrite-support-settings"])
        ss = summary["supportSettings"]
        self.assertEqual(ss["ownerAction"], "overwrote-existing")
        self.assertEqual(ss["automatedUserAction"], "preserved")
        self.assertEqual(org.state["defaultCaseOwner"], self.ADMIN2)
        self.assertEqual(org.state["defaultCaseUser"], ADMIN)  # untouched
        # Preserved means UNCHANGED: the automated user is never resolved from
        # fresh input or flipped to another type — its existing value is carried
        # through as-is (the named user stays; the System flag is not set).
        self.assertEqual(automated_user_payload(org),
                         {"defaultCaseUser": ADMIN,
                          "useSystemUserAsDefaultCaseUser": False})

    def test_overwrite_automated_only_preserves_configured_owner(self):
        # BOTH configured. Caller overwrites ONLY the automated user (supplies
        # only automated input) with the flag set. The owner must be PRESERVED.
        org = fresh_org(active_users=[ADMIN, self.ADMIN2, AUTH])
        org.state.update({"defaultCaseOwner": ADMIN,
                          "defaultCaseOwnerType": "User",
                          "defaultCaseUser": ADMIN,
                          "useSystemUserAsDefaultCaseUser": False})
        summary = self._run(org, ["--automated-type", "User",
                                  "--automated-value", self.ADMIN2,
                                  "--overwrite-support-settings"])
        ss = summary["supportSettings"]
        self.assertEqual(ss["ownerAction"], "preserved")
        self.assertEqual(ss["automatedUserAction"], "overwrote-existing")
        self.assertEqual(org.state["defaultCaseOwner"], ADMIN)  # untouched
        self.assertEqual(automated_user_payload(org),
                         {"defaultCaseUser": self.ADMIN2,
                          "useSystemUserAsDefaultCaseUser": False})

    # --- Automated-user TYPE switches clear the mutually-exclusive field ---
    # System and a named User are mutually exclusive at the platform layer, so
    # on an overwrite the payload must carry ONLY the new type's fields and must
    # NOT re-send the old type's field (leaving both populated would produce a
    # contradictory payload). Asserted on the write payload
    # because the platform preserves any OMITTED top-level field via merge.

    def test_overwrite_named_user_with_system_clears_named_user(self):
        org = fresh_org(active_users=[ADMIN, AUTH], queues=["Support_Queue"])
        org.state.update({"defaultCaseOwner": "Support_Queue",
                          "defaultCaseOwnerType": "Queue",
                          "defaultCaseUser": ADMIN,
                          "useSystemUserAsDefaultCaseUser": False})
        summary = self._run(org, ["--automated-type", "System",
                                  "--system-user-email", "ops@acme.com",
                                  "--overwrite-support-settings"])
        self.assertEqual(summary["supportSettings"]["automatedUserAction"],
                         "overwrote-existing")
        payload = automated_user_payload(org)
        self.assertEqual(payload.get("useSystemUserAsDefaultCaseUser"), True)
        self.assertEqual(payload.get("systemUserEmail"), "ops@acme.com")
        # The stale named user must NOT be re-sent alongside System.
        self.assertNotIn("defaultCaseUser", payload)

    def test_overwrite_system_with_named_user_clears_system_flag(self):
        org = fresh_org(active_users=[ADMIN, AUTH], queues=["Support_Queue"])
        org.state.update({"defaultCaseOwner": "Support_Queue",
                          "defaultCaseOwnerType": "Queue",
                          "useSystemUserAsDefaultCaseUser": True,
                          "systemUserEmail": "ops@acme.com"})
        summary = self._run(org, ["--automated-type", "User",
                                  "--automated-value", ADMIN,
                                  "--overwrite-support-settings"])
        self.assertEqual(summary["supportSettings"]["automatedUserAction"],
                         "overwrote-existing")
        payload = automated_user_payload(org)
        self.assertEqual(payload.get("defaultCaseUser"), ADMIN)
        self.assertEqual(payload.get("useSystemUserAsDefaultCaseUser"), False)
        # The stale System-user email must NOT be re-sent alongside a named User.
        self.assertNotIn("systemUserEmail", payload)


class Scenario3_ToggleOnNoOnDemand(unittest.TestCase):
    """Org has enableEmailToCase already true but on-demand off: the apply must
    turn on-demand on (so addresses can bind)."""

    def test_enables_on_demand(self):
        org = FakeOrg(
            case_settings={"fullName": "Case",
                           "defaultCaseOwner": ADMIN,
                           "defaultCaseOwnerType": "User",
                           "defaultCaseUser": ADMIN,
                           "emailToCase": {"enableEmailToCase": True,
                                           "enableOnDemandEmailToCase": False}},
            active_users=[ADMIN, AUTH])
        src = (Input().with_default_toggles()
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            summary = run_main(apply_mod, [
                "--target-org", "x", "--input", path,
                "--routing-email", "support@acme.com",
            ])
        self.assertTrue(org.state["emailToCase"]["enableOnDemandEmailToCase"])
        self.assertEqual(summary["verified"]["enableOnDemandEmailToCase"], True)


class Scenario4_AllTogglesNoAddress(unittest.TestCase):
    """All required toggles present, input declares no routing address: Phase A
    runs, Phase B is a no-op, count stays 0."""

    def test_no_address_declared(self):
        org = fresh_org(active_users=[ADMIN, AUTH])
        org.state.update({"defaultCaseOwner": ADMIN,
                          "defaultCaseOwnerType": "User",
                          "defaultCaseUser": ADMIN})
        src = Input().with_default_toggles().build()  # no .address()
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            summary = run_main(apply_mod, ["--target-org", "x", "--input", path])
        self.assertEqual(summary["phaseB"], [])
        self.assertEqual(summary["verified"]["routingAddressCount"], 0)
        self.assertTrue(org.state["emailToCase"]["enableEmailToCase"])


class Scenario5_NewAddressNotEdit(unittest.TestCase):
    """An org with an existing address gets a NEW one appended; the existing is
    preserved (create, not edit)."""

    def test_appends_new_preserves_existing(self):
        org = FakeOrg(
            case_settings={"fullName": "Case",
                           "defaultCaseOwner": ADMIN,
                           "defaultCaseOwnerType": "User",
                           "defaultCaseUser": ADMIN,
                           "emailToCase": {
                               "enableEmailToCase": True,
                               "enableOnDemandEmailToCase": True,
                               "routingAddresses": {
                                   "addressType": "EmailToCase",
                                   "routingName": "Existing Support",
                                   "caseOrigin": "Email",
                                   "casePriority": "Medium",
                                   "emailAddress": "old@acme.com",
                                   # A real provisioned address always carries
                                   # these platform-managed read-only fields on
                                   # read; seed them so the fake mirrors a live
                                   # org. Preservation is driven by document
                                   # ORDER (new address before existing), not by
                                   # these fields — see MultiAddressOrdering...
                                   "emailServicesAddress": "old@svc.example.com",
                                   "isVerified": True}}},
            active_users=[ADMIN, AUTH])
        src = (Input().with_default_toggles()
               .address(addressType="EmailToCase", routingName="Billing",
                        caseOrigin="Email", casePriority="High").build())
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            summary = run_main(apply_mod, [
                "--target-org", "x", "--input", path,
                "--routing-email", "billing@acme.com",
            ])
        self.assertEqual(summary["verified"]["routingAddressCount"], 2)
        names = {a["routingName"]
                 for a in org.state["emailToCase"]["routingAddresses"]}
        self.assertIn("Existing Support", names)  # preserved
        self.assertIn("Billing", names)           # created
        self.assertEqual(summary["phaseB"][0]["status"], "created")

    def test_duplicate_address_reported_not_duplicated(self):
        org = FakeOrg(
            case_settings={"fullName": "Case",
                           "defaultCaseOwner": ADMIN,
                           "defaultCaseOwnerType": "User",
                           "defaultCaseUser": ADMIN,
                           "emailToCase": {
                               "enableEmailToCase": True,
                               "enableOnDemandEmailToCase": True,
                               "routingAddresses": {
                                   "addressType": "EmailToCase",
                                   "routingName": "Support",
                                   "caseOrigin": "Email",
                                   "casePriority": "Medium",
                                   "emailAddress": "support@acme.com"}}},
            active_users=[ADMIN, AUTH])
        src = (Input().with_default_toggles()
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            summary = run_main(apply_mod, [
                "--target-org", "x", "--input", path,
                "--routing-email", "support@acme.com",
            ])
        self.assertEqual(summary["phaseB"][0]["status"], "already_exists")
        self.assertEqual(summary["verified"]["routingAddressCount"], 1)


class MultiAddressOrderingPreservation(unittest.TestCase):
    """Verifies multi-address ordering preserves existing addresses. The
    wholesale routingAddresses replace drops an existing, already-provisioned
    address if a brand-new address follows it in the payload, so Phase B emits
    new addresses BEFORE existing ones. The platform-managed read-only fields
    (emailServicesAddress/isVerified) are not the deciding factor: preservation
    depends on order, not those fields.

    Covers:
      * a single append preserves the existing address, and a VERIFIED existing
        address stays verified;
      * the emitted payload actually orders new addresses before existing ones
        (asserting the mechanism, not just the outcome);
      * a multi-address append (two new at once) preserves everything;
      * if the platform drops an address anyway (fault-injected), the runtime
        preservation guard fails LOUDLY rather than reporting a bogus success.
    """

    def _org_with_provisioned_address(self, verified=True,
                                      drop_one_existing_on_write=False):
        return FakeOrg(
            case_settings={"fullName": "Case",
                           "defaultCaseOwner": ADMIN,
                           "defaultCaseOwnerType": "User",
                           "defaultCaseUser": ADMIN,
                           "emailToCase": {
                               "enableEmailToCase": True,
                               "enableOnDemandEmailToCase": True,
                               "routingAddresses": {
                                   "addressType": "EmailToCase",
                                   "routingName": "Support Inbox",
                                   "caseOrigin": "Email",
                                   "casePriority": "Medium",
                                   "emailAddress": "alias1@acme.com",
                                   "emailServicesAddress":
                                       "alias1@svc.example.com",
                                   "isVerified": verified}}},
            active_users=[ADMIN, AUTH],
            drop_one_existing_on_write=drop_one_existing_on_write)

    def _append(self, org, addrs_and_emails):
        builder = Input().with_default_toggles()
        emails = []
        for routing_name, email in addrs_and_emails:
            builder.address(addressType="EmailToCase", routingName=routing_name,
                            caseOrigin="Email", casePriority="Medium")
            emails.append(email)
        src = builder.build()
        args = ["--target-org", "x"]
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            args += ["--input", path]
            for email in emails:
                args += ["--routing-email", email]
            return run_main(apply_mod, args)

    def _addr_list(self, org):
        addrs = org.state["emailToCase"]["routingAddresses"]
        return addrs if isinstance(addrs, list) else [addrs]

    def test_append_preserves_verified_existing(self):
        org = self._org_with_provisioned_address(verified=True)
        summary = self._append(org, [("Billing Inbox", "alias2@acme.com")])
        self.assertEqual(summary["verified"]["routingAddressCount"], 2)
        by_name = {a["routingName"]: a for a in self._addr_list(org)}
        self.assertEqual(set(by_name), {"Support Inbox", "Billing Inbox"})
        # the existing address survived AND kept its verified state
        self.assertTrue(by_name["Support Inbox"]["isVerified"])

    def test_payload_orders_new_before_existing(self):
        # Assert the actual fix mechanism: the emitted routingAddresses payload
        # lists the new address ahead of the carried-over existing one.
        org = self._org_with_provisioned_address()
        self._append(org, [("Billing Inbox", "alias2@acme.com")])
        e2c = last_e2c_write(org)
        addrs = e2c["routingAddresses"]
        self.assertIsInstance(addrs, list)
        names = [a["routingName"] for a in addrs]
        self.assertEqual(names.index("Billing Inbox"),
                         min(range(len(names))),
                         "new address must be emitted before the existing one")
        self.assertLess(names.index("Billing Inbox"),
                        names.index("Support Inbox"))

    def test_multi_add_preserves_all(self):
        org = self._org_with_provisioned_address(verified=True)
        summary = self._append(org, [("Inbox A", "a@acme.com"),
                                      ("Inbox B", "b@acme.com")])
        self.assertEqual(summary["verified"]["routingAddressCount"], 3)
        by_name = {a["routingName"]: a for a in self._addr_list(org)}
        self.assertEqual(set(by_name),
                         {"Support Inbox", "Inbox A", "Inbox B"})
        self.assertTrue(by_name["Support Inbox"]["isVerified"])

    def test_guard_fires_on_platform_drop(self):
        # Fault injection: the org drops an existing address despite correct
        # ordering. The runtime preservation guard must fail loudly.
        org = self._org_with_provisioned_address(
            drop_one_existing_on_write=True)
        with self.assertRaises(SystemExit):
            self._append(org, [("Billing Inbox", "alias2@acme.com")])


class Scenario6_SupportSettingsTypes(unittest.TestCase):
    """Owner + automated-user resolution across User, Queue, and System."""

    def _run(self, org, extra):
        src = Input().with_default_toggles().build()
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            return run_main(apply_mod,
                            ["--target-org", "x", "--input", path, *extra])

    def test_user_owner_and_user_automated(self):
        org = fresh_org(active_users=[ADMIN, AUTH])
        self._run(org, ["--owner-type", "User", "--owner-value", ADMIN,
                        "--automated-type", "User", "--automated-value", ADMIN])
        self.assertEqual(org.state["defaultCaseOwnerType"], "User")
        self.assertEqual(org.state["defaultCaseUser"], ADMIN)

    def test_queue_owner(self):
        org = fresh_org(active_users=[ADMIN, AUTH], queues=["Support_Queue"])
        self._run(org, ["--owner-type", "Queue", "--owner-value", "Support_Queue",
                        "--automated-type", "User", "--automated-value", ADMIN])
        self.assertEqual(org.state["defaultCaseOwnerType"], "Queue")
        self.assertEqual(org.state["defaultCaseOwner"], "Support_Queue")

    def test_system_automated_user(self):
        org = fresh_org(active_users=[ADMIN, AUTH], queues=["Support_Queue"])
        self._run(org, ["--owner-type", "Queue", "--owner-value", "Support_Queue",
                        "--automated-type", "System",
                        "--system-user-email", "ops@acme.com"])
        self.assertTrue(org.state["useSystemUserAsDefaultCaseUser"])
        # System and named defaultCaseUser are mutually exclusive
        self.assertNotIn("defaultCaseUser", org.state)

    def test_invalid_owner_fails_closed(self):
        org = fresh_org(active_users=[AUTH])  # ADMIN is NOT active
        with self.assertRaises(SystemExit):
            self._run(org, ["--owner-type", "User", "--owner-value", ADMIN,
                            "--automated-type", "User",
                            "--automated-value", ADMIN])


class Scenario7_PerAddressCaseOwner(unittest.TestCase):
    """Per-address caseOwner: absent (default), User type, Queue type, and
    fail-closed on an owner that doesn't exist."""

    def _apply(self, org, addr_kw, email="a@acme.com"):
        org.state.update({"defaultCaseOwner": ADMIN,
                          "defaultCaseOwnerType": "User",
                          "defaultCaseUser": ADMIN})
        src = (Input().with_default_toggles()
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium",
                        **addr_kw).build())
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            return run_main(apply_mod, ["--target-org", "x", "--input", path,
                                        "--routing-email", email])

    def test_no_case_owner(self):
        org = fresh_org(active_users=[ADMIN, AUTH])
        self._apply(org, {})
        addr = org.state["emailToCase"]["routingAddresses"]
        addr = addr[0] if isinstance(addr, list) else addr
        self.assertNotIn("caseOwner", addr)

    def test_user_case_owner(self):
        org = fresh_org(active_users=[ADMIN, AUTH])
        self._apply(org, {"caseOwner": ADMIN, "caseOwnerType": "User"})
        addr = org.state["emailToCase"]["routingAddresses"]
        addr = addr[0] if isinstance(addr, list) else addr
        self.assertEqual(addr["caseOwner"], ADMIN)
        self.assertEqual(addr["caseOwnerType"], "User")

    def test_queue_case_owner(self):
        org = fresh_org(active_users=[ADMIN, AUTH], queues=["Billing_Queue"])
        self._apply(org, {"caseOwner": "Billing_Queue", "caseOwnerType": "Queue"})
        addr = org.state["emailToCase"]["routingAddresses"]
        addr = addr[0] if isinstance(addr, list) else addr
        self.assertEqual(addr["caseOwner"], "Billing_Queue")
        self.assertEqual(addr["caseOwnerType"], "Queue")

    def test_nonexistent_case_owner_fails_closed(self):
        org = fresh_org(active_users=[ADMIN, AUTH])  # no such queue
        with self.assertRaises(SystemExit):
            self._apply(org, {"caseOwner": "Ghost_Queue", "caseOwnerType": "Queue"})


class OptionalToggleBehavior(unittest.TestCase):
    """Optional toggles are written when present; opted-out toggles are NOT
    written and the org keeps its current value."""

    def test_optional_toggles_written_when_present(self):
        org = fresh_org(active_users=[ADMIN, AUTH])
        org.state.update({"defaultCaseOwner": ADMIN,
                          "defaultCaseOwnerType": "User",
                          "defaultCaseUser": ADMIN})
        src = (Input().with_default_toggles()
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            summary = run_main(apply_mod, [
                "--target-org", "x", "--input", path,
                "--routing-email", "support@acme.com"])
        e2c = org.state["emailToCase"]
        for t in DEFAULT_E2C_TOGGLES:
            self.assertTrue(e2c[t], f"{t} should be enabled")
        self.assertTrue(org.state["enableDraftEmails"])
        for t in DEFAULT_E2C_TOGGLES:
            self.assertEqual(summary["verified"][f"emailToCase.{t}"], True)

    def test_opted_out_toggle_is_not_enabled(self):
        # User opted OUT of showWordCountInComposer and enableDraftEmails: they
        # are absent from the source file. The provisioning-safe mechanism does
        # a read-modify-write of the whole emailToCase block, so an opted-out
        # field DOES ride along on the wire at its CURRENT org value (echoing an
        # unchanged value is a field-level-merge no-op). The real opt-out
        # guarantee is therefore behavioral:
        #   (a) the skill does not report it in phaseA as a field it SET, and
        #   (b) the org value is unchanged — opt-out never turns it ON.
        org = fresh_org(active_users=[ADMIN, AUTH])
        org.state.update({"defaultCaseOwner": ADMIN,
                          "defaultCaseOwnerType": "User",
                          "defaultCaseUser": ADMIN})
        # org currently has these OFF; opting out must leave them OFF (not on).
        org.state["emailToCase"]["showWordCountInComposer"] = False
        org.state["enableDraftEmails"] = False
        src = (Input()
               .e2c(enableHtmlEmail="true", notifyOwnerOnNewCaseEmail="true",
                    enableE2CDeduplicateAttachments="true")  # NO showWordCount
               .address(addressType="EmailToCase", routingName="Support",
                        caseOrigin="Email", casePriority="Medium").build())
        with tempfile.TemporaryDirectory() as d, org.patch(apply_mod):
            path = write_input(d, src)
            summary = run_main(apply_mod, ["--target-org", "x", "--input", path,
                                           "--routing-email", "support@acme.com"])
        # (a) the skill did not claim to set the opted-out fields
        self.assertNotIn("emailToCase.showWordCountInComposer",
                         summary["phaseA"])
        self.assertNotIn("enableDraftEmails", summary["phaseA"])
        # (b) org values unchanged (still off) — opt-out did NOT enable them
        self.assertFalse(org.state["emailToCase"]["showWordCountInComposer"])
        self.assertFalse(org.state["enableDraftEmails"])
        # the ones the user DID keep are on
        self.assertTrue(org.state["emailToCase"]["enableHtmlEmail"])


if __name__ == "__main__":
    unittest.main()
