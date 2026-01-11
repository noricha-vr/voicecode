#!/usr/bin/env python3
"""メニューバーアイコンを生成するスクリプト。

PillowでPNGアイコンを生成する。

使用方法:
    uv run --with pillow python scripts/generate_icons.py

出力:
    assets/icon_idle.png      - グレーの丸（待機中）
    assets/icon_recording.png - 赤の丸（録音中）
    assets/icon_processing.png - オレンジの丸（処理中）
"""

from pathlib import Path

from PIL import Image, ImageDraw

# アイコンサイズ（macOSメニューバー標準）
ICON_SIZE = 22

# 色定義（RGB）
COLORS = {
    "idle": "#808080",       # グレー（待機中）
    "recording": "#FF3B30",  # 赤（録音中）
    "processing": "#FF9500", # オレンジ（処理中）
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """16進数カラーコードをRGBタプルに変換する。

    Args:
        hex_color: 16進数カラーコード（例: "#FF3B30"）

    Returns:
        RGBタプル（例: (255, 59, 48)）
    """
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def generate_icon(color_hex: str, output_path: Path) -> None:
    """円形のアイコンを生成する。

    Args:
        color_hex: 16進数カラーコード
        output_path: 出力ファイルパス
    """
    # RGBA画像を作成（透明背景）
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # 円を描画（少しマージンを取って中央に配置）
    margin = 2
    rgb = hex_to_rgb(color_hex)
    draw.ellipse(
        [margin, margin, ICON_SIZE - margin - 1, ICON_SIZE - margin - 1],
        fill=(*rgb, 255),  # 不透明
    )

    # PNG形式で保存
    image.save(output_path, "PNG")
    print(f"Generated: {output_path}")


def main() -> None:
    """アイコンを生成する。"""
    # 出力ディレクトリ
    script_dir = Path(__file__).parent
    assets_dir = script_dir.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 各状態のアイコンを生成
    icons = [
        ("idle", "icon_idle.png"),
        ("recording", "icon_recording.png"),
        ("processing", "icon_processing.png"),
    ]

    for state, filename in icons:
        output_path = assets_dir / filename
        generate_icon(COLORS[state], output_path)

    print(f"\nAll icons generated in: {assets_dir}")


if __name__ == "__main__":
    main()
