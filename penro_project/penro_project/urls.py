from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Login / Logout
    path('auth/', include('accounts.urls')),

    # Main App
    path('main/', include('main.urls')),
    path('workers/', include('workers.urls')),
]
