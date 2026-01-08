# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

| 項目 | 値 |
|------|-----|
| Python | 3.13 |
| パッケージ管理 | uv |
| ホットキー | F13（.envで変更可能） |
| 文字起こし | Groq Whisper (whisper-large-v3-turbo) |
| 後処理 | Claude 3.5 Haiku |

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
tail -f /tmp/voicecode.log
```

## 環境変数

`.env` に以下を設定:
- `GROQ_API_KEY` - Groq Whisper API キー
- `ANTHROPIC_API_KEY` - Anthropic Claude API キー

## アーキテクチャ

```
録音 (pynput/sounddevice) → Whisper (Groq) → Claude (Anthropic) → 貼り付け (pyautogui)
```

### モジュール構成

| ファイル | 責務 |
|----------|------|
| `main.py` | エントリポイント、キーボード監視、統合処理 |
| `recorder.py` | 音声録音 (sounddevice) |
| `transcriber.py` | 文字起こし (Groq Whisper API) |
| `postprocessor.py` | LLM後処理 (Claude Haiku)、用語変換辞書 |

### 処理フロー

1. `VoiceInputTool` がホットキー監視 (pynput)
2. `AudioRecorder` が WAV 録音 (16kHz, モノラル)
3. `Transcriber` が Groq Whisper で文字起こし
4. `PostProcessor` が Claude でプログラミング用語補正
5. pyperclip でクリップボードコピー、pyautogui で Cmd+V

## 設計パターン

- 各モジュールは単一責務（録音/文字起こし/後処理）
- API クライアントはコンストラクタで初期化
- 一時ファイル（WAV）は処理後に自動削除
- テストは `unittest.mock` で API モック化

## macOS 権限要件

システム設定 > プライバシーとセキュリティ で以下を許可:
- アクセシビリティ（ターミナル）
- 入力監視（ターミナル）
- マイク（ターミナル）
