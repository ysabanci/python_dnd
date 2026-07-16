"""
test_dual_hands.py - Cift El Algilama Test Scripti
====================================================
Bu dosya YALNIZCA TEST AMACLIDIR.
Cift el algilama sistemi oyuna entegre edildiginde bu dosya
kaldirilabilir.

Kullanim:
    python test_dual_hands.py

Cift el modunda kamerayi acar ve iki eli de algilar.
Her el icin:
  - Isaret parmagi ucu (yesil nokta)
  - Avuc merkezi (kirmizi nokta)
  - El iskeleti (turuncu/mavi cizgiler)
  - Sol/Sag etiketi
  - Jest durumu (Yumruk / Acik El / Isaret / -)

Kontroller:
  Q = Cikis
"""

import cv2
import numpy as np
import os
import sys

# tools/ klasorunden dogrudan calistirilabilmesi icin proje kokunu ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.vision.vision_engine import HandTracker


def main():
    print("=" * 55)
    print("  CIFT EL ALGILAMA TESTI")
    print("  Bu test scripti, iki el algilama sistemini test eder.")
    print("  Oyuna entegre edildiginde bu dosya kaldirilabilir.")
    print("=" * 55)
    print()
    print("  Q = Cikis")
    print()

    # num_hands=2 ile cift el algilama
    tracker = HandTracker(camera_index=0, dwell_time=2.0, num_hands=2)

    if not tracker.camera_available:
        print("[!] Kamera acilamadi. Test yapilamiyor.")
        return

    window = "Cift El Algilama Testi"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, tracker.frame_width, tracker.frame_height)

    while True:
        frame = tracker.read_frame()
        if frame is None:
            break

        # Tum elleri algila
        hands = tracker.detect_all_hands(frame)

        # El iskeletlerini ciz
        frame = tracker.draw_hand_landmarks(frame)

        h, w = frame.shape[:2]

        # ---- Bilgi Paneli (ust kisim) ----
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 90), (20, 20, 25), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        cv2.putText(frame, "CIFT EL ALGILAMA TESTI",
                    (w // 2 - 180, 30),
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, (80, 180, 255), 2)

        detected_text = f"Algilanan el: {len(hands)}"
        cv2.putText(frame, detected_text, (20, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.putText(frame, "Q = Cikis", (w - 130, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 140, 140), 1)

        # ---- Her el icin detay paneli ----
        panel_colors = [(0, 200, 255), (255, 150, 50)]  # Turuncu, Mavi

        for i, hd in enumerate(hands):
            color = panel_colors[i % 2]

            # Jest durumu metni
            if hd.is_fist:
                jest = "YUMRUK"
                jest_color = (60, 60, 255)  # Kirmizi
            elif hd.is_open:
                jest = "ACIK EL"
                jest_color = (100, 255, 100)  # Yesil
            elif hd.is_pointing:
                jest = "ISARET"
                jest_color = (255, 200, 50)  # Mavi
            else:
                jest = "-"
                jest_color = (180, 180, 180)

            # Sol alt / Sag alt panel
            panel_x = 10 if i == 0 else w // 2 + 10
            panel_y = h - 100

            overlay2 = frame.copy()
            cv2.rectangle(overlay2, (panel_x, panel_y),
                          (panel_x + w // 2 - 20, panel_y + 85),
                          (25, 28, 35), -1)
            cv2.addWeighted(overlay2, 0.7, frame, 0.3, 0, frame)
            cv2.rectangle(frame, (panel_x, panel_y),
                          (panel_x + w // 2 - 20, panel_y + 85),
                          color, 2)

            # Etiket: Sol/Sag
            side = hd.handedness if hd.handedness else f"El {i}"
            cv2.putText(frame, f"{side} El", (panel_x + 10, panel_y + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # Jest
            cv2.putText(frame, f"Jest: {jest}", (panel_x + 10, panel_y + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, jest_color, 1)

            # Koordinat
            if hd.finger_pos:
                coord_text = f"Parmak: ({hd.finger_pos[0]}, {hd.finger_pos[1]})"
                cv2.putText(frame, coord_text, (panel_x + 10, panel_y + 75),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

                # Isaret parmagi ucuna buyuk nokta
                cv2.circle(frame, hd.finger_pos, 10, (0, 255, 128), -1)
                cv2.circle(frame, hd.finger_pos, 12, color, 2)

            # Avuc merkezine nokta
            if hd.palm_pos:
                cv2.circle(frame, hd.palm_pos, 8, (80, 80, 255), -1)

        # El gorulmuyorsa bilgi
        if not hands:
            msg = "Elinizi kameraya gosterin..."
            (tw, _), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cv2.putText(frame, msg, (w // 2 - tw // 2, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 255), 2)

        cv2.imshow(window, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    tracker.release()
    cv2.destroyAllWindows()
    print("[*] Test tamamlandi.")


if __name__ == "__main__":
    main()
