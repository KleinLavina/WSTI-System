from django.urls import path
from . import views

app_name = "main"

urlpatterns = [
    path('admin/', views.admin_dashboard, name='admin'),
    path("admin/departments/", views.department_list, name="departments"),
    path("admin/departments/<int:dept_id>/workers/", views.workers_by_department, name="workers"),
 
    path("admin/deadlines/", views.deadline_list, name="deadline-list"),
    path("admin/deadlines/<int:pk>/edit/", views.deadline_edit, name="deadline-edit"),
    path("admin/deadlines/<int:pk>/delete/", views.deadline_delete, name="deadline-delete"),
    path("admin/deadlines/<int:deadline_id>/statuses/", views.deadline_status_view, name="deadline-status"),
]
