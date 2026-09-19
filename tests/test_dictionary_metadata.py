"""Installed content and language detection are independent of parser packs."""
import plistlib
from unittest.mock import Mock

from dictionary_metadata import read_dictionary_metadata, language_name
from dict_lookup import MacOSDictionary


def test_placeholder_bundle_is_not_installed(tmp_path):
    contents = tmp_path / 'Contents'
    contents.mkdir()
    (contents / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleName': 'Placeholder'}))
    assert read_dictionary_metadata(tmp_path) is None
    resources = contents / 'Resources'
    resources.mkdir()
    (resources / 'Body.data').touch()
    assert read_dictionary_metadata(tmp_path) is None


def test_installed_bilingual_metadata_without_any_curated_pack(tmp_path):
    resources = tmp_path / 'Contents/Resources'
    resources.mkdir(parents=True)
    (resources / 'Body.data').write_bytes(b'entry data')
    info = {'DCSDictionaryPrimaryLanguage': 'zh_CN', 'DCSDictionaryLanguages': [
        {'DCSDictionaryIndexLanguage': 'zh_CN', 'DCSDictionaryDescriptionLanguage': 'zh_CN'},
        {'DCSDictionaryIndexLanguage': 'en', 'DCSDictionaryDescriptionLanguage': 'zh_CN'},
    ]}
    (tmp_path / 'Contents/Info.plist').write_bytes(plistlib.dumps(info))
    assert read_dictionary_metadata(tmp_path)['language'] == 'Chinese (Simplified) / English'


def test_unknown_metadata_is_not_guessed(tmp_path):
    resources = tmp_path / 'Contents/Resources'
    resources.mkdir(parents=True)
    (resources / 'Body.data').write_bytes(b'entry data')
    (tmp_path / 'Contents/Info.plist').write_bytes(plistlib.dumps({}))
    assert read_dictionary_metadata(tmp_path)['language'] == 'Not provided by dictionary'
    assert language_name('xx_Latn') == 'xx_Latn'
    assert language_name('zh-Hant') == 'Chinese (Traditional)'
    assert language_name('fr') == 'French'


def test_catalogue_entries_without_content_are_filtered_and_collection_released():
    backend = MacOSDictionary.__new__(MacOSDictionary)
    backend._has_private_api = True
    backend._cs = Mock()
    backend._cf = Mock()
    backend._cs.DCSCopyAvailableDictionaries.return_value = 99
    backend._cf_collection_to_list = Mock(return_value=[1, 2, 3])
    backend._dictionary_metadata = Mock(side_effect=[None, {'language': 'French', 'path': '/installed'}, None])
    backend._cfstring_to_python = Mock(side_effect=['French Dictionary', 'French'])
    assert backend.list_dictionaries() == [('French Dictionary', 'French')]
    backend._cf.CFRelease.assert_called_once_with(99)
