"""
test_snapshots.py — Characterization (Snapshot) Testleri.

God Object'lerdeki karmaşık metodların davranışını dondurur.
Bilinen bir GameState oluşturulur, sahte AI yanıtı verilir,
çıkan state kontrol edilir. Refactoring sırasında davranış
değişirse bu testler kırılır.

NOT: Bu testler "doğru davranışı" değil "mevcut davranışı" test eder.
Bir bug düzeltildiğinde ilgili snapshot testi de güncellenmeli.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_state import GameState, Character


def _make_state(
    char_class="Savaşçı",
    hp=100, max_hp=100, gold=50,
    inventory=None, mode="kesif",
    equipped=None,
):
    """Bilinen değerlerle test state oluşturur."""
    char = Character(
        name="SnapshotKarakter",
        char_class=char_class,
        hp=hp, max_hp=max_hp, gold=gold,
        inventory=inventory or ["Uzun Kılıç", "Mesale"],
        base_stats={"STR": 18, "DEX": 10, "INT": 6, "DEF": 14, "LUCK": 8},
        event_stats={"STR": 0, "DEX": 0, "INT": 0, "DEF": 0, "LUCK": 0},
    )
    state = GameState(char)
    state.current_mode = mode
    state.equipped_items = equipped or ["Uzun Kılıç"]
    return state


# ================================================================
# Keşif Modu Snapshot'ları
# ================================================================

class TestExplorationSnapshots:
    """Keşif modunda AI yanıtı sonrası state değişimleri."""

    def test_basic_exploration_response(self):
        """Basit keşif yanıtı: hikaye + seçenekler güncellenmeli."""
        state = _make_state(mode="kesif")
        initial_turn = state.turn_count

        ai_response = {
            "hikaye_metni": "Karanlık bir ormana girdin.",
            "feedback": "Dikkatli ol!",
            "mod": "kesif",
            "hp_degisim": -5,
            "altin_degisim": 10,
            "secenekler": {
                "sol_ust": "İlerle",
                "sag_ust": "Geri dön",
                "sol_alt": "Etrafa bak",
                "sag_alt": "Kamp kur",
            },
        }
        state.update_from_ai_response(ai_response)

        # Hikaye güncellendi
        assert state.current_story == "Karanlık bir ormana girdin."
        assert state.current_feedback == "Dikkatli ol!"
        # Mod keşif kaldı
        assert state.current_mode == "kesif"
        # HP düştü (keşif modunda hp_degisim uygulanır)
        assert state.character.hp == 95
        # Altın arttı
        assert state.character.gold == 60
        # Tur sayısı arttı
        assert state.turn_count == initial_turn + 1
        # 4 seçenek var
        assert state.active_option_count == 4
        assert state.current_options["sol_ust"] == "İlerle"

    def test_exploration_with_loot(self):
        """Keşif sırasında gelen eşya pending_loot'ta tutulmalı."""
        state = _make_state(mode="kesif")
        ai_response = {
            "hikaye_metni": "Bir sandık buldun!",
            "feedback": "",
            "mod": "kesif",
            "yeni_esya": "Büyülü Yüzük",
            "secenekler": {
                "sol_ust": "Al", "sag_ust": "Bırak",
                "sol_alt": "", "sag_alt": "",
            },
        }
        state.update_from_ai_response(ai_response)

        # Eşya envantere EKLENMEDİ, beklemede
        assert state.pending_loot == "Büyülü Yüzük"
        assert "Büyülü Yüzük" not in state.character.inventory

    def test_exploration_with_stat_change(self):
        """Stat değişimi doğru uygulanmalı."""
        state = _make_state(mode="kesif")
        ai_response = {
            "hikaye_metni": "Antrenman yaptın!",
            "feedback": "",
            "mod": "kesif",
            "stat_degisim": {"str": 3, "dex": -1},
            "secenekler": {
                "sol_ust": "A", "sag_ust": "B",
                "sol_alt": "C", "sag_alt": "D",
            },
        }
        state.update_from_ai_response(ai_response)

        assert state.character.event_stats["STR"] == 3
        assert state.character.event_stats["DEX"] == -1

    def test_exploration_with_world_tracking(self):
        """Dünya takibi (alt bölge, NPC, etkileşim) güncellenmeli."""
        state = _make_state(mode="kesif")
        ai_response = {
            "hikaye_metni": "Kasaba meydanına geldin.",
            "feedback": "",
            "mod": "kesif",
            "alt_bolge": "Kasaba Meydanı",
            "npc_adi": "Demirci Hasan",
            "etkilesim": "Demirci ile konuştun",
            "secenekler": {
                "sol_ust": "A", "sag_ust": "B",
                "sol_alt": "C", "sag_alt": "D",
            },
        }
        state.update_from_ai_response(ai_response)

        assert state.current_sub_location == "Kasaba Meydanı"
        assert "Kasaba Meydanı" in state.visited_locations
        assert "Demirci Hasan" in state.npc_met
        assert "Demirci ile konuştun" in state.interactions


