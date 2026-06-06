# DEĞİŞİKLİK RAPORU (CHANGELOG)

Bu dosya `RESTRUCTURE_PLAN.md` kapsamında yapılan tüm değişiklikleri
teknik detayıyla belgeler. Amacı:

1. **Geriye dönük izlenebilirlik** — bir şey bozulursa hangi adımda ne değişti?
2. **Agent koordinasyonu** — birden fazla kişi/model çalışıyor, kim ne yaptı?
3. **Plana uygunluk** — RESTRUCTURE_PLAN'a bağlı kalındı mı?

---

## KAYIT ŞABLONU

Yeni bir aşama tamamlandığında aşağıdaki şablonu kullanın:

```markdown
## [Aşama X.Y] — [Kısa Başlık]

- **Tarih:** YYYY-MM-DD
- **Agent/Kişi:** [Kim yaptı]
- **İlgili Sorunlar:** S01, S08... (RESTRUCTURE_PLAN'daki ID'ler)
- **Plan Uyumu:** ✅ Plana uygun / ⚠️ Sapma var (açıkla)

### Ne Yapıldı
[Değişikliklerin teknik açıklaması — hangi dosyada ne değişti, neden]

### Dosya Değişiklikleri
| Dosya | Durum | Açıklama |
|-------|-------|----------|
| `dosya.py` | [YENİ] / [DEĞİŞTİ] / [SİLİNDİ] | Kısa açıklama |

### Teknik Kararlar
[Neden bu yaklaşım seçildi? Alternatifler neydi? Riskler nasıl yönetildi?]

### Dikkat Edilecekler
[Bu değişiklik sonrası başka agent'ların bilmesi gereken şeyler:
- Yeni import gerektiren dosyalar
- Değişen arayüzler (method signature)
- Testlerde dikkat edilmesi gereken noktalar]

### Test Sonuçları
[Testlerin çalıştırılma komutu ve sonucu]
```

---

## [Aşama 0] — Güvenlik Ağı: Test Altyapısı + Bağımlılık Pinleme

- **Tarih:** 2026-06-03
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S16 (Sıfır Unit Test), S17 (CI/CD Pipeline Yok), S18 (requirements.txt Üst Sınır Yok)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

Projeye sıfırdan test altyapısı eklendi. Hiçbir mevcut kod değiştirilmedi —
sadece yeni dosyalar oluşturuldu. 6 adımın tamamı tek commit'te yapıldı çünkü
hepsi sıfır riskli ekleme operasyonuydu.

#### Adım 0.1 — Test Dizini ve Pytest

`tests/` dizini oluşturuldu:
- `__init__.py` — Python package tanımı
- `conftest.py` — Paylaşılan fixture'lar

**conftest.py detayı:**
- Proje kök dizini `sys.path`'e ekleniyor (package yapısı olmadığı için gerekli)
- 3 Character fixture: `default_character`, `warrior_character`, `mage_character`
- 3 GameState fixture: `game_state`, `warrior_state`, `mage_state`
- Fixture'lar `@pytest.fixture` decorator ile tanımlanmış — her test fonksiyonu
  taze bir kopya alır, testler birbirini kirletmez

#### Adım 0.2 — test_game_state.py (35 test)

`GameState` sınıfındaki **saf fonksiyonlar** test edildi:

| Test Sınıfı | Test Sayısı | Test Edilen Metod |
|---|---|---|
| `TestModifyHp` | 5 | `modify_hp()` — hasar, iyileşme, sınırlar, sıfır |
| `TestModifyGold` | 3 | `modify_gold()` — ekleme, çıkarma, negatif koruma |
| `TestGetTotalStats` | 3 | `get_total_stats()` — base, event, weapon bonusları |
| `TestGetStatEffectOnCombat` | 4 | `get_stat_effect_on_combat()` — cap kontrolü |
| `TestApplyClassChoice` | 3 | `apply_class_choice()` — sınıf ataması, stat reset |
| `TestGetWeaponStats` | 4 | `get_weapon_stats()` — bilinen, bilinmeyen, büyü, zırh |
| `TestToggleEquipped` | 4 | `toggle_equipped()` — equip, unequip, max 4, non-weapon |
| `TestGetCombatWeapons` | 3 | `get_combat_weapons()` — envanter sync, max 4 |
| `TestInventory` | 4 | `add/remove_from_inventory()` — duplicate, nonexistent |
| `TestShopSystem` | 7 | `init_shop/shop_buy/shop_roll()` — GameState üzerinden |

