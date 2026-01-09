"""LLM後処理機能のテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from postprocessor import PostProcessor, SYSTEM_PROMPT


class TestPostProcessor:
    """PostProcessorのテスト。"""

    def test_init_without_api_key_raises_error(self):
        """APIキーがない場合にエラーが発生すること。"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY is not set"):
                PostProcessor()

    @patch("postprocessor.OpenAI")
    def test_init_with_api_key(self, mock_openai_class):
        """APIキーで初期化できること。"""
        processor = PostProcessor(api_key="test_key")
        mock_openai_class.assert_called_once_with(
            base_url="https://openrouter.ai/api/v1",
            api_key="test_key",
        )

    @patch("postprocessor.OpenAI")
    def test_init_with_env_var(self, mock_openai_class):
        """環境変数からAPIキーを取得できること。"""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "env_key"}):
            processor = PostProcessor()
            mock_openai_class.assert_called_once_with(
                base_url="https://openrouter.ai/api/v1",
                api_key="env_key",
            )

    @patch("postprocessor.OpenAI")
    def test_process_empty_string(self, mock_openai_class):
        """空文字列の場合に空文字列が返されること。"""
        processor = PostProcessor(api_key="test_key")
        result = processor.process("")
        assert result == ""

    @patch("postprocessor.OpenAI")
    def test_process_whitespace_only(self, mock_openai_class):
        """空白のみの場合に空文字列が返されること。"""
        processor = PostProcessor(api_key="test_key")
        result = processor.process("   \n\t  ")
        assert result == ""

    @patch("postprocessor.OpenAI")
    def test_process_success(self, mock_openai_class):
        """正常に処理できること。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="React"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")
        result = processor.process("リアクト")

        assert result == "React"
        mock_client.chat.completions.create.assert_called_once()

        # 呼び出し引数を検証
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "google/gemini-2.5-flash-lite"
        assert call_kwargs["messages"] == [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "リアクト"},
        ]

    @patch("postprocessor.OpenAI")
    def test_process_strips_result(self, mock_openai_class):
        """結果の前後の空白が除去されること。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="  React  \n"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")
        result = processor.process("リアクト")

        assert result == "React"

    def test_model_constant(self):
        """モデル定数が正しいこと。"""
        assert PostProcessor.MODEL == "google/gemini-2.5-flash-lite"

    def test_system_prompt_contains_conversion_examples(self):
        """システムプロンプトに変換例が含まれていること。"""
        # terminologyセクションに用語変換定義が含まれていること
        assert 'japanese="リアクト" english="React"' in SYSTEM_PROMPT
        assert 'japanese="タイプスクリプト" english="TypeScript"' in SYSTEM_PROMPT
        assert 'japanese="ユースステート" english="useState"' in SYSTEM_PROMPT

    def test_system_prompt_prevents_translation(self):
        """システムプロンプトに日本語維持ルールが含まれていること。"""
        # 日本語維持ルールが含まれていること
        assert "日本語維持" in SYSTEM_PROMPT
        assert "英語に翻訳しない" in SYSTEM_PROMPT

    def test_system_prompt_contains_examples(self):
        """システムプロンプトに入力例と出力例が含まれていること。"""
        # 日本語をそのまま維持する例
        assert "お、これは音声入力ができているのか?" in SYSTEM_PROMPT
        # カタカナ技術用語を変換する例
        assert "ReactのuseStateを使って状態管理する" in SYSTEM_PROMPT

    def test_system_prompt_contains_additional_terms(self):
        """システムプロンプトに追加の変換例が含まれていること。"""
        # terminologyセクションに追加用語が含まれていること
        assert 'japanese="ユースエフェクト" english="useEffect"' in SYSTEM_PROMPT
        assert 'japanese="クロード" english="Claude"' in SYSTEM_PROMPT
        assert 'japanese="ジーピーティー" english="GPT"' in SYSTEM_PROMPT
