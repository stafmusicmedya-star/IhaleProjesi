import os
import json
import re
import pandas as pd
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.contrib.auth.models import User
from django.http import HttpResponse

# Modellerin
from .models import Ihale, Kalem, Hastane, Mesai, Arac, AracKullanimKaydi, UrunKutuphanesi

# --- AI YAPILANDIRMASI ---
import google.generativeai as genai

# API Anahtarın
genai.configure(api_key="AIzaSyCZYpncHKYyMjQodmOome6uqi2d6R1iggY")

def ihale_dosyalarini_isle_ve_kaydet(ihale_obj, cetvel_dosya, sartname_dosya=None):
    try:
        # Gemini 1.5 Flash modeli multimodal (görsel+metin) desteği sunar
        model = genai.GenerativeModel('gemini-1.5-flash')

        # AI Talimatı: Sütun ismi bağımsız, görsel algılama odaklı
        prompt = """
        GÖREV: Ekli belgeleri (Excel, PDF veya Resim) bir insan gibi görsel olarak analiz et.
        1. Belgedeki tabloyu bul. Sütun başlıkları ne olursa olsun (örn: 'Malzemenin Cinsi', 'Ürün', 'Açıklama'); 
           hangi sütunun ürün adı, hangisinin miktar ve birim olduğunu konumundan anla.
        2. Teknik şartname belgesi varsa, oradaki maddeleri ürün adlarıyla eşleştir.
        3. Sonucu SADECE ve SADECE şu JSON yapısında döndür (kod bloğu kullanma):
        [{"urun_adi": "...", "miktar": 0, "birim": "...", "teknik_metin": "..."}]
        """

        icerik_listesi = [prompt]
        
        def dosya_hazirla(dosya):
            if not dosya: return None
            try:
                dosya.seek(0)
                data = dosya.read()
                dosya.seek(0)
                
                ext = dosya.name.lower()
                # MIME Type belirleme
                if ext.endswith('.pdf'): m_type = "application/pdf"
                elif ext.endswith(('.png', '.jpg', '.jpeg')): m_type = "image/jpeg"
                elif ext.endswith(('.xls', '.xlsx')): m_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else: m_type = "application/octet-stream"
                
                return {"mime_type": m_type, "data": data}
            except Exception as e:
                print(f"Dosya hazırlama hatası: {e}")
                return None

        # Cetvel (Birim Fiyat Cetveli) ekle
        c_part = dosya_hazirla(cetvel_dosya)
        if c_part: icerik_listesi.append(c_part)
        
        # Şartname (varsa) ekle
        s_part = dosya_hazirla(sartname_dosya)
        if s_part: icerik_listesi.append(s_part)

        # AI Çağrısı
        response = model.generate_content(icerik_listesi)

        if not response or not response.text:
            return False

        # JSON Temizleme (Markdown işaretlerini kaldırır)
        clean_text = response.text.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        try:
            veriler = json.loads(clean_text)
        except json.JSONDecodeError:
            # Bazen AI listeyi [] içine almayabiliyor, manuel kontrol
            if not clean_text.startswith('['):
                clean_text = '[' + clean_text + ']'
            veriler = json.loads(clean_text)

        # --- VERİTABANINA KAYIT ---
        kayit_sayisi = 0
        for item in veriler:
            try:
                # Miktar temizleme (nokta/virgül karmaşası için)
                raw_m = str(item.get('miktar', '0')).replace(',', '.')
                temiz_miktar = float(re.sub(r'[^\d.]', '', raw_m))
            except:
                temiz_miktar = 0

            Kalem.objects.create(
                ihale=ihale_obj,
                urun_adi=item.get('urun_adi', 'Bilinmeyen Ürün'),
                adet=temiz_miktar,
                birim=item.get('birim', 'Adet'),
                teknik_sartname_ozeti=item.get('teknik_metin', 'Detay bulunamadı.')
            )
            kayit_sayisi += 1
            
        return kayit_sayisi

    except Exception as e:
        print(f"AI Analiz Hatası: {str(e)}")
        return False

