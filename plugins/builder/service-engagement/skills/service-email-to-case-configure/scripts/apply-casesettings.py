#!/usr/bin/env python3
"""Payload builder / response validator for configuring Email-to-Case through the
Metadata CRUD route (`/headless/metadata`, type CaseSettings) in two phases.

This script makes NO network calls and holds no credentials. The agent performs
every org call with the project-codey `dispatch_readonly` / `dispatch` tools; this
script prints the exact request to make (`requests`), validates what came back, and
builds the next write. Each subcommand reads dispatch responses from files (the
`{status_code, body}` envelope the tools return, or a bare body) and prints JSON to
stdout. Any refusal or invalid input exits non-zero with the reason on stderr.

Why two phases and not one write: enabling On-Demand Email-to-Case provisions the
org's internal email-service infrastructure, and a routing address can only bind
to it in a SUBSEQUENT operation. A single write that both enables On-Demand and
declares a routing address fails on a freshly-configured org ("We couldn't save
your routing address...").

  Phase A - prerequisites + toggles (Support Settings owner / automated case
            user, enableEmailToCase, enableOnDemandEmailToCase, plus any other
            emailToCase flags EXCEPT routingAddresses).
  Phase B - routing addresses, one write after the toggles are live.

Each write sends ONLY the top-level CaseSettings fields this skill owns (see
KEEP_TOP_LEVEL_FIELDS) plus the complete emailToCase block as read from the org;
all other top-level fields are stripped. The platform re-validates any top-level
field present in the payload even at an unchanged value, and some (e.g. Case Feed)
carry dependencies unrelated to Email-to-Case (Case Feed needs Chatter). Stripped
fields keep their current value via field-level merge, and provisioning is driven
by the emailToCase block, so no Chatter prerequisite is needed. The complete
emailToCase block matters: a minimal patch that only flips
enableOnDemandEmailToCase does not provision the email service.

Support Settings (Default Case Owner + Automated Case User) are never guessed:
  * Already configured in the org -> PRESERVED (omitted from the payload) unless
    --overwrite-support-settings is passed AND new input is supplied for that field.
    The platform returns these null when unset, so a null read means "not set".
  * Not configured -> the caller must supply values (the skill elicits them):
      - Default Case Owner: --owner-type {User|Queue} + --owner-value (an active
        Username, or a Queue DeveloperName).
      - Automated Case User: --automated-type {User|System}. User needs
        --automated-value; System needs no value (optionally --system-user-email).
    Values are checked against the lookup responses and fail closed.
  * Routing-address emails come only from --routing-email (one per address, in
    document order); the script refuses a count mismatch.

Subcommands (agent flow, in order):
  requests <kind>  [--api-version X.Y] ...            print the request to dispatch
  gate             --org F [--confirm-production]     production-org safety verdict
  read             --response F                       print current settings
  phase-a          --input F --current F ...          build the Phase A write
  phase-b          --input F --current F ...          build the Phase B write
  check-write      --response F                       validate a write response
  verify           --input F --initial F --after F    preservation guard + summary
  cases            --cases F --messages F             prove inbound mail made Cases
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET

META_NS = "http://soap.sforce.com/2006/04/metadata"


def _data_path(version, tail):
    """Dispatch path for `tail`. Without a version the server injects the org's
    own API version, so by default the skill rides whatever the org supports; an
    explicit --api-version pins it."""
    return f"/services/data/v{version}{tail}" if version else f"/services/data{tail}"

# Platform-managed read-only fields the org mints on a routing address. We never
# declare these on a write (defensive hygiene). NOTE: stripping them is not what
# preserves existing addresses on a multi-address write - document ordering is
# (new addresses before existing ones).
READONLY_ADDRESS_FIELDS = {"emailServicesAddress", "isVerified"}

# Top-level CaseSettings fields this skill is responsible for - the ONLY
# top-level children we send in a write payload. Every other top-level field the
# read returns is stripped before writing.
#
# Why strip everything else: the platform RE-VALIDATES any field present in the
# payload, even at an unchanged value. Several top-level Case fields carry
# dependencies unrelated to Email-to-Case - most notably Case Feed, whose
# re-validation requires Chatter and otherwise fails the whole call with "The
# setup requirements for Case Feed Items has to be enabled."
#
# Why this is safe: CaseSettings writes merge at the field level, so any omitted
# top-level field keeps its current org value untouched. Provisioning of the
# On-Demand email service is driven entirely by the full `emailToCase` block, NOT
# by any top-level field.
KEEP_TOP_LEVEL_FIELDS = {
    "fullName",
    "emailToCase",
    "enableDraftEmails",
    "defaultCaseOwner",
    "defaultCaseOwnerType",
    "defaultCaseUser",
    "useSystemUserAsDefaultCaseUser",
    "systemUserEmail",
}

# Top-level CaseSettings fields handled explicitly by the owner / automated-user
# resolution below (or in their own block, emailToCase). Any OTHER scalar
# top-level field in the input (e.g. enableDraftEmails, a Support-Settings
# toggle) is propagated verbatim in Phase A.
HANDLED_TOP_LEVEL = {"defaultCaseOwner", "defaultCaseOwnerType", "defaultCaseUser",
                     "useSystemUserAsDefaultCaseUser", "systemUserEmail",
                     "emailToCase"}

VALID_OWNER_TYPES = {"User", "Queue"}
VALID_AUTOMATED_TYPES = {"User", "System"}
# Support-Settings fields written/read for the owner + automated case user.
SUPPORT_SETTINGS_FIELDS = ("defaultCaseOwner", "defaultCaseOwnerType",
                           "defaultCaseUser", "useSystemUserAsDefaultCaseUser",
                           "systemUserEmail")


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def emit(obj):
    print(json.dumps(obj, indent=2, sort_keys=True))


def local_name(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag


def qn(name):
    return f"{{{META_NS}}}{name}"



# ---------------------------------------------------------------------------
# dispatch responses
# ---------------------------------------------------------------------------

def load_response(path):
    """Return (status_code, body) from a saved dispatch response. Accepts the
    `{status_code, body}` envelope the dispatch tools return, or a bare body
    (treated as status 200)."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Could not read dispatch response '{path}': {exc}")
    if isinstance(data, dict) and "status_code" in data and "body" in data:
        return data["status_code"], data["body"]
    return 200, data


