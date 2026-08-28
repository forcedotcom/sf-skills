#!/usr/bin/env python3
"""Apply Email-to-Case CaseSettings to an org via the Metadata API's CRUD
updateMetadata call (read -> merge -> update -> verify), in two phases.

Why updateMetadata and not a file-based deploy: enabling On-Demand
Email-to-Case provisions the org's internal email-service infrastructure,
and a routing address can only bind to it in a SUBSEQUENT operation. A
single file-based deploy that both enables On-Demand and declares a routing
address fails on a freshly-configured org ("We couldn't save your routing
address..."). This script therefore applies changes in two phases:

  Phase A - prerequisites + toggles (Support Settings owner / automated case
            user, enableEmailToCase, enableOnDemandEmailToCase, plus any other
            emailToCase flags EXCEPT routingAddresses).
  Phase B - routing addresses, appended one updateMetadata call after the
            toggles are live.

Each write sends ONLY the top-level CaseSettings fields this skill owns (see
KEEP_TOP_LEVEL_FIELDS) plus the complete emailToCase block; all other top-level
fields read from the org are stripped. This is deliberate: the platform
re-validates any top-level field present in the payload even at an unchanged
value, and some (e.g. Case Feed) carry dependencies unrelated to Email-to-Case
(Case Feed needs Chatter), which would fail the call on orgs where that config
differs. Stripped fields keep their current value via field-level merge, and
provisioning is driven by the emailToCase block, so the skill needs no Chatter
prerequisite and is unaffected by unrelated org Case configuration.

Authentication uses the Salesforce CLI's existing session for a target-org
alias (no passwords handled here): `sf org display --target-org <alias> --json`
supplies the instanceUrl, username, and apiVersion, and
`sf org auth show-access-token` supplies the live session token. Recent CLIs
REDACT the token in `sf org display` output (a `[REDACTED ...]` marker, with or
without `--verbose`), so it is not reused directly. Only older CLIs that predate
the show-access-token subcommand are served by a fallback, and those omit the
token from non-verbose `sf org display` entirely — so the fallback issues a
`--verbose` display to obtain it.

Support Settings (Default Case Owner + Automated Case User) are handled so no
value is ever assumed or guessed:
  * If the org ALREADY has them configured, they are PRESERVED untouched
    (unless --overwrite-support-settings is passed). The platform returns these
    fields null when unset, so a null read is a reliable "not configured"
    signal.
  * If NOT configured, the caller must supply explicit values (the skill
    elicits them):
      - Default Case Owner: --owner-type {User|Queue} + --owner-value. A User
        value must be an active Username; a Queue value must be a real Queue
        (matched on DeveloperName). Invalid input fails closed with an
        actionable message so the skill can re-prompt.
      - Automated Case User: --automated-type {User|System}. User needs
        --automated-value (an active Username); System sets
        useSystemUserAsDefaultCaseUser and needs no user value (optionally
        --system-user-email when the org's automated case user doesn't exist).
    The authenticated CLI user is used ONLY with --use-authenticated-user, and
    only when the operator explicitly asks for it.
  * Routing-address email addresses must be supplied explicitly with
    --routing-email (one per routing address, in document order). The script
    refuses to run if the input declares routing addresses but no
    --routing-email is given.

Before mutating a PRODUCTION org (non-sandbox, non-trial), the script fails
closed unless --confirm-production is passed — enabling Email-to-Case is a
permanent, org-wide change. Sandboxes and trials deploy without it. The Metadata
API version is derived from the org and floored at DEFAULT_API_VERSION (67.0);
pass --api-version to force a specific version.

Usage:
  python3 apply-casesettings.py --target-org <alias> --input <file> \
      --routing-email support@yourco.com \
      --owner-type Queue --owner-value Support_Queue \
      --automated-type System --system-user-email ops-noreply@yourco.com
  python3 apply-casesettings.py --target-org <alias> --input <file> --verify-only
  # Act 3 — prove inbound email created Cases (read-only; no --input needed):
  python3 apply-casesettings.py --target-org <alias> --verify-cases \
      --supplied-email customer@external.com

The --input file is a standard CaseSettings source file (the artifact this
skill produces). The script parses it, resolves/validates the owner + automated
user (only when not already configured), substitutes the supplied routing
email(s), applies phase A then phase B, and re-reads to verify. Prints a JSON
summary to stdout; exits non-zero on any SOAP fault or failed SaveResult (the
error text is printed to stderr).
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

META_NS = "http://soap.sforce.com/2006/04/metadata"
SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
# Matches the skill's declared minApiVersion (67.0), which clears the version
# floors of every emailToCase toggle this skill sets (e.g. showWordCountInComposer)
# and the Support-Settings System-user fields. The routing-address
# `botEmailDefinition` child (Agentforce for Service on Email) requires v68.0+.
DEFAULT_API_VERSION = "67.0"
# Resolved at runtime by get_session(): an explicit --api-version wins, otherwise
# it is DERIVED from the org's own apiVersion (as reported by `sf org display`)
# but floored at DEFAULT_API_VERSION — see resolve_api_version. This lets the
# skill use the org's newer features (e.g. the v68+ botEmailDefinition binding)
# with no manual flag, while never dropping below the field version-floors this
# skill relies on and never outrunning what the org actually supports.
API_VERSION = DEFAULT_API_VERSION
# Set True in main() when the operator passed --api-version, so get_session skips
# the org-derived version and honors the explicit override.
_API_VERSION_EXPLICIT = False
# Set by get_session(): the sf CLI alias/username used to run read-only SOQL via
# `sf data query --json`, so the sf CLI holds the token. The raw session token is
# only ever put on the wire by the SOAP metadata path (readMetadata/updateMetadata),
# which has no CLI equivalent.
TARGET_ORG = None

# Platform-managed read-only fields the org mints on a routing address. We never
# declare these on a write (defensive hygiene). NOTE: stripping them is not what
# preserves existing addresses on a multi-address write — document ordering is
# (new addresses before existing ones). See strip_readonly_address_fields.
READONLY_ADDRESS_FIELDS = {"emailServicesAddress", "isVerified"}

# Top-level CaseSettings fields this skill is responsible for — the ONLY
# top-level children we send in an updateMetadata payload. Every other top-level
# field the read returns is stripped before writing.
#
# Why strip everything else: the platform RE-VALIDATES any field present in the
# payload, even at an unchanged value. Several top-level Case fields carry
# dependencies unrelated to Email-to-Case — most notably Case Feed, whose
# re-validation requires Chatter (feeds) and otherwise fails the whole call with
# "The setup requirements for Case Feed Items has to be enabled." Sending only
# the fields we own avoids every such unrelated re-validation (Case Feed,
# swarming, solutions, suggested articles, web-to-case, ...), so the skill works
# on orgs regardless of their other Case configuration and needs no Chatter
# prerequisite.
#
# Why this is safe: CaseSettings updateMetadata merges at the field level, so any
# omitted top-level field keeps its current org value untouched (verified:
# enableCaseFeed and enableCollapseEmailThread both stay true after a write that
# omits them). Provisioning of the On-Demand email service is driven entirely by
# the full `emailToCase` block, NOT by any top-level field (verified from scratch
# on a Chatter-off org: stripping all 35 other top-level fields still provisioned
# and bound a routing address). `emailToCase` and `fullName` are always kept in
# addition to these; support-settings fields (SUPPORT_SETTINGS_FIELDS) are here.
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


def local_name(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag


def qn(name):
    return f"{{{META_NS}}}{name}"


# ---------------------------------------------------------------------------
# sf CLI session
# ---------------------------------------------------------------------------

def sf_json(args):
    """Run an `sf` command with --json and return the parsed 'result'."""
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        fail("The Salesforce CLI (`sf`) was not found on PATH. Install it or "
             "authenticate the target org first.")
    if proc.returncode != 0:
        # sf prints a JSON error on stdout even on failure; try to surface it.
        detail = proc.stdout.strip() or proc.stderr.strip()
        fail(f"`{' '.join(args)}` failed: {detail}")
    try:
        return json.loads(proc.stdout)["result"]
    except (json.JSONDecodeError, KeyError) as exc:
        fail(f"Could not parse `{' '.join(args)}` output: {exc}")


def sf_json_optional(args):
    """Like ``sf_json`` but return None instead of exiting when the command is
    unavailable or fails. Used to probe optional subcommands that don't exist on
    every CLI version (e.g. older CLIs lack `sf org auth show-access-token`)."""
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout).get("result")
    except (json.JSONDecodeError, AttributeError):
        return None


def _usable_access_token(token):
    """True if ``token`` looks like a live Salesforce session token.

    A real token is ``<orgId>!<...>``; the `!` separator is always present.
    Recent CLIs redact the token in `sf org display --json` (returning a
    non-empty `[REDACTED ...]` marker), which must be rejected rather than sent
    as a Bearer token."""
    return isinstance(token, str) and "!" in token and "REDACTED" not in token


def _version_tuple(value):
    """Parse an 'X.Y' API version string to a (major, minor) int tuple, or None
    if it isn't a recognizable numeric version."""
    if not value:
        return None
    try:
        parts = str(value).strip().split(".")
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        return None