# --- DOSYA YÜKLEME ---
@login_required 
def dosya_yukleme(request):
    if request.method == 'POST' and request.FILES.get('dosya'):
        ihale_adi = request.POST.get('ihale_adi')
        kurum_adi = request.POST.get('kurum_adi')
        tarih_raw = request.POST.get('tarih')
        ikn_yil = request.POST.get('ikn_yil', '2025')
        ikn_no = request.POST.get('ikn_no', '000')
        ihale_no = f"{ikn_yil}/{ikn_no}"
        tur = request.POST.get('tur', 'Diger')
        kategori_secim = request.POST.get('kategori')
        il = request.POST.get('il', 'Istanbul')
        
        urun_listesi_dosyasi = request.FILES.get('dosya')
        sartname_dosyasi = request.FILES.get('teknik_sartname')

        try:
            if tarih_raw:
                t_obj = datetime.strptime(tarih_raw, '%Y-%m-%d')
                tarih = timezone.make_aware(t_obj)
            else:
                tarih = timezone.now()
        except:
            tarih = timezone.now()

        dogrudan_mi = (kategori_secim == 'dogrudan')
        hastane, _ = Hastane.objects.get_or_create(ad=kurum_adi)
        
        # İhale Kaydı
        yeni_ihale = Ihale.objects.create(
            ihale_adi=ihale_adi, 
            hastane=hastane, 
            tarih=tarih, 
            ihale_no=ihale_no, 
            tur=tur, 
            is_dogrudan_temin=dogrudan_mi, 
            il=il,
            cetvel_dosya=urun_listesi_dosyasi,
            sartname_dosya=sartname_dosyasi,
            olusturan_kullanici=request.user
        )

        # AI Analizini Başlat
        sonuc_sayisi = ihale_dosyalarini_isle_ve_kaydet(yeni_ihale, urun_listesi_dosyasi, sartname_dosyasi)

        if sonuc_sayisi:
            messages.success(request, f"Başarılı! {sonuc_sayisi} adet kalem belgeden okunarak sisteme eklendi.")
        else:
            messages.error(request, "Dosya yüklendi fakat AI tabloyu okuyamadı. Lütfen belgenin net olduğundan emin olun.")

        return redirect('dogrudan_temin' if dogrudan_mi else 'ihale_listesi')

    return render(request, 'ihaleler/dosya_yukleme.html')

# --- DİĞER FONKSİYONLAR (DEĞİŞMEDİ) ---
@login_required
def arabalar_view(request):
    if request.method == 'POST':
        if 'arac_ekle' in request.POST:
            plaka = request.POST.get('plaka')
            marka = request.POST.get('marka')
            personel_id = request.POST.get('personel')
            Arac.objects.create(plaka=plaka, marka_model=marka, zimmetli_personel_id=personel_id if personel_id else None)
            messages.success(request, f"{plaka} plakalı araç eklendi.")
        elif 'arac_sil' in request.POST:
            Arac.objects.filter(id=request.POST.get('arac_id')).delete()
            messages.warning(request, "Araç silindi.")
        elif 'arac_al' in request.POST:
            arac_obj = get_object_or_404(Arac, id=request.POST.get('arac_id'))
            if not AracKullanimKaydi.objects.filter(arac=arac_obj, teslim_tarihi__isnull=True).exists():
                AracKullanimKaydi.objects.create(
                    arac=arac_obj, 
                    personel_id=request.POST.get('personel_id') or request.user.id,
                    ihale_id=request.POST.get('ihale_id') or None, 
                    baslangic_km=request.POST.get('baslangic_km') or 0,
                    alis_tarihi=timezone.now()
                )
                messages.success(request, f"{arac_obj.plaka} kullanıma alındı.")
            else:
                messages.error(request, "Bu araç zaten kullanımda!")
        elif 'arac_teslim' in request.POST:
            arac_obj = get_object_or_404(Arac, id=request.POST.get('arac_id'))
            hareket = AracKullanimKaydi.objects.filter(arac=arac_obj, teslim_tarihi__isnull=True).first()
            if hareket:
                hareket.teslim_tarihi = timezone.now()
                hareket.bitis_km = request.POST.get('bitis_km')
                hareket.teslim_notu = request.POST.get('teslim_notu')
                if request.FILES.get('teslim_gorseli'): hareket.teslim_gorseli = request.FILES.get('teslim_gorseli')
                hareket.save()
                messages.info(request, f"{arac_obj.plaka} teslim edildi.")
        return redirect('arabalar_sayfasi')

    query = request.GET.get('q')
    durum_filtresi = request.GET.get('durum')
    araclar = Arac.objects.all().select_related('zimmetli_personel')
    if query: araclar = araclar.filter(Q(plaka__icontains=query) | Q(marka_model__icontains=query))
    if durum_filtresi == 'kullanimda': araclar = araclar.filter(kullanim_gecmisi__teslim_tarihi__isnull=True).distinct()
    elif durum_filtresi == 'musait': araclar = araclar.exclude(kullanim_gecmisi__teslim_tarihi__isnull=True).distinct()
    for a in araclar: a.su_an_kullanimda = a.kullanim_gecmisi.filter(teslim_tarihi__isnull=True).first()
    
    context = {'araclar': araclar, 'personeller': User.objects.all(), 'ihaleler': Ihale.objects.all().order_by('-id'), 'gecmis_hareketler': AracKullanimKaydi.objects.filter(teslim_tarihi__isnull=False).order_by('-teslim_tarihi')}
    return render(request, 'ihaleler/arabalar.html', context)

