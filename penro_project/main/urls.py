from django.urls import path
from main.views.worker_views import (
    workers_by_department, worker_create, worker_edit, worker_delete
)
# Import the views from your split structure
from main.views.admin_dashboard import admin_dashboard
from main.views.department_views import (
    department_list, department_create, department_edit, department_delete
)

from main.views.deadline_views import (
    deadline_list, deadline_create, deadline_edit,
    deadline_delete, deadline_status_view
)

app_name = "main"

urlpatterns = [
    # Dashboard
    path('admin/', admin_dashboard, name='admin'),

    # Departments
    path("admin/departments/", department_list, name="departments"),
    path("admin/departments/create/", department_create, name="department-create"),
    path("admin/departments/<int:dept_id>/edit/", department_edit, name="department-edit"),
    path("admin/departments/<int:dept_id>/delete/", department_delete, name="department-delete"),

    # Workers
    path("admin/departments/<int:dept_id>/workers/", workers_by_department, name="workers"),
    path("admin/departments/<int:dept_id>/workers/create/", worker_create, name="worker-create"),
    path("admin/departments/<int:dept_id>/workers/<int:worker_id>/edit/", worker_edit, name="worker-edit"),
    path("admin/departments/<int:dept_id>/workers/<int:worker_id>/delete/", worker_delete, name="worker-delete"),

    # Deadlines
    path("admin/deadlines/", deadline_list, name="deadline-list"),
    path("admin/deadlines/create/", deadline_create, name="deadline-create"),
    path("admin/deadlines/<int:pk>/edit/", deadline_edit, name="deadline-edit"),
    path("admin/deadlines/<int:pk>/delete/", deadline_delete, name="deadline-delete"),
    path("admin/deadlines/<int:deadline_id>/statuses/", deadline_status_view, name="deadline-status"),
]