def resolve_api_version(org_api_version):
    """Return the API version string to use, given the org's own apiVersion
    (as reported by `sf org display`; may be None/blank/garbage).

    Rule: floor, not "always latest". The effective version is
    max(org_apiVersion, DEFAULT_API_VERSION) — so the skill rides the org's newer
    features (e.g. the v68+ botEmailDefinition binding) automatically, but never
    drops below DEFAULT_API_VERSION (the floor that clears every field this skill
    sets) and never claims a version the org doesn't report. If the org's version
    can't be parsed, fall back to DEFAULT_API_VERSION."""
    org_t = _version_tuple(org_api_version)
    floor_t = _version_tuple(DEFAULT_API_VERSION)
    if org_t is None or org_t < floor_t:
        return DEFAULT_API_VERSION
    return org_api_version.strip() if isinstance(org_api_version, str) else str(
        org_api_version)


def get_session(target_org):
    """Return (session_id, metadata_url, instance_url, auth_username).

    Also resolves the global API_VERSION when it was not set explicitly via
    --api-version: it is derived from the org's reported apiVersion but floored
    at DEFAULT_API_VERSION (see resolve_api_version)."""
    display = sf_json(["sf", "org", "display", "--target-org", target_org,
                       "--json"])
    instance_url = display.get("instanceUrl")
    if not instance_url:
        fail(f"No instanceUrl for org '{target_org}'. Is it authenticated?")
    auth_username = display.get("username")
    if not auth_username:
        fail(f"Could not determine the authenticated username for "
             f"org '{target_org}'.")
    # Derive the API version from the org unless the operator forced one with
    # --api-version. `sf org display` reports the CLI's configured apiVersion for
    # the org (the org default unless locally overridden); flooring at
    # DEFAULT_API_VERSION keeps every field this skill sets valid.
    global API_VERSION, TARGET_ORG
    TARGET_ORG = target_org
    if not _API_VERSION_EXPLICIT:
        API_VERSION = resolve_api_version(display.get("apiVersion"))
    # Obtain a live access token. Prefer `sf org auth show-access-token`, which
    # returns the real session token; recent CLIs REDACT the token in
    # `sf org display --json` (a `[REDACTED ...]` marker, verbose or not) so it
    # can't be sent as a Bearer token. Only when that subcommand is unavailable
    # (older CLIs) fall back to a `--verbose` display: those CLIs omit the token
    # from non-verbose output entirely, so a plain `sf org display` never carries
    # it. Either way, accept a value only if it looks like a live token.
    token = None
    at = sf_json_optional(["sf", "org", "auth", "show-access-token",
                           "--target-org", target_org, "--no-prompt", "--json"])
    # `result` is an object (`{accessToken}`) on current CLIs, but accept a bare
    # string too in case a CLI version returns the token directly.
    if isinstance(at, str):
        token = at
    elif isinstance(at, dict):
        token = at.get("accessToken")
    if not _usable_access_token(token):
        verbose = sf_json_optional(["sf", "org", "display", "--target-org",
                                    target_org, "--verbose", "--json"])
        if isinstance(verbose, dict):
            token = verbose.get("accessToken")
    if not _usable_access_token(token):
        fail(f"Could not obtain a usable access token for org '{target_org}'. "
             f"Re-authenticate with `sf org login` and try again.")
    metadata_url = f"{instance_url}/services/Soap/m/{API_VERSION}"
    return token, metadata_url, instance_url, auth_username


def query_active_user(session_id, instance_url, username):
    """Return the exact Username of an active User matching `username`
    (case-insensitively), or None if there is no active match."""
    if not username:
        return None
    escaped = username.replace("\\", "\\\\").replace("'", "\\'")
    soql = ("SELECT Username FROM User "
            f"WHERE Username = '{escaped}' AND IsActive = true")
    records = _soql_query(session_id, instance_url, soql).get("records", [])
    return records[0]["Username"] if records else None


