#!/usr/bin/env python3
"""音声入力ツールのエントリポイント。

設定されたホットキー（デフォルト: F15）で録音開始/停止をトグル。
録音停止後、文字起こし→LLM後処理→クリップボードにコピー→貼り付けを実行。
メニューバーアプリとして動作し、状態をアイコンで表示する。
"""

import os
import subprocess
import time
from pathlib import Path

import pyperclip
import rumps
from dotenv import load_dotenv
from pynput import keyboard

from postprocessor import PostProcessor
from recorder import AudioRecorder
from settings import Settings
from transcriber import Transcriber


def _parse_hotkey(hotkey_str: str) -> set[keyboard.Key | keyboard.KeyCode]:
    """環境変数文字列をパースしてキーセットに変換する。

    Args:
        hotkey_str: ホットキー文字列（例: "f15", "ctrl+shift+r"）

    Returns:
        pynputキーオブジェクトのセット

    Raises:
        ValueError: 無効なキー文字列の場合
    """
    modifier_map: dict[str, keyboard.Key] = {
        "ctrl": keyboard.Key.ctrl,
        "shift": keyboard.Key.shift,
        "alt": keyboard.Key.alt,
        "cmd": keyboard.Key.cmd,
    }

    keys: set[keyboard.Key | keyboard.KeyCode] = set()
    parts = hotkey_str.lower().strip().split("+")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 修飾キーをチェック
        if part in modifier_map:
            keys.add(modifier_map[part])
            continue

        # ファンクションキーをチェック (f1-f20)
        if part.startswith("f") and part[1:].isdigit():
            fn_num = int(part[1:])
            if 1 <= fn_num <= 20:
                fn_key = getattr(keyboard.Key, part, None)
                if fn_key:
                    keys.add(fn_key)
                    continue
            raise ValueError(f"Invalid function key: {part}")

        # 単一文字キー
        if len(part) == 1:
            keys.add(keyboard.KeyCode.from_char(part))
            continue

        raise ValueError(f"Unknown key: {part}")

    if not keys:
        raise ValueError(f"No valid keys found in: {hotkey_str}")

    return keys


def _format_hotkey(keys: set[keyboard.Key | keyboard.KeyCode]) -> str:
    """キーセットを人間可読な文字列に変換する。

    Args:
        keys: pynputキーオブジェクトのセット

    Returns:
        人間可読なホットキー文字列（例: "Ctrl+Shift+R"）
    """
    key_names: list[str] = []

    # 修飾キーを先に処理（順序を一定にするため）
    modifier_order = [
        (keyboard.Key.ctrl, "Ctrl"),
        (keyboard.Key.shift, "Shift"),
        (keyboard.Key.alt, "Alt"),
        (keyboard.Key.cmd, "Cmd"),
    ]

    for key_obj, name in modifier_order:
        if key_obj in keys:
            key_names.append(name)

    # その他のキー
    for key in keys:
        if isinstance(key, keyboard.Key):
            if key in (keyboard.Key.ctrl, keyboard.Key.shift, keyboard.Key.alt, keyboard.Key.cmd):
                continue  # 既に処理済み
            # ファンクションキーなど
            key_names.append(key.name.upper())
        elif isinstance(key, keyboard.KeyCode):
            if key.char:
                key_names.append(key.char.upper())

    return "+".join(key_names)