def error_messages(status, body):
    """Collect the error text from any of the response shapes the route returns:
    a bare array of {errorCode, message} (unsupported operation), or a
    {results: [{errors: [{statusCode, message}]}]} object (rule violations and
    provisioning failures). Empty list means the response carried no error."""
    msgs = []
    if isinstance(body, list):
        for item in body:
            if isinstance(item, dict) and (item.get("message")
                                           or item.get("errorCode")):
                code = item.get("errorCode")
                text = item.get("message") or ""
                msgs.append(f"{code}: {text}" if code else text)
    elif isinstance(body, dict):
        for res in body.get("results") or []:
            for err in (res or {}).get("errors") or []:
                code = err.get("statusCode") or err.get("errorCode")
                text = err.get("message") or json.dumps(err)
                msgs.append(f"{code}: {text}" if code else text)
        if not msgs and body.get("message"):
            msgs.append(str(body["message"]))
    if not msgs and not (isinstance(status, int) and 200 <= status < 300):
        msgs.append(f"HTTP {status}: {json.dumps(body)[:500]}")
    return msgs


def parse_settings_response(path):
    """Return the CaseSettings root element from a read response, or fail with
    the route's error text."""
    status, body = load_response(path)
    msgs = error_messages(status, body)
    if msgs:
        fail("Reading CaseSettings failed: " + "; ".join(msgs))
    xml_rep = body.get("xmlRep") if isinstance(body, dict) else None
    if not xml_rep:
        fail("The read response carried no CaseSettings xmlRep.")
    try:
        return ET.fromstring(xml_rep)
    except ET.ParseError as exc:
        fail(f"The CaseSettings xmlRep could not be parsed: {exc}")


def parse_query_records(path, what):
    status, body = load_response(path)
    msgs = error_messages(status, body)
    if msgs:
        fail(f"{what} query failed: " + "; ".join(msgs))
    return (body.get("records") if isinstance(body, dict) else None) or []


# ---------------------------------------------------------------------------
# request builders (what the agent should dispatch)
# ---------------------------------------------------------------------------

def _escape_soql(value):
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def _soql_list(values):
    return ", ".join(f"'{_escape_soql(v)}'" for v in sorted(values))


def soql_request(version, soql, purpose):
    return {"purpose": purpose, "tool": "dispatch_readonly", "method": "GET",
            "path": _data_path(version, "/query"),
            "query_params": {"q": soql}}


def settings_read_request(version):
    return {"purpose": "read CaseSettings", "tool": "dispatch_readonly",
            "method": "GET", "path": _data_path(version, "/headless/metadata"),
            "query_params": {"type": "CaseSettings", "fullName": "Case"}}


def settings_write_request(version, records, purpose):
    """Build the PUT request for `records` (a CaseSettings element): strip the
    platform-managed address fields, keep only the fields this skill owns, and
    serialize as the route's {type, fullName, xmlRep} body."""
    strip_readonly_address_fields(records)
    root = ET.Element(qn("CaseSettings"))
    for child in list(records):
        if local_name(child.tag) in KEEP_TOP_LEVEL_FIELDS:
            root.append(child)
    ET.register_namespace("", META_NS)
    xml_rep = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               + ET.tostring(root, encoding="unicode") + "\n")
    return {"purpose": purpose, "tool": "dispatch", "method": "PUT",
            "path": _data_path(version, "/headless/metadata"),
            "body": {"type": "CaseSettings", "fullName": "Case",
                     "xmlRep": xml_rep}}


def org_request(version):
    return soql_request(
        version, "SELECT IsSandbox, OrganizationType, TrialExpirationDate "
                 "FROM Organization LIMIT 1", "production-org gate")


def cases_request(version, supplied_email=None):
    """Case rows created from inbound email (Origin = 'Email') in the last 3
    days, optionally narrowed to a SuppliedEmail. The 3-day window excludes stale
    pre-existing email Cases so a verify run can't false-pass on an old Case."""
    where = ["Origin = 'Email'"]
    if supplied_email:
        where.append(f"SuppliedEmail = '{_escape_soql(supplied_email)}'")
    # Fixed SOQL date-literal window (a constant, never operator input) - recent
    # enough to catch a test email sent over a weekend, tight enough to exclude
    # old Cases from a prior setup.
    where.append("CreatedDate >= LAST_N_DAYS:3")
    soql = ("SELECT Id, CaseNumber, Origin, SuppliedEmail, CreatedDate FROM Case "
            "WHERE " + " AND ".join(where) + " ORDER BY CreatedDate DESC LIMIT 50")
    return soql_request(version, soql, "inbound-email Cases")


def messages_request(version, case_ids):
    """Incoming EmailMessage rows whose ParentId is one of `case_ids` - proves the
    Case has its linked inbound email."""
    soql = ("SELECT Id, ParentId, Incoming FROM EmailMessage "
            f"WHERE Incoming = true AND ParentId IN ({_soql_list(case_ids)}) "
            "ORDER BY MessageDate DESC LIMIT 200")
    return soql_request(version, soql, "incoming EmailMessage rows")


# ---------------------------------------------------------------------------
# Org lookups (Users / Queues) validated from saved query responses
# ---------------------------------------------------------------------------

class Directory:
    """Active users and queues returned by the lookup queries. `users` / `queues`
    are None when the matching response was not supplied, so a missing lookup is
    reported as such instead of looking like 'not found'."""

    def __init__(self, users=None, queues=None):
        self.users = users
        self.queues = queues

    def active_user(self, username):
        """Exact Username of an active User matching `username`
        (case-insensitively), or None."""
        if not username:
            return None
        if self.users is None:
            fail(f"'{username}' must be checked against the org first: run "
                 f"`requests lookups`, dispatch the queries, and pass the result "
                 f"files with --users / --queues.")
        for name in self.users:
            if name.lower() == username.lower():
                return name
        return None

    def queue(self, name):
        """DeveloperName of a Queue matching `name` (DeveloperName is what
        CaseSettings.defaultCaseOwner stores; Name is accepted as a tolerant
        fallback), or None."""
        if not name:
            return None
        if self.queues is None:
            fail(f"Queue '{name}' must be checked against the org first: run "
                 f"`requests lookups`, dispatch the queries, and pass the result "
                 f"files with --users / --queues.")
        for dev_name, label in self.queues:
            if name == dev_name or name == label:
                return dev_name
        return None


