"""LLM後処理機能のテスト。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from postprocessor import PostProcessor, SYSTEM_PROMPT, _load_user_dictionary


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
        """空文字列の場合に空文字列と0秒が返されること。"""
        processor = PostProcessor(api_key="test_key")
        result, elapsed = processor.process("")
        assert result == ""
        assert elapsed == 0.0

    @patch("postprocessor.OpenAI")
    def test_process_whitespace_only(self, mock_openai_class):
        """空白のみの場合に空文字列と0秒が返されること。"""
        processor = PostProcessor(api_key="test_key")
        result, elapsed = processor.process("   \n\t  ")
        assert result == ""
        assert elapsed == 0.0

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary", return_value="")
    def test_process_success(self, mock_load_dict, mock_openai_class):
        """正常に処理できること。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="React"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")
        result, elapsed = processor.process("リアクト")

        assert result == "React"
        assert isinstance(elapsed, float)
        assert elapsed >= 0
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
        result, elapsed = processor.process("リアクト")

        assert result == "React"
        assert isinstance(elapsed, float)

    @patch("postprocessor.OpenAI")
    def test_process_removes_output_xml_tags(self, mock_openai_class):
        """出力からXMLタグ<output>が除去されること。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="<output>テスト</output>"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")
        result, elapsed = processor.process("テスト")

        assert result == "テスト"
        assert isinstance(elapsed, float)

    @patch("postprocessor.OpenAI")
    def test_process_without_xml_tags(self, mock_openai_class):
        """XMLタグがない場合はそのまま返されること。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="テスト"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")
        result, elapsed = processor.process("テスト")

        assert result == "テスト"
        assert isinstance(elapsed, float)

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

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary")
    def test_init_loads_user_dictionary(self, mock_load_dict, mock_openai_class):
        """初期化時にユーザー辞書が読み込まれること。"""
        mock_load_dict.return_value = '\n<category name="ユーザー辞書">\n<term japanese="クロードコード" english="Claude Code" context="always"/>\n</category>'

        processor = PostProcessor(api_key="test_key")

        mock_load_dict.assert_called_once()
        assert "ユーザー辞書" in processor._system_prompt
        assert 'japanese="クロードコード" english="Claude Code"' in processor._system_prompt

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary")
    def test_init_without_user_dictionary(self, mock_load_dict, mock_openai_class):
        """ユーザー辞書がない場合はデフォルトのシステムプロンプトが使用されること。"""
        mock_load_dict.return_value = ""

        processor = PostProcessor(api_key="test_key")

        mock_load_dict.assert_called_once()
        assert processor._system_prompt == SYSTEM_PROMPT

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary")
    def test_process_uses_system_prompt_with_user_dictionary(
        self, mock_load_dict, mock_openai_class
    ):
        """processメソッドがユーザー辞書を含むシステムプロンプトを使用すること。"""
        mock_load_dict.return_value = '\n<category name="ユーザー辞書">\n<term japanese="テスト" english="Test" context="always"/>\n</category>'

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")
        processor.process("テスト")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "ユーザー辞書" in call_kwargs["messages"][0]["content"]


class TestLoadUserDictionary:
    """_load_user_dictionary関数のテスト。"""

    def test_returns_empty_when_file_not_exists(self, tmp_path):
        """辞書ファイルが存在しない場合に空文字列を返すこと。"""
        with patch.object(Path, "home", return_value=tmp_path):
            result = _load_user_dictionary()
            assert result == ""

    def test_returns_empty_when_file_is_empty(self, tmp_path):
        """辞書ファイルが空の場合に空文字列を返すこと。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("")

        with patch.object(Path, "home", return_value=tmp_path):
            result = _load_user_dictionary()
            assert result == ""

    def test_returns_empty_when_only_comments(self, tmp_path):
        """コメント行のみの場合に空文字列を返すこと。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("# コメント行\n# もう一つのコメント\n")

        with patch.object(Path, "home", return_value=tmp_path):
            result = _load_user_dictionary()
            assert result == ""

    def test_parses_valid_entries(self, tmp_path):
        """有効なエントリを正しくパースすること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("クロードコード\tClaude Code\n")

        with patch.object(Path, "home", return_value=tmp_path):
            result = _load_user_dictionary()
            assert 'category name="ユーザー辞書"' in result
            assert 'japanese="クロードコード" english="Claude Code"' in result

    def test_parses_multiple_readings(self, tmp_path):
        """複数の読み（カンマ区切り）を正しくパースすること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("ネクスト,ネクストJS\tNext.js\n")

        with patch.object(Path, "home", return_value=tmp_path):
            result = _load_user_dictionary()
            assert 'japanese="ネクスト,ネクストJS" english="Next.js"' in result

    def test_ignores_comments_and_empty_lines(self, tmp_path):
        """コメント行と空行を無視すること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("# コメント\nクロードコード\tClaude Code\n\n# もう一つ\nスベルトキット\tSvelteKit\n")

        with patch.object(Path, "home", return_value=tmp_path):
            result = _load_user_dictionary()
            assert 'japanese="クロードコード" english="Claude Code"' in result
            assert 'japanese="スベルトキット" english="SvelteKit"' in result
            assert "# コメント" not in result

    def test_ignores_invalid_lines(self, tmp_path):
        """不正な形式の行を無視すること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("不正な行\nクロードコード\tClaude Code\nタブなし行\n")

        with patch.object(Path, "home", return_value=tmp_path):
            result = _load_user_dictionary()
            assert 'japanese="クロードコード" english="Claude Code"' in result
            assert "不正な行" not in result
            assert "タブなし行" not in result
