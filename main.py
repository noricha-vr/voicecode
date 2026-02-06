#!/usr/bin/env python3
"""音声入力ツールのエントリポイント。

設定されたホットキー（デフォルト: F15）で録音開始/停止をトグル。
録音停止後、文字起こし→（互換レイヤ）→クリップボードにコピー→貼り付けを実行。
メニューバーアプリとして動作し、状態をアイコンで表示する。
"""

import argparse
import sys

if sys.platform != "darwin":
    print("VoiceCode は macOS 専用です")
    sys.exit(1)

import logging
import os
import subprocess
import time
from pathlib import Path

import objc
import pyperclip
import rumps
from dotenv import load_dotenv
from Foundation import NSObject
from pynput import keyboard

from history import HistoryManager
from overlay import RecordingOverlay
from postprocessor import PostProcessor
from recorder import AudioRecorder, MicrophonePermissionError, RecordingConfig, check_microphone_permission
from settings import Settings
from transcriber import Transcriber

# 権限チェック関数


def check_input_monitoring_permission() -> bool:
    """入力監視権限をチェックする。

    pynput.keyboard.Listener を作成できるかどうかで権限を判定する。
    権限がない場合、Listener の start() で例外が発生する。

    Returns:
        権限がある場合は True、ない場合は False
    """
    try:
        listener = keyboard.Listener(on_press=lambda k: False)
        listener.start()
        listener.stop()
        return True
    except Exception:
        return False


def check_accessibility_permission() -> bool:
    """アクセシビリティ権限をチェックする。

    macOS の ApplicationServices フレームワークの AXIsProcessTrusted() を使用。

    Returns:
        権限がある場合は True、ない場合は False
    """
    try:
        from ApplicationServices import AXIsProcessTrusted
        return AXIsProcessTrusted()
    except ImportError:
        # ApplicationServices が使えない場合は True を返す（非 macOS 環境など）
        return True

# ログ設定
logger = logging.getLogger(__name__)

# ログディレクトリを作成
log_dir = Path.home() / ".voicecode"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "voicecode.log"

# コンソール出力用のハンドラを設定（各モジュールのlogger.infoを表示）
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(message)s'))

# ファイル出力用のハンドラ（デバッグ用）
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# ルートロガーに両方のハンドラを追加
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)


def _ensure_api_keys(env_path: Path) -> None:
    """API キーが設定されていない場合、入力を求めて .env に保存する。

    Args:
        env_path: .env ファイルのパス

    Raises:
        SystemExit: ユーザーが API キーを入力しなかった場合
    """
    keys_to_check = [
        ("GOOGLE_API_KEY", "Google API キー"),
    ]

    updated = False
    env_content: dict[str, str] = {}

    # 既存の .env を読み込む
    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    env_content[key.strip()] = value.strip()

    for key, label in keys_to_check:
        if not os.environ.get(key):
            print(f"\n{label} が設定されていません。")
            try:
                value = input(f"{label} を入力してください: ").strip()
            except EOFError:
                # 非対話的環境（GUI起動時など）
                print(f"[Error] {label} が必要です。終了します。")
                sys.exit(1)

            if not value:
                print("API キーは必須です。終了します。")
                sys.exit(1)

            os.environ[key] = value
            env_content[key] = value
            updated = True

    # 更新があれば .env に保存
    if updated:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        with open(env_path, "w", encoding="utf-8") as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        print(f"\nAPI キーを {env_path} に保存しました。")


