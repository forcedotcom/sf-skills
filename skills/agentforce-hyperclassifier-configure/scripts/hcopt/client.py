"""Customer ECA authentication and bounded HTTPS requests using the standard library."""

import base64
from datetime import timezone
from email.utils import parsedate_to_datetime
import http.client
import json
import math
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request


API = "https://api.salesforce.com"
CLASSIFIER_PATH = "/ai/gpt/v1/chat/generations"
CLASSIFIER_MODEL = "llmgateway__EinsteinHyperClassifier"
CREDENTIAL_KEYS = ("SF_INSTANCE_URL", "SF_CLIENT_ID", "SF_CLIENT_SECRET")


class ServiceError(RuntimeError):
    """A deliberately sanitized transport, authentication, or contract failure."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Prevent credentials from following a redirect to a different destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_credentials(env_file=None):
    """Read credentials as literal data, with an explicit file taking precedence."""
    values = {key: os.environ.get(key, "") for key in CREDENTIAL_KEYS}
    if env_file:
        path = Path(env_file)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Credential file must be a regular, non-symlink file")
        if os.name == "posix" and path.stat().st_mode & 0o077:
            raise ValueError("Credential file must be private: chmod 600 <file>")
        seen = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if not separator or key not in CREDENTIAL_KEYS or key in seen:
                raise ValueError("Credential file has an unknown, duplicate, or malformed key")
            seen.add(key)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[key] = value
    if any(not values[key] for key in CREDENTIAL_KEYS):
        raise ValueError("Set SF_INSTANCE_URL, SF_CLIENT_ID and SF_CLIENT_SECRET privately")
    instance = values["SF_INSTANCE_URL"].rstrip("/")
    # Restrict the destination before sending the consumer secret.
    values["SF_INSTANCE_URL"] = my_domain_origin(instance)
    return values


def my_domain_origin(value):
    """Allow only verified Salesforce My Domain origins before sending secrets."""
    pattern = (r"https://[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
               r"(?:\.(?:sandbox|develop|scratch|demo|trailblaze|patch))?\.my\.salesforce\.com")
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise ValueError("Org URL must be an HTTPS Salesforce My Domain origin")
    return value


def retry_delay(value, attempt):
    """Honor server delay or stop instead of retrying before a long cooldown."""
    fallback = min(2 ** attempt, 8)
    value = value.strip()
    try:
        if value.isascii() and value.isdigit():
            # Avoid unbounded conversion of an untrusted numeric header.
            digits = value.lstrip('0') or '0'
            delay = int(digits) if len(digits) <= 2 else 31
        else:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            delay = max(0, date.timestamp() - time.time())
    except (ValueError, TypeError, OverflowError):
        return fallback
    if delay > 30:
        raise ServiceError("Server Retry-After exceeds the 30-second retry wait budget; retry later") from None
    return delay


def jwt_expiry(token):
    """Inspect token shape and expiry; the Salesforce API verifies its signature."""
    try:
        if not isinstance(token, str) or len(token) > 20000 or not re.fullmatch(
                r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token):
            raise ValueError()
        parts = token.split(".")
        if len(parts) != 3 or not parts[2]:
            raise ValueError()
        decode = lambda part: json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        header, claims = decode(parts[0]), decode(parts[1])
        if not isinstance(header, dict) or not isinstance(claims, dict):
            raise ValueError()
        if header.get("alg") not in ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512"):
            raise ValueError()
        expiry = claims.get("exp")
        if (isinstance(expiry, bool) or not isinstance(expiry, (int, float))
                or not math.isfinite(expiry) or expiry <= time.time() + 30):
            raise ValueError()
        return expiry
    except (ValueError, TypeError, AttributeError, UnicodeError, OverflowError):
        raise ServiceError("OAuth must return an unexpired signed JWT; enable JWT tokens for named users") from None


class Client:
    """Keep credentials in memory and send inference only to api.salesforce.com."""

    def __init__(self, credentials, timeout=60, retries=1, max_calls=10000):
        self.credentials = credentials
        self.timeout = timeout
        self.retries = retries
        self.max_calls = max_calls
        self.calls = 0
        self.http_attempts = 0
        self.token = None
        self.expires = 0
        self.opener = urllib.request.build_opener(NoRedirect())

    def _request(self, url, payload, headers):
        for attempt in range(self.retries + 1):
            self.http_attempts += 1
            request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    raw = response.read(4_000_001)
                if len(raw) > 4_000_000:
                    raise ServiceError("Response exceeded the size limit")
                try:
                    data = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise ServiceError("Service returned invalid JSON") from None
                if not isinstance(data, dict):
                    raise ServiceError("Service returned an unexpected JSON envelope")
                return 200, data
            except urllib.error.HTTPError as error:
                status = error.code
                retry_after = error.headers.get("Retry-After", "") if error.headers else ""
                error.close()
                if status not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    return status, {}
                delay = retry_delay(retry_after, attempt)
            except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException):
                if attempt == self.retries:
                    raise ServiceError("HTTPS connection failed or timed out; check network and TLS") from None
                delay = min(2 ** attempt, 8)
            time.sleep(delay)
        raise ServiceError("Request retry limit reached")

    def _authenticate(self):
        body = urllib.parse.urlencode({"grant_type": "client_credentials",
                                      "client_id": self.credentials["SF_CLIENT_ID"],
                                      "client_secret": self.credentials["SF_CLIENT_SECRET"]}).encode()
        status, data = self._request(self.credentials["SF_INSTANCE_URL"] + "/services/oauth2/token", body,
                                     {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
        if status != 200:
            raise ServiceError(f"OAuth HTTP {status}; check ECA client credentials, Run As user and policy")
        token = data.get("access_token")
        self.expires = jwt_expiry(token)
        self.token = token

    def post(self, path, payload):
        """Make one logical inference call with at most one refresh after HTTP 401."""
        if path != CLASSIFIER_PATH and not re.fullmatch(
                r"/einstein/platform/v1/models/[A-Za-z0-9_.-]+/generations", path):
            raise ValueError("Unsupported inference path")
        if self.calls >= self.max_calls:
            raise ServiceError("Inference call budget exhausted")
        self.calls += 1
        for refresh in range(2):
            if not self.token or self.expires <= time.time() + 30:
                self._authenticate()
            headers = {"Authorization": "Bearer " + self.token, "Content-Type": "application/json",
                       "Accept": "application/json", "x-sfdc-app-context": "EinsteinGPT",
                       "x-client-feature-id": "ai-platform-models-connected-app"}
            status, data = self._request(API + path, json.dumps(payload).encode(), headers)
            if status == 200:
                return data
            if status == 401 and refresh == 0:
                self.token = None
                continue
            raise ServiceError(f"Inference HTTP {status}; check org entitlement, OAuth scopes and API contract")
        raise ServiceError("Authentication refresh failed")

    def classify(self, utterance, topics):
        """Send the utterance and complete descriptions, never the expected action."""
        return self.post(CLASSIFIER_PATH, {
            "model": CLASSIFIER_MODEL, "messages": [{"role": "user", "content": utterance}],
            "topics_config": {"return_single_topic": False, "topics": topics},
            "generation_settings": {"parameters": {"return_probability": True}},
        })

    def propose(self, model, prompt):
        """Generate candidate text through the documented Models API."""
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", model):
            raise ValueError("Invalid proposer model identifier")
        data = self.post(f"/einstein/platform/v1/models/{model}/generations", {"prompt": prompt})
        generation = data.get("generation")
        content = generation.get("generatedText") if isinstance(generation, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ServiceError("Proposer returned no generation.generatedText")
        return content

    def check_proposer(self, model):
        """Check generation availability without exposing customer evaluation text."""
        self.propose(model, "Reply with the word READY.")