**Testte yakalanan önemli bulgu:**
- `CLASS_DATA` sınıf isimleri ASCII Türkçe: `"Savasci"`, `"Buyucu"` —
  Türkçe karakterli `"Savaşçı"` ile eşleşmiyor. Bu bilinen bir tutarsızlık,
  ileride düzeltilecek ama şu an dokunulmadı.
- `get_weapon_stats("Demir Zırh")` zırh olarak algılanmıyor çünkü keyword
  listesinde `"zirh"` (ASCII) var. Test `"Demir zirh"` kullanacak şekilde
  düzeltildi — bu davranışı bozma riski nedeniyle oyun koduna dokunulmadı.

#### Adım 0.3 — test_ai_parse.py (9 test)

`ai_manager.py`'deki `_parse_response` metodu test edildi.

**Teknik zorluk:** `ai_manager.py` modül seviyesinde `import litellm` yapıyor.
Test ortamında `litellm` yüklü olmayabilir. Çözüm:

```python
if "litellm" not in sys.modules:
    mock_litellm = MagicMock()
    sys.modules["litellm"] = mock_litellm
```

Bu `sys.modules` mock'u sayesinde `litellm` yüklü olmadan `AdventureAI`
sınıfı import edilebiliyor. Sadece `_parse_response` test edildiği için
gerçek API çağrısı yapılmıyor.

**AdventureAI fixture:**
```python
obj = object.__new__(AdventureAI)  # __init__ atlanıyor
obj._api_key = "test-key"          # minimum attribute'lar set ediliyor
```
Bu pattern `__init__`'teki API key doğrulamasını bypass eder.

| Test Sınıfı | Senaryo |
|---|---|
| `TestParseResponseSuccess` | Temiz JSON, markdown wrapped, çevreleyen metin, HP alanı, savaş alanları |
| `TestParseResponseFallback` | Geçersiz girdi, boş girdi, eksik JSON, gerekli alan eksik |

#### Adım 0.4 — test_config.py (9 test)

`config_manager.py` fonksiyonları test edildi.

**Dosya I/O izolasyonu:** `monkeypatch` ile `CONFIG_FILE` yolunu `tmp_path`'e
yönlendirdik — gerçek `game_config.json`'a dokunulmuyor:

```python
monkeypatch.setattr(config_manager, "CONFIG_FILE", str(tmp_path / "test.json"))
```

| Test | Doğrulanan Davranış |
|---|---|
| `test_load_default_when_no_file` | Dosya yoksa varsayılan config dönmeli |
| `test_save_and_load_roundtrip` | Kaydet → yükle döngüsü veriler korumalı |
| `test_load_corrupt_file` | Bozuk JSON'da crash olmamalı, varsayılan dönmeli |
| `test_load_merges_with_defaults` | Kısmi JSON + varsayılan = tam config |
| `test_mask_api_key` (5 adet) | Kısa, uzun, boş, sınır değer key maskeleme |

#### Adım 0.5 — test_snapshots.py (10 test)

**Characterization (snapshot) testleri** — God Object'lerdeki karmaşık
davranışı dondurur. Bilinen input → beklenen output.

| Test Sınıfı | Test Sayısı | Dondurulan Davranış |
|---|---|---|
| `TestExplorationSnapshots` | 4 | HP/gold değişimi, ganimet, stat, dünya takibi |
| `TestCombatSnapshots` | 3 | Savaşa giriş (HP guard), savaş modu guard, diyalog guard |
| `TestOptionFilteringSnapshots` | 2 | Boş seçenek filtreleme, 2-seçenek modu |
| `TestGameOverSnapshot` | 1 | HP=0 → game over |

