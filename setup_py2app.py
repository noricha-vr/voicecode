"""py2app セットアップスクリプト。

配布用のスタンドアロン .app を作成する。

使用方法:
    uv pip install py2app
    uv run python setup_py2app.py py2app

出力:
    dist/VoiceCode.app
"""

import tomllib
from pathlib import Path
from setuptools import setup

# pyproject.toml からバージョンを読み込む
pyproject_path = Path(__file__).parent / "pyproject.toml"
with open(pyproject_path, "rb") as f:
    pyproject = tomllib.load(f)
version = pyproject["project"]["version"]

APP = ['main.py']
DATA_FILES = [
    ('assets', [
        'assets/icon_idle.png',
        'assets/icon_recording.png',
        'assets/icon_processing.png',
    ]),
]
OPTIONS = {
    'argv_emulation': False,  # rumps では False が推奨
    'plist': {
        'LSUIElement': True,  # Dock に表示しない（メニューバーアプリ）
        'LSBackgroundOnly': False,
        'CFBundleIdentifier': 'com.voicecode.app',
        'CFBundleName': 'VoiceCode',
        'CFBundleVersion': version,
        'CFBundleShortVersionString': version,
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': '音声入力のためにマイクを使用します',
        'NSAppleEventsUsageDescription': 'テキスト貼り付けのためにキーボードを制御します',
    },
    'packages': [
        'rumps',
        'pynput',
        'sounddevice',
        'numpy',
        'groq',
        'openai',
        'pyperclip',
        'dotenv',
    ],
    'includes': [
        'AppKit',
        'Foundation',
        'objc',
    ],
}

setup(
    name='VoiceCode',
    version=version,
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
