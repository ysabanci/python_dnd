"""
test_prompts.py — PromptBuilder birim testleri.

prompt_builder.py'deki PromptBuilder sınıfını doğrudan test eder.
Tüm fonksiyonlar @staticmethod ve saf (pure) olduğu için
GameState veya mock gerekmez.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.core.prompt_builder import PromptBuilder


# ================================================================
# build_system_prompt
# ================================================================

class TestBuildSystemPrompt:
    """Sistem prompt testleri."""

    def test_returns_string(self):
        """Sistem prompt string döndürmeli."""
        result = PromptBuilder.build_system_prompt()
        assert isinstance(result, str)

    def test_contains_dnd_context(self):
        """D&D bağlamı içermeli."""
        result = PromptBuilder.build_system_prompt()
        assert "Dungeons" in result
        assert "Dragons" in result

    def test_contains_json_instruction(self):
        """JSON formatı talimatı içermeli."""
        result = PromptBuilder.build_system_prompt()
        assert "JSON" in result

    def test_contains_mode_definitions(self):
        """Mod tanımları içermeli (kesif, savas, diyalog)."""
        result = PromptBuilder.build_system_prompt()
        assert "kesif" in result
        assert "savas" in result
        assert "diyalog" in result

    def test_contains_combat_rules(self):
        """Savaş kuralları içermeli."""
        result = PromptBuilder.build_system_prompt()
        assert "Saldir" in result
        assert "Savun" in result
        assert "Kac" in result
        assert "Buyu" in result

    def test_contains_option_keys(self):
        """Seçenek key'leri içermeli."""
        result = PromptBuilder.build_system_prompt()
        assert "sol_ust" in result
        assert "sag_ust" in result
        assert "sol_alt" in result
        assert "sag_alt" in result

    def test_contains_hp_degisim_field(self):
        """hp_degisim alanı talimatı içermeli."""
        result = PromptBuilder.build_system_prompt()
        assert "hp_degisim" in result

    def test_contains_item_system(self):
        """Eşya sistemi talimatları içermeli."""
        result = PromptBuilder.build_system_prompt()
        assert "yeni_esya" in result

    def test_contains_world_tracking(self):
        """Dünya takibi talimatları içermeli."""
        result = PromptBuilder.build_system_prompt()
        assert "alt_bolge" in result
        assert "npc_adi" in result

    def test_idempotent(self):
        """Birden fazla çağrı aynı sonucu vermeli (saf fonksiyon)."""
        result1 = PromptBuilder.build_system_prompt()
        result2 = PromptBuilder.build_system_prompt()
        assert result1 == result2


# ================================================================
# build_character_summary
# ================================================================

class TestBuildCharacterSummary:
    """Karakter özeti testleri."""

    def test_contains_all_fields(self):
        """Tüm karakter alanları dahil edilmeli."""
        result = PromptBuilder.build_character_summary(
            name="Kahraman",
            char_class="Savasci",
            hp=100,
            max_hp=120,
            gold=50,
            total_stats={"STR": 16, "DEX": 10, "INT": 8, "DEF": 14, "LUCK": 8},
            inventory=["Celik Kilic", "Mesale"],
            current_location="Karanlik Magara",
            current_sub_location="Giris Tuneli",
            turn_count=5,
        )
        assert "Kahraman" in result
        assert "Savasci" in result
        assert "100/120" in result
        assert "50" in result
        assert "STR:16" in result
        assert "Celik Kilic" in result
        assert "Karanlik Magara" in result
        assert "Giris Tuneli" in result
        assert "5" in result

    def test_empty_inventory(self):
        """Boş envanter 'Bos' yazmalı."""
        result = PromptBuilder.build_character_summary(
            name="Test", char_class="Test", hp=100, max_hp=100,
            gold=0, total_stats={}, inventory=[],
            current_location="", current_sub_location="", turn_count=0,
        )
        assert "Bos" in result

    def test_multiple_inventory_items(self):
        """Birden fazla eşya virgülle ayrılmalı."""
        result = PromptBuilder.build_character_summary(
            name="Test", char_class="Test", hp=100, max_hp=100,
            gold=0, total_stats={}, inventory=["Kilic", "Kalkan", "Iksir"],
            current_location="", current_sub_location="", turn_count=0,
        )
        assert "Kilic, Kalkan, Iksir" in result

    def test_stats_formatted(self):
        """Statlar 'KEY:VALUE' formatında olmalı."""
        result = PromptBuilder.build_character_summary(
            name="Test", char_class="Test", hp=100, max_hp=100,
            gold=0, total_stats={"STR": 20, "INT": 5},
            inventory=[], current_location="", current_sub_location="",
            turn_count=0,
        )
        assert "STR:20" in result
        assert "INT:5" in result

    def test_starts_with_prefix(self):
        """'[Karakter Durumu]' ön eki ile başlamalı."""
        result = PromptBuilder.build_character_summary(
            name="Test", char_class="Test", hp=1, max_hp=1,
            gold=0, total_stats={}, inventory=[],
            current_location="", current_sub_location="", turn_count=0,
        )
        assert result.startswith("[Karakter Durumu]")


