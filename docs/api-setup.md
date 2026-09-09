# API キー取得ガイド

VoiceCode で使用する API キーの取得方法を解説します。

## はじめに

VoiceCode は以下の 2 つの API を使用します。

| API | 用途 | 特徴 |
|-----|------|------|
| Groq Whisper | 音声からテキストへの変換（文字起こし） | 高速・高精度・無料枠あり |
| OpenRouter (Gemini) | テキストの後処理（用語補正） | 複数 LLM に統一 API でアクセス |

### なぜこの組み合わせなのか

1. **Groq Whisper**: Whisper large-v3-turbo モデルを超高速で実行できる。無料枠が十分にあり、個人利用では課金不要なケースが多い。

2. **OpenRouter 経由の Gemini**: OpenRouter は複数の LLM プロバイダに統一された API でアクセスできるサービス。Gemini を直接使う場合と比べて、将来的に別のモデルに切り替えやすく、料金比較も容易。

---

## Groq API キーの取得

Groq は高速な推論サービスを提供するプラットフォームで、Whisper モデルを使った文字起こしが可能です。

### 無料枠について

| 項目 | 無料枠 |
|------|--------|
| リクエスト数 | 14,400 リクエスト/日 |
| オーディオ時間 | 28,800 秒/日（約 8 時間） |

**1 日 8 時間分の音声を無料で処理できます。** 通常の音声入力で 1 日 8 時間も話し続けることはないため、無料枠を超えることはまずありません。

### 取得手順

1. Groq Console にアクセス
   - URL: https://console.groq.com/keys

2. アカウントを作成
   - 「Sign Up」をクリック
   - Google アカウントまたは GitHub アカウントでログイン可能
   - メールアドレスでの登録も可能

3. API キーを発行
   - ログイン後、左メニューから「API Keys」を選択
   - 「Create API Key」ボタンをクリック
   - キーの名前を入力（例: voicecode）
   - 「Submit」をクリック

4. API キーをコピー
   - 表示された API キー（gsk_ で始まる文字列）をコピー
   - このキーは一度しか表示されないので、必ず控えておく

---

## OpenRouter API キーの取得

### OpenRouter とは

OpenRouter は、複数の LLM プロバイダ（OpenAI、Anthropic、Google、Meta など）に統一された API でアクセスできるサービスです。

#### なぜ Gemini を直接使わないのか

- **統一 API**: プロバイダごとに異なる API 仕様を覚える必要がない
- **モデル切り替え**: 設定変更だけで別のモデルに切り替え可能
- **料金透明性**: 各モデルの料金を同じ画面で比較できる
- **クレジット管理**: 複数プロバイダを一元管理

### 無料枠について

OpenRouter には無料で使えるモデルが多数あります。VoiceCode で使用する Gemini 系モデルも無料枠が十分にあります。

- **無料モデル**: Gemini 2.0 Flash Experimental など、完全無料で使えるモデルあり
- **低コストモデル**: Gemini 2.5 Flash Lite は 100 万トークンあたり数セントと非常に低コスト

VoiceCode の後処理は短いテキストを扱うだけなので、無料枠を超えることはほぼありません。

### 取得手順

1. OpenRouter にアクセス
   - URL: https://openrouter.ai/keys

2. アカウントを作成
   - 「Sign In」をクリック
   - Google アカウントまたは GitHub アカウントでログイン可能
   - メールアドレスでの登録も可能

3. API キーを発行
   - ログイン後、右上のアカウントメニューから「Keys」を選択
   - 「Create Key」ボタンをクリック
   - キーの名前を入力（例: voicecode）
   - 「Create」をクリック

4. API キーをコピー
   - 表示された API キー（sk-or- で始まる文字列）をコピー
   - このキーは一度しか表示されないので、必ず控えておく

---

## VoiceCode への設定方法

### 方法 1: 初回起動時に入力

1. VoiceCode を起動

   ```bash
   uv run python main.py
   # または
   voicecode
   ```

2. プロンプトに従って API キーを入力
   - Groq API キー: gsk_ で始まる文字列を入力
   - OpenRouter API キー: sk-or- で始まる文字列を入力

3. 入力した API キーは `~/.voicecode/.env` に自動保存される

### 方法 2: 事前に .env ファイルで設定

1. 設定ディレクトリを作成

   ```bash
   mkdir -p ~/.voicecode
   ```

2. .env ファイルを作成

   ```bash
   cat > ~/.voicecode/.env << 'EOF'
   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxxxxx
   EOF
   ```

3. 各 API キーを実際の値に置き換える

4. VoiceCode を起動

   ```bash
   uv run python main.py
   ```

---

## トラブルシューティング

### API キーが認識されない

**症状**: 起動時に「API キーが設定されていません」と表示される

**対処法**:
1. `~/.voicecode/.env` ファイルが存在するか確認

   ```bash
   cat ~/.voicecode/.env
   ```

2. API キーの形式を確認
   - Groq: `gsk_` で始まる
   - OpenRouter: `sk-or-` で始まる

3. 余分なスペースや改行がないか確認

4. ファイルを再作成

   ```bash
   rm ~/.voicecode/.env
   # VoiceCode を再起動して API キーを再入力
   ```

### レート制限エラー

**症状**: 「Rate limit exceeded」「Too many requests」などのエラー

**Groq の場合**:
- 無料枠の上限に達した可能性がある
- 24 時間待つと制限がリセットされる
- https://console.groq.com/usage で使用量を確認

**OpenRouter の場合**:
- クレジットが不足している可能性がある
- https://openrouter.ai/credits でクレジット残高を確認
- 必要に応じてクレジットを追加

### 「Invalid API key」エラー

**対処法**:
1. API キーが正しくコピーされているか確認
2. API キーが無効化されていないか確認（各サービスの管理画面で確認）
3. 新しい API キーを発行して再設定

### ネットワークエラー

**症状**: 「Connection error」「Timeout」などのエラー

**対処法**:
1. インターネット接続を確認
2. プロキシやファイアウォールの設定を確認
3. 時間をおいて再試行（サービス側の一時的な障害の可能性）
