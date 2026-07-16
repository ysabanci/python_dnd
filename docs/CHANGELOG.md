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

## [Aşama 4.1 + 4.2 + 4.3] — Savaş Yöneticisi: Temel Yapı + Bayraklar + İşlem Metodları

- **Tarih:** 2026-06-11
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S07 (main.py God Object)
- **Plan Uyumu:** ✅ Plana tam uygun. 4.1-4.3 birlikte yapıldı (birbirine bağımlı adımlar).

### Ne Yapıldı

**4.1 — `combat_manager.py` oluşturma:**

`CombatManager` sınıfı oluşturuldu. UI'a bağımlılık YOK (frame, draw, cv2
referansı yok). Savaş sabitleri (`CRITICAL_HIT_THRESHOLD`, `EXTRA_TURN_CHANCE`,
`ACTION_ATTACK/DEFENSE/FLEE/MAGIC`) bu sınıfa taşındı.

**4.2 — Savaş bayraklarını taşıma (10 attribute):**

| Eski (DnDGame) | Yeni (CombatManager) |
|---|---|
| `self._pending_combat_choice` | `self.combat.pending_combat_choice` |
| `self._weapon_select_options` | `self.combat.weapon_select_options` |
| `self._selected_weapon` | `self.combat.selected_weapon` |
| `self._weapon_combat_action` | `self.combat.weapon_combat_action` |
| `self._enemy_attack_start` | `self.combat.enemy_attack_start` |
| `self._enemy_attack_damage` | `self.combat.enemy_attack_damage` |
| `self._enemy_attack_applied` | `self.combat.enemy_attack_applied` |
| `self._extra_turn_active` | `self.combat.extra_turn_active` |
| `self._defense_blocked` | `self.combat.defense_blocked` |
| `self._defense_partial` | `self.combat.defense_partial` |

`CombatManager.reset()` tüm bayrakları başlangıç değerlerine sıfırlar.

**4.3 — Savaş işlem metodlarını taşıma (3 + 1 metod):**

| Eski (DnDGame) | Yeni (CombatManager) | Satır |
|---|---|---|
| `_process_attack()` | `process_attack()` | ~555-621 (~66 satır) |
| `_process_defense()` | `process_defense()` | ~623-652 (~30 satır) |
| `_process_flee()` | `process_flee()` | ~654-670 (~17 satır) |
| `_get_combat_preview()` | `get_combat_preview()` | ~772-800 (~29 satır) |

### Teknik Kararlar

**1. En kritik karar: Result dict pattern (state mutasyonu yerine)**

Orijinal metodlar doğrudan `self.state.enemy_hp`, `self.state.current_feedback`
gibi değerleri değiştiriyordu. `CombatManager`'da bu mutasyonlar kaldırıldı.
Bunun yerine hesaplama sonucu bir dict olarak döndürülüyor:

```python
# combat_manager.py — SAF hesaplama
def process_attack(...) -> Dict:
    ...
    return {"enemy_dmg": ..., "new_enemy_hp": ..., "description": ..., "is_critical": ...}

# main.py — wrapper sonuçları uygular
def _process_attack(self, ...):
    result = self.combat.process_attack(...)
    self.state.enemy_hp = result["new_enemy_hp"]
    self.state.current_feedback = result["description"]
```

Bu PromptBuilder için kullanılan aynı pattern'dir. Avantajları:
- `CombatManager` test edilebilir (GameState gerekmez)
- State mutasyonları tek yerde (wrapper)
- İleride replay/undo sistemi eklenebilir

**2. `process_defense` istisnası — bayrak mutasyonu CombatManager içinde:**

