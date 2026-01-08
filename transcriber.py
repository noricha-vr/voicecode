"""音声文字起こしモジュール。

Groq APIのWhisperモデルを使用して音声を文字起こしする。
"""

import os
from pathlib import Path

from groq import Groq


class Transcriber:
    """音声文字起こしクラス。

    Groq APIのwhisper-large-v3-turboモデルを使用。
    """

    MODEL = "whisper-large-v3-turbo"

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

        self._client = Groq(api_key=self._api_key)

    def transcribe(self, audio_path: Path) -> str:
        """音声ファイルを文字起こしする。

        Args:
            audio_path: 音声ファイルのパス。

        Returns:
            文字起こし結果のテキスト。

        Raises:
            FileNotFoundError: 音声ファイルが存在しない場合。
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        print(f"[Transcription] Processing: {audio_path}")

        with open(audio_path, "rb") as audio_file:
            transcription = self._client.audio.transcriptions.create(
                file=(audio_path.name, audio_file.read()),
                model=self.MODEL,
                language="ja",
                response_format="text",
            )

        result = transcription.strip() if isinstance(transcription, str) else str(transcription).strip()
        print(f"[Transcription] Result: {result}")
        return result
