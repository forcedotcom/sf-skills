"""structural validation of the describe CLI recipes.

Before these recipes shipped, `scripts/probe_channels.py::_describe_sobject`
called `run_sf("describe_sobject", ...)` / `run_sf("describe_tooling_sobject",
...)` against YAMLs that didn't exist on disk. Every unit test mocked
`run_sf`, so the suite stayed green — but the first real invocation would
have raised `SfCliError: recipe not found`. This module closes that gap
by loading each YAML via `sf_cli._load_recipe` and asserting the schema
`sf_cli.run_sf` expects.

Deliberately does NOT invoke `sf sobject describe` — that needs a live
org. Structural validation only; the wire-level contract is covered by
the existing probe_channels integration path once the skill ships.
"""
from __future__ import annotations

import unittest
import unittest.mock as mock
from pathlib import Path

from . import _bootstrap  # noqa: F401

import sf_cli  # type: ignore

# SKILL_ROOT is now file-relative (config.py uses
# Path(__file__).resolve().parent.parent), so config.CLI_DIR auto-resolves
# to the repo's assets/cli/ under test. _REPO_CLI_DIR is kept for tests
# that compare paths or pass them as explicit args.
_REPO_CLI_DIR = (
    Path(__file__).resolve().parent.parent.parent / "assets" / "cli"
)


class DescribeRecipeStructureTests(unittest.TestCase):
    """Both describe recipes must parse + conform to the run_sf schema."""

    def setUp(self) -> None:
        # patch the module-level CLI_DIR binding inside sf_cli so
        # _load_recipe reads from the repo's assets/cli/. `sf_cli`
        # imported `CLI_DIR` by name at module load, so we must patch
        # the *local* reference in sf_cli — patching `config.CLI_DIR`
        # alone would leave the stale import behind.
        self._patch = mock.patch.object(sf_cli, "CLI_DIR", _REPO_CLI_DIR)
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def _load(self, name: str) -> dict:
        # _load_recipe is the same function run_sf uses at runtime, so if
        # it parses here it will parse in production. yaml.safe_load + the
        # mapping-shape guard both run inside _load_recipe .
        return sf_cli._load_recipe(name)

    # ---- parsing + mapping shape -----------------------------------------

    def test_describe_sobject_parses(self):
        recipe = self._load("describe_sobject")
        self.assertIsInstance(recipe, dict)
        self.assertEqual(recipe.get("name"), "describe_sobject")

    def test_describe_tooling_sobject_parses(self):
        recipe = self._load("describe_tooling_sobject")
        self.assertIsInstance(recipe, dict)
        self.assertEqual(recipe.get("name"), "describe_tooling_sobject")

    # ---- required_params: a list, covers what probe_channels passes -------

    def test_required_params_are_list_of_strings(self):
        for name in ("describe_sobject", "describe_tooling_sobject"):
            with self.subTest(recipe=name):
                recipe = self._load(name)
                required = recipe.get("required_params")
                self.assertIsInstance(required, list)
                self.assertTrue(
                    all(isinstance(p, str) for p in required),
                    f"{name}: required_params must be list[str]",
                )
                # probe_channels._describe_sobject passes exactly these two.
                # If the recipe drops either, run_sf will SfCliError before
                # the subprocess call — so assert both are present.
                self.assertIn("ORG_ALIAS", required)
                self.assertIn("SOBJECT", required)

    # ---- argv: a list of strings with both placeholders referenced --------

    def test_argv_is_list_of_strings(self):
        for name in ("describe_sobject", "describe_tooling_sobject"):
            with self.subTest(recipe=name):
                recipe = self._load(name)
                argv = recipe.get("argv")
                self.assertIsInstance(argv, list)
                self.assertGreater(len(argv), 0)
                self.assertTrue(
                    all(isinstance(e, str) for e in argv),
                    f"{name}: argv must be list[str]",
                )

    def test_argv_references_both_required_placeholders(self):
        """Every key in required_params must appear as `{{KEY}}` somewhere
        in argv — otherwise the substitution is a no-op and the caller's
        input never reaches the CLI. Defensive sanity check, not a
        functional run.
        """
        for name in ("describe_sobject", "describe_tooling_sobject"):
            with self.subTest(recipe=name):
                recipe = self._load(name)
                argv_joined = " ".join(recipe["argv"])
                for key in recipe.get("required_params") or []:
                    self.assertIn(
                        f"{{{{{key}}}}}", argv_joined,
                        f"{name}: required param {key} not referenced in argv",
                    )

    # ---- success_check contract -----------------------------------------

    def test_success_check_is_stdout_json_status_zero(self):
        """run_sf's success-detection code path (in sf_cli.run_sf) assumes
        `stdout_json_status_zero`. Any other value silently changes the
        pass/fail contract, so pin it.
        """
        for name in ("describe_sobject", "describe_tooling_sobject"):
            with self.subTest(recipe=name):
                recipe = self._load(name)
                self.assertEqual(
                    recipe.get("success_check"), "stdout_json_status_zero",
                )

    # ---- timeout is a positive int ---------------------------------------

    def test_timeout_is_positive_int(self):
        for name in ("describe_sobject", "describe_tooling_sobject"):
            with self.subTest(recipe=name):
                recipe = self._load(name)
                t = recipe.get("timeout_seconds")
                self.assertIsInstance(t, int)
                self.assertGreater(t, 0)

    # ---- auth_required_stderr_patterns -----------------------------------

    def test_auth_patterns_cover_the_known_failures(self):
        """sf CLI surfaces `NoOrgAuthenticationError` for a never-logged-in
        alias and `AuthInfoError` for a stale/revoked session. Both must
        classify as AuthRequired, not a generic SfCliError, so the skill
        can prompt the user to re-login instead of aborting.
        """
        for name in ("describe_sobject", "describe_tooling_sobject"):
            with self.subTest(recipe=name):
                recipe = self._load(name)
                patterns = recipe.get("auth_required_stderr_patterns") or []
                self.assertIn("NoOrgAuthenticationError", patterns)
                self.assertIn("AuthInfoError", patterns)

    # ---- tooling recipe has --use-tooling-api; data-API recipe does NOT ---

    def test_tooling_recipe_uses_tooling_api_flag(self):
        recipe = self._load("describe_tooling_sobject")
        self.assertIn("--use-tooling-api", recipe["argv"])

    def test_data_api_recipe_does_not_use_tooling_api_flag(self):
        """Separating the two recipes rather than toggling via a param
        was a deliberate design call (call sites stay explicit). Verify
        the separation hasn't regressed into a single merged recipe.
        """
        recipe = self._load("describe_sobject")
        self.assertNotIn("--use-tooling-api", recipe["argv"])

    # ---- run_sf missing-param surfacing runs end-to-end through recipe ----

    def test_run_sf_raises_cleanly_when_required_param_absent(self):
        """This exercises the full load_recipe → required_params check
        path inside run_sf, with a REAL (on-disk) recipe rather than a
        mock. If the YAML parses but required_params is malformed, this
        would surface as something other than SfCliError with a clear
        'missing required params' message.
        """
        with self.assertRaises(sf_cli.SfCliError) as ctx:
            # Deliberately omit SOBJECT — should raise at the required-
            # params check, well before subprocess.run. Pass ORG_ALIAS so
            # we isolate the failure to the missing param.
            sf_cli.run_sf("describe_sobject", ORG_ALIAS="whatever")
        self.assertIn("missing required params", str(ctx.exception))
        self.assertIn("SOBJECT", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
