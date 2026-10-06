#!/usr/bin/env python3
"""Guard translator-owned source against corpus-specific rules."""

import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_DIRS = (ROOT / "src", ROOT / "cpp_lib")
TOOL_SOURCE_DIRS = (ROOT / "tools",)
CORPUS_SYMBOL = re.compile(
    r"\b(?:cJSON|Kilo|Wolf4SDL|Wolfenstein|inih|editorOpen|"
    r"ScanNames|IN_GetScanName|US_SetScanNames)(?=[^A-Za-z0-9]|$)",
    re.IGNORECASE,
)
LEGACY_JSON_DOM = re.compile(r"\b(?:JsonValue|JsonMember)\b")


def corpus_name_mentions(source, hash_comments=True):
    """Return corpus-specific names in code or literals, excluding comments."""
    clean = []
    quote = None
    line_comment = False
    block_comment = False
    escaped = False
    index = 0
    while index < len(source):
        character = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if character == "\n":
                line_comment = False
                clean.append("\n")
            else:
                clean.append(" ")
            index += 1
            continue
        if block_comment:
            if character == "*" and following == "/":
                clean.extend((" ", " "))
                block_comment = False
                index += 2
                continue
            clean.append("\n" if character == "\n" else " ")
            index += 1
            continue
        if quote is not None:
            clean.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if not hash_comments:
            raw_prefix = next(
                (
                    prefix
                    for prefix in ('u8R"', 'uR"', 'UR"', 'LR"', 'R"')
                    if source.startswith(prefix, index)
                ),
                None,
            )
            if raw_prefix is not None:
                delimiter_start = index + len(raw_prefix)
                open_paren = source.find("(", delimiter_start, delimiter_start + 17)
                if open_paren >= 0:
                    delimiter = source[delimiter_start:open_paren]
                    if not any(char.isspace() or char in "()\\" for char in delimiter):
                        terminator = ")" + delimiter + '"'
                        close = source.find(terminator, open_paren + 1)
                        if close >= 0:
                            end = close + len(terminator)
                            clean.extend(source[index:end])
                            index = end
                            continue
        if character in ('"', "'"):
            quote = character
            clean.append(character)
            index += 1
            continue
        if character == "/" and following == "/":
            line_comment = True
            clean.extend((" ", " "))
            index += 2
            continue
        if character == "/" and following == "*":
            block_comment = True
            clean.extend((" ", " "))
            index += 2
            continue
        if hash_comments and character == "#":
            line_comment = True
            clean.append(" ")
        else:
            clean.append(character)
        index += 1

    source_without_comments = "".join(clean)
    return [
        (match.start(), match.group())
        for match in CORPUS_SYMBOL.finditer(source_without_comments)
    ]


