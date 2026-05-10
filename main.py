"""
main.py - Ana Oyun Döngüsü
============================
Tüm modülleri senkronize ederek oyunu çalıştırır.
Geometrik şekil çizme savaş sistemi entegre edilmiştir.

Savaş Mekanigi (Turn-Based):
  1. Oyuncunun sırası -> challenge (şekil/yumruk)
  2. Düşmanın sırası -> 3sn saldırı animasyonu + hasar
  3. Tekrar oyuncunun sırası (veya extra turn)
"""

import sys
import time
import random
import cv2
import numpy as np

from vision_engine import HandTracker, Quadrant
from game_state import GameState, Character
from ai_manager import AdventureAI
from ui_renderer import GameUI
from shape_challenge import ShapeChallenge, ShapeType
from fist_challenge import FistChallenge
from music_manager import MusicManager
from dice_challenge import DiceChallenge


class DnDGame:
    """Webcam kontrollü D&D oyununun ana kontrol sınıfı."""

    WINDOW_NAME = "D&D Macera Oyunu"

    # Oyun fazlari
    PHASE_NORMAL = "normal"
    PHASE_SHAPE_CHALLENGE = "shape_challenge"
    PHASE_FIST_CHALLENGE = "fist_challenge"
    PHASE_ENEMY_ATTACK = "enemy_attack"
    PHASE_WEAPON_SELECT = "weapon_select"
    PHASE_DICE_ROLL = "dice_roll"
    PHASE_INVENTORY = "inventory"

    SHAPE_TYPES = [ShapeType.TRIANGLE, ShapeType.SQUARE, ShapeType.CIRCLE,
                   ShapeType.RECTANGLE, ShapeType.INFINITY]

    # Dusman saldiri suresi (saniye)
    ENEMY_ATTACK_DURATION = 3.0

    # Kritik vurus esigi (sekil challenge %85+)
    CRITICAL_HIT_THRESHOLD = 85

    # Basarili saldiri sonrasi ekstra tur sansi (%30)
    EXTRA_TURN_CHANCE = 0.30

    def __init__(self):
        # ----- Modülleri Başlat -----
        print("[*] Kamera başlatılıyor...")
        self.tracker = HandTracker(camera_index=0, dwell_time=2.0)

        print("[*] AI motoru başlatılıyor...")
        self.ai = AdventureAI()

        print("[*] Oyun durumu hazırlanıyor...")
        self.state = GameState(Character(name="Kahraman", char_class="Savaşçı"))

        print("[*] Arayüz hazırlanıyor...")
        self.ui = GameUI(self.tracker.frame_width, self.tracker.frame_height)

        print("[*] Sekil challenge modulu hazirlaniyor...")
        self.shape_challenge = ShapeChallenge(self.tracker.frame_width, self.tracker.frame_height)

        print("[*] Yumruk challenge modulu hazirlaniyor...")
        self.fist_challenge = FistChallenge(self.tracker.frame_width, self.tracker.frame_height)

        print("[*] Muzik sistemi hazirlaniyor...")
        self.music = MusicManager()

        print("[*] Zar challenge modulu hazirlaniyor...")
        self.dice_challenge = DiceChallenge(self.tracker.frame_width, self.tracker.frame_height)

        # ----- Oyun Fazı -----
        self.current_phase = self.PHASE_NORMAL
        self._pending_combat_choice = ""

        # ----- Silah Secim Fazi -----
        self._weapon_select_options: list = []
        self._selected_weapon: str = ""
        self._weapon_combat_action: str = ""

        # ----- Dusman Saldiri Fazi -----
        self._enemy_attack_start: float = 0.0
        self._enemy_attack_damage: int = 0
        self._enemy_attack_applied: bool = False

        # ----- Ekstra Tur (saldiri sonrasi) -----
        self._extra_turn_active: bool = False

        # ----- Basarili savunma bayraği -----
        self._defense_blocked: bool = False
        self._defense_partial: bool = False

        # ----- Muzik: son bilinen mod (gecis tespiti icin) -----
        self._last_music_mode: str = ""

        # ----- Envanter Fazi -----
        self._inventory_page: int = 0
        self._inv_hovered_idx: int = -1
        self._inv_hovered_devam: bool = False
        self._inv_dwell_start: float = 0.0
        self._inv_dwell_target: str = ""  # "item:X" veya "devam" veya "prev"/"next"

        # ----- Acilis: Karakter Olusturma -----
        print("[*] Karakter olusturma bekleniyor...")
        self._init_startup()

    def run(self) -> None:
        """Ana oyun döngüsü."""
        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        # Windows 11'de kucuk pencere sorununu cozmek icin minimum boyut ayarla
        win_w = max(self.tracker.frame_width, 960)
        win_h = max(self.tracker.frame_height, 720)
        cv2.resizeWindow(self.WINDOW_NAME, win_w, win_h)

        try:
            while True:
                # 1) Kameradan kare oku
                frame = self.tracker.read_frame()
                if frame is None:
                    print("[!] Kamera okunamadı.")
                    break

                # 2) Oyun bittiyse
                if self.state.is_game_over:
                    frame = self.ui.draw_game_over(frame, self.state.game_over_reason)
                    cv2.imshow(self.WINDOW_NAME, frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("r"):
                        self._restart()
                    elif key == ord("q"):
                        break
                    continue

                # 3) AI bekleniyor mu?
                if self.state.is_waiting_for_ai:
                    self._check_ai_response()
                    frame = self.ui.draw_overlay(frame, 0.3)
                    frame = self.ui.draw_loading(frame)
                    cv2.imshow(self.WINDOW_NAME, frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4) Sekil cizme challenge aktif mi?
                if self.current_phase == self.PHASE_SHAPE_CHALLENGE:
                    self._handle_shape_challenge(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4b) Yumruk challenge aktif mi?
                if self.current_phase == self.PHASE_FIST_CHALLENGE:
                    self._handle_fist_challenge(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4c) Dusman saldiri fazi aktif mi?
                if self.current_phase == self.PHASE_ENEMY_ATTACK:
                    self._handle_enemy_attack(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4d) Silah secim fazi aktif mi?
                if self.current_phase == self.PHASE_WEAPON_SELECT:
                    self._handle_weapon_select(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4e) Zar atma fazi aktif mi?
                if self.current_phase == self.PHASE_DICE_ROLL:
                    self._handle_dice_roll(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4f) Envanter fazi aktif mi?
                if self.current_phase == self.PHASE_INVENTORY:
                    self._handle_inventory(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 5) Normal oyun akisi - El takibi
                finger_pos = self.tracker.detect_finger(frame)

                hover_quadrant = None
                progress = 0.0
                selected = None

                if finger_pos:
                    btn_qid = self.ui.get_quadrant_from_button(
                        finger_pos[0], finger_pos[1], self.state.current_options)
                    if btn_qid:
                        qmap = {"sol_ust": Quadrant.SOL_UST, "sag_ust": Quadrant.SAG_UST,
                                "sol_alt": Quadrant.SOL_ALT, "sag_alt": Quadrant.SAG_ALT}
                        q_enum = qmap.get(btn_qid)
                        selected = self.tracker.update_dwell(q_enum)
                        hover_quadrant = btn_qid
                        progress = self.tracker.get_dwell_progress()
                    else:
                        self.tracker.update_dwell(None)
                else:
                    self.tracker.update_dwell(None)

                # 6) Seçim yapıldıysa
                if selected:
                    qid = selected.value
                    choice_text = self.state.current_options.get(qid, "...")
                    print(f"[>] Seçim: {qid} -> {choice_text}")

                    if self.state.is_startup:
                        self._handle_startup_choice(choice_text)
                    elif self.state.current_mode == "savas":
                        self._start_combat_challenge(choice_text)
                    else:
                        # Zar gerektiren secenek mi kontrol et
                        if (self.state.dice_required
                                and qid == self.state.dice_option_key):
                            self.dice_challenge.start_challenge(choice_text)
                            self.current_phase = self.PHASE_DICE_ROLL
                            self.state.dice_required = False
                            self.state.dice_option_key = ""
                            print(f"[>] Zar atma tetiklendi: {choice_text}")
                        else:
                            self._handle_normal_choice(choice_text)

                # 7) Arayüzü çiz
                frame = self.ui.draw_overlay(frame, 0.35)
                # Baslangic modunda "baslangic" mode'u goster
                display_mode = "baslangic" if self.state.is_startup else self.state.current_mode
                frame = self.ui.draw_story_text(frame, self.state.current_story,
                                                self.state.current_feedback,
                                                display_mode)
                frame = self.ui.draw_hud(frame, self.state.character.hp, self.state.character.max_hp,
                                         self.state.character.gold, self.state.turn_count,
                                         self.state.current_location, self.state.current_mode,
                                         self.state.enemy_hp, self.state.enemy_max_hp)
                frame = self.ui.draw_buttons(frame, self.state.current_options,
                                             hover_quadrant, progress, self.state.current_mode,
                                             self.state.dice_option_key if self.state.dice_required else "",
                                             self.state.get_advantage_key())

                if finger_pos:
                    frame = self.ui.draw_finger_cursor(frame, finger_pos)

                frame = self.tracker.draw_hand_landmarks(frame)

                cv2.imshow(self.WINDOW_NAME, frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:
            self.tracker.release()
            self.music.cleanup()
            cv2.destroyAllWindows()
            print("[*] Oyun kapatıldı.")

    # ------------------------------------------------------------------ #
    #  OZEL METODLAR                                                      #
    # ------------------------------------------------------------------ #

    def _init_startup(self) -> None:
        """Baslangic asamasini hazirlar."""
        self.state.is_startup = True
        self.state.startup_step = 0
        self.state.current_mode = "kesif"
        self.state.current_story = "Kahramanini olustur! Sinifini sec."
        self.state.current_options = {
            "sol_ust": "Savasci",
            "sag_ust": "Buyucu",
            "sol_alt": "Okcu",
            "sag_alt": "Hirsiz"
        }

    def _handle_startup_choice(self, choice_text: str) -> None:
        """Baslangic asamasinda secim yapar (class -> weapon -> destination)."""
        step = self.state.startup_step
        self.tracker.reset_selection()

        if step == 0:
            # Sinif secildi
            self.state.apply_class_choice(choice_text)
            weapons = self.state.get_weapons_for_class(choice_text)
            self.state.current_story = f"{choice_text} sinifini sectin! Simdi ilk silahini sec."
            self.state.current_options = {
                "sol_ust": weapons[0], "sag_ust": weapons[1],
                "sol_alt": weapons[2], "sag_alt": weapons[3],
            }
            self.state.startup_step = 1
            print(f"[>] Sinif secildi: {choice_text}")

            # Sinif muzigini baslat
            self.music.play_class_music(choice_text)

        elif step == 1:
            # Silah secildi
            self.state.apply_weapon_choice(choice_text)
            locations = self.state.get_random_locations()
            self.state.current_story = f"{choice_text} silahini sectin! Nereye gitmek istersin?"
            self.state.current_options = {
                "sol_ust": locations[0], "sag_ust": locations[1],
                "sol_alt": locations[2], "sag_alt": locations[3],
            }
            self.state.startup_step = 2
            print(f"[>] Silah secildi: {choice_text}")

        elif step == 2:
            # Lokasyon secildi -> oyunu baslat
            self.state.current_theme = choice_text
            self.state.is_startup = False
            self.state.current_mode = "kesif"
            self.state.add_user_choice(f"Tema secildi: {choice_text}")

            self.state.is_waiting_for_ai = True
            history = self.state.get_message_history()
            prompt = (
                f"Oyun basladi! Secilen tema/lokasyon: {choice_text}. "
                f"{self.state.get_character_summary()}. "
                f"Buna uygun cok kisa bir acilis hikayesi ver ve ilk aksiyonlari sun."
            )
            history.append({"role": "user", "content": prompt})
            self.ai.request_story(history)
            print(f"[>] Lokasyon secildi: {choice_text} -> Oyun basliyor!")

    def _handle_normal_choice(self, choice_text: str) -> None:
        """Normal oyun gidisatinda secim yapar. Bekleyen ganimet varsa kontrol eder."""
        # Bekleyen ganimet kontrolu
        if self.state.pending_loot:
            choice_lower = choice_text.lower()
            loot_keywords = ("ganimet", "al", "topla", "esya", "silah",
                             "kabul", "evet", "loot")
            reject_keywords = ("birak", "reddet", "hayir", "devam",
                               "gec", "birakma", "istemiyorum")
            # Reddetme kontrolu (oncelikli)
            is_reject = any(kw in choice_lower for kw in reject_keywords)
            is_accept = any(kw in choice_lower for kw in loot_keywords)

            if is_accept and not is_reject:
                loot = self.state.pending_loot
                self.state.character.inventory.append(loot)
                print(f"[+] Ganimet alindi: {loot}")
                # Silahsa ve yer varsa otomatik equip
                if (loot not in self.state.NON_WEAPON_ITEMS
                        and len(self.state.equipped_items) < 4):
                    self.state.equipped_items.append(loot)
                    print(f"[+] Otomatik equip: {loot}")
                self.state.current_feedback = f"Ganimet alindi: {loot}!"
            else:
                print(f"[-] Ganimet reddedildi: {self.state.pending_loot}")
            # Bekleyen ganimeti temizle (alinsin ya da alinmasin)
            self.state.pending_loot = ""

        prompt = self.state.get_dynamic_prompt(choice_text)
        self.state.add_user_choice(prompt)
        self.state.is_waiting_for_ai = True
        self.tracker.reset_selection()

        history = self.state.get_message_history()
        self.ai.request_story(history)

    def _start_combat_challenge(self, choice_text: str) -> None:
        """Savas modunda secim yapildiginda silah secimi veya challenge baslatir."""
        self._pending_combat_choice = choice_text
        self.tracker.reset_selection()

        action_lower = choice_text.lower()
        is_attack = action_lower in ("saldir", "saldiri", "buyu")

        if is_attack:
            # Saldiri/Buyu: once silah sec, sonra challenge
            weapons = self.state.get_combat_weapons()
            self._weapon_select_options = weapons
            self._weapon_combat_action = choice_text

            if len(weapons) <= 1:
                # Tek silah varsa direkt challenge (secim ekrani atla)
                self._selected_weapon = weapons[0] if weapons else "Yumruk"
                self.state.equipped_weapon = self._selected_weapon
                print(f"[>] Tek silah, otomatik secildi: {self._selected_weapon}")
                self._start_actual_challenge(choice_text)
            else:
                # Birden fazla silah: secim ekrani goster
                option_keys = ["sol_ust", "sag_ust", "sol_alt", "sag_alt"]
                self.state.current_options = {}
                for i, key in enumerate(option_keys):
                    if i < len(weapons):
                        self.state.current_options[key] = weapons[i]
                    else:
                        self.state.current_options[key] = ""
                self.state.active_option_count = min(len(weapons), 4)
                self.state.current_story = f"{choice_text} icin silahini sec!"
                self.current_phase = self.PHASE_WEAPON_SELECT
                print(f"[>] Silah secim fazi basladi: {weapons}")
        else:
            # Savunma/Kacis: direkt challenge
            self._start_actual_challenge(choice_text)

    def _start_actual_challenge(self, choice_text: str) -> None:
        """Rastgele challenge (sekil veya yumruk) baslatir."""
        # Rastgele: %60 sekil cizme, %40 yumruk challenge
        if random.random() < 0.6:
            shape = random.choice(self.SHAPE_TYPES)
            self.shape_challenge.start_challenge(shape, choice_text)
            self.current_phase = self.PHASE_SHAPE_CHALLENGE
            print(f"[>] Sekil challenge basladi: {shape.value} - {choice_text}")
        else:
            self.fist_challenge.start_challenge(choice_text)
            self.current_phase = self.PHASE_FIST_CHALLENGE
            print(f"[>] Yumruk challenge basladi - {choice_text}")

    def _restore_combat_options(self) -> None:
        """Savas modunda standart secenekleri geri yukler (silah seciminden sonra)."""
        if self.state.current_mode == "savas":
            self.state.current_options = {
                "sol_ust": "Saldir",
                "sag_ust": "Savun",
                "sol_alt": "Kac",
                "sag_alt": "Buyu",
            }
            self.state.active_option_count = 4
            self.state.current_story = "Savas devam ediyor! Hamleni sec."

    # ------------------------------------------------------------------ #
    #  SIRAS TABANLI SAVAS MEKANIGI                                       #
    # ------------------------------------------------------------------ #

    def _process_player_combat_result(self, accuracy: float, action: str,
                                       is_shape: bool = True) -> None:
        """
        Oyuncunun challenge sonucunu isler (yeni turn-based mantik).

        Kurallar:
          - Saldiri/Buyu:
              %85+ (sekil) = KRITIK VURUS (1.5x hasar)
              %70+ = basarili (normal hasar)
              %40+ = kismi (az hasar + oyuncu az hasar alir)
              <%40 = basarisiz (oyuncu hasar alir)
            Basarili saldiri sonrasi %30 ekstra tur sansi
          - Savunma:
              %70+ = basarili -> can yenilenir
              %40+ = kismi -> az hasar
              <%40 = basarisiz -> normal hasar
          - Kac:
              %70+ = basarili kacis
              <%70 = basarisiz, hasar alir
        """
        action_lower = action.lower()
        is_attack = action_lower in ("saldir", "saldiri", "buyu")
        is_defense = action_lower in ("savun", "savunma")
        is_flee = action_lower in ("kac", "kacis")

        grant_extra_turn = False

        # Stat etkileri
        stat_fx = self.state.get_stat_effect_on_combat()

        if is_attack:
            self._process_attack(accuracy, action, is_shape, stat_fx)
            # Basarili saldiri -> ekstra tur sansi (LUCK arttirir)
            extra_chance = self.EXTRA_TURN_CHANCE + stat_fx.get("extra_turn_bonus", 0)
            if accuracy >= 70 and random.random() < extra_chance:
                grant_extra_turn = True

        elif is_defense:
            self._process_defense(accuracy)

        elif is_flee:
            self._process_flee(accuracy, stat_fx)

        print(f"[!] HP: {self.state.character.hp} | Dusman HP: {self.state.enemy_hp}")

        # HP 0 kontrolu
        if self.state.character.hp <= 0:
            self.state.is_game_over = True
            self.state.game_over_reason = "Savas sirasinda yenildin!"
            self.current_phase = self.PHASE_NORMAL
            self.shape_challenge.reset()
            self.fist_challenge.reset()
            return

        # Dusman yenildiyse -> AI'a bildir
        if self.state.enemy_hp <= 0:
            self._send_combat_result(accuracy, action)
            self.shape_challenge.reset()
            self.fist_challenge.reset()
            return

        # Kacis basariliysa -> AI'a bildir (sinif bonusuyla esik kontrol)
        class_bonus = self.state.get_class_bonus()
        flee_threshold = class_bonus.get("flee_threshold", 70)
        if is_flee and accuracy >= flee_threshold:
            self._send_combat_result(accuracy, action)
            self.shape_challenge.reset()
            self.fist_challenge.reset()
            return

        # Ekstra tur kontrolu
        if grant_extra_turn:
            self._extra_turn_active = True
            self.state.current_feedback += " | EKSTRA TUR!"
            print("[!] EKSTRA TUR kazanildi!")
            # Direkt oyuncunun sirasina don (dusman saldiramaz)
            self.current_phase = self.PHASE_NORMAL
            self._restore_combat_options()
            self.shape_challenge.reset()
            self.fist_challenge.reset()
            return

        # Normal akis: dusman saldiri fazina gec
        self._start_enemy_attack()
        self.shape_challenge.reset()
        self.fist_challenge.reset()

    def _process_attack(self, accuracy: float, action: str,
                        is_shape: bool, stat_fx: dict = None) -> None:
        """
        Saldiri/Buyu sonucunu isler.
        Stat etkileri: STR -> fiziksel bonus, INT -> buyusel bonus, LUCK -> crit esigi.
        """
        if stat_fx is None:
            stat_fx = self.state.get_stat_effect_on_combat()

        # Silah ve sinif bonuslarini al
        weapon_stats = self.state.get_weapon_stats(self._selected_weapon)
        class_bonus = self.state.get_class_bonus()
        weapon_bonus = weapon_stats.get("bonus", 0)
        weapon_type = weapon_stats.get("type", "fiziksel")

        # Sinif carpani
        action_lower = action.lower()
        if action_lower == "buyu" or weapon_type == "buyusel":
            class_mult = class_bonus.get("magic_mult", 1.0)
            stat_bonus = stat_fx.get("magic_bonus", 0)
        else:
            class_mult = class_bonus.get("attack_mult", 1.0)
            stat_bonus = stat_fx.get("attack_bonus", 0)

        # LUCK bazli kritik esigi dusurme
        crit_threshold = self.CRITICAL_HIT_THRESHOLD - stat_fx.get("crit_bonus", 0)

        if is_shape and accuracy >= crit_threshold:
            # KRITIK VURUS!
            base_dmg = random.randint(30, 50) + weapon_bonus + stat_bonus
            enemy_dmg = int(base_dmg * 1.5 * class_mult)
            self.state.enemy_hp = max(0, self.state.enemy_hp - enemy_dmg)
            self.state.current_feedback = f"KRITIK VURUS! Dusmana -{enemy_dmg} hasar!"
            print(f"[!!] KRITIK VURUS! Dusmana -{enemy_dmg} (silah: {self._selected_weapon})")
        elif accuracy >= 70:
            # Basarili saldiri
            base_dmg = random.randint(25, 40) + weapon_bonus + stat_bonus
            enemy_dmg = int(base_dmg * class_mult)
            self.state.enemy_hp = max(0, self.state.enemy_hp - enemy_dmg)
            self.state.current_feedback = f"Basarili {action}! Dusmana -{enemy_dmg} hasar!"
        elif accuracy >= 40:
            # Kismi basari
            base_dmg = random.randint(10, 20) + weapon_bonus // 2 + stat_bonus // 2
            enemy_dmg = int(base_dmg * class_mult)
            self.state.enemy_hp = max(0, self.state.enemy_hp - enemy_dmg)
            self.state.current_feedback = f"Kismi basari! Dusmana -{enemy_dmg} hasar."
        else:
            # Basarisiz
            self.state.current_feedback = f"Basarisiz {action}! Dusman saldirisi geliyor!"

    def _process_defense(self, accuracy: float) -> None:
        """
        Savunma sonucunu isler.

        Savunma ASLA dogrudan hasar vermez. Bunun yerine bir kalkan durumu
        belirler ve dusmanin bir sonraki saldiri hasarini etkiler:
          - Basarili (>=70%): Dusmanin saldirisi tamamen engellenir + HP yenilenir
          - Kismi (>=40%): Dusmanin saldiri hasari %50 azalir
          - Basarisiz (<40%): Dusman tam hasar verir (ama challenge'dan hasar yok)
        """
        if accuracy >= 70:
            # Basarili savunma: CAN YENILENIR + dusman saldirisi engellenir
            heal = random.randint(8, 20)
            self.state.modify_hp(heal)
            self.state.current_feedback = f"Mukemmel savunma! +{heal} HP yenilendi!"
            self._defense_blocked = True
            self._defense_partial = False
            print(f"[+] Savunma basarili! +{heal} HP (dusman saldirisi engellenecek)")
        elif accuracy >= 40:
            # Kismi savunma: hasar yok, ama dusmanin saldirisi %50 azalir
            self.state.current_feedback = "Kismi savunma! Dusman hasari azalacak."
            self._defense_blocked = False
            self._defense_partial = True
            print(f"[~] Kismi savunma! Dusman hasari yarilayacak")
        else:
            # Basarisiz savunma: hasar yok, dusman tam hasar verir
            self.state.current_feedback = "Savunma basarisiz! Dusman tam hasar verecek."
            self._defense_blocked = False
            self._defense_partial = False
            print(f"[-] Savunma basarisiz! Dusman normal saldirisi gelecek")

    def _process_flee(self, accuracy: float, stat_fx: dict = None) -> None:
        """
        Kacis sonucunu isler.
        DEX stat'i kacis basari esigini dusurur.
        """
        if stat_fx is None:
            stat_fx = self.state.get_stat_effect_on_combat()

        class_bonus = self.state.get_class_bonus()
        flee_threshold = class_bonus.get("flee_threshold", 70)
        # DEX bazli kacis bonusu (esigi dusurur)
        flee_threshold = max(30, flee_threshold - stat_fx.get("flee_bonus", 0))

        if accuracy >= flee_threshold:
            self.state.current_feedback = "Basariyla kactin!"
        else:
            self.state.current_feedback = "Kacilamadi! Dusman saldirisi geliyor!"

    # ------------------------------------------------------------------ #
    #  DUSMAN SALDIRI FAZI                                                #
    # ------------------------------------------------------------------ #

    def _start_enemy_attack(self) -> None:
        """Dusman saldiri fazini baslatir. DEF stat'i hasari azaltir, DEX dodge sansi verir."""
        stat_fx = self.state.get_stat_effect_on_combat()

        # DEX bazli dodge (tamamen kacinma)
        dodge_chance = stat_fx.get("dodge_chance", 0)
        if dodge_chance > 0 and random.random() < dodge_chance:
            self._enemy_attack_damage = 0
            self._defense_blocked = True
            print(f"[>] DEX DODGE! Dusman saldirisi atlatildi!")
            self._enemy_attack_start = time.time()
            self._enemy_attack_applied = False
            self.current_phase = self.PHASE_ENEMY_ATTACK
            return

        # Sinif savunma bonusu (Okcu: %20 hasar azaltma)
        class_bonus = self.state.get_class_bonus()
        defense_reduction = class_bonus.get("defense_reduction", 0.0)
        # DEF stat bazli ek azaltma
        stat_defense = stat_fx.get("defense_reduction", 0.0)
        total_reduction = min(0.6, defense_reduction + stat_defense)

        if self._defense_blocked:
            self._enemy_attack_damage = 0
            print(f"[>] Dusman saldiri fazi basladi! SAVUNMA ENGELLEDI - Hasar: 0")
        elif self._defense_partial:
            full_dmg = random.randint(8, 22)
            reduced = int(full_dmg * (1.0 - total_reduction))
            self._enemy_attack_damage = reduced // 2
            print(f"[>] Dusman saldiri fazi: KISMI SAVUNMA - Hasar: {self._enemy_attack_damage}")
        else:
            full_dmg = random.randint(8, 22)
            self._enemy_attack_damage = int(full_dmg * (1.0 - total_reduction))
            print(f"[>] Dusman saldiri fazi: Hasar: {self._enemy_attack_damage}")
        self._enemy_attack_start = time.time()
        self._enemy_attack_applied = False
        self.current_phase = self.PHASE_ENEMY_ATTACK

    def _handle_enemy_attack(self, frame: np.ndarray) -> None:
        """Dusman saldiri animasyonunu yonetir."""
        now = time.time()
        elapsed = now - self._enemy_attack_start
        progress = min(elapsed / self.ENEMY_ATTACK_DURATION, 1.0)

        # Hasar animasyonun ortasinda uygulanir (1.5sn'de)
        if elapsed >= self.ENEMY_ATTACK_DURATION * 0.5 and not self._enemy_attack_applied:
            if self._defense_blocked:
                # Savunma basarili: hasar yok
                print(f"[!] Dusman saldirdi ama SAVUNMA ENGELLEDI! Hasar: 0")
            else:
                self.state.modify_hp(-self._enemy_attack_damage)
                print(f"[!] Dusman saldirdi! -{self._enemy_attack_damage} HP "
                      f"(kalan: {self.state.character.hp})")
            self._enemy_attack_applied = True

        # Animasyon ekranini ciz
        if self._defense_blocked:
            frame = self.ui.draw_enemy_attack(frame, progress,
                                               0, "Dusman",
                                               blocked=True)
        else:
            frame = self.ui.draw_enemy_attack(frame, progress,
                                               self._enemy_attack_damage,
                                               "Dusman")

        # HUD'u da goster (HP degisimini gormek icin)
        frame = self.ui.draw_hud(frame, self.state.character.hp,
                                  self.state.character.max_hp,
                                  self.state.character.gold,
                                  self.state.turn_count,
                                  self.state.current_location,
                                  self.state.current_mode,
                                  self.state.enemy_hp,
                                  self.state.enemy_max_hp)

        cv2.imshow(self.WINDOW_NAME, frame)

        # Animasyon bitti mi?
        if progress >= 1.0:
            # HP kontrolu
            if self.state.character.hp <= 0:
                self.state.is_game_over = True
                self.state.game_over_reason = "Dusman saldirisiyla yenildin!"
                self.current_phase = self.PHASE_NORMAL
                return

            # Sira tekrar oyuncuya geciyor
            self.current_phase = self.PHASE_NORMAL
            self._restore_combat_options()
            if self._defense_blocked:
                self.state.current_feedback = (
                    "Mukemmel savunma! Dusman saldirisi engellendi! "
                    "Simdi senin siran!"
                )
            elif self._defense_partial:
                self.state.current_feedback = (
                    f"Kismi savunma! Hasar azaltildi: -{self._enemy_attack_damage} HP. "
                    f"Simdi senin siran!"
                )
            else:
                self.state.current_feedback = (
                    f"Dusman saldirdi! -{self._enemy_attack_damage} HP. "
                    f"Simdi senin siran!"
                )
            # Bayraklari sifirla
            self._defense_blocked = False
            self._defense_partial = False
            print(f"[>] Sira oyuncuya gecti. HP: {self.state.character.hp}")

    # ------------------------------------------------------------------ #
    #  CHALLENGE HANDLER'LAR                                               #
    # ------------------------------------------------------------------ #

    def _handle_shape_challenge(self, frame: np.ndarray) -> None:
        """Sekil cizme mini oyunu fazini yonetir."""
        finger_pos = self.tracker.detect_finger(frame)
        result = self.shape_challenge.update(finger_pos)

        # Result state'inde hasar bilgisini goster
        if (self.shape_challenge.state.value == "result"
                and not self.shape_challenge.result_extra_text):
            accuracy, action = self.shape_challenge.get_result()
            self.shape_challenge.result_extra_text = self._get_combat_preview(accuracy, action)

        # Challenge UI ciz
        frame = self.shape_challenge.draw(frame)

        # Parmak imlecini goster (cizim modunda)
        if finger_pos and self.shape_challenge.state.value == "drawing":
            frame = self.ui.draw_finger_cursor(frame, finger_pos)

        # El iskeletini ciz
        frame = self.tracker.draw_hand_landmarks(frame)

        cv2.imshow(self.WINDOW_NAME, frame)

        # Challenge tamamlandi mi?
        if self.shape_challenge.is_done():
            accuracy, action = self.shape_challenge.get_result()
            print(f"[>] Sekil sonucu: %{accuracy:.0f} dogruluk - {action}")
            self._process_player_combat_result(accuracy, action, is_shape=True)

    def _handle_fist_challenge(self, frame: np.ndarray) -> None:
        """Yumruk mini oyunu fazini yonetir."""
        # Once parmak tespiti yap (detect_fist icin _last_result gerekli)
        self.tracker.detect_finger(frame)
        fist_pos, is_fist = self.tracker.detect_fist(frame)

        self.fist_challenge.update(fist_pos, is_fist)

        # Result state'inde hasar bilgisini goster
        if (self.fist_challenge.state.value == "result"
                and not self.fist_challenge.result_extra_text):
            accuracy, action = self.fist_challenge.get_result()
            self.fist_challenge.result_extra_text = self._get_combat_preview(accuracy, action)

        # Challenge UI ciz
        frame = self.fist_challenge.draw(frame)

        # Yumruk imleci goster
        if fist_pos and is_fist:
            cv2.circle(frame, fist_pos, 20, (50, 50, 255), 3)
            cv2.circle(frame, fist_pos, 8, (50, 255, 50), -1)
        elif fist_pos:
            cv2.circle(frame, fist_pos, 15, (200, 200, 200), 2)

        # El iskeletini ciz
        frame = self.tracker.draw_hand_landmarks(frame)

        cv2.imshow(self.WINDOW_NAME, frame)

        # Challenge tamamlandi mi?
        if self.fist_challenge.is_done():
            accuracy, action = self.fist_challenge.get_result()
            print(f"[>] Yumruk sonucu: %{accuracy:.0f} dogruluk - {action}")
            self._process_player_combat_result(accuracy, action, is_shape=False)

    def _get_combat_preview(self, accuracy: float, action: str) -> str:
        """Challenge sonucuna gore hasar on izleme metni olusturur."""
        action_lower = action.lower()
        is_attack = action_lower in ("saldir", "saldiri", "buyu")
        is_defense = action_lower in ("savun", "savunma")
        is_flee = action_lower in ("kac", "kacis")

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
    #  SILAH SECIM VE ZAR HANDLER'LARI                                     #
    # ------------------------------------------------------------------ #

    def _handle_weapon_select(self, frame: np.ndarray) -> None:
        """Silah secim fazini yonetir (saldiri/buyu oncesi)."""
        finger_pos = self.tracker.detect_finger(frame)

        hover_quadrant = None
        progress = 0.0
        selected = None

        if finger_pos:
            btn_qid = self.ui.get_quadrant_from_button(
                finger_pos[0], finger_pos[1], self.state.current_options)
            if btn_qid:
                qmap = {"sol_ust": Quadrant.SOL_UST, "sag_ust": Quadrant.SAG_UST,
                        "sol_alt": Quadrant.SOL_ALT, "sag_alt": Quadrant.SAG_ALT}
                q_enum = qmap.get(btn_qid)
                selected = self.tracker.update_dwell(q_enum)
                hover_quadrant = btn_qid
                progress = self.tracker.get_dwell_progress()
            else:
                self.tracker.update_dwell(None)
        else:
            self.tracker.update_dwell(None)

        # Secim yapildiysa
        if selected is not None:
            qmap_rev = {Quadrant.SOL_UST: "sol_ust", Quadrant.SAG_UST: "sag_ust",
                        Quadrant.SOL_ALT: "sol_alt", Quadrant.SAG_ALT: "sag_alt"}
            key = qmap_rev.get(selected, "")
            weapon_name = self.state.current_options.get(key, "")
            if weapon_name:
                self._selected_weapon = weapon_name
                self.state.equipped_weapon = weapon_name
                self.tracker.reset_selection()
                print(f"[>] Silah secildi: {weapon_name}")
                # Challenge'i baslat
                self._start_actual_challenge(self._weapon_combat_action)
                return

        # UI ciz
        frame = self.ui.draw_overlay(frame, 0.15)
        frame = self.ui.draw_story_text(frame, self.state.current_story,
                                         self.state.current_feedback,
                                         self.state.current_mode)
        frame = self.ui.draw_buttons(frame, self.state.current_options,
                                      hover_quadrant, progress,
                                      self.state.active_option_count)
        if finger_pos:
            frame = self.ui.draw_finger_cursor(frame, finger_pos)
        frame = self.tracker.draw_hand_landmarks(frame)

        # HUD
        frame = self.ui.draw_hud(frame, self.state.character.hp,
                                  self.state.character.max_hp,
                                  self.state.character.gold,
                                  self.state.turn_count,
                                  self.state.current_location,
                                  self.state.current_mode,
                                  self.state.enemy_hp,
                                  self.state.enemy_max_hp)

        cv2.imshow(self.WINDOW_NAME, frame)

    def _handle_dice_roll(self, frame: np.ndarray) -> None:
        """Zar atma fazini yonetir."""
        # El tespiti (yumruk jesti zari tetikler)
        self.tracker.detect_finger(frame)
        _, is_fist = self.tracker.detect_fist(frame)

        self.dice_challenge.update(has_gesture=is_fist)

        # Challenge UI ciz
        frame = self.dice_challenge.draw(frame)

        # El iskeletini ciz
        frame = self.tracker.draw_hand_landmarks(frame)

        cv2.imshow(self.WINDOW_NAME, frame)

        # Challenge tamamlandi mi?
        if self.dice_challenge.is_done():
            dice_result, action_text = self.dice_challenge.get_result()
            print(f"[>] Zar sonucu: {dice_result} - {action_text}")

            # Zar sonucunu AI'a gonder
            prompt = self.state.get_dynamic_prompt(action_text)
            prompt += (
                f"\nZAR SONUCU: Oyuncu d20 zari atti ve {dice_result} geldi. "
            )
            if dice_result >= 15:
                prompt += "YUKSEK ZAR! Bu eylem cok basarili olsun. Oyuncuyu odullendir."
            elif dice_result >= 10:
                prompt += "ORTA ZAR. Eylem basarili ama muhtemelen ekstra bir odulu olmadi."
            elif dice_result >= 6:
                prompt += "DUSUK ZAR. Eylem kismi basarili olsun. Bazi sorunlar ciksin."
            elif dice_result == 1:
                prompt += "KRITIK BASARISIZLIK! Eylem feci sekilde basarisiz olsun. Oyuncuya zarar gelsin!"
            else:
                prompt += "BASARISIZ ZAR. Eylem basarisiz olsun. Olumsuz sonuc dogursun."

            self.state.add_user_choice(prompt)
            self.state.is_waiting_for_ai = True
            history = self.state.get_message_history()
            self.ai.request_story(history)

            self.dice_challenge.reset()
            self.current_phase = self.PHASE_NORMAL

    INV_DWELL_TIME = 1.2  # Envanter item secimi suresi (saniye)
    INV_DEVAM_DWELL = 1.5  # Devam butonu secim suresi

    def _handle_inventory(self, frame: np.ndarray) -> None:
        """Envanter ekranini yonetir - el takibiyle item equip/unequip."""
        finger_pos = self.tracker.detect_finger(frame)

        # Mevcut silahlar ve envanter
        all_weapons = self.state.get_all_weapons()
        equipped = self.state.equipped_items
        all_items = self.state.character.inventory

        # Eger silah yoksa direkt devam
        if not all_weapons:
            self.current_phase = self.PHASE_NORMAL
            print("[>] Envanterde silah yok, devam ediliyor...")
            return

        # Hover tespiti
        hovered_idx = -1
        hovered_devam = False
        dwell_progress = 0.0

        # Onceki frame'den regions'i kullanmak icin preview ciz
        frame_preview, regions = self.ui.draw_inventory(
            frame, all_weapons, equipped, all_items,
            self.state.get_weapon_stats,
            self._inventory_page,
            self._inv_hovered_idx,
            self._inv_hovered_devam,
            dwell_progress,
            total_stats=self.state.get_total_stats(),
            stat_names=self.state.STAT_NAMES
        )

        if finger_pos:
            fx, fy = finger_pos

            # Item satirlarina bak
            for i, (item_name, (x1, y1, x2, y2)) in enumerate(regions['items']):
                if x1 <= fx <= x2 and y1 <= fy <= y2:
                    hovered_idx = i
                    break

            # Devam butonuna bak
            if regions['devam']:
                dx1, dy1, dx2, dy2 = regions['devam']
                if dx1 <= fx <= dx2 and dy1 <= fy <= dy2:
                    hovered_devam = True

            # Onceki sayfa butonuna bak
            if regions['prev']:
                px1, py1, px2, py2 = regions['prev']
                if px1 <= fx <= px2 and py1 <= fy <= py2:
                    target = "prev"
                    if self._inv_dwell_target != target:
                        self._inv_dwell_target = target
                        self._inv_dwell_start = time.time()
                    elif time.time() - self._inv_dwell_start >= 0.8:
                        self._inventory_page = max(0, self._inventory_page - 1)
                        self._inv_dwell_start = time.time()
                        self.tracker.reset_selection()

            # Sonraki sayfa butonuna bak
            if regions['next']:
                nx1, ny1, nx2, ny2 = regions['next']
                if nx1 <= fx <= nx2 and ny1 <= fy <= ny2:
                    target = "next"
                    if self._inv_dwell_target != target:
                        self._inv_dwell_target = target
                        self._inv_dwell_start = time.time()
                    elif time.time() - self._inv_dwell_start >= 0.8:
                        self._inventory_page += 1
                        self._inv_dwell_start = time.time()
                        self.tracker.reset_selection()

        # Dwell hesapla
        now = time.time()
        current_target = ""

        if hovered_idx >= 0:
            items_on_page = regions['items']
            if hovered_idx < len(items_on_page):
                item_name = items_on_page[hovered_idx][0]
                current_target = f"item:{item_name}"
        elif hovered_devam:
            current_target = "devam"

        # Target degistiyse timer sifirla
        if current_target != self._inv_dwell_target:
            self._inv_dwell_target = current_target
            self._inv_dwell_start = now

        # Dwell progress hesapla
        if current_target:
            dwell_time = self.INV_DEVAM_DWELL if current_target == "devam" else self.INV_DWELL_TIME
            elapsed = now - self._inv_dwell_start
            dwell_progress = min(elapsed / dwell_time, 1.0)

            if dwell_progress >= 1.0:
                # Secim tamamlandi
                if current_target == "devam":
                    # Envanterden cik
                    self.current_phase = self.PHASE_NORMAL
                    self._inv_dwell_target = ""
                    self.tracker.reset_selection()
                    print(f"[>] Envanter kapatildi. Equipped: {self.state.equipped_items}")
                    return
                elif current_target.startswith("item:"):
                    weapon = current_target[5:]
                    result = self.state.toggle_equipped(weapon)
                    status = "EQUIPPED" if result else "UNEQUIPPED"
                    print(f"[>] {weapon} -> {status}")
                    # Timer'i sifirla ama target'i degistirme (bekleme efekti)
                    self._inv_dwell_start = now
                    self._inv_dwell_target = ""

        # Update hover state
        self._inv_hovered_idx = hovered_idx
        self._inv_hovered_devam = hovered_devam

        # Gercek frame'i ciz (guncellenmis hover/progress ile)
        frame, _ = self.ui.draw_inventory(
            frame, all_weapons, equipped, all_items,
            self.state.get_weapon_stats,
            self._inventory_page,
            hovered_idx, hovered_devam, dwell_progress,
            total_stats=self.state.get_total_stats(),
            stat_names=self.state.STAT_NAMES
        )

        # Parmak imleci
        if finger_pos:
            frame = self.ui.draw_finger_cursor(frame, finger_pos)
        frame = self.tracker.draw_hand_landmarks(frame)

        cv2.imshow(self.WINDOW_NAME, frame)

    def _send_combat_result(self, accuracy: float, action: str) -> None:
        """Savas sonucunu AI'a gonderir."""
        self.current_phase = self.PHASE_NORMAL

        # Sonucu state'e kaydet
        self.state.pending_combat_result = {
            "accuracy": accuracy,
            "action": action,
        }

        prompt = self.state.get_dynamic_prompt(action)
        self.state.add_user_choice(prompt)
        self.state.is_waiting_for_ai = True

        history = self.state.get_message_history()
        self.ai.request_story(history)

    def _check_ai_response(self) -> None:
        """AI yanıtını kontrol eder ve durumu günceller."""
        if not self.ai.is_requesting():
            response = self.ai.get_last_response()
            error = self.ai.get_last_error()

            if response:
                self.state.update_from_ai_response(response)
                self.state.add_ai_response(str(response))
                self.state.is_waiting_for_ai = False

                # Muzik modu gecisi: savas <-> normal
                current_mode = self.state.current_mode
                if current_mode != self._last_music_mode:
                    if current_mode == "savas":
                        self.music.play_battle_music()
                    elif self._last_music_mode == "savas":
                        # Savastan cikildiysa envanter goster
                        self.music.resume_class_music()
                        self.current_phase = self.PHASE_INVENTORY
                        self._inventory_page = 0
                        self._inv_dwell_start = 0.0
                        self._inv_dwell_target = ""
                        print("[>] Savas bitti! Envanter ekrani aciliyor...")
                    self._last_music_mode = current_mode

                # Savas/baslangic disinda rastgele can dolumu
                heal_msg = self.state.try_random_healing()
                if heal_msg:
                    self.state.current_feedback = heal_msg
                    print(f"[+] {heal_msg}")
            elif error:
                print(f"[!] AI hatası: {error}")
                self.state.is_waiting_for_ai = False

    def _restart(self) -> None:
        """Oyunu yeniden başlatır."""
        print("[*] Oyun yeniden başlatılıyor...")
        self.state.reset()
        self._init_startup()
        self.current_phase = self.PHASE_NORMAL
        self.shape_challenge.reset()
        self.fist_challenge.reset()
        self.dice_challenge.reset()
        self._extra_turn_active = False
        self._last_music_mode = ""
        self._selected_weapon = ""
        self._inventory_page = 0
        self._inv_dwell_target = ""
        self.music.stop()


def main():
    print("=" * 50)
    print("  WEBCAM KONTROLLÜ D&D ROL YAPMA OYUNU")
    print("  İşaret parmağınızı butonlarda 2sn bekletin")
    print("  'Q' = Çıkış")
    print("=" * 50)

    try:
        game = DnDGame()
        game.run()
    except KeyboardInterrupt:
        print("\n[*] Oyun kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\n[!] Hata: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