def _parse_hotkey(hotkey_str: str) -> set[keyboard.Key | keyboard.KeyCode]:
    """環境変数文字列をパースしてキーセットに変換する。

    Args:
        hotkey_str: ホットキー文字列（例: "f15", "ctrl+shift+r"）

    Returns:
        pynputキーオブジェクトのセット

    Raises:
        ValueError: 無効なキー文字列の場合
    """
    modifier_map: dict[str, keyboard.Key] = {
        "ctrl": keyboard.Key.ctrl,
        "shift": keyboard.Key.shift,
        "alt": keyboard.Key.alt,
        "cmd": keyboard.Key.cmd,
    }

    keys: set[keyboard.Key | keyboard.KeyCode] = set()
    parts = hotkey_str.lower().strip().split("+")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 修飾キーをチェック
        if part in modifier_map:
            keys.add(modifier_map[part])
            continue

        # ファンクションキーをチェック (f1-f20)
        if part.startswith("f") and part[1:].isdigit():
            fn_num = int(part[1:])
            if 1 <= fn_num <= 20:
                fn_key = getattr(keyboard.Key, part, None)
                if fn_key:
                    keys.add(fn_key)
                    continue
            raise ValueError(f"Invalid function key: {part}")

        # 単一文字キー
        if len(part) == 1:
            keys.add(keyboard.KeyCode.from_char(part))
            continue

        raise ValueError(f"Unknown key: {part}")

    if not keys:
        raise ValueError(f"No valid keys found in: {hotkey_str}")

    return keys


def _format_hotkey(keys: set[keyboard.Key | keyboard.KeyCode]) -> str:
    """キーセットを人間可読な文字列に変換する。

    Args:
        keys: pynputキーオブジェクトのセット

    Returns:
        人間可読なホットキー文字列（例: "Ctrl+Shift+R"）
    """
    key_names: list[str] = []

    # 修飾キーを先に処理（順序を一定にするため）
    modifier_order = [
        (keyboard.Key.ctrl, "Ctrl"),
        (keyboard.Key.shift, "Shift"),
        (keyboard.Key.alt, "Alt"),
        (keyboard.Key.cmd, "Cmd"),
    ]

    for key_obj, name in modifier_order:
        if key_obj in keys:
            key_names.append(name)

    # その他のキー
    for key in keys:
        if isinstance(key, keyboard.Key):
            if key in (keyboard.Key.ctrl, keyboard.Key.shift, keyboard.Key.alt, keyboard.Key.cmd):
                continue  # 既に処理済み
            # ファンクションキーなど
            key_names.append(key.name.upper())
        elif isinstance(key, keyboard.KeyCode):
            if key.char:
                key_names.append(key.char.upper())

    return "+".join(key_names)


class _StatusItemHelper(NSObject):
    """メインスレッドでアイコン更新を実行するヘルパークラス。

    pynputリスナーはバックグラウンドスレッドで動作するため、
    NSStatusItemの更新はメインスレッドで行う必要がある。
    """

    def initWithApp_(self, app):
        """ヘルパーを初期化する。

        Args:
            app: VoiceCodeAppインスタンス
        """
        self = objc.super(_StatusItemHelper, self).init()
        if self is None:
            return None
        self._app = app
        self._pending_icon_path = None
        return self

    @objc.python_method
    def set_icon(self, icon_path: str):
        """アイコンを設定する（メインスレッドで実行）。

        Args:
            icon_path: アイコンファイルのパス
        """
        self._pending_icon_path = icon_path
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "doSetIcon", None, False
        )

    def doSetIcon(self):
        """実際のアイコン設定処理（メインスレッドで実行）。"""
        if self._pending_icon_path and self._app:
            self._app.icon = self._pending_icon_path


