"""
The parsing engine: raw dictionary text + a profile → structured parts.

This is the middle step of the macOS-dictionary pipeline:

    dict_lookup.py   gets the raw text from macOS DictionaryServices
    parser.py        slices that text into parts, following a profile  ← here
    formatter.py     renders the parts the user wants as HTML

Everything in here is plain string handling — no Anki, no Qt, no macOS
frameworks — so it's easy to test (see tests/test_parser.py).

The rules that drive each step come from a profile dict (see profiles.py
for what every field means, with worked examples). The parsing happens in
five small steps, each with its own function below:

    1. _cut_sections        chop off trailing sections like 用法说明/ORIGIN
    2. (strip the headword)  the raw text usually starts by repeating it
    3. _take_pronunciation  peel the pronunciation off the front
    4. _split_senses        split the rest into numbered meanings
    5. _extract_pos / _split_examples   pick apart each meaning

The result is a ParsedEntry, which is just organized text — deciding what
to *show* (and making it pretty) is formatter.py's job.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ------------------------------------------------------------------ #
#  The output shape                                                    #
# ------------------------------------------------------------------ #

@dataclass
class Sense:
    """One numbered meaning of a word."""
    number: str = ""              # "①" / "1" / "" for a single-sense entry
    pos: str = ""                 # part-of-speech label, e.g. "动" or "noun"
    definition: str = ""          # the meaning itself
    examples: List[str] = field(default_factory=list)


@dataclass
class ParsedEntry:
    """Everything we managed to slice out of one dictionary entry."""
    pronunciation: str = ""
    senses: List[Sense] = field(default_factory=list)
    # Extra trailing sections, keyed by the *part name* the profile gave
    # them, e.g. {"usage_notes": "…", "origin": "Old English æppel…"}
    sections: Dict[str, str] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not (self.pronunciation or self.senses or self.sections)


# ------------------------------------------------------------------ #
#  Patterns shared by the steps below                                  #
# ------------------------------------------------------------------ #

# Circled sense numbers used by CJK dictionaries: ①②③…⑳
#
# The marker must start the text or follow a space or sentence break. That
# rules out the *other* use of these symbols: a cross-reference to another
# entry's sense, written tight against the word it points at. In
#     挨挤 āijǐ 动 拥挤①。天挺挺热，别挨挤在一块儿。
# the ① means "see sense ① of 拥挤" and is part of the definition — reading
# it as a sense marker would split the entry and throw the definition away.
_CIRCLED_NUM = re.compile(
    r"(?:^|(?<=[\s。；]))([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳])"
)

# Pinyin right after the headword: latin letters with tone marks, ending
# where the actual entry begins (a sense number, a CJK character
# 一-鿿, or 〈).
#
# The punctuation in the character class all shows up in real entries:
#   -   joins the halves of a four-character idiom  guāngcǎi-duómù
#   '   separates syllables where they'd be ambiguous  nǚ'ér
#   ·   separates syllables in some multi-syllable readings
# Leaving any of them out makes the whole match fail, and the unmatched
# pinyin then leaks into the first definition.
_PINYIN = re.compile(
    r"^([a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ\s·\-'’]+?)"
    r"(?=\s*[①②③④⑤⑥⑦⑧⑨⑩一-鿿〈])"
)

# ------------------------------------------------------------------ #
#  The main entry point                                                #
# ------------------------------------------------------------------ #

def parse_entry(headword: str, raw_text: str, profile: dict) -> ParsedEntry:
    """
    Slice one raw dictionary entry into structured parts, following the
    rules in `profile`. Never raises on weird input — worst case, the whole
    text ends up as one sense's definition, so the user still sees it.
    """
    entry = ParsedEntry()
    if not raw_text or not raw_text.strip():
        return entry

    working = raw_text.strip()

    if profile.get("whole_entry"):
        entry.senses.append(Sense(definition=raw_text))
        return entry

    # Step 1: chop off trailing sections (用法说明 / ORIGIN / …).
    working, entry.sections = _cut_sections(working, profile.get("sections") or {})

    # Step 2: the raw text almost always starts by repeating the headword —
    # drop it so it doesn't end up inside the first definition.
    if working.startswith(headword):
        working = working[len(headword):].strip()

    # Step 3: peel the pronunciation off the front.
    pron_style = profile.get("pronunciation_style", "none")
    entry.pronunciation, working = _take_pronunciation(working, pron_style)

    # Step 4: split what's left into senses.
    sense_style = profile.get("sense_style", "single")
    leading, numbered = _split_senses(working, sense_style)

    # In Apple's English layout the part of speech comes *before* the sense
    # numbers ("noun 1 … 2 …"), so it lands in `leading`. If that leading
    # text is (or ends with) a known POS label, apply it to every sense.
    pos_labels = profile.get("pos_labels") or []
    shared_pos = _match_pos(leading, pos_labels) if leading else ""

    # Step 5: pick each sense apart into POS + definition + examples.
    example_style = profile.get("example_style", "none")
    for number, text in numbered:
        sense = Sense(number=number)
        sense.pos, text = _extract_pos(text, pos_labels)
        if not sense.pos:
            sense.pos = shared_pos
        sense.definition, sense.examples = _split_examples(
            text, example_style, headword
        )
        if sense.definition or sense.examples:
            entry.senses.append(sense)

    return entry


# ------------------------------------------------------------------ #
#  Step 1: trailing sections                                           #
# ------------------------------------------------------------------ #

def _cut_sections(text: str, section_rules: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    """
    Find each section marker (e.g. "用法说明", "ORIGIN") in the text and cut
    the text from that marker onward into its own bucket.

    Each section runs from just after its marker to the next marker (or the
    end of the text). Returns (main text without the sections, sections
    keyed by part name).
    """
    # Where does each marker first appear?  [(position, marker, part_name)]
    hits = []
    for marker, part_name in section_rules.items():
        pos = text.find(marker)
        if pos >= 0:
            hits.append((pos, marker, part_name))
    if not hits:
        return text, {}

    hits.sort()  # left to right, so we know where each section ends
    sections: Dict[str, str] = {}
    for i, (pos, marker, part_name) in enumerate(hits):
        start = pos + len(marker)
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        content = text[start:end].strip()
        if content:
            sections[part_name] = content

    main_text = text[:hits[0][0]].strip()
    return main_text, sections


# ------------------------------------------------------------------ #
#  Step 3: pronunciation                                               #
# ------------------------------------------------------------------ #

def _take_pronunciation(text: str, style: str) -> Tuple[str, str]:
    """Return (pronunciation, rest of the text). Empty string if not found."""
    if style == "pinyin_after_headword":
        m = _PINYIN.match(text)
        if m:
            return m.group(1).strip(), text[m.end():].strip()
    return "", text


# ------------------------------------------------------------------ #
#  Step 4: senses                                                      #
# ------------------------------------------------------------------ #

def _split_senses(text: str, style: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Split the entry body into senses.

    Returns (leading text before the first sense marker, list of
    (number, sense text) pairs). If the expected markers never appear, the
    whole text becomes one un-numbered sense — a wrong sense_style should
    degrade to "show everything", never to "show nothing".
    """
    text = text.strip()
    if not text:
        return "", []

    if style == "circled":
        pattern = _CIRCLED_NUM
    else:  # "single" — the whole entry is one meaning
        return "", [("", text)]

    matches = list(pattern.finditer(text))
    if not matches:
        # Marker never found → single-sense fallback.
        return "", [("", text)]

    leading = text[:matches[0].start()].strip()
    senses = []
    for i, m in enumerate(matches):
        number = m.group(1) if m.groups() else m.group(0)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sense_text = text[start:end].strip()
        if sense_text:
            senses.append((number, sense_text))
    return leading, senses


