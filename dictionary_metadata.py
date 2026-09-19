"""Read installed dictionary metadata without guessing from a parser preset."""
from pathlib import Path
import plistlib


LANGUAGES = {
    "ar": "Arabic", "ca": "Catalan", "cs": "Czech", "da": "Danish",
    "de": "German", "el": "Greek", "en": "English", "es": "Spanish",
    "fi": "Finnish", "fr": "French", "he": "Hebrew", "hi": "Hindi",
    "hr": "Croatian", "hu": "Hungarian", "id": "Indonesian", "it": "Italian",
    "ja": "Japanese", "ko": "Korean", "ms": "Malay", "nl": "Dutch",
    "no": "Norwegian", "nb": "Norwegian", "pl": "Polish", "pt": "Portuguese",
    "ro": "Romanian", "ru": "Russian", "sk": "Slovak", "sv": "Swedish",
    "th": "Thai", "tr": "Turkish", "uk": "Ukrainian", "vi": "Vietnamese",
    "zh": "Chinese",
}


def language_name(code):
    """Keep unknown codes visible; do not invent metadata."""
    normalized = code.replace("-", "_")
    language = normalized.split("_")[0].lower()
    if language == "zh":
        if "Hans" in normalized or normalized in ("zh_CN", "zh_SG"):
            return "Chinese (Simplified)"
        if "Hant" in normalized or normalized in ("zh_TW", "zh_HK", "zh_MO"):
            return "Chinese (Traditional)"
    return LANGUAGES.get(language, code)


def read_dictionary_metadata(bundle_path):
    """Return metadata only when a bundle has nonempty local entry data.

    Catalogue placeholders can have an Info.plist without the actual entry
    database. A Wikipedia service is also not an offline dictionary.
    """
    bundle = Path(bundle_path)
    body = bundle / "Contents" / "Resources" / "Body.data"
    try:
        if not body.is_file() or body.stat().st_size == 0:
            return None
        with (bundle / "Contents" / "Info.plist").open("rb") as stream:
            metadata = plistlib.load(stream)
    except (OSError, ValueError, plistlib.InvalidFileException):
        return None

    languages = []
    codes = [metadata.get("DCSDictionaryPrimaryLanguage")]
    for pair in metadata.get("DCSDictionaryLanguages", []):
        codes.extend([pair.get("DCSDictionaryIndexLanguage"),
                      pair.get("DCSDictionaryDescriptionLanguage")])
    for code in codes:
        if isinstance(code, str) and code:
            name = language_name(code)
            if name not in languages:
                languages.append(name)
    return {"language": " / ".join(languages) or "Not provided by dictionary",
            "path": str(bundle)}
