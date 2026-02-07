# Generated migration for Arac mevcut_km and arac_foto

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ihaleler', '0015_ihale_cetvel_dosya_2_ihale_cetvel_dosya_3_ihale_sartname_dosya_2_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='arac',
            name='mevcut_km',
            field=models.PositiveIntegerField(default=0, verbose_name='Mevcut Kilometre'),
        ),
        migrations.AddField(
            model_name='arac',
            name='arac_foto',
            field=models.ImageField(blank=True, null=True, upload_to='arac_foto/%Y/%m/', verbose_name='Araç Fotoğrafı'),
        ),
    ]
