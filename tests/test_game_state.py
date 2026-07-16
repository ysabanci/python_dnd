"""
test_game_state.py — GameState saf fonksiyonları için unit testler.

Bu testler mock gerektirmez; sadece input/output doğrulaması yapar.
Refactoring sırasında kırılırlarsa, davranış değişmiş demektir.
"""

import pytest
from game.core.game_state import GameState, Character


# ================================================================
# modify_hp
# ================================================================

class TestModifyHp:
    """HP değişikliği testleri."""

    def test_damage_reduces_hp(self, game_state):
        """Negatif değer HP'yi düşürmeli."""
        initial_hp = game_state.character.hp
        game_state.modify_hp(-10)
        assert game_state.character.hp == initial_hp - 10

    def test_healing_increases_hp(self, game_state):
        """Pozitif değer HP'yi artırmalı."""
        game_state.character.hp = 50
        game_state.modify_hp(20)
        assert game_state.character.hp == 70

    def test_hp_cannot_go_below_zero(self, game_state):
        """HP sıfırın altına düşmemeli."""
        game_state.modify_hp(-9999)
        assert game_state.character.hp == 0

    def test_hp_cannot_exceed_max(self, game_state):
        """HP max_hp'yi geçmemeli."""
        game_state.character.hp = 90
        game_state.modify_hp(9999)
        assert game_state.character.hp == game_state.character.max_hp

    def test_zero_change(self, game_state):
        """0 hasar/iyileşme HP'yi değiştirmemeli."""
        initial_hp = game_state.character.hp
        game_state.modify_hp(0)
        assert game_state.character.hp == initial_hp


# ================================================================
# modify_gold
# ================================================================

class TestModifyGold:
    """Altın değişikliği testleri."""

    def test_add_gold(self, game_state):
        """Altın eklenebilmeli."""
        initial = game_state.character.gold
        game_state.modify_gold(25)
        assert game_state.character.gold == initial + 25

    def test_remove_gold(self, game_state):
        """Altın çıkarılabilmeli."""
        game_state.character.gold = 100
        game_state.modify_gold(-30)
        assert game_state.character.gold == 70

    def test_gold_cannot_go_negative(self, game_state):
        """Altın negatife düşmemeli."""
        game_state.modify_gold(-9999)
        assert game_state.character.gold == 0


# ================================================================
# get_total_stats
# ================================================================

class TestGetTotalStats:
    """Toplam istatistik hesaplama testleri."""

    def test_base_stats_only(self, game_state):
        """Silah/event bonusu yokken sadece base stat döndürmeli."""
        game_state.equipped_items = []
        total = game_state.get_total_stats()
        assert total == game_state.character.base_stats

    def test_event_stats_added(self, game_state):
        """Event bonusları base'e eklenmeli."""
        game_state.equipped_items = []
        game_state.character.base_stats = {"STR": 10, "DEX": 10, "INT": 10, "DEF": 10, "LUCK": 10}
        game_state.character.event_stats = {"STR": 5, "DEX": 0, "INT": 3, "DEF": 0, "LUCK": 0}
        total = game_state.get_total_stats()
        assert total["STR"] == 15
        assert total["INT"] == 13
        assert total["DEX"] == 10  # Event 0 → değişmemeli

    def test_equipped_weapon_adds_stats(self, warrior_state):
        """Equip edilen silahın statları toplama eklenmeli."""
        warrior_state.equipped_items = ["Uzun Kılıç"]
        total = warrior_state.get_total_stats()
        weapon_stats = warrior_state.get_weapon_stats("Uzun Kılıç")
        # Silah STR bonusu eklenmiş olmalı
        base_str = warrior_state.character.base_stats["STR"]
        weapon_str = weapon_stats.get("stats", {}).get("STR", 0)
        assert total["STR"] == base_str + weapon_str


# ================================================================
# get_stat_effect_on_combat
# ================================================================

