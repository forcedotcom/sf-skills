"""In-memory fake Salesforce org for driving apply-casesettings.py end to end
without a live org.

The skill script funnels ALL network I/O through three seams:
  * ``post_soap(url, envelope, soap_action)`` — readMetadata / updateMetadata
  * ``query_active_user(session_id, instance_url, username)``
  * ``query_queue(session_id, instance_url, name)``
plus ``get_session`` for the CLI handshake. Patching those four lets the whole
``main()`` flow run against this fake.

``FakeOrg`` holds a CaseSettings state as a nested dict and applies
``updateMetadata`` with the SAME merge semantics as the platform:
  * top-level scalar fields merge at the field level (an omitted field keeps its
    current value);
  * inside ``emailToCase``, scalar children merge at the field level;
  * the ``routingAddresses`` collection is REPLACED wholesale — but ONLY when the
    payload's ``emailToCase`` actually contains routingAddresses. A payload whose
    ``emailToCase`` omits routingAddresses (e.g. Phase A) leaves existing
    addresses untouched.
  * ORDERING drives multi-address preservation. An address already provisioned
    in the org (matched by routingName/emailAddress) is DROPPED from the replaced
    collection if any brand-new address appears AFTER it in document order; new
    addresses always survive. Placing new addresses BEFORE existing ones (what
    the skill's Phase B does) preserves everything. This was proven live: the
    platform-managed read-only fields (emailServicesAddress/isVerified) are NOT
    the cause — existing addresses dropped with those fields stripped and
    survived with them kept; only order mattered. Surviving existing addresses
    keep their minted read-only fields (so a verified address stays verified).

The ``drop_one_existing_on_write`` flag injects a fault: the org drops one
existing address on any multi-address write regardless of order, to exercise the
skill's preservation guard (its runtime safety net) independent of the ordering
model above.

Reads reflect current state. Active users / queues are configured per test.
"""
from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from unittest import mock

META_NS = "http://soap.sforce.com/2006/04/metadata"


def _q(name: str) -> str:
    return f"{{{META_NS}}}{name}"


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


