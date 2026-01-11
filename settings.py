"""設定管理モジュール。

~/.voicecode/settings.json に設定を保存する。
"""

import json
from pathlib import Path
from typing import Any


class Settings:
    """VoiceCode の設定を管理するクラス。

    設定ファイルは ~/.voicecode/settings.json に保存される。
    """

    # デフォルト設定
    DEFAULT_HOTKEY = "f15"
    DEFAULT_RESTORE_CLIPBOARD = True
    DEFAULT_MAX_RECORDING_DURATION = 120
    DEFAULT_PUSH_TO_TALK = False

    # 最大録音時間の範囲制限
    MIN_RECORDING_DURATION = 10
    MAX_RECORDING_DURATION = 300

    def __init__(self, config_dir: Path | None = None):
        """Settings を初期化する。

        Args:
            config_dir: 設定ディレクトリのパス。None の場合は ~/.voicecode を使用。
        """
        if config_dir is None:
            self._config_dir = Path.home() / ".voicecode"
        else:
            self._config_dir = config_dir
        self._config_file = self._config_dir / "settings.json"

        self._hotkey: str = self.DEFAULT_HOTKEY
        self._restore_clipboard: bool = self.DEFAULT_RESTORE_CLIPBOARD
        self._max_recording_duration: int = self.DEFAULT_MAX_RECORDING_DURATION
        self._push_to_talk: bool = self.DEFAULT_PUSH_TO_TALK

        self.load()

    @property
    def hotkey(self) -> str:
        """ホットキー設定を取得する。"""
        return self._hotkey

    @hotkey.setter
    def hotkey(self, value: str) -> None:
        """ホットキー設定を更新する。"""
        self._hotkey = value.lower().strip()

    @property
    def restore_clipboard(self) -> bool:
        """クリップボード復元設定を取得する。"""
        return self._restore_clipboard

    @restore_clipboard.setter
    def restore_clipboard(self, value: bool) -> None:
        """クリップボード復元設定を更新する。"""
        self._restore_clipboard = value

    @property
    def max_recording_duration(self) -> int:
        """最大録音時間（秒）を取得する。"""
        return self._max_recording_duration

    @max_recording_duration.setter
    def max_recording_duration(self, value: int) -> None:
        """最大録音時間（秒）を更新する。

        値は MIN_RECORDING_DURATION から MAX_RECORDING_DURATION の範囲に制限される。
        """
        self._max_recording_duration = max(
            self.MIN_RECORDING_DURATION,
            min(value, self.MAX_RECORDING_DURATION)
        )

    @property
    def push_to_talk(self) -> bool:
        """Push-to-Talk モード設定を取得する。"""
        return self._push_to_talk

    @push_to_talk.setter
    def push_to_talk(self, value: bool) -> None:
        """Push-to-Talk モード設定を更新する。"""
        self._push_to_talk = value

    def load(self) -> None:
        """設定ファイルから設定を読み込む。

        ファイルが存在しない場合はデフォルト値を使用。
        """
        if not self._config_file.exists():
            return

        try:
            with open(self._config_file, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)

            if "hotkey" in data and isinstance(data["hotkey"], str):
                self._hotkey = data["hotkey"].lower().strip()

            if "restore_clipboard" in data and isinstance(data["restore_clipboard"], bool):
                self._restore_clipboard = data["restore_clipboard"]

            if "max_recording_duration" in data and isinstance(data["max_recording_duration"], int):
                self.max_recording_duration = data["max_recording_duration"]

            if "push_to_talk" in data and isinstance(data["push_to_talk"], bool):
                self._push_to_talk = data["push_to_talk"]

        except (json.JSONDecodeError, OSError) as e:
            print(f"[Warning] Failed to load settings: {e}")

    def save(self) -> None:
        """設定をファイルに保存する。

        ディレクトリが存在しない場合は自動作成する。
        """
        # ディレクトリを自動作成
        self._config_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "hotkey": self._hotkey,
            "restore_clipboard": self._restore_clipboard,
            "max_recording_duration": self._max_recording_duration,
            "push_to_talk": self._push_to_talk,
        }

        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except OSError as e:
            print(f"[Error] Failed to save settings: {e}")

    def to_dict(self) -> dict[str, Any]:
        """設定を辞書形式で取得する。"""
        return {
            "hotkey": self._hotkey,
            "restore_clipboard": self._restore_clipboard,
            "max_recording_duration": self._max_recording_duration,
            "push_to_talk": self._push_to_talk,
        }
