# Ürün Katalog (teknik_ozellikler_json) + Kalem görsel/fatura

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ihaleler', '0011_kalem_teknik_ozellikler_json'),
    ]

    operations = [
        migrations.AddField(
            model_name='urunkutuphanesi',
            name='teknik_ozellikler_json',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Teknik Özellikler (eşleştirme için)'),
        ),
        migrations.AddField(
            model_name='kalem',
            name='kalem_gorsel',
            field=models.ImageField(blank=True, null=True, upload_to='kalem_gorseller/%Y/%m/', verbose_name='Kalem Görseli'),
        ),
        migrations.AddField(
            model_name='kalem',
            name='fatura_dosya',
            field=models.FileField(blank=True, null=True, upload_to='kalem_faturalar/%Y/%m/', verbose_name='Fatura (PDF/Resim)'),
        ),
    ]
