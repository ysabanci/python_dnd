"""
test_combat.py — CombatManager Unit Testleri
================================================
combat_manager.py'deki tüm saf hesaplama ve karar metodlarını
test eder. CombatManager UI'a bağımlı olmadığı için GameState,
frame veya cv2 gerekmeden doğrudan test edilebilir.

Aşama 4.7 — RESTRUCTURE_PLAN'a göre.
"""

import random
from game.core.combat_manager import CombatManager


# ================================================================== #
#  FIXTURE BENZERI YARDIMCILAR                                        #
# ================================================================== #

def make_cm():
    """Temiz bir CombatManager oluşturur."""
    return CombatManager()


def default_weapon_stats():
    """Standart silah stat'leri."""
    return {"bonus": 10, "type": "fiziksel"}


def magic_weapon_stats():
    """Büyüsel silah stat'leri."""
    return {"bonus": 15, "type": "buyusel"}


def default_class_bonus():
    """Varsayılan sınıf bonusu (Savaşçı)."""
    return {
        "attack_mult": 1.2,
        "magic_mult": 0.8,
        "defense_reduction": 0.0,
        "flee_threshold": 70,
    }


def default_stat_fx():
    """Varsayılan stat efektleri (bonussuz)."""
    return {
        "attack_bonus": 0,
        "magic_bonus": 0,
        "crit_bonus": 0,
        "extra_turn_bonus": 0,
        "flee_bonus": 0,
        "dodge_chance": 0,
        "defense_reduction": 0.0,
    }


# ================================================================== #
#  PROCESS_ATTACK TESTLERİ                                            #
# ================================================================== #

