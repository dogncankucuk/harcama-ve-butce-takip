# Mimari

## Giriş noktası

`main.py`, `QApplication`'ı oluşturur, `db.connect()` üzerinden
`harcama.db`'yi (script ile aynı klasördeki SQLite dosyası) açar/oluşturur
ve `MainWindow`'u gösterir.

## Modül yapısı

```
main.py                    giriş noktası
models.py                  Transaction veri sınıfı (ortak veri şekli)
db.py                       SQLite şeması, doğrulama, CRUD, toplama
csv_io.py                  CSV dışa/içe aktarma (db.py üzerine kurulu)
ui/main_window.py          ana pencere: tablo, filtreler, bütçe paneli, grafikler
ui/transaction_dialog.py   ekleme/düzenleme işlem modalı
tests/                     pytest paketi (db, aggregation, csv_io)
```

Bağımlılıklar tek yönde akar: `ui/`, `db.py` ve `csv_io.py`'ye bağımlıdır;
`csv_io.py`, `db.py`'ye bağımlıdır; ikisi de `models.py`'ye bağımlıdır.
Arayüz SQLite ile asla doğrudan konuşmaz — tüm okuma/yazmalar `db.py`'nin
fonksiyonları üzerinden geçer, böylece doğrulama (tarih biçimi, pozitif
tutar, işlem türü) çağıran ne olursa olsun (arayüz, CSV içe aktarma veya
testler) tek bir yerde uygulanır.

## Veri katmanı (`db.py`)

Stdlib `sqlite3` üzerinden SQLite, ORM yok. İki tablo:

- `transactions(id, amount_minor, category, date, note, type)` — `type`
  alanı bir `CHECK` kısıtıyla `'gelir'` (income) veya `'gider'` (expense)
  ile sınırlıdır.
- `settings(key, value)` — şu anda aylık bütçe için tek bir satır tutuyor
  (`monthly_budget_minor`).

Önemli tasarım kararları:

- **Tutarlar**, toplamlarda kayan nokta yuvarlama sapmasını önlemek için
  pozitif tam sayı küçük birim (kuruş = TL × 100) olarak saklanır. İşaret,
  tutar tarafından değil `type` alanı tarafından belirlenir.
- **Tarihler**, sıkı `YYYY-MM-DD` metin biçiminde saklanır ve
  `date.fromisoformat`'a geçirilmeden önce bir regex ile doğrulanır —
  `fromisoformat` tek başına, `strftime('%Y-%m', date)` gruplamasını ve
  sözlük sıralı tarih aralığı filtrelemesini sessizce bozacak diğer
  ISO-8601 varyantlarını (ör. `20260701`, `2026-W27-3`) kabul eder. Bu
  doğrulama `tests/test_db.py` içinde doğrudan test edilir.
- **Toplama** (`category_totals_for_month`, `monthly_totals`,
  `monthly_net`, `get_month_spending`) Python'da değil, `strftime` ve
  `GROUP BY`/`SUM` ile SQL tarafında yapılır; arayüz sorgunun döndürdüğünü
  olduğu gibi gösterir.

## CSV içe/dışa aktarma (`csv_io.py`)

`transactions` tablosuyla aynı sütunları round-trip eder (görüntü metni
değil, küçük birim değerler — kayıpsız olması için). İçe aktarma
hep-ya-da-hiç mantığıyla çalışır: her satır `commit=False` ile eklenir;
herhangi bir satır doğrulamadan geçmezse tüm işlem geri alınır (rollback)
ve hata mesajı sorunlu satırı belirtir.

## Arayüz (`ui/`)

- `MainWindow` dört bölge oluşturur: bir filtre çubuğu
  (kategori/tür/tarih aralığı/not araması), bir işlem tablosu, bir bütçe
  paneli (bütçe belirleme, mevcut ayın harcaması vs. bütçe ve aşım
  uyarısı, net bakiye) ve bir grafik paneli.
- `TransactionDialog`, hem ekleme hem düzenleme için kullanılan modal bir
  `QDialog`'dur; çağıranlar sonucu `get_transaction()` ile okur.
- Grafikler, global `pyplot` durum API'si yerine açık bir `Figure` nesnesi
  kullanan `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg` ile gömülü
  matplotlib figürleridir; böylece birden fazla pencere/yeniden çizim
  global matplotlib durumunu sızdırmaz. Her yenilemede `ax.clear()`
  ardından `canvas.draw_idle()` çağrılır. İki grafik modu tek bir tuvali
  paylaşır: mevcut ayın kategoriye göre dağılımı (çubuk) ve zaman içinde
  aylık gelir/gider toplamları (çizgi, iki seri).

## Testler (`tests/`)

Pytest, izolasyon için bellek-içi SQLite (`db.connect(":memory:")`)
kullanır — hiçbir test gerçek `harcama.db`'ye dokunmaz. Konuya göre
ayrılmıştır: `test_db.py` (CRUD + doğrulama), `test_aggregation.py`
(gruplama/toplam doğruluğu, karışık gelir/gider dahil), `test_csv_io.py`
(dışa/içe aktarma round-trip ve hatalı satırda geri alma davranışı).
