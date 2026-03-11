"""scripts/test_gemini_audio.py のテスト。"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest


def _load_script_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "test_gemini_audio.py"
    spec = importlib.util.spec_from_file_location("voicecode_test_gemini_audio_script", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = _load_script_module()


def _create_wav(path: Path, mtime: int) -> None:
    path.write_bytes(b"wav")
    os.utime(path, (mtime, mtime))


def test_find_history_audio_files_returns_newest_first(tmp_path):
    old_file = tmp_path / "old.wav"
    new_file = tmp_path / "new.wav"
    _create_wav(old_file, 100)
    _create_wav(new_file, 200)

    result = script.find_history_audio_files(tmp_path)

    assert result == [new_file, old_file]


def test_select_history_audio_raises_on_out_of_range(tmp_path):
    _create_wav(tmp_path / "only.wav", 100)

    with pytest.raises(IndexError, match="範囲外"):
        script.select_history_audio(tmp_path, history_index=1)


def test_resolve_audio_path_accepts_json_path(tmp_path):
    wav_path = tmp_path / "sample.wav"
    json_path = tmp_path / "sample.json"
    _create_wav(wav_path, 100)
    json_path.write_text("{}", encoding="utf-8")

    resolved = script.resolve_audio_path(json_path, tmp_path, history_index=0)

    assert resolved == wav_path


def test_load_expected_transcription_prefers_processed_text(tmp_path):
    wav_path = tmp_path / "sample.wav"
    _create_wav(wav_path, 100)
    wav_path.with_suffix(".json").write_text(
        json.dumps(
            {
                "raw_transcription": "らう",
                "processed_text": "プロセス済み",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert script.load_expected_transcription(wav_path) == "プロセス済み"


def test_main_success(monkeypatch, tmp_path, capsys):
    wav_path = tmp_path / "sample.wav"
    _create_wav(wav_path, 100)
    wav_path.with_suffix(".json").write_text(
        json.dumps({"processed_text": "成功テキスト"}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(script, "run_transcription", lambda audio_path, api_key: ("成功テキスト", 0.42))

    result = script.main(
        [
            "--audio",
            str(wav_path),
            "--env-file",
            str(tmp_path / "missing.env"),
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "[OK]" in captured.out


def test_main_fails_on_empty_transcription(monkeypatch, tmp_path, capsys):
    wav_path = tmp_path / "sample.wav"
    _create_wav(wav_path, 100)

    monkeypatch.setattr(script, "run_transcription", lambda audio_path, api_key: ("", 0.42))

    result = script.main(
        [
            "--audio",
            str(wav_path),
            "--env-file",
            str(tmp_path / "missing.env"),
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "空でした" in captured.err
