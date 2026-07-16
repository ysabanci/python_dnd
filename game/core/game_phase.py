"""
game_phase.py — Oyun Fazı Enum Tanımları
==========================================
main.py'deki string faz sabitleri (PHASE_NORMAL, PHASE_COMBAT vb.)
bu Enum sınıfına taşındı. Faz geçişlerinde tip güvenliği sağlar.

Aşama 5.3 — S09 çözümü (RESTRUCTURE_PLAN'a göre).

NOT: Bu modül hiçbir şeye bağımlı değildir. Circular import riski SIFIR.
"""

from enum import Enum


class GamePhase(Enum):
    """Oyun fazlarını tanımlayan Enum sınıfı.

    Ana oyun döngüsünde (main.py) kullanılır.
    Her faz, oyunun o andaki durumunu belirler:
    - NORMAL: Keşif, diyalog, seçim yapma
    - SHAPE_CHALLENGE: Şekil çizme mini oyunu
    - FIST_CHALLENGE: Yumruk mini oyunu
    - ENEMY_ATTACK: Düşman saldırı animasyonu
    - WEAPON_SELECT: Silah seçim ekranı
    - DICE_ROLL: Zar atma mini oyunu
    - INVENTORY: Envanter + shop ekranı
    """

    NORMAL = "normal"
    SHAPE_CHALLENGE = "shape_challenge"
    FIST_CHALLENGE = "fist_challenge"
    ENEMY_ATTACK = "enemy_attack"
    WEAPON_SELECT = "weapon_select"
    DICE_ROLL = "dice_roll"
    INVENTORY = "inventory"