# ================================================================
# build_world_context
# ================================================================

class TestBuildWorldContext:
    """Dünya bağlamı testleri."""

    def test_empty_returns_empty_string(self):
        """Tüm listeler boşsa boş string dönmeli."""
        result = PromptBuilder.build_world_context(
            visited_locations=[], npc_met=[], interactions=[],
            location_history=[], can_go_back=False,
        )
        assert result == ""

    def test_visited_locations_included(self):
        """Gezilen bölgeler dahil edilmeli."""
        result = PromptBuilder.build_world_context(
            visited_locations=["Magara Girisi", "Taş Oda"],
            npc_met=[], interactions=[],
            location_history=[], can_go_back=False,
        )
        assert "[Gezilen Bolgeler]" in result
        assert "Magara Girisi" in result
        assert "Taş Oda" in result

    def test_visited_locations_max_8(self):
        """En fazla son 8 konum gösterilmeli."""
        locations = [f"Bolge_{i}" for i in range(12)]
        result = PromptBuilder.build_world_context(
            visited_locations=locations,
            npc_met=[], interactions=[],
            location_history=[], can_go_back=False,
        )
        # İlk 4 olmamalı (0-3), son 8 olmalı (4-11)
        assert "Bolge_0" not in result
        assert "Bolge_3" not in result
        assert "Bolge_4" in result
        assert "Bolge_11" in result

    def test_npc_met_included(self):
        """Tanışılan NPC'ler dahil edilmeli."""
        result = PromptBuilder.build_world_context(
            visited_locations=[], npc_met=["Gandalf", "Elrond"],
            interactions=[], location_history=[], can_go_back=False,
        )
        assert "[Taninan NPC'ler]" in result
        assert "Gandalf" in result

    def test_npc_met_max_6(self):
        """En fazla son 6 NPC gösterilmeli."""
        npcs = [f"NPC_{i}" for i in range(10)]
        result = PromptBuilder.build_world_context(
            visited_locations=[], npc_met=npcs,
            interactions=[], location_history=[], can_go_back=False,
        )
        assert "NPC_0" not in result
        assert "NPC_3" not in result
        assert "NPC_4" in result
        assert "NPC_9" in result

    def test_interactions_included(self):
        """Etkileşimler dahil edilmeli."""
        result = PromptBuilder.build_world_context(
            visited_locations=[], npc_met=[],
            interactions=["Sandigi acti", "Kopruyu gecti"],
            location_history=[], can_go_back=False,
        )
        assert "[Son Etkilesimler]" in result
        assert "Sandigi acti" in result

    def test_go_back_available(self):
        """Geri dönülebilir konum ve seçenek metni."""
        result = PromptBuilder.build_world_context(
            visited_locations=[], npc_met=[], interactions=[],
            location_history=["Magara Girisi"],
            can_go_back=True,
        )
        assert "[Geri Donulebilir Konum]" in result
        assert "Magara Girisi" in result
        assert "Geri don secenegi sunulabilir" in result

    def test_go_back_false_no_message(self):
        """can_go_back=False ise geri dön mesajı olmamalı."""
        result = PromptBuilder.build_world_context(
            visited_locations=[], npc_met=[], interactions=[],
            location_history=["Test"],
            can_go_back=False,
        )
        assert "Geri don secenegi sunulabilir" not in result

    def test_combined_context(self):
        """Tüm veriler birleştirilmeli."""
        result = PromptBuilder.build_world_context(
            visited_locations=["Yer1"],
            npc_met=["NPC1"],
            interactions=["Eylem1"],
            location_history=["GeriYer"],
            can_go_back=True,
        )
        assert "[Gezilen Bolgeler]" in result
        assert "[Taninan NPC'ler]" in result
        assert "[Son Etkilesimler]" in result
        assert "[Geri Donulebilir Konum]" in result


