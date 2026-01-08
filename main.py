#!/usr/bin/env python3
"""音声入力ツールのエントリポイント。

設定されたホットキー（デフォルト: F13）で録音開始/停止をトグル。
録音停止後、文字起こし→LLM後処理→クリップボードにコピー→貼り付けを実行。
"""

import os
import sys
import time
from pathlib import Path

import pyautogui
import pyperclip
from dotenv import load_dotenv
from pynput import keyboard

from postprocessor import PostProcessor
from recorder import AudioRecorder
from transcriber import Transcriber


def _parse_hotkey(hotkey_str: str) -> set[keyboard.Key | keyboard.KeyCode]:
    """環境変数文字列をパースしてキーセットに変換する。

    Args:
        hotkey_str: ホットキー文字列（例: "f13", "ctrl+shift+r"）

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


class VoiceInputTool:
    """音声入力ツールのメインクラス。"""

    def __init__(self):
        """VoiceInputToolを初期化する。"""
        load_dotenv()

        self._hotkey = _parse_hotkey(os.getenv("HOTKEY", "f13"))
        self._recorder = AudioRecorder()
        self._transcriber = Transcriber()
        self._postprocessor = PostProcessor()

        self._current_keys: set = set()
        self._processing = False

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
            hotkey_display = self._format_hotkey_display()
            print("\n" + "=" * 50)
            print(f"Recording... Press {hotkey_display} to stop")
            print("=" * 50)
        except Exception as e:
            print(f"[Error] Failed to start recording: {e}")

    def _stop_and_process(self) -> None:
        """録音を停止し、処理を実行する。"""
        self._processing = True
        audio_path: Path | None = None

        try:
            audio_path = self._recorder.stop()
            print("\n" + "-" * 50)
            print("Processing...")
            print("-" * 50)

            # 文字起こし
            transcribed_text = self._transcriber.transcribe(audio_path)

            if not transcribed_text.strip():
                print("[Warning] No speech detected")
                return

            # LLM後処理
            processed_text = self._postprocessor.process(transcribed_text)

            # クリップボードにコピー
            pyperclip.copy(processed_text)
            print(f"\n[Clipboard] Copied: {processed_text}")

            # 少し待機してから貼り付け
            time.sleep(0.2)

            # Cmd+V で貼り付け
            pyautogui.hotkey("command", "v")
            print("[Paste] Done!")

            hotkey_display = self._format_hotkey_display()
            print("\n" + "=" * 50)
            print(f"Ready. Press {hotkey_display} to start recording")
            print("=" * 50)

        except Exception as e:
            print(f"[Error] Processing failed: {e}")

        finally:
            # 一時ファイルを削除
            if audio_path and audio_path.exists():
                try:
                    audio_path.unlink()
                    print(f"[Cleanup] Deleted: {audio_path}")
                except Exception as e:
                    print(f"[Warning] Failed to delete temp file: {e}")

            self._processing = False

    def run(self) -> None:
        """ツールを実行する。"""
        hotkey_display = self._format_hotkey_display()
        print("\n" + "=" * 50)
        print("Voice Input Tool")
        print("=" * 50)
        print(f"Hotkey: {hotkey_display} (toggle recording)")
        print("Press Ctrl+C to exit")
        print("=" * 50 + "\n")

        with keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        ) as listener:
            try:
                listener.join()
            except KeyboardInterrupt:
                print("\n\nExiting...")


def main() -> None:
    """エントリポイント。"""
    tool = VoiceInputTool()
    tool.run()


if __name__ == "__main__":
    main()
