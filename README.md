# 🎬 YouTube Downloader

[yt-dlp](https://github.com/yt-dlp/yt-dlp) tabanlı, Python ile yazılmış basit ama güçlü bir video indirici.
Tek video, playlist ya da yüzlerce linklik bir liste — ister masaüstü arayüzünden, ister terminalden indir.

![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)
![yt-dlp](https://img.shields.io/badge/powered%20by-yt--dlp-red)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)

---

## ✨ Özellikler

- **Üç farklı kullanım şekli:** koyu temalı masaüstü uygulaması, sade GUI ve komut satırı
- **Playlist çözme:** playlist linkini yapıştır, içindeki tüm videolar başlık ve süreleriyle listelensin
- **Seçerek indirme:** tek tek, seçilenleri ya da hepsini indir; her satırda ayrı ilerleme çubuğu
- **Kalite seçimi:** 4K, 1440p, 1080p, 720p, 480p, en iyi kalite ya da sadece ses (MP3 192k)
- **Tekrar indirmeyi önler:** indirilen videolar `~/.ytdl_archive.txt` arşivine yazılır, aynı video ikinci kez inmez
- **Dayanıklı indirme:** 10 tekrar deneme, parçalı (4 paralel) indirme, hatalı videoyu atlayıp devam etme
- **Liste dosyası desteği:** `.txt` dosyasından link yükle / listeyi kaydet (`#` ile başlayan satırlar yorum sayılır)
- **İşlem özeti:** iş bitince nelerin indiğini, nelerin inmediğini nedenleriyle gösterir

## 📦 Kurulum

```bash
git clone https://github.com/mustafasolak/youtube_downloader.git
cd youtube_downloader

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### ffmpeg (önerilir)

Video ile sesi birleştirmek (1080p ve üstü) ve MP3'e dönüştürmek için **ffmpeg** gerekir.

| Sistem  | Komut |
|---------|-------|
| macOS   | `brew install ffmpeg` |
| Ubuntu  | `sudo apt install ffmpeg` |
| Windows | `winget install ffmpeg` |

> ffmpeg yoksa uygulama yine açılır ama birleştirme/MP3 dönüşümü çalışmaz; arayüz bunu ayrıca uyarır.

> macOS'ta Homebrew Python kullanıyorsan Tkinter için `brew install python-tk` gerekebilir.

## 🚀 Kullanım

### 1. Toplu indirici uygulaması — `uygulama.py` (önerilen)

```bash
python uygulama.py
```

Koyu temalı, satır bazlı ilerleme gösteren ana uygulama:

1. Linkleri kutuya yapıştır (her satıra bir tane) ya da **Gözat / Yükle** ile bir `.txt` dosyası aç
2. **Listeyi çöz** → playlist'lerdeki tüm videolar başlık ve süreyle listelenir
3. Kaliteyi ve indirme klasörünü seç
4. **İndir** (tek video), **Seçilenleri indir** ya da **Tümünü indir**
5. İstersen **Durdur** ile sıradaki indirmeleri iptal et

Her satırın ilerleme çubuğu durumu renkle gösterir: 🔵 indiriliyor · 🟢 indi · 🔴 hata

### 2. Hızlı GUI / CLI — `ytdl.py`

```bash
# Arayüzü aç
python ytdl.py --gui

# Terminalden indir
python ytdl.py "https://www.youtube.com/watch?v=VIDEO_ID"

# 1080p, belirli bir klasöre
python ytdl.py -f 1080 -o ~/Videolar "https://youtu.be/VIDEO_ID"

# Sadece ses (MP3)
python ytdl.py -f audio "https://youtu.be/VIDEO_ID"

# Birden fazla link / playlist
python ytdl.py URL1 URL2 "https://www.youtube.com/playlist?list=..."
```

| Parametre | Açıklama | Varsayılan |
|-----------|----------|------------|
| `urls` | İndirilecek bir veya daha fazla link | — (verilmezse GUI açılır) |
| `-f`, `--format` | `best`, `2160`, `1440`, `1080`, `720`, `480`, `audio` | `best` |
| `-o`, `--out` | Çıktı klasörü | `indirilenler` |
| `--gui` | Arayüzü aç | — |

### 3. Listeden toplu indirme — `toplu.py`

```bash
python toplu.py liste.txt -f 720 -o ~/Downloads
```

Örnek `liste.txt`:

```text
# Ders videoları
https://www.youtube.com/playlist?list=PLxxxxxxxx
https://www.youtube.com/watch?v=xxxxxxxxxxx

# Müzikler
https://youtu.be/yyyyyyyyyyy
```

Daha önce inmiş videolar arşiv sayesinde atlanır; yarıda kalan bir listeyi aynı komutla kaldığın yerden sürdürebilirsin.

## 🗂 Proje yapısı

```
youtube_downloader/
├── ytdl.py          # Çekirdek: format tanımları, yt-dlp ayarları + basit GUI ve CLI
├── uygulama.py      # Koyu temalı toplu indirici (playlist çözme, satır bazlı ilerleme)
├── toplu.py         # .txt listesinden terminalde toplu indirme
└── requirements.txt
```

Dosya adları `Video Başlığı [VIDEO_ID].mp4` biçiminde kaydedilir; Windows'ta geçersiz karakterler otomatik temizlenir.

## 🛠 Sorun giderme

- **"Requested format is not available" / imza hataları:** YouTube sık değişir, yt-dlp'yi güncelle:
  `pip install -U yt-dlp`
- **Video ve ses ayrı dosyalar olarak indi:** ffmpeg kurulu değil.
- **Bir video "indi" görünüyor ama dosya yok:** daha önce indirilmiş ve arşive yazılmış olabilir. Tekrar indirmek için `~/.ytdl_archive.txt` içinden ilgili satırı sil.

## ⚖️ Yasal uyarı

Bu araç kişisel ve eğitim amaçlıdır. Yalnızca indirme hakkına sahip olduğun içerikleri indir;
YouTube Hizmet Şartları'na ve telif haklarına uymak kullanıcının sorumluluğundadır.
