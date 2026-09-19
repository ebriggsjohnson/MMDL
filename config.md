# Settings

Use **MMDL → Settings** to configure dictionaries and connections.

- `auto_generate`: the **典** toolbar switch.
- `overwrite_existing`: allow automatic fill to replace text.
- `dictionaries`: use switches and defaults for new connections.
- `note_types`: explicit connections for each note type.

Example:

```json
{
  "note_types": {
    "Vocabulary": {
      "connections": [{
        "dict_name": "现代汉语规范词典",
        "profile": "xiandai_hanyu_sample",
        "input_field": "Word",
        "output_field": "Definition",
        "parts": ["pos", "definitions", "examples"]
      }]
    }
  }
}
```

Use `whole_entry` for complete text. Curated presets are defined in the code.
Missing fields and disabled dictionaries are skipped. No connection means
no automatic fill; field names are never guessed.
