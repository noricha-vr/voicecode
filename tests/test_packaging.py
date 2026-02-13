"""パッケージング設定のテスト。"""

import tomllib
from pathlib import Path


def test_hatch_build_includes_icon_assets():
    """wheel ビルドにアイコン画像が含まれること。"""
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        pyproject = tomllib.load(f)

    include_patterns = pyproject["tool"]["hatch"]["build"]["include"]
    assert "assets/*.png" in include_patterns
