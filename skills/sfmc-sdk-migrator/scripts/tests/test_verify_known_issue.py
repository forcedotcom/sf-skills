"""Regression tests for scripts/verify_known_issue.py.

The verifier's whole reason to exist is to prevent the skill from emitting
false-positive shipped-artifact warnings — so its three headline verdicts
(reproduces / patched / not-materialized) are load-bearing, and the offending
declaration match must be robust to whitespace and access-control differences
that Salesforce might reflow between silent republishes without actually fixing
the bug.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import _bootstrap  # noqa: F401
import verify_known_issue

SCRIPT = os.path.join(_bootstrap.SCRIPTS_DIR, "verify_known_issue.py")

IAM_MODULE_DIR_REL = (
    "Pods/SFInAppMessagingFeatureSDK/InAppMessagingFeatureSDK.xcframework/"
    "ios-arm64/InAppMessagingFeatureSDK.framework/Modules/"
    "InAppMessagingFeatureSDK.swiftmodule"
)


def _write_iam_interface(project, body):
    module_dir = os.path.join(project, IAM_MODULE_DIR_REL)
    os.makedirs(module_dir, exist_ok=True)
    path = os.path.join(module_dir, "arm64-apple-ios.private.swiftinterface")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def _run(project, issue_id="iam-1.0.0-swiftinterface-nodoc"):
    out = subprocess.run(
        [sys.executable, SCRIPT, "--project", project, "--issue-id", issue_id, "--json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


class TestIamSwiftinterfaceVerifier(unittest.TestCase):
    def test_not_materialized_when_no_interface_on_disk(self):
        # An empty project — nothing has been resolved yet. The verifier must
        # report `not-materialized` so the caller runs the resolver and
        # re-verifies rather than emitting an unverified warning.
        with tempfile.TemporaryDirectory() as tmp:
            result = _run(tmp)
        self.assertEqual(result["verdict"], "not-materialized")
        self.assertEqual(result["interfacePaths"], [])
        self.assertIsNone(result["match"])

    def test_reproduces_on_offending_declaration(self):
        # The exact shape from the shipped 1.0.0 xcframework — an extension
        # whose conformance names `SFMCSDK.InAppMessagingFeatureProtocol`.
        with tempfile.TemporaryDirectory() as tmp:
            _write_iam_interface(tmp, (
                "// swift-interface-format-version: 1.0\n"
                "import Foundation\n"
                "public class InAppMessagingFeature {}\n"
                "extension InAppMessagingFeature : SFMCSDK.InAppMessagingFeatureProtocol {}\n"
            ))
            result = _run(tmp)
        self.assertEqual(result["verdict"], "reproduces")
        self.assertEqual(result["match"]["line"], 4)
        self.assertIn("SFMCSDK.InAppMessagingFeatureProtocol", result["match"]["text"])

    def test_reproduces_survives_spi_attribute_and_whitespace(self):
        # Salesforce could reflow the interface with an @_spi attribute or
        # extra whitespace without fixing the underlying bug. The verifier
        # must still fire.
        with tempfile.TemporaryDirectory() as tmp:
            _write_iam_interface(tmp, (
                "public class InAppMessagingFeature {}\n"
                "@_spi(SFMC)   extension  InAppMessagingFeature   :   "
                "SFMCSDK.InAppMessagingFeatureProtocol   {}\n"
            ))
            result = _run(tmp)
        self.assertEqual(result["verdict"], "reproduces")

    def test_patched_when_offending_declaration_absent(self):
        # The interface exists but the protocol reference has been removed.
        # This is the silent-republish case — the warning must be suppressed.
        with tempfile.TemporaryDirectory() as tmp:
            _write_iam_interface(tmp, (
                "public class InAppMessagingFeature {}\n"
                "extension InAppMessagingFeature : Sendable {}\n"
            ))
            result = _run(tmp)
        self.assertEqual(result["verdict"], "patched")
        self.assertEqual(len(result["interfacePaths"]), 1)
        self.assertIsNone(result["match"])

    def test_does_not_match_similar_but_unrelated_declaration(self):
        # An extension on a *different* type that happens to mention
        # SFMCSDK.InAppMessagingFeatureProtocol elsewhere in the module should
        # not trip the check — the pattern anchors on
        # `extension InAppMessagingFeature`.
        with tempfile.TemporaryDirectory() as tmp:
            _write_iam_interface(tmp, (
                "// A comment mentioning SFMCSDK.InAppMessagingFeatureProtocol\n"
                "public class InAppMessagingFeature {}\n"
                "extension SomeOtherType : Sendable {}\n"
            ))
            result = _run(tmp)
        # The pattern requires "extension InAppMessagingFeature" specifically,
        # so a bare comment mention on its own line is not a match.
        self.assertEqual(result["verdict"], "patched")

    def test_unknown_issue_id_rejected_by_argparse(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run(
                [sys.executable, SCRIPT, "--project", tmp,
                 "--issue-id", "bogus-id", "--json"],
                capture_output=True, text=True,
            )
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("invalid choice", out.stderr)


if __name__ == "__main__":
    unittest.main()
