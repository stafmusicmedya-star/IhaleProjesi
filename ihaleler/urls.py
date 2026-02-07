from django.urls import path
from . import views

urlpatterns = [
    path('', views.anasayfa, name='ana_sayfa'),
    path('ihaleler/', views.ihale_listesi, name='ihale_listesi'),
    path('dogrudan-temin/', views.dogrudan_temin_listesi, name='dogrudan_temin_listesi'),
    path('liste/', views.liste_filtre, name='liste_filtre'),
    path('dosya-yukleme/', views.dosya_yukleme, name='dosya_yukleme'),
    path('ihale/sil/<int:pk>/', views.ihale_sil, name='ihale_sil'),
    path('ihale/<int:pk>/incele/', views.ihale_detay, name='ihale_detay'),
    path('ihale/<int:pk>/excel-indir/', views.ihale_detay_excel_indir, name='ihale_detay_excel_indir'),
    path('ihale/<int:pk>/kalem-ekle/', views.kalem_ekle, name='kalem_ekle'),
    path('kalem/<int:pk>/gecmis/', views.kalem_gecmis, name='kalem_gecmis'),
    path('kalem/<int:pk>/gorsel-yukle/', views.kalem_gorsel_yukle, name='kalem_gorsel_yukle'),
    path('ihale/<int:pk>/verilen-teklif-yukle/', views.ihale_verilen_teklif_yukle, name='ihale_verilen_teklif_yukle'),
    path('ihale/excel-indir/', views.ihale_excel_indir, name='ihale_excel_indir'),
    path('toplu-fiyat-guncelle/', views.toplu_fiyat_guncelle, name='toplu_fiyat_guncelle'),

    path('profilim/', views.profilim, name='profilim'),
    path('analiz/', views.analiz_sayfasi, name='analiz'),

    path('mesailerim/', views.mesailerim_view, name='mesailerim'),
    path('arabalar/', views.arabalar_view, name='arabalar'),

    path('urun-katalog/', views.urun_katalog_listesi, name='urun_katalog'),
    path('urun-gecmis/<int:pk>/', views.urun_gecmis_analizi, name='urun_gecmis_analiz'),

    path('iletisim/', views.iletisim_view, name='iletisim'),
]
