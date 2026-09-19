import sys
from unittest.mock import MagicMock

# The project root has __init__.py which imports aqt (requires a running Anki
# instance). Pytest's Package collector imports that file during setup, before
# any test runs. Stubbing aqt here — before pytest loads anything else — lets
# the import succeed so tests that don't touch Anki internals can run normally.
for _mod in ["aqt", "aqt.qt", "aqt.utils", "aqt.gui_hooks"]:
    sys.modules[_mod] = MagicMock()
