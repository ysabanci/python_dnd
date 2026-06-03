# 🔧 Yeniden Mimari Tasarım Rehberi
# python_dnd Projesi — Yapısal Düzeltme Planı

> **Amaç:** Projeden hiçbir fonksiyon, özellik veya oynanış mekanigi çıkarmadan,
> kod tabanını düzgün, sürdürülebilir ve anlaşılır bir hale getirmek.
>
> **Kural:** Bu belgedeki hiçbir adım oyunun davranışını değiştirmez.
> Her şey "aynı şeyi yapan ama daha iyi organize edilmiş kod" üretmelidir.
>
> **Uyarı:** Bu belge hem insan hem de AI (dil modeli) tarafından
> okunmak üzere yazılmıştır. Her sorun ID ile etiketlenmiştir,
> cross-reference kolaylığı için bu ID'leri kullanın.

---

## İÇİNDEKİLER

1. [Mevcut Proje Haritası](#1-mevcut-proje-haritasi)
2. [Sorun Kataloğu](#2-sorun-katalogu)
   - [S01–S06: Sessiz Buglar](#sessiz-buglar-kodda-gizli-hatalar)
   - [S07–S12: Mimari Sorunlar](#mimari-sorunlar-surdurulebilirlik)
   - [S13–S15: Güvenlik](#guvenlik)
   - [S16–S19: Eksik Altyapı](#eksik-altyapi)
   - [S20–S22: Platform/Ortam](#platformortam)
3. [Bağımlılık Haritası](#3-bagimlilik-haritasi)
4. [Yapısal Değişiklik Planı](#4-yapisal-degisiklik-plani)
5. [Uygulama Sırası](#5-uygulama-sirasi)
6. [Her Adım İçin Doğrulama Yöntemi](#6-her-adim-icin-dogrulama-yontemi)

---

## 1. MEVCUT PROJE HARİTASI

### Dosya Büyüklükleri (Sorun Göstergesi)

| Dosya | Satır | Sorumluluk Sayısı | Durum |
|-------|------:|:-:|:-:|
| `main.py` | 1304 | ~12 farklı iş | 🔴 God Object |
| `game_state.py` | 1020 | ~10 farklı iş | 🔴 God Object |
| `ui_renderer.py` | 897 | 3-4 iş | 🟡 Büyük ama tolere edilebilir |
| `menu_system.py` | 549 | 2-3 iş | 🟡 Kabul edilebilir |
| `vision_engine.py` | 444 | 1 iş | 🟢 İyi |
| `shape_challenge.py` | 373 | 1 iş | 🟢 İyi |
| `fist_challenge.py` | 280 | 1 iş | 🟢 İyi |
| `dice_challenge.py` | 254 | 1 iş | 🟢 İyi |
| `music_manager.py` | 186 | 1 iş | 🟢 İyi |
| `config_manager.py` | 77 | 1 iş | 🟢 İyi |

### Mevcut Modüller Arası Bağımlılık Akışı

```
main.py ──────> vision_engine.py (el takibi)
   │──────────> game_state.py (oyun durumu - DEV)
   │──────────> ai_manager.py (AI istekleri)
   │──────────> ui_renderer.py (arayüz çizimi)
   │──────────> shape_challenge.py
   │──────────> fist_challenge.py
   │──────────> dice_challenge.py
   │──────────> music_manager.py
   │──────────> config_manager.py
   │
   └──> menu_system.py ──> config_manager.py
```

**Sorun:** `main.py` HER ŞEYİ biliyor ve HER ŞEYİ yapıyor.
`game_state.py` ise hem veri tutuyor, hem iş kuralı uyguluyor,
hem AI prompt'u üretiyor, hem shop yönetiyor.

---

## 2. SORUN KATALOĞU

Her sorun şu formatta belgelenmiştir:

- **ID:** Referans kodu (S01, S02...)
- **Durum:** `[ ]` = Açık, `[x]` = Çözüldü, `[/]` = Üzerinde çalışılıyor
- **Başlık:** Kısa açıklama
- **Konum:** Dosya ve satır numaraları
- **Şu An Ne Oluyor:** Mevcut hatalı davranış
- **Olması Gereken:** Doğru davranış
- **Düzeltirken Risk:** Bu sorunu çözerken nelere dikkat edilmeli
- **Bağımlılıklar:** Hangi diğer sorunlarla birlikte ele alınmalı

---

### SESSIZ BUGLAR (Kodda Gizli Hatalar)

#### - [ ] S01: `draw_buttons`'a Yanlış Parametre Tipi Gönderiliyor

- **Konum:** `main.py` satır 920-922
- **Şu An Ne Oluyor:** Silah seçim fazında `draw_buttons` çağrılırken
  5. parametre olarak `self.state.active_option_count` (bir `int`)
  gönderiliyor. Ama fonksiyonun 5. parametresi `mode: str = "kesif"`.
  ```python
  # main.py:920-922 (Hatalı)
  frame = self.ui.draw_buttons(frame, self.state.current_options,
                                hover_quadrant, progress,
                                self.state.active_option_count)  # int!
  ```
  ```python
  # ui_renderer.py:198-203 (Beklenen)
  def draw_buttons(self, frame, options, hover_quadrant=None,
                   progress=0.0, mode="kesif", ...):
  ```
  Python hata vermez çünkü `mode` parametresi string karşılaştırmasına
  girer (`mode == "savas"`) ve `int` ile string karşılaştırması `False` döner.
  **Sonuç:** Silah seçim ekranında savaş renkleri hiç uygulanmaz.
- **Olması Gereken:** `mode=self.state.current_mode` gönderilmeli.
- **Düzeltirken Risk:** ÇOK DÜŞÜK. Tek satır değişikliği. Ancak
  `draw_buttons`'ın tüm çağrı noktalarını kontrol etmek lazım (3 yer var).
  Diğer 2 çağrı doğru parametre gönderiyor mu?
- **Bağımlılıklar:** Yok. Bağımsız düzeltilebilir.

---

#### - [ ] S02: HP Çift Uygulanma Riski

- **Konum:** `game_state.py` satır 312-326 (`hp_degisim` işleme)
  ve satır 971-1007 (`_parse_hp_changes` metodu)
- **Şu An Ne Oluyor:** `update_from_ai_response()` metodu iki
  farklı yoldan HP değişikliği uygulayabiliyor:
  1. `hp_degisim` JSON alanı → `modify_hp(int(hp_change))`
  2. Hikaye metnindeki `[HP:-10]` tag'leri → `_parse_hp_changes()` → `modify_hp()`

  Eğer AI hem `"hp_degisim": -10` hem de hikaye metninde `[HP:-10]`
  yazarsa, hasar İKİ KEZ uygulanır.
- **Olması Gereken:** Sadece biri geçerli olmalı. `hp_degisim` alanı
  varsa `_parse_hp_changes` HP işlemini atlayabilir; veya
  `_parse_hp_changes` tamamen kaldırılıp sadece JSON alanına güvenilir.
- **Düzeltirken Risk:** ORTA.
  - `_parse_hp_changes` sadece fallback olarak mı tasarlanmış,
    yoksa ek bir kanal mı? Bu netleştirilmeli.
  - `_parse_hp_changes` aynı zamanda `[ESYA:...]` ve `[ALTIN:...]`
    tag'lerini de parse ediyor. HP kısmını kaldırırken eşya ve
    altın kısmını bozmamak lazım.
  - Savaş modunda `hp_degisim` zaten 0'a zorlanıyor (satır 321-322).
    Ama `_parse_hp_changes` bu guard'dan SONRA çalışıyor, yani
    savaş modunda bile hikaye tag'leri ile HP düşebilir!
- **Bağımlılıklar:** S03 ile ilişkili (AI savaş prompt'u çelişkisi).

---

#### - [ ] S03: Savaş Modunda AI Prompt Çelişkisi

- **Konum:** `game_state.py` satır 871-877 (sistem prompt'u)
  ve satır 320-322 (guard)
- **Şu An Ne Oluyor:** Sistem prompt'u AI'a diyor ki:
  *"Savas modunda hp_degisim NEGATIF olmali (-5 ile -25 arasi)"*.
  Ama `update_from_ai_response`'da savaş modunda `hp_degisim` SIFIRA
  zorlanıyor çünkü hasar challenge sistemi tarafından yönetiliyor.
  AI, talimat verildiği halde etkisiz HP değerleri üretiyor → token israfı.
- **Olması Gereken:** Sistem prompt'undaki savaş kuralları,
  gerçek oyun mantığıyla tutarlı olmalı. AI'a "savaş modunda
  hp_degisim=0 yap, hasar oyun tarafından yönetiliyor" denilmeli.
- **Düzeltirken Risk:** DÜŞÜK ama DİKKATLİ OLUNMALI.
  Bu bir prompt değişikliği. Kullanıcı prompt'a dokunmak istemiyor
  çünkü küçük bir değişiklik büyük bir mekaniği bozabilir.
  **ÖNERİ:** Bu sorun şimdilik belgelenir, ileride Katman 2'de
  prompt optimizasyonu yapılırken düzeltilir. Fonksiyonel bir hasar
  vermez, sadece gereksiz token harcar.
- **Bağımlılıklar:** S02 ile ilişkili.

---

#### - [ ] S04: `_extra_turn_active` Bayrağı Sıfırlanmıyor

- **Konum:** `main.py` satır 110 (tanım), satır 530 (True yapılıyor),
  satır 1260 (sadece `_restart`'ta sıfırlanıyor)
- **Şu An Ne Oluyor:** Ekstra tur kazanıldığında `_extra_turn_active = True`
  yapılıyor. Ama savaş bittiğinde (düşman yenildiğinde veya kaçıldığında)
  bu bayrak sıfırlanmıyor. Sadece oyun tamamen yeniden başlatıldığında
  (`_restart`) sıfırlanıyor.
- **Gerçek Etki:** Şu anki kodda `_extra_turn_active` bayrağı
  set edildikten sonra sadece `current_phase = PHASE_NORMAL` ve
  `_restore_combat_options()` çağrılıyor. Bayrak tekrar okunmuyor —
  yani şu an için **pratik bir bug yok**. Ama bu bir **saatli bomba**:
  ileride bu bayrağı kullanan yeni bir özellik eklenirse beklenmedik
  davranış ortaya çıkar.
- **Olması Gereken:** Savaş bitişinde (`_send_combat_result` veya
  mod değiştiğinde) sıfırlanmalı.
- **Düzeltirken Risk:** ÇOK DÜŞÜK. Tek satır ekleme.
  `_send_combat_result` metoduna `self._extra_turn_active = False` eklemek yeterli.
- **Bağımlılıklar:** Yok. Bağımsız düzeltilebilir.

---

#### - [ ] S05: `_defense_blocked` Dodge ile Savunma Karışıklığı

- **Konum:** `main.py` satır 674 (dodge'da True), satır 629 (savunmada True)
- **Şu An Ne Oluyor:** DEX dodge mekanizması ve savunma challenge'ı
  aynı `_defense_blocked` bayrağını kullanıyor. Dodge olduğunda
  düşman saldırı animasyonunda "MÜKEMMEL SAVUNMA!" yazısı gösteriliyor —
  oyuncu savunma yapmamış bile olsa.
- **Olması Gereken:** Dodge ve savunma farklı bayraklarla yönetilmeli;
  veya animasyon ekranında "DODGE!" / "SAVUNMA!" ayrımı yapılmalı.
- **Düzeltirken Risk:** ORTA.
  - `_defense_blocked` ve `_defense_partial` bayrakları
    `_handle_enemy_attack` (satır 704), `_process_player_combat_result`
    (satır 458) ve `_start_enemy_attack` (satır 666) tarafından
    okunuyor/yazılıyor. Yeni bir bayrak eklerken TÜM bu noktaları
    güncellemek lazım.
  - `draw_enemy_attack` fonksiyonuna yeni bir parametre
    (ör. `is_dodge=True`) eklemek gerekebilir → UI değişikliği.
- **Bağımlılıklar:** Yok. Bağımsız düzeltilebilir ama birden fazla
  dosyada değişiklik gerektirir (`main.py` + `ui_renderer.py`).

---

#### - [ ] S06: Ganimet Anahtar Kelime Çakışması

- **Konum:** `main.py` satır 356-378
- **Şu An Ne Oluyor:** Ganimet alma/reddetme kararı, seçenek metnindeki
  anahtar kelime aramasıyla yapılıyor:
  ```python
  loot_keywords = ("ganimet", "al", "topla", ...)
  reject_keywords = ("birak", "reddet", "hayir", ...)
  ```
  "Silahı al ve devam et" → hem `"al"` (kabul) hem `"devam"` (nötr) içerir.
  "Ganimeti bırak" → hem `"ganimet"` (kabul) hem `"bırak"` (ret) içerir.
  Reject öncelikli kontrol edilse de, karmaşık cümlelerde sonuç
  tahmin edilemez.
- **Olması Gereken:** Keyword matching yerine, seçenek key'ine
  (sol_ust, sag_ust...) dayalı bir sistem kullanılmalı. AI'dan
  gelen ganimet seçeneklerinde hangi key'in "al", hangisinin "reddet"
  olduğu belirlenebilir.
- **Düzeltirken Risk:** ORTA-YÜKSEK.
  - Bu değişiklik AI prompt'unu da etkiler (AI'a "ganimet seçeneklerinde
    sol_ust=al, sag_ust=reddet yap" demek gerekir).
  - Prompt değişikliği istenmiyor → **şimdilik sadece belgelenir**.
  - Alternatif: `pending_loot` varken seçeneklere özel bir işaretleme
    eklenebilir ama bu da `game_state.py`'de değişiklik gerektirir.
- **Bağımlılıklar:** AI prompt sistemiyle bağlantılı. Şimdilik
  ERTELENEBİLİR.

---

### MİMARİ SORUNLAR (Sürdürülebilirlik)

#### - [ ] S07: `main.py` God Object — 1304 Satır, 12+ Sorumluluk

- **Konum:** `main.py` tamamı
- **Şu An Ne Oluyor:** `DnDGame` sınıfı şu sorumlulukları taşıyor:
  1. Ana oyun döngüsü (`run`)
  2. Karakter oluşturma akışı (`_init_startup`, `_handle_startup_choice`)
  3. Normal seçim işleme (`_handle_normal_choice`)
  4. Savaş challenge başlatma (`_start_combat_challenge`, `_start_actual_challenge`)
  5. Saldırı/savunma/kaçış sonuç işleme (`_process_player_combat_result`,
     `_process_attack`, `_process_defense`, `_process_flee`)
  6. Düşman saldırı fazı (`_start_enemy_attack`, `_handle_enemy_attack`)
  7. Şekil challenge yönetimi (`_handle_shape_challenge`)
  8. Yumruk challenge yönetimi (`_handle_fist_challenge`)
  9. Silah seçim fazı (`_handle_weapon_select`)
  10. Zar atma fazı (`_handle_dice_roll`)
  11. Envanter yönetimi (`_handle_inventory`)
  12. AI yanıt kontrolü (`_check_ai_response`)
  13. Müzik geçişleri (check_ai_response içinde)
  14. Combat preview metni (`_get_combat_preview`)

- **Olması Gereken:** Her sorumluluk kendi modülüne çıkarılmalı.
  Aşağıda "Yapısal Değişiklik Planı" bölümünde detaylandırılmıştır.

- **Düzeltirken Risk:** YÜKSEK — Bu en riskli değişiklik.
  - Tüm metodlar birbirine `self.` ile bağlı. Bir metodu başka
    bir sınıfa taşırken `self.state`, `self.tracker`, `self.ui`,
    `self.shape_challenge` gibi referansları doğru aktarmak gerekir.
  - Faz geçişleri (`self.current_phase = ...`) birden fazla
    metotta değiştiriliyor. Geçişlerin tutarlılığı korunmalı.
  - `_defense_blocked`, `_extra_turn_active` gibi bayraklar
    birden fazla metot arasında paylaşılıyor.

  **RİSK AZALTMA:** Bu değişiklik ASLA tek seferde yapılmamalı.
  Her sorumluluk ayrı bir commit'te çıkarılmalı ve arada
  oyun test edilmelidir.

- **Bağımlılıklar:** S08, S09, S11 ile doğrudan bağlantılı.

---

#### - [ ] S08: `game_state.py` God Object — 1020 Satır, 10+ Sorumluluk

- **Konum:** `game_state.py` tamamı
- **Şu An Ne Oluyor:** `GameState` sınıfı şu sorumlulukları taşıyor:
  1. Karakter verileri (HP, gold, inventory)
  2. Statik oyun verileri (CLASS_DATA, WEAPON_DATA, WEAPON_STATS,
     THEME_LORE, CLASS_BONUS — toplam ~160 satır sözlük!)
  3. Oyun durumu bayrakları (is_game_over, is_startup, current_mode...)
  4. AI prompt üretimi (_init_system_prompt, get_dynamic_prompt,
     get_character_summary, _get_world_context)
  5. AI yanıt işleme (update_from_ai_response, _parse_hp_changes)
  6. Savaş durumu (enemy_hp, pending_combat_result)
  7. Dünya takibi (visited_locations, npc_met, interactions)
  8. Shop sistemi (init_shop, shop_buy, shop_roll, _generate_shop_items)
  9. Silah/envanter yönetimi (get_combat_weapons, toggle_equipped,
     get_weapon_stats)
  10. İstatistik sistemi (get_total_stats, get_stat_effect_on_combat,
      apply_event_stat)
  11. Mesaj geçmişi yönetimi (_message_history, _optimize_memory)
  12. Rastgele savaş zamanlayıcı (_next_combat_turn mantığı)

- **Olması Gereken:** Statik veriler ayrı bir dosyaya, prompt
  üretimi ayrı bir dosyaya, shop ayrı bir dosyaya çıkarılmalı.

- **Düzeltirken Risk:** YÜKSEK.
  - `update_from_ai_response` metodu (satır 232-412) 180 satır
    ve neredeyse TÜM state alanlarını değiştiriyor. Bu metodu
    parçalamak çok dikkat gerektirir.
  - `get_dynamic_prompt` (satır 424-495) hem savaş hem keşif
    hem ganimet mantığı içeriyor. Parçalarken prompt'un bütünlüğü
    korunmalı.
  - Birçok metot `self.character.xxx` ile doğrudan Character'a
    erişiyor. Character ayrılırsa bu referanslar kırılır.

- **Bağımlılıklar:** S07 ile birlikte ele alınmalı.

---

#### - [ ] S09: State Machine Yok — Spaghetti Faz Yönetimi

- **Konum:** `main.py` satır 130-207 (ana döngü) ve tüm
  `current_phase` atamaları
- **Şu An Ne Oluyor:** Faz geçişleri string sabitleriyle
  (`PHASE_NORMAL`, `PHASE_SHAPE_CHALLENGE`, vs.) yönetiliyor.
  Ana döngüde art arda `if/elif/continue` blokları var.
  Geçerli faz geçişleri tanımlanmamış — herhangi bir fazdan
  herhangi bir faza geçiş mümkün (guard yok).
- **Olması Gereken:** Geçerli faz geçişlerini tanımlayan bir
  state machine (en azından bir geçiş tablosu) olmalı.
- **Düzeltirken Risk:** ORTA.
  - Mevcut faz isimleri string (`"normal"`, `"shape_challenge"`...).
    Enum'a çevirmek güvenli ama tüm karşılaştırmaları güncellemek lazım.
  - Geçiş tablosu eklemek, mevcut geçişlerin hepsini haritalamayı
    gerektirir. Bir tane atlarsak oyun kilitlenir.
  - **ADIM 1 (şimdi):** String → Enum dönüşümü yapılır.
  - **ADIM 2 (ileride):** Full State Pattern uygulanır — her faz
    (`ExplorationState`, `CombatState`, `InventoryState`...) kendi
    `enter()`, `update(frame)`, `exit()` metodlarına sahip ayrı
    birer sınıf olur. Bu, faz geçiş guard'larını da içerir.
    Ancak bu adım BÜYÜK bir yeniden yazım gerektirir ve
    **Aşama 4-5 tamamlandıktan sonra** değerlendirilmelidir.
- **Bağımlılıklar:** S07 ile birlikte yapılabilir.

---

#### - [ ] S10: Hardcoded String Tekrarları

- **Konum:** `main.py` satır 394, 479, 480, 481, 560, 561, 846-848
- **Şu An Ne Oluyor:** Savaş aksiyonları (`"saldir"`, `"savun"`,
  `"kac"`, `"buyu"`) en az 6 farklı yerde tekrar ediyor.
  Biri değiştirilip diğeri unutulursa sessiz bug oluşur.
- **Olması Gereken:** Tek bir yerde tanımlanmış sabitler:
  ```python
  ATTACK_ACTIONS = ("saldir", "saldiri", "buyu")
  DEFENSE_ACTIONS = ("savun", "savunma")
  FLEE_ACTIONS = ("kac", "kacis")
  ```
- **Düzeltirken Risk:** ÇOK DÜŞÜK. Sabitler tanımlanıp yerine konur.
  Ama TÜM kullanım noktaları bulunmalı (grep ile).
- **Bağımlılıklar:** S07 ile birlikte yapılabilir ama bağımsız da yapılabilir.

---

#### - [ ] S11: Envanter Yönetiminde `getattr` Hack'i

- **Konum:** `main.py` satır 1025-1028
- **Şu An Ne Oluyor:**
  ```python
  hovered_shop=getattr(self, '_inv_hovered_shop', -1),
  hovered_roll=getattr(self, '_inv_hovered_roll', False),
  ```
  Bu `getattr` kullanımları, bu attribute'ların `__init__`'te
  tanımlanmadığını gösteriyor. İlk envanter açılışında yoksa
  varsayılan değer kullanılıyor — lazy initialization anti-pattern.
- **Olması Gereken:** Bu attribute'lar `__init__`'te tanımlanmalı.
- **Düzeltirken Risk:** ÇOK DÜŞÜK.
  `__init__` içinde `self._inv_hovered_shop = -1` vb. eklemek yeterli.
- **Bağımlılıklar:** Yok. Bağımsız düzeltilebilir.

---

#### - [ ] S12: `reset()` Metodu `__init__` Çağırıyor

- **Konum:** `game_state.py` satır 834
- **Şu An Ne Oluyor:** `self.__init__(Character())` — Python'da
  `__init__`'i doğrudan çağırmak anti-pattern. İleride `__init__`'e
  yeni parametreler eklenirse `reset()` sessizce kırılır.
- **Olması Gereken:** Ya `reset()` içinde tüm alanlar elle sıfırlanır,
  ya da bir `_reset_to_defaults()` yardımcı metod kullanılır.
- **Düzeltirken Risk:** ORTA.
  `GameState.__init__`'te 50+ attribute tanımlanıyor. `reset()` bunların
  hepsini kapsamalı. Bir tanesi atlanırsa önceki oyundan state leak olur.
  **ÖNERİ:** `reset()` düzeltilirken, `__init__` ile aynı attribute
  listesini kullandığından emin olmak için bir test yazılmalı.
- **Bağımlılıklar:** S08 ile birlikte ele alınabilir.

---

### GÜVENLİK

#### - [ ] S13: API Key Düz Metin Olarak Diskte

- **Konum:** `config_manager.py` satır 62-69, `game_config.json`
- **Şu An Ne Oluyor:** API anahtarı şifrelenmemiş JSON dosyasında tutuluyor.
  `.gitignore`'da olmasına rağmen kazara commit riski var.
- **Olması Gereken:** `.env` dosyası + `python-dotenv` kullanılmalı.
  **Neden `python-dotenv`?** Cross-platform çalışır, Linux/Docker
  ortamlarıyla uyumludur. Windows Credential Manager gibi platforma
  kilitli çözümlerden kaçınılmalı.
  ```
  # .env dosyası
  API_KEY=sk-xxxxxxxxxxxx
  ```
  ```python
  # config_manager.py
  from dotenv import load_dotenv
  load_dotenv()
  api_key = os.environ.get("API_KEY", "")
  ```
- **Düzeltirken Risk:** ORTA.
  - Tüm config okuma/yazma akışı değişir.
  - `menu_system.py`'deki API key girişi de güncellenmeli —
    kullanıcı menüden key girdiğinde `.env` dosyasına yazılmalı.
  - Mevcut `game_config.json` kullanan kullanıcıların geçişi
    (migration) düşünülmeli: ilk çalıştırmada eski JSON'daki
    key okunup `.env`'e taşınabilir.
  - `ai_manager.py`'deki `_set_api_key_env` metodu env var
    isimleriyle çakışabilir.
  - `python-dotenv` yeni bir bağımlılık → `requirements.txt`'e eklenmeli.
- **Bağımlılıklar:** Bağımsız yapılabilir ama S14 ile birlikte
  ele alınması daha temiz olur.

---

#### - [ ] S14: `ast.literal_eval` ile Dış Veri Parse'ı

- **Konum:** `ai_manager.py` satır 218, 226
- **Şu An Ne Oluyor:** AI yanıtı `json.loads` ile parse edilemezse
  `ast.literal_eval` kullanılıyor. Bu, Python literal'lerini
  (tuple, set, complex number) kabul eder.
- **Olması Gereken:** `json.loads` başarısız olursa, regex ile
  JSON bloğu çıkarılıp tekrar denenmeli. `ast.literal_eval`
  tamamen kaldırılmalı.
- **Düzeltirken Risk:** DÜŞÜK.
  - `ast.literal_eval` sadece fallback. Kaldırıldığında, daha
    önce parse edilebilen bazı yanıtlar artık parse edilemeyebilir
    → fallback JSON döner. Bu kabul edilebilir.
  - `import ast` kaldırılabilir.
- **Bağımlılıklar:** Yok. Bağımsız düzeltilebilir.

---

#### - [ ] S15: Clipboard Erişimi Platform-Bağımlı ve Şüpheli

- **Konum:** `menu_system.py` satır 26-40
- **Şu An Ne Oluyor:** PowerShell subprocess ile clipboard okunuyor.
  Kaspersky gibi güvenlik yazılımları bunu şüpheli olarak algılıyor
  (kullanıcının `not.txt` notunda da bahsettiği sorun).
- **Olması Gereken:** `pyperclip` kütüphanesi kullanılmalı.
  **Neden `pyperclip`?** Çapraz platform (Windows/macOS/Linux),
  güvenlik yazılımlarını tetiklemeyen, güvenilir ve bakımlı bir
  kütüphanedir. `tkinter` alternatifi **uygun değildir** çünkü
  OpenCV event loop'u ile çakışma riski yüksektir.
  ```python
  # menu_system.py
  import pyperclip
  clipboard = pyperclip.paste()
  ```
- **Düzeltirken Risk:** DÜŞÜK.
  - `pyperclip` yeni bir bağımlılık → `requirements.txt`'e eklenmeli.
  - `get_clipboard()` fonksiyonu tek bir yerde tanımlı, değiştirmek kolay.
  - **Test:** Değişiklik sonrası menüde Ctrl+V'nin çalışıp
    çalışmadığı kontrol edilmeli.
- **Bağımlılıklar:** S20 (platform bağımlılığı) ile ilişkili.

---

### EKSİK ALTYAPI

#### - [ ] S16: Sıfır Unit Test

- **Konum:** Proje geneli (sadece `test_dual_hands.py` var, o da
  manuel çift el testi)
- **Şu An Ne Oluyor:** Hiçbir fonksiyonun otomatik testi yok.
  Herhangi bir değişikliğin neyi kırdığını bilmenin yolu yok.
- **Olması Gereken:** İKİ KATMANLI test stratejisi:

  **Katman A — Saf Fonksiyon Unit Testleri (Mock gerektirmez):**
  Bu fonksiyonlar UI/kamera/AI'dan bağımsızdır, doğrudan test edilir:
  - `game_state.py`: `get_stat_effect_on_combat`, `get_weapon_stats`,
    `toggle_equipped`, `shop_buy`, `shop_roll`, `modify_hp`,
    `modify_gold`, `apply_class_choice`, `get_combat_weapons`
  - `ai_manager.py`: `_parse_response`, `_normalize_model`
  - `config_manager.py`: `load_config`, `save_config`, `mask_api_key`
  - `ui_renderer.py`: `sanitize_text`, `_wrap_text`

  **Katman B — Characterization (Snapshot) Testleri:**
  God Object'lerdeki karmaşık metodlar (ör. `update_from_ai_response`,
  `_process_player_combat_result`) doğrudan test etmek zordur çünkü
  UI, kamera ve global state ile sıkı bağlıdır. Bunlar için:
  1. `GameState`'i bilinen bir duruma getir (sabit karakter, sabit HP/gold)
  2. Sahte bir AI yanıtı ver (`update_from_ai_response` çağır)
  3. Sonuçtaki state'i JSON olarak kaydet (snapshot)
  4. Refactoring adımlarında aynı girdiyle aynı snapshot çıkmalı
  Bu testler "şu an ne yapıyor?" sorusunun cevabını dondurur.
  Refactoring sırasında davranış değişirse snapshot farklılık gösterir.

  **Neden iki katman?** Saf fonksiyon testleri hızlı ve kesindir —
  `modify_hp(-10)` çağrısının HP'yi tam 10 düşürdüğünü garanti eder.
  Snapshot testleri ise "büyük resmi" korur — karmaşık etkileşimlerin
  refactoring sonrasında aynı kalıp kalmadığını kontrol eder.

- **Düzeltirken Risk:** SIFIR. Test eklemek mevcut kodu değiştirmez.
- **Bağımlılıklar:** S07 ve S08'den ÖNCE yapılmalı. Testler güvenlik
  ağı oluşturacak.

---

#### - [ ] S17: CI/CD Pipeline Yok

- **Konum:** Proje geneli
- **Şu An Ne Oluyor:** Testler elle çalıştırılıyor (zaten test yok).
  Lint kontrolü yok. Formatör yok.
- **Olması Gereken:** En azından:
  - `pytest` ile test çalıştırma
  - Basit bir Makefile veya script (`run_tests.py`)
  - İleride: GitHub Actions veya benzeri
- **Düzeltirken Risk:** SIFIR. Altyapı eklemek mevcut kodu değiştirmez.
- **Bağımlılıklar:** S16 ile birlikte yapılmalı.

---

#### - [ ] S18: `requirements.txt` Üst Sınır Yok

- **Konum:** `requirements.txt`
- **Şu An Ne Oluyor:** `opencv-python>=4.8.0` gibi açık uçlu sürümler.
  Gelecekte major breaking change gelirse oyun çalışmaz.
- **Olması Gereken:** Exact pinning (`opencv-python==4.10.0.84`) veya
  en azından üst sınır (`opencv-python>=4.8.0,<5.0`).
- **Düzeltirken Risk:** ÇOK DÜŞÜK.
  `pip freeze` ile mevcut çalışan sürümler kaydedilir.
- **Bağımlılıklar:** Yok.

---

#### - [ ] S19: `hand_landmarker.task` İndirme Talimatı Yok

- **Konum:** `vision_engine.py` satır 112-119, `.gitignore`
- **Şu An Ne Oluyor:** 7.8MB model dosyası `.gitignore`'dan
  çıkarılmış (son değişiklikle). Ama dosya yoksa uygulama crash
  ediyor ve kullanıcıya sadece hata mesajı gösteriyor.
- **Güncelleme:** Kullanıcı `.gitignore`'dan `hand_landmarker.task`
  satırını sildi, yani dosya artık repo'ya dahil olacak. Bu 7.8MB'lik
  binary dosyanın Git'te tutulması sorun olabilir (repo şişmesi).
  Ancak fonksiyonellik açısından sorun çözülmüş oluyor.
- **Olması Gereken:** Ya Git LFS kullanılır, ya da README'ye
  indirme talimatı eklenir ve `.gitignore`'a geri konur.
- **Düzeltirken Risk:** DÜŞÜK. Sadece karar verilmesi gereken bir konu.
- **Bağımlılıklar:** Yok.

---

### PLATFORM/ORTAM

#### - [ ] S20: Windows'a Sıkı Bağımlılık

- **Konum:** `menu_system.py` satır 30-34 (PowerShell clipboard),
  satır 34 (`creationflags=0x08000000`)
- **Şu An Ne Oluyor:** Clipboard okuma PowerShell ile yapılıyor,
  `CREATE_NO_WINDOW` flag'i Windows-specific.
- **Olması Gereken:** Platform kontrolü eklenmeli:
  ```python
  import platform
  if platform.system() == "Windows": ...
  elif platform.system() == "Darwin": ...  # macOS
  else: ...  # Linux
  ```
- **Düzeltirken Risk:** DÜŞÜK ama TEST GEREKTİRİR.
  Windows'ta çalıştığı biliniyor, diğer platformlarda test lazım.
- **Bağımlılıklar:** S15 ile birlikte ele alınabilir.

---

#### - [ ] S21: Kamera Olmadan Oynanamaz

- **Konum:** `main.py` satır 64-68
- **Şu An Ne Oluyor:** Kamera açılamazsa `RuntimeError` fırlatılıyor.
  Masaüstü bilgisayarlarda harici kamera yoksa oyun HİÇ çalışmaz.
- **Olması Gereken:** Kamera yoksa mouse/klavye fallback modu.
- **Düzeltirken Risk:** YÜKSEK.
  - Tüm giriş sistemi (dwell selection) kamera+el takibine bağlı.
  - Mouse fallback eklemek `tracker.detect_finger` çağrılarını
    saran bir soyutlama katmanı gerektirir.
  - Bu büyük bir refactoring — **şimdilik ERTELENMELİ**.
- **Bağımlılıklar:** S07 ile bağlantılı (giriş soyutlaması).

---

#### - [ ] S22: Kaspersky ve Benzeri Güvenlik Yazılımı Çakışması

- **Konum:** `menu_system.py` satır 94-108 (menü kamerası),
  `vision_engine.py` satır 87-109 (oyun kamerası)
- **Şu An Ne Oluyor:** Menü sistemi kendi kamerasını açıp kapatıyor,
  sonra oyun ayrı bir kamera açıyor. Kaspersky her `VideoCapture`
  çağrısında izin soruyor (kullanıcının `not.txt` notunda bahsettiği).
- **Olması Gereken:** Kamera tek bir yerde açılıp, menü ve oyun
  arasında paylaşılmalı (dependency injection).
- **Düzeltirken Risk:** ORTA.
  - `MenuSystem.__init__` kendi kamerasını açıyor (satır 94-108).
  - `DnDGame.__init__` ayrı bir kamera açıyor (satır 60-68).
  - Ortak bir kamera nesnesini her ikisine de geçirmek gerekir.
  - `MenuSystem.run()` sonunda kamerayı kapatıyor (satır 150-152)
    — bu durumda oyun kamerasız kalır. Kapatma mantığı değişmeli.
  - **ÖNERİ:** `main()` fonksiyonunda tek bir kamera açılır,
    hem `MenuSystem` hem `DnDGame`'e parametre olarak geçirilir.
- **Bağımlılıklar:** S07 ile birlikte yapılabilir.

---

## 3. BAĞIMLILIK HARİTASI

Hangi sorunlar birbiriyle ilişkili ve hangi sırada ele alınmalı:

```
BAĞIMSIZ (herhangi bir sırada yapılabilir):
  S01 (draw_buttons parametre)
  S04 (_extra_turn_active reset)
  S10 (string sabitleri)
  S11 (getattr hack)
  S14 (ast.literal_eval)
  S16 (unit testler)  ← AMA bu diğerlerinden ÖNCE yapılmalı!
  S17 (CI/CD)
  S18 (requirements pinning)
  S19 (hand_landmarker)

KÜÇÜK GRUP (birlikte ele alınabilir):
  S02 + S03 (HP çift uygulama + prompt çelişkisi)
  S13 + S15 + S20 (güvenlik + platform)
  S05 (dodge/savunma — küçük ama birden fazla dosya)

BÜYÜK GRUP (dikkatli planlama gerektirir):
  S07 + S08 + S09 + S12 (God Object'leri parçalama)
  └─ S16 bundan ÖNCE tamamlanmış olmalı!

ERTELENEN:
  S06 (ganimet keyword — prompt değişikliği gerektirir)
  S21 (kamera fallback — büyük refactoring)
  S22 (kamera paylaşımı — S07 ile birlikte)
```

---

## 4. YAPISAL DEĞİŞİKLİK PLANI

God Object'lerin parçalanması sonrasında hedeflenen yeni dosya yapısı.
**Önemli:** Hiçbir fonksiyon veya özellik kaybolmaz. Sadece yer değiştirir.

### 4.1. `game_state.py`'den Çıkarılacaklar

#### [YENİ] `game_data.py` — Statik Oyun Verileri

`game_state.py`'den şu sözlükler ve sabitler TAŞINIR:

| Mevcut Konum | Taşınacak İçerik |
|---|---|
| `game_state.py:67-78` | `THEME_LORE` sözlüğü |
| `game_state.py:80-85` | `CLASS_DATA` sözlüğü |
| `game_state.py:88-93` | `CLASS_BASE_STATS` sözlüğü |
| `game_state.py:95-128` | `WEAPON_DATA` ve `WEAPON_STATS` sözlükleri |
| `game_state.py:130-137` | `STAT_NAMES` sözlüğü |
| `game_state.py:139-145` | `CLASS_BONUS` sözlüğü |
| `game_state.py:147-153` | `CLASS_ADVANTAGE_KEY` sözlüğü |
| `game_state.py:155-159` | `POSSIBLE_LOCATIONS` listesi |
| `game_state.py:606-607` | `SHOP_BASE_COST`, `SHOP_ROLL_BASE_COST` |
| `game_state.py:738-740` | `NON_WEAPON_ITEMS` |

**Taşıma Sonrası:** `game_state.py`'de `from game_data import ...`
ile import edilir. Hiçbir davranış değişmez.

**Risk:** ÇOK DÜŞÜK. Saf veri taşıması.
**Dikkat:** `get_weapon_stats` metodu (satır 690-725) hash tabanlı
dinamik silah üretimi yapıyor. Bu metod `WEAPON_STATS` sözlüğüne
bağlı. Sözlük `game_data.py`'ye giderse, metod ya `game_data.py`'de
kalır ya da `game_state.py`'de import ile erişir.
**Öneri:** Metod `game_state.py`'de kalsın, `WEAPON_STATS`'ı import etsin.

---

#### [YENİ] `prompt_builder.py` — AI Prompt Üretimi

`game_state.py`'den şu metodlar TAŞINIR:

| Mevcut Konum | Taşınacak İçerik |
|---|---|
| `game_state.py:840-921` | `_init_system_prompt` metodu |
| `game_state.py:424-495` | `get_dynamic_prompt` metodu |
| `game_state.py:923-937` | `_get_world_context` metodu |
| `game_state.py:519-541` | `get_character_summary` metodu |

**Risk:** ORTA.
- Bu metodlar `self.` ile `GameState`'in birçok alanına erişiyor
  (`self.current_theme`, `self.pending_combat_result`,
  `self.turn_count`, `self.enemy_hp`, vs.).

- **Tasarım kararı: Parametre bazlı saf fonksiyonlar.**
  `PromptBuilder` sınıfı `GameState` nesnesinin TAMAMINI ALMAMALIDIR.
  Bunun yerine, her metod sadece ihtiyacı olan verileri parametre
  olarak almalıdır. Bu yaklaşım:
  - Circular import riskini tamamen ortadan kaldırır
  - `PromptBuilder`'ı bağımsız test edilebilir yapar
  - Tight coupling'i önler

  ```python
  # KÖTÜ — GameState referansı (tight coupling)
  class PromptBuilder:
      def __init__(self, state: "GameState"):
          self._state = state
      def build_dynamic_prompt(self):
          return f"Tema: {self._state.current_theme}"  # God Object referansı!

  # İYİ — Parametre bazlı (loose coupling)
  class PromptBuilder:
      @staticmethod
      def build_system_prompt(character_class: str, theme: str,
                              world_rules: dict) -> str:
          ...

      @staticmethod
      def build_dynamic_prompt(current_mode: str, turn_count: int,
                               enemy_hp: int, enemy_max_hp: int,
                               pending_combat_result: dict,
                               pending_loot: str,
                               world_context: str,
                               character_summary: str) -> str:
          ...

      @staticmethod
      def build_world_context(visited_locations: list,
                              npc_met: list,
                              interactions: list) -> str:
          ...

      @staticmethod
      def build_character_summary(character, total_stats: dict,
                                  equipped_items: list) -> str:
          ...
  ```

  **Çağrı tarafında (game_state.py veya main.py):**
  ```python
  prompt = PromptBuilder.build_dynamic_prompt(
      current_mode=self.current_mode,
      turn_count=self.turn_count,
      enemy_hp=self.enemy_hp,
      enemy_max_hp=self.enemy_max_hp,
      pending_combat_result=self.pending_combat_result,
      pending_loot=self.pending_loot,
      world_context=PromptBuilder.build_world_context(
          self.visited_locations, self.npc_met, self.interactions
      ),
      character_summary=PromptBuilder.build_character_summary(
          self.character, self.get_total_stats(), self.character.equipped_items
      ),
  )
  ```

  Bu yaklaşımda `prompt_builder.py` hiçbir şekilde `game_state`'i
  import etmez. Circular import riski SIFIR.
  Her metod saf fonksiyondur — aynı girdiye aynı çıktıyı verir.
  Unit test yazmak trivial hale gelir.

---

#### [YENİ] `shop_system.py` — Dükkan Sistemi

`game_state.py`'den şu metodlar TAŞINIR:

| Mevcut Konum | Taşınacak İçerik |
|---|---|
| `game_state.py:609-661` | `init_shop`, `_generate_shop_items`, `get_shop_items`, `get_shop_roll_cost`, `shop_buy`, `shop_roll` |

**Risk:** DÜŞÜK.
- Shop metodları `self.character.gold` ve `self.apply_event_stat`'a
  erişiyor. `ShopSystem` sınıfına `GameState` referansı geçirilir.
- `hasattr(self, '_shop_items')` kontrolü (satır 629) → `__init__`'te
  initialize edilerek kaldırılır (S11 ile birlikte çözülür).

---

### 4.2. `main.py`'den Çıkarılacaklar

#### [YENİ] `combat_manager.py` — Savaş Mantığı

`main.py`'den şu metodlar TAŞINIR:

| Mevcut Konum | Taşınacak İçerik |
|---|---|
| `main.py:388-440` | `_start_combat_challenge`, `_start_actual_challenge` |
| `main.py:442-452` | `_restore_combat_options` |
| `main.py:458-543` | `_process_player_combat_result` |
| `main.py:545-611` | `_process_attack` |
| `main.py:613-642` | `_process_defense` |
| `main.py:644-660` | `_process_flee` |
| `main.py:666-773` | `_start_enemy_attack`, `_handle_enemy_attack` |
| `main.py:843-871` | `_get_combat_preview` |
| `main.py:1181-1196` | `_send_combat_result` |

**Risk:** YÜKSEK. Bu en karmaşık taşıma.
- Bu metodlar şu `DnDGame` attribute'larına erişiyor:
  - `self.state` (GameState)
  - `self.tracker` (HandTracker) — sadece `_handle_enemy_attack`'ta
  - `self.ui` (GameUI) — `_handle_enemy_attack`'ta draw çağrısı
  - `self.shape_challenge`, `self.fist_challenge` — reset çağrıları
  - `self.current_phase` — faz geçişleri
  - `self._selected_weapon`, `self._defense_blocked`,
    `self._defense_partial`, `self._extra_turn_active`,
    `self._enemy_attack_*` — savaş bayrakları

- **Kritik tasarım kararı: CombatManager UI'a DOKUNMAMALI.**
  `CombatManager` içinde `frame` kelimesi bile geçmemelidir.
  Savaş mantığı sadece HESAPLAMA yapar ve STATE günceller.
  Çizim işlerinin tamamı `ui_renderer.py`'de kalır, ana döngü
  CombatManager'ın state'ini okuyarak UI'a ne çizeceğini söyler.

  ```python
  class CombatManager:
      def __init__(self, state):
          self.state = state
          # Savaş bayrakları
          self.selected_weapon = ""
          self.defense_blocked = False
          self.defense_partial = False
          self.extra_turn_active = False
          # Düşman saldırı durumu
          self.enemy_attack_start = 0.0
          self.enemy_attack_damage = 0
          self.enemy_attack_applied = False
          self.enemy_attack_blocked = False
          self.enemy_attack_name = ""
          # NOT: self.ui YOK! Frame/çizim referansı YOK!

      def process_attack(self, accuracy: float, weapon: str) -> dict:
          """Saldırı sonucunu hesaplar. UI bilgisi DÖNDÜRÜR, çizmez."""
          # Hasar hesapla...
          return {
              "damage": calculated_damage,
              "is_critical": is_critical,
              "enemy_killed": self.state.enemy_hp <= 0,
              "next_phase": "enemy_attack" or "normal",
              "feedback_text": "Kritik vurus! 45 hasar!"
          }

      def start_enemy_attack(self) -> dict:
          """Düşman saldırısını başlatır. Animasyon bilgisi DÖNDÜRÜR."""
          self.enemy_attack_start = time.time()
          self.enemy_attack_damage = random.randint(5, 25)
          return {
              "damage": self.enemy_attack_damage,
              "enemy_name": self.state.enemy_name,
              "blocked": self.defense_blocked,
              "duration": ENEMY_ATTACK_DURATION,
          }

      def update_enemy_attack(self) -> dict:
          """Her frame'de çağrılır. Animasyon ilerlemesini DÖNDÜRÜR."""
          progress = (time.time() - self.enemy_attack_start) / DURATION
          return {
              "progress": min(1.0, progress),
              "is_finished": progress >= 1.0,
              "damage_applied": self.enemy_attack_applied,
          }
  ```

  **Ana döngüde kullanım:**
  ```python
  # main.py ana döngü
  if phase == PHASE_ENEMY_ATTACK:
      attack_info = self.combat.update_enemy_attack()
      frame = self.ui.draw_enemy_attack(frame,
          progress=attack_info["progress"],
          damage=attack_info["damage"],
          enemy_name=attack_info["enemy_name"],
          blocked=attack_info["blocked"])
      if attack_info["is_finished"]:
          self.current_phase = PHASE_NORMAL
  ```

  Bu yaklaşımın faydaları:
  - `CombatManager` tamamen test edilebilir (frame/UI mock gerektirmez)
  - Çizim mantığı tek yerde kalır (`ui_renderer.py`)
  - Savaş mantığı ve görsel sunum tamamen ayrışır

- **Dikkat edilmesi gereken noktalar:**
  1. `_start_actual_challenge` `shape_challenge.start_challenge` ve
     `fist_challenge.start_challenge` çağırıyor. Challenge nesneleri
     CombatManager'a referans olarak verilmeli.
  2. `current_phase` atamaları: CombatManager faz değişikliğini
     DÖNDÜRÜR (return dict'te `next_phase` alanı), ana döngü uygular.
     CombatManager ASLA `self.current_phase` yazmaz.
  3. `_handle_enemy_attack` şu an hem hesaplama hem çizim yapıyor.
     Bu metod ikiye bölünmeli: `update_enemy_attack()` (hesap) ve
     UI çizimi ana döngüde `draw_enemy_attack()` çağrısıyla yapılmalı.

---

#### [YENİ] `inventory_handler.py` — Envanter Ekranı

`main.py`'den şu bölüm TAŞINIR:

| Mevcut Konum | Taşınacak İçerik |
|---|---|
| `main.py:984-1179` | `_handle_inventory` metodu ve sabitleri |

**Risk:** ORTA.
- Bu metod 195 satır ve oldukça bağımsız. Kendi dwell state'i var
  (`_inv_hovered_*`, `_inv_dwell_*`).
- `self.state`, `self.tracker`, `self.ui` referansları gerekir.
- `self.current_phase` ataması var (envanter kapatıldığında).

---

### 4.3. Hedeflenen Nihai Dosya Yapısı

```
python_dnd/
├── main.py                 (~400 satır, sadece oyun döngüsü + faz yönlendirme)
├── game_state.py            (~400 satır, durum yönetimi + karakter + mesaj geçmişi)
├── game_data.py             [YENİ] (~200 satır, tüm statik sözlükler ve sabitler)
├── combat_manager.py        [YENİ] (~400 satır, savaş mantığı)
├── inventory_handler.py     [YENİ] (~200 satır, envanter ekranı)
├── prompt_builder.py        [YENİ] (~200 satır, AI prompt üretimi)
├── shop_system.py           [YENİ] (~80 satır, dükkan sistemi)
├── ai_manager.py            (~230 satır, değişmez)
├── ui_renderer.py           (~900 satır, değişmez — ileride ayrılabilir)
├── vision_engine.py         (~450 satır, değişmez)
├── shape_challenge.py       (~370 satır, değişmez)
├── fist_challenge.py        (~280 satır, değişmez)
├── dice_challenge.py        (~250 satır, değişmez)
├── music_manager.py         (~190 satır, değişmez)
├── config_manager.py        (~80 satır, değişmez)
├── menu_system.py           (~550 satır, değişmez — ileride kamera paylaşımı)
├── tests/                   [YENİ]
│   ├── test_game_state.py
│   ├── test_combat.py
│   ├── test_shop.py
│   ├── test_ai_parse.py
│   └── test_config.py
├── RESTRUCTURE_PLAN.md      (bu dosya)
├── requirements.txt
├── game_config.json
├── hand_landmarker.task
└── music/
    └── (11 mp3 dosyası)
```

---

## 5. UYGULAMA SIRASI

Aşağıdaki sıra, **her adımda en düşük riski** hedefler.
Her adım bir commit olmalı ve arada oyun test edilmelidir.

### AŞAMA 0: Güvenlik Ağı (Hiçbir Kod Değişmez)

- [ ] 0.1 — `tests/` dizini oluştur, `pytest` ekle (S16, S17) — Risk: Sıfır
- [ ] 0.2 — `test_game_state.py` — saf fonksiyonlar için unit testler yaz (S16) — Risk: Sıfır
- [ ] 0.3 — `test_ai_parse.py` — `_parse_response` testleri (S16) — Risk: Sıfır
- [ ] 0.4 — `test_config.py` — config fonksiyonları testleri (S16) — Risk: Sıfır
- [ ] 0.5 — `test_snapshots.py` — characterization (snapshot) testleri yaz (S16) — Risk: Sıfır
- [ ] 0.6 — `requirements.txt` pinleme (S18) — Risk: Çok düşük

**Adım 0.5 Detayı:** Snapshot testleri God Object'lerdeki karmaşık
metodların davranışını dondurur. Bilinen bir `GameState` oluşturulur
(sabit HP/gold/karakter), sahte AI yanıtı verilir, çıkan state JSON
olarak kaydedilir. Refactoring adımlarında bu JSON'lar kontrol edilir.

**DOĞRULAMA:** `pytest tests/` çalışır ve tüm testler geçer.
Oyun normal çalışır.

### AŞAMA 1: Bağımsız Küçük Düzeltmeler (Minimal Risk)

- [ ] 1.1 — `main.py:920-922` — `draw_buttons` parametre düzeltmesi (S01) — Risk: Çok düşük
- [ ] 1.2 — `main.py:__init__` — `_inv_hovered_*` attribute tanımları ekle (S11) — Risk: Çok düşük
- [ ] 1.3 — `main.py` — `_extra_turn_active` sıfırlama noktaları ekle (S04) — Risk: Çok düşük
- [ ] 1.4 — `main.py` — Savaş aksiyon string sabitleri tanımla (S10) — Risk: Çok düşük
- [ ] 1.5 — `ai_manager.py` — `ast.literal_eval` kaldır (S14) — Risk: Düşük

**DOĞRULAMA:** Her adımdan sonra:
1. `pytest tests/` — testler hala geçiyor mu?
2. Oyunu başlat, karakter oluştur, 1 savaş yap, envanter aç — crash yok mu?

### AŞAMA 2: Veri Ayrıştırma (Düşük Risk)

- [ ] 2.1 — `game_data.py` oluştur, statik sözlükleri taşı (S08) — Risk: Düşük
- [ ] 2.2 — `game_state.py`'de import'ları güncelle (S08) — Risk: Düşük
- [ ] 2.3 — `shop_system.py` oluştur, shop metodlarını taşı (S08) — Risk: Düşük
- [ ] 2.4 — `test_shop.py` yaz (S16) — Risk: Sıfır

**DOĞRULAMA:** Testler + savaş sonrası envanter+shop ekranı çalışıyor mu?

### AŞAMA 3: Prompt Ayrıştırma (Orta Risk)

- [ ] 3.1 — `prompt_builder.py` oluştur — saf fonksiyonlar (static method) (S08) — Risk: Orta
- [ ] 3.2 — Prompt metodlarını parametre bazlı olarak taşı (S08) — Risk: Orta
- [ ] 3.3 — `game_state.py`'deki çağrı noktalarını güncelle (verileri parametre olarak geçir) (S08) — Risk: Orta
- [ ] 3.4 — `test_prompts.py` — prompt fonksiyonlarını test et (saf fonksiyon, mock gereksiz) (S16) — Risk: Sıfır

**NOT:** `PromptBuilder` artık `GameState` referansı ALMAZ.
Her metod sadece ihtiyacı olan verileri parametre olarak alır.
Circular import riski sıfır. Detaylar Bölüm 4.1'de.

**DOĞRULAMA:** AI'dan yanıt alınıyor mu? Savaş prompt'u doğru mu?
Düşman çıkıyor mu? Seçenekler geliyor mu?

---

### AŞAMA 4: Savaş Yöneticisi (Yüksek Risk — En Dikkatli Aşama)

- [ ] 4.1 — `combat_manager.py` oluştur, boş sınıf (S07) — Risk: Sıfır
- [ ] 4.2 — Savaş bayraklarını taşı (`_selected_weapon`, `_defense_*`, vs.) (S07) — Risk: Orta
- [ ] 4.3 — `_process_attack`, `_process_defense`, `_process_flee` taşı (S07) — Risk: Orta
- [ ] 4.4 — `_process_player_combat_result` taşı (S07) — Risk: Yüksek
- [ ] 4.5 — `_start_enemy_attack`, `_handle_enemy_attack` taşı (S07) — Risk: Yüksek
- [ ] 4.6 — `_start_combat_challenge`, `_start_actual_challenge` taşı (S07) — Risk: Orta
- [ ] 4.7 — `test_combat.py` yaz (S16) — Risk: Sıfır
- [ ] 4.8 — S02 (HP çift uygulama) düzelt (S02) — Risk: Orta
- [ ] 4.9 — S05 (dodge/savunma karışıklığı) düzelt (S05) — Risk: Orta

**DOĞRULAMA:** Tam savaş döngüsü:
Saldır → challenge → hasar → düşman saldırısı → savunma →
düşman yenilgisi → envanter. Her adımda HP doğru mu?

---

### AŞAMA 5: Envanter ve Temizlik (Orta Risk)

- [ ] 5.1 — `inventory_handler.py` oluştur, envanter mantığını taşı (S07) — Risk: Orta
- [ ] 5.2 — `game_state.py` — `reset()` metodunu düzelt (S12) — Risk: Orta
- [ ] 5.3 — Faz geçişlerini Enum'a çevir (S09) — Risk: Orta
- [ ] 5.4 — Çift `draw_inventory` çağrısını optimize et (Performans) — Risk: Düşük

---

### AŞAMA 6: Güvenlik ve Platform (Ertelenen İşler)

- [ ] 6.1 — `python-dotenv` ekle, API key'i `.env` dosyasına taşı (S13) — Risk: Orta
- [ ] 6.2 — `pyperclip` ekle, clipboard fonksiyonunu değiştir (Kaspersky sorunu) (S15, S22) — Risk: Düşük
- [ ] 6.3 — Kamera paylaşımı (menü ↔ oyun tek kamera) (S22) — Risk: Orta
- [ ] 6.4 — `requirements.txt`'e `python-dotenv` ve `pyperclip` ekle (S18) — Risk: Çok düşük

---

## 6. HER ADIM İÇİN DOĞRULAMA YÖNTEMİ

Her commit sonrasında yapılması gereken kontrol listesi:

### Otomatik Testler
```bash
cd e:\Projeler\python_dnd
python -m pytest tests/ -v
```
Tüm testler geçmeli. Yeni kırılan test = yeni oluşturulan bug.

### Manuel Oyun Testi (5 Dakika Senaryosu)

1. **Başlat:** `python main.py` → Menü açılıyor mu?
2. **Ayarlar:** Ayarlar ekranına gir, API key görünüyor mu? Geri dön.
3. **Oyun Başlat:** Sınıf seç → Silah seç → Lokasyon seç
4. **Keşif:** AI yanıt geliyor mu? Seçenekler var mı?
   Parmakla seçim çalışıyor mu?
5. **Savaş:** Birkaç tur bekle, savaş başlıyor mu?
   Saldır → challenge çıkıyor mu? Hasar doğru mu?
   Savun → düşman saldırısı engelleniyor mu?
6. **Envanter:** Savaş bitince envanter+shop açılıyor mu?
   Silah equip/unequip çalışıyor mu? Shop'tan alım çalışıyor mu?
7. **Çıkış:** 'Q' ile çıkış → "Oyun kapatıldı" mesajı →
   Ana menüye dönüş.

Bu senaryo her AŞAMA sonunda tekrarlanmalıdır.

---

## EK: DOKUNULMAMASI GEREKENLER

Şu öğeler bu restructure sürecinde KESİNLİKLE DEĞİŞMEMELİDİR:

1. **Sistem prompt'u** (`game_state.py:842-916`) — Prompt metninin
   kendisi değişmemeli. Sadece metodu başka dosyaya taşımak kabul edilir.
2. **Hasar formülleri** (`main.py:545-611`) — Sayısal değerler
   (30-50 arası, 1.5x çarpan, vs.) korunmalı.
3. **Challenge süreleri** — `DRAW_TIME`, `COUNTDOWN_TIME`,
   `ACTIVE_DURATION` gibi sabitler korunmalı.
4. **Doğruluk hesaplama algoritması** (`shape_challenge.py:322-358`)
   — Formül korunmalı.
5. **El takip parametreleri** (`vision_engine.py:70, 125-128`)
   — Smoothing katsayısı, güven eşikleri korunmalı.
6. **Müzik dosya eşlemeleri** (`music_manager.py:46-57`)
7. **UI layout sabitleri** (`ui_renderer.py:53-110`)
8. **Sınıf/silah/stat verileri** — Veri değerleri korunmalı,
   sadece dosya lokasyonu değişebilir.

---

> **Son Not:** Bu belge yaşayan bir belgedir. Her aşama tamamlandığında
> ilgili bölüm `[TAMAMLANDI]` olarak işaretlenmeli ve karşılaşılan
> ek sorunlar eklenmelidir. Yeni bir model veya kişi projeye
> dahil olduğunda ilk okuması gereken belge budur.
