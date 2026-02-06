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

# --- KÜTÜPHANE DÜZELTMESİ ---
import google.generativeai as genai

# API Yapılandırması
genai.configure(api_key="AIzaSyCZYpncHKYyMjQodmOome6uqi2d6R1iggY")

def ihale_dosyalarini_isle_ve_kaydet(ihale_obj, cetvel_dosya, sartname_dosya=None):
    try:
        # 1. Model Tanımı (Sade isim kullanımı 404 hatasını çözer)
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = """
        GÖREV: Ekli belgeleri analiz et. 
        SADECE şu JSON yapısını döndür (açıklama ekleme): 
        [{"urun_adi": "...", "miktar": 0, "birim": "...", "teknik_metin": "..."}]
        """

        icerik_listesi = [prompt]
        
        def dosya_hazirla(dosya):
            if not dosya: return None
            dosya.seek(0)
            # Dosya uzantısına göre MIME type belirleme
            ext = dosya.name.lower()
            if ext.endswith('.pdf'): m_type = 'application/pdf'
            elif ext.endswith(('.png', '.jpg', '.jpeg')): m_type = 'image/jpeg'
            else: m_type = 'application/pdf' # Varsayılan
            
            return {"mime_type": m_type, "data": dosya.read()}

        # Ana dosya (Cetvel)
        c_part = dosya_hazirla(cetvel_dosya)
        if c_part:
            icerik_listesi.append(c_part)
        
        # Seçmeli dosya (Şartname)
        if sartname_dosya:
            s_part = dosya_hazirla(sartname_dosya)
            if s_part:
                icerik_listesi.append(s_part)

        # 2. AI Çağrısı
        response = model.generate_content(icerik_listesi)
        
        if not response or not response.text:
            print("DEBUG: AI yanıt vermedi.")
            return False

        # 3. JSON Temizleme
        cevap = response.text.strip()
        # Markdown bloklarını temizle
        cevap = re.sub(r'```json\s?|```', '', cevap).strip()
        
        # JSON'u doğrula ve yükle
        try:
            veriler = json.loads(cevap)
        except json.JSONDecodeError:
            # Eğer AI başında/sonunda metin bıraktıysa sadece köşeli parantez arasını al
            match = re.search(r'\[.*\]', cevap, re.DOTALL)
            if match:
                veriler = json.loads(match.group())
            else:
                raise ValueError("JSON formatı bozuk.")

        # --- MASAÜSTÜNE EXCEL YAZMA ---
        try:
            # Senin sistemindeki tam yol
            tam_yol = r"C:\Users\Meysa\Desktop\AI_DENETIM_{}.xlsx".format(ihale_obj.id)
            
            df = pd.DataFrame(veriler)
            df.to_excel(tam_yol, index=False)
            print(f"!!! BAŞARILI: Veri masaüstüne kaydedildi: {tam_yol}")
        except Exception as e_path:
            print(f"DEBUG: Masaüstüne yazılamadı: {e_path}")

        # 4. Veritabanına Kayıt
        kayit_sayisi = 0
        for item in veriler:
            raw_m = str(item.get('miktar', '0')).replace(',', '.')
            # Sayısal olmayan karakterleri temizle
            temiz_m_str = re.sub(r'[^\d.]', '', raw_m)
            temiz_m = float(temiz_m_str) if temiz_m_str else 0
            
            Kalem.objects.create(
                ihale=ihale_obj,
                urun_adi=item.get('urun_adi', 'Bilinmeyen Ürün'),
                adet=temiz_m,
                birim=item.get('birim', 'Adet'),
                teknik_sartname_ozeti=item.get('teknik_metin', 'Detay yok')
            )
            kayit_sayisi += 1
            
        return kayit_sayisi

    except Exception as e:
        print(f"KRİTİK HATA: {str(e)}")
        return False

# --- DOSYA YÜKLEME ---
@login_required 
def dosya_yukleme(request):
    if request.method == 'POST' and request.FILES.get('dosya'):
        ihale_adi = request.POST.get('ihale_adi')
        kurum_adi = request.POST.get('kurum_adi')
        ikn_yil = request.POST.get('ikn_yil', '2025')
        ikn_no = request.POST.get('ikn_no', '000')
        ihale_no = f"{ikn_yil}/{ikn_no}"
        
        urun_listesi_dosyasi = request.FILES.get('dosya')
        sartname_dosyasi = request.FILES.get('teknik_sartname')

        hastane, _ = Hastane.objects.get_or_create(ad=kurum_adi)
        
        yeni_ihale = Ihale.objects.create(
            ihale_adi=ihale_adi, 
            hastane=hastane, 
            tarih=timezone.now(), 
            ihale_no=ihale_no, 
            is_dogrudan_temin=(request.POST.get('kategori') == 'dogrudan'),
            olusturan_kullanici=request.user
        )

        sonuc = ihale_dosyalarini_isle_ve_kaydet(yeni_ihale, urun_listesi_dosyasi, sartname_dosyasi)

        if sonuc:
            messages.success(request, f"İşlem tamam. {sonuc} kalem eklendi.")
        else:
            messages.error(request, "AI bağlantı hatası! Terminale bakınız.")

        return redirect('ihale_listesi')

    return render(request, 'ihaleler/dosya_yukleme.html')