@login_required
def mesailerim_view(request):
    if request.method == 'POST':
        Mesai.objects.create(
            kullanici=request.user,
            ihale_id=request.POST.get('ihale_secimi') or None,
            tarih=request.POST.get('mesai_tarih'),
            baslangic_saati=request.POST.get('saat_baslangic') or None,
            bitis_saati=request.POST.get('saat_bitis') or None,
            aciklama=request.POST.get('aciklama'),
            dosya=request.FILES.get('medya')
        )
        messages.success(request, "Mesai kaydınız alındı.")
        return redirect('mesailerim_sayfasi')
    return render(request, 'ihaleler/mesailerim.html', {
        'ihaleler': Ihale.objects.all().order_by('-id'),
        'gecmis_mesailer': Mesai.objects.filter(kullanici=request.user).order_by('-tarih', '-olusturulma_tarihi')
    })

def anasayfa(request):
    context = {
        'toplam_ihale': Ihale.objects.filter(is_dogrudan_temin=False).count(),
        'toplam_dogrudan': Ihale.objects.filter(is_dogrudan_temin=True).count(),
        'aktif_kurum_sayisi': Hastane.objects.count(),
        'en_aktif_hastaneler': Hastane.objects.annotate(num_ihale=Count('ihale')).order_by('-num_ihale')[:5]
    }
    return render(request, 'ihaleler/index.html', context)

def ihale_listesi(request):
    ihaleler = Ihale.objects.filter(is_dogrudan_temin=False)
    q = request.GET.get('q')
    if q: ihaleler = ihaleler.filter(Q(ihale_adi__icontains=q) | Q(hastane__ad__icontains=q) | Q(ihale_no__icontains=q))
    return render(request, 'ihaleler/ihaleler.html', {'ihaleler': ihaleler.order_by('-id')})

def dogrudan_temin_listesi(request):
    ihaleler = Ihale.objects.filter(is_dogrudan_temin=True)
    q = request.GET.get('q')
    if q: ihaleler = ihaleler.filter(Q(ihale_adi__icontains=q) | Q(hastane__ad__icontains=q) | Q(ihale_no__icontains=q))
    return render(request, 'ihaleler/dogrudan_temin.html', {'ihaleler': ihaleler.order_by('-id')})

@login_required
def toplu_fiyat_guncelle(request):
    if request.method == "POST":
        fiyatlar = request.POST.getlist('fiyat[]')
        kalem_idleri = request.POST.getlist('kalem_id[]')
        for k_id, f in zip(kalem_idleri, fiyatlar):
            if f:
                try:
                    kalem = get_object_or_404(Kalem, id=k_id)
                    kalem.birim_fiyat = float(f.replace(',', '.'))
                    kalem.toplam_fiyat = kalem.birim_fiyat * float(kalem.adet or 0)
                    kalem.save()
                except: continue
        messages.info(request, "Fiyatlar güncellendi.")
    return redirect(request.META.get('HTTP_REFERER', 'ihale_listesi'))

@login_required
def ihale_sil(request, pk):
    ihale = get_object_or_404(Ihale, pk=pk)
    dm = ihale.is_dogrudan_temin
    ihale.delete()
    messages.warning(request, "Silindi.")
    return redirect('dogrudan_temin' if dm else 'ihale_listesi')

@login_required
def ihale_excel_indir(request):
    ihaleler = Ihale.objects.all().select_related('hastane')
    df = pd.DataFrame([{
        'İhale No': i.ihale_no, 'İhale Adı': i.ihale_adi, 'Kurum': i.hastane.ad if i.hastane else '-',
        'Tarih': i.tarih.strftime('%d.%m.%Y') if i.tarih else '-', 'Kategori': 'Doğrudan' if i.is_dogrudan_temin else 'İhale'
    } for i in ihaleler])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="meysa_ihale_listesi.xlsx"'
    df.to_excel(response, index=False)
    return response

@login_required
def profilim(request):
    ki = Ihale.objects.filter(olusturan_kullanici=request.user).order_by('-id')
    return render(request, 'ihaleler/profilim.html', {
        'user': request.user, 'ihaleler': ki, 'ihale_sayisi': ki.filter(is_dogrudan_temin=False).count(),
        'dogrudan_sayisi': ki.filter(is_dogrudan_temin=True).count(),
        'zimmetli_arac': Arac.objects.filter(zimmetli_personel=request.user).first(),
        'mesailer': Mesai.objects.filter(kullanici=request.user).order_by('-tarih')[:5]
    })

@login_required
def analiz_sayfasi(request):
    return render(request, 'ihaleler/analiz.html', {
        'hastane_verileri': Hastane.objects.annotate(toplam=Count('ihale')).order_by('-toplam'),
        'en_cok_alinanlar': Kalem.objects.values('urun_adi').annotate(adet_sum=Sum('adet')).order_by('-adet_sum')[:10]
    })