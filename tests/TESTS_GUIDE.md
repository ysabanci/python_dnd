# python_dnd Test Rehberi

Bu klasör, projenin yeniden mimari (restructure) süreci kapsamında güvenli bir şekilde kod değiştirilebilmesi için oluşturulmuş testleri içerir. Testler, yeni eklenecek veya değiştirilecek kodların oyunun mevcut davranışını bozmadığını garantiler.

## 📂 Mevcut Test Dosyaları ve Kapsamları

- **`conftest.py`**: Testler için gerekli ortak fixture'ları (hazır obje şablonları, mock veriler) barındırır. Test dosyalarının tekrarlı kod yazmasını engeller.
- **`test_ai_parse.py`**: AI'dan dönen metin/JSON formatındaki yanıtların doğru ayrıştırılıp ayrıştırılmadığını test eder (`_parse_response`). Hatalı veya eksik formatlı gelen AI mesajlarına karşı sistemin toleransını ölçer.
- **`test_config.py`**: Ayarların okunması, yazılması ve özellikle API anahtarının gizlenmesi (maskeleme) gibi konfigürasyon işlemlerinin doğru çalışıp çalışmadığını test eder.
- **`test_game_state.py`**: `GameState` sınıfındaki dışa bağımlılığı olmayan "saf fonksiyonları" (HP/altın değişimi, eşya takma/çıkarma, istatistik hesaplamaları, dükkan işlemleri) test eder.
- **`test_snapshots.py`**: Karakterizasyon (Davranış Dondurma) testlerini içerir. Yeniden yapılandırılması (refactoring) zor olan büyük ve karmaşık metotların belirli girdiler için beklenen mevcut çıktıları (state'i) vermeye devam ettiğini JSON formatında kayıt altına alır ve doğrular.

## 🚀 Testler Nasıl Çalıştırılır?

Konsoldan `pytest` komutunu doğrudan çağırdığınızda Windows PowerShell "CommandNotFoundException" hatası verebilir. Bu durum `pytest` modülünün kurulu olmamasından veya sanal ortamın (venv) `Scripts` yollarının tam olarak algılanamamasından kaynaklanır.

Testleri toplu ve sorunsuz çalıştırmanın en teknik ve kesin yolu, `pytest` modülünü doğrudan Python yürütücüsü (executable) üzerinden çağırmaktır:

```powershell
# 1. Projenin ana dizininde olduğunuzdan emin olun
cd e:\Projeler\python_dnd

# 2. Eğer pytest kurulu değilse önce kurun
pip install pytest

# 3. Testleri toplu olarak çalıştırmak için Python modülü olarak çağırın
python -m pytest tests/
```

### 🛠 Ekstra Yararlı Parametreler:
- **Detaylı Çıktı Almak İçin (`-v`):** Hangi testin geçip hangisinin kaldığını tek tek ismen görmek isterseniz:
  `python -m pytest tests/ -v`
- **Sadece Belirli Bir Test Dosyasını Çalıştırmak İçin:**
  `python -m pytest tests/test_game_state.py`
- **İçerideki Print (Konsol) Çıktılarını Görebilmek İçin (`-s`):** Normalde pytest başarılı testlerdeki `print` fonksiyonlarının çıktılarını gizler. Bunları görmek isterseniz:
  `python -m pytest tests/ -s`

## 🌐 Sanal Ortam (Virtual Environment - venv) ve Testler

Python projelerinde bağımlılıkların (kütüphanelerin) işletim sisteminin ana Python kurulumunu kirletmemesi ve projeler arası sürüm çakışması olmaması için **sanal ortamlar (venv)** kullanılır. Konsolunuzun sol başında `(venv)` ibaresini görüyorsanız, sanal ortam içerisindesiniz demektir.

### Venv İçinde `pip` Nasıl Çalışır ve Paketler Nereye İner?
Sanal ortam aktifken çalıştırdığınız `pip install pytest` veya `pip install opencv-python` gibi komutlar, kütüphaneleri bilgisayarınızın global sistemine değil, doğrudan projenin içindeki `venv` klasörüne hapseder:
- **Kaynak kodlar ve Kütüphaneler:** `e:\Projeler\python_dnd\venv\Lib\site-packages\` dizinine indirilir ve kopyalanır.
- **Çalıştırılabilir komutlar (örn. `pytest.exe`):** `e:\Projeler\python_dnd\venv\Scripts\` dizinine yerleştirilir.

### Sanal Ortamdayken Neden "Komut Bulunamadı" Hatası Alınır?
Sanal ortam aktifken normalde `pytest` yazdığınızda sistemin `venv\Scripts\pytest.exe` dosyasını bulup çalıştırması beklenir. Ancak PowerShell'in önbellek (cache) durumu, güvenlik politikaları (ExecutionPolicy) veya PATH değişkeninin o anlık oturuma tam entegre olamaması durumlarında sistem komutu bulamaz.

İşte tam bu yüzden `pytest` komutunu doğrudan çağırmak yerine **`python -m pytest`** komutunu kullanmak **teknik olarak her zaman en sağlam (bulletproof) yöntemdir.** Bu kullanım; işletim sisteminin komut çözücüsüne (PATH) güvenmek yerine, o an aktif olan Python yorumlayıcısına şu talimatı verir: *"Git, sanal ortamın içindeki site-packages klasöründe `pytest` modülünü bul ve bir script gibi çalıştır."*

### Venv İçinde Standart Test Çalıştırma Akışı:

1. **Sanal ortamı aktif edin:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
2. **Bağımlılıkları kurun:**
   ```powershell
   pip install pytest
   ```
   *(Bu işlem sadece `venv` klasörünün içini etkiler.)*
3. **Testleri modül modunda garantili şekilde çalıştırın:**
   ```powershell
   python -m pytest tests/
   ```
