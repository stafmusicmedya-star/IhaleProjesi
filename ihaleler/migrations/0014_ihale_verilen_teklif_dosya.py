# Verilen Teklif (ıslak imzalı çıktı) dosya alanı

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ihaleler', '0013_ihale_sonuc_analizi'),
    ]

    operations = [
        migrations.AddField(
            model_name='ihale',
            name='verilen_teklif_dosya',
            field=models.FileField(blank=True, null=True, upload_to='ihaleler/teklifler/', verbose_name='Verilen Teklif (ıslak imzalı çıktı)'),
        ),
    ]
