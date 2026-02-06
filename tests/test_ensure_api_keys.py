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

    def test_google_key_already_set(self, tmp_path: Path):
        """GOOGLE_API_KEY が設定済みなら何もしないこと。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "existing_google_key"}, clear=True):
            _ensure_api_keys(env_path)

        assert not env_path.exists()

    def test_prompts_for_missing_google_key(self, tmp_path: Path):
        """GOOGLE_API_KEY が未設定なら入力を求めること。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", return_value="user_google_key"):
                _ensure_api_keys(env_path)

            assert os.environ.get("GOOGLE_API_KEY") == "user_google_key"

        assert env_path.exists()
        assert "GOOGLE_API_KEY=user_google_key" in env_path.read_text()

    def test_empty_input_exits(self, tmp_path: Path):
        """空入力で終了すること。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", return_value=""):
                with pytest.raises(SystemExit) as exc_info:
                    _ensure_api_keys(env_path)

        assert exc_info.value.code == 1

    def test_eof_error_exits(self, tmp_path: Path):
        """EOFError（非対話環境）で終了すること。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", side_effect=EOFError):
                with pytest.raises(SystemExit) as exc_info:
                    _ensure_api_keys(env_path)

        assert exc_info.value.code == 1

    def test_preserves_existing_env_content(self, tmp_path: Path):
        """既存 .env の内容を保持したまま追記すること。"""
        env_path = tmp_path / ".env"
        env_path.write_text("EXISTING_KEY=existing_value\n")

        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", return_value="new_google_key"):
                _ensure_api_keys(env_path)

        content = env_path.read_text()
        assert "EXISTING_KEY=existing_value" in content
        assert "GOOGLE_API_KEY=new_google_key" in content

    def test_ignores_comments_in_env(self, tmp_path: Path):
        """コメント行を保持すること。"""
        env_path = tmp_path / ".env"
        env_path.write_text("# This is a comment\nSOME_KEY=value\n")

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "google"}, clear=True):
            _ensure_api_keys(env_path)

        content = env_path.read_text()
        assert "# This is a comment" in content

    def test_creates_parent_directories(self, tmp_path: Path):
        """親ディレクトリを自動作成すること。"""
        env_path = tmp_path / "nested" / "dir" / ".env"

        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", return_value="google_key"):
                _ensure_api_keys(env_path)

        assert env_path.exists()
        assert env_path.parent.exists()

    def test_strips_whitespace_from_input(self, tmp_path: Path):
        """入力前後の空白を除去すること。"""
        env_path = tmp_path / ".env"

        with patch.dict(os.environ, {}, clear=True):
            with patch("builtins.input", return_value="  google_key_with_spaces  "):
                _ensure_api_keys(env_path)

            assert os.environ.get("GOOGLE_API_KEY") == "google_key_with_spaces"

        assert "GOOGLE_API_KEY=google_key_with_spaces" in env_path.read_text()
