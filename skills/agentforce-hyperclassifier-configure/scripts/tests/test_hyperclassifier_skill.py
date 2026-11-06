"""Offline behavioral coverage for the portable customer-org optimizer skill."""

import base64
import importlib.util
import io
import http.client
from email.utils import formatdate
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
import urllib.error

import pytest


SKILL = Path(__file__).resolve().parents[2]


def _load_module(name, path, package=False):
    spec = importlib.util.spec_from_file_location(
        name, path, submodule_search_locations=[str(path.parent)] if package else None)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_load_module("hcopt", SKILL / "scripts/hcopt/__init__.py", package=True)
from hcopt import client, evaluation, optimizer
from hcopt import onboarding, eca

cli = _load_module("hyperclassifier_skill_cli", SKILL / "scripts/hyperclassifier.py")
setup_cli = _load_module("hyperclassifier_setup_cli", SKILL / "scripts/setup_hyperclassifier.py")
report_cli = _load_module("hyperclassifier_report_cli", SKILL / "scripts/report_hyperclassifier.py")
TOPICS = [{"go_to_orders": "Order help."}, {"go_to_billing": "Billing help."}]
CASES = [{"id": "1", "utterance": "Track a package", "expected_action": "go_to_orders", "group": "primary"},
         {"id": "2", "utterance": "Duplicate charge", "expected_action": "go_to_billing", "group": "control"}]
CREDS = {"SF_INSTANCE_URL": "https://example.my.salesforce.com", "SF_CLIENT_ID": "private-id",
         "SF_CLIENT_SECRET": "private-secret"}


def envelope(action="go_to_orders", probability=0.8):
    """Build a realistic score envelope for deterministic transport-free tests."""
    other = "go_to_billing" if action == "go_to_orders" else "go_to_orders"
    return {"generation_details": {"generations": [
        {"content": action, "parameters": {"probability": probability}},
        {"content": other, "parameters": {"probability": 1 - probability}},
    ]}}


def jwt(expiry=None):
    """Create structurally valid test tokens without real credentials."""
    encode = lambda obj: base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")
    return encode({"alg": "RS256"}) + "." + encode({"exp": expiry or time.time() + 1800}) + ".signature"


class FakeClient:
    """Control classifier outcomes and proposals while recording what was sent."""

    def __init__(self, predictions, proposals=()):
        self.predictions = iter(predictions)
        self.proposals = iter(proposals)
        self.calls = self.http_attempts = 0
        self.prompts = []

    def classify(self, utterance, topics):
        self.calls += 1
        self.http_attempts += 1
        item = next(self.predictions)
        if isinstance(item, BaseException):
            raise item
        return envelope(item)

    def propose(self, model, prompt):
        self.calls += 1
        self.http_attempts += 1
        self.prompts.append(prompt)
        return next(self.proposals)

    def check_proposer(self, model):
        self.calls += 1
        self.http_attempts += 1


def args_for(output, **changes):
    """Return a small optimizer configuration with a bounded test budget."""
    values = dict(output_dir=output, max_rounds=2, patience=2, repeats=1, target_accuracy=1.0,
                  proposer_model="example_model", max_calls=20)
    values.update(changes)
    return SimpleNamespace(**values)


def proposal(description="Existing order help, including tracking."):
    """Change one boundary without changing action names."""
    return json.dumps({"rationale": "Clarify tracking scope", "changes": {"go_to_orders": description}})


