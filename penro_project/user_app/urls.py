from django.urls import path
from .views.dashboard_views import (
    dashboard
)
from .views.work_item_views import (
    user_work_items, user_work_item_detail
)

app_name = "user_app"

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("work-items/", user_work_items, name="work-items"),
    path("work-items/<int:item_id>/", user_work_item_detail, name="work-item-detail"),
]
