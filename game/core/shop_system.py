"""
shop_system.py — Dükkan Sistemi
==================================
Savaş sonrası stat satın alma sistemi.
Oyuncuya rastgele stat artırma seçenekleri sunar.

GameState'e bağımlılık: Character nesnesi (gold ve event_stats).
Bu modül saf iş mantığı içerir, UI kodu içermez.
"""

import random
from typing import Callable, Dict, List, Optional

from game.core import game_data


class ShopSystem:
    """
    Savaş sonrası stat dükkanı.

    Kullanım:
        shop = ShopSystem()
        shop.init()
        items = shop.get_items()
        success = shop.buy(0, gold=50, apply_stat_fn=state.apply_event_stat,
                           deduct_gold_fn=lambda cost: ...)
    """

    def __init__(self):
        self._items: List[Dict] = []
        self._roll_cost: int = game_data.SHOP_ROLL_BASE_COST

    def init(self) -> None:
        """Shop'u sıfırlar (her savaş sonrası çağrılır)."""
        self._roll_cost = game_data.SHOP_ROLL_BASE_COST
        self._items = self._generate_items()

    def _generate_items(self) -> List[Dict]:
        """3 rastgele stat artırma seçeneği üretir."""
        stat_keys = ["STR", "DEX", "INT", "DEF", "LUCK"]
        items = []
        for _ in range(3):
            sk = random.choice(stat_keys)
            amount = random.randint(2, 6)
            cost = game_data.SHOP_BASE_COST + amount * 3
            items.append({"stat": sk, "amount": amount, "cost": cost})
        return items

    def get_items(self) -> List[Dict]:
        """Mevcut shop seçeneklerini döndürür."""
        if not self._items:
            self.init()
        return self._items

    def get_roll_cost(self) -> int:
        """Roll butonunun mevcut maliyetini döndürür."""
        return self._roll_cost

    def buy(self, index: int, gold: int,
            apply_stat_fn: Callable[[str, int], None],
            deduct_gold_fn: Callable[[int], None]) -> bool:
        """
        Shop'tan stat satın alır.

        Args:
            index: Satın alınacak item'ın indexi (0-2).
            gold: Oyuncunun mevcut altın miktarı.
            apply_stat_fn: Stat bonusu uygulama fonksiyonu (stat_key, amount).
            deduct_gold_fn: Altın düşürme fonksiyonu (cost).

        Returns:
            Başarılı ise True, aksi halde False.
        """
        items = self.get_items()
        if index < 0 or index >= len(items):
            return False
        item = items[index]
        if gold < item["cost"]:
            return False
        deduct_gold_fn(item["cost"])
        apply_stat_fn(item["stat"], item["amount"])
        print(f"[SHOP] {item['stat']} +{item['amount']} satin alindi ({item['cost']} altin)")
        return True

    def roll(self, gold: int,
             deduct_gold_fn: Callable[[int], None]) -> bool:
        """
        Shop seçeneklerini yeniler. Maliyet her seferinde 2x artar.

        Args:
            gold: Oyuncunun mevcut altın miktarı.
            deduct_gold_fn: Altın düşürme fonksiyonu (cost).

        Returns:
            Başarılı ise True, aksi halde False.
        """
        cost = self._roll_cost
        if gold < cost:
            return False
        deduct_gold_fn(cost)
        self._roll_cost = cost * 2
        self._items = self._generate_items()
        print(f"[SHOP] Roll yapildi ({cost} altin). Yeni maliyet: {self._roll_cost}")
        return True
