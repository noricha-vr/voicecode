"""文字起こし機能のテスト。"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from transcriber import TRANSCRIBE_PROMPT, Transcriber


def _mock_model_info(name: str, methods: list[str] | None = None) -> MagicMock:
    """list_models 用のモデル情報モックを作る。"""
    model = MagicMock()
    model.name = name if name.startswith("models/") else f"models/{name}"
    model.supported_generation_methods = methods or ["generateContent"]
    return model


@pytest.fixture(autouse=True)
def mock_list_models():
    """外部APIへ出ないよう list_models の既定値をモックする。"""
    with patch(
        "transcriber.genai.list_models",
        return_value=[_mock_model_info(Transcriber.MODEL)],
    ):
        yield


class TestTranscriber:
    """Transcriberのテスト。"""

    def test_init_without_api_key_raises_error(self):
        """APIキーがない場合にエラーが発生すること。"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="GOOGLE_API_KEY is not set"):
                Transcriber()

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_init_with_api_key(self, mock_configure, mock_model_class, mock_load_dict):
        """APIキーで初期化できること。"""
        Transcriber(api_key="test_key")
        mock_configure.assert_called_once_with(api_key="test_key")
        mock_model_class.assert_called_once()

        model_kwargs = mock_model_class.call_args.kwargs
        assert model_kwargs["model_name"] == Transcriber.MODEL
        assert "<instructions>" in model_kwargs["system_instruction"]

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_init_with_env_var(self, mock_configure, mock_model_class, mock_load_dict):
        """環境変数からAPIキーを取得できること。"""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "env_key"}):
            Transcriber()
            mock_configure.assert_called_once_with(api_key="env_key")

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_init_prefers_preview_model_when_available(self, mock_configure, mock_model_class, mock_load_dict):
        """利用可能なら Gemini 3 preview を優先選択すること。"""
        with patch(
            "transcriber.genai.list_models",
            return_value=[
                _mock_model_info("gemini-3-flash-preview"),
                _mock_model_info("gemini-2.5-flash"),
            ],
        ):
            Transcriber(api_key="test_key")

        model_kwargs = mock_model_class.call_args.kwargs
        assert model_kwargs["model_name"] == "gemini-3-flash-preview"

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_init_uses_model_env_var_when_available(self, mock_configure, mock_model_class, mock_load_dict):
        """VOICECODE_GEMINI_MODEL が利用可能なら優先されること。"""
        with patch.dict(
            "os.environ",
            {
                "GOOGLE_API_KEY": "env_key",
                "VOICECODE_GEMINI_MODEL": "gemini-2.0-flash",
            },
            clear=True,
        ):
            with patch(
                "transcriber.genai.list_models",
                return_value=[
                    _mock_model_info("gemini-3-flash-preview"),
                    _mock_model_info("gemini-2.0-flash"),
                ],
            ):
                Transcriber()

        model_kwargs = mock_model_class.call_args.kwargs
        assert model_kwargs["model_name"] == "gemini-2.0-flash"

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_init_normalizes_legacy_model_name(self, mock_configure, mock_model_class, mock_load_dict):
        """gemini-3.0-flash 指定時は互換モデル名へ正規化すること。"""
        with patch.dict(
            "os.environ",
            {
                "GOOGLE_API_KEY": "env_key",
                "VOICECODE_GEMINI_MODEL": "gemini-3.0-flash",
            },
            clear=True,
        ):
            with patch("transcriber.genai.list_models", side_effect=RuntimeError("network error")):
                Transcriber()

        model_kwargs = mock_model_class.call_args.kwargs
        assert model_kwargs["model_name"] == "gemini-3-flash-preview"

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_transcribe_file_not_found(self, mock_configure, mock_model_class, mock_load_dict):
        """存在しないファイルでエラーが発生すること。"""
        transcriber = Transcriber(api_key="test_key")

        with pytest.raises(FileNotFoundError):
            transcriber.transcribe(Path("/nonexistent/file.wav"))

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_transcribe_success(self, mock_configure, mock_model_class, mock_load_dict):
        """正常に文字起こしできること。"""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = "テスト結果"
        mock_model.generate_content.return_value = mock_response

        transcriber = Transcriber(api_key="test_key")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"dummy audio data")
            temp_path = Path(f.name)

        try:
            result, elapsed = transcriber.transcribe(temp_path)
            assert result == "テスト結果"
            assert isinstance(elapsed, float)
            assert elapsed >= 0
            mock_model.generate_content.assert_called_once()

            call_args = mock_model.generate_content.call_args
            assert call_args.args[0][0] == TRANSCRIBE_PROMPT
            assert call_args.kwargs["request_options"] == {"timeout": Transcriber.TIMEOUT}
        finally:
            temp_path.unlink()

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_transcribe_strips_whitespace_and_tags(self, mock_configure, mock_model_class, mock_load_dict):
        """結果の空白とXMLタグが除去されること。"""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = "  <output>結果</output>  \n"
        mock_model.generate_content.return_value = mock_response

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

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_transcribe_api_error_returns_empty(self, mock_configure, mock_model_class, mock_load_dict, caplog):
        """APIエラー時に空文字列を返すこと。"""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.generate_content.side_effect = RuntimeError("timeout")

        transcriber = Transcriber(api_key="test_key")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"dummy audio data")
            temp_path = Path(f.name)

        try:
            with caplog.at_level(logging.ERROR, logger="transcriber"):
                result, elapsed = transcriber.transcribe(temp_path)

            assert result == ""
            assert isinstance(elapsed, float)
            assert elapsed >= 0
            assert any("API呼び出しに失敗" in record.message for record in caplog.records)
        finally:
            temp_path.unlink()

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_transcribe_retries_on_transient_error(self, mock_configure, mock_model_class, mock_load_dict):
        """一時的なAPIエラー時に同一モデルで再試行すること。"""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        recovered_response = MagicMock()
        recovered_response.text = "再試行で復旧"
        mock_model.generate_content.side_effect = [
            RuntimeError("504 Deadline expired before operation could complete."),
            recovered_response,
        ]

        transcriber = Transcriber(api_key="test_key")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"dummy audio data")
            temp_path = Path(f.name)

        try:
            result, elapsed = transcriber.transcribe(temp_path)
            assert result == "再試行で復旧"
            assert isinstance(elapsed, float)
            assert mock_model.generate_content.call_count == 2
        finally:
            temp_path.unlink()

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_transcribe_switches_model_on_transient_error(self, mock_configure, mock_model_class, mock_load_dict):
        """一時的なAPIエラーが継続する場合にモデル切替して再試行すること。"""
        broken_model = MagicMock()
        broken_model.generate_content.side_effect = RuntimeError(
            "504 Deadline expired before operation could complete."
        )

        recovered_model = MagicMock()
        recovered_response = MagicMock()
        recovered_response.text = "別モデルで復旧"
        recovered_model.generate_content.return_value = recovered_response

        mock_model_class.side_effect = [broken_model, recovered_model]

        with patch(
            "transcriber.genai.list_models",
            return_value=[
                _mock_model_info("gemini-3-flash-preview"),
                _mock_model_info("gemini-2.5-flash"),
            ],
        ):
            transcriber = Transcriber(api_key="test_key")

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"dummy audio data")
                temp_path = Path(f.name)

            try:
                result, elapsed = transcriber.transcribe(temp_path)
                assert result == "別モデルで復旧"
                assert isinstance(elapsed, float)
                assert broken_model.generate_content.call_count == 2
                assert mock_model_class.call_count == 2
            finally:
                temp_path.unlink()

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_transcribe_logs_result_with_gemini_label(self, mock_configure, mock_model_class, mock_load_dict, caplog):
        """文字起こし結果が[Gemini]ラベルでログ出力されること。"""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_response = MagicMock()
        mock_response.text = "テスト結果"
        mock_model.generate_content.return_value = mock_response

        transcriber = Transcriber(api_key="test_key")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"dummy audio data")
            temp_path = Path(f.name)

        try:
            with caplog.at_level(logging.INFO, logger="transcriber"):
                transcriber.transcribe(temp_path)

            assert any("[Gemini]" in record.message for record in caplog.records)
            assert any("テスト結果" in record.message for record in caplog.records)
        finally:
            temp_path.unlink()

    @patch("transcriber._load_user_dictionary", return_value=("", ""))
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_transcribe_switches_model_and_retries_on_404(self, mock_configure, mock_model_class, mock_load_dict):
        """モデル404時にモデル切替して再試行すること。"""
        broken_model = MagicMock()
        broken_model.generate_content.side_effect = RuntimeError(
            "404 models/gemini-3.0-flash is not found for API version v1beta"
        )

        recovered_model = MagicMock()
        recovered_response = MagicMock()
        recovered_response.text = "復旧結果"
        recovered_model.generate_content.return_value = recovered_response

        mock_model_class.side_effect = [broken_model, recovered_model]

        with patch(
            "transcriber.genai.list_models",
            return_value=[
                _mock_model_info("gemini-3-flash-preview"),
                _mock_model_info("gemini-2.5-flash"),
            ],
        ):
            transcriber = Transcriber(api_key="test_key")

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(b"dummy audio data")
                temp_path = Path(f.name)

            try:
                result, elapsed = transcriber.transcribe(temp_path)
                assert result == "復旧結果"
                assert isinstance(elapsed, float)
                assert mock_model_class.call_count == 2
            finally:
                temp_path.unlink()

    @patch("transcriber._load_user_dictionary")
    @patch("transcriber.genai.GenerativeModel")
    @patch("transcriber.genai.configure")
    def test_init_injects_user_dictionary(self, mock_configure, mock_model_class, mock_load_dict):
        """ユーザー辞書がシステムプロンプトへ注入されること。"""
        mock_load_dict.return_value = (
            '\n<category name="ユーザー辞書（変換）">\n<term japanese="クロード" english="Claude" context="always"/>\n</category>',
            '\n<category name="ユーザー辞書（ヒント）" type="hint">\n<hint>Opus</hint>\n</category>',
        )

        Transcriber(api_key="test_key")

        model_kwargs = mock_model_class.call_args.kwargs
        system_instruction = model_kwargs["system_instruction"]
        assert "ユーザー辞書（変換）" in system_instruction
        assert "ユーザー辞書（ヒント）" in system_instruction
        assert "クロード" in system_instruction
        assert "Opus" in system_instruction

    def test_model_constant(self):
        """モデル定数が正しいこと。"""
        assert Transcriber.MODEL == "gemini-2.5-flash"

    def test_timeout_constant(self):
        """タイムアウト定数が正しいこと。"""
        assert Transcriber.TIMEOUT == 10.0