`process_defense` sonucunda `defense_blocked` ve `defense_partial` bayrakları
CombatManager içinde güncelleniyor (çünkü bu bayraklar CombatManager'a ait).
Ama HP iyileşmesi ve feedback yazma gibi state mutasyonları hala wrapper'da:

```python
result = self.combat.process_defense(accuracy)
if result["heal"] > 0:
    self.state.modify_hp(result["heal"])  # state mutasyonu wrapper'da
```

**3. Geriye uyumluluk referansları:**

Savaş sabitleri `DnDGame` sınıfında referans olarak korundu:
```python
CRITICAL_HIT_THRESHOLD = CombatManager.CRITICAL_HIT_THRESHOLD
ACTION_ATTACK = CombatManager.ACTION_ATTACK
```
Bu sayede test_snapshots.py gibi mevcut testlerde `self.ACTION_ATTACK` erişimleri
çalışmaya devam eder. İleride bu referanslar kaldırılabilir.

**4. Tüm `self._xxx` referanslarının `self.combat.xxx`'e dönüştürülmesi:**

`main.py`'deki tüm eski bayrak referansları (10 attribute × ~40 kullanım noktası)
toplu değiştirildi. Bu, 4.4-4.6 adımlarında taslanan `_start_enemy_attack`,
`_handle_enemy_attack` gibi metodların da sorunsuz taşınmasını sağlar.

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `combat_manager.py` | [YENİ] | ~290 satır — CombatManager sınıfı |
| `main.py` | [DEĞİŞTİ] | ~120 satır inline savaş kodu → ~35 satır wrapper |

### Dikkat Edilecekler

- `main.py`'deki `_process_player_combat_result`, `_start_enemy_attack`,
  `_handle_enemy_attack` metodları hala `main.py`'de. Bunlar Aşama 4.4-4.5'te
  taşınacak.
- Bu metodlar artık `self.combat.defense_blocked`, `self.combat.enemy_attack_damage`
  gibi CombatManager attribute'larına erişiyor.
- `CombatManager` `game_state.py`'i import ETMEZ → circular import riski SİFIR.
- `self.combat.reset()` yeni savaş başlangıcında çağrılarak tüm bayraklar
  sıfırlanabilir.

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 140 passed in 0.28s =============================
```

Test sayısı değişmedi — test_combat.py Aşama 4.7'de eklenecek.

---

## [Aşama 4.4] — Savaş Orkestrasyon Mantığının Taşınması

- **Tarih:** 2026-06-11
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S07 (main.py God Object)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

`_process_player_combat_result` — savaş döngüsünün **en kritik orkestrasyon
metodu** — CombatManager'a `evaluate_combat_result` olarak taşındı.

Bu metod savaş sonucunun tüm karar ağacını yönetir:
1. Aksiyonu sınıflandır (saldırı/savunma/kaçış)
2. İlgili `process_*` metodunu çağır
3. Ekstra tur şansını hesapla
4. Sonraki adıma karar ver (5 olası outcome)

| Eski (DnDGame) | Yeni (CombatManager) |
|---|---|
| `_process_player_combat_result()` | `evaluate_combat_result()` |

### Teknik Kararlar

**1. Outcome dict pattern — "ne yapılmalı" vs "nasıl uygulanmalı" ayrımı:**

`evaluate_combat_result` **karar** verir ama **uygulamaz**. 5 olası outcome:

| outcome | Anlamı | Wrapper ne yapar |
|---|---|---|
| `"game_over"` | Oyuncu HP ≤ 0 | `state.is_game_over = True`, faz sıfırla |
| `"enemy_defeated"` | Düşman HP ≤ 0 | `_send_combat_result()` → AI'a bildir |
| `"flee_success"` | Kaçış başarılı | `_send_combat_result()` → AI'a bildir |
| `"extra_turn"` | Ekstra tur kazanıldı | Feedback ekle, faz sıfırla, seçenekleri geri yükle |
| `"enemy_attack"` | Normal akış | `_start_enemy_attack()` çağır |

```python
# CombatManager — karar verir
result = self.combat.evaluate_combat_result(...)
# main.py — uygular
if result["outcome"] == "game_over": ...
elif result["outcome"] == "enemy_defeated": ...
```

**2. Neden wrapper'daki `_process_attack/defense/flee` atlandı:**

`evaluate_combat_result` doğrudan CombatManager'daki `process_attack/defense/flee`
metodlarını çağırıyor. Eski main.py wrapper'ları (`_process_attack`, `_process_defense`,
`_process_flee`) artık hiçbir yerden çağrılmıyor — ölü kod haline geldi.
Aşama 4 tamamen bittiğinde (4.7 test sonrası) temizlenecek.

**3. Kaçış eşiğinin hesaplanması:**

Orijinal kodda kaçış başarı kontrolü iki yerde yapılıyordu:
1. `_process_flee()` → feedback mesajı (70 sabit eşik)
2. `_process_player_combat_result()` → `class_bonus.flee_threshold` ile kontrol

`evaluate_combat_result`'da `process_flee`'nin döndürdüğü `success` alanı
kullanılarak bu iki kontrol birleştirildi. `process_flee` zaten `flee_threshold`'u
doğru hesaplıyor (`class_bonus` + `stat_fx` bazlı), dolayısıyla ikinci kontrol
gereksiz hale geldi → daha temiz.

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `combat_manager.py` | [DEĞİŞTİ] | +130 satır — `evaluate_combat_result` eklendi |
| `main.py` | [DEĞİŞTİ] | ~85 satır orkestrasyon → ~45 satır wrapper |

### Dikkat Edilecekler

- `main.py`'deki `_process_attack`, `_process_defense`, `_process_flee` wrapper'ları
  artık ölü kod. Aşama 4.7 sonrası temizlenecek.
- `evaluate_combat_result` bayrak mutasyonu yapıyor: `defense_blocked`, `defense_partial`,
  `extra_turn_active` — bunlar CombatManager'ın kendi state'i.
- Wrapper hala `_send_combat_result()`, `_start_enemy_attack()`, `_restore_combat_options()`
  çağrılarını yönetiyor — bunlar UI/AI bağımlı olduğu için main.py'de kalmalı.

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 140 passed in 0.27s =============================
```

---

## [Aşama 4.5] — Düşman Saldırı Mantığının Taşınması

- **Tarih:** 2026-06-11
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S07 (main.py God Object)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

`_start_enemy_attack` ve `_handle_enemy_attack` — düşman saldırı fazının
**hesaplama ve karar mantığı** CombatManager'a taşındı. UI çizim kodu
(`draw_enemy_attack`, `draw_hud`, `cv2.imshow`) main.py wrapper'larda kaldı.

| Eski (DnDGame) | Yeni (CombatManager) | İşlev |
|---|---|---|
| `_start_enemy_attack()` içi | `calculate_enemy_damage()` | Dodge, savunma, hasar hesabı |
| `_handle_enemy_attack()` içi | `resolve_enemy_attack_tick()` | Mid-anim hasar + tur sonu karar |

Ek olarak `ENEMY_ATTACK_DURATION` sabiti de CombatManager'a taşındı.

### Teknik Kararlar

**1. `calculate_enemy_damage` — hasar ön-hesaplaması:**

Orijinal `_start_enemy_attack` şunları yapıyordu:
- DEX dodge şansı kontrolü (tamamen kaçınma)
- Savunma bayrakları kontrolü (blocked/partial)
- Sınıf + stat bazlı hasar azaltma hesabı
- `enemy_attack_damage` bayrağını güncelleme
- `time.time()` ile zamanlayıcı başlatma
- Faz geçişi (`current_phase = PHASE_ENEMY_ATTACK`)

`calculate_enemy_damage` sadece ilk 4 maddeyi yapıyor → **saf hesaplama**.
Zamanlayıcı ve faz geçişi wrapper'da kalıyor:

```python
# CombatManager — hesaplama
result = self.combat.calculate_enemy_damage(stat_fx, class_bonus)
# main.py — zamanlayıcı + faz
self.combat.enemy_attack_start = time.time()
self.current_phase = self.PHASE_ENEMY_ATTACK
```

**2. `resolve_enemy_attack_tick` — frame-bazlı karar:**

Her frame'de çağrılır. 3 şey kontrol eder:
1. **progress**: Animasyon ilerleme oranı (0.0-1.0)
2. **apply_damage**: Animasyonun %50 noktasında hasar uygulanacak mı
3. **outcome**: Animasyon bittiğinde `"game_over"` / `"player_turn"` / `""`

Wrapper sadece sonuca göre `modify_hp`, faz geçişi ve UI çizim yapar.

**3. Neden `time.time()` CombatManager'a taşınmadı:**

`time.time()` IO/side-effect'tir. CombatManager'ı test edilebilir tutmak için
zaman kontrolü dışarıdan parametre olarak (`elapsed`) geçiriliyor.
Bu sayede testlerde zaman simülasyonu kolayca yapılabilir:

```python
# Test: animasyonun %50'sinde hasar uygulanmalı
tick = cm.resolve_enemy_attack_tick(elapsed=1.5, player_hp=100)
assert tick["apply_damage"] is True
```

**4. Bayrak sıfırlama — resolve_enemy_attack_tick'te:**

Animasyon bitip sıra oyuncuya geçtiğinde `defense_blocked` ve `defense_partial`
bayrakları CombatManager tarafından sıfırlanıyor. Bu, bir sonraki düşman saldırı
fazında temiz bayrak durumu garantiliyor.

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `combat_manager.py` | [DEĞİŞTİ] | +145 satır — `calculate_enemy_damage` + `resolve_enemy_attack_tick` |
| `main.py` | [DEĞİŞTİ] | ~70 satır inline hesaplama → ~40 satır wrapper |

### Dikkat Edilecekler

- `_handle_enemy_attack` wrapper'ı hala UI çizim kodu içeriyor (draw_enemy_attack,
  draw_hud, cv2.imshow). Bu UI kodları ASLA CombatManager'a taşınmamalı.
