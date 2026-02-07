import os
import json
import re
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

# --- GEMINI (Yedek kalem çıkarma) ---
try:
    import google.generativeai as genai
except ImportError:
    genai = None


def _gemini_api_key():
    try:
        from django.conf import settings
        key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")
        return (key or "").strip()
    except Exception:
        return (os.environ.get("GEMINI_API_KEY") or "").strip()


def ihale_dosyalarini_isle_ve_kaydet(ihale_obj, cetvel_dosya, sartname_dosya=None):
    """Gemini ile cetvel + şartname analiz edip Kalem kaydeder. Başarıda kalem sayısı, hata da (0, hata_mesajı) döner."""
    if genai is None:
        return (0, "Google Generative AI kütüphanesi yüklü değil. Pip ile yükleyin: pip install google-generativeai")
    api_key = _gemini_api_key()
    if not api_key:
        return (0, "GEMINI_API_KEY .env dosyasında tanımlı değil.")
    try:
        genai.configure(api_key=api_key)
        # Güncel model: gemini-1.5-flash-latest artık v1beta'da 404 veriyor. Sırayla dene.
        try:
            from django.conf import settings
            _model = (getattr(settings, "GEMINI_MODEL", None) or os.environ.get("GEMINI_MODEL") or "").strip()
        except Exception:
            _model = (os.environ.get("GEMINI_MODEL") or "").strip()
        # Kota aşıldığında daha düşük kotası olan modelleri de dene (flash-lite önce)
        model_names = [
            _model or "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
        ]

        prompt_base = """
GÖREV: Aşağıdaki belgeleri analiz et.

1) FİYAT CETVELİ: "BİRİM FİYAT TEKLİF CETVELİ" veya benzeri tabloda SADECE mal/hizmet satırlarını kalem olarak çıkar.
   - Tablo satırları TAB veya boşlukla ayrılmış olabilir. Sütunlar genelde: Sıra No, Mal Kaleminin Adı / Açıklaması, Birim, Miktar, (Birim Fiyat, Tutar).
   - Sadece sayı ile başlayan veri satırlarını al (1, 2, 3...). Başlık satırını ("Sıra No", "Mal Kaleminin Adı" vb.) ve alt bilgiyi ("Toplam Tutar", "İmza", "Kaşe" vb.) KALEM OLARAK EKLEME.
   - Her kalem için: urun_adi = mal/hizmet adı ve kısa açıklaması (tek hücrede birleşik), birim = Birimi sütunu (adet, takım, çift vb.), miktar = sayı. Birim fiyat/tutar hücreleri boş olsa bile satırı kalem olarak ekle.

2) TEKNİK ŞARTNAME: Her kalem için teknik şartnameden O KALEMLE İLİŞKİLİ bölümü BUL ve "teknik_metin" alanında GENİŞ VE AYRINTILI özet yaz.
   - Kısa tek cümle YETERLİ DEĞİL. Ürünün özellikleri, teknik şartlar, ölçüler, standartlar, malzeme bilgisi varsa hepsini 2-5 cümleyle özetle.
   - Kalem adıyla eşleşen veya sıra numarasıyla eşleşen şartname maddelerini o kalemin teknik_metin alanına yaz.

SADECE aşağıdaki JSON yapısını döndür (başka açıklama ekleme):
[{"urun_adi": "...", "miktar": 0, "birim": "...", "teknik_metin": "..."}]
"""
        cetvel_metin = None
        sartname_metin = None
        icerik_listesi = []

        def _uzanti(dosya):
            if not dosya or not getattr(dosya, 'name', None):
                return ""
            return (dosya.name or "").lower()

        def _binary_gonderilebilir(dosya):
            ext = _uzanti(dosya)
            return ext.endswith('.pdf') or ext.endswith(('.png', '.jpg', '.jpeg'))

        def dosya_hazirla(dosya):
            if not dosya:
                return None
            dosya.seek(0)
            ext = _uzanti(dosya)
            if ext.endswith('.pdf'):
                m_type = 'application/pdf'
            elif ext.endswith(('.png', '.jpg', '.jpeg')):
                m_type = 'image/jpeg'
            else:
                return None
            return {"inline_data": {"mime_type": m_type, "data": dosya.read()}}

        def dosyadan_metin_cek(dosya):
            if not dosya:
                return ""
            import tempfile
            ext = _uzanti(dosya)
            if not ext:
                return ""
            try:
                dosya.seek(0)
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    tmp.write(dosya.read())
                    tmp.flush()
                    path = tmp.name
                try:
                    from .utils.file_to_text import extract_text_from_file
                    return extract_text_from_file(path) or ""
                finally:
                    try:
                        os.unlink(path)
                    except Exception:
                        pass
            except Exception as e:
                return f"(Metin çıkarılamadı: {e})"

        # Cetvel: PDF/resim ise ekle, Excel/DOCX ise metin olarak prompt'a ekle
        if cetvel_dosya:
            if _binary_gonderilebilir(cetvel_dosya):
                c_part = dosya_hazirla(cetvel_dosya)
                if c_part:
                    icerik_listesi.append(c_part)
            else:
                cetvel_metin = dosyadan_metin_cek(cetvel_dosya)

        if sartname_dosya:
            if _binary_gonderilebilir(sartname_dosya):
                s_part = dosya_hazirla(sartname_dosya)
                if s_part:
                    icerik_listesi.append(s_part)
            else:
                sartname_metin = dosyadan_metin_cek(sartname_dosya)

        prompt = prompt_base
        if cetvel_metin:
            prompt += "\n\n--- FİYAT CETVELİ METNİ ---\n" + (cetvel_metin[:60000] or "(boş)")
        if sartname_metin:
            prompt += "\n\n--- TEKNİK ŞARTNAME METNİ ---\n" + (sartname_metin[:40000] or "(boş)")
        icerik_listesi.insert(0, prompt)

        # 2. AI Çağrısı — 404 (model bulunamadı) alınırsa yedek model dene
        response = None
        last_error = None
        for name in model_names:
            if not name:
                continue
            try:
                model = genai.GenerativeModel(name)
                response = model.generate_content(icerik_listesi)
                break
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                if "404" in err_str or "not found" in err_str or "not supported" in err_str:
                    continue
                if "quota" in err_str or "429" in err_str or "resource exhausted" in err_str or "kotası" in err_str:
                    continue
                raise
        if response is None:
            return (0, f"Kalem çıkarılamadı: Hiçbir Gemini modeli çalışmadı. Son hata: {last_error}")
        
        if not response:
            return (0, "Gemini yanıt döndürmedi.")
        if not response.text:
            # Güvenlik/engelleme veya boş yanıt
            msg = "Gemini metin üretmedi (belge engellenmiş veya boş yanıt olabilir)."
            if response.candidates:
                fc = response.candidates[0].finish_reason if hasattr(response.candidates[0], "finish_reason") else None
                if fc:
                    msg += f" Sebep: {fc}"
            return (0, msg)

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

        # 4. Veritabanına Kayıt
        kayit_sayisi = 0
        for item in veriler:
            raw_m = str(item.get('miktar', '0')).replace(',', '.')
            temiz_m_str = re.sub(r'[^\d.]', '', raw_m)
            temiz_m = float(temiz_m_str) if temiz_m_str else 0
            
            Kalem.objects.create(
                ihale=ihale_obj,
                urun_adi=(item.get('urun_adi') or 'Bilinmeyen Ürün')[:255],
                adet=temiz_m,
                birim=(item.get('birim') or 'Adet')[:50],
                teknik_sartname_ozeti=item.get('teknik_metin') or 'Detay yok'
            )
            kayit_sayisi += 1
            
        return kayit_sayisi

    except Exception as e:
        err = str(e)
        print(f"KRİTİK HATA: {err}")
        # Kullanıcıya anlamlı mesaj
        if "API_KEY" in err.upper() or "invalid" in err.lower() or "401" in err or "403" in err:
            return (0, "Geçersiz veya yetkisiz API anahtarı. https://aistudio.google.com/apikey adresinden yeni key alın.")
        if "quota" in err.lower() or "429" in err or "resource_exhausted" in err.lower():
            return (0, "Gemini kotası aşıldı. Daha sonra tekrar deneyin.")
        if "429" in err:
            return (0, "Çok fazla istek. Biraz bekleyip tekrar deneyin.")
        if "400" in err or "no pages" in err.lower() or "document has no pages" in err.lower():
            return (0, "Excel veya Word dosyası PDF gibi işlendi; sistem güncellendi. Lütfen sayfayı yenileyip dosyayı tekrar yükleyin.")
        return (0, err[:200])

