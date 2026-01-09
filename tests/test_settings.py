"""設定管理機能のテスト。"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from settings import Settings


class TestSettings:
    """Settings クラスのテスト。"""

    def test_default_values(self):
        """デフォルト値が正しく設定されていること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            settings = Settings(config_dir=config_dir)

            assert settings.hotkey == "f15"
            assert settings.restore_clipboard is True

    def test_load_from_file(self):
        """ファイルから設定を読み込めること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "settings.json"

            # 設定ファイルを作成
            config_file.write_text(
                json.dumps({"hotkey": "f12", "restore_clipboard": False}),
                encoding="utf-8",
            )

            settings = Settings(config_dir=config_dir)

            assert settings.hotkey == "f12"
            assert settings.restore_clipboard is False

    def test_save_creates_directory(self):
        """save() がディレクトリを自動作成すること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            settings = Settings(config_dir=config_dir)
            settings.hotkey = "f10"
            settings.save()

            assert config_dir.exists()
            assert (config_dir / "settings.json").exists()

    def test_save_and_load(self):
        """設定を保存して再読み込みできること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"

            # 設定を保存
            settings1 = Settings(config_dir=config_dir)
            settings1.hotkey = "ctrl+shift+r"
            settings1.restore_clipboard = False
            settings1.save()

            # 新しいインスタンスで読み込み
            settings2 = Settings(config_dir=config_dir)

            assert settings2.hotkey == "ctrl+shift+r"
            assert settings2.restore_clipboard is False

    def test_hotkey_setter_normalizes_case(self):
        """hotkey setter が小文字に正規化すること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            settings = Settings(config_dir=config_dir)

            settings.hotkey = "CTRL+SHIFT+R"

            assert settings.hotkey == "ctrl+shift+r"

    def test_hotkey_setter_strips_whitespace(self):
        """hotkey setter が空白を除去すること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            settings = Settings(config_dir=config_dir)

            settings.hotkey = "  f15  "

            assert settings.hotkey == "f15"

    def test_restore_clipboard_setter(self):
        """restore_clipboard setter が動作すること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            settings = Settings(config_dir=config_dir)

            settings.restore_clipboard = False
            assert settings.restore_clipboard is False

            settings.restore_clipboard = True
            assert settings.restore_clipboard is True

    def test_load_handles_missing_file(self):
        """存在しないファイルの場合にデフォルト値を使用すること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            settings = Settings(config_dir=config_dir)

            assert settings.hotkey == "f15"
            assert settings.restore_clipboard is True

    def test_load_handles_invalid_json(self):
        """不正なJSONファイルの場合にデフォルト値を使用すること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "settings.json"
            config_file.write_text("invalid json", encoding="utf-8")

            settings = Settings(config_dir=config_dir)

            assert settings.hotkey == "f15"
            assert settings.restore_clipboard is True

    def test_load_handles_partial_config(self):
        """一部の設定のみ含むファイルを読み込めること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "settings.json"

            # hotkey のみ設定
            config_file.write_text(
                json.dumps({"hotkey": "f12"}),
                encoding="utf-8",
            )

            settings = Settings(config_dir=config_dir)

            assert settings.hotkey == "f12"
            assert settings.restore_clipboard is True  # デフォルト値

    def test_load_ignores_invalid_types(self):
        """不正な型の値を無視すること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "settings.json"

            # 不正な型
            config_file.write_text(
                json.dumps({"hotkey": 123, "restore_clipboard": "yes"}),
                encoding="utf-8",
            )

            settings = Settings(config_dir=config_dir)

            assert settings.hotkey == "f15"  # デフォルト値
            assert settings.restore_clipboard is True  # デフォルト値

    def test_to_dict(self):
        """to_dict() が正しい辞書を返すこと。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            settings = Settings(config_dir=config_dir)
            settings.hotkey = "f12"
            settings.restore_clipboard = False

            result = settings.to_dict()

            assert result == {
                "hotkey": "f12",
                "restore_clipboard": False,
            }

    def test_default_constants(self):
        """デフォルト定数が正しいこと。"""
        assert Settings.DEFAULT_HOTKEY == "f15"
        assert Settings.DEFAULT_RESTORE_CLIPBOARD is True


class TestSettingsIntegration:
    """Settings の統合テスト。"""

    def test_multiple_saves_overwrite(self):
        """複数回の保存で上書きされること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            settings = Settings(config_dir=config_dir)

            settings.hotkey = "f10"
            settings.save()

            settings.hotkey = "f11"
            settings.save()

            # 新しいインスタンスで確認
            settings2 = Settings(config_dir=config_dir)
            assert settings2.hotkey == "f11"

    def test_file_format(self):
        """保存されるファイルの形式が正しいこと。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".voicecode"
            settings = Settings(config_dir=config_dir)
            settings.hotkey = "ctrl+r"
            settings.restore_clipboard = True
            settings.save()

            config_file = config_dir / "settings.json"
            content = config_file.read_text(encoding="utf-8")
            data = json.loads(content)

            assert data == {
                "hotkey": "ctrl+r",
                "restore_clipboard": True,
            }

    def test_config_dir_path(self):
        """デフォルトの設定ディレクトリパスが正しいこと。"""
        with patch.object(Path, "home", return_value=Path("/home/testuser")):
            settings = Settings.__new__(Settings)
            settings._config_dir = None
            settings._config_file = None
            settings._hotkey = Settings.DEFAULT_HOTKEY
            settings._restore_clipboard = Settings.DEFAULT_RESTORE_CLIPBOARD

            # __init__ を手動で呼び出さずに確認
            expected_dir = Path("/home/testuser") / ".voicecode"

            # 実際に初期化した場合のパスを確認
            with tempfile.TemporaryDirectory() as tmpdir:
                mock_home = Path(tmpdir)
                with patch.object(Path, "home", return_value=mock_home):
                    settings = Settings()
                    assert settings._config_dir == mock_home / ".voicecode"
                    assert settings._config_file == mock_home / ".voicecode" / "settings.json"
