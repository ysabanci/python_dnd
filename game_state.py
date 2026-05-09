"""
game_state.py - Oyun Durumu Yöneticisi
========================================
Karakterin canını (HP), envanterini, mevcut konumunu ve
AI'a gönderilecek mesaj geçmişini (memory) yönetir.
Geçmiş çok uzarsa eski mesajları kırpan optimizasyon içerir.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
    """
    name: str = "Kahraman"
    char_class: str = "Maceraperest"
    hp: int = 100
    max_hp: int = 100
    inventory: List[str] = field(default_factory=lambda: ["Pasli Kilic", "Mesale"])
    gold: int = 50


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

    THEME_LORE = {
        "Karanlik Magara": "Kadim bir ejderhanin yillardir uyudugu, duvarlarindan kristal suzulen rutubetli ve devasa bir magara sistemi.",
        "Gizemli Orman": "Agaclarin fisildadigi, her adimda bitkilerin yer degistirdigi ve sislerin arasinda perilerin goruldugu buyulu bir orman.",
        "Kaotik Uzay": "Fizik kurallarinin islemedigi, yildiz tozlarinin arasinda devasa gozlerin sizi izledigi boyutsal bir bosluk.",
        "Ruhlar Cehennemi": "Lav nehirlerinin aktigi, gunahkar ruhlarin cigliklarinin yankilandigi ve zebani lordlarinin hukmettigi bir diyar.",
        "Sonsuz Col": "Gunesin hic batmadigi, kumlarin altinda devasa solucanlarin dolastigi ve seraplarin insanlari delirttigi bir sahra.",
        "Batan Sehir": "Denizin altina gomulmus, su altinda nefes alinabilen ama yaratiklarin pusuya yattigi antik bir sehir.",
        "Ejderha Yuvasi": "Volkanik bir dagin icinde, altin yiginlarinin arasinda uyuyan ejderhalarin korundugu efsanevi yuva.",
        "Buzul Sarayi": "Her seyin buzdan yapildigi, buz devilerin hukmettigi dondurucu bir saray.",
        "Hayalet Kasabasi": "Yasayan kimsenin kalmadigi, geceleyin hayaletlerin sokaklarda dolastigi terk edilmis bir kasaba.",
        "Lanetli Kale": "Karanlik buyulerle korunan, icinde vampir lordun hukum surdugu gotik bir kale.",
    }

    CLASS_DATA = {
        "Savasci": {"hp": 120, "max_hp": 120, "gold": 30},
        "Buyucu": {"hp": 80, "max_hp": 80, "gold": 60},
        "Okcu": {"hp": 100, "max_hp": 100, "gold": 40},
        "Hirsiz": {"hp": 90, "max_hp": 90, "gold": 80},
    }

    WEAPON_DATA = {
        "Savasci": ["Celik Kilic", "Savas Baltasi", "Mizrak", "Cift El Kilici"],
        "Buyucu": ["Ates Asasi", "Buz Asasi", "Yildirim Degnek", "Karanlik Grimoire"],
        "Okcu": ["Uzun Yay", "Arbalete", "Cift Kisa Yay", "Zehirli Ok Seti"],
        "Hirsiz": ["Gizli Hancer", "Zehirli Bicak", "Garoz Seti", "Duman Bombalari"],
    }

    POSSIBLE_LOCATIONS = [
        "Karanlik Magara", "Gizemli Orman", "Kaotik Uzay", "Ruhlar Cehennemi",
        "Sonsuz Col", "Batan Sehir", "Ejderha Yuvasi", "Buzul Sarayi",
        "Hayalet Kasabasi", "Lanetli Kale",
    ]

    def __init__(self, character: Optional[Character] = None):
        """
        GameState'i başlatır.

        Args:
            character: Oyuncu karakteri. Verilmezse varsayılan karakter oluşturulur.
        """
        self.character = character or Character()
        self.current_location: str = "Bilinmeyen Diyar"
        self.turn_count: int = 0

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
        for i, key in enumerate(option_keys):
            if i < secenek_sayisi:
                self.current_options[key] = secenekler.get(key, "...")
            else:
                self.current_options[key] = ""

        self.turn_count += 1

        # ----- HP degisimi (guardlar ile korunmus) -----
        hp_change = ai_response.get("hp_degisim", 0)

        # Guard 1: Diyalog modunda HP asla dusmesin
        if self.current_mode == "diyalog":
            hp_change = 0
        # Guard 2: Savasa ilk girildiginde HP dusmesin
        elif just_entered_combat:
            hp_change = 0

        if isinstance(hp_change, (int, float)) and hp_change != 0:
            self.modify_hp(int(hp_change))

        # Altin degisimi (diyalogda da olabilir)
        gold_change = ai_response.get("altin_degisim", 0)
        if isinstance(gold_change, (int, float)) and gold_change != 0:
            self.modify_gold(int(gold_change))

        # Yedek: hikaye metni icindeki tag'lerden de oku
        self._parse_hp_changes(ai_response)

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
            cycle = self.turn_count % 8
            if cycle < 4:
                prompt += "Kesfe devam. Gidisat bir onceki adimla baglantili olsun, yeni ve temaya uygun bir yere ilerleyelim. "
            elif cycle == 4:
                prompt += "KARSIMA TEMA ILE UYUMLU BIR BOSS CIKAR! Boss savasi basliyor. mod'u 'savas' yap. "
            elif cycle in [5, 6]:
                prompt += "Boss savasi devam ediyor. Temaya uygun tehlikeli saldirilar yap. mod'u 'savas' yap. "
            elif cycle == 7:
                prompt += "Boss'u yeniyoruz veya kaciyoruz! Savasi sonlandir ve odul ver. mod'u 'kesif' yap. "
            
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
        inv_str = ", ".join(self.character.inventory) if self.character.inventory else "Boş"
        return (
            f"[Karakter Durumu] "
            f"Ad: {self.character.name} | "
            f"Sınıf: {self.character.char_class} | "
            f"HP: {self.character.hp}/{self.character.max_hp} | "
            f"Altın: {self.character.gold} | "
            f"Envanter: {inv_str} | "
            f"Konum: {self.current_location} | "
            f"Tur: {self.turn_count}"
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

    def apply_weapon_choice(self, weapon: str) -> None:
        """Baslangic silahini uygular."""
        self.character.inventory = [weapon, "Mesale"]

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
            '"secenekler": {"sol_ust": "...", "sag_ust": "...", "sol_alt": "...", "sag_alt": "..."}}\n'
            "4. Hikaye 3 cumleyi, secenekler 5 kelimeyi gecmesin.\n"
            "5. MOD ALANI (ZORUNLU):\n"
            "   - 'kesif': Normal kesif. secenek_sayisi 2-4 arasi. Duruma gore karar ver: bazen 2, bazen 3, bazen 4 secenek sun.\n"
            "   - 'savas': Dusman ile mucadele. secenek_sayisi DAİMA 4. Secenekler KESINLIKLE: sol_ust='Saldir', sag_ust='Savun', sol_alt='Kac', sag_alt='Buyu' olsun.\n"
            "   - 'diyalog': NPC konusmasi. secenek_sayisi 2-4 arasi. Duruma gore az veya cok secenek sun.\n"
            "6. secenek_sayisi: 2 ise sadece sol_ust ve sag_ust dolu olsun. 3 ise sol_ust, sag_ust, sol_alt dolu olsun. 4 ise hepsi dolu olsun.\n"
            "7. hp_degisim: HP degisimi (negatif=hasar, pozitif=iyilesme). Savas disinda genelde 0.\n"
            "8. altin_degisim: Altin degisimi. Odul/harcama durumunda kullan.\n"
            "9. feedback: Oyuncunun son eyleminin kisa sonucu.\n"
            "10. Oyunu dinamik yonet: bazi turlarda savas, bazi turlarda kesif, bazi turlarda diyalog olsun. Monoton olma.\n"
            "11. hp_degisim ve altin_degisim DAIMA sayi olmali (0, -10, +20 gibi). Bos birakma.\n"
            "12. SAVAS KURALLARI (COK ONEMLI):\n"
            "   - Savas modunda dusman HER TUR saldirsin. hp_degisim NEGATIF olmali (-5 ile -25 arasi).\n"
            "   - Oyuncu 'Savun' secerse hasar AZALSIN (hp_degisim -3 ile -8 arasi). Savunma hasari azaltir.\n"
            "   - Oyuncu 'Saldir' secerse dusmana hasar verir ama kendisi de hasar alir.\n"
            "   - Oyuncu 'Kac' secerse %50 sans ile kacabilir (basariliysa mod='kesif' yap), basarisizsa ekstra hasar.\n"
            "   - Oyuncu 'Buyu' secerse guclu saldiri ama HP maliyeti vardir.\n"
            "   - Savas tehlikeli olmali! Oyuncu savunma yapmazsa cok hasar alsin."
        )

        self._message_history.append({
            "role": "system",
            "content": system_prompt,
        })

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
