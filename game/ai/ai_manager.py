"""
ai_manager.py - Yapay Zeka Yöneticisi (LiteLLM)
==================================================
LiteLLM kullanarak 100+ farkli AI modeline tek bir API ile
istek gonderir: OpenAI, Gemini, Claude, Llama vb.
"""

import json
import os
import threading
from typing import Any, Callable, Dict, List, Optional

import litellm

# LiteLLM'in gereksiz loglarini sustur
litellm.suppress_debug_info = True
litellm.set_verbose = False


class AdventureAI:
    """D&D macera hikayesi üreten yapay zeka yöneticisi (LiteLLM)."""

    DEFAULT_MODEL = "gemini/gemini-2.5-flash"
    DEFAULT_MAX_TOKENS = 1024

    def __init__(self, api_key: Optional[str] = None,
                 model: str = DEFAULT_MODEL,
                 max_tokens: int = DEFAULT_MAX_TOKENS):
        resolved_key = api_key or os.environ.get("API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "API anahtari bulunamadi! "
                "Ana menudeki Ayarlar ekranindan API anahtarinizi girin."
            )

        self.api_key = resolved_key
        self.model = self._normalize_model(model)
        self.max_tokens = max_tokens

        # API key'i provider'a gore env var olarak ayarla
        self._set_api_key_env(self.model, self.api_key)

        self._is_requesting: bool = False
        self._last_response: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._lock = threading.Lock()

        print(f"[*] AI motoru hazir: {self.model}")

    @staticmethod
    def _normalize_model(model: str) -> str:
        """
        Model adini LiteLLM formatina cevirir.
        LiteLLM provider prefix'leri:
          - gemini/    -> Google Gemini
          - anthropic/ -> Anthropic Claude (veya claude- ile baslayan)
          - openrouter/ -> OpenRouter
          - (prefix yok) -> OpenAI
        """
        m = model.strip()

        # Zaten prefix varsa dokunma
        if "/" in m:
            return m

        # Gemini modelleri
        if m.startswith("gemini"):
            return f"gemini/{m}"

        # Claude modelleri
        if m.startswith("claude"):
            return f"anthropic/{m}"

        # OpenAI modelleri (gpt, o1, o3, o4 vb.) - prefix gerektirmez
        return m

    def _set_api_key_env(self, model: str, key: str) -> None:
        """Model provider'ina gore uygun env var'i ayarlar."""
        if model.startswith("gemini/"):
            os.environ["GEMINI_API_KEY"] = key
        elif model.startswith("anthropic/") or model.startswith("claude"):
            os.environ["ANTHROPIC_API_KEY"] = key
        elif model.startswith("openrouter/"):
            os.environ["OPENROUTER_API_KEY"] = key
        else:
            # OpenAI ve diger modeller
            os.environ["OPENAI_API_KEY"] = key

    def _build_params(self, message_history: List[Dict[str, str]]) -> dict:
        """LiteLLM completion parametrelerini olusturur."""
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": message_history,
            "max_tokens": self.max_tokens,
        }

        # JSON modu - modele gore ayarla
        model_lower = self.model.lower()

        # OpenAI modelleri - response_format destekler
        if any(model_lower.startswith(p) for p in ("gpt", "o1", "o3", "o4")):
            params["response_format"] = {"type": "json_object"}
        # Gemini modelleri - response_format destekler
        elif "gemini" in model_lower:
            params["response_format"] = {"type": "json_object"}

        # Temperature (reasoning modelleri haric)
        if not any(model_lower.startswith(p) for p in ("o1", "o3", "o4")):
            params["temperature"] = 0.8

        return params

    # ------------------------------------------------------------------ #
    #  PUBLIC API                                                          #
    # ------------------------------------------------------------------ #

    def request_story(self, message_history: List[Dict[str, str]],
                      callback: Optional[Callable] = None) -> None:
        """Arka planda AI'dan hikaye istegi gonderir (non-blocking)."""
        with self._lock:
            if self._is_requesting:
                return
            self._is_requesting = True
            self._last_error = None

        thread = threading.Thread(
            target=self._api_call_worker,
            args=(message_history, callback),
            daemon=True
        )
        thread.start()

    def request_story_sync(self, message_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Senkron hikaye istegi (blocking)."""
        try:
            params = self._build_params(message_history)
            response = litellm.completion(**params)
            content = response.choices[0].message.content.strip()
            return self._parse_response(content)
        except Exception as e:
            raise RuntimeError(f"AI API cagrisi basarisiz: {e}") from e

    def is_requesting(self) -> bool:
        with self._lock:
            return self._is_requesting

    def get_last_response(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            response = self._last_response
            self._last_response = None
            return response

    def get_last_error(self) -> Optional[str]:
        with self._lock:
            error = self._last_error
            self._last_error = None
            return error

    def generate_opening(self, character_summary: str) -> Dict[str, Any]:
        """Oyunun acilis hikayesini uretir."""
        opening_messages = [
            {"role": "system", "content": (
                "Sen bir D&D zindancisisin. Turkce hikaye anlat. "
                "KRITIK: Turkce ozel karakterleri (s,c,g,i,o,u) KULLANMA, ASCII karsiligini yaz. "
                "Yanitin ISTISNA TANIMADAN su JSON formatinda olmali: "
                '{"hikaye_metni": "...", "secenekler": {"sol_ust": "...", "sag_ust": "...", "sol_alt": "...", "sag_alt": "..."}} '
                "Hikaye 3-4 cumle, secenekler 6-8 kelime. SADECE JSON dondur."
            )},
            {"role": "user", "content": f"Yeni macera basliyor! {character_summary} Acilis sahnesi anlat ve 4 secenek sun."},
        ]
        return self.request_story_sync(opening_messages)

    # ------------------------------------------------------------------ #
    #  PRIVATE                                                             #
    # ------------------------------------------------------------------ #

    def _api_call_worker(self, message_history: List[Dict[str, str]],
                         callback: Optional[Callable]) -> None:
        try:
            params = self._build_params(message_history)
            response = litellm.completion(**params)
            content = response.choices[0].message.content.strip()
            parsed = self._parse_response(content)
            with self._lock:
                self._last_response = parsed
                self._is_requesting = False
            if callback:
                callback(parsed)
        except Exception as e:
            with self._lock:
                self._last_error = str(e)
                self._is_requesting = False

    def _parse_response(self, raw_content: str) -> Dict[str, Any]:
        """AI yanitini JSON olarak ayristirir."""
        import re
        content = raw_content.strip()

        fallback = {
            "hikaye_metni": "Gizemli bir sis etrafini sardi... (AI yaniti okunamadi)",
            "feedback": "Sistem hatasi veya gecersiz format.",
            "secenekler": {
                "sol_ust": "Ilerle",
                "sag_ust": "Etrafi arastir",
                "sol_alt": "Bekle",
                "sag_alt": "Geri don"
            },
        }

        try:
            # 1. Dogrudan JSON olarak parse etmeyi dene
            try:
                data = json.loads(content)
                if "hikaye_metni" in data and "secenekler" in data:
                    return data
            except json.JSONDecodeError:
                pass

            # 2. Basarisiz olursa, regex ile JSON blogunu bul ve parse et
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                try:
                    data = json.loads(json_str)
                    if "hikaye_metni" in data and "secenekler" in data:
                        return data
                except json.JSONDecodeError:
                    pass

            # 3. Hicbiri calismazsa veya gerekli anahtarlar yoksa fallback don
            print(f"\n[!] AI Yaniti Gecersiz Format (Fallback devrede):\n{raw_content}\n")
            return fallback

        except Exception as e:
            print(f"\n[!] Ayristirma Hatasi: {e}\n[!] AI Yaniti: {raw_content}\n")
            return fallback
