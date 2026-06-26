#!/usr/bin/env python3
"""Parse Bot.bot + GenAiPlannerBundle → _bundle_parsed.json + PLANNER_NAME.

Replaces old agent Phase 2a (Bot.bot planner-name extraction via XPath-ish
walk) + Phase 2c (bundle XML → topics/plannerActions + generation classifier).

Step 1 — planner name:
  Read $WORK_DIR/sf_meta/wave1_bot/unpackaged/bots/*.bot XML.
  Path: /Bot/botVersions[fullName==$AGENT_VERSION]/conversationDefinitionPlanners[0]
         /genAiPlannerName (fallback: plannerName, fullName)

Step 2 — bundle (only if planner name resolved AND bundle dir exists):
  Read $WORK_DIR/sf_meta/wave1_bundle/unpackaged/genAiPlannerBundles/<plannerName>/
       *.genAiPlannerBundle
  Extract: plannerType, description, masterLabel, localTopics[] with inline
  localActions[], and (classic-only) plannerActions[].
  Classify generation:
    plannerType startswith "AiCopilot__"  → classic
    plannerType startswith "Atlas__"      → nga
    else                                   → unknown

Emits:
  $WORK_DIR/_bundle_parsed.json   (full structured extraction)
  $WORK_DIR/_agent_generation.txt (generation string, newline-terminated)
  stdout: `PLANNER_NAME=<shlex-quoted>\nAGENT_GENERATION=<shlex-quoted>`
          + log lines (topic counts, action counts) for human readability.

If Bot.bot has no <conversationDefinitionPlanners>, prints `PLANNER_NAME=''`
and exits 0 — caller treats the tree as partial.

Usage:
    eval "$(python3 parse_bundle.py)"

Inputs (env):
    WORK_DIR       required
    AGENT_VERSION  required — used to pin the right <botVersions> element

Outputs:
    files (above)
    stdout eval-friendly K=V lines
    exit 0 always (no recoverable error condition; missing XML → empty planner)
"""
import json
import os
import pathlib
import shlex
import sys
import xml.etree.ElementTree as ET


NS = {"sf": "http://soap.sforce.com/2006/04/metadata"}


def _t(el, p):
    if el is None:
        return None
    x = el.find(p, NS)
    return x.text if x is not None else None


def classify_generation(planner_type: str) -> str:
    if not planner_type:
        return "unknown"
    if planner_type.startswith("AiCopilot__"):
        return "classic"
    if planner_type.startswith("Atlas__"):
        return "nga"
    return "unknown"


def extract_planner_name(work_dir: pathlib.Path, target_ver: str) -> str:
    bots_dir = work_dir / "sf_meta" / "wave1_bot" / "unpackaged" / "bots"
    if not bots_dir.exists():
        return ""
    for bot_file in bots_dir.glob("*.bot"):
        try:
            root = ET.parse(bot_file).getroot()
        except ET.ParseError:
            continue
        for bv in root.findall("sf:botVersions", NS):
            full = _t(bv, "sf:fullName") or _t(bv, "sf:developerName")
            if target_ver and full != target_ver:
                continue
            for cdp in bv.findall("sf:conversationDefinitionPlanners", NS):
                n = (_t(cdp, "sf:genAiPlannerName")
                     or _t(cdp, "sf:plannerName")
                     or _t(cdp, "sf:fullName"))
                if n:
                    return n
    return ""


