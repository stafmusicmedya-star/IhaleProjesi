# İhale Projesi – API Anahtarları Rehberi

Dosya yükleme ekranında **teklif cetveli** ve **teknik şartname** yüklediğinizde sistem, kalemleri (ürün/hizmet satırları) otomatik çıkarmak için bir **yapay zeka (AI) servisi** kullanır. Bunun çalışması için **en az bir** aşağıdaki API anahtarının projede tanımlı olması gerekir.

---

## Hangi API'ler kullanılıyor?

| API | Ne işe yarıyor? | Zorunlu mu? |
|-----|------------------|-------------|
| **OpenAI** (GPT) | Ana yöntem: PDF/Excel'den cetvel + teknik şartname eşleştirmesi | Hayır (ama en gelişmiş sonuç için tercih edilir) |
| **Anthropic** (Claude) | OpenAI yerine kullanılabilir; aynı işi yapar | Hayır |
| **Google Gemini** | Yedek yöntem: API key yoksa veya pipeline hata verirse otomatik denenir | **En az biri gerekli** (OpenAI, Anthropic veya Gemini) |

**Pratik öneri:** Hızlı test için sadece **Gemini** anahtarı eklemeniz yeterli. Daha sonra isterseniz OpenAI veya Anthropic ekleyebilirsiniz.

---

## 1. Google Gemini (en kolay – ücretsiz kota)

### 1.1 Anahtar nereden alınır?

1. Tarayıcıda şu adresi açın: **https://aistudio.google.com/apikey**
2. Google hesabınızla giriş yapın.
3. **"Create API Key"** (API Anahtarı Oluştur) butonuna tıklayın.
4. Bir proje seçin veya **"Create API key in new project"** ile yeni proje oluşturun.
5. Oluşturulan anahtar kopyalanır (örn. `AIzaSy...` ile başlar). Bu anahtarı bir yere not edin.

### 1.2 Projeye nasıl eklenir?

1. Projenizin **ana klasörünü** açın (içinde `manage.py` ve `ihale_sistemi` klasörü olan yer).  
   Örnek: `D:\IhaleProjesi`
2. Bu klasörde **`.env`** adında bir dosya oluşturun (başında nokta var, uzantısı yok).
3. `.env` dosyasının içine şu satırı ekleyin (kendi anahtarınızı yapıştırın):

```env
GEMINI_API_KEY=AIzaSyBurayaKendiAnahtariniziYapistirin
```

**İsteğe bağlı – model adı:** Bazen API "model bulunamadı" (404) hatası verir. O zaman `.env` dosyasına şunu ekleyin (sırayla denenir: 2.5-flash → 2.0-flash → 2.5-flash-lite):

```env
GEMINI_MODEL=gemini-2.0-flash
```

4. Kaydedin. Sunucuyu yeniden başlatmanız gerekmez; bir sonraki dosya yüklemesinde kullanılır.

---

## 2. OpenAI (GPT – cetvel + şartname eşleştirme)

### 2.1 Anahtar nereden alınır?

1. **https://platform.openai.com/** adresine gidin.
2. Giriş yapın veya hesap oluşturun.
3. Sağ üstten **profil ikonu** → **"View API keys"** (API anahtarlarını görüntüle).
4. **"Create new secret key"** ile yeni anahtar oluşturun.
5. Anahtar bir kez gösterilir; kopyalayıp güvenli bir yere kaydedin (örn. `sk-...` ile başlar).

**Not:** Ücretli kullanımdır; kredi kartı tanımlanır. Küçük kullanımda birkaç dolar yeterli olabilir.

### 2.2 Projeye nasıl eklenir?

`.env` dosyasına ekleyin:

```env
OPENAI_API_KEY=sk-BurayaKendiOpenAIAnahtariniziYapistirin
```

---

## 3. Anthropic (Claude – OpenAI alternatifi)

### 3.1 Anahtar nereden alınır?

1. **https://console.anthropic.com/** adresine gidin.
2. Hesap oluşturun / giriş yapın.
3. **"API Keys"** bölümüne gidin.
4. Yeni anahtar oluşturup kopyalayın.

### 3.2 Projeye nasıl eklenir?

`.env` dosyasına ekleyin:

```env
ANTHROPIC_API_KEY=sk-ant-BurayaKendiAnthropicAnahtariniziYapistirin
```

**Not:** Pipeline varsayılan olarak OpenAI kullanır. Sadece Anthropic kullanmak isterseniz kodda `provider="anthropic"` kullanılması gerekir (geliştirici gerekirse bunu ekleyebilir).

---

## 4. .env dosyası nerede ve nasıl olmalı?

### Konum

- Proje kökü = `manage.py` dosyasının bulunduğu klasör.  
  Örnek: `D:\IhaleProjesi`
- `.env` dosyası **tam bu klasörde** olmalı:  
  `D:\IhaleProjesi\.env`

### Örnek .env (hepsini eklemek zorunda değilsiniz)

```env
# En az birini doldurun (Gemini en kolay başlangıç için)
GEMINI_API_KEY=AIzaSy...

# İsteğe bağlı – daha gelişmiş cetvel + şartname eşleştirme
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Django (isteğe bağlı)
SECRET_KEY=rastgele-uzun-bir-metin
```

### Dikkat

- Satır başında ve sonunda **boşluk bırakmayın** (örn. `GEMINI_API_KEY = ...` yerine `GEMINI_API_KEY=...`).
- Değerin etrafına **tırnak koymayın** (`.env` için gerekmez).
- `.env` dosyasını **asla** Git'e veya başkalarıyla paylaşmayın; içinde gizli anahtarlar vardır.

---

## 5. Projeyi test etme adımları

1. **.env** dosyasını oluşturup en az **GEMINI_API_KEY** ekleyin (yukarıdaki 1. bölüme göre).
2. Sunucuyu çalıştırın:  
   `python manage.py runserver`
3. Tarayıcıda **Dosya Yükleme** sayfasına gidin:  
   `http://127.0.0.1:8000/dosya-yukleme/`
4. **Birim Fiyat Cetveli** (PDF veya Excel) ve **Teknik Şartname** (PDF) yükleyin.
5. Formu gönderin.  
   - Başarılı olursa: "İşlem tamam (Gemini ile). X kalem eklendi." benzeri mesaj görürsünüz.  
   - Admin'de **İhale Kalemleri** sayfasında kalemler listelenir.

Hata alırsanız mesajda "API anahtarı" geçiyorsa `.env` dosyasının konumunu ve anahtarın doğru yazıldığını kontrol edin; gerekirse **API_REHBERI.md** (bu dosya) ile adımları tekrar uygulayın.
