"""Tooling + Data REST client scaffolding with security-critical primitives.

This module ships the HTTP primitives used by every REST-path caller in the
skill. Two security invariants are enforced here and must not be bypassed:

the Authorization header is STRIPPED from any cross-host redirect.
Python's default HTTPRedirectHandler blindly forwards all request headers
(including Authorization) to the redirect target. A compromised or
attacker-controlled edge that returns a 302 to an arbitrary host would
otherwise receive the bearer token. We subclass HTTPRedirectHandler to
strip Authorization whenever the redirect target hostname differs from
the original. Callers MUST use `build_opener()` — never `urllib.request.
urlopen` directly, which wires the default redirect handler.

access tokens MUST NEVER appear in exception strings, tracebacks,
or logged output. `redact_error(exc)` returns a safe string representation
with `Authorization: Bearer ...` scrubbed. Every `except` that surfaces
HTTP / subprocess error text runs the text through `redact_error` first.
Never call `log.exception()` on an object that carries request headers.
"""
from __future__ import annotations

import email.utils
import functools
import json
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Tuple


# stdlib logger for transient-HTTP backoff breadcrumbs. The skill has
# no global logging config — we emit at DEBUG and leave handler/level wiring
# to callers. Absent any config, Python's "last-resort" handler suppresses
# DEBUG records, so this is a no-op in production until someone enables it.
logger = logging.getLogger(__name__)


class RestClientError(RuntimeError):
    """REST request failed — always constructed with a redacted message."""


# -----------------------------------------------------------------------------
# error redaction
# -----------------------------------------------------------------------------
# Three patterns cover the bulk of token-leakage surfaces:
# 1. `Authorization: Bearer <token>` in any string context (header echo,
# exception repr, stringified HTTP error).
# 2. `accessToken=<token>` / `access_token=<token>` in URL-encoded bodies
# or query strings (`sf org display` errors sometimes echo these).
# 3. `"accessToken":"<token>"` or `"access_token":"<token>"` in JSON
# payload echoes.
#
# Regexes are intentionally permissive on the token character class
# (anything non-whitespace, non-quote, non-ampersand) — we'd rather
# over-redact than miss a token with an unexpected encoding.

_AUTH_HEADER_RE = re.compile(
    r"(Authorization\s*:\s*Bearer\s+)\S+",
    flags=re.IGNORECASE,
)
# Matches access[_]?Token=<value> in url-encoded form; stops at & or whitespace.
_ACCESS_TOKEN_QS_RE = re.compile(
    r"(access[_]?token\s*=\s*)[^&\s\"']+",
    flags=re.IGNORECASE,
)
# Matches "access[_]?Token":"<value>" in JSON; stops at closing quote.
_ACCESS_TOKEN_JSON_RE = re.compile(
    r"(\"access[_]?token\"\s*:\s*\")[^\"]*",
    flags=re.IGNORECASE,
)


def redact_text(text: str) -> str:
    """Scrub bearer tokens and accessToken values from arbitrary text.

    Pure function; no side effects. Used by `redact_error` and available
    for use on any raw response body / stderr string before it reaches
    a log or exception message.

    renamed from `_redact_text` to a public symbol so
    cross-module callers (sf_cli._redact_subprocess_stderr) import a stable
    name instead of reaching into a module-private. The `_redact_text`
    alias below is retained for backwards compatibility with any caller
    that still imports the underscore-prefixed form; it will be removed
    in a future batch once all callers migrate.
    """
    if not text:
        return text
    text = _AUTH_HEADER_RE.sub(r"\1<redacted>", text)
    text = _ACCESS_TOKEN_QS_RE.sub(r"\1<redacted>", text)
    text = _ACCESS_TOKEN_JSON_RE.sub(r'\1<redacted>', text)
    return text


# deprecated alias. Retained so existing tests and any lingering
# `from rest_client import _redact_text` imports keep working. New code
# MUST use `redact_text` (public). Planned removal in a follow-up batch
# once the codebase is clean.
_redact_text = redact_text


