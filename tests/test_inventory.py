"""
test_inventory.py — InventoryHandler Unit Testleri
====================================================
inventory_handler.py'deki hit-test, dwell zamanlama ve
aksiyon karar mantığını test eder.

Aşama 5.1 — RESTRUCTURE_PLAN'a göre.
"""

from game.core.inventory_handler import InventoryHandler


# ================================================================== #
#  YARDIMCI FONKSIYONLAR                                              #
# ================================================================== #

def make_handler():
    """Temiz bir InventoryHandler oluşturur."""
    return InventoryHandler()


def make_regions(items=None, devam=None, prev=None, next_=None, shop=None, roll=None):
    """Test için regions dict'i oluşturur."""
    return {
        'items': items or [],
        'devam': devam,
        'prev': prev,
        'next': next_,
        'shop': shop or [],
        'roll': roll,
    }


# ================================================================== #
#  RESET TESTLERİ                                                     #
# ================================================================== #

class TestReset:
    """reset() bayrak sıfırlama testleri."""

    def test_reset_clears_all(self):
        """reset() tüm bayrakları sıfırlamalı."""
        h = make_handler()
        h.page = 3
        h.hovered_idx = 2
        h.hovered_devam = True
        h.hovered_prev = True
        h.hovered_next = True
        h.hovered_shop = 1
        h.hovered_roll = True
        h._dwell_target = "item:Kilic"
        h._dwell_start = 99.0

        h.reset()

        assert h.page == 0
        assert h.hovered_idx == -1
        assert h.hovered_devam is False
        assert h.hovered_prev is False
        assert h.hovered_next is False
        assert h.hovered_shop == -1
        assert h.hovered_roll is False
        assert h._dwell_target == ""
        assert h._dwell_start == 0.0


# ================================================================== #
#  HIT-TEST TESTLERİ                                                  #
# ================================================================== #

class TestHitTest:
    """hit_test() parmak-bölge eşleme testleri."""

    def test_no_finger_no_hover(self):
        """Parmak yoksa hover durumu değişmemeli."""
        h = make_handler()
        regions = make_regions(items=[("Kilic", (100, 100, 200, 200))])
        h.hit_test(None, regions)
        assert h.hovered_idx == -1

    def test_finger_on_item(self):
        """Parmak item üzerindeyse hover_idx set edilmeli."""
        h = make_handler()
        regions = make_regions(items=[("Kilic", (100, 100, 200, 200))])
        h.hit_test((150, 150), regions)
        assert h.hovered_idx == 0

    def test_finger_outside_item(self):
        """Parmak item dışındaysa hover_idx -1 kalmalı."""
        h = make_handler()
        regions = make_regions(items=[("Kilic", (100, 100, 200, 200))])
        h.hit_test((50, 50), regions)
        assert h.hovered_idx == -1

    def test_finger_on_devam(self):
        """Parmak devam butonundaysa hovered_devam True."""
        h = make_handler()
        regions = make_regions(devam=(300, 500, 500, 550))
        h.hit_test((400, 525), regions)
        assert h.hovered_devam is True

    def test_finger_on_prev(self):
        """Parmak prev butonundaysa hovered_prev True."""
        h = make_handler()
        regions = make_regions(prev=(10, 500, 60, 550))
        h.hit_test((35, 525), regions)
        assert h.hovered_prev is True

    def test_finger_on_next(self):
        """Parmak next butonundaysa hovered_next True."""
        h = make_handler()
        regions = make_regions(next_=(700, 500, 750, 550))
        h.hit_test((725, 525), regions)
        assert h.hovered_next is True

    def test_finger_on_shop_item(self):
        """Parmak shop item'ındaysa hovered_shop set edilmeli."""
        h = make_handler()
        regions = make_regions(shop=[(0, (100, 600, 300, 650))])
        h.hit_test((200, 625), regions)
        assert h.hovered_shop == 0

    def test_finger_on_roll(self):
        """Parmak roll butonundaysa hovered_roll True."""
        h = make_handler()
        regions = make_regions(roll=(400, 700, 600, 750))
        h.hit_test((500, 725), regions)
        assert h.hovered_roll is True

    def test_second_item_hit(self):
        """İkinci item'a parmak basınca hovered_idx=1."""
        h = make_handler()
        regions = make_regions(items=[
            ("Kilic", (100, 100, 200, 140)),
            ("Balta", (100, 150, 200, 190)),
        ])
        h.hit_test((150, 170), regions)
        assert h.hovered_idx == 1


# ================================================================== #
#  DWELL TESTLERİ                                                     #
# ================================================================== #

