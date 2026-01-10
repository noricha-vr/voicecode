"""録音機能のテスト。"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import sounddevice as sd

from recorder import AudioRecorder, RecordingConfig


class TestRecordingConfig:
    """RecordingConfigのテスト。"""

    def test_default_values(self):
        """デフォルト値が正しいこと。"""
        config = RecordingConfig()
        assert config.sample_rate == 16000
        assert config.channels == 1
        assert config.dtype == "int16"
        assert config.max_duration == 60

    def test_custom_values(self):
        """カスタム値を設定できること。"""
        config = RecordingConfig(sample_rate=44100, channels=2, dtype="float32", max_duration=30)
        assert config.sample_rate == 44100
        assert config.channels == 2
        assert config.dtype == "float32"
        assert config.max_duration == 30


class TestAudioRecorder:
    """AudioRecorderのテスト。"""

    def test_init_default_config(self):
        """デフォルト設定で初期化できること。"""
        recorder = AudioRecorder()
        assert recorder.config.sample_rate == 16000
        assert recorder.config.channels == 1
        assert not recorder.is_recording
        assert not recorder.is_timeout
        assert recorder._max_duration == 60

    def test_init_custom_config(self):
        """カスタム設定で初期化できること。"""
        config = RecordingConfig(sample_rate=44100, max_duration=30)
        recorder = AudioRecorder(config)
        assert recorder.config.sample_rate == 44100
        assert recorder._max_duration == 30

    @patch("recorder.sd.InputStream")
    def test_start_recording(self, mock_stream_class):
        """録音を開始できること。"""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start()

        assert recorder.is_recording
        assert recorder._start_time is not None
        assert not recorder.is_timeout
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


class TestAudioRecorderTimeout:
    """AudioRecorderのタイムアウト機能のテスト。"""

    def test_is_timeout_property_initial_value(self):
        """is_timeoutの初期値がFalseであること。"""
        recorder = AudioRecorder()
        assert not recorder.is_timeout

    @patch("recorder.sd.InputStream")
    def test_start_resets_timeout_flag(self, mock_stream_class):
        """start()がtimeoutフラグをリセットすること。"""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()
        recorder._timeout_reached = True  # 手動でフラグを設定

        recorder.start()

        assert not recorder.is_timeout

    @patch("recorder.sd.InputStream")
    @patch("recorder.time.time")
    def test_callback_timeout_detection(self, mock_time, mock_stream_class):
        """コールバックでタイムアウトが検出されること。"""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        # 短いmax_durationを設定
        config = RecordingConfig(max_duration=1)
        recorder = AudioRecorder(config)

        # time.time()の戻り値を制御
        # start()時に0を返し、コールバック時に2を返す（1秒のmax_durationを超過）
        mock_time.side_effect = [0.0, 2.0]

        recorder.start()

        # InputStreamに渡されたコールバックを取得
        call_kwargs = mock_stream_class.call_args.kwargs
        callback = call_kwargs["callback"]

        # コールバックを呼び出す（タイムアウト状態）
        indata = np.zeros((1000,), dtype=np.int16)
        with pytest.raises(sd.CallbackAbort):
            callback(indata, 1000, {}, None)

        assert recorder.is_timeout

    @patch("recorder.sd.InputStream")
    @patch("recorder.time.time")
    def test_callback_no_timeout_within_duration(self, mock_time, mock_stream_class):
        """max_duration内ではタイムアウトしないこと。"""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        config = RecordingConfig(max_duration=60)
        recorder = AudioRecorder(config)

        # start()時に0を返し、コールバック時に30を返す（60秒のmax_duration未満）
        mock_time.side_effect = [0.0, 30.0]

        recorder.start()

        # InputStreamに渡されたコールバックを取得
        call_kwargs = mock_stream_class.call_args.kwargs
        callback = call_kwargs["callback"]

        # コールバックを呼び出す（タイムアウトしない）
        indata = np.zeros((1000,), dtype=np.int16)
        callback(indata, 1000, {}, None)

        assert not recorder.is_timeout
        assert len(recorder._frames) == 1

    @patch("recorder.sd.InputStream")
    @patch("recorder.time.time")
    def test_callback_timeout_at_exact_duration(self, mock_time, mock_stream_class):
        """ちょうどmax_duration時にタイムアウトすること。"""
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        config = RecordingConfig(max_duration=10)
        recorder = AudioRecorder(config)

        # start()時に0を返し、コールバック時に10を返す（ちょうどmax_duration）
        mock_time.side_effect = [0.0, 10.0]

        recorder.start()

        # InputStreamに渡されたコールバックを取得
        call_kwargs = mock_stream_class.call_args.kwargs
        callback = call_kwargs["callback"]

        # コールバックを呼び出す（タイムアウト状態）
        indata = np.zeros((1000,), dtype=np.int16)
        with pytest.raises(sd.CallbackAbort):
            callback(indata, 1000, {}, None)

        assert recorder.is_timeout

    @patch("recorder.sd.InputStream")
    def test_stop_resets_timeout_flag(self, mock_stream_class):
        """stop()がtimeoutフラグをリセットすること。

        タイムアウトで録音が停止した後、is_timeoutがFalseにリセットされることを確認。
        これにより、_check_timeout()が繰り返し_stop_and_process()を呼び出すバグを防止。
        """
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream

        recorder = AudioRecorder()
        recorder.start()

        # タイムアウトが発生した状態をシミュレート
        recorder._timeout_reached = True
        recorder._frames = [np.zeros((1000,), dtype=np.int16)]

        # stop()を呼び出す
        result = recorder.stop()

        # タイムアウトフラグがリセットされていること
        assert not recorder.is_timeout
        assert not recorder.is_recording

        # クリーンアップ
        result.unlink()