class FakeOrg:
    """Models a single org's CaseSettings for apply-casesettings.py tests."""

    def __init__(self, case_settings=None, active_users=None, queues=None,
                 is_sandbox=True, org_type="Developer Edition", is_trial=False,
                 org_api_version="67.0", cases=None, email_messages=None,
                 drop_one_existing_on_write=False):
        # Current CaseSettings state (nested dict; scalars are python str/bool).
        self.state = copy.deepcopy(case_settings) if case_settings else {}
        # Active usernames (exact match, case-insensitive handled below).
        self.active_users = {u.lower() for u in (active_users or [])}
        # Queue DeveloperNames (and Names) that resolve.
        self.queues = set(queues or [])
        # Record of every updateMetadata payload sent, as nested dicts, for
        # asserting exactly what was written (e.g. stripped/kept fields).
        self.writes: list[dict] = []
        self.instance_url = "https://fake.my.salesforce.com"
        self.auth_username = "authuser@fake.example.com"
        # Organization row for the production-gate. is_sandbox=None models an
        # unreadable Organization row (gate treats it as production).
        self.is_sandbox = is_sandbox
        self.org_type = org_type
        self.is_trial = is_trial
        # apiVersion the fake `sf org display` reports (for version derivation).
        self.org_api_version = org_api_version
        # Rows returned by the Act-3 verify-cases queries.
        self.cases = list(cases or [])
        self.email_messages = list(email_messages or [])
        # Fault injection: when True, any multi-address write drops one existing
        # address regardless of ordering, to exercise the skill's preservation
        # guard independently of the (correctly-ordered) happy path.
        self.drop_one_existing_on_write = drop_one_existing_on_write

    # -- session / lookups -------------------------------------------------

    def fake_get_session(self, target_org):
        # Mirror the real get_session's version derivation (floor 67.0) so the
        # metadata URL matches what a live run would produce. get_session is
        # patched wholesale in tests, so resolve_api_version is unit-tested
        # directly; this keeps the fake's URL faithful.
        version = self.org_api_version
        try:
            major = int(str(version).split(".")[0])
            if major < 67:
                version = "67.0"
        except (ValueError, IndexError):
            version = "67.0"
        return ("SESSIONID", f"{self.instance_url}/services/Soap/m/{version}",
                self.instance_url, self.auth_username)

    def fake_query_active_user(self, session_id, instance_url, username):
        if username and username.lower() in self.active_users:
            return username
        return None

    def fake_query_queue(self, session_id, instance_url, name):
        return name if name in self.queues else None

    def fake_query_org_info(self, session_id, instance_url):
        return self.is_sandbox, self.org_type, self.is_trial

    def fake_query_email_cases(self, session_id, instance_url,
                               supplied_email=None):
        rows = self.cases
        if supplied_email is not None:
            rows = [c for c in rows if c.get("SuppliedEmail") == supplied_email]
        return list(rows)

    def fake_query_incoming_email_messages(self, session_id, instance_url,
                                           case_ids):
        ids = set(case_ids)
        return [m for m in self.email_messages
                if m.get("Incoming") and m.get("ParentId") in ids]

    # -- SOAP -------------------------------------------------------------

    def fake_post_soap(self, url, envelope, soap_action):
        if soap_action == "readMetadata":
            return self._read_response()
        if soap_action == "updateMetadata":
            return self._apply_update(envelope)
        raise AssertionError(f"unexpected SOAPAction {soap_action!r}")

    def _read_response(self):
        """Build a SOAP-ish response whose .//records mirrors current state."""
        env = ET.Element(_q("Envelope"))
        body = ET.SubElement(env, _q("Body"))
        resp = ET.SubElement(body, _q("readMetadataResponse"))
        result = ET.SubElement(resp, _q("result"))
        records = ET.SubElement(result, _q("records"))
        self._dict_to_xml(records, self.state)
        return env

    def _apply_update(self, envelope):
        """Parse the payload, record it, merge it into state, return success."""
        root = ET.fromstring(envelope)
        # find the <metadata> element under updateMetadata
        metadata = None
        for el in root.iter():
            if _local(el.tag) == "metadata":
                metadata = el
                break
        assert metadata is not None, "updateMetadata payload missing <metadata>"
        payload = self._xml_to_dict(metadata)
        self.writes.append(copy.deepcopy(payload))
        self._merge(payload)
        return self._success_response()

    def _merge(self, payload):
        for key, val in payload.items():
            if key == "fullName":
                continue
            if key == "emailToCase" and isinstance(val, dict):
                self._merge_e2c(val)
            else:
                # top-level scalar / block: field-level overwrite
                self.state[key] = val

    # Platform-managed read-only fields the org mints on a provisioned address.
    _READONLY_ADDRESS_FIELDS = ("emailServicesAddress", "isVerified")

    def _addr_key(self, addr):
        """Identity used to match a payload address against a provisioned one."""
        return addr.get("routingName") or addr.get("emailAddress")

    def _existing_address_keys(self):
        cur = self.state.get("emailToCase") or {}
        addrs = cur.get("routingAddresses")
        if addrs is None:
            return set()
        if isinstance(addrs, dict):
            addrs = [addrs]
        return {self._addr_key(a) for a in addrs}

    def _merge_e2c(self, payload_e2c):
        cur = self.state.setdefault("emailToCase", {})
        for key, val in payload_e2c.items():
            if key == "routingAddresses":
                cur["routingAddresses"] = self._resolve_addresses(val)
            else:
                cur[key] = val

    def _resolve_addresses(self, val):
        """Model the platform's wholesale routingAddresses REPLACE.

        The collection is replaced by the payload, but with the live-verified
        ORDERING behavior: an address already provisioned in the org is DROPPED
        if any brand-new address appears AFTER it in document order. New
        addresses always survive. Surviving existing addresses keep the
        platform-minted read-only fields they were provisioned with (so a
        verified address stays verified); brand-new addresses get freshly minted
        fields (unverified). Read-only fields declared in the payload are
        ignored for survival — only order matters."""
        items = [dict(a) for a in (val if isinstance(val, list) else [val])]
        existing_keys = self._existing_address_keys()
        prior = {self._addr_key(a): a
                 for a in self._existing_address_list()}

        # Fault injection: drop one existing address regardless of order.
        if self.drop_one_existing_on_write:
            for i, addr in enumerate(items):
                if self._addr_key(addr) in existing_keys:
                    items.pop(i)
                    break

        survivors = []
        for i, addr in enumerate(items):
            key = self._addr_key(addr)
            is_existing = key in existing_keys
            if is_existing:
                # Dropped if any brand-new address follows this one.
                if any(self._addr_key(later) not in existing_keys
                       for later in items[i + 1:]):
                    continue
                # Survives: carry forward its previously-minted read-only fields.
                minted = dict(addr)
                for f in self._READONLY_ADDRESS_FIELDS:
                    if f in prior.get(key, {}):
                        minted[f] = prior[key][f]
                survivors.append(minted)
            else:
                # Brand-new address: platform mints fresh read-only fields.
                minted = {k: v for k, v in addr.items()
                          if k not in self._READONLY_ADDRESS_FIELDS}
                email = minted.get("emailAddress", "addr")
                minted["emailServicesAddress"] = f"{email}.svc.example.com"
                minted["isVerified"] = False
                survivors.append(minted)
        return survivors if len(survivors) != 1 else survivors[0]

    def _existing_address_list(self):
        cur = self.state.get("emailToCase") or {}
        addrs = cur.get("routingAddresses")
        if addrs is None:
            return []
        return [addrs] if isinstance(addrs, dict) else list(addrs)

    @staticmethod
    def _success_response():
        env = ET.Element(_q("Envelope"))
        body = ET.SubElement(env, _q("Body"))
        resp = ET.SubElement(body, _q("updateMetadataResponse"))
        result = ET.SubElement(resp, _q("result"))
        ET.SubElement(result, _q("success")).text = "true"
        ET.SubElement(result, _q("fullName")).text = "Case"
        return env

    # -- dict <-> xml -----------------------------------------------------

    def _dict_to_xml(self, parent, value):
        for key, val in value.items():
            if isinstance(val, list):
                for item in val:
                    child = ET.SubElement(parent, _q(key))
                    self._dict_to_xml(child, item)
            elif isinstance(val, dict):
                child = ET.SubElement(parent, _q(key))
                self._dict_to_xml(child, val)
            else:
                child = ET.SubElement(parent, _q(key))
                child.text = self._scalar_text(val)

    @staticmethod
    def _scalar_text(val):
        if val is True:
            return "true"
        if val is False:
            return "false"
        return str(val)

    def _xml_to_dict(self, elem):
        children = list(elem)
        if not children:
            text = (elem.text or "").strip()
            if text.lower() == "true":
                return True
            if text.lower() == "false":
                return False
            return text
        result: dict = {}
        for child in children:
            tag = _local(child.tag)
            sub = self._xml_to_dict(child)
            if tag in result:
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(sub)
            else:
                result[tag] = sub
        return result

    # -- patching ---------------------------------------------------------

    def patch(self, apply_mod):
        """Return a context manager patching the four seams on apply_mod."""
        return _Patches(self, apply_mod)


