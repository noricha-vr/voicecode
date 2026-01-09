"""履歴保存機能のテスト。"""

import json
import wave
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from history import HistoryEntry, HistoryManager, _get_audio_duration


class TestHistoryEntry:
    """HistoryEntryモデルのテスト。"""

    def test_create_entry(self):
        """エントリを正しく作成できること。"""
        entry = HistoryEntry(
            timestamp="2025-01-09T15:30:00",
            raw_transcription="クロードコードで実装して",
            processed_text="Claude Codeで実装して",
            audio_file="2025-01-09_153000.wav",
            duration_sec=3.2,
        )

        assert entry.timestamp == "2025-01-09T15:30:00"
        assert entry.raw_transcription == "クロードコードで実装して"
        assert entry.processed_text == "Claude Codeで実装して"
        assert entry.audio_file == "2025-01-09_153000.wav"
        assert entry.duration_sec == 3.2

    def test_model_dump(self):
        """モデルをdictにダンプできること。"""
        entry = HistoryEntry(
            timestamp="2025-01-09T15:30:00",
            raw_transcription="テスト",
            processed_text="テスト",
            audio_file="test.wav",
            duration_sec=1.0,
        )

        data = entry.model_dump()

        assert data["timestamp"] == "2025-01-09T15:30:00"
        assert data["raw_transcription"] == "テスト"
        assert data["processed_text"] == "テスト"
        assert data["audio_file"] == "test.wav"
        assert data["duration_sec"] == 1.0


class TestGetAudioDuration:
    """_get_audio_duration関数のテスト。"""

    def test_returns_duration_for_valid_wav(self, tmp_path):
        """有効なWAVファイルの長さを取得できること。"""
        # テスト用WAVファイルを作成
        wav_path = tmp_path / "test.wav"
        sample_rate = 16000
        duration_sec = 2.5
        frames = int(sample_rate * duration_sec)

        audio_data = np.zeros(frames, dtype=np.int16)

        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

        result = _get_audio_duration(wav_path)

        assert result == 2.5

    def test_returns_zero_for_nonexistent_file(self, tmp_path):
        """存在しないファイルの場合は0.0を返すこと。"""
        wav_path = tmp_path / "nonexistent.wav"

        result = _get_audio_duration(wav_path)

        assert result == 0.0

    def test_returns_zero_for_invalid_file(self, tmp_path):
        """不正なファイルの場合は0.0を返すこと。"""
        invalid_path = tmp_path / "invalid.wav"
        invalid_path.write_text("not a wav file")

        result = _get_audio_duration(invalid_path)

        assert result == 0.0