def load_directory(args):
    users = queues = None
    if getattr(args, "users", None):
        users = [r["Username"] for r in parse_query_records(args.users, "User")]
    if getattr(args, "queues", None):
        queues = [(r.get("DeveloperName"), r.get("Name"))
                  for r in parse_query_records(args.queues, "Queue")]
    return Directory(users, queues)


def resolve_owner(directory, owner_value, owner_type):
    """Validate a user-supplied Default Case Owner against the org and return
    (resolved_value, resolved_type). Fails closed with an actionable message if
    the type is invalid or the value is not a real active user / queue."""
    if owner_type not in VALID_OWNER_TYPES:
        fail(f"defaultCaseOwnerType '{owner_type}' is not valid. It must be "
             f"'User' or 'Queue'. Ask the user for a valid type and value.")
    if not owner_value:
        fail(f"defaultCaseOwnerType is '{owner_type}' but no defaultCaseOwner "
             f"value was provided. Ask the user for the {owner_type} to use.")
    if owner_type == "User":
        resolved = directory.active_user(owner_value)
        if not resolved:
            fail(f"Default Case Owner '{owner_value}' is not an active User in "
                 f"this org. Ask the user for a valid username (or a Queue).")
        return resolved, "User"
    resolved = directory.queue(owner_value)
    if not resolved:
        fail(f"Default Case Owner '{owner_value}' is not a Queue in this org. "
             f"Ask the user for a valid queue DeveloperName (or a User).")
    return resolved, "Queue"


def _is_placeholder(value):
    """A value left as an unfilled template token, e.g. {CASE_OWNER_...}."""
    return (isinstance(value, str) and value.startswith("{")
            and value.endswith("}"))


def resolve_address_case_owner(directory, addr, label):
    """Validate the OPTIONAL per-address Default Case Owner on one routing
    address, in place. Rules (applied only when the user opted in to a
    per-address owner, i.e. caseOwner is present):
      * caseOwner must not be an unfilled placeholder.
      * caseOwnerType is required whenever caseOwner is set (platform rejects
        caseOwner without it) and must be 'User' or 'Queue'.
      * The value is validated against the org - an active Username for User, a
        real Queue DeveloperName for Queue - and fails closed if it does not
        exist, so the skill can re-prompt.
    When caseOwner is absent the address is left untouched (cases fall to the
    org Default Case Owner / assignment rules)."""
    case_owner = addr.get("caseOwner")
    case_owner_type = addr.get("caseOwnerType")
    if case_owner is None and case_owner_type is None:
        return  # no per-address owner requested
    if case_owner is None:
        fail(f"{label} sets caseOwnerType but no caseOwner value. Either supply "
             f"a caseOwner (a real active Username or Queue DeveloperName) or "
             f"remove caseOwnerType to use the org Default Case Owner.")
    if _is_placeholder(case_owner):
        fail(f"{label} caseOwner is still the placeholder '{case_owner}'. Ask "
             f"the user for a real active Username or Queue DeveloperName for "
             f"this address, or remove caseOwner to use the org Default Case "
             f"Owner.")
    if case_owner_type is None or _is_placeholder(case_owner_type):
        fail(f"{label} sets caseOwner but no valid caseOwnerType. caseOwnerType "
             f"('User' or 'Queue') is required whenever caseOwner is set. Ask "
             f"the user whether '{case_owner}' is a User or a Queue.")
    # resolve_owner validates the type and the value against the org, failing
    # closed with an actionable message; reuse it so per-address and top-level
    # owner validation are identical.
    resolved, resolved_type = resolve_owner(directory, case_owner,
                                            case_owner_type)
    addr["caseOwner"] = resolved
    addr["caseOwnerType"] = resolved_type


def resolve_automated_user(directory, automated_type, user_value, system_email):
    """Validate the user-supplied Automated Case User and return a dict of the
    CaseSettings fields to write. 'System' -> useSystemUserAsDefaultCaseUser
    (no defaultCaseUser). 'User' -> a validated defaultCaseUser username.
    Fails closed with an actionable message on any invalid input."""
    if automated_type not in VALID_AUTOMATED_TYPES:
        fail(f"Automated Case User type '{automated_type}' is not valid. It "
             f"must be 'User' or 'System'. Ask the user for a valid type.")
    if automated_type == "System":
        # System needs no user value; systemUserEmail is required only if the
        # org's automated case user does not exist yet - we pass it through
        # when provided and let the platform validate.
        fields = {"useSystemUserAsDefaultCaseUser": True}
        if system_email:
            fields["systemUserEmail"] = system_email
        return fields, "System"
    if not user_value:
        fail("Automated Case User type is 'User' but no defaultCaseUser value "
             "was provided. Ask the user for the username to use.")
    resolved = directory.active_user(user_value)
    if not resolved:
        fail(f"Automated Case User '{user_value}' is not an active User in "
             f"this org. Ask the user for a valid username (or use System).")
    return {"defaultCaseUser": resolved,
            "useSystemUserAsDefaultCaseUser": False}, "User"


# ---------------------------------------------------------------------------
# XML value helpers
# ---------------------------------------------------------------------------

def elem_to_value(elem):
    children = list(elem)
    if not children:
        text = (elem.text or "").strip()
        if text.lower() == "true":
            return True
        if text.lower() == "false":
            return False
        return text
    result = {}
    for child in children:
        tag = local_name(child.tag)
        val = elem_to_value(child)
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(val)
        else:
            result[tag] = val
    return result


def set_child_text(parent, tag, text):
    """Set (or create) a single child element's text on parent."""
    el = parent.find(qn(tag))
    if el is None:
        el = ET.SubElement(parent, qn(tag))
    el.text = str(text)
    return el


def _text(val):
    return "true" if val is True else ("false" if val is False else str(val))


def build_address_element(parent, addr_dict):
    """Append one <routingAddresses> element built from a dict."""
    ra = ET.SubElement(parent, qn("routingAddresses"))
    for key, val in addr_dict.items():
        if key in READONLY_ADDRESS_FIELDS:
            continue  # never write platform-managed fields
        child = ET.SubElement(ra, qn(key))
        child.text = _text(val)
    return ra