# ================================================================
# build_dynamic_prompt — Keşif senaryoları
# ================================================================

class TestDynamicPromptExploration:
    """Keşif modu prompt testleri."""

    def _base_params(self, **overrides):
        """Varsayılan keşif parametreleri."""
        defaults = dict(
            choice_text="Ilerle",
            current_theme="Karanlik Magara",
            theme_lore="Karanlik bir magara.",
            turn_count=5,
            current_story="Onceki hikaye.",
            current_mode="kesif",
            pending_combat_result=None,
            enemy_hp=0,
            enemy_max_hp=0,
            is_in_combat=False,
            last_combat_turn=0,
            next_combat_turn=20,  # uzak gelecek
            pending_loot="",
            world_context="",
            character_summary="[Karakter] Test",
        )
        defaults.update(overrides)
        return defaults

    def test_basic_exploration(self):
        """Basit keşif prompt'u oluşturulmalı."""
        prompt, effects = PromptBuilder.build_dynamic_prompt(**self._base_params())
        assert "Secimim: Ilerle" in prompt
        assert "Tema: Karanlik Magara" in prompt
        assert "Adim No: 6" in prompt  # turn_count + 1
        assert "Kesfe devam" in prompt

    def test_no_side_effects_in_exploration(self):
        """Keşif modunda side-effect olmamalı."""
        _, effects = PromptBuilder.build_dynamic_prompt(**self._base_params())
        assert effects["clear_combat_result"] is False
        assert effects["enter_combat"] is False
        assert effects["update_combat_turn"] is None
        assert effects["next_combat_turn"] is None

    def test_story_repeat_prevention(self):
        """Önceki hikaye tekrar engelleme metni içermeli."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(**self._base_params())
        assert "SAKIN AYNI SEYLERI TEKRAR ETME" in prompt

    def test_long_story_truncated(self):
        """100 karakterden uzun hikaye kısaltılmalı."""
        long_story = "A" * 150
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._base_params(current_story=long_story))
        assert "..." in prompt
        # 100 karakter + "..." olmalı
        assert "A" * 100 in prompt
        assert "A" * 101 not in prompt

    def test_empty_story_no_prevention(self):
        """Boş hikaye varsa tekrar engelleme metni olmamalı."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._base_params(current_story=""))
        assert "SAKIN AYNI SEYLERI TEKRAR ETME" not in prompt

    def test_pending_loot_included(self):
        """Bekleyen ganimet bilgisi dahil edilmeli."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._base_params(pending_loot="Ates Kilici"))
        assert "BEKLEYEN GANIMET" in prompt
        assert "Ates Kilici" in prompt

    def test_no_loot_no_message(self):
        """Ganimet yoksa ganimet mesajı olmamalı."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._base_params(pending_loot=""))
        assert "BEKLEYEN GANIMET" not in prompt

    def test_character_summary_appended(self):
        """Karakter özeti eklenmeli."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._base_params(character_summary="[Karakter] TestHero"))
        assert "[Karakter] TestHero" in prompt

    def test_world_context_appended(self):
        """Dünya bağlamı eklenmeli."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._base_params(world_context="[Gezilen Bolgeler] Test"))
        assert "[Gezilen Bolgeler] Test" in prompt


# ================================================================
# build_dynamic_prompt — Savaş senaryoları
# ================================================================

