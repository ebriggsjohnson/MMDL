# MMDL

Fill Anki fields from downloaded macOS dictionaries.

## Install

Requires macOS and Anki Desktop. Build with Python 3.9 or newer:

```sh
python3 build_package.py
```

Install `dist/mmdl.ankiaddon` through **Tools → Add-ons → Install from file**,
then restart Anki. The build needs no downloads or third-party Python packages.

## Use

1. Download your dictionaries in Dictionary.app Settings.
2. Open **MMDL → Settings**. The dictionary list includes only local entry data.
3. Under **Connections**, select a note type and add an input, dictionary, and output.
4. Type a word and leave its input field. The **典** button toggles automatic fill.

Existing text is kept unless you enable overwriting. **Fill Deck…** applies
your saved connections to existing notes in one undoable background operation.

**Curated** means a dictionary has a developer-maintained preset with optional
parts. Currently this is 现代汉语规范词典, with pinyin, parts of speech,
definitions, examples, and usage notes. Other dictionaries use **Whole entry**.
Language labels come from dictionary metadata and do not imply preset support.

Dictionary format defaults apply to new connections. Existing connections keep
their own choices. There is no field guessing or user-created parser system.

## Development

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m pytest
python3 cli.py --list-dicts
python3 cli.py --dict 现代汉语规范词典 --raw 学习
```

Optional dialog checks: install `PyQt6`, then run `python3 tests/smoke_dialogs.py`.
They use fake note types and never open a collection.

See [DESIGN.md](DESIGN.md) for the code map and adding curated presets,
[THIRD_PARTY.md](THIRD_PARTY.md) for bundled dependencies, and
[UPLOAD.md](UPLOAD.md) for uploading this folder to GitHub.

Dictionary discovery uses private macOS APIs and may change between system
versions. Test installation, preview, automatic fill, bulk fill, and Undo in
a disposable Anki profile before publishing an AnkiWeb release.
