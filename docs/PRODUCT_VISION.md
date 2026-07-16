# 🧭 PRODUCT_VISION.md — Ürün Yönü ve Eleştirel Durum Değerlendirmesi

> **Yazan:** Claude (Fable 5)
> **Tarih:** 2026-07-07
> **Statü:** Yaşayan belge — kullanıcı ile yapılan stratejik değerlendirmeden doğdu.
>
> **Bu belge ne için?** RESTRUCTURE_PLAN.md "kod nasıl temizlenir" sorusunu,
> CLAUDE.md "bu proje nasıl yönetilir" sorusunu cevaplar. Bu belge ise
> **"bu proje NEREYE gidiyor ve neden"** sorusunu cevaplar. Bu projede çalışan
> her ajan, teknik bir görev almadan önce bu belgeyi okumalıdır — çünkü doğru
> yapılmış yanlış iş, yanlış yapılmış doğru işten daha tehlikelidir.

---

## 0. AJANLAR İÇİN TL;DR

1. Bu proje bir "metin macerası" DEĞİLDİR. Metin arayüzü geçici bir iskeledir.
   Nihai hedef: **oyuncunun kendisini ekranda oyunun kahramanı olarak gördüğü
   webcam-AR RPG** (Bölüm 2).
2. Refactoring dönemi **Aşama 6 ile kapanıyor**. Sonrasında öncelik iç temizlik
   değil, oyuncu-görünür değerdir (E02).
3. Yeni özellik tasarlarken/uygularken **G01–G06 kurallarına** uy (Bölüm 5).
4. Mevcut test ve changelog disiplini bu projenin en değerli varlıklarından
   biridir — eleştiriler bu kültürü gevşetme bahanesi DEĞİLDİR. Testler her
   değişiklikte geçmeye devam etmelidir.

---

## 1. ELEŞTİREL DURUM TESPİTİ

Aşağıdaki maddeler, önceki ajanların gözünden kaçan veya söylenmeyen yapısal
gerçeklerdir. Her biri ID'lidir; görev planlarken bu ID'lere referans verin.

### E01 — 237 test kısmi bir güvenlik yanılsamasıdır

