"""In-memory fake Salesforce org for driving apply-casesettings.py end to end
without a live org.

The script itself does no I/O: the agent dispatches the requests it prints. This
fake plays the platform side of those `dispatch` / `dispatch_readonly` calls
(``FakeOrg.dispatch``), answering with the same `{status_code, body}` envelopes
the MCP tools return, so the whole agent flow (see ``_agent.py``) runs against it.

``FakeOrg`` holds a CaseSettings state as a nested dict and applies the PUT with
the SAME merge semantics as the platform:
  * top-level scalar fields merge at the field level (an omitted field keeps its
    current value);
  * inside ``emailToCase``, scalar children merge at the field level;
  * the ``routingAddresses`` collection is REPLACED wholesale - but ONLY when the
    payload's ``emailToCase`` actually contains routingAddresses. A payload whose
    ``emailToCase`` omits routingAddresses (e.g. Phase A) leaves existing
    addresses untouched.
  * ORDERING drives multi-address preservation. An address already provisioned
    in the org (matched by routingName/emailAddress) is DROPPED from the replaced
    collection if any brand-new address appears AFTER it in document order; new
    addresses always survive. Placing new addresses BEFORE existing ones (what
    the skill's Phase B does) preserves everything. Surviving existing addresses
    keep their minted read-only fields (so a verified address stays verified).

The ``drop_one_existing_on_write`` flag injects a fault: the org drops one
existing address on any multi-address write regardless of order, to exercise the
skill's preservation guard independent of the ordering model above.

Reads reflect current state. Active users / queues are configured per test.
"""
from __future__ import annotations

import copy
import json
import re
import xml.etree.ElementTree as ET

META_NS = "http://soap.sforce.com/2006/04/metadata"


def _q(name: str) -> str:
    return f"{{{META_NS}}}{name}"


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _in_list(soql: str, field: str):
    """Values of ``<field> IN ('a', 'b')`` in a SOQL string."""
    m = re.search(rf"{field} IN \(([^)]*)\)", soql)
    return re.findall(r"'((?:[^'\\]|\\.)*)'", m.group(1)) if m else []


