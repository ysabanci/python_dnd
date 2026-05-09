"""
ai_manager.py - Yapay Zeka Yöneticisi
=======================================
OpenAI API ile GPT-4o-mini modeli kullanarak hikaye üretir.
"""

import json
import os
import threading
from typing import Any, Callable, Dict, List, Optional

from openai import OpenAI


class AdventureAI:
    """D&D macera hikayesi üreten yapay zeka yöneticisi."""

    DEFAULT_MODEL = "gpt-4o"
    DEFAULT_MAX_TOKENS =16384
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL, max_tokens: int = DEFAULT_MAX_TOKENS):
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError("OPENAI_API_KEY ortam değişkenini ayarlayın.")

        self.client = OpenAI(api_key=resolved_key)
        self.model = model
        self.max_tokens = max_tokens
        self._is_requesting: bool = False
        self._last_response: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._lock = threading.Lock()

    def request_story(self, message_history: List[Dict[str, str]], callback: Optional[Callable] = None) -> None:
        """Arka planda AI'dan hikaye isteği gönderir (non-blocking)."""
        with self._lock:
            if self._is_requesting:
                return
            self._is_requesting = True
            self._last_error = None

        thread = threading.Thread(target=self._api_call_worker, args=(message_history, callback), daemon=True)
        thread.start()

    def request_story_sync(self, message_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Senkron hikaye isteği (blocking)."""
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=message_history, max_tokens=self.max_tokens, temperature=0.8,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content.strip()
            return self._parse_response(content)
        except Exception as e:
            raise RuntimeError(f"AI API çağrısı başarısız: {e}") from e

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
        """Oyunun açılış hikayesini üretir."""
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

    def _api_call_worker(self, message_history: List[Dict[str, str]], callback: Optional[Callable]) -> None:
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=message_history, max_tokens=self.max_tokens, temperature=0.8,
                response_format={"type": "json_object"}
            )
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
        """AI yanitini JSON olarak ayristirir (Regex ve AST ile)."""
        import re
        import ast
        content = raw_content.strip()
        
        # Fallback (Hata durumunda donulecek varsayilan yapi)
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
            # Metin icindeki JSON blogunu bul
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Eger tek tirnak (Python dict) kullanmissa json patlar, ast ile kurtaralim:
                    data = ast.literal_eval(json_str)
                    
                if "hikaye_metni" in data and "secenekler" in data:
                    return data
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = ast.literal_eval(content)
                
            return data
        except Exception as e:
            print(f"\n[!] Ayristirma Hatasi: {e}\n[!] AI Yaniti: {raw_content}\n")
            return fallback
