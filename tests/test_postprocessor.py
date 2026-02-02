"""LLM後処理機能のテスト。"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from openai import APITimeoutError

from postprocessor import (
    PostProcessor,
    SYSTEM_PROMPT,
    DICTIONARY_PROMPT,
    INSTRUCTION_PROMPT,
    _load_user_dictionary,
)


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
            timeout=PostProcessor.TIMEOUT,
            max_retries=PostProcessor.MAX_RETRIES,
        )

    @patch("postprocessor.OpenAI")
    def test_init_with_env_var(self, mock_openai_class):
        """環境変数からAPIキーを取得できること。"""
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "env_key"}):
            processor = PostProcessor()
            mock_openai_class.assert_called_once_with(
                base_url="https://openrouter.ai/api/v1",
                api_key="env_key",
                timeout=PostProcessor.TIMEOUT,
                max_retries=PostProcessor.MAX_RETRIES,
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
    @patch("postprocessor._load_user_dictionary", return_value=("", ""))
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

        # 新しいメッセージ構造を検証
        messages = call_kwargs["messages"]
        assert len(messages) == 3

        # 最初のメッセージ: 辞書（cache_control付き）
        assert messages[0]["role"] == "system"
        assert isinstance(messages[0]["content"], list)
        assert messages[0]["content"][0]["type"] == "text"
        assert "<terminology>" in messages[0]["content"][0]["text"]
        assert messages[0]["content"][0]["cache_control"] == {"type": "ephemeral"}

        # 2番目のメッセージ: ユーザー入力
        assert messages[1] == {"role": "user", "content": "リアクト"}

        # 3番目のメッセージ: 指示
        assert messages[2]["role"] == "system"
        assert "<role>" in messages[2]["content"]
        assert "<examples>" in messages[2]["content"]

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
    def test_process_removes_unexpected_xml_tags(self, mock_openai_class):
        """出力から予期しないXMLタグが除去されること。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="<bos>work tree</>テスト"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")
        result, elapsed = processor.process("テスト")

        assert result == "work treeテスト"
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

    def test_timeout_and_max_retries_constants(self):
        """タイムアウトとリトライ定数が正しいこと。"""
        assert PostProcessor.TIMEOUT == 5.0
        assert PostProcessor.MAX_RETRIES == 1

    @patch("postprocessor.OpenAI")
    def test_process_timeout_returns_original_text(self, mock_openai_class, caplog):
        """タイムアウト時に元のテキストを返すこと（フォールバック）。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())

        processor = PostProcessor(api_key="test_key")

        with caplog.at_level(logging.ERROR, logger="postprocessor"):
            result, elapsed = processor.process("リアクト")

        # 元のテキストがそのまま返されること
        assert result == "リアクト"
        assert isinstance(elapsed, float)
        assert elapsed >= 0
        # エラーログが出力されていることを確認
        assert any("APIタイムアウト" in record.message for record in caplog.records)

    def test_dictionary_prompt_contains_terminology(self):
        """DICTIONARY_PROMPTに用語辞書が含まれていること。"""
        assert "<terminology>" in DICTIONARY_PROMPT
        assert "</terminology>" in DICTIONARY_PROMPT
        assert 'japanese="リアクト" english="React"' in DICTIONARY_PROMPT
        assert 'japanese="タイプスクリプト" english="TypeScript"' in DICTIONARY_PROMPT
        assert 'japanese="ユースステート" english="useState"' in DICTIONARY_PROMPT

    def test_instruction_prompt_contains_role(self):
        """INSTRUCTION_PROMPTに役割定義が含まれていること。"""
        assert "<role>" in INSTRUCTION_PROMPT
        assert "</role>" in INSTRUCTION_PROMPT
        assert "ペアプログラマーの耳" in INSTRUCTION_PROMPT
        assert "中継役" in INSTRUCTION_PROMPT
        assert "応答する立場ではありません" in INSTRUCTION_PROMPT

    def test_instruction_prompt_contains_hallucination_removal(self):
        """INSTRUCTION_PROMPTにハルシネーション除去が含まれていること。"""
        assert "<hallucination_removal>" in INSTRUCTION_PROMPT
        assert "Whisperハルシネーションの除去" in INSTRUCTION_PROMPT
        assert "空文字列を返す" in INSTRUCTION_PROMPT

    def test_instruction_prompt_contains_examples(self):
        """INSTRUCTION_PROMPTに厳選された8つの例が含まれていること。"""
        assert "<examples>" in INSTRUCTION_PROMPT
        assert "</examples>" in INSTRUCTION_PROMPT

        # 厳選された8つの例を確認
        assert '禁止：指示への応答' in INSTRUCTION_PROMPT
        assert 'プログラミング用語変換' in INSTRUCTION_PROMPT
        assert '文脈依存変換（プログラミング）' in INSTRUCTION_PROMPT
        assert '文脈依存変換（一般）' in INSTRUCTION_PROMPT
        assert '同音異義語修正（上記/蒸気）' in INSTRUCTION_PROMPT
        assert '同音異義語修正（機能/昨日）' in INSTRUCTION_PROMPT
        assert 'ハルシネーション除去（単独）' in INSTRUCTION_PROMPT
        assert 'ハルシネーション除去（末尾付着）' in INSTRUCTION_PROMPT

    def test_system_prompt_backward_compatibility(self):
        """後方互換性のためのSYSTEM_PROMPTが正しいこと。"""
        # terminologyセクションに用語変換定義が含まれていること
        assert 'japanese="リアクト" english="React"' in SYSTEM_PROMPT
        assert 'japanese="タイプスクリプト" english="TypeScript"' in SYSTEM_PROMPT
        assert 'japanese="ユースステート" english="useState"' in SYSTEM_PROMPT
        # 役割定義が含まれていること
        assert "ペアプログラマーの耳" in SYSTEM_PROMPT
        assert "中継役" in SYSTEM_PROMPT

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
        mock_load_dict.return_value = (
            '\n<category name="ユーザー辞書（変換）">\n<term japanese="クロードコード" english="Claude Code" context="always"/>\n</category>',
            ""
        )

        processor = PostProcessor(api_key="test_key")

        mock_load_dict.assert_called_once()
        assert "ユーザー辞書（変換）" in processor._dictionary_prompt
        assert 'japanese="クロードコード" english="Claude Code"' in processor._dictionary_prompt

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary")
    def test_init_without_user_dictionary(self, mock_load_dict, mock_openai_class):
        """ユーザー辞書がない場合はデフォルトの辞書プロンプトが使用されること。"""
        mock_load_dict.return_value = ("", "")

        processor = PostProcessor(api_key="test_key")

        mock_load_dict.assert_called_once()
        assert processor._dictionary_prompt == DICTIONARY_PROMPT
        assert processor._instruction_prompt == INSTRUCTION_PROMPT

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary")
    def test_process_uses_new_message_structure_with_user_dictionary(
        self, mock_load_dict, mock_openai_class
    ):
        """processメソッドがユーザー辞書を含む新しいメッセージ構造を使用すること。"""
        mock_load_dict.return_value = (
            '\n<category name="ユーザー辞書（変換）">\n<term japanese="テスト" english="Test" context="always"/>\n</category>',
            ""
        )

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")
        processor.process("テスト")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]

        # 辞書プロンプトにユーザー辞書が含まれていること
        assert "ユーザー辞書（変換）" in messages[0]["content"][0]["text"]

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary", return_value=("", ""))
    def test_process_logs_result_with_gemini_label(self, mock_load_dict, mock_openai_class, caplog):
        """処理結果が[Gemini]ラベルでログ出力されること。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="React"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")

        with caplog.at_level(logging.INFO, logger="postprocessor"):
            result, elapsed = processor.process("リアクト")

        # ログに[Gemini]ラベルが含まれることを確認
        assert any("[Gemini]" in record.message for record in caplog.records)
        assert any("React" in record.message for record in caplog.records)

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary")
    def test_init_loads_hint_dictionary(self, mock_load_dict, mock_openai_class):
        """初期化時にヒント辞書が読み込まれること。"""
        mock_load_dict.return_value = (
            "",
            '\n<category name="ユーザー辞書（ヒント）" type="hint">\n<hint>haiku, sonnet</hint>\n<note>これらの単語はプログラミング文脈で頻繁に使用されます。</note>\n</category>'
        )

        processor = PostProcessor(api_key="test_key")

        mock_load_dict.assert_called_once()
        assert "ユーザー辞書（ヒント）" in processor._dictionary_prompt
        assert "haiku, sonnet" in processor._dictionary_prompt

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary")
    def test_init_loads_both_conversion_and_hint(self, mock_load_dict, mock_openai_class):
        """初期化時に変換辞書とヒント辞書が両方読み込まれること。"""
        mock_load_dict.return_value = (
            '\n<category name="ユーザー辞書（変換）">\n<term japanese="クロード" english="Claude" context="always"/>\n</category>',
            '\n<category name="ユーザー辞書（ヒント）" type="hint">\n<hint>Opus</hint>\n<note>これらの単語はプログラミング文脈で頻繁に使用されます。</note>\n</category>'
        )

        processor = PostProcessor(api_key="test_key")

        mock_load_dict.assert_called_once()
        # 変換辞書が含まれていること
        assert "ユーザー辞書（変換）" in processor._dictionary_prompt
        assert 'japanese="クロード" english="Claude"' in processor._dictionary_prompt
        # ヒント辞書が含まれていること
        assert "ユーザー辞書（ヒント）" in processor._dictionary_prompt
        assert "Opus" in processor._dictionary_prompt


