"""
Tests for entry_parser.py + profiles.py — the profile-driven parsing engine.

Run from the project root:
    pytest tests/
"""

import importlib.util
import os

# Load the modules directly by path — avoids triggering the project's
# __init__.py (which imports aqt and requires a running Anki instance).
_here = os.path.dirname(os.path.abspath(__file__))


def _load(module_name):
    spec = importlib.util.spec_from_file_location(
        module_name, os.path.join(_here, "..", module_name + ".py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


entry_parser = _load("entry_parser")
profiles = _load("profiles")
formatter = _load("formatter")

parse_entry = entry_parser.parse_entry
CHINESE = profiles.CHINESE_SAMPLE


# ------------------------------------------------------------------ #
#  Chinese sample profile (the built-in worked example)                #
# ------------------------------------------------------------------ #

class TestChineseProfile:
    def test_multi_sense_entry(self):
        raw = "学习 xuéxí ①动 从阅读获得知识。她在学习钢琴。 ②名 学习的行动。"
        entry = parse_entry("学习", raw, CHINESE)

        assert entry.pronunciation == "xuéxí"
        assert len(entry.senses) == 2
        assert entry.senses[0].number == "①"
        assert entry.senses[0].pos == "动"
        assert entry.senses[0].definition == "从阅读获得知识"
        assert entry.senses[0].examples == ["她在学习钢琴"]
        assert entry.senses[1].pos == "名"
        assert entry.senses[1].definition == "学习的行动"

    def test_single_sense_no_markers(self):
        # When there are no ①② markers, the whole text is one sense.
        entry = parse_entry("汉语", "汉语 hànyǔ 名 汉民族的语言。", CHINESE)

        assert len(entry.senses) == 1
        assert entry.senses[0].pos == "名"
        assert entry.senses[0].definition == "汉民族的语言"

    def test_usage_notes_section(self):
        raw = "规矩 guīju ①名 准则法则。 用法说明 与规则的使用有别。"
        entry = parse_entry("规矩", raw, CHINESE)

        assert entry.sections == {"usage_notes": "与规则的使用有别。"}
        # The section must not leak into the definition.
        assert "与规则" not in entry.senses[0].definition

    def test_pipe_separated_examples(self):
        raw = "学习 xuéxí ①动 获得知识。她在学习。|认真学习很重要。"
        entry = parse_entry("学习", raw, CHINESE)

        assert entry.senses[0].examples == ["她在学习", "认真学习很重要"]

    def test_elaboration_stays_in_definition(self):
        # Text after 。 without the headword/～/| is more definition,
        # not an example.
        raw = "儿童 értóng 名 幼小的未成年人。我国现在一般指不满14岁的。"
        entry = parse_entry("儿童", raw, CHINESE)

        assert entry.senses[0].examples == []
        assert "我国现在一般指不满14岁的" in entry.senses[0].definition

    def test_hyphenated_and_apostrophe_pinyin(self):
        # Real 现代汉语规范词典 punctuation inside readings. If the pinyin
        # pattern rejects any of these the match fails outright and the
        # reading leaks into the definition.
        idiom = parse_entry(
            "光彩夺目",
            "光彩夺目 guāngcǎi-duómù 形容光泽色彩鲜明耀眼。",
            CHINESE,
        )
        assert idiom.pronunciation == "guāngcǎi-duómù"
        assert "guāng" not in idiom.senses[0].definition

        daughter = parse_entry(
            "女儿", "女儿 nǚ'ér 名 自己生养或领养的女孩子。", CHINESE
        )
        assert daughter.pronunciation == "nǚ'ér"
        assert daughter.senses[0].pos == "名"

    def test_cross_reference_marker_is_not_a_sense_marker(self):
        # 拥挤① means "see sense ① of 拥挤" — it's part of the definition,
        # not a sense marker for this entry. Reading it as one used to
        # discard "动 拥挤" and leave only the example sentence.
        raw = "挨挤 āijǐ 动 拥挤①。天挺挺热，别挨挤在一块儿。"
        entry = parse_entry("挨挤", raw, CHINESE)

        assert len(entry.senses) == 1
        assert entry.senses[0].pos == "动"
        assert entry.senses[0].definition == "拥挤①"
        assert entry.senses[0].examples == ["天挺挺热，别挨挤在一块儿"]

    def test_sense_marker_after_full_stop_without_space(self):
        # Some entries pack senses tight: "…定义一。②定义二"
        raw = "词 cí ①名 定义一。②名 定义二。"
        entry = parse_entry("词", raw, CHINESE)

        assert [s.number for s in entry.senses] == ["①", "②"]

    def test_empty_input(self):
        assert parse_entry("学习", "", CHINESE).is_empty()
        assert parse_entry("学习", None, CHINESE).is_empty()


# ------------------------------------------------------------------ #
#  Profile helpers                                                     #
# ------------------------------------------------------------------ #

class TestProfileHelpers:
    def test_chinese_profile_parts(self):
        assert profiles.profile_parts(CHINESE) == [
            "pinyin", "pos", "definitions", "examples", "usage_notes"
        ]

    def test_minimal_profile_still_has_definitions(self):
        bare = {"pronunciation_style": "none", "example_style": "none"}
        assert profiles.profile_parts(bare) == ["definitions"]

    def test_unknown_profile_id_falls_back_to_whole_entry(self):
        assert profiles.get_profile("no_such_id") is profiles.WHOLE_ENTRY

    def test_default_profile_guess(self):
        f = profiles.default_profile_id_for_dict
        assert f(None) == "whole_entry"
        assert f("现代汉语规范词典") == "xiandai_hanyu_sample"
        assert f("New Oxford American Dictionary") == "whole_entry"

    def test_part_label_prettifies_custom_parts(self):
        assert profiles.part_label("usage_notes") == "Usage notes (用法说明)"
        assert profiles.part_label("my_custom_part") == "My custom part"
