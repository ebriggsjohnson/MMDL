"""Developer-maintained recipes. Dictionary identity and defaults live in packs.py.

Recipe keys describe query conversion, pronunciation, sense markers, parts
of speech, example boundaries, and optional trailing sections. Add regression
samples before shipping a new recipe. Users only select output parts.
"""

from typing import Dict, List, Optional


# ------------------------------------------------------------------ #
#  Built-in profiles                                                   #
# ------------------------------------------------------------------ #

# The worked example: how MMDL reads 现代汉语规范词典 (the macOS built-in
# simplified-Chinese dictionary). Given this raw text:
#
#     学习 xuéxí ①动 从阅读获得知识。她在学习钢琴。 ②名 学习的行动。 用法说明 …
#
# these rules produce:
#     pinyin:   "xuéxí"                (letters after the headword)
#     sense 1:  pos=动  def=从阅读获得知识  examples=[她在学习钢琴]
#     sense 2:  pos=名  def=学习的行动
#     usage_notes: "…"                 (everything after the 用法说明 marker)
CHINESE_SAMPLE = {
    "name": "现代汉语规范词典",
    "curated": True,
    "builtin": True,
    "input_conversion": "simplified",
    "pronunciation_style": "pinyin_after_headword",
    "pronunciation_part": "pinyin",
    "sense_style": "circled",
    "pos_labels": ["名", "动", "形", "副", "介", "连", "助", "叹",
                   "拟声", "数", "量", "代"],
    "example_style": "pipe_separated",
    "sections": {"用法说明": "usage_notes"},
}

# Safe fallback: keep every character instead of guessing the structure.
WHOLE_ENTRY = {
    "name": "Whole entry",
    "builtin": True,
    "whole_entry": True,
    "input_conversion": "none",
    "pronunciation_style": "none",
    "sense_style": "single",
    "example_style": "none",
    "pos_labels": [],
    "sections": {},
}

# Profile ids are the keys used in config.json and in each connection's
# "profile" entry. Keep them stable — renaming one would break saved configs.
BUILTIN_PROFILES: Dict[str, dict] = {
    "xiandai_hanyu_sample": CHINESE_SAMPLE,
    "whole_entry": WHOLE_ENTRY,
}


# ------------------------------------------------------------------ #
#  Looking profiles up                                                 #
# ------------------------------------------------------------------ #

def get_profile(profile_id: Optional[str]) -> dict:
    """Return a shipped recipe, or whole-entry output for an unknown ID."""
    return BUILTIN_PROFILES.get(profile_id, WHOLE_ENTRY)


def default_profile_id_for_dict(dict_name: Optional[str]) -> str:
    """Only exact dictionary matches get a curated parsing recipe."""
    try:
        from .packs import pack_for_dictionary
    except ImportError:  # standalone CLI and parser tests
        from packs import pack_for_dictionary
    return pack_for_dictionary(dict_name or "")["profile"]


# ------------------------------------------------------------------ #
#  What parts does a profile produce?                                  #
# ------------------------------------------------------------------ #

def profile_parts(profile: dict) -> List[str]:
    """
    List the part names this profile can extract, in display order.
    These become the checkboxes in the connection dialog.
    """
    parts: List[str] = []
    if profile.get("pronunciation_style", "none") != "none":
        parts.append(profile.get("pronunciation_part", "pronunciation"))
    if profile.get("pos_labels"):
        parts.append("pos")
    parts.append("definitions")
    if profile.get("example_style", "none") != "none":
        parts.append("examples")
    for part_name in (profile.get("sections") or {}).values():
        if part_name not in parts:
            parts.append(part_name)
    return parts


def part_label(part: str) -> str:
    """
    Human-friendly checkbox label for a part name.
    Known parts get a hand-written label; custom ones are prettified
    ("usage_notes" → "Usage notes").
    """
    known = {
        "pinyin": "Pinyin",
        "bopomofo": "Bopomofo (ㄅㄆㄇ)",
        "pronunciation": "Pronunciation",
        "pos": "Part of speech",
        "definitions": "Definitions",
        "examples": "Examples",
        "usage_notes": "Usage notes (用法说明)",
    }
    return known.get(part, part.replace("_", " ").capitalize())


def available_profiles(dictionary_name):
    """Offer only the matching curated preset and whole entry."""
    profile_id = default_profile_id_for_dict(dictionary_name)
    choices = {}
    if profile_id != "whole_entry":
        choices[profile_id] = get_profile(profile_id)
    choices["whole_entry"] = WHOLE_ENTRY
    return choices