class FakeOrg:
    """Models a single org's CaseSettings for apply-casesettings.py tests."""

    def __init__(self, case_settings=None, active_users=None, queues=None,
                 is_sandbox=True, org_type="Developer Edition", is_trial=False,
                 org_api_version="67.0", cases=None, email_messages=None,
                 drop_one_existing_on_write=False):
        # Current CaseSettings state (nested dict; scalars are python str/bool).
        self.state = copy.deepcopy(case_settings) if case_settings else {}
        self.active_users = list(active_users or [])
        # Queue DeveloperNames (and Names) that resolve.
        self.queues = set(queues or [])
        # Every PUT payload sent, as nested dicts, for asserting exactly what was
        # written (e.g. stripped/kept fields).
        self.writes: list[dict] = []
        # Every request the agent dispatched, as (tool, method, path).
        self.calls: list[tuple] = []
        # Organization row for the production gate. is_sandbox=None models an
        # unreadable Organization row (no record comes back).
        self.is_sandbox = is_sandbox
        self.org_type = org_type
        self.is_trial = is_trial
        # Newest version the fake `GET /services/data` lists.
        self.org_api_version = org_api_version
        # Rows returned by the Act-3 verify-cases queries.
        self.cases = list(cases or [])
        self.email_messages = list(email_messages or [])
        self.drop_one_existing_on_write = drop_one_existing_on_write

    # -- dispatch ---------------------------------------------------------

    def dispatch(self, req: dict) -> dict:
        """Answer one request the script printed, as the MCP tool would."""
        tool, method, path = req["tool"], req["method"], req["path"]
        self.calls.append((tool, method, path))
        # dispatch_readonly is GET-only; anything state-changing must use dispatch.
        assert (tool == "dispatch_readonly") == (method == "GET"), req
        assert re.fullmatch(r"/services/data/(v\d+\.\d+/)?(headless/metadata|query)",
                            path), path
        if path.endswith("/headless/metadata"):
            if method == "GET":
                assert req["query_params"] == {"type": "CaseSettings",
                                               "fullName": "Case"}
                return self._ok({"type": "CaseSettings", "fullName": "Case",
                                 "xmlRep": self._state_xml()})
            assert method == "PUT" and req["body"]["type"] == "CaseSettings"
            return self._apply_update(req["body"]["xmlRep"])
        return self._query(req["query_params"]["q"])

    @staticmethod
    def _ok(body):
        return {"status_code": 200, "body": body}

    def _query(self, soql: str) -> dict:
        if "FROM Organization" in soql:
            if self.is_sandbox is None:
                return self._ok({"totalSize": 0, "done": True, "records": []})
            return self._ok({"totalSize": 1, "done": True, "records": [{
                "IsSandbox": self.is_sandbox,
                "OrganizationType": self.org_type,
                "TrialExpirationDate":
                    "2030-01-01T00:00:00.000+0000" if self.is_trial else None}]})
        if "FROM User" in soql:
            wanted = {n.lower() for n in _in_list(soql, "Username")}
            recs = [{"Username": u} for u in self.active_users
                    if u.lower() in wanted]
            return self._ok({"totalSize": len(recs), "records": recs})
        if "FROM Group" in soql:
            wanted = set(_in_list(soql, "DeveloperName")) | set(
                _in_list(soql, "Name"))
            recs = [{"DeveloperName": q, "Name": q} for q in sorted(self.queues)
                    if q in wanted]
            return self._ok({"totalSize": len(recs), "records": recs})
        if "FROM Case" in soql:
            rows = self.cases
            m = re.search(r"SuppliedEmail = '([^']*)'", soql)
            if m:
                rows = [c for c in rows if c.get("SuppliedEmail") == m.group(1)]
            return self._ok({"totalSize": len(rows), "records": list(rows)})
        if "FROM EmailMessage" in soql:
            ids = set(_in_list(soql, "ParentId"))
            recs = [m for m in self.email_messages
                    if m.get("Incoming") and m.get("ParentId") in ids]
            return self._ok({"totalSize": len(recs), "records": recs})
        raise AssertionError(f"unexpected query: {soql}")

    def _state_xml(self) -> str:
        root = ET.Element(_q("CaseSettings"))
        self._dict_to_xml(root, self.state)
        ET.register_namespace("", META_NS)
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                + ET.tostring(root, encoding="unicode") + "\n")

    def _apply_update(self, xml_rep: str) -> dict:
        """Parse the payload, record it, merge it into state, return success."""
        payload = self._xml_to_dict(ET.fromstring(xml_rep))
        rejected = self._reject_outlook(payload)
        if rejected:
            return {"status_code": 400, "body": {"results": [{
                "success": False, "fullName": "Case", "errors": [
                    {"statusCode": "INVALID_FIELD", "message": rejected}]}]}}
        self.writes.append(copy.deepcopy(payload))
        self._merge(payload)
        return self._ok({"results": [{"success": True, "fullName": "Case",
                                      "errors": []}]})

    @staticmethod
    def _reject_outlook(payload):
        addrs = (payload.get("emailToCase") or {}).get("routingAddresses") or []
        for a in [addrs] if isinstance(addrs, dict) else addrs:
            if a.get("addressType") != "Outlook":
                continue
            label = f"EmailToCaseRoutingAddress[{a.get('routingName')}]"
            if a.get("emailAddress"):
                return f"{label}: emailAddress is not available for an Outlook routing address"
            if not a.get("caseOwner"):
                return f"{label}: Missing caseOwner"
        return None

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

    def patch(self, apply_mod=None):
        """Context manager making ``run_main`` drive the agent flow against this
        org. ``apply_mod`` is accepted for call-site symmetry with the old seam
        patching; the script itself has no seams left to patch."""
        from . import _agent
        return _agent.Active(self)


def last_e2c_write(org: FakeOrg) -> dict:
    """The emailToCase block of the most recent PUT payload."""
    for w in reversed(org.writes):
        if "emailToCase" in w:
            return w["emailToCase"]
    raise AssertionError("no updateMetadata write carried an emailToCase block")


def top_level_keys_written(org: FakeOrg) -> set:
    """Union of all top-level keys across every PUT payload."""
    keys: set = set()
    for w in org.writes:
        keys |= set(w.keys())
    return keys
