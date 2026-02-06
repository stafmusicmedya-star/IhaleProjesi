import pandas as pd
from django.core.management.base import BaseCommand
from ihaleler.models import Kalem, Ihale, Hastane
from decimal import Decimal

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('excel_dosyası', type=str)

    def handle(self, *args, **options):
        df = pd.read_excel(options['excel_dosyası'])
        
        # Sabit bir hastane ve ihale oluşturuyoruz (Kalemlerin bağlanması için şart)
        hastane, _ = Hastane.objects.get_or_create(ad="Merkez Hastanesi", sehir="Ankara")
        ihale, _ = Ihale.objects.get_or_create(
            hastane=hastane, 
            ihale_no="2026/001", 
            ihale_adi="Excel Aktarım İhalesi",
            tarih="2026-02-04"
        )

        basari = 0
        for index, row in df.iterrows():
            try:
                # Sayıları temizleme (Nokta/Virgül karmaşasını çözer)
                def temizle(deger):
                    if pd.isna(deger) or str(deger).strip() == "": return "0"
                    t = str(deger).replace(',', '.') # Virgülü noktaya çevir
                    t = "".join(c for c in t if c.isdigit() or c == '.') # Sadece rakam ve nokta kalsın
                    return t if t else "0"

                Kalem.objects.create(
                    ihale=ihale,
                    urun_adi=str(row.get('urun_adi', 'Tanımsız Ürün')),
                    adet=int(float(temizle(row.get('adet', 0)))),
                    birim_fiyat=Decimal(temizle(row.get('birim_fiyat', 0)))
                )
                basari += 1
            except Exception as e:
                print(f"Satır {index+2} (Ürün: {row.get('urun_adi')}) atlandı. Hata: {e}")

        self.stdout.write(self.style.SUCCESS(f'Tamamlandı! {basari} adet kalem sisteme yüklendi.'))