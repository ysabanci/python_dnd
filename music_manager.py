"""
music_manager.py - Oyun Müzik Yöneticisi
==========================================
Her karakter sınıfı için ayrı müzik dosyası yönetir.
Savaş modunda ortak savaş müziği çalar, savaştan çıkınca
sınıf müziğine geri döner.

Beklenen dosya yapisi (music/ klasoru):
  music/savasci.mp3
  music/buyucu.mp3
  music/okcu.mp3
  music/hirsiz.mp3
  music/savas.mp3
"""

import os
from typing import Optional

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("[!] pygame bulunamadi. Muzik sistemi devre disi.")


class MusicManager:
    """
    Oyun müzik yöneticisi.

    Kullanım:
        manager = MusicManager()
        manager.play_class_music("Savasci")   # Sınıf müziği başlat
        manager.play_battle_music()            # Savaş müziğine geç
        manager.resume_class_music()           # Sınıf müziğine geri dön
    """

    # Sınıf -> müzik dosyası eşlemesi
    CLASS_MUSIC = {
        "Savasci": "savasci.mp3",
        "Buyucu": "buyucu.mp3",
        "Okcu": "okcu.mp3",
        "Hirsiz": "hirsiz.mp3",
    }

    BATTLE_MUSIC = "savas.mp3"

    # Ses seviyeleri
    CLASS_VOLUME = 0.4
    BATTLE_VOLUME = 0.5
    FADE_MS = 1500  # Geçiş süresi (ms)

    def __init__(self):
        self._initialized = False
        self._current_class: Optional[str] = None
        self._is_battle_playing: bool = False
        self._music_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "music"
        )

        if not PYGAME_AVAILABLE:
            return

        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self._initialized = True
            print("[*] Muzik sistemi baslatildi.")
        except Exception as e:
            print(f"[!] Muzik sistemi baslatilamadi: {e}")

    def _get_music_path(self, filename: str) -> Optional[str]:
        """Müzik dosyasının tam yolunu döndürür. Yoksa None."""
        path = os.path.join(self._music_dir, filename)
        if os.path.exists(path):
            return path
        print(f"[!] Muzik dosyasi bulunamadi: {path}")
        return None

    def play_class_music(self, class_name: str) -> None:
        """Seçilen sınıfın müziğini çalmaya başlar (loop)."""
        if not self._initialized:
            return

        self._current_class = class_name
        self._is_battle_playing = False

        filename = self.CLASS_MUSIC.get(class_name)
        if not filename:
            print(f"[!] Bilinmeyen sinif: {class_name}")
            return

        path = self._get_music_path(filename)
        if not path:
            return

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.CLASS_VOLUME)
            pygame.mixer.music.play(-1, fade_ms=self.FADE_MS)  # -1 = sonsuz loop
            print(f"[♪] Sinif muzigi baslatildi: {class_name} ({filename})")
        except Exception as e:
            print(f"[!] Muzik calinamadi: {e}")

    def play_battle_music(self) -> None:
        """Savaş müziğine geçiş yapar (loop)."""
        if not self._initialized:
            return

        if self._is_battle_playing:
            return  # Zaten savas muzigi caliyorsa tekrar baslatma

        path = self._get_music_path(self.BATTLE_MUSIC)
        if not path:
            return

        try:
            pygame.mixer.music.fadeout(self.FADE_MS)
            # Fadeout bitmesini beklemeden yükle (pygame bunu yönetir)
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.BATTLE_VOLUME)
            pygame.mixer.music.play(-1, fade_ms=self.FADE_MS)
            self._is_battle_playing = True
            print(f"[♪] Savas muzigi baslatildi!")
        except Exception as e:
            print(f"[!] Savas muzigi calinamadi: {e}")

    def resume_class_music(self) -> None:
        """Savaş bittikten sonra sınıf müziğine geri döner."""
        if not self._initialized:
            return

        if not self._is_battle_playing:
            return  # Zaten sinif muzigi caliyorsa bir sey yapma

        if self._current_class:
            self._is_battle_playing = False
            self.play_class_music(self._current_class)
            print(f"[♪] Sinif muzigine geri donuldu: {self._current_class}")

    def stop(self) -> None:
        """Müziği durdurur."""
        if not self._initialized:
            return

        try:
            pygame.mixer.music.fadeout(self.FADE_MS)
            self._is_battle_playing = False
            print("[♪] Muzik durduruldu.")
        except Exception:
            pass

    def set_volume(self, volume: float) -> None:
        """Ses seviyesini ayarlar (0.0 - 1.0)."""
        if not self._initialized:
            return
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

    def cleanup(self) -> None:
        """Müzik sistemini kapatır."""
        if not self._initialized:
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            print("[*] Muzik sistemi kapatildi.")
        except Exception:
            pass
