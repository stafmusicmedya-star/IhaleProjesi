"""
Birim teklif cetveli parsing servisi.
Tüm formatları (PDF, Excel, Word, Resim) destekler; sütun adına bağımlı kalmadan
görsel yerleşimden (layout) ad, miktar, birim ve fiyat çıkarır. Tüm adımlar loglanır.
"""
import json
import logging
import os
import re
from pathlib import Path

from ihaleler.utils.file_to_text import extract_text_from_file
from ihaleler.utils.document_vision import (
    analiz_et_ve_tablo_dondur,
    file_to_image_bytes,
)

logger = logging.getLogger("ihaleler.parsing")

# Word için metin tabanlı LLM tablo çıkarma
_CETVEL_METIN_SYSTEM = """Sen bir birim fiyat cetveli / teklif listesi analiz uzmanısın.
Sana bir belgenin ham metni (OCR veya Word'den) verilecek. Görsel yerleşim (layout) bilgisi metin sırası ve satır yapısından anlaşılacak.
Sütun isimlerine bağımlı kalma; satırların anlamından kalem adı, miktar, birim ve fiyat alanlarını çıkar.
Her satır için: ad (ürün/hizmet adı), miktar (sayı), birim (adet, m², kg, mt vb.), birim_fiyat, toplam (varsa).
Yanıtını SADECE şu JSON formatında ver: {"tablo": [{"ad": "...", "miktar": "...", "birim": "...", "birim_fiyat": "...", "toplam": "..."}, ...]}
Başlık satırlarını tabloya ekleme. Belirsiz satırları atla."""


def _get_api_keys():
    try:
        from django.conf import settings
        return {
            "openai": getattr(settings, "OPENAI_API_KEY", None) or os.environ.get("OPENAI_API_KEY"),
            "anthropic": getattr(settings, "ANTHROPIC_API_KEY", None) or os.environ.get("ANTHROPIC_API_KEY"),
        }
    except Exception:
        return {"openai": os.environ.get("OPENAI_API_KEY"), "anthropic": os.environ.get("ANTHROPIC_API_KEY")}


def _call_openai_text(system: str, user: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=4096,
    )
    return (r.choices[0].message.content or "").strip()


