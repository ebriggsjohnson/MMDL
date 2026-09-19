"""Curated dictionary packs: identity and defaults, separate from parser rules.

A pack targets a dictionary, not an entire language. Add its recipe to
profiles.py and regression entries to tests/fixtures before adding a pack
here. Unknown dictionaries always receive the whole-entry preset.
"""

PACKS = {
    "xiandai_hanyu": {
        "name": "现代汉语规范词典",
        "dictionary_names": ["现代汉语规范词典", "現代漢語規範詞典"],
        "language": "Chinese",
        "script": "Simplified",
        "profile": "xiandai_hanyu_sample",
        "parts": ["pos", "definitions", "examples"],
        "samples": "tests/fixtures/xiandai_hanyu.json",
    },
    "whole_entry": {
        "name": "Whole entry",
        "dictionary_names": [],
        "language": "Not identified",
        "script": "",
        "profile": "whole_entry",
        "parts": ["definitions"],
        "samples": "tests/fixtures/whole_entry.json",
    },
}


def pack_for_dictionary(name: str) -> dict:
    for pack in PACKS.values():
        if name in pack["dictionary_names"]:
            return pack
    return PACKS["whole_entry"]
