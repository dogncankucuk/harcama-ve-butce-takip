# Harcama & Bütçe Takip

Python ve PySide6 (Qt) ile geliştirilmiş masaüstü kişisel finans / bütçe
takip uygulaması. Gelir (`gelir`) ve gider (`gider`) işlemlerini kaydedin,
filtreleyip arayın, aylık bütçe limiti belirleyip aşım uyarısı alın ve
harcamalarınızı gömülü matplotlib grafikleriyle görüntüleyin. Veriler,
ilk çalıştırmada `main.py` ile aynı klasörde otomatik oluşturulan yerel bir
SQLite veritabanında (`harcama.db`) saklanır.

## Teknoloji yığını

- Python 3.14
- [PySide6](https://doc.qt.io/qtforpython/) 6.11.1 — Qt arayüzü
- [matplotlib](https://matplotlib.org/) 3.11.0 — gömülü grafikler (`backend_qtagg`)
- SQLite, stdlib `sqlite3` modülü üzerinden — ORM kullanılmıyor
- [pytest](https://docs.pytest.org/) — test paketi

## Kurulum

```bash
pip install -r requirements.txt
```

## Uygulamayı çalıştırma

```bash
python main.py
```

Bu komut proje klasöründe `harcama.db` dosyasını açar (yoksa oluşturur) ve
ana pencereyi başlatır.

## Testleri çalıştırma

```bash
pytest tests/ -v
```

30 test; CRUD işlemlerini, sıkı tarih doğrulamasını, bütçe sınır mantığını,
karışık gelir/gider toplamalarını, filtrelemeyi ve CSV round-trip/atomiklik
davranışını kapsar.

## Özellikler

- İşlem ekleme, düzenleme ve silme (tutar, kategori, tarih, not, tür).
- İşlem türü: `gelir` (income) veya `gider` (expense).
- Kategori, tarih aralığı, serbest metin not araması ve türe göre
  filtreleme/arama.
- Aylık bütçe limiti belirleme; mevcut ayın harcamasını bütçeyle
  karşılaştırıp aşım uyarısı gösterme, ayrıca ayın net bakiyesi
  (gelir − gider).
- Grafikler (matplotlib, Qt penceresine gömülü):
  - Mevcut ayın kategoriye göre gider dağılımı (çubuk grafik).
  - Zaman içinde aylık toplamlar, gelir ve gider ayrı iki seri olarak
    (çizgi grafik).
- CSV dışa ve içe aktarma. İçe aktarma hep-ya-da-hiç mantığıyla çalışır:
  herhangi bir satır doğrulamadan geçmezse, o dosyadan hiçbir şey
  kaydedilmez.

### Kapsam dışı (bilinçli olarak)

Tekrarlayan işlemler, çoklu hesap ve tasarruf hedefleri desteklenmiyor —
bunlar bu projenin kapsamından açıkça hariç tutulmuştur.

## Veri saklama notları

- Tutarlar, kayan nokta yuvarlama sapmalarını önlemek için pozitif tam
  sayı olarak küçük birimde (kuruş = TL × 100) saklanır; işaret (artı/eksi)
  `type` alanıyla ifade edilir.
- Tarihler, sözlük sırasının kronolojik sırayla eşleşmesi ve
  `strftime('%Y-%m', date)` gruplamasının doğru çalışması için sıkı
  ISO-8601 metin biçiminde (`YYYY-MM-DD`) saklanır. Diğer ISO tarih
  varyantları (ör. `20260701`, hafta tarihi biçimi) ekleme/güncelleme
  sırasında reddedilir.
