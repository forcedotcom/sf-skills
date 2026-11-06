"""Prepare and deploy a dedicated ECA without embedding consumer credentials."""

import json
from pathlib import Path
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET

from .evaluation import write_json
from .onboarding import APP_LABEL, APP_NAME, CLIError, deployment_details, discover_eca, sf


NS = "http://soap.sforce.com/2006/04/metadata"
ET.register_namespace("", NS)


def _xml(path, kind, values):
    root = ET.Element("{" + NS + "}" + kind)
    for key, value in values.items():
        ET.SubElement(root, "{" + NS + "}" + key).text = str(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)


def require_eca_api(version):
    """Reject incompatible plans before creating any local or remote ECA metadata."""
    if not re.fullmatch(r"[0-9]{2,3}\.0", str(version)) or int(str(version).split('.')[0]) < 65:
        raise ValueError("ECA JWT timeout policies require API 65.0 or later; refresh the CLI org API version before preparation")


def prepare_eca(org, workspace, contact_email, run_as, app_name=APP_NAME):
    """Write a reviewable local ECA project and deployment plan for one org."""
    require_eca_api(org["api_version"])
    project = Path(workspace) / "eca"
    if project.exists():
        detail = "Review and reuse eca/plan.json." if (project / "plan.json").is_file() else (
            "Preparation is incomplete. Back up and move the local eca directory aside, then run prepare-eca again.")
        raise ValueError(f"ECA project already exists at {project}. {detail} Inspect org deployment status before any redeployment.")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,59}", app_name):
        raise ValueError("ECA API name must be an identifier of at most 60 characters")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact_email or ""):
        raise ValueError("A contact email is required")
    if not run_as or any(c in run_as for c in ("'", "\\", "\n", "\r")):
        raise ValueError("Supply the exact active Run As username")
    if discover_eca(org, app_name):
        raise ValueError("The optimizer ECA already exists; reuse its credentials instead of creating a duplicate")
    result = sf(["data", "query", "--target-org", org["alias"], "--query",
                 f"SELECT Id, Username, IsActive FROM User WHERE Username = '{run_as}' AND IsActive = true"])
    if not isinstance(result, dict) or len(result.get("records", [])) != 1:
        raise ValueError("Run As must resolve to exactly one active user in the selected org")
    with tempfile.TemporaryDirectory(prefix=".eca-prepare-", dir=workspace) as temporary:
        staged = Path(temporary)
        plan = _prepare_project(org, staged, contact_email, run_as, app_name)
        if project.exists():
            raise ValueError("ECA preparation appeared concurrently; inspect the existing project before retrying")
        staged.rename(project)
    return plan


def _prepare_project(org, project, contact_email, run_as, app_name):
    """Publish only a complete prepared tree; failures leave no abandoned project."""
    write_json(project / "sfdx-project.json", {"packageDirectories": [{"path": "force-app", "default": True}],
                                             "namespace": "", "sourceApiVersion": org["api_version"]})
    base = project / "force-app/main/default"
    permission = app_name + "_Access"
    _xml(base / f"externalClientApps/{app_name}.eca-meta.xml", "ExternalClientApplication", {
        "contactEmail": contact_email, "description": "Customer-org access for HyperClassifier evaluation and optimization.",
        "distributionState": "Local", "isProtected": "false", "label": APP_LABEL})
    _xml(base / f"extlClntAppGlobalOauthSets/{app_name}_glbloauth.ecaGlblOauth-meta.xml", "ExtlClntAppGlobalOauthSettings", {
        "callbackUrl": "https://login.salesforce.com/services/oauth2/success", "externalClientApplication": app_name,
        "isClientCredentialsFlowEnabled": "true", "isConsumerSecretOptional": "false", "isIntrospectAllTokens": "false",
        "isNamedUserJwtEnabled": "true", "isPkceRequired": "true", "isSecretRequiredForRefreshToken": "true",
        "label": APP_LABEL + " Global OAuth", "shouldRotateConsumerKey": "false", "shouldRotateConsumerSecret": "false"})
    _xml(base / f"extlClntAppOauthSettings/{app_name}_oauth.ecaOauth-meta.xml", "ExtlClntAppOauthSettings", {
        "commaSeparatedOauthScopes": "Api, RefreshToken, SFApiPlatform", "externalClientApplication": app_name,
        "label": APP_LABEL + " OAuth"})
    _xml(base / f"permissionsets/{permission}.permissionset-meta.xml", "PermissionSet", {
        "description": "ECA preauthorization only; grants no additional object or system permissions.",
        "hasActivationRequired": "false", "label": "HyperClassifier Optimizer Access"})
    plan = {"org_id": org["org_id"], "instance_url": org["instance_url"], "alias": org["alias"],
            "app_name": app_name, "app_label": APP_LABEL, "run_as": run_as, "permission_set": permission,
            "api_version": org["api_version"], "scopes": ["api", "refresh_token", "sfap_api"],
            "flow": "client_credentials", "jwt_minutes": 30, "ip_policy": "Enforce",
            "state": "prepared", "steps": []}
    write_json(project / "plan.json", plan)
    return plan


