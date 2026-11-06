#!/usr/bin/env python3
"""Self-contained HTML report for one replay run.

    python3 scripts/build_report.py <run dir | results.jsonl> [report.html]

Reads results.jsonl, plus units.jsonl (transcripts, offered tools) and summary.json (run
config) when they sit next to it. Writes <run dir>/report.html by default. Every value is
HTML-escaped and redacted; the report shows user utterances, so share it like the run dir.

Scorecards follow the step kinds: router decisions (topic = the go_to_* call), sub-agent
tool calls, sub-agent text replies, and overall agreement (mean unit score: 1 match,
0.5 right tools with different arguments, 0 otherwise) next to the strict score. Infra
errors are counted on their own card and never scored.
"""

import json
import os
import sys
import html as _html
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from btlib import SCHEMA_RESULT  # noqa: E402
from btlib import results as resultslib  # noqa: E402
from btlib.redact import redact  # noqa: E402
from btlib.scoring import MATCH_BUCKETS  # noqa: E402

BUCKET_LABELS = {
    "wrong_args": "same tool, different arguments",
    "wrong_tool": "called a different tool",
    "missed_call": "missed a tool call",
    "extra_call": "extra tool call",
    "tool_to_text": "replied with text instead of a tool call",
    "text_to_tool": "called a tool instead of replying",
    "text_divergence": "text reply not equivalent",
    "equivalent_tool": "equivalent tool (lenient match only)",
    "transition_args": "arguments on a transition that takes none (lenient match only)",
}
KIND_TITLES = [("router", "Routing", "router steps; topic = the go_to_* call"),
               ("subagent_tool", "Sub-agent tool calls", "steps where production called a tool"),
               ("subagent_text", "Sub-agent text replies", "steps where production replied with text")]


def _esc(text):
    return _html.escape(redact(text)) if text not in (None, "") else ""


def _json_pretty(obj):
    return _esc(json.dumps(obj, indent=2, ensure_ascii=False))


def _rating(score, safe_min=85, review_min=60):
    if score is None:
        return "N/A", "#64748b"
    if score >= safe_min:
        return "SAFE", "#15803d"
    if score >= review_min:
        return "REVIEW", "#b45309"
    return "UNSAFE", "#dc2626"


def _pct(x):
    return None if x is None else round(100 * x, 1)


def _fmt_pct(x):
    return "N/A" if x is None else f"{x}%"


LEGACY_HINT = ("This report reads the run dir of the step-level replay (sfap_replay.py --out-dir); "
               "a replay_results.json from the old replay is not comparable: re-run the replay.")


def load_run(path):
    """(records, units_by_id, summary or None, run_dir) from a run dir or a results.jsonl path."""
    run_dir = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    results_path = os.path.join(path, "results.jsonl") if os.path.isdir(path) else path
    if not os.path.exists(results_path):
        raise SystemExit(f"{results_path} not found. {LEGACY_HINT}")
    try:
        records = resultslib.read_jsonl(results_path)
    except (ValueError, UnicodeDecodeError):  # JSONDecodeError is a ValueError
        records = None
    if records is None or not all(isinstance(r, dict) and r.get("schema") == SCHEMA_RESULT for r in records):
        raise SystemExit(f"{results_path} is not a results.jsonl ({SCHEMA_RESULT}). {LEGACY_HINT}")
    units_path = os.path.join(run_dir, "units.jsonl")
    units = {u["unit_id"]: u for u in resultslib.read_jsonl(units_path)} if os.path.exists(units_path) else {}
    summary_path = os.path.join(run_dir, "summary.json")
    summary = None
    if os.path.exists(summary_path):
        with open(summary_path, encoding="utf-8") as f:
            summary = json.load(f)
    return records, units, summary, run_dir


def failure_category(rec):
    """Bucket for the failure breakdown; None for a strict match."""
    if rec["bucket"] == "match":
        return "equivalent_tool" if rec["strict"] < 1.0 else None
    return rec["bucket"]