# ------------------------------------------------------------------ #
#  Step 5a: part of speech                                             #
# ------------------------------------------------------------------ #

def _extract_pos(text: str, pos_labels: List[str]) -> Tuple[str, str]:
    """
    If the sense text *starts* with a known POS label followed by a space,
    split it off. "动 从阅读获得知识。" → ("动", "从阅读获得知识。")
    """
    # Longest labels first, so "拟声" wins over a hypothetical "拟".
    for label in sorted(pos_labels, key=len, reverse=True):
        if text.startswith(label):
            rest = text[len(label):]
            if rest[:1].isspace():
                return label, rest.strip()
    return "", text


def _match_pos(text: str, pos_labels: List[str]) -> str:
    """
    Does this leading text (before the first sense number) name a POS?
    Handles "noun" and also "apple's leftovers … noun" (label at the end),
    plus Apple's "▸noun" arrow prefix.
    """
    cleaned = text.strip().lstrip("▸").strip()
    for label in sorted(pos_labels, key=len, reverse=True):
        if cleaned == label or cleaned.endswith(" " + label):
            return label
    return ""


# ------------------------------------------------------------------ #
#  Step 5b: definition vs. examples                                    #
# ------------------------------------------------------------------ #

def _split_examples(text: str, style: str, headword: str) -> Tuple[str, List[str]]:
    """Split one sense's text into (definition, list of examples)."""
    text = text.strip()
    if style == "pipe_separated":
        return _split_examples_pipe(text, headword)
    return text, []


def _split_examples_pipe(text: str, headword: str) -> Tuple[str, List[str]]:
    """
    现代汉语规范词典 style: the definition ends at the first 。 and examples
    follow, separated by | or ｜:

        从阅读获得知识。她在学习。｜认真学习很重要。
        └─ definition ─┘└──────── examples ────────┘

    One catch: text after the 。 isn't always examples. Compare:

        迷离…。醉眼迷离          ← example (contains the headword)
        儿童…。我国现在一般指…    ← more definition (an elaboration)

    Heuristic: it's an example if it has | separators, or contains the
    headword or the ～ placeholder dictionaries use for it. Otherwise it's
    part of the definition and gets glued back on.
    """
    first, _, after = text.partition("。")
    definition = first.strip()
    after = after.strip()

    examples: List[str] = []
    if after and ("|" in after or "｜" in after):
        for chunk in re.split(r"\s*[|｜]\s*", after):
            chunk = chunk.strip().rstrip("。")
            if chunk:
                examples.append(chunk)
    elif after and (headword in after or "～" in after):
        examples.append(after.rstrip("。"))
    elif after:
        # Definitional elaboration — it belongs with the definition.
        definition = definition + "。" + after.rstrip("。")

    # The definition itself may also carry |-separated examples (entries
    # that skip the 。 before their first example).
    if "|" in definition or "｜" in definition:
        pieces = re.split(r"\s*[|｜]\s*", definition)
        definition = pieces[0].strip()
        examples = [p.strip() for p in pieces[1:] if p.strip()] + examples

    return definition, examples