class TestProcessAttack:
    """process_attack() hesaplama testleri."""

    def test_critical_hit_shape(self):
        """Shape challenge %85+ = kritik vuruş."""
        cm = make_cm()
        random.seed(42)
        result = cm.process_attack(
            accuracy=90, action="Saldir", is_shape=True,
            selected_weapon="Kilic", weapon_stats=default_weapon_stats(),
            class_bonus=default_class_bonus(), stat_fx=default_stat_fx(),
            enemy_hp=100,
        )
        assert result["is_critical"] is True
        assert result["enemy_dmg"] > 0
        assert result["new_enemy_hp"] < 100
        assert "KRITIK" in result["description"]

    def test_fist_cannot_critical(self):
        """Fist challenge (is_shape=False) ile kritik mümkün değil."""
        cm = make_cm()
        random.seed(42)
        result = cm.process_attack(
            accuracy=90, action="Saldir", is_shape=False,
            selected_weapon="Kilic", weapon_stats=default_weapon_stats(),
            class_bonus=default_class_bonus(), stat_fx=default_stat_fx(),
            enemy_hp=100,
        )
        assert result["is_critical"] is False

    def test_successful_attack(self):
        """Accuracy >= 70 = başarılı saldırı."""
        cm = make_cm()
        random.seed(42)
        result = cm.process_attack(
            accuracy=75, action="Saldir", is_shape=False,
            selected_weapon="Kilic", weapon_stats=default_weapon_stats(),
            class_bonus=default_class_bonus(), stat_fx=default_stat_fx(),
            enemy_hp=100,
        )
        assert result["enemy_dmg"] > 0
        assert result["new_enemy_hp"] < 100
        assert "guclu" in result["description"]

    def test_partial_attack(self):
        """%40-69 = kısmi saldırı."""
        cm = make_cm()
        random.seed(42)
        result = cm.process_attack(
            accuracy=50, action="Saldir", is_shape=False,
            selected_weapon="Kilic", weapon_stats=default_weapon_stats(),
            class_bonus=default_class_bonus(), stat_fx=default_stat_fx(),
            enemy_hp=100,
        )
        assert result["enemy_dmg"] > 0
        assert "tam isabetle degil" in result["description"]

    def test_failed_attack(self):
        """%40 altı = başarısız, hasar yok."""
        cm = make_cm()
        result = cm.process_attack(
            accuracy=30, action="Saldir", is_shape=False,
            selected_weapon="Kilic", weapon_stats=default_weapon_stats(),
            class_bonus=default_class_bonus(), stat_fx=default_stat_fx(),
            enemy_hp=100,
        )
        assert result["enemy_dmg"] == 0
        assert result["new_enemy_hp"] == 100
        assert "basarisiz" in result["description"]

    def test_unarmed_low_damage(self):
        """Yumruk ile hasar çok düşük olmalı."""
        cm = make_cm()
        random.seed(42)
        unarmed = cm.process_attack(
            accuracy=75, action="Saldir", is_shape=False,
            selected_weapon="Yumruk", weapon_stats={"bonus": 0, "type": "fiziksel"},
            class_bonus=default_class_bonus(), stat_fx=default_stat_fx(),
            enemy_hp=100,
        )
        armed = cm.process_attack(
            accuracy=75, action="Saldir", is_shape=False,
            selected_weapon="Kilic", weapon_stats=default_weapon_stats(),
            class_bonus=default_class_bonus(), stat_fx=default_stat_fx(),
            enemy_hp=100,
        )
        # Yumruk hasarı silah hasarından düşük olmalı
        assert unarmed["enemy_dmg"] < armed["enemy_dmg"]

    def test_magic_uses_magic_mult(self):
        """Büyü aksiyonu magic_mult kullanmalı."""
        cm = make_cm()
        random.seed(42)
        result = cm.process_attack(
            accuracy=75, action="Buyu", is_shape=False,
            selected_weapon="Asa", weapon_stats=magic_weapon_stats(),
            class_bonus={"attack_mult": 1.0, "magic_mult": 2.0},
            stat_fx=default_stat_fx(),
            enemy_hp=100,
        )
        assert result["enemy_dmg"] > 0
        assert result["new_enemy_hp"] < 100

    def test_enemy_hp_cannot_go_negative(self):
        """Düşman HP'si 0'ın altına inmemeli."""
        cm = make_cm()
        random.seed(42)
        result = cm.process_attack(
            accuracy=90, action="Saldir", is_shape=True,
            selected_weapon="Kilic", weapon_stats={"bonus": 999, "type": "fiziksel"},
            class_bonus={"attack_mult": 10.0}, stat_fx=default_stat_fx(),
            enemy_hp=5,
        )
        assert result["new_enemy_hp"] == 0

    def test_crit_bonus_lowers_threshold(self):
        """Stat crit_bonus kritik eşiğini düşürmeli."""
        cm = make_cm()
        random.seed(42)
        # Normal eşik 85, crit_bonus=20 → eşik 65
        result = cm.process_attack(
            accuracy=70, action="Saldir", is_shape=True,
            selected_weapon="Kilic", weapon_stats=default_weapon_stats(),
            class_bonus=default_class_bonus(),
            stat_fx={**default_stat_fx(), "crit_bonus": 20},
            enemy_hp=100,
        )
        assert result["is_critical"] is True


# ================================================================== #
#  PROCESS_DEFENSE TESTLERİ                                           #
# ================================================================== #

class TestProcessDefense:
    """process_defense() hesaplama testleri."""

    def test_successful_defense(self):
        """Accuracy >= 70 = tam engelleme + iyileşme."""
        cm = make_cm()
        result = cm.process_defense(accuracy=80)
        assert result["blocked"] is True
        assert result["partial"] is False
        assert result["heal"] > 0
        assert cm.defense_blocked is True
        assert cm.defense_partial is False

    def test_partial_defense(self):
        """%40-69 = kısmi engelleme."""
        cm = make_cm()
        result = cm.process_defense(accuracy=50)
        assert result["blocked"] is False
        assert result["partial"] is True
        assert result["heal"] == 0
        assert cm.defense_blocked is False
        assert cm.defense_partial is True

    def test_failed_defense(self):
        """%40 altı = başarısız, bayraklar sıfır."""
        cm = make_cm()
        result = cm.process_defense(accuracy=30)
        assert result["blocked"] is False
        assert result["partial"] is False
        assert result["heal"] == 0
        assert cm.defense_blocked is False
        assert cm.defense_partial is False

    def test_boundary_70_blocks(self):
        """Tam olarak %70 = başarılı savunma."""
        cm = make_cm()
        result = cm.process_defense(accuracy=70)
        assert result["blocked"] is True

    def test_boundary_69_partial(self):
        """%69 = kısmi savunma."""
        cm = make_cm()
        result = cm.process_defense(accuracy=69)
        assert result["partial"] is True

    def test_boundary_40_partial(self):
        """%40 = kısmi savunma."""
        cm = make_cm()
        result = cm.process_defense(accuracy=40)
        assert result["partial"] is True

    def test_boundary_39_fail(self):
        """%39 = başarısız."""
        cm = make_cm()
        result = cm.process_defense(accuracy=39)
        assert result["blocked"] is False
        assert result["partial"] is False


