"""Binary LLM judge: is the candidate equivalent to the production (golden) answer?

Used only where a deterministic comparison cannot decide: text replies, and tool arguments
that are free text (a search phrase). The judge sees the recent conversation and, for
arguments, the tool's parameter schema. A judge that cannot be reached or parsed yields
None, which the caller records as an infra error rather than a verdict.
"""

import json
import re

from .redact import redact

DEFAULT_JUDGE_MODEL = "llmgateway__OpenAIGPT41"

TEXT_RUBRIC = """You compare two replies an AI assistant could send at the same point of a customer conversation.
The REFERENCE reply is what production sent. The CANDIDATE reply was produced by another model for the identical request.

The CANDIDATE is equivalent when, for the customer, it does the same thing:
- same intent and next step: answers the same question, asks for the same missing information, offers the same options, or hands off the same way;
- no fact, number, product, price or commitment that conflicts with the REFERENCE or that the conversation does not support.
Wording, order, tone and length may differ.

The user message is a JSON object with keys "context", "reference_reply", and "candidate_reply".
Answer with JSON only: {"equivalent": true or false, "reasoning": "<one sentence>"}"""

ARGS_RUBRIC = """You compare the arguments two AI models passed to the same tool at the same point of a conversation.
The REFERENCE arguments are what production sent. The CANDIDATE arguments were produced by another model for the identical request.

The CANDIDATE is equivalent when the tool would do the same thing with it: the same search results, the same record, the same change.
Differences in wording, case or word order that the tool would treat the same do not matter. A missing optional argument matters only if the REFERENCE value changes the result.

The user message is a JSON object with keys "tool", "parameter_schema", "context", "reference_arguments", and "candidate_arguments".
Answer with JSON only: {"equivalent": true or false, "reasoning": "<one sentence>"}"""


class JudgeConfigError(ValueError):
    pass


def check_judge_model(judge_model, candidate_models):
    """Refuse a judge that is one of the models being judged (self-preference)."""
    if not judge_model:
        raise JudgeConfigError("no judge model set (--judge-model)")
    clash = sorted({m for m in candidate_models if m and m == judge_model})
    if clash:
        raise JudgeConfigError(
            f"judge model {judge_model} is also the replay model; pick a different --judge-model")


def model_family(alias):
    """'sfdc_ai__DefaultGPT41', 'llmgateway__AzureOpenAIGPT41' -> 'gpt41' (vendor prefixes dropped)."""
    name = (alias or "").split("__")[-1].lower()
    for prefix in ("default", "azureopenai", "openai", "bedrockanthropic", "vertexai"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name


def same_family(judge_model, candidate_models):
    """Candidate aliases that name the judge's model under another alias (warn, do not refuse)."""
    fam = model_family(judge_model)
    return sorted({m for m in candidate_models if m and m != judge_model and model_family(m) == fam})


def render_context(messages, max_messages=6, max_chars=800):
    """The last few non-system messages, tool calls written as name(args)."""
    lines = []
    for m in [m for m in messages if m.get("role") != "system"][-max_messages:]:
        if m.get("tool_invocations"):
            calls = ", ".join(f"{(c.get('function') or {}).get('name')}({(c.get('function') or {}).get('arguments')})"
                              for c in m["tool_invocations"])
            text = f"assistant called {calls}"
        elif m.get("role") == "tool":
            text = f"tool result ({m.get('tool_call_name') or 'tool'}): {m.get('content')}"
        else:
            text = f"{m.get('role')}: {m.get('content')}"
        lines.append(text if len(text) <= max_chars else text[:max_chars] + " ...")
    return "\n".join(lines) or "(none)"


def parse_verdict(text):
    """{"equivalent": bool, "reasoning": str} or None."""
    if not text:
        return None
    candidates = [text.strip()]
    candidates += re.findall(r"\{.*?\}", text, re.DOTALL)
    candidates += re.findall(r"\{.*\}", text, re.DOTALL)
    for c in candidates:
        try:
            v = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(v, dict) and "equivalent" in v:
            eq = v["equivalent"]
            if isinstance(eq, str):
                eq = {"true": True, "false": False, "yes": True, "no": False}.get(eq.strip().lower())
            if isinstance(eq, bool):
                return {"equivalent": eq, "reasoning": str(v.get("reasoning", ""))[:500]}
    return None


class Judge:
    """Calls the judge model through an SfapClient-like object (generate(payload))."""

    def __init__(self, client, model):
        self.client = client
        self.model = model

    def _ask(self, system_prompt, data):
        payload = {"model": self.model,
                   "messages": [
                       {"role": "system", "content": system_prompt},
                       {"role": "user", "content": redact(json.dumps(data, ensure_ascii=False))},
                   ],
                   "generation_settings": {"num_generations": 1, "max_tokens": 400, "temperature": 0.0}}
        res = self.client.generate(payload)
        if res["status"] != "ok":
            return None, res.get("error") or "judge call failed"
        verdict = parse_verdict(res["response"]["text"])
        if verdict is None:
            return None, "judge reply has no {equivalent: true|false} JSON"
        verdict["model"] = self.model
        return verdict, None

    def text(self, golden, candidate, messages):
        return self._ask(TEXT_RUBRIC, {
            "context": render_context(messages),
            "reference_reply": golden,
            "candidate_reply": candidate,
        })

    def args(self, tool, schema, golden_args, candidate_args, messages):
        return self._ask(ARGS_RUBRIC, {
            "tool": tool,
            "parameter_schema": schema or {},
            "context": render_context(messages),
            "reference_arguments": golden_args,
            "candidate_arguments": candidate_args,
        })
