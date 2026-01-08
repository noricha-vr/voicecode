"""main.pyのホットキー関連機能のテスト。"""

import pytest
from pynput import keyboard

from main import _format_hotkey, _parse_hotkey


class TestParseHotkey:
    """_parse_hotkey関数のテスト。"""

    def test_single_function_key(self):
        """単一ファンクションキーをパースできること。"""
        result = _parse_hotkey("f13")
        assert result == {keyboard.Key.f13}

    def test_function_key_f1(self):
        """F1キーをパースできること。"""
        result = _parse_hotkey("f1")
        assert result == {keyboard.Key.f1}

    def test_function_key_f20(self):
        """F20キーをパースできること。"""
        result = _parse_hotkey("f20")
        assert result == {keyboard.Key.f20}

    def test_modifier_combination(self):
        """修飾キーの組み合わせをパースできること。"""
        result = _parse_hotkey("ctrl+shift+r")
        assert result == {
            keyboard.Key.ctrl,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char("r"),
        }

    def test_cmd_modifier(self):
        """Cmdキーをパースできること。"""
        result = _parse_hotkey("cmd+r")
        assert result == {
            keyboard.Key.cmd,
            keyboard.KeyCode.from_char("r"),
        }

    def test_alt_modifier(self):
        """Altキーをパースできること。"""
        result = _parse_hotkey("alt+a")
        assert result == {
            keyboard.Key.alt,
            keyboard.KeyCode.from_char("a"),
        }

    def test_case_insensitive(self):
        """大文字小文字を区別しないこと。"""
        result = _parse_hotkey("CTRL+SHIFT+R")
        assert result == {
            keyboard.Key.ctrl,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char("r"),
        }

    def test_with_spaces(self):
        """スペースを含む入力を処理できること。"""
        result = _parse_hotkey(" ctrl + shift + r ")
        assert result == {
            keyboard.Key.ctrl,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char("r"),
        }

    def test_single_character(self):
        """単一文字キーをパースできること。"""
        result = _parse_hotkey("a")
        assert result == {keyboard.KeyCode.from_char("a")}

    def test_invalid_function_key_number(self):
        """無効なファンクションキー番号でエラーになること。"""
        with pytest.raises(ValueError, match="Invalid function key"):
            _parse_hotkey("f25")

    def test_unknown_key(self):
        """不明なキー文字列でエラーになること。"""
        with pytest.raises(ValueError, match="Unknown key"):
            _parse_hotkey("unknown")

    def test_empty_string(self):
        """空文字列でエラーになること。"""
        with pytest.raises(ValueError, match="No valid keys found"):
            _parse_hotkey("")

    def test_only_spaces(self):
        """スペースのみでエラーになること。"""
        with pytest.raises(ValueError, match="No valid keys found"):
            _parse_hotkey("   ")


class TestFormatHotkey:
    """_format_hotkey関数のテスト。"""

    def test_single_function_key(self):
        """単一ファンクションキーをフォーマットできること。"""
        keys = {keyboard.Key.f13}
        result = _format_hotkey(keys)
        assert result == "F13"

    def test_modifier_combination(self):
        """修飾キーの組み合わせをフォーマットできること。"""
        keys = {
            keyboard.Key.ctrl,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char("r"),
        }
        result = _format_hotkey(keys)
        assert result == "Ctrl+Shift+R"

    def test_cmd_combination(self):
        """Cmdを含む組み合わせをフォーマットできること。"""
        keys = {
            keyboard.Key.cmd,
            keyboard.KeyCode.from_char("r"),
        }
        result = _format_hotkey(keys)
        assert result == "Cmd+R"

    def test_all_modifiers(self):
        """全修飾キーの順序が正しいこと。"""
        keys = {
            keyboard.Key.alt,
            keyboard.Key.cmd,
            keyboard.Key.ctrl,
            keyboard.Key.shift,
            keyboard.KeyCode.from_char("x"),
        }
        result = _format_hotkey(keys)
        # 修飾キーの順序: Ctrl, Shift, Alt, Cmd
        assert result == "Ctrl+Shift+Alt+Cmd+X"

    def test_single_character(self):
        """単一文字キーをフォーマットできること。"""
        keys = {keyboard.KeyCode.from_char("a")}
        result = _format_hotkey(keys)
        assert result == "A"


class TestParseAndFormatRoundtrip:
    """パースとフォーマットの往復変換テスト。"""

    def test_f13_roundtrip(self):
        """F13の往復変換が正しいこと。"""
        parsed = _parse_hotkey("f13")
        formatted = _format_hotkey(parsed)
        assert formatted == "F13"

    def test_ctrl_shift_r_roundtrip(self):
        """Ctrl+Shift+Rの往復変換が正しいこと。"""
        parsed = _parse_hotkey("ctrl+shift+r")
        formatted = _format_hotkey(parsed)
        assert formatted == "Ctrl+Shift+R"

    def test_cmd_alt_r_roundtrip(self):
        """Cmd+Alt+Rの往復変換が正しいこと。"""
        parsed = _parse_hotkey("cmd+alt+r")
        formatted = _format_hotkey(parsed)
        assert formatted == "Alt+Cmd+R"