def _soql_query(session_id, instance_url, soql):
    # Read-only SOQL runs through `sf data query`, so the sf CLI holds the token
    # — the raw session_id is only ever put on the wire by the SOAP metadata path
    # (read/update), which has no CLI equivalent. session_id and instance_url are
    # retained for signature parity with the test seams and other query helpers.
    result = sf_json(["sf", "data", "query", "--target-org", TARGET_ORG,
                      "--query", soql, "--json"])
    # `sf data query --json` returns {"records": [...], "totalSize": N, ...} under
    # 'result' — the same shape callers already consume from the REST /query body.
    return result if isinstance(result, dict) else {"records": []}


def query_org_info(session_id, instance_url):
    """Return (is_sandbox, organization_type, is_trial) for the target org, or
    (None, None, None) if the Organization row can't be read. Used by the
    production-org safety gate."""
    soql = ("SELECT IsSandbox, OrganizationType, TrialExpirationDate "
            "FROM Organization LIMIT 1")
    data = _soql_query(session_id, instance_url, soql)
    records = data.get("records", [])
    if not records:
        return None, None, None
    row = records[0]
    return (row.get("IsSandbox"), row.get("OrganizationType"),
            row.get("TrialExpirationDate") is not None)


def query_email_cases(session_id, instance_url, supplied_email=None):
    """Return the list of Case records created from inbound email
    (Origin = 'Email') within the last 3 days, optionally narrowed to a
    SuppliedEmail. The 3-day window excludes stale pre-existing email Cases so a
    verify run can't false-pass on an old Case. Used by --verify-cases to prove
    inbound mail created Cases."""
    where = ["Origin = 'Email'"]
    if supplied_email:
        esc = supplied_email.replace("\\", "\\\\").replace("'", "\\'")
        where.append(f"SuppliedEmail = '{esc}'")
    # Fixed SOQL date-literal window (a constant, never operator input) — recent
    # enough to catch a test email sent over a weekend, tight enough to exclude
    # old Cases from a prior setup.
    where.append("CreatedDate >= LAST_N_DAYS:3")
    soql = ("SELECT Id, CaseNumber, Origin, SuppliedEmail, Subject, Status, "
            "CreatedDate FROM Case WHERE " + " AND ".join(where) +
            " ORDER BY CreatedDate DESC LIMIT 50")
    data = _soql_query(session_id, instance_url, soql)
    return data.get("records", [])


def query_incoming_email_messages(session_id, instance_url, case_ids):
    """Return incoming EmailMessage records (Incoming = true) whose ParentId is
    one of `case_ids`. Proves the Case has its linked inbound email."""
    if not case_ids:
        return []
    quoted = ", ".join(
        "'" + cid.replace("\\", "\\\\").replace("'", "\\'") + "'"
        for cid in case_ids)
    soql = ("SELECT Id, ParentId, FromAddress, ToAddress, Subject, Incoming, "
            "MessageDate FROM EmailMessage "
            f"WHERE Incoming = true AND ParentId IN ({quoted}) "
            "ORDER BY MessageDate DESC LIMIT 200")
    data = _soql_query(session_id, instance_url, soql)
    return data.get("records", [])


def query_queue(session_id, instance_url, name):
    """Return the DeveloperName of a Queue matching `name` (by DeveloperName,
    which is what CaseSettings.defaultCaseOwner stores for a queue; Name is
    accepted too as a tolerant fallback), or None if there is no match."""
    if not name:
        return None
    escaped = name.replace("\\", "\\\\").replace("'", "\\'")
    soql = ("SELECT DeveloperName FROM Group "
            f"WHERE Type = 'Queue' AND (DeveloperName = '{escaped}' "
            f"OR Name = '{escaped}')")
    data = _soql_query(session_id, instance_url, soql)
    records = data.get("records", [])
    return records[0]["DeveloperName"] if records else None


def resolve_owner(session_id, instance_url, owner_value, owner_type):
    """Validate a user-supplied Default Case Owner against the org and return
    (resolved_value, resolved_type). Fails closed with an actionable message if
    the type is invalid or the value is not a real active user / queue.

    Never assumes the authenticated user — the caller must have supplied an
    explicit owner (the skill elicits it)."""
    if owner_type not in VALID_OWNER_TYPES:
        fail(f"defaultCaseOwnerType '{owner_type}' is not valid. It must be "
             f"'User' or 'Queue'. Ask the user for a valid type and value.")
    if not owner_value:
        fail(f"defaultCaseOwnerType is '{owner_type}' but no defaultCaseOwner "
             f"value was provided. Ask the user for the {owner_type} to use.")
    if owner_type == "User":
        resolved = query_active_user(session_id, instance_url, owner_value)
        if not resolved:
            fail(f"Default Case Owner '{owner_value}' is not an active User in "
                 f"this org. Ask the user for a valid username (or a Queue).")
        return resolved, "User"
    # Queue
    resolved = query_queue(session_id, instance_url, owner_value)
    if not resolved:
        fail(f"Default Case Owner '{owner_value}' is not a Queue in this org. "
             f"Ask the user for a valid queue DeveloperName (or a User).")
    return resolved, "Queue"


def _is_placeholder(value):
    """A value left as an unfilled template token, e.g. {CASE_OWNER_...}."""
    return (isinstance(value, str) and value.startswith("{")
            and value.endswith("}"))


