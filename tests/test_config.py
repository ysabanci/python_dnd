"""
test_config.py — Config Manager fonksiyonları için testler.

config_manager.py'deki load_config, save_config ve mask_api_key
fonksiyonlarını test eder.
"""

import pytest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config_manager


# ================================================================
# mask_api_key
# ================================================================

class TestMaskApiKey:
    """API key maskeleme testleri."""

    def test_long_key_masked(self):
        """Uzun key: ilk 4 ve son 4 karakter görünür, ortası yıldız."""
        key = "sk-1234567890abcdef"
        masked = config_manager.mask_api_key(key)
        assert masked[:4] == "sk-1"
        assert masked[-4:] == "cdef"
        assert "*" in masked
        assert len(masked) == len(key)

    def test_short_key_fully_masked(self):
        """10 veya daha kısa key tamamen yıldızla maskelenmeli."""
        key = "short"
        masked = config_manager.mask_api_key(key)
        assert masked == "*" * len(key)

    def test_empty_key(self):
        """Boş key boş string döndürmeli."""
        assert config_manager.mask_api_key("") == ""

    def test_exactly_10_chars(self):
        """Tam 10 karakter — tamamen maskelenmeli."""
        key = "1234567890"
        masked = config_manager.mask_api_key(key)
        assert masked == "**********"

    def test_11_chars_partially_masked(self):
        """11 karakter — ilk 4 + son 4 görünür."""
        key = "12345678901"
        masked = config_manager.mask_api_key(key)
        assert masked[:4] == "1234"
        assert masked[-4:] == "8901"


# ================================================================
# load_config & save_config
# ================================================================

@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """CONFIG_FILE ve ENV_FILE'i gecici dizine yonlendirir.

    Testler gercek game_config.json ve .env dosyalarina ASLA dokunmamali.
    OS ortamindaki API_KEY de temizlenir ki fallback okuma test sonuclarini
    kirletmesin.
    """
    fake_json = str(tmp_path / "test_config.json")
    fake_env = str(tmp_path / ".env")
    monkeypatch.setattr(config_manager, "CONFIG_FILE", fake_json)
    monkeypatch.setattr(config_manager, "ENV_FILE", fake_env)
    monkeypatch.delenv("API_KEY", raising=False)
    return fake_json, fake_env


class TestConfigIO:
    """Config dosya okuma/yazma testleri."""

    def test_load_default_when_no_file(self, isolated_config):
        """Config dosyası yokken varsayılan değerler dönmeli."""
        config = config_manager.load_config()
        assert config["model_name"] == "gemini-2.5-flash"
        assert config["api_key"] == ""
        assert config["max_tokens"] == 1024

    def test_save_and_load_roundtrip(self, isolated_config):
        """Kaydedilen config yüklendiğinde aynı değerleri döndürmeli."""
        test_config = {
            "api_key": "test-key-123",
            "model_name": "gpt-4o",
            "max_tokens": 2048,
            "camera_index": 1,
        }
        config_manager.save_config(test_config)
        loaded = config_manager.load_config()

        assert loaded["api_key"] == "test-key-123"
        assert loaded["model_name"] == "gpt-4o"
        assert loaded["max_tokens"] == 2048
        assert loaded["camera_index"] == 1

    def test_load_corrupt_file_returns_defaults(self, isolated_config):
        """Bozuk JSON dosyası varsayılan değerleri döndürmeli."""
        fake_json, _ = isolated_config
        with open(fake_json, "w") as f:
            f.write("{broken json...")

        config = config_manager.load_config()
        assert config["model_name"] == "gemini-2.5-flash"  # Varsayılan

    def test_load_merges_with_defaults(self, isolated_config):
        """Eksik alanlar varsayılan değerlerle tamamlanmalı."""
        fake_json, _ = isolated_config
        # Sadece model_name kaydet
        with open(fake_json, "w") as f:
            json.dump({"model_name": "o3"}, f)

        config = config_manager.load_config()
        assert config["model_name"] == "o3"
        assert config["api_key"] == ""  # Varsayılandan geldi
        assert config["max_tokens"] == 1024  # Varsayılandan geldi


# ================================================================
# .env API key yönetimi (S13 — Aşama 6.1)
# ================================================================

class TestEnvApiKey:
    """API anahtarının .env dosyasında yönetilmesi testleri."""

    def test_api_key_not_written_to_json(self, isolated_config):
        """save_config sonrası JSON dosyasında api_key OLMAMALI."""
        fake_json, fake_env = isolated_config
        config_manager.save_config({"api_key": "gizli-anahtar-12345",
                                    "model_name": "gpt-4o"})

        with open(fake_json, "r", encoding="utf-8") as f:
            saved_json = json.load(f)
        assert "api_key" not in saved_json

        # Key .env dosyasına yazılmış olmalı
        assert os.path.exists(fake_env)
        with open(fake_env, "r", encoding="utf-8") as f:
            env_content = f.read()
        assert "gizli-anahtar-12345" in env_content

    def test_legacy_json_key_migrates_to_env(self, isolated_config):
        """Eski JSON'daki api_key ilk yüklemede .env'e taşınmalı."""
        fake_json, fake_env = isolated_config
        with open(fake_json, "w", encoding="utf-8") as f:
            json.dump({"api_key": "eski-json-anahtari-99",
                       "model_name": "gpt-4o"}, f)

        config = config_manager.load_config()

        # Key config'de hala erişilebilir
        assert config["api_key"] == "eski-json-anahtari-99"
        # .env oluşturulmuş ve key oraya yazılmış
        assert os.path.exists(fake_env)
        # JSON'dan silinmiş
        with open(fake_json, "r", encoding="utf-8") as f:
            cleaned = json.load(f)
        assert "api_key" not in cleaned

    def test_env_file_takes_priority_over_os_env(self, isolated_config, monkeypatch):
        """.env dosyasındaki key, OS ortam değişkeninden öncelikli olmalı."""
        _, fake_env = isolated_config
        with open(fake_env, "w", encoding="utf-8") as f:
            f.write("API_KEY='dosyadan-gelen-anahtar'\n")
        monkeypatch.setenv("API_KEY", "ortamdan-gelen-anahtar")

        config = config_manager.load_config()
        assert config["api_key"] == "dosyadan-gelen-anahtar"

    def test_os_env_used_as_fallback(self, isolated_config, monkeypatch):
        """.env yoksa OS ortam değişkenindeki key kullanılmalı."""
        monkeypatch.setenv("API_KEY", "sistem-ortam-anahtari")
        config = config_manager.load_config()
        assert config["api_key"] == "sistem-ortam-anahtari"

    def test_action_field_not_persisted(self, isolated_config):
        """Çalışma zamanı alanı _action diske yazılmamalı."""
        fake_json, _ = isolated_config
        config_manager.save_config({"model_name": "gpt-4o", "_action": "start",
                                    "api_key": ""})
        with open(fake_json, "r", encoding="utf-8") as f:
            saved_json = json.load(f)
        assert "_action" not in saved_json