def _calls_html(calls):
    return "".join(f'<div class="tool-call"><span class="tool-name">{_esc(c.get("name"))}</span>'
                   f'<pre class="tool-args">{_json_pretty(c.get("args") if "args_raw" not in c else c["args_raw"])}</pre></div>'
                   for c in calls)


def _answer_html(calls, text):
    if calls:
        return _calls_html(calls) + (f'<div class="text-resp">{_esc(text)}</div>' if text else "")
    return f'<div class="text-resp">{_esc(text)}</div>' if text else "<em>empty</em>"


def _transcript_html(unit):
    if not unit:
        return "<em>no units.jsonl next to results.jsonl</em>", 0
    msgs = unit["request"]["messages"]
    parts = []
    for m in msgs:
        role = m.get("role", "unknown")
        if m.get("tool_invocations"):
            body = "; ".join(f'{(c.get("function") or {}).get("name")}({(c.get("function") or {}).get("arguments")})'
                             for c in m["tool_invocations"])
            said = f'{_esc(m.get("content"))}<br>' if m.get("content") else ""
            parts.append(f'<div class="msg msg-assistant"><strong>assistant → tool</strong>: {said}<code>{_esc(body)}</code></div>')
        elif role == "tool":
            parts.append(f'<div class="msg msg-info"><strong>tool result ({_esc(m.get("tool_call_name") or "")})</strong>: '
                         f'{_esc(m.get("content"))}</div>')
        elif role == "system":
            content = m.get("content") or ""
            parts.append(f'<details class="msg msg-system"><summary><strong>system</strong> ({len(content)} chars)'
                         f'</summary><pre class="tool-args">{_esc(content)}</pre></details>')
        else:
            parts.append(f'<div class="msg msg-{_esc(role)}"><strong>{_esc(role)}</strong>: {_esc(m.get("content"))}</div>')
    return "".join(parts), len(msgs)


def _card(rec, unit, idx, transcript=True):
    ok = rec["status"] == "ok"
    if not ok:
        badge, badge_txt = "badge-fail", "INFRA"
    elif rec["bucket"] == "match" and rec["strict"] == 1.0:
        badge, badge_txt = "badge-pass", "PASS"
    elif rec["score"] and rec["score"] > 0:
        badge, badge_txt = "badge-warn", "PARTIAL"
    else:
        badge, badge_txt = "badge-fail", "FAIL"
    category = (failure_category(rec) if ok else rec["error_kind"]) or "match"
    flags = []
    if not ok:
        flags.append(f'<span class="flag flag-error">{_esc(rec["error"])}</span>')
    if ok and rec["detail"]:
        flags.append(f'<span class="flag flag-warn">{_esc(rec["detail"])}</span>')
    for note in rec.get("schema_violations") or []:
        flags.append(f'<span class="flag flag-error">schema: {_esc(note)}</span>')
    for j in rec.get("judge") or []:
        flags.append(f'<span class="flag flag-info">judge ({_esc(j.get("for"))}): '
                     f'{"equivalent" if j.get("equivalent") else "not equivalent"}: {_esc(j.get("reasoning"))}</span>')
    g = rec["golden"]
    resp = rec["response"] or {}

    def yn(v):
        return "N/A" if v is None else ("Yes" if v else "No")

    rows = [("Decision (tool vs text)", yn(rec["decision"])), ("Tool names (lenient)", yn(rec["names"])),
            ("Tool names (exact)", yn(rec["names_strict"])), ("Arguments", yn(rec["args"])),
            ("Text equivalent", yn(rec["text"])), ("Unit score", "N/A" if rec["score"] is None else rec["score"]),
            ("Strict", "N/A" if rec["strict"] is None else rec["strict"])]
    if rec["step_kind"] == "router":
        rows.append(("Topic (go_to) match", yn(rec["topic_match"])))
    if rec.get("proxies"):
        p = rec["proxies"]
        rows.append(("Length ratio (candidate/golden)", p["len_ratio"]))
        rows.append(("Ends with a question (golden / candidate)",
                     f'{yn(p["golden_ends_with_question"])} / {yn(p["candidate_ends_with_question"])}'))
        if p["candidate_raw_ids"] > p["golden_raw_ids"]:
            rows.append(("Raw record ids in reply", p["candidate_raw_ids"]))
    score_rows = "".join(f"<tr><td>{_esc(k)}</td><td>{_esc(str(v))}</td></tr>" for k, v in rows)
    tools = [(t.get("function") or {}).get("name") for t in unit["request"]["tools"]] if unit else []
    tools_html = ", ".join(f"<code>{_esc(t)}</code>" for t in tools) or "<em>none</em>"
    if transcript:
        body, n_msgs = _transcript_html(unit)
        request_html = f'''<details class="transcript-toggle">
          <summary>Request sent ({n_msgs} messages)</summary>
          <div class="transcript">{body}</div>
        </details>'''
    else:  # matching steps: keep the report small; the request is in units.jsonl
        request_html = f'<div class="scorecard-detail">request: units.jsonl, unit_id <code>{_esc(rec["unit_id"])}</code></div>'
    return f'''
    <details class="card">
      <summary class="card-header">
        <span class="card-idx">#{_esc(str(idx))}</span>
        <span class="{badge}">{badge_txt}</span>
        <span class="card-bucket">{_esc(BUCKET_LABELS.get(category, category))}</span>
        <span class="card-bucket">{_esc(rec["node"])}</span>
        <span class="card-utterance">{_esc((rec.get("user_utterance") or "")[:100])}</span>
        <span class="card-session">r{_esc(str(rec["repeat"]))} · {_esc(rec["unit_id"][-24:])}</span>
      </summary>
      <div class="card-body">
        <div class="flags">{" ".join(flags)}</div>
        <div class="comparison">
          <div class="comp-col"><h4>Golden ({_esc(rec.get("golden_model"))})</h4>{_answer_html(g["tool_calls"], g["text"])}</div>
          <div class="comp-col"><h4>Candidate ({_esc(rec.get("model"))})</h4>{_answer_html(resp.get("tool_calls") or [], resp.get("text")) if ok else "<em>no answer (infra error)</em>"}</div>
        </div>
        <div class="section"><h4>Scores</h4><table class="score-table">{score_rows}</table></div>
        <div class="section"><h4>Tools offered</h4><div>{tools_html}</div></div>
        {request_html}
      </div>
    </details>'''


