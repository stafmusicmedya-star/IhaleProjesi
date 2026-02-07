from django.db import models
from django.contrib.auth.models import User

# --- KURUMSAL YAPI ---

class Hastane(models.Model):
    ad = models.CharField(max_length=255, verbose_name="Hastane/Kurum Adı")
    
    def __str__(self): 
        return self.ad
    
    class Meta:
        verbose_name = "Hastane"
        verbose_name_plural = "Hastaneler"

# --- İHALE VE DOSYA YÖNETİMİ ---

class Ihale(models.Model):
    DURUM_CHOICES = [
        ('Acik', 'Açık/Devam Ediyor'),
        ('Kazandik', 'Kazanıldı'),
        ('Kaybettik', 'Kaybedildi'),
        ('Tamamlandi', 'İş Tamamlandı/Teslim Edildi'),
        ('Iptal', 'İptal Edildi'),
    ]
    KAR_ZARAR_CHOICES = [
        ('Kar', 'Kâr'),
        ('Zarar', 'Zarar'),
        ('Basababas', 'Başabaş'),
        ('', 'Belirsiz'),
    ]

    ihale_adi = models.CharField(max_length=255, verbose_name="İhale Adı")
    ihale_no = models.CharField(max_length=50, verbose_name="İhale/İKN No")
    hastane = models.ForeignKey(Hastane, on_delete=models.CASCADE, verbose_name="İlgili Hastane")
    tarih = models.DateTimeField(verbose_name="İhale Tarihi")
    is_dogrudan_temin = models.BooleanField(default=False, verbose_name="Doğrudan Temin mi?")
    tur = models.CharField(max_length=50, default='Mal', verbose_name="İhale Türü") 
    il = models.CharField(max_length=50, default='İstanbul', verbose_name="Şehir")
    ilce = models.CharField(max_length=50, blank=True, null=True, verbose_name="İlçe")
    durum = models.CharField(max_length=20, choices=DURUM_CHOICES, default='Acik', verbose_name="Durum")
    
    # --- YENİ EKLENEN DOSYA ALANLARI ---
    cetvel_dosya = models.FileField(upload_to='ihaleler/cetveller/', null=True, blank=True, verbose_name="Birim Fiyat Cetveli 1")
    cetvel_dosya_2 = models.FileField(upload_to='ihaleler/cetveller/', null=True, blank=True, verbose_name="Birim Fiyat Cetveli 2")
    cetvel_dosya_3 = models.FileField(upload_to='ihaleler/cetveller/', null=True, blank=True, verbose_name="Birim Fiyat Cetveli 3")
    sartname_dosya = models.FileField(upload_to='ihaleler/sartnameler/', null=True, blank=True, verbose_name="Teknik Şartname 1")
    sartname_dosya_2 = models.FileField(upload_to='ihaleler/sartnameler/', null=True, blank=True, verbose_name="Teknik Şartname 2")
    sartname_dosya_3 = models.FileField(upload_to='ihaleler/sartnameler/', null=True, blank=True, verbose_name="Teknik Şartname 3")
    verilen_teklif_dosya = models.FileField(upload_to='ihaleler/teklifler/', null=True, blank=True, verbose_name="Verilen Teklif (ıslak imzalı çıktı)")
    
    # --- Analiz Sekmesi ve Finansal Veriler ---
    toplam_teklif_bedeli = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Toplam Teklif (KDV Hariç)")
    toplam_maliyet = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Toplam Gerçekleşen Maliyet")
    kar_orani = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Kâr Oranı (%)")
    odeme_alindi_mi = models.BooleanField(default=False, verbose_name="Devlet Ödemesi Alındı mı?")
    odeme_tarihi = models.DateField(null=True, blank=True, verbose_name="Ödemenin Alındığı Tarih")
    # --- Maliyet Analizi ---
    tahmini_maliyet = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Tahmini Maliyet")
    alinan_fiyat = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Alınan Fiyat (Toplam)")
    satis_fiyati = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Satış Fiyatı (Toplam)")
    kar_zarar_durumu = models.CharField(max_length=20, choices=KAR_ZARAR_CHOICES, blank=True, default='', verbose_name="Kâr/Zarar Durumu")

    # --- Sonuç Analizi (ihale sonuçlandığında) ---
    kazanan_firma = models.CharField(max_length=255, blank=True, null=True, verbose_name="İhaleyi Kim Kazandı?")
    kazanan_fiyat = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name="Kazanan Fiyat (TL)")
    bizim_teklif = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name="Bizim Teklifimiz (TL)")

    olusturan_kullanici = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kaydı Açan")
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)
    guncellenme_tarihi = models.DateTimeField(auto_now=True)

    def __str__(self): 
        return f"{self.ihale_no} - {self.ihale_adi}"

    class Meta:
        verbose_name = "İhale/Dosya"
        verbose_name_plural = "İhaleler ve Dosyalar"

