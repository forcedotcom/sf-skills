"""Tests for  (cross-host redirect strips Authorization) and
 (redact_error scrubs bearer tokens).

adds: `retry_on_401` decorator + `tooling_query` / `data_query`
helpers. Tests cover both the HTTP-401 and the INVALID_SESSION_ID-in-body
code paths, as well as the non-auth-error propagation guarantee.
"""
from __future__ import annotations

import email.message
import email.utils
import io
import json
import time
import unittest
import unittest.mock as mock
import urllib.error
import urllib.request

from . import _bootstrap  # noqa: F401

import rest_client  # type: ignore


class RedirectHeaderStripTests(unittest.TestCase):
    """Authorization must be dropped on cross-host redirect."""

    def setUp(self) -> None:
        self.handler = rest_client.StripAuthOnCrossHostRedirect()
        # Minimal stand-in for the `fp` argument — the handler ignores it
        # except when constructing HTTPError on unsupported-scheme paths.
        self.fp = io.BytesIO(b"")
        # Headers are a Message-like; handler reads nothing from it for
        # the 302 path. An empty dict-like suffices.
        self.msg = {}

    def _make_request(self, url: str, auth: str = "Bearer tok123"):
        req = urllib.request.Request(url)
        if auth:
            req.add_header("Authorization", auth)
        return req

    def _has_authorization(self, req) -> bool:
        for k in list(req.headers.keys()) + list(req.unredirected_hdrs.keys()):
            if k.lower() == "authorization":
                return True
        return False

    def test_same_host_redirect_preserves_authorization(self):
        req = self._make_request("https://na1.salesforce.com/services/data/v60.0/query")
        new_req = self.handler.redirect_request(
            req, self.fp, 302, "Found", self.msg,
            "https://na1.salesforce.com/services/data/v60.0/query?page=2",
        )
        self.assertIsNotNone(new_req)
        self.assertTrue(
            self._has_authorization(new_req),
            "same-host redirect must preserve Authorization",
        )

    def test_cross_host_redirect_strips_authorization(self):
        req = self._make_request("https://na1.salesforce.com/services/data/v60.0/query")
        new_req = self.handler.redirect_request(
            req, self.fp, 302, "Found", self.msg,
            "https://attacker.example.com/steal",
        )
        self.assertIsNotNone(new_req)
        self.assertFalse(
            self._has_authorization(new_req),
            "cross-host redirect must strip Authorization ",
        )

    def test_downgrade_to_http_cross_host_strips(self):
        """A redirect from HTTPS→HTTP on a different host is the classic
        MITM bait. Authorization must not follow."""
        req = self._make_request("https://na1.salesforce.com/services/data/v60.0/query")
        new_req = self.handler.redirect_request(
            req, self.fp, 302, "Found", self.msg,
            "http://attacker.example.com/",
        )
        self.assertIsNotNone(new_req)
        self.assertFalse(self._has_authorization(new_req))

    def test_case_insensitive_host_match(self):
        """DNS is case-insensitive — `Foo.com` and `foo.com` are same host."""
        req = self._make_request("https://Foo.Salesforce.com/path")
        new_req = self.handler.redirect_request(
            req, self.fp, 302, "Found", self.msg,
            "https://foo.salesforce.com/other",
        )
        self.assertIsNotNone(new_req)
        self.assertTrue(self._has_authorization(new_req))

    def test_build_opener_wires_the_handler(self):
        opener = rest_client.build_opener()
        self.assertIsInstance(opener, urllib.request.OpenerDirector)
        installed = [
            h for h in opener.handlers
            if isinstance(h, rest_client.StripAuthOnCrossHostRedirect)
        ]
        self.assertEqual(
            len(installed), 1,
            "build_opener must install exactly one StripAuthOnCrossHostRedirect",
        )


class RedactErrorTests(unittest.TestCase):
    """redact_error must scrub bearer tokens from exception strings."""

    def test_bearer_token_redacted(self):
        # Scanner-inert placeholder — redactor only cares about the
        # `Authorization: Bearer ` prefix; the value is opaque `\S+`.
        raw = "Authorization: Bearer TESTONLY_HEADER.TESTONLY_PAYLOAD.TESTONLY_SIG"
        exc = RuntimeError(raw)
        out = rest_client.redact_error(exc)
        self.assertIn("<redacted>", out)
        self.assertNotIn("TESTONLY_HEADER", out)
        self.assertNotIn("TESTONLY_PAYLOAD", out)

    def test_bearer_token_case_insensitive(self):
        exc = RuntimeError("authorization: BEARER TESTONLY_BEARER_VALUE")
        out = rest_client.redact_error(exc)
        self.assertNotIn("TESTONLY_BEARER_VALUE", out)

    def test_access_token_querystring_redacted(self):
        exc = RuntimeError("POST /oauth/token accessToken=TESTONLY_TOKEN&foo=1")
        out = rest_client.redact_error(exc)
        self.assertNotIn("TESTONLY_TOKEN", out)
        self.assertIn("<redacted>", out)
        # The non-sensitive tail is preserved — handy for debugging.
        self.assertIn("foo=1", out)

    def test_access_token_snake_case_querystring_redacted(self):
        exc = RuntimeError("access_token=TESTONLY_SNAKE_TOKEN&other=ok")
        out = rest_client.redact_error(exc)
        self.assertNotIn("TESTONLY_SNAKE_TOKEN", out)
        self.assertIn("other=ok", out)

    def test_access_token_json_redacted(self):
        exc = RuntimeError('{"accessToken":"TESTONLY_JSON_TOKEN","status":0}')
        out = rest_client.redact_error(exc)
        self.assertNotIn("TESTONLY_JSON_TOKEN", out)
        self.assertIn("<redacted>", out)
        # Non-sensitive JSON preserved.
        self.assertIn("status", out)

    def test_access_token_json_snake_case_redacted(self):
        exc = RuntimeError('{"access_token":"tok.ABC"}')
        out = rest_client.redact_error(exc)
        self.assertNotIn("tok.ABC", out)

    def test_output_includes_exception_type(self):
        exc = ValueError("boring message")
        out = rest_client.redact_error(exc)
        self.assertTrue(out.startswith("ValueError:"))

    def test_empty_exception_safe(self):
        exc = RuntimeError("")
        out = rest_client.redact_error(exc)
        self.assertTrue(out.startswith("RuntimeError:"))

    def test_plain_message_unchanged(self):
        exc = RuntimeError("connection refused")
        out = rest_client.redact_error(exc)
        self.assertIn("connection refused", out)