def redact_error(exc: BaseException) -> str:
    """Return a safe string representation of `exc`.

    guaranteed to:
      * include the exception type name (for triage)
      * include the exception message WITH bearer tokens scrubbed
      * NEVER include raw header collections, even if the exception carries them

    For HTTPError specifically, we do NOT call `exc.read()` — the caller is
    responsible for reading the body once (reading twice is usually a no-op
    but we avoid the extra I/O and any token embedded in the body is scrubbed
    at the caller via `redact_text` when it surfaces in the error message).
    """
    exc_type = type(exc).__name__
    try:
        raw = str(exc)
    except Exception:
        raw = "<unreprable>"
    return f"{exc_type}: {redact_text(raw)}"


# -----------------------------------------------------------------------------
# cross-host redirect strips Authorization
# -----------------------------------------------------------------------------


class StripAuthOnCrossHostRedirect(urllib.request.HTTPRedirectHandler):
    """Strip Authorization header on any cross-host redirect.

    Python's default HTTPRedirectHandler preserves request headers across
    301/302/303/307/308. When `instanceUrl` is the trusted origin and a
    redirect points at ANY other hostname, we treat the Authorization
    header as tainted and drop it before the follow-up request goes out.

    Hostname comparison is case-insensitive (DNS is case-insensitive).
    We compare `urlparse(...).hostname` — which strips port and userinfo
    — because a port change on the same host is NOT a credential-leak
    vector, but treating it as cross-host would break legitimate
    `:443` → bare-host redirects.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        orig_host = urllib.parse.urlparse(req.full_url).hostname
        new_host = urllib.parse.urlparse(newurl).hostname
        # Normalize for case-insensitive comparison. `None == None` is safe
        # (both malformed URLs treated as "same host" — urllib would fail
        # the follow-up anyway).
        same_host = (orig_host or "").lower() == (new_host or "").lower()

        if same_host:
            # Default behavior: preserve Authorization (same-host redirect is
            # standard practice; stripping would break legitimate OAuth flows).
            return super().redirect_request(req, fp, code, msg, headers, newurl)

        # cross-host redirect — build a NEW Request without any
        # Authorization header. We cannot mutate `req` in place because
        # urllib's default handler reuses it; callers that retain a reference
        # would observe the mutation.
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is None:
            return None
        # Authorization may have been set via add_header (lowercased internal
        # storage as "Authorization") or via unredirected_hdrs. Remove both.
        # Note: `Request.headers` stores header names in the form produced by
        # `.capitalize()` (so "Authorization" lands as "Authorization" since
        # .capitalize() leaves single-word strings unchanged at the first
        # letter — but we defensively pop both casings).
        for hdr_name in list(new_req.headers.keys()):
            if hdr_name.lower() == "authorization":
                new_req.headers.pop(hdr_name, None)
        for hdr_name in list(new_req.unredirected_hdrs.keys()):
            if hdr_name.lower() == "authorization":
                new_req.unredirected_hdrs.pop(hdr_name, None)
        return new_req


def build_opener() -> urllib.request.OpenerDirector:
    """Return an OpenerDirector wired with StripAuthOnCrossHostRedirect.

    every REST call in this module must go through an opener built
    here. Direct use of `urllib.request.urlopen(...)` bypasses the redirect
    handler and reintroduces the cross-host-token-leak vulnerability.
    """
    return urllib.request.build_opener(StripAuthOnCrossHostRedirect())


# -----------------------------------------------------------------------------
# 401 token refresh decorator + tooling/data query helpers
# -----------------------------------------------------------------------------
# Motivation: `sf org display` returns an access token with a short TTL
# (typically 15min–2h). A pipeline run with many Flow / Tooling fetches can
# exceed TTL. Without a refresh path the pipeline fails mid-run with a raw
# 401 and the user has to re-run from scratch.
#
# Design: `retry_on_401` is a decorator-factory that takes a `refresh_fn`
# closure. On 401 (HTTP status OR body contains INVALID_SESSION_ID) it
# invokes `refresh_fn()`, retries the wrapped call ONCE, and surfaces the
# original error if the retry also 401s. The refresh closure is passed
# per-call rather than stored globally so the client stays stateless and
# testable — each caller wires its own `lambda: run_sf("org_display", ...)`.
#
# Redaction: any error text that surfaces from this decorator runs through
# `redact_error` / `redact_text` . The 401 body is read once and
# scrubbed before being used for INVALID_SESSION_ID detection — we never
# log or re-raise raw bytes from the wire.

_INVALID_SESSION_MARKER = "INVALID_SESSION_ID"


_ERROR_ENVELOPE_KEYS = ("errors", "error", "errorDetails", "messages")


def _body_indicates_invalid_session(body: Any) -> bool:
    """detect `INVALID_SESSION_ID` in a parsed or raw response body.

    Some SF endpoints (notably a few Tooling paths) return HTTP 200 with an
    error body rather than 401. The documented SF error shape is a list of
    `{"errorCode": "INVALID_SESSION_ID", "message": "..."}` dicts at the
    body root.

    BUGFIX (2026-05-03): the prior implementation recursed into ALL
    `dict.values()` and fell back to substring-matching the stringified
    form. Tooling Query responses for ApexClass include a `records` list
    whose `Body` field is the raw Apex source — which can legitimately
    contain the literal string `INVALID_SESSION_ID` (as an errorCode
    constant referenced by catch/rethrow code, e.g. `XCSF_FlowFaultMessage`
    and `SkillRulesMatchAction` in the real-org fixture). That tripped the
    value-walk and the substring fallback, misclassifying a 200 OK success
    response as an auth failure and forcing a spurious
    `INVALID_SESSION_ID after refresh` envelope into Wave B's `_unresolved`.

    The tightened rules:
      1. Top-level list/tuple: the SF error envelope — recurse (one level
         is enough in practice, but recursion is safe because list items
         are error dicts, not data rows with Apex bodies).
      2. Dict: a positive match requires `errorCode == INVALID_SESSION_ID`
         at THIS level, OR recursion into a well-known error-envelope key
         (`errors`, `error`, `errorDetails`, `messages`). Data keys like
         `records`, `Body`, `attributes` are NEVER walked — that was the
         bug. Typos / shape variants still surface through the
         error-envelope keys, which is the real world observed-shape set.
      3. Top-level raw str/bytes: an unparsed error body. A substring
         match here is still safe because this helper is only called on
         the TOP-LEVEL parsed response (never on a field inside a success
         dict), so a raw-string body means SF literally returned text
         rather than JSON — in which case substring match is the best
         we can do.
      4. Anything else (int, float, None, other types): not an error
         shape. Return False.
    """
    if body is None:
        return False
    if isinstance(body, (list, tuple)):
        return any(_body_indicates_invalid_session(item) for item in body)
    if isinstance(body, dict):
        code = body.get("errorCode") or body.get("error_code")
        if isinstance(code, str) and _INVALID_SESSION_MARKER in code:
            return True
        # Only recurse into known error-envelope keys. Walking arbitrary
        # values misclassifies legitimate success payloads whose data
        # fields (e.g. ApexClass.Body) happen to contain the string
        # `INVALID_SESSION_ID`.
        for key in _ERROR_ENVELOPE_KEYS:
            if key in body and _body_indicates_invalid_session(body[key]):
                return True
        return False
    if isinstance(body, (str, bytes)):
        text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
        return _INVALID_SESSION_MARKER in text
    return False


class _InvalidSessionSignal(Exception):
    """Internal-only: tunnel INVALID_SESSION_ID-in-200-body through retry_on_401.

    Never escapes this module — the decorator catches it, refreshes, retries,
    and on a second failure surfaces a RestClientError (redacted).
    """


def _is_invalid_session_403(exc: urllib.error.HTTPError) -> bool:
    """detect HTTP 403 + `INVALID_SESSION_ID` in body.

    Some SF endpoints respond to an expired session with `403 Forbidden`
    (body: `{"errorCode": "INVALID_SESSION_ID"}`) instead of 401. We treat
    that shape as auth-refresh-triggering just like 401. Any OTHER 403
    (permission denied, IP restriction, etc.) propagates unchanged — we
    don't burn a refresh on a non-auth 403.

    Reading `.read()` on an HTTPError is a one-shot — callers that surface
    this exception must not re-read the body. For our retry path this is
    fine: the decorator consumes the body once to decide, then discards
    the exception after retry.
    """
    if exc.code != 403:
        return False
    try:
        body = exc.read()
    except Exception:
        return False
    if not body:
        return False
    try:
        text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
    except Exception:
        return False
    return _INVALID_SESSION_MARKER in text


def retry_on_401(
    refresh_fn: Callable[[], Tuple[str, str]],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: retry a REST call ONCE after refreshing the session token.

    detects three auth-failure shapes:
      1. `urllib.error.HTTPError` with `code == 401`
      2. `urllib.error.HTTPError` with `code == 403` AND body contains
         `INVALID_SESSION_ID` (some SF endpoints return 403 for
         expired sessions; non-auth 403 is NOT treated as refreshable).
      3. HTTP 200 with response body containing `INVALID_SESSION_ID` —
         callers signal this by raising `_InvalidSessionSignal`; the
         helpers below do the body inspection before returning.

     (REMEDIATE): the retry contract is documented and enforced here:
    `refresh_fn()` returns `(instance_url, access_token)` and the caller
    MUST thread those fresh credentials into the NEXT invocation of the
    wrapped callable. See `tooling_query` / `data_query`, which implement
    this via the `creds_provider` closure pattern (Option A). The previous
    design captured credentials in a closure at call time — refresh
    returned fresh creds, the wrapped closure kept using stale ones, and
    the retry 401'd again. That's the defect. `retry_on_401` itself
    is still credential-agnostic; the invariant lives in the caller.

    If the retry ALSO fails (401 / 403+INVALID_SESSION_ID / INVALID_SESSION_ID),
    the ORIGINAL error is re-raised (wrapped as `RestClientError` with a
    redacted message) — not the retry's error. Rationale: the user sees
    the first-attempt context (what call failed) rather than a downstream
    artefact of the retry path.

    Non-auth errors (500, 403 without INVALID_SESSION_ID, network timeout,
    etc.) propagate unchanged — refresh is NOT attempted.
    """

    def _is_auth_http_error(exc: urllib.error.HTTPError) -> bool:
        # 401 is the classic shape; 403+INVALID_SESSION_ID is a
        # variant observed on some SF endpoints. All other 4xx/5xx
        # propagate without refresh.
        if exc.code == 401:
            return True
        if _is_invalid_session_403(exc):
            return True
        return False

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except urllib.error.HTTPError as first_exc:
                if not _is_auth_http_error(first_exc):
                    raise
                # auth-failure path — refresh and retry once.
                try:
                    refresh_fn()
                except Exception as refresh_exc:
                    # Refresh itself failed — surface the REFRESH error so
                    # the user knows they need to re-auth, but keep token
                    # redaction on the message.
                    raise RestClientError(
                        f"token refresh failed after auth error: {redact_error(refresh_exc)}"
                    ) from None
                try:
                    return fn(*args, **kwargs)
                except urllib.error.HTTPError as retry_exc:
                    if _is_auth_http_error(retry_exc):
                        raise RestClientError(
                            f"auth error after refresh (original): {redact_error(first_exc)}"
                        ) from None
                    raise
                except _InvalidSessionSignal:
                    raise RestClientError(
                        f"INVALID_SESSION_ID after refresh (original): "
                        f"{redact_error(first_exc)}"
                    ) from None
            except _InvalidSessionSignal as first_sig:
                # body-path INVALID_SESSION_ID — refresh and retry once.
                try:
                    refresh_fn()
                except Exception as refresh_exc:
                    raise RestClientError(
                        f"token refresh failed after INVALID_SESSION_ID: "
                        f"{redact_error(refresh_exc)}"
                    ) from None
                try:
                    return fn(*args, **kwargs)
                except urllib.error.HTTPError as retry_exc:
                    if _is_auth_http_error(retry_exc):
                        raise RestClientError(
                            f"auth error after refresh (original INVALID_SESSION_ID): "
                            f"{redact_error(first_sig)}"
                        ) from None
                    raise
                except _InvalidSessionSignal:
                    raise RestClientError(
                        f"INVALID_SESSION_ID after refresh: {redact_error(first_sig)}"
                    ) from None

        return wrapper

    return decorator