class TestHistoryManager:
    """HistoryManagerのテスト。"""

    def test_init_default_directory(self):
        """デフォルトの履歴ディレクトリが設定されること。"""
        manager = HistoryManager()

        assert manager._history_dir == Path.home() / ".voicecode" / "history"

    def test_init_custom_directory(self, tmp_path):
        """カスタム履歴ディレクトリを設定できること。"""
        custom_dir = tmp_path / "custom_history"
        manager = HistoryManager(history_dir=custom_dir)

        assert manager._history_dir == custom_dir

    def test_ensure_directory_creates_dir(self, tmp_path):
        """ディレクトリが存在しない場合に作成されること。"""
        history_dir = tmp_path / "history"
        manager = HistoryManager(history_dir=history_dir)

        assert not history_dir.exists()

        manager._ensure_directory()

        assert history_dir.exists()

    def test_ensure_directory_handles_existing_dir(self, tmp_path):
        """ディレクトリが既に存在する場合もエラーにならないこと。"""
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        manager = HistoryManager(history_dir=history_dir)

        manager._ensure_directory()

        assert history_dir.exists()

    def test_generate_filename(self, tmp_path):
        """ファイル名が正しく生成されること。"""
        manager = HistoryManager(history_dir=tmp_path)
        timestamp = datetime(2025, 1, 9, 15, 30, 0)

        filename = manager._generate_filename(timestamp)

        assert filename == "2025-01-09_153000"

    def test_save_creates_audio_and_json_files(self, tmp_path):
        """音声ファイルとJSONファイルが作成されること。"""
        history_dir = tmp_path / "history"
        manager = HistoryManager(history_dir=history_dir)

        # テスト用WAVファイルを作成
        audio_path = tmp_path / "temp.wav"
        sample_rate = 16000
        frames = int(sample_rate * 1.5)
        audio_data = np.zeros(frames, dtype=np.int16)

        with wave.open(str(audio_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

        # 固定のタイムスタンプを使用
        fixed_datetime = datetime(2025, 1, 9, 15, 30, 0)
        with patch("history.datetime") as mock_datetime:
            mock_datetime.now.return_value = fixed_datetime

            result = manager.save(
                audio_path=audio_path,
                raw_transcription="クロードコードで実装して",
                processed_text="Claude Codeで実装して",
            )

        assert result is not None
        assert result.name == "2025-01-09_153000.json"

        # JSONファイルの内容を確認
        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["timestamp"] == "2025-01-09T15:30:00"
        assert data["raw_transcription"] == "クロードコードで実装して"
        assert data["processed_text"] == "Claude Codeで実装して"
        assert data["audio_file"] == "2025-01-09_153000.wav"
        assert data["duration_sec"] == 1.5

        # 音声ファイルがコピーされていることを確認
        copied_audio = history_dir / "2025-01-09_153000.wav"
        assert copied_audio.exists()

    def test_save_creates_directory_if_not_exists(self, tmp_path):
        """履歴保存時にディレクトリが自動作成されること。"""
        history_dir = tmp_path / "nested" / "history"
        manager = HistoryManager(history_dir=history_dir)

        # テスト用WAVファイルを作成
        audio_path = tmp_path / "temp.wav"
        sample_rate = 16000
        frames = int(sample_rate * 1.0)
        audio_data = np.zeros(frames, dtype=np.int16)

        with wave.open(str(audio_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

        assert not history_dir.exists()

        result = manager.save(
            audio_path=audio_path,
            raw_transcription="テスト",
            processed_text="テスト",
        )

        assert result is not None
        assert history_dir.exists()

    def test_save_returns_none_on_error(self, tmp_path):
        """エラー時にNoneを返し、主処理は継続されること。"""
        history_dir = tmp_path / "history"
        manager = HistoryManager(history_dir=history_dir)

        # 存在しないファイルパスを指定
        nonexistent_path = tmp_path / "nonexistent.wav"

        result = manager.save(
            audio_path=nonexistent_path,
            raw_transcription="テスト",
            processed_text="テスト",
        )

        assert result is None

    def test_save_preserves_original_audio_file(self, tmp_path):
        """元の音声ファイルが削除されないこと。"""
        history_dir = tmp_path / "history"
        manager = HistoryManager(history_dir=history_dir)

        # テスト用WAVファイルを作成
        audio_path = tmp_path / "temp.wav"
        sample_rate = 16000
        frames = int(sample_rate * 1.0)
        audio_data = np.zeros(frames, dtype=np.int16)

        with wave.open(str(audio_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

        manager.save(
            audio_path=audio_path,
            raw_transcription="テスト",
            processed_text="テスト",
        )

        # 元のファイルが存在することを確認
        assert audio_path.exists()

    def test_save_handles_unicode_text(self, tmp_path):
        """Unicode文字を含むテキストを正しく保存できること。"""
        history_dir = tmp_path / "history"
        manager = HistoryManager(history_dir=history_dir)

        # テスト用WAVファイルを作成
        audio_path = tmp_path / "temp.wav"
        sample_rate = 16000
        frames = int(sample_rate * 1.0)
        audio_data = np.zeros(frames, dtype=np.int16)

        with wave.open(str(audio_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

        result = manager.save(
            audio_path=audio_path,
            raw_transcription="日本語テキスト",
            processed_text="Japanese text",
        )

        # JSONファイルの内容を確認
        with open(result, encoding="utf-8") as f:
            data = json.load(f)

        assert data["raw_transcription"] == "日本語テキスト"
        assert data["processed_text"] == "Japanese text"
