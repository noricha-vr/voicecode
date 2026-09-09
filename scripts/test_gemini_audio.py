#!/usr/bin/env python3
"""過去の履歴音声を指定したGeminiモデルで再文字起こしする。"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_HISTORY_DIR = Path.home() / ".voicecode" / "history"
DEFAULT_API_KEY_ENV = "GOOGLE_API_KEY"
DEFAULT_TIMEOUT_SECONDS = 120
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)
MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
TRANSCRIPTION_PROMPT = "音声を省略せず、そのまま日本語で文字起こししてください。"


def build_parser() -> argparse.ArgumentParser:
    """CLI引数パーサを返す。"""
    parser = argparse.ArgumentParser(
        description="過去の履歴音声を指定したGeminiモデルで再文字起こしする",
    )
    parser.add_argument("--model", required=True, help="使用するGeminiモデル名")
    parser.add_argument("--audio", type=Path, help="検証するWAVまたは履歴JSONのパス")
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
        help="履歴の新しい順インデックス（0=最新）",
    )
    parser.add_argument(
        "--api-key-env",
        default=DEFAULT_API_KEY_ENV,
        help="APIキーを読む環境変数名（デフォルト: GOOGLE_API_KEY）",
    )
    return parser


def find_history_audio_files(history_dir: Path) -> list[Path]:
    """履歴ディレクトリ内のWAVを新しい順で返す。"""
    if not history_dir.is_dir():
        raise FileNotFoundError(f"履歴ディレクトリが見つかりません: {history_dir}")
    wav_files = list(history_dir.glob("*.wav"))
    wav_files.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    return wav_files


def select_history_audio(history_dir: Path, history_index: int) -> Path:
    """履歴から指定インデックスのWAVを選ぶ。"""
    if history_index < 0:
        raise ValueError(f"--history-index は0以上で指定してください: {history_index}")
    wav_files = find_history_audio_files(history_dir)
    if history_index >= len(wav_files):
        raise IndexError(
            f"--history-index={history_index} は範囲外です。利用可能件数: {len(wav_files)}"
        )
    return wav_files[history_index]


def resolve_audio_path(audio: Path | None, history_dir: Path, history_index: int) -> Path:
    """CLI引数から検証対象のWAVを解決する。"""
    candidate = select_history_audio(history_dir, history_index) if audio is None else audio.expanduser()
    if candidate.suffix.lower() == ".json":
        candidate = candidate.with_suffix(".wav")
    if candidate.suffix.lower() != ".wav":
        raise ValueError(f"WAVファイルを指定してください: {candidate}")
    if not candidate.is_file():
        raise FileNotFoundError(f"音声ファイルが見つかりません: {candidate}")
    return candidate


def load_expected_transcription(audio_path: Path) -> str | None:
    """履歴JSONから既存の文字起こし結果を読む。"""
    json_path = audio_path.with_suffix(".json")
    if not json_path.is_file():
        return None
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    for key in ("processed_text", "raw_transcription"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def validate_model_name(model: str) -> str:
    """明示されたモデル名を検証する。"""
    if not MODEL_NAME_PATTERN.fullmatch(model):
        raise ValueError(f"モデル名の形式が不正です: {model!r}")
    return model


def build_request(audio_path: Path, model: str, api_key: str) -> Request:
    """単一モデルへのGemini APIリクエストを作る。"""
    model_name = quote(validate_model_name(model), safe="-._")
    audio_data = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": TRANSCRIPTION_PROMPT},
                    {"inlineData": {"mimeType": "audio/wav", "data": audio_data}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0},
    }
    return Request(
        GEMINI_API_URL.format(model=model_name),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-goog-api-key": api_key},
        method="POST",
    )


def extract_transcription(response: dict[str, Any]) -> str:
    """Geminiレスポンスから文字起こし本文を取り出す。"""
    try:
        parts = response["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Geminiレスポンスに文字起こし結果がありません") from exc
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    transcription = "".join(texts).strip()
    if not transcription:
        raise ValueError("Geminiレスポンスの文字起こし結果が空です")
    return transcription


def run_transcription(
    audio_path: Path,
    model: str,
    api_key: str,
    opener: Callable[..., Any] = urlopen,
) -> tuple[str, float]:
    """指定モデルを一度だけ呼び出して文字起こしする。"""
    request = build_request(audio_path, model, api_key)
    started_at = time.monotonic()
    with opener(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("GeminiレスポンスがJSONオブジェクトではありません")
    return extract_transcription(payload), time.monotonic() - started_at


def read_api_key(env_name: str) -> str:
    """指定環境変数からAPIキーを読む。"""
    if not env_name or not env_name.replace("_", "").isalnum():
        raise ValueError("--api-key-env に有効な環境変数名を指定してください")
    api_key = os.environ.get(env_name, "").strip()
    if not api_key:
        raise ValueError(f"環境変数 {env_name} にAPIキーを設定してください")
    return api_key


def main(argv: list[str] | None = None) -> int:
    """診断を実行し、成功時に0を返す。"""
    args = build_parser().parse_args(argv)
    try:
        audio_path = resolve_audio_path(args.audio, args.history_dir.expanduser(), args.history_index)
        expected = load_expected_transcription(audio_path)
        transcription, elapsed = run_transcription(
            audio_path,
            model=args.model,
            api_key=read_api_key(args.api_key_env),
        )
    except Exception as exc:
        print(f"[NG] 検証に失敗しました: {exc}", file=sys.stderr)
        return 1
    print(f"[INFO] 音声ファイル: {audio_path}")
    print(f"[INFO] 文字起こし: {transcription}")
    print(f"[INFO] 処理時間: {elapsed:.2f}s")
    if expected:
        status = "一致" if transcription == expected else "差分あり"
        print(f"[INFO] 履歴比較: {status}")
    print("[OK] API経由の過去音声検証に成功しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