@pytest.mark.parametrize("folder", [".claude/skills", ".agents/skills", ".opencode/skills"])
def test_copied_skill_runs_without_source_repo_or_credentials(tmp_path, folder):
    installed = tmp_path / "project with spaces" / folder / SKILL.name
    shutil.copytree(SKILL, installed, ignore=shutil.ignore_patterns("__pycache__"))
    output = tmp_path / "must-not-be-created"
    process = subprocess.run([sys.executable, "-B", str(installed / "scripts/hyperclassifier.py"), "evaluate",
                              "--evals", str(installed / "assets/sample_evals.csv"),
                              "--descriptions", str(installed / "assets/sample_descriptions.json"),
                              "--env-file", str(tmp_path / "missing-secret.env"),
                              "--output-dir", str(output), "--dry-run"],
                             cwd=tmp_path, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    assert "16 cases, 6 actions" in process.stdout
    assert not output.exists()


def test_inputs_bom_and_unknown_expected_action(tmp_path):
    descriptions = tmp_path / "descriptions.json"
    descriptions.write_text(json.dumps(TOPICS))
    cases = tmp_path / "evals.csv"
    cases.write_text("\ufeffutterance,expected_action\nTrack order,go_to_orders\n", encoding="utf-8")
    loaded, topics = evaluation.load_inputs(cases, descriptions)
    assert loaded[0]["id"] == "1" and topics == TOPICS
    cases.write_text("utterance,expected_action\nTrack order,unknown\n")
    with pytest.raises(ValueError, match="unknown expected"):
        evaluation.load_inputs(cases, descriptions)


def test_duplicate_case_ids_rejected(tmp_path):
    descriptions, cases = tmp_path / "descriptions.json", tmp_path / "evals.jsonl"
    descriptions.write_text(json.dumps(TOPICS))
    cases.write_text("\n".join(json.dumps(CASES[0]) for _ in range(2)))
    with pytest.raises(ValueError, match="duplicate id"):
        evaluation.load_inputs(cases, descriptions)


@pytest.mark.parametrize("bad", [True, float("nan"), float("inf"), -0.1, 1.01, "0.5", None, 10**400])
def test_invalid_probability_is_contract_error(bad):
    data = envelope()
    data["generation_details"]["generations"][0]["parameters"]["probability"] = bad
    with pytest.raises(client.ServiceError, match="invalid probability"):
        evaluation.parse_prediction(data, ["go_to_orders", "go_to_billing"])


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
def test_score_set_must_match_all_actions(mutation):
    data = envelope()
    scores = data["generation_details"]["generations"]
    if mutation == "missing":
        scores.pop()
    elif mutation == "duplicate":
        scores[1]["content"] = scores[0]["content"]
    else:
        scores[1]["content"] = "unknown"
    with pytest.raises(client.ServiceError):
        evaluation.parse_prediction(data, ["go_to_orders", "go_to_billing"])


def test_ties_keep_endpoint_order():
    result = evaluation.parse_prediction(envelope("go_to_billing", 0.5), ["go_to_orders", "go_to_billing"])
    assert result["actual_action"] == "go_to_billing" and result["top_tie"] and result["margin"] == 0


def test_credentials_are_literal_data_and_private(tmp_path, monkeypatch):
    for name in client.CREDENTIAL_KEYS:
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / "org.env"
    path.write_text("SF_INSTANCE_URL=https://example.my.salesforce.com\nSF_CLIENT_ID=id\n"
                    "SF_CLIENT_SECRET='$(touch should-not-exist)'\n")
    path.chmod(0o600)
    assert client.load_credentials(path)["SF_CLIENT_SECRET"] == "$(touch should-not-exist)"
    assert not (tmp_path / "should-not-exist").exists()
    path.chmod(0o644)
    with pytest.raises(ValueError, match="private"):
        client.load_credentials(path)


@pytest.mark.parametrize("origin", ["http://example.my.salesforce.com", "https://evil.example", "https://example.my.salesforce.com.evil.example",
                                  "https://user@example.my.salesforce.com", "https://example.my.salesforce.com/path",
                                  "https://example.my.salesforce.com:8443"])
def test_credentials_never_sent_to_arbitrary_origin(monkeypatch, origin):
    for key, value in CREDS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SF_INSTANCE_URL", origin)
    with pytest.raises(ValueError, match="My Domain"):
        client.load_credentials()


def test_redirect_is_refused():
    assert client.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://evil.example") is None


def test_http_error_body_never_leaks_and_retry_is_bounded(monkeypatch):
    attempts = []
    def fail(*args, **kwargs):
        attempts.append(1)
        raise urllib.error.HTTPError("https://api.salesforce.com", 503, "private-secret", {}, io.BytesIO(b"private-secret"))
    transport = client.Client(CREDS, retries=1)
    monkeypatch.setattr(transport.opener, "open", fail)
    monkeypatch.setattr(client.time, "sleep", lambda value: None)
    status, data = transport._request(client.API, b"{}", {})
    assert status == 503 and data == {} and len(attempts) == 2


def test_401_refreshes_once_and_keeps_expected_labels_out(monkeypatch):
    transport = client.Client(CREDS)
    requests = []
    responses = iter([(200, {"access_token": jwt()}), (401, {}), (200, {"access_token": jwt()}), (200, envelope())])
    def request(url, body, headers):
        requests.append((url, body, headers))
        return next(responses)
    monkeypatch.setattr(transport, "_request", request)
    transport.classify("Track order", TOPICS)
    assert len(requests) == 4 and transport.calls == 1
    payload = json.loads(requests[-1][1])
    assert payload["topics_config"]["topics"] == TOPICS
    assert "expected_action" not in json.dumps(payload)
    assert requests[-1][0] == client.API + client.CLASSIFIER_PATH


def test_second_401_stops(monkeypatch):
    transport = client.Client(CREDS)
    responses = iter([(200, {"access_token": jwt()}), (401, {}), (200, {"access_token": jwt()}), (401, {})])
    monkeypatch.setattr(transport, "_request", lambda *args: next(responses))
    with pytest.raises(client.ServiceError, match="HTTP 401"):
        transport.classify("Track order", TOPICS)


@pytest.mark.parametrize("token", ["not-a-jwt", "abc.def.signature", jwt(time.time() - 10), jwt() + "\r\n", jwt(10**400)])
def test_invalid_or_expired_jwt_rejected(token):
    with pytest.raises(client.ServiceError):
        client.jwt_expiry(token)


def test_call_budget_prevents_authentication(monkeypatch):
    transport = client.Client(CREDS, max_calls=1)
    transport.calls = 1
    monkeypatch.setattr(transport, "_authenticate", lambda: pytest.fail("must not authenticate"))
    with pytest.raises(client.ServiceError, match="budget"):
        transport.classify("Track order", TOPICS)


def test_evaluation_reports_repeated_mismatches_and_preserves_inputs(tmp_path):
    original = json.dumps(CASES)
    fake = FakeClient(["go_to_orders", "go_to_orders", "go_to_orders", "go_to_billing"])
    rows = evaluation.evaluate(fake, CASES, TOPICS, tmp_path / "eval", repeats=2)
    report = json.loads((tmp_path / "eval/summary.json").read_text())
    assert len(rows) == 4 and report["pass"] == 3 and report["fail"] == 1
    assert report["cases_passing_every_repeat"] == 1
    assert report["cases_with_varying_predictions"] == 1
    assert report["groups"]["control"]["accuracy"] == 0.5
    assert json.dumps(CASES) == original


def test_service_failure_checkpoints_and_stops_without_fabricating_rows(tmp_path):
    fake = FakeClient(["go_to_orders", client.ServiceError("HTTP 403")])
    folder = tmp_path / "error"
    rows = evaluation.evaluate(fake, CASES, TOPICS, folder, repeats=3)
    run = json.loads((folder / "run.json").read_text())
    assert len(rows) == 2 and run["state"] == "service_error"
    assert run["planned_predictions"] == 6 and run["completed_predictions"] == 2
    assert json.loads((folder / "summary.json").read_text())["error"] == 1


def test_interruption_preserves_completed_results(tmp_path):
    folder = tmp_path / "interrupted"
    with pytest.raises(KeyboardInterrupt):
        evaluation.evaluate(FakeClient(["go_to_orders", KeyboardInterrupt()]), CASES, TOPICS, folder)
    assert json.loads((folder / "run.json").read_text())["state"] == "interrupted"
    assert len((folder / "results.jsonl").read_text().splitlines()) == 1


def test_optimizer_accepts_only_measured_improvement(tmp_path):
    fake = FakeClient(["go_to_orders", "go_to_orders", "go_to_orders", "go_to_billing"], [proposal()])
    state = optimizer.optimize(fake, args_for(tmp_path / "loop"), CASES, TOPICS)
    assert state["state"] == "target_reached" and state["best_round"] == 1
    assert state["baseline"]["pass"] == 1 and state["best_summary"]["pass"] == 2
    assert (tmp_path / "loop/round_001/descriptions.diff").is_file()
    best = json.loads((tmp_path / "loop/best_descriptions.json").read_text())
    assert best[1] == TOPICS[1] and best[0] != TOPICS[0]


def test_optimizer_rejects_regression_and_duplicate_then_stops(tmp_path):
    fake = FakeClient(["go_to_orders", "go_to_orders", "go_to_billing", "go_to_billing"], [proposal(), proposal()])
    state = optimizer.optimize(fake, args_for(tmp_path / "loop"), CASES, TOPICS)
    assert state["state"] == "plateau" and state["best_round"] == 0
    assert [d["reason"] for d in state["history"]] == ["previous_pass_regressed", "duplicate_candidate"]
    assert fake.calls == 7
    assert json.loads((tmp_path / "loop/best_descriptions.json").read_text()) == TOPICS


@pytest.mark.parametrize("text", ['{"rationale":"x","changes":{"new_action":"x"}}',
                                 '{"rationale":"x","changes":{},"labels":[]}', "not-json"])
def test_invalid_proposal_cannot_relabel_or_add_actions(text):
    with pytest.raises(ValueError):
        optimizer.candidate_from_text(text, TOPICS)


def test_holdout_never_enters_proposal_or_selection(tmp_path):
    holdout = [{**CASES[0], "utterance": "UNSEEN HELD OUT TEXT"}]
    fake = FakeClient(["go_to_orders", "go_to_orders", "go_to_orders", "go_to_billing", "go_to_billing"], [proposal()])
    state = optimizer.optimize(fake, args_for(tmp_path / "loop"), CASES, TOPICS, holdout)
    assert state["holdout"]["fail"] == 1 and state["best_round"] == 1
    assert "UNSEEN HELD OUT TEXT" not in fake.prompts[0]


def test_budget_and_holdout_overlap_rejected_before_network(tmp_path):
    descriptions, cases = tmp_path / "descriptions.json", tmp_path / "evals.jsonl"
    descriptions.write_text(json.dumps(TOPICS))
    cases.write_text("\n".join(json.dumps(row) for row in CASES))
    args = cli.build_parser().parse_args(["optimize", "--evals", str(cases), "--descriptions", str(descriptions),
                                        "--output-dir", str(tmp_path / "new"), "--max-calls", "1"])
    with pytest.raises(ValueError, match="Worst-case plan"):
        cli.prepare(args)
    args.max_calls = 100
    args.holdout = cases
    with pytest.raises(ValueError, match="overlaps"):
        cli.prepare(args)


def test_gate_rejects_changed_labels_and_incomplete_results():
    previous = [{**CASES[0], "iteration": 1, "status": "fail", "actual_action": "go_to_billing"}]
    candidate = [{**previous[0], "expected_action": "go_to_billing", "status": "pass"}]
    assert optimizer.gate(previous, candidate) == (False, "evaluation_inputs_changed")
    assert optimizer.gate(previous, []) == (False, "incomplete_or_duplicate_results")


def test_proposer_uses_documented_generation_contract(monkeypatch):
    transport = client.Client(CREDS)
    requests = []
    def post(path, payload):
        requests.append((path, payload))
        return {"generation": {"generatedText": proposal()}}
    monkeypatch.setattr(transport, "post", post)
    assert transport.propose("example_model", "test prompt") == proposal()
    assert requests == [("/einstein/platform/v1/models/example_model/generations", {"prompt": "test prompt"})]


def test_service_error_during_candidate_preserves_previous_best(tmp_path):
    fake = FakeClient(["go_to_orders", "go_to_orders", client.ServiceError("HTTP 403")], [proposal()])
    folder = tmp_path / "loop"
    with pytest.raises(client.ServiceError):
        optimizer.optimize(fake, args_for(folder), CASES, TOPICS)
    state = json.loads((folder / "experiment.json").read_text())
    assert state["state"] == "service_error" and state["best_round"] == 0
    assert json.loads((folder / "best_descriptions.json").read_text()) == TOPICS


def test_holdout_interrupt_is_not_reported_as_completed_target(tmp_path):
    fake = FakeClient(["go_to_orders", "go_to_billing", KeyboardInterrupt()])
    folder = tmp_path / "loop"
    with pytest.raises(KeyboardInterrupt):
        optimizer.optimize(fake, args_for(folder), CASES, TOPICS, [{**CASES[0], "utterance": "Unseen case"}])
    assert json.loads((folder / "experiment.json").read_text())["state"] == "interrupted"


def test_csv_formulas_escaped_but_jsonl_preserves_utterance(tmp_path):
    cases = [{**CASES[0], "utterance": "=SUM(1+2)"}]
    evaluation.evaluate(FakeClient(["go_to_orders"]), cases, TOPICS, tmp_path / "eval")
    assert "'=SUM(1+2)" in (tmp_path / "eval/results.csv").read_text()
    assert json.loads((tmp_path / "eval/results.jsonl").read_text())["utterance"] == "=SUM(1+2)"


def test_expiring_token_is_refreshed_before_inference(monkeypatch):
    transport = client.Client(CREDS)
    transport.token, transport.expires = "old-token", time.time() + 5
    requests = []
    def request(url, body, headers):
        requests.append(url)
        return (200, {"access_token": jwt()}) if url.endswith("/token") else (200, envelope())
    monkeypatch.setattr(transport, "_request", request)
    transport.classify("Track package", TOPICS)
    assert requests[0].endswith("/services/oauth2/token")
    assert requests[1] == client.API + client.CLASSIFIER_PATH


ORG = {"org_id": "00D000000000001AAA", "alias": "customer", "username": "admin@example.com",
       "instance_url": "https://example.my.salesforce.com", "api_version": "68.0"}


def test_org_discovery_redacts_all_authentication_fields(monkeypatch):
    result = {"id": ORG["org_id"], "alias": ORG["alias"], "username": ORG["username"],
              "instanceUrl": ORG["instance_url"], "apiVersion": "68.0", "accessToken": "secret-session",
              "clientId": "private-client", "sfdxAuthUrl": "private-refresh-token"}
    calls = []
    monkeypatch.setattr(onboarding, "sf", lambda args: calls.append(args) or result)
    resolved = onboarding.resolve_org()
    assert resolved == ORG and calls == [["org", "display"]]
    assert "secret" not in json.dumps(resolved) and "private" not in json.dumps(resolved)
    monkeypatch.setattr(onboarding, "sf", lambda args: [result])
    assert "accessToken" not in onboarding.discover_orgs()[0]


def test_new_cli_secret_command_only_returns_token_in_memory(monkeypatch):
    replies = iter([{"username": "admin@example.com"}, {"accessToken": "private-session"}])
    calls = []
    def sf(args):
        calls.append(args)
        return next(replies)
    monkeypatch.setattr(onboarding, "sf", sf)
    assert onboarding.read_org_session("customer") == "private-session"
    assert calls[-1] == ["org", "auth", "show-access-token", "--target-org", "customer"]


def test_cli_failure_never_exposes_raw_secret_output(monkeypatch, capsys):
    monkeypatch.setattr(onboarding.shutil, "which", lambda name: "/fake/sf")
    monkeypatch.setattr(onboarding.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=1, stdout=json.dumps({"status": 1, "name": "AuthError", "message": "private-token"}), stderr="private-token"))
    with pytest.raises(ValueError, match="AuthError") as error:
        onboarding.sf(["org", "display"])
    assert "private-token" not in str(error.value)
    assert "private-token" not in str(capsys.readouterr())


