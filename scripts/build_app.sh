#!/bin/bash
# VoiceCode.app をシェルラッパーとして作成
# 個人利用向け。Python 環境に依存するが、更新が簡単で起動が速い。

set -e

APP_NAME="VoiceCode"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="/Applications/${APP_NAME}.app"

echo "Building ${APP_NAME}.app..."
echo "Project directory: $PROJECT_DIR"

# 既存のアプリを削除
rm -rf "$APP_DIR"

# .app 構造を作成
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# 起動スクリプト
cat > "$APP_DIR/Contents/MacOS/$APP_NAME" << EOF
#!/bin/bash
cd "$PROJECT_DIR"
exec .venv/bin/python main.py
EOF
chmod +x "$APP_DIR/Contents/MacOS/$APP_NAME"

# Info.plist
cat > "$APP_DIR/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>VoiceCode</string>
    <key>CFBundleIdentifier</key>
    <string>com.voicecode.app</string>
    <key>CFBundleName</key>
    <string>VoiceCode</string>
    <key>CFBundleVersion</key>
    <string>0.1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>LSBackgroundOnly</key>
    <false/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
EOF

echo "Created: $APP_DIR"
echo ""
echo "Note: This app requires the Python environment at $PROJECT_DIR/.venv"
echo "To start the app, double-click VoiceCode.app in /Applications"