class VoiceCodeApp(rumps.App):
    """音声入力ツールのメインクラス（メニューバーアプリ）。"""

    # 状態アイコン定数（PNG画像を使用）
    ICON_IDLE = "icon_idle.png"
    ICON_RECORDING = "icon_recording.png"
    ICON_PROCESSING = "icon_processing.png"

    # 効果音定数
    SOUND_START = "/System/Library/Sounds/Tink.aiff"
    SOUND_STOP = "/System/Library/Sounds/Pop.aiff"
    SOUND_SUCCESS = "/System/Library/Sounds/Glass.aiff"
    SOUND_ERROR = "/System/Library/Sounds/Basso.aiff"

    def __init__(self):
        """VoiceCodeAppを初期化する。"""
        super().__init__("VoiceCode", icon=self._get_icon_path(self.ICON_IDLE), title="", quit_button="終了")
        config_dir = Path.home() / ".voicecode"
        config_dir.mkdir(parents=True, exist_ok=True)
        env_path = config_dir / ".env"
        load_dotenv(env_path)

        # API キーが設定されていない場合、入力を求める
        _ensure_api_keys(env_path)

        # 設定を読み込み（settings.json から、なければデフォルト値）
        self._settings = Settings()

        # 起動時に設定内容をログ出力
        self._log_settings()

        # 権限をチェック（マイク、入力監視、アクセシビリティ）
        self._check_permissions()

        self._hotkey = _parse_hotkey(self._settings.hotkey)
        recording_config = RecordingConfig(
            max_duration=self._settings.max_recording_duration
        )
        self._recorder = AudioRecorder(config=recording_config)
        self._transcriber = Transcriber()
        self._postprocessor = PostProcessor()
        self._history_manager = HistoryManager()

        self._current_keys: set = set()
        self._processing = False
        self._overlay = RecordingOverlay()

        # アイコン更新用ヘルパー（バックグラウンドスレッドからのUI更新に必要）
        self._status_helper = _StatusItemHelper.alloc().initWithApp_(self)

        # メニュー項目を初期化
        self._init_menu()

        # キーボードリスナーを別スレッドで起動
        self._start_keyboard_listener()

    @staticmethod
    def _get_icon_path(filename: str) -> str:
        """アイコンファイルのパスを取得する。

        スクリプト実行時とpy2appビルド時の両方に対応。

        Args:
            filename: アイコンファイル名（例: "icon_idle.png"）

        Returns:
            アイコンファイルの絶対パス
        """
        # py2appでビルドした場合: アプリバンドル内のResourcesディレクトリ
        if getattr(sys, "frozen", False):
            # frozen = True は py2app でビルドされたことを示す
            bundle_dir = Path(sys.executable).parent.parent / "Resources" / "assets"
        else:
            # スクリプト実行時: main.py と同じディレクトリの assets/
            bundle_dir = Path(__file__).parent / "assets"

        icon_path = bundle_dir / filename
        return str(icon_path)

    def _play_sound(self, sound_path: str) -> None:
        """効果音を非同期再生する。

        Args:
            sound_path: 再生する効果音ファイルのパス
        """
        subprocess.Popen(
            ["afplay", sound_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _start_keyboard_listener(self) -> None:
        """キーボードリスナーを起動する。"""
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        # Listener.start() は自身をデーモンスレッドとして起動する
        self._listener.start()

        # タイムアウトチェック用タイマーを起動
        self._timeout_timer = rumps.Timer(self._check_timeout, 0.5)
        self._timeout_timer.start()

    def _log_settings(self) -> None:
        """現在の設定内容をログ出力する。"""
        logger.info(f"[Settings] Hotkey: {self._settings.hotkey.upper()}")
        logger.info(f"[Settings] Max Recording: {self._settings.max_recording_duration}s")
        logger.info(f"[Settings] Restore Clipboard: {self._settings.restore_clipboard}")
        logger.info(f"[Settings] Push-to-Talk: {self._settings.push_to_talk}")

    def _check_permissions(self) -> None:
        """起動時に必要な権限をまとめてチェックする。

        以下の権限をチェックし、不足している場合は警告メッセージを表示する:
        - マイク権限: 音声録音に必要
        - 入力監視権限: ホットキー検出に必要
        - アクセシビリティ権限: キー入力シミュレーションに必要

        権限がなくてもアプリは起動を続ける。
        """
        warnings: list[str] = []

        # マイク権限チェック
        if not check_microphone_permission():
            logger.warning("[Warning] Microphone permission not granted")
            warnings.append(
                "[Warning] マイク権限が許可されていません\n"
                "システム設定 > プライバシーとセキュリティ > マイク で\n"
                "ターミナル（または VoiceCode.app）を許可してください。"
            )

        # 入力監視権限チェック
        if not check_input_monitoring_permission():
            logger.warning("[Warning] Input monitoring permission not granted")
            warnings.append(
                "[Warning] 入力監視権限が許可されていません\n"
                "システム設定 > プライバシーとセキュリティ > 入力監視 で\n"
                "ターミナル（または VoiceCode.app）を許可してください。"
            )

        # アクセシビリティ権限チェック
        if not check_accessibility_permission():
            logger.warning("[Warning] Accessibility permission not granted")
            warnings.append(
                "[Warning] アクセシビリティ権限が許可されていません\n"
                "システム設定 > プライバシーとセキュリティ > アクセシビリティ で\n"
                "ターミナル（または VoiceCode.app）を許可してください。"
            )

        # 警告があれば一括表示
        if warnings:
            print("\n" + "=" * 60)
            for i, warning in enumerate(warnings):
                if i > 0:
                    print("-" * 60)
                print(warning)
            print("=" * 60 + "\n")

    def _init_menu(self) -> None:
        """メニュー項目を初期化する。"""
        self._hotkey_item = rumps.MenuItem("ホットキー設定...", callback=self._on_hotkey_settings)
        self._restore_item = rumps.MenuItem(
            "クリップボードを復元",
            callback=self._on_toggle_restore_clipboard,
        )
        self._restore_item.state = 1 if self._settings.restore_clipboard else 0

        self.menu = [
            self._hotkey_item,
            self._restore_item,
            rumps.separator,
        ]

    def _on_hotkey_settings(self, _) -> None:
        """ホットキー設定ダイアログを表示する。"""
        current_hotkey = self._settings.hotkey
        window = rumps.Window(
            message=f"現在のホットキー: {current_hotkey.upper()}\n\n"
                    "新しいホットキーを入力してください\n"
                    "(例: f15, ctrl+shift+r)",
            title="ホットキー設定",
            default_text=current_hotkey,
            ok="保存",
            cancel="キャンセル",
        )
        response = window.run()

        # response.clicked: 1=保存, 0=キャンセル
        if response.clicked == 1:
            # 保存ボタン
            new_hotkey = response.text.strip()
            if new_hotkey:
                self._update_hotkey(new_hotkey)

    def _update_hotkey(self, new_hotkey: str) -> None:
        """ホットキーを更新する。"""
        try:
            new_keys = _parse_hotkey(new_hotkey)
            self._hotkey = new_keys
            self._settings.hotkey = new_hotkey
            self._settings.save()
            print(f"[Info] Hotkey updated to: {new_hotkey.upper()}")
        except ValueError as e:
            rumps.alert(
                title="エラー",
                message=f"無効なホットキーです: {e}",
            )

    def _on_toggle_restore_clipboard(self, sender: rumps.MenuItem) -> None:
        """クリップボード復元設定をトグルする。"""
        new_state = not self._settings.restore_clipboard
        self._settings.restore_clipboard = new_state
        self._settings.save()
        sender.state = 1 if new_state else 0
        status = "有効" if new_state else "無効"
        print(f"[Info] Restore clipboard: {status}")

    def _check_timeout(self, _) -> None:
        """録音タイムアウトをチェックする。"""
        if self._recorder.is_recording and self._recorder.is_timeout and not self._processing:
            print("\n[Timeout] Max recording duration reached")
            self._stop_and_process()

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """キー押下時のコールバック。"""
        logger.debug(f"Key pressed: {key}")
        normalized_key = self._normalize_key(key)

        # キーリピート検出: 既に押されているキーは無視
        if normalized_key in self._current_keys:
            return

        self._current_keys.add(normalized_key)

        if self._check_hotkey():
            self._toggle_recording()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        """キー解放時のコールバック。"""
        logger.debug(f"Key released: {key}")
        normalized_key = self._normalize_key(key)
        self._current_keys.discard(normalized_key)

        # Push-to-Talk モード: キーを離したら録音停止
        if self._settings.push_to_talk and self._recorder.is_recording:
            if not self._check_hotkey():  # ホットキーが離れた
                self._stop_and_process()

    def _normalize_key(self, key: keyboard.Key | keyboard.KeyCode) -> keyboard.Key | keyboard.KeyCode:
        """キーを正規化する。"""
        if isinstance(key, keyboard.KeyCode) and key.char:
            return keyboard.KeyCode.from_char(key.char.lower())
        return key

    def _check_hotkey(self) -> bool:
        """ホットキーが押されているかチェックする。"""
        result = self._hotkey <= self._current_keys
        logger.debug(f"Checking hotkey: current_keys={self._current_keys}, hotkey={self._hotkey}, match={result}")
        return result

    def _format_hotkey_display(self) -> str:
        """ホットキーを表示用に整形する。"""
        return _format_hotkey(self._hotkey)

    def _toggle_recording(self) -> None:
        """録音のトグル処理。"""
        if self._processing:
            return

        if self._recorder.is_recording:
            self._stop_and_process()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        """録音を開始する。"""
        try:
            self._recorder.start()
            self._status_helper.set_icon(self._get_icon_path(self.ICON_RECORDING))
            self._overlay.show()
            self._play_sound(self.SOUND_START)
            hotkey_display = self._format_hotkey_display()
            print("\n" + "=" * 50)
            print(f"Recording... Press {hotkey_display} to stop")
            print("=" * 50)
        except MicrophonePermissionError as e:
            logger.error(f"Microphone permission error: {e}")
            print("\n" + "=" * 60)
            print("[Error] マイク権限が許可されていません")
            print("-" * 60)
            print("システム設定 > プライバシーとセキュリティ > マイク で")
            print("ターミナル（または VoiceCode.app）を許可してください。")
            print("=" * 60 + "\n")
            self._status_helper.set_icon(self._get_icon_path(self.ICON_IDLE))
            self._play_sound(self.SOUND_ERROR)
        except Exception as e:
            print(f"[Error] Failed to start recording: {e}")
            self._status_helper.set_icon(self._get_icon_path(self.ICON_IDLE))
            self._play_sound(self.SOUND_ERROR)

    def _stop_and_process(self) -> None:
        """録音を停止し、処理を実行する。"""
        self._processing = True
        self._status_helper.set_icon(self._get_icon_path(self.ICON_PROCESSING))
        self._overlay.hide()
        self._play_sound(self.SOUND_STOP)
        audio_path: Path | None = None
        original_clipboard: str | None = None
        transcribed_text: str = ""
        processed_text: str = ""

        # 処理時間計測用
        total_start = time.time()
        stop_time: float = 0.0
        transcription_time: float = 0.0
        postprocess_time: float = 0.0
        paste_time: float = 0.0

        try:
            # 録音停止（WAVファイル書き込み含む）
            stop_start = time.time()
            audio_path = self._recorder.stop()
            stop_time = time.time() - stop_start
            logger.info(f"[Stop] Recording saved ({stop_time:.2f}s)")

            print("\n" + "-" * 50)
            print("Processing...")
            print("-" * 50)

            # 文字起こし
            transcribed_text, transcription_time = self._transcriber.transcribe(audio_path)

            if not transcribed_text.strip():
                print("[Warning] No speech detected")
                self._status_helper.set_icon(self._get_icon_path(self.ICON_IDLE))
                self._play_sound(self.SOUND_ERROR)
                return

            # LLM後処理
            processed_text, postprocess_time = self._postprocessor.process(transcribed_text)

            # クリップボード復元が有効な場合、元の内容を保存
            if self._settings.restore_clipboard:
                try:
                    original_clipboard = pyperclip.paste()
                except Exception:
                    pass

            # クリップボード + 貼り付け
            paste_start = time.time()
            pyperclip.copy(processed_text)
            time.sleep(0.2)
            controller = keyboard.Controller()
            with controller.pressed(keyboard.Key.cmd):
                controller.tap('v')
            paste_time = time.time() - paste_start
            logger.info(f"[Paste] Clipboard + paste ({paste_time:.2f}s)")

            # 合計時間を表示
            total_time = time.time() - total_start
            print(f"[Total] {total_time:.2f}s (stop: {stop_time:.2f}s, gemini: {transcription_time:.2f}s, finalize: {postprocess_time:.2f}s, paste: {paste_time:.2f}s)")

            # 履歴を保存（貼り付け完了後、一時ファイル削除前）
            if audio_path and audio_path.exists():
                self._history_manager.save(
                    audio_path=audio_path,
                    raw_transcription=transcribed_text,
                    processed_text=processed_text,
                )

            self._status_helper.set_icon(self._get_icon_path(self.ICON_IDLE))
            self._play_sound(self.SOUND_SUCCESS)

            hotkey_display = self._format_hotkey_display()
            print("\n" + "=" * 50)
            print(f"Ready. Press {hotkey_display} to start recording")
            print("=" * 50)

        except Exception as e:
            print(f"[Error] Processing failed: {e}")
            self._status_helper.set_icon(self._get_icon_path(self.ICON_IDLE))
            self._play_sound(self.SOUND_ERROR)

        finally:
            # クリップボードを復元
            if original_clipboard is not None:
                try:
                    time.sleep(0.1)
                    pyperclip.copy(original_clipboard)
                    print("[Clipboard] Restored original content")
                except Exception:
                    pass

            # 一時ファイルを削除
            if audio_path and audio_path.exists():
                try:
                    audio_path.unlink()
                    print(f"[Cleanup] Deleted: {audio_path}")
                except Exception as e:
                    print(f"[Warning] Failed to delete temp file: {e}")

            self._processing = False


def _daemonize() -> None:
    """プロセスをデーモン化する。

    os.fork() を使用して親プロセスを終了し、子プロセスで継続する。
    標準入出力をログファイルにリダイレクトする。
    """
    # 最初の fork
    try:
        pid = os.fork()
        if pid > 0:
            # 親プロセスは終了（fork後はos._exit()を使用）
            os._exit(0)
    except OSError as e:
        print(f"[Error] fork #1 failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 新しいセッションを作成
    os.setsid()

    # ファイル作成時のパーミッションマスク（所有者のみ読み書き可能）
    os.umask(0o077)

    # 2回目の fork（セッションリーダーから離れる）
    try:
        pid = os.fork()
        if pid > 0:
            # 親プロセスは終了（fork後はos._exit()を使用）
            os._exit(0)
    except OSError as e:
        print(f"[Error] fork #2 failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 標準入出力をリダイレクト
    daemon_log_dir = Path.home() / ".voicecode"
    daemon_log_dir.mkdir(parents=True, exist_ok=True)
    daemon_log_file = daemon_log_dir / "voicecode.log"

    # 標準入力を /dev/null にリダイレクト（OSレベル + Pythonオブジェクト）
    devnull_fd = os.open("/dev/null", os.O_RDWR)
    os.dup2(devnull_fd, 0)  # stdin
    sys.stdin = os.fdopen(0, "r")

    # 標準出力と標準エラーをログファイルにリダイレクト（OSレベル + Pythonオブジェクト）
    log_fd = os.open(str(daemon_log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(log_fd, 1)  # stdout
    os.dup2(log_fd, 2)  # stderr
    sys.stdout = os.fdopen(1, "w", buffering=1)
    sys.stderr = os.fdopen(2, "w", buffering=1)

    # 元のファイルディスクリプタを閉じる（dup2でコピー済み）
    os.close(devnull_fd)
    os.close(log_fd)

    # コンソールハンドラを削除（閉じたstderrへの書き込みを防ぐ）
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and hasattr(handler.stream, 'name') and handler.stream.name == '<stderr>':
            root_logger.removeHandler(handler)


def _parse_args() -> argparse.Namespace:
    """コマンドライン引数をパースする。

    macOS Finderからの起動時に渡される -psn_0_... 引数を無視するため、
    parse_known_args() を使用する。

    Returns:
        パースされた引数
    """
    parser = argparse.ArgumentParser(
        description="VoiceCode - 音声入力ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  uv run python main.py        # フォアグラウンドで実行
  uv run python main.py -d     # バックグラウンド（デーモン）で実行
""",
    )
    parser.add_argument(
        "-d", "--daemon",
        action="store_true",
        help="バックグラウンドで実行（注意: PyObjCのfork安全性の問題があるため、"
             "launchctl経由での起動を推奨）",
    )
    # parse_known_args() を使用して未知の引数（-psn_0_... 等）を無視
    args, _ = parser.parse_known_args()
    return args


def main() -> None:
    """エントリポイント。"""
    args = _parse_args()

    if args.daemon:
        _daemonize()

    app = VoiceCodeApp()
    app.run()


if __name__ == "__main__":
    main()