class TestGetStatEffectOnCombat:
    """Savaş etkisi hesaplama testleri."""

    def test_default_stats_effects(self, game_state):
        """Varsayılan (10) statlarda bonuslar 0 olmalı."""
        game_state.equipped_items = []
        effects = game_state.get_stat_effect_on_combat()
        assert effects["attack_bonus"] == 0
        assert effects["magic_bonus"] == 0
        assert effects["dodge_chance"] == 0
        assert effects["crit_bonus"] == 0

    def test_high_str_gives_attack_bonus(self, warrior_state):
        """Yüksek STR saldırı bonusu vermeli."""
        warrior_state.equipped_items = []
        effects = warrior_state.get_stat_effect_on_combat()
        # STR=18, bonus = max(0, 18-10) = 8
        assert effects["attack_bonus"] == 8

    def test_defense_reduction_capped(self, game_state):
        """DEF reduction %60'ta sınırlanmalı."""
        game_state.character.base_stats["DEF"] = 500
        game_state.equipped_items = []
        effects = game_state.get_stat_effect_on_combat()
        assert effects["defense_reduction"] == 0.6  # Cap

    def test_dodge_chance_capped(self, game_state):
        """Dodge şansı %30'da sınırlanmalı."""
        game_state.character.base_stats["DEX"] = 500
        game_state.equipped_items = []
        effects = game_state.get_stat_effect_on_combat()
        assert effects["dodge_chance"] == 0.30  # Cap


# ================================================================
# apply_class_choice
# ================================================================

class TestApplyClassChoice:
    """Sınıf seçimi uygulama testleri."""

    def test_warrior_class_applied(self, game_state):
        """Savaşçı sınıfı doğru değerler atamalı."""
        game_state.apply_class_choice("Savasci")
        assert game_state.character.char_class == "Savasci"
        assert game_state.character.hp == 120
        assert game_state.character.max_hp == 120
        assert game_state.character.base_stats["STR"] == 16

    def test_mage_class_applied(self, game_state):
        """Büyücü sınıfı doğru değerler atamalı."""
        game_state.apply_class_choice("Buyucu")
        assert game_state.character.char_class == "Buyucu"
        assert game_state.character.hp == 80
        assert game_state.character.max_hp == 80
        assert game_state.character.base_stats["INT"] == 18

    def test_event_stats_reset_on_class_change(self, game_state):
        """Sınıf değiştirildiğinde event statları sıfırlanmalı."""
        game_state.character.event_stats["STR"] = 10
        game_state.apply_class_choice("Savasci")
        assert game_state.character.event_stats["STR"] == 0


# ================================================================
# get_weapon_stats
# ================================================================

class TestGetWeaponStats:
    """Silah istatistik testleri."""

    def test_known_weapon_returns_stats(self, game_state):
        """Bilinen silah (WEAPON_STATS'ta olan) doğru stat döndürmeli."""
        stats = game_state.get_weapon_stats("Uzun Kılıç")
        assert "bonus" in stats
        assert "type" in stats
        assert "stats" in stats

    def test_unknown_weapon_generates_deterministic_stats(self, game_state):
        """Bilinmeyen silah için hash-bazlı deterministik stat üretilmeli."""
        stats1 = game_state.get_weapon_stats("Ejderha Kılıcı")
        stats2 = game_state.get_weapon_stats("Ejderha Kılıcı")
        # Aynı isim her zaman aynı sonuç vermeli
        assert stats1 == stats2

    def test_magic_weapon_detected(self, game_state):
        """Büyü anahtar kelimesi içeren silah büyüsel tip olmalı."""
        stats = game_state.get_weapon_stats("Ateş Asası")
        assert stats["type"] == "buyusel"

    def test_armor_detected(self, game_state):
        """Zırh anahtar kelimesi içeren eşya HP/DEF bonusu vermeli."""
        # Keyword listesinde ASCII 'zirh' var, Türkçe 'Zırh' değil
        stats = game_state.get_weapon_stats("Demir zirh")
        assert "HP" in stats["stats"] or "DEF" in stats["stats"]
        assert stats["type"] == "fiziksel"


# ================================================================
# toggle_equipped
# ================================================================

