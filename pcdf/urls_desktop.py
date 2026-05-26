"""
URL config para modo desktop (DEBUG=False).
Serve arquivos de mídia diretamente pelo Django (sem nginx).
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    # Mídia servida pelo Django (aceitável em app desktop local)
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
