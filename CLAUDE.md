# CLAUDE.md — python_dnd Projesi Ajan Rehberi

> **Son güncelleme:** 2026-06-19
> **Test durumu:** 237 test, 237 passed
> **Mevcut aşama:** Aşama 5 tamamı tamamlandı — Aşama 6 sırada

---

## 1. PROJE NEDİR?

Webcam kontrollü, el hareketleriyle oynanan bir D&D rol yapma oyunu.
- **Giriş:** El ile havada seçenek seçme (parmak izleme)
- **Motor:** Herhangi bir AI (hikaye üretimi)
- **Savaş:** Geometrik şekil çizme / yumruk challenge'ları
- **Dil:** Python 3.13, pygame + OpenCV + MediaPipe

---

## 2. NE YAPIYORUZ?

Projenin kodunu **hiçbir özelliği değiştirmeden** yeniden yapılandırıyoruz (refactoring).
God Object'ler (`main.py` 1304 satır, `game_state.py` 1020 satır) parçalanıyor.

### Rehber Belgeler

| Belge | Yol | Ne İçin |
|-------|-----|---------|
| **PRODUCT_VISION.md** | `e:\Projeler\python_dnd\PRODUCT_VISION.md` | Ürün vizyonu ve yön. Eleştirel durum tespiti (E01-E06), vizyon merdiveni (V1-V4), pazar notları (P01-P06), ajan kuralları (G01-G06). **Görev almadan önce oku.** |
| **RESTRUCTURE_PLAN.md** | `e:\Projeler\python_dnd\RESTRUCTURE_PLAN.md` | Ana yol haritası. Sorun kataloğu (S01-S22), bağımlılık haritası, aşamalar. |
| **CHANGELOG.md** | `e:\Projeler\python_dnd\CHANGELOG.md` | Yapılan her değişikliğin teknik detayı. Şablon dahil. |
| **TESTS_GUIDE.md** | `e:\Projeler\python_dnd\tests\TESTS_GUIDE.md` | Test yazma kuralları ve örnekler. |

---

## 3. MEVCUT DOSYA YAPISI

```
python_dnd/
├── main.py                 Ana oyun döngüsü + faz yönlendirme (~1060 satır)
├── game_state.py            Durum yönetimi + karakter + mesaj geçmişi (~810 satır)
├── game_data.py             [YENİ] Statik sözlükler (class/weapon/stat verileri)
├── shop_system.py           [YENİ] ShopSystem sınıfı (dükkan mantığı)
├── prompt_builder.py        [YENİ] PromptBuilder sınıfı (AI prompt üretimi)
├── combat_manager.py        [YENİ] CombatManager sınıfı (savaş hesaplamaları)
├── inventory_handler.py     [YENİ] InventoryHandler sınıfı (envanter hit-test/dwell)
├── game_phase.py            [YENİ] GamePhase Enum (faz geçişleri)
├── ai_manager.py            AI ile iletişim (litellm)
├── ui_renderer.py           Tüm çizim işlemleri (~900 satır, değişmez)
├── vision_engine.py         El takibi (MediaPipe)
├── shape_challenge.py       Şekil çizme challenge
├── fist_challenge.py        Yumruk challenge
├── dice_challenge.py        Zar challenge
├── music_manager.py         Müzik sistemi
├── config_manager.py        Ayar yönetimi
├── menu_system.py           Ana menü sistemi
└── tests/
    ├── conftest.py           Paylaşılan fixture'lar
    ├── test_game_state.py    46 test
    ├── test_ai_parse.py      9 test
    ├── test_config.py        9 test
    ├── test_snapshots.py     10 test (characterization)
    ├── test_shop.py          17 test
    ├── test_prompts.py       55 test
    ├── test_combat.py        63 test
    └── test_inventory.py     23 test
```

---

## 4. TAMAMLANAN AŞAMALAR

| Aşama | Açıklama | Durum |
|-------|----------|-------|
| 0 | Safety Net (pytest altyapısı, 68 test) | ✅ Tamamlandı |
| 1 | Bağımsız küçük düzeltmeler (S01, S04, S10, S11, S14) | ✅ Tamamlandı |
| 2 | Veri ayrıştırma → `game_data.py`, `shop_system.py` | ✅ Tamamlandı |
| 3 | Prompt ayrıştırma → `prompt_builder.py` | ✅ Tamamlandı |
| 4 | Savaş yöneticisi → `combat_manager.py` + S02, S05 fix | ✅ Tamamlandı (9/9) |
| 5.1 | Envanter → `inventory_handler.py` | ✅ Tamamlandı |
| 5.2 | `reset()` anti-pattern düzeltme (S12) | ✅ Tamamlandı |
| 5.3 | Faz geçişlerini Enum'a çevir (S09) | ✅ Tamamlandı |
| 5.4 | Çift `draw_inventory` çağrısı optimize (Performans) | ✅ Tamamlandı |