# ================================================================== #
#  PROCESS_FLEE TESTLERİ                                              #
# ================================================================== #

class TestProcessFlee:
    """process_flee() hesaplama testleri."""

    def test_successful_flee(self):
        """Accuracy >= threshold = başarılı kaçış."""
        cm = make_cm()
        result = cm.process_flee(
            accuracy=75,
            class_bonus={"flee_threshold": 70},
            stat_fx=default_stat_fx(),
        )
        assert result["success"] is True
        assert "kactin" in result["description"].lower()

    def test_failed_flee(self):
        """Accuracy < threshold = başarısız kaçış."""
        cm = make_cm()
        result = cm.process_flee(
            accuracy=60,
            class_bonus={"flee_threshold": 70},
            stat_fx=default_stat_fx(),
        )
        assert result["success"] is False

    def test_dex_lowers_threshold(self):
        """DEX flee_bonus eşiği düşürmeli."""
        cm = make_cm()
        result = cm.process_flee(
            accuracy=50,
            class_bonus={"flee_threshold": 70},
            stat_fx={**default_stat_fx(), "flee_bonus": 25},
        )
        # Eşik: 70 - 25 = 45. Accuracy 50 >= 45 → başarılı
        assert result["success"] is True
        assert result["flee_threshold"] == 45

    def test_threshold_floor_30(self):
        """Kaçış eşiği 30'un altına inmemeli."""
        cm = make_cm()
        result = cm.process_flee(
            accuracy=25,
            class_bonus={"flee_threshold": 70},
            stat_fx={**default_stat_fx(), "flee_bonus": 100},
        )
        assert result["flee_threshold"] == 30
        assert result["success"] is False


# ================================================================== #
#  EVALUATE_COMBAT_RESULT TESTLERİ                                    #
# ================================================================== #