Testlerin tamamı saf mantığı (hasar formülleri, shop, prompt string'leri)
kapsıyor. Oyunun asıl riskli katmanları test edilemeyen yerlerde: el takibinin
güvenilirliği, dwell seçiminin his kalitesi, AI yanıtlarının oynanabilirliği,
cv2.imshow döngüsünün kararlılığı. "237 passed" oyunun çalıştığını değil,
hesap makinesinin çalıştığını kanıtlar.

**Ne yapmalı:** Testler gerekli ama yeterli değil. Her önemli değişiklikten
sonra manuel oyun testi (RESTRUCTURE_PLAN Bölüm 6'daki 5 dakika senaryosu)
şarttır. "Testler geçiyor" ifadesi tek başına "iş bitti" anlamına gelmez.

### E02 — Refactoring tuzağı: oyuncu-görünür değer üretimi durdu

2026 Haziran başından beri beş aşama tamamlandı, binlerce satır taşındı — ve
oyun oyuncu gözünde bir milim ilerlemedi. Kod temizliği ölçülebilir ve tatmin
edicidir; ürün geliştirmek belirsiz ve korkutucudur. Bu yüzden refactoring
bağımlılık yapar.

**Ne yapmalı:** Aşama 6 (güvenlik/platform) tamamlanır, sonra refactoring
resmen kapanır. S09'un ikinci adımı (full State Pattern) ve benzeri "iç
güzellik" işleri **gündeme alınmaz**. Bir ajan yeni bir iç refactor önerecekse,
önce şu soruyu cevaplamalıdır: "Bu iş, bir oyuncunun deneyimini nasıl değiştirir?"

### E03 — cv2.imshow + pygame iskeleti bir prototip mimarisidir

Pencere cv2.imshow ile açılıyor, ses pygame'den geliyor. Tam ekran yönetimi,
düzgün input işleme, pencere davranışı — hepsi bu garip ikilinin üstünde.
Uzun vadede renderer değişimi kaçınılmazdır (bkz. V3) ve bu, plandaki tüm
kalan işlerden daha büyük bir mimari dönüşümdür.

**Ne yapmalı:** Yeni özellikleri bu iskelete derin bağlamayın. "Hesaplama alt
modülde, çizim ui_renderer'da, side-effect main'de" ayrımı (mevcut delegasyon
deseni) korunursa, ileride renderer değişimi sadece üst katmanı değiştirir.
Bu desenin asıl değeri budur — kod güzelliği değil, V3'e hazırlıktır.

### E04 — Donmuş prompt = doğrulanamaz içerik hattı

"Prompt'a dokunma" kuralı bir teknik borç itirafıdır: bir kelimelik
değişikliğin oyunu bozabilmesinden korkuluyorsa, prompt sistemi doğrulanamaz
demektir. S03 ve S06 gerçek buglar ve bu yüzden çözülemiyor. AI-anlatımlı bir
oyunda prompt, içerik hattının kendisidir — sonsuza kadar donduramazsınız.
İngilizce lokalizasyon da (P04) bu duvara çarpar.

**Ne yapmalı:** Gelecekte bir "AI Eval" aşaması gerekiyor: sabit senaryolarla
(seed'li karakter + sabit geçmiş) AI yanıtlarının JSON şema doğrulaması + altın
kayıt karşılaştırması. Bu altyapı kurulmadan prompt değişikliği YAPILMAZ;
kurulduktan sonra prompt özgürce evrilebilir. (G03)

### E05 — Dağıtım sıfır: bu oyunu geliştiricisinden başka kimse çalıştıramaz

README yok. Kurulum zinciri: Python 3.13 + mediapipe + opencv + kendi API
key'ini getir + webcam + Windows + model dosyası. "Piyasa potansiyeli"
konuşulmadan önce cevaplanması gereken soru: **yabancı biri bu oyunu 5 dakikada
oynatabilir mi?** Şu an cevap kesin hayır — ve bu, kalan tüm teknik sorunların
toplamından büyük bir engel.

**Ne yapmalı:** Aşama 6 sonrası ilk işler: README + tek komut kurulum (ideali
PyInstaller paketi), model dosyasının otomatik indirilmesi, key gerektirmeyen
bir demo modu. Her yeni özellik "kurulum yükünü artırıyor mu?" sorusuyla tartılır.

### E06 — "Kusursuz takip" yanlış hedeftir; doğru cevap sanat yönüdür

Vücut üstünde piksel-hassas 3D kıyafet oturtma, yüzlerce mühendisin çalıştığı
şirketlerde (Snap, TikTok) bile titrer. Bu bir mühendislik yarışı değil,
**tasarım kararıdır**: 5 cm kayan fotogerçekçi pelerin "bozuk" görünür; aynı
kaymayı yapan iri, stilize, çizgi-film zırh "böyle tasarlanmış" görünür.
Takip hatasını affeden stilizasyon, bu projenin grafik kimliği olmalıdır.

**Ne yapmalı:** Görsel özellik tasarlarken hassas hizalama gerektiren çözümler
önermeyin. Glow, silüet, parçacık, iri parçalar = dost. İnce kenar hizalama,
kumaş fiziği, fotogerçekçilik = düşman. (G04)

---

## 2. VİZYON — KUZEY YILDIZI

Oyuncu ekranda **kendisini** görür: sırtında satın aldığı pelerin, elinde
havada çizdiği rünle tutuşan büyü, başının üstünde HP'si, arkasında odası
değil zindanın kendisi. Hikayeyi AI anlatır, dünyayı harita gösterir, oyun
oyuncuyu hatırlar. Metin kutuları değil; **"seni kahraman olarak filme çeken
oyun."**

Bu vizyonun üç yapısal avantajı var (iş gerekçesi için Bölüm 4):
kostüm = oyun sektörünün en güçlü monetizasyon kalıbı (skin) ama kişisel
bahisle; her oturum doğal olarak paylaşılabilir video üretir; ve bu kesişimde
(webcam-AR × LLM anlatı × RPG) henüz kimse yok.

Mevcut metin-tabanlı oyun bu vizyonun **iskelesidir**: AI anlatı motoru,
challenge mekanikleri, karakter/envanter sistemi — hepsi nihai üründe aynen
yaşayacak. Çöpe gidecek olan tek şey sunum katmanı, o da zaten prototipti.

---

## 3. VİZYON MERDİVENİ (V1–V4)

Her basamak **kendi başına yayınlanabilir bir oyundur** ve bir sonrakine
geçmeden önce gerçek oyuncularla test edilmelidir. Basamak atlamak yasaktır —
mezarlık, 4. basamağa zıplayanlarla doludur.

### V1 — Efekt Katmanı (mevcut stack ile, haftalar mertebesi)

- Şekil çizerken parmak izini takip eden büyü parıltısı; isabette vücutta
  hasar flaşı; baş üstü HP göstergesi; zar/challenge'larda ekran efektleri.
- **Teknoloji:** MediaPipe hand landmark'ları zaten var. Kamera frame'i
  üstüne alpha-blend kompozit. cv2 çizgi çizimi yerine hazırlanmış sprite
  blend'i (performans için).
- **Neden önce bu:** Sıfır yeni bağımlılık, mevcut mimariyle uyumlu ve
  60 saniyelik tanıtım videosunun malzemesi budur.

### V2 — Poz + Segmentasyon: "Odanda değil, zindandasın" (en büyük his sıçraması)

- MediaPipe Pose (33 landmark) ile omuz/gövde takibi → paper-doll 2D kostüm
  parçaları (omuzluk, göğüs plakası — omuz çizgisine göre döner/ölçeklenir).
- MediaPipe Selfie Segmentation ile kişi maskesi → oyuncunun arkasındaki oda
  silinir, yerine lokasyonun sahnesi gelir. Envanterdeki "kıyafet satın alma"
  burada gerçeğe döner.
- **Mühendislik notu:** Hands + Pose + Segmentation aynı anda CPU'da zorlanabilir.
  Çözüm katmanlama: pose her frame, segmentation 2 frame'de bir, gerekirse
  çözünürlük düşürme. "Kusursuz" değil "stilize" hedeflenir (E06).

### V3 — Motor Ayrışması: Proton Hamlesi

- Python, **tracking sunucusuna** dönüşür: MediaPipe çıktılarını (landmark +
  maske) UDP/WebSocket ile yayınlar. Render tarafı gerçek bir oyun motoruna
  (Godot önerilir; açık kaynak, hafif) geçer. Kanıtlanmış mimari: VTuber
  ekosistemi tam olarak böyle çalışır (OpenSeeFace → motor).
- Bu hamleyle bedavaya gelenler: parçacık sistemleri, shader'lar, ışık,
  gerçek UI, **harita ekranı** (visited_locations verisi zaten tutuluyor),
  düzgün pencere/tam ekran yönetimi. cv2.imshow burada ölür (E03 çözülür).
- **Kritik:** Python tarafındaki oyun mantığı (combat_manager, game_state,
  prompt_builder) saf kaldığı sürece bu geçiş sunum katmanı değişimidir,
  yeniden yazım değildir. Bugünkü delegasyon deseninin var olma sebebi budur.

### V4 — Tam Vizyon

- Poz iskeletine bağlı stilize 3D kostümler; lokasyon başına AI-üretimi sahne
  görselleri; kalıcı dünya hafızası ve haritası; kozmetik ekonomisi.
- Bu basamağın detay planı, V2–V3 oyuncu geri bildirimi olmadan YAZILMAZ.

---

## 4. İŞ / PAZAR GERÇEKLERİ

- **P01 — Kozmetik monetizasyon doğal uyum:** "Ekrandaki KENDİ üstüne pelerin
  almak", oyun sektörünün en güçlü gelir kalıbının (skin ekonomisi) kişisel
  bahisli hali. Vizyonun çekirdek fantezisi ile para modeli aynı şey.
- **P02 — Klip-doğal ürün:** Kamerada bedeniyle büyü yapan insan görüntüsü
  kendiliğinden paylaşılabilir içeriktir. Yayıncı/streamer kanalı, bu ürünün
  en ucuz ve en güçlü dağıtım yoludur. Her basamak "bunun videosu çekilir mi?"
  sorusuyla tartılmalı.
- **P03 — "Neden şimdi":** Bu fikir kategorisi daha önce donanım yüzünden öldü
  (Kinect özel donanım istiyordu). O kısıt artık yok: webcam evrensel,
  MediaPipe CPU'da gerçek zamanlı. Fikrin zamanı gelmiş olabilir.
- **P04 — Dil:** Türkçe AI-RPG nişinde ilk olunabilir ama niş küçük. Vizyon
  görselleştikçe dil bağımlılığı azalır; İngilizce'ye geçiş büyük oranda
  prompt çevirisidir — ki bu da E04'teki eval altyapısını şart koşar.
- **P05 — BYO API key ölü doğumdur:** Tüketiciden kendi key'ini istemek kitle
  ürünü öldürür. Kısa vadede: key'siz demo modu + ücretsiz tier'lı sağlayıcı
  desteği. Uzun vadede barındırılan servis + abonelik/kozmetik gerekir.
  Bu, projenin cevaplanmamış en büyük iş sorusudur.
- **P06 — Ara pazarlar:** Kitlesel Steam çıkışından önce gerçekçi duraklar:
  itch.io deney oyunu (portfolyo + geri bildirim), sergi/etkinlik/fuar
  kurulumları (jest oyunlarının fiilen para kazandığı yer), yayıncı işbirlikleri.

---

## 5. AJAN KURALLARI (G01–G06)

Bu kurallar CLAUDE.md'deki kuralların ÜSTÜNE gelir, onları iptal etmez.

- **G01:** İç refactor önerisi, oyuncu-görünür bir gerekçe olmadan gündeme
  alınmaz. "Kod daha temiz olur" tek başına gerekçe değildir (E02).
- **G02:** Yeni özellikler render/mantık ayrımını korur: hesaplama saf
  modülde, çizim ui_renderer'da, side-effect main'de. Bu, V3 motor ayrışmasının
  sigortasıdır (E03).
- **G03:** AI eval altyapısı kurulmadan prompt metnine dokunulmaz. Kurulduktan
  sonra prompt değişiklikleri eval'den geçerek yapılır (E04).
- **G04:** Hassas hizalama gerektiren görsel çözüm önerilmez; takip hatasını
  affeden stilizasyon esastır (E06).
- **G05:** Her özellik şu soruyla tartılır: "Yabancı biri bu oyunu 5 dakikada
  kurup oynayabiliyor mu, bu iş o süreyi kısaltıyor mu uzatıyor mu?" (E05)
- **G06:** Vizyon merdiveninde basamak atlanmaz; bir basamağın işi yapılırken
  bir üst basamağın altyapısı "hazırlık" bahanesiyle şimdiden inşa edilmez.

---

## 6. SIRADAKİ SOMUT SIRA

1. **Aşama 6'yı bitir** (dotenv, pyperclip, kamera paylaşımı, requirements) —
   RESTRUCTURE_PLAN'daki son refactor işi.
2. **Dağıtım paketi:** README (kurulum + oynanış), model dosyası otomatik
   indirme, mümkünse PyInstaller tek-exe denemesi (E05).
3. **V1 efekt prototipi** + 60 saniyelik oynanış videosu.
4. Videoyu ve oyunu **5 yabancıya** göster; geri bildirimi bu belgeye işle.
5. Geri bildirime göre V2'ye geç veya V1'i düzelt.

> **Son not:** Bu belge yaşayan bir belgedir. Vizyon basamakları tamamlandıkça,
> oyuncu geri bildirimi geldikçe ve iş kararları netleştikçe güncellenmelidir.
> Bir eleştiri (E01–E06) geçerliliğini yitirdiyse silinmez, üstü çizilip
> "çözüldü" olarak işaretlenir — gelecek ajanlar neyin neden yapıldığını görsün.