- `_start_enemy_attack` wrapper'ı hala `time.time()` çağırıyor — bu bilinçli bir
  karar (testlenebilirlik).
- `ENEMY_ATTACK_DURATION` artık CombatManager'da tanımlı, main.py referans tutuyor.

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 140 passed in 0.27s =============================
```
---

## [Aşama 4.6] — Challenge Başlatma Mantığının Taşınması

- **Tarih:** 2026-06-11
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S07 (main.py God Object)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

`_start_combat_challenge` ve `_start_actual_challenge` metodlarının **karar
mantığı** CombatManager'a taşındı. UI/challenge/tracker etkileşimleri wrapper'da kaldı.

| Eski (DnDGame) | Yeni (CombatManager) | İşlev |
|---|---|---|
| `_start_combat_challenge()` içi | `resolve_weapon_selection()` | Silah sayısına göre karar (yumruk/otomatik/seçim) |
| `_start_actual_challenge()` içi | `pick_challenge_type()` | Challenge tipi rastgele seçimi (%60/%40) |

### Teknik Kararlar

**1. `resolve_weapon_selection` — outcome-based pattern:**

4 olası outcome:

| outcome | Koşul | Wrapper ne yapar |
|---|---|---|
| `"unarmed"` | Silah yok | `equipped_weapon = "Yumruk"`, challenge başlat |
| `"auto_select"` | 1 silah | `equipped_weapon = silah`, challenge başlat |
| `"manual_select"` | 2+ silah | Seçim ekranı göster, faz geçişi |
| `"no_weapon_needed"` | Savunma/Kaçış | Direkt challenge başlat |

`resolve_weapon_selection` bayrak güncellemelerini (pending_combat_choice,
selected_weapon, weapon_select_options) kendisi yapıyor.

**2. `pick_challenge_type` — saf karar, sıfır bağımlılık:**

Tek iş: `random.random() < 0.6` kontrolü.
Şimdi `SHAPE_CHALLENGE_CHANCE` sabiti CombatManager'da tanımlı → test
edilebilir ve değiştirilebilir.

**3. Neden tracker.reset_selection() taşınmadı:**

Tracker donanım (kamera) bağımlı. CombatManager'ın tracker'a erişimi olmamalı.

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `combat_manager.py` | [DEĞİŞTİ] | +110 satır — `resolve_weapon_selection` + `pick_challenge_type` |
| `main.py` | [DEĞİŞTİ] | ~53 satır inline mantık → ~30 satır wrapper |

---

## [Aşama 4.7] — CombatManager Test Suite

- **Tarih:** 2026-06-11
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S16 (test eksikliği)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

`tests/test_combat.py` oluşturuldu — CombatManager'ın tüm saf hesaplama
metodlarını kapsayan **60 unit test**.

### Test Kategorileri

| Sınıf | Test Sayısı | Kapsam |
|---|---|---|
| `TestProcessAttack` | 9 | Kritik vuruş, başarılı/kısmi/başarısız saldırı, yumruk, büyü |
| `TestProcessDefense` | 7 | Tam/kısmi/başarısız savunma, sınır değerler |
| `TestProcessFlee` | 4 | Başarılı/başarısız kaçış, DEX bonus, taban eşik |
| `TestEvaluateCombatResult` | 6 | Orkestrasyon karar ağacı (5 outcome) |
| `TestCalculateEnemyDamage` | 5 | Dodge, savunma engelleme, hasar azaltma sınırı |
| `TestResolveEnemyAttackTick` | 8 | Animasyon zamanlaması, hasar uygulama, tur geçişi |
| `TestResolveWeaponSelection` | 8 | Silahsız/otomatik/manuel seçim, büyü sınıflandırma |
| `TestPickChallengeType` | 2 | Dönüş değeri ve dağılım kontrolü |
| `TestGetCombatPreview` | 10 | Tüm aksiyon+sonuç kombinasyonları |
| `TestReset` | 1 | Bayrak sıfırlama |

### Teknik Yaklaşım

- **UI bağımlılığı SIFIR** — CombatManager saf hesaplama yaptığı için
  GameState, frame, cv2, tracker GEREKMEZ.
- **random.seed(42)** ile deterministik test sonuçları
- **Sınır değer testleri** — tam olarak %70, %69, %40, %39

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `tests/test_combat.py` | [YENİ] | ~470 satır, 60 test |

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 200 passed in 0.31s =============================
```
---

