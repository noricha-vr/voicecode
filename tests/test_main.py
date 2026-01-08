"""main.pyのホットキー関連機能のテスト。"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from pynput import keyboard

from main import VoiceCodeApp, _format_hotkey, _parse_hotkey


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


class TestVoiceCodeAppConstants:
    """VoiceCodeAppの定数テスト。"""

    def test_icon_constants(self):
        """状態アイコン定数が正しいこと。"""
        assert VoiceCodeApp.ICON_IDLE == "■"
        assert VoiceCodeApp.ICON_RECORDING == "●"
        assert VoiceCodeApp.ICON_PROCESSING == "↻"

    def test_sound_constants(self):
        """効果音定数が正しいパスであること。"""
        assert VoiceCodeApp.SOUND_START == "/System/Library/Sounds/Tink.aiff"
        assert VoiceCodeApp.SOUND_STOP == "/System/Library/Sounds/Pop.aiff"
        assert VoiceCodeApp.SOUND_SUCCESS == "/System/Library/Sounds/Glass.aiff"
        assert VoiceCodeApp.SOUND_ERROR == "/System/Library/Sounds/Basso.aiff"


class TestVoiceCodeAppPlaySound:
    """VoiceCodeAppの_play_soundメソッドのテスト。"""

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", {"HOTKEY": "f15"})
    def test_play_sound_calls_afplay(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """_play_soundがafplayコマンドを呼び出すこと。"""
        app = VoiceCodeApp()
        app._play_sound("/System/Library/Sounds/Tink.aiff")

        mock_popen.assert_called_with(
            ["afplay", "/System/Library/Sounds/Tink.aiff"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", {"HOTKEY": "f15"})
    def test_play_sound_runs_async(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """_play_soundが非同期で実行されること（Popenを使用）。"""
        app = VoiceCodeApp()
        app._play_sound("/System/Library/Sounds/Pop.aiff")

        # Popen が呼ばれていることで非同期実行を確認
        assert mock_popen.called


class TestVoiceCodeAppInitialization:
    """VoiceCodeAppの初期化テスト。"""

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", {"HOTKEY": "f15"})
    def test_init_sets_idle_title(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """初期化時にIDLEアイコンがタイトルに設定されること。"""
        app = VoiceCodeApp()
        assert app.title == VoiceCodeApp.ICON_IDLE

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", {"HOTKEY": "f15"})
    def test_init_starts_keyboard_listener(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """初期化時にキーボードリスナーが起動されること。"""
        app = VoiceCodeApp()
        mock_listener.assert_called_once()

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", {"HOTKEY": "f15"})
    def test_init_starts_timeout_timer(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """初期化時にタイムアウトタイマーが起動されること。"""
        app = VoiceCodeApp()
        mock_timer.assert_called_once()
        mock_timer.return_value.start.assert_called_once()
