"""SFAP /chat/generations client and the production request shape.

The token is read from its 0600 file on every call: it never enters argv, the environment
of child processes, or any artifact, and a token refreshed in place is picked up without a
restart. On a 401, on_unauthorized(token_used) may refresh it (tokens.TokenRefresher); a True
return sends the request once more. Failures come back as status 'infra_error' after
retries, never as an answer.

A timeout is retried once only: each one costs the whole timeout, and a model that runs away on a
request runs away again. The provider has its own limit (EinsteinBYOM: ~180 s, then a 502 whose
body says "Timeout"), recorded as provider_timeout; the default --timeout is above it, so that the
provider, not the client, cuts a slow answer off.

Production request fields (from captured gateway payloads) reproduced here:
  tools                 [{"function": {name, description, parameters}}]  (no "type")
  tool_config           {"mode": "auto", "allowed_tools": [all tools], "parallel_calls": true}
  generation_settings   {"num_generations": 1, penalties 0, "stop_sequences": [],
                         "parameters": {"seed": n}}  — no max_tokens, no temperature
  system_prompt_strategy "use_model_parameter";  enable_pii_masking false
Not reproduced: safety/bias scoring flags, trust settings, localization, turn ids, tags.

STDM records a step's request before production's LLM client changes it. These of its
last-mile transform steps are ported as written, so the model sees what production's model saw:
  tools      every top-level property gets title = its name; ":" in a property name becomes
             "_" (in properties, required and that title), unless the new name is taken
  messages   an assistant message with no text and no tool calls is dropped; earlier calls to
             a renamed tool get the same renaming of their argument keys
  answer     the renamed argument keys are mapped back (restore_param_names), as production
             records them, so they score against the golden as production's did
Not ported, since no recorded request needs them: tool names cut to 64 characters (a longer
name fails loudly, HTTP 400), the repair of unpaired tool calls, URL placeholders. The seed is
--seed + repeat, not production's constant 75197747: it only picks the draw, and a constant
would make the k repeats one cached answer.
"""

import copy
import hashlib
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from .redact import redact, register_secret
from .units import parse_arguments

RETRY_STATUS = {408, 425, 429, 500, 502, 503, 504}
# No answer in time: the client's timeout, or the provider's (a 502/504 whose body says so).
TIMEOUT_KINDS = ("timeout", "provider_timeout")
DEFAULT_TIMEOUT = 200


def sanitize_tools_for_sfap(tools):
    """Drop additionalProperties and empty `required` (SFAP has rejected both with a 400)."""
    sanitized = []
    for tool in tools:
        tool = copy.deepcopy(tool)
        params = (tool.get("function") or {}).get("parameters") or {}
        params.pop("additionalProperties", None)
        if "required" in params and not params["required"]:
            del params["required"]
        sanitized.append(tool)
    return sanitized


def _param_renames(properties):
    """[(name, name with ":" -> "_")], skipping a rename onto another property's name."""
    return [(k, k.replace(":", "_")) for k in properties
            if ":" in k and k.replace(":", "_") not in properties]


def param_name_lookup(tools):
    """{tool name: {sent parameter name: recorded name}} for the tools whose names production renames."""
    lookup = {}
    for t in tools or []:
        fn = t.get("function") or {}
        props = (fn.get("parameters") or {}).get("properties")
        renames = _param_renames(props) if isinstance(props, dict) else []
        if renames:
            lookup[fn.get("name")] = {new: old for old, new in renames}
    return lookup


def _production_parameters(parameters):
    """In place: titles added, ":" renamed, as production sends a tool's parameters."""
    props = parameters.get("properties")
    if not isinstance(props, dict):
        return
    for key, value in props.items():
        if isinstance(value, dict):
            value.setdefault("title", key)
    renames = _param_renames(props)
    for old, new in renames:
        props[new] = props.pop(old)
        if isinstance(props[new], dict) and props[new].get("title") == old:
            props[new]["title"] = new
    if isinstance(parameters.get("required"), list):
        rename = dict(renames)
        parameters["required"] = [rename.get(r, r) for r in parameters["required"]]


def _remap_arguments(arguments, mapping):
    """Top-level keys of a JSON arguments string renamed; anything else returned as is."""
    if not arguments or not mapping:
        return arguments
    try:
        parsed = json.loads(arguments)
    except (json.JSONDecodeError, TypeError):
        return arguments
    if not isinstance(parsed, dict):
        return arguments
    return json.dumps({mapping.get(k, k): v for k, v in parsed.items()})


def _empty_assistant(m):
    content = m.get("content")
    return (m.get("role") == "assistant" and not m.get("tool_invocations")
            and not (content.strip() if isinstance(content, str) else content))


