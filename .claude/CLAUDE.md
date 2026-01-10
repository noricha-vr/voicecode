# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

| 項目 | 値 |
|------|-----|
| Python | 3.13 |
| パッケージ管理 | uv |
| ホットキー | F15（~/.voicecode/settings.json で設定） |
| 文字起こし | Groq Whisper (whisper-large-v3-turbo) |
| 後処理 | Gemini 2.5 Flash Lite (OpenRouter) |

## プロジェクト概要

macOS 用の音声入力ツール。ホットキー1回で録音→文字起こし→LLM後処理→貼り付けを自動実行する。プログラミング用語のカタカナを英語表記に自動変換する機能が特徴。

## コマンド

```bash
# 依存関係インストール
uv sync

# 実行
uv run python main.py

# テスト実行
uv run pytest tests/

# 単一テストファイル実行
uv run pytest tests/test_postprocessor.py

# 特定テスト実行
uv run pytest tests/test_postprocessor.py::TestPostProcessor::test_process_success -v

# サービス開始
launchctl load ~/Library/LaunchAgents/com.voicecode.plist

# サービス停止
launchctl unload ~/Library/LaunchAgents/com.voicecode.plist

# ログ確認
tail -f ~/.voicecode/voicecode.log

# ビルド（シェルラッパー版 - 個人利用向け）
./scripts/build_app.sh

# ビルド（py2app版 - 配布向け）
uv run python setup_py2app.py py2app
```

詳細なビルド手順は `docs/build.md` を参照。

## 環境変数

`.env` に以下を設定:
- `GROQ_API_KEY` - Groq Whisper API キー
- `OPENROUTER_API_KEY` - OpenRouter API キー

## アーキテクチャ

```
録音 (pynput/sounddevice) → Whisper (Groq) → Gemini (OpenRouter) → 貼り付け (pyautogui)
```

### モジュール構成

| ファイル | 責務 |
|----------|------|
| `main.py` | エントリポイント、キーボード監視、統合処理 |
| `recorder.py` | 音声録音 (sounddevice) |
| `transcriber.py` | 文字起こし (Groq Whisper API) |
| `postprocessor.py` | LLM後処理 (Gemini 2.5 Flash Lite)、用語変換辞書 |

### 処理フロー

1. `VoiceInputTool` がホットキー監視 (pynput)
2. `AudioRecorder` が WAV 録音 (16kHz, モノラル)
3. `Transcriber` が Groq Whisper で文字起こし
4. `PostProcessor` が Gemini でプログラミング用語補正
5. pyperclip でクリップボードコピー、pyautogui で Cmd+V

## 設計パターン

- 各モジュールは単一責務（録音/文字起こし/後処理）
- API クライアントはコンストラクタで初期化
- 一時ファイル（WAV）は処理後に自動削除
- テストは `unittest.mock` で API モック化

### rumps と PyObjC の併用

```
rumps（高レベルAPI）→ 内部で PyObjC を使用
PyObjC（低レベルAPI）→ rumps で足りない部分を補完
```

| レイヤー | カバー範囲 |
|----------|-----------|
| rumps | メニューバーアプリ基本構造、メニュー項目、通知、タイマー |
| PyObjC | クリップボード操作、システムサウンド、その他 macOS ネイティブ API |

**設計原則**:
- rumps をベースにして、rumps でできないことだけ PyObjC で補う
- rumps 内部で PyObjC を使用しているため、両者は同じイベントループを共有
- PyObjC の直接使用は最小限に抑え、rumps の機能を優先する

## macOS 権限要件

システム設定 > プライバシーとセキュリティ で以下を許可:
- アクセシビリティ（ターミナル）
- 入力監視（ターミナル）
- マイク（ターミナル）

## スキル/コマンド

| 名前 | 種類 | 用途 |
|------|------|------|
| fix-voice | Skill + Command | 音声認識の誤変換をユーザー辞書または同音異義語に登録 |