def strip_readonly_address_fields(records):
    """Remove platform-managed read-only fields (emailServicesAddress,
    isVerified) from EVERY routingAddresses element under emailToCase, in place.

    This is defensive hygiene, NOT the multi-address preservation mechanism: a
    write should never declare fields the org owns. Existing addresses were
    dropped with these fields stripped AND survived with them kept - the deciding
    factor is document ORDER (see phase-b: new addresses precede existing ones)."""
    e2c = records.find(qn("emailToCase"))
    if e2c is None:
        return
    for addr in e2c.findall(qn("routingAddresses")):
        for field in READONLY_ADDRESS_FIELDS:
            el = addr.find(qn(field))
            if el is not None:
                addr.remove(el)


def parse_input(path):
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        fail(f"Could not read input file '{path}': {exc}")
    root = tree.getroot()
    if local_name(root.tag) != "CaseSettings":
        fail(f"Input root must be CaseSettings, found '{local_name(root.tag)}'.")
    return elem_to_value(root)


def existing_address_keys(records_value):
    """Return (routingNames, emailAddresses) already present, to avoid duplicates."""
    addrs = _address_list(records_value)
    names = {a.get("routingName") for a in addrs if a.get("routingName")}
    emails = {a.get("emailAddress") for a in addrs if a.get("emailAddress")}
    return names, emails


def _address_list(value):
    addrs = (value.get("emailToCase") or {}).get("routingAddresses")
    if addrs is None:
        return []
    return [addrs] if isinstance(addrs, dict) else list(addrs)


def _count_addresses(value):
    return len(_address_list(value))


# Address types the platform rejects an emailAddress on ("emailAddress is not
# available for an Outlook routing address"). They also require a caseOwner.
NO_EMAIL_ADDRESS_TYPES = {"Outlook"}


def desired_addresses(desired, routing_emails):
    """The input's routing addresses with the user-supplied emails substituted
    positionally, skipping types that take no email. Fails closed on a count
    mismatch so no placeholder from the input file ever reaches the org."""
    addrs = (desired.get("emailToCase") or {}).get("routingAddresses")
    if addrs and isinstance(addrs, dict):
        addrs = [addrs]
    addrs = addrs or []
    for addr in addrs:
        if addr.get("addressType") in NO_EMAIL_ADDRESS_TYPES and not addr.get("caseOwner"):
            fail(f"{addr['addressType']} routing address "
                 f"'{addr.get('routingName')}' needs a caseOwner and "
                 f"caseOwnerType; the platform rejects it with 'Missing caseOwner'.")
    takes_email = [a for a in addrs
                   if a.get("addressType") not in NO_EMAIL_ADDRESS_TYPES]
    if takes_email and len(routing_emails) != len(takes_email):
        fail(f"--input declares {len(takes_email)} routing address(es) that take "
             f"an email (Outlook addresses take none) but {len(routing_emails)} "
             f"--routing-email value(s) were given. Provide exactly one "
             f"--routing-email per such address, in order.")
    if not takes_email and routing_emails:
        fail("--routing-email was given but no routing address takes an email.")
    for addr, email in zip(takes_email, routing_emails):
        addr["emailAddress"] = email
    return addrs


def split_addresses(addrs, existing_names, existing_emails):
    """Partition desired addresses into (new, already_existing) by routingName /
    emailAddress against what the org already has."""
    new, existing = [], []
    for addr in addrs:
        name, email = addr.get("routingName"), addr.get("emailAddress")
        if name in existing_names or (email and email in existing_emails):
            existing.append(addr)
        else:
            new.append(addr)
    return new, existing


# ---------------------------------------------------------------------------
# Support Settings
# ---------------------------------------------------------------------------

def support_settings_state(records_value):
    """Report whether Default Case Owner and Automated Case User are already
    configured in the org. The platform returns these fields null/absent when an
    admin has not set them, so null is a reliable "not configured" signal."""
    owner = records_value.get("defaultCaseOwner")
    owner_type = records_value.get("defaultCaseOwnerType")
    auto_user = records_value.get("defaultCaseUser")
    use_system = records_value.get("useSystemUserAsDefaultCaseUser")
    return {
        "ownerConfigured": bool(owner),
        "automatedUserConfigured": bool(auto_user) or use_system is True,
        "current": {
            "defaultCaseOwner": owner,
            "defaultCaseOwnerType": owner_type,
            "defaultCaseUser": auto_user,
            "useSystemUserAsDefaultCaseUser": use_system,
        },
    }


def _clear_automated_user_fields(records):
    """Remove any existing Automated Case User children (System and named-User
    are mutually exclusive at the platform layer, so we clear before writing)."""
    for f in ("defaultCaseUser", "useSystemUserAsDefaultCaseUser",
              "systemUserEmail"):
        existing = records.find(qn(f))
        if existing is not None:
            records.remove(existing)


def _strip_unwritten_support_fields(records, applied):
    """Remove any Support-Settings top-level field this run did NOT write, so it
    is omitted from the payload and preserved via field-level merge instead of
    resent verbatim.

    The five SUPPORT_SETTINGS_FIELDS are in KEEP_TOP_LEVEL_FIELDS so a field we DO
    set survives the strip. The side effect is that a field left as-read would
    otherwise be RESENT, forcing the platform to re-validate a value nobody asked
    to touch - and a platform-derived `systemUserEmail` resent this way can
    collide with the routing address ("Enter an email address for the system user
    that's not an Email-to-Case routing email address").

    Scope: touches ONLY the five SUPPORT_SETTINGS_FIELDS; `emailToCase` and its
    `routingAddresses` are unaffected."""
    for field in SUPPORT_SETTINGS_FIELDS:
        if field in applied:
            continue
        el = records.find(qn(field))
        if el is not None:
            records.remove(el)


def support_plan(args, desired, state):
    """Decide, per field, whether Phase A writes Default Case Owner / Automated
    Case User. Returns (write_owner, write_automated).

    The two fields are INDEPENDENT - an org can have one configured and the other
    not. A field is written when it is unset (input then required, fails closed),
    or when the caller opted to overwrite AND supplied input for THAT field. The
    overwrite flag is scoped per field: overwriting one configured field never
    forces a rewrite of the other."""
    owner_input = bool(
        args.owner_type or args.owner_value
        or desired.get("defaultCaseOwner") or desired.get("defaultCaseOwnerType"))
    automated_input = bool(
        args.automated_type or args.automated_value or args.system_user_email
        or desired.get("defaultCaseUser") or desired.get("systemUserEmail")
        or desired.get("useSystemUserAsDefaultCaseUser") is True)
    write_owner = ((not state["ownerConfigured"])
                   or (args.overwrite_support_settings and owner_input))
    write_automated = ((not state["automatedUserConfigured"])
                       or (args.overwrite_support_settings and automated_input))
    return write_owner, write_automated