# -----------------------------------------------------------------------------
# transient HTTP (429/503) exponential backoff
# -----------------------------------------------------------------------------
# Motivation: SF REST endpoints occasionally return 429 (rate-limited) or
# 503 (service unavailable) during API-limit windows, planned maintenance,
# or transient edge hiccups. Without a retry the pipeline fails mid-run on
# what is almost always a recoverable condition. Three attempts with
# exponential backoff (1s → 2s → 4s, roughly — `base_delay * 2**attempt`)
# resolve the vast majority of transient blips without meaningfully
# extending happy-path latency.
#
# Scope (what this decorator does NOT do):
# * Not a 401 refresher — that's `retry_on_401`. The layering is:
# retry_on_401( retry_on_transient_http()( _query_once ) )
# so 429s retry first (inner), and a 401 surfacing through that layer
# triggers the outer refresh. The two concerns stay independent.
# * No jitter. Bounded to 3 attempts + short delays; adding jitter here
# would only matter if many callers burst-retried against the same
# endpoint, which is not the shape of this skill's traffic.
# * No retry on 5xx generally. Only 503 is retried because 500/502/504
# often indicate deterministic server-side failures where retrying
# won't help and we'd prefer to surface fast.
#
# Retry-After handling:
# * If the header is present and parses as a non-negative number of
# seconds OR an HTTP-date, we honor it — bounded below by base_delay *
# 2**attempt so a "Retry-After: 0" doesn't disarm the backoff.
# * Negative / malformed values fall back to the exponential schedule.
#
# Redaction: any HTTPError surfaced from the final failure goes through
# `redact_error` at the caller's message site (see `_query_once`'s wrapper
# chain). We do NOT stringify headers here — no `str(exc.headers)` or
# `resp.read()` debug dumps on retry. URL logging strips the query string.