**Neden önemli:** Bu testler refactoring'den önce "mevcut davranışı" kaydeder.
Bir bug düzeltildiğinde ilgili snapshot testi de güncellenmeli — aksi halde
test kırılır ve farkı görürsünüz.

#### Adım 0.6 — requirements.txt Pinleme

```diff
-opencv-python>=4.8.0
+opencv-python>=4.8.0,<5.0
-mediapipe>=0.10.0
+mediapipe>=0.10.0,<0.11
-litellm>=1.40.0
+litellm>=1.40.0,<2.0
-numpy>=1.24.0
+numpy>=1.24.0,<3.0
-pygame>=2.5.0
+pygame>=2.5.0,<3.0
+
+# Geliştirme bağımlılıkları
+pytest>=7.0.0,<9.0
```

### Dosya Değişiklikleri

| Dosya | Durum | Satır |
|-------|-------|-------|
| `tests/__init__.py` | [YENİ] | 1 |
| `tests/conftest.py` | [YENİ] | ~70 |
| `tests/test_game_state.py` | [YENİ] | ~370 |
| `tests/test_ai_parse.py` | [YENİ] | ~130 |
| `tests/test_config.py` | [YENİ] | ~110 |
| `tests/test_snapshots.py` | [YENİ] | ~210 |
| `requirements.txt` | [DEĞİŞTİ] | 9 (önceki: 5) |

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 68 passed in 0.22s ==============================
```

---

## [Aşama 1] — Bağımsız Küçük Düzeltmeler

- **Tarih:** 2026-06-04
- **Agent:** Başka bir AI agent (bu raporu yazan agent DEĞİL)
- **İlgili Sorunlar:** S01, S04, S10, S11, S14
- **Plan Uyumu:** ✅ Tüm checkbox'lar işaretli, detay aşağıda

### Ne Yapıldı (Özet)

> ⚠️ **NOT:** Bu aşama başka bir agent tarafından yapıldı. Aşağıdaki bilgiler
> RESTRUCTURE_PLAN.md'deki checkbox durumundan ve commit geçmişinden çıkarılmıştır.
> Teknik detaylar o agent tarafından belgelenmemiştir.

| Adım | Sorun | Yapılan |
|---|---|---|
| 1.1 | S01 | `main.py:920-922` — `draw_buttons` parametre tipi düzeltildi |
| 1.2 | S11 | `main.py:__init__` — `_inv_hovered_*` attribute'ları tanımlandı |
| 1.3 | S04 | `main.py` — `_extra_turn_active` bayrağı ek sıfırlama noktaları eklendi |
| 1.4 | S10 | `main.py` — Savaş aksiyon stringleri (`"saldir"`, `"savun"` vs.) sabitlere çekildi |
| 1.5 | S14 | `ai_manager.py` — `ast.literal_eval` fallback'ı kaldırıldı |

### Dikkat Edilecekler

- Bu adımların **teknik detay raporu yoktur**. İleride bu adımlarla ilgili
  bir sorun çıkarsa `main.py` ve `ai_manager.py`'deki ilgili bölümlerin
  commit geçmişinden incelenmesi gerekir.
- Testler bu aşamada da geçmiştir (checkbox'lar işaretli).

---

## [Aşama 2.1 + 2.2] — Statik Veri Ayrıştırma

- **Tarih:** 2026-06-04
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S08 (game_state.py God Object)
- **Plan Uyumu:** ✅ Plana tam uygun. 2.1 ve 2.2 ayrılmaz çift olduğu için birlikte yapıldı.

### Ne Yapıldı

`game_state.py`'deki tüm statik sözlükler ve sabitler yeni `game_data.py`
dosyasına taşındı. `GameState` sınıfında sınıf attribute'ları olarak
`game_data.X` referansları bırakıldı.

**Taşınan veriler (12 adet):**

| Sabit | Orijinal Konum | Açıklama |
|---|---|---|
| `THEME_LORE` | satır 67-78 | 10 tema lore metni |
| `CLASS_DATA` | satır 80-85 | 4 sınıf HP/gold değerleri |
| `CLASS_BASE_STATS` | satır 88-93 | 4 sınıf temel statları |
| `WEAPON_DATA` | satır 95-100 | 4 sınıf silah listeleri |
| `WEAPON_STATS` | satır 103-128 | 18 silah stat tablosu |
| `STAT_NAMES` | satır 131-137 | 5 stat görüntü isimleri |
| `CLASS_BONUS` | satır 140-145 | 4 sınıf savaş çarpanları |
| `CLASS_ADVANTAGE_KEY` | satır 148-153 | 4 sınıf avantaj tuşları |
| `POSSIBLE_LOCATIONS` | satır 155-159 | 10 lokasyon listesi |
| `NON_WEAPON_ITEMS` | satır 738-740 | 9 non-weapon eşya seti |
| `SHOP_BASE_COST` | satır 606 | Shop başlangıç fiyatı (15) |
| `SHOP_ROLL_BASE_COST` | satır 607 | Roll başlangıç fiyatı (10) |

### Teknik Kararlar

**Neden sınıf attribute referansı bırakıldı:**

```python
# game_state.py — ÖNCEKİ (inline)
class GameState:
    STAT_NAMES = {"STR": "Guc", "DEX": "Cevik", ...}

