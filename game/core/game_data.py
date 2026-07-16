"""
game_data.py — Statik Oyun Verileri
======================================
Tüm sabit sözlükler ve oyun dengesi değerleri burada tanımlanır.
Bu dosya saf veri içerir — hiçbir iş mantığı yoktur.

Kaynak: Bu veriler orijinal olarak game_state.py sınıf attribute'ları
olarak tanımlıydı. Sürdürülebilirlik için ayrı dosyaya taşındı.
"""

# ------------------------------------------------------------------ #
#  TEMA ve DÜNYA VERİLERİ                                             #
# ------------------------------------------------------------------ #

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

POSSIBLE_LOCATIONS = [
    "Karanlik Magara", "Gizemli Orman", "Kaotik Uzay", "Ruhlar Cehennemi",
    "Sonsuz Col", "Batan Sehir", "Ejderha Yuvasi", "Buzul Sarayi",
    "Hayalet Kasabasi", "Lanetli Kale",
]

# ------------------------------------------------------------------ #
#  SINIF VERİLERİ                                                     #
# ------------------------------------------------------------------ #

CLASS_DATA = {
    "Savasci": {"hp": 120, "max_hp": 120, "gold": 30},
    "Buyucu": {"hp": 80, "max_hp": 80, "gold": 60},
    "Okcu": {"hp": 100, "max_hp": 100, "gold": 40},
    "Hirsiz": {"hp": 90, "max_hp": 90, "gold": 80},
}

# Sinif bazli temel istatistikler
CLASS_BASE_STATS = {
    "Savasci": {"STR": 16, "DEX": 10, "INT": 8,  "DEF": 14, "LUCK": 8},
    "Buyucu":  {"STR": 6,  "DEX": 10, "INT": 18, "DEF": 8,  "LUCK": 10},
    "Okcu":    {"STR": 10, "DEX": 16, "INT": 10, "DEF": 10, "LUCK": 12},
    "Hirsiz":  {"STR": 8,  "DEX": 14, "INT": 10, "DEF": 8,  "LUCK": 18},
}

# Sinif bonuslari (savas carpanlari)
CLASS_BONUS = {
    "Savasci": {"attack_mult": 1.25, "magic_mult": 1.0,  "flee_threshold": 70, "defense_reduction": 0.0},
    "Buyucu":  {"attack_mult": 1.0,  "magic_mult": 1.30, "flee_threshold": 70, "defense_reduction": 0.0},
    "Okcu":    {"attack_mult": 1.0,  "magic_mult": 1.0,  "flee_threshold": 70, "defense_reduction": 0.20},
    "Hirsiz":  {"attack_mult": 1.0,  "magic_mult": 1.0,  "flee_threshold": 40, "defense_reduction": 0.0},
}

# Sinif -> avantajli savas butonu (Okcu pasif bonus, buton yok)
CLASS_ADVANTAGE_KEY = {
    "Savasci": "sol_ust",   # Saldir
    "Buyucu":  "sag_alt",   # Buyu
    "Hirsiz":  "sol_alt",   # Kac
    "Okcu":    "",           # Pasif - buton yok
}

# ------------------------------------------------------------------ #
#  SİLAH VERİLERİ                                                    #
# ------------------------------------------------------------------ #

WEAPON_DATA = {
    "Savasci": ["Celik Kilic", "Savas Baltasi", "Mizrak", "Cift El Kilici"],
    "Buyucu": ["Ates Asasi", "Buz Asasi", "Yildirim Degnek", "Karanlik Grimoire"],
    "Okcu": ["Uzun Yay", "Arbalete", "Cift Kisa Yay", "Zehirli Ok Seti"],
    "Hirsiz": ["Gizli Hancer", "Zehirli Bicak", "Garoz Seti", "Duman Bombalari"],
}

# Silah istatistikleri: hasar bonusu, tipi, ve stat bonuslari
WEAPON_STATS = {
    # Savasci silahlari
    "Celik Kilic":       {"bonus": 5,  "type": "fiziksel", "stats": {"STR": 3, "DEF": 1}},
    "Savas Baltasi":     {"bonus": 8,  "type": "fiziksel", "stats": {"STR": 5, "DEX": -1}},
    "Mizrak":            {"bonus": 4,  "type": "fiziksel", "stats": {"STR": 2, "DEX": 2}},
    "Cift El Kilici":    {"bonus": 10, "type": "fiziksel", "stats": {"STR": 6, "DEF": -2}},
    # Buyucu silahlari
    "Ates Asasi":        {"bonus": 7,  "type": "buyusel",  "stats": {"INT": 4, "STR": -1}},
    "Buz Asasi":         {"bonus": 6,  "type": "buyusel",  "stats": {"INT": 3, "DEF": 2}},
    "Yildirim Degnek":   {"bonus": 9,  "type": "buyusel",  "stats": {"INT": 5, "LUCK": 1}},
    "Karanlik Grimoire": {"bonus": 12, "type": "buyusel",  "stats": {"INT": 7, "LUCK": -2}},
    # Okcu silahlari
    "Uzun Yay":          {"bonus": 6,  "type": "fiziksel", "stats": {"DEX": 4, "STR": 1}},
    "Arbalete":          {"bonus": 8,  "type": "fiziksel", "stats": {"DEX": 3, "STR": 3}},
    "Cift Kisa Yay":     {"bonus": 5,  "type": "fiziksel", "stats": {"DEX": 5, "DEF": -1}},
    "Zehirli Ok Seti":   {"bonus": 7,  "type": "buyusel",  "stats": {"DEX": 2, "INT": 3}},
    # Hirsiz silahlari
    "Gizli Hancer":      {"bonus": 6,  "type": "fiziksel", "stats": {"DEX": 3, "LUCK": 2}},
    "Zehirli Bicak":     {"bonus": 7,  "type": "buyusel",  "stats": {"DEX": 2, "INT": 2, "LUCK": 1}},
    "Garoz Seti":        {"bonus": 4,  "type": "fiziksel", "stats": {"DEX": 4, "LUCK": 3}},
    "Duman Bombalari":   {"bonus": 5,  "type": "buyusel",  "stats": {"DEX": 1, "LUCK": 4}},
    # Varsayilan
    "Pasli Kilic":       {"bonus": 2,  "type": "fiziksel", "stats": {"STR": 1}},
    "Mesale":            {"bonus": 1,  "type": "fiziksel", "stats": {}},
    "Yumruk":            {"bonus": 0,  "type": "fiziksel", "stats": {}},
}

# Silah olmayan esyalar (bu listedekiler silah seciminde gosterilmez)
NON_WEAPON_ITEMS = {"Mesale", "Harita", "Iksir", "Anahtar", "Pusula",
                    "Ip", "Canta", "Kitap", "Mum"}

# ------------------------------------------------------------------ #
#  İSTATİSTİK VERİLERİ                                               #
# ------------------------------------------------------------------ #

# Stat isimleri (gosterim icin)
STAT_NAMES = {
    "STR": "Guc",
    "DEX": "Cevik",
    "INT": "Zeka",
    "DEF": "Savun",
    "LUCK": "Sans",
}

# ------------------------------------------------------------------ #
#  SHOP VERİLERİ                                                      #
# ------------------------------------------------------------------ #

SHOP_BASE_COST = 15       # Baslangic fiyati
SHOP_ROLL_BASE_COST = 10  # Roll butonu baslangic fiyati
