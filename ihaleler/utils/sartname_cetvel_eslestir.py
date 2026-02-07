"""
Teknik şartname metni ile teklif cetveli satırlarını 'insan gözü' mantığıyla eşleştirir:
cetveldeki kalem adına (örn. 'X marka kablo') şartnamede ilgili paragrafı bulur,
teknik özellikleri (kesit, voltaj vb.) ayıklar, cetvel verisiyle birleştirip
IhaleKalemi (Kalem) modeline kaydeder.

Kullanım (view veya management command içinde):
    from ihaleler.models import Ihale
    from ihaleler.utils.sartname_cetvel_eslestir import cetvel_ve_sartname_birlestir_ihale_kalem_kaydet

    ihale = Ihale.objects.get(pk=...)
    sonuc = cetvel_ve_sartname_birlestir_ihale_kalem_kaydet(
        ihale,
        provider="openai",
        mevcut_kalemleri_sil=True,
    )
    # sonuc["olusturulan"], sonuc["hatalar"], ...
"""
import json
import os
import re
from decimal import Decimal, InvalidOperation

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from ihaleler.utils.file_to_text import extract_text_from_file
from ihaleler.utils.document_vision import analiz_et_ve_tablo_dondur
from ihaleler.utils.parsing_service import extract_cetvel_layout_based


# -----------------------------------------------------------------------------
# LLM: Şartnameden kalem için paragraf bul + teknik özellik çıkar
# -----------------------------------------------------------------------------

_SARTNAME_ESLESTIRME_SYSTEM = """Sen bir teknik şartname analiz uzmanısın. Sana bir teknik şartname metni ve teklif cetvelinden bir kalem adı (ürün/hizmet) verilecek.
Görevin: İnsan gözüyle mantık kurarak şartnamede bu kalemi anlatan paragraf(lar)ı bulmak ve oradaki teknik özellikleri yapılandırılmış şekilde çıkarmak.
Özellikle şunları mutlaka ayıkla (varsa): renk, ölçü (boyut, en, boy, çap, kalınlık), kesit, voltaj, standart, marka, model, malzeme, birim.
Örnek: Cetvelde "X marka kablo" yazıyorsa, şartnamede kablo ile ilgili geçen bölümü bul; kesit, voltaj, standart, marka, model vb. ne varsa ayıkla.
Kalem adı tam eşleşmeyebilir (eşanlamlı, kısaltma, farklı yazım); anlamsal olarak aynı ürün/hizmeti anlatan kısmı bul.

Yanıtını SADECE aşağıdaki JSON formatında ver. Başka açıklama yazma.
{"ilgili_paragraf": "şartnameden ilgili bölümün metni (tek paragraf veya birkaç cümle)", "teknik_ozellikler": {"renk": "...", "olcu": "...", "kesit": "...", "voltaj": "...", "standart": "...", "marka": "...", "model": "...", ...}}
Örnek: {"ilgili_paragraf": "Kablo NYY 3x2,5 mm²...", "teknik_ozellikler": {"kesit": "2,5 mm²", "voltaj": "0,6/1 kV", "renk": "siyah", "standart": "TS EN"}}
Eğer şartnamede bu kalemle ilgili net bir bölüm bulamazsan ilgili_paragraf ve teknik_ozellikler boş bırakılabilir."""


def _get_api_keys():
    try:
        from django.conf import settings
        return {
            "openai": getattr(settings, "OPENAI_API_KEY", None) or os.environ.get("OPENAI_API_KEY"),
            "anthropic": getattr(settings, "ANTHROPIC_API_KEY", None) or os.environ.get("ANTHROPIC_API_KEY"),
        }
    except Exception:
        return {
            "openai": os.environ.get("OPENAI_API_KEY"),
            "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        }


def _call_openai_chat(system: str, user: str, api_key: str, max_tokens: int = 2048) -> str:
    if not OpenAI:
        raise RuntimeError("openai paketi yüklü değil")
    client = OpenAI(api_key=api_key)
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
    )
    return (r.choices[0].message.content or "").strip()


def _call_anthropic_chat(system: str, user: str, api_key: str, max_tokens: int = 2048) -> str:
    if not Anthropic:
        raise RuntimeError("anthropic paketi yüklü değil")
    client = Anthropic(api_key=api_key)
    r = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return (r.content[0].text if r.content else "").strip()


def _parse_sartname_llm_response(text: str) -> dict:
    """LLM yanıtından ilgili_paragraf ve teknik_ozellikler çıkarır."""
    out = {"ilgili_paragraf": "", "teknik_ozellikler": {}}
    text = text.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return out
    try:
        data = json.loads(match.group(0))
        out["ilgili_paragraf"] = (data.get("ilgili_paragraf") or "")[:8000]
        out["teknik_ozellikler"] = data.get("teknik_ozellikler") if isinstance(data.get("teknik_ozellikler"), dict) else {}
    except json.JSONDecodeError:
        pass
    return out