---

## 5. SIRADAKI GÖREVLER

### Sıradaki görevler: Aşama 6 — Güvenlik ve Platform

- 6.1: `.env` + `python-dotenv` (API key güvenliği)
- 6.2: `pyperclip` (clipboard erişimi)
- 6.3: Kamera paylaşımı (menü ↔ oyun)
- 6.4: `requirements.txt` güncelleme

---

## 6. KRİTİK KURALLAR (HER AJAN OKUMALI)

### 🔴 DOKUNMA LİSTESİ

1. **Türkçe prompt'lar** — Prompt metnini DEĞİŞTİRME. Bir kelimelik değişiklik bile
   tüm oyun mekaniğini bozabilir. Sadece dosya taşıma kabul edilir.
2. **Hasar formülleri** — Sayısal değerler (30-50 arası, 1.5x çarpan) korunmalı.
3. **Challenge süreleri** — `DRAW_TIME`, `COUNTDOWN_TIME`, `ACTIVE_DURATION` sabitleri.
4. **Doğruluk hesaplama** — `shape_challenge.py`'deki formül.
5. **El takip parametreleri** — Smoothing katsayıları, güven eşikleri.
6. **UI layout sabitleri** — `ui_renderer.py:53-110`.

### 🟡 İŞ AKIŞI KURALLARI

1. **Önce araştır, sonra yap:** Her görevden önce bağımlılık haritasına bak.
   İlgili dosyaları oku. Olası yan etkileri listele.
2. **Test kır, commit'leme:** Her değişiklik sonrası `python -m pytest tests/ -v` çalıştır.
3. **CHANGELOG'a yaz:** Her görev sonrası CHANGELOG.md'ye detaylı giriş ekle.
   Şablon CHANGELOG.md'nin başında var.
4. **RESTRUCTURE_PLAN'ı güncelle:** Tamamlanan görevleri `[x]` olarak işaretle.
   Çözülen sorunları da `[x]` olarak işaretle.

### 🟢 TEST YAZMA KURALLARI

- Yeni modül → yeni test dosyası (`test_<modül>.py`)
- `conftest.py`'deki `game_state` fixture'ı kullan
- Deterministic testler için `random.seed(42)` kullan
- UI/IO bağımlı kodu test ETME — sadece saf mantığı test et
- Detaylar: `tests/TESTS_GUIDE.md`

---

## 7. MİMARİ BİLGİ (SORU İŞARETLERİ İÇİN)

### Modül Sorumlulukları

| Modül | Rol | Bağımlılıklar |
|-------|-----|---------------|
| `main.py` | Oyun döngüsü, faz yönlendirme, UI/IO wrapper | Her şeye bağlı |
| `game_state.py` | Oyun durumu, karakter, mesaj geçmişi | game_data, shop_system, prompt_builder |
| `combat_manager.py` | Saf savaş hesaplama motoru | game_data (sadece veri) |
| `inventory_handler.py` | Saf hit-test/dwell karar motoru | Hiçbir şeye bağlı değil |
| `prompt_builder.py` | Saf prompt üretimi (static methods) | Hiçbir şeye bağlı değil |
| `shop_system.py` | Dükkan mantığı | Hiçbir şeye bağlı değil |
| `game_data.py` | Statik sözlükler | Hiçbir şeye bağlı değil |
| `game_phase.py` | Faz Enum tanımları | Hiçbir şeye bağlı değil |

### Delegasyon Deseni

main.py hiçbir zaman doğrudan hesaplama yapmaz. Her iş ilgili modüle delege edilir:

```
main.py (wrapper) → combat_manager.py (hesaplama)
main.py (wrapper) → inventory_handler.py (karar)
game_state.py     → shop_system.py (dükkan)
game_state.py     → prompt_builder.py (prompt)
```

Side-effect'ler (state değişikliği, UI çağrıları, cv2.imshow) **her zaman main.py'de** kalır.
Alt modüller saf hesaplama yapar ve sonucu döndürür.

### HP Akışı (S02 fix sonrası)

```
AI yanıtı → update_from_ai_response()
  ├── hp_degisim JSON → modify_hp()     ← TEK HP KAYNAĞI
  └── [HP:-10] tag   → sadece temizlenir, HP'ye UYGULANMAZ
```

### Dodge vs Savunma (S05 fix sonrası)

```
DEX yeterli → combat.dodged = True       → "DEX DODGE!" feedback
Savunma başarılı → combat.defense_blocked → "MUKEMMEL SAVUNMA!" feedback
UI: is_blocked_visual = dodged OR defense_blocked
```

### reset() (S12 fix sonrası)

```python
# ESKİ (anti-pattern):
def reset(self): self.__init__(Character())  # YANLIŞ

# YENİ:
def reset(self):
    self.character = Character()
    self._reset_to_defaults()  # __init__ ile aynı yardımcı
```

