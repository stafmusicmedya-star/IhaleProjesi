# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ihaleler', '0010_maliyet_analizi_alanlari'),
    ]

    operations = [
        migrations.AddField(
            model_name='kalem',
            name='teknik_ozellikler_json',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='Teknik Özellikler (renk, ölçü, kesit vb.)'),
        ),
    ]
