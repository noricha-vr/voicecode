#!/bin/bash
# VoiceCode.app の署名と公証
#
# 前提:
#   - Apple Developer アカウント
#   - Developer ID Application 証明書
#   - App Specific Password
#
# 環境変数:
#   APPLE_ID: Apple ID メールアドレス
#   TEAM_ID: Developer Team ID
#   APP_PASSWORD: App Specific Password
#
# 使用方法:
#   ./scripts/sign_and_notarize.sh

set -e

cd "$(dirname "$0")/.."

APP_PATH="dist/VoiceCode.app"
VERSION=$(grep '^version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/')
DMG_NAME="VoiceCode-${VERSION}.dmg"

# 環境変数チェック
if [ -z "$APPLE_ID" ] || [ -z "$TEAM_ID" ] || [ -z "$APP_PASSWORD" ]; then
    echo "Error: 以下の環境変数を設定してください:"
    echo "  APPLE_ID: Apple ID メールアドレス"
    echo "  TEAM_ID: Developer Team ID"
    echo "  APP_PASSWORD: App Specific Password"
    exit 1
fi

echo "=== Signing ==="

# 署名
codesign --force --deep --sign "Developer ID Application" "$APP_PATH"

# 署名確認
codesign --verify --verbose "$APP_PATH"

echo ""
echo "=== Creating signed DMG ==="

# DMG を作成（署名済み .app を含む）
rm -rf dist/dmg
mkdir -p dist/dmg
cp -R "$APP_PATH" dist/dmg/
ln -s /Applications dist/dmg/Applications

hdiutil create -volname "VoiceCode" \
    -srcfolder dist/dmg \
    -ov -format UDZO \
    "dist/$DMG_NAME"

rm -rf dist/dmg

echo ""
echo "=== Notarizing ==="

# 公証
xcrun notarytool submit "dist/$DMG_NAME" \
    --apple-id "$APPLE_ID" \
    --team-id "$TEAM_ID" \
    --password "$APP_PASSWORD" \
    --wait

# ステープル
xcrun stapler staple "dist/$DMG_NAME"

echo ""
echo "=== Complete ==="
echo "Signed and notarized: dist/$DMG_NAME"
