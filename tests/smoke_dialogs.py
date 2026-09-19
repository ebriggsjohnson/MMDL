"""Optional real-Qt smoke test; no Anki collection is opened or modified.

Install PyQt6 in a development environment, then run this script directly.
Screenshots are written to /tmp/mmdl-settings.png and /tmp/moe-settings.png.
"""
import importlib
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from copy import deepcopy

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6 import QtCore, QtGui, QtWidgets

ROOT = Path(__file__).resolve().parents[1]
app = QtWidgets.QApplication([])
parent = QtWidgets.QWidget()
configs = {
    "smoke_core": {"note_types": {
        "Vocabulary": {"connections": []},
    }},
    "smoke_moe": {"input_field": "Front", "output_field": "MOE", "parts": ["definitions"]},
}
models = {
    1: {"name": "Vocabulary", "flds": [{"name": name} for name in ["Front", "Definition", "MOE"]]},
    2: {"name": "Words", "flds": [{"name": name} for name in ["Word", "Meaning", "MOE"]]},
}


def save(name, config):
    configs[name] = deepcopy(config)


mw = SimpleNamespace(
    addonManager=SimpleNamespace(getConfig=lambda name: deepcopy(configs[name]), writeConfig=save),
    col=SimpleNamespace(models=SimpleNamespace(
        all_names_and_ids=lambda: [SimpleNamespace(name=model["name"], id=id) for id, model in models.items()],
        get=lambda id: models[id],
    )),
)
errors = []
aqt = ModuleType("aqt")
aqt.mw = mw
qt = ModuleType("aqt.qt")
for module in [QtCore, QtGui, QtWidgets]:
    for name in dir(module):
        setattr(qt, name, getattr(module, name))
utils = ModuleType("aqt.utils")
utils.showInfo = lambda *args, **kwargs: None
utils.tooltip = lambda *args, **kwargs: None
utils.showWarning = lambda message: errors.append(message)
sys.modules.update({"aqt": aqt, "aqt.qt": qt, "aqt.utils": utils,
                    "aqt.operations": SimpleNamespace(CollectionOp=object)})


def package(name, path):
    module = ModuleType(name)
    module.__path__ = [str(path)]
    sys.modules[name] = module
    return module


core = package("smoke_core", ROOT)
core._get_macos_dict = lambda: SimpleNamespace(
    list_dictionaries=lambda: [("现代汉语规范词典", "Chinese"), ("Test dictionary", "Test")],
    list_dictionary_details=lambda: [
        {"name": "现代汉语规范词典", "language": "Chinese (Simplified)"},
        {"name": "Test dictionary", "language": "English"},
    ],
)
core_gui = importlib.import_module("smoke_core.gui")
settings = core_gui.SettingsDialog(parent)
settings.show()
app.processEvents()
settings.grab().save("/tmp/mmdl-settings.png")
assert settings._connections == []  # retired route is absent from the UI
route = {"dict_name": "Test dictionary",
         "input_field": "Front", "output_field": "Definition", "parts": ["definitions"]}
settings._connections.append(route)
settings._model_combo.setCurrentIndex(1)
settings._connections = []
settings._model_combo.setCurrentIndex(0)
assert settings._connections == [route]
settings._save()
assert configs["smoke_core"]["note_types"]["Words"]["connections"] == []
assert configs["smoke_core"]["note_types"]["Vocabulary"]["connections"] == [route]

connection = core_gui.ConnectionEditDialog(parent, ["Front", "Definition"])
connection._dictionary.setCurrentIndex(connection._dictionary.findData("现代汉语规范词典"))
assert connection.options.combo.currentData() == "xiandai_hanyu_sample"
assert "examples" in connection.options.parts()
connection._dictionary.setCurrentIndex(connection._dictionary.findData("Test dictionary"))
assert connection.options.combo.currentData() == "whole_entry"
assert connection.options.parts() == ["definitions"]
connection.show()
app.processEvents()
connection.grab().save("/tmp/mmdl-connection.png")
connection._save()
assert connection.result() == QtWidgets.QDialog.DialogCode.Accepted

format_dialog = core_gui.DictionaryFormatDialog(parent, "Test dictionary", {})
assert format_dialog.options.parts() == ["definitions"]
assert not hasattr(core_gui, "ProfileEditDialog")
assert connection.options.combo.count() == 1
assert connection.options.combo.currentData() == "whole_entry"
print("MMDL settings and curated presets passed.")
