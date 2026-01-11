"""文字起こし機能のテスト。"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from groq import APITimeoutError

from transcriber import Transcriber


class TestTranscriber:
    """Transcriberのテスト。"""

    def test_init_without_api_key_raises_error(self):
        """APIキーがない場合にエラーが発生すること。"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="GROQ_API_KEY is not set"):
                Transcriber()

    @patch("transcriber.Groq")
    def test_init_with_api_key(self, mock_groq_class):
        """APIキーで初期化できること。"""
        transcriber = Transcriber(api_key="test_key")
        mock_groq_class.assert_called_once_with(
            api_key="test_key",
            timeout=Transcriber.TIMEOUT,
            max_retries=Transcriber.MAX_RETRIES,
        )

    @patch("transcriber.Groq")
    def test_init_with_env_var(self, mock_groq_class):
        """環境変数からAPIキーを取得できること。"""
        with patch.dict("os.environ", {"GROQ_API_KEY": "env_key"}):
            transcriber = Transcriber()
            mock_groq_class.assert_called_once_with(
                api_key="env_key",
                timeout=Transcriber.TIMEOUT,
                max_retries=Transcriber.MAX_RETRIES,
            )

    @patch("transcriber.Groq")
    def test_transcribe_file_not_found(self, mock_groq_class):
        """存在しないファイルでエラーが発生すること。"""
        transcriber = Transcriber(api_key="test_key")

        with pytest.raises(FileNotFoundError):
            transcriber.transcribe(Path("/nonexistent/file.wav"))

    @patch("transcriber.Groq")
    def test_transcribe_success(self, mock_groq_class):
        """正常に文字起こしできること。"""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "テスト結果"

        transcriber = Transcriber(api_key="test_key")

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"dummy audio data")
            temp_path = Path(f.name)

        try:
            result, elapsed = transcriber.transcribe(temp_path)
            assert result == "テスト結果"
            assert isinstance(elapsed, float)
            assert elapsed >= 0
            mock_client.audio.transcriptions.create.assert_called_once()
        finally:
            temp_path.unlink()

    @patch("transcriber.Groq")
    def test_transcribe_strips_whitespace(self, mock_groq_class):
        """結果の前後の空白が除去されること。"""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "  結果  \n"

        transcriber = Transcriber(api_key="test_key")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"dummy audio data")
            temp_path = Path(f.name)

        try:
            result, elapsed = transcriber.transcribe(temp_path)
            assert result == "結果"
            assert isinstance(elapsed, float)
        finally:
            temp_path.unlink()

    def test_model_constant(self):
        """モデル定数が正しいこと。"""
        assert Transcriber.MODEL == "whisper-large-v3-turbo"

    def test_timeout_and_max_retries_constants(self):
        """タイムアウトとリトライ定数が正しいこと。"""
        assert Transcriber.TIMEOUT == 5.0
        assert Transcriber.MAX_RETRIES == 1

    @patch("transcriber.Groq")
    def test_transcribe_timeout_returns_empty_string(self, mock_groq_class, caplog):
        """タイムアウト時に空文字列と0.0秒を返すこと。"""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.side_effect = APITimeoutError(request=MagicMock())

        transcriber = Transcriber(api_key="test_key")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"dummy audio data")
            temp_path = Path(f.name)

        try:
            with caplog.at_level(logging.ERROR, logger="transcriber"):
                result, elapsed = transcriber.transcribe(temp_path)

            assert result == ""
            assert elapsed == 0.0
            # エラーログが出力されていることを確認
            assert any("APIタイムアウト" in record.message for record in caplog.records)
        finally:
            temp_path.unlink()

    @patch("transcriber.Groq")
    def test_transcribe_logs_result_with_whisper_label(self, mock_groq_class, caplog):
        """文字起こし結果が[Whisper]ラベルでログ出力されること。"""
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "テスト結果"

        transcriber = Transcriber(api_key="test_key")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"dummy audio data")
            temp_path = Path(f.name)

        try:
            with caplog.at_level(logging.INFO, logger="transcriber"):
                result, elapsed = transcriber.transcribe(temp_path)

            # ログに[Whisper]ラベルが含まれることを確認
            assert any("[Whisper]" in record.message for record in caplog.records)
            assert any("テスト結果" in record.message for record in caplog.records)
        finally:
            temp_path.unlink()