def sartname_metninden_kalem_ozetleri_cikar(
    sartname_metni: str,
    kalem_adi: str,
    provider: str = "openai",
    max_karakter: int = 120000,
) -> dict:
    """
    Şartname metninde bu kalem adına karşılık gelen paragrafı bulur ve teknik özellikleri çıkarır.

    Returns:
        {"ilgili_paragraf": "...", "teknik_ozellikler": {"kesit": "...", "voltaj": "...", ...}, "hata": None veya mesaj}
    """
    result = {"ilgili_paragraf": "", "teknik_ozellikler": {}, "hata": None}
    if not sartname_metni or not kalem_adi or not kalem_adi.strip():
        return result
    metin = sartname_metni[:max_karakter] if len(sartname_metni) > max_karakter else sartname_metni
    user = f"""Teknik şartname metni:\n\n{metin}\n\n---\n\nTeklif cetvelindeki kalem adı: "{kalem_adi.strip()}"\n\nBu kalem için şartnamede ilgili paragrafı bul ve teknik özellikleri JSON ile döndür."""

    keys = _get_api_keys()
    try:
        if provider == "openai":
            api_key = keys["openai"]
            if not api_key:
                result["hata"] = "OPENAI_API_KEY yok"
                return result
            raw = _call_openai_chat(_SARTNAME_ESLESTIRME_SYSTEM, user, api_key)
        elif provider == "anthropic":
            api_key = keys["anthropic"]
            if not api_key:
                result["hata"] = "ANTHROPIC_API_KEY yok"
                return result
            raw = _call_anthropic_chat(_SARTNAME_ESLESTIRME_SYSTEM, user, api_key)
        else:
            result["hata"] = f"Bilinmeyen provider: {provider}"
            return result
        parsed = _parse_sartname_llm_response(raw)
        result["ilgili_paragraf"] = parsed["ilgili_paragraf"]
        result["teknik_ozellikler"] = parsed["teknik_ozellikler"]
    except Exception as e:
        result["hata"] = str(e)
    return result


# -----------------------------------------------------------------------------
# Sayı / para formatı (Türkçe: 1.500,50)
# -----------------------------------------------------------------------------

