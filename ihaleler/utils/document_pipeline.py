"""
İhale dosya işleme pipeline'ı: cetvel (PDF/Excel/Word/Resim) + teknik şartname
layout tabanlı parsing ile işlenir, Kalem kayıtları oluşturulur. Tüm adımlar loglanır.
"""
import logging

from ihaleler.utils.file_to_text import extract_text_from_file
from ihaleler.utils.parsing_service import extract_cetvel_layout_based
from ihaleler.utils.sartname_cetvel_eslestir import (
    cetvel_ve_sartname_birlestir_ihale_kalem_kaydet,
)

logger = logging.getLogger("ihaleler.parsing")


def ihale_dosyalarini_isle(
    ihale,
    provider: str = "openai",
    mevcut_kalemleri_sil: bool = True,
) -> dict:
    """
    İhalenin cetvel ve şartname dosyalarını profesyonel pipeline ile işler:
    1) Birim teklif cetvelini layout tabanlı parse eder (ad, miktar, birim, fiyat).
    2) Teknik şartnameyi analiz edip her kalemle eşleştirir; renk, ölçü vb. özellikleri çıkarır.
    3) Kalem kayıtlarını teknik_sartname_ozeti ve teknik_ozellikler_json ile oluşturur.
    Tüm adımlar logs/parsing.log ve konsola yazılır.

    Args:
        ihale: Ihale model örneği (cetvel_dosya, isteğe bağlı sartname_dosya).
        provider: "openai" veya "anthropic".
        mevcut_kalemleri_sil: True ise mevcut kalemler silinip yeniden oluşturulur.

    Returns:
        {
            "basari": bool,
            "olusturulan": int,
            "atlanan": int,
            "hatalar": [str],
            "cetvel_kaynak": "vision" | "word_ocr" | None,
        }
    """
    sonuc = {
        "basari": False,
        "olusturulan": 0,
        "atlanan": 0,
        "hatalar": [],
        "cetvel_kaynak": None,
    }
    logger.info("Pipeline başladı | ihale_id=%s | ihale_no=%s", ihale.pk, getattr(ihale, "ihale_no", ""))

    if not ihale.cetvel_dosya:
        sonuc["hatalar"].append("Cetvel dosyası yok.")
        logger.error("Cetvel dosyası yok | ihale_id=%s", ihale.pk)
        return sonuc

    try:
        cetvel_path = ihale.cetvel_dosya.path
        logger.info("Cetvel dosyası işleniyor | path=%s", cetvel_path)

        cetvel_analiz = extract_cetvel_layout_based(cetvel_path, provider=provider)
        sonuc["cetvel_kaynak"] = cetvel_analiz.get("kaynak")

        if not cetvel_analiz.get("basari"):
            sonuc["hatalar"].append(cetvel_analiz.get("hata") or "Cetvel çıkarılamadı.")
            logger.error("Cetvel çıkarılamadı | %s", cetvel_analiz.get("hata"))
            return sonuc

        kalemler = cetvel_analiz.get("kalemler") or []
        logger.info("Cetvel çıkarıldı | kalem_sayisi=%s | kaynak=%s", len(kalemler), sonuc["cetvel_kaynak"])

        if not kalemler:
            sonuc["hatalar"].append("Cetvelde kalem bulunamadı.")
            logger.warning("Cetvelde kalem yok")
            return sonuc

        sartname_metni = None
        if ihale.sartname_dosya:
            try:
                sartname_metni = extract_text_from_file(ihale.sartname_dosya.path)
                if sartname_metni and not sartname_metni.startswith("Dosya bulunamadı") and not sartname_metni.startswith("Hata"):
                    logger.info("Şartname metni okundu | uzunluk=%s", len(sartname_metni))
                else:
                    sartname_metni = ""
                    logger.warning("Şartname metni okunamadı veya boş")
            except Exception as e:
                logger.exception("Şartname okuma hatası: %s", e)
                sartname_metni = ""

        birlestir_sonuc = cetvel_ve_sartname_birlestir_ihale_kalem_kaydet(
            ihale,
            provider=provider,
            cetvel_tablo=kalemler,
            sartname_metni=sartname_metni or "",
            vision_provider=provider,
            mevcut_kalemleri_sil=mevcut_kalemleri_sil,
        )

        sonuc["olusturulan"] = birlestir_sonuc.get("olusturulan", 0)
        sonuc["atlanan"] = birlestir_sonuc.get("atlanan", 0)
        sonuc["hatalar"].extend(birlestir_sonuc.get("hatalar", []))
        sonuc["basari"] = sonuc["olusturulan"] > 0 or (sonuc["olusturulan"] == 0 and not kalemler)

        logger.info(
            "Pipeline bitti | ihale_id=%s | olusturulan=%s | atlanan=%s | hata_sayisi=%s",
            ihale.pk,
            sonuc["olusturulan"],
            sonuc["atlanan"],
            len(sonuc["hatalar"]),
        )
        for h in sonuc["hatalar"]:
            logger.warning("Pipeline hata: %s", h)

        return sonuc
    except Exception as e:
        sonuc["hatalar"].append(str(e))
        logger.exception("Pipeline kritik hata: %s", e)
        return sonuc
