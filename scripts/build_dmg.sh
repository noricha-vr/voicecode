#!/bin/bash
# VoiceCode の配布用 DMG を作成
#
# 前提:
#   uv pip install py2app
#
# 使用方法:
#   ./scripts/build_dmg.sh
#
# 出力:
#   dist/VoiceCode-{version}.dmg

set -e

cd "$(dirname "$0")/.."

VERSION=$(grep '^version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')
APP_NAME="VoiceCode"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"

echo "=== Building VoiceCode.app ==="

# 既存のビルドをクリーンアップ
rm -rf build dist

# py2app でビルド
uv run python setup_py2app.py py2app

echo ""
echo "=== Creating DMG ==="

# 一時ディレクトリを作成
DMG_DIR="dist/dmg"
mkdir -p "$DMG_DIR"

# .app をコピー
cp -R "dist/${APP_NAME}.app" "$DMG_DIR/"

# Applications へのシンボリックリンクを作成
ln -s /Applications "$DMG_DIR/Applications"

# README を追加
cat > "$DMG_DIR/README.txt" << 'EOF'
VoiceCode - macOS 音声入力ツール

インストール方法:
1. VoiceCode.app を Applications フォルダにドラッグ
2. 初回起動時に macOS 権限を許可:
   - アクセシビリティ
   - 入力監視
   - マイク

設定:
~/.voicecode/.env に API キーを設定してください:
  GROQ_API_KEY=your_key
  OPENROUTER_API_KEY=your_key

ホットキー:
デフォルトは F15 キー（~/.voicecode/settings.json で変更可能）
EOF

# DMG を作成
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$DMG_DIR" \
    -ov -format UDZO \
    "dist/$DMG_NAME"

# 一時ディレクトリを削除
rm -rf "$DMG_DIR"

echo ""
echo "=== Build Complete ==="
echo "DMG: dist/$DMG_NAME"
echo ""
echo "注意: 配布前にコード署名と公証が必要です（Apple Developer アカウント要）"