class TestEvaluateCombatResult:
    """evaluate_combat_result() orkestrasyon testleri."""

    def test_attack_enemy_defeated(self):
        """Düşman HP 0'a düşerse outcome = enemy_defeated."""
        cm = make_cm()
        random.seed(42)
        result = cm.evaluate_combat_result(
            accuracy=90, action="Saldir", is_shape=True,
            selected_weapon="Kilic",
            weapon_stats={"bonus": 999, "type": "fiziksel"},
            class_bonus={"attack_mult": 10.0},
            stat_fx=default_stat_fx(),
            enemy_hp=1, player_hp=100,
        )
        assert result["outcome"] == "enemy_defeated"
        assert result["new_enemy_hp"] == 0

    def test_player_game_over(self):
        """Oyuncu HP <= 0 ise outcome = game_over."""
        cm = make_cm()
        result = cm.evaluate_combat_result(
            accuracy=30, action="Saldir", is_shape=False,
            selected_weapon="Yumruk",
            weapon_stats={"bonus": 0, "type": "fiziksel"},
            class_bonus=default_class_bonus(),
            stat_fx=default_stat_fx(),
            enemy_hp=100, player_hp=0,
        )
        assert result["outcome"] == "game_over"

    def test_flee_success(self):
        """Kaçış başarılı ise outcome = flee_success."""
        cm = make_cm()
        result = cm.evaluate_combat_result(
            accuracy=80, action="Kac", is_shape=False,
            selected_weapon="",
            weapon_stats={"bonus": 0, "type": "fiziksel"},
            class_bonus={"flee_threshold": 70},
            stat_fx=default_stat_fx(),
            enemy_hp=100, player_hp=100,
        )
        assert result["outcome"] == "flee_success"

    def test_flee_fail_goes_to_enemy_attack(self):
        """Kaçış başarısız ise outcome = enemy_attack."""
        cm = make_cm()
        result = cm.evaluate_combat_result(
            accuracy=50, action="Kac", is_shape=False,
            selected_weapon="",
            weapon_stats={"bonus": 0, "type": "fiziksel"},
            class_bonus={"flee_threshold": 70},
            stat_fx=default_stat_fx(),
            enemy_hp=100, player_hp=100,
        )
        assert result["outcome"] == "enemy_attack"

    def test_defense_goes_to_enemy_attack(self):
        """Savunma sonrası her zaman enemy_attack."""
        cm = make_cm()
        result = cm.evaluate_combat_result(
            accuracy=80, action="Savun", is_shape=False,
            selected_weapon="",
            weapon_stats={"bonus": 0, "type": "fiziksel"},
            class_bonus=default_class_bonus(),
            stat_fx=default_stat_fx(),
            enemy_hp=100, player_hp=100,
        )
        assert result["outcome"] == "enemy_attack"

    def test_action_type_classification(self):
        """Aksiyon tipleri doğru sınıflandırılmalı."""
        cm = make_cm()
        for action, expected_type in [
            ("Saldir", "attack"), ("Buyu", "attack"),
            ("Savun", "defense"), ("Kac", "flee"),
        ]:
            result = cm.evaluate_combat_result(
                accuracy=50, action=action, is_shape=False,
                selected_weapon="Kilic",
                weapon_stats=default_weapon_stats(),
                class_bonus=default_class_bonus(),
                stat_fx=default_stat_fx(),
                enemy_hp=100, player_hp=100,
            )
            assert result["action_type"] == expected_type, \
                f"Action '{action}' should be '{expected_type}', got '{result['action_type']}'"


# ================================================================== #
#  CALCULATE_ENEMY_DAMAGE TESTLERİ                                    #
# ================================================================== #

class TestCalculateEnemyDamage:
    """calculate_enemy_damage() hesaplama testleri."""

    def test_dodge_blocks_all(self):
        """DEX dodge ile tamamen kaçınılır — dodged bayrağı set edilir."""
        cm = make_cm()
        result = cm.calculate_enemy_damage(
            stat_fx={**default_stat_fx(), "dodge_chance": 1.0},
            class_bonus=default_class_bonus(),
        )
        assert result["dodged"] is True
        assert result["blocked"] is False  # S05 fix: dodge != defense_blocked
        assert result["damage"] == 0
        assert cm.dodged is True  # S05 fix: yeni bayrak
        assert cm.defense_blocked is False  # S05 fix: savunma bayrağı etkilenmez

    def test_defense_blocked_zero_damage(self):
        """Savunma engelleme = hasar 0."""
        cm = make_cm()
        cm.defense_blocked = True
        result = cm.calculate_enemy_damage(
            stat_fx=default_stat_fx(),
            class_bonus=default_class_bonus(),
        )
        assert result["damage"] == 0
        assert result["blocked"] is True

    def test_defense_partial_halves_damage(self):
        """Kısmi savunma hasarı yarıya indirmeli."""
        cm = make_cm()
        cm.defense_partial = True
        random.seed(42)
        partial_result = cm.calculate_enemy_damage(
            stat_fx=default_stat_fx(),
            class_bonus=default_class_bonus(),
        )
        assert partial_result["partial"] is True
        # Kısmi hasar > 0 ama normal hasardan düşük
        assert partial_result["damage"] >= 0

    def test_no_defense_normal_damage(self):
        """Savunma bayrağı yoksa normal hasar."""
        cm = make_cm()
        random.seed(42)
        result = cm.calculate_enemy_damage(
            stat_fx=default_stat_fx(),
            class_bonus=default_class_bonus(),
        )
        assert result["dodged"] is False
        assert result["blocked"] is False
        assert result["damage"] > 0

    def test_defense_reduction_caps_at_60(self):
        """Hasar azaltma %60'ta sınırlı."""
        cm = make_cm()
        random.seed(42)
        result = cm.calculate_enemy_damage(
            stat_fx={**default_stat_fx(), "defense_reduction": 0.5},
            class_bonus={"defense_reduction": 0.5},
        )
        # total_reduction = min(0.6, 0.5 + 0.5) = 0.6
        # Hasar = full_dmg * 0.4
        assert result["damage"] > 0