def _deploy(project, org, paths, plan, stage):
    arguments = ["project", "deploy", "start", "--target-org", org["alias"], "--wait", "10"]
    for path in paths:
        arguments.extend(["--source-dir", str(path)])
    record = {"status": "Submitting"}
    plan["steps"].append({stage: record})
    write_json(project / "plan.json", plan)
    try:
        try:
            result = sf(arguments, cwd=project, timeout=720)
        except CLIError as error:
            record.update(error.deployment)
            raise
        record.update(deployment_details(result))
        if record.get("status") != "Succeeded" or not record.get("deployment_id"):
            raise ValueError("Metadata deployment did not complete with a confirmed job ID")
    except ValueError as error:
        job = record.get("deployment_id")
        recovery = (f"Run sf project deploy report --target-org {org['alias']} --job-id {job}."
                    if job else "Inspect org deployment status; no job ID was returned.")
        raise ValueError(f"{error}. Recovery: {recovery} Saved in eca/plan.json; do not redeploy blindly.") from None
    finally:
        write_json(project / "plan.json", plan)


def _update_policy(path, values, app_name):
    tree = ET.parse(path)
    root = tree.getroot()
    parent = root.find("{" + NS + "}externalClientApplication")
    if parent is None or parent.text != app_name:
        raise ValueError("Retrieved policy does not belong to the prepared ECA")
    for key, value in values.items():
        element = root.find("{" + NS + "}" + key)
        if element is None:
            element = ET.SubElement(root, "{" + NS + "}" + key)
        element.text = str(value)
    # Metadata serializers use schema ordering; these fields are alphabetic in retrieved policies.
    root[:] = sorted(root, key=lambda element: element.tag)
    ET.indent(root)
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def deploy_eca(org, workspace):
    """Deploy once, retrieve generated policies, configure preauthorization, and assign it."""
    project = Path(workspace) / "eca"
    plan = json.loads((project / "plan.json").read_text(encoding="utf-8"))
    if plan.get("org_id") != org["org_id"] or plan.get("instance_url") != org["instance_url"]:
        raise ValueError("ECA deployment plan belongs to another org")
    if plan["state"] != "prepared":
        raise ValueError("Deployment was already attempted; inspect plan.json and org deployment status before recovery")
    require_eca_api(plan.get("api_version"))
    if discover_eca(org, plan["app_name"]):
        raise ValueError("ECA appeared after preparation; refusing to overwrite it")
    base = project / "force-app/main/default"
    plan["state"] = "deploying"
    write_json(project / "plan.json", plan)
    try:
        _deploy(project, org, [base], plan, "base")
        app = plan["app_name"]
        oauth_name, policy_name = app + "_oauth_defaultPolicy", app + "_defaultPolicy"
        sf(["project", "retrieve", "start", "--target-org", org["alias"], "--wait", "10",
            "--metadata", "ExtlClntAppOauthConfigurablePolicies:" + oauth_name,
            "--metadata", "ExtlClntAppConfigurablePolicies:" + policy_name], cwd=project, timeout=720)
        oauth = base / f"extlClntAppOauthPolicies/{oauth_name}.ecaOauthPlcy-meta.xml"
        policy = base / f"extlClntAppPolicies/{policy_name}.ecaPlcy-meta.xml"
        backup = project / "retrieved-policy-backup"
        backup.mkdir(mode=0o700)
        for path in (oauth, policy):
            if not path.is_file():
                raise ValueError("Generated policy names differ; inspect metadata and retrieve the app's policies before continuing")
            shutil.copy2(path, backup / path.name)
        _update_policy(oauth, {"clientCredentialsFlowUser": plan["run_as"],
                              "commaSeparatedPermissionSet": plan["permission_set"],
                              "ipRelaxationPolicyType": "Enforce", "isClientCredentialsFlowEnabled": "true",
                              "namedUserJwtSessionTimeoutType": "Custom", "namedUserJwtTimeout": "30",
                              "permittedUsersPolicyType": "AdminApprovedPreAuthorized"}, app)
        _update_policy(policy, {"isEnabled": "true", "isOauthPluginEnabled": "true"}, app)
        _deploy(project, org, [oauth, policy], plan, "policies")
        assigned = sf(["org", "assign", "permset", "--target-org", org["alias"],
                       "--name", plan["permission_set"], "--on-behalf-of", plan["run_as"]])
        if isinstance(assigned, dict) and assigned.get("failures"):
            raise ValueError("Permission-set assignment reported failures")
        plan["state"] = "awaiting_credentials"
        return plan
    finally:
        if plan["state"] == "deploying":
            plan["state"] = "incomplete_check_org_before_retry"
        write_json(project / "plan.json", plan)
