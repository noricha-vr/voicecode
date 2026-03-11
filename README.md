# voicecode

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

**エンジニアのための音声入力ツール**

Claude Code や Cursor などの AI コーディングツールに、音声で指示を出せます。
一般的な音声認識ではプログラミング用語がカタカナや誤った漢字で出力されますが、VoiceCode は LLM で正しい表記に自動補正します。

## 変換例

### カタカナ → 英語表記

| 話した内容 | 音声認識 | VoiceCode |
|-----------|---------|-----------|
| ユーズステート | ユーズステート | useState |
| ドットエンブローカル | .円舞.ローカル | .env.local |
| ドットギットイグノア | ..イグノア | .gitignore |
| ティーエスコンフィグ | DSコンフィグ | tsconfig.json |
| エヌピーエム | ピーピーエム | npm |
| クーベシーティーエル | 久米シティL | kubectl |
| ケーエイツエス | ケツ | k8s |
| スベルトキット | 滑るトキット | SvelteKit |
| ネクストジェイエス | Next Chess | Next.js |

### 同音異義語の修正

| 話した内容 | 音声認識 | VoiceCode |
|-----------|---------|-----------|
| イシューを立てて | 1週を立てて | Issueを立てて |
| 上記のコードを参考に | 蒸気のコードを参考に | 上記のコードを参考に |
| 機能を実装して | 昨日を実装して | 機能を実装して |
| 改行を追加 | 開業を追加 | 改行を追加 |

## 特徴

- **低コスト**: 月額約$1（約150円）で使い放題（1日100回×30日の場合）
- **ワンキー操作**: F15（カスタマイズ可能）で録音開始/停止をトグル
- **高速文字起こし**: Gemini Flash に音声を直接入力して高精度に文字起こし
- **プログラミング用語の自動補正**: Gemini のプロンプトとユーザー辞書で技術用語を補正
- **シームレスな入力**: 自動でクリップボードにコピー&貼り付け
- **メニューバー常駐**: 状態アイコン（■/●/↻）で録音状態を確認
- **効果音フィードバック**: 録音開始・停止・完了時に効果音でお知らせ

## コスト

| サービス | 用途 | 料金 |
|----------|------|------|
| Gemini Flash（自動選択） | 文字起こし + 用語補正 | Google の料金体系に準拠 |

### 月額目安

| 使用頻度 | 月額コスト |
|----------|-----------|
| 1日10回 | 約$0.10（約15円） |
| 1日50回 | 約$0.50（約75円） |
| 1日100回 | 約$1.00（約150円） |

※ プロンプトキャッシングにより、入力トークンの大部分（約4,000トークン）は75%オフで計算されます。

## クイックスタート

```bash
# リポジトリをクローン
git clone https://github.com/noricha-vr/voicecode.git
cd voicecode

# 依存関係をインストール
uv sync

# 起動（初回は API キーの入力を求められます）
uv run python main.py
```

初回起動時に API キーを入力すると `~/.voicecode/.env` に保存されます。

## インストール方法

### pipx（推奨）

```bash
# pipx をインストール（まだの場合）
brew install pipx
pipx ensurepath

# VoiceCode をインストール
pipx install git+https://github.com/noricha-vr/voicecode.git

# 起動
voicecode
```

### uv tool

```bash
# uv をインストール（まだの場合）
brew install uv

# VoiceCode を実行
uv tool run --from git+https://github.com/noricha-vr/voicecode.git voicecode
```

## セットアップ詳細

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. API キーの設定

初回起動時に API キーの入力を求められます。入力した API キーは `~/.voicecode/.env` に自動保存されます。

事前に設定したい場合は `~/.voicecode/.env` を作成:

```bash
mkdir -p ~/.voicecode
cat > ~/.voicecode/.env << EOF
GOOGLE_API_KEY=your_google_api_key
# 任意: 利用モデルを固定したい場合
# VOICECODE_GEMINI_MODEL=gemini-2.5-flash
EOF
```

API キーの取得先:
- Google AI Studio: https://aistudio.google.com/apikey
- 詳細な取得手順: [docs/api-setup.md](docs/api-setup.md)

ホットキーはメニューバーの「ホットキー設定...」から変更できます。設定は `~/.voicecode/settings.json` に保存されます。

