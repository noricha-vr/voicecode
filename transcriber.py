"""音声文字起こしモジュール。

Groq APIのWhisperモデルを使用して音声を文字起こしする。
"""

import logging
import os
import time
from pathlib import Path

from groq import APITimeoutError, Groq

logger = logging.getLogger(__name__)


class Transcriber:
    """音声文字起こしクラス。

    Groq APIのwhisper-large-v3-turboモデルを使用。
    """

    MODEL = "whisper-large-v3-turbo"
    TIMEOUT = 5.0
    MAX_RETRIES = 1

    def __init__(self, api_key: str | None = None):
        """Transcriberを初期化する。

        Args:
            api_key: Groq APIキー。Noneの場合は環境変数から取得。

        Raises:
            ValueError: APIキーが設定されていない場合。
        """
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self._api_key:
            raise ValueError("GROQ_API_KEY is not set")

        self._client = Groq(
            api_key=self._api_key,
            timeout=self.TIMEOUT,
            max_retries=self.MAX_RETRIES,
        )

    def transcribe(self, audio_path: Path) -> tuple[str, float]:
        """音声ファイルを文字起こしする。

        Args:
            audio_path: 音声ファイルのパス。

        Returns:
            文字起こし結果のテキストと処理時間（秒）のタプル。
            タイムアウトの場合は空文字列と0.0秒を返す。

        Raises:
            FileNotFoundError: 音声ファイルが存在しない場合。
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        start_time = time.time()

        try:
            with open(audio_path, "rb") as audio_file:
                transcription = self._client.audio.transcriptions.create(
                    file=(audio_path.name, audio_file.read()),
                    model=self.MODEL,
                    language="ja",
                    response_format="text",
                )
        except APITimeoutError:
            logger.error("[Whisper] APIタイムアウト: リトライ後も失敗しました")
            return "", 0.0

        elapsed = time.time() - start_time

        result = transcription.strip() if isinstance(transcription, str) else str(transcription).strip()
        logger.info(f"[Whisper] {result} ({elapsed:.2f}s)")
        return result, elapsed