def extract_bundle(work_dir: pathlib.Path, planner_name: str) -> dict:
    bundle = {
        "plannerType": None,
        "plannerName": planner_name or None,
        "generation": "unknown",
        "description": None,
        "masterLabel": None,
        "topics": [],
        "plannerActions": [],
    }

    planner_root = work_dir / "sf_meta" / "wave1_bundle" / "unpackaged" / "genAiPlannerBundles"
    if not planner_root.exists():
        return bundle

    for bundle_dir in planner_root.iterdir():
        if not bundle_dir.is_dir():
            continue
        bundle_xml = list(bundle_dir.glob("*.genAiPlannerBundle"))
        if not bundle_xml:
            continue
        try:
            root = ET.parse(bundle_xml[0]).getroot()
        except ET.ParseError as e:
            sys.stderr.write(f"parse_bundle.py: XML parse error on {bundle_xml[0]}: {e}\n")
            continue

        bundle["plannerType"] = _t(root, "sf:plannerType")
        bundle["generation"] = classify_generation(bundle["plannerType"])
        bundle["description"] = _t(root, "sf:description")
        bundle["masterLabel"] = _t(root, "sf:masterLabel")

        for lt in root.findall("sf:localTopics", NS):
            tname = _t(lt, "sf:developerName") or _t(lt, "sf:fullName")
            if not tname:
                continue
            topic = {
                "name": tname,
                "localDeveloperName": _t(lt, "sf:localDeveloperName"),
                "masterLabel": _t(lt, "sf:masterLabel"),
                "description": _t(lt, "sf:description"),
                "canEscalate": (_t(lt, "sf:canEscalate") or "false").lower() == "true",
                "pluginType": _t(lt, "sf:pluginType"),
                "actions": [],
            }
            for la in lt.findall("sf:localActions", NS):
                aname = _t(la, "sf:developerName") or _t(la, "sf:fullName")
                if not aname:
                    continue
                topic["actions"].append({
                    "name": aname,
                    "localDeveloperName": _t(la, "sf:localDeveloperName"),
                    "masterLabel": _t(la, "sf:masterLabel"),
                    "description": _t(la, "sf:description"),
                    "invocationTarget": _t(la, "sf:invocationTarget"),
                    "invocationTargetType": (_t(la, "sf:invocationTargetType") or "").strip(),
                    "source": _t(la, "sf:source"),
                })
            bundle["topics"].append(topic)

        for pa in root.findall("sf:plannerActions", NS):
            aname = _t(pa, "sf:developerName") or _t(pa, "sf:fullName")
            if not aname:
                continue
            bundle["plannerActions"].append({
                "name": aname,
                "localDeveloperName": _t(pa, "sf:localDeveloperName"),
                "masterLabel": _t(pa, "sf:masterLabel"),
                "description": _t(pa, "sf:description"),
                "invocationTarget": _t(pa, "sf:invocationTarget"),
                "invocationTargetType": (_t(pa, "sf:invocationTargetType") or "").strip(),
                "source": _t(pa, "sf:source"),
            })
        break  # first bundle dir is enough
    return bundle


def atomic_write(path: pathlib.Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, path)


def main() -> int:
    try:
        work_dir = pathlib.Path(os.environ["WORK_DIR"])
        agent_version = os.environ["AGENT_VERSION"]
    except KeyError as e:
        sys.stderr.write(f"parse_bundle.py: missing env {e}\n")
        return 1

    # Step 1: planner name
    planner_name = extract_planner_name(work_dir, agent_version)

    # Step 2: bundle (only if planner resolved)
    bundle = extract_bundle(work_dir, planner_name) if planner_name else {
        "plannerType": None, "plannerName": None, "generation": "unknown",
        "description": None, "masterLabel": None, "topics": [], "plannerActions": [],
    }

    atomic_write(work_dir / "_bundle_parsed.json", json.dumps(bundle, indent=2))
    atomic_write(work_dir / "_agent_generation.txt", bundle["generation"] + "\n")

    # Log lines (stderr would be lost via eval; use stderr for logs not shell-consumed)
    total_actions = (
        sum(len(t["actions"]) for t in bundle["topics"]) + len(bundle["plannerActions"])
    )
    sys.stderr.write(
        f"[parse_bundle] plannerName={planner_name!r} "
        f"plannerType={bundle['plannerType']!r} generation={bundle['generation']}\n"
        f"[parse_bundle]   topics={len(bundle['topics'])} "
        f"topic-scope-actions={sum(len(t['actions']) for t in bundle['topics'])} "
        f"bundle-scope-actions={len(bundle['plannerActions'])} total={total_actions}\n"
    )

    # Eval-friendly stdout
    sys.stdout.write(f"PLANNER_NAME={shlex.quote(planner_name)}\n")
    sys.stdout.write(f"AGENT_GENERATION={shlex.quote(bundle['generation'])}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
