# API キー取得ガイド（Gemini 単独構成）

VoiceCode は Gemini Flash を使って、音声入力から直接文字起こしを行います。  
必要な API キーは `GOOGLE_API_KEY` のみです。

## 1. Google API キーを取得する

1. Google AI Studio の API キーページを開く  
   URL: https://aistudio.google.com/apikey
2. Google アカウントでログイン
3. `Create API key` を選択してキーを発行
4. 表示されたキーをコピーして保管

## 2. VoiceCode に設定する

### 方法 A: 初回起動時に入力（推奨）

```bash
uv run python main.py
```

起動時に `Google API キー` の入力を求められます。  
入力したキーは `~/.voicecode/.env` に自動保存されます。

### 方法 B: 事前に .env へ設定

```bash
mkdir -p ~/.voicecode
cat > ~/.voicecode/.env << 'EOF'
GOOGLE_API_KEY=your_google_api_key
# 任意: 利用モデルを固定したい場合
# VOICECODE_GEMINI_MODEL=gemini-2.5-flash
EOF
```

## 3. 動作確認

1. `uv run python main.py` を実行
2. 録音して話す
3. Gemini で文字起こしされ、アクティブな入力欄に貼り付けされることを確認

## トラブルシューティング

### API キーが認識されない

1. `~/.voicecode/.env` が存在するか確認
2. `GOOGLE_API_KEY=...` の形式か確認
3. 余計な空白・改行がないか確認

### タイムアウト / 接続エラー

1. ネットワーク接続を確認
2. 時間をおいて再実行
3. Google 側ステータスを確認

### 文字起こし結果が期待と違う

1. `~/.voicecode/dictionary.txt` に用語辞書を追加
2. 録音環境（マイク位置・ノイズ）を確認