class RedactTextPublicSymbolTests(unittest.TestCase):
    """`redact_text` is the public symbol; `_redact_text` stays as
    a deprecated alias for backwards compatibility.
    """

    def test_redact_text_importable_at_module_top(self):
        """Public name must be reachable via a plain `from` import — this
        is what sf_cli now relies on at module-top import time.
        """
        from rest_client import redact_text  # noqa: F401
        self.assertTrue(callable(redact_text))

    def test_redact_text_same_behavior_as_alias(self):
        """The deprecated alias must be bound to the same function object
        so behavior drift is impossible.
        """
        self.assertIs(rest_client._redact_text, rest_client.redact_text)

    def test_underscore_alias_still_works(self):
        """Backwards-compat: any lingering `from rest_client import
        _redact_text` must keep functioning until the alias is removed
        in a follow-up batch.
        """
        from rest_client import _redact_text  # noqa: F401
        out = _redact_text("Authorization: Bearer tokXYZ")
        self.assertIn("<redacted>", out)
        self.assertNotIn("tokXYZ", out)

    def test_public_redact_text_scrubs_bearer(self):
        out = rest_client.redact_text("Authorization: Bearer secrettok")
        self.assertNotIn("secrettok", out)
        self.assertIn("<redacted>", out)


def _make_http_error(code: int, body: bytes = b"") -> urllib.error.HTTPError:
    """Build a minimal HTTPError carrying `code` + `body`.

    We don't need a real socket — the decorator only reads `.code` and
    (optionally) the stringified form. Body is passed for parity with
    the wire.
    """
    return urllib.error.HTTPError(
        url="https://example.salesforce.com/x",
        code=code,
        msg="error",
        hdrs={},  # type: ignore[arg-type]
        fp=io.BytesIO(body),
    )


class RetryOn401Tests(unittest.TestCase):
    """decorator refreshes the token on 401 and retries once."""

    def test_401_then_success_calls_refresh_once(self):
        """Wrapped fn raises 401 first, succeeds on retry.

        refresh_fn MUST be called exactly once; wrapped fn returns normally.
        """
        call_count = {"n": 0}

        def wrapped():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise _make_http_error(401)
            return {"ok": True}

        refresh_calls = []

        def refresh():
            refresh_calls.append(1)
            return ("https://example.salesforce.com", "new_tok")

        decorated = rest_client.retry_on_401(refresh)(wrapped)
        result = decorated()

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(refresh_calls), 1, "refresh_fn must be called exactly once")
        self.assertEqual(call_count["n"], 2)

    def test_401_twice_reraises_with_original_context(self):
        """Second 401 → original 401 context surfaces (wrapped as RestClientError).

        refresh_fn still called only once (no infinite retry).
        """

        def wrapped():
            raise _make_http_error(401, body=b"session bad")

        refresh_calls = []

        def refresh():
            refresh_calls.append(1)
            return ("https://example.salesforce.com", "new_tok")

        decorated = rest_client.retry_on_401(refresh)(wrapped)
        with self.assertRaises(rest_client.RestClientError) as ctx:
            decorated()

        self.assertIn("auth error after refresh", str(ctx.exception))
        self.assertEqual(len(refresh_calls), 1, "refresh_fn must be called only once")

    def test_invalid_session_body_triggers_refresh(self):
        """INVALID_SESSION_ID signalled via body (HTTP 200) → refresh + retry."""
        call_count = {"n": 0}

        def wrapped():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise rest_client._InvalidSessionSignal("body had INVALID_SESSION_ID")
            return {"ok": True}

        refresh_calls = []

        def refresh():
            refresh_calls.append(1)
            return ("https://example.salesforce.com", "new_tok")

        decorated = rest_client.retry_on_401(refresh)(wrapped)
        result = decorated()

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(refresh_calls), 1)

    def test_non_auth_http_error_propagates_without_refresh(self):
        """500 → NO refresh, error propagates as-is."""

        def wrapped():
            raise _make_http_error(500)

        refresh_calls = []

        def refresh():
            refresh_calls.append(1)
            return ("https://example.salesforce.com", "new_tok")

        decorated = rest_client.retry_on_401(refresh)(wrapped)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            decorated()

        self.assertEqual(ctx.exception.code, 500)
        self.assertEqual(len(refresh_calls), 0, "500 must NOT trigger refresh")

    def test_retry_error_messages_go_through_redact_error(self):
        """A token baked into the original 401 body must not survive in the
        RestClientError that gets re-raised on the second 401.
        """

        def wrapped():
            # The HTTPError's str form echoes url + code. We bake a bearer
            # token into the msg to exercise the redact path on the
            # re-raise.
            err = urllib.error.HTTPError(
                url="https://example.salesforce.com",
                code=401,
                msg="Authorization: Bearer TESTONLY_HTTPERROR_TOKEN",
                hdrs={},  # type: ignore[arg-type]
                fp=io.BytesIO(b""),
            )
            raise err

        def refresh():
            return ("https://example.salesforce.com", "new_tok")

        decorated = rest_client.retry_on_401(refresh)(wrapped)
        with self.assertRaises(rest_client.RestClientError) as ctx:
            decorated()
        msg = str(ctx.exception)
        self.assertNotIn("TESTONLY_HTTPERROR_TOKEN", msg)
        # The redaction sentinel must appear somewhere — proof the
        # substitution actually ran.
        self.assertIn("<redacted>", msg)


