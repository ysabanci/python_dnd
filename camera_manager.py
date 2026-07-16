"""
camera_manager.py — Paylaşılan Kamera Yöneticisi
==================================================
Kamerayı uygulama ömrü boyunca TEK BİR YERDE açar ve menü ↔ oyun
arasında paylaştırır (S22 fix — Aşama 6.3).

Eski davranış: MenuSystem kendi kamerasını açıp kapatıyor, ardından
DnDGame ayrı bir VideoCapture açıyordu. Kaspersky gibi güvenlik
yazılımları her VideoCapture açılışında izin bildirimi gösterdiği
için kullanıcı sürekli uyarı alıyordu.

Yeni davranış: main() tek bir CameraManager oluşturur, hem menüye hem
oyuna geçirir. Aynı index istendiği sürece kamera bir kez açılır ve
açık kalır; sadece index değişirse yeniden açılır.
"""

from typing import Optional, Tuple

import cv2


class CameraManager:
    """Uygulama genelinde tek VideoCapture nesnesi yönetir."""

    def __init__(self) -> None:
        self._cap: Optional[cv2.VideoCapture] = None
        self._index: Optional[int] = None

    @property
    def index(self) -> Optional[int]:
        """Şu an açık olan kamera indexi (kapalıysa None)."""
        return self._index

    def get(self, index: int) -> Optional[cv2.VideoCapture]:
        """
        İstenen indexteki kamerayı döndürür.

        Aynı index zaten açıksa mevcut nesne döner — kamera YENİDEN
        AÇILMAZ (güvenlik yazılımı bildirimi tetiklenmez). Farklı bir
        index istenirse eski kamera kapatılıp yenisi açılır.

        Returns:
            Açık VideoCapture veya kamera açılamazsa None.
        """
        if (self._cap is not None and self._index == index
                and self._cap.isOpened()):
            return self._cap

        self.release()
        try:
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                cap.release()
                return None
        except Exception as e:
            print(f"[!] Kamera {index} acilirken hata: {e}")
            return None

        # Standart kamera ayarları (eski HandTracker/MenuSystem ile aynı)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._cap = cap
        self._index = index
        print(f"[*] Kamera {index} acildi (paylasilan).")
        return cap

    def test(self, index: int) -> Tuple[bool, str]:
        """
        Kamerayı test eder ve (başarılı_mı, mesaj) döndürür.

        İstenen index zaten açık olan kameraysa yeniden açmadan bir kare
        okuyarak doğrular. Farklı bir indexse o kameraya geçmeyi dener
        (başarısız olursa çağıran taraf eski indexe geri dönmeli).
        """
        if (self._cap is not None and self._index == index
                and self._cap.isOpened()):
            ret, _ = self._cap.read()
            if ret:
                return True, f"Basarili! Kamera {index} calisiyor."
            return False, f"Hata: Kamera {index} goruntu vermiyor."

        cap = self.get(index)
        if cap is None:
            return False, f"Hata: Kamera {index} acilamadi."
        ret, _ = cap.read()
        if ret:
            return True, f"Basarili! Kamera {index} calisiyor."
        return False, f"Hata: Kamera {index} goruntu vermiyor."

    def release(self) -> None:
        """Açık kamerayı kapatır (uygulama çıkışında çağrılır)."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
            self._index = None
