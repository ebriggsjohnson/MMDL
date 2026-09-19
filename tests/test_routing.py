"""Curated dictionary routing tests, without a running Anki instance."""
import importlib
import json
import sys
import types
from html import escape
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).parents[1]
package = types.ModuleType("routing_core")
package.__path__ = [str(ROOT)]
sys.modules["routing_core"] = package
lookup = importlib.import_module("routing_core.lookup")
editor = importlib.import_module("routing_core.editor")
profiles = importlib.import_module("routing_core.profiles")
formatter = importlib.import_module("routing_core.formatter")

def test_explicit_empty_routes_never_trigger_field_guessing(monkeypatch):
    monkeypatch.setattr(editor, "_cfg", lambda: {"note_types": {"Vocabulary": {"connections": []}}})
    assert editor._get_connections("Vocabulary") == []


def test_unknown_dictionary_preserves_text_and_escapes_html():
    data = json.loads((ROOT / "tests/fixtures/whole_entry.json").read_text())
    for sample in data["entries"]:
        backend = Mock()
        backend.lookup.return_value = sample["raw"]
        result = lookup.run_connection({"dict_name": "Unknown", "parts": ["definitions"]},
                                       sample["word"], backend)
        assert result == '<span class="def">' + escape(sample["raw"]) + '</span>'
        backend.lookup.assert_called_once_with(sample["word"])


def test_curated_pack_regression_samples():
    parser = importlib.import_module("routing_core.entry_parser")
    data = json.loads((ROOT / "tests/fixtures/xiandai_hanyu.json").read_text())
    for sample in data["entries"]:
        entry = parser.parse_entry(sample["word"], sample["raw"], profiles.CHINESE_SAMPLE)
        assert entry.pronunciation == sample["pronunciation"]
        assert sample["definition_contains"] in entry.senses[0].definition
    assert profiles.default_profile_id_for_dict("Other 汉语 dictionary") == "whole_entry"


def test_empty_parts_produce_no_markup():
    assert formatter.format_macos_entry("word", "word ①one ②two", set()) == ""


def test_core_hook_preserves_previous_addon_changes(monkeypatch):
    monkeypatch.setattr(editor, "is_auto_enabled", lambda: False)
    assert editor.on_editor_did_unfocus_field(True, None, 0) is True
    assert editor.on_editor_did_unfocus_field(False, None, 0) is False


def test_only_matching_curated_presets_are_available():
    assert list(profiles.available_profiles("Unknown")) == ["whole_entry"]
    assert list(profiles.available_profiles("现代汉语规范词典")) == ["xiandai_hanyu_sample", "whole_entry"]


def test_disabled_or_unnamed_dictionary_never_runs():
    backend = Mock()
    assert lookup.run_connection({"dict_name": ""}, "word", backend) == ""
    cfg = {"dictionaries": {"Test": {"enabled": False}}}
    assert lookup.run_connection({"dict_name": "Test"}, "word", backend, cfg) == ""
    backend.lookup.assert_not_called()
