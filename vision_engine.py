"""
vision_engine.py - El Takip ve Bölge Algılama Motoru
=====================================================
MediaPipe Tasks API (HandLandmarker) kullanarak webcam üzerinden
işaret parmağı ucunu (landmark 8) takip eder. Ekranı 4 çeyreğe
böler ve parmak bir çeyrekte 2 saniye beklerse o bölgenin ID'sini döndürür.
"""

import os
import time
from enum import Enum
from typing import Optional, Tuple

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions


class Quadrant(Enum):
    """Ekranın 4 çeyreğini temsil eden enum."""
    SOL_UST = "sol_ust"
    SAG_UST = "sag_ust"
    SOL_ALT = "sol_alt"
    SAG_ALT = "sag_alt"


class HandTracker:
    """
    Webcam üzerinden el takibi yapan sınıf.

    MediaPipe HandLandmarker (Tasks API) ile işaret parmağı ucunu
    (landmark 8) tespit eder, ekranı 4 çeyreğe böler ve parmak bir
    çeyrekte belirli bir süre (varsayılan 2 saniye) bekletildiğinde
    seçim yapıldığını bildirir.
    """

    # İşaret parmağı ucu landmark indeksi
    INDEX_FINGER_TIP = 8

    def __init__(self, camera_index: int = 0, dwell_time: float = 2.0):
        """
        HandTracker sınıfını başlatır.

        Args:
            camera_index: Kullanılacak kamera indeksi (varsayılan: 0).
            dwell_time: Seçim için gereken bekleme süresi, saniye (varsayılan: 2.0).
        """
        self.dwell_time = dwell_time

        # ----- Kamera Kurulumu -----
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Kamera açılamadı (index={camera_index}). "
                "Lütfen kameranızın bağlı olduğundan emin olun."
            )

        # Kamera cozunurlugunu 1280x720'ye zorla (Windows'ta varsayilan 640x480 cok kucuk)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[*] Kamera cozunurlugu: {self.frame_width}x{self.frame_height}")

        # ----- MediaPipe HandLandmarker Kurulumu -----
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model dosyası bulunamadı: {model_path}\n"
                "Lütfen hand_landmarker.task dosyasını proje dizinine indirin."
            )

        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.hand_landmarker = vision.HandLandmarker.create_from_options(options)

        # Drawing utilities
        self._draw_utils = vision.drawing_utils
        self._hand_connections = vision.HandLandmarksConnections.HAND_CONNECTIONS

        # ----- Bekleme (Dwell) Durumu -----
        self._current_quadrant: Optional[Quadrant] = None
        self._quadrant_enter_time: Optional[float] = None
        self._selection_confirmed = False

        # Son algılama sonucu (çizim için cache)
        self._last_result: Optional[vision.HandLandmarkerResult] = None

    # ------------------------------------------------------------------ #
    #  GENEL (PUBLIC) METODLAR                                            #
    # ------------------------------------------------------------------ #

    def read_frame(self) -> Optional[np.ndarray]:
        """Kameradan bir kare okur (ayna efektli)."""
        success, frame = self.cap.read()
        if not success:
            return None
        frame = cv2.flip(frame, 1)
        return frame

    def detect_finger(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Verilen karede işaret parmağı ucunun (x, y) koordinatını bulur.

        Args:
            frame: BGR formatlı OpenCV görüntüsü.

        Returns:
            (x, y) piksel koordinatı veya el algılanamazsa None.
        """
        # BGR -> RGB çevir ve MediaPipe Image oluştur
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # El algılama
        result = self.hand_landmarker.detect(mp_image)
        self._last_result = result

        if not result.hand_landmarks:
            return None

        # İlk elin işaret parmağı ucu (landmark 8)
        hand = result.hand_landmarks[0]
        tip = hand[self.INDEX_FINGER_TIP]

        # Normalize koordinatları piksel koordinatlarına çevir
        x = int(tip.x * self.frame_width)
        y = int(tip.y * self.frame_height)

        return (x, y)

    def get_quadrant(self, x: int, y: int) -> Quadrant:
        """
        Verilen (x, y) koordinatının hangi çeyrekte olduğunu belirler.

        Ekran düzeni:
            ┌────────────┬────────────┐
            │  SOL_UST   │  SAG_UST   │
            ├────────────┼────────────┤
            │  SOL_ALT   │  SAG_ALT   │
            └────────────┴────────────┘
        """
        mid_x = self.frame_width // 2
        mid_y = self.frame_height // 2

        if x < mid_x and y < mid_y:
            return Quadrant.SOL_UST
        elif x >= mid_x and y < mid_y:
            return Quadrant.SAG_UST
        elif x < mid_x and y >= mid_y:
            return Quadrant.SOL_ALT
        else:
            return Quadrant.SAG_ALT

    def update_dwell(self, quadrant: Optional[Quadrant]) -> Optional[Quadrant]:
        """
        Bekleme (dwell) durumunu günceller ve gerekirse seçimi onaylar.

        Parmak aynı çeyrekte `dwell_time` saniye boyunca kalırsa,
        o çeyrek seçilmiş kabul edilir.
        """
        now = time.time()

        if quadrant is None:
            self._reset_dwell()
            return None

        if quadrant != self._current_quadrant:
            self._current_quadrant = quadrant
            self._quadrant_enter_time = now
            self._selection_confirmed = False
            return None

        elapsed = now - self._quadrant_enter_time
        if elapsed >= self.dwell_time and not self._selection_confirmed:
            self._selection_confirmed = True
            return quadrant

        return None

    def get_dwell_progress(self) -> float:
        """Mevcut bekleme süresinin 0.0-1.0 arası ilerleme oranını döndürür."""
        if self._current_quadrant is None or self._quadrant_enter_time is None:
            return 0.0
        elapsed = time.time() - self._quadrant_enter_time
        return min(elapsed / self.dwell_time, 1.0)

    def get_current_quadrant(self) -> Optional[Quadrant]:
        """Parmağın şu an bulunduğu çeyreği döndürür."""
        return self._current_quadrant

    def draw_hand_landmarks(self, frame: np.ndarray) -> np.ndarray:
        """
        Son algılama sonuçlarına göre el iskeletini kare üzerine çizer.
        """
        if self._last_result is None or not self._last_result.hand_landmarks:
            return frame

        hand = self._last_result.hand_landmarks[0]

        # Landmark'ları piksel koordinatlarına çevir ve çizgileri çiz
        h, w = frame.shape[:2]
        points = []
        for lm in hand:
            px = int(lm.x * w)
            py = int(lm.y * h)
            points.append((px, py))

        # Bağlantı çizgilerini çiz
        for connection in self._hand_connections:
            start_idx = connection.start
            end_idx = connection.end
            if start_idx < len(points) and end_idx < len(points):
                cv2.line(frame, points[start_idx], points[end_idx], (0, 200, 255), 2)

        # Landmark noktalarını çiz
        for i, pt in enumerate(points):
            color = (0, 255, 128) if i == self.INDEX_FINGER_TIP else (0, 180, 100)
            radius = 5 if i == self.INDEX_FINGER_TIP else 3
            cv2.circle(frame, pt, radius, color, -1)

        return frame

    def reset_selection(self) -> None:
        """Seçim durumunu sıfırlar."""
        self._reset_dwell()

    def release(self) -> None:
        """Kamera ve MediaPipe kaynaklarını serbest bırakır."""
        if self.cap.isOpened():
            self.cap.release()
        self.hand_landmarker.close()

    # ------------------------------------------------------------------ #
    #  ÖZEL (PRIVATE) METODLAR                                            #
    # ------------------------------------------------------------------ #

    def _reset_dwell(self) -> None:
        """Dahili bekleme durumunu sıfırlar."""
        self._current_quadrant = None
        self._quadrant_enter_time = None
        self._selection_confirmed = False

    # ------------------------------------------------------------------ #
    #  CONTEXT MANAGER DESTEĞİ                                           #
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "HandTracker":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
