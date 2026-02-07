"""
Ürün Katalog mantığı: Yeni ihale kalemi girildiğinde veritabanındaki eski ürünlerle
(isim + teknik özellik) karşılaştırır; eşleşme varsa aynı benzersiz ID (UrunKutuphanesi) ile ilişkilendirir.
"""
import logging
import re
from decimal import Decimal

logger = logging.getLogger("ihaleler.parsing")


def _normalize_urun_adi(adi: str) -> str:
    """Eşleştirme için ürün adını normalize eder (küçük harf, fazla boşluk temizle)."""
    if not adi or not isinstance(adi, str):
        return ""
    s = adi.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s[:500]


def _ozellik_anahtarlari(teknik_ozellikler: dict) -> set:
    """Teknik özellikler dict'inden karşılaştırma için anahtar seti (normalize)."""
    if not teknik_ozellikler or not isinstance(teknik_ozellikler, dict):
        return set()
    return set(k.strip().lower() for k in teknik_ozellikler.keys() if k)


def _ozellik_benzerlik(tek1: dict, tek2: dict) -> float:
    """İki teknik özellik dict'i arasında 0-1 arası benzerlik (aynı anahtarların aynı değere sahip olma oranı)."""
    if not tek1 and not tek2:
        return 1.0
    k1 = _ozellik_anahtarlari(tek1)
    k2 = _ozellik_anahtarlari(tek2)
    ortak = k1 & k2
    if not ortak:
        return 0.0
    eslesen = 0
    for k in ortak:
        v1 = str((tek1 or {}).get(k, "")).strip().lower()
        v2 = str((tek2 or {}).get(k, "")).strip().lower()
        if v1 and v2 and v1 == v2:
            eslesen += 1
    return eslesen / len(ortak) if ortak else 0.0


def kutuphane_urunu_bul_veya_olustur(kalem) -> bool:
    """
    Kalem için katalogda eşleşen ürün arar; bulursa kalem.kutuphane_urunu atar,
    bulamazsa yeni UrunKutuphanesi oluşturup ona bağlar. Kalem kaydedilmiş olmalı (pk var).

    Returns:
        True eğer eşleştirme yapıldı veya yeni kayıt oluşturuldu.
    """
    from ihaleler.models import UrunKutuphanesi

    if not kalem or not getattr(kalem, "pk", None):
        return False

    urun_adi = (getattr(kalem, "urun_adi", None) or "").strip()
    if not urun_adi:
        return False

    norm_adi = _normalize_urun_adi(urun_adi)
    teknik = getattr(kalem, "teknik_ozellikler_json", None) or {}

    # Zaten bağlı mı?
    if getattr(kalem, "kutuphane_urunu_id", None):
        return True

    # Aynı normalize isim + teknik özellik benzerliği yüksek olan katalog kaydını ara
    adaylar = UrunKutuphanesi.objects.all()
    en_iyi = None
    en_iyi_skor = 0.0

    for urun in adaylar:
        if _normalize_urun_adi(urun.urun_adi) != norm_adi:
            continue
        urun_tek = getattr(urun, "teknik_ozellikler_json", None) or {}
        skor = _ozellik_benzerlik(teknik, urun_tek)
        if not teknik and not urun_tek:
            skor = 1.0
        if skor > en_iyi_skor:
            en_iyi_skor = skor
            en_iyi = urun

    # Eşik: isim aynı ve (teknik yoksa veya benzerlik yeterliyse)
    if en_iyi and (en_iyi_skor >= 0.5 or (not teknik and not getattr(en_iyi, "teknik_ozellikler_json", None))):
        kalem.kutuphane_urunu = en_iyi
        kalem.save(update_fields=["kutuphane_urunu"])
        logger.info("Kalem %s katalog ürünü ile eşlendi: %s (id=%s)", kalem.pk, en_iyi.urun_adi, en_iyi.pk)
        return True

    # Yeni katalog ürünü oluştur
    son_alis = Decimal("0")
    if getattr(kalem, "maliyet_birim_fiyat", None):
        try:
            son_alis = Decimal(str(kalem.maliyet_birim_fiyat))
        except Exception:
            pass
    yeni = UrunKutuphanesi.objects.create(
        urun_adi=urun_adi[:500],
        teknik_ozellikler_json=teknik if isinstance(teknik, dict) else {},
        teknik_sartname_metni=(getattr(kalem, "teknik_sartname_ozeti", None) or "")[:10000],
        son_alis_fiyati=son_alis,
    )
    kalem.kutuphane_urunu = yeni
    kalem.save(update_fields=["kutuphane_urunu"])
    logger.info("Yeni katalog ürünü oluşturuldu: id=%s, ad=%s; Kalem %s bağlandı.", yeni.pk, yeni.urun_adi, kalem.pk)
    return True
