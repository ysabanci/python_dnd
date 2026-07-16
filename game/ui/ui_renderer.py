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
    FONT_SCALE_STORY = 0.9
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

        # Hikaye alani (ust %45)
        self.story_top = 55
        self.story_bottom = int(self.h * 0.45)

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
        is_error = story.startswith("[HATA]")

        if is_error:
            title = "-- HATA --"
            title_color = (60, 60, 255)  # Kirmizi
        elif mode == "baslangic":
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
        line_height = 36
        lines = self._wrap_text(story, self.FONT, self.FONT_SCALE_STORY,
                                self.FONT_THICKNESS_THIN, max_width)

        # Arka plan kutusu
        box_top = self.story_top - 5
        box_h = len(lines) * line_height + 20
        box_bottom = min(box_top + box_h, self.story_bottom)

        overlay = frame.copy()
        box_bg = (20, 15, 30) if is_error else self.COLOR_BG_OVERLAY
        cv2.rectangle(overlay, (10, box_top), (self.w - 10, box_bottom),
                      box_bg, -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        border_c = (60, 60, 220) if is_error else self.COLOR_BORDER
        cv2.rectangle(frame, (10, box_top), (self.w - 10, box_bottom),
                      border_c, 1)

        # Metni ciz (hata ise kirmizi)
        text_color = (80, 80, 255) if is_error else self.COLOR_TEXT_STORY
        y = self.story_top + 18
        for line in lines:
            if y > box_bottom - 5:
                break
            cv2.putText(frame, line, (25, y), self.FONT,
                        self.FONT_SCALE_STORY, text_color,
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
                       dwell_progress: float = 0.0,
                       total_stats: dict = None,
                       stat_names: dict = None,
                       shop_items: list = None,
                       shop_roll_cost: int = 0,
                       gold: int = 0,
                       hovered_shop: int = -1,
                       hovered_roll: bool = False,
                       hovered_prev: bool = False,
                       hovered_next: bool = False) -> Tuple[np.ndarray, dict]:
        """Envanter ekranini cizer (istatistik panelli + shop)."""
        if total_stats is None:
            total_stats = {}
        if stat_names is None:
            stat_names = {"STR": "Guc", "DEX": "Cevik", "INT": "Zeka",
                          "DEF": "Savun", "LUCK": "Sans"}
        if shop_items is None:
            shop_items = []

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (10, 10, 15), -1)
        frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)

        regions = {'items': [], 'devam': None, 'prev': None, 'next': None,
                   'shop': [], 'roll': None}
        margin = 20
        top_y = 10
        ix1, ix2 = margin, self.w - margin

        # ---- DEVAM ET (SAG UST) ----
        ddw, ddh = 180, 50
        ddx1 = self.w - ddw - margin
        ddx2, ddy1, ddy2 = ddx1+ddw, top_y+5, top_y+5+ddh
        dvc = self.COLOR_DEVAM_HOVER if hovered_devam else self.COLOR_DEVAM_BG
        ov = frame.copy()
        cv2.rectangle(ov, (ddx1,ddy1), (ddx2,ddy2), dvc, -1)
        frame = cv2.addWeighted(ov, 0.8, frame, 0.2, 0)
        dvb = (100,255,150) if hovered_devam else (80,160,100)
        cv2.rectangle(frame, (ddx1,ddy1), (ddx2,ddy2), dvb, 2)
        dtxt = "DEVAM ET"
        (dtw,dth2),_ = cv2.getTextSize(dtxt, self.FONT_BOLD, 0.85, 2)
        cv2.putText(frame, dtxt, (ddx1+(ddw-dtw)//2, ddy1+(ddh+dth2)//2),
                    self.FONT_BOLD, 0.85, self.COLOR_TEXT_WHITE, 2, cv2.LINE_AA)
        if hovered_devam and 0 < dwell_progress < 1.0:
            bw = int(ddw * dwell_progress)
            cv2.rectangle(frame, (ddx1,ddy2-4), (ddx1+bw,ddy2), self.COLOR_PROGRESS_BAR, -1)
        regions['devam'] = (ddx1, ddy1, ddx2, ddy2)

        # ---- BASLIK ----
        ec = len(equipped_items)
        cv2.putText(frame, "ENVANTER", (margin, top_y+30),
                    self.FONT_BOLD, 1.1, self.COLOR_TITLE, 2, cv2.LINE_AA)
        sub = sanitize_text(f"Silah sec ({ec}/4) | Altin: {gold}")
        cv2.putText(frame, sub, (margin, top_y+52),
                    self.FONT, 0.55, self.COLOR_TEXT_GOLD, 1, cv2.LINE_AA)

        # ---- STAT PANELI ----
        spy = top_y + 60
        sph = 38
        if total_stats:
            ov2 = frame.copy()
            cv2.rectangle(ov2, (margin,spy), (self.w-margin,spy+sph), (25,25,35), -1)
            frame = cv2.addWeighted(ov2, 0.7, frame, 0.3, 0)
            cv2.rectangle(frame, (margin,spy), (self.w-margin,spy+sph), (60,60,80), 1)
            sks = ["STR","DEX","INT","DEF","LUCK"]
            scs = {"STR":(100,100,255),"DEX":(100,255,100),"INT":(255,180,80),
                   "DEF":(200,200,100),"LUCK":(150,130,255)}
            aww = self.w - margin*2 - 10
            sww = aww // len(sks)
            for i, sk in enumerate(sks):
                val = total_stats.get(sk, 10)
                nm = stat_names.get(sk, sk)
                cl = scs.get(sk, self.COLOR_TEXT_WHITE)
                sx = margin + 5 + i * sww
                sy = spy + 15
                cv2.putText(frame, nm, (sx,sy), self.FONT, 0.4, self.COLOR_LABEL, 1, cv2.LINE_AA)
                vt = str(val)
                (vw,_),_ = cv2.getTextSize(vt, self.FONT_BOLD, 0.6, 2)
                cv2.putText(frame, vt, (sx,sy+18), self.FONT_BOLD, 0.6, cl, 2, cv2.LINE_AA)
                bx = sx+vw+5
                by = sy+9
                bmw = max(10, sww-vw-18)
                bf = min(int(bmw*val/200), bmw)
                cv2.rectangle(frame, (bx,by), (bx+bmw,by+6), (30,30,40), -1)
                cv2.rectangle(frame, (bx,by), (bx+bf,by+6), cl, -1)

        # ---- ITEMS ----
        tw = len(all_weapons)
        ipp = 5
        tp = max(1, (tw+ipp-1)//ipp)
        page = min(page, tp-1)
        si2 = page*ipp
        ei = min(si2+ipp, tw)
        pw = all_weapons[si2:ei]

        iat = spy + sph + 8
        ih, ig = 46, 3

        for i, weapon in enumerate(pw):
            y1 = iat + i*(ih+ig)
            y2 = y1+ih
            is_eq = weapon in equipped_items
            is_hov = (hovered_idx == i)
            bg = self.COLOR_ITEM_HOVER if is_hov else self.COLOR_ITEM_BG
            ov3 = frame.copy()
            cv2.rectangle(ov3, (ix1,y1), (ix2,y2), bg, -1)
            frame = cv2.addWeighted(ov3, 0.7, frame, 0.3, 0)
            bc = self.COLOR_EQUIPPED if is_eq else (80,80,80)
            cv2.rectangle(frame, (ix1,y1), (ix2,y2), bc, 2 if is_eq else 1)
            icx = ix1+12
            icy = y1+ih//2
            if is_eq:
                cv2.putText(frame, "[E]", (icx,icy+6), self.FONT_BOLD, 0.5, self.COLOR_EQUIPPED, 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "[ ]", (icx,icy+6), self.FONT, 0.45, self.COLOR_UNEQUIPPED, 1, cv2.LINE_AA)
            wt = sanitize_text(weapon)
            cv2.putText(frame, wt, (icx+42,icy+2), self.FONT, 0.5, self.COLOR_TEXT_WHITE, 1, cv2.LINE_AA)
            stats = weapon_stats_fn(weapon)
            bonus = stats.get("bonus", 0)
            wtype = stats.get("type", "fiziksel")
            w_stats = stats.get("stats", {})
            ts = "BYS" if wtype == "buyusel" else "FZK"
            parts = []
            for sk, sv in w_stats.items():
                if sv > 0: parts.append(f"+{sv}{sk}")
                elif sv < 0: parts.append(f"{sv}{sk}")
            info = f"+{bonus}{ts} {' '.join(parts)}"
            sc = (180,140,255) if wtype == "buyusel" else (255,180,100)
            (iw,_),_ = cv2.getTextSize(info, self.FONT, 0.38, 1)
            cv2.putText(frame, info, (ix2-iw-8,icy+2), self.FONT, 0.38, sc, 1, cv2.LINE_AA)
            if is_hov and 0 < dwell_progress < 1.0:
                bww = int((ix2-ix1-8)*dwell_progress)
                cv2.rectangle(frame, (ix1+4,y2-3), (ix1+4+bww,y2), self.COLOR_PROGRESS_BAR, -1)
            regions['items'].append((weapon, (ix1, y1, ix2, y2)))

        # ---- SAYFA NAV ----
        nav_y = iat + ipp*(ih+ig)
        if tp > 1:
            pgt = f"{page+1}/{tp}"
            (pgw,_),_ = cv2.getTextSize(pgt, self.FONT, 0.45, 1)
            cv2.putText(frame, pgt, ((self.w-pgw)//2, nav_y+16), self.FONT, 0.45, self.COLOR_LABEL, 1, cv2.LINE_AA)
            if page > 0:
                px1,px2,py1,py2 = margin,margin+100,nav_y,nav_y+26
                pc = (80,100,140) if hovered_prev else (50,50,70)
                ov4 = frame.copy()
                cv2.rectangle(ov4, (px1,py1), (px2,py2), pc, -1)
                frame = cv2.addWeighted(ov4, 0.7, frame, 0.3, 0)
                cv2.rectangle(frame, (px1,py1), (px2,py2), self.COLOR_BORDER, 1)
                cv2.putText(frame, "< Onceki", (px1+6,py1+18), self.FONT, 0.45, self.COLOR_TEXT_WHITE, 1, cv2.LINE_AA)
                regions['prev'] = (px1,py1,px2,py2)
                if hovered_prev and 0 < dwell_progress < 1.0:
                    bww = int(100*dwell_progress)
                    cv2.rectangle(frame, (px1,py2-3), (px1+bww,py2), self.COLOR_PROGRESS_BAR, -1)
            if page < tp-1:
                nx2 = self.w-margin
                nx1,ny1,ny2 = nx2-100,nav_y,nav_y+26
                nc = (80,100,140) if hovered_next else (50,50,70)
                ov5 = frame.copy()
                cv2.rectangle(ov5, (nx1,ny1), (nx2,ny2), nc, -1)
                frame = cv2.addWeighted(ov5, 0.7, frame, 0.3, 0)
                cv2.rectangle(frame, (nx1,ny1), (nx2,ny2), self.COLOR_BORDER, 1)
                cv2.putText(frame, "Sonraki >", (nx1+6,ny1+18), self.FONT, 0.45, self.COLOR_TEXT_WHITE, 1, cv2.LINE_AA)
                regions['next'] = (nx1,ny1,nx2,ny2)
                if hovered_next and 0 < dwell_progress < 1.0:
                    bww = int(100*dwell_progress)
                    cv2.rectangle(frame, (nx1,ny2-3), (nx1+bww,ny2), self.COLOR_PROGRESS_BAR, -1)
            nav_y += 30
        else:
            nav_y += 2

        # ---- SHOP ----
        if shop_items:
            shop_y = nav_y + 2
            cv2.putText(frame, "DUKKAN", (margin,shop_y+12), self.FONT_BOLD, 0.55, (50,200,255), 1, cv2.LINE_AA)
            shop_y += 18
            # Yan yana 3 kutu
            shop_h = 52
            gap = 6
            total_w = ix2 - ix1
            col_w = (total_w - gap * (len(shop_items) - 1)) // max(len(shop_items), 1)
            for si, sit in enumerate(shop_items):
                sx1 = ix1 + si * (col_w + gap)
                sx2 = sx1 + col_w
                sy1 = shop_y
                sy2 = sy1 + shop_h
                is_sh = (hovered_shop == si)
                ca = gold >= sit["cost"]
                sbg = (60,80,50) if (is_sh and ca) else (35,35,45)
                ov6 = frame.copy()
                cv2.rectangle(ov6, (sx1,sy1), (sx2,sy2), sbg, -1)
                frame = cv2.addWeighted(ov6, 0.7, frame, 0.3, 0)
                sbc = (80,200,100) if ca else (100,50,50)
                cv2.rectangle(frame, (sx1,sy1), (sx2,sy2), sbc, 1)
                snm = stat_names.get(sit["stat"], sit["stat"])
                scl = {"STR":(100,100,255),"DEX":(100,255,100),"INT":(255,180,80),
                       "DEF":(200,200,100),"LUCK":(150,130,255)}.get(sit["stat"], self.COLOR_TEXT_WHITE)
                stxt = f"+{sit['amount']} {snm}"
                (stw,_),_ = cv2.getTextSize(stxt, self.FONT_BOLD, 0.55, 1)
                cv2.putText(frame, stxt, (sx1+(col_w-stw)//2, sy1+24), self.FONT_BOLD, 0.55, scl, 1, cv2.LINE_AA)
                ctxt = f"{sit['cost']}G"
                ctc = (50,215,255) if ca else (100,100,100)
                (cww,_),_ = cv2.getTextSize(ctxt, self.FONT, 0.45, 1)
                cv2.putText(frame, ctxt, (sx1+(col_w-cww)//2, sy1+43), self.FONT, 0.45, ctc, 1, cv2.LINE_AA)
                if is_sh and 0 < dwell_progress < 1.0:
                    bww = int((sx2-sx1-4)*dwell_progress)
                    cv2.rectangle(frame, (sx1+2,sy2-4), (sx1+2+bww,sy2-1), self.COLOR_PROGRESS_BAR, -1)
                regions['shop'].append((si, (sx1,sy1,sx2,sy2)))
            # Roll butonu (alt kisim, tam genislik)
            ry1 = shop_y + shop_h + 5
            ry2 = ry1 + 32
            cr = gold >= shop_roll_cost
            rbg = (80,60,100) if (hovered_roll and cr) else (40,30,55)
            ov7 = frame.copy()
            cv2.rectangle(ov7, (ix1,ry1), (ix2,ry2), rbg, -1)
            frame = cv2.addWeighted(ov7, 0.7, frame, 0.3, 0)
            rbc = (160,100,255) if cr else (80,50,80)
            cv2.rectangle(frame, (ix1,ry1), (ix2,ry2), rbc, 1)
            rtxt = f"ROLL - Yenile ({shop_roll_cost}G)"
            (rww,_),_ = cv2.getTextSize(rtxt, self.FONT_BOLD, 0.5, 1)
            rc = (200,150,255) if cr else (100,80,120)
            cv2.putText(frame, rtxt, ((self.w-rww)//2,ry1+21), self.FONT_BOLD, 0.5, rc, 1, cv2.LINE_AA)
            if hovered_roll and 0 < dwell_progress < 1.0:
                bww = int((ix2-ix1-8)*dwell_progress)
                cv2.rectangle(frame, (ix1+4,ry2-3), (ix1+4+bww,ry2), self.COLOR_PROGRESS_BAR, -1)
            regions['roll'] = (ix1,ry1,ix2,ry2)

        return frame, regions
