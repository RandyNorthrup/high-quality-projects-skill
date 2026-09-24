"""Require every shipped configuration template to load in its own file format.

Loading is necessary, not sufficient: each tool's red drills prove the rules
fire. This suite catches the cheaper failure, a template that no tool can read.
"""

import configparser
import json
import tomllib
import unittest
from pathlib import Path

# Parses only checked-in templates, never untrusted XML.
from xml.etree import ElementTree as ET  # nosec B405

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

XML_TEMPLATES = ("csharp/Directory.Build.props",)
TOML_TEMPLATES = ("python/ruff.toml", "rust/clippy-strict.toml", "rust/deny.toml")
INI_TEMPLATES = ("python/mypy.ini", "csharp/.editorconfig")
JSON_TEMPLATES = ("web/.stylelintrc.json",)
# JSONC (tsconfig, knip) and YAML (pre-commit, clang-tidy) need parsers outside
# the standard library; their own tools and the repository hooks load them.
OTHER_FORMATS = (
    "typescript/tsconfig.strict.json",
    "web/knip.jsonc",
    ".pre-commit-config.yaml",
    "cpp/.clang-tidy",
    "powershell/PSScriptAnalyzerSettings.psd1",
    "typescript/eslint.config.mjs",
    "cpp/sanitizers.md",
    "workflow/PLAN.md",
    "README.md",
)


class TemplateFormatTests(unittest.TestCase):
    """Parse configuration templates with the same grammar their tools require."""

    def test_every_template_is_classified(self) -> None:
        """A new template cannot silently escape format checking."""
        shipped = {
            path.relative_to(TEMPLATES).as_posix()
            for path in TEMPLATES.rglob("*")
            if path.is_file()
        }
        classified = {
            *XML_TEMPLATES,
            *TOML_TEMPLATES,
            *INI_TEMPLATES,
            *JSON_TEMPLATES,
            *OTHER_FORMATS,
        }
        self.assertEqual(shipped, classified)

    def test_xml_templates_parse(self) -> None:
        """MSBuild rejects malformed XML, including '--' inside comments."""
        for relative in XML_TEMPLATES:
            with self.subTest(relative):
                # Checked-in template, not untrusted input.
                ET.parse(TEMPLATES / relative)  # noqa: S314  # nosec B314

    def test_toml_templates_parse(self) -> None:
        """TOML templates load with the standard TOML parser."""
        for relative in TOML_TEMPLATES:
            with self.subTest(relative), (TEMPLATES / relative).open("rb") as stream:
                self.assertIsInstance(tomllib.load(stream), dict)

    def test_ini_templates_parse(self) -> None:
        """INI-style templates have sections and no duplicate keys."""
        for relative in INI_TEMPLATES:
            with self.subTest(relative):
                parser = configparser.ConfigParser(interpolation=None)
                read = parser.read(TEMPLATES / relative, encoding="utf-8")
                self.assertEqual(len(read), 1)
                self.assertTrue(parser.sections())

    def test_json_templates_parse(self) -> None:
        """Strict JSON templates contain no comments or trailing commas."""
        for relative in JSON_TEMPLATES:
            with self.subTest(relative):
                self.assertIsInstance(
                    json.loads((TEMPLATES / relative).read_text(encoding="utf-8")), dict
                )


if __name__ == "__main__":
    unittest.main()
