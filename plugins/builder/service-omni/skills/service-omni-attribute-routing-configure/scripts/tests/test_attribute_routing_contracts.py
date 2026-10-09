#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = SKILLS_ROOT / "service-omni-attribute-routing-configure/scripts/configure-and-report.sh"
DEFAULT_SF = """#!/usr/bin/env bash
[ "$1 $2" = "org display" ] && echo '{"status":0,"result":{}}' && exit 0
echo unexpected >&2
exit 1
"""


def run_script(*args: str, sf_source: str = DEFAULT_SF, extra_env: dict[str, str] | None = None):
    with tempfile.TemporaryDirectory(prefix="attribute-routing-sf-") as directory:
        sf = Path(directory) / "sf"
        sf.write_text(sf_source)
        sf.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = directory + os.pathsep + env.get("PATH", "")
        env.update(extra_env or {})
        return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env)


class AttributeRoutingContracts(unittest.TestCase):
    def test_script_syntax(self):
        result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_create_rejects_unsupported_entity_before_write(self):
        result = run_script("org", "create", "Rule", "Rule", "Account")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unsupported related entity", result.stdout)

    def test_create_reuses_matching_inactive_rule(self):
        sf_source = """#!/usr/bin/env bash
case "$1 $2" in
  "org display") echo '{"status":0,"result":{}}' ;;
  "api request")
    if [[ " $* " == *"WorkSkillRouting/describe"* ]]; then
      echo '{"createable":true}'
    elif [[ " $* " == *"WorkSkillRouting/0Xaxx0000000001AAA"* ]]; then
      echo '{"Id":"0Xaxx0000000001AAA","Metadata":{"masterLabel":"Eval Case Routing","relatedEntity":"Case","isActive":false,"workSkillRoutingAttributes":[]}}'
    else
      exit 1
    fi
    ;;
  "data query")
    if [[ " $* " == *" FROM WorkSkillRouting WHERE DeveloperName = 'Eval_Case_Routing' "* ]]; then
      echo '{"status":0,"result":{"records":[{"Id":"0Xaxx0000000001AAA"}]}}'
    else
      exit 1
    fi
    ;;
  *) exit 1 ;;
esac
"""
        result = run_script(
            "org", "create", "Eval_Case_Routing", "Eval Case Routing", "Case",
            sf_source=sf_source,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response["status"], "reused")
        self.assertEqual(response["result"]["record"]["Id"], "0Xaxx0000000001AAA")

    def test_supported_service_entities_include_voice_and_incident(self):
        source = SCRIPT.read_text()
        self.assertIn("Incident", source)
        self.assertIn("VoiceCall", source)
        self.assertIn("ChangeRequest", source)
        self.assertIn("Problem", source)

    def test_add_attribute_rejects_level_above_ten(self):
        result = run_script(
            "org", "add-attribute", "0Xaxx0000000001AAA", "Case.Priority", "High",
            "0C5xx0000000001AAA", "10.1", "Case",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("between 0 and 10", result.stdout)

    def test_activation_preserves_complete_metadata(self):
        source = SCRIPT.read_text()
        self.assertIn(".Metadata | del(.urls) | .isActive=$active", source)
        self.assertIn("workSkillRoutingAttributes", source)

    def test_failures_are_emitted_from_parent_shell(self):
        source = SCRIPT.read_text()
        self.assertNotIn("$(request ", source)
        self.assertIn('REQUEST_OUTPUT=$(FORCE_COLOR=0 sf api request rest', source)

    def test_deletes_require_explicit_confirmation(self):
        result = run_script("org", "delete-rule", "0Xaxx0000000001AAA")
        self.assertEqual(result.returncode, 1)
        self.assertIn("CONFIRM_DELETE=1", result.stdout)

    def test_deletes_use_tooling_data_delete_instead_of_bodyless_rest(self):
        cases = (
            ("delete-rule", "WorkSkillRouting", "0Xaxx0000000001AAA"),
            ("delete-attribute", "WorkSkillRoutingAttribute", "0Yaxx0000000001AAA"),
        )
        for operation, object_name, record_id in cases:
            with self.subTest(operation=operation):
                sf_source = f"""#!/usr/bin/env bash
case "$1 $2" in
  "org display") echo '{{"status":0,"result":{{}}}}' ;;
  "api request")
    case " $* " in *" --method DELETE "*) exit 23 ;; *) echo '{{"createable":true}}' ;; esac
    ;;
  "data query") echo '{{"status":0,"result":{{"records":[{{"IsSandbox":true,"TrialExpirationDate":null,"OrganizationType":"Enterprise Edition"}}]}}}}' ;;
  "data delete")
    [ "$3" = "record" ] || exit 1
    [[ " $* " == *" --sobject {object_name} "* ]] || exit 1
    [[ " $* " == *" --record-id {record_id} "* ]] || exit 1
    [[ " $* " == *" --use-tooling-api "* ]] || exit 1
    echo '{{"status":0,"result":{{"id":"{record_id}","success":true,"errors":[]}}}}'
    ;;
  *) exit 1 ;;
esac
"""
                result = run_script(
                    "org", operation, record_id,
                    sf_source=sf_source,
                    extra_env={"CONFIRM_DELETE": "1"},
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual("deleted", json.loads(result.stdout)["status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