def production_messages(messages, lookup):
    """The messages as production sends them: empty assistant messages dropped, and earlier
    calls to a tool in `lookup` with their argument keys renamed as its parameters are. A new
    list; a message that changes is copied, the others are shared."""
    out = []
    for m in messages:
        if _empty_assistant(m):
            continue
        calls = m.get("tool_invocations") or []
        if any((c.get("function") or {}).get("name") in lookup for c in calls):
            renamed = []
            for c in calls:
                fn = c.get("function") or {}
                if fn.get("name") in lookup:
                    forward = {old: new for new, old in lookup[fn["name"]].items()}
                    c = dict(c, function=dict(fn, arguments=_remap_arguments(fn.get("arguments"), forward)))
                renamed.append(c)
            m = dict(m, tool_invocations=renamed)
        out.append(m)
    return out


def restore_param_names(response, tools):
    """A parsed answer with the renamed argument keys mapped back, as production records it."""
    lookup = param_name_lookup(tools)
    if not response or not any(c.get("name") in lookup for c in response.get("tool_calls") or []):
        return response
    calls = []
    for c in response["tool_calls"]:
        mapping = lookup.get(c.get("name"))
        if mapping and "args_raw" not in c:
            c = dict(c, args={mapping.get(k, k): v for k, v in c["args"].items()})
        calls.append(c)
    return dict(response, tool_calls=calls)


def to_sfap_tools(tools):
    """Step tool definitions (gen_ai.request.tools) in the production request shape."""
    out = []
    for t in sanitize_tools_for_sfap(tools):
        fn = t.get("function") or {}
        if isinstance(fn.get("parameters"), dict):
            _production_parameters(fn["parameters"])
        out.append({"function": fn})
    return out


def build_payload(model, messages, tools=None, seed=None, parameters=None):
    payload = {"model": model, "messages": production_messages(messages, param_name_lookup(tools))}
    if tools:
        payload["tools"] = to_sfap_tools(tools)
        payload["tool_config"] = {
            "mode": "auto",
            "allowed_tools": [{"name": (t.get("function") or {}).get("name"), "type": "function"}
                              for t in tools],
            "parallel_calls": True,
        }
    gen_params = {}
    if seed is not None:
        gen_params["seed"] = seed
    gen_params.update(parameters or {})
    payload["generation_settings"] = {
        "num_generations": 1, "frequency_penalty": 0.0, "presence_penalty": 0.0,
        "stop_sequences": [], "parameters": gen_params,
    }
    payload["system_prompt_strategy"] = "use_model_parameter"
    payload["enable_pii_masking"] = False
    return payload