def _scorecard(title, value_pct, label, details):
    verdict, color = _rating(value_pct)
    detail_html = "".join(f'<div class="scorecard-detail">{d}</div>' for d in details)
    return f'''
<div class="scorecard">
  <h3>{_esc(title)}</h3>
  <div class="scorecard-value" style="color:{color}">{_fmt_pct(value_pct)}</div>
  <div class="scorecard-label">{_esc(label)}</div>
  {detail_html}
  <div class="scorecard-detail">{verdict}</div>
</div>'''


def _production_html(summary):
    """What production's own checks said of the replayed turns; '' when STDM recorded none."""
    p = summary["production"]
    if not (set(p["groundedness"]) - {"(none)"} or p["guardrails"] or p["turns_with_step_errors"]
            or set(p["end_type"]) - {"(none)"} or p["sessions_with_action_errors"]):
        return ""
    by_cat = summary["by_groundedness"]
    rows = "".join(
        f'<tr><td>{"no check recorded" if cat == "(none)" else f"<code>{_esc(cat)}</code>"}</td>'
        f'<td>{p["groundedness"].get(cat, 0)}</td><td>{by_cat.get(cat, {}).get("n", 0)}</td>'
        f'<td>{_fmt_pct(_pct(by_cat.get(cat, {}).get("agreement")))}</td>'
        f'<td>{_fmt_pct(_pct(by_cat.get(cat, {}).get("strict")))}</td></tr>'
        for cat in list(p["groundedness"]) + [c for c in by_cat if c not in p["groundedness"]])
    lines = [f'<code>{_esc(name)}</code>: {_esc(", ".join(f"{v} {n}" for v, n in values.items()))}'
             for name, values in p["guardrails"].items()]
    end_types = ", ".join(f'{"not recorded" if t == "(none)" else _esc(t)} {n}' for t, n in p["end_type"].items())
    lines.append(f'{p["sessions"]} sessions &middot; end type: {end_types} &middot; with action errors: '
                 f'{p["sessions_with_action_errors"]} &middot; turns with a failed step: {p["turns_with_step_errors"]}')
    details = "".join(f'<div class="scorecard-detail">{line}</div>' for line in lines)
    return f'''<div class="buckets"><h3>Production's own checks (report only)</h3>
<div class="scorecard-detail">What production's groundedness check and trust guardrails said of its own replies. They never change a score: agreement with production is not correctness.</div>
<table class="score-table node-table">
<tr><th>groundedness of the turn</th><th>turns</th><th>steps</th><th>agreement</th><th>strict</th></tr>{rows}</table>
{details}</div>'''