class TestDwell:
    """update_dwell() zamanlama ve aksiyon testleri."""

    def test_no_hover_no_progress(self):
        """Hover yoksa progress 0."""
        h = make_handler()
        regions = make_regions()
        h.update_dwell(100.0, regions)
        assert h.dwell_progress == 0.0

    def test_dwell_progress_partial(self):
        """Dwell yarıda → progress ~0.5."""
        h = make_handler()
        regions = make_regions(devam=(0, 0, 100, 100))
        h.hovered_devam = True

        # Başlat
        h.update_dwell(100.0, regions)
        # Yarıya gel (devam = 1.5 saniye)
        h.update_dwell(100.75, regions)

        assert 0.4 <= h.dwell_progress <= 0.6

    def test_dwell_completes_close_inventory(self):
        """Devam dwell tamamlanınca close_inventory aksiyonu."""
        h = make_handler()
        regions = make_regions(devam=(0, 0, 100, 100))
        h.hovered_devam = True

        h.update_dwell(100.0, regions)
        h.update_dwell(101.6, regions)  # 1.6 > 1.5 saniye

        action = h.consume_action()
        assert action is not None
        assert action["type"] == "close_inventory"

    def test_dwell_completes_page_prev(self):
        """Prev dwell tamamlanınca page_change aksiyonu."""
        h = make_handler()
        h.page = 2
        regions = make_regions(prev=(0, 0, 50, 50))
        h.hovered_prev = True

        h.update_dwell(100.0, regions)
        h.update_dwell(100.9, regions)  # 0.9 > 0.8 saniye

        action = h.consume_action()
        assert action is not None
        assert action["type"] == "page_change"
        assert h.page == 1

    def test_dwell_completes_page_next(self):
        """Next dwell tamamlanınca sayfa artar."""
        h = make_handler()
        h.page = 0
        regions = make_regions(next_=(0, 0, 50, 50))
        h.hovered_next = True

        h.update_dwell(100.0, regions)
        h.update_dwell(100.9, regions)

        action = h.consume_action()
        assert action is not None
        assert action["type"] == "page_change"
        assert h.page == 1

    def test_dwell_completes_toggle_equip(self):
        """Item dwell tamamlanınca toggle_equip aksiyonu."""
        h = make_handler()
        regions = make_regions(items=[("Kilic", (0, 0, 100, 50))])
        h.hovered_idx = 0

        h.update_dwell(100.0, regions)
        h.update_dwell(101.3, regions)  # 1.3 > 1.2 saniye

        action = h.consume_action()
        assert action is not None
        assert action["type"] == "toggle_equip"
        assert action["weapon"] == "Kilic"

    def test_dwell_completes_shop_buy(self):
        """Shop item dwell tamamlanınca shop_buy aksiyonu."""
        h = make_handler()
        regions = make_regions(shop=[(2, (0, 0, 100, 50))])
        h.hovered_shop = 2

        h.update_dwell(100.0, regions)
        h.update_dwell(101.1, regions)  # 1.1 > 1.0 saniye

        action = h.consume_action()
        assert action is not None
        assert action["type"] == "shop_buy"
        assert action["index"] == 2

    def test_dwell_completes_shop_roll(self):
        """Roll dwell tamamlanınca shop_roll aksiyonu."""
        h = make_handler()
        regions = make_regions(roll=(0, 0, 100, 50))
        h.hovered_roll = True

        h.update_dwell(100.0, regions)
        h.update_dwell(101.1, regions)

        action = h.consume_action()
        assert action is not None
        assert action["type"] == "shop_roll"

    def test_target_change_resets_dwell(self):
        """Hedef değişince dwell sıfırlanır."""
        h = make_handler()
        regions = make_regions(
            items=[("Kilic", (0, 0, 100, 50))],
            devam=(200, 200, 300, 250),
        )

        # İlk: item hover
        h.hovered_idx = 0
        h.update_dwell(100.0, regions)
        h.update_dwell(100.5, regions)
        assert h.dwell_progress > 0

        # Hedef değişimi: devam'a geç
        h.hovered_idx = -1
        h.hovered_devam = True
        h.update_dwell(101.0, regions)

        # Progress sıfırlanmış olmalı (yeni hedef)
        assert h.dwell_progress < 0.1

    def test_prev_does_not_go_below_zero(self):
        """page=0 iken prev page'i 0'da tutar."""
        h = make_handler()
        h.page = 0
        regions = make_regions(prev=(0, 0, 50, 50))
        h.hovered_prev = True

        h.update_dwell(100.0, regions)
        h.update_dwell(100.9, regions)

        action = h.consume_action()
        assert h.page == 0


# ================================================================== #
#  CONSUME_ACTION TESTLERİ                                            #
# ================================================================== #

class TestConsumeAction:
    """consume_action() aksiyon tüketme testleri."""

    def test_consume_returns_none_when_empty(self):
        """Aksiyon yoksa None döner."""
        h = make_handler()
        assert h.consume_action() is None

    def test_consume_clears_after_read(self):
        """Aksiyon bir kez okunduktan sonra None döner."""
        h = make_handler()
        regions = make_regions(devam=(0, 0, 100, 100))
        h.hovered_devam = True
        h.update_dwell(100.0, regions)
        h.update_dwell(101.6, regions)

        action1 = h.consume_action()
        action2 = h.consume_action()

        assert action1 is not None
        assert action2 is None


# ================================================================== #
#  RESET_HOVER TESTLERİ                                               #
# ================================================================== #

class TestResetHover:
    """reset_hover() hover sıfırlama testleri."""

    def test_reset_hover_clears_all(self):
        """reset_hover() sadece hover bayraklarını sıfırlar, page'e dokunmaz."""
        h = make_handler()
        h.page = 5
        h.hovered_idx = 3
        h.hovered_devam = True
        h.hovered_shop = 1

        h.reset_hover()

        assert h.hovered_idx == -1
        assert h.hovered_devam is False
        assert h.hovered_shop == -1
        assert h.page == 5  # page değişmemeli
