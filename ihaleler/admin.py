from django.contrib import admin
from .models import Hastane, Ihale, Kalem

@admin.register(Kalem)
class KalemAdmin(admin.ModelAdmin):
    # Listede hangi sütunlar görünsün?
    list_display = ('urun_adi', 'adet', 'birim_fiyat', 'ihale')
    # Sağ tarafa hangi filtreler gelsin?
    list_filter = ('ihale', 'ihale__hastane')
    # Arama çubuğu hangi alanlarda arasın?
    search_fields = ('urun_adi', 'teknik_sartname_ozellik')
    # Listede direkt düzenleme yapılabilsin mi? (Opsiyonel)
    list_editable = ('adet', 'birim_fiyat')

@admin.register(Ihale)
class IhaleAdmin(admin.ModelAdmin):
    list_display = ('ihale_no', 'ihale_adi', 'hastane', 'tarih')
    search_fields = ('ihale_no', 'ihale_adi')

admin.site.register(Hastane)