def owner_choice(args, desired):
    return (args.owner_type or desired.get("defaultCaseOwnerType"),
            args.owner_value or desired.get("defaultCaseOwner"))


def automated_choice(args, desired):
    """(type, user value, system email) for the Automated Case User, inferring the
    type from the input file when no flag gave it."""
    automated_type = args.automated_type
    value = args.automated_value or desired.get("defaultCaseUser")
    system_email = args.system_user_email or desired.get("systemUserEmail")
    if automated_type is None:
        if desired.get("useSystemUserAsDefaultCaseUser") is True:
            automated_type = "System"
        elif desired.get("defaultCaseUser"):
            automated_type = "User"
    return automated_type, value, system_email


def apply_support_settings(records, args, desired, directory, state, summary):
    """Set Default Case Owner and Automated Case User on `records` in Phase A.

    A configured field is PRESERVED (omitted from the payload, so it keeps its
    value via field-level merge) unless --overwrite-support-settings is given AND
    new input was supplied for THAT field. A field that is NOT configured must be
    supplied; values are validated against the org and fail closed. Never
    assume/guess an owner or automated user."""
    ss = {"ownerConfigured": state["ownerConfigured"],
          "automatedUserConfigured": state["automatedUserConfigured"],
          "current": state["current"]}
    summary["supportSettings"] = ss
    write_owner, write_automated = support_plan(args, desired, state)

    if not write_owner and not write_automated:
        ss["action"] = "preserved-existing"
        ss["ownerAction"] = "preserved"
        ss["automatedUserAction"] = "preserved"
        # Nothing written: omit all Support-Settings fields so they merge-preserve.
        _strip_unwritten_support_fields(records, {})
        return

    applied = {}

    # ---- Default Case Owner ----
    if not write_owner:
        ss["ownerAction"] = "preserved"
    else:
        owner_type, owner_value = owner_choice(args, desired)
        if not (owner_type or owner_value):
            fail("Default Case Owner is not configured in this org and none was "
                 "provided. Ask the user for the Default Case Owner type (User "
                 "or Queue) and value, then pass --owner-type/--owner-value.")
        resolved_owner, resolved_owner_type = resolve_owner(
            directory, owner_value, owner_type)
        set_child_text(records, "defaultCaseOwner", resolved_owner)
        set_child_text(records, "defaultCaseOwnerType", resolved_owner_type)
        applied["defaultCaseOwner"] = resolved_owner
        applied["defaultCaseOwnerType"] = resolved_owner_type
        ss["ownerAction"] = ("overwrote-existing" if state["ownerConfigured"]
                             else "set-from-input")

    # ---- Automated Case User ----
    if not write_automated:
        ss["automatedUserAction"] = "preserved"
    else:
        automated_type, automated_value, system_email = automated_choice(
            args, desired)
        if automated_type is None:
            fail("Automated Case User is not configured in this org and none "
                 "was provided. Ask the user whether it should be a specific "
                 "User (and the username) or System, then pass --automated-type "
                 "User --automated-value <username> or --automated-type System.")
        auto_fields, auto_kind = resolve_automated_user(
            directory, automated_type, automated_value, system_email)
        _clear_automated_user_fields(records)
        for f, v in auto_fields.items():
            set_child_text(records, f, _text(v))
            applied[f] = v
        ss["automatedUserKind"] = auto_kind
        ss["automatedUserAction"] = (
            "overwrote-existing" if state["automatedUserConfigured"]
            else "set-from-input")

    # Roll the two per-field actions up into a single `action` for the summary.
    actions = {ss.get("ownerAction"), ss.get("automatedUserAction")}
    if actions <= {"preserved"}:
        ss["action"] = "preserved-existing"
    elif "overwrote-existing" in actions:
        ss["action"] = "overwrote-existing"
    else:
        ss["action"] = "set-from-input"

    if applied:
        ss["applied"] = applied
        summary["phaseA"].update(applied)

    # Any Support-Settings field NOT written this run must be omitted from the
    # payload (preserved via field-level merge) rather than resent verbatim.
    _strip_unwritten_support_fields(records, applied)


def lookup_targets(args, desired, state, new_addrs):
    """Usernames and Queue names the write will need checked against the org:
    the Default Case Owner and Automated Case User being written, plus each NEW
    address's optional per-address owner. Returns (usernames, queue_names)."""
    users, queues = set(), set()

    def add(kind, value):
        if not value or _is_placeholder(value):
            return
        if kind == "User":
            users.add(value)
        elif kind == "Queue":
            queues.add(value)

    write_owner, write_automated = support_plan(args, desired, state)
    if write_owner:
        owner_type, owner_value = owner_choice(args, desired)
        add(owner_type, owner_value)
    if write_automated:
        automated_type, automated_value, _ = automated_choice(args, desired)
        if automated_type == "User":
            add("User", automated_value)
    for addr in new_addrs:
        add(addr.get("caseOwnerType"), addr.get("caseOwner"))
    return users, queues


# ---------------------------------------------------------------------------
# Production-org gate
# ---------------------------------------------------------------------------