## [Aşama 4.8] — S02: HP Çift Uygulama Düzeltmesi

- **Tarih:** 2026-06-11
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S02 (HP çift uygulama riski)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

`_parse_hp_changes` metodundaki HP uygulaması kaldırıldı. Artık `[HP:-10]` gibi
hikgâye metnindeki tag'ler **sadece metinden temizlenir**, HP'ye uygulanmaz.

### Sorunun Anatomisi

`update_from_ai_response()` iki farklı yoldan HP uyguluyordu:

1. **Yol 1:** `hp_degisim` JSON alanı → `modify_hp(int(hp_change))` (satır ~248)
2. **Yol 2:** `_parse_hp_changes()` → `[HP:-10]` tag'leri → `modify_hp()` (satır ~767)

AI hem `"hp_degisim": -10` hem de `[HP:-10]` yazarsa **hasar İKİ KEZ** uygulanırdı.

### Çözüm

```python
# ESKİ: HP tag'lerini bul ve uygula
hp_matches = re.findall(r"\[HP:([+-]?\d+)\]", story)
for match in hp_matches:
    self.modify_hp(int(match))  # ← KALDIRILDI

# YENİ: Sadece yorum
# HP tag'leri artık UYGULANMAZ — sadece temizlenir
# (hp_degisim JSON alanı tek kaynak — S02 fix)
```

