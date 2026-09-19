"""
Editor integration — auto-fill definition fields when the user types a word.

The central idea is a *connection*: one saved instruction that says
"when the word field changes, look it up in this dictionary (parsed with
this profile) and write these parts into that field". A note type can have
any number of connections. They're created in Settings and stored in the
add-on config under "note_types".

Flow:
- User types a word in a note field and tabs/clicks away
- Anki fires the editor_did_unfocus_field hook (we registered for it below)
- Every connection whose *input field* is the one just left gets run:
  the word is looked up and the connection's *output field* is filled
- Fields are only filled if empty (unless overwrite_existing is set), so
  user edits are never clobbered

Also adds a 典 toggle button to the editor toolbar to turn auto-fill on/off.

"""

import logging
from html import unescape
import os
import re
from typing import List, Dict

from aqt import mw, gui_hooks
from aqt.utils import tooltip


_logger = logging.getLogger("mmdl")


# ------------------------------------------------------------------ #
#  Config                                                              #
# ------------------------------------------------------------------ #

def _cfg() -> dict:
    """Return the merged add-on config (Anki defaults from config.json)."""
    addon = __name__.split(".")[0]
    cfg = mw.addonManager.getConfig(addon)
    if cfg is None:
        # Fallback when getConfig can't locate the add-on (e.g. non-standard layout)
        import json
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    return cfg


def _save_cfg(cfg: dict):
    mw.addonManager.writeConfig(__name__.split(".")[0], cfg)


def is_auto_enabled() -> bool:
    return bool(_cfg().get("auto_generate", True))


def set_auto_enabled(v: bool):
    cfg = _cfg()
    cfg["auto_generate"] = bool(v)
    _save_cfg(cfg)


# ------------------------------------------------------------------ #
#  Field resolution                                                    #
# ------------------------------------------------------------------ #

def _get_connections(model_name: str) -> List[Dict]:
    """Only explicitly configured routes can write to a note."""
    return _cfg().get("note_types", {}).get(model_name, {}).get("connections", [])


# ------------------------------------------------------------------ #
#  Lookup + fill                                                       #
# ------------------------------------------------------------------ #

def _lookup_and_fill(note, word: str, connections: List[Dict], field_names: List[str]) -> bool:
    """Run each triggered connection and fill the target fields."""
    cfg = _cfg()
    overwrite = bool(cfg.get("overwrite_existing", False))

    try:
        from . import _get_macos_dict
        from .lookup import run_connection
    except Exception:
        _logger.exception("import error during lookup")
        return False

    macos_dict = _get_macos_dict()
    changed = False

    for conn in connections:
        output_field = conn.get("output_field")
        if output_field == conn.get("input_field"):
            continue
        if not output_field or output_field not in field_names:
            continue
        idx = field_names.index(output_field)
        if idx >= len(note.fields):
            continue
        if not overwrite and note.fields[idx].strip():
            continue
        try:
            html = run_connection(conn, word, macos_dict, cfg)
            if html:
                note.fields[idx] = html
                changed = True
        except Exception:
            _logger.exception("lookup failed for %r in %s", word, conn.get("dict_name"))

    return changed


# ------------------------------------------------------------------ #
#  Hooks                                                               #
# ------------------------------------------------------------------ #

def on_editor_did_unfocus_field(changed_by_user: bool, note, current_field_idx: int) -> bool:
    """Editor hook: when a field loses focus, auto-fill via configured connections."""
    if not is_auto_enabled():
        return changed_by_user

    try:
        model = note.note_type() if hasattr(note, "note_type") else note.model()
    except Exception:
        _logger.exception("could not get note model")
        return changed_by_user
    if not model:
        return changed_by_user

    field_names = [f["name"] for f in model["flds"]]
    if current_field_idx < 0 or current_field_idx >= len(field_names):
        return changed_by_user

    current_field_name = field_names[current_field_idx]
    connections = _get_connections(model["name"])
    triggered = [c for c in connections if c.get("input_field") == current_field_name]
    if not triggered:
        return changed_by_user

    word = unescape(re.sub(r"<[^>]+>", "", note.fields[current_field_idx])).strip()
    if not word:
        return changed_by_user

    return _lookup_and_fill(note, word, triggered, field_names) or changed_by_user


# ------------------------------------------------------------------ #
#  Toolbar button: 典                                                  #
# ------------------------------------------------------------------ #

_BUTTON_ID = "mmdl_toggle"


def _on_toggle_clicked(editor):
    new_state = not is_auto_enabled()
    set_auto_enabled(new_state)
    tooltip(f"MMDL auto-fill: {'ON' if new_state else 'OFF'}", period=1200)
    _sync_button_state(editor)


def _sync_button_state(editor):
    """Match the toolbar button's highlight to the current auto-gen state."""
    state = "true" if is_auto_enabled() else "false"
    editor.web.eval(
        f"""
        setTimeout(function() {{
            const btn = document.getElementById('{_BUTTON_ID}');
            if (!btn) return;
            btn.classList.toggle('highlighted', {state});
            btn.setAttribute('aria-pressed', '{state}');
        }}, 50);
        """
    )


def on_editor_did_init_buttons(buttons, editor):
    btn = editor.addButton(
        icon=None,
        cmd=_BUTTON_ID,
        func=_on_toggle_clicked,
        tip="MMDL auto-fill (toggle)",
        label="典",
        id=_BUTTON_ID,
        toggleable=True,
        disables=False,
    )
    buttons.append(btn)


def on_editor_did_load_note(editor):
    try:
        _sync_button_state(editor)
    except Exception:
        _logger.exception("failed to sync button state")


# ------------------------------------------------------------------ #
#  Registration                                                        #
# ------------------------------------------------------------------ #

def register_hooks():
    gui_hooks.editor_did_unfocus_field.append(on_editor_did_unfocus_field)
    gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
    gui_hooks.editor_did_load_note.append(on_editor_did_load_note)
