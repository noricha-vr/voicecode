"""録音機能モジュール。

マイクから音声をキャプチャし、一時ファイルに保存する。
"""

import logging
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sounddevice as sd


logger = logging.getLogger(__name__)


class MicrophonePermissionError(Exception):
    """マイク権限エラー。

    macOS のマイク権限が許可されていない場合に発生する。
    """

    def __init__(self, message: str | None = None):
        """MicrophonePermissionError を初期化する。

        Args:
            message: エラーメッセージ。None の場合はデフォルトメッセージを使用。
        """
        if message is None:
            message = (
                "マイク権限が許可されていません。\n"
                "システム設定 > プライバシーとセキュリティ > マイク で\n"
                "ターミナル（または VoiceCode.app）を許可してください。"
            )
        super().__init__(message)


@dataclass
class RecordingConfig:
    """録音設定。

    Attributes:
        sample_rate: サンプリングレート（Hz）。
        channels: チャンネル数。
        dtype: 音声データの型。
        max_duration: 最大録音時間（秒）。
    """

    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    max_duration: int = 120


class AudioRecorder:
    """音声録音クラス。

    マイクから音声をキャプチャし、WAVファイルとして保存する。
    """

    def __init__(self, config: RecordingConfig | None = None):
        """AudioRecorderを初期化する。

        Args:
            config: 録音設定。Noneの場合はデフォルト設定を使用。
        """
        self.config = config or RecordingConfig()
        self._frames: list[np.ndarray] = []
        self._is_recording = False
        self._stream: sd.InputStream | None = None
        self._start_time: float | None = None
        self._max_duration: int = self.config.max_duration
        self._timeout_reached: bool = False

    @property
    def is_recording(self) -> bool:
        """録音中かどうかを返す。"""
        return self._is_recording

    @property
    def is_timeout(self) -> bool:
        """タイムアウトで録音が停止したかどうかを返す。"""
        return self._timeout_reached

    def start(self) -> None:
        """録音を開始する。

        Raises:
            RuntimeError: 既に録音中の場合。
            MicrophonePermissionError: マイク権限が許可されていない場合。
        """
        if self._is_recording:
            raise RuntimeError("Already recording")

        self._frames = []
        self._is_recording = True
        self._start_time = time.time()
        self._timeout_reached = False

        def callback(
            indata: np.ndarray, frames: int, time_info: dict, status: sd.CallbackFlags
        ) -> None:
            if status:
                print(f"Recording status: {status}")

            # タイムアウトチェック
            if self._start_time is not None:
                elapsed = time.time() - self._start_time
                if elapsed >= self._max_duration:
                    self._timeout_reached = True
                    raise sd.CallbackAbort()

            self._frames.append(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                callback=callback,
            )
            self._stream.start()
        except sd.PortAudioError as e:
            self._is_recording = False
            self._start_time = None
            error_str = str(e).lower()
            # マイク権限エラーの検出パターン
            # 注: "input" は InputStream の全エラーに含まれるため除外
            if "permission" in error_str or "denied" in error_str:
                logger.error(f"Microphone permission error: {e}")
                raise MicrophonePermissionError() from e
            # その他の PortAudioError は再 raise
            logger.error(f"PortAudio error: {e}")
            raise
        print("[Recording] Started...")

    def stop(self) -> Path:
        """録音を停止し、音声ファイルのパスを返す。

        Returns:
            録音された音声ファイルのパス。

        Raises:
            RuntimeError: 録音中でない場合。
        """
        if not self._is_recording:
            raise RuntimeError("Not recording")

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._is_recording = False
        self._timeout_reached = False
        print("[Recording] Stopped.")

        return self._save_to_file()

    def _save_to_file(self) -> Path:
        """録音データをWAVファイルとして保存する。

        Returns:
            保存されたファイルのパス。
        """
        if not self._frames:
            raise ValueError("No audio data recorded")

        audio_data = np.concatenate(self._frames, axis=0)

        temp_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        )
        temp_path = Path(temp_file.name)
        temp_file.close()

        with wave.open(str(temp_path), "wb") as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(self.config.sample_rate)
            wf.writeframes(audio_data.tobytes())

        print(f"[Recording] Saved to: {temp_path}")
        return temp_path


def check_microphone_permission() -> bool:
    """マイク権限をチェックする。

    短時間の録音テストを実行してマイク権限を確認する。

    Returns:
        マイク権限が許可されている場合は True、そうでなければ False。
    """
    try:
        # 非常に短い録音テストで権限を確認（1サンプルのみ）
        sd.rec(1, samplerate=16000, channels=1, blocking=True)
        return True
    except sd.PortAudioError as e:
        logger.warning(f"Microphone permission check failed: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error during microphone check: {e}")
        return False