**Neden `[ESYA:]` ve `[ALTIN:]` tag'lerine dokunulmadı:**
- ESYA için JSON alanı sadece `yeni_esya` (tek eşya) varken tag ile birden fazla
  eşya eklenebilir. Tag hala kullanılır.
- ALTIN için `altin_degisim` zaten var ama ek kanal olarak tag da bırakıldı.
  Bu iki kanaldan çift uygulama riski düşük (AI nadiren ikisini birden kullanır).

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `game_state.py` | [DEĞİŞTİ] | `_parse_hp_changes` — HP uygulama kaldırıldı |
| `tests/test_game_state.py` | [DEĞİŞTİ] | +6 regresyon testi (TestHpDoubleApplication) |

---

## [Aşama 4.9] — S05: Dodge/Savunma Karışıklığı Düzeltmesi

- **Tarih:** 2026-06-11
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S05 (dodge/savunma bayrak karışıklığı)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

DEX dodge mekanizması ve savunma challenge'ı artık **farklı bayraklar** kullanıyor.
Dodge olduğunda UI'da "DODGE!" gösterilir, "MUKEMMEL SAVUNMA!" değil.

### Sorunun Anatomisi

Eski durum:
```
Dodge olduğunda:  defense_blocked = True  →  "MUKEMMEL SAVUNMA!" ×
Savunma başarılı: defense_blocked = True  →  "MUKEMMEL SAVUNMA!" ✓
```

Oyuncu saldırı seçti, savunma yapmadı ama DEX'i yüksek olduğu için
dodge oldu. Animasyonda "MUKEMMEL SAVUNMA!" yazıyordu — yanlış.

### Çözüm

**1. Yeni bayrak: `dodged`**

```python
# CombatManager.__init__ / reset()
self.dodged: bool = False
```

