from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path('admin/', views.admin_dashboard, name='admin'),
    path("admin/departments/", views.department_list, name="departments"),
     path("admin/departments/<int:dept_id>/workers/", views.workers_by_department, name="workers"),

    path("user/", views.user_dashboard, name='user'),
]
