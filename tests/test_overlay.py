"""オーバーレイウィンドウのテスト。"""

from unittest.mock import MagicMock, patch

import pytest


class TestRecordingOverlay:
    """RecordingOverlayのテスト。"""

    @patch("overlay._OverlayHelper")
    def test_init(self, mock_helper_class):
        """初期化時にウィンドウがNoneでヘルパーが作成されること。"""
        mock_helper = MagicMock()
        mock_helper_class.alloc.return_value.initWithOverlay_.return_value = mock_helper

        with patch.dict(
            "sys.modules",
            {"AppKit": MagicMock(), "Foundation": MagicMock(), "objc": MagicMock()},
        ):
            from overlay import RecordingOverlay

            overlay = RecordingOverlay()
            assert overlay._window is None
            assert overlay._helper == mock_helper

    @patch("overlay._OverlayHelper")
    def test_show_calls_helper_show(self, mock_helper_class):
        """show()がヘルパーのshow()を呼び出すこと。"""
        mock_helper = MagicMock()
        mock_helper_class.alloc.return_value.initWithOverlay_.return_value = mock_helper

        with patch.dict(
            "sys.modules",
            {"AppKit": MagicMock(), "Foundation": MagicMock(), "objc": MagicMock()},
        ):
            from overlay import RecordingOverlay

            overlay = RecordingOverlay()
            overlay.show()

            mock_helper.show.assert_called_once()

    @patch("overlay._OverlayHelper")
    def test_hide_calls_helper_hide(self, mock_helper_class):
        """hide()がヘルパーのhide()を呼び出すこと。"""
        mock_helper = MagicMock()
        mock_helper_class.alloc.return_value.initWithOverlay_.return_value = mock_helper

        with patch.dict(
            "sys.modules",
            {"AppKit": MagicMock(), "Foundation": MagicMock(), "objc": MagicMock()},
        ):
            from overlay import RecordingOverlay

            overlay = RecordingOverlay()
            overlay.hide()

            mock_helper.hide.assert_called_once()

    @patch("overlay._OverlayHelper")
    @patch("overlay.NSScreen")
    @patch("overlay.NSTextField")
    @patch("overlay.NSWindow")
    @patch("overlay.NSMakeRect")
    @patch("overlay.NSColor")
    @patch("overlay.NSFont")
    @patch("overlay.NSBackingStoreBuffered", 2)
    @patch("overlay.NSFloatingWindowLevel", 3)
    def test_create_and_show_creates_window(
        self,
        mock_font,
        mock_color,
        mock_make_rect,
        mock_window_class,
        mock_textfield_class,
        mock_screen,
        mock_helper_class,
    ):
        """_create_and_show()がウィンドウを作成すること。"""
        # ヘルパーのモックセットアップ
        mock_helper = MagicMock()
        mock_helper_class.alloc.return_value.initWithOverlay_.return_value = mock_helper

        # ウィンドウのモックセットアップ
        mock_window = MagicMock()
        mock_window_class.alloc.return_value.initWithContentRect_styleMask_backing_defer_.return_value = (
            mock_window
        )
        mock_window.contentView.return_value = MagicMock()

        mock_label = MagicMock()
        mock_textfield_class.alloc.return_value.initWithFrame_.return_value = mock_label

        mock_screen_frame = MagicMock()
        mock_screen_frame.size.width = 1920
        mock_screen_frame.size.height = 1080
        mock_screen.mainScreen.return_value.frame.return_value = mock_screen_frame

        mock_make_rect.return_value = "frame"

        from overlay import RecordingOverlay

        overlay = RecordingOverlay()
        overlay._create_and_show()

        # ウィンドウが作成されたことを確認
        assert overlay._window is not None
        mock_window.setLevel_.assert_called_once()
        mock_window.setOpaque_.assert_called_once_with(False)
        mock_window.setHasShadow_.assert_called_once_with(True)
        mock_window.makeKeyAndOrderFront_.assert_called_once_with(None)

    @patch("overlay._OverlayHelper")
    def test_do_hide_with_no_window(self, mock_helper_class):
        """ウィンドウがない状態で_do_hide()を呼んでもエラーにならないこと。"""
        mock_helper = MagicMock()
        mock_helper_class.alloc.return_value.initWithOverlay_.return_value = mock_helper

        with patch.dict(
            "sys.modules",
            {"AppKit": MagicMock(), "Foundation": MagicMock(), "objc": MagicMock()},
        ):
            from overlay import RecordingOverlay

            overlay = RecordingOverlay()
            overlay._window = None

            # エラーなく実行できること
            overlay._do_hide()

            assert overlay._window is None

    @patch("overlay._OverlayHelper")
    def test_do_hide_with_window(self, mock_helper_class):
        """ウィンドウがある状態で_do_hide()がorderOut_を呼び出すこと。"""
        mock_helper = MagicMock()
        mock_helper_class.alloc.return_value.initWithOverlay_.return_value = mock_helper

        with patch.dict(
            "sys.modules",
            {"AppKit": MagicMock(), "Foundation": MagicMock(), "objc": MagicMock()},
        ):
            from overlay import RecordingOverlay

            overlay = RecordingOverlay()
            mock_window = MagicMock()
            overlay._window = mock_window

            overlay._do_hide()

            mock_window.orderOut_.assert_called_once_with(None)
            assert overlay._window is None
