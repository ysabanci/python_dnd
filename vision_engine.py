"""
vision_engine.py - El Takip ve Bolge Algilama Motoru
=====================================================
MediaPipe Tasks API (HandLandmarker) kullanarak webcam uzerinden
el takibi yapar. Tek el ve cift el algilama destegi vardir.

Tek el modu (num_hands=1): Oyunda aktif olarak kullanilir.
Cift el modu (num_hands=2): Gelecek entegrasyon icin hazir,
    test_dual_hands.py ile test edilebilir.

Iyilestirmeler:
  - Smoothing (EMA filtresi) ile titresim azaltma
  - Guven esigi otomatik ayarlama
  - Cift el algilama destegi (detect_all_hands)
"""

import os
import time
from enum import Enum
from typing import Optional, Tuple, List, Dict

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions


class Quadrant(Enum):
    """Ekranin 4 ceyregini temsil eden enum."""
    SOL_UST = "sol_ust"
    SAG_UST = "sag_ust"
    SOL_ALT = "sol_alt"
    SAG_ALT = "sag_alt"


class HandData:
    """
    Tek bir elin verilerini tutan sinif.
    Cift el algilamada her el icin ayri bir HandData olusturulur.
    """
    def __init__(self, hand_index: int, handedness: str = ""):
        self.hand_index = hand_index       # 0 veya 1
        self.handedness = handedness       # "Left" veya "Right"
        self.finger_pos: Optional[Tuple[int, int]] = None   # Isaret parmagi ucu
        self.palm_pos: Optional[Tuple[int, int]] = None     # Avuc merkezi
        self.is_fist: bool = False
        self.is_open: bool = False          # Tum parmaklar acik mi
        self.is_pointing: bool = False      # Sadece isaret parmagi acik mi
        self.landmarks: list = []           # Piksel koordinatlari (21 nokta)