class QueryHelperTests(unittest.TestCase):
    """tooling_query + data_query — happy paths with mocked opener."""

    def _install_mock_opener(self, response_body: bytes):
        """Monkeypatch build_opener to return an opener whose .open returns
        a context manager yielding an object with .read() == response_body.
        """
        fake_resp = mock.MagicMock()
        fake_resp.read.return_value = response_body
        fake_resp.__enter__ = mock.MagicMock(return_value=fake_resp)
        fake_resp.__exit__ = mock.MagicMock(return_value=False)

        fake_opener = mock.MagicMock()
        fake_opener.open = mock.MagicMock(return_value=fake_resp)
        return mock.patch.object(
            rest_client, "build_opener", return_value=fake_opener
        )

    def test_tooling_query_happy_path(self):
        body = json.dumps({"records": [{"Id": "01p000000000001"}]}).encode("utf-8")
        with self._install_mock_opener(body):
            out = rest_client.tooling_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM ApexClass",
                api_version="v60.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )
        self.assertEqual(out["records"][0]["Id"], "01p000000000001")

    def test_data_query_happy_path(self):
        body = json.dumps({"totalSize": 0, "records": []}).encode("utf-8")
        with self._install_mock_opener(body):
            out = rest_client.data_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM Account LIMIT 1",
                api_version="v60.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )
        self.assertEqual(out["totalSize"], 0)

    def test_tooling_query_apex_body_with_marker_does_not_trigger_refresh(self):
        """BUGFIX 2026-05-03: 200 OK Tooling response where ApexClass.Body
        references `INVALID_SESSION_ID` in source must pass through
        unchanged — no refresh, no retry, no error wrapping."""
        good_body = json.dumps({
            "size": 1,
            "totalSize": 1,
            "done": True,
            "queryLocator": None,
            "entityTypeName": "ApexClass",
            "records": [
                {
                    "attributes": {"type": "ApexClass"},
                    "Id": "01pUv000003a1YaIAI",
                    "Name": "XCSF_FlowFaultMessage",
                    "Body": "// if (code == 'INVALID_SESSION_ID') rethrow;",
                }
            ],
        }).encode("utf-8")

        open_count = {"n": 0}

        def fake_open(req):
            open_count["n"] += 1
            resp = mock.MagicMock()
            resp.read.return_value = good_body
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=False)
            return resp

        fake_opener = mock.MagicMock()
        fake_opener.open = fake_open

        refresh_calls = []

        def refresh():
            refresh_calls.append(1)
            return ("https://example.salesforce.com", "new_tok")

        with mock.patch.object(rest_client, "build_opener", return_value=fake_opener):
            out = rest_client.tooling_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id, Name, Body FROM ApexClass WHERE Id IN (...)",
                api_version="v66.0",
                on_401_refresh=refresh,
            )

        self.assertEqual(out["totalSize"], 1)
        self.assertEqual(out["records"][0]["Name"], "XCSF_FlowFaultMessage")
        self.assertEqual(open_count["n"], 1,
                         "exactly one HTTP call — no spurious retry")
        self.assertEqual(refresh_calls, [],
                         "refresh must not fire on a 200 OK success payload")

    def test_tooling_query_invalid_session_in_body_triggers_refresh(self):
        """HTTP 200 with INVALID_SESSION_ID body → refresh closure invoked."""
        bad_body = json.dumps([
            {"errorCode": "INVALID_SESSION_ID", "message": "Session expired"}
        ]).encode("utf-8")
        good_body = json.dumps({"records": []}).encode("utf-8")

        # Two-shot opener: first call returns bad_body, second returns good.
        responses = [bad_body, good_body]

        def fake_open(req):
            resp = mock.MagicMock()
            resp.read.return_value = responses.pop(0)
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=False)
            return resp

        fake_opener = mock.MagicMock()
        fake_opener.open = fake_open

        refresh_calls = []

        def refresh():
            refresh_calls.append(1)
            return ("https://example.salesforce.com", "new_tok")

        with mock.patch.object(rest_client, "build_opener", return_value=fake_opener):
            out = rest_client.tooling_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM ApexClass",
                api_version="v60.0",
                on_401_refresh=refresh,
            )

        self.assertEqual(out, {"records": []})
        self.assertEqual(len(refresh_calls), 1)