class TestToggleEquipped:
    """Silah equip/unequip testleri."""

    def test_equip_weapon(self, game_state):
        """Silah equip edilebilmeli."""
        game_state.character.inventory = ["Uzun Kılıç", "Mesale"]
        game_state.equipped_items = []
        result = game_state.toggle_equipped("Uzun Kılıç")
        assert result is True
        assert "Uzun Kılıç" in game_state.equipped_items

    def test_unequip_weapon(self, game_state):
        """Equip edilmiş silah unequip edilebilmeli."""
        game_state.equipped_items = ["Uzun Kılıç"]
        result = game_state.toggle_equipped("Uzun Kılıç")
        assert result is False
        assert "Uzun Kılıç" not in game_state.equipped_items

    def test_max_4_equipped(self, game_state):
        """4'ten fazla silah equip edilememeli."""
        game_state.equipped_items = ["A", "B", "C", "D"]
        result = game_state.toggle_equipped("E")
        assert result is False
        assert len(game_state.equipped_items) == 4

    def test_non_weapon_cannot_equip(self, game_state):
        """Non-weapon eşyalar (Mesale, Harita vs.) equip edilememeli."""
        game_state.equipped_items = []
        result = game_state.toggle_equipped("Mesale")
        assert result is False


# ================================================================
# get_combat_weapons
# ================================================================

class TestGetCombatWeapons:
    """Savaş silahları testleri."""

    def test_returns_equipped_items(self, game_state):
        """Equipped silahları döndürmeli."""
        game_state.character.inventory = ["Uzun Kılıç", "Kısa Kılıç", "Mesale"]
        game_state.equipped_items = ["Uzun Kılıç", "Kısa Kılıç"]
        weapons = game_state.get_combat_weapons()
        assert weapons == ["Uzun Kılıç", "Kısa Kılıç"]

    def test_removes_unowned_from_equipped(self, game_state):
        """Envanterde olmayan silahlar equipped'dan çıkarılmalı."""
        game_state.character.inventory = ["Mesale"]
        game_state.equipped_items = ["Uzun Kılıç"]  # Envanterde yok
        weapons = game_state.get_combat_weapons()
        assert weapons == []
        assert "Uzun Kılıç" not in game_state.equipped_items

    def test_max_4_weapons(self, game_state):
        """En fazla 4 silah döndürmeli."""
        game_state.character.inventory = ["A", "B", "C", "D", "E"]
        game_state.equipped_items = ["A", "B", "C", "D", "E"]
        weapons = game_state.get_combat_weapons()
        assert len(weapons) == 4


# ================================================================
# Inventory Operations
# ================================================================

class TestInventory:
    """Envanter ekleme/çıkarma testleri."""

    def test_add_to_inventory(self, game_state):
        """Eşya envantere eklenmeli."""
        game_state.add_to_inventory("Büyülü Yüzük")
        assert "Büyülü Yüzük" in game_state.character.inventory

    def test_no_duplicate_items(self, game_state):
        """Aynı eşya iki kez eklenmemeli."""
        game_state.add_to_inventory("Mesale")
        count = game_state.character.inventory.count("Mesale")
        assert count == 1

    def test_remove_from_inventory(self, game_state):
        """Eşya envanterden çıkarılabilmeli."""
        game_state.character.inventory.append("TestEsya")
        result = game_state.remove_from_inventory("TestEsya")
        assert result is True
        assert "TestEsya" not in game_state.character.inventory

    def test_remove_nonexistent_returns_false(self, game_state):
        """Var olmayan eşya çıkarmaya çalışınca False dönmeli."""
        result = game_state.remove_from_inventory("YokBoyleEsya")
        assert result is False


# ================================================================
# Shop System
# ================================================================