def request_sha(messages, tools):
    """Identity of a request's content (messages + tools), independent of model and seed."""
    blob = json.dumps({"messages": messages, "tools": tools}, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _usage(body):
    gd = body.get("generation_details") or {}
    for holder in (gd.get("parameters"), body.get("parameters"), body):
        if isinstance(holder, dict) and isinstance(holder.get("usage"), dict):
            return holder["usage"]
    return None


def parse_generation(body):
    """{text, tool_calls, finish_reason, usage} from a 200 body, or None if it has no generation."""
    gens = ((body or {}).get("generation_details") or {}).get("generations") or []
    if not gens:
        return None
    g = gens[0]
    calls = []
    for inv in g.get("tool_invocations") or []:
        fn = inv.get("function") or {}
        args, raw = parse_arguments(fn.get("arguments"))
        call = {"name": fn.get("name"), "args": args}
        if raw is not None:
            call["args_raw"] = raw
        calls.append(call)
    params = g.get("parameters") if isinstance(g.get("parameters"), dict) else {}
    return {"text": g.get("content") or "", "tool_calls": calls,
            "finish_reason": params.get("finish_reason") or g.get("finish_reason"),
            "usage": _usage(body)}


class SfapClient:
    def __init__(self, base_url, token_file, core_tenant_id, timeout=DEFAULT_TIMEOUT, max_retries=3,
                 backoff=2.0, rate_limit_backoff=10.0, timeout_retries=1, feature_id="AgentBacktesting",
                 app_context="EinsteinGPT", opener=None, sleep=time.sleep, on_unauthorized=None):
        missing = [n for n, v in (("base_url", base_url), ("token_file", token_file),
                                  ("core_tenant_id", core_tenant_id)) if not v]
        if missing:
            raise ValueError("SFAP config missing: " + ", ".join(missing)
                             + " (run scripts/resolve-token.sh and pass --token-info)")
        parsed = urllib.parse.urlparse(base_url)
        if parsed.scheme != "https":
            raise ValueError(f"base_url must use https (got {parsed.scheme!r})")
        if not parsed.hostname or not parsed.hostname.endswith(".salesforce.com"):
            raise ValueError(f"base_url hostname must be *.salesforce.com (got {parsed.hostname!r})")
        self.url = base_url.rstrip("/") + "/chat/generations"
        self.token_file = token_file
        self.core_tenant_id = core_tenant_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.rate_limit_backoff = rate_limit_backoff
        self.timeout_retries = timeout_retries
        self.feature_id = feature_id
        self.app_context = app_context
        self._open = (opener.open if opener else urllib.request.urlopen)
        self._sleep = sleep
        self._on_unauthorized = on_unauthorized

    def _token(self):
        with open(self.token_file) as f:
            token = f.read().strip()
        if not token:
            raise RuntimeError("SFAP token file is empty")
        register_secret(token)
        return token

    def _delay(self, attempt, retry_after=None, http_status=None):
        if retry_after:
            try:
                return min(60.0, float(retry_after))
            except ValueError:
                pass
        if http_status == 429:  # a quota, usually per minute: a few seconds' wait meets it again
            return min(60.0, self.rate_limit_backoff * (2 ** (attempt - 1)))
        return min(30.0, self.backoff * (2 ** (attempt - 1)))

    def post(self, payload):
        """POST once per attempt. Returns {status, http_status, body, error, error_kind, attempts, latency_ms}."""
        data = json.dumps(payload).encode("utf-8")
        attempts, timeouts, refreshed, t0 = 0, 0, False, time.monotonic()
        while True:
            attempts += 1
            err_kind, err, http_status, retry_after = None, None, None, None
            try:
                token = self._token()
            except (OSError, RuntimeError) as e:
                return self._fail("token", f"cannot read the SFAP token file: {type(e).__name__}",
                                  None, attempts, t0)
            try:
                req = urllib.request.Request(self.url, data=data, method="POST", headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "x-sfdc-app-context": self.app_context,
                    "x-client-feature-id": self.feature_id,
                    "x-sfdc-core-tenant-id": self.core_tenant_id,
                })
                with self._open(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8", "replace")
                    http_status = resp.status
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    return self._fail("bad_json", f"HTTP {http_status}: response is not JSON: {redact(raw)[:200]}",
                                      http_status, attempts, t0)
                return {"status": "ok", "http_status": http_status, "body": body, "error": None,
                        "error_kind": None, "attempts": attempts,
                        "latency_ms": int((time.monotonic() - t0) * 1000)}
            except urllib.error.HTTPError as e:
                http_status = e.code
                retry_after = e.headers.get("Retry-After") if e.headers else None
                try:
                    body = e.read().decode("utf-8", "replace")
                except Exception:
                    body = ""
                finally:
                    e.close()
                err_kind, err = f"http_{e.code}", f"HTTP {e.code}: {redact(body)[:300]}"  # redact before cutting
                if e.code in (502, 504) and "timeout" in body.lower():
                    err_kind = "provider_timeout"
                if e.code == 401 and self._on_unauthorized and not refreshed:
                    refreshed = True
                    if self._on_unauthorized(token):
                        continue
                if e.code not in RETRY_STATUS:
                    return self._fail(err_kind, err, http_status, attempts, t0)
            except (socket.timeout, TimeoutError):
                err_kind, err = "timeout", f"timeout after {self.timeout}s"
            except urllib.error.URLError as e:
                if isinstance(e.reason, (socket.timeout, TimeoutError)):
                    err_kind, err = "timeout", f"timeout after {self.timeout}s"
                else:
                    err_kind, err = "network", f"network error: {e.reason}"
            except (ConnectionError, OSError) as e:
                err_kind, err = "network", f"network error: {e}"
            if err_kind in TIMEOUT_KINDS:
                timeouts += 1
            if attempts > self.max_retries or timeouts > self.timeout_retries:
                return self._fail(err_kind, err, http_status, attempts, t0)
            self._sleep(self._delay(attempts, retry_after, http_status))

    @staticmethod
    def _fail(kind, err, http_status, attempts, t0):
        return {"status": "infra_error", "http_status": http_status, "body": None,
                "error": redact(err), "error_kind": kind, "attempts": attempts,
                "latency_ms": int((time.monotonic() - t0) * 1000)}

    def generate(self, payload):
        """post() plus parsing; a 200 without a generation is an infra error too."""
        res = self.post(payload)
        if res["status"] != "ok":
            res["response"] = None
            return res
        parsed = parse_generation(res["body"])
        if parsed is None:
            res.update(status="infra_error", error_kind="empty_response",
                       error="HTTP 200 without generation_details.generations")
        res["response"] = parsed
        return res
