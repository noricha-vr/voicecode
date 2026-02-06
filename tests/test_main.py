"""main.pyのホットキー関連機能のテスト。"""

import logging
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pynput import keyboard

from main import (
    VoiceCodeApp,
    _StatusItemHelper,
    _daemonize,
    _format_hotkey,
    _parse_args,
    _parse_hotkey,
    check_accessibility_permission,
    check_input_monitoring_permission,
)


# VoiceCodeApp のテストで常に必要なモック
# API キーとマイク権限チェックをモック
VOICECODE_APP_PATCHES = {
    "GOOGLE_API_KEY": "test_google_key",
    "HOTKEY": "f15",
}


@pytest.fixture(autouse=True)
def mock_all_permission_checks():
    """全ての権限チェック関数をモックするフィクスチャ。

    autouse=True により、このモジュール内の全テストで自動的に適用される。
    """
    with patch("main.check_microphone_permission", return_value=True), \
         patch("main.check_input_monitoring_permission", return_value=True), \
         patch("main.check_accessibility_permission", return_value=True):
        yield


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
        """状態アイコン定数が正しいファイル名であること。"""
        assert VoiceCodeApp.ICON_IDLE == "icon_idle.png"
        assert VoiceCodeApp.ICON_RECORDING == "icon_recording.png"
        assert VoiceCodeApp.ICON_PROCESSING == "icon_processing.png"

    def test_sound_constants(self):
        """効果音定数が正しいパスであること。"""
        assert VoiceCodeApp.SOUND_START == "/System/Library/Sounds/Tink.aiff"
        assert VoiceCodeApp.SOUND_STOP == "/System/Library/Sounds/Pop.aiff"
        assert VoiceCodeApp.SOUND_SUCCESS == "/System/Library/Sounds/Glass.aiff"
        assert VoiceCodeApp.SOUND_ERROR == "/System/Library/Sounds/Basso.aiff"


class TestVoiceCodeAppGetIconPath:
    """VoiceCodeAppの_get_icon_pathメソッドのテスト。"""

    def test_get_icon_path_returns_assets_path(self):
        """_get_icon_pathがassets/ディレクトリ内のパスを返すこと。"""
        path = VoiceCodeApp._get_icon_path("icon_idle.png")
        assert "assets" in path
        assert path.endswith("icon_idle.png")

    def test_get_icon_path_all_icons(self):
        """全アイコンファイルのパスが正しく生成されること。"""
        icons = [
            VoiceCodeApp.ICON_IDLE,
            VoiceCodeApp.ICON_RECORDING,
            VoiceCodeApp.ICON_PROCESSING,
        ]
        for icon_name in icons:
            path = VoiceCodeApp._get_icon_path(icon_name)
            assert path.endswith(icon_name)
            assert "assets" in path