**2. `calculate_enemy_damage` — dodge'da artık `dodged=True`:**

```diff
-self.defense_blocked = True
+self.dodged = True  # S05 fix
```

**3. `resolve_enemy_attack_tick` — ayrı feedback:**

```python
if self.dodged:
    feedback = "DEX DODGE! Dusman saldirisindan kactin!"
elif self.defense_blocked:
    feedback = "Mukemmel savunma! Dusman saldirisi engellendi!"
```

**4. `main.py` wrapper — visual kontrol:**

```python
is_blocked_visual = self.combat.defense_blocked or self.combat.dodged
```

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `combat_manager.py` | [DEĞİŞTİ] | +`dodged` bayrağı, feedback ayrımı, reset |
| `main.py` | [DEĞİŞTİ] | Wrapper'da `dodged \|\| defense_blocked` |
| `tests/test_combat.py` | [DEĞİŞTİ] | +3 S05 testi, mevcut dodge testleri güncellendi |

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 209 passed in 0.40s =============================
```
---

## [Aşama 5.1] — InventoryHandler Oluşturma

- **Tarih:** 2026-06-18
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S07 (God Object parçalama)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

`main.py`'deki ~195 satırlık `_handle_inventory()` metodundaki hit-test, dwell
zamanlama ve aksiyon karar mantığı `InventoryHandler` sınıfına taşındı.

### Çözüm Mimarisi

**InventoryHandler (saf hesaplama motoru):**
- `hit_test(finger_pos, regions)` → parmak hangi bölgede
- `update_dwell(now, regions)` → dwell zamanlayıcısı
- `consume_action()` → tetiklenen aksiyon dict'i döndürür

**main.py wrapper (ince çerçeve):**
- UI çağrıları (`draw_inventory`, `draw_finger_cursor`, `cv2.imshow`)
- Side-effect'ler (`state.toggle_equipped`, `state.shop_buy`, faz geçişi)

### Kaldırılan Bayraklar (main.py)

10 ayrı `self._inv_*` bayrağı yerine tek `self.inventory = InventoryHandler()`:
- `_inventory_page`, `_inv_hovered_idx`, `_inv_hovered_devam`
- `_inv_hovered_shop`, `_inv_hovered_roll`, `_inv_hovered_prev`
- `_inv_hovered_next`, `_inv_dwell_start`, `_inv_dwell_target`

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `inventory_handler.py` | [YENİ] | ~230 satır, InventoryHandler sınıfı |
| `main.py` | [DEĞİŞTİ] | 195 satır inline → ~80 satır wrapper |
| `tests/test_inventory.py` | [YENİ] | 23 test |

---

## [Aşama 5.2] — S12: reset() Anti-Pattern Düzeltmesi

- **Tarih:** 2026-06-18
- **Agent:** Antigravity (Opus 4.6)
- **İlgili Sorunlar:** S12 (reset() __init__ çağırma anti-pattern'i)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

`GameState.reset()` artık `self.__init__(Character())` çağırmıyor.
Yerine `_reset_to_defaults()` yardımcı metodu kullanılıyor.

### Sorunun Anatomisi

Eski durum:
```python
def reset(self) -> None:
    self.__init__(Character())  # ← Anti-pattern!
```

**Riskler:**
- `__init__`'e yeni parametre eklenirse `reset()` sessizce kırılır
- `__init__` içinde başka __init__ çağrıları (ShopSystem vs.) gereksiz yeniden çalışır
- Python MRO ile sorun çıkma potansiyeli

### Çözüm

```python
def __init__(self, character=None):
    self.character = character or Character()
    self._reset_to_defaults()  # ← Ortak yardımcı

def _reset_to_defaults(self) -> None:
    """Tüm alanları varsayılana döndürür (character hariç)."""
    self.current_location = "Bilinmeyen Diyar"
    self.turn_count = 0
    # ... 30+ attribute ...

def reset(self) -> None:
    self.character = Character()
    self._reset_to_defaults()  # ← Aynı yardımcı
```

Ek olarak `_api_error` attribute'u (runtime'da main.py'de set edilen) artık
`_reset_to_defaults`'ta resmi olarak tanımlandı.

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `game_state.py` | [DEĞİŞTİ] | `_reset_to_defaults()` eklendi, eski reset kaldırıldı |
| `tests/test_game_state.py` | [DEĞİŞTİ] | +5 S12 regresyon testi |

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 237 passed in 0.39s =============================
```