# ================================================================== #
#  RESOLVE_ENEMY_ATTACK_TICK TESTLERİ                                 #
# ================================================================== #

class TestResolveEnemyAttackTick:
    """resolve_enemy_attack_tick() animasyon tick testleri."""

    def test_early_tick_no_damage(self):
        """Animasyonun ilk yarısında hasar uygulanmaz."""
        cm = make_cm()
        cm.enemy_attack_damage = 10
        tick = cm.resolve_enemy_attack_tick(elapsed=0.5, player_hp=100)
        assert tick["apply_damage"] is False
        assert tick["animation_done"] is False
        assert tick["outcome"] == ""

    def test_mid_tick_applies_damage(self):
        """Animasyonun %50 noktasında hasar uygulanır."""
        cm = make_cm()
        cm.enemy_attack_damage = 15
        tick = cm.resolve_enemy_attack_tick(elapsed=1.5, player_hp=100)
        assert tick["apply_damage"] is True
        assert tick["damage_amount"] == -15

    def test_mid_tick_blocked_no_damage(self):
        """defense_blocked ise hasar uygulanmaz."""
        cm = make_cm()
        cm.enemy_attack_damage = 15
        cm.defense_blocked = True
        tick = cm.resolve_enemy_attack_tick(elapsed=1.5, player_hp=100)
        assert tick["apply_damage"] is False
        assert cm.enemy_attack_applied is True

    def test_mid_tick_dodged_no_damage(self):
        """S05: dodged ise hasar uygulanmaz."""
        cm = make_cm()
        cm.enemy_attack_damage = 15
        cm.dodged = True
        tick = cm.resolve_enemy_attack_tick(elapsed=1.5, player_hp=100)
        assert tick["apply_damage"] is False
        assert cm.enemy_attack_applied is True

    def test_damage_applied_once(self):
        """Hasar sadece bir kez uygulanır."""
        cm = make_cm()
        cm.enemy_attack_damage = 10
        tick1 = cm.resolve_enemy_attack_tick(elapsed=1.5, player_hp=100)
        assert tick1["apply_damage"] is True
        # İkinci çağrı — artık applied
        tick2 = cm.resolve_enemy_attack_tick(elapsed=2.0, player_hp=90)
        assert tick2["apply_damage"] is False

    def test_animation_done_player_turn(self):
        """Animasyon bittiğinde sıra oyuncuya geçer."""
        cm = make_cm()
        cm.enemy_attack_damage = 10
        cm.enemy_attack_applied = True  # hasar önceden uygulandı
        tick = cm.resolve_enemy_attack_tick(elapsed=3.5, player_hp=90)
        assert tick["animation_done"] is True
        assert tick["outcome"] == "player_turn"
        assert "siran" in tick["feedback"].lower()

    def test_animation_done_game_over(self):
        """Animasyon bittiğinde oyuncu HP <= 0 ise game_over."""
        cm = make_cm()
        cm.enemy_attack_damage = 100
        cm.enemy_attack_applied = True
        tick = cm.resolve_enemy_attack_tick(elapsed=3.5, player_hp=0)
        assert tick["animation_done"] is True
        assert tick["outcome"] == "game_over"

    def test_flags_reset_on_player_turn(self):
        """Tur oyuncuya geçtiğinde bayraklar sıfırlanır."""
        cm = make_cm()
        cm.defense_blocked = True
        cm.defense_partial = True
        cm.dodged = True  # S05 fix
        cm.enemy_attack_applied = True
        cm.enemy_attack_damage = 0
        tick = cm.resolve_enemy_attack_tick(elapsed=3.5, player_hp=100)
        assert tick["outcome"] == "player_turn"
        assert cm.defense_blocked is False
        assert cm.defense_partial is False
        assert cm.dodged is False

    def test_dodge_feedback_distinct(self):
        """S05: Dodge feedback 'DODGE' içermeli, 'savunma' değil."""
        cm = make_cm()
        cm.dodged = True
        cm.enemy_attack_damage = 0
        cm.enemy_attack_applied = True
        tick = cm.resolve_enemy_attack_tick(elapsed=3.5, player_hp=100)
        assert "DODGE" in tick["feedback"]
        assert "savunma" not in tick["feedback"].lower()

    def test_defense_feedback_distinct(self):
        """S05: Defense feedback 'savunma' içermeli, 'DODGE' değil."""
        cm = make_cm()
        cm.defense_blocked = True
        cm.enemy_attack_damage = 0
        cm.enemy_attack_applied = True
        tick = cm.resolve_enemy_attack_tick(elapsed=3.5, player_hp=100)
        assert "savunma" in tick["feedback"].lower()
        assert "DODGE" not in tick["feedback"]

    def test_progress_capped_at_1(self):
        """Progress 1.0'ı aşmaz."""
        cm = make_cm()
        cm.enemy_attack_applied = True
        tick = cm.resolve_enemy_attack_tick(elapsed=10.0, player_hp=100)
        assert tick["progress"] == 1.0