class TestShopSystem:
    """Dükkan sistemi testleri."""

    def test_init_shop_creates_3_items(self, game_state):
        """Shop başlatıldığında 3 item olmalı."""
        game_state.init_shop()
        items = game_state.get_shop_items()
        assert len(items) == 3

    def test_shop_items_have_required_fields(self, game_state):
        """Her shop item'ında stat, amount, cost olmalı."""
        game_state.init_shop()
        for item in game_state.get_shop_items():
            assert "stat" in item
            assert "amount" in item
            assert "cost" in item
            assert item["stat"] in ("STR", "DEX", "INT", "DEF", "LUCK")

    def test_shop_buy_success(self, game_state):
        """Yeterli altın varsa satın alma başarılı olmalı."""
        game_state.character.gold = 999
        game_state.init_shop()
        item = game_state.get_shop_items()[0]
        old_stat = game_state.character.event_stats[item["stat"]]
        result = game_state.shop_buy(0)
        assert result is True
        assert game_state.character.event_stats[item["stat"]] == old_stat + item["amount"]

    def test_shop_buy_insufficient_gold(self, game_state):
        """Yetersiz altınla satın alma başarısız olmalı."""
        game_state.character.gold = 0
        game_state.init_shop()
        result = game_state.shop_buy(0)
        assert result is False

    def test_shop_buy_invalid_index(self, game_state):
        """Geçersiz index ile satın alma başarısız olmalı."""
        game_state.init_shop()
        assert game_state.shop_buy(-1) is False
        assert game_state.shop_buy(99) is False

    def test_shop_roll_changes_items(self, game_state):
        """Roll sonrası shop item'ları değişmeli (çoğu zaman)."""
        game_state.character.gold = 999
        game_state.init_shop()
        old_items = list(game_state.get_shop_items())
        result = game_state.shop_roll()
        assert result is True
        # Roll maliyeti artmalı
        assert game_state.get_shop_roll_cost() == game_state.SHOP_ROLL_BASE_COST * 2

    def test_shop_roll_insufficient_gold(self, game_state):
        """Yetersiz altınla roll başarısız olmalı."""
        game_state.character.gold = 0
        game_state.init_shop()
        result = game_state.shop_roll()
        assert result is False


# ================================================================
# S02: HP Çift Uygulama Regresyon Testleri
# ================================================================

class TestHpDoubleApplication:
    """S02 fix: HP tag'leri artık uygulanmamalı, sadece temizlenmeli."""

    def test_hp_tag_not_applied(self, game_state):
        """[HP:-10] tag'i HP'yi düşürmemeli — sadece hp_degisim geçerli."""
        initial_hp = game_state.character.hp
        ai_response = {
            "hikaye_metni": "Canavar saldirdi [HP:-10]",
            "secenekler": {"sol_ust": "Saldır", "sag_ust": "Kaç", "sol_alt": "", "sag_alt": ""},
            "mod": "kesfet",
            "hp_degisim": 0,
            "altin_degisim": 0,
        }
        game_state.update_from_ai_response(ai_response)
        assert game_state.character.hp == initial_hp  # HP değişmemeli

    def test_hp_tag_cleaned_from_story(self, game_state):
        """[HP:-10] tag'i hikaye metninden temizlenmeli."""
        ai_response = {
            "hikaye_metni": "Canavar saldirdi [HP:-10] ama kurtuldun.",
            "secenekler": {"sol_ust": "Devam", "sag_ust": "", "sol_alt": "", "sag_alt": ""},
            "mod": "kesfet",
            "hp_degisim": 0,
            "altin_degisim": 0,
        }
        game_state.update_from_ai_response(ai_response)
        assert "[HP:" not in game_state.current_story

    def test_hp_degisim_still_works(self, game_state):
        """hp_degisim JSON alanı hala çalışmalı."""
        initial_hp = game_state.character.hp
        ai_response = {
            "hikaye_metni": "Bir tuzaga dusun.",
            "secenekler": {"sol_ust": "Devam", "sag_ust": "", "sol_alt": "", "sag_alt": ""},
            "mod": "kesfet",
            "hp_degisim": -15,
            "altin_degisim": 0,
        }
        game_state.update_from_ai_response(ai_response)
        assert game_state.character.hp == initial_hp - 15

    def test_no_double_hp_application(self, game_state):
        """S02 ana test: hem hp_degisim hem HP tag'i varsa, sadece hp_degisim uygulanmalı."""
        initial_hp = game_state.character.hp
        ai_response = {
            "hikaye_metni": "Canavar saldirdi [HP:-10]",
            "secenekler": {"sol_ust": "Saldır", "sag_ust": "Kaç", "sol_alt": "", "sag_alt": ""},
            "mod": "kesfet",
            "hp_degisim": -10,
            "altin_degisim": 0,
        }
        game_state.update_from_ai_response(ai_response)
        # Eski davranış: HP 20 düşerdi (10+10). Yeni davranış: sadece 10 düşmeli.
        assert game_state.character.hp == initial_hp - 10

    def test_esya_tag_still_works(self, game_state):
        """ESYA tag'leri hala çalışmalı (sadece HP kaldırıldı)."""
        ai_response = {
            "hikaye_metni": "Bir sandik buldun [ESYA:Buyulu Yuzuk]",
            "secenekler": {"sol_ust": "Devam", "sag_ust": "", "sol_alt": "", "sag_alt": ""},
            "mod": "kesfet",
            "hp_degisim": 0,
            "altin_degisim": 0,
        }
        game_state.update_from_ai_response(ai_response)
        assert "Buyulu Yuzuk" in game_state.character.inventory

    def test_altin_tag_still_works(self, game_state):
        """ALTIN tag'leri hala çalışmalı (sadece HP kaldırıldı)."""
        initial_gold = game_state.character.gold
        ai_response = {
            "hikaye_metni": "Hazine buldun [ALTIN:+20]",
            "secenekler": {"sol_ust": "Devam", "sag_ust": "", "sol_alt": "", "sag_alt": ""},
            "mod": "kesfet",
            "hp_degisim": 0,
            "altin_degisim": 0,
        }
        game_state.update_from_ai_response(ai_response)
        assert game_state.character.gold == initial_gold + 20