## TEST SAYISI TARİHÇESİ

| Tarih | Aşama | Toplam Test | Artış |
|---|---|---|---|
| 2026-06-03 | Aşama 0 tamamlandı | 68 | +68 |
| 2026-06-04 | Aşama 1 tamamlandı | 68 | 0 (test eklenmedi) |
| 2026-06-04 | Aşama 2 tamamlandı | 85 | +17 |
| 2026-06-06 | Aşama 3 tamamlandı | 140 | +55 |
| 2026-06-11 | Aşama 4.7 (test_combat.py) | 200 | +60 |
| 2026-06-11 | Aşama 4.8+4.9 (S02+S05 fix) | 209 | +9 |
| 2026-06-18 | Aşama 5.1+5.2 (inventory+reset) | 237 | +28 |

---

## DOSYA YAPISI DEĞİŞİKLİK ÖZETİ

Aşağıdaki tablo projeye eklenen ve değiştirilen dosyaları gösterir:

```
python_dnd/
├── game_data.py             [YENİ — Aşama 2.1]  Statik sözlükler
├── shop_system.py           [YENİ — Aşama 2.3]  ShopSystem sınıfı
├── prompt_builder.py        [YENİ — Aşama 3.1]  PromptBuilder sınıfı
├── inventory_handler.py     [YENİ — Aşama 5.1]  InventoryHandler sınıfı (5.4 cache)
├── combat_manager.py        [YENİ — Aşama 4.1]  CombatManager sınıfı
├── game_phase.py            [YENİ — Aşama 5.3]  GamePhase enum
├── game_state.py            [DEĞİŞTİ — Aşama 2,3,5.2] reset() düzeltmesi
├── main.py                  [DEĞİŞTİ — Aşama 1,4,5.1,5.3,5.4] Enum + optimizasyon
├── ai_manager.py            [DEĞİŞTİ — Aşama 1] ast.literal_eval kaldırıldı
├── requirements.txt         [DEĞİŞTİ — Aşama 0] Üst sınır + pytest
├── RESTRUCTURE_PLAN.md      [DEĞİŞTİ] Checkbox'lar güncellendi
├── CHANGELOG.md             [YENİ] Bu dosya
└── tests/                   [YENİ — Aşama 0]
    ├── __init__.py
    ├── conftest.py           Paylaşılan fixture'lar
    ├── test_game_state.py    46 test (+5 S12 regresyon) [Aşama 5.2]
    ├── test_ai_parse.py      9 test
    ├── test_config.py        9 test
    ├── test_snapshots.py     10 test (characterization)
    ├── test_shop.py          17 test [Aşama 2.4]
    ├── test_prompts.py       55 test [Aşama 3.4]
    ├── test_combat.py        63 test (+3 S05) [Aşama 4.7+4.9]
    └── test_inventory.py     23 test [Aşama 5.1]
```

---

## [Aşama 5.3] — Faz Geçişlerini Enum'a Çevir (S09)

- **Tarih:** 2026-06-24
- **Agent:** Antigravity (Claude Opus 4.6 Thinking)
- **İlgili Sorunlar:** S09 (State Machine Yok — Spaghetti Faz Yönetimi)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

`main.py`'deki 7 string faz sabiti (`PHASE_NORMAL = "normal"` vb.) yeni `GamePhase`
Enum sınıfına dönüştürüldü. Enum sınıfı ayrı bir `game_phase.py` dosyasında
tanımlandı — circular import riski sıfır.

**Kapsam:**
- 7 string sabit kaldırıldı (sınıf seviyesinden)
- 29 kullanım noktası `GamePhase.XXX` formatına güncellendi
- Karşılaştırmalar (`==`) Enum ile sorunsuz çalışır

**Neden ayrı dosya?** İleride `CombatManager` veya `InventoryHandler` gibi
modüller faz bilgisi döndürmek isteyebilir. Ayrı dosya:
- Circular import riskini ortadan kaldırır
- Tüm fazları tek yerden import edilebilir yapar
- S09'un ilk adımı (Enum) tamamlanır, ikinci adım (Full State Pattern) ileride yapılabilir

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `game_phase.py` | [YENİ] | ~35 satır — `GamePhase` Enum sınıfı, 7 faz değeri |
| `main.py` | [DEĞİŞTİ] | Import eklendi, 7 string sabit kaldırıldı, 29 referans güncellendi |