## 設定

設定ファイル `~/.voicecode/settings.json` で以下の項目を設定できます。

```json
{
    "hotkey": "f15",
    "restore_clipboard": true,
    "max_recording_duration": 120
}
```

| 設定項目 | 説明 | デフォルト値 |
|----------|------|-------------|
| hotkey | 録音開始/停止のホットキー | f15 |
| restore_clipboard | 貼り付け後にクリップボードを復元 | true |
| max_recording_duration | 最大録音時間（秒、10-300） | 120 |

### 3. macOS 権限の設定

システム設定 > プライバシーとセキュリティ で以下を許可:

| 項目 | 対象アプリ |
|------|-----------|
| アクセシビリティ | ターミナル（または使用するターミナルアプリ） |
| 入力監視 | ターミナル |
| マイク | ターミナル |

## 使い方

```bash
uv run python main.py
```

1. **録音開始**: F15 を押す（デフォルト、メニューバーから変更可能）
2. **話す**: マイクに向かって話す
3. **録音停止**: F15 を再度押す
4. **自動処理**: 文字起こし（Gemini）→ 貼り付けが実行される

終了するには Ctrl+C を押す。メニューバーから「終了」を選択しても停止できる。

## 状態表示

メニューバーのアイコンで現在の状態を確認できます。

| アイコン | 状態 |
|----------|------|
| ■ | 待機中（録音可能） |
| ● | 録音中 |
| ↻ | 処理中（文字起こし） |

## 効果音

| タイミング | 効果音 |
|------------|--------|
| 録音開始 | Tink |
| 録音停止 | Pop |
| 処理完了 | Glass |
| エラー | Basso |

## バックグラウンドで実行

`-d` オプションでバックグラウンド起動できます。

```bash
uv run python main.py -d
```

ログは `~/.voicecode/voicecode.log` に出力されます。

```bash
tail -f ~/.voicecode/voicecode.log
```

## アーキテクチャ

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐
│  録音   │ -> │ Gemini  │ -> │ 貼り付け │
│ (音声) │    │ (文字)  │    │          │
└─────────┘    └─────────┘    └──────────┘
     |              |              |
  pynput       Google API     pyautogui
 sounddevice                  pyperclip
```

### 処理フロー

1. **録音** (recorder.py): pynput でホットキーを監視、sounddevice で音声を録音
2. **文字起こし** (transcriber.py): 利用可能な Gemini Flash モデルを自動選択して音声を直接テキスト化
3. **貼り付け** (main.py): pyperclip でクリップボードにコピー、pyautogui で Cmd+V

## ファイル構成

```
voicecode/
├── main.py           # エントリポイント、キーボード監視と統合処理
├── recorder.py       # 音声録音モジュール
├── transcriber.py    # Gemini Flash による文字起こし（モデル自動選択）
├── postprocessor.py  # 互換用の後処理レイヤ（現在はパススルー）
├── settings.py       # 設定管理
├── pyproject.toml    # プロジェクト設定・依存関係
├── .env.example      # 環境変数テンプレート
├── LICENSE           # MITライセンス
├── CONTRIBUTING.md   # 貢献ガイド
└── README.md
```

## トラブルシューティング

### 「アクセシビリティの許可が必要」エラー

システム設定 > プライバシーとセキュリティ > アクセシビリティ でターミナルを許可する。
許可後、ターミナルを再起動する。

### マイクが認識されない

システム設定 > プライバシーとセキュリティ > マイク でターミナルを許可する。

### ホットキーが反応しない

システム設定 > プライバシーとセキュリティ > 入力監視 でターミナルを許可する。

### 貼り付けが動作しない

システム設定 > プライバシーとセキュリティ > アクセシビリティ の許可を確認する。
一部のアプリケーションでは貼り付けがブロックされる場合がある。

### API エラーが発生する

- `~/.voicecode/.env` ファイルの API キーが正しく設定されているか確認
- API の利用制限に達していないか確認
- ネットワーク接続を確認

### 音声が正しく認識されない

- マイクに近づいて話す
- 静かな環境で使用する
- はっきりと発音する

## 注意事項

- 録音は最大120秒で自動停止します（設定で10-300秒に変更可能）
- メニューバーから「終了」で停止できます