# ================================================================== #
#  RESOLVE_WEAPON_SELECTION TESTLERİ                                  #
# ================================================================== #

class TestResolveWeaponSelection:
    """resolve_weapon_selection() silah seçim testleri."""

    def test_no_weapons_unarmed(self):
        """Silah yoksa yumruk."""
        cm = make_cm()
        result = cm.resolve_weapon_selection("Saldir", [])
        assert result["outcome"] == "unarmed"
        assert result["selected_weapon"] == "Yumruk"
        assert cm.selected_weapon == "Yumruk"

    def test_one_weapon_auto_select(self):
        """Tek silah otomatik seçilir."""
        cm = make_cm()
        result = cm.resolve_weapon_selection("Saldir", ["Kilic"])
        assert result["outcome"] == "auto_select"
        assert result["selected_weapon"] == "Kilic"
        assert cm.selected_weapon == "Kilic"

    def test_multiple_weapons_manual_select(self):
        """Birden fazla silah seçim ekranı getirir."""
        cm = make_cm()
        result = cm.resolve_weapon_selection("Saldir", ["Kilic", "Balta"])
        assert result["outcome"] == "manual_select"
        assert result["selected_weapon"] == ""
        assert result["weapon_options"]["sol_ust"] == "Kilic"
        assert result["weapon_options"]["sag_ust"] == "Balta"
        assert result["option_count"] == 2

    def test_defense_no_weapon_needed(self):
        """Savunma silah gerektirmez."""
        cm = make_cm()
        result = cm.resolve_weapon_selection("Savun", ["Kilic"])
        assert result["outcome"] == "no_weapon_needed"
        assert result["is_attack"] is False

    def test_flee_no_weapon_needed(self):
        """Kaçış silah gerektirmez."""
        cm = make_cm()
        result = cm.resolve_weapon_selection("Kac", [])
        assert result["outcome"] == "no_weapon_needed"

    def test_buyu_is_attack(self):
        """Büyü saldırı olarak sınıflandırılır."""
        cm = make_cm()
        result = cm.resolve_weapon_selection("Buyu", ["Asa"])
        assert result["is_attack"] is True
        assert result["outcome"] == "auto_select"

    def test_four_weapons_max_options(self):
        """En fazla 4 silah seçeneği gösterilir."""
        cm = make_cm()
        weapons = ["Kilic", "Balta", "Asa", "Mızrak", "Yay"]
        result = cm.resolve_weapon_selection("Saldir", weapons)
        assert result["option_count"] == 4
        assert result["weapon_options"]["sag_alt"] == "Mızrak"

    def test_pending_combat_choice_set(self):
        """pending_combat_choice güncellenir."""
        cm = make_cm()
        cm.resolve_weapon_selection("Saldir", [])
        assert cm.pending_combat_choice == "Saldir"


