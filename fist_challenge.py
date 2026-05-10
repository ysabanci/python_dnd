"""
fist_challenge.py - Yumruk Bulmaca Oyunu
==========================================
Ekranda rastgele yerlerde kareler belirir, oyuncu yumruk yaparak
kareleri yok etmeye calisir.
"""

import time
import random
import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum


class FistChallengeState(Enum):
    """Yumruk challenge durumlari."""
    IDLE = "idle"
    COUNTDOWN = "countdown"
    ACTIVE = "active"
    RESULT = "result"


class FistChallenge:
    """Yumruk ile kare kirma mini oyunu."""

    SQUARE_SIZE = 80
    COUNTDOWN_DURATION = 2.0
    ACTIVE_DURATION = 4.0
    RESULT_DURATION = 2.5
    FIST_HIT_RADIUS = 55

    def __init__(self, frame_width: int, frame_height: int):
        self.w = frame_width
        self.h = frame_height

        self.state = FistChallengeState.IDLE
        self.squares: List[Dict[str, Any]] = []
        self.action: str = ""
        self.start_time: float = 0.0
        self.hit_count: int = 0
        self.total_squares: int = 4
        self._challenge_completed: bool = False
        self._result_accuracy: float = 0.0
        self.result_extra_text: str = ""  # Hasar bilgisi icin

    def start_challenge(self, action: str) -> None:
        """Yeni bir yumruk challenge'i baslatir."""
        self.state = FistChallengeState.COUNTDOWN
        self.action = action
        self.start_time = time.time()
        self.hit_count = 0
        self._challenge_completed = False
        self._result_accuracy = 0.0

        # 3 rastgele kare olustur (birbirinden uzak)
        self.squares = []
        margin = self.SQUARE_SIZE + 20
        min_x = margin + 50
        max_x = self.w - margin - 50
        min_y = margin + 80
        max_y = self.h - margin - 80

        for _ in range(self.total_squares):
            attempts = 0
            x, y = self.w // 2, self.h // 2
            while attempts < 50:
                x = random.randint(min_x, max_x)
                y = random.randint(min_y, max_y)
                too_close = False
                for sq in self.squares:
                    dist = ((x - sq["x"]) ** 2 + (y - sq["y"]) ** 2) ** 0.5
                    if dist < self.SQUARE_SIZE * 3:
                        too_close = True
                        break
                if not too_close:
                    break
                attempts += 1
            self.squares.append({"x": x, "y": y, "hit": False, "hit_time": 0.0})

    def update(self, fist_pos: Optional[Tuple[int, int]], is_fist: bool) -> None:
        """Her frame'de cagirilir."""
        elapsed = time.time() - self.start_time

        if self.state == FistChallengeState.COUNTDOWN:
            if elapsed >= self.COUNTDOWN_DURATION:
                self.state = FistChallengeState.ACTIVE
                self.start_time = time.time()

        elif self.state == FistChallengeState.ACTIVE:
            if elapsed >= self.ACTIVE_DURATION:
                self._finish()
                return

            # Yumruk kontrolu
            if fist_pos and is_fist:
                fx, fy = fist_pos
                for sq in self.squares:
                    if sq["hit"]:
                        continue
                    cx = sq["x"] + self.SQUARE_SIZE // 2
                    cy = sq["y"] + self.SQUARE_SIZE // 2
                    dist = ((fx - cx) ** 2 + (fy - cy) ** 2) ** 0.5
                    if dist < self.FIST_HIT_RADIUS + self.SQUARE_SIZE // 2:
                        sq["hit"] = True
                        sq["hit_time"] = time.time()
                        self.hit_count += 1

            # Hepsi vuruldu mu?
            if self.hit_count >= self.total_squares:
                self._finish()

        elif self.state == FistChallengeState.RESULT:
            if elapsed >= self.RESULT_DURATION:
                self.state = FistChallengeState.IDLE
                self._challenge_completed = True

    def _finish(self) -> None:
        """Challenge sonucunu hesapla."""
        if self.hit_count >= 3:
            self._result_accuracy = 100.0
        elif self.hit_count == 2:
            self._result_accuracy = 60.0
        elif self.hit_count == 1:
            self._result_accuracy = 25.0
        else:
            self._result_accuracy = 0.0

        self.state = FistChallengeState.RESULT
        self.start_time = time.time()

    def draw(self, frame: np.ndarray) -> np.ndarray:
        """Challenge UI'ini cizer."""

        if self.state == FistChallengeState.COUNTDOWN:
            elapsed = time.time() - self.start_time
            remaining = max(0, self.COUNTDOWN_DURATION - elapsed)

            # Koyu overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (self.w, self.h), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)

            # Geri sayim
            count_text = f"HAZIRLAN! {int(remaining) + 1}"
            (tw, th), _ = cv2.getTextSize(count_text, cv2.FONT_HERSHEY_SIMPLEX, 2.0, 3)
            cx = (self.w - tw) // 2
            cy = (self.h + th) // 2
            cv2.putText(frame, count_text, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX,
                        2.0, (50, 200, 255), 3, cv2.LINE_AA)

            # Hamle adi
            info = f"HAMLE: {self.action}"
            (iw, _), _ = cv2.getTextSize(info, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cv2.putText(frame, info, ((self.w - iw) // 2, cy + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)

            # Talimat
            inst = "Karelere YUMRUK yap!"
            (inw, _), _ = cv2.getTextSize(inst, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.putText(frame, inst, ((self.w - inw) // 2, cy + 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 255, 150), 2, cv2.LINE_AA)

        elif self.state == FistChallengeState.ACTIVE:
            elapsed = time.time() - self.start_time
            remaining = max(0, self.ACTIVE_DURATION - elapsed)

            # Zamanlayici bar (ust kisim)
            bar_w = int((remaining / self.ACTIVE_DURATION) * (self.w - 40))
            cv2.rectangle(frame, (20, 10), (self.w - 20, 30), (40, 40, 40), -1)
            bar_color = (50, 200, 50) if remaining > 2 else (50, 50, 220)
            cv2.rectangle(frame, (20, 10), (20 + bar_w, 30), bar_color, -1)
            cv2.rectangle(frame, (20, 10), (self.w - 20, 30), (100, 100, 100), 1)

            timer_text = f"{remaining:.1f}s"
            cv2.putText(frame, timer_text, (self.w // 2 - 30, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

            # Kareleri ciz
            now = time.time()
            for sq in self.squares:
                x, y = sq["x"], sq["y"]
                s = self.SQUARE_SIZE

                if sq["hit"]:
                    # Vurulan kare - yesil, patlama efekti
                    dt = now - sq["hit_time"]
                    if dt < 0.3:
                        # Patlama animasyonu
                        expand = int(dt * 60)
                        cv2.rectangle(frame, (x - expand, y - expand),
                                      (x + s + expand, y + s + expand),
                                      (50, 255, 50), 2)
                    cv2.rectangle(frame, (x, y), (x + s, y + s), (50, 200, 50), -1)
                    cv2.rectangle(frame, (x, y), (x + s, y + s), (80, 255, 80), 2)
                    cx_sq, cy_sq = x + s // 2, y + s // 2
                    cv2.putText(frame, "OK", (cx_sq - 18, cy_sq + 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
                else:
                    # Vurulmamis kare - kirmizi, nabiz efekti
                    pulse = int(abs(((now * 3) % 2) - 1) * 50)
                    color = (60 + pulse, 40, 200 + min(pulse, 55))
                    cv2.rectangle(frame, (x, y), (x + s, y + s), color, -1)
                    cv2.rectangle(frame, (x, y), (x + s, y + s), (100, 80, 255), 2)
                    # Yumruk ikonu
                    cx_sq, cy_sq = x + s // 2, y + s // 2
                    cv2.putText(frame, "!!", (cx_sq - 14, cy_sq + 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

            # Vurulan sayisi
            hit_text = f"Vurulan: {self.hit_count}/{self.total_squares}"
            cv2.putText(frame, hit_text, (20, self.h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

        elif self.state == FistChallengeState.RESULT:
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (self.w, self.h), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

            # Sonuc metni
            if self.hit_count >= 3:
                result_text = "MUKEMMEL!"
                result_color = (50, 255, 50)
            elif self.hit_count == 2:
                result_text = "KISMI BASARI"
                result_color = (50, 200, 255)
            elif self.hit_count == 1:
                result_text = "ZAYIF"
                result_color = (50, 100, 255)
            else:
                result_text = "BASARISIZ!"
                result_color = (50, 50, 255)

            (tw, th), _ = cv2.getTextSize(result_text, cv2.FONT_HERSHEY_SIMPLEX, 1.8, 3)
            cx = (self.w - tw) // 2
            cy = (self.h + th) // 2 - 30
            cv2.putText(frame, result_text, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX,
                        1.8, result_color, 3, cv2.LINE_AA)

            # Dogruluk
            acc_text = f"Vurulan: {self.hit_count}/{self.total_squares} - %{self._result_accuracy:.0f}"
            (aw, _), _ = cv2.getTextSize(acc_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cv2.putText(frame, acc_text, ((self.w - aw) // 2, cy + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)

            # Hamle adi
            act_text = f"Hamle: {self.action}"
            (actw, _), _ = cv2.getTextSize(act_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.putText(frame, act_text, ((self.w - actw) // 2, cy + 85),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2, cv2.LINE_AA)

            # Ekstra bilgi (hasar, vs.)
            if self.result_extra_text:
                (etw, _), _ = cv2.getTextSize(self.result_extra_text,
                                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
                extra_color = (50, 255, 100) if self._result_accuracy >= 70 else (50, 200, 255)
                cv2.putText(frame, self.result_extra_text,
                            ((self.w - etw) // 2, cy + 125),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, extra_color, 2, cv2.LINE_AA)

        return frame

    def is_done(self) -> bool:
        """Challenge tamamlandi mi?"""
        return self._challenge_completed

    def get_result(self) -> Tuple[float, str]:
        """Sonuc dondurur: (accuracy, action)."""
        return self._result_accuracy, self.action

    def reset(self) -> None:
        """Challenge'i sifirlar."""
        self.state = FistChallengeState.IDLE
        self.squares = []
        self.action = ""
        self.hit_count = 0
        self._challenge_completed = False
        self._result_accuracy = 0.0
        self.result_extra_text = ""
