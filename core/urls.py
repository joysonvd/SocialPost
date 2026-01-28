"""
URL configuration for Social Media Scheduler.

Routes:
- /admin/ - Django admin interface
- /accounts/ - Authentication views (login, logout, register)
- / - Main scheduler app (dashboard, calendar, posts)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('scheduler.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