class TestDynamicPromptCombat:
    """Savaş modu prompt testleri."""

    def _combat_params(self, **overrides):
        """Varsayılan savaş parametreleri."""
        defaults = dict(
            choice_text="Saldir",
            current_theme="Karanlik Magara",
            theme_lore="Karanlik bir magara.",
            turn_count=10,
            current_story="Dusman saldirdi.",
            current_mode="savas",
            pending_combat_result={"accuracy": 85, "action": "Saldir"},
            enemy_hp=50,
            enemy_max_hp=100,
            is_in_combat=True,
            last_combat_turn=9,
            next_combat_turn=20,
            pending_loot="",
            world_context="",
            character_summary="[Karakter] Test",
        )
        defaults.update(overrides)
        return defaults

    def test_attack_success(self):
        """Başarılı saldırı (>=70) prompt'u."""
        prompt, effects = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(
                pending_combat_result={"accuracy": 85, "action": "Saldir"}
            ))
        assert "BASARIYLA gerceklestirdi" in prompt
        assert effects["clear_combat_result"] is True

    def test_attack_partial(self):
        """Kısmi başarılı saldırı (40-69) prompt'u."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(
                pending_combat_result={"accuracy": 55, "action": "Saldir"}
            ))
        assert "KISMI BASARIYLA" in prompt

    def test_attack_fail(self):
        """Başarısız saldırı (<40) prompt'u."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(
                pending_combat_result={"accuracy": 20, "action": "Saldir"}
            ))
        assert "BASARISIZ" in prompt

    def test_defense_success(self):
        """Başarılı savunma prompt'u."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(
                pending_combat_result={"accuracy": 80, "action": "Savun"}
            ))
        assert "SAVUNMA yapti" in prompt
        assert "BASARILI oldu" in prompt
        assert "Hasar tamamen engellendi" in prompt

    def test_defense_partial(self):
        """Kısmi başarılı savunma prompt'u."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(
                pending_combat_result={"accuracy": 50, "action": "Savun"}
            ))
        assert "KISMI BASARILI" in prompt

    def test_defense_fail(self):
        """Başarısız savunma prompt'u."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(
                pending_combat_result={"accuracy": 25, "action": "Savun"}
            ))
        assert "BASARISIZ oldu" in prompt

    def test_flee_success(self):
        """Başarılı kaçış prompt'u."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(
                pending_combat_result={"accuracy": 75, "action": "Kac"}
            ))
        assert "Kacis BASARILI" in prompt
        assert "mod='kesif'" in prompt

    def test_flee_fail(self):
        """Başarısız kaçış prompt'u."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(
                pending_combat_result={"accuracy": 30, "action": "Kac"}
            ))
        assert "Kacamadi" in prompt
        assert "mod='savas' kalsin" in prompt

    def test_enemy_hp_shown(self):
        """Düşman HP bilgisi gösterilmeli."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(enemy_hp=50, enemy_max_hp=100))
        assert "Dusman HP: 50/100" in prompt

    def test_enemy_defeated(self):
        """Düşman yenildiğinde (HP<=0) özel mesaj."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(enemy_hp=0, enemy_max_hp=100))
        assert "DUSMAN YENILDI" in prompt

    def test_combat_result_clears(self):
        """Savaş sonucu varsa clear_combat_result True olmalı."""
        _, effects = PromptBuilder.build_dynamic_prompt(
            **self._combat_params())
        assert effects["clear_combat_result"] is True

    def test_magic_action(self):
        """Büyü aksiyonu prompt'u."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._combat_params(
                pending_combat_result={"accuracy": 90, "action": "Buyu"}
            ))
        assert "'Buyu' hamlesini" in prompt
        assert "BASARIYLA" in prompt


# ================================================================
# build_dynamic_prompt — Savaş zamanlama ve keşif devam
# ================================================================