def evaluate_gate(org_records, confirm_production):
    """Decide whether the org may be mutated. Returns the orgInfo dict, or exits
    non-zero.

    Email-to-Case is a permanent, org-wide change (enableEmailToCase cannot be
    turned back off), so a PRODUCTION org (non-sandbox, non-trial) needs explicit
    confirmation. Sandboxes, scratch orgs, and trials proceed. If the Organization
    row cannot be read the type is unknown, and a confirmation flag cannot vouch
    for a type nobody verified - so refuse outright."""
    if not org_records:
        fail("Could not determine whether this is a production org (the "
             "Organization row was not readable). Refusing to mutate an org "
             "of unknown type. Re-authenticate and retry so the Organization "
             "row is readable.")
    row = org_records[0]
    is_sandbox = row.get("IsSandbox")
    org_type = row.get("OrganizationType")
    is_trial = row.get("TrialExpirationDate") is not None
    if is_sandbox is None:
        fail("Could not determine whether this is a production org (the "
             "Organization row was not readable). Refusing to mutate an org "
             "of unknown type. Re-authenticate and retry so the Organization "
             "row is readable.")
    is_production = (is_sandbox is False and not is_trial)
    info = {"isSandbox": is_sandbox, "organizationType": org_type,
            "isTrial": is_trial, "isProduction": is_production}
    if is_production and not confirm_production:
        detail = (f"organizationType={org_type}, isSandbox={is_sandbox}, "
                  f"isTrial={is_trial}")
        fail(f"Target org appears to be PRODUCTION ({detail}). Enabling "
             "Email-to-Case is a permanent, org-wide change. Confirm with the "
             "user that they want to configure Email-to-Case on this "
             "production org, then re-run with --confirm-production. Sandboxes "
             "and trials do not require this flag.")
    return info


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_requests(args):
    version = args.api_version
    kind = args.kind
    if kind == "settings":
        emit({"requests": [settings_read_request(version)]})
    elif kind == "org":
        emit({"requests": [org_request(version)]})
    elif kind == "lookups":
        emit({"requests": lookup_requests(args, version)})
    elif kind == "cases":
        emit({"requests": [cases_request(version, args.supplied_email)]})
    else:  # messages
        status, body = load_response(args.cases_response)
        msgs = error_messages(status, body)
        if msgs:
            fail("Case query failed: " + "; ".join(msgs))
        case_ids = [r["Id"] for r in body.get("records", []) if r.get("Id")]
        emit({"requests": [messages_request(version, case_ids)] if case_ids
              else []})


def lookup_requests(args, version):
    if not args.input or not args.current:
        fail("`requests lookups` needs --input and --current (the read of the "
             "org's CaseSettings).")
    desired = parse_input(args.input)
    current = elem_to_value(parse_settings_response(args.current))
    state = support_settings_state(current)
    addrs = desired_addresses(desired, args.routing_email)
    names, emails = existing_address_keys(current)
    new_addrs, _ = split_addresses(addrs, names, emails)
    users, queues = lookup_targets(args, desired, state, new_addrs)
    out = []
    if users:
        out.append(soql_request(
            version, "SELECT Username FROM User WHERE IsActive = true AND "
                     f"Username IN ({_soql_list(users)})",
            "validate users (pass the result as --users)"))
    if queues:
        lst = _soql_list(queues)
        out.append(soql_request(
            version, "SELECT DeveloperName, Name FROM Group WHERE "
                     f"Type = 'Queue' AND (DeveloperName IN ({lst}) OR "
                     f"Name IN ({lst}))",
            "validate queues (pass the result as --queues)"))
    return out


def cmd_gate(args):
    records = parse_query_records(args.org, "Organization")
    emit({"orgInfo": evaluate_gate(records, args.confirm_production)})


def cmd_read(args):
    emit(elem_to_value(parse_settings_response(args.response)))


def cmd_phase_a(args):
    desired = parse_input(args.input)
    directory = load_directory(args)
    records = parse_settings_response(args.current)
    state = support_settings_state(elem_to_value(records))
    desired_addresses(desired, args.routing_email)  # validates the email count
    version = args.api_version
    desired_e2c = desired.get("emailToCase") or {}
    summary = {"phaseA": {}, "supportSettings": {}}

    # Merge the desired toggles / Support Settings into the record read from the
    # org and write it back. Writing the COMPLETE emailToCase block is what
    # provisions the On-Demand email-service infrastructure; a field-level patch
    # that just flips enableOnDemandEmailToCase does NOT, so Phase B would then
    # fail with "We couldn't save your routing address... custom email services
    # named EmailToCase". Only the fields this skill owns are sent
    # (KEEP_TOP_LEVEL_FIELDS), so the platform never re-validates unrelated Case
    # config such as Case Feed (which would require Chatter).
    apply_support_settings(records, args, desired, directory, state, summary)

    # Any other top-level scalar toggle from the input (e.g. enableDraftEmails).
    # Nested/list values are skipped - only emailToCase (its own block) and the
    # owner fields above are structured. (Fields outside KEEP_TOP_LEVEL_FIELDS
    # are stripped at write time regardless.)
    for key, val in desired.items():
        if key in HANDLED_TOP_LEVEL or isinstance(val, (dict, list)):
            continue
        set_child_text(records, key, _text(val))
        summary["phaseA"][key] = val

    e2c_el = records.find(qn("emailToCase"))
    if e2c_el is None:
        e2c_el = ET.SubElement(records, qn("emailToCase"))
    for key, val in desired_e2c.items():
        if key == "routingAddresses":
            continue  # phase B
        set_child_text(e2c_el, key, _text(val))
        summary["phaseA"][f"emailToCase.{key}"] = val

    emit({"request": settings_write_request(version, records,
                                            "Phase A: toggles + Support Settings"),
          "summary": summary})


PHASE_B_PREREQUISITES = ("enableEmailToCase", "enableOnDemandEmailToCase")


def require_phase_a_applied(current, desired, new_addrs):
    """Fail if `--current` was read before Phase A's write landed.

    Phase B writes back the whole record it is given, so a stale read would
    silently revert Phase A's toggles, and a new address cannot bind without the
    On-Demand email service. Only toggles the input asks to be on are checked, so
    an org the user deliberately leaves off is not blocked here.
    """
    if not new_addrs:
        return
    wanted = desired.get("emailToCase") or {}
    have = current.get("emailToCase") or {}
    missing = [k for k in PHASE_B_PREREQUISITES
               if wanted.get(k) is True and have.get(k) is not True]
    if missing:
        fail("--current does not show " + ", ".join(missing) + " enabled. "
             "Phase B needs a fresh CaseSettings read taken AFTER the Phase A "
             "write succeeded; re-read and re-run phase-b. No write was built.")


