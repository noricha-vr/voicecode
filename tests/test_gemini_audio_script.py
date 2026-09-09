"""過去音声のGemini診断スクリプトを検証する。"""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import os
import wave
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


def _create_wav(path: Path, mtime: int = 100) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16_000)
        wav_file.writeframes(b"\x00\x00" * 16)
    os.utime(path, (mtime, mtime))


def _response(text: str) -> io.BytesIO:
    payload = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


def test_find_history_audio_files_returns_newest_first(tmp_path):
    old_file = tmp_path / "old.wav"
    new_file = tmp_path / "new.wav"
    _create_wav(old_file, 100)
    _create_wav(new_file, 200)

    assert script.find_history_audio_files(tmp_path) == [new_file, old_file]


@pytest.mark.parametrize('index,expected_name', [(0, 'new.wav'), (1, 'old.wav')])
def test_main_selects_history_audio_without_explicit_file(monkeypatch, tmp_path, index, expected_name):
    _create_wav(tmp_path / 'old.wav', 100)
    _create_wav(tmp_path / 'new.wav', 200)
    monkeypatch.setenv('TEST_GEMINI_KEY', 'test-api-key')
    selected = []

    def fake_transcription(audio_path, model, api_key):
        selected.append(audio_path.name)
        return '合成結果', 0.1

    monkeypatch.setattr(script, 'run_transcription', fake_transcription)
    args = ['--model', 'gemini-test-fixed', '--history-dir', str(tmp_path),
            '--api-key-env', 'TEST_GEMINI_KEY']
    if index:
        args.extend(['--history-index', str(index)])
    assert script.main(args) == 0
    assert selected == [expected_name]


@pytest.mark.parametrize('index,has_audio', [(-1, True), (1, True), (0, False)])
def test_invalid_history_does_not_call_api(monkeypatch, tmp_path, index, has_audio):
    if has_audio:
        _create_wav(tmp_path / 'synthetic.wav')
    monkeypatch.setenv('TEST_GEMINI_KEY', 'test-api-key')
    monkeypatch.setattr(script, 'run_transcription', lambda *args, **kwargs: pytest.fail('API must not run'))
    assert script.main(['--model', 'gemini-test-fixed', '--history-dir', str(tmp_path),
                        '--history-index', str(index), '--api-key-env', 'TEST_GEMINI_KEY']) == 1


def test_missing_model_stops_before_reading_audio_or_http(monkeypatch, tmp_path):
    monkeypatch.setattr(script, 'run_transcription', lambda *args, **kwargs: pytest.fail('HTTP must not run'))
    with pytest.raises(SystemExit) as exc:
        script.main(['--history-dir', str(tmp_path)])
    assert exc.value.code == 2


@pytest.mark.parametrize('model', ['', '../other', 'gemini?key=value'])
def test_invalid_model_stops_before_http(tmp_path, model):
    path = tmp_path / 'synthetic.wav'
    _create_wav(path)
    with pytest.raises(ValueError, match='モデル名'):
        script.run_transcription(path, model=model, api_key='test-api-key',
                                 opener=lambda *args, **kwargs: pytest.fail('HTTP must not run'))


def test_resolve_audio_path_accepts_matching_history_json(tmp_path):
    wav_path = tmp_path / "sample.wav"
    _create_wav(wav_path)
    json_path = tmp_path / "sample.json"
    json_path.write_text("{}", encoding="utf-8")

    assert script.resolve_audio_path(json_path, tmp_path, 0) == wav_path


def test_run_transcription_uses_only_explicit_model_and_mock_http(tmp_path):
    wav_path = tmp_path / "synthetic.wav"
    _create_wav(wav_path)
    calls = []

    def fake_open(request, timeout):
        calls.append((request, timeout))
        return _response("合成音声の結果")

    text, _elapsed = script.run_transcription(
        wav_path,
        model="gemini-test-fixed",
        api_key="test-api-key",
        opener=fake_open,
    )

    request, timeout = calls[0]
    request_payload = json.loads(request.data)
    inline_audio = request_payload["contents"][0]["parts"][1]["inlineData"]["data"]
    assert text == "合成音声の結果"
    assert len(calls) == 1
    assert "/models/gemini-test-fixed:generateContent" in request.full_url
    assert request.headers["X-goog-api-key"] == "test-api-key"
    assert timeout == script.DEFAULT_TIMEOUT_SECONDS
    assert base64.b64decode(inline_audio) == wav_path.read_bytes()


def test_run_transcription_does_not_retry_or_switch_models(tmp_path):
    wav_path = tmp_path / "synthetic.wav"
    _create_wav(wav_path)
    calls = []

    def failing_open(request, timeout):
        calls.append((request, timeout))
        raise RuntimeError("synthetic failure")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        script.run_transcription(
            wav_path,
            model="gemini-test-fixed",
            api_key="test-api-key",
            opener=failing_open,
        )
    assert len(calls) == 1


def test_main_requires_api_key_without_calling_http(monkeypatch, tmp_path, capsys):
    wav_path = tmp_path / "synthetic.wav"
    _create_wav(wav_path)
    monkeypatch.delenv("MISSING_GEMINI_KEY", raising=False)
    monkeypatch.setattr(
        script,
        "run_transcription",
        lambda *args, **kwargs: pytest.fail("HTTP呼び出しは実行されない"),
    )

    result = script.main(
        [
            "--model",
            "gemini-test-fixed",
            "--audio",
            str(wav_path),
            "--api-key-env",
            "MISSING_GEMINI_KEY",
        ]
    )

    assert result == 1
    assert "MISSING_GEMINI_KEY" in capsys.readouterr().err


def test_main_reports_history_comparison(monkeypatch, tmp_path, capsys):
    wav_path = tmp_path / "synthetic.wav"
    _create_wav(wav_path)
    wav_path.with_suffix(".json").write_text(
        json.dumps({"processed_text": "期待結果"}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setenv("TEST_GEMINI_KEY", "test-api-key")
    monkeypatch.setattr(
        script,
        "run_transcription",
        lambda audio_path, model, api_key: ("期待結果", 0.25),
    )

    result = script.main(
        [
            "--model",
            "gemini-test-fixed",
            "--audio",
            str(wav_path),
            "--api-key-env",
            "TEST_GEMINI_KEY",
        ]
    )

    output = capsys.readouterr().out
    assert result == 0
    assert "履歴比較: 一致" in output
    assert "[OK]" in output
