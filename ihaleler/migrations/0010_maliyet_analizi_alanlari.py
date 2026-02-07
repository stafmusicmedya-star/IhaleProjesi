# Generated manually for maliyet analizi alanları

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ihaleler', '0009_ihale_cetvel_dosya_ihale_sartname_dosya'),
    ]

    operations = [
        # Ihale modeli - maliyet analizi alanları
        migrations.AddField(
            model_name='ihale',
            name='tahmini_maliyet',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Tahmini Maliyet'),
        ),
        migrations.AddField(
            model_name='ihale',
            name='alinan_fiyat',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Alınan Fiyat (Toplam)'),
        ),
        migrations.AddField(
            model_name='ihale',
            name='satis_fiyati',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Satış Fiyatı (Toplam)'),
        ),
        migrations.AddField(
            model_name='ihale',
            name='kar_zarar_durumu',
            field=models.CharField(
                blank=True,
                choices=[('Kar', 'Kâr'), ('Zarar', 'Zarar'), ('Basababas', 'Başabaş'), ('', 'Belirsiz')],
                default='',
                max_length=20,
                verbose_name='Kâr/Zarar Durumu',
            ),
        ),
        # Kalem modeli - maliyet analizi alanları
        migrations.AddField(
            model_name='kalem',
            name='tahmini_maliyet',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Tahmini Maliyet'),
        ),
        migrations.AddField(
            model_name='kalem',
            name='alinan_fiyat',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Alınan Fiyat'),
        ),
        migrations.AddField(
            model_name='kalem',
            name='satis_fiyati',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='Satış Fiyatı'),
        ),
        migrations.AddField(
            model_name='kalem',
            name='kar_zarar_durumu',
            field=models.CharField(
                blank=True,
                choices=[('Kar', 'Kâr'), ('Zarar', 'Zarar'), ('Basababas', 'Başabaş'), ('', 'Belirsiz')],
                default='',
                max_length=20,
                verbose_name='Kâr/Zarar Durumu',
            ),
        ),
    ]
