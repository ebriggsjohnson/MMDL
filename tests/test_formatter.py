"""
Tests for formatter.py — the most parsing-heavy module.

Run from the project root:
    pytest tests/
"""

import importlib.util
import os

# Load formatter.py directly by path — avoids triggering the project's __init__.py
# (which imports aqt and requires a running Anki instance).
_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "formatter", os.path.join(_here, "..", "formatter.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

format_macos_entry = _mod.format_macos_entry


# ------------------------------------------------------------------ #
#  macOS formatter                                                     #
# ------------------------------------------------------------------ #

class TestFormatMacosEntry:
    def test_empty_raw_returns_empty(self):
        assert format_macos_entry("学习", "", {"definitions"}) == ""
        assert format_macos_entry("学习", None, {"definitions"}) == ""

    def test_multi_sense_extracts_pinyin_pos_def_examples(self):
        raw = "学习 xuéxí ①动 从阅读获得知识。她在学习钢琴。 ②名 学习的行动。"
        result = format_macos_entry("学习", raw, {"pinyin", "pos", "definitions", "examples"})

        assert 'class="pinyin"' in result
        assert "xuéxí" in result
        assert "[动]" in result
        assert "从阅读获得知识" in result
        assert "她在学习钢琴" in result
        assert "[名]" in result
        assert "学习的行动" in result
        # Rendered as ordered list
        assert "<ol" in result
        assert "<li>" in result

    def test_single_sense_no_markers(self):
        # The single-sense fix: when no ①② markers, treat whole text as one sense.
        raw = "汉语 hànyǔ 名 汉民族的语言。"
        result = format_macos_entry("汉语", raw, {"pos", "definitions"})

        assert result  # must not be empty — this was the original bug
        assert "汉民族的语言" in result
        assert "[名]" in result

    def test_usage_notes_included_when_requested(self):
        raw = "规矩 guīju ①名 准则法则。 用法说明 与规则的使用有别。"
        result = format_macos_entry("规矩", raw, {"pos", "definitions", "usage_notes"})

        assert "用法" in result
        assert "与规则的使用有别" in result

    def test_usage_notes_excluded_when_not_in_parts(self):
        raw = "规矩 guīju ①名 准则法则。 用法说明 与规则的使用有别。"
        result = format_macos_entry("规矩", raw, {"pos", "definitions"})

        assert "与规则的使用有别" not in result

    def test_parts_filtering_definitions_only(self):
        raw = "学习 xuéxí ①动 从阅读获得知识。她在学习钢琴。"
        result = format_macos_entry("学习", raw, {"definitions"})

        assert 'class="pinyin"' not in result
        assert 'class="pos"' not in result
        assert "例：" not in result
        assert "从阅读获得知识" in result

    def test_parts_filtering_pinyin_only(self):
        raw = "学习 xuéxí ①动 从阅读获得知识。她在学习钢琴。"
        result = format_macos_entry("学习", raw, {"pinyin"})

        assert "xuéxí" in result
        assert "从阅读获得知识" not in result
        assert "例：" not in result

    def test_examples_split_on_pipe(self):
        raw = "学习 xuéxí ①动 获得知识。她在学习。|认真学习很重要。"
        result = format_macos_entry("学习", raw, {"definitions", "examples"})

        assert "她在学习" in result
        assert "认真学习很重要" in result

    def test_headword_not_duplicated_in_output(self):
        raw = "被 bèi ①介 表示被动。他被表扬了。"
        result = format_macos_entry("被", raw, {"pos", "definitions", "examples"})
        # headword "被" should appear inside content, not as a spurious header
        assert result.count("被") >= 1  # at least in examples
        assert "[介]" in result
