from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # --- Ana Sayfa ---
    path('', views.anasayfa, name='ana_sayfa'),
    
    # --- İhale ve Doğrudan Temin Listeleri ---
    path('ihaleler/', views.ihale_listesi, name='ihale_listesi'),
    path('dogrudan-temin/', views.dogrudan_temin_listesi, name='dogrudan_temin'),
    
    # --- İşlem ve Dosya Yönetimi ---
    path('dosya-yukleme/', views.dosya_yukleme, name='dosya_yukleme'),
    path('sil/<int:pk>/', views.ihale_sil, name='ihale_sil'),
    path('excel-indir/', views.ihale_excel_indir, name='ihale_excel_indir'),
    
    # --- Veri Güncelleme ---
    path('fiyat-guncelle/', views.toplu_fiyat_guncelle, name='toplu_fiyat_guncelle'),

    # --- Profilim ve Analiz ---
    path('profilim/', views.profilim, name='profilim'),
    path('analiz/', views.analiz_sayfasi, name='analiz_sayfasi'),

    # --- Mesai Takip Sistemi ---
    path('mesailerim/', views.mesailerim_view, name='mesailerim_sayfasi'),

    # --- Arabalar ---
    # Sadece yetkili personelin erişebildiği araç yönetim paneli
    path('arabalar/', views.arabalar_view, name='arabalar_sayfasi'),

]

# --- Medya ve Statik Dosyalar Ayarı ---
# Logonun ve yüklenen araç resimlerinin görünmesi için bu blok kritiktir
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)