class RetryOn401CredentialRefreshIntegrationTests(unittest.TestCase):
    """Verify the retry carries the NEW token, not the stale one.

    The previous design looked correct under unit tests (refresh_fn called
    once, retry returns success) but was broken end-to-end: the closure
    around `(instance_url, token)` was captured at decoration time, so
    `refresh_fn`'s return value was thrown away and the retry saw the
    SAME stale credentials. Any real 401 (bad token) would hit the retry
    with the same bad token and 401 again.

    This test exercises a full tooling_query through a mock opener that
    401s for the stale token and succeeds for the refreshed token. A
    fix that only changes decorator bookkeeping (without threading the
    refresh into the retry's actual HTTP call) will fail this test.
    """

    def test_retry_on_401_uses_refreshed_credentials(self):
        # creds cell — a single-slot list mutated by refresh_fn.
        creds_cell: list = [("https://example.salesforce.com", "bad_token")]

        def creds_provider():
            return creds_cell[0]

        def refresh_fn():
            creds_cell[0] = ("https://example.salesforce.com", "good_token")
            return creds_cell[0]

        # Tracks the Authorization header seen on every request — this is
        # what proves whether the retry carried the refreshed token or not.
        auth_headers_seen: list[str] = []

        def fake_open(req):
            # urllib normalizes header names on add_header; read whichever
            # case lands.
            auth = None
            for k, v in req.headers.items():
                if k.lower() == "authorization":
                    auth = v
                    break
            auth_headers_seen.append(auth or "")

            if auth == "Bearer bad_token":
                raise urllib.error.HTTPError(
                    url=req.full_url,
                    code=401,
                    msg="Unauthorized",
                    hdrs={},  # type: ignore[arg-type]
                    fp=io.BytesIO(b""),
                )
            # Good token path — return a tiny success JSON.
            resp = mock.MagicMock()
            resp.read.return_value = json.dumps({"records": []}).encode("utf-8")
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=False)
            return resp

        fake_opener = mock.MagicMock()
        fake_opener.open = fake_open

        with mock.patch.object(rest_client, "build_opener", return_value=fake_opener):
            out = rest_client.tooling_query(
                creds_provider,
                "SELECT Id FROM ApexClass",
                api_version="v60.0",
                on_401_refresh=refresh_fn,
            )

        self.assertEqual(out, {"records": []})
        self.assertEqual(
            len(auth_headers_seen), 2,
            f"expected 2 attempts (401 + retry), got {len(auth_headers_seen)}",
        )
        self.assertEqual(
            auth_headers_seen[0], "Bearer bad_token",
            "first attempt should have used the stale token",
        )
        self.assertEqual(
            auth_headers_seen[1], "Bearer good_token",
            "retry MUST use the refreshed token — this is the bug",
        )


class TransientHttpWithRefreshIntegrationTests(unittest.TestCase):
    """End-to-end stack test through `tooling_query`.

    Drives the real decorator chain baked into `tooling_query`: first
    response 429 (transient retry), second response 401 (refresh + retry),
    third response 200. Proves that the stacking in the production
    helper — NOT just the raw decorators — gives the intended behavior.
    """

    def test_tooling_query_429_then_401_then_success(self):
        responses = [
            ("429", None),
            ("401", None),
            ("ok", json.dumps({"records": [{"Id": "a"}]}).encode("utf-8")),
        ]
        creds_cell = [("https://example.salesforce.com", "bad_token")]
        refresh_calls = []

        def creds_provider():
            return creds_cell[0]

        def refresh():
            refresh_calls.append(1)
            creds_cell[0] = ("https://example.salesforce.com", "good_token")
            return creds_cell[0]

        def fake_open(req):
            kind, body = responses.pop(0)
            if kind == "429":
                exc = urllib.error.HTTPError(
                    url=req.full_url,
                    code=429,
                    msg="rate limited",
                    hdrs=email.message.Message(),
                    fp=io.BytesIO(b""),
                )
                exc.headers["Retry-After"] = "0"  # 0 → base_delay wins, but sleep is mocked
                raise exc
            if kind == "401":
                raise urllib.error.HTTPError(
                    url=req.full_url,
                    code=401,
                    msg="unauthorized",
                    hdrs={},  # type: ignore[arg-type]
                    fp=io.BytesIO(b""),
                )
            resp = mock.MagicMock()
            resp.read.return_value = body
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=False)
            return resp

        fake_opener = mock.MagicMock()
        fake_opener.open = fake_open

        with mock.patch.object(rest_client, "build_opener", return_value=fake_opener), \
             mock.patch.object(rest_client.time, "sleep"):
            out = rest_client.tooling_query(
                creds_provider,
                "SELECT Id FROM ApexClass",
                api_version="v60.0",
                on_401_refresh=refresh,
            )

        self.assertEqual(out["records"][0]["Id"], "a")
        self.assertEqual(len(refresh_calls), 1,
                         "exactly one refresh — 429 must NOT trigger the refresh")
        self.assertEqual(responses, [], "all three canned responses consumed")


