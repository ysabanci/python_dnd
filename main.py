"""
main.py - Ana Oyun Döngüsü
============================
Tüm modülleri senkronize ederek oyunu çalıştırır.
Geometrik şekil çizme savaş sistemi entegre edilmiştir.
"""

import sys
import random
import cv2
import numpy as np

from vision_engine import HandTracker, Quadrant
from game_state import GameState, Character
from ai_manager import AdventureAI
from ui_renderer import GameUI
from shape_challenge import ShapeChallenge, ShapeType
from fist_challenge import FistChallenge


class DnDGame:
    """Webcam kontrollü D&D oyununun ana kontrol sınıfı."""

    WINDOW_NAME = "D&D Macera Oyunu"

    # Oyun fazlari
    PHASE_NORMAL = "normal"
    PHASE_SHAPE_CHALLENGE = "shape_challenge"
    PHASE_FIST_CHALLENGE = "fist_challenge"

    SHAPE_TYPES = [ShapeType.TRIANGLE, ShapeType.SQUARE, ShapeType.CIRCLE,
                   ShapeType.RECTANGLE, ShapeType.INFINITY]

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

        # ----- Oyun Fazı -----
        self.current_phase = self.PHASE_NORMAL
        self._pending_combat_choice = ""

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
                                             hover_quadrant, progress, self.state.current_mode)

                if finger_pos:
                    frame = self.ui.draw_finger_cursor(frame, finger_pos)

                frame = self.tracker.draw_hand_landmarks(frame)

                cv2.imshow(self.WINDOW_NAME, frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:
            self.tracker.release()
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
        """Normal oyun gidisatinda secim yapar."""
        prompt = self.state.get_dynamic_prompt(choice_text)
        self.state.add_user_choice(prompt)
        self.state.is_waiting_for_ai = True
        self.tracker.reset_selection()

        history = self.state.get_message_history()
        self.ai.request_story(history)

    def _start_combat_challenge(self, choice_text: str) -> None:
        """Savas modunda secim yapildiginda rastgele challenge baslatir."""
        self._pending_combat_choice = choice_text
        self.tracker.reset_selection()

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

    def _handle_shape_challenge(self, frame: np.ndarray) -> None:
        """Sekil cizme mini oyunu fazini yonetir."""

        finger_pos = self.tracker.detect_finger(frame)
        result = self.shape_challenge.update(finger_pos)

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

            action_lower = action.lower()
            is_attack = action_lower in ("saldir", "saldiri", "buyu")
            is_defense = action_lower in ("savun", "savunma")
            is_flee = action_lower in ("kac", "kacis")

            # ----- Oyuncu HP degisimi (sadece basarisiz/kismi) -----
            if accuracy >= 70:
                # Basarili hamle: oyuncu hasar ALMAZ
                if is_attack:
                    enemy_dmg = random.randint(25, 40)
                    self.state.enemy_hp = max(0, self.state.enemy_hp - enemy_dmg)
                    self.state.current_feedback = f"Basarili! Dusmana -{enemy_dmg} hasar!"
                elif is_defense:
                    self.state.current_feedback = "Mukemmel savunma! Hasar engellendi."
                elif is_flee:
                    self.state.current_feedback = "Basariyla kactin!"
            elif accuracy >= 40:
                # Kismi basari: az hasar al
                damage = random.randint(3, 10)
                self.state.modify_hp(-damage)
                if is_attack:
                    enemy_dmg = random.randint(10, 20)
                    self.state.enemy_hp = max(0, self.state.enemy_hp - enemy_dmg)
                    self.state.current_feedback = f"Kismi basari! -{damage} HP, dusmana -{enemy_dmg}"
                elif is_defense:
                    self.state.current_feedback = f"Zayif savunma! -{damage} HP"
                else:
                    self.state.current_feedback = f"Kismi basari! -{damage} HP"
            else:
                # Basarisiz: cok hasar al, dusmana hasar yok
                damage = random.randint(10, 25)
                self.state.modify_hp(-damage)
                self.state.current_feedback = f"Basarisiz! -{damage} HP"

            print(f"[!] HP: {self.state.character.hp} | Dusman HP: {self.state.enemy_hp}")

            # HP 0'a dustuyse oyun bitsin
            if self.state.character.hp <= 0:
                self.state.is_game_over = True
                self.state.game_over_reason = "Savas sirasinda yenildin!"
                self.current_phase = self.PHASE_NORMAL
                self.shape_challenge.reset()
                return

            self._send_combat_result(accuracy, action)
            self.shape_challenge.reset()

    def _handle_fist_challenge(self, frame: np.ndarray) -> None:
        """Yumruk mini oyunu fazini yonetir."""

        # Once parmak tespiti yap (detect_fist icin _last_result gerekli)
        self.tracker.detect_finger(frame)
        fist_pos, is_fist = self.tracker.detect_fist(frame)

        self.fist_challenge.update(fist_pos, is_fist)

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

            action_lower = action.lower()
            is_attack = action_lower in ("saldir", "saldiri", "buyu")
            is_defense = action_lower in ("savun", "savunma")
            is_flee = action_lower in ("kac", "kacis")

            # HP degisimi (ayni mantik)
            if accuracy >= 70:
                if is_attack:
                    enemy_dmg = random.randint(25, 40)
                    self.state.enemy_hp = max(0, self.state.enemy_hp - enemy_dmg)
                    self.state.current_feedback = f"Basarili! Dusmana -{enemy_dmg} hasar!"
                elif is_defense:
                    self.state.current_feedback = "Mukemmel savunma! Hasar engellendi."
                elif is_flee:
                    self.state.current_feedback = "Basariyla kactin!"
            elif accuracy >= 40:
                damage = random.randint(3, 10)
                self.state.modify_hp(-damage)
                if is_attack:
                    enemy_dmg = random.randint(10, 20)
                    self.state.enemy_hp = max(0, self.state.enemy_hp - enemy_dmg)
                    self.state.current_feedback = f"Kismi basari! -{damage} HP, dusmana -{enemy_dmg}"
                elif is_defense:
                    self.state.current_feedback = f"Zayif savunma! -{damage} HP"
                else:
                    self.state.current_feedback = f"Kismi basari! -{damage} HP"
            else:
                damage = random.randint(10, 25)
                self.state.modify_hp(-damage)
                self.state.current_feedback = f"Basarisiz! -{damage} HP"

            print(f"[!] HP: {self.state.character.hp} | Dusman HP: {self.state.enemy_hp}")

            if self.state.character.hp <= 0:
                self.state.is_game_over = True
                self.state.game_over_reason = "Savas sirasinda yenildin!"
                self.current_phase = self.PHASE_NORMAL
                self.fist_challenge.reset()
                return

            self._send_combat_result(accuracy, action)
            self.fist_challenge.reset()

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
