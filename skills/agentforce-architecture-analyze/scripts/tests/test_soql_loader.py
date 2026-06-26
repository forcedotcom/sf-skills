"""Tests for load_soql revalidates every substituted string."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import _bootstrap  # noqa: F401 — sys.path setup


class LoadSoqlValidationTests(unittest.TestCase):
    """every param must be revalidated at the substitution boundary."""

    def setUp(self) -> None:
        # Use a throwaway SOQL_DIR populated per test so we don't depend on
        # the shipped assets having a specific template name.
        self._tmpdir = tempfile.TemporaryDirectory()
        self.soql_dir = Path(self._tmpdir.name)
        # Patch config.SOQL_DIR BEFORE importing soql_loader so the module
        # constant reflects the tmpdir. Because soql_loader binds SOQL_DIR
        # at import, we re-import it fresh under the patch.
        self._patch = mock.patch("config.SOQL_DIR", self.soql_dir)
        self._patch.start()
        # Force a fresh import so load_soql reads the patched SOQL_DIR.
        import importlib
        import soql_loader  # type: ignore
        importlib.reload(soql_loader)
        self.soql_loader = soql_loader

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmpdir.cleanup()

    def _write_template(self, name: str, body: str) -> None:
        (self.soql_dir / f"{name}.soql").write_text(body)

    # ---- happy path -------------------------------------------------------

    def test_valid_param_substitutes(self):
        self._write_template(
            "bot_lookup",
            "SELECT Id FROM BotDefinition WHERE DeveloperName = '{{NAME}}'",
        )
        out = self.soql_loader.load_soql("bot_lookup", NAME="MyAgent")
        self.assertEqual(
            out,
            "SELECT Id FROM BotDefinition WHERE DeveloperName = 'MyAgent'",
        )

    def test_multiple_valid_params(self):
        self._write_template(
            "lookup",
            "SELECT Id FROM Obj WHERE A='{{A}}' AND B='{{B}}'",
        )
        out = self.soql_loader.load_soql("lookup", A="Foo", B="Bar_v2")
        self.assertIn("A='Foo'", out)
        self.assertIn("B='Bar_v2'", out)

    # ---- injection attempts must raise ------------------------------------

    def test_injection_quote_or_clause_raises(self):
        self._write_template("q", "SELECT Id FROM X WHERE Name='{{NAME}}'")
        with self.assertRaises(self.soql_loader.SoqlParamError) as ctx:
            self.soql_loader.load_soql("q", NAME="x' OR Id!=null--")
        self.assertEqual(ctx.exception.key, "NAME")

    def test_injection_drop_table_raises(self):
        self._write_template("q", "SELECT Id FROM X WHERE Name='{{NAME}}'")
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("q", NAME="'; DROP TABLE x;--")

    def test_injection_or_1eq1_raises(self):
        self._write_template("q", "SELECT Id FROM X WHERE Name='{{NAME}}'")
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("q", NAME="x OR 1=1")

    def test_whitespace_rejected(self):
        self._write_template("q", "SELECT Id FROM X WHERE Name='{{NAME}}'")
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("q", NAME="x OR y")  # space

    def test_dash_rejected(self):
        # Common SOQL-injection payload prefix.
        self._write_template("q", "SELECT Id FROM X WHERE Name='{{NAME}}'")
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("q", NAME="x-y")

    # ---- type errors ------------------------------------------------------

    def test_non_string_value_raises(self):
        self._write_template("q", "SELECT {{N}}")
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("q", N=42)

    def test_none_value_raises(self):
        self._write_template("q", "SELECT {{N}}")
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("q", N=None)

    def test_empty_string_raises(self):
        self._write_template("q", "SELECT {{N}}")
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("q", N="")

    # ---- single-pass substitution guarantee -------------------------------

    def test_value_containing_other_placeholder_does_not_retrigger(self):
        """A valid value that contains `{{OTHER}}` must NOT trigger a
        second substitution pass on OTHER. str.replace is single-pass
        by contract; we assert that the validator's regex prevents any
        value from containing `{`, `}`, or whitespace in the first place
        — so the injection path is closed at validation, not at
        substitution.
        """
        self._write_template("q", "SELECT {{A}} AND {{B}}")
        # Reject values that carry placeholder syntax — the regex forbids
        # `{` and `}` (they're not in [A-Za-z0-9_]).
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("q", A="{{B}}", B="safe")

    def test_raw_replace_is_single_pass(self):
        """Belt-and-braces: even if a value slipped through (it cannot,
        per the regex), Python's str.replace does not recursively scan
        the output. Simulate by bypassing the validator and confirming
        str.replace behavior directly.
        """
        template = "SELECT {{A}} AND {{B}}"
        # Substitute A first with a value that "looks like" the B
        # placeholder. str.replace for B should then replace the
        # template's own `{{B}}` — but A's embedded `{{B}}` should stay
        # (Python replaces left-to-right in a single pass; the output
        # of the A replacement is the NEW string and B's pass runs on
        # that new string). The assertion below therefore confirms
        # that B's replacement hits BOTH occurrences (the original and
        # the one inside A's substituted value) — demonstrating that
        # str.replace is NOT recursive on the ORIGINAL template alone,
        # but IS a single linear scan of the full post-A string.
        step1 = template.replace("{{A}}", "{{B}}")
        step2 = step1.replace("{{B}}", "replaced")
        # Both occurrences of `{{B}}` in step1 are replaced in a single
        # left-to-right pass. This is the property tested for.
        self.assertEqual(step2, "SELECT replaced AND replaced")
        # The safety net: if a caller EVER skipped revalidation and
        # allowed a `{{X}}` to reach substitution, the above behavior
        # could matter — which is PRECISELY why revalidates at
        # the boundary. The regex denies `{`, `}`, whitespace, making
        # this scenario unreachable in production.


class LoadSoqlNameValidationTests(unittest.TestCase):
    """the `name` argument is validated before any filesystem access.

    Without this, a caller that sources `name` from data (config file, user
    argument, discovered string) could read arbitrary files via traversal
    (`../../../etc/passwd`). The regex gate closes that before `read_text()`.
    """

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.soql_dir = Path(self._tmpdir.name)
        self._patch = mock.patch("config.SOQL_DIR", self.soql_dir)
        self._patch.start()
        import importlib
        import soql_loader  # type: ignore
        importlib.reload(soql_loader)
        self.soql_loader = soql_loader

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmpdir.cleanup()

    # ---- traversal attempts must raise before any file read ---------------

    def test_parent_traversal_raises(self):
        """`../../../etc/passwd` must be caught by validation, not by the
        filesystem. The error must be SoqlParamError (clearly labeled) —
        NOT a bare FileNotFoundError or a ValidationError with raw path.
        """
        with self.assertRaises(self.soql_loader.SoqlParamError) as ctx:
            self.soql_loader.load_soql("../../../etc/passwd")
        self.assertEqual(ctx.exception.key, "soql_template_name")
        # The absolute SOQL_DIR must NOT appear in the surfaced message.
        self.assertNotIn(str(self.soql_dir), str(ctx.exception))

    def test_dotdot_alone_raises(self):
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("..")

    def test_slash_in_name_raises(self):
        """`/` is not in [A-Za-z0-9_], so `plugins/by_planner` must be
        caught at validation — never reach the filesystem."""
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("plugins/by_planner")

    def test_backslash_in_name_raises(self):
        """Windows-style separators — belt and braces."""
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("plugins\\by_planner")

    def test_absolute_path_raises(self):
        """A caller passing an absolute path (a different traversal variant)
        must still hit validation, not a false-negative file read."""
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("/etc/passwd")

    def test_empty_name_raises(self):
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("")

    def test_none_name_raises(self):
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql(None)  # type: ignore[arg-type]

    def test_whitespace_in_name_raises(self):
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql("bot lookup")

    def test_traversal_never_reads_filesystem(self):
        """Validation runs before any I/O — verify read_text is never
        called when the name is invalid. If the order ever flips, a bad
        name could still leak a FileNotFoundError with raw path info.
        """
        with mock.patch.object(Path, "read_text") as mock_read:
            with self.assertRaises(self.soql_loader.SoqlParamError):
                self.soql_loader.load_soql("../../../evil")
            mock_read.assert_not_called()


class LoadSoqlTemplateNotFoundTests(unittest.TestCase):
    """FileNotFoundError is translated into SoqlTemplateNotFound
    whose message is free of filesystem-path leakage.
    """

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.soql_dir = Path(self._tmpdir.name)
        self._patch = mock.patch("config.SOQL_DIR", self.soql_dir)
        self._patch.start()
        import importlib
        import soql_loader  # type: ignore
        importlib.reload(soql_loader)
        self.soql_loader = soql_loader

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmpdir.cleanup()

    def test_missing_template_raises_custom_exception(self):
        with self.assertRaises(self.soql_loader.SoqlTemplateNotFound) as ctx:
            self.soql_loader.load_soql("nonexistent_template")
        self.assertEqual(ctx.exception.name, "nonexistent_template")

    def test_missing_template_message_excludes_soql_dir(self):
        """The SOQL_DIR absolute path must NOT appear in the surfaced error
        string — information-disclosure hygiene. Attackers don't need to know
        where the skill install lives on disk.
        """
        with self.assertRaises(self.soql_loader.SoqlTemplateNotFound) as ctx:
            self.soql_loader.load_soql("nonexistent_template")
        msg = str(ctx.exception)
        self.assertNotIn(str(self.soql_dir), msg)
        self.assertNotIn(".soql", msg)
        # Template name IS allowed in the message — that's the triage signal.
        self.assertIn("nonexistent_template", msg)

    def test_missing_template_does_not_leak_via_cause_chain(self):
        """`raise ... from None` is load-bearing: without it, the
        FileNotFoundError (with its raw `filename` attribute) would be
        reachable via `exception.__cause__`. Verify the chain is severed.
        """
        try:
            self.soql_loader.load_soql("nonexistent_template")
        except self.soql_loader.SoqlTemplateNotFound as e:
            # `from None` sets __cause__ = None AND __suppress_context__ = True.
            # Either alone suppresses traceback rendering of the underlying
            # FileNotFoundError.
            self.assertIsNone(e.__cause__)
            self.assertTrue(e.__suppress_context__)
        else:
            self.fail("expected SoqlTemplateNotFound")

    def test_not_found_exception_is_distinct_from_file_not_found(self):
        """Callers should be able to tell 'template missing' apart from
        'permission denied / I/O error' at the except-clause layer.
        """
        self.assertFalse(
            issubclass(
                self.soql_loader.SoqlTemplateNotFound,
                FileNotFoundError,
            ),
            "SoqlTemplateNotFound must not subclass FileNotFoundError",
        )

    def test_valid_name_with_params_unchanged(self):
        """Regression: must not break the happy path."""
        (self.soql_dir / "lookup.soql").write_text(
            "SELECT Id FROM X WHERE Name = '{{NAME}}'"
        )
        out = self.soql_loader.load_soql("lookup", NAME="MyAgent")
        self.assertEqual(
            out,
            "SELECT Id FROM X WHERE Name = 'MyAgent'",
        )


class LoadSoqlInListParamTests(unittest.TestCase):
    """`load_soql_in` renders `WHERE X IN (...)` list placeholders.

    Same validation surface as `load_soql` — every list element passes
    through `fs_guard.validate_api_name`. Empty lists fail fast (SOQL
    `WHERE X IN ()` is invalid). Dedup + sort are load-bearing for
    stable cache keys.
    """

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.soql_dir = Path(self._tmpdir.name)
        self._patch = mock.patch("config.SOQL_DIR", self.soql_dir)
        self._patch.start()
        import importlib
        import soql_loader  # type: ignore
        importlib.reload(soql_loader)
        self.soql_loader = soql_loader

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmpdir.cleanup()

    def _write_template(self, name: str, body: str) -> None:
        (self.soql_dir / f"{name}.soql").write_text(body)

    # ---- happy path ------------------------------------------------------

    def test_list_params_render_single_quoted_comma_joined(self):
        self._write_template(
            "apex_by_names",
            "SELECT Id FROM ApexClass WHERE Name IN ({{NAMES_LIST}})",
        )
        out = self.soql_loader.load_soql_in(
            "apex_by_names",
            list_params={"NAMES_LIST": ["ClassA", "ClassB"]},
        )
        self.assertIn("WHERE Name IN ('ClassA','ClassB')", out)

    def test_mixed_string_and_list_params(self):
        self._write_template(
            "functions_q",
            "SELECT Id FROM GenAiFunctionDefinition "
            "WHERE PlannerId = '{{PLANNER_ID}}' OR PluginId IN ({{PLUGIN_IDS}})",
        )
        out = self.soql_loader.load_soql_in(
            "functions_q",
            string_params={"PLANNER_ID": "X"},
            list_params={"PLUGIN_IDS": ["P1", "P2"]},
        )
        self.assertIn("PlannerId = 'X'", out)
        self.assertIn("PluginId IN ('P1','P2')", out)

    def test_string_params_optional(self):
        """string_params defaults to None — list_params alone should work."""
        self._write_template(
            "flow_by_names",
            "SELECT Id FROM FlowDefinition WHERE DeveloperName IN ({{NAMES_LIST}})",
        )
        out = self.soql_loader.load_soql_in(
            "flow_by_names",
            list_params={"NAMES_LIST": ["Flow_A"]},
        )
        self.assertIn("IN ('Flow_A')", out)

    # ---- validation: list elements must match api_name regex ---------------

    def test_injection_in_list_element_raises_with_list_key(self):
        """A SOQL injection attempt inside a list element must raise
        SoqlParamError whose `key` is the LIST key (not the element
        index or a synthetic name) — so the caller can log / mark
        `_unresolved[NAMES_LIST]` at the upstream boundary.
        """
        self._write_template(
            "q", "SELECT Id FROM ApexClass WHERE Name IN ({{NAMES_LIST}})",
        )
        with self.assertRaises(self.soql_loader.SoqlParamError) as ctx:
            self.soql_loader.load_soql_in(
                "q",
                list_params={"NAMES_LIST": ["ClassA", "ClassB'; DROP TABLE x;--"]},
            )
        self.assertEqual(ctx.exception.key, "NAMES_LIST")

    def test_non_string_element_raises(self):
        self._write_template("q", "SELECT Id FROM X WHERE Id IN ({{IDS}})")
        with self.assertRaises(self.soql_loader.SoqlParamError) as ctx:
            self.soql_loader.load_soql_in(
                "q", list_params={"IDS": ["ClassA", 42]},
            )
        self.assertEqual(ctx.exception.key, "IDS")

    def test_whitespace_in_list_element_raises(self):
        self._write_template("q", "SELECT Id FROM X WHERE Id IN ({{IDS}})")
        with self.assertRaises(self.soql_loader.SoqlParamError):
            self.soql_loader.load_soql_in(
                "q", list_params={"IDS": ["ClassA", "x OR 1=1"]},
            )

    # ---- empty list fails fast --------------------------------------------

    def test_empty_list_raises(self):
        """SOQL `WHERE X IN ()` is a syntax error; fail at the loader,
        not at the CLI. The reason string must mention empty so the
        `_unresolved` bucket can be tagged distinctly from injection.
        """
        self._write_template("q", "SELECT Id FROM X WHERE Id IN ({{IDS}})")
        with self.assertRaises(self.soql_loader.SoqlParamError) as ctx:
            self.soql_loader.load_soql_in("q", list_params={"IDS": []})
        self.assertEqual(ctx.exception.key, "IDS")
        self.assertIn("empty", ctx.exception.reason.lower())

    def test_list_params_not_a_list_raises(self):
        """Defensive: a dict or string passed in `list_params[KEY]`
        must be rejected — silently iterating a string would produce
        one-char-per-element SOQL, which is worse than an explicit error.
        """
        self._write_template("q", "SELECT Id FROM X WHERE Id IN ({{IDS}})")
        with self.assertRaises(self.soql_loader.SoqlParamError):
            # type: ignore[arg-type]
            self.soql_loader.load_soql_in("q", list_params={"IDS": "notalist"})

    # ---- dedupe + deterministic order -------------------------------------

    def test_dedupe_eliminates_duplicates(self):
        self._write_template("q", "SELECT Id FROM X WHERE Name IN ({{NS}})")
        out = self.soql_loader.load_soql_in(
            "q", list_params={"NS": ["ClassA", "ClassA", "ClassB"]},
        )
        self.assertEqual(out.count("'ClassA'"), 1)
        self.assertEqual(out.count("'ClassB'"), 1)

    def test_output_is_sorted_for_deterministic_order(self):
        """Stable cache-key requirement: input order MUST NOT affect
        output. `sorted(set(...))` lands ClassA before ClassB regardless
        of input order.
        """
        self._write_template("q", "SELECT Id FROM X WHERE Name IN ({{NS}})")
        out1 = self.soql_loader.load_soql_in(
            "q", list_params={"NS": ["ClassB", "ClassA"]},
        )
        out2 = self.soql_loader.load_soql_in(
            "q", list_params={"NS": ["ClassA", "ClassB"]},
        )
        self.assertEqual(out1, out2)
        # And the order is alphabetical, not input-dependent.
        self.assertLess(out1.index("'ClassA'"), out1.index("'ClassB'"))

    # ---- scalar validation path shared with load_soql ---------------------

    def test_scalar_injection_still_raises(self):
        """string_params go through the same validator as `load_soql` —
        no shortcut. A SOQL-injection attempt in a scalar must still
        surface SoqlParamError.
        """
        self._write_template(
            "q",
            "SELECT Id FROM X WHERE P = '{{PID}}' OR Q IN ({{LIST}})",
        )
        with self.assertRaises(self.soql_loader.SoqlParamError) as ctx:
            self.soql_loader.load_soql_in(
                "q",
                string_params={"PID": "x' OR Id!=null--"},
                list_params={"LIST": ["A"]},
            )
        self.assertEqual(ctx.exception.key, "PID")

    # ---- template-name validation reused ----------------------------------

    def test_template_traversal_raises(self):
        with self.assertRaises(self.soql_loader.SoqlParamError) as ctx:
            self.soql_loader.load_soql_in(
                "../../../evil", list_params={"IDS": ["A"]},
            )
        self.assertEqual(ctx.exception.key, "soql_template_name")

    def test_missing_template_raises_template_not_found(self):
        with self.assertRaises(self.soql_loader.SoqlTemplateNotFound):
            self.soql_loader.load_soql_in(
                "nonexistent_for_in", list_params={"IDS": ["A"]},
            )

    # ---- existing load_soql unchanged -------------------------------------

    def test_load_soql_signature_untouched(self):
        """contract: `load_soql(name, **params)` keeps its original
        signature — no kwargs-only, no extra params. A caller that still
        uses the old form must keep working.
        """
        self._write_template("q", "SELECT Id FROM X WHERE Name = '{{NAME}}'")
        out = self.soql_loader.load_soql("q", NAME="Foo")
        self.assertIn("'Foo'", out)


if __name__ == "__main__":
    unittest.main()
