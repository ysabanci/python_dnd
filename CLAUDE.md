# CLAUDE.md — python_dnd Projesi Ajan Rehberi

> **Son güncelleme:** 2026-07-16
> **Test durumu:** 242 test, 242 passed
> **Mevcut aşama:** Restructure TAMAMLANDI (Aşama 0-6 + dosya ağacı).
> Sırada: dağıtım + V1 efekt katmanı (bkz. PRODUCT_VISION.md Bölüm 6).

---

## 1. PROJE NEDİR?

Webcam kontrollü, el hareketleriyle oynanan bir D&D rol yapma oyunu.
- **Giriş:** El ile havada seçenek seçme (parmak izleme)
- **Motor:** Herhangi bir AI (hikaye üretimi, litellm üzerinden)
- **Savaş:** Geometrik şekil çizme / yumruk challenge'ları
- **Dil:** Python 3.13, pygame + OpenCV + MediaPipe

**Nihai hedef bu değil:** Proje, oyuncunun kendisini ekranda kahraman olarak
gördüğü webcam-AR RPG'ye evrilecek. Görev almadan önce
`docs/PRODUCT_VISION.md` oku — vizyon merdiveni (V1-V4) ve ajan kuralları
(G01-G06) orada.

---

## 2. REHBER BELGELER

| Belge | Yol | Ne İçin |
|-------|-----|---------|
| **PRODUCT_VISION.md** | `docs/PRODUCT_VISION.md` | Ürün vizyonu ve yön. Eleştiriler (E01-E06), vizyon merdiveni (V1-V4), pazar notları (P01-P06), ajan kuralları (G01-G06). **Görev almadan önce oku.** |
| **RESTRUCTURE_PLAN.md** | `docs/RESTRUCTURE_PLAN.md` | Tamamlanmış refactoring yol haritası. Sorun kataloğu (S01-S22) referans olarak hala geçerli. |
| **CHANGELOG.md** | `docs/CHANGELOG.md` | Yapılan her değişikliğin teknik detayı. Şablon başta. |
| **TESTS_GUIDE.md** | `tests/TESTS_GUIDE.md` | Test yazma kuralları ve örnekler. |

---

## 3. DOSYA YAPISI (2026-07-16 sonrası)

```
python_dnd/
├── main.py                  Giriş noktası + DnDGame (oyun döngüsü, faz yönlendirme)
├── game/
│   ├── core/                SAF MANTIK (UI/IO yok, hepsi test edilebilir)
│   │   ├── game_state.py        Durum + karakter + mesaj geçmişi
│   │   ├── game_data.py         Statik sözlükler (class/weapon/stat)
│   │   ├── game_phase.py        GamePhase Enum
│   │   ├── combat_manager.py    Savaş hesaplama motoru
│   │   ├── inventory_handler.py Envanter hit-test/dwell kararları
│   │   ├── shop_system.py       Dükkan mantığı
│   │   └── prompt_builder.py    AI prompt üretimi (static methods)
│   ├── ai/ai_manager.py         AI iletişimi (litellm, thread'li)
│   ├── vision/
│   │   ├── vision_engine.py     El takibi (MediaPipe HandLandmarker)
│   │   └── camera_manager.py    Paylaşılan kamera (S22 fix)
│   ├── challenges/              shape / fist / dice challenge'ları
│   ├── ui/
│   │   ├── ui_renderer.py       Tüm oyun çizimleri (~900 satır)
│   │   └── menu_system.py       Ana menü + ayarlar
│   ├── audio/music_manager.py   Müzik (pygame mixer)
│   └── config/config_manager.py Ayarlar (JSON) + API key (.env)
├── assets/
│   ├── models/hand_landmarker.task
│   └── music/*.mp3
├── docs/                    Rehber belgeler (yukarıdaki tablo)
├── tools/test_dual_hands.py Manuel çift el testi
├── tests/                   242 test (8 dosya + conftest)
├── game_config.json         (gitignore'da — key İÇERMEZ artık)
├── .env                     (gitignore'da — API_KEY burada)
└── venv/                    Sanal ortam (.venv eski/bayat — kullanma)
```

**Import biçimi:** `from game.core.game_state import GameState` — tam yol,
relative import kullanılmaz. `python main.py` kökten çalışır.

---

## 4. TAMAMLANAN AŞAMALAR

