"""音声文字起こしモジュール。

Gemini Flash に音声を直接入力して文字起こしする。
"""

import logging
import os
import re
import time
from pathlib import Path

import google.generativeai as genai

from postprocessor import SYSTEM_PROMPT, _load_user_dictionary

logger = logging.getLogger(__name__)


TRANSCRIBE_PROMPT = (
    "この音声を日本語で文字起こししてください。"
    "文脈を考慮して技術用語を正しい表記に修正し、"
    "最終的な文字起こし結果のみを1行で返してください。"
)


class Transcriber:
    """音声文字起こしクラス。"""

    MODEL = "gemini-2.5-flash"
    MODEL_ENV_VAR = "VOICECODE_GEMINI_MODEL"
    MODEL_ALIASES = {
        # 旧命名を受け取った場合でも実在モデルへ寄せる
        "gemini-3.0-flash": "gemini-3-flash-preview",
    }
    PREFERRED_MODELS = (
        "gemini-3-flash-preview",
        MODEL,
        "gemini-2.0-flash",
        "gemini-flash-latest",
    )
    TIMEOUT = 10.0
    MAX_TRANSIENT_RETRIES = 1
    RETRY_BACKOFF_SECONDS = 0.3

    def __init__(self, api_key: str | None = None):
        """Transcriberを初期化する。

        Args:
            api_key: Google APIキー。Noneの場合は環境変数から取得。

        Raises:
            ValueError: APIキーが設定されていない場合。
        """
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self._api_key:
            raise ValueError("GOOGLE_API_KEY is not set")

        genai.configure(api_key=self._api_key)
        self._system_prompt = self._build_system_prompt()
        self._model_name = self._resolve_model_name()
        self._model = self._create_model(self._model_name)
        logger.info(f"[Gemini] 使用モデル: {self._model_name}")

    def _build_system_prompt(self) -> str:
        """ユーザー辞書を注入したシステムプロンプトを構築する。"""
        conversion_xml, hint_xml = _load_user_dictionary()
        user_dict = conversion_xml + hint_xml
        if not user_dict:
            return SYSTEM_PROMPT

        return SYSTEM_PROMPT.replace(
            "</terminology>",
            f"{user_dict}\n</terminology>",
        )

    @staticmethod
    def _extract_response_text(response: object) -> str:
        """Geminiレスポンスからテキストを抽出する。"""
        try:
            direct_text = getattr(response, "text", "")
            if isinstance(direct_text, str) and direct_text:
                return direct_text
        except Exception:
            pass

        candidates = getattr(response, "candidates", None)
        if not candidates:
            return ""

        parts: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            content_parts = getattr(content, "parts", None)
            if not content_parts:
                continue
            for part in content_parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str):
                    parts.append(part_text)
        return "".join(parts)

    @classmethod
    def _normalize_model_name(cls, model_name: str) -> str:
        """モデル名から先頭の `models/` を除去する。"""
        normalized = model_name.removeprefix("models/").strip()
        return cls.MODEL_ALIASES.get(normalized, normalized)

    @classmethod
    def _build_model_candidates(cls) -> list[str]:
        """候補モデル名リストを構築する。"""
        configured_model = os.getenv(cls.MODEL_ENV_VAR, "").strip()
        candidates: list[str] = []

        if configured_model:
            candidates.append(cls._normalize_model_name(configured_model))

        for model_name in cls.PREFERRED_MODELS:
            if model_name not in candidates:
                candidates.append(model_name)

        return candidates

    def _list_available_models(self) -> list[str]:
        """generateContent に対応した利用可能モデル名一覧を返す。"""
        available_models: list[str] = []
        for model in genai.list_models():
            methods = getattr(model, "supported_generation_methods", None) or []
            if "generateContent" not in methods:
                continue

            model_name = getattr(model, "name", "")
            if isinstance(model_name, str) and model_name:
                available_models.append(self._normalize_model_name(model_name))

        return available_models

    def _resolve_model_name(self, exclude: set[str] | None = None) -> str:
        """実行時に利用するモデル名を解決する。"""
        excluded_models = exclude or set()
        candidates = self._build_model_candidates()
        configured_model = os.getenv(self.MODEL_ENV_VAR, "").strip()
        configured_model = self._normalize_model_name(configured_model) if configured_model else ""

        try:
            available_models = self._list_available_models()
        except Exception as e:
            if configured_model and configured_model not in excluded_models:
                logger.warning(
                    f"[Gemini] モデル一覧取得に失敗したため環境変数モデルを使用します: {configured_model} ({e})"
                )
                return configured_model

            if self.MODEL not in excluded_models:
                logger.warning(
                    f"[Gemini] モデル一覧取得に失敗したため既定モデルを使用します: {self.MODEL} ({e})"
                )
                return self.MODEL

            return ""

        for candidate in candidates:
            if candidate in available_models and candidate not in excluded_models:
                return candidate

        for available_model in available_models:
            if available_model not in excluded_models:
                logger.warning(f"[Gemini] 候補モデルが見つからないため利用可能モデルにフォールバックします: {available_model}")
                return available_model

        return ""

    def _create_model(self, model_name: str) -> genai.GenerativeModel:
        """Geminiクライアントを作成する。"""
        return genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self._system_prompt,
        )

    @staticmethod
    def _is_model_not_found_error(error: Exception) -> bool:
        """モデル未検出エラーかどうか判定する。"""
        message = str(error).lower()
        return (
            "is not found for api version" in message
            or ("404" in message and "models/" in message and "not found" in message)
        )

    @staticmethod
    def _is_transient_api_error(error: Exception) -> bool:
        """一時的なAPIエラーかどうか判定する。"""
        message = str(error).lower()
        transient_patterns = (
            "deadline expired",
            "timed out",
            "timeout",
            "temporarily unavailable",
            "service unavailable",
        )
        has_http_hint = bool(re.search(r"\b(429|500|502|503|504)\b", message)) or "too many requests" in message
        return any(pattern in message for pattern in transient_patterns) or has_http_hint

    def _generate_content(self, audio_data: bytes) -> object:
        """Gemini generate_content を呼び出す。"""
        return self._model.generate_content(
            [
                TRANSCRIBE_PROMPT,
                {"mime_type": "audio/wav", "data": audio_data},
            ],
            request_options={"timeout": self.TIMEOUT},
        )

    def _generate_content_with_retry(self, audio_data: bytes) -> object:
        """一時的なAPIエラー時に短いリトライを行う。"""
        last_error: Exception | None = None
        for attempt in range(self.MAX_TRANSIENT_RETRIES + 1):
            try:
                return self._generate_content(audio_data)
            except Exception as e:
                last_error = e
                if not self._is_transient_api_error(e) or attempt >= self.MAX_TRANSIENT_RETRIES:
                    raise

                wait_seconds = self.RETRY_BACKOFF_SECONDS * (attempt + 1)
                logger.warning(
                    f"[Gemini] 一時的なAPIエラーのため再試行します({attempt + 1}/{self.MAX_TRANSIENT_RETRIES}): {e}"
                )
                time.sleep(wait_seconds)

        # 到達不可だが型チェッカ向けに明示
        assert last_error is not None
        raise last_error

    def transcribe(self, audio_path: Path) -> tuple[str, float]:
        """音声ファイルを文字起こしする。

        Args:
            audio_path: 音声ファイルのパス。

        Returns:
            文字起こし結果のテキストと処理時間（秒）のタプル。
            APIエラー時は空文字列と経過時間を返す。

        Raises:
            FileNotFoundError: 音声ファイルが存在しない場合。
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        with open(audio_path, "rb") as audio_file:
            audio_data = audio_file.read()

        start_time = time.time()

        try:
            response = self._generate_content_with_retry(audio_data)
        except Exception as e:
            # API側のモデル差し替え・廃止、または一時エラー時は利用可能モデルへ1回だけ自動切替して再試行する
            if self._is_model_not_found_error(e) or self._is_transient_api_error(e):
                fallback_model = self._resolve_model_name(exclude={self._model_name})
                if fallback_model:
                    reason = (
                        "モデルが見つからないため"
                        if self._is_model_not_found_error(e)
                        else "一時的なAPIエラーのため"
                    )
                    logger.warning(
                        f"[Gemini] {reason}モデルを切替します: {self._model_name} -> {fallback_model}"
                    )
                    try:
                        self._model_name = fallback_model
                        self._model = self._create_model(self._model_name)
                        response = self._generate_content_with_retry(audio_data)
                    except Exception as retry_error:
                        elapsed = time.time() - start_time
                        logger.error(
                            f"[Gemini] API呼び出しに失敗しました(model={self._model_name}): {retry_error} ({elapsed:.2f}s)"
                        )
                        return "", elapsed
                else:
                    elapsed = time.time() - start_time
                    logger.error(
                        f"[Gemini] API呼び出しに失敗しました(model={self._model_name}): {e} ({elapsed:.2f}s)"
                    )
                    return "", elapsed
            else:
                elapsed = time.time() - start_time
                logger.error(f"[Gemini] API呼び出しに失敗しました(model={self._model_name}): {e} ({elapsed:.2f}s)")
                return "", elapsed

        elapsed = time.time() - start_time
        raw_text = self._extract_response_text(response)
        result = re.sub(r"<[^>]+>", "", raw_text).strip()
        logger.info(f"[Gemini] {result} ({elapsed:.2f}s, model={self._model_name})")
        return result, elapsed
