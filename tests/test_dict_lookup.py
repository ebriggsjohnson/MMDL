"""Tests for dictionary selection without loading macOS frameworks."""

from unittest.mock import Mock

from dict_lookup import MacOSDictionary


def _dictionary(selected=None, has_private_api=True):
    dictionary = MacOSDictionary.__new__(MacOSDictionary)
    dictionary._selected_dict_name = selected
    dictionary._has_private_api = has_private_api
    dictionary._lookup_in_dict = Mock()
    dictionary._lookup_all = Mock()
    return dictionary


def test_selected_dictionary_does_not_fall_back_to_all_dictionaries():
    dictionary = _dictionary("现代汉语规范词典")
    dictionary._lookup_in_dict.return_value = None
    dictionary._lookup_all.return_value = "entry from another dictionary"

    assert dictionary.lookup("亲眼目睹") is None
    dictionary._lookup_in_dict.assert_called_once_with(
        "亲眼目睹", "现代汉语规范词典"
    )
    dictionary._lookup_all.assert_not_called()


def test_selected_dictionary_without_private_api_returns_no_result():
    dictionary = _dictionary("现代汉语规范词典", has_private_api=False)
    dictionary._lookup_all.return_value = "entry from another dictionary"

    assert dictionary.lookup("亲眼目睹") is None
    dictionary._lookup_in_dict.assert_not_called()
    dictionary._lookup_all.assert_not_called()


def test_no_selection_searches_all_active_dictionaries():
    dictionary = _dictionary()
    dictionary._lookup_all.return_value = "entry"

    assert dictionary.lookup("亲眼目睹") == "entry"
    dictionary._lookup_all.assert_called_once_with("亲眼目睹")
    dictionary._lookup_in_dict.assert_not_called()