def _parse_retry_after(raw: str | None) -> float | None:
    """Parse a Retry-After header value to seconds.

    Per RFC 9110 the value is either `delta-seconds` (non-negative int) or
    an HTTP-date. We accept floats too — some clients emit decimal seconds
    and the spec-strict int parse would silently lose them.

    Returns None for missing / malformed input; caller falls back to the
    exponential schedule.
    """
    if not raw:
        return None
    raw = raw.strip()
    try:
        secs = float(raw)
        if secs < 0:
            return None
        return secs
    except ValueError:
        pass
    # HTTP-date form. `parsedate_to_datetime` raises on malformed input on
    # 3.10+; wrap defensively.
    try:
        target = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if target is None:
        return None
    # Header expresses an absolute time; convert to a delta from now.
    now = time.time()
    delta = target.timestamp() - now
    if delta < 0:
        return 0.0
    return delta


def retry_on_transient_http(
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: retry on HTTP 429/503 up to `max_retries` times.

    on `urllib.error.HTTPError` with code in {429, 503}, sleep and
    retry. Any other exception (including 401 — let `retry_on_401`
    handle that, and any 5xx besides 503) propagates immediately.

    Retry semantics:
      * max_retries: number of retries AFTER the first attempt (default 3).
      * Total attempts = 1 + max_retries (default 4: 1 original + 3 retries).
      * Final attempt's exception propagates; no further retry.

    Delay per attempt = max(Retry-After-seconds, base_delay * 2**attempt).
    If Retry-After is absent or malformed, falls back to the exponential
    schedule. `attempt` is 0-indexed for the first retry (so the first
    sleep is base_delay * 1 = base_delay).

    Logs a DEBUG breadcrumb per retry via the module-level `logger`. No
    header values are logged — only the HTTP code + computed delay +
    attempt counter.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Total attempts = 1 original + max_retries retries. `attempt`
            # below is 0-indexed over the retry slots, which matches the
            # exponential formula base_delay * 2**attempt starting at
            # base_delay for attempt=0.
            for attempt in range(max_retries):
                try:
                    return fn(*args, **kwargs)
                except urllib.error.HTTPError as exc:
                    if exc.code not in (429, 503):
                        # Any other HTTP status (including 401) — out of
                        # scope for this decorator. Propagate so outer
                        # layers (retry_on_401) can handle it.
                        raise
                    retry_after_raw = None
                    try:
                        # `exc.headers` is a Message-like; .get tolerates
                        # the case where headers are absent on some
                        # synthesized HTTPErrors.
                        retry_after_raw = exc.headers.get("Retry-After") if exc.headers else None
                    except Exception:
                        retry_after_raw = None
                    hinted = _parse_retry_after(retry_after_raw)
                    expo = base_delay * (2 ** attempt)
                    delay = max(hinted, expo) if hinted is not None else expo
                    logger.debug(
                        "retry_on_transient_http: HTTP %d, sleeping %.2fs (attempt %d/%d)",
                        exc.code, delay, attempt + 1, max_retries,
                    )
                    time.sleep(delay)
                    continue
            # Final attempt — let any exception propagate directly. If
            # this attempt raises 429/503 the caller gets the HTTPError
            # unchanged (redaction happens at the wrapping call site).
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def _query_once(
    instance_url: str,
    token: str,
    path: str,
    soql: str,
) -> dict:
    """Single SOQL GET — reads body, checks for INVALID_SESSION_ID.

    the Salesforce REST Query + Tooling Query
    endpoints are GET-only with the SOQL passed as a urlencoded `q=`
    querystring. The prior POST-with-JSON-body shape returned HTTP 405
    ("Method Not Allowed") on every real-org run — confirmed by curl
    against a real org:

        GET  /services/data/v60.0/query/?q=<soql>  -> 200 OK
        POST /services/data/v60.0/query/           -> 405 Method Not Allowed

    We urlencode the SOQL (via `urllib.parse.urlencode({"q": soql})`)
    rather than string-concatenating so spaces, single quotes, commas,
    and parentheses in the query — all legal inside SOQL string
    literals — travel through the wire correctly. The JSON body and
    `Content-Type: application/json` header are dropped (GET carries
    no body; Content-Type with a bodyless GET is technically legal but
    meaningless and some edge proxies get irritated by it).

    uses `build_opener()` so cross-host redirects strip Authorization.
    any exception is surfaced with `redact_error`; raw body is run
    through `redact_text` before it reaches an exception message.
    signals `_InvalidSessionSignal` on 200-body-error so
    `retry_on_401` can refresh + retry.
    sets `Accept-Encoding: identity` to opt out of gzip. The
    responses here are small JSON payloads — gzip would add handling
    complexity (Content-Encoding detection + decompression) for zero
    measurable benefit. Explicit `identity` keeps the body-inspection
    path (INVALID_SESSION_ID detection) straightforward and testable.
    """
    # urlencode handles all SOQL-legal characters — spaces,
    # single quotes inside string literals, commas, parentheses. Hand-
    # rolled concatenation would have to escape each class separately.
    qs = urllib.parse.urlencode({"q": soql})
    url = f"{instance_url.rstrip('/')}{path}?{qs}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    # force identity encoding — no gzip.
    req.add_header("Accept-Encoding", "identity")

    opener = build_opener()
    try:
        with opener.open(req) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        # Bug D.1 fix: HTTPError.read() is one-shot. The default
        # `redact_error()` path stringifies just `HTTP Error 4xx: <reason>`
        # which loses the Salesforce error body — and that body is what
        # tells the operator WHY (e.g. INVALID_FIELD, MALFORMED_QUERY,
        # name-too-long, or a specific bad identifier). Pull the body
        # ONCE here, scrub it via redact_text, attach it to the exception
        # as `_response_body_preview`, and re-raise. Downstream callers
        # that surface `redact_error(exc)` keep their existing string
        # output; callers that want the body read it from the attribute.
        try:
            body = exc.read()
        except Exception:
            body = b""
        try:
            body_text = body.decode("utf-8", errors="replace")
        except Exception:
            body_text = ""
        # Cap at 500 chars — enough to carry a Salesforce error array
        # element with the offending name in it; small enough that
        # downstream contexts don't bloat. redact_text strips bearer
        # tokens defensively (body shouldn't contain one but cheaper to
        # always scrub than reason about it).
        exc._response_body_preview = redact_text(body_text)[:500]  # type: ignore[attr-defined]
        raise

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise RestClientError(
            f"malformed query response: {redact_error(e)}"
        ) from None

    # HTTP 200 + INVALID_SESSION_ID in body → tunnel up to the
    # decorator so it can refresh + retry.
    if _body_indicates_invalid_session(parsed):
        raise _InvalidSessionSignal(
            redact_text(json.dumps(parsed)[:500])
        )
    return parsed


# (REMEDIATE): credentials flow through a provider closure, not
# through function arguments that are captured once at decoration time.
#
# The previous design had a fatal defect:
#
# def tooling_query(instance_url, token, soql, *, on_401_refresh):
# @retry_on_401(on_401_refresh)
# def _call():
# return _query_once(instance_url, token, ...) # stale closure
# return _call()
#
# `refresh_fn()` returned `(new_url, new_token)` but those values were
# thrown away — the decorator only called `refresh_fn()` for its side
# effects, then re-invoked the same closure holding the ORIGINAL stale
# `instance_url` / `token`. Retry 401'd again. Feature was dead.
#
# Option A (taken): `tooling_query` / `data_query` accept a
# `creds_provider: Callable[[], Tuple[str, str]]` that is called EACH
# attempt. `refresh_fn` is responsible for mutating whatever state the
# provider reads from — typically a simple closure over a list. This
# keeps `retry_on_401` credential-agnostic and makes the contract
# ("refresh updates the source that `creds_provider` reads from")
# explicit at the caller site instead of implicit in the helper.
#
# Test: `RetryOn401CredentialRefreshIntegrationTests` in
# test_rest_client.py verifies that a real refresh carries fresh
# credentials into the retry call; the prior design fails that test.


def tooling_query(
    creds_provider: Callable[[], Tuple[str, str]],
    soql: str,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> dict:
    """GET a SOQL query against the Tooling API.

    `creds_provider()` is invoked on EACH attempt. `on_401_refresh`
    is responsible for updating whatever state the provider reads from
    before it returns — otherwise the retry would hit the same stale
    credentials and 401 again.

    `api_version` is a REQUIRED keyword-only arg.
    The prior hardcoded `v60.0` was the source of — real orgs
    run on v66 and expose fields v60 does not (confirmed empirically:
    `BotDefinition.Description` exists on v66, `INVALID_FIELD` on v60).
    Callers thread the version through from `main._derive_org_ids`, which
    reads it once from `sf org display --json`. Making the param REQUIRED
    (no default) surfaces a missed call-site as a TypeError at call time
    rather than a silent regression back to a stale pinned version.
    Shape is already enforced by `fs_guard.validate_api_version`
    (`^v[0-9]+\\.[0-9]+$`) at the caller.

    Stateless: both closures are passed per-call. Each caller owns the
    storage the refresh writes to (typically a small `list[tuple[str, str]]`
    cell).
    """
    path = f"/services/data/{api_version}/tooling/query/"

    # retry_on_transient_http is the INNER layer — 429/503 retries
    # happen first, and any 401 bubbling through triggers retry_on_401's
    # refresh path at the outer layer. Ordering matters: if transient
    # retry were outer, a 429 during a refresh retry would be mis-handled.
    @retry_on_401(on_401_refresh)
    @retry_on_transient_http()
    def _call() -> dict:
        # re-read creds on every attempt so refresh actually lands.
        instance_url, token = creds_provider()
        return _query_once(instance_url, token, path, soql)

    return _call()


def data_query(
    creds_provider: Callable[[], Tuple[str, str]],
    soql: str,
    *,
    api_version: str,
    on_401_refresh: Callable[[], Tuple[str, str]],
) -> dict:
    """GET a SOQL query against the Data API (non-Tooling).

    identical retry wiring to `tooling_query`, different URL path.
    `creds_provider` is invoked on every attempt so a refresh actually
    propagates fresh credentials into the retry.

    `api_version` is a REQUIRED keyword-only arg;
    see `tooling_query` for the rationale.
    """
    path = f"/services/data/{api_version}/query/"

    # see `tooling_query` for the decorator-ordering rationale.
    @retry_on_401(on_401_refresh)
    @retry_on_transient_http()
    def _call() -> dict:
        # re-read creds on every attempt so refresh actually lands.
        instance_url, token = creds_provider()
        return _query_once(instance_url, token, path, soql)

    return _call()


def static_creds(instance_url: str, token: str) -> Callable[[], Tuple[str, str]]:
    """Build a zero-state creds_provider that always returns the same pair.

    Convenience for callers that don't wire a refresh path — tests,
    single-shot scripts where a 401 is terminal. If the call 401s, the
    retry sees the same creds and fails again; this is correct behavior
    for an unrefreshable context (no point claiming otherwise).
    """
    def _provider() -> Tuple[str, str]:
        return instance_url, token
    return _provider
