"""
dice_challenge.py - Zar Atma Mini Oyunu
==========================================
Keşif ve diyalog modlarında beceri kontrolü (skill check) için
d20 zar atma animasyonu ve sonuç ekranı.

Oyuncu el hareketiyle zarı atar, sonuç hikayeyi etkiler.
"""

import time
import random
import math
import cv2
import numpy as np
from typing import Optional, Tuple
from enum import Enum


class DiceState(Enum):
    """Zar challenge durumlari."""
    IDLE = "idle"
    READY = "ready"          # "Yumruk yap veya parmak salla" uyarisi
    ROLLING = "rolling"      # Zar donuyor animasyonu
    RESULT = "result"        # Sonuc gosteriliyor


class DiceChallenge:
    """d20 zar atma mini oyunu."""

    READY_DURATION = 3.0      # Hazirlik suresi (saniye)
    ROLL_DURATION = 2.0       # Zar donme animasyonu suresi
    RESULT_DURATION = 2.5     # Sonuc gosterim suresi

    # Fontlar
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_BOLD = cv2.FONT_HERSHEY_DUPLEX

    def __init__(self, frame_width: int, frame_height: int):
        self.w = frame_width
        self.h = frame_height

        self.state = DiceState.IDLE
        self.start_time: float = 0.0
        self.dice_result: int = 0
        self.action_text: str = ""
        self._challenge_completed: bool = False
        self._rolling_triggered: bool = False

    def start_challenge(self, action_text: str) -> None:
        """Zar atma challenge'ini baslatir."""
        self.state = DiceState.READY
        self.start_time = time.time()
        self.action_text = action_text
        self.dice_result = 0
        self._challenge_completed = False
        self._rolling_triggered = False
        print(f"[>] Zar challenge basladi: {action_text}")

    def update(self, has_gesture: bool = False) -> None:
        """Her frame'de cagirilir."""
        elapsed = time.time() - self.start_time

        if self.state == DiceState.READY:
            # Oyuncu jest yaparsa veya sure dolarsa zarı at
            if has_gesture or elapsed >= self.READY_DURATION:
                self._trigger_roll()

        elif self.state == DiceState.ROLLING:
            if elapsed >= self.ROLL_DURATION:
                # Animasyon bitti -> sonuca gec
                self.state = DiceState.RESULT
                self.start_time = time.time()
                print(f"[>] Zar sonucu: {self.dice_result}")

        elif self.state == DiceState.RESULT:
            if elapsed >= self.RESULT_DURATION:
                self.state = DiceState.IDLE
                self._challenge_completed = True

    def _trigger_roll(self) -> None:
        """Zarı at ve rolling animasyonunu baslat."""
        if self._rolling_triggered:
            return
        self._rolling_triggered = True
        self.dice_result = random.randint(1, 20)
        self.state = DiceState.ROLLING
        self.start_time = time.time()

    def draw(self, frame: np.ndarray) -> np.ndarray:
        """Challenge UI'ini cizer."""

        if self.state == DiceState.READY:
            return self._draw_ready(frame)
        elif self.state == DiceState.ROLLING:
            return self._draw_rolling(frame)
        elif self.state == DiceState.RESULT:
            return self._draw_result(frame)

        return frame

    def _draw_ready(self, frame: np.ndarray) -> np.ndarray:
        """Hazirlik ekrani - 'Zarı at!' mesaji."""
        # Koyu overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        # Baslik
        title = "ZAR ATMA ZAMANI!"
        (tw, _), _ = cv2.getTextSize(title, self.FONT_BOLD, 1.3, 3)
        cv2.putText(frame, title, ((self.w - tw) // 2, self.h // 2 - 100),
                    self.FONT_BOLD, 1.3, (50, 200, 255), 3, cv2.LINE_AA)

        # Hamle bilgisi
        act = f"Hamle: {self.action_text}"
        (aw, _), _ = cv2.getTextSize(act, self.FONT, 0.8, 2)
        cv2.putText(frame, act, ((self.w - aw) // 2, self.h // 2 - 50),
                    self.FONT, 0.8, (200, 200, 200), 2, cv2.LINE_AA)

        # Animasyonlu zar ikonu (titreyen d20)
        now = time.time()
        wobble = int(math.sin(now * 8) * 5)
        self._draw_d20_icon(frame, self.w // 2 + wobble, self.h // 2 + 30,
                            60, (100, 180, 255))

        # Talimat
        elapsed = time.time() - self.start_time
        remaining = max(0, self.READY_DURATION - elapsed)
        hint = f"Yumruk yap veya bekle! ({remaining:.0f}s)"
        (hw, _), _ = cv2.getTextSize(hint, self.FONT, 0.7, 2)
        cv2.putText(frame, hint, ((self.w - hw) // 2, self.h // 2 + 130),
                    self.FONT, 0.7, (150, 255, 150), 2, cv2.LINE_AA)

        return frame

    def _draw_rolling(self, frame: np.ndarray) -> np.ndarray:
        """Zar donme animasyonu."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.8, frame, 0.2, 0)

        elapsed = time.time() - self.start_time
        progress = min(elapsed / self.ROLL_DURATION, 1.0)

        # Yavaslayan zar animasyonu - rastgele sayilar goster
        now = time.time()
        if progress < 0.8:
            # Hizli degisim
            display_num = random.randint(1, 20)
        else:
            # Yavaslama -> gercek sonuca yaklasma
            display_num = self.dice_result

        # Zar kutusu (buyuk)
        cx, cy = self.w // 2, self.h // 2
        # Titreme efekti (yavaslayarak)
        shake = int((1 - progress) * 10)
        sx = random.randint(-shake, shake) if shake > 0 else 0
        sy = random.randint(-shake, shake) if shake > 0 else 0

        self._draw_d20_icon(frame, cx + sx, cy + sy, 80, (80, 160, 255))

        # Sayi
        num_text = str(display_num)
        (nw, nh), _ = cv2.getTextSize(num_text, self.FONT_BOLD, 2.5, 4)
        cv2.putText(frame, num_text,
                    ((self.w - nw) // 2 + sx, (self.h + nh) // 2 + sy),
                    self.FONT_BOLD, 2.5, (255, 255, 255), 4, cv2.LINE_AA)

        # "Zar atiliyor..." yazisi
        roll_text = "Zar atiliyor..."
        (rw, _), _ = cv2.getTextSize(roll_text, self.FONT, 0.8, 2)
        cv2.putText(frame, roll_text, ((self.w - rw) // 2, self.h // 2 + 100),
                    self.FONT, 0.8, (180, 180, 180), 2, cv2.LINE_AA)

        return frame

    def _draw_result(self, frame: np.ndarray) -> np.ndarray:
        """Sonuc ekrani."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

        cx, cy = self.w // 2, self.h // 2

        # Sonuca gore renk ve baslik
        if self.dice_result >= 15:
            color = (50, 255, 100)     # Yesil
            verdict = "MUKEMMEL BASARI!"
        elif self.dice_result >= 10:
            color = (50, 200, 255)     # Turuncu
            verdict = "BASARILI!"
        elif self.dice_result >= 6:
            color = (50, 150, 255)     # Sarı
            verdict = "KISMI BASARI"
        elif self.dice_result == 1:
            color = (50, 50, 255)      # Kırmızı
            verdict = "KRITIK BASARISIZLIK!"
        else:
            color = (80, 80, 255)      # Kırmızı
            verdict = "BASARISIZ!"

        # Baslik
        (tw, _), _ = cv2.getTextSize(verdict, self.FONT_BOLD, 1.3, 3)
        cv2.putText(frame, verdict, ((self.w - tw) // 2, cy - 80),
                    self.FONT_BOLD, 1.3, color, 3, cv2.LINE_AA)

        # Buyuk zar sayisi
        num_text = str(self.dice_result)
        (nw, nh), _ = cv2.getTextSize(num_text, self.FONT_BOLD, 3.5, 5)
        cv2.putText(frame, num_text, ((self.w - nw) // 2, cy + nh // 2 + 10),
                    self.FONT_BOLD, 3.5, color, 5, cv2.LINE_AA)

        # d20 ikonu (kucuk, solda)
        self._draw_d20_icon(frame, cx - 120, cy + 10, 30, color)

        # Hamle bilgisi
        act = f"Hamle: {self.action_text}"
        (aw, _), _ = cv2.getTextSize(act, self.FONT, 0.7, 2)
        cv2.putText(frame, act, ((self.w - aw) // 2, cy + 80),
                    self.FONT, 0.7, (180, 180, 180), 2, cv2.LINE_AA)

        return frame

    def _draw_d20_icon(self, frame: np.ndarray, cx: int, cy: int,
                       radius: int, color: tuple) -> None:
        """d20 (icosahedron) sekli cizer - basitleştirilmiş altigen."""
        pts = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 6
            px = int(cx + radius * math.cos(angle))
            py = int(cy + radius * math.sin(angle))
            pts.append([px, py])
        pts_arr = np.array(pts, np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts_arr], True, color, 2, cv2.LINE_AA)
        # Ic cizgiler
        cv2.line(frame, tuple(pts[0]), tuple(pts[3]), color, 1, cv2.LINE_AA)
        cv2.line(frame, tuple(pts[1]), tuple(pts[4]), color, 1, cv2.LINE_AA)
        cv2.line(frame, tuple(pts[2]), tuple(pts[5]), color, 1, cv2.LINE_AA)

    def is_done(self) -> bool:
        """Challenge tamamlandi mi?"""
        return self._challenge_completed

    def get_result(self) -> Tuple[int, str]:
        """Sonuc dondurur: (zar_sonucu, action_text)."""
        return self.dice_result, self.action_text

    def reset(self) -> None:
        """Challenge'i sifirlar."""
        self.state = DiceState.IDLE
        self.dice_result = 0
        self.action_text = ""
        self._challenge_completed = False
        self._rolling_triggered = False