class TranslatorGenericityTests(unittest.TestCase):
    def test_fp_option_model_has_one_owner_and_ordered_includes(self):
        main = (ROOT / "src" / "main.elisa").read_text(encoding="utf-8")
        types = (ROOT / "src" / "clang_fp_option_types.elisa").read_text(
            encoding="utf-8"
        )
        parser = (ROOT / "src" / "clang_fp_options.elisa").read_text(
            encoding="utf-8"
        )

        includes = (
            'include "clang_argv_options.elisa"',
            'include "clang_fp_option_types.elisa"',
            'include "clang_fp_options.elisa"',
            'include "clang_compile_command.elisa"',
        )
        positions = [main.index(include) for include in includes]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(types.startswith("extend CTranslator:"))
        self.assertIn("struct ClangFPOptionVector:", types)
        self.assertNotIn("struct ClangFPOptionVector:", parser)
        self.assertIn("def clang_fp_options_default", parser)

    def test_detects_a_hypothetical_corpus_specific_mapping(self):
        source = 'if sview_eq(name, sview("cJSON_Parse", 0, -1)):\n'
        self.assertEqual([name for _, name in corpus_name_mentions(source)], ["cJSON"])

    def test_detects_a_corpus_specific_identifier_mapping(self):
        source = "if expression.text == cJSON_Parse:\n"
        self.assertEqual([name for _, name in corpus_name_mentions(source)], ["cJSON"])

    def test_detects_wolf_specific_map_names_in_a_hypothetical_adapter(self):
        source = 'if member == "ScanNames" or member == "US_SetScanNames":\n'
        self.assertEqual(
            [name for _, name in corpus_name_mentions(source)],
            ["ScanNames", "US_SetScanNames"],
        )

    def test_ignores_generic_api_names_and_comments(self):
        source = '# cJSON-specific behavior is forbidden\nif is_builtin(name):\n'
        self.assertEqual(corpus_name_mentions(source), [])

    def test_keeps_hash_characters_inside_string_literals(self):
        source = 'message <- "prefix # cJSON"\n'
        self.assertEqual([name for _, name in corpus_name_mentions(source)], ["cJSON"])

    def test_cpp_comment_syntax_is_ignored_but_code_and_literals_are_checked(self):
        source = '''// cJSON_Parse is only mentioned in this comment.
/* ScanNames is also only a comment. */
const char *mapping = "cJSON_Parse";
if (name == editorOpen) { return mapping; }
'''
        self.assertEqual(
            [name for _, name in corpus_name_mentions(source, hash_comments=False)],
            ["cJSON", "editorOpen"],
        )

    def test_cpp_raw_strings_keep_embedded_quotes_and_comment_markers_as_literals(self):
        source = 'const char *mapping = R"tag(" // cJSON_Parse)tag";\n'
        self.assertEqual(
            [
                name
                for _, name in corpus_name_mentions(source, hash_comments=False)
            ],
            ["cJSON"],
        )

    def test_translator_owned_sources_have_no_corpus_name_literals(self):
        violations = []
        source_roots = [(directory, ("*.elisa",)) for directory in PRODUCTION_DIRS]
        source_roots.extend(
            (directory, ("*.cpp", "*.cc", "*.cxx", "*.h", "*.hpp"))
            for directory in TOOL_SOURCE_DIRS
        )
        for directory, patterns in source_roots:
            for pattern in patterns:
                for path in sorted(directory.rglob(pattern)):
                    source = path.read_text(encoding="utf-8")
                    for offset, symbol in corpus_name_mentions(
                        source, hash_comments=path.suffix == ".elisa"
                    ):
                        line = source.count("\n", 0, offset) + 1
                        violations.append(
                            "%s:%d: %s" % (path.relative_to(ROOT), line, symbol)
                        )
        self.assertEqual(
            violations,
            [],
            "corpus-specific translator source names or literals:\n"
            + "\n".join(violations),
        )

    def test_expression_emitter_does_not_special_case_argv(self):
        emitter = (ROOT / "src" / "emit_expr.elisa").read_text(encoding="utf-8")
        self.assertNotIn(
            'sview("argv"',
            emitter,
            "pointer-index emission must depend on typed expression structure, not a source identifier",
        )

    def test_integer_identity_rewrite_checks_target_abi_representation(self):
        quality = (ROOT / "src" / "emit_quality.elisa").read_text(
            encoding="utf-8"
        )
        helper = quality.split(
            "    def typed_expr_identity_result_type_matches", 1
        )[1].split("\n    def ", 1)[0]
        self.assertIn("operand.kind == TypedExprKind.Sizeof", helper)
        self.assertIn(
            "clang_target_type_abi_base(ctx.target_abi, expression.type_name)",
            helper,
        )
        self.assertIn(
            "clang_target_type_abi_base(ctx.target_abi, operand.type_name)",
            helper,
        )
        rewrite = quality.split("    def typed_expr_is_identity_binary", 1)[1].split(
            "\n    def ", 1
        )[0]
        self.assertIn(
            "typed_expr_identity_result_type_matches(ctx, index, candidate)",
            rewrite,
        )
        self.assertIn(
            '(sview_eq(expression.text, sview("<<", 0, -1)) or sview_eq(expression.text, sview(">>", 0, -1))) and not c_type_is_unsigned_integer(expression.type_name)',
            rewrite,
        )
        self.assertIn("operand-result-abi-type-mismatch", quality)
        self.assertIn("signed-left-shift-may-be-undefined", quality)
        self.assertIn("signed-right-shift-is-implementation-defined", quality)

    def test_redundant_cast_elision_keeps_numeric_and_pointer_conversion_boundaries(self):
        quality = (ROOT / "src" / "emit_quality.elisa").read_text(
            encoding="utf-8"
        )
        helper = quality.split(
            "    def typed_expr_is_redundant_cast", 1
        )[1].split("\n    def ", 1)[0]
        self.assertIn(
            "sview_eq(operand.type_name, expression.type_name)", helper
        )
        self.assertIn(
            "c_type_pointer_count(operand.type_name) > 0 or c_type_pointer_count(expression.type_name) > 0",
            helper,
        )
        self.assertIn(
            "c_type_without_qualifiers(operand.type_name), c_type_without_qualifiers(expression.type_name)",
            helper,
        )
        fixture = (ROOT / "testdata" / "fixtures" / "cast_representation.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("(int64_t)value", fixture)
        self.assertIn("(uint32_t)value", fixture)

    def test_clang_ast_uses_region_indexed_json_handles_without_legacy_dom_types(self):
        legacy_references = []
        for directory in PRODUCTION_DIRS:
            for path in sorted(directory.rglob("*.elisa")):
                source = path.read_text(encoding="utf-8")
                for match in LEGACY_JSON_DOM.finditer(source):
                    line = source.count("\n", 0, match.start()) + 1
                    legacy_references.append(
                        "%s:%d: %s" % (path.relative_to(ROOT), line, match.group())
                    )
        self.assertEqual(
            legacy_references,
            [],
            "translator sources must use the public region-indexed JSON API:\n"
            + "\n".join(legacy_references),
        )

        ast_access = (ROOT / "src" / "clang_ast.elisa").read_text(encoding="utf-8")
        self.assertRegex(
            ast_access,
            r"def ast_field\[@r\]\(node: JsonValueHandle\[r\], key: sview\) -> JsonValueHandle\[r\]:",
        )
        self.assertIn("json_handle_get(node, key)", ast_access)
        self.assertRegex(
            ast_access,
            r"def ast_child\[@r\]\(node: JsonValueHandle\[r\], index: i64\) -> JsonValueHandle\[r\]:",
        )

        parser = (ROOT / "src" / "emit_program.elisa").read_text(encoding="utf-8")
        self.assertRegex(
            parser,
            r"ast_arena: mutable Arena = zeroed\s+parsed: JsonParseResult\[ast_arena\] = json_parse_checked\(&ast_arena,",
        )
        self.assertIn(
            "root: JsonValueHandle[ast_arena] = json_handle_from_result(parsed)",
            parser,
        )
        self.assertIn(
            "context: mutable TypedContext[ast_arena] = typed_new_context(root,",
            parser,
        )


if __name__ == "__main__":
    result = unittest.main(exit=False)
    raise SystemExit(not result.result.wasSuccessful())