class AcceptEncodingAndForbiddenInvalidSessionTests(unittest.TestCase):
    """Accept-Encoding: identity + 403+INVALID_SESSION_ID handling."""

    def test_query_sends_accept_encoding_identity(self):
        """The outbound request carries `Accept-Encoding: identity` so no
        gzip body ever lands on the body-inspection path."""
        body = json.dumps({"records": []}).encode("utf-8")

        captured: list = []

        def fake_open(req):
            captured.append(req)
            resp = mock.MagicMock()
            resp.read.return_value = body
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=False)
            return resp

        fake_opener = mock.MagicMock()
        fake_opener.open = fake_open

        with mock.patch.object(rest_client, "build_opener", return_value=fake_opener):
            rest_client.tooling_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM ApexClass",
                api_version="v60.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )

        self.assertEqual(len(captured), 1)
        req = captured[0]
        # urllib stores add_header'd names via .capitalize(); read any case.
        accept_enc = None
        for k, v in req.headers.items():
            if k.lower() == "accept-encoding":
                accept_enc = v
                break
        self.assertEqual(accept_enc, "identity",
                         "Accept-Encoding must be 'identity'")

    def test_403_invalid_session_triggers_refresh(self):
        """HTTP 403 + INVALID_SESSION_ID body is treated as refreshable."""

        call_count = {"n": 0}

        def wrapped():
            call_count["n"] += 1
            if call_count["n"] == 1:
                # 403 with INVALID_SESSION_ID body → should refresh.
                raise urllib.error.HTTPError(
                    url="https://example.salesforce.com/x",
                    code=403,
                    msg="Forbidden",
                    hdrs={},  # type: ignore[arg-type]
                    fp=io.BytesIO(
                        b'[{"errorCode":"INVALID_SESSION_ID","message":"Session expired"}]'
                    ),
                )
            return {"ok": True}

        refresh_calls = []

        def refresh():
            refresh_calls.append(1)
            return ("https://example.salesforce.com", "new_tok")

        decorated = rest_client.retry_on_401(refresh)(wrapped)
        result = decorated()

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(refresh_calls), 1,
                         "403+INVALID_SESSION_ID must trigger refresh")

    def test_403_non_invalid_session_does_not_trigger_refresh(self):
        """HTTP 403 with some OTHER errorCode propagates unchanged."""

        def wrapped():
            raise urllib.error.HTTPError(
                url="https://example.salesforce.com/x",
                code=403,
                msg="Forbidden",
                hdrs={},  # type: ignore[arg-type]
                fp=io.BytesIO(
                    b'[{"errorCode":"INSUFFICIENT_ACCESS","message":"Denied"}]'
                ),
            )

        refresh_calls = []

        def refresh():
            refresh_calls.append(1)
            return ("https://example.salesforce.com", "new_tok")

        decorated = rest_client.retry_on_401(refresh)(wrapped)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            decorated()

        self.assertEqual(ctx.exception.code, 403)
        self.assertEqual(len(refresh_calls), 0,
                         "non-auth 403 must NOT burn a refresh")


