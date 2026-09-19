"""MMDL: macOS dictionaries, editor hooks, and the settings menu.

Read DESIGN.md for the small lookup pipeline and module map.
"""

import logging

from aqt import mw, gui_hooks
from aqt.qt import QAction, QMenu
from aqt.utils import showInfo

_logger = logging.getLogger("mmdl")

# Registry of available dictionary backends
_macos_dict = None


def _get_macos_dict():
    """Get or create the macOS DictionaryServices instance."""
    global _macos_dict
    if _macos_dict is None:
        try:
            from .dict_lookup import MacOSDictionary
            _macos_dict = MacOSDictionary()
        except Exception:
            pass  # Not on macOS or framework unavailable
    return _macos_dict


def _on_fill_deck():
    from .gui import FillDeckDialog
    dialog = FillDeckDialog(mw)
    dialog.exec()


def _on_settings():
    from .gui import SettingsDialog
    dialog = SettingsDialog(mw)
    dialog.exec()


def _on_list_dictionaries():
    lines = []

    macos_d = _get_macos_dict()
    if macos_d:
        dicts = macos_d.list_dictionaries()
        if dicts:
            lines.append("Downloaded macOS Dictionaries:")
            for name, short in sorted(dicts):
                lines.append(f"  {name} ({short})")
        else:
            lines.append("No downloaded dictionaries found, or macOS dictionary discovery is unavailable.")
    else:
        lines.append("macOS DictionaryServices: not available")

    showInfo("\n".join(lines))


def _setup_menu():
    """Build the MMDL menu. Called once, after Anki's main window exists."""
    menu = QMenu("MMDL", mw)

    # setMenuRole(NoRole) stops macOS from hijacking anything named
    # "Settings…" into the application menu.
    a_settings = QAction("Settings…", mw)
    a_settings.setMenuRole(QAction.MenuRole.NoRole)
    a_settings.triggered.connect(_on_settings)
    menu.addAction(a_settings)

    a_fill = QAction("Fill Deck…", mw)
    a_fill.triggered.connect(_on_fill_deck)
    menu.addAction(a_fill)

    menu.addSeparator()

    a_dicts = QAction("Show Available Dictionaries", mw)
    a_dicts.triggered.connect(_on_list_dictionaries)
    menu.addAction(a_dicts)

    mw.form.menubar.addMenu(menu)


gui_hooks.main_window_did_init.append(_setup_menu)

# Register editor hooks for auto-fill as you type
try:
    from .editor import register_hooks as _register_editor_hooks
    _register_editor_hooks()
except Exception:
    _logger.exception("Failed to register editor hooks")
