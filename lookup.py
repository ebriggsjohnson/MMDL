"""
Shared lookup helpers — used by editor.py and gui.py.

Each function takes a word + an initialized backend client + the set of
parts to render, and returns an HTML string (empty if nothing was found).

Script conversion and dictionary selection live here.

This module stays free of Anki imports on purpose: callers that live inside
Anki (editor.py, gui.py) pass the add-on config in, rather than this module
reaching out to Anki itself. That keeps it importable anywhere.

Note: cli.py uses its own sys.path setup and bare module imports, so it
does not use these helpers. Keep the two in sync if the logic changes.
"""

from typing import Optional, Set

from .profiles import default_profile_id_for_dict, get_profile


def lookup_macos(word: str, macos_dict, parts: Set[str],
                 dict_name: Optional[str] = None,
                 profile: Optional[dict] = None) -> str:
    """
    Look up `word` in a macOS dictionary and return formatted HTML.

    Args:
        word:       the word as the user typed it
        macos_dict: a dict_lookup.MacOSDictionary instance
        parts:      which parts to include (see profiles.profile_parts)
        dict_name:  restrict the lookup to one dictionary by name;
                    None/"" means "all active dictionaries"
        profile:    parsing rules for this dictionary (profiles.py);
                    None = choose a preset by dictionary name
    """
    from .convert import to_simplified, to_traditional
    from .formatter import format_macos_entry

    if profile is None:
        profile = get_profile(default_profile_id_for_dict(dict_name))

    macos_dict.select_dictionary(dict_name or None)

    # Convert the typed word into the script this dictionary expects
    # (e.g. 學習 → 学习 for a simplified-Chinese dictionary). If the
    # converted form isn't found, retry with the original — conversion is
    # a best guess, and some words only exist in one form.
    conversion = profile.get("input_conversion", "none")
    if conversion == "simplified":
        query = to_simplified(word)
    elif conversion == "traditional":
        query = to_traditional(word)
    else:
        query = word

    raw = macos_dict.lookup(query)
    if not raw and query != word:
        query = word
        raw = macos_dict.lookup(word)

    return format_macos_entry(query, raw, parts, profile) if raw else ""


def run_connection(conn: dict, word: str, macos_dict,
                   cfg: Optional[dict] = None) -> str:
    """Run a configured route through its dictionary's curated presets."""
    if not macos_dict:
        return ""
    dict_name = conn.get("dict_name")
    if not dict_name:
        return ""
    settings = (cfg or {}).get("dictionaries", {}).get(dict_name, {})
    if not settings.get("enabled", True):
        return ""
    from .profiles import available_profiles
    choices = available_profiles(dict_name)
    profile_id = conn.get("profile") or settings.get("profile") or default_profile_id_for_dict(dict_name)
    profile = choices.get(profile_id, get_profile("whole_entry"))
    parts = set(conn.get("parts", settings.get("parts", ["definitions"])))
    if profile.get("whole_entry"):
        parts = {"definitions"}
    return lookup_macos(word, macos_dict, parts, dict_name, profile)