class RetryOnTransientHttpTests(unittest.TestCase):
    """429/503 → exponential-backoff retry up to max_retries."""

    def test_429_then_success_retries_once(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] == 1:
                raise _make_http_error(429)
            return {"ok": True}

        with mock.patch.object(rest_client.time, "sleep") as slept:
            decorated = rest_client.retry_on_transient_http()(fn)
            out = decorated()

        self.assertEqual(out, {"ok": True})
        self.assertEqual(calls["n"], 2)
        slept.assert_called_once()
        # First retry: base_delay * 2**0 = 1.0
        self.assertAlmostEqual(slept.call_args[0][0], 1.0)

    def test_503_three_times_propagates_httperror(self):
        """With max_retries=3, total attempts = 4. Four 503s must surface
        the HTTPError after exactly 3 sleeps."""
        def fn():
            raise _make_http_error(503)

        with mock.patch.object(rest_client.time, "sleep") as slept:
            decorated = rest_client.retry_on_transient_http(max_retries=3)(fn)
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                decorated()

        self.assertEqual(ctx.exception.code, 503)
        self.assertEqual(slept.call_count, 3,
                         "3 sleeps for 3 retries before the final failure")

    def test_retry_after_header_honored_when_larger(self):
        """Retry-After: 10 overrides the 1s exponential schedule."""
        def fn():
            exc = urllib.error.HTTPError(
                url="https://example.salesforce.com/x",
                code=429,
                msg="rate limited",
                hdrs=email.message.Message(),
                fp=io.BytesIO(b""),
            )
            exc.headers["Retry-After"] = "10"
            raise exc

        # fn always raises → exhaust retries; we just need to observe the
        # first sleep value.
        with mock.patch.object(rest_client.time, "sleep") as slept:
            decorated = rest_client.retry_on_transient_http(max_retries=1)(fn)
            with self.assertRaises(urllib.error.HTTPError):
                decorated()

        self.assertEqual(slept.call_count, 1)
        self.assertAlmostEqual(slept.call_args_list[0][0][0], 10.0,
                               msg="Retry-After (10) must win over base_delay (1)")

    def test_retry_after_smaller_than_base_loses(self):
        """Retry-After: 0.5 with base_delay=1.0 → sleep 1.0 (base_delay wins)."""
        def fn():
            exc = urllib.error.HTTPError(
                url="https://example.salesforce.com/x",
                code=429,
                msg="rate limited",
                hdrs=email.message.Message(),
                fp=io.BytesIO(b""),
            )
            exc.headers["Retry-After"] = "0.5"
            raise exc

        with mock.patch.object(rest_client.time, "sleep") as slept:
            decorated = rest_client.retry_on_transient_http(max_retries=1)(fn)
            with self.assertRaises(urllib.error.HTTPError):
                decorated()

        self.assertAlmostEqual(slept.call_args_list[0][0][0], 1.0)

    def test_500_propagates_without_sleep(self):
        """Non-429/503 HTTP errors are out of scope — no retry, no sleep."""
        def fn():
            raise _make_http_error(500)

        with mock.patch.object(rest_client.time, "sleep") as slept:
            decorated = rest_client.retry_on_transient_http()(fn)
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                decorated()

        self.assertEqual(ctx.exception.code, 500)
        slept.assert_not_called()

    def test_401_propagates_without_sleep(self):
        """401 is retry_on_401's job — this decorator must pass it through."""
        def fn():
            raise _make_http_error(401)

        with mock.patch.object(rest_client.time, "sleep") as slept:
            decorated = rest_client.retry_on_transient_http()(fn)
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                decorated()

        self.assertEqual(ctx.exception.code, 401)
        slept.assert_not_called()

    def test_stacks_correctly_with_retry_on_401(self):
        """Integration: 429 → transient retry → 401 → refresh retry → success.

        This verifies the documented ordering in `tooling_query` /
        `data_query`: transient-HTTP is inner, 401-refresh is outer. If
        the layering were reversed, the refresh would fire on the 429.
        """
        sequence = ["429", "401", "ok"]
        refresh_calls = []

        def fn():
            code = sequence.pop(0)
            if code == "429":
                raise _make_http_error(429)
            if code == "401":
                raise _make_http_error(401)
            return {"ok": True}

        def refresh():
            refresh_calls.append(1)
            return ("https://example.salesforce.com", "new")

        with mock.patch.object(rest_client.time, "sleep"):
            # Inner: transient retry. Outer: 401 refresh. Matches the
            # stack in tooling_query / data_query.
            decorated = rest_client.retry_on_401(refresh)(
                rest_client.retry_on_transient_http()(fn)
            )
            out = decorated()

        self.assertEqual(out, {"ok": True})
        self.assertEqual(len(refresh_calls), 1,
                         "exactly one refresh — 429 must not burn a refresh")
        self.assertEqual(sequence, [], "all three responses consumed")

    def test_retry_after_http_date_parses(self):
        """HTTP-date form of Retry-After is accepted.

        We pass an RFC 7231 date roughly 5 seconds in the future. The
        parsed delta should be >= 0 and, since base_delay=1.0, the delta
        wins whenever it exceeds 1s. We accept any value >= 1.0 to avoid
        flakiness on slow test machines.
        """
        future_ts = time.time() + 30  # 30s out, plenty of slack
        http_date = email.utils.formatdate(future_ts, usegmt=True)

        def fn():
            exc = urllib.error.HTTPError(
                url="https://example.salesforce.com/x",
                code=503,
                msg="unavailable",
                hdrs=email.message.Message(),
                fp=io.BytesIO(b""),
            )
            exc.headers["Retry-After"] = http_date
            raise exc

        with mock.patch.object(rest_client.time, "sleep") as slept:
            decorated = rest_client.retry_on_transient_http(max_retries=1)(fn)
            with self.assertRaises(urllib.error.HTTPError):
                decorated()

        self.assertEqual(slept.call_count, 1)
        delay = slept.call_args_list[0][0][0]
        # Sanity: must be larger than base_delay (1.0) and no bigger than
        # the original offset (30) plus generous test-timing slack.
        self.assertGreaterEqual(delay, 1.0)
        self.assertLessEqual(delay, 35.0)

    def test_malformed_retry_after_falls_back_to_base(self):
        """`Retry-After: not-a-date` → base_delay wins."""
        def fn():
            exc = urllib.error.HTTPError(
                url="https://example.salesforce.com/x",
                code=429,
                msg="rate limited",
                hdrs=email.message.Message(),
                fp=io.BytesIO(b""),
            )
            exc.headers["Retry-After"] = "not-a-date"
            raise exc

        with mock.patch.object(rest_client.time, "sleep") as slept:
            decorated = rest_client.retry_on_transient_http(max_retries=1, base_delay=2.0)(fn)
            with self.assertRaises(urllib.error.HTTPError):
                decorated()

        self.assertAlmostEqual(slept.call_args_list[0][0][0], 2.0,
                               msg="malformed Retry-After falls back to base_delay")