class TestDynamicPromptCombatTiming:
    """Savaş zamanlama ve keşif sürdürme testleri."""

    def _timing_params(self, **overrides):
        """Savaş zamanlama test parametreleri."""
        defaults = dict(
            choice_text="Ilerle",
            current_theme="Gizemli Orman",
            theme_lore="Buyulu orman.",
            turn_count=10,
            current_story="Ormanda yuruduk.",
            current_mode="kesif",
            pending_combat_result=None,
            enemy_hp=0,
            enemy_max_hp=0,
            is_in_combat=False,
            last_combat_turn=0,
            next_combat_turn=10,  # tam bu turda savaş!
            pending_loot="",
            world_context="",
            character_summary="[Karakter] Test",
        )
        defaults.update(overrides)
        return defaults

    def test_combat_trigger(self):
        """turn_count >= next_combat_turn ise savaş başlamalı."""
        prompt, effects = PromptBuilder.build_dynamic_prompt(
            **self._timing_params(turn_count=10, next_combat_turn=10))
        assert "DUSMAN CIKAR" in prompt
        assert effects["enter_combat"] is True
        assert effects["update_combat_turn"] == 10
        assert effects["next_combat_turn"] is not None
        # Yeni next_combat_turn: 10 + (6-14) arası
        assert 16 <= effects["next_combat_turn"] <= 24

    def test_no_combat_trigger_too_early(self):
        """turn_count < next_combat_turn ise savaş başlamamalı."""
        prompt, effects = PromptBuilder.build_dynamic_prompt(
            **self._timing_params(turn_count=5, next_combat_turn=10))
        assert "DUSMAN CIKAR" not in prompt
        assert effects["enter_combat"] is False
        assert "Kesfe devam" in prompt

    def test_ongoing_combat(self):
        """Savaş devam ediyorsa (in_combat=True) uygun prompt."""
        prompt, effects = PromptBuilder.build_dynamic_prompt(
            **self._timing_params(
                current_mode="savas",
                is_in_combat=True,
                last_combat_turn=9,
                turn_count=10,
            ))
        assert "Boss savasi devam ediyor" in prompt
        assert effects["enter_combat"] is False

    def test_long_combat_ends(self):
        """3+ tur süren savaş sonlandırılmalı."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._timing_params(
                current_mode="savas",
                is_in_combat=True,
                last_combat_turn=7,
                turn_count=10,  # 10 - 7 = 3 tur
            ))
        assert "Savasi sonlandir" in prompt


# ================================================================
# build_dynamic_prompt — Savunma sınır değerleri
# ================================================================

class TestDynamicPromptBoundaryValues:
    """Sınır değer testleri — accuracy eşik noktaları."""

    def _boundary_params(self, accuracy, action="Saldir"):
        return dict(
            choice_text=action,
            current_theme="Test",
            theme_lore="Test",
            turn_count=5,
            current_story="",
            current_mode="savas",
            pending_combat_result={"accuracy": accuracy, "action": action},
            enemy_hp=50,
            enemy_max_hp=100,
            is_in_combat=True,
            last_combat_turn=4,
            next_combat_turn=20,
            pending_loot="",
            world_context="",
            character_summary="",
        )

    def test_accuracy_exactly_70_is_success(self):
        """accuracy=70 başarılı sayılmalı."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(**self._boundary_params(70))
        assert "BASARIYLA" in prompt

    def test_accuracy_69_is_partial(self):
        """accuracy=69 kısmi başarılı sayılmalı."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(**self._boundary_params(69))
        assert "KISMI BASARIYLA" in prompt

    def test_accuracy_40_is_partial(self):
        """accuracy=40 kısmi başarılı sayılmalı."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(**self._boundary_params(40))
        assert "KISMI BASARIYLA" in prompt

    def test_accuracy_39_is_fail(self):
        """accuracy=39 başarısız sayılmalı."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(**self._boundary_params(39))
        assert "BASARISIZ" in prompt

    def test_defense_exactly_70_blocks(self):
        """Savunma accuracy=70 tam engelleme."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._boundary_params(70, "Savun"))
        assert "Hasar tamamen engellendi" in prompt

    def test_defense_69_partial(self):
        """Savunma accuracy=69 kısmi."""
        prompt, _ = PromptBuilder.build_dynamic_prompt(
            **self._boundary_params(69, "Savun"))
        assert "KISMI BASARILI" in prompt