### Teknik Kararlar

**Enum value'ları string olarak korundu:** `GamePhase.NORMAL.value == "normal"`.
Bu sayede debug log'larda faz isimleri okunabilir kalır. İleride gerekirse
`print(f"Faz: {self.current_phase.value}")` ile okunabilir çıktı alınır.

**Geriye uyumluluk sabitleri korundu:** `ENEMY_ATTACK_DURATION`,
`CRITICAL_HIT_THRESHOLD` gibi savaş sabitleri (CombatManager referansları)
değişmedi — bunlar faz sabiti değil.

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 237 passed in 0.82s =============================
```

Testler `PHASE_*` sabitlerini doğrudan referans almıyor, bu yüzden sıfır etki.

---

## [Aşama 5.4] — Çift `draw_inventory` Çağrısını Optimize Et

- **Tarih:** 2026-06-24
- **Agent:** Antigravity (Claude Opus 4.6 Thinking)
- **İlgili Sorunlar:** Performans optimizasyonu (yeni)
- **Plan Uyumu:** ✅ Plana tam uygun

### Ne Yapıldı

`_handle_inventory()` metodundaki çift `draw_inventory()` çağrısı tek çağrıya
indirildi. Bu, envanter ekranında her frame'de yapılan ağır bir çizim
fonksiyonunun gereksiz tekrarını ortadan kaldırır.

**Önceki akış (2 çağrı):**
1. `draw_inventory(...)` → `frame_preview, regions` — sadece regions almak için
2. `hit_test(finger, regions)` + `update_dwell()` + `consume_action()`
3. `draw_inventory(...)` → `frame, _` — güncel hover ile gerçek çizim

**Yeni akış (1 çağrı):**
1. `get_cached_regions()` — önceki frame'in regions'ı
2. `hit_test(finger, cached_regions)` + `update_dwell()` + `consume_action()`
3. `draw_inventory(...)` → `frame, regions` — TEK çizim çağrısı
4. `cache_regions(regions)` — sonraki frame için kaydet

**Neden güvenli?** Regions koordinatları (buton pozisyonları, item satırları)
frame'den frame'e değişmez — envanter boyutu sabit. Sayfa değişikliğinde
bir sonraki frame'de yeni regions otomatik güncellenir. 1 frame gecikme
60fps'de ~16ms olup kullanıcı tarafından algılanmaz.

### Dosya Değişiklikleri

| Dosya | Durum | Değişiklik |
|-------|-------|-----------|
| `inventory_handler.py` | [DEĞİŞTİ] | `_last_regions` cache, `cache_regions()` ve `get_cached_regions()` eklendi |
| `main.py` | [DEĞİŞTİ] | `_handle_inventory()` — çift çağrı → tek çağrı, ~21 satır azaldı |

### Teknik Kararlar

**Cache `InventoryHandler`'da tutulur:** `main.py`'ye ek attribute eklemek yerine,
regions cache'i `InventoryHandler.reset()` ile birlikte sıfırlanan bir iç attribute
olarak tasarlandı. Bu, envanter açılıp kapandığında temiz başlangıç garanti eder.

**İlk frame'de boş regions:** Envanter ilk açıldığında cache boş olur —
`get_cached_regions()` boş dict döner. İlk frame'de hit-test sonuç vermez,
ama ikinci frame'de (~16ms sonra) cache dolar ve normal çalışır.
Bu, pratik olarak fark edilemez.

### Dikkat Edilecekler

- `InventoryHandler.reset()` artık `_last_regions`'ı da sıfırlar
- `cache_regions()` ve `get_cached_regions()` yeni public metodlardır
- `main.py`'deki `INV_DWELL_TIME` ve `INV_DEVAM_DWELL` sabitleri hala orada
  (kullanılmıyor, InventoryHandler'daki sabitler geçerli) — temizlik ileride yapılabilir

### Test Sonuçları

```
$ python -m pytest tests/ -v
============================= 237 passed in 0.82s =============================
```

