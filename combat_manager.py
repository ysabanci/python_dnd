"""
combat_manager.py — Savaş Mantığı Yöneticisi
================================================
Savaş mekaniklerinin hesaplama mantığını içerir.
CombatManager UI'a DOKUNMAZ — frame/çizim referansı YOK.
Savaş mantığı sadece HESAPLAMA yapar ve STATE günceller.

Kaynak: Bu fonksiyonlar orijinal olarak main.py'deki DnDGame
sınıfının metodlarıydı. Sürdürülebilirlik ve test edilebilirlik
için ayrı dosyaya taşındı.

NOT: Taşıma aşamalı yapılmaktadır. Şu an taşınan:
- Adım 4.1: Boş sınıf yapısı + savaş sabitleri
- Adım 4.2: Savaş bayrakları (state)
- Adım 4.3: _process_attack, _process_defense, _process_flee
- Adım 4.4: evaluate_combat_result (orkestrasyon karar mantığı)
- Adım 4.5: calculate_enemy_damage, resolve_enemy_attack_tick
- Adım 4.6: resolve_weapon_selection, pick_challenge_type
"""

import random
from typing import Any, Dict, Optional


class CombatManager:
    """
    Savaş mantığı yöneticisi.

    DnDGame'deki savaş bayraklarını ve hesaplama metodlarını barındırır.
    UI'a bağımlılık YOK — frame, draw, cv2 referansı YOK.

    Kullanım:
        game.combat = CombatManager()
        # main.py'den erişim: self.combat.selected_weapon, self.combat.defense_blocked vs.
    """

    # ----- Savaş Sabitleri ----- #
    CRITICAL_HIT_THRESHOLD = 85
    EXTRA_TURN_CHANCE = 0.30

    # Aksiyon tanımlama tuple'ları
    ACTION_ATTACK = ("saldir", "saldiri", "buyu")
    ACTION_DEFENSE = ("savun", "savunma")
    ACTION_FLEE = ("kac", "kacis")
    ACTION_MAGIC = "buyu"

    def __init__(self) -> None:
        """Savaş bayraklarını başlangıç değerlerine ayarlar."""
        self.reset()

    def reset(self) -> None:
        """Tüm savaş bayraklarını sıfırlar. Yeni savaş başlangıcında çağrılır."""
        # ----- Bekleyen savaş seçimi -----
        self.pending_combat_choice: str = ""

        # ----- Silah Seçim Fazı -----
        self.weapon_select_options: list = []
        self.selected_weapon: str = ""
        self.weapon_combat_action: str = ""

        # ----- Düşman Saldırı Fazı -----
        self.enemy_attack_start: float = 0.0
        self.enemy_attack_damage: int = 0
        self.enemy_attack_applied: bool = False

        # ----- Ekstra Tur (saldırı sonrası) -----
        self.extra_turn_active: bool = False

        # ----- Başarılı savunma bayrağı -----
        self.defense_blocked: bool = False
        self.defense_partial: bool = False

        # ----- DEX Dodge bayrağı (S05 fix) -----
        self.dodged: bool = False

    # ------------------------------------------------------------------ #
    #  SALDIRI İŞLEME                                                      #
    # ------------------------------------------------------------------ #

    def process_attack(
        self,
        accuracy: float,
        action: str,
        is_shape: bool,
        selected_weapon: str,
        weapon_stats: Dict[str, Any],
        class_bonus: Dict[str, Any],
        stat_fx: Dict[str, Any],
        enemy_hp: int,
    ) -> Dict[str, Any]:
        """
        Saldırı/Büyü sonucunu hesaplar.

        Args:
            accuracy: Challenge doğruluk yüzdesi (0-100).
            action: Oyuncu aksiyonu ("Saldir", "Buyu" vb).
            is_shape: Shape challenge mı (True) yoksa fist mi (False).
            selected_weapon: Seçili silah adı.
            weapon_stats: Silah istatistikleri dict'i (bonus, type).
            class_bonus: Sınıf bonusu dict'i (attack_mult, magic_mult).
            stat_fx: Stat efektleri dict'i (attack_bonus, magic_bonus, crit_bonus).
            enemy_hp: Düşmanın mevcut HP'si.

        Returns:
            dict: Sonuç bilgileri:
                - "enemy_dmg": int — düşmana verilen hasar
                - "new_enemy_hp": int — düşmanın yeni HP'si
                - "description": str — feedback metni
                - "is_critical": bool — kritik vuruş mu
        """
        weapon_bonus = weapon_stats.get("bonus", 0)
        weapon_type = weapon_stats.get("type", "fiziksel")
        is_unarmed = selected_weapon in ("Yumruk", "")

        action_lower = action.lower()
        if action_lower == self.ACTION_MAGIC or weapon_type == "buyusel":
            class_mult = class_bonus.get("magic_mult", 1.0)
            stat_bonus = stat_fx.get("magic_bonus", 0)
        else:
            class_mult = class_bonus.get("attack_mult", 1.0)
            stat_bonus = stat_fx.get("attack_bonus", 0)

        crit_threshold = self.CRITICAL_HIT_THRESHOLD - stat_fx.get("crit_bonus", 0)

        # Silahsız hasar çok düşük
        if is_unarmed:
            weapon_bonus = 0
            class_mult = 0.3

        # Betimlemeler
        weapon_name = selected_weapon if not is_unarmed else "yumruklari"

        is_critical = False
        enemy_dmg = 0

        if is_shape and accuracy >= crit_threshold:
            is_critical = True
            if is_unarmed:
                base_dmg = random.randint(5, 12) + stat_bonus
            else:
                base_dmg = random.randint(30, 50) + weapon_bonus + stat_bonus
            enemy_dmg = int(base_dmg * 1.5 * class_mult)
            desc = f"KRITIK VURUS! {weapon_name} ile muhtesem bir darbe! -{enemy_dmg} hasar!"
        elif accuracy >= 70:
            if is_unarmed:
                base_dmg = random.randint(3, 8) + stat_bonus
            else:
                base_dmg = random.randint(25, 40) + weapon_bonus + stat_bonus
            enemy_dmg = int(base_dmg * class_mult)
            desc = f"{weapon_name} ile guclu bir {action}! Dusmana -{enemy_dmg} hasar!"
        elif accuracy >= 40:
            if is_unarmed:
                base_dmg = random.randint(1, 4) + stat_bonus // 2
            else:
                base_dmg = random.randint(10, 20) + weapon_bonus // 2 + stat_bonus // 2
            enemy_dmg = int(base_dmg * class_mult)
            desc = f"{weapon_name} ile sikiyoruz ama tam isabetle degil. -{enemy_dmg} hasar."
        else:
            desc = f"{weapon_name} ile hamle basarisiz! Dusman saldirisi geliyor!"

        new_enemy_hp = max(0, enemy_hp - enemy_dmg)

        return {
            "enemy_dmg": enemy_dmg,
            "new_enemy_hp": new_enemy_hp,
            "description": desc,
            "is_critical": is_critical,
        }

    # ------------------------------------------------------------------ #
    #  SAVUNMA İŞLEME                                                      #
    # ------------------------------------------------------------------ #

    def process_defense(self, accuracy: float) -> Dict[str, Any]:
        """
        Savunma sonucunu hesaplar.

        Savunma ASLA doğrudan hasar vermez. Bunun yerine bir kalkan durumu
        belirler ve düşmanın bir sonraki saldırı hasarını etkiler:
          - Başarılı (>=70%): Hasar tamamen engellenir + HP yenilenir
          - Kısmi (>=40%): Hasar %50 azalır
          - Başarısız (<40%): Düşman tam hasar verir

        Args:
            accuracy: Challenge doğruluk yüzdesi (0-100).

        Returns:
            dict: Sonuç bilgileri:
                - "blocked": bool — tam engelleme
                - "partial": bool — kısmi engelleme
                - "heal": int — iyileşme miktarı (sadece başarılı)
                - "description": str — feedback metni
        """
        if accuracy >= 70:
            heal = random.randint(8, 20)
            desc = f"Mukemmel savunma! Kalkanini yukseltip tum hasari engelledin! +{heal} HP yenilendi!"
            self.defense_blocked = True
            self.defense_partial = False
            return {
                "blocked": True,
                "partial": False,
                "heal": heal,
                "description": desc,
            }
        elif accuracy >= 40:
            desc = "Savunma durusuna gectin ama tam koruyamadin. Hasar azalacak."
            self.defense_blocked = False
            self.defense_partial = True
            return {
                "blocked": False,
                "partial": True,
                "heal": 0,
                "description": desc,
            }
        else:
            desc = "Savunma basarisiz! Dusman tam gucuyle saldiriyor!"
            self.defense_blocked = False
            self.defense_partial = False
            return {
                "blocked": False,
                "partial": False,
                "heal": 0,
                "description": desc,
            }

    # ------------------------------------------------------------------ #
    #  KAÇIŞ İŞLEME                                                        #
    # ------------------------------------------------------------------ #

    def process_flee(
        self,
        accuracy: float,
        class_bonus: Dict[str, Any],
        stat_fx: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Kaçış sonucunu hesaplar. DEX stat'i kaçış başarı eşiğini düşürür.

        Args:
            accuracy: Challenge doğruluk yüzdesi (0-100).
            class_bonus: Sınıf bonusu dict'i (flee_threshold).
            stat_fx: Stat efektleri dict'i (flee_bonus).

        Returns:
            dict: Sonuç bilgileri:
                - "success": bool — kaçış başarılı mı
                - "description": str — feedback metni
                - "flee_threshold": float — kullanılan eşik değeri
        """
        flee_threshold = class_bonus.get("flee_threshold", 70)
        # DEX bazlı kaçış bonusu (eşiği düşürür)
        flee_threshold = max(30, flee_threshold - stat_fx.get("flee_bonus", 0))

        if accuracy >= flee_threshold:
            return {
                "success": True,
                "description": "Basariyla kactin!",
                "flee_threshold": flee_threshold,
            }
        else:
            return {
                "success": False,
                "description": "Kacilamadi! Dusman saldirisi geliyor!",
                "flee_threshold": flee_threshold,
            }

    # ------------------------------------------------------------------ #
    #  SAVAŞ ÖN İZLEME                                                     #
    # ------------------------------------------------------------------ #

    def get_combat_preview(self, accuracy: float, action: str) -> str:
        """
        Challenge sonucuna göre hasar ön izleme metni oluşturur.

        Args:
            accuracy: Challenge doğruluk yüzdesi.
            action: Oyuncu aksiyonu.

        Returns:
            Ön izleme açıklama metni.
        """
        action_lower = action.lower()
        is_attack = action_lower in self.ACTION_ATTACK
        is_defense = action_lower in self.ACTION_DEFENSE
        is_flee = action_lower in self.ACTION_FLEE

        if is_attack:
            if accuracy >= 85:
                return "KRITIK! Dusmana buyuk hasar!"
            elif accuracy >= 70:
                return "Dusmana hasar verildi!"
            elif accuracy >= 40:
                return "Dusmana az hasar verildi."
            else:
                return "Dusmana hasar verilemedi!"
        elif is_defense:
            if accuracy >= 70:
                return "Kalkan aktif! Hasar engellendi!"
            elif accuracy >= 40:
                return "Kismi kalkan! Hasar azalacak."
            else:
                return "Kalkan yok! Tam hasar gelecek."
        elif is_flee:
            if accuracy >= 70:
                return "Basariyla kaciliyor!"
            else:
                return "Kacilamadi! Hasar gelecek."
        return ""

    # ------------------------------------------------------------------ #
    #  SAVAŞ SONUCU DEĞERLENDİRME (ORKESTRASYON)                          #
    # ------------------------------------------------------------------ #

    def evaluate_combat_result(
        self,
        accuracy: float,
        action: str,
        is_shape: bool,
        selected_weapon: str,
        weapon_stats: Dict[str, Any],
        class_bonus: Dict[str, Any],
        stat_fx: Dict[str, Any],
        enemy_hp: int,
        player_hp: int,
    ) -> Dict[str, Any]:
        """
        Oyuncunun challenge sonucunu değerlendirir ve ne yapılması
        gerektiğine karar verir.

        Bu metod bir ORKESTRATÖR'dür:
        1. Aksiyonu sınıflandırır (saldırı/savunma/kaçış)
        2. İlgili process_* metodunu çağırır
        3. Sonraki adıma karar verir (game over / düşman yenilgisi /
           kaçış / ekstra tur / düşman saldırısı)

        SIDE-EFFECT: self.defense_blocked, self.defense_partial ve
        self.extra_turn_active bayrakları güncellenir.

        Args:
            accuracy: Challenge doğruluk yüzdesi (0-100).
            action: Oyuncu aksiyonu ("Saldir", "Savun", "Kac", "Buyu").
            is_shape: Shape challenge mı (True) yoksa fist mi (False).
            selected_weapon: Seçili silah adı.
            weapon_stats: Silah istatistikleri dict'i.
            class_bonus: Sınıf bonusu dict'i.
            stat_fx: Stat efektleri dict'i.
            enemy_hp: Düşmanın mevcut HP'si.
            player_hp: Oyuncunun mevcut HP'si.

        Returns:
            dict: Karar bilgileri:
                - "action_type": str — "attack" / "defense" / "flee" / "unknown"
                - "action_result": dict — process_* sonucu
                - "outcome": str — karar:
                    "game_over" — oyuncu öldü
                    "enemy_defeated" — düşman yenildi
                    "flee_success" — kaçış başarılı
                    "extra_turn" — ekstra tur kazanıldı
                    "enemy_attack" — normal akış, düşman saldıracak
                - "new_enemy_hp": int — güncel düşman HP'si
                - "feedback_append": str — ek feedback metni (ekstra tur için)
        """
        action_lower = action.lower()
        is_attack = action_lower in self.ACTION_ATTACK
        is_defense = action_lower in self.ACTION_DEFENSE
        is_flee = action_lower in self.ACTION_FLEE

        grant_extra_turn = False
        action_result = {}
        action_type = "unknown"
        current_enemy_hp = enemy_hp

        # 1. Aksiyona göre hesaplama
        if is_attack:
            action_type = "attack"
            action_result = self.process_attack(
                accuracy=accuracy,
                action=action,
                is_shape=is_shape,
                selected_weapon=selected_weapon,
                weapon_stats=weapon_stats,
                class_bonus=class_bonus,
                stat_fx=stat_fx,
                enemy_hp=enemy_hp,
            )
            current_enemy_hp = action_result["new_enemy_hp"]

            # Başarılı saldırı → ekstra tur şansı (LUCK arttırır)
            extra_chance = self.EXTRA_TURN_CHANCE + stat_fx.get("extra_turn_bonus", 0)
            if accuracy >= 70 and random.random() < extra_chance:
                grant_extra_turn = True

        elif is_defense:
            action_type = "defense"
            action_result = self.process_defense(accuracy)
            # defense_blocked ve defense_partial bayrakları process_defense
            # tarafından zaten güncelleniyor

        elif is_flee:
            action_type = "flee"
            action_result = self.process_flee(
                accuracy=accuracy,
                class_bonus=class_bonus,
                stat_fx=stat_fx,
            )

        # 2. Sonraki adıma karar ver
        feedback_append = ""

        # 2a. Oyuncu öldü mü? (HP değişikliği wrapper'da uygulanacak)
        if player_hp <= 0:
            outcome = "game_over"

        # 2b. Düşman yenildi mi?
        elif is_attack and current_enemy_hp <= 0:
            outcome = "enemy_defeated"

        # 2c. Kaçış başarılı mı?
        elif is_flee and action_result.get("success", False):
            outcome = "flee_success"

        # 2d. Ekstra tur kazanıldı mı?
        elif grant_extra_turn:
            outcome = "extra_turn"
            self.extra_turn_active = True
            feedback_append = " | EKSTRA TUR!"

        # 2e. Normal akış: düşman saldırı fazına geç
        else:
            outcome = "enemy_attack"

        return {
            "action_type": action_type,
            "action_result": action_result,
            "outcome": outcome,
            "new_enemy_hp": current_enemy_hp,
            "feedback_append": feedback_append,
        }

    # ------------------------------------------------------------------ #
    #  DÜŞMAN SALDIRI HESAPLAMASI                                            #
    # ------------------------------------------------------------------ #

    # Düşman saldiri süresi (saniye) — animasyon için
    ENEMY_ATTACK_DURATION = 3.0

    def calculate_enemy_damage(
        self,
        stat_fx: Dict[str, Any],
        class_bonus: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Düşman saldırı hasarını hesaplar. DEX dodge şansı, savunma bayrakları
        ve DEF stat indirimini dikkate alır.

        SIDE-EFFECT: enemy_attack_damage, enemy_attack_applied, defense_blocked
        bayrakları güncellenir.

        Args:
            stat_fx: Stat efektleri dict'i (dodge_chance, defense_reduction).
            class_bonus: Sınıf bonusu dict'i (defense_reduction).

        Returns:
            dict: Hesaplama sonucu:
                - "damage": int — uygulanacak hasar
                - "dodged": bool — dodge ile tamamen kaçınıldı mı
                - "blocked": bool — savunmayla tamamen engellendi mi
                - "partial": bool — kısmi savunma mı
        """
        # DEX bazlı dodge (tamamen kaçınma)
        dodge_chance = stat_fx.get("dodge_chance", 0)
        if dodge_chance > 0 and random.random() < dodge_chance:
            self.enemy_attack_damage = 0
            self.dodged = True  # S05 fix: defense_blocked yerine dodged
            self.enemy_attack_applied = False
            return {
                "damage": 0,
                "dodged": True,
                "blocked": False,
                "partial": False,
            }

        # Sınıf savunma bonusu
        defense_reduction = class_bonus.get("defense_reduction", 0.0)
        stat_defense = stat_fx.get("defense_reduction", 0.0)
        total_reduction = min(0.6, defense_reduction + stat_defense)

        if self.defense_blocked:
            self.enemy_attack_damage = 0
        elif self.defense_partial:
            full_dmg = random.randint(8, 22)
            reduced = int(full_dmg * (1.0 - total_reduction))
            self.enemy_attack_damage = reduced // 2
        else:
            full_dmg = random.randint(8, 22)
            self.enemy_attack_damage = int(full_dmg * (1.0 - total_reduction))

        self.enemy_attack_applied = False

        return {
            "damage": self.enemy_attack_damage,
            "dodged": False,
            "blocked": self.defense_blocked,
            "partial": self.defense_partial,
        }

    def resolve_enemy_attack_tick(
        self,
        elapsed: float,
        player_hp: int,
    ) -> Dict[str, Any]:
        """
        Düşman saldırı animasyonu sırasında her tick'te çağrılır.
        Hasarın orta noktada uygulanması ve animasyon sonunda tur
        geçişi kararını verir.

        Args:
            elapsed: Animasyon başlangıcından geçen süre (saniye).
            player_hp: Oyuncunun MEVCUT HP'si.

        Returns:
            dict: Tick sonucu:
                - "progress": float — animasyon ilerleme oranı (0.0-1.0)
                - "apply_damage": bool — bu tick'te hasar uygulanmalı mı
                - "damage_amount": int — uygulanacak hasar (negatif sayı)
                - "animation_done": bool — animasyon bitti mi
                - "outcome": str — animasyon bittiyse karar:
                    "" — animasyon devam ediyor
                    "game_over" — oyuncu öldü
                    "player_turn" — sıra oyuncuya geçti
                - "feedback": str — animasyon bittiyse feedback metni
        """
        progress = min(elapsed / self.ENEMY_ATTACK_DURATION, 1.0)

        # Hasar animasyonun ortasında uygulanır (%50'de)
        apply_damage = False
        damage_amount = 0
        if elapsed >= self.ENEMY_ATTACK_DURATION * 0.5 and not self.enemy_attack_applied:
            if not self.defense_blocked and not self.dodged:
                apply_damage = True
                damage_amount = -self.enemy_attack_damage
            self.enemy_attack_applied = True

        # Animasyon bitti mi?
        animation_done = progress >= 1.0
        outcome = ""
        feedback = ""

        if animation_done:
            # HP kontrolü: hasar uygulandıktan sonraki HP
            if player_hp <= 0:
                outcome = "game_over"
            else:
                outcome = "player_turn"
                # Feedback metni — S05 fix: dodge vs savunma ayrımı
                if self.dodged:
                    feedback = (
                        "DEX DODGE! Dusman saldirisindan kactin! "
                        "Simdi senin siran!"
                    )
                elif self.defense_blocked:
                    feedback = (
                        "Mukemmel savunma! Dusman saldirisi engellendi! "
                        "Simdi senin siran!"
                    )
                elif self.defense_partial:
                    feedback = (
                        f"Kismi savunma! Hasar azaltildi: "
                        f"-{self.enemy_attack_damage} HP. "
                        f"Simdi senin siran!"
                    )
                else:
                    feedback = (
                        f"Dusman saldirdi! -{self.enemy_attack_damage} HP. "
                        f"Simdi senin siran!"
                    )
                # Bayrakları sıfırla
                self.defense_blocked = False
                self.defense_partial = False
                self.dodged = False

        return {
            "progress": progress,
            "apply_damage": apply_damage,
            "damage_amount": damage_amount,
            "animation_done": animation_done,
            "outcome": outcome,
            "feedback": feedback,
        }

    # ------------------------------------------------------------------ #
    #  SİLAH SEÇİM VE CHALLENGE BAŞLATMA KARARI                             #
    # ------------------------------------------------------------------ #

    # Challenge tipi olasılıkları
    SHAPE_CHALLENGE_CHANCE = 0.6  # %60 şekil çizme, %40 yumruk

    def resolve_weapon_selection(
        self,
        choice_text: str,
        weapons: list,
    ) -> Dict[str, Any]:
        """
        Savaş aksiyonu seçildikten sonra silah durumuna karar verir.

        Args:
            choice_text: Oyuncu aksiyonu ("Saldir", "Savun", "Kac", "Buyu").
            weapons: Envanterdeki savaş silahları listesi.

        Returns:
            dict: Karar bilgileri:
                - "action": str — seçilen aksiyon
                - "is_attack": bool — saldırı/büyü mü
                - "outcome": str — karar:
                    "unarmed" — silah yok, yumruk
                    "auto_select" — tek silah, otomatik seçim
                    "manual_select" — birden fazla silah, oyuncu seçecek
                    "no_weapon_needed" — savunma/kaçış, silah gerekmez
                - "selected_weapon": str — seçilen silah adı (otomatik seçimlerde)
                - "weapon_options": dict — seçim ekranı için silah seçenekleri
                    (sadece manual_select'te dolu)
                - "option_count": int — aktif seçenek sayısı

        SIDE-EFFECT: pending_combat_choice, weapon_select_options,
        weapon_combat_action, selected_weapon bayrakları güncellenir.
        """
        self.pending_combat_choice = choice_text
        action_lower = choice_text.lower()
        is_attack = action_lower in self.ACTION_ATTACK

        if not is_attack:
            # Savunma/Kaçış: silah gerekmez, direkt challenge
            return {
                "action": choice_text,
                "is_attack": False,
                "outcome": "no_weapon_needed",
                "selected_weapon": "",
                "weapon_options": {},
                "option_count": 0,
            }

        # Saldırı/Büyü: silah seçimi gerekli
        self.weapon_select_options = weapons
        self.weapon_combat_action = choice_text

        if len(weapons) == 0:
            # Silahsiz savas
            self.selected_weapon = "Yumruk"
            return {
                "action": choice_text,
                "is_attack": True,
                "outcome": "unarmed",
                "selected_weapon": "Yumruk",
                "weapon_options": {},
                "option_count": 0,
            }

        elif len(weapons) == 1:
            # Tek silah — otomatik seçim
            self.selected_weapon = weapons[0]
            return {
                "action": choice_text,
                "is_attack": True,
                "outcome": "auto_select",
                "selected_weapon": weapons[0],
                "weapon_options": {},
                "option_count": 0,
            }

        else:
            # Birden fazla silah — seçim ekranı
            option_keys = ["sol_ust", "sag_ust", "sol_alt", "sag_alt"]
            weapon_options = {}
            for i, key in enumerate(option_keys):
                if i < len(weapons):
                    weapon_options[key] = weapons[i]
                else:
                    weapon_options[key] = ""
            option_count = min(len(weapons), 4)

            return {
                "action": choice_text,
                "is_attack": True,
                "outcome": "manual_select",
                "selected_weapon": "",
                "weapon_options": weapon_options,
                "option_count": option_count,
            }

    def pick_challenge_type(self) -> str:
        """
        Challenge tipini rastgele seçer.

        Returns:
            "shape" — %60 olasılıkla şekil çizme challenge'ı
            "fist" — %40 olasılıkla yumruk challenge'ı
        """
        if random.random() < self.SHAPE_CHALLENGE_CHANCE:
            return "shape"
        return "fist"

