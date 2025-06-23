# MSP430 Assembler & Linker GUI

Bu proje, MSP430 mimarisi için bir Assembly derleyicisi ve bağlayıcısı (assembler & linker) ile entegre edilmiş bir grafik kullanıcı arayüzü (GUI) sunar. Python ve Tkinter kütüphanesi kullanılarak geliştirilmiştir.

![1](https://github.com/user-attachments/assets/4de5f12e-d52d-4f7c-94ba-584d6edbca38)


## Özellikler

- **MSP430Assembler**: Assembly kodunu analiz eder, semboller, sectionlar, export/import ve relocation işlemlerini yönetir; makine kodu üretir.
- **LinkEditor**: Birden fazla `.obj` dosyasını birleştirir, relocation işlemlerini yapar ve çalıştırılabilir dosya oluşturur.
- **MSP430AssemblerUI**: Kod yazma, makine koduna çevirme, `.obj` üretme ve linkleme işlevlerini sunan Tkinter arayüzü.
- **LineNumberedText**: Satır numaralı ve sözdizimi renklendirmeli metin editörü.

---

## 📦 Kurulum

### Sistem Gereksinimleri

- Python 3.7+
- Tkinter (çoğu Python dağıtımı ile birlikte gelir)
- Windows, Linux veya MacOS

### Gerekli Kütüphaneler

> Sadece standart kütüphaneler: `tkinter`, `os`, `re`, vb. Ekstra modül gerekmez.

### Dosya Listesi

- `main.py`: Ana uygulama dosyası
- `README.md`: Bu belgeler
- `temp/`: Obj ve final obj dosyalarının oluşturulacağı klasör

### Çalıştırma

```bash
python --version
python main.py
```

Windows’ta: `main.py` dosyasına çift tıklayarak çalıştırabilirsiniz.

---

## 🧑‍💻 Kullanım

- Arayüz açıldığında örnek bir MSP430 Assembly kodu otomatik olarak yüklenir.
- Yeni kod yazabilir, dosyadan kod yükleyebilir veya mevcut kodu kaydedebilirsiniz.

### Arayüz Bileşenleri

- **Sol Panel**: Assembly kodu giriş alanı (satır numaralı, sözdizimi renklendirmeli)
- **Sağ Panel**: Makine kodu çıktısı
- **Alt Panel**: Semboller, export/import, section detayları
- **Butonlar**:
  - `Dosya Aç`, `Kaydet`, `Temizle`, `Kodu Çevir`, `Modülleri Link Et`

### Kod Dönüştürme

- `Kodu Çevir` butonuna tıklayın.
- PASS1: Semboller ve sectionlar analiz edilir.
- PASS2: Makine kodu üretilir.
- `temp/` klasöründe `.obj` dosyası oluşur.

### Obj Dosyası

- COFF benzeri yapı: `SECTION`, `EXPORTS`, `RELOCATIONS`
- Her `asm` dosyası için ayrı `.obj`

### Linkleme

- `Modülleri Link Et` ile `.obj` dosyaları birleştirilir.
- `temp/final.obj` adında çalıştırılabilir obj dosyası üretilir.

---

## 🧩 Assembly Dili Özellikleri

### Sözdizimi

- Label: `label:`
- Komutlar: `INSTRUCTION OPERAND1, OPERAND2`
- Direktifler: `.text`, `.data`, `.bss`, `.word`, `.byte`, `.space`, `.def`, `.ref`, `.org`, `.end`
- Yorum: `;` işareti ile

### Desteklenen Komutlar (Bazı Örnekler)

- **Veri**: `MOV`, `MOV.W`
- **Aritmetik**: `ADD`, `SUB`
- **Karşılaştırma**: `CMP`
- **Atlama**: `JMP`, `JEQ`, `JNE`
- **Fonksiyon**: `CALL`, `RET`
- **NOP**: `NOP`

---

## 📂 Dosya Formatları

### `.asm`

```asm
.def start
.text
start: MOV.W #0x1234, R4
       NOP
```

### `.obj`

- Otomatik oluşturulur
- COFF benzeri yapı

### `final.obj`

- Link sonrası oluşur
- Simülasyon için uygundur

---

## 🚀 Tipik Kullanım

1. Tek dosya: `Kodu Çevir` → `.obj`
2. Çoklu dosya: Her biri için `Kodu Çevir` → `Modülleri Link Et` → `final.obj`
3. Semboller ve sectionları alt panelde inceleyin

---

## 🛠️ Geliştirici Notları

- Ana dosya: `main.py`
- Temp klasörü: `temp/` (otomatik oluşur)
- Kod Türkçedir, yorum satırları detaylıdır

### Genişletme

- Daha fazla komut eklenebilir
- CLI, Intel HEX export gibi özellikler dahil edilebilir

---

## 🧯 Sorun Giderme

- **Tkinter hatası**: `sudo apt-get install python3-tk`
- **İzinler**: `temp/` yazılabilir olmalı
- **UTF-8 encoding** zorunlu
- **Hata**: Hata mesajını kontrol edin

---

## 📄 Lisans

Bu yazılım eğitim/akademik amaçlı geliştirilmiştir. Dilediğiniz gibi kullanabilir, değiştirebilir ve paylaşabilirsiniz.

---

## ❓ Sıkça Sorulan Sorular

**S: Programı başka bilgisayara nasıl taşırım?**  
C: `main.py` ve `README.md` dosyalarını taşımanız yeterlidir.  

**S: Kodumda kırmızı hata uyarısı neden çıkıyor?**  
C: Sözdizimi hatası olabilir.  

**S: `.obj` dosyalarını nasıl birleştiririm?**  
C: Her biri için `Kodu Çevir` → `Modülleri Link Et`.  

**S: Hangi dosyalar kaydediliyor?**  
C: Sadece siz `Kaydet` dediğinizde `.asm` + makine kodu kaydedilir. `.obj` dosyaları otomatik oluşur.

---

