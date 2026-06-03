"""
conftest.py — Pytest yapılandırma ve paylaşılan fixture'lar.

Proje kök dizinini sys.path'e ekler, böylece test dosyaları
game_state, ai_manager vs. modüllerini doğrudan import edebilir.
"""

import sys
import os

# Proje kök dizinini sys.path'e ekle
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from game_state import GameState, Character


@pytest.fixture
def default_character():
    """Varsayılan değerlerle bir Character oluşturur."""
    return Character()


@pytest.fixture
def warrior_character():
    """Savaşçı sınıfıyla yapılandırılmış bir Character oluşturur."""
    return Character(
        name="TestSavascisi",
        char_class="Savaşçı",
        hp=120,
        max_hp=120,
        gold=40,
        inventory=["Uzun Kılıç", "Mesale"],
        base_stats={"STR": 18, "DEX": 10, "INT": 6, "DEF": 14, "LUCK": 8},
        event_stats={"STR": 0, "DEX": 0, "INT": 0, "DEF": 0, "LUCK": 0},
    )


@pytest.fixture
def mage_character():
    """Büyücü sınıfıyla yapılandırılmış bir Character oluşturur."""
    return Character(
        name="TestBuyucusu",
        char_class="Büyücü",
        hp=80,
        max_hp=80,
        gold=80,
        inventory=["Ateş Asası", "Mesale"],
        base_stats={"STR": 6, "DEX": 10, "INT": 20, "DEF": 6, "LUCK": 14},
        event_stats={"STR": 0, "DEX": 0, "INT": 0, "DEF": 0, "LUCK": 0},
    )


@pytest.fixture
def game_state(default_character):
    """Varsayılan karakterle bir GameState oluşturur."""
    return GameState(default_character)


@pytest.fixture
def warrior_state(warrior_character):
    """Savaşçı karakterle bir GameState oluşturur."""
    return GameState(warrior_character)


@pytest.fixture
def mage_state(mage_character):
    """Büyücü karakterle bir GameState oluşturur."""
    return GameState(mage_character)