class _Patches:
    def __init__(self, org: FakeOrg, apply_mod):
        self.org = org
        self.mod = apply_mod
        self._patchers = []

    def __enter__(self):
        # get_session has a documented side-effect: unless --api-version was
        # given, it sets the module's API_VERSION global to the org-derived,
        # floored version. The real function is mocked here, so mirror that
        # side-effect on the patched module using its own resolve_api_version.
        mod = self.mod
        org = self.org

        def fake_get_session(target_org):
            if not getattr(mod, "_API_VERSION_EXPLICIT", False):
                mod.API_VERSION = mod.resolve_api_version(org.org_api_version)
            return org.fake_get_session(target_org)

        seams = {
            "get_session": fake_get_session,
            "post_soap": self.org.fake_post_soap,
            "query_active_user": self.org.fake_query_active_user,
            "query_queue": self.org.fake_query_queue,
            "query_org_info": self.org.fake_query_org_info,
            "query_email_cases": self.org.fake_query_email_cases,
            "query_incoming_email_messages":
                self.org.fake_query_incoming_email_messages,
        }
        for name, fn in seams.items():
            p = mock.patch.object(self.mod, name, side_effect=fn)
            p.start()
            self._patchers.append(p)
        return self

    def __exit__(self, *exc):
        for p in self._patchers:
            p.stop()
        return False


def last_e2c_write(org: FakeOrg) -> dict:
    """The emailToCase block of the most recent updateMetadata payload."""
    for w in reversed(org.writes):
        if "emailToCase" in w:
            return w["emailToCase"]
    raise AssertionError("no updateMetadata write carried an emailToCase block")


def top_level_keys_written(org: FakeOrg) -> set:
    """Union of all top-level keys across every updateMetadata payload."""
    keys: set = set()
    for w in org.writes:
        keys |= set(w.keys())
    return keys
