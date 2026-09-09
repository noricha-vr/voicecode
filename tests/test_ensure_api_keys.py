"""API キー入力プロンプト機能のテスト。"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

# main モジュールから _ensure_api_keys をインポート
# macOS 以外でもテスト可能にするため、sys.platform をモックする
with patch("sys.platform", "darwin"):
    from main import _ensure_api_keys


class TestEnsureApiKeys:
    """_ensure_api_keys のテスト。"""

    def test_all_keys_already_set(self, tmp_path: Path):
        """全てのキーが既に設定されている場合、何もしないこと。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {
            "GROQ_API_KEY": "existing_groq_key",
            "OPENROUTER_API_KEY": "existing_openrouter_key",
        }, clear=False):
            _ensure_api_keys(env_path)

        # .env ファイルは作成されない
        assert not env_path.exists()

    def test_prompts_for_missing_groq_key(self, tmp_path: Path):
        """GROQ_API_KEY が未設定の場合、入力を求めること。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "existing_openrouter_key",
        }, clear=True):
            with patch("builtins.input", return_value="user_groq_key"):
                _ensure_api_keys(env_path)

            # 環境変数に設定される（with ブロック内で確認）
            assert os.environ.get("GROQ_API_KEY") == "user_groq_key"

        # .env ファイルに保存される
        assert env_path.exists()
        content = env_path.read_text()
        assert "GROQ_API_KEY=user_groq_key" in content

    def test_prompts_for_missing_openrouter_key(self, tmp_path: Path):
        """OPENROUTER_API_KEY が未設定の場合、入力を求めること。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {
            "GROQ_API_KEY": "existing_groq_key",
        }, clear=True):
            with patch("builtins.input", return_value="user_openrouter_key"):
                _ensure_api_keys(env_path)

            # 環境変数に設定される（with ブロック内で確認）
            assert os.environ.get("OPENROUTER_API_KEY") == "user_openrouter_key"

        # .env ファイルに保存される
        assert env_path.exists()
        content = env_path.read_text()
        assert "OPENROUTER_API_KEY=user_openrouter_key" in content

    def test_prompts_for_both_keys(self, tmp_path: Path):
        """両方のキーが未設定の場合、順番に入力を求めること。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", side_effect=["user_groq", "user_openrouter"]):
                _ensure_api_keys(env_path)

            # 環境変数に設定される（with ブロック内で確認）
            assert os.environ.get("GROQ_API_KEY") == "user_groq"
            assert os.environ.get("OPENROUTER_API_KEY") == "user_openrouter"

        # .env ファイルに保存される
        content = env_path.read_text()
        assert "GROQ_API_KEY=user_groq" in content
        assert "OPENROUTER_API_KEY=user_openrouter" in content

    def test_empty_input_exits(self, tmp_path: Path):
        """空の入力で終了すること。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", return_value=""):
                with pytest.raises(SystemExit) as exc_info:
                    _ensure_api_keys(env_path)

        assert exc_info.value.code == 1

    def test_eof_error_exits(self, tmp_path: Path):
        """EOFError（非対話的環境）で終了すること。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", side_effect=EOFError):
                with pytest.raises(SystemExit) as exc_info:
                    _ensure_api_keys(env_path)

        assert exc_info.value.code == 1

    def test_preserves_existing_env_content(self, tmp_path: Path):
        """既存の .env 内容を保持すること。"""
        env_path = tmp_path / ".env"
        env_path.write_text("EXISTING_KEY=existing_value\n")

        with patch.dict(os.environ, {
            "GROQ_API_KEY": "existing_groq",
        }, clear=True):
            with patch("builtins.input", return_value="new_openrouter"):
                _ensure_api_keys(env_path)

        content = env_path.read_text()
        assert "EXISTING_KEY=existing_value" in content
        assert "OPENROUTER_API_KEY=new_openrouter" in content

    def test_ignores_comments_in_env(self, tmp_path: Path):
        """コメント行を無視すること。"""
        env_path = tmp_path / ".env"
        env_path.write_text("# This is a comment\nSOME_KEY=value\n")

        with patch.dict(os.environ, {
            "GROQ_API_KEY": "groq",
            "OPENROUTER_API_KEY": "openrouter",
        }, clear=True):
            _ensure_api_keys(env_path)

        # キーが既に設定されているので更新はない
        # ファイルは変更されていないことを確認
        content = env_path.read_text()
        assert "# This is a comment" in content

    def test_creates_parent_directories(self, tmp_path: Path):
        """親ディレクトリが存在しない場合、作成すること。"""
        env_path = tmp_path / "nested" / "dir" / ".env"

        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", side_effect=["groq_key", "openrouter_key"]):
                _ensure_api_keys(env_path)

        assert env_path.exists()
        assert env_path.parent.exists()

    def test_strips_whitespace_from_input(self, tmp_path: Path):
        """入力の前後の空白を除去すること。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "existing",
        }, clear=True):
            with patch("builtins.input", return_value="  groq_key_with_spaces  "):
                _ensure_api_keys(env_path)

            # 環境変数に設定される（with ブロック内で確認）
            assert os.environ.get("GROQ_API_KEY") == "groq_key_with_spaces"

        content = env_path.read_text()
        assert "GROQ_API_KEY=groq_key_with_spaces" in content
