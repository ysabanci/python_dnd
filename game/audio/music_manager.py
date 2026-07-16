"""
music_manager.py - Oyun Müzik Yöneticisi
==========================================
Theme_Lores bazli muzik sistemi.
Her tema (lokasyon) icin ayri muzik dosyasi yonetir.
Savas modunda ortak savas muzigi calar, savastan cikinca
tema muzigine geri doner.

Beklenen dosya yapisi (assets/music/ klasoru):
  assets/music/karanlik_magara.mp3
  assets/music/gizemli_orman.mp3
  assets/music/kaotik_uzay.mp3
  assets/music/ruhlar_cehennemi.mp3
  assets/music/sonsuz_col.mp3
  assets/music/batan_sehir.mp3
  assets/music/ejderha_yuvasi.mp3
  assets/music/buzul_sarayi.mp3
  assets/music/hayalet_kasabasi.mp3
  assets/music/lanetli_kale.mp3
  assets/music/savas.mp3
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
    Oyun müzik yöneticisi (tema bazli).

    Kullanım:
        manager = MusicManager()
        manager.play_theme_music("Karanlik Magara")   # Tema müziği başlat
        manager.play_battle_music()                    # Savaş müziğine geç
        manager.resume_class_music()                   # Tema müziğine geri dön
    """

    # Tema -> müzik dosyası eşlemesi (tum POSSIBLE_LOCATIONS)
    THEME_MUSIC = {
        "Karanlik Magara": "karanlik_magara.mp3",
        "Gizemli Orman": "gizemli_orman.mp3",
        "Kaotik Uzay": "kaotik_uzay.mp3",
        "Ruhlar Cehennemi": "ruhlar_cehennemi.mp3",
        "Sonsuz Col": "sonsuz_col.mp3",
        "Batan Sehir": "batan_sehir.mp3",
        "Ejderha Yuvasi": "ejderha_yuvasi.mp3",
        "Buzul Sarayi": "buzul_sarayi.mp3",
        "Hayalet Kasabasi": "hayalet_kasabasi.mp3",
        "Lanetli Kale": "lanetli_kale.mp3",
    }

    BATTLE_MUSIC = "savas.mp3"

    # Ses seviyeleri
    THEME_VOLUME = 0.4
    BATTLE_VOLUME = 0.5
    FADE_MS = 1500  # Geçiş süresi (ms)

    def __init__(self):
        self._initialized = False
        self._current_theme: Optional[str] = None
        self._is_battle_playing: bool = False
        # Muzik dosyalari proje kokundeki assets/music/ altindadir
        _project_root = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        self._music_dir = os.path.join(_project_root, "assets", "music")

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

    def play_theme_music(self, theme_name: str) -> None:
        """Seçilen temanın müziğini çalmaya başlar (loop)."""
        if not self._initialized:
            return

        self._current_theme = theme_name
        self._is_battle_playing = False

        filename = self.THEME_MUSIC.get(theme_name)
        if not filename:
            print(f"[!] Bilinmeyen tema: {theme_name}")
            return

        path = self._get_music_path(filename)
        if not path:
            return

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.THEME_VOLUME)
            pygame.mixer.music.play(-1, fade_ms=self.FADE_MS)
            print(f"[♪] Tema muzigi baslatildi: {theme_name} ({filename})")
        except Exception as e:
            print(f"[!] Muzik calinamadi: {e}")

    # Geriye donuk uyumluluk - eski class-based cagrilar icin
    def play_class_music(self, class_name: str) -> None:
        """Eski API uyumlulugu - tema muzigini calar veya sessiz kalir."""
        if self._current_theme:
            self.play_theme_music(self._current_theme)

    def play_battle_music(self) -> None:
        """Savaş müziğine geçiş yapar (loop)."""
        if not self._initialized:
            return

        if self._is_battle_playing:
            return

        path = self._get_music_path(self.BATTLE_MUSIC)
        if not path:
            return

        try:
            pygame.mixer.music.fadeout(self.FADE_MS)
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.BATTLE_VOLUME)
            pygame.mixer.music.play(-1, fade_ms=self.FADE_MS)
            self._is_battle_playing = True
            print(f"[♪] Savas muzigi baslatildi!")
        except Exception as e:
            print(f"[!] Savas muzigi calinamadi: {e}")

    def resume_class_music(self) -> None:
        """Savaş bittikten sonra tema müziğine geri döner."""
        if not self._initialized:
            return

        if not self._is_battle_playing:
            return

        if self._current_theme:
            self._is_battle_playing = False
            self.play_theme_music(self._current_theme)
            print(f"[♪] Tema muzigine geri donuldu: {self._current_theme}")

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
