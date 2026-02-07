from django.contrib import admin
from .models import Hastane, Ihale, Kalem, UrunKutuphanesi


@admin.register(Kalem)
class KalemAdmin(admin.ModelAdmin):
    list_display = ('urun_adi', 'adet', 'birim_fiyat', 'ihale', 'kutuphane_urunu')
    list_filter = ('ihale', 'ihale__hastane')
    search_fields = ('urun_adi', 'teknik_sartname_ozeti')
    list_editable = ('adet', 'birim_fiyat')
    readonly_fields = ('teknik_ozellikler_json',)
    fieldsets = (
        (None, {'fields': ('ihale', 'urun_adi', 'adet', 'birim', 'birim_fiyat', 'toplam_fiyat', 'kutuphane_urunu')}),
        ('Maliyet', {'fields': ('maliyet_birim_fiyat', 'alinan_fiyat', 'satis_fiyati', 'fatura_no')}),
        ('Görsel & Fatura', {'fields': ('kalem_gorsel', 'fatura_dosya')}),
        ('Teknik', {'fields': ('teknik_sartname_ozeti', 'teknik_ozellikler_json')}),
    )


@admin.register(UrunKutuphanesi)
class UrunKutuphanesiAdmin(admin.ModelAdmin):
    list_display = ('urun_adi', 'marka', 'son_alis_fiyati')
    search_fields = ('urun_adi', 'marka')

@admin.register(Ihale)
class IhaleAdmin(admin.ModelAdmin):
    list_display = ('ihale_no', 'ihale_adi', 'hastane', 'tarih', 'durum', 'kazanan_firma', 'bizim_teklif', 'kazanan_fiyat')
    search_fields = ('ihale_no', 'ihale_adi', 'kazanan_firma')
    list_filter = ('durum',)

admin.site.register(Hastane)