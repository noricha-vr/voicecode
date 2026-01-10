# VoiceCode ビルド手順

## 概要

VoiceCode は2種類の方法で .app にパッケージ化できます。

| 方式 | 用途 | 特徴 |
|------|------|------|
| シェルラッパー | 個人利用 | 高速ビルド、デバッグ容易、更新簡単 |
| py2app | 配布 | スタンドアロン、他のマシンで動作 |

## シェルラッパー版（個人利用向け）

Python 環境をそのまま使い、シェルスクリプトで .app をラップする方式。

### ビルド

```bash
./scripts/build_app.sh
```

### 出力

- `~/Applications/VoiceCode.app`

### 特徴

- ビルド時間: 数秒
- 起動速度: 高速（1-2秒）
- 更新方法: `git pull` するだけ（再ビルド不要）
- 依存: プロジェクトディレクトリの `.venv` が必要

### 制限事項

- 他のマシンには配布不可
- プロジェクトディレクトリを移動すると動作しない

## py2app 版（配布向け）

Python インタプリタと依存関係をすべて含むスタンドアロン .app を作成。

### 前提条件

```bash
uv pip install py2app
```

### ビルド

```bash
uv run python setup_py2app.py py2app
```

### 出力

- `dist/VoiceCode.app`

### 特徴

- ビルド時間: 数分
- 起動速度: 初回は遅い（5-10秒）
- 配布: 他のマシンでも動作
- サイズ: 大きい（100MB+）

### コード署名・公証（配布時）

他のユーザーに配布する場合、Apple Developer アカウント（$99/年）が必要。

```bash
# 署名
codesign --force --deep --sign "Developer ID Application: YOUR NAME" dist/VoiceCode.app

# 公証
xcrun notarytool submit dist/VoiceCode.app.zip \
    --apple-id "your@email.com" \
    --team-id "TEAMID" \
    --password "app-specific-password" \
    --wait

# ステープル
xcrun stapler staple dist/VoiceCode.app
```

## launchctl での自動起動（既存設定）

既に `~/Library/LaunchAgents/com.voicecode.plist` が設定済みの場合、ログイン時に自動起動します。

```bash
# 有効化
launchctl load ~/Library/LaunchAgents/com.voicecode.plist

# 無効化
launchctl unload ~/Library/LaunchAgents/com.voicecode.plist

# ログ確認
tail -f /tmp/voicecode.log
```

## macOS 権限設定

初回起動時に以下の権限を許可する必要があります:

1. システム設定 > プライバシーとセキュリティ > アクセシビリティ
2. システム設定 > プライバシーとセキュリティ > 入力監視
3. システム設定 > プライバシーとセキュリティ > マイク

.app から起動する場合は `VoiceCode.app` を追加してください。