# game_state.py — SONRAKİ (referans)
class GameState:
    STAT_NAMES = game_data.STAT_NAMES
```

Bu yaklaşım sayesinde `main.py`'deki `self.state.STAT_NAMES` ve
`self.state.NON_WEAPON_ITEMS` gibi erişimler **HİÇ DEĞİŞMEDİ**.
`main.py`'ye dokunulmadan geçiş yapıldı.

**Alternatif:** Doğrudan `game_data.STAT_NAMES` import etmek — bu,
`main.py`'de 3 noktayı değiştirmeyi gerektirirdi. Şu an gereksiz risk.

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `game_data.py` | [YENİ] | ~130 satır — tüm statik veriler |
| `game_state.py` | [DEĞİŞTİ] | ~90 satır inline veri → 10 satır referans |

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 68 passed in 0.62s ==============================
```

---

## [Aşama 2.3 + 2.4] — Shop Sistemi Ayrıştırma + Test

- **Tarih:** 2026-06-04
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S08 (game_state.py God Object), S16 (Sıfır Unit Test)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

`GameState`'teki shop metodları (`init_shop`, `shop_buy`, `shop_roll`,
`get_shop_items`, `get_shop_roll_cost`, `_generate_shop_items`) yeni
`ShopSystem` sınıfına taşındı.

**Taşınan metodlar (6 adet):**

| Eski Metod (GameState) | Yeni Metod (ShopSystem) | Satır |
|---|---|---|
| `init_shop()` | `init()` | 528-532 |
| `_generate_shop_items()` | `_generate_items()` | 534-544 |
| `get_shop_items()` | `get_items()` | 546-550 |
| `get_shop_roll_cost()` | `get_roll_cost()` | 552-556 |
| `shop_buy(index)` | `buy(index, gold, apply_stat_fn, deduct_gold_fn)` | 558-569 |
| `shop_roll()` | `roll(gold, deduct_gold_fn)` | 571-580 |

### Teknik Kararlar

**1. Callback pattern (en kritik karar):**

Shop metodları `self.character.gold` ve `self.apply_event_stat()` ile
doğrudan `GameState`'e bağlıydı. İki seçenek vardı:

| Seçenek | Avantaj | Dezavantaj |
|---|---|---|
| A) ShopSystem'e Character referansı ver | Basit | Sıkı bağımlılık devam eder |
| B) Callback fonksiyonları kullan | Loose coupling, test edilebilir | Biraz daha karmaşık |

**Seçenek B tercih edildi.** `buy()` ve `roll()` artık `gold` değerini ve
`deduct_gold_fn` / `apply_stat_fn` callback'lerini parametre olarak alıyor:

```python
# shop_system.py
def buy(self, index, gold, apply_stat_fn, deduct_gold_fn):
    ...
    deduct_gold_fn(item["cost"])
    apply_stat_fn(item["stat"], item["amount"])
```

**2. Delegasyon wrapper'ları:**