# --- ÜRÜN VE TEKNİK VERİ BANKASI ---

class UrunKutuphanesi(models.Model):
    """Ürün Katalog: Benzersiz ürün; isim + teknik özellik ile eşleştirilir, geçmiş analizi bu ID üzerinden yapılır."""
    urun_adi = models.CharField(max_length=500, verbose_name="Ürün Adı")
    marka = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marka")
    teknik_sartname_metni = models.TextField(blank=True, null=True, verbose_name="Teknik Özellik Arşivi")
    teknik_ozellikler_json = models.JSONField(blank=True, null=True, default=dict, verbose_name="Teknik Özellikler (eşleştirme için)")
    gorsel = models.ImageField(upload_to='urun_arsivi/', null=True, blank=True, verbose_name="Ürün Görseli")
    son_alis_fiyati = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Son Alış Fiyatı (Mikro)")

    def __str__(self):
        return f"{self.marka} - {self.urun_adi}" if self.marka else self.urun_adi

    class Meta:
        verbose_name = "Ürün Kütüphanesi"
        verbose_name_plural = "Ürün Kütüphanesi"

class Kalem(models.Model):
    KAR_ZARAR_CHOICES = [
        ('Kar', 'Kâr'),
        ('Zarar', 'Zarar'),
        ('Basababas', 'Başabaş'),
        ('', 'Belirsiz'),
    ]
    ihale = models.ForeignKey(Ihale, related_name='kalemler', on_delete=models.CASCADE, verbose_name="Bağlı Olduğu İhale")
    urun_adi = models.CharField(max_length=255, verbose_name="Ürün/Kalem Adı")
    adet = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Miktar")
    birim = models.CharField(max_length=50, default='Adet', verbose_name="Birim")
    birim_fiyat = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Teklif Birim Fiyat")
    toplam_fiyat = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Toplam Teklif Fiyatı")
    maliyet_birim_fiyat = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Gerçek Alış Fiyatı")
    fatura_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="Mikro Fatura No")
    kalem_gorsel = models.ImageField(upload_to='kalem_gorseller/%Y/%m/', null=True, blank=True, verbose_name="Kalem Görseli")
    fatura_dosya = models.FileField(upload_to='kalem_faturalar/%Y/%m/', null=True, blank=True, verbose_name="Fatura (PDF/Resim)")
    teknik_sartname_ozeti = models.TextField(blank=True, null=True, verbose_name="Bu İhale İçin Teknik Şartname Özeti")
    teknik_ozellikler_json = models.JSONField(blank=True, null=True, default=dict, verbose_name="Teknik Özellikler (renk, ölçü, kesit vb.)")
    kutuphane_urunu = models.ForeignKey(UrunKutuphanesi, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kütüphane Eşleşmesi")
    # --- Maliyet Analizi ---
    tahmini_maliyet = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Tahmini Maliyet")
    alinan_fiyat = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Alınan Fiyat")
    satis_fiyati = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Satış Fiyatı")
    kar_zarar_durumu = models.CharField(max_length=20, choices=KAR_ZARAR_CHOICES, blank=True, default='', verbose_name="Kâr/Zarar Durumu")

    def __str__(self): 
        return f"{self.urun_adi} ({self.ihale.ihale_no})"

    class Meta:
        verbose_name = "İhale Kalemi"
        verbose_name_plural = "İhale Kalemleri"

# --- ARAÇ VE ARAÇ HAREKET MODELLERİ ---

class Arac(models.Model):
    plaka = models.CharField(max_length=20, unique=True, verbose_name="Plaka")
    marka_model = models.CharField(max_length=100, verbose_name="Marka ve Model")
    mevcut_km = models.PositiveIntegerField(default=0, verbose_name="Mevcut Kilometre")
    arac_foto = models.ImageField(upload_to='arac_foto/%Y/%m/', null=True, blank=True, verbose_name="Araç Fotoğrafı")
    zimmetli_personel = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='zimmetli_araclar',
        verbose_name="Zimmetli Personel"
    )
    durum = models.CharField(
        max_length=50, 
        default="Aktif", 
        choices=[('Aktif', 'Aktif'), ('Bakımda', 'Bakımda'), ('Arızalı', 'Arızalı')],
        verbose_name="Araç Durumu"
    )
    son_bakim_tarihi = models.DateField(null=True, blank=True, verbose_name="Son Bakım Tarihi")
    notlar = models.TextField(blank=True, null=True, verbose_name="Araç Notları")

    @property
    def su_an_kullanimda(self):
        return self.kullanim_gecmisi.filter(teslim_tarihi__isnull=True).first()

    def __str__(self):
        return f"{self.plaka} - {self.marka_model}"

    class Meta:
        verbose_name = "Araç"
        verbose_name_plural = "Araçlar"