class VoiceCodeApp(rumps.App):
    """音声入力ツールのメインクラス（メニューバーアプリ）。"""

    # 状態アイコン定数
    ICON_IDLE = "■"
    ICON_RECORDING = "●"
    ICON_PROCESSING = "↻"

    # 効果音定数
    SOUND_START = "/System/Library/Sounds/Tink.aiff"
    SOUND_STOP = "/System/Library/Sounds/Pop.aiff"
    SOUND_SUCCESS = "/System/Library/Sounds/Glass.aiff"
    SOUND_ERROR = "/System/Library/Sounds/Basso.aiff"

    def __init__(self):
        """VoiceCodeAppを初期化する。"""
        super().__init__("VoiceCode", icon=None, title=self.ICON_IDLE)
        load_dotenv()

        # 設定を読み込み（settings.json優先、なければ.envのHOTKEY）
        self._settings = Settings()
        env_hotkey = os.getenv("HOTKEY", "f15")
        # settings.jsonが存在しない場合は.envの値を使用
        if not (Path.home() / ".voicecode" / "settings.json").exists():
            self._settings.hotkey = env_hotkey
            self._settings.save()

        self._hotkey = _parse_hotkey(self._settings.hotkey)
        self._recorder = AudioRecorder()
        self._transcriber = Transcriber()
        self._postprocessor = PostProcessor()

        self._current_keys: set = set()
        self._processing = False

        # レコードモード用の変数
        self._recording_hotkey = False
        self._recorded_key: str | None = None

        # メニュー項目を初期化
        self._init_menu()

        # キーボードリスナーを別スレッドで起動
        self._start_keyboard_listener()

    def _play_sound(self, sound_path: str) -> None:
        """効果音を非同期再生する。

        Args:
            sound_path: 再生する効果音ファイルのパス
        """
        subprocess.Popen(
            ["afplay", sound_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _start_keyboard_listener(self) -> None:
        """キーボードリスナーを起動する。"""
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        # Listener.start() は自身をデーモンスレッドとして起動する
        self._listener.start()

        # タイムアウトチェック用タイマーを起動
        self._timeout_timer = rumps.Timer(self._check_timeout, 0.5)
        self._timeout_timer.start()

        hotkey_display = self._format_hotkey_display()
        print(f"[Info] Keyboard listener started. Hotkey: {hotkey_display}")

    def _init_menu(self) -> None:
        """メニュー項目を初期化する。"""
        self._hotkey_item = rumps.MenuItem("ホットキー設定...", callback=self._on_hotkey_settings)
        self._restore_item = rumps.MenuItem(
            "クリップボードを復元",
            callback=self._on_toggle_restore_clipboard,
        )
        self._restore_item.state = 1 if self._settings.restore_clipboard else 0

        self.menu = [
            self._hotkey_item,
            self._restore_item,
            rumps.separator,
        ]

    def _on_hotkey_settings(self, _) -> None:
        """ホットキー設定ダイアログを表示する。"""
        current_hotkey = self._settings.hotkey
        window = rumps.Window(
            message=f"現在のホットキー: {current_hotkey.upper()}\n\n"
                    "新しいホットキーを入力してください\n"
                    "(例: f15, ctrl+shift+r)",
            title="ホットキー設定",
            default_text=current_hotkey,
            ok="保存",
            cancel="キャンセル",
        )
        window.add_button("記録")

        response = window.run()

        # response.clicked: 1=保存, 0=キャンセル, 2=記録
        if response.clicked == 1:
            # 保存ボタン
            new_hotkey = response.text.strip()
            if new_hotkey:
                self._update_hotkey(new_hotkey)
        elif response.clicked == 2:
            # 記録ボタン
            self._start_record_mode()

    def _start_record_mode(self) -> None:
        """レコードモードを開始する。"""
        self._recording_hotkey = True
        self._recorded_key = None

        # 一時的なキーボードリスナーを起動
        def on_press(key):
            if self._recording_hotkey:
                self._recorded_key = self._key_to_string(key)
                self._recording_hotkey = False
                return False  # リスナーを停止

        record_listener = keyboard.Listener(on_press=on_press)
        record_listener.start()

        # アラートを表示
        rumps.alert(
            title="ホットキー記録",
            message="キーを押してください...\n\n"
                    "ファンクションキー（F1-F20）または\n"
                    "修飾キー+文字キーの組み合わせを押してください。",
        )

        record_listener.stop()

        if self._recorded_key:
            self._update_hotkey(self._recorded_key)
            rumps.alert(
                title="ホットキー設定完了",
                message=f"ホットキーを {self._recorded_key.upper()} に設定しました。",
            )

    def _key_to_string(self, key: keyboard.Key | keyboard.KeyCode) -> str:
        """キーオブジェクトを文字列に変換する。"""
        if isinstance(key, keyboard.Key):
            return key.name.lower()
        elif isinstance(key, keyboard.KeyCode):
            if key.char:
                return key.char.lower()
            elif key.vk:
                # ファンクションキーなどの仮想キーコード
                return f"vk{key.vk}"
        return ""

    def _update_hotkey(self, new_hotkey: str) -> None:
        """ホットキーを更新する。"""
        try:
            new_keys = _parse_hotkey(new_hotkey)
            self._hotkey = new_keys
            self._settings.hotkey = new_hotkey
            self._settings.save()
            print(f"[Info] Hotkey updated to: {new_hotkey.upper()}")
        except ValueError as e:
            rumps.alert(
                title="エラー",
                message=f"無効なホットキーです: {e}",
            )

    def _on_toggle_restore_clipboard(self, sender: rumps.MenuItem) -> None:
        """クリップボード復元設定をトグルする。"""
        new_state = not self._settings.restore_clipboard
        self._settings.restore_clipboard = new_state
        self._settings.save()
        sender.state = 1 if new_state else 0
        status = "有効" if new_state else "無効"
        print(f"[Info] Restore clipboard: {status}")

    def _check_timeout(self, _) -> None:
        """録音タイムアウトをチェックする。"""
        if self._recorder.is_timeout and not self._processing:
            print("\n[Timeout] Max recording duration reached")
            self._stop_and_process()

    @rumps.clicked("終了")
    def quit_app(self, _):
        """アプリを終了する。"""
        rumps.quit_application()

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """キー押下時のコールバック。"""
        normalized_key = self._normalize_key(key)
        self._current_keys.add(normalized_key)

        if self._check_hotkey():
            self._toggle_recording()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """キー解放時のコールバック。"""
        normalized_key = self._normalize_key(key)
        self._current_keys.discard(normalized_key)

    def _normalize_key(self, key: keyboard.Key | keyboard.KeyCode) -> keyboard.Key | keyboard.KeyCode:
        """キーを正規化する。"""
        if isinstance(key, keyboard.KeyCode) and key.char:
            return keyboard.KeyCode.from_char(key.char.lower())
        return key

    def _check_hotkey(self) -> bool:
        """ホットキーが押されているかチェックする。"""
        return self._hotkey <= self._current_keys

    def _format_hotkey_display(self) -> str:
        """ホットキーを表示用に整形する。"""
        return _format_hotkey(self._hotkey)

    def _toggle_recording(self) -> None:
        """録音のトグル処理。"""
        if self._processing:
            return

        if self._recorder.is_recording:
            self._stop_and_process()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        """録音を開始する。"""
        try:
            self._recorder.start()
            self.title = self.ICON_RECORDING
            self._play_sound(self.SOUND_START)
            hotkey_display = self._format_hotkey_display()
            print("\n" + "=" * 50)
            print(f"Recording... Press {hotkey_display} to stop")
            print("=" * 50)
        except Exception as e:
            print(f"[Error] Failed to start recording: {e}")
            self.title = self.ICON_IDLE
            self._play_sound(self.SOUND_ERROR)

    def _stop_and_process(self) -> None:
        """録音を停止し、処理を実行する。"""
        self._processing = True
        self.title = self.ICON_PROCESSING
        self._play_sound(self.SOUND_STOP)
        audio_path: Path | None = None
        original_clipboard: str | None = None

        try:
            audio_path = self._recorder.stop()
            print("\n" + "-" * 50)
            print("Processing...")
            print("-" * 50)

            # 文字起こし
            transcribed_text = self._transcriber.transcribe(audio_path)

            if not transcribed_text.strip():
                print("[Warning] No speech detected")
                self.title = self.ICON_IDLE
                self._play_sound(self.SOUND_ERROR)
                return

            # LLM後処理
            processed_text = self._postprocessor.process(transcribed_text)

            # クリップボード復元が有効な場合、元の内容を保存
            if self._settings.restore_clipboard:
                try:
                    original_clipboard = pyperclip.paste()
                except Exception:
                    pass

            # クリップボードにコピー
            pyperclip.copy(processed_text)
            print(f"\n[Clipboard] Copied: {processed_text}")

            # 少し待機してから貼り付け
            time.sleep(0.2)

            # Cmd+V で貼り付け（pynputを使用）
            controller = keyboard.Controller()
            with controller.pressed(keyboard.Key.cmd):
                controller.tap('v')
            print("[Paste] Done!")

            self.title = self.ICON_IDLE
            self._play_sound(self.SOUND_SUCCESS)

            hotkey_display = self._format_hotkey_display()
            print("\n" + "=" * 50)
            print(f"Ready. Press {hotkey_display} to start recording")
            print("=" * 50)

        except Exception as e:
            print(f"[Error] Processing failed: {e}")
            self.title = self.ICON_IDLE
            self._play_sound(self.SOUND_ERROR)

        finally:
            # クリップボードを復元
            if original_clipboard is not None:
                try:
                    time.sleep(0.1)
                    pyperclip.copy(original_clipboard)
                    print("[Clipboard] Restored original content")
                except Exception:
                    pass

            # 一時ファイルを削除
            if audio_path and audio_path.exists():
                try:
                    audio_path.unlink()
                    print(f"[Cleanup] Deleted: {audio_path}")
                except Exception as e:
                    print(f"[Warning] Failed to delete temp file: {e}")

            self._processing = False


def main() -> None:
    """エントリポイント。"""
    app = VoiceCodeApp()
    app.run()


if __name__ == "__main__":
    main()
