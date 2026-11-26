"""Regression tests for scripts/semver.py.

The bug this guards against: the two old `parse_ver` copies truncated to three
components and dropped any pre-release tag, so `11.0.0` and `11.0.0-rc1` parsed
to the same `(11,0,0)` tuple and compared EQUAL. That made a real backward step
("you're on the final, you asked for the rc") read as "already current", and let
a coherence check pass a version that was never released. These tests pin the
SemVer §11 precedence that the shared util must uphold.
"""
import unittest

import _bootstrap  # noqa: F401  (sys.path side effect)
import semver


class TestPrereleasePrecedence(unittest.TestCase):
    def test_final_outranks_its_own_prerelease(self):
        # The exact collision the old code produced. These must NOT be equal.
        self.assertNotEqual(semver.parse("11.0.0"), semver.parse("11.0.0-rc1"))
        self.assertEqual(semver.compare("11.0.0", "11.0.0-rc1"), 1)
        self.assertGreater(semver.parse("11.0.0"), semver.parse("11.0.0-rc1"))

    def test_prerelease_is_flagged(self):
        self.assertTrue(semver.parse("11.0.0-rc1").is_prerelease())
        self.assertTrue(semver.parse("3.1.1-SNAPSHOT").is_prerelease())
        self.assertFalse(semver.parse("11.0.0").is_prerelease())

    def test_prerelease_ordering_numeric_vs_alpha(self):
        # SemVer §11.4: numeric identifiers rank below alphanumeric ones.
        self.assertLess(semver.parse("1.0.0-1"), semver.parse("1.0.0-alpha"))
        # Fewer fields rank below more, when the shared prefix is equal.
        self.assertLess(semver.parse("1.0.0-rc"), semver.parse("1.0.0-rc.1"))
        # Numeric pre-release identifiers compare numerically, not lexically.
        self.assertLess(semver.parse("1.0.0-rc.2"), semver.parse("1.0.0-rc.10"))


class TestReleasePrecedence(unittest.TestCase):
    def test_length_difference_is_not_a_precedence_difference(self):
        # Missing trailing fields are zero: 11.0 == 11.0.0.
        self.assertEqual(semver.compare("11.0", "11.0.0"), 0)

    def test_never_truncates_to_three_components(self):
        # The old code truncated; a 4th component must still be compared.
        self.assertGreater(semver.parse("1.2.3.4"), semver.parse("1.2.3.3"))

    def test_ordinary_ordering(self):
        self.assertLess(semver.parse("8.1.0"), semver.parse("9.0.5"))
        self.assertLess(semver.parse("9.0.5"), semver.parse("10.0.0"))
        self.assertGreater(semver.parse("11.0.1"), semver.parse("11.0.0"))

    def test_build_metadata_ignored(self):
        self.assertEqual(semver.compare("11.0.0+build.5", "11.0.0+build.9"), 0)
        self.assertEqual(semver.compare("11.0.0+build", "11.0.0"), 0)


class TestSortingAndKeys(unittest.TestCase):
    def test_key_sorts_by_precedence(self):
        raw = ["11.0.0", "11.0.0-rc1", "10.0.0", "8.1.0", "11.0.1"]
        ordered = sorted(raw, key=semver.key)
        self.assertEqual(ordered, ["8.1.0", "10.0.0", "11.0.0-rc1", "11.0.0", "11.0.1"])

    def test_max_prefers_final_over_prerelease(self):
        pool = ["11.0.0-rc1", "11.0.0", "11.0.0-beta"]
        self.assertEqual(max(pool, key=semver.key), "11.0.0")


class TestReleaseTupleIsDisplayOnly(unittest.TestCase):
    def test_release_tuple_is_three_components(self):
        self.assertEqual(semver.release_tuple("11.0.1"), (11, 0, 1))
        self.assertEqual(semver.release_tuple("11.0"), (11, 0, 0))
        self.assertEqual(semver.release_tuple("v10"), (10, 0, 0))

    def test_release_tuple_drops_prerelease(self):
        # Deliberately lossy — must NOT be used for precedence (that's the whole
        # point of keeping it separate from compare()/Version).
        self.assertEqual(semver.release_tuple("11.0.0-rc1"), (11, 0, 0))
        self.assertEqual(semver.release_tuple("11.0.0"),
                         semver.release_tuple("11.0.0-rc1"))


class TestTolerance(unittest.TestCase):
    def test_junk_degrades_rather_than_raises(self):
        # A malformed catalog entry must not crash a migration mid-flight.
        self.assertEqual(semver.release_tuple("garbage"), (0, 0, 0))
        # ...but still compares consistently.
        self.assertEqual(semver.compare("garbage", "0.0.0"), 0)


if __name__ == "__main__":
    unittest.main()
