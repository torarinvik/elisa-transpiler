#!/usr/bin/env python3
"""Compiler-free tests for identifier normalization in metamorphic checks."""

import unittest

from test_metamorphic import normalize_identifier


class IdentifierNormalizationTests(unittest.TestCase):
    def test_renames_only_complete_code_identifiers(self):
        source = "cursor + cursor2 + _cursor + 2cursor + cursor_"
        self.assertEqual(
            normalize_identifier(source, "cursor", "argv"),
            "argv + cursor2 + _cursor + 2cursor + cursor_",
        )

    def test_preserves_strings_character_literals_and_comments(self):
        source = 'cursor("cursor \\\" cursor", \'cursor\') # cursor\ncursor'
        self.assertEqual(
            normalize_identifier(source, "cursor", "argv"),
            'argv("cursor \\\" cursor", \'cursor\') # cursor\nargv',
        )

    def test_unicode_identifier_adjacency_is_not_split(self):
        source = "αcursor cursorβ cursor"
        self.assertEqual(
            normalize_identifier(source, "cursor", "argv"),
            "αcursor cursorβ argv",
        )

    def test_rejects_an_empty_search_identifier(self):
        with self.assertRaises(ValueError):
            normalize_identifier("anything", "", "replacement")


if __name__ == "__main__":
    unittest.main()