| Aşama | Açıklama | Durum |
|-------|----------|-------|
| 0-5 | Test altyapısı, küçük fix'ler, veri/prompt/savaş/envanter ayrıştırma, Enum | ✅ (detay: RESTRUCTURE_PLAN) |
| Hotfix | game_phase.py SyntaxError (oyun 3 hafta açılamamıştı!) + ölü kod | ✅ 2026-07-16 |
| 6.1 | API key → `.env` + python-dotenv + otomatik migration (S13) | ✅ 2026-07-16 |
| 6.2 | Clipboard → pyperclip (S15) | ✅ 2026-07-16 |
| 6.3 | Kamera paylaşımı: CameraManager, menü ↔ oyun tek kamera (S22) | ✅ 2026-07-16 |
| 6.4 | requirements.txt: dotenv + pyperclip (S18) | ✅ 2026-07-16 |
| 7 | Dosya ağacı `game/` paket yapısına geçirildi | ✅ 2026-07-16 |

## 5. SIRADAKI GÖREVLER (PRODUCT_VISION Bölüm 6)

1. **Dağıtım:** README (kurulum + oynanış), model dosyası otomatik indirme,
   mümkünse PyInstaller tek-exe (E05)
2. **V1 efekt katmanı:** parmak izini takip eden büyü efektleri, hasar
   flaşları (mevcut stack ile)
3. **60 saniyelik oynanış videosu** + 5 yabancıyla oyuncu testi
4. (Aday) AI eval altyapısı — prompt'ların güvenle değiştirilebilmesi için (G03)

---

## 6. KRİTİK KURALLAR (HER AJAN OKUMALI)

### 🔴 DOKUNMA LİSTESİ

1. **Türkçe prompt'lar** — Prompt metnini DEĞİŞTİRME (eval altyapısı yokken — G03).
2. **Hasar formülleri** — Sayısal değerler (30-50 arası, 1.5x çarpan) korunmalı.
3. **Challenge süreleri** — `DRAW_TIME`, `COUNTDOWN_TIME`, `ACTIVE_DURATION`.
4. **Doğruluk hesaplama** — `game/challenges/shape_challenge.py`'deki formül.
5. **El takip parametreleri** — Smoothing katsayıları, güven eşikleri.
6. **UI layout sabitleri** — `game/ui/ui_renderer.py`.

### 🟡 İŞ AKIŞI KURALLARI

1. **Önce araştır, sonra yap:** İlgili dosyaları oku, yan etkileri listele.
2. **Test + SMOKE IMPORT:** Her değişiklik sonrası İKİSİ DE zorunlu:
   ```
   python -m pytest tests/ -q
   python -c "import main"
   ```
   ⚠️ Ders: Aşama 5.3'te ajan dosyaya çöp bıraktı, 237 test yeşil kaldı ama
   oyun 3 hafta açılamadı. Testler saf mantığı korur, oyunun açıldığını
   KANITLAMAZ (PRODUCT_VISION E01).
3. **Dosya sonlarını kontrol et:** Yazdığın dosyanın son satırlarında araç
   çağrısı artığı/kapanmamış string olmadığından emin ol.
4. **CHANGELOG'a yaz:** `docs/CHANGELOG.md`'ye şablonla giriş ekle.
5. **PRODUCT_VISION kuralları:** G01 (oyuncu-görünür değer önceliği),
   G02 (render/mantık ayrımı), G04 (hata-affeden stilizasyon),
   G05 (kurulum yükü sorusu), G06 (vizyon basamağı atlanmaz).

### 🟢 TEST YAZMA KURALLARI

- Yeni modül → yeni test dosyası (`test_<modül>.py`)
- `conftest.py`'deki `game_state` fixture'ını kullan
- Deterministic testler için `random.seed(42)`
- UI/IO bağımlı kodu test ETME — sadece saf mantık
- Config testlerinde `isolated_config` fixture'ı kullan (gerçek `.env`'i korur)
- Detaylar: `tests/TESTS_GUIDE.md`

---

## 7. MİMARİ BİLGİ

### Delegasyon Deseni (G02 — V3 motor ayrışmasının sigortası)

main.py hiçbir zaman doğrudan hesaplama yapmaz; alt modüller saf hesaplama
yapıp sonuç döndürür. Side-effect'ler (state değişikliği, cv2.imshow) her
zaman main.py'de kalır.

```
main.py (wrapper)      → game/core/combat_manager.py (hesaplama)
main.py (wrapper)      → game/core/inventory_handler.py (karar)
game/core/game_state   → game/core/shop_system.py (dükkan)
game/core/game_state   → game/core/prompt_builder.py (prompt)
```

