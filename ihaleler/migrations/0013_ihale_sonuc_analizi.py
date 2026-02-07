# İhale Sonuç Analizi alanları

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ihaleler', '0012_urun_katalog_ve_kalem_gorsel_fatura'),
    ]

    operations = [
        migrations.AddField(
            model_name='ihale',
            name='kazanan_firma',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='İhaleyi Kim Kazandı?'),
        ),
        migrations.AddField(
            model_name='ihale',
            name='kazanan_fiyat',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True, verbose_name='Kazanan Fiyat (TL)'),
        ),
        migrations.AddField(
            model_name='ihale',
            name='bizim_teklif',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True, verbose_name='Bizim Teklifimiz (TL)'),
        ),
    ]
