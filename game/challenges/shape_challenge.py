"""
shape_challenge.py - Geometrik Sekil Cizme Mini Oyunu
======================================================
Savas modunda kullanicinin geometrik sekiller cizmesini
ve dogruluk oranini hesaplayan moduldur.
"""

import math
import time
import random
from enum import Enum
from typing import List, Optional, Tuple

import cv2
import numpy as np


class ShapeType(Enum):
    """Cizilebilecek geometrik sekiller."""
    TRIANGLE = "ucgen"
    SQUARE = "kare"
    CIRCLE = "daire"
    RECTANGLE = "dikdortgen"
    INFINITY = "sonsuzluk"


class ChallengeState(Enum):
    """Sekil cizme mini oyununun durumlari."""
    IDLE = "idle"
    COUNTDOWN = "countdown"
    DRAWING = "drawing"
    RESULT = "result"


class ShapeChallenge:
    """Geometrik sekil cizme mini oyunu yoneticisi."""

    DRAW_TIME = 5.0
    RESULT_DISPLAY_TIME = 3.0
    COUNTDOWN_TIME = 3.0

    COLOR_TARGET = (100, 255, 100)
    COLOR_USER_PATH = (255, 150, 50)
    COLOR_ACCURACY_HIGH = (50, 200, 50)
    COLOR_ACCURACY_MED = (50, 200, 230)
    COLOR_ACCURACY_LOW = (50, 50, 220)

    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_BOLD = cv2.FONT_HERSHEY_DUPLEX

    def __init__(self, frame_width: int, frame_height: int):
        self.w = frame_width
        self.h = frame_height
        self.state = ChallengeState.IDLE

        self.current_shape: Optional[ShapeType] = None
        self.target_points: List[Tuple[int, int]] = []
        self.user_points: List[Tuple[int, int]] = []

        self.start_time: float = 0.0
        self.result_time: float = 0.0
        self.countdown_start: float = 0.0
        self.accuracy: float = 0.0
        self.combat_action: str = ""
        self._challenge_completed: bool = False
        self.result_extra_text: str = ""  # Hasar bilgisi icin

    def start_challenge(self, shape_type: ShapeType, action: str = "") -> None:
        """Yeni bir sekil cizme challenge'i baslatir."""
        self.current_shape = shape_type
        self.combat_action = action
        self.target_points = self._generate_shape_contour(shape_type)
        self.user_points = []
        self.accuracy = 0.0
        self.state = ChallengeState.COUNTDOWN
        self.countdown_start = time.time()

    def update(self, finger_pos: Optional[Tuple[int, int]] = None) -> Optional[float]:
        """
        Her frame'de cagirilir. Durumu gunceller.
        Returns: Eger sonuc hesaplandiysa accuracy (0-100), yoksa None.
        """
        now = time.time()

        if self.state == ChallengeState.COUNTDOWN:
            if now - self.countdown_start >= self.COUNTDOWN_TIME:
                self.state = ChallengeState.DRAWING
                self.start_time = now
                self.user_points = []
            return None

        elif self.state == ChallengeState.DRAWING:
            if finger_pos is not None:
                self.user_points.append(finger_pos)
            if now - self.start_time >= self.DRAW_TIME:
                self.accuracy = self._calculate_accuracy()
                self.state = ChallengeState.RESULT
                self.result_time = now
                return self.accuracy
            return None

        elif self.state == ChallengeState.RESULT:
            if now - self.result_time >= self.RESULT_DISPLAY_TIME:
                self.state = ChallengeState.IDLE
                self._challenge_completed = True
            return None

        return None

    def is_active(self) -> bool:
        """Challenge devam ediyor mu?"""
        return self.state in (ChallengeState.COUNTDOWN, ChallengeState.DRAWING, ChallengeState.RESULT)

    def is_done(self) -> bool:
        """Challenge tamamlandi mi (sonuc ekrani gosterildi ve IDLE'a dondu)?"""
        return self.state == ChallengeState.IDLE and self._challenge_completed

    def get_remaining_time(self) -> float:
        """Kalan cizim suresi."""
        if self.state != ChallengeState.DRAWING:
            return self.DRAW_TIME
        return max(0, self.DRAW_TIME - (time.time() - self.start_time))

    def get_countdown(self) -> int:
        """Geri sayim sayisi (3, 2, 1)."""
        if self.state != ChallengeState.COUNTDOWN:
            return 0
        elapsed = time.time() - self.countdown_start
        return max(0, int(self.COUNTDOWN_TIME - elapsed) + 1)

    def get_result(self) -> Tuple[float, str]:
        """Sonuc accuracy ve combat action'i dondurur."""
        return (self.accuracy, self.combat_action)

    def reset(self) -> None:
        """Mini oyunu sifirlar."""
        self.state = ChallengeState.IDLE
        self.current_shape = None
        self.target_points = []
        self.user_points = []
        self.accuracy = 0.0
        self.combat_action = ""
        self._challenge_completed = False
        self.result_extra_text = ""

    # ------------------------------------------------------------------ #
    #  CIZIM METODLARI                                                    #
    # ------------------------------------------------------------------ #

    def draw(self, frame: np.ndarray) -> np.ndarray:
        """Mevcut duruma gore challenge UI'ini cizer."""
        if self.state == ChallengeState.COUNTDOWN:
            return self._draw_countdown(frame)
        elif self.state == ChallengeState.DRAWING:
            return self._draw_challenge(frame)
        elif self.state == ChallengeState.RESULT:
            return self._draw_result(frame)
        return frame

    def _draw_countdown(self, frame: np.ndarray) -> np.ndarray:
        """Geri sayim ekrani."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

        count = self.get_countdown()

        shape_name = self.current_shape.value.upper() if self.current_shape else "?"
        action_text = f"{self.combat_action.upper()} - {shape_name} CIZ!"
        (tw, _), _ = cv2.getTextSize(action_text, self.FONT_BOLD, 1.0, 2)
        cv2.putText(frame, action_text, ((self.w - tw) // 2, self.h // 2 - 60),
                    self.FONT_BOLD, 1.0, (100, 200, 255), 2, cv2.LINE_AA)

        count_text = str(count)
        (tw2, th2), _ = cv2.getTextSize(count_text, self.FONT_BOLD, 4.0, 4)
        cv2.putText(frame, count_text, ((self.w - tw2) // 2, self.h // 2 + th2 // 2 + 20),
                    self.FONT_BOLD, 4.0, (50, 215, 255), 4, cv2.LINE_AA)

        hint = "Sekli parmaginla ciz!"
        (tw3, _), _ = cv2.getTextSize(hint, self.FONT, 0.7, 1)
        cv2.putText(frame, hint, ((self.w - tw3) // 2, self.h // 2 + 80),
                    self.FONT, 0.7, (180, 180, 180), 1, cv2.LINE_AA)

        return frame

    def _draw_challenge(self, frame: np.ndarray) -> np.ndarray:
        """Cizim ekrani: hedef sekil + kullanici yolu + zamanlayici."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (15, 15, 15), -1)
        frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)

        # Draw target shape
        if len(self.target_points) > 1:
            if self.current_shape == ShapeType.CIRCLE:
                cx = int(np.mean([p[0] for p in self.target_points]))
                cy = int(np.mean([p[1] for p in self.target_points]))
                radius = int(np.max([math.dist((cx, cy), p) for p in self.target_points]))
                cv2.circle(frame, (cx, cy), radius, self.COLOR_TARGET, 3)
            else:
                pts = np.array(self.target_points, dtype=np.int32)
                cv2.polylines(frame, [pts], True, self.COLOR_TARGET, 3, cv2.LINE_AA)

        # Draw user path
        if len(self.user_points) > 1:
            for i in range(1, len(self.user_points)):
                pt1 = self.user_points[i - 1]
                pt2 = self.user_points[i]
                if math.dist(pt1, pt2) < 80:
                    cv2.line(frame, pt1, pt2, self.COLOR_USER_PATH, 4, cv2.LINE_AA)

        # Timer bar
        remaining = self.get_remaining_time()
        progress = remaining / self.DRAW_TIME
        bar_w = int((self.w - 40) * progress)
        cv2.rectangle(frame, (20, 15), (self.w - 20, 30), (40, 40, 40), -1)
        bar_color = (50, 200, 50) if progress > 0.5 else ((50, 200, 230) if progress > 0.25 else (50, 50, 220))
        cv2.rectangle(frame, (20, 15), (20 + bar_w, 30), bar_color, -1)
        cv2.rectangle(frame, (20, 15), (self.w - 20, 30), (120, 120, 120), 1)

        time_text = f"Sure: {remaining:.1f}s"
        cv2.putText(frame, time_text, (self.w - 180, 55),
                    self.FONT, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

        shape_name = self.current_shape.value.upper() if self.current_shape else ""
        cv2.putText(frame, f"Ciz: {shape_name}", (20, 55),
                    self.FONT, 0.8, self.COLOR_TARGET, 2, cv2.LINE_AA)

        return frame

    def _draw_result(self, frame: np.ndarray) -> np.ndarray:
        """Sonuc ekrani."""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (self.w, self.h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.8, frame, 0.2, 0)

        if self.accuracy >= 70:
            color = self.COLOR_ACCURACY_HIGH
            verdict = "BASARILI!"
        elif self.accuracy >= 40:
            color = self.COLOR_ACCURACY_MED
            verdict = "KISMI BASARI"
        else:
            color = self.COLOR_ACCURACY_LOW
            verdict = "BASARISIZ!"

        (tw, _), _ = cv2.getTextSize(verdict, self.FONT_BOLD, 1.5, 3)
        cv2.putText(frame, verdict, ((self.w - tw) // 2, self.h // 2 - 50),
                    self.FONT_BOLD, 1.5, color, 3, cv2.LINE_AA)

        acc_text = f"Dogruluk: %{self.accuracy:.0f}"
        (tw2, _), _ = cv2.getTextSize(acc_text, self.FONT_BOLD, 1.2, 2)
        cv2.putText(frame, acc_text, ((self.w - tw2) // 2, self.h // 2 + 20),
                    self.FONT_BOLD, 1.2, (255, 255, 255), 2, cv2.LINE_AA)

        action_text = f"Hamle: {self.combat_action}"
        (tw3, _), _ = cv2.getTextSize(action_text, self.FONT, 0.8, 2)
        cv2.putText(frame, action_text, ((self.w - tw3) // 2, self.h // 2 + 70),
                    self.FONT, 0.8, (50, 215, 255), 2, cv2.LINE_AA)

        bar_x, bar_y = 60, self.h // 2 + 100
        bar_w, bar_h = self.w - 120, 20
        fill_w = int(bar_w * self.accuracy / 100)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 40, 40), -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), color, -1)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (120, 120, 120), 2)

        # Ekstra bilgi (hasar, vs.)
        if self.result_extra_text:
            (tw4, _), _ = cv2.getTextSize(self.result_extra_text, self.FONT_BOLD, 0.9, 2)
            extra_color = (50, 255, 100) if self.accuracy >= 70 else (50, 200, 255)
            cv2.putText(frame, self.result_extra_text, ((self.w - tw4) // 2, self.h // 2 + 145),
                        self.FONT_BOLD, 0.9, extra_color, 2, cv2.LINE_AA)

        return frame

    # ------------------------------------------------------------------ #
    #  PRIVATE METODLAR                                                   #
    # ------------------------------------------------------------------ #

    def _generate_shape_contour(self, shape_type: ShapeType) -> List[Tuple[int, int]]:
        """Hedef seklin kontur noktalarini uretir."""
        cx, cy = self.w // 2, self.h // 2
        size = min(self.w, self.h) // 4

        if shape_type == ShapeType.TRIANGLE:
            return [
                (cx, cy - size),
                (cx - int(size * 0.87), cy + size // 2),
                (cx + int(size * 0.87), cy + size // 2),
            ]
        elif shape_type == ShapeType.SQUARE:
            half = int(size * 0.75)
            return [
                (cx - half, cy - half), (cx + half, cy - half),
                (cx + half, cy + half), (cx - half, cy + half),
            ]
        elif shape_type == ShapeType.RECTANGLE:
            hw, hh = int(size * 1.1), int(size * 0.6)
            return [
                (cx - hw, cy - hh), (cx + hw, cy - hh),
                (cx + hw, cy + hh), (cx - hw, cy + hh),
            ]
        elif shape_type == ShapeType.CIRCLE:
            points = []
            for i in range(64):
                angle = 2 * math.pi * i / 64
                points.append((int(cx + size * math.cos(angle)), int(cy + size * math.sin(angle))))
            return points
        elif shape_type == ShapeType.INFINITY:
            # Lemniscate (sonsuzluk isareti)
            points = []
            a = size * 1.3
            for i in range(80):
                t = 2 * math.pi * i / 80
                denom = 1 + math.sin(t) ** 2
                px = int(cx + a * math.cos(t) / denom)
                py = int(cy + a * math.sin(t) * math.cos(t) / denom)
                points.append((px, py))
            return points
        return []

    def _calculate_accuracy(self) -> float:
        """Kullanicinin ciziminin hedef sekle dogruluk oranini hesaplar."""
        if len(self.user_points) < 5 or len(self.target_points) < 3:
            return 0.0

        is_dense = self.current_shape in (ShapeType.CIRCLE, ShapeType.INFINITY)
        target_dense = self._densify_contour(
            self.target_points, is_circle=is_dense
        )
        target_arr = np.array(target_dense, dtype=np.float32)

        # Distance Score
        distances = []
        for pt in self.user_points:
            pt_arr = np.array(pt, dtype=np.float32)
            dists = np.linalg.norm(target_arr - pt_arr, axis=1)
            distances.append(np.min(dists))

        avg_dist = np.mean(distances)
        max_accept = min(self.w, self.h) * 0.08
        distance_score = max(0, 100 - (avg_dist / max_accept) * 100)

        # Coverage Score
        num_segments = 20
        seg_size = max(1, len(target_dense) // num_segments)
        covered = 0
        user_arr = np.array(self.user_points, dtype=np.float32)

        for i in range(num_segments):
            seg_idx = min(i * seg_size, len(target_dense) - 1)
            seg_pt = np.array(target_dense[seg_idx], dtype=np.float32)
            dists_to_seg = np.linalg.norm(user_arr - seg_pt, axis=1)
            if np.min(dists_to_seg) < max_accept * 2:
                covered += 1

        coverage_score = (covered / num_segments) * 100
        final = distance_score * 0.6 + coverage_score * 0.4
        return max(0, min(100, final))

    def _densify_contour(self, points: List[Tuple[int, int]], is_circle: bool = False) -> List[Tuple[int, int]]:
        """Kontur noktalarini yogunlastirir."""
        if is_circle:
            return points

        dense = []
        for i in range(len(points)):
            p1, p2 = points[i], points[(i + 1) % len(points)]
            for j in range(20):
                t = j / 20
                dense.append((int(p1[0] + (p2[0] - p1[0]) * t), int(p1[1] + (p2[1] - p1[1]) * t)))
        return dense