def resolve_address_case_owner(session_id, instance_url, addr, label):
    """Validate the OPTIONAL per-address Default Case Owner on one routing
    address, in place. Rules (applied only when the user opted in to a
    per-address owner, i.e. caseOwner is present):
      * caseOwner must not be an unfilled placeholder.
      * caseOwnerType is required whenever caseOwner is set (platform rejects
        caseOwner without it) and must be 'User' or 'Queue'.
      * The value is validated against the org — an active Username for User, a
        real Queue DeveloperName for Queue — and fails closed if it does not
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
    resolved, resolved_type = resolve_owner(
        session_id, instance_url, case_owner, case_owner_type)
    addr["caseOwner"] = resolved
    addr["caseOwnerType"] = resolved_type


def resolve_automated_user(session_id, instance_url, automated_type,
                           user_value, system_email):
    """Validate the user-supplied Automated Case User and return a dict of the
    CaseSettings fields to write. 'System' → useSystemUserAsDefaultCaseUser
    (no defaultCaseUser). 'User' → a validated defaultCaseUser username.
    Fails closed with an actionable message on any invalid input."""
    if automated_type not in VALID_AUTOMATED_TYPES:
        fail(f"Automated Case User type '{automated_type}' is not valid. It "
             f"must be 'User' or 'System'. Ask the user for a valid type.")
    if automated_type == "System":
        # System needs no user value; systemUserEmail is required only if the
        # org's automated case user does not exist yet — we pass it through
        # when provided and let the platform validate.
        fields = {"useSystemUserAsDefaultCaseUser": True}
        if system_email:
            fields["systemUserEmail"] = system_email
        return fields, "System"
    # User
    if not user_value:
        fail("Automated Case User type is 'User' but no defaultCaseUser value "
             "was provided. Ask the user for the username to use.")
    resolved = query_active_user(session_id, instance_url, user_value)
    if not resolved:
        fail(f"Automated Case User '{user_value}' is not an active User in "
             f"this org. Ask the user for a valid username (or use System).")
    return {"defaultCaseUser": resolved,
            "useSystemUserAsDefaultCaseUser": False}, "User"


# ---------------------------------------------------------------------------
# SOAP plumbing
# ---------------------------------------------------------------------------

def post_soap(url, envelope, soap_action):
    req = urllib.request.Request(
        url, data=envelope.encode("utf-8"), method="POST",
        headers={"Content-Type": "text/xml; charset=UTF-8",
                 "SOAPAction": soap_action})
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        body = e.read()  # SOAP faults come back with a non-2xx status + body
    except urllib.error.URLError as e:
        fail(f"Could not reach {url}: {e}")
    return ET.fromstring(body)


def find_fault(root):
    fault = root.find(f".//{{{SOAP_NS}}}Fault")
    if fault is None:
        return None
    fs = fault.find("faultstring")
    return fs.text if fs is not None else ET.tostring(fault, encoding="unicode")


def envelope(session_id, body_inner):
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<soapenv:Envelope xmlns:soapenv="{SOAP_NS}" xmlns:met="{META_NS}">'
        f'<soapenv:Header><met:SessionHeader>'
        f'<met:sessionId>{escape_xml(session_id)}</met:sessionId>'
        f'</met:SessionHeader></soapenv:Header>'
        f'<soapenv:Body>{body_inner}</soapenv:Body></soapenv:Envelope>'
    )


def escape_xml(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def read_case_settings(session_id, metadata_url):
    body = (f'<met:readMetadata><met:type>CaseSettings</met:type>'
            f'<met:fullNames>Case</met:fullNames></met:readMetadata>')
    root = post_soap(metadata_url, envelope(session_id, body), "readMetadata")
    fault = find_fault(root)
    if fault:
        fail(f"readMetadata failed: {fault}")
    records = root.find(f".//{qn('records')}")
    if records is None:
        fail("readMetadata returned no CaseSettings record.")
    return records


def strip_readonly_address_fields(records):
    """Remove platform-managed read-only fields (emailServicesAddress,
    isVerified) from EVERY routingAddresses element under emailToCase, in place.

    This is defensive hygiene, NOT the multi-address preservation mechanism. A
    write should never declare platform-managed fields the org owns; stripping
    them keeps our payload clean and avoids relying on the platform to tolerate
    them.

    It is explicitly NOT what preserves existing addresses: these fields are
    irrelevant to preservation — existing addresses were dropped with the fields
    stripped AND survived with them kept as-read — the deciding factor is document
    ORDER, not these fields. See the ORDERING note in main()'s Phase B (new
    addresses must precede existing ones in the routingAddresses collection) for
    the actual preservation mechanism."""
    e2c = records.find(qn("emailToCase"))
    if e2c is None:
        return
    for addr in e2c.findall(qn("routingAddresses")):
        for field in READONLY_ADDRESS_FIELDS:
            el = addr.find(qn(field))
            if el is not None:
                addr.remove(el)


def update_case_settings(session_id, metadata_url, records):
    metadata_el = ET.Element(qn("metadata"))
    metadata_el.set(f"{{{XSI_NS}}}type", "met:CaseSettings")
    # Defensive hygiene: don't declare platform-managed read-only address fields
    # (emailServicesAddress, isVerified) on a write. This is NOT what preserves
    # existing addresses — that is document ordering (see the Phase B ORDERING
    # note). See strip_readonly_address_fields.
    strip_readonly_address_fields(records)
    # Send ONLY the top-level fields this skill owns; drop every other top-level
    # child the read returned. This avoids the platform re-validating unrelated
    # Case config (Case Feed → Chatter, swarming, solutions, ...). Dropped fields
    # keep their current org value via field-level merge; provisioning is driven
    # by the emailToCase block, not by any top-level field. See
    # KEEP_TOP_LEVEL_FIELDS.
    for child in list(records):
        if local_name(child.tag) in KEEP_TOP_LEVEL_FIELDS:
            metadata_el.append(child)
    update_el = ET.Element(qn("updateMetadata"))
    update_el.append(metadata_el)
    ET.register_namespace("met", META_NS)
    ET.register_namespace("xsi", XSI_NS)
    body = ET.tostring(update_el, encoding="unicode")
    root = post_soap(metadata_url, envelope(session_id, body), "updateMetadata")
    fault = find_fault(root)
    if fault:
        fail(f"updateMetadata failed: {fault}")
    result = root.find(f".//{qn('result')}")
    success_el = result.find(qn("success")) if result is not None else None
    if success_el is None or success_el.text != "true":
        msgs = []
        if result is not None:
            for err in result.findall(qn("errors")):
                m = err.find(qn("message"))
                msgs.append(m.text if m is not None else
                            ET.tostring(err, encoding="unicode"))
        fail("updateMetadata reported failure: " +
             ("; ".join(msgs) if msgs else "(no error detail returned)"))


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


def build_address_element(parent, addr_dict):
    """Append one <routingAddresses> element built from a dict."""
    ra = ET.SubElement(parent, qn("routingAddresses"))
    for key, val in addr_dict.items():
        if key in READONLY_ADDRESS_FIELDS:
            continue  # never write platform-managed fields
        child = ET.SubElement(ra, qn(key))
        child.text = "true" if val is True else ("false" if val is False
                                                 else str(val))
    return ra


# ---------------------------------------------------------------------------
# Parse the input CaseSettings artifact
# ---------------------------------------------------------------------------

def parse_input(path):
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        fail(f"Could not read input file '{path}': {exc}")
    root = tree.getroot()
    if local_name(root.tag) != "CaseSettings":
        fail(f"Input root must be CaseSettings, found '{local_name(root.tag)}'.")
    return elem_to_value(root)


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def existing_address_keys(records_value):
    """Return (routingNames, emailAddresses) already present, to avoid duplicates."""
    e2c = records_value.get("emailToCase") or {}
    addrs = e2c.get("routingAddresses")
    if addrs is None:
        return set(), set()
    if isinstance(addrs, dict):
        addrs = [addrs]
    names = {a.get("routingName") for a in addrs if a.get("routingName")}
    emails = {a.get("emailAddress") for a in addrs if a.get("emailAddress")}
    return names, emails


def support_settings_state(records_value):
    """Report whether Default Case Owner and Automated Case User are already
    configured in the org (from a readMetadata). The platform returns these
    fields null/absent when an admin has not set them, so null is a reliable
    "not configured" signal. Returns a dict with two booleans and the current
    values (for the summary)."""
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

    The five SUPPORT_SETTINGS_FIELDS are in KEEP_TOP_LEVEL_FIELDS so a field we
    DO set survives update_case_settings' strip. The side effect is that a field
    left as-read (preserved, not written) would otherwise be RESENT on the write,
    forcing the platform to re-validate a value nobody asked to touch — and a
    platform-derived `systemUserEmail` resent this way can collide with the
    routing address ("Enter an email address for the system user that's not an
    Email-to-Case routing email address"). Stripping the fields absent from
    `applied` applies the same omit-to-preserve pattern used for every other
    untouched top-level field.

    Scope: touches ONLY the five SUPPORT_SETTINGS_FIELDS. `emailToCase` (and its
    `routingAddresses`) is never a support field, so routing addresses are
    unaffected."""
    for field in SUPPORT_SETTINGS_FIELDS:
        if field in applied:
            continue
        el = records.find(qn(field))
        if el is not None:
            records.remove(el)


