from django.urls import path
from . import views

app_name = "workers"

urlpatterns = [
    path("user/", views.user_dashboard, name='user'),
    path("user/reports/", views.my_reports, name="my-reports"),
    path("user/notifications/", views.my_notifications, name="my-notifications"),
]
