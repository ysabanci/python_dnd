"""
prompt_builder.py — AI Prompt Üretici
=========================================
AI'a gönderilecek sistem prompt'u ve dinamik prompt'u üretir.
Tüm fonksiyonlar SAF (pure) ve STATIK'tir — GameState referansı ALMAZ.
Her fonksiyon sadece ihtiyacı olan verileri parametre olarak alır.

Kaynak: Bu fonksiyonlar orijinal olarak game_state.py'deki GameState
sınıfının metodlarıydı. Sürdürülebilirlik ve test edilebilirlik için
ayrı dosyaya taşındı.

NOT: Prompt metinlerinin İÇERİĞİNE dokunulmamıştır. Sadece yapısal
ayrıştırma yapılmıştır. Prompt optimizasyonu ayrı bir adımda yapılacak.
"""

from typing import Any, Dict, List, Optional


class PromptBuilder:
    """
    AI prompt üretici — tüm metodlar @staticmethod.

    GameState'e bağımlılık YOK. Circular import riski SIFIR.
    Her metod saf fonksiyondur — aynı girdiye aynı çıktıyı verir.
    """

    @staticmethod
    def build_system_prompt() -> str:
        """
        AI için sistem prompt'unu oluşturur.

        Returns:
            Sistem prompt metni (role: system olarak kullanılacak).

        NOT: Bu prompt metni oyun mekaniğinin temelini oluşturur.
        İçeriğine dokunulmamıştır, sadece konumu değişmiştir.
        """
        return (
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

    @staticmethod
    def build_dynamic_prompt(
        choice_text: str,
        current_theme: str,
        theme_lore: str,
        turn_count: int,
        current_story: str,
        current_mode: str,
        pending_combat_result: Optional[Dict[str, Any]],
        enemy_hp: int,
        enemy_max_hp: int,
        is_in_combat: bool,
        last_combat_turn: int,
        next_combat_turn: int,
        pending_loot: str,
        world_context: str,
        character_summary: str,
    ) -> tuple:
        """
        Dinamik prompt üretir. Savaş sonucu, dünya durumu ve karakter
        bilgisini içerir.

        Returns:
            (prompt_text, side_effects) tuple'ı.
            side_effects: dict — çağıranın uygulaması gereken state değişiklikleri.
                - "clear_combat_result": bool — pending_combat_result sıfırlanmalı mı
                - "enter_combat": bool — savaşa girilmeli mi
                - "update_combat_turn": int — _last_combat_turn güncellenmeli
                - "next_combat_turn": int — _next_combat_turn güncellenmeli
        """
        side_effects = {
            "clear_combat_result": False,
            "enter_combat": False,
            "update_combat_turn": None,
            "next_combat_turn": None,
        }

        prompt = (
            f"Secimim: {choice_text}. Tema: {current_theme}. "
            f"Tema Arka Plani: {theme_lore}\n"
            f"Adim No: {turn_count + 1}. "
        )

        # Tekrari onlemek icin son hikayeyi hatirlat
        if current_story:
            short_story = current_story[:100] + "..." if len(current_story) > 100 else current_story
            prompt += f"SON ADIMDA ANLATILAN: '{short_story}'. SAKIN AYNI SEYLERI TEKRAR ETME, HIKAYEYI ILERLET.\n"

        # ----- Savas sonucu bilgisi -----
        if pending_combat_result:
            acc = pending_combat_result.get("accuracy", 0)
            action = pending_combat_result.get("action", "")

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
            prompt += f"Dusman HP: {enemy_hp}/{enemy_max_hp}. "
            if enemy_hp <= 0:
                prompt += "DUSMAN YENILDI! Savasi bitir, mod='kesif' yap, odul ver. "
            side_effects["clear_combat_result"] = True
        else:
            # Rastgele savas zamanlama
            if current_mode == "savas" or is_in_combat:
                # Savas devam ediyor
                turns_in_combat = turn_count - last_combat_turn
                if turns_in_combat >= 3:
                    prompt += "Boss'u yeniyoruz veya kaciyoruz! Savasi sonlandir ve odul ver. mod'u 'kesif' yap. "
                else:
                    prompt += "Boss savasi devam ediyor. Temaya uygun tehlikeli saldirilar yap. mod='savas'. "
            elif turn_count >= next_combat_turn:
                prompt += "KARSIMA TEMA ILE UYUMLU BIR DUSMAN CIKAR! Savas basliyor. mod'u 'savas' yap. "
                side_effects["enter_combat"] = True
                side_effects["update_combat_turn"] = turn_count
                # Yeni next_combat_turn değeri hesaplanır
                import random
                side_effects["next_combat_turn"] = turn_count + random.randint(6, 14)
            else:
                prompt += "Kesfe devam. Gidisat bir onceki adimla baglantili olsun. Temaya uygun yeni bir yere ilerleyelim. "

        # Bekleyen ganimet bilgisi
        if pending_loot:
            prompt += f"\nBEKLEYEN GANIMET: '{pending_loot}' - Oyuncuya bunu alip almayacagini sor. Seceneklerde 'Ganimeti al' ve 'Birak' gibi secenekler sun. yeni_esya BOSBIRAK cunku zaten beklemede."

        # Dunya durumu
        if world_context:
            prompt += "\n" + world_context
        prompt += "\n" + character_summary
        return prompt, side_effects

    @staticmethod
    def build_world_context(
        visited_locations: List[str],
        npc_met: List[str],
        interactions: List[str],
        location_history: List[str],
        can_go_back: bool,
    ) -> str:
        """
        AI'a gönderilecek dünya durumu özet metni.

        Args:
            visited_locations: Gezilen alt bölgeler.
            npc_met: Tanışılan NPC'ler.
            interactions: Son etkileşimler.
            location_history: Konum geçmişi.
            can_go_back: Geri dönülebilir mi.

        Returns:
            Dünya durumu özet metni.
        """
        parts = []
        if visited_locations:
            recent = visited_locations[-8:]  # Son 8 konum
            parts.append(f"[Gezilen Bolgeler] {', '.join(recent)}")
        if npc_met:
            parts.append(f"[Taninan NPC'ler] {', '.join(npc_met[-6:])}")
        if interactions:
            parts.append(f"[Son Etkilesimler] {' | '.join(interactions[-5:])}")
        if location_history:
            parts.append(f"[Geri Donulebilir Konum] {location_history[-1]}")
        if can_go_back and location_history:
            parts.append("Geri don secenegi sunulabilir.")
        return "\n".join(parts) if parts else ""

    @staticmethod
    def build_character_summary(
        name: str,
        char_class: str,
        hp: int,
        max_hp: int,
        gold: int,
        total_stats: Dict[str, int],
        inventory: List[str],
        current_location: str,
        current_sub_location: str,
        turn_count: int,
    ) -> str:
        """
        Karakterin mevcut durumunun özet metnini döndürür.

        Args:
            name: Karakter adı.
            char_class: Karakter sınıfı.
            hp: Mevcut HP.
            max_hp: Maksimum HP.
            gold: Altın miktarı.
            total_stats: Toplam istatistikler (base + weapon + event).
            inventory: Envanter listesi.
            current_location: Ana bölge.
            current_sub_location: Alt bölge.
            turn_count: Tur sayısı.

        Returns:
            Karakter durum özeti metni.
        """
        inv_str = ", ".join(inventory) if inventory else "Bos"
        stat_str = ", ".join(f"{k}:{v}" for k, v in total_stats.items())
        return (
            f"[Karakter Durumu] "
            f"Ad: {name} | "
            f"Sinif: {char_class} | "
            f"HP: {hp}/{max_hp} | "
            f"Altin: {gold} | "
            f"Stats: {stat_str} | "
            f"Envanter: {inv_str} | "
            f"Ana Bolge: {current_location} | "
            f"Alt Bolge: {current_sub_location} | "
            f"Tur: {turn_count}"
        )
