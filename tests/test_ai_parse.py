"""
test_ai_parse.py — AI yanıt ayrıştırma testleri.

ai_manager.py'deki _parse_response metodunu test eder.
Bu metod AI'dan gelen ham metni JSON'a çevirir.

NOT: litellm modül seviyesinde import edildiği için,
test ortamında litellm yüklü olmasa bile çalışması
için sys.modules'a sahte bir modül ekliyoruz.
"""

import pytest
import sys
import os
import json
from unittest.mock import MagicMock

# litellm'i mock'la — çünkü ai_manager.py modül seviyesinde import ediyor
# ve test ortamında yüklü olmayabilir
if "litellm" not in sys.modules:
    mock_litellm = MagicMock()
    mock_litellm.suppress_debug_info = True
    mock_litellm.set_verbose = False
    sys.modules["litellm"] = mock_litellm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_manager import AdventureAI


@pytest.fixture
def ai():
    """API key olmadan AdventureAI oluşturur (sadece parse testi için)."""
    # __init__'te API key kontrolü var, mock ile atlıyoruz
    obj = object.__new__(AdventureAI)
    obj._api_key = "test-key"
    obj._model = "test-model"
    obj._max_tokens = 1024
    obj._last_response = None
    obj._last_error = None
    obj._is_requesting = False
    obj._lock = __import__("threading").Lock()
    return obj


# ================================================================
# Başarılı Parse Senaryoları
# ================================================================

class TestParseResponseSuccess:
    """Başarılı JSON parse testleri."""

    def test_clean_json(self, ai):
        """Temiz JSON doğrudan parse edilmeli."""
        raw = json.dumps({
            "hikaye_metni": "Bir ormana girdin.",
            "feedback": "İyi seçim!",
            "secenekler": {
                "sol_ust": "İlerle",
                "sag_ust": "Geri dön",
                "sol_alt": "Bekle",
                "sag_alt": "Koş"
            }
        }, ensure_ascii=False)
        result = ai._parse_response(raw)
        assert result["hikaye_metni"] == "Bir ormana girdin."
        assert "secenekler" in result
        assert result["secenekler"]["sol_ust"] == "İlerle"

    def test_json_with_markdown_wrapper(self, ai):
        """Markdown code block içindeki JSON parse edilmeli."""
        raw = '```json\n{"hikaye_metni": "Test", "secenekler": {"sol_ust": "A", "sag_ust": "B", "sol_alt": "C", "sag_alt": "D"}}\n```'
        result = ai._parse_response(raw)
        assert result["hikaye_metni"] == "Test"

    def test_json_with_surrounding_text(self, ai):
        """JSON öncesi/sonrasında metin olsa da parse edilmeli."""
        raw = 'İşte yanıtım:\n{"hikaye_metni": "Macera", "secenekler": {"sol_ust": "A", "sag_ust": "B", "sol_alt": "C", "sag_alt": "D"}}\nUmarım beğenirsin!'
        result = ai._parse_response(raw)
        assert result["hikaye_metni"] == "Macera"

    def test_json_with_hp_field(self, ai):
        """hp_degisim alanı olan JSON doğru parse edilmeli."""
        raw = json.dumps({
            "hikaye_metni": "Düştün!",
            "feedback": "",
            "hp_degisim": -10,
            "secenekler": {
                "sol_ust": "A", "sag_ust": "B",
                "sol_alt": "C", "sag_alt": "D"
            }
        })
        result = ai._parse_response(raw)
        assert result["hp_degisim"] == -10

    def test_json_with_combat_fields(self, ai):
        """Savaş modu alanları doğru parse edilmeli."""
        raw = json.dumps({
            "hikaye_metni": "Düşman saldırıyor!",
            "feedback": "",
            "mod": "savas",
            "dusman_hp": 80,
            "dusman_max_hp": 100,
            "secenekler": {
                "sol_ust": "Saldır", "sag_ust": "Savun",
                "sol_alt": "Kaç", "sag_alt": "Büyü"
            }
        })
        result = ai._parse_response(raw)
        assert result["mod"] == "savas"
        assert result["dusman_hp"] == 80


# ================================================================
# Fallback Senaryoları
# ================================================================

class TestParseResponseFallback:
    """Parse başarısız olduğunda fallback testleri."""

    def test_completely_invalid_input(self, ai):
        """Tamamen geçersiz girdi fallback döndürmeli."""
        result = ai._parse_response("Bu bir JSON değil, düz metin.")
        assert "hikaye_metni" in result
        assert "secenekler" in result
        # Fallback mesajı içermeli
        assert "okunamadi" in result["hikaye_metni"].lower() or "hata" in result.get("feedback", "").lower()

    def test_empty_input(self, ai):
        """Boş girdi fallback döndürmeli."""
        result = ai._parse_response("")
        assert "hikaye_metni" in result
        assert "secenekler" in result

    def test_partial_json(self, ai):
        """Eksik JSON (kapanmamış bracket) fallback döndürmeli."""
        result = ai._parse_response('{"hikaye_metni": "Test", "secenekler":')
        # Ya parse edebilir ya da fallback döner — her iki durumda da crash olmamalı
        assert "hikaye_metni" in result

    def test_json_without_required_fields(self, ai):
        """Gerekli alanları olmayan JSON — ya olduğu gibi döner ya da fallback."""
        raw = '{"random_field": "value"}'
        result = ai._parse_response(raw)
        # _parse_response hikaye_metni+secenekler yoksa regex'e devam ediyor
        # Sonuçta ya data döner ya da fallback — crash olmamalı
        assert isinstance(result, dict)
