"""Tests for the bootstrap-variable parser + channel-mode deriver in assemble_dc.py.

Coverage:
  - `_parse_bootstrap_variables`
      - returns None for missing/NOT_SET/UNSET_VALUE
      - parses well-formed JSON object
      - parses HTML-entity-encoded JSON
      - returns _parse_error dict for malformed JSON
      - returns _parse_error dict for non-object JSON (array, scalar)

  - `_derive_mode`
      - voice  → when RelatedVoiceCallId set
      - production_messaging → when RelatedMessagingSessionId set
      - builder_previewer → when bootstrap has indicator keys
      - unknown → when nothing matches
"""
from __future__ import annotations

import unittest

from . import _bootstrap  # noqa: F401  — sys.path setup

from assemble_dc import _parse_bootstrap_variables, _derive_mode  # type: ignore


class ParseBootstrapVariablesTests(unittest.TestCase):

    def test_none_input_returns_none(self):
        self.assertIsNone(_parse_bootstrap_variables(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(_parse_bootstrap_variables(""))

    def test_not_set_sentinel_returns_none(self):
        self.assertIsNone(_parse_bootstrap_variables("NOT_SET"))

    def test_unset_value_sentinel_returns_none(self):
        self.assertIsNone(_parse_bootstrap_variables("UNSET_VALUE"))

    def test_well_formed_json_object_returns_dict(self):
        out = _parse_bootstrap_variables('{"__resolved_locale__":"en_US","x":1}')
        self.assertEqual(out, {"__resolved_locale__": "en_US", "x": 1})

    def test_html_entity_encoded_json_unescaped_then_parsed(self):
        """Some surfaces emit `&quot;`-encoded JSON. The parser unescapes
        first, then json.loads."""
        encoded = "{&quot;__resolved_locale__&quot;:&quot;en_US&quot;}"
        out = _parse_bootstrap_variables(encoded)
        self.assertEqual(out, {"__resolved_locale__": "en_US"})

    def test_malformed_json_returns_parse_error_dict(self):
        out = _parse_bootstrap_variables("{not-valid-json")
        self.assertIsNotNone(out)
        self.assertTrue(out.get("_parse_error"))
        self.assertIn("_raw", out)

    def test_json_array_returns_parse_error_dict(self):
        """VariableText__c is documented as an object; arrays/scalars are
        defensive cases that surface as _parse_error rather than crash."""
        out = _parse_bootstrap_variables('[1, 2, 3]')
        self.assertTrue(out.get("_parse_error"))

    def test_json_scalar_returns_parse_error_dict(self):
        out = _parse_bootstrap_variables('"just a string"')
        self.assertTrue(out.get("_parse_error"))


class DeriveModeTests(unittest.TestCase):

    def test_voice_call_id_set_returns_voice(self):
        out = _derive_mode(
            messaging_session_id="msg-1",  # ignored when voice present
            voice_call_id="voice-1",
            bootstrap_variables=None,
        )
        self.assertEqual(out, "voice")

    def test_messaging_session_id_set_returns_production_messaging(self):
        out = _derive_mode(
            messaging_session_id="0MwTESTMSG00000",
            voice_call_id=None,
            bootstrap_variables=None,
        )
        self.assertEqual(out, "production_messaging")

    def test_builder_previewer_keys_in_bootstrap_returns_builder_previewer(self):
        bootstrap = {"__resolved_locale__": "en_US", "OpenAgent": "x"}
        out = _derive_mode(
            messaging_session_id=None,
            voice_call_id=None,
            bootstrap_variables=bootstrap,
        )
        self.assertEqual(out, "builder_previewer")

    def test_no_signals_returns_unknown(self):
        out = _derive_mode(
            messaging_session_id=None,
            voice_call_id=None,
            bootstrap_variables={"OpenAgent": "x"},  # no indicator keys
        )
        self.assertEqual(out, "unknown")

    def test_voice_takes_priority_over_messaging(self):
        """Defensive: if both messaging_session_id and voice_call_id are
        set, voice wins (per priority order documented in the function)."""
        out = _derive_mode(
            messaging_session_id="msg-1",
            voice_call_id="voice-1",
            bootstrap_variables=None,
        )
        self.assertEqual(out, "voice")


if __name__ == "__main__":
    unittest.main()
