# voicecode

macOS用の音声入力ツール。ホットキー1回で音声入力から文字起こし、LLM後処理、貼り付けまでを自動化する。

## 特徴

- **ワンキー操作**: F15（カスタマイズ可能）で録音開始/停止をトグル
- **高速文字起こし**: Groq Whisper (whisper-large-v3-turbo) による高精度な音声認識
- **プログラミング用語の自動補正**: Gemini 2.5 Flash Lite (OpenRouter) でカタカナを英語表記に変換
- **シームレスな入力**: 自動でクリップボードにコピー&貼り付け
- **メニューバー常駐**: 状態アイコン（■/●/↻）で録音状態を確認
- **効果音フィードバック**: 録音開始・停止・完了時に効果音でお知らせ
- **録音時間制限**: 最大60秒で自動停止（API使用量の抑制）

## クイックスタート

```bash
# セットアップ
cp .env.example .env
# .env を編集して API キーを設定

# 手動実行
uv run python main.py

# バックグラウンドサービスとして常駐（オプション）
cp com.voicecode.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.voicecode.plist
```

## セットアップ詳細

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集して API キーを設定:

```bash
GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
HOTKEY=f15  # ホットキー（デフォルト: f15、例: ctrl+shift+r）
```

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

1. **録音開始**: F15 を押す（デフォルト、`.env` の `HOTKEY` で変更可能）
2. **話す**: マイクに向かって話す
3. **録音停止**: F15 を再度押す
4. **自動処理**: 文字起こし → 後処理 → 貼り付けが実行される

終了するには Ctrl+C を押す。メニューバーから「終了」を選択しても停止できる。

## 状態表示

メニューバーのアイコンで現在の状態を確認できます。

| アイコン | 状態 |
|----------|------|
| ■ | 待機中（録音可能） |
| ● | 録音中 |
| ↻ | 処理中（文字起こし・後処理） |

## 効果音

| タイミング | 効果音 |
|------------|--------|
| 録音開始 | Tink |
| 録音停止 | Pop |
| 処理完了 | Glass |
| エラー | Basso |

## バックグラウンドサービスとして実行

Mac起動時に自動でvoicecodeを常駐させる場合:

### 1. plistをコピー
```bash
cp com.voicecode.plist ~/Library/LaunchAgents/
```

### 2. サービスを開始
```bash
launchctl load ~/Library/LaunchAgents/com.voicecode.plist
```

### 3. サービスを停止
```bash
launchctl unload ~/Library/LaunchAgents/com.voicecode.plist
```

### ログ確認
```bash
tail -f /tmp/voicecode.log
```

## 変換例

| 音声認識結果 | 変換後 |
|-------------|--------|
| リアクト | React |
| タイプスクリプト | TypeScript |
| ネクストJS | Next.js |
| ユースステート | useState |
| クロード | Claude |
| パイソン | Python |
| ジャバスクリプト | JavaScript |

## アーキテクチャ

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐
│  録音   │ -> │ Whisper │ -> │  Gemini │ -> │ 貼り付け │
│ (音声) │    │ (文字)  │    │ (修正)  │    │          │
└─────────┘    └─────────┘    └─────────┘    └──────────┘
     |              |              |              |
  pynput      Groq API      OpenRouter      pyautogui
 sounddevice                   API          pyperclip
```

### 処理フロー

1. **録音** (recorder.py): pynput でホットキーを監視、sounddevice で音声を録音
2. **文字起こし** (transcriber.py): Groq Whisper API で音声をテキストに変換
3. **後処理** (postprocessor.py): Gemini 2.5 Flash Lite (OpenRouter) でプログラミング用語を補正
4. **貼り付け** (main.py): pyperclip でクリップボードにコピー、pyautogui で Cmd+V

## ファイル構成

```
voicecode/
├── main.py           # エントリポイント、キーボード監視と統合処理
├── recorder.py       # 音声録音モジュール
├── transcriber.py    # Groq Whisper による文字起こし
├── postprocessor.py  # Claude による後処理
├── requirements.txt  # 依存関係
├── .env.example      # 環境変数テンプレート
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

- `.env` ファイルの API キーが正しく設定されているか確認
- API の利用制限に達していないか確認
- ネットワーク接続を確認

### 音声が正しく認識されない

- マイクに近づいて話す
- 静かな環境で使用する
- はっきりと発音する

## 注意事項

- 録音は最大60秒で自動停止します
- メニューバーから「終了」で停止できます
