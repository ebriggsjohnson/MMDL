"""Build and import the package without relying on the source checkout."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).parents[1]


def test_package_is_self_contained(tmp_path):
    spec = importlib.util.spec_from_file_location("build_package", ROOT / "build_package.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    path = builder.build_package(tmp_path / "addon.ankiaddon")
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert "meta.json" not in names
        assert not any("__pycache__" in name or name.startswith("tests/") for name in names)
        assert json.loads(archive.read("manifest.json"))["package"] == "mmdl"
        assert not any("moe" in name for name in names)
        archive.extractall(tmp_path / "mmdl")
    script = """
import importlib
import sys
from unittest.mock import MagicMock
for name in ["aqt", "aqt.qt", "aqt.utils", "aqt.gui_hooks"]:
    sys.modules[name] = MagicMock()
sys.path.insert(0, sys.argv[1])
package = importlib.import_module("mmdl")
convert = importlib.import_module("mmdl.convert")
assert convert.to_traditional("学习") == "學習"
"""
    subprocess.run([sys.executable, "-I", "-c", script, str(tmp_path)],
                   check=True, capture_output=True, text=True)
