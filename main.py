#!/usr/bin/env python3
"""音声入力ツールのエントリポイント。

Ctrl+Shift+R で録音開始/停止をトグル。
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


class VoiceInputTool:
    """音声入力ツールのメインクラス。"""

    HOTKEY = {keyboard.Key.ctrl, keyboard.Key.shift, keyboard.KeyCode.from_char("r")}

    def __init__(self):
        """VoiceInputToolを初期化する。"""
        load_dotenv()

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
        return self.HOTKEY <= self._current_keys

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
            print("\n" + "=" * 50)
            print("Recording... Press Ctrl+Shift+R to stop")
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

            print("\n" + "=" * 50)
            print("Ready. Press Ctrl+Shift+R to start recording")
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
        print("\n" + "=" * 50)
        print("Voice Input Tool")
        print("=" * 50)
        print("Hotkey: Ctrl+Shift+R (toggle recording)")
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