# --- DOSYA YÜKLEME ---
@login_required 
def dosya_yukleme(request):
    if request.method == 'POST' and request.FILES.get('dosya'):
        ihale_adi = request.POST.get('ihale_adi')
        kurum_adi = request.POST.get('kurum_adi')
        ikn_yil = request.POST.get('ikn_yil', '2026')
        ikn_no = request.POST.get('ikn_no', '000')
        ihale_no = f"{ikn_yil}/{ikn_no}"
        tur = (request.POST.get('tur') or 'Mal').strip() or 'Mal'
        if tur == 'Yapim':
            tur = 'Yapım'
        il = (request.POST.get('il') or 'İstanbul').strip() or 'İstanbul'
        tarih_str = request.POST.get('tarih')
        tarih = timezone.now()
        if tarih_str:
            try:
                from datetime import datetime
                tarih = timezone.make_aware(datetime.strptime(tarih_str, '%Y-%m-%d'))
            except Exception:
                pass

        urun_listesi_dosyasi = request.FILES.get('dosya')
        sartname_dosyasi = request.FILES.get('teknik_sartname')

        hastane, _ = Hastane.objects.get_or_create(ad=kurum_adi)
        
        yeni_ihale = Ihale.objects.create(
            ihale_adi=ihale_adi,
            hastane=hastane,
            tarih=tarih,
            ihale_no=ihale_no,
            is_dogrudan_temin=(request.POST.get('kategori') == 'dogrudan'),
            tur=tur,
            il=il,
            olusturan_kullanici=request.user,
        )
        yeni_ihale.cetvel_dosya = urun_listesi_dosyasi
        if request.FILES.get('dosya_2'):
            yeni_ihale.cetvel_dosya_2 = request.FILES.get('dosya_2')
        if request.FILES.get('dosya_3'):
            yeni_ihale.cetvel_dosya_3 = request.FILES.get('dosya_3')
        if sartname_dosyasi:
            yeni_ihale.sartname_dosya = sartname_dosyasi
        if request.FILES.get('teknik_sartname_2'):
            yeni_ihale.sartname_dosya_2 = request.FILES.get('teknik_sartname_2')
        if request.FILES.get('teknik_sartname_3'):
            yeni_ihale.sartname_dosya_3 = request.FILES.get('teknik_sartname_3')
        yeni_ihale.save()

        # Gemini ile kalem çıkarma (ücretsiz kotaya uygun; OpenAI kullanılmıyor)
        if _gemini_api_key():
            sonuc = ihale_dosyalarini_isle_ve_kaydet(yeni_ihale, urun_listesi_dosyasi, sartname_dosyasi)
            if isinstance(sonuc, tuple):
                sayi, hata = sonuc
                if sayi and sayi > 0:
                    messages.success(request, f"İşlem tamam (Gemini). {sayi} kalem eklendi.")
                else:
                    messages.warning(request, f"Kalem çıkarılamadı: {hata}")
            elif sonuc and sonuc > 0:
                messages.success(request, f"İşlem tamam (Gemini). {sonuc} kalem eklendi.")
            else:
                messages.warning(request, "Kalem çıkarılamadı. .env dosyasında GEMINI_API_KEY doğru mu kontrol edin.")
        else:
            messages.warning(request, "Kalem çıkarılamadı: .env dosyasına GEMINI_API_KEY ekleyin (API_REHBERI.md).")

        from django.urls import reverse
        if yeni_ihale.is_dogrudan_temin:
            return redirect(reverse('dogrudan_temin_listesi'))
        return redirect(reverse('ihale_listesi'))

    return render(request, 'ihaleler/dosya_yukleme.html')