"""Integration tests for ``assemble_dc._assemble_gateway_direct``.

Drives the materialization-lag path: session row + gateway_requests
populated, but interactions / steps absent. Triggered by setting
``manifest.session_shape = "interactions_not_materialized_yet"``.

Complements ``test_assemble_dc_gateway_direct.py`` which calls the
private function with a hand-built rows dict; this file drives the
public ``assemble`` entry point through the disk-load path so manifest
+ rows + path resolution are all exercised.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from . import _bootstrap  # noqa: F401  — sys.path setup

import assemble_dc  # type: ignore
from config import paths  # type: ignore
from .fixtures.synthetic_session import (  # type: ignore
    IDS, write_to_disk, make_manifest,
)


def _materialization_lag_mutator(sdir: Path) -> None:
    """Make the fixture look like a session whose STDM hierarchy hasn't
    materialized yet: keep gateway_requests + gateway_responses + tags,
    but wipe interactions / steps / messages and flip the manifest.

    This is the live-DC failure mode that the gateway-direct path was
    written to handle.
    """
    # Wipe interaction/step/message rows (file with empty list)
    for name in ("interactions", "steps", "messages"):
        (sdir / f"dc.{name}.json").write_text("[]")
    # Update manifest session_shape so assemble's branch fires.
    manifest = make_manifest()
    manifest["session_shape"] = "interactions_not_materialized_yet"
    (sdir / "dc._session_manifest.json").write_text(
        json.dumps(manifest, indent=2)
    )


class _GatewayDirectHarness:
    def __enter__(self):
        self._tmp = TemporaryDirectory()
        self._tmpdir = Path(self._tmp.name)
        sdir = write_to_disk(self._tmpdir)
        _materialization_lag_mutator(sdir)
        self._patch = mock.patch.object(paths, "DATA_ROOT", self._tmpdir)
        self._patch.start()
        self.tree, self.sdir = assemble_dc.assemble(IDS.SID)
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        self._tmp.cleanup()


# -----------------------------------------------------------------------------
# Top-level shape on the gateway-direct branch
# -----------------------------------------------------------------------------


class GatewayDirectShapeTests(unittest.TestCase):

    def test_source_marker_set_to_gateway_direct(self):
        with _GatewayDirectHarness() as h:
            self.assertEqual(h.tree["_source"], "gateway_direct")

    def test_interactions_is_empty_list(self):
        with _GatewayDirectHarness() as h:
            self.assertEqual(h.tree["session"]["interactions"], [])

    def test_gateway_chain_populated_from_gateway_requests(self):
        with _GatewayDirectHarness() as h:
            chain = h.tree["session"]["gateway_chain"]
        # Fixture has 2 gateway_requests; both make it into the chain.
        self.assertEqual(len(chain), 2)
        chain_ids = {gw["gateway_request_id"] for gw in chain}
        self.assertEqual(chain_ids, {IDS.GW_REQ_DECLARED, IDS.GW_REQ_WINDOW})

    def test_chain_sorted_by_timestamp(self):
        # Earlier gateway request timestamp comes first.
        with _GatewayDirectHarness() as h:
            chain = h.tree["session"]["gateway_chain"]
        timestamps = [gw.get("timestamp") for gw in chain]
        self.assertEqual(timestamps, sorted(t or "" for t in timestamps))

    def test_each_gateway_chain_entry_has_response(self):
        # Only the declared request has a response in the fixture; the
        # window-bound one has response=None. Both shapes are accepted.
        with _GatewayDirectHarness() as h:
            chain = h.tree["session"]["gateway_chain"]
        declared = next(gw for gw in chain
                        if gw["gateway_request_id"] == IDS.GW_REQ_DECLARED)
        self.assertIsNotNone(declared["response"])

    def test_top_identity_block_resolved_from_manifest(self):
        with _GatewayDirectHarness() as h:
            ident = h.tree["identity"]
        self.assertEqual(ident["org_id_15"], IDS.ORG_ID_15)
        self.assertEqual(ident["agent_api_name"], IDS.AGENT_API)
        self.assertEqual(ident["agent_version"], IDS.AGENT_VERSION)

    def test_counts_block_records_session_shape_and_zero_interactions(self):
        with _GatewayDirectHarness() as h:
            counts = h.tree["session"]["counts"]
        self.assertEqual(counts["session_shape"],
                         "interactions_not_materialized_yet")
        self.assertEqual(counts["interactions_total"], 0)
        self.assertEqual(counts["steps_total"], 0)
        self.assertEqual(counts["gateway_requests"], 2)


# -----------------------------------------------------------------------------
# render_dc on the gateway-direct tree
# -----------------------------------------------------------------------------


class GatewayDirectRenderTests(unittest.TestCase):
    """The gateway-direct render branch is short — covers identity,
    lag banner, and gateway-chain table. Drives it end-to-end."""

    def test_render_emits_lag_banner(self):
        import render_dc  # noqa: WPS433
        with _GatewayDirectHarness() as h:
            md = render_dc.render(h.tree, manifest=None, session_dir=h.sdir)
        # _STDM_LAG_NOTE is referenced in the gateway-direct render path
        # — must surface as visible text. We assert on the substring
        # "STDM" since the exact phrasing may evolve.
        self.assertIn("STDM", md)

    def test_render_lists_both_gateway_requests(self):
        import render_dc  # noqa: WPS433
        with _GatewayDirectHarness() as h:
            md = render_dc.render(h.tree, manifest=None, session_dir=h.sdir)
        # Gateway-direct render truncates IDs to 8-char prefixes — assert
        # on the prefix substring + on the prompt-template name (verbatim
        # in the per-call detail block).
        self.assertIn(IDS.GW_REQ_DECLARED[:8], md)
        self.assertIn(IDS.GW_REQ_WINDOW[:8], md)
        self.assertIn("AiCopilot__ReactInitialPrompt", md)
        self.assertIn("AiCopilot__PromptTemplateGenerationsInvocable", md)

    def test_render_includes_session_id(self):
        import render_dc  # noqa: WPS433
        with _GatewayDirectHarness() as h:
            md = render_dc.render(h.tree, manifest=None, session_dir=h.sdir)
        self.assertIn(IDS.SID, md)


if __name__ == "__main__":
    unittest.main()