class AracKullanimKaydi(models.Model):
    arac = models.ForeignKey(Arac, on_delete=models.CASCADE, related_name='kullanim_gecmisi', verbose_name="Araç")
    personel = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Teslim Alan Personel")
    ihale = models.ForeignKey(Ihale, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="İlgili İhale")
    baslangic_km = models.PositiveIntegerField(default=0, verbose_name="Başlangıç KM")
    bitis_km = models.PositiveIntegerField(null=True, blank=True, verbose_name="Bitiş KM")
    alis_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Alış Tarih/Saat")
    teslim_tarihi = models.DateTimeField(null=True, blank=True, verbose_name="Teslim Tarih/Saat")
    teslim_notu = models.TextField(blank=True, null=True, verbose_name="Teslimat/Durum Notu")
    teslim_gorseli = models.ImageField(upload_to='arac_teslimat/%Y/%m/%d/', null=True, blank=True, verbose_name="Teslimat Görseli (Opsiyonel)")

    def __str__(self):
        durum = "Teslim Edildi" if self.teslim_tarihi else "Kullanımda"
        return f"{self.arac.plaka} - {self.personel.username} ({durum})"

    class Meta:
        verbose_name = "Araç Kullanım Kaydı"
        verbose_name_plural = "Araç Kullanım Kayıtları"
        ordering = ['-alis_tarihi']

# --- MESAI VE BAKIM MODELI ---

class Mesai(models.Model):
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Personel")
    ihale = models.ForeignKey(Ihale, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Bağlı Dosya/İhale")
    arac = models.ForeignKey(Arac, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Kullanılan Araç")
    tarih = models.DateField(verbose_name="Mesai Tarihi")
    baslangic_saati = models.TimeField(null=True, blank=True, verbose_name="Başlangıç Saati")
    bitis_saati = models.TimeField(null=True, blank=True, verbose_name="Bitiş Saati")
    aciklama = models.TextField(verbose_name="Yapılan İş/Bakım Özeti")
    dosya = models.FileField(upload_to='mesai_dosyalari/%Y/%m/%d/', null=True, blank=True, verbose_name="İş Görseli/Video")
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kullanici.get_full_name() or self.kullanici.username} - {self.tarih}"

    class Meta:
        verbose_name = "Mesai/İş Kaydı"
        verbose_name_plural = "Mesai ve İş Kayıtları"
        ordering = ['-tarih', '-olusturulma_tarihi']