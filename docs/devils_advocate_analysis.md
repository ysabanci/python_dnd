# 🔥 Şeytanın Avukatlığı: python_dnd Proje Analizi

> [!CAUTION]
> Bu analiz, projedeki **potansiyel sorunları kasıtlı olarak öne çıkaran** bir "devil's advocate" perspektifindedir. Projenin iyi yönlerini (çalışıyor olması, modüler yapısı, kapsamlı mekanikler) göz ardı etmez ama odak noktası risklerdedir.

---

## 📊 Risk Haritası (Özet)

| Kategori | Risk Seviyesi | Acil Etki | Gelecek Etki |
|----------|:---:|:---:|:---:|
| 🔐 Güvenlik & API Key | 🔴 Kritik | Yüksek | Yüksek |
| 🏗️ Mimari / God Object | 🟠 Yüksek | Orta | Yüksek |
| 🐛 Gizli Buglar | 🟠 Yüksek | Yüksek | Orta |
| ⚡ Performans | 🟡 Orta | Orta | Yüksek |
| 🧪 Test Yokluğu | 🟠 Yüksek | Düşük | Çok Yüksek |
| 📐 UI / UX Sorunları | 🟡 Orta | Orta | Orta |
| 🤖 AI Bağımlılığı | 🟠 Yüksek | Yüksek | Yüksek |
| 🔧 Bakım & Teknik Borç | 🟠 Yüksek | Düşük | Çok Yüksek |
| 🌍 Taşınabilirlik | 🟡 Orta | Düşük | Yüksek |

---

## 🔴 1. GÜVENLİK & API KEY SORUNLARI (KRİTİK)

### 1.1 API Key Düz Metin Olarak Diskte

```
game_config.json → "api_key": "a"
```