# ================================================================
# S12: reset() Regresyon Testleri
# ================================================================

class TestResetMethod:
    """S12 fix: reset() __init__ çağırmak yerine _reset_to_defaults kullanmalı."""

    def test_reset_produces_same_attributes(self, game_state):
        """reset() ile __init__ aynı attribute setini üretmeli."""
        fresh = GameState()
        fresh_attrs = set(vars(fresh).keys())

        # game_state'i kirlet
        game_state.turn_count = 999
        game_state.is_game_over = True
        game_state.current_mode = "savas"
        game_state.enemy_hp = 50

        game_state.reset()
        reset_attrs = set(vars(game_state).keys())

        # Attribute isimleri aynı olmalı
        assert fresh_attrs == reset_attrs, \
            f"Eksik: {fresh_attrs - reset_attrs}, Fazla: {reset_attrs - fresh_attrs}"

    def test_reset_clears_game_state(self, game_state):
        """reset() tüm oyun durumunu sıfırlamalı."""
        game_state.turn_count = 50
        game_state.is_game_over = True
        game_state.game_over_reason = "Oldu"
        game_state.current_mode = "savas"
        game_state.enemy_hp = 75
        game_state.current_story = "Eski hikaye"
        game_state.equipped_items = ["Kilic"]
        game_state.visited_locations = ["Orman"]
        game_state.npc_met = ["Gandalf"]
        game_state._api_error = True

        game_state.reset()

        assert game_state.turn_count == 0
        assert game_state.is_game_over is False
        assert game_state.game_over_reason == ""
        assert game_state.current_mode == "kesif"
        assert game_state.enemy_hp == 0
        assert game_state.equipped_items == []
        assert game_state.visited_locations == []
        assert game_state.npc_met == []
        assert game_state._api_error is False

    def test_reset_creates_fresh_character(self, game_state):
        """reset() yeni Character oluşturmalı."""
        game_state.character.hp = 1
        game_state.character.gold = 999
        game_state.character.name = "OldName"

        game_state.reset()

        assert game_state.character.hp == 100  # Varsayılan
        assert game_state.character.gold == 50  # Varsayılan
        assert game_state.character.name == "Kahraman"

    def test_reset_reinitializes_system_prompt(self, game_state):
        """reset() sonrası mesaj geçmişinde sistem prompt'u olmalı."""
        game_state.reset()
        history = game_state.get_message_history()
        assert len(history) >= 1
        assert history[0]["role"] == "system"

    def test_reset_does_not_call_init_directly(self):
        """reset() kodunda __init__ çağrısı olmamalı."""
        import inspect
        source = inspect.getsource(GameState.reset)
        # Docstring'i çıkar — sadece fonksiyon gövdesini kontrol et
        lines = source.split('\n')
        code_lines = []
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if in_docstring:
                    in_docstring = False
                    continue
                elif stripped.count('"""') == 2 or stripped.count("'''") == 2:
                    continue  # tek satırlık docstring
                else:
                    in_docstring = True
                    continue
            if not in_docstring:
                code_lines.append(line)
        code_body = '\n'.join(code_lines)
        assert "__init__" not in code_body, \
            "reset() gövdesinde __init__ çağrısı var! _reset_to_defaults kullanılmalı."
