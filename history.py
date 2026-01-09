"""履歴保存モジュール。

音声ファイルと文字起こし結果を ~/.voicecode/history/ に保存する。
"""

import json
import logging
import shutil
import wave
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HistoryEntry(BaseModel):
    """履歴エントリのデータモデル。

    Attributes:
        timestamp: 記録日時（ISO形式）
        raw_transcription: 生の文字起こしテキスト
        processed_text: LLM処理後のテキスト
        audio_file: 音声ファイル名
        duration_sec: 音声の長さ（秒）
    """

    timestamp: str
    raw_transcription: str
    processed_text: str
    audio_file: str
    duration_sec: float


def _get_audio_duration(audio_path: Path) -> float:
    """WAVファイルの長さを秒単位で取得する。

    Args:
        audio_path: WAVファイルのパス

    Returns:
        音声の長さ（秒）。取得に失敗した場合は0.0。
    """
    try:
        with wave.open(str(audio_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return round(frames / rate, 1)
    except Exception as e:
        logger.warning(f"Failed to get audio duration: {e}")
    return 0.0


class HistoryManager:
    """履歴を管理するクラス。

    音声ファイルとメタデータを ~/.voicecode/history/ に保存する。
    """

    DEFAULT_HISTORY_DIR = Path.home() / ".voicecode" / "history"

    def __init__(self, history_dir: Path | None = None):
        """HistoryManagerを初期化する。

        Args:
            history_dir: 履歴ディレクトリのパス。Noneの場合はデフォルトを使用。
        """
        self._history_dir = history_dir or self.DEFAULT_HISTORY_DIR

    def _ensure_directory(self) -> None:
        """履歴ディレクトリが存在することを確認し、なければ作成する。"""
        self._history_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, timestamp: datetime) -> str:
        """タイムスタンプからファイル名を生成する。

        Args:
            timestamp: 記録日時

        Returns:
            ファイル名（拡張子なし）。例: "2025-01-09_153000"
        """
        return timestamp.strftime("%Y-%m-%d_%H%M%S")

    def save(
        self,
        audio_path: Path,
        raw_transcription: str,
        processed_text: str,
    ) -> Path | None:
        """履歴を保存する。

        Args:
            audio_path: 一時音声ファイルのパス
            raw_transcription: 生の文字起こしテキスト
            processed_text: LLM処理後のテキスト

        Returns:
            保存されたJSONファイルのパス。失敗した場合はNone。
        """
        try:
            self._ensure_directory()

            timestamp = datetime.now()
            base_filename = self._generate_filename(timestamp)

            # 音声ファイルをコピー
            audio_filename = f"{base_filename}.wav"
            dest_audio_path = self._history_dir / audio_filename
            shutil.copy2(audio_path, dest_audio_path)
            logger.info(f"[History] Audio saved: {dest_audio_path}")

            # 音声の長さを取得
            duration_sec = _get_audio_duration(audio_path)

            # メタデータを作成
            entry = HistoryEntry(
                timestamp=timestamp.isoformat(timespec="seconds"),
                raw_transcription=raw_transcription,
                processed_text=processed_text,
                audio_file=audio_filename,
                duration_sec=duration_sec,
            )

            # JSONファイルを保存
            json_filename = f"{base_filename}.json"
            json_path = self._history_dir / json_filename

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(entry.model_dump(), f, indent=2, ensure_ascii=False)

            logger.info(f"[History] Metadata saved: {json_path}")
            print(f"[History] Saved to: {self._history_dir}")

            return json_path

        except Exception as e:
            logger.error(f"[History] Failed to save: {e}")
            print(f"[Warning] Failed to save history: {e}")
            return None