def cmd_phase_b(args):
    desired = parse_input(args.input)
    directory = load_directory(args)
    records = parse_settings_response(args.current)
    version = args.api_version
    addrs = desired_addresses(desired, args.routing_email)
    if not addrs:
        emit({"skip": True, "reason": "the input declares no routing addresses",
              "phaseB": []})
        return
    current = elem_to_value(records)
    names, emails = existing_address_keys(current)
    new_addrs, existing_addrs = split_addresses(addrs, names, emails)
    require_phase_a_applied(current, desired, new_addrs)
    phase_b = [{"routingName": a.get("routingName"),
                "emailAddress": a.get("emailAddress"), "status": "already_exists"}
               for a in existing_addrs]

    # The routingAddresses collection is REPLACED (not field-merged) on write, so
    # the payload must carry the existing addresses alongside the new ones.
    #
    # ORDERING IS LOAD-BEARING: when a newly-added routingAddresses element is
    # placed AFTER the existing, already-provisioned ones, the platform can DROP
    # an existing address. With the new address(es) FIRST and the existing ones
    # LAST every address was preserved, with the platform-managed read-only
    # fields stripped or kept alike - so ordering, not those fields, decides it.
    # We therefore detach the existing elements, build the new ones, then
    # re-append the existing ones after them. The `verify` guard backstops any
    # residual drop.
    e2c_el = records.find(qn("emailToCase"))
    if e2c_el is None:
        e2c_el = ET.SubElement(records, qn("emailToCase"))
    existing_ra_elements = e2c_el.findall(qn("routingAddresses"))
    for ra in existing_ra_elements:
        e2c_el.remove(ra)
    for i, addr in enumerate(new_addrs, 1):
        # Validated only for addresses that are genuinely new - a duplicate that
        # is skipped as already_exists needs no owner lookup.
        resolve_address_case_owner(directory, addr, f"routingAddresses[{i}]")
        build_address_element(e2c_el, addr)
        phase_b.append({"routingName": addr.get("routingName"),
                        "emailAddress": addr.get("emailAddress"),
                        "status": "created"})
    for ra in existing_ra_elements:
        e2c_el.append(ra)

    if not new_addrs:
        emit({"skip": True, "reason": "every declared address already exists",
              "phaseB": phase_b})
        return
    emit({"request": settings_write_request(version, records,
                                            "Phase B: routing addresses"),
          "phaseB": phase_b})


def cmd_check_write(args):
    status, body = load_response(args.response)
    msgs = error_messages(status, body)
    results = body.get("results") if isinstance(body, dict) else None
    ok = (not msgs and results
          and all((r or {}).get("success") is True for r in results))
    if not ok:
        fail("The CaseSettings write failed: "
             + ("; ".join(msgs) if msgs else "(no success result returned)"))
    emit({"success": True})


def cmd_verify(args):
    desired = parse_input(args.input)
    initial = elem_to_value(parse_settings_response(args.initial))
    after = elem_to_value(parse_settings_response(args.after))
    desired_e2c = desired.get("emailToCase") or {}
    after_e2c = after.get("emailToCase") or {}
    addrs = desired_addresses(desired, args.routing_email)
    names, emails = existing_address_keys(initial)
    new_addrs, existing_addrs = split_addresses(addrs, names, emails)

    # Preservation guard (runtime safety net): every address the org had BEFORE
    # the run, plus every address we created, must still be present. A shortfall
    # means a write REPLACED the routingAddresses collection and dropped an
    # existing address. Baselined on the very first read so a drop in Phase A is
    # caught as well as one in Phase B.
    initial_count = _count_addresses(initial)
    expected = initial_count + len(new_addrs)
    actual = _count_addresses(after)
    if actual < expected:
        fail(f"Routing-address write did not preserve existing addresses: "
             f"expected at least {expected} ({initial_count} already in the org "
             f"+ {len(new_addrs)} newly created), but the org now has {actual}. "
             f"A write replaced the routingAddresses collection and dropped an "
             f"existing address. No further changes were made; re-run after "
             f"confirming with the skill maintainer.")

    # The platform can answer a Support Settings write with success yet not
    # persist it (e.g. an Automated Case User it deems ineligible), so compare
    # what this run asked to write against what the org now holds.
    scratch = {"supportSettings": {}, "phaseA": {}}
    apply_support_settings(parse_settings_response(args.initial), args, desired,
                           load_directory(args), support_settings_state(initial),
                           scratch)
    not_applied = {
        field: {"requested": want, "orgValue": after.get(field)}
        for field, want in (scratch["supportSettings"].get("applied") or {}).items()
        if str(want).lower() != str(after.get(field)).lower()}
    if not_applied:
        fail("The org did not keep these Support Settings even though the write "
             f"reported success: {json.dumps(not_applied)}. The platform ignored "
             "them (an Automated Case User it does not accept is the usual "
             "cause). Ask the user for a different user, or leave the field alone.")

    verified = {
        "enableEmailToCase": after_e2c.get("enableEmailToCase"),
        "enableOnDemandEmailToCase": after_e2c.get("enableOnDemandEmailToCase"),
        "routingAddressCount": actual,
    }
    # Echo back every toggle the input set so the caller can confirm each
    # requested flag actually landed in the org.
    for key in desired_e2c:
        if key != "routingAddresses":
            verified[f"emailToCase.{key}"] = after_e2c.get(key)
    for key, val in desired.items():
        if key not in HANDLED_TOP_LEVEL and not isinstance(val, (dict, list)):
            verified[key] = after.get(key)
    for field in SUPPORT_SETTINGS_FIELDS:
        verified[field] = after.get(field)
    emit({"verified": verified,
          "phaseB": ([{"routingName": a.get("routingName"),
                       "emailAddress": a.get("emailAddress"),
                       "status": "already_exists"} for a in existing_addrs]
                     + [{"routingName": a.get("routingName"),
                         "emailAddress": a.get("emailAddress"),
                         "status": "created"} for a in new_addrs])})


