"""
config_manager.py - Oyun Ayarları Yöneticisi
===============================================
Kalıcı ayarları JSON dosyasından yükler ve kaydeder.

API anahtarı GÜVENLİK nedeniyle JSON'da DEĞİL, .env dosyasında tutulur
(S13 fix — Aşama 6.1):
  - Okuma önceliği: .env dosyası > işletim sistemi ortam değişkeni
  - Eski game_config.json içinde api_key bulunursa otomatik olarak
    .env'e taşınır (migration) ve JSON'dan silinir.
  - .env dosyası .gitignore'dadır, repoya sızamaz.
"""

import json
import os
from typing import Any, Dict

from dotenv import dotenv_values, set_key

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_BASE_DIR, "game_config.json")
ENV_FILE = os.path.join(_BASE_DIR, ".env")

# .env içindeki API anahtarı değişkeninin adı
# (ai_manager.py'deki os.environ fallback'i ile aynı isim)
API_KEY_ENV_VAR = "API_KEY"

# Kullanilabilir AI modelleri (OpenAI uyumlu API)
AVAILABLE_MODELS = [
    # Google Gemini
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    # OpenAI GPT
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-5.1",
    # OpenAI o-serisi
    "o4-mini",
    "o3",
    "o3-mini",
    # Anthropic Claude
    "claude-sonnet-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    # Meta Llama (OpenRouter vb.)
    "meta-llama/llama-4-maverick",
    "meta-llama/llama-3.3-70b-instruct",
    # Ozel model (kullanici girer)
    "Ozel...",
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "",
    "model_name": "gemini-2.5-flash",
    "max_tokens": 1024,
    "camera_index": 0,
}


def _read_api_key_from_env() -> str:
    """API anahtarini okur. Oncelik: .env dosyasi > OS ortam degiskeni."""
    if os.path.exists(ENV_FILE):
        try:
            key = (dotenv_values(ENV_FILE).get(API_KEY_ENV_VAR) or "").strip()
            if key:
                return key
        except Exception:
            pass
    return os.environ.get(API_KEY_ENV_VAR, "").strip()


def _write_api_key_to_env(key: str) -> None:
    """API anahtarini .env dosyasina yazar (dosya yoksa olusturur)."""
    try:
        set_key(ENV_FILE, API_KEY_ENV_VAR, key)
        # Ayni process icindeki fallback okumalar icin ortami da guncelle
        os.environ[API_KEY_ENV_VAR] = key
    except Exception as e:
        print(f"[!] .env dosyasina yazilamadi: {e}")


def load_config() -> Dict[str, Any]:
    """Ayarlari yukler. API key .env'den, digerleri JSON'dan gelir.

    Eski surumlerde api_key JSON'da tutuluyordu; bulunursa .env'e
    tasinir ve JSON'dan silinir (migration).
    """
    config = dict(DEFAULT_CONFIG)
    saved: Dict[str, Any] = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, IOError):
            saved = {}  # Bozuk dosya - varsayilan kullan

    env_key = _read_api_key_from_env()
    legacy_key = str(config.get("api_key") or "").strip()

    # Migration: JSON'da key var ama .env'de yok -> .env'e tasi
    if not env_key and legacy_key:
        _write_api_key_to_env(legacy_key)
        env_key = legacy_key
        if isinstance(saved, dict) and "api_key" in saved:
            saved.pop("api_key", None)
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(saved, f, indent=2, ensure_ascii=False)
            except IOError:
                pass
        print("[*] API anahtari game_config.json'dan .env dosyasina tasindi.")

    config["api_key"] = env_key
    if env_key:
        os.environ[API_KEY_ENV_VAR] = env_key
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Ayarlari kaydeder: API key .env'e, diger alanlar JSON'a yazilir."""
    cfg = dict(config)
    api_key = str(cfg.pop("api_key", "") or "").strip()
    cfg.pop("_action", None)  # Calisma zamani alani, diske yazilmaz

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"[*] Ayarlar kaydedildi: {CONFIG_FILE}")
    except IOError as e:
        print(f"[!] Ayarlar kaydedilemedi: {e}")

    if api_key:
        _write_api_key_to_env(api_key)


def mask_api_key(key: str) -> str:
    """API anahtarini gosterim icin maskeler (ilk 4 ve son 4 karakter gorunur)."""
    if len(key) <= 10:
        return "*" * len(key)
    return key[:4] + "*" * (len(key) - 8) + key[-4:]
