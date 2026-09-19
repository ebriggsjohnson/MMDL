"""Anki dialogs for dictionary defaults, connections, and bulk fill."""

from typing import List
from copy import deepcopy

from aqt import mw
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QComboBox, QCheckBox, QGroupBox,
    QFormLayout, QGridLayout, QTableWidget, QTabWidget,
    QTableWidgetItem, QHeaderView, QWidget, QLineEdit,
)
from aqt.utils import showInfo, showWarning, tooltip


# ------------------------------------------------------------------ #
#  Fill Deck — the one bulk operation                                  #
# ------------------------------------------------------------------ #

class FillDeckDialog(QDialog):
    """
    Fill in definition fields across every note in a deck.

    This is the bulk tool. It doesn't create notes and it doesn't export
    anything — it takes notes you already have and fills the fields your
    connections point at (Settings → Connections), the same way auto-fill
    does when you tab out of a field in the editor.

    Because it reuses the connections you already configured, there is
    nothing to set up here: pick a deck, press the button. Notes whose
    note type has no connections are skipped.

    By default it only writes to fields that are empty, so running it
    twice is harmless and your own edits are never overwritten.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("MMDL — Fill Deck")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)

        blurb = QLabel(
            "Uses your saved connections. Existing text is kept unless you choose to overwrite it."
        )
        blurb.setWordWrap(True)
        blurb.setStyleSheet("color: gray;")
        layout.addWidget(blurb)

        form = QFormLayout()
        self._deck_combo = QComboBox()
        self._deck_combo.setMinimumWidth(300)
        self._deck_combo.addItem("(whole collection)", None)
        for deck in sorted(mw.col.decks.all_names_and_ids(),
                           key=lambda d: d.name):
            self._deck_combo.addItem(deck.name, deck.id)
        form.addRow("Deck", self._deck_combo)
        layout.addLayout(form)

        self._cb_overwrite = QCheckBox(
            "Overwrite existing text"
        )
        layout.addWidget(self._cb_overwrite)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self._btn_close = QPushButton("Close")
        self._btn_close.clicked.connect(self.reject)
        buttons.addWidget(self._btn_close)
        self._btn_fill = QPushButton("Fill")
        self._btn_fill.setDefault(True)
        self._btn_fill.clicked.connect(self._do_fill)
        buttons.addWidget(self._btn_fill)
        layout.addLayout(buttons)

    # ---------------------------------------------------------------- #

    def _note_ids(self) -> List[int]:
        """Every note in the chosen deck (or the whole collection)."""
        deck_name = self._deck_combo.currentText()
        if self._deck_combo.currentData() is None:
            return list(mw.col.find_notes(""))
        # Quote the name — deck names routinely contain spaces and "::".
        escaped = deck_name.replace('"', '\\"')
        return list(mw.col.find_notes(f'deck:"{escaped}"'))

    def _do_fill(self):
        from .editor import _get_connections, _cfg
        from .lookup import run_connection
        from .dict_lookup import MacOSDictionary
        from aqt.operations import CollectionOp

        note_ids = self._note_ids()
        if not note_ids:
            showWarning("No notes found there.")
            return
        cfg = _cfg()
        overwrite = self._cb_overwrite.isChecked()
        connections = {}
        for model in mw.col.models.all_names_and_ids():
            connections[model.name] = _get_connections(model.name)
        counts = {"filled": 0}

        def operation(collection):
            # Create the native backend on this worker; do not share the
            # editor's selected dictionary while a bulk fill is running.
            backend = MacOSDictionary()
            changed_notes = []
            for note_id in note_ids:
                note = collection.get_note(note_id)
                changed = False
                for conn in connections.get(note.note_type()["name"], []):
                    source = conn.get("input_field")
                    target = conn.get("output_field")
                    if source == target or source not in note or target not in note:
                        continue
                    if note[target].strip() and not overwrite:
                        continue
                    word = _plain_text(note[source]).strip()
                    if not word:
                        continue
                    html = run_connection(conn, word, backend, cfg)
                    if html and html != note[target]:
                        note[target] = html
                        changed = True
                if changed:
                    changed_notes.append(note)
            counts["filled"] = len(changed_notes)
            return collection.update_notes(changed_notes)

        def finished(changes):
            showInfo(f"Filled {counts['filled']} of {len(note_ids)} notes. You can undo this fill in Anki.")

        self.accept()
        CollectionOp(parent=mw, op=operation).success(finished).run_in_background()


def _plain_text(html: str) -> str:
    """Strip HTML tags so a field's text can be used as a lookup word."""
    import re
    from html import unescape
    return unescape(re.sub(r"<[^>]+>", "", html or ""))



# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
#  Connection constants                                                #
# ------------------------------------------------------------------ #

class FormatOptions(QWidget):
    """Preset and output checkboxes shared by dictionary and route dialogs."""

    def __init__(self, dictionary_name, profile_id, parts, parent=None):
        super().__init__(parent)
        from .profiles import part_label, profile_parts
        self._part_label = part_label
        self._profile_parts = profile_parts
        self.checks = {}
        layout = QVBoxLayout(self)
        self.combo = QComboBox()
        layout.addWidget(self.combo)
        self.summary = QLabel("Whole entry")
        layout.addWidget(self.summary)
        self._parts_layout = QGridLayout()
        layout.addLayout(self._parts_layout)
        self.combo.currentIndexChanged.connect(self._preset_changed)
        self.set_dictionary(dictionary_name, profile_id, parts)

    def set_dictionary(self, name, profile_id, parts):
        from .profiles import available_profiles
        self._profiles = available_profiles(name)
        self.combo.blockSignals(True)
        self.combo.clear()
        for pid, profile in self._profiles.items():
            if pid == "whole_entry":
                label = "Whole entry"
            else:
                label = "Curated"
            self.combo.addItem(label, pid)
        index = self.combo.findData(profile_id)
        self.combo.setCurrentIndex(index if index >= 0 else 0)
        self.combo.blockSignals(False)
        self.combo.setVisible(len(self._profiles) > 1)
        self.summary.setVisible(len(self._profiles) == 1)
        self.set_parts(parts)

    def profile(self):
        return self._profiles[self.combo.currentData()]

    def parts(self):
        if self.profile().get("whole_entry"):
            return ["definitions"]
        return [part for part, checkbox in self.checks.items() if checkbox.isChecked()]

    def _preset_changed(self):
        self.set_parts(["definitions", "pos", "examples"])

    def set_parts(self, parts):
        while self._parts_layout.count():
            item = self._parts_layout.takeAt(0)
            item.widget().deleteLater()
        self.checks = {}
        if self.profile().get("whole_entry"):
            return
        for index, part in enumerate(self._profile_parts(self.profile())):
            label = self._part_label(part)
            checkbox = QCheckBox(label)
            checkbox.setChecked(part in parts)
            self.checks[part] = checkbox
            self._parts_layout.addWidget(checkbox, index // 3, index % 3)


class DictionaryFormatDialog(QDialog):
    """Default output for new connections to one dictionary."""

    def __init__(self, parent, name, settings):
        super().__init__(parent)
        from .packs import pack_for_dictionary
        pack = pack_for_dictionary(name)
        self.setWindowTitle(f"Format — {name}")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Applies to new connections."))
        self.options = FormatOptions(name, settings.get("profile", pack["profile"]),
                                     settings.get("parts", pack["parts"]))
        layout.addWidget(self.options)
        save = QPushButton("Save")
        save.clicked.connect(self._save)
        layout.addWidget(save)

    def _save(self):
        if not self.options.parts():
            showWarning("Select at least one output part.")
            return
        self.accept()


class ConnectionEditDialog(QDialog):
    """Plain-language routing with a preset, part checkboxes, and preview."""

    def __init__(self, parent, field_names, connection=None, dictionaries=None):
        super().__init__(parent)
        self._dictionaries = dictionaries or {}
        conn = connection or {}
        self._field_names = field_names
        self.setWindowTitle("Dictionary connection")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._input = QComboBox()
        self._input.addItems(field_names)
        self._output = QComboBox()
        self._output.addItems(field_names)
        if len(field_names) > 1:
            self._output.setCurrentIndex(1)
        for combo, key in ((self._input, "input_field"), (self._output, "output_field")):
            if conn.get(key):
                if conn[key] not in field_names:
                    combo.addItem(conn[key])
                combo.setCurrentText(conn[key])
        self._dictionary = QComboBox()
        from . import _get_macos_dict
        backend = _get_macos_dict()
        names = [name for name, short in backend.list_dictionaries()] if backend else []
        saved_name = conn.get("dict_name") or ""
        if saved_name and saved_name not in names:
            names.append(saved_name)
        for name in sorted(set(names)):
            if self._dictionaries.get(name, {}).get("enabled", True) or name == saved_name:
                self._dictionary.addItem(name, name)
        if connection:
            self._dictionary.setCurrentIndex(self._dictionary.findData(saved_name))
        form.addRow("Input", self._input)
        form.addRow("Dictionary", self._dictionary)
        form.addRow("Output", self._output)
        layout.addLayout(form)
        defaults = self._format_defaults()
        self.options = FormatOptions(self._dictionary.currentData() or "",
                                     conn.get("profile") or defaults["profile"],
                                     conn.get("parts", defaults["parts"]))
        group = QGroupBox("Format")
        QVBoxLayout(group).addWidget(self.options)
        layout.addWidget(group)
        self._dictionary.currentIndexChanged.connect(self._dictionary_changed)
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        row = QHBoxLayout()
        self._word = QLineEdit()
        self._word.setPlaceholderText("Test word")
        self._word.returnPressed.connect(self._preview_word)
        row.addWidget(self._word)
        lookup = QPushButton("Look up")
        lookup.clicked.connect(self._preview_word)
        row.addWidget(lookup)
        preview_layout.addLayout(row)
        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        preview_layout.addWidget(self._preview)
        layout.addWidget(preview_group)
        buttons = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _format_defaults(self):
        from .packs import pack_for_dictionary
        name = self._dictionary.currentData() or ""
        pack = pack_for_dictionary(name)
        settings = self._dictionaries.get(name, {})
        from .profiles import available_profiles
        profile_id = settings.get("profile", pack["profile"])
        if profile_id not in available_profiles(name):
            return {"profile": pack["profile"], "parts": pack["parts"]}
        return {"profile": profile_id, "parts": settings.get("parts", pack["parts"])}

    def _dictionary_changed(self):
        defaults = self._format_defaults()
        self.options.set_dictionary(self._dictionary.currentData() or "",
                                    defaults["profile"], defaults["parts"])

    def _preview_word(self):
        from . import _get_macos_dict
        from .lookup import lookup_macos
        word = self._word.text().strip()
        if not word:
            return
        backend = _get_macos_dict()
        if not backend:
            self._preview.setPlainText("macOS dictionaries are unavailable.")
            return
        try:
            html = lookup_macos(word, backend, set(self.options.parts()),
                                self._dictionary.currentData() or "",
                                self.options.profile())
            self._preview.setHtml(html or "No entry found.")
        except Exception as error:
            self._preview.setPlainText(f"Lookup failed: {error}")

    def _save(self):
        if self._dictionary.currentIndex() < 0:
            showWarning("Enable a dictionary in Dictionary.app and reopen Settings.")
            return
        if self._input.currentText() not in self._field_names or self._output.currentText() not in self._field_names:
            showWarning("Select input and output fields that exist in this note type.")
            return
        if self._input.currentText() == self._output.currentText():
            showWarning("Choose different input and output fields.")
            return
        if not self.options.parts():
            showWarning("Select at least one output part.")
            return
        self.accept()

    def get_connection(self):
        return {"dict_name": self._dictionary.currentData(),
                "input_field": self._input.currentText(), "output_field": self._output.currentText(),
                "profile": self.options.combo.currentData(), "parts": self.options.parts()}


class SettingsDialog(QDialog):
    """
    Dictionary selection and connections with curated output formats.
    Each dictionary has format defaults; each route can override them.

    Nothing touches the saved config until Save is clicked; both the
    dictionary defaults and connections are edited in memory first.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self._addon_name = __name__.split(".")[0]
        self._cfg = deepcopy(mw.addonManager.getConfig(self._addon_name) or {})
        self._active_model = None
        self._dictionaries = self._cfg.setdefault("dictionaries", {})
        self._connections: List[dict] = []
        self._setup_ui()
        self._on_model_changed()

    def _setup_ui(self):
        self.setWindowTitle("MMDL — Settings")
        self.setMinimumSize(700, 680)
        layout = QVBoxLayout(self)

        gen_group = QGroupBox("General")
        gen_layout = QVBoxLayout(gen_group)
        self._cb_auto = QCheckBox("Auto-fill")
        self._cb_auto.setChecked(bool(self._cfg.get("auto_generate", True)))
        gen_layout.addWidget(self._cb_auto)
        self._cb_overwrite = QCheckBox("Overwrite existing text")
        self._cb_overwrite.setChecked(bool(self._cfg.get("overwrite_existing", False)))
        gen_layout.addWidget(self._cb_overwrite)
        layout.addWidget(gen_group)

        tabs = QTabWidget()
        layout.addWidget(tabs)
        dictionary_page = QWidget()
        dictionary_layout = QVBoxLayout(dictionary_page)
        hint = QLabel("Curated presets offer individual parts. Other dictionaries use the whole entry.")
        hint.setWordWrap(True)
        dictionary_layout.addWidget(hint)
        self._dictionary_table = QTableWidget(0, 5)
        self._dictionary_table.setHorizontalHeaderLabels(["Dictionary", "Language", "Preset", "Use", ""])
        self._dictionary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3, 4):
            self._dictionary_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self._dictionary_table.verticalHeader().setVisible(False)
        self._dictionary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        dictionary_layout.addWidget(self._dictionary_table)
        tabs.addTab(dictionary_page, "Dictionaries")
        self._refresh_dictionaries()
        connection_page = QWidget()
        connection_layout = QVBoxLayout(connection_page)
        tabs.addTab(connection_page, "Connections")
        nt_row = QHBoxLayout()
        nt_row.addWidget(QLabel("Note type"))
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(260)
        self._model_combo.blockSignals(True)
        for m in sorted(mw.col.models.all_names_and_ids(), key=lambda m: m.name):
            self._model_combo.addItem(m.name, m.id)
        self._model_combo.blockSignals(False)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        nt_row.addWidget(self._model_combo)
        nt_row.addStretch()
        connection_layout.addLayout(nt_row)

        conn_group = QGroupBox("Connections")
        conn_layout = QVBoxLayout(conn_group)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Dictionary", "Input", "Output", "Parts"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.doubleClicked.connect(self._edit_connection)
        conn_layout.addWidget(self._table)

        btn_bar = QHBoxLayout()
        btn_add = QPushButton("Add…")
        btn_add.clicked.connect(self._add_connection)
        btn_bar.addWidget(btn_add)
        self._btn_edit = QPushButton("Edit…")
        self._btn_edit.clicked.connect(self._edit_connection)
        btn_bar.addWidget(self._btn_edit)
        self._btn_remove = QPushButton("Remove")
        self._btn_remove.clicked.connect(self._remove_connection)
        btn_bar.addWidget(self._btn_remove)
        btn_bar.addStretch()
        conn_layout.addLayout(btn_bar)
        connection_layout.addWidget(conn_group)

        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        bottom.addWidget(btn_cancel)
        btn_save = QPushButton("Save")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)
        bottom.addWidget(btn_save)
        layout.addLayout(bottom)

    def _store_connections(self):
        if self._active_model:
            self._cfg.setdefault("note_types", {})[self._active_model] = {
                "connections": list(self._connections)
            }

    def _refresh_dictionaries(self):
        from . import _get_macos_dict
        from .packs import pack_for_dictionary
        backend = _get_macos_dict()
        dictionaries = backend.list_dictionary_details() if backend else []
        dictionaries.sort(key=lambda item: item["name"])
        self._dictionary_table.setRowCount(len(dictionaries))
        for row, dictionary in enumerate(dictionaries):
            name = dictionary["name"]
            settings = self._dictionaries.setdefault(name, {"enabled": True})
            self._dictionary_table.setItem(row, 0, QTableWidgetItem(name))
            self._dictionary_table.setItem(row, 1, QTableWidgetItem(dictionary["language"]))
            curated = pack_for_dictionary(name)["profile"] != "whole_entry"
            self._dictionary_table.setItem(row, 2, QTableWidgetItem("Curated" if curated else "Whole entry"))
            enabled = QCheckBox()
            enabled.setToolTip("Use in MMDL")
            enabled.setChecked(settings.get("enabled", True))
            enabled.toggled.connect(lambda checked, name=name: self._set_dictionary_enabled(name, checked))
            self._dictionary_table.setCellWidget(row, 3, enabled)
            configure = QPushButton("Format…")
            configure.setEnabled(curated)
            configure.clicked.connect(lambda checked=False, name=name: self._configure_dictionary(name))
            self._dictionary_table.setCellWidget(row, 4, configure)

    def _set_dictionary_enabled(self, name, enabled):
        self._dictionaries[name]["enabled"] = enabled

    def _configure_dictionary(self, name):
        settings = self._dictionaries[name]
        dialog = DictionaryFormatDialog(self, name, settings)
        if dialog.exec():
            settings["profile"] = dialog.options.combo.currentData()
            settings["parts"] = dialog.options.parts()

    def _field_names(self) -> List[str]:
        model_id = self._model_combo.currentData()
        if not model_id:
            return []
        model = mw.col.models.get(model_id)
        return [f["name"] for f in model["flds"]] if model else []

    def _on_model_changed(self):
        self._store_connections()
        model_name = self._model_combo.currentText()
        note_types = self._cfg.get("note_types", {})
        if model_name in note_types:
            self._connections = list(note_types[model_name].get("connections", []))
        else:
            self._connections = []
        self._active_model = model_name
        self._refresh_table()

    def _refresh_table(self):
        _SHORT = {"pos": "POS", "definitions": "Def", "examples": "Ex",
                  "pinyin": "PY", "bopomofo": "BPF", "usage_notes": "Usage"}
        self._table.setRowCount(0)
        for conn in self._connections:
            row = self._table.rowCount()
            self._table.insertRow(row)
            source_text = conn.get("dict_name") or "All active"
            parts_text = ", ".join(_SHORT.get(p, p) for p in conn.get("parts", []))
            for col, text in enumerate([source_text, conn.get("input_field", ""),
                                        conn.get("output_field", ""), parts_text]):
                self._table.setItem(row, col, QTableWidgetItem(text))

    def _add_connection(self):
        field_names = self._field_names()
        if not field_names:
            showWarning("This note type has no fields.")
            return
        dlg = ConnectionEditDialog(self, field_names,
                                   dictionaries=self._dictionaries)
        if dlg.exec():
            self._connections.append(dlg.get_connection())
            self._refresh_table()

    def _edit_connection(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._connections):
            return
        dlg = ConnectionEditDialog(self, self._field_names(), self._connections[row],
                                   dictionaries=self._dictionaries)
        if dlg.exec():
            self._connections[row] = dlg.get_connection()
            self._refresh_table()

    def _remove_connection(self):
        row = self._table.currentRow()
        if 0 <= row < len(self._connections):
            self._connections.pop(row)
            self._refresh_table()

    def _save(self):
        cfg = dict(self._cfg)
        cfg["auto_generate"] = self._cb_auto.isChecked()
        cfg["overwrite_existing"] = self._cb_overwrite.isChecked()
        self._store_connections()
        cfg["note_types"] = self._cfg.get("note_types", {})
        cfg["dictionaries"] = self._dictionaries
        mw.addonManager.writeConfig(self._addon_name, cfg)
        tooltip("Settings saved.", period=1200)
        self.accept()
