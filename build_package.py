"""Build an installable Anki archive using only the Python standard library."""
import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
RUNTIME_FILES = (
    "__init__.py",
    "editor.py",
    "gui.py",
    "lookup.py",
    "profiles.py",
    "packs.py",
    "entry_parser.py",
    "formatter.py",
    "dict_lookup.py",
    "dictionary_metadata.py",
    "convert.py",
    "config.json",
    "config.md",
    "manifest.json",
    "THIRD_PARTY.md",
)


def build_package(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in RUNTIME_FILES:
            archive.write(ROOT / name, name)
        for path in sorted((ROOT / "vendor").rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc" and path.name != ".DS_Store":
                archive.write(path, path.relative_to(ROOT))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/mmdl.ankiaddon")
    args = parser.parse_args()
    output = build_package(args.output)
    print(f"Built {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
