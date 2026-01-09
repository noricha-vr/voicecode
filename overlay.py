"""録音中オーバーレイウィンドウモジュール。"""

import logging

import objc
from AppKit import (
    NSWindow,
    NSColor,
    NSFont,
    NSFloatingWindowLevel,
    NSBackingStoreBuffered,
    NSScreen,
    NSTextField,
    NSMakeRect,
)
from Foundation import NSObject

logger = logging.getLogger(__name__)


class _OverlayHelper(NSObject):
    """メインスレッドでオーバーレイ操作を実行するヘルパークラス。"""

    def initWithOverlay_(self, overlay):
        """ヘルパーを初期化する。"""
        self = objc.super(_OverlayHelper, self).init()
        if self is None:
            return None
        self._overlay = overlay
        return self

    @objc.python_method
    def show(self):
        """オーバーレイを表示する（メインスレッドで実行）。"""
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "doShow", None, False
        )

    @objc.python_method
    def hide(self):
        """オーバーレイを非表示にする（メインスレッドで実行）。"""
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "doHide", None, False
        )

    def doShow(self):
        """実際の表示処理。"""
        logger.debug("doShow() called on main thread")
        self._overlay._create_and_show()

    def doHide(self):
        """実際の非表示処理。"""
        logger.debug("doHide() called on main thread")
        self._overlay._do_hide()


class RecordingOverlay:
    """録音中オーバーレイウィンドウ。"""

    def __init__(self):
        """RecordingOverlayを初期化する。"""
        self._window = None
        self._helper = _OverlayHelper.alloc().initWithOverlay_(self)

    def show(self):
        """オーバーレイを表示する。"""
        logger.debug("show() called")
        self._helper.show()

    def hide(self):
        """オーバーレイを非表示にする。"""
        logger.debug("hide() called")
        self._helper.hide()

    def _create_and_show(self):
        """ウィンドウを作成して表示する（メインスレッドで実行）。"""
        frame = NSMakeRect(0, 0, 200, 60)
        # NSBorderlessWindowMask = 0
        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, 0, NSBackingStoreBuffered, False
        )
        self._window.setLevel_(NSFloatingWindowLevel)
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(
            NSColor.colorWithRed_green_blue_alpha_(0.2, 0.2, 0.2, 0.9)
        )
        self._window.setHasShadow_(True)

        # ラベル追加
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 15, 200, 30))
        label.setStringValue_("Recording...")
        label.setEditable_(False)
        label.setBordered_(False)
        label.setBackgroundColor_(NSColor.clearColor())
        label.setTextColor_(NSColor.whiteColor())
        label.setAlignment_(1)  # NSCenterTextAlignment = 1
        label.setFont_(NSFont.systemFontOfSize_(18))
        self._window.contentView().addSubview_(label)

        # 画面中央上部に配置
        screen = NSScreen.mainScreen().frame()
        x = (screen.size.width - 200) / 2
        y = screen.size.height - 100
        self._window.setFrameOrigin_((x, y))

        # ウィンドウを表示
        self._window.makeKeyAndOrderFront_(None)
        logger.debug("Window displayed with makeKeyAndOrderFront_")

    def _do_hide(self):
        """ウィンドウを非表示にする（メインスレッドで実行）。"""
        if self._window:
            self._window.orderOut_(None)
            self._window = None
            logger.debug("Window hidden")
