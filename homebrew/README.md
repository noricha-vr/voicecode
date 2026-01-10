# VoiceCode Homebrew Tap

VoiceCode を Homebrew 経由でインストールするための Formula です。

## インストール方法

```bash
# Tap を追加（初回のみ）
brew tap noricha-vr/voicecode https://github.com/noricha-vr/voicecode

# インストール
brew install noricha-vr/voicecode/voicecode
```

または、ワンライナーでインストール:

```bash
brew install noricha-vr/voicecode/voicecode
```

## 使用方法

```bash
# 起動
voicecode

# ログイン時に自動起動
brew services start voicecode

# 自動起動を停止
brew services stop voicecode

# ステータス確認
brew services info voicecode
```

## 前提条件

- macOS 専用
- Python 3.13（自動インストール）
- PortAudio（自動インストール）

## macOS 権限設定

初回起動前に、以下の権限を許可してください:

1. **システム設定 > プライバシーとセキュリティ > アクセシビリティ**
   - VoiceCode（またはターミナル）を追加
2. **システム設定 > プライバシーとセキュリティ > 入力監視**
   - VoiceCode（またはターミナル）を追加
3. **システム設定 > プライバシーとセキュリティ > マイク**
   - VoiceCode（またはターミナル）を追加

## API キー設定

`~/.voicecode/.env` を作成し、以下を設定:

```bash
GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## アップデート

```bash
brew update
brew upgrade voicecode
```

## アンインストール

```bash
# サービスを停止
brew services stop voicecode

# アンインストール
brew uninstall voicecode

# Tap を削除（オプション）
brew untap noricha-vr/voicecode
```

## トラブルシューティング

### 権限エラーが出る

システム設定で必要な権限（アクセシビリティ、入力監視、マイク）を確認してください。

### ホットキーが反応しない

デフォルトのホットキーは **F15** です。`~/.voicecode/settings.json` で変更できます:

```json
{
  "hotkey": "ctrl+shift+r"
}
```

### ログを確認する

```bash
# brew services 経由で起動した場合
tail -f /opt/homebrew/var/log/voicecode.log

# 直接起動した場合
tail -f /tmp/voicecode.log
```

## 開発者向け

### Formula の更新

1. `pyproject.toml` のバージョンを更新
2. GitHub でリリースタグを作成（例: `v0.2.0`）
3. SHA256 を計算:
   ```bash
   ./scripts/generate_formula.sh 0.2.0
   ```
4. `homebrew/voicecode.rb` の `url` と `sha256` を更新

### ローカルテスト

```bash
# Formula の構文チェック
brew audit --strict homebrew/voicecode.rb

# ローカルでインストールテスト
brew install --build-from-source homebrew/voicecode.rb
```

### head バージョンのインストール

開発版（main ブランチの最新）をインストール:

```bash
brew install --head noricha-vr/voicecode/voicecode
```
