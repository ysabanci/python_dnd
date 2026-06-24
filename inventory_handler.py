"""
inventory_handler.py — Envanter Ekranı Karar Mantığı
=====================================================
main.py'deki _handle_inventory() metodunun saf hesaplama ve
karar mantığını barındırır. UI çağrıları (draw_inventory,
cv2.imshow) main.py wrapper'ında kalır.

NOT: Bu modül cv2, ui_renderer veya tracker referansı İÇERMEZ.

Aşama 5.1 — RESTRUCTURE_PLAN'a göre.
"""

from typing import Dict, Any, List, Tuple, Optional


class InventoryHandler:
    """
    Envanter ekranındaki hit-test, dwell zamanlama ve aksiyon kararlarını
    yönetir. UI'dan bağımsız olarak test edilebilir.

    main.py wrapper'ı şu sırayla kullanır:
    1. handler.reset_hover()             — her frame'de hover sıfırla
    2. handler.hit_test(finger, regions) — parmak hangi bölgede
    3. handler.update_dwell(now)         — dwell ilerlemesini güncelle
    4. handler.consume_action()          — tetiklenen aksiyon varsa al
    """

    # Sabitler
    DWELL_ITEM = 1.2       # Item equip/unequip süresi (saniye)
    DWELL_DEVAM = 1.5      # Devam butonu süresi
    DWELL_PAGE = 0.8       # Prev/Next sayfa değiştirme süresi
    DWELL_SHOP = 1.0       # Shop satın alma ve roll süresi

    def __init__(self) -> None:
        """Envanter handler'ını başlatır."""
        self.reset()

    def reset(self) -> None:
        """Tüm envanter durumunu sıfırlar."""
        self.page: int = 0

        # Hover durumu (her frame'de güncellenir)
        self.hovered_idx: int = -1
        self.hovered_devam: bool = False
        self.hovered_prev: bool = False
        self.hovered_next: bool = False
        self.hovered_shop: int = -1
        self.hovered_roll: bool = False

        # Dwell durumu
        self._dwell_target: str = ""
        self._dwell_start: float = 0.0
        self._dwell_progress: float = 0.0

        # Tetiklenen aksiyon (consume_action ile alınır)
        self._pending_action: Optional[Dict[str, Any]] = None

        # Regions cache — önceki frame'in regions bilgisi (5.4 optimizasyonu)
        # draw_inventory'nin çift çağrılmasını önler
        self._last_regions: Dict[str, Any] = {
            'items': [], 'devam': None, 'prev': None,
            'next': None, 'shop': [], 'roll': None
        }

    @property
    def dwell_progress(self) -> float:
        """Mevcut dwell ilerlemesi (0.0 - 1.0)."""
        return self._dwell_progress

    def reset_hover(self) -> None:
        """Her frame başında hover durumlarını sıfırlar."""
        self.hovered_idx = -1
        self.hovered_devam = False
        self.hovered_prev = False
        self.hovered_next = False
        self.hovered_shop = -1
        self.hovered_roll = False

    def hit_test(
        self,
        finger_pos: Optional[Tuple[int, int]],
        regions: Dict[str, Any],
    ) -> None:
        """
        Parmak pozisyonunu UI bölgeleriyle karşılaştırarak hover durumunu
        günceller.

        Args:
            finger_pos: (x, y) parmak koordinatı veya None.
            regions: draw_inventory'den dönen bölge sözlüğü:
                - 'items': [(item_name, (x1,y1,x2,y2)), ...]
                - 'devam': (x1,y1,x2,y2) veya None
                - 'prev': (x1,y1,x2,y2) veya None
                - 'next': (x1,y1,x2,y2) veya None
                - 'shop': [(shop_idx, (x1,y1,x2,y2)), ...]
                - 'roll': (x1,y1,x2,y2) veya None
        """
        if not finger_pos:
            return

        fx, fy = finger_pos

        # Item satırları
        for i, (item_name, (x1, y1, x2, y2)) in enumerate(regions.get('items', [])):
            if x1 <= fx <= x2 and y1 <= fy <= y2:
                self.hovered_idx = i
                break

        # Devam butonu
        if regions.get('devam'):
            dx1, dy1, dx2, dy2 = regions['devam']
            if dx1 <= fx <= dx2 and dy1 <= fy <= dy2:
                self.hovered_devam = True

        # Prev/Next butonları
        if regions.get('prev'):
            px1, py1, px2, py2 = regions['prev']
            if px1 <= fx <= px2 and py1 <= fy <= py2:
                self.hovered_prev = True

        if regions.get('next'):
            nx1, ny1, nx2, ny2 = regions['next']
            if nx1 <= fx <= nx2 and ny1 <= fy <= ny2:
                self.hovered_next = True

        # Shop satırları
        for si, (shop_idx, (sx1, sy1, sx2, sy2)) in enumerate(regions.get('shop', [])):
            if sx1 <= fx <= sx2 and sy1 <= fy <= sy2:
                self.hovered_shop = shop_idx
                break

        # Roll butonu
        if regions.get('roll'):
            rx1, ry1, rx2, ry2 = regions['roll']
            if rx1 <= fx <= rx2 and ry1 <= fy <= ry2:
                self.hovered_roll = True

    def _resolve_current_target(self, regions: Dict[str, Any]) -> str:
        """Mevcut hover durumundan hedef string'ini çözümler."""
        if self.hovered_idx >= 0:
            items_on_page = regions.get('items', [])
            if self.hovered_idx < len(items_on_page):
                item_name = items_on_page[self.hovered_idx][0]
                return f"item:{item_name}"
        elif self.hovered_devam:
            return "devam"
        elif self.hovered_prev:
            return "prev"
        elif self.hovered_next:
            return "next"
        elif self.hovered_shop >= 0:
            return f"shop:{self.hovered_shop}"
        elif self.hovered_roll:
            return "roll"
        return ""

    def _get_dwell_time(self, target: str) -> float:
        """Hedef tipine göre gerekli dwell süresini döndürür."""
        if target in ("prev", "next"):
            return self.DWELL_PAGE
        elif target == "devam":
            return self.DWELL_DEVAM
        elif target.startswith("shop:") or target == "roll":
            return self.DWELL_SHOP
        else:
            return self.DWELL_ITEM

    def update_dwell(self, now: float, regions: Dict[str, Any]) -> None:
        """
        Dwell zamanlayıcısını günceller ve aksiyon tetikler.

        Args:
            now: Şu anki zaman (time.time()).
            regions: draw_inventory'den dönen bölge sözlüğü.
        """
        current_target = self._resolve_current_target(regions)

        # Hedef değiştiyse zamanlayıcıyı sıfırla
        if current_target != self._dwell_target:
            self._dwell_target = current_target
            self._dwell_start = now

        if not current_target:
            self._dwell_progress = 0.0
            return

        dwell_time = self._get_dwell_time(current_target)
        elapsed = now - self._dwell_start
        self._dwell_progress = min(elapsed / dwell_time, 1.0)

        if self._dwell_progress >= 1.0:
            self._trigger_action(current_target, now)

    def _trigger_action(self, target: str, now: float) -> None:
        """
        Dwell tamamlandığında aksiyonu tetikler.

        Aksiyon bir dict olarak pending_action'a kaydedilir.
        main.py wrapper'ı consume_action() ile alır ve side-effect'leri
        (state.toggle_equipped, state.shop_buy vb.) uygular.
        """
        if target == "devam":
            self._pending_action = {"type": "close_inventory"}
        elif target == "prev":
            self.page = max(0, self.page - 1)
            self._pending_action = {"type": "page_change", "page": self.page}
        elif target == "next":
            self.page += 1
            self._pending_action = {"type": "page_change", "page": self.page}
        elif target.startswith("item:"):
            weapon = target[5:]
            self._pending_action = {"type": "toggle_equip", "weapon": weapon}
        elif target.startswith("shop:"):
            shop_idx = int(target[5:])
            self._pending_action = {"type": "shop_buy", "index": shop_idx}
        elif target == "roll":
            self._pending_action = {"type": "shop_roll"}

        # Dwell sıfırla
        self._dwell_start = now
        self._dwell_target = ""

    def consume_action(self) -> Optional[Dict[str, Any]]:
        """
        Tetiklenen aksiyonu döndürür ve sıfırlar.

        Returns:
            dict veya None. Örnek sonuçlar:
                {"type": "close_inventory"}
                {"type": "page_change", "page": 2}
                {"type": "toggle_equip", "weapon": "Kılıç"}
                {"type": "shop_buy", "index": 0}
                {"type": "shop_roll"}
        """
        action = self._pending_action
        self._pending_action = None
        return action

    def cache_regions(self, regions: Dict[str, Any]) -> None:
        """draw_inventory'den dönen regions bilgisini cache'ler.

        Bir sonraki frame'de hit_test() bu cache'i kullanarak
        draw_inventory'nin iki kez çağrılmasını önler.
        """
        self._last_regions = regions

    def get_cached_regions(self) -> Dict[str, Any]:
        """Son frame'in regions bilgisini döndürür.

        İlk frame'de boş regions döner (henüz çizim yapılmamış).
        """
        return self._last_regions
