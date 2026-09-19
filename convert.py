"""Chinese script conversion, used only by recipes that request it.

The vendor is package-local so other Anki add-ons cannot replace it through
sys.path. Each converter loads its dictionaries once, on first use.
"""
try:
    from .vendor.opencc import OpenCC
except ImportError:  # standalone CLI
    from vendor.opencc import OpenCC

_s2t = None
_t2s = None


def is_available() -> bool:
    return True


def to_traditional(text: str) -> str:
    global _s2t
    if _s2t is None:
        _s2t = OpenCC("s2t")
    return _s2t.convert(text)


def to_simplified(text: str) -> str:
    global _t2s
    if _t2s is None:
        _t2s = OpenCC("t2s")
    return _t2s.convert(text)