class TestVoiceCodeAppPlaySound:
    """VoiceCodeAppの_play_soundメソッドのテスト。"""

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
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
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
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
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_init_sets_idle_icon(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """初期化時にIDLEアイコンが設定されること。"""
        app = VoiceCodeApp()
        # titleは空文字列（アイコンのみ表示）
        assert app.title == ""
        # iconにはパスが設定される
        assert app.icon is not None
        assert VoiceCodeApp.ICON_IDLE in app.icon

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
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
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
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


class TestVoiceCodeAppStopAndProcess:
    """VoiceCodeAppの_stop_and_processメソッドのテスト。"""

    @patch("main.keyboard.Controller")
    @patch("main.pyperclip.copy")
    @patch("main.time.sleep")
    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_stop_and_process_uses_pynput_for_paste(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        mock_sleep,
        mock_copy,
        mock_controller_class,
    ):
        """貼り付け処理がpynputのControllerを使用すること。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = True
        mock_recorder_instance.is_timeout = False
        mock_audio_path = MagicMock(spec=Path)
        mock_audio_path.exists.return_value = True
        mock_recorder_instance.stop.return_value = mock_audio_path
        mock_recorder.return_value = mock_recorder_instance

        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.transcribe.return_value = ("テスト音声", 1.23)
        mock_transcriber.return_value = mock_transcriber_instance

        mock_postprocessor_instance = MagicMock()
        mock_postprocessor_instance.process.return_value = ("processed text", 0.45)
        mock_postprocessor.return_value = mock_postprocessor_instance

        mock_controller_instance = MagicMock()
        mock_controller_class.return_value = mock_controller_instance

        app = VoiceCodeApp()

        # Act
        app._stop_and_process()

        # Assert
        # pynput の Controller が作成されること
        mock_controller_class.assert_called_once()
        # pressed() が cmd キーで呼ばれること
        mock_controller_instance.pressed.assert_called_once_with(keyboard.Key.cmd)
        # tap() が 'v' で呼ばれること（コンテキストマネージャ内で）
        mock_controller_instance.pressed.return_value.__enter__.assert_called_once()
        mock_controller_instance.tap.assert_called_once_with('v')

    @patch("main.keyboard.Controller")
    @patch("main.pyperclip.paste")
    @patch("main.pyperclip.copy")
    @patch("main.time.sleep")
    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_stop_and_process_copies_to_clipboard_before_paste(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        mock_sleep,
        mock_copy,
        mock_paste,
        mock_controller_class,
    ):
        """貼り付け前にクリップボードにコピーされ、元の内容が復元されること。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = True
        mock_recorder_instance.is_timeout = False
        mock_audio_path = MagicMock(spec=Path)
        mock_audio_path.exists.return_value = True
        mock_recorder_instance.stop.return_value = mock_audio_path
        mock_recorder.return_value = mock_recorder_instance

        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.transcribe.return_value = ("テスト音声", 1.23)
        mock_transcriber.return_value = mock_transcriber_instance

        mock_postprocessor_instance = MagicMock()
        mock_postprocessor_instance.process.return_value = ("processed text", 0.45)
        mock_postprocessor.return_value = mock_postprocessor_instance

        mock_controller_instance = MagicMock()
        mock_controller_class.return_value = mock_controller_instance

        # クリップボードに元のデータがある状態をシミュレート
        mock_paste.return_value = "original clipboard content"

        app = VoiceCodeApp()

        # Act
        app._stop_and_process()

        # Assert
        # copy が2回呼ばれること（1回目: 処理結果、2回目: 元の内容を復元）
        assert mock_copy.call_count == 2
        # 1回目の呼び出しは処理結果をコピー
        mock_copy.assert_any_call("processed text")
        # 2回目の呼び出しは元の内容を復元
        mock_copy.assert_any_call("original clipboard content")

    @patch("main.keyboard.Controller")
    @patch("main.pyperclip.paste")
    @patch("main.pyperclip.copy")
    @patch("main.time.sleep")
    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_stop_and_process_no_restore_when_disabled(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        mock_sleep,
        mock_copy,
        mock_paste,
        mock_controller_class,
    ):
        """クリップボード復元が無効の場合、復元されないこと。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = True
        mock_recorder_instance.is_timeout = False
        mock_audio_path = MagicMock(spec=Path)
        mock_audio_path.exists.return_value = True
        mock_recorder_instance.stop.return_value = mock_audio_path
        mock_recorder.return_value = mock_recorder_instance

        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.transcribe.return_value = ("テスト音声", 1.23)
        mock_transcriber.return_value = mock_transcriber_instance

        mock_postprocessor_instance = MagicMock()
        mock_postprocessor_instance.process.return_value = ("processed text", 0.45)
        mock_postprocessor.return_value = mock_postprocessor_instance

        mock_controller_instance = MagicMock()
        mock_controller_class.return_value = mock_controller_instance

        mock_paste.return_value = "original clipboard content"

        app = VoiceCodeApp()
        # クリップボード復元を無効にする
        app._settings.restore_clipboard = False

        # Act
        app._stop_and_process()

        # Assert
        # copy が1回のみ呼ばれること（復元なし）
        mock_copy.assert_called_once_with("processed text")
        # paste は呼ばれないこと（元の内容を取得しない）
        mock_paste.assert_not_called()

    @patch("main.HistoryManager")
    @patch("main.keyboard.Controller")
    @patch("main.pyperclip.paste")
    @patch("main.pyperclip.copy")
    @patch("main.time.sleep")
    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_stop_and_process_saves_history(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        mock_sleep,
        mock_copy,
        mock_paste,
        mock_controller_class,
        mock_history_manager_class,
    ):
        """処理完了後に履歴が保存されること。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = True
        mock_recorder_instance.is_timeout = False
        mock_audio_path = MagicMock(spec=Path)
        mock_audio_path.exists.return_value = True
        mock_recorder_instance.stop.return_value = mock_audio_path
        mock_recorder.return_value = mock_recorder_instance

        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.transcribe.return_value = ("テスト音声", 1.23)
        mock_transcriber.return_value = mock_transcriber_instance

        mock_postprocessor_instance = MagicMock()
        mock_postprocessor_instance.process.return_value = ("processed text", 0.45)
        mock_postprocessor.return_value = mock_postprocessor_instance

        mock_controller_instance = MagicMock()
        mock_controller_class.return_value = mock_controller_instance

        mock_history_manager_instance = MagicMock()
        mock_history_manager_class.return_value = mock_history_manager_instance

        mock_paste.return_value = ""

        app = VoiceCodeApp()

        # Act
        app._stop_and_process()

        # Assert
        # 履歴が保存されること
        mock_history_manager_instance.save.assert_called_once_with(
            audio_path=mock_audio_path,
            raw_transcription="テスト音声",
            processed_text="processed text",
        )

    @patch("main.HistoryManager")
    @patch("main.keyboard.Controller")
    @patch("main.pyperclip.paste")
    @patch("main.pyperclip.copy")
    @patch("main.time.sleep")
    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_stop_and_process_continues_on_history_error(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        mock_sleep,
        mock_copy,
        mock_paste,
        mock_controller_class,
        mock_history_manager_class,
    ):
        """履歴保存が失敗しても主処理は継続されること。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = True
        mock_recorder_instance.is_timeout = False
        mock_audio_path = MagicMock(spec=Path)
        mock_audio_path.exists.return_value = True
        mock_recorder_instance.stop.return_value = mock_audio_path
        mock_recorder.return_value = mock_recorder_instance

        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.transcribe.return_value = ("テスト音声", 1.23)
        mock_transcriber.return_value = mock_transcriber_instance

        mock_postprocessor_instance = MagicMock()
        mock_postprocessor_instance.process.return_value = ("processed text", 0.45)
        mock_postprocessor.return_value = mock_postprocessor_instance

        mock_controller_instance = MagicMock()
        mock_controller_class.return_value = mock_controller_instance

        # 履歴保存がNoneを返す（エラー）
        mock_history_manager_instance = MagicMock()
        mock_history_manager_instance.save.return_value = None
        mock_history_manager_class.return_value = mock_history_manager_instance

        mock_paste.return_value = ""

        app = VoiceCodeApp()

        # Act - エラーにならないこと
        app._stop_and_process()

        # Assert - 処理が完了していること
        mock_copy.assert_called()
        mock_controller_instance.tap.assert_called_once_with('v')

class TestVoiceCodeAppKeyRepeatPrevention:
    """VoiceCodeAppのキーリピート防止テスト。"""

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_key_repeat_ignored(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """キーリピート時に_toggle_recordingが1回だけ呼ばれること。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = False
        mock_recorder.return_value = mock_recorder_instance

        app = VoiceCodeApp()
        # ホットキーをF15に設定
        app._hotkey = {keyboard.Key.f15}
        app._toggle_recording = MagicMock()

        # F15キーを正規化した形でシミュレート
        f15_key = keyboard.Key.f15

        # Act - 同じキーを3回押す（キーリピートをシミュレート）
        app._on_press(f15_key)
        app._on_press(f15_key)
        app._on_press(f15_key)

        # Assert - _toggle_recordingは1回だけ呼ばれる
        app._toggle_recording.assert_called_once()

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_key_release_allows_new_press(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """キーを離してから再度押すと_toggle_recordingが再度呼ばれること。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = False
        mock_recorder.return_value = mock_recorder_instance

        app = VoiceCodeApp()
        # ホットキーをF15に設定
        app._hotkey = {keyboard.Key.f15}
        app._toggle_recording = MagicMock()

        f15_key = keyboard.Key.f15

        # Act - 押す→離す→押す
        app._on_press(f15_key)
        app._on_release(f15_key)
        app._on_press(f15_key)

        # Assert - _toggle_recordingは2回呼ばれる
        assert app._toggle_recording.call_count == 2


class TestVoiceCodeAppPushToTalk:
    """VoiceCodeAppのPush-to-Talkモードテスト。"""

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_push_to_talk_stops_on_release(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """Push-to-Talkモードで、キーを離すと録音が停止すること。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = True
        mock_recorder.return_value = mock_recorder_instance

        app = VoiceCodeApp()
        # ホットキーをF15に設定
        app._hotkey = {keyboard.Key.f15}
        app._settings._push_to_talk = True
        app._stop_and_process = MagicMock()

        # F15キーが押されている状態をシミュレート
        f15_key = keyboard.Key.f15
        app._current_keys.add(f15_key)

        # Act - キーを離す
        app._on_release(f15_key)

        # Assert - 録音停止が呼ばれる
        app._stop_and_process.assert_called_once()

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_toggle_mode_continues_on_release(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """トグルモード（デフォルト）で、キーを離しても録音が継続すること。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = True
        mock_recorder.return_value = mock_recorder_instance

        app = VoiceCodeApp()
        # ホットキーをF15に設定
        app._hotkey = {keyboard.Key.f15}
        app._settings._push_to_talk = False  # デフォルト
        app._stop_and_process = MagicMock()

        # F15キーが押されている状態をシミュレート
        f15_key = keyboard.Key.f15
        app._current_keys.add(f15_key)

        # Act - キーを離す
        app._on_release(f15_key)

        # Assert - 録音停止は呼ばれない
        app._stop_and_process.assert_not_called()

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_push_to_talk_no_stop_when_not_recording(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """Push-to-Talkモードでも、録音中でなければ停止処理は呼ばれないこと。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = False
        mock_recorder.return_value = mock_recorder_instance

        app = VoiceCodeApp()
        # ホットキーをF15に設定
        app._hotkey = {keyboard.Key.f15}
        app._settings._push_to_talk = True
        app._stop_and_process = MagicMock()

        # F15キーが押されている状態をシミュレート
        f15_key = keyboard.Key.f15
        app._current_keys.add(f15_key)

        # Act - キーを離す
        app._on_release(f15_key)

        # Assert - 録音停止は呼ばれない
        app._stop_and_process.assert_not_called()


class TestVoiceCodeAppLogSettings:
    """VoiceCodeAppの_log_settingsメソッドのテスト。"""

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_log_settings_outputs_all_settings(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        caplog,
    ):
        """_log_settingsが全ての設定を出力すること。"""
        with caplog.at_level(logging.INFO):
            app = VoiceCodeApp()
            # 設定をモックして再度ログ出力
            app._settings._hotkey = "f15"
            app._settings._max_recording_duration = 120
            app._settings._restore_clipboard = True
            caplog.clear()
            app._log_settings()

        # 設定ログが出力されていることを確認
        assert "[Settings] Hotkey: F15" in caplog.text
        assert "[Settings] Max Recording: 120s" in caplog.text
        assert "[Settings] Restore Clipboard: True" in caplog.text
        assert "[Settings] Push-to-Talk: False" in caplog.text

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_log_settings_hotkey_uppercase(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        caplog,
    ):
        """_log_settingsがホットキーを大文字で出力すること。"""
        with caplog.at_level(logging.INFO):
            app = VoiceCodeApp()
            # 設定を小文字で保存されていても大文字で出力される
            app._settings.hotkey = "ctrl+shift+r"
            caplog.clear()
            app._log_settings()

        assert "[Settings] Hotkey: CTRL+SHIFT+R" in caplog.text

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_log_settings_restore_clipboard_false(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        caplog,
    ):
        """_log_settingsがrestore_clipboard=Falseを正しく出力すること。"""
        with caplog.at_level(logging.INFO):
            app = VoiceCodeApp()
            app._settings._restore_clipboard = False
            caplog.clear()
            app._log_settings()

        assert "[Settings] Restore Clipboard: False" in caplog.text

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_log_settings_push_to_talk_true(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        caplog,
    ):
        """_log_settingsがpush_to_talk=Trueを正しく出力すること。"""
        with caplog.at_level(logging.INFO):
            app = VoiceCodeApp()
            app._settings._push_to_talk = True
            caplog.clear()
            app._log_settings()

        assert "[Settings] Push-to-Talk: True" in caplog.text


class TestVoiceCodeAppCheckTimeout:
    """VoiceCodeAppの_check_timeoutメソッドのテスト。"""

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_check_timeout_skips_when_not_recording(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """録音中でない場合、_check_timeoutはstop_and_processを呼ばないこと。

        タイムアウト後にis_recordingがFalseになった場合、_check_timeoutが
        繰り返し_stop_and_process()を呼び出すバグを防止するテスト。
        """
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = False  # 録音中でない
        mock_recorder_instance.is_timeout = True  # タイムアウトフラグが残っている
        mock_recorder.return_value = mock_recorder_instance

        app = VoiceCodeApp()
        app._processing = False

        # _stop_and_processをモック化
        app._stop_and_process = MagicMock()

        # Act
        app._check_timeout(None)

        # Assert
        # 録音中でないため、_stop_and_processは呼ばれない
        app._stop_and_process.assert_not_called()

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_check_timeout_calls_stop_when_recording_and_timeout(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """録音中かつタイムアウトの場合、_stop_and_processが呼ばれること。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = True  # 録音中
        mock_recorder_instance.is_timeout = True  # タイムアウト
        mock_recorder.return_value = mock_recorder_instance

        app = VoiceCodeApp()
        app._processing = False

        # _stop_and_processをモック化
        app._stop_and_process = MagicMock()

        # Act
        app._check_timeout(None)

        # Assert
        app._stop_and_process.assert_called_once()

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_check_timeout_skips_when_processing(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """処理中の場合、_check_timeoutはstop_and_processを呼ばないこと。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = True
        mock_recorder_instance.is_timeout = True
        mock_recorder.return_value = mock_recorder_instance

        app = VoiceCodeApp()
        app._processing = True  # 処理中

        # _stop_and_processをモック化
        app._stop_and_process = MagicMock()

        # Act
        app._check_timeout(None)

        # Assert
        app._stop_and_process.assert_not_called()

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_check_timeout_skips_when_no_timeout(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """タイムアウトしていない場合、_stop_and_processは呼ばれないこと。"""
        # Arrange
        mock_recorder_instance = MagicMock()
        mock_recorder_instance.is_recording = True
        mock_recorder_instance.is_timeout = False  # タイムアウトしていない
        mock_recorder.return_value = mock_recorder_instance

        app = VoiceCodeApp()
        app._processing = False

        # _stop_and_processをモック化
        app._stop_and_process = MagicMock()

        # Act
        app._check_timeout(None)

        # Assert
        app._stop_and_process.assert_not_called()


class TestCheckInputMonitoringPermission:
    """check_input_monitoring_permission関数のテスト。

    Note: これらのテストは autouse フィクスチャの影響を受けないよう、
    実際の関数ロジックを直接テストするのではなく、
    VoiceCodeApp._check_permissions 経由でテストする。
    """

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch("main.check_accessibility_permission", return_value=True)
    @patch("main.check_microphone_permission", return_value=True)
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_input_monitoring_permission_check_is_called(
        self,
        mock_mic_perm,
        mock_access_perm,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """入力監視権限チェックが呼び出されること。"""
        with patch("main.check_input_monitoring_permission", return_value=True) as mock_input_perm:
            app = VoiceCodeApp()
            # 初期化時に呼び出されていることを確認
            mock_input_perm.assert_called()


class TestCheckAccessibilityPermission:
    """check_accessibility_permission関数のテスト。

    Note: これらのテストは autouse フィクスチャの影響を受けないよう、
    VoiceCodeApp._check_permissions 経由でテストする。
    """

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch("main.check_input_monitoring_permission", return_value=True)
    @patch("main.check_microphone_permission", return_value=True)
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_accessibility_permission_check_is_called(
        self,
        mock_mic_perm,
        mock_input_perm,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """アクセシビリティ権限チェックが呼び出されること。"""
        with patch("main.check_accessibility_permission", return_value=True) as mock_access_perm:
            app = VoiceCodeApp()
            # 初期化時に呼び出されていることを確認
            mock_access_perm.assert_called()


class TestVoiceCodeAppCheckPermissions:
    """VoiceCodeAppの_check_permissionsメソッドのテスト。"""

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch("main.check_accessibility_permission", return_value=True)
    @patch("main.check_input_monitoring_permission", return_value=True)
    @patch("main.check_microphone_permission", return_value=True)
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_check_permissions_no_warning_when_all_granted(
        self,
        mock_mic_perm,
        mock_input_perm,
        mock_access_perm,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        caplog,
    ):
        """全権限が許可されている場合、警告が出力されないこと。"""
        with caplog.at_level(logging.WARNING):
            app = VoiceCodeApp()
            caplog.clear()
            app._check_permissions()

        assert "[Warning]" not in caplog.text

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch("main.check_accessibility_permission", return_value=True)
    @patch("main.check_input_monitoring_permission", return_value=True)
    @patch("main.check_microphone_permission", return_value=False)
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_check_permissions_warns_microphone(
        self,
        mock_mic_perm,
        mock_input_perm,
        mock_access_perm,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        caplog,
    ):
        """マイク権限がない場合、警告が出力されること。"""
        with caplog.at_level(logging.WARNING):
            app = VoiceCodeApp()
            caplog.clear()
            app._check_permissions()

        assert "Microphone permission not granted" in caplog.text

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch("main.check_accessibility_permission", return_value=True)
    @patch("main.check_input_monitoring_permission", return_value=False)
    @patch("main.check_microphone_permission", return_value=True)
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_check_permissions_warns_input_monitoring(
        self,
        mock_mic_perm,
        mock_input_perm,
        mock_access_perm,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        caplog,
    ):
        """入力監視権限がない場合、警告が出力されること。"""
        with caplog.at_level(logging.WARNING):
            app = VoiceCodeApp()
            caplog.clear()
            app._check_permissions()

        assert "Input monitoring permission not granted" in caplog.text

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch("main.check_accessibility_permission", return_value=False)
    @patch("main.check_input_monitoring_permission", return_value=True)
    @patch("main.check_microphone_permission", return_value=True)
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_check_permissions_warns_accessibility(
        self,
        mock_mic_perm,
        mock_input_perm,
        mock_access_perm,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        caplog,
    ):
        """アクセシビリティ権限がない場合、警告が出力されること。"""
        with caplog.at_level(logging.WARNING):
            app = VoiceCodeApp()
            caplog.clear()
            app._check_permissions()

        assert "Accessibility permission not granted" in caplog.text

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch("main.check_accessibility_permission", return_value=False)
    @patch("main.check_input_monitoring_permission", return_value=False)
    @patch("main.check_microphone_permission", return_value=False)
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_check_permissions_warns_all_missing(
        self,
        mock_mic_perm,
        mock_input_perm,
        mock_access_perm,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
        caplog,
    ):
        """全権限がない場合、全ての警告が出力されること。"""
        with caplog.at_level(logging.WARNING):
            app = VoiceCodeApp()
            caplog.clear()
            app._check_permissions()

        assert "Microphone permission not granted" in caplog.text
        assert "Input monitoring permission not granted" in caplog.text
        assert "Accessibility permission not granted" in caplog.text


class TestStatusItemHelper:
    """_StatusItemHelperクラスのテスト。

    バックグラウンドスレッドからメインスレッドへのUI更新委譲をテストする。
    """

    def test_init_with_app(self):
        """initWithApp_がアプリを正しく保持すること。"""
        mock_app = MagicMock()
        helper = _StatusItemHelper.alloc().initWithApp_(mock_app)

        assert helper is not None
        assert helper._app is mock_app
        assert helper._pending_icon_path is None

    def test_set_icon_stores_path(self):
        """set_iconがアイコンパスを保持すること。"""
        mock_app = MagicMock()
        helper = _StatusItemHelper.alloc().initWithApp_(mock_app)

        # performSelectorOnMainThread_ をモック
        with patch.object(helper, "performSelectorOnMainThread_withObject_waitUntilDone_"):
            helper.set_icon("/path/to/icon.png")

        assert helper._pending_icon_path == "/path/to/icon.png"

    def test_set_icon_dispatches_to_main_thread(self):
        """set_iconがメインスレッドへのディスパッチを呼び出すこと。"""
        mock_app = MagicMock()
        helper = _StatusItemHelper.alloc().initWithApp_(mock_app)

        with patch.object(helper, "performSelectorOnMainThread_withObject_waitUntilDone_") as mock_dispatch:
            helper.set_icon("/path/to/icon.png")

        mock_dispatch.assert_called_once_with("doSetIcon", None, False)

    def test_doSetIcon_updates_app_icon(self):
        """doSetIconがアプリのアイコンを更新すること。"""
        mock_app = MagicMock()
        helper = _StatusItemHelper.alloc().initWithApp_(mock_app)
        helper._pending_icon_path = "/path/to/icon.png"

        helper.doSetIcon()

        assert mock_app.icon == "/path/to/icon.png"

    def test_doSetIcon_with_none_path_does_nothing(self):
        """doSetIconがNoneパスの場合は何もしないこと。"""
        mock_app = MagicMock()
        helper = _StatusItemHelper.alloc().initWithApp_(mock_app)
        helper._pending_icon_path = None

        helper.doSetIcon()

        # アイコンは設定されない
        assert not hasattr(mock_app, "icon") or mock_app.icon != "/path/to/icon.png"

    def test_doSetIcon_with_none_app_does_not_crash(self):
        """doSetIconがNoneアプリの場合でもクラッシュしないこと。"""
        helper = _StatusItemHelper.alloc().initWithApp_(None)
        helper._pending_icon_path = "/path/to/icon.png"

        # クラッシュしないこと
        helper.doSetIcon()


class TestStatusItemHelperIntegration:
    """_StatusItemHelperとVoiceCodeAppの統合テスト。"""

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_app_initializes_status_helper(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """VoiceCodeAppが_status_helperを初期化すること。"""
        app = VoiceCodeApp()

        assert hasattr(app, "_status_helper")
        assert app._status_helper is not None
        assert isinstance(app._status_helper, _StatusItemHelper)

    @patch("main.subprocess.Popen")
    @patch("main.rumps.Timer")
    @patch("main.keyboard.Listener")
    @patch("main.Transcriber")
    @patch("main.PostProcessor")
    @patch("main.AudioRecorder")
    @patch("main.load_dotenv")
    @patch.dict("os.environ", VOICECODE_APP_PATCHES)
    def test_start_recording_uses_status_helper(
        self,
        mock_load_dotenv,
        mock_recorder,
        mock_postprocessor,
        mock_transcriber,
        mock_listener,
        mock_timer,
        mock_popen,
    ):
        """_start_recordingがstatus_helperを使用すること。"""
        mock_recorder_instance = MagicMock()
        mock_recorder.return_value = mock_recorder_instance

        app = VoiceCodeApp()

        with patch.object(app._status_helper, "set_icon") as mock_set_icon:
            app._start_recording()

        mock_set_icon.assert_called_once()
        # 呼び出された引数がRECORDINGアイコンであること
        call_args = mock_set_icon.call_args[0][0]
        assert "icon_recording.png" in call_args


class TestParseArgs:
    """_parse_args関数のテスト。"""

    def test_no_arguments(self):
        """引数なしの場合、daemon=Falseであること。"""
        with patch("sys.argv", ["main.py"]):
            args = _parse_args()
        assert args.daemon is False

    def test_daemon_short_flag(self):
        """短いフラグ -d でdaemon=Trueになること。"""
        with patch("sys.argv", ["main.py", "-d"]):
            args = _parse_args()
        assert args.daemon is True

    def test_daemon_long_flag(self):
        """長いフラグ --daemon でdaemon=Trueになること。"""
        with patch("sys.argv", ["main.py", "--daemon"]):
            args = _parse_args()
        assert args.daemon is True

    def test_help_flag_exits(self):
        """-h フラグでSystemExitが発生すること。"""
        with patch("sys.argv", ["main.py", "-h"]):
            with pytest.raises(SystemExit) as exc_info:
                _parse_args()
            # argparseは正常終了で0を返す
            assert exc_info.value.code == 0

    def test_unknown_argument_ignored(self):
        """不明な引数は無視されること（parse_known_argsを使用）。"""
        with patch("sys.argv", ["main.py", "--unknown"]):
            # parse_known_args() を使用しているため、エラーにならない
            args = _parse_args()
            assert args.daemon is False

    def test_psn_argument_ignored(self):
        """macOS Finderからの -psn 引数が無視されること。"""
        # Finderからの起動時に付与される引数をシミュレート
        with patch("sys.argv", ["VoiceCode", "-psn_0_12345678"]):
            args = _parse_args()
            assert args.daemon is False

    def test_psn_with_daemon_flag(self):
        """-psn 引数と -d フラグが混在しても正しく処理されること。"""
        with patch("sys.argv", ["VoiceCode", "-psn_0_12345678", "-d"]):
            args = _parse_args()
            assert args.daemon is True

    def test_daemon_help_mentions_launchctl(self, capsys):
        """daemonオプションのヘルプにlaunchctl推奨の警告が含まれること。"""
        import io
        import sys as real_sys

        with patch("sys.argv", ["main.py", "-h"]):
            with pytest.raises(SystemExit):
                _parse_args()

        captured = capsys.readouterr()
        assert "launchctl" in captured.out


class TestDaemonize:
    """_daemonize関数のテスト。

    注意: _daemonize()は実際にsys.stdin/stdout/stderrを閉じるため、
    すべてのテストでこれらを適切にモックする必要がある。
    os._exit()をモックしないと実際にプロセスが終了してしまうため、
    親プロセスとして終了するケースでは必ずモックする。
    """

    @patch("main.logging.getLogger")
    @patch("builtins.open")
    @patch("os.umask")
    @patch("os._exit")
    @patch("os.fork")
    @patch("os.setsid")
    def test_first_fork_parent_exits(self, mock_setsid, mock_fork, mock_exit, mock_umask, mock_open, mock_get_logger):
        """最初のforkで親プロセスがos._exit(0)で終了すること。"""
        # 最初のforkで親（pid > 0）
        mock_fork.return_value = 100

        # os._exit()をモック（呼ばれたら例外で停止）
        mock_exit.side_effect = SystemExit(0)

        with pytest.raises(SystemExit):
            _daemonize()

        mock_exit.assert_called_once_with(0)
        mock_fork.assert_called_once()
        mock_setsid.assert_not_called()

    @patch("os.fork")
    @patch("os.setsid")
    def test_first_fork_error(self, mock_setsid, mock_fork):
        """最初のforkが失敗した場合、sys.exit(1)でエラー終了すること。"""
        mock_fork.side_effect = OSError("fork failed")

        with pytest.raises(SystemExit) as exc_info:
            _daemonize()

        assert exc_info.value.code == 1
        mock_setsid.assert_not_called()

    @patch("main.logging.getLogger")
    @patch("builtins.open")
    @patch("os._exit")
    @patch("os.umask")
    @patch("os.fork")
    @patch("os.setsid")
    def test_second_fork_parent_exits(self, mock_setsid, mock_fork, mock_umask, mock_exit, mock_open, mock_get_logger):
        """2回目のforkで親プロセスがos._exit(0)で終了すること。"""
        # 最初のfork: 子（pid == 0）、2回目のfork: 親（pid > 0）
        mock_fork.side_effect = [0, 100]

        # os._exit()をモック（呼ばれたら例外で停止）
        mock_exit.side_effect = SystemExit(0)

        with pytest.raises(SystemExit):
            _daemonize()

        mock_exit.assert_called_once_with(0)
        assert mock_fork.call_count == 2
        mock_setsid.assert_called_once()
        mock_umask.assert_called_once_with(0o077)  # 所有者のみ読み書き可能

    @patch("main.logging.getLogger")
    @patch("builtins.open")
    @patch("os.umask")
    @patch("os.fork")
    @patch("os.setsid")
    def test_second_fork_error(self, mock_setsid, mock_fork, mock_umask, mock_open, mock_get_logger):
        """2回目のforkが失敗した場合、sys.exit(1)でエラー終了すること。"""
        mock_fork.side_effect = [0, OSError("fork failed")]

        with pytest.raises(SystemExit) as exc_info:
            _daemonize()

        assert exc_info.value.code == 1
        mock_setsid.assert_called_once()

    @patch("main.logging.getLogger")
    @patch("os.close")
    @patch("os.fdopen")
    @patch("os.dup2")
    @patch("os.open")
    @patch("os.umask")
    @patch("os.fork")
    @patch("os.setsid")
    def test_successful_daemonization(
        self, mock_setsid, mock_fork, mock_umask, mock_os_open, mock_dup2, mock_fdopen, mock_close, mock_get_logger
    ):
        """デーモン化が成功した場合、標準入出力がリダイレクトされること。"""
        # 両方のforkで子プロセス（pid == 0）
        mock_fork.side_effect = [0, 0]
        # os.open() は devnull_fd=3, log_fd=4 を返す
        mock_os_open.side_effect = [3, 4]
        mock_file = MagicMock()
        mock_file.name = "<stderr>"
        mock_fdopen.return_value = mock_file

        # ロガーのモック
        mock_logger = MagicMock()
        mock_handler = MagicMock(spec=logging.StreamHandler)
        mock_handler.stream = MagicMock()
        mock_handler.stream.name = "<stderr>"
        mock_logger.handlers = [mock_handler]
        mock_get_logger.return_value = mock_logger

        _daemonize()

        # forkが2回呼ばれること
        assert mock_fork.call_count == 2
        # setsidが呼ばれること
        mock_setsid.assert_called_once()
        # umaskが呼ばれること（所有者のみ読み書き可能）
        mock_umask.assert_called_once_with(0o077)
        # os.open() が2回呼ばれること（/dev/null と ログファイル）
        assert mock_os_open.call_count == 2
        # os.dup2() が3回呼ばれること（stdin, stdout, stderr）
        assert mock_dup2.call_count == 3
        mock_dup2.assert_any_call(3, 0)  # devnull -> stdin
        mock_dup2.assert_any_call(4, 1)  # log -> stdout
        mock_dup2.assert_any_call(4, 2)  # log -> stderr
        # os.fdopen() が3回呼ばれること（stdin, stdout, stderr）
        assert mock_fdopen.call_count == 3
        # os.close() が2回呼ばれること（元のdevnull_fd, log_fd）
        assert mock_close.call_count == 2
        mock_close.assert_any_call(3)  # devnull_fd
        mock_close.assert_any_call(4)  # log_fd
        # コンソールハンドラが削除されること
        mock_logger.removeHandler.assert_called()

    @patch("main.logging.getLogger")
    @patch("os.close")
    @patch("os.fdopen")
    @patch("os.dup2")
    @patch("os.open")
    @patch("os.umask")
    @patch("os.fork")
    @patch("os.setsid")
    def test_daemonization_removes_console_handler(
        self, mock_setsid, mock_fork, mock_umask, mock_os_open, mock_dup2, mock_fdopen, mock_close, mock_get_logger
    ):
        """デーモン化時にstderrに接続されたコンソールハンドラが削除されること。"""
        mock_fork.side_effect = [0, 0]
        # os.open() は devnull_fd=3, log_fd=4 を返す
        mock_os_open.side_effect = [3, 4]
        mock_file = MagicMock()
        mock_fdopen.return_value = mock_file

        # stderrに接続されたStreamHandlerをモック
        mock_logger = MagicMock()
        mock_stream_handler = MagicMock(spec=logging.StreamHandler)
        mock_stream_handler.stream = MagicMock()
        mock_stream_handler.stream.name = "<stderr>"
        # FileHandlerはStreamHandlerではないので、isinstance()チェックで弾かれる
        # specを使わずMagicMockを作成し、StreamHandlerの型チェックに失敗させる
        mock_file_handler = MagicMock()
        mock_logger.handlers = [mock_stream_handler, mock_file_handler]
        mock_get_logger.return_value = mock_logger

        _daemonize()

        # stderrハンドラのみが削除されること
        mock_logger.removeHandler.assert_called_once_with(mock_stream_handler)


class TestMainFunction:
    """main関数のテスト。"""

    @patch("main.VoiceCodeApp")
    @patch("main._daemonize")
    @patch("main._parse_args")
    def test_main_without_daemon(self, mock_parse_args, mock_daemonize, mock_app_class):
        """daemon=Falseの場合、_daemonizeが呼ばれないこと。"""
        from main import main

        mock_args = MagicMock()
        mock_args.daemon = False
        mock_parse_args.return_value = mock_args

        mock_app = MagicMock()
        mock_app_class.return_value = mock_app

        with patch("main.check_microphone_permission", return_value=True), \
             patch("main.check_input_monitoring_permission", return_value=True), \
             patch("main.check_accessibility_permission", return_value=True):
            main()

        mock_daemonize.assert_not_called()
        mock_app_class.assert_called_once()
        mock_app.run.assert_called_once()

    @patch("main.VoiceCodeApp")
    @patch("main._daemonize")
    @patch("main._parse_args")
    def test_main_with_daemon(self, mock_parse_args, mock_daemonize, mock_app_class):
        """daemon=Trueの場合、_daemonizeが呼ばれること。"""
        from main import main

        mock_args = MagicMock()
        mock_args.daemon = True
        mock_parse_args.return_value = mock_args

        mock_app = MagicMock()
        mock_app_class.return_value = mock_app

        with patch("main.check_microphone_permission", return_value=True), \
             patch("main.check_input_monitoring_permission", return_value=True), \
             patch("main.check_accessibility_permission", return_value=True):
            main()

        mock_daemonize.assert_called_once()
        mock_app_class.assert_called_once()
        mock_app.run.assert_called_once()