class InvalidSessionDetectionTests(unittest.TestCase):
    """Unit coverage for the body-inspection helper."""

    def test_list_with_invalid_session_detected(self):
        body = [{"errorCode": "INVALID_SESSION_ID", "message": "foo"}]
        self.assertTrue(rest_client._body_indicates_invalid_session(body))

    def test_dict_without_invalid_session_not_detected(self):
        body = {"records": [{"Id": "a"}]}
        self.assertFalse(rest_client._body_indicates_invalid_session(body))

    def test_none_safe(self):
        self.assertFalse(rest_client._body_indicates_invalid_session(None))

    def test_string_with_marker(self):
        self.assertTrue(rest_client._body_indicates_invalid_session(
            "...INVALID_SESSION_ID..."
        ))

    # --- BUGFIX 2026-05-03: false positive on ApexClass.Body substring -----
    # Regression: _body_indicates_invalid_session used to walk ALL dict
    # values and substring-match. A 200 OK Tooling Query response whose
    # records carried Apex source referencing the string INVALID_SESSION_ID
    # (e.g. `XCSF_FlowFaultMessage`, `SkillRulesMatchAction`) was
    # misclassified as a session error, triggering spurious Wave B retries
    # and a bogus `INVALID_SESSION_ID after refresh` entry in `_unresolved`.

    def test_success_body_with_apex_source_substring_not_detected(self):
        """200 OK Tooling response whose ApexClass.Body mentions
        INVALID_SESSION_ID in source code must NOT be flagged."""
        apex_source = (
            "public class XCSF_FlowFaultMessage {\n"
            "    // Handles INVALID_SESSION_ID by rethrowing a typed error.\n"
            "    public static void raise(String code) {\n"
            "        if (code == 'INVALID_SESSION_ID') {\n"
            "            throw new HandledException('session expired');\n"
            "        }\n"
            "    }\n"
            "}"
        )
        body = {
            "size": 2,
            "totalSize": 2,
            "done": True,
            "queryLocator": None,
            "entityTypeName": "ApexClass",
            "records": [
                {
                    "attributes": {
                        "type": "ApexClass",
                        "url": "/services/data/v66.0/tooling/sobjects/ApexClass/01pUv0",
                    },
                    "Id": "01pUv000003a1YaIAI",
                    "Name": "XCSF_FlowFaultMessage",
                    "Body": apex_source,
                },
                {
                    "attributes": {"type": "ApexClass"},
                    "Id": "01pUv000003a1YbIAI",
                    "Name": "SkillRulesMatchAction",
                    "Body": "// references INVALID_SESSION_ID constant",
                },
            ],
        }
        self.assertFalse(
            rest_client._body_indicates_invalid_session(body),
            "success payload with INVALID_SESSION_ID inside ApexClass.Body "
            "must not be misclassified as an auth failure",
        )

    def test_error_envelope_under_errors_key_still_detected(self):
        """Dict-wrapped error envelope under a known key still flags."""
        body = {
            "errors": [
                {"errorCode": "INVALID_SESSION_ID", "message": "Session expired"}
            ]
        }
        self.assertTrue(rest_client._body_indicates_invalid_session(body))

    def test_success_body_with_marker_in_data_field_not_detected(self):
        """A top-level data field whose string value mentions the marker
        must not trigger — only error-envelope keys are walked."""
        body = {"records": [{"Id": "a", "Description": "handles INVALID_SESSION_ID"}]}
        self.assertFalse(rest_client._body_indicates_invalid_session(body))


class QueryWireShapeTests(unittest.TestCase):
    """`_query_once` must send GET with a urlencoded `q=`
    querystring. The prior POST-with-JSON-body shape returned HTTP 405
    on every real-org run — three reference fixtures failed
    end-to-end. These tests pin the wire shape so a regression back to
    POST would break CI before landing.
    """

    def _install_capturing_opener(self, captured: list, response_body: bytes):
        def fake_open(req):
            captured.append(req)
            resp = mock.MagicMock()
            resp.read.return_value = response_body
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=False)
            return resp

        fake_opener = mock.MagicMock()
        fake_opener.open = fake_open
        return mock.patch.object(
            rest_client, "build_opener", return_value=fake_opener
        )

    def test_data_query_sends_get_with_urlencoded_querystring(self):
        captured: list = []
        body = json.dumps({"records": []}).encode("utf-8")
        soql = "SELECT Id FROM BotDefinition WHERE DeveloperName = 'Foo'"

        with self._install_capturing_opener(captured, body):
            rest_client.data_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                soql,
                api_version="v60.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )

        self.assertEqual(len(captured), 1)
        req = captured[0]
        # method must be GET. Previously POST.
        self.assertEqual(req.get_method(), "GET",
                         "REST Query endpoint is GET-only; POST returns 405")
        # GET has no body.
        self.assertIsNone(req.data,
                          "GET requests must carry no body")
        # URL must carry the urlencoded querystring.
        self.assertIn("/services/data/v60.0/query/?q=", req.full_url)
        # urllib.parse.urlencode produces `+` for spaces — decoding
        # should round-trip the SOQL exactly.
        import urllib.parse
        parsed = urllib.parse.urlparse(req.full_url)
        qs = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(qs.get("q"), [soql],
                         "urlencoded `q` must round-trip the SOQL exactly")

    def test_tooling_query_sends_get_to_tooling_path(self):
        captured: list = []
        body = json.dumps({"records": []}).encode("utf-8")
        soql = "SELECT Id, DeveloperName FROM BotVersion"

        with self._install_capturing_opener(captured, body):
            rest_client.tooling_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                soql,
                api_version="v60.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )

        self.assertEqual(len(captured), 1)
        req = captured[0]
        self.assertEqual(req.get_method(), "GET")
        self.assertIsNone(req.data)
        # Tooling path is distinct from Data API path.
        self.assertIn("/services/data/v60.0/tooling/query/?q=", req.full_url)

    def test_query_does_not_send_content_type_header(self):
        """GET has no body — Content-Type is inappropriate and was
        removed alongside the method change. Some edge proxies complain
        about Content-Type on a bodyless GET; we just drop it."""
        captured: list = []
        body = json.dumps({"records": []}).encode("utf-8")

        with self._install_capturing_opener(captured, body):
            rest_client.data_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM Account LIMIT 1",
                api_version="v60.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )

        req = captured[0]
        content_type = None
        for k, v in req.headers.items():
            if k.lower() == "content-type":
                content_type = v
                break
        self.assertIsNone(content_type,
                          "GET requests must not carry Content-Type")

    def test_soql_with_special_chars_is_urlencoded(self):
        """SOQL string literals contain single quotes, commas, spaces,
        parentheses. urlencode must escape them all; a naive concat
        would break either the URL parse or the SOQL semantics."""
        captured: list = []
        body = json.dumps({"records": []}).encode("utf-8")
        # Exercise the full SOQL character classes that routinely appear.
        soql = (
            "SELECT Id, Name FROM ApexClass "
            "WHERE Name IN ('Foo', 'Bar Baz') "
            "AND NamespacePrefix IS NULL LIMIT 200"
        )

        with self._install_capturing_opener(captured, body):
            rest_client.data_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                soql,
                api_version="v60.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )

        req = captured[0]
        import urllib.parse
        parsed = urllib.parse.urlparse(req.full_url)
        qs = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(qs.get("q"), [soql])
        # Spaces MUST be escaped — a raw space in a URL is malformed.
        self.assertNotIn(" ", parsed.query,
                         "querystring must contain no literal spaces")


