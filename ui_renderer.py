"""
ui_renderer.py - Oyun Arayuz Cizici
======================================
OpenCV ile seffaf butonlar, progress bar ve hikaye metni cizer.
Turkce ozel karakterler ASCII karsiliklarina donusturulur.
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple


def sanitize_text(text: str) -> str:
    """Turkce ozel karakterleri ASCII karsiliklarina donusturur."""
    tr_map = {
        "ş": "s", "Ş": "S",
        "ç": "c", "Ç": "C",
        "ğ": "g", "Ğ": "G",
        "ı": "i", "İ": "I",
        "ö": "o", "Ö": "O",
        "ü": "u", "Ü": "U",
    }
    for tr_char, ascii_char in tr_map.items():
        text = text.replace(tr_char, ascii_char)
    return text


class GameUI:
    """OpenCV tabanli oyun arayuzu cizici - uzaktan okunabilir buyuk UI."""

    # Renk paleti (BGR)
    COLOR_BG_OVERLAY = (20, 20, 20)
    COLOR_BUTTON_NORMAL = (50, 50, 50)
    COLOR_BUTTON_HOVER = (60, 120, 180)
    COLOR_BUTTON_SELECTED = (40, 180, 40)
    COLOR_TEXT_WHITE = (255, 255, 255)
    COLOR_TEXT_GOLD = (50, 215, 255)
    COLOR_TEXT_STORY = (230, 230, 230)
    COLOR_HP_BAR_BG = (40, 40, 40)
    COLOR_HP_BAR_FG = (50, 50, 220)
    COLOR_HP_BAR_HIGH = (50, 200, 50)
    COLOR_HP_BAR_LOW = (50, 50, 230)
    COLOR_PROGRESS_BAR = (0, 200, 255)
    COLOR_BORDER = (120, 120, 120)
    COLOR_BORDER_HOVER = (100, 180, 255)
    COLOR_TITLE = (100, 200, 255)
    COLOR_LABEL = (180, 180, 180)

    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_BOLD = cv2.FONT_HERSHEY_DUPLEX

    # Buyutulmus font olcekleri (uzaktan okunabilirlik) - %15-20 arttirildi
    FONT_SCALE_TITLE = 1.4
    FONT_SCALE_STORY = 0.8
    FONT_SCALE_BTN = 0.75
    FONT_SCALE_BTN_LABEL = 0.55
    FONT_SCALE_HUD = 0.85
    FONT_SCALE_HP = 0.75
    FONT_SCALE_LOADING = 1.4
    FONT_SCALE_GAMEOVER = 1.7
    FONT_THICKNESS = 2
    FONT_THICKNESS_THIN = 2

    # Buton etiketleri
    BUTTON_LABELS = {
        "sol_ust": "[1] Sol Ust",
        "sag_ust": "[2] Sag Ust",
        "sol_alt": "[3] Sol Alt",
        "sag_alt": "[4] Sag Alt",
    }

    def __init__(self, frame_width: int, frame_height: int):
        self.w = frame_width
        self.h = frame_height
        self.mid_x = frame_width // 2
        self.mid_y = frame_height // 2

        # ---- Layout: Hikaye -> HUD -> Butonlar (cakismaz) ----
        margin = 12
        gap = 10

        # Hikaye alani (ust %33)
        self.story_top = 55
        self.story_bottom = int(self.h * 0.33)

        # HUD bandi (hikaye ile butonlar arasi)
        self.hud_y = self.story_bottom + 8
        self.hud_height = 30

        # Butonlar (HUD'un altindan ekranin altina kadar)
        btn_area_top = self.hud_y + self.hud_height + 10
        btn_area_bottom = self.h - margin

        available_w = self.w - margin * 2 - gap
        available_h = btn_area_bottom - btn_area_top - gap

        btn_w = available_w // 2
        btn_h = available_h // 2

        left_x = margin
        right_x = margin + btn_w + gap
        top_y = btn_area_top
        bottom_y = btn_area_top + btn_h + gap

        self.button_regions = {
            "sol_ust": (left_x, top_y, left_x + btn_w, top_y + btn_h),
            "sag_ust": (right_x, top_y, right_x + btn_w, top_y + btn_h),
            "sol_alt": (left_x, bottom_y, left_x + btn_w, bottom_y + btn_h),
            "sag_alt": (right_x, bottom_y, right_x + btn_w, bottom_y + btn_h),
        }

        # Layout hesaplama icin sabitler
        self._layout_margin = margin
        self._layout_gap = gap
        self._btn_area_top = btn_area_top
        self._btn_area_bottom = btn_area_bottom

        # Dinamik buton bolgeleri (draw_buttons tarafindan guncellenir)
        self._active_button_regions = dict(self.button_regions)

    def draw_overlay(self, frame: np.ndarray, alpha: float = 0.4) -> np.ndarray:
        """Yari-seffaf koyu overlay cizer."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), self.COLOR_BG_OVERLAY, -1)
        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    def draw_story_text(self, frame: np.ndarray, story: str, feedback: str = "",
                         mode: str = "kesif") -> np.ndarray:
        """Hikaye metnini ve (varsa) feedback'i text-wrapping ile cizer."""
        story = sanitize_text(story)
        feedback = sanitize_text(feedback)

        # Baslik - moda gore degisir
        if mode == "baslangic":
            title = "-- BASLANGIC --"
            title_color = (50, 200, 255)  # Altin/sari
        elif mode == "savas":
            title = "-- SAVAS --"
            title_color = (60, 60, 255)  # Kirmizi (BGR)
        elif mode == "diyalog":
            title = "-- DIYALOG --"
            title_color = (100, 255, 200)  # Yesil
        else:
            title = "-- MACERA --"
            title_color = self.COLOR_TITLE

        (tw, _), _ = cv2.getTextSize(title, self.FONT_BOLD, self.FONT_SCALE_TITLE, 2)
        title_x = (self.w - tw) // 2
        cv2.putText(frame, title, (title_x, 42), self.FONT_BOLD,
                    self.FONT_SCALE_TITLE, title_color, 2)

        # Hikaye metni - satir kaydirma
        max_width = self.w - 50
        line_height = 32
        lines = self._wrap_text(story, self.FONT, self.FONT_SCALE_STORY,
                                self.FONT_THICKNESS_THIN, max_width)

        # Arka plan kutusu
        box_top = self.story_top - 5
        box_h = len(lines) * line_height + 20
        box_bottom = min(box_top + box_h, self.story_bottom)

        overlay = frame.copy()
        cv2.rectangle(overlay, (10, box_top), (self.w - 10, box_bottom),
                      self.COLOR_BG_OVERLAY, -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        cv2.rectangle(frame, (10, box_top), (self.w - 10, box_bottom),
                      self.COLOR_BORDER, 1)

        # Metni ciz
        y = self.story_top + 18
        for line in lines:
            if y > box_bottom - 5:
                break
            cv2.putText(frame, line, (25, y), self.FONT,
                        self.FONT_SCALE_STORY, self.COLOR_TEXT_STORY,
                        self.FONT_THICKNESS_THIN, cv2.LINE_AA)
            y += line_height

        # Eger feedback varsa, hikaye kutusunun hemen altina ciz
        if feedback:
            feedback_y = box_bottom + 25
            (fw, fh), _ = cv2.getTextSize(feedback, self.FONT, self.FONT_SCALE_BTN, 1)
            cv2.putText(frame, feedback, ((self.w - fw) // 2, feedback_y),
                        self.FONT, self.FONT_SCALE_BTN, self.COLOR_TEXT_GOLD,
                        self.FONT_THICKNESS_THIN, cv2.LINE_AA)

        return frame

    def draw_buttons(self, frame: np.ndarray, options: Dict[str, str],
                     hover_quadrant: Optional[str] = None,
                     progress: float = 0.0,
                     mode: str = "kesif",
                     dice_option_key: str = "",
                     advantage_key: str = "") -> np.ndarray:
        """4 buton cizer. Savas modunda renkli butonlar. Avantaj ve zar badge'leri gosterir."""

        # Savas modunda buton renkleri (BGR)
        COMBAT_COLORS = {
            "sol_ust": (60, 60, 180),    # Saldir - Kirmizi
            "sag_ust": (180, 120, 40),   # Savun - Mavi
            "sol_alt": (40, 180, 180),   # Kac - Sari
            "sag_alt": (160, 50, 160),   # Buyu - Mor
        }
        COMBAT_BORDERS = {
            "sol_ust": (80, 80, 220),
            "sag_ust": (220, 160, 60),
            "sol_alt": (60, 220, 220),
            "sag_alt": (200, 80, 200),
        }

        # Dinamik layout hesapla
        layout = self._compute_button_layout(options)
        self._active_button_regions = layout

        for qid, (x1, y1, x2, y2) in layout.items():
            text = sanitize_text(options.get(qid, ""))
            # Bos secenekleri atla
            if not text:
                continue
            btn_w = x2 - x1
            btn_h = y2 - y1

            # Buton rengi
            is_hovered = hover_quadrant == qid
            if is_hovered and progress >= 1.0:
                color = self.COLOR_BUTTON_SELECTED
                border_color = (50, 255, 50)
                border_thick = 2
            elif is_hovered:
                if mode == "savas":
                    color = COMBAT_COLORS.get(qid, self.COLOR_BUTTON_HOVER)
                else:
                    color = self.COLOR_BUTTON_HOVER
                border_color = self.COLOR_BORDER_HOVER
                border_thick = 2
            else:
                if mode == "savas":
                    color = COMBAT_COLORS.get(qid, self.COLOR_BUTTON_NORMAL)
                    border_color = COMBAT_BORDERS.get(qid, self.COLOR_BORDER)
                else:
                    color = self.COLOR_BUTTON_NORMAL
                    border_color = self.COLOR_BORDER
                border_thick = 1

            # Seffaf buton
            overlay = frame.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
            alpha = 0.7 if is_hovered else 0.55
            frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, border_thick)

            # Buton etiketi (sol ust kose)
            label = self.BUTTON_LABELS.get(qid, "")
            cv2.putText(frame, label, (x1 + 8, y1 + 20), self.FONT,
                        self.FONT_SCALE_BTN_LABEL, self.COLOR_LABEL,
                        self.FONT_THICKNESS_THIN, cv2.LINE_AA)

            # Buton metni (ortali, wrapping)
            self._draw_button_text(frame, text, x1 + 10, y1 + 25,
                                   btn_w - 20, btn_h - 35)

            # Progress bar (hover durumunda)
            if is_hovered and 0 < progress < 1.0:
                bar_h = 6
                bar_y = y2 - bar_h - 3
                bar_total_w = btn_w - 8
                bar_fill_w = int(bar_total_w * progress)
                cv2.rectangle(frame, (x1 + 4, bar_y),
                              (x1 + 4 + bar_total_w, bar_y + bar_h),
                              self.COLOR_HP_BAR_BG, -1)
                cv2.rectangle(frame, (x1 + 4, bar_y),
                              (x1 + 4 + bar_fill_w, bar_y + bar_h),
                              self.COLOR_PROGRESS_BAR, -1)
                cv2.rectangle(frame, (x1 + 4, bar_y),
                              (x1 + 4 + bar_total_w, bar_y + bar_h),
                              self.COLOR_BORDER, 1)

            # Zar ikonu (zar gerektiren butonda)
            if dice_option_key == qid:
                zar_text = "[ZAR]"
                (zw, zh), _ = cv2.getTextSize(zar_text, self.FONT, 0.5, 1)
                zx = x2 - zw - 8
                zy = y1 + zh + 6
                cv2.putText(frame, zar_text, (zx, zy), self.FONT,
                            0.5, self.COLOR_TEXT_GOLD, 1, cv2.LINE_AA)

            # Avantaj badge (sinif avantajli butonda)
            if advantage_key == qid and mode == "savas":
                adv_text = "Avantaj"
                (aw, ah), _ = cv2.getTextSize(adv_text, self.FONT, 0.5, 1)
                ax = x2 - aw - 8
                ay = y1 + ah + 6
                # Zar badge varsa alta kaydir
                if dice_option_key == qid:
                    ay += 18
                cv2.putText(frame, adv_text, (ax, ay), self.FONT,
                            0.5, (50, 255, 200), 1, cv2.LINE_AA)

        return frame

    def draw_hud(self, frame: np.ndarray, hp: int, max_hp: int,
                 gold: int, turn: int, location: str,
                 mode: str = "kesif", enemy_hp: int = 0,
                 enemy_max_hp: int = 100) -> np.ndarray:
        """HUD bandi (HP bar, altin, tur, dusman HP) - hikaye ile butonlar arasinda."""
        # HUD arka plan bandi
        hud_bg_y1 = self.hud_y - 4
        hud_bg_y2 = self.hud_y + self.hud_height + 4
        overlay = frame.copy()
        cv2.rectangle(overlay, (8, hud_bg_y1), (self.w - 8, hud_bg_y2),
                      (15, 15, 15), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        cv2.rectangle(frame, (8, hud_bg_y1), (self.w - 8, hud_bg_y2),
                      self.COLOR_BORDER, 1)

        # Oyuncu HP Bar (daima yesil)
        bar_x = 15
        bar_y = self.hud_y
        bar_h = self.hud_height
        hp_ratio = max(0, hp / max_hp)

        if mode == "savas" and enemy_hp > 0:
            # Savas modunda: iki bar yan yana
            bar_w = (self.w - 50) // 2 - 10

            # Oyuncu HP (sol - yesil)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                          self.COLOR_HP_BAR_BG, -1)
            fill_color = (50, 200, 50)  # Daima yesil
            cv2.rectangle(frame, (bar_x, bar_y),
                          (bar_x + int(bar_w * hp_ratio), bar_y + bar_h),
                          fill_color, -1)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                          (80, 200, 80), 1)

            hp_text = f"SEN: {hp}/{max_hp}"
            (tw, th), _ = cv2.getTextSize(hp_text, self.FONT_BOLD, self.FONT_SCALE_HP, 2)
            cv2.putText(frame, hp_text, (bar_x + (bar_w - tw) // 2, bar_y + (bar_h + th) // 2),
                        self.FONT_BOLD, self.FONT_SCALE_HP, self.COLOR_TEXT_WHITE, 2, cv2.LINE_AA)

            # Dusman HP (sag - kirmizi)
            enemy_bar_x = bar_x + bar_w + 20
            enemy_ratio = max(0, enemy_hp / enemy_max_hp) if enemy_max_hp > 0 else 0

            cv2.rectangle(frame, (enemy_bar_x, bar_y), (enemy_bar_x + bar_w, bar_y + bar_h),
                          self.COLOR_HP_BAR_BG, -1)
            cv2.rectangle(frame, (enemy_bar_x, bar_y),
                          (enemy_bar_x + int(bar_w * enemy_ratio), bar_y + bar_h),
                          (50, 50, 220), -1)  # Kirmizi
            cv2.rectangle(frame, (enemy_bar_x, bar_y), (enemy_bar_x + bar_w, bar_y + bar_h),
                          (80, 80, 220), 1)

            enemy_text = f"DUSMAN: {enemy_hp}/{enemy_max_hp}"
            (tw2, th2), _ = cv2.getTextSize(enemy_text, self.FONT_BOLD, self.FONT_SCALE_HP, 2)
            cv2.putText(frame, enemy_text,
                        (enemy_bar_x + (bar_w - tw2) // 2, bar_y + (bar_h + th2) // 2),
                        self.FONT_BOLD, self.FONT_SCALE_HP, self.COLOR_TEXT_WHITE, 2, cv2.LINE_AA)
        else:
            # Normal mod: tek oyuncu HP + altin/tur
            bar_w = 260

            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                          self.COLOR_HP_BAR_BG, -1)
            fill_color = (50, 200, 50)  # Daima yesil
            cv2.rectangle(frame, (bar_x, bar_y),
                          (bar_x + int(bar_w * hp_ratio), bar_y + bar_h),
                          fill_color, -1)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                          (80, 200, 80), 1)

            hp_text = f"HP: {hp}/{max_hp}"
            (tw, th), _ = cv2.getTextSize(hp_text, self.FONT_BOLD, self.FONT_SCALE_HP, 2)
            text_x = bar_x + (bar_w - tw) // 2
            text_y = bar_y + (bar_h + th) // 2
            cv2.putText(frame, hp_text, (text_x, text_y), self.FONT_BOLD,
                        self.FONT_SCALE_HP, self.COLOR_TEXT_WHITE, 2, cv2.LINE_AA)

            # Altin ve Tur bilgisi
            info_x = bar_x + bar_w + 15
            gold_text = f"Altin: {gold}"
            turn_text = f"Tur: {turn}"
            cv2.putText(frame, gold_text, (info_x, bar_y + bar_h // 2 + 2),
                        self.FONT_BOLD, self.FONT_SCALE_HUD, self.COLOR_TEXT_GOLD,
                        self.FONT_THICKNESS, cv2.LINE_AA)
            (gw, _), _ = cv2.getTextSize(gold_text, self.FONT_BOLD, self.FONT_SCALE_HUD, self.FONT_THICKNESS)
            cv2.putText(frame, turn_text, (info_x + gw + 20, bar_y + bar_h // 2 + 2),
                        self.FONT, self.FONT_SCALE_HUD, self.COLOR_TEXT_WHITE,
                        self.FONT_THICKNESS, cv2.LINE_AA)

        return frame

    def draw_loading(self, frame: np.ndarray) -> np.ndarray:
        """AI bekleme ekrani cizer."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        text = "Dungeon Master dusunuyor..."
        (tw, th), _ = cv2.getTextSize(text, self.FONT_BOLD,
                                       self.FONT_SCALE_LOADING, 2)
        x = (self.w - tw) // 2
        y = (self.h + th) // 2
        cv2.putText(frame, text, (x, y), self.FONT_BOLD,
                    self.FONT_SCALE_LOADING, self.COLOR_TEXT_GOLD, 2, cv2.LINE_AA)
        return frame

    def draw_enemy_attack(self, frame: np.ndarray, progress: float,
                          damage: int, enemy_name: str = "Dusman",
                          blocked: bool = False) -> np.ndarray:
        """Dusman saldiri animasyon ekrani (3 saniye). blocked=True ise savunma basarili."""
        if blocked:
            # SAVUNMA BASARILI - mavi/yesil kalkan efekti
            pulse = abs(((progress * 6) % 2) - 1)
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (self.w, self.h),
                          (int(120 + 40 * pulse), int(80 + 30 * pulse), 20), -1)
            frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)

            # Mavi kenar
            border = int(6 + 10 * pulse)
            cv2.rectangle(frame, (0, 0), (self.w, self.h), (255, 180, 50), border)

            # Kalkan dairesi
            radius = int(self.w * 0.05 + progress * self.w * 0.25)
            cv2.circle(frame, (self.w // 2, self.h // 2), radius, (255, 200, 80), 8)

            # Baslik
            title = "MUKEMMEL SAVUNMA!"
            (tw, _), _ = cv2.getTextSize(title, self.FONT_BOLD, 1.3, 3)
            cv2.putText(frame, title, ((self.w - tw) // 2, self.h // 2 - 60),
                        self.FONT_BOLD, 1.3, (50, 255, 100), 3, cv2.LINE_AA)

            # Engellendi bilgisi
            block_text = "Saldiri Engellendi!"
            (tw2, _), _ = cv2.getTextSize(block_text, self.FONT_BOLD, 1.2, 2)
            cv2.putText(frame, block_text, ((self.w - tw2) // 2, self.h // 2 + 20),
                        self.FONT_BOLD, 1.2, (255, 255, 255), 2, cv2.LINE_AA)
        else:
            # Normal dusman saldirisi - kirmizi overlay
            pulse = abs(((progress * 6) % 2) - 1)
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (self.w, self.h),
                          (0, 0, int(60 + 80 * pulse)), -1)
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

            # Kirmizi kenar parlamasi
            border = int(8 + 12 * pulse)
            cv2.rectangle(frame, (0, 0), (self.w, self.h), (0, 0, 220), border)

            # Baslik (asagiya cekildi: h/2-20)
            title = f"{sanitize_text(enemy_name)} SALDIRIYOR!"
            (tw, _), _ = cv2.getTextSize(title, self.FONT_BOLD, 1.3, 3)
            cv2.putText(frame, title, ((self.w - tw) // 2, self.h // 2 - 20),
                        self.FONT_BOLD, 1.3, (50, 50, 255), 3, cv2.LINE_AA)

            # Hasar bilgisi (asagiya cekildi: h/2+60)
            dmg_text = f"-{damage} HP"
            (tw2, _), _ = cv2.getTextSize(dmg_text, self.FONT_BOLD, 1.8, 3)
            y_offset = int(20 * (1 - progress))
            cv2.putText(frame, dmg_text, ((self.w - tw2) // 2, self.h // 2 + 60 + y_offset),
                        self.FONT_BOLD, 1.8, (0, 0, 255), 3, cv2.LINE_AA)

        # Progress bar (zamanlayici - asagiya cekildi: h/2+120)
        bar_x, bar_y = 60, self.h // 2 + 120
        bar_w, bar_h = self.w - 120, 12
        fill_w = int(bar_w * progress)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                      (40, 40, 40), -1)
        bar_color = (255, 180, 50) if blocked else (50, 50, 220)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h),
                      bar_color, -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                      (120, 120, 120), 1)

        # Alt bilgi (asagiya cekildi: h/2+160)
        hint = "Savunma basarili!" if blocked else "Hazirlan! Sira sana gelecek..."
        (tw3, _), _ = cv2.getTextSize(hint, self.FONT, 0.7, 1)
        cv2.putText(frame, hint, ((self.w - tw3) // 2, self.h // 2 + 160),
                    self.FONT, 0.7, (180, 180, 180), 1, cv2.LINE_AA)

        return frame

    def draw_critical_hit(self, frame: np.ndarray, damage: int) -> np.ndarray:
        """Kritik vurus animasyonu icin overlay."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (0, 100, 255), -1)
        frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
        title = "KRITIK VURUS!"
        (tw, _), _ = cv2.getTextSize(title, self.FONT_BOLD, 1.5, 3)
        cv2.putText(frame, title, ((self.w - tw) // 2, self.h // 2 - 30),
                    self.FONT_BOLD, 1.5, (0, 0, 255), 3, cv2.LINE_AA)
        dmg_text = f"-{damage} HP!"
        (tw2, _), _ = cv2.getTextSize(dmg_text, self.FONT_BOLD, 2.0, 3)
        cv2.putText(frame, dmg_text, ((self.w - tw2) // 2, self.h // 2 + 40),
                    self.FONT_BOLD, 2.0, (50, 215, 255), 3, cv2.LINE_AA)
        return frame

    def draw_game_over(self, frame: np.ndarray, reason: str) -> np.ndarray:
        """Oyun sonu ekrani cizer."""
        reason = sanitize_text(reason)

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (0, 0, 30), -1)
        frame = cv2.addWeighted(overlay, 0.8, frame, 0.2, 0)

        # OYUN BITTI
        title = "OYUN BITTI"
        (tw, _), _ = cv2.getTextSize(title, self.FONT_BOLD,
                                      self.FONT_SCALE_GAMEOVER, 3)
        cv2.putText(frame, title, ((self.w - tw) // 2, self.h // 2 - 40),
                    self.FONT_BOLD, self.FONT_SCALE_GAMEOVER, (0, 0, 255), 3,
                    cv2.LINE_AA)

        # Sebep
        (tw2, _), _ = cv2.getTextSize(reason, self.FONT,
                                       self.FONT_SCALE_STORY, 2)
        cv2.putText(frame, reason, ((self.w - tw2) // 2, self.h // 2 + 20),
                    self.FONT, self.FONT_SCALE_STORY, self.COLOR_TEXT_WHITE,
                    2, cv2.LINE_AA)

        # Talimatlar
        hint = "'R' = Yeniden Baslat  |  'Q' = Cikis"
        (tw3, _), _ = cv2.getTextSize(hint, self.FONT,
                                       self.FONT_SCALE_BTN, 2)
        cv2.putText(frame, hint, ((self.w - tw3) // 2, self.h // 2 + 70),
                    self.FONT, self.FONT_SCALE_BTN, self.COLOR_TEXT_GOLD,
                    2, cv2.LINE_AA)

        return frame

    def draw_finger_cursor(self, frame: np.ndarray, pos: Tuple[int, int]) -> np.ndarray:
        """Parmak pozisyonunda buyuk bir cursor cizer."""
        cv2.circle(frame, pos, 18, self.COLOR_PROGRESS_BAR, 3)
        cv2.circle(frame, pos, 6, self.COLOR_TEXT_WHITE, -1)
        return frame

    def get_quadrant_from_button(self, x: int, y: int,
                                  active_options: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Koordinatin hangi buton bolgesinde oldugunu dondurur."""
        regions = self._active_button_regions
        for qid, (x1, y1, x2, y2) in regions.items():
            # Bos secenekleri atla
            if active_options and not active_options.get(qid, ""):
                continue
            if x1 <= x <= x2 and y1 <= y <= y2:
                return qid
        return None

    def _compute_button_layout(self, options: Dict[str, str]) -> Dict[str, tuple]:
        """Aktif secenek sayisina gore buton pozisyonlarini hesaplar."""
        active_keys = [k for k in ["sol_ust", "sag_ust", "sol_alt", "sag_alt"]
                       if options.get(k, "")]
        count = len(active_keys)

        margin = self._layout_margin
        gap = self._layout_gap
        btn_area_top = self._btn_area_top
        btn_area_bottom = self._btn_area_bottom
        available_w = self.w - margin * 2 - gap
        available_h = btn_area_bottom - btn_area_top

        if count <= 2:
            # 2 buton: tam yukseklik, daha buyuk
            btn_w = available_w // 2
            btn_h = available_h
            top_y = btn_area_top
            left_x = margin
            right_x = margin + btn_w + gap
            return {
                "sol_ust": (left_x, top_y, left_x + btn_w, top_y + btn_h),
                "sag_ust": (right_x, top_y, right_x + btn_w, top_y + btn_h),
                "sol_alt": (0, 0, 0, 0),
                "sag_alt": (0, 0, 0, 0),
            }
        elif count == 3:
            # 3 buton: 2 ust + 1 ortada alt
            btn_w = available_w // 2
            btn_h = (available_h - gap) // 2
            left_x = margin
            right_x = margin + btn_w + gap
            top_y = btn_area_top
            bottom_y = btn_area_top + btn_h + gap

            # Alt buton ortada
            center_w = int(btn_w * 1.3)
            center_x = (self.w - center_w) // 2

            return {
                "sol_ust": (left_x, top_y, left_x + btn_w, top_y + btn_h),
                "sag_ust": (right_x, top_y, right_x + btn_w, top_y + btn_h),
                "sol_alt": (center_x, bottom_y, center_x + center_w, bottom_y + btn_h),
                "sag_alt": (0, 0, 0, 0),
            }
        else:
            # 4 buton: standart 2x2
            return dict(self.button_regions)

    # ------------------------------------------------------------------ #
    #  OZEL (PRIVATE) METODLAR                                            #
    # ------------------------------------------------------------------ #

    def _wrap_text(self, text: str, font: int, scale: float,
                   thickness: int, max_width: int) -> list:
        """Metni max_width'e gore satirlara boler."""
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            (tw, _), _ = cv2.getTextSize(test, font, scale, thickness)
            if tw > max_width and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    def _draw_button_text(self, frame: np.ndarray, text: str,
                          x: int, y: int, max_w: int, btn_h: int) -> None:
        """Buton icine sigacak sekilde metin cizer (ortali)."""
        lines = self._wrap_text(text, self.FONT, self.FONT_SCALE_BTN,
                                self.FONT_THICKNESS_THIN, max_w)

        line_height = 30
        total_h = len(lines) * line_height
        start_y = y + (btn_h - total_h) // 2 + 20

        for i, line in enumerate(lines):
            # Yatay ortalama
            (tw, _), _ = cv2.getTextSize(line, self.FONT,
                                          self.FONT_SCALE_BTN,
                                          self.FONT_THICKNESS_THIN)
            line_x = x + (max_w - tw) // 2
            cv2.putText(frame, line, (line_x, start_y + i * line_height),
                        self.FONT, self.FONT_SCALE_BTN,
                        self.COLOR_TEXT_WHITE, self.FONT_THICKNESS_THIN,
                        cv2.LINE_AA)

    # ------------------------------------------------------------------ #
    #  ENVANTER EKRANI                                                     #
    # ------------------------------------------------------------------ #

    ITEMS_PER_PAGE = 6
    COLOR_EQUIPPED = (50, 220, 120)         # Yesil
    COLOR_UNEQUIPPED = (140, 140, 140)      # Gri
    COLOR_ITEM_BG = (40, 40, 50)
    COLOR_ITEM_HOVER = (60, 80, 120)
    COLOR_DEVAM_BG = (50, 130, 80)
    COLOR_DEVAM_HOVER = (70, 180, 100)

    def draw_inventory(self, frame: np.ndarray,
                       all_weapons: list,
                       equipped_items: list,
                       all_items: list,
                       weapon_stats_fn,
                       page: int = 0,
                       hovered_idx: int = -1,
                       hovered_devam: bool = False,
                       dwell_progress: float = 0.0) -> Tuple[np.ndarray, dict]:
        """
        Envanter ekranini cizer.

        Returns:
            (frame, regions) - regions dict:
                'items': [(item_name, (x1,y1,x2,y2)), ...]
                'devam': (x1,y1,x2,y2) or None
                'prev': (x1,y1,x2,y2) or None
                'next': (x1,y1,x2,y2) or None
        """
        # Koyu overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (10, 10, 15), -1)
        frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)

        regions = {'items': [], 'devam': None, 'prev': None, 'next': None}

        margin = 30
        top_y = 20

        # ---- BASLIK ----
        equip_count = len(equipped_items)
        title = "ENVANTER"
        subtitle = sanitize_text(f"Savas icin silah sec ({equip_count}/4)")
        (tw, _), _ = cv2.getTextSize(title, self.FONT_BOLD, 1.3, 3)
        cv2.putText(frame, title, ((self.w - tw) // 2, top_y + 35),
                    self.FONT_BOLD, 1.3, self.COLOR_TITLE, 3, cv2.LINE_AA)
        (sw, _), _ = cv2.getTextSize(subtitle, self.FONT, 0.7, 2)
        cv2.putText(frame, subtitle, ((self.w - sw) // 2, top_y + 65),
                    self.FONT, 0.7, self.COLOR_TEXT_GOLD, 2, cv2.LINE_AA)

        # ---- Yardimci esya sayisi ----
        non_weapon_count = len([i for i in all_items if i not in all_weapons])
        if non_weapon_count > 0:
            nw_text = sanitize_text(f"Diger esyalar: {non_weapon_count}")
            cv2.putText(frame, nw_text, (margin, top_y + 90),
                        self.FONT, 0.5, self.COLOR_LABEL, 1, cv2.LINE_AA)

        # ---- SAYFALAMA ----
        total_weapons = len(all_weapons)
        total_pages = max(1, (total_weapons + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)
        page = min(page, total_pages - 1)
        start_idx = page * self.ITEMS_PER_PAGE
        end_idx = min(start_idx + self.ITEMS_PER_PAGE, total_weapons)
        page_weapons = all_weapons[start_idx:end_idx]

        # ---- ITEM SATIRLARI ----
        item_area_top = top_y + 105
        item_h = 62
        item_gap = 8
        item_x1 = margin
        item_x2 = self.w - margin

        for i, weapon in enumerate(page_weapons):
            global_idx = start_idx + i
            y1 = item_area_top + i * (item_h + item_gap)
            y2 = y1 + item_h

            is_equipped = weapon in equipped_items
            is_hovered = (hovered_idx == i)

            # Arka plan
            if is_hovered:
                bg_color = self.COLOR_ITEM_HOVER
            else:
                bg_color = self.COLOR_ITEM_BG

            overlay2 = frame.copy()
            cv2.rectangle(overlay2, (item_x1, y1), (item_x2, y2), bg_color, -1)
            frame = cv2.addWeighted(overlay2, 0.7, frame, 0.3, 0)

            # Cerceve (equipped ise renkli)
            border_c = self.COLOR_EQUIPPED if is_equipped else (80, 80, 80)
            thick = 2 if is_equipped else 1
            cv2.rectangle(frame, (item_x1, y1), (item_x2, y2), border_c, thick)

            # Equip ikonu
            icon_x = item_x1 + 15
            icon_y = y1 + item_h // 2
            if is_equipped:
                # Dolu yildiz
                cv2.putText(frame, "[E]", (icon_x, icon_y + 8),
                            self.FONT_BOLD, 0.65, self.COLOR_EQUIPPED, 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "[ ]", (icon_x, icon_y + 8),
                            self.FONT, 0.6, self.COLOR_UNEQUIPPED, 1, cv2.LINE_AA)

            # Silah adi
            weapon_text = sanitize_text(weapon)
            cv2.putText(frame, weapon_text, (icon_x + 55, icon_y + 5),
                        self.FONT, 0.7, self.COLOR_TEXT_WHITE, 2, cv2.LINE_AA)

            # Stat bilgisi (sag tarafa)
            stats = weapon_stats_fn(weapon)
            bonus = stats.get("bonus", 0)
            wtype = stats.get("type", "fiziksel")
            type_short = "BYS" if wtype == "buyusel" else "FZK"
            stat_text = f"+{bonus} {type_short}"
            (stw, _), _ = cv2.getTextSize(stat_text, self.FONT, 0.55, 1)
            stat_color = (180, 140, 255) if wtype == "buyusel" else (255, 180, 100)
            cv2.putText(frame, stat_text, (item_x2 - stw - 15, icon_y + 5),
                        self.FONT, 0.55, stat_color, 1, cv2.LINE_AA)

            # Dwell progress (hover + dwell durumunda)
            if is_hovered and 0 < dwell_progress < 1.0:
                bar_y = y2 - 5
                bar_w = int((item_x2 - item_x1 - 10) * dwell_progress)
                cv2.rectangle(frame, (item_x1 + 5, bar_y),
                              (item_x1 + 5 + bar_w, bar_y + 4),
                              self.COLOR_PROGRESS_BAR, -1)

            # Region kaydet
            regions['items'].append((weapon, (item_x1, y1, item_x2, y2)))

        # ---- SAYFA NAVIGASYONU ----
        nav_y = item_area_top + self.ITEMS_PER_PAGE * (item_h + item_gap) + 5
        page_text = f"Sayfa {page + 1}/{total_pages}"
        (ptw, _), _ = cv2.getTextSize(page_text, self.FONT, 0.6, 1)
        cv2.putText(frame, page_text, ((self.w - ptw) // 2, nav_y + 20),
                    self.FONT, 0.6, self.COLOR_LABEL, 1, cv2.LINE_AA)

        if total_pages > 1:
            # Onceki butonu
            if page > 0:
                prev_x1, prev_x2 = margin, margin + 120
                prev_y1, prev_y2 = nav_y, nav_y + 35
                overlay3 = frame.copy()
                cv2.rectangle(overlay3, (prev_x1, prev_y1), (prev_x2, prev_y2),
                              (60, 60, 80), -1)
                frame = cv2.addWeighted(overlay3, 0.6, frame, 0.4, 0)
                cv2.rectangle(frame, (prev_x1, prev_y1), (prev_x2, prev_y2),
                              self.COLOR_BORDER, 1)
                cv2.putText(frame, "< Onceki", (prev_x1 + 10, prev_y1 + 24),
                            self.FONT, 0.55, self.COLOR_TEXT_WHITE, 1, cv2.LINE_AA)
                regions['prev'] = (prev_x1, prev_y1, prev_x2, prev_y2)

            # Sonraki butonu
            if page < total_pages - 1:
                next_x2 = self.w - margin
                next_x1 = next_x2 - 120
                next_y1, next_y2 = nav_y, nav_y + 35
                overlay4 = frame.copy()
                cv2.rectangle(overlay4, (next_x1, next_y1), (next_x2, next_y2),
                              (60, 60, 80), -1)
                frame = cv2.addWeighted(overlay4, 0.6, frame, 0.4, 0)
                cv2.rectangle(frame, (next_x1, next_y1), (next_x2, next_y2),
                              self.COLOR_BORDER, 1)
                cv2.putText(frame, "Sonraki >", (next_x1 + 10, next_y1 + 24),
                            self.FONT, 0.55, self.COLOR_TEXT_WHITE, 1, cv2.LINE_AA)
                regions['next'] = (next_x1, next_y1, next_x2, next_y2)

        # ---- DEVAM ET BUTONU ----
        devam_w = 250
        devam_h = 50
        devam_x1 = (self.w - devam_w) // 2
        devam_x2 = devam_x1 + devam_w
        devam_y1 = self.h - 70
        devam_y2 = devam_y1 + devam_h

        dv_color = self.COLOR_DEVAM_HOVER if hovered_devam else self.COLOR_DEVAM_BG
        overlay5 = frame.copy()
        cv2.rectangle(overlay5, (devam_x1, devam_y1), (devam_x2, devam_y2),
                      dv_color, -1)
        frame = cv2.addWeighted(overlay5, 0.8, frame, 0.2, 0)
        dv_border = (100, 255, 150) if hovered_devam else (80, 160, 100)
        cv2.rectangle(frame, (devam_x1, devam_y1), (devam_x2, devam_y2),
                      dv_border, 2)

        devam_text = "DEVAM ET"
        (dtw, _), _ = cv2.getTextSize(devam_text, self.FONT_BOLD, 0.85, 2)
        cv2.putText(frame, devam_text,
                    ((self.w - dtw) // 2, devam_y1 + 33),
                    self.FONT_BOLD, 0.85, self.COLOR_TEXT_WHITE, 2, cv2.LINE_AA)

        # Dwell progress (devam butonu)
        if hovered_devam and 0 < dwell_progress < 1.0:
            bar_w = int(devam_w * dwell_progress)
            cv2.rectangle(frame, (devam_x1, devam_y2 - 5),
                          (devam_x1 + bar_w, devam_y2),
                          self.COLOR_PROGRESS_BAR, -1)

        regions['devam'] = (devam_x1, devam_y1, devam_x2, devam_y2)

        return frame, regions