def apply_support_settings(records, args, desired, session_id, instance_url,
                           auth_username, state, summary):
    """Set Default Case Owner and Automated Case User on `records` in Phase A.

    Default Case Owner and Automated Case User are INDEPENDENT fields — an org
    can have one configured and the other not — so each is preserved or written
    on its own:
      * A field already configured in the org is PRESERVED (left untouched in
        `records`, so it keeps its value via field-level merge) unless
        --overwrite-support-settings is given AND the caller supplied new input
        for THAT field. The overwrite flag is scoped per field: overwriting one
        configured field never forces a rewrite of the other, unrelated field.
        A field the caller supplies for an already-configured setting is ignored
        (preserved) without that flag.
      * A field that is NOT configured must be supplied (via flags, the input
        file, or --use-authenticated-user); values are validated against the org
        and fail closed with an actionable message. Input is required ONLY for
        the field(s) actually being written.
      * The authenticated user is used ONLY with --use-authenticated-user, and
        only for the field(s) being written.
      * Never assume/guess an owner or automated user.
    """
    ss = {"ownerConfigured": state["ownerConfigured"],
          "automatedUserConfigured": state["automatedUserConfigured"],
          "current": state["current"]}
    summary["supportSettings"] = ss

    overwrite = args.overwrite_support_settings
    # Detect, per field, whether the caller actually supplied new input for it.
    # --overwrite-support-settings scopes to the field(s) the caller is changing;
    # it must never force a rewrite of an unrelated configured field the caller
    # did not touch. --use-authenticated-user supplies input for BOTH fields (it
    # sets the authenticated user as owner and automated user by design).
    owner_input = bool(
        args.owner_type or args.owner_value
        or desired.get("defaultCaseOwner") or desired.get("defaultCaseOwnerType"))
    automated_input = bool(
        args.automated_type or args.automated_value or args.system_user_email
        or desired.get("defaultCaseUser") or desired.get("systemUserEmail")
        or desired.get("useSystemUserAsDefaultCaseUser") is True)
    if args.use_authenticated_user:
        owner_input = True
        automated_input = True

    # Decide per field: write it if it is unset (input then required, fails
    # closed), or if the caller opted to overwrite AND supplied input for THAT
    # field. A configured field the caller did not touch is preserved untouched,
    # even when --overwrite-support-settings is set for the other field.
    write_owner = (not state["ownerConfigured"]) or (overwrite and owner_input)
    write_automated = ((not state["automatedUserConfigured"])
                       or (overwrite and automated_input))

    if not write_owner and not write_automated:
        ss["action"] = "preserved-existing"
        ss["ownerAction"] = "preserved"
        ss["automatedUserAction"] = "preserved"
        # Nothing written: omit all Support-Settings fields so they merge-preserve.
        _strip_unwritten_support_fields(records, {})
        return

    # Resolve the authenticated user once if opted in; used only for fields
    # being written.
    auth_resolved = None
    if args.use_authenticated_user:
        auth_resolved = query_active_user(session_id, instance_url,
                                          auth_username)
        if not auth_resolved:
            fail(f"The authenticated user '{auth_username}' did not resolve as "
                 f"an active user (unexpected).")

    applied = {}

    # ---- Default Case Owner ----
    if not write_owner:
        ss["ownerAction"] = "preserved"
    elif auth_resolved is not None:
        set_child_text(records, "defaultCaseOwner", auth_resolved)
        set_child_text(records, "defaultCaseOwnerType", "User")
        applied["defaultCaseOwner"] = auth_resolved
        applied["defaultCaseOwnerType"] = "User"
        ss["ownerAction"] = "set-from-authenticated-user"
    else:
        owner_type = args.owner_type or desired.get("defaultCaseOwnerType")
        owner_value = args.owner_value or desired.get("defaultCaseOwner")
        if not (owner_type or owner_value):
            fail("Default Case Owner is not configured in this org and none was "
                 "provided. Ask the user for the Default Case Owner type (User "
                 "or Queue) and value, then pass --owner-type/--owner-value (or "
                 "--use-authenticated-user if the user asked to use the "
                 "authenticated user).")
        resolved_owner, resolved_owner_type = resolve_owner(
            session_id, instance_url, owner_value, owner_type)
        set_child_text(records, "defaultCaseOwner", resolved_owner)
        set_child_text(records, "defaultCaseOwnerType", resolved_owner_type)
        applied["defaultCaseOwner"] = resolved_owner
        applied["defaultCaseOwnerType"] = resolved_owner_type
        ss["ownerAction"] = ("overwrote-existing" if state["ownerConfigured"]
                             else "set-from-input")

    # ---- Automated Case User ----
    if not write_automated:
        ss["automatedUserAction"] = "preserved"
    elif auth_resolved is not None:
        _clear_automated_user_fields(records)
        set_child_text(records, "defaultCaseUser", auth_resolved)
        set_child_text(records, "useSystemUserAsDefaultCaseUser", "false")
        applied["defaultCaseUser"] = auth_resolved
        applied["useSystemUserAsDefaultCaseUser"] = False
        ss["automatedUserAction"] = "set-from-authenticated-user"
    else:
        automated_type = args.automated_type
        automated_value = args.automated_value or desired.get("defaultCaseUser")
        system_email = args.system_user_email or desired.get("systemUserEmail")
        # Infer automated type from the input file if not given via flag.
        if automated_type is None:
            if desired.get("useSystemUserAsDefaultCaseUser") is True:
                automated_type = "System"
            elif desired.get("defaultCaseUser"):
                automated_type = "User"
        if automated_type is None:
            fail("Automated Case User is not configured in this org and none "
                 "was provided. Ask the user whether it should be a specific "
                 "User (and the username) or System, then pass --automated-type "
                 "User --automated-value <username> or --automated-type System "
                 "(or --use-authenticated-user).")
        auto_fields, auto_kind = resolve_automated_user(
            session_id, instance_url, automated_type, automated_value,
            system_email)
        _clear_automated_user_fields(records)
        for f, v in auto_fields.items():
            text = "true" if v is True else ("false" if v is False else str(v))
            set_child_text(records, f, text)
            applied[f] = v
        ss["automatedUserKind"] = auto_kind
        ss["automatedUserAction"] = (
            "overwrote-existing" if state["automatedUserConfigured"]
            else "set-from-input")

    # Roll the two per-field actions up into a single backward-compatible
    # `action` for the summary.
    actions = {ss.get("ownerAction"), ss.get("automatedUserAction")}
    if actions <= {"preserved"}:
        ss["action"] = "preserved-existing"
    elif "overwrote-existing" in actions:
        ss["action"] = "overwrote-existing"
    elif actions <= {"set-from-authenticated-user", "preserved"}:
        ss["action"] = "set-from-authenticated-user"
    else:
        ss["action"] = "set-from-input"

    if applied:
        ss["applied"] = applied
        summary["phaseA"].update(applied)

    # Any Support-Settings field NOT written this run must be omitted from the
    # payload (preserved via field-level merge) rather than resent verbatim.
    _strip_unwritten_support_fields(records, applied)