class TestLoadUserDictionary:
    """_load_user_dictionary関数のテスト。"""

    def test_returns_empty_tuple_when_file_not_exists(self, tmp_path):
        """辞書ファイルが存在しない場合に空のタプルを返すこと。"""
        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert conversion_xml == ""
            assert hint_xml == ""

    def test_returns_empty_tuple_when_file_is_empty(self, tmp_path):
        """辞書ファイルが空の場合に空のタプルを返すこと。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert conversion_xml == ""
            assert hint_xml == ""

    def test_returns_empty_tuple_when_only_comments(self, tmp_path):
        """コメント行のみの場合に空のタプルを返すこと。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("# コメント行\n# もう一つのコメント\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert conversion_xml == ""
            assert hint_xml == ""

    def test_parses_conversion_entries(self, tmp_path):
        """タブ区切りの変換エントリを正しくパースすること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("クロードコード\tClaude Code\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert 'category name="ユーザー辞書（変換）"' in conversion_xml
            assert 'japanese="クロードコード" english="Claude Code"' in conversion_xml
            assert hint_xml == ""

    def test_parses_hint_entries(self, tmp_path):
        """タブなしの行をヒントエントリとして認識すること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("haiku\nsonnet\nOpus\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert conversion_xml == ""
            assert 'category name="ユーザー辞書（ヒント）" type="hint"' in hint_xml
            assert "<hint>haiku, sonnet, Opus</hint>" in hint_xml
            assert "これらの単語はプログラミング文脈で頻繁に使用されます" in hint_xml

    def test_parses_mixed_entries(self, tmp_path):
        """変換エントリとヒントエントリの混在を正しくパースすること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("クロードコード\tClaude Code\nhaiku\nスベルトキット\tSvelteKit\nsonnet\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            # 変換エントリの検証
            assert 'category name="ユーザー辞書（変換）"' in conversion_xml
            assert 'japanese="クロードコード" english="Claude Code"' in conversion_xml
            assert 'japanese="スベルトキット" english="SvelteKit"' in conversion_xml
            # ヒントエントリの検証
            assert 'category name="ユーザー辞書（ヒント）" type="hint"' in hint_xml
            assert "<hint>haiku, sonnet</hint>" in hint_xml

    def test_parses_multiple_readings(self, tmp_path):
        """複数の読み（カンマ区切り）を正しくパースすること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("ネクスト,ネクストJS\tNext.js\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert 'japanese="ネクスト,ネクストJS" english="Next.js"' in conversion_xml

    def test_ignores_comments_and_empty_lines(self, tmp_path):
        """コメント行と空行を無視すること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("# コメント\nクロードコード\tClaude Code\n\n# もう一つ\nスベルトキット\tSvelteKit\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert 'japanese="クロードコード" english="Claude Code"' in conversion_xml
            assert 'japanese="スベルトキット" english="SvelteKit"' in conversion_xml
            assert "# コメント" not in conversion_xml
            assert hint_xml == ""

    def test_hint_entries_with_comments(self, tmp_path):
        """コメント行と空行がある場合もヒントエントリを正しくパースすること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("# ヒント単語\nhaiku\n\n# モデル名\nsonnet\nOpus\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert conversion_xml == ""
            assert "<hint>haiku, sonnet, Opus</hint>" in hint_xml
            assert "# ヒント単語" not in hint_xml

    def test_hint_only_file(self, tmp_path):
        """ヒントエントリのみのファイルを正しく処理すること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("Claude\nGPT\nGemini\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert conversion_xml == ""
            assert 'category name="ユーザー辞書（ヒント）" type="hint"' in hint_xml
            assert "<hint>Claude, GPT, Gemini</hint>" in hint_xml
            assert "優先的に採用してください" in hint_xml

    def test_escapes_special_characters_in_hint(self, tmp_path):
        """ヒント語の特殊文字がエスケープされること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("AT&T\nC<->C\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert "AT&amp;T" in hint_xml
            assert "C&lt;-&gt;C" in hint_xml

    def test_escapes_special_characters_in_conversion(self, tmp_path):
        """変換エントリの特殊文字がエスケープされること。"""
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text('アンド\tA&B\n<タグ>\t<tag>\n')

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert "A&amp;B" in conversion_xml
            assert "&lt;tag&gt;" in conversion_xml


class TestSystemPromptHallucinationRemoval:
    """SYSTEM_PROMPTのハルシネーション除去機能のテスト。"""

    def test_system_prompt_contains_hallucination_removal_section(self):
        """システムプロンプトにハルシネーション除去セクションが含まれていること。"""
        assert "<hallucination_removal>" in SYSTEM_PROMPT
        assert "</hallucination_removal>" in SYSTEM_PROMPT

    def test_system_prompt_lists_hallucination_patterns(self):
        """システムプロンプトにハルシネーションパターンが記載されていること。"""
        assert "ありがとうございました" in SYSTEM_PROMPT
        assert "ご清聴ありがとうございました" in SYSTEM_PROMPT
        assert "ご視聴ありがとうございました" in SYSTEM_PROMPT

    def test_system_prompt_explains_processing_rules(self):
        """システムプロンプトに処理ルールが記載されていること。"""
        # 単独ハルシネーションの処理ルール
        assert "空文字列を返す" in SYSTEM_PROMPT
        # 末尾付着の処理ルール
        assert "その部分を除去" in SYSTEM_PROMPT

    def test_system_prompt_mentions_legitimate_thanks_preservation(self):
        """システムプロンプトに正当な感謝表現の保持が記載されていること。"""
        assert "コードレビューありがとう" in SYSTEM_PROMPT
        assert "修正ありがとうございます" in SYSTEM_PROMPT
        assert "除去しない" in SYSTEM_PROMPT

    def test_system_prompt_contains_hallucination_examples(self):
        """システムプロンプトにハルシネーション除去の例が含まれていること。"""
        # 単独ハルシネーションの例
        assert '<example type="hallucination" name="ハルシネーション除去（単独）">' in SYSTEM_PROMPT
        # ご清聴ハルシネーションの例
        assert '<example type="hallucination" name="ハルシネーション除去（ご清聴）">' in SYSTEM_PROMPT
        # 末尾付着の例
        assert '<example type="hallucination" name="ハルシネーション除去（末尾付着）">' in SYSTEM_PROMPT

    def test_system_prompt_contains_legitimate_thanks_examples(self):
        """システムプロンプトに正当な感謝表現の例が含まれていること。"""
        assert '<example type="hallucination" name="正当な感謝は維持">' in SYSTEM_PROMPT
        assert '<example type="hallucination" name="正当な感謝は維持（修正）">' in SYSTEM_PROMPT

    def test_system_prompt_hallucination_role_includes_removal(self):
        """システムプロンプトの役割にハルシネーション除去が含まれていること。"""
        assert "Whisperハルシネーションの除去" in SYSTEM_PROMPT


class TestPromptSeparation:
    """プロンプト分離機能のテスト。"""

    def test_dictionary_prompt_is_separate_from_instruction(self):
        """DICTIONARY_PROMPTとINSTRUCTION_PROMPTが分離されていること。"""
        # DICTIONARY_PROMPTはterminologyのみを含む
        assert "<terminology>" in DICTIONARY_PROMPT
        assert "</terminology>" in DICTIONARY_PROMPT
        assert "<role>" not in DICTIONARY_PROMPT
        assert "<examples>" not in DICTIONARY_PROMPT

        # INSTRUCTION_PROMPTはrole, hallucination_removal, examplesを含む
        assert "<role>" in INSTRUCTION_PROMPT
        assert "<hallucination_removal>" in INSTRUCTION_PROMPT
        assert "<examples>" in INSTRUCTION_PROMPT
        assert "<terminology>" not in INSTRUCTION_PROMPT

    def test_instruction_prompt_has_reduced_examples(self):
        """INSTRUCTION_PROMPTの例が8個に削減されていること。"""
        # 例の数をカウント（<example で始まる行を数える）
        example_count = INSTRUCTION_PROMPT.count("<example ")
        assert example_count == 8, f"Expected 8 examples, but found {example_count}"

    def test_instruction_prompt_contains_required_examples(self):
        """INSTRUCTION_PROMPTに必須の8つの例が含まれていること。"""
        required_examples = [
            "禁止：指示への応答",
            "プログラミング用語変換",
            "文脈依存変換（プログラミング）",
            "文脈依存変換（一般）",
            "同音異義語修正（上記/蒸気）",
            "同音異義語修正（機能/昨日）",
            "ハルシネーション除去（単独）",
            "ハルシネーション除去（末尾付着）",
        ]
        for example_name in required_examples:
            assert example_name in INSTRUCTION_PROMPT, f"Missing example: {example_name}"

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary", return_value=("", ""))
    def test_process_sends_cache_control_for_dictionary(self, mock_load_dict, mock_openai_class):
        """processメソッドが辞書プロンプトにcache_controlを付与すること。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="React"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")
        processor.process("リアクト")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]

        # 最初のメッセージにcache_controlが付与されていること
        assert messages[0]["content"][0]["cache_control"] == {"type": "ephemeral"}

    @patch("postprocessor.OpenAI")
    @patch("postprocessor._load_user_dictionary", return_value=("", ""))
    def test_process_message_order(self, mock_load_dict, mock_openai_class):
        """processメソッドのメッセージ順序が正しいこと（辞書→ユーザー入力→指示）。"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="React"))]
        mock_client.chat.completions.create.return_value = mock_response

        processor = PostProcessor(api_key="test_key")
        processor.process("テスト入力")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]

        # メッセージ順序を検証
        assert messages[0]["role"] == "system"  # 辞書
        assert "<terminology>" in messages[0]["content"][0]["text"]

        assert messages[1]["role"] == "user"  # ユーザー入力
        assert messages[1]["content"] == "テスト入力"

        assert messages[2]["role"] == "system"  # 指示
        assert "<role>" in messages[2]["content"]