def build(records, units, summary=None):
    saved = summary or {}
    config = saved.get("config") or {}
    counts = saved.get("counts") or {}
    summary = resultslib.summarize(records, config, counts.get("skipped_steps"), counts.get("units"))
    ok = [r for r in records if r["status"] == "ok"]
    infra = [r for r in records if r["status"] != "ok"]
    overall = _pct(summary["overall"]["agreement"])
    verdict, verdict_color = _rating(overall)

    def meta(label, value):
        return f'<div><dt>{_esc(label)}</dt><dd>{_esc(str(value)) if value not in (None, "", []) else "N/A"}</dd></div>'

    code = config.get("code") or {}
    head = [
        meta("Candidate model", ", ".join(sorted({r["model"] for r in records if r.get("model")}))),
        meta("Golden (production) model", ", ".join(sorted({r["golden_model"] for r in records if r.get("golden_model")}))),
        meta("Judge model", config.get("judge_model")),
        meta("Org", config.get("org") or next((r["org"] for r in records if r.get("org")), None)),
        meta("Agent", config.get("agent") or next((r["agent"] for r in records if r.get("agent")), None)),
        meta("Units x repeats", f'{summary["counts"]["units"]} x {config.get("k", 1)}'),
        meta("Finished", config.get("finished")),
        meta("Code", f'{code.get("git") or "?"}{"+dirty" if code.get("git_dirty") else ""} / btlib {code.get("btlib_sha256", "?")}'),
    ]
    parts = [f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Offline Analysis Report</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>Offline Analysis Report</h1>
  <div class="verdict" style="background:{verdict_color}">{verdict}</div>
  <dl class="header-meta">{"".join(head)}</dl>
</div>
<div class="scorecards">''']

    for prefix, title, label in KIND_TITLES:
        a = resultslib.aggregate([r for r in ok if r["kind"] == prefix or r["kind"].startswith(prefix + "_")])
        if not a["n"]:
            continue
        details = [f'{a["n"]} steps &middot; {a["match"]} match &middot; strict {_fmt_pct(_pct(a["strict"]))}']
        if prefix == "router" and summary["topic"]["n"]:
            details.append(f'topic {summary["topic"]["match"]}/{summary["topic"]["n"]}')
        if prefix == "subagent_text" and summary["text"]["n"]:
            t = summary["text"]
            details.append(f'median length ratio {t["median_len_ratio"]} &middot; raw-id leaks {t["raw_id_leaks"]}')
        parts.append(_scorecard(title, _pct(a["agreement"]), label, details))
    o = summary["overall"]
    parts.append(_scorecard("Overall", overall, "Agreement with production (mean unit score)",
                            [f'{o["n"]} scored &middot; {o["match"]} match &middot; strict {_fmt_pct(_pct(o["strict"]))}']))
    c = summary["counts"]
    infra_kinds = ", ".join(f"{_esc(k)} {v}" for k, v in c["infra_by_kind"].items()) or "none"
    skipped = ", ".join(f"{_esc(k)} {v}" for k, v in c["skipped_steps"].items()) or "none"
    timed_out = (f'\n  <div class="scorecard-detail">{c["timed_out_units"]} units timed out on every repeat: the model '
                 f'may not finish them</div>' if c.get("timed_out_units") else "")
    parts.append(f'''
<div class="scorecard">
  <h3>Infra errors (not scored)</h3>
  <div class="scorecard-value" style="color:{"#dc2626" if c["infra_rate"] > 0.1 else "#475569"}">{c["infra_error"]}</div>
  <div class="scorecard-label">{100 * c["infra_rate"]:.1f}% of {c["records"]} calls</div>
  <div class="scorecard-detail">by kind: {infra_kinds}</div>{timed_out}
  <div class="scorecard-detail">steps not replayed: {skipped}</div>
</div>''')
    parts.append("</div>")

    # per-node table
    node_rows = "".join(
        f'<tr><td><code>{_esc(node)}</code></td><td>{a["n"]}</td><td>{_fmt_pct(_pct(a["agreement"]))}</td>'
        f'<td>{_fmt_pct(_pct(a["strict"]))}</td><td>{_esc(", ".join(f"{BUCKET_LABELS.get(b, b)} {k}" for b, k in a["buckets"].items() if b not in MATCH_BUCKETS))}</td></tr>'
        for node, a in summary["by_node"].items())
    if node_rows:
        parts.append(f'''<div class="buckets"><h3>By node</h3><table class="score-table node-table">
<tr><th>node</th><th>steps</th><th>agreement</th><th>strict</th><th>non-matches</th></tr>{node_rows}</table></div>''')
    parts.append(_production_html(summary))

    # failure breakdown
    cats = Counter(cat for cat in (failure_category(r) for r in ok) if cat)
    if cats:
        top = max(cats.values())
        parts.append('<div class="buckets"><h3>Failure breakdown</h3>')
        for cat, n in cats.most_common():
            parts.append(f'''
<div class="bucket-row">
  <span class="bucket-name">{_esc(BUCKET_LABELS.get(cat, cat))}</span>
  <div class="bucket-bar-wrap"><div class="bucket-bar" style="width:{round(100 * n / top)}%"></div></div>
  <span class="bucket-count">{n}</span>
</div>''')
        violations = summary["schema_violations"]["records"]
        if violations:
            parts.append(f'<div class="scorecard-detail">{violations} candidate answer(s) violate the offered tool schema</div>')
        parts.append("</div>")
    if summary["confusion"]:
        conf_rows = "".join(f'<tr><td><code>{_esc(x["golden"])}</code></td><td><code>{_esc(x["candidate"])}</code></td><td>{x["n"]}</td></tr>'
                            for x in summary["confusion"][:15])
        parts.append(f'''<div class="buckets"><h3>Tool confusions (golden → candidate)</h3><table class="score-table node-table">
<tr><th>golden</th><th>candidate</th><th>n</th></tr>{conf_rows}</table></div>''')

    failing = [(i, r) for i, r in enumerate(records) if r["status"] == "ok" and failure_category(r)]
    passing = [(i, r) for i, r in enumerate(records) if r["status"] == "ok" and not failure_category(r)]
    if passing:
        parts.append(f'<div class="pass-summary">{len(passing)} step(s) matched production exactly</div>')
    if failing:
        parts.append(f"<h2>Not an exact match ({len(failing)})</h2>")
        parts.extend(_card(r, units.get(r["unit_id"]), i) for i, r in failing)
    if infra:
        parts.append(f"<h2>Infra errors ({len(infra)})</h2>")
        parts.extend(_card(r, units.get(r["unit_id"]), i) for i, r in enumerate(records) if r["status"] != "ok")
    if passing:
        parts.append(f'''
<details style="margin-top:1.5rem">
  <summary style="cursor:pointer;font-family:'Space Grotesk',sans-serif;font-weight:600;color:var(--slate-500);font-size:1.1rem;padding:0.5rem 0">
    Matching ({len(passing)})
  </summary>
  <div style="margin-top:0.5rem">''')
        parts.extend(_card(r, units.get(r["unit_id"]), i, transcript=False) for i, r in passing)
        parts.append("</div></details>")
    parts.append("\n</div>\n</body>\n</html>")
    return "\n".join(parts)


CSS = '''
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --slate-50: #f8fafc; --slate-100: #f1f5f9; --slate-200: #e2e8f0;
  --slate-300: #cbd5e1; --slate-400: #94a3b8; --slate-500: #64748b;
  --slate-600: #475569; --slate-700: #334155; --slate-800: #1e293b;
  --slate-900: #0f172a;
  --safe: #15803d; --safe-bg: #f0fdf4; --safe-border: #bbf7d0;
  --review: #b45309; --review-bg: #fffbeb; --review-border: #fde68a;
  --unsafe: #dc2626; --unsafe-bg: #fef2f2; --unsafe-border: #fecaca;
  --radius: 12px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background: linear-gradient(135deg, var(--slate-50) 0%, var(--slate-100) 100%);
  color: var(--slate-800);
  line-height: 1.6;
  min-height: 100vh;
  padding: 2rem;
}