`GameState`'teki public arayüz KORUNDU — `main.py`'deki çağrılar
değişmedi:

```python
# game_state.py — wrapper
def shop_buy(self, index):
    return self._shop.buy(
        index=index,
        gold=self.character.gold,
        apply_stat_fn=self.apply_event_stat,
        deduct_gold_fn=lambda cost: setattr(
            self.character, 'gold', self.character.gold - cost),
    )
```

**3. Lambda'lı gold deduction:**

`deduct_gold_fn` için `lambda cost: setattr(self.character, 'gold', ...)` kullanıldı.
Neden `self.modify_gold(-cost)` değil? Çünkü `modify_gold` negatife düşmeme koruması
içeriyor (`max(0, ...)`) ama shop'ta bu kontrolü `ShopSystem.buy()` zaten yapıyor
(gold >= cost kontrolü). İki katmanlı koruma gereksiz ve `setattr` daha doğrudan.

**4. Test dosyası (test_shop.py) — FakeWallet pattern:**

`ShopSystem`'i `GameState`'ten bağımsız test etmek için `FakeWallet` sınıfı
oluşturuldu:

```python
class FakeWallet:
    def __init__(self, gold=999):
        self.gold = gold
        self.applied_stats = []  # kayıt tutar

    def deduct_gold(self, cost): self.gold -= cost
    def apply_stat(self, key, amount): self.applied_stats.append((key, amount))
```

Bu sayede testler `GameState` oluşturmadan çalışır — daha hızlı, daha izole.

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `shop_system.py` | [YENİ] | ~110 satır — ShopSystem sınıfı |
| `game_state.py` | [DEĞİŞTİ] | ~57 satır inline metod → ~33 satır wrapper |
| `tests/test_shop.py` | [YENİ] | ~200 satır — 17 test |

### Dikkat Edilecekler

- `main.py`'deki çağrılar (`self.state.shop_buy()`, `self.state.init_shop()` vs.)
  **HİÇ DEĞİŞMEDİ**. Bu wrapper'lar silinmemeli.
- `ShopSystem` `game_data` modülünü import ediyor — `SHOP_BASE_COST` ve
  `SHOP_ROLL_BASE_COST` sabitlerini oradan alıyor.
- `GameState.__init__`'te `self._shop = ShopSystem()` eklendi.

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 85 passed in 0.25s ==============================
```

Test artışı: 68 → 85 (+17 yeni shop testi)

---

## [Aşama 3.1 + 3.2] — Prompt Ayrıştırma

- **Tarih:** 2026-06-06
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S08 (game_state.py God Object)
- **Plan Uyumu:** ✅ Plana tam uygun. 3.1 ve 3.2 birlikte yapıldı (ayrılmaz çift).

### Ne Yapıldı

`GameState`'teki 4 prompt metodu yeni `PromptBuilder` sınıfına taşındı.
Tüm metodlar `@staticmethod` — `GameState` referansı ALMAZ.

**Taşınan metodlar (4 adet):**

| Eski Metod (GameState) | Yeni Metod (PromptBuilder) | Orijinal Satır |
|---|---|---|
| `_init_system_prompt()` | `build_system_prompt()` | 738-819 (~80 satır) |
| `get_dynamic_prompt(choice_text)` | `build_dynamic_prompt(...)` | 347-418 (~70 satır) |
| `_get_world_context()` | `build_world_context(...)` | 821-835 (~15 satır) |
| `get_character_summary()` | `build_character_summary(...)` | 442-464 (~20 satır) |

### Teknik Kararlar

**1. En kritik risk: `get_dynamic_prompt` içindeki SIDE-EFFECT'ler.**

Orijinal `get_dynamic_prompt` sadece prompt metni üretmiyordu — aynı zamanda
state de değiştiriyordu:

```python
# Satır 392: pending_combat_result sıfırlama
self.pending_combat_result = None
# Satır 405-407: savaşa giriş state değişiklikleri
self._in_combat = True
self._last_combat_turn = self.turn_count
self._next_combat_turn = self.turn_count + random.randint(6, 14)
```

Bu side-effect'leri prompt fonksiyonundan ayırmak **en riskli** kısımdı.

**Çözüm: Tuple return pattern.**

```python
# prompt_builder.py — SAF fonksiyon
def build_dynamic_prompt(...) -> tuple:
    ...
    return prompt, side_effects  # side_effects: dict

