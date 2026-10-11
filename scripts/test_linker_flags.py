from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from linker_flags import elisa_test_link_flags


class ElisaTestLinkFlagTests(unittest.TestCase):
    def test_explicit_flags_are_split_without_shell_execution(self):
        with patch.dict(os.environ, {"ELISA_TEST_LINK_FLAGS": "-no-pie -Wl,--as-needed"}):
            self.assertEqual(elisa_test_link_flags(), ["-no-pie", "-Wl,--as-needed"])

    def test_empty_explicit_flags_are_preserved(self):
        with patch.dict(os.environ, {"ELISA_TEST_LINK_FLAGS": ""}):
            self.assertEqual(elisa_test_link_flags(), [])

    def test_platform_defaults_match_object_abi(self):
        with patch.dict(os.environ, {}, clear=True), patch("linker_flags.sys.platform", "darwin"):
            self.assertEqual(elisa_test_link_flags(), ["-Wl,-dead_strip"])
        with patch.dict(os.environ, {}, clear=True), patch("linker_flags.sys.platform", "linux"):
            self.assertEqual(elisa_test_link_flags(), ["-no-pie"])
        with patch.dict(os.environ, {}, clear=True), patch("linker_flags.sys.platform", "win32"):
            self.assertEqual(elisa_test_link_flags(), [])


if __name__ == "__main__":
    unittest.main()