# ================================================================
# Savaş Modu Snapshot'ları
# ================================================================

class TestCombatSnapshots:
    """Savaş modunda AI yanıtı sonrası state değişimleri."""

    def test_entering_combat(self):
        """Savaşa girildiğinde düşman HP başlatılmalı, HP düşmemeli."""
        state = _make_state(mode="kesif", hp=100)
        ai_response = {
            "hikaye_metni": "Bir goblin saldırıyor!",
            "feedback": "Savaş başladı!",
            "mod": "savas",
            "hp_degisim": -15,  # Bu guard'lanmalı
            "secenekler": {
                "sol_ust": "Saldır", "sag_ust": "Savun",
                "sol_alt": "Kaç", "sag_alt": "Büyü",
            },
        }
        state.update_from_ai_response(ai_response)

        assert state.current_mode == "savas"
        # Düşman HP başlatıldı
        assert state.enemy_hp == state.enemy_max_hp
        # HP değişmedi (savaşa giriş guard'ı)
        assert state.character.hp == 100
        # 4 seçenek zorunlu
        assert state.active_option_count == 4

    def test_combat_hp_guard(self):
        """Savaş modunda hp_degisim sıfırlanmalı (challenge yönetiyor)."""
        state = _make_state(mode="savas", hp=80)
        state.enemy_hp = 50
        ai_response = {
            "hikaye_metni": "Goblin saldırdı!",
            "feedback": "",
            "mod": "savas",
            "hp_degisim": -20,  # Guard'lanmalı
            "secenekler": {
                "sol_ust": "Saldır", "sag_ust": "Savun",
                "sol_alt": "Kaç", "sag_alt": "Büyü",
            },
        }
        state.update_from_ai_response(ai_response)

        # HP değişmemeli
        assert state.character.hp == 80

    def test_dialogue_hp_guard(self):
        """Diyalog modunda HP düşmemeli."""
        state = _make_state(mode="diyalog", hp=100)
        ai_response = {
            "hikaye_metni": "NPC ile konuşuyorsun.",
            "feedback": "",
            "mod": "diyalog",
            "hp_degisim": -10,  # Guard'lanmalı
            "secenekler": {
                "sol_ust": "A", "sag_ust": "B",
                "sol_alt": "C", "sag_alt": "D",
            },
        }
        state.update_from_ai_response(ai_response)

        assert state.character.hp == 100


# ================================================================
# Seçenek Filtreleme Snapshot'ları
# ================================================================

class TestOptionFilteringSnapshots:
    """Seçenek sayısı ve filtreleme davranışı."""

    def test_empty_options_filtered(self):
        """Boş seçenekler filtrelenmeli, minimum 2 kalmalı."""
        state = _make_state(mode="kesif")
        ai_response = {
            "hikaye_metni": "Test",
            "feedback": "",
            "mod": "kesif",
            "secenek_sayisi": 4,
            "secenekler": {
                "sol_ust": "İlerle",
                "sag_ust": "",
                "sol_alt": "...",
                "sag_alt": "Geri dön",
            },
        }
        state.update_from_ai_response(ai_response)

        # Boş ve "..." olan seçenekler filtrelendi
        filled = [v for v in state.current_options.values() if v]
        assert len(filled) == 2
        assert state.active_option_count == 2

    def test_two_option_mode(self):
        """secenek_sayisi=2 olduğunda sadece 2 seçenek aktif olmalı."""
        state = _make_state(mode="kesif")
        ai_response = {
            "hikaye_metni": "Yol ayrımı.",
            "feedback": "",
            "mod": "kesif",
            "secenek_sayisi": 2,
            "secenekler": {
                "sol_ust": "Sol yol",
                "sag_ust": "Sağ yol",
                "sol_alt": "Bu görünmemeli",
                "sag_alt": "Bu da görünmemeli",
            },
        }
        state.update_from_ai_response(ai_response)

        assert state.active_option_count == 2
        assert state.current_options["sol_ust"] == "Sol yol"
        assert state.current_options["sag_ust"] == "Sağ yol"
        # Alt seçenekler boş olmalı
        assert state.current_options["sol_alt"] == ""
        assert state.current_options["sag_alt"] == ""


# ================================================================
# Game Over Snapshot
# ================================================================

class TestGameOverSnapshot:
    """Oyun bitiş koşulları."""

    def test_game_over_on_zero_hp(self):
        """HP sıfıra düşünce oyun bitmeli."""
        state = _make_state(mode="kesif", hp=5)
        ai_response = {
            "hikaye_metni": "Ağır bir darbe yedin!",
            "feedback": "",
            "mod": "kesif",
            "hp_degisim": -10,
            "secenekler": {
                "sol_ust": "A", "sag_ust": "B",
                "sol_alt": "C", "sag_alt": "D",
            },
        }
        state.update_from_ai_response(ai_response)

        assert state.character.hp == 0
        assert state.is_game_over is True
        assert "can" in state.game_over_reason.lower() or "tukendi" in state.game_over_reason.lower()
