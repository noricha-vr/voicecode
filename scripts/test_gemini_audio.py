#!/usr/bin/env python3
"""Gemini APIで過去履歴の音声を再文字起こしして動作確認する。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from transcriber import Transcriber


DEFAULT_HISTORY_DIR = Path.home() / ".voicecode" / "history"
DEFAULT_ENV_FILE = Path.home() / ".voicecode" / ".env"


def build_parser() -> argparse.ArgumentParser:
    """CLI引数パーサを返す。"""
    parser = argparse.ArgumentParser(
        description="過去の履歴音声をGemini APIで再文字起こしして動作確認する",
    )
    parser.add_argument(
        "--audio",
        type=Path,
        help="検証に使うWAVまたはJSONのパス。未指定なら履歴から選択",
    )
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=DEFAULT_HISTORY_DIR,
        help="履歴ディレクトリ（デフォルト: ~/.voicecode/history）",
    )
    parser.add_argument(
        "--history-index",
        type=int,
        default=0,
        help="履歴の新しい順インデックス（0=最新、1=ひとつ前）",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help="APIキーを読み込む.envファイル（デフォルト: ~/.voicecode/.env）",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="GOOGLE_API_KEY を直接指定（指定時は環境変数より優先）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="VOICECODE_GEMINI_MODEL に設定するモデル名（例: gemini-2.5-flash）",
    )
    return parser


def find_history_audio_files(history_dir: Path) -> list[Path]:
    """履歴ディレクトリ内のWAV一覧を新しい順で返す。"""
    if not history_dir.exists():
        raise FileNotFoundError(f"履歴ディレクトリが見つかりません: {history_dir}")

    wav_files = list(history_dir.glob("*.wav"))
    wav_files.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    return wav_files


def select_history_audio(history_dir: Path, history_index: int) -> Path:
    """履歴から指定インデックスのWAVを選ぶ。"""
    if history_index < 0:
        raise ValueError(f"--history-index は0以上で指定してください: {history_index}")

    wav_files = find_history_audio_files(history_dir)
    if not wav_files:
        raise FileNotFoundError(f"WAVファイルが見つかりません: {history_dir}")
    if history_index >= len(wav_files):
        raise IndexError(
            f"--history-index={history_index} は範囲外です。利用可能件数: {len(wav_files)}"
        )
    return wav_files[history_index]


def resolve_audio_path(audio: Path | None, history_dir: Path, history_index: int) -> Path:
    """CLI引数から検証対象のWAVパスを解決する。"""
    if audio is None:
        return select_history_audio(history_dir, history_index)

    candidate = audio.expanduser()
    if candidate.suffix.lower() == ".json":
        candidate = candidate.with_suffix(".wav")

    if not candidate.exists():
        raise FileNotFoundError(f"音声ファイルが見つかりません: {candidate}")
    return candidate


def load_expected_transcription(audio_path: Path) -> str | None:
    """履歴JSONから既存文字起こし結果を読み込む。"""
    json_path = audio_path.with_suffix(".json")
    if not json_path.exists():
        return None

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    for key in ("processed_text", "raw_transcription"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def run_transcription(audio_path: Path, api_key: str | None) -> tuple[str, float]:
    """Transcriberを使って文字起こしする。"""
    transcriber = Transcriber(api_key=api_key)
    return transcriber.transcribe(audio_path)


def main(argv: list[str] | None = None) -> int:
    """エントリポイント。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.model:
        os.environ["VOICECODE_GEMINI_MODEL"] = args.model

    load_dotenv(dotenv_path=args.env_file.expanduser(), override=False)

    try:
        audio_path = resolve_audio_path(args.audio, args.history_dir.expanduser(), args.history_index)
        expected = load_expected_transcription(audio_path)
        transcription, elapsed = run_transcription(audio_path, api_key=args.api_key)
    except Exception as exc:
        print(f"[NG] 検証に失敗しました: {exc}", file=sys.stderr)
        return 1

    print(f"[INFO] 音声ファイル: {audio_path}")
    print(f"[INFO] 文字起こし: {transcription}")
    print(f"[INFO] 処理時間: {elapsed:.2f}s")

    if not transcription.strip():
        print("[NG] APIレスポンスが空でした。", file=sys.stderr)
        return 1

    if expected:
        status = "一致" if transcription.strip() == expected else "差分あり"
        print(f"[INFO] 履歴比較: {status}")

    print("[OK] API経由の過去音声検証に成功しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