---

## 8. SORUN KATALOĞU DURUMU

### Çözülenler ✅
| ID | Sorun | Çözüm Aşaması |
|----|-------|---------------|
| S01 | `draw_buttons` parametre hatası | Aşama 1.1 |
| S02 | HP çift uygulama | Aşama 4.8 |
| S04 | `extra_turn_active` sıfırlanmıyor | Aşama 1.3 |
| S05 | Dodge/savunma karışıklığı | Aşama 4.9 |
| S10 | Savaş aksiyon string'leri dağınık | Aşama 1.4 |
| S11 | `_inv_hovered_*` attribute eksik | Aşama 1.2 |
| S12 | `reset()` anti-pattern | Aşama 5.2 |
| S14 | `ast.literal_eval` güvenlik riski | Aşama 1.5 |

### Kısmen Çözülenler 🟡
| ID | Sorun | Durum |
|----|-------|-------|
| S07 | main.py God Object | Büyük kısmı çözüldü (combat, inventory, faz Enum ayrıldı). |
| S08 | game_state.py God Object | Büyük kısmı çözüldü (data, shop, prompt ayrıldı). |
| S09 | State machine yok | İlk adım tamamlandı (Enum). Full State Pattern ileride değerlendirilecek. |
| S16 | Unit test eksik | 237 test var artık. CI/CD yok (S17). |

### Çözülmeyenler ⬜
| ID | Sorun | Planlanan Aşama |
|----|-------|-----------------|
| S03 | Savaş modunda AI prompt çelişkisi | Prompt dokunulmadığı için ertelendi |
| S06 | Ganimet anahtar kelime çakışması | Prompt dokunulmadığı için ertelendi |
| S13 | API key düz metin | Aşama 6.1 |
| S15 | Clipboard platform bağımlı | Aşama 6.2 |
| S17 | CI/CD yok | Ertelendi |
| S18 | requirements.txt üst sınır | Kısmen çözüldü (Aşama 0) |
| S19 | hand_landmarker indirme talimatı yok | Ertelendi |
| S20 | Windows'a sıkı bağımlılık | Ertelendi |
| S21 | Kamera olmadan oynanamaz | Ertelendi |
| S22 | Kaspersky çakışması | Aşama 6.2-6.3 |

---

## 9. KULLANICININ BEKLENTİLERİ

### Çalışma Tarzı
- Kullanıcı görevleri **aşama aşama** veriyor
- Her görevden önce **bağımlılık analizi + olası hata kontrolü** yapılmasını istiyor
- Sonrasında **CHANGELOG ve RESTRUCTURE_PLAN güncellenmesini** bekliyor
- **Temkinli** çalışılmasını istiyor — "sorunsuz iş istiyorum"

### Dil
- Kullanıcı Türkçe konuşuyor
- Kod yorumları Türkçe
- Commit mesajları / changelog Türkçe
- Prompt'lar Türkçe (dokunma!)

### Kullanıcının Vermediği Ama Bilmen Gereken

- API key'i geçersiz olabilir (`INVALID_ARGUMENT` hatası) — bu bizim sorunumuz değil
- Kamera gerekli (webcam) — kamera olmadan oyun çalışmaz
- Oyun `pygame` ile çalışır ama pencere `cv2.imshow` ile açılır (garip ama çalışıyor)
- `venv` klasörü `e:\Projeler\python_dnd\venv` altında

---

## 10. HIZLI KOMUTLAR

```bash
# Sanal ortamı aktive et
.\venv\Scripts\activate

# Testleri çalıştır
python -m pytest tests/ -v

# Oyunu başlat (kamera gerekli)
python main.py
```

---

## 11. CHANGELOG YAZIM ŞABLONU

Her görev tamamlandığında CHANGELOG.md'ye şu formatta ekleme yap:

```markdown
## [Aşama X.Y] — Görev Başlığı

- **Tarih:** YYYY-MM-DD
- **Agent:** (senin adın)
- **İlgili Sorunlar:** SXX (sorun açıklaması)
- **Plan Uyumu:** ✅ veya ⚠️

### Ne Yapıldı
(1-2 paragraf açıklama)

### Sorunun Anatomisi
(varsa eski davranış/yeni davranış karşılaştırması)

### Çözüm
(kod değişikliği özeti, diff veya snippet)

### Dosya Değişiklikleri
| Dosya | Durum | Değişiklik |
|-------|-------|-----------|

### Test Sonuçları
```
$ python -m pytest tests/ -v
============================= XXX passed in X.XXs =============================
```
```

---

> **Son not:** Bu dosya her büyük değişiklikten sonra güncellenmelidir.
> Yeni ajan, önce bu dosyayı oku → sonra RESTRUCTURE_PLAN.md'ye bak →
> sonra kullanıcıya sıradaki görevi sor.
