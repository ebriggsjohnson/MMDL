# Code map

The main flow is:

```text
editor.py → lookup.py → dict_lookup.py → entry_parser.py → formatter.py
```

- `__init__.py` registers menus and editor hooks.
- `editor.py` reads configured routes, fills fields, and controls the toolbar toggle.
- `lookup.py` selects a dictionary and applies its query conversion and preset.
- `dict_lookup.py` calls macOS DictionaryServices through ctypes.
- `dictionary_metadata.py` checks for downloaded entry data and reads languages.
- `packs.py` matches exact dictionary names to curated presets and defaults.
- `profiles.py` defines the supported parsing recipes and output parts.
- `entry_parser.py` extracts structured parts from dictionary text.
- `formatter.py` escapes text and renders the selected parts as HTML.
- `gui.py` contains dictionary settings, connections, preview, and bulk fill.
- `convert.py` lazily loads the bundled Chinese script converters.
- `build_package.py` includes only runtime files in the installable archive.

The parser and formatter have no Anki UI dependencies. Bulk fill performs its
lookups on a worker and calls Anki's `update_notes()` once for a single undo step.
The field-unfocus hook preserves earlier add-ons' `changed` value.

## Add a curated preset

1. Capture short raw entries with `cli.py --dict "Dictionary name" --raw word`.
2. Record the source dictionary version and include difficult cases.
3. Add a recipe in `profiles.py` and a matching entry in `packs.py`.
4. Add samples and expected results under `tests/fixtures/`, then test them.

Presets target specific dictionaries, not languages. Unknown dictionaries
retain their complete text. Unsupported preset IDs fall back to whole entry.
The existing Xiandai fixtures came from earlier regression tests; their exact
dictionary version and capture dates were not recorded.

## Settings

`dictionaries[name]` contains the use switch and default format for new routes.
`note_types[name].connections` contains explicit input-to-output routes. No
connection means no automatic fill. Input and output fields must be different.

Settings are edited in a copy until Save. Switching note types first saves the
current edits into that copy. Cancel discards them.

## Tests

`python3 -m pytest` tests the parser, metadata, routing, HTML, and a freshly
built package. The package test imports the extracted add-on in an isolated
Python process, so missing runtime files cannot be masked by this checkout.
All tests belong to this repository; no companion project is required.
