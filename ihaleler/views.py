from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required


# =========================
# ANA SAYFA
# =========================
def anasayfa(request):
    return HttpResponse("Ana Sayfa çalışıyor ✅")


# =========================
# İHALE & DOĞRUDAN TEMİN
# =========================
def ihale_listesi(request):
    return HttpResponse("İhale Listesi sayfası")


def dogrudan_temin_listesi(request):
    return HttpResponse("Doğrudan Temin Listesi sayfası")


# =========================
# DOSYA & İŞLEMLER
# =========================
def dosya_yukleme(request):
    return HttpResponse("Dosya Yükleme Sayfası")


def ihale_sil(request, pk):
    return HttpResponse(f"{pk} ID'li ihale silinecek")


def ihale_excel_indir(request):
    return HttpResponse("Excel indirilecek")


# =========================
# TOPLU İŞLEMLER
# =========================
def toplu_fiyat_guncelle(request):
    return HttpResponse("Toplu fiyat güncelleme sayfası")


# =========================
# PROFİL & ANALİZ
# =========================
def profilim(request):
    return HttpResponse("Profilim sayfası")


def analiz_sayfasi(request):
    return HttpResponse("Analiz sayfası")


# =========================
# MESAİ
# =========================
def mesailerim_view(request):
    return HttpResponse("Mesailerim sayfası")


# =========================
# ARAÇLAR
# =========================
def arabalar_view(request):
    return HttpResponse("Araçlar yönetim sayfası")