class ApiVersionRequiredKwargTests(unittest.TestCase):
    """`api_version` is a REQUIRED keyword-only
    argument on `tooling_query` + `data_query`.

    The prior design hardcoded `v60.0`. Real orgs (my-org-alias,
    my-perf-org-alias) run on v66 and expose fields v60 does not — confirmed
    empirically: `BotDefinition.Description` resolves on v66, raises
    `INVALID_FIELD` on v60 for the same org. Making `api_version`
    required surfaces a missed call-site as a TypeError at call time,
    not a silent regression back to a stale pinned version.
    """

    def test_tooling_query_requires_api_version(self):
        with self.assertRaises(TypeError) as ctx:
            rest_client.tooling_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM ApexClass",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )
        self.assertIn("api_version", str(ctx.exception))

    def test_data_query_requires_api_version(self):
        with self.assertRaises(TypeError) as ctx:
            rest_client.data_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM Account LIMIT 1",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )
        self.assertIn("api_version", str(ctx.exception))


class ApiVersionUrlSubstitutionTests(unittest.TestCase):
    """the `api_version` kwarg lands in the URL path
    unchanged. A caller passing `v66.0` must produce
    `/services/data/v66.0/...` in the outbound Request, NOT the old
    hardcoded `v60.0`.

    Regression shield: if a future refactor re-pins the version string,
    these tests fail at the wire-shape assertion even when unit-level
    behavior of `tooling_query` still looks correct.
    """

    def _install_capturing_opener(self, captured: list, response_body: bytes):
        def fake_open(req):
            captured.append(req)
            resp = mock.MagicMock()
            resp.read.return_value = response_body
            resp.__enter__ = mock.MagicMock(return_value=resp)
            resp.__exit__ = mock.MagicMock(return_value=False)
            return resp

        fake_opener = mock.MagicMock()
        fake_opener.open = fake_open
        return mock.patch.object(
            rest_client, "build_opener", return_value=fake_opener
        )

    def test_tooling_query_v66_in_url(self):
        captured: list = []
        body = json.dumps({"records": []}).encode("utf-8")
        with self._install_capturing_opener(captured, body):
            rest_client.tooling_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM ApexClass",
                api_version="v66.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )
        self.assertEqual(len(captured), 1)
        url = captured[0].full_url
        self.assertIn("/services/data/v66.0/tooling/query/?q=", url)
        # And the old hardcoded version must NOT appear — otherwise the
        # substitution silently failed.
        self.assertNotIn("v60.0", url)

    def test_data_query_v66_in_url(self):
        captured: list = []
        body = json.dumps({"records": []}).encode("utf-8")
        with self._install_capturing_opener(captured, body):
            rest_client.data_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM BotDefinition LIMIT 1",
                api_version="v66.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )
        url = captured[0].full_url
        self.assertIn("/services/data/v66.0/query/?q=", url)
        self.assertNotIn("v60.0", url)

    def test_different_api_version_per_call(self):
        """Two calls with different `api_version` land on distinct URLs —
        proves the value is NOT cached in module-level state between
        invocations."""
        captured: list = []
        body = json.dumps({"records": []}).encode("utf-8")
        with self._install_capturing_opener(captured, body):
            rest_client.tooling_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM ApexClass",
                api_version="v60.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )
            rest_client.tooling_query(
                rest_client.static_creds("https://example.salesforce.com", "tok"),
                "SELECT Id FROM ApexClass",
                api_version="v66.0",
                on_401_refresh=lambda: ("https://example.salesforce.com", "new"),
            )
        self.assertEqual(len(captured), 2)
        self.assertIn("/services/data/v60.0/tooling/query/", captured[0].full_url)
        self.assertIn("/services/data/v66.0/tooling/query/", captured[1].full_url)


if __name__ == "__main__":
    unittest.main()