.container { max-width: 1200px; margin: 0 auto; }

h1 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2rem;
  font-weight: 700;
  color: var(--slate-900);
  margin-bottom: 0.5rem;
}

h2 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.4rem;
  font-weight: 600;
  color: var(--slate-700);
  margin: 2rem 0 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--slate-200);
}

h3 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--slate-600);
  margin-bottom: 0.5rem;
}

h4 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--slate-500);
  margin-bottom: 0.3rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Header */
.header {
  background: white;
  border-radius: var(--radius);
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  border: 1px solid var(--slate-200);
}

.header-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  margin-top: 1rem;
  font-size: 0.875rem;
  color: var(--slate-500);
}

.header-meta dt { font-weight: 600; color: var(--slate-600); }
.header-meta dd { font-family: 'IBM Plex Mono', monospace; }

/* Verdict badge */
.verdict {
  display: inline-block;
  padding: 0.5rem 1.5rem;
  border-radius: 999px;
  font-family: 'Space Grotesk', sans-serif;
  font-weight: 700;
  font-size: 1.1rem;
  letter-spacing: 0.05em;
  color: white;
  margin-top: 1rem;
}

/* Scorecards */
.scorecards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.scorecard {
  background: white;
  border-radius: var(--radius);
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  border: 1px solid var(--slate-200);
}

