"""
Turn parsed dictionary entries into clean HTML for Anki note fields.

This is the last step of the macOS-dictionary pipeline (see entry_parser.py
for the overview). By the time text reaches this file it is already
structured — a ParsedEntry with pronunciation, senses, and sections. This
module only decides which parts the user asked for and wraps them in HTML.

Why inline styles instead of CSS classes? Anki card styling lives in each
user's note templates, which we don't control. Inline styles guarantee the
entries look consistent no matter what template they land in. The colors
are deliberately muted (grays + one accent blue for POS) so they blend in.

"""

from html import escape
from typing import List, Set

# This file is imported two different ways:
#   - inside Anki, as part of the add-on package → relative imports work
#   - standalone, by cli.py and the tests (which load it by file path)
#     → there is no package, so fall back to plain imports after making
#     sure this file's directory is on the import path
try:
    from .entry_parser import ParsedEntry, parse_entry
    from .profiles import CHINESE_SAMPLE
except ImportError:
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from entry_parser import ParsedEntry, parse_entry
    from profiles import CHINESE_SAMPLE


# ------------------------------------------------------------------ #
#  macOS dictionaries (profile-driven)                                 #
# ------------------------------------------------------------------ #

def render_entry(entry: ParsedEntry, parts: Set[str], profile: dict) -> str:
    """
    Render a ParsedEntry as HTML, including only the parts the user picked.

    Args:
        entry:   what entry_parser.parse_entry produced
        parts:   set of part names to include, e.g. {"pos", "definitions"}
                 (the valid names for a profile come from
                 profiles.profile_parts)
        profile: the profile that parsed this entry — needed here to know
                 what the pronunciation part is called and how to label
                 the extra sections

    Returns an HTML string, or "" if nothing matched.
    """
    if not parts:
        return ""
    html: List[str] = []

    # Pronunciation. Its part *name* comes from the profile ("pinyin" for
    # the Chinese preset), and the
    # name doubles as the CSS class so note templates can target it.
    pron_part = profile.get("pronunciation_part", "pronunciation")
    if pron_part in parts and entry.pronunciation:
        html.append(
            f'<span class="{escape(pron_part)}" style="color:#888; font-style:italic;">'
            f'{escape(entry.pronunciation)}</span>'
        )

    # The senses. A single sense is rendered bare; multiple senses become a
    # numbered <ol> list.
    visible_senses = [sense for sense in entry.senses
                      if ("pos" in parts and sense.pos)
                      or ("definitions" in parts and sense.definition)
                      or ("examples" in parts and sense.examples)]
    if visible_senses:
        use_list = len(visible_senses) > 1
        if use_list:
            html.append('<ol style="margin:0.3em 0; padding-left:1.5em;">')
        for sense in visible_senses:
            if use_list:
                html.append("<li>")

            if "pos" in parts and sense.pos:
                html.append(
                    f'<span class="pos" style="color:#2a7ae2; font-size:0.85em; '
                    f'margin-right:0.3em;">[{escape(sense.pos)}]</span>'
                )

            if "definitions" in parts and sense.definition:
                html.append(f'<span class="def">{escape(sense.definition)}</span>')

            if "examples" in parts and sense.examples:
                ex_html = " &#x7C; ".join(
                    f'<span style="color:#666;">{escape(ex)}</span>'
                    for ex in sense.examples
                )
                html.append(
                    f'<div class="examples" style="margin-top:0.15em; '
                    f'font-size:0.9em; color:#555;">{ex_html}</div>'
                )

            if use_list:
                html.append("</li>")
        if use_list:
            html.append("</ol>")

    # Extra sections (usage notes, etymology, …). We walk the profile's
    # section rules — not entry.sections directly — to keep the profile's
    # ordering and to reuse the marker text as the visible label.
    for marker, part_name in (profile.get("sections") or {}).items():
        text = entry.sections.get(part_name, "")
        if part_name in parts and text:
            html.append(
                f'<div class="{escape(part_name)}" style="margin-top:0.4em; '
                f'font-size:0.85em; color:#888; border-top:1px solid #eee; '
                f'padding-top:0.3em;">{escape(marker)}：{escape(text)}</div>'
            )

    return "\n".join(html)


def format_macos_entry(headword: str, raw_text: str, parts: Set[str],
                       profile: dict = None) -> str:
    """
    Parse + render a raw macOS dictionary entry in one call.

    This is the single entry point used by lookup.py, cli.py and the tests.
    When no profile is given it uses the built-in Chinese sample profile,
    which is exactly what this add-on did before profiles existed.

    Args:
        headword: the word being looked up
        raw_text: raw text from DCSCopyTextDefinition
        parts:    set of part names to include
        profile:  parsing rules (see profiles.py); None = Chinese sample

    Returns:
        HTML string, or "" if raw_text is empty/None
    """
    if not raw_text:
        return ""
    if profile is None:
        profile = CHINESE_SAMPLE
    entry = parse_entry(headword, raw_text, profile)
    return render_entry(entry, parts, profile)
