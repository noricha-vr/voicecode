"""後処理互換レイヤと辞書読み込み機能のテスト。"""

import logging
from pathlib import Path
from unittest.mock import patch

from postprocessor import PostProcessor, SYSTEM_PROMPT, _load_user_dictionary


class TestPostProcessor:
    """PostProcessor のテスト。"""

    def test_process_empty_string(self):
        """空文字列なら空文字列と0秒を返すこと。"""
        processor = PostProcessor()
        result, elapsed = processor.process("")
        assert result == ""
        assert elapsed == 0.0

    def test_process_pass_through(self):
        """通常文字列はそのまま返すこと。"""
        processor = PostProcessor()
        result, elapsed = processor.process("テスト")
        assert result == "テスト"
        assert isinstance(elapsed, float)
        assert elapsed >= 0

    def test_process_removes_xml_tags(self):
        """互換のためXMLタグは除去すること。"""
        processor = PostProcessor()
        result, _ = processor.process("<output>テスト</output>")
        assert result == "テスト"

    def test_process_logs_with_postprocess_label(self, caplog):
        """ログにPostProcessラベルが含まれること。"""
        processor = PostProcessor()
        with caplog.at_level(logging.INFO, logger="postprocessor"):
            processor.process("テスト")
        assert any("[PostProcess]" in record.message for record in caplog.records)

    def test_model_constants(self):
        """互換クラスの定数が定義されていること。"""
        assert PostProcessor.MODEL == "pass-through"
        assert PostProcessor.TIMEOUT == 0.0
        assert PostProcessor.MAX_RETRIES == 0

    def test_system_prompt_still_available(self):
        """Transcriber で再利用するため SYSTEM_PROMPT を保持していること。"""
        assert "<instructions>" in SYSTEM_PROMPT
        assert "<terminology>" in SYSTEM_PROMPT


class TestLoadUserDictionary:
    """_load_user_dictionary 関数のテスト。"""

    def test_returns_empty_tuple_when_file_not_exists(self, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert conversion_xml == ""
            assert hint_xml == ""

    def test_parses_conversion_and_hint_entries(self, tmp_path):
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("クロードコード\tClaude Code\nhaiku\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert 'name="ユーザー辞書（変換）"' in conversion_xml
            assert 'japanese="クロードコード"' in conversion_xml
            assert 'english="Claude Code"' in conversion_xml
            assert 'name="ユーザー辞書（ヒント）"' in hint_xml
            assert "<hint>haiku</hint>" in hint_xml

    def test_escapes_special_characters(self, tmp_path):
        dict_dir = tmp_path / ".voicecode"
        dict_dir.mkdir()
        dict_file = dict_dir / "dictionary.txt"
        dict_file.write_text("アンド\tA&B\n<test>\n")

        with patch.object(Path, "home", return_value=tmp_path):
            conversion_xml, hint_xml = _load_user_dictionary()
            assert "A&amp;B" in conversion_xml
            assert "&lt;test&gt;" in hint_xml
