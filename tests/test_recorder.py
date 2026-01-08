"""録音機能のテスト。"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from recorder import AudioRecorder, RecordingConfig


class TestRecordingConfig:
    """RecordingConfigのテスト。"""

    def test_default_values(self):
        """デフォルト値が正しいこと。"""
        config = RecordingConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.dtype == "int16"

    def test_custom_values(self):
        """カスタム値を設定できること。"""
        config = RecordingConfig(sample_rate=44100, channels=2, dtype="float32")
        assert config.sample_rate == 44100
        assert config.channels == 2
        assert config.dtype == "float32"


class TestAudioRecorder:
    """AudioRecorderのテスト。"""

    def test_init_default_config(self):
        """デフォルト設定で初期化できること。"""
        recorder = AudioRecorder()
        assert recorder.config.sample_rate == 16000
        assert recorder.config.channels == 1
        assert not recorder.is_recording

    def test_init_custom_config(self):
        """カスタム設定で初期化できること。"""
        config = RecordingConfig(sample_rate=44100)
        recorder = AudioRecorder(config)
        assert recorder.config.sample_rate == 44100

    @patch("recorder.sd.InputStream")
    def test_start_recording(self, mock_stream_class):
        """録音を開始できること。"""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start()

        assert recorder.is_recording
        mock_stream.start.assert_called_once()

    @patch("recorder.sd.InputStream")
    def test_start_already_recording_raises_error(self, mock_stream_class):
        """既に録音中の場合にエラーが発生すること。"""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start()

        with pytest.raises(RuntimeError, match="Already recording"):
            recorder.start()

    def test_stop_not_recording_raises_error(self):
        """録音中でない場合にエラーが発生すること。"""
        recorder = AudioRecorder()

        with pytest.raises(RuntimeError, match="Not recording"):
            recorder.stop()

    @patch("recorder.sd.InputStream")
    def test_stop_returns_file_path(self, mock_stream_class):
        """録音停止後にファイルパスが返されること。"""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start()

        # シミュレートされた音声データを追加
        recorder._frames = [np.zeros((1000,), dtype=np.int16)]

        result = recorder.stop()

        assert isinstance(result, Path)
        assert result.suffix == ".wav"
        assert result.exists()

        # クリーンアップ
        result.unlink()

    @patch("recorder.sd.InputStream")
    def test_stop_no_audio_data_raises_error(self, mock_stream_class):
        """音声データがない場合にエラーが発生すること。"""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start()
        recorder._frames = []
        recorder._is_recording = False

        recorder._is_recording = True
        mock_stream.stop = MagicMock()
        mock_stream.close = MagicMock()

        with pytest.raises(ValueError, match="No audio data"):
            recorder.stop()