.scorecard-value {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2.5rem;
  font-weight: 700;
  margin: 0.5rem 0;
}

.scorecard-label {
  font-size: 0.875rem;
  color: var(--slate-500);
}

.scorecard-detail {
  font-size: 0.8rem;
  color: var(--slate-500);
  margin-top: 0.25rem;
}

/* Buckets */
.buckets {
  background: white;
  border-radius: var(--radius);
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  border: 1px solid var(--slate-200);
}

.bucket-row {
  display: flex;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--slate-100);
}

.bucket-row:last-child { border-bottom: none; }

.bucket-name {
  flex: 1;
  font-size: 0.9rem;
  color: var(--slate-700);
}

.bucket-bar-wrap {
  flex: 2;
  height: 24px;
  background: var(--slate-100);
  border-radius: 4px;
  overflow: hidden;
  margin: 0 1rem;
}

.bucket-bar {
  height: 100%;
  background: var(--slate-400);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.bucket-count {
  width: 3rem;
  text-align: right;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--slate-600);
}

/* Cards */
.card {
  background: white;
  border-radius: var(--radius);
  margin-bottom: 0.75rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  border: 1px solid var(--slate-200);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  cursor: pointer;
  font-size: 0.9rem;
  list-style: none;
}

.card-header::-webkit-details-marker { display: none; }
.card-header::before {
  content: '\\25B6';
  font-size: 0.7rem;
  color: var(--slate-400);
  transition: transform 0.2s;
}
details[open] > .card-header::before { transform: rotate(90deg); }

.card-idx {
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  color: var(--slate-500);
  min-width: 2.5rem;
}