def test_eca_discovery_uses_cli_tooling_session_without_gateway(monkeypatch):
    calls = []
    def sf(args):
        calls.append(args)
        return {"records": [{"Id": "example-app", "DeveloperName": onboarding.APP_NAME,
                             "MasterLabel": onboarding.APP_LABEL, "accessToken": "must-not-escape"}]}
    monkeypatch.setattr(onboarding, "sf", sf)
    records = onboarding.discover_eca(ORG)
    assert "--use-tooling-api" in calls[0]
    assert "ExternalClientApplication" in calls[0][-1]
    assert "must-not-escape" not in json.dumps(records)


def test_failed_eca_query_is_not_treated_as_missing(monkeypatch):
    def sf(args):
        raise ValueError("insufficient permissions")
    monkeypatch.setattr(onboarding, "sf", sf)
    with pytest.raises(ValueError, match="permissions"):
        onboarding.discover_eca(ORG)


def test_missing_eca_inspect_offers_onboarding_without_creating_app(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(setup_cli, "resolve_org", lambda target: ORG)
    monkeypatch.setattr(setup_cli, "discover_eca", lambda *args: [])
    monkeypatch.setattr(setup_cli, "deploy_eca", lambda *args: pytest.fail("No permission to deploy"))
    assert setup_cli.main(["inspect", "--workspace", str(tmp_path / "new")]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["next_step"] == "ask_for_existing_eca_credentials_or_create_eca"
    assert result["cli_session_is_gateway_auth"] is False
    assert not (tmp_path / "new").exists()


def test_private_saved_credentials_are_bound_to_org_and_reused(tmp_path, monkeypatch):
    workspace = onboarding.initialize_workspace(ORG, tmp_path / "profile")
    source = tmp_path / "source.env"
    source.write_text("\n".join(k + "=" + v for k, v in CREDS.items()))
    source.chmod(0o600)
    destination = onboarding.save_credentials(ORG, workspace, source)
    assert destination.stat().st_mode & 0o077 == 0
    assert client.load_credentials(destination) == CREDS
    monkeypatch.setattr(onboarding, "resolve_org", lambda alias: ORG)
    values = onboarding.credentials_for_run(SimpleNamespace(target_org="customer", env_file=None, workspace=workspace))
    assert values == CREDS
    with pytest.raises(ValueError, match="already saved"):
        onboarding.save_credentials(ORG, workspace, source)


def test_workspace_and_credentials_cannot_cross_orgs(tmp_path):
    workspace = onboarding.initialize_workspace(ORG, tmp_path / "profile")
    with pytest.raises(ValueError, match="different org"):
        onboarding.initialize_workspace({**ORG, "org_id": "00D000000000002AAA"}, workspace)
    source = tmp_path / "wrong.env"
    source.write_text("SF_INSTANCE_URL=https://different.my.salesforce.com\nSF_CLIENT_ID=id\nSF_CLIENT_SECRET=secret\n")
    source.chmod(0o600)
    with pytest.raises(ValueError, match="different org origin"):
        onboarding.save_credentials(ORG, workspace, source)
    assert not (workspace / "credentials.env").exists()


def test_existing_project_cannot_become_credential_workspace(tmp_path):
    (tmp_path / "source.py").write_text("print('project')")
    with pytest.raises(ValueError, match="empty private workspace"):
        onboarding.initialize_workspace(ORG, tmp_path)


def test_cli_session_token_never_substitutes_for_missing_eca_credentials(tmp_path, monkeypatch):
    for key in client.CREDENTIAL_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(onboarding, "resolve_org", lambda alias=None: ORG)
    monkeypatch.setattr(onboarding, "workspace_path", lambda org: tmp_path)
    monkeypatch.setattr(onboarding, "read_org_session", lambda target: pytest.fail("Must not use CLI session for inference"))
    with pytest.raises(ValueError, match="onboarding required"):
        onboarding.credentials_for_run(SimpleNamespace(target_org="customer", env_file=None, workspace=None))


def test_eca_prepare_has_only_required_scopes_and_no_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(eca, "discover_eca", lambda *args: [])
    monkeypatch.setattr(eca, "sf", lambda *args: {"records": [{"Username": "admin@example.com", "IsActive": True}]})
    plan = eca.prepare_eca(ORG, tmp_path, "admin@example.com", "admin@example.com")
    assert plan["state"] == "prepared" and plan["scopes"] == ["api", "refresh_token", "sfap_api"]
    xml = "\n".join(p.read_text() for p in (tmp_path / "eca").rglob("*.xml"))
    assert "isNamedUserJwtEnabled>true" in xml
    assert "clientSecret" not in xml and "<userPermissions>" not in xml and ">Full<" not in xml


def test_eca_prepare_rejects_existing_app(tmp_path, monkeypatch):
    monkeypatch.setattr(eca, "discover_eca", lambda *args: [{"Id": "existing"}])
    with pytest.raises(ValueError, match="already exists"):
        eca.prepare_eca(ORG, tmp_path, "admin@example.com", "admin@example.com")
    assert not (tmp_path / "eca").exists()


@pytest.mark.parametrize("run_as", [None, "", "integration@example.com", ORG["username"]])
def test_prepare_cli_warns_only_for_implicit_run_as(tmp_path, monkeypatch, capsys, run_as):
    selected_user = run_as or ORG["username"]
    monkeypatch.setattr(setup_cli, "resolve_org", lambda target: ORG)
    monkeypatch.setattr(eca, "discover_eca", lambda *args: [])
    queries = []
    def sf(arguments):
        queries.append(arguments)
        return {"records": [{"Username": selected_user, "IsActive": True}]}
    monkeypatch.setattr(eca, "sf", sf)
    arguments = ["prepare-eca", "--workspace", str(tmp_path), "--contact-email", "contact@example.com"]
    if run_as is not None:
        arguments.extend(["--run-as", run_as])
    assert setup_cli.main(arguments) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    saved_plan = json.loads((tmp_path / "eca/plan.json").read_text())
    assert result["plan"]["run_as"] == saved_plan["run_as"] == selected_user
    assert result["deployed"] is False
    assert len(queries) == 1 and queries[0][:2] == ["data", "query"]
    assert f"Username = '{selected_user}'" in queries[0][-1]
    if not run_as:
        assert len(result["warnings"]) == 1
        warning = result["warnings"][0]
        assert selected_user in warning and "--run-as" in warning
        assert "permissions" in warning and "dedicated integration user" in warning
        assert captured.err == f"Warning: {warning}\n"
    else:
        assert result["warnings"] == [] and captured.err == ""


def test_eca_policy_is_retrieved_and_backed_up_before_edit(tmp_path, monkeypatch):
    monkeypatch.setattr(eca, "discover_eca", lambda *args: [])
    monkeypatch.setattr(eca, "sf", lambda *args: {"records": [{"Username": "admin@example.com"}]})
    plan = eca.prepare_eca(ORG, tmp_path, "admin@example.com", "admin@example.com")
    calls = []
    def sf(args, cwd=None, timeout=None):
        calls.append(args)
        if args[:3] == ["project", "deploy", "start"]:
            return {"id": "0Af000000000001AAA", "status": "Succeeded"}
        if args[:3] == ["project", "retrieve", "start"]:
            base = cwd / "force-app/main/default"
            app = plan["app_name"]
            eca._xml(base / f"extlClntAppOauthPolicies/{app}_oauth_defaultPolicy.ecaOauthPlcy-meta.xml",
                     "ExtlClntAppOauthConfigurablePolicies", {"externalClientApplication": app, "refreshTokenPolicyType": "SpecificLifetime"})
            eca._xml(base / f"extlClntAppPolicies/{app}_defaultPolicy.ecaPlcy-meta.xml",
                     "ExtlClntAppConfigurablePolicies", {"externalClientApplication": app})
            return {"status": "Succeeded"}
        return {"successes": ["assigned"], "failures": []}
    monkeypatch.setattr(eca, "sf", sf)
    result = eca.deploy_eca(ORG, tmp_path)
    assert result["state"] == "awaiting_credentials"
    assert len(list((tmp_path / "eca/retrieved-policy-backup").glob("*.xml"))) == 2
    policy = next((tmp_path / "eca/force-app/main/default/extlClntAppOauthPolicies").glob("*.xml")).read_text()
    assert "SpecificLifetime" in policy and "AdminApprovedPreAuthorized" in policy and ">Enforce<" in policy
    assert calls[-1][-2:] == ["--on-behalf-of", "admin@example.com"]
    with pytest.raises(ValueError, match="already attempted"):
        eca.deploy_eca(ORG, tmp_path)


def test_deploy_preview_cannot_mutate_org(monkeypatch, tmp_path, capsys):
    workspace = onboarding.initialize_workspace(ORG, tmp_path / "profile")
    (workspace / "eca").mkdir()
    (workspace / "eca/plan.json").write_text('{"state":"prepared"}')
    monkeypatch.setattr(setup_cli, "resolve_org", lambda alias: ORG)
    monkeypatch.setattr(setup_cli, "deploy_eca", lambda *args: pytest.fail("No --apply"))
    assert setup_cli.main(["deploy-eca", "--workspace", str(workspace)]) == 0
    assert "Review this plan" in capsys.readouterr().out


def test_report_shows_the_actual_utterance_expected_and_predicted_action(tmp_path):
    cases = [{**CASES[0], "utterance": "<b>track|package</b>"}]
    evaluation.evaluate(FakeClient(["go_to_billing"]), cases, TOPICS, tmp_path / "run")
    rendered = report_cli.report(tmp_path / "run", failures_only=True)
    assert "&lt;b&gt;track\\|package&lt;/b&gt;" in rendered
    assert "go_to_orders" in rendered and "go_to_billing" in rendered and "1/1 predictions completed" in rendered


@pytest.mark.parametrize('partition', ['', 'sandbox.', 'develop.', 'scratch.', 'demo.', 'trailblaze.', 'patch.'])
def test_verified_my_domain_partitions_work_for_cli_and_credentials(monkeypatch, partition):
    origin = 'https://example.' + partition + 'my.salesforce.com'
    for key, value in dict(CREDS, SF_INSTANCE_URL=origin).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(onboarding, 'sf', lambda args: {
        'id': ORG['org_id'], 'username': ORG['username'], 'instanceUrl': origin})
    assert client.load_credentials()['SF_INSTANCE_URL'] == origin
    assert onboarding.resolve_org('customer')['instance_url'] == origin


@pytest.mark.parametrize('origin', ['https://example.unknown.my.salesforce.com',
    'https://a.b.develop.my.salesforce.com', 'https://example.develop.my.salesforce.com.evil.test',
    'https://user@example.scratch.my.salesforce.com', 'http://example.demo.my.salesforce.com',
    'https://example.trailblaze.my.salesforce.com:443', 'https://example.patch.my.salesforce.com/path',
    'https://example.my.salesforce.com?secret=x', 'https://example.my.salesforce.com#fragment'])
def test_partition_support_preserves_secret_destination_boundary(origin):
    with pytest.raises(ValueError, match='My Domain'):
        client.my_domain_origin(origin)


@pytest.mark.parametrize('wire', [b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\n{}',
                                  b'private-response-data\r\n', b'x' * 66000 + b'\r\n'])
def test_http_protocol_failure_retries_and_records_sanitized_error(tmp_path, monkeypatch, wire):
    class Socket:
        def makefile(self, *args):
            return io.BytesIO(wire)
    calls = []
    def open_response(*args, **kwargs):
        calls.append(1)
        response = http.client.HTTPResponse(Socket())
        response.begin()
        return response
    transport = client.Client(CREDS, retries=1)
    transport.token, transport.expires = 'synthetic-token', time.time() + 1800
    monkeypatch.setattr(transport.opener, 'open', open_response)
    monkeypatch.setattr(client.time, 'sleep', lambda delay: None)
    rows = evaluation.evaluate(transport, CASES, TOPICS, tmp_path / 'run')
    assert len(calls) == 2 and len(rows) == 1 and rows[0]['status'] == 'error'
    assert 'private-response-data' not in json.dumps(rows)
    assert json.loads((tmp_path / 'run/run.json').read_text())['state'] == 'service_error'


@pytest.mark.parametrize('value,expected', [('20', 20), ('date', 20), ('invalid', 1), ('0', 0)])
def test_retry_after_honored_in_request(monkeypatch, value, expected):
    now = 1700000000
    monkeypatch.setattr(client.time, 'time', lambda: now)
    if value == 'date':
        value = formatdate(now + 20, usegmt=True)
    attempts, delays = [], []
    def open_response(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise urllib.error.HTTPError(client.API, 429, 'limited', {'Retry-After': value}, io.BytesIO())
        return io.BytesIO(b'{}')
    transport = client.Client(CREDS, retries=1)
    monkeypatch.setattr(transport.opener, 'open', open_response)
    monkeypatch.setattr(client.time, 'sleep', delays.append)
    assert transport._request(client.API, b'{}', {}) == (200, {})
    assert len(attempts) == 2 and delays == [expected]


@pytest.mark.parametrize('value', ['31', '9' * 5000, 'date'])
def test_long_retry_after_stops_without_early_retry(monkeypatch, value):
    if value == 'date':
        value = formatdate(time.time() + 120, usegmt=True)
    attempts = []
    def limited(*args, **kwargs):
        attempts.append(1)
        raise urllib.error.HTTPError(client.API, 503, 'limited', {'Retry-After': value}, io.BytesIO())
    transport = client.Client(CREDS, retries=3)
    monkeypatch.setattr(transport.opener, 'open', limited)
    monkeypatch.setattr(client.time, 'sleep', lambda delay: pytest.fail('must not retry early'))
    with pytest.raises(client.ServiceError, match='retry later'):
        transport._request(client.API, b'{}', {})
    assert len(attempts) == 1


@pytest.mark.parametrize('ids,valid', [([0, 1], True), ([0, 0], False)])
def test_numeric_zero_ids_preserved_and_duplicates_rejected(tmp_path, ids, valid):
    data, descriptions = tmp_path / 'data.jsonl', tmp_path / 'descriptions.json'
    data.write_text('\n'.join(json.dumps(dict(case, id=id_)) for case, id_ in zip(CASES, ids)))
    descriptions.write_text(json.dumps(TOPICS))
    if valid:
        assert [c['id'] for c in evaluation.load_inputs(data, descriptions)[0]] == ['0', '1']
    else:
        with pytest.raises(ValueError, match='duplicate id'):
            evaluation.load_inputs(data, descriptions)


def test_csv_rejects_unclosed_quote_but_preserves_valid_multiline(tmp_path):
    descriptions, cases = tmp_path / 'descriptions.json', tmp_path / 'evals.csv'
    descriptions.write_text(json.dumps(TOPICS))
    cases.write_text('"utterance,expected_action\n')
    with pytest.raises(ValueError, match='Malformed CSV'):
        evaluation.load_inputs(cases, descriptions)
    cases.write_text('id,expected_action,utterance\n1,go_to_orders,"first\n2,go_to_billing,last\n')
    with pytest.raises(ValueError, match='Malformed CSV'):
        evaluation.load_inputs(cases, descriptions)
    cases.write_text('id,expected_action,utterance\n1,go_to_orders,"first\nsecond"\n2,go_to_billing,last\n')
    rows, _ = evaluation.load_inputs(cases, descriptions)
    assert len(rows) == 2 and rows[0]['utterance'] == 'first\nsecond'


@pytest.mark.parametrize('separator', ['\x85', '\u2028', '\u2029'])
def test_report_accepts_valid_unicode_in_saved_jsonl(tmp_path, separator):
    text = 'Track' + separator + 'package'
    evaluation.evaluate(FakeClient(['go_to_orders']), [dict(CASES[0], utterance=text)], TOPICS, tmp_path / 'run')
    assert text in report_cli.report(tmp_path / 'run')


def test_service_error_confusion_bucket_does_not_collide_with_action():
    rows = [dict(CASES[0], iteration=1, actual_action='ERROR', status='fail'),
            dict(CASES[0], iteration=2, actual_action=None, status='error')]
    evaluation.validate_topics([{'ERROR': 'An action.'}, {'go_to_orders': 'Order help.'}])
    summary = evaluation.summarize(rows)
    assert summary['confusion_matrix']['go_to_orders'] == {'ERROR': 1, '<service_error>': 1}
    assert summary['fail'] == summary['error'] == 1


@pytest.mark.parametrize('failure', ['go_to_billing', client.ServiceError('HTTP 503'), KeyboardInterrupt()])
def test_experiment_report_includes_holdout_failures_errors_and_interruption(tmp_path, failure):
    fake = FakeClient(['go_to_orders', 'go_to_billing', failure])
    folder = tmp_path / 'loop'
    try:
        optimizer.optimize(fake, args_for(folder), CASES, TOPICS, [dict(CASES[0], utterance='UNSEEN HOLDOUT')])
    except (client.ServiceError, KeyboardInterrupt):
        pass
    for only_failures in [False, True]:
        text = report_cli.report(folder, only_failures)
        assert 'Independent holdout results' in text and 'Expected action' in text and 'Repeat stability' in text
        if isinstance(failure, KeyboardInterrupt):
            assert 'interrupted' in text and '0/1 predictions completed' in text
        else:
            assert 'UNSEEN HOLDOUT' in text
        if isinstance(failure, client.ServiceError):
            assert 'HTTP 503' in text and 'service errors: 1' in text


@pytest.mark.parametrize('target', ['best_candidate.json', 'best_descriptions.json', 'best_summary.json'])
@pytest.mark.parametrize('after', [False, True])
def test_interrupted_winner_promotion_reconciles_exports(tmp_path, monkeypatch, target, after):
    original, interrupted = optimizer.write_json, []
    def write(path, value):
        winning = (isinstance(value, dict) and (value.get('round') == 1 or value.get('pass') == 2)) or (
            isinstance(value, list) and value != TOPICS)
        if path.name == target and winning and not interrupted:
            interrupted.append(True)
            if after:
                original(path, value)
            raise KeyboardInterrupt()
        return original(path, value)
    monkeypatch.setattr(optimizer, 'write_json', write)
    folder = tmp_path / 'loop'
    with pytest.raises(KeyboardInterrupt):
        optimizer.optimize(FakeClient(['go_to_orders', 'go_to_orders', 'go_to_orders', 'go_to_billing'], [proposal()]),
                           args_for(folder), CASES, TOPICS)
    winner = json.loads((folder / 'best_candidate.json').read_text())
    state = json.loads((folder / 'experiment.json').read_text())
    assert interrupted and state['state'] == 'interrupted'
    assert state['best_round'] == winner['round'] and state['best_summary'] == winner['summary']
    assert json.loads((folder / 'best_descriptions.json').read_text()) == winner['descriptions']
    assert json.loads((folder / 'best_summary.json').read_text()) == winner['summary']
    assert 'Stop state: interrupted' in report_cli.report(folder)


def test_report_uses_committed_winner_after_stale_state(tmp_path):
    folder = tmp_path / 'loop'
    optimizer.optimize(FakeClient(['go_to_orders', 'go_to_orders', 'go_to_orders', 'go_to_billing'], [proposal()]),
                       args_for(folder), CASES, TOPICS)
    state = json.loads((folder / 'experiment.json').read_text())
    state.update(best_round=0, best_summary=state['baseline'])
    evaluation.write_json(folder / 'experiment.json', state)
    assert '| Correct / completed | 1/2 | 2/2 |' in report_cli.report(folder)


def test_proposer_failure_precedes_baseline_and_is_reportable(tmp_path, monkeypatch):
    fake = FakeClient([])
    def unavailable(model):
        fake.calls += 1
        raise client.ServiceError('Inference HTTP 404')
    monkeypatch.setattr(fake, 'check_proposer', unavailable)
    folder = tmp_path / 'loop'
    with pytest.raises(client.ServiceError):
        optimizer.optimize(fake, args_for(folder), CASES, TOPICS)
    assert fake.calls == 1 and not (folder / 'baseline').exists()
    text = report_cli.report(folder)
    assert 'HTTP 404' in text and 'Tuning evaluation has not started' in text


def test_proposer_preflight_budget_is_explicit(tmp_path):
    descriptions, cases = tmp_path / 'descriptions.json', tmp_path / 'evals.jsonl'
    descriptions.write_text(json.dumps(TOPICS))
    cases.write_text('\n'.join(json.dumps(c) for c in CASES))
    argv = ['--evals', str(cases), '--descriptions', str(descriptions)]
    args = cli.build_parser().parse_args(['preflight', *argv, '--check-proposer', '--max-calls', '1'])
    with pytest.raises(ValueError, match='needs 2 inference calls'):
        cli.prepare(args)
    args = cli.build_parser().parse_args(['optimize', *argv, '--output-dir', str(tmp_path / 'run'),
                                        '--max-rounds', '2', '--max-calls', '8'])
    with pytest.raises(ValueError, match='needs 9 inference calls'):
        cli.prepare(args)


@pytest.mark.parametrize('second', ['private-session', '[REDACTED] use secret command'])
def test_cli_redacted_token_uses_dedicated_command(monkeypatch, second):
    replies = iter([{'accessToken': '[REDACTED] use org auth show-access-token'}, {'accessToken': second}])
    calls = []
    monkeypatch.setattr(onboarding, 'sf', lambda args: calls.append(args) or next(replies))
    if second.startswith('[REDACTED]'):
        with pytest.raises(ValueError, match='No CLI session'):
            onboarding.read_org_session('customer')
    else:
        assert onboarding.read_org_session('customer') == second
    assert calls[-1][:3] == ['org', 'auth', 'show-access-token']


def test_runtime_workspace_uses_setup_normalization(tmp_path, monkeypatch):
    workspace = onboarding.initialize_workspace(ORG, tmp_path / 'profile')
    creds = workspace / 'credentials.env'
    creds.write_text('\n'.join(k + '=' + v for k, v in CREDS.items()))
    creds.chmod(0o600)
    original = Path.expanduser
    monkeypatch.setattr(Path, 'expanduser', lambda path: workspace if str(path) == '~/profile' else original(path))
    args = SimpleNamespace(target_org=None, env_file=None, workspace=Path('~/profile'))
    assert onboarding.credentials_for_run(args) == CREDS


def test_prepare_failure_is_atomic_and_can_be_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(eca, 'discover_eca', lambda *args: [])
    monkeypatch.setattr(eca, 'sf', lambda *args: {'records': [{'Username': ORG['username']}]})
    real = eca.write_json
    def failed_write(*args):
        raise OSError('synthetic write failure')
    monkeypatch.setattr(eca, 'write_json', failed_write)
    with pytest.raises(OSError):
        eca.prepare_eca(ORG, tmp_path, 'admin@example.com', ORG['username'])
    assert not (tmp_path / 'eca').exists() and not list(tmp_path.glob('.eca-prepare-*'))
    monkeypatch.setattr(eca, 'write_json', real)
    assert eca.prepare_eca(ORG, tmp_path, 'admin@example.com', ORG['username'])['state'] == 'prepared'
    with pytest.raises(ValueError, match='Review and reuse'):
        eca.prepare_eca(ORG, tmp_path, 'admin@example.com', ORG['username'])


def test_abandoned_preparation_has_actionable_recovery(tmp_path):
    (tmp_path / 'eca').mkdir()
    (tmp_path / 'eca/keep.txt').write_text('preserve prior work')
    with pytest.raises(ValueError, match='Back up and move'):
        eca.prepare_eca(ORG, tmp_path, 'admin@example.com', ORG['username'])
    assert (tmp_path / 'eca/keep.txt').read_text() == 'preserve prior work'


def test_old_api_is_rejected_before_preparation_or_deployment(tmp_path, monkeypatch):
    monkeypatch.setattr(eca, 'discover_eca', lambda *args: pytest.fail('no org calls'))
    with pytest.raises(ValueError, match='API 65.0'):
        eca.prepare_eca(dict(ORG, api_version='64.0'), tmp_path, 'admin@example.com', ORG['username'])
    assert not (tmp_path / 'eca').exists()
    (tmp_path / 'eca').mkdir()
    evaluation.write_json(tmp_path / 'eca/plan.json', dict(ORG, state='prepared', api_version='64.0'))
    with pytest.raises(ValueError, match='API 65.0'):
        eca.deploy_eca(ORG, tmp_path)


@pytest.mark.parametrize('status,returncode', [('Failed', 1), ('InProgress', 0)])
def test_failed_deployment_retains_job_id_without_raw_cli_output(tmp_path, monkeypatch, status, returncode):
    monkeypatch.setattr(eca, 'discover_eca', lambda *args: [])
    monkeypatch.setattr(eca, 'sf', lambda *args: {'records': [{'Username': ORG['username']}]})
    eca.prepare_eca(ORG, tmp_path, 'admin@example.com', ORG['username'])
    monkeypatch.setattr(onboarding.shutil, 'which', lambda _: '/fake/sf')
    job = '0Af000000000001AAA'
    envelope_ = {'status': returncode, 'name': 'DeployFailed', 'message': 'private-secret',
                 'result': {'id': job, 'status': status, 'accessToken': 'private-secret'}}
    monkeypatch.setattr(onboarding.subprocess, 'run', lambda *a, **k: SimpleNamespace(
        returncode=returncode, stdout=json.dumps(envelope_), stderr='private-secret'))
    monkeypatch.setattr(eca, 'sf', onboarding.sf)
    with pytest.raises(ValueError, match=job) as error:
        eca.deploy_eca(ORG, tmp_path)
    plan = json.loads((tmp_path / 'eca/plan.json').read_text())
    assert plan['steps'][0]['base'] == {'deployment_id': job, 'status': status}
    assert plan['state'] == 'incomplete_check_org_before_retry'
    assert 'private-secret' not in json.dumps(plan) + str(error.value)


@pytest.mark.parametrize('mode', ['missing', 'corrupt', 'wrong-shape'])
def test_report_cli_expected_errors_have_no_traceback(tmp_path, capsys, mode):
    if mode != 'missing':
        (tmp_path / 'run.json').write_text('{' if mode == 'corrupt' else '[]')
    assert report_cli.main(['--run', str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert 'Report error' in captured.err and 'Traceback' not in captured.err


@pytest.mark.parametrize('key', ['groups', 'expected_actions'])
def test_report_rejects_malformed_nested_buckets(tmp_path, capsys, key):
    folder = tmp_path / 'run'
    evaluation.evaluate(FakeClient(['go_to_orders']), CASES[:1], TOPICS, folder)
    summary = json.loads((folder / 'summary.json').read_text())
    summary[key] = []
    evaluation.write_json(folder / 'summary.json', summary)
    assert report_cli.main(['--run', str(folder)]) == 2
    error = capsys.readouterr().err
    assert key in error and 'summary.json' in error and 'Traceback' not in error