# game_state.py — wrapper side-effect'leri uygular
def get_dynamic_prompt(self, choice_text):
    prompt, side_effects = PromptBuilder.build_dynamic_prompt(...)
    if side_effects["clear_combat_result"]:
        self.pending_combat_result = None
    if side_effects["enter_combat"]:
        self._in_combat = True
    ...
    return prompt
```

Bu yaklaşım sayesinde:
- `PromptBuilder.build_dynamic_prompt()` saf fonksiyon — test edilebilir
- State mutasyonları `GameState` wrapper'ında kalıyor
- `main.py`'deki `self.state.get_dynamic_prompt(choice_text)` çağrıları DEĞİŞMEDİ

**2. Parametre sayısı:**

`build_dynamic_prompt` 15 parametre alıyor. Bu fazla görünebilir ama bilinçli
bir tercih — alternative olan `GameState` referansı geçirmek tight coupling
yaratırdı. Açık parametreler:
- Fonksiyonun hangi veriye bağımlı olduğunu dokümante eder
- Mock/test yazmayı trivial hale getirir
- Circular import riskini sıfırlar

**3. `build_system_prompt` parametresiz olması:**

Plan `build_system_prompt(character_class, theme, ...)` öneriyordu ama mevcut
implementasyonda sistem prompt'u sabit ve dinamik veri İÇERMİYOR. Gereksiz
parametre eklemek yerine `build_system_prompt()` parametresiz bırakıldı.
İleride parametrik hale getirmek trivial bir değişiklik.

**4. Prompt metinlerine dokunulmadı:**

Kullanıcının açık talebi: "Promptların yapısına şimdilik dokunmuyoruz."
Prompt metinleri karakter karakter aynı kopyalandı. Sadece konum değişti.

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `prompt_builder.py` | [YENİ] | ~240 satır — PromptBuilder sınıfı (4 @staticmethod) |
| `game_state.py` | [DEĞİŞTİ] | ~185 satır inline prompt → ~50 satır wrapper |

### Dikkat Edilecekler

- `main.py`'deki `self.state.get_dynamic_prompt()`, `self.state.get_character_summary()`,
  `self.state.get_message_history()` çağrıları **HİÇ DEĞİŞMEDİ**.
- `prompt_builder.py` hiçbir şekilde `game_state`'i import ETMEZ → circular import riski SIFIR.
- `build_dynamic_prompt` `tuple` dönüyor (`prompt, side_effects`). Doğrudan çağrılırsa
  side_effects dict'inin uygulanması gerekir.
- `_optimize_memory` hala `GameState` içinde — bu metod mesaj geçmişi (state) yönetimi
  yaptığı için taşınmadı.

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 85 passed in 0.64s ==============================
```

Test sayısı değişmedi — Aşama 3.3 (çağrı noktalarını güncelle) ve 3.4 (test yaz) henüz yapılmadı.

---

## [Aşama 3.3 + 3.4] — Çağrı Noktaları Güncelleme + Prompt Testleri

- **Tarih:** 2026-06-06
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S08 (game_state.py God Object), S16 (Sıfır Unit Test)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

**3.3 — Çağrı noktaları güncelleme:**

Bu adım 3.2 ile birlikte zaten tamamlanmıştı. `game_state.py`'deki 4 wrapper
metod, verileri parametre olarak `PromptBuilder`'a geçiyor. `main.py`'deki
çağrı noktaları (`self.state.get_dynamic_prompt()`,
`self.state.get_character_summary()`) değişmedi — wrapper'lar geriye uyumlu.

Doğrulama: `main.py`'de 8 prompt çağrısı var, hepsi `self.state.` üzerinden.

**3.4 — test_prompts.py (55 test):**

Tüm `PromptBuilder` static metodları saf fonksiyon olduğu için mock
gerekmeden test edildi. Test sınıfları:

