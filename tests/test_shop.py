"""
test_shop.py — ShopSystem birim testleri.

shop_system.py'deki ShopSystem sınıfını doğrudan test eder.
GameState'e bağımlılık yoktur — callback fonksiyonları ile test edilir.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.core.shop_system import ShopSystem
from game.core import game_data


# ================================================================
# Yardımcı: Sahte gold/stat callback'leri
# ================================================================

class FakeWallet:
    """Test için basit altın cüzdanı."""

    def __init__(self, gold: int = 999):
        self.gold = gold
        self.applied_stats = []  # (stat_key, amount) kayıtları

    def deduct_gold(self, cost: int) -> None:
        self.gold -= cost

    def apply_stat(self, stat_key: str, amount: int) -> None:
        self.applied_stats.append((stat_key, amount))


@pytest.fixture
def shop():
    """Başlatılmış bir ShopSystem döndürür."""
    s = ShopSystem()
    s.init()
    return s


@pytest.fixture
def wallet():
    """999 altınlı sahte cüzdan."""
    return FakeWallet(gold=999)


@pytest.fixture
def broke_wallet():
    """0 altınlı sahte cüzdan."""
    return FakeWallet(gold=0)


# ================================================================
# init & get_items
# ================================================================

class TestShopInit:
    """Shop başlatma testleri."""

    def test_init_creates_3_items(self, shop):
        """Init sonrası 3 item olmalı."""
        assert len(shop.get_items()) == 3

    def test_items_have_required_fields(self, shop):
        """Her item stat, amount, cost içermeli."""
        for item in shop.get_items():
            assert "stat" in item
            assert "amount" in item
            assert "cost" in item

    def test_item_stats_valid(self, shop):
        """Stat key'leri geçerli olmalı."""
        valid_stats = {"STR", "DEX", "INT", "DEF", "LUCK"}
        for item in shop.get_items():
            assert item["stat"] in valid_stats

    def test_item_amount_range(self, shop):
        """Amount 2-6 arasında olmalı."""
        for item in shop.get_items():
            assert 2 <= item["amount"] <= 6

    def test_item_cost_formula(self, shop):
        """Cost = SHOP_BASE_COST + amount * 3."""
        for item in shop.get_items():
            expected = game_data.SHOP_BASE_COST + item["amount"] * 3
            assert item["cost"] == expected

    def test_lazy_init(self):
        """get_items ilk çağrıda otomatik init yapmalı."""
        s = ShopSystem()
        # init() çağrılmadan get_items()
        items = s.get_items()
        assert len(items) == 3

    def test_roll_cost_initial(self, shop):
        """Başlangıç roll maliyeti doğru olmalı."""
        assert shop.get_roll_cost() == game_data.SHOP_ROLL_BASE_COST


# ================================================================
# buy
# ================================================================

class TestShopBuy:
    """Satın alma testleri."""

    def test_buy_success(self, shop, wallet):
        """Yeterli altın varsa satın alma başarılı olmalı."""
        item = shop.get_items()[0]
        result = shop.buy(0, gold=wallet.gold,
                          apply_stat_fn=wallet.apply_stat,
                          deduct_gold_fn=wallet.deduct_gold)
        assert result is True
        # Altın düştü
        assert wallet.gold == 999 - item["cost"]
        # Stat uygulandı
        assert len(wallet.applied_stats) == 1
        assert wallet.applied_stats[0] == (item["stat"], item["amount"])

    def test_buy_insufficient_gold(self, shop, broke_wallet):
        """Yetersiz altınla satın alma başarısız olmalı."""
        result = shop.buy(0, gold=broke_wallet.gold,
                          apply_stat_fn=broke_wallet.apply_stat,
                          deduct_gold_fn=broke_wallet.deduct_gold)
        assert result is False
        # Hiçbir şey değişmemeli
        assert broke_wallet.gold == 0
        assert len(broke_wallet.applied_stats) == 0

    def test_buy_invalid_index_negative(self, shop, wallet):
        """Negatif index başarısız olmalı."""
        result = shop.buy(-1, gold=wallet.gold,
                          apply_stat_fn=wallet.apply_stat,
                          deduct_gold_fn=wallet.deduct_gold)
        assert result is False

    def test_buy_invalid_index_overflow(self, shop, wallet):
        """Çok büyük index başarısız olmalı."""
        result = shop.buy(99, gold=wallet.gold,
                          apply_stat_fn=wallet.apply_stat,
                          deduct_gold_fn=wallet.deduct_gold)
        assert result is False

    def test_buy_all_three(self, shop, wallet):
        """3 item de sırayla satın alınabilmeli."""
        items = shop.get_items()
        total_cost = sum(i["cost"] for i in items)
        for i in range(3):
            result = shop.buy(i, gold=wallet.gold,
                              apply_stat_fn=wallet.apply_stat,
                              deduct_gold_fn=wallet.deduct_gold)
            assert result is True
        assert wallet.gold == 999 - total_cost
        assert len(wallet.applied_stats) == 3


# ================================================================
# roll
# ================================================================

class TestShopRoll:
    """Roll (yenileme) testleri."""

    def test_roll_success(self, shop, wallet):
        """Roll başarılı olmalı ve maliyet 2x artmalı."""
        initial_cost = shop.get_roll_cost()
        result = shop.roll(gold=wallet.gold,
                           deduct_gold_fn=wallet.deduct_gold)
        assert result is True
        assert wallet.gold == 999 - initial_cost
        assert shop.get_roll_cost() == initial_cost * 2

    def test_roll_insufficient_gold(self, shop, broke_wallet):
        """Yetersiz altınla roll başarısız olmalı."""
        result = shop.roll(gold=broke_wallet.gold,
                           deduct_gold_fn=broke_wallet.deduct_gold)
        assert result is False
        assert broke_wallet.gold == 0

    def test_roll_regenerates_items(self, shop, wallet):
        """Roll sonrası yeni item'lar üretilmeli."""
        old_items = list(shop.get_items())
        shop.roll(gold=wallet.gold, deduct_gold_fn=wallet.deduct_gold)
        new_items = shop.get_items()
        # Yeni item'lar üretilmiş olmalı (3 tane)
        assert len(new_items) == 3
        # NOT: Rastgele olduğu için aynı olabilir, o yüzden değer değişimi kontrol etmiyoruz

    def test_double_roll_cost_escalation(self, shop, wallet):
        """Her roll'da maliyet 2x artmalı."""
        base = game_data.SHOP_ROLL_BASE_COST
        shop.roll(gold=wallet.gold, deduct_gold_fn=wallet.deduct_gold)
        assert shop.get_roll_cost() == base * 2
        shop.roll(gold=wallet.gold, deduct_gold_fn=wallet.deduct_gold)
        assert shop.get_roll_cost() == base * 4
        shop.roll(gold=wallet.gold, deduct_gold_fn=wallet.deduct_gold)
        assert shop.get_roll_cost() == base * 8

    def test_init_resets_roll_cost(self, shop, wallet):
        """init() sonrası roll maliyeti sıfırlanmalı."""
        shop.roll(gold=wallet.gold, deduct_gold_fn=wallet.deduct_gold)
        assert shop.get_roll_cost() != game_data.SHOP_ROLL_BASE_COST
        shop.init()
        assert shop.get_roll_cost() == game_data.SHOP_ROLL_BASE_COST
