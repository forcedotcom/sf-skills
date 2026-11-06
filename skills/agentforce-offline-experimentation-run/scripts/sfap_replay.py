#!/usr/bin/env python3
"""Replay production LLM steps (from STDM) on a candidate model and score them against production.

Every LLM_STEP of every turn is one unit (btlib/units.py): the request exactly as production
sent it, and production's own answer as the golden. The candidate model answers the same
request through SFAP and is scored step by step (btlib/scoring.py).

    python3 scripts/bt_fetch.py --org <alias> --agent <api name> --start <date> --end <date> \\
        --out-dir runs/fetch
    bash scripts/resolve-token.sh --org <alias> > /tmp/token_info.json
    python3 scripts/sfap_replay.py --details runs/fetch/details.json \\
        --token-info /tmp/token_info.json --model llmgateway__EinsteinSalesforceCerebro \\
        --out-dir runs/cerebro
    python3 scripts/build_report.py runs/cerebro

--model trace replays each step on the model that served it in production. That self-control
should agree almost fully; what it misses is replay noise, not a model difference.

--patch FILE applies edit ops to the requests first (references/patching.md): the replay
then scores the edited agent without a deploy. Untouched steps are sent unchanged.

An SFAP token lasts about 2 h. With --token-org <alias>, a refused token is minted again
with resolve-token.sh during the run; with --cache-dir, a rerun sends only what is unanswered.

Outputs in --out-dir: units.jsonl, results.jsonl, summary.json, replay_results_sfap.csv,
and patch_coverage.json with --patch. They contain user utterances: keep them out of git.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from btlib import SCHEMA_UNIT, agentsrc  # noqa: E402
from btlib import cache as cachelib  # noqa: E402
from btlib import judge as judgelib  # noqa: E402
from btlib import patch as patchlib  # noqa: E402
from btlib import results, scoring, stdm  # noqa: E402
from btlib import splits as splitlib  # noqa: E402
from btlib import tokens as tokenlib  # noqa: E402
from btlib import units as unitlib  # noqa: E402
from btlib import versions as versionlib  # noqa: E402
from btlib.redact import redact  # noqa: E402
from btlib.sfap import DEFAULT_TIMEOUT, SfapClient, build_payload, request_sha, restore_param_names  # noqa: E402

AGENT_CONFIG_KEYS = {"router_nodes", "equivalent_tools", "arg_defaults", "description"}
MAX_REPLAY_TARGETS = 5000


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--details", action="extend", nargs="+", metavar="FILE",
                     help="bt_fetch.py's details.json, or getMultipleConversationDetails output "
                          "(`sf apex run --json` file or plain JSON); one or more files, repeatable")
    src.add_argument("--from-units", metavar="FILE", help="units.jsonl of an earlier run")
    p.add_argument("--out-dir", required=True, help="run dir for all outputs (created; must not hold a run)")
    p.add_argument("--model", default=os.environ.get("REPLAY_MODEL"),
                   help="candidate model alias, or 'trace' for each step's production model (env REPLAY_MODEL)")
    p.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL") or judgelib.DEFAULT_JUDGE_MODEL,
                   help=f"model for text / free-text-argument equivalence (env JUDGE_MODEL; default "
                        f"{judgelib.DEFAULT_JUDGE_MODEL}); must differ from the candidate")
    p.add_argument("--token-info", metavar="FILE",
                   help="resolve-token.sh output; otherwise env SFAP_BASE_URL, SFAP_TOKEN_FILE, CORE_TENANT_ID")
    p.add_argument("--token-org", metavar="ALIAS",
                   help="when SFAP refuses the token (HTTP 401: it expired), mint a new one with "
                        "resolve-token.sh --org ALIAS into the token file and send the request again, once")
    p.add_argument("--steps", choices=("router", "subagent", "all"), default="all",
                   help="which LLM steps to replay (default all)")
    p.add_argument("--router-nodes", help="comma-separated router step names (default: agent config, else "
                                          + ",".join(unitlib.DEFAULT_ROUTER_NODES) + ")")
    p.add_argument("--agent-config", metavar="FILE",
                   help='JSON {"router_nodes": [...], "equivalent_tools": [[tool, tool], ...], '
                        '"arg_defaults": {tool: {param: value}}}')
    p.add_argument("--org-id", default=os.environ.get("ORG_ID"),
                   help="recorded in the outputs (env ORG_ID; default: from the core tenant id)")
    p.add_argument("--agent", default=os.environ.get("AGENT_API_NAME"),
                   help="agent API name recorded in the outputs (env AGENT_API_NAME)")
    p.add_argument("--k", type=int, default=1, help="repeats per unit (seed = --seed + repeat)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--limit", type=int, help="replay only the first N units")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                   help="seconds per SFAP call; above the provider's own limit (~180 s) by default")
    p.add_argument("--max-retries", type=int, default=3, help="retries after the first attempt; a timeout is "
                   "retried once")
    p.add_argument("--cache-dir", metavar="DIR",
                   help="answer a payload already answered from DIR instead of SFAP, and store every new answer "
                        "there (judge calls too); the payload as sent is the key, model and seed included")
    p.add_argument("--agent-versions", metavar="DIR",
                   help="the retrieved .agent versions (a bundle dir, a dir of bundle dirs or of .agent files): "
                        "attributes each unit to the versions that render it; writes versions.json")
    p.add_argument("--agent-version", metavar="LABEL",
                   help="replay only the sessions this version can have served (needs --agent-versions)")
    p.add_argument("--val-fraction", type=float, metavar="F",
                   help="label each session test or val: a share of about F goes to val, by a hash of the session ID")
    p.add_argument("--split-salt", default=splitlib.DEFAULT_SALT, help="salt of that hash (default %(default)s)")
    p.add_argument("--split", choices=("all",) + splitlib.SPLITS, default="all",
                   help="replay only this split (needs --val-fraction)")
    p.add_argument("--exclude-sessions", metavar="FILE",
                   help="skip these sessions: a file that names them, e.g. one ID per line, a "
                        "units.jsonl, a sessions or details JSON, a replay CSV (references/splits.md)")
    p.add_argument("--patch", metavar="FILE",
                   help="edit ops (bt.patch/1) applied to the requests before the replay; "
                        "writes patch_coverage.json and stops if an op matches nothing")
    p.add_argument("--max-replay-targets", type=int,
                   default=int(os.environ.get("MAX_REPLAY_TARGETS", str(MAX_REPLAY_TARGETS))),
                   help=f"upper bound on replay jobs (units x k); env MAX_REPLAY_TARGETS "
                        f"(default {MAX_REPLAY_TARGETS})")
    p.add_argument("--dry-run", action="store_true",
                   help="build units.jsonl (and patch_coverage.json) only; no SFAP calls")
    p.add_argument("--overwrite", action="store_true", help="replace an existing run in --out-dir")
    args = p.parse_args(argv)
    if not args.dry_run and not args.model:
        p.error("--model is required (an alias, or 'trace')")
    if args.agent_version and not args.agent_versions:
        p.error("--agent-version needs --agent-versions")
    if args.val_fraction is not None and not 0 < args.val_fraction < 1:
        p.error("--val-fraction must be between 0 and 1")
    if args.split != "all" and args.val_fraction is None:
        p.error("--split needs --val-fraction (and the --split-salt the units were labelled with)")
    if args.k < 1 or args.concurrency < 1:
        p.error("--k and --concurrency must be >= 1")
    return args


def load_agent_config(path):
    if not path:
        return {}
    with open(path) as f:
        cfg = json.load(f)
    unknown = set(cfg) - AGENT_CONFIG_KEYS
    if unknown:
        raise SystemExit(f"--agent-config: unknown keys {sorted(unknown)}")
    groups = cfg.get("equivalent_tools") or []
    if not all(isinstance(g, list) and all(isinstance(n, str) for n in g) for g in groups):
        raise SystemExit("--agent-config: equivalent_tools must be a list of lists of tool names")
    defaults = cfg.get("arg_defaults") or {}
    if not (isinstance(defaults, dict) and all(isinstance(d, dict) for d in defaults.values())):
        raise SystemExit("--agent-config: arg_defaults must map each tool name to {param: value}")
    return cfg


def sfap_config(token_info):
    info = {}
    if token_info:
        with open(token_info) as f:
            info = json.load(f)
        if info.get("error"):
            raise SystemExit(f"--token-info reports an error: {info['error']} {info.get('hint', '')}")
    return (info.get("baseUrl") or os.environ.get("SFAP_BASE_URL"),
            info.get("tokenFile") or os.environ.get("SFAP_TOKEN_FILE"),
            info.get("coreTenantId") or os.environ.get("CORE_TENANT_ID"))


def load_units(args, router_nodes, org_id):
    """(every unit of the inputs, skipped steps Counter, input paths, duplicate sessions)."""
    if args.from_units:
        units = results.read_jsonl(args.from_units)
        wrong = {u.get("schema") for u in units} - {SCHEMA_UNIT}
        if wrong:
            raise SystemExit(f"{args.from_units}: not a units file (schema {sorted(map(str, wrong))})")
        for u in units:  # the router set of this run decides the kind
            u["step_kind"] = "router" if u["node"] in router_nodes else "subagent"
        return units, Counter(), [args.from_units], 0
    convos, dupes = stdm.load_conversations(args.details)
    units, skipped = unitlib.build_units(convos, org=org_id, agent=args.agent, router_nodes=router_nodes)
    return units, skipped, args.details, dupes


def attribute_versions(units, args):
    """(session version sets, versions.json report) with --agent-versions, else (None, None)."""
    if not args.agent_versions:
        return None, None
    try:
        found = agentsrc.load_versions(args.agent_versions)
    except (OSError, agentsrc.AgentSourceError) as e:
        raise SystemExit(f"--agent-versions {args.agent_versions}: {e}")
    labels = [v.label for v in found]
    if args.agent_version and args.agent_version not in labels:
        raise SystemExit(f"--agent-version {args.agent_version}: not among the versions in "
                         f"{args.agent_versions} ({', '.join(labels)})")
    session_sets, report = versionlib.attribute(units, found)
    report["source"] = os.path.basename(os.path.normpath(args.agent_versions))
    s = report["sessions"]
    print(f"versions: {report['units_rendered']} of {report['units']} units render from a version in "
          f"{report['source']} (" + ", ".join(f"{v['label']} {v['units_rendered']}" for v in report["versions"])
          + f"); sessions {s['total']}: one version {s['one_version']}, several {s['several_versions']}, "
          f"conflict {s['conflict']}, unknown {s['unknown']}")
    missing = report["units_not_rendered_by_node"]
    if missing:
        where = "; ".join(f"{node} " + ", ".join(f"{check} {n}" for check, n in c.items()) for node, c in missing.items())
        print(f"WARNING: {report['units'] - report['units_rendered']} units render from none of the versions "
              f"(node, then the check the closest version failed: {where}); retrieve every version the "
              "traces may come from")
    return session_sets, report


def label_splits(units, args):
    """Label every unit test or val (--val-fraction); the split config, else None."""
    if args.val_fraction is None:
        return None
    try:
        counts = splitlib.label(units, args.val_fraction, args.split_salt)
    except splitlib.SplitError as e:
        raise SystemExit(f"--val-fraction: {e}")
    print(f"split (salt {args.split_salt}, val fraction {args.val_fraction}): "
          + ", ".join(f"{s} {n} sessions {k} units" for s, (n, k) in counts.items()))
    return {"val_fraction": args.val_fraction, "salt": args.split_salt, "selected": args.split,
            "sessions": {s: n for s, (n, _) in counts.items()}}


def exclude_sessions(units, skipped, args):
    """(the units of sessions not listed in --exclude-sessions, its config or None)."""
    if not args.exclude_sessions:
        return units, None
    try:
        excluded = splitlib.read_session_ids(args.exclude_sessions)
    except (OSError, splitlib.SplitError) as e:
        raise SystemExit(f"--exclude-sessions {args.exclude_sessions}: {e}")
    present = {u["session_id"] for u in units} & excluded
    keep = [u for u in units if u["session_id"] not in excluded]
    skipped["excluded_session"] += len(units) - len(keep)
    print(f"--exclude-sessions: {len(present)} of its {len(excluded)} sessions are in the input; "
          f"{len(units) - len(keep)} units skipped")
    return keep, {"file": os.path.basename(args.exclude_sessions), "sessions": len(excluded),
                  "in_input": len(present)}


def select_units(units, skipped, args, session_sets, report):
    """The units to replay: --steps, then --agent-version, then --split, then --limit."""
    if args.steps != "all":
        keep = [u for u in units if u["step_kind"] == args.steps]
        skipped["not_selected"] += len(units) - len(keep)
        units = keep
    if args.agent_version:
        units, dropped = versionlib.select(units, args.agent_version, session_sets)
        skipped.update(dropped)
        unrendered = sum(1 for u in units if not u["compatible_versions"])
        report.update(selected=args.agent_version, kept=len(units), dropped=dict(dropped),
                      kept_not_rendered=unrendered)
        print(f"--agent-version {args.agent_version}: {len(units)} units kept; dropped: "
              + (", ".join(f"{k} {v}" for k, v in sorted(dropped.items())) or "none"))
        if unrendered:
            print(f"WARNING: {unrendered} kept units do not render from {args.agent_version} exactly; "
                  "a patch may not apply to them (see patch_coverage.json)")
    if args.split != "all":
        keep = [u for u in units if u["split"] == args.split]
        skipped["other_split"] += len(units) - len(keep)
        units = keep
    if args.limit:
        units = units[:args.limit]
    return units


RUN_FILES = ("summary.json", "results.jsonl", "units.jsonl", "replay_results_sfap.csv", "patch_coverage.json",
             "versions.json", "compare.json", "report.html")


def prepare_out_dir(out_dir, overwrite):
    if os.path.exists(os.path.join(out_dir, "results.jsonl")) and not overwrite:
        raise SystemExit(f"{out_dir} already holds a run (results.jsonl); use a new --out-dir or --overwrite")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
        os.chmod(out_dir, 0o700)  # user utterances inside
    elif overwrite:  # the old run's files go first: a re-run that stops early must not pass for it
        for name in RUN_FILES:
            if os.path.isfile(os.path.join(out_dir, name)):
                os.remove(os.path.join(out_dir, name))


def warn_loose_mode(path, what, expected):
    try:
        if os.stat(path).st_mode & 0o077:
            print(f"WARNING: {what} is readable by other users (expected mode {expected})")
    except OSError:
        pass


def apply_patch(units, path, out_dir):
    """(requests, patch config): the (messages, tools, patch info) to send per unit."""
    if not path:
        return [(u["request"]["messages"], u["request"]["tools"], None) for u in units], None
    try:
        ops = patchlib.load_patch(path)
        patched, coverage = patchlib.patch_units(units, ops)
    except (OSError, patchlib.PatchError) as e:
        raise SystemExit(f"--patch {path}: {e}")
    requests, changed = [], 0
    for u, (messages, tools, applied) in zip(units, patched):
        base = request_sha(u["request"]["messages"], u["request"]["tools"])
        changed += request_sha(messages, tools) != base
        requests.append((messages, tools, {"base_request_sha": base, "ops": applied}))
    report = patchlib.coverage_report(os.path.basename(path), coverage, changed, len(units))
    results.write_json(os.path.join(out_dir, "patch_coverage.json"), report)
    for c in coverage:
        print(f"  patch {c['id']:<16} {c['target']:<40} matched {c['matched']}/{c['units_with_target']} "
              f"{c['status']}" + (f": {c['message']}" if c["message"] else ""))
    print(f"patch: {changed} of {len(units)} requests changed; coverage in {out_dir}/patch_coverage.json")
    if report["errors"]:
        raise SystemExit(f"--patch: {len(report['errors'])} op(s) failed, nothing replayed "
                         f"(see patch_coverage.json): " + "; ".join(report["errors"]))
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()[:16]
    return requests, {"file": os.path.basename(path), "sha256": digest, "ops": [op.id for op in ops],
                      "units_changed": changed}


def replay(units, requests, args, client, judge, equivalence, out_dir, arg_defaults=None):
    jobs = []
    for u, (messages, tools, patch) in zip(units, requests):
        sha = request_sha(messages, tools)
        model = u["request"]["model"] if args.model == "trace" else args.model
        for rep in range(args.k):
            jobs.append((u, messages, tools, patch, rep, model, args.seed + rep, sha))

    def work(job):
        u, messages, tools, patch, rep, model, seed, sha = job
        call = client.generate(build_payload(model, messages, tools, seed=seed))
        call["response"] = restore_param_names(call.get("response"), tools)
        # scored against the unit as captured: a patch edits texts, never tool names or schemas
        scores = (scoring.score_unit(u, call["response"], judge, equivalence, arg_defaults)
                  if call["status"] == "ok" else None)
        return results.make_record(u, rep, model, seed, sha, call, scores, patch=patch)

    records, interrupted, collected = [], False, set()
    path = os.path.join(out_dir, "results.jsonl")
    with results.open_private(path) as f:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [pool.submit(work, j) for j in jobs]
            try:
                for i, fut in enumerate(as_completed(futures), 1):
                    collected.add(fut)
                    rec = fut.result()
                    records.append(rec)
                    results.append_jsonl(f, rec)  # partial results survive a crash
                    print(f"  [{i}/{len(jobs)}] {rec['node'][:28]:<28} r{rec['repeat']} {rec['status']:<11} "
                          f"{rec['bucket'] or rec['error_kind'] or ''}", flush=True)
            except KeyboardInterrupt:
                interrupted = True
                for fut in futures:
                    fut.cancel()
                print("\nInterrupted: waiting for calls in flight, then writing partial results.")
            except Exception:
                for fut in futures:  # a bug: stop spending calls; results.jsonl keeps what finished
                    fut.cancel()
                raise
        # The pool has shut down, so calls that were in flight at an interrupt are done: keep them.
        for fut in futures:
            if fut not in collected and not fut.cancelled() and fut.exception() is None:
                rec = fut.result()
                records.append(rec)
                results.append_jsonl(f, rec)
    order = {u["unit_id"]: i for i, u in enumerate(units)}
    records.sort(key=lambda r: (order[r["unit_id"]], r["repeat"]))
    results.write_jsonl(path, records)
    return records, interrupted


def print_summary(summary, out_dir):
    c, o = summary["counts"], summary["overall"]
    skipped = ", ".join(f"{k} {v}" for k, v in c["skipped_steps"].items()) or "none"
    print("\n" + "=" * 64)
    print(f"units {c['units']} x k={summary['config'].get('k')} | scored {c['scored']} | "
          f"infra errors {c['infra_error']} ({100 * c['infra_rate']:.1f}%) | skipped steps: {skipped}")
    if c["infra_by_kind"]:
        print("  infra errors by kind: " + ", ".join(f"{k} {v}" for k, v in c["infra_by_kind"].items()))
    if o["n"]:
        print(f"agreement {o['agreement']:.3f}   strict {o['strict']:.3f}   ({o['match']}/{o['n']} match)")
        for kind, agg in summary["by_kind"].items():
            print(f"  {kind:<16} n={agg['n']:<4} agreement {agg['agreement']:.3f}")
        for split, agg in summary["by_split"].items():
            print(f"  split {split:<10} n={agg['n']:<4} agreement {agg['agreement']:.3f}")
        t = summary["topic"]
        if t["n"]:
            print(f"  topic (router go_to) {t['match']}/{t['n']}")
        print("buckets: " + ", ".join(f"{b} {n}" for b, n in summary["by_bucket"].items()))
    cache = summary["config"].get("cache")
    if cache:
        print(f"cache {cache['dir']}: {cache['hits']} answers reused, {cache['calls']} calls made (replay and judge)"
              + (f"; WARNING: {cache['write_errors']} answers could not be stored" if cache["write_errors"] else ""))
    refresh = summary["config"].get("token_refresh")
    if refresh and (refresh["refreshes"] or refresh["failures"]):
        print(f"SFAP token (--token-org {refresh['org']}): {refresh['refreshes']} new tokens minted"
              + (f"; {refresh['failures']} refreshes failed (see the WARNING above)" if refresh["failures"] else ""))
    unauthorized = summary["counts"]["infra_by_kind"].get("http_401")
    if unauthorized and not refresh:
        print(f"{unauthorized} calls were refused with HTTP 401: the SFAP token has probably expired (it lasts "
              "about 2 h). Run resolve-token.sh again before a rerun. Pass --token-org <alias> to refresh it "
              "during the run, and --cache-dir so that a rerun sends only what is unanswered")
    if c.get("timed_out_units"):
        print(f"{c['timed_out_units']} units timed out on every repeat: the model may not finish them (a runaway "
              "answer). Here they are infra errors, left out of the scores; bt_compare scores them 0 (no answer) "
              "against a run that answered them on another request or model")
    print(f"outputs: {out_dir}/ units.jsonl results.jsonl summary.json replay_results_sfap.csv")
    print(f"report:  python3 {os.path.relpath(os.path.join(os.path.dirname(__file__), 'build_report.py'))} {out_dir}")


def main(argv=None):
    args = parse_args(argv)
    cfg = load_agent_config(args.agent_config)
    if args.router_nodes:
        router_nodes = [n.strip() for n in args.router_nodes.split(",") if n.strip()]
    else:
        router_nodes = cfg.get("router_nodes") or list(unitlib.DEFAULT_ROUTER_NODES)
    base_url, token_file, tenant = sfap_config(args.token_info)
    org_id = args.org_id or (tenant.rstrip("/").rsplit("/", 1)[-1] if tenant else None)

    prepare_out_dir(args.out_dir, args.overwrite)
    units, skipped, inputs, dupes = load_units(args, set(router_nodes), org_id)
    units, exclude_info = exclude_sessions(units, skipped, args)  # another run's sessions: not input at all
    session_sets, versions_report = attribute_versions(units, args)  # on every unit: a session's other steps count
    split_info = label_splits(units, args)
    units = select_units(units, skipped, args, session_sets, versions_report)
    if versions_report is not None:
        results.write_json(os.path.join(args.out_dir, "versions.json"), versions_report)
    results.write_jsonl(os.path.join(args.out_dir, "units.jsonl"), units)
    kinds = Counter(results.unit_kind(u) for u in units)
    print(f"{len(units)} units ({', '.join(f'{k} {v}' for k, v in sorted(kinds.items()))}); "
          f"skipped steps: {dict(skipped) or 'none'}" + (f"; duplicate sessions ignored: {dupes}" if dupes else ""))
    if not units:
        raise SystemExit("no units to replay (the skipped steps above say why)")
    requests, patch_info = apply_patch(units, args.patch, args.out_dir)
    total_jobs = len(units) * args.k
    if total_jobs > args.max_replay_targets:
        raise SystemExit(f"run would dispatch {total_jobs} replay calls ({len(units)} units x {args.k}), "
                         f"exceeding --max-replay-targets {args.max_replay_targets}; "
                         f"reduce --limit or --k, or raise --max-replay-targets")
    if args.dry_run:
        print(f"dry run: wrote {args.out_dir}/units.jsonl" + (" and patch_coverage.json" if args.patch else ""))
        return 0

    candidates = sorted({u["request"]["model"] for u in units}) if args.model == "trace" else [args.model]
    try:
        judgelib.check_judge_model(args.judge_model, candidates)
        refresher = (tokenlib.TokenRefresher(token_file, args.token_org, base_url, tenant)
                     if args.token_org and token_file else None)
        client = SfapClient(base_url, token_file, tenant, timeout=args.timeout, max_retries=args.max_retries,
                            on_unauthorized=refresher)
        if args.cache_dir:
            client = cachelib.CachingClient(client, args.cache_dir)
    except (ValueError, OSError) as e:
        raise SystemExit(f"config error: {e}")
    family = judgelib.same_family(args.judge_model, candidates)
    if family:
        print(f"WARNING: judge {args.judge_model} is the same model family as {', '.join(family)}; "
              "its text verdicts may favour that model")
    warn_loose_mode(token_file, "the SFAP token file", "0600")
    if args.cache_dir:
        warn_loose_mode(args.cache_dir, f"--cache-dir {args.cache_dir}", "0700")
    judge = judgelib.Judge(client, args.judge_model)
    equivalence = scoring.Equivalence(cfg.get("equivalent_tools"))

    config = {"model": args.model, "candidate_models": candidates, "judge_model": args.judge_model,
              "judge_same_family": family, "steps": args.steps, "router_nodes": sorted(router_nodes),
              "equivalent_tools": cfg.get("equivalent_tools") or [], "arg_defaults": cfg.get("arg_defaults") or {},
              "k": args.k, "seed": args.seed,
              "limit": args.limit, "timeout": args.timeout, "max_retries": args.max_retries,
              "concurrency": args.concurrency, "inputs": [os.path.basename(p) for p in inputs],
              "org": org_id, "agent": args.agent, "sfap_base_url": base_url, "patch": patch_info,
              "versions": None if versions_report is None else {
                  "source": versions_report["source"], "labels": [v["label"] for v in versions_report["versions"]],
                  "selected": args.agent_version},
              "split": split_info, "exclude_sessions": exclude_info,
              "cache": {"dir": os.path.basename(os.path.abspath(args.cache_dir))} if args.cache_dir else None,
              "token_refresh": {"org": args.token_org} if refresher else None,
              "code": results.code_fingerprint(),
              "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    print(f"replaying {len(units)} units x {args.k} on {args.model} (judge {args.judge_model}, "
          f"concurrency {args.concurrency})")
    records, interrupted = replay(units, requests, args, client, judge, equivalence, args.out_dir,
                                  cfg.get("arg_defaults"))
    config["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    config["interrupted"] = interrupted
    if args.cache_dir:
        config["cache"].update(client.stats())
    if refresher:
        config["token_refresh"].update(refresher.stats())
    summary = results.summarize(records, config, skipped, unit_count=len(units))
    results.write_json(os.path.join(args.out_dir, "summary.json"), summary)
    results.write_csv(os.path.join(args.out_dir, "replay_results_sfap.csv"), records)
    print_summary(summary, args.out_dir)
    if interrupted:
        return 130
    return 0 if summary["counts"]["scored"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except stdm.StdmError as e:
        sys.exit(f"STDM input error: {redact(str(e))}")
