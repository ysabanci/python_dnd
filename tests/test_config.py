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

class TestConfigIO:
    """Config dosya okuma/yazma testleri."""

    def test_load_default_when_no_file(self, tmp_path, monkeypatch):
        """Config dosyası yokken varsayılan değerler dönmeli."""
        fake_path = str(tmp_path / "nonexistent.json")
        monkeypatch.setattr(config_manager, "CONFIG_FILE", fake_path)

        config = config_manager.load_config()
        assert config["model_name"] == "gemini-2.5-flash"
        assert config["api_key"] == ""
        assert config["max_tokens"] == 1024

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        """Kaydedilen config yüklendiğinde aynı değerleri döndürmeli."""
        fake_path = str(tmp_path / "test_config.json")
        monkeypatch.setattr(config_manager, "CONFIG_FILE", fake_path)

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

    def test_load_corrupt_file_returns_defaults(self, tmp_path, monkeypatch):
        """Bozuk JSON dosyası varsayılan değerleri döndürmeli."""
        fake_path = str(tmp_path / "corrupt.json")
        monkeypatch.setattr(config_manager, "CONFIG_FILE", fake_path)

        with open(fake_path, "w") as f:
            f.write("{broken json...")

        config = config_manager.load_config()
        assert config["model_name"] == "gemini-2.5-flash"  # Varsayılan

    def test_load_merges_with_defaults(self, tmp_path, monkeypatch):
        """Eksik alanlar varsayılan değerlerle tamamlanmalı."""
        fake_path = str(tmp_path / "partial.json")
        monkeypatch.setattr(config_manager, "CONFIG_FILE", fake_path)

        # Sadece model_name kaydet
        with open(fake_path, "w") as f:
            json.dump({"model_name": "o3"}, f)

        config = config_manager.load_config()
        assert config["model_name"] == "o3"
        assert config["api_key"] == ""  # Varsayılandan geldi
        assert config["max_tokens"] == 1024  # Varsayılandan geldi