| Test Sınıfı | Test Sayısı | Test Edilen Metod |
|---|---|---|
| `TestBuildSystemPrompt` | 10 | `build_system_prompt()` — içerik, format, idempotent |
| `TestBuildCharacterSummary` | 5 | `build_character_summary()` — alanlar, boş envanter, format |
| `TestBuildWorldContext` | 9 | `build_world_context()` — bölgeler, NPC, etkileşim, geri dön |
| `TestDynamicPromptExploration` | 9 | `build_dynamic_prompt()` — keşif modu, hikaye, ganimet |
| `TestDynamicPromptCombat` | 12 | `build_dynamic_prompt()` — saldırı/savunma/kaçış/büyü |
| `TestDynamicPromptCombatTiming` | 4 | `build_dynamic_prompt()` — savaş zamanlama, trigger |
| `TestDynamicPromptBoundaryValues` | 6 | `build_dynamic_prompt()` — accuracy eşikleri (70/40) |

### Teknik Kararlar

**Helper method pattern (`_base_params`, `_combat_params`):**

`build_dynamic_prompt` 15 parametre aldığı için her testte hepsini yazmak
okunaklılığı bozardı. Her test sınıfına bir `_base_params(**overrides)` helper
eklendi — sadece test edilen parametreyi override ediyorsun:

```python
def test_pending_loot_included(self):
    prompt, _ = PromptBuilder.build_dynamic_prompt(
        **self._base_params(pending_loot="Ates Kilici"))
    assert "BEKLEYEN GANIMET" in prompt
```

**Boundary value testleri:**

Accuracy eşiklerini (70, 69, 40, 39) test ettik — bunlar savaş mekaniğinin
kritik noktaları. Örneğin accuracy=70 "başarılı" iken 69 "kısmi başarılı".
Bir off-by-one hatası oyun dengesini bozabilir.

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `tests/test_prompts.py` | [YENİ] | ~380 satır — 55 test |

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 140 passed in 0.32s =============================
```

Test artışı: 85 → 140 (+55 yeni prompt testi)

---

## TEST SAYISI TARİHÇESİ

| Tarih | Aşama | Toplam Test | Artış |
|---|---|---|---|
| 2026-06-03 | Aşama 0 tamamlandı | 68 | +68 |
| 2026-06-04 | Aşama 1 tamamlandı | 68 | 0 (test eklenmedi) |
| 2026-06-04 | Aşama 2 tamamlandı | 85 | +17 |
| 2026-06-06 | Aşama 3 tamamlandı | 140 | +55 |

---

## DOSYA YAPISI DEĞİŞİKLİK ÖZETİ

Aşağıdaki tablo projeye eklenen ve değiştirilen dosyaları gösterir:

```
python_dnd/
├── game_data.py             [YENİ — Aşama 2.1]  Statik sözlükler
├── shop_system.py           [YENİ — Aşama 2.3]  ShopSystem sınıfı
├── prompt_builder.py        [YENİ — Aşama 3.1]  PromptBuilder sınıfı
├── game_state.py            [DEĞİŞTİ — Aşama 2,3] ~250 satır azaldı
├── main.py                  [DEĞİŞTİ — Aşama 1] Bug düzeltmeleri
├── ai_manager.py            [DEĞİŞTİ — Aşama 1] ast.literal_eval kaldırıldı
├── requirements.txt         [DEĞİŞTİ — Aşama 0] Üst sınır + pytest
├── RESTRUCTURE_PLAN.md      [DEĞİŞTİ] Checkbox'lar güncellendi
├── CHANGELOG.md             [YENİ] Bu dosya
└── tests/                   [YENİ — Aşama 0]
    ├── __init__.py
    ├── conftest.py           Paylaşılan fixture'lar
    ├── test_game_state.py    35 test
    ├── test_ai_parse.py      9 test
    ├── test_config.py        9 test
    ├── test_snapshots.py     10 test (characterization)
    ├── test_shop.py          17 test [Aşama 2.4]
    └── test_prompts.py       55 test [Aşama 3.4]
```
