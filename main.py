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

from game.vision.vision_engine import HandTracker, Quadrant
from game.core.game_state import GameState, Character
from game.ai.ai_manager import AdventureAI
from game.ui.ui_renderer import GameUI
from game.challenges.shape_challenge import ShapeChallenge, ShapeType
from game.challenges.fist_challenge import FistChallenge
from game.audio.music_manager import MusicManager
from game.challenges.dice_challenge import DiceChallenge
from game.config.config_manager import load_config
from game.core.combat_manager import CombatManager
from game.core.inventory_handler import InventoryHandler
from game.core.game_phase import GamePhase


class DnDGame:
    """Webcam kontrollü D&D oyununun ana kontrol sınıfı."""

    WINDOW_NAME = "D&D Macera Oyunu"

    # Oyun fazlari (GamePhase enum — game_phase.py)

    SHAPE_TYPES = [ShapeType.TRIANGLE, ShapeType.SQUARE, ShapeType.CIRCLE,
                   ShapeType.RECTANGLE, ShapeType.INFINITY]

    def __init__(self, config: dict = None, camera_manager=None):
        self._config = config or load_config()

        # ----- Modulleri Baslat -----
        camera_index = self._config.get("camera_index", 0)
        print(f"[*] Kamera baslatiliyor (index={camera_index})...")

        # Paylasilan kamera varsa yeniden ACILMAZ (S22 fix — Asama 6.3)
        shared_capture = None
        if camera_manager is not None:
            shared_capture = camera_manager.get(camera_index)
        self.tracker = HandTracker(camera_index=camera_index, dwell_time=2.0,
                                   capture=shared_capture)

        if not self.tracker.camera_available:
            raise RuntimeError(
                f"Kamera {camera_index} acilamadi. "
                "Ayarlar menusunden kamera ID'nizi kontrol edin."
            )

        print("[*] AI motoru baslatiliyor...")
        self.ai = AdventureAI(
            api_key=self._config.get("api_key"),
            model=self._config.get("model_name", "gemini-2.5-flash"),
            max_tokens=self._config.get("max_tokens", 1024),
        )

        print("[*] Oyun durumu hazirlaniyor...")
        self.state = GameState(Character(name="Kahraman", char_class="Savasci"))

        print("[*] Arayuz hazirlaniyor...")
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
        self.current_phase = GamePhase.NORMAL

        # ----- Savaş Yöneticisi -----
        self.combat = CombatManager()

        # Geriye uyumluluk: eski self._xxx erişimleri için property benzeri referanslar
        # NOT: Aşama 4.4-4.6'da bu erişimler de CombatManager üzerinden yapılacak

        # ----- Muzik: son bilinen mod (gecis tespiti icin) -----
        self._last_music_mode: str = ""

        # ----- Envanter Fazi -----
        self.inventory = InventoryHandler()

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
                if self.current_phase == GamePhase.SHAPE_CHALLENGE:
                    self._handle_shape_challenge(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4b) Yumruk challenge aktif mi?
                if self.current_phase == GamePhase.FIST_CHALLENGE:
                    self._handle_fist_challenge(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4c) Dusman saldiri fazi aktif mi?
                if self.current_phase == GamePhase.ENEMY_ATTACK:
                    self._handle_enemy_attack(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4d) Silah secim fazi aktif mi?
                if self.current_phase == GamePhase.WEAPON_SELECT:
                    self._handle_weapon_select(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4e) Zar atma fazi aktif mi?
                if self.current_phase == GamePhase.DICE_ROLL:
                    self._handle_dice_roll(frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                    continue

                # 4f) Envanter fazi aktif mi?
                if self.current_phase == GamePhase.INVENTORY:
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
                            self.current_phase = GamePhase.DICE_ROLL
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

            # Tema muzigini baslat
            self.music.play_theme_music(choice_text)

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
        """Savas modunda secim yapildiginda silah secimi veya challenge baslatir.
        CombatManager.resolve_weapon_selection()'a delege eder."""
        self.tracker.reset_selection()

        weapons = self.state.get_combat_weapons()
        result = self.combat.resolve_weapon_selection(choice_text, weapons)

        if result["outcome"] == "unarmed":
            self.state.equipped_weapon = "Yumruk"
            print(f"[>] Silahsiz savas! Yumruk kullaniliyor.")
            self._start_actual_challenge(choice_text)

        elif result["outcome"] == "auto_select":
            self.state.equipped_weapon = result["selected_weapon"]
            print(f"[>] Tek silah, otomatik secildi: {result['selected_weapon']}")
            self._start_actual_challenge(choice_text)

        elif result["outcome"] == "manual_select":
            self.state.current_options = result["weapon_options"]
            self.state.active_option_count = result["option_count"]
            self.state.current_story = f"{choice_text} icin silahini sec!"
            self.current_phase = GamePhase.WEAPON_SELECT
            print(f"[>] Silah secim fazi basladi: {weapons}")

        else:
            # no_weapon_needed — savunma/kacis
            self._start_actual_challenge(choice_text)

    def _start_actual_challenge(self, choice_text: str) -> None:
        """Rastgele challenge (sekil veya yumruk) baslatir.
        CombatManager.pick_challenge_type()'a delege eder."""
        challenge_type = self.combat.pick_challenge_type()

        if challenge_type == "shape":
            shape = random.choice(self.SHAPE_TYPES)
            self.shape_challenge.start_challenge(shape, choice_text)
            self.current_phase = GamePhase.SHAPE_CHALLENGE
            print(f"[>] Sekil challenge basladi: {shape.value} - {choice_text}")
        else:
            self.fist_challenge.start_challenge(choice_text)
            self.current_phase = GamePhase.FIST_CHALLENGE
            print(f"[>] Yumruk challenge basladi - {choice_text}")

    def _restore_combat_options(self) -> None:
        """Savas modunda standart secenekleri geri yukler."""
        if self.state.current_mode == "savas":
            self.state.current_options = {
                "sol_ust": "Saldir",
                "sag_ust": "Savun",
                "sol_alt": "Kac",
                "sag_alt": "Buyu",
            }
            self.state.active_option_count = 4
            # current_story challenge sonucu ile guncelleniyor, burada degistirmeye gerek yok

    # ------------------------------------------------------------------ #
    #  SIRAS TABANLI SAVAS MEKANIGI                                       #
    # ------------------------------------------------------------------ #

    def _process_player_combat_result(self, accuracy: float, action: str,
                                       is_shape: bool = True) -> None:
        """
        Oyuncunun challenge sonucunu isler (CombatManager'a delege eder).

        CombatManager.evaluate_combat_result() karar mantığını yürütür,
        bu wrapper yan etkileri (state, faz, challenge reset) uygular.
        """
        stat_fx = self.state.get_stat_effect_on_combat()

        # CombatManager'da hesaplama + karar
        result = self.combat.evaluate_combat_result(
            accuracy=accuracy,
            action=action,
            is_shape=is_shape,
            selected_weapon=self.combat.selected_weapon,
            weapon_stats=self.state.get_weapon_stats(self.combat.selected_weapon),
            class_bonus=self.state.get_class_bonus(),
            stat_fx=stat_fx,
            enemy_hp=self.state.enemy_hp,
            player_hp=self.state.character.hp,
        )

        action_result = result["action_result"]
        outcome = result["outcome"]

        # Aksiyon sonuçlarını state'e uygula
        if result["action_type"] == "attack":
            self.state.enemy_hp = result["new_enemy_hp"]
            self.state.current_feedback = action_result["description"]
            self.state.current_story = action_result["description"]

        elif result["action_type"] == "defense":
            if action_result.get("heal", 0) > 0:
                self.state.modify_hp(action_result["heal"])
            self.state.current_feedback = action_result["description"]
            self.state.current_story = action_result["description"]

        elif result["action_type"] == "flee":
            self.state.current_feedback = action_result["description"]

        print(f"[!] HP: {self.state.character.hp} | Dusman HP: {self.state.enemy_hp}")

        # Sonuca göre yan etkileri uygula
        if outcome == "game_over":
            self.state.is_game_over = True
            self.state.game_over_reason = "Savas sirasinda yenildin!"
            self.current_phase = GamePhase.NORMAL
            self.shape_challenge.reset()
            self.fist_challenge.reset()

        elif outcome == "enemy_defeated":
            self._send_combat_result(accuracy, action)
            self.shape_challenge.reset()
            self.fist_challenge.reset()

        elif outcome == "flee_success":
            self._send_combat_result(accuracy, action)
            self.shape_challenge.reset()
            self.fist_challenge.reset()

        elif outcome == "extra_turn":
            self.state.current_feedback += result["feedback_append"]
            print("[!] EKSTRA TUR kazanildi!")
            self.current_phase = GamePhase.NORMAL
            self._restore_combat_options()
            self.shape_challenge.reset()
            self.fist_challenge.reset()

        elif outcome == "enemy_attack":
            self._start_enemy_attack()
            self.shape_challenge.reset()
            self.fist_challenge.reset()

    # ------------------------------------------------------------------ #
    #  DUSMAN SALDIRI FAZI                                                #
    # ------------------------------------------------------------------ #

    def _start_enemy_attack(self) -> None:
        """Dusman saldiri fazini baslatir. CombatManager'a delege eder."""
        stat_fx = self.state.get_stat_effect_on_combat()
        class_bonus = self.state.get_class_bonus()

        result = self.combat.calculate_enemy_damage(
            stat_fx=stat_fx,
            class_bonus=class_bonus,
        )

        if result["dodged"]:
            print(f"[>] DEX DODGE! Dusman saldirisi atlatildi!")
        elif result["blocked"]:
            print(f"[>] Dusman saldiri fazi basladi! SAVUNMA ENGELLEDI - Hasar: 0")
        elif result["partial"]:
            print(f"[>] Dusman saldiri fazi: KISMI SAVUNMA - Hasar: {result['damage']}")
        else:
            print(f"[>] Dusman saldiri fazi: Hasar: {result['damage']}")

        self.combat.enemy_attack_start = time.time()
        self.current_phase = GamePhase.ENEMY_ATTACK

    def _handle_enemy_attack(self, frame: np.ndarray) -> None:
        """Dusman saldiri animasyonunu yonetir. CombatManager'a delege eder."""
        now = time.time()
        elapsed = now - self.combat.enemy_attack_start

        # CombatManager'da hesaplama + karar
        tick = self.combat.resolve_enemy_attack_tick(
            elapsed=elapsed,
            player_hp=self.state.character.hp,
        )

        # Hasar uygulama (mid-animation)
        if tick["apply_damage"]:
            self.state.modify_hp(tick["damage_amount"])
            print(f"[!] Dusman saldirdi! {tick['damage_amount']} HP "
                  f"(kalan: {self.state.character.hp})")

        # Animasyon ekranini ciz (UI — main.py'de kalır)
        # S05 fix: dodged veya defense_blocked ise engelleme animasyonu
        is_blocked_visual = self.combat.defense_blocked or self.combat.dodged
        if is_blocked_visual:
            frame = self.ui.draw_enemy_attack(frame, tick["progress"],
                                               0, "Dusman",
                                               blocked=True)
        else:
            frame = self.ui.draw_enemy_attack(frame, tick["progress"],
                                               self.combat.enemy_attack_damage,
                                               "Dusman")

        # HUD'u da goster
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
        if tick["animation_done"]:
            if tick["outcome"] == "game_over":
                self.state.is_game_over = True
                self.state.game_over_reason = "Dusman saldirisiyla yenildin!"
                self.current_phase = GamePhase.NORMAL
            elif tick["outcome"] == "player_turn":
                self.current_phase = GamePhase.NORMAL
                self._restore_combat_options()
                self.state.current_feedback = tick["feedback"]
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
        """Challenge sonucuna gore hasar on izleme metni olusturur. CombatManager'a delege eder."""
        return self.combat.get_combat_preview(accuracy, action)

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
                self.combat.selected_weapon = weapon_name
                self.state.equipped_weapon = weapon_name
                self.tracker.reset_selection()
                print(f"[>] Silah secildi: {weapon_name}")
                # Challenge'i baslat
                self._start_actual_challenge(self.combat.weapon_combat_action)
                return

        # UI ciz
        frame = self.ui.draw_overlay(frame, 0.15)
        frame = self.ui.draw_story_text(frame, self.state.current_story,
                                         self.state.current_feedback,
                                         self.state.current_mode)
        frame = self.ui.draw_buttons(frame, self.state.current_options,
                                      hover_quadrant, progress,
                                      mode=self.state.current_mode)
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
            self.current_phase = GamePhase.NORMAL

    def _handle_inventory(self, frame: np.ndarray) -> None:
        """Envanter ekranini yonetir — InventoryHandler'a delege eder.

        Optimizasyon (5.4): draw_inventory tek kez çağrılır.
        Hit-test için önceki frame'in cache'lenmiş regions bilgisi kullanılır.
        Regions koordinatları frame'den frame'e değişmediği için
        1 frame gecikme pratik olarak fark edilmez (~16ms @ 60fps).
        """
        finger_pos = self.tracker.detect_finger(frame)

        all_weapons = self.state.get_all_weapons()
        equipped = self.state.equipped_items
        all_items = self.state.character.inventory

        if not all_weapons:
            self.current_phase = GamePhase.NORMAL
            return

        # Hit-test ve dwell hesaplama — cache'lenmiş regions ile
        cached_regions = self.inventory.get_cached_regions()
        self.inventory.reset_hover()
        self.inventory.hit_test(finger_pos, cached_regions)
        self.inventory.update_dwell(time.time(), cached_regions)

        # Tetiklenen aksiyon varsa uygula (side-effect'ler burada)
        action = self.inventory.consume_action()
        if action:
            atype = action["type"]
            if atype == "close_inventory":
                self.current_phase = GamePhase.NORMAL
                self.tracker.reset_selection()
                print(f"[>] Envanter kapatildi. Equipped: {self.state.equipped_items}")
                return
            elif atype == "page_change":
                print(f"[>] Sayfa: {action['page']}")
            elif atype == "toggle_equip":
                weapon = action["weapon"]
                result = self.state.toggle_equipped(weapon)
                status = "EQUIPPED" if result else "UNEQUIPPED"
                print(f"[>] {weapon} -> {status}")
            elif atype == "shop_buy":
                if self.state.shop_buy(action["index"]):
                    self.state.current_feedback = "Stat satin alindi!"
                else:
                    self.state.current_feedback = "Yeterli altin yok!"
            elif atype == "shop_roll":
                if self.state.shop_roll():
                    self.state.current_feedback = "Secenekler yenilendi!"
                else:
                    self.state.current_feedback = "Yeterli altin yok!"

        # Güncel verilerle TEK draw_inventory çağrısı
        shop_items = self.state.get_shop_items()
        shop_roll_cost = self.state.get_shop_roll_cost()
        gold = self.state.character.gold

        frame, regions = self.ui.draw_inventory(
            frame, all_weapons, equipped, all_items,
            self.state.get_weapon_stats,
            self.inventory.page,
            self.inventory.hovered_idx,
            self.inventory.hovered_devam,
            self.inventory.dwell_progress,
            total_stats=self.state.get_total_stats(),
            stat_names=self.state.STAT_NAMES,
            shop_items=shop_items,
            shop_roll_cost=shop_roll_cost,
            gold=gold,
            hovered_shop=self.inventory.hovered_shop,
            hovered_roll=self.inventory.hovered_roll,
            hovered_prev=self.inventory.hovered_prev,
            hovered_next=self.inventory.hovered_next
        )

        # Regions'ı sonraki frame için cache'le
        self.inventory.cache_regions(regions)

        if finger_pos:
            frame = self.ui.draw_finger_cursor(frame, finger_pos)
        frame = self.tracker.draw_hand_landmarks(frame)

        cv2.imshow(self.WINDOW_NAME, frame)

    def _send_combat_result(self, accuracy: float, action: str) -> None:
        """Savas sonucunu AI'a gonderir."""
        self.current_phase = GamePhase.NORMAL
        self.combat.extra_turn_active = False

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
                self.state._api_error = False

                # Muzik modu gecisi: savas <-> normal
                current_mode = self.state.current_mode
                if current_mode != self._last_music_mode:
                    if current_mode == "savas":
                        self.music.play_battle_music()
                    elif self._last_music_mode == "savas":
                        # Savastan cikildiysa envanter goster + shop sifirla
                        self.music.resume_class_music()
                        self.state.init_shop()  # Shop'u sifirla
                        self.current_phase = GamePhase.INVENTORY
                        self.inventory.reset()
                        self.inventory.page = 0
                        print("[>] Savas bitti! Envanter + Shop aciliyor...")
                    self._last_music_mode = current_mode

                # Savas/baslangic disinda rastgele can dolumu
                heal_msg = self.state.try_random_healing()
                if heal_msg:
                    self.state.current_feedback = heal_msg
                    print(f"[+] {heal_msg}")
            elif error:
                print(f"[!] AI hatası: {error}")
                self.state.is_waiting_for_ai = False
                # Hatay ekranda goster
                # Hata mesajini sadeleştir
                err_short = str(error)
                if "invalid_api_key" in err_short:
                    err_short = "API anahtari gecersiz! Ayarlardan kontrol edin."
                elif "quota" in err_short.lower() or "rate" in err_short.lower():
                    err_short = "API kotasi doldu veya istek limiti asildi!"
                elif "model" in err_short.lower() and "not found" in err_short.lower():
                    err_short = "Secilen AI modeli bulunamadi! Ayarlardan degistirin."
                elif "connection" in err_short.lower() or "timeout" in err_short.lower():
                    err_short = "Baglanti hatasi! Internet baglantinizi kontrol edin."
                elif len(err_short) > 80:
                    err_short = err_short[:80] + "..."
                self.state.current_story = f"[HATA] {err_short}"
                self.state.current_feedback = "Tekrar denemek icin bir secenek secin."
                self.state._api_error = True

    def _restart(self) -> None:
        """Oyunu yeniden başlatır."""
        print("[*] Oyun yeniden başlatılıyor...")
        self.state.reset()
        self._init_startup()
        self.current_phase = GamePhase.NORMAL
        self.shape_challenge.reset()
        self.fist_challenge.reset()
        self.dice_challenge.reset()
        self.combat.extra_turn_active = False
        self._last_music_mode = ""
        self.combat.selected_weapon = ""
        self.inventory.reset()
        self.music.stop()


def main():
    print("=" * 50)
    print("  WEBCAM KONTROLLU D&D ROL YAPMA OYUNU")
    print("=" * 50)

    # Kamera TEK BIR YERDE acilir, menu ve oyun arasinda paylasilir (S22).
    from game.vision.camera_manager import CameraManager
    camera = CameraManager()

    try:
        while True:
            # ---- ANA MENU ----
            from game.ui.menu_system import MenuSystem
            menu = MenuSystem(camera_manager=camera)
            config = menu.run()

            if config.get("_action") == "exit":
                print("[*] Oyundan cikiliyor...")
                break

            # ---- OYUNU BASLAT ----
            try:
                game = DnDGame(config=config, camera_manager=camera)
                game.run()
            except KeyboardInterrupt:
                print("\n[*] Oyun kullanici tarafindan durduruldu.")
            except Exception as e:
                print(f"\n[!] Hata: {e}")
                # Hatadan sonra menuye don (crash etmesin)
                import traceback
                traceback.print_exc()
                print("\n[*] Ana menuye donuluyor...")
                continue

            # Oyun bittiyse menuye don
            print("\n[*] Ana menuye donuluyor...")
            continue
    finally:
        camera.release()


if __name__ == "__main__":
    main()