class HandTracker:
    """
    Webcam uzerinden el takibi yapan sinif.

    MediaPipe HandLandmarker (Tasks API) ile el takibi yapar.
    Tek el veya cift el algilama destegi mevcuttur.

    Iyilestirmeler:
      - EMA (Exponential Moving Average) smoothing ile titresim azaltma
      - Adaptif guven esikleri
      - Cift el algilama (detect_all_hands)
    """

    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_TIP = 12

    # EMA smoothing katsayisi (0-1, dusuk = daha yumusak)
    SMOOTHING_FACTOR = 0.45

    def __init__(self, camera_index: int = 0, dwell_time: float = 2.0,
                 num_hands: int = 1):
        """
        HandTracker sinifini baslatir.

        Args:
            camera_index: Kullanilacak kamera indeksi (varsayilan: 0).
            dwell_time: Secim icin gereken bekleme suresi, saniye (varsayilan: 2.0).
            num_hands: Algilanacak el sayisi (1 veya 2, varsayilan: 1).
        """
        self.dwell_time = dwell_time
        self.camera_available = False
        self.num_hands = max(1, min(2, num_hands))

        # ----- Kamera Kurulumu -----
        try:
            self.cap = cv2.VideoCapture(camera_index)
            if not self.cap.isOpened():
                print(f"[!] Kamera acilamadi (index={camera_index}).")
                self.frame_width = 1280
                self.frame_height = 720
            else:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                # FPS iyilestirmesi
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                # Tampon boyutunu kucult (gecikme azaltma)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.camera_available = True
                print(f"[*] Kamera cozunurlugu: {self.frame_width}x{self.frame_height}")
        except Exception as e:
            print(f"[!] Kamera hatasi: {e}")
            self.cap = None
            self.frame_width = 1280
            self.frame_height = 720

        # ----- MediaPipe HandLandmarker Kurulumu -----
        model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task"
        )
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model dosyasi bulunamadi: {model_path}\n"
                "Lutfen hand_landmarker.task dosyasini proje dizinine indirin."
            )

        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=self.num_hands,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.4,
        )
        self.hand_landmarker = vision.HandLandmarker.create_from_options(options)

        # Drawing utilities
        self._hand_connections = vision.HandLandmarksConnections.HAND_CONNECTIONS

        # ----- Bekleme (Dwell) Durumu -----
        self._current_quadrant: Optional[Quadrant] = None
        self._quadrant_enter_time: Optional[float] = None
        self._selection_confirmed = False

        # Son algilama sonucu (cizim icin cache)
        self._last_result: Optional[vision.HandLandmarkerResult] = None

        # ----- Smoothing (EMA) -----
        self._smooth_x: Optional[float] = None
        self._smooth_y: Optional[float] = None
        self._last_detect_time: float = 0.0
        self._no_hand_frames: int = 0  # El kaybedilince hemen sifirlamama

    # ------------------------------------------------------------------ #
    #  GENEL (PUBLIC) METODLAR                                            #
    # ------------------------------------------------------------------ #

    def read_frame(self) -> Optional[np.ndarray]:
        """Kameradan bir kare okur (ayna efektli)."""
        if not self.camera_available or self.cap is None:
            return None
        success, frame = self.cap.read()
        if not success:
            return None
        frame = cv2.flip(frame, 1)
        return frame

    def detect_finger(self, frame: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Verilen karede isaret parmagi ucunun (x, y) koordinatini bulur.
        EMA smoothing uygulanarak titresim azaltilir.

        Args:
            frame: BGR formatli OpenCV goruntusu.

        Returns:
            (x, y) piksel koordinati veya el algilanamazsa None.
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = self.hand_landmarker.detect(mp_image)
        self._last_result = result

        if not result.hand_landmarks:
            self._no_hand_frames += 1
            # 5 frame el gorulmezse smoothing sifirla
            if self._no_hand_frames > 5:
                self._smooth_x = None
                self._smooth_y = None
            return None

        self._no_hand_frames = 0

        # Ilk elin isaret parmagi ucu (landmark 8)
        hand = result.hand_landmarks[0]
        tip = hand[self.INDEX_FINGER_TIP]

        raw_x = tip.x * self.frame_width
        raw_y = tip.y * self.frame_height

        # EMA smoothing
        if self._smooth_x is None:
            self._smooth_x = raw_x
            self._smooth_y = raw_y
        else:
            a = self.SMOOTHING_FACTOR
            self._smooth_x = a * raw_x + (1 - a) * self._smooth_x
            self._smooth_y = a * raw_y + (1 - a) * self._smooth_y

        return (int(self._smooth_x), int(self._smooth_y))

    def detect_fist(self, frame: np.ndarray) -> Tuple[Optional[Tuple[int, int]], bool]:
        """
        Yumruk jesti ve avuc merkezi konumunu tespit eder.

        Returns:
            (palm_pos, is_fist): Avuc merkezi (x,y) ve yumruk yapilip yapilmadigi.
            El algilanmazsa (None, False) doner.
        """
        if self._last_result is None or not self._last_result.hand_landmarks:
            return None, False

        hand = self._last_result.hand_landmarks[0]
        palm_pos = self._calc_palm_center(hand)
        is_fist = self._check_fist(hand)

        return palm_pos, is_fist

    def detect_all_hands(self, frame: np.ndarray) -> List[HandData]:
        """
        Karede gornen TUM elleri (1 veya 2) algilar ve detayli bilgi dondurur.
        Cift el algilama icin num_hands=2 ile baslatilmis olmali.

        Args:
            frame: BGR formatli OpenCV goruntusu.

        Returns:
            HandData listesi (0, 1 veya 2 eleman).
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        result = self.hand_landmarker.detect(mp_image)
        self._last_result = result

        hands: List[HandData] = []

        if not result.hand_landmarks:
            return hands

        for idx, hand_lm in enumerate(result.hand_landmarks):
            # Handedness bilgisi
            handedness_str = ""
            if result.handedness and idx < len(result.handedness):
                cats = result.handedness[idx]
                if cats:
                    handedness_str = cats[0].category_name  # "Left" / "Right"

            hd = HandData(hand_index=idx, handedness=handedness_str)

            # Isaret parmagi ucu
            tip = hand_lm[self.INDEX_FINGER_TIP]
            hd.finger_pos = (
                int(tip.x * self.frame_width),
                int(tip.y * self.frame_height),
            )

            # Avuc merkezi
            hd.palm_pos = self._calc_palm_center(hand_lm)

            # Jest tespitleri
            hd.is_fist = self._check_fist(hand_lm)
            hd.is_open = self._check_open_hand(hand_lm)
            hd.is_pointing = self._check_pointing(hand_lm)

            # Piksel koordinatlari
            h, w = frame.shape[:2]
            hd.landmarks = [
                (int(lm.x * w), int(lm.y * h)) for lm in hand_lm
            ]

            hands.append(hd)

        return hands

    def get_quadrant(self, x: int, y: int) -> Quadrant:
        """
        Verilen (x, y) koordinatinin hangi ceyrekte oldugunu belirler.
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
        Bekleme (dwell) durumunu gunceller ve gerekirse secimi onaylar.
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
        """Mevcut bekleme suresinin 0.0-1.0 arasi ilerleme oranini dondurur."""
        if self._current_quadrant is None or self._quadrant_enter_time is None:
            return 0.0
        elapsed = time.time() - self._quadrant_enter_time
        return min(elapsed / self.dwell_time, 1.0)

    def get_current_quadrant(self) -> Optional[Quadrant]:
        """Parmagin su an bulundugu ceyreyi dondurur."""
        return self._current_quadrant

    def draw_hand_landmarks(self, frame: np.ndarray) -> np.ndarray:
        """Son algilama sonuclarina gore el iskeletini kare uzerine cizer."""
        if self._last_result is None or not self._last_result.hand_landmarks:
            return frame

        h, w = frame.shape[:2]
        # Renk paleti (el basina farkli renk)
        colors = [
            ((0, 200, 255), (0, 255, 128)),   # El 0: turuncu cizgi, yesil nokta
            ((255, 150, 50), (255, 200, 100)), # El 1: mavi cizgi, acik mavi nokta
        ]

        for hand_idx, hand in enumerate(self._last_result.hand_landmarks):
            line_color, point_color = colors[hand_idx % len(colors)]

            points = []
            for lm in hand:
                px = int(lm.x * w)
                py = int(lm.y * h)
                points.append((px, py))

            # Baglanti cizgilerini ciz
            for connection in self._hand_connections:
                si, ei = connection.start, connection.end
                if si < len(points) and ei < len(points):
                    cv2.line(frame, points[si], points[ei], line_color, 2)

            # Landmark noktalarini ciz
            for i, pt in enumerate(points):
                c = (0, 255, 128) if i == self.INDEX_FINGER_TIP else point_color
                r = 6 if i == self.INDEX_FINGER_TIP else 3
                cv2.circle(frame, pt, r, c, -1)

            # Handedness etiketi
            if self._last_result.handedness and hand_idx < len(self._last_result.handedness):
                cats = self._last_result.handedness[hand_idx]
                if cats and points:
                    label = cats[0].category_name  # "Left" / "Right"
                    wrist = points[0]
                    cv2.putText(frame, label, (wrist[0] - 20, wrist[1] - 15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, line_color, 2)

        return frame

    def reset_selection(self) -> None:
        """Secim durumunu sifirlar."""
        self._reset_dwell()

    def release(self) -> None:
        """Kamera ve MediaPipe kaynaklarini serbest birakir."""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        self.hand_landmarker.close()

    # ------------------------------------------------------------------ #
    #  JEST ALGILAMA YARDIMCILARI                                         #
    # ------------------------------------------------------------------ #

    def _calc_palm_center(self, hand) -> Tuple[int, int]:
        """Avuc merkezini hesaplar (wrist + index_mcp + pinky_mcp ortalamasi)."""
        wrist = hand[0]
        idx_mcp = hand[5]
        pinky_mcp = hand[17]
        px = int(((wrist.x + idx_mcp.x + pinky_mcp.x) / 3) * self.frame_width)
        py = int(((wrist.y + idx_mcp.y + pinky_mcp.y) / 3) * self.frame_height)
        return (px, py)

    def _check_fist(self, hand) -> bool:
        """Yumruk jesti kontrolu: 4 parmaktan en az 3'u kivrik mi."""
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
        curled = sum(1 for t, p in zip(finger_tips, finger_pips)
                     if hand[t].y > hand[p].y)
        return curled >= 3

    def _check_open_hand(self, hand) -> bool:
        """Acik el kontrolu: 4 parmak da duz mu."""
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
        extended = sum(1 for t, p in zip(finger_tips, finger_pips)
                       if hand[t].y < hand[p].y)
        return extended >= 4

    def _check_pointing(self, hand) -> bool:
        """Isaret jesti: sadece isaret parmagi acik, digerleri kapali."""
        # Isaret parmagi acik mi
        index_extended = hand[8].y < hand[6].y
        # Diger 3 parmak kapali mi
        others_curled = all(
            hand[t].y > hand[p].y
            for t, p in [(12, 10), (16, 14), (20, 18)]
        )
        return index_extended and others_curled

    # ------------------------------------------------------------------ #
    #  OZEL METODLAR                                                      #
    # ------------------------------------------------------------------ #

    def _reset_dwell(self) -> None:
        """Dahili bekleme durumunu sifirlar."""
        self._current_quadrant = None
        self._quadrant_enter_time = None
        self._selection_confirmed = False

    # ------------------------------------------------------------------ #
    #  CONTEXT MANAGER DESTEGI                                            #
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "HandTracker":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