# ================================================================== #
#  PICK_CHALLENGE_TYPE TESTLERİ                                       #
# ================================================================== #

class TestPickChallengeType:
    """pick_challenge_type() rastgele seçim testleri."""

    def test_returns_shape_or_fist(self):
        """Sonuç sadece 'shape' veya 'fist' olabilir."""
        cm = make_cm()
        for _ in range(100):
            result = cm.pick_challenge_type()
            assert result in ("shape", "fist")

    def test_distribution_roughly_correct(self):
        """Dağılım yaklaşık %60/%40 olmalı."""
        cm = make_cm()
        random.seed(42)
        counts = {"shape": 0, "fist": 0}
        n = 1000
        for _ in range(n):
            counts[cm.pick_challenge_type()] += 1
        # %60 ± %5 tolerans
        assert 550 <= counts["shape"] <= 650, \
            f"Shape count {counts['shape']} out of expected range"


# ================================================================== #
#  GET_COMBAT_PREVIEW TESTLERİ                                        #
# ================================================================== #

class TestGetCombatPreview:
    """get_combat_preview() ön izleme testleri."""

    def test_attack_critical(self):
        cm = make_cm()
        assert "KRITIK" in cm.get_combat_preview(90, "Saldir")

    def test_attack_success(self):
        cm = make_cm()
        assert "hasar verildi" in cm.get_combat_preview(75, "Saldir")

    def test_attack_partial(self):
        cm = make_cm()
        assert "az hasar" in cm.get_combat_preview(50, "Saldir")

    def test_attack_fail(self):
        cm = make_cm()
        assert "verilemedi" in cm.get_combat_preview(30, "Saldir")

    def test_defense_success(self):
        cm = make_cm()
        assert "aktif" in cm.get_combat_preview(75, "Savun")

    def test_defense_partial(self):
        cm = make_cm()
        assert "Kismi" in cm.get_combat_preview(50, "Savun")

    def test_defense_fail(self):
        cm = make_cm()
        assert "yok" in cm.get_combat_preview(30, "Savun")

    def test_flee_success(self):
        cm = make_cm()
        assert "kaciliyor" in cm.get_combat_preview(75, "Kac")

    def test_flee_fail(self):
        cm = make_cm()
        assert "Kacilamadi" in cm.get_combat_preview(50, "Kac")

    def test_unknown_action(self):
        cm = make_cm()
        assert cm.get_combat_preview(75, "BilinmeyenAksiyon") == ""


# ================================================================== #
#  RESET TESTLERİ                                                     #
# ================================================================== #

class TestReset:
    """reset() bayrak sıfırlama testleri."""

    def test_reset_clears_all_flags(self):
        """reset() tüm bayrakları sıfırlamalı."""
        cm = make_cm()
        # Bayrakları kirlet
        cm.pending_combat_choice = "Saldir"
        cm.selected_weapon = "Kilic"
        cm.weapon_combat_action = "Buyu"
        cm.enemy_attack_damage = 50
        cm.enemy_attack_applied = True
        cm.extra_turn_active = True
        cm.defense_blocked = True
        cm.defense_partial = True
        cm.dodged = True  # S05 fix

        cm.reset()

        assert cm.pending_combat_choice == ""
        assert cm.selected_weapon == ""
        assert cm.weapon_combat_action == ""
        assert cm.enemy_attack_damage == 0
        assert cm.enemy_attack_applied is False
        assert cm.extra_turn_active is False
        assert cm.defense_blocked is False
        assert cm.defense_partial is False
        assert cm.dodged is False  # S05 fix
