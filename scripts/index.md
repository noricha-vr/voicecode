# scripts/

一時スクリプト・ユーティリティスクリプトの格納ディレクトリ。

| ファイル | 説明 |
|----------|------|
| `start.sh` | LaunchAgent 用起動スクリプト |
| `build_app.sh` | シェルラッパー版 .app ビルドスクリプト（個人利用向け） |
| `build_dmg.sh` | py2app ビルド + DMG 作成スクリプト（配布向け） |
| `sign_and_notarize.sh` | コード署名と公証スクリプト（Apple Developer アカウント要） |
| `generate_formula.sh` | Homebrew Formula の SHA256 計算ヘルパー |
| `generate_icons.py` | メニューバーアイコン PNG 生成スクリプト |
| `test_gemini_audio.py` | 履歴音声を明示したGeminiモデルへ再送する診断スクリプト |

## Geminiで履歴音声を診断する

本体の文字起こし・後処理設定には影響しません。課金対象のAPI呼び出しを行うため、モデル名を毎回明示します。

```bash
GOOGLE_API_KEY=... uv run python scripts/test_gemini_audio.py \
  --model gemini-2.5-flash \
  --history-index 0
```