def _decimal_parse(value, default=Decimal("0")) -> Decimal:
    """Metin veya sayıyı Decimal'e çevirir. 1.500,50 veya 1500.50 kabul eder."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return default
    s = str(value).strip().replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return default


def _teknik_ozet_metin(ilgili_paragraf: str, teknik_ozellikler: dict) -> str:
    """Birleştirilmiş teknik şartname özeti metni."""
    parts = []
    if ilgili_paragraf:
        parts.append(ilgili_paragraf[:4000])
    if teknik_ozellikler:
        ozet = "; ".join(f"{k}: {v}" for k, v in teknik_ozellikler.items())
        parts.append(ozet[:2000])
    return "\n\n".join(parts) if parts else ""


# -----------------------------------------------------------------------------
# Cetvel satırından Kalem alanlarına eşleme
# -----------------------------------------------------------------------------

def _cetvel_satirindan_kalem_alanlari(satir: dict) -> dict:
    """Vision/cetvel tablosundan gelen satırı Kalem model alanlarına uygun sözlüğe çevirir."""
    # Farklı anahtar isimleri (LLM bazen farklı döndürür)
    urun_adi = (
        satir.get("ad") or satir.get("kalem") or satir.get("urun_adi") or satir.get("aciklama")
        or satir.get("malzeme") or satir.get("description") or ""
    )
    if isinstance(urun_adi, (int, float)):
        urun_adi = str(urun_adi)
    urun_adi = (urun_adi or "").strip()[:255]

    birim = (
        satir.get("birim") or satir.get("unit") or satir.get("birim_fiyat_birim")
        or "Adet"
    )
    birim = (str(birim).strip() or "Adet")[:50]

    miktar = _decimal_parse(satir.get("miktar") or satir.get("adet") or satir.get("quantity") or satir.get("miktar_adet"), Decimal("1"))
    if miktar <= 0:
        miktar = Decimal("1")

    birim_fiyat = _decimal_parse(satir.get("birim_fiyat") or satir.get("unit_price") or satir.get("fiyat"))
    toplam = _decimal_parse(satir.get("toplam") or satir.get("toplam_fiyat") or satir.get("total"))
    if toplam <= 0 and birim_fiyat > 0:
        toplam = birim_fiyat * miktar

    return {
        "urun_adi": urun_adi or "Belirtilmemiş kalem",
        "adet": miktar,
        "birim": birim,
        "birim_fiyat": birim_fiyat,
        "toplam_fiyat": toplam,
    }


# -----------------------------------------------------------------------------
# Ana fonksiyon: Cetvel + Şartname birleştirip Kalem kaydet
# -----------------------------------------------------------------------------

def cetvel_ve_sartname_birlestir_ihale_kalem_kaydet(
    ihale,
    provider: str = "openai",
    cetvel_tablo: list = None,
    sartname_metni: str = None,
    vision_provider: str = "openai",
    mevcut_kalemleri_sil: bool = False,
) -> dict:
    """
    Teklif cetveli ile teknik şartnameyi karşılaştırır; her cetvel satırı için
    şartnamede ilgili paragrafı bulup teknik özellikleri ayıklar, birleştirip
    IhaleKalemi (Kalem) olarak kaydeder.

    Args:
        ihale: Ihale model örneği (cetvel_dosya ve sartname_dosya dolu olmalı).
        provider: Şartname eşleştirme için LLM ("openai" veya "anthropic").
        cetvel_tablo: Önceden çıkarılmış cetvel satırları listesi. None ise
            ihale.cetvel_dosya'dan document_vision ile çıkarılır.
        sartname_metni: Önceden okunmuş şartname metni. None ise
            ihale.sartname_dosya'dan file_to_text ile okunur.
        vision_provider: Cetvel görsel analizi için kullanılacak API (cetvel_tablo None ise).
        mevcut_kalemleri_sil: True ise bu ihaleye ait mevcut kalemler silinir, yeniden oluşturulur.

    Returns:
        {
            "olusturulan": int,
            "guncellenen": int,
            "atlanan": int,
            "hatalar": [str, ...],
        }
    """
    from ihaleler.models import Kalem

    sonuc = {"olusturulan": 0, "guncellenen": 0, "atlanan": 0, "hatalar": []}

    # Şartname metni
    if sartname_metni is None:
        if not ihale.sartname_dosya:
            sonuc["hatalar"].append("İhaleye teknik şartname dosyası yüklenmemiş.")
            return sonuc
        sartname_path = ihale.sartname_dosya.path
        sartname_metni = extract_text_from_file(sartname_path)
        if not sartname_metni or sartname_metni.startswith("Dosya bulunamadı") or sartname_metni.startswith("Hata"):
            sonuc["hatalar"].append("Teknik şartname metni okunamadı veya boş.")
            sartname_metni = ""

    # Cetvel tablosu (layout-based: PDF, Excel, Word, Resim)
    if cetvel_tablo is None:
        if not ihale.cetvel_dosya:
            sonuc["hatalar"].append("İhaleye birim fiyat cetveli dosyası yüklenmemiş.")
            return sonuc
        cetvel_path = ihale.cetvel_dosya.path
        analiz = extract_cetvel_layout_based(cetvel_path, provider=vision_provider)
        if not analiz.get("basari") or not analiz.get("kalemler"):
            sonuc["hatalar"].append(analiz.get("hata") or "Cetvel tablosu çıkarılamadı.")
            return sonuc
        cetvel_tablo = analiz["kalemler"]

    if not cetvel_tablo:
        sonuc["hatalar"].append("Cetvel tablosu boş.")
        return sonuc

    if mevcut_kalemleri_sil:
        Kalem.objects.filter(ihale=ihale).delete()

    for idx, satir in enumerate(cetvel_tablo):
        try:
            alanlar = _cetvel_satirindan_kalem_alanlari(satir)
            urun_adi = alanlar["urun_adi"]
            if not urun_adi or urun_adi == "Belirtilmemiş kalem":
                sonuc["atlanan"] += 1
                continue

            # Şartnameden bu kalem için paragraf + teknik özellikler
            sartname_sonuc = sartname_metninden_kalem_ozetleri_cikar(
                sartname_metni, urun_adi, provider=provider
            )
            teknik_ozet = _teknik_ozet_metin(
                sartname_sonuc["ilgili_paragraf"],
                sartname_sonuc["teknik_ozellikler"],
            )
            if sartname_sonuc.get("hata"):
                sonuc["hatalar"].append(f"[{urun_adi[:40]}...] {sartname_sonuc['hata']}")

            create_kwargs = {
                "ihale": ihale,
                "urun_adi": alanlar["urun_adi"],
                "adet": alanlar["adet"],
                "birim": alanlar["birim"],
                "birim_fiyat": alanlar["birim_fiyat"],
                "toplam_fiyat": alanlar["toplam_fiyat"],
                "teknik_sartname_ozeti": teknik_ozet or None,
            }
            if hasattr(Kalem, "teknik_ozellikler_json") and sartname_sonuc.get("teknik_ozellikler"):
                create_kwargs["teknik_ozellikler_json"] = sartname_sonuc["teknik_ozellikler"]
            kalem = Kalem.objects.create(**create_kwargs)
            try:
                from ihaleler.utils.urun_katalog_eslestir import kutuphane_urunu_bul_veya_olustur
                kutuphane_urunu_bul_veya_olustur(kalem)
            except Exception:
                pass
            sonuc["olusturulan"] += 1
        except Exception as e:
            sonuc["hatalar"].append(f"Satır {idx + 1}: {e}")
            sonuc["atlanan"] += 1

    return sonuc
