"""
game_state.py - Oyun Durumu Yöneticisi
========================================
Karakterin canını (HP), envanterini, mevcut konumunu ve
AI'a gönderilecek mesaj geçmişini (memory) yönetir.
Geçmiş çok uzarsa eski mesajları kırpan optimizasyon içerir.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import game_data
from shop_system import ShopSystem


@dataclass
class Character:
    """
    Oyuncu karakterinin temel özelliklerini tutar.

    Attributes:
        name: Karakterin adı.
        char_class: Karakter sınıfı (Savaşçı, Büyücü, vb.).
        hp: Mevcut can puanı.
        max_hp: Maksimum can puanı.
        inventory: Envanter listesi.
        gold: Altın miktarı.
        base_stats: Sinif bazli temel istatistikler.
        event_stats: Olaylardan gelen gecici istatistik bonuslari.
    """
    name: str = "Kahraman"
    char_class: str = "Maceraperest"
    hp: int = 100
    max_hp: int = 100
    inventory: List[str] = field(default_factory=lambda: ["Pasli Kilic", "Mesale"])
    gold: int = 50
    # Temel istatistikler (sinif seciminde atanir)
    base_stats: Dict[str, int] = field(default_factory=lambda: {
        "STR": 10, "DEX": 10, "INT": 10, "DEF": 10, "LUCK": 10
    })
    # Olaylardan gelen kalici bonuslar
    event_stats: Dict[str, int] = field(default_factory=lambda: {
        "STR": 0, "DEX": 0, "INT": 0, "DEF": 0, "LUCK": 0
    })


class GameState:
    """
    Oyunun tüm durumunu merkezi olarak yöneten sınıf.

    Bu sınıf karakter bilgilerini, mevcut konumu, hikaye metnini,
    seçenekleri ve AI ile paylaşılan mesaj geçmişini tutar.
    Bellek yönetimi için geçmiş otomatik olarak kırpılır.

    Attributes:
        character (Character): Oyuncu karakteri.
        current_location (str): Karakterin bulunduğu konum.
        turn_count (int): Toplam tur sayısı.
        current_story (str): Ekranda gösterilen mevcut hikaye metni.
        current_options (dict): Ekrandaki 4 seçenek.
        is_game_over (bool): Oyun bitip bitmediği.
        game_over_reason (str): Oyunun bitiş nedeni.
    """

    # Mesaj geçmişi bu sayıyı aştığında kırpma uygulanır
    MAX_MEMORY_MESSAGES = 20
    # Kırpma sonrası bırakılacak mesaj sayısı (sistem mesajı hariç)
    TRIM_TO_MESSAGES = 12

    # ----- Statik veriler game_data.py'den import edilir -----
    THEME_LORE = game_data.THEME_LORE
    CLASS_DATA = game_data.CLASS_DATA
    CLASS_BASE_STATS = game_data.CLASS_BASE_STATS
    WEAPON_DATA = game_data.WEAPON_DATA
    WEAPON_STATS = game_data.WEAPON_STATS
    STAT_NAMES = game_data.STAT_NAMES
    CLASS_BONUS = game_data.CLASS_BONUS
    CLASS_ADVANTAGE_KEY = game_data.CLASS_ADVANTAGE_KEY
    POSSIBLE_LOCATIONS = game_data.POSSIBLE_LOCATIONS

    def __init__(self, character: Optional[Character] = None):
        """
        GameState'i başlatır.

        Args:
            character: Oyuncu karakteri. Verilmezse varsayılan karakter oluşturulur.
        """
        self.character = character or Character()
        self.current_location: str = "Bilinmeyen Diyar"
        self.turn_count: int = 0

        # ----- Shop Sistemi (delege) -----
        self._shop = ShopSystem()

        # ----- Hikaye ve Seçenekler -----
        self.current_story: str = "Macera başlamak üzere..."
        self.current_options: Dict[str, str] = {
            "sol_ust": "...",
            "sag_ust": "...",
            "sol_alt": "...",
            "sag_alt": "...",
        }
        self.active_option_count: int = 4  # 2, 3, veya 4 secenek

        # ----- Oyun Durumu Bayrakları -----
        self.is_game_over: bool = False
        self.game_over_reason: str = ""
        self.is_waiting_for_ai: bool = False
        self.is_startup: bool = True
        self.startup_step: int = 0  # 0=class, 1=weapon, 2=destination
        self.current_theme: str = ""
        self.current_feedback: str = ""

        # ----- AI Tarafından Yönetilen Mod -----
        self.current_mode: str = "kesif"  # "kesif" | "savas" | "diyalog"
        self.pending_combat_result: Optional[Dict[str, Any]] = None

        # ----- Dusman HP (savas modu icin) -----
        self.enemy_hp: int = 0
        self.enemy_max_hp: int = 100

        # ----- Silah ve Envanter -----
        self.equipped_weapon: str = ""
        self.equipped_items: List[str] = []  # Savas icin secilen max 4 silah

        # ----- Zar Mekaniği -----
        self.dice_required: bool = False
        self.dice_option_key: str = ""  # Hangi butonun zar gerektirdigi

        # ----- Bekleyen Ganimet (otomatik eklenmez, oyuncu secmeli) -----
        self.pending_loot: str = ""  # AI'dan gelen ama henuz alinmamis esya

        # ----- Dunya Takibi (World State) -----
        self.visited_locations: List[str] = []  # Gezilen alt bolgeler (AI'dan gelir)
        self.location_history: List[str] = []   # Tur bazli konum gecmisi (geri don icin)
        self.npc_met: List[str] = []             # Konusulan NPC'ler
        self.interactions: List[str] = []        # Onemli etkilesimler (max 20)
        self.current_sub_location: str = ""      # Alt bolge (AI'dan gelir)
        self._can_go_back: bool = False           # Geri donulebilir mi

        # ----- Rastgele Savas Zamanlayici -----
        import random
        self._next_combat_turn: int = random.randint(5, 10)  # Ilk savas 5-10. turda
        self._last_combat_turn: int = 0
        self._in_combat: bool = False

        # ----- AI Mesaj Geçmişi (Memory) -----
        self._message_history: List[Dict[str, str]] = []
        self._init_system_prompt()

    # ------------------------------------------------------------------ #
    #  GENEL (PUBLIC) METODLAR                                            #
    # ------------------------------------------------------------------ #

    def update_from_ai_response(self, ai_response: Dict[str, Any]) -> None:
        """
        AI'dan gelen JSON yanıtına göre oyun durumunu günceller.

        Beklenen format:
        {
            "hikaye_metni": "...",
            "feedback": "...",
            "mod": "kesif|savas|diyalog",
            "hp_degisim": 0,
            "altin_degisim": 0,
            "secenekler": {
                "sol_ust": "...",
                "sag_ust": "...",
                "sol_alt": "...",
                "sag_alt": "..."
            }
        }

        Args:
            ai_response: AI'dan gelen ayrıştırılmış JSON sözlüğü.
        """
        self.current_story = ai_response.get("hikaye_metni", "Hikaye alınamadı...")
        self.current_feedback = ai_response.get("feedback", "")

        # ----- Mod guncelleme (AI oyun akisini yonetiyor) -----
        new_mode = ai_response.get("mod", "kesif")
        just_entered_combat = False
        if new_mode in ("kesif", "savas", "diyalog"):
            just_entered_combat = (new_mode == "savas" and self.current_mode != "savas")
            self.current_mode = new_mode

        # Dusman HP - savasa ilk girildiginde baslat
        if just_entered_combat:
            self.enemy_hp = self.enemy_max_hp

        secenekler = ai_response.get("secenekler", {})
        secenek_sayisi = ai_response.get("secenek_sayisi", 4)

        # Savas modunda daima 4 secenek
        if self.current_mode == "savas":
            secenek_sayisi = 4

        # Secenek sayisini 2-4 arasi sinirla
        secenek_sayisi = max(2, min(4, secenek_sayisi))
        self.active_option_count = secenek_sayisi

        # Secenekleri ata (kullanilmayanlar bos kalir)
        option_keys = ["sol_ust", "sag_ust", "sol_alt", "sag_alt"]
        self.current_options = {}
        actual_count = 0
        for i, key in enumerate(option_keys):
            if i < secenek_sayisi:
                val = secenekler.get(key, "")
                # '...' veya bos secenekleri filtrele
                if val and val.strip() != "..." and val.strip() != "":
                    self.current_options[key] = val
                    actual_count += 1
                else:
                    self.current_options[key] = ""
            else:
                self.current_options[key] = ""

        # Gercek secenek sayisini guncelle (filtrelenmis)
        if actual_count < secenek_sayisi:
            # Secenekleri yeniden duz sirala (bosluksuz)
            filled = [(k, v) for k, v in self.current_options.items() if v]
            self.current_options = {}
            for i, key in enumerate(option_keys):
                if i < len(filled):
                    self.current_options[key] = filled[i][1]
                else:
                    self.current_options[key] = ""
            actual_count = len(filled)

        self.active_option_count = max(2, actual_count)

        self.turn_count += 1

        # ----- HP degisimi (guardlar ile korunmus) -----
        hp_change = ai_response.get("hp_degisim", 0)

        # Guard 1: Diyalog modunda HP asla dusmesin
        if self.current_mode == "diyalog":
            hp_change = 0
        # Guard 2: Savasa ilk girildiginde HP dusmesin
        elif just_entered_combat:
            hp_change = 0
        # Guard 3: Savas modunda HP degisimi challenge+dusman sistemi tarafindan yonetilir
        elif self.current_mode == "savas":
            hp_change = 0

        if isinstance(hp_change, (int, float)) and hp_change != 0:
            self.modify_hp(int(hp_change))

        # Altin degisimi (diyalogda da olabilir)
        gold_change = ai_response.get("altin_degisim", 0)
        if isinstance(gold_change, (int, float)) and gold_change != 0:
            self.modify_gold(int(gold_change))

        # ----- Zar mekani\u011fi -----
        self.dice_required = bool(ai_response.get("zar_gerekli", False))
        self.dice_option_key = ai_response.get("zar_secenegi", "")
        # Savas modunda zar kullanilmaz
        if self.current_mode == "savas":
            self.dice_required = False
            self.dice_option_key = ""

        # ----- Yeni esya (OTOMATIK EKLENMEZ - beklemede tutulur) -----
        yeni_esya = ai_response.get("yeni_esya", "")
        if yeni_esya and isinstance(yeni_esya, str) and yeni_esya.strip():
            yeni_esya = yeni_esya.strip()
            if yeni_esya not in self.character.inventory:
                self.pending_loot = yeni_esya
                print(f"[~] Ganimet beklemede: {yeni_esya} (oyuncu secmeli)")

        # ----- Stat degisimleri (AI yonetimli) -----
        stat_degisim = ai_response.get("stat_degisim", {})
        if isinstance(stat_degisim, dict):
            for stat_key, amount in stat_degisim.items():
                stat_key_upper = stat_key.upper()
                if stat_key_upper in self.character.event_stats and isinstance(amount, (int, float)):
                    amount = int(amount)
                    if amount != 0:
                        self.apply_event_stat(stat_key_upper, amount)
                        name = self.STAT_NAMES.get(stat_key_upper, stat_key_upper)
                        sign = "+" if amount > 0 else ""
                        stat_msg = f"{name} {sign}{amount}"
                        if self.current_feedback:
                            self.current_feedback += f" | {stat_msg}"
                        else:
                            self.current_feedback = stat_msg

        # Yedek: hikaye metni icindeki tag'lerden de oku
        self._parse_hp_changes(ai_response)

        # ----- Dunya Takibi (World State) -----
        # Alt bolge
        sub_loc = ai_response.get("alt_bolge", "")
        if sub_loc and isinstance(sub_loc, str) and sub_loc.strip():
            sub_loc = sub_loc.strip()
            # Konum gecmisine ekle (geri don icin)
            if self.current_sub_location and self.current_sub_location != sub_loc:
                self.location_history.append(self.current_sub_location)
                # Max 10 konum gecmisi tut
                if len(self.location_history) > 10:
                    self.location_history = self.location_history[-10:]
            self.current_sub_location = sub_loc
            if sub_loc not in self.visited_locations:
                self.visited_locations.append(sub_loc)
                # Max 30 konum tut
                if len(self.visited_locations) > 30:
                    self.visited_locations = self.visited_locations[-30:]

        # NPC tespiti
        npc = ai_response.get("npc_adi", "")
        if npc and isinstance(npc, str) and npc.strip():
            npc = npc.strip()
            if npc not in self.npc_met:
                self.npc_met.append(npc)
                if len(self.npc_met) > 20:
                    self.npc_met = self.npc_met[-20:]

        # Onemli etkilesim
        interaction = ai_response.get("etkilesim", "")
        if interaction and isinstance(interaction, str) and interaction.strip():
            self.interactions.append(interaction.strip())
            if len(self.interactions) > 20:
                self.interactions = self.interactions[-20:]

        # Geri donulebilirlik
        self._can_go_back = bool(ai_response.get("geri_donulebilir", False))

        # Savas durumu takibi
        if self.current_mode != "savas" and self._in_combat:
            self._in_combat = False

        # Oyun bitti mi kontrol et
        if self.character.hp <= 0:
            self.is_game_over = True
            self.game_over_reason = "Karakterin cani tukendi!"

    def add_user_choice(self, user_msg: str) -> None:
        """
        Kullanıcının dinamik seçimini mesaj geçmişine ekler.
        """
        self._message_history.append({
            "role": "user",
            "content": user_msg,
        })
        self._optimize_memory()

    def get_dynamic_prompt(self, choice_text: str) -> str:
        """Boss mantigi ve tema ilerleyisi icin dinamik prompt uretir."""
        lore = self.THEME_LORE.get(self.current_theme, "Bilinmeyen bir diyar.")
        prompt = (
            f"Secimim: {choice_text}. Tema: {self.current_theme}. "
            f"Tema Arka Plani: {lore}\n"
            f"Adim No: {self.turn_count + 1}. "
        )
        
        # Tekrari onlemek icin son hikayeyi hatirlat
        if self.current_story:
            short_story = self.current_story[:100] + "..." if len(self.current_story) > 100 else self.current_story
            prompt += f"SON ADIMDA ANLATILAN: '{short_story}'. SAKIN AYNI SEYLERI TEKRAR ETME, HIKAYEYI ILERLET.\n"

        # ----- Savas sonucu bilgisi -----
        if self.pending_combat_result:
            acc = self.pending_combat_result.get("accuracy", 0)
            action = self.pending_combat_result.get("action", "")

            # Savunma farki: basarili savunma hasari tamamen engeller
            if action.lower() in ("savun", "savunma"):
                if acc >= 70:
                    prompt += f"ONEMLI: Oyuncu SAVUNMA yapti ve %{acc:.0f} dogrulukla BASARILI oldu. Hasar tamamen engellendi! hp_degisim=0. "
                elif acc >= 40:
                    prompt += f"ONEMLI: Oyuncu SAVUNMA yapti ama %{acc:.0f} dogrulukla KISMI BASARILI oldu. hp_degisim=0, hasar zaten oyun icinde uygulandi. "
                else:
                    prompt += f"ONEMLI: Oyuncu SAVUNMA yapti ama %{acc:.0f} dogrulukla BASARISIZ oldu. hp_degisim=0, hasar zaten oyun icinde uygulandi. "
            elif action.lower() in ("kac", "kacis"):
                if acc >= 70:
                    prompt += f"ONEMLI: Oyuncu KACMAYI denedi ve %{acc:.0f} dogrulukla BASARILI oldu. Kacis BASARILI! mod='kesif' yap, hp_degisim=0. "
                else:
                    prompt += f"ONEMLI: Oyuncu KACMAYI denedi ama %{acc:.0f} dogrulukla BASARISIZ oldu. Kacamadi! hp_degisim=0, hasar zaten oyun icinde uygulandi. mod='savas' kalsin. "
            else:
                # Saldir / Buyu
                if acc >= 70:
                    prompt += f"ONEMLI: Oyuncu '{action}' hamlesini %{acc:.0f} dogrulukla BASARIYLA gerceklestirdi. Hamle tam etkili olsun. hp_degisim=0, oyuncu hasar almadi. "
                elif acc >= 40:
                    prompt += f"ONEMLI: Oyuncu '{action}' hamlesini %{acc:.0f} dogrulukla KISMI BASARIYLA gerceklestirdi. hp_degisim=0, hasar zaten oyun icinde uygulandi. "
                else:
                    prompt += f"ONEMLI: Oyuncu '{action}' hamlesini %{acc:.0f} dogrulukla BASARISIZ gerceklestirdi. hp_degisim=0, hasar zaten oyun icinde uygulandi. "

            # Dusman HP bilgisi
            prompt += f"Dusman HP: {self.enemy_hp}/{self.enemy_max_hp}. "
            if self.enemy_hp <= 0:
                prompt += "DUSMAN YENILDI! Savasi bitir, mod='kesif' yap, odul ver. "
            self.pending_combat_result = None
        else:
            # Rastgele savas zamanlama
            if self.current_mode == "savas" or self._in_combat:
                # Savas devam ediyor
                turns_in_combat = self.turn_count - self._last_combat_turn
                if turns_in_combat >= 3:
                    prompt += "Boss'u yeniyoruz veya kaciyoruz! Savasi sonlandir ve odul ver. mod'u 'kesif' yap. "
                else:
                    prompt += "Boss savasi devam ediyor. Temaya uygun tehlikeli saldirilar yap. mod='savas'. "
            elif self.turn_count >= self._next_combat_turn:
                import random
                prompt += "KARSIMA TEMA ILE UYUMLU BIR DUSMAN CIKAR! Savas basliyor. mod'u 'savas' yap. "
                self._in_combat = True
                self._last_combat_turn = self.turn_count
                self._next_combat_turn = self.turn_count + random.randint(6, 14)
            else:
                prompt += "Kesfe devam. Gidisat bir onceki adimla baglantili olsun. Temaya uygun yeni bir yere ilerleyelim. "
            
        # Bekleyen ganimet bilgisi
        if self.pending_loot:
            prompt += f"\nBEKLEYEN GANIMET: '{self.pending_loot}' - Oyuncuya bunu alip almayacagini sor. Seceneklerde 'Ganimeti al' ve 'Birak' gibi secenekler sun. yeni_esya BOSBIRAK cunku zaten beklemede."

        # Dunya durumu
        prompt += "\n" + self._get_world_context()
        prompt += "\n" + self.get_character_summary()
        return prompt

    def add_ai_response(self, raw_content: str) -> None:
        """
        AI'dan gelen ham yanıtı mesaj geçmişine ekler.

        Args:
            raw_content: AI'dan gelen ham JSON string.
        """
        self._message_history.append({
            "role": "assistant",
            "content": raw_content,
        })
        self._optimize_memory()

    def get_message_history(self) -> List[Dict[str, str]]:
        """
        AI'a gönderilecek tam mesaj geçmişini döndürür.

        Returns:
            Mesaj sözlüklerinin listesi (role, content).
        """
        return list(self._message_history)

    def get_character_summary(self) -> str:
        """
        Karakterin mevcut durumunun özet metnini döndürür.
        AI'a bağlam sağlamak için kullanılır.

        Returns:
            Karakter durum özeti.
        """
        inv_str = ", ".join(self.character.inventory) if self.character.inventory else "Bos"
        total = self.get_total_stats()
        stat_str = ", ".join(f"{k}:{v}" for k, v in total.items())
        return (
            f"[Karakter Durumu] "
            f"Ad: {self.character.name} | "
            f"Sinif: {self.character.char_class} | "
            f"HP: {self.character.hp}/{self.character.max_hp} | "
            f"Altin: {self.character.gold} | "
            f"Stats: {stat_str} | "
            f"Envanter: {inv_str} | "
            f"Ana Bolge: {self.current_location} | "
            f"Alt Bolge: {self.current_sub_location} | "
            f"Tur: {self.turn_count}"
        )

    def get_total_stats(self) -> Dict[str, int]:
        """Toplam istatistikleri hesaplar: base + equipped weapon stats + event stats."""
        total = dict(self.character.base_stats)
        # Equipped silahlardan bonus
        for weapon in self.equipped_items:
            w_stats = self.get_weapon_stats(weapon)
            for stat_key, stat_val in w_stats.get("stats", {}).items():
                if stat_key in total:
                    total[stat_key] += stat_val
                elif stat_key == "HP":
                    # HP bonusu max_hp'ye eklenir
                    pass  # HP ayri islenir
        # Event bonuslari
        for stat_key, stat_val in self.character.event_stats.items():
            if stat_key in total:
                total[stat_key] += stat_val
        return total

    def get_hp_bonus_from_equipment(self) -> int:
        """Equipped zirhlardan gelen toplam HP bonusunu hesaplar."""
        hp_bonus = 0
        for weapon in self.equipped_items:
            w_stats = self.get_weapon_stats(weapon)
            hp_bonus += w_stats.get("stats", {}).get("HP", 0)
        return hp_bonus

    def get_effective_max_hp(self) -> int:
        """Zirh HP bonusu dahil efektif max HP."""
        return self.character.max_hp + self.get_hp_bonus_from_equipment()

    def get_stat_breakdown(self, stat_key: str) -> Dict[str, int]:
        """Belirli bir stat'in kaynaklarini dondurur (base, weapon, event)."""
        base_val = self.character.base_stats.get(stat_key, 0)
        weapon_val = 0
        for weapon in self.equipped_items:
            w_stats = self.get_weapon_stats(weapon)
            weapon_val += w_stats.get("stats", {}).get(stat_key, 0)
        event_val = self.character.event_stats.get(stat_key, 0)
        return {"base": base_val, "weapon": weapon_val, "event": event_val}

    def apply_event_stat(self, stat_key: str, amount: int) -> None:
        """Olay bazli istatistik bonusu uygular (kalici)."""
        if stat_key in self.character.event_stats:
            self.character.event_stats[stat_key] += amount
            print(f"[STAT] {stat_key} {'+'if amount>=0 else ''}{amount} (event)")

    def get_stat_effect_on_combat(self) -> Dict[str, float]:
        """
        Istatistiklerin savas uzerindeki etkilerini hesaplar.
        Stat cap: 200 (formüller buna göre ölçeklendi).
        """
        total = self.get_total_stats()
        return {
            "attack_bonus": max(0, (total.get("STR", 10) - 10)),
            "magic_bonus": max(0, (total.get("INT", 10) - 10)),
            "defense_reduction": min(0.6, total.get("DEF", 10) * 0.003),
            "dodge_chance": min(0.30, max(0, (total.get("DEX", 10) - 10)) * 0.003),
            "crit_bonus": min(15.0, max(0, (total.get("LUCK", 10) - 10)) * 0.1),
            "extra_turn_bonus": min(0.20, max(0, (total.get("LUCK", 10) - 10)) * 0.002),
            "flee_bonus": min(25.0, max(0, (total.get("DEX", 10) - 10)) * 0.25),
        }

    # ---- SHOP SISTEMI (ShopSystem'e delege edilir) ----
    SHOP_BASE_COST = game_data.SHOP_BASE_COST
    SHOP_ROLL_BASE_COST = game_data.SHOP_ROLL_BASE_COST

    def init_shop(self) -> None:
        """Shop'u sifirlar (her savas sonrasi cagrilir)."""
        self._shop.init()

    def get_shop_items(self) -> list:
        """Mevcut shop seceneklerini dondurur."""
        return self._shop.get_items()

    def get_shop_roll_cost(self) -> int:
        """Roll butonunun mevcut maliyetini dondurur."""
        return self._shop.get_roll_cost()

    def shop_buy(self, index: int) -> bool:
        """Shop'tan stat satin alir. Basarili ise True."""
        return self._shop.buy(
            index=index,
            gold=self.character.gold,
            apply_stat_fn=self.apply_event_stat,
            deduct_gold_fn=lambda cost: setattr(
                self.character, 'gold', self.character.gold - cost),
        )

    def shop_roll(self) -> bool:
        """Shop seceneklerini yeniler. Maliyet her seferinde 2x artar."""
        return self._shop.roll(
            gold=self.character.gold,
            deduct_gold_fn=lambda cost: setattr(
                self.character, 'gold', self.character.gold - cost),
        )

    def modify_hp(self, amount: int) -> None:
        """
        Karakterin HP'sini değiştirir. 0 ile max_hp arasında kalmasını sağlar.

        Args:
            amount: Değişim miktarı (pozitif = iyileşme, negatif = hasar).
        """
        self.character.hp = max(0, min(self.character.max_hp, self.character.hp + amount))

    def apply_class_choice(self, class_name: str) -> None:
        """Karakter sinifini uygular."""
        data = self.CLASS_DATA.get(class_name, {})
        self.character.char_class = class_name
        self.character.hp = data.get("hp", 100)
        self.character.max_hp = data.get("max_hp", 100)
        self.character.gold = data.get("gold", 50)
        # Sinif bazli istatistikleri uygula
        base = self.CLASS_BASE_STATS.get(class_name, {"STR": 10, "DEX": 10, "INT": 10, "DEF": 10, "LUCK": 10})
        self.character.base_stats = dict(base)
        self.character.event_stats = {"STR": 0, "DEX": 0, "INT": 0, "DEF": 0, "LUCK": 0}

    def apply_weapon_choice(self, weapon: str) -> None:
        """Baslangic silahini uygular."""
        self.character.inventory = [weapon, "Mesale"]
        self.equipped_weapon = weapon
        self.equipped_items = [weapon]  # Ilk silahi equip et

    def get_weapon_stats(self, weapon: str = "") -> dict:
        """Silah istatistiklerini dondurur. Bilinmeyen silahlar icin isimden tahmin eder."""
        if not weapon:
            weapon = self.equipped_weapon
        stats = self.WEAPON_STATS.get(weapon)
        if stats:
            return stats
        # AI tarafindan verilen dinamik silah - isimden tahmin et
        import hashlib
        weapon_lower = weapon.lower()
        magic_keywords = ("asa", "degnek", "grimoire", "buyu", "ates", "buz",
                          "yildirim", "isik", "karanlik", "ruh", "lanetli",
                          "zehir", "sihirli")
        armor_keywords = ("zirh", "kalkan", "miğfer", "migfer", "pelerini",
                          "pelerin", "koruma", "yelek", "eldiven", "cizme",
                          "kask", "armor", "shield")
        is_magic = any(kw in weapon_lower for kw in magic_keywords)
        is_armor = any(kw in weapon_lower for kw in armor_keywords)
        # Deterministik seed (aynı isim her zaman aynı statları verir)
        h = int(hashlib.md5(weapon.encode()).hexdigest()[:8], 16)
        if is_armor:
            # Zırh: HP ve DEF bonusu, düşük hasar
            hp_bonus = 5 + (h % 20)
            def_val = 3 + (h % 8)
            return {"bonus": 1 + (h % 3), "type": "fiziksel",
                    "stats": {"DEF": def_val, "HP": hp_bonus}}
        elif is_magic:
            int_val = 3 + (h % 6)
            luck_val = -1 + (h % 4)
            return {"bonus": 5 + (h % 8), "type": "buyusel",
                    "stats": {"INT": int_val, "LUCK": luck_val}}
        else:
            str_val = 2 + (h % 6)
            dex_val = -1 + (h % 4)
            return {"bonus": 4 + (h % 8), "type": "fiziksel",
                    "stats": {"STR": str_val, "DEX": dex_val}}

    def get_class_bonus(self) -> dict:
        """Karakter sinifinin bonus verilerini dondurur."""
        return self.CLASS_BONUS.get(
            self.character.char_class,
            {"attack_mult": 1.0, "magic_mult": 1.0, "flee_threshold": 70, "defense_reduction": 0.0}
        )

    def get_advantage_key(self) -> str:
        """Sinifin avantajli oldugu savas buton key'ini dondurur. Bos = yok."""
        return self.CLASS_ADVANTAGE_KEY.get(self.character.char_class, "")

    # Silah olmayan esyalar (bu listedekiler silah seciminde gosterilmez)
    NON_WEAPON_ITEMS = game_data.NON_WEAPON_ITEMS

    def get_combat_weapons(self) -> list:
        """Equip edilmis savas silahlarini dondurur (max 4). Silah yoksa bos liste."""
        # Envanterde olmayanları equipped'dan cikar
        self.equipped_items = [w for w in self.equipped_items
                               if w in self.character.inventory]
        if self.equipped_items:
            return self.equipped_items[:4]
        # Silah equip edilmemisse bos liste dondur (silahsiz savas)
        return []

    def get_all_weapons(self) -> list:
        """Envanterdeki tum silahları dondurur (equip durumundan bagimsiz)."""
        weapons = []
        for item in self.character.inventory:
            if item not in self.NON_WEAPON_ITEMS:
                weapons.append(item)
        return weapons

    def toggle_equipped(self, weapon: str) -> bool:
        """Silahi equip/unequip yapar. True=equip, False=unequip."""
        if weapon in self.equipped_items:
            self.equipped_items.remove(weapon)
            return False
        elif len(self.equipped_items) < 4 and weapon not in self.NON_WEAPON_ITEMS:
            self.equipped_items.append(weapon)
            return True
        return False  # 4 slot dolu

    def get_weapons_for_class(self, class_name: str) -> list:
        """Sinifa gore silah seceneklerini dondurur."""
        return self.WEAPON_DATA.get(class_name, ["Pasli Kilic", "Tahta Sopa", "Tas", "Yumruk"])

    def get_random_locations(self) -> list:
        """10 lokasyondan rastgele 4 tanesini dondurur."""
        import random
        return random.sample(self.POSSIBLE_LOCATIONS, 4)

    def try_random_healing(self) -> Optional[str]:
        """Savas/baslangic disi modlarda rastgele can dolumu."""
        import random
        if self.current_mode == "savas" or self.is_startup:
            return None
        if self.character.hp >= self.character.max_hp:
            return None
        if random.random() < 0.25:
            heal = random.randint(5, 15)
            self.modify_hp(heal)
            messages = [
                f"Yolda bir sifa kaynagi buldun! +{heal} HP",
                f"Gizemli bir isik canini doldurdu! +{heal} HP",
                f"Yaralarinin bir kismi iyilesti! +{heal} HP",
                f"Dostca bir ruh sana sifa verdi! +{heal} HP",
            ]
            return random.choice(messages)
        return None

    def add_to_inventory(self, item: str) -> None:
        """
        Envantere yeni bir eşya ekler.

        Args:
            item: Eklenecek eşya adı.
        """
        if item not in self.character.inventory:
            self.character.inventory.append(item)

    def remove_from_inventory(self, item: str) -> bool:
        """
        Envanterden bir eşya çıkarır.

        Args:
            item: Çıkarılacak eşya adı.

        Returns:
            Eşya bulunup çıkarıldıysa True, aksi halde False.
        """
        if item in self.character.inventory:
            self.character.inventory.remove(item)
            return True
        return False

    def modify_gold(self, amount: int) -> None:
        """
        Altın miktarını değiştirir. Negatife düşmesine izin verilmez.

        Args:
            amount: Değişim miktarı.
        """
        self.character.gold = max(0, self.character.gold + amount)

    def reset(self) -> None:
        """Oyunu tamamen sıfırlar ve baştan başlatır."""
        self.__init__(Character())

    # ------------------------------------------------------------------ #
    #  ÖZEL (PRIVATE) METODLAR                                            #
    # ------------------------------------------------------------------ #

    def _init_system_prompt(self) -> None:
        """AI için sistem promptunu oluşturur ve geçmişe ekler."""
        system_prompt = (
            "Sen bir Dungeons & Dragons zindancisisin. Turkce hikaye anlat.\n\n"
            "KRITIK KURALLAR:\n"
            "1. YALNIZCA JSON formatinda cevap ver. Asla on soz veya aciklama yazma.\n"
            "2. Turkce ozel karakter (s, c, g, i, o, u) KESINLIKLE KULLANMA. Hep ASCII kullan.\n"
            "3. Yanit yapisi:\n"
            '{"hikaye_metni": "...", "feedback": "...", "mod": "kesif", "secenek_sayisi": 4, '
            '"hp_degisim": 0, "altin_degisim": 0, '
            '"zar_gerekli": false, "zar_secenegi": "", '
            '"yeni_esya": "", '
            '"stat_degisim": {}, '
            '"alt_bolge": "", "npc_adi": "", "etkilesim": "", "geri_donulebilir": false, '
            '"secenekler": {"sol_ust": "Ilerle", "sag_ust": "Etrafina bak", "sol_alt": "Geri don", "sag_alt": "Bekle"}}\n'
            "4. Hikaye 3-4 cumleyi, secenekler 5-6 kelimeyi gecmesin.\n"
            "5. MOD ALANI (ZORUNLU):\n"
            "   - 'kesif': Normal kesif. secenek_sayisi 2-4 arasi. Duruma gore karar ver.\n"
            "   - 'savas': Dusman ile mucadele. secenek_sayisi DAIMA 4. Secenekler KESINLIKLE: sol_ust='Saldir', sag_ust='Savun', sol_alt='Kac', sag_alt='Buyu' olsun.\n"
            "   - 'diyalog': NPC konusmasi. secenek_sayisi 2-4 arasi.\n"
            "6. SECENEK KURALLARI (COK ONEMLI):\n"
            "   - ASLA '...' yazma! Her secenek GERCEK, ANLAMLI bir aksiyon olmali.\n"
            "   - secenek_sayisi=2: sol_ust ve sag_ust DOLU, sol_alt ve sag_alt BOS string olmali.\n"
            "   - secenek_sayisi=3: sol_ust, sag_ust ve sol_alt DOLU, sag_alt BOS string.\n"
            "   - secenek_sayisi=4: HEPSI dolu.\n"
            "   - Bos olan secenekler icin deger olarak bos string '' kullan, '...' KULLANMA.\n"
            "7. hp_degisim: HP degisimi (negatif=hasar, pozitif=iyilesme). Savas disinda genelde 0.\n"
            "8. altin_degisim: Altin degisimi. Odul/harcama durumunda kullan.\n"
            "9. feedback: Oyuncunun son eyleminin kisa sonucu.\n"
            "10. Oyunu dinamik yonet: bazi turlarda savas, bazi turlarda kesif, bazi turlarda diyalog olsun. Monoton olma.\n"
            "11. hp_degisim ve altin_degisim DAIMA sayi olmali (0, -10, +20 gibi). Bos birakma.\n"
            "12. SAVAS KURALLARI (COK ONEMLI):\n"
            "   - Savas modunda dusman HER TUR saldirsin. hp_degisim NEGATIF olmali (-5 ile -25 arasi).\n"
            "   - Oyuncu 'Savun' secerse ve basarili olursa hasar almayacak. Kismi basariliysa hasar azalir. Basarisiz ise tam hasar.\n"
            "   - Oyuncu 'Saldir' secerse dusmana hasar verir.\n"
            "   - Oyuncu 'Kac' secerse sans ile kacabilir (basariliysa mod='kesif' yap)\n"
            "   - Oyuncu 'Buyu' secerse guclu saldiri yapar.\n"
            "   - Savas tehlikeli olmali! Oyuncu savunma yapmazsa cok hasar alsin.\n"
            "13. ZAR MEKANIĞI (ONEMLI):\n"
            "   - Kesif ve diyalog modlarinda bazi secenekler ZAR ATMA gerektirebilir.\n"
            "   - Ornegin: 'Kapiyi zorla ac', 'Tirmanmayi dene', 'Kilidi ac', 'Ikna etmeye calis' gibi beceri gerektiren secenekler.\n"
            "   - Zar gerektiren bir secenek sunuyorsan, zar_gerekli=true ve zar_secenegi='o secenegin key adi' (sol_ust, sag_ust, sol_alt, sag_alt) yap.\n"
            "   - Her turda en fazla 1 secenek zar gerektirebilir. Savas modunda zar KULLANMA.\n"
            "   - Zar sonucu (1-20) oyuncu tarafindan atilacak ve sana iletilecek. Sonuca gore hikayeyi sekillendir.\n"
            "   - Yuksek zar (15-20): Tam basari. Dusuk zar (1-5): Feci basarisizlik. Orta (6-14): Kismi basari/basarisizlik.\n"
            "14. ESYA SISTEMI (ONEMLI):\n"
            "   - yeni_esya: Oyuncuya sunulacak yeni silah, zirh veya esya adi. Bos birakmayi tercih et, sadece ozel durumlarda ver.\n"
            "   - KRITIK: yeni_esya'yi verdiginde oyuncu bunu OTOMATIK ALMAZ. Seceneklerde 'Ganimeti Al' sun.\n"
            "   - Savas kazanildiktan sonra %30 ihtimalle dusmandan silah veya zirh ver.\n"
            "   - Zirh isimleri: 'Demir Zirh', 'Ejderha Kalkani', 'Ates Pelerini' gibi olsun. Zirhlar HP ve DEF verir.\n"
            "   - Silahlar: 'Ates Kilici', 'Buzlu Balta' gibi. Silahlar STR/INT/DEX verir.\n"
            "   - Her esya FARKLI istatistiklere sahip olmali. Monoton olma.\n"
            "   - Verilen silahlar tematik olsun (Buzul Sarayi'nda 'Buz Kilici', Ruhlar Cehennemi'nde 'Lanetli Balta' gibi).\n"
            "   - Ayni esyayi tekrar verme. Envantere bak ve farkli seyler ver.\n"
            "15. ISTATISTIK SISTEMI (stat_degisim):\n"
            "   - stat_degisim: Oyuncunun istatistiklerini degistirmek icin kullan. Bos obje {} ise degisim yok.\n"
            "   - Kullanilabilir statlar: STR (guc), DEX (cevik), INT (zeka), DEF (savunma), LUCK (sans).\n"
            "   - Ornek: {\"STR\": 2, \"DEF\": -1} -> +2 guc, -1 savunma.\n"
            "   - Ozel olaylarda stat ver: Antrenman -> STR+1/2, Buyu ogrenme -> INT+1/2, Tuzak atlama -> DEX+1, Lanetlenme -> herhangi stat -1/-2.\n"
            "   - Savas kazanildiktan sonra bazen stat ver. Her turda verme, sadece onemli olaylarda.\n"
            "   - Stat degisimleri kucuk olsun: -2 ile +3 arasi. Abartma.\n"
            "16. DUNYA TAKIBI (COK ONEMLI - Tutarlilik):\n"
            "   - alt_bolge: Oyuncunun su an bulundugu alt bolge/mekan adi. Her turda doldur. Ornek: 'Batik Gemi Enkazlari', 'Kasaba Meydani'.\n"
            "   - npc_adi: Bu turda konusulan veya karsilasilan NPC varsa adi. Yoksa bos birak.\n"
            "   - etkilesim: Bu turda onemli bir etkilesim olduysa kisa aciklama. Ornek: 'Sandigi acti', 'Kopruyu gecti'. Yoksa bos birak.\n"
            "   - Sana verilen [Gezilen Bolgeler], [Taninan NPC'ler] ve [Son Etkilesimler] bilgisine SADIK KAL.\n"
            "   - Daha once gezilen bir bolgeye donuldugunde orayi HATIRLA ve tutarli betimle.\n"
            "   - NPC isimleri TUTARLI olsun. Ayni NPC'yi farkli isimle cagirma.\n"
            "   - Hikayede onceki olaylara referans ver. Oyuncunun gectigi yerleri, kararlarini hatirlat.\n"
            "17. GERI DON MEKANIĞI:\n"
            "   - geri_donulebilir: Oyuncunun bir onceki bolgeye geri donup donemeyecegi (true/false).\n"
            "   - Geri don UYGUN durumlar: yol kavsaklari, acik alanlar, kasaba sokaklari, koridorlar.\n"
            "   - Geri don UYGUN OLMAYAN durumlar: savas sirasinda, tek yonlu dusus, coken magara, kapanan kapi.\n"
            "   - geri_donulebilir=true ise seceneklerden birinde 'Geri don' secenegi sun (tercihen sag_alt).\n"
            "   - Geri don secilirse oyuncuyu bir onceki alt bolgeye gotur ve oradaki sahneyi HATIRLA.\n"
            "   - Savas modunda geri_donulebilir DAIMA false olsun."
        )

        self._message_history.append({
            "role": "system",
            "content": system_prompt,
        })

    def _get_world_context(self) -> str:
        """AI'a gonderilecek dunya durumu ozet metni."""
        parts = []
        if self.visited_locations:
            recent = self.visited_locations[-8:]  # Son 8 konum
            parts.append(f"[Gezilen Bolgeler] {', '.join(recent)}")
        if self.npc_met:
            parts.append(f"[Taninan NPC'ler] {', '.join(self.npc_met[-6:])}")
        if self.interactions:
            parts.append(f"[Son Etkilesimler] {' | '.join(self.interactions[-5:])}")
        if self.location_history:
            parts.append(f"[Geri Donulebilir Konum] {self.location_history[-1]}")
        if self._can_go_back and self.location_history:
            parts.append("Geri don secenegi sunulabilir.")
        return "\n".join(parts) if parts else ""

    def _optimize_memory(self) -> None:
        """
        Mesaj geçmişi çok uzarsa eski mesajları kırparak belleği optimize eder.

        Sistem mesajı (index 0) her zaman korunur. Kırpma uygulandığında,
        silinen mesajların bir özeti oluşturularak bağlam kaybı minimize edilir.
        """
        # Sistem mesajı hariç mesaj sayısı
        non_system_count = len(self._message_history) - 1

        if non_system_count <= self.MAX_MEMORY_MESSAGES:
            return

        # Sistem mesajını koru
        system_msg = self._message_history[0]

        # Son TRIM_TO_MESSAGES mesajı koru
        kept_messages = self._message_history[-self.TRIM_TO_MESSAGES:]

        # Silinen mesajlardan bir özet oluştur
        trimmed_count = non_system_count - self.TRIM_TO_MESSAGES
        summary_msg = {
            "role": "system",
            "content": (
                f"[Bellek Özeti: Önceki {trimmed_count} mesaj kırpıldı. "
                f"Mevcut karakter durumu: {self.get_character_summary()}]"
            ),
        }

        # Yeni geçmişi oluştur: sistem + özet + korunan mesajlar
        self._message_history = [system_msg, summary_msg] + kept_messages

    def _parse_hp_changes(self, ai_response: Dict[str, Any]) -> None:
        """
        AI yanıtındaki hikaye metninden HP, eşya ve altın değişimlerini ayrıştırır.

        Format örnekleri:
            [HP:-10]  → 10 hasar
            [HP:+5]   → 5 iyileşme
            [ESYA:Büyülü Yüzük]  → Envantere ekleme
            [ALTIN:+20]  → 20 altın kazanma

        Args:
            ai_response: AI'dan gelen ayrıştırılmış JSON sözlüğü.
        """
        import re

        story = ai_response.get("hikaye_metni", "")

        # HP değişimlerini bul ve uygula
        hp_matches = re.findall(r"\[HP:([+-]?\d+)\]", story)
        for match in hp_matches:
            self.modify_hp(int(match))

        # Eşya eklemelerini bul ve uygula
        item_matches = re.findall(r"\[ESYA:(.+?)\]", story)
        for item in item_matches:
            self.add_to_inventory(item.strip())

        # Altın değişimlerini bul ve uygula
        gold_matches = re.findall(r"\[ALTIN:([+-]?\d+)\]", story)
        for match in gold_matches:
            self.modify_gold(int(match))

        # İşlenen tag'leri hikaye metninden temizle
        cleaned_story = re.sub(r"\[HP:[+-]?\d+\]", "", story)
        cleaned_story = re.sub(r"\[ESYA:.+?\]", "", cleaned_story)
        cleaned_story = re.sub(r"\[ALTIN:[+-]?\d+\]", "", cleaned_story)
        self.current_story = cleaned_story.strip()

    # ------------------------------------------------------------------ #
    #  DUNDER METODLAR                                                    #
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return (
            f"GameState(character={self.character.name}, "
            f"hp={self.character.hp}/{self.character.max_hp}, "
            f"turn={self.turn_count}, "
            f"location={self.current_location})"
        )