def _call_anthropic_text(system: str, user: str, api_key: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    r = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return (r.content[0].text if r.content else "").strip()


def _parse_tablo_from_text(text: str) -> list:
    text = text.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
        tablo = data.get("tablo") if isinstance(data, dict) else data
        return tablo if isinstance(tablo, list) else []
    except json.JSONDecodeError:
        return []


def _cetvel_from_word_text(word_text: str, provider: str = "openai", max_chars: int = 80000) -> list:
    """Word veya OCR metninden layout mantığıyla cetvel tablosu çıkarır."""
    keys = _get_api_keys()
    metin = word_text[:max_chars] if len(word_text) > max_chars else word_text
    user = f"Belge metni:\n\n{metin}\n\nYukarıdaki metinden birim fiyat cetveli kalemlerini çıkar (ad, miktar, birim, birim_fiyat, toplam)."
    try:
        if provider == "openai" and keys.get("openai"):
            raw = _call_openai_text(_CETVEL_METIN_SYSTEM, user, keys["openai"])
        elif provider == "anthropic" and keys.get("anthropic"):
            raw = _call_anthropic_text(_CETVEL_METIN_SYSTEM, user, keys["anthropic"])
        else:
            logger.warning("Word/OCR tablo çıkarma için API anahtarı yok; boş tablo dönüyor.")
            return []
        tablo = _parse_tablo_from_text(raw)
        for row in tablo:
            if "ad" not in row and "kalem" in row:
                row["ad"] = row["kalem"]
            if "kalem" not in row and "ad" in row:
                row["kalem"] = row["ad"]
        return tablo
    except Exception as e:
        logger.exception("Word/OCR tablo çıkarma hatası: %s", e)
        return []


def _normalize_row(row: dict) -> dict:
    """Farklı anahtar isimlerini tek forma (ad, miktar, birim, birim_fiyat, toplam) getirir."""
    ad = (
        row.get("ad") or row.get("kalem") or row.get("urun_adi") or row.get("aciklama")
        or row.get("malzeme") or row.get("description") or ""
    )
    ad = str(ad).strip()[:500]
    birim = str(row.get("birim") or row.get("unit") or "Adet").strip()[:50]
    miktar = row.get("miktar") or row.get("adet") or row.get("quantity") or row.get("miktar_adet") or "1"
    birim_fiyat = row.get("birim_fiyat") or row.get("unit_price") or row.get("fiyat") or "0"
    toplam = row.get("toplam") or row.get("toplam_fiyat") or row.get("total") or ""
    return {
        "ad": ad or "Belirtilmemiş",
        "miktar": miktar,
        "birim": birim or "Adet",
        "birim_fiyat": birim_fiyat,
        "toplam": toplam,
    }


def extract_cetvel_layout_based(
    file_path: str,
    provider: str = "openai",
    page_or_sheet_index: int = 0,
) -> dict:
    """
    Her türlü formatı (PDF, Excel, Word, Resim) analiz eder; sütun adına bağımlı kalmadan
    görsel yerleşimden birim teklif cetveli kalemlerini çıkarır: ad, miktar, birim, fiyat.

    Returns:
        {
            "basari": bool,
            "kalemler": [{"ad": "...", "miktar": "...", "birim": "...", "birim_fiyat": "...", "toplam": "..."}, ...],
            "hata": str | None,
            "kaynak": "vision" | "word_ocr",
        }
    """
    result = {"basari": False, "kalemler": [], "hata": None, "kaynak": None}
    path = Path(file_path)
    if not path.exists():
        result["hata"] = f"Dosya bulunamadı: {file_path}"
        logger.error(result["hata"])
        return result

    ext = path.suffix.lower()
    logger.info("Cetvel dosyası işleniyor: %s (uzantı: %s)", path.name, ext)

    # Word: metin + LLM (layout metin üzerinden)
    if ext in (".docx", ".doc"):
        try:
            text = extract_text_from_file(str(path))
            if not text or text.startswith("Dosya bulunamadı") or text.startswith("Hata"):
                result["hata"] = "Word metni okunamadı."
                logger.warning(result["hata"])
                return result
            logger.debug("Word metni okundu, uzunluk: %s", len(text))
            tablo = _cetvel_from_word_text(text, provider=provider)
            result["kaynak"] = "word_ocr"
            result["kalemler"] = [_normalize_row(r) for r in tablo]
            result["basari"] = bool(result["kalemler"])
            logger.info("Word/OCR cetvel çıkarıldı: %s kalem", len(result["kalemler"]))
            return result
        except Exception as e:
            result["hata"] = str(e)
            logger.exception("Word cetvel işleme hatası")
            return result

    # PDF, Excel, Resim: Vision (görsel layout)
    try:
        analiz = analiz_et_ve_tablo_dondur(
            str(path),
            page_or_sheet_index=page_or_sheet_index,
            provider=provider,
            ek_talimat="Her satır için mutlaka: kalem adı (ad), miktar, birim, birim_fiyat, toplam alanlarını döndür. Sütun başlıklarına bakma, görsel düzenden anla.",
        )
        if not analiz.get("basari"):
            result["hata"] = analiz.get("hata") or "Vision analiz başarısız"
            logger.warning(result["hata"])
            return result
        tablo = analiz.get("tablo") or []
        result["kalemler"] = [_normalize_row(r) for r in tablo]
        result["basari"] = True
        result["kaynak"] = "vision"
        logger.info("Vision cetvel çıkarıldı: %s kalem (%s)", len(result["kalemler"]), path.name)
        return result
    except Exception as e:
        result["hata"] = str(e)
        logger.exception("Cetvel Vision/OCR hatası: %s", path.name)
        return result
