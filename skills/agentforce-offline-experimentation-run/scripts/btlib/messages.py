"""Rebuild an LLM step's request messages exactly as production sent them.

STDM keeps every LLM_STEP's request in `gen_ai.input.messages`. Production sends those
messages in that order, nothing merged; its LLM client drops only assistant messages with no
text and no tool calls (btlib.sfap, with its other last-mile steps):

    system                      agent-level prompt
    user / assistant ...        conversation so far
    assistant + tool_invocations, tool ...   calls made earlier in the turn and their results
    system                      the step's own instruction, LAST ("...\\n\\n# CONTEXT ...")

STDM stores tool results and call arguments as objects; production sends them as JSON
strings — tool results compact, arguments with json.dumps defaults (verified on captured
gateway payloads). Production also names each tool result (`tool_call_name`), resolved here
from the matching call id.
"""

import json


def tool_result_content(content):
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return json.dumps(content, separators=(",", ":"))


def tool_call_arguments(arguments):
    if isinstance(arguments, str):
        return arguments
    return json.dumps(arguments if arguments is not None else {})


def _text(content):
    if isinstance(content, str):
        return content
    return "" if content is None else json.dumps(content)


def build_messages(stdm_messages):
    """Production-layout messages from a step's gen_ai.input.messages."""
    out, name_by_id = [], {}
    for m in stdm_messages:
        role = m.get("role")
        if role == "assistant" and m.get("tool_invocations"):
            calls = []
            for inv in m["tool_invocations"]:
                fn = inv.get("function") or {}
                name_by_id[inv.get("id")] = fn.get("name")
                calls.append({
                    "id": inv.get("id"),
                    "type": inv.get("type") or "function",
                    "function": {"name": fn.get("name"),
                                 "arguments": tool_call_arguments(fn.get("arguments"))},
                })
            out.append({"role": "assistant", "content": _text(m.get("content")),
                        "tool_invocations": calls})
        elif role == "tool":
            msg = {"role": "tool", "content": tool_result_content(m.get("content")),
                   "tool_call_id": m.get("tool_call_id")}
            name = m.get("tool_call_name") or name_by_id.get(m.get("tool_call_id"))
            if name:
                msg["tool_call_name"] = name
            out.append(msg)
        else:
            out.append({"role": role, "content": _text(m.get("content"))})
    return out


def layout(messages):
    """Role sequence, e.g. 'S,U,A,C,T,S' (C = assistant tool call). For checks and tests."""
    code = {"system": "S", "user": "U", "assistant": "A", "tool": "T"}
    return ",".join("C" if m.get("tool_invocations") else code.get(m.get("role"), "?")
                    for m in messages)


def unresolved_tool_results(messages):
    """tool_call_ids of tool results with no earlier matching call."""
    seen, missing = set(), []
    for m in messages:
        for inv in m.get("tool_invocations") or []:
            seen.add(inv.get("id"))
        if m.get("role") == "tool" and m.get("tool_call_id") not in seen:
            missing.append(m.get("tool_call_id"))
    return missing


def last_user_text(messages):
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            return m["content"]
    return ""
