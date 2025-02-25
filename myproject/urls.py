
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render

def index(req):
    return render(req, "index/index.html")

def privacy_policy(req):
    return render(req, "index/privacy-policy.html")

def terms_conditions(req):
    return render(req, "index/terms-conditions.html")

urlpatterns = [
    path('', index, name="index"),
    path('privacy_policy/', privacy_policy, name="privacy_policy"),
    path('terms_conditions/', terms_conditions, name="terms_conditions"),
    path('pickleit-admin-main/', admin.site.urls),
    path('user/', include('apps.user.urls')),
    path('team/', include('apps.team.urls')),
    path('accessories/', include('apps.pickleitcollection.urls')),
    path('chat/', include('apps.chat.urls')),
    path('admin/', include('apps.admin_side.urls')),
    path('accessories/', include('apps.store.urls')) 
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)