def enforce_production_gate(session_id, instance_url, confirm_production,
                            summary):
    """Fail closed on a PRODUCTION org unless --confirm-production is passed.

    Email-to-Case is a permanent, org-wide change (enableEmailToCase cannot be
    turned back off), so before mutating a production org we require an explicit
    opt-in. Sandboxes, scratch orgs, and trials deploy without confirmation.
    Records what it found in `summary['org']` so the caller sees the verdict."""
    is_sandbox, org_type, is_trial = query_org_info(session_id, instance_url)
    # A production org is a non-sandbox, non-trial org. If we can't read the
    # Organization row (is_sandbox is None), treat it as production and require
    # confirmation — fail closed rather than silently mutating an unknown org.
    is_production = (is_sandbox is False and not is_trial)
    unknown = is_sandbox is None
    summary["orgInfo"] = {"isSandbox": is_sandbox, "organizationType": org_type,
                          "isTrial": is_trial, "isProduction": is_production}
    if (is_production or unknown) and not confirm_production:
        detail = (f"organizationType={org_type}, isSandbox={is_sandbox}, "
                  f"isTrial={is_trial}")
        if unknown:
            fail("Could not determine whether this is a production org (the "
                 "Organization row was not readable). Refusing to mutate an "
                 "org of unknown type. If you are certain this is safe, re-run "
                 "with --confirm-production. "
                 "Enabling Email-to-Case is a permanent org-wide change.")
        fail(f"Target org appears to be PRODUCTION ({detail}). Enabling "
             "Email-to-Case is a permanent, org-wide change. Confirm with the "
             "user that they want to configure Email-to-Case on this "
             "production org, then re-run with --confirm-production. Sandboxes "
             "and trials do not require this flag.")