### API Key Akışı (S13 fix sonrası)

```
Okuma:  .env dosyası (API_KEY) > OS ortam değişkeni
Yazma:  menü → save_config() → key .env'e, kalanı game_config.json'a
Migration: eski JSON'da key varsa ilk load_config()'ta .env'e taşınır
```

### Kamera Akışı (S22 fix sonrası)

```
main() → CameraManager (TEK kamera) → MenuSystem + DnDGame/HandTracker
Aynı index = yeniden açılmaz (Kaspersky bildirimi tetiklenmez)
HandTracker.release() paylaşılan kamerayı KAPATMAZ (_owns_camera=False)
```

### HP Akışı (S02 fix sonrası)

```
AI yanıtı → update_from_ai_response()
  ├── hp_degisim JSON → modify_hp()     ← TEK HP KAYNAĞI
  └── [HP:-10] tag   → sadece temizlenir, uygulanmaz
```

### Dodge vs Savunma (S05 fix sonrası)

```
DEX yeterli → combat.dodged = True         → "DEX DODGE!"
Savunma başarılı → combat.defense_blocked  → "MUKEMMEL SAVUNMA!"
UI: is_blocked_visual = dodged OR defense_blocked
```

### Bilinen Yarım Özellikler (denetim bulgusu, 2026-07-16)

- `game_state.py`: `get_effective_max_hp` / `get_hp_bonus_from_equipment` /
  `get_stat_breakdown` hiçbir yerden çağrılmıyor → **zırh HP bonusu fiilen
  çalışmıyor**. Tamamla veya sil — dokunmadan önce kullanıcıya sor.
- `GameState._api_error` yazılıyor ama okunmuyor (UI hata gösterimi yarım).

---

## 8. SORUN KATALOĞU DURUMU

### Çözülenler ✅
S01, S02, S04, S05, S10, S11, S12, S14 (Aşama 1-5) + **S13, S15, S18, S22** (Aşama 6)

### Kısmen Çözülenler 🟡
| ID | Sorun | Durum |
|----|-------|-------|
| S07/S08 | God Object'ler | Büyük kısmı ayrıştırıldı; main.py ~950, game_state ~810 satır |
| S09 | State machine | Enum var; full State Pattern yapılmayacak (E02/G01 gereği gündemden kalktı) |
| S16 | Test eksikliği | 242 test var; kapsam sınırı için E01'e bak |

### Çözülmeyenler ⬜
| ID | Sorun | Not |
|----|-------|-----|
| S03, S06 | Prompt sorunları | AI eval altyapısı kurulana kadar bilinçli açık (G03) |
| S17 | CI/CD yok | Ertelendi |
| S19 | Model indirme talimatı | Sıradaki "dağıtım" işinin parçası (E05) |
| S20 | Windows bağımlılığı | pyperclip ile azaldı; kalan: kamera/pencere davranışı |
| S21 | Kamera zorunlu | Mouse fallback — PRODUCT_VISION'da ürün-kritik olarak işaretli |

---

## 9. KULLANICININ BEKLENTİLERİ

- Görevler **aşama aşama**; önce bağımlılık analizi, sonra iş, sonra belge güncelleme
- **Temkinli** çalışma — "sorunsuz iş istiyorum"
- Dil: her şey Türkçe (kod yorumları, commit, changelog). Prompt'lara dokunma.
- Kamera gerekli; pencere cv2.imshow ile açılır (prototip mimari — E03)
- Sanal ortam: `venv/` (`.venv/` bayat bir kopya, KULLANMA)
- API key `.env`'de; geçersiz olabilir (`INVALID_ARGUMENT`) — bizim sorunumuz değil

---

## 10. HIZLI KOMUTLAR

```bash
# Sanal ortamı aktive et
.\venv\Scripts\activate

# Testler + smoke import (her değişiklik sonrası İKİSİ DE)
python -m pytest tests/ -q
python -c "import main"

# Oyunu başlat (kamera gerekli)
python main.py

# Manuel çift el testi
python tools/test_dual_hands.py
```

---

> **Son not:** Bu dosya her büyük değişiklikten sonra güncellenmelidir.
> Yeni ajan: önce bu dosya → sonra docs/PRODUCT_VISION.md →
> sonra kullanıcıya sıradaki görevi sor.