.card-bucket {
  font-size: 0.8rem;
  color: var(--slate-500);
  background: var(--slate-100);
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.card-utterance {
  flex: 1;
  color: var(--slate-700);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-session {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.75rem;
  color: var(--slate-500);
}

.card-body { padding: 0 1.5rem 1.5rem; }

.badge-pass {
  background: var(--safe-bg); color: var(--safe); border: 1px solid var(--safe-border);
  padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;
}
.badge-warn {
  background: var(--review-bg); color: var(--review); border: 1px solid var(--review-border);
  padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;
}
.badge-fail {
  background: var(--unsafe-bg); color: var(--unsafe); border: 1px solid var(--unsafe-border);
  padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;
}

/* Flags */
.flags { margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; }
.flag {
  font-size: 0.8rem; padding: 0.25rem 0.75rem; border-radius: 6px;
  font-family: 'IBM Plex Mono', monospace;
}
.flag-error { background: var(--unsafe-bg); color: var(--unsafe); border: 1px solid var(--unsafe-border); }
.flag-warn { background: var(--review-bg); color: var(--review); border: 1px solid var(--review-border); }
.flag-info { background: var(--slate-100); color: var(--slate-600); }

/* Comparison */
.comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.comp-col {
  background: var(--slate-50);
  border-radius: 8px;
  padding: 1rem;
  border: 1px solid var(--slate-200);
}

.tool-call { margin-bottom: 0.5rem; }
.tool-name {
  font-family: 'IBM Plex Mono', monospace;
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--slate-800);
}

.tool-args {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.8rem;
  background: var(--slate-100);
  padding: 0.5rem;
  border-radius: 4px;
  margin-top: 0.25rem;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.text-resp {
  font-size: 0.85rem;
  color: var(--slate-600);
  font-style: italic;
}

/* Section */
.section { margin-bottom: 1rem; }

.score-table {
  width: 100%;
  font-size: 0.85rem;
  border-collapse: collapse;
}
.score-table td {
  padding: 0.3rem 0.5rem;
  border-bottom: 1px solid var(--slate-100);
}
.score-table td:first-child { color: var(--slate-500); width: 60%; }
.score-table td:last-child { font-family: 'IBM Plex Mono', monospace; font-weight: 500; }

/* Transcript */
.transcript-toggle { margin-top: 1rem; }
.transcript-toggle > summary {
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--slate-500);
  padding: 0.5rem 0;
}

.transcript {
  max-height: 300px;
  overflow-y: auto;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: var(--slate-50);
  border-radius: 8px;
  border: 1px solid var(--slate-200);
}

.msg {
  padding: 0.4rem 0.6rem;
  margin-bottom: 0.25rem;
  font-size: 0.8rem;
  border-radius: 4px;
  word-break: break-word;
}

.msg strong { font-size: 0.75rem; text-transform: uppercase; }
.msg-system { background: #eff6ff; color: #1e40af; }
.msg-user { background: #f0fdf4; color: #166534; }
.msg-assistant { background: #fdf4ff; color: #86198f; }
.msg-info { background: var(--slate-100); color: var(--slate-500); }

code {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.85em;
  background: var(--slate-100);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}

/* Pass rows section */
.pass-summary {
  background: var(--safe-bg);
  border: 1px solid var(--safe-border);
  border-radius: var(--radius);
  padding: 1rem 1.5rem;
  margin-bottom: 1.5rem;
  color: var(--safe);
  font-weight: 500;
}

/* Multi-row tables (by node, confusions) */
.node-table td:first-child { width: auto; color: var(--slate-700); }
.node-table th {
  text-align: left;
  padding: 0.3rem 0.5rem;
  font-weight: 600;
  color: var(--slate-600);
  border-bottom: 2px solid var(--slate-200);
}
.node-table td:last-child { font-family: inherit; font-weight: 400; color: var(--slate-600); }
details.msg > summary { cursor: pointer; }
.msg pre.tool-args { white-space: pre-wrap; margin-top: 0.4rem; }
'''


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    records, units, summary, run_dir = load_run(argv[0])
    out = argv[1] if len(argv) > 1 else os.path.join(run_dir, "report.html")
    with resultslib.open_private(out) as f:  # the report quotes user utterances
        f.write(build(records, units, summary))
    ok = sum(1 for r in records if r["status"] == "ok")
    matched = sum(1 for r in records if r["status"] == "ok" and not failure_category(r))
    print(f"Report generated: {out}")
    print(f"  {len(records)} results: {matched} match, {ok - matched} differ, {len(records) - ok} infra errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