def verify_cases(session_id, instance_url, supplied_email):
    """Prove inbound email created Cases: query Case (Origin='Email', optionally
    a SuppliedEmail, within the last 3 days) and the linked incoming
    EmailMessage rows. Prints a JSON evidence summary and exits non-zero when no
    matching Case (or no linked incoming email) is found — a deploy landing is
    not proof; a Case with its incoming EmailMessage is."""
    cases = query_email_cases(session_id, instance_url, supplied_email)
    case_ids = [c["Id"] for c in cases if c.get("Id")]
    messages = query_incoming_email_messages(session_id, instance_url, case_ids)
    parent_ids_with_msg = {m.get("ParentId") for m in messages}
    result = {
        "mode": "verify-cases",
        "org": instance_url,
        "filter": {"suppliedEmail": supplied_email, "window": "LAST_N_DAYS:3"},
        "caseCount": len(cases),
        "cases": [
            {"caseNumber": c.get("CaseNumber"), "id": c.get("Id"),
             "origin": c.get("Origin"), "suppliedEmail": c.get("SuppliedEmail"),
             "subject": c.get("Subject"), "status": c.get("Status"),
             "createdDate": c.get("CreatedDate"),
             "hasIncomingEmailMessage": c.get("Id") in parent_ids_with_msg}
            for c in cases],
        "incomingEmailMessageCount": len(messages),
    }
    # Proof requires at least one Email-origin Case that has a linked incoming
    # EmailMessage. A Case with no incoming message (or no Case at all) is not
    # proof that the round-trip worked.
    proven = any(c.get("Id") in parent_ids_with_msg for c in cases)
    result["proven"] = proven
    print(json.dumps(result, indent=2, sort_keys=True))
    if not proven:
        if not cases:
            fail("No Cases with Origin='Email' in the last 3 days matched"
                 + (f" SuppliedEmail={supplied_email}" if supplied_email else "")
                 + ". The inbound email may not have arrived yet, the routing "
                 "address may not be verified, the test email may be older than "
                 "the 3-day window, or the sender differs. "
                 "Confirm the user actually sent the test email, wait a moment, "
                 "and re-run --verify-cases.")
        fail("Found Email-origin Case(s) but none has a linked incoming "
             "EmailMessage (Incoming=true). The Case may have been created "
             "another way. Re-run once the inbound email has been processed.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--target-org", required=True,
                    help="sf CLI alias/username of the target org")
    ap.add_argument("--input", default=None,
                    help="Path to the CaseSettings source file to apply. "
                         "Required for the write path; not needed for "
                         "--verify-cases (a read-only proof step).")
    ap.add_argument("--routing-email", action="append", default=[],
                    metavar="EMAIL",
                    help="Customer-facing email for a routing address. Repeat "
                         "once per routing address, in the order they appear "
                         "in --input. Required if --input declares any "
                         "routing addresses.")
    # --- Default Case Owner (User or Queue) ---
    ap.add_argument("--owner-type", choices=sorted(VALID_OWNER_TYPES),
                    default=None,
                    help="Default Case Owner type: User or Queue. Required when "
                         "support settings are not yet configured (unless "
                         "--use-authenticated-user). Falls back to the input "
                         "file's defaultCaseOwnerType.")
    ap.add_argument("--owner-value", default=None,
                    help="Default Case Owner value: an active Username (for "
                         "--owner-type User) or a Queue DeveloperName (for "
                         "Queue). Validated against the org; the script fails "
                         "if it is not a real active user / queue.")
    # --- Automated Case User (User or System) ---
    ap.add_argument("--automated-type", choices=sorted(VALID_AUTOMATED_TYPES),
                    default=None,
                    help="Automated Case User type: User or System. System "
                         "uses the org's automated process user (no value "
                         "needed). Required when support settings are not yet "
                         "configured (unless --use-authenticated-user).")
    ap.add_argument("--automated-value", default=None,
                    help="Automated Case User username (for --automated-type "
                         "User). Not needed for System. Validated against the "
                         "org.")
    ap.add_argument("--system-user-email", default=None,
                    help="Email for the automated process user, used with "
                         "--automated-type System when the org's automated "
                         "case user does not exist yet.")
    # --- Explicit opt-ins ---
    ap.add_argument("--use-authenticated-user", action="store_true",
                    help="Only when the user running the skill explicitly asks: "
                         "use the authenticated CLI user as both Default Case "
                         "Owner (User) and Automated Case User. Never assumed.")
    ap.add_argument("--overwrite-support-settings", action="store_true",
                    help="Overwrite an already-configured Default Case Owner or "
                         "Automated Case User. Scoped per field: only the "
                         "field(s) you also supply new input for are rewritten; "
                         "a configured field you don't touch stays preserved. "
                         "Without this, existing support settings are preserved.")
    ap.add_argument("--verify-only", action="store_true",
                    help="Read and print current settings without writing")
    # --- Production-org safety gate ---
    ap.add_argument("--confirm-production", action="store_true",
                    help="Confirm you intend to configure Email-to-Case on a "
                         "PRODUCTION org. Enabling Email-to-Case is permanent "
                         "and org-wide; without this flag the script refuses to "
                         "mutate a production org. Sandboxes and trials do not "
                         "need it.")
    # --- Act 3: prove inbound email created Cases (read-only) ---
    ap.add_argument("--verify-cases", action="store_true",
                    help="Read-only proof step: after the user has verified the "
                         "routing address and sent a test email, query the org "
                         "for Cases with Origin='Email' and their linked "
                         "incoming EmailMessage rows, and report the evidence. "
                         "Exits non-zero if no such Case is found.")
    ap.add_argument("--supplied-email", default=None, metavar="EMAIL",
                    help="With --verify-cases: narrow the Case query to this "
                         "sender address (Case.SuppliedEmail), e.g. the mailbox "
                         "the user sent the test email from.")
    ap.add_argument("--api-version", default=None,
                    metavar="X.Y",
                    help=f"Explicit Metadata API version override. When omitted, "
                         f"the version is derived from the org and floored at "
                         f"{DEFAULT_API_VERSION}. Set 68.0+ explicitly only to "
                         f"force a version (a botEmailDefinition binding needs "
                         f"v68.0+, but a v68+ org is picked up automatically).")
    args = ap.parse_args()

    global API_VERSION, _API_VERSION_EXPLICIT
    _API_VERSION_EXPLICIT = bool(args.api_version)
    if _API_VERSION_EXPLICIT:
        API_VERSION = args.api_version
    # else: get_session derives it from the org, floored at DEFAULT_API_VERSION.

    # --verify-cases is a standalone read-only proof step; it needs a session but
    # neither the input file nor a write. Handle it before parsing the input so
    # it works even without a source file on hand.
    if args.verify_cases:
        session_id, _metadata_url, instance_url, _auth = get_session(
            args.target_org)
        verify_cases(session_id, instance_url, args.supplied_email)
        return

    if not args.input:
        fail("--input <CaseSettings source file> is required to apply or verify "
             "settings. (It is only optional for the read-only --verify-cases "
             "proof step.)")

    desired = parse_input(args.input)
    session_id, metadata_url, instance_url, auth_username = get_session(
        args.target_org)

    if args.verify_only:
        records = read_case_settings(session_id, metadata_url)
        print(json.dumps(elem_to_value(records), indent=2, sort_keys=True))
        return

    # Production-org safety gate: refuse to mutate a production org unless the
    # operator confirmed. Runs only on the write path (after --verify-only /
    # --verify-cases, which are read-only). summary is created below; capture the
    # verdict into a temporary and fold it in.
    _gate_summary = {}
    enforce_production_gate(session_id, instance_url, args.confirm_production,
                            _gate_summary)

    desired_e2c = desired.get("emailToCase") or {}
    desired_addrs = desired_e2c.get("routingAddresses")
    if desired_addrs and isinstance(desired_addrs, dict):
        desired_addrs = [desired_addrs]

    # Routing emails must be supplied explicitly, one per declared address,
    # so no placeholder from the input file ever reaches the org.
    if desired_addrs:
        if len(args.routing_email) != len(desired_addrs):
            fail(f"--input declares {len(desired_addrs)} routing address(es) "
                 f"but {len(args.routing_email)} --routing-email value(s) were "
                 f"given. Provide exactly one --routing-email per address, in "
                 f"order.")

    summary = {"org": instance_url, "phaseA": {}, "phaseB": [],
               "supportSettings": {}}
    summary["orgInfo"] = _gate_summary.get("orgInfo")
    summary["apiVersion"] = API_VERSION

    # ---- Phase A: prerequisites + emailToCase toggles (NOT addresses) ----
    # Read the current CaseSettings record, merge the desired toggles / Support
    # Settings into it, and write it back. Writing the COMPLETE emailToCase block
    # is what actually provisions the org's On-Demand Email-to-Case email-service
    # infrastructure: a minimal field-level patch that just flips
    # enableOnDemandEmailToCase true does NOT trigger provisioning, so the routing
    # address in Phase B then has nothing to bind to ("We couldn't save your
    # routing address... custom email services named EmailToCase").
    #
    # No Chatter prerequisite: update_case_settings sends ONLY the top-level
    # fields this skill owns (KEEP_TOP_LEVEL_FIELDS) and strips the rest, so the
    # platform never re-validates unrelated top-level Case config (e.g. Case Feed,
    # whose re-validation would require Chatter). Stripped fields keep their
    # current org value via field-level merge. We still read the record first so
    # the emailToCase block we send carries the platform's existing children
    # (needed for provisioning) alongside our toggles.
    records = read_case_settings(session_id, metadata_url)
    initial_value = elem_to_value(records)
    state = support_settings_state(initial_value)
    # Count the addresses the org had BEFORE we touched anything. The
    # preservation guard baselines against this, not against the post-Phase-A
    # read: Phase A rewrites the whole emailToCase block, so a read-only field
    # surviving on a carried-over address would drop it THERE, and a guard that
    # re-reads after Phase A would see the already-shrunken collection and pass.
    initial_addr_count = _count_addresses(initial_value)

    # Support Settings (Default Case Owner + Automated Case User): preserve what
    # the org already has unless the caller explicitly opts to overwrite. The
    # platform returns these fields null when an admin has not set them, so a
    # null read is a reliable "not configured" signal. Modifies `records` in place.
    apply_support_settings(records, args, desired, session_id, instance_url,
                           auth_username, state, summary)

    # Merge any other top-level scalar toggle from the input (e.g.
    # enableDraftEmails) into the record. Nested/list values are skipped here —
    # only emailToCase (its own block) and the owner fields above are structured;
    # everything else at the top level is a scalar toggle. (Fields not in
    # KEEP_TOP_LEVEL_FIELDS are stripped at write time regardless.)
    for key, val in desired.items():
        if key in HANDLED_TOP_LEVEL or isinstance(val, (dict, list)):
            continue
        text = "true" if val is True else ("false" if val is False else str(val))
        set_child_text(records, key, text)
        summary["phaseA"][key] = val

    # Merge the emailToCase toggles (NOT routingAddresses) into the existing
    # emailToCase block read from the org.
    e2c_el = records.find(qn("emailToCase"))
    if e2c_el is None:
        e2c_el = ET.SubElement(records, qn("emailToCase"))
    for key, val in desired_e2c.items():
        if key == "routingAddresses":
            continue  # phase B
        text = "true" if val is True else ("false" if val is False else str(val))
        set_child_text(e2c_el, key, text)
        summary["phaseA"][f"emailToCase.{key}"] = val

    update_case_settings(session_id, metadata_url, records)

    # ---- Phase B: routing addresses, one call after toggles are live ----
    if desired_addrs:
        # Substitute the user-supplied email into each address (positional). The
        # OPTIONAL per-address Default Case Owner is validated later, only for
        # addresses that are actually new (see the build loop) — validating a
        # duplicate that is skipped as already_exists would waste an org round-trip.
        for addr, email in zip(desired_addrs, args.routing_email):
            addr["emailAddress"] = email
        # Re-read the record (now that Phase A's toggles are live and the
        # email-service infrastructure is provisioned) and add the new
        # address(es) to the emailToCase block. update_case_settings again
        # strips top-level fields we don't own, so only emailToCase (+ the fields
        # we set) is written. The routingAddresses collection is REPLACED (not
        # field-merged) on update, so the write must carry the existing addresses
        # alongside the new ones.
        #
        # ORDERING IS LOAD-BEARING: when a
        # newly-added routingAddresses element is placed AFTER the existing,
        # already-provisioned ones, the platform DROPS an existing address. When
        # the new address(es) come FIRST and the existing ones LAST, every
        # address is preserved. This held across writes with the platform-managed
        # read-only fields (emailServicesAddress/isVerified) stripped, kept, and
        # kept — so ordering, not those fields, is the deciding factor. We
        # therefore build the new addresses first, then re-append the existing
        # ones after them.
        records = read_case_settings(session_id, metadata_url)
        existing_names, existing_emails = existing_address_keys(
            elem_to_value(records))
        e2c_el = records.find(qn("emailToCase"))
        if e2c_el is None:
            e2c_el = ET.SubElement(records, qn("emailToCase"))
        # Detach the existing address elements so the new ones can be inserted
        # ahead of them; they are re-appended (unchanged) afterwards.
        existing_ra_elements = e2c_el.findall(qn("routingAddresses"))
        for ra in existing_ra_elements:
            e2c_el.remove(ra)
        # Build the new addresses FIRST (skip any that already exist by
        # name/email — those stay only as carried-over existing elements).
        added = []
        for i, addr in enumerate(desired_addrs, 1):
            name = addr.get("routingName")
            email = addr.get("emailAddress")
            if name in existing_names or (email and email in existing_emails):
                summary["phaseB"].append({"routingName": name,
                                          "emailAddress": email,
                                          "status": "already_exists"})
                continue
            # Validate the OPTIONAL per-address Default Case Owner against the org
            # now that we know this address is genuinely new.
            resolve_address_case_owner(session_id, instance_url, addr,
                                       f"routingAddresses[{i}]")
            build_address_element(e2c_el, addr)
            added.append(addr)
            summary["phaseB"].append({"routingName": name,
                                      "emailAddress": email,
                                      "status": "created"})
        # Re-append the existing addresses AFTER the new ones (see ORDERING note).
        for ra in existing_ra_elements:
            e2c_el.append(ra)
        if added:
            update_case_settings(session_id, metadata_url, records)

    # ---- Verify ----
    after = elem_to_value(read_case_settings(session_id, metadata_url))
    after_e2c = after.get("emailToCase") or {}

    # Preservation guard (runtime safety net): every address the org had before
    # this run, plus every address we newly created, must still be present. A
    # shortfall means an updateMetadata call REPLACED the routingAddresses
    # collection and dropped an existing address. Baseline against
    # initial_addr_count — the count from the very first read, before Phase A
    # touched the block — so this catches a drop in Phase A as well as Phase B.
    # Phase B orders new addresses before existing ones to prevent the known
    # ordering-driven drop; this guard backstops any residual/unknown drop.
    created_count = sum(1 for entry in summary["phaseB"]
                        if entry.get("status") == "created")
    expected_count = initial_addr_count + created_count
    actual_count = _count_addresses(after)
    if actual_count < expected_count:
        fail(
            f"Routing-address write did not preserve existing addresses: "
            f"expected at least {expected_count} ({initial_addr_count} already "
            f"in the org + {created_count} newly created), but the org now has "
            f"{actual_count}. An updateMetadata call replaced the "
            f"routingAddresses collection and dropped an existing address. No "
            f"further changes were made; re-run after confirming with the skill "
            f"maintainer.")
    verified = {
        "enableEmailToCase": after_e2c.get("enableEmailToCase"),
        "enableOnDemandEmailToCase": after_e2c.get("enableOnDemandEmailToCase"),
        "routingAddressCount": _count_addresses(after),
    }
    # Echo back every emailToCase toggle and top-level toggle the input set, so
    # the caller can confirm each requested flag actually landed in the org.
    for key in desired_e2c:
        if key == "routingAddresses":
            continue
        verified[f"emailToCase.{key}"] = after_e2c.get(key)
    for key, val in desired.items():
        if key in HANDLED_TOP_LEVEL or isinstance(val, (dict, list)):
            continue
        verified[key] = after.get(key)
    # Echo the support-settings values now in the org so the caller can confirm
    # they were preserved (or set) as intended.
    for field in SUPPORT_SETTINGS_FIELDS:
        verified[field] = after.get(field)
    summary["verified"] = verified
    print(json.dumps(summary, indent=2, sort_keys=True))


def _count_addresses(value):
    e2c = value.get("emailToCase") or {}
    addrs = e2c.get("routingAddresses")
    if addrs is None:
        return 0
    return len(addrs) if isinstance(addrs, list) else 1


if __name__ == "__main__":
    main()
