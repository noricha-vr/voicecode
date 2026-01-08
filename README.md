# Voice Input Tool

macOS用の音声入力ツール。ホットキー1回で音声入力から文字起こし、LLM後処理、貼り付けまで完結。

## 機能

- Ctrl+Shift+R でトグル（録音開始/停止）
- Groq Whisper (whisper-large-v3-turbo) で高速文字起こし
- Claude Haiku でプログラミング用語を修正（カタカナ→英語）
- 自動でクリップボードにコピー→貼り付け

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集して API キーを設定:

```
GROQ_API_KEY=your_groq_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 3. macOS 権限の設定

システム環境設定 > セキュリティとプライバシー > プライバシー で以下を許可:

- **アクセシビリティ**: ターミナル（または使用するターミナルアプリ）
- **入力監視**: ターミナル
- **マイク**: ターミナル

## 使い方

```bash
python main.py
```

1. Ctrl+Shift+R を押して録音開始
2. 話す
3. Ctrl+Shift+R を押して録音停止
4. 自動で文字起こし→後処理→貼り付けが実行される

## LLM 後処理の変換例

| 音声認識結果 | 変換後 |
|-------------|--------|
| リアクト | React |
| タイプスクリプト | TypeScript |
| ネクストJS | Next.js |
| ユースステート | useState |
| クロード | Claude |
