#!/usr/bin/env python3
"""Focused offline tests for on-demand cached org-feature detection."""
from __future__ import annotations

import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from _test_support import load_module

SCRIPTS = Path(__file__).resolve().parent.parent
MODULE_PATH = SCRIPTS / "feature_detection.py"
PLUGIN_ROOT = SCRIPTS.parent


feature = load_module(MODULE_PATH, "feature_detection_under_test")


class FakeRunner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, argv, timeout=None):
        self.calls.append(list(argv))
        if not self.responses:
            raise AssertionError(f"unexpected command: {argv}")
        response = self.responses.pop(0)
        if callable(response):
            return response(argv)
        return response


def ok(payload):
    return feature.CommandResult(True, json.dumps(payload), 0, "")


def fail(reason="nonzero"):
    return feature.CommandResult(False, "sensitive raw output", 1, reason)


def org(api="67.0", org_id="00D-stable", url="https://trial.example.salesforce.com",
        username="must-not-leak@example.com"):
    result = {"id": org_id, "instanceUrl": url, "apiVersion": api, "accessToken": "secret"}
    if username is not None:
        result["username"] = username
    return ok({"result": result})


def describe(queryable=True, relationship="SubscriberPackage"):
    return ok({"result": {"queryable": queryable, "fields": [
        {"name": "SubscriberPackageId", "relationshipName": relationship}
    ]}})


def query(names):
    return ok({"result": {"records": [
        {"Id": f"raw-{index}", "SubscriberPackage": {"Name": name,
         "NamespacePrefix": f"raw_ns_{index}"}}
        for index, name in enumerate(names)
    ]}})


def config(alias="configured-alias"):
    return ok({"result": [{"name": "target-org", "value": alias}]})


class FeatureDetectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name) / "cache"

    def tearDown(self):
        self.tmp.cleanup()

    def run_features(self, args, runner, now=1000.0):
        out, err = io.StringIO(), io.StringIO()
        ticks = iter([0.0, 0.010, 0.020, 0.030, 0.040, 0.050, 0.060, 0.070,
                      0.080, 0.090, 0.100, 0.110, 0.120])
        with redirect_stdout(out), redirect_stderr(err):
            code = feature.run_features(
                args,
                plugin_root=PLUGIN_ROOT,
                runner=runner,
                cache_root=self.cache,
                monotonic=lambda: next(ticks),
                wall_clock=lambda: now,
            )
        return code, out.getvalue(), err.getvalue()

    def refresh_responses(self, names=(), spaces=None):
        return [org(), ok({"dataSpaces": [] if spaces is None else spaces}), describe(), query(names)]

    def test_static_versioned_mapping_is_exact_and_separate_from_cache(self):
        mapping = feature.load_feature_domains(PLUGIN_ROOT)
        self.assertEqual(mapping, {
            "data360": "data360", "devops-center": "dx", "omnistudio": "omnistudio"
        })
        catalog = json.loads((PLUGIN_ROOT / "catalog/feature-domains.json").read_text())
        self.assertEqual(catalog["schemaVersion"], "1.0")
        self.assertEqual(feature.SCHEMA_VERSION, "1.0")
        self.assertEqual(feature.CACHE_SCHEMA_VERSION, "2.0")

    def test_explicit_target_skips_config_and_every_downstream_org_call_is_explicit(self):
        runner = FakeRunner(self.refresh_responses())
        code, out, err = self.run_features(["--target-org", "trial", "--refresh", "--json"], runner)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(runner.calls[0], ["sf", "org", "display", "--target-org", "trial", "--json"])
        self.assertFalse(any(call[1:4] == ["config", "get", "target-org"] for call in runner.calls))
        for call in runner.calls[1:]:
            self.assertTrue(
                ("-o" in call and call[call.index("-o") + 1] == "trial") or
                ("--target-org" in call and call[call.index("--target-org") + 1] == "trial"),
                call,
            )
        self.assertNotIn("trial", out)

    def test_omitted_target_uses_config_then_explicit_downstream_target(self):
        runner = FakeRunner([config("from-config"), *self.refresh_responses()])
        code, out, err = self.run_features(["--refresh", "--json"], runner)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(runner.calls[0], ["sf", "config", "get", "target-org", "--json"])
        self.assertEqual(runner.calls[1], ["sf", "org", "display", "--target-org", "from-config", "--json"])
        self.assertNotIn("from-config", out)

    def test_api_version_is_dynamic_and_nonempty_data_spaces_array_means_present(self):
        runner = FakeRunner([
            org(api="66.0"), ok({"dataSpaces": [{"name": "raw space"}]}), describe(), query([])
        ])
        code, out, _ = self.run_features(["--target-org", "trial", "--refresh", "--json"], runner)
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["apiVersion"], "66.0")
        self.assertIn("/services/data/v66.0/ssot/data-spaces", runner.calls[1])
        d360 = next(item for item in data["features"] if item["feature"] == "data360")
        self.assertEqual(d360["status"], "present")
        self.assertEqual(d360["evidence"], {"kind": "core-rest-reachable", "matchedCount": 1})
        self.assertNotIn("raw space", out)

    def test_empty_data_spaces_is_unknown_and_cache_preserves_empty_limitation(self):
        runner = FakeRunner(self.refresh_responses([], spaces=[]))
        code, out, _ = self.run_features(
            ["--target-org", "trial", "--refresh", "--json"], runner
        )
        item = next(x for x in json.loads(out)["features"] if x["feature"] == "data360")
        self.assertEqual(code, 0)
        self.assertEqual(item["status"], "unknown")
        self.assertEqual(
            item["evidence"], {"kind": "core-rest-reachable-empty", "matchedCount": 0}
        )
        self.assertIn("endpoint reachable", item["limitation"].lower())
        self.assertIn("readiness not established", item["limitation"].lower())

        hit = FakeRunner([org()])
        _, cached, _ = self.run_features(["--target-org", "trial", "--json"], hit, now=1001.0)
        cached_item = next(
            x for x in json.loads(cached)["features"] if x["feature"] == "data360"
        )
        self.assertEqual(cached_item, item)

    def test_cache_reconstruction_matches_fresh_feature_for_every_evidence_kind(self):
        # Fresh probes and cache-hit reconstruction both build rows through _feature,
        # which derives the limitation from the single _LIMITATION_BY_EVIDENCE map —
        # so a cache-hit row is byte-identical to a fresh row for the same evidence,
        # and limitation presence tracks the map (never an independent re-derivation
        # that could drift or drop the text).
        domains = {"data360": "data-cloud", "omnistudio": "omnistudio",
                   "devops-center": "devops-center"}
        samples = [
            ("data360", "present", "core-rest-reachable", 3),
            ("data360", "unknown", "core-rest-reachable-empty", 0),
            ("data360", "unknown", "core-rest-unavailable", 0),
            ("omnistudio", "present", "package-name-match", 2),
            ("omnistudio", "unknown", "package-name-not-detected", 0),
            ("omnistudio", "unknown", "package-inventory-unavailable", 0),
            ("devops-center", "present", "package-name-match", 1),
            ("devops-center", "unknown", "package-name-not-detected", 0),
            ("devops-center", "unknown", "package-inventory-unavailable", 0),
        ]
        for name, status, kind, count in samples:
            with self.subTest(feature=name, kind=kind):
                fresh = feature._feature(name, domains[name], status, kind, count)
                cached_shape = {"feature": name, "status": status,
                                "evidence": {"kind": kind, "matchedCount": count}}
                reconstructed = feature._cache_rows_to_output([cached_shape], domains)[0]
                self.assertEqual(reconstructed, fresh)
                self.assertEqual("limitation" in fresh, feature._limitation(name, kind) is not None)

    def test_data_failure_or_bad_shape_is_unknown_never_absent(self):
        for response in (fail("timeout"), ok({"totalSize": 0})):
            with self.subTest(response=response):
                runner = FakeRunner([org(), response, describe(), query([])])
                code, out, _ = self.run_features(["--target-org", "trial", "--refresh", "--json"], runner)
                item = next(x for x in json.loads(out)["features"] if x["feature"] == "data360")
                self.assertEqual(code, 0)
                self.assertEqual(item["status"], "unknown")
                self.assertNotEqual(item["status"], "absent")
                self.assertIn("permission", item["limitation"].lower())
                self.assertNotIn("sensitive raw output", out)

    def test_describe_precedes_one_query_and_validates_relationship(self):
        runner = FakeRunner(self.refresh_responses(["Other", "Another"]))
        code, out, _ = self.run_features(["--target-org", "trial", "--refresh", "--json"], runner)
        self.assertEqual(code, 0)
        describe_call, query_call = runner.calls[2], runner.calls[3]
        self.assertEqual(describe_call[:4], ["sf", "sobject", "describe", "-s"])
        self.assertIn("--use-tooling-api", describe_call)
        self.assertEqual(sum("query" in call[1:3] for call in runner.calls), 1)
        self.assertIn("LIMIT 100", query_call[query_call.index("--query") + 1])

        for bad_describe in (fail(), describe(queryable=False), describe(relationship="Wrong")):
            with self.subTest(bad_describe=bad_describe):
                blocked = FakeRunner([org(), ok({"dataSpaces": []}), bad_describe])
                code, raw, _ = self.run_features(["--target-org", "trial", "--refresh", "--json"], blocked)
                self.assertEqual(code, 0)
                self.assertEqual(len(blocked.calls), 3, "query must not run after failed validation")
                package = [x for x in json.loads(raw)["features"] if x["feature"] != "data360"]
                self.assertTrue(all(x["status"] == "unknown" for x in package))

    def test_package_name_matches_are_normalized_limited_and_raw_inventory_is_not_retained(self):
        names = ["OmniStudio", "Vlocity Communications", "Salesforce DevOps Center", "Unrelated"]
        runner = FakeRunner(self.refresh_responses(names))
        code, out, _ = self.run_features(["--target-org", "trial", "--refresh", "--json"], runner)
        data = json.loads(out)
        self.assertEqual(code, 0)
        omni = next(x for x in data["features"] if x["feature"] == "omnistudio")
        devops = next(x for x in data["features"] if x["feature"] == "devops-center")
        self.assertEqual((omni["status"], omni["evidence"]["matchedCount"]), ("present", 2))
        self.assertEqual((devops["status"], devops["evidence"]["matchedCount"]), ("present", 1))
        self.assertEqual(omni["evidence"]["kind"], "package-name-match")
        self.assertEqual(devops["evidence"]["kind"], "package-name-match")
        for row in (omni, devops):
            self.assertIn("name", row["limitation"].lower())
            self.assertIn("identity", row["limitation"].lower())
            self.assertIn("legacy status", row["limitation"].lower())
        self.assertIn("vlocity", omni["limitation"].lower())
        cache_blob = "".join(p.read_text() for p in self.cache.glob("*.json"))
        for forbidden in names + ["raw_ns_0", "00D-stable", "must-not-leak", "secret", "trial"]:
            self.assertNotIn(forbidden, out + cache_blob)

    def test_package_name_matching_rejects_helpers_and_unrelated_names(self):
        names = [
            "DevOps Center Helper", "OmniStudio Helper", "Acme DevOps Center Toolkit",
            "Vlocity Helper", "Unrelated Package",
        ]
        runner = FakeRunner(self.refresh_responses(names))
        code, out, _ = self.run_features(["--target-org", "trial", "--refresh", "--json"], runner)
        rows = {x["feature"]: x for x in json.loads(out)["features"]}
        self.assertEqual(code, 0)
        self.assertEqual(rows["omnistudio"]["status"], "unknown")
        self.assertEqual(rows["omnistudio"]["evidence"]["matchedCount"], 0)
        self.assertEqual(rows["devops-center"]["status"], "unknown")
        self.assertEqual(rows["devops-center"]["evidence"]["matchedCount"], 0)
        self.assertEqual(rows["omnistudio"]["evidence"]["kind"], "package-name-not-detected")
        self.assertEqual(rows["devops-center"]["evidence"]["kind"], "package-name-not-detected")

    def test_no_package_match_is_unknown_with_product_specific_blind_spots(self):
        runner = FakeRunner(self.refresh_responses(["Unrelated Package"]))
        _, out, _ = self.run_features(["--target-org", "trial", "--refresh", "--json"], runner)
        rows = {x["feature"]: x for x in json.loads(out)["features"]}
        self.assertEqual(rows["omnistudio"]["status"], "unknown")
        self.assertEqual(rows["omnistudio"]["evidence"]["kind"], "package-name-not-detected")
        self.assertIn("limit 100", rows["omnistudio"]["limitation"].lower())
        self.assertIn("standard", rows["omnistudio"]["limitation"].lower())
        self.assertEqual(rows["devops-center"]["status"], "unknown")
        self.assertEqual(rows["devops-center"]["evidence"]["kind"], "package-name-not-detected")
        self.assertIn("limit 100", rows["devops-center"]["limitation"].lower())
        self.assertIn("next-generation", rows["devops-center"]["limitation"].lower())
        self.assertTrue(all(x["status"] != "absent" for x in rows.values()))

    def test_cache_hit_skips_feature_probes_and_refresh_bypasses_cache(self):
        first = FakeRunner(self.refresh_responses(["OmniStudio", "DevOps Center"]))
        _, refreshed, _ = self.run_features(["--target-org", "alias-one", "--refresh", "--json"], first)
        self.assertEqual(json.loads(refreshed)["cacheState"], "refresh")

        hit = FakeRunner([org()])
        _, cached, _ = self.run_features(["--target-org", "renamed-alias", "--json"], hit, now=1001.0)
        cached_data = json.loads(cached)
        self.assertEqual(cached_data["cacheState"], "cache-hit")
        self.assertEqual(len(hit.calls), 1, "cache identity still requires explicit org display")
        self.assertEqual(cached_data["elapsedMs"]["data360"], 0)
        self.assertEqual(cached_data["elapsedMs"]["packageInventory"], 0)

        bypass = FakeRunner(self.refresh_responses())
        _, rerun, _ = self.run_features(["--target-org", "alias-one", "--refresh", "--json"], bypass, now=1002.0)
        self.assertEqual(json.loads(rerun)["cacheState"], "refresh")
        self.assertEqual(len(bypass.calls), 4)

    def test_cache_identity_includes_canonical_principal_without_persisting_it(self):
        first = FakeRunner([
            org(username="first-principal@example.com"),
            ok({"dataSpaces": []}), describe(), query([]),
        ])
        self.run_features(["--target-org", "first-alias", "--refresh", "--json"], first)

        second = FakeRunner([
            org(username="second-principal@example.com"),
            ok({"dataSpaces": []}), describe(), query([]),
        ])
        code, out, err = self.run_features(["--target-org", "second-alias", "--json"], second, now=1001.0)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(out)["cacheState"], "refresh")
        self.assertEqual(len(second.calls), 4, "a different principal must not share a cache hit")
        files = list(self.cache.glob("*.json"))
        self.assertEqual(len(files), 2)
        cache_blob = "".join(path.read_text(encoding="utf-8") for path in files)
        self.assertNotIn("principal", cache_blob)
        self.assertNotIn("@example.com", cache_blob)

    def test_missing_canonical_principal_fails_bounded_and_does_not_cache(self):
        runner = FakeRunner([org(username=None)])
        code, out, err = self.run_features(["--target-org", "private-alias", "--json"], runner)
        self.assertEqual(code, 2)
        self.assertEqual(err, "")
        self.assertIn("stable identity", out)
        self.assertNotIn("private-alias", out)
        self.assertEqual(len(runner.calls), 1)
        self.assertFalse(self.cache.exists())

    def test_unusable_cache_parent_is_nonfatal_to_normalized_refresh(self):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text("regular file blocks cache directory", encoding="utf-8")
        runner = FakeRunner(self.refresh_responses(["OmniStudio"]))
        code, out, err = self.run_features(
            ["--target-org", "trial", "--refresh", "--json"], runner
        )
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(data["cacheState"], "refresh")
        self.assertEqual([row["feature"] for row in data["features"]], list(feature.FEATURE_ORDER))
        self.assertTrue(self.cache.is_file())

    def test_cache_ttl_corruption_atomic_shape_and_owner_only_mode(self):
        unknown = FakeRunner(self.refresh_responses([]))
        self.run_features(["--target-org", "trial", "--refresh", "--json"], unknown)
        files = list(self.cache.glob("*.json"))
        self.assertEqual(len(files), 1)
        cache_data = json.loads(files[0].read_text())
        self.assertEqual(cache_data["schemaVersion"], "2.0")
        self.assertEqual(cache_data["ttlSeconds"], 300)
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(files[0].stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(self.cache.stat().st_mode), 0o700)
        self.assertNotIn("featureDomains", cache_data)
        self.assertFalse(list(self.cache.glob("*.tmp")))

        files[0].write_text("{corrupt", encoding="utf-8")
        miss = FakeRunner(self.refresh_responses([]))
        _, out, _ = self.run_features(["--target-org", "trial", "--json"], miss, now=1001.0)
        self.assertEqual(json.loads(out)["cacheState"], "refresh")
        self.assertEqual(len(miss.calls), 4)

        present_cache = Path(self.tmp.name) / "present-cache"
        self.cache = present_cache
        present = FakeRunner(self.refresh_responses(
            ["OmniStudio", "DevOps Center"], spaces=[{"name": "raw space"}]
        ))
        self.run_features(["--target-org", "trial", "--refresh", "--json"], present)
        body = json.loads(next(present_cache.glob("*.json")).read_text())
        self.assertEqual(body["ttlSeconds"], 1800)

        stale = json.loads(json.dumps(body["features"]))
        stale[0] = {
            "feature": "data360", "status": "present",
            "evidence": {"kind": "core-rest-reachable", "matchedCount": 0},
        }
        self.assertIsNone(feature._safe_cache_features(stale))
        stale = json.loads(json.dumps(body["features"]))
        stale[1]["evidence"]["kind"] = "legacy-package"
        self.assertIsNone(feature._safe_cache_features(stale))

    def test_expired_unknown_cache_is_a_miss(self):
        first = FakeRunner(self.refresh_responses([]))
        self.run_features(["--target-org", "trial", "--refresh", "--json"], first, now=1000.0)
        expired = FakeRunner(self.refresh_responses([]))
        _, out, _ = self.run_features(["--target-org", "trial", "--json"], expired, now=1301.0)
        self.assertEqual(json.loads(out)["cacheState"], "refresh")
        self.assertEqual(len(expired.calls), 4)

    def test_json_is_bounded_and_human_lists_present_domains_before_unknowns(self):
        runner = FakeRunner(self.refresh_responses([]))
        code, raw, err = self.run_features(["--target-org", "trial", "--refresh", "--json"], runner)
        data = json.loads(raw)
        self.assertEqual((code, err), (0, ""))
        self.assertLess(len(raw), 3000)
        self.assertEqual(data["mode"], "features")
        self.assertEqual(data["featureDomains"], feature.load_feature_domains(PLUGIN_ROOT))
        self.assertEqual(set(data["elapsedMs"]), {"data360", "packageInventory", "total"})

        human_runner = FakeRunner(self.refresh_responses(
            ["OmniStudio"], spaces=[{"name": "raw space"}]
        ))
        code, human, _ = self.run_features(["--target-org", "trial", "--refresh"], human_runner)
        self.assertEqual(code, 0)
        self.assertLess(human.index("Present domains"), human.index("Unknown / limitations"))
        self.assertIn("package-name-match", human)
        self.assertIn("identity", human.lower())
        self.assertIn("legacy status", human.lower())
        self.assertIn("not authoritative absence", human)
        self.assertNotIn("trial", human)

    def test_missing_identity_or_target_and_invalid_flags_fail_bounded_without_echoing_identity(self):
        cases = [
            ([], FakeRunner([ok({"result": []})])),
            (["--target-org", "private-alias", "--json"], FakeRunner([ok({"result": {"apiVersion": "67.0"}})])),
            (["--wat", "private-value", "--json"], FakeRunner([])),
        ]
        for args, runner in cases:
            with self.subTest(args=args):
                code, out, err = self.run_features(args, runner)
                self.assertEqual(code, 2)
                blob = out + err
                self.assertLess(len(blob), 500)
                self.assertNotIn("private", blob)


if __name__ == "__main__":
    unittest.main(verbosity=2)