- [game_config.json](file:///e:/Projeler/python_dnd/game_config.json) dosyasında API anahtarı **şifrelenmemiş JSON** olarak saklanıyor.
- `.gitignore`'da `game_config.json` var ama yanlışlıkla commit'lenmesi **bir an** meselesi.
- Herhangi bir malware, dosya tarayıcısı veya aynı makinede oturum açan başka bir kullanıcı bu anahtarı kolayca çalabilir.

> [!WARNING]
> `save_config()` fonksiyonu ([config_manager.py:62-69](file:///e:/Projeler/python_dnd/config_manager.py#L62-L69)) her çağrıldığında API key'i düz metin olarak diske yazıyor. Bu fonksiyon menü sisteminde **her ayar değişikliğinde** otomatik çağrılıyor.

### 1.2 API Key Environment Variable'dan da Çekilebiliyor

[ai_manager.py:29](file:///e:/Projeler/python_dnd/ai_manager.py#L29): `resolved_key = api_key or os.environ.get("API_KEY", "")` — Ortam değişkeni `API_KEY` adıyla set edilebilir ama bu **belgelenmemiş** ve kullanıcı bunu bilmiyor.

### 1.3 `ast.literal_eval` Güvenlik Riski

[ai_manager.py:218](file:///e:/Projeler/python_dnd/ai_manager.py#L218) ve [ai_manager.py:226](file:///e:/Projeler/python_dnd/ai_manager.py#L226):
```python
data = ast.literal_eval(json_str)
```
AI'dan gelen **dışarıdan kontrol edilemeyen** veriyi `ast.literal_eval` ile parse etmek, `json.loads` başarısız olduğunda devreye giriyor. `literal_eval` güvenli kabul edilse de, karmaşık iç içe yapılarla **bellek tüketimi saldırısı** yapılabilir. Ayrıca AI'ın beklenmedik Python literal'leri üretmesi durumunda garip davranışlara yol açabilir.

### 1.4 Clipboard Erişimi PowerShell ile

[menu_system.py:30-40](file:///e:/Projeler/python_dnd/menu_system.py#L30-L40): `subprocess.run(["powershell", "-Command", "Get-Clipboard"])` — PowerShell subprocess çağrısı, her Ctrl+V'de tetikleniyor. Güvenlik yazılımları bunu **şüpheli aktivite** olarak işaretleyebilir.

---

## 🏗️ 2. MİMARİ SORUNLAR

### 2.1 `main.py` = God Object (1304 Satır!)

[main.py](file:///e:/Projeler/python_dnd/main.py) tek başına **1304 satır** ve `DnDGame` sınıfı içinde:
- Oyun döngüsü yönetimi
- Karakter oluşturma akışı
- Savaş mantığı (saldırı, savunma, kaçış hesaplamaları)
- Düşman saldırı fazı
- Challenge yönetimi (şekil, yumruk, zar)
- Silah seçimi
- Envanter yönetimi
- Müzik geçişleri
- AI yanıt işleme

Bu sınıf **Single Responsibility Principle**'ı ciddi biçimde ihlal ediyor. Tek bir method değiştirmek bile yan etkiler yaratabilir.

### 2.2 `game_state.py` = İkinci God Object (1020 Satır!)

[game_state.py](file:///e:/Projeler/python_dnd/game_state.py) aynı şekilde devasa:
- Karakter verileri
- Savaş sistemi verileri
- Shop sistemi
- Dünya takibi
- AI prompt üretimi
- Mesaj geçmişi yönetimi
- HP/Gold hesaplamaları
- İstatistik sistemi
- Silah verileri

Her şey bu dosyada olduğu için **bir özellik eklemek bile tüm sistemi etkileyebilir**.

### 2.3 State Machine Yerine Spaghetti If-Else

[main.py:130-207](file:///e:/Projeler/python_dnd/main.py#L130-L207) — Ana oyun döngüsü, `current_phase` kontrolü için art arda `if/elif/continue` blokları kullanıyor. Bu **formal bir state machine** değil. Yeni bir faz eklemek için:
1. `PHASE_XXX` sabiti ekle
2. `_handle_xxx()` metodu yaz
3. `run()` metoduna yeni `if` bloğu ekle
4. Geçişleri her yere elle yaz

Bu süreç hataya **çok açık** ve bir faz geçişi unutulduğunda oyun kilitlenebilir.

### 2.4 Doğrudan `import random` Fonksiyon İçinde

[game_state.py:219](file:///e:/Projeler/python_dnd/game_state.py#L219), [game_state.py:480](file:///e:/Projeler/python_dnd/game_state.py#L480), [game_state.py:611](file:///e:/Projeler/python_dnd/game_state.py#L611), [game_state.py:776](file:///e:/Projeler/python_dnd/game_state.py#L776) — `random` modülü dosya başında import edilmek yerine **fonksiyon içinde tekrar tekrar import ediliyor**. Bu hem performans kaybı hem de kötü pratik.

### 2.5 Circular Awareness

`main.py` → `game_state.py` → (AI prompt'ta savaş mantığı) → `main.py`'deki hesaplamalarla çelişebilir. Savaş hasar hesabı hem `main.py`'de hem de `game_state.py`'nin prompt'larında **ayrı ayrı tarif ediliyor**, tutarsızlık riski yüksek.

---

## 🐛 3. GİZLİ BUGLAR VE HATA POTANSİYELLERİ

### 3.1 🔴 `_extra_turn_active` Hiçbir Zaman Sıfırlanmıyor (Savaş Dışında)

[main.py:110](file:///e:/Projeler/python_dnd/main.py#L110): `self._extra_turn_active: bool = False` — Bu bayrak `_process_player_combat_result` içinde `True` yapılıyor ama **sadece `_restart()`'ta sıfırlanıyor**. Savaş bittikten sonra normal modda bu bayrak `True` kalabilir ve gelecek savaşta beklenmedik davranışlara yol açabilir.

### 3.2 🔴 Düşman HP Sıfırlanma Zamanlaması

[game_state.py:266](file:///e:/Projeler/python_dnd/game_state.py#L266): `self.enemy_hp = self.enemy_max_hp` — Düşman HP'si **sadece `just_entered_combat` True olduğunda** sıfırlanıyor. Eğer AI art arda `mod='savas'` dönerse (`just_entered_combat = False` olur) düşman HP'si **önceki savaştan kalma** değerle başlayabilir.

### 3.3 🟠 Yumruk Challenge Accuracy Kesikli

[fist_challenge.py:120-127](file:///e:/Projeler/python_dnd/fist_challenge.py#L120-L127):
```python
if self.hit_count >= 3: accuracy = 100.0
elif self.hit_count == 2: accuracy = 60.0
elif self.hit_count == 1: accuracy = 25.0
else: accuracy = 0.0
```
4 hedeften 3'ünü vursan `%100`, 2'sini vursan `%60`. **4'ünü de vurmanın ekstra ödülü yok**. Bu, oyuncuyu 3'te bırakmaya teşvik eder.

### 3.4 🟠 Race Condition: AI Thread vs Main Loop

[ai_manager.py:126-131](file:///e:/Projeler/python_dnd/ai_manager.py#L126-L131): API çağrısı daemon thread'de yapılıyor. `_last_response` ve `_last_error` lock ile korunsa da, `main.py`'deki [_check_ai_response()](file:///e:/Projeler/python_dnd/main.py#L1198-L1249) metodu `get_last_response()` çağrısıyla response'u alıp `None` yapıyor. Eğer **tam o anda** yeni bir thread sonuç yazarsa, eski sonuç kaybolabilir.

### 3.5 🟠 `draw_buttons` Farklı Signature'lar

[main.py:920-922](file:///e:/Projeler/python_dnd/main.py#L920-L922) — Silah seçim fazında `draw_buttons` çağrılırken `mode` parametresi olarak `self.state.active_option_count` (integer) gönderiliyor:
```python
frame = self.ui.draw_buttons(frame, self.state.current_options,
                              hover_quadrant, progress,
                              self.state.active_option_count)
```
Ama `draw_buttons`'ın 5. parametresi `mode: str = "kesif"` — **integer verildiğinde string karşılaştırması başarısız olur**, savaş modu renkleri hiç uygulanmaz. Bu sessiz bir bug.

### 3.6 🟡 `_defense_blocked` ve `_defense_partial` Dodge'da Karışıyor

[main.py:674](file:///e:/Projeler/python_dnd/main.py#L674): DEX dodge durumunda `self._defense_blocked = True` set ediliyor. Ama bu bayrak normalde **savunma challenge sonucunda** set edilmeli. Dodge ve savunma aynı bayrağı paylaşınca, düşman saldırı animasyonunda **"MÜKEMMEL SAVUNMA!"** yazısı gösteriliyor — oyuncu savunma yapmamış bile olsa.

### 3.7 🟡 Ganimet Anahtar Kelime Çakışması

[main.py:356-363](file:///e:/Projeler/python_dnd/main.py#L356-L363): Ganimet alma/reddetme, seçenek metnindeki **anahtar kelime aramasıyla** yapılıyor. "Silahı al ve devam et" gibi bir seçenekte hem `"al"` hem `"devam"` geçiyor. `is_reject` öncelikli kontrol edilse de, **"Ganimeti al, birak bence"** gibi garip AI çıktılarında davranış tahmin edilemez.

### 3.8 🟡 Envanter `hovered_shop` `getattr` Hack'i

[main.py:1025-1028](file:///e:/Projeler/python_dnd/main.py#L1025-L1028):
```python
hovered_shop=getattr(self, '_inv_hovered_shop', -1),
```
Bu `getattr` kullanımı, attribute'un `__init__`'te tanımlanmadığını gösteriyor. İlk envanter açılışında `_inv_hovered_shop` yoksa varsayılan `-1` kullanılıyor. Bu **lazy initialization anti-pattern**.

### 3.9 🟡 `reset()` = `__init__` Çağrısı

[game_state.py:834](file:///e:/Projeler/python_dnd/game_state.py#L834): `self.__init__(Character())` — Reset metodu `__init__`'i doğrudan çağırıyor. Bu, **`__init__`'te ileride eklenen herhangi bir parametreyi** atlamaya açık ve Python'da anti-pattern olarak kabul edilir.

### 3.10 🟡 `_parse_hp_changes` Çifte HP Uygulaması

[game_state.py:971-1007](file:///e:/Projeler/python_dnd/game_state.py#L971-L1007): Bu metod, `update_from_ai_response` sonunda çağrılıyor ve hikaye metnindeki `[HP:-10]` tag'lerini parse ediyor. Ama aynı `update_from_ai_response` metodu **zaten** `hp_degisim` alanını işliyor. Eğer AI hem `hp_degisim: -10` hem de hikayede `[HP:-10]` yazarsa, hasar **iki kez** uygulanır.

---

## ⚡ 4. PERFORMANS SORUNLARI

### 4.1 Her Frame'de Çift `draw_inventory` Çağrısı

[main.py:1013-1029](file:///e:/Projeler/python_dnd/main.py#L1013-L1029) ve [main.py:1159-1173](file:///e:/Projeler/python_dnd/main.py#L1159-L1173): `_handle_inventory` metodu her frame'de `draw_inventory`'yi **iki kez** çağırıyor — ilki "regions almak için preview", ikincisi gerçek çizim. Bu devasa overlay hesaplama işlemini **her frame'de çiftliyor**.

### 4.2 `cv2.addWeighted` Overuse (Frame Kopyalama Cehennemi)

Proje genelinde `overlay = frame.copy()` + `cv2.addWeighted()` deseni **aşırı kullanılıyor**. Tek bir `draw_inventory` çağrısında en az **7-8 frame kopyası** oluşturuluyor (`ov`, `ov2`, `ov3`, `ov4`, `ov5`, `ov6`, `ov7`). 640x480 çözünürlükte bile bu **frame başına ~20-30MB** bellek ayırma/serbest bırakma demek.

### 4.3 MediaPipe IMAGE Modunda Çalışıyor

[vision_engine.py:123](file:///e:/Projeler/python_dnd/vision_engine.py#L123): `running_mode=vision.RunningMode.IMAGE` — MediaPipe **her frame'de sıfırdan algılama** yapıyor. `VIDEO` veya `LIVE_STREAM` modları temporal tracking kullanarak çok daha performanslı olurdu.

### 4.4 `_calculate_accuracy` Brute Force

[shape_challenge.py:322-358](file:///e:/Projeler/python_dnd/shape_challenge.py#L322-L358): Doğruluk hesabı, kullanıcının her noktası için **tüm hedef noktalara** mesafe hesaplayarak yapılıyor. O(n*m) karmaşıklığında. 5 saniyelik çizimde yüzlerce nokta birikiyor, bu hesaplama **anlık gecikmeye** neden olabilir.

### 4.5 Sistem Prompt'u Devasa (~3KB Metin)

[game_state.py:842-916](file:///e:/Projeler/python_dnd/game_state.py#L842-L916): Sistem prompt'u **75 satır** ve her AI isteğinde gönderiliyor. Üstelik `get_dynamic_prompt()` her turda ek bağlam ekliyor. Token maliyeti hızla artıyor.

---

## 🤖 5. AI BAĞIMLILIĞI VE KIRILANLIK

### 5.1 AI Çıktı Formatına %100 Bağımlılık

Oyun, AI'ın **her zaman geçerli JSON** döndürmesine bağımlı. `_parse_response` ([ai_manager.py:194-231](file:///e:/Projeler/python_dnd/ai_manager.py#L194-L231)) fallback döndürse de:
- `mod` alanı yoksa varsayılan `"kesif"` — savaş ortasında AI hata verirse **savaş aniden kesilir**
- `secenekler` yoksa "İlerle/Etrafi arastir/Bekle/Geri don" gösterilir — **hikayeyle alakasız seçenekler**
- Zar mekanizması, shop, ganimet sistemi tamamen AI'ın doğru alanları doldurmasına bağlı

### 5.2 Prompt Injection Riski

AI'a gönderilen prompt'larda kullanıcının seçimleri doğrudan embed ediliyor:
```python
prompt = f"Secimim: {choice_text}. Tema: {self.current_theme}."
```
Eğer AI **seçenek metnine zararlı talimatlar** yerleştirirse (prompt injection) ve kullanıcı bunu seçerse, sonraki prompt'larda AI'ın davranışı değişebilir.

### 5.3 HP Değişimi Çelişkisi

Sistem prompt'u diyor ki: *"Savas modunda dusman HER TUR saldirsin. hp_degisim NEGATIF olmali"*
Ama `update_from_ai_response`'da ([game_state.py:321-322](file:///e:/Projeler/python_dnd/game_state.py#L321-L322)):
```python
elif self.current_mode == "savas":
    hp_change = 0
```
Savaş modunda HP değişimi **sıfırlanıyor** çünkü hasar challenge sistemiyle yönetiliyor. Ama sistem prompt'u AI'dan hala hasar istiyor — **çelişkili talimat**, token israfı.

### 5.4 Mesaj Geçmişi Kırpma Sonrası Bağlam Kaybı

[game_state.py:939-969](file:///e:/Projeler/python_dnd/game_state.py#L939-L969): 20 mesajdan sonra eski mesajlar kırpılıp kısa bir özet bırakılıyor. Bu özet **sadece karakter durumunu** içeriyor — NPC isimleri, önemli olaylar, hikaye kararları **kaybolmuş oluyor**. AI, 20 turdan sonra **amnezi** yaşayacak.

### 5.5 Türkçe Karakter Çelişkisi

Sistem prompt'u: *"Turkce ozel karakter KESINLIKLE KULLANMA"* — Ama AI modelleri bunu %100 garanti edemez. `sanitize_text()` fonksiyonu mevcut ama bu **sadece gösterim katmanında** çalışıyor. AI'ın döndüğü JSON key'lerinde Türkçe karakter olursa (ör. `"seçenekler"` yerine `"secenekler"`) ayrıştırma **sessizce başarısız olur**.

---

## 🧪 6. TEST YOKLUĞU

### 6.1 Sıfır Unit Test

Projede [test_dual_hands.py](file:///e:/Projeler/python_dnd/test_dual_hands.py) dışında **hiçbir test yok**. O da çift el algılamanın manuel testi.

- Savaş hasar hesaplamaları test edilmemiş
- Shop alım mantığı test edilmemiş
- Stat etkileri test edilmemiş
- AI yanıt ayrıştırma test edilmemiş
- Ganimet sistemi test edilmemiş
- Envanter equip/unequip test edilmemiş

> [!IMPORTANT]
> 1020 satırlık `game_state.py`'de düzinelerce **saf fonksiyon** (pure function) var ve bunlar kolayca test edilebilir: `get_stat_effect_on_combat()`, `get_weapon_stats()`, `toggle_equipped()`, `shop_buy()` gibi. Bunlar test edilmeden her değişiklik **kör uçuş**.

### 6.2 Hasar Dengeleme Kör

Savaş sistemi karmaşık ama **hiç simülasyon yapılmamış**:
- Savaşçı'nın 1.25x saldırı çarpanı + Çift El Kılıcı'nın +10 bonusu + yüksek STR = **tek vuruşta düşmanı öldürebilir mi?**
- Hırsız'ın %40 kaçış eşiği + DEX bonus'uyla neredeyse **her zaman kaçabilmesi** denge sorunu mu?
- Stat cap 200 ama formüllerde kontrol yok — STR 200 olursa `attack_bonus = 190`, bu **oyunu kırar mı?**

Cevap: **Bilmiyoruz**, çünkü test yok.

---

## 📐 7. UI / UX SORUNLARI

### 7.1 OpenCV Metin Rendering = Kötü Türkçe Desteği

OpenCV'nin `putText` fonksiyonu **sadece ASCII karakter** destekliyor. `sanitize_text()` ile Türkçe karakterler ASCII'ye dönüştürülüyor ama bu:
- "Şifacı" → "Sifaci" (anlamı bozulmaz)
- "Göl" → "Gol" (spor!) 
- "Öldür" → "Oldur" (sessiz harf değişikliği, anlam bulanıklaşır)

### 7.2 640x480 Kamera ama 1280x720 İstenmiş

[vision_engine.py:94-95](file:///e:/Projeler/python_dnd/vision_engine.py#L94-L95): Kamera 1280x720 olarak ayarlanmaya çalışılıyor ama çalıştırma çıktısında `Kamera cozunurlugu: 640x480` görünüyor. UI layout'u **960x720 minimum** ile tasarlanmış ([main.py:134-135](file:///e:/Projeler/python_dnd/main.py#L134-L135)). 640x480 frame'de UI elemanları **sıkışık ve okunaksız** olabilir.

### 7.3 Dwell Selection = Erişilebilirlik Problemi

Tüm seçimler **2 saniye parmağı tutma** (dwell) ile yapılıyor. Eli titreyen, motor beceri zorluğu olan veya rahat oturamayan kullanıcılar için bu **ciddi bir engellilik bariyeri**. Alternatif giriş yöntemi (klavye, mouse) oyun içinde yok (sadece menüde mouse var).

### 7.4 `cv2.waitKey(1)` Tek Çıkış Yolu

Oyundan çıkmak için **sadece 'q' tuşu** çalışıyor. Pencere'nin X butonuna basmak OpenCV'de `cv2.waitKey` döngüsünü kırmaz — oyun **zombie process** olarak çalışmaya devam eder.

---

## 🔧 8. BAKIM VE TEKNİK BORÇ

### 8.1 Hardcoded String'ler Her Yerde

Savaş seçenekleri kontrol edilirken:
```python
action_lower in ("saldir", "saldiri", "buyu")  # main.py:394, 479, 560
action_lower in ("savun", "savunma")            # main.py:480
action_lower in ("kac", "kacis")                # main.py:481
```
Aynı string'ler **en az 6 farklı yerde** tekrar ediyor. Biri değişirse diğerleri güncellenmezse **sessiz bug** oluşur.

### 8.2 Tutarsız İsimlendirme

- `_inv_hovered_idx` vs `hovered_idx` (underscore prefix tutarsızlığı)
- `start_time` vs `countdown_start` vs `result_time` (zaman değişkeni isimleri)
- `is_done()` vs `is_active()` vs `_challenge_completed` (durum sorgu yöntemleri)
- `cleanup()` vs `release()` vs `stop()` (kaynak temizleme)

### 8.3 `_api_error` State Leak

[main.py:1208](file:///e:/Projeler/python_dnd/main.py#L1208): `self.state._api_error = False` — `main.py` doğrudan `state` nesnesinin **private attribute**'una yazıyor. Bu encapsulation ihlali.

### 8.4 Magic Number Cenneti

```python
CRITICAL_HIT_THRESHOLD = 85    # main.py:51
EXTRA_TURN_CHANCE = 0.30       # main.py:54
ENEMY_ATTACK_DURATION = 3.0    # main.py:48
DRAW_TIME = 5.0                # shape_challenge.py:38
FIST_HIT_RADIUS = 55           # fist_challenge.py:31
SMOOTHING_FACTOR = 0.45        # vision_engine.py:70
SHOP_BASE_COST = 15            # game_state.py:606
```
Bu sabitler **birbirleriyle ilişkili** olabilir ama hiçbirinde "neden bu değer?" açıklaması yok. Oyun dengeleme yapmak isteyen biri nereden başlayacağını bilemez.

### 8.5 Müzik Dosyaları Repo'da (~100MB)

`music/` dizini toplam **~105MB** müzik dosyası içeriyor. Git repo'sunda binary dosyalar **repo boyutunu şişirir**, klonlama süresini artırır ve diff'leri anlamsızlaştırır. Git LFS veya harici depolama kullanılmalı.

---

## 🌍 9. TAŞINABİLİRLİK VE DAĞITIM

### 9.1 Windows'a Sıkı Bağımlılık

- `get_clipboard()`: PowerShell subprocess çağırıyor → **Linux/macOS'ta çalışmaz**
- `cv2.VideoCapture` MSMF backend'i → Çıktıdaki `cap_msmf.cpp` uyarıları Windows'a özgü
- `creationflags=0x08000000` (CREATE_NO_WINDOW) → Windows-specific flag

### 9.2 `hand_landmarker.task` = 7.8MB Binary

Bu dosya `.gitignore`'da ama **yoksa uygulama crash ediyor** ([vision_engine.py:116-119](file:///e:/Projeler/python_dnd/vision_engine.py#L116-L119)). İndirme talimatı yok, otomatik indirme yok. Yeni bir kullanıcı projeyi klonladığında **ne yapacağını bilemez**.

### 9.3 Kamera Olmadan Oynanamaz

Kamera açılamazsa `RuntimeError` fırlatılıyor ([main.py:65-68](file:///e:/Projeler/python_dnd/main.py#L65-L68)). **Masaüstü bilgisayarlarda** harici kamera olmadan oyun **hiç çalışmaz**. Kamera-bağımsız bir mod (mouse/klavye fallback) yok.

### 9.4 Bağımlılık Sürümü Pin'lenmemiş

[requirements.txt](file:///e:/Projeler/python_dnd/requirements.txt):
```
opencv-python>=4.8.0
mediapipe>=0.10.0
litellm>=1.40.0
```
Minimum sürüm verilmiş ama **üst sınır yok**. MediaPipe veya LiteLLM'in gelecek bir major sürümü API'yi kırarsa oyun çalışmaz. `pip freeze > requirements.txt` ile exact pinleme yapılmalı.

---

## 🔮 10. GELECEK SORUNLARI (ÖLÇEKLENME)

### 10.1 Yeni Karakter Sınıfı Eklemek = 8 Dosya Değiştirmek

Yeni bir sınıf (ör. "Paladin") eklemek için:
1. `game_state.py` → `CLASS_DATA`, `CLASS_BASE_STATS`, `WEAPON_DATA`, `WEAPON_STATS`, `CLASS_BONUS`, `CLASS_ADVANTAGE_KEY` (6 sözlük!)
2. `main.py` → `_init_startup()` seçenekleri (şu an 4 sınıf hardcoded, 5. sığmaz!)
3. `music_manager.py` → yeni tema eklenmesi (dolaylı)

**4'ten fazla sınıf eklemek UI'da mümkün değil** çünkü sadece 4 buton var.

### 10.2 Multiplayer = Sıfırdan Yeniden Yazım

Tüm mimari **tek oyuncu** üzerine kurulu. Ağ kodu, senkronizasyon, shared state yok. Multiplayer eklemek istersen **%80 rewrite** gerekir.

### 10.3 Save/Load Sistemi Yok

Oyun durumu hiçbir yerde **persist edilmiyor**. Oyun kapandığında her şey sıfırlanıyor. Uzun oturumlar kaybolur. `GameState`'in serialize edilmesi gerekir ama `Character` dataclass'ı dışında tüm state **düz attribute'lar** — seri hale getirmek zor.

### 10.4 Lokalizasyon İmkansız

Tüm metinler (savaş mesajları, geri bildirimler, UI etiketleri) **hardcoded Türkçe ASCII**. İngilizce veya başka bir dile çevirmek için **yüzlerce string'i** el ile değiştirmek gerekir.

### 10.5 Mod Desteği Yok

Yeni şekil tipleri, yeni challenge türleri, yeni temalar eklemek istesen hep **kaynak kodu** değiştirmen gerekir. Plugin/mod sistemi yok.

---

## 📋 ÖNCELİKLENDİRME ÖNERİSİ

Eğer bunları düzeltmek istersen, **öncelik sırası**:

### Acil Yapılması Gerekenler
1. **API Key Güvenliği**: En azından Windows Credential Manager veya bir `.env` + `python-dotenv` kullan
2. **`draw_buttons` Signature Bug'ı**: Silah seçiminde yanlış parametre tipi (int vs str)
3. **Çift HP Uygulaması**: `_parse_hp_changes` ve `hp_degisim` çakışması
4. **Kamera Fallback**: Kamera yoksa mouse/klavye modu

### Kısa Vadede Yapılması Gerekenler
5. **Unit Test Ekle**: En azından `game_state.py`'deki saf fonksiyonlar için
6. **State Machine Formalize Et**: Faz geçişlerini enum + transition table ile yönet  
7. **String Sabitleri Centralize Et**: Savaş aksiyonlarını tek yerde tanımla
8. **`_extra_turn_active` Reset**: Savaş bitişinde sıfırlanmasını garanti et

### Orta Vadede Yapılması Gerekenler
9. **God Object'leri Parçala**: `DnDGame` → `CombatManager`, `PhaseManager`, `InventoryManager`
10. **Performans**: Çift `draw_inventory` çağrısını düzelt, frame kopyalamayı azalt
11. **Save/Load Sistemi**: `GameState` serialize
12. **Git LFS**: Müzik dosyaları için

---

> [!NOTE]
> Bu analiz **en kötü senaryo** perspektifinden yazılmıştır. Projenin şu haliyle çalışıyor ve oynanabilir olması, webcam + el takibi + AI hikaye üretimi entegrasyonunun karmaşıklığı düşünüldüğünde **etkileyici bir başarıdır**. Burada listelenen sorunların çoğu "büyüme sancıları" kategorisindedir — proje büyüdükçe acı vermeye başlayacak ama şu an için çoğu tolere edilebilir.
