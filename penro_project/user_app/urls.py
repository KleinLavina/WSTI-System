from django.urls import path
from .views.dashboard_views import (
    dashboard
)
from .views.work_item_views import (
    user_work_items, user_work_item_detail, user_work_item_comments
)
from .views.user_work_item_threads import (
    user_work_item_threads
)

app_name = "user_app"

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("work-items/", user_work_items, name="work-items"),
    path("work-items/<int:item_id>/", user_work_item_detail, name="work-item-detail"),
    # user_app/urls.py
    path(
    "discussions/",
    user_work_item_threads,
    name="discussion-list"),

    path(
        "work-items/<int:item_id>/discussion/",
        user_work_item_comments,
        name="work-item-comments"
    ),
]