def cmd_cases(args):
    """Prove inbound email created Cases: an Email-origin Case from the last 3
    days with a linked incoming EmailMessage. A deploy landing is not proof; a
    Case with its incoming message is. Exits non-zero when there is none."""
    cases = parse_query_records(args.cases, "Case")
    messages = (parse_query_records(args.messages, "EmailMessage")
                if args.messages else [])
    parents = {m.get("ParentId") for m in messages}
    result = {
        "mode": "verify-cases",
        "filter": {"suppliedEmail": args.supplied_email,
                   "window": "LAST_N_DAYS:3"},
        "caseCount": len(cases),
        "cases": [
            {"caseNumber": c.get("CaseNumber"), "id": c.get("Id"),
             "origin": c.get("Origin"), "suppliedEmail": c.get("SuppliedEmail"),
             "createdDate": c.get("CreatedDate"),
             "hasIncomingEmailMessage": c.get("Id") in parents}
            for c in cases],
        "incomingEmailMessageCount": len(messages),
    }
    result["proven"] = any(c.get("Id") in parents for c in cases)
    emit(result)
    if result["proven"]:
        return
    if not cases:
        fail("No Cases with Origin='Email' in the last 3 days matched"
             + (f" SuppliedEmail={args.supplied_email}"
                if args.supplied_email else "")
             + ". The inbound email may not have arrived yet, the routing "
             "address may not be verified, the test email may be older than "
             "the 3-day window, or the sender differs. Confirm the user "
             "actually sent the test email, wait a moment, and re-run.")
    fail("Found Email-origin Case(s) but none has a linked incoming "
         "EmailMessage (Incoming=true). The Case may have been created "
         "another way. Re-run once the inbound email has been processed.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def add_input_flags(sp, *, support=False):
    sp.add_argument("--input", required=True,
                    help="Path to the CaseSettings source file to apply.")
    sp.add_argument("--routing-email", action="append", default=[],
                    metavar="EMAIL",
                    help="Customer-facing email for a routing address. Repeat "
                         "once per routing address, in the order they appear in "
                         "--input. Required if --input declares any.")
    sp.add_argument("--api-version", default=None, metavar="X.Y",
                    help="Pin the API version in request paths. Default: unversioned "
                         "paths, so the server uses the org's own version.")
    if support:
        sp.add_argument("--owner-type", choices=sorted(VALID_OWNER_TYPES),
                        default=None,
                        help="Default Case Owner type. Required when Support "
                             "Settings are not yet configured. Falls back to the "
                             "input file's defaultCaseOwnerType.")
        sp.add_argument("--owner-value", default=None,
                        help="Default Case Owner: an active Username (User) or a "
                             "Queue DeveloperName (Queue).")
        sp.add_argument("--automated-type",
                        choices=sorted(VALID_AUTOMATED_TYPES), default=None,
                        help="Automated Case User type: User or System. System "
                             "uses the org's automated process user.")
        sp.add_argument("--automated-value", default=None,
                        help="Automated Case User username (for --automated-type "
                             "User).")
        sp.add_argument("--system-user-email", default=None,
                        help="Email for the automated process user, used with "
                             "--automated-type System when it does not exist yet.")
        sp.add_argument("--overwrite-support-settings", action="store_true",
                        help="Overwrite an already-configured Default Case Owner "
                             "or Automated Case User. Scoped per field: only the "
                             "field(s) you also supply new input for are "
                             "rewritten. Without this, existing values are "
                             "preserved.")


def add_lookup_flags(sp):
    sp.add_argument("--users", default=None, metavar="FILE",
                    help="Response of the user-validation query from "
                         "`requests lookups`.")
    sp.add_argument("--queues", default=None, metavar="FILE",
                    help="Response of the queue-validation query from "
                         "`requests lookups`.")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("requests", help="Print the request(s) to dispatch.")
    sp.add_argument("kind", choices=["settings", "org", "lookups",
                                     "cases", "messages"])
    sp.add_argument("--api-version", default=None, metavar="X.Y")
    sp.add_argument("--input", default=None)
    sp.add_argument("--current", default=None, metavar="FILE",
                    help="With `lookups`: the CaseSettings read response.")
    sp.add_argument("--routing-email", action="append", default=[],
                    metavar="EMAIL")
    sp.add_argument("--owner-type", choices=sorted(VALID_OWNER_TYPES),
                    default=None)
    sp.add_argument("--owner-value", default=None)
    sp.add_argument("--automated-type", choices=sorted(VALID_AUTOMATED_TYPES),
                    default=None)
    sp.add_argument("--automated-value", default=None)
    sp.add_argument("--system-user-email", default=None)
    sp.add_argument("--overwrite-support-settings", action="store_true")
    sp.add_argument("--supplied-email", default=None, metavar="EMAIL",
                    help="With `cases`: narrow to this sender (Case.SuppliedEmail).")
    sp.add_argument("--cases-response", default=None, metavar="FILE",
                    help="With `messages`: the Case query response.")
    sp.set_defaults(func=cmd_requests)

    sp = sub.add_parser("gate", help="Production-org safety verdict.")
    sp.add_argument("--org", required=True, metavar="FILE",
                    help="Response of `requests org`.")
    sp.add_argument("--confirm-production", action="store_true",
                    help="The user confirmed they intend to configure "
                         "Email-to-Case on a PRODUCTION org. Never pass it "
                         "unprompted; it does not override an unreadable "
                         "Organization row.")
    sp.set_defaults(func=cmd_gate)

    sp = sub.add_parser("read", help="Print the current CaseSettings.")
    sp.add_argument("--response", required=True, metavar="FILE")
    sp.set_defaults(func=cmd_read)

    sp = sub.add_parser("phase-a", help="Build the Phase A write.")
    add_input_flags(sp, support=True)
    sp.add_argument("--current", required=True, metavar="FILE",
                    help="The CaseSettings read response.")
    add_lookup_flags(sp)
    sp.set_defaults(func=cmd_phase_a)

    sp = sub.add_parser("phase-b", help="Build the Phase B write.")
    # Phase B writes only routing addresses and ignores the Support Settings
    # flags. They are still accepted so the one flag set the workflow builds
    # works unchanged on phase-a, phase-b and verify.
    add_input_flags(sp, support=True)
    sp.add_argument("--current", required=True, metavar="FILE",
                    help="A fresh CaseSettings read taken AFTER Phase A.")
    add_lookup_flags(sp)
    sp.set_defaults(func=cmd_phase_b)

    sp = sub.add_parser("check-write", help="Validate a write response.")
    sp.add_argument("--response", required=True, metavar="FILE")
    sp.set_defaults(func=cmd_check_write)

    sp = sub.add_parser("verify", help="Preservation guard + verified summary.")
    add_input_flags(sp, support=True)
    add_lookup_flags(sp)
    sp.add_argument("--initial", required=True, metavar="FILE",
                    help="The CaseSettings read taken BEFORE Phase A.")
    sp.add_argument("--after", required=True, metavar="FILE",
                    help="A CaseSettings read taken AFTER the last write.")
    sp.set_defaults(func=cmd_verify)

    sp = sub.add_parser("cases", help="Prove inbound email created Cases.")
    sp.add_argument("--cases", required=True, metavar="FILE",
                    help="Response of `requests cases`.")
    sp.add_argument("--messages", default=None, metavar="FILE",
                    help="Response of `requests messages` (omit if no Cases).")
    sp.add_argument("--supplied-email", default=None, metavar="EMAIL")
    sp.set_defaults(func=cmd_cases)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
