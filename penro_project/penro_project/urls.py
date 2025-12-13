from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('penro/django/admin/', admin.site.urls),

    # Login / Logout 
    path('auth/', include('accounts.urls')),
    path('admin/', include('admin_app.urls')),
    path('user/', include('user_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )